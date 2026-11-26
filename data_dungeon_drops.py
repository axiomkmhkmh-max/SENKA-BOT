"""Dungeon rewards by level, not by luck (Nov 26). Pure data and pure functions.

Two problems this fixes:
  1. A chest could hand a level-20 player a Mythic piece he cannot wear for 60 levels: every colour has a level requirement
     (Common 1, Uncommon 5, Rare 15, Epic 30, Legendary 50, Mythic 80). Chest colours are now clipped to what the opener can use.
  2. A dungeon paid XP and DP but no item at all. Every dungeon now has its OWN final-stage drops (fixed per dungeon, the same
     for everybody), one of which is guaranteed on a full clear, a few times a day.
"""
import zlib

RARITY_LEVEL = (1, 5, 15, 30, 50, 80)   # level_req of rarity index 0..5 (checked against data_items)
RARITIES = ("Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythic")
FINAL_QTY = {"normal": 1, "hard": 1, "nightmare": 2, "abyss": 2, "legendary": 3}
FINAL_DAY_CAP = 2                        # guaranteed final drops per dungeon per player per day (anti-farm; GAME_DEFAULTS dg_final_day_cap)
FINAL_CATEGORIES = ("material", "potion", "book")


def usable_max_idx(level: int) -> int:
    """Highest rarity index whose gear this level can use."""
    return max(i for i, need in enumerate(RARITY_LEVEL) if int(level) >= need)


def clip_chest(lo: int, hi: int, level: int):
    """A chest's two colours (lo, hi) clipped to what `level` can use. Too low for even `lo`: both become the best usable colour."""
    top = usable_max_idx(level)
    if lo > top:
        return top, top
    return lo, min(hi, top)


def drop_rarities(dungeon_level: int) -> tuple:
    """Rarities of a dungeon's final drops, by the dungeon's own level."""
    if dungeon_level < 15:
        return ("Common", "Uncommon")
    if dungeon_level < 30:
        return ("Uncommon", "Rare")
    if dungeon_level < 60:
        return ("Rare", "Epic")
    if dungeon_level < 100:
        return ("Epic",)
    return ("Epic", "Legendary")


def final_drops(dungeon_id: str) -> list:
    """The dungeon's fixed final-stage drops: one material, one potion, one book (when the colour has one). Stable forever."""
    from data_items import ALL
    from data_races import DUNGEONS
    lvl = int((DUNGEONS.get(dungeon_id) or {}).get("level", 1))
    rars = drop_rarities(lvl)
    out = []
    for cat in FINAL_CATEGORIES:
        pool = sorted(i for i, x in ALL.items() if x.get("category") == cat and x.get("rarity") in rars and not x.get("retired"))
        if pool:
            out.append(pool[zlib.crc32(f"{dungeon_id}:{cat}".encode()) % len(pool)])
    return out


def final_qty(diff: str, category: str) -> int:
    n = FINAL_QTY.get(diff, 1)
    return n if category == "material" else 1
