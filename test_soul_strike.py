"""Human Soul Strike: its own hit text (not the Fullbringer's) and a real damage bonus over a plain attack.
Run: python -m unittest test_soul_strike -v"""
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine as E  # noqa: E402
from data_bleachfx import SIG, sig_for  # noqa: E402
from locale_bleachfx import EN, FA  # noqa: E402
from render import events_text  # noqa: E402

STATS = {"zanjutsu": 10, "kido": 5, "hakuda": 10, "hoho": 10, "reiatsu": 10}


def battle(race="human"):
    a = E.new_fighter("A", 20, dict(STATS), 200, 2000, None, race=race, sig=sig_for(race))
    b = E.new_fighter("B", 20, dict(STATS), 100000, 200, None, race="human")
    st = E.new_state(a, b, random.Random(1))
    st["cur"] = "a"
    st["dist"] = E._band(a, "atk")[0]  # standing in reach, so the action is a hit and not an approach
    return st


def first_hit(st, action, seed):
    ev = E.do_action(st, action, random.Random(seed))
    ev = ev if isinstance(ev, list) else st.get("events", [])
    return [e for e in ev if e.get("k") == "hit"]


class SoulStrikeTests(unittest.TestCase):
    def test_soul_strike_is_stronger_than_it_was(self):
        self.assertGreaterEqual(SIG["soul"]["mult"], 1.5)

    def test_human_uses_soul_strike_and_it_has_its_own_hit_kind(self):
        st = battle()
        self.assertTrue(E.can(st["a"], "sg"))
        hits = first_hit(st, "sg", 5)
        self.assertTrue(hits)
        self.assertEqual(hits[0]["kind"], "soul")

    def test_soul_strike_hits_harder_than_a_plain_attack(self):
        def avg(action):  # some swings are dodged (no hit event): average over the real hits only
            hits = [h["n"] for s in range(300) for h in first_hit(battle(), action, s)]
            self.assertGreater(len(hits), 100)
            return sum(hits) / len(hits)
        self.assertGreater(avg("sg"), avg("atk") * 1.4)

    def test_fullbringer_keeps_its_own_kind(self):
        hits = first_hit(battle("fullbringer"), "sg", 5)
        self.assertEqual(hits[0]["kind"], "bring")

    def test_soul_strike_text_is_not_the_fullbring_text(self):
        for table in (FA, EN):
            self.assertIn("lg_hit_soul", table)
            self.assertNotIn("Fullbring", table["lg_hit_soul"])
        line = events_text("en", [{"k": "hit", "kind": "soul", "a": "Ann", "d": "Bob", "n": 50}])
        self.assertNotIn("Fullbring", line)
        self.assertNotIn("bound object", line)


if __name__ == "__main__":
    unittest.main()
