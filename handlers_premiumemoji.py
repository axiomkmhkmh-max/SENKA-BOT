"""Teach the bot premium emoji. An admin (level 60+) sends the bot, in private chat, either
  - a message containing premium emoji  -> the bot learns {normal emoji: id} from each one, or
  - a link to an emoji pack (t.me/addemoji/NAME) -> the bot learns every emoji of the pack that it does not have yet
    (add the word  force  after the link to replace ids it already has).
Everything is saved in MongoDB and active at once, so no restart is needed. Non-admins are ignored (their messages flow on)."""
import logging
import re

from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.types import Message

import premium_emoji as PE
from handlers_admin import admin_level, alog
from handlers_admincmd import router

log = logging.getLogger("senka.premiumemoji")
MIN_LEVEL = 60
_PACK_RE = re.compile(r"(?:https?://)?t\.me/addemoji/([A-Za-z0-9_]+)", re.I)


def _entities(m: Message):
    return m.entities or m.caption_entities or []


def _has_custom(m: Message) -> bool:
    return m.chat.type == "private" and any(en.type == "custom_emoji" for en in _entities(m))


def _has_pack(m: Message) -> bool:
    return m.chat.type == "private" and bool(m.text and _PACK_RE.search(m.text))


async def _admin_or_skip(m: Message):
    if m.from_user is None or m.from_user.is_bot or await admin_level(m.from_user.id) < MIN_LEVEL:
        raise SkipHandler


@router.message(_has_custom)
async def learn_from_message(m: Message):
    await _admin_or_skip(m)
    text = m.text or m.caption or ""
    found = {}
    for en in _entities(m):
        if en.type == "custom_emoji" and en.custom_emoji_id:
            alt = en.extract_from(text)  # aiogram handles Telegram's UTF-16 offsets
            if alt:
                found[alt] = en.custom_emoji_id
    if not found:
        return await m.answer("⚠️ ایموجی‌ای پیدا نشد.")
    changed = await PE.save_many(found, overwrite=True)
    await alog(m.from_user.id, "premium_emoji", None, None, changed, " ".join(found)[:150])
    await m.answer(f"✅ {len(found)} ایموجی خوانده شد ({changed} مورد جدید/تغییرکرده): {' '.join(found)}\n"
                   f"کل ایموجی‌های پرمیوم ربات: {PE.mapped_count()}")


@router.message(_has_pack)
async def learn_from_pack(m: Message):
    await _admin_or_skip(m)
    force = "force" in m.text.lower() or "جایگزین" in m.text
    lines = []
    for name in dict.fromkeys(_PACK_RE.findall(m.text)):
        try:
            st = await m.bot.get_sticker_set(name)
        except Exception as e:
            lines.append(f"⚠️ {name}: {str(e)[:80]}")
            continue
        found = {s.emoji: s.custom_emoji_id for s in st.stickers if s.custom_emoji_id and s.emoji}
        changed = await PE.save_many(found, overwrite=force)
        await alog(m.from_user.id, "premium_pack", None, None, changed, name)
        lines.append(f"✅ {st.title}: {len(found)} ایموجی، {changed} مورد جدید" + (" (با جایگزینی)" if force else ""))
    await m.answer("\n".join(lines) + f"\nکل ایموجی‌های پرمیوم ربات: {PE.mapped_count()}")
