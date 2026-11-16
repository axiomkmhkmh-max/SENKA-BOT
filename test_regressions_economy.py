"""Regression checks for money bugs found in review (pure logic, no MongoDB / Telegram needed).

Run:  python -m unittest test_regressions_economy -v
"""
import unittest

import engine_bank as B
import engine_casino as C


class LoanDueDateTests(unittest.TestCase):
    def test_late_repay_is_not_on_time(self):
        acc = B.new_account()
        B.deposit(acc, 10_000)
        B.take_loan(acc, 1000, 300, day=1)
        r = B.repay_loan(acc, day=1 + B.LOAN_DEFAULT_DAYS + 3)
        self.assertTrue(r["ok"])
        self.assertEqual(r["credit"], B.CREDIT_START + 5)  # late: small bump only, not +25

    def test_on_time_repay_still_pays_the_full_bump(self):
        acc = B.new_account()
        B.deposit(acc, 10_000)
        B.take_loan(acc, 1000, 300, day=1)
        r = B.repay_loan(acc, day=3)
        self.assertEqual(r["credit"], B.CREDIT_START + 25)

    def test_default_timer_counts_from_the_loan_start(self):
        acc = B.new_account()
        B.take_loan(acc, 1000, 300, day=1)
        B.repay_loan(acc, day=4)  # fails (no money) but accrues the loan in memory
        self.assertIsNotNone(B.check_default(acc, day=1 + B.LOAN_DEFAULT_DAYS))


class HiLoEdgeTests(unittest.TestCase):
    def test_every_step_keeps_the_house_edge(self):
        # whatever the card, the expected return of a guess is 0.95 x bet, so reading the card gives no advantage
        for card in range(1, 14):
            for guess in ("hi", "lo"):
                p = C.hilo_win_chance(card, guess)
                if p == 0:
                    continue
                ev = p * C.hilo_step_factor(card, guess)
                self.assertAlmostEqual(ev, 0.95, delta=0.001, msg=(card, guess))

    def test_likely_guess_pays_less_per_step(self):
        self.assertLess(C.hilo_step_factor(1, "hi"), C.hilo_step_factor(7, "hi"))


if __name__ == "__main__":
    unittest.main()


class ShopBulkTests(unittest.TestCase):
    def test_discount_tiers(self):
        import config
        from engine_shop import bulk_discount
        st = config.GAME_DEFAULTS
        self.assertEqual(bulk_discount(1, st), 0)
        self.assertEqual(bulk_discount(5, st), st["shop_disc_5"])
        self.assertEqual(bulk_discount(10, st), st["shop_disc_10"])
        self.assertEqual(bulk_discount(25, st), st["shop_disc_25"])
        self.assertLess(bulk_discount(25, {"shop_disc_25": 5}), 1)  # a typo in `set` can never make it free
