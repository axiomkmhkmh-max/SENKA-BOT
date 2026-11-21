"""# --- NEW BLEACH VIRAL SYSTEM ---
Plain-word group mechanics (no slash): sword stance words, mask, Bleach status card, Espada 0-9 board and seat challenges,
Hogyoku theft by reply, Quincy invasion strikes. Reply-based words go through `viral_hook` (called from handlers_core.on_group_text);
the other words are ordinary intents (see intents.py) that land in the actions below."""
import time

from aiogram.exceptions import TelegramAPIError

from data_artifacts import HOGYOKU
from data_bleach import DIV_BY_ID
from data_items import iname
from i18n import bar, esc, fnum
from render import glang
from security import allow
from service_bleach_systems import STANCE, STANCE_SECONDS, espada_board, espada_challenge, espada_rank, stance_set
from service_extras import hogyoku_holder, hogyoku_state, hogyoku_steal
from service_log import log_event, log_text
from service_hollowraid import bankai_lock_left, quincy_strike, raid_settle
from service_player import get_char
from service_world import group_doc
from ui import RED, SEP, Out, action, chunk, nav
from database import col, game_settings, try_cooldown
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
    "hog_fail": ("💢 {a} در نبرد هوگیوکو شکست خورد و {h} ساعت نصف ریاتسوی خود را از دست داد!", "💢 {a} lost the Hōgyoku duel and loses half their Reiatsu for {h}h!"),
    "hog_fail0": ("💢 {a} در نبرد هوگیوکو شکست خورد.", "💢 {a} lost the Hōgyoku duel."),
    "hog_weak": ("⚖️ قدرتت ({pa}) برای این چالش کافی نیست؛ دست‌کم {need} لازم است (دارنده: {pb}). قوی‌تر شو و برگرد.", "⚖️ Your power ({pa}) is too low for this challenge; you need at least {need} (holder: {pb}). Grow stronger and come back."),
    "hog_busy": ("⚔️ دارنده همین الان درگیر یک دوئل است؛ چند لحظه‌ی دیگر دوباره امتحان کن.", "⚔️ The holder is in the middle of a duel; try again in a moment."),
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
    "steal_hint": ("برای نبرد با دارنده‌ی هوگیوکو دکمه‌ی زیر را بزن، یا روی پیام او ریپلای کن و «خیانت» بنویس.\n⚔️ نتیجه را قدرت تعیین می‌کند، نه شانس: دوئل واقعی، بهترین از {r} دور (برای بردن {w} دور لازم است).\n⚖️ دست‌کم {pct}٪ قدرت دارنده را لازم داری. اگر ببازی، ریاتسویت برای مدتی نصف می‌شود.",
                   "To fight the Hōgyoku holder, tap the button below, or reply to them and write “betray”.\n⚔️ Power decides it, not luck: a real duel, best of {r} rounds ({w} wins needed).\n⚖️ You need at least {pct}% of the holder's power. Lose and your Reiatsu is halved for a while."),
    "q_gone": ("این حمله تمام شده.", "This invasion is over."),
    "q_pop": ("🩸 {dmg} آسیب! ❤️ {hp} مانده", "🩸 {dmg} damage! ❤️ {hp} left"),
    "q_last": ("🏆 ضربه‌ی آخر مال تو بود!", "🏆 You landed the final blow!"),
    "self": ("نمی‌تونی به خودت چالش بدی.", "You can't challenge yourself."),
    "notespada": ("این بازیکن دیگر اسپادا نیست.", "That player is no longer an Espada."),
    "notbetter": ("فقط به اسپادای بالاتر از خودت می‌تونی چالش بدی.", "You can only challenge a higher Espada."),
    "notholder": ("هوگیوکو دست این بازیکن نیست.", "This player doesn't hold the Hōgyoku."),
    "hog_none": ("فعلاً کسی هوگیوکو را ندارد.", "Nobody holds the Hōgyoku right now."),
    "hog_self": ("هوگیوکو همین الان دست خودته!", "You already hold the Hōgyoku!"),
    "hog_lost": ("🔮 {a} هوگیوکو را از دست تو ربود!", "🔮 {a} snatched the Hōgyoku from you!"),
}


def _t(lang, key, **kw):
    fa, en = T[key]
    return (fa if lang == "fa" else en).format(**kw)


async def _group_lang(chat_id):
    return glang(await group_doc(chat_id))


async def _active_quincy(chat_id: int):
    return await col("quincy_raids").find_one({"chat_id": chat_id, "status": "active", "end_at": {"$gt": int(time.time())}})


async def _raid_min_level() -> int:
    return int((await game_settings())["raid_min_level"])


async def _quincy_won_text(doc: dict, lang: str) -> str:
    """Pay everybody out and build the victory text (shared by the reply word and the button)."""
    out = await raid_settle(doc)
    top = "\n".join(f"{i + 1}. {esc(str(name))} — {fnum(d, lang)}" for i, (name, d) in enumerate(out["top"]))
    extra = ""
    if out["drop"]:
        uid, iid = out["drop"]
        extra = "\n✨ " + esc(iname(iid, lang)) + " → " + esc(str((doc.get("names") or {}).get(str(uid), uid)))
    for uid, iid in out.get("extra", []):
        extra += "\n🎁 " + esc(iname(iid, lang)) + " → " + esc(str((doc.get("names") or {}).get(str(uid), uid)))
    return handlers_world.quincy_text(lang, doc, "won", top=top, paid=out["paid"], drop=extra)


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
        log_text(user.id, "چالش اسپادا (ریپلای)", chat.type)  # this hook answers before the group's own text log runs
        if res in ("win", "lose"):
            log_event("esp", user.id, f"چالش اسپادا {extra} علیه {target.id}: {'برد' if res == 'win' else 'باخت'}", seat=extra, target=target.id)
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
        log_text(user.id, "خیانت (ریپلای)", chat.type)  # this hook answers before the group's own text log runs
        if res in ("win", "fail"):
            await message.reply(_hog_report(lang, extra, me, you, res == "win"))
        elif res == "weak":
            await message.reply(_t(lang, "hog_weak", **{k: fnum(v, lang) for k, v in extra.items()}))
        elif res == "shield":
            await message.reply(_t(lang, "hog_shield", n=extra))
        elif res == "cd":
            await message.reply(_t(lang, "hog_cd", m=max(1, extra // 60)))
        else:
            await message.reply(_t(lang, "hog_busy" if res == "busy" else res, n=extra))
        return True
    if n in STRIKE_WORDS and reply is None:  # the plain word opens the strike panel while an army is attacking this group
        if not await _active_quincy(chat.id):
            return False  # no army here: the word keeps its ordinary meaning (battle panel)
        if not allow(user.id, "qpanel", 3.0) or await try_cooldown(f"quincy:panel:{chat.id}", 20):
            return True
        doc = await _active_quincy(chat.id)
        if doc:
            lang = await _group_lang(chat.id)
            try:
                await message.reply(handlers_world.quincy_text(lang, doc, "live"), reply_markup=handlers_world.quincy_kb(lang))
            except TelegramAPIError:
                pass
        return True
    if n in STRIKE_WORDS and reply is not None:  # a reply strikes the army
        res, doc, dmg = await quincy_strike(chat.id, user.id)
        if res == "nodoc":
            return False
        lang = await _group_lang(chat.id)
        if res in ("noreg", "level", "cd"):
            if res != "cd":
                await message.reply(_t(lang, res, n=await _raid_min_level()))
            return True
        if res == "rage":
            await message.reply(_t(lang, "rage", who=me))
            return True
        if res == "dead":
            text_won = await _quincy_won_text(doc, lang)
            await message.reply(text_won)
            await handlers_world.edit_quincy(message.bot, doc, text_won, final=True)
            return True
        await message.reply(_t(lang, "q_hit", who=me, dmg=fnum(dmg, lang)))
        if not await try_cooldown(f"quincy:edit:{doc['_id']}", 5):
            await handlers_world.edit_quincy(message.bot, doc, handlers_world.quincy_text(lang, doc, "live"))
        return True
    return False


# ---- panel (button) versions of the reply mechanics ----------------------------------------------------------------
async def _edit_panel(ctx, doc, lang, final=False, text=None):
    """Refresh the pressed message when it is a strike panel and not the army's own message (throttled)."""
    msg = ctx.message
    if not msg or msg.message_id == doc.get("msg_id"):
        return
    if not final and await try_cooldown(f"quincy:pedit:{ctx.chat_id}:{msg.message_id}", 3):
        return
    try:
        await ctx.bot.edit_message_text(text or handlers_world.quincy_text(lang, doc, "live"), chat_id=ctx.chat_id, message_id=msg.message_id,
                                        reply_markup=None if final else handlers_world.quincy_kb(lang))
    except TelegramAPIError:
        pass


@action("vrq")
async def quincy_press(ctx, arg):
    """«⚔️ حمله» under the Quincy army message (and under the panel the word «حمله» opens). Popup for the player,
    the army message is refreshed for everyone (at most every few seconds)."""
    res, doc, dmg = await quincy_strike(ctx.chat_id, ctx.uid)
    L = ctx.lang
    if res == "nodoc":
        try:
            if ctx.message:
                await ctx.message.edit_reply_markup(reply_markup=None)
        except TelegramAPIError:
            pass
        return Out(alert=_t(L, "q_gone"))
    if res == "noreg":
        return Out(alert=_t(L, "noreg"))
    if res == "level":
        return Out(alert=_t(L, "level", n=await _raid_min_level()))
    if res == "cd":
        return Out(alert=_t(L, "cd"))
    if res == "rage":
        return Out(alert=_t(L, "rage", who=ctx.user.full_name or ctx.user.first_name or ""))
    gl = await _group_lang(ctx.chat_id)
    if res == "dead":
        text_won = await _quincy_won_text(doc, gl)
        await handlers_world.edit_quincy(ctx.bot, doc, text_won, final=True)
        await _edit_panel(ctx, doc, gl, final=True, text=text_won)
        try:
            await ctx.bot.send_message(ctx.chat_id, text_won)
        except TelegramAPIError:
            pass
        return Out(alert=_t(L, "q_last"))
    if not await try_cooldown(f"quincy:edit:{doc['_id']}", 5):
        await handlers_world.edit_quincy(ctx.bot, doc, handlers_world.quincy_text(gl, doc, "live"))
    await _edit_panel(ctx, doc, gl)
    return Out(alert=_t(L, "q_pop", dmg=fnum(dmg, L), hp=fnum(max(0, doc["hp"]), L)))


async def _hint(L: str) -> str:
    """The rules line, built from the live settings so an admin change shows up at once."""
    from data_artifacts import hog_wins_needed
    st = await game_settings()
    r = max(1, int(st["hog_rounds"]))
    return _t(L, "steal_hint", r=fnum(r, L), w=fnum(hog_wins_needed(r), L), pct=fnum(int(float(st["hog_min_power_ratio"]) * 100), L))


def _hog_report(L: str, rep: dict, a: str, b: str, won: bool) -> str:
    """The duel card: both powers with a bar, every round, then the verdict."""
    fa = L == "fa"
    pa, pb = int(rep["pa"]), int(rep["pb"])
    lines = [("🔮 <b>نبرد هوگیوکو</b>" if fa else "🔮 <b>Hōgyoku Duel</b>"), SEP,
             f"⚔️ <b>{a}</b> · {fnum(pa, L)}",
             f"🛡 <b>{b}</b> · {fnum(pb, L)}",
             bar(pa, pa + pb, 12) + f"  {fnum(round(100 * pa / max(1, pa + pb)), L)}٪" if fa else bar(pa, pa + pb, 12) + f"  {round(100 * pa / max(1, pa + pb))}%"]
    for i, w in enumerate(rep["rounds"], 1):
        who = a if w == "a" else b
        lines.append((f"دور {fnum(i, L)}: " if fa else f"Round {i}: ") + ("🟢 " if w == "a" else "🔴 ") + who)
    lines.append(SEP)
    if won:
        lines.append(_t(L, "hog_win", a=a, b=b))
    else:
        lines.append(_t(L, "hog_fail", a=a, h=rep["hours"]) if rep.get("hours") else _t(L, "hog_fail0", a=a))
    return "\n".join(lines)


async def _hog_rows(ctx):
    h = await hogyoku_holder()
    rows = []
    if h and h[0] != ctx.uid:
        rows.append([("🔮 دزدیدن هوگیوکو" if ctx.lang == "fa" else "🔮 Steal the Hōgyoku", "vrh", "", False, RED)])
    rows.append(nav(ctx))
    return rows


@action("vrh")
async def hog_press(ctx, arg):
    """Button version of «reply to the holder + خیانت»."""
    L = ctx.lang
    h = await hogyoku_holder()
    if not h:
        return Out(alert=_t(L, "hog_none"))
    if h[0] == ctx.uid:
        return Out(alert=_t(L, "hog_self"))
    res, extra = await hogyoku_steal(ctx.uid, h[0])
    me = esc(ctx.user.full_name or ctx.user.first_name or "")
    if res in ("win", "fail"):
        text = _hog_report(L, extra, me, esc(h[1]), res == "win")
    if res == "win":
        try:  # the old holder may be nowhere near this chat
            await ctx.bot.send_message(h[0], _t(await handlers_world._user_lang(h[0]), "hog_lost", a=me))
        except Exception:
            pass
    elif res == "fail":
        pass
    elif res == "weak":
        return Out(alert=_t(L, "hog_weak", **{k: fnum(v, L) for k, v in extra.items()}))
    elif res == "cd":
        return Out(alert=_t(L, "hog_cd", m=max(1, extra // 60)))
    elif res == "shield":
        return Out(alert=_t(L, "hog_shield", n=extra))
    else:  # level | noreg | notholder | self | busy
        return Out(alert=_t(L, "hog_busy" if res == "busy" else res, n=extra))
    return Out(text, await _hog_rows(ctx))


async def _esp_view(ctx):
    fa = ctx.lang == "fa"
    board = await espada_board()
    my = await espada_rank(ctx.uid)
    lines = [f"<b>{r}</b> · {esc(name)} (Lv.{lv})" for r, _u, name, lv in board]
    note = ("برای گرفتن جایگاه، روی دکمه‌ی یک اسپادای بالاتر بزن، یا روی پیامش ریپلای کن و «مبارزه» بنویس." if fa
            else "To take a seat, tap a higher Espada below, or reply to them and write “fight”.")
    btns = [(f"⚔️ #{r} {str(name)[:12]}", "vre", str(u)) for r, u, name, _lv in board if u != ctx.uid and (my is None or r < my)]
    rows = chunk(btns, 2)
    rows.append(nav(ctx))
    text = ("🔔 <b>اسپادا ۰ تا ۹</b>" if fa else "🔔 <b>Espada 0-9</b>") + f"\n{SEP}\n" + ("\n".join(lines) or "—") + "\n\n" + note
    return text, rows


@action("vre")
async def esp_press(ctx, arg):
    """Button version of «reply to a higher Espada + مبارزه». arg = the seat holder's user id."""
    L = ctx.lang
    if not (arg or "").isdigit():
        return Out(alert=_t(L, "gone"))
    tgt = int(arg)
    tc, mc = await get_char(tgt), await get_char(ctx.uid)
    res, extra = await espada_challenge(ctx.uid, tgt)
    if res not in ("win", "lose"):
        return Out(alert=_t(L, res, n=extra))
    me, you = esc((mc or {}).get("name", "?")), esc((tc or {}).get("name", "?"))
    head_t = _t(L, "esp_win" if res == "win" else "esp_lose", a=me, b=you, r=extra)
    body, rows = await _esp_view(ctx)
    return Out(head_t + "\n\n" + body, rows)


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
    from data_zanpakuto import stage_name
    if z.get("shikai"):
        forms.append(stage_name(z.get("blade_id"), "shikai", ctx.lang) or "Shikai")
    if z.get("bankai"):
        forms.append(stage_name(z.get("blade_id"), "bankai", ctx.lang) or "Bankai")
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
    return Out(await _hint(ctx.lang), await _hog_rows(ctx))


@action("wnt")
async def wanted_list(ctx, arg):
    """Targets under pursuit: the Hogyoku holder (and the Espada number 0)."""
    fa = ctx.lang == "fa"
    h = await hogyoku_holder()
    board = await espada_board()
    lines = []
    if h:
        lines.append(f"{HOGYOKU['icon']} {HOGYOKU['name_fa' if fa else 'name_en']}: <b>{esc(h[1])}</b> (Lv.{h[2]})")
        from service_player import power
        hc, mc = await get_char(h[0]), await get_char(ctx.uid)
        if hc and mc:
            ph, pm = int(power(hc)), int(power(mc))
            lines.append((f"⚔️ قدرت دارنده: {fnum(ph, ctx.lang)} · قدرت تو: {fnum(pm, ctx.lang)}" if fa
                          else f"⚔️ Holder power: {ph} · Your power: {pm}") + "\n" + bar(pm, pm + ph, 12))
    if board:
        r, _u, name, lv = board[0]
        lines.append(("🔔 اسپادا " if fa else "🔔 Espada #") + f"{r}: <b>{esc(name)}</b> (Lv.{lv})")
    body = "\n".join(lines) or ("—")
    head = "🎯 هدف‌های تحت تعقیب" if fa else "🎯 Wanted targets"
    return Out(f"⚔️ <b>{head}</b>\n{SEP}\n{body}\n\n" + await _hint(ctx.lang), await _hog_rows(ctx))


@action("esp")
async def espada_panel(ctx, arg):
    text, rows = await _esp_view(ctx)
    return Out(text, rows)
