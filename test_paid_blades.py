"""Benihime and Katen Kyōkotsu are paid blades: 20,000,000 coins each, bought once, never free."""
import asyncio
import unittest

import test_mentor_trade  # noqa: F401  (stubs motor / pymongo / aiogram when they are missing)
import data_zanpakuto as Z


class PaidBlades(unittest.TestCase):
    def test_benihime_price_and_not_beta(self):
        self.assertEqual(Z.blade_price("benihime"), 20_000_000)
        self.assertNotIn("benihime", Z.BETA_BLADES)
        self.assertEqual(Z.blade_price("zangetsu"), 0)

    def test_not_free_at_any_level(self):
        for lvl in (1, 50, 200):
            self.assertNotIn("benihime", Z.unlocked_blades(lvl))
            self.assertFalse(Z.blade_valid("benihime", lvl))

    def test_owned_and_level_gate(self):
        self.assertIn("benihime", Z.reachable_blades(50))
        self.assertNotIn("benihime", Z.reachable_blades(49))
        self.assertIn("benihime", Z.unlocked_blades(50, ["benihime"]))
        self.assertFalse(Z.blade_valid("benihime", 49, ["benihime"]))  # owning it does not skip the level gate
        self.assertTrue(Z.blade_valid("benihime", 50, ["benihime"]))


class KatenPaid(unittest.TestCase):
    def test_katen_price_and_not_beta(self):
        self.assertEqual(Z.blade_price("katen_kyokotsu"), 20_000_000)
        self.assertNotIn("katen_kyokotsu", Z.BETA_BLADES)

    def test_katen_not_free_at_any_level(self):
        for lvl in (1, 55, 200):
            self.assertNotIn("katen_kyokotsu", Z.unlocked_blades(lvl))
        self.assertIn("katen_kyokotsu", Z.unlocked_blades(55, ["katen_kyokotsu"]))
        self.assertFalse(Z.blade_valid("katen_kyokotsu", 54, ["katen_kyokotsu"]))  # owning it does not skip the level gate


class HitLines(unittest.TestCase):
    def test_blade_technique_hit_has_text_in_both_languages(self):
        """A blade technique's hit event (kind 'bt') used to print the raw key lg_hit_bt with no damage number."""
        import render
        for lang in ("fa", "en"):
            line = render.events_text(lang, [{"k": "hit", "a": "A", "d": "B", "n": 123, "kind": "bt"}])
            self.assertNotIn("lg_hit_bt", line)
            self.assertIn("123" if lang == "en" else "۱۲۳", line)


class BuyFlow(unittest.TestCase):
    def setUp(self):
        import handlers_zanpakuto as H
        self.H = H
        self.ch = {"user_id": 1, "race": "shinigami", "level": 60, "coins": 25_000_000, "zanpakuto": {}}
        self.coins_log = []

        class Res:
            def __init__(s, n):
                s.modified_count = n

        class Col:
            async def update_one(c, q, u):
                z = self.ch["zanpakuto"]
                if "$addToSet" in u:
                    if "benihime" in z.get("owned", []):
                        return Res(0)
                    z.setdefault("owned", []).append("benihime")
                    return Res(1)
                return Res(1)

            async def find_one(c, *a, **k):
                return None

        async def get_char(uid):
            return self.ch

        async def add_coins(uid, n, why=""):
            if n < 0 and self.ch["coins"] < -n:
                return False
            self.ch["coins"] += n
            self.coins_log.append((n, why))
            return True

        async def no_cd(*a, **k):
            return False

        self._saved = (H.col, H.get_char, H.add_coins, H.try_cooldown)
        H.col, H.get_char, H.add_coins, H.try_cooldown = (lambda name: Col()), get_char, add_coins, no_cd
        import znp_lock
        self._lock_col, znp_lock.col = znp_lock.col, (lambda name: Col())

        class Ctx:
            uid, lang = 1, "fa"
            def t(s, k): return k
            chat_type = "private"
        self.ctx = Ctx()

    def tearDown(self):
        self.H.col, self.H.get_char, self.H.add_coins, self.H.try_cooldown = self._saved
        import znp_lock
        znp_lock.col = self._lock_col

    def run_(self, arg):
        return asyncio.new_event_loop().run_until_complete(self.H.blade_buy(self.ctx, arg))

    def test_confirm_screen_does_not_charge(self):
        out = self.run_("benihime")
        self.assertEqual(self.ch["coins"], 25_000_000)
        self.assertNotIn("owned", self.ch["zanpakuto"])
        self.assertIn("ok:benihime", str(out.rows))

    def test_buy_charges_20m_once(self):
        self.run_("ok:benihime")
        self.assertEqual(self.ch["coins"], 5_000_000)
        self.assertEqual(self.ch["zanpakuto"]["owned"], ["benihime"])
        out = self.run_("ok:benihime")  # second tap: refused, not charged again
        self.assertEqual(self.ch["coins"], 5_000_000)
        self.assertTrue(out.alert)

    def test_not_enough_coins(self):
        self.ch["coins"] = 19_999_999
        out = self.run_("ok:benihime")
        self.assertTrue(out.alert)
        self.assertEqual(self.ch["coins"], 19_999_999)
        self.assertNotIn("owned", self.ch["zanpakuto"])

    def test_level_gate(self):
        self.ch["level"] = 49
        out = self.run_("ok:benihime")
        self.assertTrue(out.alert)
        self.assertEqual(self.ch["coins"], 25_000_000)


if __name__ == "__main__":
    unittest.main()
