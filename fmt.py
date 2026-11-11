"""Shared text formatting for items, weapons and characters."""
from data_items import ALL
from data_lore import spirit_line
from data_races import LEVEL_GATES, LOCATIONS, RACES, STAT_ICON, STATS, soft_stat
from database import settings_snapshot
from effects import describe, display_name, evo_title_index
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
        eff = it.get("effect") or {}
        if eff.get("type") in ("mat", "relic", "evo", "cosm", "pet", "tome"):
            names = {}
            if eff.get("loc") in LOCATIONS:
                names["loc"] = LOCATIONS[eff["loc"]]["fa" if lang == "fa" else "en"]
            if eff.get("race") in RACES:
                names["race"] = RACES[eff["race"]]["name_fa" if lang == "fa" else "name_en"]
            lines.append("✦ " + esc(describe(eff, lang, names)))
    if it.get("slot") and it.get("level_req", 1) > 1:
        lines.append(f"🔒 {ctx.t('lbl_level')} {fnum(it['level_req'], lang)}")
    lines.append(f"🪙 {fnum(it['base_price'], lang)} | 💱 {fnum(it.get('sell_price', 0), lang)}")
    return "\n".join(lines)


def stats_block(ctx, stats: dict) -> str:
    return " | ".join(f"{STAT_ICON[k]} {fnum(int(stats[k]), ctx.lang)}" for k in STATS)


def title_of(ch: dict, lang: str) -> str:
    evo = RACES[ch["race"]]["evo"]
    idx = min(evo_title_index(ch, LEVEL_GATES, settings_snapshot()), len(evo) - 1)
    return evo[idx][0 if lang == "fa" else 1]


def shown_name(ch: dict) -> str:
    """Player name with equipped cosmetic glyphs, HTML-escaped."""
    return esc(display_name(ch, ALL))
