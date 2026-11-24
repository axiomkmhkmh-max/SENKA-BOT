"""Duel (PvP) arena card: the group panel two players fight on. Pure rendering, no I/O.

Layout (one language per message):
    header (mode + VS line) -> both fighter cards -> arena strip (round, gap) -> last moves -> turn footer
The final card adds the winner banner, the reason the duel ended and a per-side battle report (see tally)."""
import random
import time

from data_misc import FORMS
from data_races import RACES
from i18n import esc, fnum, t
from render import dist_label, events_text

SIDE = {"a": "🔴", "b": "🔵"}
SEP = "━━━━━━━━━━━━━━━━━━"
BAR_N = 12
LOG_LINES = 14   # the newest moves shown; older ones stay in the state but would push the panel past Telegram's limit

RACE_EMBLEM = {"shinigami": "⚔️", "quincy": "🏹", "hollow": "🕳️", "arrancar": "💀", "fullbringer": "🔗",
               "human": "🧍", "visored": "🎭"}

# the race's full release (the spirit gauge's "gx"), as players call it
RELEASE = {"shinigami": ("بانکای", "Bankai"), "visored": ("بانکای", "Bankai"), "quincy": ("فولشتندیگ", "Vollständig"),
           "hollow": ("رزورکسیون", "Resurrección"), "arrancar": ("رزورکسیون", "Resurrección"),
           "fullbringer": ("فول‌برینگ کامل", "Complete Fullbring"), "human": ("بیداری روح", "Soul Awakening")}


# a line for the winner, by race (original lines in the Bleach spirit)
WIN_LINES = {
    "shinigami": (("«تیغم هنوز تشنه‌ست؛ دفعه‌ی بعد آماده‌تر بیا.»", "\"My blade is still thirsty. Come back stronger.\""),
                  ("«روح تو سنگین بود، ولی تیغ من سنگین‌تر.»", "\"Your soul was heavy. My blade was heavier.\"")),
    "visored": (("«ماسک رو فقط برای کسایی می‌زنم که ارزشش رو دارن.»", "\"I only wear the mask for those worth it.\""),),
    "quincy": (("«هر تیرم یه حکم بود.»", "\"Every arrow was a verdict.\""),
               ("«ریشی این دنیا مال منه.»", "\"The reishi of this world answers to me.\"")),
    "hollow": (("«گرسنگی‌ام هنوز تموم نشده...»", "\"My hunger is not over yet...\""),),
    "arrancar": (("«ناامیدی؛ این تنها چیزی بود که نشونم دادی.»", "\"Despair. That is all you showed me.\""),
                 ("«قدرت واقعی رو تازه دیدی.»", "\"Now you've seen true power.\"")),
    "fullbringer": (("«پیوندم با این دنیا محکم‌تر از توئه.»", "\"My bond with this world runs deeper than yours.\""),),
    "human": (("«روحم هنوز روشنه.»", "\"My soul still burns bright.\""),),
}


def _L(lang, pair):
    return pair[0] if lang == "fa" else pair[1]


def _pct(cur, mx):
    return 0 if mx <= 0 else max(0, min(100, int(round(100 * cur / mx))))


def gbar(cur, mx, n=BAR_N, full="▰", empty="▱"):
    k = 0 if mx <= 0 else max(0, min(n, int(round(n * cur / mx))))
    if cur > 0 and k == 0:  # alive is never an empty bar
        k = 1
    return full * k + empty * (n - k)


def race_name(lang, race):
    r = RACES.get(race) or {}
    return r.get("name_fa" if lang == "fa" else "name_en", race or "")


def release_name(lang, race):
    return _L(lang, RELEASE.get(race) or RELEASE["human"])


def _heart(p):
    return "❤️" if p > 60 else "🧡" if p > 30 else "💔"


def _chips(lang, f):
    """Short status tags under a fighter: barrier, lives, released forms, charges, damage over time."""
    fa = lang == "fa"
    x = f.get("x") or {}
    out = []
    if (f.get("form") or {}).get("on") and not x.get("awake", 0) > 0:  # an active release has its own line on the card
        forms = FORMS.get(f.get("race")) or FORMS["human"]
        out.append("✨ " + _L(lang, forms[0]))
    if f.get("shield", 0) > 0:
        out.append(f"🛡 {fnum(int(f['shield']), lang)}")
    if f.get("lives", 0) > 0:
        out.append(("💮 کونپاکو ×" if fa else "💮 Konpaku ×") + fnum(f["lives"], lang))
    if x.get("charge"):
        out.append("⚠️ " + ("سرو در حال شارژ" if fa else "Cero charging"))
    if x.get("chant"):
        out.append("📿 " + ("ورد خوانده شد" if fa else "chant ready"))
    if x.get("flash"):
        out.append("🌀 " + ("در حرکت" if fa else "afterimage"))
    if x.get("buff_t", 0) > 0:
        out.append("💢 " + ("تقویت" if fa else "boosted"))
    for e in f.get("fx") or []:
        if e.get("t", 0) > 0:
            label = t(lang, "fx_" + e["k"])
            if label and not label.startswith("fx_"):
                out.append(label)
    return " · ".join(out)


def fighter_card(lang, f, side, tag=""):
    fa = lang == "fa"
    x = f.get("x") or {}
    hp, mhp = int(f["hp"]), int(f["max_hp"])
    p = _pct(hp, mhp)
    emblem = RACE_EMBLEM.get(f.get("race"), "⚔️")
    lv = ("سطح " if fa else "Lv ") + fnum(f["level"], lang)
    lines = [f"{SIDE[side]} <b>{esc(f['name'])}</b>{tag}",
             f"{emblem} <i>{esc(race_name(lang, f.get('race')))}</i> · {lv}",
             f"{_heart(p)} {gbar(hp, mhp)} <b>{fnum(p, lang)}٪</b>" if fa else f"{_heart(p)} {gbar(hp, mhp)} <b>{p}%</b>",
             f"      <code>{fnum(hp, lang)} / {fnum(mhp, lang)}</code>",
             f"🔮 {gbar(f['re'], f['max_re'])} <code>{fnum(int(f['re']), lang)}</code>"]
    g = int(x.get("gauge", 0) or 0)
    rel = release_name(lang, f.get("race"))
    if x.get("awake", 0) > 0:
        lines.append(f"👑 <b>{esc(rel)}</b> " + ("فعاله!" if fa else "is active!"))
    elif g >= 100:
        lines.append(f"🔥 <b>{esc(rel)}</b> " + ("آماده‌ست! ⚡" if fa else "is ready! ⚡"))
    elif g > 0:
        lines.append(f"🔥 {gbar(g, 100, 8, '▮', '▯')} {fnum(g, lang)}{'٪' if fa else '%'} <i>{esc(rel)}</i>")
    chips = _chips(lang, f)
    if chips:
        lines.append(f"<i>{chips}</i>")
    return "\n".join(lines)


def arena_line(lang, state):
    """The gap between the fighters as a strip: 🔴 ⚔️ 🔵 at contact, more road the further they stand."""
    fa = lang == "fa"
    d = int(state.get("dist", 2))
    strip = "🔴 💥 🔵" if d == 0 else "🔴 " + "┈" * (2 * d + 1) + " 🔵"
    rnd = ("راند " if fa else "Round ") + fnum(state.get("turn", 1), lang)
    return f"🔁 <b>{rnd}</b> · 📏 {dist_label(lang, d)}\n{strip}"


def _log(lang, state, events):
    shown = events if events is not None else state.get("last", [])
    if state.get("turn") == 1 and state.get("intro") and not any(x.get("k") in ("speed", "pressure") for x in shown):
        shown = list(state["intro"]) + list(shown)
    txt = events_text(lang, shown)
    if not txt:
        return ""
    lines = [ln for ln in txt.split("\n") if ln.strip()]
    if len(lines) > LOG_LINES:
        lines = lines[-LOG_LINES:]
    head = "📜 <b>" + ("آخرین حرکات" if lang == "fa" else "Last moves") + "</b>"
    quote = "<blockquote expandable>" if len(lines) > 5 else "<blockquote>"
    return f"{head}\n{quote}" + "\n".join(lines) + "</blockquote>"


def _edge_lines(lang, state):
    """Drama under the arena: who is on the edge, who has a release ready."""
    fa = lang == "fa"
    out = []
    for s in ("a", "b"):
        f = state[s]
        if 0 < f["hp"] <= f["max_hp"] * 0.2:
            out.append(f"⚠️ {SIDE[s]} <b>{esc(f['name'])}</b> " + ("روی لبه‌ی سقوطه!" if fa else "is on the edge!"))
    return out


def header(lang, doc):
    fa = lang == "fa"
    st = doc["state"]
    mode = t(lang, "duel_ranked" if doc.get("ranked") else "duel_friendly")
    title = ("⚔️ <b>𝗦𝗘𝗡𝗞𝗔 · دوئل " if fa else "⚔️ <b>𝗦𝗘𝗡𝗞𝗔 · ") + (f"{mode}</b>" if fa else f"{mode} Duel</b>")
    if doc.get("ranked"):
        title += " 🏅"
    vs = f"🔴 <b>{esc(st['a']['name'])}</b>  ⚡ 𝗩𝗦 ⚡  <b>{esc(st['b']['name'])}</b> 🔵"
    return f"{title}\n{vs}\n{SEP}"


def turn_footer(lang, doc, now=None):
    fa = lang == "fa"
    st = doc["state"]
    cur = st["cur"] if st.get("cur") in ("a", "b") else "a"
    left = max(0, int(doc.get("deadline", 0) or 0) - int(now or time.time()))
    line = (f"🎯 نوبت {SIDE[cur]} <b>{esc(st[cur]['name'])}</b>" if fa else f"🎯 {SIDE[cur]} <b>{esc(st[cur]['name'])}</b>'s move")
    if left:
        mm, ss = divmod(left, 60)
        line += f" · ⏳ {fnum(mm, lang)}:{fnum(ss // 10, lang)}{fnum(ss % 10, lang)}"
    afk = (doc.get("timeouts") or {}).get(cur, 0)
    if afk:
        line += "\n" + ("💤 یک نوبت را از دست دادی (سپر خودکار) — نوبت بعدی هم از دست بروی = باخت" if fa
                        else "💤 You missed a turn (auto-guard) — miss the next one and you lose the duel")
    return line


def panel_text(lang, doc, events, final_text=None):
    st = doc["state"]
    done = final_text is not None
    tags = {"a": "", "b": ""}
    cur = st.get("cur")
    if done:
        w = st.get("winner")
        if w in ("a", "b"):
            tags[w], tags["b" if w == "a" else "a"] = " 🏆", " ☠️"
    elif cur in ("a", "b"):
        tags[cur] = " ◀️"
    parts = [header(lang, doc),
             fighter_card(lang, st["a"], "a", tags["a"]),
             arena_line(lang, st),
             fighter_card(lang, st["b"], "b", tags["b"])]
    edge = _edge_lines(lang, st) if not done else []
    if edge:
        parts.append("\n".join(edge))
    log = _log(lang, st, events)
    if log:
        parts.append(log)
    parts.append(SEP)
    parts.append(final_text if done else turn_footer(lang, doc))
    return "\n\n".join(parts)


# ---- battle report -------------------------------------------------------------------------------------------------
def _blank():
    return {"dmg": 0, "best": 0, "crit": 0, "hits": 0}


def tally(state, events):
    """Adds this turn's landed blows to state['tally'] (per side: total damage, biggest hit, crits, hits).
    Attackers are matched by name; when both fighters share a name the blow cannot be told apart and is skipped."""
    tl = state.setdefault("tally", {"a": _blank(), "b": _blank()})
    na, nb = state["a"]["name"], state["b"]["name"]
    for e in events or []:
        if e.get("k") != "hit" or not e.get("n"):
            continue
        a = e.get("a")
        side = "a" if a == na and a != nb else "b" if a == nb and a != na else None
        if side is None:
            continue
        s = tl[side]
        n = int(e["n"])
        s["dmg"] += n
        s["hits"] += 1
        s["best"] = max(s["best"], n)
        if e.get("c"):
            s["crit"] += 1
    return tl


def report_lines(lang, state):
    fa = lang == "fa"
    tl = state.get("tally")
    if not tl:
        return []
    out = ["📊 <b>" + ("کارنامه‌ی نبرد" if fa else "Battle report") + "</b> · ⏱ "
           + (f"{fnum(state.get('turn', 1), lang)} راند" if fa else f"{state.get('turn', 1)} rounds")]
    for s in ("a", "b"):
        r = tl.get(s) or _blank()
        out.append(f"{SIDE[s]} <b>{esc(state[s]['name'])}</b>\n"
                   f"   💥 {fnum(r['dmg'], lang)} · 🎯 {fnum(r['best'], lang)} · ✨ {fnum(r['crit'], lang)}")
    out.append("<i>" + ("💥 کل آسیب · 🎯 بزرگ‌ترین ضربه · ✨ کریتیکال" if fa else "💥 total damage · 🎯 biggest hit · ✨ crits") + "</i>")
    return out


def winner_banner(lang, doc, rng=random):
    """The top of the final card: who won, a line in their voice, and why the duel ended."""
    fa = lang == "fa"
    st = doc["state"]
    w = st.get("winner")
    if w not in ("a", "b"):
        return [t(lang, "duel_draw")]
    loser = "b" if w == "a" else "a"
    wf = st[w]
    lines = [f"🏆 {SIDE[w]} <b>{esc(wf['name'])}</b> " + ("پیروز دوئل شد!" if fa else "wins the duel!")]
    pool = WIN_LINES.get(wf.get("race")) or WIN_LINES["human"]
    lines.append(f"<i>{esc(_L(lang, rng.choice(pool)))}</i>")
    end = st.get("end")
    if end == "ff":
        lines.append(f"🏳️ {esc(st[loser]['name'])} " + ("تسلیم شد." if fa else "yielded."))
    elif end == "afk":
        lines.append(f"💤 {esc(st[loser]['name'])} " + ("دو نوبت پشت‌سرهم غایب بود." if fa else "missed two turns in a row."))
    else:
        p = _pct(wf["hp"], wf["max_hp"])
        lines.append((f"❤️ با {fnum(p, lang)}٪ جان باقی‌مانده" if fa else f"❤️ Finished with {p}% HP left")
                     + (" — 🔥 پیروزی تمیز!" if fa and p >= 70 else " — 🔥 a flawless finish!" if p >= 70
                        else (" — 😮‍💨 لب مرز!" if fa else " — 😮‍💨 by a hair!") if p <= 15 else ""))
    return lines
