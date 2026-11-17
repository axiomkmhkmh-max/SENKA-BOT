"""One shared pace for every bulk send (broadcasts, notices, group announcements).

Telegram allows a bot about 30 messages per second in total. Several broadcast loops used to run side by side
(update notice, race-weapon notice, stat-respec notice, group alerts), each at ~16-20 per second. Together they went
past the limit, Telegram answered with flood waits, and the waits hit the bot's normal replies too: players saw
replies arrive several seconds late. Every bulk sender now takes a turn here, so all of them together stay near
BULK_PER_SEC and the rest of the budget is always free for replies to players."""
import asyncio
import time

BULK_PER_SEC = 12
_lock = asyncio.Lock()
_next = 0.0


async def bulk_slot():
    """Wait for this sender's turn. Replaces the old per-loop `asyncio.sleep(0.05)`."""
    global _next
    async with _lock:
        now = time.monotonic()
        wait = _next - now
        _next = max(now, _next) + 1.0 / BULK_PER_SEC
    if wait > 0:
        await asyncio.sleep(wait)
