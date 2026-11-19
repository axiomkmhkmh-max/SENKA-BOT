"""World boss burst phase: one hit of at least boss_burst_dmg opens a special state against that player.
Run: python -m unittest test_boss_burst -v"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import GAME_DEFAULTS  # noqa: E402
from data_world import burst_rule  # noqa: E402
from i18n import LOCALES  # noqa: E402

NOW = 1000.0


def st(**kw):
    return {**GAME_DEFAULTS, **kw}


class BurstTests(unittest.TestCase):
    def test_defaults_do_not_fire_on_a_normal_hit(self):
        # live players hit for about 30k: a normal hit must never open the special state
        self.assertGreater(max(GAME_DEFAULTS["boss_burst_dmg"], 0), 30000 * 1.5)
        self.assertEqual(burst_rule(30000, 1, {}, NOW, st(), 150000), (30000, False, False))

    def test_bar_grows_with_boss_hp(self):
        s = st(boss_burst_dmg=50000, boss_burst_pct=0.05)
        self.assertEqual(burst_rule(60000, 1, {}, NOW, s, 400000)[2], True)    # bar = 50000
        self.assertEqual(burst_rule(60000, 1, {}, NOW, s, 2000000)[2], False)  # bar = 100000
        self.assertEqual(burst_rule(100000, 1, {}, NOW, s, 2000000)[2], True)

    def test_defaults(self):
        self.assertEqual(GAME_DEFAULTS["boss_burst_cd"], 20)

    def test_small_hit_does_not_burst(self):
        self.assertEqual(burst_rule(49999, 1, {}, NOW, st()), (49999, False, False))

    def test_big_hit_bursts(self):
        self.assertEqual(burst_rule(50000, 1, {}, NOW, st()), (50000, False, True))

    def test_off_when_zero(self):
        self.assertEqual(burst_rule(10 ** 6, 1, {}, NOW, st(boss_burst_dmg=0, boss_burst_pct=0)), (10 ** 6, False, False))

    def test_cooldown_mode_never_reduces(self):
        ad = {"uid": 1, "until": NOW + 10}
        self.assertEqual(burst_rule(5000, 1, ad, NOW, st(boss_burst_mode=1)), (5000, False, False))

    def test_reduce_mode_halves_damage_of_the_adapted_player_only(self):
        ad = {"uid": 1, "until": NOW + 10}
        s = st(boss_burst_mode=2)
        self.assertEqual(burst_rule(8000, 1, ad, NOW, s), (4000, True, False))
        self.assertEqual(burst_rule(8000, 2, ad, NOW, s), (8000, False, False))  # someone else: full damage

    def test_reduction_ends(self):
        ad = {"uid": 1, "until": NOW - 1}
        self.assertEqual(burst_rule(8000, 1, ad, NOW, st(boss_burst_mode=2)), (8000, False, False))

    def test_reduced_hit_cannot_renew_the_state(self):
        ad = {"uid": 1, "until": NOW + 10}
        dmg, reduced, burst = burst_rule(30000, 1, ad, NOW, st(boss_burst_mode=3))
        self.assertEqual((dmg, reduced, burst), (15000, True, False))

    def test_texts_exist_in_both_languages_without_mixing(self):
        for lang in ("fa", "en"):
            for k in ("boss_burst_state", "boss_burst_alert", "boss_burst_cd", "boss_burst_red"):
                self.assertIn(k, LOCALES[lang], (lang, k))
        for k in ("boss_burst_state", "boss_burst_alert", "boss_burst_cd", "boss_burst_red"):
            self.assertFalse(any("a" <= c.lower() <= "z" for c in LOCALES["fa"][k].replace("<b>", "").replace("</b>", "").replace("{n}", "").replace("{boss}", "").replace("{s}", "")), k)


if __name__ == "__main__":
    unittest.main()
