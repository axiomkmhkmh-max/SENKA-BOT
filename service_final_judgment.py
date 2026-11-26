"""The Final Judgment: solo, once-per-day gauntlet with persistent progress and no party assistance."""
from __future__ import annotations

import time
from database import col
from service_player import get_char, today

FJ_OPEN = False   # Nov 26: the event is closed until a new one comes. Flip to True to reopen it.

STAGE_WAVES = {1: 100, 2: 5, 6: 30, 9: 5}
STAGE_NAMES = {
    1: ("صد دشمنِ داوری", "One Hundred Judged"),
    2: ("پنج فرمانروای افسانه‌ای", "Five Legendary Sovereigns"),
    3: ("منطقه‌ی خاموش", "The Silent Zone"),
    4: ("غول‌های بی‌رحم", "Unforgiving Giants"),
    5: ("سه‌گانه‌ی ویرانگر", "The Triune Cataclysm"),
    6: ("سی موج استقامت", "Thirty Waves of Endurance"),
    7: ("آینه‌ی تاریک", "The Dark Reflection"),
    8: ("پنج چهره‌ی هیولا", "The Fivefold Abomination"),
    9: ("بدون حق درمان", "No Mercy, No Remedies"),
    10: ("بیداری مطلق", "Absolute Awakening"),
}


def stage_name(stage: int, lang: str) -> str:
    pair = STAGE_NAMES.get(int(stage), ("داوری نهایی", "Final Judgment"))
    return pair[0 if lang == "fa" else 1]


def _attempt_id(uid: int, day: str) -> str:
    return f"final-judgment:{int(uid)}:{day}"


async def start(uid: int, lang: str):
    """Consume today's entry atomically before creating the first encounter."""
    from service_combat import active_pve, duel_busy, pve_start
    if not FJ_OPEN:
        return "closed", None
    ch = await get_char(uid)
    if not ch:
        return "noreg", None
    if await active_pve(uid) or await duel_busy(uid):
        return "busy", None
    day = today()
    key = _attempt_id(uid, day)
    attempt = {"_id": key, "user_id": int(uid), "day": day, "status": "running", "stage": 1,
               "wave": 1, "created_at": int(time.time()), "updated_at": int(time.time())}
    try:
        await col("final_judgment_attempts").insert_one(attempt)
    except Exception:
        # Duplicate _id means the one daily attempt was already consumed. Do not mask unrelated DB failures.
        existing = await col("final_judgment_attempts").find_one({"_id": key})
        if not existing:
            raise
        # A run whose next encounter could not be created (crash / DB error between two encounters) is parked
        # with a `resume` marker. Claim that marker atomically and rebuild the encounter, so a technical failure
        # never burns the player's only daily attempt.
        parked = await col("final_judgment_attempts").find_one_and_update(
            {"_id": key, "status": "running", "resume": {"$exists": True}}, {"$unset": {"resume": ""}})
        if not parked:
            return "spent", None
        rs = parked.get("resume") or {}
        try:
            doc = await pve_start(uid, lang, dungeon={
                "id": "final_judgment", "stage": int(rs.get("stage", 1)), "total": 10, "diff": "legendary",
                "final_judgment": True, "attempt_day": day, "wave": int(rs.get("wave", 1)),
                "wave_total": STAGE_WAVES.get(int(rs.get("stage", 1)), 1)}, carry=rs.get("carry") or None)
        except Exception:
            await col("final_judgment_attempts").update_one({"_id": key, "status": "running"}, {"$set": {"resume": rs}})
            raise
        return "ok", doc
    try:
        doc = await pve_start(uid, lang, dungeon={"id": "final_judgment", "stage": 1, "total": 10,
                                                 "diff": "legendary", "final_judgment": True,
                                                 "attempt_day": day, "wave": 1, "wave_total": STAGE_WAVES[1]})
    except Exception:
        # The first encounter never existed: give today's entry back instead of silently consuming it.
        await col("final_judgment_attempts").delete_one({"_id": key, "status": "running", "stage": 1, "wave": 1})
        raise
    return "ok", doc


def _carry_from(doc):
    f = doc["state"]["a"]
    return {"hp": max(0.01, f["hp"] / max(1, f["max_hp"])),
            "re": max(0.0, f["re"] / max(1, f["max_re"])),
            "gauge": int((f.get("x") or {}).get("gauge", 0)),
            "shield": int(f.get("shield", 0)),
            "artifact_lives": int((f.get("mods") or {}).get("artifact_lives", 0))}


async def settle(doc, won: bool):
    """Settle a single encounter. Rewards are withheld until stage 10 is cleared."""
    from service_combat import pve_start
    d = doc.get("dungeon") or {}
    uid, day = int(doc["user_id"]), d.get("attempt_day") or today()
    key = _attempt_id(uid, day)
    stage, wave = int(d.get("stage", 1)), int(d.get("wave", 1))
    wave_total = int(d.get("wave_total", STAGE_WAVES.get(stage, 1)))
    now = int(time.time())
    if not won:
        await col("final_judgment_attempts").update_one({"_id": key, "status": "running"},
            {"$set": {"status": "failed", "failed_stage": stage, "failed_wave": wave, "updated_at": now}})
        return {"final_judgment": {"won": False, "stage": stage, "wave": wave, "wave_total": wave_total}}

    if wave < wave_total:
        next_stage, next_wave = stage, wave + 1
    elif stage < 10:
        next_stage, next_wave = stage + 1, 1
    else:
        next_stage, next_wave = 10, wave_total
        reward = ""
        # Award The Almighty through the existing unique-artifact ownership transaction.
        from service_drops import art_claim
        free_artifact = await col("artifacts").find_one({"_id": "art_almighty", "state": "free"})
        claim = await art_claim(uid, "art_almighty", from_state="free") if free_artifact else "gone"
        await col("characters").update_one({"user_id": uid}, {"$set": {"final_judgment_cleared": True,
                                                                             "final_judgment_cleared_at": now}})
        if claim == "ok":
            reward = "👁️ The Almighty"
        else:
            reward = "Judgment Conqueror" if claim == "has" else "Judgment Conqueror (artifact unavailable)"
        await col("final_judgment_attempts").update_one({"_id": key, "status": "running"},
            {"$set": {"status": "cleared", "stage": 10, "wave": wave_total, "updated_at": now,
                      "reward": reward}})
        return {"final_judgment": {"won": True, "stage": 10, "reward": reward}}

    carry = _carry_from(doc)
    # Park the run (stage, wave and carried state) BEFORE creating the next encounter: if pve_start fails, the
    # player re-enters through `start()` and continues from here instead of being locked out of the attempt.
    await col("final_judgment_attempts").update_one({"_id": key, "status": "running"},
        {"$set": {"stage": next_stage, "wave": next_wave, "updated_at": now,
                  "resume": {"stage": next_stage, "wave": next_wave, "carry": carry}}})
    next_doc = await pve_start(uid, doc.get("lang", "en"), dungeon={
        "id": "final_judgment", "stage": next_stage, "total": 10, "diff": "legendary",
        "final_judgment": True, "attempt_day": day, "wave": next_wave,
        "wave_total": STAGE_WAVES.get(next_stage, 1)}, carry=carry)
    await col("final_judgment_attempts").update_one({"_id": key, "status": "running"}, {"$unset": {"resume": ""}})
    return {"final_judgment": {"won": True, "stage": stage, "wave": wave,
                               "wave_total": wave_total, "next": next_doc}}


async def abandon(uid: int, sid: str):
    """Leave the Final Judgment from the fight screen. The battle is closed, the run is marked abandoned and
    today's entry stays spent (no second try). Returns True when an active Final Judgment battle was closed."""
    doc = await col("battles").find_one({"sid": sid, "user_id": int(uid), "mode": "pve", "status": "active"})
    d = (doc or {}).get("dungeon") or {}
    if not doc or not d.get("final_judgment"):
        return False
    closed = await col("battles").find_one_and_update({"sid": sid, "status": "active"}, {"$set": {"status": "fled"}})
    if not closed:
        return False
    day = d.get("attempt_day") or today()
    await col("final_judgment_attempts").update_one(
        {"_id": _attempt_id(uid, day), "status": "running"},
        {"$set": {"status": "abandoned", "failed_stage": int(d.get("stage", 1)),
                  "failed_wave": int(d.get("wave", 1)), "updated_at": int(time.time())},
         "$unset": {"resume": ""}})
    return True
