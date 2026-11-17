"""Respec and race change.

Stat reset: every point you put into a stat comes back to your spendable points (race base stays). Costs coins
that grow with level, and can be done once per RESPEC_COOLDOWN.

Race change: move to another unlocked race. Free; the only limit is a cooldown (RACE_CHANGE_COOLDOWN, 48 hours).
Every allocated stat point comes back to spend again on the new race (the new race brings its own base and home).
The evolution stage is kept (its title and bonuses are the new race's own at that stage). A Visored can go back to
Shinigami and, having passed the Visored Gauntlet once, return to Visored without redoing it. Kidō follows the race
rules: a race that cannot use it loses its spells. The race weapon and race armour turn into the new race's own
(service_raceweapon / service_racegear): the armour keeps its colour, the weapon must be chosen again at the same level.

Both are refused while you are in a fight (PvE, duel, trade) so nothing changes mid-battle.
"""
import time

from data_races import RACES, STATS, race_selectable
from database import col, game_settings
from service_player import add_coins, get_char

RESPEC_COST_PER_LEVEL = 150
RESPEC_COOLDOWN = 24 * 3600
RACE_CHANGE_COST_PER_LEVEL = 0          # race changes are free now
RACE_CHANGE_COOLDOWN = 48 * 3600        # ... limited only by this cooldown
KIDO_RACES = ("shinigami", "visored")


# ---- one-time rebase after the race balance pass ----------------------------------------------------------
REBASE_ID = "race_base_v2"


async def rebase_race_stats_once() -> int:
    """Move existing characters onto the rebalanced race bases. Runs once (marker in `migrations`).
    Characters created after the marker are already on the new base, so they are never touched again."""
    from data_races import OLD_RACE_BASE, PREV_RACE_BASE, rebased_stats
    if await col("migrations").find_one({"_id": REBASE_ID}):
        return 0
    moved, failed = 0, 0
    async for ch in col("characters").find({"race": {"$in": list(OLD_RACE_BASE)}}, {"user_id": 1, "race": 1, "stats": 1}):
        new = rebased_stats(ch["race"], ch.get("stats") or {}, new_base=PREV_RACE_BASE[ch["race"]])
        r = await col("characters").update_one({"_id": ch["_id"], "stats": ch.get("stats") or {}}, {"$set": {"stats": new}})
        moved += int(bool(r.modified_count))
        failed += int(not r.modified_count)
    await col("migrations").update_one({"_id": REBASE_ID}, {"$set": {"moved": moved, "failed": failed, "at": int(time.time())}}, upsert=True)
    return moved


REBASE_V3_ID = "race_base_v3"


async def rebase_race_stats_v3_once() -> int:
    """Second balance pass: move characters from the previous race bases onto the current ones, keeping every point
    they allocated. Runs once (marker in `migrations`); runs after rebase_race_stats_once, which now targets PREV_RACE_BASE."""
    from data_races import PREV_RACE_BASE, rebased_stats
    if await col("migrations").find_one({"_id": REBASE_V3_ID}):
        return 0
    moved, failed = 0, 0
    async for ch in col("characters").find({"race": {"$in": list(PREV_RACE_BASE)}}, {"user_id": 1, "race": 1, "stats": 1}):
        new = rebased_stats(ch["race"], ch.get("stats") or {}, old_base=PREV_RACE_BASE[ch["race"]])
        r = await col("characters").update_one({"_id": ch["_id"], "stats": ch.get("stats") or {}}, {"$set": {"stats": new}})
        moved += int(bool(r.modified_count))
        failed += int(not r.modified_count)
    await col("migrations").update_one({"_id": REBASE_V3_ID}, {"$set": {"moved": moved, "failed": failed, "at": int(time.time())}}, upsert=True)
    return moved


def _allocated(ch):
    base = RACES[ch["race"]]["stats"]
    return {k: max(0, int((ch.get("stats") or {}).get(k, 0)) - int(base.get(k, 0))) for k in STATS}


def respec_quote(ch):
    alloc = _allocated(ch)
    return {"points": sum(alloc.values()), "coins": RESPEC_COST_PER_LEVEL * max(1, int(ch["level"]))}


def race_change_quote(ch):
    return {"coins": RACE_CHANGE_COST_PER_LEVEL * max(1, int(ch["level"]))}


async def _busy(uid):
    from service_combat import active_pve, duel_busy
    from service_trade import busy_session
    if await active_pve(uid):
        return "fighting"
    if await duel_busy(uid):
        return "fighting"
    if await busy_session(uid):
        return "trading"
    return None


def _cooldown_left(ch, key, span):
    last = int((ch.get(key) or 0))
    return max(0, last + span - int(time.time()))


async def respec_stats(uid: int):
    ch = await get_char(uid)
    if not ch:
        return "noreg", None
    busy = await _busy(uid)
    if busy:
        return busy, None
    left = _cooldown_left(ch, "respec_at", RESPEC_COOLDOWN)
    if left:
        return "cooldown", left
    q = respec_quote(ch)
    if q["points"] <= 0:
        return "nothing", None
    if int(ch.get("coins", 0)) < q["coins"]:
        return "funds", q["coins"]
    if not await add_coins(uid, -q["coins"], "respec"):
        return "funds", q["coins"]
    base = RACES[ch["race"]]["stats"]
    r = await col("characters").update_one(
        {"user_id": uid, "stats": ch["stats"]},
        {"$set": {"stats": {k: int(base.get(k, 0)) for k in STATS}, "respec_at": int(time.time())},
         "$inc": {"points": q["points"]}})
    if not r.modified_count:
        await add_coins(uid, q["coins"], "respec_refund")  # someone else changed stats meanwhile
        return "retry", None
    return "ok", q


async def change_race(uid: int, new_race: str):
    ch = await get_char(uid)
    if not ch:
        return "noreg", None
    if new_race == ch["race"] or new_race not in RACES:
        return "invalid", None
    if not race_selectable(new_race, ch):
        return "locked", None
    busy = await _busy(uid)
    if busy:
        return busy, None
    left = _cooldown_left(ch, "race_changed_at", RACE_CHANGE_COOLDOWN)
    if left:
        return "cooldown", left
    old = ch["race"]
    alloc = _allocated(ch)
    new_base = RACES[new_race]["stats"]
    stats = {k: int(new_base.get(k, 0)) for k in STATS}  # a clean base: every point comes back to spend again
    refund = sum(alloc.values())
    upd = {"race": new_race, "stats": stats, "location": RACES[new_race]["home"],
           "race_changed_at": int(time.time()), "race_from": old}
    if old == "shinigami" and new_race == "visored" or old == "visored":
        upd["visored_unlocked"] = True  # the Gauntlet was passed once: Visored <-> Shinigami without redoing it
    if new_race not in KIDO_RACES:  # no Kidō without the Shinigami/Visored path: clear the spells
        upd.update({"kido_learned": [], "kido": {"had": [], "bak": []}})
    r = await col("characters").update_one({"user_id": uid, "race": old, "stats": ch.get("stats")},
                                           {"$set": upd, "$inc": {"points": refund}})
    if not r.modified_count:
        return "retry", None
    from service_raceweapon import on_race_change as weapon_follow
    from service_racegear import on_race_change as armour_follow
    await weapon_follow(uid, old, new_race)
    await armour_follow(uid, old, new_race)
    return "ok", {"points": refund}
