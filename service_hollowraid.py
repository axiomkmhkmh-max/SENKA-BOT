"""Hollow / Menos incursions in group chats: while a group chats, a Hollow (rarely a Menos Grande) tears through the Garganta.
Members reply to its message with a strike word; damage = their Power, shared rewards by damage share, daily reward cap per player.
Collections: hollow_raids (one doc per incursion), raid_state (per-chat message counter + last spawn). Every limit is a live `set` key (raid_*)."""
import random
import time
import uuid

from pymongo import ReturnDocument

from data_world import day_id
from database import bump_counter, col, game_settings, try_cooldown
from service_economy import inv_add, roll_drop
from service_bleach_systems import stance_mult
from service_player import add_coins, add_xp, get_char, power
from service_world import group_doc

STRIKE_WORDS = {"حمله", "ضربه", "بزن", "سرو", "attack", "strike", "hit", "cero", "slash"}


async def raid_roll(chat_id: int):
    """Count one group message; spawn an incursion when the chat is lively enough. Returns the new doc or None."""
    st = await game_settings()
    if (await group_doc(chat_id)).get("drops_off"):
        return None
    now = int(time.time())
    s = await col("raid_state").find_one_and_update({"_id": chat_id}, {"$inc": {"n": 1}, "$setOnInsert": {"last": 0}},
                                                    upsert=True, return_document=ReturnDocument.AFTER)
    if s["n"] < int(st["raid_min_msgs"]) or now - int(s.get("last", 0)) < int(st["raid_cooldown"]):
        return None
    # one winner of the race resets the counter
    got = await col("raid_state").update_one({"_id": chat_id, "last": s.get("last", 0)}, {"$set": {"n": 0, "last": now}})
    if not got.modified_count:
        return None
    if await col("hollow_raids").find_one({"chat_id": chat_id, "status": "active", "end_at": {"$gt": now}}):
        return None
    menos = random.random() < float(st["raid_menos_chance"])
    hp = int(st["raid_hp"]) * (int(st["raid_menos_mult"]) if menos else 1)
    doc = {"_id": uuid.uuid4().hex[:10], "chat_id": chat_id, "kind": "menos" if menos else "hollow", "hp": hp, "max_hp": hp,
           "status": "active", "created_at": now, "end_at": now + int(st["raid_ttl"]), "hits": {}, "names": {}, "lv": 0}
    await col("hollow_raids").insert_one(doc)
    return doc


async def raid_attach(did: str, msg_id: int):
    await col("hollow_raids").update_one({"_id": did}, {"$set": {"msg_id": msg_id}})


async def raid_abort(did: str):
    await col("hollow_raids").update_one({"_id": did}, {"$set": {"status": "failed"}})


async def raid_strike(chat_id: int, uid: int, reply_msg_id=None):
    """-> (result, doc, dmg). result: nodoc | gone | noreg | level | cd | hit | dead (this strike killed it)."""
    now = int(time.time())
    if reply_msg_id is None:  # plain «حمله» without a reply: hit the incursion currently open in this chat
        doc = await col("hollow_raids").find_one({"chat_id": chat_id, "status": "active", "end_at": {"$gt": now}})
    else:
        doc = await col("hollow_raids").find_one({"chat_id": chat_id, "msg_id": reply_msg_id})
    if not doc:
        return "nodoc", None, 0
    if doc["status"] != "active" or doc["end_at"] <= now:
        if doc["status"] == "active":
            await col("hollow_raids").update_one({"_id": doc["_id"], "status": "active"}, {"$set": {"status": "expired"}})
            doc["status"] = "expired"
        return "gone", doc, 0
    ch = await get_char(uid)
    if not ch:
        return "noreg", doc, 0
    st = await game_settings()
    if ch["level"] < int(st["raid_min_level"]):
        return "level", doc, 0
    if await try_cooldown(f"raid:{chat_id}:{uid}", float(st["raid_strike_cd"])):
        return "cd", doc, 0
    sm = stance_mult(ch)  # --- NEW BLEACH VIRAL SYSTEM: Shikai / Bankai / Hollow Mask stance
    if sm == 0.0:
        return "rage", doc, 0
    dmg = max(20, int(power(ch) * random.uniform(0.85, 1.15) * float(st["raid_dmg_k"]) * sm))
    after = await col("hollow_raids").find_one_and_update(
        {"_id": doc["_id"], "status": "active", "end_at": {"$gt": now}},
        {"$inc": {"hp": -dmg, f"hits.{uid}": dmg}, "$set": {f"names.{uid}": ch["name"]}, "$max": {"lv": int(ch["level"])}},
        return_document=ReturnDocument.AFTER)
    if not after:
        return "gone", doc, 0
    if after["hp"] <= 0:
        killed = await col("hollow_raids").find_one_and_update({"_id": doc["_id"], "status": "active"},
                                                               {"$set": {"status": "dead", "dead_at": now}},
                                                               return_document=ReturnDocument.AFTER)
        if killed:
            return "dead", killed, dmg
    return "hit", after, dmg


RAID_EXTRA_DROP_P = 0.4  # chance each non-top fighter gets an item when the incursion falls


async def raid_settle(doc: dict) -> dict:
    """Pay everyone who hit it. Returns {"top": [(name, dmg)], "paid": n, "drop": (uid, item) | None}."""
    st = await game_settings()
    hits = {int(k): int(v) for k, v in (doc.get("hits") or {}).items()}
    total = max(1, sum(hits.values()))
    menos = doc["kind"] == "menos"
    mult = {"menos": 3.0, "quincy": 4.0}.get(doc["kind"], 1.0)
    lv = max(1, int(doc.get("lv") or 1))
    paid = 0
    paid_uids = set()
    for uid, dmg in hits.items():
        if not await bump_counter(f"raid:{uid}:{day_id()}", 1, int(st["raid_daily_cap"])):
            continue
        paid_uids.add(uid)
        share = min(1.0, dmg / total * 3)  # even small contributors earn a fair cut
        xp = int((30 + 6 * lv) * mult * (0.5 + share / 2))
        coins = int((60 + 12 * lv) * mult * (0.5 + share / 2))
        await add_xp(uid, xp, "raid")
        await add_coins(uid, coins, "raid")
        paid += 1
    top = sorted(hits.items(), key=lambda kv: -kv[1])
    drop = None
    if top and (doc["kind"] != "hollow" or random.random() < 0.5):
        iid = await roll_drop(top[0][0], source_mult=1.5 if doc["kind"] != "hollow" else 1.0)
        if await inv_add(top[0][0], iid, 1):
            drop = (top[0][0], iid)
    extra = []  # everyone else who fought also gets a roll for an item (the top fighter keeps the special drop)
    for uid, _ in top:
        if drop and uid == drop[0]:
            continue
        if uid in paid_uids and random.random() < RAID_EXTRA_DROP_P:
            iid = await roll_drop(uid, source_mult=1.0)
            if await inv_add(uid, iid, 1):
                extra.append((uid, iid))
    names = doc.get("names") or {}
    return {"top": [(names.get(str(u), str(u)), d) for u, d in top[:3]], "paid": paid, "drop": drop, "extra": extra}

# --- NEW BLEACH VIRAL SYSTEM: Quincy invasion (Yhwach's army) -----------------------------------------------------------
# Every few hours the scheduler opens one per active group. Members type the strike word for the ttl; if the boss survives,
# the group's Bankai is locked for a while (collection quincy_locks, keyed by chat id).
async def quincy_tick():
    st = await game_settings()
    if not st["quincy_enabled"]:
        return []
    now = int(time.time())
    groups = await col("groups").find({"last_active": {"$gte": now - int(st["quincy_active_minutes"]) * 60}, "blocked": {"$ne": True},
                                       "drops_off": {"$ne": True}}).to_list(200)
    groups = [g for g in groups if not await col("quincy_raids").find_one({"chat_id": g["chat_id"], "status": "active"})]
    if not groups or await try_cooldown("quincy_spawn", int(st["quincy_interval_hours"]) * 3600):
        return []
    random.shuffle(groups)
    out = []
    for g in groups[: int(st["quincy_max_groups"])]:
        hp = int(st["quincy_hp"])
        doc = {"_id": uuid.uuid4().hex[:10], "chat_id": g["chat_id"], "kind": "quincy", "hp": hp, "max_hp": hp, "status": "active",
               "created_at": now, "end_at": now + int(st["quincy_ttl_minutes"]) * 60, "hits": {}, "names": {}, "lv": 0}
        await col("quincy_raids").insert_one(doc)
        out.append(doc)
    return out


async def quincy_attach(did: str, msg_id: int):
    await col("quincy_raids").update_one({"_id": did}, {"$set": {"msg_id": msg_id}})


async def quincy_abort(did: str):
    await col("quincy_raids").update_one({"_id": did}, {"$set": {"status": "aborted"}})


async def quincy_expire():
    """Raids whose time ran out with the boss alive: mark failed and lock Bankai in that group. Returns the failed docs."""
    st = await game_settings()
    now = int(time.time())
    out = []
    while True:
        d = await col("quincy_raids").find_one_and_update({"status": "active", "end_at": {"$lte": now}}, {"$set": {"status": "failed"}},
                                                          return_document=ReturnDocument.AFTER)
        if not d:
            return out
        await col("quincy_locks").update_one({"_id": d["chat_id"]}, {"$set": {"until": now + int(st["quincy_lock_minutes"]) * 60}}, upsert=True)
        out.append(d)


async def bankai_lock_left(chat_id: int) -> int:
    """Seconds this chat's Bankai stays stolen (0 = free)."""
    d = await col("quincy_locks").find_one({"_id": chat_id})
    return max(0, int(d["until"]) - int(time.time())) if d else 0


async def quincy_strike(chat_id: int, uid: int):
    """-> (result, doc, dmg). result: nodoc | noreg | level | cd | rage | hit | dead."""
    now = int(time.time())
    doc = await col("quincy_raids").find_one({"chat_id": chat_id, "status": "active", "end_at": {"$gt": now}})
    if not doc:
        return "nodoc", None, 0
    ch = await get_char(uid)
    if not ch:
        return "noreg", doc, 0
    st = await game_settings()
    if ch["level"] < int(st["raid_min_level"]):
        return "level", doc, 0
    if await try_cooldown(f"quincy:{chat_id}:{uid}", float(st["raid_strike_cd"])):
        return "cd", doc, 0
    sm = stance_mult(ch)
    if sm == 0.0:
        return "rage", doc, 0
    dmg = max(20, int(power(ch) * random.uniform(0.85, 1.15) * float(st["raid_dmg_k"]) * sm))
    after = await col("quincy_raids").find_one_and_update(
        {"_id": doc["_id"], "status": "active", "end_at": {"$gt": now}},
        {"$inc": {"hp": -dmg, f"hits.{uid}": dmg}, "$set": {f"names.{uid}": ch["name"]}, "$max": {"lv": int(ch["level"])}},
        return_document=ReturnDocument.AFTER)
    if not after:
        return "nodoc", None, 0
    if after["hp"] <= 0:
        killed = await col("quincy_raids").find_one_and_update({"_id": doc["_id"], "status": "active"}, {"$set": {"status": "dead", "dead_at": now}},
                                                               return_document=ReturnDocument.AFTER)
        if killed:
            return "dead", killed, dmg
    return "hit", after, dmg
