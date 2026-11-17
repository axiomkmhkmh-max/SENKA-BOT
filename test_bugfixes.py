"""Regression checks for the November bug pass (pure, no MongoDB / Telegram needed)."""
import ast
import glob
import unittest

import engine as E
from data_bleachfx import GAUGE, enemy_sig


def _fighter(race):
    return E.new_fighter("F", 20, {"zanjutsu": 40, "hoho": 30, "kido": 20, "hakuda": 20}, 400, 200,
                         {"attack": 12, "crit": 0.05, "element": "light", "skills": [], "weapon_type": "melee"}, race=race)


class LogEventCalls(unittest.TestCase):
    def test_no_call_passes_a_positional_name_again(self):
        # log_event(kind, uid, text, **extra): passing kind=/uid=/text= as an extra raised TypeError and crashed
        # market listings and group drops after the item had already moved.
        bad = []
        for path in glob.glob("*.py"):
            tree = ast.parse(open(path, encoding="utf-8").read())
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and getattr(node.func, "id", getattr(node.func, "attr", "")) == "log_event":
                    pos = ["kind", "uid", "text"][:len(node.args)]
                    taken = [k.arg for k in node.keywords if k.arg in pos]
                    if taken:
                        bad.append(f"{path}:{node.lineno} {taken}")
        self.assertEqual(bad, [])


class ReleaseAnnouncement(unittest.TestCase):
    def test_every_player_race_hears_it_but_wild_enemies_do_not(self):
        for race in ("shinigami", "hollow", "arrancar", "fullbringer", "quincy", "human", "visored"):
            f, ev = _fighter(race), []
            E._gain(f, GAUGE["full"], ev)
            self.assertTrue(any(e["k"] == "gauge_full" for e in ev), race)
        for race, expected in ((None, False),):
            f, ev = _fighter("human"), []
            f["wild"] = True
            E._gain(f, GAUGE["full"], ev)
            self.assertEqual(any(e["k"] == "gauge_full" for e in ev), expected, race)


class AnimeSignatures(unittest.TestCase):
    def test_arrancar_fire_cero_and_quincy_use_hirenkyaku(self):
        for name in (("سرباز نومروس", "Numeros Soldier"), ("جلاد اکسکیاس", "Exequias Executioner"),
                     ("فراسیون باراگان", "Baraggan's Fracción"), ("اسپادای پریوارون", "Privaron Espada")):
            self.assertEqual(enemy_sig(None, name), "cero", name)
        for name in (("سولدات مهاجم", "Invading Soldat"), ("محافظ شوتس‌اشتافل", "Schutzstaffel Guard"),
                     ("کوئینسی رقیب", "Rival Quincy")):
            self.assertEqual(enemy_sig(None, name), "hiren", name)
        self.assertIsNone(enemy_sig(None, ("زندانی موکن", "Muken Prisoner")))


if __name__ == "__main__":
    unittest.main()
