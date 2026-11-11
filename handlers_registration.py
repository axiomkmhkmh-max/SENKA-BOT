"""Onboarding: language -> name -> identity -> race -> 10 points -> zanpakuto."""
import time

from data_items import ALL
from data_races import RACES, STAT_ICON, STATS
from fmt import item_card, nm, race_name
from i18n import esc, fnum
from security import allow, clean_name
from service_player import (finish_registration, name_taken, reg_get, reg_set, set_lang, starter_choices, user_lang)
from service_economy import inv_add
from database import col, game_settings
from ui import Out, action, head, markup

POTION = next(i for i, x in ALL.items() if x.get("effect") and x["effect"]["type"] == "hp" and x["rarity"] == "Common")


def lang_panel(ctx):
    text = ("🌐 <b>𝖲𝖤𝖭𝖪𝖠</b>\n━━━━━━━━━━━━━━\n"
            "زبان خود را انتخاب کن\nChoose your language")
    return Out(text, [[("🇮🇷 فارسی", "lang", "fa"), ("🇬🇧 English", "lang", "en")]])


async def reg_panel(ctx, reg=None):
    reg = reg or await reg_get(ctx.uid) or {}
    step = reg.get("step", "welcome")
    t = ctx.t
    if step == "welcome":
        return Out(t("reg_welcome"), [[(t("b_begin"), "begin", "")]])
    if step == "name":
        return Out(head(ctx, "reg_t_name") + t("reg_ask_name"))
    if step == "gender":
        return Out(head(ctx, "reg_t_gender") + t("reg_ask_gender"),
                   [[(t("b_male"), "gen", "male"), (t("b_female"), "gen", "female"), (t("b_unspec"), "gen", "unspec")]])
    if step == "race":
        body = [t("reg_ask_race"), ""]
        for key, r in RACES.items():
            if r["locked"]:
                continue
            st = " ".join(f"{STAT_ICON[k]}{r['stats'][k]}" for k in STATS)
            body.append(f"<b>{race_name(key, ctx.lang)}</b>  {st}\n   ↳ {t('race_p_' + key)}")
        rows = [[(race_name(k, ctx.lang), "race", k)] for k, r in RACES.items() if not r["locked"]]
        rows = [rows[i][0:1] + (rows[i + 1][0:1] if i + 1 < len(rows) else []) for i in range(0, len(rows), 2)]
        return Out(head(ctx, "reg_t_race") + "\n".join(body), rows)
    if step == "stats":
        stats, pts = reg.get("stats", {}), reg.get("points", 10)
        rows = []
        for k in STATS:
            rows.append([("➖", "st", f"m:{k}"), (f"{STAT_ICON[k]} {t('stat_' + k)}: {fnum(RACES[reg['race']]['stats'][k] + stats.get(k, 0), ctx.lang)}", "noop", ""), ("➕", "st", f"p:{k}")])
        if pts == 0:
            rows.append([(t("b_confirm"), "st", "ok")])
        return Out(head(ctx, "reg_t_stats") + t("reg_ask_stats", pts=fnum(pts, ctx.lang)), rows)
    if step == "zanp":
        rows, body = [], [t("reg_ask_zanp"), ""]
        for wid in reg.get("starters", []):
            body.append(item_card(ctx, wid) + "\n")
            rows.append([(nm(wid, ctx.lang).replace("<", "").replace(">", ""), "zp", wid)])
        return Out(head(ctx, "reg_t_zanp") + "\n".join(body), rows)
    return Out(t("reg_welcome"), [[(t("b_begin"), "begin", "")]])


@action("noop")
async def noop(ctx, arg):
    return Out()


@action("lang")
async def pick_lang(ctx, arg):
    if arg not in ("fa", "en"):
        return Out()
    await set_lang(ctx.uid, arg)
    ctx.lang = arg
    from service_player import get_char
    if await get_char(ctx.uid):
        from handlers_panels import settings_panel
        return await settings_panel(ctx, "")
    await reg_set(ctx.uid, step="welcome")
    return await reg_panel(ctx, {"step": "welcome"})


@action("begin")
async def begin(ctx, arg):
    if not allow(ctx.uid, "reg", 1.0):
        return Out()
    await reg_set(ctx.uid, step="name")
    return await reg_panel(ctx, {"step": "name"})


async def handle_name_text(ctx, text: str):
    if not allow(ctx.uid, "regname", 2.0):
        return Out(ctx.t("slow_down"))
    try:
        name = clean_name(text)
    except ValueError as e:
        return Out(ctx.t({"len": "reg_name_len", "chars": "reg_name_chars", "bad": "reg_name_bad"}[str(e)]))
    if await name_taken(name):
        return Out(ctx.t("reg_name_taken"))
    reg = await reg_set(ctx.uid, step="gender", name=name)
    return await reg_panel(ctx, reg)


@action("gen")
async def pick_gender(ctx, arg):
    reg = await reg_get(ctx.uid)
    if not reg or reg.get("step") != "gender" or arg not in ("male", "female", "unspec"):
        return await reg_panel(ctx)
    reg = await reg_set(ctx.uid, step="race", gender=arg)
    return await reg_panel(ctx, reg)


@action("race")
async def pick_race(ctx, arg):
    reg = await reg_get(ctx.uid)
    if not reg or reg.get("step") != "race" or arg not in RACES or RACES[arg]["locked"]:
        return await reg_panel(ctx)
    reg = await reg_set(ctx.uid, step="stats", race=arg, stats={k: 0 for k in STATS}, points=10)
    return await reg_panel(ctx, reg)


@action("st")
async def adjust(ctx, arg):
    reg = await reg_get(ctx.uid)
    if not reg or reg.get("step") != "stats":
        return await reg_panel(ctx)
    stats, pts = dict(reg["stats"]), int(reg["points"])
    if arg == "ok":
        if pts != 0:
            return Out(alert=ctx.t("reg_need_points", pts=pts))
        reg = await reg_set(ctx.uid, step="zanp", starters=starter_choices(reg["race"]))
        return await reg_panel(ctx, reg)
    op, _, key = arg.partition(":")
    if key not in STATS:
        return Out()
    if op == "p" and pts > 0:
        stats[key] += 1
        pts -= 1
    elif op == "m" and stats[key] > 0:
        stats[key] -= 1
        pts += 1
    else:
        return Out()
    reg = await reg_set(ctx.uid, stats=stats, points=pts)
    return await reg_panel(ctx, reg)


@action("zp")
async def pick_zanp(ctx, arg):
    reg = await reg_get(ctx.uid)
    if not reg or reg.get("step") != "zanp" or arg not in reg.get("starters", []):
        return await reg_panel(ctx)
    reg["weapon"] = arg
    ch = await finish_registration(ctx.uid, reg)
    if ch is None:
        await reg_set(ctx.uid, step="name")
        return Out(ctx.t("reg_name_taken") + "\n\n" + ctx.t("reg_ask_name"))
    await inv_add(ctx.uid, POTION, 3, force=True)
    u = await col("users").find_one({"telegram_id": ctx.uid})
    ref = (u or {}).get("referred_by")
    if ref and ref != ctx.uid and not (u or {}).get("ref_paid"):
        st = await game_settings()
        if await col("characters").find_one({"user_id": ref}, {"_id": 1}):
            from service_player import add_coins
            await add_coins(ref, int(st["referral_reward"]), "referral")
            await col("users").update_one({"telegram_id": ctx.uid}, {"$set": {"ref_paid": True}})
    text = ctx.t("reg_done", name=esc(ch["name"]), race=race_name(ch["race"], ctx.lang), weapon=nm(ch["weapon_id"], ctx.lang))
    return Out(head(ctx, "reg_t_done") + text, [[(ctx.t("m_home"), "home", "")]])
