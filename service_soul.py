"""Nov 24 soul systems: Awakened stats, Inner World duel, Urahara training, Human World patrol, Gikongan farming,
the Dangai run (Kototsu) and Reiatsu Clash.

Rules are kept here (pure helpers are testable without the DB); handlers_soul only renders them.
Every timed system stores one small document per player in `soul` ({user_id, <system>: {...}}).
"""
import random
import time

from database import col
from data_races import STATS, soft_stat

# ---- Awakened stats (level 300+) --------------------------------------------------------------------------------
AWK_LEVEL = 300   # from this level two stats can be Awakened
AWK_SLOTS = 2     # how many
AWK_PER_LEVEL = 1  # an Awakened stat's cap grows this much per level past AWK_LEVEL


def stat_cap(ch: dict, stat: str, base_max: int) -> int:
    """The most points this stat can hold: base cap, plus the Awakened growth for the two chosen stats past level 300."""
    lvl = int((ch or {}).get("level", 1))
    if stat in ((ch or {}).get("awk_stats") or []) and lvl > AWK_LEVEL:
        return int(base_max) + (lvl - AWK_LEVEL) * AWK_PER_LEVEL
    return int(base_max)


# ---- timings and rewards -----------------------------------------------------------------------------------------
INNER_CD = 7 * 86400          # Inner World duel: once a week
URAHARA_HOURS = 72            # Urahara training length
URAHARA_CD = 4 * 86400        # wait after claiming
URAHARA_PTS = 6               # stat points it pays
HUMAN_HOURS = 4               # Human World patrol length
HUMAN_GROUP_WINDOW = 1800     # others in the same chat can join for 30 minutes
HUMAN_GROUP_BONUS = 0.15      # +15% per extra member (at most 5 members)
GIKONGAN_ID = "it_d002"       # the dungeon item: the Mod Soul fights while you are away
GIKONGAN_HOURS = 8
DANGAI_STEPS = 5
DANGAI_CD = 20 * 3600
CLASH_DAILY = 5


def plain_xp(level: int) -> int:
    """One plain open-world win's XP at this level (same formula as service_combat._rewards, without the DB)."""
    from data_misc import FARM_XP_MULT
    return int((20 * level ** 1.25 + 20) * FARM_XP_MULT)


def human_reward(level: int, members: int) -> tuple:
    members = max(1, min(5, int(members)))
    k = 1 + HUMAN_GROUP_BONUS * (members - 1)
    return int(plain_xp(level) * 6 * k), int((300 + 25 * level) * k)


def gikongan_reward(level: int) -> int:
    """The Mod Soul fights carefully: about two plain wins an hour."""
    return int(plain_xp(level) * 7 * GIKONGAN_HOURS)  # was 2/hour: 8 hours paid less than a few minutes of hunting


def urahara_reward(level: int) -> tuple:
    return int(plain_xp(level) * 40), URAHARA_PTS


def clash_power(ch: dict, rng=random) -> float:
    """Reiatsu Clash: raw spirit pressure (soft Reiatsu, a little Kidō and level), with a random surge."""
    s = ch.get("stats") or {}
    base = soft_stat(s.get("reiatsu", 0)) * 1.0 + soft_stat(s.get("kido", 0)) * 0.25 + int(ch.get("level", 1)) * 0.4
    return base * rng.uniform(0.80, 1.20)


def dangai_step(rng, choice: str, kototsu_near: int) -> tuple:
    """One step of the Dangai run. choice: "run" (fast, louder) or "hide" (slow, quiet). Returns (caught, new_near).
    The Kototsu (the cleaner) closes in each step; running gets you further but draws it closer."""
    near = kototsu_near + (2 if choice == "run" else 1)
    p = min(0.85, 0.06 * near + (0.08 if choice == "run" else 0.0))
    return rng.random() < p, near


# ---- storage -----------------------------------------------------------------------------------------------------
async def soul_doc(uid: int) -> dict:
    return (await col("soul").find_one({"user_id": uid})) or {"user_id": uid}


async def _set(uid: int, key: str, value):
    await col("soul").update_one({"user_id": uid}, {"$set": {key: value}}, upsert=True)


def left(at: int, span: int) -> int:
    return max(0, int(at or 0) + int(span) - int(time.time()))


# ---- Inner World duel --------------------------------------------------------------------------------------------
async def inner_duel(uid: int):
    """Fight your zanpakutō spirit: a mirror of yourself with +10% power. Win: bond +25 on the bound blade and XP."""
    from service_combat import build_player, blocking_pve
    from service_player import add_xp, get_char
    import engine as E
    d = await soul_doc(uid)
    cd = left((d.get("inner") or {}).get("at"), INNER_CD)
    if cd:
        return "cooldown", cd
    if await blocking_pve(uid):
        return "fighting", None
    ch = await get_char(uid)
    if not ch:
        return "noreg", None
    rng = random.Random()
    me = await build_player(ch)
    spirit = await build_player(ch, name="⚔️ Zanpakutō Spirit")
    spirit["mods"]["dmg"] = spirit["mods"].get("dmg", 1.0) * 1.10
    me["ai"] = spirit["ai"] = True
    st = E.new_state(me, spirit, rng, pvp=True)
    guard = 0
    while not st["done"] and guard < 600:
        E.do_action(st, E.ai_choose(st, st["cur"], rng), rng)
        guard += 1
    win = st.get("winner") == "a"
    await _set(uid, "inner", {"at": int(time.time()), "win": win})
    xp = 0
    if win:
        from data_zanpakuto import bond_key
        await col("characters").update_one({"user_id": uid}, {"$inc": {f"bond.{bond_key(ch)}": 25}})
        _, _, xp = await add_xp(uid, plain_xp(int(ch["level"])) * 10, "inner_duel")
    return "ok", {"win": win, "turns": int(st.get("turn", 0)), "xp": xp}


# ---- Urahara training (72h) --------------------------------------------------------------------------------------
async def urahara_start(uid: int):
    from service_player import add_coins, get_char
    d = await soul_doc(uid)
    u = d.get("urahara") or {}
    if u.get("end") and not u.get("claimed"):
        return "running", max(0, int(u["end"]) - int(time.time()))
    cd = left(u.get("claimed_at"), URAHARA_CD)
    if cd:
        return "cooldown", cd
    ch = await get_char(uid)
    cost = 200 * int(ch["level"])
    if not await add_coins(uid, -cost, "urahara"):
        return "funds", cost
    now = int(time.time())
    await _set(uid, "urahara", {"start": now, "end": now + URAHARA_HOURS * 3600, "claimed": False})
    return "ok", URAHARA_HOURS * 3600


async def urahara_claim(uid: int):
    from service_player import add_xp, get_char
    r = await col("soul").find_one_and_update(
        {"user_id": uid, "urahara.claimed": False, "urahara.end": {"$lte": int(time.time())}},
        {"$set": {"urahara.claimed": True, "urahara.claimed_at": int(time.time())}})
    if not r:
        return "notready", None
    ch = await get_char(uid)
    xp, pts = urahara_reward(int(ch["level"]))
    await col("characters").update_one({"user_id": uid}, {"$inc": {"points": pts}})
    _, _, got = await add_xp(uid, xp, "urahara")
    return "ok", {"xp": got, "pts": pts}


# ---- Human World patrol (group) ----------------------------------------------------------------------------------
async def human_join(uid: int, chat_id: int):
    """Start or join the chat's patrol. One patrol per chat at a time; joining closes after HUMAN_GROUP_WINDOW."""
    now = int(time.time())
    p = await col("soul_patrols").find_one({"chat_id": chat_id, "end": {"$gt": now}})
    if p and uid in p["members"]:
        return "already", p
    if p:
        if now - int(p["start"]) > HUMAN_GROUP_WINDOW or len(p["members"]) >= 5:
            return "closed", p
        await col("soul_patrols").update_one({"_id": p["_id"], "members": {"$ne": uid}}, {"$push": {"members": uid}})
        return "joined", await col("soul_patrols").find_one({"_id": p["_id"]})
    doc = {"chat_id": chat_id, "start": now, "end": now + HUMAN_HOURS * 3600, "members": [uid], "paid": []}
    await col("soul_patrols").insert_one(doc)
    return "started", doc


async def human_claim(uid: int, chat_id: int):
    from service_player import add_coins, add_xp, get_char
    now = int(time.time())
    p = await col("soul_patrols").find_one_and_update(
        {"chat_id": chat_id, "members": uid, "paid": {"$ne": uid}, "end": {"$lte": now}},
        {"$push": {"paid": uid}}, sort=[("end", -1)])
    if not p:
        return "notready", None
    ch = await get_char(uid)
    xp, coins = human_reward(int(ch["level"]), len(p["members"]))
    _, _, got = await add_xp(uid, xp, "human_patrol")
    await add_coins(uid, coins, "human_patrol")
    return "ok", {"xp": got, "coins": coins, "members": len(p["members"])}


# ---- Gikongan: offline farming -----------------------------------------------------------------------------------
async def gikongan_start(uid: int):
    from service_economy import inv_remove
    d = await soul_doc(uid)
    g = d.get("gikongan") or {}
    if g.get("end") and not g.get("claimed"):
        return "running", max(0, int(g["end"]) - int(time.time()))
    if not await inv_remove(uid, GIKONGAN_ID, 1):
        return "noitem", None
    now = int(time.time())
    await _set(uid, "gikongan", {"start": now, "end": now + GIKONGAN_HOURS * 3600, "claimed": False})
    return "ok", GIKONGAN_HOURS * 3600


async def gikongan_claim(uid: int):
    from service_player import add_xp, get_char
    r = await col("soul").find_one_and_update(
        {"user_id": uid, "gikongan.claimed": False, "gikongan.end": {"$lte": int(time.time())}},
        {"$set": {"gikongan.claimed": True}})
    if not r:
        return "notready", None
    ch = await get_char(uid)
    _, _, got = await add_xp(uid, gikongan_reward(int(ch["level"])), "gikongan")
    return "ok", {"xp": got}


# ---- Dangai run --------------------------------------------------------------------------------------------------
async def dangai_start(uid: int):
    d = await soul_doc(uid)
    g = d.get("dangai") or {}
    if g.get("active"):
        return "ok", g
    cd = left(g.get("at"), DANGAI_CD)
    if cd:
        return "cooldown", cd
    run = {"active": True, "step": 0, "near": 0, "at": int(time.time())}
    await _set(uid, "dangai", run)
    return "ok", run


async def dangai_move(uid: int, choice: str):
    from service_player import add_coins, add_xp, get_char
    if choice not in ("run", "hide"):
        return "bad", None
    r = await col("soul").find_one({"user_id": uid, "dangai.active": True})
    if not r:
        return "none", None
    g = r["dangai"]
    caught, near = dangai_step(random.Random(), choice, int(g["near"]))
    step = int(g["step"]) + 1
    if caught:
        await col("soul").update_one({"user_id": uid, "dangai.step": g["step"]}, {"$set": {"dangai.active": False}})
        ch = await get_char(uid)
        loss = min(int(ch.get("coins", 0)), 50 * int(ch["level"]))
        if loss:
            await add_coins(uid, -loss, "dangai_kototsu")
        return "caught", {"step": step, "loss": loss}
    if step >= DANGAI_STEPS:
        upd = await col("soul").update_one({"user_id": uid, "dangai.step": g["step"]}, {"$set": {"dangai.active": False}})
        if not upd.modified_count:
            return "none", None
        ch = await get_char(uid)
        xp, coins = plain_xp(int(ch["level"])) * 12, 120 * int(ch["level"])
        _, _, got = await add_xp(uid, xp, "dangai")
        await add_coins(uid, coins, "dangai")
        return "escaped", {"xp": got, "coins": coins}
    await col("soul").update_one({"user_id": uid, "dangai.step": g["step"]}, {"$set": {"dangai.step": step, "dangai.near": near}})
    return "step", {"step": step, "near": near}


# ---- Reiatsu Clash -----------------------------------------------------------------------------------------------
async def clash(uid: int):
    """Push your reiatsu against a random player of a similar level (best of 3). Win: +clash points and XP."""
    from service_player import add_xp, get_char
    ch = await get_char(uid)
    if not ch:
        return "noreg", None
    day = time.strftime("%Y%m%d", time.gmtime())
    d = await soul_doc(uid)
    c = d.get("clash") or {}
    used = int(c.get("n", 0)) if c.get("day") == day else 0
    if used >= CLASH_DAILY:
        return "limit", None
    lv = int(ch["level"])
    foes = await col("characters").aggregate([
        {"$match": {"user_id": {"$ne": uid}, "level": {"$gte": max(1, lv - 30), "$lte": lv + 30}}},
        {"$sample": {"size": 1}}, {"$project": {"user_id": 1, "name": 1, "level": 1, "stats": 1}}]).to_list(1)
    if not foes:
        return "nofoe", None
    foe, rng = foes[0], random.Random()
    rounds = [(clash_power(ch, rng), clash_power(foe, rng)) for _ in range(3)]
    won = sum(a > b for a, b in rounds) >= 2
    await col("soul").update_one({"user_id": uid}, {"$set": {"clash.day": day, "clash.n": used + 1},
                                                     "$inc": {"clash.pts": 3 if won else 0}}, upsert=True)
    got = 0
    if won:
        _, _, got = await add_xp(uid, plain_xp(lv) * 2, "clash")
    return "ok", {"won": won, "foe": foe.get("name") or "?", "rounds": [(int(a), int(b)) for a, b in rounds],
                  "xp": got, "left": CLASH_DAILY - used - 1}
