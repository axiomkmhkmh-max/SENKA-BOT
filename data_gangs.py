"""Xcution (Lost Substitute arc) and Bount (mansion) rules. Pure data and maths, no I/O.

Decisions (design values, documented in DESIGN_XCUTION.md and DESIGN_BOUNT.md):
  * Xcution: Fullbringers only, joined at the hideout. Wins there give siphon points (daily cap).
    Points raise the rank; each rank adds 2% damage. Leaving is free; rejoining waits 24 hours.
  * Bount: soul absorption after a win in the mansion, for every race, coins scaled by enemy level (daily cap).
"""

XCUTION_LOC = "xcution_hideout"
XCUTION_RACE = "fullbringer"
XCUTION_RANK_POINTS = [0, 40, 120, 300, 700]          # points needed for rank 0..4
XCUTION_RANK_NAMES = [("قلاب‌آزاد", "Free Hand"), ("عضو", "Member"), ("شکارچی", "Hunter"),
                      ("سایه‌ی Xcution", "Xcution Shade"), ("رهبر خاموش", "Silent Leader")]
XCUTION_RANK_DMG = 0.02                               # damage bonus per rank
SIPHON_DAILY_CAP = 60
XCUTION_REJOIN_SECONDS = 24 * 3600

BOUNT_LOC = "bount_mansion"
ABSORB_DAILY_CAP = 500


# Weekly Xcution boss: every win at the hideout is one tally. Reaching the target defeats the boss
# and every member gets the reward (siphon points). The boss resets each week.
XCUTION_BOSS_TARGET = 30
XCUTION_BOSS_REWARD = 80


def boss_week_key(day_id: str) -> str:
    """Key of the week that a YYYY-MM-DD day belongs to (weeks start on Monday)."""
    from datetime import date
    d = date.fromisoformat(day_id)
    monday = d.toordinal() - d.weekday()
    return f"w{monday}"


def boss_defeated(wins: int) -> bool:
    return int(wins or 0) >= XCUTION_BOSS_TARGET


def xcution_rank(points: int) -> int:
    """Rank index for a siphon total (0 = Free Hand)."""
    rank = 0
    for i, need in enumerate(XCUTION_RANK_POINTS):
        if int(points or 0) >= need:
            rank = i
    return rank


def xcution_rank_name(points: int, lang: str) -> str:
    fa, en = XCUTION_RANK_NAMES[xcution_rank(points)]
    return fa if lang == "fa" else en


def xcution_dmg_mult(ch: dict) -> float:
    """Damage multiplier from Xcution rank. 1.0 for anyone who is not a member."""
    x = (ch or {}).get("xcution") or {}
    if not x.get("joined"):
        return 1.0
    return 1.0 + XCUTION_RANK_DMG * xcution_rank(x.get("points", 0))


def can_join_xcution(ch: dict, location: str, now: int) -> bool:
    x = (ch or {}).get("xcution") or {}
    if (ch or {}).get("race") != XCUTION_RACE or location != XCUTION_LOC:
        return False
    if x.get("joined"):
        return False
    return now - int(x.get("left_at", 0) or 0) >= XCUTION_REJOIN_SECONDS


def siphon_gain(enemy_level: int, elite: bool, already_today: int) -> int:
    """Siphon points from one won battle at the hideout, never past the daily cap."""
    base = 3 + int(enemy_level) // 5
    if elite:
        base *= 2
    room = max(0, SIPHON_DAILY_CAP - int(already_today or 0))
    return min(base, room)


def absorb_coins(enemy_level: int, already_today: int) -> int:
    """Coins from one won battle in the mansion (soul absorption), never past the daily cap."""
    base = 10 + int(enemy_level) * 2
    room = max(0, ABSORB_DAILY_CAP - int(already_today or 0))
    return min(base, room)
