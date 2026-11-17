"""Battle Rank service (rules in data_battlerank): rank updates after normal battles, the season reset, the once-per-season
division rewards, the leaderboard and the Kenpachi crowning at the end of a season.

Character fields: br (rank points), br_season (season those points belong to), br_claimed (divisions already rewarded
this season), br_best (best division this season), br_flees, kenpachi_art (the Kenpachi artifact, forever),
kenpachi_seasons (seasons won). A season change is applied lazily on the player's next rank update.
"""
import random
import time

from data_battlerank import (DIVS, carried, division, flee_cost, loss_cost, reward_of, season_of, title, win_gain)
from data_items import EVO_BY_RARITY
from data_weapons import RARITIES
from database import col
from service_economy import inv_add
from service_player import get_char


def current(ch: dict, now: float = None):
    """(rank points, claimed divisions) of this season for a character, with the season reset applied."""
    season = season_of(now or time.time())
    if ch.get("br_season") == season:
        return int(ch.get("br", 0) or 0), list(ch.get("br_claimed") or [])
    if ch.get("br_season") is None:
        return 0, []
    return carried(int(ch.get("br", 0) or 0)), []


async def apply(uid: int, kind: str, turns: int = 1, elite: bool = False) -> dict:
    """kind: win | loss | flee. Returns {delta, rp, title_fa, title_en, up, down, rewards: [(div, [item ids])]}."""
    now = time.time()
    season = season_of(now)
    for _ in range(6):
        ch = await get_char(uid)
        if not ch:
            return {}
        rp0, claimed = current(ch, now)
        if kind == "win":
            delta = win_gain(rp0, turns, elite)
        elif kind == "loss":
            delta = -loss_cost(rp0)
        else:
            delta = -flee_cost(rp0)
        rp1 = max(0, rp0 + delta)
        k0, k1 = division(rp0), division(rp1)
        new_divs = [k for k in range(0, k1 + 1) if k not in claimed] if kind == "win" else []
        upd = {"$set": {"br": rp1, "br_season": season, "br_claimed": sorted(set(claimed) | set(new_divs)),
                        "br_best": max(k1, int(ch.get("br_best", 0) or 0) if ch.get("br_season") == season else k1)}}
        if kind == "flee":
            upd["$inc"] = {"br_flees": 1}
        flt = {"user_id": uid, "br": ch.get("br"), "br_season": ch.get("br_season")}
        r = await col("characters").update_one(flt, upd)
        if r.modified_count:
            rewards = []
            for k in new_divs:
                rewards.append((k, await grant_reward(uid, ch.get("race", "human"), k)))
            return {"delta": rp1 - rp0, "rp": rp1, "title_fa": title(rp1, "fa"), "title_en": title(rp1, "en"),
                    "up": k1 > k0, "down": k1 < k0, "rewards": rewards}
    return {}


async def grant_reward(uid: int, race: str, div: int, rng=random) -> list:
    """The chest of a division, in its tier's colour. Never lost to a full bag."""
    from service_extras import pick_item
    from service_racegear import random_armour
    kind, colour = reward_of(div)
    items = []
    if kind == "consumable":
        items.append(pick_item(rng.choice(("potion", "book", "charm")), [colour], rng))
    elif kind == "equipment":
        items.append(random_armour(race, colour, rng))
    else:  # weapon materials: forge materials of the colour and an evolution relic (raises the race weapon's colour)
        items += [pick_item("material", [colour], rng) for _ in range(3)]
        pool = EVO_BY_RARITY.get(RARITIES[min(3, colour)]) or EVO_BY_RARITY["Common"]
        items.append(rng.choice(pool))
    out = []
    for iid in items:
        if iid and await inv_add(uid, iid, 1, force=True):
            out.append(iid)
    return out


async def leaderboard(season: int = None, limit: int = 10) -> list:
    season = season_of(time.time()) if season is None else season
    return await col("characters").find({"br_season": season, "br": {"$gt": 0}},
                                        {"user_id": 1, "name": 1, "br": 1, "race": 1}).sort([("br", -1), ("user_id", 1)]).limit(limit).to_list(limit)


async def kenpachi_now():
    """The current season's number one (the live Kenpachi), or None."""
    top = await leaderboard(limit=1)
    return top[0] if top else None


async def crown_due(now: float = None):
    """At a season's end: its number one becomes Kenpachi and gets the Kenpachi artifact (once, forever).
    Returns {"season", "user_id", "name"} when a crowning happened, else None. Safe to call often."""
    prev = season_of(now or time.time()) - 1
    if prev < 0:
        return None
    marker = f"br_crown_{prev}"
    if await col("migrations").find_one({"_id": marker}):
        return None
    claim = await col("migrations").update_one({"_id": marker}, {"$setOnInsert": {"at": int(time.time())}}, upsert=True)
    if not getattr(claim, "upserted_id", None):
        return None  # another instance crowned it
    top = await leaderboard(prev, 1)
    if not top:
        return None
    w = top[0]
    await col("characters").update_one({"user_id": w["user_id"]},
                                       {"$set": {"kenpachi_art": True}, "$addToSet": {"kenpachi_seasons": prev}})
    await col("migrations").update_one({"_id": marker}, {"$set": {"user_id": w["user_id"], "rp": w.get("br", 0)}})
    return {"season": prev, "user_id": w["user_id"], "name": w.get("name", "")}


DIVS_ALL = list(range(DIVS))
