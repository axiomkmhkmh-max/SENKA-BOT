"""Services for the Nov 19 batch: adventures, level bosses, the roll shop, companion upgrades, Inner World 2 and the
elite shop (rules and numbers in data_extras2). Every coin or item write is conditional or atomic, like the rest."""
import random
import time

from data_extras2 import (ADV_DAILY, ADVENTURES, ELITE_MIN_LEVEL, ELITE_PRICE_K, ELITE_STOCK, ELITE_STOCK_100, INNER2, INNER_KEY,
                          LEVEL_BOSS_KEY, LEVEL_BOSS_MYTHIC, LEVEL_BOSS_RELIC, LEVEL_BOSS_STONE, LEVEL_BOSSES, PET_MAX_TIER,
                          PET_UP_COINS, PET_UP_MATS, ROLL_COST, ROLL_EGG_SHARE, ROLL_JACKPOT_EVERY, ROLL_TEN_COST, ROLL_WEIGHTS,
                          TEMPER_STONE, level_band)
from data_items import ALL, EVO_BY_RARITY, MYTHIC_ACCESSORIES
from data_weapons import RARITIES
from data_world import day_id
from database import bump_counter, col, counter_get, try_cooldown
from service_economy import inv_add, inv_get, inv_remove, roll_drop
from service_player import add_coins, get_char


# ---- adventures ---------------------------------------------------------------------------------------------------------
async def adventure_info(uid: int) -> dict:
    used = await counter_get(f"adv:{uid}:{day_id()}")
    return {"left": max(0, ADV_DAILY - used), "cap": ADV_DAILY}


async def adventure_start(uid: int, aid: str, lang: str):
    from service_combat import active_pve, pve_start
    a = ADVENTURES.get(aid)
    ch = await get_char(uid)
    if not a or not ch:
        return "bad", None
    if int(ch["level"]) < a["level"]:
        return "level", a["level"]
    from service_combat import blocking_pve
    if await blocking_pve(uid):
        return "busy", None
    if await try_cooldown(f"adv:go:{uid}", 3):
        return "wait", None
    if not await bump_counter(f"adv:{uid}:{day_id()}", 1, ADV_DAILY):
        return "limit", None
    doc = await pve_start(uid, lang, dungeon={"id": aid, "adv": True, "stage": 1, "total": a["stages"], "diff": "normal"})
    return "ok", doc


# ---- level bosses -------------------------------------------------------------------------------------------------------
async def level_boss_info(uid: int) -> dict:
    ch = await get_char(uid)
    band = level_band(int(ch["level"]))
    done = await counter_get(f"lboss:{uid}:{day_id()}")
    return {"band": band, "boss": LEVEL_BOSSES[band], "done": done >= 1}


async def level_boss_start(uid: int, lang: str):
    from service_combat import active_pve, pve_start
    ch = await get_char(uid)
    if not ch:
        return "bad", None
    from service_combat import blocking_pve
    if await blocking_pve(uid):
        return "busy", None
    if await try_cooldown(f"lboss:go:{uid}", 3):
        return "wait", None
    band = level_band(int(ch["level"]))  # always the player's own band: nobody can fight another band's boss
    if not await bump_counter(f"lboss:{uid}:{day_id()}", 1, 1):
        return "done", None
    doc = await pve_start(uid, lang, dungeon={"id": f"lb{band}", "lboss": True, "band": band, "stage": 1, "total": 1, "diff": "normal"})
    return "ok", doc


async def level_boss_loot(uid: int, band: int) -> dict:
    b = LEVEL_BOSSES[band]
    items = [await roll_drop(uid, exact_idx=b[4])]
    if random.random() < LEVEL_BOSS_RELIC:
        items.append(random.choice(EVO_BY_RARITY[RARITIES[min(3, b[4])]] or EVO_BY_RARITY["Common"]))
    if random.random() < LEVEL_BOSS_STONE:
        items.append(TEMPER_STONE)
    if random.random() < LEVEL_BOSS_KEY:
        items.append(INNER_KEY)
    if band == len(LEVEL_BOSSES) - 1 and MYTHIC_ACCESSORIES and random.random() < LEVEL_BOSS_MYTHIC:
        items.append(random.choice(MYTHIC_ACCESSORIES))
    for i in items:
        await inv_add(uid, i, 1, force=True)  # boss loot is never lost to a full bag
    return {"items": items}


# ---- roll shop ----------------------------------------------------------------------------------------------------------
def _roll_pool(race: str, rarity: str, rng) -> str:
    """A card (Kidō for Shinigami / Visored, the race's technique cards for the others) or a spirit egg of one colour."""
    from data_items import KIDO_CARD_BY_RARITY, race_cards
    eggs = [i for i, x in ALL.items() if x["category"] == "egg" and x["rarity"] == rarity]
    if race in ("shinigami", "visored"):
        cards = KIDO_CARD_BY_RARITY.get(rarity) or []
    else:
        cards = race_cards(race, rarity) if race else []
    if eggs and (not cards or rng.random() < ROLL_EGG_SHARE):
        return rng.choice(eggs)
    if cards:
        return rng.choice(cards)
    return rng.choice(eggs) if eggs else None


async def roll(uid: int, n: int, rng=random):
    """n = 1 or 10. Returns (status, results). Every ROLL_JACKPOT_EVERY-th roll of a player is a jackpot:
    a red accessory and a Tempering Stone."""
    if n not in (1, 10):
        return "bad", None
    if await try_cooldown(f"roll:{uid}", 2):
        return "wait", None
    cost = ROLL_COST if n == 1 else ROLL_TEN_COST
    if not await add_coins(uid, -cost, "roll_shop"):
        return "funds", cost
    ch = await get_char(uid)
    after = await col("characters").find_one_and_update({"user_id": uid}, {"$inc": {"rolls": n}}, return_document=True)
    total = int((after or {}).get("rolls", n))
    results = []
    for k in range(n):
        no = total - n + k + 1
        if no % ROLL_JACKPOT_EVERY == 0 and MYTHIC_ACCESSORIES:
            for iid in (rng.choice(MYTHIC_ACCESSORIES), TEMPER_STONE):
                await inv_add(uid, iid, 1, force=True)
                results.append({"id": iid, "jackpot": True})
            continue
        rar = rng.choices(list(ROLL_WEIGHTS), list(ROLL_WEIGHTS.values()))[0]
        iid = _roll_pool(ch.get("race"), rar, rng) or _roll_pool(ch.get("race"), "Rare", rng)
        if iid:
            await inv_add(uid, iid, 1, force=True)
            results.append({"id": iid, "jackpot": False})
    return "ok", {"results": results, "total": total, "next_jackpot": ROLL_JACKPOT_EVERY - total % ROLL_JACKPOT_EVERY}


# ---- companions ---------------------------------------------------------------------------------------------------------
def pet_up_cost(tier: int):
    """(coins, spirit materials, min colour) to raise a companion from `tier` to tier + 1."""
    return PET_UP_COINS * (tier + 1) ** 2, PET_UP_MATS * (tier + 1), min(tier, 3)


async def pet_upgrade(uid: int):
    """Raises the active companion (the first one) by one star with coins and spirit materials."""
    from data_crafting import plan_inputs
    from service_crafting import _consume
    if await try_cooldown(f"petup:{uid}", 2):
        return "wait", None
    ch = await get_char(uid)
    pets = list(ch.get("pets") or [])
    if not pets:
        return "none", None
    tier = int(pets[0].get("tier", 0))
    if tier >= PET_MAX_TIER:
        return "max", tier
    coins, n, t = pet_up_cost(tier)
    inv = await inv_get(uid)
    plan = plan_inputs([{"g": "spirit", "n": n, "t": t}], inv["items"], ALL)
    if plan is None:
        return "mats", (n, t)
    if not await add_coins(uid, -coins, "pet_upgrade"):
        return "funds", coins
    if not await _consume(uid, plan):
        await add_coins(uid, coins, "pet_upgrade_refund")
        return "mats", (n, t)
    r = await col("characters").update_one({"user_id": uid, "pets.0.tier": tier, "pets.0.sp": pets[0]["sp"]}, {"$inc": {"pets.0.tier": 1}})
    if not r.modified_count:  # the active companion changed meanwhile: give everything back
        for iid, q in plan.items():
            await inv_add(uid, iid, q, force=True)
        await add_coins(uid, coins, "pet_upgrade_refund")
        return "retry", None
    return "ok", tier + 1


# ---- Inner World 2 ------------------------------------------------------------------------------------------------------
async def inner2_use(uid: int, path: str):
    """Spend one Inner World Key on a path: a small permanent bonus, up to the path's cap."""
    if path not in INNER2:
        return "bad", None
    _fa, _en, key, step, cap = INNER2[path]
    ch = await get_char(uid)
    cur = float((ch.get("inner2") or {}).get(key, 0.0))
    if cur >= cap - 1e-9:
        return "cap", cur
    if not await inv_remove(uid, INNER_KEY, 1):
        return "nokey", None
    new = min(cap, round(cur + step, 5))
    await col("characters").update_one({"user_id": uid}, {"$set": {f"inner2.{key}": new}})
    return "ok", new


# ---- elite shop ---------------------------------------------------------------------------------------------------------
def elite_stock(day: str, level: int):
    """Epic and Legendary consumables, materials and the Tempering Stone; a bigger stock from level 100."""
    if level < ELITE_MIN_LEVEL:
        return []
    r = random.Random("elite" + day)
    pool = sorted(i for i, x in ALL.items() if x["rarity"] in ("Epic", "Legendary") and not x.get("retired")
                  and x["category"] in ("potion", "book", "egg", "material", "relic"))
    n = ELITE_STOCK_100 if level >= 100 else ELITE_STOCK
    picks = r.sample(pool, min(n, len(pool)))
    return [TEMPER_STONE] + picks


def elite_price(item_id: str) -> int:
    return int(ALL[item_id]["base_price"] * ELITE_PRICE_K)


async def elite_buy(uid: int, item_id: str, day: str):
    ch = await get_char(uid)
    if item_id not in elite_stock(day, int(ch["level"])):
        return "gone", None
    if not await bump_counter(f"elite:{uid}:{day}:{item_id}", 1, 3):  # three of each a day
        return "limit", None
    price = elite_price(item_id)
    if not await add_coins(uid, -price, "elite_shop"):
        return "funds", price
    await inv_add(uid, item_id, 1, force=True)
    return "ok", price


# ---- tempering stone (forge and armour past +5) -------------------------------------------------------------------------
STONE_FROM = 5  # levels +6 and up need stones


def stones_needed(plus: int) -> int:
    """Stones to go from `plus` to plus + 1 (0 below +5): 1 for +6, 2 for +7 ..."""
    return max(0, plus - STONE_FROM + 1)


async def take_stones(uid: int, plus: int) -> bool:
    n = stones_needed(plus)
    return n == 0 or await inv_remove(uid, TEMPER_STONE, n)


async def give_back_stones(uid: int, plus: int):
    n = stones_needed(plus)
    if n:
        await inv_add(uid, TEMPER_STONE, n, force=True)


def today_key() -> str:
    return time.strftime("%Y-%m-%d", time.gmtime())
