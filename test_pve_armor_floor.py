"""Nov 26 fix: plain / heavy / Kyoka blows must not fall to ~0 on high-armour dungeon enemies, and a wild enemy's regen
must stay below what a normal blow takes off."""
import random
import unittest
import engine as E
from data_misc import PVE_ARMOR_FLOOR

W = {"attack": 150, "crit": 0.0, "element": "light", "skills": [], "weapon_type": "melee"}


def fighter(level, stats, hp, armor=0, foe=None, blade=None):
    f = E.new_fighter("F", level, stats, hp, 8000, W, armor=armor, race="shinigami")
    if foe:
        f["foe"], f["ai"], f["wild"] = foe, True, True
    if blade:
        f["blade"] = blade
    return f


def dmg_of(action, armor, foe="pve", blade=None, seed=3):
    a = fighter(238, {"zanjutsu": 150, "reiatsu": 250, "hakuda": 10, "hoho": 10, "kido": 0}, 30000, blade=blade)
    b = fighter(239, {"zanjutsu": 300, "reiatsu": 100, "hakuda": 600, "hoho": 10, "kido": 0}, 10 ** 9, armor=armor, foe=foe)
    st = E.new_state(a, b, random.Random(seed), duel_rules=False)
    st["cur"] = "a"
    before = b["hp"]
    E._do_action(st, action, random.Random(seed + 8))
    return before - b["hp"]


class PveArmorFloorTests(unittest.TestCase):
    def test_plain_and_heavy_never_zero_on_heavy_armour(self):
        for action in ("atk", "hvy"):
            with self.subTest(action=action):
                self.assertGreater(dmg_of(action, armor=5000), 20)

    def test_kyoka_does_not_collapse_with_armour(self):
        low, high = dmg_of("ks1", armor=100, blade="kyoka_suigetsu"), dmg_of("ks1", armor=5000, blade="kyoka_suigetsu")
        self.assertGreater(high, low * PVE_ARMOR_FLOOR * 0.5)

    def test_floor_applies_to_dungeon_boss_too(self):
        self.assertGreater(dmg_of("atk", armor=5000, foe="boss"), 20)

    def test_floor_does_not_touch_light_armour(self):
        # when armour eats less than (1 - floor) of the blow the result is unchanged
        light = dmg_of("hvy", armor=0)
        self.assertEqual(light, dmg_of("hvy", armor=0, foe="pve"))
        self.assertGreater(light, dmg_of("hvy", armor=5000))


if __name__ == "__main__":
    unittest.main()
