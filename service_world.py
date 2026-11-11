"""World bosses (shared HP per group), group settings and scheduler helpers."""
import random
import time
import uuid

from pymongo import ReturnDocument

from data_bosses import BOSSES, BOSS_BY_ID
from data_weapons import ELEMENTS
import engine as E
from database import col, game_settings, try_cooldown
from service_combat import build_player
from service_economy import inv_add, roll_drop
from service_player import add_coins, add_xp, bump_quest, coin_bonus, get_char


# ---- groups -------------------------------------------------------------------------
async def note_group(chat_id: int, title: str, level: int = None):
    now = int(time.time())
    upd = {"$set": {"title": (title or "")[:60], "last_active": now, "blocked": False},
           "$setOnInsert": {"chat_id": chat_id, "lang": "both"}}
    if level:
        upd["$push"] = {"levels": {"$each": [int(level)], "$slice": -20}}
    await col("groups").update_one({"chat_id": chat_id}, upd, upsert=True)


async def group_doc(chat_id: int) -> dict:
    return await col("groups").find_one({"chat_id": chat_id}) or {"chat_id": chat_id, "lang": "both"}


async def set_group_lang(chat_id: int, lang: str):
    await col("groups").update_one({"chat_id": chat_id}, {"$set": {"lang": lang}, "$setOnInsert": {"chat_id": chat_id}}, upsert=True)


def pick_boss(levels: list) -> dict:
    target = sorted(levels)[len(levels) // 2] if levels else 3
    return min(BOSSES, key=lambda b: abs(b["level"] - target))


# ---- boss lifecycle -----------------------------------------------------------------
async def active_boss(chat_id: int):
    return await col("boss_sessions").find_one({"chat_id": chat_id, "active": True})


async def spawn_boss(chat_id: int, boss_id: str = None):
    if await active_boss(chat_id):
        return None
    st = await game_settings()
    g = await group_doc(chat_id)
    b = BOSS_BY_ID.get(boss_id) if boss_id else pick_boss(g.get("levels", []))
    now = int(time.time())
    doc = {"_id": uuid.uuid4().hex[:10], "chat_id": chat_id, "boss_id": b["_id"], "name_fa": b["name_fa"], "name_en": b["name_en"],
           "level": b["level"], "hp": b["hp"], "max_hp": b["hp"], "trait": b["trait"], "active": True, "spawn_at": now,
           "expires_at": now + int(st["boss_duration_minutes"]) * 60, "contrib": {}, "hits": 0, "last_hitter": None,
           "edit_at": 0, "msg_id": None}
    await col("boss_sessions").insert_one(doc)
    return doc


def phase(doc: dict) -> int:
    f = doc["hp"] / doc["max_hp"]
    return 1 if f > 0.6 else 2 if f > 0.3 else 3


async def boss_hit(uid: int, sid: str):
    st = await game_settings()
    ch = await get_char(uid)
    if not ch:
        return "noreg", None
    if ch["level"] < int(st["boss_min_level"]):
        return "level", int(st["boss_min_level"])
    sess = await col("boss_sessions").find_one({"_id": sid, "active": True})
    if not sess or sess["expires_at"] <= time.time() or sess["hp"] <= 0:
        return "gone", None
    wait = await try_cooldown(f"bosshit:{uid}", int(st["boss_hit_cooldown"]))
    if wait:
        return "cool", wait
    b = BOSS_BY_ID[sess["boss_id"]]
    rng = random.Random()
    trait = sess.get("trait")
    if trait == "dodge" and sess["hits"] % 5 in (1, 3):
        return "evade", 0
    if trait == "illusion" and rng.random() < 0.30:
        return "evade", 0
    player = await build_player(ch)
    boss = E.new_fighter("Boss", b["level"], {"zanjutsu": 1, "kido": 1, "hakuda": b["defense"] * 2, "hoho": 1, "reiatsu": 1}, 10 ** 9, 100,
                         {"attack": 1, "element": ELEMENTS[sum(map(ord, b["_id"])) % 8], "skills": [], "weapon_type": "melee"}, armor=0)
    state = {"a": player, "b": boss, "turn": 1, "cur": "a", "first": "a", "done": False, "winner": None}
    ev = []
    E._deal(state, "a", 1.0, rng, ev, "atk")
    dmg = sum(e.get("n", 0) for e in ev if e["k"] == "hit")
    crit = any(e.get("c") for e in ev if e["k"] == "hit")
    if dmg <= 0:
        return "miss", 0
    doc = await col("boss_sessions").find_one_and_update(
        {"_id": sid, "active": True, "hp": {"$gt": 0}},
        {"$inc": {"hp": -dmg, f"contrib.{uid}": dmg, "hits": 1}, "$set": {"last_hitter": uid}}, return_document=ReturnDocument.AFTER)
    if not doc:
        return "gone", None
    await bump_quest(uid, "boss_hit", 1)
    return "hit", {"dmg": dmg, "crit": crit, "doc": doc}


async def settle_boss(sid: str):
    """Pay out a killed boss exactly once. Returns summary or None."""
    doc = await col("boss_sessions").find_one_and_update(
        {"_id": sid, "active": True, "hp": {"$lte": 0}}, {"$set": {"active": False, "killed": True, "ended_at": int(time.time())}},
        return_document=ReturnDocument.AFTER)
    if not doc:
        return None
    return await _pay(doc, killed=True)


async def expire_bosses():
    out = []
    now = int(time.time())
    while True:
        doc = await col("boss_sessions").find_one_and_update(
            {"active": True, "expires_at": {"$lte": now}}, {"$set": {"active": False, "escaped": True, "ended_at": now}},
            return_document=ReturnDocument.AFTER)
        if not doc:
            break
        out.append((doc, await _pay(doc, killed=False)))
    return out


async def _pay(doc: dict, killed: bool):
    st = await game_settings()
    lvl = doc["level"]
    xp_pool = int(300 * lvl ** 1.3 + 500) * (1.0 if killed else 0.3)
    coin_pool = int((120 * lvl ** 1.2 + 300) * float(st["coin_rate"])) * (1.0 if killed else 0.3)
    enraged = doc["hp"] <= 0 and doc["max_hp"] > 0 and killed
    if enraged:
        xp_pool *= 1.3
    contrib = {int(k): v for k, v in doc.get("contrib", {}).items()}
    total = sum(contrib.values()) or 1
    rows, drops = [], {}
    for uid, dmg in sorted(contrib.items(), key=lambda x: -x[1]):
        share = dmg / total
        main = dmg >= 0.01 * doc["max_hp"]
        xp = xp_pool * share if main else xp_pool * 0.01
        coins = coin_pool * share if main else 0
        last = killed and uid == doc.get("last_hitter")
        if last:
            xp += xp_pool * 0.10
            coins += coin_pool * 0.10
        await add_xp(uid, int(xp), "boss", apply_rate=True)
        if coins:
            await add_coins(uid, await coin_bonus(uid, int(coins)), "boss")
        if killed and (last or (main and share >= 0.10)):
            iid = await roll_drop(uid, source_mult=2.0, weapon_chance=0.2)
            if await inv_add(uid, iid, 1):
                drops[uid] = iid
        if killed:
            await bump_quest(uid, "boss_kill", 1)
        names = await col("characters").find_one({"user_id": uid}, {"name": 1})
        rows.append({"uid": uid, "name": (names or {}).get("name", "?"), "dmg": dmg, "share": share, "xp": int(xp), "last": last})
    return {"rows": rows, "drops": drops, "killed": killed, "enraged": enraged}


# ---- scheduler helpers ----------------------------------------------------------------
async def due_groups():
    st = await game_settings()
    now = int(time.time())
    out = []
    async for g in col("groups").find({"blocked": {"$ne": True}, "last_active": {"$gte": now - 86400}}).limit(500):
        nxt = g.get("next_boss_at")
        if nxt is None:
            gap = random.randint(int(st["boss_min_minutes"]), int(st["boss_max_minutes"])) * 60
            await col("groups").update_one({"chat_id": g["chat_id"], "next_boss_at": {"$exists": False}}, {"$set": {"next_boss_at": now + gap}})
            continue
        if nxt <= now:
            out.append(g)
    return out


async def schedule_next(chat_id: int):
    st = await game_settings()
    gap = random.randint(int(st["boss_min_minutes"]), int(st["boss_max_minutes"])) * 60
    await col("groups").update_one({"chat_id": chat_id}, {"$set": {"next_boss_at": int(time.time()) + gap}})
