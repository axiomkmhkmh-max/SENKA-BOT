"""Every dungeon has its own enemies and a named last-stage boss; names are (fa, en) text pairs."""
import unittest

from data_bleachfx import enemy_sig
from data_races import DUNGEON_ENEMIES, DUNGEONS, LOCATIONS


def _pair_ok(p):
    return isinstance(p, tuple) and len(p) == 2 and all(isinstance(x, str) and x.strip() for x in p)


class DungeonEnemies(unittest.TestCase):
    def test_every_dungeon_has_enemies_and_boss(self):
        self.assertEqual(set(DUNGEON_ENEMIES), set(DUNGEONS))
        for dg, d in DUNGEON_ENEMIES.items():
            self.assertGreaterEqual(len(d["enemies"]), 3, dg)
            self.assertTrue(all(_pair_ok(p) for p in d["enemies"]), dg)
            self.assertTrue(_pair_ok(d["boss"]), dg)
            self.assertIn(d["race"], (None, "hollow", "quincy"), dg)

    def test_hollow_and_quincy_dungeons(self):
        for dg in ("hollow_den", "menos_forest"):
            self.assertTrue(all(enemy_sig(DUNGEON_ENEMIES[dg]["race"], p) == "cero" for p in DUNGEON_ENEMIES[dg]["enemies"]))
        for dg in ("quincy_fort", "schatten_depths"):
            self.assertTrue(all(enemy_sig(DUNGEON_ENEMIES[dg]["race"], p) == "hiren" for p in DUNGEON_ENEMIES[dg]["enemies"]))

    def test_location_enemies_are_pairs(self):
        for k, loc in LOCATIONS.items():
            self.assertEqual(len(loc["enemies"]), 3, k)
            self.assertTrue(all(_pair_ok(p) for p in loc["enemies"]), k)


if __name__ == "__main__":
    unittest.main()
