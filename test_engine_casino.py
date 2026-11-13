"""Bleach Casino checks (pure logic). Run: python -m unittest test_engine_casino -v"""
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine_casino as C  # noqa: E402


class LimitTests(unittest.TestCase):
    def test_bet_limits(self):
        self.assertEqual(C.validate_bet(C.MIN_BET - 1, 1), "too_small")
        self.assertIsNone(C.validate_bet(C.MIN_BET, 1))
        self.assertEqual(C.validate_bet(C.max_bet(1) + 1, 1), "too_big")

    def test_max_bet_grows_with_level(self):
        self.assertGreater(C.max_bet(50), C.max_bet(1))


class DiceTests(unittest.TestCase):
    def test_bad_pick_rejected(self):
        with self.assertRaises(ValueError):
            C.reiatsu_dice(100, "left", random.Random(1))

    def test_payout_and_loss_consistent(self):
        rng = random.Random(2)
        for _ in range(500):
            r = C.reiatsu_dice(100, rng.choice(["over", "under"]), rng)
            if r["won"]:
                self.assertEqual(r["net"], int(100 * C.REIATSU_PAYOUT) - 100)
            else:
                self.assertEqual(r["net"], -100)

    def test_dice_house_edge(self):
        rng = random.Random(3)
        n = 100_000
        total = 0
        for _ in range(n):
            total += C.reiatsu_dice(100, "over", rng)["net"]
        self.assertLess(total / n, 0)          # the player loses on average
        self.assertGreater(total / n, -10)     # but not absurdly


class HiLoTests(unittest.TestCase):
    def test_multiplier_grows(self):
        self.assertLess(C.hilo_multiplier(1), C.hilo_multiplier(2))

    def test_guess_validation(self):
        rng = random.Random(4)
        with self.assertRaises(ValueError):
            C.hilo_play(100, [], rng)
        with self.assertRaises(ValueError):
            C.hilo_play(100, ["up"], rng)
        with self.assertRaises(ValueError):
            C.hilo_play(100, ["hi"] * (C.HILO_MAX_STEPS + 1), rng)

    def test_losing_round_loses_bet(self):
        rng = random.Random(5)
        seen_loss = False
        for seed in range(200):
            r = C.hilo_play(100, ["hi", "hi"], random.Random(seed))
            if not r["won"]:
                self.assertEqual(r["net"], -100)
                seen_loss = True
        self.assertTrue(seen_loss)

    def test_winning_payout(self):
        for seed in range(300):
            r = C.hilo_play(100, ["hi"], random.Random(seed))
            if r["won"]:
                self.assertEqual(r["payout"], int(100 * C.hilo_multiplier(1)))
                return
        self.fail("no win found in 300 seeds")


class SlotsTests(unittest.TestCase):
    def test_return_rate_under_one(self):
        rtp = C.expected_return_slots(samples=100_000, seed=7)
        self.assertLess(rtp, 1.0)
        self.assertGreater(rtp, 0.5)

    def test_triple_pays_table(self):
        rng = random.Random(8)
        for _ in range(5000):
            r = C.slots_spin(10, rng)
            reels = r["reels"]
            if reels[0] == reels[1] == reels[2]:
                self.assertEqual(r["mult"], C.TRIPLE_PAY[reels[0]])


class Shinigami21Tests(unittest.TestCase):
    def test_bad_action_rejected(self):
        with self.assertRaises(ValueError):
            C.shinigami21(100, ["double"], random.Random(1))

    def test_payout_matches_result(self):
        rng = random.Random(9)
        for _ in range(2000):
            r = C.shinigami21(100, ["hit", "hit", "stand"], rng)
            expected = {"bust": 0, "lose": 0, "push": 100, "win": 200, "natural": 250}[r["result"]]
            self.assertEqual(r["payout"], expected)
            self.assertEqual(r["net"], expected - 100)

    def test_dealer_stands_at_17_or_more(self):
        rng = random.Random(10)
        for _ in range(2000):
            r = C.shinigami21(100, ["stand"], rng)
            if r["result"] != "natural":
                self.assertGreaterEqual(C._hand_total(r["dealer"]), 17)

    def test_ace_counts_as_one_when_needed(self):
        self.assertEqual(C._hand_total([1, 10, 5]), 16)
        self.assertEqual(C._hand_total([1, 10]), 21)

    def test_house_edge_is_positive(self):
        rng = random.Random(11)
        n = 60_000
        total = sum(C.shinigami21(100, ["hit"] * 1 + ["stand"], rng)["net"] for _ in range(n))
        self.assertLess(total / n, 0.5)  # a fixed simple strategy should not be a money machine


class DeepCasinoTests(unittest.TestCase):
    def test_roulette_validation(self):
        with self.assertRaises(ValueError):
            C.roulette_spin(10, "number", 40, random.Random(1))
        with self.assertRaises(ValueError):
            C.roulette_spin(10, "blue", None, random.Random(1))

    def test_roulette_house_edge_small(self):
        rng = random.Random(12)
        n = 100_000
        total = sum(C.roulette_spin(10, "red", None, rng)["net"] for _ in range(n))
        self.assertLess(total / n, 0)
        self.assertGreater(total / n, -0.6)

    def test_crash_return_near_97_percent(self):
        rng = random.Random(13)
        n = 200_000
        total = 0
        for _ in range(n):
            total += C.crash_play(100, 2.0, rng)["payout"]
        self.assertAlmostEqual(total / (n * 100), 0.97, delta=0.02)

    def test_crash_no_cashout_always_loses(self):
        r = C.crash_play(100, None, random.Random(14))
        self.assertFalse(r["won"])
        self.assertEqual(r["net"], -100)

    def test_jackpot_draw_weighted(self):
        tickets = {1: 0, 2: 1000, 3: 0}
        w = C.jackpot_draw(10_000, tickets, random.Random(15))
        self.assertEqual(w["uid"], 2)
        self.assertIsNone(C.jackpot_draw(10_000, {}, random.Random(16)))

    def test_jackpot_feed(self):
        self.assertEqual(C.jackpot_feed(0, 1000), int(1000 * C.JACKPOT_FEED))

    def test_vip_rebate_only_on_loss(self):
        self.assertEqual(C.rebate(-500, 1_000_000), 0)
        self.assertGreater(C.rebate(10_000, 6_000_000), 0)
        self.assertEqual(C.vip_tier(0), 0)
        self.assertEqual(C.vip_tier(60_000_000), len(C.VIP_TIERS) - 1)

    def test_cool_off_after_losing_streak(self):
        self.assertTrue(C.should_cool_off([True] + [False] * C.STREAK_COOLOFF_LOSSES))
        self.assertFalse(C.should_cool_off([False] * (C.STREAK_COOLOFF_LOSSES - 1)))

    def test_ledger_summary(self):
        es = [C.ledger_entry("dice", 100, 90, 1), C.ledger_entry("dice", 100, -100, 2)]
        s = C.ledger_summary(es)
        self.assertEqual(s["rounds"], 2)
        self.assertEqual(s["wagered"], 200)
        self.assertEqual(s["net"], -10)
        self.assertEqual(s["win_rate"], 0.5)


if __name__ == "__main__":
    unittest.main()
