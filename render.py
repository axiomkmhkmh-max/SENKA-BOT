"""Text rendering for battles and bosses (language-parametrised, no I/O)."""
import time

import random

from data_bleachfx import RESURRECCION_RACES, move_name
from data_bosses import BOSS_BY_ID
from i18n import LOCALES, bar, esc, fnum, t
from engine_range import ZONE_EN, ZONE_FA

FX_ICON = {"burn": "🔥", "poison": "☠️", "bleed": "🩸", "shock": "⚡", "weaken": "🔻", "fear": "😨", "hiren": "🌪️"}


KIDO_CD_LINE = True    # the "kidō cooldown" line under the fight text (Nov 26: back on, Hadō has a cooldown again)


def both(mode: str, fn) -> str:
    """Render in exactly one language (never fa+en in one message). Name kept for the existing call sites."""
    return fn(mode if mode in ("fa", "en") else "en")


def glang(g: dict) -> str:
    """Language of a group: the admin's explicit choice (fa/en), else the auto-detected one. Always one language;
    an old stored bilingual value ("both") is ignored."""
    g = g or {}
    if g.get("lang_set") and g.get("lang") in ("fa", "en"):
        return g["lang"]
    return g.get("auto_lang") if g.get("auto_lang") in ("fa", "en") else "fa"


def gl(mode: str, fa: str, en: str) -> str:
    return fa if mode == "fa" else en


def pick(lang: str, key: str, **kw) -> str:
    """Return one random flavour variant: key, key_2, key_3 ... (falls back to key)."""
    table = LOCALES.get(lang) or LOCALES["en"]
    keys = [key] + [f"{key}_{i}" for i in range(2, 9) if f"{key}_{i}" in table]
    return t(lang, random.choice(keys), **kw)


def dist_label(lang: str, d: int) -> str:
    return (ZONE_FA if lang == "fa" else ZONE_EN).get(int(d), "")


def dist_event_text(lang: str, e: dict) -> str:
    fa = lang == "fa"
    a, d = esc(e.get("a", "")), esc(e.get("d", ""))
    if e["k"] == "move":
        tech = e.get("tech", "") if fa else (e.get("tech_en") or e.get("tech", ""))  # English showed the Persian name
        return (f"🏃 {a} با {esc(tech)} به فاصله‌ی {dist_label(lang, e['to'])} رسید" if fa
                else f"🏃 {a} closes in with {esc(tech)} → {dist_label(lang, e['to'])}")
    if e["k"] == "retreat":
        return (f"↩️ {a} عقب کشید ({dist_label(lang, e['to'])})" if fa
                else f"↩️ {a} backs off ({dist_label(lang, e['to'])})")
    if e["k"] == "side":
        return (f"↔️ {a} رفت به حالت جانبی: هوهو ×۲، قدرت ضربه‌ها نصف" if fa
                else f"↔️ {a} turns side-on: Hohō x2, own blows at half power")
    if e["k"] == "side_off":
        return (f"↔️ {a} از حالت جانبی بیرون آمد و دوباره رو در رو ایستاد" if fa
                else f"↔️ {a} squares up again: the side stance ends")
    if e["k"] == "side_no":
        return (f"↔️ این نوبت حالت جانبی رو یک بار عوض کردی (یا ریاتسو کافی نیست)" if fa
                else f"↔️ The stance was already switched this turn (or not enough reiatsu)")
    if e["k"] == "outrange":
        return f"💨 {a} به برد نرسید و نوبتش هدر رفت" if fa else f"💨 {a} is out of range and loses the turn"
    return f"💥 {d} به عقب پرت شد" if fa else f"💥 {d} is knocked back"


AB_EVENTS = ("ab", "ab_charge", "abfx", "ab_evade", "ab_shadow", "ab_doble", "ab_late", "ab_trap", "ab_trap_miss", "recoil",
             "shikai", "mask_on")
_ABFX = {"daze": ("گیج شد (۵۰٪ خطا)", "is dazed (50% misses)"), "seal": ("مهر شد: توانایی ویژه نمی‌زند", "is sealed: no abilities"),
         "root": ("قفل شد: فاصله را عوض نمی‌کند", "is rooted: cannot change the gap"), "noregen": ("بازسازی‌اش قطع شد", "stops regenerating"),
         "brk": ("سپرش شکست", "loses the barrier"), "debuff": ("ضعیف‌تر شد", "is weakened"), "copy": ("بافرهایش را از دست داد", "loses the buffs to the thief"),
         "hierro": ("پوستش مثل فولاد شد", "skin turns to steel")}


def ab_event_text(lang: str, e: dict) -> str:
    import data_abilities as AB
    fa = lang == "fa"
    a, d, k = esc(e.get("a", "")), esc(e.get("d", "")), e["k"]
    if k in ("ab", "ab_charge"):
        fam, tid = e.get("fam"), e.get("tid")
        if fam == "ironfist":
            return f"🦾 {a} با مشت آهنین جلو رفت" if fa else f"🦾 {a} swings an Iron Fist"
        t = AB.type_of(fam, tid)
        name = esc(t["fa" if fa else "en"]) if t else str(tid)
        icon = AB.FAMILIES.get(fam, {}).get("icon", "✨")
        if k == "ab_charge":
            return (f"{icon} {a} دارد «{name}» را شارژ می‌کند... یک ضربه‌ی سنگین می‌شکندش!" if fa
                    else f"{icon} {a} gathers «{name}»... a hard hit can break it!")
        return f"{icon} {a}: «{name}»!"
    if k == "abfx":
        fx = _ABFX.get(e.get("fx"), (e.get("fx"), e.get("fx")))
        who = a if e.get("fx") == "hierro" else d
        return f"✨ {who} {fx[0] if fa else fx[1]}"
    if k == "ab_evade":
        return f"💨 ضربه‌ی {d} از میان تصویر {a} گذشت" if fa else f"💨 {d}'s blow passes through {a}'s afterimage"
    if k == "ab_shadow":
        return f"🌑 {a} در سایه بود؛ ضربه‌ی {d} به هیچ خورد" if fa else f"🌑 {a} is in the shadow: {d} strikes nothing"
    if k == "ab_doble":
        return f"🔁 {a} حمله را بلعید و پس زد!" if fa else f"🔁 {a} swallows the attack and fires it back!"
    if k == "ab_late":
        return f"⏳ ضربه‌ی تاخیری {a} رسید!" if fa else f"⏳ {a}'s delayed blow arrives!"
    if k == "ab_trap":
        return f"💣 تله‌ی {a} منفجر شد!" if fa else f"💣 {a}'s trap explodes!"
    if k == "ab_trap_miss":
        return f"💨 دشمن از تله‌ی {a} بیرون پرید" if fa else f"💨 The foe slipped out of {a}'s trap"
    if k == "recoil":
        return f"🩸 {a} از ضربه‌ی خودش {fnum(e.get('n', 0), lang)} آسیب خورد" if fa else f"🩸 {a} takes {e.get('n', 0)} recoil"
    if k == "shikai":
        from data_zanpakuto import release_call
        call = release_call(e.get("bl"), lang)
        if call:
            return f"🗡 {a}: «{esc(call)}» — تیغ شکل واقعی‌اش را گرفت" if fa else f"🗡 {a}: «{esc(call)}» — the blade takes its true form"
        return f"🗡 {a}: «شیکای!» — تیغ شکل واقعی‌اش را گرفت" if fa else f"🗡 {a}: «Shikai!» — the blade takes its true form"
    if k == "mask_on":
        return f"🎭 {a} ماسک هالو را روی صورتش کشید" if fa else f"🎭 {a} pulls the Hollow mask over the face"
    return ""


def dist_line(lang: str, state: dict) -> str:
    return ("📏 فاصله: " if lang == "fa" else "📏 Range: ") + dist_label(lang, state.get("dist", 2))


def events_text(lang: str, events: list) -> str:
    out = []
    for e in events:
        k = e["k"]
        a, d = esc(e.get("a", "")), esc(e.get("d", ""))
        n = fnum(e.get("n", 0), lang)
        if k == "hit":
            kind = e.get("kind", "atk")
            if e.get("gt"):  # Getsuga Tenshō: the gathered wave, named as it leaves the blade
                line = pick(lang, "lg_getsuga", a=a, d=d, n=n)
            elif kind == "hvy" and e.get("mv") and move_name(e["mv"], lang):  # released blade: the real technique name
                line = pick(lang, "lg_hit_move", a=a, d=d, n=n, move=esc(move_name(e["mv"], lang)))
            elif kind == "bala":  # Bala: the 100% hit
                line = (f"💥 بالای {a} بی‌خطا به {d} خورد: {n}" if lang == "fa" else f"💥 {a}'s Bala never misses: {d} takes {n}")
            else:
                line = pick(lang, "lg_hit_" + kind, a=a, d=d, n=n, num=e.get("num", ""), spell=e.get("spell", ""))
            if e.get("chant"):  # a chanted spell is announced before it lands
                line = pick(lang, "lg_chant_line", a=a) + "\n" + line
            if e.get("c"):
                line += " " + pick(lang, "lg_crit")
            if e.get("em", 1) > 1.4:
                line += " 🔺"
            elif e.get("em", 1) < 0.8:
                line += " 🔻"
            if e.get("abs"):
                line += " " + t(lang, "lg_absorbed", n=fnum(e["abs"], lang))
            out.append(line)
        elif k == "fx":
            out.append(t(lang, "lg_fx", a=a, d=d, fx=t(lang, "fx_" + e["fx"])))
        elif k == "dot":
            out.append(t(lang, "lg_dot", d=d, n=n, fx=t(lang, "fx_" + e["fx"])))
        elif k == "unleash":  # Bankai / Resurrección: the blade's name when it is released, a generic line otherwise
            if e.get("mv") and move_name(e["mv"], lang):
                out.append(pick(lang, "lg_unleash_move", a=a, move=esc(move_name(e["mv"], lang))))
            else:
                r = e.get("r")
                key = ("lg_unleash_res" if r in RESURRECCION_RACES
                       else f"lg_unleash_{r}" if r in ("quincy", "fullbringer", "human") else "lg_unleash")
                out.append(pick(lang, key, a=a))
        elif k in ("miss", "dodge", "heal", "drain", "reflect", "double", "skip", "guard", "form_end", "mask_lost",
                   "flash", "shunpo", "hiren", "cero_charge", "charge_break", "chant", "resolve", "guts", "pressure",
                   "gauge_full", "unleash_end", "resurrect", "konpaku", "gather", "blut_vene", "blut_arterie", "negacion", "garganta"):
            out.append(pick(lang, "lg_" + k, a=a, d=d, n=n))
        elif k == "tech":  # canon race technique (data_race_tech)
            out.append(pick(lang, "lg_tech_" + str(e.get("id")), a=a, d=d))
        elif k == "shadow_echo":
            out.append((f"🌑 سایه‌ی احضارشده‌ی {a} به {d} ضربه زد: {n}" if lang == "fa" else f"🌑 {a}'s summoned shadow struck {d}: {n}"))
        elif k == "ks_illusion":
            pt = f" ({e.get('p')}٪ خطا، {e.get('t')} نوبت)" if lang == "fa" else f" ({e.get('p')}% miss, {e.get('t')} turns)"
            out.append((f"👁️ {a} واقعیت را برای {d} منحرف کرد{pt}." if lang == "fa" else f"👁️ {a} distorted reality for {d}{pt}."))
        elif k == "ks_illusion_fail":
            out.append((f"🌫️ توهم {a} روی {d} اثر نکرد." if lang == "fa" else f"🌫️ {a}'s illusion failed to take hold of {d}."))
        elif k == "ks_mirror":
            out.append((f"🪞 {a} دنیای آینه‌ای را فعال کرد." if lang == "fa" else f"🪞 {a} activated Mirror World."))
        elif k == "ks_decoy_hit":
            out.append((f"🌫️ ضربه‌ی {d} به بدل خیالی {a} خورد و بلافاصله پاسخ گرفت!" if lang == "fa" else f"🌫️ {d} struck {a}'s decoy and was answered at once!"))
        elif k == "hog_evo":
            out.append((f"🔮 هوگیوکوی {a} تکامل یافت (مرحله‌ی {n}) — قوی‌تر و سخت‌جان‌تر." if lang == "fa" else f"🔮 {a}'s Hōgyoku evolves (stage {n}) — stronger and harder to kill."))
        elif k == "hog_rebirth":
            out.append((f"🔮 هوگیوکو مرگ را پس زد و {a} دگرگون شد (مرحله‌ی {n})!" if lang == "fa" else f"🔮 The Hōgyoku refused death; {a} metamorphosed (stage {n})!"))
        elif k == "ks_decoy":
            out.append((f"🌫️ بدل توهمی {a} آماده‌ی فریب حمله‌ی بعدی است." if lang == "fa" else f"🌫️ {a}'s illusionary decoy is ready to evade the next strike."))
        elif k in ("ks_dom", "ks_distort"):
            pt = f" ({e.get('p')}٪ خطا، {e.get('t')} نوبت)" if e.get("p") and lang == "fa" else (f" ({e.get('p')}% miss, {e.get('t')} turns)" if e.get("p") else "")
            out.append((f"🌀 {a} حواس {d} را مختل کرد{pt}." if lang == "fa" else f"🌀 {a} distorted {d}'s senses{pt}."))
        elif k == "ks_ultimate":
            out.append((f"☠️ {a}: کانزن سایمین — تسلط کامل بر ادراک میدان نبرد!" if lang == "fa" else f"☠️ {a}: Kanzen Saimin — complete domination of the battlefield's perception!"))
        elif k == "ks_shikai_end":
            out.append((f"🌫️ توهم کیوکا سویگتسو فرو نشست؛ شیکای وارد کول‌داون شد." if lang == "fa" else "🌫️ Kyōka Suigetsu's illusion fades; Shikai enters cooldown."))
        elif k == "fj_phase":
            out.append((f"⚠️ فاز {n} از {e.get('t', '?')} — {a} وارد مرحله‌ی خشم تازه‌ای شد!" if lang == "fa" else f"⚠️ Phase {n}/{e.get('t', '?')} — {a} entered a new state of fury!"))
        elif k == "fj_absolute":
            out.append((f"☠️ ABSOLUTE AWAKENING — باس نهایی تمام قدرت واقعی خود را آزاد کرد!" if lang == "fa" else "☠️ ABSOLUTE AWAKENING — the final boss has released its true power!"))
        elif k == "fj_speed":
            out.append((f"💨 سرعت باس به شکل محسوسی افزایش یافت." if lang == "fa" else "💨 The boss's speed sharply increased."))
        elif k == "fj_hazard":
            out.append((f"🔥 {a} میدان را به منطقه‌ی سوختگی تبدیل کرد." if lang == "fa" else f"🔥 {a} turned the arena into a burning hazard."))
        elif k == "fj_barrier":
            out.append((f"🛡️ {a} سپر تازه‌ای ساخت و زرهش را تقویت کرد." if lang == "fa" else f"🛡️ {a} raised a new barrier and reinforced its armor."))
        elif k == "fj_absolute_strike":
            out.append((f"☠️ حمله‌ی زنجیره‌ای Absolute Awakening آغاز شد!" if lang == "fa" else "☠️ Absolute Awakening unleashes its chained assault!"))
        elif k == "fj_triple":
            out.append((f"⚔️ سه فرمانروای مرحله‌ی پنجم، حمله‌ی زنجیره‌ای خود را آغاز کردند!" if lang == "fa" else "⚔️ The three sovereigns unleash their chained assault!"))
        elif k == "shield_t":
            out.append(pick(lang, "lg_shield_t", a=a, n=n))
        elif k == "release_lost":  # a battered Bankai / Resurrección gets out of hand: each race has its own line
            rk = f"lg_release_lost_{e.get('r') or ''}"
            out.append(pick(lang, rk if rk in (LOCALES.get(lang) or LOCALES["en"]) else "lg_mask_lost", a=a))
        elif k in AB_EVENTS:  # ability families (data_abilities)
            out.append(ab_event_text(lang, e))
        elif k == "nar":  # battle narration (data_narration)
            from data_narration import line as nar_line
            txt = nar_line(e, lang)
            if txt:
                out.append(f"<i>{esc(txt)}</i>")
        elif k == "speed":  # fight start: the speed gap and what it means for dodging
            r = e.get("r", 1.0)
            if r < 1.05:
                out.append("💨 سرعت دو طرف برابره؛ شانس جاخالی پایه ۵٪." if lang == "fa"
                           else "💨 Both sides are equally fast: base dodge 5%.")
            else:
                rs = (f"{r:.2f}".rstrip("0").rstrip("."))
                out.append(f"💨 {a} {fnum(rs, lang)} برابر سریع‌تر از {d}ه؛ {fnum(e.get('p', 5), lang)}٪ از ضربه‌های {d} رو جاخالی می‌ده." if lang == "fa"
                           else f"💨 {a} is {rs}x faster than {d}: dodges {e.get('p', 5)}% of {d}'s blows.")
        elif k == "second_guard":  # duel opening: the side that answers starts behind a thin guard
            out.append(f"🛡 {a} در حالت پاسخ ایستاده: سپر {n} — ضربه‌ی اول حریف فقط نیمه‌جان است." if lang == "fa"
                       else f"🛡 {a} stands ready to answer: a {n} guard — the opener's first blow lands at half power.")
        elif k in ("move", "retreat", "outrange", "knock", "side", "side_off", "side_no"):  # distance (فاصله) events
            out.append(dist_event_text(lang, e))
        elif k == "bu":  # blade ultimate
            out.append(f"👑 {a}: <b>{e.get('fa' if lang == 'fa' else 'en')}</b>!")
        elif k == "bt":  # blade technique
            out.append(pick(lang, "lg_bt_" + str(e.get("kind")), a=a))
        elif k == "gen":  # general skill (any race)
            out.append(pick(lang, "lg_gen_" + str(e.get("skill")), a=a, n=n))
        elif k == "bount_seal":
            out.append(pick(lang, "lg_bount_seal", a=a, d=d))
        elif k == "shield":
            out.append(t(lang, "lg_shield", a=a, n=n, num=e.get("num", ""), spell=e.get("spell", "")))
        elif k == "form":
            race_key = f"lg_form{e['n']}_{e.get('r', '')}"
            out.append(t(lang, race_key if race_key in (LOCALES.get(lang) or LOCALES["en"]) or race_key in LOCALES["en"] else "lg_form" + str(e["n"]), a=a))
        elif k == "potion":
            out.append(t(lang, "lg_potion_" + e["kind"], a=a, n=n))
    return "\n".join(out)


def fighter_line(lang: str, f: dict, icon: str) -> str:
    from panel_ui import card, edge_warning
    fx = "".join(FX_ICON.get(x["k"], "") for x in f["fx"] if x["t"] > 0)
    if f["shield"] > 0:
        fx += "🛡"
    if f["form"]["on"]:
        fx += "✨"
    x = f.get("x") or {}
    for key, ic in (("charge", "⚠️"), ("flash", "🌀"), ("chant", "📿")):  # charge: Cero gathering, answer it now
        if x.get(key):
            fx += ic
    if x.get("buff_t", 0) > 0:
        fx += "💢"
    warn = edge_warning(lang, f)
    return card(lang, f, icon, chips=((fx + "  " if fx else "") + warn).strip())


def battle_text(lang: str, state: dict, events: list = None, title: str = "") -> str:
    parts = [title] if title else []
    parts.append(fighter_line(lang, state["a"], "🧑"))
    parts.append(fighter_line(lang, state["b"], "👹"))
    parts.append(t(lang, "bt_turn", n=fnum(state["turn"], lang)) + "  " + dist_line(lang, state))
    cur = state.get("cur") if state.get("cur") in ("a", "b") else "a"
    fc = state[cur]
    if KIDO_CD_LINE and not fc.get("ai") and isinstance(fc.get("kido"), dict) and fc["kido"].get("had") is not None:
        from engine import kido_cooling  # lazy: render is imported by engine-free modules too
        cool = kido_cooling(fc)[:4]
        if cool:
            tags = "، ".join(f"{n}({fnum(left, lang)})" for _, n, left in cool) if lang == "fa" else ", ".join(f"{n} ({left})" for _, n, left in cool)
            parts.append(t(lang, "bt_kido_cd", list=tags))
    shown = events if events is not None else state.get("last", [])
    if state.get("turn") == 1 and state.get("intro") and not any(x.get("k") in ("speed", "pressure") for x in shown):
        shown = list(state["intro"]) + list(shown)  # opening of a fight: the speed gap and the spirit pressure
    ev = events_text(lang, shown)
    if ev:
        parts.append(ev)
    return "\n\n".join(parts)


def epithet_lines(lang: str, d: dict) -> list:
    b = BOSS_BY_ID.get(d.get("boss_id"))
    if not b:
        return []
    out = [f"<i>{esc(b['epi_fa' if lang == 'fa' else 'epi_en'])}</i>"]
    if d.get("trait") and ("boss_trait_" + d["trait"]) in LOCALES["en"]:
        out.append(t(lang, "boss_trait_" + d["trait"]))
    return out


def boss_text(lang: str, d: dict, result: dict = None) -> str:
    name = d["name_fa" if lang == "fa" else "name_en"]
    ph = 1 if d["hp"] > d["max_hp"] * .6 else 2 if d["hp"] > d["max_hp"] * .3 else 3
    hp = max(0, d["hp"])
    lines = [f"⚔️ <b>𝖲𝖤𝖭𝖪𝖠</b> | <b>{t(lang, 'boss_title')}</b>\n━━━━━━━━━━━━━━"]
    if d.get("active") and not d.get("hits"):  # freshly torn open: a short, dramatic arrival line
        lines.append("<i>" + t(lang, "boss_arrive_" + str(sum(map(ord, d.get("boss_id", "x"))) % 6)) + "</i>\n")
    lines += [f"👹 <b>{esc(name)}</b> — {t(lang, 'lbl_level')} {fnum(d['level'], lang)}",
              *epithet_lines(lang, d),
              f"❤️ {bar(hp, d['max_hp'], 14)}\n{fnum(hp, lang)}/{fnum(d['max_hp'], lang)}  ({fnum(max(0, hp * 100 // max(1, d['max_hp'])), lang)}{'٪' if lang == 'fa' else '%'})",
              t(lang, "boss_ph_" + str(ph))]
    if d.get("active"):
        lines.append(t(lang, "boss_left", m=fnum(max(0, int(d["expires_at"] - time.time())) // 60 + 1, lang)))
        combo = int(d.get("combo", 0))
        if combo >= 2 and time.time() - float(d.get("last_at", 0)) <= 10:
            lines.append(t(lang, "boss_combo", n=fnum(combo, lang), p=fnum(combo * 5, lang)))
        ad = d.get("adapt") or {}
        if ad and float(ad.get("until", 0)) > time.time():
            lines.append(t(lang, "boss_burst_state", n=esc(ad.get("n", "?"))))
        top = sorted(d.get("contrib", {}).items(), key=lambda kv: -kv[1])[:3]
        if top:
            lines.append(t(lang, "boss_hits", n=fnum(d.get("hits", 0), lang)) + " · " + t(lang, "boss_fighters", n=fnum(len(d.get("contrib", {})), lang)))
            names = d.get("nm") or {}
            for i, (uid, dmg) in enumerate(top):
                lines.append(f"{['🥇', '🥈', '🥉'][i]} {esc(names.get(str(uid), '?'))} — {fnum(dmg, lang)}")
        feed = (d.get("feed") or [])[::-1]
        if feed:
            lines.append("\n" + t(lang, "boss_feed"))
            for e in feed:
                lines.append(f"{'✨' if e.get('s') else '💥' if e.get('c') else '🗡️'} {esc(e['n'])} — {fnum(e['d'], lang)}")
        lines.append("\n" + t(lang, "boss_hint"))
    if result:
        lines.append(t(lang, "boss_dead" if result["killed"] else "boss_escaped"))
        for i, r in enumerate(result["rows"][:5]):
            lines.append(f"{['🥇', '🥈', '🥉', '4.', '5.'][i]} {esc(r['name'])} — {fnum(r['dmg'], lang)} ({fnum(round(r['share'] * 100), lang)}{'٪' if lang == 'fa' else '%'}) +{fnum(r['xp'], lang)} {t(lang, 'xp_word')}" + (" 🎯" if r["last"] else ""))
        if result["enraged"]:
            lines.append(t(lang, "boss_enrage_bonus"))
    return "\n".join(lines)
