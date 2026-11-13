"""Admin slash commands, batch 2 (v2): stats, search, leaderboards, history, notes, warnings,
inactive/new players, ban list, DMs, maintenance switch, CSV exports and health checks.

Uses the same @acmd decorator, permission levels and admin log as handlers_admincmd, so nothing
here bypasses the existing checks. /acmds lists these automatically (it reads ADMIN_COMMANDS)."""
import csv
import io
import re
import time

from aiogram.types import BufferedInputFile

from database import col, game_settings, ping, set_game_setting
from handlers_admin import alog
from handlers_admincmd import Env, _name, acmd, target
from handlers_adminpro import BOOT
from i18n import bar, esc, fnum

DAY = 86400
MEDAL = ["🥇", "🥈", "🥉"]
TOP_FIELDS = {"level": "level", "rating": "rating", "wins": "wins", "coins": "coins", "pvp": "pvp_w"}
CSV_KINDS = {
    "top": ({}, [("level", -1)]),
    "rich": ({}, [("coins", -1)]),
    "warn": ({}, [("warns", -1)]),
    "new": ({}, [("created_at", -1)]),
}


def _hm(ts: int) -> str:
    return time.strftime("%m-%d %H:%M", time.gmtime(ts + 12600))


def _ago(ts: int, L: str) -> str:
    m = max(0, int(time.time() - ts) // 60)
    if m < 60:
        return f"{fnum(m, L)}{'د' if L == 'fa' else 'm'}"
    h = m // 60
    return f"{fnum(h, L)}{'س' if L == 'fa' else 'h'}"


# ---- stats ---------------------------------------------------------------------------------------------------
@acmd("adash", 20, "/adash", "خلاصه‌ی سریع بات + نمودار ۷ روز", "Quick summary + 7-day chart")
async def c_adash(e: Env):
    now, L = int(time.time()), e.lang
    users = await col("users").count_documents({})
    online = await col("users").count_documents({"last_seen": {"$gte": now - 600}})
    new = await col("users").count_documents({"created_at": {"$gte": now - DAY}})
    act = await col("users").count_documents({"last_seen": {"$gte": now - DAY}})
    fights = await col("battle_logs").count_documents({"at": {"$gte": now - DAY}})
    kills = await col("boss_sessions").count_documents({"killed": True, "ended_at": {"$gte": now - DAY}})
    banned = await col("users").count_documents({"banned": True})
    fa = await col("users").count_documents({"lang": "fa"})

    # new users per day, last 7 days (oldest first)
    days = []
    for i in range(6, -1, -1):
        lo = now - (i + 1) * DAY
        hi = now - i * DAY
        n = await col("users").count_documents({"created_at": {"$gte": lo, "$lt": hi}})
        days.append(n)
    top = max(days) or 1
    spark = "".join("▁▂▃▄▅▆▇█"[min(7, round(7 * d / top))] for d in days)
    ret = round(100 * act / users) if users else 0

    await e.say("\n".join([
        e.t("📊 <b>خلاصه‌ی امروز</b>", "📊 <b>Today at a glance</b>"),
        f"👥 {fnum(users, L)} · 🟢 {fnum(online, L)} · 🆕 {fnum(new, L)} · 🔁 {ret}%",
        f"⚡ {fnum(act, L)} · ⚔️ {fnum(fights, L)} · 💀 {fnum(kills, L)}",
        f"🇮🇷 {fnum(fa, L)} · 🇬🇧 {fnum(users - fa, L)} · 🚫 {fnum(banned, L)}",
        "",
        e.t("📈 <b>ثبت‌نام ۷ روز اخیر</b>", "📈 <b>Signups, last 7 days</b>"),
        f"<code>{spark}</code> {fnum(sum(days), L)}",
    ]))


@acmd("gamestats", 20, "/gamestats", "آمار بازی ۲۴ ساعت گذشته", "Game stats for the last 24h")
async def c_gamestats(e: Env):
    now, L = int(time.time()), e.lang
    battles = await col("battle_logs").count_documents({"at": {"$gte": now - DAY}})
    pvp = await col("battle_logs").count_documents({"at": {"$gte": now - DAY}, "pvp": True})
    bosses = await col("boss_sessions").count_documents({"ended_at": {"$gte": now - DAY}})
    listings = await col("market_listings").count_documents({"status": "active"})
    await e.say("\n".join([
        e.t("🎮 <b>آمار بازی (۲۴ ساعت)</b>", "🎮 <b>Game stats (24h)</b>"),
        e.t(f"⚔️ نبردها: {fnum(battles, L)} (PvP: {fnum(pvp, L)})", f"⚔️ Battles: {fnum(battles, L)} (PvP: {fnum(pvp, L)})"),
        e.t(f"👹 باس‌ها: {fnum(bosses, L)}", f"👹 Bosses: {fnum(bosses, L)}"),
        e.t(f"🛒 آگهی‌های فعال بازار: {fnum(listings, L)}", f"🛒 Active market listings: {fnum(listings, L)}"),
    ]))


@acmd("online", 20, "/online [n]", "بازیکنان آنلاین با زمان آخرین فعالیت", "Online players with last-seen time")
async def c_online(e: Env):
    now, L = int(time.time()), e.lang
    n_show = min(30, int(e.args[0])) if e.args and e.args[0].isdigit() else 15
    q = {"last_seen": {"$gte": now - 600}}
    total = await col("users").count_documents(q)
    docs = await col("users").find(q, {"telegram_id": 1, "username": 1, "lang": 1, "last_seen": 1}) \
        .sort("last_seen", -1).limit(n_show).to_list(n_show)
    lines = [f"<code>{d['telegram_id']}</code> @{esc(d.get('username') or '-')} · {(d.get('lang') or '?').upper()} · {_ago(d.get('last_seen', now), L)}"
             for d in docs if d.get("telegram_id")]
    await e.say(e.t(f"🟢 آنلاین (۱۰ دقیقه): {fnum(total, L)}", f"🟢 Online (10 min): {fnum(total, L)}") + "\n" + ("\n".join(lines) or "—"))


@acmd("newusers", 20, "/newusers [n]", "آخرین ثبت‌نام‌ها", "Latest signups")
async def c_newusers(e: Env):
    L, now = e.lang, int(time.time())
    n = min(30, int(e.args[0])) if e.args and e.args[0].isdigit() else 10
    docs = await col("users").find({}, {"telegram_id": 1, "username": 1, "created_at": 1, "lang": 1}) \
        .sort("created_at", -1).limit(n).to_list(n)
    lines = [f"<code>{d['telegram_id']}</code> @{esc(d.get('username') or '-')} · {(d.get('lang') or '?').upper()} · {_ago(d.get('created_at', now), L)}"
             for d in docs if d.get("telegram_id")]
    await e.say(e.t("🆕 <b>ثبت‌نام‌های اخیر</b>", "🆕 <b>Latest signups</b>") + "\n" + ("\n".join(lines) or "—"))


@acmd("inactive", 20, "/inactive [روز]", "بازیکنان غیرفعال (پیش‌فرض ۷ روز)", "Inactive players (default 7 days)")
async def c_inactive(e: Env):
    L, now = e.lang, int(time.time())
    days = min(90, int(e.args[0])) if e.args and e.args[0].isdigit() else 7
    q = {"last_seen": {"$lt": now - days * DAY}}
    total = await col("users").count_documents(q)
    docs = await col("users").find(q, {"telegram_id": 1, "username": 1, "last_seen": 1}).sort("last_seen", 1).limit(10).to_list(10)
    lines = [f"<code>{d['telegram_id']}</code> @{esc(d.get('username') or '-')} · {_ago(d.get('last_seen', now), L)}" for d in docs if d.get("telegram_id")]
    await e.say(e.t(f"💤 بیش از {days} روز غیرفعال: {fnum(total, L)}", f"💤 Inactive over {days} days: {fnum(total, L)}") + "\n" + ("\n".join(lines) or "—"))


# ---- leaderboards and search --------------------------------------------------------------------------------
@acmd("top", 20, "/top <level|rating|wins|coins|pvp> [n]", "رتبه‌بندی بازیکنان (تا ۳۰ نفر)", "Player leaderboard (up to 30)")
async def c_top(e: Env):
    key = e.args[0].lower() if e.args else "level"
    if key not in TOP_FIELDS:
        return await e.usage()
    n = min(30, int(e.args[1])) if len(e.args) > 1 and e.args[1].isdigit() else 10
    field = TOP_FIELDS[key]
    docs = await col("characters").find({}, {"user_id": 1, "name": 1, "level": 1, field: 1}).sort(field, -1).limit(n).to_list(n)
    vals = [d.get(field, 0) or 0 for d in docs]
    top = max(vals, default=0)
    lines = []
    for i, d in enumerate(docs, 1):
        mark = MEDAL[i - 1] if i <= 3 else f"{i}."
        v = d.get(field, 0) or 0
        lines.append(f"{mark} <b>{esc(str(d.get('name', '?'))[:18])}</b> <code>{d.get('user_id')}</code> · Lv{d.get('level', 1)}\n"
                     f"    <code>{bar(v, top)}</code> {fnum(v, e.lang)}")
    await e.say(f"🏆 <b>{key}</b>\n" + ("\n".join(lines) or "—"))


@acmd("findname", 20, "/findname <متن>", "جستجوی کاراکتر با نام یا آیدی", "Find characters by name or ID")
async def c_findname(e: Env):
    q = " ".join(e.args).strip()[:40]
    if not q:
        return await e.usage()
    if q.isdigit():
        docs = await col("characters").find({"user_id": int(q)}, {"user_id": 1, "name": 1, "level": 1}).limit(1).to_list(1)
    else:
        docs = await col("characters").find({"name": {"$regex": re.escape(q), "$options": "i"}},
                                            {"user_id": 1, "name": 1, "level": 1}).limit(15).to_list(15)
    banned = {d["telegram_id"] for d in await col("users").find(
        {"telegram_id": {"$in": [d["user_id"] for d in docs]}, "banned": True}, {"telegram_id": 1}).to_list(15)}
    lines = [f"<code>{d['user_id']}</code> {esc(str(d.get('name', '?')))} · Lv {d.get('level', 1)}{' 🚫' if d['user_id'] in banned else ''}"
             for d in docs if "user_id" in d]
    await e.say("\n".join(lines) or e.t("چیزی پیدا نشد.", "Nothing found."))


# ---- player file --------------------------------------------------------------------------------------------
@acmd("history", 20, "/history <id|@user|reply> [نوع اقدام]", "تاریخچه‌ی اقدامات ادمین روی بازیکن", "Admin history for a player (optional action filter)")
async def c_history(e: Env):
    tid = await target(e, need_char=False)
    if tid is None:
        return
    q = {"target": tid}
    if e.args:
        q["action"] = {"$regex": re.escape(e.args[0]), "$options": "i"}
    docs = await col("admin_logs").find(q).sort("at", -1).limit(15).to_list(15)
    if not docs:
        return await e.say(e.t("چیزی ثبت نشده.", "Nothing logged."))
    lines = []
    for d in docs:
        delta = ""
        if isinstance(d.get("after"), dict) and "delta" in d["after"]:
            delta = f" {d['after']['delta']:+,}"
        lines.append(f"<code>{_hm(d['at'])}</code> {d.get('admin')} · {esc(str(d.get('action')))}{delta}")
    await e.say("\n".join(lines))


@acmd("note", 40, "/note <id|@user|reply> <متن>", "یادداشت داخلی برای بازیکن", "Internal note on a player")
async def c_note(e: Env):
    tid = await target(e, need_char=False)
    if tid is None:
        return
    text = " ".join(e.args)[:300]
    if not text:
        return await e.usage()
    await col("admin_notes").insert_one({"user_id": tid, "admin": e.uid, "text": text, "at": int(time.time())})
    await alog(e.uid, "note", tid, None, None, text[:80])
    await e.say(e.t("📝 یادداشت ثبت شد.", "📝 Note saved."))


@acmd("notes", 20, "/notes <id|@user|reply>", "یادداشت‌های بازیکن", "Player notes")
async def c_notes(e: Env):
    tid = await target(e, need_char=False)
    if tid is None:
        return
    docs = await col("admin_notes").find({"user_id": tid}).sort("at", -1).limit(10).to_list(10)
    await e.say(e.t(f"📝 {fnum(len(docs), e.lang)} یادداشت", f"📝 {len(docs)} note(s)") + "\n" + ("\n".join(
        f"<code>{time.strftime('%m-%d', time.gmtime(d['at']))}</code> {d.get('admin')}: {esc(d.get('text', ''))}" for d in docs) or "—"))


# ---- warnings and bans ------------------------------------------------------------------------------------------
@acmd("warnlist", 40, "/warnlist", "بازیکنان دارای اخطار", "Players with warnings")
async def c_warnlist(e: Env):
    docs = await col("users").find({"warns": {"$gte": 1}}, {"telegram_id": 1, "username": 1, "warns": 1, "banned": 1}) \
        .sort("warns", -1).limit(20).to_list(20)
    lines = [f"<code>{d['telegram_id']}</code> @{esc(d.get('username') or '-')} · ⚠️ {d.get('warns', 0)}{' 🚫' if d.get('banned') else ''}"
             for d in docs if d.get("telegram_id")]
    await e.say("\n".join(lines) or e.t("هیچ اخطاری نیست ✅", "No warnings ✅"))


@acmd("banlist", 40, "/banlist", "لیست بن‌شده‌ها با دلیل", "Banned players with reasons")
async def c_banlist(e: Env):
    docs = await col("users").find({"banned": True}, {"telegram_id": 1, "username": 1, "ban_reason": 1}).limit(30).to_list(30)
    total = await col("users").count_documents({"banned": True})
    lines = [f"<code>{d['telegram_id']}</code> @{esc(d.get('username') or '-')} · {esc(str(d.get('ban_reason') or '—'))[:60]}"
             for d in docs if d.get("telegram_id")]
    await e.say(e.t(f"🚫 بن‌شده‌ها: {fnum(total, e.lang)}", f"🚫 Banned: {fnum(total, e.lang)}") + "\n" + ("\n".join(lines) or "—"))


@acmd("unwarn", 40, "/unwarn <id|@user|reply>", "کم کردن یک اخطار", "Remove one warning")
async def c_unwarn(e: Env):
    tid = await target(e, need_char=False)
    if tid is None:
        return
    u = await col("users").find_one({"telegram_id": tid}, {"warns": 1}) or {}
    cur = int(u.get("warns", 0) or 0)
    if cur <= 0:
        return await e.say(e.t("این کاربر اخطار ندارد.", "No warnings on this player."))
    await col("users").update_one({"telegram_id": tid, "warns": {"$gt": 0}}, {"$inc": {"warns": -1}})
    await alog(e.uid, "unwarn", tid, {"warns": cur}, {"warns": cur - 1}, "cmd")
    await e.say("✅ " + await _name(tid))


@acmd("clearwarns", 60, "/clearwarns <id|@user|reply>", "پاک کردن همه‌ی اخطارها", "Clear all warnings")
async def c_clearwarns(e: Env):
    tid = await target(e, need_char=False)
    if tid is None:
        return
    u = await col("users").find_one({"telegram_id": tid}, {"warns": 1}) or {}
    await col("users").update_one({"telegram_id": tid}, {"$set": {"warns": 0}})
    await alog(e.uid, "clearwarns", tid, {"warns": u.get("warns", 0)}, {"warns": 0}, "cmd")
    await e.say("✅ " + await _name(tid))


# ---- messaging -----------------------------------------------------------------------------------------------
@acmd("dm", 40, "/dm <id|@user|reply> <متن>", "پیام خصوصی به بازیکن", "Private message to a player")
async def c_dm(e: Env):
    tid = await target(e, need_char=False)
    if tid is None:
        return
    text = " ".join(e.args)[:800]
    if not text:
        return await e.usage()
    try:
        await e.bot.send_message(tid, "📨 " + esc(text))
        ok = True
    except Exception:
        ok = False
    await alog(e.uid, "dm", tid, None, None, text[:80])
    await e.say(e.t("✅ ارسال شد.", "✅ Sent.") if ok else e.t("❌ ارسال نشد (شاید ربات را بلاک کرده).", "❌ Not delivered (maybe blocked)."))


# ---- system and exports ----------------------------------------------------------------------------------------
@acmd("maint", 60, "/maint on|off|status", "تعمیرات: روشن / خاموش / وضعیت", "Maintenance on / off / status")
async def c_maint(e: Env):
    sub = e.args[0].lower() if e.args else "status"
    if sub not in ("on", "off", "status"):
        return await e.usage()
    old = bool((await game_settings()).get("maintenance"))
    if sub != "status":
        new = sub == "on"
        if new != old:
            await set_game_setting("maintenance", new)
            await alog(e.uid, "maintenance", None, old, new, "cmd")
        old = new
    await e.say(e.t("🔧 تعمیرات: ", "🔧 Maintenance: ") + (e.t("روشن ✅", "ON ✅") if old else e.t("خاموش", "off")))


@acmd("health", 60, "/health", "سلامت دیتابیس، آپتایم و حجم داده", "DB health, uptime and data size")
async def c_health(e: Env):
    t0 = time.perf_counter()
    ok = bool(await ping())
    ms = int((time.perf_counter() - t0) * 1000)
    hrs, mins = divmod(int(time.time() - BOOT) // 60, 60)
    chars = await col("characters").count_documents({})
    users = await col("users").count_documents({})
    await e.say("\n".join([
        f"🗄 MongoDB: {'✅' if ok else '❌'} ({ms} ms)",
        e.t(f"⏱ آپتایم: {hrs} ساعت و {mins} دقیقه", f"⏱ Uptime: {hrs}h {mins}m"),
        e.t(f"👥 کاربران: {fnum(users, e.lang)} · 🎮 کاراکترها: {fnum(chars, e.lang)}", f"👥 Users: {fnum(users, e.lang)} · 🎮 Characters: {fnum(chars, e.lang)}"),
    ]))


@acmd("csv", 60, "/csv [top|rich|warn|new]", "خروجی CSV بازیکنان (۵۰۰ نفر)", "CSV export of players (500 rows)")
async def c_csv(e: Env):
    kind = e.args[0].lower() if e.args else "top"
    if kind not in CSV_KINDS:
        return await e.usage()
    flt, sort = CSV_KINDS[kind]
    if kind == "warn":
        docs = await col("users").find({"warns": {"$gte": 1}}, {"telegram_id": 1, "username": 1, "warns": 1, "banned": 1}) \
            .sort("warns", -1).limit(500).to_list(500)
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["telegram_id", "username", "warns", "banned"])
        for d in docs:
            w.writerow([d.get("telegram_id"), d.get("username", ""), d.get("warns", 0), bool(d.get("banned"))])
    else:
        fields = {"user_id": 1, "name": 1, "level": 1, "rating": 1, "wins": 1, "losses": 1, "coins": 1, "race": 1, "location": 1, "created_at": 1}
        docs = await col("characters").find(flt, fields).sort(sort).limit(500).to_list(500)
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(list(fields))
        for d in docs:
            w.writerow([d.get(k, "") for k in fields])
    file = BufferedInputFile(buf.getvalue().encode("utf-8-sig"), filename=f"senka_{kind}_{int(time.time())}.csv")
    await e.message.reply_document(file, caption=e.t(f"📄 {fnum(len(docs), e.lang)} ردیف · {kind}", f"📄 {len(docs)} rows · {kind}"))
