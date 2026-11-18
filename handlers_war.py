"""⚔️ Event battlefield panels (service_war has the rules, data_war the numbers and the story)."""
import time

from data_war import (FACTIONS, GENERAL_UNLOCK_WINS, RALLY_BONUS, WAR_FIGHT_CAP, WAR_PTS, WAR_STORY, WARS, faction_of,
                      other)
from i18n import bar, esc, fnum
from service_war import war_fight, war_join, war_status, war_top
from ui import Out, action, head, nav


def _T(L, fa, en):
    return fa if L == "fa" else en


def fac_name(fid: str, L: str, icon: bool = True) -> str:
    f = FACTIONS[fid]
    return (f[2] + " " if icon else "") + (f[0] if L == "fa" else f[1])


def side_name(kind: str, side: str, L: str, icon: bool = True) -> str:
    return fac_name(faction_of(kind, side), L, icon)


def war_line(L: str, kind: str) -> str:
    """One line for event announcements: who fights whom."""
    if kind not in WARS:
        return ""
    return _T(L, f"⚔️ میدان جنگ باز شد: {side_name(kind, 'a', L)} در برابر {side_name(kind, 'b', L)}",
              f"⚔️ The battlefield is open: {side_name(kind, 'a', L)} vs {side_name(kind, 'b', L)}")


def _mins(sec) -> int:
    return max(0, int(sec // 60))


@action("war")
async def war_panel(ctx, arg):
    L = ctx.lang
    s = await war_status(ctx.uid)
    if not s["ev"]:
        lines = [_T(L, "⚔️ میدان جنگ فقط وقتی یک رویداد جهانی فعال است باز می‌شود. هر رویداد جنگ دو جناح از داستان بلیچ است.",
                    "⚔️ The battlefield opens only while a world event is on. Every event is a war between two factions of the Bleach story.")]
        lw = s.get("last")
        if lw and lw.get("kind") in WARS:
            k, sh = lw["kind"], lw.get("shares") or {"a": 50, "b": 50}
            if lw.get("winner") in ("a", "b"):
                lines.append(_T(L, f"🏁 آخرین جنگ: {side_name(k, lw['winner'], L)} پیروز شد ({fnum(sh['a'], L)}٪ – {fnum(sh['b'], L)}٪)",
                                f"🏁 Last war: {side_name(k, lw['winner'], L)} won ({sh['a']}% – {sh['b']}%)"))
            else:
                lines.append(_T(L, "🏁 آخرین جنگ مساوی شد.", "🏁 The last war was a draw."))
        return Out(head(ctx, "m_war") + "\n".join(lines), [[(ctx.t("m_evt"), "evt", "")], [(_T(L, "📖 راهنمای میدان جنگ", "📖 Battlefield guide"), "hlp", "war")], nav(ctx)])
    ev, w, kind = s["ev"], s["war"], s["ev"]["kind"]
    sh, pts, n, act = s["shares"], w.get("pts") or {}, w.get("n") or {}, w.get("act") or {}
    from handlers_world import ev_name
    lines = [f"<b>{ev_name(ctx, kind)}</b>", "<i>" + WAR_STORY[kind][0 if L == "fa" else 1] + "</i>", "",
             f"{side_name(kind, 'a', L)} <b>{fnum(sh['a'], L)}{'٪' if L == 'fa' else '%'}</b>",
             bar(sh["a"], 100, 14),
             f"{side_name(kind, 'b', L)} <b>{fnum(sh['b'], L)}{'٪' if L == 'fa' else '%'}</b>",
             _T(L, f"👥 جنگجوهای فعال: {fnum(act.get('a', 0), L)} در برابر {fnum(act.get('b', 0), L)} (ثبت‌نام: {fnum(n.get('a', 0), L)} / {fnum(n.get('b', 0), L)})",
                f"👥 Active fighters: {act.get('a', 0)} vs {act.get('b', 0)} (joined: {n.get('a', 0)} / {n.get('b', 0)})"),
             _T(L, f"🎯 امتیاز خام: {fnum(pts.get('a', 0), L)} در برابر {fnum(pts.get('b', 0), L)} · ⚖️ درصدها با تعداد جنگجوی هر طرف متعادل شده‌اند",
                f"🎯 Raw points: {pts.get('a', 0)} vs {pts.get('b', 0)} · ⚖️ the percentages are balanced by each side's fighters")]
    for sd in ("a", "b"):
        if s["rally"][sd]:
            lines.append(_T(L, f"🔥 خشم جناح: {side_name(kind, sd, L)} عقب است؛ هر بردش +{fnum(round(RALLY_BONUS * 100), L)}٪ امتیاز دارد.",
                            f"🔥 Rally: {side_name(kind, sd, L)} is behind; each of its wins scores +{round(RALLY_BONUS * 100)}%."))
    lines.append(_T(L, f"⏳ {fnum(_mins(ev['end_at'] - time.time()), L)} دقیقه تا پایان جنگ (یا زودتر، اگر هدف رویداد پر شود)",
                    f"⏳ {_mins(ev['end_at'] - time.time())} minutes left (or less, if the event's goal is reached)"))
    rows = []
    m = s["me"]
    if not m:
        lines.append("")
        if s["auto"]:
            lines.append(_T(L, f"نژاد تو در این داستان کنار {side_name(kind, s['auto'], L)} می‌جنگد.",
                            f"In this story your race fights for {side_name(kind, s['auto'], L)}."))
            rows.append([(_T(L, f"⚔️ پیوستن به {side_name(kind, s['auto'], L, False)}", f"⚔️ Join {side_name(kind, s['auto'], L, False)}"), "wj", "")])
        else:
            lines.append(_T(L, "نژاد تو در این جنگ آزاد است؛ یک طرف را انتخاب کن. انتخابت تا پایان جنگ عوض نمی‌شود.\n💡 طرفی که جنگجوی کمتری دارد، هر امتیازش وزن بیشتری دارد.",
                            "Your race is free in this war: pick a side. Your choice is locked until the war ends.\n💡 The side with fewer fighters has more weight per point."))
            rows.append([(side_name(kind, "a", L), "wj", "a"), (side_name(kind, "b", L), "wj", "b")])
    else:
        my = m["side"]
        lines += ["", _T(L, f"🫡 تو: {side_name(kind, my, L)} · امتیاز {fnum(m.get('p', 0), L)} · برد {fnum(m.get('w', 0), L)} · دفاع سایه {fnum(m.get('d', 0), L)}",
                         f"🫡 You: {side_name(kind, my, L)} · {m.get('p', 0)} points · {m.get('w', 0)} wins · shadow defence {m.get('d', 0)}"),
                  _T(L, f"🎟 نبرد باقی‌مانده: {fnum(s['left'], L)}/{fnum(WAR_FIGHT_CAP, L)}", f"🎟 Fights left: {s['left']}/{WAR_FIGHT_CAP}")]
        foe = faction_of(kind, other(my))
        if s["left"] > 0:
            rows.append([(_T(L, f"🗡 سرباز {fac_name(foe, L, False)} (+{fnum(WAR_PTS['npc'], L)})", f"🗡 {fac_name(foe, L, False)} soldier (+{WAR_PTS['npc']})"), "wf", "npc")])
            rows.append([(_T(L, f"🪞 جنگجوی واقعی دشمن (+{fnum(WAR_PTS['shadow'], L)})", f"🪞 Real enemy fighter (+{WAR_PTS['shadow']})"), "wf", "shadow")])
        gen = s["general"]
        gname = gen[0] if L == "fa" else gen[1]
        if s["gen_ready"] and s["left"] > 0:
            rows.append([(_T(L, f"👑 فرمانده: {gname} (+{fnum(WAR_PTS['general'], L)})", f"👑 General: {gname} (+{WAR_PTS['general']})"), "wf", "general")])
        elif s["gen_done"]:
            lines.append(_T(L, f"👑 فرمانده‌ی این جنگ ({gname}) را به نبرد طلبیدی.", f"👑 You have challenged this war's general ({gname})."))
        else:
            lines.append(_T(L, f"👑 فرمانده‌ی دشمن ({gname}) بعد از {fnum(GENERAL_UNLOCK_WINS, L)} برد به تو اعلام نبرد می‌کند.",
                            f"👑 The enemy general ({gname}) challenges you after {GENERAL_UNLOCK_WINS} wins."))
        lines.append(_T(L, "🪞 «جنگجوی واقعی» کپی هوش مصنوعی یک بازیکن واقعی جناح دشمن، هم‌سطح تو و با تجهیزات خودش است.",
                        "🪞 A \"real fighter\" is an AI copy of a real enemy player near your level, with their own gear."))
    rows.append([(_T(L, "🏆 جدول جنگ", "🏆 War table"), "wt", ""), (_T(L, "📖 راهنما", "📖 Guide"), "hlp", "war")])
    rows.append([(ctx.t("m_evt"), "evt", "")])
    rows.append(nav(ctx))
    return Out(head(ctx, "m_war") + "\n".join(lines), rows)


@action("wj")
async def war_join_cb(ctx, arg):
    L = ctx.lang
    status, side = await war_join(ctx.uid, arg or None)
    if status == "ok":
        out = await war_panel(ctx, "")
        s = await war_status(ctx.uid)
        out.alert = _T(L, f"🫡 به {side_name(s['ev']['kind'], side, L, False)} پیوستی!", f"🫡 You joined {side_name(s['ev']['kind'], side, L, False)}!") if s["ev"] else None
        return out
    msg = {"noevent": _T(L, "الان جنگی در جریان نیست.", "No war right now."),
           "young": _T(L, "حساب‌های خیلی تازه هنوز نمی‌توانند در جنگ شرکت کنند.", "Brand-new accounts cannot join a war yet."),
           "joined": _T(L, "قبلاً به یک طرف پیوسته‌ای.", "You already joined a side."),
           "choose": _T(L, "یک طرف را انتخاب کن.", "Pick a side.")}.get(status, "❌")
    return Out(alert=msg)


@action("wf")
async def war_fight_cb(ctx, arg):
    L = ctx.lang
    status, data = await war_fight(ctx.uid, arg if arg in ("npc", "shadow", "general") else "npc", L)
    if status == "ok":
        from handlers_combat import battle_panel
        return await battle_panel(ctx, data)
    msg = {"noevent": _T(L, "جنگ تمام شده.", "The war is over."),
           "notjoined": _T(L, "اول به یک طرف بپیوند.", "Join a side first."),
           "busy": _T(L, "اول نبرد فعلی‌ات را تمام کن.", "Finish your current fight first."),
           "wait": "⏳",
           "limit": _T(L, f"به سقف {fnum(WAR_FIGHT_CAP, L)} نبرد در این جنگ رسیدی.", f"You reached the {WAR_FIGHT_CAP}-fight cap for this war."),
           "locked": _T(L, f"فرمانده بعد از {fnum(GENERAL_UNLOCK_WINS, L)} برد می‌آید.", f"The general comes after {GENERAL_UNLOCK_WINS} wins."),
           "done": _T(L, "فرمانده‌ی این جنگ را قبلاً به نبرد طلبیدی.", "You already challenged this war's general.")}.get(status, "❌")
    return Out(alert=msg)


@action("wt")
async def war_table(ctx, arg):
    L = ctx.lang
    s = await war_status(ctx.uid)
    if not s["ev"]:
        return await war_panel(ctx, "")
    kind, eid = s["ev"]["kind"], s["ev"]["_id"]
    lines = []
    for sd in ("a", "b"):
        lines.append(f"<b>{side_name(kind, sd, L)}</b>")
        top = await war_top(eid, sd, 5)
        if not top:
            lines.append("—")
        for i, m in enumerate(top):
            lines.append(f"{['🥇', '🥈', '🥉', '4.', '5.'][i]} {esc(m.get('name', '?'))} — {fnum(m.get('p', 0), L)}"
                         + (" ⭐" if int(m.get("uid", 0)) == ctx.uid else ""))
        lines.append("")
    lines.append(_T(L, "🎁 پایان جنگ: همه‌ی جنگجوهای دو طرف (با حداقل ۲ امتیاز) سکه و تجربه می‌گیرند و سهمشان با امتیاز بالا می‌رود؛ برنده‌ها بیشتر. سنگ آبدیده‌سازی برای سه نفر اول برنده و نفر اول بازنده (با ۱۰+ امتیاز)، و ۲۴ ساعت +۵٪ تجربه برای برنده‌ها.",
                    "🎁 War end: every fighter of both sides (2+ points) gets coins and XP, growing with their points; winners get more. Tempering Stones go to the winners' top three and the losers' best (10+ points), and winners get +5% XP for 24 hours."))
    return Out(head(ctx, "m_war") + "\n".join(lines), [[(ctx.t("m_war"), "war", "")], nav(ctx)])


# ---- fight screen bits used by handlers_combat ------------------------------------------------------------------------------
def battle_title(L: str, d: dict) -> str:
    t = _T(L, f"⚔️ میدان جنگ · در برابر {fac_name(d['fac'], L)}", f"⚔️ Battlefield · against {fac_name(d['fac'], L)}")
    if d.get("kind") == "shadow":
        t += "\n" + _T(L, f"🪞 سایه‌ی {esc(d.get('tname', '?'))} (کپی هوش مصنوعی، لِوِل {fnum(d.get('tlvl', 0), L)})",
                       f"🪞 {esc(d.get('tname', '?'))}'s shadow (AI copy, level {d.get('tlvl', 0)})")
    elif d.get("kind") == "general":
        t += "\n" + _T(L, "👑 نبرد با فرمانده", "👑 The general's duel")
    if d.get("nofoe"):
        t += "\n" + _T(L, "هیچ جنگجوی دشمنی هم‌سطح تو پیدا نشد؛ یک افسر جایش آمد.", "No enemy fighter near your level: an officer stepped in.")
    return t + "\n"


def result_lines(L: str, o: dict) -> list:
    w = o.get("war") or {}
    if not w:
        return []
    if w.get("closed"):
        return [_T(L, "⚔️ جنگ تمام شده بود؛ این نبرد امتیازی برای جناح نیاورد (پاداش خود نبرد پرداخت شد).",
                   "⚔️ The war had already ended: this fight scored nothing for your side (the fight itself still paid).")]
    out = []
    if not o.get("win"):
        if w.get("def_to"):
            out.append(_T(L, f"🪞 سایه‌ی {esc(w['def_to'])} از جناحش دفاع کرد (+۱ امتیاز برای آن‌ها).",
                          f"🪞 {esc(w['def_to'])}'s shadow held its ground (+1 point for their side)."))
        return out
    if w.get("pts", 0) > 0:
        mf = w.get("my_fac")
        out.append(_T(L, f"⚔️ +{fnum(w['pts'], L)} امتیاز برای {fac_name(mf, L)}" if mf in FACTIONS else f"⚔️ +{fnum(w['pts'], L)} امتیاز جنگ",
                      f"⚔️ +{w['pts']} point{'s' if w['pts'] != 1 else ''} for {fac_name(mf, L)}" if mf in FACTIONS else f"⚔️ +{w['pts']} war points")
                   + (" 🔥" if w.get("rally") else ""))
    if w.get("kind") == "shadow":
        rep = int(w.get("repeat", 0))
        if rep == 1:
            out.append(_T(L, "↩️ دومین برد مقابل همین جنگجو: نصف امتیاز.", "↩️ Second win against the same fighter: half points."))
        elif rep >= 2:
            out.append(_T(L, "↩️ این جنگجو دیگر امتیازی نمی‌دهد؛ سراغ نفر دیگری برو.", "↩️ This fighter gives no more points: find another one."))
    if w.get("gen_open"):
        out.append(_T(L, "👑 فرمانده‌ی دشمن به تو اعلام نبرد کرد! از میدان جنگ با او بجنگ.",
                      "👑 The enemy general has challenged you! Face them from the battlefield."))
    if w.get("loot"):
        from fmt import nm
        lt = w["loot"]
        out.append(_T(L, "👑 <b>فرمانده شکست خورد!</b> ", "👑 <b>General defeated!</b> ") + f"+{fnum(lt['coins'], L)} 🪙"
                   + "".join(" · " + nm(i, L) for i in lt.get("items", [])))
    return out


def result_rows(L: str, d: dict) -> list:
    kind = d.get("kind")
    again = "shadow" if kind == "shadow" else "npc"
    label = _T(L, "🪞 جنگجوی بعدی", "🪞 Next fighter") if again == "shadow" else _T(L, "🗡 سرباز بعدی", "🗡 Next soldier")
    return [[(label, "wf", again), (_T(L, "⚔️ میدان جنگ", "⚔️ Battlefield"), "war", "")]]


# ---- end of the war: group line and private message -----------------------------------------------------------------------
def war_end_line(L: str, war: dict) -> str:
    kind, sh = war["kind"], war.get("shares") or {"a": 50, "b": 50}
    pc = "٪" if L == "fa" else "%"
    score = f"{side_name(kind, 'a', L)} {fnum(sh['a'], L)}{pc} – {fnum(sh['b'], L)}{pc} {side_name(kind, 'b', L)}"
    if war.get("winner") in ("a", "b"):
        head_ = _T(L, f"⚔️ <b>{side_name(kind, war['winner'], L)} جنگ را برد!</b>", f"⚔️ <b>{side_name(kind, war['winner'], L)} won the war!</b>")
    else:
        head_ = _T(L, "⚔️ <b>جنگ مساوی شد!</b>", "⚔️ <b>The war ended in a draw!</b>")
    lines = [head_, score]
    for sd in ("a", "b"):
        top = (war.get("top") or {}).get(sd) or []
        if top:
            lines.append(f"{FACTIONS[faction_of(kind, sd)][2]} " + "، ".join(f"{esc(n)} ({fnum(p, L)})" for n, p in top))
    return "\n".join(lines)


def war_dm(L: str, war: dict, r: dict) -> str:
    from fmt import nm
    res = {"win": _T(L, "🏆 جناحت پیروز شد!", "🏆 Your side won!"), "draw": _T(L, "🤝 جنگ مساوی شد.", "🤝 The war was a draw."),
           "lose": _T(L, "🏳️ جناحت این بار شکست خورد.", "🏳️ Your side lost this time."),
           "friendly_lose": _T(L, "🎆 تیمت این بار دوم شد.", "🎆 Your team came second this time.")}[r["result"]]
    lines = [war_end_line(L, war), "", res,
             _T(L, f"🎁 سهم تو ({fnum(r['pts'], L)} امتیاز): +{fnum(r['xp'], L)} تجربه، +{fnum(r['coins'], L)} 🪙",
                f"🎁 Your share ({r['pts']} points): +{r['xp']} XP, +{r['coins']} 🪙")]
    for i in r.get("items") or []:
        lines.append("🎁 " + nm(i, L))
    if r.get("d"):
        lines.append(_T(L, f"🪞 سایه‌ات {fnum(r['d'], L)} بار از جناحت دفاع کرد.", f"🪞 Your shadow defended your side {r['d']} times."))
    if r["result"] == "win" and r["pts"] >= 5:
        lines.append(_T(L, "✨ افتخار جناح: ۲۴ ساعت +۵٪ تجربه.", "✨ Faction glory: +5% XP for 24 hours."))
    return "\n".join(lines)
