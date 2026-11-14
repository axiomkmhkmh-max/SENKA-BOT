"""# --- NEW BLEACH VIRAL SYSTEM ---
Plain-word group mechanics (no slash): sword stance words, mask, Bleach status card, Espada 0-9 board and seat challenges,
Hogyoku theft by reply, Quincy invasion strikes. Reply-based words go through `viral_hook` (called from handlers_core.on_group_text);
the other words are ordinary intents (see intents.py) that land in the actions below."""
from aiogram.exceptions import TelegramAPIError

from data_artifacts import HOGYOKU
from data_bleach import DIV_BY_ID
from data_items import iname
from i18n import esc, fnum
from render import glang
from security import allow
from service_bleach_systems import STANCE, STANCE_SECONDS, espada_board, espada_challenge, espada_rank, stance_set
from service_extras import hogyoku_holder, hogyoku_state, hogyoku_steal
from service_hollowraid import bankai_lock_left, quincy_strike, raid_settle
from service_world import group_doc
from ui import SEP, Out, action, nav
from database import try_cooldown
from handlers_zanpakuto import _chant, _state
import handlers_world

DUEL_WORDS = {"مبارزه", "دوئل", "fight", "duel"}
STEAL_WORDS = {"دزدی", "خیانت", "steal", "betray"}
STRIKE_WORDS = {"حمله", "ضربه", "attack", "strike"}

T = {  # key -> (fa, en)
    "esp_win": ("⚔️ {a} {b} را شکست داد!\n🔔 <b>جایگاه اسپادا شماره {r} تغییر کرد!</b>", "⚔️ {a} defeated {b}!\n🔔 <b>Espada seat #{r} has changed hands!</b>"),
    "esp_lose": ("🛡 {b} (اسپادا {r}) جایگاهش را نگه داشت؛ {a} شکست خورد.", "🛡 {b} (Espada #{r}) held the seat; {a} fell."),
    "level": ("به سطح {n} نیاز داری.", "You need level {n}."),
    "cd": ("هنوز خسته‌ای؛ کمی صبر کن.", "Catch your breath first."),
    "noreg": ("اول در ربات ثبت‌نام کن.", "Register with the bot first."),
    "gone": ("جایگاه همین الان دست‌به‌دست شد؛ دوباره امتحان کن.", "The seat just changed hands; try again."),
    "hog_win": ("🔮 {a} هوگیوکو را از دست {b} ربود!\n👁 حالا نام او در لیست تحت‌تعقیب است.", "🔮 {a} snatched the Hōgyoku from {b}!\n👁 Their name is now on the wanted list."),
    "hog_fail": ("💢 {a} در دزدیدن هوگیوکو شکست خورد و {h} ساعت نصف ریاتسوی خود را از دست داد!", "💢 {a} failed to steal the Hōgyoku and loses half their Reiatsu for {h}h!"),
    "hog_shield": ("🔮 هوگیوکو تازه دست‌به‌دست شده؛ {n} دقیقه امن است.", "🔮 The Hōgyoku just changed hands; it is safe for {n} min."),
    "hog_cd": ("⏳ دوباره تلاش کردن تا {m} دقیقه‌ی دیگر ممکن است.", "⏳ You can try again in {m} min."),
    "q_hit": ("🩸 {who}: {dmg} آسیب به ارتش کوئینسی!", "🩸 {who}: {dmg} damage to the Quincy army!"),
    "rage": ("🎭 هالوی درون {who} کنترل را گرفت؛ ضربه هدر رفت!", "🎭 The Hollow inside {who} took over; the strike was wasted!"),
    "locked": ("🔒 بانکای شما توسط کوئینسی‌ها دزدیده شده است! ({m} دقیقه‌ی دیگر)", "🔒 Your Bankai has been stolen by the Quincy! ({m} min left)"),
    "no_form": ("هنوز {f} را آزاد نکرده‌ای. از «زانپاکتو» شروع کن.", "You haven't unlocked {f} yet. Start with “zanpakuto”."),
    "stance": ("تا {m} دقیقه ضربه‌هایت در حمله‌های گروهی و دوئل اسپادا ×{x} است.", "For {m} min your strikes in group raids and Espada duels hit ×{x}."),
    "mask": ("🎭 ماسک روی صورتت نشست! ×{x} قدرت، اما در هر ضربه {p}٪ احتمال دارد هالوی درون کنترل را بگیرد.",
             "🎭 The mask clamps on! ×{x} power, but each strike has a {p}% chance the Hollow takes over."),
    "mask_cry": ("«خون… بیشتر!»", "“Blood… more!”"),
    "steal_hint": ("برای دزدیدن هوگیوکو روی پیام دارنده‌اش ریپلای کن و «خیانت» بنویس.", "To steal the Hōgyoku, reply to its holder and write “betray”."),
}


def _t(lang, key, **kw):
    fa, en = T[key]
    return (fa if lang == "fa" else en).format(**kw)


async def _group_lang(chat_id):
    return glang(await group_doc(chat_id))


async def viral_hook(message, text: str, n: str) -> bool:
    """True = the message was a reply-word / strike-word of these systems and has been answered."""
    user, chat = message.from_user, message.chat
    reply = message.reply_to_message
    target = reply.from_user if reply and reply.from_user and not reply.from_user.is_bot else None
    me = esc(user.full_name or user.first_name or "")
    if target and target.id != user.id and n in DUEL_WORDS | STEAL_WORDS and not allow(user.id, "viral", 1.0):
        return True
    if target and n in DUEL_WORDS:
        res, extra = await espada_challenge(user.id, target.id)
        if res in ("self", "notespada", "notbetter", "noreg"):
            return False  # an ordinary duel
        lang = await _group_lang(chat.id)
        you = esc(target.full_name or target.first_name or "")
        if res == "win":
            await message.reply(_t(lang, "esp_win", a=me, b=you, r=extra))
        elif res == "lose":
            await message.reply(_t(lang, "esp_lose", a=me, b=you, r=extra))
        else:
            await message.reply(_t(lang, res, n=extra))
        return True
    if target and n in STEAL_WORDS:
        res, extra = await hogyoku_steal(user.id, target.id)
        if res in ("self", "notholder", "noreg"):
            return False
        lang = await _group_lang(chat.id)
        you = esc(target.full_name or target.first_name or "")
        if res == "win":
            await message.reply(_t(lang, "hog_win", a=me, b=you))
        elif res == "fail":
            await message.reply(_t(lang, "hog_fail", a=me, h=extra))
        elif res == "shield":
            await message.reply(_t(lang, "hog_shield", n=extra))
        elif res == "cd":
            await message.reply(_t(lang, "hog_cd", m=max(1, extra // 60)))
        else:
            await message.reply(_t(lang, res, n=extra))
        return True
    if n in STRIKE_WORDS and reply is not None:  # a reply strikes the army; plain word = attack panel
        res, doc, dmg = await quincy_strike(chat.id, user.id)
        if res == "nodoc":
            return False
        lang = await _group_lang(chat.id)
        if res in ("noreg", "level", "cd"):
            if res != "cd":
                await message.reply(_t(lang, res, n=3))
            return True
        if res == "rage":
            await message.reply(_t(lang, "rage", who=me))
            return True
        if res == "dead":
            out = await raid_settle(doc)
            top = "\n".join(f"{i + 1}. {esc(str(nm))} — {fnum(d, lang)}" for i, (nm, d) in enumerate(out["top"]))
            extra = ""
            if out["drop"]:
                uid, iid = out["drop"]
                extra = "\n✨ " + esc(iname(iid, lang)) + " → " + esc(str((doc.get("names") or {}).get(str(uid), uid)))
            for uid, iid in out.get("extra", []):
                extra += "\n🎁 " + esc(iname(iid, lang)) + " → " + esc(str((doc.get("names") or {}).get(str(uid), uid)))
            text_won = handlers_world.quincy_text(lang, doc, "won", top=top, paid=out["paid"], drop=extra)
            await message.reply(text_won)
            await handlers_world.edit_quincy(message.bot, doc, text_won)
            return True
        await message.reply(_t(lang, "q_hit", who=me, dmg=fnum(dmg, lang)))
        if not await try_cooldown(f"quincy:edit:{doc['_id']}", 5):
            await handlers_world.edit_quincy(message.bot, doc, handlers_world.quincy_text(lang, doc, "live"))
        return True
    return False


# ---- word actions (private chat and group) ------------------------------------------------------------------------
@action("bkw")
async def sword_word(ctx, arg):
    """«بانکای» / «شایکای»: instant stance with the blade's own chant. arg: b = Bankai, s = Shikai."""
    fa = ctx.lang == "fa"
    ch, z = await _state(ctx.uid)
    if not ch:
        return Out(_t(ctx.lang, "noreg"), [nav(ctx)])
    kind = "bankai" if arg == "b" else "shikai"
    if kind == "bankai" and ctx.chat_type != "private":
        left = await bankai_lock_left(ctx.chat_id)
        if left:
            return Out(_t(ctx.lang, "locked", m=max(1, left // 60)), [nav(ctx)])
    if not z.get(kind):
        from data_misc import FORMS
        f = (FORMS.get(ch["race"]) or FORMS["human"])[1 if kind == "bankai" else 0]
        return Out(_t(ctx.lang, "no_form", f=f[0 if fa else 1]), [nav(ctx)])
    if await try_cooldown(f"stance:{ctx.uid}", 30):
        return Out(_t(ctx.lang, "cd"), [nav(ctx)])
    await stance_set(ctx.uid, kind)
    mult = STANCE[kind][0]
    return Out(f"🗡 <i>{_chant(ch, z, ctx.lang)}</i>\n" + _t(ctx.lang, "stance", m=STANCE_SECONDS // 60, x=mult), [nav(ctx)])


@action("mkw")
async def mask_word(ctx, arg):
    """«ماسک»: put the Hollow Mask on for a few minutes (strong, but it can run wild)."""
    ch, _z = await _state(ctx.uid)
    if not ch:
        return Out(_t(ctx.lang, "noreg"), [nav(ctx)])
    if await try_cooldown(f"stance:{ctx.uid}", 30):
        return Out(_t(ctx.lang, "cd"), [nav(ctx)])
    await stance_set(ctx.uid, "mask")
    mult, rage = STANCE["mask"]
    return Out("🎭 <i>" + _t(ctx.lang, "mask_cry") + "</i>\n" + _t(ctx.lang, "mask", x=mult, p=int(rage * 100)), [nav(ctx)])


@action("bst")
async def bleach_status(ctx, arg):
    """«وضعیت» / «ریاتسو»: the Bleach card (Espada seat, Hogyoku, division, blade)."""
    fa = ctx.lang == "fa"
    ch, z = await _state(ctx.uid)
    if not ch:
        return Out(_t(ctx.lang, "noreg"), [nav(ctx)])
    rank = await espada_rank(ctx.uid)
    div = DIV_BY_ID.get(ch.get("division") or "")
    hog = await hogyoku_state()
    holds = bool(hog and hog["holder"] == ctx.uid)
    forms = []
    if z.get("shikai"):
        forms.append("Shikai")
    if z.get("bankai"):
        forms.append("Bankai")
    blade = iname(z.get("blade_id") or "", ctx.lang) or "-"
    lines = [
        ("🔔 اسپادا: " + (f"شماره {rank}" if rank is not None else "—")) if fa else ("🔔 Espada: " + (f"#{rank}" if rank is not None else "—")),
        ("🔮 هوگیوکو: " + ("در دست توست!" if holds else "ندارید")) if fa else ("🔮 Hōgyoku: " + ("YOU HOLD IT" if holds else "no")),
        ("🏯 لشکر/نظم: " + (f"{div['icon']} {div['fa']}" if div else "—")) if fa else ("🏯 Division: " + (f"{div['icon']} {div['en']}" if div else "—")),
        ("⚡ زانپاکتو: " if fa else "⚡ Zanpakutō: ") + blade + (f" ({', '.join(forms)})" if forms else ""),
        ("🌀 مهارت (Mastery): " if fa else "🌀 Mastery: ") + fnum(z["mastery"], ctx.lang),
    ]
    return Out(f"⚔️ <b>{esc(ch['name'])}</b> | Lv.{ch['level']}\n{SEP}\n" + "\n".join(lines), [nav(ctx)])


@action("hgs")
async def steal_hint(ctx, arg):
    return Out(_t(ctx.lang, "steal_hint"), [nav(ctx)])


@action("wnt")
async def wanted_list(ctx, arg):
    """Targets under pursuit: the Hogyoku holder (and the Espada number 0)."""
    fa = ctx.lang == "fa"
    h = await hogyoku_holder()
    board = await espada_board()
    lines = []
    if h:
        lines.append(f"{HOGYOKU['icon']} {HOGYOKU['name_fa' if fa else 'name_en']}: <b>{esc(h[1])}</b> (Lv.{h[2]})")
    if board:
        r, _u, name, lv = board[0]
        lines.append(("🔔 اسپادا " if fa else "🔔 Espada #") + f"{r}: <b>{esc(name)}</b> (Lv.{lv})")
    body = "\n".join(lines) or ("—")
    head = "🎯 هدف‌های تحت تعقیب" if fa else "🎯 Wanted targets"
    return Out(f"⚔️ <b>{head}</b>\n{SEP}\n{body}\n\n" + _t(ctx.lang, "steal_hint"), [nav(ctx)])


@action("esp")
async def espada_panel(ctx, arg):
    fa = ctx.lang == "fa"
    board = await espada_board()
    lines = [f"<b>{r}</b> · {esc(name)} (Lv.{lv})" for r, _u, name, lv in board]
    note = ("برای گرفتن جایگاه، روی پیام یک اسپادای بالاتر ریپلای کن و «مبارزه» بنویس." if fa
            else "To take a seat, reply to a higher Espada and write “fight”.")
    return Out(("🔔 <b>اسپادا ۰ تا ۹</b>" if fa else "🔔 <b>Espada 0-9</b>") + f"\n{SEP}\n" + ("\n".join(lines) or "—") + "\n\n" + note, [nav(ctx)])
