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
# "pve" = other wild enemies, "world_boss" = shared-HP world boss (each hit counts).
# These are only residual fine-tuning (every value within 0.92-1.08). The real balance lives in the race base stats and mods
# (data_races.py). Tuned with balance_sim.py at level ~40 (equal allocated points, same weapon and armour) for the standard loadout:
# Strike for everyone; Zangetsu's technique and Hadō 1 and 4 for Shinigami and Visored. Win rates: every race 45-54% in every fight type.
RACE_CONTEXT_DMG = {
    "shinigami": {"pvp": 0.920, "hollow": 1.080, "boss": 0.961, "pve": 0.921, "world_boss": 1.007},
    "quincy": {"pvp": 0.931, "hollow": 1.047, "boss": 0.972, "pve": 0.931, "world_boss": 0.922},
    "hollow": {"pvp": 0.974, "hollow": 1.051, "boss": 0.966, "pve": 0.928, "world_boss": 1.076},
    "arrancar": {"pvp": 0.981, "hollow": 1.035, "boss": 0.979, "pve": 0.954, "world_boss": 1.071},
    "fullbringer": {"pvp": 0.961, "hollow": 1.065, "boss": 0.973, "pve": 0.939, "world_boss": 0.977},
    "human": {"pvp": 0.965, "hollow": 0.959, "boss": 1.004, "pve": 0.953, "world_boss": 0.928},
    "visored": {"pvp": 0.947, "hollow": 1.080, "boss": 1.021, "pve": 0.946, "world_boss": 0.958},
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
