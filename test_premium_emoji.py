import unittest

import premium_emoji as P


class PremiumEmoji(unittest.TestCase):
    def test_basic_and_variation_selector(self):
        out = P.apply("🔥 ⚔️ ⚔")
        self.assertEqual(out.count("<tg-emoji"), 3)
        self.assertIn('emoji-id="5256047523620995497">🔥</tg-emoji>', out)  # GameEmoji wins over NewsEmoji

    def test_news_only_emoji(self):
        self.assertIn("5456140674028019486", P.apply("⚡️"))

    def test_html_tags_code_and_existing_left_alone(self):
        self.assertEqual(P.apply("<code>🔥</code>"), "<code>🔥</code>")
        self.assertEqual(P.apply("<pre>🔥</pre>"), "<pre>🔥</pre>")
        already = '<tg-emoji emoji-id="1">🔥</tg-emoji>'
        self.assertEqual(P.apply(already), already)
        self.assertIn("<tg-emoji", P.apply("<b>🔥</b>"))
        self.assertTrue(P.apply('<a href="x">🔥</a>').startswith('<a href="x"><tg-emoji'))

    def test_unknown_skin_tone_and_zwj(self):
        self.assertEqual(P.apply("😀 abc"), "😀 abc")
        self.assertEqual(P.apply("👍🏽"), "👍🏽")  # skin-tone variant is not the plain emoji
        self.assertIn("5454136337345037322", P.apply("🧙‍♀️"))
        self.assertIn("5226929552319594190", P.apply("0️⃣"))
        self.assertEqual(P.apply("10"), "10")  # a plain digit is not a keycap

    def test_cap_and_non_text(self):
        self.assertEqual(P.apply("🔥" * 80).count("<tg-emoji"), P.MAX_PER_TEXT)
        self.assertIsNone(P.apply(None))
        self.assertEqual(P.apply(""), "")

    def test_patch_respects_parse_mode(self):
        class SendMessage:
            def __init__(s, text, parse_mode="HTML", entities=None):
                s.text, s.parse_mode, s.entities = text, parse_mode, entities
        m = SendMessage("🔥")
        self.assertEqual(P._patch(m)[1], "🔥")
        self.assertIn("<tg-emoji", m.text)
        m = SendMessage("🔥", parse_mode=None)
        self.assertIsNone(P._patch(m))
        self.assertEqual(m.text, "🔥")
        m = SendMessage("🔥", parse_mode="MarkdownV2")
        self.assertIsNone(P._patch(m))


if __name__ == "__main__":
    unittest.main()


class Dynamic(unittest.TestCase):
    def test_add_many_and_rules(self):
        self.assertEqual(P.add_many({"✅": "111"}), 1)
        self.assertIn('emoji-id="111">✅</tg-emoji>', P.apply("ok ✅"))
        self.assertIn('emoji-id="111"', P.apply("ok ✔"[:0] + "✅\ufe0f"))  # VS16 variant matches too
        self.assertEqual(P.add_many({"✅": "111"}), 0)            # same id: nothing changed
        self.assertEqual(P.add_many({"✅": "222"}, overwrite=False), 0)  # pack import never replaces
        self.assertEqual(P.add_many({"✅": "222"}), 1)            # an emoji sent by the admin replaces
        self.assertEqual(P.add_many({"x": "1", "🎁": "abc"}), 0)  # junk is ignored

    def test_never_maps_letters(self):
        self.assertEqual(P.add_many({"a": "1", "ب": "2", "5": "3", " ": "4", "hello🔥": "5"}), 0)
