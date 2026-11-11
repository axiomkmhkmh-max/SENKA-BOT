"""Background loop (single active instance via a DB lease): boss spawns, expiry,
auction settlement and PvP turn timeouts."""
import asyncio
import logging
import uuid

from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

import handlers_combat
from database import acquire_lease, col
from render import both, boss_text
from security import make_cb
from service_combat import pvp_timeouts
from service_economy import settle_listings
from service_world import due_groups, expire_bosses, group_doc, schedule_next, spawn_boss
from ui import Ctx

log = logging.getLogger("senka.sched")
INSTANCE = uuid.uuid4().hex


def boss_kb(sid: str):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⚔️ Attack / حمله", callback_data=make_cb("bh", sid, 0))]])


async def post_boss(bot, doc):
    g = await group_doc(doc["chat_id"])
    text = both(g.get("lang", "both"), lambda L: boss_text(L, doc))
    try:
        msg = await bot.send_message(doc["chat_id"], text, reply_markup=boss_kb(doc["_id"]))
        await col("boss_sessions").update_one({"_id": doc["_id"]}, {"$set": {"msg_id": msg.message_id}})
    except TelegramForbiddenError:
        await col("groups").update_one({"chat_id": doc["chat_id"]}, {"$set": {"blocked": True}})
        await col("boss_sessions").update_one({"_id": doc["_id"]}, {"$set": {"active": False}})
    except TelegramAPIError:
        log.exception("boss post failed")


async def tick(bot):
    await settle_listings()
    for doc, summary in await expire_bosses():
        g = await group_doc(doc["chat_id"])
        text = both(g.get("lang", "both"), lambda L: boss_text(L, doc, summary))
        try:
            if doc.get("msg_id"):
                await bot.edit_message_text(text, chat_id=doc["chat_id"], message_id=doc["msg_id"])
        except TelegramAPIError:
            pass
    for g in await due_groups():
        doc = await spawn_boss(g["chat_id"])
        await schedule_next(g["chat_id"])
        if doc:
            await post_boss(bot, doc)
    for doc, ev, outcome, forfeit in await pvp_timeouts():
        if not doc.get("msg_id"):
            continue
        ctx = Ctx(0, "en", doc["chat_id"], "supergroup", None, bot)
        gd = await group_doc(doc["chat_id"])
        final = handlers_combat._final(ctx, doc, outcome) if doc["state"]["done"] else None
        text, kb = await handlers_combat._pvp_panel(gd.get("lang", "both"), ctx, doc, ev, final)
        try:
            await bot.edit_message_text(text, chat_id=doc["chat_id"], message_id=doc["msg_id"], reply_markup=kb)
        except TelegramAPIError:
            pass


async def run(bot, stop: asyncio.Event):
    while not stop.is_set():
        try:
            if await acquire_lease("scheduler", INSTANCE, 45):
                await tick(bot)
        except Exception:
            log.exception("scheduler tick failed")
        try:
            await asyncio.wait_for(stop.wait(), timeout=15)
        except asyncio.TimeoutError:
            pass
