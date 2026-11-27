"""Fight flavour (Nov 21): the narrator's lines (data_narration) and one random challenge per normal fight.

Pure logic on the battle state (no I/O), so it runs inside pve_act / pvp turns and is stored with the fight.
  state["nar"]  recent narration keys (no repeats inside a fight)
  state["chl"]  the fight's challenge: {"id", "n", "c" (progress), "ok" (None / False once broken), "seen": [...]}
"""
import random

from data_narration import choose

NAR_CHANCE = 0.55          # share of turns that get a narrator line (the first turn always does)
CHL_BONUS = 0.25           # a completed challenge pays +25% XP and coins ...
CHL_CARD_CHANCE = 0.20     # ... and has this chance of an ability card of the player's race

ABILITY_ACTS = ("sg", "t1", "t2", "t3", "gt", "kd", "bk", "bal", "blv", "bla", "neg", "gar", "if", "bt", "b2", "bu", "gs", "sk")
CHALLENGES = [
    {"id": "noguard", "kind": "forbid", "acts": ("df",), "fa": "بدون گارد (دفاع) ببر", "en": "Win without Guard"},
    {"id": "nopot", "kind": "forbid", "acts": ("pot",), "fa": "بدون معجون ببر", "en": "Win without a potion"},
    {"id": "nomove", "kind": "forbid", "acts": ("mvs", "mvn", "rt"), "fa": "بدون شونپو، سونیدو و عقب‌نشینی ببر",
     "en": "Win without Shunpo, Sonido or backing off"},
    {"id": "noheavy", "kind": "forbid", "acts": ("hvy",), "fa": "بدون ضربه‌ی سنگین ببر", "en": "Win without a heavy strike"},
    {"id": "crits", "kind": "count", "ev": "crit", "n": (3, 5), "fa": "{n} ضربه‌ی بحرانی بزن و ببر", "en": "Land {n} critical hits and win"},
    {"id": "dodges", "kind": "count", "ev": "dodge", "n": (3, 5), "fa": "{n} بار جاخالی بده و ببر", "en": "Dodge {n} times and win"},
    {"id": "special", "kind": "count", "ev": "ability", "n": (5, 8), "fa": "{n} بار توانایی بزن و ببر", "en": "Use abilities {n} times and win"},
    {"id": "fast", "kind": "turns", "n": (45, 60), "fa": "در {n} نوبت یا کمتر ببر", "en": "Win in {n} turns or fewer"},
    {"id": "hp", "kind": "hp", "n": (30, 45), "fa": "با بیش از {n}٪ جان ببر", "en": "Win with more than {n}% HP"},
    {"id": "bighit", "kind": "big", "n": (6, 8), "fa": "یک ضربه‌ی {n}٪ جان دشمن بزن و ببر", "en": "Land one blow of {n}% of the foe's HP and win"},
    {"id": "variety", "kind": "variety", "n": (3, 4), "fa": "{n} توانایی مختلف بزن و ببر", "en": "Use {n} different abilities and win"},
    {"id": "finisher", "kind": "finisher", "fa": "ضربه‌ی آخر را با یک توانایی بزن", "en": "Finish the foe with an ability"},
    {"id": "sidedodge", "kind": "count", "ev": "side_dodge", "n": (2, 3), "fa": "{n} بار در حالت جانبی جاخالی بده و ببر",
     "en": "Dodge {n} times in the side stance and win"},
]
BY_ID = {c["id"]: c for c in CHALLENGES}


def start(state: dict, rng=random, challenge: bool = True):
    """At the start of a fight: the opening narrator line and (for normal fights) a random challenge."""
    state["nar"] = []
    if challenge:
        c = rng.choice(CHALLENGES)
        n = rng.randint(*c["n"]) if c.get("n") else 0
        state["chl"] = {"id": c["id"], "n": n, "c": 0, "ok": True, "seen": []}
    i = choose("start", "fa", [], rng)
    state.setdefault("intro", []).append({"k": "nar", "m": "start", "i": i, "p": state["a"]["name"], "f": state["b"]["name"]})


def _moment(state: dict, action: str, ev: list, side: str = "a"):
    me, foe = state[side], state["b" if side == "a" else "a"]
    pn, fn = me["name"], foe["name"]
    hp, fhp = me["hp"] / max(1, me["max_hp"]), foe["hp"] / max(1, foe["max_hp"])
    hits_by_me = [e for e in ev if e.get("k") == "hit" and e.get("a") == pn]
    hits_on_me = [e for e in ev if e.get("k") == "hit" and e.get("d") == pn]
    if any(e.get("k") in ("unleash", "form") and e.get("a") == pn for e in ev):
        return "release"
    if any(e.get("k") in ("shikai", "mask_on") and e.get("a") == pn for e in ev):
        return "shikai"
    if 0 < fhp < 0.15:
        return "foe_low"
    if 0 < hp < 0.22:
        return "self_low"
    if any(e.get("c") for e in hits_by_me):
        return "crit"
    if any(e.get("n", 0) >= foe["max_hp"] * 0.06 for e in hits_by_me):
        return "big"
    if any(e.get("k") in ("dodge", "flash") and e.get("d") == pn or e.get("k") in ("ab_evade", "ab_shadow") and e.get("a") == pn for e in ev):
        return "dodge_me"
    if any(e.get("c") for e in hits_on_me):
        return "foe_crit"
    if any(e.get("k") == "ab_charge" and e.get("a") == pn for e in ev):
        return "charge"
    if any(e.get("k") == "fx" and e.get("a") == pn and e.get("fx") == "stun" for e in ev):
        return "stun"
    if any(e.get("k") == "dodge" and e.get("a") == pn for e in ev):
        return "dodged"
    if hp < 0.45 and fhp < hp - 0.1:
        return "comeback"
    if action in ("kd",) and hits_by_me:
        return "kido"
    if any(e.get("k") in ("shield", "shield_t", "blut_vene", "negacion") and e.get("a") == pn for e in ev):
        return "shield"
    if any(e.get("k") == "heal" and e.get("a") == pn and e.get("n", 0) >= me["max_hp"] * 0.015 for e in ev):
        return "heal"
    if action == "hvy" and hits_by_me:
        return "heavy"
    if action in ABILITY_ACTS:
        return "ability"
    if any(e.get("k") == "dot" and e.get("d") == fn for e in ev):
        return "dot"
    if action == "df":
        return "guard"
    if action in ("mvs", "mvn", "rt"):
        return "move"
    if action == "sd":
        return "side"
    if int(state.get("turn", 1)) >= 60 and random.random() < 0.5:
        return "long"
    if abs(hp - fhp) < 0.08 and random.random() < 0.5:
        return "even"
    return "atmos"


def _track(state: dict, action: str, ev: list):
    c = state.get("chl")
    if not c or c.get("ok") is False:
        return
    spec = BY_ID.get(c["id"])
    if not spec:
        return
    pn = state["a"]["name"]
    kind = spec["kind"]
    if kind == "forbid" and action in spec["acts"]:
        c["ok"] = False
        return
    if action in ABILITY_ACTS and action != "sk":
        c["last"] = action
        if action not in c["seen"]:
            c["seen"].append(action)
    elif action not in ("sd", "pot"):
        c["last"] = action
    if kind == "count":
        if spec["ev"] == "crit":
            c["c"] += sum(1 for e in ev if e.get("k") == "hit" and e.get("a") == pn and e.get("c"))
        elif spec["ev"] == "dodge":
            c["c"] += sum(1 for e in ev if (e.get("k") in ("dodge", "flash") and e.get("d") == pn)
                          or (e.get("k") in ("ab_evade", "ab_shadow") and e.get("a") == pn))
        elif spec["ev"] == "ability" and action in ABILITY_ACTS and action != "sk":
            c["c"] += 1
        elif spec["ev"] == "side_dodge" and (state.get("ang") or {}).get("a"):
            c["c"] += sum(1 for e in ev if e.get("k") == "dodge" and e.get("d") == pn)
    elif kind == "big":
        foe = state["b"]
        if any(e.get("k") == "hit" and e.get("a") == pn and e.get("n", 0) >= foe["max_hp"] * c["n"] / 100 for e in ev):
            c["c"] = 1
    elif kind == "variety":
        c["c"] = len(c["seen"])


def after_turn(state: dict, action: str, ev: list, rng=random, lang: str = "fa", side: str = "a") -> list:
    """Called after the player's action and the foe's answer: updates the challenge and maybe adds a narrator line."""
    if side == "a":
        _track(state, action, ev)
    if action == "sd" or not ev:
        return []
    if rng.random() > NAR_CHANCE:
        return []
    m = _moment(state, action, ev, side)
    recent = state.setdefault("nar", [])
    i = choose(m, "fa", recent, rng)
    if i < 0:
        return []
    recent.append(f"{m}:{i}")
    del recent[:-40]
    me, foe = state[side], state["b" if side == "a" else "a"]
    return [{"k": "nar", "m": m, "i": i, "p": me["name"], "f": foe["name"]}]


def result(state: dict, win: bool) -> dict:
    """At the end of a fight: was the challenge met? {"id", "n", "done"} or None (no challenge)."""
    c = state.get("chl")
    if not c:
        return None
    spec = BY_ID.get(c["id"]) or {}
    a = state["a"]
    ok = bool(win) and c.get("ok") is not False
    kind = spec.get("kind")
    if ok and kind in ("count", "big", "variety"):
        ok = c["c"] >= (c["n"] if kind != "big" else 1)
    if ok and kind == "turns":
        ok = int(state.get("turn", 1)) <= c["n"]
    if ok and kind == "hp":
        ok = a["hp"] * 100 >= a["max_hp"] * c["n"]
    if ok and kind == "finisher":
        ok = c.get("last") in ABILITY_ACTS
    return {"id": c["id"], "n": c["n"], "done": ok}


def text(c: dict, lang: str) -> str:
    spec = BY_ID.get(c["id"]) or {}
    from i18n import fnum
    return (spec.get("fa" if lang == "fa" else "en") or "").format(n=fnum(c.get("n", 0), lang))


def challenge_line(state: dict, lang: str) -> str:
    """One line for the battle header: the challenge and its progress."""
    c = state.get("chl")
    if not c:
        return ""
    from i18n import fnum
    spec = BY_ID.get(c["id"]) or {}
    prog = ""
    if spec.get("kind") in ("count", "variety"):
        prog = f" ({fnum(min(c['c'], c['n']), lang)}/{fnum(c['n'], lang)})"
    elif spec.get("kind") == "big":
        prog = " ✔️" if c["c"] else ""
    mark = "❌" if c.get("ok") is False else "🎯"
    label = "چالش" if lang == "fa" else "Challenge"
    return f"{mark} {label}: {text(c, lang)}{prog}\n"
