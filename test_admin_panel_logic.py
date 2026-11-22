import unittest

from admin_panel_logic import (
    adjust_setting, coerce_setting, page_bounds, parse_amount, role_ok, split_id_rest, split_target, to_ascii_digits,
)


class Digits(unittest.TestCase):
    def test_persian_digits_become_ascii(self):
        self.assertEqual(to_ascii_digits("۱۲۳٤"), "1234")
        self.assertEqual(parse_amount("۱,۰۰۰"), 1000)


class SplitIdRest(unittest.TestCase):
    def test_id_and_reason(self):
        self.assertEqual(split_id_rest("123 spam link"), (123, "spam link"))

    def test_id_only(self):
        self.assertEqual(split_id_rest("  42 "), (42, ""))

    def test_at_sign_is_stripped(self):
        self.assertEqual(split_id_rest("@77 x"), (77, "x"))

    def test_name_is_not_an_id(self):
        self.assertEqual(split_id_rest("ruinedbara"), (None, ""))

    def test_empty(self):
        self.assertEqual(split_id_rest(""), (None, ""))


class Amount(unittest.TestCase):
    def test_bounds(self):
        self.assertEqual(parse_amount("5", 1, 10), 5)
        self.assertIsNone(parse_amount("0", 1, 10))
        self.assertIsNone(parse_amount("11", 1, 10))
        self.assertIsNone(parse_amount("-3"))
        self.assertIsNone(parse_amount("abc"))


class Coerce(unittest.TestCase):
    def test_bool_words(self):
        self.assertTrue(coerce_setting(False, "on"))
        self.assertTrue(coerce_setting(False, "روشن"))
        self.assertFalse(coerce_setting(True, "off"))
        with self.assertRaises(ValueError):
            coerce_setting(True, "maybe")

    def test_int_and_float(self):
        self.assertEqual(coerce_setting(10, "25"), 25)
        self.assertEqual(coerce_setting(0.5, "0.75"), 0.75)
        with self.assertRaises(ValueError):
            coerce_setting(10, "ten")


class Adjust(unittest.TestCase):
    def test_toggle(self):
        self.assertEqual(adjust_setting(False, False, "t"), True)
        self.assertEqual(adjust_setting(False, True, "t"), False)

    def test_percent_steps_int(self):
        self.assertEqual(adjust_setting(100, 100, "u"), 110)
        self.assertEqual(adjust_setting(100, 100, "d"), 90)

    def test_small_int_always_moves(self):
        self.assertEqual(adjust_setting(1, 1, "d"), 0)
        self.assertEqual(adjust_setting(1, 1, "u"), 2)

    def test_plus_minus_one(self):
        self.assertEqual(adjust_setting(5, 5, "u1"), 6)
        self.assertEqual(adjust_setting(5, 0, "d1"), 0)  # never below zero

    def test_float_step(self):
        self.assertAlmostEqual(adjust_setting(0.5, 0.5, "u1"), 0.6)

    def test_reset_returns_default(self):
        self.assertEqual(adjust_setting(7, 99, "r"), 7)


class Paging(unittest.TestCase):
    def test_bounds(self):
        self.assertEqual(page_bounds(25, 0, 10), (0, 3, 0))
        self.assertEqual(page_bounds(25, 2, 10), (20, 3, 2))

    def test_clamps_out_of_range(self):
        self.assertEqual(page_bounds(25, 99, 10), (20, 3, 2))
        self.assertEqual(page_bounds(25, -4, 10), (0, 3, 0))

    def test_empty_is_one_page(self):
        self.assertEqual(page_bounds(0, 3, 10), (0, 1, 0))


class Roles(unittest.TestCase):
    def test_unknown_role_falls_back(self):
        valid = {"admin", "moderator", "support", "super"}
        self.assertEqual(role_ok("moderator", valid), "moderator")
        self.assertEqual(role_ok("owner", valid), "admin")
        self.assertEqual(role_ok("", valid), "admin")


class ReplyTargets(unittest.TestCase):
    """Admin answers a panel prompt by replying to the player's message (no id typed)."""

    def test_lone_number_is_the_amount(self):
        self.assertEqual(split_target("500", 777, single_arg=True), (777, "500"))

    def test_item_and_count_with_reply(self):
        self.assertEqual(split_target("soul_sword 2", 777), (777, "soul_sword 2"))

    def test_reason_with_reply(self):
        self.assertEqual(split_target("spam links", 777), (777, "spam links"))

    def test_typed_id_wins_over_reply(self):
        self.assertEqual(split_target("12345678 500", 777, single_arg=True), (12345678, "500"))

    def test_no_reply_and_no_id_is_none(self):
        self.assertEqual(split_target("500", None, single_arg=True), (500, ""))
        self.assertEqual(split_target("hello", None), (None, ""))


if __name__ == "__main__":
    unittest.main()


class SplitTarget(unittest.TestCase):
    def test_no_reply_behaves_like_split_id_rest(self):
        self.assertEqual(split_target("123 500"), (123, "500"))
        self.assertEqual(split_target("spam"), (None, ""))

    def test_reply_with_explicit_id_keeps_the_id(self):
        self.assertEqual(split_target("123 500", reply_id=9, single_arg=True), (123, "500"))

    def test_reply_with_lone_number_is_the_amount(self):
        self.assertEqual(split_target("500", reply_id=9, single_arg=True), (9, "500"))
        self.assertEqual(split_target("۵۰۰", reply_id=9, single_arg=True), (9, "۵۰۰"))

    def test_reply_with_non_id_first_word_uses_replied_player(self):
        self.assertEqual(split_target("sword_id 3", reply_id=9), (9, "sword_id 3"))
        self.assertEqual(split_target("spam link", reply_id=9), (9, "spam link"))

    def test_reply_without_single_arg_lone_number_is_an_id(self):
        self.assertEqual(split_target("77", reply_id=9), (77, ""))
