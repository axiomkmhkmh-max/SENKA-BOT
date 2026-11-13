"""Bleach Bank checks (pure logic). Run: python -m unittest test_engine_bank -v"""
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine_bank as B  # noqa: E402


class AccountTests(unittest.TestCase):
    def test_tiers_by_balance(self):
        self.assertEqual(B.tier_for(0), 0)
        self.assertEqual(B.tier_for(60_000), 1)
        self.assertEqual(B.tier_for(10_000_000), 3)

    def test_deposit_rejects_non_positive(self):
        with self.assertRaises(ValueError):
            B.deposit(B.new_account(), 0)

    def test_withdraw_takes_fee(self):
        acc = B.new_account()
        B.deposit(acc, 1000)
        r = B.withdraw(acc, 500)
        self.assertTrue(r["ok"])
        self.assertEqual(r["fee"], int(500 * B.TIERS[0][2]))
        self.assertEqual(acc["balance"], 1000 - 500 - r["fee"])

    def test_withdraw_insufficient(self):
        acc = B.new_account()
        B.deposit(acc, 100)
        self.assertEqual(B.withdraw(acc, 1000)["reason"], "insufficient")


class InterestTests(unittest.TestCase):
    def test_interest_is_capped_per_day(self):
        acc = B.new_account()
        B.deposit(acc, 10_000_000)
        paid = B.accrue_interest(acc, 1)
        self.assertEqual(paid, B.INTEREST_CAP_PER_DAY)

    def test_no_double_payment_same_day(self):
        acc = B.new_account()
        B.deposit(acc, 10_000)
        B.accrue_interest(acc, 5)
        self.assertEqual(B.accrue_interest(acc, 5), 0)

    def test_empty_account_earns_nothing(self):
        acc = B.new_account()
        self.assertEqual(B.accrue_interest(acc, 10), 0)


class LoanTests(unittest.TestCase):
    def test_loan_over_limit_rejected(self):
        acc = B.new_account()
        r = B.take_loan(acc, 1000, 700, day=1)
        self.assertEqual(r["reason"], "over_limit")

    def test_one_loan_at_a_time(self):
        acc = B.new_account()
        self.assertTrue(B.take_loan(acc, 1000, 300, day=1)["ok"])
        self.assertEqual(B.take_loan(acc, 1000, 100, day=1)["reason"], "already_has_loan")

    def test_repay_clears_loan(self):
        acc = B.new_account()
        B.take_loan(acc, 1000, 300, day=1)
        r = B.repay_loan(acc, day=1)
        self.assertTrue(r["ok"])
        self.assertEqual(acc["loans"], [])

    def test_default_seizes_collateral(self):
        acc = B.new_account()
        B.take_loan(acc, 1000, 300, day=1)
        self.assertIsNone(B.check_default(acc, day=1 + B.LOAN_DEFAULT_DAYS - 1))
        d = B.check_default(acc, day=1 + B.LOAN_DEFAULT_DAYS)
        self.assertEqual(d["seized"], 1000)
        self.assertEqual(acc["loans"], [])


class RaidTests(unittest.TestCase):
    def test_small_vault_never_raided(self):
        acc = B.new_account()
        B.deposit(acc, 1000)
        rng = random.Random(1)
        self.assertTrue(all(B.raid_roll(acc, rng) is None for _ in range(500)))

    def test_insurance_reduces_loss(self):
        base = B.new_account()
        B.deposit(base, 10_000_000)
        raided_plain = None
        for seed in range(2000):
            acc = {**base, "loans": [], "balance": base["balance"]}
            r = B.raid_roll(acc, random.Random(seed))
            if r:
                raided_plain = r["lost"]
                break
        self.assertIsNotNone(raided_plain)

        ins = {**base, "balance": base["balance"], "insured_days": 3}
        for seed in range(2000):
            acc = {**ins, "balance": ins["balance"], "insured_days": 3}
            r = B.raid_roll(acc, random.Random(seed))
            if r:
                self.assertTrue(r["insured"])
                self.assertLess(r["lost"], raided_plain)
                return
        self.fail("no raid found for insured account")

    def test_buy_insurance_costs_and_counts(self):
        acc = B.new_account()
        B.deposit(acc, 100_000)
        r = B.buy_insurance(acc, 2)
        self.assertTrue(r["ok"])
        self.assertEqual(acc["insured_days"], 2)
        self.assertLess(acc["balance"], 100_000)


class DeepBankTests(unittest.TestCase):
    def test_collectors_take_capped_share_each_day(self):
        acc = B.new_account()
        B.deposit(acc, 1_000_000)
        B.assign_collectors(acc, owed=500_000, day=1)
        r = B.collect_daily(acc, day=2)
        self.assertEqual(r["taken"], B.COLLECTOR_DAILY_CAP)
        self.assertFalse(r["done"])

    def test_collectors_finish_after_window(self):
        acc = B.new_account()
        B.deposit(acc, 100)
        B.assign_collectors(acc, owed=10_000_000, day=1)
        r = B.collect_daily(acc, day=1 + B.COLLECTOR_DAYS + 1)
        self.assertTrue(r["done"])
        self.assertIsNone(acc["collectors"])

    def test_upgrade_needs_money_and_is_not_repeatable(self):
        acc = B.new_account()
        self.assertEqual(B.upgrade_vault(acc, 1)["reason"], "insufficient")
        B.deposit(acc, 40_000)
        r = B.upgrade_vault(acc, 1)
        self.assertTrue(r["ok"])
        self.assertEqual(B.upgrade_vault(acc, 1)["reason"], "not_needed")

    def test_upgrade_lapses_when_balance_drops(self):
        acc = B.new_account()
        acc["upgraded_to"] = 2
        acc["balance"] = 100
        self.assertEqual(B.effective_tier(acc), 0)
        acc["balance"] = 500_000
        self.assertEqual(B.effective_tier(acc), 2)


class VeryDeepBankTests(unittest.TestCase):
    def test_credit_limit_grows(self):
        self.assertLess(B.credit_limit_pct(300), B.credit_limit_pct(850))
        self.assertAlmostEqual(B.credit_limit_pct(850), 0.6)

    def test_repay_on_time_raises_credit(self):
        acc = B.new_account()
        B.deposit(acc, 10_000)
        B.take_loan(acc, 1000, 300, day=1)
        r = B.repay_loan(acc, day=2)
        self.assertGreater(r["credit"], B.CREDIT_START)

    def test_default_lowers_credit(self):
        acc = B.new_account()
        B.take_loan(acc, 1000, 300, day=1)
        B.check_default(acc, day=1 + B.LOAN_DEFAULT_DAYS)
        self.assertLess(acc["credit"], B.CREDIT_START)

    def test_bond_matures_with_interest(self):
        acc = B.new_account()
        B.deposit(acc, 10_000)
        B.open_bond(acc, 5_000, 7, day=1)
        self.assertEqual(B.mature_bonds(acc, day=3), 0)
        self.assertGreater(B.mature_bonds(acc, day=8), 5_000)

    def test_early_bond_break_penalty(self):
        acc = B.new_account()
        B.deposit(acc, 10_000)
        B.open_bond(acc, 5_000, 30, day=1)
        r = B.break_bond(acc, 0)
        self.assertEqual(r["penalty"], 1_000)
        self.assertEqual(acc["bonds"], [])

    def test_transfer_fee_and_insufficient(self):
        a, b = B.new_account(), B.new_account()
        B.deposit(a, 10_000)
        r = B.transfer(a, b, 1000, random.Random(1))
        self.assertEqual(r["fee"], 10)
        self.assertEqual(b["balance"], 1000)
        self.assertEqual(B.transfer(a, b, 10**9, random.Random(1))["reason"], "insufficient")

    def test_big_transfer_can_be_audited(self):
        audited = False
        for seed in range(200):
            a, b = B.new_account(), B.new_account()
            B.deposit(a, 1_000_000)
            if B.transfer(a, b, 300_000, random.Random(seed))["audit"]:
                audited = True
                break
        self.assertTrue(audited)

    def test_security_reduces_raid_chance(self):
        acc = B.new_account()
        B.deposit(acc, 1_000_000)
        before = B.raid_multiplier(acc)
        B.deposit(acc, 25_000)
        self.assertTrue(B.buy_security(acc)["ok"])
        self.assertLess(B.raid_multiplier(acc), before)

    def test_espada_only_hits_top_tiers(self):
        acc = B.new_account()
        B.deposit(acc, 1000)
        self.assertTrue(all(B.espada_roll(acc, random.Random(s)) is None for s in range(3000)))

    def test_ledger_keeps_last_50(self):
        acc = B.new_account()
        for i in range(60):
            B.ledger(acc, "dep", 1, i)
        self.assertEqual(len(acc["ledger"]), 50)
        self.assertEqual(B.statement(acc)["entries"], 50)


if __name__ == "__main__":
    unittest.main()
