"""Visored unlock through the Visored Gauntlet (pure logic). Run: python -m unittest test_visored_unlock -v"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_races import race_selectable, unlocks_visored  # noqa: E402


class VisoredUnlockTests(unittest.TestCase):
    def test_only_shinigami_clearing_the_gauntlet_unlocks(self):
        self.assertTrue(unlocks_visored("shinigami", "visored_gauntlet"))
        for race in ("human", "hollow", "quincy", "arrancar", "fullbringer", "visored"):
            self.assertFalse(unlocks_visored(race, "visored_gauntlet"), race)
        self.assertFalse(unlocks_visored("shinigami", "hollow_den"))
        self.assertFalse(unlocks_visored("shinigami", None))

    def test_locked_race_needs_the_unlock_flag(self):
        self.assertFalse(race_selectable("visored", {}))
        self.assertFalse(race_selectable("visored", {"visored_unlocked": False}))
        self.assertTrue(race_selectable("visored", {"visored_unlocked": True}))

    def test_normal_races_are_always_selectable(self):
        for race in ("shinigami", "quincy", "hollow", "arrancar", "fullbringer", "human"):
            self.assertTrue(race_selectable(race, {}), race)

    def test_unknown_race_is_never_selectable(self):
        self.assertFalse(race_selectable("nonexistent", {"visored_unlocked": True}))
        self.assertFalse(race_selectable(None, {}))


if __name__ == "__main__":
    unittest.main()
