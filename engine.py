"""Pure turn-based combat engine (no I/O). State is plain JSON-able dicts.

Fighters are 'a' and 'b'. Events are small dicts rendered later by battle_text.
"""
import math
import random

from data_misc import FORM1, FORM2, FORM2_EFFECT, FORM1_LEVEL, FORM2_LEVEL, KIDO_NAMES, MASK_RAGE
from data_races import soft_stat
from data_weapons import BEATS
from data_bleachfx import (CERO_BREAK_AI, CERO_BREAK_PLAYER, CHANT_BAK, CHANT_HADO, CHANT_OPEN, GAUGE, RESOLVE,
                           RESURRECCION, RESURRECCION_RACES, SHUNPO_COUNTER, SIG)

DOT = {"burn": 0.03, "poison": 0.05, "bleed": 0.02}
from data_bleachfx import KONPAKU, RACE_KILLER  # SENKA+ race killers and Konpaku

DOT_TURNS = {"burn": 3, "poison": 3, "bleed": 4}


def new_fighter(name, level, stats, max_hp, max_re, weapon, armor=0, mods=None, kido=None,
                race="human", ai=False, zmult=1.0, element=None, luck=0, sig=None, mv=None):
    w = weapon or {"attack": 3, "crit": 0.0, "element": element or "light", "skills": [], "weapon_type": "melee"}
    return {"name": name, "level": level, "stats": dict(stats), "hp": int(max_hp), "max_hp": int(max_hp),
            "re": int(max_re), "max_re": int(max_re), "weapon": {"attack": w.get("attack", 3), "crit": w.get("crit", 0.0),
            "element": element or w.get("element", "light"), "skills": list(w.get("skills", [])),
            "type": w.get("weapon_type", "melee")}, "armor": armor, "mods": dict(mods or {}),
            "kido": {"had": list((kido or {}).get("had", [1])), "bak": list((kido or {}).get("bak", [1]))},
            "race": race, "ai": ai, "zmult": zmult, "fx": [], "guard": False, "shield": 0, "luck": luck,
            "form": {"on": 0, "mult": 1.0, "left": 0, "fat": 0, "used": [0, 0], "fx": None},
            "sig": sig, "mv": mv, "x": _new_x()}


def eff(f, k):
    v = soft_stat(f["stats"].get(k, 0))
    if f["form"]["on"] and k in ("zanjutsu", "kido", "hakuda"):
        v *= f["form"]["mult"]
    return v


def has_fx(f, k):
    return any(x["k"] == k and x["t"] > 0 for x in f["fx"])


def _new_x():
    """Bleach combat-feel state (see data_bleachfx). Plain ints only, so it is stored as-is in MongoDB."""
    return {"flash": 0, "charge": 0, "chant": 0, "open": 0, "cd": 0, "res_used": 0, "buff_t": 0, "buff_m": 1.0,
            "gauge": 0, "awake": 0}


def _x(f):
    """Fighter's feel-state. Battles saved before this pack (or hand-built fighters) have none: create it lazily."""
    x = f.get("x")
    if x is None:
        x = f["x"] = _new_x()
    for k, v in _new_x().items():  # battles saved before a field existed get it with its default
        x.setdefault(k, v)
    return x


def add_fx(f, k, turns, stacks=1):
    for x in f["fx"]:
        if x["k"] == k:
            x["t"] = max(x["t"], turns)
            if k == "poison":
                x["s"] = min(3, x["s"] + stacks)
            return
    f["fx"].append({"k": k, "t": turns, "s": stacks})


def total_def(f):
    d = (eff(f, "hakuda") * 0.5 + f["armor"]) * f["mods"].get("def", 1.0)
    return d * (0.85 if has_fx(f, "weaken") else 1.0)


def skill_p(f, sid):
    return sum(s["p"] for s in f["weapon"]["skills"] if s["id"] == sid)


def elem_mult(att, dfn):
    ae, de = att["weapon"]["element"], dfn["weapon"]["element"]
    if BEATS.get(ae) == de:
        return 1.5
    if BEATS.get(de) == ae:
        return 0.75
    return 1.1 if ae == "poison" else 1.0


def _f2fx(f):
    return f["form"]["fx"] if f["form"]["on"] else None


def _dmg_mult(att):
    m = att["mods"].get("dmg", 1.0)
    if att["form"]["fat"] > 0:
        m *= 0.6
    if has_fx(att, "fear"):
        m *= 0.9
    x = att.get("x")
    if x and x.get("buff_t", 0) > 0:
        m *= x.get("buff_m", 1.0)
    if x and x.get("awake", 0) > 0:  # released (Bankai / Resurrección)
        m *= GAUGE["dmg"]
    return m


def _take_mult(dfn):
    m = 1.0
    if has_fx(dfn, "shock"):
        m *= 1.15
    if dfn["guard"]:
        m *= 0.5
    if (dfn.get("x") or {}).get("open"):
        m *= CHANT_OPEN
    fx = _f2fx(dfn)
    if fx and fx[0] == "guard":
        m *= 1 - fx[1]
    return m


def _deal(state, side, power, rng, ev, kind="atk", allow_procs=True, extra_pierce=0.0):
    att, dfn = state[side], state["b" if side == "a" else "a"]
    fx = _f2fx(att)
    if (dfn.get("x") or {}).get("flash") and kind != "counter":  # Shunpo: the strike meets empty air, then is answered
        dfn["x"]["flash"] = 0
        ev.append({"k": "flash", "a": dfn["name"], "d": att["name"]})
        _deal(state, "b" if side == "a" else "a", SHUNPO_COUNTER, rng, ev, "counter", allow_procs=False)
        return 0
    dodge = min(0.45, max(0.05, eff(dfn, "hoho") * 0.002 - eff(att, "hoho") * 0.001))
    if has_fx(dfn, "hiren"):  # Hirenkyaku: a blur of speed
        dodge = min(0.70, dodge + SIG["hiren"]["dodge"])
    if fx and fx[0] == "pierce":
        pass
    dfx = _f2fx(dfn)
    if dfx and dfx[0] == "miss" and rng.random() < dfx[1]:
        ev.append({"k": "miss", "a": att["name"], "d": dfn["name"]})
        return 0
    if rng.random() < dodge:
        ev.append({"k": "dodge", "a": att["name"], "d": dfn["name"]})
        return 0
    pierce = att["mods"].get("pierce", 0) + skill_p(att, "pierce") / 100 + (fx[1] if fx and fx[0] == "pierce" else 0) + extra_pierce
    defense = total_def(dfn) * (1 - min(0.8, pierce))
    base = eff(att, "zanjutsu") * att["zmult"] + att["weapon"]["attack"]
    raw = max(1.0, base - defense * 0.6) * power
    crit_p = 0.05 + eff(att, "hoho") * 0.001 + att["weapon"]["crit"] + att["mods"].get("crit", 0) + (SIG["hiren"]["crit"] if has_fx(att, "hiren") else 0)
    if _x(att)["awake"] > 0:
        crit_p += GAUGE["crit"]
    crit = rng.random() < crit_p
    cm = 1.5 + eff(att, "zanjutsu") * 0.003 + skill_p(att, "surge") / 100
    dmg = raw * (cm if crit else 1.0) * elem_mult(att, dfn) * rng.uniform(0.9, 1.1) * _dmg_mult(att)
    dmg *= RACE_KILLER.get(att.get("race"), {}).get(dfn.get("race"), 1.0)  # canon race killers (SENKA+)
    ex = skill_p(att, "execute")
    if ex and dfn["hp"] < dfn["max_hp"] * 0.3:
        dmg *= 1 + ex / 100
    dmg *= _take_mult(dfn)
    return _apply(state, side, int(max(1, dmg)), crit, rng, ev, kind, allow_procs)


def _maybe_resolve(f, ev):
    """Resolve (Reiatsu surge): once per battle a human-controlled fighter pushed under the HP line digs in -
    a little healing, ailments cleansed, a short damage buff. Wild enemies never get it."""
    x = _x(f)
    if f.get("ai") or x["res_used"] or f["hp"] <= 0 or f["hp"] >= f["max_hp"] * RESOLVE["hp"]:
        return
    esp = f.get("race") in RESURRECCION_RACES  # Hollow / Arrancar answer the edge of death with Resurrección
    heal, dmg, turns = (RESURRECCION["heal"], RESURRECCION["dmg"], RESURRECCION["turns"]) if esp else (RESOLVE["heal"], RESOLVE["dmg"], RESOLVE["turns"])
    x["res_used"] = 1
    f["hp"] = min(f["max_hp"], f["hp"] + max(1, int(f["max_hp"] * heal)))
    f["fx"] = [e for e in f["fx"] if e["k"] not in DOT and e["k"] not in ("fear", "weaken", "shock")]
    x["buff_t"], x["buff_m"] = turns, dmg
    ev.append({"k": "resurrect" if esp else "resolve", "a": f["name"]})


def _gain(f, n, ev):
    """Spirit gauge fills while fighting. The event announces the moment it becomes ready to unleash."""
    x = _x(f)
    before = x["gauge"]
    x["gauge"] = min(GAUGE["full"], before + n)
    if before < GAUGE["full"] <= x["gauge"]:
        ev.append({"k": "gauge_full", "a": f["name"]})


def _apply(state, side, dmg, crit, rng, ev, kind, procs):
    att, dfn = state[side], state["b" if side == "a" else "a"]
    absorbed = 0
    if dfn["shield"] > 0:
        absorbed = min(dfn["shield"], dmg)
        dfn["shield"] -= absorbed
        dmg -= absorbed
    dfn["hp"] = max(0, dfn["hp"] - dmg)
    ev.append({"k": "hit", "a": att["name"], "d": dfn["name"], "n": dmg, "c": crit, "kind": kind, "abs": absorbed,
               "em": elem_mult(att, dfn)})
    if dmg > 0:  # every blow fills both spirits: the attacker's by striking, the target's by bleeding
        _gain(att, GAUGE["deal"], ev)
        _gain(dfn, GAUGE["take"] + min(GAUGE["take_cap"], int(dmg / max(1, dfn["max_hp"]) * GAUGE["take_share"])), ev)
    _maybe_resolve(dfn, ev)
    dx = dfn.get("x")
    if dx and dx.get("charge") and dfn["hp"] > 0 and dmg >= dfn["max_hp"] * (CERO_BREAK_AI if dfn.get("ai") else CERO_BREAK_PLAYER):  # a hard hit interrupts the gathering Cero
        dx["charge"] = 0
        ev.append({"k": "charge_break", "a": dfn["name"]})
    if dfn["guard"] and dmg > 0:
        cp = skill_p(dfn, "counter")
        if cp:
            back = max(1, int(dmg * cp / 100))
            att["hp"] = max(0, att["hp"] - back)
            ev.append({"k": "reflect", "a": dfn["name"], "d": att["name"], "n": back})
    if not procs or dmg <= 0 and absorbed <= 0:
        return dmg
    fx = _f2fx(att)
    for s in att["weapon"]["skills"]:
        sid, p = s["id"], s["p"]
        if sid in ("bleed", "burn", "poison", "shock", "freeze", "stun", "weaken") and rng.random() < p / 100:
            if sid == "freeze" or sid == "stun":
                add_fx(dfn, "skip", 1)
            elif sid == "shock":
                add_fx(dfn, "shock", 2)
            elif sid == "weaken":
                add_fx(dfn, "weaken", 3)
            else:
                add_fx(dfn, sid, DOT_TURNS[sid])
            ev.append({"k": "fx", "a": att["name"], "d": dfn["name"], "fx": sid})
        elif sid == "lifesteal" and dmg > 0:
            h = max(1, int(dmg * p / 100))
            att["hp"] = min(att["max_hp"], att["hp"] + h)
            ev.append({"k": "heal", "a": att["name"], "n": h})
        elif sid == "drain":
            stolen = int(dfn["max_re"] * p / 100)
            stolen = min(stolen, dfn["re"])
            dfn["re"] -= stolen
            att["re"] = min(att["max_re"], att["re"] + stolen)
            if stolen:
                ev.append({"k": "drain", "a": att["name"], "d": dfn["name"], "n": stolen})
    if fx:
        if fx[0] == "burn":
            add_fx(dfn, "burn", 3)
        elif fx[0] == "lifesteal" and dmg > 0:
            h = max(1, int(dmg * fx[1]))
            att["hp"] = min(att["max_hp"], att["hp"] + h)
            ev.append({"k": "heal", "a": att["name"], "n": h})
        elif fx[0] == "drain":
            stolen = min(int(dfn["max_re"] * fx[1]), dfn["re"])
            dfn["re"] -= stolen
            att["re"] = min(att["max_re"], att["re"] + stolen)
    dbl = skill_p(att, "double") / 100 + (fx[1] if fx and fx[0] == "double" else 0)
    if kind in ("atk", "hvy") and dfn["hp"] > 0 and dbl and rng.random() < dbl:
        ev.append({"k": "double", "a": att["name"]})
        _deal(state, side, 0.5, rng, ev, "echo", allow_procs=False)
    return dmg


def best_kido(f, branch):
    """Highest affordable spell number of a branch the fighter may cast."""
    mult = 2.5 if branch == "had" else 2.0
    ok = [n for n in f["kido"][branch] if f["level"] >= math.ceil(n * 0.8) and f["re"] >= n * mult]
    return max(ok) if ok else None


def can(f, action):
    if action in ("atk", "df"):
        return True
    if action == "hvy":
        return f["re"] >= f["max_re"] * 0.10
    if action == "kd":
        return best_kido(f, "had") is not None
    if action == "bk":
        return best_kido(f, "bak") is not None
    if action == "sg":
        sg = f.get("sig")
        x = _x(f)
        if sg not in SIG:
            return False
        if sg == "cero" and x["charge"]:
            return True  # the charge is already paid for: firing is always possible
        return x["cd"] <= 0 and f["re"] >= f["max_re"] * SIG[sg]["cost"]
    if action == "gx":  # Bankai / Resurrección: a full spirit gauge, and not already released
        x = _x(f)
        return x["gauge"] >= GAUGE["full"] and x["awake"] <= 0 and f["re"] >= f["max_re"] * GAUGE["cost"]
    if action == "ch":
        return best_kido(f, "had") is not None and not _x(f)["chant"]
    if action == "f1":
        return f["level"] >= FORM1_LEVEL and not f["form"]["on"] and not f["form"]["used"][0] and f["re"] >= f["max_re"] * FORM1[3]
    if action == "f2":
        c = FORM2.get(f["race"], FORM2["default"])
        return f["level"] >= FORM2_LEVEL and not f["form"]["on"] and not f["form"]["used"][1] and f["re"] >= f["max_re"] * c[3]
    return False


def start_turn(state, rng):
    """Apply start-of-turn effects for the current side. Returns (events, skipped)."""
    side = state["cur"]
    f = state[side]
    ev = []
    f["guard"] = False
    fs = _x(f)
    fs["flash"] = fs["open"] = 0
    if fs["cd"] > 0:
        fs["cd"] -= 1
    if fs["buff_t"] > 0:
        fs["buff_t"] -= 1
        if fs["buff_t"] <= 0:
            fs["buff_m"] = 1.0
    if fs["awake"] > 0:
        fs["awake"] -= 1
        if fs["awake"] == 0:
            ev.append({"k": "unleash_end", "a": f["name"]})
    f["re"] = min(f["max_re"], f["re"] + max(3, int(f["max_re"] * 0.05)))
    rg = f["mods"].get("regen", 0)
    if rg and 0 < f["hp"] < f["max_hp"]:  # companion healing (pet role)
        h = max(1, int(f["max_hp"] * rg))
        f["hp"] = min(f["max_hp"], f["hp"] + h)
        ev.append({"k": "heal", "a": f["name"], "n": h})
    for x in list(f["fx"]):
        if x["k"] in DOT:
            d = max(1, int(f["max_hp"] * DOT[x["k"]] * (x["s"] if x["k"] == "poison" else 1)))
            f["hp"] = max(0, f["hp"] - d)
            ev.append({"k": "dot", "d": f["name"], "n": d, "fx": x["k"]})
        if x["k"] != "skip":
            x["t"] -= 1
    f["fx"] = [x for x in f["fx"] if x["t"] > 0 or x["k"] == "skip"]
    fm = f["form"]
    if fm["fat"] > 0:
        fm["fat"] -= 1
    if fm["on"]:
        fm["left"] -= 1
        if fm["left"] <= 0:
            fm["fat"] = fm.get("fat_turns", 0)
            fm.update(on=0, mult=1.0, fx=None)
            ev.append({"k": "form_end", "a": f["name"]})
    if _check_end(state):
        return ev, True
    if fm["on"] and f["race"] == "visored" and rng.random() < MASK_RAGE:  # the Hollow inside takes the wheel
        add_fx(f, "skip", 1)
        ev.append({"k": "mask_lost", "a": f["name"]})
    if fs["awake"] > 0 and f["hp"] < f["max_hp"] * GAUGE["hollow_hp"] and rng.random() < GAUGE["hollow_p"]:
        add_fx(f, "skip", 1)  # released and battered: the Hollow inside takes the wheel
        ev.append({"k": "mask_lost", "a": f["name"]})
    skip = [x for x in f["fx"] if x["k"] == "skip"]
    if skip:
        f["fx"] = [e for e in f["fx"] if e["k"] != "skip"]
        ev.append({"k": "skip", "a": f["name"]})
        if _x(f)["charge"]:  # a stunned fighter loses the Cero they were gathering
            _x(f)["charge"] = 0
            ev.append({"k": "charge_break", "a": f["name"]})
        return ev, True
    state["awaiting"] = True
    return ev, False


def _check_end(state, ev=None):
    a, b = state["a"], state["b"]
    for f in (a, b):  # Konpaku (SENKA+): duels only; the soul is pulled back once
        if f["hp"] <= 0 and state.get("pvp") and f.get("lives", 0) > 0:
            f["lives"] -= 1
            f["hp"] = max(1, int(f["max_hp"] * KONPAKU["hp"]))
            f["fx"] = [e for e in f["fx"] if e["k"] not in DOT and e["k"] not in ("fear", "weaken", "shock")]
            if ev is not None:
                ev.append({"k": "konpaku", "a": f["name"]})
    if a["hp"] <= 0 or b["hp"] <= 0:
        state["done"] = True
        state["winner"] = "b" if a["hp"] <= 0 and b["hp"] > 0 else "a" if b["hp"] <= 0 and a["hp"] > 0 else "draw"
        return True
    return False


def advance(state, max_turns=30):
    state["awaiting"] = False
    state["cur"] = "b" if state["cur"] == "a" else "a"
    if state["cur"] == state["first"]:
        state["turn"] += 1
        if state["turn"] > max_turns:
            state["done"] = True
            ra, rb = state["a"]["hp"] / state["a"]["max_hp"], state["b"]["hp"] / state["b"]["max_hp"]
            state["winner"] = "a" if ra > rb else "b" if rb > ra else "draw"


def _signature(state, side, rng, ev):
    """The race's signature move (see data_bleachfx.SIG). Caller has already checked can(f, "sg")."""
    f = state[side]
    o = state["b" if side == "a" else "a"]
    sg, c, x = f["sig"], SIG[f["sig"]], _x(f)
    if sg == "cero":
        if not x["charge"]:  # turn 1: gather the Cero (telegraphed - the opponent can guard, shield or strike first)
            f["re"] -= int(f["max_re"] * c["cost"])
            x["charge"] = 1
            ev.append({"k": "cero_charge", "a": f["name"], "d": o["name"]})
        else:  # turn 2: fire
            x["charge"] = 0
            x["cd"] = c["cd"]
            mult, pierce = (c["ai_mult"], c["ai_pierce"]) if f.get("ai") else (c["mult"], c["pierce"])
            _deal(state, side, mult, rng, ev, "cero", allow_procs=True, extra_pierce=pierce)
        return
    f["re"] -= int(f["max_re"] * c["cost"])
    x["cd"] = c["cd"]
    if sg == "shunpo":
        x["flash"] = 1
        ev.append({"k": "shunpo", "a": f["name"]})
    elif sg == "hiren":
        add_fx(f, "hiren", c["turns"])
        ev.append({"k": "hiren", "a": f["name"]})
        _deal(state, side, c["strike"], rng, ev, "blitz", allow_procs=False)  # arrives with a quick strike
    elif sg == "bring":
        _deal(state, side, c["mult"], rng, ev, "bring", allow_procs=True)
        if o["hp"] > 0 and rng.random() < c["bleed"]:
            add_fx(o, "bleed", DOT_TURNS["bleed"])
            ev.append({"k": "fx", "a": f["name"], "d": o["name"], "fx": "bleed"})
    elif sg == "guts":
        h = max(1, int(f["max_hp"] * c["heal"]))
        f["hp"] = min(f["max_hp"], f["hp"] + h)
        f["fx"] = [e for e in f["fx"] if e["k"] not in DOT and e["k"] not in ("fear", "weaken", "shock")]
        x["buff_t"], x["buff_m"] = c["turns"] + 1, c["dmg"]
        ev.append({"k": "guts", "a": f["name"], "n": h})


def do_action(state, action, rng, max_turns=30):
    side = state["cur"]
    f = state[side]
    ev = []
    if not can(f, action):
        action = "atk"
    if action == "atk":
        _deal(state, side, 1.0, rng, ev, "atk")
    elif action == "hvy":
        f["re"] -= int(f["max_re"] * 0.10)
        _deal(state, side, 1.6, rng, ev, "hvy")
        if f.get("mv") and (f["form"]["on"] or _x(f)["awake"] > 0) and ev and ev[-1].get("k") == "hit":
            ev[-1]["mv"] = f["mv"]  # released + known blade: the strike is called by its technique name
    elif action == "kd":
        n = best_kido(f, "had")
        f["re"] -= int(n * 2.5)
        o = state["b" if side == "a" else "a"]
        raw = eff(f, "kido") * (n / 10) * 1.8 * f["mods"].get("kido", 1.0) * rng.uniform(0.9, 1.1)
        chanted = bool(_x(f)["chant"])
        if chanted:  # the incantation is spent: full-power spell
            raw *= CHANT_HADO
            _x(f)["chant"] = 0
        dmg = int(max(1, raw * _dmg_mult(f) * _take_mult(o) - total_def(o) * 0.15))
        _apply(state, side, dmg, False, rng, ev, "hado", False)
        ev[-1]["chant"] = chanted
        ev[-1]["num"] = n
        ev[-1]["spell"] = KIDO_NAMES.get(("had", n), "")
    elif action == "bk":
        n = best_kido(f, "bak")
        f["re"] -= int(n * 2.0)
        gain = eff(f, "kido") * (n / 10) * 2.5 + 10 + f["max_hp"] * 0.05
        if _x(f)["chant"]:
            gain *= CHANT_BAK
            _x(f)["chant"] = 0
        f["shield"] += int(gain)
        ev.append({"k": "shield", "a": f["name"], "n": f["shield"], "num": n, "spell": KIDO_NAMES.get(("bak", n), "")})
        if n >= 30 and rng.random() < 0.6:
            o = state["b" if side == "a" else "a"]
            add_fx(o, "skip", 1)
            ev.append({"k": "fx", "a": f["name"], "d": o["name"], "fx": "stun"})
    elif action == "df":
        f["guard"] = True
        f["re"] = min(f["max_re"], f["re"] + int(f["max_re"] * 0.05))
        ev.append({"k": "guard", "a": f["name"]})
    elif action == "ch":  # Kidō chanting: the turn is spent speaking the incantation, and you stand open
        _x(f)["chant"] = 1
        _x(f)["open"] = 1
        ev.append({"k": "chant", "a": f["name"]})
    elif action == "sg":
        _signature(state, side, rng, ev)
    elif action == "gx":
        x = _x(f)
        f["re"] -= int(f["max_re"] * GAUGE["cost"])
        x["gauge"] = 0
        x["awake"] = GAUGE["turns"] + 1  # +1: the countdown ticks at the start of each of your turns, so this covers `turns` actions
        ev.append({"k": "unleash", "a": f["name"], "mv": f.get("mv"), "r": f.get("race")})
        _deal(state, side, GAUGE["strike"], rng, ev, "hvy")  # arrives with the release: Bankai is an attack, not a pause
        if f.get("mv") and ev and ev[-1].get("k") == "hit":
            ev[-1]["mv"] = f["mv"]
    elif action == "f1":
        f["re"] -= int(f["max_re"] * FORM1[3])
        f["form"].update(on=1, mult=FORM1[0], left=FORM1[1], fx=None, fat_turns=FORM1[2])
        f["form"]["used"][0] = 1
        ev.append({"k": "form", "a": f["name"], "n": 1, "r": f["race"]})
    elif action == "f2":
        c = FORM2.get(f["race"], FORM2["default"])
        f["re"] -= int(f["max_re"] * c[3])
        f["form"].update(on=2, mult=c[0], left=c[1], fat_turns=c[2], fx=list(FORM2_EFFECT.get(f["weapon"]["type"], ("pierce", 0.15))))
        f["form"]["used"][1] = 1
        ev.append({"k": "form", "a": f["name"], "n": 2, "r": f["race"]})
    _check_end(state, ev)
    if not state["done"]:
        advance(state, max_turns)
    else:
        state["awaiting"] = False
    state["last"] = ev
    return ev


def ai_choose(state, side, rng):
    f = state[side]
    r = rng.random()
    sg = f.get("sig")
    if can(f, "gx") and r < 0.7:  # a full spirit gauge is almost always spent
        return "gx"
    if sg == "cero" and _x(f)["charge"] and r < 0.85:  # a gathered Cero is almost always fired
        return "sg"
    if f["hp"] < f["max_hp"] * 0.3 and r < 0.3:
        return "df"
    if sg and sg != "cero" and r < 0.22 and can(f, "sg") and not (sg == "guts" and f["hp"] > f["max_hp"] * 0.7):
        return "sg"
    if sg == "cero" and r < 0.20 and can(f, "sg"):
        return "sg"
    if r < 0.70:
        return "atk"
    if r < 0.85:
        return "df"
    for a in ("f2", "kd", "hvy"):
        if can(f, a) and (a != "f2" or f["hp"] < f["max_hp"] * 0.6):
            return a
    return "atk"


def new_state(a, b, rng, pvp=False):
    intro = []
    if pvp:  # duels give both fighters their Konpaku lives (SENKA+)
        a["lives"] = b["lives"] = KONPAKU["lives"]
    for x, y in ((a, b), (b, a)):  # spiritual pressure
        if x["max_re"] >= 2 * y["max_re"]:
            add_fx(y, "fear", 3)
            intro.append({"k": "pressure", "a": x["name"], "d": y["name"]})
    ea, eb = eff(a, "hoho"), eff(b, "hoho")
    first = "a" if ea > eb or (ea == eb and rng.random() < 0.5) else "b"
    return {"a": a, "b": b, "turn": 1, "cur": first, "first": first, "done": False, "winner": None,
            "awaiting": False, "last": [], "intro": intro, "pvp": bool(pvp)}


def run_ai(state, rng, max_turns=30, ai_sides=("b",)):
    """Advance until a human must act or the fight ends. Returns events."""
    events = []
    guard = 0
    while not state["done"] and guard < 200:
        guard += 1
        if state.get("awaiting") and state["cur"] not in ai_sides:
            break
        ev, skipped = start_turn(state, rng)
        events += ev
        if state["done"]:
            break
        if skipped:
            advance(state, max_turns)
            continue
        if state["cur"] in ai_sides:
            events += do_action(state, ai_choose(state, state["cur"], rng), rng, max_turns)
        else:
            break
    return events


def hp_bar(cur, mx, n=10):
    k = 0 if mx <= 0 else max(0, min(n, math.ceil(n * cur / mx)))
    return "█" * k + "░" * (n - k)


def do_potion(state, kind, pct, max_turns=30):
    f = state[state["cur"]]
    if kind == "hp":
        n = int(f["max_hp"] * pct / 100)
        f["hp"] = min(f["max_hp"], f["hp"] + n)
    else:
        n = int(f["max_re"] * pct / 100)
        f["re"] = min(f["max_re"], f["re"] + n)
    ev = [{"k": "potion", "a": f["name"], "n": n, "kind": kind}]
    advance(state, max_turns)
    state["last"] = ev
    return ev
