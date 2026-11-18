"""Dungeon special items, the live dungeon-point cap and the shorter world-boss gap.
No MongoDB needed: the database layer is faked. Run: python -m unittest test_dungeon_special -v"""
import asyncio
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _stubs import import_with_stubs  # noqa: E402

S = import_with_stubs("service_dungeonshop")
from config import GAME_DEFAULTS  # noqa: E402
from data_items import ALL, BY_RARITY, DG_SPECIAL  # noqa: E402

SETTINGS = {}
COUNTERS = []
GIVEN = []
INC = []


async def _settings():
    return dict(SETTINGS)


async def _bump(key, n, cap):
    COUNTERS.append((key, n, cap))
    used = sum(c[1] for c in COUNTERS if c[0] == key and c is not COUNTERS[-1])
    if used + n > cap:
        COUNTERS.pop()
        return False
    return True


async def _inv_add(uid, iid, qty=1, force=False):
    GIVEN.append((iid, force))
    return True


class _Chars:
    async def update_one(self, flt, upd):
        INC.append(upd["$inc"]["dp"])


class _Rng:
    def __init__(self, roll):
        self.roll = roll

    def random(self):
        return self.roll

    def choice(self, seq):
        return seq[0]


class SpecialItemTests(unittest.TestCase):
    def setUp(self):
        SETTINGS.clear()
        SETTINGS.update({"dg_special_on": 1, "dg_special_day_cap": 2, "dp_daily_cap": 4000})
        for lst in (COUNTERS, GIVEN, INC):
            lst.clear()
        self._saved = {k: getattr(S, k) for k in ("col", "game_settings", "bump_counter", "inv_add", "log_event")}
        S.col, S.game_settings, S.bump_counter, S.inv_add = (lambda n: _Chars()), _settings, _bump, _inv_add
        S.log_event = lambda *a, **k: None

    def tearDown(self):
        for k, v in self._saved.items():
            setattr(S, k, v)

    def test_catalog_items_are_valid_and_dungeon_only(self):
        self.assertEqual(set(DG_SPECIAL), {"normal", "hard", "nightmare", "abyss", "legendary"})
        for diff, ids in DG_SPECIAL.items():
            self.assertTrue(ids, diff)
            for iid in ids:
                it = ALL[iid]
                self.assertEqual(it["category"], "dungeon")
                self.assertTrue(it["name_en"] and it["name_fa"] and it["desc_en"] and it["desc_fa"])
                eff = it["effect"]
                self.assertIn(eff["type"], ("buff", "konpaku", "xp", "bond"))
                if eff["type"] == "buff":
                    self.assertIn(eff["stat"], ("dmg", "def", "crit"))
                    self.assertLessEqual(eff["minutes"], GAME_DEFAULTS["buff_max_minutes"])
                for pool in BY_RARITY.values():  # never in a random drop pool
                    self.assertNotIn(iid, pool)

    def test_item_ids_are_unique(self):
        ids = [i for v in DG_SPECIAL.values() for i in v]
        self.assertEqual(len(ids), len(set(ids)))

    def test_hit_gives_item_of_that_difficulty(self):
        got = asyncio.run(S.roll_special(1, {"id": "muken", "diff": "abyss"}, _Rng(0.0)))
        self.assertIn(got, DG_SPECIAL["abyss"])
        self.assertEqual(GIVEN, [(got, True)])

    def test_miss_gives_nothing_and_uses_no_cap(self):
        got = asyncio.run(S.roll_special(1, {"id": "trial", "diff": "normal"}, _Rng(0.99)))
        self.assertIsNone(got)
        self.assertEqual(GIVEN, [])
        self.assertEqual(COUNTERS, [])

    def test_daily_cap_stops_further_drops(self):
        d = {"id": "trial", "diff": "legendary"}
        r = [asyncio.run(S.roll_special(1, d, _Rng(0.0))) for _ in range(4)]
        self.assertEqual([x is not None for x in r], [True, True, False, False])
        self.assertEqual(len(GIVEN), 2)

    def test_switch_off(self):
        SETTINGS["dg_special_on"] = 0
        self.assertIsNone(asyncio.run(S.roll_special(1, {"id": "trial", "diff": "legendary"}, _Rng(0.0))))
        self.assertEqual(GIVEN, [])

    def test_harder_difficulty_has_better_odds(self):
        c = S.SPECIAL_CHANCE
        self.assertTrue(c["normal"] < c["hard"] < c["nightmare"] < c["abyss"] < c["legendary"])

    def test_dp_cap_comes_from_settings(self):
        SETTINGS["dp_daily_cap"] = 777
        asyncio.run(S.award_dp(1, {"id": "trial", "diff": "normal"}))
        self.assertEqual(COUNTERS[-1][2], 777)

    def test_defaults(self):
        self.assertEqual(GAME_DEFAULTS["dp_daily_cap"], 4000)
        self.assertGreater(GAME_DEFAULTS["dp_daily_cap"], 1500)
        self.assertLess(GAME_DEFAULTS["boss_max_minutes"], 120)
        self.assertLessEqual(GAME_DEFAULTS["boss_min_minutes"], GAME_DEFAULTS["boss_max_minutes"])


if __name__ == "__main__":
    unittest.main()
