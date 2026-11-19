"""Shared text formatting for items, weapons and characters."""
from data_crafting import PET_ROLES, race_title_ev
from data_items import ALL
from data_lore import spirit_line
from data_races import LOCATIONS, RACES, STAT_ICON, STATS, soft_stat
from data_weapons import ELEMENT_FA, RARITY_FA, RARITY_ICON, TYPE_FA, skill_text
from i18n import esc, fnum


def nm(item_id, lang: str) -> str:
    it = ALL.get(item_id or "")
    if not it:
        return "—"
    return f"{RARITY_ICON[it['rarity']]} {esc(it['name_fa' if lang == 'fa' else 'name_en'])}"


def rarity_name(rarity: str, lang: str) -> str:
    return RARITY_FA.get(rarity, rarity) if lang == "fa" else rarity


def pctf(value, lang: str, spec: str = "g") -> str:
    """A percentage in one script only: Persian digits and ٪ for fa, Latin digits and % for en."""
    s = format(value, spec)
    return s.translate(str.maketrans("0123456789.-", "۰۱۲۳۴۵۶۷۸۹٫-")) + "٪" if lang == "fa" else s + "%"


def race_name(race: str, lang: str) -> str:
    return RACES[race]["name_fa" if lang == "fa" else "name_en"]


def item_card(ctx, item_id: str, qty: int = None, shop_price: int = None) -> str:
    it = ALL[item_id]
    lang = ctx.lang
    lines = [f"<b>{nm(item_id, lang)}</b>" + (f"  ×{fnum(qty, lang)}" if qty else "")]
    lines.append(f"{ctx.t('lbl_rarity')}: {rarity_name(it['rarity'], lang)} | {ctx.t('cat_' + it['category'])}")
    if it["category"] == "weapon":
        el = ELEMENT_FA[it["element"]] if lang == "fa" else it["element"].title()
        ty = TYPE_FA[it["weapon_type"]] if lang == "fa" else it["weapon_type"].title()
        if it.get("meaning_en"):
            lines.append("「" + esc(it["meaning_fa" if lang == "fa" else "meaning_en"]) + "」")
        lines.append(f"⚔️ {fnum(it['attack'], lang)} | 🎯 {pctf(it['crit'] * 100, lang, '.1f')} | {el} | {ty}")
        _sl = spirit_line(it, lang)
        if _sl:
            lines.append("<i>" + esc(_sl) + "</i>")
        for s in it["skills"]:
            lines.append("✦ " + skill_text(s, lang))
    else:
        lines.append(esc(it.get("desc_fa" if lang == "fa" else "desc_en", "")))
        eff_line = effect_text(ctx, it)
        if eff_line:
            lines.append("✦ " + eff_line)
    if it["category"] == "accessory" and it.get("subtype") in ("ring", "necklace"):
        lines.append(("💍 جای نشان/انگشتر" if it["subtype"] == "ring" else "📿 جای گردن/سر") if lang == "fa"
                     else ("💍 Badge/ring slot" if it["subtype"] == "ring" else "📿 Neck/head slot"))
    if it.get("slot") and it.get("level_req", 1) > 1:
        lines.append(f"🔒 {ctx.t('lbl_level')} {fnum(it['level_req'], lang)}")
    price = it["base_price"] if shop_price is None else shop_price  # shop shows the scarcity-adjusted price it charges
    lines.append(f"🪙 {fnum(price, lang)} | 💱 {fnum(it.get('sell_price', 0), lang)}")
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
    if ty == "kido":  # a numbered Hadō / Bakudō card: what the spell does in a fight (numbers from engine.py)
        import math
        n = int(e["num"])
        if e["branch"] == "had":
            import data_kido as _KD
            return (f"هادو {n}: جادوی تهاجمی؛ ضریب آسیب ×{0.7 + 0.3 * n:.1f}؛ هزینه {_KD.cost_pct('had', n):g}٪ ریاتسوی حداکثر"
                    if L == "fa" else f"Hadō {n}: attack spell; damage ×{0.7 + 0.3 * n:.1f}; costs {_KD.cost_pct('had', n):g}% of max reiatsu")
        import data_kido as _KD
        return (f"باکودو {n}: سپر محافظ + {min(60, 10 + 5 * n)}٪ شانس بستن دشمن (نصف روی باس)؛ هزینه {_KD.cost_pct('bak', n):g}٪ ریاتسوی حداکثر"
                if L == "fa" else f"Bakudō {n}: a shield + {min(60, 10 + 5 * n)}% chance to bind the foe (half on bosses); costs {_KD.cost_pct('bak', n):g}% of max reiatsu")
    if ty == "kido_book":
        br = ("هادو" if e["branch"] == "had" else "باکودو") if L == "fa" else ("Hadō" if e["branch"] == "had" else "Bakudō")
        return (f"کوچک‌ترین {br}ی یادنگرفته را تا شماره‌ی {e['cap']} یاد می‌دهد." if L == "fa"
                else f"Teaches your lowest unknown {br} up to number {e['cap']}.")
    if ty == "xp":
        return f"+{fnum(int(e['amount']), L)} تجربه" if L == "fa" else f"+{fnum(int(e['amount']), L)} XP"
    if ty == "bond":
        return f"+{fnum(int(e['amount']), L)} پیوند با زانپاکتو" if L == "fa" else f"+{fnum(int(e['amount']), L)} Zanpakutō bond"
    if ty == "cosmetic":
        return ctx.t("ef_cosmetic", icon=e["icon"], slot=ctx.t("cos_slot_" + e["slot"]), fame=e["fame"])
    if ty == "evo":
        return ctx.t("ef_evo")
    if ty == "almighty":
        return ctx.t("ef_almighty", m=e["minutes"])
    if ty == "konpaku":  # SENKA+ charm
        return ctx.t("ef_konpaku", m=e["minutes"])
    if ty == "buff":  # temporary buff: its exact size and length (some descriptions only said "stronger" / "less damage")
        names = {"dmg": ("آسیب", "damage"), "def": ("دفاع", "defence"), "crit": ("شانس ضربه‌ی بحرانی", "crit chance"),
                 "xp": ("تجربه", "XP"), "drop": ("شانس دراپ", "drop chance")}
        nfa, nen = names.get(e.get("stat"), (str(e.get("stat")), str(e.get("stat"))))
        pct, mins = float(e.get("pct", 0)) * 100, int(e.get("minutes", 0))
        return (f"+{pctf(pct, L)} {nfa} · {fnum(mins, L)} دقیقه" if L == "fa" else f"+{pctf(pct, L)} {nen} · {mins} min")
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
