"""Xcution membership panel: status, join at the hideout, leave. Rules live in data_gangs.py.

Actions: xgn (panel), xgj (join), xgl (leave).
"""
import time

from data_gangs import (BOSS_NAME, XCUTION_BOSS_PHASES, XCUTION_LOC, XCUTION_RANK_POINTS,
                        XCUTION_REJOIN_SECONDS, can_join_xcution, xcution_rank, xcution_rank_name)
from database import col
from service_gangs_hook import boss_state, current_boss_buff
from service_player import get_char
from ui import Out, action, nav


def _t(lang, fa, en):
    return fa if lang == "fa" else en


@action("xgn")
async def gang_panel(ctx, arg):
    ch = await get_char(ctx.uid)
    if not ch:
        return Out(ctx.t("not_registered"), [nav(ctx)])
    if ch.get("race") != "fullbringer":
        return Out(_t(ctx.lang, "Xcution فقط برای فول‌برینگرهاست.", "Xcution is for Fullbringers only."), [nav(ctx)])
    x = ch.get("xcution") or {}
    now = int(time.time())
    if x.get("joined"):
        pts = int(x.get("points", 0))
        rank = xcution_rank(pts)
        nxt = XCUTION_RANK_POINTS[rank + 1] if rank + 1 < len(XCUTION_RANK_POINTS) else None
        lines = [_t(ctx.lang, "🌀 <b>Xcution</b>", "🌀 <b>Xcution</b>"),
                 _t(ctx.lang, f"عضو هستی. رتبه: <b>{xcution_rank_name(pts, 'fa')}</b> ({rank})",
                    f"You are a member. Rank: <b>{xcution_rank_name(pts, 'en')}</b> ({rank})"),
                 _t(ctx.lang, f"امتیاز دزدی ریاتسو: {pts}" + (f" (رتبه‌ی بعد در {nxt})" if nxt else " (بالاترین رتبه)"),
                    f"Siphon points: {pts}" + (f" (next rank at {nxt})" if nxt else " (top rank)")),
                 _t(ctx.lang, "امتیاز را با بردن در هالوگاه اکسکیوشن جمع کن.",
                    "Earn siphon points by winning at the Xcution hideout.")]
        b = await boss_state()
        if b["defeated"]:
            lines.append(_t(ctx.lang, f"👹 <b>{BOSS_NAME[0]}</b> این هفته شکست خورده. پاداش گرفتی.",
                            f"👹 <b>{BOSS_NAME[1]}</b> is defeated this week. Rewards paid."))
        else:
            nxt_need = next((n for n in XCUTION_BOSS_PHASES if n > b["wins"]), None)
            lines.append(_t(ctx.lang, f"👹 <b>{BOSS_NAME[0]}</b>: {b['wins']}/{b['target']} برد در هالوگاه",
                            f"👹 <b>{BOSS_NAME[1]}</b>: {b['wins']}/{b['target']} wins at the hideout"))
            bonus = round(b["dmg"] * 100)
            if bonus:
                lines.append(_t(ctx.lang, f"🔥 فاز {b['phase']}: آسیب همه‌ی اعضا +{bonus}%",
                                f"🔥 Phase {b['phase']}: all members deal +{bonus}% damage"))
            if nxt_need:
                lines.append(_t(ctx.lang, f"⏭️ فاز بعدی در {nxt_need} برد", f"⏭️ Next phase at {nxt_need} wins"))
        if int(x.get("surge_until", 0) or 0) > now:
            mins = max(1, (int(x["surge_until"]) - now) // 60)
            lines.append(_t(ctx.lang, f"⚡ موج Xcution فعال است: {mins} دقیقه مانده", f"⚡ Xcution surge active: {mins} min left"))
        rows = [[(_t(ctx.lang, "🚪 ترک گروه", "🚪 Leave"), "xgl", "")], nav(ctx)]
        return Out("\n".join(lines), rows)
    rows = [nav(ctx)]
    if can_join_xcution(ch, ch.get("location"), now):
        rows.insert(0, [(_t(ctx.lang, "🤝 پیوستن", "🤝 Join"), "xgj", "")])
        text = _t(ctx.lang, "هنوز عضو نیستی. پیوستن فقط در هالوگاه اکسکیوشن ممکنه.",
                  "You are not a member. You can join here at the Xcution hideout.")
    else:
        wait = max(0, XCUTION_REJOIN_SECONDS - (now - int(x.get("left_at", 0) or 0)))
        if ch.get("location") != XCUTION_LOC:
            text = _t(ctx.lang, "برای پیوستن به هالوگاه اکسکیوشن برو.", "Travel to the Xcution hideout to join.")
        else:
            text = _t(ctx.lang, f"بعد از ترک باید {max(1, wait // 3600)} ساعت صبر کنی.",
                      f"You must wait {max(1, wait // 3600)} hours after leaving.")
    return Out(text, rows)


@action("xgj")
async def gang_join(ctx, arg):
    ch = await get_char(ctx.uid)
    if not ch:
        return Out(ctx.t("not_registered"), [nav(ctx)])
    if not can_join_xcution(ch, ch.get("location"), int(time.time())):
        return Out(alert=_t(ctx.lang, "الان نمی‌تونی بپیوندی.", "You cannot join right now."))
    boss_dmg, boss_until = await current_boss_buff()  # a newcomer gets the phase bonus the group already unlocked
    await col("characters").update_one({"user_id": ctx.uid, "xcution.joined": {"$ne": True}},
                                       {"$set": {"xcution.joined": True,
                                                 "xcution.points": int((ch.get("xcution") or {}).get("points", 0)),
                                                 "xcution.boss_dmg": boss_dmg, "xcution.boss_until": boss_until}})
    return await gang_panel(ctx, "")


@action("xgl")
async def gang_leave(ctx, arg):
    ch = await get_char(ctx.uid)
    if not ch or not (ch.get("xcution") or {}).get("joined"):
        return await gang_panel(ctx, "")
    await col("characters").update_one({"user_id": ctx.uid}, {"$set": {"xcution.joined": False, "xcution.left_at": int(time.time())}})
    return await gang_panel(ctx, "")
