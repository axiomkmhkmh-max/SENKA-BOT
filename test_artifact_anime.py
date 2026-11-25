"""Anime artifact powers: Toshiro / Yhwach / Aizen / Ichigo relics fire real combat effects."""
import random
import unittest
import engine as E
import data_artifacts as D

W = {"attack": 100, "crit": 0.0, "element": "light", "skills": [], "weapon_type": "melee"}


def fighter(name, **mods):
    f = E.new_fighter(name, 100, {"zanjutsu": 100, "reiatsu": 100, "hakuda": 1, "hoho": 1, "kido": 1},
                      100000, 100000, W, race="shinigami", mods=mods)
    return f


class AnimeArtifacts(unittest.TestCase):
    def test_every_tier3_plus_artifact_has_an_effect(self):
        for a in D.ARTIFACTS:
            if int(a.get("tier", 1)) >= 3 and a["_id"] not in ("art_hogyoku", "art_soulking"):
                self.assertTrue(D.ART_BY_ID[a["_id"]].get("effect"), a["_id"])

    def test_hyorinmaru_seal_stuns_once_per_three_turns(self):
        a, b = fighter("Toshiro", art_stun_p=1.0), fighter("Foe")
        st = E.new_state(a, b, random.Random(1), duel_rules=False)
        st["turn"] = 5
        E._deal(st, "a", 1.0, random.Random(2), [], "atk")
        self.assertTrue(E.has_fx(b, "skip"))
        b["fx"] = []
        E._deal(st, "a", 1.0, random.Random(3), [], "atk")
        self.assertFalse(E.has_fx(b, "skip"))  # on cooldown

    def test_low_hp_surge(self):
        a = fighter("Ichigo", art_low_hp=[0.5, 0.3])
        high = E._dmg_mult(a)
        a["hp"] = int(a["max_hp"] * 0.3)
        self.assertAlmostEqual(E._dmg_mult(a) / high, 1.3, places=3)

    def test_thorns_reflect(self):
        a, b = fighter("Att"), fighter("Aizen", art_thorns=0.2)
        st = E.new_state(a, b, random.Random(1), duel_rules=False)
        hp = a["hp"]
        E._deal(st, "a", 1.0, random.Random(2), [], "atk")
        self.assertLess(a["hp"], hp)

    def test_almighty_is_mythic_sized(self):
        self.assertGreaterEqual(sum(D.ART_BY_ID["art_almighty"]["bonus"].values()), 0.9)




class ThematicMechanics(unittest.TestCase):
    def test_foresight_dodges_every_nth_blow(self):
        a, b = fighter("Att"), fighter("Yhwach", art_foresight=3)
        st = E.new_state(a, b, random.Random(1), duel_rules=False)
        hits = []
        for i in range(6):
            ev = []
            E._deal(st, "a", 1.0, random.Random(i), ev, "atk")
            hits.append(any(e["k"] == "hit" for e in ev))
        self.assertEqual(hits.count(False) >= 2, True)
        self.assertFalse(hits[2] or hits[5])

    def test_hit_cap_and_no_crit(self):
        a, b = fighter("Att"), fighter("King", art_hit_cap=0.01, art_no_crit=True)
        st = E.new_state(a, b, random.Random(1), duel_rules=False)
        hp = b["hp"]
        for i in range(5):
            ev = []
            E._deal(st, "a", 50.0, random.Random(i), ev, "atk")
            for e in ev:
                if e["k"] == "hit":
                    self.assertFalse(e["c"])
        self.assertGreaterEqual(b["hp"], hp - 5 * int(b["max_hp"] * 0.01) - 5)


if __name__ == "__main__":
    unittest.main()
