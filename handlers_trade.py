"""Trade panels.

Hub (command "ترید" / "trade"): your open session if you have one, otherwise the choices:
  - one-to-one trade with a player in this place
  - open a group table (3 to 6 players, pooled and shared)
  - join an open group table in this place
  - your trade history

Callback codes: trdhub, trdnew:<uid>, trdgrp, trdjoin:<tid>, trdlog, trdv:<tid>, trdadd:<tid>, trdi:<tid>:<item>,
trdrm:<tid>, trdr:<tid>:<item>, trdc:<tid>:<coins>, trdok:<tid>, trdx:<tid>.
"""
import logging

from bson import ObjectId

from data_items import iname
from database import col
from i18n import esc, fnum
from service_player import get_char, user_lang
from service_trade import (TRADE_GROUP_MAX, TRADE_GROUP_MIN, add_item, busy_session, cancel, confirm, get_session,
                           history, join_group, nearby_players, open_group, open_pair, open_tables, remove_item,
                           set_coins, set_view)
from ui import SEP, Ctx, Out, action, head, markup, nav

log = logging.getLogger("senka.trade")


def T(ctx, fa, en):
    return fa if ctx.lang == "fa" else en


ERR = {
    "level": ("برای ترید باید حداقل لول ۱۰ باشی.", "You need at least level 10 to trade."),
    "new": ("حساب تازه‌ساخته تا مدتی نمی‌تونه ترید کنه.", "New accounts cannot trade yet."),
    "busy": ("یکی از شما الان یه ترید بازی داره.", "One of you already has an open trade."),
    "self": ("با خودت نمی‌تونی ترید کنی.", "You cannot trade with yourself."),
    "missing": ("این آیتم رو دیگه نداری.", "You no longer have that item."),
    "notrade": ("این آیتم قابل ترید نیست (مثل کلید دانجن یا سلاح نژاد).", "This item cannot be traded (like dungeon keys or race weapons)."),
    "race": ("زره و کارت نژادی فقط به بازیکن همان نژاد می‌رسد؛ ترید انجام نشد.", "Race armour and race cards only go to a player of that race; the trade did not go through."),
    "lines": ("حداکثر ۸ نوع آیتم توی هر ترید.", "Up to 8 item types per trade."),
    "funds": ("سکه‌ی کافی نداری.", "Not enough coins."),
    "closed": ("این ترید بسته شده.", "This trade is closed."),
    "full": ("میز ترید پر شده.", "The trade table is full."),
    "group_min": (f"میز گروهی حداقل {TRADE_GROUP_MIN} نفر می‌خواد.", f"A group table needs at least {TRADE_GROUP_MIN} players."),
    "waiting": ("تأیید شد. منتظر بقیه باش.", "Confirmed. Waiting for the others."),
    "done": ("ترید انجام شد! 🤝", "Trade complete! 🤝"),
    "error": ("ترید ناموفق بود؛ آیتم‌ها برگشتن.", "The trade failed; items were returned."),
    "noreg": ("اول ثبت‌نام کن.", "Register first."),
    "stale": ("پیشنهاد عوض شد. دوباره نگاه کن و بعد تأیید کن.", "The offer just changed. Look again, then confirm."),
    "other_level": ("طرف مقابل هنوز به لول ۱۰ نرسیده.", "The other player is below level 10."),
    "other_new": ("حساب طرف مقابل تازه‌ساخته‌ست و فعلاً نمی‌تونه ترید کنه.", "The other player's account is too new to trade."),
    "other_noreg": ("طرف مقابل ثبت‌نام نکرده.", "The other player is not registered."),
    "left": ("از میز بیرون اومدی.", "You left the table."),
    "ok": ("", ""),
}


def _pubify(rows):
    """Session buttons are shared: a group table message is seen by every member, so the signature must not
    bind them to whoever opened it. Access is still checked on each press (service_trade.get_session).
    trdnew stays private: its argument is a player id, so only the one who was offered it may press it."""
    out = []
    for row in rows:
        new = []
        for b in row:
            if b[1].startswith("trd") and b[1] != "trdnew":
                style = b[4] if len(b) > 4 else "auto"
                b = (b[0], b[1], b[2] if len(b) > 2 else "", True, style)
            new.append(b)
        out.append(new)
    return out


def _err(ctx, code):
    fa, en = ERR.get(code, ("یه مشکلی پیش اومد.", "Something went wrong."))
    return fa if ctx.lang == "fa" else en


def _offer_lines(offer, L):
    items = offer.get("items") or {}
    lines = [f"• {esc(iname(i, L))} ×{fnum(q, L)}" for i, q in items.items()] or ["—"]
    lines.append(f"🪙 {fnum(int(offer.get('coins', 0)), L)}")
    return lines


async def _member_ctx(ctx, uid, chat_id):
    return Ctx(uid, (await user_lang(uid)) or "en", chat_id, "private", None, ctx.bot)


async def _refresh_others(ctx, tid):
    """The other players' open table message is re-drawn in place, so nobody keeps looking (and confirming) an
    old offer. Best effort: a blocked bot, a deleted message or "not modified" must never break the trade."""
    try:
        doc = await col("trades").find_one({"_id": ObjectId(tid)})
        for m in (doc or {}).get("members", []):
            ref = (doc.get("views") or {}).get(str(m))
            if m == ctx.uid or not ref:
                continue
            try:
                c = await _member_ctx(ctx, m, ref[0])
                out = await trade_view(c, tid)
                await ctx.bot.edit_message_text(out.text, chat_id=ref[0], message_id=ref[1], reply_markup=markup(c, out.rows))
            except Exception as e:
                log.debug("trade refresh skipped: %s", e)
    except Exception:
        log.exception("trade refresh failed")


async def _tell_others(ctx, tid, fa, en):
    """A trade ended (done, cancelled, failed): replace the other players' table with the result, or message them."""
    try:
        doc = await col("trades").find_one({"_id": ObjectId(tid)})
        for m in (doc or {}).get("members", []):
            if m == ctx.uid:
                continue
            ref = (doc.get("views") or {}).get(str(m))
            c = await _member_ctx(ctx, m, ref[0] if ref else m)
            text, kb = (fa if c.lang == "fa" else en), markup(c, [nav(c, ("trdhub", ""))])
            try:
                if not ref:
                    raise LookupError
                await ctx.bot.edit_message_text(text, chat_id=ref[0], message_id=ref[1], reply_markup=kb)
            except Exception:
                try:
                    await ctx.bot.send_message(m, text, reply_markup=kb)
                except Exception as e:
                    log.debug("trade notice skipped: %s", e)
    except Exception:
        log.exception("trade notice failed")


@action("trdhub")
async def trade_hub(ctx, arg):
    L = ctx.lang
    sess = await busy_session(ctx.uid)
    if sess:
        return await trade_view(ctx, str(sess["_id"]))
    ch = await get_char(ctx.uid)
    if not ch:
        return Out(_err(ctx, "noreg"), [nav(ctx)])
    lines = [head(ctx, "ttl_trade"),
             T(ctx, "🤝 دو نفره: یه معامله‌ی مستقیم با یه پلیر همین‌جا.",
               "🤝 One-to-one: a direct deal with a player here."),
             T(ctx, f"👥 گروهی: میز مشترک ({TRADE_GROUP_MIN} تا {TRADE_GROUP_MAX} نفر). همه چیز جمع میشه و بینشون پخش میشه.",
               f"👥 Group: a shared table ({TRADE_GROUP_MIN} to {TRADE_GROUP_MAX} players). Everything is pooled and shared out.")]
    rows = [[(T(ctx, "👥 ساخت میز گروهی", "👥 Open a group table"), "trdgrp", "")]]
    tables = await open_tables(ch["location"])
    for t in tables:
        rows.append([(T(ctx, f"➕ پیوستن به میز ({len(t['members'])} نفر)", f"➕ Join table ({len(t['members'])})"),
                      "trdjoin", str(t["_id"]))])
    people = await nearby_players(ctx.uid, ch["location"])
    if people:
        lines.append(T(ctx, "پلیرهای همین مکان (دو نفره):", "Players here (one-to-one):"))
        for p in people:
            rows.append([(f"{p['name']} · {p['level']} · {p['race']}", "trdnew", str(p["user_id"]))])
    rows.append([(T(ctx, "📜 تاریخچه", "📜 History"), "trdlog", "")])
    return Out("\n".join(lines), _pubify(rows + [nav(ctx)]))


@action("trdnew")
async def trade_new(ctx, arg):
    tid, err = await open_pair(ctx.uid, int(arg))
    if err:
        return Out(alert=_err(ctx, err))
    # the other player gets the live table straight away (in their language, with buttons), not a note to go look for
    try:
        c = await _member_ctx(ctx, int(arg), int(arg))
        theirs = await trade_view(c, tid)
        msg = await ctx.bot.send_message(int(arg), f"🔔 {esc(ctx.user.first_name or '?')}\n" + theirs.text,
                                         reply_markup=markup(c, theirs.rows))
        await set_view(tid, int(arg), int(arg), msg.message_id)
    except Exception as e:
        log.info("trade invite not delivered: %s", e)  # the partner may never have started the bot; «trade» still shows it
    return await trade_view(ctx, tid)


@action("trdv")
async def trade_panel(ctx, arg):
    return await trade_view(ctx, arg)


@action("trdgrp")
async def trade_group_new(ctx, arg):
    tid, err = await open_group(ctx.uid)
    if err:
        return Out(alert=_err(ctx, err))
    return await trade_view(ctx, tid)


@action("trdjoin")
async def trade_join(ctx, tid):
    code = await join_group(tid, ctx.uid)
    if code not in ("ok",):
        return Out(alert=_err(ctx, code))
    out = await trade_view(ctx, tid)
    await _refresh_others(ctx, tid)
    return out


@action("trdlog")
async def trade_log(ctx, arg):
    L = ctx.lang
    rows_db = await history(ctx.uid)
    if not rows_db:
        return Out(T(ctx, "هنوز ترید تمام‌شده‌ای نداری.", "No finished trades yet."), [nav(ctx, ("trdhub", ""))])
    lines = [head(ctx, "ttl_trade")]
    for r in rows_db:
        kind = T(ctx, "گروهی" if r["kind"] == "group" else "دو نفره", "group" if r["kind"] == "group" else "one-to-one")
        lines.append(f"• {kind} · {len(r['members'])} {T(ctx, 'نفر', 'players')}")
    return Out("\n".join(lines), [nav(ctx, ("trdhub", ""))])


async def trade_view(ctx, tid):
    L = ctx.lang
    doc = await get_session(tid, ctx.uid, allow_join=True)
    if not doc:
        return Out(_err(ctx, "closed"), [nav(ctx)])
    members = doc["members"]
    conf = doc.get("confirm") or {}
    lines = [head(ctx, "ttl_trade"),
             T(ctx, "میز گروهی" if doc["kind"] == "group" else "ترید دو نفره",
               "Group table" if doc["kind"] == "group" else "One-to-one trade"), SEP]
    for m in members:
        ch = await get_char(m)
        name = esc((ch or {}).get("name", "?"))
        mark = "✅" if conf.get(str(m)) else "⏳"
        mine = m == ctx.uid
        lines.append(f"<b>{name}</b>{' (تو)' if mine and L == 'fa' else (' (you)' if mine else '')} {mark}")
        lines += _offer_lines(doc["offers"].get(str(m)) or {}, L)
        lines.append("")
    rows = []
    msg = getattr(ctx.cb, "message", None) if ctx.cb is not None else None
    if msg is not None and ctx.uid in members:
        await set_view(tid, ctx.uid, msg.chat.id, msg.message_id)  # so the others' changes can refresh this very message
    if ctx.uid in members:
        rows.append([(T(ctx, "➕ آیتم", "➕ Item"), "trdadd", tid), (T(ctx, "➖ آیتم", "➖ Item"), "trdrm", tid)])
        rows.append([(T(ctx, "🪙 ۱۰۰", "🪙 100"), "trdc", f"{tid}:100"), (T(ctx, "🪙 ۱٬۰۰۰", "🪙 1,000"), "trdc", f"{tid}:1000"),
                     (T(ctx, "🪙 صفر", "🪙 Zero"), "trdc", f"{tid}:0")])
        rows.append([(T(ctx, "✅ تأیید", "✅ Confirm"), "trdok", f"{tid}:{int(doc.get('rev', 0))}"),
                     (T(ctx, "❌ لغو / ترک", "❌ Cancel / leave"), "trdx", tid)])
    elif doc["kind"] == "group" and len(members) < TRADE_GROUP_MAX:
        rows.append([(T(ctx, "➕ پیوستن", "➕ Join"), "trdjoin", tid)])
    rows.append(nav(ctx, ("trdhub", "")))
    return Out("\n".join(lines), _pubify(rows))


TRADE_PAGE = 10


@action("trdadd")
async def trade_add_list(ctx, arg):
    # arg = "<tid>" or "<tid>:<page>". Only tradeable items are listed, and every one of them can be reached
    # (the list used to stop at the first 12 items of the bag, tradeable or not).
    from data_items import ALL
    from service_economy import inv_get
    tid, _, pg = arg.partition(":")
    page = max(0, int(pg)) if pg.isdigit() else 0
    inv = await inv_get(ctx.uid)
    items = sorted(((i, q) for i, q in (inv.get("items") or {}).items() if q > 0 and (ALL.get(i) or {}).get("tradeable")),
                   key=lambda x: iname(x[0], ctx.lang))
    pages = max(1, -(-len(items) // TRADE_PAGE))
    page = min(page, pages - 1)
    rows = [[(f"{iname(i, ctx.lang)} ×{q}", "trdi", f"{tid}:{i}")]
            for i, q in items[page * TRADE_PAGE:(page + 1) * TRADE_PAGE]]
    if pages > 1:
        pager = []
        if page > 0:
            pager.append(("◀️", "trdadd", f"{tid}:{page - 1}"))
        pager.append((f"{page + 1}/{pages}", "trdadd", f"{tid}:{page}"))
        if page < pages - 1:
            pager.append(("▶️", "trdadd", f"{tid}:{page + 1}"))
        rows.append(pager)
    if not items:
        rows.append([(T(ctx, "آیتم قابل تریدی نداری", "No tradeable items"), "trdv", tid)])
    rows.append(nav(ctx, ("trdv", tid)))
    return Out(T(ctx, "کدوم آیتم رو بذارم روی میز؟", "Which item do you want to put on the table?"), _pubify(rows))


@action("trdi")
async def trade_add_pick(ctx, arg):
    tid, _, item = arg.partition(":")
    code = await add_item(tid, ctx.uid, item)
    if code != "ok":
        return Out(alert=_err(ctx, code))
    out = await trade_view(ctx, tid)
    await _refresh_others(ctx, tid)
    return out


@action("trdrm")
async def trade_rm_list(ctx, tid):
    doc = await get_session(tid, ctx.uid)
    if not doc:
        return Out(_err(ctx, "closed"), [nav(ctx)])
    mine = (doc["offers"].get(str(ctx.uid)) or {}).get("items") or {}
    rows = [[(f"{iname(i, ctx.lang)} ×{q}", "trdr", f"{tid}:{i}")] for i, q in mine.items()]
    rows.append(nav(ctx, ("trdv", tid)))
    return Out(T(ctx, "کدوم آیتم رو از میز برداریم؟", "Which item do you want to take off the table?"), _pubify(rows))


@action("trdr")
async def trade_rm_pick(ctx, arg):
    tid, _, item = arg.partition(":")
    code = await remove_item(tid, ctx.uid, item)
    if code != "ok":
        return Out(alert=_err(ctx, code))
    out = await trade_view(ctx, tid)
    await _refresh_others(ctx, tid)
    return out


@action("trdc")
async def trade_coins(ctx, arg):
    tid, _, amount = arg.partition(":")
    code = await set_coins(tid, ctx.uid, int(amount or 0))
    if code != "ok":
        return Out(alert=_err(ctx, code))
    out = await trade_view(ctx, tid)
    await _refresh_others(ctx, tid)
    return out


@action("trdok")
async def trade_confirm(ctx, arg):
    tid, _, rev = arg.partition(":")  # the button carries the version of the table the player was looking at
    code = await confirm(tid, ctx.uid, int(rev) if rev.isdigit() else None)
    if code == "waiting":
        out = await trade_view(ctx, tid)
        await _refresh_others(ctx, tid)  # the others see the ✅ right away
        return out
    if code == "stale":
        out = await trade_view(ctx, tid)  # show the table as it is now, then let them decide again
        out.alert = _err(ctx, "stale")
        return out
    if code == "done":
        await _tell_others(ctx, tid, *ERR["done"])
        return Out(_err(ctx, "done"), [nav(ctx, ("trdhub", ""))])
    if code == "closed":
        return Out(_err(ctx, "closed"), [nav(ctx, ("trdhub", ""))])
    if code in ("missing", "race", "notrade", "error"):  # the trade ended without moving anything: both sides must know
        await _tell_others(ctx, tid, *ERR[code])
        return Out(_err(ctx, code), [nav(ctx, ("trdhub", ""))])
    return Out(alert=_err(ctx, code))


@action("trdx")
async def trade_cancel(ctx, tid):
    code = await cancel(tid, ctx.uid)
    if code == "closed":
        return Out(_err(ctx, "closed"), [nav(ctx, ("trdhub", ""))])
    if code == "left":
        await _refresh_others(ctx, tid)
        return Out(_err(ctx, "left"), [nav(ctx, ("trdhub", ""))])
    await _tell_others(ctx, tid, "ترید توسط طرف مقابل لغو شد.", "The trade was cancelled by the other player.")
    return Out(T(ctx, "ترید لغو شد.", "Trade cancelled."), [nav(ctx, ("trdhub", ""))])
