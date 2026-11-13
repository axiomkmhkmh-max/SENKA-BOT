"""Background loop (single active instance via a DB lease): boss spawns, expiry,
auction settlement and PvP turn timeouts."""
import asyncio
import logging
import time
import uuid

from pymongo import ReturnDocument

from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError
from aiogram.types import InlineKeyboardMarkup

import handlers_combat
import handlers_drops
import handlers_world
from database import acquire_lease, col, game_settings, try_cooldown
from service_combat import pvp_timeouts
from service_drops import art_reconcile, art_settle, expire_drops, typing_expire
from service_hollowraid import quincy_expire, quincy_tick
from service_economy import settle_listings
from service_interact import expire_bounties
from service_world import active_boss, boss_due, expire_bosses, group_doc, spawn_boss
from service_worldstate import tick as world_tick
from ui import Ctx

log = logging.getLogger("senka.sched")
INSTANCE = uuid.uuid4().hex


async def tick(bot):
    await settle_listings()
    await expire_bounties()
    await art_settle()
    for d in await expire_drops():
        await handlers_drops.announce_expired(bot, d)
    if not await try_cooldown("art_reconcile", 600):
        await art_reconcile()
    # ---- the living world: drift, events, territories, season ----
    res = await world_tick()
    if res["event_started"]:
        await handlers_world.announce_event_start(bot, res["event_started"])
    if res["event_ended"]:
        await handlers_world.announce_event_end(bot, res["event_ended"])
    if res["terr"]:
        await handlers_world.announce_territories(bot, res["terr"])
    if res["season"]:
        await handlers_world.announce_season(bot, res["season"])
    # ---- the single global boss ----
    for doc, summary in await expire_bosses():
        if doc.get("scope") == "global":
            await handlers_world.end_global_boss(bot, doc, summary)
    cur = await active_boss()
    if cur is None and await boss_due():
        doc = await spawn_boss()
        if doc:
            await handlers_world.post_global_boss(bot, doc)
    elif cur is not None:
        st = await game_settings()
        now = int(time.time())
        hit = await col("boss_sessions").find_one_and_update({"_id": cur["_id"], "active": True, "refresh_at": {"$lte": now - int(st["boss_refresh_seconds"])}},
                                                              {"$set": {"refresh_at": now}}, return_document=ReturnDocument.AFTER)
        if hit:
            await handlers_world.refresh_global_boss(bot, hit)
    # --- NEW BLEACH VIRAL SYSTEM: Quincy invasion + unwon typing races ---
    try:
        for doc in await quincy_tick():
            await handlers_world.post_quincy(bot, doc)
        for doc in await quincy_expire():
            await handlers_world.end_quincy_lost(bot, doc)
        for d in await typing_expire():
            await handlers_drops.announce_typing_expired(bot, d)
    except Exception:
        log.exception("viral systems tick failed")
    for doc, ev, outcome, forfeit in await pvp_timeouts():
        if not doc.get("msg_id"):
            continue
        ctx = Ctx(0, "en", doc["chat_id"], "supergroup", None, bot)
        gd = await group_doc(doc["chat_id"])
        final = handlers_combat._final(ctx, doc, outcome) if doc["state"]["done"] else None
        text, kb = await handlers_combat._pvp_panel(__import__("render").glang(gd), ctx, doc, ev, final)
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
