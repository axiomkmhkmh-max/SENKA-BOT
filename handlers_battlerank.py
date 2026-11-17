"""Battle Rank panel, the flee button and the rank lines shown after a normal battle.

Codes: brk (rank panel), brl (season ladder: every division and its reward), bf:<sid> (ask to flee), bfx:<sid> (flee).
"""
import time

from data_battlerank import (DIVS, KENPACHI, KENPACHI_ART, REWARD_NAME, SEASON_DAYS, TIER_ICON, div_title, flee_cost,
                             progress, reward_of, season_end, season_of, title)
from fmt import nm
from i18n import esc, fnum
from service_battlerank import current, kenpachi_now, leaderboard
from service_combat import pve_flee
from service_player import get_char
from ui import Out, action, head, nav


def T(ctx, fa, en):
    return fa if ctx.lang == "fa" else en


def _bar(have, need, n=10):
    k = max(0, min(n, int(n * have / max(1, need))))
    return "█" * k + "░" * (n - k)


async def rank_title(ch, lang) -> str:
    """The battle-rank title shown beside (not instead of) the race title. The season's live number one is Kenpachi."""
    rp, _ = current(ch)
    top = await kenpachi_now()
    if top and top.get("user_id") == ch.get("user_id") and rp > 0:
        return f"⚔️ {KENPACHI[0 if lang == 'fa' else 1]}"
    return title(rp, lang)


def result_lines(ctx, br: dict) -> list:
    """Lines for the battle result: the rank change, a promotion or demotion, and the chests won."""
    if not br:
        return []
    L = ctx.lang
    t = br["title_fa" if L == "fa" else "title_en"]
    d = br["delta"]
    sign = "+" if d >= 0 else "−"
    lines = [T(ctx, f"🎖 رنک نبرد: {sign}{fnum(abs(d), L)} → {t}", f"🎖 Battle Rank: {sign}{abs(d)} → {t}")]
    if br.get("up"):
        lines.append(T(ctx, f"⬆️ ارتقا! حالا <b>{t}</b> هستی.", f"⬆️ Promoted! You are now <b>{t}</b>."))
    elif br.get("down"):
        lines.append(T(ctx, f"⬇️ سقوط رتبه به <b>{t}</b>.", f"⬇️ Dropped to <b>{t}</b>."))
    for k, items in br.get("rewards") or []:
        kind, _c = reward_of(k)
        names = ("، " if L == "fa" else ", ").join(nm(i, L) for i in items)
        lines.append(T(ctx, f"🎁 جایزه‌ی {div_title(k, 'fa')}: {REWARD_NAME[kind][0]} — {names}",
                       f"🎁 {div_title(k, 'en')} reward: {REWARD_NAME[kind][1]} — {names}"))
    return lines


@action("brk")
async def rank_panel(ctx, arg):
    ch = await get_char(ctx.uid)
    if not ch:
        return Out(ctx.t("not_registered"), [nav(ctx)])
    L = ctx.lang
    rp, claimed = current(ch)
    k, into, w = progress(rp)
    season = season_of(time.time())
    left = max(0, season_end(season) - int(time.time()))
    days, hours = left // 86400, (left % 86400) // 3600
    lines = [T(ctx, "🎖 <b>رنک نبرد</b> — فقط نبردهای عادی (نه دانجن)", "🎖 <b>Battle Rank</b> — normal battles only (not dungeons)"),
             T(ctx, f"رتبه‌ی تو: <b>{await rank_title(ch, 'fa')}</b>", f"Your rank: <b>{await rank_title(ch, 'en')}</b>"),
             f"<code>{_bar(into, w)}</code> {fnum(into, L)}/{fnum(w, L)}" if k < DIVS - 1 else T(ctx, f"امتیاز: {fnum(rp, L)}", f"Points: {rp}"),
             T(ctx, f"🗓 فصل {fnum(season + 1, L)} · {fnum(days, L)} روز و {fnum(hours, L)} ساعت مانده",
               f"🗓 Season {season + 1} · {days}d {hours}h left"), "",
             T(ctx, "📜 <b>قانون‌ها</b>\n• برد با نوبت کمتر = رنک بیشتر\n• باخت زنجیره را می‌شکند و هرچه رنکت بالاتر باشد بیشتر کم می‌کند\n"
                    f"• فرار رنک زیادی کم می‌کند (الان {fnum(flee_cost(rp), L)}) ولی زنجیره نمی‌شکند\n"
                    "• همه‌چیز نسبیه: درصدی از بازه‌ی همان رتبه\n• به هر زیررتبه که برسی یک‌بار در فصل جایزه می‌گیری\n"
                    f"• نفر اول فصل «{KENPACHI[0]}» می‌شود و «{KENPACHI_ART['name'][0]}» را برای همیشه می‌گیرد",
               "📜 <b>Rules</b>\n• A win in fewer rounds = more rank\n• A loss breaks the chain and costs more the higher you are\n"
               f"• Fleeing costs a lot of rank (now {flee_cost(rp)}) but keeps the chain\n"
               "• Everything is proportional: a share of your division\n• Each sub-tier you reach pays once per season\n"
               f"• The season's number one becomes {KENPACHI[1]} and keeps {KENPACHI_ART['name'][1]} forever")]
    if ch.get("kenpachi_art"):
        lines.append(T(ctx, f"\n👁 {KENPACHI_ART['name'][0]} مال توست.", f"\n👁 You hold {KENPACHI_ART['name'][1]}."))
    top = await leaderboard(season, 10)
    if top:
        lines.append(T(ctx, "\n🏆 <b>ده نفر اول این فصل</b>", "\n🏆 <b>Top ten this season</b>"))
        for i, c in enumerate(top, 1):
            badge = f"⚔️ {KENPACHI[0 if L == 'fa' else 1]}" if i == 1 else title(int(c.get("br", 0)), L)
            lines.append(f"{fnum(i, L)}. {esc(c.get('name', '?'))} — {badge} ({fnum(int(c.get('br', 0)), L)})")
    rows = [[(T(ctx, "🪜 نردبان و جایزه‌ها", "🪜 Ladder and rewards"), "brl", "")], nav(ctx)]
    return Out(head(ctx, "ttl_brk") + "\n".join(lines), rows)


@action("brl")
async def rank_ladder(ctx, arg):
    ch = await get_char(ctx.uid)
    if not ch:
        return Out(ctx.t("not_registered"), [nav(ctx)])
    L = ctx.lang
    rp, claimed = current(ch)
    lines = [T(ctx, f"🪜 <b>نردبان فصل</b> (هر جایزه یک‌بار در فصل؛ فصل‌ها {fnum(SEASON_DAYS, L)} روزه‌اند)",
               f"🪜 <b>Season ladder</b> (each reward once per season; seasons last {SEASON_DAYS} days)")]
    for k in range(DIVS - 1, -1, -1):
        kind, colour = reward_of(k)
        mark = "✅" if k in claimed else "▫️"
        lines.append(f"{mark} {div_title(k, L)} → {TIER_ICON[colour]} {REWARD_NAME[kind][0 if L == 'fa' else 1]}")
    rows = [nav(ctx, ("brk", ""))]
    return Out(head(ctx, "ttl_brk") + "\n".join(lines), rows)


@action("bf")
async def flee_ask(ctx, arg):
    ch = await get_char(ctx.uid)
    rp, _ = current(ch or {})
    text = T(ctx, f"🏃 مطمئنی فرار می‌کنی؟ {fnum(flee_cost(rp), ctx.lang)} امتیاز رنک نبرد از دست می‌دهی (زنجیره‌ی بردت نمی‌شکند).",
             f"🏃 Sure you want to flee? You lose {flee_cost(rp)} Battle Rank points (your win chain is kept).")
    rows = [[(T(ctx, "🏃 فرار کن", "🏃 Flee"), "bfx", arg)], [(T(ctx, "⚔️ می‌جنگم", "⚔️ I fight on"), "bt", "")]]
    return Out(text, rows)


@action("bfx")
async def flee_do(ctx, arg):
    status, res = await pve_flee(ctx.uid, arg)
    if status != "ok":
        return Out(alert=T(ctx, "این نبرد دیگر فعال نیست یا نمی‌شود از آن فرار کرد.", "This battle is over or cannot be fled."))
    lines = [T(ctx, "🏃 از نبرد فرار کردی. زنجیره‌ی بردت سر جایش است.", "🏃 You fled the battle. Your win chain is kept.")]
    lines += result_lines(ctx, res)
    return Out("\n".join(lines), [[(ctx.t("b_again"), "bs", "")], nav(ctx)])
