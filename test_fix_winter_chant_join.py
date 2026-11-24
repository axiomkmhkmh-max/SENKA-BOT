import unittest

import engine as E
from data_world import event_pts


class WinterChantJoin(unittest.TestCase):
    def test_winter_war_kills_count_anywhere(self):
        for loc in ("rukongai", "seireitei", "karakura", "hueco_mundo"):
            self.assertEqual(event_pts("winter_war", "pve_win", loc), 1)
            self.assertEqual(event_pts("winter_war", "elite_win", loc), 2)

    def test_chant_offered_for_bakudo_only_caster(self):
        f = E.new_fighter("P", 60, {"zanjutsu": 5, "kido": 50, "hakuda": 5, "hoho": 5, "reiatsu": 50}, 5000, 5000,
                          {"attack": 10, "element": "fire", "skills": [], "weapon_type": "melee"}, armor=0, race="shinigami")
        f["kido"] = {"had": [], "bak": [98, 82, 79]}
        f["re"] = f["max_re"] = 5000
        self.assertTrue(E.kido_castable(f, "bak", 98))    # Nov 25: 98 is castable bare ...
        self.assertTrue(E.can(f, "ch"))                   # ... and the chant button is still there for full power
        E._x(f)["chant"] = 1
        self.assertTrue(E.kido_castable(f, "bak", 98))
        self.assertEqual(E.best_kido(f, "bak"), 98)


if __name__ == "__main__":
    unittest.main()
