"""Guild Quest Board: the generator and reward tables (pure), and the service glue (start, once-a-day, daily cap, payout)
against a small in-memory stand-in for MongoDB. The real pve_start / pve_settle wiring needs MongoDB and the Telegram
libraries and is not covered here."""
import asyncio
import random
import sys
import types
import unittest

import data_guildquest as G
from config import GAME_DEFAULTS


# ---- pure ------------------------------------------------------------------------------------------------------------
class BoardTests(unittest.TestCase):
    def test_board_is_random_per_day_but_fixed_for_a_seed(self):
        a = G.make_board(7, "2026-11-20", 40)
        self.assertEqual(a, G.make_board(7, "2026-11-20", 40))
        self.assertTrue(any(G.make_board(7, f"2026-12-{d:02d}", 40) != a for d in range(1, 10)))

    def test_slots_levels_and_ranks(self):
        for lvl in (1, 5, 40, 120):
            for seed in range(30):
                b = G.make_board(seed, "d", lvl)
                self.assertEqual([q["slot"] for q in b], list(range(G.BOARD_SIZE)))
                for q, (lo, hi) in zip(b, G.SLOT_OFFSETS):
                    self.assertGreaterEqual(q["lvl"], 1)
                    self.assertLessEqual(q["lvl"] - lvl, max(hi, 1 - lvl))  # a quest is never below level 1
                    self.assertGreaterEqual(q["lvl"] - lvl, max(lo, 1 - lvl))
                    if lvl > 5:  # no clamping at level 1: the level gap and the rank agree
                        self.assertEqual(q["rank"], G.rank_of(q["lvl"] - lvl))
                    else:
                        self.assertLessEqual(q["rank"], G.rank_of(max(hi, q["lvl"] - lvl)))
                    self.assertIn(q["type"], G.QTYPES)
                    self.assertEqual(q["stages"], G.stage_count(q["rank"], q["type"]))

    def test_regions_are_only_unlocked_ones(self):
        from data_extras2 import ADVENTURES
        for seed in range(40):
            for q in G.make_board(seed, "d", 10):
                self.assertLessEqual(ADVENTURES[q["region"]]["level"], 10)
        self.assertEqual(set(G.regions_for(1)), {"menos_forest", "rukongai_outskirts"})

    def test_rank_steps(self):
        self.assertEqual([G.rank_of(o) for o in (-4, -3, -2, 0, 2, 4, 6, 8, 20)], [0, 0, 1, 2, 3, 4, 5, 6, 6])

    def test_rewards_never_shrink_with_rank(self):
        for tbl in (G.ITEM_IDX, G.ZNP_MASTERY, G.ZNP_BOND):
            self.assertEqual(tbl, sorted(tbl))
            self.assertEqual(len(tbl), len(G.RANKS))
        for t in G.QTYPES:
            self.assertEqual([G.item_count(r, t) for r in range(7)], sorted(G.item_count(r, t) for r in range(7)))
        self.assertEqual(G.item_count(3, "gauntlet"), G.item_count(3, "purge") + 1)
        self.assertEqual(G.stage_count(3, "gauntlet"), G.stage_count(3, "purge") + 1)
        self.assertLessEqual(G.stage_count(6, "gauntlet"), 6)

    def test_item_colours_are_real_rarities(self):
        self.assertTrue(all(0 <= i <= 5 for i in G.ITEM_IDX))

    def test_final_foe_by_type(self):
        from data_extras2 import ADVENTURES
        base = {"region": "dangai", "stages": 4, "total": 4}
        a = ADVENTURES["dangai"]
        self.assertEqual(G.quest_foe({**base, "type": "subjugation"}, 4), a["boss"])
        self.assertEqual(G.quest_foe({**base, "type": "gauntlet"}, 4), a["boss"])
        self.assertEqual(G.quest_foe({**base, "type": "purge"}, 4), a["foes"][-1])
        for _ in range(30):
            self.assertIn(G.quest_foe({**base, "type": "purge"}, 2), a["foes"][:-1])

    def test_titles_and_preview(self):
        q = G.make_board(1, "d", 30)[4]
        self.assertTrue(G.title(q, "fa").startswith(G.RANKS[q["rank"]]))
        self.assertTrue(G.title(q, "en").startswith(G.RANKS[q["rank"]]))
        pv = G.reward_preview(q)
        self.assertEqual(pv["items"], G.item_count(q["rank"], q["type"]))

    def test_settings_and_texts_exist(self):
        for k in ("gq_daily", "gq_xp_k", "gq_final_xp_mult", "gq_coin_base", "gq_coin_rank_k"):
            self.assertIn(k, GAME_DEFAULTS)
        import locale_en
        import locale_fa
        keys = {k for k in locale_fa.TEXT if k.startswith("gq_")} | {"m_avl"}
        self.assertEqual(keys, {k for k in locale_en.TEXT if k.startswith("gq_")} | {"m_avl"})
        for k in keys:
            self.assertTrue(locale_fa.TEXT[k] and locale_en.TEXT[k])
        locale_en.TEXT["gq_row"].format(mark="", title="", lvl=1, stages=1, warn="")
        locale_fa.TEXT["gq_row"].format(mark="", title="", lvl=1, stages=1, warn="")


# ---- service glue against an in-memory fake -----------------------------------------------------------------------------
class Dup(Exception):
    pass


class FakeDB:
    def __init__(self):
        self.t = {"counters": [], "characters": [], "gq_boards": []}
        self.coins = {}
        self.inv = {}

    def col(self, name):
        return FakeCol(self.t[name])


class FakeCol:
    def __init__(self, rows):
        self.rows = rows

    def _find(self, flt):
        return next((r for r in self.rows if all(r.get(k) == v for k, v in flt.items())), None)

    async def find_one(self, flt):
        return self._find(flt)

    async def find_one_and_update(self, flt, upd, upsert=False, return_document=False):
        r = self._find(flt)
        if r is None and upsert:
            r = dict(upd.get("$setOnInsert", {}))
            self.rows.append(r)
        return r

    async def update_one(self, flt, upd):
        r = self._find(flt)
        for path, n in (upd.get("$inc") or {}).items():
            cur = r
            parts = path.split(".")
            for p in parts[:-1]:
                cur = cur.setdefault(p, {})
            cur[parts[-1]] = cur.get(parts[-1], 0) + n
        return types.SimpleNamespace(modified_count=1 if r else 0)


def _install_stubs(db: FakeDB, state: dict):
    def mod(name, **attrs):
        m = types.ModuleType(name)
        m.__dict__.update(attrs)
        sys.modules[name] = m
        return m

    async def bump_counter(key, amount, cap, ttl_hours=48):
        c = db.col("counters")
        r = c._find({"key": key})
        if r is None:
            if amount > cap:
                return False
            db.t["counters"].append({"key": key, "n": amount})
            return True
        if r["n"] <= cap - amount:
            r["n"] += amount
            return True
        return False

    async def counter_get(key):
        r = db.col("counters")._find({"key": key})
        return int((r or {}).get("n", 0))

    async def try_cooldown(key, seconds):
        return 0

    async def game_settings(force=False):
        return dict(GAME_DEFAULTS)

    async def get_char(uid):
        return db.col("characters")._find({"user_id": uid})

    async def add_coins(uid, n, why):
        db.coins[uid] = db.coins.get(uid, 0) + n
        return True

    async def inv_add(uid, iid, q, force=False):
        db.inv.setdefault(uid, []).append(iid)
        return True

    async def roll_drop(uid, exact_idx=None, **kw):
        state["drops"].append(exact_idx)
        return f"item_{exact_idx}_{len(state['drops'])}"

    async def blocking_pve(uid):
        return state["busy"]

    async def pve_start(uid, lang, dungeon=None, **kw):
        if state.get("boom"):
            raise RuntimeError("boom")
        state["started"].append(dungeon)
        return {"dungeon": dungeon}

    mod("pymongo"); mod("pymongo.errors", DuplicateKeyError=Dup)
    mod("database", bump_counter=bump_counter, col=db.col, counter_get=counter_get, game_settings=game_settings, try_cooldown=try_cooldown)
    mod("service_player", add_coins=add_coins, get_char=get_char)
    mod("service_economy", inv_add=inv_add, inv_get=None, inv_remove=None, roll_drop=roll_drop)
    mod("service_combat", blocking_pve=blocking_pve, pve_start=pve_start, active_pve=blocking_pve)


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self._saved = {k: sys.modules.get(k) for k in ("pymongo", "pymongo.errors", "database", "service_player", "service_economy",
                                                       "service_combat", "service_adventure")}
        self.db = FakeDB()
        self.state = {"busy": False, "drops": [], "started": []}
        _install_stubs(self.db, self.state)
        sys.modules.pop("service_adventure", None)
        import service_adventure as SA
        self.SA = SA
        self.db.t["characters"].append({"user_id": 1, "level": 40, "zanpakuto": {}, "bond": {}, "weapon_id": "w1"})

    def tearDown(self):
        for k, v in self._saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v

    def run_(self, coro):
        return asyncio.run(coro)

    def test_board_fixed_for_the_day_even_after_a_level_up(self):
        b1 = self.run_(self.SA.gq_board(1, 40))
        self.db.t["characters"][0]["level"] = 90
        self.assertEqual(self.run_(self.SA.gq_board(1, 90)), b1)

    def test_start_once_per_quest_and_daily_cap(self):
        gs_cap = GAME_DEFAULTS["gq_daily"]
        for slot in range(gs_cap):
            st, doc = self.run_(self.SA.gq_start(1, slot, "en"))
            self.assertEqual(st, "ok")
            d = doc["dungeon"]
            self.assertTrue(d["gq"] and d["stage"] == 1 and d["slot"] == slot)
            self.assertEqual(d["total"], self.run_(self.SA.gq_board(1, 40))[slot]["stages"])
        self.assertEqual(self.run_(self.SA.gq_start(1, 0, "en"))[0], "taken")
        self.assertEqual(self.run_(self.SA.gq_start(1, 99, "en"))[0], "bad")

    def test_daily_limit_does_not_burn_the_quest(self):
        import config
        old = config.GAME_DEFAULTS["gq_daily"]
        config.GAME_DEFAULTS["gq_daily"] = 2
        try:
            self.assertEqual(self.run_(self.SA.gq_start(1, 0, "en"))[0], "ok")
            self.assertEqual(self.run_(self.SA.gq_start(1, 1, "en"))[0], "ok")
            self.assertEqual(self.run_(self.SA.gq_start(1, 2, "en"))[0], "limit")
            day_slot = [r for r in self.db.t["counters"] if r["key"].endswith(":2")]
            self.assertEqual(day_slot[0]["n"], 0)  # given back: it can be taken tomorrow's ticket or after the reset
        finally:
            config.GAME_DEFAULTS["gq_daily"] = old

    def test_busy_consumes_nothing(self):
        self.state["busy"] = True
        self.assertEqual(self.run_(self.SA.gq_start(1, 0, "en"))[0], "busy")
        self.assertFalse([r for r in self.db.t["counters"] if r["key"].startswith("gq:") or r["key"].startswith("adv:")])

    def test_failed_start_gives_the_ticket_back(self):
        self.state["boom"] = True
        with self.assertRaises(RuntimeError):
            self.run_(self.SA.gq_start(1, 0, "en"))
        self.assertTrue(all(r["n"] == 0 for r in self.db.t["counters"]))

    def _quest(self, rank, typ, lvl=40):
        return {"gq": True, "rank": rank, "type": typ, "qlvl": lvl, "slot": 0}

    def test_finish_without_shikai_gives_bond_and_items_only(self):
        out = self.run_(self.SA.gq_finish(1, self._quest(3, "purge"), dict(GAME_DEFAULTS)))
        self.assertEqual(len(out["items"]), G.item_count(3, "purge"))
        self.assertEqual(self.state["drops"], [G.ITEM_IDX[3]] * len(out["items"]))
        self.assertEqual(out["mastery"], 0)
        ch = self.db.t["characters"][0]
        self.assertEqual(ch["bond"]["w1"], G.ZNP_BOND[3])
        self.assertNotIn("mastery", ch["zanpakuto"])
        self.assertEqual(self.db.inv[1], out["items"])

    def test_finish_with_shikai_adds_mastery_up_to_the_cap(self):
        ch = self.db.t["characters"][0]
        ch["zanpakuto"] = {"shikai": True, "mastery": 100, "blade_id": "zangetsu"}
        out = self.run_(self.SA.gq_finish(1, self._quest(6, "gauntlet"), dict(GAME_DEFAULTS)))
        self.assertEqual(out["mastery"], G.ZNP_MASTERY[6])
        self.assertEqual(ch["zanpakuto"]["mastery"], 100 + G.ZNP_MASTERY[6])
        self.assertEqual(ch["bond"]["zangetsu"], G.ZNP_BOND[6])
        self.assertEqual(len(out["items"]), G.item_count(6, "gauntlet"))
        ch["zanpakuto"]["mastery"] = GAME_DEFAULTS["znp_mastery_cap"] - 4
        out = self.run_(self.SA.gq_finish(1, self._quest(6, "purge"), dict(GAME_DEFAULTS)))
        self.assertEqual(out["mastery"], 4)
        ch["zanpakuto"]["mastery"] = GAME_DEFAULTS["znp_mastery_cap"]
        out = self.run_(self.SA.gq_finish(1, self._quest(6, "purge"), dict(GAME_DEFAULTS)))
        self.assertEqual(out["mastery"], 0)
        self.assertEqual(ch["zanpakuto"]["mastery"], GAME_DEFAULTS["znp_mastery_cap"])

    def test_purse_grows_with_level_and_rank(self):
        gs = dict(GAME_DEFAULTS)
        lo = self.run_(self.SA.gq_finish(1, self._quest(0, "purge", 10), gs))["coins"]
        hi = self.run_(self.SA.gq_finish(1, self._quest(6, "purge", 60), gs))["coins"]
        self.assertGreater(hi, lo)
        self.assertEqual(lo, int(300 * (1 + 10 / 10) * 1.0))


class BossDataTests(unittest.TestCase):
    def test_level_boss_and_mini_boss_data_the_combat_wiring_reads(self):
        from data_extras2 import LEVEL_BOSSES, MINI_BOSS_CHANCE, MINI_BOSS_NAMES, level_band
        for lvl in (1, 20, 21, 100, 101, 5000):
            lo, hi, fa, en, colour, race = LEVEL_BOSSES[level_band(lvl)]
            self.assertTrue(lo <= lvl <= hi and fa and en)
        self.assertTrue(0 < MINI_BOSS_CHANCE < 0.2 and all(len(n) == 2 for n in MINI_BOSS_NAMES))
        import locale_en, locale_fa
        for k in ("lb_stage", "lb_done", "lb_items"):
            self.assertIn(k, locale_en.TEXT)
            self.assertIn(k, locale_fa.TEXT)


if __name__ == "__main__":
    unittest.main()
