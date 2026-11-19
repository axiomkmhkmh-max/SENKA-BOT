"""Pure turn-based combat engine (no I/O). State is plain JSON-able dicts.

Fighters are 'a' and 'b'. Events are small dicts rendered later by battle_text.
"""
import math
import random

from data_misc import FORM1, FORM2, FORM2_EFFECT, FORM1_LEVEL, FORM2_LEVEL, KIDO_NAMES, MASK_RAGE
from data_races import soft_stat
from data_race_rules import race_allows, fight_context, ctx_dmg_mult, GENERAL_SKILLS, gen_power
from data_race_tech import ABILITY_SHARE, ABILITY_STAT, FULLBRING_WEAPON, HEAVY_REIATSU, TECH_SLOTS, tech_of
from data_weapons import BEATS
from engine_range import (START_DIST, ZONE_MAX, MOVES, reach_for, can_move, apply_move, apply_retreat,
                          apply_knockback, zone_mult, SIDESTEP)
import data_kido as KD
from data_bleachfx import (CERO_BREAK_AI, CERO_BREAK_PLAYER, CHANT_BAK, CHANT_HADO, CHANT_OPEN, GAUGE, RESOLVE,
                           RESURRECCION, RESURRECCION_RACES, SHUNPO_COUNTER, SIG)

DOT = {"burn": 0.03, "poison": 0.05, "bleed": 0.02}
from data_bleachfx import KONPAKU, RACE_KILLER  # SENKA+ race killers and Konpaku

DOT_TURNS = {"burn": 3, "poison": 3, "bleed": 4}


TURN_RE_REGEN = 0.10   # share of max reiatsu recovered at the end of each of a fighter's turns (was 5%)
GUARD_RE_GAIN = 0.10   # share of max reiatsu a Guard turn gives back (was 5%)
GUARD_HP_GAIN = 0.05   # share of max HP a Guard turn gives back (new)
TURN_HP_REGEN = 0.03   # share of max HP recovered at the end of each turn (natural recovery, back again)

def new_fighter(name, level, stats, max_hp, max_re, weapon, armor=0, mods=None, kido=None,
                race="human", ai=False, zmult=1.0, element=None, luck=0, sig=None, mv=None, gen=None, bt=None):
    w = weapon or {"attack": 3, "crit": 0.0, "element": element or "light", "skills": [], "weapon_type": "melee"}
    return {"name": name, "level": level, "stats": dict(stats), "hp": int(max_hp), "max_hp": int(max_hp),
            "re": int(max_re), "max_re": int(max_re), "weapon": {"attack": w.get("attack", 3), "crit": w.get("crit", 0.0),
            "element": element or w.get("element", "light"), "skills": list(w.get("skills", [])),
            "type": w.get("weapon_type", "melee"), "reach": reach_for(w.get("weapon_type", "melee"), w.get("reach"))}, "armor": armor, "mods": dict(mods or {}),
            "kido": {"had": list((kido or {}).get("had", [1])), "bak": list((kido or {}).get("bak", [1]))},
            "race": race, "ai": ai, "zmult": zmult, "fx": [], "guard": False, "shield": 0, "luck": luck,
            "form": {"on": 0, "mult": 1.0, "left": 0, "fat": 0, "used": [0, 0], "fx": None},
            "sig": sig, "mv": mv, "gen": gen, "bt": bt, "x": _new_x()}


def eff(f, k):
    v = soft_stat(f["stats"].get(k, 0))
    if f["form"]["on"] and k in ("zanjutsu", "kido", "hakuda"):
        v *= f["form"]["mult"]
    return v


def evb(f, key, default=None):
    """The fighter's evolution bonus `key` (data_evolution), or `default`. Enemies and old saves have none."""
    return (f.get("evo") or {}).get(key, default)


def has_fx(f, k):
    return any(x["k"] == k and x["t"] > 0 for x in f["fx"])


def _new_x():
    """Bleach combat-feel state (see data_bleachfx). Plain ints only, so it is stored as-is in MongoDB."""
    return {"flash": 0, "charge": 0, "chant": 0, "open": 0, "cd": 0, "gcd": 0, "tcd": 0, "res_used": 0, "buff_t": 0, "buff_m": 1.0,
            "gauge": 0, "awake": 0, "slash": 0, "bstack": 0, "bseal": 0,
            # race techniques (data_race_tech): own cooldowns, a guard buff (Hierro) and a crit buff (Pesquisa)
            "t1cd": 0, "t2cd": 0, "t3cd": 0, "gd_t": 0, "gd_m": 1.0, "cb_t": 0, "cb_v": 0.0,
            # kidō (data_kido): per-spell cooldowns {"h31": turns} and the spell picked this turn ["kd"|"bk", number]
            "kcd": {}, "pick": None}


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


def _foe_mult(att, dfn):
    """Race passive against the foe kind (Spiritual Awareness: humans vs hollows). Enemies carry `foe`."""
    from data_races import spiritual_awareness_mult
    m = spiritual_awareness_mult(att.get("race"), dfn.get("foe"))
    if m != 1.0 and evb(att, "aware"):  # evolved Spiritual Awareness replaces the default bonus
        m = evb(att, "aware")
    return m


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
    dx = dfn.get("x") or {}
    if dx.get("gd_t", 0) > 0:  # Hierro and other guard techniques
        m *= dx.get("gd_m", 1.0)
    return m


# gear soft cap: weapon attack above GEAR_KNEE only counts GEAR_SLOPE. Stops the level-80 tier from
# doubling the level-30 tier and keeps the power curve continuous after level 30. Tunable here.
GEAR_KNEE, GEAR_SLOPE = 90, 0.6


def gear_soft(attack: float) -> float:
    a = float(attack or 0)
    return a if a <= GEAR_KNEE else GEAR_KNEE + (a - GEAR_KNEE) * GEAR_SLOPE


def strike_base(att, src="atk"):
    """Stat part + weapon of a blow. src: atk (plain attack: Zanjutsu), hvy (heavy: Zanjutsu and Reiatsu half and half),
    abl (ability: ABILITY_SHARE from the race's own stat, the rest from Zanjutsu; Fullbringer: the weapon counts more).
    The bond (zmult) strengthens the Zanjutsu part. Wild enemies always use the plain formula."""
    zpart = eff(att, "zanjutsu") * att["zmult"]
    w = gear_soft(att["weapon"]["attack"])
    if att.get("wild") or src == "atk":
        return zpart + w

    def power_of(stat):  # a form (mask, Shikai, Vollständig...) strengthens the race's ability stat too
        v = eff(att, stat)
        if att["form"]["on"] and stat not in ("zanjutsu", "kido", "hakuda"):  # eff() already scales those three
            v *= att["form"]["mult"]
        return v
    if src == "hvy":
        return (1 - HEAVY_REIATSU) * zpart + HEAVY_REIATSU * power_of("reiatsu") + w
    rs = ABILITY_STAT.get(att.get("race"))
    if rs == "weapon":
        return zpart + FULLBRING_WEAPON * w
    if rs:
        return (1 - ABILITY_SHARE) * zpart + ABILITY_SHARE * power_of(rs) + w
    return zpart + w


def race_factor(f) -> float:
    """How strongly a fighter's shields, heals and buffs work: ABILITY_SHARE of it follows the race's own stat against
    the fighter's average stat (0.5..2.0). 1.0 for wild enemies and for races whose stat is the weapon."""
    rs = ABILITY_STAT.get(f.get("race"))
    if f.get("wild") or not rs or rs == "weapon":
        return 1.0
    mean = sum(eff(f, k) for k in ("zanjutsu", "kido", "hakuda", "hoho", "reiatsu")) / 5 or 1.0
    return max(0.5, min(2.0, (1 - ABILITY_SHARE) + ABILITY_SHARE * eff(f, rs) / mean))


def _deal(state, side, power, rng, ev, kind="atk", allow_procs=True, extra_pierce=0.0, src=None):
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
    base = strike_base(att, src or ("hvy" if kind == "hvy" else "abl" if kind not in ("atk", "echo") else "atk"))
    raw = max(1.0, base - defense * 0.6) * power
    crit_p = 0.05 + eff(att, "hoho") * 0.001 + att["weapon"]["crit"] + att["mods"].get("crit", 0) + (SIG["hiren"]["crit"] if has_fx(att, "hiren") else 0)
    if _x(att)["awake"] > 0:
        crit_p += GAUGE["crit"]
    if _x(att)["cb_t"] > 0:  # Pesquisa and other focus techniques
        crit_p += _x(att)["cb_v"]
    crit = rng.random() < crit_p
    cm = 1.5 + eff(att, "zanjutsu") * 0.003 + skill_p(att, "surge") / 100
    dmg = raw * (cm if crit else 1.0) * elem_mult(att, dfn) * rng.uniform(0.9, 1.1) * _dmg_mult(att) * _zone(state, side) * _foe_mult(att, dfn)
    dmg *= RACE_KILLER.get(att.get("race"), {}).get(dfn.get("race"), 1.0)  # canon race killers (SENKA+)
    dmg *= ctx_dmg_mult(att.get("race"), fight_context(state, dfn))  # balance by fight type (data_race_rules)
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
    # only fighters that can release (Bankai / Resurrección) hear "the release is ready": Fullbringer, Quincy, Human and
    # wild enemies have no release button, so the line only confused them
    if before < GAUGE["full"] <= x["gauge"] and race_allows(f.get("race"), "gx") and not f.get("wild"):
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


def _kcd(f) -> dict:
    x = _x(f)
    if not isinstance(x.get("kcd"), dict):
        x["kcd"] = {}
    return x["kcd"]


def kido_castable(f, branch, n) -> bool:
    """Can this fighter cast spell n of the branch right now? Known, enough reiatsu (cost = share of max reiatsu), the spell
    is not cooling down, and from number 91 up the incantation must have been spoken. No level gate in the fight."""
    if n not in f["kido"][branch]:
        return False
    if f["re"] < KD.cost(branch, n, f["max_re"]) or _kcd(f).get(KD.key(branch, n), 0) > 0:
        return False
    return not KD.needs_chant(n, branch) or bool(_x(f)["chant"])


def kido_cooling(f) -> list:
    """Known spells that are cooling down right now: [(branch, number, turns_left)], highest number first."""
    out = []
    for branch in ("had", "bak"):
        for n in f["kido"][branch]:
            left = int(_kcd(f).get(KD.key(branch, n), 0))
            if left > 0:
                out.append((branch, n, left))
    return sorted(out, key=lambda r: -r[1])


def kido_list(f, branch) -> list:
    """Every spell of the branch the fighter can cast now, highest number first."""
    return sorted({n for n in f["kido"][branch] if kido_castable(f, branch, n)}, reverse=True)


def kido_menu(f, branch) -> list:
    """The spell menu: [(number, cost share of max reiatsu in %)] for every spell of the branch castable right now,
    highest number first. The player picks one of these (the button sends \"kd:<n>\" / \"bk:<n>\")."""
    return [(n, KD.cost_pct(branch, n)) for n in kido_list(f, branch)]


def kido_chant_locked(f, branch) -> bool:
    """True when the fighter knows a spell of the branch that only waits for the incantation (91+, no chant spoken yet)."""
    if _x(f)["chant"]:
        return False
    return any(KD.needs_chant(n, branch) and f["re"] >= KD.cost(branch, n, f["max_re"]) and _kcd(f).get(KD.key(branch, n), 0) <= 0
               for n in f["kido"][branch])


def chant_wanted(f) -> bool:
    """True when the fighter knows a spell that is blocked only by the missing incantation (Hadō and Bakudō 91+):
    enough reiatsu, level gate passed, not cooling down. Without this the 📿 button never showed for a Bakudō caster,
    the 98 could not be cast and the fight silently fell back to a weaker 82 / 79."""
    for branch in ("had", "bak"):
        for n in f["kido"][branch]:
            if not KD.needs_chant(n, branch):
                continue
            if f["re"] >= KD.cost(branch, n, f["max_re"]) and _kcd(f).get(KD.key(branch, n), 0) <= 0:
                return True
    return False


def best_kido(f, branch):
    """The spell that is cast: the one picked this turn (see do_action), else the highest castable number."""
    pick = _x(f).get("pick")
    if pick and pick[0] == ("kd" if branch == "had" else "bk"):
        return pick[1] if kido_castable(f, branch, pick[1]) else None
    ok = kido_list(f, branch)
    return ok[0] if ok else None


GETSUGA_COST = 0.15   # share of max reiatsu for the release
GETSUGA_DMG = 2.4     # strike multiplier of the release (a heavy strike is 1.6)


# ---- distance (فاصله): see engine_range.py ----
MOVE_ACTIONS = {"mvs": "shunpo", "mvn": "sonido", "rt": None}   # player/AI movement actions
PUSH_KIND = {"hvy": "hvy", "gt": "gt", "gx": "unleash"}         # attacks that knock the target back


def dist_of(state):
    return int(state.get("dist", START_DIST))


def _band(f, action):
    """(min, max) zones this action can hit at, or None when the action ignores distance."""
    lo, hi = reach_for(f["weapon"].get("type", "melee"), f["weapon"].get("reach"))
    if action == "atk" or (action == "sg" and f.get("sig") in ("bring", "soul")):
        return lo, hi
    if action in ("hvy", "gx"):
        return lo, min(ZONE_MAX, hi + 1)
    if action == "gt":
        return lo, min(ZONE_MAX, hi + 2)
    if action == "kd":  # kidō carries: no minimum range
        return 0, min(ZONE_MAX, hi + 1)
    if action == "sg" and f.get("sig") == "cero":
        return 0, ZONE_MAX
    if action in TECH_SLOTS:
        t = tech_of(f.get("race"), action)
        if t and t["kind"] in ("strike", "blur"):
            return (0, ZONE_MAX) if t["id"] == "cero_oscuras" else (lo, min(ZONE_MAX, hi + (1 if f["weapon"].get("type") == "ranged" else 0)))
    return None


def _zone(state, side):
    """Damage multiplier from spacing (attacker's weapon vs gap) and the target's stance."""
    lo, hi = reach_for(state[side]["weapon"].get("type", "melee"), state[side]["weapon"].get("reach"))
    other = "b" if side == "a" else "a"
    stance = SIDESTEP["mult"] if (state.get("ang") or {}).get(other) else 1.0
    return zone_mult(lo, hi, dist_of(state)) * stance


def _finish(state, ev, max_turns):
    _check_end(state, ev)
    if not state["done"]:
        advance(state, max_turns)
    else:
        state["awaiting"] = False
    state["last"] = ev
    return ev


def _move(state, side, move):
    f = state[side]
    if not can_move(f, move, dist_of(state)):
        return {"k": "outrange", "a": f["name"]}
    return apply_move(state, side, move)


def _close_in(state, side, hi):
    """Out of reach: the turn is spent closing the gap (sonido for a long gap, shunpo otherwise)."""
    d = dist_of(state)
    long_gap = d - MOVES["shunpo"]["zones"] > hi
    return _move(state, side, "sonido" if long_gap and can_move(state[side], "sonido", d) else "shunpo")


def _range_move(state, side, action):
    if action == "rt":
        if dist_of(state) >= ZONE_MAX:
            return {"k": "outrange", "a": state[side]["name"]}
        return apply_retreat(state, side)
    return _move(state, side, MOVE_ACTIONS[action])


def can(f, action):
    if action in ("atk", "df"):
        return True
    if not race_allows(f.get("race"), action):  # e.g. Arrancar cannot cast Kidō or release Bankai
        return False
    if action == "hvy":
        return f["re"] >= f["max_re"] * 0.10 and not _x(f).get("hv_last")
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
    if action in ("neg", "gar"):  # Hollow Negación and Garganta: own cost, shared special cooldown
        from data_bleachfx import GARGANTA, NEGACION
        c = NEGACION if action == "neg" else GARGANTA
        return _x(f)["cd"] <= 0 and f["re"] >= f["max_re"] * c["cost"]
    if action == "bt":  # the blade's own technique (after Shikai): its own cost and cooldown
        return bool(f.get("bt")) and _x(f)["tcd"] <= 0 and f["re"] >= f["max_re"] * f["bt"]["cost"]
    if action == "gs":  # general skill chosen in the profile: any race, own cost and cooldown
        spec = GENERAL_SKILLS.get(f.get("gen"))
        return bool(spec) and _x(f)["gcd"] <= 0 and f["re"] >= f["max_re"] * spec["cost"]
    if action in ("blv", "bla", "bal"):  # Quincy Blut / Arrancar Bala: their own cost, sharing the special cooldown
        from data_bleachfx import BALA, BLUT
        c = BLUT["blut_vene"] if action == "blv" else BLUT["blut_arterie"] if action == "bla" else BALA
        return _x(f)["cd"] <= 0 and f["re"] >= f["max_re"] * c["cost"]
    if action == "bnt":  # Bount Seal: spend soul stacks (set by PvE only) to hold the foe, own cooldown and cost
        from data_gangs import BOUNT_SEAL
        x = _x(f)
        return x["cd"] <= 0 and x["bstack"] >= BOUNT_SEAL["stacks"] and f["re"] >= f["max_re"] * BOUNT_SEAL["re"]
    if action == "gx":  # the race's release (Bankai, Resurrección...): a full spirit gauge, and not already released
        if f.get("wild"):
            return False  # wild enemies have no release
        x = _x(f)
        return x["gauge"] >= GAUGE["full"] and x["awake"] <= 0 and f["re"] >= f["max_re"] * GAUGE["cost"]
    if action in TECH_SLOTS:  # canon race technique (data_race_tech): unlocked by evolution, own cost and cooldown
        t = tech_of(f.get("race"), action)
        if not t or f.get("ai") and f.get("wild") or int(f.get("evs", -1)) < t["unlock"]:
            return False
        if t.get("need_form") and not f["form"]["on"]:
            return False
        return _x(f)[action + "cd"] <= 0 and f["re"] >= f["max_re"] * t["cost"]
    if action == "gc":  # Getsuga: raise the blade and gather reiatsu into it (the turn is spent)
        return _x(f)["slash"] <= 0 and not _x(f)["chant"]
    if action == "gt":  # release the gathered reiatsu as one wave
        return _x(f)["slash"] > 0 and f["re"] >= f["max_re"] * GETSUGA_COST
    if action == "ch":
        return (best_kido(f, "had") is not None or chant_wanted(f)) and not _x(f)["chant"]
    if action in ("f1", "f2"):
        # Shikai / Bankai, Resurrección / Full Resurrección and every race's forms are no longer free buttons at the
        # start of a fight: they come only with the full spirit gauge, as part of the 👑 release ("gx" in do_action).
        return False
    return False


def release_form(f) -> int:
    """Which form the 👑 release opens at this level: 2 (Bankai, Full Resurrección...) from FORM2_LEVEL,
    1 (Shikai, Resurrección...) from FORM1_LEVEL, 0 below (the release strike only)."""
    if f.get("wild"):
        return 0
    return 2 if f["level"] >= FORM2_LEVEL else 1 if f["level"] >= FORM1_LEVEL else 0


def merge_heals(ev):
    """One heal line per fighter per stretch of events: natural recovery, companion regen and Guard recovery
    used to print as two or three separate '+N HP' lines in the same turn. They are summed into the first one."""
    out, first = [], {}
    for e in ev:
        if e.get("k") == "heal":
            i = first.get(e["a"])
            if i is not None:
                out[i] = dict(out[i], n=out[i]["n"] + e["n"])
                continue
            first[e["a"]] = len(out)
        out.append(e)
    return out


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
    for k in ("t1cd", "t2cd", "t3cd", "gd_t", "cb_t"):
        if fs[k] > 0:
            fs[k] -= 1
    kc = _kcd(f)
    for k in list(kc):
        kc[k] -= 1
        if kc[k] <= 0:
            del kc[k]
    if fs["gd_t"] <= 0:
        fs["gd_m"] = 1.0
    if fs["cb_t"] <= 0:
        fs["cb_v"] = 0.0
    if fs["buff_t"] > 0:
        fs["buff_t"] -= 1
        if fs["buff_t"] <= 0:
            fs["buff_m"] = 1.0
    if fs["awake"] > 0:
        fs["awake"] -= 1
        if fs["awake"] == 0:
            ev.append({"k": "unleash_end", "a": f["name"]})
    f["re"] = min(f["max_re"], f["re"] + max(3, int(f["max_re"] * TURN_RE_REGEN)))
    if 0 < f["hp"] < f["max_hp"]:  # natural recovery every turn (tunable: TURN_HP_REGEN)
        h = max(1, int(f["max_hp"] * TURN_HP_REGEN))
        f["hp"] = min(f["max_hp"], f["hp"] + h)
        ev.append({"k": "heal", "a": f["name"], "n": h})
        fs["nat_h"] = h
    else:
        fs["nat_h"] = 0
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
        return merge_heals(ev), True
    if fm["on"] and f["race"] == "visored" and rng.random() < evb(f, "mask_rage", MASK_RAGE):  # the Hollow inside takes the wheel
        add_fx(f, "skip", 1)
        ev.append({"k": "mask_lost", "a": f["name"]})
    if fs["awake"] > 0 and f["hp"] < f["max_hp"] * GAUGE["hollow_hp"] and rng.random() < GAUGE["hollow_p"]:
        add_fx(f, "skip", 1)  # released and battered: the release slips out of control (its line depends on the race)
        ev.append({"k": "release_lost", "a": f["name"], "r": f.get("race")})
    skip = [x for x in f["fx"] if x["k"] == "skip"]
    if skip:
        f["fx"] = [e for e in f["fx"] if e["k"] != "skip"]
        ev.append({"k": "skip", "a": f["name"]})
        if _x(f)["charge"]:  # a stunned fighter loses the Cero they were gathering
            _x(f)["charge"] = 0
            ev.append({"k": "charge_break", "a": f["name"]})
        return merge_heals(ev), True
    state["awaiting"] = True
    return merge_heals(ev), False


def _check_end(state, ev=None):
    a, b = state["a"], state["b"]
    for f in (a, b):  # Konpaku (SENKA+): duels only; the soul is pulled back once
        if f["hp"] <= 0 and (state.get("pvp") or f.get("almighty")) and f.get("lives", 0) > 0:
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
            x["cd"] = int(evb(f, "sig_cd", c["cd"]))
            mult, pierce = (c["ai_mult"], c["ai_pierce"]) if f.get("ai") else (c["mult"], c["pierce"])
            mult *= evb(f, "cero_mult", 1.0) * evb(f, "sig_mult", 1.0)
            _deal(state, side, mult, rng, ev, "cero", allow_procs=True, extra_pierce=pierce)
        return
    f["re"] -= int(f["max_re"] * c["cost"])
    x["cd"] = int(evb(f, "sig_cd", c["cd"]))
    sm = evb(f, "sig_mult", 1.0)
    if sg == "shunpo":
        x["flash"] = 1
        ev.append({"k": "shunpo", "a": f["name"]})
    elif sg == "hiren":
        add_fx(f, "hiren", c["turns"])
        ev.append({"k": "hiren", "a": f["name"]})
        _deal(state, side, c["strike"] * sm, rng, ev, "blitz", allow_procs=False)  # arrives with a quick strike
    elif sg == "bring":
        _deal(state, side, c["mult"] * sm, rng, ev, "bring", allow_procs=True)
        if o["hp"] > 0 and rng.random() < evb(f, "bleed", c["bleed"]):
            add_fx(o, "bleed", DOT_TURNS["bleed"])
            ev.append({"k": "fx", "a": f["name"], "d": o["name"], "fx": "bleed"})
    elif sg == "soul":  # Soul Strike: a reiatsu strike (no bleed, no shield); own hit kind so it has its own text
        _deal(state, side, c["mult"] * sm, rng, ev, "soul", allow_procs=True)
    elif sg == "guts":  # Santen Kesshun: a shield that soaks the next hits
        n = max(1, int(f["max_hp"] * c["shield"]))
        f["shield"] += n
        ev.append({"k": "guts", "a": f["name"], "n": n})


CLEANSE = ("bleed", "burn", "poison", "fear", "weaken", "shock")


def _technique(state, side, slot, rng, ev):
    """A canon race technique (data_race_tech). Caller has already checked can(f, slot)."""
    f = state[side]
    o = state["b" if side == "a" else "a"]
    t = tech_of(f["race"], slot)
    x = _x(f)
    from data_racegear import TECH_LVL_STEP
    pw = 1 + TECH_LVL_STEP * int((f.get("tm") or {}).get(slot, 0))  # mastery from race technique cards
    rf = race_factor(f)  # shields, heals and buffs follow the race's own stat
    f["re"] -= int(f["max_re"] * t["cost"])
    x[slot + "cd"] = t["cd"]
    ev.append({"k": "tech", "a": f["name"], "d": o["name"], "id": t["id"]})
    kind = t["kind"]
    if kind == "strike":
        hits = int(t.get("hits", 1))
        for _ in range(hits):
            if o["hp"] <= 0:
                break
            hp0 = o["hp"]
            _deal(state, side, t["mult"] * pw, rng, ev, "tech", allow_procs=(hits == 1), extra_pierce=t.get("pierce", 0.0))
            if t.get("lifesteal") and o["hp"] < hp0:
                h = max(1, int((hp0 - o["hp"]) * t["lifesteal"]))
                f["hp"] = min(f["max_hp"], f["hp"] + h)
                ev.append({"k": "heal", "a": f["name"], "n": h})
        if t.get("fx") and o["hp"] > 0 and rng.random() < t.get("fx_p", 1.0):
            if t["fx"] == "skip":
                add_fx(o, "skip", 1)
                ev.append({"k": "fx", "a": f["name"], "d": o["name"], "fx": "stun"})
            else:
                add_fx(o, t["fx"], 3 if t["fx"] == "weaken" else DOT_TURNS.get(t["fx"], 3))
                ev.append({"k": "fx", "a": f["name"], "d": o["name"], "fx": t["fx"]})
    elif kind == "shield":
        n = max(1, int(f["max_hp"] * t["shield"] * pw * rf))
        f["shield"] += n
        ev.append({"k": "shield_t", "a": f["name"], "n": n})
    elif kind == "heal":
        n = max(1, int(f["max_hp"] * t["heal"] * pw * rf))
        f["hp"] = min(f["max_hp"], f["hp"] + n)
        if t.get("cleanse"):
            f["fx"] = [e for e in f["fx"] if e["k"] not in CLEANSE]
        ev.append({"k": "heal", "a": f["name"], "n": n})
    elif kind == "buff":
        turns = int(t.get("turns", 2)) + 1  # +1: the countdown ticks at the start of each own turn
        if t.get("guard"):
            x["gd_t"], x["gd_m"] = turns, max(0.3, 1 - (1 - t["guard"]) * pw * rf)
        if t.get("crit"):
            x["cb_t"], x["cb_v"] = turns, t["crit"] * pw * rf
        if t.get("dmg"):
            x["buff_t"], x["buff_m"] = turns, 1 + (t["dmg"] - 1) * pw * rf
    elif kind == "blur":
        add_fx(f, "hiren", int(t.get("turns", 2)))
        _deal(state, side, t["mult"] * pw, rng, ev, "tech", allow_procs=False)


def _do_action(state, action, rng, max_turns=30):
    side = state["cur"]
    f = state[side]
    ev = []
    if not can(f, action):
        action = "atk"
    if action == "atk":
        _deal(state, side, 1.0, rng, ev, "atk")
    elif action == "blv":  # Blut Vene: reinforced skin, a shield that soaks the next hits
        from data_bleachfx import BLUT
        c = BLUT["blut_vene"]
        f["re"] -= int(f["max_re"] * c["cost"])
        _x(f)["cd"] = c["cd"]
        n = max(1, int(f["max_hp"] * c["shield"] * evb(f, "blut", 1.0) * race_factor(f)))
        f["shield"] += n
        ev.append({"k": "blut_vene", "a": f["name"], "n": n})
    elif action == "bla":  # Blut Arterie: the blood runs through the blade, stronger strikes for a while
        from data_bleachfx import BLUT
        c = BLUT["blut_arterie"]
        f["re"] -= int(f["max_re"] * c["cost"])
        _x(f)["cd"] = c["cd"]
        _x(f)["buff_t"], _x(f)["buff_m"] = c["turns"] + 1, 1 + (c["mult"] - 1) * evb(f, "blut", 1.0)
        ev.append({"k": "blut_arterie", "a": f["name"]})
    elif action == "neg":  # Negación: the Hollow power field shields its bearer
        from data_bleachfx import NEGACION
        f["re"] -= int(f["max_re"] * NEGACION["cost"])
        _x(f)["cd"] = NEGACION["cd"]
        n = max(1, int(f["max_hp"] * NEGACION["shield"] * race_factor(f)))
        f["shield"] += n
        ev.append({"k": "negacion", "a": f["name"], "n": n})
    elif action == "gar":  # Garganta: a tunnel opens and the gap to the foe is the full range
        from data_bleachfx import GARGANTA
        f["re"] -= int(f["max_re"] * GARGANTA["cost"])
        _x(f)["cd"] = GARGANTA["cd"]
        state["dist"] = ZONE_MAX
        ev.append({"k": "garganta", "a": f["name"]})
    elif action == "bt":  # blade technique: pierce / bleed / twin / heavy, by the blade chosen
        t = f["bt"]
        f["re"] -= int(f["max_re"] * t["cost"])
        _x(f)["tcd"] = t["cd"]
        ev.append({"k": "bt", "a": f["name"], "kind": t["kind"]})
        if t["kind"] == "twin":
            _deal(state, side, t["mult"], rng, ev, "bt", allow_procs=True)
            if state["b" if side == "a" else "a"]["hp"] > 0:
                _deal(state, side, t["mult"], rng, ev, "bt", allow_procs=True)
        else:
            _deal(state, side, t["mult"], rng, ev, "bt", allow_procs=True, extra_pierce=t.get("pierce", 0.0))
            foe = state["b" if side == "a" else "a"]
            if t.get("bleed") and foe["hp"] > 0:
                add_fx(foe, "bleed", DOT_TURNS["bleed"])
                ev.append({"k": "fx", "a": f["name"], "d": foe["name"], "fx": "bleed"})
    elif action == "gs":  # general skill: guard (shield), strike (a blow) or focus (a damage buff)
        key = f["gen"]
        spec, pw = GENERAL_SKILLS[key], gen_power(f.get("race"), key)
        f["re"] -= int(f["max_re"] * spec["cost"])
        _x(f)["gcd"] = spec["cd"]
        if key == "guard":
            n = max(1, int(f["max_hp"] * spec["shield"] * pw))
            f["shield"] += n
            ev.append({"k": "gen", "a": f["name"], "skill": key, "n": n})
        elif key == "strike":
            ev.append({"k": "gen", "a": f["name"], "skill": key})
            _deal(state, side, spec["mult"] * pw, rng, ev, "gen", allow_procs=True)
        else:  # focus
            _x(f)["buff_t"], _x(f)["buff_m"] = spec["turns"] + 1, spec["buff"] * pw
            ev.append({"k": "gen", "a": f["name"], "skill": key})
    elif action == "bnt":  # Bount Seal: the souls bind the foe, who loses its next turn
        from data_gangs import BOUNT_SEAL
        foe = state["b" if side == "a" else "a"]
        f["re"] -= int(f["max_re"] * BOUNT_SEAL["re"])
        x = _x(f)
        x["cd"] = BOUNT_SEAL["cd"]
        x["bstack"] -= BOUNT_SEAL["stacks"]
        x["bseal"] += 1
        add_fx(foe, "skip", 1)
        ev.append({"k": "bount_seal", "a": f["name"], "d": foe["name"]})
    elif action == "bal":  # Bala: a hardened reiatsu bullet, piercing armour
        from data_bleachfx import BALA
        f["re"] -= int(f["max_re"] * BALA["cost"])
        _x(f)["cd"] = BALA["cd"]
        _deal(state, side, BALA["mult"], rng, ev, "atk", allow_procs=True, extra_pierce=BALA["pierce"], src="abl")
    elif action == "hvy":
        f["re"] -= int(f["max_re"] * 0.10)
        _deal(state, side, 1.6, rng, ev, "hvy")
        if f.get("mv") and (f["form"]["on"] or _x(f)["awake"] > 0) and ev and ev[-1].get("k") == "hit":
            ev[-1]["mv"] = f["mv"]  # released + known blade: the strike is called by its technique name
    elif action == "kd":
        n = best_kido(f, "had")
        P = KD.hado_params(n)
        f["re"] -= KD.cost("had", n, f["max_re"])
        if KD.spell_cd(n):
            _kcd(f)[KD.key("had", n)] = KD.spell_cd(n)
        o = state["b" if side == "a" else "a"]
        # hadō power: kidō stat and level set the base, the spell number scales it, the spell's own factor shapes it
        raw = (eff(f, "kido") * 0.9 + f["level"] * 1.0) * (0.7 + 0.3 * n) * f["mods"].get("kido", 1.0) * rng.uniform(0.9, 1.1) * P["mult"]
        chanted = bool(_x(f)["chant"])
        if chanted:  # the incantation is spent: full-power spell
            raw *= CHANT_HADO
            _x(f)["chant"] = 0
        else:        # no incantation: the high spells lose strength (and from 80 up cannot be cast at all, see kido_castable)
            raw *= KD.unchanted_mult(n)
        dmg = int(max(1, raw * _dmg_mult(f) * _zone(state, side) * _take_mult(o) - total_def(o) * 0.6 * (1 - P["pierce"])))  # pierce: part of the armour is ignored
        _apply(state, side, dmg, False, rng, ev, "hado", False)
        ev[-1]["chant"] = chanted
        ev[-1]["num"] = n
        ev[-1]["spell"] = KIDO_NAMES.get(("had", n), "")
        ev[-1]["short"] = (not chanted) and KD.unchanted_mult(n) < 1.0
        if o["hp"] > 0 and not state["done"]:
            if P["burn"]:
                add_fx(o, "burn", 3)
            if P["weaken"]:
                add_fx(o, "weaken", 3)
            if P["stun"] and rng.random() < P["stun"] * (0.5 if o.get("foe") == "boss" else 1.0):  # bosses shrug it off half as often
                add_fx(o, "skip", 1)
                ev.append({"k": "fx", "a": f["name"], "d": o["name"], "fx": "stun"})
    elif action == "bk":
        n = best_kido(f, "bak")
        P = KD.bakudo_params(n)
        f["re"] -= KD.cost("bak", n, f["max_re"])
        if KD.spell_cd(n):
            _kcd(f)[KD.key("bak", n)] = KD.spell_cd(n)
        gain = (eff(f, "kido") * (n / 10) * 2.5 + 10 + f["max_hp"] * 0.05) * P["shield"]
        if _x(f)["chant"]:
            gain *= CHANT_BAK
            _x(f)["chant"] = 0
        else:
            gain *= KD.unchanted_mult(n)
        f["shield"] += int(gain)
        ev.append({"k": "shield", "a": f["name"], "n": f["shield"], "num": n, "spell": KIDO_NAMES.get(("bak", n), "")})
        # the bind is the spell's own: Sai / Hainawa often, Rikujōkōrō always, Sajō Sabaku for two turns; the walls
        # (Enkōsen, Tozanshō, Danku) do not bind at all. Bosses resist half as well, so they can be bound but not chain-locked.
        o = state["b" if side == "a" else "a"]
        boss = o.get("foe") == "boss"
        if P["bind"] > 0 and rng.random() < P["bind"] * (0.5 if boss else 1.0):
            add_fx(o, "skip", 1 if boss else P["turns"])
            ev.append({"k": "fx", "a": f["name"], "d": o["name"], "fx": "stun"})
        if P["weaken"]:
            add_fx(o, "weaken", 3)
    elif action == "df":
        f["guard"] = True
        f["re"] = min(f["max_re"], f["re"] + int(f["max_re"] * GUARD_RE_GAIN))
        ev.append({"k": "guard", "a": f["name"]})
        if 0 < f["hp"] < f["max_hp"]:  # guarding also recovers HP, but replaces the natural recovery instead of stacking on it
            h = max(0, int(f["max_hp"] * GUARD_HP_GAIN) - int(_x(f).get("nat_h", 0)))
            if h > 0:
                f["hp"] = min(f["max_hp"], f["hp"] + h)
                ev.append({"k": "heal", "a": f["name"], "n": h})
    elif action == "gc":
        _x(f)["slash"] = 1
        _x(f)["open"] = 1
        ev.append({"k": "gather", "a": f["name"]})
    elif action == "gt":
        f["re"] -= int(f["max_re"] * GETSUGA_COST)
        _x(f)["slash"] = 0
        other = "b" if side == "a" else "a"
        o = state[other]
        if (state.get("ang") or {}).get(other):
            # the crescent wave flies through the space the target just left: step off the line and it misses
            ev.append({"k": "miss", "a": f["name"], "d": o["name"]})
        else:
            _deal(state, side, GETSUGA_DMG, rng, ev, "hvy", src="abl")
            if ev and ev[-1].get("k") == "hit":
                ev[-1]["gt"] = True
    elif action == "ch":  # Kidō chanting: the turn is spent speaking the incantation, and you stand open
        _x(f)["chant"] = 1
        _x(f)["open"] = 1
        ev.append({"k": "chant", "a": f["name"]})
    elif action == "sg":
        _signature(state, side, rng, ev)
    elif action in TECH_SLOTS:
        _technique(state, side, action, rng, ev)
    elif action == "gx":
        x = _x(f)
        f["re"] -= int(f["max_re"] * GAUGE["cost"])
        x["gauge"] = 0
        # +1: the countdown ticks at the start of each of your turns, so this covers `turns` actions (evolution adds more)
        x["awake"] = GAUGE["turns"] + int(evb(f, "release_turns", 0)) + 1
        ev.append({"k": "unleash", "a": f["name"], "mv": f.get("mv"), "r": f.get("race")})
        n = release_form(f)
        if n == 2:  # the release at a full gauge opens the race's form: Bankai / Full Resurrección / Letzt Stil ...
            c = FORM2.get(f["race"], FORM2["default"])
            f["form"].update(on=2, mult=c[0], left=c[1] + int(evb(f, "mask_turns", 0)), fat_turns=c[2], fat=0,
                             fx=list(FORM2_EFFECT.get(f["weapon"]["type"], ("pierce", 0.15))))
        elif n == 1:  # below FORM2_LEVEL: Shikai / Resurrección / Fullbring ...
            f["form"].update(on=1, mult=FORM1[0], left=FORM1[1] + int(evb(f, "mask_turns", 0)), fat_turns=FORM1[2], fat=0, fx=None)
        if n:
            f["form"]["used"][n - 1] = 1
            ev.append({"k": "form", "a": f["name"], "n": n, "r": f["race"]})
        _deal(state, side, GAUGE["strike"], rng, ev, "hvy", src="abl")  # arrives with the release: Bankai is an attack, not a pause
        if f.get("mv") and ev and ev[-1].get("k") == "hit":
            ev[-1]["mv"] = f["mv"]
    elif action == "f1":
        f["re"] -= int(f["max_re"] * FORM1[3])
        f["form"].update(on=1, mult=FORM1[0], left=FORM1[1] + int(evb(f, "mask_turns", 0)), fx=None, fat_turns=FORM1[2])
        f["form"]["used"][0] = 1
        ev.append({"k": "form", "a": f["name"], "n": 1, "r": f["race"]})
    elif action == "f2":
        c = FORM2.get(f["race"], FORM2["default"])
        f["re"] -= int(f["max_re"] * c[3])
        f["form"].update(on=2, mult=c[0], left=c[1] + int(evb(f, "mask_turns", 0)), fat_turns=c[2],
                         fx=list(FORM2_EFFECT.get(f["weapon"]["type"], ("pierce", 0.15))))
        f["form"]["used"][1] = 1
        ev.append({"k": "form", "a": f["name"], "n": 2, "r": f["race"]})
    _check_end(state, ev)
    if not state["done"]:
        advance(state, max_turns)
    else:
        state["awaiting"] = False
    state["last"] = ev
    return ev


def _parse_kido(f, action):
    """A picked spell comes as "kd:<number>" (Hadō) or "bk:<number>" (Bakudō): remember the pick for this turn and return
    the plain action. A bad number becomes a plain attack, like any action the fighter cannot do."""
    if isinstance(action, str) and action[:3] in ("kd:", "bk:"):
        try:
            n = int(action[3:])
        except ValueError:
            return "atk"
        _x(f)["pick"] = [action[:2], n]
        return action[:2]
    _x(f)["pick"] = None
    return action


def do_action(state, action, rng, max_turns=30):
    """Distance-aware action: movement, reach checks, auto-approach/back-off, knockback and sidestep."""
    side = state["cur"]
    f = state[side]
    o = state["b" if side == "a" else "a"]
    action = _parse_kido(f, action)  # "kd:31" / "bk:61": the player picked the spell
    state.setdefault("dist", START_DIST)  # a battle saved before the distance update carries no gap yet
    ang = state.setdefault("ang", {"a": 0, "b": 0})
    ang[side] = 0  # your stance ends when your turn starts; a sidestep below sets it again
    if action == "sd":
        if f["re"] < f["max_re"] * SIDESTEP["cost"]:
            return _finish(state, [{"k": "outrange", "a": f["name"]}], max_turns)
        f["re"] -= int(f["max_re"] * SIDESTEP["cost"])
        ang[side] = 1
        return _finish(state, [{"k": "side", "a": f["name"]}], max_turns)
    if action in MOVE_ACTIONS:
        return _finish(state, [_range_move(state, side, action)], max_turns)
    eff = action if can(f, action) else "atk"
    band = _band(f, eff)
    if band:
        lo, hi = band
        d = dist_of(state)
        if d > hi:  # out of reach: the turn closes the gap instead of striking
            _x(f)["pick"] = None  # the picked spell is not cast this turn: forget it
            return _finish(state, [_close_in(state, side, hi)], max_turns)
        if d < lo:  # too close for this weapon: the turn backs off
            _x(f)["pick"] = None
            return _finish(state, [apply_retreat(state, side)], max_turns)
    # a fighter who was just knocked back is not knocked again until they have struck back
    kbl = state.setdefault("kbl", {"a": False, "b": False})
    kbl[side] = False  # this fighter is striking now: their knock-lock ends
    # a heavy cannot be followed by another heavy: the blade must be re-set
    hp0 = o["hp"]
    # hv_last is read by can(f, "hvy") inside _do_action, so it must only be set after the strike
    ev = _do_action(state, action, rng, max_turns)
    _x(f)["pick"] = None
    _x(f)["hv_last"] = (eff == "hvy")
    dmg = hp0 - o["hp"]
    other = "b" if side == "a" else "a"
    if eff in PUSH_KIND and dmg > 0 and o["hp"] > 0 and not state["done"] and not kbl[other]:
        push = apply_knockback(state, other, PUSH_KIND[eff], dmg, o["max_hp"])
        if push:
            kbl[other] = True
            ev.append({"k": "knock", "a": f["name"], "d": o["name"], "n": push})
    return ev


NPC_RETREAT_LOW_HP = (0.35, 0.15)   # an NPC under 35% HP backs off one zone 15% of the time ...
NPC_RETREAT_RANGED = 0.25           # ... a ranged / Cero NPC at contact backs off 25% of the time to keep its distance
NPC_RETREAT_MAX_STREAK = 2          # never more than two retreats in a row
NPC_RETREAT_FROM_TURN = 3           # and never in the first two turns


def _npc_retreat(state, side, rng) -> bool:
    """Tactical retreat for NPCs (wild enemies and bosses): the player has to chase them with Shunpo / Sonido."""
    f = state[side]
    if not f.get("wild") or state.get("turn", 1) < NPC_RETREAT_FROM_TURN:
        return False
    if _x(f).get("rt_streak", 0) >= NPC_RETREAT_MAX_STREAK or dist_of(state) >= ZONE_MAX:
        return False
    if f["hp"] < f["max_hp"] * NPC_RETREAT_LOW_HP[0] and rng.random() < NPC_RETREAT_LOW_HP[1]:
        return True
    ranged = f.get("sig") == "cero" or (f.get("weapon") or {}).get("weapon_type") == "ranged"
    return ranged and dist_of(state) <= 1 and rng.random() < NPC_RETREAT_RANGED


def ai_choose(state, side, rng):
    act = "rt" if _npc_retreat(state, side, rng) else _ai_core(state, side, rng)
    x = _x(state[side])
    x["rt_streak"] = x.get("rt_streak", 0) + 1 if act == "rt" else 0
    return act


def _ai_core(state, side, rng):
    f = state[side]
    r = rng.random()
    sg = f.get("sig")
    if can(f, "gx") and r < 0.7:  # a full spirit gauge is almost always spent
        return "gx"
    if sg == "cero" and _x(f)["charge"] and r < 0.85:  # a gathered Cero is almost always fired
        return "sg"
    if f["hp"] < f["max_hp"] * 0.3 and r < 0.3:
        return "df"
    if not f.get("wild") and r < 0.30:  # a player-like fighter (duel stand-in, simulator) uses its race techniques
        ready = [s for s in TECH_SLOTS if can(f, s)]
        if ready:
            return rng.choice(ready)
    if sg and sg != "cero" and r < 0.22 and can(f, "sg") and not (sg == "guts" and f["shield"] > 0):
        return "sg"
    if sg == "cero" and r < 0.20 and can(f, "sg"):
        return "sg"
    band = _band(f, "atk")
    d = dist_of(state)
    if band and d > band[1] and r < 0.8:  # out of reach: close in
        return "mvs"
    if band and d < band[0]:  # ranged weapon at contact: back off
        return "rt"
    if d <= 1 and r < 0.12 and not (state.get("ang") or {}).get(side):  # sidestep out of an adjacent fight
        return "sd"
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
            "awaiting": False, "last": [], "intro": intro, "pvp": bool(pvp), "dist": START_DIST}


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
            events = events[:len(events) - len(ev)] + merge_heals(ev + do_action(state, ai_choose(state, state["cur"], rng), rng, max_turns))
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
