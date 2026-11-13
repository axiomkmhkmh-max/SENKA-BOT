"""Bleach Bank: in-game coins only. Pure logic, no I/O; the handler persists the returned state.

Features: vault tiers, deposit/withdraw fees, capped daily interest, collateral loans that
seize the collateral on default, and Hollow raids on large vaults (insurance softens them).
Run tests: python -m unittest test_engine_bank -v
"""
import random

# (name, min_balance_to_unlock, withdraw_fee_pct, raid_chance_per_day)
TIERS = [
    ("Rukongai Box", 0, 0.05, 0.00),
    ("Seireitei Vault", 50_000, 0.03, 0.05),
    ("Hōgyoku Chamber", 500_000, 0.02, 0.12),
    ("Central 46 Sanctum", 5_000_000, 0.01, 0.20),
]
DAILY_INTEREST = 0.002        # 0.2% a day, capped below
INTEREST_CAP_PER_DAY = 5_000
LOAN_RATIO = 0.6              # loan up to 60% of collateral value
LOAN_RATE_PER_DAY = 0.01
LOAN_DEFAULT_DAYS = 7
INSURANCE_COST_PCT = 0.02     # of the vault balance, per day covered
INSURANCE_LOSS_CUT = 0.7      # insurance cuts a raid's loss by 70%
RAID_LOSS_PCT = 0.25          # a successful raid takes 25% of the vault


def tier_for(balance: int) -> int:
    idx = 0
    for i, (_, minimum, _, _) in enumerate(TIERS):
        if balance >= minimum:
            idx = i
    return idx


def new_account() -> dict:
    return {"balance": 0, "loans": [], "insured_days": 0, "last_interest_day": 0, "raids_survived": 0,
            "raids_lost": 0, "credit": CREDIT_START, "security": 0, "bonds": [], "ledger": []}


def deposit(acc: dict, amount: int) -> dict:
    if amount <= 0:
        raise ValueError("amount must be positive")
    acc["balance"] += amount
    return {"ok": True, "balance": acc["balance"], "tier": TIERS[tier_for(acc["balance"])][0]}


def withdraw(acc: dict, amount: int) -> dict:
    if amount <= 0:
        raise ValueError("amount must be positive")
    fee_pct = TIERS[tier_for(acc["balance"])][2]
    fee = int(amount * fee_pct)
    total = amount + fee
    if total > acc["balance"]:
        return {"ok": False, "reason": "insufficient"}
    acc["balance"] -= total
    return {"ok": True, "paid": amount, "fee": fee, "balance": acc["balance"]}


def accrue_interest(acc: dict, day: int) -> int:
    """Pay interest for every day since last_interest_day (capped per day). Returns amount paid."""
    days = max(0, day - acc["last_interest_day"])
    if days == 0 or acc["balance"] <= 0:
        acc["last_interest_day"] = day
        return 0
    paid = 0
    for _ in range(min(days, 30)):  # never more than 30 days in one go
        gain = min(int(acc["balance"] * DAILY_INTEREST), INTEREST_CAP_PER_DAY)
        acc["balance"] += gain
        paid += gain
    acc["last_interest_day"] = day
    return paid


def take_loan(acc: dict, collateral_value: int, amount: int, day: int) -> dict:
    limit = int(collateral_value * credit_limit_pct(acc.get("credit", CREDIT_START)))
    if amount <= 0 or amount > limit:
        return {"ok": False, "reason": "over_limit", "limit": limit}
    if acc["loans"]:
        return {"ok": False, "reason": "already_has_loan"}
    acc["loans"].append({"principal": amount, "owed": amount, "day": day, "collateral_value": collateral_value})
    acc["balance"] += amount
    return {"ok": True, "owed": amount, "balance": acc["balance"]}


def accrue_loan(loan: dict, day: int) -> None:
    days = max(0, day - loan["day"])
    if days:
        loan["owed"] = int(loan["owed"] * ((1 + LOAN_RATE_PER_DAY) ** days))
        loan["day"] = day


def repay_loan(acc: dict, day: int) -> dict:
    if not acc["loans"]:
        return {"ok": False, "reason": "no_loan"}
    loan = acc["loans"][0]
    accrue_loan(loan, day)
    if acc["balance"] < loan["owed"]:
        return {"ok": False, "reason": "insufficient", "owed": loan["owed"]}
    acc["balance"] -= loan["owed"]
    acc["loans"].clear()
    acc["credit"] = credit_on_repay(acc.get("credit", CREDIT_START), on_time=day - loan["day"] <= LOAN_DEFAULT_DAYS)
    return {"ok": True, "paid": loan["owed"], "balance": acc["balance"], "credit": acc["credit"]}


def check_default(acc: dict, day: int) -> dict | None:
    """Seize the collateral if the loan is older than LOAN_DEFAULT_DAYS and still unpaid."""
    if not acc["loans"]:
        return None
    loan = acc["loans"][0]
    if day - loan["day"] < LOAN_DEFAULT_DAYS:
        return None
    seized = loan["collateral_value"]
    acc["loans"].clear()
    acc["credit"] = credit_on_default(acc.get("credit", CREDIT_START))
    return {"seized": seized, "owed": loan["owed"]}


def buy_insurance(acc: dict, days: int) -> dict:
    cost_each = int(acc["balance"] * INSURANCE_COST_PCT)
    total = cost_each * days
    if total > acc["balance"] or days <= 0:
        return {"ok": False, "reason": "insufficient"}
    acc["balance"] -= total
    acc["insured_days"] += days
    return {"ok": True, "cost": total, "insured_days": acc["insured_days"]}


def raid_roll(acc: dict, rng: random.Random) -> dict | None:
    """Daily Hollow raid check. Only vaults in a tier with raid chance can be raided."""
    chance = TIERS[tier_for(acc["balance"])][3] * raid_multiplier(acc)
    if chance <= 0 or rng.random() >= chance:
        return None
    loss = int(acc["balance"] * RAID_LOSS_PCT)
    insured = acc["insured_days"] > 0
    if insured:
        loss = int(loss * (1 - INSURANCE_LOSS_CUT))
        acc["insured_days"] -= 1
    loss = min(loss, acc["balance"])
    acc["balance"] -= loss
    acc["raids_lost"] += 1
    return {"lost": loss, "insured": insured, "balance": acc["balance"]}


# ---- Debt collection: after a default, Gotei 13 collectors chase the debtor for a while.
COLLECTOR_DAYS = 5            # collectors stay on the debtor this many days
COLLECTOR_TAKE_PCT = 0.10     # each day they take 10% of what is left in the vault (capped below)
COLLECTOR_DAILY_CAP = 20_000


def assign_collectors(acc: dict, owed: int, day: int) -> None:
    acc["collectors"] = {"owed": owed, "until": day + COLLECTOR_DAYS, "taken": 0}


def collect_daily(acc: dict, day: int) -> dict | None:
    c = acc.get("collectors")
    if not c:
        return None
    if day > c["until"]:
        acc["collectors"] = None
        return {"done": True, "taken": 0}
    take = min(int(acc["balance"] * COLLECTOR_TAKE_PCT), COLLECTOR_DAILY_CAP, max(0, c["owed"] - c["taken"]))
    acc["balance"] -= take
    c["taken"] += take
    if c["taken"] >= c["owed"]:
        acc["collectors"] = None
        return {"done": True, "taken": take, "paid_off": True}
    return {"done": False, "taken": take, "remaining": c["owed"] - c["taken"]}


# ---- Vault upgrades: pay to unlock a better tier early (cheaper than waiting for balance).
UPGRADE_COST_PCT = {1: 0.02, 2: 0.05, 3: 0.10}  # cost as share of the target tier's minimum


def upgrade_cost(target_tier: int) -> int:
    return int(TIERS[target_tier][1] * UPGRADE_COST_PCT.get(target_tier, 0.05))


def upgrade_vault(acc: dict, target_tier: int) -> dict:
    if target_tier <= effective_tier(acc) or target_tier >= len(TIERS):
        return {"ok": False, "reason": "not_needed"}
    cost = upgrade_cost(target_tier)
    if cost > acc["balance"]:
        return {"ok": False, "reason": "insufficient", "cost": cost}
    acc["balance"] -= cost
    acc["upgraded_to"] = target_tier
    return {"ok": True, "cost": cost, "tier": TIERS[target_tier][0]}


def effective_tier(acc: dict) -> int:
    """A paid upgrade holds while the balance stays above half of that tier's minimum."""
    up = acc.get("upgraded_to", 0)
    if up and acc["balance"] >= TIERS[up][1] // 2:
        return max(tier_for(acc["balance"]), up)
    return tier_for(acc["balance"])


# =====================================================================================
# Deep bank: credit score, savings bonds, transfers with audit, vault security, Espada raids,
# and a ledger. Still pure logic; the handler persists the account dict.
# =====================================================================================

CREDIT_MIN, CREDIT_MAX, CREDIT_START = 300, 850, 600


def credit_limit_pct(score: int) -> float:
    """Loan ratio grows with credit score: 0.3 at the bottom, LOAN_RATIO (0.6) at the top."""
    s = min(max(score, CREDIT_MIN), CREDIT_MAX)
    return round(0.3 + (s - CREDIT_MIN) / (CREDIT_MAX - CREDIT_MIN) * 0.3, 3)


def credit_on_repay(score: int, on_time: bool) -> int:
    return min(CREDIT_MAX, score + (25 if on_time else 5))


def credit_on_default(score: int) -> int:
    return max(CREDIT_MIN, score - 120)


# Savings bonds: lock coins for a fixed number of days for higher interest; early break costs 20%.
BOND_TERMS = {7: 0.004, 30: 0.0035, 90: 0.003}  # days -> daily rate (higher for shorter lock? kept modest)


def open_bond(acc: dict, amount: int, term_days: int, day: int) -> dict:
    if term_days not in BOND_TERMS:
        return {"ok": False, "reason": "bad_term"}
    if amount <= 0 or amount > acc["balance"]:
        return {"ok": False, "reason": "insufficient"}
    acc["balance"] -= amount
    acc.setdefault("bonds", []).append({"principal": amount, "term": term_days, "start": day,
                                        "rate": BOND_TERMS[term_days]})
    return {"ok": True, "principal": amount, "matures_day": day + term_days}


def mature_bonds(acc: dict, day: int) -> int:
    """Pay out bonds that reached their term. Returns total paid out this call."""
    paid = 0
    keep = []
    for b in acc.get("bonds", []):
        if day - b["start"] >= b["term"]:
            gain = int(b["principal"] * (b["rate"] * b["term"]))
            acc["balance"] += b["principal"] + gain
            paid += b["principal"] + gain
        else:
            keep.append(b)
    acc["bonds"] = keep
    return paid


def break_bond(acc: dict, index: int) -> dict:
    bonds = acc.get("bonds", [])
    if not 0 <= index < len(bonds):
        return {"ok": False, "reason": "no_bond"}
    b = bonds.pop(index)
    back = int(b["principal"] * 0.8)
    acc["balance"] += back
    return {"ok": True, "returned": back, "penalty": b["principal"] - back}


# Transfers between players: 1% fee, and a random Wire Audit (Gotei auditors) sometimes taxes big sends.
TRANSFER_FEE = 0.01
AUDIT_THRESHOLD = 200_000
AUDIT_CHANCE = 0.25
AUDIT_TAX = 0.05


def transfer(sender: dict, receiver: dict, amount: int, rng: random.Random) -> dict:
    if amount <= 0:
        raise ValueError("amount must be positive")
    fee = int(amount * TRANSFER_FEE)
    audit = 0
    if amount >= AUDIT_THRESHOLD and rng.random() < AUDIT_CHANCE:
        audit = int(amount * AUDIT_TAX)
    total = amount + fee + audit
    if total > sender["balance"]:
        return {"ok": False, "reason": "insufficient", "need": total}
    sender["balance"] -= total
    receiver["balance"] += amount
    return {"ok": True, "sent": amount, "fee": fee, "audit": audit, "sender_balance": sender["balance"]}


# Vault security: each level cuts the raid chance and loss; costs grow.
SECURITY_LEVELS = [
    (0, 0, 1.00),          # (level, cost, raid multiplier)
    (1, 20_000, 0.80),
    (2, 150_000, 0.55),
    (3, 1_000_000, 0.30),
]


def security_level(acc: dict) -> int:
    return int(acc.get("security", 0))


def buy_security(acc: dict) -> dict:
    lvl = security_level(acc)
    if lvl + 1 >= len(SECURITY_LEVELS):
        return {"ok": False, "reason": "max"}
    _, cost, _ = SECURITY_LEVELS[lvl + 1]
    if cost > acc["balance"]:
        return {"ok": False, "reason": "insufficient", "cost": cost}
    acc["balance"] -= cost
    acc["security"] = lvl + 1
    return {"ok": True, "cost": cost, "level": lvl + 1}


def raid_multiplier(acc: dict) -> float:
    return SECURITY_LEVELS[security_level(acc)][2]


# Espada robbery: a rare, large attack on the richest vaults that ignores half of insurance.
ESPADA_ROB_CHANCE = 0.01          # daily, only for accounts in the top two tiers
ESPADA_ROB_PCT = 0.40


def espada_roll(acc: dict, rng: random.Random) -> dict | None:
    if tier_for(acc["balance"]) < 2 or rng.random() >= ESPADA_ROB_CHANCE:
        return None
    loss = int(acc["balance"] * ESPADA_ROB_PCT * raid_multiplier(acc))
    loss = min(loss, acc["balance"])
    acc["balance"] -= loss
    acc["raids_lost"] += 1
    return {"lost": loss, "balance": acc["balance"]}


# Ledger for statements and audits.
def ledger(acc: dict, kind: str, amount: int, day: int) -> None:
    log = acc.setdefault("ledger", [])
    log.append({"k": kind, "a": amount, "d": day})
    del log[:-50]  # keep the last 50 entries


def statement(acc: dict) -> dict:
    log = acc.get("ledger", [])
    return {"entries": len(log), "in": sum(e["a"] for e in log if e["a"] > 0),
            "out": -sum(e["a"] for e in log if e["a"] < 0), "credit": acc.get("credit", CREDIT_START)}
