"""Event battlefield maths (data_war): factions, sides, population balance, rally, anti-farming, rewards."""
import unittest

import data_war as W
from data_world import EVENTS

RACES = ("shinigami", "quincy", "hollow", "arrancar", "fullbringer", "human", "visored")


class Catalog(unittest.TestCase):
    def test_every_event_is_a_war(self):
        self.assertTrue(set(EVENTS) <= set(W.WARS), set(EVENTS) - set(W.WARS))
        self.assertTrue(set(W.WARS) <= set(W.WAR_STORY))

    def test_factions_complete(self):
        for kind, (a, b, ra, rb) in W.WARS.items():
            self.assertNotEqual(a, b)
            self.assertFalse(set(ra) & set(rb), kind)
            for f in (a, b):
                self.assertIn(f, W.FACTIONS)
                self.assertGreaterEqual(len(W.SOLDIERS[f]), 5)
                self.assertIn(f, W.OFFICERS)
                self.assertEqual(len(W.GENERALS[f]), 4)
            for r in tuple(ra) + tuple(rb):
                self.assertIn(r, RACES)

    def test_auto_side(self):
        self.assertEqual(W.auto_side("winter_war", "arrancar"), "a")
        self.assertEqual(W.auto_side("winter_war", "shinigami"), "b")
        self.assertIsNone(W.auto_side("winter_war", "quincy"))
        self.assertIsNone(W.auto_side("soul_festival", "shinigami"))
        self.assertEqual(W.auto_side("wandenreich", "quincy"), "a")

    def test_general_tiers(self):
        self.assertEqual(W.general_of("aizen", 10)[1], "Dordoni")
        self.assertEqual(W.general_of("aizen", 95)[1], "Sōsuke Aizen")


class Balance(unittest.TestCase):
    def test_equal_sides_are_neutral(self):
        self.assertEqual(W.balance(10, 10), 1.0)

    def test_bigger_side_does_not_win_by_size(self):
        # 30 fighters with 300 points against 10 fighters with 150: the smaller, harder-working side wins
        self.assertEqual(W.winner({"a": 300, "b": 150}, {"a": 30, "b": 10}), "b")

    def test_tiny_side_is_clamped(self):
        # 2 fighters cannot outweigh 50 by size alone
        self.assertEqual(W.winner({"a": 500, "b": 40}, {"a": 50, "b": 2}), "a")
        self.assertEqual(W.balance(1, 1000), W.BALANCE_MAX)
        self.assertEqual(W.balance(1000, 1), W.BALANCE_MIN)

    def test_empty_side_scores_nothing(self):
        self.assertEqual(W.weighed({"a": 9, "b": 3}, {"a": 0, "b": 1})["a"], 0)

    def test_shares(self):
        self.assertEqual(W.shares({}, {}), {"a": 50, "b": 50})
        s = W.shares({"a": 30, "b": 10}, {"a": 3, "b": 3})
        self.assertEqual(s["a"] + s["b"], 100)
        self.assertEqual(s["a"], 75)

    def test_draw(self):
        self.assertIsNone(W.winner({"a": 10, "b": 10}, {"a": 2, "b": 2}))


class Rally(unittest.TestCase):
    def test_side_behind_rallies(self):
        self.assertTrue(W.rally("b", {"a": 100, "b": 40}, {"a": 5, "b": 5}))
        self.assertFalse(W.rally("a", {"a": 100, "b": 40}, {"a": 5, "b": 5}))

    def test_no_rally_at_the_start(self):
        self.assertFalse(W.rally("b", {"a": 3, "b": 0}, {"a": 1, "b": 0}))

    def test_bonus(self):
        self.assertEqual(W.with_rally(3, True), 4)
        self.assertEqual(W.with_rally(10, True), 13)
        self.assertEqual(W.with_rally(3, False), 3)
        self.assertEqual(W.with_rally(0, True), 0)


class AntiFarm(unittest.TestCase):
    def test_repeat_wins_pay_less(self):
        self.assertEqual(W.shadow_points(60, 60, 0), 3)
        self.assertEqual(W.shadow_points(60, 60, 1), 1)
        self.assertEqual(W.shadow_points(60, 60, 2), 0)
        self.assertEqual(W.shadow_points(60, 60, 9), 0)

    def test_level_gap(self):
        self.assertEqual(W.shadow_points(60, 65, 0), 4)
        self.assertEqual(W.shadow_points(60, 55, 0), 2)


class Rewards(unittest.TestCase):
    def test_result_order(self):
        win = W.end_reward(50, 10, 10, "win")[1]
        fl = W.end_reward(50, 10, 10, "friendly_lose")[1]
        lose = W.end_reward(50, 10, 10, "lose")[1]
        self.assertGreater(win, fl)
        self.assertGreater(fl, lose)

    def test_performance_is_bounded(self):
        hi = W.end_reward(50, 1000, 1, "win")[1]
        self.assertEqual(hi, W.end_reward(50, 2000, 1, "win")[1])
        self.assertGreater(W.end_reward(50, 1, 100, "win")[1], 0)


if __name__ == "__main__":
    unittest.main()
