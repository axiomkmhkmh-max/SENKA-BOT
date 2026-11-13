"""Persistent Bleach-inspired race, faction and Kidō progression."""
import time
from database import col, game_settings, try_cooldown
from service_player import get_char, add_xp, add_coins

RACE_PATHS = {
    "hollow": [
        ("hollow", 1, 0, "Hollow"), ("gillian", 20, 10, "Gillian"),
        ("adjuchas", 40, 35, "Adjuchas"), ("vastolorde", 65, 80, "Vasto Lorde")],
    "arrancar": [("arrancar", 1, 0, "Arrancar"), ("resurreccion", 35, 25, "Resurrección"),
                 ("segunda_etapa", 75, 90, "Segunda Etapa")],
    "quincy": [("quincy", 1, 0, "Quincy"), ("schrift", 35, 30, "Schrift"),
               ("vollstandig", 70, 80, "Vollständig")],
    "shinigami": [("academy", 1, 0, "Academy Student"), ("shikai", 20, 30, "Shikai"),
                  ("lieutenant", 45, 55, "Lieutenant"), ("bankai", 60, 80, "Bankai")],
    "visored": [("mask", 1, 0, "Visored"), ("controlled_mask", 30, 25, "Controlled Mask"),
                ("mastered_mask", 60, 70, "Mastered Hollowfication")],
    "fullbringer": [("awakened", 1, 0, "Awakened Fullbringer"), ("fullbring", 25, 25, "Fullbring"),
                    ("complete", 55, 65, "Fullbring: Complete")],
    "human": [("sensitive", 1, 0, "Spiritually Aware"), ("medium", 20, 20, "Spirit Medium"),
              ("awakened", 45, 50, "Awakened Human")],
}

KIDO = {
    "hado1": {"name":"Shō", "type":"Hadō", "level":1, "cost":8, "power":1.15, "fa":"شو — ضربه نیرویی"},
    "hado4": {"name":"Byakurai", "type":"Hadō", "level":8, "cost":16, "power":1.55, "fa":"بیاکورای — صاعقه سفید"},
    "hado31": {"name":"Shakkahō", "type":"Hadō", "level":25, "cost":28, "power":2.05, "fa":"شاکاهو — توپ آتش سرخ"},
    "bakudo1": {"name":"Sai", "type":"Bakudō", "level":1, "cost":10, "power":0.0, "fa":"سای — مهار موقت"},
    "bakudo4": {"name":"Hainawa", "type":"Bakudō", "level":10, "cost":18, "power":0.0, "fa":"هایناوا — طناب انرژی"},
    "bakudo9": {"name":"Geki", "type":"Bakudō", "level":16, "cost":24, "power":0.0, "fa":"گِکی — فلج‌سازی"},
    "kaido": {"name":"Kaidō: Minor Recovery", "type":"Kaidō", "level":12, "cost":25, "power":0.0, "fa":"کایدو — بازیابی جزئی"},
}

FACTIONS = {
    "gotei13": {"fa":"گوتی ۱۳", "en":"Gotei 13", "races":["shinigami","visored"], "ranks":["Academy Student","Unseated Officer","Seated Officer","Lieutenant Candidate","Captain Candidate"]},
    "espada": {"fa":"اسپادا", "en":"Espada", "races":["arrancar"], "ranks":["Arrancar","Fracción","Espada Candidate","Espada"]},
    "wandenreich": {"fa":"وندن‌رایش", "en":"Wandenreich", "races":["quincy"], "ranks":["Soldat","Sternritter Candidate","Sternritter","Elite Sternritter"]},
}

async def race_state(uid):
    ch = await get_char(uid)
    if not ch: return None
    race = ch.get("race", "human")
    progress = ch.get("race_progress") or {"wins": int(ch.get("wins", 0)), "hunts": 0}
    path = RACE_PATHS.get(race, RACE_PATHS["human"])
    stage = min(len(path)-1, int(progress.get("stage", 0)))
    wins = int(ch.get("wins", 0))
    hunts = int(progress.get("hunts", 0))
    progress_count = hunts if race in ("hollow", "arrancar") else wins
    return {"race":race,"level":int(ch.get("level",1)),"wins":wins,"hunts":hunts,"progress_count":progress_count,"stage":stage,"current":path[stage],"next":path[stage+1] if stage+1<len(path) else None,"progress":progress}

async def evolve(uid):
    s = await race_state(uid)
    if not s: return "missing", None
    nxt = s["next"]
    if not nxt: return "max", s
    key, lvl, wins, label = nxt
    if s["level"] < lvl or s["progress_count"] < wins:
        return "requirements", {"level":lvl,"wins":wins,"state":s}
    ch = await get_char(uid)
    z = ch.get("zanpakuto") or {}
    if s["race"] == "shinigami" and key == "shikai" and not z.get("shikai"):
        return "release_required", {"release": "Shikai"}
    if s["race"] == "shinigami" and key == "bankai" and not z.get("bankai"):
        return "release_required", {"release": "Bankai"}
    # Conditional update makes double taps unable to advance multiple stages.
    r = await col("characters").update_one({"user_id":uid,"$or":[{"race_progress.stage":s["stage"]},{"race_progress.stage":{"$exists":False}}]},
        {"$set":{"race_progress.stage":s["stage"]+1,"race_progress.stage_id":key,"race_progress.updated_at":int(time.time())}})
    if not r.modified_count:
        return "race", await race_state(uid)
    return "ok", await race_state(uid)

async def kido_state(uid):
    ch=await get_char(uid)
    if not ch:return None
    if ch.get("race") not in ("shinigami", "visored"):
        return {"race": ch.get("race"), "eligible": False, "level": int(ch.get("level", 1)), "learned": set(), "available": [], "reiatsu": int(ch.get("reiatsu_current", 100))}
    learned=set((ch.get("kido_learned") or []))
    known_kido=ch.get("kido") or {}
    for key, data in KIDO.items():
        branch = "had" if data["type"] == "Hadō" else "bak" if data["type"] == "Bakudō" else None
        if branch:
            number = int(key.replace("hado", "").replace("bakudo", ""))
            if number in (known_kido.get(branch) or []): learned.add(key)
    available=[(k,v) for k,v in KIDO.items() if ch["level"]>=v["level"]]
    return {"race": ch.get("race"), "eligible": True, "level":ch["level"],"stats":ch.get("stats",{}),"learned":learned,"available":available,"reiatsu":int(ch.get("reiatsu_current", 100))}

async def learn_kido(uid, spell):
    s=await kido_state(uid)
    if not s:return "missing",None
    if not s.get("eligible", False):return "race",s
    if spell not in KIDO:return "invalid",s
    if s["level"]<KIDO[spell]["level"]:return "level",s
    if spell in s["learned"]:return "known",s
    data = KIDO[spell]
    branch = "had" if data["type"] == "Hadō" else "bak" if data["type"] == "Bakudō" else None
    updates = {"$addToSet": {"kido_learned": spell}}
    if branch:
        number = int(spell.replace("hado", "").replace("bakudo", ""))
        updates["$addToSet"]["kido." + branch] = number
    r=await col("characters").update_one({"user_id":uid,"kido_learned":{"$ne":spell}}, updates)
    return ("ok" if r.modified_count else "known"),await kido_state(uid)

async def cast_kido(uid: int, spell: str):
    """Compatibility wrapper: spells are cast by the battle engine on combat turns."""
    s = await kido_state(uid)
    if not s: return "missing", None
    if not s.get("eligible"): return "race", s
    if spell not in s["learned"]: return "locked", s
    return "combat_only", KIDO[spell]

async def faction_state(uid):
    ch=await get_char(uid)
    if not ch:return None
    return {"race":ch["race"],"faction":ch.get("faction"),"rank":ch.get("faction_rank","Unranked"),"level":ch["level"]}

async def join_faction(uid, faction):
    s=await faction_state(uid)
    if not s:return "missing",None
    f=FACTIONS.get(faction)
    if not f or s["race"] not in f["races"]:return "race",s
    if s["faction"]:return "joined",s
    r=await col("characters").update_one({"user_id":uid,"faction":{"$in":[None,""]}}, {"$set":{"faction":faction,"faction_rank":f["ranks"][0],"faction_joined_at":int(time.time())}})
    return ("ok" if r.modified_count else "joined"),await faction_state(uid)

# --- NEW BLEACH VIRAL SYSTEM: live Espada 0-9, sword/mask stances, quick duels ---
import random as _rnd

from pymongo.errors import DuplicateKeyError as _Dup

from data_artifacts import ESPADA_N

STANCE = {"shikai": (1.15, 0.0), "bankai": (1.35, 0.0), "mask": (1.5, 0.15)}  # kind -> (damage multiplier, rage chance)
STANCE_SECONDS = 600


def stance_mult(ch: dict, now: float = None) -> float:
    """Damage multiplier of the active group stance. 1.0 = none. 0.0 = the Hollow Mask ran wild (caller loses the action)."""
    s = (ch or {}).get("stance") or {}
    if float(s.get("until") or 0) <= (now or time.time()) or s.get("k") not in STANCE:
        return 1.0
    mult, rage = STANCE[s["k"]]
    return 0.0 if rage and _rnd.random() < rage else mult


async def stance_set(uid: int, kind: str):
    await col("characters").update_one({"user_id": uid}, {"$set": {"stance": {"k": kind, "until": int(time.time()) + STANCE_SECONDS}}})


async def espada_seed():
    """Fill empty seats 0..9 with the strongest unranked players (strongest gets the lowest free number)."""
    from service_player import power
    docs = await col("espada").find({}).to_list(20)
    free = [r for r in range(ESPADA_N) if r not in {d["_id"] for d in docs}]
    if not free:
        return
    held = {d["holder"] for d in docs}
    cands = [c for c in await col("characters").find({}).sort("level", -1).limit(100).to_list(100) if c["user_id"] not in held]
    cands.sort(key=lambda c: -power(c))
    for r, c in zip(free, cands):
        try:
            await col("espada").insert_one({"_id": r, "holder": c["user_id"], "since": int(time.time())})
        except _Dup:
            pass


async def espada_board():
    await espada_seed()
    docs = await col("espada").find({}).sort("_id", 1).to_list(ESPADA_N)
    chars = {c["user_id"]: c async for c in col("characters").find({"user_id": {"$in": [d["holder"] for d in docs]}}, {"user_id": 1, "name": 1, "level": 1})}
    return [(d["_id"], d["holder"], (chars.get(d["holder"]) or {}).get("name", "?"), (chars.get(d["holder"]) or {}).get("level", 0)) for d in docs]


async def espada_rank(uid: int):
    d = await col("espada").find_one({"holder": uid})
    return d["_id"] if d else None


async def quick_fight(uid_a: int, uid_b: int) -> str:
    """Instant simulated duel using the real combat engine on both sides. Returns "a" or "b"."""
    import engine as E
    from service_combat import build_player
    ca, cb = await get_char(uid_a), await get_char(uid_b)
    fa, fb = await build_player(ca), await build_player(cb)
    for f, c in ((fa, ca), (fb, cb)):
        m = stance_mult(c)
        f["mods"]["dmg"] = f["mods"].get("dmg", 1.0) * (m if m else 0.5)
    rng = _rnd.Random()
    st = E.new_state(fa, fb, rng)
    E.run_ai(st, rng, 40, ai_sides=("a", "b"))
    if st.get("winner") in ("a", "b"):
        return st["winner"]
    return "a" if fa["hp"] / max(1, fa["max_hp"]) >= fb["hp"] / max(1, fb["max_hp"]) else "b"


async def espada_challenge(att: int, tgt: int):
    """-> (result, extra). result: self | noreg | level | notespada | notbetter | cd | gone | win (extra = seat number) | lose (extra = seat)."""
    if att == tgt:
        return "self", None
    await espada_seed()
    t = await col("espada").find_one({"holder": tgt})
    if not t:
        return "notespada", None
    a = await col("espada").find_one({"holder": att})
    if a and a["_id"] < t["_id"]:
        return "notbetter", None
    ch = await get_char(att)
    if not ch or not await get_char(tgt):
        return "noreg", None
    st = await game_settings()
    if ch["level"] < int(st["espada_min_level"]):
        return "level", int(st["espada_min_level"])
    if await try_cooldown(f"esp:{att}", int(st["espada_cd"])) or await try_cooldown(f"esp:tgt:{tgt}", 30):
        return "cd", None
    if await quick_fight(att, tgt) == "b":
        return "lose", t["_id"]
    now = int(time.time())
    r = await col("espada").update_one({"_id": t["_id"], "holder": tgt}, {"$set": {"holder": att, "since": now}})
    if not r.modified_count:
        return "gone", None
    if a:  # the old seat goes to the one who was pushed out
        await col("espada").update_one({"_id": a["_id"], "holder": att}, {"$set": {"holder": tgt, "since": now}})
    return "win", t["_id"]
