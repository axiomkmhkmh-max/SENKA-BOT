"""Shared-world core: the single `world_state` document, its atomic clamped updates, modifiers,
the World Chronicle and season points. Low level on purpose: player/economy/combat import it."""
import logging
import random
import time
from datetime import datetime, timedelta, timezone

from data_world import REISHI_START, VAR_START, clamp, day_id, week_id, world_mods
from database import bump_counter, col, game_settings
from i18n import esc, t

log = logging.getLogger("senka.world")
WS_ID = "main"
_cache = {"at": 0.0, "ws": None, "ev": None}


# ---- state document ------------------------------------------------------------------------------------
async def get_world(force: bool = False):
    """Return (world_state, active_event_or_None). Cached for a few seconds."""
    now = time.monotonic()
    if not force and _cache["ws"] is not None and now - _cache["at"] < 5:
        return _cache["ws"], _cache["ev"]
    st = await game_settings()
    ts = int(time.time())
    await col("world_state").update_one({"_id": WS_ID}, {"$setOnInsert": {
        "threat": VAR_START["threat"], "stability": VAR_START["stability"], "reishi": {},
        "season": {"id": 1, "start": ts, "end": ts + int(st["season_days"]) * 86400},
        "next_boss_at": ts + 600, "drift_at": ts + 3600, "terr_week": week_id(), "event_id": None, "next_event_at": ts + 3600,
        "created_at": ts}}, upsert=True)
    ws = await col("world_state").find_one({"_id": WS_ID})
    ev = None
    if ws.get("event_id"):
        ev = await col("world_events").find_one({"_id": ws["event_id"], "status": "active"})
    _cache.update(at=now, ws=ws, ev=ev)
    return ws, ev


def invalidate():
    _cache["at"] = 0.0


async def world_adjust(threat: float = 0.0, stability: float = 0.0, reishi_loc: str = None, reishi: float = 0.0):
    """Atomic +/- on world variables, clamped to 0..100 inside MongoDB (needs MongoDB 4.2+)."""
    stage = {}
    if threat:
        stage["threat"] = {"$min": [100, {"$max": [0, {"$add": [{"$ifNull": ["$threat", VAR_START["threat"]]}, float(threat)]}]}]}
    if stability:
        stage["stability"] = {"$min": [100, {"$max": [0, {"$add": [{"$ifNull": ["$stability", VAR_START["stability"]]}, float(stability)]}]}]}
    if reishi_loc and reishi:
        stage[f"reishi.{reishi_loc}"] = {"$min": [100, {"$max": [0, {"$add": [{"$ifNull": [f"$reishi.{reishi_loc}", REISHI_START]}, float(reishi)]}]}]}
    if not stage:
        return
    await col("world_state").update_one({"_id": WS_ID}, [{"$set": stage}])


async def world_set(**vals):
    """Admin helper: set threat / stability or reishi.<loc> to an absolute value."""
    upd = {}
    for k, v in vals.items():
        if k in ("threat", "stability"):
            upd[k] = clamp(v)
        elif k.startswith("reishi."):
            upd[k] = clamp(v)
    if upd:
        await col("world_state").update_one({"_id": WS_ID}, {"$set": upd})
        invalidate()


async def mods_for(loc: str) -> dict:
    st = await game_settings()
    ws, ev = await get_world()
    return world_mods(ws, loc, st, ev)


# ---- population helpers ---------------------------------------------------------------------------------------
async def active_players(hours: int = 24) -> int:
    return await col("users").count_documents({"last_seen": {"$gte": int(time.time()) - hours * 3600}})


async def active_levels(limit: int = 300) -> list:
    ids = [u["telegram_id"] async for u in col("users").find({"last_seen": {"$gte": int(time.time()) - 86400}}, {"telegram_id": 1}).limit(limit)]
    if not ids:
        return []
    return [c["level"] async for c in col("characters").find({"user_id": {"$in": ids}}, {"level": 1})]


def is_new_account(ch: dict, st: dict) -> bool:
    return time.time() - int(ch.get("created_at", 0)) < int(st["new_acct_minutes"]) * 60


# ---- World Chronicle ---------------------------------------------------------------------------------------------
async def chronicle(kind: str, **params):
    """Append one short line to the world feed (kept 14 days). Never raises."""
    try:
        now = int(time.time())
        await col("world_log").insert_one({"at": now, "k": kind, "p": params, "expire_at": datetime.now(timezone.utc) + timedelta(days=14)})
    except Exception:
        log.exception("chronicle write failed")


async def chronicle_recent(n: int = 5) -> list:
    return await col("world_log").find({}).sort("at", -1).limit(n).to_list(n)


def chronicle_line(lang: str, row: dict) -> str:
    kw = {}
    for k, v in (row.get("p") or {}).items():
        if k.endswith("_fa") or k.endswith("_en"):
            base = k[:-3]
            if k.endswith("_" + ("fa" if lang == "fa" else "en")):
                kw[base] = esc(v)
        else:
            kw.setdefault(k, esc(v))
    ago = max(0, int(time.time()) - int(row["at"]))
    mark = f"{ago // 3600}h" if ago >= 3600 else f"{ago // 60}m"
    from i18n import LOCALES
    table = LOCALES.get(lang) or LOCALES["en"]
    base = "chr_" + row["k"]
    keys = [base] + [f"{base}_{i}" for i in range(2, 6) if f"{base}_{i}" in table]
    key = keys[int(row["at"]) % len(keys)]
    return f"▫️ {t(lang, key, **kw)} <i>({mark})</i>"


async def chronicle_text(lang: str, n: int = 5) -> str:
    rows = await chronicle_recent(n)
    return "\n".join(chronicle_line(lang, r) for r in rows)


# ---- season points ------------------------------------------------------------------------------------------------
async def season_add(uid: int, pts: int, name: str = None):
    """Seasonal world-participation points with a daily cap per player."""
    pts = int(pts)
    if pts <= 0:
        return
    st = await game_settings()
    ws, _ = await get_world()
    sid = ws["season"]["id"]
    if not await bump_counter(f"spts:{uid}:{day_id()}", pts, int(st["season_daily_pts_cap"])):
        return
    upd = {"$inc": {"pts": pts}, "$setOnInsert": {"season": sid, "user_id": uid}}
    if name:
        upd["$set"] = {"name": name[:30]}
    from pymongo import ReturnDocument
    from data_extras import seat_index
    doc = await col("season_scores").find_one_and_update({"_id": f"{sid}:{uid}"}, upd, upsert=True, return_document=ReturnDocument.AFTER)
    if doc:
        await col("characters").update_one({"user_id": uid}, {"$set": {"seat": seat_index(int(doc.get("pts", 0)))}})
