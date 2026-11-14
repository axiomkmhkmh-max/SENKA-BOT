"""Inner World (دنیای درون) UI: the weekly scene panel and the choice buttons.

The state and rules live in service_extras (inner_state / inner_choose); this module only renders them and
registers the two callbacks the Mind panel sends: "inr" (show the next scene) and "inc" (answer it).
Without these handlers the button did nothing, because the dispatcher silently drops unknown codes.
"""
from data_extras import INNER
from fmt import nm
from i18n import esc, fnum
from service_extras import inner_choose, inner_state
from service_player import get_char
from ui import SEP, Out, action, head, nav


def T(ctx, fa, en):
    return fa if ctx.lang == "fa" else en


def _blade(ch: dict, lang: str) -> str:
    return esc(nm(ch.get("weapon_id"), lang) if ch and ch.get("weapon_id") else T_BLADE_FALLBACK[lang])


T_BLADE_FALLBACK = {"fa": "تیغه‌ات", "en": "your blade"}


def _panel(ctx, st: dict, ch: dict):
    L = ctx.lang
    if st["scene"] is None:
        body = ctx.t("inr_none").format(cap=st["cap"])
        return Out(head(ctx, "ttl_inr") + body, [nav(ctx, ("mg", "grow"))])
    blade = _blade(ch, L)
    scene = INNER[st["scene"]]
    text = scene["t"][0 if L == "fa" else 1].format(w=f"<b>{blade}</b>")
    body = (ctx.t("inr_intro").format(left=fnum(st["left"], L), cap=fnum(st["cap"], L))
            + "\n" + SEP + "\n" + text)
    i = 0 if L == "fa" else 1
    rows = [[(scene["a"][i], "inc", f"{st['scene']}:a"), (scene["b"][i], "inc", f"{st['scene']}:b")],
            nav(ctx, ("mg", "grow"))]
    return Out(head(ctx, "ttl_inr") + body, rows)


@action("inr")
async def inner_panel(ctx, arg):
    st = await inner_state(ctx.uid)
    ch = await get_char(ctx.uid)
    return _panel(ctx, st, ch)


@action("inc")
async def inner_pick(ctx, arg):
    try:
        scene_s, choice = (arg or "").split(":", 1)
        scene = int(scene_s)
    except ValueError:
        return Out(alert=ctx.t("inr_e_bad"))
    status, res = await inner_choose(ctx.uid, scene, choice)
    if status != "ok":
        msgs = {"limit": ctx.t("inr_e_limit"), "stale": ctx.t("inr_e_stale"), "wait": T(ctx, "⏳ یک لحظه صبر کن.", "⏳ One moment."),
                "bad": ctx.t("inr_e_bad")}
        return Out(alert=msgs.get(status, ctx.t("inr_e_bad")))
    L = ctx.lang
    ch = await get_char(ctx.uid)
    blade = _blade(ch, L)
    i = 0 if L == "fa" else 1
    outcome = INNER[scene][choice][2 + i]
    lines = [outcome.format(w=f"<b>{blade}</b>")]
    if res.get("bond"):
        lines.append(ctx.t("inr_bond").format(n=fnum(res["bond"], L)))
    if res.get("xp"):
        lines.append(T(ctx, f"📈 تجربه: +{fnum(res['xp'], L)}", f"📈 XP: +{fnum(res['xp'], L)}"))
    if res.get("buff"):
        key, pct, minutes = res["buff"]
        lines.append(ctx.t("inr_buff").format(key=ctx.t("buff_" + key), pct=fnum(round(pct * 100), L), m=fnum(minutes, L)))
    body = "\n".join(lines)
    st = await inner_state(ctx.uid)
    rows = []
    if st["scene"] is not None:
        rows.append([(ctx.t("b_inr_again"), "inr", "")])
    rows.append(nav(ctx, ("mg", "grow")))
    return Out(head(ctx, "ttl_inr") + body, rows)
