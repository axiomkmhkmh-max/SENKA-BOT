"""Catalog / patch notes: what every item kind is, every skin, every dungeon with its own drops, the chests.
Pages are built by data_catalog from the game's own data. The owner can post everything to the news channel.

Callback codes: cat (hub), cati (item guide), catk (skins), catc (chests), catd:<page> (dungeons), catpost (owner: post to channel).
"""
import asyncio
import logging

from config import settings
from data_catalog import chests_pages, dungeons_pages, kinds_pages, skins_pages, all_pages
from service_dungeonshop import BOXES
from ui import SEP, Out, action, nav

log = logging.getLogger("senka.catalog")


def T(ctx, fa, en):
    return fa if ctx.lang == "fa" else en


def _title(ctx, sub=""):
    return f"⚔️ <b>𝖲𝖤𝖭𝖪𝖠</b> | <b>{T(ctx, 'کاتالوگ', 'Catalog')}</b>\n{SEP}\n{sub}"


@action("cat")
async def catalog_hub(ctx, arg):
    rows = [[(T(ctx, "📖 راهنمای آیتم‌ها", "📖 Item guide"), "cati", "")],
            [(T(ctx, "🎭 اسکین‌ها", "🎭 Skins"), "catk", ""), (T(ctx, "🥇 جعبه‌ها", "🥇 Chests"), "catc", "")],
            [(T(ctx, "🏰 دانجن‌ها و دراپ‌ها", "🏰 Dungeons and drops"), "catd", "0")],
            [(T(ctx, "🛠 ماموریت ساخت آیتم", "🛠 Forge mission"), "wsh", "")]]
    if ctx.uid == settings.owner_id:
        rows.append([(T(ctx, "📣 ارسال به کانال خبر", "📣 Post to the news channel"), "catpost", "")])
    rows.append(nav(ctx))
    return Out(_title(ctx, T(ctx, "همه‌چیز درباره‌ی آیتم‌ها، اسکین‌ها و دانجن‌ها: از کجا میاد، چیه و چطور فعالش کنی.",
                             "Everything about items, skins and dungeons: where it comes from, what it is and how to activate it.")), rows)


def _page(ctx, pages, code, arg):
    i = min(max(int(arg), 0), len(pages) - 1) if str(arg).isdigit() else 0
    nav_row = []
    if i > 0:
        nav_row.append(("◀️", code, str(i - 1), False, "none"))
    if i < len(pages) - 1:
        nav_row.append(("▶️", code, str(i + 1), False, "none"))
    rows = ([nav_row] if nav_row else []) + [nav(ctx, ("cat", ""))]
    return Out(pages[i], rows)


@action("cati")
async def catalog_items(ctx, arg):
    return _page(ctx, kinds_pages(ctx.lang), "cati", arg)


@action("catk")
async def catalog_skins(ctx, arg):
    return _page(ctx, skins_pages(ctx.lang), "catk", arg)


@action("catc")
async def catalog_chests(ctx, arg):
    return _page(ctx, chests_pages(ctx.lang, BOXES), "catc", arg)


@action("catd")
async def catalog_dungeons(ctx, arg):
    return _page(ctx, dungeons_pages(ctx.lang), "catd", arg)


@action("catpost")
async def catalog_post(ctx, arg):
    """Owner only: post the whole catalog (Persian) to the news channel, one message per page."""
    if ctx.uid != settings.owner_id:
        return Out(alert=T(ctx, "فقط مالک.", "Owner only."))
    target = settings.join_channel
    if not target:
        return Out(alert=T(ctx, "کانال خبر تنظیم نشده (JOIN_CHANNEL).", "No news channel set (JOIN_CHANNEL)."))
    sent = 0
    try:
        for page in all_pages("fa", BOXES):
            await ctx.bot.send_message(target, page)
            sent += 1
            await asyncio.sleep(1.2)
    except Exception as e:  # the bot must be an admin of the channel
        log.warning("catalog post failed after %s pages: %s", sent, e)
        return Out(alert=T(ctx, f"ارسال بعد از {sent} پیام قطع شد: ربات باید ادمین کانال باشد.", f"Stopped after {sent} messages: the bot must be a channel admin."))
    return Out(alert=T(ctx, f"{sent} پیام به کانال رفت.", f"{sent} messages posted."))
