"""Race evolution: one 5-stage canon path per race, cumulative bonuses that really reach the fight.
Run: python -m unittest test_evolution -v"""
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _stubs import import_with_stubs  # noqa: E402

import_with_stubs("service_combat")
import engine as E  # noqa: E402
from data_bleachfx import GAUGE  # noqa: E402
from data_evolution import EVO_PATHS, evo_bonus, evo_title  # noqa: E402
from data_races import RACES  # noqa: E402


def fighter(race, evo=None, **kw):
    w = {"attack": 30, "crit": 0.0, "element": "light", "skills": [], "weapon_type": "melee"}
    f = E.new_fighter("X", 40, {"zanjutsu": 60, "kido": 40, "hakuda": 40, "hoho": 40, "reiatsu": 40}, 2000, 800, w,
                      race=race, sig=kw.pop("sig", None), **kw)
    if evo:
        f["evo"] = evo
    return f


class FixedRng(random.Random):
    def __init__(self, v):
        super().__init__(1)
        self.v = v

    def random(self):
        return self.v


class PathTests(unittest.TestCase):
    def test_every_race_has_five_canon_stages(self):
        for race in RACES:
            self.assertEqual(len(EVO_PATHS[race]), 5, race)
            self.assertEqual(len(RACES[race]["evo"]), 5, race)
        self.assertEqual(evo_title("shinigami", 4, "en"), "Captain")
        self.assertEqual(evo_title("arrancar", 4, "en"), "Segunda Etapa")
        self.assertEqual(evo_title("quincy", 4, "en"), "Schutzstaffel")

    def test_bonuses_are_cumulative(self):
        b = evo_bonus("shinigami", 4)
        self.assertAlmostEqual(b["dmg"], 0.15)
        self.assertEqual(b["kido"], 0.10)
        self.assertEqual(b["release_turns"], 1)
        self.assertEqual(evo_bonus("shinigami", 0), {})

    def test_visored_mask_rage_falls_to_zero(self):
        self.assertEqual(evo_bonus("visored", 1)["mask_rage"], 0.08)
        self.assertEqual(evo_bonus("visored", 3)["mask_rage"], 0.0)


class EngineTests(unittest.TestCase):
    def test_release_turns_grow_with_evolution(self):
        for evo, want in ((None, GAUGE["turns"] + 1), ({"release_turns": 1}, GAUGE["turns"] + 2)):
            a, b = fighter("shinigami", evo), fighter("hollow", ai=True)
            st = E.new_state(a, b, random.Random(1))
            st["cur"], st["awaiting"] = "a", True
            a["x"]["gauge"] = GAUGE["full"]
            E._do_action(st, "gx", random.Random(1))
            self.assertEqual(a["x"]["awake"], want)

    def test_mastered_mask_never_rages(self):
        a, b = fighter("visored", {"mask_rage": 0.0}), fighter("hollow", ai=True)
        st = E.new_state(a, b, random.Random(1))
        st["cur"] = "a"
        a["form"].update(on=1, left=5)
        ev, skipped = E.start_turn(st, FixedRng(0.01))
        self.assertFalse(skipped)

    def test_wild_mask_still_rages(self):
        a, b = fighter("visored"), fighter("hollow", ai=True)
        st = E.new_state(a, b, random.Random(1))
        st["cur"] = "a"
        a["form"].update(on=1, left=5)
        ev, skipped = E.start_turn(st, FixedRng(0.01))
        self.assertTrue(skipped)

    def test_lieutenant_shunpo_cooldown(self):
        a, b = fighter("shinigami", {"sig_cd": 3}, sig="shunpo"), fighter("hollow", ai=True)
        st = E.new_state(a, b, random.Random(1))
        st["cur"] = "a"
        E._signature(st, "a", random.Random(1), [])
        self.assertEqual(a["x"]["cd"], 3)

    def test_wild_enemies_never_release(self):
        b = fighter("human", ai=True)
        b["wild"] = True
        b["x"]["gauge"] = GAUGE["full"]
        self.assertFalse(E.can(b, "gx"))


if __name__ == "__main__":
    unittest.main()
