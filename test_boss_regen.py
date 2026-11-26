import random
import unittest

import engine as E
from data_misc import BOSS_REGEN_SHARE, PVE_REGEN_SHARE


def _regen(foe):
    p = E.new_fighter("P", 100, {"zanjutsu": 50, "kido": 1, "hakuda": 50, "hoho": 50, "reiatsu": 50}, 10 ** 4, 100, None)
    f = E.new_fighter("X", 140, {"zanjutsu": 50, "kido": 1, "hakuda": 50, "hoho": 50, "reiatsu": 50}, 272361, 100, None)
    if foe:
        f["foe"] = foe
    f["hp"] = 100000
    state = {"a": p, "b": f, "turn": 1, "cur": "b", "first": "a", "done": False, "winner": None}
    E.start_turn(state, random.Random(1))
    return f["hp"] - 100000


class BossRegen(unittest.TestCase):
    def test_boss_regen_is_a_fraction_of_normal(self):
        normal, boss = _regen(None), _regen("boss")
        self.assertGreater(normal, 4000)               # 3% of 272K / 1.5 = ~5.4K a turn
        self.assertAlmostEqual(boss / normal, BOSS_REGEN_SHARE, delta=0.01)
        self.assertEqual(_regen("world_boss"), boss)

    def test_wild_foes_regen_a_reduced_share(self):
        # Nov 26: a war commander healed 2,204 a turn against a 2,108 heavy strike. Wild foes now get PVE_REGEN_SHARE of it.
        normal = _regen(None)
        self.assertAlmostEqual(_regen("pve") / normal, PVE_REGEN_SHARE, delta=0.01)
        self.assertAlmostEqual(_regen("hollow") / normal, PVE_REGEN_SHARE, delta=0.01)
        self.assertGreater(_regen("pve"), _regen("boss"))  # still more than a boss


if __name__ == "__main__":
    unittest.main()
