"""Nov 26 rebuild: power soft-cap, kidō quick picks, shared fighter card."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine as E
import data_kido as KD
from panel_ui import card


class Rebuild(unittest.TestCase):
    def test_soft_power_leaves_normal_skills_alone_and_tames_outliers(self):
        for p in (1.0, 1.6, 2.4, 4.0):
            self.assertEqual(E.soft_power(p), p)
        self.assertLess(E.soft_power(15.0), 15.0)
        self.assertGreater(E.soft_power(15.0), E.soft_power(9.0))

    def test_quick_picks_name_the_best_spell_per_role(self):
        picks = {r: n for r, _, _, _, n in KD.quick_picks("had", [1, 4, 31, 63, 90])}
        self.assertEqual(picks["best"], 90)
        self.assertEqual(picks["burn"], 31)
        self.assertEqual(picks["cheap"], 1)
        self.assertEqual(KD.quick_picks("had", []), [])

    def test_card_has_hp_and_reiatsu(self):
        f = {"name": "A", "level": 5, "hp": 50, "max_hp": 100, "re": 10, "max_re": 100, "x": {"gauge": 40}}
        txt = card("en", f, "🧑")
        self.assertIn("50%", txt)
        self.assertIn("40%", txt)
        self.assertIn("🔮", txt)


if __name__ == "__main__":
    unittest.main()
