"""Home, profile, stat upgrades, world map, exploration, quests, ranking, daily,
mini-games, guilds, settings and help."""
import random
import time

from pymongo import ReturnDocument

from data_crafting import cosmetic_tag, player_bonus
from data_items import ALL
from data_races import LOCATIONS, RACES, STAT_ICON, STATS, soft_stat
from database import col, game_settings, try_cooldown
from render import pick
from fmt import effect_text, nm, race_name, rarity_name, stats_block, title_of
from handlers_world import bonus_line, world_line
from service_interact import crowd_counts, find_trace
from service_worldcore import mods_for
from service_worldstate import on_action_bg, territory_income, territory_owners
from i18n import bar, esc, fnum
from security import clean_name
from data_lore import streak_line
from data_misc import LOC_DESC
from service_combat import active_pve, rank_label, rank_letter
from service_economy import inv_add, roll_drop
from service_player import (add_coins, add_xp, claim_daily, claim_quest, energy_now, get_char, max_hp, max_reiatsu,
                            power, quest_list, set_lang, spend_energy, xp_to_next)
from service_social import (guild_create, guild_deposit, guild_join, guild_leave, guild_list, mg_answer, mg_new)
from ui import Out, action, chunk, head, input_handler, nav, pager


async def need_char(ctx):
    ch = await get_char(ctx.uid)
    return ch


def loc_name(loc_id: str, lang: str) -> str:
    return LOCATIONS[loc_id]["fa" if lang == "fa" else "en"]


@action("home")
async def home(ctx, arg):
    ch = await need_char(ctx)
    if not ch:
        return Out(ctx.t("not_registered"))
    st = await game_settings()
    L = ctx.lang
    en, nxt, _ = energy_now(ch, st)
    hp = max_hp(ch["level"], soft_stat(ch["stats"]["hakuda"]), RACES[ch["race"]]["mods"].get("hp", 1.0))
    re = max_reiatsu(ch["level"], soft_stat(ch["stats"]["reiatsu"]))
    need = xp_to_next(ch["level"])
    text = (head(ctx, "ttl_home") +
            ctx.t("home_body", name=esc(ch["name"]), race=race_name(ch["race"], L), title=title_of(ch, L), lvl=fnum(ch["level"], L),
                  xpbar=bar(ch["xp"], need), xp=fnum(ch["xp"], L), need=fnum(need, L), power=fnum(power(ch), L), hp=fnum(hp, L),
                  re=fnum(re, L), loc=loc_name(ch["location"], L), en=fnum(en, L), enmax=fnum(st["energy_max"], L),
                  coins=fnum(ch["coins"], L), pts=fnum(ch.get("points", 0), L)))
    if ch["level"] < 6 and ch.get("wins", 0) < 10:  # newcomers: one line that says what to do next
        text += "\n\n" + ctx.t("home_tip")
    else:
        text += "\n\n" + await world_line(ctx, ch)
    banner = "🌑 ━━━━━━━━━━━━━━━━━━ 🌑\n"
    text = banner + text + "\n🌑 ━━━━━━━━━━━━━━━━━━ 🌑"
    # home: the things people use every minute, in a 2-column grid; everything else lives in "More", grouped
    rows = [[(ctx.t("m_exp"), "exp", ""), (ctx.t("m_bt"), "bt", "")],
            [(ctx.t("m_dgn"), "dgn", ""), (ctx.t("m_gch"), "gch", "")],
            [(ctx.t("m_prof"), "prof", ""), (ctx.t("m_bag"), "bag", "0")],
            [(ctx.t("m_qst"), "qst", ""), (ctx.t("m_mkt"), "mkt", "")],
            [(ctx.t("m_dly"), "dly", ""), (ctx.t("m_rnk"), "rnk", "")],
            [(ctx.t("m_map"), "map", ""), (ctx.t("m_crf"), "crf", "")],
            [(ctx.t("b_more"), "menu2", "")]]
    return Out(text, rows)


@action("menu2")
async def menu2(ctx, arg):
    rows = [[(ctx.t("mg_adv"), "mg", "adv"), (ctx.t("mg_grow"), "mg", "grow")],
            [(ctx.t("mg_soc"), "mg", "soc"), (ctx.t("mg_fun"), "mg", "fun")],
            [(("✨ امکانات" if ctx.lang == "fa" else "✨ Extras"), "xf", "")],
            [(ctx.t("m_set"), "set", ""), (ctx.t("m_hlp"), "hlp", "")], nav(ctx)]
    return Out(head(ctx, "ttl_menu") + ctx.t("menu_body"), rows)


# "More" is split into four small groups of at most 4 buttons, so no screen ever shows a wall of options.
MENU_GROUPS = {
    "adv": [[("m_dgn", "dgn"), ("m_twr", "twr")], [("m_avl", "avl"), ("m_lbs", "lbs")], [("m_map", "map"), ("m_wrd", "wrd")]],
    "grow": [[("m_gch", "gch"), ("m_crf", "crf")], [("m_dsp", "dsp"), ("m_art", "art")], [("m_inr", "inr"), ("m_in2", "in2")],
             [("m_sat", "sat"), ("m_rsh", "rsh")], [("m_els", "els"), ("m_div", "div")], [("m_hlf", "hlf")]],
    "soc": [[("m_rnk", "rnk"), ("m_gld", "gld")]],
    "fun": [[("m_dly", "dly"), ("m_whl", "whl")], [("m_mgm", "mgm")]],
}


@action("mg")
async def menu_group(ctx, arg):
    if arg not in MENU_GROUPS:
        return await menu2(ctx, "")
    rows = [[(ctx.t(key), code, "") for key, code in row] for row in MENU_GROUPS[arg]]
    rows.append(nav(ctx, ("menu2", "")))
    return Out(head(ctx, "ttl_menu") + ctx.t("mg_" + arg + "_body"), rows)


# ---- profile & upgrades -------------------------------------------------------------
@action("prof")
async def profile(ctx, arg):
    ch = await need_char(ctx)
    L = ctx.lang
    hp = max_hp(ch["level"], soft_stat(ch["stats"]["hakuda"]), RACES[ch["race"]]["mods"].get("hp", 1.0))
    re_max = max_reiatsu(ch["level"], soft_stat(ch["stats"]["reiatsu"]))
    need = xp_to_next(ch["level"])
    vitals = f"<code>{bar(ch['xp'], need)}</code> ⭐ {fnum(ch['xp'], L)}/{fnum(need, L)}   ❤️ {fnum(hp, L)}   🔵 {fnum(re_max, L)}"
    lines = [head(ctx, "ttl_prof"), vitals,
             ctx.t("prof_body", name=esc(ch["name"]), race=race_name(ch["race"], L), title=title_of(ch, L), lvl=fnum(ch["level"], L),
                   rank=rank_label(ch["rating"], L), rating=fnum(ch["rating"], L), bond=fnum(min(100, __import__("data_zanpakuto").bond_value(ch) // 5), L), plus=fnum((ch.get("weapon_plus") or {}).get(ch.get("weapon_id"), 0), L), w=fnum(ch["wins"], L), l=fnum(ch["losses"], L),
                   pw=fnum(ch["pvp_w"], L), pl=fnum(ch["pvp_l"], L), power=fnum(power(ch), L)),
             stats_block(ctx, ch["stats"]),
             "🧿 " + bonus_line(ctx, player_bonus(ch, ALL, await game_settings())),
             f"⚔️ {nm(ch['weapon_id'], L)}\n🛡️ {nm(ch.get('armor_id'), L)}\n💍 {nm(ch.get('acc_id'), L)}\n📿 {nm(ch.get('charm_id'), L)}"]
    from handlers_battlerank import rank_title
    lines.insert(3, ctx.t("prof_rank_line", t=await rank_title(ch, L)))  # the battle-rank title, beside the race title
    if ch.get("artifact"):
        from data_artifacts import art_name
        lines.append("🔱 " + art_name(ch["artifact"], L))
    if ch.get("kenpachi_art"):
        from data_battlerank import KENPACHI_ART
        lines.append("👁 " + KENPACHI_ART["name"][0 if L == "fa" else 1])
    if ch.get("points", 0) > 0:
        lines.append("💡 " + ("امتیاز ارتقا داری؛ از دکمه‌ی ارتقا استفاده کن." if L == "fa" else "You have upgrade points; open Upgrade to spend them."))
    if ch.get("guild_id"):
        g = await col("guilds").find_one({"_id": ch["guild_id"]})
        if g:
            lines.append("🛡️ " + esc(g["name_fa" if L == "fa" else "name_en"]))
    rows = [[(ctx.t("b_upgrade") + f" ({ch.get('points', 0)})", "upg", "")], [(ctx.t("m_bag"), "bag", "0"), (ctx.t("m_pty"), "pty", "0")], [(ctx.t("b_forge"), "frg", ""), (ctx.t("m_eqp"), "eqp", "")],
            [("🧍 " + ("تن من" if L == "fa" else "What I wear"), "worn", ""), ("🗡 " + ("سلاح نژاد" if L == "fa" else "Race weapon"), "rwp", "")],
            [("🎖 " + ("رنک نبرد" if L == "fa" else "Battle Rank"), "brk", "")]]
    gen = ch.get("gen_skill")  # general skill: any race can equip one (see data_race_rules.GENERAL_SKILLS)
    gen_name = {"guard": ("گارد", "Guard"), "strike": ("ضربه‌ی عمومی", "General strike"), "focus": ("تمرکز", "Focus")}.get(gen, ("هیچ", "None"))
    rows.append([("🧩 " + ("مهارت عمومی: " if L == "fa" else "General skill: ") + gen_name[0 if L == "fa" else 1], "gsp", "")])
    if ch.get("race") in ("shinigami", "visored"):  # the boss attack switch, reachable from the profile too
        kido = ch.get("boss_style") == "kido"
        if L == "fa":
            lbl = "🔁 حمله به باس: " + ("هادو" if kido else "زانپاکتو")
        else:
            lbl = "🔁 Boss attack: " + ("Hadō" if kido else "Zanpakutō")
        rows.append([(lbl, "bsp", "")])
    rows.append(nav(ctx))
    return Out("\n".join(lines), rows)


@action("bsp")
async def boss_style_profile(ctx, arg):
    me = await get_char(ctx.uid)
    if not me or me.get("race") not in ("shinigami", "visored"):
        return Out(alert=("فقط شینیگامی و ویزرد می‌تونن با هادو به باس حمله کنن." if ctx.lang == "fa"
                          else "Only Shinigami and Visored can strike bosses with Hadō."))
    new = "blade" if me.get("boss_style") == "kido" else "kido"
    await col("characters").update_one({"user_id": ctx.uid}, {"$set": {"boss_style": new}})
    return await profile(ctx, "")


@action("gsp")
async def general_skill_switch(ctx, arg):
    from data_race_rules import GEN_ORDER
    me = await get_char(ctx.uid)
    if not me:
        return Out(alert=ctx.t("not_registered"))
    cur = me.get("gen_skill")
    new = GEN_ORDER[(GEN_ORDER.index(cur) + 1) % len(GEN_ORDER)] if cur in GEN_ORDER else GEN_ORDER[1]
    await col("characters").update_one({"user_id": ctx.uid}, {"$set": {"gen_skill": new}})
    return await profile(ctx, "")


@action("upg")
async def upgrade(ctx, arg):
    L = ctx.lang
    k, _, many = (arg or "").partition(":")  # "zanjutsu" = +1, "zanjutsu:10" = +10 (or all points left when fewer)
    if k in STATS:
        want = 10 if many == "10" else 1
        have = int(((await col("characters").find_one({"user_id": ctx.uid}, {"points": 1})) or {}).get("points", 0))
        n = min(want, have)
        r = await col("characters").update_one({"user_id": ctx.uid, "points": {"$gte": n}}, {"$inc": {"points": -n, f"stats.{k}": n}}) if n >= 1 else None
        if not r or not r.modified_count:
            return Out(alert=ctx.t("no_points"))
    ch = await get_char(ctx.uid)
    rows = [[(f"➕ {STAT_ICON[s]} {ctx.t('stat_' + s)}: {fnum(int(ch['stats'][s]), L)}", "upg", s), ("+" + fnum(10, L), "upg", s + ":10")]
            for s in STATS]
    rows.append(nav(ctx, ("prof", "")))
    return Out(head(ctx, "ttl_upg") + ctx.t("upg_body", pts=fnum(ch.get("points", 0), L)), rows)


# ---- map / travel -------------------------------------------------------------------
@action("map")
async def world_map(ctx, arg):
    ch = await need_char(ctx)
    L = ctx.lang
    rows, body = [], [ctx.t("map_body", loc=loc_name(ch["location"], L)), f"<i>{esc(LOC_DESC[ch['location']][0 if L == 'fa' else 1])}</i>", ""]
    owners, crowds = await territory_owners(), await crowd_counts()
    for lid, loc in LOCATIONS.items():
        ok = ch["level"] >= loc["level"] and (not loc["race"] or loc["race"] == ch["race"] or loc["level"] <= 60)
        mark = "📍" if lid == ch["location"] else "✅" if ok else "🔒"
        extra = (f" 🏴{esc(owners[lid]['owner_fa' if L == 'fa' else 'owner_en'])}" if lid in owners else "") + (f" 👥{fnum(crowds[lid], L)}" if crowds.get(lid) else "")
        body.append(f"{mark} {loc_name(lid, L)} — {ctx.t('lbl_level')} {fnum(loc['level'], L)}{extra}")
        if ok and lid != ch["location"]:
            rows.append((f"🧭 {loc_name(lid, L)}", "tr", lid))
    return Out(head(ctx, "ttl_map") + "\n".join(body), chunk(rows, 2) + [nav(ctx)])


@action("tr")
async def travel(ctx, arg):
    ch = await need_char(ctx)
    loc = LOCATIONS.get(arg)
    if not loc or ch["level"] < loc["level"]:
        return Out(alert=ctx.t("loc_locked"))
    st = await game_settings()
    wait = await try_cooldown(f"travel:{ctx.uid}", int(st["travel_cooldown"]))
    if wait:
        return Out(alert=ctx.t("wait_s", n=wait))
    await col("characters").update_one({"user_id": ctx.uid}, {"$set": {"location": arg, "seen_at": int(time.time())}})
    return await world_map(ctx, "")


# ---- explore --------------------------------------------------------------------------
# konso = a lost soul to send on (ignoring it can birth a Hollow), pressure = a strong reiatsu approaches (elite fight or retreat)
EVENTS = [("item", .26), ("enemy", .22), ("npc", .12), ("secret", .09), ("empty", .12), ("gate", .03), ("konso", .09), ("pressure", .07)]


@action("exp")
async def explore(ctx, arg):
    ch = await need_char(ctx)
    L = ctx.lang
    st = await game_settings()
    if await active_pve(ctx.uid):
        from handlers_combat import resume_battle
        return await resume_battle(ctx)
    if arg != "go":
        cur, nxt, _ = energy_now(ch, st)
        rows = [[(ctx.t("b_go"), "exp", "go")], [(ctx.t("m_map"), "map", "")], nav(ctx)]
        atmosphere = f"<i>{esc(LOC_DESC[ch['location']][0 if L == 'fa' else 1])}</i>\n\n"
        return Out(head(ctx, "ttl_exp") + atmosphere + ctx.t("exp_body", loc=loc_name(ch["location"], L), en=fnum(cur, L), cost=fnum(st["explore_cost"], L)), rows)
    if ch.get("bx_hunt"):  # an unfinished hunt is resumed, not paid for again
        from handlers_hunt import start as hunt_start
        return await hunt_start(ctx, ch)
    ok, left, nxt = await spend_energy(ctx.uid, int(st["explore_cost"]))
    if not ok:
        return Out(alert=ctx.t("exp_no_energy", n=fnum(left, L), s=fnum(nxt // 60 + 1, L)))
    on_action_bg(ctx.uid, "explore", ch["location"])
    # every successful explore moves the incubator on by one; an egg that finishes hatches here
    from service_effects import tick_incubator
    from service_economy import PETS
    hatched = await tick_incubator(ctx.uid)
    from handlers_hunt import start as hunt_start
    out = await hunt_start(ctx, ch)
    if hatched and isinstance(out, Out):
        nm_ = PETS[hatched["sp"] % len(PETS)][0 if L == "en" else 1]
        note = (f"🐾 یک همراه ({nm_}) از تخم بیرون اومد!" if L == "fa" else f"🐾 A companion ({nm_}) hatched from the egg!")
        out.alert = f"{note}\n{out.alert}" if out.alert else note
    return out


async def _claim_pending(uid: int, kind: str):
    """Atomically take the pending hunt event (one answer per event, expires after 10 minutes)."""
    return await col("characters").find_one_and_update(
        {"user_id": uid, "bx_pending.kind": kind, "bx_pending.until": {"$gt": int(time.time())}}, {"$unset": {"bx_pending": ""}})


@action("kns")
async def konso(ctx, arg):
    """Konso: send a wandering soul to Soul Society (reward + counter) or leave it (it may become a Hollow)."""
    if not await _claim_pending(ctx.uid, "konso"):
        return Out(alert=ctx.t("exp_konso_gone"))
    L = ctx.lang
    again = [[(ctx.t("b_again"), "exp", "go")], nav(ctx)]
    if arg == "ig":
        await col("characters").update_one({"user_id": ctx.uid}, {"$inc": {"bx_hollow": 1}})
        return Out(head(ctx, "ttl_exp") + ctx.t("exp_konso_ignore"), again)
    ch = await need_char(ctx)
    st = await game_settings()
    bn = player_bonus(ch, ALL, st)
    wm = await mods_for(ch["location"])
    lvl = ch["level"]
    base_xp = int((18 + lvl * 4) * (1 + bn["hunt"]))
    _, _, xp = await add_xp(ctx.uid, int(base_xp * 1.3), "explore")
    coins = int((10 + lvl * 3) * float(st["coin_rate"]) * (1 + bn["coin"] + bn["hunt"]) * wm["coin"])
    await add_coins(ctx.uid, coins, "explore")
    r = await col("characters").find_one_and_update({"user_id": ctx.uid}, {"$inc": {"konso": 1}}, return_document=ReturnDocument.AFTER)
    n = int((r or {}).get("konso", 1))
    text = ctx.t("exp_konso_ok", xp=fnum(xp, L), coins=fnum(coins, L), n=fnum(n, L))
    if n % 10 == 0:  # every tenth soul: a small keepsake
        iid = await roll_drop(ctx.uid, source_mult=1.5, floor_idx=1)
        got = await inv_add(ctx.uid, iid, 1)
        text += "\n" + ctx.t("exp_konso_milestone", n=fnum(n, L), item=nm(iid, L)) + ("" if got else "\n" + ctx.t("bag_full"))
    return Out(head(ctx, "ttl_exp") + text, again)


@action("prs")
async def pressure(ctx, arg):
    """A strong reiatsu approaches: face it (elite fight, better rewards) or slip away."""
    if not await _claim_pending(ctx.uid, "pressure"):
        return Out(alert=ctx.t("exp_press_gone"))
    if arg == "run":
        ch = await need_char(ctx)
        _, _, xp = await add_xp(ctx.uid, int((18 + ch["level"] * 4) * 0.5), "explore")
        return Out(head(ctx, "ttl_exp") + ctx.t("exp_press_run", xp=fnum(xp, ctx.lang)), [[(ctx.t("b_again"), "exp", "go")], nav(ctx)])
    from handlers_combat import start_pve_panel
    return await start_pve_panel(ctx, force_elite=True)


# ---- ranking ---------------------------------------------------------------------------
@action("rnk")
async def ranking(ctx, arg):
    L = ctx.lang
    mode = arg or "lvl"
    key = [("rating", -1)] if mode == "pvp" else [("level", -1), ("xp", -1)]
    top = await col("characters").find({}, {"name": 1, "level": 1, "rating": 1, "race": 1, "cosmetics": 1, "seat": 1}).sort(key).limit(10).to_list(10)
    medals = ["🥇", "🥈", "🥉"] + [f"{i}." for i in range(4, 11)]
    lines = [f"{medals[i]} {cosmetic_tag(x, ALL)} {esc(x['name'])} — " + (f"{rank_letter(x['rating'])} {fnum(x['rating'], L)}" if mode == "pvp" else f"{ctx.t('lbl_level')} {fnum(x['level'], L)}") for i, x in enumerate(top)]
    rows = [[(ctx.t("rk_lvl"), "rnk", "lvl"), (ctx.t("rk_pvp"), "rnk", "pvp")], [(ctx.t("m_ssn"), "ssn", "")], nav(ctx)]
    return Out(head(ctx, "ttl_rnk") + ("\n".join(lines) or ctx.t("empty")), rows)


# ---- daily -------------------------------------------------------------------------------
@action("dly")
async def daily(ctx, arg):
    r = await claim_daily(ctx.uid)
    L = ctx.lang
    text = ctx.t("dly_done") if r is None else ctx.t("dly_ok", coins=fnum(r["coins"], L), streak=fnum(r["streak"], L)) + (("\n" + streak_line(r["streak"], L)) if streak_line(r["streak"], L) else "")
    return Out(head(ctx, "ttl_dly") + text, [nav(ctx)])


# ---- quests ------------------------------------------------------------------------------
QUEST_PAGE = 10  # quests per page: with 50+ quests one message cut off everything after the first ~25


@action("qst")
async def quests(ctx, arg):
    ch = await need_char(ctx)
    L = ctx.lang
    states = await quest_list(ctx.uid, ch["level"])
    pages = max(1, -(-len(states) // QUEST_PAGE))
    page = min(max(int(arg), 0), pages - 1) if (arg or "").isdigit() else 0
    ready = sum(1 for s in states if s["done"] and not s["claimed"])
    lines, rows = [], []
    for s in states[page * QUEST_PAGE:(page + 1) * QUEST_PAGE]:
        q = s["q"]
        mark = "✅" if s["claimed"] else "🎁" if s["done"] else "▫️"
        lines.append(f"{mark} <b>{esc(q['name_fa' if L == 'fa' else 'name_en'])}</b> [{ctx.t('qc_' + q['cat'])}] {fnum(s['prog'], L)}/{fnum(q['count'], L)}")
        if not s["claimed"] and q.get("desc_fa"):
            lines.append("   <i>" + esc(q["desc_fa" if L == "fa" else "desc_en"]) + "</i>")
        if s["done"] and not s["claimed"]:
            rows.append([(f"🎁 {esc(q['name_fa' if L == 'fa' else 'name_en'])}", "qc", f"{q['_id']}.{page}")])
    foot = f"\n{'صفحه' if L == 'fa' else 'Page'} {fnum(page + 1, L)}/{fnum(pages, L)}"
    if ready:
        foot += f" · 🎁 {fnum(ready, L)} " + ("جایزه‌ی آماده" if L == "fa" else "rewards ready")
    if pages > 1:
        rows.append([("◀️", "qst", str((page - 1) % pages), False, "none"), ("▶️", "qst", str((page + 1) % pages), False, "none")])
    body, size = [], 0
    for ln in lines:  # cut on whole lines so HTML tags never break
        size += len(ln) + 1
        if size > 3500:
            break
        body.append(ln)
    return Out(head(ctx, "ttl_qst") + "\n".join(body) + foot, rows + [nav(ctx)])


@action("qc")
async def quest_claim(ctx, arg):
    qid, _, pg = (arg or "").partition(".")  # "<quest id>.<page>": come back to the page the player was on
    d = await claim_quest(ctx.uid, qid)
    if not d:
        return Out(alert=ctx.t("qst_cant"))
    out = await quests(ctx, pg)
    out.alert = ctx.t("qst_claimed", xp=fnum(d["xp"], ctx.lang), coins=fnum(d["coins"], ctx.lang))
    return out


# ---- mini-games ----------------------------------------------------------------------------
@action("mgm")
async def minigames(ctx, arg):
    status, data = await mg_new(ctx.uid, ctx.lang)
    if status == "cool":
        return Out(head(ctx, "ttl_mgm") + ctx.t("wait_s", n=data), [[(ctx.t("b_again"), "mgm", "")], nav(ctx)])
    rows = [[(o, "mga", f"{data['gid']}.{i}")] for i, o in enumerate(data["options"])]
    return Out(head(ctx, "ttl_mgm") + data["q"], rows + [nav(ctx)])


@action("mga")
async def minigame_answer(ctx, arg):
    gid, _, idx = arg.partition(".")
    status, data = await mg_answer(ctx.uid, gid, int(idx or 0))
    if status == "gone":
        return Out(alert=ctx.t("mg_gone"))
    text = ctx.t("mg_right", xp=fnum(data, ctx.lang)) if status == "right" else ctx.t("mg_wrong", ans=esc(data))
    return Out(head(ctx, "ttl_mgm") + text, [[(ctx.t("b_again"), "mgm", "")], nav(ctx)])


# ---- guilds ---------------------------------------------------------------------------------
@action("gld")
async def guilds(ctx, arg):
    ch = await need_char(ctx)
    L = ctx.lang
    if ch.get("guild_id"):
        g = await col("guilds").find_one({"_id": ch["guild_id"]})
        if g:
            body = ctx.t("gld_mine", name=esc(g["name_fa" if L == "fa" else "name_en"]), n=fnum(g["members"], L), bank=fnum(g["bank"], L), role=ctx.t("role_" + ch.get("guild_role", "member")))
            rows = [[(ctx.t("b_deposit") + " 500", "gdp", "500"), (ctx.t("b_deposit") + " 5000", "gdp", "5000")], [(ctx.t("b_leave"), "gll", "")], nav(ctx)]
            return Out(head(ctx, "ttl_gld") + body, rows)
    page = int(arg) if arg.isdigit() else 0
    items = await guild_list(page)
    rows = [[(f"{'⚔️' if g['kind'] == 'squad' else '🛡️'} {g['name_fa' if L == 'fa' else 'name_en']} ({g['members']})", "gj", g["_id"])] for g in items]
    rows.append([("◀️", "gld", str(max(0, page - 1)), False, "none"), ("▶️", "gld", str(page + 1), False, "none")])
    rows.append([(ctx.t("b_create"), "glc", "")])
    rows.append(nav(ctx))
    return Out(head(ctx, "ttl_gld") + ctx.t("gld_none"), rows)


@action("gj")
async def guild_join_cb(ctx, arg):
    r = await guild_join(ctx.uid, arg)
    if r != "ok":
        return Out(alert=ctx.t("gld_e_" + r))
    return await guilds(ctx, "")


@action("gll")
async def guild_leave_cb(ctx, arg):
    r = await guild_leave(ctx.uid)
    if r != "ok":
        return Out(alert=ctx.t("gld_e_" + r))
    return await guilds(ctx, "")


@action("gdp")
async def guild_deposit_cb(ctx, arg):
    r = await guild_deposit(ctx.uid, int(arg))
    if r != "ok":
        return Out(alert=ctx.t("gld_e_" + r))
    return await guilds(ctx, "")


@action("glc")
async def guild_create_prompt(ctx, arg):
    st = await game_settings()
    await col("inputs").update_one({"user_id": ctx.uid}, {"$set": {"kind": "guild_name", "at": int(time.time())}}, upsert=True)
    return Out(head(ctx, "ttl_gld") + ctx.t("gld_ask_name", cost=fnum(st["guild_create_cost"], ctx.lang), lvl=fnum(st["guild_min_level"], ctx.lang)), [nav(ctx, ("gld", ""))])


@input_handler("guild_name")
async def guild_name_input(ctx, text):
    try:
        name = clean_name(text)
    except ValueError:
        return Out(ctx.t("reg_name_chars"))
    status, extra = await guild_create(ctx.uid, name)
    if status != "ok":
        return Out(ctx.t("gld_c_" + status, n=fnum(extra or 0, ctx.lang)))
    return Out(ctx.t("gld_created", name=esc(name)), [[(ctx.t("m_gld"), "gld", "")]])


# ---- settings & help ---------------------------------------------------------------------------
@action("set")
async def settings_panel(ctx, arg):
    rows = [[("🇮🇷 فارسی", "lang", "fa"), ("🇬🇧 English", "lang", "en")], nav(ctx)]
    return Out(head(ctx, "ttl_set") + ctx.t("set_body"), rows)


@action("cmd")
async def commands_panel(ctx, arg):
    rows = [[(ctx.t("m_wrd"), "wrd", ""), (ctx.t("m_crf"), "crf", "")], [(ctx.t("m_hlp"), "hlp", "")], nav(ctx)]
    return Out(head(ctx, "ttl_cmd") + ctx.t("cmd_body"), rows, new=not ctx.private)


@action("hlp")
async def help_panel(ctx, arg):
    """The guide: one topic per system (data_help.TOPICS), the stats page, and a guide page for every race."""
    from data_help import STATS_TOPIC, TOPIC_ORDER, TOPICS
    from data_races import RACES
    lang = "fa" if ctx.lang == "fa" else "en"
    back = [nav(ctx, ("hlp", ""))]
    if arg == "stats":
        return Out(STATS_TOPIC[lang], back)
    if arg in TOPICS:
        return Out(TOPICS[arg][2][lang], back)
    if arg == "races":
        rows = [[(("🧬 " + r["name_fa"]) if lang == "fa" else ("🧬 " + r["name_en"]), "hlp", "race:" + k)] for k, r in RACES.items()]
        text = ("🧬 <b>نژادها</b>\nروی هر نژاد بزن تا راهنمای کاملش را ببینی." if lang == "fa"
                else "🧬 <b>Races</b>\nTap a race to see its full guide.")
        return Out(text, rows + back)
    if arg.startswith("race:") and arg[5:] in RACES:
        from data_guides import race_guide
        return Out(race_guide(arg[5:], lang), [nav(ctx, ("hlp", "races"))])
    names = {"stats": ("📊 استت‌ها", "📊 Stats"), "races": ("🧬 نژادها", "🧬 Races")}
    for k, (fa, en, _t) in TOPICS.items():
        names[k] = (fa, en)
    labels = [(names[k][0 if lang == "fa" else 1], "hlp", k) for k in TOPIC_ORDER if k in names]
    topics = [labels[i:i + 2] for i in range(0, len(labels), 2)]
    return Out(head(ctx, "ttl_hlp") + ctx.t("help_body"), topics + [nav(ctx)])


@action("worn")
async def worn_panel(ctx, arg):
    """Deep view of what the character wears: three pages.
    Page 0: the four gear pieces with their full item cards (weapon forge level, armour tempering included).
    Page 1: relics with real power, cosmetics, companion, artifact, evolution and the total bonuses."""
    from fmt import item_card
    from effects import RELIC_MAX_LVL, relic_level_mult, relic_slots
    from handlers_world import bonus_line as _bl
    ch = await need_char(ctx)
    L, fa = ctx.lang, ctx.lang == "fa"
    st = await game_settings()
    # the profile button sends an empty arg; int("") used to raise here, so "تن من" never opened
    page = int(arg) if str(arg or "").strip() in ("0", "1", "2") else 0
    H = lambda t: f"\n<b>{t}</b>"  # noqa: E731

    if page == 0:
        parts = ["🧍 <b>" + ("تن من — جنگ‌افزار و پوشش" if fa else "What I wear — gear") + "</b>  (1/3)"]
        for field, label in (("weapon_id", "⚔️"), ("armor_id", "🛡️"), ("acc_id", "💍"), ("charm_id", "📿")):
            iid = ch.get(field)
            if not iid or iid not in ALL:
                parts.append(H(f"{label} " + ("خالی" if fa else "empty")))
                continue
            extra = []
            if field == "weapon_id":
                plus = int((ch.get("weapon_plus") or {}).get(iid, 0))
                if plus:  # show what the level is worth: forge gives +6% attack per level
                    extra.append(f"🔨 +{fnum(plus, L)} (×{round(1 + 0.06 * plus, 2)} {'قدرت' if fa else 'attack'})")
            if field == "armor_id":
                plus = int((ch.get("armor_plus") or {}).get(iid, 0))
                if plus:  # tempering adds temper_def_pct of the base defence per level
                    pct = round(float(st["temper_def_pct"]) * 100 * plus)
                    extra.append(f"🔨 +{fnum(plus, L)} (+{fnum(pct, L)}٪ {'دفاع' if fa else 'defence'})")
            parts.append(H(f"{label} " + ("" if not extra else " ".join(extra))) + "\n" + item_card(ctx, iid))
        bn = player_bonus(ch, ALL, st)
        parts.append(H("🧿 " + ("بونوس کل" if fa else "Total bonuses")) + "\n" + _bl(ctx, bn))
        rows = [[("➡️ " + ("ادامه" if fa else "Next"), "worn", "1")], nav(ctx, ("prof", ""))]
    elif page == 2:
        parts = ["🧍 <b>" + ("تن من — تحلیل عددی" if fa else "What I wear — numbers") + "</b>  (3/3)"]
        # real combat numbers
        wid = ch.get("weapon_id")
        w = ALL.get(wid) or {}
        wplus = int((ch.get("weapon_plus") or {}).get(wid, 0))
        if w:
            atk = float(w.get("attack", 0)) * (1 + 0.06 * wplus)
            parts.append(H("⚔️ " + ("جنگ‌افزار در مبارزه" if fa else "Weapon in combat")))
            parts.append(f"• {'قدرت' if fa else 'attack'}: {fnum(int(atk), L)} (پایه {fnum(int(w.get('attack', 0)), L)} · فورج +{fnum(wplus, L)} ×{round(1 + 0.06 * wplus, 2)})")
            parts.append(f"• {'شانس کریتیکال' if fa else 'crit'}: {round(float(w.get('crit', 0)) * 100, 1)}%")
        from data_zanpakuto import bond_value
        bond = bond_value(ch)
        zst = ch.get("zanpakuto") or {}
        parts.append(H("🔗 " + ("زانپاکتو" if fa else "Zanpakuto")))
        parts.append(f"• {'پیوند' if fa else 'bond'}: {fnum(bond, L)} → ×{round(1 + min(1.0, bond / 500), 2)} "
                     f"({'سقف پیوند ۵۰۰' if fa else 'cap 500'})")
        parts.append(f"• {'شکل' if fa else 'form'}: " + (("بانکای" if fa else "Bankai") if zst.get("bankai") else ("شیکای" if zst.get("shikai") else ("عادی" if fa else "normal"))))
        if zst.get("mastery") is not None:
            parts.append(f"• {'تسلط' if fa else 'mastery'}: {fnum(int(zst.get('mastery', 0)), L)}")
        # where the bonus comes from: remove one source at a time and see what it was worth
        full = player_bonus(ch, ALL, st)
        sources = [
            ("🗿 " + ("یادگارها" if fa else "Relics"), {"relics": []}),
            ("🐾 " + ("همراه" if fa else "Companion"), {"pets": []}),
            ("🔱 " + ("آرتیفکت" if fa else "Artifact"), {"artifact": None}),
            ("🔮 " + ("هوگیوکو" if fa else "Hōgyoku"), {"hogyoku": False}),
            ("⬆️ " + ("تکامل" if fa else "Evolution"), {"evo": 0}),
            ("🎲 " + ("باف موقت" if fa else "Temporary buffs"), {"buffs": {}}),
        ]
        parts.append(H("📊 " + ("سهم هر منبع از بونوس" if fa else "Where the bonus comes from")))
        keys = [k for k in ("dmg", "def", "crit", "xp", "drop", "coin") if full.get(k)]
        if not keys:
            parts.append("—")
        for label, patch in sources:
            alt = dict(ch, **patch)
            without = player_bonus(alt, ALL, st)
            diff = {k: full[k] - without.get(k, 0) for k in keys if abs(full[k] - without.get(k, 0)) > 1e-9}
            if diff:
                parts.append(f"• {label}: " + " ".join(f"{k} +{round(v * 100, 1)}%" for k, v in diff.items()))
            else:
                parts.append(f"• {label}: —")
        parts.append(f"<i>{'جمع با سقف بازی، پس ممکن است کمتر از مجموع باشد.' if fa else 'Totals are capped by the game, so the sum may be lower.'}</i>")
        rows = [[("⬅️ " + ("قبلی" if fa else "Back"), "worn", "1")], nav(ctx, ("prof", ""))]
    else:
        parts = ["🧍 <b>" + ("تن من — یادگار و ظاهر" if fa else "What I wear — relics & look") + "</b>  (2/3)"]
        slots = relic_slots(int(ch.get("level", 1)), st)
        rel = list(dict.fromkeys(ch.get("relics") or []))
        parts.append(H(("🗿 یادگارها" if fa else "🗿 Relics") + f" ({fnum(min(len(rel), slots), L)}/{fnum(slots, L)})"))
        if not rel:
            parts.append("—")
        for iid in rel[:slots]:
            lvl = int((ch.get("relic_lvl") or {}).get(iid, 1))
            mult = relic_level_mult(ch, iid)
            parts.append(f"• <b>{nm(iid, L)}</b> — {'سطح' if fa else 'Lv.'} {fnum(lvl, L)}/{fnum(RELIC_MAX_LVL, L)} · "
                         f"{'قدرت' if fa else 'power'} ×{round(mult, 2)}"
                         + (f"\n   <i>{effect_text(ctx, ALL[iid])}</i>" if iid in ALL else ""))
        cs = ch.get("cosmetic") or {}
        parts.append(H("✨ " + ("ظاهر" if fa else "Look")))
        shown = [f"• <b>{nm(cs[k], L)}</b>" + (f"\n   <i>{effect_text(ctx, ALL[cs[k]])}</i>" if cs[k] in ALL else "") for k in ("aura", "trail", "banner") if cs.get(k)]
        parts.append("\n".join(shown) or "—")
        pets = ch.get("pets") or []
        parts.append(H("🐾 " + ("همراه" if fa else "Companion")))
        if pets:
            from service_economy import PETS
            # same line as the companion list: the role comes from the species, which is what the bonus uses
            from fmt import pet_line
            parts.append("• " + pet_line(ctx, pets[0]))
            parts.append(f"   {'همراه‌ها' if fa else 'Companions'}: {fnum(len(pets), L)}/12")
        else:
            parts.append("—")
        if ch.get("artifact"):
            from data_artifacts import art_name
            parts.append(H("🔱 " + ("آرتیفکت" if fa else "Artifact")) + "\n• " + art_name(ch["artifact"], L))
        if ch.get("hogyoku"):
            parts.append(H("🔮 " + ("هوگیوکو" if fa else "Hōgyoku")))
        stage = int(ch.get("evo", 0) or 0)
        if stage:
            parts.append(H("⬆️ " + ("تکامل" if fa else "Evolution")) + f" {fnum(stage, L)}")
        rows = [[("⬅️ " + ("قبلی" if fa else "Back"), "worn", "0"), ("➡️ " + ("ادامه" if fa else "Next"), "worn", "2")], nav(ctx, ("prof", ""))]
    text = "\n".join(parts)
    if len(text) > 3900:
        text = text[:3900] + "…"
    return Out(text, rows)
