"""One-time migrations of the big rework (evolution titles, race weapons, race armour). Each runs once (marker in the
`migrations` collection) and is safe to re-run: every write is conditional on the document it read."""
import logging
import time

from database import col

log = logging.getLogger("senka.migrate")

EVO_PIN_ID = "evo_pin_v1"


def legacy_evo_stage(race: str, level: int) -> int:
    """The stage a character without an `evo` field showed before the rework (titles then rose by level gates)."""
    from data_evolution import OLD_EVO_LEN
    from data_races import LEVEL_GATES
    idx = 0
    for i, gate in enumerate(LEVEL_GATES[: OLD_EVO_LEN.get(race, 3)]):
        if level >= gate:
            idx = i
    return idx


async def pin_evolution_once() -> int:
    """Titles rise only through evolution now. Characters that never took a trial kept a level-based title: pin it as
    their evolution stage so nobody loses the title they had, and from now on only a trial raises it."""
    if await col("migrations").find_one({"_id": EVO_PIN_ID}):
        return 0
    moved = 0
    async for ch in col("characters").find({"evo": {"$exists": False}}, {"user_id": 1, "race": 1, "level": 1}):
        stage = legacy_evo_stage(ch.get("race", "human"), int(ch.get("level", 1)))
        r = await col("characters").update_one({"_id": ch["_id"], "evo": {"$exists": False}}, {"$set": {"evo": stage}})
        moved += int(bool(r.modified_count))
    await col("migrations").update_one({"_id": EVO_PIN_ID}, {"$set": {"moved": moved, "at": int(time.time())}}, upsert=True)
    return moved


RESPEC_ID = "ability_stats_respec_v1"


async def free_respec_once() -> int:
    """Abilities now draw on each race's own stat, so every player gets one free stat reset: allocated points come
    back (stats return to the race base) and a notice tells them to spend the points again."""
    if await col("migrations").find_one({"_id": RESPEC_ID}):
        return 0
    from data_races import RACES, STATS
    moved = 0
    async for ch in col("characters").find({}, {"user_id": 1, "race": 1, "stats": 1}):
        race = ch.get("race")
        if race not in RACES:
            continue
        base = RACES[race]["stats"]
        alloc = sum(max(0, int((ch.get("stats") or {}).get(k, 0)) - int(base.get(k, 0))) for k in STATS)
        upd = {"$set": {"stats": {k: int(base.get(k, 0)) for k in STATS}, "respec_notice": False}}
        if alloc:
            upd["$inc"] = {"points": alloc}
        r = await col("characters").update_one({"_id": ch["_id"], "stats": ch.get("stats")}, upd)
        moved += int(bool(r.modified_count))
    await col("migrations").update_one({"_id": RESPEC_ID}, {"$set": {"moved": moved, "at": int(time.time())}}, upsert=True)
    return moved


RESPEC_NOTICE = {
    "fa": "📊 <b>همه‌ی امتیازهای استتت برگشت!</b>\n\nحالا قدرت ابیلیتی‌های هر نژاد ۷۰٪ از استت خود آن نژاد می‌آید:\n"
          "شینیگامی کیدو · کوئینسی، ویزورد و انسان ریاتسو · آرانکار هوهو · هالو هاکودا · فول‌برینگر قدرت سلاح.\n"
          "حمله‌ی معمولی فقط با زنجوتسو و ضربه‌ی سنگین با زنجوتسو و ریاتسو است.\n\nاز پروفایل امتیازهایت را دوباره پخش کن.",
    "en": "📊 <b>All your stat points came back!</b>\n\nEvery race's abilities now draw 70% of their power from that race's own stat:\n"
          "Shinigami Kidō · Quincy, Visored and Human Reiatsu · Arrancar Hohō · Hollow Hakuda · Fullbringer weapon attack.\n"
          "Plain attacks use Zanjutsu only and heavy strikes Zanjutsu and Reiatsu.\n\nSpend your points again in your profile.",
}


async def notify_respec(bot, stop) -> None:
    """One private message to every player whose points were returned (resumes after a restart)."""
    from service_raceweapon import broadcast_flag
    await broadcast_flag(bot, stop, "respec_notice", RESPEC_NOTICE, {"fa": "👤 پروفایل", "en": "👤 Profile"}, "prof")


BR_RESET_ID = "battlerank_fair_reset_v2"


async def battlerank_reset_once() -> int:
    """Battle Rank became flat and level-free (rework 2). Points earned this season under the old rules came mostly from
    level, so the current season restarts from zero for everyone. Rewards already claimed stay claimed (no double chests)."""
    if await col("migrations").find_one({"_id": BR_RESET_ID}):
        return 0
    from data_battlerank import season_of
    season = season_of(time.time())
    r = await col("characters").update_many({"br_season": season, "br": {"$gt": 0}}, {"$set": {"br": 0, "br_best": 0}})
    await col("migrations").update_one({"_id": BR_RESET_ID}, {"$set": {"at": int(time.time()), "n": r.modified_count, "season": season}},
                                       upsert=True)
    return r.modified_count


CREDIT_RESET_ID = "bank_credit_reset_v1"


async def bank_credit_reset_once() -> int:
    """Credit used to rise +25 for a loan taken and repaid in the same minute, so it was farmed to the top. Every score
    above the starting 600 goes back to 600 once (a bump of v makes a save that was loaded before this lose the race)."""
    if await col("migrations").find_one({"_id": CREDIT_RESET_ID}):
        return 0
    from engine_bank import CREDIT_START
    r = await col("bank_accounts").update_many({"credit": {"$gt": CREDIT_START}}, {"$set": {"credit": CREDIT_START}, "$inc": {"v": 1}})
    await col("migrations").update_one({"_id": CREDIT_RESET_ID}, {"$set": {"at": int(time.time()), "n": r.modified_count}}, upsert=True)
    return r.modified_count


MAT_MERGE_ID = "materials_merge_v1"


async def merge_materials_once() -> int:
    """Move every retired material in the bags into its merged item (data_items.MAT_MERGE). Each old stack is taken
    out with one atomic read-and-unset, then added to the merged item, so nothing is counted twice."""
    if await col("migrations").find_one({"_id": MAT_MERGE_ID}):
        return 0
    from data_items import ACC_SWAP, MAT_MERGE
    MAT_ONLY = {k: v for k, v in MAT_MERGE.items() if k not in ACC_SWAP}
    moved = 0
    flt = {"$or": [{f"items.{i}": {"$exists": True}} for i in MAT_ONLY]}
    async for inv in col("inventories").find(flt, {"user_id": 1, "items": 1}):
        uid = inv["user_id"]
        for old, new in MAT_ONLY.items():
            if old not in (inv.get("items") or {}):
                continue
            before = await col("inventories").find_one_and_update({"user_id": uid, f"items.{old}": {"$exists": True}},
                                                                  {"$unset": {f"items.{old}": ""}})
            q = int(((before or {}).get("items") or {}).get(old, 0))
            if q > 0:
                await col("inventories").update_one({"user_id": uid}, {"$inc": {f"items.{new}": q}})
        moved += 1
    await col("migrations").update_one({"_id": MAT_MERGE_ID}, {"$set": {"at": int(time.time()), "n": moved}}, upsert=True)
    return moved


ACC_SWAP_ID = "accessories_swap_v1"


async def swap_accessories_once() -> int:
    """Old accessories (the same names at several colours) become their fixed replacement of the same colour and slot:
    in bags (atomic per stack, like merge_materials_once) and in the two equipped slots."""
    if await col("migrations").find_one({"_id": ACC_SWAP_ID}):
        return 0
    from data_items import ACC_SWAP
    moved = 0
    flt = {"$or": [{f"items.{i}": {"$exists": True}} for i in ACC_SWAP]}
    async for inv in col("inventories").find(flt, {"user_id": 1, "items": 1}):
        uid = inv["user_id"]
        for old in [i for i in (inv.get("items") or {}) if i in ACC_SWAP]:
            before = await col("inventories").find_one_and_update({"user_id": uid, f"items.{old}": {"$exists": True}},
                                                                  {"$unset": {f"items.{old}": ""}})
            q = int(((before or {}).get("items") or {}).get(old, 0))
            if q > 0:
                await col("inventories").update_one({"user_id": uid}, {"$inc": {f"items.{ACC_SWAP[old]}": q}})
        moved += 1
    for slot in ("acc_id", "charm_id"):
        async for ch in col("characters").find({slot: {"$in": list(ACC_SWAP)}}, {"user_id": 1, slot: 1}):
            await col("characters").update_one({"user_id": ch["user_id"], slot: ch[slot]}, {"$set": {slot: ACC_SWAP[ch[slot]]}})
            moved += 1
    await col("migrations").update_one({"_id": ACC_SWAP_ID}, {"$set": {"at": int(time.time()), "n": moved}}, upsert=True)
    return moved


async def run_all() -> None:
    from service_racegear import migrate_armour_once
    from service_raceweapon import migrate_blades_once
    for name, fn in (("evolution pin", pin_evolution_once), ("race weapons", migrate_blades_once),
                     ("race armour", migrate_armour_once), ("free stat reset", free_respec_once),
                     ("battle rank fair reset", battlerank_reset_once), ("bank credit reset", bank_credit_reset_once),
                     ("materials merge", merge_materials_once), ("accessories swap", swap_accessories_once)):
        try:
            log.info("%s: %s character(s) moved", name, await fn())
        except Exception:
            log.exception("%s failed; it will retry on next start", name)
