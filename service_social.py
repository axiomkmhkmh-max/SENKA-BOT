"""Guilds / squads and reply mini-games."""
import random
import time
import uuid
from datetime import datetime, timedelta, timezone

from pymongo.errors import DuplicateKeyError

from data_misc import KIDO_NUM_POOL, KIDO_Q, TRIVIA, ZANP
from database import col, game_settings, try_cooldown
from security import normalize_text
from service_player import add_coins, add_xp, bump_quest, get_char, today

CAP = {"squad": 50, "clan": 30}


async def seed_squads():
    for n in range(1, 14):
        await col("guilds").update_one({"_id": f"squad_{n:02d}"}, {"$setOnInsert": {
            "_id": f"squad_{n:02d}", "kind": "squad", "name_fa": f"گروه {n}", "name_en": f"Squad {n}", "name_key": f"squad {n}",
            "members": 0, "bank": 0, "leader": None, "created_at": int(time.time())}}, upsert=True)


async def guild_create(uid: int, name: str):
    st = await game_settings()
    ch = await get_char(uid)
    if ch.get("guild_id"):
        return "in_guild", None
    if ch["level"] < int(st["guild_min_level"]):
        return "level", int(st["guild_min_level"])
    if not await add_coins(uid, -int(st["guild_create_cost"]), "guild_create"):
        return "funds", int(st["guild_create_cost"])
    gid = "g_" + uuid.uuid4().hex[:8]
    try:
        await col("guilds").insert_one({"_id": gid, "kind": "clan", "name_fa": name, "name_en": name, "name_key": name.casefold(),
                                        "members": 1, "bank": 0, "leader": uid, "created_at": int(time.time())})
    except DuplicateKeyError:
        await add_coins(uid, int(st["guild_create_cost"]), "guild_refund")
        return "taken", None
    await col("characters").update_one({"user_id": uid}, {"$set": {"guild_id": gid, "guild_role": "leader"}})
    return "ok", gid


async def guild_join(uid: int, gid: str):
    st = await game_settings()
    ch = await get_char(uid)
    g = await col("guilds").find_one({"_id": gid})
    if not g:
        return "gone"
    if ch.get("guild_id"):
        return "in_guild"
    if g["kind"] == "squad" and ch["race"] != "shinigami":
        return "race"
    days = int(st["squad_change_days"])
    if await try_cooldown(f"guildjoin:{uid}", 5):
        return "wait"
    last = ch.get("guild_left_at", 0)
    if last and time.time() - last < days * 86400 and g["kind"] == "squad":
        return "cooldown"
    r = await col("guilds").update_one({"_id": gid, "members": {"$lt": CAP[g["kind"]]}}, {"$inc": {"members": 1}})
    if not r.modified_count:
        return "full"
    await col("characters").update_one({"user_id": uid}, {"$set": {"guild_id": gid, "guild_role": "member"}})
    return "ok"


async def guild_leave(uid: int):
    ch = await get_char(uid)
    gid = ch.get("guild_id")
    if not gid:
        return "none"
    g = await col("guilds").find_one({"_id": gid})
    if g and g.get("leader") == uid and g["members"] > 1:
        return "leader"
    await col("characters").update_one({"user_id": uid}, {"$set": {"guild_id": None, "guild_role": None, "guild_left_at": int(time.time())}})
    if g:
        await col("guilds").update_one({"_id": gid}, {"$inc": {"members": -1}})
        if g["kind"] == "clan" and g["members"] <= 1:
            await col("guilds").delete_one({"_id": gid})
    return "ok"


async def guild_deposit(uid: int, amount: int):
    ch = await get_char(uid)
    if not ch.get("guild_id"):
        return "none"
    if not await add_coins(uid, -amount, "guild_deposit"):
        return "funds"
    await col("guilds").update_one({"_id": ch["guild_id"]}, {"$inc": {"bank": amount}})
    await bump_quest(uid, "guild_deposit", 1)
    return "ok"


async def guild_list(page: int, size: int = 6):
    cur = col("guilds").find({}).sort([("kind", 1), ("members", -1)]).skip(page * size).limit(size)
    return await cur.to_list(size)


# ---- mini-games -------------------------------------------------------------------------
async def mg_new(uid: int, lang: str, kind: str = None):
    wait = await try_cooldown(f"mg:{uid}", 20)
    if wait:
        return "cool", wait
    kind = kind or random.choice(["zanp", "kido", "trivia"])
    i = 0 if lang == "fa" else 1
    if kind == "zanp":
        pick = random.choice(ZANP)
        others = random.sample([z for z in ZANP if z != pick], 3)
        opts = [pick] + others
        random.shuffle(opts)
        q = ("🗡️ تیغه‌ای نامش را زمزمه می‌کند: «{}». صاحبش کیست؟" if lang == "fa" else "🗡️ A blade whispers its name: «{}». Who wields it?").format(pick[i * 2 if False else (1 if lang == "fa" else 0)])
        options = [o[3] if lang == "fa" else o[2] for o in opts]
        ans = opts.index(pick)
    elif kind == "kido":
        pick = random.choice(KIDO_Q)
        nums = {pick[3]}
        while len(nums) < 4:
            nums.add(random.choice(KIDO_NUM_POOL))
        nums = sorted(nums)
        branch = {"had": ("هادو", "Hadō"), "bak": ("باکودو", "Bakudō")}[pick[2]][0 if lang == "fa" else 1]
        q = (f"🔮 وردِ «{pick[1]}» چندمین {branch} است؟" if lang == "fa" else f"🔮 «{pick[0]}» is which number of {branch}?")
        options = [str(n) for n in nums]
        ans = nums.index(pick[3])
    else:
        t = random.choice(TRIVIA)
        q = "🧠 " + t[0 if lang == "fa" else 1]
        options = list(t[3 if lang == "fa" else 4])
        ans = t[2]
    gid = uuid.uuid4().hex[:8]
    await col("minigames").insert_one({"gid": gid, "user_id": uid, "q": q, "options": options, "ans": ans, "done": False,
                                       "expire_at": datetime.now(timezone.utc) + timedelta(minutes=5)})
    return "ok", {"gid": gid, "q": q, "options": options}


async def mg_answer(uid: int, gid: str, idx: int):
    doc = await col("minigames").find_one_and_update({"gid": gid, "user_id": uid, "done": False}, {"$set": {"done": True}})
    if not doc:
        return "gone", None
    if idx != doc["ans"]:
        return "wrong", doc["options"][doc["ans"]]
    st = await game_settings()
    ch = await get_char(uid)
    day = today()
    rec = await col("cooldowns").find_one({"key": f"mgxp:{uid}:{day}"}) or {"xp": 0}
    want = 15 + ch["level"] * 2
    give = max(0, min(want, int(st["minigame_daily_xp_cap"]) - rec["xp"]))
    await col("cooldowns").update_one({"key": f"mgxp:{uid}:{day}"}, {"$inc": {"xp": give}, "$set": {"until": 0, "expire_at": datetime.now(timezone.utc) + timedelta(days=2)}}, upsert=True)
    if give:
        await add_xp(uid, give, "minigame", apply_rate=False)
    await add_coins(uid, 10 + ch["level"], "minigame")
    await bump_quest(uid, "minigame_win", 1)
    return "right", give
