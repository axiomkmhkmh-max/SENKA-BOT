"""Nov 26: beta blades open to everyone, rarity tiers, per-difficulty dungeon XP caps."""
import unittest

import data_zanpakuto as Z


class BetaAndTiers(unittest.TestCase):
    def test_beta_blades_open_at_level_1(self):
        for b in Z.BETA_BLADES:
            self.assertIn(b, Z.unlocked_blades(1))
            self.assertTrue(Z.blade_valid(b, 1))

    def test_non_beta_blades_keep_their_gate(self):
        self.assertNotIn("kyoka_suigetsu", Z.unlocked_blades(44))
        self.assertIn("kyoka_suigetsu", Z.unlocked_blades(45))

    def test_every_blade_has_a_tier_and_list_is_best_first(self):
        self.assertTrue(set(Z.BLADE_STAGES) <= set(Z.BLADE_TIER))
        tiers = [Z.blade_tier(b) for b in Z.unlocked_blades(200)]
        self.assertEqual(tiers, sorted(tiers, reverse=True))

    def test_dungeon_xp_caps_grow_with_difficulty(self):
        src = open("service_combat.py", encoding="utf-8").read()
        self.assertIn("DG_FINAL_XP_CAP_BY_DIFF", src)
        ns = {}
        line = [l for l in src.splitlines() if l.startswith("DG_FINAL_XP_CAP_BY_DIFF")][0]
        exec(line, ns)
        v = [ns["DG_FINAL_XP_CAP_BY_DIFF"][d] for d in ("normal", "hard", "nightmare", "abyss", "legendary")]
        self.assertEqual(v, sorted(v))


if __name__ == "__main__":
    unittest.main()
