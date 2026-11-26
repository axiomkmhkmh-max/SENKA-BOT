"""Kyoka Suigetsu damage must scale with Reiatsu and Zanjutsu upgrades."""
import random
import unittest
import engine as E

W = {"attack": 100, "crit": 0.0, "element": "light", "skills": [], "weapon_type": "melee"}


def make_fighter(name, reiatsu, zanjutsu):
    f = E.new_fighter(name, 100,
                      {"zanjutsu": zanjutsu, "reiatsu": reiatsu, "hakuda": 1, "hoho": 1, "kido": 1},
                      100000, 100000, W, race="shinigami")
    f["blade"] = "kyoka_suigetsu"
    return f


def run_damage(action, reiatsu, zanjutsu):
    a, b = make_fighter("Kyoka", reiatsu, zanjutsu), make_fighter("Target", 1, 1)
    st = E.new_state(a, b, random.Random(7), duel_rules=False)
    st["cur"] = "a"
    if action == "ks2":
        E._do_action(st, "ks2", random.Random(7))
        before = b["hp"]
        E._deal(st, "b", 1.0, random.Random(11), [], "atk")
        return before - b["hp"]  # damage from the decoy's counter
    before = b["hp"]
    E._do_action(st, action, random.Random(11))
    return before - b["hp"]


class KyokaStatScalingTests(unittest.TestCase):
    def test_illusion_strike_scales_with_both_stats(self):
        self.assertGreater(run_damage("ks1", 160, 160), run_damage("ks1", 40, 40))

    def test_false_reality_counter_scales_with_both_stats(self):
        self.assertGreater(run_damage("ks2", 160, 160), run_damage("ks2", 40, 40))

    def test_mind_distortion_scales_with_both_stats(self):
        self.assertGreater(run_damage("ks3", 160, 160), run_damage("ks3", 40, 40))

    def test_phantom_step_scales_with_both_stats(self):
        self.assertGreater(run_damage("ks4", 160, 160), run_damage("ks4", 40, 40))

    def test_each_damage_skill_scales_when_reiatsu_alone_is_upgraded(self):
        for action in ("ks1", "ks2", "ks3", "ks4"):
            with self.subTest(action=action):
                self.assertGreater(run_damage(action, 160, 80), run_damage(action, 40, 80))

    def test_each_damage_skill_scales_when_zanjutsu_alone_is_upgraded(self):
        for action in ("ks1", "ks2", "ks3", "ks4"):
            with self.subTest(action=action):
                self.assertGreater(run_damage(action, 80, 160), run_damage(action, 80, 40))

    def test_kyoka_damage_source_has_explicit_stat_weights(self):
        self.assertEqual(E.KYOKA_DAMAGE_SRC["mix"], {"reiatsu": 0.50, "zanjutsu": 0.50})


if __name__ == "__main__":
    unittest.main()
