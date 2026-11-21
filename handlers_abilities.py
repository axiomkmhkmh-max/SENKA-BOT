"""⚔️ Ability panel (Nov 21): every special button of the race is a family with many types. Here the player sees each
family's level, the stat its power comes from (and their own value of it), picks the type each button fires before a
fight, learns type cards and levels a family with duplicate cards and coins. Data in data_abilities, rules in
service_abilities, the fight in engine._ab_run."""
import data_abilities as AB
from data_items import ALL
from database import try_cooldown
from fmt import nm, rarity_name
from i18n import fnum
from service_abilities import (card_fits, dup_cards, family_level, learn, owned, picks, set_kpick, set_pick, upgrade)
from service_economy import inv_get
from service_player import get_char
from ui import Out, action, head, nav

SLOT_FA = {"sg": "دکمه‌ی ویژه", "t1": "تکنیک ۱", "t2": "تکنیک ۲", "t3": "تکنیک ۳", "gt": "دکمه‌ی گتسوگا", "kd": "دکمه‌ی هادو", "bk": "دکمه‌ی باکودو"}
SLOT_EN = {"sg": "special button", "t1": "technique 1", "t2": "technique 2", "t3": "technique 3", "gt": "Getsuga button", "kd": "Hadō button", "bk": "Bakudō button"}


def _T(ctx, fa, en):
    return fa if ctx.lang == "fa" else en


def _n(ctx, v):
    return fnum(v, ctx.lang)


def _fam_meta(fam):
    return AB.FAMILIES.get(fam) or AB.KIDO_FAMS.get(fam) or AB.FIXED.get(fam) or {}


def _fam_name(ctx, fam):
    m = _fam_meta(fam)
    return f"{m.get('icon', '')} {m.get('fa' if ctx.lang == 'fa' else 'en', fam)}".strip()


def _type_name(ctx, fam, tid):
    t = AB.type_of(fam, tid)
    return t["fa" if ctx.lang == "fa" else "en"] if t else tid


def _stat_line(ctx, ch, mix):
    """'Reiatsu (yours: 120)' for the family's stat mix."""
    parts = []
    for k, w in sorted(mix.items(), key=lambda kv: -kv[1]):
        nmk = AB.STAT_NAMES.get(k, (k, k))[0 if ctx.lang == "fa" else 1]
        share = "" if w >= 0.999 else (fnum(int(w * 100), ctx.lang) + ("٪ " if ctx.lang == "fa" else "% "))
        if k == "weapon":
            parts.append(share + nmk)
        else:
            val = int((ch.get("stats") or {}).get(k, 0))
            parts.append(f"{share}{nmk} ({_T(ctx, 'تو', 'you')}: {fnum(val, ctx.lang)})")
    return " + ".join(parts)


def _slot_label(ctx, race, act, fam):
    slots = AB.fam_slots(race, fam)
    base = (SLOT_FA if ctx.lang == "fa" else SLOT_EN).get(act, act)
    if len(slots) > 1:
        i = slots.index(act) + 1
        return base + (f" (خانه‌ی {fnum(i, 'fa')})" if ctx.lang == "fa" else f" (slot {i})")
    return base


def _up_line(ctx, ch, inv_items, fam):
    lv = family_level(ch, fam)
    cost = AB.upgrade_cost(lv)
    if not cost:
        return _T(ctx, "⭐ حداکثر لِوِل (۱۰)", "⭐ Max level (10)"), None
    cards, coins = cost
    have = sum(q for _i, q in dup_cards(ch, inv_items, fam))
    txt = _T(ctx, f"⬆️ لِوِل بعد: {fnum(cards, 'fa')} کارت تکراری (داری {fnum(have, 'fa')}) + {fnum(coins, 'fa')} 🪙",
             f"⬆️ Next level: {cards} duplicate card(s) (you have {have}) + {coins:,} 🪙")
    return txt, (cards, coins, have)


@action("abl")
async def ability_list(ctx, arg):
    ch = await get_char(ctx.uid)
    if not ch:
        return Out(ctx.t("not_registered"))
    race = ch.get("race")
    if race not in AB.RACE_SLOTS:
        return Out(alert="—")
    L = ctx.lang
    inv = await inv_get(ctx.uid)
    items = inv.get("items") or {}
    pk, own = picks(ch), owned(ch)
    lines = [_T(ctx, "هر دکمه‌ی ویژه‌ی نژادت یک خانواده است با نوع‌های مختلف. قبل از نبرد انتخاب کن هر دکمه کدام نوع را بزند؛ "
                     "کارت تکراری + سکه لِوِل خانواده را بالا می‌برد (لِوِل بین همه‌ی نوع‌های خانواده مشترک است).",
                "Every special button of your race is a family with many types. Pick before a fight which type each button fires; "
                "duplicate cards + coins raise the family's level (shared by all its types)."), ""]
    rows, seen = [], []
    for act, fam, _i in AB.slots_of(race):
        if fam in seen:
            continue
        seen.append(fam)
        lv = family_level(ch, fam)
        if fam in AB.KIDO_FAMS:
            br = AB.KIDO_FAMS[fam]["branch"]
            kp = ((ch.get("abil") or {}).get("kpick") or {}).get(br)
            known = (ch.get("kido") or {}).get(br) or []
            cur = (f"{fnum(kp, L)}" if kp else _T(ctx, "خودکار (بهترین طلسم)", "auto (best spell)"))
            lines.append(f"<b>{_fam_name(ctx, fam)}</b> · {_T(ctx, 'لِوِل', 'level')} {fnum(lv, L)}")
            lines.append(f"   ▸ {_T(ctx, 'طلسم دکمه', 'button spell')}: {cur} · {_T(ctx, 'طلسم‌های تو', 'your spells')}: {fnum(len(known), L)}")
        else:
            F = AB.FAMILIES[fam]
            acts = AB.fam_slots(race, fam)
            chosen = " · ".join(_type_name(ctx, fam, pk[a]) for a in acts)
            lines.append(f"<b>{_fam_name(ctx, fam)}</b> · {_T(ctx, 'لِوِل', 'level')} {fnum(lv, L)} · "
                         f"{_T(ctx, 'نوع‌ها', 'types')} {fnum(len(own.get(fam, [])), L)}/{fnum(len(F['types']), L)}")
            lines.append(f"   ▸ {chosen}")
        rows.append((_fam_name(ctx, fam), "abf", fam))
    fixed = AB.RACE_FIXED.get(race, [])
    if fixed:
        lines += ["", _T(ctx, "<b>ثابت‌ها</b> (نوع ندارند ولی لِوِل دارند):", "<b>Fixed</b> (no types, but levels):")]
        lines.append(" · ".join(f"{_fam_name(ctx, fid)} {fnum(family_level(ch, fid), L)}" for fid in fixed))
        for fid in fixed:
            rows.append((_fam_name(ctx, fid), "abf", fid))
    learnable = [i for i, q in items.items() if q > 0 and (ALL.get(i) or {}).get("category") == "ability_card" and card_fits(ch, ALL[i])]
    if learnable:
        lines += ["", _T(ctx, f"🎴 {fnum(sum(items[i] for i in learnable), 'fa')} کارت توانایی در کیفت داری.",
                         f"🎴 You have {sum(items[i] for i in learnable)} ability card(s) in your bag.")]
    lines += ["", _T(ctx, "🎴 کارت‌ها از دراپ، شاپ رول، فروشگاه و جایزه‌ها می‌آیند و فقط مال نژاد خودت هستند. کارت نژاد دیگر را فقط می‌توانی بفروشی.",
                     "🎴 Cards come from drops, the roll shop, the shop and rewards, and only your race's. Another race's card can only be sold.")]
    grid = [rows[i:i + 2] for i in range(0, len(rows), 2)]
    grid.append([("🎴 " + _T(ctx, "کارت‌های کیف", "Cards in bag"), "abc", "")])
    grid.append(nav(ctx))
    return Out(head(ctx, "m_abl") + "\n".join(lines), grid)


def _kido_page(ctx, ch, fam, items):
    L = ctx.lang
    br = AB.KIDO_FAMS[fam]["branch"]
    from data_misc import KIDO_NAMES
    known = sorted((ch.get("kido") or {}).get(br) or [], reverse=True)
    kp = ((ch.get("abil") or {}).get("kpick") or {}).get(br)
    lv = family_level(ch, fam)
    up, cost = _up_line(ctx, ch, items, fam)
    lines = [f"<b>{_fam_name(ctx, fam)}</b> · {_T(ctx, 'لِوِل', 'level')} {fnum(lv, L)}/{fnum(AB.LV_MAX, L)}",
             _T(ctx, f"قدرت: کیدو — {_stat_line(ctx, ch, {'kido': 1.0})}", f"Power: Kidō — {_stat_line(ctx, ch, {'kido': 1.0})}"),
             _T(ctx, f"هر لِوِل: {'آسیب هادو' if br == 'had' else 'سپر باکودو'} +۶٪" + ("" if br == "had" else "، شانس بستن +۱"),
                f"Each level: {'Hadō damage' if br == 'had' else 'Bakudō barrier'} +6%" + ("" if br == "had" else ", bind chance +1")),
             _T(ctx, "کارت تکراری = کارت کیدوی طلسمی که بلدی.", "A duplicate = a Kidō card of a spell you know."), up, "",
             _T(ctx, f"دکمه الان می‌زند: {fnum(kp, L) + ' ' + KIDO_NAMES.get((br, kp), '') if kp else 'خودکار (بهترین طلسمی که بشود زد)'}",
                f"The button casts: {str(kp) + ' ' + KIDO_NAMES.get((br, kp), '') if kp else 'auto (the best castable spell)'}")]
    rows = []
    for n in known[:16]:
        mark = "✅ " if kp == n else ""
        rows.append((f"{mark}{fnum(n, L)} {KIDO_NAMES.get((br, n), '')}"[:40], "abk", f"{br}.{n}"))
    grid = [rows[i:i + 2] for i in range(0, len(rows), 2)]
    grid.append([("🔁 " + _T(ctx, "خودکار", "Auto"), "abk", f"{br}.0")])
    if cost and cost[2] >= cost[0]:
        grid.append([("⬆️ " + _T(ctx, f"ارتقا به لِوِل {fnum(lv + 1, 'fa')}", f"Level up to {lv + 1}"), "abu", fam)])
    grid.append(nav(ctx, ("abl", "")))
    return Out(head(ctx, "m_abl") + "\n".join(lines), grid)


@action("abf")
async def ability_family(ctx, arg):
    ch = await get_char(ctx.uid)
    if not ch:
        return Out(ctx.t("not_registered"))
    race, L = ch.get("race"), ctx.lang
    inv = await inv_get(ctx.uid)
    items = inv.get("items") or {}
    if arg in AB.KIDO_FAMS:
        return _kido_page(ctx, ch, arg, items)
    up, cost = _up_line(ctx, ch, items, arg)
    lv = family_level(ch, arg)
    if arg in AB.FIXED:
        if arg not in AB.RACE_FIXED.get(race, []):
            return Out(alert="—")
        fx = AB.FIXED[arg]
        lines = [f"<b>{_fam_name(ctx, arg)}</b> · {_T(ctx, 'لِوِل', 'level')} {fnum(lv, L)}/{fnum(AB.LV_MAX, L)}",
                 AB.fixed_text(arg, lv, L),
                 _T(ctx, f"قدرت: {_stat_line(ctx, ch, AB.stat_mix(race, arg))}", f"Power: {_stat_line(ctx, ch, AB.stat_mix(race, arg))}"),
                 _T(ctx, f"کارت تکراری: «{nm(AB.fixed_card_id(arg), 'fa')}»", f"Duplicate card: «{nm(AB.fixed_card_id(arg), 'en')}»"), up]
        grid = []
        if cost and cost[2] >= cost[0]:
            grid.append([("⬆️ " + _T(ctx, f"ارتقا به لِوِل {fnum(lv + 1, 'fa')}", f"Level up to {lv + 1}"), "abu", arg)])
        grid.append(nav(ctx, ("abl", "")))
        return Out(head(ctx, "m_abl") + "\n".join(lines), grid)
    F = AB.FAMILIES.get(arg)
    if not F or arg not in {f for _a, f, _i in AB.slots_of(race)}:
        return Out(alert="—")
    pk, own = picks(ch), owned(ch).get(arg, [])
    acts = AB.fam_slots(race, arg)
    lines = [f"<b>{_fam_name(ctx, arg)}</b> · {_T(ctx, 'لِوِل', 'level')} {fnum(lv, L)}/{fnum(AB.LV_MAX, L)}",
             _T(ctx, "هر لِوِل: ضریب‌ها +۶٪، شانس‌ها +۱، مدت +۱ نوبت در لِوِل ۵ و ۱۰، کول‌داون −۱ در لِوِل ۸، هزینه −۲٪",
                "Each level: multipliers +6%, chances +1, +1 turn at levels 5 and 10, cooldown −1 at level 8, cost −2%"),
             up, ""]
    for a in acts:
        lines.append(f"🎯 {_slot_label(ctx, race, a, arg)}: <b>{_type_name(ctx, arg, pk[a])}</b>")
    lines.append("")
    rows = []
    for t in F["types"]:
        has = t["id"] in own
        on = [a for a in acts if pk.get(a) == t["id"]]
        gate = AB.gate_of(race, arg, t)
        need = (" · " + _T(ctx, "نیاز: ", "needs: ") + AB.GATES[gate][0 if L == "fa" else 1]) if gate else ""
        mark = "✅" if on else ("▫️" if has else "🔒")
        col = rarity_name(AB.RARITIES[t["rar"]], L)
        lines.append(f"{mark} <b>{t['fa' if L == 'fa' else 'en']}</b> ({col}){need}")
        if has:
            rows.append((f"{'✅ ' if on else ''}{t['fa' if L == 'fa' else 'en']}"[:40], "abt", f"{arg}.{t['id']}"))
    lines += ["", _T(ctx, "🔒 = کارتش را نداری. روی نوع‌هایی که داری بزن تا جزئیات و انتخاب را ببینی.",
                     "🔒 = you lack its card. Tap a type you own for its details and to pick it.")]
    grid = [rows[i:i + 2] for i in range(0, len(rows), 2)]
    locked = [t for t in F["types"] if t["id"] not in own]
    if locked:
        grid.append([("🔍 " + _T(ctx, "جزئیات نوع‌های قفل", "Locked types' details"), "abt", f"{arg}.~0")])
    if cost and cost[2] >= cost[0]:
        grid.append([("⬆️ " + _T(ctx, f"ارتقا به لِوِل {fnum(lv + 1, 'fa')}", f"Level up to {lv + 1}"), "abu", arg)])
    grid.append(nav(ctx, ("abl", "")))
    return Out(head(ctx, "m_abl") + "\n".join(lines), grid)


@action("abt")
async def ability_type(ctx, arg):
    ch = await get_char(ctx.uid)
    if not ch or "." not in arg:
        return Out(alert="—")
    race, L = ch.get("race"), ctx.lang
    fam, tid = arg.split(".", 1)
    F = AB.FAMILIES.get(fam)
    if not F or fam not in {f for _a, f, _i in AB.slots_of(race)}:
        return Out(alert="—")
    lv = family_level(ch, fam)
    if tid.startswith("~"):  # the locked types of the family, a few at a time
        page = int(tid[1:] or 0)
        locked = [t for t in F["types"] if t["id"] not in owned(ch).get(fam, [])]
        chunk_ = locked[page * 6:(page + 1) * 6]
        lines = [f"<b>{_fam_name(ctx, fam)}</b> · " + _T(ctx, "نوع‌های قفل (در لِوِل فعلی خانواده)", "locked types (at the family's current level)"), ""]
        for t in chunk_:
            gate = AB.gate_of(race, fam, t)
            lines.append(f"🔒 <b>{t['fa' if L == 'fa' else 'en']}</b> — {t['src'][0 if L == 'fa' else 1]}")
            lines.append("   " + AB.describe(t, lv, L, race))
            lines.append("   " + _T(ctx, f"هزینه {AB.cost_text(t, lv, 'fa')} · کول‌داون {fnum(AB.lv_cd(t['cd'], lv), 'fa') if t['cd'] else '—'}",
                                    f"cost {AB.cost_text(t, lv, 'en')} · cooldown {AB.lv_cd(t['cd'], lv) if t['cd'] else '—'}")
                         + ((" · " + _T(ctx, "نیاز: ", "needs: ") + AB.GATES[gate][0 if L == "fa" else 1]) if gate else ""))
        nav_row = []
        if page > 0:
            nav_row.append(("◀️", "abt", f"{fam}.~{page - 1}"))
        if (page + 1) * 6 < len(locked):
            nav_row.append(("▶️", "abt", f"{fam}.~{page + 1}"))
        grid = [nav_row] if nav_row else []
        grid.append(nav(ctx, ("abf", fam)))
        return Out(head(ctx, "m_abl") + "\n".join(lines), grid)
    t = AB.type_of(fam, tid)
    if not t:
        return Out(alert="—")
    has = tid in owned(ch).get(fam, [])
    gate = AB.gate_of(race, fam, t)
    mix = AB.stat_mix(race, fam, t)
    lines = [f"<b>{t['fa' if L == 'fa' else 'en']}</b> — {_fam_name(ctx, fam)} · {_T(ctx, 'لِوِل', 'level')} {fnum(lv, L)}",
             f"{_T(ctx, 'منبع', 'Source')}: {t['src'][0 if L == 'fa' else 1]} · {_T(ctx, 'رنگ کارت', 'card colour')}: {rarity_name(AB.RARITIES[t['rar']], L)}",
             "", "📜 " + AB.describe(t, lv, L, race), "",
             _T(ctx, f"💧 هزینه: {AB.cost_text(t, lv, 'fa')} · ⏳ کول‌داون: {fnum(AB.lv_cd(t['cd'], lv), 'fa') if t['cd'] else '—'}",
                f"💧 Cost: {AB.cost_text(t, lv, 'en')} · ⏳ Cooldown: {AB.lv_cd(t['cd'], lv) if t['cd'] else '—'}"),
             _T(ctx, f"📊 قدرت از: {_stat_line(ctx, ch, mix)}", f"📊 Power from: {_stat_line(ctx, ch, mix)}")]
    if gate:
        lines.append(_T(ctx, f"🔐 نیاز: {AB.GATES[gate][0]} (دکمه فقط وقتی این حالت فعال است دیده می‌شود)",
                        f"🔐 Needs: {AB.GATES[gate][1]} (the button shows only while it holds)"))
    if lv < AB.LV_MAX:
        lines.append(_T(ctx, f"در لِوِل ۱۰: {AB.describe(t, 10, 'fa', race)}", f"At level 10: {AB.describe(t, 10, 'en', race)}"))
    rows = []
    if has:
        pk = picks(ch)
        for a in AB.fam_slots(race, fam):
            if pk.get(a) == tid:
                rows.append([("✅ " + _T(ctx, f"روی {_slot_label(ctx, race, a, fam)}", f"On the {_slot_label(ctx, race, a, fam)}"), "abf", fam)])
            else:
                rows.append([("🎯 " + _T(ctx, f"بگذار روی {_slot_label(ctx, race, a, fam)}", f"Put on the {_slot_label(ctx, race, a, fam)}"), "abp", f"{a}.{tid}")])
    else:
        lines.append(_T(ctx, f"🔒 کارتش را نداری: «{nm(AB.card_id(fam, tid), 'fa')}»", f"🔒 You lack its card: «{nm(AB.card_id(fam, tid), 'en')}»"))
    rows.append(nav(ctx, ("abf", fam)))
    return Out(head(ctx, "m_abl") + "\n".join(lines), rows)


@action("abp")
async def ability_pick(ctx, arg):
    if "." not in arg:
        return Out(alert="—")
    act, tid = arg.split(".", 1)
    r = await set_pick(ctx.uid, act, tid)
    if r == "infight":
        return Out(alert=_T(ctx, "⛔ وسط نبرد نمی‌شود نوع را عوض کرد.", "⛔ The choice is locked during a fight."))
    if r != "ok":
        return Out(alert="—")
    ch = await get_char(ctx.uid)
    fam = next((f for a, f, _i in AB.slots_of(ch.get("race")) if a == act), "")
    out = await ability_family(ctx, fam)
    out.alert = _T(ctx, f"✅ «{_type_name(ctx, fam, tid)}» روی دکمه گذاشته شد.", f"✅ «{_type_name(ctx, fam, tid)}» is on the button.")
    return out


@action("abk")
async def ability_kido_pick(ctx, arg):
    if "." not in arg:
        return Out(alert="—")
    br, n = arg.split(".", 1)
    fam = "hado" if br == "had" else "bakudo"
    if n == "0":
        from database import col
        if await col("battles").find_one({"user_id": ctx.uid, "status": "active"}, {"_id": 1}):
            return Out(alert=_T(ctx, "⛔ وسط نبرد نمی‌شود طلسم را عوض کرد.", "⛔ The spell is locked during a fight."))
        await col("characters").update_one({"user_id": ctx.uid}, {"$unset": {f"abil.kpick.{br}": ""}})
        out = await ability_family(ctx, fam)
        out.alert = _T(ctx, "🔁 دکمه بهترین طلسم را خودکار می‌زند.", "🔁 The button casts the best spell by itself.")
        return out
    r = await set_kpick(ctx.uid, br, int(n))
    if r == "infight":
        return Out(alert=_T(ctx, "⛔ وسط نبرد نمی‌شود طلسم را عوض کرد.", "⛔ The spell is locked during a fight."))
    if r != "ok":
        return Out(alert="—")
    out = await ability_family(ctx, fam)
    out.alert = _T(ctx, "✅ طلسم دکمه انتخاب شد.", "✅ Button spell set.")
    return out


@action("abu")
async def ability_upgrade(ctx, arg):
    wait = await try_cooldown(f"abup:{ctx.uid}", 2)
    if wait:
        return Out(alert=ctx.t("wait_s", n=wait))
    r, info = await upgrade(ctx.uid, arg)
    if r == "ok":
        out = await ability_family(ctx, arg)
        out.alert = _T(ctx, f"⬆️ لِوِل {fnum(info, 'fa')}!", f"⬆️ Level {info}!")
        return out
    msg = {"max": _T(ctx, "⭐ به حداکثر رسیده.", "⭐ Already at the top."),
           "cards": _T(ctx, "🎴 کارت تکراری کافی نداری.", "🎴 Not enough duplicate cards."),
           "coins": _T(ctx, "🪙 سکه کافی نداری.", "🪙 Not enough coins.")}.get(r, "—")
    return Out(alert=msg)


@action("abc")
async def ability_cards(ctx, arg):
    ch = await get_char(ctx.uid)
    if not ch:
        return Out(ctx.t("not_registered"))
    L = ctx.lang
    if arg:
        r, info = await learn(ctx.uid, arg)
        msg = {"ok": _T(ctx, "📥 نوع جدید باز شد! حالا می‌توانی آن را روی دکمه بگذاری.", "📥 A new type is open! You can put it on a button now."),
               "dup": _T(ctx, "♻️ این نوع را داری؛ کارت در کیف می‌ماند و برای ارتقای لِوِل خانواده خرج می‌شود.",
                         "♻️ You own this type; the card stays in the bag and is spent to level the family up."),
               "fixed": _T(ctx, "♻️ کارت توانایی ثابت است؛ در پنل همان توانایی برای ارتقا خرج می‌شود.",
                           "♻️ A fixed ability card: it is spent in that ability's page to level it up."),
               "race": _T(ctx, "⛔ این کارت مال نژاد دیگری است؛ فقط می‌توانی بفروشیش.", "⛔ This card is another race's; you can only sell it."),
               }.get(r, "—")
        if r == "ok":
            fam, tid = info
            out = await ability_type(ctx, f"{fam}.{tid}")
        elif r in ("dup", "fixed"):
            out = await ability_family(ctx, info)
        else:
            out = await ability_cards(ctx, "")
        out.alert = msg
        return out
    inv = await inv_get(ctx.uid)
    items = inv.get("items") or {}
    own = owned(ch)
    lines, rows = [_T(ctx, "🎴 کارت‌های توانایی در کیفت:", "🎴 Ability cards in your bag:"), ""], []
    for iid, q in sorted(items.items()):
        it = ALL.get(iid) or {}
        if q <= 0 or it.get("category") != "ability_card":
            continue
        eff = it.get("effect") or {}
        if not card_fits(ch, it):
            lines.append(f"⛔ {nm(iid, L)} ×{fnum(q, L)} — {_T(ctx, 'نژاد دیگر (فقط فروش)', 'another race (sell only)')}")
            continue
        new = eff.get("tid") and eff["tid"] not in own.get(eff["fam"], [])
        lines.append(f"{'🆕' if new else '♻️'} {nm(iid, L)} ×{fnum(q, L)}")
        if new:
            rows.append([("📥 " + nm(iid, L).replace("<", "").replace(">", ""))[:40], "abc", iid])
    if len(lines) == 2:
        lines.append(_T(ctx, "کارتی نداری.", "No cards."))
    lines += ["", _T(ctx, "🆕 = نوع جدید (بزن تا باز شود) · ♻️ = تکراری، برای ارتقا", "🆕 = a new type (tap to open) · ♻️ = a duplicate, for levelling")]
    rows = [[(r[0], r[1], r[2])] for r in rows[:12]]
    rows.append(nav(ctx, ("abl", "")))
    return Out(head(ctx, "m_abl") + "\n".join(lines), rows)
