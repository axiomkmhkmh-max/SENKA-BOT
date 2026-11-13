"""Spirit gauge, Bankai / Resurrección unleash, Hell Butterfly and Hollow Herald (no MongoDB / Telegram needed).

Run:  python -m unittest discover -s tests -v   (from the project root)
"""
import asyncio
import os
import random
import sys
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
for k, v in {"BOT_TOKEN": "1:test", "MONGODB_URI": "mongodb://localhost:1/test", "OWNER_ID": "1",
             "HMAC_SECRET": "x" * 40}.items():
    os.environ.setdefault(k, v)

import engine as E  # noqa: E402
from data_bleachfx import GAUGE, RESOLVE, RESURRECCION  # noqa: E402
from data_items import ALL  # noqa: E402


def fighter(name="A", race="shinigami", ai=False, lvl=20):
    return E.new_fighter(name, lvl, {"zanjutsu": 40, "hoho": 30, "kido": 20, "hakuda": 20}, 400, 200,
                         {"attack": 12, "crit": 0.05, "element": "light", "skills": [], "weapon_type": "melee"},
                         race=race, ai=ai)


class FixedRng(random.Random):
    """random() always returns `value`; uniform() stays the normal random (damage spread)."""

    def __init__(self, value=0.0, seed=1):
        super().__init__(seed)
        self.value = value

    def random(self):
        return self.value


class GaugeEngineTests(unittest.TestCase):
    def setUp(self):
        self._saved = dict(GAUGE)

    def tearDown(self):
        GAUGE.clear()
        GAUGE.update(self._saved)

    def test_hits_fill_both_gauges(self):
        a, b = fighter("A"), fighter("B", race="hollow", ai=True)
        st = E.new_state(a, b, random.Random(3))
        st["cur"], st["awaiting"] = "a", True
        E.do_action(st, "atk", random.Random(3))
        self.assertGreater(a["x"]["gauge"], 0, "the attacker's spirit grows by striking")
        self.assertGreater(b["x"]["gauge"], 0, "the target's spirit grows by being struck")

    def test_gauge_full_announced_once(self):
        f = fighter()
        ev = []
        E._gain(f, GAUGE["full"], ev)
        E._gain(f, 20, ev)  # already full: no second announcement, and it never exceeds the cap
        self.assertEqual([e["k"] for e in ev], ["gauge_full"])
        self.assertEqual(f["x"]["gauge"], GAUGE["full"])

    def test_unleash_needs_full_gauge_and_reiatsu(self):
        f = fighter()
        self.assertFalse(E.can(f, "gx"))
        f["x"]["gauge"] = GAUGE["full"]
        self.assertTrue(E.can(f, "gx"))
        f["re"] = 0
        self.assertFalse(E.can(f, "gx"))

    def test_illegal_unleash_is_not_silently_spent(self):
        # do_action falls back to a plain attack for an illegal action; the release must not fire, nor the gauge drop
        a, b = fighter("A"), fighter("B", race="hollow", ai=True)
        st = E.new_state(a, b, random.Random(2))
        st["cur"], st["awaiting"] = "a", True
        ev = E.do_action(st, "gx", random.Random(2))
        self.assertNotIn("unleash", [e["k"] for e in ev])
        self.assertEqual(a["x"]["awake"], 0)

    def test_unleash_is_a_strike_and_releases_for_its_turns(self):
        a, b = fighter("A"), fighter("B", race="hollow", ai=True)
        st = E.new_state(a, b, random.Random(5))
        st["cur"], st["awaiting"] = "a", True
        a["x"]["gauge"] = GAUGE["full"]
        ev = E.do_action(st, "gx", random.Random(5))
        kinds = [e["k"] for e in ev]
        self.assertIn("unleash", kinds)
        hits = [e for e in ev if e["k"] == "hit"]
        self.assertTrue(hits and hits[0]["kind"] == "hvy", "the release lands a strike, it is not a wasted turn")
        self.assertLess(a["x"]["gauge"], GAUGE["full"], "the release spent the gauge (the strike may refill a little)")
        self.assertEqual(a["x"]["awake"], GAUGE["turns"] + 1)
        self.assertGreater(E._dmg_mult(a), 1.0, "released fighters hit harder")

    def test_release_ends_after_its_turns(self):
        a, b = fighter("A"), fighter("B", race="hollow", ai=True)
        st = E.new_state(a, b, random.Random(9))
        a["x"]["awake"] = 2
        ended = []
        rng = FixedRng(0.99)  # never trigger the Hollow take-over here
        for _ in range(3):
            ev, _ = E.start_turn(st, rng)
            ended += [e for e in ev if e["k"] == "unleash_end"]
            st["awaiting"] = False
        self.assertEqual(len(ended), 1)
        self.assertEqual(a["x"]["awake"], 0)

    def test_hollow_takes_the_wheel_when_released_and_battered(self):
        a, b = fighter("A"), fighter("B", race="hollow", ai=True)
        st = E.new_state(a, b, random.Random(4))
        a["x"]["awake"] = 3
        a["hp"] = int(a["max_hp"] * (GAUGE["hollow_hp"] - 0.05))
        ev, skipped = E.start_turn(st, FixedRng(0.0))  # roll always under hollow_p
        self.assertTrue(skipped)
        self.assertIn("mask_lost", [e["k"] for e in ev])

    def test_no_hollow_take_over_when_healthy(self):
        a, b = fighter("A"), fighter("B", race="hollow", ai=True)
        st = E.new_state(a, b, random.Random(4))
        a["x"]["awake"] = 3
        ev, skipped = E.start_turn(st, FixedRng(0.0))
        self.assertFalse(skipped)
        self.assertNotIn("mask_lost", [e["k"] for e in ev])

    def test_old_battles_get_the_new_fields(self):
        f = fighter()
        f["x"] = {"flash": 0, "charge": 0, "chant": 0, "open": 0, "cd": 0, "res_used": 0, "buff_t": 0, "buff_m": 1.0}
        x = E._x(f)  # a battle saved before the gauge existed must not raise KeyError
        self.assertEqual((x["gauge"], x["awake"]), (0, 0))


class ResurreccionTests(unittest.TestCase):
    def _drop_below_resolve(self, f):
        f["hp"] = int(f["max_hp"] * (RESOLVE["hp"] - 0.05))

    def test_hollow_gets_resurreccion(self):
        f = fighter("H", race="hollow")
        ev = []
        self._drop_below_resolve(f)
        E._maybe_resolve(f, ev)
        self.assertEqual([e["k"] for e in ev], ["resurrect"])
        self.assertEqual(f["x"]["buff_m"], RESURRECCION["dmg"])
        self.assertEqual(f["x"]["buff_t"], RESURRECCION["turns"])

    def test_arrancar_gets_resurreccion(self):
        f = fighter("R", race="arrancar")
        ev = []
        self._drop_below_resolve(f)
        E._maybe_resolve(f, ev)
        self.assertEqual([e["k"] for e in ev], ["resurrect"])

    def test_shinigami_keeps_plain_resolve(self):
        f = fighter("S", race="shinigami")
        ev = []
        self._drop_below_resolve(f)
        E._maybe_resolve(f, ev)
        self.assertEqual([e["k"] for e in ev], ["resolve"])
        self.assertEqual(f["x"]["buff_m"], RESOLVE["dmg"])

    def test_resolve_is_once_per_battle(self):
        f = fighter("S", race="shinigami")
        ev = []
        self._drop_below_resolve(f)
        E._maybe_resolve(f, ev)
        self._drop_below_resolve(f)
        E._maybe_resolve(f, ev)
        self.assertEqual(len(ev), 1)


class RenderTests(unittest.TestCase):
    def test_unleash_line_uses_the_blade_name(self):
        from render import events_text
        blade = next(i for i, it in ALL.items() if it.get("category") == "weapon")
        txt = events_text("en", [{"k": "unleash", "a": "Ichigo", "mv": blade, "r": "shinigami"}])
        self.assertIn("Ichigo", txt)
        self.assertIn(":", txt, "the blade's technique name ('<blade>: <technique>') is shown")

    def test_unleash_line_for_hollow_is_resurreccion(self):
        from render import events_text
        txt = events_text("en", [{"k": "unleash", "a": "Grimmjow", "r": "hollow"}])
        self.assertIn("Resurrección", txt)

    def test_fighter_card_shows_gauge_and_release(self):
        from render import fighter_line
        f = fighter("Ichigo")
        f["x"]["gauge"] = 55
        f["x"]["awake"] = 2
        line = fighter_line("en", f, "🧑")
        self.assertIn("55%", line)
        self.assertIn("👑", line)


class WordReleaseTests(unittest.TestCase):
    """The blade's name, typed mid-fight, releases Bankai when the gauge is full (handlers_combat.battle_word)."""

    class Ctx:
        def __init__(self, uid=7, lang="en"):
            self.uid, self.lang = uid, lang

        def t(self, key, **kw):
            from i18n import t
            return t(self.lang, key, **kw)

    def _run(self, coro):
        return asyncio.run(coro)

    def _patched(self, doc, zanpakuto, pve_result=None):
        import handlers_combat as H
        col_mock = mock.MagicMock()
        col_mock.return_value.find_one = mock.AsyncMock(return_value={"zanpakuto": zanpakuto})
        patches = [
            mock.patch.object(H, "active_pve", mock.AsyncMock(return_value=doc)),
            mock.patch.object(H, "col", col_mock),
            mock.patch.object(H, "battle_panel", mock.AsyncMock(side_effect=lambda ctx, d, ev: H.Out("panel", []))),
        ]
        return H, patches

    def _doc(self, gauge, sid="s1"):
        a, b = fighter("Ichigo"), fighter("Hollow", race="hollow", ai=True)
        a["x"]["gauge"] = gauge
        st = E.new_state(a, b, random.Random(1))
        st["cur"], st["awaiting"] = "a", True
        return {"sid": sid, "state": st, "user_id": 7}

    def _call(self, text, doc, zanpakuto):
        H, patches = self._patched(doc, zanpakuto)
        for p in patches:
            p.start()
        try:
            return self._run(H.battle_word(self.Ctx(), text)), H
        finally:
            for p in patches:
                p.stop()

    def test_plain_text_is_not_a_release(self):
        out, _ = self._call("hello there", self._doc(100), {"blade_id": "x", "shikai": True})
        self.assertIsNone(out)

    def test_no_active_fight_is_not_a_release(self):
        H, patches = self._patched(None, {})
        for p in patches:
            p.start()
        try:
            self.assertIsNone(self._run(H.battle_word(self.Ctx(), "bankai")))
        finally:
            for p in patches:
                p.stop()

    def test_unreleased_blade_is_told_so(self):
        out, _ = self._call("bankai", self._doc(100), {"blade_id": "wp_001", "shikai": False})
        self.assertEqual(out.text, self.Ctx().t("wr_locked"))

    def test_low_gauge_is_explained(self):
        out, _ = self._call("bankai", self._doc(40), {"blade_id": "wp_001", "shikai": True})
        self.assertIn("40/100", out.text)

    def test_full_gauge_unleashes_through_pve_act(self):
        import handlers_combat as H
        doc = self._doc(100)
        pve = mock.AsyncMock(return_value=("ok", doc, ([], None)))  # pve_act is the one that spends the gauge
        H_, patches = self._patched(doc, {"blade_id": "wp_001", "shikai": True})
        patches.append(mock.patch.object(H, "pve_act", pve))
        for p in patches:
            p.start()
        try:
            out = self._run(H.battle_word(self.Ctx(), "bankai"))
        finally:
            for p in patches:
                p.stop()
        pve.assert_awaited_once_with(7, "s1", "gx")
        self.assertEqual(out.text, "panel")


class ButterflyTests(unittest.TestCase):
    class Bot:
        def __init__(self):
            self.sent = []

        async def send_message(self, uid, text):
            self.sent.append((uid, text))

    def test_sent_once_per_cooldown(self):
        import service_butterfly as B
        bot = self.Bot()
        cd = {"n": 0}

        async def fake_cooldown(key, seconds):
            cd["n"] += 1
            return 0 if cd["n"] == 1 else 600  # first call arms it, the second is still cooling down

        async def run():
            with mock.patch.object(B, "game_settings", mock.AsyncMock(return_value={"butterfly_on": 1, "butterfly_cooldown": 1800})), \
                    mock.patch.object(B, "try_cooldown", fake_cooldown):
                first = await B.butterfly(bot, 9, "en", "shikai", blade="<Zabimaru>")
                second = await B.butterfly(bot, 9, "en", "bankai", blade="Zabimaru")
            return first, second
        first, second = asyncio.run(run())
        self.assertTrue(first)
        self.assertFalse(second)
        self.assertEqual(len(bot.sent), 1)
        self.assertIn("&lt;Zabimaru&gt;", bot.sent[0][1], "blade names are escaped for HTML")

    def test_switched_off(self):
        import service_butterfly as B
        bot = self.Bot()

        async def run():
            with mock.patch.object(B, "game_settings", mock.AsyncMock(return_value={"butterfly_on": 0})):
                return await B.butterfly(bot, 9, "fa", "seat")
        self.assertFalse(asyncio.run(run()))
        self.assertEqual(bot.sent, [])

    def test_blocked_user_never_breaks_the_caller(self):
        import service_butterfly as B

        class Blocked(self.Bot):
            async def send_message(self, uid, text):
                raise RuntimeError("bot was blocked by the user")

        async def run():
            with mock.patch.object(B, "game_settings", mock.AsyncMock(return_value={"butterfly_on": 1, "butterfly_cooldown": 1})), \
                    mock.patch.object(B, "try_cooldown", mock.AsyncMock(return_value=0)):
                return await B.butterfly(Blocked(), 9, "en", "seat")
        self.assertFalse(asyncio.run(run()))


class HeraldTests(unittest.TestCase):
    def _due(self, nxt_in, window=600, modified=1, boss_id=None):
        import time as _t
        import service_world as W
        now = int(_t.time())
        ws = {"next_boss_at": now + nxt_in, "boss_id": boss_id}
        col_mock = mock.MagicMock()
        col_mock.return_value.update_one = mock.AsyncMock(return_value=mock.Mock(modified_count=modified))
        with mock.patch.object(W, "get_world", mock.AsyncMock(return_value=(ws, None))), \
                mock.patch.object(W, "col", col_mock):
            return asyncio.run(W.herald_due(window))

    def test_outside_window_is_silent(self):
        self.assertEqual(self._due(3600), 0)

    def test_inside_window_announces_minutes(self):
        self.assertEqual(self._due(540), 9)

    def test_only_once_per_boss_slot(self):
        self.assertEqual(self._due(540, modified=0), 0)

    def test_no_herald_when_a_boss_is_already_alive(self):
        self.assertEqual(self._due(300, boss_id="boss_1"), 0)


class SimulationSmokeTests(unittest.TestCase):
    def test_many_fights_run_clean_and_release_happens(self):
        counts = {"unleash": 0, "errors": 0}
        for i in range(300):
            r = random.Random(i)
            a, b = fighter("A", race="shinigami"), fighter("B", race="hollow", ai=True)
            st = E.new_state(a, b, r)
            try:
                for e in E.run_ai(st, r, ai_sides=("a", "b")):
                    if e["k"] == "unleash":
                        counts["unleash"] += 1
                self.assertTrue(st["done"])
            except Exception:  # pragma: no cover - reported below
                counts["errors"] += 1
        self.assertEqual(counts["errors"], 0)
        self.assertGreater(counts["unleash"], 0)


if __name__ == "__main__":
    unittest.main()
