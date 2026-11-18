"""Race weapon panel: the mandatory first choice, the weapon card, colour ascension and the Rebirth Seal type switch.

Codes: rwp (panel), rwc:<n> (look at weapon n before choosing), rwk:<n> (choose it), rwa (ascend one colour),
rws (switch list, needs a Rebirth Seal), rwsk:<n> (switch to n).
"""
from data_items import ALL, iname
from data_raceweapons import RACE_STYLE, RACE_WEAPONS, rw_id
from data_weapons import RARITIES, RARITY_ICON
from fmt import item_card, nm, rarity_name
from i18n import fnum
from service_economy import inv_get
from service_player import get_char
from service_raceweapon import REBIRTH_SEAL, ascend, ascend_need, choose, needs_choice, offer_level, switch_type
from ui import Out, action, head, nav

ERR = {
    "bad": ("این سلاح وجود ندارد.", "That weapon does not exist."),
    "has": ("سلاحت را قبلاً انتخاب کرده‌ای.", "You already chose your weapon."),
    "retry": ("دوباره امتحان کن.", "Please try again."),
    "noreg": ("اول ثبت‌نام کن.", "Register first."),
    "choose": ("اول سلاح نژادت را انتخاب کن.", "Choose your race weapon first."),
    "max": ("سلاحت به رنگ قرمز (اوج) رسیده است.", "Your weapon is already red (the peak)."),
    "level": ("برای این رنگ باید به سطح {n} برسی.", "You need level {n} for this colour."),
    "items": ("یادگار تکامل کافی نداری ({n} عدد لازم است).", "Not enough evolution relics ({n} needed)."),
    "funds": ("سکه‌ی کافی نداری ({n} 🪙).", "Not enough coins ({n} 🪙)."),
    "seal": ("برای عوض کردن نوع سلاح، «مهر بازآفرینی سلاح» لازم داری.", "You need a Weapon Rebirth Seal to switch type."),
}


def _e(ctx, code, n=0):
    fa, en = ERR.get(code, ("مشکلی پیش آمد.", "Something went wrong."))
    return (fa if ctx.lang == "fa" else en).format(n=fnum(n, ctx.lang))


def T(ctx, fa, en):
    return fa if ctx.lang == "fa" else en


def _level_line(ctx, lvl):
    L = ctx.lang
    rar = RARITIES[lvl["c"]]
    return T(ctx, f"سطح پیشنهادی: {RARITY_ICON[rar]} {rarity_name(rar, L)} · فورج +{fnum(lvl['plus'], L)} · پیوند {fnum(lvl['bond'], L)}",
             f"Offered level: {RARITY_ICON[rar]} {rarity_name(rar, L)} · forge +{lvl['plus']} · bond {lvl['bond']}")


async def choice_panel(ctx, ch=None):
    """The mandatory choice: ten raw weapons of the player's race, offered at the old blade's level."""
    ch = ch or await get_char(ctx.uid)
    L = ctx.lang
    race = ch["race"]
    lvl = offer_level(ch)
    style = RACE_STYLE[race][0 if L == "fa" else 1]
    lines = [T(ctx, "🗡 <b>سلاح نژادت را انتخاب کن</b>", "🗡 <b>Choose your race weapon</b>"),
             T(ctx, f"سبک نژادت: {style}", f"Your race style: {style}"),
             _level_line(ctx, lvl), "",
             T(ctx, "هر سلاح گرایش خودش را دارد. با پیروزی پیوند می‌گیرد، با فورج تا +۱۰ قوی می‌شود و با یادگار تکامل رنگش بالا می‌رود.\n"
                    "⚠️ تا انتخاب نکنی نمی‌توانی وارد نبرد شوی.",
               "Each weapon has its own leaning. It gains bond by winning, grows to +10 at the forge and rises in colour with "
               "evolution relics.\n⚠️ You cannot fight until you choose.")]
    rows = []
    for n, w in enumerate(RACE_WEAPONS[race]):
        atk = fnum(ALL[rw_id(race, n, lvl["c"])]["attack"], L)  # attack at the offered colour
        rows.append([(f"ℹ️ {w['fa' if L == 'fa' else 'en']} · {w['lean'][0 if L == 'fa' else 1]} · ⚔️{atk}", "rwc", str(n))])
    lines.append(ctx.t("reg_weapon_hint"))
    rows.append(nav(ctx))
    return Out(head(ctx, "ttl_rw") + "\n".join(lines), rows)


async def weapon_panel(ctx, ch, note=None):
    L = ctx.lang
    wid = ch["weapon_id"]
    plus = int((ch.get("weapon_plus") or {}).get(wid, 0))
    from data_zanpakuto import bond_value
    mult = str(round(1 + 0.06 * plus, 2))
    mult_fa = mult.replace(".", "٫").translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
    lines = [T(ctx, "🗡 <b>سلاح نژاد تو</b>", "🗡 <b>Your race weapon</b>"),
             item_card(ctx, wid),
             T(ctx, f"🔨 فورج: +{fnum(plus, L)} (×{mult_fa} قدرت) · 🔗 پیوند: {fnum(bond_value(ch), L)}",
               f"🔨 Forge: +{plus} (×{round(1 + 0.06 * plus, 2)} attack) · 🔗 Bond: {bond_value(ch)}")]
    from data_raceweapons import weapon_focus
    from data_items import ALL as _ALL
    foc = weapon_focus(_ALL.get(wid), plus)
    if foc:
        p100 = round(foc[1] * 100 / (2 if foc[0] in ("crit", "pierce") else 1), 1)
        lines.append(T(ctx, f"🎯 تمرکز سلاح: +{fnum(f'{p100:g}', L).replace('.', '٫')}٪ {foc[2]} (با هر رنگ و هر فورج بیشتر)",
                       f"🎯 Weapon focus: +{p100:g}% {foc[3]} (grows with every colour and forge level)"))
    rows = []
    nxt = ascend_need(ch)
    if nxt:
        colour, gate, need, tier, coins = nxt
        rar, req = RARITIES[colour], RARITIES[tier]
        lines.append(T(ctx, f"\n⬆️ رنگ بعدی: {RARITY_ICON[rar]} {rarity_name(rar, L)} · سطح {fnum(gate, L)} · "
                            f"{fnum(need, L)} یادگار تکامل {RARITY_ICON[req]}+ · {fnum(coins, L)} 🪙",
                       f"\n⬆️ Next colour: {RARITY_ICON[rar]} {rarity_name(rar, L)} · level {gate} · "
                       f"{need} evolution relics {RARITY_ICON[req]}+ · {fnum(coins, L)} 🪙"))
        rows.append([(T(ctx, "⬆️ ارتقای رنگ", "⬆️ Raise colour"), "rwa", "")])
    else:
        lines.append(T(ctx, "\n🔴 سلاحت به اوج رنگ رسیده است.", "\n🔴 Your weapon has reached the top colour."))
    rows.append([(T(ctx, "🔨 فورج", "🔨 Forge"), "frg", ""), (T(ctx, "🔄 عوض کردن نوع", "🔄 Switch type"), "rws", "")])
    rows.append(nav(ctx, ("prof", "")))
    text = head(ctx, "ttl_rw") + "\n".join(lines)
    return Out(text, rows, alert=note)


@action("rwp")
async def race_weapon(ctx, arg):
    ch = await get_char(ctx.uid)
    if not ch:
        return Out(_e(ctx, "noreg"), [nav(ctx)])
    if needs_choice(ch):
        return await choice_panel(ctx, ch)
    return await weapon_panel(ctx, ch)


@action("rwc")
async def race_weapon_look(ctx, arg):
    ch = await get_char(ctx.uid)
    if not ch or not needs_choice(ch):
        return await race_weapon(ctx, "")
    n = int(arg) if str(arg).isdigit() else -1
    if not 0 <= n < len(RACE_WEAPONS[ch["race"]]):
        return Out(alert=_e(ctx, "bad"))
    lvl = offer_level(ch)
    iid = rw_id(ch["race"], n, lvl["c"])
    from data_guides import weapon_guide
    text = head(ctx, "ttl_rw") + weapon_guide(iid, ctx.lang) + "\n\n" + _level_line(ctx, lvl)
    rows = [[(T(ctx, "✅ همین را برمی‌دارم", "✅ I take this one"), "rwk", str(n))], [(T(ctx, "↩️ بقیه", "↩️ The others"), "rwp", "")], nav(ctx)]
    return Out(text, rows)


@action("rwk")
async def race_weapon_take(ctx, arg):
    n = int(arg) if str(arg).isdigit() else -1
    status, iid = await choose(ctx.uid, n)
    if status != "ok":
        return Out(alert=_e(ctx, status))
    ch = await get_char(ctx.uid)
    return await weapon_panel(ctx, ch, note=T(ctx, f"🗡 «{iname(iid, 'fa')}» حالا سلاح توست!", f"🗡 «{iname(iid, 'en')}» is now your weapon!"))


@action("rwa")
async def race_weapon_ascend(ctx, arg):
    status, extra = await ascend(ctx.uid)
    ch = await get_char(ctx.uid)
    if status != "ok":
        return Out(alert=_e(ctx, status, extra if isinstance(extra, int) else 0))
    return await weapon_panel(ctx, ch, note=T(ctx, f"⬆️ رنگ سلاحت بالا رفت: {nm(extra, 'fa')}", f"⬆️ Your weapon rose in colour: {nm(extra, 'en')}"))


@action("rws")
async def race_weapon_switch(ctx, arg):
    ch = await get_char(ctx.uid)
    if not ch or needs_choice(ch):
        return await race_weapon(ctx, "")
    inv = await inv_get(ctx.uid)
    seals = int((inv.get("items") or {}).get(REBIRTH_SEAL, 0))
    L = ctx.lang
    lines = [T(ctx, "🔄 <b>عوض کردن نوع سلاح</b>", "🔄 <b>Switch weapon type</b>"),
             T(ctx, f"رنگ، فورج و پیوند سلاحت حفظ می‌شود. یک «{iname(REBIRTH_SEAL, 'fa')}» مصرف می‌شود (داری: {fnum(seals, L)}).",
               f"Colour, forge level and bond are kept. One «{iname(REBIRTH_SEAL, 'en')}» is used (you have {seals}).")]
    rows = []
    cur = ALL[ch["weapon_id"]]["rw_n"]
    if seals:
        for n, w in enumerate(RACE_WEAPONS[ch["race"]]):
            if n != cur:
                rows.append([(f"ℹ️ {w['fa' if L == 'fa' else 'en']} · {w['lean'][0 if L == 'fa' else 1]}", "rwsi", str(n))])
    rows.append(nav(ctx, ("rwp", "")))
    return Out(head(ctx, "ttl_rw") + "\n".join(lines), rows)


@action("rwsi")
async def race_weapon_switch_info(ctx, arg):
    """The guide of the weapon to switch to, at the colour of the weapon in hand."""
    from data_guides import weapon_guide
    ch = await get_char(ctx.uid)
    if not ch or needs_choice(ch) or not str(arg).isdigit() or not 0 <= int(arg) < len(RACE_WEAPONS[ch["race"]]):
        return await race_weapon(ctx, "")
    iid = rw_id(ch["race"], int(arg), ALL[ch["weapon_id"]]["rw_c"])
    rows = [[(T(ctx, "🔄 به این سلاح عوض کن", "🔄 Switch to this weapon"), "rwsk", arg)], [(T(ctx, "↩️ بقیه", "↩️ The others"), "rws", "")]]
    return Out(head(ctx, "ttl_rw") + weapon_guide(iid, ctx.lang), rows)


@action("rwsk")
async def race_weapon_switch_do(ctx, arg):
    n = int(arg) if str(arg).isdigit() else -1
    status, iid = await switch_type(ctx.uid, n)
    if status != "ok":
        return Out(alert=_e(ctx, status))
    ch = await get_char(ctx.uid)
    return await weapon_panel(ctx, ch, note=T(ctx, f"🔄 سلاحت حالا «{iname(iid, 'fa')}» است.", f"🔄 Your weapon is now «{iname(iid, 'en')}»."))
