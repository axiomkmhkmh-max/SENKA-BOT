"""PvE, dungeons and PvP built on the pure engine. All outcomes are server-side."""
import asyncio
import logging
import random
import time
import uuid
from datetime import datetime, timedelta, timezone

from data_crafting import player_bonus, tagged_name, temper_def
from data_items import ALL, EVO_BY_RARITY
from data_races import DIFFICULTY, DUNGEONS, LOCATIONS, RACES, soft_stat
from data_weapons import ELEMENTS, RARITIES
from data_crafting import DIFFS
import engine as E
from database import col, game_settings
from service_log import log_event
from service_economy import gacha_doc, inv_remove, party_bonus, roll_drop, inv_add
from service_player import add_coins, add_xp, bump_quest, get_char, max_hp, max_reiatsu
from service_worldcore import mods_for

_bg_tasks: set = set()


def _bg(coro):
    """Fire-and-forget for bookkeeping the player does not wait for (world points, battle log)."""
    task = asyncio.ensure_future(coro)
    _bg_tasks.add(task)

    def _done(t):
        _bg_tasks.discard(t)
        if not t.cancelled() and t.exception():
            logging.getLogger("senka.combat").error("background task failed", exc_info=t.exception())
    task.add_done_callback(_done)


ENEMY_K = {"s": 1.6, "d": 1.2, "h0": 60, "h1": 30, "a": 2.6, "ar": 0.9}
RANKS = [(0, "E"), (1100, "D"), (1250, "C"), (1400, "B"), (1600, "A"), (1850, "S"), (2150, "SS"), (2500, "SSS")]


def rank_letter(rating: int) -> str:
    out = "E"
    for thr, name in RANKS:
        if rating >= thr:
            out = name
    return out


def rank_label(rating: int, lang: str) -> str:
    from i18n import t
    letter = rank_letter(rating)
    return f"{letter} · {t(lang, 'rank_' + letter)}"


def _exp():
    return datetime.now(timezone.utc) + timedelta(hours=2)


async def build_player(ch: dict, name: str = None):
    race = RACES[ch["race"]]
    gs = await game_settings()
    stats = dict(ch["stats"])
    armor = 0
    for f in ("armor_id", "acc_id", "charm_id"):
        it = ALL.get(ch.get(f) or "")
        if not it:
            continue
        d = it["stats"].get("def", 0)
        if f == "armor_id" and d:
            d = temper_def(d, (ch.get("armor_plus") or {}).get(it["_id"], 0), gs)
        armor += d
        if "stat" in it["stats"]:
            stats[it["stats"]["stat"]] += it["stats"]["bonus"]
    g = await gacha_doc(ch["user_id"])
    pb = party_bonus(ch.get("party", []), g.get("chars", {}))
    bn = player_bonus(ch, ALL, gs)  # evolution, pet role, relics, temporary buffs
    mods = dict(race["mods"])
    # Persistent race evolution modifies the existing combat model; no parallel stats engine.
    rp = ch.get("race_progress") or {}
    stage = max(0, min(4, int(rp.get("stage", 0))))
    race_stage_mods = {
        "shinigami": {"dmg": 0.025, "kido": 0.025},
        "hollow": {"hp": 0.035, "dmg": 0.02},
        "arrancar": {"def": 0.025, "dmg": 0.025},
        "quincy": {"pierce": 0.025, "kido": 0.02},
        "visored": {"dmg": 0.02, "def": 0.02},
        "fullbringer": {"crit": 0.008, "dmg": 0.015},
        "human": {"xp": 0.01},
    }.get(ch.get("race"), {})
    for key, per_stage in race_stage_mods.items():
        if key in ("dmg", "def", "hp", "kido", "pierce"):
            mods[key] = mods.get(key, 1.0) * (1 + per_stage * stage)
        elif key == "crit":
            mods[key] = mods.get(key, 0.0) + per_stage * stage
    mods["dmg"] = mods.get("dmg", 1.0) * (1 + pb.get("dmg", 0) + bn["dmg"])
    mods["def"] = mods.get("def", 1.0) * (1 + pb.get("def", 0) + bn["def"])
    # Preserve race/evolution Kidō modifiers while adding companion bonuses.
    mods["kido"] = mods.get("kido", 1.0) * (1 + pb.get("kido", 0))
    mods["crit"] = mods.get("crit", 0) + bn["crit"]
    mods["regen"] = bn["regen"]
    hp = max_hp(ch["level"], soft_stat(stats["hakuda"]), mods.get("hp", 1.0))
    re = max_reiatsu(ch["level"], soft_stat(stats["reiatsu"]))
    wid = ch.get("weapon_id") or ""
    w = ALL.get(wid)
    if w:
        plus = (ch.get("weapon_plus") or {}).get(wid, 0)
        w = dict(w, attack=w["attack"] * (1 + 0.06 * plus))
    zstate = ch.get("zanpakuto") or {}
    bond = max(int((ch.get("bond") or {}).get(wid, 0)), int(zstate.get("bond", 0)))
    # Release stages feed the existing weapon-skill multiplier; no parallel combat engine.
    release_bonus = 0.10 if zstate.get("shikai") else 0.0
    if zstate.get("bankai"):
        release_bonus += 0.12 + min(0.08, int(zstate.get("mastery", 0)) / 500)
    zmult = 1 + min(0.30, bond / 500) + release_bonus
    # Distinct release identities alter battle style rather than granting identical flat power.
    blade_style = {
        "zangetsu": {"dmg": 1.08}, "senbonzakura": {"crit": 0.05},
        "hyorinmaru": {"def": 1.08}, "kyoka_suigetsu": {"crit": 0.04, "dmg": 1.03},
        "zanka_no_tachi": {"dmg": 1.12}, "sode_no_shirayuki": {"def": 1.05, "kido": 1.08},
        "zabimaru": {"dmg": 1.07}, "wabisuke": {"def": 1.10},
    }.get(zstate.get("blade_id"), {})
    if zstate.get("shikai") or zstate.get("bankai"):
        for stat, value in blade_style.items():
            if stat in ("dmg", "def", "kido"):
                mods[stat] = mods.get(stat, 1.0) * value
            elif stat == "crit":
                mods[stat] = mods.get(stat, 0.0) + value
    # Spells available in combat = the character's stored Hadō/Bakudō lists (race starter spells + anything
    # learned; learn_kido writes to both) merged with kido_learned. Starting from an empty set would strip
    # every existing character of their spells, because the engine only defaults when the key is missing.
    from service_bleach_systems import KIDO
    legacy = ch.get("kido") or {}
    had, bak, kaido = set(legacy.get("had") or [1]), set(legacy.get("bak") or [1]), set()
    for spell_id in set(ch.get("kido_learned") or []):
        spell = KIDO.get(spell_id)
        if not spell:
            continue
        if spell["type"] == "Hadō":
            had.add(int(spell_id.replace("hado", "")))
        elif spell["type"] == "Bakudō":
            bak.add(int(spell_id.replace("bakudo", "")))
        elif spell["type"] == "Kaidō":
            kaido.add(spell_id)
    combat_kido = {"had": sorted(had), "bak": sorted(bak), "kaido": sorted(kaido)}
    return E.new_fighter(name or tagged_name(ch, ALL), ch["level"], stats, hp, re, w, armor=armor, mods=mods, kido=combat_kido,
                         race=ch["race"], zmult=zmult)


def make_enemy(level: int, scale: float, name: str, rng=random):
    k = ENEMY_K
    s = (4 + level * k["s"]) * scale
    stats = {"zanjutsu": s, "kido": s * 0.6, "hakuda": (4 + level * k["d"]) * scale, "hoho": 6 + level * 0.5, "reiatsu": 5 + level}
    w = {"attack": (3 + level * k["a"]) * scale, "crit": 0.03, "element": rng.choice(ELEMENTS), "skills": [], "weapon_type": "melee"}
    return E.new_fighter(name, level, stats, (k["h0"] + level * k["h1"]) * scale, 80 + level * 10, w,
                         armor=level * k["ar"] * scale, ai=True)


def _rewards(level: int, scale: float, st: dict):
    xp = (20 * level ** 1.25 + 20) * (scale if scale > 1 else 1.0)
    coins = (10 + 6 * level) * (scale if scale > 1 else 1.0) * float(st["coin_rate"])
    return int(xp), int(coins)


# ---- PvE ---------------------------------------------------------------------------
async def active_pve(uid: int):
    return await col("battles").find_one({"user_id": uid, "mode": "pve", "status": "active"})


async def pve_start(uid: int, lang: str, scale: float = 1.0, dungeon: dict = None, carry: dict = None, trial: dict = None):
    ch = await get_char(uid)
    gs = await game_settings()
    wm = await mods_for(ch["location"])
    rng = random.Random()
    loc = LOCATIONS[ch["location"]]
    pick = rng.choice(loc["enemies"])
    name = pick[0 if lang == "fa" else 1]
    lvl = max(1, ch["level"] + rng.randint(-1, 1))
    tower = bool(dungeon and dungeon.get("tower"))
    if tower:  # Soul Tower: endless floors, a Warden every 5th
        from data_extras import TOWER_BOSS_EVERY, TOWER_ENEMIES
        floor = int(dungeon["stage"])
        scale = 0.85 * (1.045 ** (floor - 1))
        name = rng.choice(TOWER_ENEMIES)[0 if lang == "fa" else 1]
        if floor % TOWER_BOSS_EVERY == 0:
            scale *= 1.5
            name = "👑 " + name
    elif dungeon:
        stage, total = dungeon["stage"], dungeon["total"]
        mult = DIFFICULTY[dungeon["diff"]] * (1 + 0.12 * (stage - 1))
        if stage == total:
            mult *= 1.6
            name = "👑 " + name
        elif stage == max(2, total // 2):
            mult *= 1.3
            name = "⚔️ " + name
        scale = mult
    elite = (not dungeon) and (not trial) and rng.random() < 0.15
    if elite:
        scale, name = 1.4, "💀 " + name
    if trial:
        scale, name = float(gs["evo_trial_scale"]) * (1 + 0.2 * (trial["stage"] - 1)), "🌀 " + name
    elif not tower:
        scale *= wm["enemy"]  # Hollow Threat + active world event strengthen every enemy
    player = await build_player(ch)
    if carry:
        player["hp"] = max(1, int(player["max_hp"] * carry["hp"]))
        player["re"] = max(0, int(player["max_re"] * carry["re"]))
    state = E.new_state(player, make_enemy(lvl, scale, name, rng), rng)
    E.run_ai(state, rng)
    doc = {"sid": uuid.uuid4().hex[:8], "user_id": uid, "mode": "pve", "state": state, "status": "active", "rev": 0,
           "created_at": int(time.time()), "expire_at": _exp(), "scale": scale, "elite": elite, "lvl": lvl,
           "dungeon": dungeon, "trial": trial, "loc": ch["location"], "lang": lang}
    await col("battles").insert_one(doc)
    return doc


async def _save(doc: dict, state: dict, extra: dict = None):
    upd = {"state": state, "rev": doc["rev"] + 1, "expire_at": _exp()}
    upd.update(extra or {})
    r = await col("battles").update_one({"sid": doc["sid"], "rev": doc["rev"], "status": "active"}, {"$set": upd})
    return bool(r.modified_count)


async def pve_act(uid: int, sid: str, action: str, potion: dict = None):
    doc = await col("battles").find_one({"sid": sid, "user_id": uid, "mode": "pve"})
    if not doc or doc["status"] != "active":
        return "gone", None, None
    st = doc["state"]
    if st["cur"] != "a" or not st.get("awaiting"):
        return "notturn", None, None
    rng = random.Random()
    if action == "pot" and potion:
        ev = E.do_potion(st, potion["type"], potion["pct"])
    else:
        ev = E.do_action(st, action, rng)
    ev += E.run_ai(st, rng)
    if not await _save(doc, st):
        return "stale", None, None
    doc["state"], doc["rev"] = st, doc["rev"] + 1
    outcome = await pve_settle(doc) if st["done"] else None
    return "ok", doc, (ev, outcome)


async def pve_settle(doc: dict):
    won = await col("battles").find_one_and_update({"sid": doc["sid"], "status": "active"}, {"$set": {"status": "done"}})
    if not won:
        return None
    uid, st = doc["user_id"], doc["state"]
    gs = await game_settings()
    win = st["winner"] == "a"
    out = {"win": win, "xp": 0, "coins": 0, "drop": None, "levels": 0, "next": None, "dungeon_done": False}
    now = int(time.time())
    if (doc.get("dungeon") or {}).get("tower"):
        from service_extras import tower_settle
        out = await tower_settle(doc, win)
        await col("battle_logs").insert_one({"user_id": uid, "mode": "tower", "win": win, "lvl": doc["lvl"], "at": now})
        return out
    if win:
        xp, coins = _rewards(doc["lvl"], doc["scale"], gs)
        d = doc.get("dungeon")
        plain = not d and not doc.get("trial")
        if plain:  # win chain: consecutive plain victories raise coin/XP rewards
            from service_extras import chain_win
            cn, cm, cdrop = await chain_win(uid)
            xp, coins = int(xp * cm), int(coins * cm)
            out["chain"] = {"n": cn, "pct": round((cm - 1) * 100), "item": cdrop}
        if d and d["stage"] == d["total"]:
            xp, coins = xp * 3, coins * 3
        wm = await mods_for(doc["loc"])
        coins = int(coins * wm["coin"])
        ch0 = await get_char(uid)
        coins = int(coins * (1 + player_bonus(ch0, ALL, gs)["coin"]))
        ch, lv, got = await add_xp(uid, xp, "pve")
        # independent writes: run together instead of one after another
        await asyncio.gather(add_coins(uid, coins, "pve"),
                             col("characters").update_one({"user_id": uid}, {"$inc": {"wins": 1, f"bond.{(ch or {}).get('weapon_id') or 'none'}": 1, **({"race_progress.hunts": 1} if (ch or {}).get("race") in ("hollow", "arrancar") else {})}}),
                             bump_quest(uid, "battle_win", 1))
        out.update(xp=got, coins=coins, levels=lv)
        from service_worldstate import on_action, territory_income
        out["terr"] = await territory_income(uid, doc["loc"], coins, xp)
        chance = 1.0 if (doc["elite"] or (d and d["stage"] == d["total"])) else 0.35
        if random.random() < chance:
            iid = await roll_drop(uid, source_mult=2.0 if doc["elite"] else 1.0, floor_idx=2 if (d and d["stage"] == d["total"]) else 0)
            if await inv_add(uid, iid, 1):
                out["drop"] = iid
        if d and d["stage"] < d["total"]:
            f = st["a"]
            nxt = await pve_start(uid, doc.get("lang", "en"), dungeon={**d, "stage": d["stage"] + 1},
                                  carry={"hp": f["hp"] / f["max_hp"], "re": f["re"] / f["max_re"]})
            out["next"] = nxt["sid"]
        elif d:
            out["dungeon_done"] = True
            await bump_quest(uid, "dungeon_clear", 1)
            di = DIFFS.index(d["diff"]) if d["diff"] in DIFFS else 0
            if random.random() < 0.20 + 0.08 * di:  # evolution fuel comes from the deep places
                pool = EVO_BY_RARITY[RARITIES[min(3, max(0, di - (1 if random.random() < 0.5 else 0)))]] or EVO_BY_RARITY["Common"]
                eid = random.choice(pool)
                if await inv_add(uid, eid, 1):
                    out["bonus_drop"] = eid
        if doc.get("trial"):
            from service_crafting import evo_complete
            out["evo"] = await evo_complete(uid, doc["trial"]["stage"])
        _bg(on_action(uid, "dungeon_clear" if out["dungeon_done"] else "elite_win" if doc["elite"] else "pve_win", doc["loc"]))
    else:
        await col("characters").update_one({"user_id": uid}, {"$inc": {"losses": 1}})
        if not doc.get("dungeon") and not doc.get("trial"):
            from service_extras import chain_break
            lost = await chain_break(uid)
            if lost >= 2:
                out["chain_lost"] = lost
        from service_worldstate import on_action
        _bg(on_action(uid, "pve_loss", doc["loc"]))
    _bg(col("battle_logs").insert_one({"user_id": uid, "mode": "pve", "win": win, "lvl": doc["lvl"], "at": now}))
    return out


async def start_dungeon(uid: int, lang: str, dungeon_id: str, diff: str):
    ch = await get_char(uid)
    d = DUNGEONS[dungeon_id]
    if ch["level"] < d["level"]:
        return "level", None
    if await active_pve(uid):
        return "busy", None
    if diff != "normal":
        key = next((i for i, x in ALL.items() if x.get("effect") and x["effect"].get("type") == "key"
                    and x["effect"]["dungeon"] == dungeon_id and x["effect"]["diff"] == diff), None)
        if not key or not await inv_remove(uid, key, 1):
            return "key", None
    doc = await pve_start(uid, lang, dungeon={"id": dungeon_id, "stage": 1, "total": d["stages"], "diff": diff})
    return "ok", doc


# ---- PvP -----------------------------------------------------------------------------
def _pair(a: int, b: int) -> str:
    return f"{min(a, b)}:{max(a, b)}"


async def duel_busy(uid: int) -> bool:
    return bool(await col("battles").find_one({"mode": "pvp", "status": {"$in": ["pending", "active"]}, "$or": [{"a_uid": uid}, {"b_uid": uid}]}))


async def duel_challenge(chat_id: int, a_uid: int, b_uid: int, ranked: bool):
    gs = await game_settings()
    if a_uid == b_uid:
        return "self", None
    ca, cb = await get_char(a_uid), await get_char(b_uid)
    if not ca:
        return "noreg", None
    if not cb:
        return "opp_noreg", None
    if ranked and (ca["level"] < int(gs["pvp_min_level"]) or cb["level"] < int(gs["pvp_min_level"])):
        return "minlevel", int(gs["pvp_min_level"])
    if await duel_busy(a_uid) or await duel_busy(b_uid):
        return "busy", None
    doc = {"sid": uuid.uuid4().hex[:8], "mode": "pvp", "a_uid": a_uid, "b_uid": b_uid, "ranked": ranked, "chat_id": chat_id,
           "status": "pending", "rev": 0, "created_at": int(time.time()), "expire_at": datetime.now(timezone.utc) + timedelta(minutes=5),
           "a_name": ca["name"], "b_name": cb["name"], "timeouts": {"a": 0, "b": 0}}
    await col("battles").insert_one(doc)
    return "ok", doc


async def duel_accept(sid: str, uid: int):
    gs = await game_settings()
    doc = await col("battles").find_one({"sid": sid, "mode": "pvp", "status": "pending", "b_uid": uid})
    if not doc:
        return None
    ca, cb = await get_char(doc["a_uid"]), await get_char(uid)
    fa, fb = await build_player(ca), await build_player(cb)
    rng = random.Random()
    state = E.new_state(fa, fb, rng)
    E.run_ai(state, rng, ai_sides=())
    r = await col("battles").update_one({"sid": sid, "status": "pending"}, {"$set": {
        "status": "active", "state": state, "rev": 1, "deadline": int(time.time()) + int(gs["pvp_turn_seconds"]),
        "expire_at": _exp(), "started_at": int(time.time())}})
    return await col("battles").find_one({"sid": sid}) if r.modified_count else None


async def duel_decline(sid: str, uid: int):
    r = await col("battles").update_one({"sid": sid, "mode": "pvp", "status": "pending", "b_uid": uid}, {"$set": {"status": "declined"}})
    return bool(r.modified_count)


async def pvp_act(uid: int, sid: str, action: str, forced: str = None):
    gs = await game_settings()
    doc = await col("battles").find_one({"sid": sid, "mode": "pvp", "status": "active"})
    if not doc:
        return "gone", None, None
    st = doc["state"]
    side = "a" if uid == doc["a_uid"] else "b" if uid == doc["b_uid"] else forced
    if side is None:
        return "notplayer", None, None
    if st["cur"] != side or not st.get("awaiting"):
        return "notturn", None, None
    rng = random.Random()
    ev = E.do_action(st, action, rng, int(gs["pvp_max_turns"]))
    ev += E.run_ai(st, rng, int(gs["pvp_max_turns"]), ai_sides=())
    upd = {"deadline": int(time.time()) + int(gs["pvp_turn_seconds"]), f"timeouts.{side}": 0 if forced is None else doc["timeouts"][side] + 1}
    if not await _save(doc, st, upd):
        return "stale", None, None
    doc["state"], doc["rev"] = st, doc["rev"] + 1
    outcome = await pvp_settle(doc) if st["done"] else None
    return "ok", doc, (ev, outcome)


async def pvp_timeouts():
    """Called by the scheduler: auto-guard stalled turns, forfeit after 3 in a row."""
    now = int(time.time())
    out = []
    async for d in col("battles").find({"mode": "pvp", "status": "active", "deadline": {"$lte": now}}).limit(50):
        side = d["state"]["cur"]
        uid = d["a_uid"] if side == "a" else d["b_uid"]
        if d["timeouts"][side] + 1 >= 3:
            st = d["state"]
            st[side]["hp"] = 0
            st["done"], st["winner"] = True, "b" if side == "a" else "a"
            if await _save(d, st):
                d["state"], d["rev"] = st, d["rev"] + 1
                out.append((d, [], await pvp_settle(d), True))
            continue
        res, doc, data = await pvp_act(uid, d["sid"], "df", forced=side)
        if res == "ok":
            out.append((doc, data[0], data[1], False))
    return out


async def pvp_settle(doc: dict):
    claimed = await col("battles").find_one_and_update({"sid": doc["sid"], "status": "active"}, {"$set": {"status": "done"}})
    if not claimed:
        return None
    gs = await game_settings()
    st = doc["state"]
    now = int(time.time())
    a_uid, b_uid = doc["a_uid"], doc["b_uid"]
    res = {"winner": None, "draw": st["winner"] == "draw", "rating": {}, "xp": {}, "note": None}
    if res["draw"]:
        return res
    w_uid, l_uid = (a_uid, b_uid) if st["winner"] == "a" else (b_uid, a_uid)
    cw, cl = await get_char(w_uid), await get_char(l_uid)
    res["winner"] = w_uid
    pair = _pair(a_uid, b_uid)
    note = None
    if doc["ranked"]:
        pair_n = await col("battle_logs").count_documents({"pair": pair, "rated": True, "at": {"$gte": now - 86400}})
        if pair_n >= int(gs["pvp_pair_daily_cap"]):
            note = "pair_cap"
        elif abs(cw["level"] - cl["level"]) > 10:
            note = "level_gap"
        elif now - cw["created_at"] < 3600 or now - cl["created_at"] < 3600:
            note = "new_account"
    rated = doc["ranked"] and not note
    if rated:
        diff = (cl["rating"] - cw["rating"]) / 800
        gain = int(random.randint(int(gs["pvp_gain_min"]), int(gs["pvp_gain_max"])) * max(0.6, min(1.5, 1 + diff)))
        loss = int(random.randint(int(gs["pvp_loss_min"]), int(gs["pvp_loss_max"])) * max(0.6, min(1.5, 1 - diff)))
        new_l = max(0, cl["rating"] - loss)
        await col("characters").update_one({"user_id": w_uid}, {"$inc": {"rating": gain, "pvp_w": 1}})
        await col("characters").update_one({"user_id": l_uid}, {"$set": {"rating": new_l}, "$inc": {"pvp_l": 1}})
        res["rating"] = {w_uid: (cw["rating"] + gain, gain), l_uid: (new_l, -(cl["rating"] - new_l))}
    log_event("pvp", w_uid, f"دوئل {'رنکد' if doc['ranked'] else 'دوستانه'}: برد مقابل {cl['name']} ({l_uid})" + (f" | رتبه {res['rating'][w_uid][1]:+d}" if rated else (f" | بدون امتیاز ({note})" if note else "")),
              loser=l_uid, ranked=bool(doc["ranked"]))
    wins_today = await col("battle_logs").count_documents({"user_id": w_uid, "mode": "pvp", "win": True, "at": {"$gte": now - 86400}})
    frac = 1.0 if wins_today < int(gs["pvp_full_xp_wins"]) else 0.3
    if note != "pair_cap":
        xp = int((30 + cw["level"] * 8) * frac)
        _, _, got = await add_xp(w_uid, xp, "pvp")
        await add_coins(w_uid, int((60 + cw["level"] * 4) * float(gs["coin_rate"]) * frac), "pvp")
        res["xp"][w_uid] = got
        await bump_quest(w_uid, "pvp_win", 1)
    res["note"] = note
    from service_interact import claim_bounty
    from service_worldstate import on_action
    await on_action(w_uid, "pvp_win", cw["location"])
    if doc["ranked"] and note not in ("pair_cap", "new_account", "level_gap"):
        res["bounty"] = await claim_bounty(w_uid, l_uid)
    base = {"mode": "pvp", "pair": pair, "rated": rated, "at": now}
    await col("battle_logs").insert_many([{**base, "user_id": w_uid, "opp": l_uid, "win": True},
                                          {**base, "user_id": l_uid, "opp": w_uid, "win": False}])
    return res
