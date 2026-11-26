"""One heal line per turn: natural recovery, companion regen and Guard no longer print (and stack) as separate heals."""
import random
import unittest

import engine as E


def _f(name, ai=False, regen=0.0):
    f = E.new_fighter(name, 20, {"zanjutsu": 40, "hoho": 30, "kido": 20, "hakuda": 20, "reiatsu": 20}, 1000, 200,
                      {"attack": 12, "crit": 0.0, "element": "light", "skills": [], "weapon_type": "melee"}, race="human", ai=ai)
    if regen:
        f["mods"]["regen"] = regen
    return f


class HealMerge(unittest.TestCase):
    def test_merge_sums_same_fighter(self):
        ev = [{"k": "heal", "a": "A", "n": 10}, {"k": "x"}, {"k": "heal", "a": "A", "n": 5}, {"k": "heal", "a": "B", "n": 7}]
        out = E.merge_heals(ev)
        self.assertEqual([e for e in out if e["k"] == "heal"], [{"k": "heal", "a": "A", "n": 15}, {"k": "heal", "a": "B", "n": 7}])

    def test_start_turn_one_heal_line_with_companion_regen(self):
        a, b = _f("A", regen=0.02), _f("B")
        st = E.new_state(a, b, random.Random(1))
        a["hp"] = 500
        st["cur"] = "a"
        ev, _ = E.start_turn(st, random.Random(1))
        heals = [e for e in ev if e["k"] == "heal"]
        self.assertEqual(len(heals), 1)
        hb = 1000 / E.HP_MULT  # repeating heals are measured on the old-scale HP (long fights)
        import data_balance as BAL
        want = min(int(hb * E.TURN_HP_REGEN) + int(hb * 0.02), int(1000 * BAL.PASSIVE_REGEN_CAP))  # Nov 26: one per-turn regen budget
        self.assertEqual(heals[0]["n"], want)

    def test_guard_does_not_stack_on_natural_regen(self):
        a, b = _f("A"), _f("B")
        st = E.new_state(a, b, random.Random(1))
        a["hp"] = 500
        st["cur"] = "a"
        E.start_turn(st, random.Random(1))
        hp_after_tick = a["hp"]
        E.do_action(st, "df", random.Random(1))
        # total recovery of the turn is the Guard share (5%), not 3% + 5%
        self.assertEqual(a["hp"] - 500, int(1000 / E.HP_MULT * E.GUARD_HP_GAIN))
        self.assertGreaterEqual(a["hp"], hp_after_tick)  # Nov 26: natural regen is now 5% = the Guard share, so Guard adds nothing on top but never lowers it

    def test_ai_guard_turn_prints_a_single_heal(self):
        a, b = _f("A"), _f("B", ai=True)
        st = E.new_state(a, b, random.Random(3))
        b["hp"] = 400
        st["cur"] = "b"
        st["first"] = "b"
        rng = random.Random(3)
        # force the AI to guard
        orig = E.ai_choose
        E.ai_choose = lambda s, side, r: "df"
        try:
            ev = E.run_ai(st, rng)
        finally:
            E.ai_choose = orig
        self.assertLessEqual(len([e for e in ev if e["k"] == "heal" and e["a"] == "B"]), 1)


if __name__ == "__main__":
    unittest.main()
