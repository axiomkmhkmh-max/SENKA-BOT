"""Hōgyoku theft is a duel the challenger PLAYS with the battle panel (best of N rounds, real combat engine, AI copy of
the holder), not a dice roll. Losing costs only the try (cooldown): no Reiatsu penalty.
The rule tests need nothing; the flow tests need the app's imports (motor/aiogram) and skip without them.
Run: python -m unittest test_hogyoku_duel -v"""
import asyncio
import copy
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

    def test_duel_over_rules(self):
        self.assertEqual(DA.hog_duel_over(2, 0, 3), "win")
        self.assertEqual(DA.hog_duel_over(1, 1, 3), None)
        self.assertEqual(DA.hog_duel_over(0, 2, 3), "fail")
        self.assertEqual(DA.hog_duel_over(1, 2, 3), "fail")
        self.assertEqual(DA.hog_duel_over(1, 0, 3), None)
        self.assertEqual(DA.hog_duel_over(1, 1, 2), "fail")       # an even number of rounds cannot end level: the holder keeps it

    def test_reiatsu_has_no_penalty_any_more(self):
        import time
        self.assertEqual(DA.reiatsu_mult({"reiatsu_pen_until": time.time() + 3600}), 1.0)   # old stored penalties are ignored
        self.assertEqual(DA.reiatsu_mult({"hogyoku": True}), 2.0)

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


def _get(doc, path):
    cur = doc
    for part in path.split("."):
        cur = cur.get(part) if isinstance(cur, dict) else None
    return cur


def _match(doc, q):
    for k, v in q.items():
        cur = _get(doc, k)
        if isinstance(v, dict) and any(str(x).startswith("$") for x in v):
            for op, arg in v.items():
                if (op == "$gte" and not (cur is not None and cur >= arg)) or (op == "$ne" and cur == arg):
                    return False
        elif cur != v:
            return False
    return True


def _apply(doc, upd):
    for k, v in (upd.get("$set") or {}).items():
        t = doc
        parts = k.split(".")
        for part in parts[:-1]:
            t = t.setdefault(part, {})
        t[parts[-1]] = v
    for k in (upd.get("$unset") or {}):
        doc.pop(k, None)
    for k, v in (upd.get("$push") or {}).items():
        doc.setdefault(k, []).extend(v["$each"])
        if "$slice" in v:
            doc[k] = doc[k][v["$slice"]:]


class _Res:
    def __init__(self, n):
        self.modified_count = n


class FakeCol:
    """In-memory stand-in for a Mongo collection (deep copies in and out, like a real database)."""
    def __init__(self, rows):
        self.rows = rows

    async def insert_one(self, doc):
        self.rows.append(copy.deepcopy(doc))

    async def find_one(self, q, proj=None):
        return next((copy.deepcopy(r) for r in self.rows if _match(r, q)), None)

    async def update_one(self, q, upd):
        for r in self.rows:
            if _match(r, q):
                _apply(r, upd)
                return _Res(1)
        return _Res(0)

    async def find_one_and_update(self, q, upd):
        for r in self.rows:
            if _match(r, q):
                old = copy.deepcopy(r)
                _apply(r, upd)
                return old
        return None

    async def delete_one(self, q):
        self.rows[:] = [r for r in self.rows if not _match(r, q)]


class FakeDB:
    def __init__(self):
        self.t = {}

    def __call__(self, name):
        return FakeCol(self.t.setdefault(name, []))


_MISSING = object()   # an attribute a test replaced that did not exist before (other test files stub whole modules)

try:
    import service_combat as SC
    import engine as E
except Exception:
    SC = E = None


@unittest.skipIf(SX is None or SC is None, "app imports unavailable")
class Flow(unittest.TestCase):
    """The whole duel against an in-memory database: start, the panel rounds, the theft, a loss, forfeit."""

    def setUp(self):
        import service_bleach_systems as SB
        import service_fightfx as FX
        import service_player as SP
        self.db = FakeDB()
        self.db.t["hogyoku"] = [{"_id": "main", "holder": 2, "since": 0, "history": []}]
        self.db.t["characters"] = [self._char(1, "T", 400), self._char(2, "H", 60)]
        self.st = {"hog_min_level": 10, "hog_shield_minutes": 30, "hog_steal_cd_hours": 2,
                   "hog_rounds": 3, "hog_min_power_ratio": 0.0, "hog_target_lock": 60}
        self.logs = []
        self.saved = [(m, n, getattr(m, n, _MISSING)) for m, n in (
            (SX, "col"), (SX, "get_char"), (SX, "game_settings"), (SX, "try_cooldown"), (SX, "hogyoku_state"),
            (SC, "col"), (SC, "get_char"), (SC, "build_player"), (SC, "log_event"), (SP, "power"))]

        async def get_char(u):
            return copy.deepcopy(next((c for c in self.db.t["characters"] if c["user_id"] == u), None))

        async def gs():
            return self.st

        async def tc(key, sec):
            rows = self.db.t.setdefault("cooldowns", [])
            if any(r["key"] == key for r in rows):
                return 99
            rows.append({"key": key})
            return 0

        async def state():
            return self.db.t["hogyoku"][0]

        async def build_player(ch, name=None):
            s = ch["stats"]
            w = {"attack": s["zanjutsu"] / 4, "crit": 0.03, "element": "light", "skills": [], "weapon_type": "melee"}
            return E.new_fighter(name or ch["name"], ch["level"], s, 4000, 300, w, mods={}, race="human")

        SX.col = SC.col = self.db
        SX.get_char = SC.get_char = get_char
        SX.game_settings, SX.try_cooldown, SX.hogyoku_state = gs, tc, state
        SC.build_player = build_player
        SC.log_event = lambda kind, uid=0, text="", **x: self.logs.append((kind, uid, text, x))
        SP.power = lambda ch: ch["p"]

    def tearDown(self):
        for m, n, v in self.saved:
            if v is _MISSING:
                delattr(m, n)
            else:
                setattr(m, n, v)

    @property
    def cd(self):
        """The cooldown keys currently spent (the fake try_cooldown stores them in the fake database)."""
        return {r["key"]: 1 for r in self.db.t.get("cooldowns", [])}

    @staticmethod
    def _char(uid, name, z):
        return {"user_id": uid, "name": name, "level": 30, "location": "karakura", "p": z,
                "stats": {"zanjutsu": z, "kido": 1, "hakuda": 50, "hoho": 20, "reiatsu": 50}}

    def steal(self):
        return asyncio.run(SX.hogyoku_steal(1, 2, "fa"))

    def play_round(self, doc):
        """The challenger presses Attack until the round is over -> (battle doc, outcome)."""
        for _ in range(600):
            status, d, data = asyncio.run(SC.pve_act(1, doc["sid"], "atk"))
            self.assertEqual(status, "ok")
            ev, outcome = data
            if outcome:
                return d, outcome
        self.fail("the round never ended")

    def holder(self):
        return self.db.t["hogyoku"][0]["holder"]

    def test_start_is_a_panel_fight_not_an_instant_result(self):
        res, doc = self.steal()
        self.assertEqual(res, "start")
        self.assertEqual(doc["mode"], "pve")
        self.assertTrue(doc["dungeon"]["hog"])
        self.assertEqual((doc["dungeon"]["round"], doc["dungeon"]["rounds_n"]), (1, 3))
        self.assertTrue(doc["state"]["pvp"])
        self.assertTrue(doc["state"]["b"]["ai"] and not doc["state"]["a"]["ai"])
        self.assertEqual(self.holder(), 2)          # nothing is decided yet
        self.assertIn("hog:steal:1", self.cd)

    def test_strong_challenger_wins_two_rounds_and_takes_the_hogyoku(self):
        res, doc = self.steal()
        d, out = self.play_round(doc)
        self.assertTrue(out["win"])
        self.assertFalse(out["hog"]["done"])
        self.assertTrue(out["next"])
        d, out = self.play_round(asyncio.run(SC.col("battles").find_one({"sid": out["next"]})))
        self.assertTrue(out["hog"]["done"])
        self.assertEqual(out["hog"]["result"], "win")
        self.assertEqual(out["hog"]["rep"]["rounds"], ["a", "a"])
        self.assertEqual(self.holder(), 1)
        chars = {c["user_id"]: c for c in self.db.t["characters"]}
        self.assertTrue(chars[1].get("hogyoku"))
        self.assertNotIn("hogyoku", chars[2])
        self.assertEqual(self.logs[-1][0:2], ("hog", 1))
        self.assertIn("دزدید", self.logs[-1][2])

    def test_loss_keeps_holder_and_costs_no_reiatsu(self):
        self.db.t["characters"] = [self._char(1, "T", 20), self._char(2, "H", 400)]
        res, doc = self.steal()
        d, out = self.play_round(doc)
        self.assertFalse(out["win"])
        d, out = self.play_round(asyncio.run(SC.col("battles").find_one({"sid": out["next"]})))
        self.assertEqual(out["hog"]["result"], "fail")
        self.assertEqual(out["hog"]["rep"]["hours"], 0)
        self.assertEqual(self.holder(), 2)
        self.assertTrue(all("reiatsu_pen_until" not in c for c in self.db.t["characters"]))
        self.assertIn("شکست", self.logs[-1][2])

    def test_second_try_needs_the_cooldown(self):
        self.steal()
        asyncio.run(SX.hogyoku_forfeit(1, self.db.t["battles"][0]["sid"]))
        res, extra = self.steal()
        self.assertEqual((res, extra), ("cd", 99))

    def test_open_duel_is_resumed_not_restarted(self):
        res, doc = self.steal()
        res2, doc2 = self.steal()
        self.assertEqual((res2, doc2["sid"]), ("start", doc["sid"]))
        self.assertEqual(len(self.db.t["battles"]), 1)

    def test_other_open_fight_blocks_the_duel_and_gives_the_cooldown_back(self):
        self.db.t["battles"] = [{"sid": "x", "user_id": 1, "mode": "pve", "status": "active", "dungeon": None}]
        res, _ = self.steal()
        self.assertEqual(res, "infight")
        self.assertEqual(self.cd, {})

    def test_holder_is_fought_by_one_challenger_at_a_time(self):
        self.db.t["characters"].append(self._char(3, "X", 400))
        self.db.t["battles"] = [{"sid": "y", "user_id": 3, "mode": "pve", "status": "active",
                                 "dungeon": {"hog": True, "tgt": 2, "t0": __import__("time").time() - 30}}]
        res, _ = self.steal()
        self.assertEqual(res, "busy")
        self.assertNotIn("hog:steal:1", self.cd)

    def test_forfeit_closes_the_duel_without_penalty(self):
        res, doc = self.steal()
        self.assertTrue(asyncio.run(SX.hogyoku_forfeit(1, doc["sid"])))
        self.assertFalse(asyncio.run(SX.hogyoku_forfeit(1, doc["sid"])))
        self.assertEqual(self.holder(), 2)
        self.assertTrue(all("reiatsu_pen_until" not in c for c in self.db.t["characters"]))

    def test_far_weaker_challenger_cannot_try_and_keeps_cooldown(self):
        self.st["hog_min_power_ratio"] = 0.5
        self.db.t["characters"] = [self._char(1, "T", 100), self._char(2, "H", 1000)]
        res, extra = self.steal()
        self.assertEqual(res, "weak")
        self.assertEqual(extra["need"], 500)
        self.assertEqual(self.cd, {})

    def test_hogyoku_changing_hands_mid_duel_voids_it(self):
        res, doc = self.steal()
        d, out = self.play_round(doc)
        self.db.t["hogyoku"][0]["holder"] = 3          # somebody else took it between the rounds
        # the round that was just settled had already queued the next round; settle the next one as a loss-free check
        nxt = asyncio.run(SC.col("battles").find_one({"sid": out["next"]}))
        d, out2 = self.play_round(nxt)
        self.assertTrue(out2["hog"]["done"])
        self.assertEqual(out2["hog"]["result"], "gone")
        self.assertEqual(self.holder(), 3)


if __name__ == "__main__":
    unittest.main()
