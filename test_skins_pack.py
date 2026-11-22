"""Light tests for the Nov 22 pack: skins, katana wheel prize, new dungeons / keys, new events, new Soul Core sources.
Uses an in-memory fake DB (no Mongo, no Telegram). Run on its own: python -m unittest test_skins_pack"""
import asyncio
import random
import sys
import types
import unittest

STATE = {"chars": [], "wallet": [], "counters": {}, "log": [], "settings": {}, "coins": {}, "inv": []}


def _stub(name, **attrs):
    m = types.ModuleType(name)
    m.__dict__.update(attrs)
    sys.modules[name] = m
    return m


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
        cur = _getp(doc, k)
        if isinstance(v, dict) and "$ne" in v:
            if isinstance(cur, list) and v["$ne"] in cur or cur == v["$ne"]:
                return False
        elif isinstance(v, dict) and "$gte" in v:
            if (cur or 0) < v["$gte"]:
                return False
        elif isinstance(cur, list) and not isinstance(v, list):
            if v not in cur:
                return False
        elif cur != v:
            return False
    return True


class Res:
    def __init__(self, matched, modified):
        self.matched_count, self.modified_count = matched, modified


class Col:
    def __init__(self, docs):
        self.docs = docs

    def _apply(self, d, upd):
        for p, v in upd.get("$inc", {}).items():
            _setp(d, p, (_getp(d, p, 0) or 0) + v)
        for p, v in upd.get("$set", {}).items():
            _setp(d, p, v)
        for p in upd.get("$unset", {}):
            parts = p.split(".")
            cur = d
            for q in parts[:-1]:
                cur = cur.get(q, {})
            cur.pop(parts[-1], None)
        for p, v in upd.get("$addToSet", {}).items():
            arr = _getp(d, p)
            if arr is None:
                arr = []
                _setp(d, p, arr)
            if v not in arr:
                arr.append(v)

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
            d = {k: v for k, v in flt.items() if not isinstance(v, dict)}
            self._apply(d, upd)
            self.docs.append(d)
            return dict(d)

    async def update_one(self, flt, upd, upsert=False):
        for d in self.docs:
            if _match(d, flt):
                before = repr(d)
                self._apply(d, upd)
                return Res(1, 1 if repr(d) != before else 0)
        if upsert:
            d = {k: v for k, v in flt.items() if not isinstance(v, dict)}
            self._apply(d, upd)
            self.docs.append(d)
            return Res(0, 1)
        return Res(0, 0)


def col(name):
    return Col({"characters": STATE["chars"], "wheel_wallet": STATE["wallet"], "core_log": STATE["log"]}.setdefault(name, STATE.setdefault("x_" + name, [])))


async def bump_counter(key, amount, cap, ttl_hours=48):
    n = STATE["counters"].get(key, 0)
    if n + amount > cap:
        return False
    STATE["counters"][key] = n + amount
    return True


async def counter_get(key):
    return STATE["counters"].get(key, 0)


async def game_settings(force=False):
    base = {"wheel2_enabled": True, "wheel_free_daily": 0, "pity_leg": 30, "pity_myth": 90, "coin_rate": 1.0,
            "core_quest_chance": 1.0, "core_dungeon_chance": 1.0, "core_day_cap": 1, "core_new_day_cap": 1,
            "core_new_dungeon_k": 1.0, "core_event_chance": 1.0}
    base.update(STATE["settings"])
    return base


async def try_cooldown(key, s):
    return 0


async def get_char(uid):
    for d in STATE["chars"]:
        if d["user_id"] == uid:
            return dict(d)
    return None


async def add_coins(uid, n, why):
    STATE["coins"][uid] = STATE["coins"].get(uid, 0) + n
    return True


async def add_xp(*a, **k):
    return True


async def inv_add(uid, item, qty=1, force=False, keep=False):
    STATE["inv"].append((uid, item))
    return True


async def _bulk():
    return None


try:
    from pymongo import ReturnDocument  # noqa: F401
except ImportError:  # same trick as test_wheels_service: the fake DB does not need the real driver
    class ReturnDocument:
        AFTER = "after"
    _stub("pymongo", ReturnDocument=ReturnDocument)
    _stub("pymongo.errors", DuplicateKeyError=Exception)

_stub("database", col=col, game_settings=game_settings, try_cooldown=try_cooldown, bump_counter=bump_counter, counter_get=counter_get)
_stub("service_player", add_coins=add_coins, add_xp=add_xp, get_char=get_char)
_stub("service_economy", inv_add=inv_add, inv_get=inv_add, inv_remove=inv_add)
_stub("service_extras", pick_item=lambda cat, idx, rng=None: "item_x")
_stub("service_pace", bulk_slot=_bulk)

import data_crafting  # noqa: E402
import data_items  # noqa: E402
import data_races  # noqa: E402
import data_skins as ds  # noqa: E402
import data_war  # noqa: E402
import data_world  # noqa: E402
import service_cores as sc  # noqa: E402
import service_raceweapon as srw  # noqa: E402
import service_skins as ss  # noqa: E402
import service_wheels as sw  # noqa: E402

NEW_DG = sorted(sc.NEW_DUNGEONS)
ST_PB = {"relic_k": 1.0, "pet_k": 1.0, "relic_slots": 2, "cosmetic_fame_cap": 0.1, "cosmetic_fame_xp": 0.001}


def reset(*chars):
    for k in ("chars", "wallet", "log", "inv"):
        STATE[k].clear()
    STATE["counters"].clear()
    STATE["settings"].clear()
    STATE["coins"].clear()
    STATE["chars"].extend(chars)


class SkinData(unittest.TestCase):
    def test_counts_and_strength_by_rarity(self):
        self.assertEqual({r: len(v) for r, v in ds.BY_RARITY.items()}, {"Epic": 10, "Legendary": 10, "Mythic": 10})
        for s in ds.SKINS.values():
            self.assertEqual(len(s["bonus"]), {"Epic": 1, "Legendary": 2, "Mythic": 3}[s["rarity"]], s["id"])
            self.assertTrue(set(s["bonus"]) <= set(ds.PB_KEYS) | set(ds.EXTRA_KEYS), s["id"])

    def test_skins_never_touch_attack(self):
        for s in ds.SKINS.values():
            self.assertFalse(set(s["bonus"]) & {"dmg", "def", "crit", "regen"}, s["id"])

    def test_every_skin_is_useful_and_named(self):
        for s in ds.SKINS.values():
            self.assertTrue(s["fa"] and s["en"] and s["icon"])
            self.assertTrue(all(v > 0 for v in s["bonus"].values()))

    def test_bonus_only_when_owned_and_equipped(self):
        self.assertEqual(ds.skin_bonus({"skin": "sk_l01"}), {})                       # equipped but not owned: nothing
        ch = {"skin": "sk_l01", "skins_owned": ["sk_l01"]}
        self.assertEqual(ds.skin_bonus(ch), {"xp": 0.07, "coin": 0.07})
        self.assertEqual(ds.skin_extra({})["wheel"], 0.0)

    def test_extras_are_capped(self):
        ch = {"skin": "sk_m10", "skins_owned": ["sk_m10"]}
        ex = ds.skin_extra(ch)
        self.assertLessEqual(ex["core"], ds.CORE_BOOST_CAP)
        self.assertLessEqual(ex["wheel"], ds.WHEEL_DISCOUNT_CAP)
        self.assertEqual(ex["pity"], 8)

    def test_player_bonus_uses_the_skin(self):
        base = data_crafting.player_bonus({}, {}, ST_PB)
        ch = {"skin": "sk_m06", "skins_owned": ["sk_m06"]}
        b = data_crafting.player_bonus(ch, {}, ST_PB)
        self.assertAlmostEqual(b["xp"] - base["xp"], 0.10)
        self.assertAlmostEqual(b["coin"] - base["coin"], 0.12)
        self.assertAlmostEqual(b["drop"] - base["drop"], 0.10)
        self.assertEqual((b["dmg"], b["def"], b["crit"]), (base["dmg"], base["def"], base["crit"]))   # attack untouched


class Catalog(unittest.TestCase):
    def test_new_dungeons_are_complete(self):
        self.assertEqual(len(NEW_DG), 6)
        for d in NEW_DG:
            self.assertIn(d, data_races.DUNGEONS)
            e = data_races.DUNGEON_ENEMIES[d]
            self.assertEqual(len(e["enemies"]), 3)
            self.assertTrue(e["boss"][0] and e["boss"][1])
            self.assertIn(d, data_items.DUNGEON_IDS)
            self.assertIn(d, data_crafting.DUNGEON_IDS)
            for diff in data_items.DIFFS:
                keys = [x for x in data_items.ALL.values() if (x.get("effect") or {}).get("type") == "key"
                        and x["effect"]["dungeon"] == d and x["effect"]["diff"] == diff]
                self.assertEqual(len(keys), 1, (d, diff))
        self.assertEqual(data_items.DUNGEON_IDS, data_crafting.DUNGEON_IDS)
        self.assertEqual(set(data_items.DUNGEON_IDS), set(data_races.DUNGEONS))
        self.assertEqual(set(data_races.DUNGEONS), set(data_races.DUNGEON_ENEMIES))

    def test_old_key_ids_did_not_move(self):
        k = data_items.ALL["it_k001"] if "it_k001" in data_items.ALL else None
        old_first = next(x for x in data_items.ALL.values() if (x.get("effect") or {}).get("type") == "key")
        self.assertEqual(old_first["effect"]["dungeon"], "trial")

    def test_new_events_are_complete(self):
        import locale_extras as le
        for k in ("core_rift", "kenpachi_rampage", "blade_festival", "mask_masquerade"):
            self.assertIn(k, data_world.EVENTS)
            self.assertIn(k, data_war.WARS)
            self.assertIn(k, data_war.WAR_STORY)
            self.assertIn(f"ev_{k}_name", le.FA)
            self.assertIn(f"ev_{k}_desc", le.EN)
            ev = data_world.EVENTS[k]
            self.assertTrue(ev["pts"] and ev["win"] and ev["lose"])
            self.assertGreaterEqual(ev.get("core", 1.0), 1.5)


class Services(unittest.IsolatedAsyncioTestCase):
    async def test_grant_new_then_duplicate_pays_coins(self):
        reset({"user_id": 1, "level": 10})
        self.assertEqual(await ss.grant_skin(1, "sk_m01"), ("new", 0))
        st, coins = await ss.grant_skin(1, "sk_m01")
        self.assertEqual((st, coins), ("dup", ds.DUP_COINS["Mythic"]))
        self.assertEqual(STATE["coins"][1], ds.DUP_COINS["Mythic"])
        self.assertEqual(STATE["chars"][0]["skins_owned"], ["sk_m01"])

    async def test_parallel_grants_give_one_skin(self):
        reset({"user_id": 1, "level": 10})
        res = await asyncio.gather(*[ss.grant_skin(1, "sk_e01") for _ in range(8)])
        self.assertEqual(sum(1 for r in res if r[0] == "new"), 1)
        self.assertEqual(STATE["chars"][0]["skins_owned"], ["sk_e01"])

    async def test_equip_needs_ownership(self):
        reset({"user_id": 1, "level": 10})
        self.assertEqual(await ss.equip_skin(1, "sk_e02"), "notowned")
        await ss.grant_skin(1, "sk_e02")
        self.assertEqual(await ss.equip_skin(1, "sk_e02"), "ok")
        self.assertEqual(STATE["chars"][0]["skin"], "sk_e02")
        self.assertEqual(await ss.equip_skin(1, "nope"), "bad")
        await ss.unequip_skin(1)
        self.assertIsNone(STATE["chars"][0]["skin"])

    async def test_pick_prefers_unowned(self):
        owned = ds.BY_RARITY["Epic"][:9]
        for _ in range(20):
            self.assertEqual(ss.pick_skin("Epic", owned), ds.BY_RARITY["Epic"][9])

    def test_discount_and_pity_math(self):
        self.assertEqual(sw.discounted(100, 0.10), 90)
        self.assertEqual(sw.discounted(1, 0.10), 1)
        self.assertEqual(sw.discounted(0, 0.10), 0)
        self.assertEqual(sw.pity_at(30, 8), 22)
        self.assertEqual(sw.pity_at(30, 40), 5)
        self.assertEqual(sw.pity_at(0, 8), 0)      # pity switched off stays off

    async def test_katana_rises_one_colour_keeps_forge_and_respects_level(self):
        reset({"user_id": 1, "level": 20, "race": "shinigami", "weapon_id": "rw_shinigami_03_1", "weapon_plus": {"rw_shinigami_03_1": 4}})
        self.assertEqual(await srw.free_ascend(1), ("ok", "rw_shinigami_03_2"))      # colour 2 needs level 15
        c = STATE["chars"][0]
        self.assertEqual(c["weapon_id"], "rw_shinigami_03_2")
        self.assertEqual(c["weapon_plus"], {"rw_shinigami_03_2": 4})
        self.assertEqual(await srw.free_ascend(1), ("level", 30))                    # colour 3 needs level 30: no skipping the gate
        STATE["chars"][0].update(weapon_id="rw_shinigami_03_5")
        self.assertEqual(await srw.free_ascend(1), ("max", None))                    # never above red
        STATE["chars"][0].update(weapon_id="rw_human_00_1")                          # a weapon of another race: choice pending
        self.assertEqual((await srw.free_ascend(1))[0], "choose")

    async def test_bonus_prize_paths(self):
        reset({"user_id": 1, "level": 90, "race": "shinigami", "weapon_id": "rw_shinigami_00_0", "skins_owned": []})
        ch = await get_char(1)

        class Always(random.Random):
            def random(self):
                return 0.0
        b = await sw.bonus_prize(1, "w_cosmetic", "Mythic", ch, {}, Always(1))
        self.assertEqual((b["kind"], b["status"]), ("skin", "new"))
        self.assertEqual(ds.SKINS[b["skin"]]["rarity"], "Mythic")
        reset({"user_id": 1, "level": 90, "race": "shinigami", "weapon_id": "rw_shinigami_00_0", "skins_owned": []})
        ch = await get_char(1)
        b = await sw.bonus_prize(1, "w_weapon", "Legendary", ch, {"skin_chance_leg": 0.0}, Always(1))
        self.assertEqual((b["kind"], b["weapon"]), ("katana", "rw_shinigami_00_1"))
        self.assertIsNone(await sw.bonus_prize(1, "w_weapon", "Common", ch, {}, Always(1)))   # small results carry nothing
        # weapon already red: the katana prize turns into evolution fuel, never an empty prize
        STATE["chars"][0].update(weapon_id="rw_shinigami_00_5")
        ch = await get_char(1)
        b = await sw.bonus_prize(1, "w_weapon", "Legendary", ch, {"skin_chance_leg": 0.0}, Always(1))
        self.assertEqual((b["kind"], b["why"]), ("katana_relic", "max"))

    async def test_full_spin_with_skin_discount(self):
        reset({"user_id": 2, "level": 30, "race": "shinigami", "weapon_id": "rw_shinigami_00_0", "skin": "sk_e07", "skins_owned": ["sk_e07"]})
        STATE["wallet"].append({"_id": 2, "cores": 100})
        st, res = await sw.spin(2, "w_ichigo", 1)                                   # base 60, Epic skin: -3%
        self.assertEqual(st, "ok")
        self.assertEqual(res["cost"], 58)
        self.assertEqual(res["cores_left"], 42)

    async def test_spin_loop_is_stable_and_skins_appear(self):
        reset({"user_id": 3, "level": 100, "race": "shinigami", "weapon_id": "rw_shinigami_00_0", "skins_owned": []})
        STATE["wallet"].append({"_id": 3, "cores": 10 ** 9})
        random.seed(7)
        kinds, skins = {}, 0
        for _ in range(300):
            st, res = await sw.spin(3, "w_cosmetic", 1)
            self.assertEqual(st, "ok")
            b = res["bonus"]
            kinds[b["kind"] if b else None] = kinds.get(b["kind"] if b else None, 0) + 1
            skins += bool(b and b["kind"] == "skin")
        self.assertGreater(skins, 3)
        self.assertLess(skins, 120)
        self.assertTrue(set(kinds) <= {None, "skin", "katana", "katana_relic"})
        self.assertLessEqual(len(STATE["chars"][0]["skins_owned"]), 30)


class Cores(unittest.IsolatedAsyncioTestCase):
    async def test_new_dungeon_cores_from_nightmare_with_own_cap(self):
        reset({"user_id": 4, "level": 50})
        self.assertFalse(await sc.on_dungeon_clear(4, "normal", "bankai_dojo"))
        self.assertFalse(await sc.on_dungeon_clear(4, "hard", "bankai_dojo"))
        self.assertTrue(await sc.on_dungeon_clear(4, "nightmare", "bankai_dojo"))
        self.assertFalse(await sc.on_dungeon_clear(4, "legendary", "vasto_lair"))   # new cap of 1 per day reached
        self.assertTrue(await sc.on_dungeon_clear(4, "abyss", "trial"))             # the OLD cap is separate and untouched
        self.assertEqual(STATE["wallet"][0]["cores"], 2)

    async def test_old_dungeons_still_only_abyss_and_legendary(self):
        reset({"user_id": 4, "level": 50})
        self.assertFalse(await sc.on_dungeon_clear(4, "nightmare", "trial"))
        self.assertEqual(STATE["wallet"], [])

    async def test_event_cores_use_the_new_cap_and_respect_chance(self):
        reset({"user_id": 5, "level": 50})
        self.assertTrue(await sc.on_event_end(5, 0, True, "core_rift"))
        self.assertFalse(await sc.on_event_end(5, 1, True, "core_rift"))             # same day, cap reached
        STATE["settings"]["core_event_chance"] = 0.0
        reset({"user_id": 6, "level": 50})
        STATE["settings"]["core_event_chance"] = 0.0
        self.assertFalse(await sc.on_event_end(6, 0, True, "core_rift"))

    async def test_skin_raises_core_chance(self):
        reset({"user_id": 7, "level": 50, "skin": "sk_m01", "skins_owned": ["sk_m01"]})
        self.assertAlmostEqual(await sc.core_boost(7), 1.25)
        reset({"user_id": 8, "level": 50})
        self.assertEqual(await sc.core_boost(8), 1.0)


if __name__ == "__main__":
    unittest.main()
