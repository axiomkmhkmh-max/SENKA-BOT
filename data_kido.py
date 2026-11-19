"""Kidō the way the anime does it: Hadō (destruction, 1-99) and Bakudō (binding, 1-99), cast by name, with an incantation.

Pure data and rules, no database, so the engine, the panel and the tests all read the same numbers.

What the anime shows, and what the fight does with it:
  * You pick the spell you cast (Shō is a quick jab, Shakkahō a fireball, Kurohitsugi the black coffin), not "the best one".
  * The incantation (📿 chant) is the real power of a spell. Low spells are fine without it; from number 60 up an
    unchanted spell is weaker (UNCHANTED_MULT); from number 80 up (Bakudō: 90) it cannot be cast at all, as with Hadō 88 / 90.
  * Each spell does its own thing: Byakurai pierces, Shakkahō burns, Raikōhō stuns; Sai and Hainawa bind, Rikujōkōrō
    holds fast, Sajō Sabaku holds longer, Enkōsen and Danku are walls.
  * High numbers need time to gather: the same spell cannot be cast again at once (spell_cd).
All of it is tuned here; spells that are not in the tables behave as the old plain Hadō / Bakudō did.
"""

CHANT_REQUIRED = {"had": 80, "bak": 90}   # from this number up, a spell cannot be cast without the incantation (Hadō 88 / 90,
                                           # Bakudō 99 Kin; Danku, Bakudō 81, is cast bare in the anime)
UNCHANTED_FROM = 60          # from this number up, an unchanted spell is weaker ...
UNCHANTED_MULT = 0.75        # ... by this factor (Hadō damage, Bakudō shield)
HADO_COST, BAK_COST = 2.5, 2.0   # reiatsu per spell number (as before)

# Hadō: mult = damage factor, pierce = share of the target's armour ignored, burn / weaken = status for 3 turns,
# stun = chance the target loses its next turn, cost_k = reiatsu factor.
HADO = {
    1:  {"mult": 0.9, "cost_k": 0.5},                                  # Shō: a quick palm strike, cheap
    4:  {"pierce": 0.5},                                               # Byakurai: a thin bolt that pierces armour
    11: {"stun": 0.25},                                                # Tsuzuri Raiden: lightning that shocks
    12: {"pierce": 0.35, "mult": 1.05},                                # Fushibi: a thrown spear of light
    31: {"burn": True},                                                # Shakkahō: the red cannon
    32: {"burn": True, "mult": 1.1},                                   # Ōkasen: a wave of flame
    33: {"mult": 1.15},                                                # Sōkatsui: blue fire
    54: {"burn": True, "mult": 1.05},                                  # Haien: a cloud of ash
    57: {"weaken": True, "stun": 0.25},                                # Daichi Tenyō: the earth turns
    58: {"mult": 1.2},                                                 # Tenran: a storm of reiatsu
    63: {"stun": 0.35, "mult": 1.05},                                  # Raikōhō: thunder roar cannon
    73: {"mult": 1.3, "burn": True},                                   # Sōren Sōkatsui: twin blue fire
    78: {"pierce": 0.4, "mult": 1.1},                                  # Zangeki
    88: {"mult": 1.5, "stun": 0.4},                                    # Hiryūgekizoku Shinten Raihō: needs the chant
    90: {"mult": 1.6, "weaken": True},                                 # Kurohitsugi: the black coffin, needs the chant
    91: {"mult": 1.2, "burn": True},                                   # Senju Kōtenkan
    96: {"mult": 1.35, "burn": True},                                  # Ittō Kasō: a pillar of flame
}

# Bakudō: shield = factor on the shield, bind = chance to take the target's next turn (None = the old formula,
# 10% + 5% per number, max 60%), turns = how long, weaken = the target is weakened. Bosses resist binds by half.
BAKUDO = {
    1:  {"bind": 0.55, "shield": 0.6},                                 # Sai: bind the arms
    4:  {"bind": 0.60, "shield": 0.6},                                 # Hainawa: a rope of reiatsu
    8:  {"bind": 0.0, "shield": 1.2},                                  # Seki: repel
    9:  {"bind": 0.5, "weaken": True, "shield": 0.6},                  # Geki: curse that numbs
    30: {"bind": 0.70, "shield": 0.8},                                 # Shitotsu Sansen: three bars of light
    37: {"bind": 0.0, "weaken": True, "shield": 0.7},                  # Tsuribōshi: hang the foe off balance
    39: {"bind": 0.0, "shield": 1.8},                                  # Enkōsen: a round shield
    58: {"bind": 0.0, "weaken": True, "shield": 0.8},                  # Kakushitsuijaku
    61: {"bind": 1.0, "shield": 1.0},                                  # Rikujōkōrō: six rods of light hold fast
    62: {"bind": 0.8, "shield": 1.0},                                  # Hyapporankan: a hundred bars
    63: {"bind": 1.0, "turns": 2, "shield": 1.0},                      # Sajō Sabaku: the chain of the Soul King's net
    73: {"bind": 0.0, "shield": 2.0},                                  # Tozanshō: a mountain wall
    77: {"bind": 0.0, "weaken": True, "shield": 1.0},                  # Tenteikūra
    81: {"bind": 0.0, "shield": 2.5},                                  # Danku: the splitting void wall
}


def hado_params(n: int) -> dict:
    p = {"mult": 1.0, "pierce": 0.0, "burn": False, "weaken": False, "stun": 0.0, "cost_k": 1.0}
    p.update(HADO.get(int(n), {}))
    return p


def bakudo_params(n: int) -> dict:
    p = {"shield": 1.0, "bind": None, "turns": 1, "weaken": False}
    p.update(BAKUDO.get(int(n), {}))
    if p["bind"] is None:
        p["bind"] = min(0.6, 0.10 + 0.05 * int(n))
    return p


def cost(branch: str, n: int) -> int:
    if branch == "had":
        return max(1, int(int(n) * HADO_COST * hado_params(n)["cost_k"]))
    return max(1, int(int(n) * BAK_COST))


def needs_chant(n: int, branch: str = "had") -> bool:
    return int(n) >= CHANT_REQUIRED.get(branch, 80)


def unchanted_mult(n: int) -> float:
    return UNCHANTED_MULT if int(n) >= UNCHANTED_FROM else 1.0


def spell_cd(n: int) -> int:
    """Turns before the same spell can be cast again (counted in the caster's own turns)."""
    n = int(n)
    return 0 if n < 30 else 1 if n < 60 else 2 if n < 80 else 3


def key(branch: str, n: int) -> str:
    return ("h" if branch == "had" else "b") + str(int(n))


def icons(branch: str, n: int) -> str:
    """A short tag for the button: what the spell does besides its plain damage / shield."""
    out = ""
    if branch == "had":
        p = hado_params(n)
        out += ("🎯" if p["pierce"] else "") + ("🔥" if p["burn"] else "") + ("⚡" if p["stun"] else "") + ("🔻" if p["weaken"] else "")
        out += "💥" if p["mult"] >= 1.2 else ""
    else:
        p = bakudo_params(n)
        out += ("🔗" if p["bind"] and (n in BAKUDO or p["bind"] >= 0.3) else "") + ("🔻" if p["weaken"] else "") + ("🧱" if p["shield"] >= 1.5 else "")
    return out + ("📿" if needs_chant(n, branch) else "")
