"""Gotei Trial: a timed tournament that runs beside the main game.

Phase 1 (training, default 27h): ranked duels earn tournament points only. They never change rating or Battle
Rank. Points and per-pair counts are atomic counters in their own collections (tour_points, tour_pairs).
Phase 2 (ready): the window is over; an admin starts the bracket by hand (`tournament start`).
Phase 3 (bracket): single elimination, simulated by the existing engine, one round per `tour_round_minutes`,
results posted to the chat the tournament was opened in.
Phase 4 (done): the champion gets the prize.

Bracket fighters are built from a STANDARD KIT (engine_tournament.standard_char): a fresh minimal character with
fixed level, fixed stat total, no blade, one standard weapon and armour. Nothing of the real character is read
except its race, so main-game power cannot decide a match.

Live keys (`set <key> <value>`): tour_train_hours, tour_round_minutes, tour_max_entrants, tour_level, tour_evo,
tour_prize_coins. The prize item is set per tournament with the admin command `tournament prize item <id>`.
"""
import logging
import math
import random
import time
import uuid
from html import escape

from aiogram.exceptions import TelegramAPIError
from pymongo import ReturnDocument

from database import col, game_settings
from engine_tournament import (pair_round, play_match, round_name, seed_bracket, standard_armor,
                               standard_char, standard_weapon, training_points)

log = logging.getLogger("senka.tournament")
KEY = "current"
OPEN = ("training", "ready", "bracket")
LABEL_FA = {"preliminary": "مرحلهٔ مقدماتی", "academy_exam": "امتحان آکادمی", "seat_trial": "آزمون درجه",
            "captains_assembly": "مجلس کاپیتان‌ها"}
LABEL_EN = {"preliminary": "Preliminary", "academy_exam": "Academy Exam", "seat_trial": "Seat Trial",
            "captains_assembly": "Captains' Assembly"}


async def _setting(key, default):
    gs = await game_settings()
    try:
        return type(default)(gs.get(key, default))
    except (TypeError, ValueError):
        return default


async def current():
    return await col("tournaments").find_one({"key": KEY})


async def training_open() -> bool:
    d = await current()
    return bool(d and d.get("phase") == "training" and int(time.time()) < int(d.get("train_end", 0)))


# ---- training points -------------------------------------------------------------------------------------------
async def record_training(w: int, l: int, w_name: str, l_name: str, started_at: int = None):
    """Called by service_combat.pvp_settle for a ranked duel that was started inside the training window.
    The pair counter is an atomic upsert-increment, so two duels settling at once can never both slip past the cap."""
    d = await current()
    if not d or d.get("phase") not in ("training", "ready"):
        return
    if int(started_at or time.time()) >= int(d.get("train_end", 0)):
        return
    tid = d["tid"]
    pair = f"{min(w, l)}:{max(w, l)}"
    r = await col("tour_pairs").find_one_and_update({"_id": f"{tid}:{pair}"}, {"$inc": {"n": 1}}, upsert=True,
                                                    return_document=ReturnDocument.AFTER)
    seen = int(r["n"]) - 1
    for uid, name, won in ((w, w_name, True), (l, l_name, False)):
        pts = training_points(won, seen)
        if pts:
            await col("tour_points").update_one({"_id": f"{tid}:{uid}"},
                                                {"$inc": {"pts": pts}, "$set": {"tid": tid, "uid": int(uid), "name": name}},
                                                upsert=True)


async def _top(tid: str, limit: int) -> list:
    cur = col("tour_points").find({"tid": tid, "pts": {"$gt": 0}}).sort([("pts", -1), ("uid", 1)]).limit(int(limit))
    return [x async for x in cur]


# ---- lifecycle ----------------------------------------------------------------------------------------------------
async def open_training(chat_id: int, hours: int = None):
    d = await current()
    if d and d.get("phase") in OPEN:
        return "active", d
    hours = max(1, min(int(hours or await _setting("tour_train_hours", 27)), 720))
    now = int(time.time())
    if d and d.get("tid"):  # the old tournament's counters are no longer needed
        await col("tour_points").delete_many({"tid": d["tid"]})
        await col("tour_pairs").delete_many({"_id": {"$regex": f"^{d['tid']}:"}})
    doc = {"key": KEY, "tid": uuid.uuid4().hex[:10], "phase": "training", "chat_id": int(chat_id), "created_at": now,
           "train_start": now, "train_end": now + hours * 3600, "names": {}, "alive": [], "round": 0,
           "rounds_total": 0, "round_seconds": 3600, "next_at": 0, "champion": None, "log": [],
           "prize_coins": None, "prize_item": ""}
    await col("tournaments").replace_one({"key": KEY}, doc, upsert=True)
    try:
        await col("tour_points").create_index([("tid", 1), ("pts", -1)])
    except Exception:  # an index only speeds up seeding; never block opening on it
        log.warning("tour_points index not created")
    return "ok", doc


async def set_prize(coins: int = None, item: str = None):
    d = await current()
    if not d or d.get("phase") not in OPEN:
        return False
    upd = {}
    if coins is not None:
        upd["prize_coins"] = int(coins)
    if item is not None:
        upd["prize_item"] = item
    await col("tournaments").update_one({"key": KEY}, {"$set": upd})
    return True


async def start_bracket(force: bool = False):
    d = await current()
    if not d:
        return "none", None
    if d["phase"] == "training" and not force:
        return "training", d
    if d["phase"] not in ("training", "ready"):
        return "phase", d
    top = await _top(d["tid"], await _setting("tour_max_entrants", 32))
    now = int(time.time())
    if len(top) < 2:
        await col("tournaments").update_one({"key": KEY}, {"$set": {"phase": "done", "champion": None, "next_at": 0}})
        return "few", d
    order = seed_bracket([int(x["uid"]) for x in top])
    names = {str(x["uid"]): x["name"] for x in top}
    r = await col("tournaments").update_one({"key": KEY, "phase": {"$in": ["training", "ready"]}}, {"$set": {
        "phase": "bracket", "alive": order, "names": names, "round": 0,
        "rounds_total": int(math.log2(len(order))),
        "round_seconds": await _setting("tour_round_minutes", 60) * 60,
        "next_at": now + 60, "seeded_at": now}})
    if not r.modified_count:  # someone else started it a moment ago
        return "phase", d
    return "ok", await current()


async def set_chat(chat_id: int) -> bool:
    r = await col("tournaments").update_one({"key": KEY}, {"$set": {"chat_id": int(chat_id)}})
    return bool(r.matched_count)


async def cancel():
    d = await current()
    if not d or d.get("phase") == "done":
        return False
    await col("tournaments").update_one({"key": KEY}, {"$set": {"phase": "done", "champion": None, "next_at": 0}})
    return True


async def status_text() -> str:
    d = await current()
    if not d:
        return "هیچ تورنومنتی ثبت نشده.\nNo tournament on record."
    top = await _top(d["tid"], 10)
    board = "\n".join(f"{i + 1}. {escape(str(x['name']))} — {x['pts']}" for i, x in enumerate(top)) or "—"
    total = await col("tour_points").count_documents({"tid": d["tid"], "pts": {"$gt": 0}})
    names = d.get("names", {})
    if d["phase"] == "training":
        left = max(0, int(d["train_end"]) - int(time.time())) // 60
        head = f"⏳ تمرین — {left} دقیقهٔ دیگر / Training — {left} min left"
    elif d["phase"] == "ready":
        head = "✅ تمرین تمام شد؛ منتظر <code>tournament start</code> / Training over; waiting for the admin"
    elif d["phase"] == "bracket":
        head = (f"⚔️ جدول — دور {d.get('round', 0)} از {d.get('rounds_total', 0)}، "
                f"{sum(1 for u in d.get('alive', []) if u is not None)} باقی‌مانده / Bracket — {sum(1 for u in d.get('alive', []) if u is not None)} left")
    else:
        ch = escape(str(names.get(str(d["champion"]), d["champion"]))) if d.get("champion") else "—"
        head = f"🏁 پایان — قهرمان / Done — champion: {ch}"
    prize = f"\n🎁 {d.get('prize_coins') if d.get('prize_coins') is not None else await _setting('tour_prize_coins', 300000):,}" \
            + (f" + {escape(d['prize_item'])}" if d.get("prize_item") else "")
    return f"{head}{prize}\n👥 {total}\n\n{board}"


# ---- the bracket ------------------------------------------------------------------------------------------------
async def _fighter(uid: int, level: int, evo: int):
    """The STANDARD fighter of a player: built from a minimal character document, never from the real one."""
    from data_races import RACES
    from service_combat import KIDO_RACES, build_player
    from service_player import get_char
    real = await get_char(uid)
    if not real:
        return None
    race = real["race"]
    kit = standard_char(uid, real["name"], race, level, RACES[race]["stats"], race in KIDO_RACES, evo)
    f = await build_player(kit, name=real["name"])
    f["weapon"] = standard_weapon(level)
    f["armor"] = standard_armor(level)
    return f


async def _grant_prize(uid: int, d: dict) -> str:
    """Pay the champion. Never raises; returns a one-line description for the announcement."""
    from data_items import ALL
    from service_economy import inv_add
    from service_player import add_coins
    coins = d.get("prize_coins")
    coins = int(coins if coins is not None else await _setting("tour_prize_coins", 300000))
    parts = []
    try:
        if coins > 0 and await add_coins(uid, coins, "tournament"):
            parts.append(f"🪙 {coins:,}")
        item = d.get("prize_item") or ""
        if item in ALL and await inv_add(uid, item, 1, force=True):
            parts.append("🎁 " + escape(str(ALL[item].get("name_en") or item)))
    except Exception:
        log.exception("tournament prize for %s failed", uid)
        return "⚠️ prize error — see the server log"
    return " · ".join(parts) or "—"


async def _say(bot, chat_id, text: str):
    if bot is None or not chat_id:
        return
    chunks, cur = [], ""
    for line in text.split("\n"):
        if cur and len(cur) + len(line) + 1 > 3500:
            chunks.append(cur)
            cur = ""
        cur = f"{cur}\n{line}" if cur else line
    chunks.append(cur)
    for c in chunks:
        try:
            await bot.send_message(int(chat_id), c, parse_mode="HTML")
        except TelegramAPIError:
            log.warning("tournament announce failed for chat %s", chat_id)
            return


async def _play_round(bot, d: dict):
    now = int(time.time())
    # claim the round first: a second tick cannot play it again (compare-and-set on next_at)
    claimed = await col("tournaments").find_one_and_update(
        {"key": KEY, "phase": "bracket", "next_at": d["next_at"]}, {"$set": {"next_at": now + 3600}})
    if claimed is None:
        return
    level = await _setting("tour_level", 30)
    evo = await _setting("tour_evo", 2)
    max_turns = int((await game_settings())["pvp_max_turns"])
    names = d.get("names", {})

    def nm(u):
        return escape(str(names.get(str(u), u)))

    alive = [None if u is None else int(u) for u in d["alive"]]
    rnd = int(d.get("round", 0)) + 1
    key = round_name(len(alive))
    rng = random.Random()
    winners, lines = [], []
    for a, b in pair_round(alive):
        if b is None:  # a bye: the slot's seed rests
            winners.append(a)
            lines.append(f"• {nm(a)} → ⏭ bye")
            continue
        try:
            fa, fb = await _fighter(a, level, evo), await _fighter(b, level, evo)
            if fa is None or fb is None:  # a deleted character forfeits (if both are gone, the higher seed advances)
                w = b if fa is None and fb is not None else a
                lines.append(f"• {nm(a)} ↔ {nm(b)} → <b>{nm(w)}</b> (forfeit)")
            else:
                w = a if play_match(fa, fb, rng, max_turns) == "a" else b
                lines.append(f"• {nm(a)} ⚔ {nm(b)} → <b>{nm(w)}</b>")
        except Exception:  # one broken fighter must never freeze the whole bracket: the higher seed (listed first) advances
            log.exception("tournament match %s vs %s failed", a, b)
            w = a
            lines.append(f"• {nm(a)} ⚔ {nm(b)} → <b>{nm(w)}</b>")
        winners.append(w)
    entry = {"round": rnd, "key": key, "lines": lines[:40]}
    head = f"⚔️ <b>{LABEL_FA.get(key, key)} / {LABEL_EN.get(key, key)}</b>"

    if len(winners) == 1:
        champ = winners[0]
        await col("tournaments").update_one({"key": KEY}, {
            "$set": {"phase": "done", "alive": winners, "round": rnd, "champion": champ, "next_at": 0},
            "$push": {"log": {"$each": [entry], "$slice": -8}}})
        paid = await _grant_prize(champ, d)
        await _say(bot, d["chat_id"], f"{head}\n" + "\n".join(lines))
        await _say(bot, d["chat_id"], f"🏆 <b>قهرمان گوتی‌تریال: {nm(champ)}</b>\n🏆 <b>Gotei Trial champion: {nm(champ)}</b>\n🎁 {paid}")
        return

    interval = int(d.get("round_seconds", 3600))
    await col("tournaments").update_one({"key": KEY}, {
        "$set": {"alive": winners, "round": rnd, "next_at": now + interval},
        "$push": {"log": {"$each": [entry], "$slice": -8}}})
    await _say(bot, d["chat_id"], f"{head} — {len(winners)} ✔\n" + "\n".join(lines) + f"\n⏭ {interval // 60} min / دقیقه")


async def tick(bot):
    """Called by the scheduler every loop. Ends the training window and plays due bracket rounds."""
    d = await current()
    if not d:
        return
    now = int(time.time())
    if d.get("phase") == "training" and now >= int(d.get("train_end", 0)):
        r = await col("tournaments").update_one({"key": KEY, "phase": "training"}, {"$set": {"phase": "ready"}})
        if r.modified_count:
            n = await col("tour_points").count_documents({"tid": d["tid"], "pts": {"$gt": 0}})
            await _say(bot, d.get("chat_id"),
                       f"🔔 تمرین تورنومنت تمام شد! {n} شرکت‌کننده ثبت شدند. ادمین جدول را شروع می‌کند.\n"
                       f"🔔 Training is over! {n} entrants. An admin will start the bracket.")
    elif d.get("phase") == "bracket" and now >= int(d.get("next_at", 0)):
        await _play_round(bot, d)
