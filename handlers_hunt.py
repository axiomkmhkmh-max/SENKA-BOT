"""Hollow Hunt panels: a 3-stage chain of risk choices that replaces the passive hunt roll."""
import random

import engine_hunt as H
from database import col, game_settings
from i18n import fnum
from service_economy import inv_add, roll_drop
from service_player import add_coins, add_xp, bump_quest, get_char
from ui import Out, action, head, nav

LABELS = {
    "track": ("🐾 ردیابی", "🐾 Track"), "ambush": ("🗡 کمین", "🗡 Ambush"), "wait": ("🌫 صبر", "🌫 Wait"),
    "sneak": ("🤫 دزدکی", "🤫 Sneak"), "charge": ("⚔️ حمله", "⚔️ Charge"), "bait": ("🪤 طعمه", "🪤 Bait"),
    "seal": ("🧿 مهر", "🧿 Seal"), "push": ("🔥 فشار", "🔥 Push"), "retreat": ("🏃 عقب‌نشینی", "🏃 Retreat"),
}
STAGE_NAME = ("مرحله‌ی اول: ردپا", "Stage one: the trail")
STAGE_NAMES = [("مرحله‌ی اول: ردپا", "Stage one: the trail"), ("مرحله‌ی دوم: تعقیب", "Stage two: the chase"),
               ("مرحله‌ی سوم: قله", "Stage three: the summit")]


def _L(ctx, pair):
    return pair[0] if ctx.lang == "fa" else pair[1]


def _stage_out(ctx, hunt, intro=""):
    stage = hunt["stage"]
    title = _L(ctx, STAGE_NAMES[stage]) if stage < H.STAGES else ""
    buttons = [[(_L(ctx, LABELS[o["id"]]), "hnt", o["id"])] for o in H.current_options(hunt)]
    body = (intro + "\n" if intro else "") + f"<b>{title}</b>\n" + \
        _L(ctx, ("هر انتخاب ریسک و پاداش خودش را دارد. بعضی کمین‌ها فریب‌اند.",
                 "Each choice carries its own risk and reward. Some ambushes are feints."))
    return Out(head(ctx, "ttl_exp") + body, buttons + [nav(ctx)])


async def start(ctx, ch):
    """Called by the explore panel. Resumes an unfinished hunt, or starts a new one."""
    if ch.get("bx_hunt"):
        return _stage_out(ctx, ch["bx_hunt"], intro=_L(ctx, ("ادامه‌ی شکار:", "Continuing the hunt:")))
    hunt = H.new_hunt(random.Random())
    await col("characters").update_one({"user_id": ctx.uid}, {"$set": {"bx_hunt": hunt}})
    return _stage_out(ctx, hunt)


@action("hnt")
async def hunt_choose(ctx, arg):
    ch = await get_char(ctx.uid)
    if not ch or not ch.get("bx_hunt"):
        return Out(alert=_L(ctx, ("شکاری فعال نداری.", "No active hunt.")))
    hunt = ch["bx_hunt"]
    try:
        out = H.choose(hunt, arg, random.Random())
    except ValueError:
        return Out(alert=_L(ctx, ("این گزینه معتبر نیست.", "Invalid choice.")))
    st = await game_settings()
    L = ctx.lang
    lvl = ch["level"]
    base_xp = int(18 + lvl * 4)
    base_coins = int((10 + lvl * 3) * float(st["coin_rate"]))
    lines = []
    fight_scale = None

    if out["kind"] == "fight":
        fight_scale = out["scale"]
    if out["xp"]:
        _, _, gained = await add_xp(ctx.uid, int(base_xp * out["xp"]), "hunt")
        lines.append(f"+{fnum(gained, L)} XP")
    if out["coin"]:
        coins = int(base_coins * out["coin"])
        await add_coins(ctx.uid, coins, "hunt")
        lines.append(f"+{fnum(coins, L)} 🪙")
    if out["item"]:
        iid = await roll_drop(ctx.uid)
        got = await inv_add(ctx.uid, iid, 1)
        lines.append(_L(ctx, ("🎁 یک آیتم پیدا کردی.", "🎁 You found an item.")) + ("" if got else _L(ctx, (" (کوله پر است)", " (bag full)"))))
    if out["dmg_pct"]:
        loss = min(int(ch["coins"]), int(ch["coins"] * out["dmg_pct"] * 0.2))
        if loss:
            await add_coins(ctx.uid, -loss, "hunt_trap")
        lines.append(_L(ctx, (f"🪤 تله! {fnum(loss, L)} 🪙 از دست رفت.", f"🪤 Trap! Lost {fnum(loss, L)} 🪙.")))
    if out.get("feint"):
        lines.append(_L(ctx, ("کمین فریب بود و به تله تبدیل شد.", "The ambush was a feint and turned into a trap.")))
    if out["kind"] == "none":
        lines.append(_L(ctx, ("هیچ‌چیز نبود. ادامه بده.", "Nothing there. Keep going.")))

    intro = "\n".join(lines)
    if out["finished"]:
        summ = H.summarize(hunt)
        if summ["clean"]:
            _, _, bonus = await add_xp(ctx.uid, int(base_xp * H.CLEAN_BONUS_XP), "hunt_clean")
            intro += "\n" + _L(ctx, (f"🏅 شکار بی‌تله! +{fnum(bonus, L)} XP", f"🏅 Clean hunt! +{fnum(bonus, L)} XP"))
        await bump_quest(ctx.uid, "explore", 1)
        await col("characters").update_one({"user_id": ctx.uid}, {"$unset": {"bx_hunt": ""}})
        if fight_scale is not None:
            from handlers_combat import start_pve_panel
            return await start_pve_panel(ctx, scale=fight_scale, intro=intro)
        return Out(head(ctx, "ttl_exp") + intro, [[(_L(ctx, ("🐾 شکار دوباره", "🐾 Hunt again")), "exp", "go")], nav(ctx)])

    await col("characters").update_one({"user_id": ctx.uid}, {"$set": {"bx_hunt": hunt}})
    if fight_scale is not None:
        from handlers_combat import start_pve_panel
        return await start_pve_panel(ctx, scale=fight_scale, intro=intro)
    return _stage_out(ctx, hunt, intro=intro)
