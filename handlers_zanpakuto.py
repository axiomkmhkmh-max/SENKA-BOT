"""Zanpakuto progression: bond, Mastery training, Shikai / Bankai (and each race's equivalent) release.
State lives in characters.zanpakuto = {blade_id, bond, mastery, shikai, bankai}; combat reads it in service_combat.build_player.
Mastery grows by real use: every PvE win while released (+1) and the daily Training Grounds (energy cost, daily cap)."""
import time

from service_butterfly import butterfly
from data_items import ALL, iname
from data_misc import FORMS
from data_zanpakuto import (BETA_BLADES, BLADE_STAGES, PAID_BLADES, blade_price, blade_valid, reachable_blades, stage_name,
                            tier_label, unlocked_blades)
from data_world import day_id
from database import bump_counter, col, counter_get, game_settings, try_cooldown
from i18n import fnum
from service_player import add_coins, get_char, spend_energy
from ui import SEP, Out, action, nav

T = {  # key -> (fa, en)
    "title": ("\u26a1 \u0632\u0627\u0646\u067e\u0627\u06a9\u062a\u0648", "\u26a1 Zanpakut\u014d"),
    "body": ("\u062a\u06cc\u063a\u0647: <b>{blade}</b>\n\U0001f517 \u067e\u06cc\u0648\u0646\u062f: <b>{bond}</b>\n\U0001f4aa \u0645\u0647\u0627\u0631\u062a (Mastery): <b>{mastery}</b>/{cap}\n\n{f1}: {s1}\n{f2}: {s2}\n\n\U0001f3cb\ufe0f \u062a\u0645\u0631\u06cc\u0646 \u0627\u0645\u0631\u0648\u0632: {left}/{daily} (\u0647\u0631 \u0628\u0627\u0631 {gain} \u0645\u0647\u0627\u0631\u062a\u060c {cost} \u0627\u0646\u0631\u0698\u06cc)\n\u0647\u0631 \u067e\u06cc\u0631\u0648\u0632\u06cc PvE \u0628\u0627 \u0634\u06a9\u0644 \u0622\u0632\u0627\u062f\u0634\u062f\u0647 \u06f1 \u0645\u0647\u0627\u0631\u062a \u0645\u06cc\u200c\u062f\u0647\u062f.",
             "Blade: <b>{blade}</b>\n\U0001f517 Bond: <b>{bond}</b>\n\U0001f4aa Mastery: <b>{mastery}</b>/{cap}\n\n{f1}: {s1}\n{f2}: {s2}\n\n\U0001f3cb\ufe0f Training today: {left}/{daily} ({gain} Mastery each, {cost} energy)\nEvery PvE win while released gives +1 Mastery."),
    "on": ("\u2705 \u0641\u0639\u0627\u0644", "\u2705 unlocked"),
    "off": ("\U0001f512 \u0642\u0641\u0644 ({need})", "\U0001f512 locked ({need})"),
    "need_s": ("\u0633\u0637\u062d {lv} \u0648 \u067e\u06cc\u0648\u0646\u062f {bond}", "Lv.{lv}, bond {bond}"),
    "need_b": ("\u0633\u0637\u062d {lv}\u060c \u0645\u0631\u062d\u0644\u0647\u200c\u06cc \u0627\u0648\u0644 \u0648 \u0645\u0647\u0627\u0631\u062a {m}", "Lv.{lv}, first form and Mastery {m}"),
    "b_train": ("\U0001f3cb\ufe0f \u062a\u0645\u0631\u06cc\u0646", "\U0001f3cb\ufe0f Train"),
    "b_rel1": ("\U0001f525 \u0622\u0632\u0627\u062f\u0633\u0627\u0632\u06cc {f}", "\U0001f525 Unlock {f}"),
    "b_rel2": ("\U0001f4a5 \u0622\u0632\u0627\u062f\u0633\u0627\u0632\u06cc {f}", "\U0001f4a5 Unlock {f}"),
    "locked": ("\u0634\u0631\u0627\u06cc\u0637 \u0647\u0646\u0648\u0632 \u06a9\u0627\u0645\u0644 \u0646\u06cc\u0633\u062a.", "Requirements not met yet."),
    "done1": ("\U0001f525 {f} \u0622\u0632\u0627\u062f \u0634\u062f! \u0642\u062f\u0631\u062a \u0646\u0628\u0631\u062f\u062a \u0628\u0627\u0644\u0627 \u0631\u0641\u062a.", "\U0001f525 {f} unlocked! Your battle power rose."),
    "done2": ("\U0001f4a5 {f} \u0622\u0632\u0627\u062f \u0634\u062f! \u0627\u06cc\u0646 \u0642\u062f\u0631\u062a \u0645\u0647\u0627\u0631\u062a \u0645\u06cc\u200c\u06af\u06cc\u0631\u062f.", "\U0001f4a5 {f} unlocked! Mastery now amplifies it."),
    "wait": ("\u06a9\u0645\u06cc \u0635\u0628\u0631 \u06a9\u0646.", "Slow down a moment."),
    "cap": ("\u0633\u0642\u0641 \u062a\u0645\u0631\u06cc\u0646 \u0627\u0645\u0631\u0648\u0632 \u067e\u0631 \u0634\u062f\u0647.", "Today's training cap is reached."),
    "energy": ("\u0627\u0646\u0631\u0698\u06cc \u06a9\u0627\u0641\u06cc \u0646\u06cc\u0633\u062a.", "Not enough energy."),
    "maxed": ("\u0645\u0647\u0627\u0631\u062a \u0628\u0647 \u062d\u062f\u0627\u06a9\u062b\u0631 \u0631\u0633\u06cc\u062f\u0647.", "Mastery is maxed."),
    "trained": ("\U0001f3cb\ufe0f +{g} \u0645\u0647\u0627\u0631\u062a!", "\U0001f3cb\ufe0f +{g} Mastery!"),
    "noreg": ("\u0627\u0628\u062a\u062f\u0627 \u062b\u0628\u062a\u200c\u0646\u0627\u0645 \u06a9\u0646.", "Register first."),
}


CHANTS = {  # blade_id -> (fa, en)
    "zangetsu": ("بپوس، زانگتسو!", "Cleave, Zangetsu!"), "senbonzakura": ("پراکنده شو، سنبون‌زاکورا!", "Scatter, Senbonzakura!"),
    "hyorinmaru": ("بر آسمان یخ‌زده فرمان بران، هیورین‌مارو!", "Reign over the frozen heavens, Hyōrinmaru!"),
    "kyoka_suigetsu": ("بشکن، کیوکا سویگتسو!", "Shatter, Kyōka Suigetsu!"), "zanka_no_tachi": ("بسوزان، زانکا نو تاچی!", "Reduce all creation to ash, Zanka no Tachi!"),
    "sode_no_shirayuki": ("برقص، سوده نو شیرایوکی!", "Dance, Sode no Shirayuki!"), "zabimaru": ("غرش کن، زابیمارو!", "Howl, Zabimaru!"),
    "wabisuke": ("بسنج، وابیسوکه!", "Weigh them, Wabisuke!"),
}
GENERIC = {"shinigami": ("بیدار شو، {b}!", "Awaken, {b}!"), "quincy": ("تیر را رها کن، {b}!", "Loose the arrow, {b}!"),
           "hollow": ("بدر، {b}!", "Tear free, {b}!"), "arrancar": ("بدر، {b}!", "Tear free, {b}!"),
           "visored": ("ماسک را بزن، {b}!", "Mask on, {b}!")}
PRESSURE = [(50, "خفته", "Dormant"), (150, "بیدار", "Awakened"), (400, "غران", "Roaring"), (800, "سنگین", "Overwhelming"), (10**9, "فرمانروا", "Sovereign")]


def _chant(ch, z, lang, stage="shikai"):
    from data_zanpakuto import bankai_scene, release_call
    if stage == "bankai" and z.get("blade_id") in BLADE_STAGES:  # Nov 27: every Bankai has its shout and epic line
        return bankai_scene(z["blade_id"], lang)
    canon = release_call(z.get("blade_id"), lang, stage)
    if canon:
        return canon
    c = CHANTS.get(z.get("blade_id"))
    if c:
        return c[0 if lang == "fa" else 1]
    # the blade's own display name (blade ids are not items, so iname() used to print the raw id)
    b = stage_name(z.get("blade_id"), "shikai", lang) or iname(z.get("blade_id") or "", lang) or ""
    g = GENERIC.get(ch.get("race"), ("آزاد شو، {b}!", "Break free, {b}!"))
    return g[0 if lang == "fa" else 1].format(b=b)


def _pressure(mastery, lang):
    for lim, fa, en in PRESSURE:
        if mastery < lim:
            return ("🌀 فشار روحی: " + fa) if lang == "fa" else ("🌀 Reiatsu pressure: " + en)


def _t(lang, key, **kw):
    fa, en = T[key]
    s = fa if lang == "fa" else en
    return s.format(**kw) if kw else s


async def _state(uid):
    ch = await get_char(uid)
    if not ch:
        return None, None
    wid = ch.get("weapon_id") or ""
    z = dict(ch.get("zanpakuto") or {})
    # The blade is chosen from the catalogue (zanpakuto.blade_id), never from the weapon in hand.
    # Anything else, including the old weapon ids saved by the previous version, is dropped here.
    from znp_lock import blade_allowed
    if z.get("blade_id") and not await blade_allowed(uid, z["blade_id"]):  # owner-only blade: hidden from others
        z.pop("blade_id", None)
    if z.get("blade_id") and not blade_valid(z["blade_id"], ch["level"], z.get("owned")):  # also drops a paid blade nobody bought
        z.pop("blade_id", None)
        await col("characters").update_one({"user_id": uid}, {"$unset": {"zanpakuto.blade_id": ""}})
    # Bond is per blade (data_zanpakuto.bond_key): taking the weapon out does not touch it.
    from data_zanpakuto import bond_value
    z["bond"] = bond_value(ch)
    z["mastery"] = int(z.get("mastery", 0))
    return ch, z


@action("znp")
async def zanpakuto_panel(ctx, arg):
    ch, z = await _state(ctx.uid)
    if ch and ch.get("race") not in ("shinigami", "visored"):  # zanpakutō is a Shinigami / Visored path
        return Out("این بخش فقط برای شینیگامی و ویزورد است." if ctx.lang == "fa" else "This path is for Shinigami and Visored only.")
    if not ch:
        return Out(ctx.t("not_registered"))
    gs = await game_settings()
    f1, f2 = (FORMS.get(ch["race"]) or FORMS["human"])
    f1, f2 = f1[0 if ctx.lang == "fa" else 1], f2[0 if ctx.lang == "fa" else 1]
    lv, bond = int(ch["level"]), z["bond"]
    n1 = (int(gs["znp_shikai_level"]), int(gs["znp_shikai_bond"]))
    n2 = (int(gs["znp_bankai_level"]), int(gs["znp_bankai_mastery"]))
    s1 = _t(ctx.lang, "on") if z.get("shikai") else _t(ctx.lang, "off", need=_t(ctx.lang, "need_s", lv=n1[0], bond=n1[1]))
    s2 = _t(ctx.lang, "on") if z.get("bankai") else _t(ctx.lang, "off", need=_t(ctx.lang, "need_b", lv=n2[0], m=n2[1]))
    left = max(0, int(gs["znp_train_daily"]) - await counter_get(f"znp:train:{ctx.uid}:{day_id()}"))
    body = _t(ctx.lang, "body", blade=_blade_label(z, ctx.lang), bond=fnum(bond, ctx.lang),
              mastery=fnum(z["mastery"], ctx.lang), cap=fnum(int(gs["znp_mastery_cap"]), ctx.lang), f1=f1, s1=s1, f2=f2, s2=s2,
              left=left, daily=int(gs["znp_train_daily"]), gain=int(gs["znp_train_gain"]), cost=int(gs["znp_train_energy"]))
    body += "\n" + _pressure(z["mastery"], ctx.lang)
    rows = [[(_t(ctx.lang, "b_train"), "ztrn", "")]]
    rows.append([("📖 توانایی‌های تیغه" if ctx.lang == "fa" else "📖 Blade abilities", "znpa", "")])  # Nov 27: the blade's technique, finisher and Bankai
    if reachable_blades(ch["level"]):  # the blade is chosen here, not by the weapon in hand
        rows.append([("🗡 تغییر تیغه" if ctx.lang == "fa" else "🗡 Choose blade", "znpb", "")])
    if not z.get("shikai") and lv >= n1[0] and bond >= n1[1]:
        rows.append([(_t(ctx.lang, "b_rel1", f=f1), "zrel", "1")])
    if z.get("shikai") and not z.get("bankai") and lv >= n2[0] and z["mastery"] >= n2[1]:
        rows.append([(_t(ctx.lang, "b_rel2", f=f2), "zrel", "2")])
    rows.append(nav(ctx))
    return Out(f"\u2694\ufe0f <b>\U0001d5b2\U0001d5a4\U0001d5ad\U0001d5aa\U0001d5a0</b> | <b>{_t(ctx.lang, 'title')}</b>\n{SEP}\n" + body, rows)


def _blade_label(z, lang):
    bid = z.get("blade_id")
    if bid not in BLADE_STAGES:
        return "-"
    return BLADE_STAGES[bid]["shikai"][0 if lang == "fa" else 1]


@action("znpb")
async def blade_choose(ctx, arg):
    ch, z = await _state(ctx.uid)
    if not ch:
        return Out(ctx.t("not_registered"), [nav(ctx)])
    from znp_lock import blade_allowed
    owned = z.get("owned") or []
    picks = [b for b in unlocked_blades(ch["level"], owned) if await blade_allowed(ctx.uid, b)]
    rows = [[(f"{tier_label(b, ctx.lang)} · {BLADE_STAGES[b]['shikai'][0 if ctx.lang == 'fa' else 1]}"
              + (" 🧪" if b in BETA_BLADES else ""), "znpc", b)] for b in picks]
    # paid blades this level has reached but the player has not bought yet: a price button
    for b in reachable_blades(ch["level"]):
        if b in PAID_BLADES and b not in owned and await blade_allowed(ctx.uid, b):
            rows.append([(f"💰 {tier_label(b, ctx.lang)} · {BLADE_STAGES[b]['shikai'][0 if ctx.lang == 'fa' else 1]} — "
                          f"{fnum(blade_price(b), ctx.lang)}", "znpbuy", b)])
    rows.append(nav(ctx, ("znp", "")))
    text = ("🗡 تیغه‌ای که می‌خوای بگیری را انتخاب کن. هر تیغه با رسیدن به لول خودش باز میشه.\n🧪 = بتا: برای همه بازه تا تست بشه؛ مشکلش را به ادمین بگو. بعد از فیکس ممکنه قفل بشه.\n💰 = تیغه‌ی پولی: یک‌بار با سکه می‌خری و برای همیشه مال توئه." if ctx.lang == "fa"
            else "🗡 Pick the blade you want to bind. Each blade opens at its own level.\n🧪 = beta: open to everyone while it is tested; report problems to the admin. It may be locked once fixed.\n💰 = paid blade: buy it once with coins and it is yours for good.")
    return Out(text, rows)


@action("znpbuy")
async def blade_buy(ctx, arg):
    """Buy a paid blade. First tap shows the price, the second tap (arg 'ok:<blade>') pays."""
    confirm = arg.startswith("ok:")
    bid = arg[3:] if confirm else arg
    ch, z = await _state(ctx.uid)
    if not ch:
        return Out(ctx.t("not_registered"), [nav(ctx)])
    if ch.get("race") not in ("shinigami", "visored") or bid not in PAID_BLADES or bid not in reachable_blades(ch["level"]):
        return Out(alert=("این تیغه هنوز باز نشده." if ctx.lang == "fa" else "That blade is still locked."))
    from znp_lock import blade_allowed
    if not await blade_allowed(ctx.uid, bid):
        return Out(alert=("این تیغه فقط برای مالک بازی است." if ctx.lang == "fa" else "This blade is reserved for the owner."))
    if bid in (z.get("owned") or []):
        return Out(alert=("این تیغه را قبلاً خریده‌ای." if ctx.lang == "fa" else "You already own this blade."))
    price = blade_price(bid)
    name = BLADE_STAGES[bid]["shikai"][0 if ctx.lang == "fa" else 1]
    if not confirm:
        text = (f"💰 خرید تیغه <b>{name}</b> ({tier_label(bid, 'fa')})\nقیمت: <b>{fnum(price, 'fa')}</b> سکه — یک‌بار خرید، برای همیشه.\nسکه‌ی تو: {fnum(ch.get('coins', 0), 'fa')}" if ctx.lang == "fa"
                else f"💰 Buy the blade <b>{name}</b> ({tier_label(bid, 'en')})\nPrice: <b>{fnum(price)}</b> coins, one time, yours for good.\nYour coins: {fnum(ch.get('coins', 0))}")
        return Out(text, [[("✅ تأیید خرید" if ctx.lang == "fa" else "✅ Confirm", "znpbuy", f"ok:{bid}")],
                          nav(ctx, ("znpb", ""))])
    if await try_cooldown(f"znp:buy:cd:{ctx.uid}", 3):  # double tap
        return Out(alert=_t(ctx.lang, "wait"))
    if not await add_coins(ctx.uid, -price, f"blade_{bid}"):  # atomic: takes the coins only if the balance covers them
        return Out(alert=("سکه‌ی کافی نداری." if ctx.lang == "fa" else "Not enough coins."))
    r = await col("characters").update_one({"user_id": ctx.uid, "zanpakuto.owned": {"$ne": bid}},
                                           {"$addToSet": {"zanpakuto.owned": bid}})
    if not r.modified_count:  # bought in parallel: give the coins back
        await add_coins(ctx.uid, price, f"blade_{bid}_refund")
        return Out(alert=("این تیغه را قبلاً خریده‌ای." if ctx.lang == "fa" else "You already own this blade."))
    out = await blade_choose(ctx, "")
    out.text = (f"✅ تیغه‌ی <b>{name}</b> مال تو شد!\n" if ctx.lang == "fa" else f"✅ <b>{name}</b> is yours!\n") + out.text
    return out


@action("znpc")
async def blade_set(ctx, arg):
    ch, z = await _state(ctx.uid)
    if not ch:
        return Out(ctx.t("not_registered"), [nav(ctx)])
    if not blade_valid(arg, ch["level"], z.get("owned")):
        return Out(alert=("این تیغه هنوز باز نشده." if ctx.lang == "fa" else "That blade is still locked."))
    from znp_lock import blade_allowed
    if not await blade_allowed(ctx.uid, arg):
        return Out(alert=("این تیغه فقط برای مالک بازی است." if ctx.lang == "fa" else "This blade is reserved for the owner."))
    await col("characters").update_one({"user_id": ctx.uid}, {"$set": {"zanpakuto.blade_id": arg}})
    return await zanpakuto_panel(ctx, "")


@action("ztrn")
async def zanpakuto_train(ctx, arg):
    ch, z = await _state(ctx.uid)
    if ch and ch.get("race") not in ("shinigami", "visored"):  # zanpakutō is a Shinigami / Visored path
        return Out("این بخش فقط برای شینیگامی و ویزورد است." if ctx.lang == "fa" else "This path is for Shinigami and Visored only.")
    if not ch:
        return Out(alert=_t(ctx.lang, "noreg"))
    gs = await game_settings()
    cap = int(gs["znp_mastery_cap"])
    if z["mastery"] >= cap:
        return Out(alert=_t(ctx.lang, "maxed"))
    if await try_cooldown(f"znp:train:cd:{ctx.uid}", 3):
        return Out(alert=_t(ctx.lang, "wait"))
    daily = int(gs["znp_train_daily"])
    if await counter_get(f"znp:train:{ctx.uid}:{day_id()}") >= daily:
        return Out(alert=_t(ctx.lang, "cap"))
    ok, _cur, _nxt = await spend_energy(ctx.uid, int(gs["znp_train_energy"]))
    if not ok:
        return Out(alert=_t(ctx.lang, "energy"))
    if not await bump_counter(f"znp:train:{ctx.uid}:{day_id()}", 1, daily):
        from service_extras import add_energy
        await add_energy(ctx.uid, int(gs["znp_train_energy"]))
        return Out(alert=_t(ctx.lang, "cap"))
    gain = int(gs["znp_train_gain"])
    await col("characters").update_one({"user_id": ctx.uid, "zanpakuto.mastery": {"$lt": cap}},
                                       {"$inc": {"zanpakuto.mastery": gain}})
    out = await zanpakuto_panel(ctx, "")
    out.text = _t(ctx.lang, "trained", g=gain) + "\n" + out.text
    return out


@action("zrel")
async def zanpakuto_release(ctx, arg):
    ch, z = await _state(ctx.uid)
    if ch and ch.get("race") not in ("shinigami", "visored"):  # zanpakutō is a Shinigami / Visored path
        return Out("این بخش فقط برای شینیگامی و ویزورد است." if ctx.lang == "fa" else "This path is for Shinigami and Visored only.")
    if not ch:
        return Out(alert=_t(ctx.lang, "noreg"))
    gs = await game_settings()
    lv, f = int(ch["level"]), (FORMS.get(ch["race"]) or FORMS["human"])
    if arg == "1":
        if z.get("shikai") or lv < int(gs["znp_shikai_level"]) or z["bond"] < int(gs["znp_shikai_bond"]):
            return Out(alert=_t(ctx.lang, "locked"))
        r = await col("characters").update_one({"user_id": ctx.uid, "zanpakuto.shikai": {"$ne": True}},
                                               {"$set": {"zanpakuto.shikai": True, "zanpakuto.shikai_at": int(time.time())}})
        key, name = "done1", f[0]
    elif arg == "2":
        if (not z.get("shikai")) or z.get("bankai") or lv < int(gs["znp_bankai_level"]) or z["mastery"] < int(gs["znp_bankai_mastery"]):
            return Out(alert=_t(ctx.lang, "locked"))
        r = await col("characters").update_one({"user_id": ctx.uid, "zanpakuto.shikai": True, "zanpakuto.bankai": {"$ne": True}},
                                               {"$set": {"zanpakuto.bankai": True, "zanpakuto.bankai_at": int(time.time())}})
        key, name = "done2", f[1]
    else:
        return Out(alert=_t(ctx.lang, "locked"))
    if not r.modified_count:  # double tap
        return await zanpakuto_panel(ctx, "")
    stage = "shikai" if arg == "1" else "bankai"
    await butterfly(ctx.bot, ctx.uid, ctx.lang, stage,
                    blade=stage_name(z.get("blade_id"), stage, ctx.lang) or iname(z.get("blade_id") or "", ctx.lang) or "—")
    out = await zanpakuto_panel(ctx, "")
    out.text = "🗡 <i>" + _chant(ch, z, ctx.lang, stage) + "</i>\n" + _t(ctx.lang, key, f=name[0 if ctx.lang == "fa" else 1]) + "\n" + out.text
    return out


def _pct(v):
    return f"{round(float(v) * 100)}%"


def _tier_str(b, lang):
    return tier_label(b, lang)


@action("znpa")
async def blade_abilities(ctx, arg):
    """Nov 27: the abilities panel of a blade: technique, finisher, Bankai finisher, bonuses and how to use them in a fight.
    arg = blade id (default: the chosen blade). Buttons let the player look at any blade they can reach."""
    from data_zanpakuto import BLADE_STYLE, BLADE_TECH_COST, bankai_shout, blade_b2, blade_extra, blade_technique, blade_ultimate
    ch, z = await _state(ctx.uid)
    if not ch:
        return Out(ctx.t("not_registered"), [nav(ctx)])
    fa = ctx.lang == "fa"
    reach = reachable_blades(ch["level"])
    bid = arg if arg in BLADE_STAGES else z.get("blade_id")
    if bid not in BLADE_STAGES:
        text = ("📖 هنوز تیغه‌ای انتخاب نکرده‌ای. یکی را از لیست انتخاب کن تا توانایی‌هایش را ببینی." if fa
                else "📖 You have not chosen a blade yet. Pick one below to see its abilities.")
        rows = [[(f"{_tier_str(b, ctx.lang)} · {BLADE_STAGES[b]['shikai'][0 if fa else 1]}", "znpa", b)] for b in reach]
        rows.append(nav(ctx, ("znp", "")))
        return Out(text, rows)
    i = 0 if fa else 1
    st = BLADE_STAGES[bid]
    name = st["shikai"][i]
    bk_name = (st.get("bankai") or st["shikai"])[i]
    lines = [f"📖 <b>{name}</b> · {_tier_str(bid, ctx.lang)}", SEP]
    sty = BLADE_STYLE.get(bid, {})
    bonus = []
    if sty.get("dmg"): bonus.append((f"آسیب ×{sty['dmg']}" if fa else f"damage x{sty['dmg']}"))
    if sty.get("def"): bonus.append((f"دفاع ×{sty['def']}" if fa else f"defence x{sty['def']}"))
    if sty.get("kido"): bonus.append((f"کیدو ×{sty['kido']}" if fa else f"kidō x{sty['kido']}"))
    if sty.get("crit"): bonus.append((f"+{_pct(sty['crit'])} کریت" if fa else f"+{_pct(sty['crit'])} crit"))
    lines.append(("🔧 سبک: " if fa else "🔧 Style: ") + (" · ".join(bonus) if bonus else "—"))
    lines.append((f"🔥 شیکای: +{_pct(0.10 + st.get('shikai_bonus', 0))} · 💥 بانکای: +{_pct(0.12 + st.get('bankai_bonus', 0))} (+ مهارت)" if fa
                  else f"🔥 Shikai: +{_pct(0.10 + st.get('shikai_bonus', 0))} · 💥 Bankai: +{_pct(0.12 + st.get('bankai_bonus', 0))} (+ Mastery)"))
    lines.append("")
    if bid == "kyoka_suigetsu":
        lines.append("🌫️ کیوکا سویگتسو کیت مخصوص خودش را دارد: ۴ توانایی توهمی، و بعد از شیکای ۵ توانایی (از جمله «کانزن سایمین»)." if fa
                     else "🌫️ Kyōka Suigetsu has its own kit: 4 illusion abilities, and 5 after Shikai (including Kanzen Saimin).")
    else:
        t = blade_technique(bid)
        if t:
            cost = t.get("cost", BLADE_TECH_COST["cost"])
            extra = []
            if t.get("pierce"): extra.append((f"{_pct(t['pierce'])} نفوذ" if fa else f"{_pct(t['pierce'])} pierce"))
            if t.get("bleed"): extra.append("خون‌ریزی" if fa else "bleed")
            if t.get("twice"): extra.append("دو ضربه" if fa else "two cuts")
            if t.get("bk_mult"): extra.append((f"در بانکای ×{t['bk_mult']}" if fa else f"x{t['bk_mult']} in Bankai"))
            lines.append(f"🗡 <b>{t['fa' if fa else 'en']}</b> — " + ((f"ضرب ×{t['mult']}" if fa else f"power x{t['mult']}")
                         + ((" · " + " · ".join(extra)) if extra else "")
                         + (f" · هزینه {_pct(cost)} ریاتسو · کول‌داون {t['cd']}" if fa else f" · cost {_pct(cost)} reiatsu · cooldown {t['cd']}")))
            if t.get("bk"):  # Nov 27: what the technique becomes in Bankai
                tb = {**t, **t["bk"]}
                ex = []
                if tb.get("pierce"): ex.append((f"{_pct(tb['pierce'])} نفوذ" if fa else f"{_pct(tb['pierce'])} pierce"))
                fxn = {"burn": ("سوختگی", "burn"), "bleed": ("خون‌ریزی", "bleed"), "weaken": ("تضعیف", "weaken"), "skip": ("یخ‌زدگی", "freeze")}
                for k_ in ([tb["fx"]] if isinstance(tb.get("fx"), str) else list(tb.get("fx") or [])):
                    ex.append(fxn.get(k_, (k_, k_))[i])
                lines.append(f"   💥 {'در بانکای' if fa else 'In Bankai'}: <b>{tb['fa' if fa else 'en']}</b> — "
                             + (f"ضرب ×{tb['mult']}" if fa else f"power x{tb['mult']}") + ((" · " + " · ".join(ex)) if ex else ""))
        b2 = blade_b2(bid)
        if b2:  # the second simple ability and its Bankai form
            def _b2(x):
                ex = []
                if x.get("mult"): ex.append((f"ضرب ×{x['mult']}" if fa else f"power x{x['mult']}"))
                if x.get("shield"): ex.append((f"سپر {_pct(x['shield'])}" if fa else f"{_pct(x['shield'])} barrier"))
                if x.get("heal"): ex.append((f"ترمیم {_pct(x['heal'])}" if fa else f"{_pct(x['heal'])} heal"))
                if x.get("buff"): ex.append((f"آسیب ×{x['buff'][1]} برای {x['buff'][0]} نوبت" if fa else f"damage x{x['buff'][1]} for {x['buff'][0]} turns"))
                fxn = {"burn": ("سوختگی", "burn"), "bleed": ("خون‌ریزی", "bleed"), "weaken": ("تضعیف", "weaken"), "skip": ("یخ‌زدگی", "freeze")}
                for k_ in ([x["fx"]] if isinstance(x.get("fx"), str) else list(x.get("fx") or [])):
                    ex.append(fxn.get(k_, (k_, k_))[i] + (f" {_pct(x['skip_p'])}" if k_ == "skip" and x.get("skip_p") else ""))
                return " · ".join(ex)
            lines.append(f"🔰 <b>{b2['fa' if fa else 'en']}</b> — {_b2(b2)} · " + (f"هزینه {_pct(b2['cost'])} ریاتسو · کول‌داون {b2['cd']}" if fa else f"cost {_pct(b2['cost'])} reiatsu · cooldown {b2['cd']}"))
            bb = {**b2, **b2["bk"]}
            lines.append(f"   💥 {'در بانکای' if fa else 'In Bankai'}: <b>{bb['fa' if fa else 'en']}</b> — {_b2(bb)}")
        for _slot, _ic in (("b3", "🔥"), ("b4", "🛠"), ("b5", "☀️")):  # Nov 27 round 4: Yamamoto's / Urahara's 3rd and 4th simple abilities
            ex_ = blade_extra(bid, _slot)
            if ex_:
                lines.append(f"{_ic} <b>{ex_['fa' if fa else 'en']}</b> — {_b2(ex_)} · " + (f"هزینه {_pct(ex_['cost'])} ریاتسو · کول‌داون {ex_['cd']}" if fa else f"cost {_pct(ex_['cost'])} reiatsu · cooldown {ex_['cd']}"))
                bb_ = {**ex_, **ex_["bk"]}
                lines.append(f"   💥 {'در بانکای' if fa else 'In Bankai'}: <b>{bb_['fa' if fa else 'en']}</b> — {_b2(bb_)}")
        u = blade_ultimate(bid)
        if u:
            def _ult(x):
                ex = []
                if x.get("pierce"): ex.append((f"{_pct(x['pierce'])} نفوذ" if fa else f"{_pct(x['pierce'])} pierce"))
                fx = {"burn": ("سوختگی", "burn"), "bleed": ("خون‌ریزی", "bleed"), "weaken": ("تضعیف", "weaken"), "skip": ("یخ‌زدگی/از دست دادن نوبت", "freeze / lost turn")}.get(x.get("fx"))
                if fx: ex.append(fx[i])
                if x.get("shield"): ex.append((f"سپر {_pct(x['shield'])}" if fa else f"{_pct(x['shield'])} barrier"))
                if x.get("heal"): ex.append((f"ترمیم {_pct(x['heal'])}" if fa else f"{_pct(x['heal'])} heal"))
                if x.get("cleanse"): ex.append("پاک‌سازی زخم‌ها" if fa else "cleanses wounds")
                hits = f" × {x['hits']}" if int(x.get("hits", 1)) > 1 else ""
                return ((f"ضرب ×{x['mult']}{hits}" if fa else f"power x{x['mult']}{hits}") + ((" · " + " · ".join(ex)) if ex else "")
                        + (f" · هزینه {_pct(x['cost'])} ریاتسو · کول‌داون {x['cd']}" if fa else f" · cost {_pct(x['cost'])} reiatsu · cooldown {x['cd']}"))
            lines.append(f"👑 <b>{u['fa' if fa else 'en']}</b> — " + _ult(u))
            if u.get("bk"):
                bk = {**u, **u["bk"]}
                lines.append(f"💥 {'در بانکای' if fa else 'In Bankai'}: <b>{bk['fa' if fa else 'en']}</b> — " + _ult(bk) + (" (+۳۵٪ آسیب بانکای)" if fa else " (+35% Bankai damage)"))
            else:
                lines.append("💥 " + ("در بانکای ضربه‌ی نهایی ۳۵٪ قوی‌تر می‌خورد." if fa else "In Bankai the finisher hits 35% harder."))
    lines.append("")
    lines.append(f"🗣 {'ورد بانکای' if fa else 'Bankai call'}: «{bankai_shout(bid, ctx.lang)}»")
    lines.append("")
    lines.append(("ℹ️ در نبرد اول دکمه‌ی 🗡 شیکای را بزن؛ بعد دکمه‌ی تکنیک و ضربه‌ی نهایی ظاهر می‌شوند. بانکای با پر شدن روحیه‌ی جنگ فعال می‌شود (دکمه‌ی 👑 یا تایپ «بانکای»)." if fa
                  else "ℹ️ In a fight press 🗡 Shikai first; the technique and finisher buttons then appear. Bankai opens when the spirit gauge is full (the 👑 button or type «Bankai»)."))
    rows = []
    if bid != z.get("blade_id") and blade_valid(bid, ch["level"], z.get("owned")):
        rows.append([("✅ انتخاب این تیغه" if fa else "✅ Choose this blade", "znpc", bid)])
    others = [b for b in reach if b != bid]
    pair = []
    for b in others:
        pair.append((BLADE_STAGES[b]["shikai"][i][:20], "znpa", b))
        if len(pair) == 2:
            rows.append(pair); pair = []
    if pair:
        rows.append(pair)
    rows.append(nav(ctx, ("znp", "")))
    return Out("\n".join(lines), rows)
