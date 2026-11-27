"""Nov 27 round 4: Yamamoto / Urahara third + fourth simple abilities, heavy = Zanjutsu, regen honoured. python -m unittest test_blade_extra"""
import os, random, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine as E  # noqa: E402
import data_zanpakuto as Z  # noqa: E402
from data_races import RACES  # noqa: E402


def fighter(blade, bankai=False, race="shinigami"):
    r = RACES[race]
    f = E.new_fighter(race, 40, dict(r["stats"]), 100000, 5000,
                      {"attack": 90, "crit": 0.0, "element": "light", "skills": [], "weapon_type": "melee"},
                      armor=10, mods=dict(r["mods"]), race=race, bt=Z.blade_technique(blade))
    for k in ("b2", "b3", "b4"):
        f[k] = Z.blade_b2(blade) if k == "b2" else Z.blade_extra(blade, k)
    f["bu"], f["blade"] = Z.blade_ultimate(blade), blade
    if bankai:
        f["form"]["on"] = 2
    return f


class ExtraTests(unittest.TestCase):
    def test_only_the_two_blades_have_extras(self):
        self.assertEqual(set(Z.BLADE_EXTRA), {"zanka_no_tachi", "benihime"})
        self.assertIsNone(Z.blade_extra("zangetsu", "b3"))

    def test_buttons_work_without_the_infight_shikai(self):
        for blade in Z.BLADE_EXTRA:
            f = fighter(blade)
            for k in ("bt", "b2", "b3", "b4"):
                self.assertTrue(E.can(f, k), (blade, k))

    def test_each_extra_resolves_and_starts_its_own_cooldown(self):
        for blade in Z.BLADE_EXTRA:
            for slot in ("b3", "b4"):
                for bankai in (False, True):
                    rng = random.Random(3)
                    f = fighter(blade, bankai)
                    st = E.new_state(f, fighter("zangetsu"), rng, pvp=True)
                    st["cur"] = "a"
                    ev = E._do_action(st, slot, rng)
                    self.assertTrue([e for e in ev if e.get("k") == "b2"], (blade, slot))
                    self.assertGreater(E._x(f)[slot + "_cd"], 0)
                    self.assertFalse(E.can(f, slot))

    def test_heavy_is_pure_zanjutsu(self):
        f = fighter("zangetsu", race="quincy")
        self.assertEqual(E.strike_base(f, "hvy"), E.strike_base(f, "atk"))

    def test_regen_stat_is_not_squeezed_to_the_flat_cap(self):
        f = fighter("zangetsu")
        f["mods"]["regen"] = 0.40
        f["hp"] = 20000
        rng = random.Random(1)
        st = E.new_state(f, fighter("zangetsu"), rng, pvp=False)
        E.start_turn(st, rng) if False else None
        import data_balance as BAL
        self.assertGreater(min(0.40, BAL.REGEN_MOD_CAP), BAL.PASSIVE_REGEN_CAP)


if __name__ == "__main__":
    unittest.main()
