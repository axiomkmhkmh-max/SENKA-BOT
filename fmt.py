"""Shared text formatting for items, weapons and characters."""
from data_crafting import PET_ROLES, race_title_ev
from data_items import ALL
from data_lore import spirit_line
from data_races import LOCATIONS, RACES, STAT_ICON, STATS, soft_stat
from data_weapons import ELEMENT_FA, RARITY_ICON, TYPE_FA, skill_text
from i18n import esc, fnum


def nm(item_id, lang: str) -> str:
    it = ALL.get(item_id or "")
    if not it:
        return "—"
    return f"{RARITY_ICON[it['rarity']]} {esc(it['name_fa' if lang == 'fa' else 'name_en'])}"


def race_name(race: str, lang: str) -> str:
    return RACES[race]["name_fa" if lang == "fa" else "name_en"]


def item_card(ctx, item_id: str, qty: int = None) -> str:
    it = ALL[item_id]
    lang = ctx.lang
    lines = [f"<b>{nm(item_id, lang)}</b>" + (f"  ×{fnum(qty, lang)}" if qty else "")]
    lines.append(f"{ctx.t('lbl_rarity')}: {it['rarity']} | {ctx.t('cat_' + it['category'])}")
    if it["category"] == "weapon":
        el = ELEMENT_FA[it["element"]] if lang == "fa" else it["element"].title()
        ty = TYPE_FA[it["weapon_type"]] if lang == "fa" else it["weapon_type"].title()
        if it.get("meaning_en"):
            lines.append("「" + esc(it["meaning_fa" if lang == "fa" else "meaning_en"]) + "」")
        lines.append(f"⚔️ {fnum(it['attack'], lang)} | 🎯 {it['crit'] * 100:.1f}% | {el} | {ty}")
        lines.append("<i>" + esc(spirit_line(it, lang)) + "</i>")
        for s in it["skills"]:
            lines.append("✦ " + skill_text(s, lang))
    else:
        lines.append(esc(it.get("desc_fa" if lang == "fa" else "desc_en", "")))
        eff_line = effect_text(ctx, it)
        if eff_line:
            lines.append("✦ " + eff_line)
    if it.get("slot") and it.get("level_req", 1) > 1:
        lines.append(f"🔒 {ctx.t('lbl_level')} {fnum(it['level_req'], lang)}")
    lines.append(f"🪙 {fnum(it['base_price'], lang)} | 💱 {fnum(it.get('sell_price', 0), lang)}")
    return "\n".join(lines)


def stats_block(ctx, stats: dict) -> str:
    return " | ".join(f"{STAT_ICON[k]} {fnum(int(stats[k]), ctx.lang)}" for k in STATS)


def title_of(ch: dict, lang: str) -> str:
    return race_title_ev(ch["race"], ch["level"], ch.get("evo"), lang)


def effect_text(ctx, it: dict) -> str:
    """One plain Bleach-flavoured line describing what an item really does (read from its data fields)."""
    L = ctx.lang
    e = it.get("effect") or {}
    ty = e.get("type")
    if ty == "mat":
        from data_crafting import forge_value
        return ctx.t("ef_mat", grp=ctx.t("grp_" + e["group"]), v=forge_value(it["rarity"]))
    if ty == "relic":
        loc = LOCATIONS[e["loc"]]["fa" if L == "fa" else "en"] if e.get("loc") else ""
        return ctx.t("ef_relic_" + e["kind"], v=f"{e['v'] * 100:g}", loc=esc(loc))
    if ty == "cosmetic":
        return ctx.t("ef_cosmetic", icon=e["icon"], slot=ctx.t("cos_slot_" + e["slot"]), fame=e["fame"])
    if ty == "evo":
        return ctx.t("ef_evo")
    if ty == "pet":
        return ctx.t("ef_egg")
    if ty == "key":
        from data_world import KEY_PTS
        return ctx.t("ef_key", pts=KEY_PTS.get(e["diff"], 1))
    if it.get("category") == "armor":
        return ctx.t("ef_armor")
    if it.get("category") == "accessory" and it.get("stats", {}).get("luck"):
        return ctx.t("ef_luck", n=it["stats"]["luck"])
    return ""


def pet_line(ctx, pet: dict) -> str:
    from service_economy import PETS
    role, per = PET_ROLES.get(pet["sp"] % len(PET_ROLES), ("dmg", 0.01))
    name = PETS[pet["sp"] % len(PETS)][0 if ctx.lang != "fa" else 1]
    return f"{esc(name)} ★{pet['tier'] + 1} — " + ctx.t("pet_role_" + role, v=f"{per * (pet['tier'] + 1) * 100:.1f}")
