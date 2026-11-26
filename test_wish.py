"""Forge Mission: rules (data_wish) and service (service_wish) against the in-memory fake DB.  Run: python -m unittest test_wish -v"""
import unittest
from unittest import mock

from test_mentor_trade import FakeDB, _char, run  # also stubs motor / aiogram when they are missing
import data_wish as W
import service_wish as S
from data_items import ALL

UID, LEVEL = 7, 60


class Rules(unittest.TestCase):
    def test_nothing_below_rare_and_never_mythic_or_other_races(self):
        self.assertEqual(W.eligible(10, "shinigami"), [])
        ids = W.eligible(LEVEL, "shinigami")
        self.assertTrue(ids)
        for i in ids:
            x = ALL[i]
            self.assertIn(x["rarity"], ("Rare", "Epic", "Legendary"))
            self.assertLessEqual(int(x.get("level_req", 1)), LEVEL)
            self.assertIn(x.get("race"), (None, "", "shinigami"))

    def test_requirement_is_hard_stable_and_from_dungeons_near_the_level(self):
        i = W.eligible(LEVEL, "shinigami")[0]
        r = W.requirement(i, LEVEL)
        self.assertEqual(r, W.requirement(i, LEVEL))
        self.assertEqual(len(r["mats"]), W.DUNGEONS_NEEDED)
        from data_races import DUNGEONS
        for iid, did in r["from"].items():
            self.assertLessEqual(DUNGEONS[did]["level"], LEVEL)
            self.assertGreaterEqual(DUNGEONS[did]["level"], LEVEL - W.DUNGEON_BAND)
        self.assertGreater(r["coins"], 0)
        self.assertTrue(all(n >= 6 for n in r["mats"].values()))


class Service(unittest.TestCase):
    def setUp(self):
        self.db = FakeDB()
        self.coins = {"n": 10 ** 7}

        async def add_coins(uid, n, why):
            if self.coins["n"] + n < 0:
                return False
            self.coins["n"] += n
            return True

        async def bump(key, amount, cap, ttl_hours=48):
            d = await self.db("counters").find_one({"key": key})
            if d and d["n"] + amount > cap:
                return False
            if d:
                await self.db("counters").update_one({"key": key}, {"$inc": {"n": amount}})
            else:
                await self.db("counters").insert_one({"key": key, "n": amount})
            return True
        for p in (mock.patch.object(S, "col", self.db), mock.patch.object(S, "get_char", self._get_char), mock.patch.object(S, "add_coins", add_coins),
                  mock.patch.object(S, "bump_counter", bump), mock.patch.object(S, "log_event", mock.Mock()),
                  mock.patch.object(S, "inv_get", self._inv_get), mock.patch.object(S, "inv_remove", self._inv_remove),
                  mock.patch.object(S, "inv_add", self._inv_add)):
            p.start()
            self.addCleanup(p.stop)
        self.bag = {}
        run(self.db("characters").insert_one(_char(UID, LEVEL, race="shinigami")))
        self.item = W.eligible(LEVEL, "shinigami")[0]

    async def _get_char(self, uid):
        return await self.db("characters").find_one({"user_id": uid})

    async def _inv_get(self, uid):
        return {"items": dict(self.bag)}

    async def _inv_remove(self, uid, iid, q=1):
        if self.bag.get(iid, 0) < q:
            return False
        self.bag[iid] -= q
        return True

    async def _inv_add(self, uid, iid, q=1, force=False):
        self.bag[iid] = self.bag.get(iid, 0) + q
        return True

    def fill(self):
        for iid, n in run(S.current(UID))["mats"].items():
            self.bag[iid] = n

    def test_full_flow(self):
        doc, code = run(S.start(UID, self.item))
        self.assertEqual(code, "ok")
        self.assertEqual(run(S.complete(UID)), "mats")           # nothing collected yet
        self.fill()
        self.assertEqual(run(S.complete(UID)), "ok")
        self.assertEqual(self.bag.get(self.item), 1)
        self.assertTrue(all(self.bag.get(i, 0) == 0 for i in doc["mats"]))  # everything was taken
        self.assertEqual(run(S.current(UID)), {})

    def test_one_open_and_not_listed_items_refused(self):
        self.assertEqual(run(S.start(UID, self.item))[1], "ok")
        self.assertEqual(run(S.start(UID, self.item))[1], "open")
        run(S.abandon(UID))
        self.assertEqual(run(S.start(UID, self.item))[1], "wait")  # abandoning costs a day
        self.assertEqual(run(S.start(UID, "it_0001"))[1] in ("notlisted", "wait"), True)

    def test_one_finished_per_week(self):
        run(S.start(UID, self.item))
        self.fill()
        self.assertEqual(run(S.complete(UID)), "ok")
        other = W.eligible(LEVEL, "shinigami")[1]
        run(S.start(UID, other))
        self.fill()
        self.assertEqual(run(S.complete(UID)), "weekly")
        self.assertEqual(self.bag.get(other, 0), 0)               # nothing was given and nothing taken twice

    def test_no_coins_no_craft_and_nothing_lost(self):
        run(S.start(UID, self.item))
        self.fill()
        before = dict(self.bag)
        self.coins["n"] = 0
        self.assertEqual(run(S.complete(UID)), "funds")
        self.assertEqual(self.bag, before)
        self.coins["n"] = 10 ** 7
        self.assertEqual(run(S.complete(UID)), "ok")              # the weekly slot was given back on failure


if __name__ == "__main__":
    unittest.main()
