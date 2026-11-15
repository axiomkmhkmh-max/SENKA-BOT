"""Casino persistence + game flow. Coins move through service_player.add_coins (atomic, logged)."""
import random
import time

from pymongo import ReturnDocument

import engine_casino as C
from database import col
from service_player import add_coins, get_char

DAY = 86400
COOL_SECONDS = C.STREAK_COOLOFF_MINUTES * 60


def _today() -> int:
    return int(time.time()) // DAY


async def profile(uid: int) -> dict:
    doc = await col("casino_profile").find_one({"user_id": uid})
    if not doc:
        doc = {"user_id": uid, "wagered": 0, "daily": {"day": _today(), "loss": 0}, "recent": [],
               "cool_until": 0, "hilo": None, "shini": None}
    if doc["daily"]["day"] != _today():
        doc["daily"] = {"day": _today(), "loss": 0}
    return doc


async def _save(doc: dict) -> None:
    await col("casino_profile").replace_one({"user_id": doc["user_id"]}, doc, upsert=True)


async def _feed_jackpot(uid: int, bet: int) -> None:
    feed = int(bet * C.JACKPOT_FEED)
    await col("casino_jackpot").update_one(
        {"_id": "main"}, {"$inc": {"pool": feed, f"tickets.{uid}": max(1, bet // 100)}}, upsert=True)


async def guard(uid: int, bet: int):
    """Returns (char, error_key). error_key is None when the bet may be placed."""
    ch = await get_char(uid)
    if not ch:
        return None, "no_char"
    lim = C.validate_bet(bet, ch["level"])
    if lim:
        return ch, lim
    prof = await profile(uid)
    if prof["cool_until"] > time.time():
        return ch, "cool"
    if prof["daily"]["loss"] >= C.DAILY_LOSS_CAP:
        return ch, "daily_cap"
    if ch["coins"] < bet:
        return ch, "insufficient"
    return ch, None


async def settle(uid: int, game: str, bet: int, result: dict, debit: bool = True) -> dict:
    """Pay out, feed the jackpot, update profile, VIP progress, cool-off and ledger.
    debit=False when the bet was already taken when the round started (Hi-Lo)."""
    if debit and not await add_coins(uid, -bet, f"casino_{game}"):
        return {"err": "insufficient"}
    if result["payout"] > 0:
        await add_coins(uid, result["payout"], f"casino_{game}_win")
    await _feed_jackpot(uid, bet)
    prof = await profile(uid)
    prof["wagered"] += bet
    if result["net"] < 0:
        prof["daily"]["loss"] += -result["net"]
    prof["recent"] = (prof["recent"] + [bool(result["net"] > 0)])[-C.STREAK_COOLOFF_LOSSES:]
    if C.should_cool_off(prof["recent"]):
        prof["cool_until"] = int(time.time()) + COOL_SECONDS
        prof["recent"] = []
        result["cool_off"] = True
    rb = C.rebate(-result["net"], prof["wagered"]) if result["net"] < 0 else 0
    if rb:
        await add_coins(uid, rb, "casino_rebate")
        result["rebate"] = rb
    await _save(prof)
    await col("casino_ledger").insert_one(
        {"user_id": uid, "g": game, "bet": bet, "net": result["net"], "at": int(time.time())})
    result["vip"] = C.VIP_TIERS[C.vip_tier(prof["wagered"])][0]
    return result


async def play_dice(uid: int, bet: int, pick: str):
    ch, err = await guard(uid, bet)
    if err:
        return None, err
    rng = random.Random()
    return await settle(uid, "dice", bet, C.reiatsu_dice(bet, pick, rng)), None


async def play_slots(uid: int, bet: int):
    ch, err = await guard(uid, bet)
    if err:
        return None, err
    return await settle(uid, "slots", bet, C.slots_spin(bet, random.Random())), None


async def play_roulette(uid: int, bet: int, kind: str, value=None):
    ch, err = await guard(uid, bet)
    if err:
        return None, err
    return await settle(uid, "roulette", bet, C.roulette_spin(bet, kind, value, random.Random())), None


async def play_crash(uid: int, bet: int, cash_at):
    ch, err = await guard(uid, bet)
    if err:
        return None, err
    return await settle(uid, "crash", bet, C.crash_play(bet, cash_at, random.Random())), None


async def play_shini21(uid: int, bet: int, hit_once: bool):
    ch, err = await guard(uid, bet)
    if err:
        return None, err
    actions = ["hit", "stand"] if hit_once else ["stand"]
    return await settle(uid, "21", bet, C.shinigami21(bet, actions, random.Random())), None


async def hilo_start(uid: int, bet: int):
    ch, err = await guard(uid, bet)
    if err:
        return None, err
    prof = await profile(uid)
    if prof.get("hilo"):
        return None, "busy"
    if not await add_coins(uid, -bet, "casino_hilo"):
        return None, "insufficient"
    card = random.randint(1, 13)
    prof["hilo"] = {"bet": bet, "card": card, "steps": 0, "mult": 1.0}
    await _save(prof)
    return prof["hilo"], None


async def _claim_hilo(uid: int):
    """Take the live Hi-Lo round out of the profile in one atomic step. Only one request can hold it,
    so a double-tapped 'cash' cannot pay out twice and a double-tapped guess cannot count twice."""
    doc = await col("casino_profile").find_one_and_update(
        {"user_id": uid, "hilo": {"$ne": None}}, {"$set": {"hilo": None}}, return_document=ReturnDocument.BEFORE)
    return (doc or {}).get("hilo")


async def _put_back_hilo(uid: int, st: dict) -> None:
    await col("casino_profile").update_one({"user_id": uid}, {"$set": {"hilo": st}})


async def hilo_guess(uid: int, guess: str):
    """guess: 'hi' | 'lo' | 'cash'. Returns (state, finished_result or None)."""
    if guess not in ("hi", "lo", "cash"):
        return None, None
    st = await _claim_hilo(uid)
    if not st:  # no live round, or another request is already handling it
        return None, None
    bet = st["bet"]
    mult = float(st.get("mult", C.hilo_multiplier(st["steps"])))  # rounds started before the fix have no "mult"
    if guess == "cash":
        if st["steps"] == 0:  # cashing out before any guess refunds the stake
            await add_coins(uid, bet, "casino_hilo_refund")
            return None, None
        payout = int(bet * mult)
        result = {"game": "hilo", "won": True, "bet": bet, "payout": payout, "net": payout - bet,
                  "steps": st["steps"], "cards": [st["card"]]}
        return None, await settle(uid, "hilo", bet, result, debit=False)
    if st["steps"] >= C.HILO_MAX_STEPS:
        await _put_back_hilo(uid, st)
        return st, None
    ok, nxt = C.hilo_step(st["card"], guess, random.Random())
    if not ok:
        result = {"game": "hilo", "won": False, "bet": bet, "payout": 0, "net": -bet,
                  "steps": st["steps"], "cards": [st["card"], nxt]}
        return None, await settle(uid, "hilo", bet, result, debit=False)
    # the step pays by the chance it had to win, so reading the card gives no edge
    st["mult"] = round(mult * C.hilo_step_factor(st["card"], guess), 4)
    st["card"], st["steps"] = nxt, st["steps"] + 1
    await _put_back_hilo(uid, st)
    return st, None


async def jackpot_status() -> dict:
    doc = await col("casino_jackpot").find_one({"_id": "main"}) or {"pool": C.JACKPOT_SEED, "tickets": {}}
    return {"pool": max(C.JACKPOT_SEED, int(doc.get("pool", 0)))}


async def jackpot_draw() -> dict | None:
    """Run one draw (call from the scheduler). Pays the winner and resets the pool and tickets."""
    doc = await col("casino_jackpot").find_one({"_id": "main"}) or {}
    tickets = {int(k): int(v) for k, v in (doc.get("tickets") or {}).items() if int(v) > 0}
    win = C.jackpot_draw(int(doc.get("pool", 0)), tickets, random.Random())
    if not win:
        return None
    await add_coins(win["uid"], win["prize"], "casino_jackpot")
    await col("casino_jackpot").update_one(
        {"_id": "main"},
        {"$set": {"pool": C.JACKPOT_SEED, "tickets": {}, "last_winner": {"uid": win["uid"], "prize": win["prize"],
                                                                         "at": int(time.time())}}})
    return win


async def last_jackpot_winner() -> dict | None:
    doc = await col("casino_jackpot").find_one({"_id": "main"}) or {}
    return doc.get("last_winner")
