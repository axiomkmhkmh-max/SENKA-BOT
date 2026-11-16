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
    "shinigami": {"pvp": 1.318, "hollow": 1.390, "boss": 1.290, "pve": 1.328, "world_boss": 1.004},
    "quincy": {"pvp": 1.171, "hollow": 1.218, "boss": 1.154, "pve": 1.128, "world_boss": 1.003},
    "hollow": {"pvp": 0.835, "hollow": 0.801, "boss": 0.782, "pve": 0.812, "world_boss": 1.020},
    "arrancar": {"pvp": 0.813, "hollow": 0.803, "boss": 0.767, "pve": 0.834, "world_boss": 0.978},
    "fullbringer": {"pvp": 1.132, "hollow": 1.221, "boss": 1.139, "pve": 1.131, "world_boss": 0.996},
    "human": {"pvp": 1.048, "hollow": 1.059, "boss": 1.046, "pve": 1.089, "world_boss": 1.008},
    "visored": {"pvp": 1.130, "hollow": 1.134, "boss": 1.098, "pve": 1.119, "world_boss": 0.993},
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
