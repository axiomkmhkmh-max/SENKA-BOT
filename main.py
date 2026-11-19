"""Entry point: DB, catalog seed, health endpoint, scheduler, long polling."""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeAllGroupChats, MenuButtonCommands
from aiohttp import web

from config import settings, validate_settings
from data_bosses import BOSSES
from data_chars import CHARS
from data_items import ALL, ITEMS
from data_misc import QUESTS
from data_weapons import WEAPONS
from database import bulk_upsert, close_db, col, connect_db, ping

log = logging.getLogger("senka")


async def seed():
    """Mirror static catalogs into MongoDB (for inspection/analytics) and apply admin overrides."""
    await bulk_upsert("items_catalog", [dict(x) for x in ITEMS])
    await bulk_upsert("weapons_catalog", [dict(x) for x in WEAPONS])
    await bulk_upsert("bosses", [dict(x) for x in BOSSES])
    await bulk_upsert("quests", [dict(x) for x in QUESTS])
    await bulk_upsert("characters_catalog", [dict(x) for x in CHARS])
    async for o in col("overrides").find({}):
        item = ALL.get(o["_id"])
        if item:
            item.update({k: v for k, v in o.items() if k != "_id"})
    from service_social import seed_squads
    await seed_squads()
    await migrate_world()
    from service_drops import art_seed
    await art_seed()


async def migrate_world():
    """Create world_state and give old characters the new fields without touching existing data.
    Evolution is grandfathered: every old character keeps the title their level already shows."""
    from service_migrate_rework import legacy_evo_stage
    from service_worldcore import get_world
    await get_world(force=True)
    claimed = await col("world_state").find_one_and_update({"_id": "main", "evo_migrated": {"$ne": True}}, {"$set": {"evo_migrated": True}})
    if claimed:
        async for c in col("characters").find({"evo": {"$exists": False}}, {"race": 1, "level": 1}):
            await col("characters").update_one({"_id": c["_id"], "evo": {"$exists": False}}, {"$set": {"evo": legacy_evo_stage(c["race"], c["level"])}})
    # bag v2: every existing bag gains the new starting slots once (upgrades already bought are kept)
    from config import BAG_OLD_START, BAG_START
    if await col("world_state").find_one_and_update({"_id": "main", "bag_v2": {"$ne": True}}, {"$set": {"bag_v2": True}}):
        await col("inventories").update_many({"capacity": {"$exists": True}}, {"$inc": {"capacity": BAG_START - BAG_OLD_START}})
    # bag grows with level: existing bags gain the slots of the levels already reached, once
    from config import BAG_PER_LEVEL
    if await col("world_state").find_one_and_update({"_id": "main", "bag_lvl": {"$ne": True}}, {"$set": {"bag_lvl": True}}):
        async for c in col("characters").find({"level": {"$gt": 1}}, {"user_id": 1, "level": 1}):
            await col("inventories").update_one({"user_id": c["user_id"], "capacity": {"$exists": True}},
                                                {"$inc": {"capacity": BAG_PER_LEVEL * (int(c["level"]) - 1)}})
    await col("characters").update_many({"relics": {"$exists": False}}, {"$set": {"relics": [], "cosmetics": {}, "armor_plus": {}, "buffs": {}}})
    await col("characters").update_many({"seen_at": {"$exists": False}}, {"$set": {"seen_at": 0}})


from cmdlist import CMD_EN, CMD_FA, GROUP_CMDS


async def setup_commands(bot):
    """Typing '/' in the chat shows this list; the game itself is driven by words. Each step is isolated so one failure can't hide the rest."""
    mk = lambda rows: [BotCommand(command=c, description=d) for c, d in rows]
    grp_en = [x for x in CMD_EN if x[0] in GROUP_CMDS]
    grp_fa = [x for x in CMD_FA if x[0] in GROUP_CMDS]
    steps = [lambda: bot.set_my_commands(mk(CMD_EN)),
             lambda: bot.set_my_commands(mk(CMD_FA), language_code="fa"),
             lambda: bot.set_my_commands(mk(grp_en), scope=BotCommandScopeAllGroupChats()),
             lambda: bot.set_my_commands(mk(grp_fa), scope=BotCommandScopeAllGroupChats(), language_code="fa"),
             lambda: bot.set_chat_menu_button(menu_button=MenuButtonCommands())]
    for step in steps:
        try:
            await step()
        except Exception:
            log.exception("command menu step failed")
    try:
        from handlers_adminpanel import refresh_admin_commands
        await refresh_admin_commands(bot)
    except Exception:
        log.exception("admin command menu failed")


async def health_server():
    async def health(_):
        return web.json_response({"ok": True, "db": await ping()})
    app = web.Application()
    app.router.add_get("/health", health)
    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", settings.port).start()
    return runner


async def main():
    logging.basicConfig(level=getattr(logging, settings.log_level, logging.INFO), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    validate_settings()
    from service_joingate import log_config_warnings
    log_config_warnings()
    await connect_db()
    await seed()
    from service_respec import rebase_race_stats_once, rebase_race_stats_v3_once
    try:
        log.info("race rebase: %s character(s) moved", await rebase_race_stats_once())
        log.info("race rebase v3: %s character(s) moved", await rebase_race_stats_v3_once())
    except Exception:
        log.exception("race rebase failed; it will retry on next start")
    from service_migrate_rework import run_all as rework_migrations
    await rework_migrations()  # evolution titles, race weapons, race armour (each runs once)
    runner = await health_server()
    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML, link_preview_is_disabled=True))
    from handlers_core import router
    from handlers_admincmd import router as admin_cmd_router  # admin slash commands + /redeem + /tokens (must come before the text router)
    import handlers_admincmd2  # noqa: F401  (admin slash commands, batch 2)
    import scheduler
    dp = Dispatcher()
    dp.include_router(admin_cmd_router)
    dp.include_router(router)
    stop = asyncio.Event()
    import service_log
    task = asyncio.create_task(scheduler.run(bot, stop))
    log_task = asyncio.create_task(service_log.run(bot, stop))
    import service_notify
    notify_task = asyncio.create_task(service_notify.run(bot, stop))
    import service_raceweapon
    rw_task = asyncio.create_task(service_raceweapon.notify_pending(bot, stop))  # "choose your race weapon" notice
    from service_migrate_rework import notify_respec
    rs_task = asyncio.create_task(notify_respec(bot, stop))  # "your stat points came back" notice
    try:
        await bot.delete_webhook(drop_pending_updates=settings.drop_pending)
        await setup_commands(bot)
        me = await bot.get_me()
        log.info("SENKA online as @%s", me.username)
        from service_joingate import self_check
        await self_check(bot)
        await dp.start_polling(bot, allowed_updates=["message", "callback_query"], handle_signals=True)
    finally:
        stop.set()
        await asyncio.gather(task, log_task, notify_task, rw_task, rs_task, return_exceptions=True)
        await bot.session.close()
        await runner.cleanup()
        await close_db()
        log.info("SENKA stopped cleanly")


if __name__ == "__main__":
    asyncio.run(main())
