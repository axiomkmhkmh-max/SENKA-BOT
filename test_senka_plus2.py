"""SENKA+ Traitor Hunt and Shikai Riddle checks (pure logic). Run: python -m unittest test_senka_plus2 -v"""
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine_mafia as M  # noqa: E402
import engine_riddle as R  # noqa: E402


class TraitorHuntTests(unittest.TestCase):
    def setUp(self):
        self.uids = list(range(1, 9))  # 8 players -> 2 traitors, 1 captain, 5 shinigami
        self.g = M.new_game(self.uids, random.Random(4))

    def roles(self, role):
        return [u for u, p in self.g["players"].items() if p["role"] == role]

    def test_roles_are_dealt(self):
        self.assertEqual(len(self.roles(M.TRAITOR)), 2)
        self.assertEqual(len(self.roles(M.CAPTAIN)), 1)
        self.assertEqual(len(self.roles(M.SHINIGAMI)), 5)

    def test_needs_five_players(self):
        with self.assertRaises(ValueError):
            M.new_game([1, 2, 3, 4])

    def test_traitors_cannot_target_each_other(self):
        t = self.roles(M.TRAITOR)
        with self.assertRaises(ValueError):
            M.traitor_pick(self.g, t[0], t[1])

    def test_night_kill_then_day(self):
        t = self.roles(M.TRAITOR)[0]
        victim = [u for u in self.uids if self.g["players"][u]["role"] != M.TRAITOR][0]
        M.traitor_pick(self.g, t, victim)
        self.assertEqual(M.resolve_night(self.g), victim)
        self.assertFalse(self.g["players"][victim]["alive"])
        self.assertEqual(self.g["phase"], "day")

    def test_captain_learns_if_suspect_is_a_spy(self):
        cap = self.roles(M.CAPTAIN)[0]
        spy = self.roles(M.TRAITOR)[0]
        self.assertTrue(M.captain_check(self.g, cap, spy))

    def test_tie_exiles_nobody_and_strict_majority_does(self):
        M.resolve_night(self.g)  # no kill
        alive = M.alive(self.g)
        a, b = alive[0], alive[1]
        M.vote(self.g, alive[2], a)
        M.vote(self.g, alive[3], b)
        self.assertIsNone(M.resolve_day(self.g))
        M.resolve_night(self.g)
        alive = M.alive(self.g)
        for v in alive[:-1]:
            M.vote(self.g, v, alive[-1])
        self.assertEqual(M.resolve_day(self.g), alive[-1])

    def test_shinigami_win_when_spies_are_gone(self):
        for t in self.roles(M.TRAITOR):
            self.g["players"][t]["alive"] = False
        M._check_win(self.g)
        self.assertEqual(self.g["winner"], M.SHINIGAMI)

    def test_spies_win_when_they_match_the_rest(self):
        for u in self.roles(M.SHINIGAMI):  # only the 2 spies and the Captain are left: 2 >= 1
            self.g["players"][u]["alive"] = False
        M._check_win(self.g)
        self.assertEqual(self.g["winner"], M.TRAITOR)

    def test_dead_players_cannot_vote(self):
        M.resolve_night(self.g)
        dead = self.roles(M.SHINIGAMI)[0]
        self.g["players"][dead]["alive"] = False
        with self.assertRaises(ValueError):
            M.vote(self.g, dead, self.uids[0])


class ShikaiRiddleTests(unittest.TestCase):
    def test_correct_letters_score_and_reveal(self):
        st = R.new_round(random.Random(1), name="Hyorinmaru")
        ev = R.guess(st, 10, "y")
        self.assertEqual(ev["k"], "hit")
        self.assertEqual(st["scores"][10], R.CORRECT_POINTS * 1)
        self.assertIn("y", st["guessed"])
        self.assertIn("y", R.masked(st))

    def test_wrong_letter_costs_a_life(self):
        st = R.new_round(name="Zangetsu")
        before = st["lives"]
        R.guess(st, 1, "q")
        self.assertEqual(st["lives"], before - 1)

    def test_repeat_is_ignored(self):
        st = R.new_round(name="Zangetsu")
        R.guess(st, 1, "z")
        self.assertEqual(R.guess(st, 2, "z")["k"], "repeat")

    def test_full_name_wins_with_bonus(self):
        st = R.new_round(name="Sode no Shirayuki")
        ev = R.guess(st, 7, "sode no shirayuki")
        self.assertEqual(ev["k"], "solved")
        self.assertTrue(st["won"])
        self.assertEqual(st["scores"][7], R.WORD_BONUS)

    def test_running_out_of_lives_loses(self):
        st = R.new_round(name="Benihime")
        for letter in "qwxzjvk":  # 7 lives: seven wrong letters are needed
            if not st["done"]:
                R.guess(st, 3, letter)
        self.assertTrue(st["done"])
        self.assertFalse(st["won"])

    def test_normalization_ignores_macrons_and_case(self):
        self.assertEqual(R.normalize("Hōkō"), "hoko")
        st = R.new_round(name="Hōkō")
        self.assertEqual(R.guess(st, 1, "HOKO")["k"], "solved")

    def test_guesses_after_end_are_ignored(self):
        st = R.new_round(name="Tobiume")
        R.guess(st, 1, "tobiume")
        self.assertEqual(R.guess(st, 2, "a")["k"], "over")


if __name__ == "__main__":
    unittest.main()
