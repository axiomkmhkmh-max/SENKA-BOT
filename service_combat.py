"""PvE, dungeons and PvP built on the pure engine. All outcomes are server-side."""
import asyncio
import logging
import random
import time
import uuid
from datetime import datetime, timedelta, timezone

from data_crafting import player_bonus, tagged_name, temper_def
from data_items import ALL
from data_races import DIFFICULTY, DUNGEON_ENEMIES, DUNGEONS, LOCATIONS, RACES, soft_stat
from data_weapons import ELEMENTS
from data_zanpakuto import BLADE_STAGES, BLADE_STYLE
import engine as E
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
        if "stat2" in it["stats"]:  # the new accessories can carry a second stat
            stats[it["stats"]["stat2"]] += it["stats"]["bonus2"]
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
    from data_raceweapons import weapon_focus  # the weapon's own lean grows with its colour and forge level
    _wid = ch.get("weapon_id") or ""
    foc = weapon_focus(ALL.get(_wid), (ch.get("weapon_plus") or {}).get(_wid, 0))
    if foc:
        key, pct = foc[0], foc[1]
        if key in ("dmg", "def", "kido"):
            mods[key] = mods.get(key, 1.0) * (1 + pct)
        else:  # crit / pierce: half of it as a flat chance
            mods[key] = mods.get(key, 0.0) + pct / 2
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
    # Release stages feed the existing weapon-skill multiplier; no parallel combat engine.
    stage = BLADE_STAGES.get(zstate.get("blade_id"), {})
    release_bonus = (0.10 + stage.get("shikai_bonus", 0.0)) if zstate.get("shikai") else 0.0
    if zstate.get("bankai"):
        release_bonus += 0.12 + min(0.08, int(zstate.get("mastery", 0)) / 500) + stage.get("bankai_bonus", 0.0)
    zmult = 1 + min(1.0, bond / 500) + release_bonus  # bond adds up to +100% (500 bond); no 30 ceiling
    # Distinct release identities alter battle style rather than granting identical flat power.
    blade_style = BLADE_STYLE.get(zstate.get("blade_id"), {})
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
    for spell_id in set(ch.get("kido_learned") or []):
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
    fighter["evs"] = evo_stage(ch)  # evolution stage: opens the canon race techniques (data_race_tech)
    fighter["tm"] = {k: int(v) for k, v in (ch.get("tech_lvl") or {}).items()}  # technique mastery (race technique cards)
    return fighter


def make_enemy(level: int, scale: float, name: str, rng=random, sig=None):
    k = ENEMY_K
    s = (4 + level * k["s"]) * scale
    stats = {"zanjutsu": s, "kido": s * 0.6, "hakuda": (4 + level * k["d"]) * scale, "hoho": 6 + level * 0.5, "reiatsu": 5 + level}
    w = {"attack": (3 + level * k["a"]) * scale, "crit": 0.03, "element": rng.choice(ELEMENTS), "skills": [], "weapon_type": "melee"}
    foe = E.new_fighter(name, level, stats, (k["h0"] + level * k["h1"]) * scale, 80 + level * 10, w,
                        armor=level * k["ar"] * scale, ai=True, sig=sig)
    foe["wild"] = True  # wild enemies never release (every player race can, since the release rework)
    return foe


def _rewards(level: int, scale: float, st: dict):
    xp = (20 * level ** 1.25 + 20) * (scale if scale > 1 else 1.0)
    # coins grow faster than the level (more than linear), so higher levels earn clearly more per fight:
    # Lv1 ≈ 20, Lv10 ≈ 97, Lv30 ≈ 297, Lv50 ≈ 537, Lv80 ≈ 972, Lv100 ≈ 1312 (was 16 / 70 / 190 / 310 / 490 / 610)
    coins = (12 + 8 * level + 0.05 * level ** 2) * (scale if scale > 1 else 1.0) * float(st["coin_rate"])
    return int(xp), int(coins)


# ---- PvE ---------------------------------------------------------------------------
async def active_pve(uid: int):
    return await col("battles").find_one({"user_id": uid, "mode": "pve", "status": "active"})


DG_XP_MULT = 2.0        # dungeon stages pay this much more XP than a normal fight (they pay no coins or items)
DG_STAGE_HEAL = 0.25    # every new dungeon floor restores this share of max HP and max reiatsu (capped at full)
DG_BOSS_HEAL = 0.40     # ... and this much before the last floor (the boss), so the boss is not met on empty
# Full-clear coins of the two hardest difficulties (the others pay XP and DP only), x (1 + dungeon level / 20)
DG_CLEAR_COINS = {"abyss": 2500, "legendary": 8000}


def _is_boss_stage(dungeon, tower_floor_flag) -> bool:
    """True for a dungeon's last stage and for a Soul Tower Warden floor (fight-type balance, see data_race_rules)."""
    if not dungeon:
        return False
    if dungeon.get("tower") or tower_floor_flag:
        from data_extras import TOWER_BOSS_EVERY
        return int(dungeon.get("stage", 0)) % TOWER_BOSS_EVERY == 0
    return dungeon.get("stage") == dungeon.get("total")


async def pve_start(uid: int, lang: str, scale: float = 1.0, dungeon: dict = None, carry: dict = None, trial: dict = None,
                    force_elite: bool = False):
    ch = await get_char(uid)
    gs = await game_settings()
    wm = await mods_for(ch["location"])
    rng = random.Random()
    loc = LOCATIONS[ch["location"]]
    pick = rng.choice(loc["enemies"])
    sig_race = loc.get("race")
    name = pick[0 if lang == "fa" else 1]
    lvl = max(1, ch["level"] + rng.randint(-1, 1))
    tower = bool(dungeon and dungeon.get("tower"))
    fixed_dg = bool(dungeon and not tower and dungeon.get("id") in DUNGEONS)
    if fixed_dg:  # a dungeon's enemies keep the dungeon's own level, whatever level the player is
        lvl = int(DUNGEONS[dungeon["id"]]["level"])
        dg_foes = DUNGEON_ENEMIES.get(dungeon["id"])
        if dg_foes:  # the dungeon's own enemies (and its named boss on the last stage), not the player's location
            pick = dg_foes["boss"] if dungeon["stage"] == dungeon["total"] else rng.choice(dg_foes["enemies"])
            sig_race = dg_foes.get("race")
            name = pick[0 if lang == "fa" else 1]
    if tower:  # Soul Tower: endless floors, a Warden every 5th
        from data_extras import TOWER_BOSS_EVERY, TOWER_ENEMIES
        floor = int(dungeon["stage"])
        scale = 0.85 * (1.045 ** (floor - 1))
        name = rng.choice(TOWER_ENEMIES)[0 if lang == "fa" else 1]
        if floor % TOWER_BOSS_EVERY == 0:
            scale *= 1.5
            name = "👑 " + name
    elif dungeon and dungeon.get("adv"):  # adventure: themed foes of a random level around the player's
        from data_extras2 import ADVENTURES
        a = ADVENTURES[dungeon["id"]]
        stage, total = dungeon["stage"], dungeon["total"]
        lvl = max(1, ch["level"] + rng.randint(-3, 4))
        pick = a["boss"] if stage == total else rng.choice(a["foes"])
        name = pick[0 if lang == "fa" else 1]
        scale = 0.9 + 0.08 * (stage - 1)
        if stage == total:
            scale *= 1.35
            name = "👑 " + name
    elif dungeon and dungeon.get("war"):  # event battlefield: the enemy faction's soldier, officer or general (shadows below)
        from service_war import war_foe
        lvl, name, scale, sig_race, pick = war_foe(dungeon, int(ch["level"]), lang, rng)
    elif dungeon and dungeon.get("lboss"):  # level boss of the player's band
        from data_extras2 import LEVEL_BOSS_SCALE, LEVEL_BOSSES
        b = LEVEL_BOSSES[int(dungeon["band"])]
        lvl = max(1, min(ch["level"], b[1]) + 2)
        pick = (b[2], b[3])
        name = "👹 " + pick[0 if lang == "fa" else 1]
        sig_race = b[5]
        scale = LEVEL_BOSS_SCALE
    elif dungeon:
        stage, total = dungeon["stage"], dungeon["total"]
        mult = DIFFICULTY[dungeon["diff"]] * (1 + 0.12 * (stage - 1))
        if stage == total:
            mult *= 1.6
            name = "👑 " + name
        elif stage == max(2, total // 2):
            mult *= 1.3
            name = "⚔️ " + name
        scale = mult
    elite = bool(force_elite) or ((not dungeon) and (not trial) and rng.random() < 0.15)
    mini = False
    if elite:
        scale, name = (1.55 if force_elite else 1.4), "💀 " + name
    elif not dungeon and not trial:  # mini-boss: a rare, much stronger foe in a normal battle, with a big reward
        from data_extras2 import MINI_BOSS_CHANCE, MINI_BOSS_NAMES, MINI_BOSS_SCALE
        if rng.random() < MINI_BOSS_CHANCE:
            mini = True
            scale = MINI_BOSS_SCALE
            name = "👺 " + rng.choice(MINI_BOSS_NAMES)[0 if lang == "fa" else 1]
    if trial:
        scale, name = float(gs["evo_trial_scale"]) * (1 + 0.2 * (trial["stage"] - 1)), "🌀 " + name
    elif not tower and not fixed_dg and not (dungeon and dungeon.get("war")):  # dungeons and the battlefield: no world-event scaling
        scale *= wm["enemy"]  # Hollow Threat + active world event strengthen every enemy
    player = await build_player(ch)
    player["x"]["bstack"] = int((ch.get("bount") or {}).get("stacks", 0))  # soul stacks: PvE only, settled in pve_settle
    if float(ch.get("almighty_until", 0) or 0) > time.time():  # Yhwach's Eye: one fatal blow is survived
        player["almighty"] = True
        player["lives"] = 1
    if carry:
        player["hp"] = max(1, int(player["max_hp"] * carry["hp"]))
        player["re"] = max(0, int(player["max_re"] * carry["re"]))
        if "gauge" in carry:  # the spirit gauge is the same fighter's courage: it does not reset between stages
            player["x"]["gauge"] = max(0, int(carry["gauge"]))
        if carry.get("shield", 0) > 0:  # the barrier was dropped between stages, so the enemy's opening hit landed on bare HP
            player["shield"] = int(carry["shield"])
    from data_bleachfx import enemy_sig
    sig = enemy_sig(sig_race, pick)
    foe = make_enemy(lvl, scale, name, rng, sig=sig)
    if sig == "cero":  # hollow foe: tells the human passive who it is
        foe["foe"] = "hollow"
    elif _is_boss_stage(dungeon, tower):  # dungeon final stage or Soul Tower Warden: race balance by fight type
        foe["foe"] = "boss"
    else:  # every other wild enemy
        foe["foe"] = "pve"
    shadow = False
    if dungeon and dungeon.get("war"):
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
    if action == "pot" and potion:
        ev = E.do_potion(st, potion["type"], potion["pct"])
    else:
        ev = E.do_action(st, action, rng)
    ev += E.run_ai(st, rng)
    if not await _save(doc, st):
        return "stale", None, None
    doc["state"], doc["rev"] = st, doc["rev"] + 1
    outcome = await pve_settle(doc) if st["done"] else None
    return "ok", doc, (ev, outcome)


async def pve_settle(doc: dict):
    won = await col("battles").find_one_and_update({"sid": doc["sid"], "status": "active"}, {"$set": {"status": "done"}})
    if not won:
        return None
    uid, st = doc["user_id"], doc["state"]
    gs = await game_settings()
    win = st["winner"] == "a"
    out = {"win": win, "xp": 0, "coins": 0, "drop": None, "levels": 0, "next": None, "dungeon_done": False}
    now = int(time.time())
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
        if plain:  # win chain: consecutive plain victories raise coin/XP rewards
            cn, cm, cdrop, cfull, cms = chain_res
            xp, coins = int(xp * cm), int(coins * cm)
            out["chain"] = {"n": cn, "pct": round((cm - 1) * 100), "item": cdrop, "ms": cms}
            if cfull:
                out["drop_full"] = out.get("drop_full") or cfull
        if doc.get("mini"):  # mini-boss: triple XP and coins, a guaranteed blue-or-better item, a chance of a relic
            from data_extras2 import MINI_BOSS_RELIC, MINI_BOSS_REWARD
            xp, coins = int(xp * MINI_BOSS_REWARD), int(coins * MINI_BOSS_REWARD)
            mi = await roll_drop(uid, source_mult=2.0, floor_idx=2)
            await inv_add(uid, mi, 1, force=True)
            out["mini"] = {"item": mi, "relic": None}
            if random.random() < MINI_BOSS_RELIC:
                from data_items import EVO_BY_RARITY
                rel = random.choice(EVO_BY_RARITY["Rare"] or EVO_BY_RARITY["Common"])
                await inv_add(uid, rel, 1, force=True)
                out["mini"]["relic"] = rel
        if d and d.get("adv"):  # adventures pay coins (more than a normal fight) and a bit more XP
            from data_extras2 import ADV_COIN_K, ADV_XP_K
            xp, coins = int(xp * ADV_XP_K), int(coins * ADV_COIN_K)
        elif d and d.get("war"):  # battlefield: a normal fight's pay, more for officers, shadows and the general
            from service_war import fight_k
            kx, kc = fight_k(d)
            xp, coins = int(xp * kx), int(coins * kc)
        elif d and d.get("lboss"):  # level boss: x4 XP and coins (its loot is paid at the end)
            from data_extras2 import LEVEL_BOSS_REWARD
            xp, coins = int(xp * LEVEL_BOSS_REWARD), int(coins * LEVEL_BOSS_REWARD)
        elif d:  # dungeons pay no coins (and no items): XP and dungeon points instead, so the XP is doubled on every stage
            xp, coins = int(xp * DG_XP_MULT), 0
            if d["stage"] == d["total"]:
                xp *= 3
        coins = int(coins * wm["coin"])
        coins = int(coins * (1 + player_bonus(ch0, ALL, gs)["coin"]))
        ch, lv, got = await add_xp(uid, xp, "pve", ch=ch0)
        # independent writes: run together instead of one after another
        await asyncio.gather(add_coins(uid, coins, "pve") if coins > 0 else asyncio.sleep(0),
                             col("characters").update_one({"user_id": uid}, {"$inc": {"wins": 1, f"bond.{__import__('data_zanpakuto').bond_key(ch or {})}": 1, **({"zanpakuto.mastery": 1} if (ch0.get("zanpakuto") or {}).get("shikai") and int((ch0.get("zanpakuto") or {}).get("mastery", 0)) < int(gs.get("znp_mastery_cap", 1000)) else {}), **({"race_progress.hunts": 1} if (ch or {}).get("race") in ("hollow", "arrancar") else {})}}),
                             bump_quest(uid, "battle_win", 1))
        out.update(xp=got, coins=coins, levels=lv)
        if (ch0 or {}).get("mentor"):  # an apprentice: the master earns a small EXTRA cut of this win's XP (service_mentor)
            try:
                from service_mentor import share_xp
                out["mentor"] = await share_xp(uid, int(ch0["mentor"]), got, ch)
            except Exception:
                logging.getLogger("senka.mentor").exception("mentor xp share failed")  # must never break the fight's settlement
        from service_gangs_hook import gang_rewards  # Xcution siphon and Bount absorption (rules in data_gangs.py)
        out["gang"] = await gang_rewards(uid, doc) if not d else {}  # dungeons pay no coins (Bount absorption included)
        from service_worldstate import on_action, territory_income
        out["terr"] = await territory_income(uid, doc["loc"], coins, xp)
        chance = 1.0 if doc["elite"] else 0.35
        if not d and random.random() < chance:  # dungeons drop no items any more: XP, coins and dungeon points (DP) instead
            iid = await roll_drop(uid, source_mult=2.0 if doc["elite"] else 1.0)
            if await inv_add(uid, iid, 1):
                out["drop"] = iid
            else:
                out["drop_full"] = iid  # bag full: shown to the player (it used to vanish silently)
        if d and d["stage"] < d["total"]:
            f = st["a"]
            # a breather between floors: HP and reiatsu come back a little (more before the boss floor), so the
            # reiatsu is not gone by the time the boss arrives
            heal = DG_BOSS_HEAL if d["stage"] + 1 == d["total"] else DG_STAGE_HEAL
            hp_frac = min(1.0, f["hp"] / f["max_hp"] + heal)
            re_frac = min(1.0, f["re"] / max(1, f["max_re"]) + heal)
            out["dg_heal"] = {"pct": int(heal * 100), "boss": d["stage"] + 1 == d["total"]}
            nxt = await pve_start(uid, doc.get("lang", "en"), dungeon={**d, "stage": d["stage"] + 1},
                                  carry={"hp": hp_frac, "re": re_frac,
                                         "gauge": int((f.get("x") or {}).get("gauge", 0)),
                                         "shield": int(f.get("shield", 0))})  # a Bakudō barrier survives the stage change  # spirit carries over; HP and reiatsu are kept as fractions
            out["next"] = nxt["sid"]
        elif d and d.get("adv"):  # adventure finished: a purse of coins
            from data_extras2 import ADV_FINISH_COINS
            out["adv_done"] = int(ADV_FINISH_COINS * (1 + int(doc["lvl"]) / 10))
            await add_coins(uid, out["adv_done"], "adventure")
        elif d and d.get("lboss"):  # level boss down: its loot
            from service_adventure import level_boss_loot
            out["lboss"] = await level_boss_loot(uid, int(d["band"]))
        elif d and d.get("war"):  # battlefield: war points for the player's side
            from service_war import war_after_fight
            out["war"] = await war_after_fight(uid, doc, True)
        elif d:
            out["dungeon_done"] = True
            await bump_quest(uid, "dungeon_clear", 1)
            from service_dungeonshop import award_dp
            out["dp"] = await award_dp(uid, d)
            from service_dungeonshop import roll_special
            out["special"] = await roll_special(uid, d)  # dungeon-only item, small chance
            if d.get("diff") in DG_CLEAR_COINS:  # the hardest dungeons pay coins on a full clear (players asked for it)
                from data_races import DUNGEONS
                dlv = int((DUNGEONS.get(d.get("id")) or {}).get("level", 1))
                out["dg_coins"] = int(DG_CLEAR_COINS[d["diff"]] * (1 + dlv / 20))
                await add_coins(uid, out["dg_coins"], "dungeon_clear")
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


async def save_tower(uid: int) -> int:
    """Register the climb: remember the floor the player is standing on, so the next climb starts exactly there instead
    of at the start of its 5-floor block. Returns that floor (0 when no tower fight is open)."""
    doc = await col("battles").find_one({"user_id": uid, "mode": "pve", "status": "active", "dungeon.tower": True})
    if not doc:
        return 0
    floor = int(doc["dungeon"]["stage"])
    await col("characters").update_one({"user_id": uid}, {"$set": {"tower.saved": floor}})
    return floor


async def abandon_tower(uid: int) -> bool:
    """Leave the Soul Tower: the open tower fight (the current or the already-waiting next floor) is closed with no
    penalty and no reward. Before this existed, the tower fight stayed active forever and blocked every dungeon,
    battle and new climb until the player lost it on purpose. Returns True when a tower fight was closed."""
    r = await col("battles").update_many({"user_id": uid, "mode": "pve", "status": "active", "dungeon.tower": True},
                                         {"$set": {"status": "fled"}})
    return bool(r.modified_count)


async def blocking_pve(uid: int):
    """The active fight that really blocks other activities. An open Soul Tower fight does not: it is closed for free
    (the tower can be re-entered), so a player is never locked out of dungeons, adventures, exploring or war by it."""
    await abandon_tower(uid)
    return await active_pve(uid)


async def start_dungeon(uid: int, lang: str, dungeon_id: str, diff: str):
    ch = await get_char(uid)
    d = DUNGEONS[dungeon_id]
    if ch["level"] < d["level"]:
        return "level", None
    await abandon_tower(uid)  # an open tower fight must never lock the player out of a dungeon
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


async def _tour_training() -> bool:
    from service_tournament import training_open
    return await training_open()


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
           "a_name": ca["name"], "b_name": cb["name"], "timeouts": {"a": 0, "b": 0}, "tournament": bool(ranked and await _tour_training())}
    await col("battles").insert_one(doc)
    return "ok", doc


async def duel_accept(sid: str, uid: int):
    gs = await game_settings()
    doc = await col("battles").find_one({"sid": sid, "mode": "pvp", "status": "pending", "b_uid": uid})
    if not doc:
        return None
    ca, cb = await get_char(doc["a_uid"]), await get_char(uid)
    equal = bool(doc.get("tournament")) and int(gs.get("tour_equal_training", 1))
    if equal:  # Gotei Trial training: both fight with the standard kit (no race, no gear), exactly like the bracket
        from engine_tournament import standard_fighter
        lvl = int(gs.get("tour_level", 30))
        fa, fb = standard_fighter(ca["name"], lvl), standard_fighter(cb["name"], lvl)
    else:
        fa, fb = await build_player(ca), await build_player(cb)
    rng = random.Random()
    state = E.new_state(fa, fb, rng, pvp=True)
    now = time.time()  # SENKA+ Konpaku charm: an active charm adds one life for this duel
    for f, c in ((fa, ca), (fb, cb)):
        if not equal and float(c.get("konpaku_until", 0) or 0) > now:
            f["lives"] = f.get("lives", 0) + 1
    E.run_ai(state, rng, ai_sides=())
    r = await col("battles").update_one({"sid": sid, "status": "pending"}, {"$set": {
        "status": "active", "state": state, "rev": 1, "deadline": int(time.time()) + int(gs["pvp_turn_seconds"]),
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
    ev = E.do_action(st, action, rng, int(gs["pvp_max_turns"]))
    ev += E.run_ai(st, rng, int(gs["pvp_max_turns"]), ai_sides=())
    upd = {"deadline": int(time.time()) + int(gs["pvp_turn_seconds"]), f"timeouts.{side}": 0 if forced is None else doc["timeouts"][side] + 1}
    if not await _save(doc, st, upd):
        return "stale", None, None
    doc["state"], doc["rev"] = st, doc["rev"] + 1
    outcome = await pvp_settle(doc) if st["done"] else None
    return "ok", doc, (ev, outcome)


async def pvp_timeouts():
    """Called by the scheduler: auto-guard stalled turns, forfeit after 3 in a row."""
    now = int(time.time())
    out = []
    async for d in col("battles").find({"mode": "pvp", "status": "active", "deadline": {"$lte": now}}).limit(50):
        side = d["state"]["cur"]
        uid = d["a_uid"] if side == "a" else d["b_uid"]
        if d["timeouts"][side] + 1 >= 3:
            st = d["state"]
            st[side]["hp"] = 0
            st["done"], st["winner"] = True, "b" if side == "a" else "a"
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
    if doc["ranked"]:
        pair_n = await col("battle_logs").count_documents({"pair": pair, "rated": True, "win": True, "at": {"$gte": now - 86400}})  # one log per duel (each duel stores two)
        if pair_n >= int(gs["pvp_pair_daily_cap"]):
            note = "pair_cap"
        elif abs(cw["level"] - cl["level"]) > 10:
            note = "level_gap"
        elif now - cw["created_at"] < 3600 or now - cl["created_at"] < 3600:
            note = "new_account"
    in_tour = bool(doc.get("tournament"))
    if in_tour and note != "new_account":  # Gotei Trial training: only tournament points, the main ladder is untouched
        from service_tournament import record_training
        await record_training(w_uid, l_uid, cw["name"], cl["name"], doc.get("created_at"))
    rated = doc["ranked"] and not note and not in_tour
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
            bw, bl = await asyncio.gather(br_apply(w_uid, "duel_win", opp_rp=rl), br_apply(l_uid, "duel_loss", opp_rp=rw))
            res["br"] = {w_uid: bw, l_uid: bl}
    log_event("pvp", w_uid, f"دوئل {'رنکد' if doc['ranked'] else 'دوستانه'}: برد مقابل {cl['name']} ({l_uid})" + (f" | رتبه {res['rating'][w_uid][1]:+d}" if rated else (f" | بدون امتیاز ({note})" if note else "")),
              loser=l_uid, ranked=bool(doc["ranked"]))
    wins_today = await col("battle_logs").count_documents({"user_id": w_uid, "mode": "pvp", "win": True, "at": {"$gte": now - 86400}})
    frac = 1.0 if wins_today < int(gs["pvp_full_xp_wins"]) else 0.3
    if note != "pair_cap":
        xp = int((30 + cw["level"] * 8) * frac)
        _, _, got = await add_xp(w_uid, xp, "pvp")
        await add_coins(w_uid, int((60 + cw["level"] * 4) * float(gs["coin_rate"]) * frac), "pvp")
        res["xp"][w_uid] = got
        await bump_quest(w_uid, "pvp_win", 1)
    res["note"] = note or ("tour" if in_tour else None)
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
