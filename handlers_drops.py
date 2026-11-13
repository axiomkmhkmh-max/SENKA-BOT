"""Panels for Soul Artifacts / Artifact Exchange and the group side of drops (claim word, auto-drop, admin drop)."""
import logging
import math
import re
import time

from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError

from data_artifacts import ART_BY_ID, art_bonus_text, art_name
from data_items import ALL
from database import col, game_settings
from fmt import nm, rarity_name
from i18n import esc, fnum, t
from render import both
from security import allow, normalize_text
from service_drops import (CLAIM_WORDS, art_cancel, art_doc, art_buy, art_list, art_listings_page, art_registry, art_release, art_settle,
                           drop_abort, drop_attach, drop_claim, drop_create, drop_roll, player_drop_create, set_group_drops,
                           typing_abort, typing_attach, typing_claim, typing_roll)
from service_log import log_event
from service_player import get_char
from service_world import group_doc
from ui import SEP, Out, action, chunk, head, input_handler, nav

log = logging.getLogger("senka.drops")
PER = 5
PRICES = (10_000, 25_000, 50_000, 100_000, 250_000, 500_000, 1_000_000, 2_500_000)


# ===================================================================================================
# Artifact panels (private chat)
# ===================================================================================================
def _lore(a: dict, L: str) -> str:
    return esc(a["lore_fa" if L == "fa" else "lore_en"])


def _hours_left(end_at: int) -> int:
    return max(0, math.ceil((end_at - time.time()) / 3600))


@action("art")
async def art_panel(ctx, arg):
    L = ctx.lang
    st = await game_settings()
    ch = await get_char(ctx.uid)
    aid = ch.get("artifact")
    rows = []
    if aid:
        a, d = ART_BY_ID[aid], await art_doc(aid)
        body = ctx.t("art_body", name=art_name(aid, L), lore=_lore(a, L), bonus=art_bonus_text(aid, float(st["art_k"])), n=fnum(len(d.get("history") or []), L))
        rows.append([(ctx.t("b_art_sell"), "axl", ""), (ctx.t("b_art_release"), "axr", "")])
    else:
        lst = await col("art_listings").find_one({"seller": ctx.uid, "status": "active"})
        if lst:
            body = ctx.t("art_listed", price=fnum(lst["price"], L), h=fnum(_hours_left(lst["end_at"]), L), name=art_name(lst["art"], L))
            rows.append([(ctx.t("b_cancel"), "axc", lst["_id"])])
        else:
            body = ctx.t("art_none")
    rows.append([(ctx.t("b_art_reg"), "arr", ""), (ctx.t("b_art_mkt"), "axm", "0")])
    rows.append(nav(ctx))
    return Out(head(ctx, "ttl_art") + body, rows)


@action("arr")
async def art_registry_panel(ctx, arg):
    L = ctx.lang
    st = await game_settings()
    lines = [ctx.t("arr_body")]
    for a, state, owner in await art_registry():
        who = ctx.t("arr_owner", name=esc(owner["name"]), lvl=fnum(owner["level"], L)) if owner else ctx.t("arr_free")
        if state == "dropped":
            who = ctx.t("arr_dropped")
        elif state == "listed":
            who += " · " + ctx.t("arr_listed")
        lines.append(f"{art_name(a['_id'], L)}  {art_bonus_text(a['_id'], float(st['art_k']))}\n   {who}")
    return Out(head(ctx, "ttl_arr") + "\n".join(lines), [[(ctx.t("b_art_mkt"), "axm", "0")], nav(ctx, ("art", ""))])


@action("axm")
async def exchange(ctx, arg):
    L = ctx.lang
    st = await game_settings()
    await art_settle()
    page = int(arg) if arg.isdigit() else 0
    docs, total = await art_listings_page(page, PER)
    rows = [[(f"{art_name(d['art'], L)} — {fnum(d['price'], L)}🪙", "axv", d["_id"])] for d in docs]
    pages = max(1, math.ceil(total / PER))
    pg = []
    if page > 0:
        pg.append(("◀️", "axm", str(page - 1), False, "none"))
    if page < pages - 1:
        pg.append(("▶️", "axm", str(page + 1), False, "none"))
    if pg:
        rows.append(pg)
    rows.append(nav(ctx, ("art", "")))
    body = ctx.t("axm_body", fee=fnum(round(float(st["art_fee"]) * 100), L))
    body += "\n\n" + (ctx.t("ax_page", p=fnum(page + 1, L), n=fnum(pages, L)) if docs else ctx.t("axm_empty"))
    return Out(head(ctx, "ttl_axm") + body, rows)


@action("axv")
async def exchange_view(ctx, arg):
    L = ctx.lang
    st = await game_settings()
    d = await col("art_listings").find_one({"_id": arg, "status": "active"})
    if not d or d["end_at"] <= time.time():
        return Out(alert=ctx.t("art_e_gone"))
    a = ART_BY_ID[d["art"]]
    seller = await get_char(d["seller"])
    body = ctx.t("axv_body", name=art_name(d["art"], L), lore=_lore(a, L), bonus=art_bonus_text(d["art"], float(st["art_k"])),
                 price=fnum(d["price"], L), seller=esc((seller or {}).get("name", "?")), h=fnum(_hours_left(d["end_at"]), L))
    act = [(ctx.t("b_abuy"), "axy", arg)] if d["seller"] != ctx.uid else [(ctx.t("b_cancel"), "axc", arg)]
    return Out(head(ctx, "ttl_axm") + body, [act, nav(ctx, ("axm", "0"))])


@action("axy")
async def exchange_buy(ctx, arg):
    r, _ = await art_buy(ctx.uid, arg)
    if r != "ok":
        return Out(alert=ctx.t("art_e_" + r))
    out = await art_panel(ctx, "")
    out.alert = ctx.t("art_bought")
    return out


@action("axc")
async def exchange_cancel(ctx, arg):
    r = await art_cancel(ctx.uid, arg)
    if r != "ok":
        return Out(alert=ctx.t("art_e_gone"))
    out = await art_panel(ctx, "")
    out.alert = ctx.t("art_cancel_ok")
    return out


@action("axl")
async def sell_prices(ctx, arg):
    L = ctx.lang
    st = await game_settings()
    ch = await get_char(ctx.uid)
    if not ch.get("artifact"):
        return Out(alert=ctx.t("art_e_none"))
    prices = [p for p in PRICES if int(st["art_price_min"]) <= p <= int(st["art_price_max"])]
    rows = chunk([(f"{fnum(p, L)} 🪙", "axp", str(p)) for p in prices], 2)
    rows.append([(ctx.t("b_art_custom"), "axi", "")])
    rows.append(nav(ctx, ("art", "")))
    return Out(head(ctx, "ttl_art") + ctx.t("art_price_ask", fee=fnum(round(float(st["art_fee"]) * 100), L)), rows)


@action("axp")
async def sell_do(ctx, arg):
    if not arg.isdigit():
        return Out()
    r, _ = await art_list(ctx.uid, int(arg))
    if r != "ok":
        return Out(alert=ctx.t("art_e_" + r))
    out = await art_panel(ctx, "")
    out.alert = ctx.t("art_listed_ok")
    return out


@action("axi")
async def sell_custom(ctx, arg):
    st = await game_settings()
    await col("inputs").update_one({"user_id": ctx.uid}, {"$set": {"kind": "art_price", "at": int(time.time())}}, upsert=True)
    return Out(head(ctx, "ttl_art") + ctx.t("art_custom_ask", lo=fnum(st["art_price_min"], ctx.lang), hi=fnum(st["art_price_max"], ctx.lang)), [nav(ctx, ("art", ""))])


@input_handler("art_price")
async def sell_custom_input(ctx, text):
    digits = re.sub(r"\D", "", normalize_text(text))
    if not digits or len(digits) > 12:
        return Out(ctx.t("art_e_price"), [nav(ctx, ("art", ""))])
    r, _ = await art_list(ctx.uid, int(digits))
    if r != "ok":
        return Out(ctx.t("art_e_" + r), [nav(ctx, ("art", ""))])
    return await art_panel(ctx, "")


@action("axr")
async def release_ask(ctx, arg):
    ch = await get_char(ctx.uid)
    if not ch.get("artifact"):
        return Out(alert=ctx.t("art_e_none"))
    return Out(head(ctx, "ttl_art") + ctx.t("art_release_ask"), [[(ctx.t("b_yes"), "axk", "")], nav(ctx, ("art", ""))])


@action("axk")
async def release_do(ctx, arg):
    r = await art_release(ctx.uid)
    if r != "ok":
        return Out(alert=ctx.t("art_e_" + ("none" if r == "none" else "busy")))
    out = await art_panel(ctx, "")
    out.alert = ctx.t("art_released")
    return out


# ===================================================================================================
# Group side: the drop message, claiming, auto drops
# ===================================================================================================
def _prize(L: str, doc: dict) -> str:
    return art_name(doc["ref"], L) if doc["kind"] == "art" else nm(doc["ref"], L)


def _top(L: str, doc: dict) -> str:
    art = doc["kind"] == "art"
    parts = [t(L, "dr_head_art" if art else "dr_head_item")]
    if art:
        a = ART_BY_ID[doc["ref"]]
        parts.append(t(L, "dr_art", name=art_name(doc["ref"], L), bonus=art_bonus_text(doc["ref"]), lore=_lore(a, L)))
    else:
        parts.append(t(L, "dr_item", name=nm(doc["ref"], L), rar=rarity_name(ALL[doc["ref"]]["rarity"], L)))
    who = esc(doc["dropper_name"]) if doc.get("dropper") and doc.get("dropper_name") else t(L, "dr_gate")
    parts.append(t(L, "dr_by", name=who))
    return "\n".join(parts)


def drop_text(L: str, doc: dict) -> str:
    return _top(L, doc) + f"\n{SEP}\n" + t(L, "dr_how", s=fnum(doc["end_at"] - doc["created_at"], L))


def claimed_text(L: str, doc: dict) -> str:
    key = "dr_claimed_art" if doc["kind"] == "art" else "dr_claimed"
    return _top(L, doc) + f"\n{SEP}\n" + t(L, key, who=esc(doc.get("claimer_name", "?")), name=_prize(L, doc))


def expired_text(L: str, doc: dict) -> str:
    return _top(L, doc) + f"\n{SEP}\n" + t(L, "dr_expired", name=_prize(L, doc))


async def _lang(chat_id: int) -> str:
    from render import glang
    return glang(await group_doc(chat_id))


async def send_drop(bot, chat_id: int, doc: dict):
    """Post the drop message. On failure the prize is handed back."""
    lang = await _lang(chat_id)
    try:
        msg = await bot.send_message(chat_id, both(lang, lambda L: drop_text(L, doc)))
    except TelegramForbiddenError:
        await col("groups").update_one({"chat_id": chat_id}, {"$set": {"blocked": True}})
        await drop_abort(doc)
        return None
    except TelegramAPIError:
        log.warning("drop send failed in %s", chat_id)
        await drop_abort(doc)
        return None
    await drop_attach(doc["_id"], msg.message_id)
    g = await col("groups").find_one({"chat_id": chat_id}, {"title": 1}) or {}
    what = art_name(doc["ref"], "fa") if doc["kind"] == "art" else nm(doc["ref"], "fa").replace("<", "").replace(">", "")
    log_event("drop", doc.get("dropper", 0), f"دراپ «{what}» در گروه «{g.get('title', chat_id)}»" + (" 🔱 (آرتیفکت یکتا)" if doc["kind"] == "art" else ""),
              chat=chat_id, kind=doc["kind"], ref=doc["ref"])
    return msg


async def _edit(bot, doc: dict, text_fn):
    if not doc.get("msg_id"):
        return
    lang = await _lang(doc["chat_id"])
    try:
        await bot.edit_message_text(both(lang, text_fn), chat_id=doc["chat_id"], message_id=doc["msg_id"])
    except TelegramAPIError:
        pass


async def announce_expired(bot, doc: dict):
    await _edit(bot, doc, lambda L: expired_text(L, doc))


async def _is_chat_admin(message) -> bool:
    try:
        m = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
        return m.status in ("creator", "administrator")
    except TelegramAPIError:
        return False


async def group_hook(message, text: str, n: str) -> bool:
    """Runs on every group text. True = the message was a drop word and has been handled."""
    user, chat = message.from_user, message.chat
    if await _typing_hook(message, text):  # --- NEW BLEACH VIRAL SYSTEM: typing race
        return True
    # ---- claiming: reply to the drop message with «بردار» ----
    if n in CLAIM_WORDS:
        if message.reply_to_message is None:
            return False
        if not allow(user.id, "dropclaim", 0.8):
            return True
        res, doc = await drop_claim(chat.id, user.id, message.reply_to_message.message_id)
        if res == "nodrop":
            return False
        lang = await _lang(chat.id)
        st = await game_settings()
        if res == "ok":
            await _edit(message.bot, doc, lambda L: claimed_text(L, doc))
            await message.reply(both(lang, lambda L: claimed_text(L, doc)))
            what = _prize("fa", doc).replace("<", "").replace(">", "")
            log_event("drop", user.id, f"برنده‌ی دراپ شد: «{what}»" + (" 🔱" if doc["kind"] == "art" else ""), chat=chat.id, kind=doc["kind"], ref=doc["ref"])
            return True
        if res == "gone":
            end = doc.get("claimed_at") or doc.get("end_at") or 0
            if doc["status"] in ("claimed", "claiming", "expired") and time.time() - end < 60:
                await message.reply(both(lang, lambda L: t(L, "dr_e_gone")))
            return True
        extra = {"n": st["drop_min_level"] if res == "level" else st["drop_daily_per_user"] if res == "cap" else st["drop_pair_daily"]}
        await message.reply(both(lang, lambda L: t(L, "dr_e_" + res, n=fnum(extra["n"], L))))
        return True
    # ---- group admin switches ----
    if n in ("دراپ خاموش", "drops off", "drop off", "دراپ روشن", "drops on", "drop on"):
        if await _is_chat_admin(message):
            on = n in ("دراپ روشن", "drops on", "drop on")
            await set_group_drops(chat.id, on)
            await message.reply(t("fa", "dr_on" if on else "dr_off") + "\n" + t("en", "dr_on" if on else "dr_off"))
        return True
    # ---- bot admin: manual drop (item / artifact) ----
    if n in ("دراپ", "drop", "دراپ آرتیفکت", "drop artifact", "drop art"):
        from handlers_admin import admin_level
        if await admin_level(user.id) < 60:
            return False
        kind = "art" if "art" in n or "آرتیفکت" in n else None
        doc = await drop_create(chat.id, user.id, user.full_name or user.first_name or "admin", kind)
        if not doc:
            await message.reply(t("fa", "dr_nothing"))
            return True
        await send_drop(message.bot, chat.id, doc)
        return True
    # ---- a player throws one of their own items into the group: «دراپ <نام آیتم>» ----
    head_w, _, rest = n.partition(" ")
    if head_w in ("دراپ", "drop") and rest and rest not in ("خاموش", "روشن", "off", "on", "آرتیفکت", "artifact", "art"):
        if not allow(user.id, "pdrop", 3):
            return True
        res, doc = await player_drop_create(user.id, chat.id, rest, user.full_name or user.first_name or "player")
        lang = await _lang(chat.id)
        if res != "ok":
            st = await game_settings()
            n_ = {"level": st["drop_player_min_level"], "new": st["drop_player_min_age_hours"], "cap": st["drop_player_daily"],
                  "cd": max(1, int(st["drop_player_cooldown"]) // 60)}.get(res, 0)
            await message.reply(both(lang, lambda L: t(L, "dr_p_e_" + res, n=fnum(n_, L))))
            return True
        if not await send_drop(message.bot, chat.id, doc):
            await message.reply(both(lang, lambda L: t(L, "dr_p_e_fail")))
        return True
    # ---- automatic drops while the group is chatting ----
    if allow(user.id, "dropcnt", 5):
        try:
            if await drop_roll(chat.id, user.id):
                doc = await drop_create(chat.id)
                if doc:
                    await send_drop(message.bot, chat.id, doc)
        except Exception:
            log.exception("auto drop failed")
    return False

# --- NEW BLEACH VIRAL SYSTEM: Gillian / spirit chest typing race ---
_TT = {
    "spawn": ("{icon} <b>{name} ظاهر شد!</b>\nاولین نفری که این ورد را <b>دقیقاً</b> تایپ کند برنده است:\n\n<code>{phrase}</code>\n⏳ {sec} ثانیه",
              "{icon} <b>A {name} appears!</b>\nFirst to type this incantation <b>exactly</b> wins:\n\n<code>{phrase}</code>\n⏳ {sec}s"),
    "won": ("{icon} {who} ورد را درست خواند و برنده شد!\n✨ موج ریاتسو: +{xp} XP و +{coins} سکه", "{icon} {who} spoke the incantation first!\n✨ Reiatsu surge: +{xp} XP and +{coins} coins"),
    "expired": ("{icon} {name} ناپدید شد؛ کسی ورد را نگفت.", "{icon} The {name} vanished — nobody spoke the incantation."),
}
_TN = {"gillian": ("👹", "گلیان", "Gillian"), "chest": ("🧰", "صندوقچه‌ی روحی", "spirit chest")}


def _tt(lang, key, **kw):
    fa, en = _TT[key]
    return (fa if lang == "fa" else en).format(**kw)


async def _typing_hook(message, text: str) -> bool:
    user, chat = message.from_user, message.chat
    res = await typing_claim(chat.id, user.id, text)
    if res:
        doc, name, xp, coins = res
        lang = await _lang(chat.id)
        icon, _fa, _en = _TN[doc["kind"]]
        out = _tt(lang, "won", icon=icon, who=esc(user.full_name or name), xp=fnum(xp, lang), coins=fnum(coins, lang))
        await message.reply(out)
        if doc.get("msg_id"):
            try:
                await message.bot.edit_message_text(out, chat_id=chat.id, message_id=doc["msg_id"])
            except TelegramAPIError:
                pass
        return True
    if allow(user.id, "typecnt", 4):
        try:
            doc = await typing_roll(chat.id)
            if doc:
                lang = await _lang(chat.id)
                icon, fa, en = _TN[doc["kind"]]
                try:
                    msg = await message.bot.send_message(chat.id, _tt(lang, "spawn", icon=icon, name=fa if lang == "fa" else en, phrase=esc(doc["phrase"]),
                                                                      sec=doc["end_at"] - doc["created_at"]))
                except TelegramAPIError:
                    await typing_abort(doc["_id"], chat.id)
                else:
                    await typing_attach(doc["_id"], msg.message_id)
        except Exception:
            log.exception("typing roll failed")
    return False


async def announce_typing_expired(bot, d: dict):
    if not d.get("msg_id"):
        return
    lang = await _lang(d["chat_id"])
    icon, fa, en = _TN[d["kind"]]
    try:
        await bot.edit_message_text(_tt(lang, "expired", icon=icon, name=fa if lang == "fa" else en), chat_id=d["chat_id"], message_id=d["msg_id"])
    except TelegramAPIError:
        pass
