"""Item roles (pure, data-driven): material groups, recipes, relic / cosmetic / pet / book effects,
evolution requirements and the single `player_bonus` aggregator used by combat, XP and drops.

Every number that matters is either read from the item's own `effect` field or from GAME_DEFAULTS."""
import time

from data_artifacts import ART_BY_ID as _ART_BY_ID
from data_races import LEVEL_GATES, LOCATIONS, RACES
from data_weapons import RARITIES

LOC_IDS = list(LOCATIONS)

# ---- materials -----------------------------------------------------------------------------
MAT_KINDS = ["reishi", "sekkiseki", "bone", "thread", "fang", "cloth", "mask", "ribbon", "ore", "dust"]
MAT_GROUP = {"reishi": "reishi", "dust": "reishi", "thread": "spirit", "ribbon": "spirit", "cloth": "spirit",
             "sekkiseki": "hard", "bone": "hard", "fang": "hard", "mask": "hard", "ore": "hard"}
GROUPS = ("reishi", "spirit", "hard", "any")

# ---- relics --------------------------------------------------------------------------------------
RELIC_KINDS = ["xp_loc", "drop", "coin", "calm", "stab"]
RELIC_BASE = {"xp_loc": 0.06, "drop": 0.04, "coin": 0.05, "calm": 0.20, "stab": 0.03}


def relic_effect(i: int, tier: int) -> dict:
    kind = RELIC_KINDS[i % 5]
    v = round(RELIC_BASE[kind] * (1 + tier * 0.5), 4)
    return {"type": "relic", "kind": kind, "loc": LOC_IDS[(i // 5) % len(LOC_IDS)] if kind == "xp_loc" else None, "v": v}


# ---- cosmetics ------------------------------------------------------------------------------------------
COSMETIC_SLOTS = ["trail", "aura", "banner", "aura", "trail"]  # by noun order in data_items
COSMETIC_ICONS = {"aura": ["✨", "💠", "🔆", "🌟", "💫", "🔱", "☄️", "🌈"],
                  "trail": ["🌙", "🌸", "🍃", "❄️", "🔥", "⚡", "🌊", "🪷"],
                  "banner": ["🚩", "🏴", "🎌", "⚜️", "🔰", "🛡️", "⚔️", "🏯"]}


def cosmetic_effect(i: int, tier: int) -> dict:
    slot = COSMETIC_SLOTS[(i // 16) % 5]
    return {"type": "cosmetic", "slot": slot, "icon": COSMETIC_ICONS[slot][(i % 16) // 2], "fame": tier + 1}


# ---- pets: species index -> (role, bonus per tier step) -----------------------------------------------------
PET_ROLES = {0: ("luck", 0.015), 1: ("regen", 0.006), 2: ("dmg", 0.010), 3: ("def", 0.010), 4: ("patrol", 0.020), 5: ("crit", 0.004)}

# ---- books -------------------------------------------------------------------------------------------------------
BOOK_BUFFS = ["dmg", "def", "crit", "xp", "drop"]


def book_effect(i: int, tier: int) -> dict:
    m = i % 4
    if m == 0:
        return {"type": "xp", "amount": 150 * (tier + 1) ** 2}
    if m == 1:
        stat = BOOK_BUFFS[(i // 4) % 5]
        return {"type": "buff", "stat": stat, "pct": round((0.02 if stat == "crit" else 0.04) + (0.01 if stat == "crit" else 0.02) * tier, 3),
                "minutes": 30 + 15 * tier}
    if m == 2:
        return {"type": "kido_book", "branch": "had" if (i // 4) % 2 == 0 else "bak", "cap": 8 + tier * 12}
    return {"type": "bond", "amount": 20 * (tier + 1)}


# ---- evolution ----------------------------------------------------------------------------------------------------------
EVO_REQ = {1: (1, 0), 2: (2, 1), 3: (3, 2), 4: (4, 3)}  # stage -> (item count, min rarity index)
EVO_KINDS = ["hogyoku", "vasto", "ginto"]


def evo_gate_stage(race: str, level: int) -> int:
    n = len(RACES[race]["evo"])
    idx = 0
    for i, gate in enumerate(LEVEL_GATES[:n]):
        if level >= gate:
            idx = i
    return idx


def evo_stage(ch: dict) -> int:
    """Stage the player may display/use. Missing `evo` field (old saves) = grandfathered by level."""
    gate = evo_gate_stage(ch["race"], ch["level"])
    ev = ch.get("evo")
    return gate if ev is None else min(gate, int(ev))


def evo_next(ch: dict):
    """(stage, level_gate, need_count, min_rarity_idx) of the next trial, or None."""
    s = evo_stage(ch) + 1
    if s >= len(RACES[ch["race"]]["evo"]) or s not in EVO_REQ:
        return None
    return s, LEVEL_GATES[s], EVO_REQ[s][0], EVO_REQ[s][1]


def race_title_ev(race: str, level: int, evo, lang: str) -> str:
    stage = evo_stage({"race": race, "level": level, "evo": evo})
    return RACES[race]["evo"][stage][0 if lang == "fa" else 1]


# ---- forge value of a material (rarer = worth more units) -----------------------------------------------------------------
def forge_value(rarity: str) -> int:
    return 1 + RARITIES.index(rarity) // 2


# ---- recipes -------------------------------------------------------------------------------------------------------------------
TEMPER_CHANCE = [100, 90, 75, 60, 45]
DUNGEON_IDS = ["trial", "hollow_den", "menos_forest", "noches_depths", "quincy_fort", "palace_trial", "dangai_rift"]
DIFFS = ["normal", "hard", "nightmare", "abyss", "legendary"]


def _fits(it: dict, req: dict) -> bool:
    if it.get("category") != req.get("cat", "material"):
        return False
    if RARITIES.index(it["rarity"]) < req.get("t", 0):
        return False
    g = req.get("g", "any")
    return g == "any" or (it.get("effect") or {}).get("group") == g


def plan_inputs(inputs: list, items: dict, catalog: dict):
    """Pick the cheapest owned items that satisfy every requirement. Returns {item_id: qty} or None."""
    left = {i: q for i, q in items.items() if q > 0 and i in catalog}
    plan = {}
    for req in sorted(inputs, key=lambda r: (-r.get("t", 0), r.get("g", "any") == "any")):
        need = int(req["n"])
        cands = sorted((i for i in left if _fits(catalog[i], req)),
                       key=lambda i: (RARITIES.index(catalog[i]["rarity"]), catalog[i]["base_price"], i))
        for i in cands:
            if need <= 0:
                break
            take = min(left[i], need)
            left[i] -= take
            plan[i] = plan.get(i, 0) + take
            need -= take
        if need > 0:
            return None
    return plan


def _first(catalog: dict, pred):
    return next((i for i, x in catalog.items() if pred(x)), None)


def build_recipes(catalog: dict) -> list:
    """Data-driven recipe table: potions and dungeon keys (armor tempering uses `temper_recipe`)."""
    out = []
    for t in range(4):
        for kind, grp in (("hp", "spirit"), ("reiatsu", "reishi")):
            oid = _first(catalog, lambda x, t=t, kind=kind: x.get("category") == "potion" and (x.get("effect") or {}).get("type") == kind
                         and x["rarity"] == RARITIES[t])
            if oid:
                out.append({"id": f"pot_{kind}_{t}", "type": "potion", "out": oid, "coins": max(10, int(catalog[oid]["base_price"] * 0.5)),
                            "in": [{"g": grp, "n": 2, "t": 0}, {"g": "any", "n": 1 + t, "t": t}]})
    for d_i, d in enumerate(DUNGEON_IDS):
        for idx in range(1, 5):
            diff = DIFFS[idx]
            oid = _first(catalog, lambda x, d=d, diff=diff: (x.get("effect") or {}).get("type") == "key"
                         and x["effect"]["dungeon"] == d and x["effect"]["diff"] == diff)
            if oid:
                out.append({"id": f"key_{d}_{idx}", "type": "key", "out": oid, "dungeon": d, "diff": diff,
                            "coins": 150 * idx * (d_i + 1),
                            "in": [{"g": "hard", "n": 2 * idx, "t": 0}, {"g": "any", "n": idx, "t": idx}]})
    return out


def temper_recipe(plus: int, armor_item: dict) -> dict:
    return {"id": f"temper_{plus + 1}", "type": "temper", "chance": TEMPER_CHANCE[min(plus, len(TEMPER_CHANCE) - 1)],
            "coins": max(20, int(armor_item["base_price"] * 0.15 * (plus + 1))),
            "in": [{"g": "hard", "n": 2 + plus, "t": min(plus, 2)}, {"g": "spirit", "n": 2, "t": 0}]}


def temper_def(base_def: float, plus: int, st: dict) -> float:
    return base_def * (1 + float(st["temper_def_pct"]) * plus)


# ---- the single aggregator ------------------------------------------------------------------------------------------------------------
def active_buffs(ch: dict, now: float = None) -> dict:
    now = now or time.time()
    return {k: v for k, v in (ch.get("buffs") or {}).items() if v.get("until", 0) > now}


def fame(ch: dict, catalog: dict) -> int:
    return sum((catalog.get(i, {}).get("effect") or {}).get("fame", 0) for i in (ch.get("cosmetics") or {}).values() if i)


def cosmetic_tag(ch: dict, catalog: dict) -> str:
    c = ch.get("cosmetics") or {}
    from data_extras import seat_icon
    return "".join((catalog.get(c.get(s) or "", {}).get("effect") or {}).get("icon", "") for s in ("aura", "trail", "banner")) + seat_icon(ch.get("seat", 0))


def tagged_name(ch: dict, catalog: dict) -> str:
    tag = cosmetic_tag(ch, catalog)
    return f"{tag} {ch['name']}" if tag else ch["name"]


def player_bonus(ch: dict, catalog: dict, st: dict, now: float = None) -> dict:
    """Everything equipment-like adds, as plain numbers. Caps keep stacking sane."""
    b = {"dmg": 0.0, "def": 0.0, "crit": 0.0, "regen": 0.0, "xp": 0.0, "drop": 0.0, "coin": 0.0, "patrol": 0.0, "calm": 0.0, "stab": 0.0}
    k_r, k_p = float(st["relic_k"]), float(st["pet_k"])
    stage = evo_stage(ch)
    b["dmg"] += float(st["evo_bonus_pct"]) * stage
    b["def"] += float(st["evo_bonus_pct"]) * stage
    pets = ch.get("pets") or []
    if pets:
        role, per = PET_ROLES.get(pets[0]["sp"] % len(PET_ROLES), ("dmg", 0.01))
        b[{"luck": "drop"}.get(role, role)] += per * (pets[0]["tier"] + 1) * k_p
    for rid in (ch.get("relics") or [])[: int(st["relic_slots"])]:
        e = (catalog.get(rid) or {}).get("effect") or {}
        if e.get("type") != "relic":
            continue
        kind, v = e["kind"], e["v"] * k_r
        if kind == "xp_loc":
            if ch.get("location") == e.get("loc"):
                b["xp"] += v
        else:
            b[kind] += v
    art = (_ART_BY_ID.get(ch.get("artifact") or "") or {}).get("bonus") or {}
    for kind, v in art.items():
        if kind in b:
            b[kind] += v * float(st.get("art_k", 1.0))
    b["xp"] += min(float(st["cosmetic_fame_cap"]), fame(ch, catalog) * float(st["cosmetic_fame_xp"]))
    for key, buf in active_buffs(ch, now).items():
        if key in b:
            b[key] += buf["pct"]
    for k in ("xp", "drop", "coin", "dmg", "def"):
        b[k] = min(b[k], 0.60)
    b["calm"] = min(b["calm"], 1.0)
    return b
