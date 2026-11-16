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

def player(race):
    r = RACES[race]
    stats = {k: v + ALLOC for k, v in r["stats"].items()}
    mods = dict(r["mods"])
    kido = {"had": [1], "bak": [1]} if race in ("shinigami", "visored") else {"had": [], "bak": []}
    return E.new_fighter(race, LEVEL, stats, max_hp(LEVEL, soft_stat(stats["hakuda"]), mods.get("hp", 1.0)),
                         max_reiatsu(LEVEL, soft_stat(stats["reiatsu"])), dict(WEAPON), armor=ARMOR, mods=mods,
                         kido=kido, race=race, sig=sig_for(race))

def foe(scale, hollow):
    k, lvl = ENEMY_K, LEVEL
    s = (4 + lvl * k["s"]) * scale
    stats = {"zanjutsu": s, "kido": s * 0.6, "hakuda": (4 + lvl * k["d"]) * scale, "hoho": 6 + lvl * 0.5, "reiatsu": 5 + lvl}
    w = {"attack": (3 + lvl * k["a"]) * scale, "crit": 0.03, "element": "light", "skills": [], "weapon_type": "melee"}
    f = E.new_fighter("hollow" if hollow else "boss", lvl, stats, (k["h0"] + lvl * k["h1"]) * scale, 80 + lvl * 10, w,
                      armor=lvl * k["ar"] * scale, ai=True, sig=("cero" if hollow else None))
    f["foe"] = "hollow" if hollow else ("boss" if scale > 0.91 else "pve")
    return f

def run(n=300, seed=1):
    rng = random.Random(seed)
    pvp = {r: [0, 0] for r in RACE_LIST}
    for x in RACE_LIST:
        for y in RACE_LIST:
            if x == y:
                continue
            for _ in range(n):
                st = E.new_state(player(x), player(y), rng, pvp=True)
                E.run_ai(st, rng, ai_sides=("a", "b"))
                pvp[x][1] += 1
                if st["winner"] == "a":
                    pvp[x][0] += 1
    out = {"pvp": {r: round(100 * w / t, 1) for r, (w, t) in pvp.items()}}
    for name, scale, hollow in (("hollow", 0.9, True), ("boss", 0.92, False), ("pve", 0.9, False)):
        out[name] = {}
        for r in RACE_LIST:
            w = 0
            for _ in range(n * 3):
                st = E.new_state(player(r), foe(scale, hollow), rng, pvp=False)
                E.run_ai(st, rng, ai_sides=("a", "b"))
                w += st["winner"] == "a"
            out[name][r] = round(100 * w / (n * 3), 1)
    out["world_boss"] = {}
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
    out["world_boss"] = {r: round(100 * tot[r] / mean, 1) for r in RACE_LIST}  # relative damage per hit, 100 = average
    return out

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    for ctx, table in run(n).items():
        print(ctx, table)
