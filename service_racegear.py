"""Race armour (data_racegear): random grants, the move to the new race on a race change, and the one-time move of the
old shared armour onto each player's own race armour.

Armour keeps its colour (rarity) and its kind number (0..19) when it moves, and its tempering (armor_plus) moves with it.
"""
import random
import time
import zlib

from data_items import ALL
from data_racegear import COLOURS, GARMENTS, MAKEUPS, parse_ra, ra_id
from data_weapons import RARITIES
from database import col
from service_economy import inv_add

KINDS = len(next(iter(GARMENTS.values()))) * len(MAKEUPS)   # 20 kinds per race


def random_armour(race: str, colour: int, rng=random) -> str:
    """One random race armour of this colour (armour is never chosen, only won)."""
    return ra_id(race, rng.randrange(KINDS), max(0, min(COLOURS - 1, int(colour))))


async def grant_armour(uid: int, race: str, colour: int, rng=random) -> str:
    iid = random_armour(race, colour, rng)
    await inv_add(uid, iid, 1, force=True)
    return iid


def _moved_id(item_id: str, race: str):
    """The race armour an armour item becomes for `race`, or None if it is not armour."""
    it = ALL.get(item_id or "")
    if not it or it.get("category") != "armor":
        return None
    p = parse_ra(item_id)
    if p:
        n, c = p[1], p[2]
    else:  # old shared armour: same colour, a kind picked from its id so it is always the same one
        n, c = zlib.crc32(item_id.encode()) % KINDS, RARITIES.index(it["rarity"]) if it["rarity"] in RARITIES else 0
    return ra_id(race, n, c)


async def _move_all(uid: int, race: str, only_other_race: bool) -> int:
    """Turn every armour of the player (bag and worn) into the race's own. Returns how many moved."""
    moved = 0
    ch = await col("characters").find_one({"user_id": uid}, {"armor_id": 1, "armor_plus": 1})
    if not ch:
        return 0
    cur = ch.get("armor_id")
    tgt = _moved_id(cur, race) if cur else None
    if tgt and tgt != cur and (not only_other_race or (ALL.get(cur) or {}).get("race") != race):
        plus = int((ch.get("armor_plus") or {}).get(cur, 0))
        upd = {"$set": {"armor_id": tgt}}
        if plus:
            upd["$set"][f"armor_plus.{tgt}"] = plus
            upd["$unset"] = {f"armor_plus.{cur}": ""}
        r = await col("characters").update_one({"user_id": uid, "armor_id": cur}, upd)
        moved += int(bool(r.modified_count))
    inv = await col("inventories").find_one({"user_id": uid}, {"items": 1}) or {}
    inc, unset = {}, {}
    for iid, q in (inv.get("items") or {}).items():
        if q <= 0:
            continue
        it = ALL.get(iid) or {}
        if it.get("category") != "armor" or (only_other_race and it.get("race") == race):
            continue
        tgt = _moved_id(iid, race)
        if tgt and tgt != iid:
            inc[f"items.{tgt}"] = inc.get(f"items.{tgt}", 0) + q
            unset[f"items.{iid}"] = ""
            moved += q
    if inc:
        await col("inventories").update_one({"user_id": uid}, {"$unset": unset})
        await col("inventories").update_one({"user_id": uid}, {"$inc": inc})
    return moved


async def on_race_change(uid: int, old_race: str, new_race: str):
    """Race armour of the old race becomes the new race's, same kind, same colour, same tempering."""
    await _move_all(uid, new_race, only_other_race=True)


MIGRATION_ID = "race_armour_v1"


async def migrate_armour_once() -> int:
    """The old shared armour (bag and worn) becomes each player's own race armour, same colour. Runs once."""
    if await col("migrations").find_one({"_id": MIGRATION_ID}):
        return 0
    n = 0
    async for ch in col("characters").find({}, {"user_id": 1, "race": 1}):
        n += await _move_all(ch["user_id"], ch.get("race", "human"), only_other_race=False)
    await col("migrations").update_one({"_id": MIGRATION_ID}, {"$set": {"moved": n, "at": int(time.time())}}, upsert=True)
    return n
