"""Xcution membership and rank, siphon and absorption caps (pure logic).
Run: python -m unittest test_xcution_bount -v"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_gangs import (SIPHON_DAILY_CAP, XCUTION_REJOIN_SECONDS, ABSORB_DAILY_CAP, absorb_coins, can_join_xcution,  # noqa: E402
                        siphon_gain, xcution_dmg_mult, xcution_rank, xcution_rank_name)


class RankTests(unittest.TestCase):
    def test_rank_rises_with_points(self):
        self.assertEqual(xcution_rank(0), 0)
        self.assertEqual(xcution_rank(40), 1)
        self.assertEqual(xcution_rank(120), 2)
        self.assertEqual(xcution_rank(700), 4)
        self.assertEqual(xcution_rank(10 ** 6), 4)

    def test_rank_never_falls_when_points_are_monotonic(self):
        prev = -1
        for p in range(0, 1000, 7):
            r = xcution_rank(p)
            self.assertGreaterEqual(r, prev)
            prev = r

    def test_rank_names_exist_in_both_languages(self):
        self.assertTrue(xcution_rank_name(0, "fa"))
        self.assertTrue(xcution_rank_name(0, "en"))


class DamageTests(unittest.TestCase):
    def test_non_members_get_no_bonus(self):
        self.assertEqual(xcution_dmg_mult({"xcution": {"joined": False, "points": 999}}), 1.0)
        self.assertEqual(xcution_dmg_mult({}), 1.0)

    def test_members_get_two_percent_per_rank(self):
        self.assertAlmostEqual(xcution_dmg_mult({"xcution": {"joined": True, "points": 0}}), 1.0)
        self.assertAlmostEqual(xcution_dmg_mult({"xcution": {"joined": True, "points": 120}}), 1.04)


class MembershipTests(unittest.TestCase):
    def test_only_fullbringers_at_the_hideout_can_join(self):
        ok = {"race": "fullbringer", "xcution": {}}
        self.assertTrue(can_join_xcution(ok, "xcution_hideout", now=10 ** 9))
        self.assertFalse(can_join_xcution(ok, "karakura", now=10 ** 9))
        self.assertFalse(can_join_xcution({"race": "shinigami", "xcution": {}}, "xcution_hideout", now=10 ** 9))

    def test_members_cannot_join_twice(self):
        self.assertFalse(can_join_xcution({"race": "fullbringer", "xcution": {"joined": True}}, "xcution_hideout", now=10 ** 9))

    def test_rejoin_waits_after_leaving(self):
        left = 10 ** 9
        ch = {"race": "fullbringer", "xcution": {"joined": False, "left_at": left}}
        self.assertFalse(can_join_xcution(ch, "xcution_hideout", now=left + XCUTION_REJOIN_SECONDS - 1))
        self.assertTrue(can_join_xcution(ch, "xcution_hideout", now=left + XCUTION_REJOIN_SECONDS))


class SiphonTests(unittest.TestCase):
    def test_elite_wins_give_more(self):
        self.assertGreater(siphon_gain(20, True, 0), siphon_gain(20, False, 0))

    def test_daily_cap_is_never_passed(self):
        self.assertEqual(siphon_gain(100, True, SIPHON_DAILY_CAP), 0)
        self.assertLessEqual(siphon_gain(100, True, SIPHON_DAILY_CAP - 5), 5)

    def test_gain_is_never_negative(self):
        self.assertGreaterEqual(siphon_gain(1, False, 10 ** 6), 0)


class AbsorptionTests(unittest.TestCase):
    def test_higher_level_absorbs_more(self):
        self.assertGreater(absorb_coins(50, 0), absorb_coins(5, 0))

    def test_daily_cap_is_never_passed(self):
        self.assertEqual(absorb_coins(90, ABSORB_DAILY_CAP), 0)
        self.assertLessEqual(absorb_coins(90, ABSORB_DAILY_CAP - 10), 10)


if __name__ == "__main__":
    unittest.main()


from data_gangs import XCUTION_BOSS_REWARD, XCUTION_BOSS_TARGET, boss_defeated, boss_week_key  # noqa: E402


class BossTests(unittest.TestCase):
    def test_week_starts_on_monday(self):
        # 2026-11-16 is a Monday, 2026-11-22 the Sunday of the same week
        self.assertEqual(boss_week_key("2026-11-16"), boss_week_key("2026-11-22"))
        self.assertNotEqual(boss_week_key("2026-11-15"), boss_week_key("2026-11-16"))

    def test_boss_falls_at_the_target_and_not_before(self):
        self.assertFalse(boss_defeated(XCUTION_BOSS_TARGET - 1))
        self.assertTrue(boss_defeated(XCUTION_BOSS_TARGET))
        self.assertTrue(boss_defeated(XCUTION_BOSS_TARGET + 10))

    def test_reward_is_positive(self):
        self.assertGreater(XCUTION_BOSS_REWARD, 0)

    def test_missing_wins_count_as_zero(self):
        self.assertFalse(boss_defeated(None))
