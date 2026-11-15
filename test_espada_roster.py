"""Espada raid roster checks (pure logic). Run: python -m unittest test_espada_roster -v"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_espada_raid import ESPADA, effect, phase  # noqa: E402


class EspadaRosterTests(unittest.TestCase):
    def test_all_ten_espada_are_present(self):
        names = {v["en"] for v in ESPADA.values()}
        for n in ("Coyote Starrk", "Baraggan Luisenbarn", "Tia Harribel", "Ulquiorra Cifer", "Nnoitra Gilga",
                  "Szayel Aporro", "Grimmjow Jaegerjaquez", "Zommari Rureaux", "Aaroniero Arruruerie"):
            self.assertIn(n, names)
        self.assertTrue(any("Yammy" in x for x in names))

    def test_every_entry_has_required_fields(self):
        for k, v in ESPADA.items():
            for f in ("fa", "en", "hp_mult", "barrier_hi", "barrier_lo", "phase2", "line_fa", "line_en"):
                self.assertIn(f, v, (k, f))
            self.assertIn("fa", v["phase2"], k)
            self.assertIn("en", v["phase2"], k)
            self.assertGreater(v["hp_mult"], 1.0, k)
            self.assertGreaterEqual(v["barrier_lo"], v["barrier_hi"], k)  # second half is tougher

    def test_damage_is_always_at_least_one(self):
        for k in ESPADA:
            for frac in (1.0, 0.5, 0.1):
                out, heal = effect(k, frac, False, 1, 100, 100)
                self.assertGreaterEqual(out, 1, (k, frac))
                self.assertGreaterEqual(heal, 0, (k, frac))

    def test_regen_never_exceeds_max_hp(self):
        for k, v in ESPADA.items():
            _, heal = effect(k, 0.2, False, 10, 99, 100)
            self.assertLessEqual(99 + heal, 100, k)

    def test_released_espada_takes_full_damage(self):
        for k in ESPADA:
            out, heal = effect(k, 0.9, True, 50, 100, 100)
            self.assertEqual((out, heal), (50, 0), k)

    def test_phase_switch_at_half_hp(self):
        for k in ESPADA:
            self.assertEqual(phase(k, 0.6), 1)
            self.assertEqual(phase(k, 0.5), 2)

    def test_healing_follows_the_declared_pattern(self):
        # Phase 1 heals only with pattern "regen"; phase 2 heals with the phase-2 regen value (0 = none).
        for k, v in ESPADA.items():
            _, heal1 = effect(k, 0.8, False, 10, 10, 100)
            if v.get("pattern") != "regen":
                self.assertEqual(heal1, 0, k)
            _, heal2 = effect(k, 0.2, False, 10, 10, 100)
            if float(v["phase2"].get("regen", 0)) == 0:
                self.assertEqual(heal2, 0, k)


if __name__ == "__main__":
    unittest.main()
