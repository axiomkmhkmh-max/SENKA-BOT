"""Hollow Chase: a Hollow runs through three paths and the players decide where to chase it.

Each round the Hollow leaves a hint that is right 60% of the time. Players vote left, mid or right.
The majority choice wins the round. A right choice moves the chase forward; a wrong one costs one
of the Hollow's stamina and the chase repeats the same round. Reach CATCH_AT rounds to catch it,
or lose all stamina and it escapes. Works for one player (solo) or a whole group (votes).

Pure logic, no I/O. Run tests: python -m unittest test_engine_chase -v
"""
import random
from collections import Counter

DIRECTIONS = ("left", "mid", "right")
CATCH_AT = 4          # correct rounds needed to catch it
STAMINA = 3           # wrong rounds before it escapes
HINT_TRUE = 0.6       # chance the hint points the right way


def new_chase(rng: random.Random) -> dict:
    return {"path": [rng.choice(DIRECTIONS) for _ in range(CATCH_AT)], "round": 0, "stamina": STAMINA,
            "status": "running", "hint": None, "correct_votes": {}, "votes_total": 0, "log": []}


def make_hint(chase: dict, rng: random.Random) -> str:
    """The hint for the current round: right with HINT_TRUE probability, otherwise a wrong direction."""
    right = chase["path"][chase["round"]]
    if rng.random() < HINT_TRUE:
        hint = right
    else:
        hint = rng.choice([d for d in DIRECTIONS if d != right])
    chase["hint"] = hint
    return hint


def majority(votes: dict, rng: random.Random):
    """votes: uid -> direction. Returns the winning direction, breaking ties at random. None if no votes."""
    if not votes:
        return None
    counts = Counter(votes.values())
    top = max(counts.values())
    leaders = [d for d, n in counts.items() if n == top]
    return rng.choice(leaders)


def resolve_round(chase: dict, votes: dict, rng: random.Random) -> dict:
    """Resolve one round. Mutates and returns the chase; the outcome is in result['outcome']."""
    if chase["status"] != "running":
        raise ValueError("chase already finished")
    pick = majority(votes, rng)
    right = chase["path"][chase["round"]]
    if pick is None:
        chase["stamina"] -= 1
        outcome = "no_votes"
    elif pick == right:
        for uid, d in votes.items():
            if d == right:
                chase["correct_votes"][str(uid)] = chase["correct_votes"].get(str(uid), 0) + 1
        chase["round"] += 1
        outcome = "correct"
    else:
        chase["stamina"] -= 1
        outcome = "wrong"
    chase["votes_total"] += len(votes)
    chase["log"].append({"pick": pick, "right": right, "outcome": outcome})
    if chase["round"] >= CATCH_AT:
        chase["status"] = "caught"
    elif chase["stamina"] <= 0:
        chase["status"] = "escaped"
    return {"outcome": outcome, "pick": pick, "right": right, "status": chase["status"]}


def settle(chase: dict, pool: int) -> dict:
    """Split a catch pool among correct voters, proportional to correct votes. MVP = most correct votes."""
    if chase["status"] != "caught":
        return {"payouts": {}, "mvp": None}
    total = sum(chase["correct_votes"].values())
    payouts = {}
    if total:
        for uid, n in chase["correct_votes"].items():
            payouts[uid] = int(pool * n / total)
    mvp = max(chase["correct_votes"], key=chase["correct_votes"].get) if chase["correct_votes"] else None
    return {"payouts": payouts, "mvp": mvp}


def catch_pool(base_xp: int, base_coins: int, players: int) -> dict:
    """Bigger groups get a bigger reward, with diminishing returns."""
    k = 1.0 + 0.25 * min(players, 8) ** 0.5
    return {"xp": int(base_xp * 3 * k), "coins": int(base_coins * 3 * k)}
