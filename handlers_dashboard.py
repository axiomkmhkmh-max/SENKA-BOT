"""Player 'Today' board: one compact screen with energy, XP, daily reward, world pulse
and a single suggested next step. Read-only except for the existing 'dly' claim button."""
from data_races import RACES  # noqa: F401  (kept for future race flavour in this board)
from database import col, game_settings
from handlers_world import world_line
from i18n import bar, esc, fnum
from service_player import energy_now, get_char, power, today, xp_to_next
from ui import Out, action, head, nav


def T(ctx, fa, en):
    return fa if ctx.lang == "fa" else en


@action("bd")
async def today_board(ctx, arg):
    ch = await get_char(ctx.uid)
    if not ch:
        return Out(ctx.t("not_registered"))
    L = ctx.lang
    st = await game_settings()
    en, _, _ = energy_now(ch, st)
    mx = int(st["energy_max"])
    need = xp_to_next(ch["level"])
    claimed = await col("daily_claims").find_one({"user_id": ctx.uid, "day": today()}) is not None
    streak = int(ch.get("daily_streak", 0) or 0)

    if claimed:
        daily = T(ctx, f"🎁 پاداش امروز گرفته شد ✅ · 🔥 {fnum(streak, L)} روز پیاپی",
                  f"🎁 Today's reward claimed ✅ · 🔥 {fnum(streak, L)} day streak")
    else:
        daily = T(ctx, f"🎁 پاداش امروز آماده است! · 🔥 {fnum(streak, L)} روز پیاپی",
                  f"🎁 Today's reward is ready! · 🔥 {fnum(streak, L)} day streak")

    lines = [
        f"<b>{esc(ch['name'])}</b> · {T(ctx, 'سطح', 'Lv')} {fnum(ch['level'], L)} · ⚔️ {fnum(power(ch), L)}",
        "",
        f"⚡ <code>{bar(en, mx)}</code> {fnum(en, L)}/{fnum(mx, L)}",
        f"⭐ <code>{bar(ch['xp'], need)}</code> {fnum(ch['xp'], L)}/{fnum(need, L)}",
        "",
        daily,
        "",
        await world_line(ctx, ch),
    ]

    # one suggestion, chosen from the state above, so the player never has to guess what to do next
    if not claimed:
        sug = (T(ctx, "🎁 اول پاداش امروز", "🎁 Claim today's reward"), "dly", "")
        hint = T(ctx, "پاداش روزانه را بگیر، بعد برو سراغ نبرد.", "Grab the daily reward first, then head out.")
    elif en >= mx * 0.7:
        sug = (T(ctx, "⚔️ برو شکار", "⚔️ Go explore"), "exp", "")
        hint = T(ctx, "انرژی‌ات پره؛ وقتش برای نبرد است.", "Energy is high; time to fight.")
    else:
        sug = (T(ctx, "📜 ماموریت‌ها", "📜 Missions"), "qst", "")
        hint = T(ctx, "انرژی کمه؛ تا پر شدنش ماموریت‌ها را انجام بده.", "Energy is low; finish missions while it refills.")
    lines += ["", f"💡 <i>{hint}</i>"]

    rows = [
        [sug],
        [(T(ctx, "⚔️ شکار", "⚔️ Explore"), "exp", ""), (T(ctx, "👤 پروفایل", "👤 Profile"), "prof", "")],
        [(T(ctx, "🎒 کوله‌پشتی", "🎒 Bag"), "bag", "0"), (T(ctx, "🛒 بازار", "🛒 Market"), "mkt", "")],
        nav(ctx),
    ]
    return Out(head(ctx, "ttl_home") + "\n".join(lines), rows)
