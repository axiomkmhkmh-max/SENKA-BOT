"""Combat contracts for signature artifact effects and the revised dungeon XP curve."""
import ast
import unittest
from pathlib import Path

import data_artifacts as A
import data_zanpakuto as Z
import engine as E
import random


class ArtifactCombatContracts(unittest.TestCase):
    def test_signature_effects_are_defined_and_localized(self):
        for aid in ("art_hogyoku", "art_soulking", "art_lifesteal_crown", "art_shadow_monarch", "art_almighty", "art_transcendent_armor"):
            self.assertIn(aid, A.ART_BY_ID)
            self.assertTrue(A.art_bonus_text(aid, lang="fa"))
            self.assertTrue(A.art_bonus_text(aid, lang="en"))
        self.assertIn("دیواین", A.art_bonus_text("art_shadow_monarch", lang="fa"))
        self.assertIn("Divine", A.art_bonus_text("art_shadow_monarch", lang="en"))

    def test_reconciliation_preserves_over_cap_occupancy(self):
        held = A.art_held_count(3, 2)
        self.assertEqual(held, 5)
        self.assertGreaterEqual(held, A.art_cap("art_transcendent_armor"))

    def test_rare_artifacts_have_explicit_tiers_and_caps(self):
        self.assertEqual(A.ART_BY_ID["art_transcendent_armor"]["tier"], 7)
        self.assertEqual(A.ART_BY_ID["art_shadow_monarch"]["tier"], 6)
        self.assertEqual(A.ART_BY_ID["art_lifesteal_crown"]["tier"], 5)
        self.assertEqual(A.ART_BY_ID["art_transcendent_armor"]["cap"], 2)
        self.assertLess(A.art_drop_weight("art_lifesteal_crown"), 1.0)
        self.assertLess(A.art_drop_weight("art_shadow_monarch"), A.art_drop_weight("art_lifesteal_crown"))
        self.assertLess(A.art_drop_weight("art_transcendent_armor"), A.art_drop_weight("art_shadow_monarch"))

    def test_kyoka_suigetsu_is_a_high_power_release(self):
        stage = Z.BLADE_STAGES["kyoka_suigetsu"]
        self.assertGreaterEqual(stage["shikai_bonus"], 0.20)
        self.assertGreaterEqual(stage["bankai_bonus"], 0.30)

    def test_transcendent_armor_revives_once_at_half_hp(self):
        a = E.new_fighter("Bearer", 50, {"hoho": 10}, 1000, 100, None,
                          mods={"artifact_lives": 1, "artifact_revive_hp": 0.50})
        b = E.new_fighter("Enemy", 50, {"hoho": 10}, 1000, 100, None)
        state = {"a": a, "b": b, "pvp": False}
        a["hp"] = 0
        self.assertFalse(E._check_end(state, []))
        self.assertEqual(a["hp"], 500)
        self.assertEqual(a["mods"]["artifact_lives"], 0)
        a["hp"] = 0
        self.assertTrue(E._check_end(state, []))

    def test_lifesteal_uses_actual_damage_dealt(self):
        a = E.new_fighter("Bearer", 50, {"zanjutsu": 30, "hoho": 10}, 1000, 100, None,
                          mods={"artifact_lifesteal": 0.10})
        b = E.new_fighter("Enemy", 50, {"hoho": 1}, 1000, 100, None)
        a["hp"] = 500
        state = E.new_state(a, b, random.Random(7))
        events = []
        E._deal(state, "a", 1.0, random.Random(7), events)
        self.assertGreater(a["hp"], 500)
        self.assertLessEqual(a["hp"], 1000)

    def test_hogyoku_evolution_stops_at_exactly_24_percent(self):
        a = E.new_fighter("Bearer", 50, {"hoho": 10}, 1000, 100, None,
                          mods={"dmg": 1.5, "artifact_hogyoku": True})
        b = E.new_fighter("Enemy", 50, {"hoho": 10}, 1000, 100, None)
        state = E.new_state(a, b, random.Random(11))
        state["cur"] = "a"
        for _ in range(8):
            E.start_turn(state, random.Random(11))
        self.assertEqual(a["x"]["hogyoku_evo"], 6)
        self.assertAlmostEqual(a["mods"]["dmg"], 1.5 * 1.24, places=8)

    def test_shadow_echo_cannot_bypass_duel_hit_cap(self):
        a = E.new_fighter("Bearer", 50, {"zanjutsu": 30, "hoho": 10}, 1000, 100, None,
                          mods={"artifact_shadow_echo": 0.12})
        b = E.new_fighter("Enemy", 50, {"hoho": 1}, 1000, 100, None)
        state = E.new_state(a, b, random.Random(7), pvp=True)
        before = b["hp"]
        E._deal(state, "a", 100.0, random.Random(7), [])
        self.assertLessEqual(before - b["hp"], int(E.duel_cap_hp(state) * E.DUEL["hit_cap"]))

    def test_shadow_echo_is_absorbed_by_shields(self):
        a = E.new_fighter("Bearer", 50, {"zanjutsu": 30, "hoho": 10}, 1000, 100, None,
                          mods={"artifact_shadow_echo": 0.12})
        b = E.new_fighter("Enemy", 50, {"hoho": 1}, 1000, 100, None)
        state = E.new_state(a, b, random.Random(7))
        b["shield"] = 100000
        before_hp, before_shield = b["hp"], b["shield"]
        E._deal(state, "a", 1.0, random.Random(7), [])
        self.assertEqual(b["hp"], before_hp)
        self.assertLess(b["shield"], before_shield)

    def test_dungeon_xp_is_capped_to_prevent_runaway_level_farming(self):
        tree = ast.parse(Path(__file__).with_name("service_combat.py").read_text(encoding="utf-8"))
        values = {}
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                if node.targets[0].id in {"DG_XP_MULT", "DG_SCALE_XP_EXP", "DG_FINAL_XP_MULT"}:
                    values[node.targets[0].id] = ast.literal_eval(node.value)
        self.assertLessEqual(values["DG_XP_MULT"], 1.6)
        self.assertLessEqual(values["DG_SCALE_XP_EXP"], 0.85)  # Nov 26: raised from 0.60 so higher difficulties pay clearly more XP
        self.assertLessEqual(values["DG_FINAL_XP_MULT"], 1.6)


if __name__ == "__main__":
    unittest.main()
