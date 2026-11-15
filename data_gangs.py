"""Xcution (Lost Substitute arc) and Bount (mansion). Pure data and maths, no I/O.

Xcution (canon: Kugo Ginjō's gang of Fullbringers who siphon power from others):
  * Fullbringers join at the hideout. Wins there siphon points (daily cap), points raise a rank (+2% damage each).
  * Siphon Surge: every siphon win opens a short surge that adds damage.
  * Weekly boss, Kugo Ginjō: every member win at the hideout is one tally. Phases open at 10 and 20 tallies, and the
    group gets a damage bonus per phase. Reaching 30 defeats him, pays every member, and pays the top contributor.

Bount (filler arc, optional design, see DESIGN_BOUNT.md):
  * Soul stacks: each win in the mansion adds one stack (max 5). Stacks also raise the mansion's soul-absorption coins.
  * Bount Seal: spends stacks in a fight to hold the foe, who loses its next turn (cooldown, reiatsu cost).

Documented in DESIGN_XCUTION.md and DESIGN_BOUNT.md. Balance numbers are design values, not canon.
"""
import time
from datetime import date, datetime, timedelta, timezone

XCUTION_LOC = "xcution_hideout"
XCUTION_RACE = "fullbringer"
XCUTION_RANK_POINTS = [0, 40, 120, 300, 700]          # points needed for rank 0..4
XCUTION_RANK_NAMES = [("قلاب‌آزاد", "Free Hand"), ("عضو", "Member"), ("شکارچی", "Hunter"),
                      ("سایه‌ی Xcution", "Xcution Shade"), ("رهبر خاموش", "Silent Leader")]
XCUTION_RANK_DMG = 0.02                               # damage bonus per rank
SIPHON_DAILY_CAP = 60
XCUTION_REJOIN_SECONDS = 24 * 3600

SURGE_SECONDS = 30 * 60                               # a siphon win opens a surge for this long
SURGE_DMG = 0.06

BOSS_NAME = ("کوگو جینجو", "Kugo Ginjō")
XCUTION_BOSS_PHASES = [10, 20, 30]                    # tallies that open phase 1, 2 and 3 (3 defeats the boss)
XCUTION_BOSS_TARGET = XCUTION_BOSS_PHASES[-1]
XCUTION_BOSS_DMG = [0.0, 0.03, 0.06, 0.10]            # member damage bonus: before phase 1, phase 1, phase 2, defeated
XCUTION_BOSS_REWARD = 80                              # siphon points for every member when defeated
XCUTION_BOSS_TOP_BONUS = 40                           # extra points for the top contributor

BOUNT_LOC = "bount_mansion"
ABSORB_DAILY_CAP = 500
BOUNT_STACK_MAX = 5
BOUNT_STACK_COIN = 0.10                               # absorption coins +10% per stack held
BOUNT_SEAL = {"stacks": 3, "re": 0.20, "cd": 3}       # cost in stacks and reiatsu share, cooldown in turns


def boss_week_key(day_id: str) -> str:
    """Key of the week that a YYYY-MM-DD day belongs to (weeks start on Monday)."""
    d = date.fromisoformat(day_id)
    monday = d.toordinal() - d.weekday()
    return f"w{monday}"


def week_end_epoch(day_id: str) -> int:
    """Unix time when the boss week of this day ends (next Monday 00:00 UTC)."""
    d = date.fromisoformat(day_id)
    monday = d - timedelta(days=d.weekday())
    end = datetime(monday.year, monday.month, monday.day, tzinfo=timezone.utc) + timedelta(days=7)
    return int(end.timestamp())


def boss_phase(wins: int) -> int:
    """Phase reached for a tally count: 0 before phase 1, 3 when defeated."""
    return sum(1 for need in XCUTION_BOSS_PHASES if int(wins or 0) >= need)


def boss_defeated(wins: int) -> bool:
    return int(wins or 0) >= XCUTION_BOSS_TARGET


def boss_dmg(wins: int) -> float:
    return XCUTION_BOSS_DMG[boss_phase(wins)]


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


def xcution_dmg_mult(ch: dict, now: int = None) -> float:
    """Damage multiplier for a fighter. 1.0 for anyone who is not a member.

    Rank, Siphon Surge and the boss phase bonus multiply together. Surge and boss bonus only count while active.
    """
    x = (ch or {}).get("xcution") or {}
    if not x.get("joined"):
        return 1.0
    now = int(time.time()) if now is None else now
    m = 1.0 + XCUTION_RANK_DMG * xcution_rank(x.get("points", 0))
    if int(x.get("surge_until", 0) or 0) > now:
        m *= 1.0 + SURGE_DMG
    if int(x.get("boss_until", 0) or 0) > now:
        m *= 1.0 + float(x.get("boss_dmg", 0) or 0)
    return m


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


def absorb_coins(enemy_level: int, already_today: int, stacks: int = 0) -> int:
    """Coins from one won battle in the mansion, scaled by soul stacks, never past the daily cap."""
    base = 10 + int(enemy_level) * 2
    base = int(base * (1 + BOUNT_STACK_COIN * max(0, min(BOUNT_STACK_MAX, int(stacks or 0)))))
    room = max(0, ABSORB_DAILY_CAP - int(already_today or 0))
    return min(base, room)


def bount_stacks_after(remaining: int, gained: bool) -> int:
    """Soul stacks after a battle: what the seal left unspent, plus one for a mansion win."""
    return max(0, min(BOUNT_STACK_MAX, int(remaining or 0) + (1 if gained else 0)))


def _t(lang: str, fa: str, en: str) -> str:
    return fa if lang == "fa" else en


def gang_result_lines(o: dict, lang: str) -> list:
    """Player-facing lines for a won battle's Xcution / Bount outcome. Empty when nothing applies."""
    lines = []
    g = o.get("gang") or {}
    if g.get("absorbed"):
        n = g["absorbed"]
        lines.append(_t(lang, f"🕳️ جذب روح: +{n} سکه", f"🕳️ Soul absorption: +{n} coins"))
    if g.get("siphon"):
        n = g["siphon"]
        lines.append(_t(lang, f"🌀 دزدی ریاتسو: +{n} امتیاز", f"🌀 Siphon: +{n} points"))
    if g.get("rank_up"):
        nm = xcution_rank_name(g.get("points", 0), lang)
        lines.append(_t(lang, f"⬆️ رتبه‌ی Xcution بالا رفت: <b>{nm}</b>", f"⬆️ Xcution rank up: <b>{nm}</b>"))
    if g.get("surge"):
        pct = round(SURGE_DMG * 100)
        mins = SURGE_SECONDS // 60
        lines.append(_t(lang, f"⚡ موج Xcution: +{pct}% آسیب تا {mins} دقیقه", f"⚡ Xcution surge: +{pct}% damage for {mins} min"))
    b = g.get("boss")
    if b:
        bn_fa, bn_en = BOSS_NAME
        if b.get("paid_now"):
            lines.append(_t(lang, f"👹 <b>{bn_fa}</b> شکست خورد! پاداش به همه‌ی اعضا رسید.",
                            f"👹 <b>{bn_en}</b> is defeated! Every member is rewarded."))
            if b.get("you_top"):
                lines.append(_t(lang, f"🥇 بیشترین مشارکت را داشتی: +{XCUTION_BOSS_TOP_BONUS} امتیاز",
                                f"🥇 You were the top contributor: +{XCUTION_BOSS_TOP_BONUS} points"))
        else:
            if b.get("phase_up"):
                lines.append(_t(lang, f"👹 {bn_fa} وارد فاز {b['phase']} شد؛ آسیب اعضا بیشتر شد.",
                                f"👹 {bn_en} enters phase {b['phase']}; member damage is up."))
            lines.append(_t(lang, f"👹 باس هفتگی: {b['wins']}/{b['target']}", f"👹 Weekly boss: {b['wins']}/{b['target']}"))
    if o.get("bstacks") is not None and (o.get("bstacks") or g.get("absorbed")):
        n = o["bstacks"]
        lines.append(_t(lang, f"🕳️ روح‌های جذب‌شده: {n}/{BOUNT_STACK_MAX}", f"🕳️ Absorbed souls: {n}/{BOUNT_STACK_MAX}"))
    return lines
