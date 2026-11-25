"""Shared fighter card for the PvE battle panel and the PvP duel panel (Nov 26 rebuild). Pure rendering, no I/O.

One card, four lines, the same everywhere:
    {icon} NAME  ·  Lv 80 {tag}
    ❤️ ▰▰▰▰▰▰▰▱▱▱▱▱ 62%  12,400/20,000
    🔮 ▰▰▰▰▱▱▱▱ 51%   🔥 ▮▮▮▯▯▯ 40%
    <status chips>   (shield, release, chant, burning ...)
Bars use the same glyphs in both panels so a player reads a duel and a hunt the same way."""
from i18n import esc, fnum


def pct(cur, mx) -> int:
    return 0 if mx <= 0 else max(0, min(100, int(round(100 * cur / mx))))


def bar(cur, mx, n=10, full="▰", empty="▱") -> str:
    k = 0 if mx <= 0 else max(0, min(n, int(round(n * cur / mx))))
    if cur > 0 and k == 0:  # alive is never an empty bar
        k = 1
    return full * k + empty * (n - k)


def heart(p: int) -> str:
    return "❤️" if p > 60 else "🧡" if p > 30 else "💔"


def card(lang: str, f: dict, icon: str, tag: str = "", chips: str = "", subtitle: str = "") -> str:
    fa = lang == "fa"
    x = f.get("x") or {}
    hp, mhp = int(f["hp"]), int(f["max_hp"])
    p = pct(hp, mhp)
    sign = "٪" if fa else "%"
    lv = ("سطح " if fa else "Lv ") + fnum(f["level"], lang)
    lines = [f"{icon} <b>{esc(f['name'])}</b> · {lv}{tag}"]
    if subtitle:
        lines.append(f"<i>{subtitle}</i>")
    lines.append(f"{heart(p)} {bar(hp, mhp)} <b>{fnum(p, lang)}{sign}</b> <code>{fnum(hp, lang)}/{fnum(mhp, lang)}</code>")
    re_, mre = int(f["re"]), int(f["max_re"])
    line = f"🔮 {bar(re_, mre, 8)} <code>{fnum(re_, lang)}</code>"
    g = int(x.get("gauge", 0) or 0)
    if x.get("awake", 0) > 0:
        line += f"  👑 {fnum(g, lang)}{sign} " + ("فعال!" if fa else "ACTIVE!")
    elif g >= 100:
        line += "  🔥 " + ("آماده! ⚡" if fa else "READY! ⚡")
    elif g > 0:
        line += f"  🔥 {bar(g, 100, 6, '▮', '▯')} {fnum(g, lang)}{sign}"
    lines.append(line)
    if chips:
        lines.append(f"<i>{chips}</i>")
    return "\n".join(lines)


def edge_warning(lang: str, f: dict) -> str:
    """One line when a fighter is close to falling or out of reiatsu; empty otherwise."""
    fa = lang == "fa"
    out = []
    if 0 < f["hp"] <= f["max_hp"] * 0.2:
        out.append("⚠️ " + ("روی لبه‌ی سقوطه!" if fa else "on the edge!"))
    if f["max_re"] and f["re"] < f["max_re"] * 0.1:
        out.append("🪫 " + ("ریاتسو ته کشیده" if fa else "reiatsu nearly empty"))
    return " · ".join(out)
