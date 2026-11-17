"""Bond books raise the bond of the chosen blade (the key the Zanpakuto panel reads), not the weapon in hand.
No MongoDB needed: the database layer is replaced by fakes. Run: python -m unittest test_bond_book -v"""
import asyncio
import os
import sys
import types
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

CH = {}
CALLS = []
REMOVED = []


class _Col:
    async def update_one(self, flt, upd):
        CALLS.append(upd)


def _install_stubs():
    def mod(name, **attrs):
        m = types.ModuleType(name)
        m.__dict__.update(attrs)
        sys.modules[name] = m

    async def _noop(*a, **k):
        return None

    async def get_char(uid):
        return CH

    mod("pymongo", ReturnDocument=types.SimpleNamespace(AFTER=1, BEFORE=0))
    mod("database", col=lambda name: _Col(), game_settings=_noop, try_cooldown=_noop)
    mod("service_log", log_event=_noop)
    mod("service_player", add_coins=_noop, add_xp=_noop, bump_quest=_noop, get_char=get_char)
    mod("service_worldcore", mods_for=_noop)


_install_stubs()
import service_economy as E  # noqa: E402
from data_items import ALL  # noqa: E402

BOND_ITEMS = [i for i, it in ALL.items() if (it.get("effect") or {}).get("type") == "bond"]


async def _remove(uid, item_id, qty=1):
    REMOVED.append(item_id)
    return True


E.inv_remove = _remove


class BondBookTests(unittest.TestCase):
    def setUp(self):
        CALLS.clear()
        REMOVED.clear()
        self.item = BOND_ITEMS[0]
        self.amount = ALL[self.item]["effect"]["amount"]

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
