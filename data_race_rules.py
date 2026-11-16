"""Which races may use which combat abilities. One table, read by engine.can (so buttons and actions agree).

Only player-facing restrictions live here. Wild enemies keep their own behaviour (they are built elsewhere).
Keys are engine action codes; a missing key means every race may use it.
"""

SHINIGAMI_LIKE = ("shinigami", "visored")

RACE_ABILITIES = {
    # Kidō (Hadō / Bakudō): Shinigami and Visored only. Arrancar, Hollow, Quincy, Fullbringer and humans cannot cast.
    "kd": SHINIGAMI_LIKE,
    "bk": SHINIGAMI_LIKE,
    "ch": SHINIGAMI_LIKE,
    # Getsuga Tenshō is a zanpakutō technique.
    "gc": SHINIGAMI_LIKE,
    "gt": SHINIGAMI_LIKE,
    # Spirit-gauge release: Bankai for Shinigami/Visored, Resurrección for Hollow/Arrancar. Nobody else has one.
    "gx": SHINIGAMI_LIKE + ("hollow", "arrancar"),
    # Canon: Quincy Blut (Vene and Arterie) and Arrancar Bala.
    "blv": ("quincy",),
    "bla": ("quincy",),
    "bal": ("arrancar",),
    "neg": ("hollow",),
    "gar": ("hollow", "arrancar"),
}


def race_allows(race, action):
    allowed = RACE_ABILITIES.get(action)
    return True if allowed is None else (race in allowed)


# ---- Balance by fight type ----------------------------------------------------------------------------------
# Damage multiplier a race deals in each fight context. Race strength is meant to show up differently in each
# kind of fight (PvP duel, Hollow foe, Boss), while every race ends up with about the same win rate.
# Contexts: "pvp" = duel against a player, "hollow" = wild Hollow foe, "boss" = dungeon / tower boss,
# "pve" = other wild enemies, "world_boss" = shared-HP world boss (each hit counts). Tuned with the duel and fight simulator at level ~40 (equal allocated points, same weapon and armour).
RACE_CONTEXT_DMG = {
    "shinigami": {"pvp": 1.301, "hollow": 1.379, "boss": 1.311, "pve": 1.307, "world_boss": 1.001},
    "quincy": {"pvp": 1.152, "hollow": 1.208, "boss": 1.147, "pve": 1.170, "world_boss": 1.008},
    "hollow": {"pvp": 0.813, "hollow": 0.806, "boss": 0.772, "pve": 0.777, "world_boss": 1.031},
    "arrancar": {"pvp": 0.808, "hollow": 0.792, "boss": 0.758, "pve": 0.814, "world_boss": 0.989},
    "fullbringer": {"pvp": 1.122, "hollow": 1.207, "boss": 1.121, "pve": 1.152, "world_boss": 0.985},
    "human": {"pvp": 1.144, "hollow": 1.120, "boss": 1.112, "pve": 1.174, "world_boss": 1.005},
    "visored": {"pvp": 1.133, "hollow": 1.120, "boss": 1.072, "pve": 1.090, "world_boss": 0.983},
}


FIGHT_CONTEXTS = ("hollow", "boss", "pve", "world_boss")


def fight_context(state: dict, dfn: dict):
    """Which fight type this hit belongs to: 'pvp', 'hollow', 'boss', 'pve' (wild), 'world_boss', or None."""
    if state.get("pvp"):
        return "pvp"
    foe = dfn.get("foe")
    return foe if foe in FIGHT_CONTEXTS else None


def ctx_dmg_mult(att_race, context) -> float:
    """Fight-type damage multiplier for an attacker race (1.0 when there is no context or no entry)."""
    if context is None:
        return 1.0
    return float(RACE_CONTEXT_DMG.get(att_race, {}).get(context, 1.0))


# ---- General skills: one shared list any race can equip (profile switch). Race is a bonus, not a gate. ----------
# cost = share of max Reiatsu, cd = turns before reuse. `fav` races get the bonus strength (GEN_FAV_MULT).
GENERAL_SKILLS = {
    "guard": {"cost": 0.08, "cd": 3, "shield": 0.12, "fav": ("quincy", "hollow", "human")},
    "strike": {"cost": 0.10, "cd": 3, "mult": 1.15, "fav": ("shinigami", "fullbringer", "arrancar")},
    "focus": {"cost": 0.08, "cd": 4, "buff": 1.20, "turns": 2, "fav": ("visored", "human", "fullbringer")},
}
GEN_ORDER = (None, "guard", "strike", "focus")  # the profile switch cycles through these
GEN_FAV_MULT = 1.25


def gen_power(race: str, key: str) -> float:
    """Strength factor of a general skill for this race (1.25 when the race is one of its favourites)."""
    spec = GENERAL_SKILLS.get(key) or {}
    return GEN_FAV_MULT if race in spec.get("fav", ()) else 1.0
