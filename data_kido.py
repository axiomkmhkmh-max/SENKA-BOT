"""Kidō the way the anime does it: Hadō (destruction, 1-99) and Bakudō (binding, 1-99), cast by name, with an incantation.

Pure data and rules, no database, so the engine, the panel and the tests all read the same numbers.

What the anime shows, and what the fight does with it:
  * You pick the spell you cast (Shō is a quick jab, Shakkahō a fireball, Kurohitsugi the black coffin), not "the best one".
  * The incantation (📿 chant) is the real power of a spell. Low spells are fine without it; from number 60 up an
    unchanted spell is weaker (UNCHANTED_MULT). Nov 25: every spell 1-99 can be cast bare or after a chant.
  * Each spell does its own thing: Byakurai pierces, Shakkahō burns, Raikōhō stuns; Sai and Hainawa bind, Rikujōkōrō
    holds fast, Sajō Sabaku holds longer, Enkōsen and Danku are walls.
  * No cooldown: any spell can be cast again right away (spell_cd is always 0; the only limit is reiatsu).
  * No level gate in the fight: every spell the fighter knows (Hadō and Bakudō alike) is castable at any level.
  * Reiatsu cost is a share of the caster's MAX reiatsu (HADO_COST_PCT / BAK_COST_PCT per spell number), so the
    same spell costs the same fraction of the pool at every level and the best known spell does not drop out as the pool shrinks.
All of it is tuned here; spells that are not in the tables behave as the old plain Hadō / Bakudō did.
"""

CHANT_REQUIRED = {"had": 100, "bak": 100}  # Nov 25: no spell NEEDS the incantation any more (was 91). Every spell 1-99 can be cast bare
                                            # (weaker from UNCHANTED_FROM up) or after a chant (full power), so a 99 card is never dead weight
UNCHANTED_FROM = 60          # from this number up, an unchanted spell is weaker ...
UNCHANTED_MULT = 0.85        # ... by this factor (Hadō damage, Bakudō shield). Nov 26: 0.75 -> 0.85, a chant is a bonus, not a tax
HADO_COST_PCT, BAK_COST_PCT = 0.0025, 0.002   # share of max reiatsu per spell number (Hadō 89 = 22.2%, Bakudō 89 = 17.8%)
# Nov 26: four clear cost tiers (the same for Hadō and Bakudō), so the cheap spell and the big spell are a real choice
COST_TIERS = ((91, 0.08), (70, 0.05), (40, 0.035), (0, 0.02))   # (from number, share of max reiatsu)
NORMAL_SPELL_PCT = 0.02
HIGH_SPELL_FROM = 91
HIGH_SPELL_PCT = 0.08

# Hadō: mult = damage factor, pierce = share of the target's armour ignored, burn / weaken = status for 3 turns,
# stun = chance the target loses its next turn, cost_k = reiatsu factor.
# Hadō damage factor by spell number. It used to be 0.7 + 0.3 * n (Kurohitsugi x27.7): a high-level caster hit for 200K while every
# other attack (a plain blow, Hollow Claw, Mask Strike) hit for about 1K, so nothing else was worth pressing. Now the first
# HADO_KNEE numbers keep the old slope and the numbers above it grow at HADO_SLOPE_HIGH per number (Kurohitsugi about x10).
HADO_KNEE = 20
HADO_TOP_FROM = 90  # spells above this number are the top tier (see hado_params)
HADO_SLOPE_HIGH = 0.05


def hado_factor(n: int) -> float:
    """Nov 26: one smooth curve (was a steep 0.3/number up to 20, then a kink). Shō ~1.4, Shakkahō ~4.5, Raikōhō ~6.3,
    Kurohitsugi ~7.6, 99 ~8.0: low spells stay close to before, the 30-90 range is about a quarter lower, the top keeps its
    own multiplier on top (hado_params), so the ladder 'higher number = stronger' still holds without 20x gaps."""
    n = max(1, min(99, int(n)))
    return 1.0 + 7.0 * (n / 99) ** 0.6


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
    88: {"mult": 1.5, "stun": 0.4},                                    # Hiryūgekizoku Shinten Raihō: bare = weaker
    90: {"mult": 1.6, "weaken": True},                                 # Kurohitsugi: the black coffin, bare = weaker
    91: {"mult": 1.7, "burn": True},                                   # Senju Kōtenkan
    96: {"mult": 1.85, "burn": True},                                  # Ittō Kasō: a pillar of flame
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


def card_min_level(n: int) -> int:
    """Level a player needs to learn spell n from a card. Up to 59 it is the old 80% of the number; an Epic card (60-79)
    needs level 100-195 and a Legendary card (80-99) level 205-300, so nobody gets the top spells early."""
    n = int(n)
    base = -(-n * 8 // 10)  # ceil(n * 0.8)
    if n >= 80:
        return max(base, 205 + (n - 80) * 5)
    if n >= 60:
        return max(base, 100 + (n - 60) * 5)
    return base


def hado_params(n: int) -> dict:
    p = {"mult": 1.0, "pierce": 0.0, "burn": False, "weaken": False, "stun": 0.0, "cost_k": 1.0}
    if int(n) > HADO_TOP_FROM:  # 91-99 always out-hit Kurohitsugi (90, x1.6): x1.7 at 91 up to x1.94 at 99, unless the spell has its own entry
        p["mult"] = 1.7 + 0.03 * (int(n) - HADO_TOP_FROM - 1)
    p.update(HADO.get(int(n), {}))
    return p


def bakudo_params(n: int) -> dict:
    p = {"shield": 1.0, "bind": None, "turns": 1, "weaken": False}
    p.update(BAKUDO.get(int(n), {}))
    if p["bind"] is None:
        p["bind"] = min(0.6, 0.10 + 0.05 * int(n))
    return p


def cost_share(n: int) -> float:
    for start, share in COST_TIERS:
        if int(n) >= start:
            return share
    return NORMAL_SPELL_PCT


def cost(branch: str, n: int, max_re: int) -> int:
    """Reiatsu a spell costs: a share of the caster's max reiatsu, so it scales with the pool."""
    return max(1, int(int(max_re) * cost_share(n)))


def cost_pct(branch: str, n: int) -> float:
    """The same cost as a percentage of max reiatsu (for texts)."""
    return round(cost_share(n) * 100, 1)


def needs_chant(n: int, branch: str = "had") -> bool:
    return int(n) >= CHANT_REQUIRED.get(branch, 91)


def unchanted_mult(n: int) -> float:
    return UNCHANTED_MULT if int(n) >= UNCHANTED_FROM else 1.0


def spell_cd(n: int) -> int:
    """Turns before the same spell can be cast again (counted in the caster's own turns)."""
    return 0   # cooldowns removed: only reiatsu limits how often a spell is cast


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


# ---- quick picks (Nov 26) ----------------------------------------------------------------------------------------------
# The spell menu used to be 99 numbers in pages. Now the fighter sees a handful of ROLES and the best spell they own for each
# (highest number that does the job). Pure functions over the castable list the engine already builds (engine.kido_list).
ROLES_HAD = (("best", "💥", "قوی‌ترین", "Strongest"), ("burn", "🔥", "سوزاننده", "Burn"), ("stun", "⚡", "شوک", "Stun"),
             ("pierce", "🎯", "سوراخ‌کن زره", "Armour pierce"), ("weaken", "🔻", "تضعیف", "Weaken"), ("cheap", "🪶", "ارزان", "Cheap"))
ROLES_BAK = (("bind", "🔗", "بند", "Bind"), ("shield", "🧱", "سپر", "Barrier"), ("weaken", "🔻", "تضعیف", "Weaken"),
             ("cheap", "🪶", "ارزان", "Cheap"))


def roles(branch: str) -> tuple:
    return ROLES_HAD if branch == "had" else ROLES_BAK


def _has_role(branch: str, role: str, n: int) -> bool:
    if branch == "had":
        p = hado_params(n)
        return {"burn": p["burn"], "stun": p["stun"] > 0, "pierce": p["pierce"] > 0, "weaken": p["weaken"]}.get(role, False)
    p = bakudo_params(n)
    return {"bind": p["bind"] >= 0.5, "shield": p["shield"] >= 1.5, "weaken": p["weaken"]}.get(role, False)


def quick_picks(branch: str, castable) -> list:
    """[(role, icon, fa, en, number)] for every role the fighter can fill right now, without repeating a number twice in a row
    of the list (a spell that is the best for two roles is shown once, under its first role)."""
    nums = sorted({int(n) for n in castable}, reverse=True)
    out, used = [], set()
    for role, icon, fa, en in roles(branch):
        if role == "best":
            pick = nums[0] if nums else None
        elif role == "cheap":
            pick = nums[-1] if nums else None
        else:
            pick = next((n for n in nums if _has_role(branch, role, n)), None)
        if pick is None or pick in used:
            continue
        used.add(pick)
        out.append((role, icon, fa, en, pick))
    return out
