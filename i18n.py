"""Translations with English fallback, number formatting and HTML escaping."""
import html

import locale_en
import locale_fa

LOCALES = {"fa": locale_fa.TEXT, "en": locale_en.TEXT}
_FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
_RLM = "\u200f"


def esc(value) -> str:
    return html.escape(str(value), quote=False)


def fnum(n, lang: str = "en") -> str:
    try:
        s = f"{int(n):,}"
    except (TypeError, ValueError):
        s = str(n)
    return s.translate(_FA).replace(",", "٬") if lang == "fa" else s


def t(lang: str, key: str, **kw) -> str:
    table = LOCALES.get(lang) or LOCALES["en"]
    text = table.get(key)
    if text is None:
        text = LOCALES["en"].get(key, key)
    if kw:
        try:
            return text.format(**kw)
        except (KeyError, IndexError, ValueError):
            return text
    return text


def bar(cur, mx, n=10) -> str:
    k = 0 if mx <= 0 else max(0, min(n, int(round(n * cur / mx))))
    return "▰" * k + "▱" * (n - k)
