import random
import unittest

import engine as E


def _hit(zan, wpn, boss_lvl, n=60):
    tot = 0
    for s in range(n):
        rng = random.Random(s)
        p = E.new_fighter("P", boss_lvl, {"zanjutsu": zan, "kido": 1, "hakuda": 50, "hoho": 50, "reiatsu": 50}, 10 ** 5, 100,
                          {"attack": wpn, "crit": 0.0, "element": "light", "skills": [], "weapon_type": "melee"})
        d = 2 + boss_lvl * 1.1
        b = E.new_fighter("Boss", boss_lvl, {"zanjutsu": 1, "kido": 1, "hakuda": d * 2, "hoho": 1, "reiatsu": 1}, 10 ** 9, 100,
                          {"attack": 1, "element": "fire", "skills": [], "weapon_type": "melee"}, armor=0)
        b["foe"] = "world_boss"
        p["dmgx"] = 2.0
        ev = []
        E._deal({"a": p, "b": b, "turn": 1, "cur": "a", "first": "a", "done": False, "winner": None}, "a", 1.0, rng, ev, "atk")
        tot += sum(e.get("n", 0) for e in ev if e["k"] == "hit")
    return tot / n


class WorldBossFloor(unittest.TestCase):
    def tearDown(self):
        E.WORLD_BOSS_FLOOR = 0.25

    def test_hit_below_boss_defence_is_not_one_point(self):
        E.WORLD_BOSS_FLOOR = 0
        low = _hit(80, 40, 300)
        E.WORLD_BOSS_FLOOR = 0.25
        self.assertLess(low, 4)                 # (x2 here, x6 boss_dmg_mult later) the old collapse
        self.assertGreater(_hit(80, 40, 300), 25)

    def test_strong_player_unchanged(self):
        E.WORLD_BOSS_FLOOR = 0
        a = _hit(350, 200, 650)
        E.WORLD_BOSS_FLOOR = 0.25
        self.assertEqual(a, _hit(350, 200, 650))


if __name__ == "__main__":
    unittest.main()
