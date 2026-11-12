"""Bag, equipment, NPC shop, player market, auctions, gacha and party."""
import math
import time

from data_chars import CHAR_BY_ID, CHARS, GACHA_RATES, char_bonus, copies_to_level_star
from data_items import ALL
from data_lore import CHAR_EPI
from data_weapons import RARITIES, RARITY_ICON
from database import col, game_settings
from fmt import item_card, nm, pctf
from i18n import esc, fnum
from service_economy import (FORGE_CHANCE, auction_bid, equip, forge, forge_cost, gacha_doc, gacha_pull, inv_get, market_buy, market_cancel, market_create,
                             npc_sell, price_mult, settle_listings, shop_buy, shop_stock, slots_used, suggested_price, toggle_party, unequip,
                             use_item)
from service_player import get_char, today
from ui import Out, action, chunk, head, nav

PER = 6
FILTERS = {"a": None, "w": ("weapon",), "e": ("armor", "accessory", "relic", "cosmetic"), "u": ("potion", "kido_card", "book", "egg", "key", "material", "evolution")}


def _rk(i):
    return -RARITIES.index(ALL[i]["rarity"])


# ---- bag ----------------------------------------------------------------------------------
@action("bag")
async def bag(ctx, arg):
    L = ctx.lang
    page_s, _, flt = (arg or "0").partition(":")
    page, flt = int(page_s or 0), (flt or "a")
    inv = await inv_get(ctx.uid)
    ch = await get_char(ctx.uid)
    cats = FILTERS.get(flt)
    ids = sorted([i for i, q in inv["items"].items() if q > 0 and i in ALL and (not cats or ALL[i]["category"] in cats)], key=lambda i: (_rk(i), i))
    pages = max(1, math.ceil(len(ids) / PER))
    page = max(0, min(page, pages - 1))
    rows = [[(f"{nm(i, L).replace('<', '').replace('>', '')} ×{inv['items'][i]}", "iv", i)] for i in ids[page * PER:(page + 1) * PER]]
    fr = [(("• " if flt == k else "") + ctx.t("flt_" + k), "bag", f"0:{k}") for k in FILTERS]
    rows.append(fr)
    pg = []
    if page > 0:
        pg.append(("◀️", "bag", f"{page - 1}:{flt}"))
    if page < pages - 1:
        pg.append(("▶️", "bag", f"{page + 1}:{flt}"))
    if pg:
        rows.append(pg)
    rows.append(nav(ctx))
    eq = f"⚔️ {nm(ch['weapon_id'], L)}\n🛡️ {nm(ch.get('armor_id'), L)}\n💍 {nm(ch.get('acc_id'), L)}\n📿 {nm(ch.get('charm_id'), L)}"
    cap = f"{fnum(slots_used(inv['items']), L)}/{fnum(inv.get('capacity', 50), L)}"
    body = ctx.t("bag_body", cap=cap, eq=eq, n=fnum(len(ids), L))
    return Out(head(ctx, "ttl_bag") + body, rows)


@action("iv")
async def item_view(ctx, arg):
    inv = await inv_get(ctx.uid)
    qty = inv["items"].get(arg, 0)
    if arg not in ALL or qty <= 0:
        return await bag(ctx, "0")
    it = ALL[arg]
    rows = []
    if it.get("slot") or it["category"] == "weapon":
        rows.append([(ctx.t("b_equip"), "eq", arg)])
    ety = (it.get("effect") or {}).get("type")
    if ety in ("kido", "xp", "pet", "buff", "kido_book", "bond"):
        rows.append([(ctx.t("b_use"), "us", arg)])
    elif ety == "relic":
        rows.append([(ctx.t("m_rlc"), "rlc", "")])
    elif ety == "cosmetic":
        rows.append([(ctx.t("m_cos"), "cos", "")])
    elif ety in ("mat", "evo"):
        rows.append([(ctx.t("m_crf"), "crf" if ety == "mat" else "evo", "")])
    elif ety == "key":
        rows.append([(ctx.t("m_evt"), "evt", "")])
    row2 = [(ctx.t("b_sell_npc"), "sl", arg)]
    if it.get("tradeable"):
        row2.append((ctx.t("b_list"), "ml", arg))
    rows.append(row2)
    rows.append(nav(ctx, ("bag", "0")))
    return Out(head(ctx, "ttl_bag") + item_card(ctx, arg, qty), rows)


@action("eq")
async def eq(ctx, arg):
    r = await equip(ctx.uid, arg)
    if r != "ok":
        return Out(alert=ctx.t("eq_" + r))
    out = await bag(ctx, "0")
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
    r, extra = await use_item(ctx.uid, arg)
    if r == "ok":
        out = await bag(ctx, "0")
        out.alert = ctx.t("us_ok", n=fnum(extra if isinstance(extra, int) else 0, ctx.lang))
        return out
    return Out(alert=ctx.t("us_" + r, n=extra or 0))


@action("sl")
async def sell_npc(ctx, arg):
    inv = await inv_get(ctx.uid)
    n = await npc_sell(ctx.uid, arg, 1)
    if not n:
        return Out(alert=ctx.t("sell_fail"))
    out = await bag(ctx, "0")
    out.alert = ctx.t("sell_ok", n=fnum(n, ctx.lang))
    return out


# ---- listing flow -----------------------------------------------------------------------------
@action("ml")
async def market_list_prompt(ctx, arg):
    it = ALL.get(arg)
    if not it:
        return await bag(ctx, "0")
    sp = await suggested_price(arg)
    kind = "auction" if it["rarity"] in ("Epic", "Legendary", "Mythic") else "fixed"
    rows = [[(f"{fnum(int(sp * m / 10), ctx.lang)} 🪙", "mlp", f"{arg}.{m}")] for m in (7, 10, 15, 22)]
    rows = chunk([r[0] for r in rows], 2)
    rows.append(nav(ctx, ("iv", arg)))
    note = ctx.t("ml_auction") if kind == "auction" else ctx.t("ml_fixed")
    return Out(head(ctx, "ttl_mkt") + item_card(ctx, arg) + f"\n\n{note}\n" + ctx.t("ml_pick", sp=fnum(sp, ctx.lang)), rows)


@action("mlp")
async def market_list_do(ctx, arg):
    iid, _, m = arg.partition(".")
    it = ALL.get(iid)
    if not it:
        return Out()
    sp = await suggested_price(iid)
    price = max(1, int(sp * int(m) / 10))
    kind = "auction" if it["rarity"] in ("Epic", "Legendary", "Mythic") else "fixed"
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
    stock = shop_stock(today())
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
    return Out(head(ctx, "ttl_shp") + ctx.t("shp_body", p=fnum(page + 1, L), n=fnum(pages, L)), rows)


@action("sv")
async def shop_view(ctx, arg):
    if arg not in shop_stock(today()):
        return Out(alert=ctx.t("mk_gone"))
    return Out(head(ctx, "ttl_shp") + item_card(ctx, arg), [[(ctx.t("b_buy"), "sb", arg)], nav(ctx, ("shp", "0"))])


@action("sb")
async def shop_buy_cb(ctx, arg):
    r = await shop_buy(ctx.uid, arg, today())
    if r != "ok":
        return Out(alert=ctx.t("mk_e_" + r))
    from service_player import bump_quest
    await bump_quest(ctx.uid, "market_buy", 1)
    out = await shop(ctx, "0")
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
            [(ctx.t("m_pty"), "pty", "0")], nav(ctx)]
    return Out(head(ctx, "ttl_gch") + body, rows)


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
        rows.append([(f"{on}{RARITY_ICON[c['rarity']]} {c['name_fa' if L == 'fa' else 'name_en']} {ctx.t('lbl_level')} {fnum(lvl, L)}{'★' * star} ({bonus})", "pt", f"{cid}.{page}")])
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
    plus = (ch.get("weapon_plus") or {}).get(wid, 0)
    alert = None
    if arg == "go":
        r, extra = await forge(ctx.uid)
        alert = ctx.t("frg_" + r, n=fnum(extra, L))
        ch = await get_char(ctx.uid)
        plus = (ch.get("weapon_plus") or {}).get(wid, 0)
    if plus >= 10:
        body = ctx.t("frg_maxed", name=nm(wid, L), plus=fnum(plus, L))
        rows = [nav(ctx, ("prof", ""))]
    else:
        cost, need = forge_cost(wid, plus)
        body = ctx.t("frg_body", name=nm(wid, L), plus=fnum(plus, L), cost=fnum(cost, L), mats=fnum(need, L), chance=FORGE_CHANCE[plus])
        rows = [[(ctx.t("b_forge_go"), "frg", "go")], nav(ctx, ("prof", ""))]
    return Out(head(ctx, "ttl_frg") + body, rows, alert=alert)
