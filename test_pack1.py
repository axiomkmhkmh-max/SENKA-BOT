"""Pack 1: duel first-strike fairness, easier levelling, duel XP for both sides, canon release commands."""
import _isolate  # noqa: E402  (a clean module cache for this file; restored afterwards)

setUpModule, tearDownModule = _isolate.set_up, _isolate.tear_down

import random
import unittest

import balance_sim as B
import engine as E
from data_misc import DUEL


def _pair(race="shinigami"):
    return B.player(race), B.player(race)


class DuelOpening(unittest.TestCase):
    def test_faster_side_no_longer_always_opens(self):
        rng = random.Random(7)
        opened = 0
        for _ in range(400):
            a, b = _pair()
            a["stats"]["hoho"] = b["stats"]["hoho"] * 3  # a is far faster
            st = E.new_state(a, b, rng, pvp=True)
            opened += st["first"] == "a"
        share = opened / 400
        self.assertGreater(share, 0.55)  # speed still matters...
        self.assertLess(share, 0.5 + DUEL["init_spread"] + 0.06)  # ...but never decides it outright

    def test_second_mover_starts_with_guard(self):
        a, b = _pair()
        st = E.new_state(a, b, random.Random(1), pvp=True)
        second = st["b" if st["first"] == "a" else "a"]
        self.assertEqual(second["shield"], int(second["max_hp"] * DUEL["second_guard"]))
        self.assertTrue(any(e["k"] == "second_guard" for e in st["intro"]))

    def test_pve_initiative_unchanged(self):
        a, b = _pair()
        a["stats"]["hoho"] = b["stats"]["hoho"] * 3
        for seed in range(20):
            st = E.new_state(dict(a, fx=[], shield=0), dict(b, fx=[], shield=0), random.Random(seed), pvp=False)
            self.assertEqual(st["first"], "a")

    def test_opening_blow_is_softened(self):
        def first_hit(turn):
            a, b = _pair()
            st = E.new_state(a, b, random.Random(3), pvp=True)
            side = st["first"]
            st["turn"] = turn
            tgt = st["b" if side == "a" else "a"]
            tgt["shield"] = 0
            ev = []
            return E._apply(st, side, 200, False, random.Random(3), ev, "atk", False)  # below the 25% hit cap
        self.assertEqual(first_hit(1), int(200 * DUEL["opening_dmg"]))
        self.assertEqual(first_hit(2), 200)


class StunGuard(unittest.TestCase):
    def test_duel_stun_guard_lasts(self):
        a, b = _pair()
        st = E.new_state(a, b, random.Random(2), pvp=True)
        side = st["cur"]
        f = st[side]
        E.add_fx(f, "skip", 1)
        _, skipped = E.start_turn(st, random.Random(2))
        self.assertTrue(skipped)
        self.assertEqual(f["x"]["stun_im"], DUEL["stun_guard"])
        _, skipped = E.start_turn(st, random.Random(2))  # next own turn: acts, guard ticks down but stays on
        self.assertFalse(skipped)
        E.add_fx(f, "skip", 1)
        self.assertFalse(any(x["k"] == "skip" for x in f["fx"]))


class Levelling(unittest.TestCase):
    def test_curve_default_is_easier(self):
        from config import GAME_DEFAULTS
        self.assertLessEqual(GAME_DEFAULTS["xp_curve_k"], 1.6)

    def test_newbie_mult(self):
        from service_player import newbie_xp_mult
        st = {"newbie_xp_level": 40, "newbie_xp_mult": 1.5}
        self.assertEqual(newbie_xp_mult(10, st), 1.5)
        self.assertEqual(newbie_xp_mult(40, st), 1.0)


class CanonCalls(unittest.TestCase):
    def test_release_calls(self):
        from data_zanpakuto import release_call, stage_name
        self.assertEqual(release_call("senbonzakura", "en"), "Scatter, Senbonzakura!")
        self.assertEqual(stage_name("senbonzakura", "bankai", "en"), "Senbonzakura Kageyoshi")
        self.assertEqual(release_call("zabimaru", "en", "bankai"), "Bankai! Hihiō Zabimaru!")
        self.assertIsNone(release_call("tengumaru", "en"))

    def test_shikai_event_speaks_the_command(self):
        from render import ab_event_text
        line = ab_event_text("en", {"k": "shikai", "a": "Rukia", "bl": "sode_no_shirayuki"})
        self.assertIn("Dance, Sode no Shirayuki!", line)


if __name__ == "__main__":
    unittest.main()
