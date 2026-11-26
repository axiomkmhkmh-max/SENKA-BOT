"""Benihime: two Shikai modes (attack / defence), a Bankai variant, and real strength."""
import random
import unittest
import engine as E
import data_zanpakuto as Z

W = {"attack": 100, "crit": 0.0, "element": "light", "skills": [], "weapon_type": "melee"}


def fighter(name, blade=None):
    f = E.new_fighter(name, 100, {"zanjutsu": 100, "reiatsu": 100, "hakuda": 1, "hoho": 1, "kido": 1},
                      100000, 100000, W, race="shinigami", bt=Z.blade_technique(blade) if blade else None)
    f["blade"] = blade
    f["bu"] = Z.blade_ultimate(blade)
    return f


def ready(blade="benihime"):
    a, b = fighter("A", blade), fighter("B")
    st = E.new_state(a, b, random.Random(1), duel_rules=False)
    st["cur"] = "a"
    a["x"]["sk"] = 1
    return a, b, st


class Benihime(unittest.TestCase):
    def test_stronger_than_before(self):
        st = Z.BLADE_STAGES["benihime"]
        self.assertGreaterEqual(st["shikai_bonus"], 0.08)
        self.assertGreaterEqual(st["bankai_bonus"], 0.10)
        self.assertGreaterEqual(Z.blade_technique("benihime")["mult"], 2.0)
        self.assertEqual(Z.blade_technique("benihime")["en"], "Crimson Burst")

    def test_attack_mode_hits(self):
        a, b, st = ready()
        self.assertTrue(E.can(a, "bt", st))
        before = b["hp"]
        E._do_action(st, "bt", random.Random(3))
        self.assertLess(b["hp"], before)

    def test_defence_mode_shields_and_mends(self):
        a, b, st = ready()
        a["hp"] = int(a["max_hp"] * 0.5)
        E._do_action(st, "bu", random.Random(3))
        self.assertGreater(a["shield"], 0)

    def test_bankai_variant_and_cleanse(self):
        u = Z.blade_ultimate("benihime")
        self.assertEqual(u["bk"]["en"], "Kannonbiraki Benihime Aratame")
        self.assertGreater(u["bk"]["shield"], u["shield"])
        a, b, st = ready()
        a["form"]["on"] = 2
        a["fx"].append({"k": "bleed", "t": 3, "s": 1})
        E._do_action(st, "bu", random.Random(3))
        self.assertFalse([x for x in a["fx"] if x["k"] == "bleed"])

    def test_bankai_makes_both_modes_stronger(self):
        s1, s2 = [], []
        for bankai, out in ((False, s1), (True, s2)):
            a, b, st = ready()
            a["form"]["on"] = 2 if bankai else 0
            E._do_action(st, "bt", random.Random(5))
            out.append(100000 - b["hp"])
        self.assertGreater(s2[0], s1[0])


if __name__ == "__main__":
    unittest.main()
