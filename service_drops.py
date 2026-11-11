"""Group drops (first to reply "بردار" wins), unique Soul Artifacts and the Artifact Exchange.

Atomicity rules (MongoDB):
  * an artifact document moves free -> dropped -> claiming -> owned (or owned -> listed -> owned/sold, owned -> free),
    every hop is a single find_one_and_update on the expected previous state, so two people can never own the same one;
  * the character holds it in `characters.artifact` (max one per player), taken with the filter {artifact: None};
  * every multi-step move has a revert path, and `art_reconcile` repairs anything a crash left half-done.
"""
import random
import time
import uuid

from pymongo import ReturnDocument

from data_artifacts import ARTIFACTS, ART_BY_ID
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
        await col("artifacts").update_one({"_id": a["_id"]}, {"$setOnInsert": {"_id": a["_id"], "state": "free", "owner": None, "since": 0, "history": []}}, upsert=True)
    await art_reconcile()


async def art_reconcile():
    """Repair after crashes or admin resets: every artifact must match what characters and listings really say."""
    now = int(time.time())
    async for d in col("artifacts").find({}):
        aid, st = d["_id"], d.get("state")
        holder = await col("characters").find_one({"artifact": aid}, {"user_id": 1})
        if holder:
            if st != "owned" or d.get("owner") != holder["user_id"]:
                await col("artifacts").update_one({"_id": aid}, {"$set": {"state": "owned", "owner": holder["user_id"]}})
            continue
        if st in ("owned", "claiming", "releasing"):
            await col("artifacts").update_one({"_id": aid, "state": st}, {"$set": {"state": "free", "owner": None}, "$unset": {"claimer": "", "drop_id": ""}})
        elif st == "listed":
            if not await col("art_listings").find_one({"art": aid, "status": "active"}):
                await col("artifacts").update_one({"_id": aid, "state": "listed"}, {"$set": {"state": "free", "owner": None}})
        elif st == "dropped":
            live = await col("drops").find_one({"_id": d.get("drop_id"), "status": {"$in": ["active", "claiming"]}})
            if not live:
                await col("artifacts").update_one({"_id": aid, "state": "dropped"}, {"$set": {"state": "free"}, "$unset": {"drop_id": ""}})
    # drops that were mid-claim when the process died
    await col("drops").update_many({"status": "claiming", "end_at": {"$lte": now - 60}}, {"$set": {"status": "expired"}})


# ---- artifacts ----------------------------------------------------------------------------------------
async def art_doc(aid: str) -> dict:
    return await col("artifacts").find_one({"_id": aid}) or {}


async def _has_listing(uid: int) -> bool:
    return bool(await col("art_listings").find_one({"seller": uid, "status": "active"}, {"_id": 1}))


def _hist(uid: int, how: str, price: int = 0) -> dict:
    return {"history": {"$each": [{"uid": uid, "at": int(time.time()), "how": how, "price": price}], "$slice": -10}}


async def art_claim(uid: int, aid: str, from_state: str = "dropped") -> str:
    ch = await get_char(uid)
    if not ch:
        return "noreg"
    if ch.get("artifact") or await _has_listing(uid):
        return "has"
    d = await col("artifacts").find_one_and_update({"_id": aid, "state": from_state}, {"$set": {"state": "claiming", "claimer": uid}})
    if not d:
        return "gone"
    r = await col("characters").update_one({"user_id": uid, "artifact": None}, {"$set": {"artifact": aid}})
    if not r.modified_count:
        await col("artifacts").update_one({"_id": aid}, {"$set": {"state": from_state}, "$unset": {"claimer": ""}})
        return "has"
    await col("artifacts").update_one({"_id": aid}, {"$set": {"owner": uid, "state": "owned", "since": int(time.time())},
                                                     "$unset": {"claimer": "", "drop_id": ""}, "$push": _hist(uid, "drop")})
    return "ok"


async def art_release(uid: int) -> str:
    ch = await get_char(uid)
    aid = (ch or {}).get("artifact")
    if not aid:
        return "none"
    d = await col("artifacts").find_one_and_update({"_id": aid, "owner": uid, "state": "owned"}, {"$set": {"state": "releasing"}})
    if not d:
        return "busy"
    r = await col("characters").update_one({"user_id": uid, "artifact": aid}, {"$unset": {"artifact": ""}})
    if not r.modified_count:
        await col("artifacts").update_one({"_id": aid}, {"$set": {"state": "owned"}})
        return "busy"
    await col("artifacts").update_one({"_id": aid}, {"$set": {"state": "free", "owner": None}})
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
    d = await col("artifacts").find_one_and_update({"_id": aid, "owner": uid, "state": "owned"}, {"$set": {"state": "listed"}})
    if not d:
        return "busy", None
    r = await col("characters").update_one({"user_id": uid, "artifact": aid}, {"$unset": {"artifact": ""}})  # escrow: bonus stops while listed
    if not r.modified_count:
        await col("artifacts").update_one({"_id": aid}, {"$set": {"state": "owned"}})
        return "busy", None
    now = int(time.time())
    doc = {"_id": uuid.uuid4().hex[:10], "art": aid, "seller": uid, "price": int(price), "status": "active",
           "created_at": now, "end_at": now + int(st["art_list_hours"]) * 3600}
    await col("art_listings").insert_one(doc)
    log_event("art", uid, f"«{ART_BY_ID[aid]['name_fa']}» را به قیمت {price:,} 🪙 در بازار آرتیفکت گذاشت", art=aid, price=price)
    return "ok", doc


async def _return_to_seller(d: dict):
    uid, aid = d["seller"], d["art"]
    r = await col("characters").update_one({"user_id": uid, "artifact": None}, {"$set": {"artifact": aid}})
    if r.matched_count:
        await col("artifacts").update_one({"_id": aid}, {"$set": {"state": "owned", "owner": uid}})
    else:  # seller deleted / already holds another: the artifact goes back to the world
        await col("artifacts").update_one({"_id": aid}, {"$set": {"state": "free", "owner": None}})


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
    r = await col("characters").update_one({"user_id": uid, "artifact": None}, {"$set": {"artifact": d["art"]}})
    if not r.modified_count:
        await add_coins(uid, d["price"], "art_refund")
        await revert()
        return "has", None
    await col("artifacts").update_one({"_id": d["art"]}, {"$set": {"owner": uid, "state": "owned", "since": now}, "$push": _hist(uid, "market", d["price"])})
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
    """[(artifact, state, owner_name|None)] for the world registry."""
    docs = {d["_id"]: d async for d in col("artifacts").find({})}
    owners = {d["owner"] for d in docs.values() if d.get("owner")}
    names = {}
    if owners:
        async for c in col("characters").find({"user_id": {"$in": list(owners)}}, {"user_id": 1, "name": 1, "level": 1}):
            names[c["user_id"]] = c
    out = []
    for a in ARTIFACTS:
        d = docs.get(a["_id"], {})
        o = names.get(d.get("owner"))
        out.append((a, d.get("state", "free"), o))
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
    ids = [aid] if aid else [d["_id"] async for d in col("artifacts").find({"state": "free"}, {"_id": 1})]
    random.shuffle(ids)
    for i in ids:
        hit = await col("artifacts").find_one_and_update({"_id": i, "state": "free"}, {"$set": {"state": "dropped", "drop_id": drop_id}})
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
    await col("groups").update_one({"chat_id": chat_id}, {"$set": {"drops_off": not on}, "$setOnInsert": {"chat_id": chat_id, "lang": "both"}}, upsert=True)
