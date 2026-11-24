"""PvE, dungeons and PvP built on the pure engine. All outcomes are server-side."""
import asyncio
import logging
import random
import time
import uuid
from datetime import datetime, timedelta, timezone

from data_crafting import player_bonus, tagged_name, temper_def
from data_extras2 import (LEVEL_BOSS_REWARD, LEVEL_BOSS_SCALE, LEVEL_BOSSES, MINI_BOSS_CHANCE, MINI_BOSS_NAMES, MINI_BOSS_RELIC,
                          MINI_BOSS_REWARD, MINI_BOSS_SCALE, BOSS_XP_BONUS)
from data_guildquest import XP_BONUS_RANK
from data_items import ALL
from data_races import DIFFICULTY, DUNGEON_ENEMIES, DUNGEONS, LOCATIONS, RACES, soft_stat

RATED_LEVEL_GAP = 50  # ranked duel: a winner more than this many levels above the loser is unrated (anti-farming)
from data_weapons import ELEMENTS
from data_zanpakuto import BLADE_STAGES, BLADE_STYLE
import engine as E
from data_misc import DUEL
from database import col, game_settings
from service_log import log_event
from service_economy import gacha_doc, inv_remove, party_bonus, roll_drop, inv_add
from service_player import add_coins, add_xp, bump_quest, get_char, max_hp, max_reiatsu
from service_worldcore import mods_for

_bg_tasks: set = set()


def _bg(coro):
    """Fire-and-forget for bookkeeping the player does not wait for (world points, battle log)."""
    task = asyncio.ensure_future(coro)
    _bg_tasks.add(task)

    def _done(t):
        _bg_tasks.discard(t)
        if not t.cancelled() and t.exception():
            logging.getLogger("senka.combat").error("background task failed", exc_info=t.exception())
    task.add_done_callback(_done)


ENEMY_K = {"s": 1.6, "d": 1.2, "h0": 60, "h1": 30, "a": 2.6, "ar": 0.9}
RANKS = [(0, "E"), (1100, "D"), (1250, "C"), (1400, "B"), (1600, "A"), (1850, "S"), (2150, "SS"), (2500, "SSS")]


def rank_letter(rating: int) -> str:
    out = "E"
    for thr, name in RANKS:
        if rating >= thr:
            out = name
    return out


def rank_label(rating: int, lang: str) -> str:
    from i18n import t
    letter = rank_letter(rating)
    return f"{letter} · {t(lang, 'rank_' + letter)}"


def _exp():
    return datetime.now(timezone.utc) + timedelta(hours=2)


KIDO_RACES = ("shinigami", "visored")  # only these learn Hadō / Bakudō (same rule as the Kidō learning path)


async def refund_kido_points(ch: dict) -> dict:
    """One-time fix for characters of other races who put points into Kidō: give the points back to spend.
    Runs once per character (kido_refunded) and only moves points above the race's base Kidō."""
    if ch.get("race") in KIDO_RACES or ch.get("kido_refunded"):
        return ch
    base = int(RACES[ch["race"]]["stats"].get("kido", 0))
    extra = max(0, int(ch["stats"].get("kido", 0)) - base)
    ch["stats"] = {**ch["stats"], "kido": base}
    ch["points"] = int(ch.get("points", 0)) + extra
    ch["kido_refunded"] = True
    await col("characters").update_one({"user_id": ch["user_id"]},
                                       {"$set": {"stats.kido": base, "points": ch["points"], "kido_refunded": True}})
    return ch


async def build_player(ch: dict, name: str = None):
    ch = await refund_kido_points(ch)
    race = RACES[ch["race"]]
    gs = await game_settings()
    stats = dict(ch["stats"])
    armor = 0
    perks = {}
    for f in ("armor_id", "acc_id", "charm_id"):
        it = ALL.get(ch.get(f) or "")
        if not it:
            continue
        if it.get("race") and it["race"] != ch.get("race"):
            continue  # another race's armour gives nothing (it cannot be worn; old saves are covered too)
        for k, v in (it.get("perk") or {}).items():  # race armour perks (data_racegear)
            perks[k] = perks.get(k, 0.0) + float(v)
        d = it["stats"].get("def", 0)
        if f == "armor_id" and d:
            d = temper_def(d, (ch.get("armor_plus") or {}).get(it["_id"], 0), gs)
        armor += d
        if "stat" in it["stats"]:
            stats[it["stats"]["stat"]] += it["stats"]["bonus"]
    # --- NEW BLEACH VIRAL SYSTEM: Hogyoku doubles Reiatsu, a failed theft halves it for a while ---
    from data_artifacts import reiatsu_mult
    stats["reiatsu"] = stats["reiatsu"] * reiatsu_mult(ch)
    g = await gacha_doc(ch["user_id"])
    pb = party_bonus(ch.get("party", []), g.get("chars", {}))
    bn = player_bonus(ch, ALL, gs)  # evolution, pet role, relics, temporary buffs
    mods = dict(race["mods"])
    # Race evolution (data_evolution): one 5-stage canon path per race, cumulative bonuses. Multipliers go on the race
    # modifiers; the rest (release turns, mask rage, Cero power...) rides on the fighter as fighter["evo"] for the engine.
    from data_crafting import evo_stage
    from data_evolution import evo_bonus
    evb = evo_bonus(ch["race"], evo_stage(ch))
    for key in ("dmg", "def", "hp", "kido"):
        if evb.get(key):
            mods[key] = mods.get(key, 1.0) * (1 + evb[key])
    for key in ("crit", "pierce"):
        if evb.get(key):
            mods[key] = mods.get(key, 0.0) + evb[key]
    for key, v in perks.items():  # race armour perks: multipliers on dmg/def/hp/kido, flat crit/pierce, regen below
        if key in ("dmg", "def", "hp", "kido"):
            mods[key] = mods.get(key, 1.0) * (1 + v)
        elif key in ("crit", "pierce"):
            mods[key] = mods.get(key, 0.0) + v
    mods["dmg"] = mods.get("dmg", 1.0) * (1 + pb.get("dmg", 0) + bn["dmg"])
    from data_gangs import xcution_dmg_mult
    mods["dmg"] *= xcution_dmg_mult(ch)  # Xcution rank: +2% damage per rank for members
    mods["def"] = mods.get("def", 1.0) * (1 + pb.get("def", 0) + bn["def"])
    # Preserve race/evolution Kidō modifiers while adding companion bonuses.
    mods["kido"] = mods.get("kido", 1.0) * (1 + pb.get("kido", 0))
    mods["crit"] = mods.get("crit", 0) + bn["crit"]
    mods["regen"] = bn["regen"] + evb.get("regen", 0.0) + perks.get("regen", 0.0)
    hp = max_hp(ch["level"], soft_stat(stats["hakuda"]), mods.get("hp", 1.0))
    re = max_reiatsu(ch["level"], soft_stat(stats["reiatsu"]))
    wid = ch.get("weapon_id") or ""
    w = ALL.get(wid)
    if w:
        plus = (ch.get("weapon_plus") or {}).get(wid, 0)
        w = dict(w, attack=w["attack"] * (1 + 0.06 * plus))
    zstate = ch.get("zanpakuto") or {}
    from znp_lock import blade_allowed  # owner-only blades give nothing to other players
    if zstate.get("blade_id") and not await blade_allowed(ch.get("user_id"), zstate["blade_id"]):
        zstate = dict(zstate, blade_id=None)
    from data_zanpakuto import bond_value
    bond = bond_value(ch)  # per blade: the bond belongs to the chosen blade, not to the weapon in hand
    # Artifact signature effects are real engine modifiers, not display-only bonuses.
    artifact_id = ch.get("artifact") or ""
    from data_artifacts import ART_BY_ID
    artifact_effect = (ART_BY_ID.get(artifact_id) or {}).get("effect") or {}
    if artifact_effect.get("kind") == "hogyoku_evolution":
        mods["artifact_hogyoku"] = True
    if artifact_effect.get("kind") == "soulking":
        hp = int(hp * float(artifact_effect.get("hp_mult", 1.20)))
        mods["regen"] += float(artifact_effect.get("regen", 0.12))
        mods["dmg"] *= 1.0 + float(artifact_effect.get("dmg", 0.08))
        mods["artifact_lives"] = int(artifact_effect.get("uses", 1))
        mods["artifact_revive_hp"] = float(artifact_effect.get("hp", 0.50))
    if ch.get("hogyoku"):
        mods["artifact_hogyoku"] = True
    if artifact_effect.get("kind") == "lifesteal":
        mods["artifact_lifesteal"] = float(artifact_effect.get("value", 0.08))
    elif artifact_effect.get("kind") == "precognition":
        mods["dodge"] = mods.get("dodge", 0.0) + float(artifact_effect.get("dodge", 0.10))
    elif artifact_effect.get("kind") == "revive":
        mods["artifact_lives"] = int(artifact_effect.get("uses", 1))
        mods["artifact_revive_hp"] = float(artifact_effect.get("hp", 0.50))
    elif artifact_effect.get("kind") == "shadow_echo":
        mods["artifact_shadow_echo"] = float(artifact_effect.get("value", 0.10))
    if ch.get("hogyoku"):
        # The true Hōgyoku is not just a Reiatsu item: +25% max HP, +20% defence, base regeneration, one revival,
        # and an in-fight evolution (engine HOG_*) that makes it harder to kill the longer the battle lasts.
        hp = int(hp * 1.25)
        mods["def"] = mods.get("def", 1.0) * 1.20
        mods["regen"] = mods.get("regen", 0.0) + 0.04
        mods["artifact_lives"] = int(mods.get("artifact_lives", 0)) + 1
        mods["artifact_revive_hp"] = max(float(mods.get("artifact_revive_hp", 0.0)), 0.60)
        mods["hogyoku_true"] = True
    # Kyōka's release bonuses are applied by the actual Shikai/Bankai combat actions, not merely
    # because the character has unlocked those forms in the profile.
    # Release stages feed the existing weapon-skill multiplier; no parallel combat engine.
    stage = BLADE_STAGES.get(zstate.get("blade_id"), {})
    # Kyoka's bonuses are stateful: an unlocked Shikai/Bankai does not grant its combat multiplier until released.
    release_bonus = 0.0 if zstate.get("blade_id") == "kyoka_suigetsu" else ((0.10 + stage.get("shikai_bonus", 0.0)) if zstate.get("shikai") else 0.0)
    if zstate.get("bankai") and zstate.get("blade_id") != "kyoka_suigetsu":
        release_bonus += 0.12 + min(0.08, int(zstate.get("mastery", 0)) / 500) + stage.get("bankai_bonus", 0.0)
    zmult = 1 + min(1.0, bond / 500) + release_bonus  # bond adds up to +100% (500 bond); no 30 ceiling
    # Distinct release identities alter battle style rather than granting identical flat power.
    blade_style = {} if zstate.get("blade_id") == "kyoka_suigetsu" else BLADE_STYLE.get(zstate.get("blade_id"), {})
    if zstate.get("shikai") or zstate.get("bankai"):
        for stat, value in blade_style.items():
            if stat in ("dmg", "def", "kido"):
                mods[stat] = mods.get(stat, 1.0) * value
            elif stat == "crit":
                mods[stat] = mods.get(stat, 0.0) + value
    # Spells available in combat = the character's stored Hadō/Bakudō lists (race starter spells + anything
    # learned; learn_kido writes to both) merged with kido_learned. Starting from an empty set would strip
    # every existing character of their spells, because the engine only defaults when the key is missing.
    from service_bleach_systems import KIDO
    legacy = ch.get("kido") or {}
    had, bak, kaido = set(legacy.get("had") or [1]), set(legacy.get("bak") or [1]), set()
    if ch.get("race") not in KIDO_RACES:  # Arrancar, Hollow, Quincy and the rest have no Hadō or Bakudō
        had, bak, kaido = set(), set(), set()
    for spell_id in (set(ch.get("kido_learned") or []) if ch.get("race") in KIDO_RACES else ()):
        spell = KIDO.get(spell_id)
        if not spell:
            continue
        if spell["type"] == "Hadō":
            had.add(int(spell_id.replace("hado", "")))
        elif spell["type"] == "Bakudō":
            bak.add(int(spell_id.replace("bakudo", "")))
        elif spell["type"] == "Kaidō":
            kaido.add(spell_id)
    combat_kido = {"had": sorted(had), "bak": sorted(bak), "kaido": sorted(kaido)}
    # Bleach feel: the race's signature move, and the real technique name of a released blade (see data_bleachfx)
    from data_bleachfx import sig_for
    released = zstate.get("shikai") or zstate.get("bankai")
    mv = wid if released and w else None  # weapon id; render turns it into "<blade>: <technique>"
    fighter = E.new_fighter(name or tagged_name(ch, ALL), ch["level"], stats, hp, re, w, armor=armor, mods=mods, kido=combat_kido,
                            race=ch["race"], zmult=zmult, sig=sig_for(ch["race"]), mv=mv, gen=ch.get("gen_skill"),
                            bt=(__import__("data_zanpakuto").blade_technique(zstate.get("blade_id"))
                                if released and zstate.get("blade_id") and zstate.get("shikai") else None))
    fighter["evo"] = {k: v for k, v in evb.items() if k not in ("dmg", "def", "hp", "kido", "crit", "pierce", "regen")}
    fighter["blade"] = zstate.get("blade_id")  # Pack 1: the in-battle Shikai line speaks this blade's release command
    fighter["evs"] = evo_stage(ch)  # evolution stage: opens the canon race techniques (data_race_tech)
    fighter["tm"] = {k: int(v) for k, v in (ch.get("tech_lvl") or {}).items()}  # technique mastery (race technique cards)
    from service_abilities import loadout  # ability families: the type on each button, levels, the Kidō picks (Nov 21)
    fighter.update(loadout(ch))
    return fighter


DG_BOSS_HOHO, DG_FOE_HOHO = 0.40, 0.70   # dungeon boss Hohō -60%, other dungeon foes -30%


def make_enemy(level: int, scale: float, name: str, rng=random, sig=None):
    k = ENEMY_K
    s = (4 + level * k["s"]) * scale
    stats = {"zanjutsu": s, "kido": s * 0.6, "hakuda": (4 + level * k["d"]) * scale, "hoho": 6 + level * 0.5, "reiatsu": 5 + level}
    w = {"attack": (3 + level * k["a"]) * scale, "crit": 0.03, "element": rng.choice(ELEMENTS), "skills": [], "weapon_type": "melee"}
    from data_misc import ENEMY_HAKUDA_HP, HP_MULT
    # their Hakuda gives them HP too (Nov 21: Hakuda's effect on HP is x6 for players; enemies carry about twice the Hakuda)
    foe = E.new_fighter(name, level, stats, (k["h0"] + level * k["h1"] + (4 + level * k["d"]) * ENEMY_HAKUDA_HP) * scale * HP_MULT,
                        80 + level * 10, w,
                        armor=level * k["ar"] * scale, ai=True, sig=sig)
    foe["wild"] = True  # wild enemies never release (every player race can, since the release rework)
    return foe


def _rewards(level: int, scale: float, st: dict):
    from data_misc import FARM_XP_MULT
    # a win pays FARM_XP_MULT times the XP (Nov 21); coins stay as they were
    xp = (20 * level ** 1.25 + 20) * (scale if scale > 1 else 1.0) * FARM_XP_MULT
    # coins grow faster than the level (more than linear), so higher levels earn clearly more per fight:
    # Lv1 ≈ 20, Lv10 ≈ 97, Lv30 ≈ 297, Lv50 ≈ 537, Lv80 ≈ 972, Lv100 ≈ 1312 (was 16 / 70 / 190 / 310 / 490 / 610)
    coins = (12 + 8 * level + 0.05 * level ** 2) * (scale if scale > 1 else 1.0) * float(st["coin_rate"])
    return int(xp), int(coins)


def duel_xp(level: int, gs: dict, frac: float = 1.0) -> int:
    """XP of a duel win: pvp_xp_mult plain PvE wins at the same level (a duel is harder than a wild Hollow).
    It used to be a flat 30 + 8 per level, which at level 50 was ~3% of one PvE win."""
    return int(_rewards(level, 1.0, gs)[0] * float(gs.get("pvp_xp_mult", 1.5)) * frac)


# ---- PvE ---------------------------------------------------------------------------
async def active_pve(uid: int):
    return await col("battles").find_one({"user_id": uid, "mode": "pve", "status": "active"})


async def blocking_pve(uid: int) -> bool:
    """True while any open PvE fight (normal, dungeon, adventure, tower or evolution trial) is running: nothing else may
    start until it ends. A Soul Tower climb can be left for free with abandon_tower."""
    return bool(await active_pve(uid))


async def save_tower(uid: int) -> int:
    """Register the floor of the open tower fight as the next start (never beyond the floor after the best one).
    Returns that floor, or 0 when no tower fight is open."""
    doc = await active_pve(uid)
    d = (doc or {}).get("dungeon") or {}
    if not d.get("tower"):
        return 0
    ch = await get_char(uid)
    best = int(((ch or {}).get("tower") or {}).get("best", 0))
    floor = max(1, min(int(d.get("stage", 1)), best + 1))
    await col("characters").update_one({"user_id": uid}, {"$set": {"tower.saved": floor}})
    return floor


async def abandon_tower(uid: int) -> bool:
    """Close the open tower fight with no penalty and no reward. Atomic: only an active tower battle is closed."""
    r = await col("battles").update_one({"user_id": uid, "mode": "pve", "status": "active", "dungeon.tower": True},
                                        {"$set": {"status": "fled"}})
    return bool(r.modified_count)


DG_XP_MULT = 4.0        # Dungeon clears are the core progression loop; raise stage XP after the severe drop reported by players.
DG_SCALE_XP_EXP = 0.80  # Higher difficulty now contributes more of its actual challenge to XP.
FAST_KILL_XP = {1: 0.5, 2: 0.7}  # plain open-world fights won in 1 / 2 turns pay this share (one-tap farming paid 500K)
DG_FINAL_XP_MULT = 3.0  # The final stage pays a substantial completion bonus on top of the higher stage XP.
DG_STAGE3_HEAL_AT = 3   # the dungeon stage that starts with a breather
DG_STAGE3_HEAL = 0.25   # share of max HP restored when entering it (capped at full)


def _is_boss_stage(dungeon, tower_floor_flag) -> bool:
    """True for a dungeon's last stage and for a Soul Tower Warden floor (fight-type balance, see data_race_rules)."""
    if not dungeon:
        return False
    if dungeon.get("tower") or tower_floor_flag:
        from data_extras import TOWER_BOSS_EVERY
        return int(dungeon.get("stage", 0)) % TOWER_BOSS_EVERY == 0
    return dungeon.get("stage") == dungeon.get("total")


async def _hog_round_start(uid: int, lang: str, ch: dict, dungeon: dict):
    """One round of the Hōgyoku duel. The challenger plays it with the normal battle panel (every button, Cero included)
    against an AI copy of the holder's real build. Both sides are 'neutral': no Hōgyoku bonuses, no theft penalty, and
    the fight follows duel rules (race balance of duels, Konpaku lives), like a battlefield shadow."""
    from service_bleach_systems import apply_stance, neutral_char
    tch = await get_char(int(dungeon["tgt"]))
    if not ch or not tch:
        raise ValueError("Hōgyoku duel: a fighter is missing")
    rng = random.Random()
    ca, cb = neutral_char(ch), neutral_char(tch)
    player = await build_player(ca)
    foe = await build_player(cb, name="🔮 " + str(tch.get("name", "?")))
    for f, c in ((player, ca), (foe, cb)):
        apply_stance(f, c)
    foe["ai"] = True
    foe["foe"] = "pve"
    state = E.new_state(player, foe, rng, pvp=True)
    from service_fightfx import start as fx_start
    fx_start(state, rng, challenge=False)
    E.run_ai(state, rng)
    doc = {"sid": uuid.uuid4().hex[:8], "user_id": uid, "mode": "pve", "state": state, "status": "active", "rev": 0,
           "created_at": int(time.time()), "expire_at": _exp(), "scale": 1.0, "elite": False, "mini": False,
           "lvl": int(ch["level"]), "dungeon": dungeon, "trial": None, "loc": ch.get("location"), "lang": lang}
    await col("battles").insert_one(doc)
    return doc


async def _hog_round_settle(doc: dict, st: dict):
    """A Hōgyoku duel round is over: count it, then start the next round or settle the whole duel (theft or nothing)."""
    from data_artifacts import hog_duel_over
    d = doc["dungeon"]
    uid, victim = doc["user_id"], int(d["tgt"])
    winner = st.get("winner")
    if winner not in ("a", "b"):  # turn cap: the healthier fighter takes the round
        fa, fb = st["a"], st["b"]
        winner = "a" if fa["hp"] / max(1, fa["max_hp"]) >= fb["hp"] / max(1, fb["max_hp"]) else "b"
    won = winner == "a"
    wa, wb = int(d["wa"]) + (1 if won else 0), int(d["wb"]) + (0 if won else 1)
    seq = list(d["seq"]) + [winner]
    rep = {"pa": int(d["pa"]), "pb": int(d["pb"]), "rounds": seq, "wa": wa, "wb": wb, "hours": 0}
    out = {"win": won, "xp": 0, "coins": 0, "drop": None, "levels": 0, "next": None, "dungeon_done": False}
    info = {"done": False, "rep": rep, "round": int(d["round"]), "rounds_n": int(d["rounds_n"]), "victim": victim,
            "victim_name": d.get("tgt_name", "?")}
    verdict = hog_duel_over(wa, wb, int(d["rounds_n"]))
    if verdict is None:  # still undecided: the holder must still be the holder for another round to make sense
        h = await col("hogyoku").find_one({"_id": "main"})
        if not h or h.get("holder") != victim:
            verdict = "gone"
        else:
            try:
                nxt = await pve_start(uid, doc.get("lang", "fa"), dungeon={**d, "round": int(d["round"]) + 1, "wa": wa, "wb": wb, "seq": seq})
                out["next"] = nxt["sid"]
            except Exception:
                logging.getLogger("senka.combat").exception("hogyoku next round failed")
                verdict = "gone"
    if verdict is not None:
        info["done"] = True
        if verdict == "win":
            now = int(time.time())
            got = await col("hogyoku").find_one_and_update({"_id": "main", "holder": victim}, {
                "$set": {"holder": uid, "since": now},
                "$push": {"history": {"$each": [{"uid": uid, "from": victim, "at": now}], "$slice": -10}}})
            if got:
                await col("characters").update_one({"user_id": victim}, {"$unset": {"hogyoku": ""}})
                await col("characters").update_one({"user_id": uid}, {"$set": {"hogyoku": True}})
            else:
                verdict = "gone"  # the Hōgyoku changed hands while the duel was running
        info["result"] = verdict
        seq_txt = "".join("✅" if w == "a" else "❌" for w in seq)
        name = d.get("tgt_name", "?")
        text = ("هوگیوکو را از «" + str(name) + "» (" + str(victim) + ") دزدید" if verdict == "win"
                else "در دزدی هوگیوکو از «" + str(name) + "» (" + str(victim) + ") شکست خورد" if verdict == "fail"
                else "دوئل هوگیوکو با «" + str(name) + "» (" + str(victim) + ") بی‌نتیجه ماند (هوگیوکو دست‌به‌دست شد)")
        log_event("hog", uid, f"{text} | قدرت {rep['pa']} در برابر {rep['pb']} | دورها {seq_txt}", victim=victim, won=verdict == "win")
    out["hog"] = info
    return out


async def pve_start(uid: int, lang: str, scale: float = 1.0, dungeon: dict = None, carry: dict = None, trial: dict = None,
                    force_elite: bool = False):
    ch = await get_char(uid)
    if dungeon and dungeon.get("hog"):  # one round of the Hōgyoku duel (its own build of the fight, see _hog_round_start)
        return await _hog_round_start(uid, lang, ch, dungeon)
    gs = await game_settings()
    wm = await mods_for(ch["location"])
    rng = random.Random()
    loc = LOCATIONS[ch["location"]]
    pick = rng.choice(loc["enemies"])
    sig_race = loc.get("race")
    name = pick[0 if lang == "fa" else 1]
    from data_races import loc_band
    lo_, hi_ = loc_band(ch["location"], ch["level"], ch.get("race"))  # every world has its own band of enemy levels (Nov 21)
    lvl = max(1, rng.randint(lo_, hi_))
    tower = bool(dungeon and dungeon.get("tower"))
    fixed_dg = bool(dungeon and not tower and dungeon.get("id") in DUNGEONS)
    if fixed_dg:  # a dungeon's enemies keep the dungeon's own level, whatever level the player is
        lvl = int(DUNGEONS[dungeon["id"]]["level"])
        dg_foes = DUNGEON_ENEMIES.get(dungeon["id"])
        if dg_foes:  # the dungeon's own enemies (and its named boss on the last stage), not the player's location
            pick = dg_foes["boss"] if dungeon["stage"] == dungeon["total"] else rng.choice(dg_foes["enemies"])
            sig_race = dg_foes.get("race")
            name = pick[0 if lang == "fa" else 1]
    if dungeon and dungeon.get("gq"):  # Guild Quest: the quest's own random level and its region's foes
        from data_guildquest import quest_foe
        lvl = int(dungeon["qlvl"])
        pick = quest_foe(dungeon, int(dungeon["stage"]), rng)
        sig_race = None  # the foe's signature comes from its name, not from where the player happens to stand
        name = pick[0 if lang == "fa" else 1]
    if dungeon and dungeon.get("lboss"):  # level-band boss: fought at the player's own level, with its own signature
        lo, hi, b_fa, b_en, _c, b_race = LEVEL_BOSSES[int(dungeon["band"])]
        lvl, sig_race, pick = int(ch["level"]), b_race, (b_fa, b_en)
        name = pick[0 if lang == "fa" else 1]
    war = bool(dungeon and dungeon.get("war"))
    if war:  # event battlefield: the enemy faction's soldier, officer or general (a shadow is built from the player below)
        from service_war import war_foe
        lvl, name, scale, sig_race, pick = war_foe(dungeon, int(ch["level"]), lang, rng)
    if tower:  # Soul Tower: endless floors, a Warden every 5th
        from data_extras import TOWER_BOSS_EVERY, TOWER_ENEMIES
        floor = int(dungeon["stage"])
        scale = 0.85 * (1.045 ** (floor - 1))
        name = rng.choice(TOWER_ENEMIES)[0 if lang == "fa" else 1]
        if floor % TOWER_BOSS_EVERY == 0:
            scale *= 1.5
            name = "👑 " + name
    elif dungeon and not war:
        stage, total = dungeon["stage"], dungeon["total"]
        mult = DIFFICULTY[dungeon["diff"]] * (1 + 0.12 * (stage - 1))
        if stage == total:
            mult *= 1.6
            name = "👑 " + name
        elif stage == max(2, total // 2):
            mult *= 1.3
            name = "⚔️ " + name
        scale = LEVEL_BOSS_SCALE if dungeon.get("lboss") else mult
        if dungeon.get("lboss"):
            name = "👹 " + name
    mini = bool(not dungeon and not trial and not force_elite and rng.random() < MINI_BOSS_CHANCE)
    elite = bool(force_elite) or ((not dungeon) and (not trial) and rng.random() < 0.15)
    if mini:  # rare stronger foe in a normal fight (pays x3 and a guaranteed drop, see pve_settle)
        scale, name = MINI_BOSS_SCALE, "👺 " + rng.choice(MINI_BOSS_NAMES)[0 if lang == "fa" else 1]
        elite = False
    elif elite:
        scale, name = (1.55 if force_elite else 1.4), "💀 " + name
    if trial:
        scale, name = float(gs["evo_trial_scale"]) * (1 + 0.2 * (trial["stage"] - 1)), "🌀 " + name
    elif not tower and not fixed_dg and not war:  # dungeons and the battlefield stay fixed: no world-event scaling on top
        scale *= wm["enemy"]  # Hollow Threat + active world event strengthen every enemy
    player = await build_player(ch)
    player["x"]["bstack"] = int((ch.get("bount") or {}).get("stacks", 0))  # soul stacks: PvE only, settled in pve_settle
    if dungeon and dungeon.get("final_judgment"):
        player["fj_stage"] = int(dungeon.get("stage", 1))
        player["fj_no_potions"] = int(dungeon.get("stage", 1)) == 9
        player["fj_limited"] = int(dungeon.get("stage", 1)) == 3
        if carry and "artifact_lives" in carry:
            player["mods"]["artifact_lives"] = int(carry["artifact_lives"])
    if float(ch.get("almighty_until", 0) or 0) > time.time():  # Yhwach's Eye: one fatal blow is survived
        player["almighty"] = True
        player["lives"] = 1
    if carry:
        player["hp"] = max(1, int(player["max_hp"] * carry["hp"]))
        player["re"] = max(0, int(player["max_re"] * carry["re"]))
        if "gauge" in carry:  # the spirit gauge is the same fighter's courage: it does not reset between stages
            player["x"]["gauge"] = max(0, int(carry["gauge"]))
        if "artifact_lives" in carry:
            player["mods"]["artifact_lives"] = max(0, int(carry["artifact_lives"]))
        if carry.get("shield", 0) > 0:  # preserve any remaining barrier across encounters
            player["shield"] = int(carry["shield"])
    from data_bleachfx import enemy_sig
    if dungeon and dungeon.get("final_judgment"):
        fj_stage = int(dungeon.get("stage", 1))
        fj_wave = int(dungeon.get("wave", 1))
        if lang == "fa":
            name = {
                1: f"قاضی شماره {fj_wave}", 2: f"فرمانروای افسانه‌ای {fj_wave}",
                3: "نگهبان منطقه خاموش", 4: "غول ورطه", 5: "سه‌گانه ویرانگر",
                6: f"نگهبان موج {fj_wave}", 7: "بازتاب تاریک", 8: "هیولای پنج‌چهره",
                9: f"جلاد نهایی {fj_wave}", 10: "THE FINAL JUDGE",
            }.get(fj_stage, "داور نهایی")
        else:
            name = {
                1: f"Judgment Executioner {fj_wave}", 2: f"Legendary Sovereign {fj_wave}",
                3: "Warden of the Silent Zone", 4: "Abyssal Colossus", 5: "The Triune Cataclysm",
                6: f"Wave Warden {fj_wave}", 7: "Dark Reflection", 8: "The Fivefold Abomination",
                9: f"Final Executioner {fj_wave}", 10: "THE FINAL JUDGE",
            }.get(fj_stage, "The Final Judge")
    sig = enemy_sig(sig_race, pick)
    foe = make_enemy(lvl, scale, name, rng, sig=sig)
    if dungeon and dungeon.get("final_judgment"):
        fj_stage = int(dungeon.get("stage", 1))
        fj_wave = int(dungeon.get("wave", 1))
        foe["foe"] = "boss"
        foe["name"] = f"⚖️ {name}"
        # Multi-encounter stages are genuinely separate fights; HP/Reiatsu are carried forward by the event service.
        hp_k, dmg_k = {
            1: (1.20, 1.00), 2: (2.40, 1.15), 3: (3.00, 1.10), 4: (5.00, 1.45),
            5: (6.00, 1.65), 6: (1.35, 1.12), 7: (1.00, 1.00), 8: (8.00, 1.75),
            9: (3.20, 1.45), 10: (12.0, 2.10),
        }.get(fj_stage, (2.0, 1.0))
        # Later encounters in boss gauntlets gain a small escalation; it is bounded and deterministic.
        if fj_stage in (2, 9):
            hp_k *= 1.0 + 0.12 * (fj_wave - 1)
            dmg_k *= 1.0 + 0.05 * (fj_wave - 1)
        foe["max_hp"] = foe["hp"] = max(1, int(foe["max_hp"] * hp_k))
        foe["mods"]["dmg"] = float(foe["mods"].get("dmg", 1.0)) * dmg_k
        if fj_stage == 7:
            # The Dark Reflection copies the player's current build, including artifact procs and emergency lives.
            foe = await build_player(ch, name="🪞 Dark Reflection")
            # It is an AI-controlled boss, not a generic wild NPC: retain the complete player build and artifact effects.
            foe["ai"], foe["wild"], foe["foe"] = True, False, "boss"
            foe["mods"]["dmg"] *= 1.25
        if fj_stage in (2, 8, 10):
            foe["mods"]["dmg"] *= 1.10
    if dungeon and dungeon.get("final_judgment"):
        foe["foe"] = "boss"
    elif sig == "cero":  # hollow foe: tells the human passive who it is
        foe["foe"] = "hollow"
    elif _is_boss_stage(dungeon, tower):  # dungeon final stage or Soul Tower Warden: race balance by fight type
        foe["foe"] = "boss"
    else:  # every other wild enemy
        foe["foe"] = "pve"
    if foe["foe"] == "boss":  # a boss hits with its old power but has far more HP (damage is x2 for everyone else)
        from data_misc import BOSS_HP_MULT
        foe["max_hp"] = foe["hp"] = int(foe["max_hp"] * BOSS_HP_MULT)
    if (dungeon and not war and not tower and not dungeon.get("final_judgment")
            and dungeon.get("diff") == "legendary" and int(dungeon.get("stage", 1)) == 1):
        from data_misc import LEGEND_S1_HP, LEGEND_S1_DMG  # legendary dungeon, stage 1: more HP, weaker blows
        foe["max_hp"] = foe["hp"] = int(foe["max_hp"] * LEGEND_S1_HP)
        foe["mods"]["dmg"] = foe["mods"].get("dmg", 1.0) * LEGEND_S1_DMG
    if fixed_dg or (dungeon and not war and not tower and not dungeon.get("gq") and not dungeon.get("lboss")
                    and not (dungeon.get("final_judgment") and int(dungeon.get("stage", 1)) == 7)):
        # dungeon foes are slow (Nov 21): the boss of the last stage has 60% less Hohō, its guards 30% less, so a
        # high-level dungeon is not a wall of dodged blows and fast counter-hits
        foe["stats"]["hoho"] = foe["stats"]["hoho"] * (DG_BOSS_HOHO if dungeon["stage"] == dungeon["total"] else DG_FOE_HOHO)
    shadow = False
    if war:
        if foe["foe"] == "boss" and dungeon.get("kind") != "general":
            foe["foe"] = "pve"  # a battlefield soldier is not a dungeon boss (one-stage fight)
        if dungeon.get("kind") == "shadow" and dungeon.get("tgt"):  # an AI copy of a real enemy player, with their gear
            tch = await get_char(int(dungeon["tgt"]))
            if tch:
                from data_war import FACTIONS
                foe = await build_player(tch, name="🪞 " + FACTIONS[dungeon["fac"]][2] + " " + tch["name"])
                foe["ai"] = True
                foe["foe"] = "pve"
                lvl = int(tch["level"])
                shadow = True
    # a shadow is a real player's copy, so the fight follows duel rules (race balance of duels, Konpaku lives on both sides)
    state = E.new_state(player, foe, rng, pvp=shadow)
    if dungeon and dungeon.get("final_judgment"):
        stage = int(dungeon.get("stage", 1))
        state["final_judgment"] = {"stage": stage, "phases": 5 if stage in (8, 10) else 1, "phase": 1}
        state["cur"] = state["first"] = "a"  # Judgment encounters always begin with the challenger.
    from service_fightfx import start as fx_start  # the narrator's opening line, and a challenge for a normal fight
    fx_start(state, rng, challenge=not dungeon and not trial)
    if carry:  # next dungeon stage: the player always opens, so no free enemy hit lands on carried HP / the Bakudō barrier
        state["cur"] = state["first"] = "a"
    E.run_ai(state, rng)
    doc = {"sid": uuid.uuid4().hex[:8], "user_id": uid, "mode": "pve", "state": state, "status": "active", "rev": 0,
           "created_at": int(time.time()), "expire_at": _exp(), "scale": scale, "elite": elite, "mini": mini, "lvl": lvl,
           "dungeon": dungeon, "trial": trial, "loc": ch["location"], "lang": lang}
    await col("battles").insert_one(doc)
    return doc


async def _save(doc: dict, state: dict, extra: dict = None):
    upd = {"state": state, "rev": doc["rev"] + 1, "expire_at": _exp()}
    upd.update(extra or {})
    r = await col("battles").update_one({"sid": doc["sid"], "rev": doc["rev"], "status": "active"}, {"$set": upd})
    return bool(r.modified_count)


async def pve_act(uid: int, sid: str, action: str, potion: dict = None):
    doc = await col("battles").find_one({"sid": sid, "user_id": uid, "mode": "pve"})
    if not doc or doc["status"] != "active":
        return "gone", None, None
    st = doc["state"]
    if st.get("done"):
        # The fight already ended without being settled (e.g. the enemy's opening move killed a fighter who entered
        # the next dungeon stage with 1 HP). Settle it now so the result shows and the player is not stuck in it.
        return "ok", doc, ([], await pve_settle(doc))
    if st["cur"] != "a" or not st.get("awaiting"):
        return "notturn", None, None
    rng = random.Random()
    fj = doc.get("dungeon") or {}
    if action == "pot" and fj.get("final_judgment") and int(fj.get("stage", 0)) == 9:
        return "forbidden", doc, None
    if action == "pot" and potion:
        ev = E.do_potion(st, potion["type"], potion["pct"])
    else:
        ev = E.do_action(st, action, rng)
    ev += E.run_ai(st, rng)
    from service_fightfx import after_turn  # challenge progress and maybe a narrator line
    ev += after_turn(st, "pot" if action == "pot" else action, ev, rng)
    if not await _save(doc, st):
        return "stale", None, None
    doc["state"], doc["rev"] = st, doc["rev"] + 1
    outcome = await pve_settle(doc) if st["done"] else None
    return "ok", doc, (ev, outcome)


async def pve_settle(doc: dict):
    won = await col("battles").find_one_and_update({"sid": doc["sid"], "status": "active"}, {"$set": {"status": "done"}})
    if not won:
        return None
    if (doc.get("dungeon") or {}).get("hog"):  # Hōgyoku duel round: no XP, coins, drops or Battle Rank
        return await _hog_round_settle(doc, doc["state"])
    uid, st = doc["user_id"], doc["state"]
    gs = await game_settings()
    win = st["winner"] == "a"
    out = {"win": win, "xp": 0, "coins": 0, "drop": None, "levels": 0, "next": None, "dungeon_done": False}
    now = int(time.time())
    if (doc.get("dungeon") or {}).get("final_judgment"):
        from service_final_judgment import settle as settle_final_judgment
        return await settle_final_judgment(doc, win)
    from service_gangs_hook import bount_settle  # soul stacks left after the fight, +1 for a mansion win
    out["bstacks"] = await bount_settle(uid, doc, st)
    if (doc.get("dungeon") or {}).get("tower"):
        from service_extras import tower_settle
        out = await tower_settle(doc, win)
        await col("battle_logs").insert_one({"user_id": uid, "mode": "tower", "win": win, "lvl": doc["lvl"], "at": now})
        return out
    if win:
        xp, coins = _rewards(doc["lvl"], doc["scale"], gs)
        d = doc.get("dungeon")
        plain = not d and not doc.get("trial")
        # Battle Rank, win chain, world modifiers and the character are independent: fetched together (one wait, not four)
        from service_battlerank import apply as br_apply
        from service_extras import chain_win
        br_res, chain_res, wm, ch0 = await asyncio.gather(
            br_apply(uid, "win", int(st.get("turn", 1)), bool(doc.get("elite"))) if plain else asyncio.sleep(0),
            chain_win(uid) if plain else asyncio.sleep(0), mods_for(doc["loc"]), get_char(uid))
        if plain:  # Battle Rank: normal battles only
            out["br"] = br_res
        if not d and not doc.get("trial"):  # open worlds: stronger foes pay more, far weaker ones pay little
            from data_races import level_gap_k
            gk = level_gap_k(doc["lvl"], (ch0 or {}).get("level", doc["lvl"]))
            xp, coins = int(xp * gk), int(coins * gk)
            if gk != 1.0:
                out["gap_k"] = round(gk, 2)
        if plain:  # a one-tap farm win pays less than a real fight
            xp = int(xp * FAST_KILL_XP.get(int(st.get("turn", 3)), 1.0))
        if plain:  # win chain: consecutive plain victories raise coin/XP rewards
            cn, cm, cdrop, cfull, cms = chain_res  # chain_win returns 5 values (the milestone was added; 4 broke every win)
            xp, coins = int(xp * cm), int(coins * cm)
            out["chain"] = {"n": cn, "pct": round((cm - 1) * 100), "item": cdrop, "milestone": cms}
            if cfull:
                out["drop_full"] = out.get("drop_full") or cfull
        if d and d.get("gq"):  # Guild Quest: XP per stage (more for a higher rank), the items and release progress come at the end
            xp, coins = int(xp * float(gs["gq_xp_k"]) * (1 + XP_BONUS_RANK * int(d["rank"]))), 0
            if d["stage"] == d["total"]:
                xp = int(xp * float(gs["gq_final_xp_mult"]))
        elif d and d.get("war"):  # battlefield: a normal fight's pay, more for officers, shadows and the general
            from service_war import fight_k
            kx, kc = fight_k(d)
            xp, coins = int(xp * kx), int(coins * kc)
        elif d and d.get("lboss"):  # level boss: XP and coins x4, items from level_boss_loot
            xp, coins = int(xp * LEVEL_BOSS_REWARD * BOSS_XP_BONUS), int(coins * LEVEL_BOSS_REWARD)
        elif d:  # dungeons pay no coins (and no items): XP and dungeon points instead, so the XP is doubled on every stage
            xp, coins = int(xp * DG_XP_MULT), 0
            sc = max(1.0, float(doc.get("scale") or 1.0))
            xp = int(xp / sc ** (1 - DG_SCALE_XP_EXP))  # the difficulty multiplier counts at sc ** DG_SCALE_XP_EXP (abyss x8 -> x4.8 XP)
            if d["stage"] == d["total"]:
                xp *= DG_FINAL_XP_MULT
        if doc.get("mini"):
            xp, coins = int(xp * MINI_BOSS_REWARD * BOSS_XP_BONUS), int(coins * MINI_BOSS_REWARD)
        coins = int(coins * wm["coin"])
        coins = int(coins * (1 + player_bonus(ch0, ALL, gs)["coin"]))
        from service_fightfx import CHL_BONUS, CHL_CARD_CHANCE, result as fx_result
        chl = fx_result(st, True)
        if chl:
            out["chl"] = chl
            if chl["done"]:  # the fight's challenge was met: more pay, and maybe an ability card of the race
                xp, coins = int(xp * (1 + CHL_BONUS)), int(coins * (1 + CHL_BONUS))
                if random.random() < CHL_CARD_CHANCE:
                    from data_items import race_cards
                    pool = [c for c in race_cards(ch0.get("race"), random.choice(["Common", "Uncommon", "Rare"]))
                            if c.startswith("ab")] or race_cards(ch0.get("race"), "Common")
                    if pool:
                        cid = random.choice(pool)
                        await inv_add(uid, cid, 1, force=True)
                        out["chl"]["card"] = cid
        ch, lv, got = await add_xp(uid, xp, "pve")
        # independent writes: run together instead of one after another
        await asyncio.gather(add_coins(uid, coins, "pve") if coins > 0 else asyncio.sleep(0),
                             col("characters").update_one({"user_id": uid}, {"$inc": {"wins": 1, f"bond.{__import__('data_zanpakuto').bond_key(ch or {})}": 1, **({"zanpakuto.mastery": 1} if (ch0.get("zanpakuto") or {}).get("shikai") and int((ch0.get("zanpakuto") or {}).get("mastery", 0)) < int(gs.get("znp_mastery_cap", 1000)) else {}), **({"race_progress.hunts": 1} if (ch or {}).get("race") in ("hollow", "arrancar") else {})}}),
                             bump_quest(uid, "battle_win", 1))
        out.update(xp=got, coins=coins, levels=lv)
        from service_gangs_hook import gang_rewards  # Xcution siphon and Bount absorption (rules in data_gangs.py)
        out["gang"] = await gang_rewards(uid, doc) if not d else {}  # dungeons pay no coins (Bount absorption included)
        from service_worldstate import on_action, territory_income
        out["terr"] = await territory_income(uid, doc["loc"], coins, xp)
        chance = 1.0 if (doc["elite"] or doc.get("mini")) else 0.35
        if doc.get("mini") and random.random() < MINI_BOSS_RELIC:
            from data_items import EVO_BY_RARITY
            rid = random.choice(EVO_BY_RARITY.get("Rare") or EVO_BY_RARITY["Common"])
            await inv_add(uid, rid, 1, force=True)
            out["extra_drops"] = [rid]
        if not d and random.random() < chance:  # dungeons drop no items any more: XP, coins and dungeon points (DP) instead
            iid = await roll_drop(uid, source_mult=2.0 if doc["elite"] else 1.0)
            if await inv_add(uid, iid, 1):
                out["drop"] = iid
            else:
                out["drop_full"] = iid  # bag full: shown to the player (it used to vanish silently)
        if d and d["stage"] < d["total"]:
            f = st["a"]
            hp_frac = f["hp"] / f["max_hp"]
            if d["stage"] + 1 == DG_STAGE3_HEAL_AT and hp_frac < 1.0 and not (d.get("gq") and d.get("type") == "gauntlet"):
                # stage 3 was too hard on carried-over wounds: a breather restores part of the HP on the way in
                hp_frac = min(1.0, hp_frac + DG_STAGE3_HEAL)
                out["dg_heal"] = int(DG_STAGE3_HEAL * 100)
            nxt = await pve_start(uid, doc.get("lang", "en"), dungeon={**d, "stage": d["stage"] + 1},
                                  carry={"hp": hp_frac, "re": f["re"] / f["max_re"],
                                         "gauge": int((f.get("x") or {}).get("gauge", 0)),
                                         "shield": int(f.get("shield", 0))})  # a Bakudō barrier survives the stage change  # spirit carries over; HP and reiatsu are kept as fractions
            out["next"] = nxt["sid"]
        elif d and d.get("war"):  # battlefield: war points for the player's side (not a dungeon clear)
            from service_war import war_after_fight
            out["war"] = await war_after_fight(uid, doc, True)
        elif d and d.get("lboss"):  # level boss down: not a dungeon clear
            from service_adventure import level_boss_loot
            out["lboss"] = await level_boss_loot(uid, int(d["band"]))
        elif d and d.get("gq"):  # quest cleared: not a dungeon clear (no DP, cores or Visored trial)
            from service_adventure import gq_finish
            out["quest"] = await gq_finish(uid, d, gs)
        elif d:
            out["dungeon_done"] = True
            await bump_quest(uid, "dungeon_clear", 1)
            from service_dungeonshop import award_dp
            out["dp"] = await award_dp(uid, d)
            from service_dungeonshop import roll_special
            out["special"] = await roll_special(uid, d)  # dungeon-only item, small chance
            from service_cores import on_dungeon_clear  # rare Soul Core, abyss/legendary clears only
            await on_dungeon_clear(uid, d.get("diff", "normal"), d.get("id", ""))
            from data_races import unlocks_visored
            dch = await get_char(uid)
            if dch and unlocks_visored(dch.get("race"), d.get("id")):
                await col("characters").update_one({"user_id": uid}, {"$set": {"visored_unlocked": True}})  # Visored trial passed
        if doc.get("trial"):
            from service_crafting import evo_complete
            out["evo"] = await evo_complete(uid, doc["trial"]["stage"])
        _bg(on_action(uid, "dungeon_clear" if out["dungeon_done"] else "elite_win" if doc["elite"] else "pve_win", doc["loc"]))
    else:
        await col("characters").update_one({"user_id": uid}, {"$inc": {"losses": 1}})
        from service_fightfx import result as fx_result
        if st.get("chl"):
            out["chl"] = fx_result(st, False)
        if (doc.get("dungeon") or {}).get("war"):  # a lost battlefield fight: an enemy shadow may score for its owner
            from service_war import war_after_fight
            out["war"] = await war_after_fight(uid, doc, False)
        if not doc.get("dungeon") and not doc.get("trial"):
            from service_battlerank import apply as br_apply
            out["br"] = await br_apply(uid, "loss")  # a loss costs more the higher the rank
            from service_extras import chain_break
            lost, shielded = await chain_break(uid)
            if shielded:
                out["chain_shield"] = True
            elif lost >= 2:
                out["chain_lost"] = lost
        from service_worldstate import on_action
        _bg(on_action(uid, "pve_loss", doc["loc"]))
    _bg(col("battle_logs").insert_one({"user_id": uid, "mode": "pve", "win": win, "lvl": doc["lvl"], "at": now}))
    return out


def can_flee(doc: dict) -> bool:
    """Only normal battles can be fled (not dungeons, towers or evolution trials)."""
    return bool(doc) and not doc.get("dungeon") and not doc.get("trial")


async def pve_flee(uid: int, sid: str):
    """Run from a normal battle: no reward, the battle ends, Battle Rank drops a lot, but the win chain is kept."""
    doc = await col("battles").find_one({"sid": sid, "user_id": uid, "mode": "pve", "status": "active"})
    if not doc:
        return "gone", None
    if not can_flee(doc):
        return "noflee", None
    r = await col("battles").update_one({"sid": sid, "status": "active"}, {"$set": {"status": "fled"}})
    if not r.modified_count:
        return "gone", None
    from service_battlerank import apply as br_apply
    res = await br_apply(uid, "flee")
    _bg(col("battle_logs").insert_one({"user_id": uid, "mode": "pve", "win": False, "fled": True, "lvl": doc.get("lvl", 1),
                                        "at": int(time.time())}))
    return "ok", res


async def start_dungeon(uid: int, lang: str, dungeon_id: str, diff: str):
    ch = await get_char(uid)
    d = DUNGEONS[dungeon_id]
    if ch["level"] < d["level"]:
        return "level", None
    if await active_pve(uid):
        return "busy", None
    if diff != "normal":
        key = next((i for i, x in ALL.items() if x.get("effect") and x["effect"].get("type") == "key"
                    and x["effect"]["dungeon"] == dungeon_id and x["effect"]["diff"] == diff), None)
        if not key or not await inv_remove(uid, key, 1):
            return "key", None
    doc = await pve_start(uid, lang, dungeon={"id": dungeon_id, "stage": 1, "total": d["stages"], "diff": diff})
    return "ok", doc


# ---- PvP -----------------------------------------------------------------------------
def _pair(a: int, b: int) -> str:
    return f"{min(a, b)}:{max(a, b)}"


def _turn_secs() -> int:
    """Seconds one duel turn lasts: DUEL turn_seconds (5 minutes). The old live setting pvp_turn_seconds is no longer used here."""
    return int(DUEL["turn_seconds"])


async def duel_busy(uid: int) -> bool:
    return bool(await col("battles").find_one({"mode": "pvp", "status": {"$in": ["pending", "active"]}, "$or": [{"a_uid": uid}, {"b_uid": uid}]}))


async def duel_challenge(chat_id: int, a_uid: int, b_uid: int, ranked: bool):
    gs = await game_settings()
    if a_uid == b_uid:
        return "self", None
    ca, cb = await get_char(a_uid), await get_char(b_uid)
    if not ca:
        return "noreg", None
    if not cb:
        return "opp_noreg", None
    if ranked and (ca["level"] < int(gs["pvp_min_level"]) or cb["level"] < int(gs["pvp_min_level"])):
        return "minlevel", int(gs["pvp_min_level"])
    if await duel_busy(a_uid) or await duel_busy(b_uid):
        return "busy", None
    doc = {"sid": uuid.uuid4().hex[:8], "mode": "pvp", "a_uid": a_uid, "b_uid": b_uid, "ranked": ranked, "chat_id": chat_id,
           "status": "pending", "rev": 0, "created_at": int(time.time()), "expire_at": datetime.now(timezone.utc) + timedelta(minutes=5),
           "a_name": ca["name"], "b_name": cb["name"], "timeouts": {"a": 0, "b": 0}}
    await col("battles").insert_one(doc)
    return "ok", doc


async def duel_accept(sid: str, uid: int):
    gs = await game_settings()
    doc = await col("battles").find_one({"sid": sid, "mode": "pvp", "status": "pending", "b_uid": uid})
    if not doc:
        return None
    ca, cb = await get_char(doc["a_uid"]), await get_char(uid)
    fa, fb = await build_player(ca), await build_player(cb)
    rng = random.Random()
    state = E.new_state(fa, fb, rng, pvp=True)
    now = time.time()  # SENKA+ Konpaku charm: an active charm adds one life for this duel
    for f, c in ((fa, ca), (fb, cb)):
        if float(c.get("konpaku_until", 0) or 0) > now:
            f["lives"] = f.get("lives", 0) + 1
    E.run_ai(state, rng, ai_sides=())
    r = await col("battles").update_one({"sid": sid, "status": "pending"}, {"$set": {
        "status": "active", "state": state, "rev": 1, "deadline": int(time.time()) + _turn_secs(),
        "expire_at": _exp(), "started_at": int(time.time())}})
    return await col("battles").find_one({"sid": sid}) if r.modified_count else None


async def duel_decline(sid: str, uid: int):
    r = await col("battles").update_one({"sid": sid, "mode": "pvp", "status": "pending", "b_uid": uid}, {"$set": {"status": "declined"}})
    return bool(r.modified_count)


async def pvp_act(uid: int, sid: str, action: str, forced: str = None):
    gs = await game_settings()
    doc = await col("battles").find_one({"sid": sid, "mode": "pvp", "status": "active"})
    if not doc:
        return "gone", None, None
    st = doc["state"]
    side = "a" if uid == doc["a_uid"] else "b" if uid == doc["b_uid"] else forced
    if side is None:
        return "notplayer", None, None
    # a duel that already ended (its settle may still be pending) is over, not "not your turn":
    # after the last blow `awaiting` is cleared, so an old panel's button used to show the wrong message
    if st.get("done"):
        return "gone", None, None
    if st["cur"] != side or not st.get("awaiting"):
        return "notturn", None, None
    rng = random.Random()
    mt = max(E.MAX_TURNS, int(gs["pvp_max_turns"]))  # a stored old value (30) would cut the long fights short
    ev = E.do_action(st, action, rng, mt)
    ev += E.run_ai(st, rng, mt, ai_sides=())
    from service_fightfx import after_turn  # a narrator line now and then (duels have no challenge)
    ev += after_turn(st, action, ev, rng, side=side)
    from duel_ui import tally
    tally(st, ev)  # the battle report on the final card (damage, biggest hit, crits per side)
    upd = {"deadline": int(time.time()) + _turn_secs(), f"timeouts.{side}": 0 if forced is None else doc["timeouts"][side] + 1}
    if not await _save(doc, st, upd):
        return "stale", None, None
    doc["state"], doc["rev"] = st, doc["rev"] + 1
    outcome = await pvp_settle(doc) if st["done"] else None
    return "ok", doc, (ev, outcome)


async def pvp_forfeit(uid: int, sid: str):
    """A fighter yields: the other side wins, settled like any finished duel (rating, XP and caps apply).
    Returns (status, doc, outcome); status is ok / gone / notplayer / stale."""
    doc = await col("battles").find_one({"sid": sid, "mode": "pvp", "status": "active"})
    if not doc or doc["state"].get("done"):
        return "gone", None, None
    side = "a" if uid == doc["a_uid"] else "b" if uid == doc["b_uid"] else None
    if side is None:
        return "notplayer", None, None
    st = doc["state"]
    st[side]["hp"] = 0
    st["done"], st["winner"], st["end"], st["awaiting"] = True, "b" if side == "a" else "a", "ff", False
    st["last"] = []
    if not await _save(doc, st):
        return "stale", None, None
    doc["state"], doc["rev"] = st, doc["rev"] + 1
    return "ok", doc, await pvp_settle(doc)


async def pvp_timeouts():
    """Called by the scheduler: the first stalled turn is an automatic Guard, the second one in a row loses the duel."""
    now = int(time.time())
    out = []
    async for d in col("battles").find({"mode": "pvp", "status": "active", "deadline": {"$lte": now}}).limit(50):
        side = d["state"]["cur"]
        uid = d["a_uid"] if side == "a" else d["b_uid"]
        if d["timeouts"][side] + 1 >= int(DUEL["afk_limit"]):
            st = d["state"]
            st[side]["hp"] = 0
            st["done"], st["winner"], st["end"] = True, "b" if side == "a" else "a", "afk"
            st["awaiting"] = False
            if await _save(d, st):
                d["state"], d["rev"] = st, d["rev"] + 1
                out.append((d, [], await pvp_settle(d), True))
            continue
        res, doc, data = await pvp_act(uid, d["sid"], "df", forced=side)
        if res == "ok":
            out.append((doc, data[0], data[1], False))
    return out


async def pvp_settle(doc: dict):
    claimed = await col("battles").find_one_and_update({"sid": doc["sid"], "status": "active"}, {"$set": {"status": "done"}})
    if not claimed:
        return None
    gs = await game_settings()
    st = doc["state"]
    now = int(time.time())
    a_uid, b_uid = doc["a_uid"], doc["b_uid"]
    res = {"winner": None, "draw": st["winner"] == "draw", "rating": {}, "xp": {}, "note": None}
    if res["draw"]:
        return res
    w_uid, l_uid = (a_uid, b_uid) if st["winner"] == "a" else (b_uid, a_uid)
    cw, cl = await get_char(w_uid), await get_char(l_uid)
    res["winner"] = w_uid
    pair = _pair(a_uid, b_uid)
    note = None
    if not doc["ranked"]:  # Pack 1: duel XP is real now, so friendly duels share the same pair-per-day and fresh-account guards
        pair_any = await col("battle_logs").count_documents({"pair": pair, "win": True, "at": {"$gte": now - 86400}})
        if pair_any >= int(gs["pvp_pair_daily_cap"]):
            note = "pair_cap"
        elif now - cw["created_at"] < 3600 or now - cl["created_at"] < 3600:
            note = "new_account"
    if doc["ranked"]:
        pair_n = await col("battle_logs").count_documents({"pair": pair, "rated": True, "win": True, "at": {"$gte": now - 86400}})  # one log per duel (each duel stores two)
        if pair_n >= int(gs["pvp_pair_daily_cap"]):
            note = "pair_cap"
        elif cw["level"] - cl["level"] > RATED_LEVEL_GAP:  # only a much STRONGER-level winner is unrated (anti-farming); a lower level beating a higher one always counts
            note = "level_gap"
        elif now - cw["created_at"] < 3600 or now - cl["created_at"] < 3600:
            note = "new_account"
    rated = doc["ranked"] and not note
    if rated:
        diff = (cl["rating"] - cw["rating"]) / 800
        gain = int(random.randint(int(gs["pvp_gain_min"]), int(gs["pvp_gain_max"])) * max(0.6, min(1.5, 1 + diff)))
        loss = int(random.randint(int(gs["pvp_loss_min"]), int(gs["pvp_loss_max"])) * max(0.6, min(1.5, 1 - diff)))
        new_l = max(0, cl["rating"] - loss)
        await col("characters").update_one({"user_id": w_uid}, {"$inc": {"rating": gain, "pvp_w": 1}})
        await col("characters").update_one({"user_id": l_uid}, {"$set": {"rating": new_l}, "$inc": {"pvp_l": 1}})
        res["rating"] = {w_uid: (cw["rating"] + gain, gain), l_uid: (new_l, -(cl["rating"] - new_l))}
        # Battle Rank from ranked duels (skill, not level): only the first few duels of the same pair each day count
        from data_battlerank import DUEL_PAIR_DAILY
        from data_world import day_id
        from database import bump_counter
        if await bump_counter(f"brpair:{pair}:{day_id()}", 1, DUEL_PAIR_DAILY):
            from service_battlerank import apply as br_apply, current as br_current
            rw, rl = br_current(cw)[0], br_current(cl)[0]
            bw = await br_apply(w_uid, "duel_win", opp_rp=rl)
            if bw and bw.get("delta", 0) > 0:
                bl = await br_apply(l_uid, "duel_loss", opp_rp=rw)
            else:  # the winner's daily duel cap was already full: nobody earned anything, so the loser must not bleed rank for it
                bl = None
                res["br_note"] = "cap"
            res["br"] = {w_uid: bw, l_uid: bl}
        else:  # this pair already used its rank duels today: say so instead of staying silent
            res["br_note"] = "pair"
    log_event("pvp", w_uid, f"دوئل {'رنکد' if doc['ranked'] else 'دوستانه'}: برد مقابل {cl['name']} ({l_uid})" + (f" | رتبه {res['rating'][w_uid][1]:+d}" if rated else (f" | بدون امتیاز ({note})" if note else "")),
              loser=l_uid, ranked=bool(doc["ranked"]))
    wins_today = await col("battle_logs").count_documents({"user_id": w_uid, "mode": "pvp", "win": True, "at": {"$gte": now - 86400}})
    frac = 1.0 if wins_today < int(gs["pvp_full_xp_wins"]) else 0.3
    if note != "pair_cap":
        xp = duel_xp(cw["level"], gs, frac)
        _, _, got = await add_xp(w_uid, xp, "pvp")
        await add_coins(w_uid, int((60 + cw["level"] * 4) * float(gs["coin_rate"]) * frac), "pvp")
        res["xp"][w_uid] = got
        await bump_quest(w_uid, "pvp_win", 1)
        if note != "new_account":  # Pack 1: a fought-out loss still teaches something
            lose_xp = int(duel_xp(cl["level"], gs, frac) * float(gs.get("pvp_loser_xp", 0.0)))
            if lose_xp > 0:
                _, _, lgot = await add_xp(l_uid, lose_xp, "pvp")
                res["xp"][l_uid] = lgot
    res["note"] = note
    from service_interact import claim_bounty
    from service_worldstate import on_action_bg
    if note not in ("pair_cap", "new_account"):  # farming the same friend must not feed events, territory or season
        on_action_bg(w_uid, "pvp_win", cw["location"])
    if doc["ranked"] and note not in ("pair_cap", "new_account", "level_gap"):
        res["bounty"] = await claim_bounty(w_uid, l_uid)
    base = {"mode": "pvp", "pair": pair, "rated": rated, "at": now}
    await col("battle_logs").insert_many([{**base, "user_id": w_uid, "opp": l_uid, "win": True},
                                          {**base, "user_id": l_uid, "opp": w_uid, "win": False}])
    return res
