"""Isolated service tests: no MongoDB, Telegram or live bot required."""
import asyncio
import importlib
import sys
import types
import unittest


class FakeCollection:
    def __init__(self):
        self.docs = {}
        self.updates = []

    async def insert_one(self, doc):
        if doc["_id"] in self.docs:
            raise RuntimeError("duplicate key")
        self.docs[doc["_id"]] = dict(doc)
        return types.SimpleNamespace(inserted_id=doc["_id"])

    async def find_one(self, query):
        if "_id" in query:
            doc = self.docs.get(query["_id"])
            if doc and all(doc.get(k) == v for k, v in query.items() if k != "_id"):
                return dict(doc)
            return None
        return None

    @staticmethod
    def _match(doc, query):
        for k, v in query.items():
            if k == "_id":
                continue
            if isinstance(v, dict) and "$exists" in v:
                if (k in doc) != bool(v["$exists"]):
                    return False
            elif doc.get(k) != v:
                return False
        return True

    @staticmethod
    def _apply(doc, update):
        doc.update(update.get("$set", {}))
        for k in update.get("$unset", {}):
            doc.pop(k, None)

    async def update_one(self, query, update):
        self.updates.append((query, update))
        doc = self.docs.get(query.get("_id"))
        if doc:
            self._apply(doc, update)
        return types.SimpleNamespace(modified_count=1 if doc else 0)

    async def find_one_and_update(self, query, update):
        doc = self.docs.get(query.get("_id"))
        if not doc or not self._match(doc, query):
            return None
        before = {k: (dict(v) if isinstance(v, dict) else v) for k, v in doc.items()}
        self._apply(doc, update)
        return before

    async def delete_one(self, query):
        doc = self.docs.get(query.get("_id"))
        if doc and self._match(doc, query):
            del self.docs[query["_id"]]
            return types.SimpleNamespace(deleted_count=1)
        return types.SimpleNamespace(deleted_count=0)


class FinalJudgmentServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_database = sys.modules.get("database")
        cls.original_player = sys.modules.get("service_player")
        cls.original_combat = sys.modules.get("service_combat")
        cls.db = types.ModuleType("database")
        cls.player = types.ModuleType("service_player")
        cls.collections = {}
        cls.db.col = lambda name: cls.collections.setdefault(name, FakeCollection())
        cls.player.today = lambda: "2026-11-25"
        async def get_char(uid):
            return {"user_id": uid, "level": 100}
        cls.player.get_char = get_char
        sys.modules["database"] = cls.db
        sys.modules["service_player"] = cls.player
        sys.modules.pop("service_final_judgment", None)
        cls.svc = importlib.import_module("service_final_judgment")

    @classmethod
    def tearDownClass(cls):
        sys.modules.pop("service_final_judgment", None)
        if cls.original_database is None:
            sys.modules.pop("database", None)
        else:
            sys.modules["database"] = cls.original_database
        if cls.original_player is None:
            sys.modules.pop("service_player", None)
        else:
            sys.modules["service_player"] = cls.original_player
        if cls.original_combat is None:
            sys.modules.pop("service_combat", None)
        else:
            sys.modules["service_combat"] = cls.original_combat

    def setUp(self):
        self.collections.clear()
        # Nov 26: the event is closed in production (FJ_OPEN = False). These tests cover the open event's rules.
        self._fj_open = self.svc.FJ_OPEN
        self.svc.FJ_OPEN = True
        self.addCleanup(setattr, self.svc, "FJ_OPEN", self._fj_open)

    def _combat_stub(self, pve_start=None):
        m = types.ModuleType("service_combat")
        async def active_pve(uid):
            return None
        async def duel_busy(uid):
            return False
        async def start(uid, lang, dungeon=None, carry=None):
            return {"sid": "next", "dungeon": dungeon, "carry": carry}
        m.active_pve = active_pve
        m.duel_busy = duel_busy
        m.pve_start = pve_start or start
        return m

    def test_wave_counts_match_the_ten_stage_gauntlet(self):
        self.assertEqual(self.svc.STAGE_WAVES, {1: 100, 2: 5, 6: 30, 9: 5})

    def test_entry_is_consumed_once_per_day(self):
        sys.modules["service_combat"] = self._combat_stub()
        status, doc = asyncio.run(self.svc.start(42, "en"))
        self.assertEqual(status, "ok")
        self.assertEqual(doc["dungeon"]["wave_total"], 100)
        status2, _ = asyncio.run(self.svc.start(42, "en"))
        self.assertEqual(status2, "spent")

    def test_win_advances_to_next_wave_and_carries_resources(self):
        captured = {}
        async def start(uid, lang, dungeon=None, carry=None):
            captured.update(dungeon=dungeon, carry=carry)
            return {"sid": "next", "dungeon": dungeon}
        sys.modules["service_combat"] = self._combat_stub(start)
        doc = {"user_id": 42, "lang": "en", "dungeon": {"stage": 1, "wave": 1, "wave_total": 100,
                "attempt_day": "2026-11-25"}, "state": {"a": {"hp": 400, "max_hp": 1000, "re": 200,
                "max_re": 500, "x": {"gauge": 35}, "shield": 80, "mods": {"artifact_lives": 0}}}}
        result = asyncio.run(self.svc.settle(doc, True))["final_judgment"]
        self.assertEqual(result["next"]["dungeon"]["wave"], 2)
        self.assertEqual(captured["carry"]["hp"], 0.4)
        self.assertEqual(captured["carry"]["re"], 0.4)
        self.assertEqual(captured["carry"]["gauge"], 35)
        self.assertEqual(captured["carry"]["shield"], 80)

    def test_last_wave_of_stage_one_advances_to_stage_two(self):
        sys.modules["service_combat"] = self._combat_stub()
        doc = {"user_id": 42, "lang": "en", "dungeon": {"stage": 1, "wave": 100, "wave_total": 100,
                "attempt_day": "2026-11-25"}, "state": {"a": {"hp": 900, "max_hp": 1000, "re": 500,
                "max_re": 500, "x": {}, "shield": 0, "mods": {}}}}
        result = asyncio.run(self.svc.settle(doc, True))["final_judgment"]
        self.assertEqual(result["next"]["dungeon"]["stage"], 2)
        self.assertEqual(result["next"]["dungeon"]["wave_total"], 5)

    def test_final_clear_awards_the_almighty_and_records_permanent_clear(self):
        async def claim(uid, aid, from_state="dropped"):
            self.assertEqual((aid, from_state), ("art_almighty", "free"))
            return "ok"
        drops = types.ModuleType("service_drops")
        drops.art_claim = claim
        previous = sys.modules.get("service_drops")
        sys.modules["service_drops"] = drops
        try:
            self.collections.setdefault("artifacts", FakeCollection()).docs["art_almighty"] = {
                "_id": "art_almighty", "state": "free", "held": 0}
            sys.modules["service_combat"] = self._combat_stub()
            doc = {"user_id": 42, "lang": "en", "dungeon": {"stage": 10, "wave": 1, "wave_total": 1,
                    "attempt_day": "2026-11-25"}, "state": {"a": {"hp": 100, "max_hp": 100, "re": 100,
                    "max_re": 100, "x": {}, "shield": 0, "mods": {}}}}
            result = asyncio.run(self.svc.settle(doc, True))["final_judgment"]
            self.assertTrue(result["won"])
            self.assertEqual(result["reward"], "👁️ The Almighty")
            updates = self.collections["characters"].updates
            self.assertTrue(any(u[1].get("$set", {}).get("final_judgment_cleared") for u in updates))
        finally:
            if previous is None:
                sys.modules.pop("service_drops", None)
            else:
                sys.modules["service_drops"] = previous

    def test_loss_ends_attempt_and_does_not_spawn_next_fight(self):
        sys.modules["service_combat"] = self._combat_stub()
        key = self.svc._attempt_id(42, "2026-11-25")
        self.collections.setdefault("final_judgment_attempts", FakeCollection()).docs[key] = {"_id": key, "status": "running"}
        doc = {"user_id": 42, "dungeon": {"stage": 6, "wave": 12, "wave_total": 30,
                "attempt_day": "2026-11-25"}, "state": {}}
        result = asyncio.run(self.svc.settle(doc, False))["final_judgment"]
        self.assertFalse(result["won"])
        self.assertEqual(self.collections["final_judgment_attempts"].docs[key]["status"], "failed")

    def test_failed_first_encounter_gives_the_daily_entry_back(self):
        async def broken(uid, lang, dungeon=None, carry=None):
            raise RuntimeError("db down")
        sys.modules["service_combat"] = self._combat_stub(broken)
        with self.assertRaises(RuntimeError):
            asyncio.run(self.svc.start(42, "en"))
        sys.modules["service_combat"] = self._combat_stub()
        status, doc = asyncio.run(self.svc.start(42, "en"))
        self.assertEqual(status, "ok")
        self.assertEqual(doc["dungeon"]["stage"], 1)

    def test_run_is_resumable_when_the_next_encounter_could_not_be_created(self):
        sys.modules["service_combat"] = self._combat_stub()
        asyncio.run(self.svc.start(42, "en"))
        doc = {"user_id": 42, "lang": "en",
               "dungeon": {"stage": 2, "wave": 5, "wave_total": 5, "attempt_day": "2026-11-25"},
               "state": {"a": {"hp": 50, "max_hp": 100, "re": 30, "max_re": 60, "shield": 7,
                               "x": {"gauge": 40}, "mods": {"artifact_lives": 1}}}}

        async def broken(uid, lang, dungeon=None, carry=None):
            raise RuntimeError("db down")
        sys.modules["service_combat"] = self._combat_stub(broken)
        with self.assertRaises(RuntimeError):
            asyncio.run(self.svc.settle(doc, True))
        # the run is parked at stage 3 with its carried state; today's entry is NOT lost
        sys.modules["service_combat"] = self._combat_stub()
        status, resumed = asyncio.run(self.svc.start(42, "en"))
        self.assertEqual(status, "ok")
        self.assertEqual((resumed["dungeon"]["stage"], resumed["dungeon"]["wave"]), (3, 1))
        self.assertAlmostEqual(resumed["carry"]["hp"], 0.5)
        self.assertEqual(resumed["carry"]["shield"], 7)
        # and it can only be resumed once
        status2, _ = asyncio.run(self.svc.start(42, "en"))
        self.assertEqual(status2, "spent")


if __name__ == "__main__":
    unittest.main()
