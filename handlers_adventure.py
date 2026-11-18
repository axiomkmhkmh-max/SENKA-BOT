"""Panels for the Nov 19 batch: 🧭 adventures, 👹 level boss, 🎰 roll shop, 🏛 elite shop, 🌌 Inner World 2 and the
companion upgrade button (services in service_adventure, numbers in data_extras2)."""
from data_extras2 import (ADV_FINISH_COINS, ADVENTURES, ELITE_MIN_LEVEL, INNER2, INNER_KEY, LEVEL_BOSSES, PET_MAX_TIER,
                          ROLL_COST, ROLL_JACKPOT_EVERY, ROLL_TEN_COST, ROLL_WEIGHTS)
from data_items import ALL, iname
from i18n import fnum
from service_adventure import (adventure_info, adventure_start, elite_buy, elite_price, elite_stock, inner2_use,
                               level_boss_info, level_boss_start, pet_up_cost, pet_upgrade, roll, today_key)
from service_economy import inv_get
from fmt import rarity_name
from service_player import get_char
from ui import Out, action, head, nav

_RARS = ["Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythic"]


def _T(ctx, fa, en):
    return fa if ctx.lang == "fa" else en


async def _to_battle(ctx, doc):
    from handlers_combat import battle_panel
    return await battle_panel(ctx, doc)


# ---- adventures -----------------------------------------------------------------------------------------------------------
@action("avl")
async def adventure_list(ctx, arg):
    L = ctx.lang
    ch = await get_char(ctx.uid)
    info = await adventure_info(ctx.uid)
    lines = [_T(ctx, "🧭 <b>ماجراجویی</b>\nسفرهای چندمرحله‌ای با دشمن‌های هم‌سطح تو (کمی ضعیف‌تر یا قوی‌تر). سکه‌محور: هر مرحله سکه‌ی بیشتر از نبرد عادی و آخرش یک کیسه‌ی سکه. رنک و دانجن پوینت ندارد.",
                "🧭 <b>Adventures</b>\nMulti-stage journeys against foes around your level. Coin-focused: each stage pays more coins than a normal fight and the end pays a coin purse. No rank or dungeon points."),
             _T(ctx, f"🎟 امروز: {fnum(info['left'], L)}/{fnum(info['cap'], L)}", f"🎟 Today: {info['left']}/{info['cap']}"), ""]
    rows = []
    for aid, a in ADVENTURES.items():
        ok = int(ch["level"]) >= a["level"]
        lines.append(("✅ " if ok else "🔒 ") + f"{a['fa' if L == 'fa' else 'en']} · {fnum(a['stages'], L)} " + _T(ctx, "مرحله", "stages")
                     + ("" if ok else f" · Lv.{fnum(a['level'], L)}"))
        if ok:
            rows.append([(f"🧭 {a['fa' if L == 'fa' else 'en']}", "avs", aid)])
    lines.append("")
    lines.append(_T(ctx, f"🪙 کیسه‌ی پایان: {fnum(ADV_FINISH_COINS, L)} × (۱ + لول ÷ ۱۰)", f"🪙 Finish purse: {ADV_FINISH_COINS} × (1 + level ÷ 10)"))
    rows.append(nav(ctx))
    return Out(head(ctx, "m_avl") + "\n".join(lines), rows)


@action("avs")
async def adventure_go(ctx, arg):
    status, doc = await adventure_start(ctx.uid, arg, ctx.lang)
    if status == "ok":
        return await _to_battle(ctx, doc)
    msg = {"level": _T(ctx, "لِوِلت برای این ماجراجویی کم است.", "Your level is too low for this one."),
           "busy": _T(ctx, "اول نبرد فعلی‌ات را تمام کن.", "Finish your current fight first."),
           "limit": _T(ctx, "ماجراجویی‌های امروزت تمام شد.", "No adventures left today."),
           "wait": "⏳"}.get(status, _T(ctx, "انتخاب نامعتبر.", "Invalid choice."))
    return Out(alert=msg)


# ---- level boss ---------------------------------------------------------------------------------------------------------
@action("lbs")
async def level_boss_panel(ctx, arg):
    L = ctx.lang
    info = await level_boss_info(ctx.uid)
    lo, hi, b_fa, b_en, colour, _race = info["boss"]
    band_txt = f"{fnum(lo, L)}–{fnum(hi, L)}" if hi < 9999 else f"{fnum(lo, L)}+"
    lines = [_T(ctx, "👹 <b>باس سطح</b>\nهر بازه‌ی لِوِل باس خودش را دارد و فقط بازیکن‌های همان بازه می‌توانند با آن بجنگند؛ روزی یک بار. جدا از باس جهانی.",
                "👹 <b>Level boss</b>\nEvery level band has its own boss and only players of that band can fight it, once a day. Separate from the world boss."),
             "", _T(ctx, f"بازه‌ی تو: {band_txt} · باس: <b>{b_fa}</b>", f"Your band: {band_txt} · Boss: <b>{b_en}</b>"),
             _T(ctx, "🎁 جایزه: تجربه و سکه ×۴ و یک آیتم هم‌رنگ بازه؛ شانس یادگار تکامل ۲۵٪، سنگ آبدیده‌سازی ۲۰٪، کلید دنیای درون ۲٪ (و در بازه‌ی آخر ۳٪ اکسسوری قرمز)",
                "🎁 Reward: XP and coins ×4 and an item of the band's colour; 25% evolution relic, 20% Tempering Stone, 2% Inner World Key (and 3% red accessory in the top band)"),
             "", _T(ctx, "همه‌ی باس‌ها:", "All bosses:")]
    for i, (a, b, f, e, _c, _r) in enumerate(LEVEL_BOSSES):
        lines.append(("▶️ " if i == info["band"] else "• ") + (f"{fnum(a, L)}–{fnum(b, L)}" if b < 9999 else f"{fnum(a, L)}+") + f" · {f if L == 'fa' else e}")
    rows = []
    if info["done"]:
        lines += ["", _T(ctx, "✅ امروز با باست جنگیدی؛ فردا دوباره.", "✅ You fought your boss today; again tomorrow.")]
    else:
        rows.append([(_T(ctx, f"⚔️ نبرد با {b_fa}", f"⚔️ Fight {b_en}"), "lbg", "")])
    rows.append(nav(ctx))
    return Out(head(ctx, "m_lbs") + "\n".join(lines), rows)


@action("lbg")
async def level_boss_go(ctx, arg):
    status, doc = await level_boss_start(ctx.uid, ctx.lang)
    if status == "ok":
        return await _to_battle(ctx, doc)
    msg = {"busy": _T(ctx, "اول نبرد فعلی‌ات را تمام کن.", "Finish your current fight first."),
           "done": _T(ctx, "امروز با باست جنگیدی.", "You fought your boss today."), "wait": "⏳"}.get(status, "❌")
    return Out(alert=msg)


# ---- roll shop ----------------------------------------------------------------------------------------------------------
@action("rsh")
async def roll_shop(ctx, arg):
    L = ctx.lang
    ch = await get_char(ctx.uid)
    done = int(ch.get("rolls", 0))
    left = ROLL_JACKPOT_EVERY - done % ROLL_JACKPOT_EVERY
    odds = " · ".join(f"{rarity_name(r, L)} {fnum(w, L)}{'٪' if L == 'fa' else '%'}" for r, w in ROLL_WEIGHTS.items())
    kind = _T(ctx, "کارت‌های کیدو (باکودو و هادو)" if ch.get("race") in ("shinigami", "visored") else "کارت‌های تکنیک نژادت",
              "Kidō cards (Bakudō and Hadō)" if ch.get("race") in ("shinigami", "visored") else "your race's technique cards")
    lines = [_T(ctx, f"🎰 <b>شاپ رول</b>\nهر رول یک {kind} یا تخم روح آبی به بالا. شانس رنگ‌ها: {odds}",
                f"🎰 <b>Roll shop</b>\nEach roll gives {kind} or a spirit egg, blue and up. Colour odds: {odds}"),
             _T(ctx, f"🌟 جک‌پات: هر {fnum(ROLL_JACKPOT_EVERY, L)} رول یک اکسسوری قرمز + سنگ آبدیده‌سازی. {fnum(left, L)} رول تا جک‌پات بعدی.",
                f"🌟 Jackpot: every {ROLL_JACKPOT_EVERY} rolls a red accessory + a Tempering Stone. {left} rolls to the next one."),
             _T(ctx, f"💰 سکه‌ی تو: {fnum(ch.get('coins', 0), L)}", f"💰 Your coins: {fnum(ch.get('coins', 0), L)}")]
    rows = [[(_T(ctx, f"🎲 ۱ رول · {fnum(ROLL_COST, L)}", f"🎲 1 roll · {fnum(ROLL_COST, L)}"), "rr1", "1"),
             (_T(ctx, f"🎲 ۱۰ رول · {fnum(ROLL_TEN_COST, L)}", f"🎲 10 rolls · {fnum(ROLL_TEN_COST, L)}"), "rr1", "10")],
            nav(ctx)]
    return Out(head(ctx, "m_rsh") + "\n".join(lines), rows)


@action("rr1")
async def roll_do(ctx, arg):
    L = ctx.lang
    status, data = await roll(ctx.uid, 10 if arg == "10" else 1)
    if status == "funds":
        return Out(alert=_T(ctx, f"{fnum(data, L)} 🪙 لازم است.", f"Needs {fnum(data, L)} 🪙."))
    if status != "ok":
        return Out(alert="⏳")
    got = [("🌟 " if r["jackpot"] else "• ") + iname(r["id"], L) for r in data["results"]]
    out = await roll_shop(ctx, "")
    out.text = _T(ctx, "🎲 نتیجه:\n", "🎲 You got:\n") + "\n".join(got) + "\n\n" + out.text
    return out


# ---- elite shop ---------------------------------------------------------------------------------------------------------
@action("els")
async def elite_shop(ctx, arg):
    L = ctx.lang
    ch = await get_char(ctx.uid)
    if int(ch["level"]) < ELITE_MIN_LEVEL:
        return Out(head(ctx, "m_els") + _T(ctx, f"🏛 شاپ نخبگان از لِوِل {fnum(ELITE_MIN_LEVEL, L)} باز می‌شود.",
                                           f"🏛 The elite shop opens at level {ELITE_MIN_LEVEL}."), [nav(ctx)])
    stock = elite_stock(today_key(), int(ch["level"]))
    lines = [_T(ctx, "🏛 <b>شاپ نخبگان</b>\nآیتم‌های بنفش و طلایی و سنگ آبدیده‌سازی؛ از لِوِل ۱۰۰ موجودی بیشتر. از هر کدام روزی ۳ تا.",
                "🏛 <b>Elite shop</b>\nPurple and gold items and the Tempering Stone; a bigger stock from level 100. Up to 3 of each a day.")]
    rows = [[(f"{iname(i, L)} — {fnum(elite_price(i), L)}🪙"[:60], "elb", i)] for i in stock]
    rows.append(nav(ctx))
    return Out(head(ctx, "m_els") + "\n".join(lines), rows)


@action("elb")
async def elite_buy_cb(ctx, arg):
    L = ctx.lang
    status, data = await elite_buy(ctx.uid, arg, today_key())
    if status == "ok":
        out = await elite_shop(ctx, "")
        out.alert = _T(ctx, f"✅ خریدی: {iname(arg, L)}", f"✅ Bought: {iname(arg, L)}")
        return out
    msg = {"funds": _T(ctx, f"{fnum(data or 0, L)} 🪙 لازم است.", f"Needs {fnum(data or 0, L)} 🪙."),
           "limit": _T(ctx, "از این آیتم امروز ۳ تا خریدی.", "You bought 3 of this today."),
           "gone": _T(ctx, "این آیتم دیگر در قفسه نیست.", "No longer in stock.")}.get(status, "❌")
    return Out(alert=msg)


# ---- Inner World 2 ------------------------------------------------------------------------------------------------------
@action("in2")
async def inner2_panel(ctx, arg):
    L = ctx.lang
    ch = await get_char(ctx.uid)
    inv = await inv_get(ctx.uid)
    keys = int(inv["items"].get(INNER_KEY, 0))
    cur = ch.get("inner2") or {}
    lines = [_T(ctx, "🌌 <b>دنیای درون ۲</b>\nبا «کلید دنیای درون» به عمیق‌ترین لایه‌ی روحت برو. هر بار یک مسیر را انتخاب کن تا یک بونوس دائمی و خالص (غیر از استت) بگیری؛ هر مسیر سقف دارد.",
                "🌌 <b>Inner World 2</b>\nUse an Inner World Key to reach the deepest layer of your soul. Each visit, pick a path for a small permanent pure bonus (not a stat); every path has a cap."),
             _T(ctx, f"🗝 کلیدهای تو: {fnum(keys, L)} (خیلی کمیاب: باس سطح و جک‌پات‌ها)", f"🗝 Your keys: {keys} (very rare: level bosses and jackpots)"), ""]
    rows = []
    for path, (f, e, key, step, cap) in INNER2.items():
        have = float(cur.get(key, 0.0))
        label = {"dmg": _T(ctx, "آسیب", "damage"), "def": _T(ctx, "دفاع", "defence"), "regen": _T(ctx, "بازسازی جان در هر نوبت", "HP regen per turn"),
                 "xp": _T(ctx, "تجربه", "XP")}[key]
        lines.append(f"• {f if L == 'fa' else e}: +{have * 100:g}% {label} (" + _T(ctx, "سقف", "cap") + f" {cap * 100:g}%)")
        if keys and have < cap - 1e-9:
            rows.append([(f"🗝 {f if L == 'fa' else e} (+{step * 100:g}%)", "in2c", path)])
    rows.append(nav(ctx))
    return Out(head(ctx, "m_in2") + "\n".join(lines), rows)


@action("in2c")
async def inner2_choose(ctx, arg):
    status, data = await inner2_use(ctx.uid, arg)
    if status == "ok":
        out = await inner2_panel(ctx, "")
        out.alert = _T(ctx, "✨ روحت قوی‌تر شد.", "✨ Your soul grew stronger.")
        return out
    msg = {"cap": _T(ctx, "این مسیر به سقف رسیده.", "This path is at its cap."),
           "nokey": _T(ctx, "کلید دنیای درون نداری.", "You have no Inner World Key.")}.get(status, "❌")
    return Out(alert=msg)


# ---- companion upgrade ---------------------------------------------------------------------------------------------------
@action("pup")
async def pet_upgrade_cb(ctx, arg):
    L = ctx.lang
    status, data = await pet_upgrade(ctx.uid)
    from handlers_world import pet_panel
    if status == "ok":
        out = await pet_panel(ctx, "")
        out.alert = _T(ctx, f"⭐ همراهت به ★{fnum(data + 1, L)} رسید!", f"⭐ Your companion reached ★{data + 1}!")
        return out
    if status == "mats":
        n, t = data
        return Out(alert=_T(ctx, f"{fnum(n, L)} ماده‌ی روحی (نخ روحی، پارچه‌ی گیگای، نوار روحی) {rarity_name(_RARS[t], L)} یا بالاتر لازم است.",
                            f"Needs {n} spirit materials (thread, gigai cloth, ribbon), {rarity_name(_RARS[t], L)} or higher."))
    msg = {"funds": _T(ctx, f"{fnum(data or 0, L)} 🪙 لازم است.", f"Needs {fnum(data or 0, L)} 🪙."),
           "max": _T(ctx, f"همراهت در بالاترین ستاره است (★{fnum(PET_MAX_TIER + 1, L)}).", f"Your companion is at the top (★{PET_MAX_TIER + 1})."),
           "none": _T(ctx, "همراهی نداری.", "You have no companion.")}.get(status, "⏳")
    return Out(alert=msg)


def pet_up_line(ctx, tier: int) -> str:
    L = ctx.lang
    if tier >= PET_MAX_TIER:
        return ""
    coins, n, t = pet_up_cost(tier)
    return _T(ctx, f"⬆️ ارتقای همراه فعال: {fnum(coins, L)} 🪙 + {fnum(n, L)} ماده‌ی روحی ({rarity_name(_RARS[t], L)} یا بالاتر)",
              f"⬆️ Upgrade the active companion: {fnum(coins, L)} 🪙 + {n} spirit materials ({rarity_name(_RARS[t], L)} or higher)")


_ = ALL  # keep the import for item checks in tests
