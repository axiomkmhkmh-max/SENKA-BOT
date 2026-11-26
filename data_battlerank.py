"""Battle Rank: a seasonal skill rank from normal battles and ranked duels only (no dungeons, trials or towers).
Call of Duty style: winning raises it, losing lowers it, the rank shows a title.

Fair on purpose (rework 2): rank points are flat and the same for every level. A level 120 player and a level 10
player get exactly the same points for a normal win, so a strong account can no longer race up the ladder. Normal
battles add at most PVE_DAILY_CAP points a day; above that only duels raise the rank. Ranked duels are where skill
shows: points move like cups (beating a higher-ranked player pays a lot, beating one 300+ points below you pays nothing), with
a cap per opponent per day so two friends cannot farm each other. Divisions are wide: a sub-tier takes days and the
top of the ladder takes most of the 30-day season.

Titles (school-of-mastery licences, so they read as earned skill and stay true after a season reset): Minarai (white),
Shoden (green), Chūden (blue), Okuden (purple), Kaiden (gold), Menkyo Kaiden (red), each with three sub-tiers 1, 2, 3.
The season's number one is Kenpachi. Pure rules, no I/O.
"""
from datetime import datetime, timezone

TIERS = [  # key, (fa, en), colour index (rarity of its rewards)
    ("minarai", ("میناری", "Minarai"), 0),
    ("shoden", ("شودن", "Shoden"), 1),
    ("chuden", ("چودن", "Chūden"), 2),
    ("okuden", ("اوکودن", "Okuden"), 3),
    ("kaiden", ("کایدن", "Kaiden"), 4),
    ("menkyo", ("منکیو کایدن", "Menkyo Kaiden"), 5),
]
TIER_ICON = ["⚪", "🟢", "🔵", "🟣", "🟠", "🔴"]
SUBS = 3
DIVS = len(TIERS) * SUBS            # 18 divisions
KENPACHI = ("کنپاچی", "Kenpachi")


def width(div: int) -> int:
    """Rank points needed to cross division `div`. 300 at the bottom, +60 per division (1,260 for the last step):
    about 13,300 points from zero to the top sub-tier, so the ladder lasts the month."""
    return 300 + 60 * int(div)


THRESHOLDS = [0]
for _k in range(DIVS - 1):
    THRESHOLDS.append(THRESHOLDS[-1] + width(_k))


def division(rp: int) -> int:
    rp = max(0, int(rp))
    k = 0
    for i, t in enumerate(THRESHOLDS):
        if rp >= t:
            k = i
    return k


def progress(rp: int):
    """(division, points into it, its width). The last division keeps counting past its width."""
    k = division(rp)
    return k, int(rp) - THRESHOLDS[k], width(k)


def title(rp: int, lang: str) -> str:
    k = division(rp)
    tier, sub = TIERS[k // SUBS], k % SUBS + 1
    name = tier[1][0 if lang == "fa" else 1]
    num = str(sub).translate(str.maketrans("123", "۱۲۳")) if lang == "fa" else str(sub)
    return f"{TIER_ICON[k // SUBS]} {name} {num}"


def div_title(k: int, lang: str) -> str:
    k = max(0, min(DIVS - 1, int(k)))
    return title(THRESHOLDS[k], lang)


# ---- the flat, level-free rules -------------------------------------------------------------------------------------
PVE_WIN = 20            # a normal win (same for every level and every number of rounds)
PVE_ELITE = 25          # an elite (💀) foe
PVE_DAILY_CAP = 600     # rank points a day from normal battles (about 30 wins); after that only duels raise the rank (was 400)
LOSS_BASE = 10          # a normal loss costs 10 at the bottom ...
LOSS_STEP = 1.5         # ... +1.5 per division above (about 35 at the top)
FLEE_MIN = 40           # fleeing always costs more than losing (the win chain is kept)

DUEL_BASE = 35          # a ranked duel between equals
DUEL_SLOPE = 0.15       # Nov 26 (cup style): +0.15 rank point for every point the LOSER is above the winner
                        # (900 vs 1800 -> +170, capped at DUEL_MAX), so beating a much higher rank pays a lot
DUEL_NO_GAIN_GAP = 300  # a winner this many points (or more) ABOVE the loser gets nothing, and the loser loses nothing;
                        # between 0 and this gap the gain fades out linearly (no cliff)
DUEL_MIN, DUEL_MAX = 0, 150
DUEL_LOSS_SHARE = 0.8   # the loser drops 80% of what the winner gains
DUEL_PAIR_DAILY = 3     # the same two players move each other's rank only in their first 3 duels of the day
DUEL_DAILY_CAP = 500    # rank points a day from duels


def win_gain(rp: int = 0, turns: int = 1, elite: bool = False) -> int:
    """A normal win. `rp` and `turns` are ignored on purpose: rank does not depend on level, power or speed."""
    return PVE_ELITE if elite else PVE_WIN


def loss_cost(rp: int) -> int:
    return int(round(LOSS_BASE + LOSS_STEP * division(rp)))


def flee_cost(rp: int) -> int:
    return max(FLEE_MIN, loss_cost(rp) + 10)


def duel_gain(rp_winner: int, rp_loser: int) -> int:
    """Cup style (Nov 26): the bigger the gap in the winner's favour, the less it pays, down to 0 at DUEL_NO_GAIN_GAP;
    beating someone ranked ABOVE you pays DUEL_SLOPE per point of gap, up to DUEL_MAX."""
    diff = int(rp_loser) - int(rp_winner)           # > 0: the loser was ranked higher (an upset)
    if diff <= -DUEL_NO_GAIN_GAP:
        return 0
    if diff < 0:
        gain = DUEL_BASE * (1.0 + diff / DUEL_NO_GAIN_GAP)
    else:
        gain = DUEL_BASE + diff * DUEL_SLOPE
    return max(DUEL_MIN, min(DUEL_MAX, int(round(gain))))


def duel_loss(rp_winner: int, rp_loser: int) -> int:
    g = duel_gain(rp_winner, rp_loser)
    return 0 if g <= 0 else max(1, int(round(g * DUEL_LOSS_SHARE)))


# ---- seasons -------------------------------------------------------------------------------------------------------------
SEASON_DAYS = 30
EPOCH = int(datetime(2026, 11, 15, tzinfo=timezone.utc).timestamp())
CARRY = 0.4             # at a new season everyone keeps 40% of their rank points


def season_of(ts: float) -> int:
    return max(0, int((int(ts) - EPOCH) // (SEASON_DAYS * 86400)))


def season_end(season: int) -> int:
    return EPOCH + (int(season) + 1) * SEASON_DAYS * 86400


def carried(rp: int) -> int:
    return int(max(0, int(rp)) * CARRY)


# ---- rewards (each once per season) --------------------------------------------------------------------------------------
# sub-tier 1: a chest with a random consumable, 2: a chest with equipment (race armour), 3: a chest of forge and
# evolution materials (blades no longer drop), always in the tier's colour.
REWARD_KIND = ("consumable", "equipment", "materials")
REWARD_NAME = {
    "consumable": ("صندوق مصرفی", "Consumable chest"),
    "equipment": ("صندوق تجهیزات", "Equipment chest"),
    "materials": ("صندوق مواد سلاح", "Weapon materials chest"),
}


def reward_of(div: int):
    """(kind, colour index) of the reward for reaching division `div`."""
    return REWARD_KIND[int(div) % SUBS], int(div) // SUBS


# Kenpachi: the season's number one gets this artifact once and keeps it forever (it is not one of the world artifacts
# and sits on top of any artifact the player holds). Bonus keys as in data_crafting.player_bonus.
KENPACHI_ART = {"name": ("چشم‌بند کنپاچی", "Kenpachi's Eyepatch"),
                "desc": ("چشم‌بندی که ریاتسو را می‌بلعد؛ وقتی برداشته شود، فقط جنگ می‌ماند.",
                         "An eyepatch that devours reiatsu; when it comes off, only the fight remains."),
                "bonus": {"dmg": 0.08, "def": 0.04, "crit": 0.03}}
