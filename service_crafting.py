"""Crafting, armor tempering, relic / cosmetic / pet management and the race evolution trial.
Everything is driven by data_crafting tables and item `effect` fields."""
import random

from data_crafting import (EVO_REQ, RELIC_KINDS, build_recipes, evo_next, evo_stage, plan_inputs, temper_recipe)
from data_items import ALL
from data_races import DUNGEONS, RACES
from database import col, game_settings, try_cooldown
from service_economy import inv_add, inv_get, inv_remove
from service_player import add_coins, get_char
from service_worldcore import chronicle, world_adjust

RECIPES = build_recipes(ALL)
RECIPE_BY_ID = {r["id"]: r for r in RECIPES}


def scaled_coins(recipe: dict, st: dict) -> int:
    return max(0, int(recipe["coins"] * float(st["craft_cost_k"])))


async def _consume(uid: int, plan: dict) -> bool:
    """Remove every planned item, or none (rolls back on a race)."""
    done = []
    for iid, q in plan.items():
        if await inv_remove(uid, iid, q):
            done.append((iid, q))
        else:
            for j, qq in done:
                await inv_add(uid, j, qq, force=True)
            return False
    return True


async def _pay_and_consume(uid: int, recipe: dict, st: dict, inv: dict):
    plan = plan_inputs(recipe["in"], inv["items"], ALL)
    if plan is None:
        return "mats", None
    coins = scaled_coins(recipe, st)
    if coins and not await add_coins(uid, -coins, "craft"):
        return "funds", coins
    if not await _consume(uid, plan):
        if coins:
            await add_coins(uid, coins, "craft_refund")
        return "mats", None
    return "ok", (plan, coins)


# ---- crafting ---------------------------------------------------------------------------------------------
def recipes_for(ch: dict, kind: str) -> list:
    out = [r for r in RECIPES if r["type"] == kind]
    if kind == "key":
        out = [r for r in out if ch["level"] >= DUNGEONS[r["dungeon"]]["level"]]
    return out


async def craft(uid: int, rid: str):
    r = RECIPE_BY_ID.get(rid)
    if not r:
        return "norecipe", None
    if await try_cooldown(f"craft:{uid}", 1):
        return "wait", None
    ch = await get_char(uid)
    if r["type"] == "key" and ch["level"] < DUNGEONS[r["dungeon"]]["level"]:
        return "level", DUNGEONS[r["dungeon"]]["level"]
    st = await game_settings()
    inv = await inv_get(uid)
    res, data = await _pay_and_consume(uid, r, st, inv)
    if res != "ok":
        return res, data
    plan, coins = data
    if not await inv_add(uid, r["out"], 1):
        for iid, q in plan.items():
            await inv_add(uid, iid, q, force=True)
        if coins:
            await add_coins(uid, coins, "craft_refund")
        return "full", None
    await world_adjust(reishi_loc=ch["location"], reishi=float(st["world_reishi_craft"]))
    from service_worldstate import on_action
    await on_action(uid, "craft", ch["location"])
    return "ok", r["out"]


async def temper(uid: int):
    if await try_cooldown(f"craft:{uid}", 1):
        return "wait", None
    ch = await get_char(uid)
    st = await game_settings()
    aid = ch.get("armor_id")
    if not aid:
        return "noarmor", None
    plus = (ch.get("armor_plus") or {}).get(aid, 0)
    if plus >= int(st["temper_max"]):
        return "max", plus
    r = temper_recipe(plus, ALL[aid])
    res, data = await _pay_and_consume(uid, r, st, await inv_get(uid))
    if res != "ok":
        return res, data
    await world_adjust(reishi_loc=ch["location"], reishi=float(st["world_reishi_craft"]))
    if random.random() * 100 < r["chance"]:
        await col("characters").update_one({"user_id": uid, "armor_id": aid}, {"$set": {f"armor_plus.{aid}": plus + 1}})
        return "ok", plus + 1
    return "fail", plus


# ---- relics ------------------------------------------------------------------------------------------------------
async def relic_attune(uid: int, item_id: str) -> str:
    st = await game_settings()
    it = ALL.get(item_id)
    if not it or (it.get("effect") or {}).get("type") != "relic":
        return "norelic"
    slots = max(1, int(st["relic_slots"]))
    if not await inv_remove(uid, item_id, 1):
        return "missing"
    r = await col("characters").update_one({"user_id": uid, f"relics.{slots - 1}": {"$exists": False}}, {"$push": {"relics": item_id}})
    if not r.modified_count:
        await inv_add(uid, item_id, 1, force=True)
        return "slots"
    return "ok"


async def relic_release(uid: int, idx: int) -> str:
    ch = await get_char(uid)
    rel = list(ch.get("relics") or [])
    if not 0 <= idx < len(rel):
        return "empty"
    iid = rel.pop(idx)
    r = await col("characters").update_one({"user_id": uid, "relics": ch.get("relics")}, {"$set": {"relics": rel}})
    if not r.modified_count:
        return "retry"
    await inv_add(uid, iid, 1, force=True)
    return "ok"


# ---- cosmetics -----------------------------------------------------------------------------------------------------
async def cosmetic_wear(uid: int, item_id: str) -> str:
    it = ALL.get(item_id)
    e = (it or {}).get("effect") or {}
    if e.get("type") != "cosmetic":
        return "nocosmetic"
    slot = e["slot"]
    ch = await get_char(uid)
    cur = (ch.get("cosmetics") or {}).get(slot)
    if cur == item_id:
        return "already"
    if not await inv_remove(uid, item_id, 1):
        return "missing"
    r = await col("characters").update_one({"user_id": uid, f"cosmetics.{slot}": cur}, {"$set": {f"cosmetics.{slot}": item_id}})
    if not r.modified_count:
        await inv_add(uid, item_id, 1, force=True)
        return "retry"
    if cur:
        await inv_add(uid, cur, 1, force=True)
    return "ok"


async def cosmetic_remove(uid: int, slot: str) -> str:
    ch = await get_char(uid)
    cur = (ch.get("cosmetics") or {}).get(slot)
    if not cur:
        return "empty"
    if not await inv_add(uid, cur, 1):
        return "full"
    r = await col("characters").update_one({"user_id": uid, f"cosmetics.{slot}": cur}, {"$set": {f"cosmetics.{slot}": None}})
    if not r.modified_count:
        await inv_remove(uid, cur, 1)
        return "retry"
    return "ok"


# ---- pets -------------------------------------------------------------------------------------------------------------
async def pet_activate(uid: int, idx: int) -> str:
    ch = await get_char(uid)
    pets = list(ch.get("pets") or [])
    if not 0 < idx < len(pets):
        return "bad"
    new = list(pets)
    new[0], new[idx] = new[idx], new[0]
    r = await col("characters").update_one({"user_id": uid, "pets": pets}, {"$set": {"pets": new}})
    return "ok" if r.modified_count else "retry"


# ---- evolution trial -----------------------------------------------------------------------------------------------------
def evo_requirement(ch: dict):
    """(stage, level_gate, need, min_rarity) for the next trial, or None at max stage."""
    return evo_next(ch)


async def evo_status(uid: int):
    ch = await get_char(uid)
    nxt = evo_next(ch)
    if not nxt:
        return ch, None, None
    stage, gate, need, tier = nxt
    inv = await inv_get(uid)
    plan = plan_inputs([{"cat": "evolution", "n": need, "t": tier}], inv["items"], ALL)
    return ch, nxt, plan


async def evo_start(uid: int, lang: str):
    from service_combat import active_pve, pve_start
    ch, nxt, plan = await evo_status(uid)
    if not nxt:
        return "max", None
    stage, gate, need, tier = nxt
    if ch["level"] < gate:
        return "level", gate
    if plan is None:
        return "items", need
    if await active_pve(uid):
        return "busy", None
    if await try_cooldown(f"evo:{uid}", 20):
        return "wait", None
    return "ok", await pve_start(uid, lang, trial={"stage": stage})


async def evo_complete(uid: int, stage: int):
    """Called once when the trial is won. Items are spent only now, atomically."""
    ch, nxt, plan = await evo_status(uid)
    if not nxt or nxt[0] != stage or plan is None:
        return None
    if not await _consume(uid, plan):
        return None
    await col("characters").update_one({"user_id": uid}, {"$set": {"evo": stage}})
    ev = RACES[ch["race"]]["evo"][stage]
    await chronicle("evo", name=ch["name"], title_fa=ev[0], title_en=ev[1])
    return {"stage": stage, "title_fa": ev[0], "title_en": ev[1]}
