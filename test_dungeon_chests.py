"""Dungeon chests pay coins AND an item, never lower than the chest's floor, with pity.
No MongoDB needed: the database layer is faked. Run: python -m unittest test_dungeon_chests -v"""
import asyncio
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _stubs import import_with_stubs  # noqa: E402

S = import_with_stubs("service_dungeonshop")

CHAR = {}
SETS = []
COINS = []
ITEMS = []
DROPS = []


class _Chars:
    async def find_one_and_update(self, flt, upd):
        dp = CHAR.get("dp", 0)
        if dp < flt["dp"]["$gte"]:
            return None
        CHAR["dp"] = dp + upd["$inc"]["dp"]
        return dict(CHAR)

    async def update_one(self, flt, upd):
        SETS.append(upd["$set"])


async def _settings():
    return {"dp_pity_bronze": 6, "dp_pity_silver": 5, "dp_pity_gold": 4}


async def _add_coins(uid, n, why):
    COINS.append(n)
    return True


async def _inv_add(uid, iid, qty=1, force=False):
    ITEMS.append((iid, force))
    return True


async def _roll_drop(uid, source_mult=1.0, weapon_chance=0.1, floor_idx=0, rng=random):
    DROPS.append({"floor": floor_idx, "weapon": weapon_chance})
    return f"item_{floor_idx}"


class _Forced:
    """rng that always picks the given choices index and the low end of ranges."""
    def __init__(self, pick):
        self.pick = pick

    def choices(self, population, weights=None, k=1):
        return [population[self.pick]]

    def randint(self, a, b):
        return a


class ChestTests(unittest.TestCase):
    def setUp(self):
        CHAR.clear()
        for lst in (SETS, COINS, ITEMS, DROPS):
            lst.clear()
        self._saved = {k: getattr(S, k) for k in ("col", "game_settings", "add_coins", "inv_add", "roll_drop", "log_event")}
        S.col, S.game_settings, S.add_coins, S.inv_add, S.roll_drop = (lambda n: _Chars()), _settings, _add_coins, _inv_add, _roll_drop
        S.log_event = lambda *a, **k: None

    def tearDown(self):
        for k, v in self._saved.items():
            setattr(S, k, v)

    def _buy(self, key, rng=None):
        return asyncio.run(S.buy_box(1, key, rng or random.Random(3)))

    def test_not_enough_dp_gives_nothing(self):
        CHAR["dp"] = S.BOXES["gold"]["cost"] - 1
        self.assertEqual(self._buy("gold"), ("poor", None))
        self.assertEqual((COINS, ITEMS), ([], []))
        self.assertEqual(CHAR["dp"], S.BOXES["gold"]["cost"] - 1)

    def test_every_chest_pays_coins_and_an_item(self):
        for key, b in S.BOXES.items():
            CHAR["dp"] = b["cost"]
            status, res = self._buy(key)
            self.assertEqual(status, "ok")
            self.assertTrue(b["coins"][0] <= res["coins"] <= b["coins"][1], key)
            self.assertTrue(res["item"], key)
            self.assertEqual(CHAR["dp"], 0)
        self.assertEqual(len(COINS), 3)
        self.assertEqual(len(ITEMS), 3)
        self.assertTrue(all(force for _, force in ITEMS))  # a full bag never loses the item

    def test_rarity_never_below_the_chest_floor(self):
        for key, b in S.BOXES.items():
            for seed in range(60):
                DROPS.clear()
                CHAR["dp"] = b["cost"]
                self._buy(key, random.Random(seed))
                self.assertGreaterEqual(DROPS[0]["floor"], b["floor"], key)

    def test_gold_chest_odds(self):
        legendary_up = 0
        runs = 600
        for seed in range(runs):
            DROPS.clear()
            CHAR.clear()
            CHAR["dp"] = S.BOXES["gold"]["cost"]
            self._buy("gold", random.Random(seed))
            legendary_up += DROPS[0]["floor"] >= 4
        share = legendary_up / runs
        self.assertTrue(0.25 < share < 0.47, share)  # about a third (34% Legendary + 2% Mythic)

    def test_pity_guarantees_a_better_item(self):
        CHAR["dp"] = S.BOXES["gold"]["cost"]
        CHAR["box_pity"] = {"gold": 3}  # pity is 4: this is the 4th chest without Legendary
        status, res = self._buy("gold", _Forced(0))  # the unluckiest roll
        self.assertTrue(res["pity"])
        self.assertEqual(DROPS[0]["floor"], 4)
        self.assertEqual(SETS[-1], {"box_pity.gold": 0})

    def test_pity_counts_up_after_a_plain_chest(self):
        CHAR["dp"] = S.BOXES["gold"]["cost"]
        CHAR["box_pity"] = {"gold": 1}
        status, res = self._buy("gold", _Forced(0))
        self.assertFalse(res["pity"])
        self.assertEqual(DROPS[0]["floor"], 3)
        self.assertEqual(SETS[-1], {"box_pity.gold": 2})

    def test_a_good_roll_resets_pity(self):
        CHAR["dp"] = S.BOXES["gold"]["cost"]
        CHAR["box_pity"] = {"gold": 2}
        self._buy("gold", _Forced(1))
        self.assertEqual(SETS[-1], {"box_pity.gold": 0})

    def test_mythic_result_is_a_weapon(self):
        CHAR["dp"] = S.BOXES["gold"]["cost"]
        self._buy("gold", _Forced(2))
        self.assertEqual(DROPS[0]["floor"], 5)
        self.assertEqual(DROPS[0]["weapon"], 1.0)

    def test_pity_can_be_switched_off(self):
        async def off():
            return {"dp_pity_bronze": 0, "dp_pity_silver": 0, "dp_pity_gold": 0}
        S.game_settings = off
        CHAR["dp"] = S.BOXES["gold"]["cost"]
        CHAR["box_pity"] = {"gold": 50}
        status, res = self._buy("gold", _Forced(0))
        self.assertFalse(res["pity"])
        self.assertEqual(DROPS[0]["floor"], 3)


if __name__ == "__main__":
    unittest.main()
