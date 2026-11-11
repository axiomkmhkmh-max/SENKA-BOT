"""Allegiance panel: Gotei division / Espada number / Wandenreich order / Karakura allies."""
import time

from data_bleach import DIV_BY_ID, FACTION_OF, FACTION_TITLE, divisions_for
from database import col, game_settings
from handlers_world import bonus_line
from i18n import esc, fnum
from service_player import add_coins, get_char
from ui import Out, action, chunk, head, nav


def _name(d, L):
    return f"{d['icon']} {d['fa' if L == 'fa' else 'en']}"


def _bonus_text(ctx, d):
    return bonus_line(ctx, d["bonus"])


@action("div")
async def division(ctx, arg):
    ch = await get_char(ctx.uid)
    st = await game_settings()
    L = ctx.lang
    faction = FACTION_OF.get(ch["race"], "allies")
    title = FACTION_TITLE[faction][0 if L == "fa" else 1]
    cur = DIV_BY_ID.get(ch.get("division") or "")
    lines = [f"<b>{title}</b>"]
    if ch["level"] < int(st["div_min_level"]):
        return Out(head(ctx, "ttl_div") + "\n".join(lines) + "\n" + ctx.t("div_e_level", n=fnum(st["div_min_level"], L)), [nav(ctx, ("mg", "grow"))])
    if cur:
        lines.append(ctx.t("div_cur", name=_name(cur, L), bonus=_bonus_text(ctx, cur)))
        lines.append(f"<i>{esc(cur['desc_fa' if L == 'fa' else 'desc_en'])}</i>")
        lines.append(ctx.t("div_change", cost=fnum(st["div_change_cost"], L)))
    else:
        lines.append(ctx.t("div_none", faction=title))
    opts = [(_name(d, L) + (" ✅" if cur and d["_id"] == cur["_id"] else ""), "dvi", d["_id"]) for d in divisions_for(ch["race"])]
    rows = chunk(opts, 2) + [nav(ctx, ("mg", "grow"))]
    return Out(head(ctx, "ttl_div") + "\n".join(lines), rows)


@action("dvi")
async def division_info(ctx, arg):
    d = DIV_BY_ID.get(arg)
    ch = await get_char(ctx.uid)
    L = ctx.lang
    if not d or d["faction"] != FACTION_OF.get(ch["race"], "allies"):
        return Out(alert=ctx.t("div_e_bad"))
    text = f"<b>{_name(d, L)}</b>\n{_bonus_text(ctx, d)}\n<i>{esc(d['desc_fa' if L == 'fa' else 'desc_en'])}</i>"
    rows = [[(ctx.t("b_div_pick"), "dvy", d["_id"])], nav(ctx, ("div", ""))]
    return Out(head(ctx, "ttl_div") + text, rows)


@action("dvy")
async def division_pick(ctx, arg):
    d = DIV_BY_ID.get(arg)
    ch = await get_char(ctx.uid)
    st = await game_settings()
    L = ctx.lang
    if not d or d["faction"] != FACTION_OF.get(ch["race"], "allies"):
        return Out(alert=ctx.t("div_e_bad"))
    if ch["level"] < int(st["div_min_level"]):
        return Out(alert=ctx.t("div_e_level", n=fnum(st["div_min_level"], L)))
    if ch.get("division") == arg:
        return Out(alert=ctx.t("div_e_same"))
    first = not ch.get("division")
    cost = 0 if first else int(st["div_change_cost"])
    if cost and not await add_coins(ctx.uid, -cost, "division"):
        return Out(alert=ctx.t("div_e_funds", n=fnum(cost, L)))
    await col("characters").update_one({"user_id": ctx.uid}, {"$set": {"division": arg, "division_at": int(time.time())}})
    return Out(head(ctx, "ttl_div") + ctx.t("div_ok", name=_name(d, L), bonus=_bonus_text(ctx, d)), [nav(ctx, ("div", ""))])


# ---- Hollowfication: a Shinigami can become a Visored (the race is locked at registration) --------------------
@action("hlf")
async def hollowfy(ctx, arg):
    ch = await get_char(ctx.uid)
    st = await game_settings()
    L = ctx.lang
    need, cost, chance = int(st["hlf_min_level"]), int(st["hlf_cost"]), float(st["hlf_chance"])
    back = [nav(ctx, ("mg", "grow"))]
    if ch["race"] == "visored":
        return Out(head(ctx, "ttl_hlf") + ctx.t("hlf_done"), back)
    if ch["race"] != "shinigami":
        return Out(head(ctx, "ttl_hlf") + ctx.t("hlf_only"), back)
    text = ctx.t("hlf_body", n=fnum(need, L), cost=fnum(cost, L), pct=fnum(round(chance * 100), L))
    if ch["level"] < need:
        return Out(head(ctx, "ttl_hlf") + text + "\n\n" + ctx.t("hlf_e_level", n=fnum(need, L)), back)
    return Out(head(ctx, "ttl_hlf") + text, [[(ctx.t("b_hlf_go"), "hlg", "")]] + back)


@action("hlg")
async def hollowfy_go(ctx, arg):
    import random
    from data_crafting import evo_gate_stage
    from database import try_cooldown
    from service_combat import active_pve
    ch = await get_char(ctx.uid)
    st = await game_settings()
    L = ctx.lang
    need, cost, chance = int(st["hlf_min_level"]), int(st["hlf_cost"]), float(st["hlf_chance"])
    if ch["race"] != "shinigami" or ch["level"] < need:
        return Out(alert=ctx.t("hlf_e_level", n=fnum(need, L)))
    if await active_pve(ctx.uid):
        return Out(alert=ctx.t("evo_e_busy"))
    wait = await try_cooldown(f"hlf:{ctx.uid}", 6 * 3600)
    if wait:
        return Out(alert=ctx.t("wait_s", n=wait))
    if not await add_coins(ctx.uid, -cost, "hollowfication"):
        return Out(alert=ctx.t("div_e_funds", n=fnum(cost, L)))
    if random.random() < chance:
        await col("characters").update_one({"user_id": ctx.uid, "race": "shinigami"}, {"$set": {"race": "visored", "division": None, "evo": evo_gate_stage("visored", ch["level"])}})
        return Out(head(ctx, "ttl_hlf") + ctx.t("hlf_ok"), [nav(ctx, ("div", ""))])
    await add_coins(ctx.uid, cost // 2, "hollowfication_refund")
    return Out(head(ctx, "ttl_hlf") + ctx.t("hlf_fail", n=fnum(cost // 2, L)), [nav(ctx, ("mg", "grow"))])
