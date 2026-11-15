"""Soul Core (هسته‌ی روح) economy.

Sources (the only ones):
- the hardest quests (HARDEST_QUESTS): claiming one rolls a small chance;
- the hardest dungeon difficulties (HARDEST_DIFFS): clearing one rolls a small chance.
Both rolls share one daily cap per player (`core_day_cap`), so the grind cannot be stacked.

Every grant and spend is written to `core_log` (TTL-expired after 90 days).
The wallet is `wheel_wallet` (the same doc the wheels use).
"""
import logging
import random
import time
from datetime import datetime, timedelta, timezone

from data_world import day_id
from database import bump_counter, col, game_settings

log = logging.getLogger("senka.cores")

WALLET = "wheel_wallet"
HARDEST_QUESTS = frozenset({"l_legend", "b_bankai", "m_lvl30"})  # Slayer of Legends, Road to Bankai, Call of Bankai
HARDEST_DIFFS = frozenset({"abyss", "legendary"})               # the two top dungeon difficulties
LOG_TTL_DAYS = 90
_indexed = False


async def _ensure_index() -> None:
    global _indexed
    if _indexed:
        return
    _indexed = True
    try:
        await col("core_log").create_index("expire_at", expireAfterSeconds=0)
    except Exception:
        log.exception("core_log TTL index failed")


async def _log(uid: int, n: int, reason: str) -> None:
    await _ensure_index()
    now = datetime.now(timezone.utc)
    await col("core_log").insert_one({
        "user_id": uid, "n": int(n), "reason": reason, "at": int(time.time()),
        "expire_at": now + timedelta(days=LOG_TTL_DAYS),
    })


async def get_cores(uid: int) -> int:
    d = await col(WALLET).find_one({"_id": uid}) or {}
    return int(d.get("cores", 0))


async def grant_cores(uid: int, n: int, reason: str) -> None:
    if n <= 0:
        return
    await col(WALLET).update_one({"_id": uid}, {"$inc": {"cores": int(n)}}, upsert=True)
    await _log(uid, n, reason)


async def spend_cores(uid: int, n: int, reason: str) -> bool:
    """Conditional debit: never goes below zero. Returns False when there are not enough cores."""
    if n <= 0:
        return True
    r = await col(WALLET).update_one({"_id": uid, "cores": {"$gte": int(n)}}, {"$inc": {"cores": -int(n)}})
    if not r.modified_count:
        return False
    await _log(uid, -int(n), reason)
    return True


async def roll_core(uid: int, chance: float, reason: str) -> bool:
    """A small chance for one Soul Core, limited to `core_day_cap` per player per day.
    The daily cap is only used when the chance actually hits."""
    if random.random() >= chance:
        return False
    st = await game_settings()
    if not await bump_counter(f"core:day:{uid}:{day_id()}", 1, int(st["core_day_cap"])):
        return False
    await grant_cores(uid, 1, reason)
    return True


async def on_quest_claim(uid: int, qid: str) -> bool:
    if qid not in HARDEST_QUESTS:
        return False
    st = await game_settings()
    return await roll_core(uid, float(st["core_quest_chance"]), f"quest:{qid}")


async def on_dungeon_clear(uid: int, diff: str, dungeon_id: str) -> bool:
    if diff not in HARDEST_DIFFS:
        return False
    st = await game_settings()
    return await roll_core(uid, float(st["core_dungeon_chance"]), f"dungeon:{dungeon_id}:{diff}")
