"""Respec and race-change panels.

Commands: "ریست استت" / "respec" open the menu. Callback codes: resp, rspst (reset stats), rspr (pick a race),
rspc:<race> (ask to confirm), rspx:<race> (do it).
"""
from data_races import RACES, race_selectable
from i18n import fnum
from service_player import get_char
from service_respec import change_race, race_change_quote, respec_quote, respec_stats
from ui import Out, action, head, nav

ERR = {
    "fighting": ("همین الان توی مبارزه‌ای؛ بعد از اون بیا.", "You are in a fight right now; come back after it."),
    "trading": ("یه ترید بازی داری؛ اول تمومش کن.", "You have an open trade; finish or cancel it first."),
    "cooldown": ("هنوز زمانش نشده.", "Not yet; the cooldown is still running."),
    "funds": ("سکه‌ی کافی نداری.", "Not enough coins."),
    "nothing": ("هیچ امتیازی برای برگشت نداری.", "You have no allocated points to return."),
    "locked": ("این نژاد هنوز قفله.", "That race is still locked."),
    "invalid": ("این نژاد قابل انتخاب نیست.", "That race is not an option."),
    "retry": ("لطفاً دوباره امتحان کن.", "Please try again."),
    "noreg": ("اول ثبت‌نام کن.", "Register first."),
    "ok": ("انجام شد.", "Done."),
}


def _msg(ctx, code, extra=None):
    fa, en = ERR.get(code, ("یه مشکلی پیش اومد.", "Something went wrong."))
    text = fa if ctx.lang == "fa" else en
    if code == "cooldown" and extra:
        hours = max(1, int(extra) // 3600)
        text += (f" ({fnum(hours, ctx.lang)} ساعت مونده)" if ctx.lang == "fa" else f" ({hours}h left)")
    if code == "funds" and extra:
        text += (f" (لازم: {fnum(extra, ctx.lang)} 🪙)" if ctx.lang == "fa" else f" (need {fnum(extra, ctx.lang)} 🪙)")
    return text


def _race_name(key, L):
    r = RACES[key]
    return r["name_fa"] if L == "fa" else r["name_en"]


@action("resp")
async def respec_menu(ctx, arg):
    L = ctx.lang
    ch = await get_char(ctx.uid)
    if not ch:
        return Out(_msg(ctx, "noreg"), [nav(ctx)])
    rq = respec_quote(ch)
    cq = race_change_quote(ch)
    lines = [T(ctx, "🔁 <b>ریست و تغییر نژاد</b>", "🔁 <b>Respec and race change</b>"),
             T(ctx, f"نژاد فعلی: <b>{_race_name(ch['race'], L)}</b> · لول {fnum(ch['level'], L)}",
               f"Current race: <b>{_race_name(ch['race'], L)}</b> · Lv.{fnum(ch['level'], L)}"),
             "",
             T(ctx, f"🔁 <b>ریست استت:</b> {fnum(rq['points'], L)} امتیاز برمی‌گرده. هزینه: {fnum(rq['coins'], L)} 🪙. "
                    "هر ۲۴ ساعت یک بار.",
               f"🔁 <b>Stat reset:</b> returns {fnum(rq['points'], L)} points. Cost: {fnum(rq['coins'], L)} 🪙. Once per 24h."),
             T(ctx, f"🧬 <b>تغییر نژاد:</b> امتیازهای استت حفظ میشن و روی پایه‌ی نژاد جدید میشینن. "
                    f"هزینه: {fnum(cq['coins'], L)} 🪙. هر ۳۰ روز یک بار. کیدو و مسیر تکامل نژاد قبلی ریست میشه.",
               f"🧬 <b>Race change:</b> your allocated points are kept on the new race's base. Cost: {fnum(cq['coins'], L)} 🪙. "
                    "Once per 30 days. Kidō and the old race's evolution progress reset.")]
    rows = [[(T(ctx, "🔁 ریست استت", "🔁 Reset stats"), "rspst", "")],
            [(T(ctx, "🧬 تغییر نژاد", "🧬 Change race"), "rspr", "")],
            nav(ctx)]
    return Out("\n".join(lines), rows)


@action("rspst")
async def respec_do(ctx, arg):
    code, extra = await respec_stats(ctx.uid)
    if code != "ok":
        return Out(alert=_msg(ctx, code, extra))
    return await respec_menu(ctx, "")


@action("rspr")
async def race_pick(ctx, arg):
    L = ctx.lang
    ch = await get_char(ctx.uid)
    if not ch:
        return Out(_msg(ctx, "noreg"), [nav(ctx)])
    rows = []
    for key, r in RACES.items():
        if key == ch["race"] or not race_selectable(key, ch):
            continue
        rows.append([(_race_name(key, L), "rspc", key)])
    rows.append(nav(ctx, ("resp", "")))
    text = T(ctx, "کدوم نژاد؟ امتیازهای استت حفظ میشن.", "Which race? Your stat points are kept.")
    return Out(text, rows)


@action("rspc")
async def race_confirm(ctx, arg):
    L = ctx.lang
    cq = race_change_quote(await get_char(ctx.uid) or {"level": 1})
    text = T(ctx, f"مطمئنی به <b>{_race_name(arg, L)}</b> میری؟ {fnum(cq['coins'], L)} 🪙 هزینه داره و ۳۰ روز دیگه نمی‌تونی عوض کنی.",
             f"Sure about <b>{_race_name(arg, L)}</b>? It costs {fnum(cq['coins'], L)} 🪙 and you cannot change again for 30 days.")
    rows = [[(T(ctx, "✅ بله، تغییر بده", "✅ Yes, change"), "rspx", arg)],
            [(T(ctx, "❌ نه", "❌ No"), "resp", "")]]
    return Out(text, rows)


@action("rspx")
async def race_do(ctx, arg):
    code, extra = await change_race(ctx.uid, arg)
    if code != "ok":
        return Out(alert=_msg(ctx, code, extra))
    text = T(ctx, f"نژادت حالا <b>{_race_name(arg, ctx.lang)}</b> شده. امتیازهات سر جاشونن.",
             f"You are now <b>{_race_name(arg, ctx.lang)}</b>. Your points stayed with you.")
    return Out(text, [nav(ctx)])


def T(ctx, fa, en):
    return fa if ctx.lang == "fa" else en
