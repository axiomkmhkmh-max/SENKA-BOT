"""Nov 26 rebalance: data_balance rules, regen budget, Hadō rhythm, artifacts, blades, dungeon drops. Run: python -m unittest test_nov26_balance -v"""
import random
import unittest

from test_mentor_trade import run  # noqa: F401  (stubs motor / aiogram when missing)
import data_balance as BAL
import data_dungeon_drops as DD
import data_kido as KD
import data_zanpakuto as Z
import engine as E

W = {"attack": 300, "crit": 0.05, "element": "light", "skills": [], "weapon_type": "melee"}


def fighter(name, level=150, zan=250, hak=120, regen=0.0, hpk=1.35):
    st = {"zanjutsu": zan, "kido": 5, "hakuda": hak, "hoho": 60, "reiatsu": 60}
    f = E.new_fighter(name, level, st, int((100 + level * 20 + hak * 60) * 1.5 * hpk), 4000, W, armor=60, race="shinigami",
                      mods={"regen": regen, "dmg": 1.0, "def": 1.0})
    f["hpk"] = hpk
    return f


class Rules(unittest.TestCase):
    def test_cap_scale_follows_power_and_is_bounded(self):
        self.assertAlmostEqual(BAL.cap_scale(100, 100), 1.0)
        self.assertGreater(BAL.cap_scale(200, 100), 1.0)
        self.assertLess(BAL.cap_scale(50, 100), 1.0)
        self.assertEqual(BAL.cap_scale(10 ** 6, 1), BAL.CAP_MAX)
        self.assertEqual(BAL.cap_scale(1, 10 ** 6), BAL.CAP_MIN)

    def test_rating_uses_level_and_stats(self):
        self.assertGreater(BAL.rating(100, {"zanjutsu": 300}), BAL.rating(100, {"zanjutsu": 50}))
        self.assertGreater(BAL.rating(200, {}), BAL.rating(100, {}))

    def test_heal_budget_stops_a_fair_duel_from_stalling(self):
        for seed in range(6):
            a, b = fighter("A", regen=0.12), fighter("B", regen=0.12)
            st = E.new_state(a, b, random.Random(seed), pvp=True)
            E.run_ai(st, random.Random(seed), ai_sides=("a", "b"))
            self.assertLess(st.get("turn", 0), 120, f"seed {seed} stalled")

    def test_passive_regen_never_beats_the_budget(self):
        a = fighter("A", regen=0.5)
        b = fighter("B")
        st = E.new_state(a, b, random.Random(1), pvp=True)
        a["hp"] = a["max_hp"] // 2
        before = a["hp"]
        st["cur"] = "a"
        E.start_turn(st, random.Random(1))
        self.assertLessEqual(a["hp"] - before, int(a["max_hp"] * BAL.PASSIVE_REGEN_CAP_DUEL) + 1)

    def test_hpk_keeps_heals_on_the_old_pool(self):
        self.assertAlmostEqual(E._hb(fighter("A", hpk=1.35)), E._hb(fighter("A", hpk=1.0)) * (fighter("A", hpk=1.35)["max_hp"] / fighter("A", hpk=1.0)["max_hp"]) / 1.35, delta=2)


class Hado(unittest.TestCase):
    def test_small_spells_are_fast_and_big_ones_start_a_group_lock(self):
        self.assertEqual(KD.spell_cd(10, "had"), BAL.SMALL_CD)
        self.assertEqual(BAL.hado_group_cd(99), BAL.BIG_GROUP_CD)
        self.assertEqual(BAL.hado_group_cd(60), 0)

    def test_big_spell_locks_the_other_big_ones(self):
        f = fighter("K")
        f["kido"] = {"had": [97, 98, 99, 31], "bak": []}
        f["re"] = f["max_re"]
        self.assertTrue(E.kido_castable(f, "had", 99))
        E._kcd(f)["hgrp"] = 3
        self.assertFalse(E.kido_castable(f, "had", 98))
        self.assertTrue(E.kido_castable(f, "had", 31))   # a filler is never locked
        self.assertEqual(E._kd_left(f, "had", 98), 3)


class Artifacts(unittest.TestCase):
    def test_short_fight_abilities_exist(self):
        import data_artifacts as A
        ex = A.ANIME_EXTRA
        self.assertIn("opener", ex["art_sokyoku"])
        self.assertIn("open_shield", ex["art_pantera"])
        self.assertIn("mitigate", ex["art_tiburon"])
        self.assertIn("turn_heal", ex["art_murcielago"])

    def test_open_shield_and_mitigate_and_opener_in_the_engine(self):
        a, b = fighter("A"), fighter("B")
        a["mods"]["art_open_shield"] = 0.06
        st = E.new_state(a, b, random.Random(2), pvp=True)
        self.assertGreater(a["shield"], 0)
        c = fighter("C")
        base = E._take_mult(c)
        c["mods"]["art_mitigate"] = 0.10
        self.assertLess(E._take_mult(c), base)


class Blades(unittest.TestCase):
    def test_new_blades_have_kits(self):
        for bid in ("benihime", "katen_kyokotsu"):
            self.assertIn(bid, Z.unlocked_blades(200))
            self.assertIsNotNone(Z.blade_technique(bid))
            self.assertIsNotNone(Z.blade_ultimate(bid))
        self.assertTrue(Z.blade_ultimate("benihime").get("shield"))   # the defence mode


class Dungeons(unittest.TestCase):
    def test_usable_colour_by_level(self):
        self.assertEqual(DD.usable_max_idx(1), 0)
        self.assertEqual(DD.usable_max_idx(49), 3)
        self.assertEqual(DD.usable_max_idx(50), 4)
        self.assertEqual(DD.usable_max_idx(80), 5)
        self.assertEqual(DD.clip_chest(4, 5, 60), (4, 4))
        self.assertEqual(DD.clip_chest(4, 5, 10), (1, 1))

    def test_every_dungeon_has_its_own_final_drops(self):
        from data_races import DUNGEONS
        seen = set()
        for did in DUNGEONS:
            drops = DD.final_drops(did)
            self.assertTrue(drops, did)
            self.assertEqual(drops, DD.final_drops(did))   # stable
            seen.add(tuple(drops))
        self.assertGreater(len(seen), len(DUNGEONS) // 3)


if __name__ == "__main__":
    unittest.main()
