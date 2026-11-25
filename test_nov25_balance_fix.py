"""Regression tests for the Nov 25 Kyoka, relic-slot, artifact and dungeon-economy fixes."""
import unittest
import data_artifacts as A
import data_zanpakuto as Z
import effects
import engine as E
from config import GAME_DEFAULTS


class Nov25BalanceFix(unittest.TestCase):
    def test_relic_slots_unlock_progressively_to_four(self):
        self.assertEqual([effects.relic_slots(x, GAME_DEFAULTS) for x in (1, 34, 35, 59, 60, 84, 85)],
                         [1, 1, 2, 2, 3, 3, 4])

    def test_kyoka_has_sealed_damage_baseline(self):
        f = E.new_fighter("Kyoka", 50, {"zanjutsu": 20, "hoho": 10}, 1000, 100, None)
        f["blade"] = "kyoka_suigetsu"
        self.assertGreaterEqual(E._dmg_mult(f), 1.30)

    def test_all_signature_artifacts_have_a_real_effect(self):
        ids = ("art_hogyoku", "art_kyoka", "art_glasses", "art_restraint_chair", "art_ice",
               "art_zangetsu_frag", "art_badge", "art_visored_mask", "art_soulking",
               "art_lifesteal_crown", "art_shadow_monarch", "art_almighty", "art_transcendent_armor")
        for aid in ids:
            self.assertTrue(A.ART_BY_ID[aid].get("effect"), aid)
            self.assertTrue(A.art_bonus_text(aid, lang="fa"), aid)
            self.assertTrue(A.art_bonus_text(aid, lang="en"), aid)

    def test_dungeon_xp_is_reduced_and_key_limits_are_declared(self):
        from pathlib import Path
        import ast
        root = Path(__file__).parent
        tree = ast.parse((root / "service_combat.py").read_text(encoding="utf-8"))
        values = {n.targets[0].id: ast.literal_eval(n.value) for n in tree.body
                  if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)
                  and n.targets[0].id in {"DG_XP_MULT", "DG_FINAL_XP_MULT"}}
        self.assertLessEqual(values["DG_XP_MULT"], 1.6)
        self.assertLessEqual(values["DG_FINAL_XP_MULT"], 1.6)
        craft_src = (root / "service_crafting.py").read_text(encoding="utf-8")
        self.assertIn('"legendary": 1, "abyss": 2, "nightmare": 4', craft_src)
        self.assertIn("dailycap", craft_src)


if __name__ == "__main__":
    unittest.main()
