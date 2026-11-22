"""Nov 19 batch: 500 accessories, drop share, tempering stones, level bands, roll shop, Inner World 2, wheels."""
import random
import unittest
from collections import Counter

import data_accessories as A
import data_extras2 as X
import data_items as D
import service_adventure as S


class AccessoryCatalog(unittest.TestCase):
    def test_exactly_500_unique(self):
        self.assertEqual(len(A.ACCESSORIES), 500)
        self.assertEqual(len({a["item_id"] for a in A.ACCESSORIES}), 500)
        self.assertEqual(len({a["name_en"].lower() for a in A.ACCESSORIES}), 500)
        self.assertEqual(len({a["name_fa"] for a in A.ACCESSORIES}), 500)

    def test_one_colour_per_name_and_no_stages(self):
        for a in A.ACCESSORIES:
            self.assertNotRegex(a["name_en"], r"(?i)stage|\b(I|II|III)\b$")
            self.assertIn(a["rarity"], X.RARITIES)
            self.assertIn(a["subtype"], ("ring", "necklace"))
            self.assertEqual(a["category"], "accessory")

    def test_single_quincy_cross(self):
        crosses = [a for a in D.ALL.values() if a["category"] == "accessory" and not a.get("retired")
                   and "quincy cross" in a["name_en"].lower()]
        self.assertEqual(len(crosses), 1)

    def test_higher_colour_is_stronger(self):
        best = {}
        for a in A.ACCESSORIES:
            best.setdefault(a["rarity"], []).append(a["stats"]["bonus"])
        order = [r for r in X.RARITIES if r in best]
        for lo, hi in zip(order, order[1:]):
            self.assertLess(max(best[lo]), min(best[hi]) + 1e-9)

    def test_mythic_reserved(self):
        self.assertEqual(len(D.MYTHIC_ACCESSORIES), 20)
        for iid in D.MYTHIC_ACCESSORIES:
            self.assertFalse(D.ALL[iid]["tradeable"])
            self.assertNotIn(iid, D.BY_RARITY["Mythic"])

    def test_old_accessories_swap_to_same_colour_and_slot(self):
        self.assertTrue(D.ACC_SWAP)
        for old, new in D.ACC_SWAP.items():
            self.assertTrue(D.ALL[old].get("retired"))
            self.assertEqual(D.ALL[old]["rarity"], D.ALL[new]["rarity"])
            self.assertEqual(D.ALL[old]["subtype"], D.ALL[new]["subtype"])

    def test_drop_share_kept(self):
        rng = random.Random(7)
        picks = [D.pick_shared("Epic", rng) for _ in range(4000)]
        share = sum(D.ALL[i]["category"] == "accessory" for i in picks) / len(picks)
        self.assertAlmostEqual(share, D.ACC_SHARE.get("Epic", share), delta=0.05)
        self.assertFalse(any(D.ALL[i].get("retired") for i in picks))


class Stones(unittest.TestCase):
    def test_from_plus_six(self):
        self.assertEqual([S.stones_needed(p) for p in range(0, 10)], [0, 0, 0, 0, 0, 1, 2, 3, 4, 5])

    def test_items_exist(self):
        self.assertEqual(D.ALL[X.TEMPER_STONE]["category"], "temper")
        self.assertEqual(D.ALL[X.INNER_KEY]["category"], "inner_key")
        self.assertFalse(D.ALL[X.INNER_KEY]["tradeable"])


class Bands(unittest.TestCase):
    def test_level_band(self):
        self.assertEqual(X.level_band(1), 0)
        self.assertEqual(X.level_band(20), 0)
        self.assertEqual(X.level_band(21), 1)
        self.assertEqual(X.level_band(100), 4)
        self.assertEqual(X.level_band(250), len(X.LEVEL_BOSSES) - 1)


class Inner2(unittest.TestCase):
    def test_caps_are_whole_steps(self):
        for _f, _e, key, step, cap in X.INNER2.values():
            self.assertAlmostEqual(cap / step, round(cap / step))


class NewRelics(unittest.TestCase):
    def test_forty_relics_and_the_luck_relic(self):
        self.assertEqual(len(X.NEW_RELICS), 41)  # 40 + Urahara's Striped Hat, the first Legendary luck relic
        for r in X.NEW_RELICS:
            self.assertIn(r["item_id"], D.ALL)
        hat = D.ALL[X.NEW_RELICS[-1]["item_id"]]
        self.assertEqual((hat["rarity"], hat["effect"]["kind"]), ("Legendary", "drop"))
        self.assertAlmostEqual(hat["effect"]["v"], 0.13)
        self.assertIn(hat["item_id"], D.BY_RARITY["Legendary"])


class MythicKidoRings(unittest.TestCase):
    def test_three_red_kido_rings_reach_the_game(self):
        rings = [D.ALL[i] for i in D.MYTHIC_ACCESSORIES
                 if D.ALL[i]["subtype"] == "ring" and D.ALL[i]["stats"]["stat"] == "kido"]
        self.assertEqual({r["name_en"] for r in rings},
                         {"Tsuba of Kyōka Suigetsu", "Tsuba of Ichimonji", "Ichibei's Ink Brush"})
        for r in rings:
            self.assertFalse(r["tradeable"])
            self.assertNotIn(r["item_id"], D.BY_RARITY["Mythic"])


class RemovedPieces(unittest.TestCase):
    def test_bag_per_level_and_tower_helpers_exist(self):
        import config
        import service_combat as C
        self.assertGreaterEqual(config.BAG_PER_LEVEL, 1)
        for fn in ("blocking_pve", "save_tower", "abandon_tower"):
            self.assertTrue(callable(getattr(C, fn)))

    def test_merged_maps_old_to_live(self):
        for old, new in D.MAT_MERGE.items():
            self.assertEqual(D.merged(old), new)
            self.assertFalse(D.ALL[new].get("retired"))
        self.assertEqual(D.merged("it_t001"), "it_t001")


class RollWeights(unittest.TestCase):
    def test_purple_and_up(self):  # Nov 23: Epic and up only, Legendary is rare, no Mythic from rolls, two rolls a day
        self.assertEqual(set(X.ROLL_WEIGHTS), {"Epic", "Legendary"})
        self.assertEqual(sum(X.ROLL_WEIGHTS.values()), 100)
        self.assertLessEqual(X.ROLL_WEIGHTS["Legendary"], 5)
        self.assertEqual(X.ROLL_DAILY_LIMIT, 2)
        self.assertEqual(X.ROLL_TEN_COST, X.ROLL_COST * 9)


class Wheels(unittest.TestCase):
    def test_yamamoto_above_ichigo(self):
        from data_wheels import WHEELS
        self.assertGreater(WHEELS["w_yamamoto"]["base_cost"], WHEELS["w_ichigo"]["base_cost"])


if __name__ == "__main__":
    unittest.main()
