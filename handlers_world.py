"""Panels for the shared world (hub, boss helpers, events, territories, season, chronicle, here/aid/traces,
bounties) and for item roles (craft, tempering, evolution, relics, cosmetics, pets). Also the broadcast
helpers the scheduler uses. UI stays word + simple buttons."""
import asyncio
import logging
import time

from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError
from aiogram.types import InlineKeyboardMarkup

from data_crafting import (GROUPS, PET_ROLES, evo_next, evo_stage, player_bonus, plan_inputs, race_title_ev, tagged_name, temper_recipe, _fits)
from data_items import ALL
from data_races import LOCATIONS, RACES
from data_weapons import RARITIES, RARITY_ICON
from data_world import EVENTS, KEY_PTS, week_id
from database import col, game_settings
from fmt import item_card, nm, pet_line
from i18n import bar, esc, fnum
from render import both, boss_text, gl, glang, pick
from security import make_cb
from service_crafting import (RECIPE_BY_ID, RECIPES, craft, cosmetic_remove, cosmetic_wear, evo_start, pet_activate, recipes_for, relic_attune,
                              relic_release, scaled_coins, temper)
from service_economy import PETS, inv_get
from service_interact import (MARK_ICON, MARKS, bounty_board, bounty_place, bounty_total, crowd, crowd_counts, find_by_name, leave_trace, send_aid)
from service_player import get_char
from service_world import active_boss, broadcast_groups, group_doc
from service_worldcore import chronicle_text, get_world, mods_for
from service_worldstate import event_contribute_key, season_top, territory_board, territory_owners
from ui import INPUTS, Out, action, chunk, head, input_handler, make_button, markup, nav

log = logging.getLogger("senka.hworld")
PER_PAGE = 6


def loc_name(loc_id: str, lang: str) -> str:
    return LOCATIONS[loc_id]["fa" if lang == "fa" else "en"]


def ev_name(ctx_or_lang, kind: str) -> str:
    from i18n import t
    lang = getattr(ctx_or_lang, "lang", ctx_or_lang)
    return f"{EVENTS[kind]['icon']} {t(lang, 'ev_' + kind + '_name')}"


def _mins(sec: int) -> int:
    return max(0, int(sec)) // 60 + 1


# ---- small shared text blocks ------------------------------------------------------------------------------------------
async def world_line(ctx, ch: dict) -> str:
    """Two compact lines for the home panel: the world's pulse and the active event."""
    ws, ev = await get_world()
    L = ctx.lang
    line = ctx.t("wrd_line", threat=fnum(ws.get("threat", 20), L), stab=fnum(ws.get("stability", 70), L),
                 rei=fnum((ws.get("reishi") or {}).get(ch["location"], 50), L))
    if ev:
        line += "\n" + ctx.t("wrd_event_line", ev=ev_name(ctx, ev["kind"]), p=fnum(min(100, ev["progress"] * 100 // max(1, ev["goal"])), L),
                             m=fnum(_mins(ev["end_at"] - time.time()), L))
    return line


def _boss_line(ctx, b) -> str:
    L = ctx.lang
    if b:
        return ctx.t("wrd_boss_on", name=esc(b["name_fa" if L == "fa" else "name_en"]), p=fnum(max(0, b["hp"]) * 100 // b["max_hp"], L),
                     m=fnum(_mins(b["expires_at"] - time.time()), L))
    return ""


# ---- hub ------------------------------------------------------------------------------------------------------------------
@action("wrd")
async def world_hub(ctx, arg):
    ch = await get_char(ctx.uid)
    L = ctx.lang
    ws, ev = await get_world(force=True)
    wm = await mods_for(ch["location"])
    b = await active_boss()
    lines = [head(ctx, "ttl_wrd") + "<i>" + pick(ctx.lang, "epi_wrd") + "</i>\n\n",
             ctx.t("wrd_vars", threat=fnum(ws.get("threat", 20), L), tbar=bar(ws.get("threat", 20), 100, 8),
                   stab=fnum(ws.get("stability", 70), L), sbar=bar(ws.get("stability", 70), 100, 8),
                   rei=fnum(wm["reishi"], L), rbar=bar(wm["reishi"], 100, 8), loc=loc_name(ch["location"], L)),
             ctx.t("wrd_effects", enemy=fnum(round((wm["enemy"] - 1) * 100), L), drop=fnum(round((wm["drop"] - 1) * 100), L),
                   xp=fnum(round((wm["xp"] - 1) * 100), L), price=fnum(round((wm["price"] - 1) * 100), L))]
    if ev:
        lines.append(ctx.t("wrd_event_line", ev=ev_name(ctx, ev["kind"]), p=fnum(min(100, ev["progress"] * 100 // max(1, ev["goal"])), L),
                           m=fnum(_mins(ev["end_at"] - time.time()), L)))
    bl = _boss_line(ctx, b)
    lines.append(bl or ctx.t("wrd_boss_next", m=fnum(_mins(ws.get("next_boss_at", 0) - time.time()), L)))
    chron = await chronicle_text(L, 4)
    if chron:
        lines += ["", ctx.t("wrd_chron_title"), chron]
    rows = [[(ctx.t("m_boss"), "bossinfo", ""), (ctx.t("m_evt"), "evt", "")],
            [(ctx.t("m_ter"), "ter", ""), (ctx.t("m_hre"), "hre", "")],
            [(ctx.t("m_bty"), "bty", ""), (ctx.t("m_ssn"), "ssn", "")],
            [(ctx.t("m_chr"), "chr", "")], nav(ctx)]
    return Out("\n".join(lines), rows)


@action("chr")
async def chronicle_panel(ctx, arg):
    text = await chronicle_text(ctx.lang, 12)
    return Out(head(ctx, "ttl_chr") + (text or ctx.t("chr_empty")), [nav(ctx, ("wrd", ""))])


# ---- world events -----------------------------------------------------------------------------------------------------------------
async def event_text(ctx, ev) -> str:
    L = ctx.lang
    contrib = {int(k): v for k, v in (ev.get("contrib") or {}).items()}
    top = sorted(contrib.items(), key=lambda kv: -kv[1])[:5]
    nmap = ev.get("nm") or {}
    lines = [head(ctx, "ttl_evt"), f"<b>{ev_name(ctx, ev['kind'])}</b>", f"<i>{ctx.t('ev_' + ev['kind'] + '_desc')}</i>",
             f"{bar(min(ev['progress'], ev['goal']), ev['goal'], 14)} {fnum(ev['progress'], L)}/{fnum(ev['goal'], L)}",
             ctx.t("evt_left", m=fnum(_mins(ev["end_at"] - time.time()), L)), ctx.t("evt_mine", n=fnum(contrib.get(ctx.uid, 0), L))]
    for i, (uid, pts) in enumerate(top):
        lines.append(f"{['🥇', '🥈', '🥉', '4.', '5.'][i]} {esc(nmap.get(str(uid), '?'))} — {fnum(pts, L)}")
    return "\n".join(lines)


@action("evt")
async def event_panel(ctx, arg):
    ws, ev = await get_world(force=True)
    L = ctx.lang
    if not ev:
        return Out(head(ctx, "ttl_evt") + ctx.t("evt_none", m=fnum(_mins(ws.get("next_event_at", 0) - time.time()), L)), [nav(ctx, ("wrd", ""))])
    inv = await inv_get(ctx.uid)
    keys = [i for i, q in inv["items"].items() if q > 0 and (ALL.get(i, {}).get("effect") or {}).get("type") == "key"]
    keys.sort(key=lambda i: -KEY_PTS.get(ALL[i]["effect"]["diff"], 1))
    rows = [[(f"🗝️ {nm(i, L)} (+{KEY_PTS.get(ALL[i]['effect']['diff'], 1)})".replace("<", "").replace(">", ""), "evk", i)] for i in keys[:5]]
    return Out(await event_text(ctx, ev) + "\n\n" + ctx.t("evt_keyhint"), rows + [nav(ctx, ("wrd", ""))])


@action("evk")
async def event_key(ctx, arg):
    r, pts = await event_contribute_key(ctx.uid, arg)
    if r != "ok":
        return Out(alert=ctx.t("evt_e_" + r))
    out = await event_panel(ctx, "")
    out.alert = ctx.t("evt_key_ok", n=fnum(pts, ctx.lang))
    return out


# ---- territories --------------------------------------------------------------------------------------------------------------------
@action("ter")
async def territory_panel(ctx, arg):
    ch = await get_char(ctx.uid)
    L = ctx.lang
    st = await game_settings()
    owner, top = await territory_board(ch["location"])
    owners = await territory_owners()
    lines = [head(ctx, "ttl_ter") + "<i>" + pick(ctx.lang, "epi_ter") + "</i>\n\n", ctx.t("ter_body", loc=loc_name(ch["location"], L), buff=fnum(round(float(st["terr_buff_pct"]) * 100), L),
                                         tax=fnum(round(float(st["terr_tax_pct"]) * 100), L))]
    if owner and owner.get("owner"):
        lines.append(ctx.t("ter_owner", g=esc(owner["owner_fa" if L == "fa" else "owner_en"])))
    else:
        lines.append(ctx.t("ter_free"))
    if top:
        lines.append(ctx.t("ter_top"))
        for i, (gid, fa, en, pts) in enumerate(top):
            lines.append(f"{['🥇', '🥈', '🥉'][i]} {esc(fa if L == 'fa' else en)} — {fnum(pts, L)}" + (" ⭐" if gid == ch.get("guild_id") else ""))
    lines.append(ctx.t("ter_rules", n=fnum(st["terr_min_members"], L), s=fnum(st["terr_min_score"], L)))
    lines.append("")
    for lid in LOCATIONS:
        o = owners.get(lid)
        lines.append(f"{'📍' if lid == ch['location'] else '▫️'} {loc_name(lid, L)}: " + (f"🏴 {esc(o['owner_fa' if L == 'fa' else 'owner_en'])}" if o else "—"))
    return Out("\n".join(lines), [[(ctx.t("m_gld"), "gld", "")], nav(ctx, ("wrd", ""))])


# ---- here: crowd, aid, traces -------------------------------------------------------------------------------------------------------
@action("hre")
async def here_panel(ctx, arg):
    ch = await get_char(ctx.uid)
    L = ctx.lang
    st = await game_settings()
    total, others = await crowd(ch["location"], ctx.uid)
    from datetime import datetime, timezone
    traces = await col("traces").count_documents({"loc": ch["location"], "active": True, "expire_at": {"$gt": datetime.now(timezone.utc)}})
    lines = [head(ctx, "ttl_hre") + "<i>" + pick(ctx.lang, "epi_hre") + "</i>\n\n", ctx.t("hre_body", loc=loc_name(ch["location"], L), n=fnum(total, L), tr=fnum(traces, L),
                                         cost=fnum(st["trace_cost"], L), en=fnum(st["aid_energy"], L))]
    rows = []
    for o in others:
        from data_crafting import cosmetic_tag
        tag = cosmetic_tag(o, ALL)
        rows.append((f"💞 {tag} {o['name']} · {ctx.t('lbl_level')} {o['level']}".replace("  ", " "), "aid", str(o["user_id"])))
    rows = chunk(rows, 1)
    rows.append([(f"{MARK_ICON[m]} {fnum(st['trace_cost'], L)}🪙", "trc", m) for m in MARKS])
    rows.append(nav(ctx, ("wrd", "")))
    return Out("\n".join(lines), rows)


@action("aid")
async def aid_do(ctx, arg):
    if not arg.isdigit():
        return Out()
    r, data = await send_aid(ctx.uid, int(arg))
    if r != "ok":
        return Out(alert=ctx.t("aid_e_" + r, n=data or 0))
    try:
        tl = await _user_lang(int(arg))
        from i18n import t
        await ctx.bot.send_message(int(arg), t(tl, "aid_dm", name=esc(data["me"]), n=fnum(data["n"], tl)))
    except Exception:
        pass
    out = await here_panel(ctx, "")
    out.alert = ctx.t("aid_ok", name=data["name"], n=data["n"])
    return out


async def _user_lang(uid: int) -> str:
    from service_player import user_lang
    return (await user_lang(uid)) or "en"


@action("trc")
async def trace_do(ctx, arg):
    r, extra = await leave_trace(ctx.uid, arg)
    if r != "ok":
        return Out(alert=ctx.t("trc_e_" + r, n=extra or 0))
    out = await here_panel(ctx, "")
    out.alert = ctx.t("trc_ok", icon=MARK_ICON[arg])
    return out


# ---- bounties -----------------------------------------------------------------------------------------------------------------------------
@action("bty")
async def bounty_panel(ctx, arg):
    L = ctx.lang
    st = await game_settings()
    board = await bounty_board(5)
    lines = [head(ctx, "ttl_bty") + "<i>" + pick(ctx.lang, "epi_bty") + "</i>\n\n", ctx.t("bty_body", fee=fnum(round(float(st["bounty_fee"]) * 100), L), lvl=fnum(st["bounty_min_level"], L),
                                         hrs=fnum(st["bounty_hours"], L))]
    if board:
        for i, b in enumerate(board):
            lines.append(f"🎯 {esc(b['name'])} ({ctx.t('lbl_level')} {fnum(b['level'], L)}) — {fnum(b['amount'], L)} 🪙")
    else:
        lines.append(ctx.t("bty_none"))
    return Out("\n".join(lines), [[(ctx.t("b_bty_new"), "btn", "")], nav(ctx, ("wrd", ""))])


@action("btn")
async def bounty_ask(ctx, arg):
    await col("inputs").update_one({"user_id": ctx.uid}, {"$set": {"kind": "bounty_name", "at": int(time.time())}}, upsert=True)
    return Out(head(ctx, "ttl_bty") + ctx.t("bty_ask"), [nav(ctx, ("bty", ""))])


@input_handler("bounty_name")
async def bounty_name_input(ctx, text):
    tgt = await find_by_name(text)
    if not tgt or tgt["user_id"] == ctx.uid:
        return Out(ctx.t("bty_nofind"), [nav(ctx, ("bty", ""))])
    st = await game_settings()
    amts = [int(st["bounty_min"]) * m for m in (1, 4, 10, 40)]
    rows = [[(f"{fnum(a, ctx.lang)} 🪙", "btp", f"{tgt['user_id']}.{a}") for a in amts[:2]], [(f"{fnum(a, ctx.lang)} 🪙", "btp", f"{tgt['user_id']}.{a}") for a in amts[2:]]]
    return Out(ctx.t("bty_pick", name=esc(tgt["name"]), lvl=fnum(tgt["level"], ctx.lang), total=fnum(await bounty_total(tgt["user_id"]), ctx.lang)),
               rows + [nav(ctx, ("bty", ""))])


@action("btp")
async def bounty_do(ctx, arg):
    uid_s, _, amt_s = arg.partition(".")
    if not (uid_s.isdigit() and amt_s.isdigit()):
        return Out()
    r, extra = await bounty_place(ctx.uid, int(uid_s), int(amt_s))
    if r != "ok":
        return Out(alert=ctx.t("bty_e_" + r, n=fnum(extra or 0, ctx.lang)))
    out = await bounty_panel(ctx, "")
    out.alert = ctx.t("bty_ok", name=extra)
    return out


# ---- season ----------------------------------------------------------------------------------------------------------------------------------
@action("ssn")
async def season_panel(ctx, arg):
    L = ctx.lang
    st = await game_settings()
    ws, _ = await get_world()
    s = ws["season"]
    mine = await col("season_scores").find_one({"_id": f"{s['id']}:{ctx.uid}"}) or {}
    my_pts = int(mine.get("pts", 0))
    rank = (await col("season_scores").count_documents({"season": s["id"], "pts": {"$gt": my_pts}}) + 1) if my_pts else 0
    top = await season_top(s["id"], 10)
    pvp = await col("characters").find({}, {"name": 1, "rating": 1}).sort("rating", -1).limit(3).to_list(3)
    ch = await get_char(ctx.uid)
    lines = [head(ctx, "ttl_ssn") + "<i>" + pick(ctx.lang, "epi_ssn") + "</i>\n\n", ctx.t("ssn_body", n=fnum(s["id"], L), d=fnum(max(0, (s["end"] - int(time.time())) // 86400), L),
                                         pts=fnum(my_pts, L), rank=(fnum(rank, L) if rank else "—"), rating=fnum(ch["rating"], L),
                                         k=fnum(round(float(st["season_soft_reset"]) * 100), L)), ctx.t("ssn_top")]
    medals = ["🥇", "🥈", "🥉"] + [f"{i}." for i in range(4, 11)]
    for i, r in enumerate(top):
        lines.append(f"{medals[i]} {esc(r.get('name', '?'))} — {fnum(r['pts'], L)}")
    if not top:
        lines.append(ctx.t("empty"))
    lines.append(ctx.t("ssn_pvp"))
    for i, r in enumerate(pvp):
        lines.append(f"{medals[i]} {esc(r['name'])} — {fnum(r['rating'], L)}")
    return Out("\n".join(lines), [[(ctx.t("m_rnk"), "rnk", "")], nav(ctx, ("wrd", ""))])


# ---- craft ---------------------------------------------------------------------------------------------------------------------------------------
def _count_fit(req: dict, items: dict) -> int:
    return sum(q for i, q in items.items() if q > 0 and i in ALL and _fits(ALL[i], req))


def _req_lines(ctx, inputs: list, items: dict) -> list:
    L = ctx.lang
    out = []
    for req in inputs:
        have = _count_fit(req, items)
        rar = RARITIES[req.get("t", 0)]
        out.append(f"{'✅' if have >= req['n'] else '▫️'} {ctx.t('grp_' + req.get('g', 'any'))} ×{fnum(req['n'], L)} "
                   f"({RARITY_ICON[rar]}+) — {fnum(have, L)}")
    return out


@action("crf")
async def craft_hub(ctx, arg):
    rows = [[(ctx.t("crf_pot"), "crp", ""), (ctx.t("crf_key"), "crk", "0")],
            [(ctx.t("crf_tmp"), "crv", ""), (ctx.t("crf_evo"), "evo", "")],
            [(ctx.t("m_eqp"), "eqp", ""), (ctx.t("b_forge"), "frg", "")], nav(ctx)]
    return Out(head(ctx, "ttl_crf") + "<i>" + pick(ctx.lang, "epi_crf") + "</i>\n\n" + ctx.t("crf_body"), rows)


def _recipe_buttons(ctx, items: dict, recs: list):
    rows = []
    for r in recs:
        ok = plan_inputs(r["in"], items, ALL) is not None
        label = f"{'✅' if ok else '▫️'} {nm(r['out'], ctx.lang)}".replace("<", "").replace(">", "")
        rows.append([(label, "crw", r["id"])])
    return rows


@action("crp")
async def craft_potions(ctx, arg):
    ch = await get_char(ctx.uid)
    inv = await inv_get(ctx.uid)
    rows = _recipe_buttons(ctx, inv["items"], recipes_for(ch, "potion"))
    return Out(head(ctx, "ttl_crf") + ctx.t("crf_pot_body"), rows + [nav(ctx, ("crf", ""))])


@action("crk")
async def craft_keys(ctx, arg):
    ch = await get_char(ctx.uid)
    inv = await inv_get(ctx.uid)
    recs = recipes_for(ch, "key")
    pages = max(1, -(-len(recs) // PER_PAGE))
    page = max(0, min(int(arg or 0), pages - 1))
    rows = _recipe_buttons(ctx, inv["items"], recs[page * PER_PAGE:(page + 1) * PER_PAGE])
    pg = []
    if page > 0:
        pg.append(("◀️", "crk", str(page - 1), False, "none"))
    if page < pages - 1:
        pg.append(("▶️", "crk", str(page + 1), False, "none"))
    if pg:
        rows.append(pg)
    return Out(head(ctx, "ttl_crf") + ctx.t("crf_key_body"), rows + [nav(ctx, ("crf", ""))])


@action("crw")
async def craft_view(ctx, arg):
    r = RECIPE_BY_ID.get(arg)
    if not r:
        return await craft_hub(ctx, "")
    st = await game_settings()
    inv = await inv_get(ctx.uid)
    ok = plan_inputs(r["in"], inv["items"], ALL) is not None
    text = (head(ctx, "ttl_crf") + item_card(ctx, r["out"]) + "\n\n" + ctx.t("crf_needs") + "\n" +
            "\n".join(_req_lines(ctx, r["in"], inv["items"])) + f"\n🪙 {fnum(scaled_coins(r, st), ctx.lang)}")
    back = ("crp", "") if r["type"] == "potion" else ("crk", "0")
    rows = [[(ctx.t("b_craft"), "crd", arg)]] if ok else []
    return Out(text, rows + [nav(ctx, back)])


@action("crd")
async def craft_do(ctx, arg):
    res, data = await craft(ctx.uid, arg)
    if res != "ok":
        return Out(alert=ctx.t("crf_e_" + res, n=fnum(data or 0, ctx.lang)))
    out = await craft_view(ctx, arg)
    out.alert = ctx.t("crf_ok", item=nm(data, ctx.lang).replace("<b>", "").replace("</b>", ""))
    return out


@action("crv")
async def temper_view(ctx, arg):
    ch = await get_char(ctx.uid)
    st = await game_settings()
    L = ctx.lang
    aid = ch.get("armor_id")
    if not aid:
        return Out(head(ctx, "ttl_crf") + ctx.t("tmp_none"), [nav(ctx, ("crf", ""))])
    plus = (ch.get("armor_plus") or {}).get(aid, 0)
    if plus >= int(st["temper_max"]):
        return Out(head(ctx, "ttl_crf") + ctx.t("tmp_max", item=nm(aid, L), plus=fnum(plus, L)), [nav(ctx, ("crf", ""))])
    r = temper_recipe(plus, ALL[aid])
    inv = await inv_get(ctx.uid)
    text = (head(ctx, "ttl_crf") + ctx.t("tmp_body", item=nm(aid, L), plus=fnum(plus, L), nxt=fnum(plus + 1, L), pct=fnum(round(float(st["temper_def_pct"]) * 100), L),
                                         chance=fnum(r["chance"], L)) + "\n" + "\n".join(_req_lines(ctx, r["in"], inv["items"])) + f"\n🪙 {fnum(scaled_coins(r, st), L)}")
    return Out(text, [[(ctx.t("b_temper"), "crt", "")], nav(ctx, ("crf", ""))])


@action("crt")
async def temper_do(ctx, arg):
    res, data = await temper(ctx.uid)
    if res in ("ok", "fail"):
        out = await temper_view(ctx, "")
        out.alert = ctx.t("tmp_" + res, n=fnum(data, ctx.lang))
        return out
    return Out(alert=ctx.t("crf_e_" + res, n=fnum(data or 0, ctx.lang)))


# ---- evolution ----------------------------------------------------------------------------------------------------------------------------------
@action("evo")
async def evolution_panel(ctx, arg):
    ch = await get_char(ctx.uid)
    L = ctx.lang
    inv = await inv_get(ctx.uid)
    cur = RACES[ch["race"]]["evo"][evo_stage(ch)][0 if L == "fa" else 1]
    nxt = evo_next(ch)
    if not nxt:
        return Out(head(ctx, "ttl_evo") + "<i>" + pick(ctx.lang, "epi_evo") + "</i>\n\n" + ctx.t("evo_max", cur=cur), [nav(ctx, ("crf", ""))])
    stage, gate, need, tier = nxt
    req = {"cat": "evolution", "n": need, "t": tier}
    have = _count_fit(req, inv["items"])
    to = RACES[ch["race"]]["evo"][stage][0 if L == "fa" else 1]
    from config import GAME_DEFAULTS
    text = (head(ctx, "ttl_evo") + ctx.t("evo_body", cur=cur, to=to, lvl=fnum(gate, L), mine=fnum(ch["level"], L), need=fnum(need, L),
                                          rar=RARITY_ICON[RARITIES[tier]], have=fnum(have, L), pct=fnum(round(float((await game_settings())["evo_bonus_pct"]) * 100), L)))
    rows = [[(ctx.t("b_evo_go"), "evs", "")]] if ch["level"] >= gate and have >= need else []
    return Out(text, rows + [nav(ctx, ("crf", ""))])


@action("evs")
async def evolution_start(ctx, arg):
    res, data = await evo_start(ctx.uid, ctx.lang)
    if res != "ok":
        return Out(alert=ctx.t("evo_e_" + res, n=fnum(data or 0, ctx.lang)))
    from handlers_combat import battle_panel
    return await battle_panel(ctx, data, [])


# ---- gear hub: relics, cosmetics, pets --------------------------------------------------------------------------------------------------------------------
@action("eqp")
async def gear_hub(ctx, arg):
    ch = await get_char(ctx.uid)
    st = await game_settings()
    L = ctx.lang
    bn = player_bonus(ch, ALL, st)
    rel = [nm(i, L) for i in (ch.get("relics") or [])] or ["—"]
    cos = (ch.get("cosmetics") or {})
    pets = ch.get("pets") or []
    text = head(ctx, "ttl_eqp") + "<i>" + pick(ctx.lang, "epi_eqp") + "</i>\n\n" + ctx.t("eqp_body", relics=" · ".join(rel), slots=fnum(st["relic_slots"], L),
                                        cos=" ".join((ALL[cos[s]]["effect"]["icon"] if cos.get(s) else "▫️") for s in ("aura", "trail", "banner")),
                                        pet=pet_line(ctx, pets[0]) if pets else "—", bonus=bonus_line(ctx, bn))
    rows = [[(ctx.t("m_rlc"), "rlc", ""), (ctx.t("m_cos"), "cos", "")], [(ctx.t("m_pet"), "pet", "")], nav(ctx, ("crf", ""))]
    return Out(text, rows)


def bonus_line(ctx, bn: dict) -> str:
    L = ctx.lang
    parts = []
    for key, icon in (("dmg", "⚔️"), ("def", "🛡️"), ("crit", "🎯"), ("xp", "⭐"), ("drop", "🎁"), ("coin", "🪙"), ("patrol", "🧭"), ("regen", "💚")):
        if bn.get(key):
            parts.append(f"{icon} +{bn[key] * 100:.1f}%")
    return " ".join(parts) if parts else ctx.t("bonus_none")


@action("rlc")
async def relic_panel(ctx, arg):
    ch = await get_char(ctx.uid)
    inv = await inv_get(ctx.uid)
    L = ctx.lang
    st = await game_settings()
    from fmt import effect_text
    lines = [head(ctx, "ttl_rlc"), ctx.t("rlc_body", n=fnum(len(ch.get("relics") or []), L), slots=fnum(st["relic_slots"], L))]
    rows = []
    for idx, rid in enumerate(ch.get("relics") or []):
        lines.append(f"{idx + 1}. {nm(rid, L)}\n   {effect_text(ctx, ALL[rid])}")
        rows.append([(f"⬇️ {nm(rid, L)}".replace("<", "").replace(">", ""), "rlr", str(idx))])
    bag = [i for i, q in inv["items"].items() if q > 0 and (ALL.get(i, {}).get("effect") or {}).get("type") == "relic"]
    bag.sort(key=lambda i: -RARITIES.index(ALL[i]["rarity"]))
    for i in bag[:6]:
        rows.append([(f"⬆️ {nm(i, L)}".replace("<", "").replace(">", ""), "rla", i)])
    return Out("\n".join(lines), rows + [nav(ctx, ("eqp", ""))])


@action("rla")
async def relic_attune_cb(ctx, arg):
    r = await relic_attune(ctx.uid, arg)
    if r != "ok":
        return Out(alert=ctx.t("rlc_e_" + r))
    return await relic_panel(ctx, "")


@action("rlr")
async def relic_release_cb(ctx, arg):
    r = await relic_release(ctx.uid, int(arg or 0))
    if r != "ok":
        return Out(alert=ctx.t("rlc_e_" + r))
    return await relic_panel(ctx, "")


@action("cos")
async def cosmetic_panel(ctx, arg):
    ch = await get_char(ctx.uid)
    inv = await inv_get(ctx.uid)
    L = ctx.lang
    from data_crafting import fame
    cos = ch.get("cosmetics") or {}
    lines = [head(ctx, "ttl_cos"), ctx.t("cos_body", fame=fnum(fame(ch, ALL), L), name=esc(tagged_name(ch, ALL)))]
    rows = []
    for s in ("aura", "trail", "banner"):
        if cos.get(s):
            lines.append(f"{ctx.t('cos_slot_' + s)}: {nm(cos[s], L)}")
            rows.append([(f"⬇️ {ctx.t('cos_slot_' + s)}", "cor", s)])
    bag = [i for i, q in inv["items"].items() if q > 0 and (ALL.get(i, {}).get("effect") or {}).get("type") == "cosmetic"]
    bag.sort(key=lambda i: -RARITIES.index(ALL[i]["rarity"]))
    for i in bag[:6]:
        rows.append([(f"{ALL[i]['effect']['icon']} {nm(i, L)}".replace("<", "").replace(">", ""), "cow", i)])
    return Out("\n".join(lines), rows + [nav(ctx, ("eqp", ""))])


@action("cow")
async def cosmetic_wear_cb(ctx, arg):
    r = await cosmetic_wear(ctx.uid, arg)
    if r not in ("ok",):
        return Out(alert=ctx.t("cos_e_" + r))
    return await cosmetic_panel(ctx, "")


@action("cor")
async def cosmetic_remove_cb(ctx, arg):
    r = await cosmetic_remove(ctx.uid, arg)
    if r != "ok":
        return Out(alert=ctx.t("cos_e_" + r))
    return await cosmetic_panel(ctx, "")


@action("pet")
async def pet_panel(ctx, arg):
    ch = await get_char(ctx.uid)
    L = ctx.lang
    pets = ch.get("pets") or []
    lines = [head(ctx, "ttl_pet"), ctx.t("pet_body")]
    rows = []
    for idx, p in enumerate(pets):
        lines.append(("✅ " if idx == 0 else f"{idx}. ") + pet_line(ctx, p))
        if idx:
            rows.append([(f"🐾 {PETS[p['sp'] % len(PETS)][0 if L != 'fa' else 1]} ★{p['tier'] + 1}", "pea", str(idx))])
    if not pets:
        lines.append(ctx.t("pet_none"))
    return Out("\n".join(lines), rows[:8] + [nav(ctx, ("eqp", ""))])


@action("pea")
async def pet_activate_cb(ctx, arg):
    r = await pet_activate(ctx.uid, int(arg or 0))
    if r != "ok":
        return Out(alert=ctx.t("pet_e_" + r))
    return await pet_panel(ctx, "")


# ---- broadcast helpers (used by the scheduler) ---------------------------------------------------------------------------------------------------------------
def boss_kb(sid: str, mode: str = "fa"):
    return InlineKeyboardMarkup(inline_keyboard=[[make_button("⚔️ " + gl(mode, "حمله", "Attack"), make_cb("bh", sid, 0), "bh")]])


async def _send_groups(bot, text_fn, kb=None, limit: int = 300, want_ids: bool = False):
    ids = {}
    for g in await broadcast_groups(limit):
        try:
            mode = glang(g)
            msg = await bot.send_message(g["chat_id"], both(mode, text_fn), reply_markup=kb(mode) if callable(kb) else kb)
            ids[str(g["chat_id"])] = (msg.message_id, mode)
        except TelegramForbiddenError:
            await col("groups").update_one({"chat_id": g["chat_id"]}, {"$set": {"blocked": True}})
        except TelegramAPIError:
            log.warning("announce failed for %s", g["chat_id"])
        await asyncio.sleep(0.05)
    return ids


async def post_global_boss(bot, doc):
    st = await game_settings()
    ids = await _send_groups(bot, lambda L: boss_text(L, doc), (lambda m, _s=doc["_id"]: boss_kb(_s, m)), int(st["boss_broadcast_cap"]))
    await col("boss_sessions").update_one({"_id": doc["_id"]}, {"$set": {"msgs": {k: v[0] for k, v in ids.items()}, "refresh_at": int(time.time())}})


async def _edit_all(bot, doc, text_fn, kb):
    langs = {str(g["chat_id"]): glang(g) for g in await broadcast_groups(1000)}
    for cid, mid in (doc.get("msgs") or {}).items():
        try:
            await bot.edit_message_text(both(langs.get(cid, "fa"), text_fn), chat_id=int(cid), message_id=int(mid), reply_markup=kb(langs.get(cid, "fa")) if callable(kb) else kb)
        except TelegramAPIError:
            pass
        await asyncio.sleep(0.05)


async def announce_boss_phase(bot, doc, phase_no):
    """A short extra message in every announced group when the boss enters a new phase."""
    from i18n import t
    if phase_no not in (2, 3):
        return
    await _send_groups(bot, lambda L: t(L, "boss_phase_alert_" + str(phase_no), boss=esc(doc["name_fa" if L == "fa" else "name_en"])), (lambda m, _s=doc["_id"]: boss_kb(_s, m)))


async def refresh_global_boss(bot, doc):
    await _edit_all(bot, doc, lambda L: boss_text(L, doc), (lambda m, _s=doc["_id"]: boss_kb(_s, m)))


async def end_global_boss(bot, doc, summary):
    from handlers_combat import _drops
    await _edit_all(bot, doc, lambda L: boss_text(L, doc, summary) + _drops(L, summary), None)


async def announce_event_start(bot, ev):
    from i18n import t
    await _send_groups(bot, lambda L: t(L, "ev_announce", ev=ev_name(L, ev["kind"]), desc=t(L, "ev_" + ev["kind"] + "_desc"), goal=fnum(ev["goal"], L),
                                        m=fnum(_mins(ev["end_at"] - time.time()), L)))


async def announce_event_end(bot, summary):
    from i18n import t
    ev, ok = summary["doc"], summary["ok"]
    nmap = {r["uid"]: r["name"] for r in summary["rows"]}

    def fn(L):
        top = ", ".join(esc(r["name"]) for r in summary["rows"][:3])
        return t(L, "ev_end_ok" if ok else "ev_end_fail", ev=ev_name(L, ev["kind"]), n=fnum(summary["n"], L), top=top or "—")
    await _send_groups(bot, fn)
    for r in summary["rows"][:400]:
        try:
            tl = await _user_lang(r["uid"])
            await bot.send_message(r["uid"], t(tl, "ev_dm", xp=fnum(r["xp"], tl), coins=fnum(r["coins"], tl)) + (("\n🎁 " + nm(r["prize"], tl)) if r["prize"] else ""))
        except Exception:
            pass
        await asyncio.sleep(0.05)


async def announce_territories(bot, changes):
    from i18n import t
    for c in changes[:12]:
        await _send_groups(bot, lambda L, c=c: t(L, "ter_announce", g=esc(c["guild_fa" if L == "fa" else "guild_en"]), loc=loc_name(c["loc"], L)))


async def announce_season(bot, summary):
    from i18n import t
    top = summary["top"][:3]

    def fn(L):
        return t(L, "ssn_announce", n=fnum(summary["season"], L), top=", ".join(esc(r.get("name", "?")) for r in top) or "—")
    await _send_groups(bot, fn)
    for uid, key, params in summary["dm"]:
        try:
            tl = await _user_lang(uid)
            await bot.send_message(uid, t(tl, key, **{k: fnum(v, tl) for k, v in params.items()}))
        except Exception:
            pass
        await asyncio.sleep(0.05)
