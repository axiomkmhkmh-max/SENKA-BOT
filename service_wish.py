"""Forge Mission service (rules in data_wish). One open mission per player; progress is read from the bag, nothing is
locked away, and the items are taken only when the mission is completed (all or nothing)."""
import time

from data_items import ALL
from data_wish import ABANDON_WAIT_H, WEEKLY_DONE, eligible, requirement
from database import bump_counter, col
from service_economy import inv_add, inv_get, inv_remove
from service_log import log_event
from service_player import add_coins, get_char


def _week() -> str:
    return time.strftime("%G%V", time.gmtime())


async def current(uid: int) -> dict:
    return await col("wishes").find_one({"user_id": uid, "status": "open"}) or {}


async def start(uid: int, item_id: str):
    """-> (mission | None, code). Codes: ok noreg level notlisted open wait."""
    ch = await get_char(uid)
    if not ch:
        return None, "noreg"
    if item_id not in eligible(int(ch.get("level", 1)), ch.get("race")):
        return None, "notlisted"
    if await current(uid):
        return None, "open"
    last = await col("wishes").find_one({"user_id": uid, "status": "abandoned"})
    if last and time.time() - int(last.get("closed_at", 0)) < ABANDON_WAIT_H * 3600:
        return None, "wait"
    req = requirement(item_id, int(ch.get("level", 1)))
    doc = {"user_id": uid, "item": item_id, "status": "open", "mats": req["mats"], "from": req["from"], "coins": req["coins"], "at": int(time.time())}
    await col("wishes").insert_one(doc)
    return doc, "ok"


async def progress(uid: int, doc: dict) -> list:
    """[(item id, need, have)] for each material, plus coins in the caller."""
    inv = (await inv_get(uid)).get("items", {})
    return [(i, int(n), int(inv.get(i, 0))) for i, n in doc["mats"].items()]


async def abandon(uid: int) -> str:
    r = await col("wishes").update_one({"user_id": uid, "status": "open"}, {"$set": {"status": "abandoned", "closed_at": int(time.time())}})
    return "ok" if r.modified_count else "none"


async def complete(uid: int):
    """-> code. ok / none / mats / funds / weekly / full. Takes every material and the coins, or nothing."""
    doc = await current(uid)
    if not doc:
        return "none"
    if any(have < need for _, need, have in await progress(uid, doc)):
        return "mats"
    if not await bump_counter(f"wishdone:{uid}:{_week()}", 1, WEEKLY_DONE, ttl_hours=24 * 8):
        return "weekly"
    if doc["coins"] and not await add_coins(uid, -int(doc["coins"]), "wish_forge"):
        await _undo_week(uid)
        return "funds"
    done = []
    for iid, need in doc["mats"].items():
        if await inv_remove(uid, iid, int(need)):
            done.append((iid, int(need)))
            continue
        for j, q in done:  # a race with another action: put everything back
            await inv_add(uid, j, q, force=True)
        if doc["coins"]:
            await add_coins(uid, int(doc["coins"]), "wish_refund")
        await _undo_week(uid)
        return "mats"
    if not await inv_add(uid, doc["item"], 1):
        for j, q in done:
            await inv_add(uid, j, q, force=True)
        if doc["coins"]:
            await add_coins(uid, int(doc["coins"]), "wish_refund")
        await _undo_week(uid)
        return "full"
    await col("wishes").update_one({"user_id": uid, "status": "open"}, {"$set": {"status": "done", "closed_at": int(time.time())}})
    log_event("wish_forge", uid, f"ماموریت ساخت کامل شد: {doc['item']}", item=doc["item"])
    return "ok"


async def _undo_week(uid: int):
    await col("counters").update_one({"key": f"wishdone:{uid}:{_week()}"}, {"$inc": {"n": -1}})
