"""Distance (فاصله) system: pure logic, no I/O. Shared by PvP, PvE, bosses, raids and hunts.

Zones: 0 contact, 1 near, 2 mid, 3 far, 4 very far. Positions are per fighter pair: `dist` is the gap.
Every fighter carries `reach` = (min, max) for the weapon; attacks may widen it (heavy/release).
"""
import math

ZONE_MIN, ZONE_MAX = 0, 4
START_DIST = 2

ZONE_FA = {0: "تماس", 1: "نزدیک", 2: "متوسط", 3: "دور", 4: "خیلی دور"}
ZONE_EN = {0: "contact", 1: "near", 2: "mid", 3: "far", 4: "very far"}

# default reach per weapon_type (data_weapons.TYPES)
TYPE_REACH = {
    "melee": (0, 1), "elemental": (0, 2), "kido": (1, 4), "illusion": (0, 2), "living": (0, 1),
    "defensive": (0, 1), "ranged": (2, 4), "speed": (0, 1), "hybrid": (0, 2),
}

# movement techniques: (name, zones moved, reiatsu cost share, prep turns after landing)
MOVES = {
    "shunpo": {"zones": 2, "cost": 0.02, "prep": 0, "fa": "شونپو", "en": "Shunpo"},
    "sonido": {"zones": 3, "cost": 0.05, "prep": 0, "fa": "سونیدو", "en": "Sonido"},
    "hiren": {"zones": 2, "cost": 0.0, "prep": 1, "fa": "هیرن‌کیاکو", "en": "Hirenkyaku"},
}
RETREAT = {"zones": 1, "cost": 0.0}  # backing off one zone (costs the turn)

KNOCKBACK = {"hvy": 1, "gt": 2, "unleash": 2}  # zones pushed by attack kind


def reach_for(weapon_type: str, override=None) -> tuple:
    """Weapon reach: explicit override (min, max) wins, else the type default."""
    if override:
        return int(override[0]), int(override[1])
    return TYPE_REACH.get(weapon_type, (0, 1))


def widen(reach: tuple, by: int) -> tuple:
    """Heavy attacks and releases reach further; the minimum stays the same."""
    return reach[0], min(ZONE_MAX, reach[1] + by)


def in_reach(dist: int, reach: tuple) -> bool:
    return reach[0] <= dist <= reach[1]


def get_dist(state: dict) -> int:
    """Current gap. Battles saved before the distance update have no `dist`: they start at START_DIST."""
    return clamp(int(state.get("dist", START_DIST)))


def clamp(d: int) -> int:
    return max(ZONE_MIN, min(ZONE_MAX, d))


def move_cost(f_max_re: int, move: str) -> int:
    return int(f_max_re * MOVES[move]["cost"])


def can_move(f: dict, move: str, dist: int) -> bool:
    """A technique needs a gap to cover and the reiatsu to pay for it."""
    m = MOVES.get(move)
    if not m or dist <= 0:
        return False
    return f["re"] >= f["max_re"] * m["cost"]


def apply_move(state: dict, side: str, move: str) -> dict:
    """Close the gap for `side` (toward the opponent). Returns the event dict."""
    f = state[side]
    m = MOVES[move]
    f["re"] -= move_cost(f["max_re"], move)
    gap = get_dist(state)
    new = clamp(gap - m["zones"])
    gap_before = gap
    state["dist"] = new
    if m["prep"]:  # Hirenkyaku: arrives, but the blade is not ready this turn
        f.setdefault("x", {})["open"] = m["prep"]
    return {"k": "move", "a": f["name"], "tech": m["fa"], "from": gap_before, "to": new}


def apply_retreat(state: dict, side: str) -> dict:
    gap_before = get_dist(state)
    state["dist"] = clamp(gap_before + RETREAT["zones"])
    return {"k": "retreat", "a": state[side]["name"], "from": gap_before, "to": state["dist"]}


def apply_knockback(state: dict, target_side: str, kind: str, dmg: int, max_hp: int) -> int:
    """Pushes the target away. Stronger hits (over 20% of max HP) push one extra zone."""
    base = KNOCKBACK.get(kind, 0)
    if base == 0:
        return 0
    extra = 1 if dmg >= max_hp * 0.20 else 0
    push = base + extra
    state["dist"] = clamp(get_dist(state) + push)
    return push


def approach_turns(dist: int, move: str) -> int:
    """Turns needed to reach contact with one technique (for AI and UI hints)."""
    zones = MOVES[move]["zones"]
    return max(1, math.ceil(dist / zones))


def describe(dist: int, lang: str = "fa") -> str:
    return (ZONE_FA if lang == "fa" else ZONE_EN)[dist]


def new_state_fields(dist: int = START_DIST) -> dict:
    return {"dist": clamp(dist)}


def zone_mult(lo: int, hi: int, dist: int) -> float:
    """Damage multiplier from the spacing itself. Ranged weapons own the far zones and lose the
    contact zones; melee weapons own contact and lose the far zones. Balanced weapons are neutral."""
    if lo >= 2:  # ranged / long reach
        if dist >= 3:
            return 1.15
        if dist <= 1:
            return 0.85
        return 1.0
    if hi <= 1:  # melee
        if dist <= 1:
            return 1.12
        if dist >= 3:
            return 0.85
    return 1.0


# sidestep (گام جانبی): a turn spent stepping off the line. It lasts until your next turn starts,
# so every blow the opponent throws in between is glancing.
SIDESTEP = {"cost": 0.03, "mult": 0.8}
