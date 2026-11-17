"""Bank persistence and daily tick. Coins move through service_player.add_coins (atomic, logged).

Every change to an account goes through _mutate: load, change, then save only if nobody else saved the account in
between (version field "v"). Before, two quick taps both read the same balance and the second save overwrote the first,
so a double-tapped withdrawal paid twice and a deposit made at the same moment as another action could vanish.
Wallet coins are only paid out after the vault change is saved, so a lost race never prints coins.

Unpaid loans: after LOAN_DEFAULT_DAYS the debt (with interest) is taken from the vault first, then from the wallet.
Whatever is still missing stays as `debt`: it is collected from vault and wallet every day, and no new loan is given
until it is cleared (it used to be taken from the vault only, which is usually empty, so a loan never had to be repaid).
"""
import random
import time

import engine_bank as B
from database import col
from service_player import add_coins, get_char

DAY = 86400
RETRIES = 8


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


async def save(doc: dict) -> bool:
    """Save only if the stored account is still the version that was loaded. False = someone saved in between."""
    v = doc.get("v")
    body = {k: val for k, val in doc.items() if k not in ("_id", "v")}
    body["v"] = int(v or 0) + 1
    if "_id" not in doc:  # never stored: create it once (a unique index on user_id stops a double create)
        try:
            r = await col("bank_accounts").update_one({"user_id": doc["user_id"]}, {"$setOnInsert": body}, upsert=True)
        except Exception:  # DuplicateKeyError: another request created it first
            return False
        ok = r.upserted_id is not None
    else:
        flt = {"_id": doc["_id"], "v": v} if v is not None else {"_id": doc["_id"], "v": {"$exists": False}}
        r = await col("bank_accounts").replace_one(flt, body)
        ok = bool(r.modified_count)
    if ok:
        doc["v"] = body["v"]
    return ok


async def _mutate(uid: int, fn):
    """Run fn(acc) -> result dict on a fresh copy until it is saved without a conflict.
    A result with ok == False is returned without saving. Returns (acc, result); result None = gave up."""
    for _ in range(RETRIES):
        acc = await load(uid)
        res = fn(acc)
        if isinstance(res, dict) and res.get("ok") is False:
            return acc, res
        if await save(acc):
            return acc, res
    return None, None


async def _take_wallet(uid: int, amount: int, reason: str) -> int:
    """Take up to `amount` coins from the wallet (as much as there is). Returns what was taken."""
    for _ in range(RETRIES):
        ch = await get_char(uid)
        have = int((ch or {}).get("coins", 0))
        take = min(have, int(amount))
        if take <= 0:
            return 0
        if await add_coins(uid, -take, reason):
            return take
    return 0


async def _collect_debt(uid: int, day: int) -> int:
    """Take outstanding debt from the vault, then from the wallet. Returns the total collected."""
    def from_vault(acc):
        owed = int(acc.get("debt", 0))
        take = min(owed, max(0, int(acc["balance"])))
        if owed <= 0 or take <= 0:
            return {"ok": False, "take": 0}
        acc["balance"] -= take
        acc["debt"] = owed - take
        B.ledger(acc, "debt", -take, day)
        return {"ok": True, "take": take}
    acc, r = await _mutate(uid, from_vault)
    got = int((r or {}).get("take", 0)) if r and r.get("ok") else 0
    rest = int((acc or {}).get("debt", 0))
    if rest > 0:
        taken = await _take_wallet(uid, rest, "bank_debt")
        if taken:
            def lower(acc):
                acc["debt"] = max(0, int(acc.get("debt", 0)) - taken)
                B.ledger(acc, "debt_wallet", -taken, day)
                return {"ok": True}
            _, ok = await _mutate(uid, lower)
            if ok is None:  # could not record it: give the coins back rather than take them twice
                await add_coins(uid, taken, "bank_debt_refund")
            else:
                got += taken
    return got


async def daily_tick(uid: int) -> list:
    """Run once per day per account: interest, bonds, raids, Espada, defaults, collectors, debt.
    Safe to call often; it does nothing after the first run of the day. Returns event notes."""
    day = _today()

    def tick(acc):
        if acc.get("tick_day") == day:
            return {"ok": False, "notes": []}
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
        if acc["loans"]:
            ln = acc["loans"][0]
            ln.setdefault("start", ln["day"])  # older loans had no start; accruing moves "day", so pin the due date first
            B.accrue_loan(ln, day)  # the debt includes the interest up to today
        default = B.check_default(acc, day)
        if default:
            owed = int(default["owed"])
            take = min(max(0, int(acc["balance"])), owed)
            acc["balance"] -= take
            acc["debt"] = int(acc.get("debt", 0)) + owed - take  # the rest is collected from the wallet, then daily
            B.ledger(acc, "default", -take, day)
            notes.append(("default", take))
        col_res = B.collect_daily(acc, day)  # collectors of defaults from before the debt rule
        if col_res and col_res.get("taken"):
            B.ledger(acc, "collectors", -col_res["taken"], day)
            notes.append(("collectors", col_res["taken"]))
        acc["tick_day"] = day
        return {"ok": True, "notes": notes}

    acc, r = await _mutate(uid, tick)
    notes = list((r or {}).get("notes", []))
    if acc and int(acc.get("debt", 0)) > 0:
        got = await _collect_debt(uid, day)
        if got:
            notes.append(("debt", got))
    return notes


async def deposit(uid: int, amount: int):
    ch = await get_char(uid)
    if not ch:
        return None, "no_char"
    if amount <= 0 or ch["coins"] < amount:
        return None, "insufficient"
    if not await add_coins(uid, -amount, "bank_deposit"):
        return None, "insufficient"

    def dep(acc):
        B.deposit(acc, amount)
        B.ledger(acc, "deposit", amount, _today())
        return {"ok": True}
    acc, r = await _mutate(uid, dep)
    if r is None:  # the vault could not be updated: the coins go back to the wallet
        await add_coins(uid, amount, "bank_deposit_refund")
        return None, "busy"
    return acc, None


async def withdraw(uid: int, amount: int):
    if amount <= 0:
        return None, "insufficient"

    def wd(acc):
        r = B.withdraw(acc, amount)
        if r["ok"]:
            B.ledger(acc, "withdraw", -(r["paid"] + r["fee"]), _today())
        return r
    acc, r = await _mutate(uid, wd)
    if r is None:
        return None, "busy"
    if not r["ok"]:
        return None, r["reason"]
    await add_coins(uid, r["paid"], "bank_withdraw")  # paid only after the vault debit is saved
    return acc, None


async def loan(uid: int, amount: int):
    ch = await get_char(uid)
    if not ch:
        return None, "no_char"
    value = collateral_value(ch)

    def ln(acc):
        if int(acc.get("debt", 0)) > 0:
            return {"ok": False, "reason": "has_debt"}
        r = B.take_loan(acc, value, amount, _today())
        if r["ok"]:
            # the loan is credited to the vault only (the engine adds it to acc["balance"])
            B.ledger(acc, "loan", amount, _today())
        return r
    acc, r = await _mutate(uid, ln)
    if r is None:
        return None, "busy"
    if not r["ok"]:
        return None, r["reason"]
    return acc, None


async def repay(uid: int):
    day = _today()
    acc = await load(uid)
    if not acc["loans"] and int(acc.get("debt", 0)) > 0:  # an old default: clear the debt from vault and wallet
        await _collect_debt(uid, day)
        acc = await load(uid)
        if int(acc.get("debt", 0)) > 0:
            return None, "debt_left"
        return acc, None

    def rp(acc):
        r = B.repay_loan(acc, day)
        if r["ok"]:
            B.ledger(acc, "repay", -r["paid"], day)
        return r
    acc, r = await _mutate(uid, rp)
    if r is None:
        return None, "busy"
    if not r["ok"]:
        return None, r["reason"]
    return acc, None


async def _simple(uid: int, fn, ledger_key: str = None, cost_key: str = "cost"):
    def run(acc):
        r = fn(acc)
        if r.get("ok") and ledger_key:
            B.ledger(acc, ledger_key, -r[cost_key], _today())
        return r
    acc, r = await _mutate(uid, run)
    if r is None:
        return None, "busy"
    if not r["ok"]:
        return None, r["reason"]
    return acc, None


async def open_bond(uid: int, amount: int, term: int):
    return await _simple(uid, lambda acc: B.open_bond(acc, amount, term, _today()))


async def break_bond(uid: int, index: int):
    return await _simple(uid, lambda acc: B.break_bond(acc, index))


async def upgrade(uid: int, target: int):
    return await _simple(uid, lambda acc: B.upgrade_vault(acc, target), "upgrade")


async def security(uid: int):
    return await _simple(uid, B.buy_security, "security")


async def insurance(uid: int, days: int):
    return await _simple(uid, lambda acc: B.buy_insurance(acc, days))


async def transfer(sender_uid: int, receiver_uid: int, amount: int):
    if sender_uid == receiver_uid:
        return None, "self"
    if amount <= 0:
        return None, "bad_amount"
    rng = random.Random()

    def send(acc):
        dummy = {"balance": 0}
        r = B.transfer(acc, dummy, amount, rng)
        if r["ok"]:
            B.ledger(acc, "send", -(r["sent"] + r["fee"] + r["audit"]), _today())
        return r
    _, r = await _mutate(sender_uid, send)
    if r is None:
        return None, "busy"
    if not r["ok"]:
        return None, r["reason"]

    def receive(acc):
        acc["balance"] += r["sent"]
        B.ledger(acc, "receive", r["sent"], _today())
        return {"ok": True}
    _, got = await _mutate(receiver_uid, receive)
    if got is None:  # the receiver's vault could not be credited: give the whole amount back to the sender
        def refund(acc):
            acc["balance"] += r["sent"] + r["fee"] + r["audit"]
            B.ledger(acc, "send_refund", r["sent"] + r["fee"] + r["audit"], _today())
            return {"ok": True}
        await _mutate(sender_uid, refund)
        return None, "busy"
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
