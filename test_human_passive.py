"""Human Spiritual Awareness passive (pure logic). Run: python -m unittest test_human_passive -v"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_races import SPIRITUAL_AWARENESS_VS_HOLLOW, spiritual_awareness_mult  # noqa: E402


class HumanPassiveTests(unittest.TestCase):
    def test_humans_hit_harder_against_hollows(self):
        self.assertEqual(spiritual_awareness_mult("human", "hollow"), SPIRITUAL_AWARENESS_VS_HOLLOW)
        self.assertGreater(SPIRITUAL_AWARENESS_VS_HOLLOW, 1.0)

    def test_no_bonus_for_other_races_or_foes(self):
        for race in ("shinigami", "quincy", "hollow", "arrancar", "fullbringer", "visored"):
            self.assertEqual(spiritual_awareness_mult(race, "hollow"), 1.0, race)
        self.assertEqual(spiritual_awareness_mult("human", None), 1.0)
        self.assertEqual(spiritual_awareness_mult("human", "human"), 1.0)

    def test_missing_fields_are_safe(self):
        self.assertEqual(spiritual_awareness_mult(None, None), 1.0)


if __name__ == "__main__":
    unittest.main()
