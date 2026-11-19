"""Master and apprentice panels (rules and data: service_mentor.py).

Command: «استاد» / «شاگرد» / «mentor» (also under More > Social).

Callback codes: mnt (panel), mntfind (stronger players to ask), mntask (type a name or id), mntreq:<master>,
mntcr (cancel my request), mntrq (the master's waiting requests), mntok:<app>, mntno:<app>, mntap:<app>,
mntgf:<app>:<page> (book list), mntgi:<app>:<item> (give one), mntrl:<app> / mntrx:<app> (release, confirm),
mntlv / mntlx (leave my master, confirm).
Typed prompt: mnt_who.
"""
import logging
import time

from data_items import ALL, iname
from database import col
from i18n import esc, fnum
from service_mentor import (GIFT_PER_DAY, MAX_APPRENTICES, MENTOR_GAP, MENTOR_MIN_LEVEL, REQUEST_TTL, accept,
                            apprentices_of, cancel_request, decline, end, find_masters, gift, gifts_left, giftable,
                            mentorship_of, open_request, request_master, requests_for, xp_pct)
from service_player import get_char, user_lang
from service_trade import find_partner
from ui import Ctx, Out, action, head, input_handler, markup, nav

log = logging.getLogger("senka.mentor")

PAGE = 8


def T(ctx, fa, en):
    return fa if ctx.lang == "fa" else en


def _pct_text(p: float) -> str:
    return f"{p:g}"


ERR = {
    "noreg": ("اول ثبت‌نام کن.", "Register first."),
    "self": ("با خودت نمی‌تونی.", "You cannot pick yourself."),
    "unknown": ("پلیری با این نام یا شناسه پیدا نشد.", "No player found with that name or id."),
    "has_master": ("این شاگرد از قبل استاد داره.", "That apprentice already has a master."),
    "master_is_apprentice": ("اون پلیر خودش شاگرده و نمی‌تونه استاد بشه.", "That player is an apprentice and cannot be a master."),
    "app_is_master": ("تو خودت شاگرد داری؛ نمی‌تونی همزمان شاگرد باشی.", "You have apprentices of your own; you cannot also be one."),
    "app_low": (f"برای شاگردی باید حداقل لول ۵ باشی.", "You need at least level 5 to be an apprentice."),
    "new": ("حساب تازه‌ساخته تا مدتی نمی‌تونه وارد این سیستم بشه.", "A brand-new account cannot join this yet."),
    "master_low": (f"استاد باید حداقل لول {MENTOR_MIN_LEVEL} باشه.", f"A master must be at least level {MENTOR_MIN_LEVEL}."),
    "gap": (f"استاد باید حداقل {MENTOR_GAP} لول از تو بالاتر باشه.", f"A master must be at least {MENTOR_GAP} levels above you."),
    "full": (f"این استاد ظرفیتش (حداکثر {MAX_APPRENTICES} شاگرد) پره.", f"That master is full (at most {MAX_APPRENTICES} apprentices)."),
    "pending": ("یه درخواست باز داری؛ اول لغوش کن یا منتظر جواب بمون.", "You already have an open request; cancel it or wait for the answer."),
    "gone": ("این درخواست دیگه وجود نداره.", "That request no longer exists."),
    "notmine": ("این پلیر شاگرد تو نیست.", "That player is not your apprentice."),
    "notgift": ("فقط کتاب‌های رساله و خاطرات رو می‌تونی هدیه بدی.", "You can only give Treatise and Memoir books."),
    "limit": (f"امروز به این شاگرد {GIFT_PER_DAY} کتاب دادی؛ فردا دوباره.", f"You gave this apprentice {GIFT_PER_DAY} books today; try again tomorrow."),
    "missing": ("این کتاب رو دیگه نداری.", "You no longer have that book."),
    "bag_full": ("کوله‌ی شاگرد پره.", "The apprentice's bag is full."),
}


def _err(ctx, code):
    fa, en = ERR.get(code, ("یه مشکلی پیش اومد.", "Something went wrong."))
    return fa if ctx.lang == "fa" else en


async def _ctx_for(ctx, uid):
    return Ctx(uid, (await user_lang(uid)) or "en", uid, "private", None, ctx.bot)


async def _dm(ctx, uid, fa, en, rows=None):
    """A private note to another player in THEIR language. Best effort: a blocked bot never breaks the action."""
    try:
        c = await _ctx_for(ctx, uid)
        await ctx.bot.send_message(uid, fa if c.lang == "fa" else en, reply_markup=markup(c, rows(c)) if rows else None)
    except Exception as e:
        log.debug("mentor note skipped: %s", e)


def _name(ch):
    return esc((ch or {}).get("name", "?"))


# ---- main panel --------------------------------------------------------------------------------------------------------
@action("mnt")
async def mentor_panel(ctx, arg):
    ch = await get_char(ctx.uid)
    if not ch:
        return Out(_err(ctx, "noreg"), [nav(ctx)])
    pct = await xp_pct()
    lines = [head(ctx, "ttl_mentor")]
    rows = []
    mine = await mentorship_of(ctx.uid)
    apps = await apprentices_of(ctx.uid)
    if mine:  # I am an apprentice
        m = await get_char(mine["master"])
        lines.append(T(ctx, f"🎓 استاد تو: <b>{_name(m)}</b> · لول {fnum((m or {}).get('level', 0), 'fa')}",
                       f"🎓 Your master: <b>{_name(m)}</b> · level {fnum((m or {}).get('level', 0), 'en')}"))
        lines.append(T(ctx, f"از هر نبرد و دانجنی که می‌بری {_pct_text(pct)}٪ تجربه‌ی اضافه به‌عنوان پاداش آموزش می‌گیری. "
                            "هر وقت به لول استادت برسی فارغ‌التحصیل می‌شی.",
                       f"You earn {_pct_text(pct)}% extra XP as a mentoring bonus from every battle and dungeon you win. "
                       "You graduate when you reach your master's level."))
        rows.append([(T(ctx, "🚪 ترک استاد", "🚪 Leave master"), "mntlv", "")])
    if apps or (not mine and int(ch["level"]) >= MENTOR_MIN_LEVEL):  # I am (or can be) a master
        waiting = await requests_for(ctx.uid)
        lines.append(T(ctx, f"📚 شاگردهای تو ({len(apps)}/{MAX_APPRENTICES}):", f"📚 Your apprentices ({len(apps)}/{MAX_APPRENTICES}):"))
        if not apps:
            lines.append("—")
        for d in apps:
            a = await get_char(d["_id"])
            lines.append(f"• <b>{_name(a)}</b> · {T(ctx, 'لول', 'lvl')} {fnum((a or {}).get('level', 0), ctx.lang)} · "
                         f"{T(ctx, 'پاداش تجربه‌ی شاگرد', 'Apprentice bonus XP')}: {fnum(int(d.get('xp_total', 0)), ctx.lang)}")
            rows.append([(f"🎓 {(a or {}).get('name', '?')}", "mntap", str(d["_id"]))])
        if apps:
            lines.append(T(ctx, f"از هر نبرد و دانجن شاگردهات {_pct_text(pct)}٪ تجربه‌ی اضافه می‌گیری و می‌تونی بهشون کتاب رساله و خاطرات هدیه بدی.",
                           f"You earn {_pct_text(pct)}% extra XP from your apprentices' battles and dungeons and can give them Treatise and Memoir books."))
        else:
            lines.append(T(ctx, "شاگردها از لول پایین‌تر بهت درخواست می‌دن و اینجا می‌بینی‌شون.",
                           "Lower-level players send you requests and you see them here."))
        rows.insert(0, [(T(ctx, f"📬 درخواست‌ها ({len(waiting)})", f"📬 Requests ({len(waiting)})"), "mntrq", "")])
    if not mine and not apps:  # I can ask for a master
        req = await open_request(ctx.uid)
        if req:
            m = await get_char(req["master"])
            lines.append(T(ctx, f"⏳ درخواستت برای <b>{_name(m)}</b> منتظر جواب مونده.", f"⏳ Your request to <b>{_name(m)}</b> is waiting for an answer."))
            rows.append([(T(ctx, "❌ لغو درخواست", "❌ Cancel request"), "mntcr", "")])
        else:
            lines.append(T(ctx, f"می‌خوای شاگرد بشی؟ از یه پلیر قوی‌تر (حداقل {MENTOR_GAP} لول بالاتر از تو و لول {MENTOR_MIN_LEVEL}+) بخواه استادت بشه.",
                           f"Want to be an apprentice? Ask a stronger player (at least {MENTOR_GAP} levels above you, level {MENTOR_MIN_LEVEL}+) to be your master."))
            rows.append([(T(ctx, "🎓 پیدا کردن استاد", "🎓 Find a master"), "mntfind", "")])
    rows.append(nav(ctx))
    return Out("\n".join(lines), rows)


# ---- asking for a master -----------------------------------------------------------------------------------------------
@action("mntfind")
async def mentor_find(ctx, arg):
    ch = await get_char(ctx.uid)
    if not ch:
        return Out(_err(ctx, "noreg"), [nav(ctx)])
    cands = await find_masters(ch)
    lines = [head(ctx, "ttl_mentor"), T(ctx, "استادهای ممکن (نزدیک‌ترین بالاتر از تو اول):", "Possible masters (closest above you first):")]
    rows = []
    if not cands:
        lines.append(T(ctx, "الان استاد آزادی پیدا نشد. می‌تونی اسم یا شناسه‌ی یه پلیر رو بفرستی.", "No free master found right now. You can send a player's name or id."))
    for c in cands:
        rows.append([(f"{c['name']} · {c['level']} · {c['race']}", "mntreq", str(c["user_id"]))])
    rows.append([(T(ctx, "✍️ نام یا شناسه", "✍️ Name or id"), "mntask", "")])
    rows.append(nav(ctx, ("mnt", "")))
    return Out("\n".join(lines), rows)


@action("mntask")
async def mentor_ask(ctx, arg):
    await col("inputs").update_one({"user_id": ctx.uid}, {"$set": {"kind": "mnt_who", "at": int(time.time())}}, upsert=True)
    return Out(head(ctx, "ttl_mentor") + T(ctx, "اسم پلیر یا شناسه‌ی عددیش رو بفرست.\nبرای انصراف بنویس «لغو».",
                                           "Send the player's name or numeric id.\nWrite cancel to stop."), [nav(ctx, ("mnt", ""))])


async def _send_request(ctx, master_uid: int):
    """-> error text or None. The request lands in the master's panel and they get a private note with Accept / Decline."""
    code = await request_master(ctx.uid, master_uid)
    if code != "ok":
        return _err(ctx, code)
    me = await get_char(ctx.uid)
    await _dm(ctx, master_uid,
              f"📬 <b>{_name(me)}</b> (لول {me['level']}) می‌خواد شاگردت بشه.",
              f"📬 <b>{_name(me)}</b> (level {me['level']}) wants to be your apprentice.",
              lambda c: [[(T(c, "✅ قبول", "✅ Accept"), "mntok", str(ctx.uid)), (T(c, "❌ رد", "❌ Decline"), "mntno", str(ctx.uid))]])
    return None


@action("mntreq")
async def mentor_request(ctx, arg):
    err = await _send_request(ctx, int(arg))
    if err:
        return Out(alert=err)
    return await mentor_panel(ctx, "")


@input_handler("mnt_who")
async def mentor_who_input(ctx, text):
    target = await find_partner(text)
    if target is None:
        await col("inputs").update_one({"user_id": ctx.uid}, {"$set": {"kind": "mnt_who", "at": int(time.time())}}, upsert=True)
        return Out(_err(ctx, "unknown") + T(ctx, "\nدوباره بفرست یا بنویس «لغو».", "\nSend it again or write cancel."))
    err = await _send_request(ctx, target)
    if err:
        return Out(err, [nav(ctx, ("mnt", ""))])
    return await mentor_panel(ctx, "")


@action("mntcr")
async def mentor_cancel_request(ctx, arg):
    master = await cancel_request(ctx.uid)
    if master:
        me = await get_char(ctx.uid)
        await _dm(ctx, master, f"{_name(me)} درخواست شاگردی‌اش رو پس گرفت.", f"{_name(me)} withdrew their apprentice request.")
    return await mentor_panel(ctx, "")


# ---- the master's side -------------------------------------------------------------------------------------------------
@action("mntrq")
async def mentor_requests(ctx, arg):
    waiting = await requests_for(ctx.uid)
    lines = [head(ctx, "ttl_mentor"), T(ctx, f"📬 درخواست‌های شاگردی ({len(waiting)}):", f"📬 Apprentice requests ({len(waiting)}):")]
    rows = []
    if not waiting:
        lines.append("—")
    for r in waiting:
        a = await get_char(r["_id"])
        if not a:
            continue
        lines.append(f"• <b>{_name(a)}</b> · {T(ctx, 'لول', 'lvl')} {fnum(a['level'], ctx.lang)} · {a['race']}")
        rows.append([(f"✅ {a['name']} · {a['level']}", "mntok", str(r["_id"])), ("❌", "mntno", str(r["_id"]))])
    lines.append(T(ctx, f"درخواست‌ها {REQUEST_TTL // 86400} روز اعتبار دارن.", f"Requests last {REQUEST_TTL // 86400} days."))
    rows.append(nav(ctx, ("mnt", "")))
    return Out("\n".join(lines), rows)


@action("mntok")
async def mentor_accept(ctx, arg):
    app = int(arg)
    code = await accept(ctx.uid, app)
    if code != "ok":
        return Out(_err(ctx, code), [nav(ctx, ("mnt", ""))])
    me = await get_char(ctx.uid)
    await _dm(ctx, app, f"🎓 <b>{_name(me)}</b> شاگردیت رو قبول کرد! حالا استادته.",
              f"🎓 <b>{_name(me)}</b> accepted you as an apprentice! They are your master now.")
    return await mentor_panel(ctx, "")


@action("mntno")
async def mentor_decline(ctx, arg):
    app = int(arg)
    if await decline(ctx.uid, app):
        me = await get_char(ctx.uid)
        await _dm(ctx, app, f"{_name(me)} درخواست شاگردیت رو رد کرد.", f"{_name(me)} declined your apprentice request.")
    return await mentor_requests(ctx, "")


@action("mntap")
async def mentor_apprentice(ctx, arg):
    app = int(arg)
    doc = await mentorship_of(app)
    if not doc or int(doc["master"]) != ctx.uid:
        return Out(_err(ctx, "notmine"), [nav(ctx, ("mnt", ""))])
    a = await get_char(app)
    left = await gifts_left(doc)
    lines = [head(ctx, "ttl_mentor"),
             f"🎓 <b>{_name(a)}</b> · {T(ctx, 'لول', 'lvl')} {fnum((a or {}).get('level', 0), ctx.lang)}",
             T(ctx, f"پاداش تجربه‌ای که شاگرد از آموزش تو گرفته: {fnum(int(doc.get('xp_total', 0)), 'fa')}",
               f"Bonus XP this apprentice earned from your teaching: {fnum(int(doc.get('xp_total', 0)), 'en')}"),
             T(ctx, f"🎁 هدیه‌ی امروز: {left} از {GIFT_PER_DAY} باقی مونده", f"🎁 Gifts today: {left} of {GIFT_PER_DAY} left")]
    rows = [[(T(ctx, "🎁 هدیه (رساله و خاطرات)", "🎁 Give (Treatise & Memoir)"), "mntgf", f"{app}:0")],
            [(T(ctx, "🚪 آزاد کردن شاگرد", "🚪 Release apprentice"), "mntrl", str(app))], nav(ctx, ("mnt", ""))]
    return Out("\n".join(lines), rows)


@action("mntgf")
async def mentor_gift_list(ctx, arg):
    a, _, pg = arg.partition(":")
    app = int(a)
    doc = await mentorship_of(app)
    if not doc or int(doc["master"]) != ctx.uid:
        return Out(_err(ctx, "notmine"), [nav(ctx, ("mnt", ""))])
    items = await giftable(ctx.uid)
    pages = max(1, -(-len(items) // PAGE))
    page = min(max(0, int(pg)) if pg.isdigit() else 0, pages - 1)
    ap = await get_char(app)
    left = await gifts_left(doc)
    lines = [head(ctx, "ttl_mentor"),
             T(ctx, f"🎁 کدوم کتاب رو به <b>{_name(ap)}</b> بدم؟ (امروز {left} تا مونده)", f"🎁 Which book for <b>{_name(ap)}</b>? ({left} left today)")]
    rows = [[(f"{iname(i, ctx.lang)} ×{q}", "mntgi", f"{app}:{i}")] for i, q in items[page * PAGE:(page + 1) * PAGE]]
    if not items:
        lines.append(T(ctx, "توی کوله‌ات کتاب رساله یا خاطرات نداری.", "You have no Treatise or Memoir books in your bag."))
    if pages > 1:
        pager = []
        if page > 0:
            pager.append(("◀️", "mntgf", f"{app}:{page - 1}"))
        pager.append((f"{page + 1}/{pages}", "mntgf", f"{app}:{page}"))
        if page < pages - 1:
            pager.append(("▶️", "mntgf", f"{app}:{page + 1}"))
        rows.append(pager)
    rows.append(nav(ctx, ("mntap", str(app))))
    return Out("\n".join(lines), rows)


@action("mntgi")
async def mentor_gift_give(ctx, arg):
    a, _, item = arg.partition(":")
    app = int(a)
    code = await gift(ctx.uid, app, item)
    if code == "full":
        return Out(alert=_err(ctx, "bag_full"))
    if code != "ok":
        return Out(alert=_err(ctx, code))
    me = await get_char(ctx.uid)
    await _dm(ctx, app, f"🎁 استادت <b>{_name(me)}</b> بهت «{iname(item, 'fa')}» هدیه داد! توی کوله‌ات هست.",
              f"🎁 Your master <b>{_name(me)}</b> gave you “{iname(item, 'en')}”! It is in your bag.")
    out = await mentor_gift_list(ctx, f"{app}:0")
    out.alert = T(ctx, f"✅ {iname(item, 'fa')} داده شد.", f"✅ {iname(item, 'en')} given.")
    return out


@action("mntrl")
async def mentor_release_ask(ctx, arg):
    app = int(arg)
    doc = await mentorship_of(app)
    if not doc or int(doc["master"]) != ctx.uid:
        return Out(_err(ctx, "notmine"), [nav(ctx, ("mnt", ""))])
    a = await get_char(app)
    return Out(T(ctx, f"مطمئنی می‌خوای <b>{_name(a)}</b> رو آزاد کنی؟", f"Release <b>{_name(a)}</b> as your apprentice?"),
               [[(T(ctx, "✅ آره", "✅ Yes"), "mntrx", str(app)), (T(ctx, "↩️ نه", "↩️ No"), "mntap", str(app))]])


@action("mntrx")
async def mentor_release(ctx, arg):
    app = int(arg)
    doc = await mentorship_of(app)
    if not doc or int(doc["master"]) != ctx.uid:
        return Out(_err(ctx, "notmine"), [nav(ctx, ("mnt", ""))])
    await end(app)
    me = await get_char(ctx.uid)
    await _dm(ctx, app, f"استادت {_name(me)} شاگردی‌ات رو تموم کرد.", f"Your master {_name(me)} ended the apprenticeship.")
    return await mentor_panel(ctx, "")


# ---- the apprentice's side ---------------------------------------------------------------------------------------------
@action("mntlv")
async def mentor_leave_ask(ctx, arg):
    if not await mentorship_of(ctx.uid):
        return await mentor_panel(ctx, "")
    return Out(T(ctx, "مطمئنی می‌خوای استادت رو ترک کنی؟", "Leave your master?"),
               [[(T(ctx, "✅ آره", "✅ Yes"), "mntlx", ""), (T(ctx, "↩️ نه", "↩️ No"), "mnt", "")]])


@action("mntlx")
async def mentor_leave(ctx, arg):
    master = await end(ctx.uid)
    if master:
        me = await get_char(ctx.uid)
        await _dm(ctx, master, f"شاگردت {_name(me)} رفت.", f"Your apprentice {_name(me)} left.")
    return await mentor_panel(ctx, "")
