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
# The six dungeons of the Nov 22 pack also drop Soul Cores, from Nightmare up. Their cores and the event cores have a daily cap
# of their own (core_new_day_cap), so the old cap is untouched and nobody can farm unlimited cores.
NEW_DUNGEONS = frozenset({"eleventh_arena", "kuchiki_archive", "fake_karakura_rift", "bankai_dojo", "vasto_lair", "final_trial_gate"})
NEW_DIFF_MULT = {"nightmare": 1.0, "abyss": 2.0, "legendary": 4.0}
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


async def core_boost(uid: int) -> float:
    """1.0 + the equipped skin's Soul Core bonus (skins give at most +30%). Any failure means no boost."""
    try:
        from data_skins import skin_extra
        from service_player import get_char
        return 1.0 + float(skin_extra(await get_char(uid))["core"])
    except Exception:
        log.exception("core boost lookup failed")
        return 1.0


async def roll_core(uid: int, chance: float, reason: str, *, new_source: bool = False) -> bool:
    """A small chance for one Soul Core, limited per player per day.
    Old sources share `core_day_cap`; the new dungeons and events share `core_new_day_cap` (new_source=True).
    The daily cap is only used when the chance actually hits."""
    if random.random() >= chance:
        return False
    st = await game_settings()
    if new_source:
        ok = await bump_counter(f"core:new:{uid}:{day_id()}", 1, int(st.get("core_new_day_cap", 1)))
    else:
        ok = await bump_counter(f"core:day:{uid}:{day_id()}", 1, int(st["core_day_cap"]))
    if not ok:
        return False
    await grant_cores(uid, 1, reason)
    return True


async def on_quest_claim(uid: int, qid: str) -> bool:
    if qid not in HARDEST_QUESTS:
        return False
    st = await game_settings()
    return await roll_core(uid, float(st["core_quest_chance"]) * await core_boost(uid), f"quest:{qid}")


async def on_dungeon_clear(uid: int, diff: str, dungeon_id: str) -> bool:
    st = await game_settings()
    if dungeon_id in NEW_DUNGEONS and diff in NEW_DIFF_MULT:  # the new pack: cores from Nightmare up, own daily cap
        chance = (float(st["core_dungeon_chance"]) * NEW_DIFF_MULT[diff] * float(st.get("core_new_dungeon_k", 1.5))
                  * await core_boost(uid))
        return await roll_core(uid, chance, f"dungeon:{dungeon_id}:{diff}", new_source=True)
    if diff not in HARDEST_DIFFS:
        return False
    mult = {"abyss": 2.0, "legendary": 4.0}.get(diff, 1.0)  # Soul Cores come more often from the hardest clears
    return await roll_core(uid, float(st["core_dungeon_chance"]) * mult * await core_boost(uid), f"dungeon:{dungeon_id}:{diff}")


async def on_event_end(uid: int, rank: int, ok: bool, kind: str = "") -> bool:
    """Event settlement: every real participant rolls a small chance for a Soul Core; the top three roll three times as
    likely, a lost event a bit less than half as likely. Uses the new-source daily cap, so it is never farmable."""
    st = await game_settings()
    chance = float(st.get("core_event_chance", 0.05)) * (3.0 if rank < 3 else 1.0) * (1.0 if ok else 0.4)
    chance *= float(__import__("data_world").EVENTS.get(kind, {}).get("core", 1.0)) * await core_boost(uid)
    return await roll_core(uid, chance, f"event:{kind}", new_source=True)
