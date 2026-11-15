"""Post-win rewards for Xcution (siphon) and the Bount mansion (soul absorption).

Called from service_combat's win branch. Rules live in data_gangs.py; this module only reads and writes the DB.
"""
from pymongo import ReturnDocument

from data_gangs import (BOUNT_LOC, XCUTION_BOSS_REWARD, XCUTION_BOSS_TARGET, XCUTION_LOC, absorb_coins,
                        boss_week_key, siphon_gain, xcution_rank)
from database import bump_counter, col, counter_get
from data_world import day_id
from service_player import get_char


async def gang_rewards(uid: int, doc: dict) -> dict:
    out = {}
    loc = doc.get("loc")
    ch = await get_char(uid)
    if not ch:
        return out
    if loc == BOUNT_LOC:
        key = f"bount:absorb:{uid}:{day_id()}"
        today = await counter_get(key)
        coins = absorb_coins(doc.get("lvl", 1), today)
        if coins > 0:
            from service_player import add_coins
            await add_coins(uid, coins, "bount_absorb")
            await bump_counter(key, coins, 10 ** 6)
        out["absorbed"] = coins
    if loc == XCUTION_LOC and (ch.get("xcution") or {}).get("joined"):
        key = f"xcn:siphon:{uid}:{day_id()}"
        today = await counter_get(key)
        gain = siphon_gain(doc.get("lvl", 1), bool(doc.get("elite")), today)
        if gain > 0:
            await col("characters").update_one({"user_id": uid}, {"$inc": {"xcution.points": gain}})
            await bump_counter(key, gain, 10 ** 6)
        pts = int((ch.get("xcution") or {}).get("points", 0)) + gain
        out["siphon"] = gain
        out["rank"] = xcution_rank(pts)
        out["boss"] = await xcution_boss_tally()
    return out


async def boss_state() -> dict:
    """This week's Xcution boss: wins so far, target, defeated flag."""
    key = f"xcution:{boss_week_key(day_id())}"
    await col("gangs").update_one({"_id": key}, {"$setOnInsert": {"wins": 0, "defeated": False}}, upsert=True)
    doc = await col("gangs").find_one({"_id": key}) or {}
    return {"wins": int(doc.get("wins", 0)), "target": XCUTION_BOSS_TARGET, "defeated": bool(doc.get("defeated"))}


async def xcution_boss_tally() -> dict:
    """Count one member win at the hideout. Defeats the boss once and rewards every member."""
    key = f"xcution:{boss_week_key(day_id())}"
    await col("gangs").update_one({"_id": key}, {"$setOnInsert": {"wins": 0, "defeated": False}}, upsert=True)
    doc = await col("gangs").find_one_and_update({"_id": key, "defeated": False}, {"$inc": {"wins": 1}},
                                                 return_document=ReturnDocument.AFTER)
    if doc and int(doc.get("wins", 0)) >= XCUTION_BOSS_TARGET:
        # Only the single write that flips `defeated` pays the reward, so members are paid exactly once.
        won = await col("gangs").find_one_and_update({"_id": key, "defeated": False, "wins": {"$gte": XCUTION_BOSS_TARGET}},
                                                     {"$set": {"defeated": True}}, return_document=ReturnDocument.AFTER)
        if won:
            await col("characters").update_many({"xcution.joined": True}, {"$inc": {"xcution.points": XCUTION_BOSS_REWARD}})
            return {"wins": int(won.get("wins", 0)), "target": XCUTION_BOSS_TARGET, "defeated": True, "paid_now": True}
    return {"wins": int((doc or {}).get("wins", 0)), "target": XCUTION_BOSS_TARGET,
            "defeated": bool((doc or {}).get("defeated")), "paid_now": False}
