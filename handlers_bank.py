"""Bleach Bank panels: vault, deposits and withdrawals, loans, savings bonds, upgrades, security, transfers, statement.
Also the reply command for player-to-player coin transfers (`انتقال 1000` as a reply in a group) and its confirm button."""
import time
import uuid
from datetime import datetime, timedelta, timezone

import service_bank as SB
import engine_bank as B
from database import col, game_settings
from engine_xfer import fee_for, parse_number, parse_transfer
from i18n import esc, fnum
from render import glang
from security import allow
from service_player import get_char
from service_world import group_doc
from ui import Ctx, Out, action, head, input_handler, markup, nav


def _L(ctx, fa, en):
    return fa if ctx.lang == "fa" else en


AMOUNTS = [10_000, 100_000, 1_000_000]

ERRORS = {
    "insufficient": ("موجودی کافی نیست.", "Not enough funds."),
    "no_char": ("اول ثبت‌نام کن.", "Register first."),
    "over_limit": ("بیشتر از سقف وام امتیاز اعتباری تو است.", "Above your credit-based loan limit."),
    "already_has_loan": ("یک وام فعال داری؛ اول پسش بده.", "You already have a loan. Repay it first."),
    "no_loan": ("وام فعالی نداری.", "You have no active loan."),
    "bad_term": ("این مدت قفل معتبر نیست.", "Invalid lock term."),
    "not_needed": ("این سطح الان لازم نیست.", "That tier is not needed."),
    "max": ("امنیت گاوصندوق در بالاترین سطح است.", "Vault security is already maxed."),
    "self": ("به خودت نمی‌تونی پول بفرستی.", "You cannot send money to yourself."),
    "no_bond": ("اوراق پیدا نشد.", "Bond not found."),
    "has_debt": ("بدهی معوقه داری؛ تا صافش نکنی وام جدید نمی‌دن.", "You have unpaid debt. No new loan until it is cleared."),
    "debt_left": ("هر چی تو بانک و جیبت بود برداشته شد، ولی هنوز بدهی مونده.", "Everything in your vault and wallet was taken, but some debt is still left."),
    "busy": ("بانک شلوغه، یه لحظه دیگه دوباره بزن.", "The bank is busy. Try again in a moment."),
    "bad_amount": ("مبلغ باید بیشتر از صفر باشه.", "The amount must be above zero."),
    "max_days": (f"بیمه‌ی فعالت نباید از {B.MAX_INSURED_DAYS} روز بیشتر بشه.", f"Active insurance cannot go above {B.MAX_INSURED_DAYS} days."),
    "balance_low": ("با پرداخت این ارتقا موجودیت از نصفِ حداقل آن سطح پایین‌تر می‌آید و ارتقا بلافاصله باطل می‌شد. اول موجودی را بیشتر کن.",
                    "Paying for this upgrade would drop your balance under half of the tier minimum and it would lapse at once. Deposit more first."),
    "too_small": ("این مبلغ برای انتقال خیلی کمه.", "That amount is too small to send."),
    "no_sender": ("اول ثبت‌نام کن.", "Register first."),
    "no_target": ("گیرنده هنوز ثبت‌نام نکرده.", "The receiver has not registered yet."),
    "new_acct": ("حساب تازه‌ساخته‌ست؛ چند دقیقه بعد می‌تونی سکه بفرستی.", "Your account is too new to send coins. Try again in a few minutes."),
    "low_level": ("سطحت برای انتقال سکه کمه.", "Your level is too low to send coins."),
    "cap": ("سقف انتقال امروزت پر شده.", "Your daily transfer cap is reached."),
}


def _text(ctx, key):
    fa, en = ERRORS.get(key, ("خطا.", "Error."))
    return _L(ctx, fa, en)


def _err(ctx, key):
    """Popup error for a button press."""
    return Out(alert=_text(ctx, key))


def _errt(ctx, key):
    """Error for a typed answer: a popup cannot be shown there (nothing is sent for an alert-only Out), so it is a message."""
    return Out(_text(ctx, key), [[(_L(ctx, "🏦 بانک", "🏦 Bank"), "bnk", "")]])


def _vault_text(ctx, acc, ch):
    L = ctx.lang
    st = B.statement(acc)
    tier = B.TIERS[B.effective_tier(acc)][0]
    lines = [
        f"🏦 {_L(ctx, 'گاوصندوق', 'Vault')}: <b>{tier}</b>",
        f"💰 {_L(ctx, 'موجودی', 'Balance')}: {fnum(acc['balance'], L)}",
        f"🪙 {_L(ctx, 'سکه‌ی جیب', 'Wallet')}: {fnum(ch['coins'], L)}",
        f"📊 {_L(ctx, 'امتیاز اعتباری', 'Credit score')}: {fnum(acc.get('credit', B.CREDIT_START), L)}",
        f"🛡 {_L(ctx, 'امنیت', 'Security')}: {acc.get('security', 0)}/{len(B.SECURITY_LEVELS) - 1}",
        f"🎫 {_L(ctx, 'بیمه', 'Insurance')}: {acc.get('insured_days', 0)} {_L(ctx, 'روز', 'days')}",
    ]
    if acc.get("loans"):
        lines.append(f"🧾 {_L(ctx, 'بدهی', 'Owed')}: {fnum(acc['loans'][0]['owed'], L)}")
    if int(acc.get("debt", 0)) > 0:
        lines.append(f"⛔ {_L(ctx, 'بدهی معوقه (از بانک و جیبت برداشته می‌شه)', 'Overdue debt (taken from vault and wallet)')}: "
                     f"{fnum(acc['debt'], L)}")
    if acc.get("collectors"):
        c = acc["collectors"]
        lines.append(f"🕴 {_L(ctx, 'ماموران گوتی ۱۳ روی تو هستن', 'Gotei 13 collectors are on you')}: "
                     f"{fnum(c['owed'] - c['taken'], L)} {_L(ctx, 'مانده', 'left')}")
    if acc.get("bonds"):
        lines.append(f"📜 {_L(ctx, 'اوراق باز', 'Open bonds')}: {len(acc['bonds'])}")
    lines.append(f"📈 {_L(ctx, 'بهره‌ی روزانه', 'Daily interest')}: {B.DAILY_INTEREST * 100:.1f}%")
    return "\n".join(lines)



async def _panel(ctx, events=None, alert=None):
    """The bank home panel (fresh numbers). Every button below ends here, so the player sees the new balance at once."""
    ch = await get_char(ctx.uid)
    if not ch:
        return _err(ctx, "no_char")
    acc = await SB.load(ctx.uid)
    body = _vault_text(ctx, acc, ch)
    if events:
        names = {"interest": _L(ctx, "بهره", "interest"), "bond": _L(ctx, "اوراق", "bond"),
                 "raid": _L(ctx, "حمله‌ی هالو", "Hollow raid"), "espada": _L(ctx, "حمله‌ی اسپادا", "Espada raid"),
                 "default": _L(ctx, "نکول وام", "loan default"), "collectors": _L(ctx, "ماموران", "collectors"),
                 "debt": _L(ctx, "وصول بدهی", "debt collected")}
        body = "\n".join(f"• {names.get(k, k)}: {'+' if k in ('interest', 'bond') else '-'}{fnum(v, ctx.lang)}" for k, v in events) + "\n\n" + body
    rows = [
        [(_L(ctx, "⬇️ واریز", "⬇️ Deposit"), "bnk_dep", "menu"), (_L(ctx, "⬆️ برداشت", "⬆️ Withdraw"), "bnk_wdr", "menu")],
        [(_L(ctx, "💳 وام", "💳 Loan"), "bnk_loan", "menu"), (_L(ctx, "🧾 پرداخت وام", "🧾 Repay"), "bnk_repay", "")],
        [(_L(ctx, "📜 اوراق", "📜 Bonds"), "bnk_bond", "menu"), (_L(ctx, "🏗 ارتقای گاوصندوق", "🏗 Upgrade vault"), "bnk_upg", "menu")],
        [(_L(ctx, "🛡 امنیت", "🛡 Security"), "bnk_sec", ""), (_L(ctx, "🎫 بیمه", "🎫 Insurance"), "bnk_ins", "menu")],
        [(_L(ctx, "📤 انتقال", "📤 Send"), "bnk_send", ""), (_L(ctx, "🧾 صورت‌حساب", "🧾 Statement"), "bnk_stmt", "")],
        nav(ctx),
    ]
    out = Out(head(ctx, "ttl_bank") + body, rows)
    out.alert = alert
    return out


@action("bnk")
async def bank_home(ctx, arg):
    if not await get_char(ctx.uid):
        return _err(ctx, "no_char")
    events = await SB.daily_tick(ctx.uid)
    return await _panel(ctx, events)


def _amount_menu(ctx, code, prompt):
    rows = [[(fnum(a, ctx.lang), code, str(a)) for a in AMOUNTS],
            [(_L(ctx, "همه", "All"), code, "all"), (_L(ctx, "✍️ مبلغ دلخواه", "✍️ Custom amount"), code, "custom")],
            nav(ctx, ("bnk", ""))]
    return Out(head(ctx, "ttl_bank") + prompt, rows)


def _max_withdraw(acc) -> int:
    """The largest amount whose fee still fits in the vault (the fee is taken on top of the amount)."""
    pct = B.TIERS[B.effective_tier(acc)][2]
    amount = int(acc["balance"] / (1 + pct))
    while amount > 0 and amount + int(amount * pct) > acc["balance"]:
        amount -= 1
    return max(0, amount)


async def _ask_amount(ctx, kind, prompt):
    await col("inputs").update_one({"user_id": ctx.uid}, {"$set": {"kind": kind, "at": int(time.time())}}, upsert=True)
    return Out(head(ctx, "ttl_bank") + prompt, [nav(ctx, ("bnk", ""))])


@action("bnk_dep")
async def bank_deposit(ctx, arg):
    if arg == "menu":
        return _amount_menu(ctx, "bnk_dep", _L(ctx, "چقدر واریز کنی؟", "How much to deposit?"))
    if arg == "custom":
        return await _ask_amount(ctx, "bank_dep_amt", _L(ctx, "مبلغ واریز را بفرست (مثلاً 5000 یا 5k).", "Send the amount to deposit (e.g. 5000 or 5k)."))
    if arg == "all":
        ch = await get_char(ctx.uid)
        amount = int((ch or {}).get("coins", 0))
    else:
        amount = int(arg)
    acc, err = await SB.deposit(ctx.uid, amount)
    if err:
        return _err(ctx, err)
    return await _panel(ctx, alert=_L(ctx, f"واریز شد: {fnum(amount, ctx.lang)}", f"Deposited: {fnum(amount, ctx.lang)}"))


@action("bnk_wdr")
async def bank_withdraw(ctx, arg):
    if arg == "menu":
        return _amount_menu(ctx, "bnk_wdr", _L(ctx, "چقدر برداشت کنی؟ (کارمزد بر اساس سطح، روی مبلغ اضافه می‌شود)",
                                               "How much to withdraw? (the tier fee is added on top)"))
    if arg == "custom":
        return await _ask_amount(ctx, "bank_wdr_amt", _L(ctx, "مبلغ برداشت را بفرست (مثلاً 5000 یا 5k).", "Send the amount to withdraw (e.g. 5000 or 5k)."))
    if arg == "all":
        amount = _max_withdraw(await SB.load(ctx.uid))
    else:
        amount = int(arg)
    acc, err = await SB.withdraw(ctx.uid, amount)
    if err:
        return _err(ctx, err)
    return await _panel(ctx, alert=_L(ctx, f"برداشت شد: {fnum(amount, ctx.lang)}", f"Withdrawn: {fnum(amount, ctx.lang)}"))


async def _typed_amount(ctx, text, kind, fn, ok_fa, ok_en):
    amount = parse_number(text)
    if amount is None:  # not a number: ask again instead of dropping the prompt
        await col("inputs").update_one({"user_id": ctx.uid}, {"$set": {"kind": kind, "at": int(time.time())}}, upsert=True)
        return Out(_L(ctx, "فقط یک عدد بفرست (مثلاً 5000 یا 5k). برای انصراف بنویس «لغو».", "Send a number only (e.g. 5000 or 5k). Write cancel to stop."))
    acc, err = await fn(ctx.uid, amount)
    if err:
        return _errt(ctx, err)
    out = await _panel(ctx)
    out.text = _L(ctx, ok_fa.format(n=fnum(amount, ctx.lang)), ok_en.format(n=fnum(amount, ctx.lang))) + "\n\n" + out.text
    return out


@input_handler("bank_dep_amt")
async def bank_dep_amt_input(ctx, text):
    return await _typed_amount(ctx, text, "bank_dep_amt", SB.deposit, "✅ واریز شد: {n}", "✅ Deposited: {n}")


@input_handler("bank_wdr_amt")
async def bank_wdr_amt_input(ctx, text):
    return await _typed_amount(ctx, text, "bank_wdr_amt", SB.withdraw, "✅ برداشت شد: {n}", "✅ Withdrawn: {n}")


@action("bnk_loan")
async def bank_loan(ctx, arg):
    if arg == "menu":
        ch = await get_char(ctx.uid)
        acc = await SB.load(ctx.uid)
        limit = int(SB.collateral_value(ch) * B.credit_limit_pct(acc.get("credit", B.CREDIT_START)))
        return Out(head(ctx, "ttl_bank") + _L(ctx, f"سقف وام: {fnum(limit, ctx.lang)}", f"Loan limit: {fnum(limit, ctx.lang)}"),
                   [[(fnum(a, ctx.lang), "bnk_loan", str(a)) for a in AMOUNTS if a <= limit] or [(_L(ctx, "سقف کم است", "Limit too low"), "bnk_loan", "menu")], nav(ctx, ("bnk", ""))])
    acc, err = await SB.loan(ctx.uid, int(arg))
    if err:
        return _err(ctx, err)
    return await _panel(ctx, alert=_L(ctx, "وام گرفته شد. ۷ روز مهلت داری.", "Loan granted. You have 7 days to repay."))


@action("bnk_repay")
async def bank_repay(ctx, arg):
    acc, err = await SB.repay(ctx.uid)
    if err:
        return _err(ctx, err)
    return await _panel(ctx, alert=_L(ctx, "وام پرداخت شد.", "Loan repaid."))


@action("bnk_bond")
async def bank_bond(ctx, arg):
    if arg == "menu":
        rows = [[(_L(ctx, f"{d} روز", f"{d} days"), "bnk_bond", f"{d}") for d in B.BOND_TERMS], nav(ctx, ("bnk", ""))]
        return Out(head(ctx, "ttl_bank") + _L(ctx, "مدت قفل را انتخاب کن. شکستن زودهنگام ۲۰٪ جریمه دارد.", "Pick a lock term. Early break costs 20%."), rows)
    if "|" not in arg:
        return Out(head(ctx, "ttl_bank") + _L(ctx, "مبلغ را انتخاب کن.", "Pick an amount."),
                   [[(fnum(a, ctx.lang), "bnk_bond", f"{arg}|{a}") for a in AMOUNTS], nav(ctx, ("bnk_bond", "menu"))])
    term, amt = arg.split("|")
    acc, err = await SB.open_bond(ctx.uid, int(amt), int(term))
    if err:
        return _err(ctx, err)
    return await _panel(ctx, alert=_L(ctx, "اوراق باز شد.", "Bond opened."))


@action("bnk_upg")
async def bank_upgrade(ctx, arg):
    if arg == "menu":
        rows = [[(B.TIERS[t][0], "bnk_upg", str(t)) for t in range(1, len(B.TIERS))], nav(ctx, ("bnk", ""))]
        return Out(head(ctx, "ttl_bank") + _L(ctx, "کدام سطح؟ هزینه‌ی ارتقا از سطح پایین‌تر بیشتر است.", "Which tier? Cost is a share of the target tier's minimum."), rows)
    acc, err = await SB.upgrade(ctx.uid, int(arg))
    if err:
        return _err(ctx, err)
    return await _panel(ctx, alert=_L(ctx, "گاوصندوق ارتقا یافت.", "Vault upgraded."))


@action("bnk_sec")
async def bank_security(ctx, arg):
    acc, err = await SB.security(ctx.uid)
    if err:
        return _err(ctx, err)
    return await _panel(ctx, alert=_L(ctx, "امنیت گاوصندوق بالا رفت.", "Vault security increased."))


@action("bnk_ins")
async def bank_insurance(ctx, arg):
    if arg == "menu":
        return Out(head(ctx, "ttl_bank") + _L(ctx, "چند روز بیمه شوی؟ هزینه روزانه ۲٪ موجودی.", "How many days? 2% of balance per day."),
                   [[(_L(ctx, f"{d} روز", f"{d} days"), "bnk_ins", str(d)) for d in (1, 3, 7)], nav(ctx, ("bnk", ""))])
    acc, err = await SB.insurance(ctx.uid, int(arg))
    if err:
        return _err(ctx, err)
    return await _panel(ctx, alert=_L(ctx, "بیمه خریده شد.", "Insurance bought."))


@action("bnk_stmt")
async def bank_statement(ctx, arg):
    st = await SB.statement(ctx.uid)
    L = ctx.lang
    lines = [f"{_L(ctx, 'تراکنش‌ها', 'Entries')}: {fnum(st['entries'], L)}",
             f"⬆️ {_L(ctx, 'ورودی', 'In')}: {fnum(st['in'], L)}",
             f"⬇️ {_L(ctx, 'خروجی', 'Out')}: {fnum(st['out'], L)}",
             f"📊 {_L(ctx, 'امتیاز اعتباری', 'Credit')}: {fnum(st['credit'], L)}"]
    recent = st["acc"].get("ledger", [])[-8:]
    for e in reversed(recent):
        sign = "+" if e["a"] > 0 else ""
        lines.append(f"• {e['k']}: {sign}{fnum(e['a'], L)}")
    return Out(head(ctx, "ttl_bank") + "\n".join(lines), [nav(ctx, ("bnk", ""))])


# ---- vault-to-vault transfer by player id --------------------------------------------------------------------------
@action("bnk_send")
async def bank_send(ctx, arg):
    """Step 1: ask for the receiver's player id."""
    await col("inputs").update_one({"user_id": ctx.uid}, {"$set": {"kind": "bank_send_to", "at": int(time.time())}}, upsert=True)
    return Out(head(ctx, "ttl_bank") + _L(ctx, "شناسه‌ی گیرنده را بفرست (عدد). ۱٪ کارمزد و در مبالغ بالا احتمال حسابرسی.\n"
                                                "برای فرستادن سکه‌ی جیب، در گروه روی پیام بازیکن ریپلای کن و بنویس: <code>انتقال 1000</code>",
                                             "Send the receiver's player id (number). 1% fee; big sends can be audited.\n"
                                             "To send wallet coins, reply to a player in a group and write: <code>transfer 1000</code>"),
               [nav(ctx, ("bnk", ""))])


@input_handler("bank_send_to")
async def bank_send_to_input(ctx, text):
    target = parse_number(text)
    if target is None:
        await col("inputs").update_one({"user_id": ctx.uid}, {"$set": {"kind": "bank_send_to", "at": int(time.time())}}, upsert=True)
        return Out(_L(ctx, "فقط عدد بفرست. برای انصراف بنویس «لغو».", "Send a number only. Write cancel to stop."))
    if target == ctx.uid:
        return _errt(ctx, "self")
    if not await get_char(target):
        return Out(_L(ctx, "این بازیکن پیدا نشد.", "Player not found."), [[(_L(ctx, "🏦 بانک", "🏦 Bank"), "bnk", "")]])
    # The pending prompt is already consumed when this handler runs, so it is written again with upsert (before, a plain
    # update matched nothing and the amount step never started), and the target travels in it.
    await col("inputs").update_one({"user_id": ctx.uid}, {"$set": {"kind": "bank_send_amt", "target": target, "at": int(time.time())}}, upsert=True)
    return Out(_L(ctx, "چقدر بفرستی؟ (عدد)", "How much to send? (number)"))


@input_handler("bank_send_amt")
async def bank_send_amt_input(ctx, text):
    target = int((getattr(ctx, "pend", None) or {}).get("target") or 0)  # the pending prompt (already removed) is handed over by the dispatcher
    if not target:
        return _errt(ctx, "no_char")
    amount = parse_number(text)
    if amount is None:
        await col("inputs").update_one({"user_id": ctx.uid}, {"$set": {"kind": "bank_send_amt", "target": target, "at": int(time.time())}}, upsert=True)
        return Out(_L(ctx, "فقط عدد بفرست. برای انصراف بنویس «لغو».", "Send a number only. Write cancel to stop."))
    r, err = await SB.transfer(ctx.uid, target, amount)
    if err:
        return _errt(ctx, err)
    lines = [_L(ctx, f"📤 فرستادی: {fnum(r['sent'], ctx.lang)}", f"📤 Sent: {fnum(r['sent'], ctx.lang)}"),
             _L(ctx, f"کارمزد: {fnum(r['fee'], ctx.lang)}", f"Fee: {fnum(r['fee'], ctx.lang)}")]
    if r["audit"]:
        lines.append(_L(ctx, f"🕴 حسابرسی گوتی ۱۳: {fnum(r['audit'], ctx.lang)}", f"🕴 Gotei 13 audit: {fnum(r['audit'], ctx.lang)}"))
    try:  # the receiver should learn about it (a blocked bot must not break the transfer)
        me = esc(ctx.user.full_name or ctx.user.first_name or "")
        await ctx.bot.send_message(target, f"🏦 {me}: +{fnum(r['sent'], 'fa')} 🪙 → گاوصندوق تو / into your vault")
    except Exception:
        pass
    return Out("\n".join(lines), [[(_L(ctx, "🏦 بانک", "🏦 Bank"), "bnk", "")]])


# ---- wallet-to-wallet transfer by replying to a player: «انتقال 1000» ----------------------------------------------
def _mention(uid: int, name: str) -> str:
    return f'<a href="tg://user?id={int(uid)}">{esc(name or str(uid))}</a>'


def _sent_text(lang, a, b, r):
    fa = lang == "fa"
    n, f = fnum(r["sent"], lang), fnum(r["fee"], lang)
    return (f"💸 {a} مبلغ <b>{n}</b> 🪙 به {b} انتقال داد.\nکارمزد: {f} 🪙" if fa
            else f"💸 {a} sent <b>{n}</b> 🪙 to {b}.\nFee: {f} 🪙")


async def transfer_hook(message, text: str, n: str) -> bool:
    """Group word: reply to a player and write «انتقال 1000» (also: transfer / send, 5k, ۲ میلیون, 1,000 سکه).
    True = the message was a transfer command and has been answered."""
    amount = parse_transfer(text)
    if amount is None:
        return False
    user, chat = message.from_user, message.chat
    if not allow(user.id, "xfer", 2.0):  # a double send of the same message does not pay twice
        return True
    lang = glang(await group_doc(chat.id))
    ctx = Ctx(user.id, lang, chat.id, chat.type, user, message.bot, message)
    reply = message.reply_to_message
    target = reply.from_user if reply and reply.from_user and not reply.from_user.is_bot else None
    if not target:
        await message.reply(_L(ctx, "برای انتقال سکه روی پیامِ بازیکن ریپلای کن و بنویس: <code>انتقال 1000</code>",
                               "Reply to a player's message and write: <code>transfer 1000</code>"))
        return True
    if target.id == user.id:
        await message.reply(_text(ctx, "self"))
        return True
    st = await game_settings()
    me_name, to_name = user.full_name or user.first_name or "", target.full_name or target.first_name or ""
    if amount >= int(st.get("xfer_confirm_over", 50_000)):  # a typo with an extra zero must not cost a fortune: ask first
        fee = fee_for(amount, st.get("xfer_fee_pct", 0.05))
        me = await get_char(user.id)  # obvious refusals come before the question, so nobody confirms something that cannot happen
        if not me:
            await message.reply(_text(ctx, "no_sender"))
            return True
        if amount > int(st.get("xfer_daily_cap", 500_000)):
            await message.reply(_text(ctx, "cap"))
            return True
        if int(me.get("coins", 0)) < amount + fee:
            await message.reply(_text(ctx, "insufficient"))
            return True
        token = uuid.uuid4().hex[:12]
        now = int(time.time())
        await col("pending_xfers").insert_one({"_id": token, "uid": user.id, "to": target.id, "to_name": to_name, "amount": amount,
                                               "exp": now + 120, "expire_at": datetime.now(timezone.utc) + timedelta(minutes=10)})
        ask = _L(ctx, f"⚠️ مطمئنی؟ {fnum(amount, lang)} 🪙 به {_mention(target.id, to_name)} منتقل بشه؟\nکارمزد: {fnum(fee, lang)} 🪙 (از تو کم می‌شه)",
                 f"⚠️ Sure? Send {fnum(amount, lang)} 🪙 to {_mention(target.id, to_name)}?\nFee: {fnum(fee, lang)} 🪙 (added to your cost)")
        rows = [[(_L(ctx, "✅ تأیید", "✅ Confirm"), "xfc", f"y.{token}", False, "success"), (_L(ctx, "❌ لغو", "❌ Cancel"), "xfc", f"n.{token}", False, "danger")]]
        await message.reply(ask, reply_markup=markup(ctx, rows))
        return True
    r, err = await SB.wallet_transfer(user.id, target.id, amount)
    if err:
        await message.reply(_text(ctx, err))
        return True
    await message.reply(_sent_text(lang, _mention(user.id, me_name), _mention(target.id, to_name), r))
    return True


@action("xfc")
async def transfer_confirm(ctx, arg):
    """Confirm / cancel button of a big transfer. Only the sender can press it (signed button) and a token works once."""
    yes, _, token = (arg or "").partition(".")
    doc = await col("pending_xfers").find_one_and_delete({"_id": token, "uid": ctx.uid})
    if not doc or int(doc.get("exp", 0)) < time.time():
        return Out(alert=_L(ctx, "این درخواست منقضی شده؛ دوباره بنویس.", "This request expired. Write the command again."))
    if yes != "y":
        return Out(_L(ctx, "❌ انتقال لغو شد.", "❌ Transfer cancelled."), [])
    r, err = await SB.wallet_transfer(ctx.uid, int(doc["to"]), int(doc["amount"]))
    if err:
        return Out(_text(ctx, err), [])
    me = _mention(ctx.uid, ctx.user.full_name or ctx.user.first_name or "")
    return Out(_sent_text(ctx.lang, me, _mention(doc["to"], doc.get("to_name", "")), r), [])
