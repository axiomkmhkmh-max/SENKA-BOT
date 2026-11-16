"""Zanpakuto bond belongs to the blade, not to the weapon in hand. Run: python -m unittest test_zanpakuto_bond -v"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_zanpakuto import bond_key, bond_value  # noqa: E402


class BondTests(unittest.TestCase):
    def test_bond_survives_taking_the_weapon_out(self):
        ch = {"weapon_id": "wp_001", "zanpakuto": {"blade_id": "zangetsu"}, "bond": {"zangetsu": 300}}
        self.assertEqual(bond_value(ch), 300)
        ch["weapon_id"] = None  # weapon taken out of the hand
        self.assertEqual(bond_value(ch), 300)
        self.assertEqual(bond_key(ch), "zangetsu")

    def test_switching_blades_starts_each_blades_own_count(self):
        ch = {"weapon_id": "wp_001", "zanpakuto": {"blade_id": "senbonzakura"}, "bond": {"zangetsu": 300}}
        self.assertEqual(bond_value(ch), 0)

    def test_no_blade_chosen_keeps_the_old_weapon_key(self):
        ch = {"weapon_id": "wp_002", "zanpakuto": {}, "bond": {"wp_002": 120}}
        self.assertEqual(bond_key(ch), "wp_002")
        self.assertEqual(bond_value(ch), 120)

    def test_no_weapon_and_no_blade_reads_zero(self):
        self.assertEqual(bond_value({"weapon_id": None, "zanpakuto": {}, "bond": {"none": 40}}), 40)
        self.assertEqual(bond_value({}), 0)


if __name__ == "__main__":
    unittest.main()
