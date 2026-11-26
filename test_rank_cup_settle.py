"""Nov 26: ranked duel settle with cup-style Battle Rank. A win over a much higher rank pays a lot, a win over someone 300+ points
below pays nothing (and costs the loser nothing), and a level gap no longer blocks Battle Rank (the bug: the high-level
player lost rank when he lost but gained nothing when he won)."""
import asyncio
import sys
import types
import unittest
from unittest import mock

for _n in ("motor", "motor.motor_asyncio", "pymongo", "pymongo.errors"):  # stubs only where the libraries are missing
    try:
        __import__(_n)
    except ImportError:
        sys.modules.setdefault(_n, types.ModuleType(_n))
if not hasattr(sys.modules.get("motor.motor_asyncio"), "AsyncIOMotorClient"):
    sys.modules["motor.motor_asyncio"].AsyncIOMotorClient = lambda *a, **k: types.SimpleNamespace()
if not hasattr(sys.modules.get("pymongo"), "ReturnDocument"):
    sys.modules["pymongo"].ReturnDocument = types.SimpleNamespace(AFTER="after")
    sys.modules["pymongo.errors"].DuplicateKeyError = Exception

try:
    import service_combat as SC
    import data_battlerank as B
    IMPORT_ERR = None
except Exception as e:  # aiogram etc. missing in a bare environment
    SC, IMPORT_ERR = None, e


def _char(uid, level, br):
    return {"user_id": uid, "level": level, "name": f"P{uid}", "rating": 1000, "created_at": 0, "location": "rukongai",
            "br": br, "br_season": 10 ** 6}  # a season far in the future would reset; current() is patched below


class _Col:
    async def find_one_and_update(self, *a, **k):
        return {"claimed": True}

    async def count_documents(self, *a, **k):
        return 0

    async def update_one(self, *a, **k):
        return types.SimpleNamespace(modified_count=1, matched_count=1)

    async def insert_many(self, *a, **k):
        return None


@unittest.skipIf(SC is None, f"service_combat cannot be imported here: {IMPORT_ERR}")
class RankCupSettle(unittest.TestCase):
    def settle(self, w_level, l_level, w_rp, l_rp, pair_ok=True):
        chars = {1: _char(1, w_level, w_rp), 2: _char(2, l_level, l_rp)}
        calls = []

        async def get_char(uid):
            return chars[uid]

        async def br_apply(uid, kind, **kw):
            calls.append((uid, kind, kw.get("opp_rp")))
            if kind == "duel_win":
                return {"delta": B.duel_gain(w_rp, kw["opp_rp"]), "title_fa": "", "title_en": ""}
            return {"delta": -B.duel_loss(kw["opp_rp"], l_rp), "title_fa": "", "title_en": ""}

        async def bump(*a, **k):
            return pair_ok

        async def gs():
            return {"pvp_pair_daily_cap": 3, "pvp_gain_min": 10, "pvp_gain_max": 20, "pvp_loss_min": 5, "pvp_loss_max": 10,
                    "pvp_full_xp_wins": 99, "coin_rate": 1.0, "pvp_xp_mult": 1.5, "pvp_loser_xp": 0.0}
        doc = {"sid": "x", "a_uid": 1, "b_uid": 2, "ranked": True,
               "state": {"winner": "a", "a": {}, "b": {}}}
        stack = [mock.patch.object(SC, "col", lambda name: _Col()), mock.patch.object(SC, "get_char", get_char),
                 mock.patch.object(SC, "game_settings", gs), mock.patch.object(SC, "add_xp", mock.AsyncMock(return_value=(None, 0, 0))),
                 mock.patch.object(SC, "add_coins", mock.AsyncMock()), mock.patch.object(SC, "bump_quest", mock.AsyncMock()),
                 mock.patch.object(SC, "log_event", lambda *a, **k: None),
                 mock.patch("database.bump_counter", bump),
                 mock.patch("service_battlerank.apply", br_apply),
                 mock.patch("service_battlerank.current", lambda ch, now=None: (int(ch["br"]), [])),
                 mock.patch("service_interact.claim_bounty", mock.AsyncMock(return_value=0), create=True),
                 mock.patch("service_worldstate.on_action_bg", lambda *a, **k: None, create=True)]
        for p in stack:
            p.start()
            self.addCleanup(p.stop)
        res = asyncio.run(SC.pvp_settle(doc))
        return res, calls

    def test_upset_pays_and_costs(self):
        res, calls = self.settle(100, 100, 900, 1800)
        self.assertEqual([c[1] for c in calls], ["duel_win", "duel_loss"])
        self.assertEqual(res["br"][1]["delta"], B.duel_gain(900, 1800))
        self.assertLess(res["br"][2]["delta"], 0)

    def test_far_below_pays_nothing_and_does_not_punish_the_loser(self):
        res, calls = self.settle(100, 100, 1800, 900)
        self.assertEqual(calls, [])
        self.assertEqual(res.get("br_note"), "gap")
        self.assertNotIn("br", res)

    def test_level_gap_no_longer_blocks_battle_rank(self):
        # a level 238 player beats a level 100 player of equal rank: unrated for the classic rating, but rank moves
        res, calls = self.settle(238, 100, 900, 900)
        self.assertEqual(res["note"], "level_gap")
        self.assertEqual([c[1] for c in calls], ["duel_win", "duel_loss"])
        self.assertGreater(res["br"][1]["delta"], 0)

    def test_pair_daily_limit_still_applies(self):
        res, calls = self.settle(100, 100, 900, 900, pair_ok=False)
        self.assertEqual(calls, [])
        self.assertEqual(res.get("br_note"), "pair")


if __name__ == "__main__":
    unittest.main()
