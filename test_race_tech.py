"""Canon race techniques (t1-t3): unlocked by evolution, own cost and cooldown, and they really act.
Run: python -m unittest test_race_tech -v"""
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine as E  # noqa: E402
from data_race_tech import RACE_TECH, TECH_SLOTS  # noqa: E402


def fighter(race, evs=4, ai=False):
    w = {"attack": 30, "crit": 0.0, "element": "light", "skills": [], "weapon_type": "melee"}
    f = E.new_fighter(race, 40, {"zanjutsu": 60, "kido": 40, "hakuda": 40, "hoho": 0, "reiatsu": 40}, 2000, 800, w, race=race, ai=ai)
    f["evs"] = evs
    return f


def duel(a, b):
    st = E.new_state(a, b, random.Random(2))
    st["cur"], st["awaiting"], st["dist"] = "a", True, 1
    return st


class TechTests(unittest.TestCase):
    def test_every_non_shinigami_race_has_techniques(self):
        for race in ("quincy", "hollow", "arrancar", "fullbringer", "human", "visored"):
            self.assertTrue(RACE_TECH[race], race)
        self.assertNotIn("shinigami", RACE_TECH)

    def test_every_technique_is_open_from_level_one(self):
        for race, techs in RACE_TECH.items():
            f = fighter(race, evs=0)
            if race == "visored":
                f["form"]["on"] = 1  # Mask Strike still needs the mask on
            for slot in techs:
                self.assertTrue(E.can(f, slot), (race, slot))

    def test_wild_enemies_cannot_use_them(self):
        f = fighter("hollow", ai=True)
        f["wild"] = True
        self.assertFalse(any(E.can(f, s) for s in TECH_SLOTS))

    def test_cooldown_and_cost(self):
        a, b = fighter("hollow"), fighter("human")
        st = duel(a, b)
        re0 = a["re"]
        E._do_action(st, "t1", random.Random(1))
        self.assertLess(a["re"], re0)
        self.assertEqual(a["x"]["t1cd"], RACE_TECH["hollow"]["t1"]["cd"])
        self.assertFalse(E.can(a, "t1"))

    def test_licht_regen_hits_several_times(self):
        a, b = fighter("quincy"), fighter("human")
        st = duel(a, b)
        ev = E._do_action(st, "t1", random.Random(1))
        hits = [e for e in ev if e["k"] == "hit" and e.get("kind") == "tech"]
        self.assertGreaterEqual(len(hits), 3)

    def test_hierro_cuts_damage_taken(self):
        a, b = fighter("arrancar"), fighter("human")
        st = duel(a, b)
        E._do_action(st, "t1", random.Random(1))
        self.assertLess(E._take_mult(a), 1.0)

    def test_santen_kesshun_shield_and_soten_heal(self):
        a, b = fighter("human"), fighter("hollow")
        st = duel(a, b)
        E._do_action(st, "t1", random.Random(1))
        self.assertGreater(a["shield"], 0)
        a["hp"] = 500
        a["fx"].append({"k": "bleed", "t": 3, "s": 1})
        st["cur"], st["awaiting"] = "a", True
        E._do_action(st, "t2", random.Random(1))
        self.assertGreater(a["hp"], 500)
        self.assertFalse(any(e["k"] == "bleed" for e in a["fx"]))

    def test_mask_strike_needs_the_mask(self):
        a = fighter("visored")
        self.assertFalse(E.can(a, "t1"))
        a["form"]["on"] = 1
        self.assertTrue(E.can(a, "t1"))

    def test_buttons_reach_and_ai(self):
        a = fighter("quincy")
        self.assertIsNotNone(E._band(a, "t1"))
        self.assertIsNone(E._band(fighter("human"), "t1"))  # a shield ignores distance


class StatScalingTests(unittest.TestCase):
    """Abilities draw 70% of their stat part from the race's own stat; plain = Zanjutsu, heavy = Zanjutsu + Reiatsu."""

    def _f(self, race, **stats):
        w = {"attack": 30, "crit": 0.0, "element": "light", "skills": [], "weapon_type": "melee"}
        base = {"zanjutsu": 40, "kido": 40, "hakuda": 40, "hoho": 40, "reiatsu": 40}
        base.update(stats)
        return E.new_fighter(race, 40, base, 2000, 800, w, race=race)

    def test_race_stat_drives_abilities(self):
        for race, stat in (("quincy", "reiatsu"), ("arrancar", "hoho"), ("shinigami", "kido"), ("hollow", "hakuda"),
                           ("human", "reiatsu"), ("visored", "reiatsu")):
            lo, hi = self._f(race), self._f(race, **{stat: 140})
            self.assertGreater(E.strike_base(hi, "abl"), E.strike_base(lo, "abl") + 60, race)
            self.assertEqual(E.strike_base(hi, "atk"), E.strike_base(lo, "atk"), race)  # plain attack: Zanjutsu only

    def test_heavy_uses_zanjutsu_and_reiatsu(self):
        a, b, c = self._f("quincy"), self._f("quincy", reiatsu=140), self._f("quincy", hoho=140)
        self.assertGreater(E.strike_base(b, "hvy"), E.strike_base(a, "hvy"))
        self.assertEqual(E.strike_base(c, "hvy"), E.strike_base(a, "hvy"))

    def test_fullbringer_leans_on_the_weapon(self):
        f = self._f("fullbringer")
        self.assertGreater(E.strike_base(f, "abl"), E.strike_base(f, "atk"))

    def test_wild_enemies_keep_the_plain_formula(self):
        f = self._f("quincy", reiatsu=140)
        f["wild"] = True
        self.assertEqual(E.strike_base(f, "abl"), E.strike_base(f, "atk"))

    def test_shields_follow_the_race_stat(self):
        out = []
        for rei in (40, 140):
            a, b = self._f("human", reiatsu=rei), self._f("hollow")
            a["evs"] = 0
            st = E.new_state(a, b, random.Random(1))
            st["cur"], st["awaiting"] = "a", True
            E._do_action(st, "t1", random.Random(1))
            out.append(a["shield"])
        self.assertGreater(out[1], out[0])


if __name__ == "__main__":
    unittest.main()
