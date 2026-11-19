"""Master and apprentice (استاد و شاگرد).

A weaker player asks a stronger one to be their master; the request lands in the master's panel. Once the master
accepts:
- the apprentice earns a small extra bonus (`mentor_xp_pct`, default 3%) of the XP they win in every battle and
  dungeon fight. The cut is EXTRA: the apprentice's own XP is never reduced;
- the master can hand their apprentices the Treatise (رساله) and Memoir (خاطرات) books from the master panel.

Rules (all constants below): the master needs MENTOR_MIN_LEVEL and must be at least MENTOR_GAP levels above the
apprentice; a master has at most MAX_APPRENTICES apprentices; an apprentice has exactly one master; nobody is a
master and an apprentice at the same time (no chains). The bond ends when either side leaves, or by itself when
the apprentice catches up with the master ("graduates").

Data: `mentorships` (_id = the apprentice's user id, so one master per apprentice is enforced by the database;
fields master, since, xp_total, gift_day, gift_n), `mentor_requests` (_id = the apprentice, one open request each,
dies after REQUEST_TTL). The apprentice's character carries `mentor` (the master's id) so the XP hook costs no query
for the (many) players who have none.
"""
import logging
import time
from datetime import datetime, timedelta, timezone

from pymongo.errors import DuplicateKeyError

from data_items import ALL
from database import col, game_settings
from service_economy import inv_add, inv_get, inv_remove
from service_player import add_xp, get_char, today
from service_worldcore import is_new_account

log = logging.getLogger("senka.mentor")

MENTOR_MIN_LEVEL = 20        # to take apprentices
MENTOR_GAP = 10              # the master must be at least this many levels above the apprentice
APPRENTICE_MIN_LEVEL = 5
MAX_APPRENTICES = 3
REQUEST_TTL = 3 * 24 * 3600
GIFT_PER_DAY = 10            # books a master can give ONE apprentice per day
XP_PCT_DEFAULT = 3.0         # percent of the apprentice's fight XP; live-tunable through the game setting `mentor_xp_pct`


def gift_ids() -> list:
    """The books a master may give: every Treatise (رساله) and Memoir (خاطرات) book, in a stable order."""
    return sorted(i for i, it in ALL.items()
                  if it.get("category") == "book" and it.get("tradeable")
                  and str(it.get("name_fa", "")).startswith(("رساله", "خاطرات")))


_GIFTS: set = set()


def is_gift(item_id: str) -> bool:
    if not _GIFTS:
        _GIFTS.update(gift_ids())
    return item_id in _GIFTS


# ---- lookups ---------------------------------------------------------------------------------------------------------
async def mentorship_of(app_uid: int):
    return await col("mentorships").find_one({"_id": int(app_uid)})


async def apprentices_of(master: int) -> list:
    docs = [d async for d in col("mentorships").find({"master": int(master)})]
    return sorted(docs, key=lambda d: int(d.get("since", 0)))


async def apprentice_count(master: int) -> int:
    return len([d async for d in col("mentorships").find({"master": int(master)})])


async def open_request(app_uid: int):
    doc = await col("mentor_requests").find_one({"_id": int(app_uid)})
    if doc and time.time() - int(doc.get("at", 0)) > REQUEST_TTL:
        await col("mentor_requests").delete_one({"_id": int(app_uid)})
        return None
    return doc


async def requests_for(master: int) -> list:
    now = time.time()
    docs = [d async for d in col("mentor_requests").find({"master": int(master)})]
    return sorted([d for d in docs if now - int(d.get("at", 0)) <= REQUEST_TTL], key=lambda d: -int(d.get("at", 0)))


async def xp_pct() -> float:
    st = await game_settings()
    try:
        return max(0.0, float(st.get("mentor_xp_pct", XP_PCT_DEFAULT)))
    except (TypeError, ValueError):
        return XP_PCT_DEFAULT


async def find_masters(app_ch: dict, limit: int = 8) -> list:
    """Stronger players who could take this apprentice: level high enough, a free slot, not apprentices themselves.
    Closest above the apprentice first (the most natural teacher)."""
    floor = max(MENTOR_MIN_LEVEL, int(app_ch["level"]) + MENTOR_GAP)
    cands = [d async for d in col("characters").find({"level": {"$gte": floor}, "user_id": {"$ne": app_ch["user_id"]}},
                                                      {"user_id": 1, "name": 1, "level": 1, "race": 1, "mentor": 1})]
    cands = sorted([c for c in cands if not c.get("mentor")], key=lambda c: int(c["level"]))
    out = []
    for c in cands:
        if await apprentice_count(c["user_id"]) < MAX_APPRENTICES:
            out.append(c)
            if len(out) >= limit:
                break
    return out


# ---- request / accept ------------------------------------------------------------------------------------------------
async def _check_pair(app_ch: dict, master_ch: dict, st: dict):
    """The rules that must hold both when asking and when accepting. -> error code or None."""
    if app_ch["user_id"] == master_ch["user_id"]:
        return "self"
    if app_ch.get("mentor"):
        return "has_master"
    if master_ch.get("mentor"):
        return "master_is_apprentice"
    if await apprentice_count(app_ch["user_id"]):
        return "app_is_master"
    if int(app_ch["level"]) < APPRENTICE_MIN_LEVEL:
        return "app_low"
    if is_new_account(app_ch, st) or is_new_account(master_ch, st):
        return "new"
    if int(master_ch["level"]) < MENTOR_MIN_LEVEL:
        return "master_low"
    if int(master_ch["level"]) - int(app_ch["level"]) < MENTOR_GAP:
        return "gap"
    return None


async def request_master(app_uid: int, master_uid: int):
    """An apprentice asks a stronger player. -> 'ok' or an error code."""
    app_ch, master_ch = await get_char(app_uid), await get_char(master_uid)
    if not app_ch:
        return "noreg"
    if not master_ch:
        return "unknown"
    st = await game_settings()
    err = await _check_pair(app_ch, master_ch, st)
    if err:
        return err
    if await apprentice_count(master_uid) >= MAX_APPRENTICES:
        return "full"
    if await open_request(app_uid):
        return "pending"
    try:
        await col("mentor_requests").insert_one({"_id": int(app_uid), "master": int(master_uid), "at": int(time.time()),
                                                  "expire_at": datetime.now(timezone.utc) + timedelta(seconds=REQUEST_TTL + 3600)})
    except DuplicateKeyError:
        return "pending"
    return "ok"


async def cancel_request(app_uid: int):
    """-> the master the request was for, or None."""
    doc = await col("mentor_requests").find_one({"_id": int(app_uid)})
    if not doc:
        return None
    await col("mentor_requests").delete_one({"_id": int(app_uid)})
    return int(doc["master"])


async def decline(master_uid: int, app_uid: int) -> bool:
    doc = await col("mentor_requests").find_one({"_id": int(app_uid), "master": int(master_uid)})
    if not doc:
        return False
    await col("mentor_requests").delete_one({"_id": int(app_uid)})
    return True


async def accept(master_uid: int, app_uid: int) -> str:
    """The master accepts a waiting request. -> 'ok' or an error code ('gone' when there is no such request)."""
    req = await col("mentor_requests").find_one({"_id": int(app_uid), "master": int(master_uid)})
    if not req or time.time() - int(req.get("at", 0)) > REQUEST_TTL:
        return "gone"
    app_ch, master_ch = await get_char(app_uid), await get_char(master_uid)
    if not app_ch or not master_ch:
        return "gone"
    st = await game_settings()
    err = await _check_pair(app_ch, master_ch, st)  # levels may have changed since the request
    if err:
        await col("mentor_requests").delete_one({"_id": int(app_uid)})
        return err
    try:
        await col("mentorships").insert_one({"_id": int(app_uid), "master": int(master_uid), "since": int(time.time()),
                                              "xp_total": 0, "gift_day": "", "gift_n": 0})
    except DuplicateKeyError:
        await col("mentor_requests").delete_one({"_id": int(app_uid)})
        return "has_master"
    if await apprentice_count(master_uid) > MAX_APPRENTICES:  # two accepts raced: the later one gives way
        await col("mentorships").delete_one({"_id": int(app_uid)})
        return "full"
    await col("characters").update_one({"user_id": int(app_uid)}, {"$set": {"mentor": int(master_uid)}})
    await col("mentor_requests").delete_one({"_id": int(app_uid)})
    return "ok"


async def end(app_uid: int):
    """Break the bond (either side leaving, or graduation). -> the master's id, or None when there was none."""
    doc = await col("mentorships").find_one({"_id": int(app_uid)})
    await col("characters").update_one({"user_id": int(app_uid)}, {"$unset": {"mentor": ""}})
    if not doc:
        return None
    await col("mentorships").delete_one({"_id": int(app_uid)})
    return int(doc["master"])


# ---- the XP cut ------------------------------------------------------------------------------------------------------
async def share_xp(app_uid: int, master_uid: int, got: int, app_ch: dict = None) -> dict:
    """Called after an apprentice wins a battle / dungeon fight and earned `got` XP: the APPRENTICE gets a small mentoring bonus on top.
    -> {"xp": the bonus the apprentice got, "graduated": bool}. Never raises into the fight (the caller also guards it)."""
    res = {"xp": 0, "graduated": False}
    bonus = int(int(got or 0) * await xp_pct() / 100.0)
    doc = await col("mentorships").find_one({"_id": int(app_uid), "master": int(master_uid)})
    if not doc:  # a stale `mentor` marker: clear it so the fight path stops asking
        await col("characters").update_one({"user_id": int(app_uid), "mentor": int(master_uid)}, {"$unset": {"mentor": ""}})
        return res
    if bonus >= 1:
        await col("mentorships").update_one({"_id": int(app_uid)}, {"$inc": {"xp_total": bonus}})
        await add_xp(int(app_uid), bonus, "mentor", apply_rate=False)  # the APPRENTICE gets the mentoring bonus (the fight's XP already carried every rate)
        res["xp"] = bonus
        app_ch = None  # the bonus may have levelled the apprentice: re-read before the graduation check
    master_ch = await get_char(master_uid)
    app_ch = app_ch or await get_char(app_uid)
    if not master_ch or not app_ch or int(app_ch["level"]) >= int(master_ch["level"]):
        await end(app_uid)  # the apprentice caught up: graduation
        res["graduated"] = True
    return res


# ---- gifts -----------------------------------------------------------------------------------------------------------
async def giftable(master_uid: int) -> list:
    """[(item_id, qty)] of the Treatise and Memoir books in the master's bag."""
    inv = await inv_get(master_uid)
    return sorted(((i, int(q)) for i, q in (inv.get("items") or {}).items() if int(q) > 0 and is_gift(i)),
                  key=lambda x: ALL[x[0]].get("name_fa", ""))


async def gifts_left(doc: dict) -> int:
    used = int(doc.get("gift_n", 0)) if doc.get("gift_day") == today() else 0
    return max(0, GIFT_PER_DAY - used)


async def gift(master_uid: int, app_uid: int, item_id: str) -> str:
    """The master gives ONE book to an apprentice. -> 'ok' | 'notmine' | 'notgift' | 'limit' | 'missing' | 'full'."""
    doc = await col("mentorships").find_one({"_id": int(app_uid), "master": int(master_uid)})
    if not doc:
        return "notmine"
    if not is_gift(item_id):
        return "notgift"
    if await gifts_left(doc) <= 0:
        return "limit"
    if not await inv_remove(master_uid, item_id, 1):
        return "missing"
    if not await inv_add(app_uid, item_id, 1, keep=True):  # not forced: the apprentice's bag capacity counts
        await inv_add(master_uid, item_id, 1, force=True, keep=True)
        return "full"
    day = today()
    if doc.get("gift_day") == day:
        await col("mentorships").update_one({"_id": int(app_uid)}, {"$inc": {"gift_n": 1}})
    else:
        await col("mentorships").update_one({"_id": int(app_uid)}, {"$set": {"gift_day": day, "gift_n": 1}})
    return "ok"
