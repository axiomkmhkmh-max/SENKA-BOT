"""Nov 21 update: stats, HP x6, ratio dodge, side stance, ability families, open worlds, narration, challenges."""
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import data_abilities as AB
import engine as E
from data_misc import DMG_MULT, HAKUDA_HP, HP_MULT
from data_narration import FA, TOTAL_FA
from data_races import band_mark, level_gap_k, loc_band, soft_stat, TOP_LOC


def _f(name, race="human", hoho=50, ab=None, abx=None, ai=False, level=40):
    st = {"zanjutsu": 60, "kido": 40, "hakuda": 50, "hoho": hoho, "reiatsu": 60}
    f = E.new_fighter(name, level, st, 6000, 1000, None, race=race, ai=ai)
    if ab is not None:
        f["ab"], f["abx"] = ab, abx or {}
    return f


class Numbers(unittest.TestCase):
    def test_soft_cap(self):
        self.assertEqual(soft_stat(150), 150)
        self.assertAlmostEqual(soft_stat(300), 150 + 150 * 0.85)
        self.assertAlmostEqual(soft_stat(700), 150 + 127.5 + 180 + 40)

    def test_hakuda_hp_x6(self):
        from service_player import max_hp
        self.assertEqual(HAKUDA_HP, 60)
        self.assertEqual(max_hp(10, 10), int((100 + 200 + 600) * HP_MULT))  # Hakuda's share is x6, then all HP x HP_MULT
        self.assertEqual(E._hb(_f("A")), 6000 / HP_MULT)

    def test_damage_x2_except_a_boss_own_blows(self):
        a, b = _f("A"), _f("B")
        E.new_state(a, b, random.Random(1))
        self.assertEqual((a["dmgx"], b["dmgx"]), (DMG_MULT, DMG_MULT))
        p, boss = _f("P"), _f("Boss")
        boss["foe"] = "boss"
        E.new_state(p, boss, random.Random(1))
        self.assertEqual((p["dmgx"], boss["dmgx"]), (DMG_MULT, 1.0))  # the player still hits x2, the boss does not

    def test_ratio_dodge(self):
        a, b = _f("A", hoho=50), _f("B", hoho=100)
        st = E.new_state(a, b, random.Random(1))
        self.assertAlmostEqual(E.dodge_chance(st, "a"), 0.30)  # B is 2x faster: 5% + 25%
        self.assertAlmostEqual(E.dodge_chance(st, "b"), 0.05)
        b["stats"]["hoho"] = 1000
        self.assertAlmostEqual(E.dodge_chance(st, "a"), 0.60)  # capped

    def test_speed_line_at_start(self):
        st = E.new_state(_f("A", hoho=40), _f("B", hoho=80), random.Random(1))
        sp = [e for e in st["intro"] if e["k"] == "speed"][0]
        self.assertEqual(sp["a"], "B")
        self.assertEqual(sp["p"], 30)


class SideStance(unittest.TestCase):
    def test_free_toggle_once_per_turn(self):
        a, b = _f("A"), _f("B", ai=True)
        st = E.new_state(a, b, random.Random(1))
        st["cur"], st["awaiting"] = "a", True
        re0 = a["re"]
        ev = E.do_action(st, "sd", random.Random(1))
        self.assertEqual(ev[0]["k"], "side")
        self.assertEqual(st["cur"], "a")  # the turn is not spent
        self.assertTrue(st["awaiting"])
        self.assertLess(a["re"], re0)
        self.assertEqual(E.do_action(st, "sd", random.Random(1))[0]["k"], "side_no")
        self.assertAlmostEqual(E.hoho_of(st, "a"), E.eff(a, "hoho") * 2)
        self.assertEqual(E._zone(st, "a"), E.zone_mult(*E.reach_for("melee", None), E.dist_of(st)) * 0.5)


class Families(unittest.TestCase):
    def test_every_race_has_defaults_on_every_button(self):
        for race, slots in AB.RACE_SLOTS.items():
            for act, fam, _i in slots:
                if fam in AB.KIDO_FAMS:
                    continue
                self.assertIn(AB.DEFAULTS[race][act], AB.FAMILIES[fam]["by"], (race, act))

    def test_twenty_ceros_and_arrancar_two_slots(self):
        self.assertEqual(len(AB.FAMILIES["cero"]["types"]), 20)
        self.assertEqual(AB.fam_slots("arrancar", "cero"), ["sg", "t3"])
        self.assertEqual(AB.fam_slots("hollow", "cero"), ["sg"])

    def test_cards_are_race_locked(self):
        kido_free = [c for c in AB.ABILITY_CARD_ITEMS if "fullbringer" in c["races"]]
        self.assertTrue(kido_free)
        self.assertFalse(any(c["effect"]["fam"] in AB.KIDO_FAMS for c in kido_free))
        from data_items import race_cards
        for rar in AB.RARITIES:
            fb = race_cards("fullbringer", rar)
            self.assertFalse(any(i.startswith("kc_") or "kido" in i for i in fb), fb)

    def test_level_scaling(self):
        self.assertAlmostEqual(AB.lv_k(10), 1.54)
        self.assertEqual(AB.lv_turns(2, 5), 3)
        self.assertEqual(AB.lv_turns(2, 10), 4)
        self.assertEqual(AB.lv_cd(4, 8), 3)
        self.assertEqual(AB.lv_cd(1, 10), 1)
        self.assertAlmostEqual(AB.lv_cost(0.10, 10), 0.082)
        self.assertEqual(sum(c for c, _ in AB.UPGRADE), 25)
        self.assertEqual(sum(c for _, c in AB.UPGRADE), 172000)

    def test_bala_always_hits(self):
        a = _f("A", race="arrancar", ab={"sg": {"fam": "cero", "tid": "cero", "lv": 1}})
        b = _f("B", hoho=100000)
        st = E.new_state(a, b, random.Random(1))
        hits = 0
        for i in range(30):
            ev = []
            E._deal(st, "a", 1.0, random.Random(i), ev, "bala", src={"mix": {"reiatsu": 1.0}})
            hits += any(e["k"] == "hit" for e in ev)
        self.assertEqual(hits, 30)

    def test_gates(self):
        a = _f("A", race="shinigami", ab={"gt": {"fam": "getsuga", "tid": "tensho", "lv": 1}})
        self.assertFalse(E.can(a, "gc"))  # Getsuga needs Shikai
        a["x"]["sk"] = 1
        self.assertTrue(E.can(a, "gc"))
        a["ab"]["gt"]["tid"] = "mugetsu"
        self.assertFalse(E.can(a, "gt"))  # Mugetsu needs Bankai
        a["form"]["on"] = 2
        self.assertTrue(E.can(a, "gt"))

    def test_every_type_runs(self):
        rng = random.Random(3)
        for race, slots in AB.RACE_SLOTS.items():
            for act, fam, _i in slots:
                if fam in AB.KIDO_FAMS:
                    continue
                for t in AB.FAMILIES[fam]["types"]:
                    a = _f("A", race=race, ab={act: {"fam": fam, "tid": t["id"], "lv": 10}}, ai=True)
                    a["x"]["sk"], a["form"]["on"] = 1, 2  # every gate open
                    a["x"]["buff_t"], a["x"]["art"] = 3, 1
                    a["hp"] = 2000
                    b = _f("B", ai=True)
                    st = E.new_state(a, b, rng)
                    st["cur"], st["awaiting"] = "a", True
                    for _ in range(3):
                        if st["done"]:
                            break
                        if E.can(a, act):
                            E._ab_run(st, "a", act, rng, [])
                        E.start_turn(st, rng)
                    self.assertTrue(E.describe if hasattr(E, "describe") else True)
                    self.assertTrue(AB.describe(t, 5, "fa", race))
                    self.assertTrue(AB.describe(t, 5, "en", race))


class Worlds(unittest.TestCase):
    def test_bands(self):
        self.assertEqual(loc_band("soul_society", 50), (1, 3))
        self.assertEqual(loc_band(TOP_LOC, 37), (37, 37))
        self.assertEqual(band_mark("soul_society", 50), "🟢")
        self.assertEqual(band_mark("dangai", 21), "🔴")

    def test_reward_by_level_gap(self):
        self.assertAlmostEqual(level_gap_k(45, 21), 1.60)
        self.assertAlmostEqual(level_gap_k(21, 21), 1.0)
        self.assertAlmostEqual(level_gap_k(10, 21), 0.70)
        self.assertAlmostEqual(level_gap_k(1, 80), 0.30)


class Flavour(unittest.TestCase):
    def test_500_lines(self):
        self.assertEqual(TOTAL_FA, 500)
        for pool in FA.values():
            for line in pool:
                line.format(p="x", f="y")

    def test_challenge_cycle(self):
        import service_fightfx as FX
        st = E.new_state(_f("A"), _f("B", ai=True), random.Random(1))
        FX.start(st, random.Random(2))
        self.assertIn(st["chl"]["id"], FX.BY_ID)
        st["chl"] = {"id": "noguard", "n": 0, "c": 0, "ok": True, "seen": []}
        FX.after_turn(st, "df", [{"k": "guard"}], random.Random(1))
        self.assertFalse(FX.result(st, True)["done"])
        st["chl"] = {"id": "crits", "n": 2, "c": 0, "ok": True, "seen": []}
        FX.after_turn(st, "atk", [{"k": "hit", "a": "A", "d": "B", "n": 10, "c": True}] * 2, random.Random(1))
        self.assertTrue(FX.result(st, True)["done"])
        self.assertFalse(FX.result(st, False)["done"])


if __name__ == "__main__":
    unittest.main()
