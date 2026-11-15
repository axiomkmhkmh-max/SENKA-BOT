"""Post-battle effects for Xcution (siphon, surge, rank, weekly boss), the Bount mansion (absorption, soul stacks).

Called from service_combat's settle. Rules live in data_gangs.py; this module only reads and writes the DB.
"""
import time

from pymongo import ReturnDocument

from data_gangs import (BOUNT_LOC, SURGE_DMG, SURGE_SECONDS, XCUTION_BOSS_DMG, XCUTION_BOSS_REWARD,
                        XCUTION_BOSS_TARGET, XCUTION_BOSS_TOP_BONUS, XCUTION_LOC, absorb_coins, boss_dmg,
                        boss_phase, boss_week_key, bount_stacks_after, siphon_gain, week_end_epoch, xcution_rank)
from database import bump_counter, col, counter_get
from data_world import day_id
from service_player import get_char


def _boss_key() -> str:
    return f"xcution:{boss_week_key(day_id())}"


async def gang_rewards(uid: int, doc: dict) -> dict:
    """Xcution and Bount rewards for a won battle. Called only on a win."""
    out = {}
    loc = doc.get("loc")
    ch = await get_char(uid)
    if not ch:
        return out
    if loc == BOUNT_LOC:
        stacks = int((ch.get("bount") or {}).get("stacks", 0))
        key = f"bount:absorb:{uid}:{day_id()}"
        today = await counter_get(key)
        coins = absorb_coins(doc.get("lvl", 1), today, stacks)
        if coins > 0:
            from service_player import add_coins
            await add_coins(uid, coins, "bount_absorb")
            await bump_counter(key, coins, 10 ** 6)
        out["absorbed"] = coins
    x = ch.get("xcution") or {}
    if loc == XCUTION_LOC and x.get("joined"):
        key = f"xcn:siphon:{uid}:{day_id()}"
        today = await counter_get(key)
        gain = siphon_gain(doc.get("lvl", 1), bool(doc.get("elite")), today)
        old = int(x.get("points", 0))
        if gain > 0:
            now = int(time.time())
            await col("characters").update_one({"user_id": uid},
                                               {"$inc": {"xcution.points": gain},
                                                "$set": {"xcution.surge_until": now + SURGE_SECONDS}})
            await bump_counter(key, gain, 10 ** 6)
        pts = old + gain
        out["siphon"] = gain
        out["points"] = pts
        out["rank"] = xcution_rank(pts)
        out["rank_up"] = xcution_rank(pts) > xcution_rank(old)
        out["surge"] = gain > 0
        out["boss"] = await xcution_boss_tally(uid)
    return out


async def boss_state() -> dict:
    """This week's Xcution boss: wins so far, target, phase, damage bonus for members, defeated flag."""
    key = _boss_key()
    await col("gangs").update_one({"_id": key}, {"$setOnInsert": {"wins": 0, "defeated": False, "contrib": {}}}, upsert=True)
    doc = await col("gangs").find_one({"_id": key}) or {}
    wins = int(doc.get("wins", 0))
    return {"wins": wins, "target": XCUTION_BOSS_TARGET, "defeated": bool(doc.get("defeated")),
            "phase": boss_phase(wins), "dmg": boss_dmg(wins)}


async def current_boss_buff() -> tuple:
    """(damage bonus, valid until) for a member who joins now, so a newcomer gets the phase they missed."""
    st = await boss_state()
    return st["dmg"], week_end_epoch(day_id())


async def xcution_boss_tally(uid: int = 0) -> dict:
    """Count one member win at the hideout. Opens phases for everyone, defeats the boss once and pays out.

    Only the write that flips `defeated` pays the reward, so members are paid exactly once.
    """
    key = _boss_key()
    until = week_end_epoch(day_id())
    await col("gangs").update_one({"_id": key}, {"$setOnInsert": {"wins": 0, "defeated": False, "contrib": {}}}, upsert=True)
    doc = await col("gangs").find_one_and_update({"_id": key, "defeated": False},
                                                 {"$inc": {"wins": 1, f"contrib.{uid}": 1}},
                                                 return_document=ReturnDocument.AFTER)
    if not doc:  # already defeated this week
        cur = await col("gangs").find_one({"_id": key}) or {}
        return {"wins": int(cur.get("wins", 0)), "target": XCUTION_BOSS_TARGET, "defeated": True,
                "phase_up": False, "paid_now": False, "you_top": False}
    wins = int(doc.get("wins", 0))
    out = {"wins": wins, "target": XCUTION_BOSS_TARGET, "defeated": False, "phase_up": False,
           "paid_now": False, "you_top": False}
    phase, prev = boss_phase(wins), boss_phase(wins - 1)
    if phase > prev and phase < len(XCUTION_BOSS_DMG) - 1:  # a phase opens (not the final defeat)
        await col("characters").update_many({"xcution.joined": True},
                                            {"$set": {"xcution.boss_dmg": XCUTION_BOSS_DMG[phase], "xcution.boss_until": until}})
        out.update(phase_up=True, phase=phase)
    if wins >= XCUTION_BOSS_TARGET:
        won = await col("gangs").find_one_and_update({"_id": key, "defeated": False, "wins": {"$gte": XCUTION_BOSS_TARGET}},
                                                     {"$set": {"defeated": True}}, return_document=ReturnDocument.AFTER)
        if won:
            await col("characters").update_many({"xcution.joined": True},
                                                {"$inc": {"xcution.points": XCUTION_BOSS_REWARD},
                                                 "$set": {"xcution.boss_dmg": XCUTION_BOSS_DMG[-1], "xcution.boss_until": until}})
            top_uid, top_n = None, 0
            for k, v in (won.get("contrib") or {}).items():
                if int(v) > top_n:
                    top_uid, top_n = int(k), int(v)
            if top_uid is not None:
                await col("characters").update_one({"user_id": top_uid, "xcution.joined": True},
                                                   {"$inc": {"xcution.points": XCUTION_BOSS_TOP_BONUS}})
            out.update(defeated=True, paid_now=True, you_top=(top_uid == uid and uid != 0), phase_up=False)
    return out


async def bount_settle(uid: int, doc: dict, st: dict) -> int:
    """Store the soul stacks left after a PvE battle (seal spent in the fight is gone), and add one for a mansion win."""
    x = (st["a"].get("x") or {})
    won = st.get("winner") == "a"
    new = bount_stacks_after(int(x.get("bstack", 0)), won and doc.get("loc") == BOUNT_LOC)
    await col("characters").update_one({"user_id": uid}, {"$set": {"bount.stacks": new}})
    return new
