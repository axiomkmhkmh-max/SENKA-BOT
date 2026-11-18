"""Dungeon points (DP) and the dungeon shop.

Dungeons pay no coins and no items: a full clear pays DP (and XP). DP buys chests that hold coins and an item of the
chest's own colours. Pure rules first, then the database parts."""
import random

from data_items import ALL

from data_world import day_id
from database import bump_counter, col, game_settings
from service_economy import inv_add, roll_drop
from service_log import log_event
from service_player import add_coins, get_char

# DP per full clear = DP_BY_DIFF[difficulty] x (1 + dungeon level / DP_LEVEL_STEP). Harder and higher dungeons pay
# much more; dungeons pay no coins and no items any more, so DP (and XP) is the whole reward.
DP_BY_DIFF = {"normal": 6, "hard": 12, "nightmare": 25, "abyss": 60, "legendary": 150}
DP_LEVEL_STEP = 20
DP_DAILY_CAP = 4000  # fallback only: the live value is GAME_DEFAULTS["dp_daily_cap"]
# key -> cost in DP, the two rarity indexes the chest can hold (0 Common/white .. 5 Mythic/red), the odds of the lower
# and the higher one, coin range, icon, names. Each chest holds only its own colours:
# bronze = white + green, silver = blue + purple, gold = gold + red.
# Pity (GAME_DEFAULTS dp_pity_<key>): after that many chests in a row with the lower colour, the next one is the higher.
BOXES = {
    "bronze": {"cost": 40, "rar": (0, 1), "odds": (60, 40), "coins": (150, 450), "icon": "🥉", "fa": "جعبه‌ی برنزی", "en": "Bronze Chest"},
    "silver": {"cost": 120, "rar": (2, 3), "odds": (65, 35), "coins": (600, 1500), "icon": "🥈", "fa": "جعبه‌ی نقره‌ای", "en": "Silver Chest"},
    "gold": {"cost": 360, "rar": (4, 5), "odds": (80, 20), "coins": (2250, 5000), "icon": "🥇", "fa": "جعبه‌ی طلایی", "en": "Gold Chest"},
}
# Evolution relics (the fuel of evolution and of a race weapon's colour) come from these chests by luck, on top of the
# item: key -> (chance, relic rarities it can be). Relics only exist up to Epic (purple), so the gold chest gives purple.
RELIC_ODDS = {"bronze": (0.20, ("Common", "Uncommon")), "silver": (0.30, ("Rare", "Epic")), "gold": (0.40, ("Epic",))}


def dp_for_clear(dungeon: dict) -> int:
    """DP for one full clear: grows with difficulty and with the dungeon's level."""
    from data_races import DUNGEONS
    lvl = int((DUNGEONS.get(dungeon.get("id")) or {}).get("level", 1))
    return int(round(DP_BY_DIFF.get(dungeon.get("diff", "normal"), DP_BY_DIFF["normal"]) * (1 + lvl / DP_LEVEL_STEP)))


async def award_dp(uid: int, dungeon: dict) -> int:
    pts = dp_for_clear(dungeon)
    cap = int((await game_settings()).get("dp_daily_cap", DP_DAILY_CAP))
    if not await bump_counter(f"dp:{uid}:{day_id()}", pts, cap):
        return 0  # today's cap is used up (anti-farming)
    await col("characters").update_one({"user_id": uid}, {"$inc": {"dp": pts}})
    return pts


# Dungeon-only special items (data_items.DG_SPECIAL): chance per full clear by difficulty. Capped per player per day
# (GAME_DEFAULTS dg_special_day_cap); the cap is only used when the roll hits, and the whole thing can be switched off
# with dg_special_on.
SPECIAL_CHANCE = {"normal": 0.08, "hard": 0.12, "nightmare": 0.16, "abyss": 0.22, "legendary": 0.30}


async def roll_special(uid: int, dungeon: dict, rng=random):
    """After a full clear: a small chance of one special item of the dungeon's difficulty. Returns the item id or None."""
    from data_items import DG_SPECIAL
    st = await game_settings()
    if not int(st.get("dg_special_on", 1)):
        return None
    diff = dungeon.get("diff", "normal")
    pool = DG_SPECIAL.get(diff) or []
    if not pool or rng.random() >= SPECIAL_CHANCE.get(diff, 0.0):
        return None
    if not await bump_counter(f"dgsp:{uid}:{day_id()}", 1, int(st.get("dg_special_day_cap", 6))):
        return None
    iid = rng.choice(pool)
    await inv_add(uid, iid, 1, force=True)  # a special item is never lost to a full bag
    log_event("dungeon_special", uid, f"آیتم مخصوص دانجن: {iid}", item=iid, diff=diff)
    return iid


async def dp_balance(uid: int) -> int:
    ch = await get_char(uid)
    return int((ch or {}).get("dp", 0) or 0)


async def buy_box(uid: int, key: str, rng=random):
    """Returns (status, result). status: ok | nobox | poor.
    result: {"coins": n, "item": id, "rar_idx": i, "pity": bool, "relic": evolution relic id or None}."""
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
    qty = rng.randint(2, 3) if ALL.get(iid, {}).get("category") == "material" else 1  # materials come 2-3 at a time
    await inv_add(uid, iid, qty, force=True)  # a chest is never lost to a full bag
    bonus = None
    if key == "gold":  # the gold chest also holds a second prize of its colour: materials, potions or a book
        from service_extras import pick_item
        cat = rng.choice(("material", "material", "potion", "book"))
        bid = pick_item(cat, [idx], rng)
        if bid:
            bq = rng.randint(2, 3) if cat == "material" else 2 if cat == "potion" else 1
            await inv_add(uid, bid, bq, force=True)
            bonus = {"item": bid, "qty": bq}
        if rng.random() < 0.15:  # and sometimes a Tempering Stone (forge and armour past +5)
            from data_extras2 import TEMPER_STONE
            await inv_add(uid, TEMPER_STONE, 1, force=True)
            bonus = dict(bonus or {}, stone=True)
    relic = None
    chance, rars = RELIC_ODDS.get(key, (0.0, ()))
    if rars and rng.random() < chance:
        from data_items import EVO_BY_RARITY
        pool = EVO_BY_RARITY.get(rng.choice(rars)) or []
        if pool:
            relic = rng.choice(pool)
            await inv_add(uid, relic, 1, force=True)
    res = {"coins": n, "item": iid, "qty": qty, "rar_idx": idx, "pity": pity, "relic": relic, "bonus": bonus}
    log_event("dungeon_shop", uid, f"جعبه‌ی دانجن {key}: {res}", box=key)
    return "ok", res
