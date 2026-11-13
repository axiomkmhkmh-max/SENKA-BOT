"""SENKA+ Traitor Hunt (Bleach mafia): Soul Society hunts Aizen's spies in a group chat.

Roles: Captain (one; investigates one player per night), Traitor (Aizen's spies; they choose a victim each night),
Shinigami (everyone else). Night: traitors pick a victim, the Captain checks a suspect. Day: everyone votes to exile
one player (a tie exiles nobody). Soul Society wins when every traitor is gone; the traitors win when they equal
or outnumber everyone else. Pure logic: no MongoDB, no Telegram.
"""
import random

MIN_PLAYERS = 5
CAPTAIN, TRAITOR, SHINIGAMI = "captain", "traitor", "shinigami"


def new_game(uids, rng=None):
    rng = rng or random.Random()
    uids = list(dict.fromkeys(uids))
    if len(uids) < MIN_PLAYERS:
        raise ValueError("Traitor Hunt needs at least 5 players")
    rng.shuffle(uids)
    n_traitors = max(1, len(uids) // 4)
    players = {}
    for i, uid in enumerate(uids):
        role = TRAITOR if i < n_traitors else CAPTAIN if i == n_traitors else SHINIGAMI
        players[uid] = {"role": role, "alive": True}
    return {"players": players, "phase": "night", "day": 1, "kill": None, "votes": {}, "check": {},
            "winner": None, "log": []}


def alive(state, role=None):
    return [u for u, p in state["players"].items() if p["alive"] and (role is None or p["role"] == role)]


def _need_night(state):
    if state["winner"]:
        raise ValueError("the game is over")
    if state["phase"] != "night":
        raise ValueError("not night")


def traitor_pick(state, traitor, victim):
    _need_night(state)
    if traitor not in alive(state, TRAITOR):
        raise ValueError("only living traitors choose a victim")
    p = state["players"].get(victim)
    if not p or not p["alive"] or p["role"] == TRAITOR:
        raise ValueError("invalid victim")
    state["kill"] = victim
    return True


def captain_check(state, captain, suspect):
    _need_night(state)
    if captain not in alive(state, CAPTAIN):
        raise ValueError("only the living Captain investigates")
    p = state["players"].get(suspect)
    if not p or not p["alive"] or suspect == captain:
        raise ValueError("invalid suspect")
    state["check"][captain] = p["role"] == TRAITOR  # True = a spy of Aizen
    return state["check"][captain]


def resolve_night(state):
    _need_night(state)
    victim = state.get("kill")
    if victim and state["players"][victim]["alive"]:
        state["players"][victim]["alive"] = False
        state["log"].append({"k": "killed", "uid": victim})
    state["kill"] = None
    state["phase"] = "day"
    state["votes"] = {}
    _check_win(state)
    return victim


def vote(state, voter, target):
    if state["winner"]:
        raise ValueError("the game is over")
    if state["phase"] != "day":
        raise ValueError("not day")
    if voter not in alive(state):
        raise ValueError("only living players vote")
    if target is not None and (target not in state["players"] or not state["players"][target]["alive"] or target == voter):
        raise ValueError("invalid vote")
    state["votes"][voter] = target
    return True


def resolve_day(state):
    if state["winner"]:
        raise ValueError("the game is over")
    if state["phase"] != "day":
        raise ValueError("not day")
    tally = {}
    for t in state["votes"].values():
        if t is not None:
            tally[t] = tally.get(t, 0) + 1
    exiled = None
    if tally:
        top = max(tally.values())
        leaders = [u for u, c in tally.items() if c == top]
        if len(leaders) == 1 and top * 2 > len(alive(state)):  # a strict majority of the living must agree
            exiled = leaders[0]
            state["players"][exiled]["alive"] = False
            state["log"].append({"k": "exiled", "uid": exiled})
    state["votes"] = {}
    state["phase"] = "night"
    state["day"] += 1
    _check_win(state)
    return exiled


def _check_win(state):
    spies = len(alive(state, TRAITOR))
    others = len(alive(state)) - spies
    if spies == 0:
        state["winner"] = SHINIGAMI
    elif spies >= others:
        state["winner"] = TRAITOR
    return state["winner"]
