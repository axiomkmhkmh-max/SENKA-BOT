"""Skin service (اسکین‌ها). Ownership lives on the character: `skins_owned` (list) and `skin` (equipped id).

No migration is needed: old characters simply do not have the two fields, and every read uses `.get`.
Write rules (same as the rest of the bot): every change is one conditional update, so two parallel taps cannot
grant the same skin twice or equip a skin the player does not own.
"""
import random

from data_skins import BY_RARITY, DUP_COINS, SKINS, skin_by_id
from database import col
from service_player import add_coins, get_char


def pick_skin(rarity: str, owned, rng=random):
    """A random skin of this rarity, preferring one the player does not own yet. None when the rarity is empty."""
    pool = BY_RARITY.get(rarity) or []
    if not pool:
        return None
    owned = set(owned or [])
    fresh = [s for s in pool if s not in owned]
    return rng.choice(fresh or pool)


async def grant_skin(uid: int, sid: str, source: str = "wheel"):
    """Give a skin. Returns (status, coins): new | dup (paid as coins) | bad | noreg."""
    s = skin_by_id(sid)
    if not s:
        return "bad", 0
    r = await col("characters").update_one({"user_id": uid, "skins_owned": {"$ne": sid}},
                                           {"$addToSet": {"skins_owned": sid}})
    if r.modified_count:
        return "new", 0
    ch = await get_char(uid)
    if not ch:
        return "noreg", 0
    coins = int(DUP_COINS[s["rarity"]])
    await add_coins(uid, coins, f"skin_dup:{source}")
    return "dup", coins


async def equip_skin(uid: int, sid: str) -> str:
    """ok | bad | notowned."""
    if not skin_by_id(sid):
        return "bad"
    r = await col("characters").update_one({"user_id": uid, "skins_owned": sid}, {"$set": {"skin": sid}})
    return "ok" if r.matched_count else "notowned"


async def unequip_skin(uid: int) -> str:
    await col("characters").update_one({"user_id": uid}, {"$set": {"skin": None}})
    return "ok"


async def owned_and_equipped(uid: int):
    ch = await get_char(uid) or {}
    return list(ch.get("skins_owned") or []), ch.get("skin")


def all_skin_ids():
    return list(SKINS)
