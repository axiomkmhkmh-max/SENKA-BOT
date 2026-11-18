"""Inventory, equipment, drops, NPC shop, player market, auctions, gacha."""
import math
import random
import time
import uuid

from pymongo import ReturnDocument

from config import BAG_START
from data_crafting import forge_value, player_bonus
from data_chars import CHAR_BY_ID, CHARS, GACHA_RATES, char_bonus
from data_items import ALL, BY_RARITY, WEAPON_BY_RARITY, iname
from data_weapons import RARITIES
from database import col, game_settings, try_cooldown
from service_log import log_event
from service_player import add_coins, add_xp, bump_quest, get_char
from service_worldcore import mods_for

SLOT_FIELD = {"weapon": "weapon_id", "armor": "armor_id", "ring": "acc_id", "necklace": "charm_id"}
PETS = [("Spirit Fox", "روباه روحی"), ("Moon Cat", "گربه‌ی ماه"), ("Ember Wisp", "شراره‌ی زنده"),
        ("Tide Serpent", "مار جزرومد"), ("Hollow Pup", "توله‌ی تهی"), ("Storm Hawk", "عقاب توفان")]
from data_extras2 import NEW_PETS  # noqa: E402
PETS += NEW_PETS  # appended, so the species of companions already hatched (index sp) never change
DROP_W = [50, 25, 15, 7, 2.5, 0.5]
# Pity: this many drops in a row below the tier guarantees it. It used to be 1000 / 200 / 50, which almost nobody ever reached.
PITY = (("legendary", 4, 150), ("epic", 3, 40), ("rare", 2, 15))


# ---- inventory ---------------------------------------------------------------
async def inv_get(uid: int) -> dict:
    d = await col("inventories").find_one({"user_id": uid})
    if not d:
        await col("inventories").update_one({"user_id": uid}, {"$setOnInsert": {"user_id": uid, "items": {}, "capacity": BAG_START}}, upsert=True)
        d = await col("inventories").find_one({"user_id": uid})
    return d


def slots_used(items: dict) -> int:
    return sum(math.ceil(q / max(1, ALL[i]["stack_max"])) for i, q in items.items() if q > 0 and i in ALL)


async def inv_add(uid: int, item_id: str, qty: int = 1, force: bool = False) -> bool:
    from data_items import merged
    item_id = merged(item_id)  # a retired material (old listing, old trade) arrives as the merged one
    if item_id not in ALL or qty <= 0:
        return False
    inv = await inv_get(uid)
    cur = inv["items"].get(item_id, 0)
    sm = max(1, ALL[item_id]["stack_max"])
    need = math.ceil((cur + qty) / sm) - math.ceil(cur / sm)
    if not force and slots_used(inv["items"]) + need > inv.get("capacity", BAG_START):
        return False
    await col("inventories").update_one({"user_id": uid}, {"$inc": {f"items.{item_id}": qty}}, upsert=True)
    return True


async def inv_remove(uid: int, item_id: str, qty: int = 1) -> bool:
    r = await col("inventories").update_one({"user_id": uid, f"items.{item_id}": {"$gte": qty}}, {"$inc": {f"items.{item_id}": -qty}})
    if r.modified_count:
        await col("inventories").update_one({"user_id": uid, f"items.{item_id}": 0}, {"$unset": {f"items.{item_id}": ""}})
    return bool(r.modified_count)


def slot_of(item: dict):
    if item["category"] == "weapon":
        return "weapon_id"
    if item["category"] == "armor":
        return "armor_id"
    return SLOT_FIELD.get(item.get("subtype"))


async def equip(uid: int, item_id: str) -> str:
    it, ch = ALL.get(item_id), await get_char(uid)
    field = slot_of(it) if it else None
    if not field:
        return "noequip"
    if it.get("retired") or it.get("subtype") == "rweapon":
        return "noequip"  # old blades are gone; the race weapon is chosen in its own panel, never from the bag
    if it.get("race") and it["race"] != ch.get("race"):
        return "race"  # race armour fits only its own race
    if ch["level"] < it.get("level_req", 1):
        return "level"
    cur = ch.get(field)
    if cur == item_id:
        return "already"
    if not await inv_remove(uid, item_id, 1):
        return "missing"
    r = await col("characters").update_one({"user_id": uid, field: cur}, {"$set": {field: item_id}})
    if not r.modified_count:
        await inv_add(uid, item_id, 1, force=True)
        return "retry"
    if cur:
        await inv_add(uid, cur, 1, force=True)
    return "ok"


async def unequip(uid: int, field: str) -> str:
    ch = await get_char(uid)
    cur = ch.get(field)
    if not cur:
        return "empty"
    if field == "weapon_id" and (ALL.get(cur) or {}).get("subtype") == "rweapon":
        return "locked"  # the race weapon stays in hand (it grows with you; switch it with a Rebirth Seal)
    if not await inv_add(uid, cur, 1):
        return "full"
    r = await col("characters").update_one({"user_id": uid, field: cur}, {"$set": {field: None}})
    if not r.modified_count:
        await inv_remove(uid, cur, 1)
        return "retry"
    return "ok"


async def use_item(uid: int, item_id: str):
    it, ch = ALL.get(item_id), await get_char(uid)
    eff = (it or {}).get("effect")
    if not eff:
        return "nouse", None
    t = eff["type"]
    if t in ("kido", "kido_book"):
        from data_race_rules import race_allows
        if not race_allows(ch.get("race"), "kd"):  # only Shinigami / Visored cast Kidō: other races used to lose the item for nothing
            return "race", None
    if t == "kido":
        import math as _m
        if ch["level"] < _m.ceil(eff["num"] * 0.8):
            return "level", _m.ceil(eff["num"] * 0.8)
        if eff["num"] in ch["kido"][eff["branch"]]:
            return "known", None
        if not await inv_remove(uid, item_id, 1):
            return "missing", None
        await col("characters").update_one({"user_id": uid}, {"$addToSet": {f"kido.{eff['branch']}": eff["num"]}})
        return "ok", eff["num"]
    if t == "konpaku":  # SENKA+ charm: one extra Konpaku life in duels while it lasts
        if not await inv_remove(uid, item_id, 1):
            return "missing", None
        until = int(time.time()) + int(eff["minutes"]) * 60
        await col("characters").update_one({"user_id": uid}, {"$set": {"konpaku_until": until}})
        return "ok", eff["minutes"]
    if t == "tech_lvl":  # race technique card: raises that technique's mastery, in order
        if eff["race"] != ch.get("race"):
            return "race_card", None
        cur = int((ch.get("tech_lvl") or {}).get(eff["slot"], 0))
        if cur >= eff["lvl"]:
            return "known", None
        if cur < eff["lvl"] - 1:
            return "order", eff["lvl"] - 1
        if not await inv_remove(uid, item_id, 1):
            return "missing", None
        r = await col("characters").update_one({"user_id": uid, f"tech_lvl.{eff['slot']}": cur if cur else {"$in": [0, None]}},
                                               {"$set": {f"tech_lvl.{eff['slot']}": eff["lvl"]}})
        if not r.modified_count:
            await inv_add(uid, item_id, 1, force=True)
            return "retry", None
        return "ok", eff["lvl"]
    if t == "znp_reset":  # Weapon Rebirth Seal: switch the race weapon's type (the seal is spent in that panel)
        return "rw_switch", None
    if t == "almighty":  # Yhwach's Eye: arms one survival of a fatal blow in PvE (see service_combat.pve_start)
        if not await inv_remove(uid, item_id, 1):
            return "missing", None
        until = int(time.time()) + int(eff["minutes"]) * 60
        await col("characters").update_one({"user_id": uid}, {"$set": {"almighty_until": until}})
        return "ok", eff["minutes"]
    if t == "xp":
        if not await inv_remove(uid, item_id, 1):
            return "missing", None
        _, _, got = await add_xp(uid, eff["amount"], "book", apply_rate=False)
        return "ok", got
    if t == "buff":
        if not await inv_remove(uid, item_id, 1):
            return "missing", None
        st = await game_settings()
        now = time.time()
        old = (ch.get("buffs") or {}).get(eff["stat"]) or {}
        base = max(now, old.get("until", 0))
        until = min(now + int(st["buff_max_minutes"]) * 60, base + eff["minutes"] * 60)
        await col("characters").update_one({"user_id": uid}, {"$set": {f"buffs.{eff['stat']}": {"pct": max(eff["pct"], old.get("pct", 0) if old.get("until", 0) > now else 0), "until": until}}})
        return "ok", eff["minutes"]
    if t == "kido_book":
        known = set(ch["kido"][eff["branch"]])
        pick = next((n for n in range(1, min(99, eff["cap"]) + 1) if n not in known), None)
        if pick is None:
            return "known", None
        if ch["level"] < math.ceil(pick * 0.8):
            return "level", math.ceil(pick * 0.8)
        if not await inv_remove(uid, item_id, 1):
            return "missing", None
        await col("characters").update_one({"user_id": uid}, {"$addToSet": {f"kido.{eff['branch']}": pick}})
        return "ok", pick
    if t == "bond":
        # The bond belongs to the chosen blade (data_zanpakuto.bond_key), the same key the Zanpakuto panel and combat
        # read. It used to be written under the weapon in hand, so a character with a chosen blade never saw it grow.
        from data_zanpakuto import bond_key
        key = bond_key(ch)
        if key == "none":
            return "nouse", None
        if not await inv_remove(uid, item_id, 1):
            return "missing", None
        await col("characters").update_one({"user_id": uid}, {"$inc": {f"bond.{key}": eff["amount"]}})
        return "ok", eff["amount"]
    if t == "pet":
        # eggs go through the incubator (service_effects.use_egg): they hatch after egg_hatch_explores explores.
        # This branch used to push a pet straight away, so the incubator was dead code.
        from service_effects import use_egg
        return await use_egg(uid, item_id)
    return "nouse", None


# ---- drops & pity --------------------------------------------------------------
# Drop caps. Each one limits one stacking source; the stacked total is what made rare drops too common.
DROP_BONUS_CAP = 0.15   # faction, division, artifact, relic and pet drop bonuses, summed, count at most this much
WORLD_DROP_CAP = 1.5    # location (reishi) and event drop factor ceiling
LUCK_BOOST_CAP = 0.2    # luck from level and accessories: at most +20% on rare-and-up weights
RARE_MULT_CAP = 2.5     # rare and epic weights never get more than this multiplier
TOP_MULT_CAP = 1.5      # legendary and mythic get a gentler cap: the drop buff was lifting them too much


async def roll_drop(uid: int, source_mult: float = 1.0, weapon_chance: float = 0.1, floor_idx: int = 0, rng=random,
                    exact_idx: int = None):
    """One random item for this player. exact_idx: skip the rarity roll and pity, and give exactly that colour
    (dungeon-shop chests hold only their own colours)."""
    st = await game_settings()
    ch = await get_char(uid)
    if exact_idx is not None:
        return _pick_of_rarity(ch, int(exact_idx), weapon_chance=0.0, rng=rng)
    luck = ch.get("level", 1) // 20
    for k in ("acc_id", "charm_id"):
        luck += ALL.get(ch.get(k) or "", {}).get("stats", {}).get("luck", 0)
    boost = 1 + min(LUCK_BOOST_CAP, luck * 0.005)
    mult = float(st["drop_rate"]) * source_mult
    mult *= 1 + min(DROP_BONUS_CAP, player_bonus(ch, ALL, st)["drop"])
    try:
        mult *= min(WORLD_DROP_CAP, (await mods_for(ch["location"]))["drop"])
    except Exception:
        pass
    # rare-and-up weights take the whole stacked multiplier, but never more than RARE_MULT_CAP.
    # Before this cap, boss/elite x2 * faction + artifact drop bonus * world factor * luck could reach ~10x,
    # which is why Legendary and Mythic showed up almost every time.
    rare_mult = min(RARE_MULT_CAP, boost * mult)
    top_mult = min(TOP_MULT_CAP, rare_mult)
    weights = [w * (top_mult if i >= 4 else rare_mult if i >= 2 else 1.0) for i, w in enumerate(DROP_W)]
    idx = rng.choices(range(6), weights)[0]
    idx = max(idx, floor_idx)
    pity = dict(ch.get("pity") or {"rare": 0, "epic": 0, "legendary": 0})
    for name, tier_idx, thr in PITY:
        if pity.get(name, 0) + 1 >= thr and idx < tier_idx:
            idx = tier_idx
            break
    for name, tier_idx, thr in PITY:
        pity[name] = 0 if idx >= tier_idx else pity.get(name, 0) + 1
    await col("characters").update_one({"user_id": uid}, {"$set": {"pity": pity}})
    return _pick_of_rarity(ch, idx, weapon_chance, rng)


RACE_ARMOUR_SHARE = 0.25   # share of drops that are the player's own race armour
RACE_CARD_SHARE = 0.10     # ... and their race cards (Kidō cards for Shinigami / Visored, technique cards for the rest)


def _pick_of_rarity(ch: dict, idx: int, weapon_chance: float, rng=random):
    """An item of rarity index `idx` (falls back to lower colours only if that colour has nothing). Armour and cards
    are the player's own race's: other races' gear never drops for them."""
    from data_items import RACE_ARMOUR_BY_RARITY, race_cards
    race = (ch or {}).get("race")
    for i in range(idx, -1, -1):
        r = RARITIES[i]
        if rng.random() < weapon_chance and WEAPON_BY_RARITY[r]:
            return rng.choice(WEAPON_BY_RARITY[r])
        roll = rng.random()
        armour = (RACE_ARMOUR_BY_RARITY.get(race) or {}).get(r) or []
        if roll < RACE_ARMOUR_SHARE and armour:
            return rng.choice(armour)
        cards = race_cards(race, r) if race else []
        if roll < RACE_ARMOUR_SHARE + RACE_CARD_SHARE and cards:
            return rng.choice(cards)
        if BY_RARITY[r]:
            from data_items import pick_shared
            return pick_shared(r, rng)  # accessories keep their old share of drops
        if armour or cards:  # no shared item of this colour (red): the race's own armour or cards keep the colour
            return rng.choice(armour + cards)
    return rng.choice(BY_RARITY["Common"])


async def grant_item(uid: int, item_id: str) -> bool:
    return await inv_add(uid, item_id, 1)


# ---- NPC shop (Urahara) ---------------------------------------------------------
def shop_stock(day: str, race: str = None):
    """Urahara's stock of the day: 56 shared items plus 8 cards of the buyer's race (Kidō cards for Shinigami / Visored,
    technique cards for the rest), so nobody is offered cards they cannot use."""
    r = random.Random("shop" + day)
    pool = [i for i, x in ALL.items() if x["rarity"] in ("Common", "Uncommon", "Rare") and x["category"] in ("potion", "accessory", "book", "material")
            and not x.get("retired")]
    base = r.sample(pool, 56)
    if race:
        from data_items import race_cards
        cards = [c for rar in ("Common", "Uncommon", "Rare") for c in race_cards(race, rar)]
        if cards:
            base += random.Random(f"shop{day}{race}").sample(cards, min(8, len(cards)))
    return sorted(base)


async def price_mult() -> float:
    try:
        return (await mods_for("seireitei"))["price"]
    except Exception:
        return 1.0


async def shop_price(item_id: str) -> int:
    """Urahara's price: the base price moved by the world's Hollow Threat (scarcity)."""
    return max(1, int(ALL[item_id]["base_price"] * await price_mult()))


from engine_shop import SHOP_QTYS, bulk_discount  # noqa: E402  (pure, unit-tested)


async def shop_quote(item_id: str, qty: int = 1) -> tuple:
    """(unit price after discount, total, discount fraction). The total is what is charged, so the button and the charge always agree."""
    st = await game_settings()
    unit = await shop_price(item_id)
    disc = bulk_discount(qty, st)
    total = max(qty, int(unit * qty * (1 - disc)))
    return unit, total, disc


async def shop_buy(uid: int, item_id: str, day: str, qty: int = 1) -> str:
    qty = int(qty)
    ch = await get_char(uid)
    if item_id not in shop_stock(day, (ch or {}).get("race")):
        return "gone"
    if qty < 1 or qty > max(SHOP_QTYS):
        return "gone"
    _, total, _ = await shop_quote(item_id, qty)
    if not await add_coins(uid, -total, "shop_buy"):
        return "funds"
    if not await inv_add(uid, item_id, qty):
        await add_coins(uid, total, "shop_refund")
        return "full"
    log_event("shop", uid, f"از اوراهارا خرید: {iname(item_id, 'fa')} ×{qty} به قیمت {total:,} 🪙", item=item_id, price=total, qty=qty)
    return "ok"


async def npc_sell(uid: int, item_id: str, qty: int = 1):
    it = ALL.get(item_id)
    if not it:
        return 0
    if not await inv_remove(uid, item_id, qty):
        return 0
    st = await game_settings()
    pay = int(it["sell_price"] * qty * float(st["coin_rate"]))
    await add_coins(uid, max(1, pay), "npc_sell")
    log_event("shop", uid, f"فروش به فروشگاه: {iname(item_id, 'fa')} ×{qty} → {max(1, pay):,} 🪙", item=item_id)
    return max(1, pay)


# ---- market ----------------------------------------------------------------------
async def demand_index(item_id: str) -> float:
    d = await col("market_demand").find_one({"_id": item_id}) or {"idx": 1.0, "at": time.time()}
    idx = d["idx"] - 0.1 * int((time.time() - d["at"]) // 86400)
    return min(3.0, max(0.5, idx))


async def suggested_price(item_id: str) -> int:
    return max(1, int(ALL[item_id]["base_price"] * (1 + (await demand_index(item_id)) * 0.3) * await price_mult()))


async def market_create(uid: int, item_id: str, price: int, kind: str = "fixed", hours: int = None) -> str:
    st = await game_settings()
    it = ALL.get(item_id)
    if not it or not it.get("tradeable"):
        return "notrade"
    if price < max(1, it["base_price"] // 10) or price > it["base_price"] * 20:
        return "price"
    if await col("market_listings").count_documents({"seller": uid, "status": "active"}) >= int(st["market_slots"]):
        return "slots"
    if not await inv_remove(uid, item_id, 1):
        return "missing"
    hrs = hours or (24 if kind == "auction" else int(st["market_hours"]))
    await col("market_listings").insert_one({"_id": uuid.uuid4().hex[:10], "seller": uid, "item_id": item_id, "price": int(price),
                                              "kind": kind, "status": "active", "created_at": int(time.time()),
                                              "end_at": int(time.time()) + hrs * 3600, "bid": 0, "bidder": None})
    await bump_quest(uid, "market_sell", 1)
    log_event("market", uid, f"{'حراج' if kind == 'auction' else 'آگهی'} گذاشت: {iname(item_id, 'fa')} ({it['rarity']}) به قیمت {int(price):,} 🪙", item=item_id, price=int(price), listing=kind)
    return "ok"


async def market_cancel(uid: int, lid: str) -> str:
    d = await col("market_listings").find_one_and_update(
        {"_id": lid, "seller": uid, "status": "active", "bid": 0}, {"$set": {"status": "cancelled"}})
    if not d:
        return "cant"
    await inv_add(uid, d["item_id"], 1, force=True)
    log_event("market", uid, f"آگهی «{iname(d['item_id'], 'fa')}» را لغو کرد", item=d["item_id"])
    return "ok"


async def market_buy(uid: int, lid: str) -> str:
    st = await game_settings()
    d = await col("market_listings").find_one_and_update(
        {"_id": lid, "status": "active", "kind": "fixed", "seller": {"$ne": uid}, "end_at": {"$gt": int(time.time())}},
        {"$set": {"status": "sold", "buyer": uid, "sold_at": int(time.time())}}, return_document=ReturnDocument.AFTER)
    if not d:
        return "gone"
    fee = math.ceil(d["price"] * float(st["market_buyer_fee"]))

    async def revert():
        await col("market_listings").update_one({"_id": lid, "status": "sold", "buyer": uid}, {"$set": {"status": "active"}, "$unset": {"buyer": ""}})
    item_race = (ALL.get(d["item_id"]) or {}).get("race")
    if item_race and item_race != ((await get_char(uid)) or {}).get("race"):
        await revert()
        return "race"  # race armour / cards only go to a player of that race
    if not await add_coins(uid, -(d["price"] + fee), "market_buy"):
        await revert()
        return "funds"
    if not await inv_add(uid, d["item_id"], 1):
        await add_coins(uid, d["price"] + fee, "market_refund")
        await revert()
        return "full"
    await add_coins(d["seller"], d["price"] - int(d["price"] * float(st["market_seller_fee"])), "market_sale")
    await col("market_demand").update_one({"_id": d["item_id"]}, {"$set": {"idx": min(3.0, (await demand_index(d["item_id"])) + 0.05), "at": time.time()}}, upsert=True)
    await bump_quest(uid, "market_buy", 1)
    log_event("market", uid, f"خرید از بازار: {iname(d['item_id'], 'fa')} به قیمت {d['price']:,} 🪙 (فروشنده: {d['seller']})", item=d["item_id"], price=d["price"], seller=d["seller"])
    return "ok"


async def auction_bid(uid: int, lid: str, amount: int) -> str:
    st = await game_settings()
    now = int(time.time())
    d = await col("market_listings").find_one({"_id": lid, "kind": "auction", "status": "active"})
    if not d or d["end_at"] <= now or d["seller"] == uid:
        return "gone"
    low = d["price"] if not d["bid"] else math.ceil(d["bid"] * 1.05)
    if amount < low:
        return "low"
    if d.get("bidder") == uid:
        return "own"
    if not await add_coins(uid, -amount, "auction_escrow"):
        return "funds"
    new_end = now + int(st["auction_extend_seconds"]) if d["end_at"] - now <= int(st["auction_snipe_seconds"]) else d["end_at"]
    r = await col("market_listings").update_one({"_id": lid, "status": "active", "bid": d["bid"], "end_at": d["end_at"]},
                                                {"$set": {"bid": int(amount), "bidder": uid, "end_at": new_end}})
    if not r.modified_count:
        await add_coins(uid, amount, "auction_refund")
        return "race"
    if d.get("bidder"):
        await add_coins(d["bidder"], d["bid"], "auction_outbid")
    log_event("market", uid, f"پیشنهاد در حراج: {iname(d['item_id'], 'fa')} — {int(amount):,} 🪙", item=d["item_id"], price=int(amount))
    return "ok"


async def settle_listings():
    """Close finished auctions and expire old listings (idempotent, scheduler-run)."""
    st = await game_settings()
    now = int(time.time())
    while True:
        d = await col("market_listings").find_one_and_update({"status": "active", "end_at": {"$lte": now}}, {"$set": {"status": "closing"}})
        if not d:
            break
        if d["kind"] == "auction" and d.get("bidder"):
            await inv_add(d["bidder"], d["item_id"], 1, force=True)
            await add_coins(d["seller"], d["bid"] - int(d["bid"] * float(st["market_seller_fee"])), "auction_sale")
            await col("market_listings").update_one({"_id": d["_id"]}, {"$set": {"status": "sold", "buyer": d["bidder"]}})
            log_event("market", d["bidder"], f"برنده‌ی حراج شد: {iname(d['item_id'], 'fa')} با {d['bid']:,} 🪙 (فروشنده: {d['seller']})", item=d["item_id"], price=d["bid"], seller=d["seller"])
        else:
            await inv_add(d["seller"], d["item_id"], 1, force=True)
            await col("market_listings").update_one({"_id": d["_id"]}, {"$set": {"status": "expired"}})


# ---- gacha ------------------------------------------------------------------------
async def gacha_pull(uid: int, n: int = 1):
    st = await game_settings()
    if await try_cooldown(f"gacha:{uid}", 2):
        return None, "wait"
    cost = int(st["gacha_cost"]) * n
    if not await add_coins(uid, -cost, "gacha"):
        return None, "funds"
    g = await gacha_doc(uid)
    # Lifetime Mythic count from summons. Players who summoned before this counter existed start from the Mythic
    # characters they already own (Mythic items were never tracked, so they are not counted).
    if "mythic" not in g:
        g["mythic"] = sum(int(c) for cid, c in (g.get("chars") or {}).items() if (CHAR_BY_ID.get(cid) or {}).get("rarity") == "Mythic")
    mythic_cap = int(st["gacha_mythic_cap"])  # 0 = no limit
    rng = random.Random()
    results = []
    won = {}  # character id -> copies won in this pull (written with $inc, see below)
    from data_extras2 import SUMMON_JACKPOT, SUMMON_JACKPOT_COINS
    for _ in range(n):
        if random.random() < SUMMON_JACKPOT:  # 1 in 10,000: the summon jackpot (coins, a red accessory and an Inner World Key)
            from data_extras2 import INNER_KEY
            from data_items import MYTHIC_ACCESSORIES
            jp = rng.choice(MYTHIC_ACCESSORIES) if MYTHIC_ACCESSORIES else None
            await add_coins(uid, SUMMON_JACKPOT_COINS, "summon_jackpot")
            for iid in [x for x in (jp, INNER_KEY) if x]:
                await inv_add(uid, iid, 1, force=True)
            results.append({"t": "jackpot", "id": jp, "rar": "Mythic", "coins": SUMMON_JACKPOT_COINS})
            log_event("summon_jackpot", uid, f"🎰 جک‌پات احضار! {SUMMON_JACKPOT_COINS} سکه + {jp}", item=jp)
            continue
        idx = rng.choices(range(6), list(GACHA_RATES.values()))[0]
        g["since_rare"] += 1
        g["since_leg"] += 1
        if g["since_leg"] >= int(st["gacha_pity_legendary"]) and idx < 4:
            idx = 4
        elif g["since_rare"] >= int(st["gacha_pity_rare"]) and idx < 2:
            idx = 2
        if idx == 5 and mythic_cap > 0 and g["mythic"] >= mythic_cap:
            idx = 4  # Mythic limit reached: this roll becomes a Legendary
        if idx >= 2:
            g["since_rare"] = 0
        if idx >= 4:
            g["since_leg"] = 0
        rar = RARITIES[idx]
        pool = [c["_id"] for c in CHARS if c["rarity"] == rar]
        if pool and rng.random() < 0.6:
            cid = rng.choice(pool)
            g["chars"][cid] = g["chars"].get(cid, 0) + 1
            won[cid] = won.get(cid, 0) + 1
            results.append({"t": "char", "id": cid, "rar": rar, "copies": g["chars"][cid]})
        else:
            from data_items import MYTHIC_ACCESSORIES, pick_shared
            if rar == "Mythic" and MYTHIC_ACCESSORIES:  # a red item roll pays one of the red accessories
                iid = rng.choice(MYTHIC_ACCESSORIES)
            else:
                iid = pick_shared(rar if BY_RARITY[rar] else "Legendary", rng)
            await inv_add(uid, iid, 1, force=True)
            results.append({"t": "item", "id": iid, "rar": ALL[iid]["rarity"]})
        if results[-1]["rar"] == "Mythic":  # count what the player really received (a Mythic roll can land on a lower item)
            g["mythic"] += 1
    g["total"] += n
    # Only what this pull changed is written: copies and the total go in with $inc. The whole document used to be
    # written back, so a character sold while the pull was running came back (sold for coins and kept).
    await col("gacha").update_one({"user_id": uid},
                                  {"$inc": {**{f"chars.{cid}": k for cid, k in won.items()}, "total": n},
                                   "$set": {"since_rare": g["since_rare"], "since_leg": g["since_leg"], "mythic": g["mythic"]}},
                                  upsert=True)
    await bump_quest(uid, "gacha_pull", n)
    top = [r for r in results if r["rar"] in ("Epic", "Legendary", "Mythic")]
    names = "، ".join((CHAR_BY_ID[r["id"]]["name_fa"] if r["t"] == "char" else iname(r["id"], "fa")) + f" ({r['rar']})" for r in top[:6])
    log_event("gacha", uid, f"{n} احضار ({cost:,} 🪙)" + (f" — نایاب‌ها: {names}" if names else ""), n=n)
    return results, "ok"


async def gacha_doc(uid: int) -> dict:
    g = await col("gacha").find_one({"user_id": uid}) or {"user_id": uid}
    for k, v in (("since_rare", 0), ("since_leg", 0), ("chars", {}), ("total", 0)):
        g.setdefault(k, v)  # a pull that only gave items creates the document without "chars"
    return g


# Selling summoned characters: the whole stack (every copy) goes for this much per copy, by rarity.
# Kept well under the price of a pull (gacha_cost), so selling never beats summoning. Coins only, never premium.
CHAR_SELL_PER_COPY = {"Common": 100, "Uncommon": 200, "Rare": 400, "Epic": 800, "Legendary": 1600, "Mythic": 3000}


def char_sell_value(cid: str, copies: int, coin_rate: float = 1.0) -> int:
    base = CHAR_SELL_PER_COPY.get(CHAR_BY_ID[cid]["rarity"], 100)
    return max(1, int(base * max(1, int(copies)) * float(coin_rate)))


async def sell_character(uid: int, cid: str, qty=None) -> tuple:
    """Sell copies of a summoned character: qty copies, or all of them when qty is None/'all'/>= what you own.
    Selling every copy removes it from the party. Returns (status, coins)."""
    g = await gacha_doc(uid)
    copies = int(g["chars"].get(cid, 0) or 0)
    if copies <= 0:
        return "notowned", 0
    n = copies if qty in (None, "all") else max(1, min(int(qty), copies))
    st = await game_settings()
    pay = char_sell_value(cid, n, float(st.get("coin_rate", 1.0)))
    # one atomic claim on the exact copy count: a double tap or a second window cannot sell it twice
    change = {"$unset": {f"chars.{cid}": ""}} if n >= copies else {"$inc": {f"chars.{cid}": -n}}
    r = await col("gacha").update_one({"user_id": uid, f"chars.{cid}": copies}, change)
    if not r.modified_count:
        return "retry", 0
    if n >= copies:
        await col("characters").update_one({"user_id": uid}, {"$pull": {"party": cid}})
    await add_coins(uid, pay, "char_sell")
    log_event("gacha", uid, f"فروش احضار {CHAR_BY_ID[cid]['name_fa']} ×{n} → {pay:,} 🪙", char=cid, copies=n)
    return "ok", pay


async def toggle_party(uid: int, cid: str) -> str:
    g = await gacha_doc(uid)
    ch = await get_char(uid)
    if cid not in g["chars"]:
        return "notowned"
    party = list(ch.get("party", []))
    if cid in party:
        party.remove(cid)
        res = "removed"
    elif len(party) >= 3:
        return "full"
    else:
        party.append(cid)
        res = "added"
    await col("characters").update_one({"user_id": uid}, {"$set": {"party": party}})
    return res


def party_bonus(party: list, chars: dict) -> dict:
    out = {}
    for cid in party:
        if cid in chars and cid in CHAR_BY_ID:
            for k, v in char_bonus(cid, chars[cid]).items():
                out[k] = out.get(k, 0) + v
    return out


# ---- forge (weapon +1..+10) --------------------------------------------------------------------
FORGE_CHANCE = [100, 95, 90, 80, 70, 60, 50, 40, 30, 20]


def forge_cost(weapon_id: str, plus: int):
    need = plus + 1
    return int(ALL[weapon_id]["base_price"] * 0.18 * need) + 220 * need, need  # was 0.25 x price + 300 per level


async def forge(uid: int):
    if await try_cooldown(f"forge:{uid}", 2):
        return "wait", 0
    ch = await get_char(uid)
    wid = ch.get("weapon_id")
    if wid not in ALL:
        return "noweapon", 0  # the race weapon has not been chosen yet
    plus = (ch.get("weapon_plus") or {}).get(wid, 0)
    if plus >= 10:
        return "max", plus
    coins, need = forge_cost(wid, plus)
    inv = await inv_get(uid)
    mats = sorted([i for i, q in inv["items"].items() if q > 0 and ALL.get(i, {}).get("category") == "material"], key=lambda i: ALL[i]["base_price"])
    val = {i: forge_value(ALL[i]["rarity"]) for i in mats}
    if sum(inv["items"][i] * val[i] for i in mats) < need:
        return "mats", need
    from service_adventure import give_back_stones, stones_needed, take_stones
    if stones_needed(plus) and int(inv["items"].get("it_t001", 0)) < stones_needed(plus):
        return "stone", stones_needed(plus)  # +6 and up need Tempering Stones
    if not await take_stones(uid, plus):
        return "stone", stones_needed(plus)
    if not await add_coins(uid, -coins, "forge"):
        await give_back_stones(uid, plus)
        return "funds", coins
    left = need
    for i in mats:
        take = min(inv["items"][i], -(-left // val[i]))
        if take and await inv_remove(uid, i, take):
            left -= take * val[i]
        if left <= 0:
            break
    if random.random() * 100 < FORGE_CHANCE[plus]:
        await col("characters").update_one({"user_id": uid}, {"$set": {f"weapon_plus.{wid}": plus + 1}})
        return "ok", plus + 1
    return "fail", plus
