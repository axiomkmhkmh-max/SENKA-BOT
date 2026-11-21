"""Pure turn-based combat engine (no I/O). State is plain JSON-able dicts.

Fighters are 'a' and 'b'. Events are small dicts rendered later by battle_text.
"""
import math
import random

from data_misc import FORM1, FORM2, FORM2_EFFECT, FORM1_LEVEL, FORM2_LEVEL, KIDO_NAMES, MASK_RAGE, HP_MULT
from data_races import soft_stat
from data_race_rules import race_allows, fight_context, ctx_dmg_mult, GENERAL_SKILLS, gen_power
from data_race_tech import ABILITY_SHARE, ABILITY_STAT, FULLBRING_WEAPON, FULLBRING_LOW, HEAVY_REIATSU, TECH_SLOTS, tech_of
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
GUARD_HP_GAIN = 0.05   # share of the old-scale HP (_hb) a Guard turn gives back
TURN_HP_REGEN = 0.03   # share of the old-scale HP (_hb) recovered at the end of each turn (natural recovery)
MAX_TURNS = 200        # turn cap of a fight (was 30): HP is x6 now, so fights are long and epic
CRIT_ZAN = 0.004       # crit damage: 1.5 + 0.4% per effective Zanjutsu point (was 0.3%)
HAKUDA_DEF = 0.6       # defence per effective Hakuda point (was 0.5)
# Hohō (Nov 21): no extra turns; the faster fighter dodges more, by the ratio of the two speeds.
DODGE_BASE, DODGE_RATIO, DODGE_CAP, DODGE_CAP_ALL = 0.05, 0.25, 0.60, 0.75
SIDE_DMG, SIDE_HOHO = 0.5, 2.0  # side stance: your blows deal half, your Hohō counts double
BAKUDO_SHIELD = 3.0    # Bakudō barriers are three times as thick (Nov 21)


def _hb(f) -> float:
    """The fighter's HP on the old scale (before every HP became x HP_MULT): repeating heals, shields, regen and DoT
    are measured on it, so each use keeps its old size in a fight that is now HP_MULT times longer."""
    return f["max_hp"] / HP_MULT


def in_side(state, side) -> bool:
    return bool((state.get("ang") or {}).get(side))


def hoho_of(state, side) -> float:
    """Effective Hohō in this fight: the side stance doubles it."""
    return eff(state[side], "hoho") * (SIDE_HOHO if in_side(state, side) else 1.0) * max(0.2, 1 + bsum(state[side], "hoho"))


def dodge_chance(state, side) -> float:
    """Chance that the defender of a blow by `side` dodges it: 5% + 25% per step of speed ratio above 1, 5%..60%."""
    other = "b" if side == "a" else "a"
    ha, hd = max(1.0, hoho_of(state, side)), max(1.0, hoho_of(state, other))
    return min(DODGE_CAP, max(DODGE_BASE, DODGE_BASE + DODGE_RATIO * (hd / ha - 1)))

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
            "kcd": {}, "pick": None,
            # anti stun-lock: set right after a fighter loses a turn to a stun, cleared when they act again
            "stun_im": 0}


def _x(f):
    """Fighter's feel-state. Battles saved before this pack (or hand-built fighters) have none: create it lazily."""
    x = f.get("x")
    if x is None:
        x = f["x"] = _new_x()
    for k, v in _new_x().items():  # battles saved before a field existed get it with its default
        x.setdefault(k, v)
    return x


def add_fx(f, k, turns, stacks=1):
    if k == "skip" and (f.get("x") or {}).get("stun_im"):
        return  # just lost a turn: immune to being stunned again until they have acted (no chain-stun)
    for x in f["fx"]:
        if x["k"] == k:
            x["t"] = max(x["t"], turns)
            if k == "poison":
                x["s"] = min(3, x["s"] + stacks)
            return
    f["fx"].append({"k": k, "t": turns, "s": stacks})


def total_def(f):
    d = (eff(f, "hakuda") * HAKUDA_DEF + f["armor"]) * f["mods"].get("def", 1.0) * max(0.1, 1 + bsum(f, "def"))
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
    if x and (x.get("bf") or x.get("perm")):  # ability buffs (dmg +/-) and lasting bonuses (Shikai, Adjuchas, Full Mask)
        m *= max(0.1, 1 + bsum(att, "dmg") + float(x.get("perm", 0.0)))
    return m


def _take_mult(dfn):
    m = bred(dfn)  # Hierro, Total Rejection...
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
    if isinstance(src, dict):  # an ability type: its family's own stat mix (data_abilities), the weapon always counts
        mix = src.get("mix") or {}
        if "weapon" in mix:  # Fullbringer: the soul of the object
            lowb, lowl = FULLBRING_LOW
            wk = FULLBRING_WEAPON * (2.0 if src.get("wpn2") else 1.0)
            return (zpart + wk * w) * (1 + lowb * max(0.0, 1 - float(att.get("level", 1)) / lowl))
        part = 0.0
        for stat, wt in mix.items():
            if stat == "zanjutsu":
                part += wt * zpart
            else:
                v = eff(att, stat)
                if att["form"]["on"] and stat not in ("zanjutsu", "kido", "hakuda"):
                    v *= att["form"]["mult"]
                part += wt * v
        return part + w

    def power_of(stat):  # a form (mask, Shikai, Vollständig...) strengthens the race's ability stat too
        v = eff(att, stat)
        if att["form"]["on"] and stat not in ("zanjutsu", "kido", "hakuda"):  # eff() already scales those three
            v *= att["form"]["mult"]
        return v
    if src == "hvy":
        return (1 - HEAVY_REIATSU) * zpart + HEAVY_REIATSU * power_of("reiatsu") + w
    rs = ABILITY_STAT.get(att.get("race"))
    if rs == "weapon":
        lowb, lowl = FULLBRING_LOW
        return (zpart + FULLBRING_WEAPON * w) * (1 + lowb * max(0.0, 1 - float(att.get("level", 1)) / lowl))
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
    if kind != "bala" and _ab_defend(state, side, kind, rng, ev):  # Utsusemi, Schatten, Cero Doble...
        return 0
    tmp = (att.get("x") or {}).get("tmp") or {}
    dodge = dodge_chance(state, side) + bsum(dfn, "dodge")
    if has_fx(dfn, "hiren"):  # Hirenkyaku: a blur of speed
        dodge += SIG["hiren"]["dodge"]
    dodge = min(DODGE_CAP_ALL, dodge)
    if bhas(dfn, "nododge"):
        dodge = 0.0
    if kind == "bala":  # Bala: a 100% hit, whatever the speed or the blur
        dodge = 0.0
    amiss = bsum(att, "miss")  # Sakanade, a daze: the attacker's own blows go astray
    if amiss > 0 and kind not in ("bala", "counter") and rng.random() < min(0.75, amiss):
        ev.append({"k": "miss", "a": att["name"], "d": dfn["name"]})
        return 0
    if fx and fx[0] == "pierce":
        pass
    dfx = _f2fx(dfn)
    if dfx and dfx[0] == "miss" and kind != "bala" and rng.random() < dfx[1]:
        ev.append({"k": "miss", "a": att["name"], "d": dfn["name"]})
        return 0
    if rng.random() < dodge:
        ev.append({"k": "dodge", "a": att["name"], "d": dfn["name"]})
        return 0
    pierce = att["mods"].get("pierce", 0) + skill_p(att, "pierce") / 100 + (fx[1] if fx and fx[0] == "pierce" else 0) + extra_pierce + bsum(att, "pierce")
    defense = total_def(dfn) * (1 - min(0.8, pierce))
    base = strike_base(att, src or ("hvy" if kind == "hvy" else "abl" if kind not in ("atk", "echo") else "atk"))
    raw = max(1.0, base - defense * 0.6) * power
    crit_p = 0.05 + eff(att, "hoho") * 0.001 + att["weapon"]["crit"] + att["mods"].get("crit", 0) + (SIG["hiren"]["crit"] if has_fx(att, "hiren") else 0)
    if _x(att)["awake"] > 0:
        crit_p += GAUGE["crit"]
    if _x(att)["cb_t"] > 0:  # Pesquisa and other focus techniques
        crit_p += _x(att)["cb_v"]
    crit_p += bsum(att, "crit") + tmp.get("crit", 0.0)
    crit = rng.random() < crit_p
    cm = 1.5 + eff(att, "zanjutsu") * CRIT_ZAN + skill_p(att, "surge") / 100 + bsum(att, "cdmg") + tmp.get("cdmg", 0.0)
    zone = (SIDE_DMG if in_side(state, side) else 1.0) if tmp.get("any") else _zone(state, side)
    dmg = raw * (cm if crit else 1.0) * elem_mult(att, dfn) * rng.uniform(0.9, 1.1) * _dmg_mult(att) * zone * _foe_mult(att, dfn)
    if dfn["hp"] < dfn["max_hp"] * 0.5:
        dmg *= 1 + bsum(att, "lowfoe")
    dmg *= RACE_KILLER.get(att.get("race"), {}).get(dfn.get("race"), 1.0)  # canon race killers (SENKA+)
    dmg *= ctx_dmg_mult(att.get("race"), fight_context(state, dfn))  # balance by fight type (data_race_rules)
    ex = skill_p(att, "execute")
    if ex and dfn["hp"] < dfn["max_hp"] * 0.3:
        dmg *= 1 + ex / 100
    tm = _take_mult(dfn)
    if tmp.get("ng") and dfn["guard"]:  # Cero Oculto: the Guard does not soften it
        tm /= 0.5
    dmg *= tm
    return _apply(state, side, int(max(1, dmg)), crit, rng, ev, kind, allow_procs)


def _atk_reference(state, side) -> float:
    """What one plain attack of this fighter does to the foe on average (no crit, no dice): the same pieces as _deal."""
    att, dfn = state[side], state["b" if side == "a" else "a"]
    pierce = att["mods"].get("pierce", 0) + skill_p(att, "pierce") / 100
    raw = max(1.0, strike_base(att, "atk") - total_def(dfn) * (1 - min(0.8, pierce)) * 0.6)
    m = elem_mult(att, dfn) * _dmg_mult(att) * _zone(state, side) * _foe_mult(att, dfn)
    m *= RACE_KILLER.get(att.get("race"), {}).get(dfn.get("race"), 1.0)
    m *= ctx_dmg_mult(att.get("race"), fight_context(state, dfn))
    return raw * m * _take_mult(dfn)


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
        _gain(dfn, GAUGE["take"] + min(GAUGE["take_cap"], int(dmg / max(1, _hb(dfn)) * GAUGE["take_share"])), ev)
    _maybe_resolve(dfn, ev)
    dx = dfn.get("x")
    if dx and dmg > 0 and dfn["hp"] > 0 and kind not in ("reflect", "counter", "dot"):
        th = bsum(dfn, "thorns") if kind in PHYS_KINDS else 0.0
        rf = float(dx.get("refl") or 0.0)
        if rf:
            dx["refl"] = 0.0
        back = int(dmg * (th + rf))
        if back > 0:
            att["hp"] = max(0, att["hp"] - back)
            ev.append({"k": "reflect", "a": dfn["name"], "d": att["name"], "n": back})
        hh = bsum(dfn, "heal_hit")
        if hh > 0:
            h = max(1, int(_hb(dfn) * hh))
            dfn["hp"] = min(dfn["max_hp"], dfn["hp"] + h)
    if dx and any((dx.get("chg") or {}).values()) and dfn["hp"] > 0 and dmg >= _hb(dfn) * CERO_BREAK_PLAYER:
        dx["chg"] = {}  # a hard hit breaks a charging ability (Cero, Gran Rey, Schuss, La Muerte)
        ev.append({"k": "charge_break", "a": dfn["name"]})
    if dx and dx.get("charge") and dfn["hp"] > 0 and dmg >= _hb(dfn) * (CERO_BREAK_AI if dfn.get("ai") else CERO_BREAK_PLAYER):  # a hard hit interrupts the gathering Cero
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
    kp = (f.get("kpick") or {}).get(branch)
    if kp and kp in f["kido"][branch]:  # the spell the player put on this button before the fight (ability panel)
        return kp if kido_castable(f, branch, kp) else None
    ok = kido_list(f, branch)
    return ok[0] if ok else None


HADO_FLOOR = 1.0      # a Hadō never hits for less than this many plain attacks (chanted: x CHANT_HADO on top). 0 = off
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
    if f.get("ab") and (action in f["ab"] or action == "gt"):
        a, t = _ab(f, action)
        if not t:
            return None
        s = t["spec"]
        if not (s.get("m") or s.get("rand_m")) or s.get("anyrange") or s.get("dist") == "close" or s.get("charge") and not (_x(f).get("chg") or {}).get(action):
            return None  # buffs, heals, evades, charges and any-range blows ignore the gap
        if action == "gt":
            return lo, min(ZONE_MAX, hi + 2)
        if a["fam"] == "cero":
            return 0, ZONE_MAX
        if a["fam"] in ("arrow", "ginto", "lblade") and f["weapon"].get("type") == "ranged":
            return 0, min(ZONE_MAX, hi + 1)
        return lo, min(ZONE_MAX, hi + (1 if f["weapon"].get("type") == "ranged" else 0))
    if action == "if":
        return lo, hi
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
    stance = SIDE_DMG if in_side(state, side) else 1.0  # side stance: the striker's own blows are halved
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
    f["hoho_eff"] = round(hoho_of(state, side), 1)  # faster fighters move for less reiatsu (engine_range.move_cost)
    if not can_move(f, move, dist_of(state)):
        return {"k": "outrange", "a": f["name"]}
    return apply_move(state, side, move)


def _close_in(state, side, hi):
    """Out of reach: the turn is spent closing the gap (sonido for a long gap, shunpo otherwise)."""
    d = dist_of(state)
    long_gap = d - MOVES["shunpo"]["zones"] > hi
    state[side]["hoho_eff"] = round(hoho_of(state, side), 1)
    return _move(state, side, "sonido" if long_gap and can_move(state[side], "sonido", d) else "shunpo")


def _range_move(state, side, action):
    if action == "rt":
        if dist_of(state) >= ZONE_MAX:
            return {"k": "outrange", "a": state[side]["name"]}
        return apply_retreat(state, side)
    return _move(state, side, MOVE_ACTIONS[action])


def can(f, action, state=None):
    if action in ("atk", "df"):
        return True
    if not race_allows(f.get("race"), action):  # e.g. Arrancar cannot cast Kidō or release Bankai
        return False
    if f.get("ab"):  # a player's ability families (data_abilities)
        if action == "sk":
            return sk_can(f)
        if action == "if":
            return if_can(f)
        if action in ("sg", "t1", "t2", "t3") and action in f["ab"]:
            return ab_can(state, f, action)
        if action == "sg":
            return False  # every race's special button is a family now
        if action in TECH_SLOTS and bhas(f, "seal"):
            return False
        if action == "gc":  # Getsuga: gather only for the types that need it, and only once the blade is ready
            a, t = _ab(f, "gt")
            return bool(t) and bool(t["spec"].get("gather")) and _x(f)["slash"] <= 0 and not _x(f)["chant"] \
                and ab_can(state, f, "gt") and not bhas(f, "seal")
        if action == "gt":
            a, t = _ab(f, "gt")
            if not t or bhas(f, "seal"):
                return False
            if t["spec"].get("gather"):
                return _x(f)["slash"] > 0 and ab_can(state, f, "gt")
            return ab_can(state, f, "gt")
        if action in ("kd", "bk", "bal", "blv", "bla", "neg", "gar", "bt", "gs", "ch") and bhas(f, "seal"):
            return False
        if action == "bt" and not gate_ok(state or {"a": f, "b": f}, "a" if (state or {"a": f})["a"] is f else "b", "shikai"):
            return False  # the blade's own technique comes with Shikai
    if action in ("sk", "if"):
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
        if f.get("ab"):
            cost = c["cost"] * (1 - 0.02 * (int((f.get("abx") or {}).get("garg" if action == "gar" else "neg", 1)) - 1))
            return (_x(f).get("acd") or {}).get(action, 0) <= 0 and f["re"] >= f["max_re"] * cost
        return _x(f)["cd"] <= 0 and f["re"] >= f["max_re"] * c["cost"]
    if action == "bt":  # the blade's own technique (after Shikai): its own cost and cooldown
        return bool(f.get("bt")) and _x(f)["tcd"] <= 0 and f["re"] >= f["max_re"] * f["bt"]["cost"]
    if action == "gs":  # general skill chosen in the profile: any race, own cost and cooldown
        spec = GENERAL_SKILLS.get(f.get("gen"))
        return bool(spec) and _x(f)["gcd"] <= 0 and f["re"] >= f["max_re"] * spec["cost"]
    if action in ("blv", "bla", "bal"):  # Quincy Blut / Arrancar Bala: their own cost, sharing the special cooldown
        from data_bleachfx import BALA, BLUT
        c = BLUT["blut_vene"] if action == "blv" else BLUT["blut_arterie"] if action == "bla" else BALA
        if action == "bal" and f.get("ab") and bf_tag(f, "hierro"):  # with Hierro on, Bala has no cooldown
            return f["re"] >= f["max_re"] * c["cost"]
        if f.get("ab"):  # their own cooldown now (the special button has its own)
            return (_x(f).get("acd") or {}).get(action, 0) <= 0 and f["re"] >= f["max_re"] * c["cost"]
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
    bf_tick(state, side)  # ability buffs and debuffs this side cast lose a turn
    if fs.get("ifcd", 0) > 0:
        fs["ifcd"] -= 1
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
    if 0 < f["hp"] < f["max_hp"] and not bhas(f, "noregen"):  # natural recovery every turn (tunable: TURN_HP_REGEN)
        h = max(1, int(_hb(f) * TURN_HP_REGEN))
        f["hp"] = min(f["max_hp"], f["hp"] + h)
        ev.append({"k": "heal", "a": f["name"], "n": h})
        fs["nat_h"] = h
    else:
        fs["nat_h"] = 0
    rg = f["mods"].get("regen", 0)
    if rg and 0 < f["hp"] < f["max_hp"]:  # companion healing (pet role)
        h = max(1, int(_hb(f) * rg))
        f["hp"] = min(f["max_hp"], f["hp"] + h)
        ev.append({"k": "heal", "a": f["name"], "n": h})
    for x in list(f["fx"]):
        if x["k"] in DOT:
            d = max(1, int(_hb(f) * DOT[x["k"]] * (x["s"] if x["k"] == "poison" else 1)))
            f["hp"] = max(0, f["hp"] - d)
            ev.append({"k": "dot", "d": f["name"], "n": d, "fx": x["k"]})
        if x["k"] != "skip":
            x["t"] -= 1
    f["fx"] = [x for x in f["fx"] if x["t"] > 0 or x["k"] == "skip"]
    if f.get("ab"):
        _ab_turn_start(state, side, ev, rng)
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
    rage_p = 0.0 if fs.get("mfull") else evb(f, "mask_rage", MASK_RAGE) if fm["on"] else AB.MASK_STATE_RAGE if fs.get("sk") else 0.0
    if f["race"] == "visored" and rage_p and rng.random() < rage_p:  # the Hollow inside takes the wheel
        add_fx(f, "skip", 1)
        ev.append({"k": "mask_lost", "a": f["name"]})
    if fs["awake"] > 0 and f["hp"] < f["max_hp"] * GAUGE["hollow_hp"] and rng.random() < GAUGE["hollow_p"]:
        add_fx(f, "skip", 1)  # released and battered: the release slips out of control (its line depends on the race)
        ev.append({"k": "release_lost", "a": f["name"], "r": f.get("race")})
    skip = [x for x in f["fx"] if x["k"] == "skip"]
    if skip:
        f["fx"] = [e for e in f["fx"] if e["k"] != "skip"]
        ev.append({"k": "skip", "a": f["name"]})
        if _x(f)["charge"] or any((_x(f).get("chg") or {}).values()):  # a stunned fighter loses what they were gathering
            _x(f)["charge"] = 0
            _x(f)["chg"] = {}
            ev.append({"k": "charge_break", "a": f["name"]})
        fs["stun_im"] = 1  # the foe cannot stun this fighter again before they get to act
        return merge_heals(ev), True
    fs["stun_im"] = 0
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


def advance(state, max_turns=MAX_TURNS):
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
        n = max(1, int(_hb(f) * c["shield"]))
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
    if f.get("ab"):  # Bringer Light (a fixed Fullbringer ability): its own level from the ability panel
        pw = fixed_k(f, "blight")
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
        n = max(1, int(_hb(f) * t["shield"] * pw * rf))
        f["shield"] += n
        ev.append({"k": "shield_t", "a": f["name"], "n": n})
    elif kind == "heal":
        n = max(1, int(_hb(f) * t["heal"] * pw * rf))
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


def _do_action(state, action, rng, max_turns=MAX_TURNS):
    side = state["cur"]
    f = state[side]
    ev = []
    if not can(f, action, state):
        action = "atk"
    fab = f.get("ab") or {}
    acd = _x(f).setdefault("acd", {}) if fab else {}
    if action == "atk":
        _deal(state, side, 1.0, rng, ev, "atk")
    elif fab and action in fab and action in ("sg", "t1", "t2", "t3", "gt"):  # the picked type of this family (data_abilities)
        if action == "gt":
            _x(f)["slash"] = 0
        _ab_run(state, side, action, rng, ev)
    elif action == "sk":  # Shikai / Hollow Mask: one turn, then it holds for the whole fight
        sk_run(state, side, ev)
    elif action == "if":  # Iron Fist: Arrancar, only while Hierro holds
        if_run(state, side, rng, ev)
    elif action == "blv":  # Blut Vene: reinforced skin, a shield that soaks the next hits
        from data_bleachfx import BLUT
        c = BLUT["blut_vene"]
        f["re"] -= int(f["max_re"] * c["cost"])
        _x(f)["cd"] = c["cd"]
        n = max(1, int(_hb(f) * c["shield"] * evb(f, "blut", 1.0) * race_factor(f) * fixed_k(f, "vene")))
        if fab:
            acd["blv"], _x(f)["cd"] = c["cd"] + 1, 0
        f["shield"] += n
        ev.append({"k": "blut_vene", "a": f["name"], "n": n})
    elif action == "bla":  # Blut Arterie: the blood runs through the blade, stronger strikes for a while
        from data_bleachfx import BLUT
        c = BLUT["blut_arterie"]
        f["re"] -= int(f["max_re"] * c["cost"])
        _x(f)["cd"] = c["cd"]
        lv = int((f.get("abx") or {}).get("arterie", 1))
        _x(f)["buff_t"], _x(f)["buff_m"] = AB.lv_turns(c["turns"], lv) + 1, 1 + (c["mult"] - 1) * evb(f, "blut", 1.0) * AB.lv_k(lv)
        _x(f)["art"] = 1  # Blut Arterie holds: opens Sprenger and Gintō: Heizen
        if fab:
            acd["bla"], _x(f)["cd"] = c["cd"] + 1, 0
        ev.append({"k": "blut_arterie", "a": f["name"]})
    elif action == "neg":  # Negación: the Hollow power field shields its bearer
        from data_bleachfx import NEGACION
        f["re"] -= int(f["max_re"] * NEGACION["cost"])
        _x(f)["cd"] = NEGACION["cd"]
        n = max(1, int(_hb(f) * NEGACION["shield"] * race_factor(f) * fixed_k(f, "neg")))
        if fab:
            acd["neg"], _x(f)["cd"] = NEGACION["cd"] + 1, 0
        f["shield"] += n
        ev.append({"k": "negacion", "a": f["name"], "n": n})
    elif action == "gar":  # Garganta: a tunnel opens and the gap to the foe is the full range
        from data_bleachfx import GARGANTA
        lv = int((f.get("abx") or {}).get("garg", 1))
        f["re"] -= int(f["max_re"] * GARGANTA["cost"] * (1 - 0.02 * (lv - 1)))
        _x(f)["cd"] = GARGANTA["cd"]
        if fab:
            acd["gar"], _x(f)["cd"] = GARGANTA["cd"] + 1, 0
        state["dist"] = ZONE_MAX
        ev.append({"k": "garganta", "a": f["name"]})
    elif action == "bt":  # blade technique: pierce / bleed / twin / heavy, by the blade chosen
        t = f["bt"]
        f["re"] -= int(f["max_re"] * t["cost"])
        _x(f)["tcd"] = t["cd"]
        ev.append({"k": "bt", "a": f["name"], "kind": t["kind"]})
        bk = fixed_k(f, "blade")
        if t["kind"] == "twin":
            _deal(state, side, t["mult"] * bk, rng, ev, "bt", allow_procs=True)
            if state["b" if side == "a" else "a"]["hp"] > 0:
                _deal(state, side, t["mult"] * bk, rng, ev, "bt", allow_procs=True)
        else:
            _deal(state, side, t["mult"] * bk, rng, ev, "bt", allow_procs=True, extra_pierce=t.get("pierce", 0.0))
            foe = state["b" if side == "a" else "a"]
            if t.get("bleed") and foe["hp"] > 0:
                add_fx(foe, "bleed", DOT_TURNS["bleed"])
                ev.append({"k": "fx", "a": f["name"], "d": foe["name"], "fx": "bleed"})
    elif action == "gs":  # general skill: guard (shield), strike (a blow) or focus (a damage buff)
        key = f["gen"]
        spec, pw = GENERAL_SKILLS[key], gen_power(f.get("race"), key) * fixed_k(f, "gen")
        f["re"] -= int(f["max_re"] * spec["cost"])
        _x(f)["gcd"] = spec["cd"]
        if key == "guard":
            n = max(1, int(_hb(f) * spec["shield"] * pw))
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
        if fab:  # its own cooldown, none at all while Hierro holds
            acd["bal"] = 0 if bf_tag(f, "hierro") else BALA["cd"] + 1
            _deal(state, side, BALA["mult"] * fixed_k(f, "bala"), rng, ev, "bala", allow_procs=True, extra_pierce=BALA["pierce"],
                  src={"mix": {"reiatsu": 1.0}})
        else:
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
        raw = (eff(f, "kido") * 1.1 + f["level"] * 1.0) * (0.7 + 0.3 * n) * AB.lv_k(int((f.get("klv") or {}).get("had", 1))) * f["mods"].get("kido", 1.0) * rng.uniform(0.9, 1.1) * P["mult"]
        chanted = bool(_x(f)["chant"])
        if chanted:  # the incantation is spent: full-power spell
            raw *= CHANT_HADO
            _x(f)["chant"] = 0
        else:        # no incantation: the high spells lose strength (and from 80 up cannot be cast at all, see kido_castable)
            raw *= KD.unchanted_mult(n)
        dmg = int(max(1, raw * _dmg_mult(f) * _zone(state, side) * _take_mult(o) - total_def(o) * 0.6 * (1 - P["pierce"])))  # pierce: part of the armour is ignored
        if HADO_FLOOR > 0:  # armour comes off AFTER the multipliers, so a low spell (Shō) or a low Kidō stat hit weaker than a plain
            # attack even with the chant. Now a Hadō is never worse than an attack, and the chant keeps its x1.6 on top of that
            dmg = max(dmg, int(_atk_reference(state, side) * HADO_FLOOR * (CHANT_HADO if chanted else 1.0)))
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
        blv_ = int((f.get("klv") or {}).get("bak", 1))
        gain = (eff(f, "kido") * (n / 10) * 2.5 + 10 + _hb(f) * 0.05) * P["shield"] * BAKUDO_SHIELD * AB.lv_k(blv_)
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
        if P["bind"] > 0 and rng.random() < (P["bind"] + 0.01 * (blv_ - 1)) * (0.5 if boss else 1.0):
            add_fx(o, "skip", 1 if boss else P["turns"])
            ev.append({"k": "fx", "a": f["name"], "d": o["name"], "fx": "stun"})
        if P["weaken"]:
            add_fx(o, "weaken", 3)
    elif action == "df":
        f["guard"] = True
        f["re"] = min(f["max_re"], f["re"] + int(f["max_re"] * GUARD_RE_GAIN))
        ev.append({"k": "guard", "a": f["name"]})
        if 0 < f["hp"] < f["max_hp"]:  # guarding also recovers HP, but replaces the natural recovery instead of stacking on it
            h = max(0, int(_hb(f) * GUARD_HP_GAIN) - int(_x(f).get("nat_h", 0)))
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
        if True:  # Nov 21: the side stance no longer makes Getsuga miss (it doubles Hohō, so dodging does the work)
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
        rlv = int((f.get("abx") or {}).get("rel", 1))
        if n == 1 and fab and f.get("race") in ("shinigami", "visored"):
            n = 0  # Shikai / the Hollow Mask has its own button now: below Bankai level the release is the strike only
        if n == 2:  # the release at a full gauge opens the race's form: Bankai / Full Resurrección / Letzt Stil ...
            c = FORM2.get(f["race"], FORM2["default"])
            f["form"].update(on=2, mult=c[0] * (1 + 0.02 * (rlv - 1)), left=AB.lv_turns(c[1], rlv) + int(evb(f, "mask_turns", 0)),
                             fat_turns=c[2], fat=0, fx=list(FORM2_EFFECT.get(f["weapon"]["type"], ("pierce", 0.15))))
        elif n == 1:  # below FORM2_LEVEL: Shikai / Resurrección / Fullbring ...
            f["form"].update(on=1, mult=FORM1[0] * (1 + 0.02 * (rlv - 1)), left=AB.lv_turns(FORM1[1], rlv) + int(evb(f, "mask_turns", 0)),
                             fat_turns=FORM1[2], fat=0, fx=None)
        if n:
            f["form"]["used"][n - 1] = 1
            ev.append({"k": "form", "a": f["name"], "n": n, "r": f["race"]})
        _deal(state, side, GAUGE["strike"] * fixed_k(f, "rel"), rng, ev, "hvy", src="abl")  # arrives with the release: Bankai is an attack, not a pause
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


def do_action(state, action, rng, max_turns=MAX_TURNS):
    """Distance-aware action: movement, reach checks, auto-approach/back-off, knockback and sidestep."""
    side = state["cur"]
    f = state[side]
    o = state["b" if side == "a" else "a"]
    action = _parse_kido(f, action)  # "kd:31" / "bk:61": the player picked the spell
    state.setdefault("dist", START_DIST)  # a battle saved before the distance update carries no gap yet
    ang = state.setdefault("ang", {"a": 0, "b": 0})
    if action == "sd":  # side stance (Nov 21): a free toggle, once per turn, before acting; the turn is not spent
        return side_toggle(state, side)
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
        push = apply_knockback(state, other, PUSH_KIND[eff], dmg, _hb(o))
        if push:
            kbl[other] = True
            ev.append({"k": "knock", "a": f["name"], "d": o["name"], "n": push})
    return ev


def side_ok(state, side) -> bool:
    """The stance can be toggled once per turn; turning it on costs SIDESTEP['cost'] of max reiatsu."""
    f = state[side]
    if _x(f).get("sd_t") == state.get("turn"):
        return False
    return in_side(state, side) or f["re"] >= f["max_re"] * SIDESTEP["cost"]


def side_toggle(state, side):
    """Toggle the side stance without spending the turn: on = Hohō x2 and own damage x0.5, off = normal."""
    f = state[side]
    ang = state.setdefault("ang", {"a": 0, "b": 0})
    if not side_ok(state, side):
        return [{"k": "side_no", "a": f["name"]}]
    _x(f)["sd_t"] = state.get("turn")
    if ang.get(side):
        ang[side] = 0
        return [{"k": "side_off", "a": f["name"]}]
    f["re"] -= int(f["max_re"] * SIDESTEP["cost"])
    ang[side] = 1
    return [{"k": "side", "a": f["name"]}]


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


def _ai_ab(state, side, rng):
    """A player-like choice for fighters with ability families (duel shadows, the simulator, tournament stand-ins)."""
    f = state[side]
    r = rng.random()
    x = _x(f)
    if can(f, "sk", state) and r < 0.8:
        return "sk"
    for act, on in (x.get("chg") or {}).items():
        if on and r < 0.9:
            return act
    if can(f, "gx", state) and r < 0.7:
        return "gx"
    if f["hp"] < f["max_hp"] * 0.25 and r < 0.2:
        return "df"
    if can(f, "gt", state) and r < 0.6:
        return "gt"
    if can(f, "gc", state) and r < 0.35:
        return "gc"
    if can(f, "if", state) and r < 0.4:
        return "if"
    ready = []
    for act in ("sg", "t1", "t2", "t3", "bal", "blv", "bla", "neg", "bt", "gs"):
        if not can(f, act, state):
            continue
        a, t = _ab(f, act)
        if t:
            s = t["spec"]
            healer = (s.get("heal") or s.get("hot") or s.get("rewind")) and not (s.get("m") or s.get("rand_m"))
            if healer and f["hp"] > f["max_hp"] * 0.7:
                continue
            if s.get("buff") and any(b.get("t", 0) > 0 and b.get("o") == side for b in _bfl(f)) and not s.get("m"):
                continue
        ready.append(act)
    if ready and rng.random() < 0.5:
        return rng.choice(ready)
    if can(f, "bk", state) and rng.random() < 0.12:
        return "bk"
    return None


def _ai_core(state, side, rng):
    f = state[side]
    if f.get("ab") and not f.get("wild"):
        pick = _ai_ab(state, side, rng)
        if pick:
            return pick
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
    if side_ok(state, side):  # the side stance is a free toggle: on when hurt and outpaced, off again to hit hard
        on, low = in_side(state, side), f["hp"] < f["max_hp"] * 0.45
        if (not on and low and r < 0.25) or (on and (not low or r < 0.15)):
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
    # the speed line: who is faster and by how much, and what that means for dodging (dodge_chance)
    fast, slow = (a, b) if ea >= eb else (b, a)
    ratio = max(1.0, max(ea, eb)) / max(1.0, min(ea, eb))
    intro.append({"k": "speed", "a": fast["name"], "d": slow["name"], "r": round(ratio, 2),
                  "p": int(round(min(DODGE_CAP, DODGE_BASE + DODGE_RATIO * (ratio - 1)) * 100))})
    return {"a": a, "b": b, "turn": 1, "cur": first, "first": first, "done": False, "winner": None,
            "awaiting": False, "last": [], "intro": intro, "pvp": bool(pvp), "dist": START_DIST}


def run_ai(state, rng, max_turns=MAX_TURNS, ai_sides=("b",)):
    """Advance until a human must act or the fight ends. Returns events."""
    events = []
    guard = 0
    while not state["done"] and guard < 1000:
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
            act, pre = ai_choose(state, state["cur"], rng), []
            if act == "sd":  # the side stance is free: toggle it, then choose the real action of this turn
                pre = do_action(state, "sd", rng, max_turns)
                act = ai_choose(state, state["cur"], rng)
                if act == "sd":
                    act = "atk"
            events = events[:len(events) - len(ev)] + merge_heals(ev + pre + do_action(state, act, rng, max_turns))
        else:
            break
    return events


def hp_bar(cur, mx, n=10):
    k = 0 if mx <= 0 else max(0, min(n, math.ceil(n * cur / mx)))
    return "█" * k + "░" * (n - k)


def do_potion(state, kind, pct, max_turns=MAX_TURNS):
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


# ==== Ability families (Nov 21, data_abilities) ======================================================================
# A player's special buttons (sg, t1-t3, gt) fire the TYPE the player picked for that family before the fight
# (f["ab"][action] = {"fam", "tid", "lv"}). Fighters without "ab" (wild enemies, old saves, tournament kits) keep the old
# signature / race-technique code above. Buffs and debuffs of the types live in x["bf"]: each entry ticks down at the
# start of the turn of the side that cast it ("o"), so a 2-turn debuff covers two of the foe's turns.
import data_abilities as AB

PHYS_KINDS = ("atk", "hvy", "echo")   # blows a plain evade (Shunpo) can dodge; everything else is an ability


def _bfl(f):
    return _x(f).setdefault("bf", [])


def bsum(f, k) -> float:
    return sum(float(b.get(k, 0)) for b in (f.get("x") or {}).get("bf", []) if b.get("t", 0) > 0)


def bhas(f, k) -> bool:
    return any(b.get(k) for b in (f.get("x") or {}).get("bf", []) if b.get("t", 0) > 0)


def bred(f) -> float:
    """Damage-taken multiplier of the reduction buffs (Hierro, Total Rejection...): at most 90% less."""
    m = 1.0
    for b in (f.get("x") or {}).get("bf", []):
        if b.get("t", 0) > 0 and b.get("red"):
            m *= 1 - float(b["red"])
    return max(0.10, m)


def add_bf(f, d: dict, owner: str, tag: str = None):
    e = {k: v for k, v in d.items()}
    e["t"], e["o"] = int(d.get("t", 1)), owner
    if tag or d.get("tag"):
        e["tag"] = tag or d.get("tag")
    _bfl(f).append(e)


def bf_tick(state, side):
    """Start of `side`'s turn: every buff / debuff that side cast loses a turn (on both fighters)."""
    for s in ("a", "b"):
        x = state[s].get("x")
        if not x or not x.get("bf"):
            continue
        for b in x["bf"]:
            if b.get("o") == side:
                b["t"] -= 1
        x["bf"] = [b for b in x["bf"] if b["t"] > 0]


def bf_tag(f, tag) -> bool:
    return any(b.get("tag") == tag and b.get("t", 0) > 0 for b in (f.get("x") or {}).get("bf", []))


def released(f) -> bool:
    return bool(f["form"]["on"]) or _x(f).get("awake", 0) > 0


def gate_ok(state, side, gate) -> bool:
    f = state[side]
    if not gate:
        return True
    x = _x(f)
    if gate == "shikai":
        return bool(x.get("sk")) or f["form"]["on"] == 2
    if gate == "mask":
        return bool(x.get("sk")) or bool(f["form"]["on"])
    if gate == "bankai":
        return f["form"]["on"] == 2
    if gate == "hierro":
        return bf_tag(f, "hierro")
    if gate in ("rel", "res", "voll", "cfb", "awake"):
        return released(f)
    if gate == "arterie":
        return x.get("buff_t", 0) > 0 and bool(x.get("art"))
    if gate == "rage":
        return f["hp"] < f["max_hp"] * 0.5
    return False


def _ab(f, action):
    a = (f.get("ab") or {}).get(action)
    if not a:
        return None, None
    t = AB.type_of(a["fam"], a["tid"])
    return a, t


def fam_factor(f, mix: dict) -> float:
    """How strongly heals, shields and buffs of a family work: its stat mix against the fighter's average stat."""
    if not mix or "weapon" in mix or f.get("wild"):
        return 1.0
    mean = sum(eff(f, k) for k in ("zanjutsu", "kido", "hakuda", "hoho", "reiatsu")) / 5 or 1.0
    pw = sum(w * eff(f, k) for k, w in mix.items())
    return max(0.5, min(2.0, (1 - ABILITY_SHARE) + ABILITY_SHARE * pw / mean))


def ab_can(state_or_none, f, action) -> bool:
    """Can the picked type of this button fire now (gate, once, cooldown, cost, seal)?"""
    a, t = _ab(f, action)
    if not t:
        return False
    x = _x(f)
    if bhas(f, "seal"):
        return False
    if (x.get("chg") or {}).get(action):
        return True  # the charge is paid: firing is always possible
    gate = AB.gate_of(f.get("race"), a["fam"], t)
    if gate:
        st = state_or_none or {"a": f, "b": f}
        side = "a" if st["a"] is f else "b"
        if not gate_ok(st, side, gate):
            return False
    if t["spec"].get("once") and (a["fam"] + ":" + t["id"]) in (x.get("once") or []):
        return False
    if (x.get("acd") or {}).get(action, 0) > 0:
        return False
    s = t["spec"]
    if s.get("hpcost"):
        return f["hp"] > _hb(f) * s["hpcost"] + 1
    return f["re"] >= f["max_re"] * AB.lv_cost(t["cost"], a["lv"])


def _ab_pay(f, action, a, t):
    s, x = t["spec"], _x(f)
    if s.get("hpcost"):
        f["hp"] = max(1, f["hp"] - int(_hb(f) * s["hpcost"]))
    else:
        f["re"] -= int(f["max_re"] * AB.lv_cost(t["cost"], a["lv"]))
    cd = AB.lv_cd(t["cd"], a["lv"])
    if cd:
        x.setdefault("acd", {})[action] = cd + 1  # +1: ticks at the start of your next turn
    if s.get("once"):
        x.setdefault("once", []).append(a["fam"] + ":" + t["id"])


def _ab_fx(state, side, kind, turns, ev):
    f, o = state[side], state["b" if side == "a" else "a"]
    if kind == "skip":
        if o.get("foe") == "boss" and turns > 1:
            turns = 1
        add_fx(o, "skip", turns)
        ev.append({"k": "fx", "a": f["name"], "d": o["name"], "fx": "stun"})
    elif kind == "daze":
        add_bf(o, {"miss": 0.5, "t": turns}, side)
        ev.append({"k": "abfx", "a": f["name"], "d": o["name"], "fx": "daze"})
    elif kind in ("seal", "root", "noregen"):
        add_bf(o, {kind: 1, "t": turns}, side)
        ev.append({"k": "abfx", "a": f["name"], "d": o["name"], "fx": kind})
    else:
        add_fx(o, kind, turns)
        ev.append({"k": "fx", "a": f["name"], "d": o["name"], "fx": kind})


def _ab_run(state, side, action, rng, ev):
    f = state[side]
    other = "b" if side == "a" else "a"
    o = state[other]
    a, t = _ab(f, action)
    s, lv, x = t["spec"], int(a["lv"]), _x(f)
    k = AB.lv_k(lv)
    mix = AB.stat_mix(f.get("race"), a["fam"], t)
    chg = x.setdefault("chg", {})
    if s.get("charge") and not chg.get(action):  # first press: gather the power (telegraphed, breakable)
        _ab_pay(f, action, a, t)
        x.setdefault("acd", {})[action] = 0  # the cooldown starts when it fires
        chg[action] = 1
        ev.append({"k": "ab_charge", "a": f["name"], "fam": a["fam"], "tid": t["id"], "d": o["name"]})
        return
    if chg.get(action):
        chg[action] = 0
        cd = AB.lv_cd(t["cd"], lv)
        if cd:
            x.setdefault("acd", {})[action] = cd + 1
    else:
        _ab_pay(f, action, a, t)
    ev.append({"k": "ab", "a": f["name"], "d": o["name"], "fam": a["fam"], "tid": t["id"]})
    if s.get("shadow"):
        x["shadow"] = 2  # cleared at the start of your turn after next: the foe's next turn finds nothing
        return
    if s.get("dist") == "close":
        state["dist"] = 0
    elif s.get("dist") == "back2":
        state["dist"] = min(ZONE_MAX, dist_of(state) + 2)
    stk = x.setdefault("stk", {})
    key = a["fam"] + ":" + t["id"]
    m = s.get("m")
    if s.get("rand_m"):
        lo, hi = s["rand_m"]
        m = rng.uniform(lo, hi)
    if m:
        m *= k
        if s.get("rel_m") and released(f):
            m = s["rel_m"] * k
        if s.get("low_foe") and o["hp"] < o["max_hp"] * s["low_foe"][0]:
            m = s["low_foe"][1] * k
        if s.get("low_self") and f["hp"] < f["max_hp"] * s["low_self"][0]:
            m = s["low_self"][1] * k
        if s.get("stack"):
            m *= 1 + s["stack"][0] * k * min(stk.get(key, 0), s["stack"][1])
        hits = s.get("hits") or 1
        if s.get("hits_rand"):
            hits = rng.randint(*s["hits_rand"])
        src = {"mix": mix, "wpn2": bool(s.get("wpn2"))}
        hp0 = o["hp"]
        x["tmp"] = {"crit": AB.lv_p(s["crit_add"], lv) if s.get("crit_add") else 0.0, "cdmg": s.get("cdmg_add", 0) * k,
                    "ng": bool(s.get("noguard")), "any": bool(s.get("anyrange"))}
        last_crit = False
        for i in range(hits):
            if o["hp"] <= 0:
                break
            if s.get("miss_self") and rng.random() < s["miss_self"]:
                ev.append({"k": "miss", "a": f["name"], "d": o["name"]})
                continue
            n0 = len(ev)
            _deal(state, side, m, rng, ev, "tech", allow_procs=(i == 0), extra_pierce=s.get("pierce", 0.0) * k, src=src)
            last_crit = any(e.get("k") == "hit" and e.get("c") for e in ev[n0:])
        if s.get("combo") and last_crit and o["hp"] > 0:
            _deal(state, side, s["combo"] * k, rng, ev, "tech", allow_procs=False, src=src)
        x["tmp"] = None
        dealt = max(0, hp0 - o["hp"])
        if s.get("curhp") and o["hp"] > 0:
            extra = int(o["hp"] * s["curhp"] * k * (0.3 if o.get("foe") in ("boss", "world_boss") else 1.0))
            extra = min(extra, int(_hb(o) * 0.25))  # a share of the current HP, never a one-shot
            if extra > 0:
                _apply(state, side, extra, False, rng, ev, "tech", False)
                dealt += extra
        if s.get("ls") and dealt > 0:
            h = max(1, int(dealt * s["ls"] * k))
            f["hp"] = min(f["max_hp"], f["hp"] + h)
            ev.append({"k": "heal", "a": f["name"], "n": h})
        if s.get("recoil") and dealt > 0:
            r = max(1, int(dealt * s["recoil"]))
            f["hp"] = max(1, f["hp"] - r)
            ev.append({"k": "recoil", "a": f["name"], "n": r})
        if s.get("stack"):
            stk[key] = stk.get(key, 0) + 1
    if s.get("perm"):
        if x.get("perm_n", 0) < s["perm"][1]:
            x["perm_n"] = x.get("perm_n", 0) + 1
            x["perm"] = x.get("perm", 0.0) + s["perm"][0] * k
    if o["hp"] > 0 and not state.get("done"):
        if s.get("fx") and rng.random() < (AB.lv_p(s["fx_p"], lv) if s.get("fx_p") else 1.0):
            kind, n = s["fx"]
            _ab_fx(state, side, kind, n if kind in ("skip", "seal", "root", "daze") else AB.lv_turns(n, lv), ev)
        if s.get("steal_re"):
            st_ = min(o["re"], int(o["max_re"] * s["steal_re"] * k))
            o["re"] -= st_
            f["re"] = min(f["max_re"], f["re"] + st_)
            if st_:
                ev.append({"k": "drain", "a": f["name"], "d": o["name"], "n": st_})
        if s.get("brk") and o["shield"] > 0:
            o["shield"] = 0 if s["brk"] >= 1 else int(o["shield"] * (1 - s["brk"]))
            ev.append({"k": "abfx", "a": f["name"], "d": o["name"], "fx": "brk"})
        if s.get("debuff"):
            add_bf(o, AB.scaled_buff(s["debuff"], lv), side)
            ev.append({"k": "abfx", "a": f["name"], "d": o["name"], "fx": "debuff"})
        if s.get("dist") == "pull2":
            state["dist"] = max(0, dist_of(state) - 2)
        if s.get("copy"):
            mine = [b for b in _bfl(o) if any(b.get(q, 0) > 0 for q in ("dmg", "def", "hoho", "red", "crit", "dodge", "pierce"))]
            if mine:
                _x(o)["bf"] = [b for b in _bfl(o) if b not in mine]
                for b in mine:
                    b["o"] = side
                    _bfl(f).append(b)
                ev.append({"k": "abfx", "a": f["name"], "d": o["name"], "fx": "copy"})
        if s.get("trap"):
            x["trap"] = {"m": s["trap"] * k, "dist": dist_of(state), "mix": mix}
        if s.get("delay"):
            x["delay"] = {"t": s["delay"][0], "m": s["delay"][1] * k, "mix": mix}
    rf = fam_factor(f, mix)
    if s.get("heal"):
        h = max(1, int(_hb(f) * s["heal"] * k * rf))
        f["hp"] = min(f["max_hp"], f["hp"] + h)
        ev.append({"k": "heal", "a": f["name"], "n": h})
    if s.get("cleanse"):
        f["fx"] = [z for z in f["fx"] if z["k"] not in ("bleed", "burn", "poison", "fear", "weaken", "shock")]
    if s.get("shield"):
        n = max(1, int(_hb(f) * s["shield"] * k * rf))
        f["shield"] += n
        ev.append({"k": "shield_t", "a": f["name"], "n": n})
    if s.get("hot"):
        add_bf(f, {"hot": s["hot"][0] * k * rf, "t": AB.lv_turns(s["hot"][1], lv)}, side)
    if s.get("sot"):
        add_bf(f, {"sot": s["sot"][0] * k * rf, "t": AB.lv_turns(s["sot"][1], lv)}, side)
    if s.get("re"):
        f["re"] = min(f["max_re"], f["re"] + int(f["max_re"] * s["re"] * k))
    if s.get("buff"):
        b = AB.scaled_buff(s["buff"], lv)
        if f.get("race") == "arrancar" and s.get("arr"):
            b.update(AB.scaled_buff(s["arr"], lv))
        add_bf(f, b, side)
        if b.get("tag") == "hierro":
            ev.append({"k": "abfx", "a": f["name"], "d": o["name"], "fx": "hierro"})
    if s.get("evade"):
        e = dict(s["evade"])
        x["ev"] = {"n": int(e.get("n", 1)), "p": 1.0 if e["p"] >= 1 else AB.lv_p(e["p"], lv), "all": bool(e.get("all")),
                   "c": float(e.get("c", 0)) * k, "tt": 2 if e.get("n", 1) > 1 else 1}
    if s.get("reflect"):
        x["refl"] = s["reflect"] * k
    if s.get("absorb"):
        x["absorb"] = {"t": AB.lv_turns(s["absorb"][0], lv), "m": s["absorb"][1] * k, "mix": mix}
    if s.get("rewind"):
        hist = x.get("hph") or []
        if len(hist) >= 2 and hist[-2] > f["hp"]:
            h = hist[-2] - f["hp"]
            f["hp"] = min(f["max_hp"], hist[-2])
            ev.append({"k": "heal", "a": f["name"], "n": h})
    if s.get("mask_full"):
        x["mfull"] = 1
        x["perm"] = x.get("perm", 0.0) + 0.10
    if s.get("fatigue"):
        add_fx(f, "skip", int(s["fatigue"]))
    if s.get("after"):
        add_bf(f, dict(s["after"]), side)


def _ab_turn_start(state, side, ev, rng):
    """Start of `side`'s turn: hot / sot, drain, delayed blows, traps, absorb expiry, evade expiry, HP history."""
    f = state[side]
    x = _x(f)
    for b in list(_bfl(f)):
        if b.get("t", 0) <= 0:
            continue
        if b.get("hot") and 0 < f["hp"] < f["max_hp"]:
            h = max(1, int(_hb(f) * b["hot"]))
            f["hp"] = min(f["max_hp"], f["hp"] + h)
            ev.append({"k": "heal", "a": f["name"], "n": h})
        if b.get("sot"):
            f["shield"] += max(1, int(_hb(f) * b["sot"]))
        if b.get("drain_re"):
            f["re"] = max(0, f["re"] - int(f["max_re"] * b["drain_re"]))
    acd = x.get("acd") or {}
    for kk in list(acd):
        if acd[kk] > 0:
            acd[kk] -= 1
    if x.get("ev"):
        x["ev"]["tt"] = x["ev"].get("tt", 1) - 1
        if x["ev"]["tt"] <= 0:
            x["ev"] = None
    if x.get("shadow"):
        x["shadow"] -= 1
    x["refl_t"] = 0
    hist = x.setdefault("hph", [])
    hist.append(int(f["hp"]))
    del hist[:-3]
    d = x.get("delay")
    if d:
        d["t"] -= 1
        if d["t"] <= 0:
            x["delay"] = None
            ev.append({"k": "ab_late", "a": f["name"]})
            _deal(state, side, d["m"], rng, ev, "tech", allow_procs=False, src={"mix": d.get("mix") or {}})
    tr = x.get("trap")
    if tr:
        x["trap"] = None
        if dist_of(state) == tr["dist"]:
            ev.append({"k": "ab_trap", "a": f["name"]})
            _deal(state, side, tr["m"], rng, ev, "tech", allow_procs=False, src={"mix": tr.get("mix") or {}})
        else:
            ev.append({"k": "ab_trap_miss", "a": f["name"]})
    ab = x.get("absorb")
    if ab:
        ab["t"] -= 1
        if ab["t"] <= 0:
            x["absorb"] = None
            ev.append({"k": "ab_doble", "a": f["name"]})
            _deal(state, side, ab["m"], rng, ev, "tech", allow_procs=False, src={"mix": ab.get("mix") or {}})


def _ab_defend(state, side, kind, rng, ev) -> bool:
    """Before a blow of `side` lands: shadow, evade and absorb of the defender. True = the blow does not land."""
    att, dfn = state[side], state["b" if side == "a" else "a"]
    dx = dfn.get("x") or {}
    if dx.get("shadow", 0) > 0 and kind not in ("counter", "dot"):
        ev.append({"k": "ab_shadow", "a": dfn["name"], "d": att["name"]})
        return True
    e = dx.get("ev")
    if e and e.get("n", 0) > 0 and kind != "counter" and (kind in PHYS_KINDS or e.get("all")):
        e["n"] -= 1
        if e["n"] <= 0:
            dx["ev"] = None
        if rng.random() < e["p"]:
            ev.append({"k": "ab_evade", "a": dfn["name"], "d": att["name"]})
            if e.get("c"):
                _deal(state, "b" if side == "a" else "a", e["c"], rng, ev, "counter", allow_procs=False)
            return True
    ab = dx.get("absorb")
    if ab and kind not in PHYS_KINDS and kind not in ("counter", "dot"):
        dx["absorb"] = None
        ev.append({"k": "ab_doble", "a": dfn["name"], "d": att["name"]})
        _deal(state, "b" if side == "a" else "a", ab["m"] + 0.8, rng, ev, "tech", allow_procs=False, src={"mix": ab.get("mix") or {}})
        return True
    return False


SHIKAI_EVENTS = {"shinigami": "shikai", "visored": "mask_on"}


def sk_can(f) -> bool:
    if f.get("race") not in ("shinigami", "visored") or f.get("wild") or not f.get("ab"):
        return False
    return f["level"] >= AB.SHIKAI_LEVEL and not _x(f).get("sk") and f["re"] >= f["max_re"] * AB.SHIKAI_COST


def sk_run(state, side, ev):
    f = state[side]
    f["re"] -= int(f["max_re"] * AB.SHIKAI_COST)
    x = _x(f)
    x["sk"] = 1
    lv = int((f.get("abx") or {}).get("sk_shikai" if f["race"] == "shinigami" else "sk_mask", 1))
    x["perm"] = x.get("perm", 0.0) + AB.SHIKAI_DMG * AB.lv_k(lv)
    ev.append({"k": SHIKAI_EVENTS[f["race"]], "a": f["name"], "mv": f.get("mv")})


def if_can(f) -> bool:
    return f.get("race") == "arrancar" and bool(f.get("ab")) and bf_tag(f, "hierro") and _x(f).get("ifcd", 0) <= 0 \
        and f["re"] >= f["max_re"] * 0.08 and not bhas(f, "seal")


def if_run(state, side, rng, ev):
    f = state[side]
    f["re"] -= int(f["max_re"] * 0.08)
    _x(f)["ifcd"] = 3
    lv = int((f.get("abx") or {}).get("ironfist", 1))
    ev.append({"k": "ab", "a": f["name"], "d": state["b" if side == "a" else "a"]["name"], "fam": "ironfist", "tid": "ironfist"})
    _deal(state, side, 1.5 * AB.lv_k(lv), rng, ev, "tech", allow_procs=True, src={"mix": {"hakuda": 1.0}})


def fixed_k(f, fid) -> float:
    return AB.lv_k(int((f.get("abx") or {}).get(fid, 1)))
