"""Duel rules (DUEL in data_misc): hit cap, hit floor, multiplier caps, flat release price, one release, release lock.
Pure engine tests, no database. Run: python -m unittest test_duel_rules -v"""
import os, random, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine as E
from data_misc import DUEL

W = {"attack": 100, "crit": 0.0, "element": "light", "skills": [], "weapon_type": "melee"}


def fighter(name, level, zan, hakuda, hp=None, re=3000, race="shinigami"):
    stats = {"zanjutsu": zan, "kido": 5, "hakuda": hakuda, "hoho": 20, "reiatsu": 20}
    return E.new_fighter(name, level, stats, hp or (100 + level * 20 + hakuda * 60), re, W, race=race)


def state(a, b, **kw):
    return E.new_state(a, b, random.Random(1), **kw)


class Rules(unittest.TestCase):
    def test_no_one_shot(self):
        for seed in range(30):
            strong, weak = fighter("S", 100, 4000, 500, 20000), fighter("W", 40, 50, 20, 3000)
            st = E.new_state(strong, weak, random.Random(seed), pvp=True)
            ev = []
            E._deal(st, "a", 5.0, random.Random(seed), ev)
            self.assertGreaterEqual(weak["hp"], weak["max_hp"] * (1 - DUEL["hit_cap"]) - 1)

    def test_floor_follows_attacker_power_not_target_hp(self):
        weak, strong, tank = fighter("W", 40, 60, 5, 3000), fighter("S", 100, 4000, 500, 20000), fighter("T", 100, 100, 3000, 60000)
        tank["armor"] = 5000
        def avg(att, dfn, rules):
            tot = 0
            for seed in range(40):
                a, d = dict(att), dict(dfn)
                import copy
                a, d = copy.deepcopy(att), copy.deepcopy(dfn)
                st = E.new_state(a, d, random.Random(seed), pvp=True, duel_rules=rules)
                st["dist"] = 0
                ev = []
                E._deal(st, "a", 1.0, random.Random(seed), ev, "atk")
                tot += sum(e.get("n", 0) for e in ev if e["k"] == "hit")
            return tot / 40
        on, off = avg(weak, tank, True), avg(weak, tank, False)
        self.assertGreater(on, off)                      # the floor lifts a weak hitter against heavy armour
        self.assertGreater(avg(strong, tank, True), on)  # ... but a stronger hitter still hits harder (no flattening)

    def test_rules_off_outside_duels(self):
        a, b = fighter("A", 100, 4000, 500, 20000), fighter("B", 40, 50, 20, 3000)
        st = E.new_state(a, b, random.Random(1), pvp=False)
        self.assertFalse(st["duel"] or a.get("duel"))
        st = E.new_state(*[fighter("A", 50, 100, 50), fighter("B", 50, 100, 50)], random.Random(1), pvp=True, duel_rules=False)
        self.assertFalse(st["duel"])

    def test_boss_and_wild_never_get_duel_rules(self):
        a, b = fighter("A", 50, 100, 50), fighter("B", 50, 100, 50)
        b["foe"], b["wild"] = "boss", True
        E.new_state(a, b, random.Random(1), pvp=True)
        self.assertTrue(a["duel"])
        self.assertFalse(b["duel"])

    def test_form_cap(self):
        a, b = fighter("A", 50, 100, 50), fighter("B", 50, 100, 50)
        E.new_state(a, b, random.Random(1), pvp=True)
        base = E.eff(a, "zanjutsu")
        a["form"].update(on=2, mult=3.0)
        self.assertAlmostEqual(E.eff(a, "zanjutsu"), base * DUEL["form_cap"], places=4)
        b["duel"] = False
        b["form"].update(on=2, mult=3.0)
        self.assertAlmostEqual(E.eff(b, "zanjutsu"), E.soft_stat(100) * 3.0, places=4)

    def test_mult_cap(self):
        a, b = fighter("A", 50, 100, 50), fighter("B", 50, 100, 50)
        E.new_state(a, b, random.Random(1), pvp=True)
        a["x"]["buff_t"], a["x"]["buff_m"], a["x"]["awake"] = 3, 2.0, 3
        a["x"]["perm"] = 2.0
        self.assertLessEqual(E._dmg_mult(a), a["dmgx"] * DUEL["mult_cap"] + 1e-9)
        a["duel"] = False
        self.assertGreater(E._dmg_mult(a), a["dmgx"] * DUEL["mult_cap"])

    def test_release_price_flat_and_capped(self):
        big, small = fighter("B", 80, 100, 50, re=20000), fighter("S", 20, 100, 50, re=900)
        E.new_state(big, small, random.Random(1), pvp=True)
        self.assertEqual(E.gx_cost(big), 2000)        # 10% pool is above the flat price
        big["max_re"] = 5000
        self.assertEqual(E.gx_cost(big), 1000)        # flat price
        self.assertEqual(E.gx_cost(small), 315)       # 35% pool cap
        small["duel"] = False
        self.assertEqual(E.gx_cost(small), 90)        # outside duels: normal 10%

    def test_one_release_and_lock(self):
        a, b = fighter("A", 60, 300, 100, re=9000), fighter("B", 60, 300, 100, re=9000)
        st = E.new_state(a, b, random.Random(3), pvp=True, )
        st["cur"] = "a"
        a["x"]["gauge"] = 100
        self.assertTrue(E.can(a, "gx", st))
        E.do_action(st, "gx", random.Random(3))
        self.assertEqual(a["dl_rel"], 1)
        self.assertEqual(a["x"]["awake"] > 0 or a["x"]["awake"] == 0, True)
        a["x"]["gauge"], a["x"]["awake"] = 100, 0
        self.assertFalse(E.can(a, "gx", st))          # second release in the same duel
        a["x"]["awake"] = 2
        for act in E.DUEL_RELEASE_LOCK:
            self.assertFalse(E.can(a, act, st), act)  # locked while released

    def test_full_duel_runs_and_ends(self):
        for seed in range(10):
            a, b = fighter("A", 100, 3000, 400, 20000), fighter("B", 40, 300, 80, 4000)
            st = E.new_state(a, b, random.Random(seed), pvp=True)
            E.run_ai(st, random.Random(seed), ai_sides=("a", "b"))
            self.assertTrue(st["done"])


if __name__ == "__main__":
    unittest.main()


class ShieldCap(unittest.TestCase):
    def test_shield_capped_in_duel(self):
        a, b = fighter("A", 50, 100, 50, 10000), fighter("B", 50, 100, 50, 10000)
        E.new_state(a, b, random.Random(1), pvp=True)
        E._shield_add(a, 10 ** 7)
        self.assertEqual(a["shield"], int(a["max_hp"] * DUEL["shield_cap"]))
        E._shield_add(a, 5000)
        self.assertEqual(a["shield"], int(a["max_hp"] * DUEL["shield_cap"]))
        b["duel"] = False
        E._shield_add(b, 10 ** 7)
        self.assertEqual(b["shield"], 10 ** 7)
