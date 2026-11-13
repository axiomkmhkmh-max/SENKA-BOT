"""Admin button panel (the text commands in handlers_admin keep working). Every action re-checks the admin level."""
import asyncio
import time

from aiogram.types import BotCommand, BotCommandScopeChat

from admin_fa import ACTION_FA, EVENT_FA, LANG_FA, ROLE_FA, setting_label
from cmdlist import ADMIN_CMDS_EN, ADMIN_CMDS_FA, CMD_EN, CMD_FA
from config import GAME_DEFAULTS, settings
from database import col, game_settings, set_game_setting
from handlers_admin import ROLES, _broadcast, admin_level, admin_world, alog, dashboard
from i18n import esc, fnum
from service_player import add_coins, add_xp, get_char
from ui import Out, action, chunk, head, input_handler, nav

import logging
log = logging.getLogger("senka.adminpanel")
KEYS = sorted(GAME_DEFAULTS)
PAGE = 10
AUD_FA = {"fa": "فارسی", "en": "انگلیسی", "all": "همه"}


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
    ids = [uid] if uid else [settings.owner_id] + [d["user_id"] async for d in col("admin_users").find({}, {"user_id": 1})]
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
    mt = T(ctx, "🔧 تعمیرات: روشن ✅" if st["maintenance"] else "🔧 تعمیرات: خاموش", "🔧 Maintenance: ON ✅" if st["maintenance"] else "🔧 Maintenance: off")
    role = next((k for k, v in ROLES.items() if v == lvl), "?")
    role = ROLE_FA.get(role, role) if ctx.lang == "fa" else role
    rows = [[(T(ctx, "📊 آمار زنده", "📊 Live stats"), "adm", ""), (T(ctx, "🌍 دنیا", "🌍 World"), "adw", "")],
            [(T(ctx, "👤 کاربر", "👤 Users"), "adu", ""), (T(ctx, "📣 پیام همگانی", "📣 Broadcast"), "adc", "")],
            [(T(ctx, "⚙️ تنظیمات بازی", "⚙️ Game settings"), "ads", "0"), (mt, "adt", "")],
            [(T(ctx, "📜 لاگ مدیریت", "📜 Admin log"), "adl", ""), (T(ctx, "👑 ادمین‌ها", "👑 Admins"), "ada", "")],
            [(T(ctx, "🎁 هدیه، آرتیفکت و کدها", "🎁 Gifts, artifacts & codes"), "adg", "")],
            nav(ctx)]
    return Out(head(ctx, "ttl_adm") + f"<i>{role} ({lvl})</i>\n\n" + await dashboard(ctx), rows)


def _back(ctx):
    return nav(ctx, ("adm", ""))


# ---- maintenance ---------------------------------------------------------------------------------------------
@action("adt")
async def toggle_maintenance(ctx, arg):
    if not await _need(ctx, 60):
        return _deny(ctx)
    old = bool((await game_settings())["maintenance"])
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
    msg = await admin_world(ctx, sub, lvl)
    out = await world_panel(ctx, "")
    out.alert = msg if len(msg) < 190 else None
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
    items = [(f"{setting_label(k, ctx.lang == 'fa')}: {_short(st[k])}"[:48], "adk", str(KEYS.index(k))) for k in KEYS[p * PAGE:(p + 1) * PAGE]]
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
    old = st[key]
    new = old
    if op == "t" and isinstance(default, bool):
        new = not old
    elif op == "r":
        new = default
    elif op in ("d", "u", "d1", "u1") and not isinstance(default, bool):
        up = op[0] == "u"
        if op.endswith("1"):
            step = 1 if isinstance(old, int) else 0.1
            new = old + step if up else old - step
        else:
            f = 1.1 if up else 0.9
            new = old * f
            if isinstance(old, int):
                new = int(round(new))
                if new == old:
                    new = old + (1 if up else -1)
        new = max(0, new)
        new = type(default)(new) if isinstance(default, int) else round(float(new), 4)
    if new != old:
        await set_game_setting(key, new)
        await alog(ctx.uid, "set", key, old, new)
    text = head(ctx, "ttl_adm") + f"<b>{setting_label(key, ctx.lang == 'fa')}</b>\n<code>{key}</code>\n{T(ctx, 'الان', 'Now')}: <b>{_short(new)}</b>\n{T(ctx, 'پیش‌فرض', 'Default')}: {_short(default)}"
    ix = str(idx)
    if isinstance(default, bool):
        rows = [[(T(ctx, "🔁 تغییر", "🔁 Toggle"), "adk", ix + ":t")]]
    else:
        rows = [[("−10%", "adk", ix + ":d"), ("+10%", "adk", ix + ":u")], [("−1", "adk", ix + ":d1"), ("+1", "adk", ix + ":u1")]]
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
    rows = chunk([(f"{d.get('name', '?')[:14]} · {T(ctx, 'سطح ', 'Lv')}{d.get('level', 1)}", "adb", f"v.{d['user_id']}") for d in docs], 2)
    rows.append(nav(ctx, ("adu", "")))
    return Out(head(ctx, "ttl_adm") + T(ctx, "یک کاربر انتخاب کن:", "Pick a user:"), rows)


async def _resolve_user(text: str):
    t = text.strip().lstrip("@")
    if t.lstrip("-").isdigit():
        return int(t)
    u = await col("users").find_one({"username": {"$regex": f"^{__import__('re').escape(t)}$", "$options": "i"}}, {"telegram_id": 1})
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
        rn = RACES.get(ch['race'], {}).get('name_fa' if L == 'fa' else 'name_en', ch['race'])
        body += f"{esc(ch['name'])} | {rn} | {T(ctx, 'سطح', 'Lv')} {ch['level']} | 🪙 {fnum(ch['coins'], L)} | ⭐ {ch['rating']}"
        if ch.get("division"):
            from data_bleach import DIV_BY_ID
            dv = DIV_BY_ID.get(ch['division'])
            body += f" | {(dv['fa'] if L == 'fa' else dv['en']) if dv else ch['division']}"
        body += f"\n🎟 {fnum(ch.get('tokens', 0), L)}"
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
    if op != "v" and (lvl < 40 or (op in ("c1", "c2", "x1") and lvl < 60)):
        return _deny(ctx)
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
        await col("admin_drafts").update_one({"admin": ctx.uid}, {"$set": {"aud": aud, "text": text[:3500], "at": int(time.time())}}, upsert=True)
        n = await col("users").count_documents({} if aud == "all" else {"lang": aud, "banned": {"$ne": True}})
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
    if arg != "go" or not d or time.time() - d["at"] > 900:
        return Out(head(ctx, "ttl_adm") + T(ctx, "لغو شد.", "Cancelled."), [_back(ctx)])
    flt = {} if d["aud"] == "all" else {"lang": d["aud"]}
    asyncio.create_task(_broadcast(ctx.bot, flt, d["text"], ctx.uid))
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
        hm = time.strftime("%m-%d %H:%M", time.gmtime(d["at"] + 12600))
        lines.append(f"<code>{hm}</code> {d['admin']} · {esc(ACTION_FA.get(d['action'], str(d['action'])) if ctx.lang == 'fa' else str(d['action']))} → {esc(str(d.get('target')))}")
    return Out(head(ctx, "ttl_adm") + ("\n".join(lines) or "—"), [_back(ctx)])


@action("ada")
async def admins_panel(ctx, arg):
    lvl = await admin_level(ctx.uid)
    if lvl < 20:
        return _deny(ctx)
    if arg.startswith("rm."):
        if lvl < 100:
            return _deny(ctx)
        tid = int(arg[3:])
        await col("admin_users").delete_one({"user_id": tid})
        await alog(ctx.uid, "rmadmin", tid, None, None, "panel")
        await refresh_admin_commands(ctx.bot, tid, False)
    docs = await col("admin_users").find({}).to_list(50)
    lines = [f"👑 <code>{settings.owner_id}</code> {T(ctx, 'مالک', 'owner')}"] + [f"• <code>{d['user_id']}</code> {ROLE_FA.get(d.get('role'), d.get('role')) if ctx.lang == 'fa' else d.get('role')}" for d in docs]
    rows = chunk([(f"❌ {d['user_id']}", "ada", f"rm.{d['user_id']}") for d in docs], 3) if lvl >= 100 else []
    rows.append(_back(ctx))
    hint = T(ctx, "\n\nافزودن: <code>افزودن ادمین آیدی نقش</code> (ادمین، ناظر، پشتیبان، سوپر)", "\n\nAdd: <code>addadmin id role</code> (admin, moderator, support, super)")
    return Out(head(ctx, "ttl_adm") + "\n".join(lines) + (hint if lvl >= 100 else ""), rows)
