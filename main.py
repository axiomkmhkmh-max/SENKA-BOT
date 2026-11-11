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
    from data_crafting import evo_gate_stage
    from service_worldcore import get_world
    await get_world(force=True)
    claimed = await col("world_state").find_one_and_update({"_id": "main", "evo_migrated": {"$ne": True}}, {"$set": {"evo_migrated": True}})
    if claimed:
        async for c in col("characters").find({"evo": {"$exists": False}}, {"race": 1, "level": 1}):
            await col("characters").update_one({"_id": c["_id"], "evo": {"$exists": False}}, {"$set": {"evo": evo_gate_stage(c["race"], c["level"])}})
    await col("characters").update_many({"relics": {"$exists": False}}, {"$set": {"relics": [], "cosmetics": {}, "armor_plus": {}, "buffs": {}}})
    await col("characters").update_many({"seen_at": {"$exists": False}}, {"$set": {"seen_at": 0}})


CMD_EN = [("home", "Open your world panel"), ("profile", "Your Soul Reaper profile"), ("explore", "Patrol the world"), ("battle", "Fight Hollows"),
          ("bag", "Inventory & equipment"), ("market", "Urahara shop, market & auctions"), ("quests", "Missions"), ("summon", "Summon characters & gear"),
          ("squad", "Squad / clan"), ("ranking", "Leaderboards"), ("daily", "Daily reward"), ("dungeon", "Enter dungeons"), ("map", "World map"),
          ("forge", "Strengthen your zanpakuto"), ("party", "Your companions"), ("minigame", "Bleach puzzle"), ("boss", "World boss"), ("world", "Living world panel"), ("craft", "Craft, evolve, gear"), ("season", "Season standings"), ("tower", "Soul Tower"), ("dispatch", "Dispatch companions"), ("wheel", "Urahara's wheel"), ("seat", "Gotei seat rank"), ("inner", "Inner World"), ("artifact", "Your Soul Artifact"),
          ("duel", "Ranked duel (reply to a player)"), ("friendly", "Friendly duel"), ("settings", "Language & settings"), ("commands", "All commands"), ("help", "Help")]
CMD_FA = [("home", "پنل دنیای من"), ("profile", "پروفایل شینیگامی"), ("explore", "گشت در جهان"), ("battle", "نبرد با هالوها"),
          ("bag", "کوله و تجهیزات"), ("market", "فروشگاه اوراهارا، بازار و حراج"), ("quests", "ماموریت‌ها"), ("summon", "احضار کاراکتر و تجهیزات"),
          ("squad", "جوخه / کلن"), ("ranking", "رتبه‌بندی"), ("daily", "جایزه روزانه"), ("dungeon", "ورود به دانجن"), ("map", "نقشه جهان"),
          ("forge", "تقویت زانپاکتو"), ("party", "همراهان من"), ("minigame", "معمای بلیچ"), ("boss", "باس جهانی"), ("world", "پنل دنیای زنده"), ("craft", "ساخت، تکامل و تجهیز"), ("season", "رتبه‌ی فصل"), ("tower", "برج روح"), ("dispatch", "اعزام همراهان"), ("wheel", "چرخ اوراهارا"), ("seat", "درجه‌ی گوتی"), ("inner", "دنیای درون"), ("artifact", "آرتیفکت من"),
          ("duel", "دوئل رنکد (ریپلای)"), ("friendly", "دوئل دوستانه"), ("settings", "زبان و تنظیمات"), ("commands", "همه‌ی دستورات"), ("help", "راهنما")]


async def setup_commands(bot):
    """Typing '/' in the chat shows this list; the game itself is driven by words."""
    try:
        mk = lambda rows: [BotCommand(command=c, description=d) for c, d in rows]
        await bot.set_my_commands(mk(CMD_EN))
        await bot.set_my_commands(mk(CMD_FA), language_code="fa")
        grp_en = [x for x in CMD_EN if x[0] in ("duel", "friendly", "boss", "help")]
        grp_fa = [x for x in CMD_FA if x[0] in ("duel", "friendly", "boss", "help")]
        await bot.set_my_commands(mk(grp_en), scope=BotCommandScopeAllGroupChats())
        await bot.set_my_commands(mk(grp_fa), scope=BotCommandScopeAllGroupChats(), language_code="fa")
        await bot.set_chat_menu_button(menu_button=MenuButtonCommands())
    except Exception:
        log.exception("could not register the command menu")


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
    await connect_db()
    await seed()
    runner = await health_server()
    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML, link_preview_is_disabled=True))
    from handlers_core import router
    import scheduler
    dp = Dispatcher()
    dp.include_router(router)
    stop = asyncio.Event()
    import service_log
    task = asyncio.create_task(scheduler.run(bot, stop))
    log_task = asyncio.create_task(service_log.run(bot, stop))
    try:
        await bot.delete_webhook(drop_pending_updates=settings.drop_pending)
        await setup_commands(bot)
        me = await bot.get_me()
        log.info("SENKA online as @%s", me.username)
        await dp.start_polling(bot, allowed_updates=["message", "callback_query"], handle_signals=True)
    finally:
        stop.set()
        await asyncio.gather(task, log_task, return_exceptions=True)
        await bot.session.close()
        await runner.cleanup()
        await close_db()
        log.info("SENKA stopped cleanly")


if __name__ == "__main__":
    asyncio.run(main())
