"""Soul Hub (🌌 مرکز روح) panels for the Nov 24 systems (rules in service_soul).

Callback codes: soul (hub), sinr (Inner World duel), suh / suhc (Urahara start / claim), shw / shwc (Human World
patrol join / claim), sgk / sgkc (Gikongan start / claim), sdg / sdgm:<run|hide> (Dangai), scl (Reiatsu Clash).
"""
import time

import service_soul as S
from i18n import esc, fnum
from ui import SEP, Out, action, nav


def T(ctx, fa, en):
    return fa if ctx.lang == "fa" else en


def _dur(ctx, sec: int) -> str:
    h, m = int(sec) // 3600, (int(sec) % 3600) // 60
    if ctx.lang == "fa":
        return f"{fnum(h, 'fa')} ساعت و {fnum(m, 'fa')} دقیقه" if h else f"{fnum(max(1, m), 'fa')} دقیقه"
    return f"{h}h {m}m" if h else f"{max(1, m)}m"


def _head(ctx):
    return f"⚔️ <b>𝖲𝖤𝖭𝖪𝖠</b> | <b>{T(ctx, '🌌 مرکز روح', '🌌 Soul Hub')}</b>\n{SEP}\n"


def _back(ctx):
    return [[(T(ctx, "🔙 مرکز روح", "🔙 Soul Hub"), "soul", "")], nav(ctx)]


ERR = {
    "cooldown": ("هنوز زمانش نرسیده: {t}", "Not yet: {t} left"),
    "fighting": ("الان توی مبارزه‌ای.", "You are in a fight right now."),
    "noreg": ("اول ثبت‌نام کن.", "Register first."),
    "funds": ("سکه کافی نیست (لازم: {t} 🪙).", "Not enough coins (need {t} 🪙)."),
    "running": ("در جریان است؛ {t} مانده.", "In progress; {t} left."),
    "notready": ("هنوز آماده‌ی تحویل نیست.", "Not ready to collect yet."),
    "noitem": ("گیکونگان نداری (از سیاه‌چال عادی می‌افتد).", "You have no Gikongan (drops from normal dungeons)."),
    "limit": ("سهم امروزت تمام شد.", "No clashes left today."),
    "nofoe": ("حریف هم‌سطحی پیدا نشد.", "No opponent of your level found."),
    "closed": ("گشت این گروه بسته شده؛ بعد از پایانش دوباره شروع کن.", "This chat's patrol is closed; start a new one after it ends."),
    "none": ("مسیری در جریان نیست.", "No run in progress."),
    "bad": ("انتخاب نامعتبر.", "Invalid choice."),
}


def _err(ctx, code, extra=None):
    fa, en = ERR.get(code, ("مشکلی پیش آمد.", "Something went wrong."))
    t = _dur(ctx, extra) if code in ("cooldown", "running") and extra else fnum(extra or 0, ctx.lang)
    return Out(alert=(fa if ctx.lang == "fa" else en).format(t=t))


@action("soul")
async def soul_hub(ctx, arg):
    d = await S.soul_doc(ctx.uid)
    now = int(time.time())
    L = ctx.lang

    def state(key, span=None, end_key="end"):
        g = d.get(key) or {}
        if g.get(end_key) and not g.get("claimed", True):
            return T(ctx, "✅ آماده" if g[end_key] <= now else "⏳ " + _dur(ctx, g[end_key] - now),
                     "✅ ready" if g[end_key] <= now else "⏳ " + _dur(ctx, g[end_key] - now))
        cd = S.left(g.get("claimed_at" if key == "urahara" else "at"), span) if span else 0
        return ("⏳ " + _dur(ctx, cd)) if cd else T(ctx, "🟢 آزاد", "🟢 open")

    lines = [T(ctx, "سیستم‌های تازه‌ی دنیای روح:", "New Soul Society systems:"), "",
             T(ctx, f"🗡 <b>نبرد دنیای درون</b> — با روح زنپاکتوی خودت بجنگ (هفتگی). {state('inner', S.INNER_CD)}",
               f"🗡 <b>Inner World duel</b> — fight your own zanpakutō spirit (weekly). {state('inner', S.INNER_CD)}"),
             T(ctx, f"🎩 <b>تمرین اوراهارا</b> — ۷۲ ساعت، {fnum(S.URAHARA_PTS, L)} استت‌پوینت + تجربه. {state('urahara', S.URAHARA_CD)}",
               f"🎩 <b>Urahara training</b> — 72h, {S.URAHARA_PTS} stat points + XP. {state('urahara', S.URAHARA_CD)}"),
             T(ctx, f"🌆 <b>گشت دنیای انسان‌ها</b> — گروهی در همین چت، {fnum(S.HUMAN_HOURS, L)} ساعت، هر هم‌گروه +۱۵٪.",
               f"🌆 <b>Human World patrol</b> — group in this chat, {S.HUMAN_HOURS}h, +15% per member."),
             T(ctx, f"💊 <b>گیکونگان</b> — روح مصنوعی {fnum(S.GIKONGAN_HOURS, L)} ساعت جای تو فارم می‌کند. {state('gikongan')}",
               f"💊 <b>Gikongan</b> — the Mod Soul farms for you for {S.GIKONGAN_HOURS}h. {state('gikongan')}"),
             T(ctx, f"🌀 <b>دانگای</b> — از کوتوتسو فرار کن و به آن طرف برس. {state('dangai', S.DANGAI_CD)}",
               f"🌀 <b>Dangai</b> — outrun the Kototsu to the other side. {state('dangai', S.DANGAI_CD)}"),
             T(ctx, f"💥 <b>برخورد ریاتسو</b> — فشار روحی‌ات را به یک بازیکن هم‌سطح بکوب. امتیاز: {fnum(int((d.get('clash') or {}).get('pts', 0)), L)}",
               f"💥 <b>Reiatsu Clash</b> — slam your spirit pressure into a player of your level. Points: {int((d.get('clash') or {}).get('pts', 0))}")]
    u, g = d.get("urahara") or {}, d.get("gikongan") or {}
    rows = [[(T(ctx, "🗡 دنیای درون", "🗡 Inner World"), "sinr", ""), (T(ctx, "💥 برخورد ریاتسو", "💥 Reiatsu Clash"), "scl", "")],
            [(T(ctx, "🎩 تحویل اوراهارا", "🎩 Collect Urahara") if u.get("end") and not u.get("claimed") else T(ctx, "🎩 تمرین اوراهارا", "🎩 Urahara training"),
              "suhc" if u.get("end") and not u.get("claimed") else "suh", ""),
             (T(ctx, "💊 تحویل گیکونگان", "💊 Collect Gikongan") if g.get("end") and not g.get("claimed") else T(ctx, "💊 گیکونگان", "💊 Gikongan"),
              "sgkc" if g.get("end") and not g.get("claimed") else "sgk", "")],
            [(T(ctx, "🌆 گشت انسان‌ها", "🌆 Human patrol"), "shw", ""), (T(ctx, "🎁 تحویل گشت", "🎁 Collect patrol"), "shwc", "")],
            [(T(ctx, "🌀 دانگای", "🌀 Dangai"), "sdg", "")],
            nav(ctx)]
    return Out(_head(ctx) + "\n".join(lines), rows)


@action("sinr")
async def soul_inner(ctx, arg):
    code, r = await S.inner_duel(ctx.uid)
    if code != "ok":
        return _err(ctx, code, r)
    if r["win"]:
        text = T(ctx, f"🗡 بعد از {fnum(r['turns'], ctx.lang)} نوبت، روح شمشیرت سر خم کرد: «حالا اسم واقعی‌ام را می‌شنوی.»\n"
                      f"+۲۵ پیوند · +{fnum(r['xp'], ctx.lang)} تجربه",
                 f"🗡 After {r['turns']} turns your blade's spirit bows: \"Now you hear my true name.\"\n+25 bond · +{r['xp']:,} XP")
    else:
        text = T(ctx, "🗡 روح شمشیرت تو را از دنیای درونت بیرون انداخت. هفته‌ی بعد قوی‌تر برگرد.",
                 "🗡 Your blade's spirit throws you out of your inner world. Come back stronger next week.")
    return Out(_head(ctx) + text, _back(ctx))


@action("suh")
async def soul_urahara(ctx, arg):
    code, r = await S.urahara_start(ctx.uid)
    if code != "ok":
        return _err(ctx, code, r)
    return Out(_head(ctx) + T(ctx, f"🎩 «خب، شروع کنیم؟» اوراهارا تو را به زیرزمین مغازه برد. {_dur(ctx, r)} دیگر برگرد.",
                              f"🎩 \"Shall we begin?\" Urahara takes you under the shop. Come back in {_dur(ctx, r)}."), _back(ctx))


@action("suhc")
async def soul_urahara_claim(ctx, arg):
    code, r = await S.urahara_claim(ctx.uid)
    if code != "ok":
        return _err(ctx, code, r)
    return Out(_head(ctx) + T(ctx, f"🎩 تمرین تمام شد! +{fnum(r['pts'], ctx.lang)} استت‌پوینت · +{fnum(r['xp'], ctx.lang)} تجربه",
                              f"🎩 Training done! +{r['pts']} stat points · +{r['xp']:,} XP"), _back(ctx))


@action("shw")
async def soul_human(ctx, arg):
    code, p = await S.human_join(ctx.uid, ctx.chat_id)
    if code in ("closed",):
        return _err(ctx, code)
    n, end = len(p["members"]), _dur(ctx, max(0, int(p["end"]) - int(time.time())))
    msg = {"started": T(ctx, f"🌆 گشت در کاراکورا شروع شد ({end}). بقیه تا ۳۰ دقیقه می‌توانند ملحق شوند.",
                        f"🌆 A patrol of Karakura started ({end}). Others can join for 30 minutes."),
           "joined": T(ctx, f"🌆 به گشت پیوستی. اعضا: {fnum(n, ctx.lang)} · {end} مانده.", f"🌆 You joined the patrol. Members: {n} · {end} left."),
           "already": T(ctx, f"🌆 در گشت هستی. اعضا: {fnum(n, ctx.lang)} · {end} مانده.", f"🌆 You are on patrol. Members: {n} · {end} left.")}[code]
    return Out(_head(ctx) + msg, _back(ctx))


@action("shwc")
async def soul_human_claim(ctx, arg):
    code, r = await S.human_claim(ctx.uid, ctx.chat_id)
    if code != "ok":
        return _err(ctx, code, r)
    return Out(_head(ctx) + T(ctx, f"🌆 گشت تمام شد ({fnum(r['members'], ctx.lang)} نفر). +{fnum(r['xp'], ctx.lang)} تجربه · +{fnum(r['coins'], ctx.lang)} 🪙",
                              f"🌆 Patrol over ({r['members']} members). +{r['xp']:,} XP · +{r['coins']:,} 🪙"), _back(ctx))


@action("sgk")
async def soul_gikongan(ctx, arg):
    code, r = await S.gikongan_start(ctx.uid)
    if code != "ok":
        return _err(ctx, code, r)
    return Out(_head(ctx) + T(ctx, f"💊 گیکونگان را قورت دادی؛ روح مصنوعی {_dur(ctx, r)} جای تو هالو شکار می‌کند.",
                              f"💊 You swallow the Gikongan; the Mod Soul hunts Hollows for you for {_dur(ctx, r)}."), _back(ctx))


@action("sgkc")
async def soul_gikongan_claim(ctx, arg):
    code, r = await S.gikongan_claim(ctx.uid)
    if code != "ok":
        return _err(ctx, code, r)
    return Out(_head(ctx) + T(ctx, f"💊 روح مصنوعی برگشت: +{fnum(r['xp'], ctx.lang)} تجربه", f"💊 The Mod Soul is back: +{r['xp']:,} XP"), _back(ctx))


def _dangai_rows(ctx):
    return [[(T(ctx, "🏃 بدو", "🏃 Run"), "sdgm", "run"), (T(ctx, "🫥 پنهان شو", "🫥 Hide"), "sdgm", "hide")]] + _back(ctx)


@action("sdg")
async def soul_dangai(ctx, arg):
    code, r = await S.dangai_start(ctx.uid)
    if code != "ok":
        return _err(ctx, code, r)
    return Out(_head(ctx) + T(ctx, f"🌀 وارد دانگای شدی. دیوارهای کوتوتسو پشت سرت می‌لغزند... مرحله {fnum(r['step'], ctx.lang)}/{fnum(S.DANGAI_STEPS, ctx.lang)}",
                              f"🌀 You enter the Dangai. The Kototsu's walls slide behind you... step {r['step']}/{S.DANGAI_STEPS}"), _dangai_rows(ctx))


@action("sdgm")
async def soul_dangai_move(ctx, arg):
    code, r = await S.dangai_move(ctx.uid, arg)
    if code in ("none", "bad"):
        return _err(ctx, code)
    L = ctx.lang
    if code == "caught":
        return Out(_head(ctx) + T(ctx, f"☠️ کوتوتسو در مرحله {fnum(r['step'], L)} گرفتت و به بیرون پرتت کرد. −{fnum(r['loss'], L)} 🪙",
                                  f"☠️ The Kototsu caught you at step {r['step']} and threw you out. −{r['loss']:,} 🪙"), _back(ctx))
    if code == "escaped":
        return Out(_head(ctx) + T(ctx, f"🚪 از دانگای گذشتی! +{fnum(r['xp'], L)} تجربه · +{fnum(r['coins'], L)} 🪙",
                                  f"🚪 You made it through the Dangai! +{r['xp']:,} XP · +{r['coins']:,} 🪙"), _back(ctx))
    danger = "🟥" * min(10, r["near"]) + "⬜" * max(0, 10 - r["near"])
    return Out(_head(ctx) + T(ctx, f"🌀 مرحله {fnum(r['step'], L)}/{fnum(S.DANGAI_STEPS, L)} · نزدیکی کوتوتسو: {danger}",
                              f"🌀 Step {r['step']}/{S.DANGAI_STEPS} · Kototsu: {danger}"), _dangai_rows(ctx))


@action("scl")
async def soul_clash(ctx, arg):
    code, r = await S.clash(ctx.uid)
    if code != "ok":
        return _err(ctx, code, r)
    L = ctx.lang
    rounds = "\n".join(f"{'🟢' if a > b else '🔴'} {fnum(a, L)} ⚡ {fnum(b, L)}" for a, b in r["rounds"])
    res = (T(ctx, f"💥 فشارت حریف را عقب راند! +۳ امتیاز · +{fnum(r['xp'], L)} تجربه", f"💥 Your pressure drives them back! +3 points · +{r['xp']:,} XP")
           if r["won"] else T(ctx, "💥 ریاتسوی حریف سنگین‌تر بود.", "💥 Their reiatsu was heavier."))
    return Out(_head(ctx) + T(ctx, f"حریف: <b>{esc(r['foe'])}</b>\n", f"Opponent: <b>{esc(r['foe'])}</b>\n") + rounds + "\n\n" + res
               + T(ctx, f"\nباقی‌مانده امروز: {fnum(r['left'], L)}", f"\nLeft today: {r['left']}"), _back(ctx))
