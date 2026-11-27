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




def _act_rows(ctx, f, sid, pub=False, pot=False, dist=None, side_on=False):
    """The attack panel (Nov 26 rebuild). One screen, five bands, always in the same order:
        1. STRIKE   ⚔️ attack · 💥 heavy
        2. KIDŌ     🔮 best Hadō [▾ quick picks] · 🛡 best Bakudō [▾ quick picks]
        3. SPECIAL  release / Shikai / techniques / signature / finishers (only what can be used right now)
        4. MOVE     one row: Shunpo · Sonido · back · side
        5. DEFEND   guard · forms · potion
    Buttons that cannot be used are simply not drawn, so what you see is what you can press."""
    L = ctx.lang
    fa = L == "fa"
    form1, form2 = FORMS[f["race"]]
    i = 0 if fa else 1

    def reach_tag(label, act):
        # an attack pressed outside its reach spends the turn closing in (➡️) or backing off (⬅️): say it on the button
        band = E._band(f, act) if dist is not None else None
        if band and dist > band[1]:
            return "➡️ " + label
        if band and dist < band[0]:
            return "⬅️ " + label
        return label

    def mk(label, act):
        base = {"kdm": "kd", "bkm": "bk"}.get(act.split(":")[0], act.split(":")[0])  # "kd:31" / "kdm:q" press the kidō button
        return (reach_tag(label, base) if base in ("atk", "hvy", "kd", "gt", "gx", "sg", "t1", "t2", "t3") else label,
                "pa" if pub else "ba", f"{sid}.{act}", pub)
    import data_abilities as AB
    fab = f.get("ab") or {}

    def ab_label(act):  # the picked type's name on its family's button (data_abilities)
        a = fab.get(act)
        t = AB.type_of(a["fam"], a["tid"]) if a else None
        if not t:
            return None
        icon = AB.FAMILIES[a["fam"]]["icon"]
        chg = (f.get("x") or {}).get("chg") or {}
        name = t["fa" if fa else "en"]
        return f"{icon} {name}" + (" 🔥" if chg.get(act) else "")
    from engine_range import move_label

    rows = []
    # 1. STRIKE
    strike = [mk(ctx.t("a_atk"), "atk")]
    if E.can(f, "hvy"):
        strike.append(mk(ctx.t("a_hvy"), "hvy"))
    rows.append(strike)

    # 2. KIDŌ: the big button casts the best spell now (one tap), the small ▾ opens the quick picks
    for branch, can_act in (("had", "kd"), ("bak", "bk")):
        if not E.can(f, can_act):
            continue
        n = E.best_kido(f, branch)
        spells = E.kido_list(f, branch)
        row = [mk(ctx.t("a_" + can_act, n=n, spell=KIDO_NAMES.get((branch, n), "")), can_act)]
        if len(spells) > 1:
            row.append(mk("▾", f"{can_act}m:q"))
        rows.append(row)
    if E.can(f, "ch"):  # chanting costs the turn and leaves you open, but the next spell hits at full power
        rows.append([mk(ctx.t("a_ch"), "ch")])

    # 3. SPECIAL
    special = []
    if E.can(f, "gx"):  # spirit gauge full: the race's release, which also opens its form (Shikai/Bankai, Resurrección...)
        r = f.get("race")
        n = E.release_form(f)
        if n:
            label = f"👑 {(FORMS.get(r) or FORMS['human'])[n - 1][i]}!"
        else:
            label = ctx.t("a_gx_hollow" if r in RESURRECCION_RACES else f"a_gx_{r}" if r in ("quincy", "fullbringer", "human") else "a_gx")
        rows.append([mk(label, "gx")])  # the payoff move gets its own full-width line
    if (fab or f.get("blade") == "kyoka_suigetsu") and E.can(f, "sk"):  # Shikai / Hollow Mask: the early state button
        special.append(mk(("🗡 شیکای!" if fa else "🗡 Shikai!") if f.get("race") == "shinigami" or f.get("blade") == "kyoka_suigetsu"
                          else ("🎭 ماسک هالو!" if fa else "🎭 Hollow Mask!"), "sk"))
    if E.can(f, "gc"):  # Getsuga: gather reiatsu into the blade (turn spent)
        special.append(mk((("🌙 جمع کردن: " if fa else "🌙 Gather: ") + (ab_label("gt") or "").split(" ", 1)[-1]) if fab.get("gt") else ctx.t("a_gc"), "gc"))
    if E.can(f, "gt"):  # gathered: release the wave
        special.append(mk(ab_label("gt") if fab.get("gt") else ctx.t("a_gt"), "gt"))
    for act, key in (("blv", "a_blv"), ("bla", "a_bla"), ("bal", "a_bal"), ("neg", "a_neg"), ("gar", "a_gar")):
        if E.can(f, act):
            special.append(mk(ctx.t(key), act))
    if E.can(f, "if"):  # Iron Fist: only while Hierro holds
        special.append(mk("🦾 ضربه‌ی آهنین" if fa else "🦾 Iron Fist", "if"))
    from data_race_tech import TECH_SLOTS, tech_name, tech_of
    for s_ in TECH_SLOTS:  # canon race techniques (Licht Regen, Hierro, Santen Kesshun...)
        if E.can(f, s_):
            special.append(mk(ab_label(s_) or tech_name(tech_of(f["race"], s_), L), s_))
    if E.can(f, "sg"):  # race signature move: Shunpo / Hirenkyaku / Cero / Fullbring / Fighting spirit
        key = "a_sg_cero_fire" if f.get("sig") == "cero" and (f.get("x") or {}).get("charge") else "a_sg_" + f["sig"]
        special.append(mk(ab_label("sg") or ctx.t(key), "sg"))
    if E.can(f, "bt"):  # the blade's own technique (after Shikai); in Bankai its deadlier form
        bt = f["bt"]
        if f["form"]["on"] == 2 and bt.get("bk"):
            bt = {**bt, **bt["bk"]}
            special.append(mk(f"💥 {bt['fa' if fa else 'en']}", "bt"))
        else:
            special.append(mk(f"🗡 {bt['blade_fa' if fa else 'blade_en']}: {bt['fa' if fa else 'en']}", "bt"))
    if E.can(f, "b2"):  # the blade's second simple ability (after Shikai); in Bankai its deadlier form
        b2 = f["b2"]
        if f["form"]["on"] == 2 and b2.get("bk"):
            b2 = {**b2, **b2["bk"]}
            special.append(mk(f"💥 {b2['fa' if fa else 'en']}", "b2"))
        else:
            special.append(mk(f"🔰 {b2['fa' if fa else 'en']}", "b2"))
    if f.get("blade") == "kyoka_suigetsu":
        shikai = bool((f.get("x") or {}).get("kyoka_shikai_t", 0) > 0)
        names = (["🌫️ توهم مطلق" if fa else "🌫️ Absolute Illusion", "🪞 دنیای آینه‌ای" if fa else "🪞 Mirror World",
                  "👁️ تسلط حواس پنج‌گانه" if fa else "👁️ Five Senses Domination", "☠️ اعدام توهمی" if fa else "☠️ Illusionary Execution"] if shikai else
                 ["🌫️ ضربه‌ی توهمی" if fa else "🌫️ Illusion Strike", "🪞 بدل خیالی" if fa else "🪞 False Reality",
                  "🧠 اختلال ذهنی" if fa else "🧠 Mind Distortion", "💨 قدم شبح" if fa else "💨 Phantom Step"])
        for idx, label in enumerate(names, 1):
            if E.can(f, f"ks{idx}"):
                special.append(mk(label, f"ks{idx}"))
        if shikai and E.can(f, "ks5"):
            special.append(mk("👑 کانزن سایمین: سراب بی‌نهایت" if fa else "👑 Kanzen Saimin: Infinite Mirage", "ks5"))
    if E.can(f, "gs"):  # general skill chosen in the profile (any race)
        gl_, ge_ = GEN_BUTTON[f["gen"]]
        special.append(mk(gl_ if fa else ge_, "gs"))
    rows.extend(chunk(special, 2))
    if E.can(f, "bu"):  # the blade's finisher (after Shikai): full width, it is the big moment
        bu = f["bu"]
        if f["form"]["on"] == 2 and bu.get("bk"):
            bu = {**bu, **bu["bk"]}
        rows.append([mk("👑 " + bu["fa" if fa else "en"], "bu")])

    # 4. MOVE: one compact row
    rows.append([mk("🏃 " + move_label(f.get("race"), "shunpo")[i], "mvs"),
                 mk("💨 " + move_label(f.get("race"), "sonido")[i], "mvn"),
                 mk("↩️", "rt"),
                 mk("↔️✔" if side_on else "↔️", "sd")])  # side stance: a free toggle (no turn)

    # 5. DEFEND
    r3 = [mk(ctx.t("a_df"), "df")]
    if E.can(f, "f1"):
        r3.append(mk("✨ " + form1[i], "f1"))
    if E.can(f, "f2"):
        r3.append(mk("🌟 " + form2[i], "f2"))
    rows.append(r3)
    if pot and not ((f.get("fj_stage") == 9) or f.get("fj_no_potions")):
        rows.append([mk(ctx.t("a_pot"), "pot")])
    return rows


KIDO_PAGE = 10   # spells per menu page (two per row)


def _kido_menu(ctx, f, sid, branch, page, pub):
    """The spell menu. page == -1 is the QUICK view: one button per role (strongest / burn / stun / pierce / weaken / cheap
    for Hadō; bind / barrier / weaken / cheap for Bakudō) with the best spell the fighter owns for it. page >= 0 is the full
    list (highest first, 10 per page). A tap sends kd:<n> / bk:<n>. Returns (header text, rows)."""
    import data_kido as KD
    fa = ctx.lang == "fa"
    code, pre = ("pa" if pub else "ba"), ("kd" if branch == "had" else "bk")
    menu = E.kido_menu(f, branch)
    title = (("🔮 هادو" if fa else "🔮 Hadō") if branch == "had" else ("🛡️ باکودو" if fa else "🛡️ Bakudō"))
    text = f"{title}\n💠 {fnum(f['re'], ctx.lang)}/{fnum(f['max_re'], ctx.lang)}"
    back = [("⬅️ برگشت" if fa else "⬅️ Back", code, f"{sid}.kdb", pub)]
    if page < 0:
        rows = []
        for role, icon, rfa, ren, n in KD.quick_picks(branch, [n for n, _ in menu]):
            name = KIDO_NAMES.get((branch, n), "")
            rows.append([(f"{icon} {rfa if fa else ren} · {n} {name} · {KD.cost_pct(branch, n):g}%", code, f"{sid}.{pre}:{n}", pub)])
        rows.append([("📚 " + ("همه‌ی اسپل‌ها" if fa else "All spells"), code, f"{sid}.{pre}m:0", pub)] + back)
        text += "\n" + ("یکی را بزن؛ بهترین اسپل تو برای هر کار نشان داده شده." if fa else "Pick a job; your best spell for it is shown.")
    else:
        pages = max(1, -(-len(menu) // KIDO_PAGE))
        page = min(max(page, 0), pages - 1)
        btns = []
        for n, pct in menu[page * KIDO_PAGE:(page + 1) * KIDO_PAGE]:
            name = KIDO_NAMES.get((branch, n), "")
            btns.append((" ".join(x for x in (KD.icons(branch, n), str(n), name) if x) + f" · {pct:g}%", code, f"{sid}.{pre}:{n}", pub))
        rows = chunk(btns, 2)
        if pages > 1:
            nv = []
            if page > 0:
                nv.append(("◀️", code, f"{sid}.{pre}m:{page - 1}", pub))
            if page < pages - 1:
                nv.append(("▶️", code, f"{sid}.{pre}m:{page + 1}", pub))
            rows.append(nv)
            text += f" · {fnum(page + 1, ctx.lang)}/{fnum(pages, ctx.lang)}"
        rows.append([("⚡ " + ("انتخاب سریع" if fa else "Quick picks"), code, f"{sid}.{pre}m:q", pub)] + back)
    if E._x(f)["chant"]:
        text += "\n" + ("📿 ورد خوانده شده؛ اولین کیدو با قدرت کامل زده می‌شه." if fa else "📿 Chant spoken: your next spell hits at full power.")
    return text, rows


def _kido_act(act):
    """\"kdm:2\" / \"bkm:0\" -> (branch, page), anything else -> None."""
    if act[:4] in ("kdm:", "bkm:"):
        if act[4:] == "q":   # the quick-picks view
            return ("had" if act[0] == "k" else "bak"), -1
        try:
            return ("had" if act[0] == "k" else "bak"), int(act[4:])
        except ValueError:
            return ("had" if act[0] == "k" else "bak"), 0
    return None


def battle_potion(iid):
    """(kind, pct) if the item can be drunk mid-fight, else None. kind: hp (heal %), reiatsu (restore %), def (defence share)."""
    it = ALL.get(iid) or {}
    e = it.get("effect") or {}
    if e.get("type") in ("hp", "reiatsu"):
        return e["type"], e["pct"]
    if it.get("category") == "potion" and e.get("type") == "buff" and e.get("stat") == "def":
        from data_misc import POTION_DEF_BOOST
        return "def", min(0.6, float(e["pct"]) * POTION_DEF_BOOST)  # +5-10% was not felt in a fight: the potion is worth more mid-battle
    return None


def _potion_rank(iid):
    kind, pct = battle_potion(iid)
    return ({"hp": 0, "reiatsu": 1, "def": 2}[kind], -pct)


async def _has_potion(uid):
    inv = await inv_get(uid)
    return next((i for i, q in inv["items"].items() if q > 0 and battle_potion(i)), None)


def _tower_leave_row(ctx):
    """Soul Tower exit buttons (handled by handlers_towerx.tower_exit): register the floor and leave, or leave as is."""
    fa = ctx.lang == "fa"
    return [("💾 " + ("ثبت و خروج" if fa else "Save & leave"), "twx", "save"),
            ("🚪 " + ("خروج از برج" if fa else "Leave tower"), "twx", "")]


async def battle_panel(ctx, doc, events=None):
    st = doc["state"]
    title = head(ctx, "ttl_bt")
    d = doc.get("dungeon")
    if d and d.get("final_judgment"):
        title += (f"⚖️ <b>THE FINAL JUDGMENT — مرحله {d['stage']}/10</b>\n" if ctx.lang == "fa"
                  else f"⚖️ <b>THE FINAL JUDGMENT — Stage {d['stage']}/10</b>\n")
        title += (f"{d.get('wave', 1)}/{d.get('wave_total', 1)} · " + __import__('service_final_judgment').stage_name(d['stage'], ctx.lang) + "\n")
    if d and d.get("tower"):
        title += ctx.t("tw_floor_boss" if d["stage"] % 5 == 0 else "tw_floor", n=fnum(d["stage"], ctx.lang)) + "\n"
    elif d and d.get("hog"):  # Hōgyoku duel: round counter and the rounds already decided
        from handlers_viral import hog_title
        title += hog_title(ctx.lang, d)
    elif d and d.get("war"):
        from handlers_war import battle_title
        title += battle_title(ctx.lang, d)
    elif d and d.get("lboss"):
        title += ctx.t("lb_stage") + "\n"
    elif d and d.get("gq"):
        from data_guildquest import title as gq_title
        title += ctx.t("gq_stage", title=gq_title(d, ctx.lang), n=fnum(d["stage"], ctx.lang), t=fnum(d["total"], ctx.lang)) + "\n"
    elif d and not d.get("final_judgment"):
        title += ctx.t("dg_stage", n=fnum(d["stage"], ctx.lang), t=fnum(d["total"], ctx.lang), diff=ctx.t("diff_" + d["diff"])) + "\n"
        flavor = dungeon_line(d.get("id"), d["stage"], d["total"], ctx.lang)
        if flavor:
            title += f"<i>{flavor}</i>\n"
    if (st["a"].get("blade") == "kyoka_suigetsu"):
        kx = st["a"].get("x") or {}
        if kx.get("kyoka_shikai_t", 0) > 0:
            title += (f"👁️ شیکای فعال · {max(1, kx['kyoka_shikai_t'] - 1)} نوبت باقی‌مانده\n" if ctx.lang == "fa"
                      else f"👁️ Shikai active · {max(1, kx['kyoka_shikai_t'] - 1)} turns remaining\n")
        elif kx.get("kyoka_shikai_cd", 0) > 0:
            title += (f"⏳ کول‌داون شیکای: {kx['kyoka_shikai_cd']}\n" if ctx.lang == "fa"
                      else f"⏳ Shikai cooldown: {kx['kyoka_shikai_cd']}\n")
        title += ctx.t("kyoka_stat_scaling", re=fnum(E.eff(st["a"], "reiatsu"), ctx.lang),
                       zan=fnum(E.eff(st["a"], "zanjutsu"), ctx.lang)) + "\n"
    from service_fightfx import challenge_line
    title += challenge_line(st, ctx.lang)
    text = battle_text(ctx.lang, st, events, title)
    pot = await _has_potion(ctx.uid)
    from service_combat import can_flee
    tail = [(ctx.t("b_home"), "home", "")]
    if can_flee(doc) and not st.get("done"):  # normal battles only: fleeing costs Battle Rank, the chain stays
        tail.insert(0, ("🏃 " + ("فرار" if ctx.lang == "fa" else "Flee"), "bf", doc["sid"]))
    rows = _act_rows(ctx, st["a"], doc["sid"], pot=bool(pot), dist=E.dist_of(st), side_on=E.in_side(st, "a")) + [tail]
    if d and d.get("tower") and not st.get("done"):  # a tower climb can always be left from the fight screen itself
        rows.append(_tower_leave_row(ctx))
    if d and d.get("final_judgment") and not st.get("done"):  # the Judgment can always be left from the fight screen
        rows.append([("🚪 " + ("خروج از داوری" if ctx.lang == "fa" else "Leave the Judgment"), "fjq", doc["sid"])])
    if d and d.get("hog") and not st.get("done"):  # a Hōgyoku duel can be given up (no penalty, the try stays spent)
        rows.append([("🏳️ " + ("تسلیم" if ctx.lang == "fa" else "Forfeit"), "vrf", doc["sid"])])
    return Out(text, rows)


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
    rows = [[(ctx.t("b_fight"), "bs", ""), (ctx.t("m_dgn"), "dgn", "")], nav(ctx)]  # Nov 26: the Final Judgment event is closed (service_final_judgment.FJ_OPEN)
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
    return Out("\n".join(lines), [[(ctx.t("b_tnext"), "bn", o["next"])], _tower_leave_row(ctx), nav(ctx)])


async def _pve_result(ctx, doc, ev, o):
    L = ctx.lang
    log = events_text(L, ev)
    if o.get("final_judgment"):
        fj = o["final_judgment"]
        body = battle_text(L, doc["state"], ev, head(ctx, "ttl_bt"))
        if fj.get("next"):
            next_doc = fj["next"]
            nd = next_doc.get("dungeon") or {}
            if int(nd.get("stage", 0)) == int(fj.get("stage", 0)):
                intro = (f"\n\n⚖️ موج {fj['wave']} از {fj['wave_total']} پاک‌سازی شد؛ موج بعدی آغاز شد." if L == "fa"
                         else f"\n\n⚖️ Wave {fj['wave']}/{fj['wave_total']} cleared; the next wave begins.")
            else:
                intro = (f"\n\n⚖️ مرحله‌ی {fj['stage']} پاک‌سازی شد. مرحله‌ی بعدی آغاز شد." if L == "fa"
                         else f"\n\n⚖️ Stage {fj['stage']} cleared. The next stage begins.")
            panel = await battle_panel(ctx, next_doc, [])
            panel.text = body + intro + "\n\n" + panel.text
            return panel
        if fj.get("won"):
            reward = fj.get("reward") or ""
            msg = ("\n\n👑 <b>THE FINAL JUDGMENT CLEARED</b>\nتو از هر ده مرحله عبور کردی." if L == "fa"
                   else "\n\n👑 <b>THE FINAL JUDGMENT CLEARED</b>\nYou survived all ten stages.")
            if reward:
                msg += "\n🏆 " + reward
            return Out(body + msg, [[(ctx.t("b_home"), "home", "")]])
        return Out(body + ("\n\n☠️ تلاش امروزت به پایان رسید. پیشرفت این تلاش از بین رفت." if L == "fa"
                           else "\n\n☠️ Your attempt has ended. All progress from this run was lost."), [[(ctx.t("b_home"), "home", "")]])
    if o.get("tower"):
        return _tower_result(ctx, doc, ev, o)
    if o.get("hog"):  # Hōgyoku duel round / final card
        from handlers_viral import hog_result
        return await hog_result(ctx, doc, ev, o)
    if not o["win"]:
        text = battle_text(L, doc["state"], ev, head(ctx, "ttl_bt")) + "\n\n" + ctx.t("bt_lose")
        if o.get("chain_shield"):
            text += "\n" + ctx.t("ch_shield")
        if o.get("chain_lost"):
            text += "\n" + ctx.t("ch_lost", n=fnum(o["chain_lost"], L))
        from handlers_battlerank import result_lines
        for line in result_lines(ctx, o.get("br")):
            text += "\n" + line
        if o.get("chl"):
            from service_fightfx import text as chl_text
            text += "\n" + ("❌ چالش: " if L == "fa" else "❌ Challenge: ") + chl_text(o["chl"], L)
        dlx = doc.get("dungeon") or {}
        if dlx.get("war"):
            from handlers_war import result_lines as war_lines, result_rows as war_rows
            for line in war_lines(L, o):
                text += "\n" + line
            return Out(text, war_rows(L, dlx) + [nav(ctx)])
        return Out(text, [[(ctx.t("b_again"), "bs", "")], nav(ctx)])
    dgx = doc.get("dungeon") or {}
    win_line = (ctx.t("bt_win_dg", xp=fnum(o["xp"], L)) if doc.get("dungeon") and not dgx.get("war")
                else ctx.t("bt_win", xp=fnum(o["xp"], L), coins=fnum(o["coins"], L)))
    lines = [battle_text(L, doc["state"], ev, head(ctx, "ttl_bt")), "", win_line]
    from handlers_battlerank import result_lines
    lines += result_lines(ctx, o.get("br"))
    if o.get("chain") and o["chain"]["n"] >= 2:
        lines.append(ctx.t("ch_line", n=fnum(o["chain"]["n"], L), pct=fnum(o["chain"]["pct"], L)))
        if o["chain"].get("item"):
            lines.append(ctx.t("ch_bonus", item=nm(o["chain"]["item"], L)))
    ms = (o.get("chain") or {}).get("milestone")
    if ms:  # chain milestone: coins and a guaranteed item, paid by chain_win
        lines.append((f"🏆 نقطه‌عطف زنجیره‌ی {fnum(ms['n'], L)} برد: +{fnum(ms['coins'], L)} 🪙" if L == "fa"
                      else f"🏆 Chain milestone, {fnum(ms['n'], L)} wins: +{fnum(ms['coins'], L)} 🪙")
                     + (f" · {nm(ms['item'], L)}" if ms.get("item") else ""))
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
    if dgx.get("war"):
        from handlers_war import result_lines as war_lines
        lines += war_lines(L, o)
    if o.get("gap_k"):  # open worlds: the enemy's level against yours
        gk = o["gap_k"]
        lines.append((f"⚖️ ضریب سطح دشمن: ×{fnum(str(gk), L)}" if L == "fa" else f"⚖️ Enemy level factor: x{gk}")
                     + ((" (دشمن قوی‌تر)" if L == "fa" else " (a stronger foe)") if gk > 1 else (" (دشمن خیلی ضعیف‌تر)" if L == "fa" else " (a much weaker foe)")))
    if o.get("chl"):  # the fight's challenge
        from service_fightfx import CHL_BONUS, text as chl_text
        c = o["chl"]
        if c["done"]:
            lines.append(("🎯 چالش انجام شد: " if L == "fa" else "🎯 Challenge done: ") + chl_text(c, L)
                         + (f" (+{fnum(int(CHL_BONUS * 100), L)}٪ اکس‌پی و سکه)" if L == "fa" else f" (+{int(CHL_BONUS * 100)}% XP and coins)"))
            if c.get("card"):
                lines.append(("🎴 جایزه‌ی چالش: " if L == "fa" else "🎴 Challenge prize: ") + nm(c["card"], L))
        else:
            lines.append(("❌ چالش انجام نشد: " if L == "fa" else "❌ Challenge missed: ") + chl_text(c, L))
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
    elif dgx.get("war"):  # battlefield: next fight or back to the battlefield
        from handlers_war import result_rows as war_rows
        rows += war_rows(L, dgx)
    elif o.get("lboss"):  # level boss defeated
        lines.append(ctx.t("lb_done"))
        lines.append(ctx.t("lb_items", items=", ".join(nm(i, L) for i in o["lboss"]["items"]) or "—"))
    elif o.get("quest"):  # Guild Quest cleared: items, release progress, purse
        from data_guildquest import RANKS
        qd = o["quest"]
        lines.append(ctx.t("gq_done", rank=RANKS[qd["rank"]]))
        lines.append(ctx.t("gq_items", items=", ".join(nm(i, L) for i in qd["items"]) or "—"))
        lines.append(ctx.t("gq_znp", bond=fnum(qd["bond"], L)) + (ctx.t("gq_znp_m", m=fnum(qd["mastery"], L)) if qd["mastery"] else ""))
        lines.append(ctx.t("gq_coins", c=fnum(qd["coins"], L)))
        rows.append([(ctx.t("gq_back"), "avl", "")])
    elif o["dungeon_done"]:
        lines.append(ctx.t("dg_done"))
        if o.get("dp"):
            lines.append(f"💠 دانجن پوینت: +{fnum(o['dp'], L)}" if L == "fa" else f"💠 Dungeon Points: +{fnum(o['dp'], L)}")
        if o.get("final"):
            fid, fq = o["final"]
            lines.append(f"🏆 دراپ پایان دانجن: {nm(fid, L)} ×{fq}" if L == "fa" else f"🏆 Final-stage drop: {nm(fid, L)} x{fq}")
        if o.get("special"):
            lines.append(f"🎁 آیتم مخصوص دانجن: {nm(o['special'], L)}" if L == "fa" else f"🎁 Dungeon special item: {nm(o['special'], L)}")
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
    pots = [(i, q) for i, q in inv["items"].items() if q > 0 and battle_potion(i)]
    pots.sort(key=lambda x: _potion_rank(x[0]))
    fa = ctx.lang == "fa"
    if not pots:
        return Out(alert=ctx.t("bt_no_potion"))
    def _what(i):
        kind, pct = battle_potion(i)
        if kind == "def":
            return f"+{round(pct * 100):g}% " + (f"دفاع ({fnum(E.POTION_DEF_TURNS, ctx.lang)} نوبت)" if fa else f"defence ({E.POTION_DEF_TURNS} turns)")
        return f"+{pct}% " + (("جان" if fa else "HP") if kind == "hp" else ("ریاتسو" if fa else "Reiatsu"))
    rows = [[(f"{nm(i, ctx.lang)} ×{q} · {_what(i)}", "ba", f"{sid}.pot:{i}")] for i, q in pots]
    rows.append([("⬅️ برگشت" if fa else "⬅️ Back", "ba", f"{sid}.potb")])
    return Out(("🧪 کدام معجون را بخوری؟" if fa else "🧪 Which potion do you drink?"), rows)


@action("ba")
async def battle_action(ctx, arg):
    sid, _, act = arg.partition(".")
    potion = None
    if act == "pot":
        return await _potion_picker(ctx, sid)
    if act == "potb" or act == "kdb":  # back from the picker / spell menu: nothing is used
        return await battle_menu(ctx, "")
    km = _kido_act(act)
    if km:  # the spell menu (no turn is spent)
        doc = await active_pve(ctx.uid)
        if not doc or doc["sid"] != sid:
            return Out(alert=ctx.t("bt_gone"))
        st = doc["state"]
        if st["cur"] != "a" or not st.get("awaiting") or st.get("done"):
            return Out(alert=ctx.t("bt_notturn"))
        if not E.kido_menu(st["a"], km[0]):
            return Out(alert=ctx.t("bt_notturn"))
        text, rows = _kido_menu(ctx, st["a"], sid, km[0], km[1], False)
        return Out(battle_text(ctx.lang, st, [], head(ctx, "ttl_bt")) + "\n\n" + text, rows)
    if act.startswith("pot:"):
        iid = act[4:]
        bp = battle_potion(iid)
        if not bp or not await inv_remove(ctx.uid, iid, 1):
            return Out(alert=ctx.t("bt_no_potion"))
        potion = {"type": bp[0], "pct": bp[1], "id": iid}
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
        from data_zanpakuto import BLADE_STAGES
        _BLADE_WORDS = {normalize_text(iname(b, lg)) for b in BLADE_UNLOCK for lg in ("fa", "en")}
        for b, st in BLADE_STAGES.items():  # Nov 27: «بانکای زانکا نو تاچی» / "Bankai Zanka no Tachi" works too
            for i, lg in enumerate(("fa", "en")):
                if st.get("bankai"):
                    _BLADE_WORDS.add(normalize_text(st["bankai"][i]))
                    _BLADE_WORDS.add(normalize_text(("بانکای " if lg == "fa" else "bankai ") + st["bankai"][i]))
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
        from data_zanpakuto import BLADE_STAGES
        bk = (BLADE_STAGES.get(z["blade_id"]) or {}).get("bankai")
        if bk:  # the Bankai name, alone or after the word "Bankai"
            for i, w in enumerate(("بانکای ", "bankai ")):
                names |= {normalize_text(bk[i]), normalize_text(w + bk[i])}
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
def _invite_text(L, d, ca, cb, ranked):
    """The challenge card: both fighters side by side (race, level, rank, record) before the blades are drawn."""
    import duel_ui as DU
    from i18n import t
    fa = L == "fa"

    def card(side, c):
        rt = int(c.get("rating", 0) or 0)
        w, l_ = int(c.get("pvp_w", 0) or 0), int(c.get("pvp_l", 0) or 0)
        lv = ("سطح " if fa else "Lv ") + fnum(c.get("level", 1), L)
        rec = (f"📈 {fnum(w, L)} برد · {fnum(l_, L)} باخت" if fa else f"📈 {w}W · {l_}L")
        return (f"{DU.SIDE[side]} <b>{esc(c['name'])}</b>\n"
                f"   {DU.RACE_EMBLEM.get(c.get('race'), '⚔️')} <i>{esc(DU.race_name(L, c.get('race')))}</i> · {lv}\n"
                f"   🏅 {rank_letter(rt)} · {fnum(rt, L)} · {rec}")
    mode = t(L, "duel_ranked" if ranked else "duel_friendly")
    title = ("🥊 <b>چالش دوئل " + mode + "!</b>" if fa else f"🥊 <b>{mode} duel challenge!</b>") + (" 🏅" if ranked else "")
    lines = [title, DU.SEP,
             t(L, "duel_invite", a=esc(d["a_name"]), b=esc(d["b_name"]), mode=mode), "",
             card("a", ca), "            ⚡ 𝗩𝗦 ⚡", card("b", cb), DU.SEP,
             (f"⏳ <b>{esc(d['b_name'])}</b> پنج دقیقه فرصت داره قبول کنه." if fa
              else f"⏳ <b>{esc(d['b_name'])}</b> has five minutes to answer.")]
    if ranked:
        lines.append("🎖 " + ("برنده رتبه و رنک نبرد می‌گیره؛ بازنده از دست می‌ده." if fa
                              else "The winner gains rating and Battle Rank; the loser drops."))
    return "\n".join(lines)


async def _invite(chat_id, a_uid, b_uid, ranked):
    """Create the duel and build its invite. Returns (status, extra, text, kb)."""
    status, extra = await duel_challenge(chat_id, a_uid, b_uid, ranked)
    if status != "ok":
        return status, extra, None, None
    d = extra
    g = await group_doc(chat_id)
    L = glang(g)
    ca, cb = await get_char(a_uid), await get_char(b_uid)
    text = _invite_text(L, d, ca or {"name": d["a_name"]}, cb or {"name": d["b_name"]}, ranked)
    # accept/decline are bound to the challenged player
    from security import make_cb
    from aiogram.types import InlineKeyboardMarkup
    from ui import make_button
    kb = InlineKeyboardMarkup(inline_keyboard=[[make_button(gl(L, "⚔️ قبول دوئل", "⚔️ Accept duel"), make_cb("dua", d["sid"], d["b_uid"]), "dua"),
                                                make_button(gl(L, "🏳️ رد", "🏳️ Decline"), make_cb("dud", d["sid"], d["b_uid"]), "dud")]])
    return status, extra, text, kb


async def challenge(ctx, target, ranked: bool):
    """Called from the text router when someone replies 'duel' to another player."""
    status, extra, text, kb = await _invite(ctx.chat_id, ctx.uid, target.id, ranked)
    if status != "ok":
        return Out(ctx.t("duel_e_" + status, n=extra or ""))
    return Out(text, new=True), kb


class _LangCtx:
    """The clicker's context, speaking the group's language: a duel panel is shared, so its buttons must not follow
    whoever pressed last."""
    def __init__(self, ctx, lang):
        self._ctx, self.lang = ctx, lang

    def __getattr__(self, name):
        return getattr(self._ctx, name)

    def t(self, key, **kw):
        from i18n import t
        return t(self.lang, key, **kw)


async def _pvp_panel(chat_lang, ctx, doc, events, final=None):
    import duel_ui as DU
    st = doc["state"]
    L = chat_lang if chat_lang in ("fa", "en") else "en"
    gctx = _LangCtx(ctx, L)
    text = DU.panel_text(L, doc, events, final(L) if final is not None else None)
    if len(text) > 4000:  # Telegram's limit: drop the move log before anything else
        text = DU.panel_text(L, doc, [], final(L) if final is not None else None)
    sid = doc["sid"]
    if final is None:
        cur = st["cur"]
        me = st[cur]
        turn = (f"{DU.SIDE[cur]} نوبت {me['name']}" if L == "fa" else f"{DU.SIDE[cur]} {me['name']}'s turn")
        rows = [[(turn[:60], "noop", "", True)]]
        rows += _act_rows(gctx, me, sid, pub=True, dist=E.dist_of(st), side_on=E.in_side(st, cur))
        rows.append([("🏳️ " + ("تسلیم" if L == "fa" else "Yield"), "pff", sid, True)])
    else:
        rows = [[("🔁 " + ("دوئل دوباره" if L == "fa" else "Rematch"), "drm", sid, True)]] if not doc.get("tournament") else []
    return text, markup(gctx, rows)


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

    import duel_ui as DU

    def fn(L):
        st = doc["state"]
        if st.get("winner") not in ("a", "b") or (outcome or {}).get("draw"):
            return "\n".join([t(L, "duel_draw")] + [""] + DU.report_lines(L, st))
        lines = DU.winner_banner(L, doc, random.Random(doc.get("sid")))  # the same line on every refresh of this card
        report = DU.report_lines(L, st)
        if report:
            lines += [""] + report
        if outcome is None:  # settled by another tap a moment earlier: the banner is all this card can show
            return "\n".join(lines)
        if outcome["rating"] or outcome.get("xp") or outcome.get("br"):
            lines += ["", "🎖 <b>" + ("پاداش‌ها" if L == "fa" else "Rewards") + "</b>"]
        for uid, (rt, delta) in outcome["rating"].items():
            nm_ = doc["a_name"] if uid == doc["a_uid"] else doc["b_name"]
            arrow = "🔺" if delta > 0 else "🔻"
            lines.append(f"{arrow} {esc(nm_)}: 🏅 {rank_letter(rt)} {fnum(rt, L)} ({'+' if delta > 0 else ''}{fnum(delta, L)})")
        for uid, got in (outcome.get("xp") or {}).items():
            if got:
                nm_ = doc["a_name"] if uid == doc["a_uid"] else doc["b_name"]
                lines.append(f"📈 {esc(nm_)}: +{fnum(got, L)} " + ("تجربه" if L == "fa" else "XP"))
        for uid, br in (outcome.get("br") or {}).items():
            if br:
                nm_ = doc["a_name"] if uid == doc["a_uid"] else doc["b_name"]
                d = br["delta"]
                lines.append(f"🎖 {esc(nm_)}: {'+' if d >= 0 else '−'}{fnum(abs(d), L)} → {br['title_fa' if L == 'fa' else 'title_en']}"
                             + (" ⬆️" if br.get("up") else " ⬇️" if br.get("down") else ""))
        bn = outcome.get("br_note")
        if bn:
            from data_battlerank import DUEL_DAILY_CAP, DUEL_PAIR_DAILY
            if bn == "gap":
                from data_battlerank import DUEL_NO_GAIN_GAP
                lines.append(f"⚖️ برنده بیشتر از {fnum(DUEL_NO_GAIN_GAP, L)} امتیاز رنک بالاتر از حریف بود؛ رنک هیچ‌کدام تغییر نکرد." if L == "fa"
                             else f"⚖️ The winner was {DUEL_NO_GAIN_GAP}+ rank points above the loser; nobody's rank changed.")
            elif bn == "pair":
                lines.append(f"⏳ با این حریف فقط {fnum(DUEL_PAIR_DAILY, L)} دوئل اول هر روز رنک دارد." if L == "fa"
                             else f"⏳ Only the first {DUEL_PAIR_DAILY} duels a day against the same opponent change Battle Rank.")
            else:
                lines.append(f"⏳ سقف روزانه‌ی رنک دوئل ({fnum(DUEL_DAILY_CAP, L)}) برای برنده پر بود؛ رنک هیچ‌کدام تغییر نکرد." if L == "fa"
                             else f"⏳ The winner's daily duel rank cap ({DUEL_DAILY_CAP}) was full; nobody's rank changed.")
        if outcome.get("note"):
            lines.append(t(L, "duel_note_" + outcome["note"]))
        if outcome.get("bounty"):
            lines.append(t(L, "bty_claimed", n=fnum(outcome["bounty"], L)))
        return "\n".join(lines)
    return fn


@action("pa")
async def pvp_action(ctx, arg):
    sid, _, act = arg.partition(".")
    km = _kido_act(act)
    if km or act == "kdb":  # spell menu / back from it: no turn is spent
        return await _pvp_kido_menu(ctx, sid, km, act)
    status, doc, data = await pvp_act(ctx.uid, sid, act)
    if status != "ok":
        return Out(alert=ctx.t("bt_" + status if status != "notplayer" else "duel_notplayer"))
    ev, outcome = data
    g = await group_doc(doc["chat_id"])
    final = _final(ctx, doc, outcome) if doc["state"]["done"] else None
    text, kb = await _pvp_panel(glang(g), ctx, doc, ev, final)
    await _edit(ctx, text, kb)
    return Out()


FORFEIT_CONFIRM_S = 8   # a second tap on Yield within this window ends the duel (one stray tap never does)


@action("pff")
async def pvp_forfeit_cb(ctx, arg):
    from database import try_cooldown
    from service_combat import pvp_forfeit
    doc = await col("battles").find_one({"sid": arg, "mode": "pvp", "status": "active"}, {"a_uid": 1, "b_uid": 1})
    if not doc:
        return Out(alert=ctx.t("bt_gone"))
    if ctx.uid not in (doc["a_uid"], doc["b_uid"]):
        return Out(alert=ctx.t("duel_notplayer"))
    if not await try_cooldown(f"pff:{arg}:{ctx.uid}", FORFEIT_CONFIRM_S):
        return Out(alert=(f"🏳️ مطمئنی؟ برای تسلیم ظرف {fnum(FORFEIT_CONFIRM_S, ctx.lang)} ثانیه دوباره بزن. تسلیم یعنی باخت."
                          if ctx.lang == "fa" else
                          f"🏳️ Sure? Tap Yield again within {FORFEIT_CONFIRM_S}s. Yielding counts as a loss."))
    status, doc, outcome = await pvp_forfeit(ctx.uid, arg)
    if status != "ok":
        return Out(alert=ctx.t("bt_gone" if status != "notplayer" else "duel_notplayer"))
    g = await group_doc(doc["chat_id"])
    text, kb = await _pvp_panel(glang(g), ctx, doc, [], _final(ctx, doc, outcome))
    await _edit(ctx, text, kb)
    return Out()


@action("drm")
async def duel_rematch_cb(ctx, arg):
    """Rematch from the final card: the presser challenges the other fighter again, same mode, same group."""
    doc = await col("battles").find_one({"sid": arg, "mode": "pvp"})
    if not doc or doc.get("status") != "done" or doc.get("tournament"):
        return Out(alert=ctx.t("duel_gone"))
    if ctx.uid not in (doc["a_uid"], doc["b_uid"]):
        return Out(alert=ctx.t("duel_notplayer"))
    other = doc["b_uid"] if ctx.uid == doc["a_uid"] else doc["a_uid"]
    status, extra, text, kb = await _invite(doc["chat_id"], ctx.uid, other, bool(doc.get("ranked")))
    if status != "ok":
        return Out(alert=ctx.t("duel_e_" + status, n=extra or ""))
    await ctx.bot.send_message(doc["chat_id"], text, reply_markup=kb)
    return Out(alert="🔁 " + ("دعوت دوئل دوباره فرستاده شد!" if ctx.lang == "fa" else "Rematch challenge sent!"))


async def _pvp_kido_menu(ctx, sid, km, act):
    doc = await col("battles").find_one({"sid": sid, "mode": "pvp", "status": "active"})
    if not doc:
        return Out(alert=ctx.t("bt_gone"))
    st = doc["state"]
    side = "a" if ctx.uid == doc["a_uid"] else "b" if ctx.uid == doc["b_uid"] else None
    if side is None:
        return Out(alert=ctx.t("duel_notplayer"))
    if st.get("done") or st["cur"] != side or not st.get("awaiting"):
        return Out(alert=ctx.t("bt_notturn"))
    g = await group_doc(doc["chat_id"])
    text, kb = await _pvp_panel(glang(g), ctx, doc, [])
    if km:
        if not E.kido_menu(st[side], km[0]):
            return Out(alert=ctx.t("bt_notturn"))
        mtext, rows = _kido_menu(_LangCtx(ctx, glang(g)), st[side], sid, km[0], km[1], True)
        text, kb = text + "\n\n" + mtext, markup(ctx, rows)
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


def _kido_call(lang, num, spell):
    """Battle cry of a Hadō strike: its own name, never the race's Mask / Getsuga line."""
    name = f"{spell} " if spell else ""
    return f" {name}" + (f"هادو {fnum(num, lang)}!" if lang == "fa" else f"Hadō {num}!")


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
        from database import game_settings as _gs
        _st = await _gs()
        if data.get("burst") and not killing:
            from service_world import claim_burst_announce
            if await claim_burst_announce(arg, int(_st["boss_burst_announce_gap"])):  # one group message per gap, not per hit
                import asyncio
                import handlers_world
                asyncio.ensure_future(handlers_world.announce_boss_burst(ctx.bot, d, (d.get("adapt") or {}).get("n", "?")))
        burst = ""
        if data.get("burst"):
            if int(_st["boss_burst_mode"]) in (1, 3):
                burst += ctx.t("boss_burst_cd", s=fnum(int(_st["boss_burst_cd"]), ctx.lang))
            if int(_st["boss_burst_mode"]) in (2, 3):
                burst += ctx.t("boss_burst_red")
        tail = (" · " + ctx.t("boss_combo_s", n=fnum(data["combo"], ctx.lang))) if data["combo"] >= 2 else ""
        fin = (" " + ctx.t("boss_final_blow")) if killing else ""
        return Out(alert=head + ctx.t("boss_hit_ok", n=fnum(data["dmg"], ctx.lang)) + crit + (_kido_call(ctx.lang, data["kido"], data.get("spell", "")) if data.get("kido") else _call(ctx.lang, data["race"], data["special"] or killing)) + tail + burst + fin)
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
