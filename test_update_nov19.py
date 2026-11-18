"""Update of 19 Nov: chain milestones and softer resets, merged materials, weapon focus, NPC retreats, cheaper ascension,
easier Legendary dungeons."""
import random
import unittest

import data_items as D
import engine as E
from data_raceweapons import ascend_cost, weapon_focus
from data_races import DIFFICULTY
from service_extras import BY_CAT, chain_after_gap, chain_floor, chain_milestone


class ChainTests(unittest.TestCase):
    def test_milestones(self):
        self.assertEqual(chain_milestone(50)[0], 2)
        self.assertEqual(chain_milestone(500)[0], 5)
        self.assertEqual(chain_milestone(1000), chain_milestone(500))
        self.assertIsNone(chain_milestone(51))

    def test_floor_rises(self):
        self.assertLess(chain_floor(10), chain_floor(60))
        self.assertLess(chain_floor(60), chain_floor(500))

    def test_gap_halves_then_clears(self):
        self.assertEqual(chain_after_gap(600, 3600, 24), 600)
        self.assertEqual(chain_after_gap(600, 30 * 3600, 24), 300)
        self.assertEqual(chain_after_gap(600, 80 * 3600, 24), 0)


class MaterialMergeTests(unittest.TestCase):
    def test_one_material_per_group_and_colour(self):
        live = [x for x in D.ALL.values() if x["category"] == "material" and not x.get("retired")]
        keys = {((x.get("effect") or {}).get("group"), x["rarity"]) for x in live}
        self.assertEqual(len(live), len(keys))
        for old, new in D.MAT_MERGE.items():
            self.assertFalse(D.ALL[new].get("retired"))
            self.assertEqual(D.ALL[old]["rarity"], D.ALL[new]["rarity"])
            self.assertEqual(D.ALL[old]["effect"]["group"], D.ALL[new]["effect"]["group"])

    def test_pools_hand_out_only_live_materials(self):
        for r, ids in D.BY_RARITY.items():
            self.assertFalse(any(D.ALL[i].get("retired") for i in ids if D.ALL[i]["category"] == "material"))
        for rar, ids in BY_CAT.get("material", {}).items():
            self.assertFalse(any(D.ALL[i].get("retired") for i in ids))


class WeaponTests(unittest.TestCase):
    def test_focus_grows(self):
        w0, w5 = D.ALL["rw_shinigami_04_0"], D.ALL["rw_shinigami_04_5"]  # Kidō Asauchi
        self.assertIsNone(weapon_focus(w0, 0))
        self.assertEqual(weapon_focus(w5, 10)[0], "kido")
        self.assertAlmostEqual(weapon_focus(w5, 10)[1], 0.10)

    def test_ascension_cheaper(self):
        self.assertEqual(ascend_cost(0)[2], 1400)

    def test_legendary_easier(self):
        self.assertLess(DIFFICULTY["legendary"], 30)


class NpcRetreatTests(unittest.TestCase):
    def test_never_more_than_two_in_a_row(self):
        from balance_sim import foe, player
        rng = random.Random(3)
        for _ in range(200):
            st = E.new_state(player("quincy"), foe(0.9, True), rng, pvp=False)
            st["turn"] = 5
            st["b"]["hp"] = 1
            run = 0
            for _i in range(6):
                a = E.ai_choose(st, "b", rng)
                run = run + 1 if a == "rt" else 0
                self.assertLessEqual(run, 2)

    def test_no_retreat_early(self):
        from balance_sim import foe, player
        rng = random.Random(4)
        st = E.new_state(player("quincy"), foe(0.9, True), rng, pvp=False)
        st["turn"] = 1
        st["b"]["hp"] = 1
        self.assertFalse(E._npc_retreat(st, "b", rng))


if __name__ == "__main__":
    unittest.main()
