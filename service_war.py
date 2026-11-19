"""⚔️ Event battlefield (rules and numbers in data_war). One `wars` document per world event and one `war_members`
document per player who joined it. Every shared write is a single atomic update."""
import logging
import random
import time
from datetime import datetime, timedelta, timezone

from data_war import (FACTIONS, FIGHT_K, FRIENDLY, GENERAL_COINS, GENERAL_RELIC, GENERAL_SCALE, GENERAL_STONE,
                      GENERAL_UNLOCK_WINS, GLORY_PTS, GLORY_SECONDS, GLORY_XP, MIN_PTS_REWARD, OFFICER_CHANCE, OFFICERS,
                      OFFICER_SCALE, SHADOW_DEF_CAP, SHADOW_WINDOWS, SOLDIERS, STONE_PTS, WAR_FIGHT_CAP, WAR_PTS, WARS,
                      WIN_ITEM_CHANCE,
                      WIN_ITEM_PTS, auto_side, end_reward, faction_of, general_of, other, rally, shadow_points, shares,
                      weighed, winner, with_rally)
from database import col, game_settings, try_cooldown
from service_player import add_coins, add_xp, get_char

log = logging.getLogger("senka.war")
KEEP_DAYS = 14


def _exp():
    return datetime.now(timezone.utc) + timedelta(days=KEEP_DAYS)


def _mid(eid: str, uid: int) -> str:
    return f"{eid}:{uid}"


async def _active_event():
    from service_worldcore import get_world
    _, ev = await get_world()
    return ev if ev and ev.get("status", "active") == "active" and ev["kind"] in WARS else None


async def war_doc(ev: dict):
    """The war of this event (created the first time anyone looks at it)."""
    if not ev or ev["kind"] not in WARS:
        return None
    a, b, _ra, _rb = WARS[ev["kind"]]
    await col("wars").update_one({"_id": ev["_id"]}, {"$setOnInsert": {
        "kind": ev["kind"], "a": a, "b": b, "status": "active", "pts": {"a": 0, "b": 0}, "act": {"a": 0, "b": 0},
        "n": {"a": 0, "b": 0}, "start_at": int(ev.get("start_at", time.time())), "end_at": int(ev.get("end_at", 0)),
        "expire_at": _exp()}}, upsert=True)
    return await col("wars").find_one({"_id": ev["_id"]})


async def member(eid: str, uid: int):
    return await col("war_members").find_one({"_id": _mid(eid, uid)})


async def war_status(uid: int) -> dict:
    """Everything the battlefield panel shows. {'ev': None} when no war is on."""
    ev = await _active_event()
    if not ev:
        return {"ev": None, "last": await last_war()}
    w = await war_doc(ev)
    ch = await get_char(uid)
    m = await member(ev["_id"], uid)
    pts, act = w.get("pts") or {}, w.get("act") or {}
    side = m["side"] if m else None
    return {"ev": ev, "war": w, "me": m, "side": side, "auto": auto_side(ev["kind"], ch.get("race")), "shares": shares(pts, act),
            "rally": {s: rally(s, pts, act) for s in ("a", "b")}, "left": max(0, WAR_FIGHT_CAP - int((m or {}).get("f", 0))),
            "general": general_of(faction_of(ev["kind"], other(side)), int(ch["level"])) if side else None,
            "gen_ready": bool(m) and int(m.get("w", 0)) >= GENERAL_UNLOCK_WINS and not m.get("g"),
            "gen_done": bool(m and m.get("g")), "level": int(ch["level"])}


async def war_join(uid: int, side: str = None):
    """-> status: noevent | young | joined | choose | ok (with the side)."""
    ev = await _active_event()
    if not ev:
        return "noevent", None
    ch = await get_char(uid)
    st = await game_settings()
    from service_worldcore import is_new_account
    if not ch or is_new_account(ch, st):
        return "young", None
    w = await war_doc(ev)
    if await member(ev["_id"], uid):
        return "joined", None
    auto = auto_side(ev["kind"], ch.get("race"))
    side = auto or (side if side in ("a", "b") else None)  # the story decides when it can; a free choice is final
    if not side:
        return "choose", None
    try:
        await col("war_members").insert_one({"_id": _mid(ev["_id"], uid), "eid": ev["_id"], "uid": uid, "side": side,
                                             "name": ch["name"], "lvl": int(ch["level"]), "race": ch.get("race"), "p": 0,
                                             "w": 0, "f": 0, "d": 0, "g": False, "beat": {}, "lost": {}, "at": int(time.time()),
                                             "expire_at": _exp()})
    except Exception:  # a double tap: the unique _id already exists
        return "joined", None
    await col("wars").update_one({"_id": w["_id"]}, {"$inc": {f"n.{side}": 1}})
    return "ok", side


async def _pick_shadow(eid: str, kind: str, side: str, uid: int, level: int, rng):
    """An enemy player near this level whose shadow will fight: joined enemies first (their shadow earns them
    defence points), then any active player of the enemy's races. None when nobody fits."""
    opp = other(side)
    m = await member(eid, uid) or {}
    beat = m.get("beat") or {}
    for win in SHADOW_WINDOWS:
        cands = await col("war_members").find({"eid": eid, "side": opp, "lvl": {"$gte": level - win, "$lte": level + win}},
                                               {"uid": 1, "lvl": 1}).limit(40).to_list(40)
        cands = [c for c in cands if int(c["uid"]) != uid]
        if cands:
            fresh = [c for c in cands if int(beat.get(str(c["uid"]), 0)) < 2]  # prefer ones that still pay points
            return int(rng.choice(fresh or cands)["uid"]), True
    races = WARS[kind][2] if opp == "a" else WARS[kind][3]
    if races:
        since = int(time.time()) - 7 * 86400
        st = await game_settings()
        from service_worldcore import is_new_account
        for win in SHADOW_WINDOWS:
            cands = await col("characters").find({"race": {"$in": list(races)}, "level": {"$gte": level - win, "$lte": level + win},
                                                  "seen_at": {"$gte": since}}, {"user_id": 1, "created_at": 1}).limit(40).to_list(40)
            cands = [c for c in cands if int(c["user_id"]) != uid and not is_new_account(c, st)]
            if cands:
                return int(rng.choice(cands)["user_id"]), False
    return None, False


async def war_fight(uid: int, kind: str, lang: str):
    """Start a battlefield fight. kind: npc | shadow | general.
    -> (status, doc|info): noevent | notjoined | busy | wait | limit | locked | done | ok."""
    from service_combat import active_pve, pve_start
    ev = await _active_event()
    if not ev:
        return "noevent", None
    m = await member(ev["_id"], uid)
    if not m:
        return "notjoined", None
    from service_combat import blocking_pve
    if await blocking_pve(uid):
        return "busy", None
    if await try_cooldown(f"war:go:{uid}", 4):
        return "wait", None
    ch = await get_char(uid)
    level = int(ch["level"])
    if kind == "general":
        if int(m.get("w", 0)) < GENERAL_UNLOCK_WINS:
            return "locked", GENERAL_UNLOCK_WINS
        r = await col("war_members").update_one({"_id": m["_id"], "g": False}, {"$set": {"g": True}})
        if not r.modified_count:
            return "done", None
    r = await col("war_members").update_one({"_id": m["_id"], "f": {"$lt": WAR_FIGHT_CAP}},
                                            {"$inc": {"f": 1}, "$set": {"lvl": level, "name": ch["name"]}})
    if not r.modified_count:
        if kind == "general":  # the general's chance is not lost to a full fight count
            await col("war_members").update_one({"_id": m["_id"]}, {"$set": {"g": False}})
        return "limit", None
    side = m["side"]
    foe_fac = faction_of(ev["kind"], other(side))
    rng = random.Random()
    d = {"id": f"war:{ev['_id']}", "war": True, "eid": ev["_id"], "wk": ev["kind"], "side": side, "fac": foe_fac,
         "stage": 1, "total": 1, "diff": "normal"}
    if kind == "shadow":
        tuid, joined = await _pick_shadow(ev["_id"], ev["kind"], side, uid, level, rng)
        if tuid:
            tch = await get_char(tuid)
            d.update(kind="shadow", tgt=tuid, tj=joined, tname=tch["name"] if tch else "?", tlvl=int((tch or {}).get("level", level)))
        else:  # nobody of the enemy near this level: one of their officers steps up instead
            d.update(kind="officer", nofoe=True)
    elif kind == "general":
        d.update(kind="general", gen=list(general_of(foe_fac, level)))
    else:
        d.update(kind="officer" if rng.random() < OFFICER_CHANCE else "npc")
    doc = await pve_start(uid, lang, dungeon=d)
    return "ok", doc


def war_foe(d: dict, level: int, lang: str, rng):
    """(level, name, scale, sig race, (fa, en)) of a battlefield NPC. Shadows are built from the player in service_combat."""
    fac = d["fac"]
    sig_race = FACTIONS[fac][3]
    if d["kind"] == "general":
        pick = tuple(d["gen"])
        return level + 2, "👑 " + pick[0 if lang == "fa" else 1], GENERAL_SCALE, sig_race, pick
    if d["kind"] == "officer":
        pick = OFFICERS[fac]
        return level + 1, "🎖 " + pick[0 if lang == "fa" else 1], OFFICER_SCALE, sig_race, pick
    pick = rng.choice(SOLDIERS[fac])
    return max(1, level + rng.randint(-1, 1)), FACTIONS[fac][2] + " " + pick[0 if lang == "fa" else 1], 1.0, sig_race, pick


def fight_k(d: dict):
    return FIGHT_K.get(d.get("kind"), (1.0, 1.0))


async def _event_points(uid: int, eid: str, name: str, pts: int):
    """Battlefield points also push the world event forward (no daily cap: only dungeon keys are capped)."""
    if pts <= 0:
        return
    got = int(pts)
    if got:
        await col("world_events").update_one({"_id": eid, "status": "active"},
                                             {"$inc": {"progress": got, f"contrib.{uid}": got}, "$set": {f"nm.{uid}": name}})


async def war_after_fight(uid: int, doc: dict, win: bool) -> dict:
    """Settle one battlefield fight for the war. Never raises (the fight's own reward must not depend on it)."""
    try:
        return await _after(uid, doc, win)
    except Exception:
        log.exception("war settle failed for %s", uid)
        return {}


async def _after(uid: int, doc: dict, win: bool) -> dict:
    d = doc.get("dungeon") or {}
    eid, kind = d.get("eid"), d.get("kind")
    w = await col("wars").find_one({"_id": eid})
    out = {"kind": kind, "pts": 0, "fac": d.get("fac"), "closed": False}
    if not w or w.get("status") != "active":
        out["closed"] = True  # the war ended while this fight was on: the fight still pays, the war is over
        return out
    m = await member(eid, uid)
    if not m:
        return out
    side = m["side"]
    out["my_fac"] = faction_of(w["kind"], side)
    if not win:
        if kind == "shadow" and d.get("tj"):  # the enemy's shadow held its ground: a point for its owner's side
            tkey = str(int(d["tgt"]))
            me = await col("war_members").find_one_and_update({"_id": m["_id"]}, {"$inc": {f"lost.{tkey}": 1}})
            if int(((me or {}).get("lost") or {}).get(tkey, 0)) < 2:  # losing to the same shadow again and again scores nothing more
                tm = await col("war_members").find_one_and_update({"_id": _mid(eid, int(d["tgt"])), "d": {"$lt": SHADOW_DEF_CAP}},
                                                                  {"$inc": {"d": 1, "p": 1}})
                if tm:
                    winc = {f"pts.{tm['side']}": 1}
                    if int(tm.get("p", 0)) == 0:  # their first point: they now count as an active fighter
                        winc[f"act.{tm['side']}"] = 1
                    await col("wars").update_one({"_id": eid, "status": "active"}, {"$inc": winc})
                    out["def_to"] = d.get("tname")
        return out
    if kind == "shadow":
        tkey = str(int(d["tgt"]))
        before = int((m.get("beat") or {}).get(tkey, 0))
        pts = shadow_points(int(m.get("lvl", 1)), int(d.get("tlvl", 1)), before)
        out["repeat"] = before
    else:
        pts = WAR_PTS.get(kind, 1)
    out["rally"] = rally(side, w.get("pts") or {}, w.get("act") or {})
    pts = with_rally(pts, out["rally"])
    inc = {"w": 1, "p": pts}
    if kind == "shadow":
        inc[f"beat.{int(d['tgt'])}"] = 1
    prev = await col("war_members").find_one_and_update({"_id": m["_id"]}, {"$inc": inc})
    winc = {f"pts.{side}": pts}
    if prev and int(prev.get("p", 0)) == 0:  # first point: this player now counts as active for the population balance
        winc[f"act.{side}"] = 1
    await col("wars").update_one({"_id": eid, "status": "active"}, {"$inc": winc})
    out["pts"] = pts
    out["total"] = int((prev or {}).get("p", 0)) + pts
    if kind == "general":
        out["loot"] = await _general_loot(uid, int(m.get("lvl", 1)))
    await _event_points(uid, eid, m.get("name", "?"), pts)
    if int((prev or {}).get("w", 0)) + 1 == GENERAL_UNLOCK_WINS:
        out["gen_open"] = True
    return out


async def _general_loot(uid: int, level: int) -> dict:
    from data_extras2 import TEMPER_STONE
    from data_items import EVO_BY_RARITY
    from service_economy import inv_add
    coins = int(GENERAL_COINS * (1 + level / 10))
    await add_coins(uid, coins, "war_general")
    items = []
    if random.random() < GENERAL_RELIC and (EVO_BY_RARITY.get("Rare") or EVO_BY_RARITY.get("Uncommon")):
        items.append(random.choice(EVO_BY_RARITY.get("Rare") or EVO_BY_RARITY["Uncommon"]))
    if random.random() < GENERAL_STONE:
        items.append(TEMPER_STONE)
    for i in items:
        await inv_add(uid, i, 1, force=True)
    return {"coins": coins, "items": items}


async def war_top(eid: str, side: str, n: int = 5) -> list:
    return await col("war_members").find({"eid": eid, "side": side}, {"name": 1, "p": 1, "uid": 1}).sort("p", -1).limit(n).to_list(n)


async def last_war():
    docs = await col("wars").find({"status": "done"}).sort("ended_at", -1).limit(1).to_list(1)
    return docs[0] if docs else None


async def war_settle(ev_doc: dict):
    """Close the war of an ending event exactly once and pay its fighters. Returns a summary or None."""
    if not ev_doc or ev_doc.get("kind") not in WARS:
        return None
    w = await col("wars").find_one_and_update({"_id": ev_doc["_id"], "status": "active"}, {"$set": {"status": "settling"}})
    if not w:
        return None
    pts, act = w.get("pts") or {}, w.get("act") or {}
    win = winner(pts, act)
    sh = shares(pts, act)
    friendly = w["kind"] in FRIENDLY
    members = await col("war_members").find({"eid": w["_id"]}).to_list(None)
    by_side = {"a": sorted([m for m in members if m["side"] == "a"], key=lambda m: -int(m.get("p", 0))),
               "b": sorted([m for m in members if m["side"] == "b"], key=lambda m: -int(m.get("p", 0)))}
    from data_extras2 import TEMPER_STONE
    from service_economy import inv_add, roll_drop
    rows = []
    now = int(time.time())
    for side, ms in by_side.items():
        scored = [int(m.get("p", 0)) for m in ms if int(m.get("p", 0)) >= MIN_PTS_REWARD]
        avg = sum(scored) / len(scored) if scored else 1.0
        result = "draw" if win is None else "win" if side == win else ("friendly_lose" if friendly else "lose")
        for rank, m in enumerate(ms):
            p = int(m.get("p", 0))
            if p < MIN_PTS_REWARD:
                continue
            uid = int(m["uid"])
            ch = await get_char(uid)
            if not ch:
                continue
            xp, coins = end_reward(int(ch["level"]), p, avg, result)
            items = []
            try:
                await add_xp(uid, xp, "war", apply_rate=False)
                await add_coins(uid, coins, "war")
                if result == "win":
                    if p >= STONE_PTS:  # stones need a real contribution (a lone fighter with 2 points gets none)
                        items += [TEMPER_STONE] * (2 if rank == 0 else 1 if rank < 3 else 0)
                    if p >= WIN_ITEM_PTS and random.random() < WIN_ITEM_CHANCE:
                        items.append(await roll_drop(uid, source_mult=2.0, floor_idx=3))
                    if p >= GLORY_PTS:  # faction glory: +5% XP for a day (a stronger XP buff already running is kept)
                        old = (ch.get("buffs") or {}).get("xp") or {}
                        if not (old.get("until", 0) > now and float(old.get("pct", 0)) >= GLORY_XP):
                            await col("characters").update_one({"user_id": uid}, {"$set": {"buffs.xp": {"pct": GLORY_XP, "until": now + GLORY_SECONDS}}})
                elif rank == 0 and p >= STONE_PTS:  # the best fighter of the other side is not sent home empty-handed
                    items.append(TEMPER_STONE)
                for i in items:
                    await inv_add(uid, i, 1, force=True)
                await col("characters").update_one({"user_id": uid}, {"$inc": {"war_fought": 1, **({"war_won": 1} if result == "win" else {})}})
            except Exception:
                log.exception("war reward failed for %s", uid)
            rows.append({"uid": uid, "side": side, "rank": rank, "pts": p, "xp": xp, "coins": coins, "items": items, "result": result,
                         "d": int(m.get("d", 0))})
    top = {s: [(m.get("name", "?"), int(m.get("p", 0))) for m in by_side[s][:3]] for s in ("a", "b")}
    await col("wars").update_one({"_id": w["_id"]}, {"$set": {"status": "done", "ended_at": now, "winner": win, "shares": sh,
                                                              "weighed": weighed(pts, act), "top": top,
                                                              "expire_at": _exp()}})
    return {"kind": w["kind"], "a": w["a"], "b": w["b"], "winner": win, "shares": sh, "pts": pts, "act": act, "top": top,
            "rows": rows, "n": len(members)}
