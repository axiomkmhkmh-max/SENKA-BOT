"""Coin transfer (reply command) and the bank fixes. No MongoDB / Telegram needed.

Run:  python -m unittest test_xfer -v
"""
import asyncio
import sys
import unittest
from unittest import mock


def _stub_missing_libs():
    """Run anywhere: when motor / pymongo / aiogram are not installed (e.g. a bare CI box) they are replaced by stand-ins.
    Nothing here talks to a real database or to Telegram."""
    for root in ("motor", "pymongo", "aiogram", "aiohttp"):
        try:
            __import__(root)
            continue
        except ImportError:
            pass
        for name in (root, f"{root}.motor_asyncio", f"{root}.errors", f"{root}.exceptions", f"{root}.types", f"{root}.enums",
                     f"{root}.client", f"{root}.client.default", f"{root}.filters", f"{root}.fsm", f"{root}.utils",
                     f"{root}.utils.keyboard", f"{root}.web"):
            sys.modules.setdefault(name, mock.MagicMock())
    err = sys.modules.get("pymongo.errors")
    if isinstance(err, mock.MagicMock):
        err.DuplicateKeyError = type("DuplicateKeyError", (Exception,), {})
    exc = sys.modules.get("aiogram.exceptions")
    if isinstance(exc, mock.MagicMock):
        for n in ("TelegramAPIError", "TelegramBadRequest", "TelegramForbiddenError", "TelegramRetryAfter"):
            setattr(exc, n, type(n, (Exception,), {}))


_stub_missing_libs()

import engine_bank as B
import engine_xfer as X
import service_bank as SB


class ParseTests(unittest.TestCase):
    def test_commands_that_must_parse(self):
        cases = {
            "انتقال 1000": 1000, "انتقال ۱۰۰۰": 1000, "انتقال ۱۰۰۰ سکه": 1000, "انتقال سکه 1000": 1000,
            "ارسال 2500 سکه": 2500, "بفرست ۵۰۰": 500, "انتقال 1,000": 1000, "انتقال ۱٬۰۰۰": 1000,
            "انتقال 5k": 5000, "انتقال 5K": 5000, "انتقال 5 هزار": 5000, "انتقال ۲ میلیون": 2_000_000,
            "انتقال 1.5m": 1_500_000, "transfer 1000": 1000, "Send 500 coins": 500, "pay 70 coin": 70,
            "  انتقال   1000  ": 1000, "انتقال 1000!": 1000,
        }
        for text, want in cases.items():
            self.assertEqual(X.parse_transfer(text), want, text)

    def test_normal_chat_is_never_a_transfer(self):
        for text in ["سلام", "انتقال", "انتقال بده", "انتقال 0", "انتقال 1.5", "من 1000 تا سکه دارم", "انتقال 1000 به علی",
                     "send it", "transfer", "انتقال -5", "انتقال 99999999999999999999", "بانک"]:
            self.assertIsNone(X.parse_transfer(text), text)

    def test_parse_number_for_prompts(self):
        self.assertEqual(X.parse_number("۱۲۳۴۵"), 12345)
        self.assertEqual(X.parse_number("5k"), 5000)
        self.assertEqual(X.parse_number("1,000"), 1000)
        self.assertIsNone(X.parse_number("abc"))
        self.assertIsNone(X.parse_number("0"))
        self.assertIsNone(X.parse_number("12 ab"))

    def test_fee_is_never_zero(self):
        self.assertEqual(X.fee_for(10, 0.05), 1)
        self.assertEqual(X.fee_for(1000, 0.05), 50)
        self.assertEqual(X.fee_for(1, 0.0), 1)


class BankFixTests(unittest.TestCase):
    def test_withdraw_fee_follows_a_paid_upgrade(self):
        acc = B.new_account()
        B.deposit(acc, 100_000)  # Seireitei tier by balance (3%)
        acc["upgraded_to"] = 2   # paid upgrade to the 2% tier, holds above 250k only -> lapses at 100k
        self.assertEqual(B.withdraw(dict(acc), 1000)["fee"], 30)
        acc["balance"] = 300_000
        self.assertEqual(B.withdraw(acc, 1000)["fee"], 20)

    def test_insurance_is_never_free_and_capped(self):
        acc = B.new_account()
        acc["balance"] = 10
        r = B.buy_insurance(acc, 3)
        self.assertTrue(r["ok"])
        self.assertGreaterEqual(r["cost"], 3)
        acc2 = B.new_account()
        B.deposit(acc2, 10_000_000)
        self.assertEqual(B.buy_insurance(acc2, B.MAX_INSURED_DAYS + 1)["reason"], "max_days")
        self.assertEqual(B.buy_insurance(acc2, 0)["reason"], "bad_amount")

    def test_upgrade_that_would_lapse_at_once_is_refused(self):
        acc = B.new_account()
        acc["balance"] = 30_000  # tier 2 costs 25,000 and needs 250,000 to hold: it would be wasted money
        r = B.upgrade_vault(acc, 2)
        self.assertFalse(r["ok"])
        self.assertEqual(acc["balance"], 30_000)
        self.assertIn(r["reason"], ("insufficient", "balance_low"))
        acc["balance"] = 300_000
        self.assertTrue(B.upgrade_vault(acc, 2)["ok"])

    def test_bank_transfer_fee_has_a_floor(self):
        a, b = B.new_account(), B.new_account()
        a["balance"] = 1000
        import random
        self.assertEqual(B.transfer(a, b, 10, random.Random(1))["fee"], 1)


# ---- wallet_transfer with an in-memory database ---------------------------------------------------------------------
class FakeCounters:
    def __init__(self):
        self.n = {}

    async def update_one(self, flt, upd):
        self.n[flt["key"]] = self.n.get(flt["key"], 0) + upd["$inc"]["n"]


class WalletTransferTests(unittest.TestCase):
    def setUp(self):
        self.chars = {1: {"user_id": 1, "level": 10, "coins": 10_000, "created_at": 0},
                      2: {"user_id": 2, "level": 1, "coins": 0, "created_at": 0}}
        self.counters = {}
        self.fail_credit = False
        self.st = {"xfer_fee_pct": 0.05, "xfer_daily_cap": 5000, "xfer_min_amount": 10, "xfer_min_level": 3,
                   "new_acct_minutes": 10}
        self.fc = FakeCounters()
        self.orig = (SB.get_char, SB.add_coins, SB.bump_counter, SB.game_settings, SB.col)

        async def get_char(uid):
            return self.chars.get(uid)

        async def add_coins(uid, n, reason=""):
            if n > 0 and self.fail_credit and uid == 2:
                return False
            ch = self.chars.get(uid)
            if not ch or (n < 0 and ch["coins"] < -n):
                return False
            ch["coins"] += n
            return True

        async def bump_counter(key, amount, cap, ttl=48):
            cur = self.fc.n.get(key, 0)
            if amount > cap or cur + amount > cap:
                return False
            self.fc.n[key] = cur + amount
            return True

        async def game_settings(force=False):
            return self.st

        SB.get_char, SB.add_coins, SB.bump_counter, SB.game_settings = get_char, add_coins, bump_counter, game_settings
        SB.col = lambda name: self.fc

    def tearDown(self):
        SB.get_char, SB.add_coins, SB.bump_counter, SB.game_settings, SB.col = self.orig

    def run_t(self, *a):
        return asyncio.run(SB.wallet_transfer(*a))

    def test_happy_path_moves_amount_and_charges_fee_on_top(self):
        r, err = self.run_t(1, 2, 1000)
        self.assertIsNone(err)
        self.assertEqual((r["sent"], r["fee"], r["total"]), (1000, 50, 1050))
        self.assertEqual(self.chars[1]["coins"], 10_000 - 1050)
        self.assertEqual(self.chars[2]["coins"], 1000)

    def test_refusals_move_nothing(self):
        for args, reason in [((1, 1, 100), "self"), ((1, 2, 0), "bad_amount"), ((1, 2, 5), "too_small"),
                             ((1, 99, 100), "no_target"), ((99, 2, 100), "no_sender"), ((1, 2, 10_000), "insufficient")]:
            r, err = self.run_t(*args)
            self.assertIsNone(r)
            self.assertEqual(err, reason, args)
        self.assertEqual(self.chars[1]["coins"], 10_000)
        self.assertEqual(self.chars[2]["coins"], 0)

    def test_a_refused_send_does_not_use_up_the_daily_cap(self):
        self.run_t(1, 2, 9_999)  # not enough coins with the fee
        self.assertEqual(self.fc.n.get("tr:1", 0), 0)

    def test_daily_cap(self):
        self.assertIsNone(self.run_t(1, 2, 4000)[1])
        self.assertEqual(self.run_t(1, 2, 2000)[1], "cap")

    def test_level_gate(self):
        self.chars[1]["level"] = 2
        self.assertEqual(self.run_t(1, 2, 100)[1], "low_level")

    def test_new_account_gate(self):
        import time
        self.chars[1]["created_at"] = int(time.time())
        self.assertEqual(self.run_t(1, 2, 100)[1], "new_acct")

    def test_failed_credit_refunds_everything(self):
        self.fail_credit = True
        r, err = self.run_t(1, 2, 1000)
        self.assertEqual(err, "busy")
        self.assertEqual(self.chars[1]["coins"], 10_000)
        self.assertEqual(self.fc.n.get("tr:1", 0), 0)


if __name__ == "__main__":
    unittest.main()
