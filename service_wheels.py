"""Wheel service (گردونه‌ها): Soul Core wallet, spin cost, pity counters and rewards.

Write rules (same as the rest of the bot):
- the spin count is incremented atomically first; that count decides the tier, so two parallel
  taps cannot both get the cheap price;
- the Soul Core cost is taken with a conditional update (`cores >= cost`); if it fails, the spin
  count is rolled back and nothing is granted;
- the free daily spin goes through `bump_counter`, which is capped and race-safe.
The rarity is decided here, before any animation, so the animation can never change a result.
"""
import random

from pymongo import ReturnDocument

from data_wheels import (
    TOKEN, RARITY_ICON, WHEEL_ITEM_CAT, can_spin, next_streaks, reward_for, resolve_rarity,
    spin_cost, wheel_by_id,
)
from data_skins import (KATANA_CHANCE_DEFAULT, KATANA_CHANCE_KEY, SKIN_CHANCE_DEFAULT, SKIN_CHANCE_KEY, SKIN_RARITY_OF,
                        skin_extra, wheel_boost)
from database import bump_counter, col, counter_get, game_settings, try_cooldown
from service_cores import grant_cores, spend_cores
from data_world import day_id
from service_economy import inv_add
from service_extras import pick_item
from service_player import add_coins, add_xp, get_char
from service_skins import grant_skin, pick_skin

WALLET = "wheel_wallet"  # one doc per user: {_id, cores, spins: {wid: n}, pity: {wid: {leg, myth}}}


def discounted(cost: int, disc: float) -> int:
    """Skin discount on a paid spin: never below 1, never more than the skin cap (already capped in skin_extra)."""
    if cost <= 0 or disc <= 0:
        return cost
    return max(1, int(round(cost * (1.0 - disc))))


def pity_at(base: int, closer: int) -> int:
    """A pity threshold of 0 stays off; otherwise a skin pulls it closer but never below 5 spins."""
    return base if base <= 0 else max(5, base - int(closer))


async def bonus_prize(uid: int, wid: str, rarity: str, ch: dict, st: dict, rng=random):
    """Extra prize that rides on top of a big result: a skin (any wheel) or a katana boost (free colour for the race weapon).
    Returns None or a dict. Never raises: a failed bonus must not undo a paid, decided spin."""
    try:
        if not ch or rarity not in SKIN_RARITY_OF:
            return None
        w = wheel_by_id(wid) or {}
        sk_mult, kt_mult = wheel_boost(wid, w.get("cat", ""))
        p = float(st.get(SKIN_CHANCE_KEY[rarity], SKIN_CHANCE_DEFAULT[rarity])) * sk_mult
        if rng.random() < min(0.95, p):
            sid = pick_skin(SKIN_RARITY_OF[rarity], ch.get("skins_owned"), rng)
            if sid:
                status, coins = await grant_skin(uid, sid, f"wheel:{wid}")
                if status in ("new", "dup"):
                    return {"kind": "skin", "skin": sid, "status": status, "coins": coins}
        if rarity in KATANA_CHANCE_KEY:
            pk = float(st.get(KATANA_CHANCE_KEY[rarity], KATANA_CHANCE_DEFAULT[rarity])) * kt_mult
            if rng.random() < min(0.95, pk):
                from service_raceweapon import free_ascend
                status, info = await free_ascend(uid)
                if status == "ok":
                    return {"kind": "katana", "weapon": info}
                # the weapon could not rise (level gate, max colour, no weapon): pay evolution fuel instead, never an empty prize
                from data_items import EVO_BY_RARITY
                pool = EVO_BY_RARITY.get("Rare") or EVO_BY_RARITY.get("Common") or []
                if pool:
                    item = rng.choice(pool)
                    if await inv_add(uid, item, 1, force=True):
                        return {"kind": "katana_relic", "item": item, "why": status}
    except Exception:
        import logging
        logging.getLogger("senka.wheel").exception("wheel bonus prize failed for %s", uid)
    return None


async def wallet(uid: int) -> dict:
    doc = await col(WALLET).find_one({"_id": uid}) or {}
    return {"cores": int(doc.get("cores", 0)), "spins": doc.get("spins") or {}, "pity": doc.get("pity") or {}}


async def wheel_info(uid: int, wid: str) -> dict:
    """Everything the wheel page needs, read-only."""
    st = await game_settings()
    w = await wallet(uid)
    done = int(w["spins"].get(wid, 0))
    p = w["pity"].get(wid, {})
    used_free = await counter_get(f"wheel2:free:{uid}:{day_id()}")
    return {
        "cores": w["cores"],
        "done": done,
        "next_cost": spin_cost(wid, done + 1),
        "free_left": max(0, int(st["wheel_free_daily"]) - used_free),
        "leg": int(p.get("leg", 0)), "myth": int(p.get("myth", 0)),
        "leg_at": int(st["pity_leg"]), "myth_at": int(st["pity_myth"]),
    }


async def spin(uid: int, wid: str, owner_id: int):
    """Returns (status, result). status: ok | off | bad | locked | wait | funds."""
    st = await game_settings()
    if not st["wheel2_enabled"]:
        return "off", None
    if wheel_by_id(wid) is None:
        return "bad", None
    if not can_spin(wid, uid, owner_id):
        return "locked", None
    if await try_cooldown(f"wheel2:cd:{uid}", 2):
        return "wait", None

    # 1) count this spin atomically; the count is what sets the price tier
    doc = await col(WALLET).find_one_and_update(
        {"_id": uid}, {"$inc": {f"spins.{wid}": 1}}, upsert=True, return_document=ReturnDocument.AFTER)
    n = int((doc.get("spins") or {}).get(wid, 1))

    # 2) free daily spin (capped counter) or paid spin (conditional debit); the equipped skin may give a small discount
    ch = await get_char(uid)
    ex = skin_extra(ch)
    free = await bump_counter(f"wheel2:free:{uid}:{day_id()}", 1, int(st["wheel_free_daily"]))
    cost = 0 if free else discounted(spin_cost(wid, n), ex["wheel"])
    if cost:
        if not await spend_cores(uid, cost, f"spin:{wid}"):
            await col(WALLET).update_one({"_id": uid}, {"$inc": {f"spins.{wid}": -1}})
            return "funds", None

    # 3) rarity with pity, then update the streaks
    w = await wallet(uid)
    p = w["pity"].get(wid, {})
    leg0, myth0 = int(p.get("leg", 0)), int(p.get("myth", 0))
    rarity = resolve_rarity(random, leg0, myth0, pity_at(int(st["pity_leg"]), ex["pity"]), pity_at(int(st["pity_myth"]), ex["pity"]))
    leg1, myth1 = next_streaks(rarity, leg0, myth0)
    await col(WALLET).update_one({"_id": uid},
                                 {"$set": {f"pity.{wid}.leg": leg1, f"pity.{wid}.myth": myth1}}, upsert=True)

    # 4) rewards (the prize is decided; everything below is only granting it)
    lvl = int(ch["level"]) if ch else 1
    cr = float(st["coin_rate"])
    coins = xp = cores = 0
    item = None
    if rarity == "Common":
        coins = int((80 + lvl * 10) * cr)
    elif rarity == "Rare":
        xp = 80 + lvl * 15
    elif rarity == "Epic":
        coins = int((200 + lvl * 20) * cr)
        item = pick_item("material", [1, 2, 2, 3])
    elif rarity == "Legendary":
        coins = int((600 + lvl * 40) * cr)
        item = pick_item("relic", [1, 2, 2, 3])
    elif rarity == "Mythic":
        coins = int((3000 + lvl * 120) * cr)
        item = pick_item("relic", [2, 3, 3, 4])
    elif rarity == "Legacy":
        coins = int((12000 + lvl * 250) * cr)
        item = pick_item("relic", [4])

    if rarity in ("Mythic", "Legacy") and random.random() < (0.30 if rarity == "Mythic" else 0.60):
        from data_mythic import MYTHIC_ITEM_IDS  # themed treasure: one of the ten red items (potion, charm, egg, relic...)
        item = random.choice(MYTHIC_ITEM_IDS)
    if wid == "w_armor" and ch and rarity in ("Rare", "Epic", "Legendary", "Mythic", "Legacy"):
        # the armour wheel really pays armour: a random piece of the player's own race armour, colour by the spin
        from service_racegear import random_armour
        colour = {"Rare": 1, "Epic": random.choice((2, 3)), "Legendary": 4, "Mythic": 5, "Legacy": 5}[rarity]
        item = random_armour(ch["race"], colour)
    elif wid == "w_weapon" and ch and rarity in ("Legendary", "Mythic", "Legacy"):
        # blades no longer drop: the weapon wheel pays evolution relics, the fuel that raises a race weapon's colour
        from data_items import EVO_BY_RARITY
        pool = EVO_BY_RARITY[{"Legendary": "Rare", "Mythic": "Epic", "Legacy": "Epic"}[rarity]] or EVO_BY_RARITY["Common"]
        item = random.choice(pool)
    cat = WHEEL_ITEM_CAT.get(wid)
    if cat and item and rarity in ("Epic", "Legendary", "Mythic", "Legacy"):
        idx = {"Epic": [1, 2, 2, 3], "Legendary": [2, 3, 3, 4], "Mythic": [3, 4, 4, 5], "Legacy": [4, 5]}[rarity]
        item = pick_item(cat, idx) or item  # the wheel's own kind of item; the generic pick stays as a fallback
    in_bag = False
    if coins:
        await add_coins(uid, coins, "wheel2")
    if xp:
        await add_xp(uid, xp, "wheel2")
    if item:
        in_bag = bool(await inv_add(uid, item, 1, force=True))
    if cores:
        await grant_cores(uid, cores, f"wheel:{wid}")
    bonus = await bonus_prize(uid, wid, rarity, ch, st)

    icon, fa, en = reward_for(rarity, wid)
    w_after = await wallet(uid)
    return "ok", {
        "wid": wid, "n": n, "cost": cost, "free": bool(free), "rarity": rarity,
        "rarity_icon": RARITY_ICON[rarity], "icon": icon, "fa": fa, "en": en,
        "coins": coins, "xp": xp, "cores_won": cores, "item": item, "in_bag": in_bag, "bonus": bonus,
        "cores_left": w_after["cores"], "leg": leg1, "myth": myth1,
        "token": TOKEN,
    }
