"""Race weapons (data_raceweapons): choosing, switching type, colour ascension, race change and the one-time move from
the old blades.

Character fields:
  weapon_id            the race weapon in hand (rw_<race>_<nn>_<colour>); None while a choice is pending
  weapon_plus.<id>     forge level of that item (the existing forge, service_economy.forge)
  bond.<rw base id>    bond of the weapon (data_zanpakuto.bond_key), the same at every colour and after a type switch
  rw_pending           {"c": colour, "plus": forge, "bond": bond} while the player must choose (mandatory: fights wait)
Every write is conditional on what was read, so double taps cannot apply twice.
"""
import asyncio
import logging
import time

from data_items import ALL
from data_raceweapons import COLOURS, LEVEL_BY_COLOUR, RACE_WEAPONS, ascend_cost, colour_for_rarity, parse_rw, rw_base, rw_id
from database import col
from service_economy import inv_get, inv_remove
from service_player import add_coins, get_char

log = logging.getLogger("senka.rweapon")
REBIRTH_SEAL = "it_q017"     # the old Zanpakutō Rebirth Seal: now switches the race weapon's type, keeping its level


def is_race_weapon_of(item_id, race) -> bool:
    p = parse_rw(item_id)
    return bool(p and p[0] == race and item_id in ALL)


def needs_choice(ch: dict) -> bool:
    """True while the player has no race weapon of their own race in hand (choice pending, old blade, race changed)."""
    if not ch:
        return False
    return bool(ch.get("rw_pending")) or not is_race_weapon_of(ch.get("weapon_id"), ch.get("race"))


def _old_level(ch: dict) -> dict:
    """The level a new race weapon is offered at: the colour, forge level and bond of the weapon in hand now."""
    wid = ch.get("weapon_id")
    it = ALL.get(wid or "")
    if not it:
        return {"c": 0, "plus": 0, "bond": 0}
    p = parse_rw(wid)
    colour = p[2] if p else colour_for_rarity(it.get("rarity", "Common"))
    plus = int((ch.get("weapon_plus") or {}).get(wid, 0))
    bond_k = p and rw_base(p[0], p[1]) or wid
    has_blade = bool((ch.get("zanpakuto") or {}).get("blade_id"))  # a chosen Zanpakutō keeps its own bond
    bond = 0 if has_blade else int((ch.get("bond") or {}).get(bond_k, 0))
    return {"c": int(colour), "plus": plus, "bond": bond}


def offer_level(ch: dict) -> dict:
    lvl = ch.get("rw_pending") or _old_level(ch)
    c = max(0, min(COLOURS - 1, int(lvl.get("c", 0))))
    return {"c": c, "plus": max(0, min(10, int(lvl.get("plus", 0)))), "bond": max(0, int(lvl.get("bond", 0)))}


async def choose(uid: int, n: int):
    """Take race weapon number n (0..9) at the offered level. Returns (status, item_id)."""
    ch = await get_char(uid)
    if not ch:
        return "noreg", None
    race = ch["race"]
    if not 0 <= int(n) < len(RACE_WEAPONS.get(race, [])):
        return "bad", None
    if not needs_choice(ch):
        return "has", ch.get("weapon_id")
    lvl = offer_level(ch)
    new = rw_id(race, int(n), lvl["c"])
    upd = {"$set": {"weapon_id": new, f"weapon_plus.{new}": lvl["plus"], "rw_chosen_at": int(time.time())},
           "$unset": {"rw_pending": ""}}
    if lvl["bond"]:
        upd["$max"] = {f"bond.{rw_base(race, int(n))}": lvl["bond"]}
    flt = {"user_id": uid, "race": race, "weapon_id": ch.get("weapon_id")}
    r = await col("characters").update_one(flt, upd)
    return ("ok", new) if r.modified_count else ("retry", None)


async def switch_type(uid: int, n: int):
    """Rebirth Seal: move to another of the race's ten weapons, keeping colour, forge level and bond."""
    ch = await get_char(uid)
    if not ch:
        return "noreg", None
    p = parse_rw(ch.get("weapon_id"))
    if not p or p[0] != ch["race"]:
        return "choose", None
    race, cur_n, colour = p
    if int(n) == cur_n or not 0 <= int(n) < len(RACE_WEAPONS.get(race, [])):
        return "bad", None
    if not await inv_remove(uid, REBIRTH_SEAL, 1):
        return "seal", None
    old, new = ch["weapon_id"], rw_id(race, int(n), colour)
    plus = int((ch.get("weapon_plus") or {}).get(old, 0))
    bond = int((ch.get("bond") or {}).get(rw_base(race, cur_n), 0))
    upd = {"$set": {"weapon_id": new, f"weapon_plus.{new}": plus}, "$unset": {f"weapon_plus.{old}": ""}}
    if bond:
        upd["$set"][f"bond.{rw_base(race, int(n))}"] = bond
    r = await col("characters").update_one({"user_id": uid, "weapon_id": old}, upd)
    if not r.modified_count:
        from service_economy import inv_add
        await inv_add(uid, REBIRTH_SEAL, 1, force=True)
        return "retry", None
    return "ok", new


def ascend_need(ch: dict):
    """(next colour, level gate, items needed, min item rarity index, coins) or None at red."""
    p = parse_rw(ch.get("weapon_id"))
    if not p or p[2] >= COLOURS - 1:
        return None
    need, tier, coins = ascend_cost(p[2])
    return p[2] + 1, LEVEL_BY_COLOUR[p[2] + 1], need, tier, coins


async def ascend(uid: int):
    """Raise the weapon one colour with evolution items and coins. Forge level and bond are kept."""
    from data_crafting import plan_inputs
    from service_crafting import _consume
    ch = await get_char(uid)
    if not ch or needs_choice(ch):
        return "choose", None
    nxt = ascend_need(ch)
    if not nxt:
        return "max", None
    colour, gate, need, tier, coins = nxt
    if int(ch["level"]) < gate:
        return "level", gate
    inv = await inv_get(uid)
    plan = plan_inputs([{"cat": "evolution", "n": need, "t": tier}], inv["items"], ALL)
    if plan is None:
        return "items", need
    if int(ch.get("coins", 0)) < coins or not await add_coins(uid, -coins, "rw_ascend"):
        return "funds", coins
    if not await _consume(uid, plan):
        await add_coins(uid, coins, "rw_ascend_refund")
        return "items", need
    race, n, _c = parse_rw(ch["weapon_id"])
    old, new = ch["weapon_id"], rw_id(race, n, colour)
    plus = int((ch.get("weapon_plus") or {}).get(old, 0))
    r = await col("characters").update_one({"user_id": uid, "weapon_id": old},
                                           {"$set": {"weapon_id": new, f"weapon_plus.{new}": plus}, "$unset": {f"weapon_plus.{old}": ""}})
    if not r.modified_count:
        from service_economy import inv_add
        for iid, q in plan.items():
            await inv_add(uid, iid, q, force=True)
        await add_coins(uid, coins, "rw_ascend_refund")
        return "retry", None
    return "ok", new


async def on_race_change(uid: int, old_race: str, new_race: str):
    """A new race cannot hold the old race's weapon: the choice opens again, at the same colour, forge and bond."""
    ch = await get_char(uid)
    if not ch:
        return
    lvl = offer_level({**ch, "race": old_race})
    await col("characters").update_one({"user_id": uid}, {"$set": {"rw_pending": lvl, "weapon_id": None}})


# ---- one-time move from the old blades -------------------------------------------------------------------------------
MIGRATION_ID = "race_weapons_v1"


def _is_old_blade(item_id) -> bool:
    it = ALL.get(item_id or "")
    return bool(it and it.get("category") == "weapon" and it.get("subtype") != "rweapon")


async def migrate_blades_once() -> int:
    """Every old blade is removed (bag and hand). Each character gets a pending choice of a race weapon at the level
    of the blade in hand (its colour, forge level and bond). Runs once (marker in `migrations`)."""
    if await col("migrations").find_one({"_id": MIGRATION_ID}):
        return 0
    moved = 0
    async for ch in col("characters").find({"rw_pending": {"$exists": False}},
                                            {"user_id": 1, "race": 1, "weapon_id": 1, "weapon_plus": 1, "bond": 1, "zanpakuto": 1}):
        if is_race_weapon_of(ch.get("weapon_id"), ch.get("race")):
            continue
        lvl = _old_level(ch)
        r = await col("characters").update_one({"_id": ch["_id"], "weapon_id": ch.get("weapon_id")},
                                               {"$set": {"rw_pending": lvl, "weapon_id": None, "rw_notice": False}})
        moved += int(bool(r.modified_count))
    async for inv in col("inventories").find({}, {"user_id": 1, "items": 1}):
        old = [i for i in (inv.get("items") or {}) if _is_old_blade(i)]
        if old:
            await col("inventories").update_one({"_id": inv["_id"]}, {"$unset": {f"items.{i}": "" for i in old}})
    await col("migrations").update_one({"_id": MIGRATION_ID}, {"$set": {"moved": moved, "at": int(time.time())}}, upsert=True)
    return moved


# ---- the notice: one private message per player who must choose ------------------------------------------------------
NOTICE = {
    "fa": "🗡 <b>زمان انتخاب سلاح نژادت رسیده!</b>\n\nتیغه‌های قدیمی از دنیای سنکا رفتند. هر نژاد حالا ده سلاح خام مخصوص خودش دارد "
          "و تو یکی را انتخاب می‌کنی و با خودت بزرگش می‌کنی. سلاحی که انتخاب می‌کنی با <b>همان سطح تیغه‌ی قبلی‌ات</b> "
          "(همان رنگ، همان فورج و همان پیوند) شروع می‌شود.\n\n⚠️ تا انتخاب نکنی نمی‌توانی وارد نبرد شوی.",
    "en": "🗡 <b>Time to choose your race weapon!</b>\n\nThe old blades have left the world of SENKA. Every race now has ten raw "
          "weapons of its own; you pick one and grow it. The weapon you choose starts at <b>the level of your old blade</b> "
          "(same colour, same forge level, same bond).\n\n⚠️ You cannot fight until you choose.",
}
BTN = {"fa": "🗡 انتخاب سلاح نژاد", "en": "🗡 Choose race weapon"}


async def notify_pending(bot, stop: asyncio.Event):
    """Send the notice to every player with a pending choice who has not had it yet (resumes after a restart)."""
    from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError, TelegramRetryAfter
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    from security import make_cb
    await asyncio.sleep(8)
    try:
        while not stop.is_set():
            batch = await col("characters").find({"rw_pending": {"$exists": True}, "rw_notice": {"$ne": True}},
                                                 {"user_id": 1}).limit(200).to_list(200)
            if not batch:
                return
            for ch in batch:
                uid = ch["user_id"]
                u = await col("users").find_one({"telegram_id": uid}, {"lang": 1, "blocked_bot": 1}) or {}
                await col("characters").update_one({"_id": ch["_id"]}, {"$set": {"rw_notice": True}})
                if u.get("blocked_bot"):
                    continue
                lang = "fa" if (u.get("lang") or "fa") == "fa" else "en"
                kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=BTN[lang], callback_data=make_cb("rwp", "", uid))]])
                for _ in range(3):
                    try:
                        await bot.send_message(uid, NOTICE[lang], reply_markup=kb)
                        break
                    except TelegramRetryAfter as e:
                        await asyncio.sleep(min(60, e.retry_after + 1))
                    except TelegramForbiddenError:
                        await col("users").update_one({"telegram_id": uid}, {"$set": {"blocked_bot": True}})
                        break
                    except TelegramAPIError:
                        break
                await asyncio.sleep(0.06)
    except Exception:
        log.exception("race weapon notice failed")
