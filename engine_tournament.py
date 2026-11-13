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


def play_match(a, b, rng):
    """Fight a vs b on fresh copies. Returns 'a', 'b' (the winner's side) — never a draw."""
    fa, fb = copy.deepcopy(a), copy.deepcopy(b)
    st = E.new_state(fa, fb, rng)
    E.run_ai(st, rng, ai_sides=("a", "b"))
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
