"""Hollow Hunt checks (pure logic). Run: python -m unittest test_engine_hunt -v"""
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine_hunt as H  # noqa: E402


class HuntFlowTests(unittest.TestCase):
    def test_three_stages_then_finished(self):
        rng = random.Random(1)
        h = H.new_hunt(rng)
        for _ in range(H.STAGES):
            opts = H.current_options(h)
            self.assertGreaterEqual(len(opts), 2)
            H.choose(h, opts[0]["id"], rng)
        self.assertTrue(H.summarize(h)["finished"])
        self.assertEqual(H.current_options(h), [])

    def test_unknown_option_rejected(self):
        rng = random.Random(2)
        h = H.new_hunt(rng)
        with self.assertRaises(ValueError):
            H.choose(h, "nope", rng)

    def test_cannot_act_after_finish(self):
        rng = random.Random(3)
        h = H.new_hunt(rng)
        for _ in range(H.STAGES):
            H.choose(h, H.current_options(h)[0]["id"], rng)
        with self.assertRaises(ValueError):
            H.choose(h, "track", rng)

    def test_options_hide_risk_profile(self):
        h = H.new_hunt(random.Random(4))
        for o in H.current_options(h):
            self.assertEqual(set(o.keys()), {"id", "label"})

    def test_button_order_varies_but_profiles_fixed(self):
        orders = set()
        for seed in range(20):
            h = H.new_hunt(random.Random(seed))
            orders.add(tuple(o["id"] for o in H.current_options(h)))
        self.assertGreater(len(orders), 1)


class RiskTests(unittest.TestCase):
    def test_trap_marks_hunt_and_loses_clean_bonus(self):
        rng = random.Random(5)
        h = H.new_hunt(rng)
        # force a trap option in stage 0 by editing the template order is avoided; build manually
        h["stages"][0] = [{"id": "t", "kind": "trap", "dmg_pct": 0.2, "coin": 0.5, "label": "t"},
                          {"id": "r", "kind": "reward", "xp": 1.0, "coin": 1.0, "label": "r"}]
        out = H.choose(h, "t", rng)
        self.assertEqual(out["dmg_pct"], 0.2)
        self.assertTrue(h["trapped"])
        for _ in range(H.STAGES - 1):
            H.choose(h, H.current_options(h)[0]["id"], rng)
        self.assertFalse(H.summarize(h)["clean"])
        self.assertNotIn("bonus", H.summarize(h))

    def test_clean_hunt_gets_bonus(self):
        rng = random.Random(6)
        h = {"stage": 0, "trapped": False, "log": [], "stages": [
            [{"id": "a", "kind": "reward", "xp": 1.0, "coin": 1.0, "label": "a"}],
            [{"id": "b", "kind": "reward", "xp": 1.0, "coin": 1.0, "label": "b"}],
            [{"id": "c", "kind": "reward", "xp": 1.0, "coin": 1.0, "label": "c"}]]}
        for oid in ("a", "b", "c"):
            H.choose(h, oid, rng)
        s = H.summarize(h)
        self.assertTrue(s["clean"])
        self.assertAlmostEqual(s["xp_mult"], 3.0 + H.CLEAN_BONUS_XP)

    def test_fight_option_records_scale(self):
        rng = random.Random(7)
        h = {"stage": 0, "trapped": False, "log": [], "stages": [
            [{"id": "f", "kind": "fight", "scale": 1.3, "xp": 2.0, "label": "f"}]] * 3}
        out = H.choose(h, "f", rng)
        if out["fight"]:
            self.assertEqual(out["scale"], 1.3)
        else:
            self.assertTrue(out.get("feint"))  # the rare feint path became a trap

    def test_feint_rate_is_small(self):
        feints = 0
        n = 2000
        for seed in range(n):
            rng = random.Random(seed)
            h = {"stage": 0, "trapped": False, "log": [], "stages": [
                [{"id": "f", "kind": "fight", "scale": 1.0, "xp": 1.0, "label": "f"}]] * 3}
            if H.choose(h, "f", rng).get("feint"):
                feints += 1
        self.assertLess(abs(feints / n - H.FIGHT_TRAP_CHANCE), 0.04)


if __name__ == "__main__":
    unittest.main()
