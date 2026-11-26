"""Artifact swap (service_artswap) against the in-memory fake DB.  Run: python -m unittest test_artswap -v"""
import unittest
from unittest import mock

from test_mentor_trade import FakeDB, _char, run  # also stubs motor / aiogram when they are missing
import service_artswap as S
import service_player as SP
from data_artifacts import ARTIFACTS

X, Y, Z = (a["_id"] for a in ARTIFACTS[:3])


class Swap(unittest.TestCase):
    def setUp(self):
        self.db = FakeDB()
        self.counts = {}

        async def bump(key, amount, cap, ttl_hours=48):
            if self.counts.get(key, 0) + amount > cap:
                return False
            self.counts[key] = self.counts.get(key, 0) + amount
            return True
        for p in (mock.patch.object(S, "col", self.db), mock.patch.object(SP, "col", self.db),
                  mock.patch.object(S, "bump_counter", bump), mock.patch.object(S, "log_event", mock.Mock())):
            p.start()
            self.addCleanup(p.stop)
        for uid, art in ((1, X), (2, Y), (3, None), (4, Z)):
            c = _char(uid, 30)
            if art:
                c["artifact"] = art
            run(self.db("characters").insert_one(c))

    def art(self, uid):
        return run(self.db("characters").find_one({"user_id": uid})).get("artifact")

    def test_swap_works_and_counts_do_not_change(self):
        sid, code = run(S.offer(1, 2))
        self.assertEqual(code, "ok")
        self.assertEqual(run(S.accept(sid, 2)), "ok")
        self.assertEqual((self.art(1), self.art(2)), (Y, X))

    def test_only_receiver_accepts_and_decline_changes_nothing(self):
        sid, _ = run(S.offer(1, 2))
        self.assertEqual(run(S.accept(sid, 1)), "gone")
        self.assertEqual(run(S.decline(sid, 2)), "ok")
        self.assertEqual(run(S.accept(sid, 2)), "gone")
        self.assertEqual((self.art(1), self.art(2)), (X, Y))

    def test_refusals(self):
        self.assertEqual(run(S.offer(1, 1))[1], "self")
        self.assertEqual(run(S.offer(3, 1))[1], "none")
        self.assertEqual(run(S.offer(1, 3))[1], "other_none")
        run(self.db("art_listings").insert_one({"_id": "l", "seller": 2, "status": "active"}))
        self.assertEqual(run(S.offer(1, 2))[1], "listed")

    def test_artifact_moved_before_accept_fails_safely(self):
        sid, _ = run(S.offer(1, 2))
        run(self.db("characters").update_one({"user_id": 1}, {"$set": {"artifact": Z}}))  # A gave it up in the meantime
        self.assertEqual(run(S.accept(sid, 2)), "changed")
        self.assertEqual((self.art(1), self.art(2)), (Z, Y))

    def test_one_open_offer_and_pair_cap(self):
        self.assertEqual(run(S.offer(1, 2))[1], "ok")
        self.assertEqual(run(S.offer(1, 4))[1], "busy")
        self.assertEqual(run(S.offer(2, 4))[1], "busy")

    def test_pair_daily_cap(self):
        sid, _ = run(S.offer(1, 2))
        run(S.accept(sid, 2))
        self.assertEqual(run(S.offer(1, 2))[1], "pair_limit")

    def test_expired_offer(self):
        sid, _ = run(S.offer(1, 2))
        run(self.db("art_swaps").update_one({"_id": sid}, {"$set": {"end_at": 1}}))
        self.assertEqual(run(S.accept(sid, 2)), "expired")
        self.assertEqual((self.art(1), self.art(2)), (X, Y))


if __name__ == "__main__":
    unittest.main()
