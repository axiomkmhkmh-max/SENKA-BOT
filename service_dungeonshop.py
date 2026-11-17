"""Dungeon points (DP) and the dungeon shop.

Dungeons pay no coins and no items: a full clear pays DP (and XP). DP buys chests that hold coins and an item of the
chest's own colours. Pure rules first, then the database parts."""
import random

from data_world import day_id
from database import bump_counter, col, game_settings
from service_economy import inv_add, roll_drop
from service_log import log_event
from service_player import add_coins, get_char

# DP per full clear = DP_BY_DIFF[difficulty] x (1 + dungeon level / DP_LEVEL_STEP). Harder and higher dungeons pay
# much more; dungeons pay no coins and no items any more, so DP (and XP) is the whole reward.
DP_BY_DIFF = {"normal": 6, "hard": 12, "nightmare": 25, "abyss": 60, "legendary": 150}
DP_LEVEL_STEP = 20
DP_DAILY_CAP = 1500
# key -> cost in DP, the two rarity indexes the chest can hold (0 Common/white .. 5 Mythic/red), the odds of the lower
# and the higher one, coin range, icon, names. Each chest holds only its own colours:
# bronze = white + green, silver = blue + purple, gold = gold + red.
# Pity (GAME_DEFAULTS dp_pity_<key>): after that many chests in a row with the lower colour, the next one is the higher.
BOXES = {
    "bronze": {"cost": 40, "rar": (0, 1), "odds": (60, 40), "coins": (150, 450), "icon": "🥉", "fa": "جعبه‌ی برنزی", "en": "Bronze Chest"},
    "silver": {"cost": 120, "rar": (2, 3), "odds": (65, 35), "coins": (600, 1500), "icon": "🥈", "fa": "جعبه‌ی نقره‌ای", "en": "Silver Chest"},
    "gold": {"cost": 360, "rar": (4, 5), "odds": (80, 20), "coins": (2250, 5000), "icon": "🥇", "fa": "جعبه‌ی طلایی", "en": "Gold Chest"},
}


def dp_for_clear(dungeon: dict) -> int:
    """DP for one full clear: grows with difficulty and with the dungeon's level."""
    from data_races import DUNGEONS
    lvl = int((DUNGEONS.get(dungeon.get("id")) or {}).get("level", 1))
    return int(round(DP_BY_DIFF.get(dungeon.get("diff", "normal"), DP_BY_DIFF["normal"]) * (1 + lvl / DP_LEVEL_STEP)))


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
    """Returns (status, result). status: ok | nobox | poor. result: {"coins": n, "item": id, "rar_idx": i, "pity": bool}."""
    b = BOXES.get(key)
    if not b:
        return "nobox", None
    # atomic: the DP is taken only if the balance covers it, so a double tap cannot overspend
    hit = await col("characters").find_one_and_update({"user_id": uid, "dp": {"$gte": b["cost"]}}, {"$inc": {"dp": -b["cost"]}})
    if not hit:
        return "poor", None
    st = await game_settings()
    pity_n = int(st[f"dp_pity_{key}"])  # 0 = no pity
    streak = int((hit.get("box_pity") or {}).get(key, 0))
    lo, hi = b["rar"]
    idx = rng.choices((lo, hi), b["odds"])[0]
    pity = pity_n > 0 and streak + 1 >= pity_n and idx < hi
    if pity:
        idx = hi
    up = hi
    await col("characters").update_one({"user_id": uid}, {"$set": {f"box_pity.{key}": 0 if idx >= up else streak + 1}})
    n = rng.randint(*b["coins"])
    await add_coins(uid, n, "dp_chest")
    iid = await roll_drop(uid, exact_idx=idx, rng=rng)  # exactly the rolled colour: the chest never pays outside its own
    await inv_add(uid, iid, 1, force=True)  # a chest is never lost to a full bag
    res = {"coins": n, "item": iid, "rar_idx": idx, "pity": pity}
    log_event("dungeon_shop", uid, f"جعبه‌ی دانجن {key}: {res}", box=key)
    return "ok", res
