"""PvE battles, dungeons, group duels (PvP) and world-boss buttons."""
import random

from aiogram.exceptions import TelegramBadRequest

from data_items import ALL
from data_lore import dungeon_line
from data_bleachfx import RESURRECCION_RACES
from data_race_rules import GEN_ORDER

GEN_BUTTON = {"guard": ("🧱 گارد", "🧱 Guard"), "strike": ("⚡ ضربه‌ی عمومی", "⚡ General strike"),
              "focus": ("🎯 تمرکز", "🎯 Focus")}
from data_items import iname
from data_misc import FORMS, KIDO_NAMES
from data_races import DIFFICULTY, DIFF_FA, DUNGEONS
from database import col
import engine as E
from fmt import nm
from i18n import esc, fnum
from security import normalize_text
from render import battle_text, both, boss_text, events_text, gl, glang
from service_combat import (active_pve, duel_accept, duel_challenge, duel_decline, pve_act, pve_start, pvp_act,
                            rank_letter, start_dungeon)
from service_economy import inv_get, inv_remove
from service_player import get_char
from service_world import active_boss, boss_hit, group_doc, settle_boss
from ui import Out, action, chunk, head, markup, nav


def _act_rows(ctx, f, sid, pub=False, pot=False, dist=None):
    L = ctx.lang
    form1, form2 = FORMS[f["race"]]
    i = 0 if L == "fa" else 1

    def reach_tag(label, act):
        # an attack pressed outside its reach does not strike: the turn is spent closing in (➡️) or backing off (⬅️).
        # Players read that as "my skill is locked", so say it on the button.
        band = E._band(f, act) if dist is not None else None
        if band and dist > band[1]:
            return "➡️ " + label
        if band and dist < band[0]:
            return "⬅️ " + label
        return label

    mk = lambda label, act: (reach_tag(label, act) if act in ("atk", "hvy", "kd", "gt", "gx", "sg", "t1", "t2", "t3") else label,
                             "pa" if pub else "ba", f"{sid}.{act}", pub)
    rows = [[mk(ctx.t("a_atk"), "atk")]]
    rows.append([mk("🏃 شونپو" if L == "fa" else "🏃 Shunpo", "mvs"),
                 mk("⚡ سونیدو" if L == "fa" else "⚡ Sonido", "mvn"),
                 mk("↩️ عقب" if L == "fa" else "↩️ Back", "rt"),
                 mk("↔️ جانبی" if L == "fa" else "↔️ Side", "sd")])  # distance: close in / back off
    if E.can(f, "hvy"):
        rows[0].append(mk(ctx.t("a_hvy"), "hvy"))
    r2 = []
    if E.can(f, "gc"):  # Getsuga: gather reiatsu into the blade (turn spent)
        r2.append(mk(ctx.t("a_gc"), "gc"))
    if E.can(f, "ch"):  # Kidō chanting: costs the turn, leaves you open, boosts the next spell
        r2.append(mk(ctx.t("a_ch"), "ch"))
    if E.can(f, "kd"):
        r2.append(mk(ctx.t("a_kd", n=E.best_kido(f, "had"), spell=KIDO_NAMES.get(("had", E.best_kido(f, "had")), "")), "kd"))
    if E.can(f, "bk"):
        r2.append(mk(ctx.t("a_bk", n=E.best_kido(f, "bak"), spell=KIDO_NAMES.get(("bak", E.best_kido(f, "bak")), "")), "bk"))
    for k in range(0, len(r2), 2):  # at most two long labels per line, so they stay readable on a phone
        rows.append(r2[k:k + 2])
    if E.can(f, "gt"):  # gathered: release the wave
        rows.append([mk(ctx.t("a_gt"), "gt")])
    if E.can(f, "gx"):  # spirit gauge full: the race's release (Bankai, Resurrección, Vollständig, Complete Fullbring...)
        r = f.get("race")
        rows.append([mk(ctx.t("a_gx_hollow" if r in RESURRECCION_RACES
                              else f"a_gx_{r}" if r in ("quincy", "fullbringer", "human") else "a_gx"), "gx")])
    canon_row = []
    if E.can(f, "blv"):
        canon_row.append(mk(ctx.t("a_blv"), "blv"))
    if E.can(f, "bla"):
        canon_row.append(mk(ctx.t("a_bla"), "bla"))
    if E.can(f, "bal"):
        canon_row.append(mk(ctx.t("a_bal"), "bal"))
    if E.can(f, "neg"):
        canon_row.append(mk(ctx.t("a_neg"), "neg"))
    if E.can(f, "gar"):
        canon_row.append(mk(ctx.t("a_gar"), "gar"))
    if canon_row:
        rows.append(canon_row[:2])
        if canon_row[2:]:
            rows.append(canon_row[2:])
    from data_race_tech import TECH_SLOTS, tech_name, tech_of
    tech_row = [mk(tech_name(tech_of(f["race"], s), L), s) for s in TECH_SLOTS if E.can(f, s)]
    for k in range(0, len(tech_row), 2):  # canon race techniques (Licht Regen, Hierro, Santen Kesshun...)
        rows.append(tech_row[k:k + 2])
    if E.can(f, "sg"):  # race signature move: Shunpo / Hirenkyaku / Cero / Fullbring / Fighting spirit
        key = "a_sg_cero_fire" if f.get("sig") == "cero" and (f.get("x") or {}).get("charge") else "a_sg_" + f["sig"]
        rows.append([mk(ctx.t(key), "sg")])
    if E.can(f, "bt"):  # the blade's own technique (after Shikai)
        bt = f["bt"]
        rows.append([mk(f"🗡 {bt['blade_fa' if L == 'fa' else 'blade_en']}: {bt['fa' if L == 'fa' else 'en']}", "bt")])
    if E.can(f, "gs"):  # general skill chosen in the profile (any race)
        gl_, ge_ = GEN_BUTTON[f["gen"]]
        rows.append([mk(gl_ if L == "fa" else ge_, "gs")])
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
    if d and d.get("tower"):
        title += ctx.t("tw_floor_boss" if d["stage"] % 5 == 0 else "tw_floor", n=fnum(d["stage"], ctx.lang)) + "\n"
    elif d:
        title += ctx.t("dg_stage", n=fnum(d["stage"], ctx.lang), t=fnum(d["total"], ctx.lang), diff=ctx.t("diff_" + d["diff"])) + "\n"
        flavor = dungeon_line(d.get("id"), d["stage"], d["total"], ctx.lang)
        if flavor:
            title += f"<i>{flavor}</i>\n"
    text = battle_text(ctx.lang, st, events, title)
    pot = await _has_potion(ctx.uid)
    from service_combat import can_flee
    tail = [(ctx.t("b_home"), "home", "")]
    if can_flee(doc) and not st.get("done"):  # normal battles only: fleeing costs Battle Rank, the chain stays
        tail.insert(0, ("🏃 " + ("فرار" if ctx.lang == "fa" else "Flee"), "bf", doc["sid"]))
    return Out(text, _act_rows(ctx, st["a"], doc["sid"], pot=bool(pot), dist=E.dist_of(st)) + [tail])


async def resume_battle(ctx):
    doc = await active_pve(ctx.uid)
    if not doc:
        return Out(ctx.t("bt_none"), [nav(ctx)])
    return await battle_panel(ctx, doc, [])


async def start_pve_panel(ctx, scale=1.0, force_elite=False, intro=""):
    doc = await active_pve(ctx.uid) or await pve_start(ctx.uid, ctx.lang, scale=scale, force_elite=force_elite)
    out = await battle_panel(ctx, doc, [])
    if intro:  # e.g. the "the soul you ignored became a Hollow" line above the fight
        out.text = intro + out.text
    return out


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


def _tower_result(ctx, doc, ev, o):
    L, t = ctx.lang, o["tower"]
    body = battle_text(L, doc["state"], ev, head(ctx, "ttl_bt"))
    if not o["win"]:
        text = body + "\n\n" + ctx.t("tw_fall", n=fnum(t["floor"], L), best=fnum(t["best"], L))
        return Out(text, [[(ctx.t("b_tretry"), "twr", "")], nav(ctx)])
    lines = [body, ""]
    if t["paid"]:
        lines.append(ctx.t("tw_win", n=fnum(t["floor"], L), xp=fnum(o["xp"], L), coins=fnum(o["coins"], L)))
    else:
        lines.append(ctx.t("tw_floor_n", n=fnum(t["floor"], L)) + " ✅\n" + ctx.t("tw_nopay"))
    if o["levels"]:
        lines.append(ctx.t("bt_levelup", n=fnum(o["levels"], L)))
    if o["drop"]:
        lines.append(ctx.t("bt_drop", item=nm(o["drop"], L)))
    if t["record"]:
        lines.append(ctx.t("tw_record", n=fnum(t["floor"], L)))
    if t["milestone"]:
        lines.append(ctx.t("tw_milestone", coins=fnum(t["milestone"], L)) + " · " + nm(t["milestone_item"], L))
    lines.append(ctx.t("tw_next"))
    return Out("\n".join(lines), [[(ctx.t("b_tnext"), "bn", o["next"])], nav(ctx)])


async def _pve_result(ctx, doc, ev, o):
    L = ctx.lang
    log = events_text(L, ev)
    if o.get("tower"):
        return _tower_result(ctx, doc, ev, o)
    if not o["win"]:
        text = battle_text(L, doc["state"], ev, head(ctx, "ttl_bt")) + "\n\n" + ctx.t("bt_lose")
        if o.get("chain_shield"):
            text += "\n" + ctx.t("ch_shield")
        if o.get("chain_lost"):
            text += "\n" + ctx.t("ch_lost", n=fnum(o["chain_lost"], L))
        from handlers_battlerank import result_lines
        for line in result_lines(ctx, o.get("br")):
            text += "\n" + line
        return Out(text, [[(ctx.t("b_again"), "bs", "")], nav(ctx)])
    win_line = (ctx.t("bt_win_dg", xp=fnum(o["xp"], L)) if doc.get("dungeon")
                else ctx.t("bt_win", xp=fnum(o["xp"], L), coins=fnum(o["coins"], L)))
    lines = [battle_text(L, doc["state"], ev, head(ctx, "ttl_bt")), "", win_line]
    from handlers_battlerank import result_lines
    lines += result_lines(ctx, o.get("br"))
    if o.get("chain") and o["chain"]["n"] >= 2:
        lines.append(ctx.t("ch_line", n=fnum(o["chain"]["n"], L), pct=fnum(o["chain"]["pct"], L)))
        if o["chain"].get("item"):
            lines.append(ctx.t("ch_bonus", item=nm(o["chain"]["item"], L)))
    if o["levels"]:
        lines.append(ctx.t("bt_levelup", n=fnum(o["levels"], L)))
    if o["drop"]:
        lines.append(ctx.t("bt_drop", item=nm(o["drop"], L)))
    for xid in o.get("extra_drops") or []:
        lines.append(ctx.t("bt_drop", item=nm(xid, L)))
    if o.get("bonus_drop"):
        lines.append(ctx.t("bt_drop", item=nm(o["bonus_drop"], L)))
    if o.get("dg_heal"):
        lines.append(f"💚 استراحت قبل از طبقه‌ی ۳: {fnum(o['dg_heal'], L)}٪ جان برگشت." if L == "fa"
                     else f"💚 A breather before floor 3: +{o['dg_heal']}% HP restored.")
    if o.get("drop_full"):
        lines.append(f"🎒 کیفت پره! «{nm(o['drop_full'], L)}» دراپ شد ولی جا نداشت. کیف رو خالی کن." if L == "fa"
                     else f"🎒 Bag full! «{nm(o['drop_full'], L)}» dropped but there was no room. Free some slots.")
    if o.get("evo"):
        lines.append(ctx.t("evo_done", title=o["evo"]["title_fa" if L == "fa" else "title_en"]))
    terr = o.get("terr")
    if terr:
        lines.append(ctx.t("ter_got_mine", c=fnum(terr["coins"], L), x=fnum(terr["xp"], L)) if terr.get("mine") else ctx.t("ter_got_tax", n=fnum(terr["tax"], L)))
    rows = []
    if o["next"]:
        lines.append(ctx.t("dg_next"))
        rows.append([(ctx.t("b_next_stage"), "bn", o["next"])])
    elif o["dungeon_done"]:
        lines.append(ctx.t("dg_done"))
        if o.get("dp"):
            lines.append(f"💠 دانجن پوینت: +{fnum(o['dp'], L)}" if L == "fa" else f"💠 Dungeon Points: +{fnum(o['dp'], L)}")
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


async def _potion_picker(ctx, sid: str):
    """The Potion button no longer drinks the strongest potion by itself: it lists every healing potion in the bag
    so the player picks which one to use (with its heal %)."""
    inv = await inv_get(ctx.uid)
    pots = [(i, q) for i, q in inv["items"].items() if q > 0 and ((ALL.get(i) or {}).get("effect") or {}).get("type") == "hp"]
    pots.sort(key=lambda x: -ALL[x[0]]["effect"]["pct"])
    fa = ctx.lang == "fa"
    if not pots:
        return Out(alert=ctx.t("bt_no_potion"))
    rows = [[(f"{nm(i, ctx.lang)} ×{q} · +{ALL[i]['effect']['pct']}%", "ba", f"{sid}.pot:{i}")] for i, q in pots]
    rows.append([("⬅️ برگشت" if fa else "⬅️ Back", "ba", f"{sid}.potb")])
    return Out(("🧪 کدام معجون را بخوری؟" if fa else "🧪 Which potion do you drink?"), rows)


@action("ba")
async def battle_action(ctx, arg):
    sid, _, act = arg.partition(".")
    potion = None
    if act == "pot":
        return await _potion_picker(ctx, sid)
    if act == "potb":  # back from the picker: nothing is used
        return await battle_menu(ctx, "")
    if act.startswith("pot:"):
        iid = act[4:]
        if ((ALL.get(iid) or {}).get("effect") or {}).get("type") != "hp" or not await inv_remove(ctx.uid, iid, 1):
            return Out(alert=ctx.t("bt_no_potion"))
        potion = {"type": "hp", "pct": ALL[iid]["effect"]["pct"], "id": iid}
        act = "pot"
    status, doc, data = await pve_act(ctx.uid, sid, act, potion)
    if status != "ok":
        if potion:
            from service_economy import inv_add
            await inv_add(ctx.uid, potion["id"], 1, force=True)
        return Out(alert=ctx.t("bt_" + status))
    ev, outcome = data
    if potion and not ev:  # the fight had already ended: the potion was not used
        from service_economy import inv_add
        await inv_add(ctx.uid, potion["id"], 1, force=True)
    if outcome:
        return await _pve_result(ctx, doc, ev, outcome)
    return await battle_panel(ctx, doc, ev)


WORD_ACTIONS = {"حمله": "atk", "ضربه": "atk", "attack": "atk", "atk": "atk", "strike": "atk",
                "سنگین": "hvy", "heavy": "hvy", "شونپو": "mvs", "shunpo": "mvs", "سونیدو": "mvn", "sonido": "mvn", "عقب": "rt", "retreat": "rt", "back": "rt", "جانبی": "sd", "sidestep": "sd", "دفاع": "df", "guard": "df", "defend": "df", "defense": "df"}
WORD_RELEASE = ("بانکای", "bankai", "رهاسازی", "release", "رسورکسیون", "resurreccion", "resurrección",
                "فولشتندیگ", "vollstandig", "vollständig", "فول‌برینگ کامل", "complete fullbring", "بیداری کامل روح", "awakening")
_BLADE_WORDS = None


def _maybe_battle_word(n: str) -> bool:
    """Cheap check before any database call: only an action word, a release word or a Zanpakutō name can matter."""
    global _BLADE_WORDS
    if _BLADE_WORDS is None:
        from data_zanpakuto import BLADE_UNLOCK
        _BLADE_WORDS = {normalize_text(iname(b, lg)) for b in BLADE_UNLOCK for lg in ("fa", "en")}
    return n in WORD_ACTIONS or n in WORD_RELEASE or n in _BLADE_WORDS


async def battle_word(ctx, text):
    """Typing the released blade's name (or "Bankai") during a fight unleashes it, if the spirit gauge is full.
    Returns an Out for the chat, or None when the text is not a release word (normal routing continues)."""
    n = normalize_text(text)
    if not n or not _maybe_battle_word(n):
        return None  # ordinary words skip the battle lookup entirely (one database round trip less per message)
    doc = await active_pve(ctx.uid)
    if not doc:
        return None
    act = WORD_ACTIONS.get(n)
    if act:  # typed «حمله» / "attack" in a fight = the same as pressing the button
        if not E.can(doc["state"]["a"], act):
            return None  # e.g. not enough reiatsu for a heavy strike: normal routing
        status, d, data = await pve_act(ctx.uid, doc["sid"], act)
        if status != "ok":
            return Out(ctx.t("bt_" + status), [nav(ctx)], new=True)
        ev, outcome = data
        out = await _pve_result(ctx, d, ev, outcome) if outcome else await battle_panel(ctx, d, ev)
        out.new = True
        return out
    z = ((await col("characters").find_one({"user_id": ctx.uid}, {"zanpakuto": 1})) or {}).get("zanpakuto") or {}
    released = bool(z.get("shikai") or z.get("bankai")) and bool(z.get("blade_id"))
    names = set(WORD_RELEASE)
    if z.get("blade_id"):
        names |= {normalize_text(iname(z["blade_id"], "fa")), normalize_text(iname(z["blade_id"], "en"))}
    if n not in names:
        return None
    from data_race_rules import SHINIGAMI_LIKE
    if not released and doc["state"]["a"].get("race") in SHINIGAMI_LIKE:  # only a Zanpakutō needs its Shikai first
        return Out(ctx.t("wr_locked"), [nav(ctx)], new=True)
    f = doc["state"]["a"]
    if not E.can(f, "gx"):
        return Out(ctx.t("bt_gauge_low", n=fnum((f.get("x") or {}).get("gauge", 0), ctx.lang)), [nav(ctx)], new=True)
    status, d, data = await pve_act(ctx.uid, doc["sid"], "gx")
    if status != "ok":
        return Out(ctx.t("bt_" + status), [nav(ctx)], new=True)
    ev, outcome = data
    out = await _pve_result(ctx, d, ev, outcome) if outcome else await battle_panel(ctx, d, ev)
    out.new = True
    return out


# ---- dungeons ---------------------------------------------------------------------------------
@action("dgn")
async def dungeons(ctx, arg):
    ch = await get_char(ctx.uid)
    L = ctx.lang
    rows = []
    for did, d in DUNGEONS.items():
        ok = ch["level"] >= d["level"]
        rows.append([(("🕳️ " if ok else "🔒 ") + f"{d['fa' if L == 'fa' else 'en']} ({fnum(d['level'], L)})", "dgd" if ok else "noop", did)])
    rows.append([(("💠 شاپ دانجن" if L == "fa" else "💠 Dungeon Shop"), "dps", "")])
    rows.append(nav(ctx))
    dp = int(ch.get("dp", 0) or 0)
    return Out(head(ctx, "ttl_dgn") + ctx.t("dgn_body") + (f"\n\n💠 دانجن پوینت: {fnum(dp, L)}" if L == "fa" else f"\n\n💠 Dungeon Points: {fnum(dp, L)}"), rows)


@action("dgd")
async def dungeon_diff(ctx, arg):
    L = ctx.lang
    d = DUNGEONS.get(arg)
    if not d:
        return Out()
    rows = [[(ctx.t("diff_" + k) + f" ×{DIFFICULTY[k]:g}" + (" 🔑" if k != "normal" else ""), "dgs", f"{arg}.{k}")] for k in DIFFICULTY]
    rows.append(nav(ctx, ("dgn", "")))
    lvl_line = (f"\n🎚 سطح دشمنان ثابت: {fnum(d['level'], L)} — ضریب سختی روی قدرت دشمن و پاداش اثر می‌گذارد."
                if L == "fa" else f"\n🎚 Fixed enemy level: {d['level']}. The difficulty multiplier scales enemy power and rewards.")
    return Out(head(ctx, "ttl_dgn") + f"<b>{d['fa' if L == 'fa' else 'en']}</b>\n<i>{dungeon_line(arg, 1, d['stages'], L)}</i>\n" + ctx.t("dgn_pick", n=fnum(d["stages"], L)) + lvl_line, rows)


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
    text = both(glang(g), lambda L: __import__("i18n").t(L, "duel_invite", a=esc(d["a_name"]), b=esc(d["b_name"]),
                mode=__import__("i18n").t(L, "duel_ranked" if ranked else "duel_friendly")))
    rows = [[(ctx.t("b_accept"), "dua", d["sid"], False), (ctx.t("b_decline"), "dud", d["sid"], False)]]
    # accept/decline are bound to the challenged player
    from security import make_cb
    from aiogram.types import InlineKeyboardMarkup
    from ui import make_button
    kb = InlineKeyboardMarkup(inline_keyboard=[[make_button(gl(glang(g), "✅ قبول", "✅ Accept"), make_cb("dua", d["sid"], d["b_uid"]), "dua"),
                                                make_button(gl(glang(g), "❌ رد", "❌ Decline"), make_cb("dud", d["sid"], d["b_uid"]), "dud")]])
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
        rows = _act_rows(ctx, st[st["cur"]], doc["sid"], pub=True, dist=E.dist_of(st))
    return text, markup(ctx, rows)


@action("dua")
async def duel_accept_cb(ctx, arg):
    doc = await duel_accept(arg, ctx.uid)
    if not doc:
        return Out(alert=ctx.t("duel_gone"))
    g = await group_doc(doc["chat_id"])
    text, kb = await _pvp_panel(glang(g), ctx, doc, [])
    await _edit(ctx, text, kb)
    if ctx.message is not None:  # the scheduler needs the panel's message id to refresh the buttons after a turn timeout
        await col("battles").update_one({"sid": arg, "mode": "pvp"}, {"$set": {"msg_id": ctx.message.message_id}})
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
        for uid, br in (outcome.get("br") or {}).items():
            if br:
                nm_ = doc["a_name"] if uid == doc["a_uid"] else doc["b_name"]
                d = br["delta"]
                lines.append(f"🎖 {esc(nm_)}: {'+' if d >= 0 else '−'}{fnum(abs(d), L)} → {br['title_fa' if L == 'fa' else 'title_en']}"
                             + (" ⬆️" if br.get("up") else " ⬇️" if br.get("down") else ""))
        if outcome.get("note"):
            lines.append(t(L, "duel_note_" + outcome["note"]))
        if outcome.get("bounty"):
            lines.append(t(L, "bty_claimed", n=fnum(outcome["bounty"], L)))
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
    text, kb = await _pvp_panel(glang(g), ctx, doc, ev, final)
    await _edit(ctx, text, kb)
    return Out()


async def _edit(ctx, text, kb):
    try:
        await ctx.message.edit_text(text, reply_markup=kb)
    except (TelegramBadRequest, AttributeError) as e:
        if "not modified" not in str(e):
            await ctx.bot.send_message(ctx.chat_id, text, reply_markup=kb)


# ---- world boss (one global boss) ------------------------------------------------------------------------------------
def _panel_text(ctx, d, result=None):
    if ctx.private:
        return boss_text(ctx.lang, d, result)
    return None


# battle cries by race (Bleach flavour); a signature strike always gets one, normal hits sometimes
CALLS = {"shinigami": (["گتسوگا تنشو!", "بانکای!", "شیکای: ببُر!"], ["Getsuga Tenshō!", "Bankai!", "Shikai: Cleave!"]),
         "quincy": (["هایلیگ پفایل!", "ضربه‌ی خون‌ورید!"], ["Heilig Pfeil!", "Blut Vene Strike!"]),
         "hollow": (["سرو!", "غرش هالو!"], ["Cero!", "Hollow Roar!"]),
         "arrancar": (["سرو اسکوراس!", "رزورکسیون!"], ["Cero Oscuras!", "Resurrección!"]),
         "human": (["مشت روح!", "ضربه‌ی قلب!"], ["Spirit Fist!", "Heart Strike!"]),
         "fullbringer": (["فول‌برینگ!", "ضربه‌ی پیوند!"], ["Fullbring!", "Bond Strike!"]),
         "visored": (["ماسک هالو!", "سرو ویزورد!"], ["Hollow Mask!", "Visored Cero!"])}


def _call(lang, race, always):
    import random
    if not always and random.random() > 0.5:
        return ""
    fa, en = CALLS.get(race, CALLS["human"])
    return " " + random.choice(fa if lang == "fa" else en)


@action("bh")
async def boss_hit_cb(ctx, arg):
    status, data = await boss_hit(ctx.uid, arg)
    if status == "hit":
        d = data["doc"]
        crit = " 💥" if data["crit"] else ""
        killing = d["hp"] <= 0
        if killing:
            summary = await settle_boss(arg)
            if summary:
                import handlers_world
                try:
                    await handlers_world.end_global_boss(ctx.bot, d, summary)
                    if ctx.private:
                        await _edit(ctx, boss_text(ctx.lang, d, summary) + _drops(ctx.lang, summary), None)
                except Exception:
                    import logging
                    logging.getLogger(__name__).exception("boss end announce failed")
        else:
            await _refresh_boss(ctx, d)
            if data.get("phase_up"):
                import asyncio
                import handlers_world
                asyncio.ensure_future(handlers_world.announce_boss_phase(ctx.bot, d, data["phase_up"]))
        head = ("✨ " + ctx.t("boss_special") + " ") if data["special"] else ""
        tail = (" · " + ctx.t("boss_combo_s", n=fnum(data["combo"], ctx.lang))) if data["combo"] >= 2 else ""
        fin = (" " + ctx.t("boss_final_blow")) if killing else ""
        return Out(alert=head + ctx.t("boss_hit_ok", n=fnum(data["dmg"], ctx.lang)) + crit + _call(ctx.lang, data["race"], data["special"] or killing) + tail + fin)
    if status == "cool":
        return Out(alert=ctx.t("wait_s", n=data))
    if status == "level":
        return Out(alert=ctx.t("boss_e_level", n=data))
    # "dead" and "gone" are only answers, never a settlement: the killing blow settles its own kill, and the
    # scheduler's expiry settles anything left over (a crash). A second settle here used to steal the payout
    # from the killer, who then saw no result and no drop.
    return Out(alert=ctx.t("boss_e_" + status))


def _drops(L, summary):
    out = "".join(f"\n🎁 {esc(str(r['name']))}: {nm(summary['drops'][r['uid']], L)}" for r in summary["rows"] if r["uid"] in summary["drops"])
    out += "".join(f"\n🌀 {esc(str(r['name']))}: {nm(summary['evo_drops'][r['uid']], L)}" for r in summary["rows"] if r["uid"] in summary.get("evo_drops", {}))
    return out


async def _refresh_boss(ctx, d):
    import time
    now = int(time.time())
    hit = await col("boss_sessions").find_one_and_update({"_id": d["_id"], "edit_at": {"$lte": now - 3}}, {"$set": {"edit_at": now}})
    if not hit:
        return
    from ui import markup as mk
    if ctx.private:
        kb = mk(ctx, [[(ctx.t("b_attack"), "bh", d["_id"], True)]])
        text = boss_text(ctx.lang, d)
    else:
        g = await group_doc(ctx.chat_id)
        kb = mk(ctx, [[("⚔️ " + gl(glang(g), "حمله", "Attack"), "bh", d["_id"], True)]])
        text = both(glang(g), lambda L: boss_text(L, d))
    await _edit(ctx, text, kb)


@action("bsty")
async def boss_style_toggle(ctx, arg):
    """Switch the boss attack between the blade and Hadō (Shinigami and Visored only)."""
    me = await get_char(ctx.uid)
    if not me or me.get("race") not in ("shinigami", "visored"):
        return Out(alert=("فقط شینیگامی و ویزرد می‌تونن با هادو به باس حمله کنن." if ctx.lang == "fa"
                          else "Only Shinigami and Visored can strike bosses with Hadō."))
    new = "blade" if me.get("boss_style") == "kido" else "kido"
    await col("characters").update_one({"user_id": ctx.uid}, {"$set": {"boss_style": new}})
    return await boss_info(ctx, "")


@action("bossinfo")
async def boss_info(ctx, arg):
    from database import game_settings
    import time
    from service_worldcore import get_world
    d = await active_boss()
    if not d:
        ws, _ = await get_world(force=True)
        m = max(0, int(ws.get("next_boss_at", 0) - time.time())) // 60 + 1
        return Out(ctx.t("boss_none_next", m=fnum(m, ctx.lang)), [nav(ctx, ("wrd", ""))] if ctx.private else None, new=not ctx.private)
    kb = [[(ctx.t("b_attack"), "bh", d["_id"], True)]]
    if ctx.private:
        rows = kb + [nav(ctx, ("wrd", ""))]
        me = await get_char(ctx.uid)
        if me and me.get("race") in ("shinigami", "visored"):  # the only races that can strike with Hadō
            style_kido = me.get("boss_style") == "kido"
            label = ("🔁 نوع حمله: هادو" if style_kido else "🔁 نوع حمله: زانپاکتو") if ctx.lang == "fa" else \
                    ("🔁 Attack: Hadō" if style_kido else "🔁 Attack: Zanpakutō")
            rows = kb + [[(label, "bsty", "")], nav(ctx, ("wrd", ""))]
        return Out(boss_text(ctx.lang, d), rows)
    g = await group_doc(ctx.chat_id)
    kb = [[("⚔️ " + gl(glang(g), "حمله", "Attack"), "bh", d["_id"], True)]]
    return Out(both(glang(g), lambda L: boss_text(L, d)), kb, new=True)
