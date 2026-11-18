"""Gotei Trial tests: pure helpers, the standard kit, and the whole tournament flow on an in-memory fake DB.
No MongoDB / Telegram needed (missing third-party modules are stubbed only when they are not installed).

Run:  python -m unittest test_gotei_trial -v   (from the project root)
"""
import asyncio
import importlib.abc
import importlib.machinery
import importlib.util
import os
import random
import sys
import types
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
for k, v in {"BOT_TOKEN": "1:test", "MONGODB_URI": "mongodb://localhost:1/test", "OWNER_ID": "1",
             "HMAC_SECRET": "x" * 40}.items():
    os.environ.setdefault(k, v)


class _Any:
    def __getattr__(self, n):
        return _Any()

    def __call__(self, *a, **k):
        return _Any()


def _install_stubs():
    """Only for modules that are really missing (a dev machine without the bot's dependencies)."""
    def missing(name):
        try:
            __import__(name)
            return False
        except ImportError:
            return True
    if missing("pymongo"):
        for n, attrs in (("pymongo", {"ReturnDocument": types.SimpleNamespace(AFTER=1, BEFORE=0), "ASCENDING": 1,
                                      "DESCENDING": -1, "UpdateOne": _Any, "InsertOne": _Any}),
                         ("pymongo.errors", {"DuplicateKeyError": Exception, "PyMongoError": Exception})):
            m = types.ModuleType(n)
            m.__dict__.update(attrs)
            sys.modules[n] = m
    if missing("motor"):
        sys.modules["motor"] = types.ModuleType("motor")
        m = types.ModuleType("motor.motor_asyncio")
        m.AsyncIOMotorClient = _Any
        sys.modules["motor.motor_asyncio"] = m

    class Loader(importlib.abc.Loader):
        def create_module(self, spec):
            m = types.ModuleType(spec.name)
            m.__path__ = []
            m.__getattr__ = lambda n: type(n, (Exception,), {}) if n.startswith("Telegram") else _Any()
            return m

        def exec_module(self, m):
            pass

    stub_roots = {n for n in ("aiogram", "aiohttp", "redis") if importlib.util.find_spec(n) is None}  # before the finder exists

    class Finder(importlib.abc.MetaPathFinder):
        def find_spec(self, name, path, target=None):
            if name.split(".")[0] in stub_roots:
                return importlib.machinery.ModuleSpec(name, Loader(), is_package=True)
    if stub_roots:
        _FINDERS.append(Finder())
        sys.meta_path.insert(0, _FINDERS[-1])


_ROOT = os.path.dirname(os.path.abspath(__file__))
_SAVED, _SNAP, _FINDERS = {}, set(), []


def setUpModule():
    """Run on a clean module cache. Other test files leave fake `service_*` modules behind and I must not use them;
    mine (stubs + real project modules built on them) are removed afterwards and theirs are put back, so no other
    test module can ever pick up one of my stubbed modules."""
    for name in list(sys.modules):
        root = name.split(".")[0]
        fake_dep = root in ("pymongo", "motor", "aiogram", "aiohttp", "redis") and getattr(sys.modules[name], "__file__", None) is None
        if fake_dep or (not root.startswith("test_") and os.path.exists(os.path.join(_ROOT, root + ".py"))):
            _SAVED[name] = sys.modules.pop(name)
    _SNAP.update(sys.modules)
    _install_stubs()


def tearDownModule():
    for name in set(sys.modules) - set(_SNAP):
        del sys.modules[name]
    sys.modules.update(_SAVED)
    for f in _FINDERS:
        if f in sys.meta_path:
            sys.meta_path.remove(f)


import engine as E  # noqa: E402
from config import GAME_DEFAULTS  # noqa: E402
from data_races import RACES  # noqa: E402
from engine_tournament import (STD_EVO, TRAIN_LOSS_PTS, TRAIN_PAIR_CAP, TRAIN_WIN_PTS, pair_round, points_for_level,  # noqa: E402
                               seed_bracket, standard_armor, standard_char, standard_stats, standard_weapon,
                               training_points)


def run(coro):
    return asyncio.run(coro)


# ---- pure helpers ---------------------------------------------------------------------------------------------
class TrainingPoints(unittest.TestCase):
    def test_win_and_loss(self):
        self.assertEqual(training_points(True, 0), TRAIN_WIN_PTS)
        self.assertEqual(training_points(False, 0), TRAIN_LOSS_PTS)

    def test_pair_cap_zeroes_points(self):
        self.assertEqual(training_points(True, TRAIN_PAIR_CAP), 0)
        self.assertEqual(training_points(False, TRAIN_PAIR_CAP + 3), 0)
        self.assertGreater(training_points(True, TRAIN_PAIR_CAP - 1), 0)


class Bracket(unittest.TestCase):
    def test_four_seeds(self):
        self.assertEqual(seed_bracket([1, 2, 3, 4]), [1, 4, 2, 3])
        self.assertEqual(pair_round(seed_bracket([1, 2, 3, 4])), [(1, 4), (2, 3)])

    def test_eight_seeds_standard_order(self):
        self.assertEqual(seed_bracket(list(range(1, 9))), [1, 8, 4, 5, 2, 7, 3, 6])

    def test_missing_seeds_are_byes_for_the_top_seeds(self):
        self.assertEqual(seed_bracket([1, 2, 3]), [1, None, 2, 3])
        self.assertEqual(pair_round(seed_bracket([1, 2, 3])), [(1, None), (2, 3)])
        order = seed_bracket(list(range(1, 6)))  # 5 entrants in 8 slots: seeds 1, 2, 3 rest
        self.assertEqual([a for a, b in pair_round(order) if b is None], [1, 2, 3])

    def test_every_entrant_appears_once(self):
        for n in range(2, 40):
            real = [x for x in seed_bracket(list(range(1, n + 1))) if x is not None]
            self.assertEqual(sorted(real), list(range(1, n + 1)))

    def test_bracket_always_ends_with_one_and_top_two_meet_only_in_the_final(self):
        for n in range(2, 40):
            alive = seed_bracket(list(range(1, n + 1)))
            self.assertTrue(len(alive) & (len(alive) - 1) == 0)
            while len(alive) > 2:
                alive = [a if b is None else min(a, b) for a, b in pair_round(alive)]  # the better seed always wins
            if n >= 2:
                self.assertEqual(sorted(alive), [1, 2], n)  # 1 and 2 reach the final
            alive = [a if b is None else min(a, b) for a, b in pair_round(alive)]
            self.assertEqual(alive, [1])


# ---- the standard kit ---------------------------------------------------------------------------------------------
class StandardKit(unittest.TestCase):
    def test_points_for_level(self):
        self.assertEqual(points_for_level(1), 0)
        self.assertEqual(points_for_level(5), 3 * 4 + 1)
        self.assertEqual(points_for_level(30), 29 * 3 + 6)

    def test_every_race_gets_the_same_stat_total(self):
        totals = {r: sum(standard_stats(v["stats"], 30).values()) for r, v in RACES.items()}
        base = {r: sum(v["stats"].values()) for r, v in RACES.items()}
        for r, t in totals.items():  # total = race base + the level's points, to rounding
            self.assertAlmostEqual(t, base[r] + points_for_level(30), delta=0.05)

    def test_kit_carries_nothing_of_the_real_character(self):
        kit = standard_char(7, "A", "quincy", 30, RACES["quincy"]["stats"], False)
        self.assertEqual(set(kit), {"user_id", "name", "race", "level", "stats", "points", "kido_refunded", "kido",
                                    "party", "zanpakuto", "evo"})
        self.assertEqual(kit["evo"], STD_EVO)
        self.assertEqual(kit["zanpakuto"], {})
        self.assertEqual(kit["kido"], {"had": [], "bak": []})

    def test_kit_is_neutral_for_every_bonus_source(self):
        from data_artifacts import reiatsu_mult
        from data_bleach import division_bonus
        from data_crafting import evo_stage, player_bonus
        from data_gangs import xcution_dmg_mult
        from data_items import ALL
        from data_zanpakuto import bond_value
        for race, v in RACES.items():
            kit = standard_char(1, "X", race, 30, v["stats"], race in ("shinigami", "visored"))
            b = player_bonus(kit, ALL, GAME_DEFAULTS)
            self.assertTrue(all(x == 0 for x in b.values()), (race, b))
            self.assertEqual(xcution_dmg_mult(kit), 1.0)
            self.assertEqual(reiatsu_mult(kit), 1.0)
            self.assertEqual(division_bonus(kit), {})
            self.assertEqual(bond_value(kit), 0)
            self.assertEqual(evo_stage(kit), STD_EVO)

    def test_weapon_and_armor_are_level_scaled_and_equal(self):
        w = standard_weapon(30)
        self.assertEqual(w, standard_weapon(30))
        self.assertGreater(standard_weapon(40)["attack"], w["attack"])
        self.assertEqual(w["type"], "melee")
        self.assertEqual(w["skills"], [])
        self.assertGreater(standard_armor(40), standard_armor(30))


# ---- the build through the real build_player ------------------------------------------------------------------------
class BuiltFighters(unittest.TestCase):
    def setUp(self):
        import service_combat as SC
        self.SC = SC

        async def gacha(uid):
            return {"chars": {}}

        async def blade_ok(uid, bid):
            return True
        self.patches = [mock.patch.object(SC, "gacha_doc", gacha), mock.patch.object(SC, "game_settings", self._gs)]
        for p in self.patches:
            p.start()

    async def _gs(self, force=False):
        return dict(GAME_DEFAULTS)

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def _build(self, race, name, uid):
        from engine_tournament import standard_armor as sa, standard_weapon as sw
        kit = standard_char(uid, name, race, 30, RACES[race]["stats"], race in self.SC.KIDO_RACES)
        f = run(self.SC.build_player(kit, name=name))
        f["weapon"], f["armor"] = sw(30), sa(30)
        return f

    def test_same_race_gives_identical_fighters_whoever_the_player_is(self):
        for race in RACES:
            a, b = self._build(race, "A", 1), self._build(race, "B", 999)
            a.pop("name"), b.pop("name")
            self.assertEqual(a, b, race)

    def test_no_blade_no_release_bonus_no_gear(self):
        f = self._build("shinigami", "A", 1)
        self.assertEqual(f["zmult"], 1.0)
        self.assertIsNone(f["mv"])
        self.assertIsNone(f["bt"])
        self.assertEqual(f["weapon"], standard_weapon(30))
        self.assertEqual(f["armor"], standard_armor(30))
        self.assertEqual(f["level"], 30)

    def test_every_race_can_fight(self):
        rng = random.Random(5)
        for race in RACES:
            for other in ("shinigami", "hollow"):
                from engine_tournament import play_match
                self.assertIn(play_match(self._build(race, "A", 1), self._build(other, "B", 2), rng), ("a", "b"))


# ---- the whole tournament on a fake DB ----------------------------------------------------------------------------
def _match(doc, flt):
    for k, want in flt.items():
        got = doc.get(k)
        if isinstance(want, dict):
            for op, val in want.items():
                if op == "$gt" and not (got is not None and got > val):
                    return False
                if op == "$in" and got not in val:
                    return False
                if op == "$regex" and not str(got).startswith(val.lstrip("^")):
                    return False
        elif got != want:
            return False
    return True


class FakeCursor:
    def __init__(self, docs):
        self.docs = docs

    def sort(self, spec):
        for key, d in reversed(spec):
            self.docs.sort(key=lambda x: x.get(key), reverse=d < 0)
        return self

    def limit(self, n):
        self.docs = self.docs[:n]
        return self

    def __aiter__(self):
        async def gen():
            for d in self.docs:
                yield d
        return gen()


class FakeCol:
    def __init__(self):
        self.d = {}

    def _find(self, flt):
        return [x for x in self.d.values() if _match(x, flt)]

    @staticmethod
    def _apply(doc, upd):
        for k, v in upd.get("$set", {}).items():
            doc[k] = v
        for k, v in upd.get("$inc", {}).items():
            doc[k] = doc.get(k, 0) + v
        for k, v in upd.get("$push", {}).items():
            arr = doc.setdefault(k, [])
            arr.extend(v["$each"])
            if "$slice" in v:
                doc[k] = arr[v["$slice"]:]

    async def find_one(self, flt):
        r = self._find(flt)
        return dict(r[0]) if r else None

    def find(self, flt):
        return FakeCursor([dict(x) for x in self._find(flt)])

    async def count_documents(self, flt):
        return len(self._find(flt))

    async def replace_one(self, flt, doc, upsert=False):
        self.d["current" if "key" in doc else doc["_id"]] = dict(doc)

    async def delete_many(self, flt):
        for x in self._find(flt):
            self.d = {k: v for k, v in self.d.items() if v is not x}

    async def create_index(self, *a, **k):
        return None

    async def update_one(self, flt, upd, upsert=False):
        r = self._find(flt)
        if not r and upsert:
            doc = {"_id": flt["_id"]}
            self.d[doc["_id"]] = doc
            r = [doc]
        for x in r[:1]:
            self._apply(x, upd)
        return types.SimpleNamespace(modified_count=len(r[:1]), matched_count=len(r[:1]))

    async def find_one_and_update(self, flt, upd, upsert=False, return_document=0):
        r = self._find(flt)
        before = dict(r[0]) if r else None
        if not r and upsert:
            doc = {"_id": flt["_id"]}
            self.d[doc["_id"]] = doc
            r = [doc]
        if not r:
            return None
        self._apply(r[0], upd)
        return dict(r[0]) if return_document else before


class FakeBot:
    def __init__(self):
        self.sent = []

    async def send_message(self, chat_id, text, parse_mode=None):
        self.sent.append((chat_id, text))


class TournamentFlow(unittest.TestCase):
    def setUp(self):
        import service_tournament as T
        self.T = T
        self.cols = {}
        self.chars = {}
        self.paid = []

        def col(name):
            return self.cols.setdefault(name, FakeCol())

        async def gs(force=False):
            return dict(GAME_DEFAULTS)

        async def fighter(uid, level, evo):
            if uid not in self.chars:
                return None
            f = E.new_fighter(self.chars[uid], level, {"zanjutsu": 20, "hoho": 10, "kido": 5, "hakuda": 12, "reiatsu": 10},
                              300 + uid, 120, standard_weapon(level), armor=standard_armor(level))
            return f

        async def prize(uid, d):
            self.paid.append((uid, d.get("prize_coins"), d.get("prize_item")))
            return "paid"
        self.patches = [mock.patch.object(T, "col", col), mock.patch.object(T, "game_settings", gs),
                        mock.patch.object(T, "_fighter", fighter), mock.patch.object(T, "_grant_prize", prize)]
        for p in self.patches:
            p.start()
        self.bot = FakeBot()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def _open(self, hours=27):
        return run(self.T.open_training(-100, hours))

    def test_open_twice_is_refused_until_cancelled(self):
        self.assertEqual(self._open()[0], "ok")
        self.assertEqual(self._open()[0], "active")
        self.assertTrue(run(self.T.cancel()))
        self.assertEqual(self._open()[0], "ok")

    def test_training_open_only_inside_the_window(self):
        self._open()
        self.assertTrue(run(self.T.training_open()))
        self.cols["tournaments"].d["current"]["train_end"] = 1
        self.assertFalse(run(self.T.training_open()))

    def test_points_and_pair_cap_are_exact(self):
        self._open()
        for _ in range(TRAIN_PAIR_CAP + 3):  # the same pair duels many times
            run(self.T.record_training(1, 2, "A", "B"))
        pts = {d["uid"]: d["pts"] for d in self.cols["tour_points"].d.values()}
        self.assertEqual(pts, {1: TRAIN_WIN_PTS * TRAIN_PAIR_CAP, 2: TRAIN_LOSS_PTS * TRAIN_PAIR_CAP})

    def test_concurrent_settles_cannot_beat_the_cap(self):
        self._open()

        async def go():
            await asyncio.gather(*[self.T.record_training(1, 2, "A", "B") for _ in range(10)])
        run(go())
        self.assertEqual(self.cols["tour_pairs"].d[next(iter(self.cols["tour_pairs"].d))]["n"], 10)
        self.assertEqual(sum(d["pts"] for d in self.cols["tour_points"].d.values()),
                         (TRAIN_WIN_PTS + TRAIN_LOSS_PTS) * TRAIN_PAIR_CAP)

    def test_duel_started_after_the_window_gives_nothing(self):
        self._open()
        run(self.T.record_training(1, 2, "A", "B", started_at=2 ** 40))
        self.assertEqual(self.cols.get("tour_points", FakeCol()).d, {})

    def test_start_needs_two_entrants(self):
        self._open()
        self.assertEqual(run(self.T.start_bracket())[0], "training")
        self.assertEqual(run(self.T.start_bracket(force=True))[0], "few")
        self.assertEqual(self.cols["tournaments"].d["current"]["phase"], "done")

    def _play_all(self, n):
        self._open()
        for uid in range(1, n + 1):
            self.chars[uid] = f"P{uid}"
            run(self.T.record_training(uid, 1000 + uid, f"P{uid}", f"X{uid}"))
        # X-players have no character: they are seeded too, so give them one
        for uid in range(1, n + 1):
            self.chars[1000 + uid] = f"X{uid}"
        self.assertEqual(run(self.T.start_bracket(force=True))[0], "ok")
        doc = self.cols["tournaments"].d["current"]
        total = sum(1 for u in doc["alive"] if u is not None)
        for _ in range(20):
            doc = self.cols["tournaments"].d["current"]
            if doc["phase"] == "done":
                break
            doc["next_at"] = 0
            run(self.T.tick(self.bot))
        return total, self.cols["tournaments"].d["current"]

    def test_full_bracket_crowns_one_champion(self):
        total, doc = self._play_all(6)
        self.assertEqual(total, 12)
        self.assertEqual(doc["phase"], "done")
        self.assertIn(doc["champion"], doc["names"] and [int(k) for k in doc["names"]])
        self.assertEqual(len(self.paid), 1)
        self.assertEqual(self.paid[0][0], doc["champion"])
        self.assertTrue(any("🏆" in t for _c, t in self.bot.sent))
        self.assertTrue(all(len(t) <= 4096 for _c, t in self.bot.sent))

    def test_a_round_is_never_played_twice(self):
        self._open()
        for uid in (1, 2, 3, 4):
            self.chars[uid] = f"P{uid}"
        run(self.T.record_training(1, 2, "P1", "P2"))
        run(self.T.record_training(3, 4, "P3", "P4"))
        run(self.T.start_bracket(force=True))
        doc = self.cols["tournaments"].d["current"]
        doc["next_at"] = 0
        stale = dict(doc)

        async def twice():
            await self.T._play_round(self.bot, stale)
            await self.T._play_round(self.bot, stale)  # same stale snapshot: the compare-and-set must refuse it
        run(twice())
        self.assertEqual(self.cols["tournaments"].d["current"]["round"], 1)

    def test_a_broken_match_does_not_freeze_the_bracket(self):
        self._open()
        for uid in (1, 2):
            self.chars[uid] = f"P{uid}"
        run(self.T.record_training(1, 2, "P1", "P2"))
        run(self.T.start_bracket(force=True))
        self.cols["tournaments"].d["current"]["next_at"] = 0
        with mock.patch.object(self.T, "play_match", side_effect=RuntimeError("boom")):
            run(self.T.tick(self.bot))
        self.assertEqual(self.cols["tournaments"].d["current"]["phase"], "done")

    def test_deleted_character_forfeits(self):
        self._open()
        self.chars[1] = "P1"  # player 2 has no character any more
        run(self.T.record_training(1, 2, "P1", "P2"))
        run(self.T.start_bracket(force=True))
        self.cols["tournaments"].d["current"]["next_at"] = 0
        run(self.T.tick(self.bot))
        self.assertEqual(self.cols["tournaments"].d["current"]["champion"], 1)

    def test_prize_is_stored_per_tournament(self):
        self._open()
        self.assertTrue(run(self.T.set_prize(coins=5, item="wp_001")))
        d = self.cols["tournaments"].d["current"]
        self.assertEqual((d["prize_coins"], d["prize_item"]), (5, "wp_001"))
        run(self.T.cancel())
        self.assertFalse(run(self.T.set_prize(coins=1)))

    def test_status_text_runs_in_every_phase(self):
        self.assertIn("No tournament", run(self.T.status_text()))
        self._open()
        self.assertIn("Training", run(self.T.status_text()))


if __name__ == "__main__":
    unittest.main()
