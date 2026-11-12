"""Log channel: every player action is queued (non-blocking), stored in MongoDB (`action_logs`, 14-day TTL)
and posted to the Telegram log channel in small batches so Telegram's flood limits are never hit."""
import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone

from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter

from config import settings
from database import col, game_settings
from i18n import esc

log = logging.getLogger("senka.log")
TEHRAN = timezone(timedelta(hours=3, minutes=30))
ICONS = {"reg": "🆕", "act": "🔘", "txt": "💬", "market": "🛒", "shop": "🏪", "drop": "🎁", "art": "🔱", "lvl": "⬆️", "pvp": "🥊",
         "gacha": "🎰", "admin": "🛡️", "boss": "👹", "econ": "💰", "bounty": "🎯", "sys": "⚙️"}

# Persian label for every button/word the game has. Unknown codes fall back to the code itself.
LABELS = {
    "home": "پنل اصلی", "menu2": "منوی بیشتر", "prof": "پروفایل", "upg": "ارتقای استت", "map": "نقشه", "tr": "سفر", "exp": "گشت",
    "rnk": "رتبه‌بندی", "dly": "جایزه روزانه", "qst": "ماموریت‌ها", "qc": "دریافت جایزه ماموریت", "mgm": "مینی‌گیم", "mga": "پاسخ مینی‌گیم",
    "gld": "جوخه", "gj": "ورود به جوخه", "gll": "خروج از جوخه", "gdp": "واریز به جوخه", "glc": "ساخت جوخه", "set": "تنظیمات",
    "cmd": "لیست دستورات", "hlp": "راهنما", "lang": "تغییر زبان", "bag": "کوله", "iv": "مشاهده آیتم", "eq": "تجهیز", "ueq": "درآوردن تجهیز",
    "us": "استفاده از آیتم", "sl": "فروش به فروشگاه", "ml": "ثبت آگهی بازار", "mlp": "تایید آگهی بازار", "mkt": "بازار", "mkb": "آگهی‌های بازار",
    "mka": "حراج‌ها", "mkv": "مشاهده آگهی", "mkby": "خرید از بازار", "mkav": "مشاهده حراج", "abd": "پیشنهاد در حراج", "mkm": "آگهی‌های من",
    "mkc": "لغو آگهی", "shp": "فروشگاه اوراهارا", "sv": "مشاهده کالای فروشگاه", "sb": "خرید از فروشگاه", "gch": "احضار", "gp": "احضار انجام شد",
    "pty": "تیم", "pt": "تغییر تیم", "frg": "فورج", "bt": "منوی نبرد", "bs": "شروع نبرد", "bn": "مرحله بعد", "ba": "حرکت در نبرد",
    "dgn": "دانجن", "dgd": "سختی دانجن", "dgs": "شروع دانجن", "dua": "قبول دوئل", "dud": "رد دوئل", "pa": "حرکت در دوئل", "bh": "ضربه به باس",
    "bossinfo": "اطلاعات باس", "wrd": "دنیای زنده", "chr": "تاریخچه جهان", "evt": "رویداد جهانی", "evk": "مشارکت در رویداد", "ter": "قلمرو",
    "hre": "اینجا چه خبر", "aid": "کمک به بازیکن", "trc": "ردپا", "bty": "باونتی", "btn": "ثبت باونتی", "btp": "پرداخت باونتی", "ssn": "فصل",
    "crf": "ساخت", "crp": "ساخت معجون", "crk": "ساخت کلید", "crw": "مشاهده دستور ساخت", "crd": "ساخت آیتم", "crl": "لیست ساخت",
    "crx": "ساخت آیتم", "crv": "مشاهده تمپر", "crt": "تمپر", "evo": "تکامل", "evs": "شروع آزمون تکامل", "eqp": "یادگارها و همراهان",
    "rlc": "یادگارها", "rla": "هم‌سازی یادگار", "rlr": "رهاسازی یادگار", "rel": "یادگارها", "urel": "درآوردن یادگار", "cos": "کاسمتیک",
    "cow": "پوشیدن کاسمتیک", "cor": "درآوردن کاسمتیک", "ucos": "درآوردن کاسمتیک", "pet": "همراه", "pea": "فعال‌سازی همراه", "pta": "فعال‌سازی همراه",
    "twr": "برج روح", "twg": "صعود برج", "twl": "رتبه برج", "dsp": "اعزام", "dsm": "انتخاب اعزام", "dss": "شروع اعزام", "dsc": "دریافت اعزام",
    "whl": "چرخ اوراهارا", "whs": "چرخاندن چرخ", "sat": "درجه گوتی", "sac": "جایزه درجه", "inr": "دنیای درون", "inc": "انتخاب دنیای درون",
    "begin": "شروع ثبت‌نام", "gen": "انتخاب جنسیت", "race": "انتخاب نژاد", "st": "تنظیم استت", "zp": "انتخاب زانپاکتو", "adm": "پنل ادمین",
    "art": "آرتیفکت من", "arr": "ثبت‌نامه آرتیفکت‌ها", "axm": "بازار آرتیفکت", "axb": "مرور بازار آرتیفکت", "axv": "مشاهده آگهی آرتیفکت",
    "axy": "خرید آرتیفکت", "axl": "گذاشتن آرتیفکت در بازار", "axp": "تایید قیمت آرتیفکت", "axc": "لغو آگهی آرتیفکت", "axr": "رها کردن آرتیفکت",
    "axk": "تایید رها کردن آرتیفکت", "axn": "آگهی آرتیفکت من",
}
# pure navigation: logged only when `log_nav` is on
NAV = {"home", "menu2", "mg", "div", "dvi", "hlf", "adm", "adw", "adx", "ads", "adk", "adu", "adn", "adb", "adc", "adz", "adl", "ada", "adt", "noop", "cmd", "hlp", "lang", "set", "bag", "iv", "mkt", "mkb", "mka", "mkv", "mkav", "mkm", "shp", "sv", "bt", "map", "rnk",
       "wrd", "chr", "evt", "ter", "hre", "ssn", "crf", "crl", "crw", "crv", "eqp", "rlc", "rel", "cos", "pet", "pty", "twr", "twl", "dsp", "dsm", "whl", "sat",
       "inr", "gld", "qst", "mgm", "gch", "ml", "dgn", "dgd", "bossinfo", "prof", "arr", "axm", "axb", "axv", "axn", "art", "evo", "bty", "btn", "glc", "upg"}

_q: asyncio.Queue = asyncio.Queue(maxsize=5000)
_names: dict = {}
_off_until = 0.0
_warned = False


def log_event(kind: str, uid: int = 0, text: str = "", **extra):
    """Queue one log line. Never blocks and never raises, so it is safe to call anywhere."""
    try:
        _q.put_nowait({"at": time.time(), "kind": kind, "uid": int(uid or 0), "text": str(text)[:400], **extra})
    except Exception:
        pass


def log_action(uid: int, code: str, arg: str = "", nav: bool = False):
    if code in NAV and not nav:
        return
    log_event("act", uid, f"{LABELS.get(code, code)}" + (f" ‹{arg}›" if arg and len(arg) <= 24 and code in ("sb", "mkby", "axy", "ml", "mlp", "us", "eq", "gp") else ""), code=code)


def log_text(uid: int, intent: str, chat_type: str = "private"):
    log_event("txt", uid, f"{intent}" + ("" if chat_type == "private" else " (گروه)"))


async def _who(uid: int) -> str:
    hit = _names.get(uid)
    if hit and time.monotonic() - hit[1] < 600:
        return hit[0]
    ch = await col("characters").find_one({"user_id": uid}, {"name": 1, "level": 1})
    u = await col("users").find_one({"telegram_id": uid}, {"username": 1, "first_name": 1})
    name = (ch or {}).get("name") or (u or {}).get("first_name") or "?"
    tag = f" @{u['username']}" if u and u.get("username") else ""
    lvl = f" Lv{ch['level']}" if ch else ""
    s = f"<b>{esc(name)}</b>{esc(tag)}{lvl} <code>{uid}</code>"
    _names[uid] = (s, time.monotonic())
    if len(_names) > 5000:
        _names.clear()
    return s


async def _render(ev: dict) -> str:
    ts = datetime.fromtimestamp(ev["at"], TEHRAN).strftime("%H:%M:%S")
    who = await _who(ev["uid"]) if ev["uid"] else "<b>SYSTEM</b>"
    return f"{ICONS.get(ev['kind'], '▫️')} <code>{ts}</code> {who} — {esc(ev['text'])}"


def _target():
    ch = (settings.log_channel or "").strip()
    if not ch:
        return None
    return int(ch) if ch.lstrip("-").isdigit() else ch


async def _post(bot, text: str):
    global _off_until, _warned
    target = _target()
    if target is None:
        return
    for attempt in range(2):
        try:
            await bot.send_message(target, text)
            _warned = False
            return
        except TelegramRetryAfter as e:
            await asyncio.sleep(min(60, e.retry_after + 1))
        except (TelegramForbiddenError, TelegramBadRequest) as e:
            _off_until = time.time() + 300
            if not _warned:
                log.warning("log channel %s unreachable (%s). Add the bot as an admin of the channel with permission to post.", target, e)
                _warned = True
            return
        except TelegramAPIError as e:
            log.warning("log post failed: %s", e)
            return


async def _flush(bot, batch: list):
    st = await game_settings()
    if not st.get("log_enabled", True):
        return
    exp = datetime.now(timezone.utc) + timedelta(days=14)
    try:
        await col("action_logs").insert_many([{k: v for k, v in ev.items()} | {"expire_at": exp} for ev in batch], ordered=False)
    except Exception:
        log.exception("could not store action logs")
    if time.time() < _off_until or _target() is None:
        return
    cap = 120
    shown, omitted = batch[:cap], max(0, len(batch) - cap)
    lines = [await _render(ev) for ev in shown]
    if omitted:
        lines.append(f"… +{omitted} رویداد دیگر (در دیتابیس ذخیره شد)")
    chunk, size = [], 0
    for ln in lines:
        if size + len(ln) > 3700 and chunk:
            await _post(bot, "\n".join(chunk))
            await asyncio.sleep(3.2)
            chunk, size = [], 0
        chunk.append(ln)
        size += len(ln) + 1
    if chunk:
        await _post(bot, "\n".join(chunk))
        await asyncio.sleep(3.2)


async def run(bot, stop: asyncio.Event):
    """Collector loop: waits for events, lets a short window fill up, then posts them as one message."""
    while not stop.is_set():
        try:
            first = await asyncio.wait_for(_q.get(), timeout=2)
        except asyncio.TimeoutError:
            continue
        except Exception:
            log.exception("log queue failed")
            continue
        batch = [first]
        try:
            await asyncio.sleep(2.5)
            while len(batch) < 400:
                batch.append(_q.get_nowait())
        except asyncio.QueueEmpty:
            pass
        try:
            await _flush(bot, batch)
        except Exception:
            log.exception("log flush failed")
    # final drain on shutdown
    rest = []
    while not _q.empty() and len(rest) < 400:
        rest.append(_q.get_nowait())
    if rest:
        try:
            await _flush(bot, rest)
        except Exception:
            pass
