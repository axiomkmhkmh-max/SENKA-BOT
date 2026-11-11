"""The living world: every player action nudges shared variables, feeds the active world event,
earns territory points for the player's guild and season points. Also the scheduler-side ticks
(drift, events, weekly territory settlement, season rollover). All shared writes are atomic."""
import logging
import random
import time
from datetime import datetime, timedelta, timezone

from data_crafting import player_bonus
from data_items import ALL, COSMETIC_BY_RARITY, EVO_BY_RARITY
from data_weapons import RARITIES
from data_world import (EVENTS, HOLLOW_LOCS, REISHI_START, SEI_LOCS, clamp, day_id, event_goal, event_pts, pick_event_kind,
                        soft_reset_rating, terr_pick_owner, week_id)
from database import bump_counter, col, game_settings
from i18n import t
from service_economy import inv_add
from service_player import add_coins, add_xp, get_char
from service_worldcore import (WS_ID, active_players, chronicle, get_world, invalidate, is_new_account, season_add, world_adjust)

log = logging.getLogger("senka.worldstate")
TERR_PTS = {"explore": 1, "pve_win": 1, "elite_win": 2, "dungeon_clear": 4, "boss_hit": 2}
SEASON_PTS = {"explore": 1, "pve_win": 1, "elite_win": 2, "dungeon_clear": 4, "pvp_win": 3, "craft": 1}


# ---- the one entry point every gameplay action calls ----------------------------------------------------
async def on_action(uid: int, action: str, loc: str = None):
    """Never raises: the world must not be able to break a player's own action."""
    try:
        await _on_action(uid, action, loc)
    except Exception:
        log.exception("on_action failed: %s %s", action, uid)


async def _on_action(uid: int, action: str, loc: str):
    ch = await get_char(uid)
    if not ch:
        return
    st = await game_settings()
    loc = loc or ch["location"]
    now = int(time.time())
    bn = player_bonus(ch, ALL, st)
    await col("characters").update_one({"user_id": uid}, {"$set": {"seen_at": now}})
    # 1) shared variables
    if action == "explore":
        await world_adjust(stability=(float(st["world_stab_patrol"]) + bn["stab"]) if loc in SEI_LOCS else 0.0,
                           reishi_loc=loc, reishi=float(st["world_reishi_patrol"]))
    elif action in ("pve_win", "elite_win"):
        await world_adjust(threat=-float(st["world_threat_win"]) * (2 if action == "elite_win" else 1) * (1 + bn["calm"]))
    elif action == "dungeon_clear":
        await world_adjust(threat=-float(st["world_threat_dungeon"]) * (1 + bn["calm"]))
    elif action == "pve_loss":
        from service_interact import auto_grave
        await auto_grave(ch)
    # 2) world event contribution
    _, ev = await get_world()
    if ev and not is_new_account(ch, st):
        pts = event_pts(ev["kind"], action, loc)
        if pts and await bump_counter(f"evpts:{uid}:{day_id()}", pts, int(st["event_daily_pts_cap"])):
            await col("world_events").update_one({"_id": ev["_id"], "status": "active"},
                                                 {"$inc": {"progress": pts, f"contrib.{uid}": pts}, "$set": {f"nm.{uid}": ch["name"]}})
    # 3) territory points for the guild
    if action in TERR_PTS:
        await territory_score(ch, loc, TERR_PTS[action], st)
    # 4) season points
    if action in SEASON_PTS:
        await season_add(uid, SEASON_PTS[action], ch["name"])


# ---- territories ------------------------------------------------------------------------------------------------------
async def territory_score(ch: dict, loc: str, pts: int, st: dict):
    gid = ch.get("guild_id")
    if not gid or not st["terr_enabled"]:
        return
    if ch["level"] < int(st["terr_min_level"]) or time.time() - int(ch.get("created_at", 0)) < int(st["terr_min_age_hours"]) * 3600:
        return
    g = await col("guilds").find_one({"_id": gid}, {"members": 1})
    if not g or g.get("members", 0) < int(st["terr_min_members"]):
        return
    if not await bump_counter(f"terr:{ch['user_id']}:{day_id()}", pts, int(st["terr_daily_cap"])):
        return
    await col("territory_scores").update_one(
        {"_id": f"{week_id()}:{loc}"},
        {"$inc": {f"scores.{gid}": pts}, "$setOnInsert": {"expire_at": datetime.now(timezone.utc) + timedelta(days=60), "week": week_id(), "loc": loc}},
        upsert=True)


async def territory_income(uid: int, loc: str, coins: int, xp: int = 0):
    """Owner guild members get a small buff in their land; everyone else pays a small patrol tax into the owner's bank."""
    st = await game_settings()
    if not st["terr_enabled"] or coins <= 0:
        return None
    t_doc = await col("territories").find_one({"_id": loc})
    if not t_doc or not t_doc.get("owner"):
        return None
    ch = await get_char(uid)
    if not ch:
        return None
    if ch.get("guild_id") == t_doc["owner"]:
        bc, bx = int(coins * float(st["terr_buff_pct"])), int(xp * float(st["terr_buff_pct"]))
        if bc:
            await add_coins(uid, bc, "territory")
        if bx:
            await add_xp(uid, bx, "territory", apply_rate=False)
        return {"mine": True, "coins": bc, "xp": bx}
    tax = int(coins * float(st["terr_tax_pct"]))
    if tax > 0 and await bump_counter(f"tax:{loc}:{day_id()}", tax, int(st["terr_tax_daily_cap"])):
        await col("guilds").update_one({"_id": t_doc["owner"]}, {"$inc": {"bank": tax}})
        return {"mine": False, "tax": tax}
    return None


async def territory_board(loc: str, top: int = 3):
    """(owner doc or None, [(gid, name_fa, name_en, pts)], my-week id)."""
    owner = await col("territories").find_one({"_id": loc})
    sc = await col("territory_scores").find_one({"_id": f"{week_id()}:{loc}"}) or {}
    rows = sorted((sc.get("scores") or {}).items(), key=lambda kv: -kv[1])[:top]
    out = []
    for gid, pts in rows:
        g = await col("guilds").find_one({"_id": gid}, {"name_fa": 1, "name_en": 1})
        if g:
            out.append((gid, g["name_fa"], g["name_en"], pts))
    return owner, out


async def territory_owners() -> dict:
    return {d["_id"]: d async for d in col("territories").find({"owner": {"$ne": None}})}


async def _territory_rollover():
    ws, _ = await get_world(force=True)
    old, wk = ws.get("terr_week"), week_id()
    if old == wk:
        return []
    claim = await col("world_state").update_one({"_id": WS_ID, "terr_week": old}, {"$set": {"terr_week": wk}})
    if not claim.modified_count:
        return []
    st = await game_settings()
    changes = []
    for loc in {d["loc"] async for d in col("territory_scores").find({"week": old}, {"loc": 1})}:
        sc = await col("territory_scores").find_one({"_id": f"{old}:{loc}"}) or {}
        cur = await col("territories").find_one({"_id": loc}) or {}
        prev = cur.get("owner")
        new = terr_pick_owner(sc.get("scores") or {}, prev, int(st["terr_min_score"]))
        if not new or new == prev:
            continue
        g = await col("guilds").find_one({"_id": new}, {"name_fa": 1, "name_en": 1, "members": 1})
        if not g or g.get("members", 0) < int(st["terr_min_members"]):
            continue
        await col("territories").update_one({"_id": loc}, {"$set": {"owner": new, "owner_fa": g["name_fa"], "owner_en": g["name_en"], "since": int(time.time()),
                                                                     "week": wk}}, upsert=True)
        from data_races import LOCATIONS
        await chronicle("terr_take", guild_fa=g["name_fa"], guild_en=g["name_en"], loc_fa=LOCATIONS[loc]["fa"], loc_en=LOCATIONS[loc]["en"])
        changes.append({"loc": loc, "guild_fa": g["name_fa"], "guild_en": g["name_en"]})
    return changes


# ---- world events --------------------------------------------------------------------------------------------------------
async def event_start(kind: str):
    import uuid
    if kind not in EVENTS:
        return None
    st = await game_settings()
    eid = uuid.uuid4().hex[:10]
    claim = await col("world_state").update_one({"_id": WS_ID, "$or": [{"event_id": None}, {"event_id": {"$exists": False}}]}, {"$set": {"event_id": eid}})
    if not claim.modified_count:
        return None
    now = int(time.time())
    end = now + int(st["event_duration_minutes"]) * 60
    doc = {"_id": eid, "kind": kind, "status": "active", "start_at": now, "end_at": end, "goal": event_goal(await active_players(), st),
           "progress": 0, "contrib": {}, "nm": {}}
    await col("world_events").insert_one(doc)
    await col("world_state").update_one({"_id": WS_ID}, {"$set": {"next_event_at": end + int(st["event_min_gap_minutes"]) * 60}})
    await chronicle("event_start", ev_fa=t("fa", f"ev_{kind}_name"), ev_en=t("en", f"ev_{kind}_name"))
    invalidate()
    return doc


async def event_end(eid: str = None, force_success: bool = None):
    """Settle the active event exactly once and pay participants. Returns summary or None."""
    ws, ev = await get_world(force=True)
    if not ev or (eid and ev["_id"] != eid):
        return None
    doc = await col("world_events").find_one_and_update({"_id": ev["_id"], "status": "active"}, {"$set": {"status": "settling"}})
    if not doc:
        return None
    st = await game_settings()
    ok = doc["progress"] >= doc["goal"] if force_success is None else bool(force_success)
    contrib = {int(k): v for k, v in doc.get("contrib", {}).items()}
    n = len(contrib)
    avg = max(1.0, sum(contrib.values()) / n) if n else 1.0
    rows = []
    for rank, (uid, pts) in enumerate(sorted(contrib.items(), key=lambda kv: -kv[1])):
        ch = await get_char(uid)
        if not ch or pts < 3 or is_new_account(ch, st):
            continue
        mult = 0.6 + 0.4 * min(2.0, pts / avg)
        base = 1.0 if ok else 0.4
        lvlk = 1 + ch["level"] / 20
        xp, coins = int(float(st["event_reward_xp"]) * base * mult * lvlk), int(float(st["event_reward_coins"]) * base * mult * lvlk)
        await add_xp(uid, xp, "event", apply_rate=False)
        await add_coins(uid, coins, "event")
        prize = None
        if ok and rank < 3:
            r = RARITIES[(2, 1, 0)[rank]]
            if COSMETIC_BY_RARITY[r]:
                prize = random.choice(COSMETIC_BY_RARITY[r])
        elif ok and random.random() < 0.15 and EVO_BY_RARITY["Common"]:
            prize = random.choice(EVO_BY_RARITY["Common"] + EVO_BY_RARITY["Uncommon"])
        if prize and not await inv_add(uid, prize, 1):
            prize = None
        await season_add(uid, min(60, int(pts)) + (20 if ok else 5), ch["name"])
        rows.append({"uid": uid, "name": (doc.get("nm") or {}).get(str(uid)) or ch["name"], "pts": pts, "xp": xp, "coins": coins, "prize": prize})
    eff = EVENTS[doc["kind"]]["win" if ok else "lose"]
    await world_adjust(threat=eff["threat"], stability=eff["stability"])
    await col("world_events").update_one({"_id": doc["_id"]}, {"$set": {"status": "done", "ended_at": int(time.time()), "success": ok,
                                                                          "expire_at": datetime.now(timezone.utc) + timedelta(days=14)}})
    await col("world_state").update_one({"_id": WS_ID, "event_id": doc["_id"]}, {"$set": {"event_id": None}})
    await chronicle("event_win" if ok else "event_lose", ev_fa=t("fa", f"ev_{doc['kind']}_name"), ev_en=t("en", f"ev_{doc['kind']}_name"), n=n)
    invalidate()
    return {"doc": doc, "ok": ok, "rows": rows, "n": n}


async def event_contribute_key(uid: int, item_id: str):
    """Spend one dungeon key as an offering to the active event."""
    from data_world import KEY_PTS
    from service_economy import inv_remove
    ch = await get_char(uid)
    st = await game_settings()
    _, ev = await get_world(force=True)
    e = (ALL.get(item_id) or {}).get("effect") or {}
    if e.get("type") != "key":
        return "nokey", None
    if not ev:
        return "noevent", None
    if is_new_account(ch, st):
        return "young", None
    pts = event_pts(ev["kind"], "key", ch["location"]) * KEY_PTS.get(e["diff"], 1)
    if pts <= 0:
        return "noevent", None
    if not await bump_counter(f"evpts:{uid}:{day_id()}", pts, int(st["event_daily_pts_cap"])):
        return "cap", None
    if not await inv_remove(uid, item_id, 1):
        return "missing", None
    await col("world_events").update_one({"_id": ev["_id"], "status": "active"}, {"$inc": {"progress": pts, f"contrib.{uid}": pts}, "$set": {f"nm.{uid}": ch["name"]}})
    return "ok", pts


# ---- season ---------------------------------------------------------------------------------------------------------------------
async def season_top(sid: int, n: int = 10) -> list:
    return await col("season_scores").find({"season": sid}).sort("pts", -1).limit(n).to_list(n)


async def _season_rollover():
    ws, _ = await get_world(force=True)
    cur = ws["season"]
    now = int(time.time())
    if now < cur["end"]:
        return None
    st = await game_settings()
    new = {"id": cur["id"] + 1, "start": now, "end": now + int(st["season_days"]) * 86400}
    claim = await col("world_state").update_one({"_id": WS_ID, "season.id": cur["id"]}, {"$set": {"season": new}})
    if not claim.modified_count:
        return None
    sid = cur["id"]
    top = await season_top(sid, 10)
    pvp_top = await col("characters").find({}, {"user_id": 1, "name": 1, "rating": 1}).sort("rating", -1).limit(3).to_list(3)
    dm = []
    shares = (1.0, 0.6, 0.4)
    prize_r = ("Legendary", "Epic", "Rare")
    paid_top = set()
    for i, row in enumerate(top[:3]):
        if row["pts"] < int(st["season_min_pts"]):
            continue
        paid_top.add(row["user_id"])
        await add_coins(row["user_id"], int(int(st["season_top_coins"]) * shares[i]), "season")
        pool = COSMETIC_BY_RARITY[prize_r[i]] or COSMETIC_BY_RARITY["Rare"]
        if pool:
            await inv_add(row["user_id"], random.choice(pool), 1, force=True)
        dm.append((row["user_id"], "ssn_dm_top", {"rank": i + 1, "pts": row["pts"]}))
    for i, row in enumerate(pvp_top):
        await add_coins(row["user_id"], int(int(st["season_top_coins"]) * shares[i]), "season_pvp")
        pool = COSMETIC_BY_RARITY[prize_r[i]] or COSMETIC_BY_RARITY["Rare"]
        if pool:
            await inv_add(row["user_id"], random.choice(pool), 1, force=True)
        dm.append((row["user_id"], "ssn_dm_pvp", {"rank": i + 1, "rating": row["rating"]}))
    async for row in col("season_scores").find({"season": sid, "pts": {"$gte": int(st["season_min_pts"])}}):
        if row["user_id"] in paid_top:
            continue
        coins = int(row["pts"] * int(st["season_part_coin_per_pt"]))
        if coins:
            await add_coins(row["user_id"], coins, "season_part")
            if len(dm) < 400:
                dm.append((row["user_id"], "ssn_dm_part", {"coins": coins, "pts": row["pts"]}))
    agg = await col("characters").aggregate([{"$group": {"_id": None, "m": {"$avg": "$rating"}}}]).to_list(1)
    mean = float(agg[0]["m"]) if agg else 1000.0
    k = float(st["season_soft_reset"])
    await col("characters").update_many({}, [{"$set": {"rating": {"$toInt": {"$round": [{"$add": ["$rating", {"$multiply": [{"$subtract": [mean, "$rating"]}, k]}]}, 0]}}}}])
    await col("seasons").update_one({"id": sid}, {"$set": {"id": sid, "start": cur["start"], "end": now,
                                                              "top": [{"user_id": r["user_id"], "name": r.get("name"), "pts": r["pts"]} for r in top],
                                                              "pvp_top": [{"user_id": r["user_id"], "name": r["name"], "rating": r["rating"]} for r in pvp_top],
                                                              "mean": mean}}, upsert=True)
    await chronicle("season_end", n=sid, name=(top[0].get("name") if top else "—") or "—")
    invalidate()
    return {"season": sid, "top": top, "pvp_top": pvp_top, "dm": dm}


async def season_force_end():
    await col("world_state").update_one({"_id": WS_ID}, {"$set": {"season.end": 0}})
    invalidate()


# ---- scheduler tick -----------------------------------------------------------------------------------------------------------------
async def tick() -> dict:
    """One pass of background world logic. Returns announcements for the scheduler to broadcast."""
    out = {"event_started": None, "event_ended": None, "terr": [], "season": None, "boss_orphan": False}
    st = await game_settings()
    now = int(time.time())
    try:
        ws, ev = await get_world(force=True)
        # hourly drift: threat creeps up, stability erodes, reishi settles back to normal
        hit = await col("world_state").find_one_and_update({"_id": WS_ID, "drift_at": {"$lte": now}}, {"$set": {"drift_at": now + 3600}})
        if hit:
            threat = clamp(hit.get("threat", 20) + float(st["world_threat_drift_hour"]))
            stab = clamp(hit.get("stability", 70) - float(st["world_stab_decay_hour"]) - threat / 100 * 0.3)
            upd = {"threat": threat, "stability": stab}
            for loc, v in (hit.get("reishi") or {}).items():
                upd[f"reishi.{loc}"] = clamp(v + (REISHI_START - v) * float(st["world_reishi_decay"]))
            await col("world_state").update_one({"_id": WS_ID}, {"$set": upd})
            invalidate()
        # orphan boss slot (crash between claim and insert)
        if ws.get("boss_id"):
            alive = await col("boss_sessions").find_one({"_id": ws["boss_id"], "active": True}, {"_id": 1})
            if not alive and now - ws.get("next_boss_at", 0) > 60:
                await col("world_state").update_one({"_id": WS_ID, "boss_id": ws["boss_id"]}, {"$set": {"boss_id": None}})
        # events
        if ev and (ev["progress"] >= ev["goal"] or now >= ev["end_at"]):
            out["event_ended"] = await event_end(ev["_id"])
        elif not ev and st["event_enabled"] and ws.get("next_event_at", 0) <= now:
            kind = pick_event_kind(ws, st, random)
            if kind:
                out["event_started"] = await event_start(kind)
            else:
                await col("world_state").update_one({"_id": WS_ID}, {"$set": {"next_event_at": now + 600}})
    except Exception:
        log.exception("world tick (state) failed")
    try:
        out["terr"] = await _territory_rollover()
    except Exception:
        log.exception("territory rollover failed")
    try:
        out["season"] = await _season_rollover()
    except Exception:
        log.exception("season rollover failed")
    return out
