"""Bracket picture for the Gotei Trial, in the style of the Call of Duty Mobile tournament screen:
dark and gold, the entrants on both outer edges, every round closing in on the middle, a trophy for the champion,
and a "?" in every slot nobody has reached yet.

Pure drawing (Pillow only): no database, no Telegram. render_bracket() returns PNG bytes, or None when Pillow is not
installed (the tournament then simply runs without pictures).

Persian / Arabic names: Pillow's RAQM layout engine shapes them itself when libraqm is present; otherwise the
optional `arabic-reshaper` + `python-bidi` packages are used; otherwise the raw text is drawn.
"""
import io
import logging
import os
import unicodedata

from engine_tournament import UNKNOWN, bracket_columns

log = logging.getLogger("senka.tournament.render")

try:
    from PIL import Image, ImageDraw, ImageFont, features
except ImportError:  # the bot keeps running without pictures
    Image = None

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fonts")

# palette: black and old gold, like the game screen
BG_TOP, BG_BOT = (26, 22, 15), (8, 7, 5)
GOLD, GOLD_LIGHT, GOLD_DIM = (214, 176, 62), (250, 222, 120), (104, 86, 38)
TEXT, TEXT_DIM = (240, 232, 212), (128, 120, 102)
BOX, BOX_WIN, BOX_OUT, BOX_Q = (40, 36, 29), (66, 54, 22), (28, 26, 22), (34, 32, 28)
LINE_DIM = (78, 70, 52)

LABELS = {"preliminary": ("مقدماتی", "PRELIMINARY"), "academy_exam": ("امتحان آکادمی", "ACADEMY EXAM"),
          "seat_trial": ("آزمون درجه", "SEAT TRIAL"), "captains_assembly": ("مجلس کاپیتان‌ها", "CAPTAINS' ASSEMBLY")}
_FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

_font_cache: dict = {}
_raqm = None


def _has_raqm() -> bool:
    global _raqm
    if _raqm is None:
        try:
            _raqm = bool(features.check("raqm"))
        except Exception:
            _raqm = False
    return _raqm


def _font(size: int, bold: bool = True):
    key = (size, bold)
    if key not in _font_cache:
        path = os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")
        try:
            engine = ImageFont.Layout.RAQM if _has_raqm() else ImageFont.Layout.BASIC
            _font_cache[key] = ImageFont.truetype(path, size, layout_engine=engine)
        except Exception:
            try:
                _font_cache[key] = ImageFont.truetype(path, size)
            except Exception:
                log.warning("tournament font missing; using Pillow's default")
                _font_cache[key] = ImageFont.load_default()
    return _font_cache[key]


def _shape(text: str) -> str:
    """Text ready for ImageDraw: with RAQM it is left alone (the engine shapes and reorders it)."""
    if not text or _has_raqm():
        return text
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        return get_display(arabic_reshaper.reshape(text))
    except Exception:
        return text


def clean_name(name, limit: int = 24) -> str:
    """A name the bundled font can draw: letters, digits, marks and a little punctuation (no emoji or symbols)."""
    out = []
    for ch in str(name or ""):
        cat = unicodedata.category(ch)
        if "︀" <= ch <= "️":
            continue
        if cat[0] in "LNM" or ch in " ._-'‌":
            out.append(ch)
    s = " ".join("".join(out).split())
    return (s[:limit - 1] + "…") if len(s) > limit else (s or "Player")


def _fit(draw, text, font, max_w):
    t = _shape(text)
    if draw.textlength(t, font=font) <= max_w:
        return t
    while len(text) > 2:
        text = text[:-1]
        t = _shape(text.rstrip() + "…")
        if draw.textlength(t, font=font) <= max_w:
            return t
    return t


def _center_text(draw, xy, text, font, fill, anchor="mm"):
    draw.text(xy, _shape(text), font=font, fill=fill, anchor=anchor)


def round_label(players: int, fa: bool = True) -> str:
    """Header of the column whose `players` fighters are about to play."""
    key = "captains_assembly" if players <= 2 else "seat_trial" if players <= 4 else "academy_exam" if players <= 8 else "preliminary"
    return LABELS[key][0 if fa else 1]


def _gradient(w, h):
    img = Image.new("RGB", (w, h), BG_BOT)
    px = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(1, h - 1)
        px.line([(0, y), (w, y)], fill=tuple(int(BG_TOP[i] + (BG_BOT[i] - BG_TOP[i]) * t) for i in range(3)))
    glow = Image.new("RGB", (w, h), (0, 0, 0))  # a gold haze along the bottom edge, like the game screen
    gd = ImageDraw.Draw(glow)
    for k in range(120):
        a = int(70 * (1 - k / 120) ** 2)
        gd.line([(0, h - 1 - k), (w, h - 1 - k)], fill=(a, int(a * 0.8), int(a * 0.3)))
    from PIL import ImageChops
    return ImageChops.add(img, glow)


def _trophy(d, cx, cy, s=1.0):
    """A small gold cup, drawn with polygons (no image files needed)."""
    def P(pts):
        return [(cx + x * s, cy + y * s) for x, y in pts]
    d.polygon(P([(-46, -70), (46, -70), (40, -20), (22, 8), (-22, 8), (-40, -20)]), fill=GOLD, outline=GOLD_LIGHT)
    d.polygon(P([(-30, -64), (-8, -64), (-14, -22), (-24, -18)]), fill=GOLD_LIGHT)
    d.arc([cx - 78 * s, cy - 66 * s, cx - 34 * s, cy - 14 * s], 90, 270, fill=GOLD, width=max(3, int(7 * s)))
    d.arc([cx + 34 * s, cy - 66 * s, cx + 78 * s, cy - 14 * s], 270, 90, fill=GOLD, width=max(3, int(7 * s)))
    d.rectangle(P([(-8, 8), (8, 38)]), fill=GOLD)
    d.polygon(P([(-34, 38), (34, 38), (40, 56), (-40, 56)]), fill=GOLD, outline=GOLD_LIGHT)
    d.rectangle(P([(-44, 56), (44, 70)]), fill=GOLD_DIM)


def render_bracket(order, names, hist, seeds=None, title="GOTEI TRIAL", subtitle="", footer="", highlight_round=None):
    """order: round-one slots (uid or None for a bye); names: {str(uid) or uid: name}; hist: finished rounds
    (see engine_tournament.bracket_columns); seeds: {uid: seed number}. Returns PNG bytes, or None without Pillow."""
    if Image is None:
        return None
    names = {str(k): v for k, v in (names or {}).items()}
    seeds = {str(k): v for k, v in (seeds or {}).items()}
    cols, scores = bracket_columns(order, hist or [])
    size = len(order)
    rounds = len(cols) - 1                     # columns per side
    half = size // 2                           # entrants on one side

    box_w, box_h, gap_x = 256, 40, 40
    pitch = max(box_h + 10, min(104, 660 // half))
    top = 200
    body_h = pitch * half
    W = 2 * (40 + rounds * box_w + (rounds - 1) * gap_x + gap_x) + 300
    H = top + body_h + 150
    img = _gradient(W, H)
    d = ImageDraw.Draw(img, "RGBA")

    # ---- header
    _center_text(d, (W // 2, 62), title, _font(54), GOLD_LIGHT)
    d.line([(W // 2 - 300, 100), (W // 2 + 300, 100)], fill=GOLD_DIM, width=3)
    if subtitle:
        _center_text(d, (W // 2, 132), clean_name(subtitle, 90), _font(26, False), TEXT)

    def col_x(c, left):
        x = 40 + c * (box_w + gap_x)
        return x if left else W - x - box_w

    def cy(c, j):                              # vertical centre of box j in column c, counted inside one half
        return top + pitch * (2 ** c) * (j + 0.5)

    def uid_of(c, side_left, j):
        n = len(cols[c])
        idx = j if side_left else n // 2 + j
        return cols[c][idx], idx

    def label_for(v):
        if v == UNKNOWN:
            return None
        if v is None:
            return ""
        return clean_name(names.get(str(v), v), 24)

    def draw_box(x, y, v, state):
        """state: 'win' (advanced or champion), 'out' (eliminated), 'live', 'q' (unknown)"""
        fill = {"win": BOX_WIN, "out": BOX_OUT, "live": BOX, "q": BOX_Q}[state]
        edge = {"win": GOLD, "out": (48, 44, 36), "live": GOLD_DIM, "q": (58, 54, 44)}[state]
        d.rectangle([x, y - box_h / 2, x + box_w, y + box_h / 2], fill=fill, outline=edge, width=2)
        d.rectangle([x, y - box_h / 2, x + 5, y + box_h / 2], fill=edge)
        txt = label_for(v)
        if txt is None:
            _center_text(d, (x + box_w / 2, y), "؟", _font(30), (96, 90, 76))
            return
        if txt == "":
            _center_text(d, (x + box_w / 2, y), "BYE", _font(20), (86, 80, 66))
            return
        seed = seeds.get(str(v))
        tx0 = x + 14
        if seed is not None:
            d.text((x + 12, y), f"{seed}", font=_font(17), fill=GOLD if state != "out" else TEXT_DIM, anchor="lm")
            tx0 = x + 44
        color = {"win": GOLD_LIGHT, "live": TEXT, "out": TEXT_DIM}[state]
        d.text((tx0, y), _fit(d, txt, _font(22), box_w - (tx0 - x) - 10), font=_font(22), fill=color, anchor="lm")

    def state_of(c, v, parent):
        """advanced / eliminated / waiting, by looking at the next column."""
        if v == UNKNOWN:
            return "q"
        if v is None:
            return "out"
        if parent == UNKNOWN:
            return "live"
        return "win" if parent == v else "out"

    # ---- connectors first (boxes are drawn over their ends)
    for left in (True, False):
        for c in range(rounds - 1):
            n = len(cols[c]) // 2
            for j in range(n // 2):
                for k in (0, 1):
                    child_j = 2 * j + k
                    v, idx = uid_of(c, left, child_j)
                    parent_v, _ = uid_of(c + 1, left, j)
                    x0 = col_x(c, left) + (box_w if left else 0)
                    xp = col_x(c + 1, left) + (0 if left else box_w)
                    xm = (x0 + xp) / 2
                    y0, yp = cy(c, child_j), cy(c + 1, j)
                    won = v not in (UNKNOWN, None) and parent_v == v
                    col_ = GOLD if won else LINE_DIM
                    w_ = 4 if won else 2
                    d.line([(x0, y0), (xm, y0), (xm, yp), (xp, yp)], fill=col_, width=w_)
                sc = scores[c][(0 if left else len(cols[c + 1]) // 2) + j]
                if sc and sc != "bye":
                    xm = (col_x(c, left) + (box_w if left else 0) + col_x(c + 1, left) + (0 if left else box_w)) / 2
                    _center_text(d, (xm, cy(c + 1, j)), sc, _font(17), GOLD_LIGHT)
    # finalists to the champion box
    fy = cy(rounds - 1, 0)
    cx0 = W // 2
    champ = cols[-1][0]
    for left in (True, False):
        v, _ = uid_of(rounds - 1, left, 0)
        xe = col_x(rounds - 1, left) + (box_w if left else 0)
        won = champ not in (UNKNOWN, None) and champ == v
        d.line([(xe, fy), (cx0 + (-box_w / 2 if left else box_w / 2), fy)], fill=GOLD if won else LINE_DIM, width=4 if won else 2)

    # ---- boxes + column headers
    for left in (True, False):
        for c in range(rounds):
            x = col_x(c, left)
            n = len(cols[c]) // 2
            hdr_y = top - 52
            active = highlight_round is not None and c == highlight_round
            _center_text(d, (x + box_w / 2, hdr_y), round_label(len(cols[c])), _font(21), GOLD_LIGHT if active else GOLD)
            en = round_label(len(cols[c]), False) + " · " + str(len(cols[c]))
            _center_text(d, (x + box_w / 2, hdr_y + 26), en, _font(14, False), TEXT if active else TEXT_DIM)
            for j in range(n):
                v, idx = uid_of(c, left, j)
                if c + 1 < len(cols) - 0 and c < rounds - 1:
                    parent_v, _ = uid_of(c + 1, left, j // 2)
                else:
                    parent_v = cols[-1][0]
                draw_box(x, cy(c, j), v, state_of(c, v, parent_v))

    # ---- centre: trophy + champion
    _trophy(d, cx0, fy - 150, 1.15)
    _center_text(d, (cx0, fy - 62), "CHAMPION · قهرمان", _font(19), GOLD)
    draw_box(cx0 - box_w / 2, fy, champ, "q" if champ == UNKNOWN else "win")

    if footer:
        _center_text(d, (W // 2, H - 56), clean_name(footer, 90), _font(24, False), GOLD)
    _center_text(d, (W // 2, H - 24), "SENKA  ·  GOTEI TRIAL", _font(15, False), (150, 130, 80))
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "PNG", optimize=True)
    return buf.getvalue()
