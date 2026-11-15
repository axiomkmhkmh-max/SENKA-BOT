"""Zanpakutō catalogue, unlock gates and the blade-ID root fix (pure logic).
Run: python -m unittest test_zanpakuto_blades -v"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_zanpakuto import BLADE_STAGES, BLADE_STYLE, BLADE_UNLOCK, blade_valid, stage_name, unlocked_blades  # noqa: E402


class CatalogueTests(unittest.TestCase):
    def test_every_gated_blade_is_in_the_catalogue(self):
        self.assertTrue(set(BLADE_UNLOCK) <= set(BLADE_STAGES))

    def test_every_styled_blade_is_in_the_catalogue(self):
        self.assertTrue(set(BLADE_STYLE) <= set(BLADE_STAGES))

    def test_every_blade_has_a_shikai_name_in_both_languages(self):
        for bid, s in BLADE_STAGES.items():
            self.assertEqual(len(s["shikai"]), 2, bid)
            self.assertTrue(all(s["shikai"]), bid)

    def test_no_blade_id_looks_like_a_weapon_item(self):
        # the old bug: blade ids were weapon ids such as "it_1234"
        for bid in BLADE_STAGES:
            self.assertFalse(bid.startswith("it_"), bid)


class UnlockTests(unittest.TestCase):
    def test_unlocks_grow_with_level(self):
        prev = set()
        for lvl in (1, 20, 30, 45, 60, 100):
            cur = set(unlocked_blades(lvl))
            self.assertTrue(prev <= cur, lvl)
            prev = cur

    def test_nothing_is_open_below_the_first_gate(self):
        self.assertEqual(unlocked_blades(0), [])

    def test_zangetsu_is_the_first_blade(self):
        self.assertIn("zangetsu", unlocked_blades(1))

    def test_kokujo_needs_level_60(self):
        self.assertNotIn("kokujo_tengen_myoo", unlocked_blades(59))
        self.assertIn("kokujo_tengen_myoo", unlocked_blades(60))


class RootFixTests(unittest.TestCase):
    def test_a_weapon_id_is_never_a_valid_blade(self):
        self.assertFalse(blade_valid("it_1234", 100))
        self.assertFalse(blade_valid("", 100))
        self.assertFalse(blade_valid(None, 100))

    def test_a_locked_blade_is_refused(self):
        self.assertFalse(blade_valid("kokujo_tengen_myoo", 59))
        self.assertTrue(blade_valid("kokujo_tengen_myoo", 60))

    def test_stage_name_for_unknown_blade_is_none(self):
        self.assertIsNone(stage_name("it_1234", "shikai", "en"))
        self.assertEqual(stage_name("minazuki", "shikai", "en"), "Minazuki")


if __name__ == "__main__":
    unittest.main()
