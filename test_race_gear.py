"""Race armour (twenty kinds per race, random, own race only) and race technique cards.
Run: python -m unittest test_race_gear -v"""
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _stubs import import_with_stubs  # noqa: E402

SE = import_with_stubs("service_economy")
G = import_with_stubs("service_racegear")
import engine as E  # noqa: E402
from data_items import ALL, BY_RARITY, race_cards  # noqa: E402
from data_racegear import RACE_ARMOUR_ITEMS, parse_ra  # noqa: E402


class ArmourTests(unittest.TestCase):
    def test_twenty_kinds_per_race_in_six_colours(self):
        for race in ("shinigami", "visored", "quincy", "hollow", "arrancar", "fullbringer", "human"):
            items = [x for x in RACE_ARMOUR_ITEMS if x["race"] == race]
            self.assertEqual(len(items), 20 * 6, race)
            self.assertEqual(len({x["ra_n"] for x in items}), 20)
            self.assertTrue(all(x["perk"] for x in items))

    def test_old_shared_armour_no_longer_drops(self):
        for ids in BY_RARITY.values():
            self.assertFalse(any(ALL[i]["category"] == "armor" for i in ids))

    def test_drops_are_the_players_own_race(self):
        rng = random.Random(4)
        got = [SE._pick_of_rarity({"race": "hollow"}, 3, 0.0, rng) for _ in range(800)]
        armour = [i for i in got if ALL[i]["category"] == "armor"]
        self.assertTrue(armour)
        self.assertTrue(all(ALL[i]["race"] == "hollow" for i in armour))
        cards = [i for i in got if ALL[i]["category"] in ("race_card", "kido_card")]
        self.assertTrue(all(ALL[i]["category"] == "race_card" and ALL[i]["race"] == "hollow" for i in cards))

    def test_kido_cards_only_for_kido_races(self):
        self.assertTrue(any(ALL[i]["category"] == "kido_card" for i in race_cards("shinigami", "Common")))
        self.assertFalse(any(ALL[i]["category"] == "kido_card" for i in race_cards("quincy", "Common")))

    def test_old_armour_moves_to_the_same_colour(self):
        old = next(i for i, x in ALL.items() if x["category"] == "armor" and x.get("subtype") != "rarmor" and x["rarity"] == "Epic")
        new = G._moved_id(old, "quincy")
        race, n, c = parse_ra(new)
        self.assertEqual((race, c), ("quincy", 3))
        self.assertEqual(G._moved_id(old, "quincy"), new)  # always the same kind for the same old piece

    def test_race_change_keeps_kind_and_colour(self):
        self.assertEqual(G._moved_id("ra_hollow_07_4", "human"), "ra_human_07_4")


class CardTests(unittest.TestCase):
    def _f(self, tm):
        w = {"attack": 30, "crit": 0.0, "element": "light", "skills": [], "weapon_type": "melee"}
        f = E.new_fighter("H", 40, {"zanjutsu": 50, "kido": 10, "hakuda": 40, "hoho": 10, "reiatsu": 40}, 2000, 800, w, race="human")
        f["evs"], f["tm"] = 4, tm
        return f

    def test_mastery_makes_the_technique_stronger(self):
        out = []
        for tm in ({}, {"t1": 10}):
            a, b = self._f(tm), self._f({})
            st = E.new_state(a, b, random.Random(1))
            st["cur"], st["awaiting"] = "a", True
            E._do_action(st, "t1", random.Random(1))   # Santen Kesshun shield
            out.append(a["shield"])
        self.assertGreater(out[1], out[0])


if __name__ == "__main__":
    unittest.main()
