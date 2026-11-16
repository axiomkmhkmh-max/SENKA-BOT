"""Dungeon points (DP) and the dungeon shop.

Dungeons no longer drop level-based items (they were mostly junk). A full clear pays DP instead; DP buys chests
that hold coins or an item. Pure rules first, then the database parts."""
import random

from data_world import day_id
from database import bump_counter, col
from service_economy import inv_add, roll_drop
from service_log import log_event
from service_player import add_coins, get_char

DP_BY_DIFF = {"normal": 2, "hard": 4, "nightmare": 8, "abyss": 16, "legendary": 32}
DP_DAILY_CAP = 400
# key -> cost in DP, lowest item rarity index (0 Common .. 5 Mythic), coin range, icon, names
BOXES = {
    "bronze": {"cost": 40, "floor": 1, "coins": (300, 900), "icon": "🥉", "fa": "جعبه‌ی برنزی", "en": "Bronze Chest"},
    "silver": {"cost": 120, "floor": 2, "coins": (1200, 3000), "icon": "🥈", "fa": "جعبه‌ی نقره‌ای", "en": "Silver Chest"},
    "gold": {"cost": 360, "floor": 3, "coins": (4500, 10000), "icon": "🥇", "fa": "جعبه‌ی طلایی", "en": "Gold Chest"},
}


def dp_for_clear(dungeon: dict) -> int:
    """DP for one full clear: grows with difficulty and with the dungeon's level."""
    from data_races import DUNGEONS
    lvl = int((DUNGEONS.get(dungeon.get("id")) or {}).get("level", 1))
    return DP_BY_DIFF.get(dungeon.get("diff", "normal"), 2) * (1 + lvl // 25)


async def award_dp(uid: int, dungeon: dict) -> int:
    pts = dp_for_clear(dungeon)
    if not await bump_counter(f"dp:{uid}:{day_id()}", pts, DP_DAILY_CAP):
        return 0  # today's cap is used up (anti-farming)
    await col("characters").update_one({"user_id": uid}, {"$inc": {"dp": pts}})
    return pts


async def dp_balance(uid: int) -> int:
    ch = await get_char(uid)
    return int((ch or {}).get("dp", 0) or 0)


async def buy_box(uid: int, key: str, rng=random):
    """Returns (status, result). status: ok | nobox | poor. result: {"coins": n} or {"item": id} (+ "full" when the bag was full)."""
    b = BOXES.get(key)
    if not b:
        return "nobox", None
    # atomic: the DP is taken only if the balance covers it, so a double tap cannot overspend
    hit = await col("characters").find_one_and_update({"user_id": uid, "dp": {"$gte": b["cost"]}}, {"$inc": {"dp": -b["cost"]}})
    if not hit:
        return "poor", None
    res = {}
    if rng.random() < 0.5:
        n = rng.randint(*b["coins"])
        await add_coins(uid, n, "dp_chest")
        res["coins"] = n
    else:
        iid = await roll_drop(uid, source_mult=1.5, floor_idx=b["floor"])
        if await inv_add(uid, iid, 1):
            res["item"] = iid
        else:  # bag full: pay the top of the coin range instead of losing the chest
            n = b["coins"][1]
            await add_coins(uid, n, "dp_chest")
            res.update(coins=n, full=iid)
    log_event("dungeon_shop", uid, f"جعبه‌ی دانجن {key}: {res}", box=key)
    return "ok", res
