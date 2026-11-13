"""Extra player features (✨ امکانات): stats card, achievements, rank tiers, wealth/level rank,
daily fortune and tip, Bleach trivia (paid once a day), coin flip, coin transfer, compare with
another player, feedback to admins, shareable card, newcomer checklist.

Money moves only through add_coins (grants) or an atomic conditional $inc (debits), and every
gamble / transfer goes through bump_counter daily caps, so nothing here can mint or lose coins
outside those rules."""
import hashlib
import random
import time

from data_races import STAT_ICON, STATS, soft_stat
from database import bump_counter, col, game_settings
from i18n import esc, fnum, bar
from service_player import add_coins, energy_now, get_char, power, xp_to_next
from ui import Out, action, head, input_handler, nav

DAY = 86400


def T(ctx, fa, en):
    return fa if ctx.lang == "fa" else en


def _day() -> str:
    return time.strftime("%Y-%m-%d", time.gmtime())


# ---- static content --------------------------------------------------------------------------------------
FORTUNES = [
    ("امروز سرنوشت خوبی برات نوشته شده؛ ولی با احتیاط پیش برو.", "Fate looks kind today. Still, move carefully."),
    ("یه ناشناس توی نبرد کمکت می‌کنه؛ مراقب دوستی‌های تازه باش.", "A stranger will help in battle. Watch new alliances."),
    ("گنج پنهان نزدیکه، اما فقط برای کسی که صبر کنه.", "Hidden treasure is near, for those who wait."),
    ("امروز آرامش داری، از این فرصت برای ارتقا استفاده کن.", "Calm day. Use it to grow stronger."),
    ("یه جنگ بزرگ داره شروع میشه؛ آماده باش.", "A great battle is coming. Be ready."),
    ("سکه‌هات امروز بیشتر از همیشه دوست دارن بمونن؛ خرج نکن.", "Your coins want to stay today. Think before spending."),
    ("یه رئیس قدیمی دوباره بیدار میشه.", "An old boss is stirring again."),
    ("شانس با توئه؛ امروز بهترین روز برای ریسک کردن نیست، برای یادگیری هست.", "Luck is yours. Today is for learning, not gambling."),
]
TIPS = [
    ("انرژی قبل از گشت‌وگذار رو پر کن تا اتلاف نشه.", "Fill energy before exploring so none gets wasted."),
    ("وقتی انرژی پره، دانجن بهتر از گشت‌وگذاره.", "When energy is full, dungeons pay better than exploring."),
    ("ماموریت‌های روزانه رو از دست نده؛ سکه‌ی خوبی میدن.", "Do your daily missions; they pay well."),
    ("قبل از ارتقا، ببین کدوم استات بیشترین اثر رو داره.", "Before upgrading, check which stat gives the most power."),
    ("تو بازار قیمت‌ها رو مقایسه کن؛ همیشه ارزون‌ترین بهترین نیست.", "Compare market prices; cheapest is not always best."),
    ("دوستات رو به گیلد دعوت کن، پاداش گروهی داره.", "Invite friends to a guild for group rewards."),
    ("پاداش روزانه رو هر روز بگیر، streak بیشتر، پاداش بهتر.", "Claim the daily reward every day; longer streaks pay more."),
    ("رنکینگ رو چک کن تا ببینی کجا ایستادی.", "Check the ranking to see where you stand."),
    ("قبل از نبرد سخت، کیدو و اکسیر رو آماده کن.", "Prepare your Kido and potions before a hard fight."),
    ("اگه ویژگی جدیدی دیدی، توی منوی امکانات ببینش.", "New features live in the Extras menu."),
]
TRIVIA = [
    ("ایچیگو کوروساکی کدوم شینیگامی رو داره؟", ["زانپاکوتو", "تنسا‌زانگتسو", "هیورینمارو"], 0),
    ("نام شهر شینیگامی‌ها چیه؟", ["سوکائه", "هوئکو موندو", "روکونگای"], 0),
    ("کدوم شخصیت شینیگامی است و هالو نیست؟", ["گریمجو", "یاچیرو", "ولزی"], 1),
    ("کاپیتان دیویژن اول گوتئی ۱۳ کیست؟", ["کاپیتان یاماموتو", "بیاکویا کوچیکی", "کاپیتان کیراکا"], 0),
    ("شمشیر شینیگامی‌ها چه نام دارد؟", ["زانپاکوتو", "کیدو", "هوگیوکو"], 0),
    ("رنگ موی اصلی ایچیگو چیه؟", ["نارنجی", "سیاه", "سفید"], 0),
    ("شمشیر هیتسوگایا توشیرو چه نام داره؟", ["هیورینمارو", "زانپاکوتو", "کیدو"], 0),
]
RANK_TIERS = [
    (0, "شینیگامی درجه‌ی ۵", "5th-Seat Shinigami"),
    (10, "شینیگامی درجه‌ی ۳", "3rd-Seat Shinigami"),
    (25, "کاپیتان", "Captain"),
    (50, "فرمانده", "Commander"),
    (80, "کاپیتان فرمانده", "Captain-Commander"),
]


def _tier(level: int, L: str) -> str:
    name = RANK_TIERS[0]
    for lv, fa, en in RANK_TIERS:
        if level >= lv:
            name = (lv, fa, en)
    return name[1] if L == "fa" else name[2]


ACHIEVEMENTS = [
    ("level", 10, "سطح ۱۰", "Level 10"),
    ("level", 30, "سطح ۳۰", "Level 30"),
    ("level", 60, "سطح ۶۰", "Level 60"),
    ("wins", 10, "۱۰ برد", "10 wins"),
    ("wins", 100, "۱۰۰ برد", "100 wins"),
    ("coins", 10000, "۱۰هزار سکه", "10k coins"),
    ("coins", 1000000, "یک میلیون سکه", "1M coins"),
    ("rating", 1200, "رتبه ۱۲۰۰", "Rating 1200"),
    ("pvp_w", 20, "۲۰ برد PvP", "20 PvP wins"),
    ("daily_streak", 7, "استریک ۷ روزه", "7-day streak"),
]


# ---- hub ------------------------------------------------------------------------------------------------------
@action("xf")
async def hub(ctx, arg):
    rows = [
        [(T(ctx, "🧾 کارت آمار", "🧾 Stats card"), "xf_card", ""), (T(ctx, "🏅 دستاوردها", "🏅 Achievements"), "xf_ach", "")],
        [(T(ctx, "🎖 درجه و رتبه", "🎖 Rank"), "xf_rank", ""), (T(ctx, "🔮 فال امروز", "🔮 Daily fortune"), "xf_fort", "")],
        [(T(ctx, "🧠 مسابقه‌ی بلیچ", "🧠 Bleach quiz"), "xf_quiz", ""), (T(ctx, "🪙 شیر یا خط", "🪙 Coin flip"), "xf_cf", "")],
        [(T(ctx, "💸 انتقال سکه", "💸 Send coins"), "xf_tr", ""), (T(ctx, "⚖️ مقایسه", "⚖️ Compare"), "xf_cmp", "")],
        [(T(ctx, "💡 نکته‌ی امروز", "💡 Tip of the day"), "xf_tip", ""), (T(ctx, "✅ چک‌لیست", "✅ Checklist"), "xf_todo", "")],
        [(T(ctx, "🔬 جزئیات قدرت", "🔬 Power details"), "xf_stats", ""), (T(ctx, "⚡ انرژی", "⚡ Energy"), "xf_energy", "")],
        [(T(ctx, "📮 بازخورد به ادمین", "📮 Feedback"), "xf_fb", ""), (T(ctx, "🪪 کارت برای دوستان", "🪪 Share card"), "xf_share", "")],
        nav(ctx),
    ]
    return Out(head(ctx, "ttl_menu") + T(ctx, "✨ <b>امکانات</b>\nیکی رو انتخاب کن.", "✨ <b>Extras</b>\nPick one."), rows)


# ---- stats & progress ------------------------------------------------------------------------------------------
@action("xf_card")
async def card(ctx, arg):
    ch = await get_char(ctx.uid)
    if not ch:
        return Out(ctx.t("not_registered"))
    L = ctx.lang
    w, l = int(ch.get("wins", 0) or 0), int(ch.get("losses", 0) or 0)
    total = w + l
    wr = round(100 * w / total) if total else 0
    lines = [
        f"<b>{esc(ch['name'])}</b> · {_tier(ch['level'], L)}",
        T(ctx, f"⚔️ قدرت: {fnum(power(ch), L)} · 🎖 سطح: {fnum(ch['level'], L)}", f"⚔️ Power: {fnum(power(ch), L)} · 🎖 Lv: {fnum(ch['level'], L)}"),
        T(ctx, f"🏆 برد: {fnum(w, L)} · 💀 باخت: {fnum(l, L)} · نرخ برد: {wr}٪", f"🏆 Wins: {w} · Losses: {l} · Win rate: {wr}%"),
        T(ctx, f"🪙 سکه: {fnum(ch['coins'], L)}", f"🪙 Coins: {fnum(ch['coins'], L)}"),
        f"<code>{bar(wr, 100)}</code> {wr}%",
    ]
    return Out(head(ctx, "ttl_menu") + "\n".join(x for x in lines if x), [nav(ctx, ("xf", ""))])


@action("xf_ach")
async def achievements(ctx, arg):
    ch = await get_char(ctx.uid)
    if not ch:
        return Out(ctx.t("not_registered"))
    L = ctx.lang
    done = 0
    lines = []
    for field, need, fa, en in ACHIEVEMENTS:
        have = ch.get(field, 0) or 0
        ok = have >= need
        done += ok
        label = fa if L == "fa" else en
        lines.append(f"{'✅' if ok else '🔒'} {label} · <code>{fnum(min(have, need), L)}/{fnum(need, L)}</code>")
    head_line = T(ctx, f"🏅 دستاوردها: {fnum(done, L)}/{fnum(len(ACHIEVEMENTS), L)}", f"🏅 Achievements: {done}/{len(ACHIEVEMENTS)}")
    return Out(head(ctx, "ttl_menu") + head_line + "\n\n" + "\n".join(lines), [nav(ctx, ("xf", ""))])


@action("xf_stats")
async def stat_breakdown(ctx, arg):
    ch = await get_char(ctx.uid)
    if not ch:
        return Out(ctx.t("not_registered"))
    L = ctx.lang
    vals = {k: soft_stat(ch["stats"][k]) for k in STATS}
    top = max(vals.values(), default=1) or 1
    lines = [f"{STAT_ICON.get(k, '•')} {k}: <code>{bar(v, top)}</code> {fnum(v, L)}" for k, v in vals.items()]
    return Out(head(ctx, "ttl_menu") + T(ctx, "🔬 <b>جزئیات قدرت</b>", "🔬 <b>Power breakdown</b>") + "\n\n" + "\n".join(lines), [nav(ctx, ("xf", ""))])


@action("xf_energy")
async def energy_info(ctx, arg):
    ch = await get_char(ctx.uid)
    if not ch:
        return Out(ctx.t("not_registered"))
    L = ctx.lang
    st = await game_settings()
    en, _, _ = energy_now(ch, st)
    mx = int(st["energy_max"])
    text = T(ctx, f"⚡ انرژی: <code>{bar(en, mx)}</code> {fnum(en, L)}/{fnum(mx, L)}",
             f"⚡ Energy: <code>{bar(en, mx)}</code> {en}/{mx}")
    return Out(head(ctx, "ttl_menu") + text, [nav(ctx, ("xf", ""))])


@action("xf_rank")
async def rank(ctx, arg):
    ch = await get_char(ctx.uid)
    if not ch:
        return Out(ctx.t("not_registered"))
    L = ctx.lang
    wealth = await col("characters").count_documents({"coins": {"$gt": ch.get("coins", 0)}}) + 1
    levels = await col("characters").count_documents({"level": {"$gt": ch.get("level", 1)}}) + 1
    need = xp_to_next(ch["level"])
    text = "\n".join([
        T(ctx, f"🎖 درجه: <b>{_tier(ch['level'], L)}</b>", f"🎖 Rank: <b>{_tier(ch['level'], L)}</b>"),
        T(ctx, f"🪙 رتبه‌ات در ثروت: #{fnum(wealth, L)}", f"🪙 Wealth rank: #{wealth}"),
        T(ctx, f"📈 رتبه‌ات در سطح: #{fnum(levels, L)}", f"📈 Level rank: #{levels}"),
        T(ctx, f"⭐ تا سطح بعد: <code>{bar(ch['xp'], need)}</code> {fnum(need - ch['xp'], L)} XP",
          f"⭐ To next level: <code>{bar(ch['xp'], need)}</code> {need - ch['xp']} XP"),
    ])
    return Out(head(ctx, "ttl_menu") + text, [nav(ctx, ("xf", ""))])


@action("xf_todo")
async def checklist(ctx, arg):
    ch = await get_char(ctx.uid)
    if not ch:
        return Out(ctx.t("not_registered"))
    L = ctx.lang
    items = [
        (T(ctx, "پاداش روزانه", "Daily reward"), int(ch.get("daily_streak", 0) or 0) > 0),
        (T(ctx, "اولین نبرد", "First battle"), int(ch.get("wins", 0) or 0) + int(ch.get("losses", 0) or 0) > 0),
        (T(ctx, "یک بار ارتقا", "Upgrade once"), int(ch.get("points", 0) or 0) == 0 and ch["level"] > 1),
        (T(ctx, "یک آیتم در کوله‌پشتی", "An item in your bag"), bool(ch.get("items"))),
        (T(ctx, "سطح ۵", "Reach level 5"), ch["level"] >= 5),
    ]
    done = sum(1 for _, ok in items if ok)
    lines = [f"{'✅' if ok else '⬜'} {label}" for label, ok in items]
    return Out(head(ctx, "ttl_menu") + T(ctx, f"✅ چک‌لیست: {fnum(done, L)}/{len(items)}", f"✅ Checklist: {done}/{len(items)}")
               + "\n\n" + "\n".join(lines), [nav(ctx, ("xf", ""))])


# ---- daily fun -------------------------------------------------------------------------------------------------
@action("xf_fort")
async def fortune(ctx, arg):
    rnd = random.Random(hashlib.sha256(f"{ctx.uid}{_day()}".encode()).hexdigest())
    fa, en = rnd.choice(FORTUNES)
    return Out(head(ctx, "ttl_menu") + "🔮 " + T(ctx, fa, en), [nav(ctx, ("xf", ""))])


@action("xf_tip")
async def tip(ctx, arg):
    rnd = random.Random(_day())
    fa, en = rnd.choice(TIPS)
    return Out(head(ctx, "ttl_menu") + "💡 " + T(ctx, fa, en), [nav(ctx, ("xf", ""))])


# ---- trivia (once a day, paid) ------------------------------------------------------------------------------
@action("xf_quiz")
async def quiz(ctx, arg):
    if not await get_char(ctx.uid):
        return Out(ctx.t("not_registered"))
    idx = random.Random(hashlib.sha256(f"q{ctx.uid}{_day()}".encode()).hexdigest()).randrange(len(TRIVIA))
    q, opts, _ = TRIVIA[idx]
    if arg == "":
        rows = [[(opt, "xf_qa", f"{idx}.{i}")] for i, opt in enumerate(opts)] + [nav(ctx, ("xf", ""))]
        return Out(head(ctx, "ttl_menu") + "🧠 " + q, rows)
    return Out(head(ctx, "ttl_menu") + T(ctx, "جوابت رو زدی؛ دوباره امروز بیا.", "Answer sent; come back tomorrow."), [nav(ctx, ("xf", ""))])


@action("xf_qa")
async def quiz_answer(ctx, arg):
    try:
        idx, pick = (int(x) for x in arg.split("."))
    except Exception:
        return Out(alert="?")
    _, _, correct = TRIVIA[idx % len(TRIVIA)]
    if pick != correct:
        return Out(head(ctx, "ttl_menu") + T(ctx, "❌ اشتباه بود. فردا دوباره امتحان کن.", "❌ Wrong. Try again tomorrow."), [nav(ctx, ("xf", ""))])
    granted = await bump_counter(f"quiz:{ctx.uid}", 1, 1, 24)
    if not granted:
        return Out(head(ctx, "ttl_menu") + T(ctx, "درست بود، ولی جایزه‌ی امروزت رو گرفتی.", "Correct, but you already claimed today's reward."), [nav(ctx, ("xf", ""))])
    await add_coins(ctx.uid, 40, "quiz")
    return Out(head(ctx, "ttl_menu") + T(ctx, "✅ درست! +۴۰ سکه", "✅ Correct! +40 coins"), [nav(ctx, ("xf", ""))])


# ---- coin flip (bounded) ----------------------------------------------------------------------------------------
@action("xf_cf")
async def coinflip(ctx, arg):
    ch = await get_char(ctx.uid)
    if not ch:
        return Out(ctx.t("not_registered"))
    L = ctx.lang
    if arg == "":
        rows = [[(f"{p}٪", "xf_cf", str(p)) for p in (5, 10, 25)], nav(ctx, ("xf", ""))]
        return Out(head(ctx, "ttl_menu") + T(ctx, "🪙 چقدر شرط می‌بندی؟ (درصدی از سکه‌هات)", "🪙 Bet how much? (percent of your coins)"), rows)
    pct = int(arg) if arg.isdigit() and int(arg) in (5, 10, 25) else 5
    bet = max(1, int(ch["coins"]) * pct // 100)
    if bet > 200000:
        bet = 200000
    if not await bump_counter(f"cf:{ctx.uid}", 1, 20, 24):
        return Out(head(ctx, "ttl_menu") + T(ctx, "امروز ۲۰ بار شیر یا خط زدی؛ فردا.", "You used 20 flips today; come back tomorrow."), [nav(ctx, ("xf", ""))])
    # debit first, atomically: the bet must be covered by the balance at this moment
    res = await col("characters").find_one_and_update({"user_id": ctx.uid, "coins": {"$gte": bet}}, {"$inc": {"coins": -bet}})
    if not res:
        return Out(head(ctx, "ttl_menu") + T(ctx, "سکه‌ی کافی نداری.", "Not enough coins."), [nav(ctx, ("xf", ""))])
    if random.random() < 0.48:  # house edge, so flipping is not a money printer
        await add_coins(ctx.uid, bet * 2, "coinflip")
        msg = T(ctx, f"🎉 بردی! +{fnum(bet, L)} سکه", f"🎉 You won! +{bet}")
    else:
        msg = T(ctx, f"💀 باختی: -{fnum(bet, L)} سکه", f"💀 You lost {bet} coins")
    return Out(head(ctx, "ttl_menu") + msg, [[(T(ctx, "🔁 دوباره", "🔁 Again"), "xf_cf", str(pct))], nav(ctx, ("xf", ""))])


# ---- transfer and compare -------------------------------------------------------------------------------------
@action("xf_tr")
async def transfer_start(ctx, arg):
    if not await get_char(ctx.uid):
        return Out(ctx.t("not_registered"))
    await col("inputs").update_one({"user_id": ctx.uid}, {"$set": {"kind": "xf_tr", "at": int(time.time())}}, upsert=True)
    return Out(head(ctx, "ttl_menu") + T(ctx, "بفرست: <code>آیدی_بازیکن مقدار</code>\nمثال: <code>123456 1000</code>\nکارمزد ۵٪ و سقف روزانه‌ی ۵۰۰هزار سکه.",
                                         "Send: <code>player_id amount</code>\nExample: <code>123456 1000</code>\n5% fee, 500k per day cap."),
               [nav(ctx, ("xf", ""))])


@input_handler("xf_tr")
async def transfer_input(ctx, text):
    L = ctx.lang
    parts = (text or "").split()
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
        return Out(T(ctx, "فرمت اشتباهه. مثال: 123456 1000", "Bad format. Example: 123456 1000"), [nav(ctx, ("xf", ""))])
    to, amount = int(parts[0]), int(parts[1])
    if to == ctx.uid or amount <= 0:
        return Out(T(ctx, "این انتقال ممکن نیست.", "Transfer not allowed."), [nav(ctx, ("xf", ""))])
    fee = max(1, amount * 5 // 100)
    total = amount + fee
    if not await col("characters").find_one({"user_id": to}, {"_id": 1}):
        return Out(T(ctx, "بازیکن پیدا نشد.", "Player not found."), [nav(ctx, ("xf", ""))])
    if not await bump_counter(f"tr:{ctx.uid}", amount, 500000, 24):
        return Out(T(ctx, "سقف انتقال امروزت پر شده.", "Daily transfer cap reached."), [nav(ctx, ("xf", ""))])
    res = await col("characters").find_one_and_update({"user_id": ctx.uid, "coins": {"$gte": total}}, {"$inc": {"coins": -total}})
    if not res:
        return Out(T(ctx, "سکه‌ی کافی نداری (با کارمزد).", "Not enough coins (including fee)."), [nav(ctx, ("xf", ""))])
    await add_coins(to, amount, f"transfer from {ctx.uid}")
    return Out(T(ctx, f"✅ {fnum(amount, L)} سکه فرستاده شد (کارمزد: {fnum(fee, L)})", f"✅ Sent {amount} coins (fee: {fee})"), [nav(ctx, ("xf", ""))])


@action("xf_cmp")
async def compare_start(ctx, arg):
    if not await get_char(ctx.uid):
        return Out(ctx.t("not_registered"))
    await col("inputs").update_one({"user_id": ctx.uid}, {"$set": {"kind": "xf_cmp", "at": int(time.time())}}, upsert=True)
    return Out(head(ctx, "ttl_menu") + T(ctx, "آیدی بازیکنی که می‌خوای باهاش مقایسه کنی رو بفرست.", "Send the player ID you want to compare with."), [nav(ctx, ("xf", ""))])


@input_handler("xf_cmp")
async def compare_input(ctx, text):
    L = ctx.lang
    me, other = await get_char(ctx.uid), None
    if (text or "").strip().isdigit():
        other = await get_char(int(text.strip()))
    if not other:
        return Out(T(ctx, "بازیکن پیدا نشد.", "Player not found."), [nav(ctx, ("xf", ""))])
    def row(label, a, b):
        mark = "🟢" if a > b else ("🔴" if a < b else "⚪")
        return f"{mark} {label}: {fnum(a, L)} | {fnum(b, L)}"
    lines = [
        f"<b>{esc(me['name'])}</b> vs <b>{esc(other['name'])}</b>",
        row("Lv", me["level"], other["level"]),
        row("⚔️", power(me), power(other)),
        row("🏆", int(me.get("wins", 0) or 0), int(other.get("wins", 0) or 0)),
        row("🪙", int(me["coins"]), int(other["coins"])),
    ]
    return Out("\n".join(lines), [nav(ctx, ("xf", ""))])


# ---- feedback and share ------------------------------------------------------------------------------------
@action("xf_fb")
async def feedback_start(ctx, arg):
    await col("inputs").update_one({"user_id": ctx.uid}, {"$set": {"kind": "xf_fb", "at": int(time.time())}}, upsert=True)
    return Out(head(ctx, "ttl_menu") + T(ctx, "پیشنهاد، باگ یا ایده‌ات رو بنویس؛ مستقیم برای ادمین‌ها میره.",
                                         "Write your idea or bug; it goes straight to the admins."), [nav(ctx, ("xf", ""))])


@input_handler("xf_fb")
async def feedback_input(ctx, text):
    msg = (text or "").strip()[:1000]
    if not msg:
        return Out(T(ctx, "خالیه.", "Empty."), [nav(ctx, ("xf", ""))])
    await col("feedback").insert_one({"user_id": ctx.uid, "text": msg, "at": int(time.time()), "read": False})
    return Out(T(ctx, "ممنون! ثبت شد. 🙏", "Thanks! Recorded. 🙏"), [nav(ctx, ("xf", ""))])


@action("xf_share")
async def share(ctx, arg):
    ch = await get_char(ctx.uid)
    if not ch:
        return Out(ctx.t("not_registered"))
    L = ctx.lang
    text = (f"⚔️ {ch['name']} · {_tier(ch['level'], L)}\n"
            f"🎖 Lv {ch['level']} · ⚔️ {power(ch)} · 🏆 {int(ch.get('wins', 0) or 0)}\n"
            f"🆔 {ch['user_id']}")
    return Out(head(ctx, "ttl_menu") + T(ctx, "کارتت رو کپی کن و برای دوستات بفرست:", "Copy your card and share it:") + f"\n\n<code>{esc(text)}</code>", [nav(ctx, ("xf", ""))])
