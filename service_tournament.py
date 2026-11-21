"""Gotei Trial: a timed tournament that runs beside the main game.

Phase 1 (training, default 27h): ranked duels earn tournament points only. They never change rating or Battle
Rank. Points and per-pair counts are atomic counters in their own collections (tour_points, tour_pairs).
Phase 2 (ready): the window is over; an admin starts the bracket by hand (`tournament start`).
Phase 3 (bracket): single elimination, simulated by the existing engine, one round per `tour_round_minutes`,
results posted to the chat the tournament was opened in.
Phase 4 (done): the champion gets the prize.

Every fighter (bracket AND, by default, the training duels) is built from the STANDARD KIT
(engine_tournament.standard_fighter): no race at all, one stat block, one weapon, one armour, no blade, no gear. Race,
level, stats, equipment and every other main-game power are never read, so nothing but the tournament itself decides a
match. The only difference between two fighters is training mastery: each counted training duel adds one stat point
in the bracket, up to `tour_mastery_cap` (0 = strictly equal).
Bracket matches are series (Bo3, Bo5 in the semifinals, Bo7 in the final). The draw and every round are announced with a
bracket picture (tournament_render).

Live keys (`set <key> <value>`): tour_train_hours, tour_round_minutes, tour_draw_minutes, tour_max_entrants, tour_level,
tour_mastery_cap, tour_equal_training, tour_prize_coins. The prize item is set per tournament with the admin command
`tournament prize item <id>`.
"""
import asyncio
import logging
import math
import random
import time
import uuid
from html import escape

from aiogram.exceptions import TelegramAPIError
from pymongo import ReturnDocument

from database import col, game_settings
from engine_tournament import (MASTERY_CAP_DEFAULT, best_of, mastery_points, pair_round, play_series, round_name,
                               seed_bracket, standard_fighter, training_points)

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
                                                {"$inc": {"pts": pts, "duels": 1, "wins": 1 if won else 0},
                                                 "$set": {"tid": tid, "uid": int(uid), "name": name}},
                                                upsert=True)


async def _top(tid: str, limit: int) -> list:
    """Standings: points, then wins, then the lower user id (a fixed, boring tie-break)."""
    cur = col("tour_points").find({"tid": tid, "pts": {"$gt": 0}}).sort([("pts", -1), ("wins", -1), ("uid", 1)]).limit(int(limit))
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
           "order": [], "seeds": {}, "mastery": {}, "hist": [], "draw_sent": False,
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
    cap = await _setting("tour_mastery_cap", MASTERY_CAP_DEFAULT)
    order = seed_bracket([int(x["uid"]) for x in top])
    names = {str(x["uid"]): x["name"] for x in top}
    seeds = {str(x["uid"]): i + 1 for i, x in enumerate(top)}
    mastery = {str(x["uid"]): mastery_points(x.get("duels", 0), cap) for x in top}  # frozen now, so it cannot change mid-bracket
    r = await col("tournaments").update_one({"key": KEY, "phase": {"$in": ["training", "ready"]}}, {"$set": {
        "phase": "bracket", "alive": order, "order": order, "names": names, "seeds": seeds, "mastery": mastery, "hist": [],
        "round": 0, "rounds_total": int(math.log2(len(order))), "draw_sent": False,
        "round_seconds": await _setting("tour_round_minutes", 60) * 60,
        "next_at": now + max(0, await _setting("tour_draw_minutes", 5)) * 60, "seeded_at": now}})
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


# ---- texts and pictures -------------------------------------------------------------------------------------------
def _nm(d: dict, u) -> str:
    names = d.get("names", {})
    seed = (d.get("seeds") or {}).get(str(u))
    return (f"#{seed} " if seed else "") + escape(str(names.get(str(u), u)))


def _label(left: int) -> str:
    key = round_name(left)
    return f"{LABEL_FA[key]} / {LABEL_EN[key]} · {left}"


async def top_text(limit: int = 32) -> str:
    """The training standings: who is in, who is on the bubble."""
    d = await current()
    if not d:
        return "هیچ تورنومنتی ثبت نشده.\nNo tournament on record."
    limit = max(1, min(int(limit), 64))
    cut = await _setting("tour_max_entrants", 32)
    cap = await _setting("tour_mastery_cap", MASTERY_CAP_DEFAULT)
    rows = await _top(d["tid"], limit)
    lines = []
    for i, x in enumerate(rows):
        mark = "✅" if i < cut else "▫️"
        lines.append(f"{mark} {i + 1}. {escape(str(x['name']))} — {x['pts']} · {x.get('wins', 0)}W/{x.get('duels', 0)} "
                     f"· 🧠{mastery_points(x.get('duels', 0), cap)}")
    return (f"🏆 جدول امتیاز تمرین — {cut} نفر اول وارد جدول می‌شوند / Training standings — top {cut} qualify\n"
            + ("\n".join(lines) or "—"))


async def status_text() -> str:
    d = await current()
    if not d:
        return "هیچ تورنومنتی ثبت نشده.\nNo tournament on record."
    top = await _top(d["tid"], 10)
    board = "\n".join(f"{i + 1}. {escape(str(x['name']))} — {x['pts']}" for i, x in enumerate(top)) or "—"
    total = await col("tour_points").count_documents({"tid": d["tid"], "pts": {"$gt": 0}})
    names = d.get("names", {})
    left = sum(1 for u in d.get("alive", []) if u is not None)
    if d["phase"] == "training":
        mins = max(0, int(d["train_end"]) - int(time.time())) // 60
        head = f"⏳ تمرین — {mins} دقیقهٔ دیگر / Training — {mins} min left"
    elif d["phase"] == "ready":
        head = "✅ تمرین تمام شد؛ منتظر <code>tournament start</code> / Training over; waiting for the admin"
    elif d["phase"] == "bracket":
        nxt = max(0, int(d.get("next_at", 0)) - int(time.time())) // 60
        head = (f"⚔️ جدول — دور {d.get('round', 0)} از {d.get('rounds_total', 0)} انجام شد، {left} نفر باقی‌مانده، "
                f"دور بعد: {_label(left)} تا {nxt} دقیقه / Bracket — round {d.get('round', 0)}/{d.get('rounds_total', 0)} done, "
                f"{left} left, next in {nxt} min")
    else:
        ch = escape(str(names.get(str(d["champion"]), d["champion"]))) if d.get("champion") else "—"
        head = f"🏁 پایان — قهرمان / Done — champion: {ch}"
    prize = f"\n🎁 {d.get('prize_coins') if d.get('prize_coins') is not None else await _setting('tour_prize_coins', 300000):,}" \
            + (f" + {escape(d['prize_item'])}" if d.get("prize_item") else "")
    return f"{head}{prize}\n👥 {total}\n\n{board}"


def _draw_blocking(d: dict, subtitle: str, footer: str = "", highlight=None, order=None, hist=None):
    from tournament_render import render_bracket
    return render_bracket(order if order is not None else d.get("order") or [], d.get("names", {}),
                          hist if hist is not None else d.get("hist", []), d.get("seeds"), "GOTEI TRIAL", subtitle, footer,
                          highlight)


async def _picture(d: dict, subtitle: str, footer: str = "", highlight=None, order=None, hist=None):
    """PNG bytes of a bracket, or None (no Pillow, or the drawing failed: a picture is never worth breaking a round)."""
    try:
        return await asyncio.to_thread(_draw_blocking, d, subtitle, footer, highlight, order, hist)
    except Exception:
        log.exception("bracket picture failed")
        return None


async def bracket_png():
    """Picture for the admin command: the real bracket once it exists, otherwise the PROJECTED one from the standings."""
    d = await current()
    if not d:
        return None
    if d.get("phase") in ("bracket", "done") and d.get("order"):
        left = sum(1 for u in d.get("alive", []) if u is not None)
        sub = "🏁 قهرمان مشخص شد" if d["phase"] == "done" else f"{left} نفر باقی‌مانده"
        return await _picture(d, sub, highlight=None if d["phase"] == "done" else int(d.get("round", 0)))
    top = await _top(d["tid"], await _setting("tour_max_entrants", 32))
    if len(top) < 2:
        return None
    proj = dict(d, names={str(x["uid"]): x["name"] for x in top}, seeds={str(x["uid"]): i + 1 for i, x in enumerate(top)})
    return await _picture(proj, "جدول پیش‌بینی‌شده از امتیاز فعلی / Projected from current points", order=seed_bracket([int(x["uid"]) for x in top]), hist=[])


async def _say_photo(bot, chat_id, png, caption: str = ""):
    if bot is None or not chat_id or not png:
        return
    try:
        from aiogram.types import BufferedInputFile
        await bot.send_photo(int(chat_id), BufferedInputFile(png, filename="gotei_trial_bracket.png"), caption=caption[:1000] or None,
                             parse_mode="HTML")
    except Exception:  # TelegramAPIError, or aiogram missing in a test: the text announcement already went out
        log.warning("tournament picture not sent to chat %s", chat_id)


# ---- the bracket ------------------------------------------------------------------------------------------------
async def _fighter(uid: int, name: str, level: int, mastery: int):
    """The STANDARD fighter of a player (no race, no gear, see engine_tournament.standard_fighter). None = the player's
    character no longer exists. Only the character's existence is checked; nothing of it is used."""
    from service_player import get_char
    if not await get_char(uid):
        return None
    return standard_fighter(name, level, mastery)


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


def _fixtures(d: dict, alive: list) -> list:
    """Lines for the matches of the round that is about to be played."""
    out = []
    for a, b in pair_round(alive):
        out.append(f"• {_nm(d, a)} ⚔ {_nm(d, b)}" if b is not None else f"• {_nm(d, a)} → ⏭ bye")
    return out


async def _announce_draw(bot, d: dict):
    """The bracket draw: seeds, round-one fixtures, and the picture. Sent once per tournament."""
    claimed = await col("tournaments").update_one({"key": KEY, "phase": "bracket", "draw_sent": False}, {"$set": {"draw_sent": True}})
    if not claimed.modified_count:
        return
    alive = [None if u is None else int(u) for u in d["alive"]]
    left = sum(1 for u in alive if u is not None)
    mins = max(1, (int(d.get("next_at", 0)) - int(time.time())) // 60)
    text = (f"🏆 <b>قرعه‌کشی گوتی‌تریال!</b> {left} نفر وارد جدول شدند.\n"
            f"🏆 <b>Gotei Trial draw!</b> {left} entrants.\n"
            "⚖️ همه با کیت یکسان می‌جنگند: بدون نژاد، بدون تجهیزات. فقط مهارت تمرینت مهمه.\n"
            "⚖️ Everyone fights with the same kit: no race, no gear.\n"
            f"⏭ {_label(len(alive))} — {mins} دقیقهٔ دیگر / in {mins} min\n\n" + "\n".join(_fixtures(d, alive)))
    await _say(bot, d.get("chat_id"), text)
    await _say_photo(bot, d.get("chat_id"), await _picture(d, f"قرعه‌کشی · {left} نفر / Draw · {left} entrants", highlight=0))


async def _play_round(bot, d: dict):
    now = int(time.time())
    # claim the round first: a second tick cannot play it again (compare-and-set on next_at)
    claimed = await col("tournaments").find_one_and_update(
        {"key": KEY, "phase": "bracket", "next_at": d["next_at"]}, {"$set": {"next_at": now + 3600}})
    if claimed is None:
        return
    level = await _setting("tour_level", 30)
    import engine as _E
    max_turns = max(_E.MAX_TURNS, int((await game_settings())["pvp_max_turns"]))
    names = d.get("names", {})
    mastery = d.get("mastery", {})
    alive = [None if u is None else int(u) for u in d["alive"]]
    rnd = int(d.get("round", 0)) + 1
    left = len(alive)
    key = round_name(left)
    bo = best_of(left)
    rng = random.Random()
    matches, lines = [], []
    for a, b in pair_round(alive):
        if b is None:  # a bye: the slot's seed rests
            matches.append({"a": a, "b": None, "w": a, "s": "bye"})
            lines.append(f"• {_nm(d, a)} → ⏭ bye")
            continue
        score = "—"
        try:
            fa = await _fighter(a, str(names.get(str(a), a)), level, int(mastery.get(str(a), 0)))
            fb = await _fighter(b, str(names.get(str(b), b)), level, int(mastery.get(str(b), 0)))
            if fa is None or fb is None:  # a deleted character forfeits (if both are gone, the higher seed advances)
                w = b if fa is None and fb is not None else a
                score = "forfeit"
                lines.append(f"• {_nm(d, a)} ↔ {_nm(d, b)} → <b>{_nm(d, w)}</b> (forfeit)")
            else:
                side, (wa, wb) = play_series(fa, fb, rng, bo, max_turns)
                w = a if side == "a" else b
                score = f"{wa}-{wb}"
                lines.append(f"• {_nm(d, a)} ⚔ {_nm(d, b)} → <b>{_nm(d, w)}</b> ({wa}–{wb})")
        except Exception:  # one broken fighter must never freeze the whole bracket: the higher seed (listed first) advances
            log.exception("tournament match %s vs %s failed", a, b)
            w = a
            lines.append(f"• {_nm(d, a)} ⚔ {_nm(d, b)} → <b>{_nm(d, w)}</b>")
        matches.append({"a": a, "b": b, "w": w, "s": score})
    winners = [m["w"] for m in matches]
    hist = list(d.get("hist", [])) + [matches]
    head = f"⚔️ <b>{_label(left)}</b> — Bo{bo}"
    d2 = dict(d, hist=hist)

    if len(winners) == 1:
        champ = winners[0]
        await col("tournaments").update_one({"key": KEY}, {"$set": {
            "phase": "done", "alive": winners, "round": rnd, "champion": champ, "next_at": 0, "hist": hist}})
        paid = await _grant_prize(champ, d)
        await _say(bot, d["chat_id"], f"{head}\n" + "\n".join(lines))
        await _say(bot, d["chat_id"], f"🏆 <b>قهرمان گوتی‌تریال: {_nm(d, champ)}</b>\n🏆 <b>Gotei Trial champion: {_nm(d, champ)}</b>\n🎁 {paid}")
        await _say_photo(bot, d["chat_id"], await _picture(d2, "🏁 قهرمان مشخص شد / Champion crowned"))
        return

    interval = int(d.get("round_seconds", 3600))
    await col("tournaments").update_one({"key": KEY}, {"$set": {"alive": winners, "round": rnd, "next_at": now + interval, "hist": hist}})
    nxt = _fixtures(d, winners)
    await _say(bot, d["chat_id"], f"{head} — {len(winners)} ✔\n" + "\n".join(lines)
               + f"\n\n⏭ بعدی / Next: <b>{_label(len(winners))}</b> — {interval // 60} min / دقیقه\n" + "\n".join(nxt))
    await _say_photo(bot, d["chat_id"], await _picture(d2, f"پایان {LABEL_FA[key]} · {len(winners)} نفر باقی ماند", highlight=rnd))


async def tick(bot):
    """Called by the scheduler every loop. Ends the training window, announces the draw, plays due bracket rounds."""
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
                       f"🔔 Training is over! {n} entrants. An admin will start the bracket.\n\n" + await top_text(10))
    elif d.get("phase") == "bracket":
        if not d.get("draw_sent") and d.get("order"):
            await _announce_draw(bot, d)
        if now >= int(d.get("next_at", 0)):
            await _play_round(bot, d)
