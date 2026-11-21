"""Hōgyoku theft is a power duel (best of N, real combat engine per round), not a dice roll.
The rule tests need nothing; the flow tests need the app's imports (motor/aiogram) and skip without them.
Run: python -m unittest test_hogyoku_duel -v"""
import asyncio
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data_artifacts as DA  # noqa: E402


class Rules(unittest.TestCase):
    def test_wins_needed(self):
        self.assertEqual([DA.hog_wins_needed(n) for n in (1, 3, 5)], [1, 2, 3])

    def test_too_weak_uses_the_ratio(self):
        self.assertTrue(DA.hog_too_weak(400, 1000, 0.5))
        self.assertFalse(DA.hog_too_weak(500, 1000, 0.5))
        self.assertFalse(DA.hog_too_weak(1, 0, 0.5))      # an empty holder never locks anyone out

    def test_penalty_full_when_swept_half_when_close(self):
        self.assertEqual(DA.hog_penalty_hours(0, 2, 3), 3)
        self.assertEqual(DA.hog_penalty_hours(1, 2, 3), 1)   # half of 3, at least 1
        self.assertEqual(DA.hog_penalty_hours(1, 2, 4), 2)
        self.assertEqual(DA.hog_penalty_hours(0, 2, 0), 0)   # penalty switched off

    def test_no_luck_setting_left(self):
        import config
        self.assertNotIn("hog_steal_chance", config.GAME_DEFAULTS)
        for k in ("hog_rounds", "hog_min_power_ratio", "hog_target_lock"):
            self.assertIn(k, config.GAME_DEFAULTS)


try:
    import service_extras as SX
except Exception as ex:  # motor / pymongo / aiogram are not installed here
    SX = None
    _WHY = str(ex)


class FakeCol:
    def __init__(self):
        self.docs = {}

    async def find_one_and_update(self, q, upd):
        d = self.docs.get("hogyoku")
        if d and d["holder"] == q["holder"]:
            d.update(upd["$set"])
            return dict(d)
        return None

    async def update_one(self, q, upd):
        self.docs.setdefault("updates", []).append((q, upd))

    async def delete_one(self, q):
        self.docs.setdefault("deleted", []).append(q)


@unittest.skipIf(SX is None, "app imports unavailable")
class Flow(unittest.TestCase):
    def setUp(self):
        import service_bleach_systems as SB
        import service_player as SP
        self.c = FakeCol()
        self.c.docs["hogyoku"] = {"holder": 2, "since": 0}
        self.chars = {1: {"level": 30, "name": "T", "p": 1000}, 2: {"level": 30, "name": "H", "p": 1000}}
        self.st = {"hog_min_level": 10, "hog_shield_minutes": 30, "hog_steal_cd_hours": 2, "hog_pen_hours": 3,
                   "hog_rounds": 3, "hog_min_power_ratio": 0.5, "hog_target_lock": 60}
        self.cd = {}
        self.script = []
        self.saved = (SX.col, SX.get_char, SX.game_settings, SX.try_cooldown, SX.hogyoku_state, SB.quick_fight, SP.power)

        async def get_char(u):
            return self.chars.get(u)

        async def gs():
            return self.st

        async def tc(key, sec):
            if key in self.cd:
                return 99
            self.cd[key] = 1
            return 0

        async def state():
            return self.c.docs["hogyoku"]

        async def qf(a, b):
            return self.script.pop(0)

        SX.col, SX.get_char, SX.game_settings, SX.try_cooldown, SX.hogyoku_state = (lambda name: self.c), get_char, gs, tc, state
        SB.quick_fight = qf
        SP.power = lambda ch: ch["p"]

    def tearDown(self):
        import service_bleach_systems as SB
        import service_player as SP
        SX.col, SX.get_char, SX.game_settings, SX.try_cooldown, SX.hogyoku_state, SB.quick_fight, SP.power = self.saved

    def run_steal(self):
        return asyncio.run(SX.hogyoku_steal(1, 2))

    def test_two_round_win_takes_it_and_stops(self):
        self.script = ["a", "a", "b"]
        res, rep = self.run_steal()
        self.assertEqual(res, "win")
        self.assertEqual(rep["rounds"], ["a", "a"])
        self.assertEqual(self.c.docs["hogyoku"]["holder"], 1)

    def test_loss_keeps_holder_and_full_penalty_when_swept(self):
        self.script = ["b", "b"]
        res, rep = self.run_steal()
        self.assertEqual((res, rep["hours"]), ("fail", 3))
        self.assertEqual(self.c.docs["hogyoku"]["holder"], 2)

    def test_close_loss_halves_penalty(self):
        self.script = ["a", "b", "b"]
        res, rep = self.run_steal()
        self.assertEqual((res, rep["hours"]), ("fail", 1))

    def test_far_weaker_challenger_cannot_try_and_keeps_cooldown(self):
        self.chars[1]["p"] = 100
        res, extra = self.run_steal()
        self.assertEqual(res, "weak")
        self.assertEqual(extra["need"], 500)
        self.assertEqual(self.cd, {})      # nothing was spent

    def test_win_and_loss_reach_the_log_channel(self):
        import service_log as SL
        seen = []
        orig = SL.log_event
        SL.log_event = lambda kind, uid=0, text="", **x: seen.append((kind, uid, text))
        try:
            self.script = ["a", "a"]
            self.run_steal()
            self.assertEqual(seen[-1][0:2], ("hog", 1))
            self.assertIn("دزدید", seen[-1][2])
            self.assertIn("✅✅", seen[-1][2])
            self.c.docs["hogyoku"] = {"holder": 2, "since": 0}
            self.cd.clear()
            self.script = ["b", "b"]
            self.run_steal()
            self.assertIn("شکست", seen[-1][2])
        finally:
            SL.log_event = orig

    def test_busy_holder_gives_the_try_back(self):
        self.cd["hog:tgt:2"] = 1
        res, _ = self.run_steal()
        self.assertEqual(res, "busy")
        self.assertIn({"key": "hog:steal:1"}, self.c.docs.get("deleted", []))


if __name__ == "__main__":
    unittest.main()
