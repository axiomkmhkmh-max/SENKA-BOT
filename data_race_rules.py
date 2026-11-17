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
    # Spirit-gauge release ("gx"): every race has one now (Bankai, Resurrección, Vollständig, Complete Fullbring,
    # full soul awakening; names in data_bleachfx.RELEASE_NAME), so it is not listed here.
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
# Residual fine-tuning (every value within 0.80-1.20). The race base stats and mods (data_races.py), the evolution bonuses
# (data_evolution.py) and the race techniques (data_race_tech.py) carry the identity; these even out what is left.
# Retuned after the rework (releases for every race, canon evolution bonuses, race techniques) with balance_sim.py at
# level ~40, evolution stage 2 (equal allocated points, same weapon and armour), standard loadout: Strike for everyone;
# Zangetsu's technique and Hadō 1 and 4 for Shinigami and Visored. PvP win rates: every race 49-53%; against wild foes
# every race within about 5 points of the average (players now win far more often there, because of the stronger releases).
RACE_CONTEXT_DMG = {
    "shinigami": {"pvp": 1.023, "hollow": 1.2, "boss": 1.129, "pve": 1.073, "world_boss": 1.012},
    "quincy": {"pvp": 0.807, "hollow": 0.8, "boss": 0.801, "pve": 0.8, "world_boss": 0.883},
    "hollow": {"pvp": 0.913, "hollow": 0.914, "boss": 0.879, "pve": 0.851, "world_boss": 1.019},
    "arrancar": {"pvp": 1.066, "hollow": 1.104, "boss": 1.065, "pve": 1.07, "world_boss": 1.037},
    "fullbringer": {"pvp": 0.939, "hollow": 0.91, "boss": 0.928, "pve": 0.919, "world_boss": 1.005},
    "human": {"pvp": 0.906, "hollow": 0.825, "boss": 0.904, "pve": 0.874, "world_boss": 0.978},
    "visored": {"pvp": 1.115, "hollow": 1.2, "boss": 1.166, "pve": 1.2, "world_boss": 1.052},
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
