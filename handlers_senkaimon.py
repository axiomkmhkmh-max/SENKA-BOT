"""Senkaimon: the Soul Society gate. One tap portal between the main parts of the game."""
from ui import SEP, Out, action, nav

GATES = [  # (fa, en, action code)
    ("⚔️ نبرد", "⚔️ Battle", "bt"), ("🕳 دانجن‌ها", "🕳 Dungeons", "dgn"),
    ("🗼 برج ارواح", "🗼 Soul Tower", "twr"), ("👹 باس جهانی", "👹 World Boss", "bossinfo"),
    ("🏆 رتبه‌بندی", "🏆 Rankings", "rnk"), ("🏯 درجه‌ی گوتی", "🏯 Gotei Rank", "sat"),
    ("⚡ زانپاکتو", "⚡ Zanpakutō", "znp"), ("🎭 ماسک هالو", "🎭 Hollow Mask", "hlf"),
    ("🌍 رویدادها", "🌍 World Events", "evt"), ("🗺️ نقشه", "🗺️ Map", "map"),
    ("🛒 بازار", "🛒 Market", "mkt"), ("🎯 بانتی", "🎯 Bounties", "bty"),
]


@action("skm")
async def senkaimon(ctx, arg):
    fa = ctx.lang == "fa"
    title = "🚪 سنکایمون" if fa else "🚪 Senkaimon"
    body = ("دروازه‌ی جهان‌ها باز شد. مقصدت را انتخاب کن." if fa else "The gate between worlds is open. Choose your destination.")
    rows, row = [], []
    for g in GATES:
        row.append((g[0] if fa else g[1], g[2], ""))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append(nav(ctx))
    return Out(f"⚔️ <b>𝖲𝖤𝖭𝖪𝖠</b> | <b>{title}</b>\n{SEP}\n{body}", rows)
