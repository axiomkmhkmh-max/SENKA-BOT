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
GROUP_LANG = re.compile(r"^(?:زبان گروه|group language|group lang)\s+(فارسی|fa|persian|english|en|انگلیسی|دوزبانه|both|bilingual)$")
GL_MAP = {"فارسی": "fa", "fa": "fa", "persian": "fa", "english": "en", "en": "en", "انگلیسی": "en", "دوزبانه": "both", "both": "both", "bilingual": "both"}


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
    blocked = await gate(ctx)
    if blocked:
        return await send_out(message, ctx, blocked)
    await show_home_or_reg(message, ctx)


# Telegram's "/" menu: every command just runs the same word router as typed text.
COMMANDS = {"home": "home", "profile": "profile", "explore": "explore", "battle": "battle", "bag": "bag", "market": "market",
            "quests": "quests", "summon": "gacha", "squad": "squad", "ranking": "ranking", "daily": "daily", "dungeon": "dungeon",
            "map": "adventure", "boss": "boss", "duel": "duel", "friendly": "duel_friendly", "minigame": "mini", "forge": "forge",
            "party": "party", "settings": "settings", "help": "help", "world": "world", "craft": "craft", "season": "season", "commands": "commands",
            "tower": "tower", "dispatch": "dispatch", "wheel": "wheel", "seat": "seat", "inner": "inner", "artifact": "artifact"}


@router.message(Command(*COMMANDS))
async def on_command(message: Message, command: CommandObject):
    if message.from_user is None or message.from_user.is_bot:
        return
    intent = COMMANDS.get((command.command or "").lower())
    if not intent:
        return
    if message.chat.type != "private" and intent not in GROUP_OK:
        ctx = await make_ctx(message.from_user, message.chat, message.bot, message)
        return await message.reply(ctx.t("cmd_private"))
    await handle_text(message, word_for(intent))


@router.message(F.text)
async def on_text(message: Message):
    await handle_text(message, message.text or "")


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
    blocked = await gate(ctx)
    if blocked:
        return await send_out(message, ctx, blocked)
    ch = await get_char(user.id)
    if not ch:
        if not await user_lang(user.id):
            return await send_out(message, ctx, reg.lang_panel(ctx))
        r = await reg_get(user.id)
        if r and r.get("step") == "name":
            return await send_out(message, ctx, await reg.handle_name_text(ctx, text))
        return await send_out(message, ctx, await reg.reg_panel(ctx, r))
    # admin text commands
    if await handlers_admin.admin_level(user.id) >= 20:
        out = await handlers_admin.handle_admin_text(ctx, text)
        if out is not None:
            return await send_out(message, ctx, out)
    # pending free-text prompts (e.g. guild name)
    pend = await col("inputs").find_one_and_delete({"user_id": user.id})
    if pend and pend["kind"] in INPUTS:
        import time
        if time.time() - pend["at"] < 300 and normalize_text(text) not in ("لغو", "cancel"):
            return await send_out(message, ctx, await INPUTS[pend["kind"]](ctx, text))
    hit = await resolve(text)
    if not hit:
        return await message.answer(ctx.t("unknown"), reply_markup=markup(ctx, [[(ctx.t("m_home"), "home", "")]]))
    name, code, arg = hit
    log_text(user.id, name)
    if code.startswith("*"):
        return await message.answer(ctx.t("duel_group_only"))
    if code == "adm" and await handlers_admin.admin_level(user.id) < 20:
        return
    out = await REGISTRY[code](ctx, arg)
    out.new = True
    await send_out(message, ctx, out)


async def on_group_text(message: Message, text: str):
    user, chat = message.from_user, message.chat
    n = normalize_text(text)
    if allow(chat.id, "note", 60):
        ch = await get_char(user.id)
        await note_group(chat.id, chat.title or "", ch["level"] if ch else None)
    m = GROUP_LANG.match(n)
    if m:
        member = await message.bot.get_chat_member(chat.id, user.id)
        if member.status in ("creator", "administrator"):
            await set_group_lang(chat.id, GL_MAP[m.group(1)])
            await message.reply("✅")
        return
    if await handlers_drops.group_hook(message, text, n):
        return
    if not allow(user.id, "grp", 1.5):
        return
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
    if name not in GROUP_OK:
        return
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
    blocked = await gate(ctx)
    if blocked:
        return await cb.answer(blocked.text, show_alert=True)
    if code not in ("lang", "noop") and code not in ("begin", "gen", "race", "st", "zp", "bh", "dua", "dud", "pa") and not await _has_char(user.id):
        r = await reg.reg_panel(ctx)
        return await _deliver(cb, ctx, r)
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
