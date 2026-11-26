import random
import unittest

import engine as E


def fighter(name="A", blade="kyoka_suigetsu", shikai=False, artifact=None):
    f = E.new_fighter(name, 100, {"zanjutsu": 100, "hakuda": 100, "hoho": 80, "reiatsu": 100, "kido": 100},
                      10000, 10000, {"attack": 100, "crit": 0.1, "element": "light", "skills": [], "weapon_type": "melee"},
                      mods={"dmg": 1.0, "def": 1.0, "artifact_lives": 0})
    f["blade"] = blade
    if shikai:
        f["x"]["sk"] = 1
    if artifact:
        f["mods"].update(artifact)
    return f


class KyokaSuigetsuTests(unittest.TestCase):
    def setUp(self):
        self.a = fighter()
        self.b = fighter("B", blade=None)
        self.state = E.new_state(self.a, self.b, random.Random(7), duel_rules=False)
        self.state["cur"] = self.state["first"] = "a"
        self.state["awaiting"] = True

    def test_sealed_abilities_available_without_shikai(self):
        for action in ("ks1", "ks2", "ks3", "ks4"):
            self.assertTrue(E.can(self.a, action, self.state), action)
        self.assertFalse(E.can(self.a, "ks5", self.state))
        self.assertEqual(self.a["mods"]["dmg"], 1.0)  # unlocking Shikai in the profile is not activating it

    def test_actual_shikai_activation_applies_kyoka_and_hogyoku_resonance(self):
        self.a["race"] = "shinigami"
        self.a["mods"]["artifact_hogyoku"] = True
        events = []
        base = E._dmg_mult(self.a)
        E.sk_run(self.state, "a", events)
        self.assertAlmostEqual(E._dmg_mult(self.a) / base, 1.30 * 1.35)
        self.assertEqual(self.a["x"]["kyoka_shikai_t"], 5)
        self.assertEqual(self.a["x"]["kyoka_shikai_cd"], 9)
        self.assertEqual(self.a["x"]["kyoka_hogyoku"], 1)
        self.assertTrue(E.can(self.a, "ks5", self.state))

    def test_absolute_manipulator_has_sealed_dodge_and_shikai_regeneration(self):
        self.assertEqual(self.a["x"]["kyoka_shikai_t"], 0)
        self.a["hp"] = 5000
        self.a["race"] = "shinigami"
        self.a["ab"] = {"sg": {}}
        E.sk_run(self.state, "a", [])
        self.state["cur"] = "a"
        before = self.a["hp"]
        E.start_turn(self.state, random.Random(1))
        self.assertGreater(self.a["hp"], before)
        import data_balance as BAL
        # Nov 26: Kyoka's Shikai heal is KYOKA_HEAL_SHARE of max HP (was 10%), plus the natural turn regeneration (E.TURN_HP_REGEN, Nov 26: raised to 5%)
        self.assertEqual(self.a["hp"] - before, int(self.a["max_hp"] * BAL.KYOKA_HEAL_SHARE) + int(E._hb(self.a) * E.TURN_HP_REGEN))

    def test_shikai_last_four_player_actions_then_cools_down(self):
        self.a["race"] = "shinigami"
        self.a["ab"] = {"sg": {}}
        E.sk_run(self.state, "a", [])
        self.state["cur"] = "a"
        for _ in range(4):
            E.start_turn(self.state, random.Random(1))
            self.assertGreater(self.a["x"]["kyoka_shikai_t"], 0)
        E.start_turn(self.state, random.Random(1))
        self.assertEqual(self.a["x"]["kyoka_shikai_t"], 0)
        self.assertFalse(E.can(self.a, "ks5", self.state))
        self.assertFalse(E.sk_can(self.a))
        for _ in range(4):
            E.start_turn(self.state, random.Random(1))
        self.assertTrue(E.sk_can(self.a))

    def test_ultimate_requires_shikai(self):
        self.a["x"]["kyoka_shikai_t"] = 5
        self.assertTrue(E.can(self.a, "ks5", self.state))

    def test_ability_cooldown_is_enforced(self):
        self.a["x"]["ks_cd"]["ks1"] = 2
        self.assertFalse(E.can(self.a, "ks1", self.state))

    def test_sealed_illusion_strike_executes_and_starts_cooldown(self):
        before = self.b["hp"]
        E._do_action(self.state, "ks1", random.Random(1))
        self.assertLess(self.b["hp"], before)
        self.assertGreater(self.a["x"]["ks_cd"]["ks1"], 0)

    def test_ultimate_uses_five_turn_cooldown(self):
        self.a["x"]["kyoka_shikai_t"] = 5
        E._do_action(self.state, "ks5", random.Random(6))
        self.assertEqual(self.a["x"]["ks_cd"]["ks5"], 5)

    def test_shikai_execution_has_crit_and_pierce_profile(self):
        self.a["x"]["kyoka_shikai_t"] = 5
        before = self.b["hp"]
        E._do_action(self.state, "ks4", random.Random(2))
        self.assertLess(self.b["hp"], before)
        self.assertEqual(self.a["mods"].get("crit", 0), 0.0)  # temporary +30% is always restored

    def test_mirror_world_reflects_damage(self):
        self.a["x"]["ks_mirror"] = 2
        before = self.b["hp"]
        E._apply(self.state, "b", 500, False, random.Random(3), [], "atk", False)
        self.assertLess(self.a["hp"], self.a["max_hp"])
        self.assertEqual(self.b["hp"], before - 250)

    def test_undying_artifact_revives_once(self):
        self.a["mods"].update(artifact_lives=1, artifact_revive_hp=0.5)
        self.a["hp"] = 0
        E._check_end(self.state, [])
        self.assertEqual(self.a["hp"], 5000)
        self.assertEqual(self.a["mods"]["artifact_lives"], 0)

    def test_shadow_monarch_echo_uses_combat_damage_pipeline(self):
        self.a["mods"]["artifact_shadow_echo"] = 0.12
        self.state["cur"] = "a"
        before = self.b["hp"]
        events, _ = E.start_turn(self.state, random.Random(5))
        self.assertLess(self.b["hp"], before)
        self.assertTrue(any(e.get("k") == "shadow_echo" for e in events))

    def test_final_judgment_triple_boss_has_three_attacks(self):
        self.b["foe"] = "boss"
        self.state["b"]["wild"] = True
        self.state["final_judgment"] = {"stage": 5, "phases": 1, "phase": 1}
        self.state["cur"] = "b"
        self.state["dist"] = 0
        self.state["done"] = False
        self.state["awaiting"] = False
        events = E.do_action(self.state, "atk", random.Random(9))
        self.assertTrue(any(e.get("k") == "fj_triple" for e in events))

    def test_hogyoku_growth_is_bounded(self):
        self.a["mods"]["artifact_hogyoku"] = True
        st = {"a": self.a, "b": self.b, "cur": "a", "done": False, "final_judgment": {"phases": 1}}
        for _ in range(10):
            E.start_turn(st, random.Random(1))
        self.assertLessEqual(self.a["mods"]["dmg"], 1.241)

    def test_dark_reflection_ai_can_use_kyoka_abilities(self):
        self.b["race"] = "shinigami"
        self.b["blade"] = "kyoka_suigetsu"
        self.b["ai"] = True
        self.b["wild"] = False
        self.b["ab"] = {"sg": {}}
        self.b["x"]["kyoka_shikai_t"] = 4
        actions = {E._ai_ab(self.state, "b", random.Random(seed)) for seed in range(20)}
        self.assertTrue(any(action in {"ks1", "ks2", "ks3", "ks4", "ks5"} for action in actions))

    def test_final_judgment_absolute_phase_changes_mechanics(self):
        self.b["foe"] = "boss"
        self.b["hp"] = 1500
        self.state["cur"] = "b"
        self.state["final_judgment"] = {"stage": 10, "phases": 5, "phase": 1}
        events, _ = E.start_turn(self.state, random.Random(4))
        self.assertEqual(self.state["final_judgment"]["phase"], 5)
        self.assertTrue(any(e.get("k") == "fj_absolute" for e in events))
        self.assertTrue(any(e.get("k") == "fj_hazard" for e in events))
        self.assertTrue(any(e.get("k") == "fj_barrier" for e in events))
        self.assertGreater(self.b["shield"], 0)
        self.assertTrue(any(fx.get("k") == "burn" for fx in self.a["fx"]))

    def test_judgment_stage_three_blocks_specials(self):
        self.a["fj_limited"] = True
        self.assertTrue(E.can(self.a, "atk", self.state))
        self.assertFalse(E.can(self.a, "ks1", self.state))
        self.assertFalse(E.can(self.a, "hvy", self.state))


if __name__ == "__main__":
    unittest.main()
