import unittest
from config import GAME_DEFAULTS as G


class StatPoints(unittest.TestCase):
    def test_total_points_and_cap(self):
        total = sum(G["pts_per_level"] + (G["pts_every5"] if lv % 5 == 0 else 0) for lv in range(2, G["level_max"] + 1))
        self.assertEqual(G["pts_per_level"], 2)
        self.assertEqual(G["stat_max"], 350)
        self.assertEqual(total, 2 * 749)          # 1498 points from level 1 to 750
        self.assertLess(total, 5 * G["stat_max"])  # cannot max every stat


if __name__ == "__main__":
    unittest.main()
