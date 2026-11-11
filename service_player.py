"""Users, registration state machine, characters, XP, energy, coins, quests."""
import math
import random
import time
import uuid
from datetime import datetime, timezone

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from data_crafting import player_bonus
from data_items import ALL
from data_misc import DAILY_POOL, QUEST_BY_ID, QUESTS, RACE_START_KIDO, START_KIDO
from data_races import RACES, STATS, soft_stat
from data_weapons import WEAPONS
from database import col, game_settings
from service_log import log_event
from service_worldcore import mods_for

_lang_cache: dict = {}


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def week() -> str:
    y, w, _ = datetime.now(timezone.utc).isocalendar()
    return f"{y}-W{w}"


def xp_to_next(level: int) -> int:
    return math.floor(100 * level ** 1.7 + 50 * level + 25 * math.sqrt(level))


def max_hp(level: int, hakuda: float, mult: float = 1.0) -> int:
    return int((100 + level * 20 + hakuda * 8) * mult)


def max_reiatsu(level: int, reiatsu: float) -> int:
    return int(50 + level * 15 + reiatsu * 12)


# ---- users -------------------------------------------------------------------
async def get_user(uid: int):
    return await col("users").find_one({"telegram_id": uid})


async def touch_user(tg_user, ref=None):
    now = int(time.time())
    res = await col("users").update_one(
        {"telegram_id": tg_user.id},
        {"$setOnInsert": {"telegram_id": tg_user.id, "created_at": now, "referred_by": ref},
         "$set": {"username": tg_user.username, "first_name": (tg_user.first_name or "")[:40], "last_seen": now}},
        upsert=True)
    return res.upserted_id is not None


async def user_lang(uid: int):
    hit = _lang_cache.get(uid)
    if hit and time.monotonic() - hit[1] < 60:
        return hit[0]
    u = await get_user(uid)
    lang = (u or {}).get("lang")
    if lang:
        _lang_cache[uid] = (lang, time.monotonic())
    return lang


async def set_lang(uid: int, lang: str):
    await col("users").update_one({"telegram_id": uid}, {"$set": {"lang": lang}})
    _lang_cache[uid] = (lang, time.monotonic())


# ---- registration (state lives in MongoDB, survives restarts) -----------------
async def reg_get(uid: int):
    return await col("registration").find_one({"user_id": uid})


async def reg_set(uid: int, **vals):
    vals["updated_at"] = int(time.time())
    await col("registration").update_one({"user_id": uid}, {"$set": vals, "$setOnInsert": {"user_id": uid}}, upsert=True)
    return await reg_get(uid)


async def reg_clear(uid: int):
    await col("registration").delete_one({"user_id": uid})


def starter_choices(race: str, rng=random):
    pool = [w for w in WEAPONS if w["rarity"] in ("Common", "Uncommon")]
    return [w["_id"] for w in rng.sample(pool, 3)]


async def finish_registration(uid: int, reg: dict):
    """Create the character atomically enough: unique indexes guard duplicates."""
    st = await game_settings()
    race = RACES[reg["race"]]
    stats = dict(race["stats"])
    for k, v in (reg.get("stats") or {}).items():
        if k in stats:
            stats[k] += int(v)
    name = reg["name"]
    lvl = 1
    kido = {"had": list(RACE_START_KIDO.get(reg["race"], START_KIDO)["had"]), "bak": list(RACE_START_KIDO.get(reg["race"], START_KIDO)["bak"])}
    doc = {"uuid": str(uuid.uuid4()), "user_id": uid, "name": name, "name_key": name.casefold(), "gender": reg["gender"],
           "race": reg["race"], "level": lvl, "xp": 0, "coins": int(st["start_coins"]), "points": 0, "stats": stats,
           "location": race["home"], "weapon_id": reg["weapon"], "armor_id": None, "acc_id": None, "charm_id": None,
           "energy": int(st["energy_max"]), "energy_ts": int(time.time()), "kido": kido, "rating": 1000,
           "wins": 0, "losses": 0, "pvp_w": 0, "pvp_l": 0, "pity": {"rare": 0, "epic": 0, "legendary": 0},
           "pets": [], "party": [], "guild_id": None, "created_at": int(time.time()), "daily_streak": 0, "last_daily": None,
           "evo": 0, "relics": [], "cosmetics": {}, "armor_plus": {}, "buffs": {}, "seen_at": int(time.time())}
    try:
        await col("characters").insert_one(doc)
    except DuplicateKeyError:
        return None
    await col("inventories").update_one({"user_id": uid}, {"$setOnInsert": {"user_id": uid, "items": {}, "capacity": 50}}, upsert=True)
    await col("player_quests").update_one({"user_id": uid}, {"$setOnInsert": {"user_id": uid, "total": {}, "daily": {"day": today(), "c": {}}, "weekly": {"week": week(), "c": {}}, "claimed": []}}, upsert=True)
    await reg_clear(uid)
    log_event("reg", uid, f"ثبت‌نام کرد: {name} — نژاد {race['name_fa']}", race=reg["race"])
    return doc


async def name_taken(name: str) -> bool:
    return bool(await col("characters").find_one({"name_key": name.casefold()}, {"_id": 1}))


# ---- characters --------------------------------------------------------------
async def get_char(uid: int):
    return await col("characters").find_one({"user_id": uid})


def power(ch: dict) -> int:
    s = sum(soft_stat(ch["stats"][k]) for k in STATS)
    w = ALL.get(ch.get("weapon_id") or "", {}).get("attack", 0)
    a = ALL.get(ch.get("armor_id") or "", {}).get("stats", {}).get("def", 0)
    return int(s * 3 + w * 2 + a + ch["level"] * 10)


async def add_coins(uid: int, n: int, reason: str = "") -> bool:
    n = int(n)
    if n == 0:
        return True
    q = {"user_id": uid}
    if n < 0:
        q["coins"] = {"$gte": -n}
    r = await col("characters").update_one(q, {"$inc": {"coins": n}})
    if r.modified_count:
        await col("transactions").insert_one({"tx_key": uuid.uuid4().hex, "user_id": uid, "coins": n, "reason": reason, "at": int(time.time())})
    return bool(r.modified_count)


async def add_xp(uid: int, amount: int, source: str = "", apply_rate: bool = True):
    """Optimistic-concurrency XP grant. Returns (character, levels_gained, xp_given)."""
    st = await game_settings()
    for _ in range(6):
        ch = await get_char(uid)
        if not ch:
            return None, 0, 0
        gain = float(amount)
        if apply_rate:
            gain *= float(st["xp_rate"]) * RACES[ch["race"]]["mods"].get("xp", 1.0)
            gain *= 1 + player_bonus(ch, ALL, st)["xp"]
            try:
                gain *= (await mods_for(ch["location"]))["xp"]
            except Exception:
                pass
        gain = max(0, int(gain))
        level, xp, pts, gained = ch["level"], ch["xp"] + gain, ch.get("points", 0), 0
        while xp >= xp_to_next(level) and gained < 200:
            xp -= xp_to_next(level)
            level += 1
            gained += 1
            pts += 3 + (1 if level % 5 == 0 else 0)
        upd = {"xp": xp, "level": level, "points": pts}
        r = await col("characters").update_one({"user_id": uid, "level": ch["level"], "xp": ch["xp"]}, {"$set": upd})
        if r.modified_count:
            ch.update(upd)
            if gained:
                await bump_quest(uid, "level", 0, absolute=level)
                log_event("lvl", uid, f"به سطح {level} رسید (+{gained})", level=level)
            return ch, gained, gain
    return await get_char(uid), 0, 0


def energy_now(ch: dict, st: dict):
    mx, per = int(st["energy_max"]), int(st["energy_regen_seconds"])
    cur = int(ch.get("energy", mx))
    ts = int(ch.get("energy_ts", time.time()))
    if cur >= mx:
        return mx, 0, ts
    gained = max(0, (int(time.time()) - ts) // per)
    cur2 = min(mx, cur + gained)
    nxt = 0 if cur2 >= mx else per - ((int(time.time()) - ts) % per)
    return cur2, nxt, ts + gained * per


async def spend_energy(uid: int, cost: int):
    st = await game_settings()
    for _ in range(4):
        ch = await get_char(uid)
        cur, nxt, new_ts = energy_now(ch, st)
        if cur < cost:
            return False, cur, nxt
        mx = int(st["energy_max"])
        ts = int(time.time()) if cur >= mx else new_ts
        r = await col("characters").update_one({"user_id": uid, "energy": ch.get("energy"), "energy_ts": ch.get("energy_ts")},
                                               {"$set": {"energy": cur - cost, "energy_ts": ts}})
        if r.modified_count:
            return True, cur - cost, 0
    return False, 0, 0


# ---- daily reward --------------------------------------------------------------
async def claim_daily(uid: int):
    day = today()
    try:
        await col("daily_claims").insert_one({"user_id": uid, "day": day, "at": int(time.time())})
    except DuplicateKeyError:
        return None
    ch = await get_char(uid)
    yday = datetime.fromtimestamp(time.time() - 86400, timezone.utc).strftime("%Y-%m-%d")
    streak = ch.get("daily_streak", 0) + 1 if ch.get("last_daily") == yday else 1
    st = await game_settings()
    coins = int((100 + min(streak, 14) * 25 + ch["level"] * 5) * float(st["coin_rate"]))
    await col("characters").update_one({"user_id": uid}, {"$set": {"daily_streak": streak, "last_daily": day}})
    await add_coins(uid, coins, "daily")
    await bump_quest(uid, "daily_claim", 1)
    return {"coins": coins, "streak": streak}


# ---- quests ------------------------------------------------------------------
def _daily_ids(day: str):
    r = random.Random(day)
    return r.sample(DAILY_POOL, min(3, len(DAILY_POOL)))


async def _quest_doc(uid: int):
    q = await col("player_quests").find_one({"user_id": uid})
    if not q:
        await col("player_quests").update_one({"user_id": uid}, {"$setOnInsert": {"user_id": uid, "total": {}, "daily": {"day": today(), "c": {}}, "weekly": {"week": week(), "c": {}}, "claimed": []}}, upsert=True)
        q = await col("player_quests").find_one({"user_id": uid})
    upd = {}
    if q["daily"]["day"] != today():
        upd["daily"] = {"day": today(), "c": {}}
        upd["claimed"] = [c for c in q.get("claimed", []) if QUEST_BY_ID.get(c, {}).get("cat") not in ("daily",)]
    if q["weekly"]["week"] != week():
        upd["weekly"] = {"week": week(), "c": {}}
        base = upd.get("claimed", q.get("claimed", []))
        upd["claimed"] = [c for c in base if QUEST_BY_ID.get(c, {}).get("cat") != "weekly"]
    if upd:
        await col("player_quests").update_one({"user_id": uid}, {"$set": upd})
        q.update(upd)
    return q


async def bump_quest(uid: int, goal: str, n: int = 1, absolute: int = None):
    q = await _quest_doc(uid)
    if absolute is not None:
        await col("player_quests").update_one({"user_id": uid}, {"$max": {f"total.{goal}": int(absolute)}})
        return
    await col("player_quests").update_one({"user_id": uid}, {"$inc": {f"total.{goal}": n, f"daily.c.{goal}": n, f"weekly.c.{goal}": n}})


async def quest_list(uid: int, level: int):
    q = await _quest_doc(uid)
    out = []
    daily = set(_daily_ids(today()))
    for d in QUESTS:
        if d["min_level"] > level and d["cat"] not in ("main",):
            continue
        if d["cat"] == "daily" and d["_id"] not in daily:
            continue
        src = q["daily"]["c"] if d["cat"] == "daily" else q["weekly"]["c"] if d["cat"] == "weekly" else q["total"]
        prog = src.get(d["goal"], 0)
        if d["goal"] == "level":
            prog = level
        out.append({"q": d, "prog": min(prog, d["count"]), "done": prog >= d["count"], "claimed": d["_id"] in q.get("claimed", [])})
    return out


async def claim_quest(uid: int, qid: str):
    d = QUEST_BY_ID.get(qid)
    ch = await get_char(uid)
    if not d or not ch:
        return None
    states = {s["q"]["_id"]: s for s in await quest_list(uid, ch["level"])}
    s = states.get(qid)
    if not s or not s["done"] or s["claimed"]:
        return None
    r = await col("player_quests").update_one({"user_id": uid, "claimed": {"$ne": qid}}, {"$addToSet": {"claimed": qid}})
    if not r.modified_count:
        return None
    await add_coins(uid, d["coins"], "quest")
    await add_xp(uid, d["xp"], "quest", apply_rate=False)
    return d
