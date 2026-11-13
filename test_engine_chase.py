"""Hollow Chase checks (pure logic). Run: python -m unittest test_engine_chase -v"""
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine_chase as E  # noqa: E402


class ChaseFlowTests(unittest.TestCase):
    def test_correct_majority_advances_and_catches(self):
        rng = random.Random(1)
        c = E.new_chase(rng)
        for _ in range(E.CATCH_AT):
            right = c["path"][c["round"]]
            r = E.resolve_round(c, {1: right, 2: right, 3: "left" if right != "left" else "right"}, rng)
            self.assertEqual(r["outcome"], "correct")
        self.assertEqual(c["status"], "caught")

    def test_wrong_majority_costs_stamina_and_repeats_round(self):
        rng = random.Random(2)
        c = E.new_chase(rng)
        right = c["path"][0]
        wrong = [d for d in E.DIRECTIONS if d != right][0]
        r = E.resolve_round(c, {1: wrong}, rng)
        self.assertEqual(r["outcome"], "wrong")
        self.assertEqual(c["round"], 0)
        self.assertEqual(c["stamina"], E.STAMINA - 1)

    def test_no_votes_costs_stamina(self):
        rng = random.Random(3)
        c = E.new_chase(rng)
        r = E.resolve_round(c, {}, rng)
        self.assertEqual(r["outcome"], "no_votes")
        self.assertEqual(c["stamina"], E.STAMINA - 1)

    def test_escape_when_stamina_gone(self):
        rng = random.Random(4)
        c = E.new_chase(rng)
        for _ in range(E.STAMINA):
            right = c["path"][c["round"]]
            wrong = [d for d in E.DIRECTIONS if d != right][0]
            E.resolve_round(c, {1: wrong}, rng)
        self.assertEqual(c["status"], "escaped")
        with self.assertRaises(ValueError):
            E.resolve_round(c, {1: "left"}, rng)

    def test_correct_votes_are_counted_per_player(self):
        rng = random.Random(5)
        c = E.new_chase(rng)
        right = c["path"][0]
        E.resolve_round(c, {7: right, 8: right, 9: "mid" if right != "mid" else "left"}, rng)
        self.assertEqual(c["correct_votes"], {"7": 1, "8": 1})


class HintAndSettleTests(unittest.TestCase):
    def test_hint_is_right_about_60_percent(self):
        rng = random.Random(6)
        c = E.new_chase(rng)
        right = c["path"][0]
        hits = sum(1 for _ in range(20000) if E.make_hint(c, rng) == right)
        self.assertAlmostEqual(hits / 20000, E.HINT_TRUE, delta=0.02)

    def test_settle_splits_pool_by_correct_votes(self):
        c = {"status": "caught", "correct_votes": {"1": 3, "2": 1}}
        s = E.settle(c, 400)
        self.assertEqual(s["payouts"], {"1": 300, "2": 100})
        self.assertEqual(s["mvp"], "1")

    def test_settle_pays_nothing_if_not_caught(self):
        self.assertEqual(E.settle({"status": "escaped", "correct_votes": {"1": 2}}, 400)["payouts"], {})

    def test_bigger_groups_pay_more_but_not_linearly(self):
        small = E.catch_pool(100, 100, 1)["coins"]
        big = E.catch_pool(100, 100, 8)["coins"]
        self.assertGreater(big, small)
        self.assertLess(big, small * 8)

    def test_majority_tie_is_random_among_leaders(self):
        seen = set()
        for s in range(200):
            seen.add(E.majority({1: "left", 2: "right"}, random.Random(s)))
        self.assertEqual(seen, {"left", "right"})


if __name__ == "__main__":
    unittest.main()
