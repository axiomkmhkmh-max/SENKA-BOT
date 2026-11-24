"""World boss: a Hadō strike must be announced as a Hadō, never as the race's Hollow Mask / Getsuga cry.
No MongoDB needed. Run: python -m unittest test_boss_kido_call -v"""
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine as E  # noqa: E402

STATS = {"zanjutsu": 10, "kido": 40, "hakuda": 10, "hoho": 10, "reiatsu": 10}


class BossKidoCall(unittest.TestCase):
    def _hit(self, race):
        a = E.new_fighter("A", 100, dict(STATS), 5000, 9000, None, race=race, kido={"had": [1, 4, 31], "bak": []})
        b = E.new_fighter("Boss", 100, dict(STATS), 10 ** 9, 100, None, race="human")
        b["foe"] = "world_boss"
        st = {"a": a, "b": b, "turn": 1, "cur": "a", "first": "a", "done": False, "winner": None}
        return E._do_action(st, "kd", random.Random(3)), a

    def test_hado_event_is_tagged(self):
        for race in ("visored", "shinigami"):
            ev, a = self._hit(race)
            self.assertTrue(any(e.get("k") == "hit" and e.get("kind") == "hado" for e in ev), race)
            self.assertTrue(any(e.get("num") and e.get("spell") for e in ev), race)

    def test_cry_names_the_spell_not_the_mask(self):
        try:
            import handlers_combat as H
        except Exception as ex:  # the handler needs aiogram / the full app; the check above still covers the engine side
            self.skipTest(f"handlers_combat not importable here: {ex}")
        out_en = H._kido_call("en", 31, "Shakkahō")
        out_fa = H._kido_call("fa", 31, "Shakkahō")
        self.assertIn("Hadō 31", out_en)
        self.assertNotIn("Mask", out_en)
        self.assertIn("هادو", out_fa)


if __name__ == "__main__":
    unittest.main()


class PickedSpellNotCastable(unittest.TestCase):
    def _player(self, pick):
        a = E.new_fighter("A", 60, dict(STATS), 5000, 9000, None, race="visored", kido={"had": [1, 4, 31, 96], "bak": []})
        a["kpick"] = {"had": pick}
        return a

    def test_uncastable_pick_falls_back_to_best_castable_hado(self):
        a = self._player(96)                       # 96 is castable bare now (Nov 25) ...
        self.assertTrue(E.can(a, "kd"))
        self.assertEqual(E.best_kido(a, "had"), 96)
        a["re"] = int(a["max_re"] * 0.05)          # ... but with too little reiatsu for the 8% spell the pick is not castable
        self.assertFalse(E.can(a, "kd"))
        self.assertTrue(E.ready_hado(a))
        self.assertEqual(E.best_kido(a, "had"), 31)

    def test_castable_pick_is_kept(self):
        a = self._player(4)
        self.assertTrue(E.ready_hado(a))
        self.assertEqual(E.best_kido(a, "had"), 4)


class WorldBossSourceWiring(unittest.TestCase):
    def test_boss_hit_uses_ready_hado(self):
        src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "service_world.py"), encoding="utf-8").read()
        self.assertIn("E.ready_hado(player)", src)
