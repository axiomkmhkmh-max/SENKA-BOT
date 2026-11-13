"""Bank persistence and daily tick. Coins move through service_player.add_coins (atomic, logged)."""
import random
import time

import engine_bank as B
from database import col
from service_player import add_coins, get_char

DAY = 86400


def _today() -> int:
    return int(time.time()) // DAY


def collateral_value(ch: dict) -> int:
    """Loans are secured by the character's standing: a simple, level-based collateral value."""
    return int(ch["level"]) * 2000


async def load(uid: int) -> dict:
    doc = await col("bank_accounts").find_one({"user_id": uid})
    if not doc:
        doc = {"user_id": uid, **B.new_account(), "tick_day": 0, "last_interest_day": _today()}
    return doc


async def save(doc: dict) -> None:
    await col("bank_accounts").replace_one({"user_id": doc["user_id"]}, doc, upsert=True)


async def daily_tick(uid: int) -> list:
    """Run once per day per account: interest, bonds, raids, Espada, defaults, collectors.
    Safe to call often; it does nothing after the first run of the day. Returns event notes."""
    acc = await load(uid)
    day = _today()
    if acc.get("tick_day") == day:
        return []
    notes = []
    paid = B.accrue_interest(acc, day)
    if paid:
        B.ledger(acc, "interest", paid, day)
        notes.append(("interest", paid))
    matured = B.mature_bonds(acc, day)
    if matured:
        B.ledger(acc, "bond", matured, day)
        notes.append(("bond", matured))
    raid = B.raid_roll(acc, random.Random())
    if raid:
        B.ledger(acc, "raid", -raid["lost"], day)
        notes.append(("raid", raid["lost"]))
    espada = B.espada_roll(acc, random.Random())
    if espada:
        B.ledger(acc, "espada", -espada["lost"], day)
        notes.append(("espada", espada["lost"]))
    default = B.check_default(acc, day)
    if default:
        # the collateral is not an inventory item here, so it is recovered as a coin penalty
        penalty = min(acc["balance"], default["seized"])
        acc["balance"] -= penalty
        B.ledger(acc, "default", -penalty, day)
        B.assign_collectors(acc, owed=default["owed"], day=day)
        notes.append(("default", penalty))
    col_res = B.collect_daily(acc, day)
    if col_res and col_res.get("taken"):
        B.ledger(acc, "collectors", -col_res["taken"], day)
        notes.append(("collectors", col_res["taken"]))
    acc["tick_day"] = day
    await save(acc)
    return notes


async def deposit(uid: int, amount: int):
    ch = await get_char(uid)
    if not ch:
        return None, "no_char"
    if amount <= 0 or ch["coins"] < amount:
        return None, "insufficient"
    if not await add_coins(uid, -amount, "bank_deposit"):
        return None, "insufficient"
    acc = await load(uid)
    B.deposit(acc, amount)
    B.ledger(acc, "deposit", amount, _today())
    await save(acc)
    return acc, None


async def withdraw(uid: int, amount: int):
    acc = await load(uid)
    r = B.withdraw(acc, amount)
    if not r["ok"]:
        return None, r["reason"]
    await add_coins(uid, r["paid"], "bank_withdraw")
    B.ledger(acc, "withdraw", -(r["paid"] + r["fee"]), _today())
    await save(acc)
    return acc, None


async def loan(uid: int, amount: int):
    ch = await get_char(uid)
    if not ch:
        return None, "no_char"
    acc = await load(uid)
    r = B.take_loan(acc, collateral_value(ch), amount, _today())
    if not r["ok"]:
        return None, r["reason"]
    await add_coins(uid, amount, "bank_loan")
    B.ledger(acc, "loan", amount, _today())
    await save(acc)
    return acc, None


async def repay(uid: int):
    acc = await load(uid)
    r = B.repay_loan(acc, _today())
    if not r["ok"]:
        return None, r["reason"]
    B.ledger(acc, "repay", -r["paid"], _today())
    await save(acc)
    return acc, None


async def open_bond(uid: int, amount: int, term: int):
    acc = await load(uid)
    r = B.open_bond(acc, amount, term, _today())
    if not r["ok"]:
        return None, r["reason"]
    await save(acc)
    return acc, None


async def break_bond(uid: int, index: int):
    acc = await load(uid)
    r = B.break_bond(acc, index)
    if not r["ok"]:
        return None, r["reason"]
    await save(acc)
    return acc, None


async def upgrade(uid: int, target: int):
    acc = await load(uid)
    r = B.upgrade_vault(acc, target)
    if not r["ok"]:
        return None, r["reason"]
    B.ledger(acc, "upgrade", -r["cost"], _today())
    await save(acc)
    return acc, None


async def security(uid: int):
    acc = await load(uid)
    r = B.buy_security(acc)
    if not r["ok"]:
        return None, r["reason"]
    B.ledger(acc, "security", -r["cost"], _today())
    await save(acc)
    return acc, None


async def transfer(sender_uid: int, receiver_uid: int, amount: int):
    if sender_uid == receiver_uid:
        return None, "self"
    sa, ra = await load(sender_uid), await load(receiver_uid)
    r = B.transfer(sa, ra, amount, random.Random())
    if not r["ok"]:
        return None, r["reason"]
    B.ledger(sa, "send", -(r["sent"] + r["fee"] + r["audit"]), _today())
    B.ledger(ra, "receive", r["sent"], _today())
    await save(sa)
    await save(ra)
    return r, None


async def statement(uid: int) -> dict:
    acc = await load(uid)
    return {"acc": acc, **B.statement(acc), "tier": B.TIERS[B.effective_tier(acc)][0]}


async def tick_all(limit: int = 200) -> int:
    """Scheduler entry: run the daily tick for accounts not yet ticked today. Returns how many ran."""
    today = _today()
    ran = 0
    cursor = col("bank_accounts").find({"tick_day": {"$ne": today}}, {"user_id": 1}).limit(limit)
    async for doc in cursor:
        await daily_tick(doc["user_id"])
        ran += 1
    return ran
