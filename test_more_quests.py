"""The extra quests: unique ids, only goals the game really tracks, both languages, grouped by category.
Run: python -m unittest test_more_quests -v"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_misc import DAILY_POOL, QUEST_BY_ID, QUESTS  # noqa: E402
from i18n import LOCALES  # noqa: E402

TRACKED = {"explore", "battle_win", "market_buy", "market_sell", "boss_hit", "boss_kill", "level", "gacha_pull",
           "dungeon_clear", "pvp_win", "minigame_win", "guild_deposit", "daily_claim"}
CAT_ORDER = ["main", "side", "race", "weapon", "bankai", "guild", "exploration", "legendary", "hidden", "daily", "weekly"]


class QuestTests(unittest.TestCase):
    def test_ids_unique(self):
        ids = [q["_id"] for q in QUESTS]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(QUEST_BY_ID), len(QUESTS))

    def test_only_tracked_goals_and_valid_numbers(self):
        for q in QUESTS:
            self.assertIn(q["goal"], TRACKED, q["_id"])
            self.assertGreater(q["count"], 0)
            self.assertGreater(q["xp"], 0)
            self.assertGreater(q["coins"], 0)

    def test_texts_in_both_languages(self):
        for q in QUESTS:
            for k in ("name_fa", "name_en", "desc_fa", "desc_en"):
                self.assertTrue(q[k], (q["_id"], k))
            self.assertIn("qc_" + q["cat"], LOCALES["fa"], q["cat"])
            self.assertIn("qc_" + q["cat"], LOCALES["en"], q["cat"])
            self.assertFalse(any("a" <= c.lower() <= "z" for c in q["name_fa"] + q["desc_fa"]), q["_id"])

    def test_grouped_by_category(self):
        ranks = [CAT_ORDER.index(q["cat"]) for q in QUESTS]
        self.assertEqual(ranks, sorted(ranks))

    def test_daily_pool_is_wider_and_sane(self):
        self.assertGreaterEqual(len(DAILY_POOL), 10)
        self.assertTrue(all(QUEST_BY_ID[i]["cat"] == "daily" for i in DAILY_POOL))

    def test_bigger_goals_pay_more_within_a_goal_chain(self):
        for goal, lo, hi in (("level", "m_lvl30", "m_lvl80"), ("explore", "s_explore", "e_loot500"), ("boss_kill", "w_boss", "l_legend50")):
            self.assertLess(QUEST_BY_ID[lo]["xp"], QUEST_BY_ID[hi]["xp"], goal)


if __name__ == "__main__":
    unittest.main()
