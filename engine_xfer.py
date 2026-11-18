"""Coin transfer between players: parsing of the reply command and the fee rule. Pure logic, no I/O.

Reply to a player's message in a group and write e.g.:
    انتقال 1000        انتقال ۱۰۰۰ سکه        انتقال 5k        انتقال ۲ میلیون        transfer 1,000        send 500 coins
Run tests: python -m unittest test_xfer -v
"""
import re

_DIGITS = str.maketrans({**{c: str(i) for i, c in enumerate("۰۱۲۳۴۵۶۷۸۹")}, **{c: str(i) for i, c in enumerate("٠١٢٣٤٥٦٧٨٩")},
                         "٫": ".", "٬": ",", "،": ","})
MAX_AMOUNT = 10 ** 12

VERBS = r"(?:انتقال|ارسال|حواله|بفرست|واریز|transfer|send|pay)"
# number: 1000 / 1,000 / 1.5 (a fraction only makes sense with a unit such as k or هزار)
NUM = r"(\d+(?:,\d{3})*(?:\.\d+)?)"
UNITS = {"k": 10 ** 3, "هزار": 10 ** 3, "m": 10 ** 6, "میلیون": 10 ** 6, "b": 10 ** 9, "میلیارد": 10 ** 9}
_RE = re.compile(rf"^{VERBS}\s*(?:سکه|coins?|🪙)?\s*{NUM}\s*(k|m|b|هزار|میلیون|میلیارد)?\s*(?:سکه|coins?|🪙)?$", re.IGNORECASE)


def _clean(text: str) -> str:
    t = (text or "").translate(_DIGITS)
    t = t.replace("ي", "ی").replace("ك", "ک")
    t = re.sub(r"[\u200c\u200d\u200e\u200f\u064b-\u0652\u0640]", " ", t)  # zero-width marks, harakat, tatweel
    t = re.sub(r"[!.؟?]+$", "", t.strip())  # a trailing "!" or "." is not part of the number
    return re.sub(r"\s+", " ", t).strip().lower()


def parse_transfer(text: str):
    """The amount if `text` is a transfer command, else None. 0 is never returned (an amount must be positive)."""
    m = _RE.match(_clean(text))
    if not m:
        return None
    num, unit = m.group(1), m.group(2)
    if "." in num and not unit:  # "1.5" alone is not a coin amount
        return None
    try:
        value = float(num.replace(",", "")) * (UNITS.get(unit.lower(), 1) if unit else 1)
    except ValueError:
        return None
    amount = int(round(value))
    return amount if 0 < amount <= MAX_AMOUNT else None


def parse_number(text: str):
    """A plain amount typed in a prompt (Persian digits, separators and a k / هزار unit accepted), else None."""
    t = _clean(text)
    m = re.match(rf"^{NUM}\s*(k|m|b|هزار|میلیون|میلیارد)?$", t)
    if not m:
        return None
    num, unit = m.group(1), m.group(2)
    if "." in num and not unit:
        return None
    amount = int(round(float(num.replace(",", "")) * (UNITS.get(unit.lower(), 1) if unit else 1)))
    return amount if 0 < amount <= MAX_AMOUNT else None


def fee_for(amount: int, pct: float) -> int:
    """Sender pays this on top of the amount. Never zero, so tiny sends cannot dodge the fee."""
    return max(1, int(amount * float(pct)))
