"""Text rendering for battles and bosses (language-parametrised, no I/O)."""
import time

import random

from data_bosses import BOSS_BY_ID
from i18n import LOCALES, bar, esc, fnum, t

FX_ICON = {"burn": "🔥", "poison": "☠️", "bleed": "🩸", "shock": "⚡", "weaken": "🔻", "fear": "😨"}


def both(mode: str, fn) -> str:
    if mode == "both":
        return fn("fa") + "\n\n" + "┄" * 10 + "\n\n" + fn("en")
    return fn(mode if mode in ("fa", "en") else "en")


def glang(g: dict) -> str:
    """Language mode of a group: only an explicit admin choice (incl. bilingual) is kept; otherwise one language."""
    g = g or {}
    if g.get("lang_set") and g.get("lang") in ("fa", "en", "both"):
        return g["lang"]
    return g.get("auto_lang") if g.get("auto_lang") in ("fa", "en") else "fa"


def gl(mode: str, fa: str, en: str) -> str:
    return fa if mode == "fa" else en if mode == "en" else f"{en} / {fa}"


def pick(lang: str, key: str, **kw) -> str:
    """Return one random flavour variant: key, key_2, key_3 ... (falls back to key)."""
    table = LOCALES.get(lang) or LOCALES["en"]
    keys = [key] + [f"{key}_{i}" for i in range(2, 9) if f"{key}_{i}" in table]
    return t(lang, random.choice(keys), **kw)


def events_text(lang: str, events: list) -> str:
    out = []
    for e in events:
        k = e["k"]
        a, d = esc(e.get("a", "")), esc(e.get("d", ""))
        n = fnum(e.get("n", 0), lang)
        if k == "hit":
            kind = e.get("kind", "atk")
            line = pick(lang, "lg_hit_" + kind, a=a, d=d, n=n, num=e.get("num", ""), spell=e.get("spell", ""))
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
        elif k in ("miss", "dodge", "heal", "drain", "reflect", "double", "skip", "guard", "form_end"):
            out.append(pick(lang, "lg_" + k, a=a, d=d, n=n))
        elif k == "shield":
            out.append(t(lang, "lg_shield", a=a, n=n, num=e.get("num", ""), spell=e.get("spell", "")))
        elif k == "form":
            race_key = f"lg_form{e['n']}_{e.get('r', '')}"
            out.append(t(lang, race_key if race_key in (LOCALES.get(lang) or LOCALES["en"]) or race_key in LOCALES["en"] else "lg_form" + str(e["n"]), a=a))
        elif k == "potion":
            out.append(t(lang, "lg_potion_" + e["kind"], a=a, n=n))
    return "\n".join(out)


def fighter_line(lang: str, f: dict, icon: str) -> str:
    fx = "".join(FX_ICON.get(x["k"], "") for x in f["fx"] if x["t"] > 0)
    if f["shield"] > 0:
        fx += "🛡"
    if f["form"]["on"]:
        fx += "✨"
    return (f"{icon} <b>{esc(f['name'])}</b> {fnum(f['level'], lang)} {fx}\n"
            f"❤️ {bar(f['hp'], f['max_hp'])} {fnum(f['hp'], lang)}/{fnum(f['max_hp'], lang)}\n"
            f"🔮 {fnum(f['re'], lang)}/{fnum(f['max_re'], lang)}")


def battle_text(lang: str, state: dict, events: list = None, title: str = "") -> str:
    parts = [title] if title else []
    parts.append(fighter_line(lang, state["a"], "🧑"))
    parts.append(fighter_line(lang, state["b"], "👹"))
    parts.append(t(lang, "bt_turn", n=fnum(state["turn"], lang)))
    ev = events_text(lang, events if events is not None else state.get("last", []))
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
              f"❤️ {bar(hp, d['max_hp'], 14)}\n{fnum(hp, lang)}/{fnum(d['max_hp'], lang)}  ({max(0, hp * 100 // max(1, d['max_hp']))}%)",
              t(lang, "boss_ph_" + str(ph))]
    if d.get("active"):
        lines.append(t(lang, "boss_left", m=fnum(max(0, int(d["expires_at"] - time.time())) // 60 + 1, lang)))
        combo = int(d.get("combo", 0))
        if combo >= 2 and time.time() - float(d.get("last_at", 0)) <= 10:
            lines.append(t(lang, "boss_combo", n=fnum(combo, lang), p=fnum(combo * 5, lang)))
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
            lines.append(f"{['🥇', '🥈', '🥉', '4.', '5.'][i]} {esc(r['name'])} — {fnum(r['dmg'], lang)} ({r['share'] * 100:.0f}%) +{fnum(r['xp'], lang)} XP" + (" 🎯" if r["last"] else ""))
        if result["enraged"]:
            lines.append(t(lang, "boss_enrage_bonus"))
    return "\n".join(lines)
