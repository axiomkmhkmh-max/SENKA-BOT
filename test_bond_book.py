"""Bond books raise the bond of the chosen blade (the key the Zanpakuto panel reads), not the weapon in hand.
No MongoDB needed: the database layer is replaced by fakes. Run: python -m unittest test_bond_book -v"""
import asyncio
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _stubs import import_with_stubs  # noqa: E402

E = import_with_stubs("service_economy")
from data_items import ALL  # noqa: E402

CH = {}
CALLS = []
REMOVED = []
BOND_ITEMS = [i for i, it in ALL.items() if (it.get("effect") or {}).get("type") == "bond"]


class _Col:
    async def update_one(self, flt, upd):
        CALLS.append(upd)


async def _get_char(uid):
    return CH


async def _remove(uid, item_id, qty=1):
    REMOVED.append(item_id)
    return True


class BondBookTests(unittest.TestCase):
    def setUp(self):
        self._saved = {k: getattr(E, k) for k in ("get_char", "col", "inv_remove")}
        E.get_char, E.col, E.inv_remove = _get_char, (lambda name: _Col()), _remove
        CALLS.clear()
        REMOVED.clear()
        self.item = BOND_ITEMS[0]
        self.amount = ALL[self.item]["effect"]["amount"]

    def tearDown(self):
        for k, v in self._saved.items():
            setattr(E, k, v)

    def _use(self, ch):
        CH.clear()
        CH.update(ch)
        return asyncio.run(E.use_item(1, self.item))

    def test_there_is_a_bond_book(self):
        self.assertTrue(BOND_ITEMS)

    def test_chosen_blade_gets_the_bond_even_with_another_weapon_in_hand(self):
        res = self._use({"weapon_id": "wp_001", "zanpakuto": {"blade_id": "zangetsu"}, "bond": {}})
        self.assertEqual(res, ("ok", self.amount))
        self.assertEqual(CALLS, [{"$inc": {"bond.zangetsu": self.amount}}])

    def test_chosen_blade_gets_the_bond_with_no_weapon_in_hand(self):
        res = self._use({"weapon_id": None, "zanpakuto": {"blade_id": "hyorinmaru"}, "bond": {}})
        self.assertEqual(res[0], "ok")
        self.assertEqual(CALLS, [{"$inc": {"bond.hyorinmaru": self.amount}}])

    def test_no_blade_chosen_keeps_the_weapon_key(self):
        res = self._use({"weapon_id": "wp_002", "zanpakuto": {}, "bond": {}})
        self.assertEqual(res[0], "ok")
        self.assertEqual(CALLS, [{"$inc": {"bond.wp_002": self.amount}}])

    def test_nothing_to_bond_with_keeps_the_book(self):
        res = self._use({"weapon_id": None, "zanpakuto": {}, "bond": {}})
        self.assertEqual(res, ("nouse", None))
        self.assertEqual(REMOVED, [])
        self.assertEqual(CALLS, [])


if __name__ == "__main__":
    unittest.main()
