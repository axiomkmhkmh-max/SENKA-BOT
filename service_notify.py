"""Update notice: when the code on disk changes (new deploy), every player gets one message asking them to press /start.

The version is a hash of all .py files, so a redeploy with identical code stays silent. Progress is stored per user
(`users.notified_ver`), so a crash or restart in the middle of the broadcast simply resumes where it stopped."""
import asyncio
import hashlib
import logging
import os
import time

from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError, TelegramRetryAfter
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import settings
from database import acquire_lease, col
from security import make_cb
from service_log import log_event

log = logging.getLogger("senka.notify")
INSTANCE = os.urandom(6).hex()

# Fixed message: it never says what changed. Players only need to press /start so the update applies.
TEXT = {
    "fa": "🔄 <b>ربات آپدیت شد!</b>\n\nبرای اعمال آپدیت، همین حالا یک بار <b>/start</b> بزن (یا دکمه‌ی زیر را بزن). پیشرفتت کاملاً حفظ می‌شود.",
    "en": "🔄 <b>The bot has been updated!</b>\n\nTo apply the update, send <b>/start</b> once right now (or tap the button below). Your progress is fully kept.",
}
BTN = {"fa": "▶️ استارت", "en": "▶️ Start"}


def code_version() -> str:
    h = hashlib.sha1()
    root = os.path.dirname(os.path.abspath(__file__))
    for name in sorted(os.listdir(root)):
        if name.endswith(".py"):
            h.update(name.encode())
            with open(os.path.join(root, name), "rb") as f:
                h.update(f.read())
    return h.hexdigest()[:12]


async def _send(bot, u: dict, ver: str) -> bool:
    lang = u.get("lang") or "fa"
    lang = lang if lang in TEXT else "en"
    text = TEXT[lang]
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=BTN[lang], callback_data=make_cb("home", "", u["telegram_id"]))]])
    for _ in range(3):
        try:
            await bot.send_message(u["telegram_id"], text, reply_markup=kb)
            return True
        except TelegramRetryAfter as e:
            await asyncio.sleep(min(60, e.retry_after + 1))
        except TelegramForbiddenError:
            await col("users").update_one({"telegram_id": u["telegram_id"]}, {"$set": {"blocked_bot": True}})
            return False
        except TelegramAPIError:
            return False
    return False


async def broadcast(bot, ver: str):
    sent = failed = 0
    q = {"notified_ver": {"$ne": ver}, "blocked_bot": {"$ne": True}, "banned": {"$ne": True}}
    while True:
        batch = await col("users").find(q, {"telegram_id": 1, "lang": 1}).limit(200).to_list(200)
        if not batch:
            break
        for u in batch:
            ok = await _send(bot, u, ver)
            sent += ok
            failed += not ok
            await col("users").update_one({"telegram_id": u["telegram_id"]}, {"$set": {"notified_ver": ver}})
            await asyncio.sleep(0.06)  # ~16 msg/s, under Telegram's 30/s global limit
    return sent, failed


async def run(bot, stop: asyncio.Event):
    if not settings.notify_updates:
        return
    try:
        await asyncio.sleep(5)
        ver = code_version()
        doc = await col("settings").find_one({"_id": "update_notice"}) or {}
        if doc.get("ver") != ver:
            await col("settings").update_one({"_id": "update_notice"}, {"$set": {"ver": ver, "done": False, "at": int(time.time())}}, upsert=True)
        elif doc.get("done"):
            return
        if not await acquire_lease("update_notice", INSTANCE, 3600):
            return
        sent, failed = await broadcast(bot, ver)
        await col("settings").update_one({"_id": "update_notice"}, {"$set": {"done": True}})
        log.info("update notice %s: %s sent, %s failed", ver, sent, failed)
        log_event("sys", 0, f"پیام آپدیت (نسخه {ver}) فرستاده شد: {sent} موفق، {failed} ناموفق")
    except Exception:
        log.exception("update notice failed")
