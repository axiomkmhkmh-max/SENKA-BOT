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


async def run_all() -> None:
    from service_racegear import migrate_armour_once
    from service_raceweapon import migrate_blades_once
    for name, fn in (("evolution pin", pin_evolution_once), ("race weapons", migrate_blades_once),
                     ("race armour", migrate_armour_once)):
        try:
            log.info("%s: %s character(s) moved", name, await fn())
        except Exception:
            log.exception("%s failed; it will retry on next start", name)
