"""Soul Tower, Dispatch and Gotei Seat panels.

The menu buttons 🗼 Soul Tower, 🧭 Dispatch and 🎖️ Gotei Seat (and the words «برج», «اعزام», «درجه») pointed at actions
that were never registered, so they did nothing. The game logic for all three already lived in service_extras
(tower_start / tower_settle, dispatch_send / dispatch_claim, seat_info / seat_claim) and their texts in locale_extras;
this module adds the screens and buttons on top of it.
"""
import time

from data_chars import CHAR_BY_ID
from data_extras import MISSIONS, RARITY_MULT, ROLE_NOTE, SEATS
from database import game_settings
from i18n import fnum
from service_economy import gacha_doc
from service_extras import (dispatch_active, dispatch_claim, dispatch_send, seat_claim, seat_info, tower_board, tower_info,
                            tower_start)
from service_player import get_char
from ui import Out, action, head, nav


def _T(ctx, fa, en):
    return fa if ctx.lang == "fa" else en


def _mins(sec: int, L: str) -> str:
    sec = max(0, int(sec))
    h, m = sec // 3600, (sec % 3600) // 60
    if L == "fa":
        return (f"{fnum(h, L)} ساعت و " if h else "") + f"{fnum(m, L)} دقیقه"
    return (f"{h}h " if h else "") + f"{m}m"


# ---- Soul Tower ------------------------------------------------------------------------------------------------------
@action("twr")
async def tower_panel(ctx, arg):
    info = await tower_info(ctx.uid)
    L = ctx.lang
    body = ctx.t("tw_body", best=fnum(info["best"], L), wk=fnum(info["wk"], L), start=fnum(info["start"], L),
                 cost=fnum(info["cost"], L), left=fnum(info["left"], L), cap=fnum(info["cap"], L))
    body += "\n\n" + _T(ctx, "🎁 هر ۵ طبقه (رکورد جدید): سکه و یک آیتم تضمینی · هر ۱۰ طبقه: یک یادگار تکامل هم.",
                        "🎁 Every 5th floor (new record): coins and a guaranteed item · every 10th: an evolution relic too.")
    rows = [[(_T(ctx, f"⚔️ صعود از طبقه‌ی {fnum(info['start'], L)}", f"⚔️ Climb from floor {info['start']}"), "twg", "")],
            [(_T(ctx, "🏅 برترین‌های هفته", "🏅 This week's best"), "twl", "")],
            nav(ctx)]
    return Out(head(ctx, "m_twr") + body, rows)


@action("twg")
async def tower_go(ctx, arg):
    status, doc = await tower_start(ctx.uid, ctx.lang)
    if status == "busy":
        return Out(alert=ctx.t("tw_e_busy"))
    if status == "energy":
        return Out(alert=ctx.t("tw_e_energy"))
    if status != "ok":
        return Out(alert="⏳")
    from handlers_combat import battle_panel
    return await battle_panel(ctx, doc)


@action("twl")
async def tower_leaders(ctx, arg):
    L = ctx.lang
    lines = [ctx.t("tw_lb"), ""]
    for i, d in enumerate(await tower_board(10), 1):
        lines.append(f"{fnum(i, L)}. {d.get('name', '?')} — {ctx.t('tw_floor_n', n=fnum(int((d.get('tower') or {}).get('wk_best', 0)), L))}")
    if len(lines) == 2:
        lines.append(_T(ctx, "هنوز کسی این هفته بالا نرفته.", "Nobody has climbed this week yet."))
    return Out(head(ctx, "m_twr") + "\n".join(lines), [nav(ctx, ("twr", ""))])


# ---- Dispatch -------------------------------------------------------------------------------------------------------
def _cname(ctx, cid):
    c = CHAR_BY_ID.get(cid) or {}
    return c.get("name_fa" if ctx.lang == "fa" else "name_en", cid)


@action("dsp")
async def dispatch_panel(ctx, arg):
    L = ctx.lang
    st = await game_settings()
    act = await dispatch_active(ctx.uid)
    roles = "، ".join(f"{k}: {v[0]}" for k, v in ROLE_NOTE.items()) if L == "fa" else ", ".join(f"{k}: {v[1]}" for k, v in ROLE_NOTE.items())
    lines = [ctx.t("ds_body", roles=roles, used=fnum(len(act), L), slots=fnum(int(st["dispatch_slots"]), L)), ""]
    now = int(time.time())
    ready = 0
    for d in act:
        m = MISSIONS.get(d["mission"], {})
        left = int(d["end"]) - now
        ready += left <= 0
        state = _T(ctx, "✅ آماده‌ی تحویل", "✅ ready") if left <= 0 else f"⏳ {_mins(left, L)}"
        lines.append(f"• {_cname(ctx, d['cid'])} → {m.get('fa' if L == 'fa' else 'en', d['mission'])} · {state}")
    rows = []
    if ready:
        rows.append([(_T(ctx, f"🎁 تحویل جایزه‌ها ({fnum(ready, L)})", f"🎁 Collect rewards ({ready})"), "dsc", "")])
    if len(act) < int(st["dispatch_slots"]):
        rows.append([(_T(ctx, "🧭 اعزام جدید", "🧭 New dispatch"), "dsm", "")])
    rows.append(nav(ctx))
    return Out(head(ctx, "m_dsp") + "\n".join(lines), rows)


@action("dsm")
async def dispatch_pick_mission(ctx, arg):
    L = ctx.lang
    ch = await get_char(ctx.uid)
    lvl = int(ch["level"])
    rows = []
    for mid, m in sorted(MISSIONS.items(), key=lambda kv: (kv[1]["level"], kv[1]["hours"])):
        if m["level"] > lvl:
            continue
        rows.append([(f"{m['fa' if L == 'fa' else 'en']} · {ctx.t('ds_hours', h=fnum(m['hours'], L))} · Lv.{fnum(m['level'], L)}", "dss", mid)])
    rows = rows[-12:]  # the highest twelve the player can take
    rows.append(nav(ctx, ("dsp", "")))
    return Out(head(ctx, "m_dsp") + ctx.t("ds_pick_m"), rows)


@action("dss")
async def dispatch_pick_char(ctx, arg):
    """arg: '<mission>' to choose a character, '<mission>.<character>' to send."""
    mid, _, cid = (arg or "").partition(".")
    if mid not in MISSIONS:
        return Out(alert=ctx.t("ds_e_bad"))
    if cid:
        r = await dispatch_send(ctx.uid, mid, cid)
        if r != "ok":
            return Out(alert=ctx.t("ds_e_" + r))
        out = await dispatch_panel(ctx, "")
        out.alert = ctx.t("ds_sent")
        return out
    g = await gacha_doc(ctx.uid)
    busy = {d["cid"] for d in await dispatch_active(ctx.uid)}
    owned = [c for c in (g.get("chars") or {}) if c in CHAR_BY_ID and c not in busy]
    if not owned:
        return Out(head(ctx, "m_dsp") + ctx.t("ds_nochars"), [[(_T(ctx, "🎴 احضار", "🎴 Summon"), "gch", "")], nav(ctx, ("dsp", ""))])
    owned.sort(key=lambda c: -RARITY_MULT.get(CHAR_BY_ID[c]["rarity"], 1.0))
    rows = [[(f"{_cname(ctx, c)} · {CHAR_BY_ID[c]['role']}", "dss", f"{mid}.{c}")] for c in owned[:12]]
    rows.append(nav(ctx, ("dsm", "")))
    return Out(head(ctx, "m_dsp") + ctx.t("ds_pick_c"), rows)


@action("dsc")
async def dispatch_collect(ctx, arg):
    L = ctx.lang
    res = await dispatch_claim(ctx.uid)
    if not res:
        return Out(alert=ctx.t("ds_e_none"))
    from data_items import iname
    lines = [ctx.t("ds_done")]
    for r in res:
        extra = (f" · {iname(r['item'], L)}" if r.get("item") else "") + (f" · ⚡+{fnum(r['energy'], L)}" if r.get("energy") else "")
        lines.append(f"• {_cname(ctx, r['cid'])}: +{fnum(r['coins'], L)} 🪙 · +{fnum(r['xp'], L)} XP{extra}")
    out = await dispatch_panel(ctx, "")
    out.text = "\n".join(lines) + "\n\n" + out.text
    return out


# ---- Gotei seat -----------------------------------------------------------------------------------------------------
@action("sat")
async def seat_panel(ctx, arg):
    L = ctx.lang
    info = await seat_info(ctx.uid)
    _need, icon, fa, en = SEATS[info["idx"]]
    lines = [ctx.t("sat_now", icon=icon, name=fa if L == "fa" else en, pts=fnum(info["pts"], L))]
    if info["next"]:
        need, nicon, nfa, nen = info["next"]
        lines.append(ctx.t("sat_next", icon=nicon, name=nfa if L == "fa" else nen, n=fnum(max(0, need - info["pts"]), L)))
    lines += ["", ctx.t("sat_hint"), ""]
    for i, (need, sicon, sfa, sen) in enumerate(SEATS):
        mark = "✅" if i <= info["idx"] else "▫️"
        lines.append(f"{mark} {sicon} {sfa if L == 'fa' else sen} · {fnum(need, L)}")
    rows = []
    if info["idx"] > info["claimed"]:
        rows.append([(_T(ctx, "🎁 دریافت جایزه‌ی درجه", "🎁 Claim seat reward"), "sac", "")])
    rows.append(nav(ctx))
    return Out(head(ctx, "m_sat") + "\n".join(lines), rows)


@action("sac")
async def seat_collect(ctx, arg):
    r = await seat_claim(ctx.uid)
    if not r:
        return Out(alert=ctx.t("sat_e_none"))
    from data_items import iname
    out = await seat_panel(ctx, "")
    out.text = (ctx.t("sat_claimed", coins=fnum(r["coins"], ctx.lang)) + " " + "، ".join(iname(i, ctx.lang) for i in r["items"])
                + "\n\n" + out.text)
    return out
