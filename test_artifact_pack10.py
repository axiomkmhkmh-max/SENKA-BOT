"""Artifact pack 10: 32 more Bleach artifacts. Same rules as the rest: low power, two stats, tiered copy counts."""
import re
import unittest

import data_artifacts as D

NEW = [a for a in D.ARTIFACTS if a["_id"] in {
    "art_hiyori_sandal", "art_jinta_club", "art_kukaku_pipe", "art_lieutenant_badge", "art_chappy", "art_heilig_pfeil",
    "art_yukio_console", "art_seireitei_news", "art_urahara_cane", "art_zabimaru", "art_wabisuke", "art_hozukimaru",
    "art_ruriiro_kujaku", "art_kazeshini", "art_tobiume", "art_haineko", "art_suzumebachi", "art_kenseikan", "art_brazo_izq",
    "art_cross_scaffold", "art_book_end", "art_senzaikyu", "art_sternritter_cloak", "art_schrift", "art_pantera",
    "art_murcielago", "art_los_lobos", "art_tiburon", "art_santa_teresa", "art_ryujin_cane", "art_aizen_coat",
    "art_unohana_braid"}]


class Pack10(unittest.TestCase):
    def test_thirty_two_added_and_all_unique(self):
        self.assertEqual(len(NEW), 32)
        self.assertEqual(len(D.ARTIFACTS), 84)
        for key in ("_id", "name_en", "name_fa"):
            vals = [a[key] for a in D.ARTIFACTS]
            self.assertEqual(len(vals), len(set(vals)), key)

    def test_text_complete_and_persian_has_no_latin(self):
        for a in NEW:
            for k in ("name_en", "name_fa", "lore_en", "lore_fa"):
                self.assertTrue(a[k].strip(), (a["_id"], k))
            self.assertIsNone(re.search(r"[A-Za-z0-9]", a["name_fa"] + a["lore_fa"]), a["_id"])

    def test_low_power_rules_hold(self):
        for a in NEW:
            self.assertGreaterEqual(len(a["bonus"]), 2, a["_id"])
            self.assertTrue(all(0.03 <= v <= D.MAX_STAT for v in a["bonus"].values()), a["_id"])
            self.assertIn(a["tier"], (1, 2, 3))
            self.assertEqual(a["cap"], D.TIERS[a["tier"]]["cap"])
            self.assertEqual(D.art_drop_weight(a["_id"]), 1.0)

    def test_signature_relics_still_the_strongest(self):
        best_normal = max(sum(a["bonus"].values()) for a in D.ARTIFACTS if a["_id"] not in D.SIGNATURE)
        for aid in D.SIGNATURE:
            self.assertGreater(sum(D.ART_BY_ID[aid]["bonus"].values()), best_normal)


if __name__ == "__main__":
    unittest.main()
