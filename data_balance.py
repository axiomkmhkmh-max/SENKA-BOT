"""Nov 26 rebalance: damage by level and stats, HP up, regen down, Hadō rhythm.

Pure data and pure functions (no I/O). Everything tunable lives here so one file changes the feel of the game.

Why this exists (player feedback):
  * Every duel blow was cut to the same flat share of HP, so a stronger fighter hit exactly as hard as a weaker one,
    while healing (natural regen + pet + Kyōka + guard) put back more per turn than the blows took off.
    -> the duel hit cap now follows the attacker's power against the defender's (level + stats), players get more HP,
       and passive regen is capped per turn so nobody out-heals a fair fight.
  * Hadō: one 150K blow and then nothing but waiting is no fun for a caster, and spamming 99 / 98 / 97 in a row is no fun
    for the opponent. -> big spells share one cooldown group, small spells are cheap fillers that come back fast.
"""

# ---- players get more HP (wild enemies and bosses keep their numbers) ----------------------------------------------
PLAYER_HP_K = 1.35   # x on a player's max HP. Heals / shields / DoT are measured on the OLD pool (engine._hb divides by it)

# ---- passive regen budget ----------------------------------------------------------------------------------------
# Natural recovery + companion (pet / Hōgyoku / Soul King) regen together never heal more than this share of MAX HP per
# own turn. Before: 3% of the old pool + the pet's share + Kyōka's 10% = often 10%+ a turn, more than a fair blow.
PASSIVE_REGEN_CAP = 0.030        # outside duels (hunts, dungeons, bosses)
PASSIVE_REGEN_CAP_DUEL = 0.018   # players against players
KYOKA_HEAL_SHARE = 0.05          # Kyōka Suigetsu's Shikai heal per turn (was 10% of max HP)

# ---- duel hit cap follows power ----------------------------------------------------------------------------------
# cap share = DUEL["hit_cap"] x scale, scale = (attacker rating / defender rating) ** CAP_EXP, clamped.
# Equal fighters keep exactly the old cap; a much stronger attacker hits up to CAP_MAX x harder (never a one-shot: the cap
# is still a share of the smaller HP pool), a much weaker one is held down to CAP_MIN x.
CAP_EXP = 0.75
CAP_MIN, CAP_MAX = 0.60, 1.40
LEVEL_W, STAT_W = 1.0, 1.0       # rating = LEVEL_W * level + STAT_W * mean(zanjutsu, kido, hakuda, hoho, reiatsu)
RATING_STATS = ("zanjutsu", "kido", "hakuda", "hoho", "reiatsu")


def rating(level, stats: dict) -> float:
    """One number for 'how strong is this fighter': level plus the average of the five stats (all effective values)."""
    vals = [float(stats.get(k, 0) or 0) for k in RATING_STATS]
    return max(1.0, LEVEL_W * float(level or 1) + STAT_W * (sum(vals) / len(vals)))


def cap_scale(att_rating: float, dfn_rating: float) -> float:
    """Multiplier on the duel hit cap for this attacker against this defender."""
    r = max(1.0, float(att_rating)) / max(1.0, float(dfn_rating))
    return max(CAP_MIN, min(CAP_MAX, r ** CAP_EXP))


def passive_regen_cap(duel: bool) -> float:
    return PASSIVE_REGEN_CAP_DUEL if duel else PASSIVE_REGEN_CAP


# ---- Hadō rhythm ---------------------------------------------------------------------------------------------------
# A "big" spell (number >= BIG_FROM) starts a shared cooldown for every OTHER big Hadō, so rotating 99 -> 98 -> 97 does not
# become a spam loop. Small spells (< SMALL_TO) are fillers: short cooldown, always there, so a caster never just waits.
BIG_FROM = 70
BIG_GROUP_CD = 3      # own turns before ANY other big Hadō can be cast after one was cast
SMALL_TO = 40
SMALL_CD = 2          # a filler spell comes back after this many own turns (the old tier value was 3)


def hado_group_cd(n: int) -> int:
    """Own turns the shared big-spell lock lasts after casting spell n (0 = this spell does not start the lock)."""
    return BIG_GROUP_CD if int(n) >= BIG_FROM else 0


def hado_small_cd(n: int):
    """Cooldown override for filler spells, or None to keep the tier value."""
    return SMALL_CD if int(n) < SMALL_TO else None
