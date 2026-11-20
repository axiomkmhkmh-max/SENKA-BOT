"""A fighter who just lost a turn to a stun cannot be stunned again before they act (no chain-stun)."""
import random
import unittest

import engine as E


def _f(name):
    return E.new_fighter(name, 20, {"zanjutsu": 40, "hoho": 30, "kido": 20, "hakuda": 20}, 400, 200,
                         {"attack": 12, "crit": 0.05, "element": "light", "skills": [], "weapon_type": "melee"})


class StunLock(unittest.TestCase):
    def test_no_chain_stun(self):
        rng = random.Random(1)
        st = E.new_state(_f("A"), _f("B"), rng)
        st["cur"] = st["first"] = "a"
        E.add_fx(st["b"], "skip", 1)               # B is stunned
        ev, skipped = E.start_turn({**st, "cur": "b"} if False else st, rng) if st["cur"] == "b" else (None, None)
        st["cur"] = "b"
        ev, skipped = E.start_turn(st, rng)
        self.assertTrue(skipped)                    # B loses the turn
        E.add_fx(st["b"], "skip", 1)               # A tries to stun again right away
        self.assertFalse(E.has_fx(st["b"], "skip"))
        ev, skipped = E.start_turn(st, rng)         # B's next turn: acts normally
        self.assertFalse(skipped)
        E.add_fx(st["b"], "skip", 1)               # after acting, B can be stunned again
        self.assertTrue(any(x["k"] == "skip" for x in st["b"]["fx"]))


if __name__ == "__main__":
    unittest.main()
