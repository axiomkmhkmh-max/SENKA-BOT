"""Mandatory join: a player must be in the channel and the group before the bot plays with them.

Membership is checked with Telegram's getChatMember (the bot must be an admin in both chats). A confirmed player is
remembered for JOIN_OK_SECONDS, so a normal conversation does not call Telegram on every message. A Telegram error
lets the player through (and is logged): a broken check must not lock the whole game out.
"""
import logging
import time

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import settings
from database import col
from security import make_cb
from ui import Out

log = logging.getLogger("senka.joingate")

JOIN_OK_SECONDS = 600
_MEMBER_STATUSES = ("creator", "administrator", "member")
_confirmed: dict = {}  # uid -> monotonic time of the last confirmed membership


_group_cache = {"id": 0, "at": -1e9}


async def group_id() -> int:
    """The group's numeric id: JOIN_GROUP_ID if set, else the one an admin saved with /setjoingroup (a private invite
    link cannot be turned into an id by the bot, so an admin sends the command once inside the group)."""
    if settings.join_group_id:
        return int(settings.join_group_id)
    now = time.monotonic()
    if now - _group_cache["at"] > 60:
        try:
            d = await col("settings").find_one({"_id": "joingate"}) or {}
            _group_cache.update(id=int(d.get("group_id", 0) or 0), at=now)
        except Exception:
            log.exception("could not read the saved join group")
    return int(_group_cache["id"])


async def set_group_id(gid: int):
    await col("settings").update_one({"_id": "joingate"}, {"$set": {"group_id": int(gid)}}, upsert=True)
    _group_cache.update(id=int(gid), at=time.monotonic())
    _confirmed.clear()  # everybody is checked again against the group


async def _targets():
    out = [("channel", settings.join_channel, settings.join_channel_url)]
    gid = await group_id()
    if gid:
        out.append(("group", gid, settings.join_group_url))
    return out


def log_config_warnings():
    if settings.join_gate and not settings.join_group_id:
        log.warning("JOIN_GROUP_ID is not set: the group membership is NOT checked yet")


async def self_check(bot):
    """At start: log whether the bot can actually read membership in every required chat (the usual cause of
    'nobody is asked to join' is the bot not being an admin there; the check then lets everyone through)."""
    if not settings.join_gate:
        log.warning("JOIN GATE is OFF (JOIN_GATE=0)")
        return
    me = await bot.get_me()
    if not await group_id():
        log.error("JOIN CHECK PROBLEM: the group id is not known; send /setjoingroup inside the group (as an admin)")
    for name, chat, _ in await _targets():
        try:
            m = await bot.get_chat_member(chat, me.id)
            if m.status in ("administrator", "creator"):
                log.warning("JOIN CHECK OK: bot is %s in %s (%s)", m.status, name, chat)
            else:
                log.error("JOIN CHECK PROBLEM: bot is only %r in %s (%s); add the bot as admin there", m.status, name, chat)
        except Exception as e:
            log.error("JOIN CHECK PROBLEM for %s (%s): %s; the join gate will let everyone through until fixed", name, chat, e)


async def _is_member(bot, chat, uid: int) -> bool:
    try:
        m = await bot.get_chat_member(chat, uid)
    except Exception:
        log.exception("join check failed for %s in %s; letting the player through", uid, chat)
        return True
    if m.status == "restricted":
        return bool(getattr(m, "is_member", False))
    return m.status in _MEMBER_STATUSES


async def missing(bot, uid: int) -> list:
    """The (name, url) of every required chat the player is not in yet."""
    if not settings.join_gate:
        return []
    hit = _confirmed.get(uid)
    if hit and time.monotonic() - hit < JOIN_OK_SECONDS:
        return []
    out = []
    for name, chat, url in await _targets():
        if not await _is_member(bot, chat, uid):
            out.append((name, url))
    if out:
        _confirmed.pop(uid, None)
    else:
        if len(_confirmed) > 20000:
            _confirmed.clear()
        _confirmed[uid] = time.monotonic()
    return out


async def wall_for(ctx):
    """None when the player may play. Otherwise (text, keyboard) of the join panel to send instead."""
    if not settings.join_gate:
        return None
    from handlers_admin import admin_level
    if await admin_level(ctx.uid) >= 20:  # admins are never locked out of their own bot
        return None
    lacking = await missing(ctx.bot, ctx.uid)
    if not lacking:
        return None
    if not any(n == "group" for n, _ in lacking) and not await group_id():
        lacking = list(lacking) + [("group", settings.join_group_url)]  # not verifiable yet, but still asked for
    names = {"channel": ("کانال", "channel"), "group": ("گروه", "group")}
    fa_list = " و ".join(names[n][0] for n, _ in lacking)
    en_list = " and ".join(names[n][1] for n, _ in lacking)
    text = (f"🔒 برای بازی با SENKA اول باید عضو {fa_list} شوی.\n"
            f"After joining the {en_list}, press the check button below.")
    rows = []
    for name, url in lacking:
        label = "📢 عضویت در کانال" if name == "channel" else "💬 عضویت در گروه"
        rows.append([InlineKeyboardButton(text=label, url=url)])
    rows.append([InlineKeyboardButton(text="✅ عضو شدم / I joined", callback_data=make_cb("jchk", "", 0))])
    return text, InlineKeyboardMarkup(inline_keyboard=rows)


async def check_again(ctx):
    """The check button: True when the player has joined everything now."""
    _confirmed.pop(ctx.uid, None)
    return not await missing(ctx.bot, ctx.uid)
