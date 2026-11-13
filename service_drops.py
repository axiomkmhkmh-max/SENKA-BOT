"""Group drops (first to reply "بردار" wins), unique Soul Artifacts and the Artifact Exchange.

Atomicity rules (MongoDB):
  * an artifact has `cap` copies (tier-based); `held` counts holders + listings and changes only via a guarded $inc,
    so the cap is never exceeded; a drop reserves it with state=dropped (one live drop per artifact at a time);
  * a character holds at most one copy in `characters.artifact`, taken with the filter {artifact: None};
  * every multi-step move has a revert path, and `art_reconcile` repairs anything a crash left half-done.
"""
import random
import time
import uuid

from pymongo import ReturnDocument

from data_artifacts import ARTIFACTS, ART_BY_ID, art_cap
from data_items import ALL, BY_RARITY, WEAPON_BY_RARITY
from database import bump_counter, col, counter_get, game_settings, try_cooldown
from service_economy import inv_add, inv_get, inv_remove
from security import normalize_text
from service_log import log_event
from service_player import add_coins, get_char, today
from service_world import group_doc

CLAIM_WORDS = {"بردار", "بردارم", "برش دار", "برش دارم", "bardar", "take", "grab", "pick", "pick up", "claim", "loot"}
_act: dict = {}


# ---- seeding & repair ---------------------------------------------------------------------------------
async def art_seed():
    for a in ARTIFACTS:
        await col("artifacts").update_one({"_id": a["_id"]}, {"$setOnInsert": {"_id": a["_id"], "state": "free", "held": 0, "since": 0, "history": []}}, upsert=True)
        await col("artifacts").update_one({"_id": a["_id"], "held": {"$exists": False}}, {"$set": {"held": 0}})
    await art_reconcile()


async def art_reconcile():
    """Repair after crashes or admin resets: `held` must equal the characters holding it plus its active listings."""
    now = int(time.time())
    async for d in col("artifacts").find({}):
        aid = d["_id"]
        holders = await col("characters").count_documents({"artifact": aid})
        listed = await col("art_listings").count_documents({"art": aid, "status": "active"})
        st = d.get("state")
        upd = {"held": min(holders + listed, art_cap(aid))}
        unset = {"owner": "", "claimer": ""}
        if st == "dropped":
            live = await col("drops").find_one({"_id": d.get("drop_id"), "status": {"$in": ["active", "claiming"]}})
            if not live:
                upd["state"] = "free"
                unset["drop_id"] = ""
        elif st != "free":
            upd["state"] = "free"
        await col("artifacts").update_one({"_id": aid}, {"$set": upd, "$unset": unset})
    # drops that were mid-claim when the process died
    await col("drops").update_many({"status": "claiming", "end_at": {"$lte": now - 60}}, {"$set": {"status": "expired"}})


# ---- artifacts ----------------------------------------------------------------------------------------
# Several players may hold the same artifact, up to its tier cap (data_artifacts.art_cap). `held` counts
# holders plus active listings; every change goes through one atomic $inc guarded by {held: {$lt: cap}},
# so the cap can never be exceeded even when two players act at the same moment.
async def art_doc(aid: str) -> dict:
    return await col("artifacts").find_one({"_id": aid}) or {}


async def _has_listing(uid: int) -> bool:
    return bool(await col("art_listings").find_one({"seller": uid, "status": "active"}, {"_id": 1}))


def _hist(uid: int, how: str, price: int = 0) -> dict:
    return {"history": {"$each": [{"uid": uid, "at": int(time.time()), "how": how, "price": price}], "$slice": -10}}


async def _take_slot(aid: str) -> bool:
    return bool(await col("artifacts").find_one_and_update({"_id": aid, "held": {"$lt": art_cap(aid)}}, {"$inc": {"held": 1}}))


async def _free_slot(aid: str):
    await col("artifacts").update_one({"_id": aid, "held": {"$gt": 0}}, {"$inc": {"held": -1}})


async def art_claim(uid: int, aid: str, from_state: str = "dropped") -> str:
    ch = await get_char(uid)
    if not ch:
        return "noreg"
    if ch.get("artifact") or await _has_listing(uid):
        return "has"
    if not await _take_slot(aid):
        return "gone"
    r = await col("characters").update_one({"user_id": uid, "artifact": None}, {"$set": {"artifact": aid}})
    if not r.modified_count:
        await _free_slot(aid)
        return "has"
    await col("artifacts").update_one({"_id": aid, "state": from_state}, {"$set": {"state": "free"}, "$unset": {"drop_id": ""}, "$push": _hist(uid, "drop")})
    return "ok"


async def art_release(uid: int) -> str:
    ch = await get_char(uid)
    aid = (ch or {}).get("artifact")
    if not aid:
        return "none"
    r = await col("characters").update_one({"user_id": uid, "artifact": aid}, {"$unset": {"artifact": ""}})
    if not r.modified_count:
        return "busy"
    await _free_slot(aid)
    log_event("art", uid, f"آرتیفکت «{ART_BY_ID[aid]['name_fa']}» را رها کرد و به جهان بازگشت", art=aid)
    return "ok"


async def art_list(uid: int, price: int):
    st = await game_settings()
    ch = await get_char(uid)
    aid = (ch or {}).get("artifact")
    if not aid:
        return "none", None
    if not int(st["art_price_min"]) <= price <= int(st["art_price_max"]):
        return "price", None
    if await _has_listing(uid):
        return "dup", None
    # the listing keeps this player's copy reserved in `held`; only the holder slot is released (escrow: bonus stops while listed)
    r = await col("characters").update_one({"user_id": uid, "artifact": aid}, {"$unset": {"artifact": ""}})
    if not r.modified_count:
        return "busy", None
    now = int(time.time())
    doc = {"_id": uuid.uuid4().hex[:10], "art": aid, "seller": uid, "price": int(price), "status": "active",
           "created_at": now, "end_at": now + int(st["art_list_hours"]) * 3600}
    await col("art_listings").insert_one(doc)
    log_event("art", uid, f"«{ART_BY_ID[aid]['name_fa']}» را به قیمت {price:,} 🪙 در بازار آرتیفکت گذاشت", art=aid, price=price)
    return "ok", doc


async def _return_to_seller(d: dict):
    """The listing ends: the copy goes back to its seller (or back to the world if the seller already holds one)."""
    uid, aid = d["seller"], d["art"]
    r = await col("characters").update_one({"user_id": uid, "artifact": None}, {"$set": {"artifact": aid}})
    if not r.modified_count:
        await _free_slot(aid)


async def art_cancel(uid: int, lid: str) -> str:
    d = await col("art_listings").find_one_and_update({"_id": lid, "seller": uid, "status": "active"}, {"$set": {"status": "cancelled"}})
    if not d:
        return "gone"
    await _return_to_seller(d)
    log_event("art", uid, f"آگهی «{ART_BY_ID[d['art']]['name_fa']}» را لغو کرد", art=d["art"])
    return "ok"


async def art_buy(uid: int, lid: str):
    st = await game_settings()
    now = int(time.time())
    ch = await get_char(uid)
    if not ch:
        return "noreg", None
    if ch.get("artifact") or await _has_listing(uid):
        return "has", None
    d = await col("art_listings").find_one_and_update(
        {"_id": lid, "status": "active", "seller": {"$ne": uid}, "end_at": {"$gt": now}},
        {"$set": {"status": "sold", "buyer": uid, "sold_at": now}}, return_document=ReturnDocument.AFTER)
    if not d:
        return "gone", None

    async def revert():
        await col("art_listings").update_one({"_id": lid, "status": "sold", "buyer": uid}, {"$set": {"status": "active"}, "$unset": {"buyer": "", "sold_at": ""}})
    if not await add_coins(uid, -d["price"], "art_buy"):
        await revert()
        return "funds", None
    # the copy's slot was already reserved by the listing, so the buyer simply takes it over
    r = await col("characters").update_one({"user_id": uid, "artifact": None}, {"$set": {"artifact": d["art"]}})
    if not r.modified_count:
        await add_coins(uid, d["price"], "art_refund")
        await revert()
        return "has", None
    await col("artifacts").update_one({"_id": d["art"]}, {"$set": {"since": now}, "$push": _hist(uid, "market", d["price"])})
    fee = int(d["price"] * float(st["art_fee"]))
    await add_coins(d["seller"], d["price"] - fee, "art_sale")
    a = ART_BY_ID[d["art"]]
    log_event("art", uid, f"«{a['name_fa']}» را از بازار آرتیفکت به قیمت {d['price']:,} 🪙 خرید (فروشنده: {d['seller']}، کارمزد سوخته: {fee:,})",
              art=d["art"], price=d["price"], seller=d["seller"])
    return "ok", d


async def art_settle():
    """Expire old listings (scheduler): the artifact goes back to its seller."""
    now = int(time.time())
    while True:
        d = await col("art_listings").find_one_and_update({"status": "active", "end_at": {"$lte": now}}, {"$set": {"status": "expired"}})
        if not d:
            break
        await _return_to_seller(d)
        log_event("art", d["seller"], f"آگهی «{ART_BY_ID[d['art']]['name_fa']}» منقضی شد و برگشت", art=d["art"])


async def art_registry() -> list:
    """[(artifact, state, holders)] where holders is a list of {name, level} for every player holding a copy."""
    docs = {d["_id"]: d async for d in col("artifacts").find({})}
    out = []
    for a in ARTIFACTS:
        d = docs.get(a["_id"], {})
        holders = [c async for c in col("characters").find({"artifact": a["_id"]}, {"user_id": 1, "name": 1, "level": 1})]
        state = "dropped" if d.get("state") == "dropped" else ("full" if d.get("held", 0) >= a["cap"] else "free")
        out.append((a, state, holders))
    return out


async def art_listings_page(page: int, per: int):
    q = {"status": "active", "end_at": {"$gt": int(time.time())}}
    total = await col("art_listings").count_documents(q)
    docs = await col("art_listings").find(q).sort("price", 1).skip(page * per).limit(per).to_list(per)
    return docs, total


# ---- drops --------------------------------------------------------------------------------------------
def pick_item(rng=random) -> str:
    rar = rng.choices(("Rare", "Epic", "Legendary"), (62, 28, 10))[0]
    wp = WEAPON_BY_RARITY.get(rar) or []
    if wp and rng.random() < 0.3:
        return rng.choice(wp)
    pool = [i for i in BY_RARITY.get(rar, []) if ALL[i].get("tradeable")]
    return rng.choice(pool or BY_RARITY["Rare"])


async def _reserve_art(drop_id: str, aid: str = None):
    """Pick an artifact that still has a free copy and is not already on another drop."""
    if aid:
        ids = [aid]
    else:
        ids = [d["_id"] async for d in col("artifacts").find({}, {"_id": 1, "held": 1}) if (d.get("held") or 0) < art_cap(d["_id"])]
    random.shuffle(ids)
    for i in ids:
        hit = await col("artifacts").find_one_and_update({"_id": i, "state": {"$ne": "dropped"}, "held": {"$lt": art_cap(i)}},
                                                         {"$set": {"state": "dropped", "drop_id": drop_id}})
        if hit:
            return i
    return None


async def drop_roll(chat_id: int, uid: int) -> bool:
    """Called for every group message: True when it is time to drop something in this chat."""
    st = await game_settings()
    if not st["drop_enabled"]:
        return False
    now = time.time()
    a = _act.get(chat_id)
    if not a or now - a["t"] > 3600:
        a = _act[chat_id] = {"n": 0, "u": set(), "t": now}
    a["n"] += 1
    a["u"].add(uid)
    if a["n"] < int(st["drop_min_msgs"]) or len(a["u"]) < int(st["drop_min_users"]):
        return False
    _act.pop(chat_id, None)
    if random.random() > float(st["drop_chance"]):
        return False
    if (await group_doc(chat_id)).get("drops_off"):
        return False
    return not await try_cooldown(f"dropspawn:{chat_id}", int(st["drop_cooldown_minutes"]) * 60)


async def drop_create(chat_id: int, dropper: int = 0, dropper_name: str = "", kind: str = None, ref: str = None):
    """Reserve the prize and create the drop document (message id is attached after sending). None = nothing to drop."""
    st = await game_settings()
    did = uuid.uuid4().hex[:10]
    if kind is None:
        if random.random() < float(st["drop_artifact_chance"]):
            ref = await _reserve_art(did)
            kind = "art" if ref else None
        if kind is None:
            kind, ref = "item", pick_item()
    elif kind == "art":
        ref = await _reserve_art(did, ref)
        if not ref:
            return None
    elif kind == "item" and (not ref or ref not in ALL):
        ref = pick_item()
    now = int(time.time())
    doc = {"_id": did, "chat_id": chat_id, "msg_id": None, "kind": kind, "ref": ref, "dropper": dropper, "dropper_name": dropper_name[:40],
           "status": "active", "created_at": now, "end_at": now + int(st["drop_ttl_seconds"])}
    await col("drops").insert_one(doc)
    return doc


async def _refund(doc: dict):
    """A player-made drop nobody took (or that could not be posted): the item goes back to its owner."""
    if doc.get("kind") == "item" and doc.get("dropper"):
        await inv_add(doc["dropper"], doc["ref"], 1, force=True)


def find_item(items: dict, query: str):
    """Match a typed name against tradeable items in a bag -> (item_id | None, 'ok'|'none'|'amb')."""
    q = normalize_text(query)
    if len(q) < 2:
        return None, "none"
    pool = [(i, [normalize_text(ALL[i].get("name_fa", "")), normalize_text(ALL[i].get("name_en", ""))]) for i, n in items.items() if n > 0 and i in ALL and ALL[i].get("tradeable")]
    exact = [i for i, names in pool if q in names]
    if len(exact) == 1:
        return exact[0], "ok"
    part = exact or [i for i, names in pool if any(q in nm for nm in names)]
    if len(part) == 1:
        return part[0], "ok"
    return None, ("amb" if part else "none")


async def player_drop_create(uid: int, chat_id: int, query: str, name: str):
    """A player throws one of their own tradeable items into the group. -> (status, doc|None)."""
    st = await game_settings()
    if not st["drop_player_enabled"] or (await group_doc(chat_id)).get("drops_off"):
        return "off", None
    ch = await get_char(uid)
    if not ch:
        return "noreg", None
    if ch["level"] < int(st["drop_player_min_level"]):
        return "level", None
    if time.time() - ch.get("created_at", 0) < int(st["drop_player_min_age_hours"]) * 3600:
        return "new", None
    day = f"pdrop:{uid}:{today()}"
    if await counter_get(day) >= int(st["drop_player_daily"]):
        return "cap", None
    iid, how = find_item((await inv_get(uid))["items"], query)
    if not iid:
        return how, None
    if await try_cooldown(f"pdrop:{uid}", int(st["drop_player_cooldown"])):
        return "cd", None
    if not await inv_remove(uid, iid, 1):
        return "none", None
    await bump_counter(day, 1, 10 ** 6)
    now = int(time.time())
    doc = {"_id": uuid.uuid4().hex[:10], "chat_id": chat_id, "msg_id": None, "kind": "item", "ref": iid, "dropper": uid, "dropper_name": name[:40],
           "status": "active", "created_at": now, "end_at": now + int(st["drop_ttl_seconds"])}
    await col("drops").insert_one(doc)
    return "ok", doc


async def drop_attach(did: str, msg_id: int):
    await col("drops").update_one({"_id": did}, {"$set": {"msg_id": msg_id}})


async def drop_abort(doc: dict):
    """Sending failed: give the prize back."""
    await col("drops").update_one({"_id": doc["_id"]}, {"$set": {"status": "failed"}})
    await _refund(doc)
    if doc["kind"] == "art":
        await col("artifacts").update_one({"_id": doc["ref"], "state": "dropped", "drop_id": doc["_id"]}, {"$set": {"state": "free"}, "$unset": {"drop_id": ""}})


async def drop_claim(chat_id: int, uid: int, reply_msg_id: int):
    """-> (status, doc). status: nodrop | gone | noreg | level | cap | has | full | ok."""
    st = await game_settings()
    doc = await col("drops").find_one({"chat_id": chat_id, "msg_id": reply_msg_id})
    if not doc:
        return "nodrop", None
    now = int(time.time())
    if doc["status"] != "active" or doc["end_at"] <= now:
        return "gone", doc
    ch = await get_char(uid)
    if not ch:
        return "noreg", doc
    if doc.get("dropper") and doc["dropper"] == uid:
        return "self", doc
    pair = f"dpair:{doc.get('dropper', 0)}:{uid}:{today()}"
    if doc.get("dropper") and await counter_get(pair) >= int(st["drop_pair_daily"]):
        return "pair", doc
    if ch["level"] < int(st["drop_min_level"]):
        return "level", doc
    key = f"dropclaim:{uid}:{today()}"
    if await counter_get(key) >= int(st["drop_daily_per_user"]):
        return "cap", doc
    got = await col("drops").find_one_and_update({"_id": doc["_id"], "status": "active", "end_at": {"$gt": now}},
                                                 {"$set": {"status": "claiming", "claimer": uid}}, return_document=ReturnDocument.AFTER)
    if not got:
        return "gone", doc
    if got["kind"] == "art":
        res = await art_claim(uid, got["ref"], "dropped")
        res = "ok" if res == "ok" else ("has" if res == "has" else "gone")
    else:
        res = "ok" if await inv_add(uid, got["ref"], 1) else "full"
    if res == "gone":
        await col("drops").update_one({"_id": got["_id"]}, {"$set": {"status": "expired"}})
        return "gone", got
    if res != "ok":
        await col("drops").update_one({"_id": got["_id"]}, {"$set": {"status": "active"}, "$unset": {"claimer": ""}})
        return res, got
    await bump_counter(key, 1, 10 ** 6)
    if got.get("dropper"):
        await bump_counter(pair, 1, 10 ** 6)
    await col("drops").update_one({"_id": got["_id"]}, {"$set": {"status": "claimed", "claimed_at": int(time.time()), "claimer_name": ch["name"]}})
    got["claimer_name"], got["status"] = ch["name"], "claimed"
    return "ok", got


async def expire_drops() -> list:
    now = int(time.time())
    out = []
    while True:
        d = await col("drops").find_one_and_update({"status": "active", "end_at": {"$lte": now}}, {"$set": {"status": "expired"}}, return_document=ReturnDocument.AFTER)
        if not d:
            break
        if d["kind"] == "art":
            await col("artifacts").update_one({"_id": d["ref"], "state": "dropped", "drop_id": d["_id"]}, {"$set": {"state": "free"}, "$unset": {"drop_id": ""}})
        await _refund(d)
        out.append(d)
    return out


async def set_group_drops(chat_id: int, on: bool):
    await col("groups").update_one({"chat_id": chat_id}, {"$set": {"drops_off": not on}, "$setOnInsert": {"chat_id": chat_id, "lang": "fa"}}, upsert=True)

# --- NEW BLEACH VIRAL SYSTEM: Gillian / spirit-chest typing race ---
_typing = {}  # chat_id -> (normalised phrase, end_at, drop id): keeps the hot path (every group message) free of DB reads


async def typing_roll(chat_id: int):
    """Count one group message; return a new typing-race doc when the chat is lively enough, else None."""
    from data_artifacts import VERSES
    st = await game_settings()
    if not st["drop_enabled"] or (await group_doc(chat_id)).get("drops_off"):
        return None
    now = int(time.time())
    s = await col("type_state").find_one_and_update({"_id": chat_id}, {"$inc": {"n": 1}, "$setOnInsert": {"last": 0}}, upsert=True,
                                                    return_document=ReturnDocument.AFTER)
    if s["n"] < int(st["type_min_msgs"]) or now - int(s.get("last", 0)) < int(st["type_cooldown"]):
        return None
    if not (await col("type_state").update_one({"_id": chat_id, "last": s.get("last", 0)}, {"$set": {"n": 0, "last": now}})).modified_count:
        return None
    phrase = random.choice(VERSES)
    doc = {"_id": uuid.uuid4().hex[:10], "chat_id": chat_id, "phrase": phrase, "kind": random.choice(["gillian", "chest"]),
           "status": "active", "created_at": now, "end_at": now + int(st["type_ttl"])}
    await col("type_drops").insert_one(doc)
    from data_artifacts import norm_phrase
    _typing[chat_id] = (norm_phrase(phrase), doc["end_at"], doc["_id"])
    return doc


async def typing_attach(did: str, msg_id: int):
    await col("type_drops").update_one({"_id": did}, {"$set": {"msg_id": msg_id}})


async def typing_abort(did: str, chat_id: int):
    _typing.pop(chat_id, None)
    await col("type_drops").update_one({"_id": did}, {"$set": {"status": "failed"}})


async def typing_claim(chat_id: int, uid: int, text: str):
    """-> (doc, name, xp, coins) when `text` is exactly the verse of the live race and the sender may win it, else None."""
    from data_artifacts import norm_phrase
    cur = _typing.get(chat_id)
    if not cur or cur[1] <= time.time():
        _typing.pop(chat_id, None)
        return None
    if norm_phrase(text) != cur[0]:
        return None
    ch = await get_char(uid)
    st = await game_settings()
    if not ch or ch["level"] < int(st["drop_min_level"]):
        return None
    if await counter_get(f"typing:{uid}:{today()}") >= int(st["type_daily_cap"]):
        return None
    doc = await col("type_drops").find_one_and_update({"_id": cur[2], "status": "active", "end_at": {"$gt": int(time.time())}},
                                                      {"$set": {"status": "won", "winner": uid, "won_at": int(time.time())}},
                                                      return_document=ReturnDocument.AFTER)
    if not doc:
        return None
    _typing.pop(chat_id, None)
    await bump_counter(f"typing:{uid}:{today()}", 1, int(st["type_daily_cap"]))
    from service_player import add_xp
    xp, coins = int((80 + 15 * ch["level"]) * 3), int((150 + 25 * ch["level"]) * 2)  # a "Reiatsu surge": triple XP
    await add_xp(uid, xp, "typing")
    await add_coins(uid, coins, "typing")
    return doc, ch["name"], xp, coins


async def typing_expire():
    """Close races nobody won. Returns the docs so the scheduler can edit their messages."""
    now = int(time.time())
    out = []
    while True:
        d = await col("type_drops").find_one_and_update({"status": "active", "end_at": {"$lte": now}}, {"$set": {"status": "expired"}},
                                                        return_document=ReturnDocument.AFTER)
        if not d:
            return out
        _typing.pop(d["chat_id"], None)
        out.append(d)
