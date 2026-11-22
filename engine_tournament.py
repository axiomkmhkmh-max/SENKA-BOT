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


def play_match(a, b, rng, max_turns=200, pvp=True):
    """Fight a vs b on fresh copies. Returns 'a', 'b' (the winner's side) — never a draw.
    pvp=True gives both the duel rules (Konpaku lives), so a bracket match plays like a real duel."""
    fa, fb = copy.deepcopy(a), copy.deepcopy(b)
    st = E.new_state(fa, fb, rng, pvp=pvp, duel_rules=False)  # standard-kit bracket: Konpaku lives, plain damage rules
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


# ---- Gotei Trial helpers (pure): training points, seeding, series, round pairing -----------------------------------
TRAIN_WIN_PTS = 10      # tournament points for winning a ranked training duel
TRAIN_LOSS_PTS = 2      # a loss still earns a little, so losing players keep training
TRAIN_PAIR_CAP = 2      # only the first N duels of the same pair in the training window earn points
MASTERY_PER_DUEL = 1    # stat points a counted training duel adds to the bracket fighter ...
MASTERY_CAP_DEFAULT = 20  # ... up to this many counted duels (live key `tour_mastery_cap`; 0 = everyone strictly equal)
NEUTRAL_RACE = "neutral"  # the one "race" every tournament fighter has: it appears in NO race table, so no race rule applies


def training_points(won: bool, pair_count: int) -> int:
    """Points for one ranked training duel. pair_count = duels this pair already counted in the window."""
    if int(pair_count) >= TRAIN_PAIR_CAP:
        return 0
    return TRAIN_WIN_PTS if won else TRAIN_LOSS_PTS


def mastery_points(duels: int, cap: int = MASTERY_CAP_DEFAULT) -> int:
    """Training mastery: every counted training duel (win or loss) is practice. It is worth a few stat points in the
    bracket, capped, so training makes you sharper but nobody can buy a big edge by grinding."""
    return max(0, min(int(cap), int(duels))) * MASTERY_PER_DUEL


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


def best_of(left: int) -> int:
    """Games in a series by how many fighters are still in the round: Bo3 early, Bo5 semifinals, Bo7 final.
    A longer series only removes upsets between equal fighters; it never favours anybody."""
    if left <= 2:
        return 7
    if left <= 4:
        return 5
    return 3


def play_series(a, b, rng, best_of_n: int = 3, max_turns: int = 200):
    """Fight a vs b until one side has won a majority of `best_of_n` games. -> ('a' | 'b', (wins_a, wins_b)).
    Every game is on fresh copies, so HP, Reiatsu and the spirit gauge never carry over."""
    need = int(best_of_n) // 2 + 1
    wa = wb = 0
    while wa < need and wb < need:
        if play_match(a, b, rng, max_turns) == "a":
            wa += 1
        else:
            wb += 1
    return ("a" if wa > wb else "b"), (wa, wb)


UNKNOWN = "?"   # a slot nobody has reached yet (drawn as a question mark, like the Call of Duty bracket)


def bracket_columns(order: list, hist: list):
    """Everything a bracket picture needs. `order` = round-one slots (seed_bracket output, None = bye slot), `hist` = one
    list of {a, b, w, s} dicts per finished round, in pair order. Returns (columns, scores): columns[0] = the entrants,
    columns[k] = the winners of round k (UNKNOWN until it is played), the last column = the champion; scores[k][j] is the
    series score of the match that produced columns[k+1][j]."""
    size = len(order)
    cols, scores = [list(order)], []
    n, r = size, 0
    while n > 1:
        n //= 2
        if r < len(hist):
            cols.append([m["w"] for m in hist[r]])
            scores.append([str(m.get("s", "")) for m in hist[r]])
        else:
            cols.append([UNKNOWN] * n)
            scores.append([""] * n)
        r += 1
    return cols, scores


# ---- Standard kit: what a tournament fighter is made of (pure) ------------------------------------------------
# NO race. The fighter is built from nothing but the level, one standard weapon, one standard armour and a stat
# block that is the same in every stat. It has no race technique, no signature move, no race killer, no race
# damage / defence / HP modifier, no evolution and no Kidō (the race "neutral" is in none of those tables), so the
# only thing that differs between two fighters is the training mastery they earned in the tournament itself.
# Level, stats, gear, blade, pets, relics, artifacts, division, buffs, Xcution rank, Hōgyoku, spells and techniques of the
# real character are never read.
STD_WEAPON_K = 2.6      # same level scaling as a level-appropriate enemy (service_combat.ENEMY_K["a"])
STD_ARMOR_K = 0.9       # ... and ENEMY_K["ar"]
STD_CRIT = 0.05
STD_BASE = 8.0          # every stat starts here
STAT_KEYS = ("zanjutsu", "kido", "hakuda", "hoho", "reiatsu")


def points_for_level(level: int) -> int:
    """Stat points a character has earned by `level` (3 per level, +1 on every 5th)."""
    return sum(3 + (1 if lv % 5 == 0 else 0) for lv in range(2, int(level) + 1))


def standard_stats(level: int, mastery: int = 0) -> dict:
    """The same value in all five stats: STD_BASE plus the level's points and the mastery, spread evenly."""
    each = round(STD_BASE + (points_for_level(level) + int(mastery)) / len(STAT_KEYS), 3)
    return {k: each for k in STAT_KEYS}


def standard_weapon(level: int) -> dict:
    """The one weapon everybody fights with, in the shape engine.new_fighter stores it."""
    from engine_range import reach_for
    return {"attack": 3 + int(level) * STD_WEAPON_K, "crit": STD_CRIT, "element": "light", "skills": [],
            "type": "melee", "reach": reach_for("melee")}


def standard_armor(level: int) -> float:
    return int(level) * STD_ARMOR_K


def standard_fighter(name: str, level: int, mastery: int = 0) -> dict:
    """The tournament fighter: identical for everybody except for `mastery` (see mastery_points)."""
    from data_races import soft_stat
    from service_player import max_hp, max_reiatsu
    st = standard_stats(level, mastery)
    f = E.new_fighter(name, int(level), st, max_hp(int(level), soft_stat(st["hakuda"])),
                      max_reiatsu(int(level), soft_stat(st["reiatsu"])), None, armor=standard_armor(level), mods={},
                      kido={"had": [], "bak": []}, race=NEUTRAL_RACE, zmult=1.0, element="light")
    f["weapon"] = standard_weapon(level)
    return f
