"""Summons: a player can get only `gacha_mythic_cap` Mythic results from summons (0 = no limit). Over the limit a Mythic
roll becomes a Legendary. No MongoDB needed: the database layer is faked. Run: python -m unittest test_gacha_mythic_cap -v"""
import asyncio
import os
import sys
import types
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


from _stubs import import_with_stubs  # noqa: E402

E = import_with_stubs("service_economy")

DOC = {}
INV = []


class _Gacha:
    async def find_one(self, flt):
        return dict(DOC) if DOC else None

    async def update_one(self, flt, upd, upsert=False):
        DOC.clear()
        DOC.update(upd["$set"])


class _Rng:
    """Always rolls Mythic (index 5) and takes the character path (random() < 0.6)."""
    def choices(self, population, weights=None, k=1):
        return [5]

    def random(self):
        return 0.0

    def choice(self, seq):
        return seq[0]


def _settings(cap):
    async def gs():
        return {"gacha_cost": 1, "gacha_pity_legendary": 80, "gacha_pity_rare": 10, "gacha_mythic_cap": cap}
    return gs


async def _true(*a, **k):
    return True


async def _no_cooldown(*a, **k):
    return False


async def _noop(*a, **k):
    return None


async def _inv_add(uid, iid, qty=1, force=False):
    INV.append(iid)
    return True


class MythicCapTests(unittest.TestCase):
    def setUp(self):
        DOC.clear()
        INV.clear()
        self._saved = {k: getattr(E, k) for k in ("game_settings", "try_cooldown", "add_coins", "col", "inv_add",
                                                  "bump_quest", "log_event")}
        E.try_cooldown, E.add_coins, E.inv_add, E.bump_quest = _no_cooldown, _true, _inv_add, _noop
        E.log_event = lambda *a, **k: None
        E.col = lambda name: _Gacha()
        self._rng = E.random.Random
        E.random.Random = _Rng

    def tearDown(self):
        E.random.Random = self._rng
        for k, v in self._saved.items():
            setattr(E, k, v)

    def _pull(self, cap, n):
        E.game_settings = _settings(cap)
        res, status = asyncio.run(E.gacha_pull(1, n))
        self.assertEqual(status, "ok")
        return [r["rar"] for r in res]

    def test_mythic_stops_at_the_cap(self):
        rars = self._pull(3, 10)
        self.assertEqual(rars.count("Mythic"), 3)
        self.assertEqual(rars.count("Legendary"), 7)
        self.assertEqual(DOC["mythic"], 3)

    def test_cap_is_for_life_across_pulls(self):
        self._pull(3, 2)
        rars = self._pull(3, 5)
        self.assertEqual(rars.count("Mythic"), 1)
        self.assertEqual(DOC["mythic"], 3)

    def test_zero_means_no_limit(self):
        self.assertEqual(self._pull(0, 6).count("Mythic"), 6)

    def test_existing_mythic_characters_count_from_the_start(self):
        mythic_char = next(c["_id"] for c in E.CHARS if c["rarity"] == "Mythic")
        DOC.update({"user_id": 1, "since_rare": 0, "since_leg": 0, "chars": {mythic_char: 3}, "total": 50})
        self.assertEqual(self._pull(3, 4).count("Mythic"), 0)


if __name__ == "__main__":
    unittest.main()
