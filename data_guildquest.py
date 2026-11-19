"""Guild Quest Board: the adventure mode. A daily board of random-level quests, each a short dungeon-like run through one
of the adventure regions (data_extras2.ADVENTURES). Rank F..S follows how far the quest level is above the player's level.
Rewards focus on items and Zanpakutō release progress (bond and mastery, the numbers Shikai and Bankai are gated on).
Everything here is pure: no database, so the generator and the reward table are unit-tested. Numbers that are tuning knobs
live in config.GAME_DEFAULTS (gq_*); the tables below are the shape of the system."""
import random

from data_extras2 import ADVENTURES

RANKS = ["F", "E", "D", "C", "B", "A", "S"]
# quest level offset (quest level - player level) per board slot: an easy quest first, a very hard one last
SLOT_OFFSETS = [(-4, -1), (-2, 1), (0, 4), (2, 7), (5, 10)]
BOARD_SIZE = len(SLOT_OFFSETS)
# fight types: fa / en name, weight, what is real about it (nothing here is flavour only)
QTYPES = {
    "purge": {"fa": "پاکسازی", "en": "Purge", "w": 5, "boss": False, "gap": True, "bonus_items": 0},
    "subjugation": {"fa": "سرکوب", "en": "Subjugation", "w": 4, "boss": True, "gap": True, "bonus_items": 0},
    "gauntlet": {"fa": "آزمون سخت", "en": "Gauntlet", "w": 2, "boss": True, "gap": False, "bonus_items": 1},
}
# purge: the last foe is a tougher regular of the region; subjugation: the region's boss; gauntlet: boss, one more stage,
# no breather before floor 3, but one extra item
ITEM_IDX = [0, 1, 2, 2, 3, 3, 4]            # item colour (0 Common .. 5 Mythic) by rank
ZNP_MASTERY = [1, 2, 3, 5, 8, 12, 18]       # Zanpakutō Mastery by rank (only when Shikai is already released)
ZNP_BOND = [1, 2, 3, 4, 6, 8, 12]           # Zanpakutō bond by rank (the road to Shikai)
XP_BONUS_RANK = 0.10                        # +10% XP per rank step


def rank_of(offset: int) -> int:
    """Rank index from the level offset: -4..-3 F, -2..-1 E, 0..1 D, 2..3 C, 4..5 B, 6..7 A, 8+ S."""
    return max(0, min(len(RANKS) - 1, (int(offset) + 4) // 2))


def stage_count(rank: int, qtype: str) -> int:
    return min(6, 2 + rank // 2 + (1 if qtype == "gauntlet" else 0))


def item_count(rank: int, qtype: str) -> int:
    return 1 + rank // 3 + QTYPES[qtype]["bonus_items"]


def regions_for(level: int):
    """Adventure regions the player has unlocked (the quest's own level can be higher than the player's)."""
    ok = [a for a, v in ADVENTURES.items() if int(level) >= v["level"]]
    return ok or [next(iter(ADVENTURES))]


def make_board(uid: int, day: str, level: int, rng=None) -> list:
    """The day's quests for one player. Random but fixed once stored (service_adventure keeps the first board of the day)."""
    rng = rng or random.Random(f"gq:{uid}:{day}")
    regions = regions_for(level)
    types, weights = list(QTYPES), [QTYPES[t]["w"] for t in QTYPES]
    board = []
    for slot, (lo, hi) in enumerate(SLOT_OFFSETS):
        off = rng.randint(lo, hi)
        qlvl = max(1, int(level) + off)
        rank = rank_of(off)  # the rolled gap sets the rank, so a low-level player still sees a full F..S spread
        qtype = rng.choices(types, weights)[0]
        board.append({"slot": slot, "region": rng.choice(regions), "type": qtype, "lvl": qlvl, "rank": rank,
                      "stages": stage_count(rank, qtype)})
    return board


def quest_foe(q: dict, stage: int, rng=random):
    """(fa, en) name of the foe for a stage of a quest dict (or the dungeon dict stored in the fight)."""
    a = ADVENTURES[q["region"]]
    total = int(q.get("stages") or q.get("total"))
    if stage == total:
        return a["boss"] if QTYPES[q["type"]]["boss"] else a["foes"][-1]
    return rng.choice(a["foes"][:-1] or a["foes"])


def title(q: dict, lang: str) -> str:
    a = ADVENTURES[q["region"]]
    k = "fa" if lang == "fa" else "en"
    return f"{RANKS[q['rank']]} · {QTYPES[q['type']][k]}: {a[k]}"


def reward_preview(q: dict) -> dict:
    r = q["rank"]
    return {"items": item_count(r, q["type"]), "item_idx": ITEM_IDX[r], "mastery": ZNP_MASTERY[r], "bond": ZNP_BOND[r]}
