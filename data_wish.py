"""Forge Mission (ماموریت ساخت): pick a piece of gear for your level, then go and collect what it needs. Pure rules.

Deliberately hard (player request): the materials are the FINAL-STAGE drops of dungeons around your level (each dungeon
pays only a couple of them a day), so one piece takes days of real dungeon clears. One mission at a time, one finished mission
per week, a big coin cost. It is a way to aim at a piece you want, not a faster road than playing.
"""
import zlib

from data_dungeon_drops import final_drops, usable_max_idx
from data_items import ALL

GEAR = ("weapon", "armor", "accessory")
RARITIES = ("Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythic")
MIN_IDX = 2                       # Rare and up: lower colours drop everywhere, nobody needs a mission for them
QTY_BY_IDX = {2: 6, 3: 9, 4: 12}  # of each dungeon drop
DUNGEON_BAND = 30                 # drops come from dungeons up to this many levels below the player (and not above)
DUNGEONS_NEEDED = 3
COINS_K = 1.5                     # x the item's base price
WEEKLY_DONE = 1                   # finished missions per player per week
ABANDON_WAIT_H = 24               # after abandoning a mission, wait before starting another


def eligible(level: int, race: str) -> list:
    """Item ids this player may aim at: own-race (or raceless) gear of his top two usable colours, from Rare up, never Mythic."""
    top = min(usable_max_idx(level), 4)
    if top < MIN_IDX:
        return []
    idxs = {i for i in (top - 1, top) if i >= MIN_IDX}
    out = [i for i, x in ALL.items() if x.get("category") in GEAR and RARITIES.index(x.get("rarity", "Common")) in idxs
           and not x.get("retired") and not x.get("special") and int(x.get("level_req", 1)) <= int(level)
           and x.get("race") in (None, "", race)]
    return sorted(out, key=lambda i: (-RARITIES.index(ALL[i]["rarity"]), ALL[i].get("category", ""), i))


def source_dungeons(level: int) -> list:
    """Dungeons that feed missions at this level: the highest ones the player can enter, within DUNGEON_BAND levels."""
    from data_races import DUNGEONS
    pool = sorted((d for d, v in DUNGEONS.items() if int(v["level"]) <= level and int(v["level"]) >= level - DUNGEON_BAND),
                  key=lambda d: -DUNGEONS[d]["level"])
    if len(pool) < DUNGEONS_NEEDED:  # a young player: take the best ones he can enter
        pool = sorted((d for d, v in DUNGEONS.items() if int(v["level"]) <= level), key=lambda d: -DUNGEONS[d]["level"])
    return pool


def requirement(item_id: str, level: int) -> dict:
    """{'mats': {item id: qty}, 'coins': n, 'from': {item id: dungeon id}} for this item at this level. Stable per (item, level band)."""
    x = ALL[item_id]
    idx = RARITIES.index(x["rarity"])
    qty = QTY_BY_IDX.get(idx, 12)
    pool = source_dungeons(level)[:6]
    seed = zlib.crc32(item_id.encode())
    mats, src = {}, {}
    for k in range(len(pool)):
        if len(mats) >= DUNGEONS_NEEDED:
            break
        did = pool[(seed + k) % len(pool)]
        drops = final_drops(did)
        if not drops:
            continue
        iid = drops[len(mats) % len(drops)]  # material, then potion, then book: three different kinds of drop
        if iid in mats:
            continue
        mats[iid] = qty
        src[iid] = did
    return {"mats": mats, "from": src, "coins": int(x.get("base_price", 0) * COINS_K)}
