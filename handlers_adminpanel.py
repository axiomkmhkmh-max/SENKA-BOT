"""Admin button panel (rebuilt). The text commands in handlers_admin and the slash commands keep working.

Layout: hub -> category page -> action. Every action re-checks its permission level when pressed AND
when the typed input arrives, so an old message can never be used beyond the admin's level.

Typed input: pressing an input button stores what is pending in `admin_pending` and marks the admin's
next text message as an input (`inputs` collection, kind `ad_act`); handlers_core routes it to act_input.
Dangerous actions (full reset, admin changes, broadcast) need a second press.
"""
import asyncio
import logging
import re
import time
from datetime import datetime

from aiogram.types import BotCommand, BotCommandScopeChat

from admin_fa import LANG_FA, ROLE_FA, setting_label
from admin_panel_logic import adjust_setting, coerce_setting, page_bounds, parse_amount, role_ok, split_id_rest, split_target
from cmdlist import ADMIN_CMDS_EN, ADMIN_CMDS_FA, CMD_EN, CMD_FA
from config import GAME_DEFAULTS, settings
from data_items import ALL
from database import col, game_settings, ping, set_game_setting
from handlers_admin import ROLES, _broadcast, admin_level, admin_world, alog, dashboard
from i18n import esc, fnum
from service_cores import get_cores, grant_cores, spend_cores
from service_economy import inv_add, inv_remove
from service_player import add_coins, add_xp, get_char
from ui import Out, action, head, input_handler, nav

log = logging.getLogger("senka.adminpanel")
BOOT = time.time()
PAGE = 10
PENDING_TTL = 180
KEYS = sorted(GAME_DEFAULTS)
ROLE_CHOICES = {"admin", "moderator", "support", "super"}
RESET_COLLECTIONS = ("characters", "inventories", "player_quests", "gacha", "registration")

# action -> (permission level, prompt fa, prompt en, where «back» goes)
ASK = {
    "find":       (20, "نام، @یوزرنیم یا آیدی عددی پلیر را بفرست:", "Send a name, @username or numeric id:", ("adu", "")),
    "ban":        (40, "بفرست: `<آیدی> [دلیل]`", "Send: `<id> [reason]`", ("admo", "")),
    "unban":      (40, "آیدی عددی پلیر را بفرست:", "Send the numeric id:", ("admo", "")),
    "warn":       (40, "بفرست: `<آیدی> [دلیل]`", "Send: `<id> [reason]`", ("admo", "")),
    "give_coins": (60, "بفرست: `<آیدی> <مقدار>`", "Send: `<id> <amount>`", ("ade", "")),
    "take_coins": (60, "بفرست: `<آیدی> <مقدار>`", "Send: `<id> <amount>`", ("ade", "")),
    "give_xp":    (60, "بفرست: `<آیدی> <مقدار>`", "Send: `<id> <amount>`", ("ade", "")),
    "give_cores": (60, "بفرست: `<آیدی> <تعداد>` (هسته‌ی روح 🔮)", "Send: `<id> <count>` (Soul Cores 🔮)", ("ade", "")),
    "take_cores": (60, "بفرست: `<آیدی> <تعداد>`", "Send: `<id> <count>`", ("ade", "")),
    "give_item":  (60, "بفرست: `<آیدی> <item_id> [تعداد]`", "Send: `<id> <item_id> [count]`", ("ade", "")),
    "take_item":  (60, "بفرست: `<آیدی> <item_id> [تعداد]`", "Send: `<id> <item_id> [count]`", ("ade", "")),
    "reset":      (80, "آیدی پلیری که می‌خوای ریست بشه را بفرست:", "Send the id of the player to reset:", ("admo", "")),
    "addadmin":   (100, "بفرست: `<آیدی> [admin|moderator|support|super]`", "Send: `<id> [role]`", ("ada", "")),
    "rmadmin":    (100, "آیدی ادمینی که برداشته می‌شود را بفرست:", "Send the admin id to remove:", ("ada", "")),
    "bcast":      (60, "متن پیام همگانی را بفرست (بعدش گیرنده را انتخاب می‌کنی):", "Send the broadcast text (you pick the audience next):", ("adc", "")),
    "worldset":   (60, "بفرست: `threat|stability <0-100>`", "Send: `threat|stability <0-100>`", ("adw", "")),
    "setkey":     (80, "مقدار جدید را بفرست:", "Send the new value:", ("ads", "0")),
}


REPLY_FA = "\n↩️ یا روی پیام بازیکن ریپلای کن و فقط بقیه را بنویس."
REPLY_EN = "\n↩️ Or reply to the player's message and send only the rest."
REPLY_ACTIONS = {"find", "ban", "unban", "warn", "give_coins", "take_coins", "give_xp", "give_cores", "take_cores",
                 "give_item", "take_item", "reset", "addadmin", "rmadmin", "give_pick", "give_summon"}
ONE_NUMBER = {"give_coins", "take_coins", "give_xp", "give_cores", "take_cores", "give_pick", "give_summon"}


def T(ctx, fa, en):
    return fa if ctx.lang == "fa" else en


async def _need(ctx, lvl: int) -> bool:
    return await admin_level(ctx.uid) >= lvl


def _deny(ctx):
    return Out(alert=T(ctx, "دسترسی نداری.", "No permission."))


def _back(ctx, code="adm", arg=""):
    return nav(ctx, (code, arg))


# ---- pending input state -------------------------------------------------------------------------------
WAITING: dict = {}  # uid -> time an input button was pressed; lets group chats pick up the typed answer cheaply


def admin_waiting(uid: int) -> bool:
    t0 = WAITING.get(uid)
    if t0 is None:
        return False
    if time.time() - t0 > PENDING_TTL:
        WAITING.pop(uid, None)
        return False
    return True


def _reply_target(ctx):
    """The player the admin replied to (never a bot), or None."""
    rp = getattr(ctx.message, "reply_to_message", None)
    u = getattr(rp, "from_user", None)
    return u.id if u is not None and not u.is_bot else None


async def _pending_set(uid: int, action_name: str, target=None, extra=None):
    now = time.time()
    if action_name != "bcast_ready":
        WAITING[uid] = now
    await col("admin_pending").update_one(
        {"_id": uid}, {"$set": {"action": action_name, "target": target, "extra": extra, "at": now}}, upsert=True)
    if action_name != "bcast_ready":
        await col("inputs").update_one({"user_id": uid}, {"$set": {"kind": "ad_act", "at": int(now)}}, upsert=True)


async def _pending_get(uid: int):
    doc = await col("admin_pending").find_one({"_id": uid})
    if not doc or time.time() - doc.get("at", 0) > PENDING_TTL:
        return None
    return doc


async def _pending_clear(uid: int):
    WAITING.pop(uid, None)
    await col("admin_pending").delete_one({"_id": uid})


# ---- admin slash menu (main.py and the admin commands use this) --------------------------------------------
async def refresh_admin_commands(bot, uid=None, on=True):
    """Admins also get the admin commands in their own '/' menu (per-chat scope)."""
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


# ---- hub (the 'adm' action in handlers_admin calls this) ----------------------------------------------------
async def main_menu(ctx, lvl):
    st = await game_settings()
    on = bool(st.get("maintenance"))
    mt = T(ctx, "🔧 تعمیرات: روشن ✅" if on else "🔧 تعمیرات: خاموش",
           "🔧 Maintenance: ON ✅" if on else "🔧 Maintenance: off")
    role = next((k for k, v in ROLES.items() if v == lvl), "?")
    role = ROLE_FA.get(role, role) if ctx.lang == "fa" else role
    # (label, code, arg, minimum level) — a button only appears when the admin can use it
    cats = [
        (T(ctx, "👤 کاربران", "👤 Users"), "adu", "", 20),
        (T(ctx, "🛡 مدیریت", "🛡 Moderation"), "admo", "", 40),
        (T(ctx, "🎁 اقتصاد", "🎁 Economy"), "ade", "", 60),
        (T(ctx, "🌍 دنیا و باس", "🌍 World & bosses"), "adw", "", 20),
        (T(ctx, "📣 همگانی", "📣 Broadcast"), "adc", "", 60),
        (T(ctx, "⚙️ تنظیمات زنده", "⚙️ Live settings"), "ads", "0", 80),
        (T(ctx, "📜 لاگ مدیریت", "📜 Admin log"), "adl", "0", 20),
        (T(ctx, "👑 ادمین‌ها", "👑 Admins"), "ada", "", 100),
        (T(ctx, "🩺 سلامت سیستم", "🩺 System health"), "adh", "", 20),
    ]
    visible = [(label, code, arg) for label, code, arg, need in cats if lvl >= need]
    rows = [visible[i:i + 2] for i in range(0, len(visible), 2)]
    if lvl >= 60:
        rows.append([(mt, "adt", "")])
    rows.append([(T(ctx, "🎁 هدیه و کدها", "🎁 Gifts & codes"), "adg", "")])
    rows.append(nav(ctx))
    return Out(head(ctx, "ttl_adm") + f"<i>{role} ({lvl})</i>\n\n" + await dashboard(ctx), rows)


# ---- users --------------------------------------------------------------------------------------------------
async def _resolve_user(text: str):
    tid, _ = split_id_rest(text)
    if tid is not None:
        return tid
    name = (text or "").strip().lstrip("@")
    if not name:
        return None
    u = await col("users").find_one({"username": {"$regex": f"^{re.escape(name)}$", "$options": "i"}},
                                    {"telegram_id": 1})
    return u["telegram_id"] if u else None


async def user_card(ctx, tid: int):
    L = ctx.lang
    lvl = await admin_level(ctx.uid)
    u = await col("users").find_one({"telegram_id": tid})
    if not u:
        return Out(T(ctx, "کاربر پیدا نشد.", "User not found."), [_back(ctx, "adu", "")])
    ch = await get_char(tid)
    body = (f"<code>{tid}</code> @{esc(u.get('username') or '-')} · "
            f"{LANG_FA.get(u.get('lang'), u.get('lang', '?')) if L == 'fa' else u.get('lang', '?')}\n")
    if u.get("banned"):
        body += T(ctx, "🚫 بن‌شده", "🚫 banned") + (f" — {esc(u['ban_reason'])}" if u.get("ban_reason") else "") + "\n"
    body += f"⚠️ {u.get('warns', 0)}\n"
    if ch:
        from data_races import RACES
        rn = RACES.get(ch["race"], {}).get("name_fa" if L == "fa" else "name_en", ch["race"])
        body += (f"<b>{esc(ch['name'])}</b> | {rn} | {T(ctx, 'سطح', 'Lv')} {ch['level']} | "
                 f"🪙 {fnum(ch['coins'], L)}\n")
        body += f"🔮 {fnum(await get_cores(tid), L)} {T(ctx, 'هسته‌ی روح', 'Soul Cores')}"
    else:
        body += T(ctx, "هنوز کاراکتری ندارد.", "No character yet.")

    rows = []
    if lvl >= 40:
        if u.get("banned"):
            rows.append([(T(ctx, "✅ آنبن", "✅ Unban"), "adx", f"ub:{tid}")])
        else:
            rows.append([(T(ctx, "🚫 بن", "🚫 Ban"), "adx", f"bn:{tid}"), (T(ctx, "⚠️ اخطار", "⚠️ Warn"), "adx", f"wn:{tid}")])
    if lvl >= 60 and ch:
        rows.append([(T(ctx, "+۱۰ هزار 🪙", "+10k 🪙"), "adx", f"c1:{tid}"),
                     (T(ctx, "+۱۰۰ هزار 🪙", "+100k 🪙"), "adx", f"c2:{tid}"),
                     (T(ctx, "+۱ هزار XP", "+1k XP"), "adx", f"x1:{tid}")])
        rows.append([(T(ctx, "🔮 +۱ هسته", "🔮 +1 core"), "adx", f"k1:{tid}")])
    if lvl >= 80:
        rows.append([(T(ctx, "🔄 ریست پلیر", "🔄 Reset player"), "adx", f"rs:{tid}")])
    rows.append(_back(ctx, "adu", ""))
    return Out(head(ctx, "ttl_adm") + body, rows)


@action("adu")
async def users_panel(ctx, arg):
    if not await _need(ctx, 20):
        return _deny(ctx)
    rows = [[(T(ctx, "🔍 جستجو", "🔍 Search"), "adq", "find"), (T(ctx, "🆕 جدیدترین‌ها", "🆕 Newest"), "adn", "new:0")],
            [(T(ctx, "💰 ثروتمندترین‌ها", "💰 Richest"), "adn", "rich:0"),
             (T(ctx, "🔝 بالاترین سطح", "🔝 Top level"), "adn", "lvl:0")],
            _back(ctx)]
    return Out(head(ctx, "ttl_adm") + T(ctx, "یک کاربر را جستجو کن یا از لیست‌ها انتخاب کن.",
                                          "Search a user or pick a list."), rows)


@action("adn")
async def users_list(ctx, arg):
    if not await _need(ctx, 20):
        return _deny(ctx)
    mode, _, page_s = (arg or "new:0").partition(":")
    if mode == "new":
        docs = await col("users").find({}, {"telegram_id": 1}).sort("telegram_id", -1).limit(200).to_list(200)
        ids = [d["telegram_id"] for d in docs]
        label = T(ctx, "جدیدترین", "Newest")
    else:
        field = "coins" if mode == "rich" else "level"
        docs = await col("characters").find({}, {"user_id": 1}).sort(field, -1).limit(200).to_list(200)
        ids = [d["user_id"] for d in docs]
        label = T(ctx, "ثروتمندترین", "Richest") if mode == "rich" else T(ctx, "بالاترین سطح", "Top level")
    want = int(page_s) if page_s.isdigit() else 0
    start, pages, page = page_bounds(len(ids), want, PAGE)
    rows = [[(str(tid), "adp", str(tid))] for tid in ids[start:start + PAGE]]
    nav_row = []
    if page > 0:
        nav_row.append(("◀️", "adn", f"{mode}:{page - 1}"))
    if page < pages - 1:
        nav_row.append(("▶️", "adn", f"{mode}:{page + 1}"))
    if nav_row:
        rows.append(nav_row)
    rows.append(_back(ctx, "adu", ""))
    return Out(head(ctx, "ttl_adm") + f"<b>{label}</b> ({page + 1}/{pages})", rows)


@action("adp")
async def user_view(ctx, arg):
    if not await _need(ctx, 20):
        return _deny(ctx)
    tid, _ = split_id_rest(arg)
    if tid is None:
        return Out(alert="?")
    return await user_card(ctx, tid)


# ---- moderation page ------------------------------------------------------------------------------------------
@action("admo")
async def moderation_panel(ctx, arg):
    if not await _need(ctx, 40):
        return _deny(ctx)
    banned = await col("users").find({"banned": True}, {"telegram_id": 1}).limit(PAGE).to_list(PAGE)
    lines = [f"🚫 <code>{d['telegram_id']}</code>" for d in banned] or [T(ctx, "کسی بن نیست.", "No one is banned.")]
    rows = [[(T(ctx, "🚫 بن", "🚫 Ban"), "adq", "ban"), (T(ctx, "✅ آنبن", "✅ Unban"), "adq", "unban")],
            [(T(ctx, "⚠️ اخطار", "⚠️ Warn"), "adq", "warn")]]
    if await _need(ctx, 80):
        rows.append([(T(ctx, "🔄 ریست پلیر", "🔄 Reset player"), "adq", "reset")])
    rows.append(_back(ctx))
    return Out(head(ctx, "ttl_adm") + T(ctx, "مدیریت کاربران", "Moderation") + "\n" + "\n".join(lines), rows)


# ---- ask an input (any action in ASK) --------------------------------------------------------------------------
@action("adq")
async def ask_action(ctx, arg):
    name, _, key = (arg or "").partition(":")
    spec = ASK.get(name)
    if spec is None:
        return Out(alert="?")
    need, fa, en, (back_code, back_arg) = spec
    if not await _need(ctx, need):
        return _deny(ctx)
    if name == "setkey":
        if key not in GAME_DEFAULTS:
            return Out(alert="?")
        await _pending_set(ctx.uid, "setkey", target=key)
        return Out(head(ctx, "ttl_adm") + f"<code>{key}</code>\n" + esc(T(ctx, fa, en))
                   + "\n\n" + esc(T(ctx, "برای لغو: «لغو» بفرست.", "To cancel: send «cancel».")),
                   [_back(ctx, back_code, back_arg)])
    await _pending_set(ctx.uid, name)
    hint = T(ctx, REPLY_FA, REPLY_EN) if name in REPLY_ACTIONS else ""
    return Out(head(ctx, "ttl_adm") + esc(T(ctx, fa, en)) + hint + "\n\n"
               + esc(T(ctx, "برای لغو: «لغو» بفرست.", "To cancel: send «cancel».")),
               [_back(ctx, back_code, back_arg)])


# ---- quick buttons on a user card ---------------------------------------------------------------------------------
@action("adx")
async def user_quick(ctx, arg):
    op, _, tid_s = (arg or "").partition(":")
    tid, _ = split_id_rest(tid_s)
    if tid is None:
        return Out(alert="?")
    need = {"bn": 40, "ub": 40, "wn": 40, "c1": 60, "c2": 60, "x1": 60, "k1": 60, "rs": 80, "rk": 80}.get(op)
    if need is None or not await _need(ctx, need):
        return _deny(ctx)
    u = await col("users").find_one({"telegram_id": tid})
    if not u:
        return Out(alert=T(ctx, "کاربر پیدا نشد.", "User not found."))
    if op in ("bn", "wn", "rs", "rk"):
        # nobody acts on the owner, and nobody acts on an admin of their own level or higher
        if tid == settings.owner_id or await admin_level(tid) >= await admin_level(ctx.uid):
            return Out(alert=T(ctx, "اجازه نداری.", "Not allowed."))

    if op == "bn":
        await col("users").update_one({"telegram_id": tid}, {"$set": {"banned": True, "ban_reason": "panel"}})
        await alog(ctx.uid, "ban", tid, {"banned": bool(u.get("banned"))}, {"banned": True}, "panel")
    elif op == "ub":
        await col("users").update_one({"telegram_id": tid}, {"$set": {"banned": False}})
        await alog(ctx.uid, "unban", tid, {"banned": bool(u.get("banned"))}, {"banned": False}, "panel")
    elif op == "wn":
        await col("users").update_one({"telegram_id": tid}, {"$inc": {"warns": 1}})
        await alog(ctx.uid, "warn", tid, None, None, "panel")
    elif op in ("c1", "c2"):
        n = 10_000 if op == "c1" else 100_000
        await add_coins(tid, n, "admin")
        await alog(ctx.uid, "give_coins", tid, None, {"delta": n}, "panel")
    elif op == "x1":
        await add_xp(tid, 1000, "admin", apply_rate=False)
        await alog(ctx.uid, "give_xp", tid, None, {"delta": 1000}, "panel")
    elif op == "k1":
        await grant_cores(tid, 1, f"admin:{ctx.uid}")
        await alog(ctx.uid, "give_cores", tid, None, {"delta": 1}, "panel")
    elif op == "rs":
        text = head(ctx, "ttl_adm") + T(
            ctx,
            f"⚠️ ریست کامل پلیر <code>{tid}</code>: کاراکتر، ایتم‌ها، کوئست‌ها و گاچا پاک می‌شوند. مطمئنی؟",
            f"⚠️ Full reset of <code>{tid}</code>: character, items, quests and gacha are deleted. Sure?")
        return Out(text, [[(T(ctx, "⚠️ بله، ریست کن", "⚠️ Yes, reset"), "adx", f"rk:{tid}")],
                          _back(ctx, "adu", "")])
    elif op == "rk":
        before = await get_char(tid)
        for c in RESET_COLLECTIONS:
            await col(c).delete_many({"user_id": tid})
        if before and before.get("guild_id"):
            await col("guilds").update_one({"_id": before["guild_id"]}, {"$inc": {"members": -1}})
        await alog(ctx.uid, "reset", tid, {"level": (before or {}).get("level")}, None, "panel")

    out = await user_card(ctx, tid)
    out.alert = T(ctx, "انجام شد ✅", "Done ✅")
    return out


# ---- economy page ----------------------------------------------------------------------------------------------------
@action("ade")
async def economy_panel(ctx, arg):
    if not await _need(ctx, 60):
        return _deny(ctx)
    rows = [[(T(ctx, "💰 دادن سکه", "💰 Give coins"), "adq", "give_coins"),
             (T(ctx, "💸 گرفتن سکه", "💸 Take coins"), "adq", "take_coins")],
            [(T(ctx, "✨ دادن XP", "✨ Give XP"), "adq", "give_xp")],
            [(T(ctx, "🔮 دادن هسته", "🔮 Give cores"), "adq", "give_cores"),
             (T(ctx, "🔮 گرفتن هسته", "🔮 Take cores"), "adq", "take_cores")],
            [(T(ctx, "🎒 دادن آیتم", "🎒 Give item"), "adq", "give_item"),
             (T(ctx, "🎒 گرفتن آیتم", "🎒 Take item"), "adq", "take_item")],
            [(T(ctx, "📋 انتخاب آیتم از لیست", "📋 Pick item from list"), "adi", ""),
             (T(ctx, "🎴 دادن احضار", "🎴 Give summon"), "adz", "")],
            _back(ctx)]
    return Out(head(ctx, "ttl_adm") + T(ctx, "یک عملیات اقتصادی را انتخاب کن. هر کار در لاگ ثبت می‌شود.",
                                          "Pick an economy action. Every change is logged."), rows)


# ---- world & bosses -----------------------------------------------------------------------------------------------------
@action("adw")
async def world_panel(ctx, arg):
    if not await _need(ctx, 20):
        return _deny(ctx)
    lvl = await admin_level(ctx.uid)
    text = await admin_world(ctx, [], lvl)
    rows = []
    if lvl >= 60:
        rows.append([(T(ctx, "👹 اسپان باس جهانی", "👹 Spawn world boss"), "adw_do", "boss_spawn"),
                     (T(ctx, "🛑 پایان باس", "🛑 End boss"), "adw_do", "boss_end")])
        rows.append([(T(ctx, "👹 انتخاب باس از لیست", "👹 Pick a boss"), "adbs", "0"),
                     (T(ctx, "🌀 انتخاب رویداد", "🌀 Pick an event"), "adev", "")])
        rows.append([(T(ctx, "🎯 تنظیم تهدید/ثبات", "🎯 Set threat/stability"), "adq", "worldset")])
    if lvl >= 80:
        rows.append([(T(ctx, "♻️ ریست دنیا", "♻️ Reset world"), "adw_do", "reset")])
    rows.append(_back(ctx))
    return Out(head(ctx, "ttl_adm") + text, rows)


@action("adw_do")
async def world_do(ctx, arg):
    need = {"boss_spawn": 60, "boss_end": 60, "reset": 80}.get(arg)
    if need is None or not await _need(ctx, need):
        return _deny(ctx)
    lvl = await admin_level(ctx.uid)
    args = {"boss_spawn": ["boss", "spawn"], "boss_end": ["boss", "end"], "reset": ["reset"]}[arg]
    res = await admin_world(ctx, args, lvl)
    out = await world_panel(ctx, "")
    out.alert = (res or "")[:180] or T(ctx, "انجام شد ✅", "Done ✅")
    return out


# ---- broadcast ------------------------------------------------------------------------------------------------------------
@action("adc")
async def broadcast_panel(ctx, arg):
    if not await _need(ctx, 60):
        return _deny(ctx)
    return Out(head(ctx, "ttl_adm") + T(ctx, "اول متن پیام را بنویس، بعد گیرنده را انتخاب کن.",
                                          "Write the text first, then pick the audience."),
               [[(T(ctx, "✏️ نوشتن پیام", "✏️ Write message"), "adq", "bcast")], _back(ctx)])


@action("adcs")
async def broadcast_send(ctx, arg):
    if not await _need(ctx, 60):
        return _deny(ctx)
    aud = arg if arg in ("all", "fa", "en") else None
    pend = await _pending_get(ctx.uid)
    if aud is None or not pend or pend.get("action") != "bcast_ready" or not pend.get("extra"):
        return Out(alert=T(ctx, "پیامی برای ارسال نیست.", "No message to send."))
    await _pending_clear(ctx.uid)
    flt = {} if aud == "all" else {"lang": aud}
    asyncio.create_task(_broadcast(ctx.bot, flt, pend["extra"], ctx.uid))
    await alog(ctx.uid, "broadcast", aud, None, pend["extra"][:100], "panel")
    return Out(head(ctx, "ttl_adm") + T(ctx, "📣 ارسال شروع شد؛ نتیجه برایت پیام می‌شود.",
                                          "📣 Sending started; the result will be messaged to you."),
               [_back(ctx, "adc", "")])


# ---- live settings ---------------------------------------------------------------------------------------------------------
@action("ads")
async def settings_list(ctx, arg):
    if not await _need(ctx, 80):
        return _deny(ctx)
    want = int(arg) if str(arg or "").isdigit() else 0
    start, pages, page = page_bounds(len(KEYS), want, PAGE)
    st = await game_settings()
    rows = []
    for i in range(start, min(start + PAGE, len(KEYS))):
        k = KEYS[i]
        rows.append([(f"{setting_label(k, ctx.lang == 'fa')}: {st[k]}"[:60], "adk", f"{i}:open")])
    nav_row = []
    if page > 0:
        nav_row.append(("◀️", "ads", str(page - 1)))
    if page < pages - 1:
        nav_row.append(("▶️", "ads", str(page + 1)))
    if nav_row:
        rows.append(nav_row)
    rows.append(_back(ctx))
    return Out(head(ctx, "ttl_adm") + T(ctx, f"تنظیمات زنده ({page + 1}/{pages}) — روی هر کدام بزن.",
                                          f"Live settings ({page + 1}/{pages}) — tap one."), rows)


@action("adk")
async def setting_edit(ctx, arg):
    if not await _need(ctx, 80):
        return _deny(ctx)
    idx, _, op = (arg or "").partition(":")
    if not idx.isdigit() or int(idx) >= len(KEYS) or op not in ("open", "t", "d", "u", "d1", "u1", "r"):
        return Out(alert="?")
    key = KEYS[int(idx)]
    default = GAME_DEFAULTS[key]
    if op != "open":
        old = (await game_settings())[key]
        new = adjust_setting(default, old, op)
        if new != old:
            await set_game_setting(key, new)
            await alog(ctx.uid, "set", key, old, new, "panel")
    old = (await game_settings())[key]

    if isinstance(default, bool):
        controls = [[(T(ctx, "🔁 تغییر", "🔁 Toggle"), "adk", f"{idx}:t")]]
    else:
        controls = [[("−10%", "adk", f"{idx}:d"), ("+10%", "adk", f"{idx}:u")],
                    [("−1", "adk", f"{idx}:d1"), ("+1", "adk", f"{idx}:u1")]]
    controls.append([(T(ctx, "✏️ مقدار دقیق", "✏️ Exact value"), "adq", f"setkey:{key}")])
    controls.append([(T(ctx, "↩️ پیش‌فرض", "↩️ Default"), "adk", f"{idx}:r")])
    controls.append(_back(ctx, "ads", str(int(idx) // PAGE)))
    text = (head(ctx, "ttl_adm") + f"<b>{esc(setting_label(key, ctx.lang == 'fa'))}</b>\n<code>{key}</code>\n"
            + T(ctx, f"الان: <b>{old}</b> | پیش‌فرض: {default}", f"Now: <b>{old}</b> | default: {default}"))
    return Out(text, controls)


@action("adt")
async def maintenance_toggle(ctx, arg):
    if not await _need(ctx, 60):
        return _deny(ctx)
    st = await game_settings()
    on = not bool(st.get("maintenance"))
    await set_game_setting("maintenance", on)
    await alog(ctx.uid, "maintenance", None, None, on, "panel")
    out = await main_menu(ctx, await admin_level(ctx.uid))
    out.alert = T(ctx, "تعمیرات روشن شد.", "Maintenance ON.") if on else T(ctx, "تعمیرات خاموش شد.", "Maintenance off.")
    return out


# ---- logs ---------------------------------------------------------------------------------------------------------------------
@action("adl")
async def admin_log(ctx, arg):
    if not await _need(ctx, 20):
        return _deny(ctx)
    total = await col("admin_logs").count_documents({})
    want = int(arg) if str(arg or "").isdigit() else 0
    start, pages, page = page_bounds(total, want, PAGE)
    docs = await col("admin_logs").find({}).sort("at", -1).skip(start).limit(PAGE).to_list(PAGE)
    lines = []
    for d in docs:
        when = datetime.fromtimestamp(d.get("at", 0)).strftime("%m-%d %H:%M")
        lines.append(f"<code>{when}</code> {d.get('admin')} · <b>{esc(str(d.get('action')))}</b> → "
                     f"{esc(str(d.get('target', '-')))}")
    body = "\n".join(lines) or T(ctx, "هنوز لاگی نیست.", "No logs yet.")
    rows = []
    nav_row = []
    if page > 0:
        nav_row.append(("◀️", "adl", str(page - 1)))
    if page < pages - 1:
        nav_row.append(("▶️", "adl", str(page + 1)))
    if nav_row:
        rows.append(nav_row)
    rows.append(_back(ctx))
    return Out(head(ctx, "ttl_adm") + f"<i>{page + 1}/{pages}</i>\n" + body, rows)


# ---- admins (owner only) ----------------------------------------------------------------------------------------------------------
@action("ada")
async def admins_panel(ctx, arg):
    if not await _need(ctx, 100):
        return _deny(ctx)
    lines = [f"👑 <code>{settings.owner_id}</code> — {ROLE_FA.get('owner', 'owner') if ctx.lang == 'fa' else 'owner'}"]
    async for d in col("admin_users").find({}).sort("user_id", 1).limit(50):
        role = d.get("role", "?")
        lines.append(f"<code>{d['user_id']}</code> — {ROLE_FA.get(role, role) if ctx.lang == 'fa' else role}")
    rows = [[(T(ctx, "➕ افزودن ادمین", "➕ Add admin"), "adq", "addadmin"),
             (T(ctx, "➖ برداشتن ادمین", "➖ Remove admin"), "adq", "rmadmin")],
            _back(ctx)]
    return Out(head(ctx, "ttl_adm") + "\n".join(lines), rows)


# ---- health ---------------------------------------------------------------------------------------------------------------------------
@action("adh")
async def health(ctx, arg):
    if not await _need(ctx, 20):
        return _deny(ctx)
    db_ok = await ping()
    up = int(time.time() - BOOT) // 60
    users = await col("users").count_documents({})
    chars = await col("characters").count_documents({})
    pend = await col("admin_pending").count_documents({})
    lines = [
        f"🗄 {T(ctx, 'دیتابیس', 'Database')}: {'✅' if db_ok else '❌'}",
        f"⏱ {T(ctx, 'آپتایم', 'Uptime')}: {up // 60}h {up % 60}m",
        f"👥 {T(ctx, 'کاربران', 'Users')}: {fnum(users, ctx.lang)} · 🧙 {fnum(chars, ctx.lang)}",
        f"⏳ {T(ctx, 'ورودی‌های باز ادمین', 'Open admin inputs')}: {pend}",
    ]
    return Out(head(ctx, "ttl_adm") + "\n".join(lines), [_back(ctx)])


# ---- typed answers to ASK buttons (routed here by handlers_core) ------------------------------------------------------------------
@input_handler("ad_act")
async def act_input(ctx, text):
    pend = await _pending_get(ctx.uid)
    await _pending_clear(ctx.uid)
    if not pend:
        return Out(T(ctx, "⌛ زمانش تمام شد؛ دوباره از پنل شروع کن.", "⌛ Timed out; start again from the panel."),
                   [_back(ctx)])
    raw = (text or "").strip()
    if raw.lower() in ("لغو", "cancel"):
        return Out(T(ctx, "لغو شد.", "Cancelled."), [_back(ctx)])
    name = pend.get("action")
    spec = ASK.get(name)
    if spec is None or not await _need(ctx, spec[0]):
        return Out(T(ctx, "اجازه نداری.", "No permission."), [_back(ctx)])
    try:
        return await _run_input(ctx, name, pend, raw)
    except ValueError:
        return Out(T(ctx, "❌ ورودی نامعتبر است. دوباره از پنل امتحان کن.",
                     "❌ Invalid input. Try again from the panel."), [_back(ctx)])


async def _target_or_none(raw: str, lvl: int, check_level: bool, reply_id=None, single_arg: bool = False):
    """(tid, rest, user doc) or (None, '', None) when the target is unknown or protected."""
    tid, rest = split_target(raw, reply_id, single_arg)
    if tid is None:
        raise ValueError(raw)
    u = await col("users").find_one({"telegram_id": tid})
    if not u:
        return tid, rest, None
    if tid == settings.owner_id or (check_level and await admin_level(tid) >= lvl):
        return tid, rest, "protected"
    return tid, rest, u


async def _run_input(ctx, name, pend, raw):
    lvl = await admin_level(ctx.uid)

    if name == "find":
        tid = await _resolve_user(raw)
        if tid is None:
            tid = _reply_target(ctx)
        if tid is None:
            return Out(T(ctx, "پیدا نشد.", "Not found."), [_back(ctx, "adu", "")])
        return await user_card(ctx, tid)

    if name in ("ban", "unban", "warn", "give_coins", "take_coins", "give_xp", "give_cores", "take_cores",
                "give_item", "take_item"):
        tid, rest, u = await _target_or_none(
            raw, lvl, check_level=name in ("ban", "warn"), reply_id=_reply_target(ctx), single_arg=name in ONE_NUMBER)
        if u is None:
            return Out(T(ctx, "کاربر پیدا نشد.", "User not found."), [_back(ctx, "adu", "")])
        if u == "protected":
            return Out(T(ctx, "اجازه نداری.", "Not allowed."), [_back(ctx)])
    else:
        tid = rest = u = None

    if name == "ban":
        await col("users").update_one({"telegram_id": tid}, {"$set": {"banned": True, "ban_reason": rest[:100]}})
        await alog(ctx.uid, "ban", tid, {"banned": bool(u.get("banned"))}, {"banned": True}, rest)
        return await user_card(ctx, tid)
    if name == "unban":
        await col("users").update_one({"telegram_id": tid}, {"$set": {"banned": False}})
        await alog(ctx.uid, "unban", tid, {"banned": bool(u.get("banned"))}, {"banned": False}, "panel")
        return await user_card(ctx, tid)
    if name == "warn":
        await col("users").update_one({"telegram_id": tid}, {"$inc": {"warns": 1}})
        await alog(ctx.uid, "warn", tid, None, None, rest)
        return await user_card(ctx, tid)

    if name in ("give_coins", "take_coins"):
        n = parse_amount(rest, 1, 10 ** 9)
        if n is None:
            raise ValueError(raw)
        sign = 1 if name == "give_coins" else -1
        if not await add_coins(tid, sign * n, "admin"):
            return Out(T(ctx, "❌ موجودی کافی نیست.", "❌ Not enough balance."), [_back(ctx, "ade", "")])
        await alog(ctx.uid, name, tid, None, {"delta": sign * n}, "panel")
        return await user_card(ctx, tid)
    if name == "give_xp":
        n = parse_amount(rest, 1, 10 ** 9)
        if n is None:
            raise ValueError(raw)
        await add_xp(tid, n, "admin", apply_rate=False)
        await alog(ctx.uid, "give_xp", tid, None, {"delta": n}, "panel")
        return await user_card(ctx, tid)
    if name in ("give_cores", "take_cores"):
        n = parse_amount(rest, 1, 10_000)
        if n is None:
            raise ValueError(raw)
        if name == "give_cores":
            await grant_cores(tid, n, f"admin:{ctx.uid}")
        elif not await spend_cores(tid, n, f"admin_take:{ctx.uid}"):
            return Out(T(ctx, "❌ هسته‌ی کافی نیست.", "❌ Not enough cores."), [_back(ctx, "ade", "")])
        await alog(ctx.uid, name, tid, None, {"delta": n if name == "give_cores" else -n}, "panel")
        return await user_card(ctx, tid)
    if name in ("give_item", "take_item"):
        parts = rest.split()
        if not parts or parts[0] not in ALL:
            raise ValueError(raw)
        iid = parts[0]
        n = parse_amount(parts[1], 1, 999) if len(parts) > 1 else 1
        if n is None:
            raise ValueError(raw)
        if name == "give_item":
            from service_raceweapon import ADMIN_GIVE_MSG, admin_give
            res = await admin_give(tid, iid, n)
            if res not in ("ok", "equipped"):
                fa_m, en_m = ADMIN_GIVE_MSG[res]
                return Out(T(ctx, fa_m, en_m), [_back(ctx, "ade", "")])
        elif not await inv_remove(tid, iid, n):
            return Out(T(ctx, "❌ آیتم کافی نیست.", "❌ Not enough items."), [_back(ctx, "ade", "")])
        await alog(ctx.uid, name, tid, None, {"item": iid, "n": n}, "panel")
        return await user_card(ctx, tid)

    if name == "reset":
        tid, _ = split_target(raw, _reply_target(ctx))
        if tid is None or tid == settings.owner_id or await admin_level(tid) >= lvl:
            raise ValueError(raw)
        text = head(ctx, "ttl_adm") + T(
            ctx,
            f"⚠️ ریست کامل پلیر <code>{tid}</code>: کاراکتر، ایتم‌ها، کوئست‌ها و گاچا پاک می‌شوند. مطمئنی؟",
            f"⚠️ Full reset of <code>{tid}</code>: character, items, quests and gacha are deleted. Sure?")
        return Out(text, [[(T(ctx, "⚠️ بله، ریست کن", "⚠️ Yes, reset"), "adx", f"rk:{tid}")],
                          _back(ctx, "admo", "")])

    if name == "addadmin":
        tid, rest = split_target(raw, _reply_target(ctx))
        if tid is None or tid == settings.owner_id:
            raise ValueError(raw)
        role = role_ok(rest.split()[0] if rest else "", ROLE_CHOICES)
        await col("admin_users").update_one({"user_id": tid}, {"$set": {"role": role}}, upsert=True)
        from handlers_admin import forget_admin
        forget_admin(tid)
        try:
            await refresh_admin_commands(ctx.bot, tid, True)
        except Exception:
            log.exception("admin command menu refresh failed")
        await alog(ctx.uid, "addadmin", tid, None, role, "panel")
        return Out(T(ctx, "✅ ادمین ثبت شد.", "✅ Admin added."), [_back(ctx, "ada", "")])
    if name == "rmadmin":
        tid, _ = split_target(raw, _reply_target(ctx))
        if tid is None or tid == settings.owner_id:
            raise ValueError(raw)
        await col("admin_users").delete_one({"user_id": tid})
        from handlers_admin import forget_admin
        forget_admin(tid)
        try:
            await refresh_admin_commands(ctx.bot, tid, False)
        except Exception:
            log.exception("admin command menu refresh failed")
        await alog(ctx.uid, "rmadmin", tid, None, None, "panel")
        return Out(T(ctx, "✅ ادمین برداشته شد.", "✅ Admin removed."), [_back(ctx, "ada", "")])

    if name == "bcast":
        if len(raw) < 2:
            raise ValueError(raw)
        await _pending_set(ctx.uid, "bcast_ready", extra=raw[:3500])
        return Out(head(ctx, "ttl_adm") + T(ctx, "پیش‌نمایش:\n", "Preview:\n") + esc(raw[:300]) + "\n\n"
                   + T(ctx, "گیرنده را انتخاب کن:", "Pick the audience:"),
                   [[(T(ctx, "همه", "All"), "adcs", "all"), (T(ctx, "فارسی", "Persian"), "adcs", "fa"),
                     (T(ctx, "انگلیسی", "English"), "adcs", "en")],
                    _back(ctx, "adc", "")])

    if name == "worldset":
        bits = raw.split()
        if len(bits) < 2 or bits[0].lower() not in ("threat", "stability"):
            raise ValueError(raw)
        float(bits[1])  # raises ValueError for a non-number; admin_world re-checks the range
        res = await admin_world(ctx, ["set", bits[0].lower(), bits[1]], lvl)
        return Out(head(ctx, "ttl_adm") + (res or ""), [_back(ctx, "adw", "")])

    if name == "setkey":
        key = pend.get("target")
        if key not in GAME_DEFAULTS:
            raise ValueError(raw)
        old = (await game_settings())[key]
        new = coerce_setting(GAME_DEFAULTS[key], raw)
        if not isinstance(new, bool) and new < 0:
            raise ValueError(raw)
        await set_game_setting(key, new)
        await alog(ctx.uid, "set", key, old, new, "panel")
        return Out(head(ctx, "ttl_adm") + f"✅ {key} = {new}", [_back(ctx, "ads", "0")])

    from handlers_adminplus import run_input as _plus_input  # picker steps (item / summon): own module
    res = await _plus_input(ctx, name, pend, raw)
    if res is not None:
        return res
    raise ValueError(raw)


# alias kept for handlers_admincmd (its gift panel renders the same user card)
_user_card = user_card
