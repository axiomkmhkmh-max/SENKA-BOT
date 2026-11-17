"""Dungeon chests pay coins AND an item of the chest's own two colours only (bronze white/green, silver blue/purple,
gold gold/red), with pity towards the higher colour.
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


async def _roll_drop(uid, source_mult=1.0, weapon_chance=0.1, floor_idx=0, rng=random, exact_idx=None):
    DROPS.append({"idx": exact_idx})
    return f"item_{exact_idx}"


class _Forced:
    """rng that always picks the given choices index and the low end of ranges."""
    def __init__(self, pick):
        self.pick = pick

    def choices(self, population, weights=None, k=1):
        return [population[self.pick]]

    def randint(self, a, b):
        return a

    def random(self):
        return 0.99  # no relic

    def choice(self, seq):
        return seq[0]


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

    def test_colours_per_chest(self):
        self.assertEqual(S.BOXES["bronze"]["rar"], (0, 1))   # white, green
        self.assertEqual(S.BOXES["silver"]["rar"], (2, 3))   # blue, purple
        self.assertEqual(S.BOXES["gold"]["rar"], (4, 5))     # gold, red

    def test_not_enough_dp_gives_nothing(self):
        CHAR["dp"] = S.BOXES["gold"]["cost"] - 1
        status, res = self._buy("gold")
        self.assertEqual(status, "poor")
        self.assertEqual(CHAR["dp"], S.BOXES["gold"]["cost"] - 1)
        self.assertEqual(DROPS, [])

    def test_every_chest_pays_coins_and_an_item_of_its_own_colours(self):
        rng = random.Random(11)
        for key, b in S.BOXES.items():
            for _ in range(200):
                CHAR.clear()
                CHAR["dp"] = b["cost"]
                DROPS.clear()
                status, res = asyncio.run(S.buy_box(1, key, rng))
                self.assertEqual(status, "ok")
                self.assertGreater(res["coins"], 0)
                self.assertIn(DROPS[0]["idx"], b["rar"], key)

    def test_pity_gives_the_higher_colour(self):
        CHAR["dp"] = S.BOXES["gold"]["cost"]
        CHAR["box_pity"] = {"gold": 3}  # pity 4: this is the 4th in a row
        status, res = self._buy("gold", _Forced(0))
        self.assertTrue(res["pity"])
        self.assertEqual(DROPS[0]["idx"], 5)

    def test_pity_counts_up_after_a_lower_colour(self):
        CHAR["dp"] = S.BOXES["gold"]["cost"]
        status, res = self._buy("gold", _Forced(0))
        self.assertFalse(res["pity"])
        self.assertEqual(DROPS[0]["idx"], 4)
        self.assertEqual(SETS[-1], {"box_pity.gold": 1})

    def test_a_higher_colour_resets_pity(self):
        CHAR["dp"] = S.BOXES["gold"]["cost"]
        CHAR["box_pity"] = {"gold": 2}
        self._buy("gold", _Forced(1))
        self.assertEqual(SETS[-1], {"box_pity.gold": 0})

    def test_relics_come_by_luck_in_the_chest_colours(self):
        from data_items import ALL
        rng = random.Random(21)
        for key, (chance, rars) in S.RELIC_ODDS.items():
            got = 0
            for _ in range(400):
                CHAR.clear()
                CHAR["dp"] = S.BOXES[key]["cost"]
                ITEMS.clear()
                status, res = asyncio.run(S.buy_box(1, key, rng))
                if res["relic"]:
                    got += 1
                    self.assertEqual(ALL[res["relic"]]["category"], "evolution")
                    self.assertIn(ALL[res["relic"]]["rarity"], rars)
            self.assertAlmostEqual(got / 400, chance, delta=0.07)

    def test_dp_grows_with_level_and_difficulty(self):
        low = S.dp_for_clear({"id": "trial", "diff": "normal"})
        high = S.dp_for_clear({"id": "jigoku_pit", "diff": "normal"})
        hard = S.dp_for_clear({"id": "jigoku_pit", "diff": "legendary"})
        self.assertLess(low, high)
        self.assertLess(high, hard)


if __name__ == "__main__":
    unittest.main()
