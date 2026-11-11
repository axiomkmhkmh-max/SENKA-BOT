"""Player-to-player effects: location crowd, traces and graves, spirit aid, bounties.
All limits are live settings; every shared write is atomic."""
import random
import time
import uuid
from datetime import datetime, timedelta, timezone

from data_world import day_id
from database import bump_counter, col, counter_get, game_settings, try_cooldown
from service_log import log_event
from service_player import add_coins, add_xp, energy_now, get_char
from service_worldcore import chronicle, is_new_account, season_add

MARKS = ("candle", "flower", "blade")
MARK_ICON = {"candle": "🕯️", "flower": "🌸", "blade": "🗡️", "grave": "🪦"}
FIND_MAX = 5


# ---- crowd -----------------------------------------------------------------------------------------------------
async def crowd(loc: str, me: int = None, limit: int = 6):
    """(total players seen here recently, up to `limit` others)."""
    st = await game_settings()
    since = int(time.time()) - int(st["presence_minutes"]) * 60
    q = {"location": loc, "seen_at": {"$gte": since}}
    total = await col("characters").count_documents(q)
    rows = await col("characters").find({**q, "user_id": {"$ne": me}}, {"user_id": 1, "name": 1, "level": 1, "cosmetics": 1}).sort("seen_at", -1).limit(limit).to_list(limit)
    return total, rows


async def crowd_counts() -> dict:
    st = await game_settings()
    since = int(time.time()) - int(st["presence_minutes"]) * 60
    rows = await col("characters").aggregate([{"$match": {"seen_at": {"$gte": since}}}, {"$group": {"_id": "$location", "n": {"$sum": 1}}}]).to_list(50)
    return {r["_id"]: r["n"] for r in rows}


# ---- traces & graves -------------------------------------------------------------------------------------------------
async def leave_trace(uid: int, mark: str):
    st = await game_settings()
    ch = await get_char(uid)
    if mark not in MARKS:
        return "bad", None
    if ch["level"] < int(st["aid_min_level"]) or is_new_account(ch, st):
        return "young", None
    active = await col("traces").count_documents({"uid": uid, "active": True, "kind": "mark", "expire_at": {"$gt": datetime.now(timezone.utc)}})
    if active >= int(st["trace_max_active"]):
        return "max", int(st["trace_max_active"])
    wait = await try_cooldown(f"trace:{uid}", int(st["trace_cooldown"]))
    if wait:
        return "wait", wait
    cost = int(st["trace_cost"])
    if cost and not await add_coins(uid, -cost, "trace"):
        await col("cooldowns").delete_one({"key": f"trace:{uid}"})
        return "funds", cost
    await col("traces").insert_one({"_id": uuid.uuid4().hex[:10], "uid": uid, "name": ch["name"], "loc": ch["location"], "mark": mark, "kind": "mark",
                                    "active": True, "found_n": 0, "found_by": [], "at": int(time.time()),
                                    "expire_at": datetime.now(timezone.utc) + timedelta(hours=int(st["trace_hours"]))})
    return "ok", cost


async def auto_grave(ch: dict):
    """A defeat leaves a grave marker where the player fell (rate-limited, never spam)."""
    st = await game_settings()
    if is_new_account(ch, st) or ch["level"] < int(st["aid_min_level"]):
        return
    if await try_cooldown(f"grave:{ch['user_id']}", int(st["grave_cooldown_hours"]) * 3600):
        return
    await col("traces").insert_one({"_id": uuid.uuid4().hex[:10], "uid": ch["user_id"], "name": ch["name"], "loc": ch["location"], "mark": "grave",
                                    "kind": "grave", "active": True, "found_n": 0, "found_by": [], "at": int(time.time()),
                                    "expire_at": datetime.now(timezone.utc) + timedelta(hours=int(st["trace_hours"]))})


async def find_trace(uid: int):
    """Called by patrol: maybe stumble on another player's trace in this location."""
    st = await game_settings()
    if random.random() > float(st["trace_find_chance"]):
        return None
    ch = await get_char(uid)
    now = datetime.now(timezone.utc)
    cands = await col("traces").find({"loc": ch["location"], "active": True, "expire_at": {"$gt": now}, "uid": {"$ne": uid},
                                      "found_by": {"$ne": uid}, "found_n": {"$lt": FIND_MAX}}).limit(10).to_list(10)
    if not cands:
        return None
    if not await bump_counter(f"tfind:{uid}:{day_id()}", 1, int(st["trace_find_daily"])):
        return None
    tr = random.choice(cands)
    hit = await col("traces").find_one_and_update({"_id": tr["_id"], "found_by": {"$ne": uid}, "found_n": {"$lt": FIND_MAX}},
                                                  {"$push": {"found_by": uid}, "$inc": {"found_n": 1}})
    if not hit:
        return None
    coins = int(int(st["trace_reward_coins"]) * (1 + ch["level"] / 30) * float(st["coin_rate"]))
    await add_coins(uid, coins, "trace")
    xp_got = 0
    if tr["kind"] == "mark" and await bump_counter(f"town:{tr['uid']}:{day_id()}", 1, int(st["trace_owner_daily"])):
        await add_xp(tr["uid"], int(st["trace_owner_xp"]), "trace", apply_rate=False)
    _, _, xp_got = await add_xp(uid, 10 + ch["level"], "trace", apply_rate=False)
    return {"mark": tr["mark"], "icon": MARK_ICON.get(tr["mark"], "✨"), "kind": tr["kind"], "owner": tr["name"], "coins": coins, "xp": xp_got}


# ---- spirit aid ---------------------------------------------------------------------------------------------------------------
async def send_aid(uid: int, target: int):
    """Give a nearby player a breath of reiatsu (energy). Returns (status, extra)."""
    st = await game_settings()
    if uid == target:
        return "self", None
    me, tg = await get_char(uid), await get_char(target)
    if not tg:
        return "gone", None
    if me["location"] != tg["location"]:
        return "far", None
    lvl = int(st["aid_min_level"])
    if me["level"] < lvl or tg["level"] < lvl or is_new_account(me, st) or is_new_account(tg, st):
        return "young", None
    day = day_id()
    if await counter_get(f"aidsend:{uid}:{day}") >= int(st["aid_daily_send"]):
        return "cap_send", None
    if await counter_get(f"aidrecv:{target}:{day}") >= int(st["aid_daily_recv"]):
        return "cap_recv", None
    wait = await try_cooldown(f"aid:{uid}:{target}", 86400)
    if wait:
        return "pair", wait
    await bump_counter(f"aidsend:{uid}:{day}", 1, int(st["aid_daily_send"]))
    await bump_counter(f"aidrecv:{target}:{day}", 1, int(st["aid_daily_recv"]))
    mx = int(st["energy_max"])
    for _ in range(3):
        tg = await get_char(target)
        cur, _, ts = energy_now(tg, st)
        new = min(mx, cur + int(st["aid_energy"]))
        r = await col("characters").update_one({"user_id": target, "energy": tg.get("energy"), "energy_ts": tg.get("energy_ts")},
                                               {"$set": {"energy": new, "energy_ts": int(time.time()) if new >= mx else ts}})
        if r.modified_count:
            break
    await add_xp(uid, int(st["aid_xp"]), "aid", apply_rate=False)
    await season_add(uid, 2, me["name"])
    return "ok", {"name": tg["name"], "me": me["name"], "n": int(st["aid_energy"])}


# ---- bounties ------------------------------------------------------------------------------------------------------------------------
async def bounty_total(target: int) -> int:
    rows = await col("bounties").aggregate([{"$match": {"target": target, "status": "active"}}, {"$group": {"_id": None, "s": {"$sum": "$amount"}}}]).to_list(1)
    return int(rows[0]["s"]) if rows else 0


async def bounty_board(n: int = 5) -> list:
    rows = await col("bounties").aggregate([{"$match": {"status": "active"}}, {"$group": {"_id": "$target", "s": {"$sum": "$amount"}}},
                                            {"$sort": {"s": -1}}, {"$limit": n}]).to_list(n)
    out = []
    for r in rows:
        c = await col("characters").find_one({"user_id": r["_id"]}, {"name": 1, "level": 1})
        if c:
            out.append({"uid": r["_id"], "name": c["name"], "level": c["level"], "amount": int(r["s"])})
    return out


async def find_by_name(name: str):
    return await col("characters").find_one({"name_key": (name or "").strip().casefold()}, {"user_id": 1, "name": 1, "level": 1})


async def bounty_place(uid: int, target: int, amount: int):
    st = await game_settings()
    if uid == target:
        return "self", None
    me, tg = await get_char(uid), await get_char(target)
    if not tg:
        return "gone", None
    if me["level"] < int(st["aid_min_level"]) or is_new_account(me, st):
        return "young", None
    if amount < int(st["bounty_min"]):
        return "low", int(st["bounty_min"])
    if await bounty_total(target) + amount > int(st["bounty_max_total"]):
        return "max", int(st["bounty_max_total"])
    if not await add_coins(uid, -amount, "bounty_escrow"):
        return "funds", amount
    await col("bounties").insert_one({"_id": uuid.uuid4().hex[:10], "target": target, "placer": uid, "amount": int(amount), "status": "active",
                                      "at": int(time.time()), "end_at": int(time.time()) + int(st["bounty_hours"]) * 3600})
    await chronicle("bounty_new", name=tg["name"], n=amount)
    log_event("bounty", uid, f"روی «{tg['name']}» ({target}) باونتی {int(amount):,} 🪙 گذاشت", target=target, amount=int(amount))
    return "ok", tg["name"]


async def claim_bounty(hunter: int, victim: int):
    """Pay every open bounty on `victim` to the winning hunter (minus fee). Returns coins or None."""
    st = await game_settings()
    hc = await get_char(hunter)
    if not hc or hc["level"] < int(st["bounty_min_level"]) or is_new_account(hc, st):
        return None
    open_ = await col("bounties").find({"target": victim, "status": "active", "placer": {"$ne": hunter}}).to_list(20)
    if not open_:
        return None
    if not await bump_counter(f"bclaim:{hunter}:{day_id()}", 1, int(st["bounty_daily_claims"])):
        return None
    total = 0
    for b in open_:
        hit = await col("bounties").find_one_and_update({"_id": b["_id"], "status": "active"}, {"$set": {"status": "claimed", "hunter": hunter}})
        if hit:
            total += int(hit["amount"])
    if not total:
        return None
    pay = int(total * (1 - float(st["bounty_fee"])))
    await add_coins(hunter, pay, "bounty")
    vc = await get_char(victim)
    await chronicle("bounty_claim", name=hc["name"], target=(vc or {}).get("name", "?"), n=pay)
    return pay


async def expire_bounties():
    """Scheduler: refund (minus fee) bounties nobody claimed."""
    st = await game_settings()
    now = int(time.time())
    while True:
        b = await col("bounties").find_one_and_update({"status": "active", "end_at": {"$lte": now}}, {"$set": {"status": "expired"}})
        if not b:
            break
        await add_coins(b["placer"], int(b["amount"] * (1 - float(st["bounty_fee"]))), "bounty_refund")
