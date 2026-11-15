"""Service-level tests for the wheels with an in-memory fake DB (no Mongo, no Telegram needed).
Stubs only the modules that need motor/pymongo/Telegram; the wheel logic itself is the real code."""
import sys
import types
import unittest
from unittest import mock


def _stub(name, **attrs):
    m = types.ModuleType(name)
    m.__dict__.update(attrs)
    sys.modules.setdefault(name, m)
    return sys.modules[name]


try:
    from pymongo import ReturnDocument  # noqa: F401
except ImportError:
    class ReturnDocument:
        AFTER = "after"
    _stub("pymongo", ReturnDocument=ReturnDocument)

FAKE_STATE = {"collections": {}, "counters": {}, "settings": {}}


def _getp(doc, path, default=None):
    cur = doc
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def _setp(doc, path, val):
    parts = path.split(".")
    cur = doc
    for p in parts[:-1]:
        cur = cur.setdefault(p, {})
    cur[parts[-1]] = val


def _match(doc, flt):
    for k, v in flt.items():
        if isinstance(v, dict) and "$gte" in v:
            if (_getp(doc, k, 0) or 0) < v["$gte"]:
                return False
        elif _getp(doc, k) != v:
            return False
    return True


class FakeResult:
    def __init__(self, n):
        self.modified_count = n


class FakeCol:
    def __init__(self, docs):
        self.docs = docs

    def _apply(self, doc, upd):
        for path, v in upd.get("$inc", {}).items():
            _setp(doc, path, (_getp(doc, path, 0) or 0) + v)
        for path, v in upd.get("$set", {}).items():
            _setp(doc, path, v)

    async def insert_one(self, doc):
        self.docs.append(dict(doc))

    async def create_index(self, *a, **k):
        return "ok"

    async def find_one(self, flt):
        for d in self.docs:
            if _match(d, flt):
                return dict(d)
        return None

    async def find_one_and_update(self, flt, upd, upsert=False, return_document=None):
        for d in self.docs:
            if _match(d, flt):
                self._apply(d, upd)
                return dict(d)
        if upsert:
            d = dict(flt)
            self._apply(d, upd)
            self.docs.append(d)
            return dict(d)
        return None

    async def update_one(self, flt, upd, upsert=False):
        for d in self.docs:
            if _match(d, flt):
                self._apply(d, upd)
                return FakeResult(1)
        if upsert:
            d = dict(flt)
            self._apply(d, upd)
            self.docs.append(d)
            return FakeResult(1)
        return FakeResult(0)


def _col(name):
    return FakeCol(FAKE_STATE["collections"].setdefault(name, []))


async def _bump(key, amount, cap, ttl_hours=48):
    n = FAKE_STATE["counters"].get(key, 0)
    if n + amount > cap:
        return False
    FAKE_STATE["counters"][key] = n + amount
    return True


async def _counter_get(key):
    return FAKE_STATE["counters"].get(key, 0)


async def _settings(force=False):
    base = {"wheel2_enabled": True, "wheel_free_daily": 0, "pity_leg": 30, "pity_myth": 90,
            "coin_rate": 1.0, "core_quest_chance": 1.0, "core_dungeon_chance": 1.0, "core_day_cap": 1}
    base.update(FAKE_STATE["settings"])
    return base


async def _no_cd(key, seconds):
    return 0


async def _noop(*a, **k):
    return True


async def _char(uid):
    return {"level": 5}


_stub("database", col=_col, game_settings=_settings, try_cooldown=_no_cd, bump_counter=_bump,
      counter_get=_counter_get)
_stub("data_world", day_id=lambda now=None: "d1")
_stub("service_economy", inv_add=_noop)
_stub("service_extras", pick_item=lambda cat, idx, rng=None: "item_x")
_stub("service_player", add_coins=_noop, add_xp=_noop, get_char=_char)

import service_cores as sc  # noqa: E402
import service_wheels as sw  # noqa: E402

OWNER = 1


class SpinService(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        FAKE_STATE["collections"].clear()
        FAKE_STATE["counters"].clear()
        FAKE_STATE["settings"].clear()

    def _wallet(self, uid=5):
        return next(d for d in FAKE_STATE["collections"]["wheel_wallet"] if d["_id"] == uid)

    async def test_paid_spin_debits_cores(self):
        await sc.grant_cores(5, 100, "test")
        status, res = await sw.spin(5, "w_ichigo", OWNER)
        self.assertEqual(status, "ok")
        self.assertEqual(res["cost"], 60)
        self.assertEqual(res["cores_left"], 40)
        self.assertEqual(self._wallet()["cores"], 40)

    async def test_not_enough_cores_rolls_back_spin_count(self):
        await sc.grant_cores(5, 10, "test")
        status, res = await sw.spin(5, "w_ichigo", OWNER)
        self.assertEqual(status, "funds")
        self.assertIsNone(res)
        self.assertEqual(self._wallet()["spins"].get("w_ichigo", 0), 0)
        self.assertEqual(self._wallet()["cores"], 10)

    async def test_owner_only_wheel(self):
        await sc.grant_cores(5, 999, "test")
        self.assertEqual((await sw.spin(5, "w_hitsugaya", OWNER))[0], "locked")
        await sc.grant_cores(OWNER, 25, "test")
        self.assertEqual((await sw.spin(OWNER, "w_hitsugaya", OWNER))[0], "ok")

    async def test_price_tier_after_ten_spins(self):
        await sc.grant_cores(5, 10_000, "test")
        for _ in range(10):
            await sw.spin(5, "w_yamamoto", OWNER)  # 10 spins at x1
        status, res = await sw.spin(5, "w_yamamoto", OWNER)  # 11th: x2
        self.assertEqual(status, "ok")
        self.assertEqual(res["n"], 11)
        self.assertEqual(res["cost"], 14 * 2)

    async def test_free_spin_costs_nothing(self):
        FAKE_STATE["settings"]["wheel_free_daily"] = 1
        status, res = await sw.spin(5, "w_ichigo", OWNER)
        self.assertEqual(status, "ok")
        self.assertTrue(res["free"])
        self.assertEqual(res["cost"], 0)
        # second spin the same day is paid, and there are no cores -> funds
        self.assertEqual((await sw.spin(5, "w_ichigo", OWNER))[0], "funds")

    async def test_disabled_wheels(self):
        FAKE_STATE["settings"]["wheel2_enabled"] = False
        self.assertEqual((await sw.spin(5, "w_ichigo", OWNER))[0], "off")

    async def test_pity_streak_updates_match_rarity(self):
        FAKE_STATE["settings"]["wheel_free_daily"] = 1000
        for _ in range(25):
            status, res = await sw.spin(5, "w_nowruz", OWNER)
            self.assertEqual(status, "ok")
            leg = self._wallet()["pity"]["w_nowruz"]["leg"]
            if res["rarity"] in ("Legendary", "Mythic", "Legacy"):
                self.assertEqual(leg, 0)
            else:
                self.assertGreaterEqual(leg, 1)
        self.assertEqual(self._wallet()["spins"]["w_nowruz"], 25)


class SoulCoreEconomy(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        FAKE_STATE["collections"].clear()
        FAKE_STATE["counters"].clear()
        FAKE_STATE["settings"].clear()

    def _logs(self):
        return FAKE_STATE["collections"].get("core_log", [])

    async def test_hard_quest_can_grant(self):
        self.assertTrue(await sc.on_quest_claim(5, "l_legend"))
        self.assertEqual(await sc.get_cores(5), 1)
        self.assertEqual(self._logs()[-1]["reason"], "quest:l_legend")

    async def test_easy_quest_never_grants(self):
        self.assertFalse(await sc.on_quest_claim(5, "m_first"))
        self.assertEqual(await sc.get_cores(5), 0)

    async def test_normal_and_hard_dungeon_never_grant(self):
        self.assertFalse(await sc.on_dungeon_clear(5, "normal", "trial"))
        self.assertFalse(await sc.on_dungeon_clear(5, "hard", "trial"))
        self.assertEqual(await sc.get_cores(5), 0)

    async def test_abyss_dungeon_grants(self):
        self.assertTrue(await sc.on_dungeon_clear(5, "abyss", "dangai_rift"))
        self.assertEqual(await sc.get_cores(5), 1)

    async def test_daily_cap_blocks_second_core(self):
        self.assertTrue(await sc.on_quest_claim(5, "b_bankai"))
        self.assertFalse(await sc.on_dungeon_clear(5, "legendary", "dangai_rift"))  # same day, cap 1
        self.assertEqual(await sc.get_cores(5), 1)

    async def test_low_chance_mostly_fails(self):
        FAKE_STATE["settings"]["core_quest_chance"] = 0.03
        hits = 0
        for i in range(2000):
            FAKE_STATE["counters"].clear()  # ignore the cap here: only the chance matters
            hits += await sc.on_quest_claim(i, "l_legend")
        self.assertLess(hits, 150)  # ~3% expected, well below 7.5%

    async def test_spin_spend_is_logged(self):
        await sc.grant_cores(5, 100, "test")
        status, _ = await sw.spin(5, "w_ichigo", OWNER)
        self.assertEqual(status, "ok")
        self.assertEqual(self._logs()[-1]["n"], -60)
        self.assertEqual(self._logs()[-1]["reason"], "spin:w_ichigo")


if __name__ == "__main__":
    unittest.main()
