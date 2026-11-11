"""Pure item-effect logic (no database). Every item effect is data in item["effect"];
this module is the single registry that reads it: describing it, validating it and
turning equipped/active effects into numeric modifiers."""
import math
import time

from i18n import t

# ---- tunables (defaults mirrored in config.GAME_DEFAULTS) ------------------------------------
DEFAULTS = {
    "relic_slot2_level": 50, "relic_slot1_level": 20, "relic_effect_mult": 1.0,
    "pet_fang_pct": 1.0, "pet_heal_pct": 0.5, "pet_luck_pct": 1.0, "egg_hatch_explores": 5,
    "book_buff_minutes": 30, "evo_item_required": 1, "evo_coin_cost": 5000,
}

COSM_SLOTS = ("aura", "trail", "banner")
BUFF_KEYS = ("xp_pct", "coin_pct", "drop_pct")


def _g(st, key):
    if st and key in st:
        return st[key]
    return DEFAULTS[key]


# ---- validation (used by tests and by startup self-check) ----------------------------------------
def validate_effect(eff: dict) -> bool:
    tp = (eff or {}).get("type")
    if tp == "mat":
        return bool(eff.get("tag")) and eff.get("pw", 0) >= 1
    if tp == "relic":
        return eff.get("kind") in ("xp_loc", "xp_pct", "coin_pct", "drop_pct") and eff.get("pct", 0) > 0 \
            and (eff["kind"] != "xp_loc" or bool(eff.get("loc")))
    if tp == "evo":
        return eff.get("stage", 0) >= 1 and bool(eff.get("race"))
    if tp == "cosm":
        return eff.get("slot") in COSM_SLOTS and bool(eff.get("glyph"))
    if tp == "pet":
        return eff.get("role") in ("fang", "heal", "luck") or "role" not in eff
    if tp == "tome":
        return (eff.get("kind") == "kido" and eff.get("branch") in ("had", "bak") and 1 <= eff.get("num", 0) <= 99) or \
               (eff.get("kind") == "buff" and eff.get("key") in BUFF_KEYS and eff.get("pct", 0) > 0)
    return tp in ("hp", "reiatsu", "xp", "kido", "key")


# ---- worn gear (armor, ring, necklace) ---------------------------------------------------------------------
def gear_bonus(ch: dict, items: dict):
    """-> (armor_total, {stat: bonus}, luck) from armor_id / acc_id / charm_id."""
    armor, stats, luck = 0, {}, 0
    for f in ("armor_id", "acc_id", "charm_id"):
        it = items.get(ch.get(f) or "")
        if not it:
            continue
        armor += it["stats"].get("def", 0)
        if "stat" in it["stats"]:
            stats[it["stats"]["stat"]] = stats.get(it["stats"]["stat"], 0) + it["stats"]["bonus"]
        if f != "armor_id":
            luck += it["stats"].get("luck", 0)
    return armor, stats, luck


# ---- relics / cosmetics / buffs -> modifiers ---------------------------------------------------
def relic_slots(level: int, st=None) -> int:
    return (1 if level >= int(_g(st, "relic_slot1_level")) else 0) + (1 if level >= int(_g(st, "relic_slot2_level")) else 0)


def active_buffs(ch: dict, now: int = None) -> dict:
    now = int(now if now is not None else time.time())
    out = {}
    for k, b in (ch.get("buffs") or {}).items():
        if k in BUFF_KEYS and b.get("until", 0) > now:
            out[k] = float(b.get("pct", 0))
    return out


def passive_mods(ch: dict, items: dict, st=None, now: int = None) -> dict:
    """Numeric bonuses from equipped relics, cosmetics and temporary buffs. Percent values."""
    mods = {"xp_pct": 0.0, "coin_pct": 0.0, "drop_pct": 0.0, "fame": 0, "luck": 0.0}
    mult = float(_g(st, "relic_effect_mult"))
    slots = relic_slots(int(ch.get("level", 1)), st)
    for iid in list(ch.get("relics") or [])[:slots]:
        e = (items.get(iid) or {}).get("effect") or {}
        if e.get("type") != "relic":
            continue
        k, pct = e["kind"], float(e["pct"]) * mult
        if k == "xp_loc":
            if e.get("loc") == ch.get("location"):
                mods["xp_pct"] += pct
        else:
            mods[k] += pct
    for slot in COSM_SLOTS:
        iid = (ch.get("cosmetic") or {}).get(slot)
        e = (items.get(iid) or {}).get("effect") or {} if iid else {}
        if e.get("type") != "cosm":
            continue
        mods["fame"] += int(e.get("fame", 0))
        for k, v in (e.get("buff") or {}).items():
            mods[k] = mods.get(k, 0.0) + float(v)
    for k, v in active_buffs(ch, now).items():
        mods[k] += v
    pet = active_pet(ch)
    if pet and pet["role"] == "luck":
        mods["drop_pct"] += float(_g(st, "pet_luck_pct")) * (pet["tier"] + 1)
    return mods


def display_name(ch: dict, items: dict, name: str = None) -> str:
    """Name with the equipped aura/trail/banner glyphs. Plain text (caller escapes)."""
    cs = ch.get("cosmetic") or {}

    def g(slot):
        e = (items.get(cs.get(slot)) or {}).get("effect") or {} if cs.get(slot) else {}
        return e.get("glyph", "")
    return f"{g('aura')}{name or ch.get('name', '?')}{g('banner')}{g('trail')}".strip()


# ---- pets ------------------------------------------------------------------------------------------------
def active_pet(ch: dict):
    p = (ch.get("pets") or [None])[0]
    if not p:
        return None
    return {"sp": p.get("sp", 0), "tier": int(p.get("tier", 0)), "role": p.get("role", "fang")}  # legacy pets are fangs


def pet_combat_mods(ch: dict, st=None) -> dict:
    """{'dmg': extra fraction, 'regen': fraction of max HP per turn}"""
    pet = active_pet(ch)
    if not pet:
        return {"dmg": 0.0, "regen": 0.0}
    n = pet["tier"] + 1
    if pet["role"] == "fang":
        return {"dmg": float(_g(st, "pet_fang_pct")) / 100 * n, "regen": 0.0}
    if pet["role"] == "heal":
        return {"dmg": 0.0, "regen": float(_g(st, "pet_heal_pct")) / 100 * n}
    return {"dmg": 0.0, "regen": 0.0}


# ---- evolution -------------------------------------------------------------------------------------------------
def evo_stage_cap(levels_gates: list, level: int) -> int:
    idx = 0
    for i, gate in enumerate(levels_gates):
        if level >= gate:
            idx = i
    return idx


def evo_can(ch: dict, eff: dict, level_gates: list, max_stage: int, st=None):
    """(ok, reason). Stage n needs: race match, previous stage reached, level gate."""
    cur = ch.get("evo_stage")
    if cur is None:
        return False, "legacy"
    if eff["race"] not in ("*", ch["race"]):
        return False, "race"
    nxt = int(cur) + 1
    if eff["stage"] != nxt:
        return False, "order"
    if nxt > max_stage:
        return False, "max"
    if ch["level"] < level_gates[nxt]:
        return False, "level"
    return True, "ok"


def evo_title_index(ch: dict, level_gates: list, st=None) -> int:
    """Title/form stage. Legacy characters (no evo_stage) and servers with evo_item_required=0 stay level-based."""
    lvl_idx = evo_stage_cap(level_gates, ch["level"])
    if not int(_g(st, "evo_item_required")) or ch.get("evo_stage") is None:
        return lvl_idx
    return min(int(ch["evo_stage"]), lvl_idx)


# ---- text -----------------------------------------------------------------------------------------------------------
def describe(eff: dict, lang: str, names: dict = None) -> str:
    """One simple line shown on the item card. `names` may carry loc/race display names."""
    names = names or {}
    tp = (eff or {}).get("type")
    if tp == "mat":
        return t(lang, "fx_mat", tag=t(lang, "tag_" + eff["tag"]), pw=eff["pw"])
    if tp == "relic":
        if eff["kind"] == "xp_loc":
            return t(lang, "fx_relic_xp_loc", pct=_p(eff["pct"]), loc=names.get("loc", eff.get("loc")))
        return t(lang, "fx_relic_" + eff["kind"], pct=_p(eff["pct"]))
    if tp == "evo":
        race = names.get("race") or t(lang, "fx_any_race")
        return t(lang, "fx_evo", race=race, stage=eff["stage"])
    if tp == "cosm":
        s = t(lang, "fx_cosm", slot=t(lang, "slot_" + eff["slot"]), glyph=eff["glyph"], fame=eff["fame"])
        for k, v in (eff.get("buff") or {}).items():
            s += " · " + t(lang, "fx_buff_" + k, pct=_p(v))
        return s
    if tp == "pet":
        return t(lang, "fx_pet_" + eff.get("role", "fang"), tier=eff["tier"] + 1)
    if tp == "tome":
        if eff["kind"] == "kido":
            return t(lang, "fx_tome_kido", br=t(lang, "br_" + eff["branch"]), num=eff["num"])
        return t(lang, "fx_buff_" + eff["key"], pct=_p(eff["pct"])) + " · " + t(lang, "fx_tome_buff")
    return ""


def _p(x):
    x = float(x)
    return str(int(x)) if x == int(x) else f"{x:.1f}"
