"""Race balance and one-time rebase checks (pure logic, no DB). Run: python -m unittest test_race_balance -v"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_races import OLD_RACE_BASE, PREV_RACE_BASE, RACES, STATS, rebased_stats  # noqa: E402
from data_race_rules import RACE_ABILITIES  # noqa: E402


class RaceBalanceTests(unittest.TestCase):
    def test_every_race_has_the_same_base_total(self):
        totals = {k: sum(r["stats"].values()) for k, r in RACES.items()}
        self.assertEqual(set(totals.values()), {40}, totals)

    def test_no_race_is_weakest_or_strongest_by_stat_total(self):
        # Strength must come from level and items, not from the race name.
        self.assertEqual(len({sum(r["stats"].values()) for r in RACES.values()}), 1)

    def test_mods_are_small_and_similar_in_size(self):
        # Each race gets one signature bonus. Keep them within a narrow band.
        for key, race in RACES.items():
            for mod, val in race["mods"].items():
                if mod in ("crit",):
                    self.assertLessEqual(val, 0.05, key)
                elif mod == "pierce":
                    self.assertLessEqual(val, 0.10 + 1e-9, key)
                elif mod == "xp":
                    self.assertLessEqual(val, 1.15, key)
                else:
                    # hp / dmg / def / kido: small in either direction (ability-stat pass: Visored needed a lift, no race far off 1.0)
                    self.assertLessEqual(val, 1.15 + 1e-9, key)
                    self.assertGreaterEqual(val, 0.88 - 1e-9, key)

    def test_shinigami_and_visored_keep_kido_and_bankai_paths(self):
        self.assertTrue({"shinigami", "visored"} <= set(RACE_ABILITIES["bk"]))
        from data_race_rules import race_allows
        for r in ("shinigami", "visored", "quincy", "hollow", "arrancar", "fullbringer", "human"):
            self.assertTrue(race_allows(r, "gx"), r)  # every race has a release since the release rework
        self.assertNotIn("human", RACE_ABILITIES["kd"])
        self.assertNotIn("quincy", RACE_ABILITIES["kd"])

    def test_every_stat_is_non_negative(self):
        for key, race in RACES.items():
            for s in STATS:
                self.assertGreaterEqual(race["stats"][s], 0, (key, s))


class RebaseTests(unittest.TestCase):
    def test_allocated_points_survive_the_rebase(self):
        for race, old in OLD_RACE_BASE.items():
            spent = {"zanjutsu": 5, "kido": 0, "hakuda": 3, "hoho": 0, "reiatsu": 2}
            stats = {k: old[i] + spent[k] for i, k in enumerate(STATS)}
            new = rebased_stats(race, stats)
            for k in STATS:
                self.assertEqual(new[k], RACES[race]["stats"][k] + spent[k], (race, k))

    def test_untouched_character_lands_on_the_new_base(self):
        for race, old in OLD_RACE_BASE.items():
            stats = dict(zip(STATS, old))
            self.assertEqual(rebased_stats(race, stats), {k: RACES[race]["stats"][k] for k in STATS})

    def test_second_pass_keeps_allocated_points(self):
        for race, prev in PREV_RACE_BASE.items():
            spent = {"zanjutsu": 4, "kido": 1, "hakuda": 6, "hoho": 0, "reiatsu": 3}
            stats = {k: prev[i] + spent[k] for i, k in enumerate(STATS)}
            new = rebased_stats(race, stats, old_base=prev)
            for k in STATS:
                self.assertEqual(new[k], RACES[race]["stats"][k] + spent[k], (race, k))

    def test_first_pass_now_targets_the_previous_base(self):
        for race, old in OLD_RACE_BASE.items():
            stats = dict(zip(STATS, old))
            self.assertEqual(rebased_stats(race, stats, new_base=PREV_RACE_BASE[race]), dict(zip(STATS, PREV_RACE_BASE[race])))

    def test_context_multipliers_stay_near_one(self):
        from data_race_rules import RACE_CONTEXT_DMG
        for race, ctxs in RACE_CONTEXT_DMG.items():
            for c, v in ctxs.items():
                # Nov 21: long fights (HP x6) and the ability families widened the band (retuned with balance_sim)
                self.assertTrue(0.50 - 1e-9 <= v <= 2.5 + 1e-9, (race, c, v))

    def test_rebase_is_never_negative(self):
        new = rebased_stats("human", {"zanjutsu": 0, "kido": 0, "hakuda": 0, "hoho": 0, "reiatsu": 0})
        self.assertTrue(all(v >= 0 for v in new.values()))


class CommandRouteTests(unittest.TestCase):
    """Every slash command target must exist in the intent table (this was the /respec and /trade crash)."""

    def test_slash_targets_are_registered_intents(self):
        here = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(here, "handlers_core.py"), encoding="utf-8") as f:
            core = f.read()
        with open(os.path.join(here, "intents.py"), encoding="utf-8") as f:
            intents = f.read()
        block = core[core.index("COMMANDS = {"):core.index("from data_races import LOCATIONS")]
        targets = set(re.findall(r':\s*"([a-z_]+)"', block))
        raw_keys = set(re.findall(r'^    "([a-z_]+)": \(', intents, re.M))
        raw_keys |= set(re.findall(r'RAW\["([a-z_]+)"\]\s*=', intents))
        missing = sorted(t for t in targets if t not in raw_keys)
        self.assertEqual(missing, [], f"slash targets without an intent: {missing}")


class FightTypeBalanceTests(unittest.TestCase):
    """Race damage by fight type (data_race_rules.RACE_CONTEXT_DMG)."""

    def test_every_race_has_every_fight_type(self):
        from data_race_rules import RACE_CONTEXT_DMG
        for race in RACE_CONTEXT_DMG:
            self.assertEqual(set(RACE_CONTEXT_DMG[race]), {"pvp", "hollow", "boss", "pve", "world_boss"}, race)

    def test_multipliers_stay_in_a_sane_band(self):
        from data_race_rules import RACE_CONTEXT_DMG
        for race, table in RACE_CONTEXT_DMG.items():
            for ctx, val in table.items():
                self.assertTrue(0.5 <= val <= 2.5, (race, ctx, val))  # widened for the long fights (Nov 21)

    def test_context_routing(self):
        from data_race_rules import fight_context, ctx_dmg_mult
        self.assertEqual(fight_context({"pvp": True}, {}), "pvp")
        self.assertEqual(fight_context({}, {"foe": "hollow"}), "hollow")
        self.assertEqual(fight_context({}, {"foe": "boss"}), "boss")
        self.assertEqual(fight_context({}, {"foe": "pve"}), "pve")
        self.assertEqual(fight_context({}, {"foe": "world_boss"}), "world_boss")
        self.assertIsNone(fight_context({}, {}))
        self.assertEqual(ctx_dmg_mult("shinigami", None), 1.0)
        self.assertEqual(ctx_dmg_mult("nobody", "pvp"), 1.0)


if __name__ == "__main__":
    unittest.main()
