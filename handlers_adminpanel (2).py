"""Admin button panel (the text commands in handlers_admin keep working). Every action re-checks the admin level."""
import asyncio
import logging
import re
import time

from aiogram.types import BotCommand, BotCommandScopeChat

from admin_fa import ACTION_FA, EVENT_FA, LANG_FA, ROLE_FA, setting_label
from cmdlist import ADMIN_CMDS_EN, ADMIN_CMDS_FA, CMD_EN, CMD_FA
from config import GAME_DEFAULTS, settings
from database import col, game_settings, set_game_setting, ping as database_ping
from handlers_admin import ROLES, _broadcast, admin_level, admin_world, alog, dashboard
from i18n import esc, fnum
from service_player import add_coins, add_xp, get_char
from ui import Out, action, chunk, head, input_handler, nav

log = logging.getLogger("senka.adminpanel")
KEYS = sorted(GAME_DEFAULTS)
PAGE = 10
AUD_FA = {"fa": "فارسی", "en": "انگلیسی", "all": "همه"}
_bg_tasks: set = set()  # strong refs so fire-and-forget tasks are not garbage-collected mid-run


def _n(v):
    """Safe number for display: lists/dicts -> their length, None/garbage -> 0."""
    if isinstance(v, (list, tuple, set, dict)):
        return len(v)
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else 0


def _aud_filter(aud):
    """One filter for both the preview count and the real send, so the number shown is the number sent."""
    flt = {"banned": {"$ne": True}}
    if aud != "all":
        flt["lang"] = aud
    return flt


def T(ctx, fa, en):
    return fa if ctx.lang == "fa" else en


async def _need(ctx, level):
    return await admin_level(ctx.uid) >= level


def _deny(ctx):
    return Out(alert=T(ctx, "دسترسی نداری.", "No permission."))


async def _set_input(ctx, kind):
    await col("inputs").update_one({"user_id": ctx.uid}, {"$set": {"kind": kind, "at": int(time.time())}}, upsert=True)


# ---- slash menu for admins ---------------------------------------------------------------------------------
async def refresh_admin_commands(bot, uid=None, on=True):
    """Admins also get /admin in their own '/' menu (per-chat scope); with no uid: everyone who is an admin."""
    ids = [uid] if uid else list(dict.fromkeys([settings.owner_id] + [d["user_id"] async for d in col("admin_users").find({}, {"user_id": 1}) if "user_id" in d]))
    mk = lambda rows: [BotCommand(command=c, description=d) for c, d in rows]
    for i in ids:
        try:
            scope = BotCommandScopeChat(chat_id=i)
            if on:
                await bot.set_my_commands(mk(CMD_EN + ADMIN_CMDS_EN), scope=scope)
                await bot.set_my_commands(mk(CMD_FA + ADMIN_CMDS_FA), scope=scope, language_code="fa")
            else:
                await bot.delete_my_commands(scope=scope)
                await bot.delete_my_commands(scope=scope, language_code="fa")
        except Exception as e:
            log.warning("admin commands for %s: %s", i, e)


# ---- main menu ---------------------------------------------------------------------------------------------
async def main_menu(ctx, lvl):
    st = await game_settings()
    on = bool(st.get("maintenance", GAME_DEFAULTS.get("maintenance", False)))
    mt = T(ctx, "🔧 تعمیرات: روشن ✅" if on else "🔧 تعمیرات: خاموش", "🔧 Maintenance: ON ✅" if on else "🔧 Maintenance: off")
    role = next((k for k, v in ROLES.items() if v == lvl), "?")
    role = ROLE_FA.get(role, role) if ctx.lang == "fa" else role
    rows = [
        [(T(ctx, "📡 مرکز عملیات", "📡 Operations"), "adop", ""),
         (T(ctx, "📊 آمار زنده", "📊 Live stats"), "adm", "")],
        [(T(ctx, "👥 بازیکنان", "👥 Players"), "adu", ""),
         (T(ctx, "🌍 جهان بازی", "🌍 Game world"), "adw", "")],
        [(T(ctx, "💰 اقتصاد و بازار", "💰 Economy & market"), "ade", ""),
         (T(ctx, "🛡 امنیت و نظارت", "🛡 Security"), "adsec", "")],
        [(T(ctx, "🏯 انجمن‌ها و قلمروها", "🏯 Guilds & territories"), "adguild", ""),
         (T(ctx, "🏆 رتبه‌بندی بازیکنان", "🏆 Player rankings"), "adtop", "")],
        [(T(ctx, "📣 پیام همگانی", "📣 Broadcast"), "adc", ""),
         (T(ctx, "🎁 جوایز و آرتیفکت", "🎁 Rewards & artifacts"), "adg", "")],
        [(T(ctx, "⚙️ تنظیمات پیشرفته", "⚙️ Advanced settings"), "ads", "0"),
         (mt, "adt", "")],
        [(T(ctx, "📜 گزارش فعالیت", "📜 Activity log"), "adl", ""),
         (T(ctx, "👑 مدیریت ادمین‌ها", "👑 Admin team"), "ada", "")],
        nav(ctx)]
    return Out(head(ctx, "ttl_adm") + f"<i>{role} ({lvl})</i>\n" +
               T(ctx, "مرکز فرماندهی مدیریتی SENKA", "SENKA Control Center") +
               "\n\n" + await dashboard(ctx), rows)


def _back(ctx):
    return nav(ctx, ("adm", ""))




# ---- advanced control center -------------------------------------------------------------------------------
async def _count(name, query=None):
    return await col(name).count_documents(query or {})


def _metric(label, value):
    return f"{label}: <b>{value}</b>"


@action("adop")
async def operations_panel(ctx, arg):
    if not await _need(ctx, 20):
        return _deny(ctx)
    now = int(time.time())
    day = now - 86400
    # Every metric below uses collections and fields already used by SENKA services.
    total = await _count("users")
    active = await _count("users", {"last_seen": {"$gte": day}})
    online = await _count("users", {"last_seen": {"$gte": now - 600}})
    new = await _count("users", {"created_at": {"$gte": day}})
    banned = await _count("users", {"banned": True})
    chars = await _count("characters")
    battles = await _count("battle_logs", {"at": {"$gte": day}})
    boss_kills = await _count("boss_sessions", {"killed": True, "ended_at": {"$gte": day}})
    listings = await _count("market_listings", {"status": "active"})
    art_listings = await _count("art_listings", {"status": "active"})
    events = await _count("world_events", {"status": "active"})
    guilds = await _count("guilds")
    groups = await _count("groups")
    try:
        db_ok = bool(await database_ping())
    except Exception:
        db_ok = False
    body = [
        "📡 <b>" + T(ctx, "مرکز عملیات SENKA", "SENKA Operations Center") + "</b>",
        "━━━━━━━━━━━━━━━━━━",
        ("🟢 " + T(ctx, "پایگاه داده: متصل", "Database: connected")) if db_ok else ("🔴 " + T(ctx, "پایگاه داده: قطع", "Database: offline")),
        _metric(T(ctx, "کل کاربران", "Total users"), fnum(total, ctx.lang)),
        _metric(T(ctx, "شخصیت‌های ساخته‌شده", "Characters created"), fnum(chars, ctx.lang)),
        _metric(T(ctx, "آنلاین در ۱۰ دقیقه", "Online · 10 min"), fnum(online, ctx.lang)),
        _metric(T(ctx, "فعال در ۲۴ ساعت", "Active · 24h"), fnum(active, ctx.lang)),
        _metric(T(ctx, "ثبت‌نام جدید · ۲۴ ساعت", "New registrations · 24h"), fnum(new, ctx.lang)),
        _metric(T(ctx, "کاربران مسدود", "Banned users"), fnum(banned, ctx.lang)),
        "━━━━━━━━━━━━━━━━━━",
        _metric(T(ctx, "نبردهای ثبت‌شده · ۲۴ ساعت", "Battles logged · 24h"), fnum(battles, ctx.lang)),
        _metric(T(ctx, "شکست باس‌ها · ۲۴ ساعت", "Boss kills · 24h"), fnum(boss_kills, ctx.lang)),
        _metric(T(ctx, "آگهی‌های فعال بازار", "Active market listings"), fnum(listings, ctx.lang)),
        _metric(T(ctx, "آگهی‌های آرتیفکت", "Artifact listings"), fnum(art_listings, ctx.lang)),
        _metric(T(ctx, "رویدادهای فعال", "Active world events"), fnum(events, ctx.lang)),
        _metric(T(ctx, "انجمن‌ها / گروه‌ها", "Guilds / groups"), f"{fnum(guilds, ctx.lang)} / {fnum(groups, ctx.lang)}"),
        "━━━━━━━━━━━━━━━━━━",
        T(ctx, "این آمار در هر بار باز کردن صفحه از دیتابیس خوانده می‌شود.", "Metrics are refreshed from the database whenever this page opens.")
    ]
    rows = [[(T(ctx, "👥 بازیکنان", "👥 Players"), "adu", ""), (T(ctx, "💰 اقتصاد", "💰 Economy"), "ade", "")],
            [(T(ctx, "🏆 رتبه‌بندی", "🏆 Rankings"), "adtop", ""), (T(ctx, "🏯 انجمن‌ها", "🏯 Guilds"), "adguild", "")],
            [(T(ctx, "🛡 امنیت", "🛡 Security"), "adsec", ""), (T(ctx, "🌍 جهان", "🌍 World"), "adw", "")], _back(ctx)]
    return Out(head(ctx, "ttl_adm") + "\n".join(body), rows)


@action("ade")
async def economy_panel(ctx, arg):
    if not await _need(ctx, 40):
        return _deny(ctx)
    agg = await col("characters").aggregate([
        {"$group": {"_id": None, "coins": {"$sum": "$coins"}, "tokens": {"$sum": "$tokens"},
                    "avg_level": {"$avg": "$level"}, "max_coins": {"$max": "$coins"}}}
    ]).to_list(1)
    d = agg[0] if agg else {}
    market = await _count("market_listings", {"status": "active"})
    arts = await _count("art_listings", {"status": "active"})
    tx = await _count("transactions", {"at": {"$gte": int(time.time()) - 86400}})
    guild_bank = await col("guilds").aggregate([{"$group": {"_id": None, "total": {"$sum": "$bank"}}}]).to_list(1)
    body = [
        "💰 <b>" + T(ctx, "نمای اقتصاد بازی", "Economy overview") + "</b>",
        "━━━━━━━━━━━━━━",
        _metric(T(ctx, "مجموع سکه در گردش", "Coins in circulation"), fnum(int(d.get("coins") or 0), ctx.lang)),
        _metric(T(ctx, "مجموع توکن‌ها", "Total tokens"), fnum(int(d.get("tokens") or 0), ctx.lang)),
        _metric(T(ctx, "میانگین سطح", "Average level"), f"{float(d.get('avg_level') or 0):.1f}"),
        _metric(T(ctx, "بیشترین موجودی سکه", "Highest coin balance"), fnum(int(d.get("max_coins") or 0), ctx.lang)),
        _metric(T(ctx, "موجودی بانک انجمن‌ها", "Guild bank balance"), fnum(int((guild_bank[0] if guild_bank else {}).get("total") or 0), ctx.lang)),
        "━━━━━━━━━━━━━━",
        _metric(T(ctx, "تراکنش‌های ۲۴ ساعت", "Transactions · 24h"), fnum(tx, ctx.lang)),
        _metric(T(ctx, "آگهی فعال بازار", "Active market listings"), fnum(market, ctx.lang)),
        _metric(T(ctx, "آگهی فعال آرتیفکت", "Active artifact listings"), fnum(arts, ctx.lang)),
        "",
        T(ctx, "ابزارهای تغییر موجودی از کارت هر بازیکن در دسترس‌اند.", "Balance tools are available from each player's profile.")
    ]
    return Out(head(ctx, "ttl_adm") + "\n".join(body),
               [[(T(ctx, "👥 جستجوی بازیکن", "👥 Find player"), "adu", ""),
                 (T(ctx, "🏆 رتبه‌بندی", "🏆 Rankings"), "adtop", "")],
                [(T(ctx, "🏯 انجمن‌ها", "🏯 Guilds"), "adguild", ""),
                 (T(ctx, "🎁 ابزار هدیه", "🎁 Gift tools"), "adg", "")], _back(ctx)])


@action("adsec")
async def security_panel(ctx, arg):
    if not await _need(ctx, 40):
        return _deny(ctx)
    banned = await col("users").find({"banned": True}, {"telegram_id": 1, "username": 1, "warns": 1}).sort("last_seen", -1).limit(12).to_list(12)
    recent = await col("admin_logs").find({}).sort("at", -1).limit(8).to_list(8)
    body = ["🛡 <b>" + T(ctx, "امنیت و نظارت", "Security & moderation") + "</b>",
            "━━━━━━━━━━━━━━",
            _metric(T(ctx, "کاربران مسدود", "Banned users"), fnum(await _count("users", {"banned": True}), ctx.lang)),
            _metric(T(ctx, "کاربران دارای اخطار", "Users with warnings"), fnum(await _count("users", {"warns": {"$gt": 0}}), ctx.lang)),
            "", "<b>" + T(ctx, "آخرین مسدودی‌ها", "Recently banned") + "</b>"]
    if banned:
        body.extend([f"• <code>{d.get('telegram_id')}</code> @{esc(d.get('username') or '—')} · ⚠️ {d.get('warns', 0)}" for d in banned])
    else:
        body.append(T(ctx, "موردی ثبت نشده است.", "No banned users."))
    body += ["", "<b>" + T(ctx, "آخرین اقدامات مدیریتی", "Recent admin actions") + "</b>"]
    for d in recent:
        stamp = time.strftime("%m-%d %H:%M", time.gmtime(d.get("at", 0) + 12600))
        act = ACTION_FA.get(d.get("action"), d.get("action", "?")) if ctx.lang == "fa" else d.get("action", "?")
        body.append(f"• <code>{stamp}</code> {esc(str(act))} · <code>{esc(str(d.get('target', '—')))}</code>")
    rows = [[(T(ctx, "👤 جستجوی کاربر", "👤 Find user"), "adu", ""),
             (T(ctx, "📜 همه گزارش‌ها", "📜 Full audit log"), "adl", "")], _back(ctx)]
    return Out(head(ctx, "ttl_adm") + "\n".join(body), rows)


# ---- guild, territory and competitive intelligence ---------------------------------------------------------
@action("adguild")
async def guilds_panel(ctx, arg):
    if not await _need(ctx, 40):
        return _deny(ctx)
    guilds = await col("guilds").find({}).sort("members", -1).limit(12).to_list(12)
    territories = await col("territories").find({"owner": {"$ne": None}}).limit(12).to_list(12)
    body = ["🏯 <b>" + T(ctx, "انجمن‌ها و قلمروها", "Guilds & territories") + "</b>",
            "━━━━━━━━━━━━━━━━━━",
            _metric(T(ctx, "تعداد انجمن‌ها", "Total guilds"), fnum(await _count("guilds"), ctx.lang)),
            _metric(T(ctx, "قلمروهای تحت مالکیت", "Owned territories"), fnum(await _count("territories", {"owner": {"$ne": None}}), ctx.lang)), "",
            "<b>" + T(ctx, "برترین انجمن‌ها", "Top guilds") + "</b>"]
    for g in guilds:
        name = esc(str(g.get("name_fa" if ctx.lang == "fa" else "name_en") or g.get("name_fa") or g.get("name_en") or g.get("_id") or "—")[:24])
        body.append(f"• <b>{name}</b> · 👥 {fnum(_n(g.get('members')), ctx.lang)} · 🏦 {fnum(_n(g.get('bank')), ctx.lang)}")
    if not guilds:
        body.append(T(ctx, "هنوز انجمنی ثبت نشده.", "No guilds registered yet."))
    body += ["", "<b>" + T(ctx, "وضعیت قلمروها", "Territory overview") + "</b>"]
    for t in territories:
        owner = t.get("owner_fa" if ctx.lang == "fa" else "owner_en") or t.get("owner") or "—"
        body.append(f"• <code>{esc(str(t.get('_id', '?')))}</code> · {T(ctx, 'مالک', 'Owner')}: <b>{esc(str(owner)[:24])}</b>")
    rows = [[(T(ctx, "🏆 رتبه‌بندی", "🏆 Rankings"), "adtop", ""), (T(ctx, "🌍 جهان", "🌍 World"), "adw", "")], _back(ctx)]
    return Out(head(ctx, "ttl_adm") + "\n".join(body), rows)


@action("adtop")
async def rankings_panel(ctx, arg):
    if not await _need(ctx, 40):
        return _deny(ctx)
    kind = arg if arg in ("level", "coins", "rating", "xp") else "rating"
    fields = {"level": ("level", T(ctx, "بالاترین سطح", "Highest level")),
              "coins": ("coins", T(ctx, "ثروتمندترین", "Richest")),
              "rating": ("rating", T(ctx, "بالاترین امتیاز", "Highest rating")),
              "xp": ("xp", T(ctx, "بیشترین تجربه", "Most XP"))}
    field, label = fields[kind]
    docs = await col("characters").find({}, {"user_id": 1, "name": 1, "level": 1, "coins": 1, "rating": 1, "xp": 1}).sort(field, -1).limit(15).to_list(15)
    body = ["🏆 <b>" + T(ctx, "رتبه‌بندی بازیکنان", "Player rankings") + "</b>",
            f"<i>{label}</i>", "━━━━━━━━━━━━━━━━━━"]
    for i, d in enumerate(docs, 1):
        value = _n(d.get(field))
        body.append(f"{i:02d}. {esc(str(d.get('name') or '—')[:18])} · <code>{d.get('user_id', '?')}</code> · <b>{fnum(value, ctx.lang)}</b>")
    if not docs:
        body.append("—")
    rows = [[(T(ctx, "⭐ امتیاز", "⭐ Rating"), "adtop", "rating"), (T(ctx, "🔝 سطح", "🔝 Level"), "adtop", "level")],
            [(T(ctx, "💰 سکه", "💰 Coins"), "adtop", "coins"), (T(ctx, "✨ تجربه", "✨ XP"), "adtop", "xp")], _back(ctx)]
    return Out(head(ctx, "ttl_adm") + "\n".join(body), rows)


# ---- maintenance ---------------------------------------------------------------------------------------------
@action("adt")
async def toggle_maintenance(ctx, arg):
    if not await _need(ctx, 60):
        return _deny(ctx)
    old = bool((await game_settings()).get("maintenance", False))
    await set_game_setting("maintenance", not old)
    await alog(ctx.uid, "maintenance", None, old, not old)
    from handlers_admin import admin_panel
    return await admin_panel(ctx, "")


# ---- world ---------------------------------------------------------------------------------------------------
@action("adw")
async def world_panel(ctx, arg):
    lvl = await admin_level(ctx.uid)
    if lvl < 20:
        return _deny(ctx)
    from data_world import EVENTS
    text = head(ctx, "ttl_adm") + await admin_world(ctx, [], lvl)
    rows = []
    if lvl >= 60:
        rows += [[(T(ctx, "🐉 ظهور باس", "🐉 Spawn boss"), "adx", "bs"), (T(ctx, "⛔ پایان باس", "⛔ End boss"), "adx", "be")]]
        rows += chunk([(f"{e['icon']} {EVENT_FA.get(k, k) if ctx.lang == 'fa' else k}", "adx", "ev:" + k) for k, e in EVENTS.items()], 3)
        rows += [[(T(ctx, "⏹ پایان رویداد", "⏹ End event"), "adx", "ee"), (T(ctx, "🏁 پایان فصل", "🏁 End season"), "adx", "se")],
                 [(T(ctx, "🔄 ریست دنیا", "🔄 Reset world"), "adx", "rs?")]]
    rows.append(_back(ctx))
    return Out(text, rows)


@action("adx")
async def world_do(ctx, arg):
    lvl = await admin_level(ctx.uid)
    if lvl < 60:
        return _deny(ctx)
    if arg.endswith("?"):  # destructive: ask once
        return Out(head(ctx, "ttl_adm") + T(ctx, "مطمئنی؟ این کار برگشت‌ناپذیر است.", "Sure? This cannot be undone."),
                   [[(T(ctx, "✅ بله", "✅ Yes"), "adx", arg[:-1]), (T(ctx, "❌ نه", "❌ No"), "adw", "")]])
    sub = {"bs": ["boss", "spawn"], "be": ["boss", "end"], "ee": ["event", "end"], "se": ["season", "end"], "rs": ["reset"]}.get(arg)
    if arg.startswith("ev:"):
        sub = ["event", arg[3:]]
    if not sub:
        return Out(alert="?")
    msg = str(await admin_world(ctx, sub, lvl) or "")
    out = await world_panel(ctx, "")
    out.alert = msg if 0 < len(msg) < 190 else None
    return out


# ---- live settings -------------------------------------------------------------------------------------------
def _short(v):
    return f"{v:g}" if isinstance(v, float) else str(v)


@action("ads")
async def settings_list(ctx, arg):
    if not await _need(ctx, 80):
        return _deny(ctx)
    pages = (len(KEYS) + PAGE - 1) // PAGE
    p = max(0, min(int(arg or 0), pages - 1)) if str(arg).lstrip("-").isdigit() else 0
    st = await game_settings()
    items = [(f"{setting_label(k, ctx.lang == 'fa')}: {_short(st.get(k, GAME_DEFAULTS[k]))}"[:48], "adk", str(KEYS.index(k))) for k in KEYS[p * PAGE:(p + 1) * PAGE]]
    rows = chunk(items, 2)
    pn = []
    if p > 0:
        pn.append(("◀️", "ads", str(p - 1)))
    pn.append((f"{p + 1}/{pages}", "noop", ""))
    if p < pages - 1:
        pn.append(("▶️", "ads", str(p + 1)))
    rows += [pn, _back(ctx)]
    return Out(head(ctx, "ttl_adm") + T(ctx, "⚙️ تنظیمات زنده؛ روی هر مورد بزن.", "⚙️ Live settings: tap one to edit."), rows)


@action("adk")
async def setting_edit(ctx, arg):
    if not await _need(ctx, 80):
        return _deny(ctx)
    idx, _, op = arg.partition(":")
    if not idx.isdigit() or int(idx) >= len(KEYS):
        return Out(alert="?")
    key = KEYS[int(idx)]
    default = GAME_DEFAULTS[key]
    st = await game_settings()
    old = st.get(key, default)
    new = old
    is_bool = isinstance(default, bool)
    is_int = isinstance(default, int) and not is_bool
    is_num = is_int or isinstance(default, float)
    if op == "t" and is_bool:
        new = not old
    elif op == "r":
        new = default
    elif op in ("d", "u", "d1", "u1") and is_num:
        try:
            cur = float(old)
        except (TypeError, ValueError):
            cur = float(default)
        up = op[0] == "u"
        if op.endswith("1"):
            val = cur + (1 if is_int else 0.1) * (1 if up else -1)
        else:
            val = cur * (1.1 if up else 0.9)
            if is_int:
                val = round(val)
                if val == round(cur):
                    val = round(cur) + (1 if up else -1)
            elif cur == 0:  # 10% of zero is zero; give float settings a way off zero
                val = 0.1 if up else 0.0
        val = max(0, val)
        new = int(round(val)) if is_int else round(float(val), 4)
    if new != old:
        await set_game_setting(key, new)
        await alog(ctx.uid, "set", key, old, new)
    text = head(ctx, "ttl_adm") + f"<b>{setting_label(key, ctx.lang == 'fa')}</b>\n<code>{key}</code>\n{T(ctx, 'الان', 'Now')}: <b>{_short(new)}</b>\n{T(ctx, 'پیش‌فرض', 'Default')}: {_short(default)}"
    ix = str(idx)
    if is_bool:
        rows = [[(T(ctx, "🔁 تغییر", "🔁 Toggle"), "adk", ix + ":t")]]
    elif is_num:
        rows = [[("−10%", "adk", ix + ":d"), ("+10%", "adk", ix + ":u")], [("−1", "adk", ix + ":d1"), ("+1", "adk", ix + ":u1")]]
    else:
        rows = []
    rows += [[(T(ctx, "↩️ پیش‌فرض", "↩️ Default"), "adk", ix + ":r")], nav(ctx, ("ads", str(int(idx) // PAGE)))]
    return Out(text, rows)


# ---- users ---------------------------------------------------------------------------------------------------
@action("adu")
async def users_panel(ctx, arg):
    if not await _need(ctx, 20):
        return _deny(ctx)
    await _set_input(ctx, "ad_user")
    rows = [[(T(ctx, "🆕 جدیدترین‌ها", "🆕 Newest"), "adn", "new"), (T(ctx, "💰 ثروتمندترین‌ها", "💰 Richest"), "adn", "rich")],
            [(T(ctx, "🔝 بالاترین سطح", "🔝 Top level"), "adn", "lvl")], _back(ctx)]
    return Out(head(ctx, "ttl_adm") + T(ctx, "آیدی عددی یا @یوزرنیم کاربر را بفرست (یا از لیست‌ها انتخاب کن).",
                                      "Send the numeric ID or @username (or pick from a list)."), rows)


@action("adn")
async def users_list(ctx, arg):
    if not await _need(ctx, 20):
        return _deny(ctx)
    if arg == "new":
        docs = await col("characters").find({}, {"user_id": 1, "name": 1, "level": 1}).sort("_id", -1).limit(10).to_list(10)
    elif arg == "rich":
        docs = await col("characters").find({}, {"user_id": 1, "name": 1, "level": 1}).sort("coins", -1).limit(10).to_list(10)
    else:
        docs = await col("characters").find({}, {"user_id": 1, "name": 1, "level": 1}).sort("level", -1).limit(10).to_list(10)
    rows = chunk([(f"{str(d.get('name') or '?')[:14]} · {T(ctx, 'سطح ', 'Lv')}{d.get('level', 1)}", "adb", f"v.{d['user_id']}") for d in docs if "user_id" in d], 2)
    rows.append(nav(ctx, ("adu", "")))
    return Out(head(ctx, "ttl_adm") + T(ctx, "یک کاربر انتخاب کن:", "Pick a user:"), rows)


async def _resolve_user(text: str):
    t = text.strip().lstrip("@")
    if not t:
        return None
    if t.lstrip("-").isdigit():
        try:
            return int(t)
        except ValueError:
            return None
    u = await col("users").find_one({"username": {"$regex": f"^{re.escape(t)}$", "$options": "i"}}, {"telegram_id": 1})
    return u["telegram_id"] if u else None


async def _user_card(ctx, tid):
    L = ctx.lang
    u = await col("users").find_one({"telegram_id": tid})
    if not u:
        return Out(T(ctx, "کاربر پیدا نشد.", "User not found."), [nav(ctx, ("adu", ""))])
    ch = await get_char(tid)
    lvl = await admin_level(ctx.uid)
    body = f"<code>{tid}</code> @{esc(u.get('username') or '-')} · {LANG_FA.get(u.get('lang'), u.get('lang', '?')) if L == 'fa' else u.get('lang', '?')}\n"
    body += T(ctx, "🚫 بن‌شده", "🚫 banned") + "\n" if u.get("banned") else ""
    body += f"⚠️ {u.get('warns', 0)}\n"
    if ch:
        from data_races import RACES
        race = ch.get('race', '?')
        rn = esc(str(RACES.get(race, {}).get('name_fa' if L == 'fa' else 'name_en', race)))
        body += f"{esc(str(ch.get('name', '?')))} | {rn} | {T(ctx, 'سطح', 'Lv')} {ch.get('level', 1)} | 🪙 {fnum(_n(ch.get('coins')), L)} | ⭐ {ch.get('rating', 0)}"
        if ch.get("division"):
            from data_bleach import DIV_BY_ID
            dv = DIV_BY_ID.get(ch['division'])
            body += f" | {esc(str((dv['fa'] if L == 'fa' else dv['en']) if dv else ch['division']))}"
        body += f"\n🎟 {fnum(_n(ch.get('tokens')), L)}"
        from data_artifacts import ART_BY_ID
        if ch.get("artifact") in ART_BY_ID:
            body += f" | {ART_BY_ID[ch['artifact']]['icon']} {ART_BY_ID[ch['artifact']]['name_fa' if L == 'fa' else 'name_en']}"
        if ch.get("hogyoku"):
            body += " | 🔮"
    rows = []
    if lvl >= 40:
        rows.append([(T(ctx, "✅ آنبن", "✅ Unban") if u.get("banned") else T(ctx, "🚫 بن", "🚫 Ban"), "adb", f"{'ub' if u.get('banned') else 'bn'}.{tid}"),
                     (T(ctx, "⚠️ اخطار", "⚠️ Warn"), "adb", f"wn.{tid}")])
    if lvl >= 60 and ch:
        rows.append([(T(ctx, "+۱۰ هزار 🪙", "+10k 🪙"), "adb", f"c1.{tid}"), (T(ctx, "+۱۰۰ هزار 🪙", "+100k 🪙"), "adb", f"c2.{tid}"), (T(ctx, "+۱ هزار تجربه", "+1k XP"), "adb", f"x1.{tid}")])
    if lvl >= 60 and ch:
        rows.append([(T(ctx, "🎟 +۱۰ توکن", "🎟 +10 tokens"), "adg", f"t1.{tid}"), (T(ctx, "🎟 +۱۰۰ توکن", "🎟 +100 tokens"), "adg", f"t2.{tid}")])
    if lvl >= 80 and ch:
        rows.append([(T(ctx, "💎 دادن آرتیفکت", "💎 Give artifact"), "adg", f"pa.{tid}"), (T(ctx, "🔮 دادن هوگیوکو", "🔮 Give Hōgyoku"), "adg", f"hq.{tid}")])
    rows.append(nav(ctx, ("adu", "")))
    return Out(head(ctx, "ttl_adm") + body, rows)


@input_handler("ad_user")
async def user_input(ctx, text):
    if not await _need(ctx, 20):
        return Out(alert="?")
    tid = await _resolve_user(text)
    if tid is None:
        return Out(T(ctx, "پیدا نشد؛ دوباره از پنل شروع کن.", "Not found; start again from the panel."), [_back(ctx)])
    return await _user_card(ctx, tid)


@action("adb")
async def user_do(ctx, arg):
    op, _, raw = arg.partition(".")
    if not raw.lstrip("-").isdigit():
        return Out(alert="?")
    tid = int(raw)
    lvl = await admin_level(ctx.uid)
    # viewing a card needs admin level too (stale buttons of a demoted/removed admin must not leak user data)
    if lvl < 20 or (op != "v" and lvl < 40) or (op in ("c1", "c2", "x1") and lvl < 60):
        return _deny(ctx)
    if op not in ("v", "bn", "ub", "wn", "c1", "c2", "x1"):
        return Out(alert="?")
    if not await col("users").find_one({"telegram_id": tid}, {"_id": 1}):
        return Out(alert=T(ctx, "کاربر پیدا نشد.", "User not found."))
    if op in ("c1", "c2", "x1") and not await get_char(tid):
        return Out(alert=T(ctx, "این کاربر هنوز شخصیتی ندارد.", "This user has no character yet."))
    if op in ("bn", "wn") and (tid == settings.owner_id or await admin_level(tid) >= lvl):
        return Out(alert=T(ctx, "روی این کاربر اختیار نداری.", "You cannot act on this user."))
    if op == "bn":
        await col("users").update_one({"telegram_id": tid}, {"$set": {"banned": True}})
        await alog(ctx.uid, "ban", tid, None, {"banned": True}, "panel")
    elif op == "ub":
        await col("users").update_one({"telegram_id": tid}, {"$set": {"banned": False}})
        await alog(ctx.uid, "unban", tid, None, {"banned": False}, "panel")
    elif op == "wn":
        await col("users").update_one({"telegram_id": tid}, {"$inc": {"warns": 1}})
        await alog(ctx.uid, "warn", tid, None, None, "panel")
    elif op in ("c1", "c2"):
        amt = 10_000 if op == "c1" else 100_000
        await add_coins(tid, amt, "admin")
        await alog(ctx.uid, "give_coins", tid, None, {"delta": amt}, "panel")
    elif op == "x1":
        await add_xp(tid, 1000, "admin", apply_rate=False)
        await alog(ctx.uid, "give_xp", tid, None, {"delta": 1000}, "panel")
    try:  # the ban cache in handlers_core lives 15 s; make it instant for the panel
        from handlers_core import _ban_cache
        _ban_cache.pop(tid, None)
    except Exception:
        pass
    out = await _user_card(ctx, tid)
    out.alert = T(ctx, "انجام شد ✅", "Done ✅") if op != "v" else None
    return out


# ---- broadcast -----------------------------------------------------------------------------------------------
@action("adc")
async def broadcast_panel(ctx, arg):
    if not await _need(ctx, 60):
        return _deny(ctx)
    if arg in ("fa", "en", "all"):
        await _set_input(ctx, "ad_bc_" + arg)
        return Out(head(ctx, "ttl_adm") + T(ctx, f"متن پیام ({AUD_FA[arg]}) را بفرست. «لغو» برای انصراف.", f"Send the message text ({arg}). Type cancel to abort."), [_back(ctx)])
    rows = [[("🌐 " + T(ctx, "همه", "Everyone"), "adc", "all")], [("🇮🇷 فارسی", "adc", "fa"), (T(ctx, "🇬🇧 انگلیسی", "🇬🇧 English"), "adc", "en")], _back(ctx)]
    return Out(head(ctx, "ttl_adm") + T(ctx, "پیام همگانی برای چه کسانی؟", "Broadcast to whom?"), rows)


def _bc_handler(aud):
    async def handler(ctx, text):
        if not await _need(ctx, 60):
            return Out(alert="?")
        if text.strip().lower() in ("لغو", "cancel"):  # the prompt promises this works
            await col("admin_drafts").delete_one({"admin": ctx.uid})
            return Out(head(ctx, "ttl_adm") + T(ctx, "لغو شد.", "Cancelled."), [_back(ctx)])
        if not text.strip():
            return Out(alert=T(ctx, "متن خالی است.", "Empty message."))
        await col("admin_drafts").update_one({"admin": ctx.uid}, {"$set": {"aud": aud, "text": text[:3500], "at": int(time.time())}}, upsert=True)
        n = await col("users").count_documents(_aud_filter(aud))
        rows = [[(T(ctx, f"✅ ارسال به {fnum(n, ctx.lang)} نفر", f"✅ Send to {n}"), "adz", "go"), (T(ctx, "❌ لغو", "❌ Cancel"), "adz", "no")]]
        return Out(head(ctx, "ttl_adm") + T(ctx, "پیش‌نمایش:", "Preview:") + "\n\n" + esc(text[:3500]), rows)
    return handler


for _aud in ("fa", "en", "all"):
    input_handler("ad_bc_" + _aud)(_bc_handler(_aud))


@action("adz")
async def broadcast_go(ctx, arg):
    if not await _need(ctx, 60):
        return _deny(ctx)
    d = await col("admin_drafts").find_one_and_delete({"admin": ctx.uid})
    if arg != "go" or not d or time.time() - d.get("at", 0) > 900 or d.get("aud") not in AUD_FA:
        return Out(head(ctx, "ttl_adm") + T(ctx, "لغو شد.", "Cancelled."), [_back(ctx)])
    task = asyncio.create_task(_broadcast(ctx.bot, _aud_filter(d["aud"]), d["text"], ctx.uid))
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)
    await alog(ctx.uid, "broadcast", d["aud"], None, d["text"][:100], "panel")
    return Out(head(ctx, "ttl_adm") + T(ctx, "ارسال شروع شد؛ نتیجه را در پیام خصوصی می‌فرستم.", "Sending started; I will DM you the result."), [_back(ctx)])


# ---- admin log / admins ----------------------------------------------------------------------------------------
@action("adl")
async def log_panel(ctx, arg):
    if not await _need(ctx, 20):
        return _deny(ctx)
    docs = await col("admin_logs").find({}).sort("at", -1).limit(12).to_list(12)
    lines = []
    for d in docs:
        hm = time.strftime("%m-%d %H:%M", time.gmtime(d.get("at", 0) + 12600))
        act = str(d.get("action", "?"))
        lines.append(f"<code>{hm}</code> {d.get('admin', '?')} · {esc(ACTION_FA.get(act, act) if ctx.lang == 'fa' else act)} → {esc(str(d.get('target')))}")
    return Out(head(ctx, "ttl_adm") + ("\n".join(lines) or "—"), [_back(ctx)])


@action("ada")
async def admins_panel(ctx, arg):
    lvl = await admin_level(ctx.uid)
    if lvl < 20:
        return _deny(ctx)
    if arg.startswith("rm."):
        if lvl < 100:
            return _deny(ctx)
        raw = arg[3:]
        if not raw.lstrip("-").isdigit():
            return Out(alert="?")
        tid = int(raw)
        await col("admin_users").delete_one({"user_id": tid})
        await alog(ctx.uid, "rmadmin", tid, None, None, "panel")
        await refresh_admin_commands(ctx.bot, tid, False)
    docs = [d for d in await col("admin_users").find({}).to_list(50) if "user_id" in d]
    lines = [f"👑 <code>{settings.owner_id}</code> {T(ctx, 'مالک', 'owner')}"] + [f"• <code>{d['user_id']}</code> {esc(str(ROLE_FA.get(d.get('role'), d.get('role')) if ctx.lang == 'fa' else d.get('role')))}" for d in docs]
    rows = chunk([(f"❌ {d['user_id']}", "ada", f"rm.{d['user_id']}") for d in docs], 3) if lvl >= 100 else []
    rows.append(_back(ctx))
    hint = T(ctx, "\n\nافزودن: <code>افزودن ادمین آیدی نقش</code> (ادمین، ناظر، پشتیبان، سوپر)", "\n\nAdd: <code>addadmin id role</code> (admin, moderator, support, super)")
    return Out(head(ctx, "ttl_adm") + "\n".join(lines) + (hint if lvl >= 100 else ""), rows)
