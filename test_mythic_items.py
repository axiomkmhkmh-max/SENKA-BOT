"""The ten Mythic items (data_mythic.py): one-of-each category gaps, strong, bound, and kept out of random pools."""
import random
import unittest

import data_items as D
from data_crafting import forge_value, player_bonus
from data_mythic import MYTHIC_ITEMS

USABLE = {"hp", "reiatsu", "kido_book", "buff", "pet", "relic", "cosmetic", "mat"}


class MythicItems(unittest.TestCase):
    def test_ten_unique_and_registered(self):
        self.assertEqual(len(MYTHIC_ITEMS), 10)
        self.assertEqual(len({x["_id"] for x in MYTHIC_ITEMS}), 10)
        self.assertEqual(len({x["name_en"] for x in MYTHIC_ITEMS}), 10)
        for x in MYTHIC_ITEMS:
            self.assertIs(D.ALL[x["_id"]], x)
            self.assertEqual(x["rarity"], "Mythic")
            self.assertFalse(x["tradeable"])
            self.assertIn(x["effect"]["type"], USABLE)
            self.assertNotRegex(x["name_fa"] + x["desc_fa"], r"[A-Za-z0-9]")  # Persian text carries no Latin letters or digits

    def test_only_categories_that_had_no_mythic(self):
        cats = {x["category"] for x in MYTHIC_ITEMS}
        self.assertEqual(cats, {"potion", "book", "charm", "egg", "relic", "cosmetic", "material"})
        for c in cats:
            old = [x for x in D.ITEMS if x["category"] == c and x["rarity"] == "Mythic" and not x.get("special")]
            self.assertEqual(old, [], c)

    def test_kept_out_of_every_random_pool(self):
        ids = {x["_id"] for x in MYTHIC_ITEMS}
        self.assertFalse(ids & set(D.BY_RARITY["Mythic"]))
        rng = random.Random(3)
        self.assertEqual(D.pick_shared("Mythic", rng), None)
        for r in D.RARITIES:
            self.assertFalse(ids & set(D._REST_POOL[r]))

    def test_stronger_than_the_best_non_mythic_of_their_kind(self):
        by = {x["_id"]: x for x in MYTHIC_ITEMS}
        best_hp = max(x["effect"]["pct"] for x in D.ITEMS if x["category"] == "potion" and x["effect"]["type"] == "hp" and x["rarity"] != "Mythic")
        self.assertGreater(by["it_m001"]["effect"]["pct"], best_hp)
        for k in ("dmg", "xp"):
            old = max(x["effect"]["v"] for x in D.ITEMS if x["category"] == "relic" and x["effect"]["kind"] == k and x["rarity"] != "Mythic")
            new = max(x["effect"]["v"] for x in MYTHIC_ITEMS if x["category"] == "relic" and x["effect"]["kind"] == k)
            self.assertGreater(new, old, k)
        self.assertEqual(forge_value("Mythic"), 3)

    def test_relic_bonus_applies(self):
        from config import GAME_DEFAULTS
        ch = {"relics": ["it_m007"], "location": "soul_society"}
        b = player_bonus(ch, D.ALL, GAME_DEFAULTS)
        self.assertGreater(b["dmg"], 0.05)

    def test_egg_hatches_top_tier(self):
        self.assertEqual(D.ALL["it_m006"]["effect"]["tier"], 7)


if __name__ == "__main__":
    unittest.main()
