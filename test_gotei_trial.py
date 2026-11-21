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
from engine_tournament import (NEUTRAL_RACE, TRAIN_LOSS_PTS, TRAIN_PAIR_CAP, TRAIN_WIN_PTS, UNKNOWN, best_of,  # noqa: E402
                               bracket_columns, mastery_points, pair_round, play_series, points_for_level, seed_bracket,
                               standard_armor, standard_fighter, standard_stats, standard_weapon, training_points)


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


# ---- series and bracket picture data -----------------------------------------------------------------------------
class Series(unittest.TestCase):
    def test_best_of_by_round(self):
        self.assertEqual([best_of(n) for n in (32, 16, 8, 4, 2)], [3, 3, 3, 5, 7])

    def test_series_stops_at_a_majority(self):
        f = lambda n: standard_fighter(n, 30)
        rng = random.Random(3)
        for bo in (1, 3, 5, 7):
            side, (wa, wb) = play_series(f("A"), f("B"), rng, bo)
            self.assertEqual(max(wa, wb), bo // 2 + 1)
            self.assertEqual(side, "a" if wa > wb else "b")

    def test_columns_follow_the_history(self):
        order = seed_bracket([1, 2, 3, 4])
        cols, scores = bracket_columns(order, [])
        self.assertEqual([len(c) for c in cols], [4, 2, 1])
        self.assertTrue(all(v == UNKNOWN for v in cols[1] + cols[2]))
        hist = [[{"a": 1, "b": 4, "w": 1, "s": "2-0"}, {"a": 2, "b": 3, "w": 3, "s": "2-1"}]]
        cols, scores = bracket_columns(order, hist)
        self.assertEqual(cols[1], [1, 3])
        self.assertEqual(scores[0], ["2-0", "2-1"])
        self.assertEqual(cols[2], [UNKNOWN])

    def test_mastery_is_capped(self):
        self.assertEqual(mastery_points(5, 20), 5)
        self.assertEqual(mastery_points(99, 20), 20)
        self.assertEqual(mastery_points(99, 0), 0)


# ---- the standard kit: NO race -------------------------------------------------------------------------------------
class StandardKit(unittest.TestCase):
    def test_points_for_level(self):
        self.assertEqual(points_for_level(1), 0)
        self.assertEqual(points_for_level(5), 3 * 4 + 1)
        self.assertEqual(points_for_level(30), 29 * 3 + 6)

    def test_every_stat_is_equal_and_mastery_adds_points(self):
        st = standard_stats(30)
        self.assertEqual(len(set(st.values())), 1)
        self.assertAlmostEqual(sum(standard_stats(30, 10).values()) - sum(st.values()), 10, delta=0.02)

    def test_fighter_has_no_race_at_all(self):
        from data_race_rules import RACE_ABILITIES, RACE_CONTEXT_DMG
        from data_race_tech import ABILITY_STAT, RACE_TECH
        from data_bleachfx import RACE_KILLER, RACE_SIG
        f = standard_fighter("A", 30)
        self.assertEqual(f["race"], NEUTRAL_RACE)
        for table in (RACE_CONTEXT_DMG, ABILITY_STAT, RACE_TECH, RACE_KILLER, RACE_SIG):
            self.assertNotIn(NEUTRAL_RACE, table)
        self.assertIsNone(f["sig"])
        self.assertIsNone(f["gen"])
        self.assertEqual(f["mods"], {})
        self.assertNotIn("evo", f)
        for act in ("sg", "t1", "t2", "t3", "kd", "bk", "ch", "gc", "gt", "blv", "bla", "bal", "neg", "gar", "bt", "gs"):
            self.assertFalse(E.can(f, act), act)
        self.assertEqual(f["weapon"]["skills"], [])  # no lifesteal, no reiatsu drain, no weapon skill of any kind
        self.assertEqual(E.race_factor(f), 1.0)

    def test_two_fighters_are_identical_whoever_the_player_is(self):
        a, b = standard_fighter("A", 30), standard_fighter("B", 30)
        a.pop("name"), b.pop("name")
        self.assertEqual(a, b)

    def test_weapon_and_armor_are_level_scaled_and_equal(self):
        w = standard_weapon(30)
        self.assertEqual(w, standard_weapon(30))
        self.assertGreater(standard_weapon(40)["attack"], w["attack"])
        self.assertEqual(w["type"], "melee")
        self.assertEqual(w["skills"], [])
        self.assertGreater(standard_armor(40), standard_armor(30))
        self.assertEqual(standard_fighter("A", 30)["armor"], standard_armor(30))

    def test_the_mirror_match_is_fair(self):
        """Equal fighters: side a wins about half the games (no hidden edge for the first slot)."""
        rng = random.Random(11)
        wins = sum(1 for _ in range(300) if play_series(standard_fighter("A", 30), standard_fighter("B", 30), rng, 1)[0] == "a")
        self.assertTrue(110 < wins < 190, wins)

    def test_mastery_gives_a_small_real_edge(self):
        rng = random.Random(5)
        wins = sum(1 for _ in range(300) if play_series(standard_fighter("A", 30, 20), standard_fighter("B", 30, 0), rng, 1)[0] == "a")
        self.assertGreater(wins, 150)
        self.assertLess(wins, 290)  # an edge, not a guaranteed win (long fights since HP x6 let a small edge add up)


class TrainingDuelKit(unittest.TestCase):
    def test_duel_accept_uses_the_standard_kit_in_tournament_duels(self):
        src = open(os.path.join(_ROOT, "service_combat.py"), encoding="utf-8").read()
        self.assertIn("standard_fighter", src)
        self.assertIn('doc.get("tournament")', src)


class RenderPicture(unittest.TestCase):
    def test_bracket_picture_for_every_size(self):
        try:
            import PIL  # noqa: F401
        except ImportError:
            self.skipTest("Pillow not installed")
        import tournament_render as R
        for n in (2, 3, 5, 8, 13, 32):
            order = seed_bracket(list(range(1, n + 1)))
            names = {i: f"P{i}" for i in range(1, n + 1)}
            png = R.render_bracket(order, names, [], None, "GOTEI TRIAL", "x", "")
            self.assertTrue(png.startswith(b"\x89PNG"), n)

    def test_name_cleaning(self):
        import tournament_render as R
        self.assertEqual(R.clean_name("Ichigo ⚔️🔥"), "Ichigo")
        self.assertEqual(R.clean_name("🔥"), "Player")
        self.assertEqual(R.clean_name("ایچیگو"), "ایچیگو")


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

    async def send_photo(self, chat_id, photo, caption=None, parse_mode=None):
        self.photos = getattr(self, "photos", 0) + 1


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

        async def fighter(uid, name, level, mastery):
            if uid not in self.chars:
                return None
            return standard_fighter(name, level, mastery)

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
        self.assertEqual(len(doc["hist"]), doc["rounds_total"])          # every round is kept for the picture
        self.assertTrue(all(m["s"] for rnd in doc["hist"] for m in rnd))
        self.assertGreaterEqual(getattr(self.bot, "photos", 0), doc["rounds_total"])  # draw + every round got a picture
        self.assertTrue(doc["draw_sent"])

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
        with mock.patch.object(self.T, "play_series", side_effect=RuntimeError("boom")):
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
