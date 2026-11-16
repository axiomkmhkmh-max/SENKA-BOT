"""Hyōrinmaru is owner-only and stronger. Run: python -m unittest test_hyorinmaru -v"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_zanpakuto import BLADE_STAGES, BLADE_TECH_KINDS, blade_technique  # noqa: E402


class HyorinmaruTests(unittest.TestCase):
    def test_it_is_owner_only_by_default(self):
        # znp_lock imports the database driver, so read its default list from the source instead
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "znp_lock.py"), encoding="utf-8") as f:
            src = f.read()
        self.assertIn('DEFAULT_OWNER_ONLY = ["hyorinmaru"]', src)

    def test_stronger_than_the_common_blades(self):
        t = blade_technique("hyorinmaru")
        self.assertGreater(t["mult"], BLADE_TECH_KINDS["pierce"]["mult"])
        self.assertGreater(t["pierce"], BLADE_TECH_KINDS["pierce"]["pierce"])
        self.assertGreaterEqual(BLADE_STAGES["hyorinmaru"]["bankai_bonus"], 0.10)


if __name__ == "__main__":
    unittest.main()
