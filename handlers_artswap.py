"""Artifact swap panels (service_artswap): trade your artifact for another player's, one for one.

Callback codes: axs (hub), axsn:<uid> (offer to a player), axsa:<id> (accept), axsd:<id> (decline / cancel).
Typed prompt: axs_who (a player name or id).
"""
import logging
import time

from data_artifacts import ART_BY_ID
from database import col
from i18n import esc
from service_artswap import SWAP_DAILY, SWAP_MIN_LEVEL, SWAP_TTL, accept, decline, get, offer, pending_for
from service_player import get_char, user_lang
from service_trade import find_partner
from ui import Ctx, Out, action, head, input_handler, markup, nav

log = logging.getLogger("senka.artswap")


def T(ctx, fa, en):
    return fa if ctx.lang == "fa" else en


def _name(aid: str, lang: str) -> str:
    a = ART_BY_ID.get(aid) or {}
    return f"{a.get('icon', '')} {a.get('name_fa' if lang == 'fa' else 'name_en', aid)}".strip()


ERR = {
    "self": ("با خودت نمی‌تونی تبادل کنی.", "You cannot swap with yourself."),
    "level": (f"هر دو نفر باید حداقل لول {SWAP_MIN_LEVEL} باشید.", f"Both players need level {SWAP_MIN_LEVEL}+."),
    "none": ("خودت آرتیفکت نداری.", "You do not hold an artifact."),
    "other_none": ("طرف مقابل آرتیفکت ندارد (یا ثبت‌نام نکرده).", "The other player holds no artifact (or is not registered)."),
    "same": ("هر دو یک آرتیفکت دارید؛ تبادل بی‌معنیه.", "You both hold the same artifact."),
    "listed": ("یکی از آرتیفکت‌ها توی بازار آرتیفکت برای فروش گذاشته شده.", "One of the artifacts is listed on the exchange."),
    "busy": ("یکی از شما همین الان یه پیشنهاد تبادل باز داره.", "One of you already has an open swap offer."),
    "limit": (f"سقف روزانه: {SWAP_DAILY} تبادل برای هر پلیر.", f"Daily limit: {SWAP_DAILY} swaps per player."),
    "pair_limit": ("امروز با همین پلیر یک بار تبادل کردید.", "You already swapped with this player today."),
    "unknown": ("پلیری با این اسم یا آیدی پیدا نشد.", "No player with that name or id."),
    "gone": ("این پیشنهاد دیگه فعال نیست.", "This offer is no longer active."),
    "expired": ("زمان پیشنهاد تموم شد.", "This offer has expired."),
    "changed": ("آرتیفکت یکی از شما عوض شده؛ تبادل انجام نشد و چیزی از دست نرفت.", "One artifact changed hands; nothing was swapped and nothing was lost."),
    "busy_now": ("همین الان در حال انجامه.", "It is being processed right now."),
}


def _err(ctx, code):
    fa, en = ERR.get(code, ERR["gone"])
    return T(ctx, fa, en)


@action("axs")
async def swap_hub(ctx, arg):
    ch = await get_char(ctx.uid)
    if not ch:
        return Out(_err(ctx, "other_none"), [nav(ctx)])
    rows = []
    lines = [T(ctx, "🔄 <b>تبادل آرتیفکت</b>\nآرتیفکتت رو یک‌به‌یک با آرتیفکت یه پلیر دیگه عوض کن؛ بدون سکه و بدون بازار. هر دو باید قبول کنید.",
               "🔄 <b>Artifact swap</b>\nTrade your artifact one-for-one with another player's: no coins, no market. Both of you must agree.")]
    if ch.get("artifact"):
        lines.append(T(ctx, f"آرتیفکت تو: {_name(ch['artifact'], 'fa')}", f"Yours: {_name(ch['artifact'], 'en')}"))
        rows.append([(T(ctx, "📨 پیشنهاد تبادل", "📨 Offer a swap"), "axsw", "")])
    else:
        lines.append(T(ctx, "فعلاً آرتیفکت نداری.", "You hold no artifact yet."))
    for d in await pending_for(ctx.uid):
        who = await get_char(d["a"]) or {}
        lines.append(T(ctx, f"\n📩 {esc(who.get('name', '?'))} پیشنهاد میده: {_name(d['art_a'], 'fa')} ⇄ {_name(d['art_b'], 'fa')}",
                       f"\n📩 {esc(who.get('name', '?'))} offers: {_name(d['art_a'], 'en')} ⇄ {_name(d['art_b'], 'en')}"))
        rows.append([(T(ctx, "✅ قبول", "✅ Accept"), "axsa", d["_id"]), (T(ctx, "❌ رد", "❌ Decline"), "axsd", d["_id"])])
    rows.append(nav(ctx, ("art", "")))
    return Out(head(ctx, "ttl_art") + "\n".join(lines), rows)


@action("axsw")
async def swap_ask(ctx, arg):
    if not await get_char(ctx.uid):
        return Out(_err(ctx, "other_none"), [nav(ctx)])
    await col("inputs").update_one({"user_id": ctx.uid}, {"$set": {"kind": "axs_who", "at": int(time.time())}}, upsert=True)
    return Out(head(ctx, "ttl_art") + T(ctx, "اسم پلیر یا آیدی عددیش رو بفرست.\nبرای انصراف بنویس «لغو».",
                                        "Send the player's name or numeric id.\nWrite cancel to stop."), [nav(ctx, ("axs", ""))])


async def _send_offer(ctx, target: int):
    sid, code = await offer(ctx.uid, target)
    if code != "ok":
        return Out(_err(ctx, code), [nav(ctx, ("axs", ""))])
    d, me = await get(sid), await get_char(ctx.uid)
    try:  # the other player gets the offer in private, in their own language
        lang = await user_lang(target)
        c = Ctx(target, lang, target, "private", None, ctx.bot)
        text = T(c, f"📩 <b>{esc(me.get('name', '?'))}</b> می‌خواد آرتیفکتش رو با مال تو عوض کنه:\n{_name(d['art_a'], 'fa')} ⇄ {_name(d['art_b'], 'fa')}\n(تا {SWAP_TTL // 60} دقیقه وقت داری)",
                  f"📩 <b>{esc(me.get('name', '?'))}</b> wants to swap artifacts:\n{_name(d['art_a'], 'en')} ⇄ {_name(d['art_b'], 'en')}\n({SWAP_TTL // 60} minutes to answer)")
        rows = [[(T(c, "✅ قبول", "✅ Accept"), "axsa", sid), (T(c, "❌ رد", "❌ Decline"), "axsd", sid)]]
        await ctx.bot.send_message(target, text, reply_markup=markup(c, rows))
    except Exception:  # blocked the bot / never opened private chat: the offer still shows in their swap hub
        log.info("artswap notify failed for %s", target)
    return Out(T(ctx, "📨 پیشنهاد فرستاده شد. منتظر جواب باش.", "📨 Offer sent. Wait for the answer."),
               [[(T(ctx, "❌ لغو پیشنهاد", "❌ Cancel offer"), "axsd", sid)], nav(ctx, ("axs", ""))])


@input_handler("axs_who")
async def swap_who_input(ctx, text):
    target = await find_partner(text)
    if target is None:
        await col("inputs").update_one({"user_id": ctx.uid}, {"$set": {"kind": "axs_who", "at": int(time.time())}}, upsert=True)
        return Out(_err(ctx, "unknown") + T(ctx, "\nدوباره بفرست یا بنویس «لغو».", "\nSend it again or write cancel."))
    return await _send_offer(ctx, target)


@action("axsa")
async def swap_accept(ctx, sid):
    d = await get(sid)
    code = await accept(sid, ctx.uid)
    if code != "ok":
        return Out(alert=_err(ctx, code))
    try:  # tell the offerer
        c = Ctx(d["a"], await user_lang(d["a"]), d["a"], "private", None, ctx.bot)
        await ctx.bot.send_message(d["a"], T(c, f"🔄 تبادل انجام شد! آرتیفکت جدیدت: {_name(d['art_b'], 'fa')}", f"🔄 Swap done! Your new artifact: {_name(d['art_b'], 'en')}"))
    except Exception:
        pass
    return Out(head(ctx, "ttl_art") + T(ctx, f"🔄 تبادل انجام شد! آرتیفکت جدیدت: {_name(d['art_a'], 'fa')}", f"🔄 Swap done! Your new artifact: {_name(d['art_a'], 'en')}"),
               [[(T(ctx, "آرتیفکت من", "My artifact"), "art", "")], nav(ctx)])


@action("axsd")
async def swap_decline(ctx, sid):
    code = await decline(sid, ctx.uid)
    return Out(T(ctx, "پیشنهاد بسته شد.", "Offer closed.") if code == "ok" else _err(ctx, "gone"), [nav(ctx, ("axs", ""))])
