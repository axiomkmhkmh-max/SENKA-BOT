"""Bleach Casino panels: Reiatsu Dice, Hollow Slots, Kido Roulette, Crimson Crash, Hi-Lo, Shinigami 21, jackpot, VIP."""
import service_casino as SC
import engine_casino as C
from i18n import fnum
from service_player import get_char
from ui import Out, action, head, nav

BETS = [100, 1_000, 10_000, 100_000]


def _L(ctx, fa, en):
    return fa if ctx.lang == "fa" else en


def _bet_row(code, prefix_fa, prefix_en, ctx, extra=""):
    return [(f"{prefix_fa if ctx.lang == 'fa' else prefix_en} {fnum(b, ctx.lang)}", code, f"{extra}{b}") for b in BETS]


ERRORS = {
    "too_small": ("شرط خیلی کم است.", "Bet is too small."),
    "too_big": ("شرط از سقف سطح تو بیشتر است.", "Bet is above your level cap."),
    "cool": ("بازی را قطع کن؛ کول‌داون فعال است. کمی استراحت کن.", "Cool-off is active. Take a break."),
    "daily_cap": ("به سقف باخت روزانه رسیدی؛ فردا برگرد.", "You hit today's loss cap. Come back tomorrow."),
    "insufficient": ("سکه‌ی کافی نداری.", "Not enough coins."),
    "no_char": ("اول ثبت‌نام کن.", "Register first."),
    "busy": ("یک هی‌لو باز داری؛ اول تمامش کن.", "You have a Hi-Lo round open. Finish it first."),
}


def _err(ctx, key):
    fa, en = ERRORS.get(key, ("خطا.", "Error."))
    return Out(alert=_L(ctx, fa, en))


def _result_text(ctx, r):
    L = ctx.lang
    won = r["net"] > 0
    lines = [_L(ctx, "🎉 بردی!" if won else ("🤝 مساوی." if r["net"] == 0 else "💀 باختی."), "🎉 You won!" if won else ("🤝 Push." if r["net"] == 0 else "💀 You lost.")),
             f"{_L(ctx, 'شرط', 'Bet')}: {fnum(r['bet'], L)} 🪙  |  {_L(ctx, 'خالص', 'Net')}: {'+' if r['net'] > 0 else ''}{fnum(r['net'], L)}"]
    if r.get("rebate"):
        lines.append(_L(ctx, f"🎟 بازپرداخت VIP: {fnum(r['rebate'], L)} 🪙", f"🎟 VIP rebate: {fnum(r['rebate'], L)} 🪙"))
    if r.get("cool_off"):
        lines.append(_L(ctx, "🧘 پنج باخت پشت‌سرهم؛ ۳۰ دقیقه کول‌داون.", "5 losses in a row: 30 minute cool-off."))
    lines.append(f"👑 VIP: {r['vip']}")
    return "\n".join(lines)


@action("cas")
async def casino_menu(ctx, arg):
    ch = await get_char(ctx.uid)
    if not ch:
        return Out(alert=_L(ctx, "اول ثبت‌نام کن.", "Register first."))
    prof = await SC.profile(ctx.uid)
    jp = await SC.jackpot_status()
    winner = await SC.last_jackpot_winner()
    L = ctx.lang
    win_line = (_L(ctx, f"🏆 آخرین برنده: {winner['uid']} ({fnum(winner['prize'], L)} 🪙)",
                   f"🏆 Last winner: {winner['uid']} ({fnum(winner['prize'], L)} 🪙)") + "\n") if winner else ""
    tier = C.VIP_TIERS[C.vip_tier(prof["wagered"])][0]
    body = (f"🪙 {fnum(ch['coins'], L)}  |  {_L(ctx, 'سقف شرط', 'Max bet')}: {fnum(C.max_bet(ch['level']), L)}\n"
            f"🎰 {_L(ctx, 'جکپات ماسک', 'Mask Jackpot')}: {fnum(jp['pool'], L)} 🪙\n" + win_line +
            f"👑 VIP: {tier}  |  {_L(ctx, 'کل شرط', 'Wagered')}: {fnum(prof['wagered'], L)}\n"
            f"📉 {_L(ctx, 'باخت امروز', 'Lost today')}: {fnum(prof['daily']['loss'], L)} / {fnum(C.DAILY_LOSS_CAP, L)}\n"
            f"{C.HOUSE_EDGE_NOTE}")
    rows = [
        [(_L(ctx, "🎲 تاس ریاتسو", "🎲 Reiatsu Dice"), "cas_dice", "menu")],
        [(_L(ctx, "🎰 اسلات هولو", "🎰 Hollow Slots"), "cas_slots", "menu")],
        [(_L(ctx, "🛞 روله‌ت کیدو", "🛞 Kido Roulette"), "cas_roul", "menu")],
        [(_L(ctx, "📈 کریمسون کراش", "📈 Crimson Crash"), "cas_crash", "menu")],
        [(_L(ctx, "🔼 هی‌لو کیدو", "🔼 Kido Hi-Lo"), "cas_hilo", "menu")],
        [(_L(ctx, "🂡 شینیگامی ۲۱", "🂡 Shinigami 21"), "cas_21", "menu")],
        [(_L(ctx, "🧾 دفتر حساب", "🧾 Ledger"), "cas_ledger", "")],
        nav(ctx),
    ]
    return Out(head(ctx, "ttl_casino") + body, rows)


@action("cas_dice")
async def casino_dice(ctx, arg):
    """arg 'menu' shows the sides; 'o' or 'u' shows bet buttons for that side."""
    if arg == "menu":
        rows = [[(_L(ctx, "⬆️ بالا (۵۱+)", "⬆️ Over (51+)"), "cas_dice", "o"),
                 (_L(ctx, "⬇️ پایین (۴۹-)", "⬇️ Under (49-)"), "cas_dice", "u")], nav(ctx, ("cas", ""))]
        return Out(head(ctx, "ttl_casino") + _L(ctx, "جهت را انتخاب کن. برد ۱.۹ برابر.", "Pick a side. Pays 1.9x."), rows)
    rows = [_bet_row("cas_dice_bet", "🎲", "🎲", ctx, extra=arg + "|"), nav(ctx, ("cas_dice", "menu"))]
    return Out(head(ctx, "ttl_casino") + _L(ctx, "شرط را انتخاب کن.", "Pick a bet."), rows)


@action("cas_dice_bet")
async def casino_dice_bet(ctx, arg):
    pick, bet = arg.split("|")
    res, err = await SC.play_dice(ctx.uid, int(bet), "over" if pick == "o" else "under")
    if err:
        return _err(ctx, err)
    return Out(head(ctx, "ttl_casino") + _result_text(ctx, res), [nav(ctx, ("cas", ""))])


@action("cas_slots")
async def casino_slots(ctx, arg):
    if arg == "menu":
        return Out(head(ctx, "ttl_casino") + _L(ctx, "سه چرخ، هر سه یکی بردن. شرط را انتخاب کن.", "Three reels, match them. Pick a bet."),
                   [_bet_row("cas_slots", "🎰", "🎰", ctx), nav(ctx, ("cas", ""))])
    res, err = await SC.play_slots(ctx.uid, int(arg))
    if err:
        return _err(ctx, err)
    reels = " ".join(res["reels"])
    return Out(head(ctx, "ttl_casino") + f"🎰 {reels}\n" + _result_text(ctx, res), [nav(ctx, ("cas_slots", "menu"))])


@action("cas_roul")
async def casino_roulette(ctx, arg):
    """arg 'menu' shows colours; 'r' 'b' 'g' show bet buttons for that colour."""
    if arg == "menu":
        rows = [[(_L(ctx, "🔴 قرمز", "🔴 Red"), "cas_roul", "r"), (_L(ctx, "⚫ مشکی", "⚫ Black"), "cas_roul", "b"),
                 (_L(ctx, "🟢 سبز", "🟢 Green"), "cas_roul", "g")], nav(ctx, ("cas", ""))]
        return Out(head(ctx, "ttl_casino") + _L(ctx, "رنگ را انتخاب کن. سبز ۳۶ برابر.", "Pick a colour. Green pays 36x."), rows)
    rows = [_bet_row("cas_roul_bet", "🛞", "🛞", ctx, extra=arg + "|"), nav(ctx, ("cas_roul", "menu"))]
    return Out(head(ctx, "ttl_casino") + _L(ctx, "شرط را انتخاب کن.", "Pick a bet."), rows)


@action("cas_roul_bet")
async def casino_roulette_bet(ctx, arg):
    kind, bet = arg.split("|")
    kmap = {"r": "red", "b": "black", "g": "green"}
    res, err = await SC.play_roulette(ctx.uid, int(bet), kmap[kind])
    if err:
        return _err(ctx, err)
    return Out(head(ctx, "ttl_casino") + f"🛞 {res['spin']} ({res['colour']})\n" + _result_text(ctx, res), [nav(ctx, ("cas", ""))])


CRASH_TARGETS = ["1.5", "2", "3", "5"]


@action("cas_crash")
async def casino_crash(ctx, arg):
    """arg 'menu' shows auto-cash targets; a target shows bet buttons for it."""
    if arg == "menu":
        rows = [[(f"x{m}", "cas_crash", m) for m in CRASH_TARGETS], nav(ctx, ("cas", ""))]
        return Out(head(ctx, "ttl_casino") + _L(ctx, "ضریب برداشت خودکار را انتخاب کن.", "Pick an auto-cash multiplier."), rows)
    rows = [_bet_row("cas_crash_bet", "📈", "📈", ctx, extra=arg + "|"), nav(ctx, ("cas_crash", "menu"))]
    return Out(head(ctx, "ttl_casino") + _L(ctx, "شرط را انتخاب کن.", "Pick a bet."), rows)


@action("cas_crash_bet")
async def casino_crash_bet(ctx, arg):
    target, bet = arg.split("|")
    res, err = await SC.play_crash(ctx.uid, int(bet), float(target))
    if err:
        return _err(ctx, err)
    return Out(head(ctx, "ttl_casino") + f"📈 {_L(ctx, 'نقطه‌ی کراش', 'Crash point')}: x{res['point']}\n" + _result_text(ctx, res), [nav(ctx, ("cas", ""))])


@action("cas_hilo")
async def casino_hilo(ctx, arg):
    if arg == "menu":
        return Out(head(ctx, "ttl_casino") + _L(ctx, "شرط بگذار، بعد حدس بزن کارت بعدی بالاتر است یا پایین‌تر.", "Place a bet, then guess higher or lower."),
                   [_bet_row("cas_hilo", "🔼", "🔼", ctx), nav(ctx, ("cas", ""))])
    if arg.startswith("g:"):
        st, res = await SC.hilo_guess(ctx.uid, arg[2:])
        if res:
            return Out(head(ctx, "ttl_casino") + _result_text(ctx, res), [nav(ctx, ("cas", ""))])
        if st is None:
            return Out(alert=_L(ctx, "دور بازی نداری.", "No open round."))
        return Out(head(ctx, "ttl_casino") + _L(ctx, f"کارت: {st['card']} | مرحله: {st['steps']}", f"Card: {st['card']} | Step: {st['steps']}"),
                   [[("⬆️", "cas_hilo", "g:hi"), ("⬇️", "cas_hilo", "g:lo"), (_L(ctx, "💰 برداشت", "💰 Cash out"), "cas_hilo", "g:cash")], nav(ctx, ("cas", ""))])
    st, err = await SC.hilo_start(ctx.uid, int(arg))
    if err:
        return _err(ctx, err)
    return Out(head(ctx, "ttl_casino") + _L(ctx, f"کارت: {st['card']} | مرحله: {st['steps']}", f"Card: {st['card']} | Step: {st['steps']}"),
               [[("⬆️", "cas_hilo", "g:hi"), ("⬇️", "cas_hilo", "g:lo"), (_L(ctx, "💰 برداشت", "💰 Cash out"), "cas_hilo", "g:cash")], nav(ctx, ("cas", ""))])


@action("cas_21")
async def casino_21(ctx, arg):
    if arg == "menu":
        return Out(head(ctx, "ttl_casino") + _L(ctx, "یک بار کارت بکش یا بایست. طبیعی ۲.۵ برابر.", "Hit once or stand. Natural 21 pays 2.5x."),
                   [[(_L(ctx, "🂡 یک کارت", "🂡 Hit once"), "cas_21", "h"), (_L(ctx, "✋ بایست", "✋ Stand"), "cas_21", "s")], nav(ctx, ("cas", ""))])
    if "|" not in arg:
        return Out(head(ctx, "ttl_casino") + _L(ctx, "شرط را انتخاب کن.", "Pick a bet."), [_bet_row("cas_21", "🂡", "🂡", ctx, extra=arg + "|"), nav(ctx, ("cas_21", "menu"))])
    mode, bet = arg.split("|")
    res, err = await SC.play_shini21(ctx.uid, int(bet), hit_once=(mode == "h"))
    if err:
        return _err(ctx, err)
    return Out(head(ctx, "ttl_casino") + _result_text(ctx, res), [nav(ctx, ("cas", ""))])
