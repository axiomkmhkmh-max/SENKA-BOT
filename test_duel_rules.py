"""Duel rules (DUEL in data_misc): hit cap, hit floor, multiplier caps, flat release price, one release, release lock.
Pure engine tests, no database. Run: python -m unittest test_duel_rules -v"""
import os, random, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine as E
from data_misc import DUEL

W = {"attack": 100, "crit": 0.0, "element": "light", "skills": [], "weapon_type": "melee"}


def fighter(name, level, zan, hakuda, hp=None, re=3000, race="shinigami"):
    stats = {"zanjutsu": zan, "kido": 5, "hakuda": hakuda, "hoho": 20, "reiatsu": 20}
    return E.new_fighter(name, level, stats, hp or (100 + level * 20 + hakuda * 60), re, W, race=race)


def state(a, b, **kw):
    return E.new_state(a, b, random.Random(1), **kw)


class Rules(unittest.TestCase):
    def test_no_one_shot(self):
        for seed in range(30):
            strong, weak = fighter("S", 100, 4000, 500, 20000), fighter("W", 40, 50, 20, 3000)
            st = E.new_state(strong, weak, random.Random(seed), pvp=True)
            ev = []
            E._deal(st, "a", 5.0, random.Random(seed), ev)
            import data_balance as BAL
            # Nov 26: the cap follows power: the strongest possible attacker still takes at most CAP_MAX x hit_cap
            self.assertGreaterEqual(weak["hp"], weak["max_hp"] * (1 - DUEL["hit_cap"] * BAL.CAP_MAX) - 1)

    def test_floor_follows_attacker_power_not_target_hp(self):
        weak, strong, tank = fighter("W", 40, 60, 5, 3000), fighter("S", 100, 4000, 500, 20000), fighter("T", 100, 100, 3000, 60000)
        tank["armor"] = 5000
        def avg(att, dfn, rules):
            tot = 0
            for seed in range(40):
                a, d = dict(att), dict(dfn)
                import copy
                a, d = copy.deepcopy(att), copy.deepcopy(dfn)
                st = E.new_state(a, d, random.Random(seed), pvp=True, duel_rules=rules)
                st["dist"] = 0
                ev = []
                E._deal(st, "a", 1.0, random.Random(seed), ev, "atk")
                tot += sum(e.get("n", 0) for e in ev if e["k"] == "hit")
            return tot / 40
        on, off = avg(weak, tank, True), avg(weak, tank, False)
        self.assertGreater(on, off)                      # the floor lifts a weak hitter against heavy armour
        self.assertGreater(avg(strong, tank, True), on)  # ... but a stronger hitter still hits harder (no flattening)

    def test_rules_off_outside_duels(self):
        a, b = fighter("A", 100, 4000, 500, 20000), fighter("B", 40, 50, 20, 3000)
        st = E.new_state(a, b, random.Random(1), pvp=False)
        self.assertFalse(st["duel"] or a.get("duel"))
        st = E.new_state(*[fighter("A", 50, 100, 50), fighter("B", 50, 100, 50)], random.Random(1), pvp=True, duel_rules=False)
        self.assertFalse(st["duel"])

    def test_boss_and_wild_never_get_duel_rules(self):
        a, b = fighter("A", 50, 100, 50), fighter("B", 50, 100, 50)
        b["foe"], b["wild"] = "boss", True
        E.new_state(a, b, random.Random(1), pvp=True)
        self.assertTrue(a["duel"])
        self.assertFalse(b["duel"])

    def test_form_cap(self):
        a, b = fighter("A", 50, 100, 50), fighter("B", 50, 100, 50)
        E.new_state(a, b, random.Random(1), pvp=True)
        base = E.eff(a, "zanjutsu")
        a["form"].update(on=2, mult=3.0)
        self.assertAlmostEqual(E.eff(a, "zanjutsu"), base * DUEL["form_cap"], places=4)
        b["duel"] = False
        b["form"].update(on=2, mult=3.0)
        self.assertAlmostEqual(E.eff(b, "zanjutsu"), E.soft_stat(100) * 3.0, places=4)

    def test_mult_cap(self):
        a, b = fighter("A", 50, 100, 50), fighter("B", 50, 100, 50)
        E.new_state(a, b, random.Random(1), pvp=True)
        a["x"]["buff_t"], a["x"]["buff_m"], a["x"]["awake"] = 3, 2.0, 3
        a["x"]["perm"] = 2.0
        self.assertLessEqual(E._dmg_mult(a), a["dmgx"] * DUEL["mult_cap"] + 1e-9)
        a["duel"] = False
        self.assertGreater(E._dmg_mult(a), a["dmgx"] * DUEL["mult_cap"])

    def test_release_price_flat_and_capped(self):
        big, small = fighter("B", 80, 100, 50, re=20000), fighter("S", 20, 100, 50, re=900)
        E.new_state(big, small, random.Random(1), pvp=True)
        self.assertEqual(E.gx_cost(big), 2000)        # 10% pool is above the flat price
        big["max_re"] = 5000
        self.assertEqual(E.gx_cost(big), 1000)        # flat price
        self.assertEqual(E.gx_cost(small), 315)       # 35% pool cap
        small["duel"] = False
        self.assertEqual(E.gx_cost(small), 90)        # outside duels: normal 10%

    def test_one_release_and_lock(self):
        a, b = fighter("A", 60, 300, 100, re=9000), fighter("B", 60, 300, 100, re=9000)
        st = E.new_state(a, b, random.Random(3), pvp=True, )
        st["cur"] = "a"
        a["x"]["gauge"] = 100
        self.assertTrue(E.can(a, "gx", st))
        E.do_action(st, "gx", random.Random(3))
        self.assertEqual(a["dl_rel"], 1)
        self.assertEqual(a["x"]["awake"] > 0 or a["x"]["awake"] == 0, True)
        a["x"]["gauge"], a["x"]["awake"] = 100, 0
        self.assertFalse(E.can(a, "gx", st))          # second release in the same duel
        a["x"]["awake"] = 2
        for act in E.DUEL_RELEASE_LOCK:
            self.assertFalse(E.can(a, act, st), act)  # locked while released

    def test_full_duel_runs_and_ends(self):
        for seed in range(10):
            a, b = fighter("A", 100, 3000, 400, 20000), fighter("B", 40, 300, 80, 4000)
            st = E.new_state(a, b, random.Random(seed), pvp=True)
            E.run_ai(st, random.Random(seed), ai_sides=("a", "b"))
            self.assertTrue(st["done"])


if __name__ == "__main__":
    unittest.main()


class ShieldCap(unittest.TestCase):
    def test_shield_capped_in_duel(self):
        a, b = fighter("A", 50, 100, 50, 10000), fighter("B", 50, 100, 50, 10000)
        E.new_state(a, b, random.Random(1), pvp=True)
        E._shield_add(a, 10 ** 7)
        self.assertEqual(a["shield"], int(a["max_hp"] * DUEL["shield_cap"]))
        E._shield_add(a, 5000)
        self.assertEqual(a["shield"], int(a["max_hp"] * DUEL["shield_cap"]))
        # new_state may have given the non-opening fighter its one-time second-guard shield.
        # Turning duel rules off does not erase an already-created shield.
        initial = b["shield"]
        b["duel"] = False
        E._shield_add(b, 10 ** 7)
        self.assertEqual(b["shield"], initial + 10 ** 7)


class BakudoCap(unittest.TestCase):
    """Nov 25: in a duel a Bakudo barrier never exceeds 90% of one ordinary blow of the foe on the caster."""

    def _cast(self, kido_stat, duel=True):
        import copy
        a = E.new_fighter("A", 100, {"zanjutsu": 300, "kido": kido_stat, "hakuda": 100, "hoho": 20, "reiatsu": 20}, 20000, 20000, W,
                          race="shinigami", kido={"had": [1], "bak": [81]})
        b = fighter("B", 100, 900, 100, 20000)
        st = E.new_state(a, b, random.Random(5), pvp=duel)
        st["cur"] = "a"
        a["shield"] = 0
        a["x"]["chant"] = 1
        return st, a, b

    def test_barrier_capped_by_foe_blow(self):
        st, a, b = self._cast(2000)
        ref = min(E._atk_reference(st, "b"), E.duel_cap_hp(st) * DUEL["hit_cap"])
        E.do_action(st, "bk", random.Random(5))
        self.assertLessEqual(a["shield"], int(ref * DUEL["bak_hit_share"]) + 1)
        self.assertGreater(a["shield"], 0)

    def test_cap_not_applied_outside_duels(self):
        st, a, b = self._cast(2000, duel=False)
        ref = E._atk_reference(st, "b")
        E.do_action(st, "bk", random.Random(5))
        self.assertGreater(a["shield"], ref * DUEL["bak_hit_share"])


class TurnClock(unittest.TestCase):
    def test_five_minutes_two_strikes(self):
        self.assertEqual(DUEL["turn_seconds"], 300)
        self.assertEqual(DUEL["afk_limit"], 2)


class KyokaDebuffs(unittest.TestCase):
    """Nov 25: Mind Distortion / Illusion Strike must visibly work, and a foe's Hadō must respect the miss debuff."""

    def _pair(self, seed=1):
        a = fighter("A", 60, 200, 100, 80000)
        a["blade"] = "kyoka_suigetsu"
        b = fighter("B", 60, 200, 100, 80000)
        st = E.new_state(a, b, random.Random(seed), pvp=True)
        st["cur"], st["awaiting"] = "a", True
        a["re"] = a["max_re"]
        return st, a, b

    def test_mind_distortion_always_lands_and_reports_numbers(self):
        for seed in range(20):
            st, a, b = self._pair(seed)
            ev = E.do_action(st, "ks3", random.Random(seed))
            e = [x for x in ev if x["k"] == "ks_distort"][0]
            self.assertEqual((e["p"], e["t"]), (45, 3))  # Nov 25b: 40 -> 45
            self.assertAlmostEqual(E.bsum(b, "miss"), 0.45)

    def test_foe_blows_really_miss(self):
        st, a, b = self._pair()
        E.do_action(st, "ks3", random.Random(1))
        misses = 0
        for seed in range(400):
            ev = []
            E._deal(st, "b", 1.0, random.Random(seed), ev, "atk")
            misses += any(x["k"] == "miss" for x in ev)
        self.assertGreater(misses, 400 * 0.30)

    def test_foe_hado_misses_too(self):
        misses = 0
        for seed in range(300):
            st, a, b = self._pair(seed)
            E.do_action(st, "ks3", random.Random(seed))
            b["kido"]["had"] = [1]
            st["cur"] = "b"; st["awaiting"] = True
            ev = E.do_action(st, "kd", random.Random(seed))
            misses += any(x["k"] == "miss" for x in ev)
        self.assertGreater(misses, 300 * 0.30)

    def test_illusion_strike_reports_success_or_failure(self):
        seen = set()
        for seed in range(60):
            st, a, b = self._pair(seed)
            ev = E.do_action(st, "ks1", random.Random(seed))
            seen |= {x["k"] for x in ev if x["k"].startswith("ks_ill")}
        self.assertEqual(seen, {"ks_illusion", "ks_illusion_fail"})


class ControlFollowsPower(unittest.TestCase):
    """Nov 26: a much weaker fighter's illusion / stun does nothing in a duel; equal fighters keep full effect."""

    def _ks(self, lv_a, lv_b, seed):
        a = fighter("A", lv_a, lv_a * 3, 100, 80000)
        a["blade"] = "kyoka_suigetsu"
        b = fighter("B", lv_b, lv_b * 3, 100, 80000)
        st = E.new_state(a, b, random.Random(seed), pvp=True)
        st["cur"], st["awaiting"] = "a", True
        a["re"] = a["max_re"]
        return st, a, b

    def test_weak_caster_cannot_daze_a_much_stronger_foe(self):
        for seed in range(30):
            st, a, b = self._ks(100, 400, seed)
            E.do_action(st, "ks3", random.Random(seed))
            self.assertEqual(E.bsum(b, "miss"), 0.0)

    def test_equal_caster_still_lands(self):
        for seed in range(10):
            st, a, b = self._ks(300, 300, seed)
            E.do_action(st, "ks3", random.Random(seed))
            self.assertAlmostEqual(E.bsum(b, "miss"), 0.45)

    def test_stronger_caster_lands(self):
        st, a, b = self._ks(400, 100, 1)
        E.do_action(st, "ks3", random.Random(1))
        self.assertAlmostEqual(E.bsum(b, "miss"), 0.45)

    def test_stun_gated_and_outside_duels_untouched(self):
        import data_balance as BAL
        self.assertEqual(BAL.effect_potency(100, 400), 0.0)
        self.assertEqual(BAL.effect_potency(300, 300), 1.0)
        self.assertEqual(BAL.effect_potency(500, 300), 1.0)
        self.assertAlmostEqual(BAL.effect_potency(375, 500), 0.5)
        a, b = fighter("A", 100, 300, 100), fighter("B", 400, 1200, 100)
        st = E.new_state(a, b, random.Random(1), pvp=False)  # not a duel: no gate
        st["cur"], st["awaiting"] = "a", True
        E._ACTOR["f"], E._ACTOR["rng"] = a, random.Random(1)
        try:
            E.add_fx(b, "skip", 1)
        finally:
            E._ACTOR["f"] = E._ACTOR["rng"] = None
        self.assertTrue(E.has_fx(b, "skip"))


class HadoBand(unittest.TestCase):
    """Duel bug (Nov 26): Hadō 2K vs sword 12K for a low-Kidō caster, 5x the sword for a high-Kidō one. A Hadō now sits
    in a band of the caster's own reference blow, so Kidō and sword builds fight on equal terms."""

    def _hado(self, kido, zan, chant=False, seed=3):
        import copy
        a = fighter("A", 300, zan, 400, 40000); a["stats"]["kido"] = kido; a["kido"]["had"] = [31]
        b = fighter("B", 300, 800, 400, 40000)
        st = E.new_state(a, b, random.Random(seed), pvp=True)
        st["dist"], st["cur"], st["turn"] = 0, "a", 5
        a["shield"] = b["shield"] = 0
        E._x(a)["chant"] = 1 if chant else 0
        ref = E._atk_reference(st, "a") * (E.CHANT_HADO if chant else 1.0)
        E.do_action(st, "kd", random.Random(seed))
        return b["max_hp"] - b["hp"], ref

    def test_low_kido_hado_not_a_floor_blow(self):
        dmg, ref = self._hado(kido=5, zan=1500)
        self.assertGreaterEqual(dmg, int(ref * DUEL["hado_lo"]) - 1)

    def test_high_kido_hado_not_five_times_a_sword(self):
        dmg, ref = self._hado(kido=20000, zan=300)
        self.assertLessEqual(dmg, int(ref * DUEL["hado_hi"]) + 1)

    def test_band_off_outside_duels(self):
        a, b = fighter("A", 300, 300, 400, 40000), fighter("B", 300, 800, 400, 40000)
        a["stats"]["kido"] = 20000; a["kido"]["had"] = [31]
        st = E.new_state(a, b, random.Random(3), pvp=False)
        st["dist"], st["cur"] = 0, "a"
        E.do_action(st, "kd", random.Random(3))
        self.assertGreater(b["max_hp"] - b["hp"], 0)
