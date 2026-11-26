"""Nov 26 requests: stronger Hadō, higher regen, Final Judgment closed, Bakudō without cooldown."""
import re
import pathlib
import random
import unittest

import data_balance as BAL
import data_kido as KD
import engine as E
from test_nov26_balance import fighter


class Nov26Requests(unittest.TestCase):
    def test_hado_hits_harder_and_may_pass_the_blow_cap_in_duels(self):
        self.assertGreaterEqual(E.HADO_DMG_K, 3.0)
        self.assertGreater(E.HADO_HIT_CAP, 0.30)
        self.assertGreater(E.HADO_DUEL_CAP_K, 1.0)

    def test_regen_is_higher(self):
        self.assertGreaterEqual(E.TURN_HP_REGEN, 0.05)
        self.assertGreaterEqual(BAL.PASSIVE_REGEN_CAP_DUEL, 0.05)
        self.assertGreaterEqual(BAL.PASSIVE_REGEN_CAP, 0.06)

    def test_final_judgment_is_closed(self):
        # read the source: the service imports the database driver, which a plain test run may not have
        src = pathlib.Path(__file__).with_name("service_final_judgment.py").read_text(encoding="utf-8")
        self.assertRegex(src, r"(?m)^FJ_OPEN\s*=\s*False")
        self.assertIn('return "closed", None', src)
        combat = pathlib.Path(__file__).with_name("handlers_combat.py").read_text(encoding="utf-8")
        self.assertNotIn('"fjd"', combat)

    def test_bakudo_has_no_cooldown_after_casting(self):
        a, b = fighter("A"), fighter("B")
        a["kido"] = {"had": [], "bak": [30]}
        a["max_re"] = a["re"] = 100000
        st = E.new_state(a, b, random.Random(1), pvp=True)
        st["cur"] = "a"
        E.do_action(st, "bk", random.Random(1))
        self.assertEqual(KD.spell_cd(30, "bak"), 0)
        self.assertNotIn("b30", E._kcd(a))


if __name__ == "__main__":
    unittest.main()
