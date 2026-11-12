"""Panels for crafting, companions (pets/eggs), relics & cosmetics, and evolution."""
import math

from data_crafting import CATS, RECIPES, get_recipe, mat_candidates, missing, upgrade_of
from data_items import ALL
from data_races import LEVEL_GATES, RACES
from database import game_settings
from effects import active_buffs, passive_mods, relic_slots
from fmt import item_card, nm, pctf, title_of
from i18n import esc, fnum
from service_economy import PETS, inv_get
from service_effects import (craft, craft_coins, evolve, set_active_pet, unequip_cosmetic, unequip_relic)
from service_player import get_char
from ui import Out, action, head, nav

PER = 6
ROLE_ICON = {"fang": "🗡️", "heal": "💚", "luck": "🍀"}


def _plain(s):
    return s.replace("<", "").replace(">", "")


# ---- crafting ----------------------------------------------------------------------------------------------------
@action("crf")
async def craft_home(ctx, arg):
    rows = [[(ctx.t("crc_" + c), "crl", f"{c}:0")] for c in CATS]
    rows.append(nav(ctx, ("prof", "")))
    return Out(head(ctx, "ttl_crf") + ctx.t("crf_body"), rows)


async def _recipes_for(ctx, ch, inv, cat):
    if cat == "upgrade":
        from data_crafting import upgrade_recipe
        ids = [i for i, q in inv["items"].items() if q > 0 and i in ALL and upgrade_of(i)]
        return [upgrade_recipe(i) for i in sorted(ids)]
    out = [r for r in RECIPES.values() if r["cat"] == cat]
    if cat == "evo":
        out = [r for r in out if ALL[r["out"]]["effect"]["race"] in ("*", ch["race"])]
    return sorted(out, key=lambda r: r["id"])


@action("crl")
async def craft_list(ctx, arg):
    cat, _, pg = (arg or "potion:0").partition(":")
    if cat not in CATS:
        return await craft_home(ctx, "")
    ch, inv, L = await get_char(ctx.uid), None, ctx.lang
    inv = await inv_get(ctx.uid)
    recs = await _recipes_for(ctx, ch, inv, cat)
    pages = max(1, math.ceil(len(recs) / PER))
    page = max(0, min(int(pg or 0), pages - 1))
    rows = []
    for r in recs[page * PER:(page + 1) * PER]:
        can = not any(missing(inv["items"], r)) and (not r.get("src") or inv["items"].get(r["src"], 0) > 0)
        rows.append([(("✅ " if can else "▫️ ") + _plain(nm(r["out"], L)), "crd", r["id"])])
    pg_row = []
    if page > 0:
        pg_row.append(("◀️", "crl", f"{cat}:{page - 1}", False, "none"))
    if page < pages - 1:
        pg_row.append(("▶️", "crl", f"{cat}:{page + 1}", False, "none"))
    if pg_row:
        rows.append(pg_row)
    rows.append(nav(ctx, ("crf", "")))
    body = ctx.t("crl_body", cat=ctx.t("crc_" + cat)) if recs else ctx.t("crl_empty_" + cat)
    return Out(head(ctx, "ttl_crf") + body, rows)


def _need_lines(ctx, rec, inv):
    L, lines = ctx.lang, []
    miss = missing(inv["items"], rec)
    if rec.get("src"):
        have = inv["items"].get(rec["src"], 0) > 0
        lines.append(f"{'✅' if have else '❌'} {nm(rec['src'], L)} ×1")
    for inp, m in zip(rec["inputs"], miss):
        tags = " / ".join(ctx.t("tag_" + t) for t in inp["tags"][:3]) + ("…" if len(inp["tags"]) > 3 else "")
        have = inp["qty"] - m
        lines.append(f"{'✅' if m == 0 else '❌'} {tags} ≥{inp['pw']} ×{fnum(have, L)}/{fnum(inp['qty'], L)}")
    return lines


@action("crd")
async def craft_detail(ctx, arg, alert=None):
    rec = get_recipe(arg)
    if not rec:
        return await craft_home(ctx, "")
    st, inv, L = await game_settings(), await inv_get(ctx.uid), ctx.lang
    lines = [item_card(ctx, rec["out"]), "", ctx.t("crd_needs")] + _need_lines(ctx, rec, inv)
    lines.append(f"🪙 {fnum(craft_coins(rec, st), L)}")
    if rec.get("min_level", 1) > 1:
        lines.append(f"🔒 {ctx.t('lbl_level')} {fnum(rec['min_level'], L)}")
    rows = [[(ctx.t("b_craft_go"), "crx", rec["id"])], nav(ctx, ("crl", f"{rec['cat']}:0"))]
    out = Out(head(ctx, "ttl_crf") + "\n".join(lines), rows)
    out.alert = alert
    return out


@action("crx")
async def craft_do(ctx, arg):
    r, extra = await craft(ctx.uid, arg)
    if r == "ok":
        return await craft_detail(ctx, arg, alert=ctx.t("cr_ok", item=_plain(nm(extra, ctx.lang))))
    return Out(alert=ctx.t("cr_" + r, n=fnum(extra or 0, ctx.lang)))


# ---- companions ---------------------------------------------------------------------------------------------------
@action("pet")
async def pets_panel(ctx, arg):
    L, ch = ctx.lang, await get_char(ctx.uid)
    pets = ch.get("pets") or []
    page = max(0, min(int(arg or 0), max(0, math.ceil(len(pets) / PER) - 1)))
    rows = []
    for i in range(page * PER, min(len(pets), (page + 1) * PER)):
        p = pets[i]
        nmx = PETS[p.get("sp", 0) % len(PETS)][0 if L == "en" else 1]
        mark = "✅ " if i == 0 else ""
        rows.append([(f"{mark}{ROLE_ICON[p.get('role', 'fang')]} {nmx} · T{p.get('tier', 0) + 1}", "pta", f"{i}.{page}")])
    pg_row = []
    if page > 0:
        pg_row.append(("◀️", "pet", str(page - 1), False, "none"))
    if (page + 1) * PER < len(pets):
        pg_row.append(("▶️", "pet", str(page + 1), False, "none"))
    if pg_row:
        rows.append(pg_row)
    rows.append(nav(ctx, ("prof", "")))
    inc = ch.get("incubator")
    lines = [ctx.t("pet_body") if pets else ctx.t("pet_empty")]
    if inc:
        lines.append(ctx.t("pet_incubating", n=fnum(max(0, inc["left"]), L), role=ctx.t("role_" + inc["role"])))
    return Out(head(ctx, "ttl_pet") + "\n".join(lines), rows)


@action("pta")
async def pet_activate(ctx, arg):
    i, _, page = arg.partition(".")
    r = await set_active_pet(ctx.uid, int(i))
    if r in ("empty", "retry"):
        return Out(alert=ctx.t("pet_e_" + r))
    return await pets_panel(ctx, page or "0")


# ---- relics & cosmetics ----------------------------------------------------------------------------------
@action("rel")
async def relics_panel(ctx, arg):
    L, ch, st = ctx.lang, await get_char(ctx.uid), await game_settings()
    slots = relic_slots(ch["level"], st)
    rel = ch.get("relics") or []
    rows, lines = [], [ctx.t("rel_body", used=fnum(min(len(rel), slots), L), slots=fnum(slots, L),
                             lv=fnum(int(st["relic_slot1_level"]), L), lv2=fnum(int(st["relic_slot2_level"]), L))]
    for iid in rel[:slots]:
        rows.append([("➖ " + _plain(nm(iid, L)), "urel", iid, False, "danger")])
    cs = ch.get("cosmetic") or {}
    for slot in ("aura", "trail", "banner"):
        if cs.get(slot):
            rows.append([("➖ " + _plain(nm(cs[slot], L)), "ucos", slot, False, "danger")])
    pm = passive_mods(ch, ALL, st)
    bits = [f"+{pctf(pm['xp_pct'], L)} {ctx.t('xp_word')}" if pm["xp_pct"] else "", f"+{pctf(pm['coin_pct'], L)} 🪙" if pm["coin_pct"] else "",
            f"+{pctf(pm['drop_pct'], L)} 🎁" if pm["drop_pct"] else "", f"🏅 {pm['fame']}" if pm["fame"] else ""]
    bits = [b for b in bits if b]
    if bits:
        lines.append(" · ".join(bits))
    for k, v in active_buffs(ch).items():
        lines.append("🕯️ " + ctx.t("fx_buff_" + k, pct=f"{v:g}"))
    rows.append(nav(ctx, ("prof", "")))
    return Out(head(ctx, "ttl_rel") + "\n".join(lines), rows)


@action("urel")
async def unequip_relic_act(ctx, arg):
    r = await unequip_relic(ctx.uid, arg)
    if r != "ok":
        return Out(alert=ctx.t("ueq_" + ("full" if r == "full" else "empty")))
    return await relics_panel(ctx, "")


@action("ucos")
async def unequip_cosmetic_act(ctx, arg):
    r = await unequip_cosmetic(ctx.uid, arg)
    if r != "ok":
        return Out(alert=ctx.t("ueq_" + r))
    return await relics_panel(ctx, "")


# ---- evolution ---------------------------------------------------------------------------------------------------
@action("evo")
async def evolve_act(ctx, arg):
    r, extra = await evolve(ctx.uid, arg)
    if r == "ok":
        ch = await get_char(ctx.uid)
        from handlers_items import bag
        out = await bag(ctx, "0")
        out.alert = ctx.t("evo_ok", title=title_of(ch, ctx.lang))
        return out
    return Out(alert=ctx.t("evo_" + r, n=fnum(extra or 0, ctx.lang)))
