"""SENKA+ tag battle: 1-3 fighters a side, one active at a time.

Tagging (Heat the Soul style) spends your turn to bring in a fresh fighter, who hits harder with their first blow.
When the active fighter falls, the next one steps in for free. Every blow goes through engine._deal, so Bleach
race killers, signature rules and the spirit gauge all keep working inside team fights.
Pure logic: no MongoDB, no Telegram.
"""
import engine as E
from engine_range import START_DIST, MOVES, ZONE_MAX

TEAM_MIN, TEAM_MAX = 1, 3
TAG_POWER = 1.10        # first blow of a fighter who was tagged in
TEAM_TURNS = 40         # rounds (each side acts once per round) before the higher HP share wins


def new_team_state(team_a, team_b, rng=None):
    for team in (team_a, team_b):
        if not (TEAM_MIN <= len(team) <= TEAM_MAX):
            raise ValueError("a team needs 1 to 3 fighters")
    st = {"teams": {"a": list(team_a), "b": list(team_b)}, "idx": {"a": 0, "b": 0}, "cur": "a",
          "round": 1, "done": False, "winner": None, "last": [], "dist": START_DIST}
    for f in list(team_a) + list(team_b):
        f["tag_in"] = False
    return st


def _alive(team):
    return [i for i, f in enumerate(team) if f["hp"] > 0]


def active(st, side):
    team, i = st["teams"][side], st["idx"][side]
    if i < len(team) and team[i]["hp"] > 0:
        return team[i]
    alive = _alive(team)
    if not alive:
        return None
    st["idx"][side] = alive[0]
    return team[alive[0]]


def _other(side):
    return "b" if side == "a" else "a"


def _check_end(st):
    for side in ("a", "b"):
        if not _alive(st["teams"][side]):
            st["done"] = True
            st["winner"] = _other(side)
            return True
    return False


def _view(st, side):
    """The active pair as a two-fighter view, so the shared distance helpers can run on it."""
    return {"a": active(st, "a"), "b": active(st, "b"), "cur": side, "dist": E.dist_of(st)}


def _sync(st, v):
    st["dist"] = v["dist"]


def act(st, side, action, target=None, rng=None):
    """action: 'atk' or 'tag' (target = index of the fighter to bring in). Returns the events of this action."""
    if st["done"]:
        raise ValueError("battle is over")
    if side != st["cur"]:
        raise ValueError("not this side's turn")
    rng = rng or __import__("random").Random()
    me, foe = active(st, side), active(st, _other(side))
    ev = []
    if me is None or foe is None:
        _check_end(st)
        return ev
    if action == "tag":
        team = st["teams"][side]
        ok = target is not None and 0 <= target < len(team) and team[target]["hp"] > 0 and target != st["idx"][side]
        if ok:
            st["idx"][side] = target
            team[target]["tag_in"] = True
            ev.append({"k": "tag", "a": team[target]["name"]})
        else:  # no valid fighter to bring in: the turn is lost to a plain attack instead
            action = "atk"
            ev.append({"k": "tag_fail"})
    if action in ("mvs", "mvn", "rt"):  # distance: the turn is spent moving, not striking
        v = _view(st, side)
        ev.append(E._range_move(v, side, action))
        _sync(st, v)
        action = None
    if action == "atk":
        me = active(st, side)
        band = E._band(me, "atk")
        d = E.dist_of(st)
        if band and d > band[1]:  # out of reach: the turn closes the gap
            v = _view(st, side)
            ev.append(E._close_in(v, side, band[1]))
            _sync(st, v)
            action = None
        elif band and d < band[0]:  # too close for this weapon: back off
            v = _view(st, side)
            ev.append(E.apply_retreat(v, side))
            _sync(st, v)
            action = None
    if action == "atk":
        me = active(st, side)
        power = 1.0
        if me.get("tag_in"):
            power = TAG_POWER
            me["tag_in"] = False
        view = {"a": me, "b": foe} if side == "a" else {"a": foe, "b": me}
        E._deal(view, side, power, rng, ev, "atk", allow_procs=True)
    _check_end(st)
    if not st["done"]:
        st["cur"] = _other(side)
        if st["cur"] == "a":
            st["round"] += 1
            if st["round"] > TEAM_TURNS:
                st["done"] = True
                ha = sum(max(0, f["hp"]) / f["max_hp"] for f in st["teams"]["a"]) / len(st["teams"]["a"])
                hb = sum(max(0, f["hp"]) / f["max_hp"] for f in st["teams"]["b"]) / len(st["teams"]["b"])
                st["winner"] = "a" if ha > hb else "b" if hb > ha else "draw"
    st["last"] = ev
    return ev
