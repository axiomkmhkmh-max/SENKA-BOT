"""Dungeon points (DP) and the dungeon shop.

Dungeons no longer drop level-based items (they were mostly junk). A full clear pays DP instead; DP buys chests
that hold coins or an item. Pure rules first, then the database parts."""
import random

from data_world import day_id
from database import bump_counter, col, game_settings
from service_economy import inv_add, roll_drop
from service_log import log_event
from service_player import add_coins, get_char

DP_BY_DIFF = {"normal": 2, "hard": 4, "nightmare": 8, "abyss": 16, "legendary": 32}
DP_DAILY_CAP = 400
# key -> cost in DP, lowest item rarity index (0 Common .. 5 Mythic), coin range, icon, names.
# Every chest now pays coins AND an item (it used to be coins OR an item, so the best chest was half the time just coins).
# The coin range is half of the old one, so the coins per chest stay the same on average.
# odds: weights for floor, floor+1, floor+2 rarity. weapon: chance the item is a weapon.
# Pity (GAME_DEFAULTS dp_pity_<key>): after that many chests in a row without reaching floor+1, the next one does.
BOXES = {
    "bronze": {"cost": 40, "floor": 1, "coins": (150, 450), "odds": (40, 45, 15), "weapon": 0.15, "icon": "🥉", "fa": "جعبه‌ی برنزی", "en": "Bronze Chest"},
    "silver": {"cost": 120, "floor": 2, "coins": (600, 1500), "odds": (40, 45, 15), "weapon": 0.25, "icon": "🥈", "fa": "جعبه‌ی نقره‌ای", "en": "Silver Chest"},
    "gold": {"cost": 360, "floor": 3, "coins": (2250, 5000), "odds": (48, 42, 10), "weapon": 0.35, "icon": "🥇", "fa": "جعبه‌ی طلایی", "en": "Gold Chest"},
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
    idx = b["floor"] + rng.choices((0, 1, 2), b["odds"])[0]
    up = b["floor"] + 1
    pity = pity_n > 0 and streak + 1 >= pity_n and idx < up
    if pity:
        idx = up
    await col("characters").update_one({"user_id": uid}, {"$set": {f"box_pity.{key}": 0 if idx >= up else streak + 1}})
    n = rng.randint(*b["coins"])
    await add_coins(uid, n, "dp_chest")
    # a Mythic result is a Mythic weapon (the only Mythic items roll_drop can hand out)
    iid = await roll_drop(uid, source_mult=1.0, weapon_chance=1.0 if idx >= 5 else b["weapon"], floor_idx=idx, rng=rng)
    await inv_add(uid, iid, 1, force=True)  # a chest is never lost to a full bag
    res = {"coins": n, "item": iid, "rar_idx": idx, "pity": pity}
    log_event("dungeon_shop", uid, f"جعبه‌ی دانجن {key}: {res}", box=key)
    return "ok", res
