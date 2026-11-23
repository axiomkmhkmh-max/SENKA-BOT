"""Duel arena card (duel_ui): rendering, battle report, race move names. No database.
Run: python -m unittest test_duel_panel -v"""
import os, random, sys, time, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine as E
import duel_ui as DU
from engine_range import move_label
from test_duel_rules import fighter


def _duel(seed=3):
    a, b = fighter("Ichigo", 80, 500, 100, race="shinigami"), fighter("Grimm", 80, 500, 100, race="arrancar")
    rng = random.Random(seed)
    st = E.new_state(a, b, rng, pvp=True)
    E.run_ai(st, rng, ai_sides=())
    doc = {"sid": "s1", "state": st, "ranked": True, "deadline": int(time.time()) + 30, "timeouts": {"a": 0, "b": 0}}
    return doc, rng


class Panel(unittest.TestCase):
    def test_panel_shows_both_fighters_and_the_turn(self):
        doc, _ = _duel()
        for L in ("fa", "en"):
            txt = DU.panel_text(L, doc, [])
            self.assertIn("Ichigo", txt)
            self.assertIn("Grimm", txt)
            self.assertIn("🎯", txt)
            self.assertLess(len(txt), 4096)

    def test_tally_counts_each_sides_blows(self):
        doc, rng = _duel()
        st = doc["state"]
        for _ in range(400):
            if st["done"]:
                break
            DU.tally(st, E.do_action(st, "atk", rng) + E.run_ai(st, rng, ai_sides=()))
        tl = st["tally"]
        self.assertGreater(tl["a"]["dmg"] + tl["b"]["dmg"], 0)
        for s in ("a", "b"):
            self.assertGreaterEqual(tl[s]["dmg"], tl[s]["best"])

    def test_same_name_blows_are_skipped(self):
        doc, _ = _duel()
        st = doc["state"]
        st["b"]["name"] = st["a"]["name"]
        DU.tally(st, [{"k": "hit", "a": st["a"]["name"], "d": st["a"]["name"], "n": 500}])
        self.assertEqual(st["tally"]["a"]["dmg"] + st["tally"]["b"]["dmg"], 0)

    def test_final_card_names_the_yielder(self):
        doc, _ = _duel()
        st = doc["state"]
        st["done"], st["winner"], st["end"] = True, "a", "ff"
        txt = "\n".join(DU.winner_banner("en", doc, random.Random(1)))
        self.assertIn("Grimm yielded", txt)

    def test_moves_use_the_race_name(self):
        self.assertEqual(move_label("quincy", "shunpo")[1], "Hirenkyaku")
        self.assertEqual(move_label("arrancar", "sonido")[1], "Sonído")
        self.assertEqual(move_label("shinigami", "shunpo")[1], "Shunpo")


if __name__ == "__main__":
    unittest.main()
