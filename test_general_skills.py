"""General skills: any race can equip guard / strike / focus. Run: python -m unittest test_general_skills -v"""
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine as E  # noqa: E402
from data_race_rules import GENERAL_SKILLS, GEN_ORDER, gen_power  # noqa: E402
from data_races import RACES  # noqa: E402


def fighter(race, gen):
    r = RACES[race]
    return E.new_fighter(race, 40, dict(r["stats"]), 1000, 500, {"attack": 60, "crit": 0.05, "element": "light",
                         "skills": [], "weapon_type": "melee"}, armor=10, mods=dict(r["mods"]), race=race, gen=gen)


class GeneralSkillTests(unittest.TestCase):
    def test_every_race_can_use_every_general_skill(self):
        for race in RACES:
            for key in GENERAL_SKILLS:
                self.assertTrue(E.can(fighter(race, key), "gs"), (race, key))

    def test_no_skill_equipped_means_no_button(self):
        self.assertFalse(E.can(fighter("human", None), "gs"))

    def test_favourite_races_get_the_bonus(self):
        self.assertEqual(gen_power("quincy", "guard"), 1.25)
        self.assertEqual(gen_power("shinigami", "guard"), 1.0)

    def test_switch_cycles_through_all_states(self):
        seen, cur = [], None
        for _ in range(len(GEN_ORDER) + 1):
            seen.append(cur)
            cur = GEN_ORDER[(GEN_ORDER.index(cur) + 1) % len(GEN_ORDER)]
        self.assertEqual(seen[:4], [None, "guard", "strike", "focus"])
        self.assertEqual(seen[4], None)

    def test_each_skill_resolves_and_starts_its_cooldown(self):
        rng = random.Random(3)
        for key in GENERAL_SKILLS:
            f = fighter("human", key)
            foe = fighter("hollow", None)
            st = E.new_state(f, foe, rng, pvp=True)
            ev = E._do_action(st, "gs", rng)
            self.assertTrue(ev, key)
            self.assertGreater(E._x(f)["gcd"], 0, key)
            self.assertFalse(E.can(f, "gs"), key)  # on cooldown right after use

    def test_guard_adds_shield_and_focus_buffs(self):
        rng = random.Random(4)
        g = fighter("quincy", "guard")
        st = E.new_state(g, fighter("hollow", None), rng, pvp=True)
        E._do_action(st, "gs", rng)
        self.assertGreater(g["shield"], 0)
        fo = fighter("visored", "focus")
        st = E.new_state(fo, fighter("hollow", None), rng, pvp=True)
        E._do_action(st, "gs", rng)
        self.assertGreater(E._x(fo)["buff_m"], 1.0)


if __name__ == "__main__":
    unittest.main()
