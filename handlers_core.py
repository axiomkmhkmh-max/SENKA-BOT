"""Routers: /start, bilingual text intents, group handling and callback dispatch."""
import asyncio
import logging
import re
import time

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import CallbackQuery, Message

import handlers_admin
import handlers_combat
import handlers_drops
import handlers_extras  # noqa: F401  (registers the new panels)
import handlers_bleach  # noqa: F401  (allegiance panel)
import handlers_zanpakuto  # noqa: F401 (Zanpakuto progression)
import handlers_senkaimon  # noqa: F401 (Senkaimon portal)
import handlers_dungeonshop  # noqa: F401 (dungeon points shop)
import handlers_hollowraid
import handlers_viral  # --- NEW BLEACH VIRAL SYSTEM
import handlers_bleach_systems  # noqa: F401 (race, Kidō and faction progression)
import handlers_casino  # noqa: F401 (Bleach Casino)
import handlers_bank  # noqa: F401 (Bleach Bank)
import handlers_hunt  # noqa: F401 (Hollow Hunt)
import handlers_adminpanel  # noqa: F401  (admin button panel)
import handlers_adminplus  # noqa: F401  (admin pickers: boss, event, item, summon)
import handlers_extras  # noqa: F401  (player extras: stats, quiz, coinflip, transfer...)
import handlers_wheel  # noqa: F401  (Urahara's wheel: panel + animated spin)
import handlers_inner  # noqa: F401  (Inner World: weekly scene panel + choices)
import handlers_trade  # noqa: F401  (player trading: hub, shared view, group offers)
import handlers_respec  # noqa: F401  (stat reset and race change)
import handlers_raceweapon  # noqa: F401  (race weapon: choice, ascension, type switch)
import handlers_battlerank  # noqa: F401  (Battle Rank: panel, ladder, flee)
import handlers_gangs  # noqa: F401  (Xcution membership panel)
import handlers_towerx  # noqa: F401  (Soul Tower, Dispatch and Gotei Seat panels)
import handlers_items
import handlers_panels
import handlers_world
import handlers_registration as reg
from config import settings
from database import col, game_settings
from intents import GROUP_OK, resolve, word_for
from security import allow, normalize_text, parse_cb
from service_log import log_action, log_text
from service_player import get_char, reg_get, touch_user, user_lang
from service_world import note_group, set_group_lang, spawn_boss
from ui import INPUTS, REGISTRY, Ctx, Out, markup

log = logging.getLogger("senka.core")
router = Router()
GROUP_LANG = re.compile(r"^(?:زبان گروه|group language|group lang)\s+(فارسی|fa|persian|english|en|انگلیسی)$")
GL_MAP = {"فارسی": "fa", "fa": "fa", "persian": "fa", "english": "en", "en": "en", "انگلیسی": "en"}


async def make_ctx(user, chat, bot, message=None, cb=None):
    lang = await user_lang(user.id)
    if not lang and user.language_code:
        lang = "fa" if user.language_code.startswith("fa") else None
    return Ctx(user.id, lang or "en", chat.id, chat.type, user, bot, message, cb)


_ban_cache: dict = {}   # uid -> (banned, monotonic time): saves one Mongo round trip on every click
_char_ok: dict = {}     # uid -> monotonic time we last saw a character for this user


async def _is_banned(uid: int) -> bool:
    hit = _ban_cache.get(uid)
    now = time.monotonic()
    if hit and now - hit[1] < 15:
        return hit[0]
    u = await col("users").find_one({"telegram_id": uid}, {"banned": 1})
    banned = bool(u and u.get("banned"))
    if len(_ban_cache) > 20000:
        _ban_cache.clear()
    _ban_cache[uid] = (banned, now)
    return banned


async def _has_char(uid: int) -> bool:
    now = time.monotonic()
    if now - _char_ok.get(uid, -1e9) < 120:
        return True
    ok = bool(await col("characters").find_one({"user_id": uid}, {"_id": 1}))
    if ok:
        if len(_char_ok) > 20000:
            _char_ok.clear()
        _char_ok[uid] = now
    return ok


async def gate(ctx):
    if await _is_banned(ctx.uid):
        return Out(ctx.t("banned"))
    st = await game_settings()
    if st["maintenance"] and await handlers_admin.admin_level(ctx.uid) < 20:
        return Out(ctx.t("maintenance"))
    return None


# Codes that start a fight. A player who still has to choose a race weapon is sent to that choice first (mandatory).
FIGHT_CODES = {"bs", "bn", "dgs", "dua", "bh", "hnt", "exp", "evs", "skm"}


async def weapon_gate(ctx, code):
    """The race-weapon choice panel if this code starts a fight and the choice is still pending, else None."""
    if code not in FIGHT_CODES:
        return None
    from service_raceweapon import needs_choice
    ch = await get_char(ctx.uid)
    if not ch or not needs_choice(ch):
        return None
    from handlers_raceweapon import choice_panel
    return await choice_panel(ctx, ch)


async def send_out(message: Message, ctx: Ctx, out: Out):
    if out.text:
        await message.answer(out.text, reply_markup=markup(ctx, out.rows))


async def show_home_or_reg(message: Message, ctx: Ctx):
    ch = await get_char(ctx.uid)
    if ch:
        return await send_out(message, ctx, await REGISTRY["home"](ctx, ""))
    if not await user_lang(ctx.uid):
        return await send_out(message, ctx, reg.lang_panel(ctx))
    await send_out(message, ctx, await reg.reg_panel(ctx))


@router.message(CommandStart())
async def on_start(message: Message, command: CommandObject):
    if message.chat.type != "private":
        return
    ref = None
    if command.args and command.args.startswith("ref_") and command.args[4:].isdigit():
        ref = int(command.args[4:])
    await touch_user(message.from_user, ref)
    ctx = await make_ctx(message.from_user, message.chat, message.bot, message)
    asyncio.ensure_future(_ensure_admin_menu(message.bot, message.from_user.id))
    blocked = await gate(ctx)
    if blocked:
        return await send_out(message, ctx, blocked)
    await show_home_or_reg(message, ctx)


# Telegram's "/" menu: every command just runs the same word router as typed text.
COMMANDS = {"home": "home", "profile": "profile", "explore": "explore", "battle": "battle", "bag": "bag", "market": "market",
            "quests": "quests", "summon": "gacha", "squad": "squad", "ranking": "ranking", "daily": "daily", "dungeon": "dungeon",
            "map": "adventure", "boss": "boss", "duel": "duel", "friendly": "duel_friendly", "minigame": "mini", "forge": "forge",
            "party": "party", "trade": "trdhub", "ترید": "trdhub", "respec": "resp", "ریست استت": "resp", "تغییر نژاد": "resp", "settings": "settings", "help": "help", "world": "world", "craft": "craft", "season": "season", "commands": "commands",
            "zanpakuto": "zanpakuto", "znp": "zanpakuto", "kido": "kido", "racepath": "racepath", "faction": "faction", "bleach": "bleach_hub", "senkaimon": "senkaimon", "portal": "senkaimon", "tower": "tower", "dispatch": "dispatch", "wheel": "wheel", "seat": "seat", "inner": "inner", "artifact": "artifact",
            "battlerank": "battle_rank", "upgrade": "upgrade", "weapon": "race_weapon", "division": "division", "hollow": "hollow", "event": "event",
            "chronicle": "chronicle", "territory": "territory", "bounty": "bounty", "relics": "gear", "evolve": "evolution",
            "exchange": "artifact_mkt", "registry": "artifact_reg", "admin": "admin",
            "shop": "shop", "listings": "listings", "auction": "auction", "mylistings": "mylistings", "pets": "pets", "cosmetics": "cosmetics",
            "potions": "potions", "keys": "keys", "armor": "armor", "towertop": "towertop", "here": "here",
            # hidden aliases: not in the "/" menu, but typing them works
            "me": "profile", "stats": "profile", "fight": "battle", "hunt": "battle", "patrol": "explore", "wander": "explore",
            "inventory": "bag", "inv": "bag", "items": "bag", "clan": "squad", "guild": "squad", "top": "ranking", "leaderboard": "ranking",
            "quest": "quests", "missions": "quests", "gacha": "gacha", "pull": "gacha", "lang": "settings", "language": "settings",
            "zanpakuto": "zanpakuto", "gotei": "seat", "worldboss": "boss", "bosses": "boss", "shinigami": "profile", "reward": "daily",
            "wiki": "help", "guide": "help", "cmds": "commands", "travel": "adventure", "locations": "adventure", "pet": "pets",
            "pvptop": "pvptop", "leveltop": "leveltop", "consumables": "consumables", "mygear": "mygear",
            "aworld": "admin_world", "ausers": "admin_users", "asettings": "admin_settings", "announce": "admin_announce",
            "alog": "admin_log", "aadmins": "admin_admins",
            "relic": "gear", "evolution": "evolution", "news": "chronicle", "land": "territory", "wanted": "bounty"}

from data_races import LOCATIONS as _LOCS  # noqa: E402
COMMANDS.update({"go_" + k: "go_" + k for k in _LOCS})  # /go_rukongai, /go_hueco_mundo ... (hidden from the menu)


@router.message(Command(*COMMANDS))
async def on_command(message: Message, command: CommandObject):
    if message.from_user is None or message.from_user.is_bot:
        return
    intent = COMMANDS.get((command.command or "").lower())
    if not intent:
        return
    await handle_text(message, word_for(intent))


@router.message(F.text)
async def on_text(message: Message):
    await handle_text(message, message.text or "")


_admin_menu_done: set = set()


async def _ensure_admin_menu(bot, uid: int):
    """First time an admin talks to the bot after a (re)start: make sure /admin & co are in their own '/' menu."""
    if uid in _admin_menu_done:
        return
    _admin_menu_done.add(uid)
    try:
        if await handlers_admin.admin_level(uid) >= 20:
            from handlers_adminpanel import refresh_admin_commands
            await refresh_admin_commands(bot, uid)
    except Exception:
        log.exception("admin menu refresh failed")


async def _is_player_phrase(text: str) -> bool:
    """True when a multi-word text is a player command (so admin shortcuts must not take it)."""
    return len(text.split()) >= 2 and await resolve(text) is not None


async def handle_text(message: Message, text: str):
    user = message.from_user
    if user is None or user.is_bot:
        return
    if message.chat.type != "private":
        return await on_group_text(message, text)
    if not allow(user.id, "msg", 0.6):
        return
    await touch_user(user)
    ctx = await make_ctx(user, message.chat, message.bot, message)
    asyncio.ensure_future(_ensure_admin_menu(message.bot, user.id))
    # the gate, the character and a pending typed prompt are independent: one round trip instead of three in a row
    blocked, ch, pend = await asyncio.gather(gate(ctx), get_char(user.id), col("inputs").find_one({"user_id": user.id}))
    if blocked:
        return await send_out(message, ctx, blocked)
    if not ch:
        if not await user_lang(user.id):
            return await send_out(message, ctx, reg.lang_panel(ctx))
        r = await reg_get(user.id)
        if r and r.get("step") == "name":
            return await send_out(message, ctx, await reg.handle_name_text(ctx, text))
        return await send_out(message, ctx, await reg.reg_panel(ctx, r))
    # admin text commands (a multi-word player phrase wins over an admin shortcut with the same first word)
    admin_prompt = bool(pend and str(pend.get("kind", "")).startswith("ad_") and pend.get("at", 0) >= time.time() - 300)
    if not admin_prompt and await handlers_admin.admin_level(user.id) >= 20 and not await _is_player_phrase(text):
        out = await handlers_admin.handle_admin_text(ctx, text)
        if out is not None:
            return await send_out(message, ctx, out)
    # pending free-text prompts (e.g. guild name). Usually there is none: then no write at all
    if pend:
        pend = await col("inputs").find_one_and_delete({"_id": pend["_id"]})
    if pend and pend["kind"] in INPUTS:
        if time.time() - pend["at"] < 300 and normalize_text(text) not in ("لغو", "cancel"):
            return await send_out(message, ctx, await INPUTS[pend["kind"]](ctx, text))
    war = await handlers_combat.battle_word(ctx, text)  # in a fight: the blade's name releases Bankai when the gauge is full
    if war is not None:
        return await send_out(message, ctx, war)
    chase = await handlers_hunt.solo_word(ctx, normalize_text(text))  # typed چپ/وسط/راست during a solo chase
    if chase is not None:
        return await send_out(message, ctx, chase)
    hit = await resolve(text)
    if not hit:
        return await message.answer(ctx.t("unknown"), reply_markup=markup(ctx, [[(ctx.t("m_home"), "home", "")]]))
    name, code, arg = hit
    log_text(user.id, name)
    if code.startswith("*"):
        return await message.answer(ctx.t("duel_group_only"))
    if code.startswith("ad") and len(code) == 3 and await handlers_admin.admin_level(user.id) < 20:
        return
    out = await weapon_gate(ctx, code) or await REGISTRY[code](ctx, arg)
    out.new = True
    await send_out(message, ctx, out)


async def on_group_text(message: Message, text: str):
    user, chat = message.from_user, message.chat
    n = normalize_text(text)
    if allow(chat.id, "note", 60):
        ch = await get_char(user.id)
        await note_group(chat.id, chat.title or "", ch["level"] if ch else None, "fa" if (user.language_code or "").startswith("fa") else "en")
        if ch:  # who plays in this group, for group alerts (boss / drop private messages)
            await col("group_members").update_one({"chat_id": chat.id, "uid": user.id},
                                                  {"$set": {"last_seen": int(time.time()), "lang": "fa" if (user.language_code or "").startswith("fa") else "en"}},
                                                  upsert=True)
    m = GROUP_LANG.match(n)
    if m:
        member = await message.bot.get_chat_member(chat.id, user.id)
        if member.status in ("creator", "administrator"):
            await set_group_lang(chat.id, GL_MAP[m.group(1)])
            await message.reply("✅")
        return
    if await handlers_drops.group_hook(message, text, n):
        return
    if await handlers_hunt.group_hook(message, n):
        return
    if await handlers_hollowraid.raid_hook(message, n):
        return
    if await handlers_viral.viral_hook(message, text, n):  # --- NEW BLEACH VIRAL SYSTEM: espada fights, hogyoku theft, quincy strikes
        return
    if n in ("مبارزه", "fight") and message.reply_to_message:  # a plain duel when no Espada seat is at stake
        text = n = "دوئل"
    if not allow(user.id, "grp", 1.5):
        return
    if not await _is_player_phrase(text):
        ctx = await make_ctx(user, chat, message.bot, message)
        out = await handlers_admin.handle_admin_text(ctx, text)
        if out is not None and out.text:
            return await message.reply(out.text, reply_markup=markup(ctx, out.rows))
    if n in ("spawn boss", "ظهور باس"):
        if await handlers_admin.admin_level(user.id) >= 60:
            doc = await spawn_boss()
            if doc:
                await handlers_world.post_global_boss(message.bot, doc)
        return
    hit = await resolve(text)
    if not hit:
        return
    name, code, arg = hit
    if code.startswith("ad") and len(code) == 3 and await handlers_admin.admin_level(user.id) < 20:
        return  # admin-only panels stay invisible to everyone else, in groups too
    log_text(user.id, name, chat.type)
    await touch_user(user)
    ctx = await make_ctx(user, chat, message.bot, message)
    if await gate(ctx):
        return
    if code == "*duel":
        target = message.reply_to_message.from_user if message.reply_to_message else None
        if not target or target.is_bot:
            return await message.reply(ctx.t("duel_need_reply"))
        res = await handlers_combat.challenge(ctx, target, arg == "r")
        if isinstance(res, tuple):
            out, kb = res
            await message.answer(out.text, reply_markup=kb)
        else:
            await message.reply(res.text)
        return
    if code == "hlp":
        return await message.reply(ctx.t("group_help"))
    if not await get_char(user.id) and code not in ("home", "commands", "chronicle", "event", "boss", "battle", "duel"):
        return await message.reply(ctx.t("cmd_private"))  # registration is private-chat only
    if await weapon_gate(ctx, code):
        return await message.reply(ctx.t("rw_choose_first"))
    out = await REGISTRY[code](ctx, arg)
    out.new = True
    await message.answer(out.text, reply_markup=markup(ctx, out.rows))


@router.callback_query()
async def on_callback(cb: CallbackQuery):
    user = cb.from_user
    parsed = parse_cb(cb.data or "", user.id)
    lang = await user_lang(user.id) or "en"
    if not parsed:
        return await cb.answer("⚠️")
    code, arg, allowed = parsed
    ctx = Ctx(user.id, lang, cb.message.chat.id if cb.message else user.id, cb.message.chat.type if cb.message else "private",
              user, cb.bot, cb.message, cb)
    if not allowed:
        return await cb.answer(ctx.t("not_yours"), show_alert=True)
    if not allow(user.id, "cb", 0.2):
        return await cb.answer()
    fn = REGISTRY.get(code)
    if not fn:
        return await cb.answer()
    need_char = code not in ("lang", "noop") and code not in ("begin", "gen", "race", "st", "zp", "rgi", "zpi", "rgl", "bh", "dua", "dud", "pa")
    blocked, has_char = await asyncio.gather(gate(ctx), _has_char(user.id) if need_char else asyncio.sleep(0, True))  # together: one wait
    if blocked:
        return await cb.answer(blocked.text, show_alert=True)
    if need_char and not has_char:
        r = await reg.reg_panel(ctx)
        return await _deliver(cb, ctx, r)
    wg = await weapon_gate(ctx, code)
    if wg:  # a fight button while the race-weapon choice is pending: choose first (in a group, only a popup)
        if ctx.chat_type != "private":
            return await cb.answer(ctx.t("rw_choose_first"), show_alert=True)
        return await _deliver(cb, ctx, wg)
    try:
        out = await fn(ctx, arg)
    except Exception:
        log.exception("callback failed: %s %s", code, arg)
        return await cb.answer(ctx.t("error"), show_alert=True)
    log_action(user.id, code, arg, bool((await game_settings()).get("log_nav")))
    await _deliver(cb, ctx, out)


async def _answer_quiet(cb: CallbackQuery, out: Out):
    try:
        await cb.answer(out.alert or None, show_alert=bool(out.alert and len(out.alert) > 60))
    except Exception:
        pass


async def _deliver(cb: CallbackQuery, ctx: Ctx, out: Out):
    # the popup ack and the message edit are independent Telegram calls: run them together (saves one round trip)
    if not out.text or cb.message is None:
        return await _answer_quiet(cb, out)
    ack = asyncio.create_task(_answer_quiet(cb, out))
    kb = markup(ctx, out.rows)
    try:
        if out.new:
            await cb.message.answer(out.text, reply_markup=kb)
        else:
            await cb.message.edit_text(out.text, reply_markup=kb)
    except (TelegramBadRequest, AttributeError) as e:
        if "not modified" not in str(e):
            log.warning("edit failed (%s); sending new message", e)
            try:
                await cb.bot.send_message(ctx.chat_id, out.text, reply_markup=kb)
            except Exception:
                log.exception("send failed")
    finally:
        await ack
