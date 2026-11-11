"""Shared UI primitives: context, output, signed inline keyboards, registry."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from i18n import t
from security import make_cb

REGISTRY: dict = {}
SEP = "━━━━━━━━━━━━━━"


def action(code: str):
    def deco(fn):
        REGISTRY[code] = fn
        return fn
    return deco


class Ctx:
    def __init__(self, uid, lang, chat_id, chat_type, user, bot, message=None, cb=None):
        self.uid, self.lang, self.chat_id, self.chat_type = uid, lang or "en", chat_id, chat_type
        self.user, self.bot, self.message, self.cb = user, bot, message, cb

    def t(self, key, **kw):
        return t(self.lang, key, **kw)

    @property
    def private(self):
        return self.chat_type == "private"


class Out:
    """text/rows -> edit (or send when new=True). alert -> popup answer."""
    def __init__(self, text="", rows=None, alert=None, new=False):
        self.text, self.rows, self.alert, self.new = text, rows, alert, new


def head(ctx: Ctx, title_key: str) -> str:
    return f"⚔️ <b>𝖲𝖤𝖭𝖪𝖠</b> | <b>{ctx.t(title_key)}</b>\n{SEP}\n"


def markup(ctx: Ctx, rows):
    out = []
    for row in rows or []:
        line = []
        for b in row:
            label, code = b[0], b[1]
            arg = b[2] if len(b) > 2 else ""
            pub = b[3] if len(b) > 3 else False
            line.append(InlineKeyboardButton(text=label, callback_data=make_cb(code, str(arg), 0 if pub else ctx.uid)))
        out.append(line)
    return InlineKeyboardMarkup(inline_keyboard=out) if out else None


def nav(ctx: Ctx, back=None):
    """Back bottom-left, Home bottom-right."""
    row = []
    if back:
        row.append((ctx.t("b_back"), back[0], back[1] if len(back) > 1 else ""))
    row.append((ctx.t("b_home"), "home", ""))
    return row


def pager(ctx: Ctx, code: str, page: int, total_pages: int, extra: str = ""):
    row = []
    if page > 0:
        row.append(("◀️", code, f"{page - 1}{extra}"))
    if page < total_pages - 1:
        row.append(("▶️", code, f"{page + 1}{extra}"))
    return row


def chunk(seq, size):
    return [seq[i:i + size] for i in range(0, len(seq), size)]


INPUTS: dict = {}


def input_handler(kind: str):
    """Register a handler for a pending free-text answer (e.g. a guild name)."""
    def deco(fn):
        INPUTS[kind] = fn
        return fn
    return deco
