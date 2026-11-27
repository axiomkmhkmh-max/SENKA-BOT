"""Nov 27: every Bankai has an activation word («Bankai!!! <name>») and an epic line; Zanka no Tachi and Katen Kyōkotsu are Mythic."""
import unittest

import data_zanpakuto as Z


class BankaiScenes(unittest.TestCase):
    def test_every_blade_has_a_scene_in_both_languages(self):
        for b in Z.BLADE_STAGES:
            for lang in ("fa", "en"):
                t = Z.bankai_scene(b, lang, a="A", d="D")
                self.assertTrue(t.startswith("«" + Z.bankai_shout(b, lang)), b)
                self.assertNotIn("{", t, b)  # every placeholder filled
                self.assertIn("D", t.split("\n", 1)[1] if "\n" in t else "")

    def test_zanka_scene_and_shout(self):
        t = Z.bankai_scene("zanka_no_tachi", "fa", d="حریف۱")
        self.assertIn("بانکای!!! زانکا نو تاچی", t)
        self.assertIn("خاکستر", t)
        self.assertIn("حریف۱", t)

    def test_unknown_or_missing_blade_still_gets_a_scene(self):
        self.assertIn("بانکای!!!", Z.bankai_scene(None, "fa"))
        self.assertIn("Bankai!!!", Z.bankai_scene("nope", "en"))


class MythicBlades(unittest.TestCase):
    def test_zanka_and_katen_are_mythic(self):
        self.assertEqual(Z.blade_tier("zanka_no_tachi"), 5)
        self.assertEqual(Z.blade_tier("katen_kyokotsu"), 5)

    def test_zanka_is_the_strongest_bankai_bonus(self):
        z = Z.BLADE_STAGES["zanka_no_tachi"]["bankai_bonus"]
        self.assertTrue(all(z >= s.get("bankai_bonus", 0) for s in Z.BLADE_STAGES.values()))

    def test_bankai_finishers(self):
        for b in ("zanka_no_tachi", "katen_kyokotsu"):
            u = Z.blade_ultimate(b)
            self.assertIn("bk", u)
            self.assertGreater(u["bk"]["mult"], u["mult"])


if __name__ == "__main__":
    unittest.main()


class AbilitiesOpen(unittest.TestCase):
    def test_chosen_blade_opens_abilities_without_profile_shikai(self):
        self.assertTrue(Z.abilities_open({"blade_id": "zanka_no_tachi"}))
        self.assertFalse(Z.abilities_open({}))
        self.assertFalse(Z.abilities_open({"shikai": True}))  # no blade chosen: nothing to fire


class BankaiSimpleAbilities(unittest.TestCase):
    """Nov 27: every blade has a technique + a second simple ability; both turn deadlier when the Bankai is open."""

    def _run(self, blade, act, bank):
        import random
        import engine as E
        w = {"attack": 12, "crit": 0.0, "element": "light", "skills": [], "weapon_type": "melee"}
        S = {"zanjutsu": 40, "hoho": 30, "kido": 20, "hakuda": 20}
        f = E.new_fighter("A", 60, S, 800, 400, w, race="shinigami", bt=Z.blade_technique(blade))
        f["blade"], f["bu"], f["b2"] = blade, Z.blade_ultimate(blade), Z.blade_b2(blade)
        b = E.new_fighter("B", 60, S, 100000, 400, w, ai=True)
        f["x"]["sk"] = 1
        if bank:
            f["form"].update(on=2, mult=1.0, left=3)
        f["hp"] = int(f["max_hp"] * 0.5)
        st = E.new_state(f, b, random.Random(4))
        st["cur"], st["awaiting"], st["dist"] = "a", True, 0
        self.assertTrue(E.can(f, act, st), (blade, act))
        h = b["hp"]
        ev = E.do_action(st, act, random.Random(4))
        return h - b["hp"], ev

    def test_every_blade_has_b2_and_a_bankai_form(self):
        for b in Z.BLADE_TECH:
            if b == "kyoka_suigetsu":
                continue
            t, u = Z.blade_technique(b), Z.blade_b2(b)
            self.assertTrue(t["bk"].get("fa") and t["bk"].get("en"), b)
            self.assertTrue(u["bk"].get("fa") and u["bk"].get("en"), b)
            self.assertNotEqual(t["bk"]["fa"], t["fa"], b)
            self.assertNotEqual(u["bk"]["fa"], u["fa"], b)

    def test_bankai_hits_harder_and_names_the_ability(self):
        for b in ("zanka_no_tachi", "katen_kyokotsu", "hyorinmaru", "senbonzakura", "zabimaru"):
            d0, _ = self._run(b, "bt", False)
            d1, ev = self._run(b, "bt", True)
            self.assertGreater(d1, d0, b)
            self.assertTrue([e for e in ev if e["k"] == "bt" and e["bk"]], b)
        for b in ("hyorinmaru", "zabimaru", "zanka_no_tachi"):
            d0, _ = self._run(b, "b2", False)
            d1, ev = self._run(b, "b2", True)
            self.assertGreater(d1, d0, b)
            self.assertTrue([e for e in ev if e["k"] == "b2" and e["bk"]], b)

    def test_guard_and_focus_get_stronger_in_bankai(self):
        for b in ("senbonzakura", "zangetsu"):
            a, ev0 = self._run(b, "b2", False)
            c, ev1 = self._run(b, "b2", True)
            self.assertTrue(any(e["k"] == "gen" for e in ev0) and any(e["k"] == "gen" for e in ev1), b)
        self.assertGreater(Z.blade_b2("senbonzakura")["bk"]["shield"], Z.blade_b2("senbonzakura")["shield"])
        self.assertGreater(Z.blade_b2("zangetsu")["bk"]["buff"][1], Z.blade_b2("zangetsu")["buff"][1])

    def test_kyoka_keeps_its_own_kit(self):
        self.assertIsNone(Z.blade_b2("kyoka_suigetsu"))
