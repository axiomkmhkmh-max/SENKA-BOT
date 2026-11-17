"""Battle Rank: a seasonal skill rank for normal battles only (no dungeons, trials or towers; level, world and race play
no part). Call of Duty style: winning raises it, losing lowers it, the rank shows a title.

Everything is proportional: every gain and loss is a share of the width of the division the player stands in, so the
pace is the same at every rank. Winning in fewer rounds gives more; winning in many rounds gives less. A loss breaks
the win chain and costs more the higher the rank. Fleeing costs a lot of rank but does not break the chain.

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
    """Rank points needed to cross division `div` (they grow slowly, so higher divisions take a little longer)."""
    return 100 + 25 * int(div)


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


# ---- the proportional rules -----------------------------------------------------------------------------------------
WIN_SHARE = 0.22        # a win at the reference pace is worth 22% of the division
ELITE_MULT = 1.3        # an elite (💀) foe is worth more
LOSS_SHARE = 0.10       # a loss costs 10% of the division at the bottom ...
LOSS_STEP = 0.012       # ... +1.2% per division above (about 30% at the top)
FLEE_SHARE = 0.35       # fleeing costs a lot: 35% of the division (but the win chain stays)


def round_factor(turns: int) -> float:
    """Fewer rounds, more rank: 1 round x1.5, 6 rounds x1.0, 11 or more rounds x0.5."""
    return max(0.5, min(1.5, 1.5 - 0.1 * (max(1, int(turns)) - 1)))


def win_gain(rp: int, turns: int, elite: bool = False) -> int:
    k = division(rp)
    return max(1, int(round(width(k) * WIN_SHARE * round_factor(turns) * (ELITE_MULT if elite else 1.0))))


def loss_cost(rp: int) -> int:
    k = division(rp)
    return max(1, int(round(width(k) * (LOSS_SHARE + LOSS_STEP * k))))


def flee_cost(rp: int) -> int:
    return max(1, int(round(width(division(rp)) * FLEE_SHARE)))


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
