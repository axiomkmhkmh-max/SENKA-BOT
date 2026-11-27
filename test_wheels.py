import _isolate  # noqa: E402  (a clean module cache for this file; restored afterwards)

setUpModule, tearDownModule = _isolate.set_up, _isolate.tear_down

import random
import unittest

from data_wheels import (
    CATEGORIES, RARITY_WEIGHTS, WHEELS, WHEEL_IDS, _WHEEL_LIST,
    can_spin, next_streaks, odds_table, reward_for, resolve_rarity, roll,
    spin_cost, spin_multiplier, wheel_by_id, wheels_in,
)


class WheelData(unittest.TestCase):
    def test_exactly_100_wheels_unique_ids(self):
        self.assertEqual(len(WHEEL_IDS), 100)
        self.assertEqual(len(set(WHEEL_IDS)), 100)

    def test_ten_per_category(self):
        for cat, items in _WHEEL_LIST.items():
            self.assertEqual(len(items), 10, cat)
            self.assertIn(cat, CATEGORIES)

    def test_yamamoto_then_ichigo_are_the_most_expensive(self):
        top = max(WHEELS.values(), key=lambda w: w["base_cost"])
        self.assertEqual(top["id"], "w_yamamoto")
        others = [w["base_cost"] for w in WHEELS.values() if w["id"] not in ("w_ichigo", "w_yamamoto")]
        self.assertLess(max(others), WHEELS["w_ichigo"]["base_cost"])
        self.assertLess(WHEELS["w_ichigo"]["base_cost"], WHEELS["w_yamamoto"]["base_cost"])

    def test_toshiro_is_owner_only(self):
        self.assertTrue(WHEELS["w_hitsugaya"]["owner_only"])
        self.assertEqual(sum(w["owner_only"] for w in WHEELS.values()), 1)


class SpinCost(unittest.TestCase):
    def test_tiers(self):
        self.assertEqual(spin_multiplier(1), 1)
        self.assertEqual(spin_multiplier(10), 1)
        self.assertEqual(spin_multiplier(11), 2)
        self.assertEqual(spin_multiplier(40), 2)
        self.assertEqual(spin_multiplier(41), 4)
        self.assertEqual(spin_multiplier(90), 4)
        self.assertEqual(spin_multiplier(91), 8)
        self.assertEqual(spin_multiplier(5000), 8)

    def test_cost_scales_with_base(self):
        base = WHEELS["w_ichigo"]["base_cost"]
        self.assertEqual(spin_cost("w_ichigo", 1), base)
        self.assertEqual(spin_cost("w_ichigo", 95), base * 8)

    def test_bad_spin_number(self):
        with self.assertRaises(ValueError):
            spin_multiplier(0)


class Access(unittest.TestCase):
    def test_owner_only_wheel(self):
        self.assertTrue(can_spin("w_hitsugaya", 1, 1))
        self.assertFalse(can_spin("w_hitsugaya", 2, 1))

    def test_normal_wheel_open_to_all(self):
        self.assertTrue(can_spin("w_ichigo", 2, 1))

    def test_unknown_wheel(self):
        self.assertFalse(can_spin("nope", 1, 1))
        self.assertIsNone(wheel_by_id("nope"))


class Roll(unittest.TestCase):
    def test_distribution_roughly_matches_weights(self):
        rng = random.Random(42)
        n = 200_000
        counts = {}
        for _ in range(n):
            r = roll(rng)
            counts[r] = counts.get(r, 0) + 1
        total = sum(RARITY_WEIGHTS.values())
        for k, w in RARITY_WEIGHTS.items():
            expected = w / total
            self.assertAlmostEqual(counts.get(k, 0) / n, expected, delta=0.01 if expected > 0.01 else 0.002, msg=k)

    def test_reward_top_tier_uses_theme(self):
        _, fa, en = reward_for("Mythic", "w_ichigo")
        self.assertIn("ایچیگو", fa)
        self.assertIn("Ichigo", en)

    def test_reward_common_is_generic(self):
        _, fa, en = reward_for("Common", "w_ichigo")
        self.assertNotIn("ایچیگو", fa)


class Pity(unittest.TestCase):
    def test_leg_pity_forces_legendary_or_better(self):
        rng = random.Random(1)
        for _ in range(2000):
            r = resolve_rarity(rng, leg_streak=30, myth_streak=0, leg_at=30, myth_at=90)
            self.assertIn(r, ("Legendary", "Mythic", "Legacy"))

    def test_myth_pity_beats_leg_pity(self):
        rng = random.Random(2)
        for _ in range(2000):
            r = resolve_rarity(rng, leg_streak=30, myth_streak=90, leg_at=30, myth_at=90)
            self.assertIn(r, ("Mythic", "Legacy"))

    def test_zero_threshold_disables_pity(self):
        rng = random.Random(3)
        seen = {resolve_rarity(rng, 10_000, 10_000, 0, 0) for _ in range(5000)}
        self.assertIn("Common", seen)

    def test_streaks_reset_on_hit(self):
        self.assertEqual(next_streaks("Common", 5, 5), (6, 6))
        self.assertEqual(next_streaks("Legendary", 5, 5), (0, 6))
        self.assertEqual(next_streaks("Mythic", 5, 5), (0, 0))
        self.assertEqual(next_streaks("Soul Core", 0, 0), (1, 1))

    def test_odds_sum_to_100(self):
        self.assertAlmostEqual(sum(p for _r, p in odds_table()), 100.0, places=6)

    def test_category_lookup(self):
        self.assertEqual(len(wheels_in("captains")), 10)
        self.assertEqual(wheels_in("nope"), [])


class ItemWheels(unittest.TestCase):
    def test_item_wheels_exist_and_have_items_in_every_paying_tier(self):
        from _stubs import import_with_stubs  # service_extras pulls in pymongo / motor: stub them only when they are not installed
        from data_wheels import WHEEL_ITEM_CAT, WHEELS
        from data_items import ALL
        _se = import_with_stubs("service_extras")
        BY_CAT, RARITIES = _se.BY_CAT, _se.RARITIES
        for wid, cat in WHEEL_ITEM_CAT.items():
            self.assertIn(wid, WHEELS)
            pool = [i for r in RARITIES for i in BY_CAT.get(cat, {}).get(r, [])]
            self.assertTrue(pool, cat)
            self.assertTrue(all(i in ALL for i in pool), cat)


if __name__ == "__main__":
    unittest.main()
