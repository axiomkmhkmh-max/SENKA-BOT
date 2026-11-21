"""Ability families: the player's loadout, learning cards, levelling and the one-time migration (Nov 21).

Stored on the character as `abil`:
  {"lv": {family or fixed id: level}, "own": {family: [type ids]}, "pick": {button: type id}, "kpick": {"had": n, "bak": n}}
Defaults (today's buttons) are always owned. Levels start at 1; the old technique mastery (`tech_lvl`) became the level.
"""
import time

import data_abilities as AB
from database import col
from service_player import get_char, add_coins


def _legacy_lv(ch: dict, fam: str) -> int:
    """Family level before the migration wrote one: the old mastery of the race technique on that button."""
    best = 1
    for act, f, _i in AB.slots_of(ch.get("race")):
        if f == fam and act in ("t1", "t2", "t3"):
            best = max(best, int((ch.get("tech_lvl") or {}).get(act, 0) or 0))
    return max(1, min(AB.LV_MAX, best))


def family_level(ch: dict, fam: str) -> int:
    lv = ((ch.get("abil") or {}).get("lv") or {}).get(fam)
    return max(1, min(AB.LV_MAX, int(lv))) if lv else _legacy_lv(ch, fam)


def owned(ch: dict) -> dict:
    """Types the player owns per family: the race defaults plus every learned card."""
    out = AB.default_owned(ch.get("race"))
    for fam, lst in ((ch.get("abil") or {}).get("own") or {}).items():
        for tid in lst or []:
            if AB.type_of(fam, tid) and tid not in out.setdefault(fam, []):
                out[fam].append(tid)
    return out


def picks(ch: dict) -> dict:
    """The type each button fires: the stored pick when it is still valid, else the race default."""
    race = ch.get("race")
    own, stored = owned(ch), (ch.get("abil") or {}).get("pick") or {}
    out = {}
    for act, fam, _i in sorted(AB.slots_of(race), key=lambda s: (s[1], s[2])):
        if fam in AB.KIDO_FAMS:
            continue
        tid = stored.get(act)
        taken = {out[a] for a, f, _j in AB.slots_of(race) if f == fam and a in out}
        if not tid or tid not in own.get(fam, []) or tid in taken:
            tid = (AB.DEFAULTS.get(race) or {}).get(act)
            if tid in taken:  # Arrancar: the default of this slot is already on the other Cero button
                tid = next((t for t in own.get(fam, []) if t not in taken), tid)
        out[act] = tid
    return out


def loadout(ch: dict) -> dict:
    """What build_player puts on the fighter: ab (buttons), abx (fixed levels), kpick and klv (Kidō)."""
    race = ch.get("race")
    if race not in AB.RACE_SLOTS:
        return {}
    pk = picks(ch)
    ab = {}
    for act, fam, _i in AB.slots_of(race):
        if fam in AB.KIDO_FAMS:
            continue
        ab[act] = {"fam": fam, "tid": pk[act], "lv": family_level(ch, fam)}
    abx = {fid: family_level(ch, fid) for fid in AB.RACE_FIXED.get(race, [])}
    out = {"ab": ab, "abx": abx}
    if any(f in AB.KIDO_FAMS for _a, f, _i in AB.slots_of(race)):
        out["klv"] = {"had": family_level(ch, "hado"), "bak": family_level(ch, "bakudo")}
        kp = (ch.get("abil") or {}).get("kpick") or {}
        known = ch.get("kido") or {}
        out["kpick"] = {b: int(kp[b]) for b in ("had", "bak") if kp.get(b) and int(kp[b]) in (known.get(b) or [])}
    return out


# ---- player actions -------------------------------------------------------------------------------------------------
async def set_pick(uid: int, act: str, tid: str) -> str:
    ch = await get_char(uid)
    if not ch:
        return "nochar"
    race = ch.get("race")
    fam = next((f for a, f, _i in AB.slots_of(race) if a == act), None)
    if not fam or fam in AB.KIDO_FAMS:
        return "bad"
    if tid not in owned(ch).get(fam, []):
        return "notowned"
    others = [a for a, f, _i in AB.slots_of(race) if f == fam and a != act]
    pk = picks(ch)
    swap = {}
    for a in others:
        if pk.get(a) == tid:  # Arrancar: the type was on the other Cero button, so the two buttons swap
            swap[a] = pk.get(act)
    upd = {f"abil.pick.{act}": tid, **{f"abil.pick.{a}": v for a, v in swap.items()}}
    if await col("battles").find_one({"user_id": uid, "status": "active"}, {"_id": 1}):
        return "infight"  # the choice is locked during a fight
    await col("characters").update_one({"user_id": uid}, {"$set": upd})
    return "ok"


async def set_kpick(uid: int, branch: str, n: int) -> str:
    ch = await get_char(uid)
    if not ch or branch not in ("had", "bak"):
        return "bad"
    if int(n) not in ((ch.get("kido") or {}).get(branch) or []):
        return "notowned"
    if await col("battles").find_one({"user_id": uid, "status": "active"}, {"_id": 1}):
        return "infight"
    await col("characters").update_one({"user_id": uid}, {"$set": {f"abil.kpick.{branch}": int(n)}})
    return "ok"


def card_fits(ch: dict, item: dict) -> bool:
    eff = (item or {}).get("effect") or {}
    return eff.get("type") == "ab_card" and ch.get("race") in (eff.get("races") or [])


async def learn(uid: int, item_id: str):
    """Use an ability card from the bag: opens its type (the card is spent). A type already owned stays in the bag
    as upgrade material. Returns (status, info)."""
    from data_items import ALL
    from service_economy import inv_remove
    it = ALL.get(item_id)
    ch = await get_char(uid)
    if not it or not ch:
        return "bad", None
    eff = it.get("effect") or {}
    if not card_fits(ch, it):
        return "race", None
    fam, tid = eff["fam"], eff.get("tid")
    if not tid:
        return "fixed", fam  # a fixed ability card: it only levels up (panel)
    if tid in owned(ch).get(fam, []):
        return "dup", fam
    if not await inv_remove(uid, item_id, 1):
        return "missing", None
    await col("characters").update_one({"user_id": uid}, {"$addToSet": {f"abil.own.{fam}": tid}})
    return "ok", (fam, tid)


def dup_cards(ch: dict, inv_items: dict, fam: str) -> list:
    """Cards in the bag that count as duplicates for this family: types already owned (or the fixed ability's own
    card). Kidō masteries take Kidō cards of spells already known."""
    from data_items import ALL
    out = []
    if fam in AB.KIDO_FAMS:
        branch = AB.KIDO_FAMS[fam]["branch"]
        known = set((ch.get("kido") or {}).get(branch) or [])
        for iid, q in inv_items.items():
            e = (ALL.get(iid) or {}).get("effect") or {}
            if q > 0 and e.get("type") == "kido" and e.get("branch") == branch and int(e.get("num", -1)) in known:
                out.append((iid, q))
        return out
    if fam in AB.FIXED:
        iid = AB.fixed_card_id(fam)
        q = int(inv_items.get(iid, 0))
        return [(iid, q)] if q > 0 else []
    own = set(owned(ch).get(fam, []))
    for tid in own:
        iid = AB.card_id(fam, tid)
        q = int(inv_items.get(iid, 0))
        if q > 0:
            out.append((iid, q))
    return out


async def upgrade(uid: int, fam: str):
    """Raise a family (or fixed ability, or Kidō mastery) one level: duplicate cards and coins. Returns (status, info)."""
    from service_economy import inv_get, inv_remove
    ch = await get_char(uid)
    if not ch:
        return "bad", None
    race = ch.get("race")
    fams = {f for _a, f, _i in AB.slots_of(race)} | set(AB.RACE_FIXED.get(race, []))
    if fam not in fams:
        return "bad", None
    lv = family_level(ch, fam)
    cost = AB.upgrade_cost(lv)
    if not cost:
        return "max", lv
    cards, coins = cost
    inv = await inv_get(uid)
    have = dup_cards(ch, inv.get("items") or {}, fam)
    if sum(q for _i, q in have) < cards:
        return "cards", (cards, sum(q for _i, q in have))
    if int(ch.get("coins", 0)) < coins:
        return "coins", coins
    if not await add_coins(uid, -coins, "ability_up"):
        return "coins", coins
    taken = []
    need = cards
    for iid, q in sorted(have, key=lambda x: -x[1]):
        n = min(q, need)
        if n and await inv_remove(uid, iid, n):
            taken.append((iid, n))
            need -= n
        if need <= 0:
            break
    if need > 0:  # a card vanished in between (trade, sale): give everything back
        from service_economy import inv_add
        for iid, n in taken:
            await inv_add(uid, iid, n, force=True, keep=True)
        await add_coins(uid, coins, "ability_up_refund")
        return "cards", (cards, cards - need)
    await col("characters").update_one({"user_id": uid}, {"$set": {f"abil.lv.{fam}": lv + 1}})
    return "ok", lv + 1


# ---- one-time migration -----------------------------------------------------------------------------------------------
MIGRATION_ID = "ability_families_v1"


async def migrate_once() -> int:
    """tech_lvl -> family level, old race technique cards -> duplicates of the family's default type, and one free stat
    reset for everyone (abilities now draw on their own stats). Runs once."""
    if await col("migrations").find_one({"_id": MIGRATION_ID}):
        return 0
    from data_races import RACES, STATS
    moved = 0
    async for ch in col("characters").find({}, {"user_id": 1, "race": 1, "stats": 1, "tech_lvl": 1, "abil": 1}):
        race = ch.get("race")
        if race not in AB.RACE_SLOTS:
            continue
        upd = {"respec_notice": True, "abil_notice": False}
        lv = {}
        for act, fam, _i in AB.slots_of(race):
            if act in ("t1", "t2", "t3"):
                old = int((ch.get("tech_lvl") or {}).get(act, 0) or 0)
                if old > 1:
                    lv[fam] = max(lv.get(fam, 1), min(AB.LV_MAX, old))
        for fam, n in lv.items():
            if not ((ch.get("abil") or {}).get("lv") or {}).get(fam):
                upd[f"abil.lv.{fam}"] = n
        base = RACES[race]["stats"] if race in RACES else {}
        alloc = sum(max(0, int((ch.get("stats") or {}).get(k, 0)) - int(base.get(k, 0))) for k in STATS)
        op = {"$set": {**upd, "stats": {k: int(base.get(k, 0)) for k in STATS}}}
        if alloc:
            op["$inc"] = {"points": alloc}
        r = await col("characters").update_one({"_id": ch["_id"], "stats": ch.get("stats")}, op)
        moved += int(bool(r.modified_count))
    # old technique cards in bags become cards of the family's default type (same count)
    async for inv in col("inventories").find({"items": {"$exists": True}}, {"user_id": 1, "items": 1}):
        inc, unset = {}, {}
        for iid, q in (inv.get("items") or {}).items():
            if not iid.startswith("rc_") or q <= 0:
                continue
            parts = iid.split("_")
            if len(parts) < 4:
                continue
            new = AB.old_card_to_new(parts[1], parts[2])
            if new:
                inc[f"items.{new}"] = inc.get(f"items.{new}", 0) + int(q)
                unset[f"items.{iid}"] = ""
        if inc:
            await col("inventories").update_one({"_id": inv["_id"]}, {"$inc": inc, "$unset": unset})
    await col("migrations").update_one({"_id": MIGRATION_ID}, {"$set": {"moved": moved, "at": int(time.time())}}, upsert=True)
    return moved


ABIL_NOTICE = {
    "fa": "⚔️ <b>پنل توانایی‌ها باز شد!</b>\n\n"
          "هر دکمه‌ی ویژه‌ی نژادت حالا یک خانواده است با نوع‌های مختلف (مثلاً ۲۰ نوع سرو، شونپو، اوتسوسمی، سنکا...).\n"
          "• با کارت هر نوع، آن نوع باز می‌شود؛ کارت تکراری + سکه لِوِل خانواده را تا ۱۰ بالا می‌برد.\n"
          "• قبل از نبرد انتخاب کن هر دکمه کدام نوع را بزند.\n"
          "• HP همه ۶ برابر شد و اکس‌پی فارم هم ۶ برابر: نبردها طولانی‌تر و حماسی‌تر.\n"
          "• هوهوی بیشتر = جاخالی بیشتر؛ حالت جانبی رایگان شد (هوهو ×۲، آسیب نصف).\n\n"
          "📊 همه‌ی امتیازهای استتت هم یک بار رایگان برگشت؛ دوباره پخششان کن.",
    "en": "⚔️ <b>The ability panel is open!</b>\n\n"
          "Every special button of your race is now a family with many types (20 Ceros, Shunpo, Utsusemi, Senka...).\n"
          "• A type's card opens it; duplicate cards + coins raise the family up to level 10.\n"
          "• Before a fight, pick which type each button fires.\n"
          "• Everyone's HP is x6 and farm XP is x6 too: longer, more epic fights.\n"
          "• More Hohō = more dodging; the side stance is free now (Hohō x2, half damage).\n\n"
          "📊 All your stat points came back once, for free: spend them again.",
}


async def notify(bot, stop) -> None:
    from service_raceweapon import broadcast_flag
    await broadcast_flag(bot, stop, "abil_notice", ABIL_NOTICE, {"fa": "⚔️ توانایی‌ها", "en": "⚔️ Abilities"}, "abl")
