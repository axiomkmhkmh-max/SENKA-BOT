"""Gotei wheels (گردونه‌ها): category list (`whl`), one wheel page (`whw`), odds (`whx`), spin (`whs`).

Rules live in data_wheels (pure) and service_wheels (DB). This module only draws.
The prize is decided by service_wheels BEFORE the animation starts, so a failed frame edit
(flood limit, deleted message) never changes or repeats a result.
"""
import asyncio
import logging
import random

from aiogram.exceptions import TelegramBadRequest

from config import settings
from data_wheels import CATEGORIES, RARITY_ICON, can_spin, odds_table, wheel_by_id, wheels_in
from fmt import nm
from i18n import esc, fnum
from service_wheels import spin, wallet, wheel_info
from ui import SEP, Out, action, nav

log = logging.getLogger("senka.wheel")

FRAME_DELAYS = (0.35, 0.4, 0.5, 0.65)  # pause after each animation frame; the wheel slows down
ICONS = list(RARITY_ICON.values())


def T(ctx, fa, en):
    return fa if ctx.lang == "fa" else en


def _title(sub: str = "") -> str:
    return f"⚔️ <b>𝖲𝖤𝖭𝖪𝖠</b> | <b>گردونه‌ها / Wheels</b>\n{SEP}\n" + (f"{sub}\n" if sub else "")


def _pairs(items: list) -> list:
    return [items[i:i + 2] for i in range(0, len(items), 2)]


def _locked(ctx, wid: str) -> bool:
    return not can_spin(wid, ctx.uid, settings.owner_id)


def _name(ctx, w: dict) -> str:
    return w["fa"] if ctx.lang == "fa" else w["en"]


def _cat_name(ctx, cat: str) -> str:
    fa, en, _ = CATEGORIES[cat]
    return fa if ctx.lang == "fa" else en


# ---------------------------------------------------------------------------------------------
@action("whl")
async def wheels_home(ctx, arg):
    w = await wallet(ctx.uid)
    body = T(ctx,
             "هر گردونه با «هسته‌ی روح» 🔮 می‌چرخد.\nهرچه یک گردونه را بیشتر بچرخانی، گرانتر می‌شود.\n"
             "ضمانت دارد: جایزه‌ی بزرگ دیرتر ولی حتماً می‌آید.\n\n"
             "🔮 هسته‌ی روح فقط از سخت‌ترین کوئست‌ها (افسانه‌ای، بانکای، سطح ۳۰) و دانجن‌های "
             "«ورطه» و «افسانه‌ای» به‌دست می‌آید، و شانسش کم است.",
             "Each wheel spins for Soul Cores 🔮.\nThe more you spin one wheel, the pricier it gets.\n"
             "Pity guarantees a big prize eventually.\n\n"
             "🔮 Soul Cores drop only from the hardest quests (Legend, Bankai, level 30) and "
             "the Abyss and Legendary dungeon difficulties, and the chance is low.")
    body += f"\n\n🔮 {T(ctx, 'هسته‌ی روح', 'Soul Cores')}: <b>{fnum(w['cores'], ctx.lang)}</b>"
    rows = [[(_cat_name(ctx, c), "whc", c) for c in pair] for pair in _pairs(list(CATEGORIES))]
    rows.append(nav(ctx, ("mg", "fun")))
    return Out(_title() + body, rows)


@action("whc")
async def wheels_category(ctx, arg):
    if arg not in CATEGORIES:
        return Out(alert=T(ctx, "⚠️ دسته پیدا نشد.", "⚠️ Category not found."))
    rows = []
    for pair in _pairs(wheels_in(arg)):
        line = []
        for wid in pair:
            w = wheel_by_id(wid)
            lock = " 🔒" if _locked(ctx, wid) else ""
            line.append((f"{w['icon']} {_name(ctx, w)} · {w['base_cost']}🔮{lock}", "whw", wid))
        rows.append(line)
    rows.append(nav(ctx, ("whl", "")))
    return Out(_title(_cat_name(ctx, arg)) + T(ctx, "یک گردونه را انتخاب کن:", "Pick a wheel:"), rows)


@action("whw")
async def wheel_page(ctx, arg):
    w = wheel_by_id(arg)
    if w is None:
        return Out(alert=T(ctx, "⚠️ گردونه پیدا نشد.", "⚠️ Wheel not found."))
    info = await wheel_info(ctx.uid, arg)
    L = ctx.lang
    locked = _locked(ctx, arg)
    lines = [
        f"{w['icon']} <b>{esc(_name(ctx, w))}</b>",
        f"{T(ctx, 'دسته', 'Category')}: {_cat_name(ctx, w['cat'])}",
        "",
        f"🔮 {T(ctx, 'هسته‌ی روح تو', 'Your Soul Cores')}: <b>{fnum(info['cores'], L)}</b>",
        f"🎡 {T(ctx, 'چرخش‌های تو روی این گردونه', 'Your spins on this wheel')}: <b>{fnum(info['done'], L)}</b>",
        f"💸 {T(ctx, 'قیمت چرخش بعدی', 'Next spin costs')}: <b>{fnum(info['next_cost'], L)}</b> 🔮",
        f"🎁 {T(ctx, 'چرخش رایگان امروز', 'Free spin today')}: {'✅' if info['free_left'] else '❌'}",
        "",
        f"🟧 {T(ctx, 'ضمانت Legendary', 'Legendary pity')}: {info['leg']}/{info['leg_at']}",
        f"🟥 {T(ctx, 'ضمانت Mythic', 'Mythic pity')}: {info['myth']}/{info['myth_at']}",
    ]
    if locked:
        lines += ["", "🔒 " + T(ctx, "این گردونه فقط برای مالک ربات است.", "This wheel is for the bot owner only.")]
    rows = []
    if not locked:
        tag = T(ctx, "🎁 رایگان", "🎁 Free") if info["free_left"] else f"{fnum(info['next_cost'], L)} 🔮"
        rows.append([(f"🎡 {T(ctx, 'چرخش', 'Spin')} ({tag})", "whs", arg)])
    rows.append([(T(ctx, "📊 جدول شانس", "📊 Odds"), "whx", arg)])
    rows.append(nav(ctx, ("whc", w["cat"])))
    return Out(_title() + "\n".join(lines), rows)


@action("whx")
async def wheel_odds(ctx, arg):
    w = wheel_by_id(arg)
    if w is None:
        return Out(alert=T(ctx, "⚠️ گردونه پیدا نشد.", "⚠️ Wheel not found."))
    info = await wheel_info(ctx.uid, arg)
    lines = [f"{RARITY_ICON[r]} {r}: {p:.2f}%" for r, p in odds_table()]
    lines += [
        "",
        T(ctx, f"ضمانت: بعد از {info['leg_at']} چرخش بدون Legendary، یکی حتماً می‌آید؛ "
               f"بعد از {info['myth_at']} چرخش بدون Mythic، حتماً Mythic یا بالاتر.",
          f"Pity: after {info['leg_at']} spins with no Legendary, one is guaranteed; "
          f"after {info['myth_at']} with no Mythic, a Mythic or better is guaranteed."),
        T(ctx, "قیمت هر چرخش: ۱۰ اول ×۱، ۳۰ بعدی ×۲، ۵۰ بعدی ×۴، بقیه ×۸.",
          "Price per spin: first 10 ×1, next 30 ×2, next 50 ×4, after that ×8."),
    ]
    return Out(_title(f"{w['icon']} {_name(ctx, w)}") + "\n".join(lines), [nav(ctx, ("whw", arg))])


# ---------------------------------------------------------------------------------------------
async def _show(ctx, text: str) -> bool:
    try:
        await ctx.message.edit_text(text, reply_markup=None)
        return True
    except TelegramBadRequest as e:
        if "not modified" not in str(e):
            log.warning("wheel frame failed: %s", e)
        return False
    except Exception:
        log.exception("wheel frame crashed")
        return False


def _reward_lines(ctx, res: dict) -> str:
    L = ctx.lang
    out = []
    if res["coins"]:
        out.append(f"🪙 +{fnum(res['coins'], L)}")
    if res["xp"]:
        out.append(f"✨ +{fnum(res['xp'], L)} XP")
    if res["cores_won"]:
        out.append(f"🔮 +{res['cores_won']} {T(ctx, 'هسته‌ی روح', 'Soul Core')}")
    if res["item"]:
        out.append(f"🎁 {esc(str(nm(res['item'], L)))}")
    return "\n".join(out)


@action("whs")
async def wheel_spin_cb(ctx, arg):
    status, res = await spin(ctx.uid, arg, settings.owner_id)
    if status != "ok":
        msgs = {
            "off": T(ctx, "⏸ گردونه‌ها موقتاً خاموش‌اند.", "⏸ Wheels are temporarily off."),
            "bad": T(ctx, "⚠️ گردونه پیدا نشد.", "⚠️ Wheel not found."),
            "locked": T(ctx, "🔒 این گردونه فقط برای مالک است.", "🔒 This wheel is owner-only."),
            "wait": T(ctx, "⏳ یک لحظه صبر کن.", "⏳ One moment."),
            "funds": T(ctx, "🔮 هسته‌ی روح کافی نداری.", "🔮 Not enough Soul Cores."),
        }
        return Out(alert=msgs.get(status, T(ctx, "⚠️ نشد. دوباره تلاش کن.", "⚠️ Failed. Try again.")))

    # the result is already paid and granted: from here on it is only drawing
    w = wheel_by_id(arg)
    if ctx.cb is not None and ctx.message is not None:
        try:
            await ctx.cb.answer()
        except Exception:
            pass
        head = f"⚔️ <b>𝖲𝖤𝖭𝖪𝖠</b> | <b>{esc(_name(ctx, w))}</b>\n{SEP}\n"
        for delay in FRAME_DELAYS:
            frame = " ".join(random.choice(ICONS) for _ in range(5))
            if not await _show(ctx, head + T(ctx, "🎡 در حال چرخش...", "🎡 Spinning...") + f"\n\n{frame}"):
                break
            await asyncio.sleep(delay)

    L = ctx.lang
    paid = (T(ctx, "🎁 چرخش رایگان امروز", "🎁 Free daily spin") if res["free"]
            else f"🔮 -{fnum(res['cost'], L)}")
    name = esc(res["fa"] if L == "fa" else res["en"])
    big = res["rarity"] in ("Legendary", "Mythic", "Legacy")
    text = (_title()
            + f"{w['icon']} <b>{esc(_name(ctx, w))}</b> · #{fnum(res['n'], L)}\n{paid}\n{SEP}\n"
            + f"{res['rarity_icon']} <b>{res['rarity']}</b>\n{res['icon']} <b>{name}</b>\n"
            + (_reward_lines(ctx, res) or "—")
            + (f"\n\n✨ {T(ctx, 'جایزه‌ی بزرگ!', 'Big win!')}" if big else "")
            + f"\n\n🔮 {T(ctx, 'هسته‌ی روح باقی‌مانده', 'Soul Cores left')}: <b>{fnum(res['cores_left'], L)}</b>")
    rows = []
    if can_spin(arg, ctx.uid, settings.owner_id):
        rows.append([(f"🎡 {T(ctx, 'دوباره', 'Again')}", "whs", arg)])
    rows.append(nav(ctx, ("whw", arg)))
    return Out(text, rows)
