"""Hollow Chase, solo and in groups. A Hollow runs through three paths; the players call where to chase.

Solo: explore starts a chase and each button press is a vote that resolves at once.
Group: type 'شکار' (or 'hunt') in the chat to release a Hollow. Players reply to its message with
چپ / وسط / راست (or left / mid / right). The round closes after ROUND_SECONDS, or on the scheduler.
"""
import random
import time
import uuid

import engine_chase as E
from database import col
from i18n import esc, fnum
from service_economy import inv_add, roll_drop
from service_player import add_coins, add_xp, bump_quest, get_char
from ui import Out, action, head, nav

ROUND_SECONDS = 60
DIR_LABEL = {"left": ("⬅️ چپ", "⬅️ Left"), "mid": ("⏺ وسط", "⏺ Mid"), "right": ("➡️ راست", "➡️ Right")}
WORD_TO_DIR = {"چپ": "left", "left": "left", "وسط": "mid", "mid": "mid", "راست": "right", "right": "right"}
START_WORDS = {"شکار", "hunt"}

T = {
    "hint": ("🌫 ردپا: <b>{hint}</b>\n{dirs}", "🌫 Trail hint: <b>{hint}</b>\n{dirs}"),
    "round_ok": ("✅ درست حدس زدید! {n}/{total}", "✅ Right call! {n}/{total}"),
    "round_bad": ("❌ اشتباه. هالو فرار کرد و ۱ جان از دست داد. جان: {s}", "❌ Wrong. The Hollow slipped away and lost 1 stamina. Stamina: {s}"),
    "round_none": ("😴 هیچ‌کس رأی نداد. هالو ۱ جان از دست داد. جان: {s}", "😴 Nobody voted. The Hollow lost 1 stamina. Stamina: {s}"),
    "caught": ("🏆 <b>هالو گرفته شد!</b>\n{rewards}\n{mvp}", "🏆 <b>The Hollow is caught!</b>\n{rewards}\n{mvp}"),
    "escaped": ("💨 هالو در تاریکی ناپدید شد. فقط {xp} XP گرفتی.", "💨 The Hollow vanished into the dark. You got {xp} XP."),
    "busy": ("یک هالو الان در حال تعقیب است. رأی بده!", "A Hollow is already being chased. Vote!"),
    "no_hunt": ("شکاری فعال نداری.", "No active hunt."),
    "vote_ok": ("رأیت ثبت شد.", "Vote recorded."),
    "mvp": ("⭐ برترین شکارچی: {name}", "⭐ MVP: {name}"),
    "reg": ("اول در ربات ثبت‌نام کن.", "Register with the bot first."),
    "escaped_group": ("💨 هالو فرار کرد. ارواح دوباره در این گوشه پیدا می‌شوند.", "💨 The Hollow escaped. Souls will show up again here."),
}


def _t(lang, key, **kw):
    fa, en = T[key]
    return (fa if lang == "fa" else en).format(**kw)


def _dirs_text(lang):
    return "  ".join(DIR_LABEL[d][0 if lang == "fa" else 1] for d in E.DIRECTIONS)


def _panel(ctx, chase, extra=""):
    hint = DIR_LABEL[chase["hint"]][0 if ctx.lang == "fa" else 1]
    body = (extra + "\n" if extra else "") + _t(ctx.lang, "hint", hint=hint, dirs="")
    body += f"\n<i>{_dirs_text(ctx.lang)}</i>"
    rows = [[(DIR_LABEL[d][0 if ctx.lang == "fa" else 1], "hnt", d) for d in E.DIRECTIONS], nav(ctx)]
    return Out(head(ctx, "ttl_exp") + body, rows)


async def start(ctx, ch):
    """Called by the explore panel: resume an unfinished solo chase, or start one."""
    if ch.get("bx_hunt"):
        return _panel(ctx, ch["bx_hunt"]["chase"], extra=("ادامه‌ی تعقیب:" if ctx.lang == "fa" else "Continuing the chase:"))
    chase = E.new_chase(random.Random())
    E.make_hint(chase, random.Random())
    await col("characters").update_one({"user_id": ctx.uid}, {"$set": {"bx_hunt": {"chase": chase}}})
    return _panel(ctx, chase)


async def _rewards_solo(ctx, ch, caught: bool, chase):
    lvl = ch["level"]
    base_xp = int(18 + lvl * 4)
    base_coins = int((10 + lvl * 3))
    if not caught:
        _, _, xp = await add_xp(ctx.uid, int(base_xp * 0.5), "hunt")
        return _t(ctx.lang, "escaped", xp=fnum(xp, ctx.lang))
    pool = E.catch_pool(base_xp, base_coins, 1)
    _, _, xp = await add_xp(ctx.uid, pool["xp"], "hunt")
    await add_coins(ctx.uid, pool["coins"], "hunt")
    iid = await roll_drop(ctx.uid)
    got = await inv_add(ctx.uid, iid, 1)
    rewards = f"+{fnum(xp, ctx.lang)} XP  +{fnum(pool['coins'], ctx.lang)} 🪙"
    if not got:
        rewards += "\n" + ("کوله پر است." if ctx.lang == "fa" else "Your bag is full.")
    return _t(ctx.lang, "caught", rewards=rewards, mvp="")


@action("hnt")
async def solo_vote(ctx, arg):
    ch = await get_char(ctx.uid)
    if not ch or not ch.get("bx_hunt"):
        return Out(alert=_t(ctx.lang, "no_hunt"))
    chase = ch["bx_hunt"]["chase"]
    if arg not in E.DIRECTIONS:
        return Out(alert=_t(ctx.lang, "no_hunt"))
    res = E.resolve_round(chase, {ctx.uid: arg}, random.Random())
    if res["status"] != "running":
        await bump_quest(ctx.uid, "explore", 1)
    if res["status"] == "running":
        E.make_hint(chase, random.Random())
        await col("characters").update_one({"user_id": ctx.uid}, {"$set": {"bx_hunt": {"chase": chase}}})
        msg = _t(ctx.lang, "round_ok" if res["outcome"] == "correct" else "round_bad",
                 n=chase["round"], total=E.CATCH_AT, s=chase["stamina"])
        return _panel(ctx, chase, extra=msg)
    await col("characters").update_one({"user_id": ctx.uid}, {"$unset": {"bx_hunt": ""}})
    text = await _rewards_solo(ctx, ch, res["status"] == "caught", chase)
    again = "🐾 شکار دوباره" if ctx.lang == "fa" else "🐾 Hunt again"
    return Out(head(ctx, "ttl_exp") + text, [[(again, "exp", "go")], nav(ctx)])


# ---- group side ------------------------------------------------------------------------------

def _group_text(lang, chase, names, votes, seconds_left, extra=""):
    hint = DIR_LABEL[chase["hint"]][0 if lang == "fa" else 1]
    voters = len(votes)
    pre = (extra + "\n\n") if extra else ""
    return pre + (f"👻 <b>هالوی سرگردان در حال فرار است</b>\n🌫 ردپا: <b>{hint}</b>\n"
            f"🏁 پیشرفت: {chase['round']}/{E.CATCH_AT}  |  💚 جان: {chase['stamina']}\n"
            f"🗳 رأی‌ها: {voters}  |  ⏳ {max(0, seconds_left)} ثانیه\n"
            f"ریپلای کن: چپ / وسط / راست") if lang == "fa" else (
            f"👻 <b>A wandering Hollow is fleeing</b>\n🌫 Trail: <b>{hint}</b>\n"
            f"🏁 Progress: {chase['round']}/{E.CATCH_AT}  |  💚 Stamina: {chase['stamina']}\n"
            f"🗳 Votes: {voters}  |  ⏳ {max(0, seconds_left)}s\n"
            f"Reply: left / mid / right")


async def group_hook(message, n: str) -> bool:
    """Called on every group text. True = handled (a start word or a vote reply)."""
    chat, user = message.chat, message.from_user
    if n in START_WORDS:
        active = await col("group_hunts").find_one({"chat_id": chat.id, "status": "running"})
        if active:
            await message.reply(_t("fa", "busy"))
            return True
        chase = E.new_chase(random.Random())
        E.make_hint(chase, random.Random())
        doc = {"_id": uuid.uuid4().hex, "chat_id": chat.id, "chase": chase, "votes": {}, "names": {},
               "status": "running", "round_ends": int(time.time()) + ROUND_SECONDS}
        msg = await message.bot.send_message(chat.id, _group_text("fa", chase, {}, {}, ROUND_SECONDS))
        doc["msg_id"] = msg.message_id
        doc["msg_ids"] = [msg.message_id]
        await col("group_hunts").insert_one(doc)
        return True
    if n in WORD_TO_DIR and message.reply_to_message is not None:
        rid = message.reply_to_message.message_id
        doc = await col("group_hunts").find_one({"chat_id": chat.id, "status": "running",
                                                "$or": [{"msg_id": rid}, {"msg_ids": rid}]})
        if not doc:
            return False
        await col("group_hunts").update_one(
            {"_id": doc["_id"]},
            {"$set": {f"votes.{user.id}": WORD_TO_DIR[n], f"names.{user.id}": user.full_name or str(user.id)}})
        return True
    return False


async def _finish_group(bot, doc, caught: bool):
    chase = doc["chase"]
    chat_id = doc["chat_id"]
    from render import glang
    from service_world import group_doc
    lang = glang(await group_doc(chat_id))
    if not caught:
        await bot.send_message(chat_id, _t(lang, "escaped_group"))
        return
    players = len(chase["correct_votes"]) or 1
    pool = E.catch_pool(60, 60, players)
    settled = E.settle(chase, pool["coins"])
    lines = []
    for uid, coins in settled["payouts"].items():
        if coins:
            await add_coins(int(uid), coins, "hunt_group")
            name = esc(doc.get("names", {}).get(uid, uid))
            lines.append(f"• {name}: +{fnum(coins, lang)} 🪙")
    mvp = ""
    if settled["mvp"]:
        mvp_name = esc(doc.get("names", {}).get(settled["mvp"], settled["mvp"]))
        mvp = _t(lang, "mvp", name=mvp_name)
        iid = await roll_drop(int(settled["mvp"]))
        await inv_add(int(settled["mvp"]), iid, 1)
    await bot.send_message(chat_id, _t(lang, "caught", rewards="\n".join(lines) or "—", mvp=mvp))


async def group_tick(bot) -> int:
    """Scheduler: close every group round whose timer has passed. Returns how many rounds closed."""
    now = int(time.time())
    closed = 0
    async for doc in col("group_hunts").find({"status": "running", "round_ends": {"$lte": now}}):
        chase = doc["chase"]
        votes = {int(k): v for k, v in (doc.get("votes") or {}).items()}
        res = E.resolve_round(chase, votes, random.Random())
        closed += 1
        if res["status"] == "running":
            E.make_hint(chase, random.Random())
            if res["outcome"] == "correct":
                extra = _t("fa", "round_ok", n=chase["round"], total=E.CATCH_AT)
            elif res["outcome"] == "wrong":
                extra = _t("fa", "round_bad", s=chase["stamina"])
            else:
                extra = _t("fa", "round_none", s=chase["stamina"])
            msg = await bot.send_message(doc["chat_id"],
                                         _group_text("fa", chase, doc.get("names", {}), {}, ROUND_SECONDS, extra))
            await col("group_hunts").update_one(
                {"_id": doc["_id"]},
                {"$set": {"chase": chase, "votes": {}, "round_ends": now + ROUND_SECONDS, "msg_id": msg.message_id},
                 "$push": {"msg_ids": msg.message_id}})
        else:
            await col("group_hunts").update_one({"_id": doc["_id"]}, {"$set": {"chase": chase, "status": res["status"]}})
            await _finish_group(bot, {**doc, "chase": chase}, res["status"] == "caught")
    return closed
