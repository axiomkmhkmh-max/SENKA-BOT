"""Nov 23: Kidō card level gates, harder dungeon XP, roll shop limits."""
import unittest

import data_abilities as AB
import data_extras2 as X
from data_kido import card_min_level


class KidoCardGate(unittest.TestCase):
    def test_low_cards_unchanged(self):
        for n in (1, 10, 31, 59):
            self.assertEqual(card_min_level(n), -(-n * 8 // 10))

    def test_epic_and_legendary_cards_need_real_levels(self):
        self.assertEqual(card_min_level(60), 100)
        self.assertEqual(card_min_level(79), 195)
        self.assertEqual(card_min_level(80), 205)
        self.assertEqual(card_min_level(90), 255)
        self.assertEqual(card_min_level(99), 300)

    def test_never_decreasing(self):
        vals = [card_min_level(n) for n in range(1, 100)]
        self.assertEqual(vals, sorted(vals))


class RollShop(unittest.TestCase):
    def test_no_rare_or_mythic(self):
        self.assertNotIn("Rare", X.ROLL_WEIGHTS)
        self.assertNotIn("Mythic", X.ROLL_WEIGHTS)

    def test_limit_blocks_ten(self):
        self.assertLess(X.ROLL_DAILY_LIMIT, 10)


class MasteryGate(unittest.TestCase):
    def test_top_step_needs_300(self):
        self.assertEqual(AB.upgrade_min_level(AB.LV_MAX - 1), 300)

    def test_gate_rises(self):
        self.assertEqual(AB.UPGRADE_MIN_LEVEL, sorted(AB.UPGRADE_MIN_LEVEL))


if __name__ == "__main__":
    unittest.main()
