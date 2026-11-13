"""Admin toolbox logic (no Telegram I/O): artifact / Hogyoku hand-outs, tokens, redeem codes, mass gifts, fuzzy lookups.
Every function keeps the game's own invariants: one owner per artifact, one artifact per player, one Hogyoku in the world."""
import asyncio
import difflib
import re
import secrets
import time
import uuid

from pymongo.errors import DuplicateKeyError

from data_artifacts import ART_BY_ID, ARTIFACTS, norm_phrase
from data_items import ALL, iname
from database import col
from i18n import fnum
from security import normalize_text
from service_economy import inv_add
from service_log import log_event
from service_player import add_coins, add_xp, get_char

_DIG = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
MAX_QTY = 9999
MAX_COINS = 10 ** 9


# ---- parsing -------------------------------------------------------------------------------------------------
def parse_amount(s):
    """'5000', '5,000', '۵۰۰۰', '5k', '2.5m' -> int. None when it is not a positive number."""
    s = (s or "").translate(_DIG).replace(",", "").replace("٬", "").strip().lower()
    m = re.fullmatch(r"(\d+(?:\.\d+)?)([km]?)", s)
    if not m:
        return None
    v = int(float(m.group(1)) * {"": 1, "k": 1000, "m": 1000000}[m.group(2)])
    return v if v > 0 else None


def norm_code(s: str) -> str:
    return re.sub(r"\s+", "", (s or "").translate(_DIG)).upper()


CODE_RE = re.compile(r"^[A-Z0-9_\-]{3,24}$")


def auto_code() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "SENKA-" + "".join(secrets.choice(alphabet) for _ in range(8))


# ---- fuzzy lookups (id, English name, Persian name; typos tolerated) -----------------------------------------
def _key(s: str) -> str:
    return normalize_text(norm_phrase(s)).replace(" ", "")


def _rank(q: str, entries, limit: int = 10):
    """entries: [(id, [names])]. exact id -> substring -> fuzzy."""
    raw = (q or "").strip()
    k = _key(raw)
    if not k:
        return []
    for i, _names in entries:
        if raw.lower() == i.lower():
            return [i]
    sub = [i for i, names in entries if k in _key(i) or any(k in _key(n) for n in names if n)]
    if sub:
        exact = [i for i, names in entries if k in [_key(n) for n in names if n]]
        return (exact or sub)[:limit]
    scored = []
    for i, names in entries:
        best = max([difflib.SequenceMatcher(None, k, _key(n)).ratio() for n in names if n] + [0])
        if best >= 0.72:
            scored.append((best, i))
    scored.sort(reverse=True)
    return [i for _, i in scored[:limit]]


_ART_ENTRIES = [(a["_id"], [a["name_en"], a["name_fa"]]) for a in ARTIFACTS]
_ITEM_ENTRIES = None


def find_artifacts(q: str):
    return _rank(q, _ART_ENTRIES, 6)


def find_items(q: str, limit: int = 10):
    global _ITEM_ENTRIES
    if _ITEM_ENTRIES is None:
        _ITEM_ENTRIES = [(i, [x.get("name_en", ""), x.get("name_fa", "")]) for i, x in ALL.items()]
    return _rank(q, _ITEM_ENTRIES, limit)


# ---- artifacts -------------------------------------------------------------------------------------------------
async def _detach_artifact(aid: str):
    """Pull an artifact out of whatever state it is in (owner's slot, market listing, group drop). -> (status, previous_owner)."""
    d = await col("artifacts").find_one({"_id": aid}) or {}
    st = d.get("state", "free")
    if st in ("claiming", "releasing"):
        return "busy", None
    prev = d.get("owner") if st in ("owned", "listed") else None
    if st == "listed":
        await col("art_listings").update_many({"art": aid, "status": "active"}, {"$set": {"status": "cancelled"}})
    elif st == "dropped" and d.get("drop_id"):
        await col("drops").update_one({"_id": d["drop_id"]}, {"$set": {"status": "failed"}})
    await col("characters").update_many({"artifact": aid}, {"$unset": {"artifact": ""}})  # also repairs any drift
    return "ok", prev


async def artifact_give(aid: str, uid: int, replace: bool = True):
    """-> (status, previous_owner). status: ok | noreg | noart | already | has | busy."""
    if aid not in ART_BY_ID:
        return "noart", None
    ch = await get_char(uid)
    if not ch:
        return "noreg", None
    cur = ch.get("artifact")
    d = await col("artifacts").find_one({"_id": aid}) or {}
    if cur == aid and d.get("owner") == uid and d.get("state") == "owned":
        return "already", None
    if cur and cur != aid and not replace:
        return "has", None
    status, prev = await _detach_artifact(aid)
    if status == "busy":
        return "busy", None
    if cur and cur != aid:  # the old one goes back to the world
        await col("artifacts").update_one({"_id": cur, "owner": uid}, {"$set": {"state": "free", "owner": None}})
    now = int(time.time())
    await col("characters").update_one({"user_id": uid}, {"$set": {"artifact": aid}})
    await col("artifacts").update_one(
        {"_id": aid},
        {"$set": {"state": "owned", "owner": uid, "since": now}, "$unset": {"claimer": "", "drop_id": ""},
         "$push": {"history": {"$each": [{"uid": uid, "at": now, "how": "admin", "price": 0}], "$slice": -10}}}, upsert=True)
    log_event("art", uid, f"«{ART_BY_ID[aid]['name_fa']}» را از دست یک ادمین گرفت", art=aid)
    return "ok", prev


async def artifact_take(uid: int) -> str:
    """Remove whatever artifact the player holds (it returns to the world). -> ok | none | busy."""
    from service_drops import art_release
    return await art_release(uid)


async def artifact_free(aid: str):
    """Send an artifact back to the world no matter who has it. -> (status, previous_owner)."""
    if aid not in ART_BY_ID:
        return "noart", None
    status, prev = await _detach_artifact(aid)
    if status == "busy":
        return "busy", None
    await col("artifacts").update_one({"_id": aid}, {"$set": {"state": "free", "owner": None}, "$unset": {"claimer": "", "drop_id": ""}}, upsert=True)
    return "ok", prev


# ---- Hogyoku -----------------------------------------------------------------------------------------------------
async def hogyoku_give(uid: int):
    """Make `uid` the holder of the one Hogyoku. -> (status, previous_holder). status: ok | noreg | already."""
    ch = await get_char(uid)
    if not ch:
        return "noreg", None
    d = await col("hogyoku").find_one({"_id": "main"}) or {}
    old = d.get("holder")
    if old == uid and ch.get("hogyoku"):
        return "already", None
    now = int(time.time())
    await col("hogyoku").update_one({"_id": "main"}, {"$set": {"holder": uid, "since": now},
                                                      "$push": {"history": {"$each": [{"uid": uid, "from": old, "at": now, "how": "admin"}], "$slice": -10}}}, upsert=True)
    await col("characters").update_many({"hogyoku": True, "user_id": {"$ne": uid}}, {"$unset": {"hogyoku": ""}})
    await col("characters").update_one({"user_id": uid}, {"$set": {"hogyoku": True}})
    return "ok", old


async def hogyoku_info():
    """-> (uid, name, level, since) or None."""
    d = await col("hogyoku").find_one({"_id": "main"})
    if not d:
        return None
    ch = await get_char(d["holder"])
    return (d["holder"], ch["name"] if ch else "?", ch["level"] if ch else 0, d.get("since", 0))


# ---- tokens (a plain balance on the character: characters.tokens) --------------------------------------------------
async def add_tokens(uid: int, n: int, reason: str = "admin") -> bool:
    n = int(n)
    if n == 0:
        return True
    q = {"user_id": uid}
    if n < 0:
        q["tokens"] = {"$gte": -n}
    r = await col("characters").update_one(q, {"$inc": {"tokens": n}})
    if r.modified_count:
        await col("transactions").insert_one({"tx_key": uuid.uuid4().hex, "user_id": uid, "tokens": n, "reason": reason, "at": int(time.time())})
    return bool(r.modified_count)


async def set_tokens(uid: int, n: int) -> bool:
    r = await col("characters").update_one({"user_id": uid}, {"$set": {"tokens": max(0, int(n))}})
    return bool(r.matched_count)


# ---- rewards ---------------------------------------------------------------------------------------------------------
def validate_rewards(r: dict):
    """-> error key or None."""
    if not any(r.get(k) for k in ("coins", "xp", "tokens", "items", "art")):
        return "empty"
    for k in ("coins", "xp", "tokens"):
        if r.get(k) and not 0 < int(r[k]) <= MAX_COINS:
            return "range"
    for iid, n in (r.get("items") or {}).items():
        if iid not in ALL:
            return "item:" + iid
        if not 0 < int(n) <= MAX_QTY:
            return "range"
    if r.get("art") and r["art"] not in ART_BY_ID:
        return "noart"
    return None


def rewards_text(r: dict, lang: str) -> str:
    fa = lang == "fa"
    out = []
    if r.get("coins"):
        out.append(f"🪙 {fnum(r['coins'], lang)}")
    if r.get("xp"):
        out.append(f"✨ {fnum(r['xp'], lang)} " + ("تجربه" if fa else "XP"))
    if r.get("tokens"):
        out.append(f"🎟 {fnum(r['tokens'], lang)} " + ("توکن" if fa else "tokens"))
    for iid, n in (r.get("items") or {}).items():
        out.append(f"📦 {iname(iid, lang)} ×{fnum(n, lang)}")
    if r.get("art") and r["art"] in ART_BY_ID:
        a = ART_BY_ID[r["art"]]
        out.append(f"{a['icon']} {a['name_fa' if fa else 'name_en']}")
    return "\n".join(out)


async def grant_rewards(uid: int, r: dict, reason: str = "admin"):
    """Give everything in `r`. The artifact goes first (it is the only part that can be refused). -> 'ok' or an artifact status."""
    if r.get("art"):
        st, _ = await artifact_give(r["art"], uid, replace=False)
        if st != "ok":
            return st
    if r.get("coins"):
        await add_coins(uid, int(r["coins"]), reason)
    if r.get("xp"):
        await add_xp(uid, int(r["xp"]), reason, apply_rate=False)
    if r.get("tokens"):
        await add_tokens(uid, int(r["tokens"]), reason)
    for iid, n in (r.get("items") or {}).items():
        await inv_add(uid, iid, int(n), force=True)
    return "ok"


# ---- redeem codes -----------------------------------------------------------------------------------------------------
async def create_code(admin: int, code: str, rewards: dict, max_uses: int = 1, expires_at: int = 0, note: str = ""):
    """-> 'ok' | 'bad' | 'exists'. max_uses 0 = unlimited (still once per player)."""
    code = norm_code(code)
    if not CODE_RE.match(code):
        return "bad"
    doc = {"_id": code, "rewards": rewards, "max_uses": int(max_uses), "uses": 0, "used_by": [], "active": True,
           "expires_at": int(expires_at or 0), "note": (note or "")[:120], "created_by": admin, "created_at": int(time.time())}
    try:
        await col("redeem_codes").insert_one(doc)
    except DuplicateKeyError:
        return "exists"
    return "ok"


async def get_code(code: str):
    return await col("redeem_codes").find_one({"_id": norm_code(code)})


def code_state(d: dict, now: int = None) -> str:
    """active | off | expired | full"""
    now = now or int(time.time())
    if not d.get("active", True):
        return "off"
    if d.get("expires_at") and d["expires_at"] <= now:
        return "expired"
    if d.get("max_uses") and d.get("uses", 0) >= d["max_uses"]:
        return "full"
    return "active"


async def set_code_active(code: str, on: bool) -> bool:
    r = await col("redeem_codes").update_one({"_id": norm_code(code)}, {"$set": {"active": on}})
    return bool(r.matched_count)


async def delete_code(code: str) -> bool:
    r = await col("redeem_codes").delete_one({"_id": norm_code(code)})
    return bool(r.deleted_count)


async def list_codes(limit: int = 20):
    return await col("redeem_codes").find({}, {"used_by": 0}).sort("created_at", -1).limit(limit).to_list(limit)


async def redeem(uid: int, raw: str):
    """-> (status, doc). status: noreg | nocode | off | expired | used | full | art_has | art_busy | ok."""
    code = norm_code(raw)
    if not await get_char(uid):
        return "noreg", None
    d = await col("redeem_codes").find_one({"_id": code})
    if not d:
        return "nocode", None
    now = int(time.time())
    stt = code_state(d, now)
    if stt in ("off", "expired", "full"):
        return stt, d
    if uid in d.get("used_by", []):
        return "used", d
    flt = {"_id": code, "active": {"$ne": False}, "used_by": {"$ne": uid},
           "$or": [{"expires_at": {"$in": [None, 0]}}, {"expires_at": {"$gt": now}}]}
    if d.get("max_uses"):
        flt["uses"] = {"$lt": d["max_uses"]}
    claimed = await col("redeem_codes").find_one_and_update(flt, {"$inc": {"uses": 1}, "$push": {"used_by": uid}})
    if not claimed:  # somebody else took the last use a moment ago
        return "full", d
    res = await grant_rewards(uid, d.get("rewards") or {}, "redeem")
    if res != "ok":
        await col("redeem_codes").update_one({"_id": code}, {"$inc": {"uses": -1}, "$pull": {"used_by": uid}})
        return ("art_has" if res == "has" else "art_busy"), d
    log_event("admin", uid, f"کد هدیه «{code}» را وارد کرد")
    return "ok", d


# ---- mass gifts --------------------------------------------------------------------------------------------------------
async def gift_all(kind: str, n: int, item_id: str = None):
    """kind: coins | tokens | xp | item. -> number of players reached."""
    if kind in ("coins", "tokens"):
        r = await col("characters").update_many({}, {"$inc": {kind: int(n)}})
        return r.modified_count
    done = 0
    async for c in col("characters").find({}, {"user_id": 1}):
        try:
            if kind == "xp":
                await add_xp(c["user_id"], int(n), "admin", apply_rate=False)
            else:
                await inv_add(c["user_id"], item_id, int(n), force=True)
            done += 1
        except Exception:
            pass
        if done % 40 == 0:
            await asyncio.sleep(0.05)
    return done
