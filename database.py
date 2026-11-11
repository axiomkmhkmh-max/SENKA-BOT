"""MongoDB access, indexes, atomic cooldowns/leases and live game settings."""
import logging
import time
from datetime import datetime, timedelta, timezone

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING, UpdateOne
from pymongo.errors import DuplicateKeyError

from config import GAME_DEFAULTS, settings

log = logging.getLogger("senka.db")
_client = None
_db = None
_cache = {"at": 0.0, "data": dict(GAME_DEFAULTS)}


def col(name):
    if _db is None:
        raise RuntimeError("Database is not connected")
    return _db[name]


async def connect_db():
    global _client, _db
    _client = AsyncIOMotorClient(settings.mongodb_uri, serverSelectionTimeoutMS=15000)
    await _client.admin.command("ping")
    _db = _client[settings.database_name]
    await ensure_indexes()
    log.info("MongoDB connected")


async def close_db():
    if _client is not None:
        _client.close()


async def ping() -> bool:
    try:
        await _client.admin.command("ping")
        return True
    except Exception:
        return False


async def ensure_indexes():
    U = {"unique": True}
    specs = {
        "users": [([("telegram_id", ASCENDING)], U), ([("last_seen", DESCENDING)], {})],
        "characters": [([("user_id", ASCENDING)], U), ([("name_key", ASCENDING)], U),
                       ([("level", DESCENDING), ("xp", DESCENDING)], {}),
                       ([("rating", DESCENDING)], {}), ([("guild_id", ASCENDING)], {})],
        "inventories": [([("user_id", ASCENDING)], U)],
        "registration": [([("user_id", ASCENDING)], U)],
        "cooldowns": [([("key", ASCENDING)], U), ([("expire_at", ASCENDING)], {"expireAfterSeconds": 0})],
        "daily_claims": [([("user_id", ASCENDING), ("day", ASCENDING)], U)],
        "transactions": [([("tx_key", ASCENDING)], U), ([("user_id", ASCENDING), ("at", DESCENDING)], {})],
        "market_listings": [([("status", ASCENDING), ("kind", ASCENDING), ("created_at", DESCENDING)], {}),
                            ([("seller", ASCENDING), ("status", ASCENDING)], {}),
                            ([("end_at", ASCENDING)], {})],
        "battles": [([("sid", ASCENDING)], U), ([("status", ASCENDING), ("deadline", ASCENDING)], {}),
                    ([("expire_at", ASCENDING)], {"expireAfterSeconds": 0})],
        "battle_logs": [([("user_id", ASCENDING), ("at", DESCENDING)], {}),
                        ([("at", ASCENDING)], {"expireAfterSeconds": 60 * 60 * 24 * 60})],
        "boss_sessions": [([("chat_id", ASCENDING), ("active", ASCENDING)], {})],
        "groups": [([("chat_id", ASCENDING)], U)],
        "guilds": [([("name_key", ASCENDING)], U)],
        "player_quests": [([("user_id", ASCENDING)], U)],
        "gacha": [([("user_id", ASCENDING)], U)],
        "minigames": [([("gid", ASCENDING)], U), ([("expire_at", ASCENDING)], {"expireAfterSeconds": 0})],
        "admin_logs": [([("at", DESCENDING)], {})],
        "admin_users": [([("user_id", ASCENDING)], U)],
        "locks": [],
        "intents": [([("action", ASCENDING)], U)],
    }
    for name, items in specs.items():
        for keys, opts in items:
            try:
                await col(name).create_index(keys, **opts)
            except Exception:
                log.exception("index failed on %s %s", name, keys)


# ---- live settings ---------------------------------------------------------
def settings_snapshot() -> dict:
    """Last cached settings, synchronous (for pure formatting code)."""
    return _cache["data"]


async def game_settings(force: bool = False) -> dict:
    now = time.monotonic()
    if force or now - _cache["at"] > 20:
        doc = await col("settings").find_one({"_id": "game"}) or {}
        data = dict(GAME_DEFAULTS)
        data.update({k: v for k, v in doc.items() if k in GAME_DEFAULTS})
        _cache.update(at=now, data=data)
    return _cache["data"]


async def set_game_setting(key: str, value):
    if key not in GAME_DEFAULTS:
        raise KeyError(key)
    await col("settings").update_one({"_id": "game"}, {"$set": {key: value}}, upsert=True)
    await game_settings(force=True)


# ---- atomic primitives -----------------------------------------------------
async def try_cooldown(key: str, seconds: float) -> int:
    """Return 0 and arm the cooldown, or the remaining seconds. Race-safe."""
    now = time.time()
    exp = datetime.now(timezone.utc) + timedelta(seconds=seconds + 3600)
    c = col("cooldowns")
    hit = await c.find_one_and_update({"key": key, "until": {"$lte": now}},
                                      {"$set": {"until": now + seconds, "expire_at": exp}})
    if hit:
        return 0
    try:
        await c.insert_one({"key": key, "until": now + seconds, "expire_at": exp})
        return 0
    except DuplicateKeyError:
        doc = await c.find_one({"key": key})
        return max(1, int((doc or {}).get("until", now + 1) - now) + 1)


async def acquire_lease(name: str, owner: str, ttl: int) -> bool:
    """Distributed lock so only one instance runs schedulers."""
    now = time.time()
    try:
        hit = await col("locks").find_one_and_update(
            {"_id": name, "$or": [{"owner": owner}, {"until": {"$lte": now}}]},
            {"$set": {"owner": owner, "until": now + ttl}})
        if hit:
            return True
        await col("locks").insert_one({"_id": name, "owner": owner, "until": now + ttl})
        return True
    except DuplicateKeyError:
        return False


async def bulk_upsert(name: str, rows: list, chunk: int = 500):
    ops = [UpdateOne({"_id": r["_id"]}, {"$set": {k: v for k, v in r.items() if k != "_id"}}, upsert=True) for r in rows]
    for i in range(0, len(ops), chunk):
        await col(name).bulk_write(ops[i:i + chunk], ordered=False)
