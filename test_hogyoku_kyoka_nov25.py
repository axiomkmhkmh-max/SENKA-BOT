import random
import unittest

import engine as E


def fighter(name="A", blade=None, true_hog=False):
    f = E.new_fighter(name, 100, {"zanjutsu": 100, "hakuda": 100, "hoho": 80, "reiatsu": 100, "kido": 100},
                      10000, 10000, {"attack": 100, "crit": 0.0, "element": "light", "skills": [], "weapon_type": "melee"},
                      mods={"dmg": 1.0, "def": 1.0, "regen": 0.04 if true_hog else 0.0,
                            "artifact_lives": 1 if true_hog else 0, "artifact_revive_hp": 0.60})
    f["blade"] = blade
    if true_hog:
        f["mods"]["hogyoku_true"] = True
        f["mods"]["artifact_hogyoku"] = True
    return f


def state(a, b, seed=1):
    st = E.new_state(a, b, random.Random(seed), duel_rules=False)
    st["cur"] = st["first"] = "a"
    st["awaiting"] = True
    st["dist"] = 0
    return st


def avg_dmg(action, shikai=False, n=300):
    tot = 0
    for s in range(n):
        a, b = fighter("A", "kyoka_suigetsu"), fighter("B")
        st = state(a, b, s)
        if shikai:
            a["x"]["kyoka_shikai_t"] = 5
        h = b["hp"]
        E._do_action(st, action, random.Random(s))
        tot += h - b["hp"]
    return tot / n


class SealedKyokaPanels(unittest.TestCase):
    def test_sealed_strikes_are_real_strikes(self):
        base = avg_dmg("atk")
        self.assertGreater(avg_dmg("ks1"), base * 2.0)
        self.assertGreater(avg_dmg("ks4"), base * 2.3)
        self.assertGreater(avg_dmg("ks3"), 0)  # Mind Distortion used to deal nothing

    def test_domination_halves_the_victims_own_damage_not_damage_taken(self):
        def hit(dom_target=False, dom_attacker=False):
            a, b = fighter("A"), fighter("B")
            st = state(a, b)
            if dom_target:
                b["x"]["ks_dom"] = 3
            if dom_attacker:
                a["x"]["ks_dom"] = 3
            h = b["hp"]
            E._deal(st, "a", 1.0, random.Random(3), [], "atk")
            return h - b["hp"]
        n = sum(hit() for _ in range(1)); 
        self.assertEqual(hit(dom_target=True), n)         # the dominated target takes the same as before
        self.assertAlmostEqual(hit(dom_attacker=True) / n, 0.5, delta=0.02)  # the dominated attacker deals half

    def test_false_reality_decoy_absorbs_next_blow_and_counters(self):
        a, b = fighter("A", "kyoka_suigetsu"), fighter("B")
        st = state(a, b)
        E._do_action(st, "ks2", random.Random(1))
        self.assertEqual(a["x"]["ks_decoy"], 1)
        hp_a, hp_b = a["hp"], b["hp"]
        ev = []
        E._deal(st, "b", 1.0, random.Random(2), ev, "atk")
        self.assertEqual(a["hp"], hp_a)          # the blow hit the decoy
        self.assertLess(b["hp"], hp_b)           # and was answered
        self.assertEqual(a["x"]["ks_decoy"], 0)  # one blow only
        self.assertTrue(any(e.get("k") == "ks_decoy_hit" for e in ev))


class TrueHogyoku(unittest.TestCase):
    def test_evolution_grows_and_is_bounded(self):
        a, b = fighter("A", true_hog=True), fighter("B")
        st = state(a, b)
        st["final_judgment"] = {"phases": 1}
        for _ in range(25):
            st["cur"] = "a"
            E.start_turn(st, random.Random(1))
        self.assertEqual(a["x"]["hog_stage"], E.HOG_MAX_STAGE)
        self.assertAlmostEqual(a["mods"]["dmg"], 1.0 + E.HOG_DMG_STAGE * E.HOG_MAX_STAGE)
        self.assertAlmostEqual(a["mods"]["regen"], 0.04 + E.HOG_REGEN_STAGE * E.HOG_MAX_STAGE)

    def test_longer_fight_means_less_damage_taken(self):
        def taken(stage):
            a, b = fighter("A", true_hog=True), fighter("B")
            st = state(a, b)
            a["x"]["hog_stage"] = stage
            st["cur"] = "b"
            h = a["hp"]
            E._deal(st, "b", 1.0, random.Random(5), [], "atk")
            return h - a["hp"]
        self.assertLess(taken(10), taken(0) * 0.8)

    def test_big_hit_is_capped_at_high_stage(self):
        a, b = fighter("A", true_hog=True), fighter("B")
        st = state(a, b)
        a["x"]["hog_stage"] = 10
        h = a["hp"]
        E._apply(st, "b", 9000, False, random.Random(1), [], "tech", False)
        self.assertGreaterEqual(a["hp"], h - int(a["max_hp"] * 0.20))

    def test_revive_once_and_jumps_stages(self):
        a, b = fighter("A", true_hog=True), fighter("B")
        st = state(a, b)
        a["x"]["hog_stage"] = 2
        a["hp"] = 0
        ev = []
        E._check_end(st, ev)
        self.assertEqual(a["hp"], 6000)
        self.assertEqual(a["x"]["hog_stage"], 2 + E.HOG_REBIRTH_STAGES)
        self.assertTrue(any(e.get("k") == "hog_rebirth" for e in ev))
        a["hp"] = 0
        E._check_end(st, [])
        self.assertTrue(st["done"])  # only one revival

    def test_shard_artifact_keeps_old_bounded_evolution(self):
        a, b = fighter("A"), fighter("B")
        a["mods"]["artifact_hogyoku"] = True
        st = {"a": a, "b": b, "cur": "a", "done": False, "final_judgment": {"phases": 1}}
        for _ in range(10):
            E.start_turn(st, random.Random(1))
        self.assertLessEqual(a["mods"]["dmg"], 1.241)
        self.assertNotIn("hog_stage", {k: v for k, v in a["x"].items() if v})


if __name__ == "__main__":
    unittest.main()
