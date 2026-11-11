"""Home, profile, stat upgrades, world map, exploration, quests, ranking, daily,
mini-games, guilds, settings and help."""
import random
import time

from data_crafting import cosmetic_tag, player_bonus
from data_items import ALL
from data_races import LOCATIONS, RACES, STAT_ICON, STATS, soft_stat
from database import col, game_settings, try_cooldown
from render import pick
from fmt import nm, race_name, stats_block, title_of
from handlers_world import bonus_line, world_line
from service_interact import crowd_counts, find_trace
from service_worldcore import mods_for
from service_worldstate import on_action, territory_income, territory_owners
from i18n import bar, esc, fnum
from security import clean_name
from data_lore import streak_line
from data_misc import LOC_DESC, LORE
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
    # home keeps only the 6 things people use every minute; everything else lives in "More", grouped
    rows = [[(ctx.t("m_exp"), "exp", ""), (ctx.t("m_bt"), "bt", "")],
            [(ctx.t("m_prof"), "prof", ""), (ctx.t("m_bag"), "bag", "0")],
            [(ctx.t("m_qst"), "qst", ""), (ctx.t("m_mkt"), "mkt", "")],
            [(ctx.t("b_more"), "menu2", "")]]
    return Out(text, rows)


@action("menu2")
async def menu2(ctx, arg):
    rows = [[(ctx.t("mg_adv"), "mg", "adv"), (ctx.t("mg_grow"), "mg", "grow")],
            [(ctx.t("mg_soc"), "mg", "soc"), (ctx.t("mg_fun"), "mg", "fun")],
            [(ctx.t("m_set"), "set", ""), (ctx.t("m_hlp"), "hlp", "")], nav(ctx)]
    return Out(head(ctx, "ttl_menu") + ctx.t("menu_body"), rows)


# "More" is split into four small groups of at most 4 buttons, so no screen ever shows a wall of options.
MENU_GROUPS = {
    "adv": [[("m_dgn", "dgn"), ("m_twr", "twr")], [("m_map", "map"), ("m_wrd", "wrd")]],
    "grow": [[("m_gch", "gch"), ("m_crf", "crf")], [("m_dsp", "dsp"), ("m_art", "art")], [("m_inr", "inr"), ("m_sat", "sat")]],
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
    lines = [head(ctx, "ttl_prof"),
             ctx.t("prof_body", name=esc(ch["name"]), race=race_name(ch["race"], L), title=title_of(ch, L), lvl=fnum(ch["level"], L),
                   rank=rank_label(ch["rating"], L), rating=fnum(ch["rating"], L), bond=fnum(min(30, (ch.get("bond") or {}).get(ch.get("weapon_id"), 0) // 5), L), plus=fnum((ch.get("weapon_plus") or {}).get(ch.get("weapon_id"), 0), L), w=fnum(ch["wins"], L), l=fnum(ch["losses"], L),
                   pw=fnum(ch["pvp_w"], L), pl=fnum(ch["pvp_l"], L), power=fnum(power(ch), L)),
             stats_block(ctx, ch["stats"]),
             "🧿 " + bonus_line(ctx, player_bonus(ch, ALL, await game_settings())),
             f"⚔️ {nm(ch['weapon_id'], L)}\n🛡️ {nm(ch.get('armor_id'), L)}\n💍 {nm(ch.get('acc_id'), L)}\n📿 {nm(ch.get('charm_id'), L)}"]
    if ch.get("artifact"):
        from data_artifacts import art_name
        lines.append("🔱 " + art_name(ch["artifact"], L))
    if ch.get("guild_id"):
        g = await col("guilds").find_one({"_id": ch["guild_id"]})
        if g:
            lines.append("🛡️ " + esc(g["name_fa" if L == "fa" else "name_en"]))
    rows = [[(ctx.t("b_upgrade") + f" ({ch.get('points', 0)})", "upg", "")], [(ctx.t("m_bag"), "bag", "0"), (ctx.t("m_pty"), "pty", "0")], [(ctx.t("b_forge"), "frg", ""), (ctx.t("m_eqp"), "eqp", "")], nav(ctx)]
    return Out("\n".join(lines), rows)


@action("upg")
async def upgrade(ctx, arg):
    L = ctx.lang
    if arg in STATS:
        r = await col("characters").update_one({"user_id": ctx.uid, "points": {"$gte": 1}}, {"$inc": {"points": -1, f"stats.{arg}": 1}})
        if not r.modified_count:
            return Out(alert=ctx.t("no_points"))
    ch = await get_char(ctx.uid)
    rows = [[(f"➕ {STAT_ICON[k]} {ctx.t('stat_' + k)}: {fnum(int(ch['stats'][k]), L)}", "upg", k)] for k in STATS]
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
EVENTS = [("item", .30), ("enemy", .25), ("npc", .15), ("secret", .10), ("empty", .15), ("gate", .05)]


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
    ok, left, nxt = await spend_energy(ctx.uid, int(st["explore_cost"]))
    if not ok:
        return Out(alert=ctx.t("exp_no_energy", n=fnum(left, L), s=fnum(nxt // 60 + 1, L)))
    await on_action(ctx.uid, "explore", ch["location"])
    bn = player_bonus(ch, ALL, st)
    wm = await mods_for(ch["location"])
    roll, acc, ev = random.random(), 0.0, "empty"
    for name, p in EVENTS:
        acc += p
        if roll <= acc:
            ev = name
            break
    lvl = ch["level"]
    base_xp = int((18 + lvl * 4) * (1 + bn["patrol"]))
    text = ""
    terr = None
    if ev == "enemy":
        from handlers_combat import start_pve_panel
        return await start_pve_panel(ctx)
    if ev == "item":
        iid = await roll_drop(ctx.uid)
        got = await inv_add(ctx.uid, iid, 1)
        _, _, xp = await add_xp(ctx.uid, base_xp, "explore")
        text = ctx.t("exp_item", item=nm(iid, L), xp=fnum(xp, L)) + ("" if got else "\n" + ctx.t("bag_full"))
    elif ev == "npc":
        _, _, xp = await add_xp(ctx.uid, int(base_xp * 1.2), "explore")
        coins = int((10 + lvl * 3) * float(st["coin_rate"]) * (1 + bn["coin"] + bn["patrol"]) * wm["coin"])
        await add_coins(ctx.uid, coins, "explore")
        terr = await territory_income(ctx.uid, ch["location"], coins, xp)
        text = ctx.t("exp_npc", xp=fnum(xp, L), coins=fnum(coins, L), lore=random.choice(LORE[ch["location"]])[0 if L == "fa" else 1])
    elif ev == "secret":
        iid = await roll_drop(ctx.uid, source_mult=1.5, floor_idx=1)
        got = await inv_add(ctx.uid, iid, 1)
        _, _, xp = await add_xp(ctx.uid, base_xp * 2, "explore")
        text = ctx.t("exp_secret", item=nm(iid, L), xp=fnum(xp, L)) + ("" if got else "\n" + ctx.t("bag_full"))
    elif ev == "gate":
        keys = [i for i, x in ALL.items() if x.get("effect") and x["effect"].get("type") == "key" and x["effect"]["diff"] == "hard"]
        iid = random.choice(keys)
        await inv_add(ctx.uid, iid, 1, force=True)
        _, _, xp = await add_xp(ctx.uid, base_xp, "explore")
        text = ctx.t("exp_gate", item=nm(iid, L), xp=fnum(xp, L))
    else:
        _, _, xp = await add_xp(ctx.uid, int(base_xp * 0.5), "explore")
        text = ctx.t("exp_empty", xp=fnum(xp, L), lore=random.choice(LORE[ch["location"]])[0 if L == "fa" else 1])
    from service_player import bump_quest
    await bump_quest(ctx.uid, "explore", 1)
    if terr:
        text += "\n" + (ctx.t("ter_got_mine", c=fnum(terr["coins"], L), x=fnum(terr["xp"], L)) if terr.get("mine") else ctx.t("ter_got_tax", n=fnum(terr["tax"], L)))
    tr = await find_trace(ctx.uid)
    if tr:
        text += "\n\n" + pick(L, "trace_found_" + tr["kind"], icon=tr["icon"], who=esc(tr["owner"]), c=fnum(tr["coins"], L), x=fnum(tr["xp"], L))
    return Out(head(ctx, "ttl_exp") + text, [[(ctx.t("b_again"), "exp", "go")], nav(ctx)])


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
@action("qst")
async def quests(ctx, arg):
    ch = await need_char(ctx)
    L = ctx.lang
    states = await quest_list(ctx.uid, ch["level"])
    lines, rows, shown = [], [], 0
    for s in states:
        q = s["q"]
        mark = "✅" if s["claimed"] else "🎁" if s["done"] else "▫️"
        lines.append(f"{mark} <b>{esc(q['name_fa' if L == 'fa' else 'name_en'])}</b> [{ctx.t('qc_' + q['cat'])}] {fnum(s['prog'], L)}/{fnum(q['count'], L)}")
        if not s["claimed"] and shown < 6 and q.get("desc_fa"):
            lines.append("   <i>" + esc(q["desc_fa" if L == "fa" else "desc_en"]) + "</i>")
            shown += 1
        if s["done"] and not s["claimed"] and len(rows) < 6:
            rows.append([(f"🎁 {esc(q['name_fa' if L == 'fa' else 'name_en'])}", "qc", q["_id"])])
    body, size = [], 0
    for ln in lines:  # cut on whole lines so HTML tags never break
        size += len(ln) + 1
        if size > 3500:
            break
        body.append(ln)
    return Out(head(ctx, "ttl_qst") + "\n".join(body), rows + [nav(ctx)])


@action("qc")
async def quest_claim(ctx, arg):
    d = await claim_quest(ctx.uid, arg)
    if not d:
        return Out(alert=ctx.t("qst_cant"))
    out = await quests(ctx, "")
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
    return Out(head(ctx, "ttl_hlp") + ctx.t("help_body"), [nav(ctx)])
