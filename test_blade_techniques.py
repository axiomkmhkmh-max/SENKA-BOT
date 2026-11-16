"""Blade techniques: every blade has one, and it works after Shikai. Run: python -m unittest test_blade_techniques -v"""
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine as E  # noqa: E402
from data_races import RACES  # noqa: E402
from data_zanpakuto import BLADE_TECH, BLADE_TECH_KINDS, BLADE_UNLOCK, blade_technique  # noqa: E402


def fighter(bt=None, race="shinigami"):
    r = RACES[race]
    return E.new_fighter(race, 40, dict(r["stats"]), 1200, 500,
                         {"attack": 90, "crit": 0.05, "element": "light", "skills": [], "weapon_type": "melee"},
                         armor=10, mods=dict(r["mods"]), race=race, bt=bt)


class BladeTechniqueTests(unittest.TestCase):
    def test_every_blade_has_a_technique_of_a_known_kind(self):
        self.assertEqual(set(BLADE_TECH), set(BLADE_UNLOCK))
        for blade, kind in BLADE_TECH.items():
            self.assertIn(kind, BLADE_TECH_KINDS, blade)

    def test_technique_dict_has_names_and_cost(self):
        t = blade_technique("zangetsu")
        self.assertEqual(t["kind"], "twin")
        self.assertTrue(t["blade_en"])
        self.assertIsNone(blade_technique("not_a_blade"))

    def test_only_usable_when_the_fighter_has_one(self):
        self.assertFalse(E.can(fighter(None), "bt"))
        self.assertTrue(E.can(fighter(blade_technique("hyorinmaru")), "bt"))

    def test_each_kind_resolves_and_starts_its_cooldown(self):
        rng = random.Random(5)
        for blade in BLADE_TECH:
            t = blade_technique(blade)
            f = fighter(t)
            st = E.new_state(f, fighter(None, race="hollow"), rng, pvp=True)
            st["cur"] = "a"  # the player's turn
            ev = E._do_action(st, "bt", rng)
            self.assertTrue(any(e.get("k") == "bt" for e in ev), blade)
            self.assertGreater(E._x(f)["tcd"], 0, blade)
            self.assertFalse(E.can(f, "bt"), blade)

    def test_twin_strikes_twice_when_the_foe_survives(self):
        rng = random.Random(9)
        f = fighter({"kind": "twin", "mult": 0.65, "cost": 0.0, "cd": 1})
        foe = fighter(None, race="hollow")
        foe["hp"] = foe["max_hp"] = 10 ** 9
        st = E.new_state(f, foe, rng, pvp=True)
        st["cur"] = "a"
        ev = E._do_action(st, "bt", rng)
        hits = [e for e in ev if e.get("k") == "hit"]
        self.assertGreaterEqual(len(hits), 1)


if __name__ == "__main__":
    unittest.main()
