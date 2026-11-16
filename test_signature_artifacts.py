import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data_artifacts as D  # noqa: E402


class SignatureArtifacts(unittest.TestCase):
    def test_all_signature_ids_exist(self):
        for aid in D.SIGNATURE:
            self.assertIn(aid, D.ART_BY_ID)

    def test_signature_are_rarest_and_strongest(self):
        normal = [a for a in D.ARTIFACTS if a["_id"] not in D.SIGNATURE]
        best_normal = max(sum(a["bonus"].values()) for a in normal)
        min_normal_cap = min(a["cap"] for a in normal)
        for aid in D.SIGNATURE:
            a = D.ART_BY_ID[aid]
            self.assertEqual(a["tier"], D.SIGNATURE_TIER)
            self.assertLess(a["cap"], min_normal_cap)
            self.assertEqual(D.art_cap(aid), 1)
            self.assertGreater(sum(a["bonus"].values()), best_normal)
            self.assertLess(D.art_drop_weight(aid), 1.0)

    def test_normal_artifacts_unchanged_low_power(self):
        for a in D.ARTIFACTS:
            if a["_id"] not in D.SIGNATURE:
                self.assertTrue(all(0.03 <= v <= D.MAX_STAT for v in a["bonus"].values()), a["_id"])
                self.assertEqual(D.art_drop_weight(a["_id"]), 1.0)


if __name__ == "__main__":
    unittest.main()
