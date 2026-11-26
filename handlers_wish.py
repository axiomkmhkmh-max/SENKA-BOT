"""Forge Mission panels (data_wish / service_wish): pick gear for your level, see what it needs and where to get it, and
finish it when the bag has everything.

Callback codes: wsh (hub), wshl:<page> (gear list), wshi:<item> (one item and what it needs), wshs:<item> (start),
wshc (complete), wshx (abandon).
"""
from data_items import ALL
from data_races import DUNGEONS
from data_wish import ABANDON_WAIT_H, WEEKLY_DONE, eligible, requirement
from i18n import esc, fnum
from service_player import get_char
from service_wish import abandon, complete, current, progress, start
from ui import SEP, Out, action, nav

PER = 8
RAR_FA = {"Rare": "کمیاب", "Epic": "حماسی", "Legendary": "افسانه‌ای"}


def T(ctx, fa, en):
    return fa if ctx.lang == "fa" else en


def _title(ctx, sub=""):
    return f"⚔️ <b>𝖲𝖤𝖭𝖪𝖠</b> | <b>{T(ctx, 'ماموریت ساخت', 'Forge Mission')}</b>\n{SEP}\n{sub}"


def _nm(ctx, iid):
    x = ALL.get(iid) or {}
    return x.get("name_fa" if ctx.lang == "fa" else "name_en", iid)


def _dg(ctx, did):
    d = DUNGEONS.get(did) or {}
    return f"{d.get('fa' if ctx.lang == 'fa' else 'en', did)} ({T(ctx, 'لول', 'Lv')} {fnum(d.get('level', 0), ctx.lang)})"


def _req_lines(ctx, req, have=None):
    lines = []
    for iid, n in req["mats"].items():
        h = "" if have is None else f" — {fnum(min(have.get(iid, 0), n), ctx.lang)}/{fnum(n, ctx.lang)}"
        tick = "" if have is None else ("✅ " if have.get(iid, 0) >= n else "▫️ ")
        lines.append(f"{tick}{_nm(ctx, iid)} ×{fnum(n, ctx.lang)}{h}\n   ↳ {T(ctx, 'دراپ پایان', 'Final drop of')}: {_dg(ctx, req['from'][iid])}")
    lines.append(f"🪙 {T(ctx, 'سکه', 'Coins')}: {fnum(req['coins'], ctx.lang)}")
    return lines


@action("wsh")
async def wish_hub(ctx, arg):
    ch = await get_char(ctx.uid)
    if not ch:
        return Out(T(ctx, "اول ثبت‌نام کن.", "Register first."), [nav(ctx)])
    doc = await current(ctx.uid)
    if doc:
        prog = {i: have for i, _, have in await progress(ctx.uid, doc)}
        body = T(ctx, f"🎯 هدف: <b>{esc(_nm(ctx, doc['item']))}</b>\nمواد رو از دانجن‌ها جمع کن (هر دانجن روزی چند دراپ می‌ده):\n",
                 f"🎯 Goal: <b>{esc(_nm(ctx, doc['item']))}</b>\nCollect the materials from the dungeons (each dungeon pays only a few drops a day):\n")
        body += "\n".join(_req_lines(ctx, doc, prog))
        rows = [[(T(ctx, "✅ تکمیل ساخت", "✅ Complete"), "wshc", ""), (T(ctx, "🗑 رها کردن", "🗑 Abandon"), "wshx", "")],
                [(T(ctx, "📖 کاتالوگ دانجن‌ها", "📖 Dungeon catalog"), "catd", "0")], nav(ctx)]
        return Out(_title(ctx, body), rows)
    if not eligible(int(ch.get("level", 1)), ch.get("race")):
        return Out(_title(ctx, T(ctx, "از لول ۱۵ به بعد می‌تونی یک آیتم رو هدف بگیری.", "From level 15 you can aim at a piece of gear.")), [nav(ctx)])
    info = T(ctx, f"یک تجهیز مناسب لولت رو انتخاب کن؛ بعد مواد لازمش رو ببین و دنبالشون برو.\n⚠️ عمداً سخته: مواد، دراپ پایان چند دانجن نزدیک لول تو هستن، سکه‌ی زیادی لازمه، و فقط {fnum(WEEKLY_DONE, 'fa')} ماموریت در هفته تموم می‌شه.",
              f"Pick gear for your level, then see what it needs and go and get it.\n⚠️ Deliberately hard: the materials are final drops of several dungeons near your level, it costs a lot of coins, and only {WEEKLY_DONE} mission can be finished per week.")
    return Out(_title(ctx, info), [[(T(ctx, "🛠 انتخاب آیتم", "🛠 Choose an item"), "wshl", "0")], nav(ctx)])


@action("wshl")
async def wish_list(ctx, arg):
    ch = await get_char(ctx.uid)
    ids = eligible(int((ch or {}).get("level", 1)), (ch or {}).get("race"))
    pages = max(1, -(-len(ids) // PER))
    page = min(max(int(arg), 0), pages - 1) if str(arg).isdigit() else 0
    rows = [[(f"{'🟣🟡'[ALL[i]['rarity'] == 'Legendary'] if ALL[i]['rarity'] != 'Rare' else '🔵'} {_nm(ctx, i)}", "wshi", i)] for i in ids[page * PER:(page + 1) * PER]]
    pg = []
    if page > 0:
        pg.append(("◀️", "wshl", str(page - 1), False, "none"))
    if page < pages - 1:
        pg.append(("▶️", "wshl", str(page + 1), False, "none"))
    if pg:
        rows.append(pg)
    rows.append(nav(ctx, ("wsh", "")))
    return Out(_title(ctx, T(ctx, f"صفحه {fnum(page + 1, 'fa')} از {fnum(pages, 'fa')}", f"Page {page + 1} of {pages}")), rows)


@action("wshi")
async def wish_item(ctx, iid):
    ch = await get_char(ctx.uid)
    if not ch or iid not in eligible(int(ch.get("level", 1)), ch.get("race")):
        return Out(alert=T(ctx, "این آیتم الان برات در دسترس نیست.", "This item is not available to you now."))
    req = requirement(iid, int(ch.get("level", 1)))
    body = f"<b>{esc(_nm(ctx, iid))}</b>\n" + "\n".join(_req_lines(ctx, req))
    return Out(_title(ctx, body), [[(T(ctx, "🎯 شروع ماموریت", "🎯 Start mission"), "wshs", iid)], nav(ctx, ("wshl", "0"))])


@action("wshs")
async def wish_start(ctx, iid):
    doc, code = await start(ctx.uid, iid)
    if code == "ok":
        return await wish_hub(ctx, "")
    msg = {"open": ("یک ماموریت باز داری.", "You already have an open mission."),
           "wait": (f"بعد از رها کردن باید {fnum(ABANDON_WAIT_H, 'fa')} ساعت صبر کنی.", f"After abandoning, wait {ABANDON_WAIT_H} hours."),
           "notlisted": ("این آیتم الان برات در دسترس نیست.", "This item is not available to you now."),
           "noreg": ("اول ثبت‌نام کن.", "Register first.")}[code]
    return Out(alert=T(ctx, *msg))


@action("wshc")
async def wish_complete(ctx, arg):
    code = await complete(ctx.uid)
    if code == "ok":
        return Out(_title(ctx, T(ctx, "🎉 ساخته شد! آیتم توی کیفته.", "🎉 Forged! The item is in your bag.")), [nav(ctx)])
    msg = {"none": ("ماموریت بازی نداری.", "No open mission."), "mats": ("هنوز همه‌ی مواد رو نداری.", "You do not have all the materials yet."),
           "funds": ("سکه‌ی کافی نداری.", "Not enough coins."), "weekly": ("این هفته یک ماموریت رو تموم کردی؛ هفته‌ی بعد.", "You finished a mission this week; next week."),
           "full": ("کیفت پره؛ جا باز کن.", "Your bag is full; make room.")}[code]
    return Out(alert=T(ctx, *msg))


@action("wshx")
async def wish_abandon(ctx, arg):
    await abandon(ctx.uid)
    return await wish_hub(ctx, "")
