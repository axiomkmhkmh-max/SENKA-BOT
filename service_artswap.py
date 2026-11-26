"""Artifact swap: two players trade their artifacts straight across (no coins, no market).

Flow: A offers a swap to B (both hold an artifact, neither is listed on the exchange) -> B accepts or declines.
The swap itself is two guarded updates (each checks that the holder still has the expected artifact) with a roll-back, so an
artifact is never duplicated or lost. Held counts do not change: A's copy of X becomes B's, B's copy of Y becomes A's.

Anti-abuse: min level, per-player and per-pair daily caps, one open offer per player, offers expire.
"""
import time
import uuid

from data_artifacts import ART_BY_ID
from database import bump_counter, col
from service_log import log_event
from service_player import get_char

SWAP_TTL = 10 * 60           # an offer lives 10 minutes
SWAP_MIN_LEVEL = 10
SWAP_DAILY = 2               # swaps per player per day
SWAP_PAIR_DAILY = 1          # swaps between the same two players per day


def _day() -> str:
    return time.strftime("%Y%m%d", time.gmtime())


async def _listed(uid: int) -> bool:
    return bool(await col("art_listings").find_one({"seller": uid, "status": "active"}, {"_id": 1}))


async def offer(a: int, b: int):
    """-> (swap_id | None, code). Codes: ok self level none other_none same listed busy limit pair_limit."""
    if a == b:
        return None, "self"
    ca, cb = await get_char(a), await get_char(b)
    if not ca or not cb:
        return None, "other_none"
    if min(int(ca.get("level", 1)), int(cb.get("level", 1))) < SWAP_MIN_LEVEL:
        return None, "level"
    xa, xb = ca.get("artifact"), cb.get("artifact")
    if not xa:
        return None, "none"
    if not xb:
        return None, "other_none"
    if xa == xb:
        return None, "same"
    if await _listed(a) or await _listed(b):
        return None, "listed"
    now = int(time.time())
    async for d in col("art_swaps").find({"status": "pending"}):
        if int(d.get("end_at", 0)) > now and (a in (d["a"], d["b"]) or b in (d["a"], d["b"])):
            return None, "busy"
    day = _day()
    pair = f"{min(a, b)}:{max(a, b)}"
    if not await bump_counter(f"artswap:{day}:{a}", 1, SWAP_DAILY) or not await bump_counter(f"artswap:{day}:{b}", 1, SWAP_DAILY):
        return None, "limit"
    if not await bump_counter(f"artswap_pair:{day}:{pair}", 1, SWAP_PAIR_DAILY):
        return None, "pair_limit"
    sid = uuid.uuid4().hex[:10]
    await col("art_swaps").insert_one({"_id": sid, "a": a, "b": b, "art_a": xa, "art_b": xb, "status": "pending",
                                       "created_at": now, "end_at": now + SWAP_TTL})
    return sid, "ok"


async def get(sid: str) -> dict:
    return await col("art_swaps").find_one({"_id": sid}) or {}


async def pending_for(uid: int) -> list:
    """Open offers waiting for `uid` to answer."""
    now = int(time.time())
    return [d async for d in col("art_swaps").find({"status": "pending", "b": uid}) if int(d.get("end_at", 0)) > now]


async def decline(sid: str, uid: int) -> str:
    """Either side can close an open offer: ok / gone."""
    d = await get(sid)
    if not d or d.get("status") != "pending" or uid not in (d["a"], d["b"]):
        return "gone"
    r = await col("art_swaps").update_one({"_id": sid, "status": "pending"}, {"$set": {"status": "declined"}})
    return "ok" if r.modified_count or r.matched_count else "gone"


async def accept(sid: str, uid: int) -> str:
    """Only the receiver accepts. -> ok / gone / expired / changed / busy."""
    d = await get(sid)
    if not d or d.get("status") != "pending" or d["b"] != uid:
        return "gone"
    if int(d.get("end_at", 0)) <= int(time.time()):
        await col("art_swaps").update_one({"_id": sid}, {"$set": {"status": "expired"}})
        return "expired"
    claimed = await col("art_swaps").find_one_and_update({"_id": sid, "status": "pending"}, {"$set": {"status": "running"}})
    if not claimed:
        return "busy"
    a, b, xa, xb = d["a"], d["b"], d["art_a"], d["art_b"]
    if await _listed(a) or await _listed(b):
        await col("art_swaps").update_one({"_id": sid}, {"$set": {"status": "failed"}})
        return "changed"
    chars = col("characters")
    r1 = await chars.update_one({"user_id": a, "artifact": xa}, {"$set": {"artifact": xb}})
    if not r1.modified_count:
        await col("art_swaps").update_one({"_id": sid}, {"$set": {"status": "failed"}})
        return "changed"
    r2 = await chars.update_one({"user_id": b, "artifact": xb}, {"$set": {"artifact": xa}})
    if not r2.modified_count:  # roll A back: nothing is lost or duplicated
        await chars.update_one({"user_id": a, "artifact": xb}, {"$set": {"artifact": xa}})
        await col("art_swaps").update_one({"_id": sid}, {"$set": {"status": "failed"}})
        return "changed"
    await col("art_swaps").update_one({"_id": sid}, {"$set": {"status": "done", "done_at": int(time.time())}})
    na, nb = ART_BY_ID[xa]["name_fa"], ART_BY_ID[xb]["name_fa"]
    log_event("art", a, f"آرتیفکت «{na}» را با «{nb}» پلیر دیگر عوض کرد", art=xb)
    log_event("art", b, f"آرتیفکت «{nb}» را با «{na}» پلیر دیگر عوض کرد", art=xa)
    return "ok"
