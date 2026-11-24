"""Telegram entry point for The Final Judgment."""
from ui import Out, action, head, nav
from service_final_judgment import start

@action("fjd")
async def final_judgment_info(ctx, arg):
    fa = ctx.lang == "fa"
    text = ("⚖️ <b>THE FINAL JUDGMENT</b>\nده مرحله‌ی تک‌نفره؛ هر شکست، پایان تلاش همان روز است.\n\n"
            "مرحله ۱: صد دشمن · مرحله ۲: پنج باس پیاپی · مرحله ۳: مهر توانایی‌ها · مرحله ۴: غول‌ها\n"
            "مرحله ۵: سه‌گانه‌ی ویرانگر · مرحله ۶: سی موج · مرحله ۷: نسخه‌ی تاریک خودت\n"
            "مرحله ۸: باس پنج‌فازه · مرحله ۹: بدون آیتم درمانی · مرحله ۱۰: Absolute Awakening\n\n"
            "HP و Reiatsu بین نبردها کامل بازیابی نمی‌شوند. فقط یک ورود در روز داری.") if fa else (
            "⚖️ <b>THE FINAL JUDGMENT</b>\nA ten-stage solo gauntlet. One defeat ends today's attempt.\n\n"
            "1: One hundred enemies · 2: Five consecutive bosses · 3: Sealed abilities · 4: Giants\n"
            "5: Three bosses · 6: Thirty waves · 7: Your dark reflection\n"
            "8: Five-phase boss · 9: No healing items · 10: Absolute Awakening\n\n"
            "HP and Reiatsu are carried between encounters. One entry per day.")
    label = "⚔️ ورود به داوری" if fa else "⚔️ Enter the Judgment"
    return Out(head(ctx, "ttl_bt") + text, [[(label, "fjs", "")], nav(ctx)])

@action("fjs")
async def final_judgment_start(ctx, arg):
    status, doc = await start(ctx.uid, ctx.lang)
    if status != "ok":
        messages = {
            "fa": {"noreg": "ابتدا شخصیت بساز.", "busy": "اول نبرد فعلی را تمام کن.", "spent": "فرصت امروزت را قبلاً استفاده کرده‌ای."},
            "en": {"noreg": "Create a character first.", "busy": "Finish your current battle first.", "spent": "You have already used today's attempt."},
        }
        return Out(alert=messages["fa" if ctx.lang == "fa" else "en"].get(status, "Unavailable"))
    from handlers_combat import battle_panel
    return await battle_panel(ctx, doc, [])
