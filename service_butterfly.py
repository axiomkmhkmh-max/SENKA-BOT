"""Hell Butterfly: a rare private message when a player achieves something big.

It is deliberately sparse: at most one butterfly per player per `butterfly_cooldown` seconds (default 30 min), and it
can be switched off for everyone with `set butterfly_on 0`. A failed send is logged and never breaks the action
that triggered it (a player who blocked the bot simply gets no message).
"""
import logging

from database import game_settings, try_cooldown
from i18n import esc

log = logging.getLogger(__name__)

TEXT = {
    "shikai": ("🦋 پروانه‌ی جهنمی روی شانه‌ات نشست… تیغه‌ات برای نخستین بار شیکای خود را بیدار کرد: <b>{blade}</b>. "
               "حالا در نبرد می‌توانی نامش را صدا بزنی.",
               "🦋 A Hell Butterfly settles on your shoulder… your blade has awakened its Shikai: <b>{blade}</b>. "
               "In battle, you can now call its name."),
    "bankai": ("🦋 پروانه‌ی جهنمی به سمتت پرواز کرد… <b>{blade}</b> به بانکای رسید. سوول سوسایتی این را فراموش نمی‌کند.",
               "🦋 A Hell Butterfly drifts toward you… <b>{blade}</b> has reached Bankai. Soul Society will not forget."),
    "seat": ("🦋 پروانه‌ی جهنمی جایزه‌ات را آورد: جایگاه گوتی‌ات بالاتر رفت.",
             "🦋 A Hell Butterfly delivers your reward: your Gotei seat has risen."),
}


async def butterfly(bot, uid: int, lang: str, kind: str, **kw) -> bool:
    """Send the butterfly if it is switched on and this player has not had one recently. Returns True if sent."""
    try:
        gs = await game_settings()
        if not int(gs.get("butterfly_on", 1)):
            return False
        if await try_cooldown(f"butterfly:{uid}", float(gs.get("butterfly_cooldown", 1800))):
            return False
        fa, en = TEXT[kind]
        kw = {k: esc(str(v)) for k, v in kw.items()}
        await bot.send_message(uid, (fa if lang == "fa" else en).format(**kw))
        return True
    except Exception:  # blocked bot, deleted chat, ...: never let a message break the action that caused it
        log.debug("hell butterfly to %s failed", uid, exc_info=True)
        return False
