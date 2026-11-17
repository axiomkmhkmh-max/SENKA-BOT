"""Race balance simulator. Run from the bot folder: python balance_sim.py [games_per_pair]
Pure logic, no database. Prints win rate per race for pvp duels, hollow foes and boss foes."""
import os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine as E
from data_races import RACES, soft_stat
from data_bleachfx import sig_for
import data_race_rules as RR

LEVEL, ALLOC = 40, 25
WEAPON = {"attack": 107, "crit": 0.05, "element": "light", "skills": [], "weapon_type": "melee"}
ARMOR = 20
RACE_LIST = ["shinigami", "quincy", "hollow", "arrancar", "fullbringer", "human", "visored"]
ENEMY_K = {"s": 1.6, "d": 1.2, "h0": 60, "h1": 30, "a": 2.6, "ar": 0.9}

def max_hp(level, hakuda, mult=1.0):
    return int((100 + level * 20 + hakuda * 8) * mult)

def max_reiatsu(level, reiatsu):
    return int(50 + level * 15 + reiatsu * 12)

# Standard Hadō list of a level-40 Shinigami / Visored. Balance of the kidō races depends heavily on this choice.
STD_HADO = (1, 4)
KD_CHANCE = 0.4   # a human player casts a Hadō on roughly this share of turns when one is available


def _player_policy():
    """Players pick their own actions; the production AI almost never casts Hadō, so the simulator makes a player-like choice."""
    base = E.ai_choose

    def choose(state, side, rng):
        f = state[side]
        if not f.get("ai") and E.can(f, "kd") and rng.random() < KD_CHANCE:
            return "kd"
        return base(state, side, rng)
    E.ai_choose = choose


_player_policy()

# Standard loadout: everyone has the general Strike skill; Shinigami and Visored also have Zangetsu's blade technique.
# Hyorinmaru (owner-only) is not part of the standard loadout.
def loadout(race):
    from data_zanpakuto import blade_technique
    return {"gen": "strike", "bt": blade_technique("zangetsu") if race in ("shinigami", "visored") else None}

EVO_STAGE = 2   # a level-40 player is at about the third evolution stage (level gate 35)


def player(race):
    from data_evolution import evo_bonus
    r = RACES[race]
    stats = {k: v + ALLOC for k, v in r["stats"].items()}
    mods = dict(r["mods"])
    evb = evo_bonus(race, EVO_STAGE)  # same split as service_combat.build_player
    for key in ("dmg", "def", "hp", "kido"):
        if evb.get(key):
            mods[key] = mods.get(key, 1.0) * (1 + evb[key])
    for key in ("crit", "pierce"):
        if evb.get(key):
            mods[key] = mods.get(key, 0.0) + evb[key]
    mods["regen"] = evb.get("regen", 0.0)
    kido = {"had": list(STD_HADO), "bak": [1]} if race in ("shinigami", "visored") else {"had": [], "bak": []}
    f = E.new_fighter(race, LEVEL, stats, max_hp(LEVEL, soft_stat(stats["hakuda"]), mods.get("hp", 1.0)),
                      max_reiatsu(LEVEL, soft_stat(stats["reiatsu"])), dict(WEAPON), armor=ARMOR, mods=mods,
                      kido=kido, race=race, sig=sig_for(race), **loadout(race))
    f["evo"] = {k: v for k, v in evb.items() if k not in ("dmg", "def", "hp", "kido", "crit", "pierce", "regen")}
    f["evs"] = EVO_STAGE
    return f

def foe(scale, hollow):
    k, lvl = ENEMY_K, LEVEL
    s = (4 + lvl * k["s"]) * scale
    stats = {"zanjutsu": s, "kido": s * 0.6, "hakuda": (4 + lvl * k["d"]) * scale, "hoho": 6 + lvl * 0.5, "reiatsu": 5 + lvl}
    w = {"attack": (3 + lvl * k["a"]) * scale, "crit": 0.03, "element": "light", "skills": [], "weapon_type": "melee"}
    f = E.new_fighter("hollow" if hollow else "boss", lvl, stats, (k["h0"] + lvl * k["h1"]) * scale, 80 + lvl * 10, w,
                      armor=lvl * k["ar"] * scale, ai=True, sig=("cero" if hollow else None))
    f["foe"] = "hollow" if hollow else ("boss" if scale > 0.91 else "pve")
    f["wild"] = True
    return f

def pvp_rates(n, rng):
    pvp = {r: [0, 0] for r in RACE_LIST}
    for x in RACE_LIST:
        for y in RACE_LIST:
            if x == y:
                continue
            for _ in range(n):
                st = E.new_state(player(x), player(y), rng, pvp=True)
                E.run_ai(st, rng, ai_sides=("a", "b"))
                pvp[x][1] += 1
                pvp[x][0] += st["winner"] == "a"
    return {r: round(100 * w / t, 1) for r, (w, t) in pvp.items()}

def foe_rates(scale, hollow, n, rng):
    out = {}
    for r in RACE_LIST:
        w = 0
        for _ in range(n * 3):
            st = E.new_state(player(r), foe(scale, hollow), rng, pvp=False)
            E.run_ai(st, rng, ai_sides=("a", "b"))
            w += st["winner"] == "a"
        out[r] = round(100 * w / (n * 3), 1)
    return out

FOES = (("hollow", 0.9, True), ("boss", 0.92, False), ("pve", 0.9, False))

def world_boss_rel(n, rng):
    tot = {}
    for r in RACE_LIST:
        d = 0
        for _ in range(n):
            a = player(r)
            boss = E.new_fighter("Boss", LEVEL, {"zanjutsu": 1, "kido": 1, "hakuda": 120, "hoho": 1, "reiatsu": 1}, 10 ** 9, 100,
                                 {"attack": 1, "element": "light", "skills": [], "weapon_type": "melee"}, armor=0)
            boss["foe"] = "world_boss"
            st = {"a": a, "b": boss, "turn": 1, "cur": "a", "first": "a", "done": False, "winner": None, "dist": 2}
            ev = []
            E._deal(st, "a", 1.0, rng, ev, "atk")
            d += sum(e.get("n", 0) for e in ev if e["k"] == "hit")
        tot[r] = d / n
    mean = sum(tot.values()) / len(tot)
    return {r: round(100 * tot[r] / mean, 1) for r in RACE_LIST}  # relative damage per hit, 100 = average

def run(n=300, seed=1):
    rng = random.Random(seed)
    out = {"pvp": pvp_rates(n, rng)}
    for name, scale, hollow in FOES:
        out[name] = foe_rates(scale, hollow, n, rng)
    out["world_boss"] = world_boss_rel(n, rng)
    return out

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    for ctx, table in run(n).items():
        print(ctx, table)
