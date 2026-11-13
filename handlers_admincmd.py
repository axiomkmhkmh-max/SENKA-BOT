"""Admin slash commands (/give_art, /give_item, /give_token, /code_new ...), the player commands /redeem and /tokens,
and the 🎁 "Gifts & codes" page of the admin button panel.
Every command re-checks the admin level, writes to the admin log and (for gifts) tells the receiver by DM.
Non-admins get no answer at all, so the commands stay invisible to them."""
import asyncio
import logging
import random
import re
import time

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from admin_fa import ROLE_ALIAS
from config import settings
from data_artifacts import ARTIFACTS, ART_BY_ID
from data_items import ALL, iname
from database import col, game_settings
from handlers_admin import ROLES, admin_level, alog
from i18n import esc, fnum
from security import allow
from service_admin_tools import (MAX_COINS, MAX_QTY, _DIG, add_tokens, artifact_free, artifact_give, artifact_take, auto_code,
                                 code_state, create_code, delete_code, find_artifacts, find_items, get_code, gift_all,
                                 hogyoku_give, hogyoku_info, list_codes, parse_amount, redeem, rewards_text, set_code_active,
                                 set_tokens, validate_rewards)
from service_player import add_coins, add_xp, get_char, touch_user, user_lang
from ui import Out, action, chunk, head, nav

log = logging.getLogger("senka.admincmd")
router = Router()

# (name, min level, usage, Persian description, English description) - drives /acmds
ADMIN_COMMANDS: list = []

STATE_FA = {"free": "آزاد", "full": "نسخه‌ها پر", "dropped": "در دراپ"}
CODE_FA = {"active": "✅ فعال", "off": "⛔ خاموش", "expired": "⌛ منقضی", "full": "🈵 پر شده"}
CODE_EN = {"active": "✅ active", "off": "⛔ off", "expired": "⌛ expired", "full": "🈵 used up"}
KEY_ALIAS = {"سکه": "coins", "coin": "coins", "coins": "coins", "تجربه": "xp", "xp": "xp", "توکن": "token", "token": "token", "tokens": "token",
             "آیتم": "item", "item": "item", "items": "item", "آرتیفکت": "art", "art": "art", "artifact": "art",
             "تعداد": "uses", "uses": "uses", "ساعت": "hours", "hours": "hours", "روز": "days", "days": "days", "یادداشت": "note", "note": "note"}


def tr(lang: str, fa: str, en: str) -> str:
    return fa if lang == "fa" else en


class Env:
    """What a command handler works with."""

    def __init__(self, message: Message, lang: str, lvl: int, raw: str):
        self.message, self.lang, self.lvl, self.raw = message, lang, lvl, raw.strip()
        self.args = self.raw.split()
        self.uid = message.from_user.id
        self.bot = message.bot
        rp = message.reply_to_message
        self.reply_user = rp.from_user if rp and rp.from_user and not rp.from_user.is_bot else None

    def t(self, fa, en):
        return tr(self.lang, fa, en)

    async def say(self, text: str):
        """Reply; long texts are split on line breaks so no HTML tag is ever cut in half (Telegram limit is 4096)."""
        chunks, cur = [], ""
        for line in text.split("\n"):
            if cur and len(cur) + len(line) + 1 > 3500:
                chunks.append(cur)
                cur = ""
            cur = f"{cur}\n{line}" if cur else line
        chunks.append(cur)
        for c in chunks:
            await self.message.reply(c)

    async def usage(self):
        await self.say(self.t("📌 طرز استفاده:\n", "📌 Usage:\n") + "<code>" + esc(self.cmd_usage) + "</code>")

    cmd_usage = ""


def acmd(name: str, level: int, usage: str, fa: str, en: str):
    """Register an admin slash command. The handler gets an Env; exceptions are logged and answered with a short error."""
    def deco(fn):
        ADMIN_COMMANDS.append((name, level, usage, fa, en))

        @router.message(Command(name))
        async def _handler(message: Message, command: CommandObject):
            if message.from_user is None or message.from_user.is_bot:
                return
            lvl = await admin_level(message.from_user.id)
            if lvl < 20:
                return  # invisible to non-admins
            lang = await user_lang(message.from_user.id) or "fa"
            e = Env(message, lang, lvl, command.args or "")
            e.cmd_usage = usage
            if lvl < level:
                return await e.say(e.t("⛔ دسترسی کافی نداری.", "⛔ Not allowed."))
            try:
                await fn(e)
            except Exception:
                log.exception("admin command /%s failed", name)
                await e.say(e.t("❌ خطا؛ لاگ سرور را ببین.", "❌ Error; check the server log."))
        return fn
    return deco


# ---- helpers ------------------------------------------------------------------------------------------------------
async def _resolve(text: str):
    t = text.strip().lstrip("@").translate(_DIG)
    if t.lstrip("-").isdigit():
        return int(t)
    u = await col("users").find_one({"username": {"$regex": "^" + re.escape(t) + "$", "$options": "i"}}, {"telegram_id": 1})
    return u["telegram_id"] if u else None


async def target(e: Env, need_char: bool = True):
    """Who the command is about: first argument (id or @username) or the replied-to user. Consumes the argument."""
    a = e.args
    tid = None
    first = a[0].translate(_DIG) if a else ""
    if a and (first.startswith("@") or (first.lstrip("-").isdigit() and (len(first) >= 7 or not e.reply_user))):
        tid = await _resolve(first)
        e.args = a[1:]
    elif e.reply_user:
        tid = e.reply_user.id
    else:
        await e.usage()
        return None
    if tid is None or not await col("users").find_one({"telegram_id": tid}, {"_id": 1}):
        await e.say(e.t("❌ کاربر پیدا نشد (باید قبلاً ربات را استارت کرده باشد).", "❌ User not found (they must have started the bot)."))
        return None
    if need_char and not await get_char(tid):
        await e.say(e.t("❌ این کاربر هنوز کاراکتر نساخته.", "❌ This user has no character yet."))
        return None
    return tid


async def _name(tid: int) -> str:
    ch = await get_char(tid)
    return f"{esc(ch['name'])} (<code>{tid}</code>)" if ch else f"<code>{tid}</code>"


async def _dm(bot, tid: int, fa: str, en: str):
    try:
        lang = await user_lang(tid) or "fa"
        await bot.send_message(tid, tr(lang, fa, en))
    except Exception:
        pass


def _split_qty(args: list):
    """['Reishi', 'Shard', '5'] -> ('Reishi Shard', 5); no trailing number -> qty 1."""
    if len(args) >= 2 and parse_amount(args[-1]):
        return " ".join(args[:-1]), parse_amount(args[-1])
    return " ".join(args), 1


async def _pick_item(e: Env, query: str):
    if not query:
        await e.usage()
        return None
    hits = find_items(query, 8)
    if not hits:
        await e.say(e.t("❌ آیتمی با این نام پیدا نشد. با /finditem جست‌وجو کن.", "❌ No such item. Search with /finditem."))
        return None
    if len(hits) > 1 and query.lower() not in ALL:
        lines = [f"• {esc(iname(i, e.lang))} — <code>{i}</code>" for i in hits]
        await e.say(e.t("چند آیتم پیدا شد؛ شناسه‌ی دقیق را بنویس:\n", "Several matches; use the exact id:\n") + "\n".join(lines))
        return None
    return hits[0]


async def _pick_art(e: Env, query: str):
    if not query:
        await e.usage()
        return None
    hits = find_artifacts(query)
    if not hits:
        await e.say(e.t("❌ آرتیفکتی با این نام پیدا نشد. لیست: /arts", "❌ No such artifact. List: /arts"))
        return None
    if len(hits) > 1:
        lines = [f"• {ART_BY_ID[i]['icon']} {esc(ART_BY_ID[i]['name_fa' if e.lang == 'fa' else 'name_en'])} — <code>{i}</code>" for i in hits]
        await e.say(e.t("چند آرتیفکت پیدا شد؛ شناسه‌ی دقیق را بنویس:\n", "Several matches; use the exact id:\n") + "\n".join(lines))
        return None
    return hits[0]


def _aname(aid: str, lang: str) -> str:
    a = ART_BY_ID[aid]
    return f"{a['icon']} {a['name_fa' if lang == 'fa' else 'name_en']}"


def _fmt_ts(ts: int) -> str:
    return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(ts) + 12600)) if ts else "—"


def _clear_ban_cache(tid: int):
    try:
        from handlers_core import _ban_cache
        _ban_cache.pop(tid, None)
    except Exception:
        pass


# ---- /acmds ---------------------------------------------------------------------------------------------------------
@acmd("acmds", 20, "/acmds", "فهرست دستورات ادمین", "List admin commands")
async def c_acmds(e: Env):
    rows = [f"<code>{esc(u)}</code>\n   ↳ {esc(fa if e.lang == 'fa' else en)}" for _n, lv, u, fa, en in ADMIN_COMMANDS if lv <= e.lvl]
    await e.say(e.t("🛠 <b>دستورات ادمین</b> (به‌جای آیدی می‌توانی روی پیام بازیکن ریپلای کنی یا @یوزرنیم بنویسی)\n\n",
                    "🛠 <b>Admin commands</b> (instead of an id you can reply to a player's message or use @username)\n\n") + "\n".join(rows))


# ---- users ------------------------------------------------------------------------------------------------------------
@acmd("uinfo", 20, "/uinfo <id|@user|reply>", "اطلاعات کامل بازیکن", "Full player card")
async def c_uinfo(e: Env):
    tid = await target(e, need_char=False)
    if tid is None:
        return
    u = await col("users").find_one({"telegram_id": tid}) or {}
    ch = await get_char(tid)
    lines = [f"<code>{tid}</code> @{esc(u.get('username') or '-')} · {u.get('lang', '?')}"]
    if u.get("banned"):
        lines.append(e.t("🚫 بن‌شده", "🚫 banned"))
    lines.append(f"⚠️ {u.get('warns', 0)}")
    if ch:
        from data_races import RACES
        rn = RACES.get(ch["race"], {}).get("name_fa" if e.lang == "fa" else "name_en", ch["race"])
        lines.append(f"<b>{esc(ch['name'])}</b> | {rn} | {e.t('سطح', 'Lv')} {ch['level']} | ⭐ {ch['rating']}")
        lines.append(f"🪙 {fnum(ch['coins'], e.lang)} | 🎟 {fnum(ch.get('tokens', 0), e.lang)} | ⚡ {ch.get('energy', 0)}")
        if ch.get("weapon_id"):
            lines.append(f"⚔️ {esc(iname(ch['weapon_id'], e.lang))}")
        if ch.get("artifact") in ART_BY_ID:
            lines.append(_aname(ch["artifact"], e.lang))
        if ch.get("hogyoku"):
            lines.append("🔮 " + e.t("دارنده‌ی هوگیوکو", "Hōgyoku holder"))
        inv = await col("inventories").find_one({"user_id": tid}, {"items": 1})
        lines.append(f"🎒 {len((inv or {}).get('items', {}))} " + e.t("نوع آیتم", "item types"))
    else:
        lines.append(e.t("کاراکتر ندارد.", "No character."))
    await e.say("\n".join(lines))


@acmd("ban", 40, "/ban <id|@user|reply> [reason]", "بن کردن بازیکن", "Ban a player")
async def c_ban(e: Env):
    tid = await target(e, need_char=False)
    if tid is None:
        return
    if tid == settings.owner_id or await admin_level(tid) >= e.lvl:
        return await e.say(e.t("⛔ روی این کاربر اختیار نداری.", "⛔ You cannot act on this user."))
    reason = " ".join(e.args)[:100]
    await col("users").update_one({"telegram_id": tid}, {"$set": {"banned": True, "ban_reason": reason}})
    _clear_ban_cache(tid)
    await alog(e.uid, "ban", tid, None, {"banned": True}, reason or "cmd")
    await e.say(e.t("🚫 بن شد: ", "🚫 Banned: ") + await _name(tid))


@acmd("unban", 40, "/unban <id|@user|reply>", "آنبن کردن بازیکن", "Unban a player")
async def c_unban(e: Env):
    tid = await target(e, need_char=False)
    if tid is None:
        return
    await col("users").update_one({"telegram_id": tid}, {"$set": {"banned": False}})
    _clear_ban_cache(tid)
    await alog(e.uid, "unban", tid, None, {"banned": False}, "cmd")
    await e.say(e.t("✅ آنبن شد: ", "✅ Unbanned: ") + await _name(tid))


@acmd("warn", 40, "/warn <id|@user|reply> [reason]", "اخطار دادن", "Warn a player")
async def c_warn(e: Env):
    tid = await target(e, need_char=False)
    if tid is None:
        return
    if tid == settings.owner_id or await admin_level(tid) >= e.lvl:
        return await e.say(e.t("⛔ روی این کاربر اختیار نداری.", "⛔ You cannot act on this user."))
    reason = " ".join(e.args)[:100]
    await col("users").update_one({"telegram_id": tid}, {"$inc": {"warns": 1}})
    await alog(e.uid, "warn", tid, None, None, reason or "cmd")
    await _dm(e.bot, tid, f"⚠️ یک اخطار از طرف ادمین دریافت کردی.{(' دلیل: ' + reason) if reason else ''}", f"⚠️ You received a warning from an admin.{(' Reason: ' + reason) if reason else ''}")
    await e.say(e.t("⚠️ اخطار ثبت شد: ", "⚠️ Warned: ") + await _name(tid))


# ---- coins / xp / tokens ----------------------------------------------------------------------------------------------
async def _amount_cmd(e: Env, kind: str, sign: int):
    tid = await target(e)
    if tid is None:
        return
    n = parse_amount(e.args[0]) if e.args else None
    if not n or n > MAX_COINS:
        return await e.usage()
    ch = await get_char(tid)
    if kind == "coins":
        ok = await add_coins(tid, sign * n, "admin")
    elif kind == "xp":
        ok = bool((await add_xp(tid, n, "admin", apply_rate=False))[0])
    else:
        ok = await add_tokens(tid, sign * n, "admin")
    if not ok:
        return await e.say(e.t("❌ موجودی بازیکن کافی نیست.", "❌ The player does not have enough."))
    await alog(e.uid, f"{'give' if sign > 0 else 'take'}_{kind}", tid, {"coins": ch["coins"], "tokens": ch.get("tokens", 0)}, {"delta": sign * n}, "cmd")
    sym = {"coins": "🪙", "xp": "✨", "tokens": "🎟"}[kind]
    if sign > 0:
        await _dm(e.bot, tid, f"🎁 ادمین {sym} {n:,} به تو داد!", f"🎁 An admin gave you {sym} {n:,}!")
    await e.say(f"{'✅' if sign > 0 else '➖'} {sym} {n:,} → " + await _name(tid))


@acmd("give_coins", 60, "/give_coins <id|@user|reply> <amount>", "دادن سکه", "Give coins")
async def c_give_coins(e: Env):
    await _amount_cmd(e, "coins", 1)


@acmd("take_coins", 60, "/take_coins <id|@user|reply> <amount>", "گرفتن سکه", "Take coins")
async def c_take_coins(e: Env):
    await _amount_cmd(e, "coins", -1)


@acmd("give_xp", 60, "/give_xp <id|@user|reply> <amount>", "دادن تجربه", "Give XP")
async def c_give_xp(e: Env):
    await _amount_cmd(e, "xp", 1)


@acmd("give_token", 60, "/give_token <id|@user|reply> <amount>", "دادن توکن", "Give tokens")
async def c_give_token(e: Env):
    await _amount_cmd(e, "tokens", 1)


@acmd("take_token", 60, "/take_token <id|@user|reply> <amount>", "گرفتن توکن", "Take tokens")
async def c_take_token(e: Env):
    await _amount_cmd(e, "tokens", -1)


@acmd("set_token", 80, "/set_token <id|@user|reply> <amount>", "تنظیم دقیق توکن", "Set token balance")
async def c_set_token(e: Env):
    tid = await target(e)
    if tid is None:
        return
    raw = (e.args[0] if e.args else "").translate(_DIG)
    if not raw.isdigit() or int(raw) > MAX_COINS:
        return await e.usage()
    ch = await get_char(tid)
    await set_tokens(tid, int(raw))
    await alog(e.uid, "set_token", tid, ch.get("tokens", 0), int(raw), "cmd")
    await e.say(f"🎟 {int(raw):,} → " + await _name(tid))


@acmd("refill", 60, "/refill <id|@user|reply>", "پر کردن انرژی", "Refill energy")
async def c_refill(e: Env):
    tid = await target(e)
    if tid is None:
        return
    gs = await game_settings()
    await col("characters").update_one({"user_id": tid}, {"$set": {"energy": int(gs["energy_max"]), "energy_ts": int(time.time())}})
    await alog(e.uid, "refill", tid, None, None, "cmd")
    await _dm(e.bot, tid, "⚡ انرژی‌ات توسط ادمین پر شد.", "⚡ An admin refilled your energy.")
    await e.say(e.t("⚡ انرژی پر شد: ", "⚡ Energy refilled: ") + await _name(tid))


# ---- items ------------------------------------------------------------------------------------------------------------
@acmd("finditem", 20, "/finditem <name or id>", "جست‌وجوی آیتم (نام فارسی/انگلیسی)", "Search items by name or id")
async def c_finditem(e: Env):
    if not e.raw:
        return await e.usage()
    hits = find_items(e.raw, 15)
    if not hits:
        return await e.say(e.t("❌ چیزی پیدا نشد.", "❌ Nothing found."))
    lines = []
    for i in hits:
        x = ALL[i]
        lines.append(f"• {esc(iname(i, e.lang))} — <code>{i}</code> · {x.get('category', '')} {x.get('rarity', '')}".rstrip())
    await e.say("\n".join(lines))


@acmd("give_item", 60, "/give_item <id|@user|reply> <item name or id> [qty]", "دادن آیتم (با نام یا شناسه)", "Give an item")
async def c_give_item(e: Env):
    tid = await target(e)
    if tid is None:
        return
    q, n = _split_qty(e.args)
    iid = await _pick_item(e, q)
    if not iid:
        return
    if n > MAX_QTY:
        return await e.say(e.t(f"❌ حداکثر {MAX_QTY} عدد.", f"❌ Max {MAX_QTY}."))
    from service_economy import inv_add
    await inv_add(tid, iid, n, force=True)
    await alog(e.uid, "give_item", tid, None, {"item": iid, "n": n}, "cmd")
    await _dm(e.bot, tid, f"🎁 ادمین «{iname(iid, 'fa')}» ×{n} به تو داد!", f"🎁 An admin gave you {iname(iid, 'en')} ×{n}!")
    await e.say(f"✅ {esc(iname(iid, e.lang))} ×{n} → " + await _name(tid))


@acmd("take_item", 60, "/take_item <id|@user|reply> <item name or id> [qty]", "گرفتن آیتم", "Take an item")
async def c_take_item(e: Env):
    tid = await target(e)
    if tid is None:
        return
    q, n = _split_qty(e.args)
    iid = await _pick_item(e, q)
    if not iid:
        return
    from service_economy import inv_remove
    if not await inv_remove(tid, iid, n):
        return await e.say(e.t("❌ این تعداد در کوله‌ی بازیکن نیست.", "❌ The player does not have that many."))
    await alog(e.uid, "take_item", tid, None, {"item": iid, "n": n}, "cmd")
    await e.say(f"➖ {esc(iname(iid, e.lang))} ×{n} ← " + await _name(tid))


# ---- artifacts & Hogyoku ----------------------------------------------------------------------------------------------
@acmd("arts", 20, "/arts", "فهرست آرتیفکت‌ها و صاحبانشان", "List artifacts and owners")
async def c_arts(e: Env):
    from service_drops import art_registry
    lines = []
    for a, st, holders in await art_registry():
        who = (" → " + ", ".join(f"{esc(h['name'])} (<code>{h['user_id']}</code>)" for h in holders)) if holders else ""
        lines.append(f"{a['icon']} {esc(a['name_fa' if e.lang == 'fa' else 'name_en'])} · {STATE_FA.get(st, st) if e.lang == 'fa' else st}{who}\n   <code>{a['_id']}</code>")
    await e.say("\n".join(lines))


@acmd("give_art", 80, "/give_art <id|@user|reply> <artifact name or id>", "دادن آرتیفکت (مثلاً کیوکا سویگتسو)", "Give a Soul Artifact")
async def c_give_art(e: Env):
    tid = await target(e)
    if tid is None:
        return
    aid = await _pick_art(e, " ".join(e.args))
    if not aid:
        return
    st, prev = await artifact_give(aid, tid, replace=True)
    if st == "already":
        return await e.say(e.t("ℹ️ همین الان مال خودش است.", "ℹ️ They already hold it."))
    if st == "busy":
        return await e.say(e.t("⏳ آرتیفکت همین لحظه در حال جابه‌جایی است؛ چند ثانیه بعد دوباره بزن.", "⏳ That artifact is mid-transfer; try again in a few seconds."))
    if st != "ok":
        return await e.say("❌ " + st)
    await alog(e.uid, "give_art", tid, {"from": prev}, {"art": aid}, "cmd")
    if prev and prev != tid:
        await _dm(e.bot, prev, f"⚠️ آرتیفکت «{ART_BY_ID[aid]['name_fa']}» توسط ادمین از تو گرفته شد.", f"⚠️ An admin took {ART_BY_ID[aid]['name_en']} from you.")
    await _dm(e.bot, tid, f"🎁 ادمین آرتیفکت {_aname(aid, 'fa')} را به تو داد!", f"🎁 An admin gave you {_aname(aid, 'en')}!")
    extra = e.t(f"\n(از صاحب قبلی گرفته شد: <code>{prev}</code>)", f"\n(taken from the previous owner: <code>{prev}</code>)") if prev and prev != tid else ""
    await e.say(f"✅ {esc(_aname(aid, e.lang))} → " + await _name(tid) + extra)


@acmd("take_art", 80, "/take_art <id|@user|reply>", "گرفتن آرتیفکت (به جهان برمی‌گردد)", "Take a player's artifact (returns to the world)")
async def c_take_art(e: Env):
    tid = await target(e)
    if tid is None:
        return
    ch = await get_char(tid)
    aid = ch.get("artifact")
    st = await artifact_take(tid)
    if st == "none":
        return await e.say(e.t("ℹ️ این بازیکن آرتیفکتی ندارد.", "ℹ️ This player holds no artifact."))
    if st != "ok":
        return await e.say(e.t("⏳ همین لحظه در حال جابه‌جایی است؛ دوباره امتحان کن.", "⏳ Mid-transfer; try again."))
    await alog(e.uid, "take_art", tid, {"art": aid}, None, "cmd")
    await _dm(e.bot, tid, "⚠️ آرتیفکتت توسط ادمین گرفته شد.", "⚠️ An admin took your artifact.")
    await e.say(f"➖ {esc(_aname(aid, e.lang)) if aid in ART_BY_ID else aid} ← " + await _name(tid))


@acmd("free_art", 80, "/free_art <artifact name or id>", "آزاد کردن آرتیفکت به جهان", "Send an artifact back to the world")
async def c_free_art(e: Env):
    aid = await _pick_art(e, e.raw)
    if not aid:
        return
    st, prev = await artifact_free(aid)
    if st != "ok":
        return await e.say(e.t("⏳ همین لحظه در حال جابه‌جایی است؛ دوباره امتحان کن.", "⏳ Mid-transfer; try again."))
    await alog(e.uid, "free_art", aid, {"from": prev}, None, "cmd")
    for h in prev or []:
        await _dm(e.bot, h["user_id"], f"⚠️ آرتیفکت «{ART_BY_ID[aid]['name_fa']}» توسط ادمین به جهان بازگردانده شد.", f"⚠️ An admin returned {ART_BY_ID[aid]['name_en']} to the world.")
    await e.say(f"🌍 {esc(_aname(aid, e.lang))} " + e.t("آزاد شد.", "is free again."))


@acmd("hogyoku", 20, "/hogyoku", "دارنده‌ی فعلی هوگیوکو", "Who holds the Hōgyoku")
async def c_hogyoku(e: Env):
    h = await hogyoku_info()
    if not h:
        return await e.say(e.t("🔮 هوگیوکو هنوز صاحبی ندارد.", "🔮 The Hōgyoku has no holder yet."))
    await e.say(f"🔮 {esc(h[1])} (<code>{h[0]}</code>) · {e.t('سطح', 'Lv')} {h[2]} · {e.t('از', 'since')} {_fmt_ts(h[3])}")


@acmd("give_hogyoku", 80, "/give_hogyoku <id|@user|reply>", "دادن هوگیوکو", "Give the Hōgyoku")
async def c_give_hogyoku(e: Env):
    tid = await target(e)
    if tid is None:
        return
    st, old = await hogyoku_give(tid)
    if st == "already":
        return await e.say(e.t("ℹ️ همین الان دست خودش است.", "ℹ️ They already hold it."))
    await alog(e.uid, "give_hogyoku", tid, {"from": old}, None, "cmd")
    if old and old != tid:
        await _dm(e.bot, old, "⚠️ هوگیوکو توسط ادمین از تو گرفته شد.", "⚠️ An admin took the Hōgyoku from you.")
    await _dm(e.bot, tid, "🔮 ادمین هوگیوکو را به تو داد!", "🔮 An admin gave you the Hōgyoku!")
    await e.say("🔮 → " + await _name(tid))


# ---- redeem codes ------------------------------------------------------------------------------------------------------
CODE_USAGE = ("/code_new <CODE|auto> coins=5000 xp=1000 token=5 item=<id>:<n>,<id>:<n> art=<artifact> uses=1 hours=72 note=text\n"
              "(سکه=، تجربه=، توکن=، آیتم=، آرتیفکت=، تعداد=، ساعت= هم کار می‌کند. uses=0 یعنی نامحدود)")


@acmd("code_new", 60, CODE_USAGE, "ساخت ردیم کد (سکه، تجربه، توکن، آیتم، آرتیفکت)", "Create a redeem code")
async def c_code_new(e: Env):
    raw = e.raw
    note = ""
    m = re.search(r"(?:note|یادداشت)=(.*)$", raw, re.S)
    if m:
        note, raw = m.group(1).strip(), raw[:m.start()]
    toks = raw.split()
    if not toks:
        return await e.usage()
    code = auto_code() if toks[0].lower() == "auto" else toks[0]
    rewards, max_uses, hours = {}, 1, 0
    for tk in toks[1:]:
        k, sep, v = tk.partition("=")
        k = KEY_ALIAS.get(k.lower()) or KEY_ALIAS.get(k)
        if not sep or not k:
            return await e.say(e.t(f"❌ آرگومان نامعتبر: <code>{esc(tk)}</code>", f"❌ Bad argument: <code>{esc(tk)}</code>"))
        if k in ("coins", "xp", "token"):
            n = parse_amount(v)
            if not n:
                return await e.say(e.t(f"❌ عدد نامعتبر: {esc(v)}", f"❌ Bad number: {esc(v)}"))
            rewards["tokens" if k == "token" else k] = n
        elif k == "uses":
            v2 = v.translate(_DIG)
            if not v2.isdigit():
                return await e.say(e.t("❌ uses باید عدد باشد.", "❌ uses must be a number."))
            max_uses = int(v2)
        elif k in ("hours", "days"):
            n = parse_amount(v)
            if not n:
                return await e.say(e.t("❌ زمان نامعتبر.", "❌ Bad duration."))
            hours = n * (24 if k == "days" else 1)
        elif k == "item":
            items = {}
            for part in v.split(","):
                iq, _, qn = part.partition(":")
                hits = find_items(iq, 3)
                if not hits or (len(hits) > 1 and iq.lower() not in ALL):
                    return await e.say(e.t(f"❌ آیتم مبهم یا ناموجود: <code>{esc(iq)}</code> (از /finditem استفاده کن)", f"❌ Unknown or ambiguous item: <code>{esc(iq)}</code> (use /finditem)"))
                items[hits[0]] = parse_amount(qn) or 1
            rewards.setdefault("items", {}).update(items)
        elif k == "art":
            hits = find_artifacts(v)
            if len(hits) != 1:
                return await e.say(e.t(f"❌ آرتیفکت مبهم یا ناموجود: <code>{esc(v)}</code> (/arts)", f"❌ Unknown or ambiguous artifact: <code>{esc(v)}</code> (/arts)"))
            rewards["art"] = hits[0]
    err = validate_rewards(rewards)
    if err:
        return await e.say(e.t("❌ جایزه‌ای تعریف نشده یا مقدارها نامعتبرند. ", "❌ No reward given or values out of range. ") + esc(err) + "\n\n<code>" + esc(CODE_USAGE) + "</code>")
    if rewards.get("art") and max_uses != 1:
        max_uses = 1  # an artifact exists once; a code that hands it out can be used once
    exp = int(time.time()) + hours * 3600 if hours else 0
    st = await create_code(e.uid, code, rewards, max_uses, exp, note)
    if st == "bad":
        return await e.say(e.t("❌ کد باید ۳ تا ۲۴ حرف/عدد انگلیسی (با - و _) باشد.", "❌ A code is 3-24 letters/digits (plus - and _)."))
    if st == "exists":
        return await e.say(e.t("❌ این کد قبلاً ساخته شده.", "❌ That code already exists."))
    from service_admin_tools import norm_code
    code = norm_code(code)
    await alog(e.uid, "code_new", code, None, rewards, note)
    await e.say(e.t("🎟 <b>کد ساخته شد</b>\n", "🎟 <b>Code created</b>\n") + f"<code>{esc(code)}</code>\n\n" + esc_rewards(rewards, e.lang)
                + "\n\n" + e.t(f"👥 ظرفیت: {max_uses or 'نامحدود'} · ⏳ انقضا: {_fmt_ts(exp) if exp else 'ندارد'}", f"👥 Uses: {max_uses or 'unlimited'} · ⏳ Expires: {_fmt_ts(exp) if exp else 'never'}")
                + "\n" + e.t("بازیکن‌ها در پیوی ربات بنویسند:", "Players send in private chat:") + f" <code>/redeem {esc(code)}</code>")


def esc_rewards(r: dict, lang: str) -> str:
    return esc(rewards_text(r, lang))


@acmd("codes", 60, "/codes", "فهرست ردیم کدها", "List redeem codes")
async def c_codes(e: Env):
    docs = await list_codes(25)
    if not docs:
        return await e.say(e.t("هنوز کدی نساخته‌ای.", "No codes yet."))
    now = int(time.time())
    lines = []
    for d in docs:
        stt = code_state(d, now)
        lines.append(f"<code>{esc(d['_id'])}</code> · {(CODE_FA if e.lang == 'fa' else CODE_EN)[stt]} · {d.get('uses', 0)}/{d.get('max_uses') or '∞'}")
    await e.say("\n".join(lines))


@acmd("code_info", 60, "/code_info <CODE>", "جزئیات یک کد و کسانی که استفاده کرده‌اند", "Code details and who used it")
async def c_code_info(e: Env):
    d = await get_code(e.raw) if e.raw else None
    if not d:
        return await e.say(e.t("❌ کد پیدا نشد.", "❌ Code not found.") if e.raw else "<code>/code_info CODE</code>")
    stt = code_state(d)
    used = d.get("used_by", [])
    await e.say(f"🎟 <code>{esc(d['_id'])}</code> · {(CODE_FA if e.lang == 'fa' else CODE_EN)[stt]}\n\n" + esc_rewards(d.get("rewards") or {}, e.lang)
                + f"\n\n👥 {d.get('uses', 0)}/{d.get('max_uses') or '∞'} · ⏳ {_fmt_ts(d.get('expires_at', 0)) if d.get('expires_at') else '—'}"
                + (f"\n📝 {esc(d['note'])}" if d.get("note") else "")
                + ("\n" + e.t("آخرین استفاده‌کننده‌ها: ", "Latest users: ") + " ".join(f"<code>{u}</code>" for u in used[-10:]) if used else ""))


@acmd("code_off", 60, "/code_off <CODE>", "خاموش کردن کد", "Disable a code")
async def c_code_off(e: Env):
    ok = bool(e.raw) and await set_code_active(e.raw, False)
    if ok:
        await alog(e.uid, "code_off", e.raw.upper(), None, None, "cmd")
    await e.say("⛔ OK" if ok else e.t("❌ کد پیدا نشد.", "❌ Code not found."))


@acmd("code_on", 60, "/code_on <CODE>", "روشن کردن دوباره‌ی کد", "Re-enable a code")
async def c_code_on(e: Env):
    ok = bool(e.raw) and await set_code_active(e.raw, True)
    if ok:
        await alog(e.uid, "code_on", e.raw.upper(), None, None, "cmd")
    await e.say("✅ OK" if ok else e.t("❌ کد پیدا نشد.", "❌ Code not found."))


@acmd("code_del", 80, "/code_del <CODE>", "حذف کامل کد", "Delete a code")
async def c_code_del(e: Env):
    ok = bool(e.raw) and await delete_code(e.raw)
    if ok:
        await alog(e.uid, "code_del", e.raw.upper(), None, None, "cmd")
    await e.say("🗑 OK" if ok else e.t("❌ کد پیدا نشد.", "❌ Code not found."))


# ---- mass gifts (two steps) ----------------------------------------------------------------------------------------------
GIFT_USAGE = "/gift_all <coins|xp|token> <amount>   یا   /gift_all item <item> [qty]"


@acmd("gift_all", 80, GIFT_USAGE, "هدیه به همه‌ی بازیکن‌ها (با تایید)", "Gift everyone (needs confirmation)")
async def c_gift_all(e: Env):
    if not e.args:
        return await e.usage()
    kind = {"coins": "coins", "سکه": "coins", "xp": "xp", "تجربه": "xp", "token": "tokens", "tokens": "tokens", "توکن": "tokens", "item": "item", "آیتم": "item"}.get(e.args[0].lower())
    if not kind or len(e.args) < 2:
        return await e.usage()
    item_id = None
    if kind == "item":
        q, n = _split_qty(e.args[1:])
        item_id = await _pick_item(e, q)
        if not item_id:
            return
        if n > MAX_QTY:
            return await e.say(e.t(f"❌ حداکثر {MAX_QTY} عدد.", f"❌ Max {MAX_QTY}."))
    else:
        n = parse_amount(e.args[1])
        if not n or n > MAX_COINS:
            return await e.usage()
    total = await col("characters").count_documents({})
    code = str(random.randint(100000, 999999))
    await col("admin_gift_confirms").update_one({"admin": e.uid}, {"$set": {"code": code, "kind": kind, "n": n, "item": item_id, "at": int(time.time())}}, upsert=True)
    what = f"{esc(iname(item_id, e.lang))} ×{n:,}" if kind == "item" else {"coins": f"🪙 {n:,}", "xp": f"✨ {n:,} XP", "tokens": f"🎟 {n:,}"}[kind]
    await e.say(e.t(f"⚠️ <b>هدیه‌ی همگانی</b>\n{what} برای <b>{total:,}</b> بازیکن.\nبرای تایید تا ۲ دقیقه: <code>/gift_yes {code}</code>",
                    f"⚠️ <b>Mass gift</b>\n{what} for <b>{total:,}</b> players.\nConfirm within 2 minutes: <code>/gift_yes {code}</code>"))


@acmd("gift_yes", 80, "/gift_yes <code>", "تایید هدیه‌ی همگانی", "Confirm the mass gift")
async def c_gift_yes(e: Env):
    d = await col("admin_gift_confirms").find_one_and_delete({"admin": e.uid})
    if not d or not e.args or e.args[0] != d["code"] or time.time() - d["at"] > 120:
        return await e.say(e.t("❌ کد تایید اشتباه است یا منقضی شده.", "❌ Wrong or expired confirmation code."))
    await alog(e.uid, "gift_all", d["kind"], None, {"n": d["n"], "item": d.get("item")}, "cmd")
    await e.say(e.t("🚀 ارسال هدیه شروع شد؛ نتیجه را در پیوی می‌فرستم.", "🚀 Gifting started; I will DM you the result."))

    async def run():
        count = await gift_all(d["kind"], d["n"], d.get("item"))
        try:
            await e.bot.send_message(e.uid, e.t(f"🎁 هدیه‌ی همگانی تمام شد: {count:,} بازیکن.", f"🎁 Mass gift finished: {count:,} players."))
        except Exception:
            pass
    asyncio.create_task(run())


# ---- admins (owner only) ---------------------------------------------------------------------------------------------------
@acmd("addadmin", 100, "/addadmin <id|@user|reply> [admin|super|moderator|support]", "افزودن ادمین", "Add an admin")
async def c_addadmin(e: Env):
    tid = await target(e, need_char=False)
    if tid is None:
        return
    word = e.args[0] if e.args else "admin"
    role = ROLE_ALIAS.get(word, word)
    if role not in ROLES or role == "owner":
        role = "admin"
    await col("admin_users").update_one({"user_id": tid}, {"$set": {"role": role}}, upsert=True)
    try:
        from handlers_adminpanel import refresh_admin_commands
        await refresh_admin_commands(e.bot, tid, True)
    except Exception:
        log.exception("admin menu refresh failed")
    await alog(e.uid, "addadmin", tid, None, role, "cmd")
    await e.say(f"👑 {role} → <code>{tid}</code>")


@acmd("rmadmin", 100, "/rmadmin <id|@user|reply>", "حذف ادمین", "Remove an admin")
async def c_rmadmin(e: Env):
    tid = await target(e, need_char=False)
    if tid is None:
        return
    await col("admin_users").delete_one({"user_id": tid})
    try:
        from handlers_adminpanel import refresh_admin_commands
        await refresh_admin_commands(e.bot, tid, False)
    except Exception:
        log.exception("admin menu refresh failed")
    await alog(e.uid, "rmadmin", tid, None, None, "cmd")
    await e.say(f"✅ <code>{tid}</code>")


# ---- player commands: /redeem and /tokens -----------------------------------------------------------------------------------
REDEEM_FA = {"noreg": "اول باید ثبت‌نام کنی.", "nocode": "❌ این کد وجود ندارد.", "off": "⛔ این کد غیرفعال شده.", "expired": "⌛ این کد منقضی شده.",
             "used": "ℹ️ این کد را قبلاً استفاده کرده‌ای.", "full": "🈵 ظرفیت این کد تمام شده.",
             "art_has": "❌ برای گرفتن این جایزه باید اول آرتیفکت فعلی‌ات را رها کنی (کد هنوز مصرف نشد).",
             "art_busy": "⏳ جایزه همین لحظه در حال جابه‌جایی است؛ چند ثانیه بعد دوباره امتحان کن."}
REDEEM_EN = {"noreg": "Register first.", "nocode": "❌ That code does not exist.", "off": "⛔ That code is disabled.", "expired": "⌛ That code has expired.",
             "used": "ℹ️ You already used that code.", "full": "🈵 That code has no uses left.",
             "art_has": "❌ Release your current artifact first to receive this prize (the code was not used up).",
             "art_busy": "⏳ The prize is mid-transfer; try again in a few seconds."}


async def _player_ctx(message: Message):
    from handlers_core import gate, make_ctx
    await touch_user(message.from_user)
    ctx = await make_ctx(message.from_user, message.chat, message.bot, message)
    blocked = await gate(ctx)
    return ctx, blocked


@router.message(Command("redeem", "code"))
async def cmd_redeem(message: Message, command: CommandObject):
    if message.from_user is None or message.from_user.is_bot:
        return
    ctx, blocked = await _player_ctx(message)
    if blocked:
        return await message.reply(blocked.text)
    if message.chat.type != "private":
        return await message.reply(tr(ctx.lang, "🔒 کد را در پیوی ربات بفرست (نه در گروه).", "🔒 Send the code in private chat, not in a group."))
    if not command.args:
        return await message.reply(tr(ctx.lang, "🎟 مثال: <code>/redeem SENKA-AB12CD34</code>", "🎟 Example: <code>/redeem SENKA-AB12CD34</code>"))
    if not allow(ctx.uid, "redeem", 3):
        return await message.reply(tr(ctx.lang, "کمی صبر کن.", "Slow down a moment."))
    st, d = await redeem(ctx.uid, command.args.split()[0])
    if st != "ok":
        return await message.reply((REDEEM_FA if ctx.lang == "fa" else REDEEM_EN)[st])
    await message.reply(tr(ctx.lang, "🎁 <b>کد با موفقیت ثبت شد!</b>\n\n", "🎁 <b>Code redeemed!</b>\n\n") + esc_rewards(d.get("rewards") or {}, ctx.lang))


@router.message(Command("tokens", "token"))
async def cmd_tokens(message: Message):
    if message.from_user is None or message.from_user.is_bot:
        return
    ctx, blocked = await _player_ctx(message)
    if blocked:
        return await message.reply(blocked.text)
    ch = await get_char(ctx.uid)
    if not ch:
        return await message.reply(tr(ctx.lang, "اول باید ثبت‌نام کنی.", "Register first."))
    await message.reply(f"🎟 {tr(ctx.lang, 'توکن‌های تو', 'Your tokens')}: <b>{fnum(ch.get('tokens', 0), ctx.lang)}</b>")


# ---- button panel: 🎁 Gifts & codes -------------------------------------------------------------------------------------------
def _T(ctx, fa, en):
    return fa if ctx.lang == "fa" else en


def _deny(ctx):
    return Out(alert=_T(ctx, "دسترسی نداری.", "No permission."))


@action("adg")
async def gifts_panel(ctx, arg):
    lvl = await admin_level(ctx.uid)
    if lvl < 20:
        return _deny(ctx)
    op, _, rest = arg.partition(".")
    back = nav(ctx, ("adg", ""))
    if op == "":
        text = head(ctx, "ttl_adm") + _T(ctx, "🎁 <b>هدیه، آرتیفکت و کدها</b>\nبرای دادن آرتیفکت/توکن به یک نفر: از «👤 کاربر» او را پیدا کن، یا در چت دستورات اسلش را بزن:\n\n",
                                         "🎁 <b>Gifts, artifacts & codes</b>\nTo give an artifact/tokens: open the player under “👤 Users”, or use the slash commands:\n\n")
        text += "<code>/give_art</code> · <code>/take_art</code> · <code>/give_item</code> · <code>/give_token</code>\n<code>/code_new</code> · <code>/codes</code> · <code>/gift_all</code> · <code>/acmds</code>"
        rows = [[(_T(ctx, "💎 آرتیفکت‌ها", "💎 Artifacts"), "adg", "a"), (_T(ctx, "🔮 هوگیوکو", "🔮 Hōgyoku"), "adg", "h")]]
        if lvl >= 60:
            rows.append([(_T(ctx, "🎟 ردیم کدها", "🎟 Redeem codes"), "adg", "c")])
        rows.append(nav(ctx, ("adm", "")))
        return Out(text, rows)
    if op == "a":
        from service_drops import art_registry
        lines = []
        for a, st, holders in await art_registry():
            who = (" → " + ", ".join(esc(h["name"]) for h in holders)) if holders else ""
            lines.append(f"{a['icon']} {esc(a['name_fa' if ctx.lang == 'fa' else 'name_en'])} · {STATE_FA.get(st, st) if ctx.lang == 'fa' else st}{who}")
        return Out(head(ctx, "ttl_adm") + "\n".join(lines), [back])
    if op == "h":
        h = await hogyoku_info()
        body = f"🔮 {esc(h[1])} (<code>{h[0]}</code>) · {_T(ctx, 'سطح', 'Lv')} {h[2]}" if h else _T(ctx, "🔮 هنوز صاحبی ندارد.", "🔮 No holder yet.")
        return Out(head(ctx, "ttl_adm") + body, [back])
    if op == "c":
        if lvl < 60:
            return _deny(ctx)
        now = int(time.time())
        lines = [f"<code>{esc(d['_id'])}</code> · {(CODE_FA if ctx.lang == 'fa' else CODE_EN)[code_state(d, now)]} · {d.get('uses', 0)}/{d.get('max_uses') or '∞'}" for d in await list_codes(20)]
        return Out(head(ctx, "ttl_adm") + ("\n".join(lines) or "—") + "\n\n" + _T(ctx, "ساخت کد: ", "Create: ") + "<code>/code_new auto coins=5000 token=3 uses=20 hours=48</code>", [back])
    # ---- actions on one player: arg = "<op>.<tid>[.<index>]"
    parts = rest.split(".")
    if not parts[0].lstrip("-").isdigit():
        return Out(alert="?")
    tid = int(parts[0])
    from handlers_adminpanel import _user_card
    if op in ("t1", "t2") and lvl >= 60:
        n = 10 if op == "t1" else 100
        await add_tokens(tid, n, "admin")
        await alog(ctx.uid, "give_token", tid, None, {"delta": n}, "panel")
        await _dm(ctx.bot, tid, f"🎁 ادمین 🎟 {n} به تو داد!", f"🎁 An admin gave you 🎟 {n}!")
        out = await _user_card(ctx, tid)
        out.alert = _T(ctx, "انجام شد ✅", "Done ✅")
        return out
    if op == "pa" and lvl >= 80:
        items = [(f"{a['icon']} {a['name_fa' if ctx.lang == 'fa' else 'name_en']}"[:30], "adg", f"ga.{tid}.{i}") for i, a in enumerate(ARTIFACTS)]
        rows = chunk(items, 2) + [nav(ctx, ("adb", f"v.{tid}"))]
        return Out(head(ctx, "ttl_adm") + _T(ctx, "کدام آرتیفکت داده شود؟", "Which artifact?"), rows)
    if op == "ga" and lvl >= 80 and len(parts) == 2 and parts[1].isdigit() and int(parts[1]) < len(ARTIFACTS):
        a = ARTIFACTS[int(parts[1])]
        return Out(head(ctx, "ttl_adm") + _T(ctx, f"{a['icon']} «{esc(a['name_fa'])}» به <code>{tid}</code> داده شود؟\n(اگر کسی دارد، از او گرفته می‌شود؛ آرتیفکت فعلی گیرنده آزاد می‌شود.)",
                                              f"Give {a['icon']} {esc(a['name_en'])} to <code>{tid}</code>?\n(If someone holds it, it is taken from them; the receiver's current artifact is freed.)"),
                   [[(_T(ctx, "✅ بله", "✅ Yes"), "adg", f"gy.{tid}.{parts[1]}"), (_T(ctx, "❌ نه", "❌ No"), "adb", f"v.{tid}")]])
    if op == "gy" and lvl >= 80 and len(parts) == 2 and parts[1].isdigit() and int(parts[1]) < len(ARTIFACTS):
        aid = ARTIFACTS[int(parts[1])]["_id"]
        st, prev = await artifact_give(aid, tid, replace=True)
        if st == "ok":
            await alog(ctx.uid, "give_art", tid, {"from": prev}, {"art": aid}, "panel")
            if prev and prev != tid:
                await _dm(ctx.bot, prev, f"⚠️ آرتیفکت «{ART_BY_ID[aid]['name_fa']}» توسط ادمین از تو گرفته شد.", f"⚠️ An admin took {ART_BY_ID[aid]['name_en']} from you.")
            await _dm(ctx.bot, tid, f"🎁 ادمین آرتیفکت {_aname(aid, 'fa')} را به تو داد!", f"🎁 An admin gave you {_aname(aid, 'en')}!")
        out = await _user_card(ctx, tid)
        out.alert = _T(ctx, "انجام شد ✅", "Done ✅") if st in ("ok", "already") else _T(ctx, "ناموفق: ", "Failed: ") + st
        return out
    if op == "hq" and lvl >= 80:
        return Out(head(ctx, "ttl_adm") + _T(ctx, f"🔮 هوگیوکو به <code>{tid}</code> داده شود؟", f"🔮 Give the Hōgyoku to <code>{tid}</code>?"),
                   [[(_T(ctx, "✅ بله", "✅ Yes"), "adg", f"hy.{tid}"), (_T(ctx, "❌ نه", "❌ No"), "adb", f"v.{tid}")]])
    if op == "hy" and lvl >= 80:
        st, old = await hogyoku_give(tid)
        if st == "ok":
            await alog(ctx.uid, "give_hogyoku", tid, {"from": old}, None, "panel")
            await _dm(ctx.bot, tid, "🔮 ادمین هوگیوکو را به تو داد!", "🔮 An admin gave you the Hōgyoku!")
            if old and old != tid:
                await _dm(ctx.bot, old, "⚠️ هوگیوکو توسط ادمین از تو گرفته شد.", "⚠️ An admin took the Hōgyoku from you.")
        out = await _user_card(ctx, tid)
        out.alert = _T(ctx, "انجام شد ✅", "Done ✅") if st in ("ok", "already") else _T(ctx, "ناموفق", "Failed")
        return out
    return _deny(ctx)
