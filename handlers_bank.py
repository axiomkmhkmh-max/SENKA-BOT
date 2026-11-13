"""Bleach Bank panels: vault, deposits and withdrawals, loans, savings bonds, upgrades, security, transfers, statement."""
import service_bank as SB
import engine_bank as B
from i18n import fnum
from service_player import get_char
from database import col
from service_player import get_char as _gc
from ui import Out, action, head, input_handler, nav
import time


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
}


def _err(ctx, key):
    fa, en = ERRORS.get(key, ("خطا.", "Error."))
    return Out(alert=_L(ctx, fa, en))


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
    if acc.get("collectors"):
        c = acc["collectors"]
        lines.append(f"🕴 {_L(ctx, 'ماموران گوتی ۱۳ روی تو هستن', 'Gotei 13 collectors are on you')}: "
                     f"{fnum(c['owed'] - c['taken'], L)} {_L(ctx, 'مانده', 'left')}")
    if acc.get("bonds"):
        lines.append(f"📜 {_L(ctx, 'اوراق باز', 'Open bonds')}: {len(acc['bonds'])}")
    lines.append(f"📈 {_L(ctx, 'بهره‌ی روزانه', 'Daily interest')}: {B.DAILY_INTEREST * 100:.1f}%")
    return "\n".join(lines)


@action("bnk")
async def bank_home(ctx, arg):
    ch = await get_char(ctx.uid)
    if not ch:
        return _err(ctx, "no_char")
    events = await SB.daily_tick(ctx.uid)
    acc = await SB.load(ctx.uid)
    body = _vault_text(ctx, acc, ch)
    if events:
        names = {"interest": _L(ctx, "بهره", "interest"), "bond": _L(ctx, "اوراق", "bond"),
                 "raid": _L(ctx, "حمله‌ی هالو", "Hollow raid"), "espada": _L(ctx, "حمله‌ی اسپادا", "Espada raid"),
                 "default": _L(ctx, "نکول وام", "loan default"), "collectors": _L(ctx, "ماموران", "collectors")}
        body = "\n".join(f"• {names.get(k, k)}: {'+' if k in ('interest', 'bond') else '-'}{fnum(v, ctx.lang)}" for k, v in events) + "\n\n" + body
    rows = [
        [(_L(ctx, "⬇️ واریز", "⬇️ Deposit"), "bnk_dep", "menu"), (_L(ctx, "⬆️ برداشت", "⬆️ Withdraw"), "bnk_wdr", "menu")],
        [(_L(ctx, "💳 وام", "💳 Loan"), "bnk_loan", "menu"), (_L(ctx, "🧾 پرداخت وام", "🧾 Repay"), "bnk_repay", "")],
        [(_L(ctx, "📜 اوراق", "📜 Bonds"), "bnk_bond", "menu"), (_L(ctx, "🏗 ارتقای گاوصندوق", "🏗 Upgrade vault"), "bnk_upg", "menu")],
        [(_L(ctx, "🛡 امنیت", "🛡 Security"), "bnk_sec", ""), (_L(ctx, "🎫 بیمه", "🎫 Insurance"), "bnk_ins", "menu")],
        [(_L(ctx, "📤 انتقال", "📤 Send"), "bnk_send", ""), (_L(ctx, "🧾 صورت‌حساب", "🧾 Statement"), "bnk_stmt", "")],
        nav(ctx),
    ]
    return Out(head(ctx, "ttl_bank") + body, rows)


@action("bnk_dep")
async def bank_deposit(ctx, arg):
    if arg == "menu":
        return Out(head(ctx, "ttl_bank") + _L(ctx, "چقدر واریز کنی؟", "How much to deposit?"),
                   [[(fnum(a, ctx.lang), "bnk_dep", str(a)) for a in AMOUNTS], nav(ctx, ("bnk", ""))])
    acc, err = await SB.deposit(ctx.uid, int(arg))
    if err:
        return _err(ctx, err)
    return Out(alert=_L(ctx, "واریز شد.", "Deposited."), new=False)


@action("bnk_wdr")
async def bank_withdraw(ctx, arg):
    if arg == "menu":
        return Out(head(ctx, "ttl_bank") + _L(ctx, "چقدر برداشت کنی؟ (کارمزد بر اساس سطح)", "How much to withdraw? (fee depends on tier)"),
                   [[(fnum(a, ctx.lang), "bnk_wdr", str(a)) for a in AMOUNTS], nav(ctx, ("bnk", ""))])
    acc, err = await SB.withdraw(ctx.uid, int(arg))
    if err:
        return _err(ctx, err)
    return Out(alert=_L(ctx, "برداشت انجام شد.", "Withdrawn."))


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
    return Out(alert=_L(ctx, "وام گرفته شد. ۷ روز مهلت داری.", "Loan granted. You have 7 days to repay."))


@action("bnk_repay")
async def bank_repay(ctx, arg):
    acc, err = await SB.repay(ctx.uid)
    if err:
        return _err(ctx, err)
    return Out(alert=_L(ctx, "وام پرداخت شد.", "Loan repaid."))


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
    return Out(alert=_L(ctx, "اوراق باز شد.", "Bond opened."))


@action("bnk_upg")
async def bank_upgrade(ctx, arg):
    if arg == "menu":
        rows = [[(B.TIERS[t][0], "bnk_upg", str(t)) for t in range(1, len(B.TIERS))], nav(ctx, ("bnk", ""))]
        return Out(head(ctx, "ttl_bank") + _L(ctx, "کدام سطح؟ هزینه‌ی ارتقا از سطح پایین‌تر بیشتر است.", "Which tier? Cost is a share of the target tier's minimum."), rows)
    acc, err = await SB.upgrade(ctx.uid, int(arg))
    if err:
        return _err(ctx, err)
    return Out(alert=_L(ctx, "گاوصندوق ارتقا یافت.", "Vault upgraded."))


@action("bnk_sec")
async def bank_security(ctx, arg):
    acc, err = await SB.security(ctx.uid)
    if err:
        return _err(ctx, err)
    return Out(alert=_L(ctx, "امنیت گاوصندوق بالا رفت.", "Vault security increased."))


@action("bnk_ins")
async def bank_insurance(ctx, arg):
    if arg == "menu":
        return Out(head(ctx, "ttl_bank") + _L(ctx, "چند روز بیمه شوی؟ هزینه روزانه ۲٪ موجودی.", "How many days? 2% of balance per day."),
                   [[(_L(ctx, f"{d} روز", f"{d} days"), "bnk_ins", str(d)) for d in (1, 3, 7)], nav(ctx, ("bnk", ""))])
    acc = await SB.load(ctx.uid)
    r = B.buy_insurance(acc, int(arg))
    if not r["ok"]:
        return _err(ctx, r["reason"])
    await SB.save(acc)
    return Out(alert=_L(ctx, "بیمه خریده شد.", "Insurance bought."))


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



@action("bnk_send")
async def bank_send(ctx, arg):
    """Step 1: ask for the receiver's player id."""
    await col("inputs").update_one({"user_id": ctx.uid},
                                   {"$set": {"kind": "bank_send_to", "at": int(time.time())}}, upsert=True)
    return Out(head(ctx, "ttl_bank") + _L(ctx, "شناسه‌ی گیرنده را بفرست (عدد). ۱٪ کارمزد و در مبالغ بالا احتمال حسابرسی.",
                                             "Send the receiver's player id (number). 1% fee; big sends can be audited."),
               [nav(ctx, ("bnk", ""))])


@input_handler("bank_send_to")
async def bank_send_to_input(ctx, text):
    try:
        target = int(text.strip())
    except ValueError:
        return Out(_L(ctx, "فقط عدد بفرست.", "Send a number only."))
    if target == ctx.uid:
        return _err(ctx, "self")
    if not await _gc(target):
        return Out(_L(ctx, "این بازیکن پیدا نشد.", "Player not found."))
    await col("inputs").update_one({"user_id": ctx.uid},
                                   {"$set": {"kind": "bank_send_amt", "target": target, "at": int(time.time())}})
    return Out(_L(ctx, "چقدر بفرستی؟ (عدد)", "How much to send? (number)"))


@input_handler("bank_send_amt")
async def bank_send_amt_input(ctx, text):
    doc = await col("inputs").find_one({"user_id": ctx.uid}) or {}
    target = doc.get("target")
    try:
        amount = int(text.strip())
    except ValueError:
        return Out(_L(ctx, "فقط عدد بفرست.", "Send a number only."))
    await col("inputs").delete_one({"user_id": ctx.uid})
    if not target:
        return _err(ctx, "no_char")
    import service_bank as SB
    r, err = await SB.transfer(ctx.uid, int(target), amount)
    if err:
        return _err(ctx, err)
    lines = [_L(ctx, f"📤 فرستادی: {fnum(r['sent'], ctx.lang)}", f"📤 Sent: {fnum(r['sent'], ctx.lang)}"),
             _L(ctx, f"کارمزد: {fnum(r['fee'], ctx.lang)}", f"Fee: {fnum(r['fee'], ctx.lang)}")]
    if r["audit"]:
        lines.append(_L(ctx, f"🕴 حسابرسی گوتی ۱۳: {fnum(r['audit'], ctx.lang)}", f"🕴 Gotei 13 audit: {fnum(r['audit'], ctx.lang)}"))
    return Out("\n".join(lines), [[(_L(ctx, "🏦 بانک", "🏦 Bank"), "bnk", "")]])
