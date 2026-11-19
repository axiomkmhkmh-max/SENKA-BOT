"""Kidō the Bleach way (data_kido + engine): pick the spell, the incantation, each spell's own effect, cooldowns.
No MongoDB needed. Run: python -m unittest test_kido_system -v"""
import copy
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data_kido as KD  # noqa: E402
import engine as E  # noqa: E402

STATS = {"zanjutsu": 10, "kido": 40, "hakuda": 10, "hoho": 10, "reiatsu": 10}
HADO = [1, 4, 31, 63, 88, 90, 96]
BAK = [1, 61, 63, 81]


def battle(armor_b=0, boss=False):
    a = E.new_fighter("A", 100, dict(STATS), 5000, 9000, None, race="shinigami", kido={"had": list(HADO), "bak": list(BAK)})
    b = E.new_fighter("B", 100, dict(STATS), 10 ** 6, 5000, None, armor=armor_b, race="human")
    if boss:
        b["foe"] = "boss"
    st = E.new_state(a, b, random.Random(1))
    st["cur"] = "a"
    return st


def cast(st, action, seed=7):
    st["cur"] = "a"
    st["awaiting"] = True
    return E.do_action(st, action, random.Random(seed))


class PickAndChant(unittest.TestCase):
    def test_picked_spell_is_the_one_cast(self):
        st = battle()
        ev = cast(st, "kd:31")
        hit = [e for e in ev if e.get("num")][0]
        self.assertEqual((hit["num"], hit["spell"]), (31, "Shakkahō"))
        self.assertTrue(E.has_fx(st["b"], "burn"))          # Shakkahō burns

    def test_without_a_pick_the_best_castable_is_used(self):
        st = battle()
        self.assertEqual(E.best_kido(st["a"], "had"), 90)    # 88 / 90 are cast bare now; 91-99 wait for the incantation
        self.assertEqual(E.best_kido(st["a"], "bak"), 81)

    def test_unknown_or_bad_pick_is_a_plain_attack(self):
        st = battle()
        ev = cast(st, "kd:7")                                # not learned
        self.assertFalse([e for e in ev if e.get("num")])
        self.assertFalse(E.has_fx(st["b"], "burn"))
        self.assertFalse([e for e in cast(battle(), "kd:abc") if e.get("num")])

    def test_high_spells_need_the_chant(self):
        st = battle()
        self.assertTrue(E.kido_castable(st["a"], "had", 90))   # 90 is cast bare
        self.assertFalse(E.kido_castable(st["a"], "had", 96))
        self.assertFalse([e for e in cast(st, "kd:96") if e.get("num")])      # pressing it does nothing special
        cast(st, "ch")
        self.assertTrue(E.kido_castable(st["a"], "had", 96))
        ev = cast(st, "kd:96")
        hit = [e for e in ev if e.get("num")][0]
        self.assertEqual(hit["num"], 96)
        self.assertTrue(hit["chant"])
        self.assertTrue(E.has_fx(st["b"], "burn"))           # Ittō Kasō burns
        self.assertEqual(E._x(st["a"])["chant"], 0)          # the incantation is spent

    def test_unchanted_high_spell_hits_weaker(self):
        a, b = battle(), battle()
        cast(b, "ch")                                        # same spell with the incantation: stronger
        weak = [e for e in cast(a, "kd:63") if e.get("num")][0]
        strong = [e for e in cast(b, "kd:63") if e.get("num")][0]
        self.assertTrue(weak["short"])
        self.assertFalse(strong["short"])
        self.assertLess(weak["n"], strong["n"])

    def test_low_spells_do_not_lose_power_without_the_chant(self):
        self.assertEqual(KD.unchanted_mult(31), 1.0)
        self.assertLess(KD.unchanted_mult(60), 1.0)
        self.assertTrue(KD.needs_chant(91) and not KD.needs_chant(90))
        self.assertFalse(KD.needs_chant(90, "bak"))          # up to 90 is cast bare
        self.assertTrue(KD.needs_chant(99, "bak"))


class Cooldowns(unittest.TestCase):
    def test_no_spell_has_a_cooldown(self):
        self.assertEqual({KD.spell_cd(n) for n in range(1, 100)}, {0})
        st = battle()
        cast(st, "kd:63")
        self.assertTrue(E.kido_castable(st["a"], "had", 63))   # can be cast again right away
        cast(st, "kd:1")
        self.assertTrue(E.kido_castable(st["a"], "had", 1))

    def test_old_saved_fighter_without_kcd_still_works(self):
        st = battle()
        x = E._x(st["a"])
        x.pop("kcd", None)
        x.pop("pick", None)
        self.assertTrue(E.kido_castable(st["a"], "had", 31))
        cast(st, "kd:31")


class SpellEffects(unittest.TestCase):
    def test_byakurai_pierces_armour(self):
        hits = {}
        for pierce in (0.5, 0.0):
            saved = KD.HADO[4]
            KD.HADO[4] = {"pierce": pierce}
            try:
                st = battle(armor_b=400)
                hits[pierce] = [e for e in cast(st, "kd:4") if e.get("num")][0]["n"]
            finally:
                KD.HADO[4] = saved
        self.assertGreater(hits[0.5], hits[0.0])

    def test_rikujokoro_always_binds_sai_often(self):
        st = battle()
        cast(st, "bk:61")
        self.assertTrue(E.has_fx(st["b"], "skip"))
        bound = 0
        for seed in range(200):
            s2 = battle()
            cast(s2, "bk:1", seed)
            bound += E.has_fx(s2["b"], "skip")
        self.assertAlmostEqual(bound / 200, 0.55, delta=0.12)

    def test_sajo_sabaku_binds_two_turns_but_a_boss_only_one(self):
        st = battle()
        cast(st, "bk:63")
        self.assertEqual([x["t"] for x in st["b"]["fx"] if x["k"] == "skip"], [2])
        for seed in range(40):
            s2 = battle(boss=True)
            cast(s2, "bk:63", seed)
            self.assertTrue(all(x["t"] <= 1 for x in s2["b"]["fx"] if x["k"] == "skip"))

    def test_walls_shield_more_and_never_bind(self):
        sai, danku = battle(), battle()
        cast(sai, "bk:1")
        cast(danku, "bk:81")
        self.assertGreater(danku["a"]["shield"], sai["a"]["shield"])
        self.assertFalse(E.has_fx(danku["b"], "skip"))

    def test_sho_is_cheap(self):
        self.assertLess(KD.cost("had", 1, 1000), int(1000 * 1 * KD.HADO_COST_PCT))
        self.assertEqual(KD.cost("had", 31, 1000), int(1000 * 31 * KD.HADO_COST_PCT))
        self.assertEqual(KD.cost("bak", 61, 1000), int(1000 * 61 * KD.BAK_COST_PCT))

    def test_cost_is_a_share_of_max_reiatsu_and_no_level_gate(self):
        for lvl, mx in ((1, 200), (59, 1000)):
            st = battle()
            f = st["a"]; f["level"] = lvl; f["max_re"] = mx; f["re"] = mx
            f["kido"] = {"had": list(range(1, 100)), "bak": list(range(1, 100))}
            f["x"] = {"chant": 0}
            self.assertEqual(E.kido_list(f, "had")[0], 90)
            self.assertEqual(E.kido_list(f, "bak")[0], 90)

    def test_spell_without_enough_reiatsu_is_not_castable(self):
        st = battle()
        st["a"]["re"] = KD.cost("had", 31, st["a"]["max_re"]) - 1
        self.assertFalse(E.kido_castable(st["a"], "had", 31))
        self.assertTrue(E.kido_castable(st["a"], "had", 1))

    def test_unlisted_spells_keep_the_old_behaviour(self):
        p = KD.bakudo_params(23)
        self.assertEqual((p["shield"], p["turns"]), (1.0, 1))
        self.assertAlmostEqual(p["bind"], min(0.6, 0.10 + 0.05 * 23))
        self.assertEqual(KD.hado_params(23), {"mult": 1.0, "pierce": 0.0, "burn": False, "weaken": False, "stun": 0.0, "cost_k": 1.0})

    def test_every_named_spell_is_in_the_name_table(self):
        from data_misc import KIDO_NAMES
        for n in KD.HADO:
            self.assertIn(("had", n), KIDO_NAMES, n)
        for n in KD.BAKUDO:
            self.assertIn(("bak", n), KIDO_NAMES, n)


if __name__ == "__main__":
    unittest.main()
