"""Keep group chats readable: the bot's short, transient replies (raid hits, spawns, status lines) remove themselves
after a while, so a long fight does not push the chat up with a wall of identical lines.

Only use this for messages nobody needs to scroll back to. Results that matter (raid settled, boss killed) stay.
"""
import asyncio
import logging

log = logging.getLogger(__name__)


async def _delete_later(msg, delay: int) -> None:
    await asyncio.sleep(delay)
    try:
        await msg.delete()
    except Exception:  # already deleted, too old, or no delete rights: nothing to do
        log.debug("auto-delete skipped", exc_info=True)


async def reply_tidy(message, text: str, delay: int = 120, **kw):
    """Reply to `message` and schedule the reply to delete itself after `delay` seconds."""
    sent = await message.reply(text, **kw)
    asyncio.create_task(_delete_later(sent, delay))
    return sent
