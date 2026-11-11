"""Panels: Soul Tower, Dispatch, Urahara's wheel, Gotei seat ranks, Inner World."""
import math
import time

from data_chars import CHAR_BY_ID, copies_to_level_star
from data_crafting import cosmetic_tag
from data_extras import INNER, MISSIONS, ROLE_NOTE, SEATS, WHEEL
from data_items import ALL
from data_weapons import RARITIES, RARITY_ICON
from fmt import nm
from i18n import bar, esc, fnum
from service_combat import active_pve
from service_economy import gacha_doc
from service_extras import (dispatch_active, dispatch_claim, dispatch_send, inner_choose, inner_state, seat_claim, seat_info,
                            tower_board, tower_info, tower_start, wheel_spin, wheel_state)
from service_player import get_char
from ui import Out, action, head, nav

PER = 6
ROLE_ICON = {"attacker": "⚔️", "caster": "🔮", "tank": "🛡️", "support": "💚"}


def _fa(ctx) -> int:
    return 0 if ctx.lang == "fa" else 1


def _dur(sec: int, L: str) -> str:
    sec = max(0, int(sec))
    h, m = sec // 3600, (sec % 3600) // 60
    if L == "fa":
        return (f"{fnum(h, L)} ساعت " if h else "") + f"{fnum(m, L)} دقیقه"
    return (f"{h}h " if h else "") + f"{m}m"


# ===================================================================================================
# Soul Tower
# ===================================================================================================
@action("twr")
async def tower(ctx, arg):
    if await active_pve(ctx.uid):
        from handlers_combat import resume_battle
        return await resume_battle(ctx)
    L = ctx.lang
    i = await tower_info(ctx.uid)
    body = ctx.t("tw_body", best=fnum(i["best"], L), wk=fnum(i["wk"], L), start=fnum(i["start"], L), cost=fnum(i["cost"], L),
                 left=fnum(i["left"], L), cap=fnum(i["cap"], L))
    rows = [[(ctx.t("b_tgo"), "twg", "")], [(ctx.t("b_tlb"), "twl", "")], nav(ctx)]
    return Out(head(ctx, "ttl_twr") + body, rows)


@action("twg")
async def tower_go(ctx, arg):
    status, doc = await tower_start(ctx.uid, ctx.lang)
    if status == "wait":
        return Out()
    if status != "ok":
        return Out(alert=ctx.t("tw_e_" + status))
    from handlers_combat import battle_panel
    return await battle_panel(ctx, doc, [])


@action("twl")
async def tower_lb(ctx, arg):
    L = ctx.lang
    top = await tower_board()
    medals = ["🥇", "🥈", "🥉"] + [f"{i}." for i in range(4, 11)]
    lines = [f"{medals[i]} {cosmetic_tag(x, ALL)} {esc(x['name'])} — {ctx.t('tw_floor_n', n=fnum(x['tower']['wk_best'], L))}" for i, x in enumerate(top)]
    return Out(head(ctx, "ttl_twr") + ctx.t("tw_lb") + "\n\n" + ("\n".join(lines) or ctx.t("empty")), [nav(ctx, ("twr", ""))])


# ===================================================================================================
# Dispatch
# ===================================================================================================
@action("dsp")
async def dispatch(ctx, arg):
    L, now = ctx.lang, int(time.time())
    from database import game_settings
    st = await game_settings()
    act = await dispatch_active(ctx.uid)
    lines, ready = [], 0
    for d in act:
        c, m = CHAR_BY_ID[d["cid"]], MISSIONS[d["mission"]]
        label = f"{ROLE_ICON[c['role']]} <b>{esc(c['name_fa' if L == 'fa' else 'name_en'])}</b> — {m['fa' if L == 'fa' else 'en']}"
        if d["end"] <= now:
            ready += 1
            lines.append(f"✅ {label}")
        else:
            lines.append(f"⏳ {label} ({_dur(d['end'] - now, L)})")
    roles = " · ".join(f"{ROLE_ICON[r]} {n[_fa(ctx)]}" for r, n in ROLE_NOTE.items())
    body = ctx.t("ds_body", roles=roles, used=fnum(len(act), L), slots=fnum(int(st["dispatch_slots"]), L))
    if lines:
        body += "\n\n" + "\n".join(lines)
    rows = []
    if ready:
        rows.append([(ctx.t("b_dclaim") + f" ({fnum(ready, L)})", "dsc", "")])
    rows.append([(ctx.t("b_dsend"), "dsm", "")])
    rows.append(nav(ctx))
    return Out(head(ctx, "ttl_dsp") + body, rows)


@action("dsm")
async def dispatch_pick(ctx, arg):
    L = ctx.lang
    mid, _, page = arg.partition(".")
    if mid not in MISSIONS:
        ch = await get_char(ctx.uid)
        rows = []
        for k, m in MISSIONS.items():
            ok = ch["level"] >= m["level"]
            lbl = f"{m['fa' if L == 'fa' else 'en']} — {ctx.t('ds_hours', h=fnum(m['hours'], L))}"
            rows.append([(lbl if ok else f"🔒 {lbl} ({fnum(m['level'], L)})", "dsm" if ok else "noop", k)])
        rows.append(nav(ctx, ("dsp", "")))
        return Out(head(ctx, "ttl_dsp") + ctx.t("ds_pick_m"), rows)
    g = await gacha_doc(ctx.uid)
    busy = {d["cid"] for d in await dispatch_active(ctx.uid)}
    owned = sorted([(c, n) for c, n in g["chars"].items() if c in CHAR_BY_ID and c not in busy],
                   key=lambda kv: (-RARITIES.index(CHAR_BY_ID[kv[0]]["rarity"]), kv[0]))
    if not owned:
        return Out(head(ctx, "ttl_dsp") + ctx.t("ds_nochars"), [nav(ctx, ("dsp", ""))])
    pages = max(1, math.ceil(len(owned) / PER))
    page = max(0, min(int(page or 0), pages - 1))
    rows = []
    for cid, copies in owned[page * PER:(page + 1) * PER]:
        c = CHAR_BY_ID[cid]
        lvl, star = copies_to_level_star(copies)
        rows.append([(f"{RARITY_ICON[c['rarity']]}{ROLE_ICON[c['role']]} {c['name_fa' if L == 'fa' else 'name_en']} Lv{lvl}{'★' * star}", "dss", f"{mid}.{cid}")])
    pg = []
    if page > 0:
        pg.append(("◀️", "dsm", f"{mid}.{page - 1}", False, "none"))
    if page < pages - 1:
        pg.append(("▶️", "dsm", f"{mid}.{page + 1}", False, "none"))
    if pg:
        rows.append(pg)
    rows.append(nav(ctx, ("dsm", "")))
    return Out(head(ctx, "ttl_dsp") + ctx.t("ds_pick_c"), rows)


@action("dss")
async def dispatch_do(ctx, arg):
    mid, _, cid = arg.partition(".")
    r = await dispatch_send(ctx.uid, mid, cid)
    if r != "ok":
        return Out(alert=ctx.t("ds_e_" + r))
    out = await dispatch(ctx, "")
    out.alert = ctx.t("ds_sent")
    return out


@action("dsc")
async def dispatch_collect(ctx, arg):
    L = ctx.lang
    res = await dispatch_claim(ctx.uid)
    if not res:
        return Out(alert=ctx.t("ds_e_none"))
    lines = []
    for r in res:
        c = CHAR_BY_ID[r["cid"]]
        extra = (" · " + nm(r["item"], L)) if r["item"] else ""
        extra += (" · ⚡" + fnum(r["energy"], L)) if r["energy"] else ""
        lines.append(f"{ROLE_ICON[r['role']]} <b>{esc(c['name_fa' if L == 'fa' else 'name_en'])}</b>: +{fnum(r['coins'], L)} 🪙 · +{fnum(r['xp'], L)} XP{extra}")
    return Out(head(ctx, "ttl_dsp") + ctx.t("ds_done") + "\n\n" + "\n".join(lines), [[(ctx.t("b_dsend"), "dsm", "")], nav(ctx, ("dsp", ""))])


# ===================================================================================================
# Urahara's wheel
# ===================================================================================================
@action("whl")
async def wheel(ctx, arg):
    L = ctx.lang
    s = await wheel_state(ctx.uid)
    prizes = " ".join(w[2] for w in WHEEL)
    body = ctx.t("wh_body", prizes=prizes, cost=fnum(s["cost"], L))
    if s["free"]:
        body += "\n\n" + ctx.t("wh_free")
        label = ctx.t("b_spin_free")
    elif s["extra"] > 0:
        body += "\n\n" + ctx.t("wh_extra", n=fnum(s["extra"], L), cost=fnum(s["cost"], L))
        label = ctx.t("b_spin_paid", cost=fnum(s["cost"], L))
    else:
        return Out(head(ctx, "ttl_whl") + body + "\n\n" + ctx.t("wh_none"), [nav(ctx)])
    return Out(head(ctx, "ttl_whl") + body, [[(label, "whs", "")], nav(ctx)])


@action("whs")
async def wheel_do(ctx, arg):
    L = ctx.lang
    status, r = await wheel_spin(ctx.uid)
    if status == "wait":
        return Out()
    if status != "ok":
        return Out(alert=ctx.t("wh_e_" + status))
    lines = [f"🎡 {r['icon']} <b>{r['fa'] if L == 'fa' else r['en']}</b>"]
    if r["coins"]:
        lines.append(f"+{fnum(r['coins'], L)} 🪙")
    if r["xp"]:
        lines.append(f"+{fnum(r['xp'], L)} XP")
    if r["energy"]:
        lines.append(f"+{fnum(r['energy'], L)} ⚡")
    if r["item"]:
        lines.append(nm(r["item"], L))
    s = await wheel_state(ctx.uid)
    rows = []
    if s["free"] or s["extra"] > 0:
        rows.append([(ctx.t("b_spin_free") if s["free"] else ctx.t("b_spin_paid", cost=fnum(s["cost"], L)), "whs", "")])
    rows.append(nav(ctx))
    return Out(head(ctx, "ttl_whl") + "\n".join(lines), rows)


# ===================================================================================================
# Gotei seat ranks
# ===================================================================================================
@action("sat")
async def seat(ctx, arg):
    L = ctx.lang
    i = await seat_info(ctx.uid)
    idx = i["idx"]
    name = SEATS[idx][2 + _fa(ctx)]
    icon = SEATS[idx][1]
    lines = [ctx.t("sat_now", icon=icon, name=name, pts=fnum(i["pts"], L))]
    if i["next"]:
        cur_need = SEATS[idx][0]
        lines.append(bar(i["pts"] - cur_need, i["next"][0] - cur_need) + " " + ctx.t("sat_next", icon=i["next"][1], name=i["next"][2 + _fa(ctx)],
                                                                                    n=fnum(i["next"][0] - i["pts"], L)))
    ladder = []
    for k, (need, ic, fa, en) in enumerate(SEATS):
        mark = "✅" if k <= idx else "▫️"
        ladder.append(f"{mark} {ic} {fa if L == 'fa' else en} — {fnum(need, L)}")
    rows = []
    if i["claimed"] < idx:
        rows.append([(ctx.t("b_sclaim"), "sac", "")])
    rows.append([(ctx.t("m_ssn"), "ssn", "")])
    rows.append(nav(ctx))
    return Out(head(ctx, "ttl_sat") + "\n".join(lines) + "\n\n" + "\n".join(ladder) + "\n\n" + ctx.t("sat_hint"), rows)


@action("sac")
async def seat_collect(ctx, arg):
    L = ctx.lang
    r = await seat_claim(ctx.uid)
    if not r:
        return Out(alert=ctx.t("sat_e_none"))
    text = ctx.t("sat_claimed", coins=fnum(r["coins"], L)) + "\n" + "\n".join(nm(i, L) for i in r["items"])
    return Out(head(ctx, "ttl_sat") + text, [nav(ctx, ("sat", ""))])


# ===================================================================================================
# Inner World
# ===================================================================================================
@action("inr")
async def inner(ctx, arg):
    L = ctx.lang
    s = await inner_state(ctx.uid)
    if s["scene"] is None:
        return Out(head(ctx, "ttl_inr") + ctx.t("inr_none", cap=fnum(s["cap"], L)), [nav(ctx)])
    ch = await get_char(ctx.uid)
    w = ALL.get(ch.get("weapon_id") or "") or {}
    wname = esc(w.get("name_fa" if L == "fa" else "name_en", ctx.t("inr_blade")))
    sc = INNER[s["scene"]]
    text = ctx.t("inr_intro", left=fnum(s["left"], L), cap=fnum(s["cap"], L)) + "\n\n<i>" + sc["t"][_fa(ctx)].format(w=wname) + "</i>"
    rows = [[(sc["a"][_fa(ctx)], "inc", f"{s['scene']}.a")], [(sc["b"][_fa(ctx)], "inc", f"{s['scene']}.b")], nav(ctx)]
    return Out(head(ctx, "ttl_inr") + text, rows)


@action("inc")
async def inner_pick(ctx, arg):
    L = ctx.lang
    sc_s, _, choice = arg.partition(".")
    if not sc_s.isdigit() or int(sc_s) >= len(INNER):
        return Out()
    status, r = await inner_choose(ctx.uid, int(sc_s), choice)
    if status == "wait":
        return Out()
    if status != "ok":
        return Out(alert=ctx.t("inr_e_" + status))
    ch = INNER[int(sc_s)][choice]
    lines = ["<i>" + ch[2 + _fa(ctx)] + "</i>", ""]
    if r["bond"]:
        lines.append(ctx.t("inr_bond", n=fnum(r["bond"], L)))
    if r["xp"]:
        lines.append(f"+{fnum(r['xp'], L)} XP")
    if r["buff"]:
        key, pct, minutes = r["buff"]
        lines.append(ctx.t("inr_buff", key=ctx.t("buff_" + key), pct=fnum(round(pct * 100), L), m=fnum(minutes, L)))
    s = await inner_state(ctx.uid)
    rows = [[(ctx.t("b_inr_again"), "inr", "")]] if s["scene"] is not None else []
    rows.append(nav(ctx))
    return Out(head(ctx, "ttl_inr") + "\n".join(lines), rows)
