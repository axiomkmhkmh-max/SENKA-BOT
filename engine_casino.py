"""Bleach Casino: in-game coins only (never real money, never cash-out).

Pure logic, no I/O. Each game takes a bet, an rng and returns a result dict; the handler
does the coin movement. Every game has a house edge so the economy stays balanced.
Run tests: python -m unittest test_engine_casino -v
"""
import random

HOUSE_EDGE_NOTE = "every game favours the house"

MIN_BET = 10
MAX_BET_BASE = 5_000       # scaled up with level by max_bet()
DAILY_LOSS_CAP = 50_000    # per player per day, checked by the handler

# --- Reiatsu Dice: roll 1..100, guess "over" or "under" 50. Paid 1.9x -> ~5% edge.
REIATSU_PAYOUT = 1.9


def max_bet(level: int) -> int:
    return MAX_BET_BASE + max(0, level) * 150


def validate_bet(bet: int, level: int) -> str | None:
    if bet < MIN_BET:
        return "too_small"
    if bet > max_bet(level):
        return "too_big"
    return None


def reiatsu_dice(bet: int, pick: str, rng: random.Random) -> dict:
    if pick not in ("over", "under"):
        raise ValueError("pick must be over or under")
    roll = rng.randint(1, 100)
    if roll == 50:  # the exact middle is a house win: keeps the edge honest
        won = False
    else:
        won = (roll > 50) if pick == "over" else (roll < 50)
    payout = int(bet * REIATSU_PAYOUT) if won else 0
    return {"game": "dice", "roll": roll, "pick": pick, "won": won, "bet": bet,
            "net": payout - bet}


# --- Kido Hi-Lo: a card 1..13 is shown, guess whether the next is higher or lower.
# Ties lose. Multiplier grows with each correct guess and is lost on the first miss.
HILO_STEP = 2.0
HILO_MAX_STEPS = 5


def hilo_multiplier(steps: int) -> float:
    return round(HILO_STEP ** steps * 0.95, 4)  # 0.95 keeps a small edge for the house


def hilo_play(bet: int, guesses: list, rng: random.Random) -> dict:
    """Play a whole Hi-Lo round from a list of 'hi'/'lo' guesses (max HILO_MAX_STEPS)."""
    if not guesses or len(guesses) > HILO_MAX_STEPS:
        raise ValueError("between 1 and HILO_MAX_STEPS guesses")
    card = rng.randint(1, 13)
    steps = 0
    cards = [card]
    for g in guesses:
        if g not in ("hi", "lo"):
            raise ValueError("guess must be hi or lo")
        nxt = rng.randint(1, 13)
        cards.append(nxt)
        ok = (nxt > card) if g == "hi" else (nxt < card)
        if not ok or nxt == card:
            return {"game": "hilo", "cards": cards, "steps": steps, "won": False, "bet": bet,
                    "net": -bet, "payout": 0}
        steps += 1
        card = nxt
    payout = int(bet * hilo_multiplier(steps))
    return {"game": "hilo", "cards": cards, "steps": steps, "won": True, "bet": bet,
            "net": payout - bet, "payout": payout}


# --- Hollow Slots: three reels, weighted symbols. Expected return is kept under 1.0.
SYMBOLS = [
    # (name, weight, pays-for-three)
    ("mask", 30, 0),        # any three masks: mild win table below
    ("zanpakuto", 20, 0),
    ("hogyoku", 3, 0),
    ("hollow", 15, 0),
    ("soul", 12, 0),
    ("seven", 2, 0),
]
TRIPLE_PAY = {"mask": 3, "zanpakuto": 5, "hollow": 8, "soul": 15, "hogyoku": 60, "seven": 120}
PAIR_PAY = 1  # two matching symbols return the bet


def _spin(rng: random.Random) -> list:
    names = [s[0] for s in SYMBOLS]
    weights = [s[1] for s in SYMBOLS]
    return rng.choices(names, weights=weights, k=3)


def slots_spin(bet: int, rng: random.Random) -> dict:
    reels = _spin(rng)
    if reels[0] == reels[1] == reels[2]:
        mult = TRIPLE_PAY[reels[0]]
    elif len({reels[0], reels[1], reels[2]}) < 3:
        mult = PAIR_PAY
    else:
        mult = 0
    payout = bet * mult
    return {"game": "slots", "reels": reels, "mult": mult, "bet": bet, "payout": payout,
            "net": payout - bet, "won": payout > bet}


def expected_return_slots(samples: int = 200_000, seed: int = 0) -> float:
    """Monte-Carlo estimate of the slots return rate (used by tests, not by players)."""
    rng = random.Random(seed)
    total = 0
    for _ in range(samples):
        total += slots_spin(1, rng)["payout"]
    return total / samples


# --- Shinigami 21 (blackjack): ace = 11 or 1, face cards = 10. Dealer stands on 17.
# Natural 21 pays 2.5x, a normal win 2x, a push returns the bet, a bust or a lower hand loses.
BJ_NATURAL_PAY = 2.5
BJ_WIN_PAY = 2.0


def _card_value(rank: int) -> int:
    return 10 if rank >= 10 else rank  # 1 is an ace, handled in _hand_total


def _hand_total(cards: list) -> int:
    total = sum(11 if c == 1 else _card_value(c) for c in cards)
    aces = cards.count(1)
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total


def shinigami21(bet: int, actions: list, rng: random.Random) -> dict:
    """Play one hand. actions is the player's ordered decisions: 'hit' or 'stand' (max 8 hits)."""
    deck = [r for r in range(1, 14) for _ in range(4)]
    rng.shuffle(deck)
    player = [deck.pop(), deck.pop()]
    dealer = [deck.pop(), deck.pop()]
    natural = _hand_total(player) == 21 and len(player) == 2
    hits = 0
    if not natural:
        for a in actions:
            if a == "stand":
                break
            if a != "hit":
                raise ValueError("action must be hit or stand")
            player.append(deck.pop())
            hits += 1
            if _hand_total(player) > 21 or hits >= 8:
                break
    p = _hand_total(player)
    if p > 21:
        return {"game": "21", "player": player, "dealer": dealer, "result": "bust", "bet": bet,
                "payout": 0, "net": -bet}
    if natural and _hand_total(dealer) != 21:
        payout = int(bet * BJ_NATURAL_PAY)
        return {"game": "21", "player": player, "dealer": dealer, "result": "natural", "bet": bet,
                "payout": payout, "net": payout - bet}
    while _hand_total(dealer) < 17:
        dealer.append(deck.pop())
    d = _hand_total(dealer)
    if d > 21 or p > d:
        result, payout = "win", int(bet * BJ_WIN_PAY)
    elif p == d:
        result, payout = "push", bet
    else:
        result, payout = "lose", 0
    return {"game": "21", "player": player, "dealer": dealer, "result": result, "bet": bet,
            "payout": payout, "net": payout - bet}


# =====================================================================================
# Deep casino: Kido Roulette, Crimson Crash, Mask Jackpot, VIP rebates, ledger & limits.
# =====================================================================================

# --- Kido Roulette: bet on a colour (red/black/green) or a single number 0..36.
ROULETTE_RED = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
ROULETTE_PAY = {"red": 2, "black": 2, "green": 36, "number": 36}  # single zero: ~2.7% house edge everywhere


def roulette_spin(bet: int, kind: str, value, rng: random.Random) -> dict:
    """kind: 'red' | 'black' | 'green' (value ignored) | 'number' (value 0..36)."""
    if kind not in ROULETTE_PAY:
        raise ValueError("kind must be red, black, green or number")
    if kind == "number" and (not isinstance(value, int) or not 0 <= value <= 36):
        raise ValueError("number must be 0..36")
    spin = rng.randint(0, 36)
    if spin == 0:
        colour = "green"
    else:
        colour = "red" if spin in ROULETTE_RED else "black"
    if kind == "number":
        won = spin == value
    elif kind == "green":
        won = spin == 0
    else:
        won = colour == kind
    mult = ROULETTE_PAY["number" if kind == "number" else ("green" if kind == "green" else "red")]
    payout = bet * mult if won else 0
    return {"game": "roulette", "spin": spin, "colour": colour, "kind": kind, "value": value,
            "won": won, "bet": bet, "payout": payout, "net": payout - bet}


# --- Crimson Crash: a multiplier climbs from 1.00; cash out before it crashes.
# Crash point follows a heavy tail; the house keeps ~3% by using a 0.97 factor.
CRASH_HOUSE = 0.97
CRASH_MAX = 100.0


def crash_point(rng: random.Random) -> float:
    u = rng.random()
    if u < 1e-9:
        return CRASH_MAX
    point = CRASH_HOUSE / (1 - u)
    return round(min(point, CRASH_MAX), 2)


def crash_play(bet: int, cash_at: float | None, rng: random.Random) -> dict:
    """cash_at: target multiplier (>= 1.01) to auto-cash, or None to ride it out (always loses)."""
    point = crash_point(rng)
    if cash_at is None or cash_at < 1.01:
        return {"game": "crash", "point": point, "cashed": None, "won": False, "bet": bet,
                "payout": 0, "net": -bet}
    won = point >= cash_at
    payout = int(bet * cash_at) if won else 0
    return {"game": "crash", "point": point, "cashed": cash_at if won else None, "won": won,
            "bet": bet, "payout": payout, "net": payout - bet}


# --- Mask Jackpot: every bet feeds a pool; one random winner per draw gets the pool.
JACKPOT_FEED = 0.02          # 2% of every bet goes to the pool
JACKPOT_SEED = 5_000


def jackpot_feed(pool: int, bet: int) -> int:
    return pool + int(bet * JACKPOT_FEED)


def jackpot_draw(pool: int, tickets: dict, rng: random.Random) -> dict | None:
    """tickets: uid -> ticket count (1 ticket per 100 coins bet this cycle). Returns winner or None."""
    total = sum(tickets.values())
    if total <= 0:
        return None
    pick = rng.randrange(total)
    acc = 0
    for uid, n in sorted(tickets.items()):
        acc += n
        if pick < acc:
            return {"uid": uid, "prize": max(JACKPOT_SEED, pool), "reset_pool_to": JACKPOT_SEED}
    return None


# --- VIP tiers: comp points from wagered coins; higher tiers get a rebate on net losses.
VIP_TIERS = [
    ("Rukongai", 0, 0.00),
    ("Shinigami Academy", 50_000, 0.02),
    ("Squad Officer", 500_000, 0.04),
    ("Captain", 5_000_000, 0.06),
    ("Central 46", 50_000_000, 0.08),
]


def vip_tier(total_wagered: int) -> int:
    idx = 0
    for i, (_, minimum, _) in enumerate(VIP_TIERS):
        if total_wagered >= minimum:
            idx = i
    return idx


def rebate(total_net_loss: int, total_wagered: int) -> int:
    """Rebate on net losses for the player's VIP tier. Never pays on a net win."""
    if total_net_loss <= 0:
        return 0
    return int(total_net_loss * VIP_TIERS[vip_tier(total_wagered)][2])


# --- Responsible-play guards: per-day caps and a cool-off after a big loss streak.
STREAK_COOLOFF_LOSSES = 5
STREAK_COOLOFF_MINUTES = 30


def should_cool_off(recent_results: list) -> bool:
    """recent_results: list of bools (won?), newest last."""
    tail = recent_results[-STREAK_COOLOFF_LOSSES:]
    return len(tail) == STREAK_COOLOFF_LOSSES and not any(tail)


# --- Ledger: every bet is recorded so the admin and the player can audit the session.
def ledger_entry(game: str, bet: int, net: int, at: int) -> dict:
    return {"g": game, "bet": bet, "net": net, "at": at}


def ledger_summary(entries: list) -> dict:
    wagered = sum(e["bet"] for e in entries)
    net = sum(e["net"] for e in entries)
    wins = sum(1 for e in entries if e["net"] > 0)
    return {"rounds": len(entries), "wagered": wagered, "net": net,
            "win_rate": round(wins / len(entries), 3) if entries else 0.0}


def hilo_step(card: int, guess: str, rng: random.Random) -> tuple:
    """One interactive Hi-Lo guess. Returns (won_step, next_card). Ties lose."""
    if guess not in ("hi", "lo"):
        raise ValueError("guess must be hi or lo")
    nxt = rng.randint(1, 13)
    ok = (nxt > card) if guess == "hi" else (nxt < card)
    if nxt == card:
        ok = False
    return ok, nxt
