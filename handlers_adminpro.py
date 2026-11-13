"""Advanced admin hub: main menu, analytics, risk scan and system health.

The hub is what the 'adm' action shows (handlers_admin.admin_panel imports main_menu from here).
Anything that changes data (ban, coins, broadcast, settings, world) still goes through the existing
panels (adu, adw, adc, ads, ...), so their permission checks and admin_logs stay exactly as they were.
"""
import time

from admin_fa import ROLE_FA
from database import col, game_settings, ping
from handlers_admin import ROLES, admin_level, dashboard
from i18n import esc, fnum
from ui import Out, action, chunk, head, input_handler, nav, pager

BOOT = time.time()
BAR = 10
DAY = 86400


def T(ctx, fa, en):
    return fa if ctx.lang == "fa" else en


def _denied(ctx):
    return Out(alert=T(ctx, "دسترسی نداری.", "No permission."))


def _bar(n, top):
    filled = round(BAR * n / top) if top > 0 else 0
    return "█" * filled + "░" * (BAR - filled)


def _back(ctx):
    return nav(ctx, ("adm", ""))


# ---- hub (shown by the 'adm' action) --------------------------------------------------------------------
async def main_menu(ctx, lvl):
    st = await game_settings()
    on = bool(st.get("maintenance"))
    mt = T(ctx, "روشن ✅" if on else "خاموش", "ON ✅" if on else "off")
    role = next((k for k, v in ROLES.items() if v == lvl), "?")
    role = ROLE_FA.get(role, role) if ctx.lang == "fa" else role
    rows = [
        [(T(ctx, "📈 تحلیل", "📈 Analytics"), "apa", ""), (T(ctx, "🚨 اسکن ریسک", "🚨 Risk scan"), "apr", "")],
        [(T(ctx, "🩺 سلامت سیستم", "🩺 Health"), "aph", ""), (T(ctx, "🔄 تازه‌سازی", "🔄 Refresh"), "adm", "")],
        [(T(ctx, "👤 کاربران", "👤 Users"), "adu", ""), (T(ctx, "🌍 دنیا", "🌍 World"), "adw", "")],
        [(T(ctx, "📣 همگانی", "📣 Broadcast"), "adc", ""), (T(ctx, "🎁 هدیه و کد", "🎁 Gifts & codes"), "adg", "")],
        [(T(ctx, "⚙️ تنظیمات زنده", "⚙️ Live settings"), "ads", "0"),
         (T(ctx, f"🔧 تعمیرات: {mt}", f"🔧 Maintenance: {mt}"), "adt", "")],
        [(T(ctx, "📜 لاگ مدیریت", "📜 Admin log"), "adl", ""), (T(ctx, "👑 ادمین‌ها", "👑 Admins"), "ada", "")],
        [(T(ctx, "🔎 جستجو", "🔎 Search"), "apq", ""), (T(ctx, "🏆 رتبه‌بندی", "🏆 Leaderboard"), "apk", "level")],
        [(T(ctx, "📊 توزیع", "📊 Distribution"), "apd", "race"), (T(ctx, "🛡 امنیت", "🛡 Security"), "apx", "")],
        [(T(ctx, "📜 لاگ صفحه‌بندی", "📜 Paged log"), "apl", "0")],
        nav(ctx),
    ]
    return Out(head(ctx, "ttl_adm") + f"<i>{role} ({lvl})</i>\n\n" + await dashboard(ctx), rows)


# ---- analytics -------------------------------------------------------------------------------------------
@action("apa")
async def analytics(ctx, arg):
    if await admin_level(ctx.uid) < 20:
        return _denied(ctx)
    L, now = ctx.lang, int(time.time())
    users = await col("users").count_documents({})
    act1 = await col("users").count_documents({"last_seen": {"$gte": now - DAY}})
    act7 = await col("users").count_documents({"last_seen": {"$gte": now - 7 * DAY}})
    new1 = await col("users").count_documents({"created_at": {"$gte": now - DAY}})
    new7 = await col("users").count_documents({"created_at": {"$gte": now - 7 * DAY}})
    buckets = await col("characters").aggregate([
        {"$project": {"b": {"$multiply": [{"$floor": {"$divide": ["$level", 10]}}, 10]}}},
        {"$group": {"_id": "$b", "n": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]).to_list(None)
    econ = await col("characters").aggregate([
        {"$group": {"_id": None, "sum": {"$sum": "$coins"}, "avg": {"$avg": "$coins"}}}
    ]).to_list(1)
    e = econ[0] if econ else {"sum": 0, "avg": 0}
    top = max((b["n"] for b in buckets), default=0)
    ret = round(100 * act7 / users) if users else 0

    lines = [
        T(ctx, "👥 <b>کاربران</b>", "👥 <b>Users</b>"),
        T(ctx, f"کل: {fnum(users, L)} · جدید ۲۴س: {fnum(new1, L)} · ۷روز: {fnum(new7, L)}",
          f"Total: {fnum(users, L)} · new 24h: {fnum(new1, L)} · 7d: {fnum(new7, L)}"),
        T(ctx, f"فعال ۲۴س: {fnum(act1, L)} · ۷روز: {fnum(act7, L)} ({ret}٪)",
          f"Active 24h: {fnum(act1, L)} · 7d: {fnum(act7, L)} ({ret}%)"),
        "",
        T(ctx, "🪙 <b>اقتصاد</b>", "🪙 <b>Economy</b>"),
        T(ctx, f"مجموع سکه: {fnum(int(e['sum'] or 0), L)} · میانگین: {fnum(int(e['avg'] or 0), L)}",
          f"Total coins: {fnum(int(e['sum'] or 0), L)} · avg: {fnum(int(e['avg'] or 0), L)}"),
        "",
        T(ctx, "📊 <b>توزیع سطح</b>", "📊 <b>Level spread</b>"),
    ]
    for b in buckets:
        lo = int(b["_id"] or 0)
        lines.append(f"<code>{lo:>3}+ {_bar(b['n'], top)}</code> {fnum(b['n'], L)}")
    rows = [[(T(ctx, "🔄 تازه‌سازی", "🔄 Refresh"), "apa", "")], _back(ctx)]
    return Out(head(ctx, "ttl_adm") + "\n".join(lines), rows)


# ---- risk scan -------------------------------------------------------------------------------------------
@action("apr")
async def risk_scan(ctx, arg):
    if await admin_level(ctx.uid) < 40:
        return _denied(ctx)
    L = ctx.lang
    rich = await col("characters").find({}, {"user_id": 1, "name": 1, "coins": 1}).sort("coins", -1).limit(5).to_list(5)
    warned = await col("users").find({"warns": {"$gte": 2}, "banned": {"$ne": True}},
                                     {"telegram_id": 1, "username": 1, "warns": 1}).sort("warns", -1).limit(5).to_list(5)
    banned = await col("users").count_documents({"banned": True})

    lines = [T(ctx, f"🚫 بن‌شده‌ها: {fnum(banned, L)}", f"🚫 Banned: {fnum(banned, L)}"), "",
             T(ctx, "💰 <b>ثروتمندترین‌ها</b>", "💰 <b>Richest</b>")]
    for i, d in enumerate(rich, 1):
        lines.append(f"{i}. {esc(str(d.get('name', '?'))[:20])} · 🪙 {fnum(d.get('coins', 0), L)}")
    lines += ["", T(ctx, "⚠️ <b>اخطار زیاد (بن‌نشده)</b>", "⚠️ <b>High warns (not banned)</b>")]
    if not warned:
        lines.append(T(ctx, "— موردی نیست ✅", "— none ✅"))
    for d in warned:
        lines.append(f"<code>{d.get('telegram_id')}</code> @{esc(d.get('username') or '-')} · ⚠️ {d.get('warns', 0)}")

    buttons = [(f"💰 {str(d.get('name', '?'))[:12]}", "adb", f"v.{d['user_id']}") for d in rich if "user_id" in d]
    buttons += [(f"⚠️ {d.get('telegram_id')}", "adb", f"v.{d['telegram_id']}") for d in warned if "telegram_id" in d]
    rows = chunk(buttons, 2) if buttons else []
    rows += [[(T(ctx, "🔄 تازه‌سازی", "🔄 Refresh"), "apr", "")], _back(ctx)]
    return Out(head(ctx, "ttl_adm") + "\n".join(lines), rows)


# ---- health ----------------------------------------------------------------------------------------------
@action("aph")
async def health(ctx, arg):
    if await admin_level(ctx.uid) < 60:
        return _denied(ctx)
    L, now = ctx.lang, int(time.time())
    ok = bool(await ping())
    hrs, mins = divmod(int(now - BOOT) // 60, 60)
    chars = await col("characters").count_documents({})
    fights = await col("battle_logs").count_documents({"at": {"$gte": now - DAY}})
    actions = await col("admin_logs").count_documents({"at": {"$gte": now - DAY}})
    lines = [
        f"🗄 MongoDB: {'✅' if ok else '❌'}",
        T(ctx, f"⏱ آپتایم: {fnum(hrs, L)} ساعت و {fnum(mins, L)} دقیقه", f"⏱ Uptime: {hrs}h {mins}m"),
        T(ctx, f"🎮 کاراکترها: {fnum(chars, L)}", f"🎮 Characters: {fnum(chars, L)}"),
        T(ctx, f"⚔️ نبرد ۲۴س: {fnum(fights, L)}", f"⚔️ Battles 24h: {fnum(fights, L)}"),
        T(ctx, f"📜 اقدام ادمین ۲۴س: {fnum(actions, L)}", f"📜 Admin actions 24h: {fnum(actions, L)}"),
    ]
    rows = [[(T(ctx, "🔄 تازه‌سازی", "🔄 Refresh"), "aph", "")], _back(ctx)]
    return Out(head(ctx, "ttl_adm") + "\n".join(lines), rows)


# ---- character search (free text) ------------------------------------------------------------------------
async def _set_input(ctx, kind):
    await col("inputs").update_one({"user_id": ctx.uid}, {"$set": {"kind": kind, "at": int(time.time())}}, upsert=True)


@action("apq")
async def search_start(ctx, arg):
    if await admin_level(ctx.uid) < 20:
        return _denied(ctx)
    await _set_input(ctx, "ap_search")
    return Out(head(ctx, "ttl_adm") + T(ctx, "نام کاراکتر یا آیدی عددی را بفرست.",
                                         "Send a character name or numeric ID."), [_back(ctx)])


@input_handler("ap_search")
async def search_input(ctx, text):
    if await admin_level(ctx.uid) < 20:
        return Out(alert="?")
    q = (text or "").strip()[:40]
    if not q:
        return Out(T(ctx, "خالیه؛ دوباره بفرست.", "Empty; send again."), [_back(ctx)])
    found = []
    if q.lstrip("-").isdigit():
        d = await col("characters").find_one({"user_id": int(q)}, {"user_id": 1, "name": 1, "level": 1})
        found = [d] if d else []
    if not found:
        import re
        found = await col("characters").find({"name": {"$regex": re.escape(q), "$options": "i"}},
                                             {"user_id": 1, "name": 1, "level": 1}).limit(10).to_list(10)
    if not found:
        return Out(head(ctx, "ttl_adm") + T(ctx, "چیزی پیدا نشد.", "Nothing found."), [_back(ctx)])
    buttons = [(f"{str(d.get('name', '?'))[:12]} · {T(ctx, 'سطح', 'Lv')}{d.get('level', 1)}", "adb", f"v.{d['user_id']}")
               for d in found if "user_id" in d]
    rows = chunk(buttons, 2) + [_back(ctx)]
    return Out(head(ctx, "ttl_adm") + T(ctx, f"{len(found)} نتیجه:", f"{len(found)} result(s):"), rows)


# ---- leaderboards ------------------------------------------------------------------------------------------
METRICS = {"level": ("سطح", "Level"), "rating": ("رتبه", "Rating"), "wins": ("برد", "Wins"), "coins": ("سکه", "Coins")}


@action("apk")
async def leaderboard(ctx, arg):
    if await admin_level(ctx.uid) < 20:
        return _denied(ctx)
    metric = arg if arg in METRICS else "level"
    L = ctx.lang
    docs = await col("characters").find({}, {"user_id": 1, "name": 1, "level": 1, "rating": 1, "wins": 1, "coins": 1}) \
        .sort(metric, -1).limit(10).to_list(10)
    label = METRICS[metric][0 if L == "fa" else 1]
    lines = [f"{i}. {esc(str(d.get('name', '?'))[:18])} · {label}: {fnum(d.get(metric, 0) or 0, L)}" for i, d in enumerate(docs, 1)]
    tabs = [(T(ctx, v[0], v[1]), "apk", k) for k, v in METRICS.items()]
    rows = [tabs[:2], tabs[2:]]
    rows.append([(f"👤 {str(d.get('name', '?'))[:10]}", "adb", f"v.{d['user_id']}") for d in docs[:4] if "user_id" in d])
    rows.append(_back(ctx))
    return Out(head(ctx, "ttl_adm") + (T(ctx, "🏆 رتبه‌بندی", "🏆 Leaderboard") + f" · {label}\n\n" + "\n".join(lines) if lines else "—"), rows)


# ---- distributions -----------------------------------------------------------------------------------------
DIMS = {"race": ("نژاد", "Race"), "location": ("مکان", "Location"), "division": ("دیویژن", "Division")}


def _dim_name(dim, key, L):
    try:
        if dim == "race":
            from data_races import RACES
            r = RACES.get(key, {})
            return r.get("name_fa" if L == "fa" else "name_en", key)
        if dim == "location":
            from data_races import LOCATIONS
            loc = LOCATIONS.get(key, {})
            return loc.get("fa" if L == "fa" else "en", key)
        if dim == "division":
            from data_bleach import DIV_BY_ID
            dv = DIV_BY_ID.get(key)
            return (dv["fa"] if L == "fa" else dv["en"]) if dv else str(key)
    except Exception:
        pass
    return str(key)


@action("apd")
async def distribution(ctx, arg):
    if await admin_level(ctx.uid) < 20:
        return _denied(ctx)
    dim = arg if arg in DIMS else "race"
    L = ctx.lang
    agg = await col("characters").aggregate([
        {"$group": {"_id": f"${dim}", "n": {"$sum": 1}}},
        {"$sort": {"n": -1}}, {"$limit": 12},
    ]).to_list(12)
    top = max((a["n"] for a in agg), default=0)
    lines = [f"<code>{_bar(a['n'], top)}</code> {esc(_dim_name(dim, a['_id'], L))[:22]} · {fnum(a['n'], L)}" for a in agg]
    tabs = [(T(ctx, v[0], v[1]), "apd", k) for k, v in DIMS.items()]
    rows = [tabs, _back(ctx)]
    return Out(head(ctx, "ttl_adm") + T(ctx, "📊 توزیع", "📊 Distribution") + f" · {DIMS[dim][0 if L == 'fa' else 1]}\n\n" + ("\n".join(lines) or "—"), rows)


# ---- security ----------------------------------------------------------------------------------------------
@action("apx")
async def security(ctx, arg):
    if await admin_level(ctx.uid) < 40:
        return _denied(ctx)
    L = ctx.lang
    banned = await col("users").find({"banned": True}, {"telegram_id": 1, "username": 1}).limit(8).to_list(8)
    warned = await col("users").find({"warns": {"$gte": 1}, "banned": {"$ne": True}},
                                     {"telegram_id": 1, "username": 1, "warns": 1}).sort("warns", -1).limit(8).to_list(8)
    lines = [T(ctx, "🚫 <b>بن‌شده‌ها</b>", "🚫 <b>Banned</b>")]
    lines += [f"<code>{d.get('telegram_id')}</code> @{esc(d.get('username') or '-')}" for d in banned] or ["—"]
    lines += ["", T(ctx, "⚠️ <b>دارای اخطار</b>", "⚠️ <b>Warned</b>")]
    lines += [f"<code>{d.get('telegram_id')}</code> @{esc(d.get('username') or '-')} · ⚠️ {d.get('warns', 0)}" for d in warned] or ["—"]
    rows = []
    rows += chunk([(f"✅ {d.get('telegram_id')}", "adb", f"ub.{d.get('telegram_id')}") for d in banned if d.get("telegram_id")], 2)
    rows += chunk([(f"🔎 {d.get('telegram_id')}", "adb", f"v.{d.get('telegram_id')}") for d in warned if d.get("telegram_id")], 2)
    rows += [[(T(ctx, "🔄 تازه‌سازی", "🔄 Refresh"), "apx", "")], _back(ctx)]
    return Out(head(ctx, "ttl_adm") + "\n".join(lines), rows)


# ---- admin log, paginated -----------------------------------------------------------------------------------
LOG_PAGE = 10


@action("apl")
async def admin_log(ctx, arg):
    if await admin_level(ctx.uid) < 20:
        return _denied(ctx)
    L = ctx.lang
    page = int(arg) if str(arg).isdigit() else 0
    total = await col("admin_logs").count_documents({})
    pages = max(1, (total + LOG_PAGE - 1) // LOG_PAGE)
    page = min(page, pages - 1)
    docs = await col("admin_logs").find({}).sort("at", -1).skip(page * LOG_PAGE).limit(LOG_PAGE).to_list(LOG_PAGE)
    lines = []
    for d in docs:
        hm = time.strftime("%m-%d %H:%M", time.gmtime(d["at"] + 12600))
        lines.append(f"<code>{hm}</code> {d.get('admin')} · {esc(str(d.get('action')))} → {esc(str(d.get('target')))}")
    rows = []
    pg = pager(ctx, "apl", page, pages)
    if pg:
        rows.append(pg)
    rows.append(_back(ctx))
    return Out(head(ctx, "ttl_adm") + f"{page + 1}/{pages} · {fnum(total, L)}\n\n" + ("\n".join(lines) or "—"), rows)
