"""Pure helpers for the admin panel: input parsing, setting values, paging. No I/O, no Telegram.

Kept separate from handlers_adminpanel so the rules can be unit-tested without a database or a bot.
"""

_FA_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
_BOOL_ON = {"on", "true", "1", "yes", "روشن", "بله"}
_BOOL_OFF = {"off", "false", "0", "no", "خاموش", "خیر"}


def to_ascii_digits(text: str) -> str:
    """Persian and Arabic digits become ASCII, so '۱۰۰۰' parses like '1000'."""
    return (text or "").translate(_FA_DIGITS)


def split_id_rest(text: str):
    """'<id> rest of text' -> (id or None, rest). The id may carry a leading @ or a minus sign."""
    parts = to_ascii_digits(text or "").strip().split(maxsplit=1)
    if not parts:
        return None, ""
    head = parts[0].lstrip("@")
    tid = int(head) if head.lstrip("-").isdigit() else None
    return tid, (parts[1].strip() if len(parts) > 1 else "")


def split_target(text: str, reply_id=None, single_arg: bool = False):
    """Like split_id_rest, but an admin who replied to a player's message may leave the id out.

    With a reply target: a first word that is not an id means "the replied player, this is the rest";
    for actions that take one number (single_arg) a lone word is that number, not an id.
    """
    tid, rest = split_id_rest(text)
    if reply_id is not None:
        parts = to_ascii_digits(text or "").split()
        if tid is None or (single_arg and len(parts) == 1):
            return reply_id, (text or "").strip()
    return tid, rest


def parse_amount(text: str, lo: int = 1, hi: int = 10 ** 9):
    """A positive whole number inside [lo, hi], or None."""
    raw = to_ascii_digits(text or "").strip().replace(",", "")
    if not raw.isdigit():
        return None
    n = int(raw)
    return n if lo <= n <= hi else None


def coerce_setting(default, raw: str):
    """Turn typed text into the type of the setting's default. Raises ValueError when it does not fit."""
    text = to_ascii_digits(raw or "").strip().lower()
    if isinstance(default, bool):
        if text in _BOOL_ON:
            return True
        if text in _BOOL_OFF:
            return False
        raise ValueError(raw)
    if isinstance(default, int):
        return int(float(text))
    if isinstance(default, float):
        return float(text)
    raise ValueError(raw)


def adjust_setting(default, old, op: str):
    """Step a numeric setting: d/u = -10% / +10%, d1/u1 = -1 / +1 (0.1 for floats), r = back to default.
    Booleans toggle on 't'. Never goes below zero for numbers."""
    if op == "r":
        return default
    if isinstance(default, bool):
        return (not old) if op == "t" else old
    if op in ("d", "u"):
        new = old * (1.1 if op == "u" else 0.9)
        if isinstance(old, int):
            new = int(round(new))
            if new == old:
                new = old + (1 if op == "u" else -1)
        return max(0, type(default)(new))
    if op in ("d1", "u1"):
        step = 1 if isinstance(old, int) else 0.1
        new = old + step if op == "u1" else old - step
        return max(0, type(default)(round(new, 4)) if isinstance(default, float) else int(new))
    return old


def page_bounds(total: int, page: int, size: int):
    """(start index, page count, clamped page). Empty lists give one empty page."""
    pages = max(1, -(-total // size))
    page = min(max(0, page), pages - 1)
    return page * size, pages, page


def role_ok(role: str, valid: set) -> str:
    """Role for `addadmin`: anything unknown falls back to 'admin'."""
    return role if role in valid else "admin"
