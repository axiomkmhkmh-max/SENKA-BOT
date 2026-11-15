"""Hollow Negación and Garganta, and the Visored Cero signature (engine level).
Run: python -m unittest test_hollow_moves -v"""
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine as E  # noqa: E402
from data_bleachfx import RACE_SIG  # noqa: E402
from data_race_rules import race_allows  # noqa: E402
from engine_range import ZONE_MAX  # noqa: E402

STATS = {"zanjutsu": 10, "kido": 5, "hakuda": 10, "hoho": 10, "reiatsu": 10}


def battle(race):
    a = E.new_fighter("A", 20, dict(STATS), 200, 200, None, race=race)
    b = E.new_fighter("B", 20, dict(STATS), 200, 200, None, race="human")
    st = E.new_state(a, b, random.Random(1))
    st["cur"] = "a"
    return st


class GateTests(unittest.TestCase):
    def test_negacion_is_hollow_only(self):
        self.assertTrue(race_allows("hollow", "neg"))
        for r in ("arrancar", "shinigami", "quincy", "fullbringer", "human", "visored"):
            self.assertFalse(race_allows(r, "neg"), r)

    def test_garganta_is_hollow_and_arrancar(self):
        self.assertTrue(race_allows("hollow", "gar"))
        self.assertTrue(race_allows("arrancar", "gar"))
        for r in ("shinigami", "quincy", "fullbringer", "human", "visored"):
            self.assertFalse(race_allows(r, "gar"), r)


class NegacionTests(unittest.TestCase):
    def test_negacion_shields_and_costs_reiatsu(self):
        st = battle("hollow")
        re0, sh0 = st["a"]["re"], st["a"]["shield"]
        self.assertTrue(E.can(st["a"], "neg"))
        E.do_action(st, "neg", random.Random(2))
        self.assertGreater(st["a"]["shield"], sh0)
        self.assertLess(st["a"]["re"], re0)

    def test_negacion_sets_cooldown(self):
        st = battle("hollow")
        E.do_action(st, "neg", random.Random(3))
        self.assertGreater(st["a"]["x"]["cd"], 0)


class GargantaTests(unittest.TestCase):
    def test_garganta_opens_the_full_gap(self):
        st = battle("hollow")
        st["dist"] = 0
        E.do_action(st, "gar", random.Random(4))
        self.assertEqual(st["dist"], ZONE_MAX)

    def test_garganta_costs_reiatsu_and_sets_cooldown(self):
        st = battle("arrancar")
        re0 = st["a"]["re"]
        E.do_action(st, "gar", random.Random(5))
        self.assertLess(st["a"]["re"], re0)
        self.assertGreater(st["a"]["x"]["cd"], 0)


class VisoredSignatureTests(unittest.TestCase):
    def test_visored_signature_is_cero_not_shunpo(self):
        self.assertEqual(RACE_SIG["visored"], "cero")
        self.assertEqual(RACE_SIG["shinigami"], "shunpo")

    def test_visored_sig_is_available_as_cero(self):
        # production sets the signature with sig_for(race) in service_combat.build_player
        from data_bleachfx import sig_for
        a = E.new_fighter("A", 20, dict(STATS), 200, 200, None, race="visored", sig=sig_for("visored"))
        b = E.new_fighter("B", 20, dict(STATS), 200, 200, None, race="human")
        st = E.new_state(a, b, random.Random(1))
        self.assertEqual(st["a"]["sig"], "cero")
        self.assertTrue(E.can(st["a"], "sg"))


if __name__ == "__main__":
    unittest.main()
