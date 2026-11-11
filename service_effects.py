"""Async item-effect actions on top of effects.py: relics, cosmetics, tomes, eggs/pets,
evolution and crafting. Every write is a conditional single-document update so a double
tap can never duplicate an item or a reward."""
import random
import time

from pymongo import ReturnDocument

from data_crafting import get_recipe, plan
from data_items import ALL
from data_races import LEVEL_GATES, RACES
from database import col, game_settings, try_cooldown
from effects import (BUFF_KEYS, active_buffs, evo_can, evo_stage_cap, passive_mods, relic_slots)
from service_economy import PETS, inv_add, inv_get, inv_remove
from service_player import add_coins, get_char, today

PET_CAP = 12


async def passives(ch: dict, st: dict = None) -> dict:
    return passive_mods(ch, ALL, st or await game_settings())


# ---- relics ---------------------------------------------------------------------------------------------------
async def equip_relic(uid: int, item_id: str) -> str:
    st, ch = await game_settings(), await get_char(uid)
    slots = relic_slots(ch["level"], st)
    if slots <= 0:
        return "relic_level"
    if item_id in (ch.get("relics") or []):
        return "already"
    if len(ch.get("relics") or []) >= slots:
        return "relic_full"
    if not await inv_remove(uid, item_id, 1):
        return "missing"
    r = await col("characters").update_one(
        {"user_id": uid, "relics": {"$ne": item_id}, f"relics.{slots - 1}": {"$exists": False}}, {"$push": {"relics": item_id}})
    if not r.modified_count:
        await inv_add(uid, item_id, 1, force=True)
        return "retry"
    return "ok"


async def unequip_relic(uid: int, item_id: str) -> str:
    if not await inv_add(uid, item_id, 1):
        return "full"
    r = await col("characters").update_one({"user_id": uid, "relics": item_id}, {"$pull": {"relics": item_id}})
    if not r.modified_count:
        await inv_remove(uid, item_id, 1)
        return "empty"
    return "ok"


# ---- cosmetics -----------------------------------------------------------------------------------------------
async def equip_cosmetic(uid: int, item_id: str) -> str:
    ch = await get_char(uid)
    slot = ALL[item_id]["effect"]["slot"]
    cur = (ch.get("cosmetic") or {}).get(slot)
    if cur == item_id:
        return "already"
    if not await inv_remove(uid, item_id, 1):
        return "missing"
    r = await col("characters").update_one({"user_id": uid, f"cosmetic.{slot}": cur}, {"$set": {f"cosmetic.{slot}": item_id}})
    if not r.modified_count:
        await inv_add(uid, item_id, 1, force=True)
        return "retry"
    if cur:
        await inv_add(uid, cur, 1, force=True)
    return "ok"


async def unequip_cosmetic(uid: int, slot: str) -> str:
    ch = await get_char(uid)
    cur = (ch.get("cosmetic") or {}).get(slot)
    if not cur:
        return "empty"
    if not await inv_add(uid, cur, 1):
        return "full"
    r = await col("characters").update_one({"user_id": uid, f"cosmetic.{slot}": cur}, {"$set": {f"cosmetic.{slot}": None}})
    if not r.modified_count:
        await inv_remove(uid, cur, 1)
        return "retry"
    return "ok"


async def equip_special(uid: int, item_id: str) -> str:
    sub = ALL[item_id]["subtype"]
    return await (equip_relic if sub == "relic" else equip_cosmetic)(uid, item_id)


# ---- tomes (books) & eggs ----------------------------------------------------------------------------------
async def use_tome(uid: int, item_id: str):
    import math
    eff, ch, st = ALL[item_id]["effect"], await get_char(uid), await game_settings()
    if eff["kind"] == "kido":
        need = math.ceil(eff["num"] * 0.8)
        if ch["level"] < need:
            return "level", need
        if eff["num"] in ch["kido"][eff["branch"]]:
            return "known", None
        if not await inv_remove(uid, item_id, 1):
            return "missing", None
        await col("characters").update_one({"user_id": uid}, {"$addToSet": {f"kido.{eff['branch']}": eff["num"]}})
        return "ok", eff["num"]
    key = eff["key"]
    if key not in BUFF_KEYS:
        return "nouse", None
    cur = active_buffs(ch).get(key, 0)
    if cur > eff["pct"]:
        return "stronger", int(cur)
    if not await inv_remove(uid, item_id, 1):
        return "missing", None
    until = int(time.time()) + int(st["book_buff_minutes"]) * 60
    await col("characters").update_one({"user_id": uid}, {"$set": {f"buffs.{key}": {"pct": eff["pct"], "until": until}}})
    return "ok", int(eff["pct"])


async def use_egg(uid: int, item_id: str):
    eff, ch, st = ALL[item_id]["effect"], await get_char(uid), await game_settings()
    if len(ch.get("pets") or []) >= PET_CAP:
        return "petfull", None
    explores = int(st["egg_hatch_explores"])
    if explores > 0 and ch.get("incubator"):
        return "incubating", ch["incubator"]["left"]
    if not await inv_remove(uid, item_id, 1):
        return "missing", None
    role = eff.get("role", "fang")
    if explores <= 0:
        sp = random.randrange(len(PETS))
        await col("characters").update_one({"user_id": uid}, {"$push": {"pets": {"sp": sp, "tier": eff["tier"], "role": role}}})
        return "ok", sp
    r = await col("characters").update_one({"user_id": uid, "incubator": {"$exists": False}},
                                           {"$set": {"incubator": {"tier": eff["tier"], "role": role, "left": explores}}})
    if not r.modified_count:
        await inv_add(uid, item_id, 1, force=True)
        return "incubating", None
    return "incubate", explores


async def use_special(uid: int, item_id: str):
    tp = ALL[item_id]["effect"]["type"]
    if tp == "tome":
        return await use_tome(uid, item_id)
    return await use_egg(uid, item_id)


async def tick_incubator(uid: int):
    """Call once per successful explore. Returns the hatched pet dict or None."""
    c = col("characters")
    after = await c.find_one_and_update({"user_id": uid, "incubator.left": {"$gt": 0}}, {"$inc": {"incubator.left": -1}},
                                        return_document=ReturnDocument.AFTER)
    if after is None:
        after = await c.find_one({"user_id": uid, "incubator.left": {"$lte": 0}})
    if not after or (after.get("incubator") or {}).get("left", 1) > 0:
        return None
    before = await c.find_one_and_update({"user_id": uid, "incubator.left": {"$lte": 0}, f"pets.{PET_CAP - 1}": {"$exists": False}},
                                         {"$unset": {"incubator": ""}})
    if not before:
        return None
    inc = before["incubator"]
    pet = {"sp": random.randrange(len(PETS)), "tier": inc["tier"], "role": inc["role"]}
    await c.update_one({"user_id": uid}, {"$push": {"pets": pet}})
    return pet


async def set_active_pet(uid: int, idx: int) -> str:
    ch = await get_char(uid)
    pets = list(ch.get("pets") or [])
    if not (0 < idx < len(pets)):
        return "same" if idx == 0 and pets else "empty"
    new = list(pets)
    new[0], new[idx] = new[idx], new[0]
    r = await col("characters").update_one({"user_id": uid, "pets": pets}, {"$set": {"pets": new}})
    return "ok" if r.modified_count else "retry"


# ---- evolution ----------------------------------------------------------------------------------------------------
async def evolve(uid: int, item_id: str):
    st, ch = await game_settings(), await get_char(uid)
    eff = ALL[item_id]["effect"]
    if ch.get("evo_stage") is None:   # legacy character: freeze the stage they already have by level
        await col("characters").update_one({"user_id": uid, "evo_stage": {"$exists": False}},
                                           {"$set": {"evo_stage": evo_stage_cap(LEVEL_GATES, ch["level"])}})
        ch = await get_char(uid)
    max_stage = len(RACES[ch["race"]]["evo"]) - 1
    ok, why = evo_can(ch, eff, LEVEL_GATES, max_stage, st)
    if not ok:
        return why, (LEVEL_GATES[eff["stage"]] if why == "level" else None)
    cost = int(st["evo_coin_cost"]) * eff["stage"]
    if not await inv_remove(uid, item_id, 1):
        return "missing", None
    if not await add_coins(uid, -cost, "evolve"):
        await inv_add(uid, item_id, 1, force=True)
        return "funds", cost
    r = await col("characters").update_one({"user_id": uid, "evo_stage": ch["evo_stage"]}, {"$set": {"evo_stage": eff["stage"]}})
    if not r.modified_count:
        await inv_add(uid, item_id, 1, force=True)
        await add_coins(uid, cost, "evolve_refund")
        return "retry", None
    return "ok", eff["stage"]


# ---- crafting -----------------------------------------------------------------------------------------------------
def craft_coins(recipe: dict, st: dict) -> int:
    return max(0, int(recipe["coins"] * float(st["craft_cost_mult"])))


async def craft(uid: int, rid: str):
    st, ch = await game_settings(), await get_char(uid)
    rec = get_recipe(rid)
    if not rec:
        return "norec", None
    if ch["level"] < rec.get("min_level", 1):
        return "level", rec["min_level"]
    if await try_cooldown(f"craft:{uid}", int(st["craft_cooldown"])):
        return "wait", None
    inv = await inv_get(uid)
    take = plan(inv["items"], rec)
    if take is None:
        return "mats", None
    coins = craft_coins(rec, st)
    day, cap = today(), int(st["craft_daily_cap"])
    await col("characters").update_one({"user_id": uid, "craft.day": {"$ne": day}}, {"$set": {"craft": {"day": day, "n": 0}}})
    got = await col("characters").update_one({"user_id": uid, "craft.day": day, "craft.n": {"$lt": cap}}, {"$inc": {"craft.n": 1}})
    if not got.modified_count:
        return "cap", cap
    done = []
    why = None
    for iid, q in take:
        if await inv_remove(uid, iid, q):
            done.append((iid, q))
        else:
            why = "mats"
            break
    if why is None and coins and not await add_coins(uid, -coins, "craft"):
        why = "funds"
    if why:
        for iid, q in done:
            await inv_add(uid, iid, q, force=True)
        await col("characters").update_one({"user_id": uid, "craft.day": day}, {"$inc": {"craft.n": -1}})
        return why, coins if why == "funds" else None
    await inv_add(uid, rec["out"], 1, force=True)
    return "ok", rec["out"]
