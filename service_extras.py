"""Six retention loops: Soul Tower, win chain, Dispatch, Urahara's wheel, Gotei seat ranks, Inner World.
All writes are atomic (`bump_counter`, conditional `find_one_and_update`); every limit is a live `set` key."""
import random
import time
import uuid
from datetime import datetime, timedelta, timezone

from pymongo.errors import DuplicateKeyError

from data_chars import CHAR_BY_ID
from data_extras import INNER, MISSIONS, RARITY_MULT, SEATS, TOWER_BOSS_EVERY, WHEEL, seat_index
from data_items import ALL
from data_weapons import RARITIES
from database import bump_counter, col, counter_get, game_settings, try_cooldown
from data_world import day_id
from service_economy import gacha_doc, inv_add, roll_drop
from service_player import add_coins, add_xp, energy_now, get_char, week

# ---- item pools by category ---------------------------------------------------------------------------
BY_CAT = {}
for _id, _it in ALL.items():
    if _it.get("category") != "weapon":
        BY_CAT.setdefault(_it["category"], {}).setdefault(_it["rarity"], []).append(_id)


def pick_item(cat: str, rarity_idxs, rng=random):
    """Random item of a category; falls back to neighbouring rarities when a tier is empty."""
    want = rng.choice(rarity_idxs)
    for i in sorted(range(len(RARITIES)), key=lambda k: abs(k - want)):
        pool = BY_CAT.get(cat, {}).get(RARITIES[i])
        if pool:
            return rng.choice(pool)
    return None


async def add_energy(uid: int, n: int) -> int:
    st = await game_settings()
    mx = int(st["energy_max"])
    for _ in range(4):
        ch = await get_char(uid)
        cur, _nxt, new_ts = energy_now(ch, st)
        newv = min(mx, cur + int(n))
        ts = int(time.time()) if newv >= mx else new_ts
        r = await col("characters").update_one({"user_id": uid, "energy": ch.get("energy"), "energy_ts": ch.get("energy_ts")},
                                               {"$set": {"energy": newv, "energy_ts": ts}})
        if r.modified_count:
            return newv - cur
    return 0


# ===================================================================================================
# 1. Soul Tower
# ===================================================================================================
def tower_checkpoint(best: int) -> int:
    """Runs restart at the first floor of the 5-floor block the player reached."""
    return 1 if best <= 1 else ((best - 1) // TOWER_BOSS_EVERY) * TOWER_BOSS_EVERY + 1


async def tower_info(uid: int) -> dict:
    ch = await get_char(uid)
    t = ch.get("tower") or {}
    st = await game_settings()
    wk = t.get("wk_best", 0) if t.get("wk") == week() else 0
    left = max(0, int(st["tower_daily_floors"]) - await counter_get(f"tower:{uid}:{day_id()}"))
    best = int(t.get("best", 0))
    return {"best": best, "wk": wk, "start": tower_checkpoint(best), "left": left, "cap": int(st["tower_daily_floors"]),
            "cost": int(st["tower_energy"])}


async def tower_start(uid: int, lang: str):
    from service_combat import active_pve, pve_start
    from service_player import spend_energy
    st = await game_settings()
    if await active_pve(uid):
        return "busy", None
    if await try_cooldown(f"tower:go:{uid}", 3):
        return "wait", None
    ok, _cur, _nxt = await spend_energy(uid, int(st["tower_energy"]))
    if not ok:
        return "energy", None
    info = await tower_info(uid)
    doc = await pve_start(uid, lang, dungeon={"id": "tower", "tower": True, "stage": info["start"], "total": 0, "diff": "normal"})
    return "ok", doc


async def tower_settle(doc: dict, win: bool) -> dict:
    """Called by service_combat.pve_settle for tower fights."""
    from service_combat import _rewards, pve_start
    uid, d, state = doc["user_id"], doc["dungeon"], doc["state"]
    floor = int(d["stage"])
    gs = await game_settings()
    out = {"win": win, "xp": 0, "coins": 0, "drop": None, "levels": 0, "next": None, "dungeon_done": False,
           "tower": {"floor": floor, "paid": False, "record": False, "milestone": 0, "best": 0}}
    ch = await get_char(uid)
    t = dict(ch.get("tower") or {})
    wk = week()
    if not win:
        await col("characters").update_one({"user_id": uid}, {"$inc": {"losses": 1, "tower.runs": 1}})
        out["tower"]["best"] = int(t.get("best", 0))
        return out
    if await bump_counter(f"tower:{uid}:{day_id()}", 1, int(gs["tower_daily_floors"])):
        xp, coins = _rewards(doc["lvl"], 1.0, gs)
        k = min(2.0, 1 + 0.02 * floor)
        xp, coins = int(xp * k), int(coins * k)
        _ch, lv, got = await add_xp(uid, xp, "tower")
        await add_coins(uid, coins, "tower")
        out.update(xp=got, coins=coins, levels=lv)
        out["tower"]["paid"] = True
        if random.random() < 0.30:
            iid = await roll_drop(uid, floor_idx=min(3, floor // 25))
            if await inv_add(uid, iid, 1):
                out["drop"] = iid
    best = int(t.get("best", 0))
    wk_best = int(t.get("wk_best", 0)) if t.get("wk") == wk else 0
    upd = {"tower.wk": wk, "tower.wk_best": max(wk_best, floor), "tower.best": max(best, floor)}
    if floor > best:
        out["tower"]["record"] = True
        if floor % TOWER_BOSS_EVERY == 0:  # milestone: a guaranteed item + coins, once per floor ever
            bonus = 200 * floor
            await add_coins(uid, bonus, "tower_milestone")
            iid = await roll_drop(uid, source_mult=1.5, floor_idx=min(4, 1 + floor // 20))
            await inv_add(uid, iid, 1, force=True)
            out["tower"]["milestone"] = bonus
            out["tower"]["milestone_item"] = iid
    out["tower"]["best"] = max(best, floor)
    await col("characters").update_one({"user_id": uid}, {"$set": upd, "$inc": {"wins": 1}})
    f = state["a"]
    heal = float(gs["tower_heal"])
    nxt = await pve_start(uid, doc.get("lang", "en"), dungeon={**d, "stage": floor + 1},
                          carry={"hp": min(1.0, f["hp"] / f["max_hp"] + heal), "re": min(1.0, f["re"] / f["max_re"] + heal)})
    out["next"] = nxt["sid"]
    return out


async def tower_board(limit: int = 10):
    cur = col("characters").find({"tower.wk": week(), "tower.wk_best": {"$gt": 0}}, {"name": 1, "tower": 1, "cosmetics": 1, "seat": 1})
    return await cur.sort([("tower.wk_best", -1)]).limit(limit).to_list(limit)


# ===================================================================================================
# 2. Win chain (plain PvE fights only)
# ===================================================================================================
async def chain_win(uid: int):
    """Returns (n, multiplier, bonus_item_id|None)."""
    st = await game_settings()
    ch = await get_char(uid)
    c = ch.get("chain") or {}
    now = int(time.time())
    n = int(c.get("n", 0)) if now - int(c.get("at", 0)) < float(st["chain_expire_hours"]) * 3600 else 0
    n += 1
    await col("characters").update_one({"user_id": uid}, {"$set": {"chain.n": n, "chain.at": now, "chain.best": max(n, int(c.get("best", 0)))}})
    mult = 1 + min(n - 1, int(st["chain_cap"])) * float(st["chain_step"])
    item = None
    every = int(st["chain_bonus_every"])
    if every > 0 and n % every == 0:
        item = await roll_drop(uid, source_mult=1.3, floor_idx=1)
        if not await inv_add(uid, item, 1):
            item = None
    return n, mult, item


async def chain_break(uid: int) -> int:
    ch = await get_char(uid)
    n = int((ch.get("chain") or {}).get("n", 0))
    if n:
        await col("characters").update_one({"user_id": uid}, {"$set": {"chain.n": 0}})
    return n


# ===================================================================================================
# 3. Dispatch
# ===================================================================================================
async def dispatch_active(uid: int) -> list:
    return await col("dispatches").find({"user_id": uid, "active": True}).sort("end", 1).to_list(20)


async def dispatch_send(uid: int, mid: str, cid: str):
    st = await game_settings()
    m = MISSIONS.get(mid)
    ch = await get_char(uid)
    if not m or cid not in CHAR_BY_ID:
        return "bad"
    if ch["level"] < m["level"]:
        return "level"
    if cid not in (await gacha_doc(uid))["chars"]:
        return "notowned"
    now = int(time.time())
    doc = {"_id": uuid.uuid4().hex[:12], "user_id": uid, "cid": cid, "mission": mid, "start": now,
           "end": now + int(m["hours"] * 3600 * float(st["dispatch_time_k"])), "active": True}
    try:
        await col("dispatches").insert_one(doc)
    except DuplicateKeyError:
        return "busy"
    if await col("dispatches").count_documents({"user_id": uid, "active": True}) > int(st["dispatch_slots"]):
        await col("dispatches").delete_one({"_id": doc["_id"]})
        return "slots"
    return "ok"


async def dispatch_claim(uid: int):
    """Pay every finished dispatch. Returns a list of result dicts."""
    st = await game_settings()
    now = int(time.time())
    out = []
    for d in await col("dispatches").find({"user_id": uid, "active": True, "end": {"$lte": now}}).to_list(20):
        hit = await col("dispatches").find_one_and_update({"_id": d["_id"], "active": True}, {"$set": {"active": False, "claimed_at": now, "expire_at": datetime.now(timezone.utc) + timedelta(days=7)}})
        if not hit:
            continue
        ch = await get_char(uid)
        c, m = CHAR_BY_ID[d["cid"]], MISSIONS[d["mission"]]
        lvl, hours = ch["level"], m["hours"]
        k = float(st["dispatch_k"]) * RARITY_MULT[c["rarity"]] * m["k"] * hours
        coins = (12 + lvl * 2) * k * float(st["coin_rate"])
        xp = (10 + lvl * 1.5) * k
        role = c["role"]
        res = {"cid": d["cid"], "role": role, "item": None, "energy": 0}
        if role == "attacker":
            coins *= 1.25
        elif role == "caster":
            xp *= 1.25
        elif role == "tank":
            iid = pick_item("material", [min(3, RARITIES.index(c["rarity"])), min(3, RARITIES.index(c["rarity"]))])
            if iid and await inv_add(uid, iid, 1, force=True):
                res["item"] = iid
        elif role == "support":
            res["energy"] = await add_energy(uid, int(st["dispatch_energy"]))
        if res["item"] is None and random.random() < 0.20:
            iid = await roll_drop(uid)
            if await inv_add(uid, iid, 1):
                res["item"] = iid
        res["coins"], res["xp"] = int(coins), int(xp)
        await add_coins(uid, res["coins"], "dispatch")
        await add_xp(uid, res["xp"], "dispatch")
        out.append(res)
    return out


# ===================================================================================================
# 4. Urahara's wheel
# ===================================================================================================
async def wheel_state(uid: int) -> dict:
    st = await game_settings()
    day = day_id()
    free_left = 1 - await counter_get(f"wheel:{uid}:{day}")
    extra_left = int(st["wheel_extra_daily"]) - await counter_get(f"wheelx:{uid}:{day}")
    return {"free": max(0, free_left), "extra": max(0, extra_left), "cost": int(st["wheel_cost"])}


async def wheel_spin(uid: int):
    st = await game_settings()
    day = day_id()
    if await try_cooldown(f"wheel:cd:{uid}", 2):
        return "wait", None
    free = await bump_counter(f"wheel:{uid}:{day}", 1, 1)
    if not free:
        cap = int(st["wheel_extra_daily"])
        if cap <= 0:
            return "used", None
        if not await bump_counter(f"wheelx:{uid}:{day}", 1, cap):
            return "limit", None
        if not await add_coins(uid, -int(st["wheel_cost"]), "wheel"):
            await col("counters").update_one({"key": f"wheelx:{uid}:{day}"}, {"$inc": {"n": -1}})
            return "funds", None
    ch = await get_char(uid)
    lvl = ch["level"]
    pid, _w, icon, fa, en = random.choices(WHEEL, [w[1] for w in WHEEL])[0]
    res = {"id": pid, "icon": icon, "fa": fa, "en": en, "free": bool(free), "coins": 0, "xp": 0, "item": None, "energy": 0}
    cr = float(st["coin_rate"])
    if pid == "coins_s":
        res["coins"] = int((60 + lvl * 8) * cr)
    elif pid == "coins_l":
        res["coins"] = int((300 + lvl * 30) * cr)
    elif pid == "jackpot":
        res["coins"] = int((5000 + lvl * 150) * cr)
        res["item"] = pick_item("relic", [4])
    elif pid == "xp":
        res["xp"] = 60 + lvl * 12
    elif pid == "energy":
        res["energy"] = await add_energy(uid, 9999)
    elif pid == "potion":
        res["item"] = pick_item("potion", [0, 1, 1, 2])
    elif pid == "material":
        res["item"] = pick_item("material", [1, 2, 2, 3])
    elif pid == "egg":
        res["item"] = pick_item("egg", [1, 1, 2, 3])
    elif pid == "book":
        res["item"] = pick_item("book", [0, 1, 1, 2])
    elif pid == "relic":
        res["item"] = pick_item("relic", [1, 2, 2, 3])
    elif pid == "key":
        keys = [i for i, x in ALL.items() if (x.get("effect") or {}).get("type") == "key" and x["effect"]["diff"] in ("normal", "hard")]
        res["item"] = random.choice(keys)
    if res["coins"]:
        await add_coins(uid, res["coins"], "wheel")
    if res["xp"]:
        await add_xp(uid, res["xp"], "wheel")
    if res["item"]:
        await inv_add(uid, res["item"], 1, force=True)
    return "ok", res


# ===================================================================================================
# 5. Gotei seat ranks
# ===================================================================================================
async def seat_info(uid: int) -> dict:
    from service_worldcore import get_world
    ws, _ = await get_world()
    doc = await col("season_scores").find_one({"_id": f"{ws['season']['id']}:{uid}"}) or {}
    pts = int(doc.get("pts", 0))
    idx = seat_index(pts)
    ch = await get_char(uid)
    if int(ch.get("seat", 0) or 0) != idx:
        await col("characters").update_one({"user_id": uid}, {"$set": {"seat": idx}})
    nxt = SEATS[idx + 1] if idx + 1 < len(SEATS) else None
    return {"pts": pts, "idx": idx, "next": nxt, "claimed": int(ch.get("seat_claimed", 0) or 0)}


async def seat_claim(uid: int):
    info = await seat_info(uid)
    idx = info["idx"]
    prev = await col("characters").find_one_and_update(
        {"user_id": uid, "$or": [{"seat_claimed": {"$lt": idx}}, {"seat_claimed": {"$exists": False}}]},
        {"$set": {"seat_claimed": idx}})
    if not prev:
        return None
    start = int(prev.get("seat_claimed", 0) or 0)
    if idx <= start:
        return None
    coins, items = 0, []
    for i in range(start + 1, idx + 1):
        coins += 800 * i
        iid = await roll_drop(uid, source_mult=1.2, floor_idx=min(4, i - 1))
        await inv_add(uid, iid, 1, force=True)
        items.append(iid)
    await add_coins(uid, coins, "seat")
    return {"coins": coins, "items": items, "idx": idx}


# ===================================================================================================
# 6. Inner World (weekly, a few visits)
# ===================================================================================================
def _scene_for(uid: int, wk: str, n: int) -> int:
    return random.Random(f"{uid}:{wk}:{n}").randrange(len(INNER))


async def inner_state(uid: int) -> dict:
    st = await game_settings()
    wk = week()
    used = await counter_get(f"inner:{uid}:{wk}")
    cap = int(st["inner_weekly"])
    return {"used": used, "cap": cap, "left": max(0, cap - used), "scene": _scene_for(uid, wk, used) if used < cap else None}


async def inner_choose(uid: int, scene: int, choice: str):
    st = await game_settings()
    wk = week()
    if choice not in ("a", "b"):
        return "bad", None
    if await try_cooldown(f"inner:cd:{uid}", 3):
        return "wait", None
    used = await counter_get(f"inner:{uid}:{wk}")
    if used >= int(st["inner_weekly"]):
        return "limit", None
    if scene != _scene_for(uid, wk, used):
        return "stale", None
    if not await bump_counter(f"inner:{uid}:{wk}", 1, int(st["inner_weekly"]), ttl_hours=24 * 9):
        return "limit", None
    eff = INNER[scene][choice][4]
    ch = await get_char(uid)
    wid = ch.get("weapon_id") or "none"
    res = {"bond": int(eff.get("bond", 0)), "xp": 0, "buff": None}
    if res["bond"]:
        await col("characters").update_one({"user_id": uid}, {"$inc": {f"bond.{wid}": res["bond"]}})
    if eff.get("xp"):
        res["xp"] = int((40 + ch["level"] * 6) * eff["xp"])
        await add_xp(uid, res["xp"], "inner")
    if eff.get("buff"):
        key, pct, minutes = eff["buff"]
        cur = (ch.get("buffs") or {}).get(key) or {}
        if cur.get("until", 0) <= time.time() or cur.get("pct", 0) <= pct:
            await col("characters").update_one({"user_id": uid}, {"$set": {f"buffs.{key}": {"pct": pct, "until": int(time.time()) + minutes * 60}}})
            res["buff"] = (key, pct, minutes)
    return "ok", res
