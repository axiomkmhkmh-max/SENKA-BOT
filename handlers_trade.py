"""Trade panels.

Hub (command "ترید" / "trade"): your open session if you have one, otherwise the choices:
  - one-to-one trade with a player in this place
  - open a group table (3 to 6 players, pooled and shared)
  - join an open group table in this place
  - your trade history

Callback codes: trdhub, trdnew:<uid>, trdgrp, trdjoin:<tid>, trdlog, trdv:<tid>, trdadd:<tid>, trdi:<tid>:<item>,
trdrm:<tid>, trdr:<tid>:<item>, trdc:<tid>:<coins>, trdok:<tid>, trdx:<tid>.
"""
from data_items import iname
from database import col
from i18n import esc, fnum
from service_player import get_char
from service_trade import (TRADE_GROUP_MAX, TRADE_GROUP_MIN, add_item, busy_session, cancel, confirm, get_session,
                           history, join_group, nearby_players, open_group, open_pair, open_tables, remove_item, set_coins)
from ui import SEP, Out, action, head, nav


def T(ctx, fa, en):
    return fa if ctx.lang == "fa" else en


ERR = {
    "level": ("برای ترید باید حداقل لول ۱۰ باشی.", "You need at least level 10 to trade."),
    "new": ("حساب تازه‌ساخته تا مدتی نمی‌تونه ترید کنه.", "New accounts cannot trade yet."),
    "busy": ("یکی از شما الان یه ترید بازی داره.", "One of you already has an open trade."),
    "self": ("با خودت نمی‌تونی ترید کنی.", "You cannot trade with yourself."),
    "missing": ("این آیتم رو دیگه نداری.", "You no longer have that item."),
    "lines": ("حداکثر ۸ نوع آیتم توی هر ترید.", "Up to 8 item types per trade."),
    "funds": ("سکه‌ی کافی نداری.", "Not enough coins."),
    "closed": ("این ترید بسته شده.", "This trade is closed."),
    "full": ("میز ترید پر شده.", "The trade table is full."),
    "group_min": (f"میز گروهی حداقل {TRADE_GROUP_MIN} نفر می‌خواد.", f"A group table needs at least {TRADE_GROUP_MIN} players."),
    "waiting": ("تأیید شد. منتظر بقیه باش.", "Confirmed. Waiting for the others."),
    "done": ("ترید انجام شد! 🤝", "Trade complete! 🤝"),
    "error": ("ترید ناموفق بود؛ آیتم‌ها برگشتن.", "The trade failed; items were returned."),
    "noreg": ("اول ثبت‌نام کن.", "Register first."),
    "left": ("از میز بیرون اومدی.", "You left the table."),
    "ok": ("", ""),
}


def _err(ctx, code):
    fa, en = ERR.get(code, ("یه مشکلی پیش اومد.", "Something went wrong."))
    return fa if ctx.lang == "fa" else en


def _offer_lines(offer, L):
    items = offer.get("items") or {}
    lines = [f"• {esc(iname(i, L))} ×{fnum(q, L)}" for i, q in items.items()] or ["—"]
    lines.append(f"🪙 {fnum(int(offer.get('coins', 0)), L)}")
    return lines


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
    return Out("\n".join(lines), rows + [nav(ctx)])


@action("trdnew")
async def trade_new(ctx, arg):
    tid, err = await open_pair(ctx.uid, int(arg))
    if err:
        return Out(alert=_err(ctx, err))
    return await trade_view(ctx, tid)


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
    return await trade_view(ctx, tid)


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
    if ctx.uid in members:
        rows.append([(T(ctx, "➕ آیتم", "➕ Item"), "trdadd", tid), (T(ctx, "➖ آیتم", "➖ Item"), "trdrm", tid)])
        rows.append([(T(ctx, "🪙 ۱۰۰", "🪙 100"), "trdc", f"{tid}:100"), (T(ctx, "🪙 ۱٬۰۰۰", "🪙 1,000"), "trdc", f"{tid}:1000"),
                     (T(ctx, "🪙 صفر", "🪙 Zero"), "trdc", f"{tid}:0")])
        rows.append([(T(ctx, "✅ تأیید", "✅ Confirm"), "trdok", tid),
                     (T(ctx, "❌ لغو / ترک", "❌ Cancel / leave"), "trdx", tid)])
    elif doc["kind"] == "group" and len(members) < TRADE_GROUP_MAX:
        rows.append([(T(ctx, "➕ پیوستن", "➕ Join"), "trdjoin", tid)])
    rows.append(nav(ctx, ("trdhub", "")))
    return Out("\n".join(lines), rows)


@action("trdadd")
async def trade_add_list(ctx, tid):
    from service_economy import inv_get
    inv = await inv_get(ctx.uid)
    items = [(i, q) for i, q in (inv.get("items") or {}).items() if q > 0][:12]
    rows = [[(f"{iname(i, ctx.lang)} ×{q}", "trdi", f"{tid}:{i}")] for i, q in items]
    rows.append(nav(ctx, ("trdv", tid)))
    return Out(T(ctx, "کدوم آیتم رو بذارم روی میز؟", "Which item do you want to put on the table?"), rows)


@action("trdi")
async def trade_add_pick(ctx, arg):
    tid, _, item = arg.partition(":")
    code = await add_item(tid, ctx.uid, item)
    if code != "ok":
        return Out(alert=_err(ctx, code))
    return await trade_view(ctx, tid)


@action("trdrm")
async def trade_rm_list(ctx, tid):
    doc = await get_session(tid, ctx.uid)
    if not doc:
        return Out(_err(ctx, "closed"), [nav(ctx)])
    mine = (doc["offers"].get(str(ctx.uid)) or {}).get("items") or {}
    rows = [[(f"{iname(i, ctx.lang)} ×{q}", "trdr", f"{tid}:{i}")] for i, q in mine.items()]
    rows.append(nav(ctx, ("trdv", tid)))
    return Out(T(ctx, "کدوم آیتم رو از میز برداریم؟", "Which item do you want to take off the table?"), rows)


@action("trdr")
async def trade_rm_pick(ctx, arg):
    tid, _, item = arg.partition(":")
    code = await remove_item(tid, ctx.uid, item)
    if code != "ok":
        return Out(alert=_err(ctx, code))
    return await trade_view(ctx, tid)


@action("trdc")
async def trade_coins(ctx, arg):
    tid, _, amount = arg.partition(":")
    code = await set_coins(tid, ctx.uid, int(amount or 0))
    if code != "ok":
        return Out(alert=_err(ctx, code))
    return await trade_view(ctx, tid)


@action("trdok")
async def trade_confirm(ctx, tid):
    code = await confirm(tid, ctx.uid)
    if code == "waiting":
        return await trade_view(ctx, tid)
    if code == "done":
        return Out(_err(ctx, "done"), [nav(ctx, ("trdhub", ""))])
    return Out(alert=_err(ctx, code)) if code != "closed" else Out(_err(ctx, "closed"), [nav(ctx, ("trdhub", ""))])


@action("trdx")
async def trade_cancel(ctx, tid):
    code = await cancel(tid, ctx.uid)
    if code == "left":
        return Out(_err(ctx, "left"), [nav(ctx, ("trdhub", ""))])
    return Out(T(ctx, "ترید لغو شد.", "Trade cancelled."), [nav(ctx, ("trdhub", ""))])
