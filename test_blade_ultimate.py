"""Every released blade gets one finishing technique (data_zanpakuto.BLADE_ULT)."""
import random
import unittest
import engine as E
from data_zanpakuto import BLADE_TECH, blade_ultimate

W = {"attack": 100, "crit": 0.0, "element": "light", "skills": [], "weapon_type": "melee"}


def fighter(name, blade=None):
    f = E.new_fighter(name, 100, {"zanjutsu": 100, "reiatsu": 100, "hakuda": 1, "hoho": 1, "kido": 1},
                      100000, 100000, W, race="shinigami")
    f["blade"] = blade
    f["bu"] = blade_ultimate(blade)
    return f


class BladeUltimateTests(unittest.TestCase):
    def test_every_blade_has_one_except_kyoka(self):
        for b in BLADE_TECH:
            self.assertEqual(blade_ultimate(b) is None, b == "kyoka_suigetsu", b)

    def test_needs_shikai_then_hits_and_goes_on_cooldown(self):
        a, b = fighter("A", "hyorinmaru"), fighter("B")
        st = E.new_state(a, b, random.Random(1), duel_rules=False)
        st["cur"] = "a"
        self.assertFalse(E.can(a, "bu", st))
        a["x"]["sk"] = 1
        self.assertTrue(E.can(a, "bu", st))
        before = b["hp"]
        E._do_action(st, "bu", random.Random(3))
        self.assertLess(b["hp"], before)
        self.assertGreater(a["x"]["bu_cd"], 0)
        self.assertFalse(E.can(a, "bu", st))

    def test_effects_apply(self):
        for blade, fx in (("zanka_no_tachi", "burn"), ("zabimaru", "bleed"), ("wabisuke", "weaken")):
            a, b = fighter("A", blade), fighter("B")
            a["x"]["sk"] = 1
            st = E.new_state(a, b, random.Random(1), duel_rules=False)
            st["cur"] = "a"
            E._do_action(st, "bu", random.Random(3))
            self.assertTrue(E.has_fx(b, fx), blade)


if __name__ == "__main__":
    unittest.main()
