"""Admin tools: text commands (no slash), dashboard, logs, two-step confirmations."""
import asyncio
import logging
import random
import time

from config import GAME_DEFAULTS, settings
from data_items import ALL
from database import col, game_settings, set_game_setting
from i18n import esc, fnum
from service_economy import inv_add
from service_log import log_event
from service_player import add_coins, add_xp, get_char, today
from ui import Out, action, head, nav

log = logging.getLogger("senka.admin")
CMD = {"stats": "stats", "آمار": "stats", "ban": "ban", "بن": "ban", "unban": "unban", "آنبن": "unban",
       "give": "give", "بده": "give", "take": "take", "بگیر": "take", "broadcast": "broadcast", "پیام همگانی": "broadcast",
       "set": "set", "تنظیم": "set", "addadmin": "addadmin", "rmadmin": "rmadmin", "user": "user", "کاربر": "user",
       "reset": "reset", "ریست": "reset", "confirm": "confirm", "تایید": "confirm", "item": "item", "آیتم": "item",
       "spawn": "spawn", "ظهور": "spawn", "maintenance": "maintenance", "تعمیرات": "maintenance", "mute": "mute", "warn": "warn", "world": "world", "دنیا": "world"}
ROLES = {"owner": 100, "super": 80, "admin": 60, "moderator": 40, "support": 20}
NEED = {"stats": 20, "user": 20, "warn": 40, "mute": 40, "ban": 40, "unban": 40, "give": 60, "take": 60, "item": 60, "set": 80,
        "broadcast": 60, "reset": 80, "confirm": 80, "spawn": 60, "world": 20, "maintenance": 60, "addadmin": 100, "rmadmin": 100}


async def admin_level(uid: int) -> int:
    if uid == settings.owner_id:
        return 100
    d = await col("admin_users").find_one({"user_id": uid})
    return ROLES.get((d or {}).get("role", ""), 0)


async def alog(admin: int, act: str, target=None, before=None, after=None, reason: str = ""):
    await col("admin_logs").insert_one({"admin": admin, "action": act, "target": target, "before": before, "after": after,
                                        "reason": reason[:200], "at": int(time.time())})
    log_event("admin", admin, f"{act} → {target}" + (f" | {before} ⇒ {after}" if before is not None or after is not None else "") + (f" | {reason[:80]}" if reason else ""))


async def dashboard(ctx):
    L = ctx.lang
    now = int(time.time())
    day = now - 86400
    users = await col("users").count_documents({})
    new = await col("users").count_documents({"created_at": {"$gte": day}})
    active = await col("users").count_documents({"last_seen": {"$gte": day}})
    online = await col("users").count_documents({"last_seen": {"$gte": now - 600}})
    chars = await col("characters").count_documents({})
    fights = await col("battle_logs").count_documents({"at": {"$gte": day}})
    kills = await col("boss_sessions").count_documents({"killed": True, "ended_at": {"$gte": day}})
    agg = await col("characters").aggregate([{"$group": {"_id": None, "c": {"$sum": "$coins"}}}]).to_list(1)
    fa = await col("users").count_documents({"lang": "fa"})
    en = await col("users").count_documents({"lang": "en"})
    listings = await col("market_listings").count_documents({"status": "active"})
    return ctx.t("adm_dash", users=fnum(users, L), new=fnum(new, L), active=fnum(active, L), online=fnum(online, L), chars=fnum(chars, L),
                 fights=fnum(fights, L), kills=fnum(kills, L), coins=fnum((agg[0]["c"] if agg else 0), L), fa=fnum(fa, L), en=fnum(en, L),
                 listings=fnum(listings, L))


@action("adm")
async def admin_panel(ctx, arg):
    lvl = await admin_level(ctx.uid)
    if lvl < 20:
        return Out(alert=ctx.t("admin_only"))
    from handlers_adminpanel import main_menu
    return await main_menu(ctx, lvl)


def _int(x, default=None):
    try:
        return int(x)
    except (TypeError, ValueError):
        return default


async def handle_admin_text(ctx, text: str):
    parts = text.strip().split()
    if not parts:
        return None
    word = parts[0].lower()
    cmd = CMD.get(word)
    if not cmd and len(parts) > 1:
        cmd = CMD.get((parts[0] + " " + parts[1]).lower())
        if cmd:
            parts = [parts[0] + " " + parts[1]] + parts[2:]
    if not cmd:
        return None
    lvl = await admin_level(ctx.uid)
    if lvl < NEED.get(cmd, 100):
        return None if lvl < 20 else Out(ctx.t("adm_noperm"))
    args = parts[1:]
    L = ctx.lang
    if cmd == "stats":
        return Out(await dashboard(ctx))
    if cmd in ("ban", "unban", "warn", "mute", "user", "give", "take", "reset", "item") and cmd != "item":
        tid = _int(args[0]) if args else None
        if tid is None:
            return Out(ctx.t("adm_usage_" + cmd))
        if tid == settings.owner_id and cmd != "user":
            return Out(ctx.t("adm_noperm"))
        if cmd in ("ban", "mute", "warn") and await admin_level(tid) >= lvl:
            return Out(ctx.t("adm_noperm"))
        u = await col("users").find_one({"telegram_id": tid})
        if not u:
            return Out(ctx.t("adm_nouser"))
        reason = " ".join(args[1:])
        if cmd == "user":
            ch = await get_char(tid)
            body = f"<code>{tid}</code> @{esc(u.get('username') or '-')} lang={u.get('lang')} banned={bool(u.get('banned'))}"
            if ch:
                body += f"\n{esc(ch['name'])} | {ch['race']} | Lv {ch['level']} | 🪙 {fnum(ch['coins'], L)} | ⭐ {ch['rating']}"
            return Out(body)
        if cmd == "ban":
            await col("users").update_one({"telegram_id": tid}, {"$set": {"banned": True, "ban_reason": reason[:100]}})
            await alog(ctx.uid, "ban", tid, {"banned": bool(u.get("banned"))}, {"banned": True}, reason)
            return Out(ctx.t("adm_done"))
        if cmd == "unban":
            await col("users").update_one({"telegram_id": tid}, {"$set": {"banned": False}})
            await alog(ctx.uid, "unban", tid, {"banned": bool(u.get("banned"))}, {"banned": False})
            return Out(ctx.t("adm_done"))
        if cmd in ("warn", "mute"):
            await col("users").update_one({"telegram_id": tid}, {"$inc": {"warns": 1}})
            await alog(ctx.uid, cmd, tid, None, None, reason)
            return Out(ctx.t("adm_done"))
        if cmd in ("give", "take"):
            kind, amount = (args[1].lower() if len(args) > 1 else ""), _int(args[2] if len(args) > 2 else None)
            if kind == "item":
                iid, n = (args[2] if len(args) > 2 else ""), _int(args[3] if len(args) > 3 else 1, 1)
                if iid not in ALL or not n or n < 1 or n > 999:
                    return Out(ctx.t("adm_usage_give"))
                if cmd == "give":
                    await inv_add(tid, iid, n, force=True)
                else:
                    from service_economy import inv_remove
                    if not await inv_remove(tid, iid, n):
                        return Out(ctx.t("adm_fail"))
                await alog(ctx.uid, f"{cmd}_item", tid, None, {"item": iid, "n": n})
                return Out(ctx.t("adm_done"))
            if kind not in ("coins", "xp") or not amount or amount < 1 or amount > 10 ** 9:
                return Out(ctx.t("adm_usage_give"))
            ch = await get_char(tid)
            if not ch:
                return Out(ctx.t("adm_nouser"))
            if kind == "coins":
                ok = await add_coins(tid, amount if cmd == "give" else -amount, "admin")
                if not ok:
                    return Out(ctx.t("adm_fail"))
            else:
                if cmd == "take":
                    return Out(ctx.t("adm_usage_give"))
                await add_xp(tid, amount, "admin", apply_rate=False)
            await alog(ctx.uid, f"{cmd}_{kind}", tid, {"coins": ch["coins"], "xp": ch["xp"], "level": ch["level"]}, {"delta": amount})
            return Out(ctx.t("adm_done"))
        if cmd == "reset":
            code = str(random.randint(100000, 999999))
            await col("admin_confirms").update_one({"admin": ctx.uid}, {"$set": {"code": code, "target": tid, "at": int(time.time())}}, upsert=True)
            return Out(ctx.t("adm_confirm_ask", code=code, tid=tid))
    if cmd == "confirm":
        d = await col("admin_confirms").find_one_and_delete({"admin": ctx.uid})
        if not d or not args or args[0] != d["code"] or time.time() - d["at"] > 120:
            return Out(ctx.t("adm_fail"))
        tid = d["target"]
        before = await get_char(tid)
        for c in ("characters", "inventories", "player_quests", "gacha", "registration"):
            await col(c).delete_many({"user_id": tid})
        if before and before.get("guild_id"):
            await col("guilds").update_one({"_id": before["guild_id"]}, {"$inc": {"members": -1}})
        await alog(ctx.uid, "reset", tid, {"level": (before or {}).get("level")}, None)
        return Out(ctx.t("adm_done"))
    if cmd == "set":
        if len(args) < 2 or args[0] not in GAME_DEFAULTS:
            return Out(ctx.t("adm_usage_set") + "\n" + ", ".join(GAME_DEFAULTS))
        old = (await game_settings())[args[0]]
        raw = args[1].lower()
        try:
            val = (raw in ("on", "true", "1", "yes")) if isinstance(old, bool) else type(old)(float(raw) if isinstance(old, float) else int(raw))
        except ValueError:
            return Out(ctx.t("adm_fail"))
        await set_game_setting(args[0], val)
        await alog(ctx.uid, "set", args[0], old, val)
        return Out(ctx.t("adm_done"))
    if cmd == "maintenance":
        on = bool(args) and args[0].lower() in ("on", "1", "روشن")
        await set_game_setting("maintenance", on)
        await alog(ctx.uid, "maintenance", None, None, on)
        return Out(ctx.t("adm_done"))
    if cmd == "item":
        if len(args) < 3 or args[0] not in ALL or args[1] not in ("base_price", "sell_price", "attack", "level_req") or _int(args[2]) is None:
            return Out(ctx.t("adm_usage_item"))
        before = ALL[args[0]].get(args[1])
        ALL[args[0]][args[1]] = int(args[2])
        await col("overrides").update_one({"_id": args[0]}, {"$set": {args[1]: int(args[2])}}, upsert=True)
        await alog(ctx.uid, "item", args[0], before, int(args[2]))
        return Out(ctx.t("adm_done"))
    if cmd == "addadmin" or cmd == "rmadmin":
        tid = _int(args[0]) if args else None
        if tid is None:
            return Out(ctx.t("adm_usage_addadmin"))
        if cmd == "addadmin":
            role = args[1] if len(args) > 1 and args[1] in ROLES and args[1] != "owner" else "admin"
            await col("admin_users").update_one({"user_id": tid}, {"$set": {"role": role}}, upsert=True)
        else:
            await col("admin_users").delete_one({"user_id": tid})
        try:
            from handlers_adminpanel import refresh_admin_commands
            await refresh_admin_commands(ctx.bot, tid, cmd == "addadmin")
        except Exception:
            log.exception("admin command menu refresh failed")
        await alog(ctx.uid, cmd, tid)
        return Out(ctx.t("adm_done"))
    if cmd == "broadcast":
        if len(args) < 2 or args[0].lower() not in ("fa", "en", "all"):
            return Out(ctx.t("adm_usage_broadcast"))
        flt = {} if args[0].lower() == "all" else {"lang": args[0].lower()}
        msg = " ".join(args[1:])
        asyncio.create_task(_broadcast(ctx.bot, flt, msg, ctx.uid))
        await alog(ctx.uid, "broadcast", args[0], None, msg[:100])
        return Out(ctx.t("adm_broadcast_started"))
    if cmd == "spawn":
        return Out(ctx.t("adm_spawn_group"))
    if cmd == "world":
        return Out(await admin_world(ctx, args, lvl))
    return None


async def _broadcast(bot, flt, msg, admin):
    ok = fail = 0
    async for u in col("users").find({**flt, "banned": {"$ne": True}}, {"telegram_id": 1}):
        try:
            await bot.send_message(u["telegram_id"], msg)
            ok += 1
        except Exception:
            fail += 1
        await asyncio.sleep(0.06)
    try:
        await bot.send_message(admin, f"📣 ✅ {ok} | ❌ {fail}")
    except Exception:
        pass


async def admin_world(ctx, args, lvl: int) -> str:
    """world | world set threat|stability|reishi <loc> <0-100> | world reset | world event <kind>|end |
    world boss spawn|end | world season end | world territory reset <loc>"""
    from data_races import LOCATIONS
    from data_world import EVENTS, VAR_START
    from service_worldcore import get_world, invalidate, world_set
    from service_worldstate import event_end, event_start, season_force_end
    L = ctx.lang
    ws, ev = await get_world(force=True)
    sub = args[0].lower() if args else ""
    if not sub:
        b = await col("boss_sessions").find_one({"scope": "global", "active": True})
        rei = ", ".join(f"{k}:{v:.0f}" for k, v in sorted((ws.get("reishi") or {}).items()))
        return ctx.t("adm_world", threat=f"{ws.get('threat', 0):.1f}", stab=f"{ws.get('stability', 0):.1f}", rei=rei or "—",
                     ev=(f"{ev['kind']} {ev['progress']}/{ev['goal']}" if ev else "—"), boss=(f"{b['name_en']} {max(0, b['hp'])}/{b['max_hp']}" if b else "—"),
                     season=ws["season"]["id"])
    if lvl < 60:
        return ctx.t("adm_noperm")
    if sub == "set" and len(args) >= 3:
        key = args[1].lower()
        try:
            val = float(args[-1])
        except ValueError:
            return ctx.t("adm_fail")
        if key in ("threat", "stability"):
            await world_set(**{key: val})
        elif key == "reishi" and len(args) == 4 and args[2] in LOCATIONS:
            await world_set(**{f"reishi.{args[2]}": val})
        else:
            return ctx.t("adm_usage_world")
        await alog(ctx.uid, "world_set", key, None, val)
        return ctx.t("adm_done")
    if sub == "reset":
        await col("world_state").update_one({"_id": "main"}, {"$set": {"threat": VAR_START["threat"], "stability": VAR_START["stability"], "reishi": {}}})
        invalidate()
        await alog(ctx.uid, "world_reset")
        return ctx.t("adm_done")
    if sub == "event" and len(args) >= 2:
        if args[1].lower() == "end":
            res = await event_end(force_success=False)
            await alog(ctx.uid, "world_event_end")
            return ctx.t("adm_done" if res else "adm_fail")
        if args[1] in EVENTS:
            res = await event_start(args[1])
            await alog(ctx.uid, "world_event_start", args[1])
            return ctx.t("adm_done" if res else "adm_fail")
    if sub == "boss" and len(args) >= 2:
        if args[1].lower() == "spawn":
            from service_world import spawn_boss
            import handlers_world
            doc = await spawn_boss()
            if doc:
                await handlers_world.post_global_boss(ctx.bot, doc)
            await alog(ctx.uid, "world_boss_spawn")
            return ctx.t("adm_done" if doc else "adm_fail")
        if args[1].lower() == "end":
            await col("boss_sessions").update_many({"scope": "global", "active": True}, {"$set": {"expires_at": 0}})
            await alog(ctx.uid, "world_boss_end")
            return ctx.t("adm_done")
    if sub == "season" and len(args) >= 2 and args[1].lower() == "end":
        await season_force_end()
        await alog(ctx.uid, "world_season_end")
        return ctx.t("adm_done")
    if sub == "territory" and len(args) >= 3 and args[1].lower() == "reset" and args[2] in LOCATIONS:
        await col("territories").delete_one({"_id": args[2]})
        await alog(ctx.uid, "territory_reset", args[2])
        return ctx.t("adm_done")
    return ctx.t("adm_usage_world")
