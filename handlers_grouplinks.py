"""Group links for admins: every group the bot is in, with a join link.

  /groups [page | refresh]   (admin level 60 and up, private chat only)
  admin panel -> 🔗 Group links  (action `adgl`, same page with ◀️ ▶️ and a refresh button)

Where the link comes from, in this order:
  1. public group      -> https://t.me/<username>
  2. private group     -> the group's own invite link (the bot can read it when it is an admin there)
  3. otherwise         -> the bot creates one extra invite link with create_chat_invite_link. That never revokes
                          the links the group already has (exportChatInviteLink would). The link is saved in the
                          `groups` collection and reused for a week.
A private group where the bot is not an admin with the "invite users" right has no link; it is shown with its id.

Private links are secrets, so the command refuses to answer inside a group.
This module also records the groups the bot is added to or removed from (my_chat_member), so a group shows up here
before anybody has written a word in it.
"""
import asyncio
import logging
import time

from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import ChatMemberUpdated

from admin_panel_logic import page_bounds, to_ascii_digits
from database import col
from handlers_admin import alog
from handlers_admincmd import Env, acmd, router
from handlers_adminpanel import _back, _deny, _need
from i18n import esc, fnum
from service_world import note_group
from ui import Ctx, Out, action, head, markup, pager

log = logging.getLogger("senka.grouplinks")

PAGE = 8                  # groups per page (each takes about 5 lines; Telegram allows 4096 characters)
LINK_TTL = 7 * 86400      # a saved private invite link is trusted for a week, then looked up again
NEED = 60                 # admin and above (support 20 and moderator 40 never see these links)
_sem = asyncio.Semaphore(5)   # at most 5 Telegram lookups at the same time


def _t(lang: str, fa: str, en: str) -> str:
    return fa if lang == "fa" else en


def _ago(ts, lang: str) -> str:
    if not ts:
        return "-"
    mins = max(0, (int(time.time()) - int(ts)) // 60)
    if mins < 60:
        return f"{fnum(mins, lang)}{_t(lang, 'د', 'm')}"
    hours = mins // 60
    if hours < 48:
        return f"{fnum(hours, lang)}{_t(lang, 'س', 'h')}"
    return f"{fnum(hours // 24, lang)}{_t(lang, 'روز', 'd')}"


def _is_gone(exc: Exception) -> bool:
    """True when Telegram says the bot is no longer in the chat (kicked, left, chat deleted or upgraded to a supergroup)."""
    if isinstance(exc, TelegramForbiddenError):
        return True
    if isinstance(exc, TelegramBadRequest):
        s = str(exc).lower()
        return "chat not found" in s or "upgraded" in s or "kicked" in s
    return False


async def resolve_group(bot, g: dict, fresh: bool = False) -> dict:
    """Look one group up. Returns {"gone": bool, "error": bool, "link": str|None, "members": int|None, "kind": "public"|"private"|"none"}.
    Never raises: a Telegram error for one group must not hide the others."""
    cid = g["chat_id"]
    out = {"gone": False, "error": False, "link": None, "members": None, "kind": "none"}
    now = int(time.time())
    async with _sem:
        try:
            chat = await bot.get_chat(cid)
        except Exception as e:
            if _is_gone(e):
                out["gone"] = True
                await col("groups").update_one({"chat_id": cid}, {"$set": {"blocked": True, "left_at": now}})
            else:  # Telegram hiccup: say so, do not call the group "linkless"
                out["error"] = True
                log.warning("get_chat %s failed: %s", cid, e)
            return out
        upd = {}
        title = (chat.title or "")[:60]
        if title and title != g.get("title"):
            upd["title"] = title
        username = getattr(chat, "username", None)
        if username:
            out["link"], out["kind"] = f"https://t.me/{username}", "public"
            if username != g.get("username"):
                upd["username"] = username
        else:
            if g.get("username"):
                upd["username"] = None  # the group went private
            link = getattr(chat, "invite_link", None)  # filled in when the bot is an admin of the group
            if not link and not fresh and g.get("invite_link") and now - int(g.get("link_at", 0) or 0) < LINK_TTL:
                link = g["invite_link"]
            if not link:
                try:
                    created = await bot.create_chat_invite_link(cid, name="SENKA admin")
                    link = created.invite_link
                except Exception as e:  # no "invite users" right: normal, the group is simply listed without a link
                    log.info("no invite link for %s: %s", cid, e)
            if link:
                out["link"], out["kind"] = link, "private"
                if link != g.get("invite_link"):
                    upd["invite_link"], upd["link_at"] = link, now
        try:
            out["members"] = await bot.get_chat_member_count(cid)
            upd["members"] = out["members"]
        except Exception:
            out["members"] = g.get("members")
        if upd:
            await col("groups").update_one({"chat_id": cid}, {"$set": upd})
    return out


def _parse_arg(arg) -> tuple:
    """Panel button argument '<page>' or '<page>:r' (page counted from 0, r = look the links up again) -> (page, fresh)."""
    raw = to_ascii_digits(str(arg or "")).strip()
    num, _, flag = raw.partition(":")
    return (int(num) if num.isdigit() else 0), flag == "r"


async def _page(ctx: Ctx, want: int = 0, fresh: bool = False) -> Out:
    """The list page shared by /groups and the panel button."""
    L = ctx.lang
    query = {"blocked": {"$ne": True}}
    total = await col("groups").count_documents(query)
    start, pages, page = page_bounds(total, want, PAGE)
    docs = await col("groups").find(query).sort("last_active", -1).skip(start).limit(PAGE).to_list(PAGE)
    infos = await asyncio.gather(*(resolve_group(ctx.bot, g, fresh) for g in docs))

    lines, gone, linkless = [], 0, 0
    n = start
    for g, info in zip(docs, infos):
        if info["gone"]:
            gone += 1
            continue
        n += 1
        title = esc((g.get("title") or "").strip() or str(g["chat_id"]))
        members = f" · 👥 {fnum(info['members'], L)}" if info["members"] is not None else ""
        if info["error"]:
            link_line = _t(L, "⚠️ تلگرام جواب نداد؛ دوباره تلاش کن", "⚠️ Telegram did not answer; try again")
        elif info["link"]:
            mark = "🌐" if info["kind"] == "public" else "🔐"
            link_line = f"{mark} {esc(info['link'])}"
        else:
            linkless += 1
            link_line = _t(L, "🔒 لینک ندارد", "🔒 no link")
        lines.append(f"<b>{fnum(n, L)}. {title}</b>{members}\n{link_line}\n"
                     f"🆔 <code>{g['chat_id']}</code> · 🕒 {_ago(g.get('last_active'), L)}")
    body = "\n\n".join(lines) or _t(L, "هنوز گروهی ثبت نشده. ربات را به یک گروه اضافه کن یا یک پیام در گروه بفرست.",
                                   "No group is recorded yet. Add the bot to a group or send a message there.")
    notes = []
    if linkless:
        notes.append(_t(L, "🔒 برای گرفتن لینک، ربات را در آن گروه ادمین کن و دسترسی «دعوت کاربران» بده.",
                        "🔒 To get a link, make the bot an admin of that group with the “invite users” right."))
    if gone:
        notes.append(_t(L, f"ℹ️ {fnum(gone, L)} گروه که ربات دیگر در آن نیست از لیست حذف شد.",
                        f"ℹ️ {fnum(gone, L)} group(s) the bot is no longer in were removed from the list."))
    text = (head(ctx, "ttl_adm") + _t(L, "🔗 <b>لینک گروه‌ها</b>", "🔗 <b>Group links</b>")
            + f"  <i>{fnum(page + 1, L)}/{fnum(pages, L)} · {fnum(total, L)}</i>\n\n" + body
            + ("\n\n" + "\n".join(notes) if notes else ""))
    rows = []
    pg = pager(ctx, "adgl", page, pages)
    if pg:
        rows.append(pg)
    rows.append([(_t(L, "🔄 تازه‌سازی لینک‌ها", "🔄 Refresh links"), "adgl", f"{page}:r")])
    rows.append(_back(ctx))
    return Out(text, rows)


# ---- admin panel page ---------------------------------------------------------------------------------------
@action("adgl")
async def groups_panel(ctx, arg):
    if not await _need(ctx, NEED):
        return _deny(ctx)
    want, fresh = _parse_arg(arg)
    out = await _page(ctx, want, fresh)
    await alog(ctx.uid, "group_links", target=f"panel page {want + 1}")
    return out


# ---- slash command ------------------------------------------------------------------------------------------
@acmd("groups", NEED, "/groups [page | refresh]", "لینک گروه‌هایی که ربات داخلشونه", "Links of the groups the bot is in")
async def c_groups(e: Env):
    msg = e.message
    if msg.chat.type != "private":
        return await e.say(e.t("🔒 این دستور را در پیوی ربات بزن؛ لینک گروه‌های خصوصی نباید جلوی بقیه نمایش داده شود.",
                               "🔒 Use this command in the bot's private chat; private group links must not be shown in front of others."))
    ctx = Ctx(e.uid, e.lang, msg.chat.id, msg.chat.type, msg.from_user, e.bot, message=msg)
    word = to_ascii_digits(e.args[0]).strip().lower() if e.args else ""
    fresh = word in ("refresh", "r", "تازه", "تازه‌سازی", "بروزرسانی")
    want = int(word) - 1 if word.isdigit() and int(word) > 0 else 0  # typed pages count from 1
    out = await _page(ctx, want, fresh)
    await alog(e.uid, "group_links", target=f"cmd {'refresh' if fresh else want + 1}")
    await msg.answer(out.text, reply_markup=markup(ctx, out.rows))


# ---- keep the registry current ---------------------------------------------------------------------------
@router.my_chat_member()
async def on_bot_membership(upd: ChatMemberUpdated):
    """The bot was added to / removed from a group: record it, so /groups is right before anybody writes there."""
    chat = upd.chat
    if chat.type not in ("group", "supergroup"):
        return
    status = upd.new_chat_member.status
    try:
        if status in ("member", "administrator"):
            await note_group(chat.id, chat.title or "")
            if chat.username:
                await col("groups").update_one({"chat_id": chat.id}, {"$set": {"username": chat.username}})
        elif status in ("left", "kicked"):
            await col("groups").update_one({"chat_id": chat.id}, {"$set": {"blocked": True, "left_at": int(time.time())}})
    except Exception:
        log.exception("could not record membership change for %s", chat.id)
