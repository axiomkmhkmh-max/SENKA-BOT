"""SENKA+ checks: canon race killers, Konpaku in duels only, the new Bleach bosses (no MongoDB / Telegram needed).

Run:  python -m unittest test_senka_plus -v   (from the project root)
"""
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
for k, v in {"BOT_TOKEN": "1:test", "MONGODB_URI": "mongodb://localhost:1/test", "OWNER_ID": "1",
             "HMAC_SECRET": "x" * 40}.items():
    os.environ.setdefault(k, v)

import engine as E  # noqa: E402
from data_bleachfx import KONPAKU, RACE_KILLER  # noqa: E402
import data_bosses  # noqa: E402


def fighter(name, race, hp=400):
    return E.new_fighter(name, 20, {"zanjutsu": 40, "hoho": 30, "kido": 20, "hakuda": 20}, hp, 200,
                         {"attack": 12, "crit": 0.0, "element": "light", "skills": [], "weapon_type": "melee"},
                         race=race)


class FixedRng(random.Random):
    """No dodge, no crit, no damage spread: the damage numbers become exact."""

    def random(self):
        return 0.99

    def uniform(self, a, b):
        return 1.0


def hit_damage(att_race, def_race):
    a, b = fighter("A", att_race), fighter("B", def_race)
    ev = []
    E._deal({"a": a, "b": b, "turn": 1, "cur": "a"}, "a", 1.0, FixedRng(), ev, "atk", allow_procs=False)
    hits = [e for e in ev if e.get("k") == "hit"]
    return hits[0]["n"] if hits else 0


class RaceKillerTests(unittest.TestCase):
    def test_table_only_raises_damage(self):
        for att, table in RACE_KILLER.items():
            for dfn, mult in table.items():
                self.assertGreater(mult, 1.0, (att, dfn))
                self.assertLessEqual(mult, 1.10, (att, dfn))  # keep it a flavour bonus, not a rule-breaker

    def test_quincy_hits_hollow_harder_than_human(self):
        self.assertGreater(hit_damage("quincy", "hollow"), hit_damage("quincy", "human"))

    def test_no_bonus_when_no_entry(self):
        self.assertEqual(hit_damage("human", "hollow"), hit_damage("human", "human"))


class KonpakuTests(unittest.TestCase):
    def _knock_out(self, pvp):
        a, b = fighter("A", "shinigami"), fighter("B", "human", hp=400)
        st = E.new_state(a, b, random.Random(1), pvp=pvp)
        b["hp"] = 0
        ev = []
        E._check_end(st, ev)
        return st, b, ev

    def test_duel_revives_once(self):
        st, b, ev = self._knock_out(pvp=True)
        self.assertFalse(st["done"])
        self.assertEqual(b["hp"], max(1, int(b["max_hp"] * KONPAKU["hp"])))
        self.assertEqual(b["lives"], KONPAKU["lives"] - 1)
        self.assertTrue(any(e.get("k") == "konpaku" for e in ev))

    def test_second_death_ends_the_duel(self):
        st, b, _ = self._knock_out(pvp=True)
        b["hp"] = 0
        E._check_end(st, [])
        self.assertTrue(st["done"])
        self.assertEqual(st["winner"], "a")

    def test_pve_has_no_konpaku(self):
        st, b, ev = self._knock_out(pvp=False)
        self.assertTrue(st["done"])
        self.assertFalse(any(e.get("k") == "konpaku" for e in ev))


class BossPackSixTests(unittest.TestCase):
    def test_new_bosses_are_wired(self):
        ids = [b["_id"] for b in data_bosses.BOSSES]
        self.assertEqual(len(ids), len(set(ids)))
        for n in ("Tia Halibel", "Cirucci Sanfilippo", "Kokichi Muramasa", "Jin Kariya",
                  "Lilynette Gingerbuck", "Gamuza"):
            self.assertTrue(any(b["name_en"] == n for b in data_bosses.BOSSES), n)
        self.assertEqual(data_bosses.BOSS_BY_ID["boss_104"]["name_en"], "Gamuza")


class TeamBattleTests(unittest.TestCase):
    def setUp(self):
        import engine_team as T
        self.T = T

    def test_team_size_is_checked(self):
        with self.assertRaises(ValueError):
            self.T.new_team_state([], [fighter("B", "human")])
        with self.assertRaises(ValueError):
            self.T.new_team_state([fighter("A%d" % i, "human") for i in range(4)], [fighter("B", "human")])

    def test_tag_gives_first_blow_bonus(self):
        T = self.T
        plain = T.new_team_state([fighter("A", "shinigami")], [fighter("B", "human", hp=10**6)])
        ev1 = T.act(plain, "a", "atk", rng=FixedRng())
        h1 = [e for e in ev1 if e.get("k") == "hit"][0]["n"]
        tagged = T.new_team_state([fighter("A0", "human", hp=10**6), fighter("A1", "shinigami")],
                                  [fighter("B", "human", hp=10**6)])
        T.act(tagged, "a", "tag", target=1, rng=FixedRng())
        T.act(tagged, "b", "atk", rng=FixedRng())
        ev2 = T.act(tagged, "a", "atk", rng=FixedRng())
        h2 = [e for e in ev2 if e.get("k") == "hit"][0]["n"]
        self.assertGreater(h2, h1)

    def test_fallen_fighter_is_replaced_for_free(self):
        T = self.T
        a0, a1 = fighter("A0", "human"), fighter("A1", "human")
        st = T.new_team_state([a0, a1], [fighter("B", "human", hp=10**6)])
        a0["hp"] = 0
        self.assertIs(T.active(st, "a"), a1)

    def test_last_fighter_down_loses_the_battle(self):
        T = self.T
        st = T.new_team_state([fighter("A", "human")], [fighter("B", "human", hp=10**6)])
        st["teams"]["a"][0]["hp"] = 0
        T._check_end(st)
        self.assertTrue(st["done"])
        self.assertEqual(st["winner"], "b")

    def test_team_fights_use_race_killers(self):
        T = self.T
        def first_hit(att_race):
            st = T.new_team_state([fighter("A", att_race)], [fighter("B", "hollow", hp=10**6)])
            ev = T.act(st, "a", "atk", rng=FixedRng())
            return [e for e in ev if e.get("k") == "hit"][0]["n"]
        self.assertGreater(first_hit("quincy"), first_hit("human"))

    def test_turn_order_alternates(self):
        T = self.T
        st = T.new_team_state([fighter("A", "human")], [fighter("B", "human", hp=10**6)])
        T.act(st, "a", "atk", rng=FixedRng())
        self.assertEqual(st["cur"], "b")
        with self.assertRaises(ValueError):
            T.act(st, "a", "atk", rng=FixedRng())


class CharmItemTests(unittest.TestCase):
    def test_charms_exist_and_older_ids_unchanged(self):
        from data_items import ALL, ITEMS
        charms = [x for x in ITEMS if x["category"] == "charm"]
        self.assertEqual(len(charms), 30)
        kinds = {x["effect"]["type"] for x in charms}
        self.assertEqual(kinds, {"buff", "konpaku"})
        self.assertEqual(ITEMS[0]["item_id"], "it_0001")
        self.assertTrue(all(x["effect"] for x in charms))
        self.assertIn("it_0001", ALL)



if __name__ == "__main__":
    unittest.main()
