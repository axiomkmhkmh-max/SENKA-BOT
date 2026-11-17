"""Race weapons: ten per race, one item per colour, the mandatory choice at the old blade's level, ascension and the
Rebirth Seal switch. The database is faked. Run: python -m unittest test_race_weapons -v"""
import asyncio
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _stubs import import_with_stubs  # noqa: E402

S = import_with_stubs("service_raceweapon")
from data_items import ALL, WEAPON_BY_RARITY  # noqa: E402
from data_raceweapons import RACE_WEAPONS, parse_rw, rw_id  # noqa: E402
from data_zanpakuto import bond_key  # noqa: E402

CH = {}
INV = {}


class _Chars:
    async def update_one(self, flt, upd):
        for k, v in flt.items():
            if k == "_id" or k == "user_id":
                continue
            if CH.get(k) != v:
                return type("R", (), {"modified_count": 0})()
        for k, v in (upd.get("$set") or {}).items():
            if "." in k:
                a, b = k.split(".", 1)
                CH.setdefault(a, {})[b] = v
            else:
                CH[k] = v
        for k in (upd.get("$unset") or {}):
            if "." in k:
                a, b = k.split(".", 1)
                (CH.get(a) or {}).pop(b, None)
            else:
                CH.pop(k, None)
        for k, v in (upd.get("$max") or {}).items():
            a, b = k.split(".", 1)
            CH.setdefault(a, {})[b] = max(CH.get(a, {}).get(b, 0), v)
        return type("R", (), {"modified_count": 1})()


async def _get_char(uid):
    return dict(CH) if CH else None


async def _inv_remove(uid, iid, q=1):
    if INV.get(iid, 0) >= q:
        INV[iid] -= q
        return True
    return False


class RaceWeaponTests(unittest.TestCase):
    def setUp(self):
        CH.clear()
        INV.clear()
        self._saved = {k: getattr(S, k) for k in ("col", "get_char", "inv_remove")}
        S.col, S.get_char, S.inv_remove = (lambda n: _Chars()), _get_char, _inv_remove

    def tearDown(self):
        for k, v in self._saved.items():
            setattr(S, k, v)

    def test_ten_weapons_per_race_and_every_colour_exists(self):
        for race, ws in RACE_WEAPONS.items():
            self.assertEqual(len(ws), 10, race)
            for n in range(10):
                for c in range(6):
                    it = ALL[rw_id(race, n, c)]
                    self.assertEqual(it["race"], race)
                    self.assertFalse(it["tradeable"])
        self.assertTrue(all(not v for v in WEAPON_BY_RARITY.values()))  # blades no longer drop

    def test_offer_matches_the_blade_in_hand(self):
        CH.update({"user_id": 1, "race": "quincy", "weapon_id": "wp_090", "weapon_plus": {"wp_090": 4}, "bond": {"wp_090": 77}})
        lvl = S.offer_level(CH)
        self.assertEqual(lvl["c"], ["Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythic"].index(ALL["wp_090"]["rarity"]))
        self.assertEqual(lvl["plus"], 4)
        self.assertEqual(lvl["bond"], 77)

    def test_choice_is_mandatory_then_taken_at_that_level(self):
        CH.update({"user_id": 1, "race": "hollow", "weapon_id": None, "rw_pending": {"c": 3, "plus": 6, "bond": 40}})
        self.assertTrue(S.needs_choice(CH))
        status, iid = asyncio.run(S.choose(1, 2))
        self.assertEqual(status, "ok")
        self.assertEqual(parse_rw(iid), ("hollow", 2, 3))
        self.assertEqual(CH["weapon_plus"][iid], 6)
        self.assertEqual(CH["bond"]["rw_hollow_02"], 40)
        self.assertNotIn("rw_pending", CH)
        self.assertFalse(S.needs_choice(CH))
        self.assertEqual(bond_key(CH), "rw_hollow_02")

    def test_switch_needs_a_seal_and_keeps_level(self):
        CH.update({"user_id": 1, "race": "human", "weapon_id": rw_id("human", 0, 2), "weapon_plus": {rw_id("human", 0, 2): 5},
                   "bond": {"rw_human_00": 30}})
        status, _ = asyncio.run(S.switch_type(1, 4))
        self.assertEqual(status, "seal")
        INV[S.REBIRTH_SEAL] = 1
        status, iid = asyncio.run(S.switch_type(1, 4))
        self.assertEqual(status, "ok")
        self.assertEqual(iid, rw_id("human", 4, 2))
        self.assertEqual(CH["weapon_plus"][iid], 5)
        self.assertEqual(CH["bond"]["rw_human_04"], 30)

    def test_race_change_reopens_the_choice(self):
        CH.update({"user_id": 1, "race": "arrancar", "weapon_id": rw_id("quincy", 1, 4), "weapon_plus": {rw_id("quincy", 1, 4): 7}})
        asyncio.run(S.on_race_change(1, "quincy", "arrancar"))
        self.assertIsNone(CH["weapon_id"])
        self.assertEqual(CH["rw_pending"]["c"], 4)
        self.assertEqual(CH["rw_pending"]["plus"], 7)

    def test_ascend_need(self):
        CH.update({"race": "shinigami", "weapon_id": rw_id("shinigami", 0, 5)})
        self.assertIsNone(S.ascend_need(CH))
        CH["weapon_id"] = rw_id("shinigami", 0, 1)
        colour, gate, need, tier, coins = S.ascend_need(CH)
        self.assertEqual((colour, need), (2, 2))


if __name__ == "__main__":
    unittest.main()
