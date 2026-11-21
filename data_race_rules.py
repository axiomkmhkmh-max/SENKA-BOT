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
    "sk": SHINIGAMI_LIKE,   # Shikai (Shinigami) / Hollow Mask (Visored): the early state button (data_abilities)
    "if": ("arrancar",),    # Iron Fist, only while Hierro holds
}


def race_allows(race, action):
    allowed = RACE_ABILITIES.get(action)
    return True if allowed is None else (race in allowed)


# ---- Balance by fight type ----------------------------------------------------------------------------------
# Damage multiplier a race deals in each fight context. Race strength is meant to show up differently in each
# kind of fight (PvP duel, Hollow foe, Boss), while every race ends up with about the same win rate.
# Contexts: "pvp" = duel against a player, "hollow" = wild Hollow foe, "boss" = dungeon / tower boss,
# "pve" = other wild enemies, "world_boss" = shared-HP world boss (each hit counts).
# Fine-tuning by fight type (every value within 0.60-1.40). Race base stats and mods (data_races.py), evolution bonuses
# (data_evolution.py), race techniques and the ability stat of each race (data_race_tech.py) carry the identity; these
# even out what is left. Retuned after abilities started to draw 70% of their power from the race's own stat, with
# balance_sim.py at level ~40, evolution stage 2, and a sensible allocation (40% of the points into the race's ability
# stat; balance_sim.allocation). Retuned again when every form (Shikai/Bankai, Resurrección...) moved behind the full
# spirit gauge. PvP win rates: every race 48-51%. Against wild foes every race wins 77-96% (the strong
# releases make players win far more often there than before the rework).
RACE_CONTEXT_DMG = {  # Nov 21 retune (HP x6, ability families, ratio dodge): balance_sim at levels 20/40/80, PvE ~35 turns for every race
    "shinigami": {"pvp": 1.80, "hollow": 1.362, "boss": 1.362, "pve": 1.362, "world_boss": 1.063},
    "quincy": {"pvp": 0.99, "hollow": 1.171, "boss": 1.157, "pve": 1.172, "world_boss": 0.927},
    "hollow": {"pvp": 1.01, "hollow": 1.852, "boss": 1.852, "pve": 1.852, "world_boss": 1.173},
    "arrancar": {"pvp": 1.115, "hollow": 1.184, "boss": 1.192, "pve": 1.237, "world_boss": 1.073},
    "fullbringer": {"pvp": 0.715, "hollow": 0.761, "boss": 0.761, "pve": 0.761, "world_boss": 0.878},
    "human": {"pvp": 1.145, "hollow": 1.362, "boss": 1.547, "pve": 1.499, "world_boss": 1.026},
    "visored": {"pvp": 1.38, "hollow": 1.115, "boss": 1.115, "pve": 1.115, "world_boss": 0.961},
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
