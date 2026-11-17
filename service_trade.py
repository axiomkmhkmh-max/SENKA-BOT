"""Player trading: one-to-one trades and group trade tables.

Two kinds of session share one model (collection `trades`):
- "pair": two players swap their offers exactly as written (several item stacks + coins each).
- "group": a table of 3 to TRADE_GROUP_MAX players. Everyone puts an offer on the table; when every member confirms
  the SAME table, all offers are pooled and shared out evenly (items round-robin, coins split equally, the
  remainder goes to the table host). Good for a shared drop or a big bundle among friends.

Shared rules: a level floor, no brand-new accounts, one open session per player, idle sessions close after
TRADE_TTL, any change clears all confirmations, and execution is one claim (open -> executing) so it runs once.
Every finished trade is written to `trade_log` so players can look back at it.
"""
import time

from bson import ObjectId

from data_items import ALL
from database import col, game_settings
from service_economy import inv_add, inv_get, inv_remove
from service_player import add_coins, get_char
from service_worldcore import is_new_account

TRADE_MIN_LEVEL = 10
TRADE_MAX_LINES = 8          # item stacks per side
TRADE_MAX_COINS = 10_000_000
TRADE_TTL = 15 * 60
TRADE_GROUP_MAX = 6
TRADE_GROUP_MIN = 3


def _side(offer):
    return offer or {"items": {}, "coins": 0}


async def _eligible(uid):
    ch = await get_char(uid)
    if not ch:
        return None, "noreg"
    if int(ch["level"]) < TRADE_MIN_LEVEL:
        return None, "level"
    if is_new_account(ch, await game_settings()):
        return None, "new"
    return ch, None


async def busy_session(uid):
    """The player's live open session. Idle ones past TRADE_TTL are closed here: they used to stay `open` until
    their own owner looked at them, and in the meantime they blocked every new trade ("one of you already has an
    open trade")."""
    for _ in range(5):
        doc = await col("trades").find_one({"status": "open", "members": uid})
        if not doc:
            return None
        if time.time() - int(doc.get("updated_at", 0)) <= TRADE_TTL:
            return doc
        await col("trades").update_one({"_id": doc["_id"], "status": "open"}, {"$set": {"status": "expired"}})
    return None


async def _create(kind, host, members, limit_note=None):
    doc = {"kind": kind, "host": host, "members": members, "status": "open",
           "offers": {str(u): _side(None) for u in members}, "confirm": {},
           "created_at": int(time.time()), "updated_at": int(time.time())}
    res = await col("trades").insert_one(doc)
    return str(res.inserted_id)


async def open_pair(a: int, b: int):
    if a == b:
        return None, "self"
    for uid in (a, b):
        _, err = await _eligible(uid)
        if err:
            return None, err
        if await busy_session(uid):
            return None, "busy"
    return await _create("pair", a, [a, b]), None


async def open_group(host: int):
    _, err = await _eligible(host)
    if err:
        return None, err
    if await busy_session(host):
        return None, "busy"
    return await _create("group", host, [host]), None


async def join_group(tid: str, uid: int):
    doc = await get_session(tid, uid, allow_join=True)
    if not doc or doc["kind"] != "group":
        return "closed"
    if uid in doc["members"]:
        return "ok"
    if len(doc["members"]) >= TRADE_GROUP_MAX:
        return "full"
    _, err = await _eligible(uid)
    if err:
        return err
    if await busy_session(uid):
        return "busy"
    await col("trades").update_one({"_id": ObjectId(tid), "status": "open"},
                                   {"$push": {"members": uid}, "$set": {f"offers.{uid}": _side(None),
                                                                        "confirm": {}, "updated_at": int(time.time())}})
    return "ok"


async def get_session(tid, uid, allow_join=False):
    try:
        doc = await col("trades").find_one({"_id": ObjectId(tid), "status": "open"})
    except Exception:
        return None
    if not doc:
        return None
    if not allow_join and uid not in doc["members"]:
        return None
    if time.time() - int(doc.get("updated_at", 0)) > TRADE_TTL:
        await col("trades").update_one({"_id": doc["_id"], "status": "open"}, {"$set": {"status": "expired"}})
        return None
    return doc


async def _touch(tid, changes: dict):
    return await col("trades").update_one({"_id": ObjectId(tid), "status": "open"},
                                          {"$set": {**changes, "confirm": {}, "updated_at": int(time.time())}})


async def add_item(tid, uid, item_id):
    doc = await get_session(tid, uid)
    if not doc:
        return "closed"
    if not (ALL.get(item_id) or {}).get("tradeable"):  # keys, Mythic blades... are bound to their owner (same rule as the market)
        return "notrade"
    inv = await inv_get(uid)
    offer = _side(doc["offers"].get(str(uid)))
    have = int((inv.get("items") or {}).get(item_id, 0))
    held = int(offer["items"].get(item_id, 0))
    if have <= held:
        return "missing"
    if item_id not in offer["items"] and len(offer["items"]) >= TRADE_MAX_LINES:
        return "lines"
    offer["items"][item_id] = held + 1
    await _touch(tid, {f"offers.{uid}": offer})
    return "ok"


async def remove_item(tid, uid, item_id):
    doc = await get_session(tid, uid)
    if not doc:
        return "closed"
    offer = _side(doc["offers"].get(str(uid)))
    if item_id not in offer["items"]:
        return "missing"
    offer["items"][item_id] -= 1
    if offer["items"][item_id] <= 0:
        del offer["items"][item_id]
    await _touch(tid, {f"offers.{uid}": offer})
    return "ok"


async def set_coins(tid, uid, coins: int):
    doc = await get_session(tid, uid)
    if not doc:
        return "closed"
    coins = max(0, min(int(coins), TRADE_MAX_COINS))
    ch = await get_char(uid)
    if coins > int(ch.get("coins", 0)):
        return "funds"
    offer = _side(doc["offers"].get(str(uid)))
    offer["coins"] = coins
    await _touch(tid, {f"offers.{uid}": offer})
    return "ok"


async def confirm(tid, uid):
    doc = await get_session(tid, uid)
    if not doc:
        return "closed"
    if doc["kind"] == "group" and len(doc["members"]) < TRADE_GROUP_MIN:
        return "group_min"
    await col("trades").update_one({"_id": ObjectId(tid), "status": "open"},
                                   {"$set": {f"confirm.{uid}": True, "updated_at": int(time.time())}})
    doc = await col("trades").find_one({"_id": ObjectId(tid)})
    conf = doc.get("confirm") or {}
    if not all(conf.get(str(m)) for m in doc["members"]):
        return "waiting"
    return await _execute(doc)


def _plan_pair(doc):
    a, b = doc["members"][0], doc["members"][1]
    return {a: (_side(doc["offers"].get(str(a))), _side(doc["offers"].get(str(b)))),
            b: (_side(doc["offers"].get(str(b))), _side(doc["offers"].get(str(a))))}


def _plan_group(doc):
    """Pool every offer, then share it out. Returns {uid: (give, get)} where give is what that uid puts in."""
    members = doc["members"]
    host = doc["host"]
    pool_items, pool_coins, gives = {}, 0, {}
    for m in members:
        o = _side(doc["offers"].get(str(m)))
        gives[m] = o
        for i, q in o["items"].items():
            pool_items[i] = pool_items.get(i, 0) + int(q)
        pool_coins += int(o["coins"])
    n = len(members)
    shares = {m: {"items": {}, "coins": pool_coins // n} for m in members}
    shares[host]["coins"] += pool_coins - (pool_coins // n) * n  # remainder to the host
    order = sorted(members, key=lambda u: (u != host, u))  # host first, then stable order
    k = 0
    for item, qty in pool_items.items():  # round-robin, so each stack is split as evenly as possible
        for _ in range(qty):
            who = order[k % n]
            shares[who]["items"][item] = shares[who]["items"].get(item, 0) + 1
            k += 1
    return {m: (gives[m], shares[m]) for m in members}


async def _execute(doc):
    tid = doc["_id"]
    claim = await col("trades").find_one_and_update({"_id": tid, "status": "open"}, {"$set": {"status": "executing"}})
    if not claim:
        return "closed"
    plan = _plan_pair(doc) if doc["kind"] == "pair" else _plan_group(doc)
    # every participant must still hold what they put in, and enough coins
    for uid, (give, _) in plan.items():
        inv = await inv_get(uid)
        ch = await get_char(uid) or {}
        if any(not (ALL.get(i) or {}).get("tradeable") for i in give["items"]):  # offers made before the rule existed
            await col("trades").update_one({"_id": tid}, {"$set": {"status": "failed", "reason": "notrade"}})
            return "notrade"
        if any(int((inv.get("items") or {}).get(i, 0)) < q for i, q in give["items"].items()) or \
           int(ch.get("coins", 0)) < int(give["coins"]):
            await col("trades").update_one({"_id": tid}, {"$set": {"status": "failed", "reason": "missing"}})
            return "missing"
    for uid, (_give, get) in plan.items():  # race armour and race cards go only to a player of that race
        race = ((await get_char(uid)) or {}).get("race")
        if any((ALL.get(i) or {}).get("race") not in (None, race) for i in get["items"]):
            await col("trades").update_one({"_id": tid}, {"$set": {"status": "failed", "reason": "race"}})
            return "race"
    removed, debited = [], []
    try:
        # take what each side gives. A coin debit that fails (the player spent the coins since the check) must
        # abort the trade; before, its return value was ignored and the other side got items for free.
        for uid, (give, _) in plan.items():
            amount = int(give["coins"])
            if amount:
                if not await add_coins(uid, -amount, "trade"):
                    raise RuntimeError("missing")
                debited.append((uid, amount))
            for i, q in give["items"].items():
                if not await inv_remove(uid, i, q):
                    raise RuntimeError("missing")
                removed.append((uid, i, q))
        # pair: each side receives exactly the other side's offer; group: the host-split shares
        for uid, (_, get) in plan.items():
            for i, q in get["items"].items():
                await inv_add(uid, i, q, force=True)
            amount = int(get.get("coins", 0))
            if amount:
                await add_coins(uid, amount, "trade")
    except Exception as exc:
        # roll back everything already moved: items go back, coins are refunded
        for uid, amount in debited:
            await add_coins(uid, amount, "trade_refund")
        for uid, i, q in removed:
            await inv_add(uid, i, q, force=True)
        reason = "missing" if str(exc) == "missing" else "error"
        await col("trades").update_one({"_id": tid}, {"$set": {"status": "failed", "reason": reason}})
        return reason
    await col("trades").update_one({"_id": tid}, {"$set": {"status": "done", "finished_at": int(time.time())}})
    await col("trade_log").insert_one({"trade": str(tid), "kind": doc["kind"], "members": doc["members"],
                                       "offers": doc["offers"], "at": int(time.time())})
    return "done"


async def cancel(tid, uid):
    doc = await get_session(tid, uid)
    if not doc:
        return "closed"
    if doc["kind"] == "group" and uid != doc["host"]:
        await col("trades").update_one({"_id": ObjectId(tid), "status": "open"},
                                       {"$pull": {"members": uid}, "$unset": {f"offers.{uid}": "", f"confirm.{uid}": ""}})
        return "left"
    await col("trades").update_one({"_id": ObjectId(tid), "status": "open"}, {"$set": {"status": "cancelled"}})
    return "ok"


async def nearby_players(uid, location, limit=8):
    cur = col("characters").find({"location": location, "user_id": {"$ne": uid}, "level": {"$gte": TRADE_MIN_LEVEL}},
                                 {"user_id": 1, "name": 1, "level": 1, "race": 1}).sort("level", -1).limit(limit)
    return [d async for d in cur]


async def open_tables(location, limit=6):
    """Group tables that are open and whose host is in this place."""
    cur = col("trades").find({"status": "open", "kind": "group"}).sort("created_at", -1).limit(limit)
    out = []
    async for t in cur:
        host = await get_char(t["host"])
        if host and host.get("location") == location and len(t["members"]) < TRADE_GROUP_MAX:
            out.append(t)
    return out


async def history(uid, limit=8):
    cur = col("trade_log").find({"members": uid}).sort("at", -1).limit(limit)
    return [d async for d in cur]
