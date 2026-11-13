"""Hollow Hunt: a short chain of risk choices that replaces the passive hunt roll.

Pure logic, no I/O. A hunt has STAGES stages. Each stage offers 2-3 options; every option
has a risk profile (fight, trap or safe reward). Outcomes are plain dicts the handler turns
into XP/coins/items/battles. Run tests: python -m unittest test_engine_hunt -v
"""
import random

STAGES = 3

# Each option: kind = reward | fight | trap | none ; weight = roll chance inside its kind.
# Reward values are multipliers on the base XP/coins the handler computes from the level.
STAGE_TEMPLATES = [
    [
        {"id": "track", "kind": "reward", "xp": 1.0, "coin": 1.0, "label": "track"},
        {"id": "ambush", "kind": "fight", "scale": 1.0, "xp": 1.6, "label": "ambush"},
        {"id": "wait", "kind": "none", "label": "wait"},
    ],
    [
        {"id": "sneak", "kind": "reward", "xp": 0.8, "coin": 1.4, "label": "sneak"},
        {"id": "charge", "kind": "fight", "scale": 1.2, "xp": 2.0, "label": "charge"},
        {"id": "bait", "kind": "trap", "dmg_pct": 0.15, "coin": 0.5, "label": "bait"},
    ],
    [
        {"id": "seal", "kind": "item", "xp": 1.2, "label": "seal"},
        {"id": "push", "kind": "fight", "scale": 1.4, "xp": 2.5, "label": "push"},
        {"id": "retreat", "kind": "reward", "xp": 0.5, "coin": 0.5, "label": "retreat"},
    ],
]

# Chance that a fight option actually fights vs. turns into a trap (keeps risk visible).
FIGHT_TRAP_CHANCE = 0.15
# Bonus for finishing the whole chain without taking a trap.
CLEAN_BONUS_XP = 1.5


def new_hunt(rng: random.Random) -> dict:
    """Start a hunt. Stage templates are fixed; rng only decides small variations."""
    stages = []
    for tpl in STAGE_TEMPLATES[:STAGES]:
        opts = [dict(o) for o in tpl]
        rng.shuffle(opts)  # the order of buttons changes, the risk profile does not
        stages.append(opts)
    return {"stage": 0, "stages": stages, "trapped": False, "log": []}


def current_options(hunt: dict) -> list:
    """Options the player sees now (id + label only, no hidden rolls)."""
    if hunt["stage"] >= STAGES:
        return []
    return [{"id": o["id"], "label": o["label"]} for o in hunt["stages"][hunt["stage"]]]


def choose(hunt: dict, option_id: str, rng: random.Random) -> dict:
    """Resolve the chosen option. Returns an outcome dict and advances the hunt in place."""
    if hunt["stage"] >= STAGES:
        raise ValueError("hunt already finished")
    opt = next((o for o in hunt["stages"][hunt["stage"]] if o["id"] == option_id), None)
    if opt is None:
        raise ValueError(f"unknown option {option_id!r}")

    kind = opt["kind"]
    outcome = {"stage": hunt["stage"], "option": option_id, "kind": kind,
               "xp": 0.0, "coin": 0.0, "item": False, "fight": False, "scale": 1.0, "dmg_pct": 0.0}

    if kind == "fight" and rng.random() < FIGHT_TRAP_CHANCE:
        # the ambush was a feint: converted to a trap, reward reduced
        kind = "trap"
        outcome.update(kind=kind, dmg_pct=0.10, xp=opt.get("xp", 1.0) * 0.4, coin=0.0)
        outcome["feint"] = True
    elif kind == "fight":
        outcome.update(fight=True, scale=opt.get("scale", 1.0), xp=opt.get("xp", 1.0))
    elif kind == "trap":
        outcome.update(dmg_pct=opt.get("dmg_pct", 0.15), coin=opt.get("coin", 0.0))
    elif kind == "reward":
        outcome.update(xp=opt.get("xp", 1.0), coin=opt.get("coin", 1.0))
    elif kind == "item":
        outcome.update(item=True, xp=opt.get("xp", 1.0))
    # kind == "none": nothing happens, the hunt just moves on

    if kind == "trap":
        hunt["trapped"] = True
    hunt["log"].append(outcome)
    hunt["stage"] += 1
    outcome["finished"] = hunt["stage"] >= STAGES
    return outcome


def summarize(hunt: dict) -> dict:
    """Total multipliers for a finished (or partly finished) hunt."""
    xp = sum(o["xp"] for o in hunt["log"])
    coin = sum(o["coin"] for o in hunt["log"])
    if hunt["stage"] >= STAGES and not hunt["trapped"]:
        xp += CLEAN_BONUS_XP
    return {
        "xp_mult": round(xp, 3),
        "coin_mult": round(coin, 3),
        "items": sum(1 for o in hunt["log"] if o["item"]),
        "fights": [o["scale"] for o in hunt["log"] if o["fight"]],
        "dmg_pct": round(sum(o["dmg_pct"] for o in hunt["log"]), 3),
        "clean": not hunt["trapped"],
        "finished": hunt["stage"] >= STAGES,
    }
