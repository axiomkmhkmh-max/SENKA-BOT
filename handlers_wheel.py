"""Urahara's wheel: the panel (`whl`) and the animated spin (`whs`).

The game logic lives in service_extras.wheel_state / wheel_spin (daily free spin, paid extra spins, prizes).
This module only draws it: the wheel scrolls through a few frames that slow down and stop on the real prize.
The prize is decided by the service BEFORE the animation starts, so the animation can never change the result
and a failed frame edit (flood limit, deleted message) never loses or repeats a prize."""
import asyncio
import logging

from aiogram.exceptions import TelegramBadRequest

from data_extras import WHEEL
from fmt import nm
from i18n import esc, fnum
from service_extras import wheel_spin, wheel_state
from ui import SEP, Out, action, head, nav

log = logging.getLogger("senka.wheel")

SPIN_STEPS = (7, 5, 3, 2, 1, 0)            # how many slots before the stop each frame shows
FRAME_DELAYS = (0.45, 0.5, 0.6, 0.75, 0.95)  # pause after each non-final frame (the wheel slows down)


def T(ctx, fa, en):
    return fa if ctx.lang == "fa" else en


def wheel_frame(center: int, spinning: bool = True) -> str:
    """Five prize icons with the one under the pointer framed; pure function (no Telegram), easy to test."""
    icons = [w[2] for w in WHEEL]
    n = len(icons)
    cells = []
    for k in range(-2, 3):
        icon = icons[(center + k) % n]
        cells.append(f"【{icon}】" if k == 0 else icon)
    pointer = "🔻" if spinning else "⭐"
    return f"{pointer}\n{'  '.join(cells)}\n{'🔺' if spinning else '⭐'}"


def frame_centers(target: int, n: int) -> list:
    """Slot index shown under the pointer in each frame; the last one is always the real prize."""
    return [(target - off) % n for off in SPIN_STEPS]


def _prize_lines(ctx, res: dict) -> str:
    L = ctx.lang
    out = []
    if res.get("coins"):
        out.append(f"🪙 +{fnum(res['coins'], L)}")
    if res.get("xp"):
        out.append(f"✨ +{fnum(res['xp'], L)} XP")
    if res.get("energy"):
        out.append(f"⚡ +{fnum(res['energy'], L)} " + T(ctx, "انرژی", "energy"))
    if res.get("item"):
        out.append(f"🎁 {esc(str(nm(res['item'], L)))}")
    return "\n".join(out)


def _spin_row(ctx, st: dict):
    if st["free"] > 0:
        return [(T(ctx, "🎡 چرخش رایگان", "🎡 Free spin"), "whs", "")]
    if st["extra"] > 0:
        return [(T(ctx, f"🎡 چرخش ({fnum(st['cost'], ctx.lang)} 🪙)", f"🎡 Spin ({fnum(st['cost'], ctx.lang)} 🪙)"), "whs", "")]
    return None


def _state_line(ctx, st: dict) -> str:
    L = ctx.lang
    if st["free"] > 0:
        return T(ctx, "🎁 یک چرخش رایگان امروز داری!", "🎁 You have a free spin today!")
    if st["extra"] > 0:
        return T(ctx, f"🪙 چرخش اضافه: {fnum(st['extra'], L)} بار باقی‌مانده، هر بار {fnum(st['cost'], L)} سکه",
                 f"🪙 Extra spins left: {fnum(st['extra'], L)}, {fnum(st['cost'], L)} coins each")
    return T(ctx, "⏳ چرخش‌های امروز تمام شد. فردا برگرد!", "⏳ No spins left today. Come back tomorrow!")


@action("whl")
async def wheel_panel(ctx, arg):
    st = await wheel_state(ctx.uid)
    body = (T(ctx, "گردونه را بچرخان و جایزه‌ات را بگیر.\nسکه، تجربه، انرژی، آیتم و گاهی جکپات!",
              "Spin the wheel and win a prize.\nCoins, XP, energy, items, and sometimes the jackpot!")
            + "\n\n" + wheel_frame(0, spinning=False) + "\n\n" + _state_line(ctx, st))
    rows = []
    row = _spin_row(ctx, st)
    if row:
        rows.append(row)
    rows.append(nav(ctx, ("mg", "fun")))
    return Out(head(ctx, "ttl_whl") + body, rows)


async def _show(ctx, text: str):
    """One animation frame: edit the panel message, ignoring harmless Telegram refusals."""
    try:
        await ctx.message.edit_text(text, reply_markup=None)
        return True
    except TelegramBadRequest as e:
        if "not modified" not in str(e):
            log.warning("wheel frame failed: %s", e)
        return False
    except Exception:
        log.exception("wheel frame crashed")
        return False


@action("whs")
async def wheel_spin_cb(ctx, arg):
    status, res = await wheel_spin(ctx.uid)
    if status != "ok":
        msgs = {
            "wait": T(ctx, "⏳ یک لحظه صبر کن.", "⏳ One moment."),
            "used": T(ctx, "⏳ چرخش امروزت را زده‌ای.", "⏳ You already spun today."),
            "limit": T(ctx, "⏳ چرخش‌های اضافه‌ی امروز تمام شد.", "⏳ No extra spins left today."),
            "funds": T(ctx, "🪙 سکه‌ی کافی نداری.", "🪙 Not enough coins."),
        }
        return Out(alert=msgs.get(status, T(ctx, "⚠️ نشد. دوباره تلاش کن.", "⚠️ Failed. Try again.")))

    # the prize is already paid: from here on everything is only drawing
    ids = [w[0] for w in WHEEL]
    target = ids.index(res["id"]) if res["id"] in ids else 0
    can_animate = ctx.cb is not None and ctx.message is not None
    if can_animate:
        try:
            await ctx.cb.answer()  # stop the button's loading spinner right away
        except Exception:
            pass
        title = head(ctx, "ttl_whl") + T(ctx, "🎡 در حال چرخش...", "🎡 Spinning...") + "\n\n"
        centers = frame_centers(target, len(WHEEL))
        for c, delay in zip(centers[:-1], FRAME_DELAYS):
            if not await _show(ctx, title + wheel_frame(c)):
                break
            await asyncio.sleep(delay)

    st = await wheel_state(ctx.uid)
    icon = res.get("icon", "🎁")
    name = esc(res["fa"] if ctx.lang == "fa" else res["en"])
    big = res["id"] in ("jackpot", "relic", "coins_l")
    head_line = (T(ctx, "🎉🎉 ", "🎉🎉 ") if res["id"] == "jackpot" else "") + f"{icon} <b>{name}</b>"
    text = (head(ctx, "ttl_whl") + wheel_frame(target, spinning=False) + "\n\n" + head_line + "\n" + SEP + "\n"
            + (_prize_lines(ctx, res) or T(ctx, "—", "—")) + ("\n\n" + T(ctx, "✨ جایزه‌ی بزرگ!", "✨ Big win!") if big and res["id"] != "jackpot" else "")
            + "\n\n" + _state_line(ctx, st))
    rows = []
    row = _spin_row(ctx, st)
    if row:
        rows.append(row)
    rows.append(nav(ctx, ("mg", "fun")))
    return Out(text, rows)
