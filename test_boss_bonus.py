import random
import unittest

import engine as E
from data_misc import DMG_MULT, PLAYER_VS_BOSS_DMG, PLAYER_VS_PVE_DMG, BOSS_DMG_MULT


def _f(name, foe=None):
    f = E.new_fighter(name, 100, {"zanjutsu": 100, "kido": 1, "hakuda": 50, "hoho": 50, "reiatsu": 50}, 10 ** 4, 100, None)
    if foe:
        f["foe"] = foe
    return f


class BossBonus(unittest.TestCase):
    def dmgx(self, foe):
        p, e = _f("P"), _f("E", foe)
        E.new_state(p, e, random.Random(1))
        return p["dmgx"], e["dmgx"]

    def test_players_hit_bosses_harder(self):
        for foe in ("boss", "world_boss"):
            pd, ed = self.dmgx(foe)
            self.assertAlmostEqual(pd, DMG_MULT * PLAYER_VS_BOSS_DMG)
            self.assertEqual(ed, BOSS_DMG_MULT)

    def test_wild_enemies_a_little_harder(self):
        for foe in ("pve", "hollow"):
            self.assertAlmostEqual(self.dmgx(foe)[0], DMG_MULT * PLAYER_VS_PVE_DMG)

    def test_pvp_unchanged(self):
        self.assertEqual(self.dmgx(None)[0], DMG_MULT)


if __name__ == "__main__":
    unittest.main()
