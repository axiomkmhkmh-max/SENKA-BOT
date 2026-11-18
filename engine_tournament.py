"""SENKA+ Gotei Tournament: single elimination with Bleach round names. Pure logic (no MongoDB / Telegram).

Each match is a full fight run by the engine (engine.run_ai), on fresh copies of the fighters, so entrants
are never changed by a match. Odd entrant counts get a bye. A match that ends in a draw is settled by the
higher HP share, and a perfect tie by a coin toss.
"""
import copy
import random

import engine as E

MIN_ENTRANTS = 2
MAX_ENTRANTS = 64


def round_name(left: int) -> str:
    """Name of a round by how many fighters are still in it (2 = the final)."""
    if left <= 2:
        return "captains_assembly"   # Captains' Assembly: the final
    if left <= 4:
        return "seat_trial"          # Seat Trial: semifinal
    if left <= 8:
        return "academy_exam"        # Academy Exam: quarterfinal
    return "preliminary"


def play_match(a, b, rng, max_turns=30, pvp=True):
    """Fight a vs b on fresh copies. Returns 'a', 'b' (the winner's side) — never a draw.
    pvp=True gives both the duel rules (Konpaku lives), so a bracket match plays like a real duel."""
    fa, fb = copy.deepcopy(a), copy.deepcopy(b)
    st = E.new_state(fa, fb, rng, pvp=pvp)
    E.run_ai(st, rng, max_turns, ai_sides=("a", "b"))
    if st.get("winner") in ("a", "b"):
        return st["winner"]
    ra = fa["hp"] / fa["max_hp"]
    rb = fb["hp"] / fb["max_hp"]
    if ra != rb:
        return "a" if ra > rb else "b"
    return rng.choice(["a", "b"])


def run_tournament(entrants, rng=None):
    """entrants: fighter dicts (from engine.new_fighter), each with a unique 'name'.
    Returns {'champion': name, 'rounds': [{'name': round_key, 'matches': [(a, b, winner_name_or_None)]}]}.
    """
    rng = rng or random.Random()
    if not (MIN_ENTRANTS <= len(entrants) <= MAX_ENTRANTS):
        raise ValueError("a tournament needs 2 to 64 entrants")
    names = [f["name"] for f in entrants]
    if len(set(names)) != len(names):
        raise ValueError("entrant names must be unique")
    alive = list(entrants)
    rng.shuffle(alive)
    rounds = []
    while len(alive) > 1:
        key = round_name(len(alive))
        matches, nxt = [], []
        for i in range(0, len(alive) - 1, 2):
            a, b = alive[i], alive[i + 1]
            side = play_match(a, b, rng)
            win = a if side == "a" else b
            matches.append((a["name"], b["name"], win["name"]))
            nxt.append(win)
        if len(alive) % 2:  # odd one out gets a bye into the next round
            bye = alive[-1]
            matches.append((bye["name"], None, bye["name"]))
            nxt.append(bye)
        rounds.append({"name": key, "matches": matches})
        alive = nxt
    return {"champion": alive[0]["name"], "rounds": rounds}


# ---- Gotei Trial helpers (pure): training points, seeding, round pairing ---------------------------------------
TRAIN_WIN_PTS = 10      # tournament points for winning a ranked training duel
TRAIN_LOSS_PTS = 2      # a loss still earns a little, so losing players keep training
TRAIN_PAIR_CAP = 2      # only the first N duels of the same pair in the training window earn points


def training_points(won: bool, pair_count: int) -> int:
    """Points for one ranked training duel. pair_count = duels this pair already counted in the window."""
    if int(pair_count) >= TRAIN_PAIR_CAP:
        return 0
    return TRAIN_WIN_PTS if won else TRAIN_LOSS_PTS


def seed_bracket(seeds: list) -> list:
    """Standard seeded bracket slots for `seeds` (best first). The size is the next power of two; missing seeds are
    None (byes, which go to the top seeds). Adjacent slots meet in round one and winners keep their slot order,
    so seeds 1 and 2 can only meet in the final, 1-4 in the semifinals, and so on."""
    n = len(seeds)
    size = 1
    while size < n:
        size *= 2
    order = [1]
    while len(order) < size:
        nxt = len(order) * 2
        order = [x for s in order for x in (s, nxt + 1 - s)]
    return [seeds[k - 1] if k <= n else None for k in order]


def pair_round(alive: list) -> list:
    """Adjacent slots of a bracket round as (a, b); b is None for a bye. len(alive) is a power of two."""
    return [(alive[i], alive[i + 1]) for i in range(0, len(alive) - 1, 2)]


# ---- Standard kit: what a tournament fighter is made of (pure) ------------------------------------------------
# Only the race (and its evolution stage, fixed for everyone) decides how two fighters differ. Level, stat points,
# gear, blade, pets, relics, artifacts, division, buffs, Xcution rank, Hogyoku, spells and techniques of the
# real character are never read: the fighter is built from a brand-new minimal character document.
STD_WEAPON_K = 2.6      # same level scaling as a level-appropriate enemy (service_combat.ENEMY_K["a"])
STD_ARMOR_K = 0.9       # ... and ENEMY_K["ar"]
STD_CRIT = 0.05
STD_EVO = 2             # evolution stage every fighter gets (0..4)


def points_for_level(level: int) -> int:
    """Stat points a character has earned by `level` (3 per level, +1 on every 5th)."""
    return sum(3 + (1 if lv % 5 == 0 else 0) for lv in range(2, int(level) + 1))


def standard_stats(race_stats: dict, level: int) -> dict:
    """The race's base block plus the level's points, spread in the race's own proportions.
    Every race ends with the same total; only the shape differs."""
    base = {k: float(v) for k, v in race_stats.items()}
    tot = sum(base.values())
    extra = points_for_level(level)
    return {k: round(v + extra * v / tot, 3) for k, v in base.items()}


def standard_char(uid: int, name: str, race: str, level: int, race_stats: dict, kido_race: bool, evo: int = STD_EVO) -> dict:
    """A minimal character document: it carries ONLY what the standard kit needs."""
    return {"user_id": int(uid), "name": name, "race": race, "level": int(level),
            "stats": standard_stats(race_stats, level), "points": 0,
            "kido_refunded": True,                      # no refund write to the real character
            "kido": {"had": [1] if kido_race else [], "bak": [1] if kido_race else []},
            "party": [], "zanpakuto": {}, "evo": int(evo)}


def standard_weapon(level: int) -> dict:
    """The one weapon everybody fights with, in the shape engine.new_fighter stores it."""
    from engine_range import reach_for
    return {"attack": 3 + int(level) * STD_WEAPON_K, "crit": STD_CRIT, "element": "light", "skills": [],
            "type": "melee", "reach": reach_for("melee")}


def standard_armor(level: int) -> float:
    return int(level) * STD_ARMOR_K
