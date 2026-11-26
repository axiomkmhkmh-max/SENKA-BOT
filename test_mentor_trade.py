"""One-to-one trade invitations and master / apprentice, against an in-memory fake DB (no MongoDB, no Telegram).

Run:  python -m unittest test_mentor_trade -v
"""
import asyncio
import sys
import types
import unittest
import uuid
from unittest import mock


def _stub_missing_libs():
    for root in ("motor", "pymongo", "aiogram", "aiohttp"):
        try:
            __import__(root)
            continue
        except ImportError:
            pass
        for name in (root, f"{root}.motor_asyncio", f"{root}.errors", f"{root}.exceptions", f"{root}.types", f"{root}.enums",
                     f"{root}.client", f"{root}.client.default", f"{root}.filters", f"{root}.fsm", f"{root}.utils",
                     f"{root}.utils.keyboard", f"{root}.web"):
            sys.modules.setdefault(name, mock.MagicMock())
    err = sys.modules.get("pymongo.errors")
    if isinstance(err, mock.MagicMock):
        err.DuplicateKeyError = type("DuplicateKeyError", (Exception,), {})
    exc = sys.modules.get("aiogram.exceptions")
    if isinstance(exc, mock.MagicMock):
        for n in ("TelegramAPIError", "TelegramBadRequest", "TelegramForbiddenError", "TelegramRetryAfter"):
            setattr(exc, n, type(n, (Exception,), {}))
    try:
        import bson  # noqa: F401
    except ImportError:
        class ObjectId:
            def __init__(self, v=None):
                self.v = str(v) if v is not None else uuid.uuid4().hex[:24]

            def __eq__(self, o):
                return isinstance(o, ObjectId) and o.v == self.v

            def __hash__(self):
                return hash(self.v)

            def __str__(self):
                return self.v

        m = types.ModuleType("bson")
        m.ObjectId = ObjectId
        sys.modules["bson"] = m


_stub_missing_libs()

from bson import ObjectId  # noqa: E402
from pymongo.errors import DuplicateKeyError  # noqa: E402

import service_economy as SE  # noqa: E402
import service_mentor as M  # noqa: E402
import service_player as SP  # noqa: E402
import service_trade as TR  # noqa: E402
from data_items import ALL  # noqa: E402


# ---- a small in-memory Mongo ---------------------------------------------------------------------------------------
def _getp(doc, path, default=None):
    cur = doc
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def _setp(doc, path, val):
    parts = path.split(".")
    cur = doc
    for p in parts[:-1]:
        cur = cur.setdefault(p, {})
    cur[parts[-1]] = val


def _delp(doc, path):
    parts = path.split(".")
    cur = doc
    for p in parts[:-1]:
        cur = cur.get(p)
        if not isinstance(cur, dict):
            return
    cur.pop(parts[-1], None)


_MISSING = object()


def _match(doc, flt):
    for k, v in flt.items():
        have = _getp(doc, k, _MISSING)
        if isinstance(v, dict) and any(str(x).startswith("$") for x in v):
            for op, arg in v.items():
                if op == "$exists":
                    if (have is not _MISSING) != bool(arg):
                        return False
                elif op == "$ne":
                    if have is not _MISSING and have == arg:
                        return False
                elif op == "$in":
                    if have is _MISSING or have not in arg:
                        return False
                elif have is _MISSING:
                    return False
                elif op == "$gte" and not have >= arg:
                    return False
                elif op == "$gt" and not have > arg:
                    return False
                elif op == "$lte" and not have <= arg:
                    return False
                elif op == "$lt" and not have < arg:
                    return False
        elif isinstance(have, list) and not isinstance(v, list):
            if v not in have:
                return False
        elif have is _MISSING or have != v:
            return False
    return True


class _Cursor:
    def __init__(self, docs):
        self.docs = docs

    def sort(self, key, direction=1):
        self.docs.sort(key=lambda d: _getp(d, key, 0), reverse=direction < 0)
        return self

    def limit(self, n):
        self.docs = self.docs[:n]
        return self

    def __aiter__(self):
        self._it = iter(self.docs)
        return self

    async def __anext__(self):
        try:
            return next(self._it)
        except StopIteration:
            raise StopAsyncIteration


class _Res:
    def __init__(self, matched, modified=None, inserted_id=None):
        self.matched_count, self.modified_count, self.inserted_id = matched, matched if modified is None else modified, inserted_id


class FakeCol:
    def __init__(self):
        self.docs = []

    @staticmethod
    def _apply(doc, upd):
        for p, v in upd.get("$set", {}).items():
            _setp(doc, p, v)
        for p, v in upd.get("$inc", {}).items():
            _setp(doc, p, (_getp(doc, p, 0) or 0) + v)
        for p in upd.get("$unset", {}):
            _delp(doc, p)
        for p, v in upd.get("$push", {}).items():
            _setp(doc, p, list(_getp(doc, p, [])) + [v])
        for p, v in upd.get("$pull", {}).items():
            _setp(doc, p, [x for x in _getp(doc, p, []) if x != v])

    async def insert_one(self, doc):
        doc = dict(doc)
        if "_id" in doc:
            if any(d["_id"] == doc["_id"] for d in self.docs):
                raise DuplicateKeyError("dup")
        else:
            doc["_id"] = ObjectId()
        self.docs.append(doc)
        return _Res(1, inserted_id=doc["_id"])

    async def find_one(self, flt=None, proj=None):
        for d in self.docs:
            if _match(d, flt or {}):
                return dict(d)
        return None

    def find(self, flt=None, proj=None):
        return _Cursor([dict(d) for d in self.docs if _match(d, flt or {})])

    async def update_one(self, flt, upd, upsert=False):
        for d in self.docs:
            if _match(d, flt):
                self._apply(d, upd)
                return _Res(1)
        if upsert:
            doc = {k: v for k, v in flt.items() if not isinstance(v, dict)}
            for p, v in upd.get("$setOnInsert", {}).items():
                _setp(doc, p, v)
            self._apply(doc, upd)
            doc.setdefault("_id", ObjectId())
            self.docs.append(doc)
            return _Res(0, 1)
        return _Res(0)

    async def find_one_and_update(self, flt, upd, upsert=False, return_document=None):
        for d in self.docs:
            if _match(d, flt):
                before = dict(d)
                self._apply(d, upd)
                return before
        return None

    async def delete_one(self, flt):
        for i, d in enumerate(self.docs):
            if _match(d, flt):
                del self.docs[i]
                return _Res(1)
        return _Res(0)


class FakeDB:
    def __init__(self):
        self.cols = {}

    def __call__(self, name):
        return self.cols.setdefault(name, FakeCol())


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


SETTINGS = {"new_acct_minutes": 0, "mentor_xp_pct": 3.0}


async def _settings(force=False):
    return dict(SETTINGS)


def _char(uid, level, name=None, coins=0, race="shinigami", location="rukongai"):
    return {"user_id": uid, "level": level, "name": name or f"P{uid}", "name_key": (name or f"P{uid}").casefold(), "race": race,
            "location": location, "coins": coins, "created_at": 0, "xp": 0, "stats": {}}


class Base(unittest.TestCase):
    def setUp(self):
        self.db = FakeDB()
        self.patches = []
        for mod in (TR, M, SP, SE):
            self.patches.append(mock.patch.object(mod, "col", self.db))
        for mod in (TR, M, SP):
            self.patches.append(mock.patch.object(mod, "game_settings", _settings))
        self.add_xp = mock.AsyncMock(return_value=(None, 0, 0))
        self.patches.append(mock.patch.object(M, "add_xp", self.add_xp))
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def char(self, uid, level, **kw):
        self.db("characters").docs.append(_char(uid, level, **kw))

    async def inv(self, uid):
        return (await SE.inv_get(uid))["items"]


def _tradeable_item():
    return next(i for i, it in sorted(ALL.items()) if it.get("tradeable") and it.get("category") == "potion")


# ---- trade ---------------------------------------------------------------------------------------------------------
class PairTradeTests(Base):
    def test_invitation_does_not_lock_the_invitee(self):
        async def go():
            self.char(1, 20)
            self.char(2, 20)
            tid, err = await TR.open_pair(1, 2)
            self.assertIsNone(err)
            self.assertIsNotNone(await TR.busy_session(1))      # the inviter waits
            self.assertIsNone(await TR.busy_session(2))         # the invitee is free to do anything else
            self.assertEqual([str(d["_id"]) for d in await TR.invites_for(2)], [tid])
            self.assertEqual(await TR.invites_for(1), [])
        run(go())

    def test_table_is_closed_until_accepted(self):
        async def go():
            self.char(1, 20)
            self.char(2, 20)
            tid, _ = await TR.open_pair(1, 2)
            item = _tradeable_item()
            await SE.inv_add(1, item, 2)
            self.assertEqual(await TR.add_item(tid, 1, item), "pending")
            self.assertEqual(await TR.set_coins(tid, 1, 5), "pending")
            self.assertEqual(await TR.confirm(tid, 1, 0), "pending")
        run(go())

    def test_only_the_invitee_can_accept(self):
        async def go():
            self.char(1, 20)
            self.char(2, 20)
            self.char(3, 20)
            tid, _ = await TR.open_pair(1, 2)
            self.assertEqual(await TR.accept_pair(tid, 1), "closed")
            self.assertEqual(await TR.accept_pair(tid, 3), "closed")
            self.assertEqual(await TR.accept_pair(tid, 2), "ok")
            self.assertIsNotNone(await TR.busy_session(2))      # now it locks both
            self.assertEqual(await TR.accept_pair(tid, 2), "closed")  # and a second press does nothing
        run(go())

    def test_accept_refused_when_invitee_is_busy(self):
        async def go():
            for u in (1, 2, 3):
                self.char(u, 20)
            tid, _ = await TR.open_pair(1, 2)
            other, err = await TR.open_pair(3, 2)               # a second invitation to the same player is allowed
            self.assertIsNone(err)
            self.assertEqual(await TR.accept_pair(other, 2), "ok")
            self.assertEqual(await TR.accept_pair(tid, 2), "busy")
        run(go())

    def test_expired_invitation_dies(self):
        async def go():
            self.char(1, 20)
            self.char(2, 20)
            tid, _ = await TR.open_pair(1, 2)
            self.db("trades").docs[0]["created_at"] -= TR.PENDING_TTL + 5
            self.assertEqual(await TR.accept_pair(tid, 2), "closed")
            self.assertIsNone(await TR.busy_session(1))         # and the inviter is free again
        run(go())

    def test_cannot_invite_yourself_or_a_low_level(self):
        async def go():
            self.char(1, 20)
            self.char(2, 5)
            self.assertEqual((await TR.open_pair(1, 1))[1], "self")
            self.assertEqual((await TR.open_pair(1, 2))[1], "other_level")
            self.assertEqual((await TR.open_pair(1, 99))[1], "other_noreg")
        run(go())

    def test_full_trade_swaps_items_and_coins(self):
        async def go():
            self.char(1, 20, coins=1000)
            self.char(2, 20, coins=1000)
            item = _tradeable_item()
            await SE.inv_add(1, item, 3)
            tid, _ = await TR.open_pair(1, 2)
            self.assertEqual(await TR.accept_pair(tid, 2), "ok")
            self.assertEqual(await TR.add_item(tid, 1, item), "ok")
            self.assertEqual(await TR.add_item(tid, 1, item), "ok")
            self.assertEqual(await TR.set_coins(tid, 2, 500), "ok")
            rev = (await TR.get_session(tid, 1))["rev"]
            self.assertEqual(await TR.confirm(tid, 1, rev), "waiting")
            self.assertEqual(await TR.confirm(tid, 2, rev), "done")
            self.assertEqual((await self.inv(1)).get(item, 0), 1)
            self.assertEqual((await self.inv(2)).get(item, 0), 2)
            chars = {c["user_id"]: c["coins"] for c in self.db("characters").docs}
            self.assertEqual(chars, {1: 1500, 2: 500})
            self.assertEqual(len(self.db("trade_log").docs), 1)
        run(go())

    def test_find_partner_by_id_and_name(self):
        async def go():
            self.char(7, 20, name="Ichigo")
            self.assertEqual(await TR.find_partner("7"), 7)
            self.assertEqual(await TR.find_partner("  ichigo "), 7)
            self.assertIsNone(await TR.find_partner("nobody"))
            self.assertIsNone(await TR.find_partner("99"))
            self.assertIsNone(await TR.find_partner(""))
        run(go())


# ---- master and apprentice -----------------------------------------------------------------------------------------
class MentorTests(Base):
    def test_gift_books_are_treatises_and_memoirs(self):
        ids = M.gift_ids()
        self.assertEqual(len(ids), 22)
        for i in ids:
            self.assertTrue(ALL[i]["name_fa"].startswith(("رساله", "خاطرات")), ALL[i]["name_fa"])
            self.assertEqual(ALL[i]["category"], "book")
        manual = next(i for i, it in ALL.items() if it.get("category") == "book" and it["name_fa"].startswith("راهنمای"))
        self.assertFalse(M.is_gift(manual))

    def test_request_rules(self):
        async def go():
            self.char(1, 10)    # apprentice
            self.char(2, 25)    # gap 15: fine
            self.char(3, 15)    # below the master minimum
            self.char(4, 18)    # below the master minimum
            self.char(5, 3)     # too weak to be an apprentice
            self.char(8, 16)    # gap 9 to master 2: refused
            self.assertEqual(await M.request_master(1, 1), "self")
            self.assertEqual(await M.request_master(1, 99), "unknown")
            self.assertEqual(await M.request_master(1, 3), "master_low")
            self.assertEqual(await M.request_master(1, 4), "master_low")
            self.assertEqual(await M.request_master(8, 2), "gap")
            self.assertEqual(await M.request_master(5, 2), "app_low")
            self.assertEqual(await M.request_master(1, 2), "ok")
            self.assertEqual(await M.request_master(1, 2), "pending")
            self.assertEqual([r["_id"] for r in await M.requests_for(2)], [1])
            self.assertEqual(await M.cancel_request(1), 2)
            self.assertEqual(await M.requests_for(2), [])
        run(go())

    def test_master_must_reach_the_minimum_level(self):
        async def go():
            self.char(1, 5)
            self.char(2, 19)
            self.assertEqual(await M.request_master(1, 2), "master_low")
        run(go())

    def test_accept_creates_the_bond(self):
        async def go():
            self.char(1, 10)
            self.char(2, 30)
            self.assertEqual(await M.accept(2, 1), "gone")        # nothing was asked
            await M.request_master(1, 2)
            self.assertEqual(await M.accept(2, 1), "ok")
            self.assertEqual((await SP.get_char(1))["mentor"], 2)
            self.assertEqual((await M.mentorship_of(1))["master"], 2)
            self.assertEqual(await M.requests_for(2), [])
            self.assertEqual(await M.request_master(1, 2), "has_master")
        run(go())

    def test_no_chains_and_a_cap_of_three(self):
        async def go():
            self.char(10, 40)                       # the master
            self.char(11, 12)
            self.char(12, 12)
            self.char(13, 12)
            self.char(14, 12)
            self.char(20, 28)                       # an apprentice of 10 that is stronger than the others
            for a in (11, 12, 13):
                self.assertEqual(await M.request_master(a, 10), "ok")
                self.assertEqual(await M.accept(10, a), "ok")
            self.assertEqual(await M.request_master(14, 10), "full")
            # a master cannot become an apprentice, and an apprentice cannot become a master
            self.char(50, 45)
            self.assertEqual(await M.request_master(10, 50), "app_is_master")
            self.assertEqual(await M.request_master(20, 11), "master_is_apprentice")
            self.assertEqual(await M.request_master(14, 11), "master_is_apprentice")
        run(go())

    def test_xp_cut_is_extra_and_small(self):
        async def go():
            self.char(1, 10)   # apprentice
            self.char(2, 30)   # master: the one who earned the XP
            await M.request_master(1, 2)
            await M.accept(2, 1)
            res = await M.share_to_apprentices(2, 200)
            self.assertEqual(res, {"xp": 6, "n": 1, "graduated": []})   # 3% of 200, paid to the apprentice
            self.add_xp.assert_awaited_once_with(1, 6, "mentor", apply_rate=False)
            self.assertEqual((await M.mentorship_of(1))["xp_total"], 6)
            self.add_xp.reset_mock()
            res = await M.share_to_apprentices(2, 20)                   # 3% of 20 rounds to nothing: no free XP
            self.assertEqual(res["xp"], 0)
            self.add_xp.assert_not_awaited()
        run(go())

    def test_xp_cut_follows_the_live_setting(self):
        async def go():
            self.char(1, 10)
            self.char(2, 30)
            await M.request_master(1, 2)
            await M.accept(2, 1)
            with mock.patch.dict(SETTINGS, {"mentor_xp_pct": 10}):
                self.assertEqual((await M.share_to_apprentices(2, 200))["xp"], 20)
            with mock.patch.dict(SETTINGS, {"mentor_xp_pct": 0}):
                self.assertEqual((await M.share_to_apprentices(2, 200))["xp"], 0)
        run(go())

    def test_graduation_when_the_apprentice_catches_up(self):
        async def go():
            self.char(1, 10)
            self.char(2, 30)
            await M.request_master(1, 2)
            await M.accept(2, 1)
            self.db("characters").docs[0]["level"] = 30
            res = await M.share_to_apprentices(2, 100)
            self.assertEqual(res["graduated"], [1])
            self.assertIsNone(await M.mentorship_of(1))
            self.assertNotIn("mentor", await SP.get_char(1))
        run(go())

    def test_stale_marker_is_cleared(self):
        async def go():
            self.char(1, 10)
            self.char(2, 30)
            self.db("characters").docs[1]["apps"] = 1               # the master's marker says "has apprentices" but no bond exists
            res = await M.share_to_apprentices(2, 100)
            self.assertEqual(res["xp"], 0)
            self.assertNotIn("apps", await SP.get_char(2))
            self.add_xp.assert_not_awaited()
        run(go())

    def test_leaving_ends_the_bond(self):
        async def go():
            self.char(1, 10)
            self.char(2, 30)
            await M.request_master(1, 2)
            await M.accept(2, 1)
            self.assertEqual(await M.end(1), 2)
            self.assertIsNone(await M.mentorship_of(1))
            self.assertNotIn("mentor", await SP.get_char(1))
            self.assertIsNone(await M.end(1))
        run(go())

    def test_gifts(self):
        async def go():
            self.char(1, 10)
            self.char(2, 30)
            self.char(3, 12)
            await M.request_master(1, 2)
            await M.accept(2, 1)
            book = M.gift_ids()[0]
            other = _tradeable_item()
            await SE.inv_add(2, book, 12)
            await SE.inv_add(2, other, 1)
            self.assertEqual(await M.gift(2, 3, book), "notmine")      # not their apprentice
            self.assertEqual(await M.gift(2, 1, other), "notgift")     # only treatises and memoirs
            self.assertEqual(await M.gift(2, 1, M.gift_ids()[1]), "missing")
            for _ in range(M.GIFT_PER_DAY):
                self.assertEqual(await M.gift(2, 1, book), "ok")
            self.assertEqual(await M.gift(2, 1, book), "limit")        # the daily cap
            self.assertEqual((await self.inv(1))[book], M.GIFT_PER_DAY)
            self.assertEqual((await self.inv(2))[book], 2)
            self.assertEqual([(i, q) for i, q in await M.giftable(2)], [(book, 2)])
        run(go())

    def test_a_full_bag_gets_the_book_back(self):
        async def go():
            self.char(1, 10)
            self.char(2, 30)
            await M.request_master(1, 2)
            await M.accept(2, 1)
            book = M.gift_ids()[0]
            await SE.inv_add(2, book, 1)
            inv = await SE.inv_get(1)
            self.db("inventories").docs[[d["user_id"] for d in self.db("inventories").docs].index(1)]["capacity"] = 0
            self.assertEqual(await M.gift(2, 1, book), "full")
            self.assertEqual((await self.inv(2))[book], 1)             # nothing was lost
            self.assertEqual((await M.mentorship_of(1)).get("gift_n", 0), 0)
        run(go())

    def test_find_masters_lists_free_stronger_players(self):
        async def go():
            self.char(1, 10)
            self.char(2, 30)
            self.char(3, 21)          # gap 11: ok
            self.char(4, 15)          # too close
            self.char(5, 19)          # below the master minimum
            ch = await SP.get_char(1)
            self.assertEqual([c["user_id"] for c in await M.find_masters(ch)], [3, 2])
        run(go())


if __name__ == "__main__":
    unittest.main()
