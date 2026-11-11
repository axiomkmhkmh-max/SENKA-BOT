"""PvE battles, dungeons, group duels (PvP) and world-boss buttons."""
import random

from aiogram.exceptions import TelegramBadRequest

from data_items import ALL
from data_misc import FORMS, KIDO_NAMES
from data_races import DIFFICULTY, DIFF_FA, DUNGEONS
from database import col
import engine as E
from fmt import nm
from i18n import esc, fnum
from render import battle_text, both, boss_text, events_text
from service_combat import (active_pve, duel_accept, duel_challenge, duel_decline, pve_act, pve_start, pvp_act,
                            rank_letter, start_dungeon)
from service_economy import inv_get, inv_remove
from service_player import get_char
from service_world import active_boss, boss_hit, group_doc, settle_boss
from ui import Out, action, chunk, head, markup, nav


def _act_rows(ctx, f, sid, pub=False, pot=False):
    L = ctx.lang
    form1, form2 = FORMS[f["race"]]
    i = 0 if L == "fa" else 1
    mk = lambda label, act: (label, "pa" if pub else "ba", f"{sid}.{act}", pub)
    rows = [[mk(ctx.t("a_atk"), "atk")]]
    if E.can(f, "hvy"):
        rows[0].append(mk(ctx.t("a_hvy"), "hvy"))
    r2 = []
    if E.can(f, "kd"):
        r2.append(mk(ctx.t("a_kd", n=E.best_kido(f, "had"), spell=KIDO_NAMES.get(("had", E.best_kido(f, "had")), "")), "kd"))
    if E.can(f, "bk"):
        r2.append(mk(ctx.t("a_bk", n=E.best_kido(f, "bak"), spell=KIDO_NAMES.get(("bak", E.best_kido(f, "bak")), "")), "bk"))
    if r2:
        rows.append(r2)
    r3 = [mk(ctx.t("a_df"), "df")]
    if E.can(f, "f1"):
        r3.append(mk("✨ " + form1[i], "f1"))
    if E.can(f, "f2"):
        r3.append(mk("🌟 " + form2[i], "f2"))
    rows.append(r3)
    if pot:
        rows.append([mk(ctx.t("a_pot"), "pot")])
    return rows


async def _has_potion(uid):
    inv = await inv_get(uid)
    best = None
    for i, q in inv["items"].items():
        e = (ALL.get(i) or {}).get("effect")
        if q > 0 and e and e["type"] == "hp" and (best is None or e["pct"] > ALL[best]["effect"]["pct"]):
            best = i
    return best


async def battle_panel(ctx, doc, events=None):
    st = doc["state"]
    title = head(ctx, "ttl_bt")
    d = doc.get("dungeon")
    if d:
        title += ctx.t("dg_stage", n=fnum(d["stage"], ctx.lang), t=fnum(d["total"], ctx.lang), diff=ctx.t("diff_" + d["diff"])) + "\n"
    text = battle_text(ctx.lang, st, events, title)
    pot = await _has_potion(ctx.uid)
    return Out(text, _act_rows(ctx, st["a"], doc["sid"], pot=bool(pot)) + [[(ctx.t("b_home"), "home", "")]])


async def resume_battle(ctx):
    doc = await active_pve(ctx.uid)
    if not doc:
        return Out(ctx.t("bt_none"), [nav(ctx)])
    return await battle_panel(ctx, doc, [])


async def start_pve_panel(ctx, scale=1.0):
    doc = await active_pve(ctx.uid) or await pve_start(ctx.uid, ctx.lang)
    return await battle_panel(ctx, doc, [])


@action("bt")
async def battle_menu(ctx, arg):
    doc = await active_pve(ctx.uid)
    if doc:
        return await battle_panel(ctx, doc, [])
    rows = [[(ctx.t("b_fight"), "bs", ""), (ctx.t("m_dgn"), "dgn", "")], nav(ctx)]
    return Out(head(ctx, "ttl_bt") + ctx.t("bt_body"), rows)


@action("bs")
async def battle_start(ctx, arg):
    from service_combat import pve_start
    from service_player import energy_now
    from database import try_cooldown
    if not await active_pve(ctx.uid):
        wait = await try_cooldown(f"battle:{ctx.uid}", 8)
        if wait:
            return Out(alert=ctx.t("wait_s", n=wait))
    return await start_pve_panel(ctx)


async def _pve_result(ctx, doc, ev, o):
    L = ctx.lang
    log = events_text(L, ev)
    if not o["win"]:
        text = battle_text(L, doc["state"], ev, head(ctx, "ttl_bt")) + "\n\n" + ctx.t("bt_lose")
        return Out(text, [[(ctx.t("b_again"), "bs", "")], nav(ctx)])
    lines = [battle_text(L, doc["state"], ev, head(ctx, "ttl_bt")), "", ctx.t("bt_win", xp=fnum(o["xp"], L), coins=fnum(o["coins"], L))]
    if o["levels"]:
        lines.append(ctx.t("bt_levelup", n=fnum(o["levels"], L)))
    if o["drop"]:
        lines.append(ctx.t("bt_drop", item=nm(o["drop"], L)))
    rows = []
    if o["next"]:
        lines.append(ctx.t("dg_next"))
        rows.append([(ctx.t("b_next_stage"), "bn", o["next"])])
    elif o["dungeon_done"]:
        lines.append(ctx.t("dg_done"))
    else:
        rows.append([(ctx.t("b_again"), "bs", "")])
    rows.append(nav(ctx))
    return Out("\n".join(lines), rows)


@action("bn")
async def next_stage(ctx, arg):
    doc = await col("battles").find_one({"sid": arg, "user_id": ctx.uid, "status": "active"})
    if not doc:
        return Out(alert=ctx.t("bt_none"))
    return await battle_panel(ctx, doc, [])


@action("ba")
async def battle_action(ctx, arg):
    sid, _, act = arg.partition(".")
    potion = None
    if act == "pot":
        potion = await _has_potion(ctx.uid)
        if not potion or not await inv_remove(ctx.uid, potion, 1):
            return Out(alert=ctx.t("bt_no_potion"))
        potion = {"type": "hp", "pct": ALL[potion]["effect"]["pct"], "id": potion}
    status, doc, data = await pve_act(ctx.uid, sid, act, potion)
    if status != "ok":
        if potion:
            from service_economy import inv_add
            await inv_add(ctx.uid, potion["id"], 1, force=True)
        return Out(alert=ctx.t("bt_" + status))
    ev, outcome = data
    if outcome:
        return await _pve_result(ctx, doc, ev, outcome)
    return await battle_panel(ctx, doc, ev)


# ---- dungeons ---------------------------------------------------------------------------------
@action("dgn")
async def dungeons(ctx, arg):
    ch = await get_char(ctx.uid)
    L = ctx.lang
    rows = []
    for did, d in DUNGEONS.items():
        ok = ch["level"] >= d["level"]
        rows.append([(("🕳️ " if ok else "🔒 ") + f"{d['fa' if L == 'fa' else 'en']} ({fnum(d['level'], L)})", "dgd" if ok else "noop", did)])
    rows.append(nav(ctx))
    return Out(head(ctx, "ttl_dgn") + ctx.t("dgn_body"), rows)


@action("dgd")
async def dungeon_diff(ctx, arg):
    L = ctx.lang
    d = DUNGEONS.get(arg)
    if not d:
        return Out()
    rows = [[(ctx.t("diff_" + k) + (" 🔑" if k != "normal" else ""), "dgs", f"{arg}.{k}")] for k in DIFFICULTY]
    rows.append(nav(ctx, ("dgn", "")))
    return Out(head(ctx, "ttl_dgn") + f"<b>{d['fa' if L == 'fa' else 'en']}</b>\n" + ctx.t("dgn_pick", n=fnum(d["stages"], L)), rows)


@action("dgs")
async def dungeon_start(ctx, arg):
    did, _, diff = arg.partition(".")
    if did not in DUNGEONS or diff not in DIFFICULTY:
        return Out()
    status, doc = await start_dungeon(ctx.uid, ctx.lang, did, diff)
    if status != "ok":
        return Out(alert=ctx.t("dgn_e_" + status))
    return await battle_panel(ctx, doc, [])


# ---- duels ---------------------------------------------------------------------------------------
async def challenge(ctx, target, ranked: bool):
    """Called from the text router when someone replies 'duel' to another player."""
    status, extra = await duel_challenge(ctx.chat_id, ctx.uid, target.id, ranked)
    if status != "ok":
        return Out(ctx.t("duel_e_" + status, n=extra or ""))
    d = extra
    g = await group_doc(ctx.chat_id)
    text = both(g.get("lang", "both"), lambda L: __import__("i18n").t(L, "duel_invite", a=esc(d["a_name"]), b=esc(d["b_name"]),
                mode=__import__("i18n").t(L, "duel_ranked" if ranked else "duel_friendly")))
    rows = [[(ctx.t("b_accept"), "dua", d["sid"], False), (ctx.t("b_decline"), "dud", d["sid"], False)]]
    # accept/decline are bound to the challenged player
    from security import make_cb
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Accept / قبول", callback_data=make_cb("dua", d["sid"], d["b_uid"])),
                                                InlineKeyboardButton(text="❌ Decline / رد", callback_data=make_cb("dud", d["sid"], d["b_uid"]))]])
    return Out(text, new=True), kb


async def _pvp_panel(chat_lang, ctx, doc, events, final=None):
    st = doc["state"]
    cur = st[st["cur"]]["name"]

    def render(L):
        from i18n import t
        txt = battle_text(L, st, events, f"⚔️ <b>{t(L, 'duel_title')}</b> ({t(L, 'duel_ranked' if doc['ranked'] else 'duel_friendly')})")
        if final is not None:
            txt += "\n\n" + final(L)
        else:
            txt += "\n\n" + t(L, "duel_turn", name=esc(cur))
        return txt
    text = both(chat_lang, render)
    rows = []
    if final is None:
        rows = _act_rows(ctx, st[st["cur"]], doc["sid"], pub=True)
    return text, markup(ctx, rows)


@action("dua")
async def duel_accept_cb(ctx, arg):
    doc = await duel_accept(arg, ctx.uid)
    if not doc:
        return Out(alert=ctx.t("duel_gone"))
    g = await group_doc(doc["chat_id"])
    text, kb = await _pvp_panel(g.get("lang", "both"), ctx, doc, [])
    await _edit(ctx, text, kb)
    return Out()


@action("dud")
async def duel_decline_cb(ctx, arg):
    if await duel_decline(arg, ctx.uid):
        await _edit(ctx, ctx.t("duel_declined"), None)
    return Out()


def _final(ctx, doc, outcome):
    from i18n import t

    def fn(L):
        if outcome is None or outcome.get("draw"):
            return t(L, "duel_draw")
        st = doc["state"]
        wname = doc["a_name"] if outcome["winner"] == doc["a_uid"] else doc["b_name"]
        lines = [t(L, "duel_win", name=esc(wname))]
        for uid, (rt, delta) in outcome["rating"].items():
            nm_ = doc["a_name"] if uid == doc["a_uid"] else doc["b_name"]
            lines.append(f"{esc(nm_)}: {rank_letter(rt)} {fnum(rt, L)} ({'+' if delta > 0 else ''}{fnum(delta, L)})")
        if outcome.get("note"):
            lines.append(t(L, "duel_note_" + outcome["note"]))
        return "\n".join(lines)
    return fn


@action("pa")
async def pvp_action(ctx, arg):
    sid, _, act = arg.partition(".")
    status, doc, data = await pvp_act(ctx.uid, sid, act)
    if status != "ok":
        return Out(alert=ctx.t("bt_" + status if status != "notplayer" else "duel_notplayer"))
    ev, outcome = data
    g = await group_doc(doc["chat_id"])
    final = _final(ctx, doc, outcome) if doc["state"]["done"] else None
    text, kb = await _pvp_panel(g.get("lang", "both"), ctx, doc, ev, final)
    await _edit(ctx, text, kb)
    return Out()


async def _edit(ctx, text, kb):
    try:
        await ctx.message.edit_text(text, reply_markup=kb)
    except (TelegramBadRequest, AttributeError) as e:
        if "not modified" not in str(e):
            await ctx.bot.send_message(ctx.chat_id, text, reply_markup=kb)


# ---- world boss ------------------------------------------------------------------------------------
@action("bh")
async def boss_hit_cb(ctx, arg):
    status, data = await boss_hit(ctx.uid, arg)
    if status == "hit":
        d = data["doc"]
        crit = " 💥" if data["crit"] else ""
        if d["hp"] <= 0:
            summary = await settle_boss(arg)
            if summary:
                g = await group_doc(d["chat_id"])
                text = both(g.get("lang", "both"), lambda L: boss_text(L, d, summary) + _drops(L, summary))
                await _edit(ctx, text, None)
        else:
            await _refresh_boss(ctx, d)
        return Out(alert=ctx.t("boss_hit_ok", n=fnum(data["dmg"], ctx.lang)) + crit)
    if status == "cool":
        return Out(alert=ctx.t("wait_s", n=data))
    if status == "level":
        return Out(alert=ctx.t("boss_e_level", n=data))
    return Out(alert=ctx.t("boss_e_" + status))


def _drops(L, summary):
    from i18n import t
    return "".join(f"\n🎁 {esc(str(r['name']))}: {nm(summary['drops'][r['uid']], L)}" for r in summary["rows"] if r["uid"] in summary["drops"])


async def _refresh_boss(ctx, d):
    import time
    now = int(time.time())
    hit = await col("boss_sessions").find_one_and_update({"_id": d["_id"], "edit_at": {"$lte": now - 3}}, {"$set": {"edit_at": now}})
    if not hit:
        return
    g = await group_doc(d["chat_id"])
    from ui import markup as mk
    kb = mk(ctx, [[(ctx.t("b_attack"), "bh", d["_id"], True)]])
    await _edit(ctx, both(g.get("lang", "both"), lambda L: boss_text(L, d)), kb)


@action("bossinfo")
async def boss_info(ctx, arg):
    if ctx.private:
        return Out(ctx.t("boss_private"), [nav(ctx)])
    d = await active_boss(ctx.chat_id)
    if not d:
        return Out(ctx.t("boss_none"), new=True)
    g = await group_doc(ctx.chat_id)
    return Out(both(g.get("lang", "both"), lambda L: boss_text(L, d)), [[(ctx.t("b_attack"), "bh", d["_id"], True)]], new=True)
