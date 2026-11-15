"""Group side of the Hollow / Menos incursions: spawn on chat activity, strike by replying to the message."""
import logging

from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError

from data_items import iname
from database import col, try_cooldown
from i18n import bar, esc, fnum
from render import glang
from security import allow
from chat_tidy import reply_tidy
from data_espada_raid import ESPADA
from service_hollowraid import STRIKE_WORDS, raid_abort, raid_attach, raid_roll, raid_settle, raid_strike
from service_world import group_doc

log = logging.getLogger("senka.raid")

NAME = {"hollow": ("هالوی سرگردان", "Wandering Hollow"), "menos": ("منوس گرانده", "Menos Grande")}


def _kname(doc, lang):
    """Display name of an incursion; an Espada shows its own name."""
    if doc.get("kind") == "espada":
        e = ESPADA.get(int(doc.get("esp") or 0))
        if e:
            return e["fa" if lang == "fa" else "en"]
        return "اسپادا" if lang == "fa" else "Espada"
    return NAME[doc["kind"]][0 if lang == "fa" else 1]
T = {
    "spawn": ("🕳 <b>گارگانتا شکافت!</b>\n{icon} <b>{name}</b> وارد جامعه ارواح شد!\n❤️ {bar} {hp}/{mx}\n⏳ {mins} دقیقه فرصت داری.\nروی این پیام ریپلای کن: «حمله»",
              "🕳 <b>The Garganta tears open!</b>\n{icon} <b>{name}</b> has entered Soul Society!\n❤️ {bar} {hp}/{mx}\n⏳ {mins} minutes to purge it.\nReply to this message: “strike”"),
    "live": ("{icon} <b>{name}</b>\n❤️ {bar} {hp}/{mx}\n⚔️ ضربه‌ها: {n} نفر\nریپلای کن: «حمله»", "{icon} <b>{name}</b>\n❤️ {bar} {hp}/{mx}\n⚔️ Fighters: {n}\nReply: “strike”"),
    "hit": ("⚔️ {who}: {dmg} آسیب!", "⚔️ {who}: {dmg} damage!"),
    "dead": ("💀 <b>{name}</b> پاک‌سازی شد!\n🏆 برترین‌ها:\n{top}\n🎁 پاداش برای {paid} نفر{drop}", "💀 <b>{name}</b> has been purged!\n🏆 Top damage:\n{top}\n🎁 Rewards paid to {paid}{drop}"),
    "drop": ("\n✨ دراپ ویژه: {item} برای {who}", "\n✨ Special drop: {item} for {who}"),
    "drop_more": ("\n🎁 {item} برای {who}", "\n🎁 {item} for {who}"),
    "gone": ("این هالو دیگر اینجا نیست.", "That Hollow is gone."),
    "noreg": ("اول در ربات ثبت‌نام کن.", "Register with the bot first."),
    "level": ("سطح بالاتری لازم است.", "You need a higher level."),
    "cd": ("هنوز خسته‌ای؛ کمی صبر کن.", "Catch your breath first."),
}


def _t(lang, key, **kw):
    fa, en = T[key]
    return (fa if lang == "fa" else en).format(**kw)


def _view(lang, doc, key="live"):
    nm = _kname(doc, lang)
    icon = {"menos": "👹", "espada": "💀"}.get(doc["kind"], "👻")
    return _t(lang, key, icon=icon, name=nm, bar=bar(max(0, doc["hp"]), doc["max_hp"]), hp=fnum(max(0, doc["hp"]), lang),
              mx=fnum(doc["max_hp"], lang), n=len(doc.get("hits") or {}), mins=max(1, (doc["end_at"] - doc["created_at"]) // 60))


async def raid_hook(message, n: str) -> bool:
    """Called on every group text. True = it was a strike on an incursion and has been handled."""
    user, chat = message.from_user, message.chat
    if n in STRIKE_WORDS and message.reply_to_message is not None:  # a reply strikes the incursion; plain word = attack panel
        if not allow(user.id, "raidhit", 0.8):
            return True
        res, doc, dmg = await raid_strike(chat.id, user.id, message.reply_to_message.message_id)
        if res == "nodoc":
            return False
        lang = glang(await group_doc(chat.id))
        if res in ("gone", "noreg", "level", "cd"):
            await reply_tidy(message, _t(lang, res), 60)
            return True
        nm = esc(user.full_name or user.first_name or "")
        if res == "dead":
            out = await raid_settle(doc)
            top = "\n".join(f"{i + 1}. {esc(str(name))} — {fnum(d, lang)}" for i, (name, d) in enumerate(out["top"]))
            extra = ""
            if out["drop"]:
                uid, iid = out["drop"]
                who = esc(str((doc.get("names") or {}).get(str(uid), uid)))
                extra = _t(lang, "drop", item=esc(iname(iid, lang)), who=who)
            for uid, iid in out.get("extra", []):
                who = esc(str((doc.get("names") or {}).get(str(uid), uid)))
                extra += _t(lang, "drop_more", item=esc(iname(iid, lang)), who=who)
            text = _t(lang, "dead", name=_kname(doc, lang), top=top, paid=out["paid"], drop=extra)
            await message.reply(text)
            await _edit(message.bot, doc, text)
            return True
        if doc.get("kind") == "espada":  # announce the Espada's second pattern the strike it begins
            from data_espada_raid import phase
            before = (doc["hp"] + dmg) / max(1, doc["max_hp"])  # heal is not returned by raid_strike; close enough for a banner
            now_f = doc["hp"] / max(1, doc["max_hp"])
            if phase(doc.get("esp"), before) != phase(doc.get("esp"), now_f):
                p2 = (ESPADA.get(int(doc.get("esp") or 0)) or {}).get("phase2") or {}
                if p2:
                    await reply_tidy(message, "⚠️ " + esc(p2["fa" if lang == "fa" else "en"]), 90)
        await reply_tidy(message, _t(lang, "hit", who=nm, dmg=fnum(dmg, lang)), 90)
        if not await try_cooldown(f"raid:edit:{doc['_id']}", 5):
            await _edit(message.bot, doc, _view(lang, doc))
        return True
    if allow(user.id, "raidcnt", 4):
        try:
            doc = await raid_roll(chat.id)
            if doc:
                lang = glang(await group_doc(chat.id))
                try:
                    msg = await message.bot.send_message(chat.id, _view(lang, doc, "spawn"))
                except TelegramForbiddenError:
                    await col("groups").update_one({"chat_id": chat.id}, {"$set": {"blocked": True}})
                    await raid_abort(doc["_id"])
                except TelegramAPIError:
                    log.warning("raid send failed in %s", chat.id)
                    await raid_abort(doc["_id"])
                else:
                    await raid_attach(doc["_id"], msg.message_id)
        except Exception:
            log.exception("raid roll failed")
    return False


async def _edit(bot, doc, text):
    if not doc.get("msg_id"):
        return
    try:
        await bot.edit_message_text(text, chat_id=doc["chat_id"], message_id=doc["msg_id"])
    except TelegramAPIError:
        pass
