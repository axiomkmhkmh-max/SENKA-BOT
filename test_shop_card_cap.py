"""Urahara's skill cards: a per-player daily cap (shop_card_daily), taken atomically, given back when the purchase fails.
The database is faked in memory; the fake mimics Mongo's upsert-on-a-failed-filter -> DuplicateKeyError."""
import asyncio
import sys
import types
import unittest

try:
    import pymongo.errors as _pe
    DupKey = _pe.DuplicateKeyError
except ImportError:  # no pymongo in this sandbox: stand one in so the module under test can import it
    DupKey = type("DuplicateKeyError", (Exception,), {})
    _pm = types.ModuleType("pymongo")
    _pm.errors = types.ModuleType("pymongo.errors")
    _pm.errors.DuplicateKeyError = DupKey
    _pm.ReturnDocument = types.SimpleNamespace(AFTER=1, BEFORE=0)
    _pm.ASCENDING, _pm.DESCENDING, _pm.UpdateOne = 1, -1, object
    sys.modules.setdefault("pymongo", _pm)
    sys.modules.setdefault("pymongo.errors", _pm.errors)

try:
    import motor.motor_asyncio  # noqa: F401
except ImportError:
    _m = types.ModuleType("motor")
    _m.motor_asyncio = types.ModuleType("motor.motor_asyncio")
    _m.motor_asyncio.AsyncIOMotorClient = object
    sys.modules.setdefault("motor", _m)
    sys.modules.setdefault("motor.motor_asyncio", _m.motor_asyncio)

try:
    import aiogram  # noqa: F401
except ImportError:  # the logger only needs aiogram for its Telegram error types: stand it in
    _sl = types.ModuleType("service_log")
    _sl.log_event = lambda *a, **k: None
    sys.modules.setdefault("service_log", _sl)

import service_economy as se  # noqa: E402


class FakeCol:
    def __init__(self):
        self.docs = {}

    async def update_one(self, flt, upd, upsert=False):
        d = self.docs.get(flt["_id"])
        ok = d is not None and all(d.get(k, 0) <= v["$lte"] for k, v in flt.items() if isinstance(v, dict) and "$lte" in v)
        if d is None and upsert:
            self.docs[flt["_id"]] = dict(upd["$inc"])
        elif d is not None and (ok or "n" not in flt or not isinstance(flt["n"], dict)):
            if ok:
                for k, v in upd["$inc"].items():
                    d[k] = d.get(k, 0) + v
            else:
                raise DupKey()
        elif d is not None and upsert:
            raise DupKey()

    async def find_one(self, flt):
        return self.docs.get(flt["_id"])


CARD = next(i for i, x in se.ALL.items() if x["category"] in ("ability_card", "kido_card"))
POTION = next(i for i, x in se.ALL.items() if x["category"] == "potion")


class CardCap(unittest.TestCase):
    def setUp(self):
        self.fc = FakeCol()
        self._col, self._gs = se.col, se.game_settings
        se.col = lambda name: self.fc

        async def gs():
            return {"shop_card_daily": 5}
        se.game_settings = gs

    def tearDown(self):
        se.col, se.game_settings = self._col, self._gs

    def run_(self, coro):
        return asyncio.new_event_loop().run_until_complete(coro)

    def test_cap_is_five_a_day(self):
        self.assertTrue(self.run_(se._card_quota_take(1, CARD, "d1", 5)))
        self.assertFalse(self.run_(se._card_quota_take(1, CARD, "d1", 1)))
        self.assertEqual(self.run_(se.shop_card_left(1, "d1")), 0)

    def test_order_over_the_cap_is_refused_whole(self):
        self.assertTrue(self.run_(se._card_quota_take(1, CARD, "d1", 3)))
        self.assertFalse(self.run_(se._card_quota_take(1, CARD, "d1", 3)))
        self.assertEqual(self.run_(se.shop_card_left(1, "d1")), 2)

    def test_next_day_and_other_player_are_free(self):
        self.run_(se._card_quota_take(1, CARD, "d1", 5))
        self.assertTrue(self.run_(se._card_quota_take(1, CARD, "d2", 5)))
        self.assertTrue(self.run_(se._card_quota_take(2, CARD, "d1", 5)))

    def test_give_back_after_failed_purchase(self):
        self.run_(se._card_quota_take(1, CARD, "d1", 5))
        self.run_(se._card_quota_give(1, CARD, "d1", 5))
        self.assertEqual(self.run_(se.shop_card_left(1, "d1")), 5)

    def test_other_goods_are_never_limited(self):
        for _ in range(10):
            self.assertTrue(self.run_(se._card_quota_take(1, POTION, "d1", 25)))


if __name__ == "__main__":
    unittest.main()
