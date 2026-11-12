"""Persistent Bleach-inspired race, story, faction and Kidō progression."""
import time
from database import col
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

STORY_ARCS = [
    {"id":"substitute", "fa":"جانشین شینیگامی", "en":"Substitute Soul Reaper", "level":1, "race":["human","shinigami","visored","fullbringer"]},
    {"id":"soul_society", "fa":"نجات روکیـا در سول سوسایتی", "en":"Soul Society: The Rescue", "level":15, "race":["shinigami","visored","human","fullbringer"]},
    {"id":"arrancar", "fa":"ظهور آرانکار", "en":"Arrancar: The Arrancar", "level":30, "race":["shinigami","visored","hollow","arrancar","quincy"]},
    {"id":"fake_karakura", "fa":"نبرد کاراکورای جعلی", "en":"Fake Karakura Town", "level":50, "race":["shinigami","visored","arrancar","quincy"]},
    {"id":"fullbring", "fa":"عامل گمشده", "en":"The Lost Agent", "level":55, "race":["human","fullbringer","shinigami"]},
    {"id":"tybw", "fa":"جنگ خونین هزارساله", "en":"Thousand-Year Blood War", "level":70, "race":["shinigami","quincy","arrancar","visored"]},
]

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

async def story_state(uid):
    ch = await get_char(uid)
    if not ch: return None
    doc = await col("story_progress").find_one({"user_id":uid}) or {"completed":[],"active":None}
    available = [a for a in STORY_ARCS
                 if ch["level"] >= a["level"] and ch["race"] in a["race"]
                 and a["id"] not in doc.get("completed", [])
                 and a["id"] != doc.get("active")]
    active = next((a for a in STORY_ARCS if a["id"] == doc.get("active")), None)
    return {"doc":doc,"available":available,"active":active,"level":ch["level"],"race":ch["race"]}

async def start_story(uid, arc_id):
    s = await story_state(uid)
    if not s: return "missing",None
    arc = next((a for a in s["available"] if a["id"]==arc_id),None)
    if not arc: return "locked",s
    if s["active"]: return "busy",s
    ch = await get_char(uid)
    # Ensure the progress document exists first; then claim the empty active slot atomically.
    await col("story_progress").update_one(
        {"user_id": uid},
        {"$setOnInsert": {"user_id": uid, "completed": [], "active": None, "step": 0}},
        upsert=True)
    result = await col("story_progress").update_one(
        {"user_id": uid, "active": None, "completed": {"$ne": arc_id}},
        {"$set": {"active": arc_id, "step": 0,
                  "start_wins": int(ch.get("wins", 0)), "updated_at": int(time.time())}})
    if not result.modified_count:
        return "busy", await story_state(uid)
    return "ok", await story_state(uid)

async def advance_story(uid):
    s=await story_state(uid)
    if not s or not s["active"]: return "none",s
    arc=s["active"]
    # Each checkpoint consumes one distinct PvE victory recorded after the arc began.
    ch=await get_char(uid)
    doc=s["doc"]; step=int(doc.get("step",0))
    if int(ch.get("wins",0)) < int(doc.get("start_wins",0)) + step + 1:
        return "need_win",s
    if step < 2:
        r=await col("story_progress").update_one({"user_id":uid,"active":arc["id"],"step":step},{"$inc":{"step":1},"$set":{"updated_at":int(time.time())}})
        return ("step" if r.modified_count else "race"),await story_state(uid)
    r=await col("story_progress").update_one({"user_id":uid,"active":arc["id"],"step":step},{"$addToSet":{"completed":arc["id"]},"$set":{"active":None,"step":0,"updated_at":int(time.time())}})
    if r.modified_count:
        await add_xp(uid, max(100, s["level"]*25), "story", apply_rate=False)
        await add_coins(uid, max(50,s["level"]*10), "story")
        return "complete",await story_state(uid)
    return "race",await story_state(uid)

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
