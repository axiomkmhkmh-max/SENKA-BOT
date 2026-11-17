"""Battle Rank: flat level-free gains, daily caps, Elo-like ranked duels, flee costs more than a loss, the season reset
and the once-per-season division rewards. Run: python -m unittest test_battlerank -v"""
import asyncio
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _stubs import import_with_stubs  # noqa: E402

S = import_with_stubs("service_battlerank")
import data_battlerank as B  # noqa: E402

CH = {}
GRANTS = []


class _Chars:
    async def update_one(self, flt, upd):
        for k, v in flt.items():
            if k != "user_id" and CH.get(k) != v:
                return type("R", (), {"modified_count": 0})()
        CH.update(upd.get("$set") or {})
        for k, v in (upd.get("$inc") or {}).items():
            CH[k] = CH.get(k, 0) + v
        return type("R", (), {"modified_count": 1})()


async def _get_char(uid):
    return dict(CH)


CAPS = {}


async def _bump(key, n, cap, *a, **k):
    if CAPS.get(key, 0) + n > cap:
        return False
    CAPS[key] = CAPS.get(key, 0) + n
    return True


async def _grant(uid, race, div, rng=None):
    GRANTS.append(div)
    return [f"item{div}"]


class RulesTests(unittest.TestCase):
    def test_eighteen_divisions_with_titles(self):
        self.assertEqual(B.DIVS, 18)
        self.assertEqual(B.title(0, "en"), "⚪ Minarai 1")
        self.assertEqual(B.div_title(17, "en"), "🔴 Menkyo Kaiden 3")
        self.assertIn("شودن", B.div_title(4, "fa"))

    def test_win_is_flat_for_everyone(self):
        # the same points whatever the rank, the number of rounds (= power) or the level
        self.assertEqual(B.win_gain(0, 1), B.win_gain(9000, 12))
        self.assertGreater(B.win_gain(500, 3, elite=True), B.win_gain(500, 3))

    def test_ladder_lasts_the_season(self):
        # even at the daily cap every day, normal battles alone cannot reach the top in under a month
        self.assertGreater(B.THRESHOLDS[-1] / B.PVE_DAILY_CAP, 30)
        self.assertGreaterEqual(B.width(10) / B.PVE_DAILY_CAP, 2)  # a mid sub-tier takes days

    def test_losses_grow_with_rank_and_flee_costs_more(self):
        self.assertGreater(B.loss_cost(B.THRESHOLDS[16]), B.loss_cost(0))
        for rp in (0, 300, B.THRESHOLDS[-1]):
            self.assertGreater(B.flee_cost(rp), B.loss_cost(rp))

    def test_duel_is_elo_like(self):
        self.assertGreater(B.duel_gain(0, 5000), B.duel_gain(0, 0))      # beating a higher rank pays more
        self.assertLess(B.duel_gain(5000, 0), B.duel_gain(0, 0))         # farming a lower rank pays little
        self.assertEqual(B.duel_gain(0, 99999), B.DUEL_MAX)
        self.assertEqual(B.duel_gain(99999, 0), B.DUEL_MIN)
        self.assertLess(B.duel_loss(0, 0), B.duel_gain(0, 0))

    def test_rewards_follow_sub_tiers(self):
        self.assertEqual(B.reward_of(3), ("consumable", 1))   # Shoden 1: green consumable chest
        self.assertEqual(B.reward_of(4), ("equipment", 1))    # Shoden 2: green equipment chest
        self.assertEqual(B.reward_of(17), ("materials", 5))   # Menkyo Kaiden 3: red materials chest

    def test_season_carry(self):
        ch = {"br": 1000, "br_season": -5, "br_claimed": [1, 2]}
        rp, claimed = S.current(ch)
        self.assertEqual((rp, claimed), (400, []))


class ServiceTests(unittest.TestCase):
    def setUp(self):
        CH.clear()
        GRANTS.clear()
        CAPS.clear()
        self._saved = {k: getattr(S, k) for k in ("col", "get_char", "grant_reward", "bump_counter")}
        S.col, S.get_char, S.grant_reward, S.bump_counter = (lambda n: _Chars()), _get_char, _grant, _bump
        CH.update({"user_id": 1, "race": "hollow"})

    def tearDown(self):
        for k, v in self._saved.items():
            setattr(S, k, v)

    def test_win_promotes_and_pays_each_division_once(self):
        res = asyncio.run(S.apply(1, "win", 1))
        self.assertGreater(res["delta"], 0)
        self.assertEqual(GRANTS, [0])        # Minarai 1 reward on the first win
        CH["br"] = B.THRESHOLDS[1] - 1
        asyncio.run(S.apply(1, "win", 1))
        self.assertEqual(GRANTS, [0, 1])
        CH["br"] = 0                         # dropped back down ...
        asyncio.run(S.apply(1, "win", 1))
        CH["br"] = B.THRESHOLDS[1] - 1
        asyncio.run(S.apply(1, "win", 1))
        self.assertEqual(GRANTS, [0, 1])     # ... climbing again pays nothing again this season

    def test_daily_cap_on_normal_battles(self):
        got = sum(asyncio.run(S.apply(1, "win", 1))["delta"] for _ in range(B.PVE_DAILY_CAP // B.PVE_WIN + 5))
        self.assertEqual(got, B.PVE_DAILY_CAP)
        last = asyncio.run(S.apply(1, "win", 1))
        self.assertEqual(last["delta"], 0)
        self.assertTrue(last["capped"])
        res = asyncio.run(S.apply(1, "duel_win", opp_rp=CH["br"]))  # duels still count
        self.assertEqual(res["delta"], B.DUEL_BASE)

    def test_duel_loss_lowers_rank(self):
        CH.update({"br": 500, "br_season": B.season_of(__import__("time").time())})
        res = asyncio.run(S.apply(1, "duel_loss", opp_rp=500))
        self.assertEqual(res["delta"], -B.duel_loss(500, 500))

    def test_flee_costs_rank_and_never_goes_below_zero(self):
        CH.update({"br": 20, "br_season": B.season_of(__import__("time").time())})
        res = asyncio.run(S.apply(1, "flee"))
        self.assertLess(res["delta"], 0)
        self.assertEqual(CH["br"], 0)
        self.assertEqual(CH["br_flees"], 1)


if __name__ == "__main__":
    unittest.main()
