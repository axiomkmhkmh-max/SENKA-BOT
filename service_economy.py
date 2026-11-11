"""Inventory, equipment, drops, NPC shop, player market, auctions, gacha."""
import math
import random
import time
import uuid

from pymongo import ReturnDocument

from data_chars import CHAR_BY_ID, CHARS, GACHA_RATES, char_bonus
from data_items import ALL, BY_RARITY, WEAPON_BY_RARITY
from data_weapons import RARITIES
from database import col, game_settings, try_cooldown
from service_player import add_coins, add_xp, bump_quest, get_char

SLOT_FIELD = {"weapon": "weapon_id", "armor": "armor_id", "ring": "acc_id", "necklace": "charm_id"}
PETS = [("Spirit Fox", "روباه روحی"), ("Moon Cat", "گربه‌ی ماه"), ("Ember Wisp", "شراره‌ی زنده"),
        ("Tide Serpent", "مار جزرومد"), ("Hollow Pup", "توله‌ی تهی"), ("Storm Hawk", "عقاب توفان")]
DROP_W = [50, 25, 15, 7, 2.5, 0.5]
PITY = (("legendary", 4, 1000), ("epic", 3, 200), ("rare", 2, 50))


# ---- inventory ---------------------------------------------------------------
async def inv_get(uid: int) -> dict:
    d = await col("inventories").find_one({"user_id": uid})
    if not d:
        await col("inventories").update_one({"user_id": uid}, {"$setOnInsert": {"user_id": uid, "items": {}, "capacity": 50}}, upsert=True)
        d = await col("inventories").find_one({"user_id": uid})
    return d


def slots_used(items: dict) -> int:
    return sum(math.ceil(q / max(1, ALL[i]["stack_max"])) for i, q in items.items() if q > 0 and i in ALL)


async def inv_add(uid: int, item_id: str, qty: int = 1, force: bool = False) -> bool:
    if item_id not in ALL or qty <= 0:
        return False
    inv = await inv_get(uid)
    cur = inv["items"].get(item_id, 0)
    sm = max(1, ALL[item_id]["stack_max"])
    need = math.ceil((cur + qty) / sm) - math.ceil(cur / sm)
    if not force and slots_used(inv["items"]) + need > inv.get("capacity", 50):
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
    if t == "xp":
        if not await inv_remove(uid, item_id, 1):
            return "missing", None
        _, _, got = await add_xp(uid, eff["amount"], "book", apply_rate=False)
        return "ok", got
    if t == "pet":
        if len(ch.get("pets", [])) >= 12:
            return "petfull", None
        if not await inv_remove(uid, item_id, 1):
            return "missing", None
        sp = random.randrange(len(PETS))
        await col("characters").update_one({"user_id": uid}, {"$push": {"pets": {"sp": sp, "tier": eff["tier"]}}})
        return "ok", sp
    return "nouse", None


# ---- drops & pity --------------------------------------------------------------
async def roll_drop(uid: int, source_mult: float = 1.0, weapon_chance: float = 0.1, floor_idx: int = 0, rng=random):
    st = await game_settings()
    ch = await get_char(uid)
    luck = ch.get("level", 1) // 20
    for k in ("acc_id", "charm_id"):
        luck += ALL.get(ch.get(k) or "", {}).get("stats", {}).get("luck", 0)
    boost = 1 + min(0.5, luck * 0.005)
    mult = float(st["drop_rate"]) * source_mult
    weights = [w * (boost * mult if i >= 2 else 1.0) for i, w in enumerate(DROP_W)]
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
    for i in range(idx, -1, -1):
        r = RARITIES[i]
        if rng.random() < weapon_chance and WEAPON_BY_RARITY[r]:
            return rng.choice(WEAPON_BY_RARITY[r])
        if BY_RARITY[r]:
            return rng.choice(BY_RARITY[r])
    return rng.choice(BY_RARITY["Common"])


async def grant_item(uid: int, item_id: str) -> bool:
    return await inv_add(uid, item_id, 1)


# ---- NPC shop (Urahara) ---------------------------------------------------------
def shop_stock(day: str):
    r = random.Random("shop" + day)
    pool = [i for i, x in ALL.items() if x["rarity"] in ("Common", "Uncommon", "Rare") and x["category"] in ("potion", "armor", "accessory", "weapon", "kido_card", "book", "material")]
    return sorted(r.sample(pool, 64))


async def shop_buy(uid: int, item_id: str, day: str) -> str:
    if item_id not in shop_stock(day):
        return "gone"
    price = ALL[item_id]["base_price"]
    if not await add_coins(uid, -price, "shop_buy"):
        return "funds"
    if not await inv_add(uid, item_id, 1):
        await add_coins(uid, price, "shop_refund")
        return "full"
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
    return max(1, pay)


# ---- market ----------------------------------------------------------------------
async def demand_index(item_id: str) -> float:
    d = await col("market_demand").find_one({"_id": item_id}) or {"idx": 1.0, "at": time.time()}
    idx = d["idx"] - 0.1 * int((time.time() - d["at"]) // 86400)
    return min(3.0, max(0.5, idx))


async def suggested_price(item_id: str) -> int:
    return max(1, int(ALL[item_id]["base_price"] * (1 + (await demand_index(item_id)) * 0.3)))


async def market_create(uid: int, item_id: str, price: int, kind: str = "fixed", hours: int = None) -> str:
    st = await game_settings()
    it = ALL.get(item_id)
    if not it or not it.get("tradeable"):
        return "notrade"
    if kind == "fixed" and it["rarity"] in ("Epic", "Legendary", "Mythic"):
        return "auction_only"
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
    return "ok"


async def market_cancel(uid: int, lid: str) -> str:
    d = await col("market_listings").find_one_and_update(
        {"_id": lid, "seller": uid, "status": "active", "bid": 0}, {"$set": {"status": "cancelled"}})
    if not d:
        return "cant"
    await inv_add(uid, d["item_id"], 1, force=True)
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
    g = await col("gacha").find_one({"user_id": uid}) or {"user_id": uid, "since_rare": 0, "since_leg": 0, "chars": {}, "total": 0}
    rng = random.Random()
    results = []
    for _ in range(n):
        idx = rng.choices(range(6), list(GACHA_RATES.values()))[0]
        g["since_rare"] += 1
        g["since_leg"] += 1
        if g["since_leg"] >= int(st["gacha_pity_legendary"]) and idx < 4:
            idx = 4
        elif g["since_rare"] >= int(st["gacha_pity_rare"]) and idx < 2:
            idx = 2
        if idx >= 2:
            g["since_rare"] = 0
        if idx >= 4:
            g["since_leg"] = 0
        rar = RARITIES[idx]
        pool = [c["_id"] for c in CHARS if c["rarity"] == rar]
        if pool and rng.random() < 0.6:
            cid = rng.choice(pool)
            g["chars"][cid] = g["chars"].get(cid, 0) + 1
            results.append({"t": "char", "id": cid, "rar": rar, "copies": g["chars"][cid]})
        else:
            wp = WEAPON_BY_RARITY[rar]
            items = BY_RARITY[rar] or BY_RARITY["Legendary"]
            iid = rng.choice(wp) if wp and rng.random() < 0.4 else rng.choice(items)
            await inv_add(uid, iid, 1, force=True)
            results.append({"t": "item", "id": iid, "rar": ALL[iid]["rarity"]})
    g["total"] += n
    g.pop("_id", None)
    await col("gacha").update_one({"user_id": uid}, {"$set": g}, upsert=True)
    await bump_quest(uid, "gacha_pull", n)
    return results, "ok"


async def gacha_doc(uid: int) -> dict:
    return await col("gacha").find_one({"user_id": uid}) or {"user_id": uid, "since_rare": 0, "since_leg": 0, "chars": {}, "total": 0}


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
    return int(ALL[weapon_id]["base_price"] * 0.25 * need) + 300 * need, need


async def forge(uid: int):
    if await try_cooldown(f"forge:{uid}", 2):
        return "wait", 0
    ch = await get_char(uid)
    wid = ch.get("weapon_id")
    plus = (ch.get("weapon_plus") or {}).get(wid, 0)
    if plus >= 10:
        return "max", plus
    coins, need = forge_cost(wid, plus)
    inv = await inv_get(uid)
    mats = sorted([i for i, q in inv["items"].items() if q > 0 and ALL.get(i, {}).get("category") == "material"], key=lambda i: ALL[i]["base_price"])
    if sum(inv["items"][i] for i in mats) < need:
        return "mats", need
    if not await add_coins(uid, -coins, "forge"):
        return "funds", coins
    left = need
    for i in mats:
        take = min(inv["items"][i], left)
        if take and await inv_remove(uid, i, take):
            left -= take
        if left <= 0:
            break
    if random.random() * 100 < FORGE_CHANCE[plus]:
        await col("characters").update_one({"user_id": uid}, {"$set": {f"weapon_plus.{wid}": plus + 1}})
        return "ok", plus + 1
    return "fail", plus
