"""Canon moves: Quincy Blut and Arrancar Bala (engine level). Run: python -m unittest test_canon_moves -v"""
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine as E  # noqa: E402
from data_race_rules import race_allows  # noqa: E402

STATS = {"zanjutsu": 10, "kido": 5, "hakuda": 10, "hoho": 10, "reiatsu": 10}


def fighter(race, name="F"):
    return E.new_fighter(name, 20, dict(STATS), 200, 200, None, race=race)


def battle(race):
    a = fighter(race, "A")
    b = fighter("hollow", "B")
    st = E.new_state(a, b, random.Random(1))
    st["cur"] = "a"
    return st


class RaceGateTests(unittest.TestCase):
    def test_blut_is_quincy_only(self):
        self.assertTrue(race_allows("quincy", "blv"))
        self.assertTrue(race_allows("quincy", "bla"))
        for r in ("shinigami", "hollow", "arrancar", "fullbringer", "human", "visored"):
            self.assertFalse(race_allows(r, "blv"), r)
            self.assertFalse(race_allows(r, "bla"), r)

    def test_bala_is_arrancar_only(self):
        self.assertTrue(race_allows("arrancar", "bal"))
        for r in ("quincy", "hollow", "shinigami", "human"):
            self.assertFalse(race_allows(r, "bal"), r)


class BlutTests(unittest.TestCase):
    def test_vene_adds_a_shield_and_costs_reiatsu(self):
        st = battle("quincy")
        f = st["a"]
        re0, shield0 = f["re"], f["shield"]
        self.assertTrue(E.can(f, "blv"))
        E.do_action(st, "blv", random.Random(2))
        self.assertGreater(st["a"]["shield"], shield0)
        self.assertLess(st["a"]["re"], re0)

    def test_arterie_sets_a_timed_damage_buff(self):
        st = battle("quincy")
        E.do_action(st, "bla", random.Random(3))
        x = st["a"]["x"]
        self.assertGreater(x["buff_t"], 0)
        self.assertGreater(x["buff_m"], 1.0)

    def test_blut_shares_one_cooldown(self):
        st = battle("quincy")
        E.do_action(st, "blv", random.Random(4))
        self.assertGreater(st["a"]["x"]["cd"], 0)
        self.assertFalse(E.can(st["a"], "bla"))
        self.assertFalse(E.can(st["a"], "blv"))

    def test_no_reiatsu_means_no_blut(self):
        st = battle("quincy")
        st["a"]["re"] = 0
        self.assertFalse(E.can(st["a"], "blv"))
        self.assertFalse(E.can(st["a"], "bla"))


class BalaTests(unittest.TestCase):
    def test_bala_is_available_to_arrancar_only(self):
        self.assertTrue(E.can(battle("arrancar")["a"], "bal"))
        self.assertFalse(E.can(battle("quincy")["a"], "bal"))

    def test_bala_starts_a_short_cooldown(self):
        st = battle("arrancar")
        E.do_action(st, "bal", random.Random(5))
        self.assertGreater(st["a"]["x"]["cd"], 0)

    def test_bala_pierces_more_than_a_plain_strike(self):
        from data_bleachfx import BALA
        self.assertGreater(BALA["pierce"], 0)
        self.assertGreater(BALA["mult"], 1.0)


if __name__ == "__main__":
    unittest.main()
