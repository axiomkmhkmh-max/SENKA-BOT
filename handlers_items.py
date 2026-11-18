"""Bag, equipment, NPC shop, player market, auctions, gacha and party."""
import math
import time

from config import BAG_MAX, BAG_PER_LEVEL, BAG_START, BAG_STEP
from data_chars import CHAR_BY_ID, CHARS, GACHA_RATES, char_bonus, copies_to_level_star
from data_items import ALL
from data_lore import CHAR_EPI
from data_weapons import RARITIES, RARITY_ICON
from database import col, game_settings
from fmt import item_card, nm, pctf
from i18n import esc, fnum
from service_economy import (FORGE_CHANCE, auction_bid, equip, forge, forge_cost, gacha_doc, gacha_pull, inv_get, market_buy, market_cancel, market_create,
                             npc_sell, price_mult, settle_listings, shop_buy, shop_price, shop_quote, shop_stock, SHOP_QTYS, slots_used, suggested_price, toggle_party, unequip,
                             use_item)
from service_economy import char_sell_value, inv_remove, sell_character
from service_log import log_event
from service_player import add_coins, get_char, today
from ui import GREEN, RED, Out, action, chunk, head, nav

PER = 6
FILTERS = {"a": None, "w": ("weapon",), "e": ("armor", "accessory", "relic", "cosmetic"), "u": ("potion", "kido_card", "race_card", "book", "egg", "key", "material", "evolution", "quincy", "dungeon",
                                                                                            "temper", "inner_key")}


def _rk(i):
    return -RARITIES.index(ALL[i]["rarity"])


# ---- bag ----------------------------------------------------------------------------------
# BAG_START / BAG_STEP / BAG_MAX live in config.py (slots: start, +per upgrade, ceiling)


def bag_upgrade_cost(capacity: int) -> int:
    """Coins for the next +BAG_STEP slots: 500 for the first, +100 for each step after."""
    return 500 + 100 * max(0, (int(capacity) - BAG_START) // BAG_STEP)


@action("bagup")
async def bag_upgrade(ctx, arg):
    L = ctx.lang
    inv = await inv_get(ctx.uid)
    cap = max(1, inv.get("capacity", BAG_START))
    bought = cap - BAG_PER_LEVEL * (int((await get_char(ctx.uid))["level"]) - 1)  # the level slots are not part of the upgrades
    if bought >= BAG_MAX:
        return Out(alert="کوله‌ت به سقف رسیده." if L == "fa" else "Your bag is already at its maximum.")
    cost = bag_upgrade_cost(bought)
    if not await add_coins(ctx.uid, -cost, "bag_upgrade"):
        return Out(alert=("سکه‌ی کافی نداری." if L == "fa" else "Not enough coins."))
    # conditional on the capacity we priced, so two taps cannot both upgrade for one payment
    res = await col("inventories").update_one({"user_id": ctx.uid, "capacity": cap}, {"$inc": {"capacity": BAG_STEP}})
    if not res.modified_count:
        await add_coins(ctx.uid, cost, "bag_upgrade_refund")
        return Out(alert=("لطفاً دوباره امتحان کن." if L == "fa" else "Please try again."))
    return await bag(ctx, "0")


@action("bag")
async def bag(ctx, arg):
    L = ctx.lang
    parts = (arg or "0").split(":")
    try:
        page = int(parts[0] or 0)
    except ValueError:
        page = 0
    flt = (parts[1] if len(parts) > 1 and parts[1] else "a")
    srt = (parts[2] if len(parts) > 2 and parts[2] else "r")  # r = rarity (default), d = damage (weapons first)
    if flt not in FILTERS:
        flt = "a"
    inv = await inv_get(ctx.uid)
    ch = await get_char(ctx.uid)
    cats = FILTERS.get(flt)
    ids = [i for i, q in inv["items"].items() if q > 0 and i in ALL and (not cats or ALL[i]["category"] in cats)]
    if srt == "d":
        ids.sort(key=lambda i: (-ALL[i].get("attack", 0), _rk(i), i))
    else:
        ids.sort(key=lambda i: (_rk(i), i))
    pages = max(1, math.ceil(len(ids) / PER))
    page = max(0, min(page, pages - 1))
    back = f"{page}:{flt}:{srt}"  # the item card returns here, to the same page, filter and sort
    rows = [[(f"{nm(i, L).replace('<', '').replace('>', '')} ×{inv['items'][i]}", "iv", f"{i}:{back}")]
            for i in ids[page * PER:(page + 1) * PER]]
    fr = [((("• " if flt == k else "") + ctx.t("flt_" + k)), "bag", f"0:{k}:{srt}") for k in FILTERS]
    rows.append(fr)
    if ids:
        sort_lbl = ("🔀 مرتب: آسیب" if srt != "d" else "🔀 مرتب: کمیاب‌ترین") if L == "fa" else ("🔀 Sort: damage" if srt != "d" else "🔀 Sort: rarity")
        rows.append([(sort_lbl, "bag", f"{page}:{flt}:{'d' if srt != 'd' else 'r'}")])
    pg = []
    if page > 0:
        pg.append(("◀️", "bag", f"{page - 1}:{flt}:{srt}"))
    if page < pages - 1:
        pg.append(("▶️", "bag", f"{page + 1}:{flt}:{srt}"))
    if pg:
        rows.append(pg)
    if ids:
        rows.append([("☑️ انتخاب چندتایی و حذف" if L == "fa" else "☑️ Select multiple & remove", "bqm", f"{page}:{flt}")])
    capn_now = max(1, inv.get("capacity", BAG_START))
    bought_now = capn_now - BAG_PER_LEVEL * (int(ch["level"]) - 1)
    if bought_now < BAG_MAX:
        cost = bag_upgrade_cost(bought_now)
        lbl = (f"⬆️ ارتقای کوله +{BAG_STEP} ({fnum(cost, L)} 🪙)" if L == "fa" else f"⬆️ Upgrade bag +{BAG_STEP} ({fnum(cost, L)} 🪙)")
        rows.append([(lbl, "bagup", "")])
    rows.append(nav(ctx))
    eq = f"⚔️ {nm(ch['weapon_id'], L)}\n🛡️ {nm(ch.get('armor_id'), L)}\n💍 {nm(ch.get('acc_id'), L)}\n📿 {nm(ch.get('charm_id'), L)}"
    used, capn = slots_used(inv["items"]), max(1, inv.get("capacity", BAG_START))
    k = min(10, round(10 * used / capn))
    cap = f"<code>{'▰' * k}{'▱' * (10 - k)}</code> {fnum(used, L)}/{fnum(capn, L)}"
    body = ctx.t("bag_body", cap=cap, eq=eq, n=fnum(len(ids), L))
    if not ids:
        body += "\n\n" + ("اینجا خالیه؛ از شکار و دانجن غنیمت جمع کن 🎒" if L == "fa" else "Empty for now. Loot something in Explore or Dungeons 🎒")
    return Out(head(ctx, "ttl_bag") + body, rows)


@action("iv")
async def item_view(ctx, arg):
    # arg is "<item_id>" or "<item_id>:<page>:<filter>:<sort>" so Back returns to the same spot in the bag
    iid, _, back = (arg or "").partition(":")
    back = back or "0:a:r"
    inv = await inv_get(ctx.uid)
    qty = inv["items"].get(iid, 0)
    if iid not in ALL or qty <= 0:
        return await bag(ctx, "0")
    it = ALL[iid]
    rows = []
    if it.get("slot") or it["category"] == "weapon":
        rows.append([(ctx.t("b_equip"), "eq", f"{iid}:{back}")])
    ety = (it.get("effect") or {}).get("type")
    if ety in ("kido", "xp", "pet", "buff", "kido_book", "bond"):
        rows.append([(ctx.t("b_use"), "us", f"{iid}:{back}")])
    elif ety == "relic":
        rows.append([(ctx.t("m_rlc"), "rlc", "")])
    elif ety == "cosmetic":
        rows.append([(ctx.t("m_cos"), "cos", "")])
    elif ety in ("mat", "evo"):
        rows.append([(ctx.t("m_crf"), "crf" if ety == "mat" else "evo", "")])
    elif ety == "key":
        rows.append([(ctx.t("m_evt"), "evt", "")])
    elif ety == "inner_key":
        rows.append([(ctx.t("m_in2"), "in2", "")])
    elif it["category"] == "temper":
        rows.append([(ctx.t("b_forge"), "frg", "")])
    row2 = [(ctx.t("b_sell_npc"), "sl", f"{iid}:{back}")]
    if it.get("tradeable"):
        row2.append((ctx.t("b_list"), "ml", iid))
    rows.append(row2)
    rows.append(nav(ctx, ("bag", back)))
    return Out(head(ctx, "ttl_bag") + item_card(ctx, iid, qty), rows)


def _split_back(arg):
    """'<item>:<page>:<filter>:<sort>' -> (item, back). The bag reopens at the same page after using an item
    (it used to jump back to page one every time)."""
    iid, _, back = (arg or "").partition(":")
    return iid, (back or "0")


@action("eq")
async def eq(ctx, arg):
    arg, back = _split_back(arg)
    r = await equip(ctx.uid, arg)
    if r != "ok":
        return Out(alert=ctx.t("eq_" + r))
    out = await bag(ctx, back)
    out.alert = ctx.t("eq_ok")
    return out


@action("ueq")
async def ueq(ctx, arg):
    r = await unequip(ctx.uid, arg)
    if r != "ok":
        return Out(alert=ctx.t("ueq_" + r))
    return await bag(ctx, "0")


@action("us")
async def use(ctx, arg):
    arg, back = _split_back(arg)
    r, extra = await use_item(ctx.uid, arg)
    if r == "ok" and ((ALL.get(arg) or {}).get("effect") or {}).get("type") == "pet":  # egg hatched on the spot
        from service_economy import PETS
        nmx = PETS[int(extra) % len(PETS)][0 if ctx.lang != "fa" else 1]
        out = await bag(ctx, back)
        out.alert = (f"🐣 تخم شکست و یک همراه بیرون اومد: {nmx}! از پنل همراه می‌تونی ببینیش." if ctx.lang == "fa"
                     else f"🐣 The egg hatched: {nmx}! See it in the companion panel.")
        return out
    if r == "ok":
        out = await bag(ctx, back)
        out.alert = ctx.t("us_ok", n=fnum(extra if isinstance(extra, int) else 0, ctx.lang))
        return out
    if r in ("incubate", "incubating"):  # egg placed in the incubator (or one is already incubating)
        L, n = ctx.lang, fnum(extra or 0, ctx.lang)
        if r == "incubate":
            txt = (f"🥚 تخم در انکوباتور گذاشته شد؛ {n} اکتشاف دیگه تا بیرون اومدنش." if L == "fa"
                   else f"🥚 The egg is incubating; {n} more explores until it hatches.")
        else:
            txt = (f"🥚 انکوباتور پر است؛ {n} اکتشاف دیگه مونده." if L == "fa"
                   else f"🥚 The incubator is busy; {n} explores left.")
        out = await bag(ctx, back)
        out.alert = txt
        return out
    if r == "race_card":
        return Out(alert=ctx.t("us_race_card"))
    if r == "order":
        return Out(alert=ctx.t("us_order", n=fnum(extra or 0, ctx.lang)))
    if r == "rw_switch":  # Weapon Rebirth Seal: pick the new type (the seal is spent only when you pick)
        from handlers_raceweapon import race_weapon_switch
        return await race_weapon_switch(ctx, "")
    if r == "race":
        return Out(alert=("📜 فقط شینیگامی و ویزورد می‌تونن کیدو یاد بگیرن؛ این آیتم مصرف نشد. می‌تونی بفروشیش یا ترید کنی."
                          if ctx.lang == "fa" else
                          "📜 Only Shinigami and Visored can learn Kidō; the item was not used. You can sell or trade it."))
    return Out(alert=ctx.t("us_" + r, n=extra or 0))


@action("sl")
async def sell_npc(ctx, arg):
    inv = await inv_get(ctx.uid)
    arg, back = _split_back(arg)
    n = await npc_sell(ctx.uid, arg, 1)
    if not n:
        return Out(alert=ctx.t("sell_fail"))
    out = await bag(ctx, back)
    out.alert = ctx.t("sell_ok", n=fnum(n, ctx.lang))
    return out


# ---- multi-select remove -------------------------------------------------------------------
# Selection lives in Mongo (collection "bag_sel", one doc per player) because callback_data is capped at 64 bytes.
# One unit is removed per selected item. Every removal goes through a confirmation screen.
SEL_MAX = 40
RAR_FA = {"Common": "معمولی", "Uncommon": "غیرمعمول", "Rare": "نادر", "Epic": "حماسی", "Legendary": "افسانه‌ای", "Mythic": "اساطیری"}


def _ids_for(inv, flt):
    cats = FILTERS.get(flt)
    return sorted([i for i, q in inv["items"].items() if q > 0 and i in ALL and (not cats or ALL[i]["category"] in cats)], key=lambda i: (_rk(i), i))


async def _sel_get(uid, inv):
    d = await col("bag_sel").find_one({"_id": uid})
    return [i for i in (d or {}).get("items", []) if inv["items"].get(i, 0) > 0 and i in ALL]


async def _sel_set(uid, items):
    if items:
        await col("bag_sel").update_one({"_id": uid}, {"$set": {"items": items, "at": time.time()}}, upsert=True)
    else:
        await col("bag_sel").delete_one({"_id": uid})


def _pf(arg):
    """'page:flt' -> (page, flt) with safe defaults."""
    p, _, f = (arg or "0").partition(":")
    return (int(p) if p.lstrip("-").isdigit() else 0), (f if f in FILTERS else "a")


async def _sel_view(ctx, page, flt, alert=None):
    L = ctx.lang
    fa = L == "fa"
    inv = await inv_get(ctx.uid)
    ids = _ids_for(inv, flt)
    sel = await _sel_get(ctx.uid, inv)
    sset = set(sel)
    pages = max(1, math.ceil(len(ids) / PER))
    page = max(0, min(page, pages - 1))
    rows = []
    for i in ids[page * PER:(page + 1) * PER]:
        on = i in sset
        label = f"{'☑️' if on else '⬜'} {nm(i, L).replace('<', '').replace('>', '')} ×{inv['items'][i]}"
        rows.append([(label, "bqt", f"{i}:{page}:{flt}", False, GREEN if on else "none")])
    rows.append([(("• " if flt == k else "") + ctx.t("flt_" + k), "bqv", f"0:{k}", False, "none") for k in FILTERS])
    pg = []
    if page > 0:
        pg.append(("◀️", "bqv", f"{page - 1}:{flt}", False, "none"))
    if page < pages - 1:
        pg.append(("▶️", "bqv", f"{page + 1}:{flt}", False, "none"))
    if pg:
        rows.append(pg)
    rows.append([("✅ همه‌ی این صفحه" if fa else "✅ Whole page", "bqa", f"{page}:{flt}", False, "none"),
                 ("🧹 پاک‌کردن انتخاب" if fa else "🧹 Clear", "bqc", f"{page}:{flt}", False, "none")])
    # whole rarity tiers in the current filter (e.g. every Epic), so a big bag can be cleared in a few taps
    present = [r for r in RARITIES if any(ALL[i].get("rarity") == r for i in ids)]
    if present:
        rows.append([((f"🎯 همه‌ی {RAR_FA.get(r, r)}" if fa else f"🎯 All {r}"), "bqr", f"{r}:{page}:{flt}", False, "none")
                     for r in present[:6]])
    if sel:
        n = fnum(len(sel), L)
        rows.append([((f"💱 فروش ({n})" if fa else f"💱 Sell ({n})"), "bqx", f"s:{page}:{flt}", False, GREEN),
                     ((f"🚮 دور انداختن ({n})" if fa else f"🚮 Discard ({n})"), "bqx", f"d:{page}:{flt}", False, RED)])
    rows.append(nav(ctx, ("bag", f"{page}:{flt}")))
    if fa:
        body = (f"☑️ <b>حالت انتخاب</b> | صفحه {fnum(page + 1, L)}/{fnum(pages, L)}\n"
                f"انتخاب‌شده: <b>{fnum(len(sel), L)}</b> از حداکثر {fnum(SEL_MAX, L)}\n"
                "روی هر آیتم بزن تا تیک بخوره. انتخاب‌ها بین صفحه‌ها و فیلترها می‌مونه و صفحه نمی‌پره 👌\n"
                "از هر آیتم انتخاب‌شده فقط <b>یک عدد</b> حذف می‌شه.")
        if not ids:
            body += "\n\nاین فیلتر خالیه."
    else:
        body = (f"☑️ <b>Select mode</b> | page {page + 1}/{pages}\n"
                f"Selected: <b>{len(sel)}</b> / {SEL_MAX} max\n"
                "Tap items to tick them. Picks survive page and filter changes, and the page won't jump.\n"
                "Only <b>one unit</b> of each selected item is removed.")
        if not ids:
            body += "\n\nNothing under this filter."
    return Out(head(ctx, "ttl_bag") + body, rows, alert=alert)


@action("bqm")
async def bag_select_enter(ctx, arg):
    page, flt = _pf(arg)
    await _sel_set(ctx.uid, [])  # always start a fresh selection
    return await _sel_view(ctx, page, flt)


@action("bqv")
async def bag_select_view(ctx, arg):
    page, flt = _pf(arg)
    return await _sel_view(ctx, page, flt)


@action("bqt")
async def bag_select_toggle(ctx, arg):
    item, _, rest = (arg or "").partition(":")
    page, flt = _pf(rest)
    inv = await inv_get(ctx.uid)
    if item not in ALL or inv["items"].get(item, 0) <= 0:
        return await _sel_view(ctx, page, flt)
    sel = await _sel_get(ctx.uid, inv)
    alert = None
    if item in sel:
        sel.remove(item)
    elif len(sel) >= SEL_MAX:
        alert = f"حداکثر {fnum(SEL_MAX, ctx.lang)} آیتم در هر نوبت." if ctx.lang == "fa" else f"Max {SEL_MAX} items at a time."
    else:
        sel.append(item)
    await _sel_set(ctx.uid, sel)
    return await _sel_view(ctx, page, flt, alert)


@action("bqa")
async def bag_select_page(ctx, arg):
    page, flt = _pf(arg)
    inv = await inv_get(ctx.uid)
    ids = _ids_for(inv, flt)
    pages = max(1, math.ceil(len(ids) / PER))
    page = max(0, min(page, pages - 1))
    sel = await _sel_get(ctx.uid, inv)
    alert = None
    for i in ids[page * PER:(page + 1) * PER]:
        if i in sel:
            continue
        if len(sel) >= SEL_MAX:
            alert = f"حداکثر {fnum(SEL_MAX, ctx.lang)} آیتم در هر نوبت." if ctx.lang == "fa" else f"Max {SEL_MAX} items at a time."
            break
        sel.append(i)
    await _sel_set(ctx.uid, sel)
    return await _sel_view(ctx, page, flt, alert)


@action("bqr")
async def bag_select_rarity(ctx, arg):
    """Select every item of one rarity in the current filter (up to SEL_MAX). arg = rarity:page:filter"""
    rar, _, rest = (arg or "").partition(":")
    page, flt = _pf(rest)
    inv = await inv_get(ctx.uid)
    ids = [i for i in _ids_for(inv, flt) if ALL[i].get("rarity") == rar]
    sel = await _sel_get(ctx.uid, inv)
    alert = None
    for i in ids:
        if i in sel:
            continue
        if len(sel) >= SEL_MAX:
            alert = f"حداکثر {fnum(SEL_MAX, ctx.lang)} آیتم در هر نوبت." if ctx.lang == "fa" else f"Max {SEL_MAX} items at a time."
            break
        sel.append(i)
    await _sel_set(ctx.uid, sel)
    return await _sel_view(ctx, page, flt, alert)


@action("bqc")
async def bag_select_clear(ctx, arg):
    page, flt = _pf(arg)
    await _sel_set(ctx.uid, [])
    return await _sel_view(ctx, page, flt)


@action("bqx")
async def bag_select_confirm(ctx, arg):
    mode, _, rest = (arg or "").partition(":")
    page, flt = _pf(rest)
    L = ctx.lang
    fa = L == "fa"
    inv = await inv_get(ctx.uid)
    sel = await _sel_get(ctx.uid, inv)
    if not sel or mode not in ("s", "d"):
        return await _sel_view(ctx, page, flt, ("چیزی انتخاب نشده." if fa else "Nothing selected."))
    sell = mode == "s"
    shown = [f"• {nm(i, L)} ×1 <i>({'از' if fa else 'of'} {fnum(inv['items'][i], L)})</i>" for i in sel[:15]]
    if len(sel) > 15:
        shown.append((f"… و {fnum(len(sel) - 15, L)} مورد دیگه" if fa else f"… and {len(sel) - 15} more"))
    if sell:
        rate = float((await game_settings())["coin_rate"])
        est = sum(max(1, int(ALL[i]["sell_price"] * rate)) for i in sel)
        if fa:
            head_t = f"💱 <b>تأیید فروش به فروشگاه</b>\n{fnum(len(sel), L)} آیتم، از هرکدوم ۱ عدد:\n\n"
            tail = f"\n\n💰 دریافتی تقریبی: <b>{fnum(est, L)} 🪙</b>\nمطمئنی؟"
        else:
            head_t = f"💱 <b>Confirm sale to shop</b>\n{len(sel)} items, 1 unit each:\n\n"
            tail = f"\n\n💰 Estimated payout: <b>{est:,} 🪙</b>\nAre you sure?"
        yes = ("✅ تأیید فروش" if fa else "✅ Confirm sale", "bqy", f"s:{page}:{flt}", False, GREEN)
    else:
        if fa:
            head_t = f"🚮 <b>تأیید دور انداختن</b>\n{fnum(len(sel), L)} آیتم، از هرکدوم ۱ عدد (بدون سکه و غیرقابل بازگشت):\n\n"
            tail = "\n\nمطمئنی؟"
        else:
            head_t = f"🚮 <b>Confirm discard</b>\n{len(sel)} items, 1 unit each (no coins, cannot be undone):\n\n"
            tail = "\n\nAre you sure?"
        yes = ("✅ تأیید دور انداختن" if fa else "✅ Confirm discard", "bqy", f"d:{page}:{flt}", False, RED)
    rows = [[yes], [("❌ لغو" if fa else "❌ Cancel", "bqv", f"{page}:{flt}", False, "none")]]
    return Out(head(ctx, "ttl_bag") + head_t + "\n".join(shown) + tail, rows)


@action("bqy")
async def bag_select_do(ctx, arg):
    mode, _, rest = (arg or "").partition(":")
    page, flt = _pf(rest)
    fa = ctx.lang == "fa"
    # take the selection atomically: a double tap on "confirm" can never run it twice
    d = await col("bag_sel").find_one_and_delete({"_id": ctx.uid})
    items = [i for i in (d or {}).get("items", []) if i in ALL][:SEL_MAX]
    if not items or mode not in ("s", "d"):
        return await _sel_view(ctx, page, flt, ("چیزی انتخاب نشده." if fa else "Nothing selected."))
    done, total = 0, 0
    for i in items:
        if mode == "s":
            n = await npc_sell(ctx.uid, i, 1)
            if n:
                done += 1
                total += n
        elif await inv_remove(ctx.uid, i, 1):
            done += 1
            log_event("shop", ctx.uid, f"دور انداختن: {ALL[i]['name_fa']} ×1", item=i)
    if not done:
        return await _sel_view(ctx, page, flt, ("انجام نشد؛ آیتم‌ها دیگه تو کیفت نیستن." if fa else "Nothing happened; those items are gone from your bag."))
    if mode == "s":
        msg = f"✅ {fnum(done, ctx.lang)} آیتم فروخته شد: {fnum(total, ctx.lang)} 🪙" if fa else f"✅ Sold {done} items for {total:,} 🪙"
    else:
        msg = f"🚮 {fnum(done, ctx.lang)} آیتم دور انداخته شد." if fa else f"🚮 Discarded {done} items."
    return await _sel_view(ctx, page, flt, msg)


# ---- listing flow -----------------------------------------------------------------------------
@action("ml")
async def market_list_prompt(ctx, arg):
    it = ALL.get(arg)
    if not it:
        return await bag(ctx, "0")
    sp = await suggested_price(arg)
    high = it["rarity"] in ("Epic", "Legendary", "Mythic")  # these can be sold either way: the seller picks fixed or auction
    btns = [(f"🏷 {fnum(int(sp * m / 10), ctx.lang)} 🪙", "mlp", f"{arg}.{m}.f") for m in (7, 10, 15, 22)]
    rows = chunk(btns, 2)
    if high:
        abtns = [(f"🔨 {fnum(int(sp * m / 10), ctx.lang)} 🪙", "mlp", f"{arg}.{m}.a") for m in (7, 10, 15, 22)]
        rows += chunk(abtns, 2)
    rows.append(nav(ctx, ("iv", arg)))
    note = ctx.t("ml_fixed") + ("\n" + ctx.t("ml_auction") if high else "")
    if high:
        note += "\n🏷 = قیمت ثابت · 🔨 = حراج" if ctx.lang == "fa" else "\n🏷 = fixed price · 🔨 = auction"
    return Out(head(ctx, "ttl_mkt") + item_card(ctx, arg) + f"\n\n{note}\n" + ctx.t("ml_pick", sp=fnum(sp, ctx.lang)), rows)


@action("mlp")
async def market_list_do(ctx, arg):
    iid, _, rest = arg.partition(".")
    m, _, k = rest.partition(".")
    it = ALL.get(iid)
    if not it:
        return Out()
    sp = await suggested_price(iid)
    price = max(1, int(sp * int(m) / 10))
    kind = "auction" if k == "a" else "fixed"
    r = await market_create(ctx.uid, iid, price, kind)
    if r != "ok":
        return Out(alert=ctx.t("ml_e_" + r))
    return await my_listings(ctx, "")


# ---- market views -------------------------------------------------------------------------------
@action("mkt")
async def market(ctx, arg):
    await settle_listings()
    rows = [[(ctx.t("mk_shop"), "shp", "0"), (ctx.t("mk_fixed"), "mkb", "0")],
            [(ctx.t("mk_auction"), "mka", "0"), (ctx.t("mk_mine"), "mkm", "")], [(ctx.t("b_art_mkt"), "axm", "0")], nav(ctx)]
    return Out(head(ctx, "ttl_mkt") + ctx.t("mkt_body"), rows)


async def _listing_page(ctx, kind, arg, code, view):
    L = ctx.lang
    page = int(arg or 0)
    q = {"status": "active", "kind": kind, "end_at": {"$gt": int(time.time())}}
    total = await col("market_listings").count_documents(q)
    docs = await col("market_listings").find(q).sort("created_at", -1).skip(page * PER).limit(PER).to_list(PER)
    rows = []
    for d in docs:
        price = d["bid"] or d["price"]
        rows.append([(f"{nm(d['item_id'], L).replace('<', '').replace('>', '')} — {fnum(price, L)}🪙", view, d["_id"])])
    pages = max(1, math.ceil(total / PER))
    pg = []
    if page > 0:
        pg.append(("◀️", code, str(page - 1)))
    if page < pages - 1:
        pg.append(("▶️", code, str(page + 1)))
    if pg:
        rows.append(pg)
    rows.append(nav(ctx, ("mkt", "")))
    return Out(head(ctx, "ttl_mkt") + (ctx.t("mk_empty") if not docs else ctx.t("mk_page", p=fnum(page + 1, L), n=fnum(pages, L))), rows)


@action("mkb")
async def market_browse(ctx, arg):
    return await _listing_page(ctx, "fixed", arg, "mkb", "mkv")


@action("mka")
async def auction_browse(ctx, arg):
    return await _listing_page(ctx, "auction", arg, "mka", "mkav")


@action("mkv")
async def listing_view(ctx, arg):
    d = await col("market_listings").find_one({"_id": arg, "status": "active"})
    if not d:
        return Out(alert=ctx.t("mk_gone"))
    st = await game_settings()
    fee = math.ceil(d["price"] * float(st["market_buyer_fee"]))
    body = item_card(ctx, d["item_id"]) + "\n\n" + ctx.t("mk_price", p=fnum(d["price"], ctx.lang), fee=fnum(fee, ctx.lang))
    rows = [[(ctx.t("b_buy"), "mkby", arg)] if d["seller"] != ctx.uid else [(ctx.t("b_cancel"), "mkc", arg)], nav(ctx, ("mkb", "0"))]
    return Out(head(ctx, "ttl_mkt") + body, rows)


@action("mkby")
async def listing_buy(ctx, arg):
    r = await market_buy(ctx.uid, arg)
    if r != "ok":
        return Out(alert=ctx.t("mk_e_" + r))
    out = await market_browse(ctx, "0")
    out.alert = ctx.t("mk_bought")
    return out


@action("mkav")
async def auction_view(ctx, arg):
    d = await col("market_listings").find_one({"_id": arg, "status": "active"})
    if not d:
        return Out(alert=ctx.t("mk_gone"))
    L = ctx.lang
    low = d["price"] if not d["bid"] else math.ceil(d["bid"] * 1.05)
    left = max(0, d["end_at"] - int(time.time()))
    body = item_card(ctx, d["item_id"]) + "\n\n" + ctx.t("au_info", bid=fnum(d["bid"], L), low=fnum(low, L), m=fnum(left // 60, L))
    base = d["bid"] or d["price"]
    rows = [[(f"+5% = {fnum(math.ceil(max(low, base * 1.05)), L)}🪙", "abd", f"{arg}.5"), (f"+10% = {fnum(math.ceil(max(low, base * 1.10)), L)}🪙", "abd", f"{arg}.10")],
            [(f"+25% = {fnum(math.ceil(max(low, base * 1.25)), L)}🪙", "abd", f"{arg}.25")]]
    if d["seller"] == ctx.uid and not d["bid"]:
        rows.append([(ctx.t("b_cancel"), "mkc", arg)])
    rows.append(nav(ctx, ("mka", "0")))
    return Out(head(ctx, "ttl_mkt") + body, rows)


@action("abd")
async def auction_bid_cb(ctx, arg):
    lid, _, pct = arg.partition(".")
    d = await col("market_listings").find_one({"_id": lid, "status": "active"})
    if not d:
        return Out(alert=ctx.t("mk_gone"))
    low = d["price"] if not d["bid"] else math.ceil(d["bid"] * 1.05)
    amount = max(low, math.ceil((d["bid"] or d["price"]) * (1 + int(pct) / 100)))
    r = await auction_bid(ctx.uid, lid, amount)
    if r != "ok":
        return Out(alert=ctx.t("au_e_" + r))
    out = await auction_view(ctx, lid)
    out.alert = ctx.t("au_ok")
    return out


@action("mkm")
async def my_listings(ctx, arg):
    L = ctx.lang
    docs = await col("market_listings").find({"seller": ctx.uid, "status": "active"}).to_list(10)
    rows = [[(f"❌ {nm(d['item_id'], L).replace('<', '').replace('>', '')} — {fnum(d['bid'] or d['price'], L)}🪙", "mkc", d["_id"])] for d in docs]
    rows.append(nav(ctx, ("mkt", "")))
    return Out(head(ctx, "ttl_mkt") + (ctx.t("mk_mine_body") if docs else ctx.t("mk_empty")), rows)


@action("mkc")
async def listing_cancel(ctx, arg):
    r = await market_cancel(ctx.uid, arg)
    if r != "ok":
        return Out(alert=ctx.t("mk_e_cant"))
    out = await my_listings(ctx, "")
    out.alert = ctx.t("mk_cancelled")
    return out


# ---- NPC shop -------------------------------------------------------------------------------------
@action("shp")
async def shop(ctx, arg):
    L = ctx.lang
    stock = shop_stock(today(), ((await get_char(ctx.uid)) or {}).get("race"))
    page = int(arg or 0)
    pages = math.ceil(len(stock) / PER)
    page = max(0, min(page, pages - 1))
    ids = stock[page * PER:(page + 1) * PER]
    pm = await price_mult()
    prices = {i: max(1, int(ALL[i]['base_price'] * pm)) for i in ids}
    rows = [[(f"{nm(i, L).replace('<', '').replace('>', '')} — {fnum(prices[i], L)}🪙", "sv", i)] for i in ids]
    pg = []
    if page > 0:
        pg.append(("◀️", "shp", str(page - 1)))
    if page < pages - 1:
        pg.append(("▶️", "shp", str(page + 1)))
    if pg:
        rows.append(pg)
    rows.append(nav(ctx, ("mkt", "")))
    # the stock turns over at 00:00 UTC, which is 03:30 in Tehran. Show that clock time, not only a countdown.
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    left = int((now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1) - now).total_seconds() // 60)
    h, m = divmod(left, 60)
    reset = (f"🕓 ریست بعدی فروشگاه: ۰۳:۳۰ (به وقت تهران) — {fnum(h, L)} ساعت و {fnum(m, L)} دقیقه دیگر" if L == "fa"
             else f"🕓 Next shop reset: 03:30 Tehran time — in {h}h {m}m")
    return Out(head(ctx, "ttl_shp") + ctx.t("shp_body", p=fnum(page + 1, L), n=fnum(pages, L)) + "\n" + reset, rows)


async def _shop_item_view(ctx, item_id, note=""):
    L = ctx.lang
    st = await game_settings()
    unit = await shop_price(item_id)
    lines = []
    for q in SHOP_QTYS:
        _, total, disc = await shop_quote(item_id, q)
        tag = f" (−{int(round(disc * 100))}٪)" if disc and L == "fa" else f" (−{int(round(disc * 100))}%)" if disc else ""
        lines.append(f"×{fnum(q, L)} → {fnum(total, L)}🪙{tag}")
    hdr = ("🛒 خرید تعدادی (تخفیف حجمی):" if L == "fa" else "🛒 Bulk buy (volume discount):")
    body = head(ctx, "ttl_shp") + item_card(ctx, item_id, shop_price=unit) + "\n\n" + hdr + "\n" + "\n".join(lines)
    if note:
        body += "\n\n" + note
    rows = [[(f"{'🟢 ' if q == 1 else ''}×{fnum(q, L)}", "sb", f"{item_id}|{q}") for q in SHOP_QTYS], nav(ctx, ("shp", "0"))]
    return Out(body, rows)


@action("sv")
async def shop_view(ctx, arg):
    if arg not in shop_stock(today(), ((await get_char(ctx.uid)) or {}).get("race")):
        return Out(alert=ctx.t("mk_gone"))
    return await _shop_item_view(ctx, arg)


@action("sb")
async def shop_buy_cb(ctx, arg):
    iid, _, q = (arg or "").partition("|")
    try:
        qty = int(q) if q else 1
    except ValueError:
        qty = 1
    r = await shop_buy(ctx.uid, iid, today(), qty)
    if r != "ok":
        return Out(alert=ctx.t("mk_e_" + r))
    from service_player import bump_quest
    await bump_quest(ctx.uid, "market_buy", 1)
    # stay on the same item so the player can buy more, instead of being thrown back to page 1 of the shop
    ch = await get_char(ctx.uid)
    left = fnum((ch or {}).get("coins", 0), ctx.lang)
    note = (f"✅ خرید انجام شد! ×{fnum(qty, ctx.lang)} — موجودی: {left}🪙" if ctx.lang == "fa" else f"✅ Bought ×{qty}! Balance: {left}🪙")
    out = await _shop_item_view(ctx, iid, note)
    out.alert = ctx.t("mk_bought")
    return out


# ---- gacha ------------------------------------------------------------------------------------------
@action("gch")
async def gacha(ctx, arg):
    L = ctx.lang
    st = await game_settings()
    g = await gacha_doc(ctx.uid)
    rates = " | ".join(f"{RARITY_ICON[r]} {pctf(p, L)}" for r, p in GACHA_RATES.items())
    body = ctx.t("gch_body", cost=fnum(st["gacha_cost"], L), rates=rates, pr=fnum(int(st["gacha_pity_rare"]) - g["since_rare"], L),
                 pl=fnum(int(st["gacha_pity_legendary"]) - g["since_leg"], L), total=fnum(g["total"], L), owned=fnum(len(g["chars"]), L), allc=fnum(len(CHARS), L))
    rows = [[(ctx.t("b_pull1") + f" ({fnum(st['gacha_cost'], L)})", "gp", "1")],
            [(ctx.t("b_pull10") + f" ({fnum(int(st['gacha_cost']) * 10, L)})", "gp", "10")],
            [(ctx.t("m_pty"), "pty", "0")],
            [(("💱 فروش احضارها" if L == "fa" else "💱 Sell summons"), "gsl", "0")], nav(ctx)]
    return Out(head(ctx, "ttl_gch") + body, rows)


@action("gsl")
async def gacha_sell_list(ctx, arg):
    """Summoned characters you can sell, with what each one is worth."""
    L = ctx.lang
    st = await game_settings()
    g = await gacha_doc(ctx.uid)
    in_party = set((await get_char(ctx.uid) or {}).get("party") or [])
    rate = float(st.get("coin_rate", 1.0))
    owned = sorted(g["chars"].items(), key=lambda kv: (-RARITIES.index(CHAR_BY_ID[kv[0]]["rarity"]), kv[0]))
    page = int(arg or 0)
    pages = max(1, math.ceil(len(owned) / PER))
    page = max(0, min(page, pages - 1))
    rows = []
    for cid, copies in owned[page * PER:(page + 1) * PER]:
        c = CHAR_BY_ID[cid]
        pay = char_sell_value(cid, copies, rate)
        on = "✅ " if cid in in_party else ""
        label = f"{on}{RARITY_ICON[c['rarity']]} {c['name_fa' if L == 'fa' else 'name_en']} ×{fnum(copies, L)} · {fnum(pay, L)} 🪙"
        rows.append([(label, "gsc", f"{cid}.{page}")])
    pg = []
    if page > 0:
        pg.append(("◀️", "gsl", str(page - 1)))
    if page < pages - 1:
        pg.append(("▶️", "gsl", str(page + 1)))
    if pg:
        rows.append(pg)
    if owned:
        rows.append([("☑️ انتخاب چندتایی و فروش" if L == "fa" else "☑️ Select multiple & sell", "gml", str(page))])
    rows.append(nav(ctx, ("gch", "")))
    body = ("اینجا احضارهایی که داری و قیمت فروششون. روی هر احضار بزن و تعداد فروش رو (×۱، ×۵، ×۱۰ یا همه) انتخاب کن. فقط با فروش همه‌ی نسخه‌ها از پارتی حذف میشه."
            if L == "fa" else
            "Summons you own and what each one sells for. Tap one and pick how many copies to sell (×1, ×5, ×10 or all). It leaves the party only when every copy is sold.")
    if owned:
        body += "\n✅ = در پارتی (فعال)" if L == "fa" else "\n✅ = in your party (active)"
    else:
        body = "هنوز احضاری نداری." if L == "fa" else "You have no summons yet."
    return Out(head(ctx, "ttl_gch") + body, rows)


@action("gsc")
async def gacha_sell_confirm(ctx, arg):
    """Pick how many copies to sell (like the shop's quantity row), then confirm: a sale is permanent."""
    L = ctx.lang
    cid, _, rest = arg.partition(".")
    page, _, q = rest.partition(".")
    g = await gacha_doc(ctx.uid)
    copies = int(g["chars"].get(cid, 0) or 0)
    if copies <= 0:
        return Out(alert=("این احضار دیگه مال تو نیست." if L == "fa" else "You no longer own this summon."))
    n = copies if q == "all" else max(1, min(int(q or 1), copies))
    st = await game_settings()
    rate = float(st.get("coin_rate", 1.0))
    c = CHAR_BY_ID[cid]
    name = c["name_fa" if L == "fa" else "name_en"]
    active = (cid in ((await get_char(ctx.uid) or {}).get("party") or []))
    lines = []
    qopts = [x for x in (1, 5, 10) if x < copies] + [copies]
    for x in qopts:
        lines.append(f"×{fnum(x, L)} → {fnum(char_sell_value(cid, x, rate), L)} 🪙")
    pay = char_sell_value(cid, n, rate)
    rm = n >= copies
    body = ((("✅ در پارتی (فعال)\n" if active else "") + f"{RARITY_ICON[c['rarity']]} <b>{esc(name)}</b> (داری: {fnum(copies, L)})\n"
             + "\n".join(lines) + f"\n\nانتخاب تو: ×{fnum(n, L)} = {fnum(pay, L)} 🪙"
             + ("\n⚠️ با فروش همه‌ی نسخه‌ها از پارتی هم حذف میشه." if rm and active else "") + "\nاین کار برگشت ندارد.")
            if L == "fa" else
            ((("✅ In your party (active)\n" if active else "") + f"{RARITY_ICON[c['rarity']]} <b>{esc(name)}</b> (you own {fnum(copies, L)})\n"
              + "\n".join(lines) + f"\n\nYour pick: ×{fnum(n, L)} = {fnum(pay, L)} 🪙"
              + ("\n⚠️ Selling every copy also removes it from the party." if rm and active else "") + "\nThis cannot be undone.")))
    pg = page or "0"
    qrow = [(f"{'🟢 ' if (x == n) else ''}×{fnum(x, L)}", "gsc", f"{cid}.{pg}.{'all' if x == copies else x}") for x in qopts]
    rows = [qrow, [("✅ فروش" if L == "fa" else "✅ Sell", "gsy", f"{cid}.{pg}.{'all' if rm else n}")], nav(ctx, ("gsl", pg))]
    return Out(head(ctx, "ttl_gch") + body, rows)


@action("gsy")
async def gacha_sell_do(ctx, arg):
    L = ctx.lang
    cid, _, rest = arg.partition(".")
    page, _, q = rest.partition(".")
    status, pay = await sell_character(ctx.uid, cid, "all" if q in ("", "all") else q)
    if status != "ok":
        return Out(alert=("فروش انجام نشد، دوباره امتحان کن." if L == "fa" else "The sale did not go through. Try again."))
    out = await gacha_sell_list(ctx, page or "0")
    out.alert = (f"💱 فروخته شد: {fnum(pay, 'fa')} 🪙" if L == "fa" else f"💱 Sold for {fnum(pay, 'en')} 🪙")
    return out


# ---- multi-select sell for summons ------------------------------------------------------------
# Same idea as the bag's multi-select: the selection lives in Mongo (collection "gacha_sel", one doc per player) because
# callback_data is capped at 64 bytes. Two sale modes: only the extra copies (keeps 1 of each, so level/stars and the
# party are untouched) or every copy (the summon is gone and leaves the party). Every sale goes through a confirmation.
async def _gsel_get(uid, g):
    d = await col("gacha_sel").find_one({"_id": uid})
    return [c for c in (d or {}).get("chars", []) if c in CHAR_BY_ID and int(g["chars"].get(c, 0) or 0) > 0]


async def _gsel_set(uid, chars):
    if chars:
        await col("gacha_sel").update_one({"_id": uid}, {"$set": {"chars": chars, "at": time.time()}}, upsert=True)
    else:
        await col("gacha_sel").delete_one({"_id": uid})


def _owned_sorted(g):
    return sorted((c for c, n in g["chars"].items() if int(n or 0) > 0 and c in CHAR_BY_ID),
                  key=lambda c: (-RARITIES.index(CHAR_BY_ID[c]["rarity"]), c))


def _gm_page(arg):
    p = (arg or "0").split(":")[0]
    return int(p) if p.lstrip("-").isdigit() else 0


async def _gm_view(ctx, page, alert=None):
    L = ctx.lang
    fa = L == "fa"
    g = await gacha_doc(ctx.uid)
    ch = await get_char(ctx.uid) or {}
    in_party = set(ch.get("party") or [])
    rate = float((await game_settings()).get("coin_rate", 1.0))
    owned = _owned_sorted(g)
    sel = await _gsel_get(ctx.uid, g)
    sset = set(sel)
    pages = max(1, math.ceil(len(owned) / PER))
    page = max(0, min(page, pages - 1))
    rows = []
    for cid in owned[page * PER:(page + 1) * PER]:
        c = CHAR_BY_ID[cid]
        copies = int(g["chars"][cid])
        on = cid in sset
        name = c["name_fa" if fa else "name_en"].replace("<", "").replace(">", "")
        label = f"{'☑️' if on else '⬜'} {'✅' if cid in in_party else ''}{RARITY_ICON[c['rarity']]} {name} ×{fnum(copies, L)} · {fnum(char_sell_value(cid, copies, rate), L)} 🪙"
        rows.append([(label, "gmt", f"{cid}:{page}", False, GREEN if on else "none")])
    pg = []
    if page > 0:
        pg.append(("◀️", "gmv", str(page - 1), False, "none"))
    if page < pages - 1:
        pg.append(("▶️", "gmv", str(page + 1), False, "none"))
    if pg:
        rows.append(pg)
    rows.append([("✅ همه‌ی این صفحه" if fa else "✅ Whole page", "gma", str(page), False, "none"),
                 ("🧹 پاک‌کردن انتخاب" if fa else "🧹 Clear", "gmc", str(page), False, "none")])
    present = [r for r in RARITIES if any(CHAR_BY_ID[c]["rarity"] == r for c in owned)]
    if present:  # tap a tier to tick every summon of it; tap again to untick them
        for k in range(0, len(present), 3):
            rows.append([((f"🎯 همه‌ی {RAR_FA.get(r, r)}" if fa else f"🎯 All {r}"), "gmr", f"{r}:{page}", False, "none")
                         for r in present[k:k + 3]])
    if sel:
        n_extra = sum(1 for c in sel if int(g["chars"][c]) > 1)
        rows.append([((f"💱 فروش اضافه‌ها ({fnum(n_extra, L)})" if fa else f"💱 Sell extras ({n_extra})"), "gmx", f"e:{page}", False, GREEN),
                     ((f"💥 فروش همه‌ی نسخه‌ها ({fnum(len(sel), L)})" if fa else f"💥 Sell all copies ({len(sel)})"), "gmx", f"a:{page}", False, RED)])
    rows.append(nav(ctx, ("gsl", str(page))))
    if fa:
        body = (f"☑️ <b>انتخاب چندتایی احضارها</b> | صفحه {fnum(page + 1, L)}/{fnum(pages, L)}\n"
                f"انتخاب‌شده: <b>{fnum(len(sel), L)}</b>\n"
                "روی هر احضار بزن تا تیک بخوره، یا یک رده رو کامل انتخاب کن. انتخاب‌ها بین صفحه‌ها می‌مونه.\n"
                "💱 <b>فروش اضافه‌ها</b>: از هر احضار فقط نسخه‌های تکراری فروخته می‌شه و ۱ نسخه (با سطح و ستاره‌ش) می‌مونه.\n"
                "💥 <b>فروش همه‌ی نسخه‌ها</b>: احضار کامل رفته و از پارتی هم حذف می‌شه.\n✅ = در پارتی")
        if not owned:
            body = "هنوز احضاری نداری."
    else:
        body = (f"☑️ <b>Multi-select summons</b> | page {page + 1}/{pages}\n"
                f"Selected: <b>{len(sel)}</b>\n"
                "Tap summons to tick them, or select a whole tier. Picks survive page changes.\n"
                "💱 <b>Sell extras</b>: only the duplicate copies are sold; 1 copy (with its level and stars) stays.\n"
                "💥 <b>Sell all copies</b>: the summon is gone and leaves your party.\n✅ = in your party")
        if not owned:
            body = "You have no summons yet."
    return Out(head(ctx, "ttl_gch") + body, rows, alert=alert)


@action("gml")
async def gacha_multi_enter(ctx, arg):
    await _gsel_set(ctx.uid, [])  # always start a fresh selection
    return await _gm_view(ctx, _gm_page(arg))


@action("gmv")
async def gacha_multi_view(ctx, arg):
    return await _gm_view(ctx, _gm_page(arg))


@action("gmt")
async def gacha_multi_toggle(ctx, arg):
    cid, _, p = (arg or "").partition(":")
    page = _gm_page(p)
    g = await gacha_doc(ctx.uid)
    if cid not in CHAR_BY_ID or int(g["chars"].get(cid, 0) or 0) <= 0:
        return await _gm_view(ctx, page)
    sel = await _gsel_get(ctx.uid, g)
    if cid in sel:
        sel.remove(cid)
    else:
        sel.append(cid)
    await _gsel_set(ctx.uid, sel)
    return await _gm_view(ctx, page)


@action("gma")
async def gacha_multi_page(ctx, arg):
    page = _gm_page(arg)
    g = await gacha_doc(ctx.uid)
    owned = _owned_sorted(g)
    page = max(0, min(page, max(1, math.ceil(len(owned) / PER)) - 1))
    sel = await _gsel_get(ctx.uid, g)
    for cid in owned[page * PER:(page + 1) * PER]:
        if cid not in sel:
            sel.append(cid)
    await _gsel_set(ctx.uid, sel)
    return await _gm_view(ctx, page)


@action("gmr")
async def gacha_multi_rarity(ctx, arg):
    """Tick every owned summon of one rarity (or untick them if they are all ticked already). arg = rarity:page"""
    rar, _, p = (arg or "").partition(":")
    page = _gm_page(p)
    g = await gacha_doc(ctx.uid)
    ids = [c for c in _owned_sorted(g) if CHAR_BY_ID[c]["rarity"] == rar]
    sel = await _gsel_get(ctx.uid, g)
    if ids and all(c in sel for c in ids):
        sel = [c for c in sel if c not in ids]
    else:
        sel += [c for c in ids if c not in sel]
    await _gsel_set(ctx.uid, sel)
    return await _gm_view(ctx, page)


@action("gmc")
async def gacha_multi_clear(ctx, arg):
    await _gsel_set(ctx.uid, [])
    return await _gm_view(ctx, _gm_page(arg))


def _gm_plan(g, sel, mode):
    """[(cid, qty_to_sell)] for the mode: 'e' = extras only (keep 1), 'a' = every copy."""
    plan = []
    for cid in sel:
        copies = int(g["chars"].get(cid, 0) or 0)
        qty = copies - 1 if mode == "e" else copies
        if qty > 0:
            plan.append((cid, qty, copies))
    return plan


@action("gmx")
async def gacha_multi_confirm(ctx, arg):
    mode, _, p = (arg or "").partition(":")
    page = _gm_page(p)
    L = ctx.lang
    fa = L == "fa"
    g = await gacha_doc(ctx.uid)
    sel = await _gsel_get(ctx.uid, g)
    if not sel or mode not in ("e", "a"):
        return await _gm_view(ctx, page, ("چیزی انتخاب نشده." if fa else "Nothing selected."))
    plan = _gm_plan(g, sel, mode)
    if not plan:
        return await _gm_view(ctx, page, ("نسخه‌ی اضافه‌ای در انتخابت نیست؛ همه‌شون فقط ۱ نسخه‌ان." if fa else "No extra copies in your selection; each one has only 1 copy."))
    rate = float((await game_settings()).get("coin_rate", 1.0))
    party = set((await get_char(ctx.uid) or {}).get("party") or [])
    est = sum(char_sell_value(c, q, rate) for c, q, _ in plan)
    shown = []
    for c, q, copies in plan[:15]:
        d = CHAR_BY_ID[c]
        shown.append(f"• {RARITY_ICON[d['rarity']]} {esc(d['name_fa' if fa else 'name_en'])} ×{fnum(q, L)} <i>({'از' if fa else 'of'} {fnum(copies, L)})</i>")
    if len(plan) > 15:
        shown.append(f"… و {fnum(len(plan) - 15, L)} مورد دیگه" if fa else f"… and {len(plan) - 15} more")
    lost_party = [c for c, q, copies in plan if q >= copies and c in party]
    if fa:
        title = "💱 <b>تأیید فروش اضافه‌ها</b>" if mode == "e" else "💥 <b>تأیید فروش همه‌ی نسخه‌ها</b>"
        warn = (f"\n⚠️ {fnum(len(lost_party), L)} احضار از پارتی حذف می‌شه." if lost_party else "")
        body = f"{title}\n{fnum(len(plan), L)} احضار:\n\n" + "\n".join(shown) + f"\n\n💰 دریافتی: <b>{fnum(est, L)} 🪙</b>{warn}\nاین کار برگشت ندارد. مطمئنی؟"
    else:
        title = "💱 <b>Confirm selling extras</b>" if mode == "e" else "💥 <b>Confirm selling all copies</b>"
        warn = (f"\n⚠️ {len(lost_party)} summon(s) will leave your party." if lost_party else "")
        body = f"{title}\n{len(plan)} summons:\n\n" + "\n".join(shown) + f"\n\n💰 Payout: <b>{fnum(est, L)} 🪙</b>{warn}\nThis cannot be undone. Are you sure?"
    yes = (("✅ تأیید فروش" if fa else "✅ Confirm sale"), "gmy", f"{mode}:{page}", False, RED if mode == "a" else GREEN)
    rows = [[yes], [("❌ لغو" if fa else "❌ Cancel", "gmv", str(page), False, "none")]]
    return Out(head(ctx, "ttl_gch") + body, rows)


@action("gmy")
async def gacha_multi_do(ctx, arg):
    mode, _, p = (arg or "").partition(":")
    page = _gm_page(p)
    fa = ctx.lang == "fa"
    # take the selection atomically: a double tap on "confirm" can never run it twice
    d = await col("gacha_sel").find_one_and_delete({"_id": ctx.uid})
    chars = [c for c in (d or {}).get("chars", []) if c in CHAR_BY_ID]
    if not chars or mode not in ("e", "a"):
        return await _gm_view(ctx, page, ("چیزی انتخاب نشده." if fa else "Nothing selected."))
    g = await gacha_doc(ctx.uid)
    done, total = 0, 0
    for cid, qty, _copies in _gm_plan(g, chars, mode):
        status, pay = await sell_character(ctx.uid, cid, "all" if mode == "a" else qty)
        if status == "retry":  # copies changed under us (a pull landed mid-sale): re-read once and try again
            g2 = await gacha_doc(ctx.uid)
            again = _gm_plan(g2, [cid], mode)
            if again:
                status, pay = await sell_character(ctx.uid, cid, "all" if mode == "a" else again[0][1])
        if status == "ok":
            done += 1
            total += pay
    if not done:
        return await _gm_view(ctx, page, ("فروش انجام نشد؛ احضارها تغییر کرده بودن." if fa else "Nothing was sold; your summons changed."))
    msg = f"✅ {fnum(done, ctx.lang)} احضار فروخته شد: {fnum(total, ctx.lang)} 🪙" if fa else f"✅ Sold {done} summons for {fnum(total, ctx.lang)} 🪙"
    return await _gm_view(ctx, page, msg)


@action("gp")
async def gacha_do(ctx, arg):
    n = 10 if arg == "10" else 1
    res, status = await gacha_pull(ctx.uid, n)
    if status != "ok":
        return Out(alert=ctx.t("gch_e_" + status))
    L = ctx.lang
    lines = []
    for r in res:
        icon = RARITY_ICON[r["rar"]]
        if r["t"] == "jackpot":  # 1 in 10,000
            lines.append(("🎰🌟 <b>جک‌پات احضار!</b> " if L == "fa" else "🎰🌟 <b>SUMMON JACKPOT!</b> ") + f"+{fnum(r['coins'], L)} 🪙"
                         + (f" + {nm(r['id'], L)}" if r.get("id") else "") + " + 🗝")
            continue
        if r["t"] == "char":
            c = CHAR_BY_ID[r["id"]]
            tag = ctx.t("gch_new") if r["copies"] == 1 else ctx.t("gch_dupe", n=fnum(r["copies"], L))
            lines.append(f"{icon} 🎴 <b>{esc(c['name_fa' if L == 'fa' else 'name_en'])}</b> {tag}")
            if c["rarity"] not in ("Common", "Uncommon") and c["name_en"] in CHAR_EPI:
                lines.append("   <i>" + esc(CHAR_EPI[c["name_en"]][0 if L == "fa" else 1]) + "</i>")
        else:
            lines.append(f"{icon} {nm(r['id'], L)}")
    rows = [[(ctx.t("b_pull1"), "gp", "1"), (ctx.t("b_pull10"), "gp", "10")], nav(ctx, ("gch", ""))]
    return Out(head(ctx, "ttl_gch") + "\n".join(lines), rows)


@action("pty")
async def party(ctx, arg):
    L = ctx.lang
    ch = await get_char(ctx.uid)
    g = await gacha_doc(ctx.uid)
    owned = sorted(g["chars"].items(), key=lambda kv: (-RARITIES.index(CHAR_BY_ID[kv[0]]["rarity"]), kv[0]))
    page = int(arg or 0)
    pages = max(1, math.ceil(len(owned) / PER))
    page = max(0, min(page, pages - 1))
    rows = []
    for cid, copies in owned[page * PER:(page + 1) * PER]:
        c = CHAR_BY_ID[cid]
        lvl, star = copies_to_level_star(copies)
        on = "✅ " if cid in ch.get("party", []) else ""
        bonus = ", ".join(f"{ctx.t('bn_' + k)} +{pctf(v * 100, L, '.1f')}" for k, v in char_bonus(cid, copies).items())
        label = f"{on}{RARITY_ICON[c['rarity']]} {c['name_fa' if L == 'fa' else 'name_en']} {ctx.t('lbl_level')} {fnum(lvl, L)}{'★' * star} ({bonus})"
        # one tap on the name adds or removes it from the party. Selling lives in the sell list (gsl), not here, so the
        # team view is never cut across by a trash button (its confirm screen used to send you away from the party).
        rows.append([(label, "pt", f"{cid}.{page}")])
    pg = []
    if page > 0:
        pg.append(("◀️", "pty", str(page - 1)))
    if page < pages - 1:
        pg.append(("▶️", "pty", str(page + 1)))
    if pg:
        rows.append(pg)
    rows.append(nav(ctx, ("gch", "")))
    return Out(head(ctx, "ttl_pty") + (ctx.t("pty_body") if owned else ctx.t("pty_empty")), rows)


@action("pt")
async def party_toggle(ctx, arg):
    cid, _, page = arg.partition(".")
    r = await toggle_party(ctx.uid, cid)
    if r in ("notowned", "full"):
        return Out(alert=ctx.t("pty_e_" + r))
    return await party(ctx, page or "0")


# ---- forge ----------------------------------------------------------------------------------------
@action("frg")
async def forge_panel(ctx, arg):
    L = ctx.lang
    ch = await get_char(ctx.uid)
    wid = ch.get("weapon_id")
    if wid not in ALL:  # race weapon not chosen yet: choose it first
        from handlers_raceweapon import choice_panel
        return await choice_panel(ctx, ch)
    plus = (ch.get("weapon_plus") or {}).get(wid, 0)
    alert = None
    if arg == "go":
        r, extra = await forge(ctx.uid)
        alert = ctx.t("frg_" + r, n=fnum(extra, L))
        ch = await get_char(ctx.uid)
        plus = (ch.get("weapon_plus") or {}).get(wid, 0)
        if r == "ok":  # say what the new level is worth, not just the number (combat uses +6% attack per level)
            alert += (f"\n⚔️ +۶٪ قدرت به جنگ‌افزار اضافه شد (کل ×{round(1 + 0.06 * plus, 2)})" if L == "fa"
                      else f"\n⚔️ +6% attack added (total ×{round(1 + 0.06 * plus, 2)})")
    if plus >= 10:
        body = ctx.t("frg_maxed", name=nm(wid, L), plus=fnum(plus, L))
        rows = [nav(ctx, ("prof", ""))]
    else:
        cost, need = forge_cost(wid, plus)
        body = ctx.t("frg_body", name=nm(wid, L), plus=fnum(plus, L), cost=fnum(cost, L), mats=fnum(need, L), chance=FORGE_CHANCE[plus])
        from service_adventure import stones_needed
        if stones_needed(plus):
            body += "\n" + ctx.t("need_stone", n=fnum(stones_needed(plus), L))
        body += (f"\n⚔️ بونوس فعلی: ×{round(1 + 0.06 * plus, 2)} قدرت" if L == "fa" else f"\n⚔️ Current bonus: ×{round(1 + 0.06 * plus, 2)} attack")
        rows = [[(ctx.t("b_forge_go"), "frg", "go")], nav(ctx, ("prof", ""))]
    return Out(head(ctx, "ttl_frg") + body, rows, alert=alert)
