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
