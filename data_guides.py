"""Player guides: what each race is good at, and what each race weapon really does (shown when choosing them).

Weapon guides are built from the weapon's own data (type, element, skills), so they always match the game rules in
engine.py, engine_range.py and data_misc.FORM2_EFFECT. Pure data, no I/O.
"""
from data_items import ALL
from data_race_tech import RACE_TECH
from data_weapons import BEATS, ELEMENT_FA, TYPE_FA

_FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def _n(v, lang):
    return str(v).translate(_FA) if lang == "fa" else str(v)


# ---- races -------------------------------------------------------------------------------------------------------------
# (fa, en) for: style, strengths, weakness, release, evolution peak, who it suits, difficulty
RACE_GUIDE = {
    "shinigami": {
        "style": ("شمشیر و کیدو؛ همه‌کاره و پرابزارترین نژاد", "Sword and Kidō; the all-rounder with the most tools"),
        "good": ("کیدو (هادو برای ضربه، باکودو برای سپر)، گتسوگا، شونپو برای جاخالی و ضدحمله، و تکنیک زانپاکتو بعد از شیکای",
                 "Kidō (Hadō to strike, Bakudō to shield), Getsuga, Shunpo to dodge and counter, and the Zanpakutō technique after Shikai"),
        "bad": ("جان کم (هاکودای پایین)؛ باید با سپر و جاخالی بازی کنی", "Low HP (low Hakuda); you must play with shields and dodges"),
        "peak": ("کاپیتان: بانکای یک نوبت بیشتر و ۱۰٪ آسیب", "Captain: Bankai lasts one more turn, +10% damage"),
        "for": ("کسی که دوست داره هر نوبت بین ضربه، جادو و دفاع فکر کنه", "Players who like to think every turn between blade, spell and guard"),
        "level": ("متوسط", "Medium"),
    },
    "visored": {
        "style": ("شمشیرزن انفجاری؛ شینیگامی با قدرت هالوی درون", "Burst swordsman: a Shinigami with the Hollow inside"),
        "good": ("همه‌ی ابزار شینیگامی، به‌اضافه‌ی سرو و ماسک هالو؛ با ماسک «ضربه‌ی ماسک» باز می‌شه",
                 "Every Shinigami tool plus Cero and the Hollow Mask; the mask opens Mask Strike"),
        "bad": ("تا تکامل نیافته، ماسک گاهی کنترل رو می‌گیره و نوبت می‌سوزه", "Until evolved, the mask sometimes takes control and the turn is lost"),
        "peak": ("هالوفیکیشن کامل: بی‌خشم، سرو ۱٫۲ برابر و ۱۰٪ آسیب", "Perfect Hollowfication: no mask rage, Cero ×1.2, +10% damage"),
        "for": ("کسی که ریسک رو برای ضربه‌های بزرگ دوست داره (اول شینیگامی شو و گذرگاه ویزورد رو رد کن)",
                "Players who take risks for big hits (be a Shinigami first and clear the Visored Gauntlet)"),
        "level": ("سخت", "Hard"),
    },
    "quincy": {
        "style": ("کماندار دوربرد با ریاتسوی زیاد", "Ranged archer with a deep reiatsu pool"),
        "good": ("بیشترین ریاتسو، ۱۲٪ آسیب و ۱۰٪ نفوذ پایه، هیرنکیاکو برای جاخالی، بلوت برای سپر یا قدرت، و تیر رگباری",
                 "The most reiatsu, +12% damage and 10% pierce at base, Hirenkyaku to dodge, Blut for shield or power, and arrow volleys"),
        "bad": ("زنجوتسو و هاکودای کم؛ با سلاح دوربرد اگه دشمن بچسبه اول باید عقب بکشی",
                "Low Zanjutsu and Hakuda; with a ranged weapon you must step back when the foe closes in"),
        "peak": ("شوتس‌اشتافل: ۱۵٪ آسیب و ۱۰٪ نفوذ بیشتر", "Schutzstaffel: +15% damage, +10% pierce"),
        "for": ("کسی که از دور و با ضربه‌های پشت‌سرهم بازی می‌کنه", "Players who fight from range with rapid shots"),
        "level": ("آسان تا متوسط", "Easy to medium"),
    },
    "hollow": {
        "style": ("مبارز هاکودای سنگین با بازسازی", "Heavy Hakuda brute that regenerates"),
        "good": ("جان زیاد، سرو (یک نوبت جمع، نوبت بعد شلیک)، نگاسیون برای سپر، بلعیدن که جان می‌مکه، بازسازی سریع",
                 "Lots of HP, Cero (gather one turn, fire the next), Negación shield, Devour that drains life, fast regeneration"),
        "bad": ("آسیب پایه کمتر؛ سروی در حال جمع شدن با ضربه‌ی سنگین قطع می‌شه",
                "Lower base damage; a gathering Cero breaks under a heavy hit"),
        "peak": ("آرانکار: رسورکسیون یک نوبت بیشتر (واستو لورد هم هر نوبت ۳٪ جان برمی‌گردونه)",
                 "Arrancar: Resurrección lasts one more turn (Vasto Lorde heals 3% HP every turn)"),
        "for": ("کسی که می‌خواد دیر بمیره و با حوصله دشمن رو خسته کنه", "Players who want to outlast the foe"),
        "level": ("آسان", "Easy"),
    },
    "arrancar": {
        "style": ("شمشیرزن سریع با زانپاکتوی مهرشده", "Fast swordsman with a sealed Zanpakutō"),
        "good": ("زنجوتسو و هوهوی بالا، بالا (گلوله‌ی سریع و نفوذی)، سرو، هیرو برای کم کردن آسیب، پسکیسا برای ضربه‌ی کاری، و سرو اسکوراس",
                 "High Zanjutsu and Hohō, Bala (a fast piercing shot), Cero, Hierro to cut damage, Pesquisa for crits, and Cero Oscuras"),
        "bad": ("ضریب آسیب پایه کمتر و بدون کیدو؛ قدرتش بیشتر با تکامل و هوهوی بالا میاد",
                "Lower base damage multiplier and no Kidō; much of its power comes with evolution and high Hohō"),
        "peak": ("سگوندا اتاپا: رسورکسیون یک نوبت بیشتر و ۱۰٪ آسیب", "Segunda Etapa: Resurrección lasts one more turn, +10% damage"),
        "for": ("کسی که اول می‌زنه و با سرعت بازی می‌کنه", "Players who strike first and play fast"),
        "level": ("متوسط", "Medium"),
    },
    "fullbringer": {
        "style": ("ضربه‌ی کاری و ترفند با شیء دلبسته", "Crits and tricks through a beloved object"),
        "good": ("۴٪ ضربه‌ی کاری و ۱۲٪ جان پایه، ضربه‌ی براینگر با خونریزی، براینگر لایت برای جاخالی، کتاب پایان برای ضعیف کردن دشمن و «زمان دروغ نمی‌گوید» برای گرفتن نوبتش",
                 "+4% crit and +12% HP at base, the Bringer strike that bleeds, Bringer Light to dodge, Book of the End to weaken and Time Tells No Lies to take the foe's turn"),
        "bad": ("کیدو نداره و آسیب خامش متوسطه؛ باید از ترفندها درست استفاده کنی", "No Kidō and only average raw damage; the tricks must be used well"),
        "peak": ("فول‌برینگ کامل: رهاسازی یک نوبت بیشتر و ۱۰٪ جان", "Complete Fullbring: release lasts one more turn, +10% HP"),
        "for": ("کسی که از کنترل دشمن و ضربه‌های کاری لذت می‌بره", "Players who enjoy controlling the foe and landing crits"),
        "level": ("متوسط", "Medium"),
    },
    "human": {
        "style": ("پشتیبان و دفاع روحی", "Support and spiritual defence"),
        "good": ("۱۰٪ تجربه‌ی بیشتر، ۶٪ آسیب و ۹٪ جان پایه، ضربه‌ی روح، سپر سانتن کسشون، درمان سوتن کیشون و ضربه‌ی کوتن زانشون؛ به هالوها هم بیشتر آسیب می‌زنه",
                 "+10% XP, +6% damage and +9% HP at base, Soul Strike, the Santen Kesshun shield, Sōten Kisshun healing and the Koten Zanshun strike; extra damage to Hollows"),
        "bad": ("دفاعش ۳٪ کمتره و ابزار انفجاری کمی داره", "3% less defence and few burst tools"),
        "peak": ("نگهبان کاراکورا: رهاسازی یک نوبت بیشتر و ۱۰٪ آسیب", "Karakura Guardian: release lasts one more turn, +10% damage"),
        "for": ("تازه‌کارها؛ زود لِوِل می‌گیره و با سپر و درمان کم‌تر می‌بازه", "Beginners: levels fast, and shields and heals forgive mistakes"),
        "level": ("آسان", "Easy"),
    },
}


def race_guide(race: str, lang: str) -> str:
    """A short guide to a race: style, strengths, weakness, release, techniques, evolution peak, who it suits."""
    from data_bleachfx import RELEASE_NAME
    from data_races import RACES
    g, i = RACE_GUIDE[race], 0 if lang == "fa" else 1
    r = RACES[race]
    techs = [t["icon"] + " " + t["name"][i] for t in (RACE_TECH.get(race) or {}).values()]
    from data_race_tech import ABILITY_SHARE, ABILITY_STAT, STAT_FA
    stat = ABILITY_STAT.get(race)
    pct = round(ABILITY_SHARE * 100)
    if stat == "weapon":
        power = (("قدرت سلاح در ابیلیتی‌ها دو برابر حساب می‌شه (روی زنجوتسو)؛ سلاح قوی‌تر یعنی ابیلیتی قوی‌تر",
                  "the weapon's attack counts double in abilities (on top of Zanjutsu): a stronger weapon, stronger abilities"))
    else:
        power = ((f"{pct}٪ قدرت ابیلیتی‌ها، سپرها و درمان‌ها از {STAT_FA[stat]} میاد؛ امتیاز رو بیشتر روی {STAT_FA[stat]} بذار",
                  f"{pct}% of the power of abilities, shields and heals comes from {stat.capitalize()}: put your points there"))
    power = power[i].replace(str(pct), str(pct).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))) if lang == "fa" else power[i]
    if lang == "fa":
        lines = [f"🧬 <b>{r['name_fa']}</b> · سختی بازی: {g['level'][0]}",
                 f"⚔️ <b>سبک:</b> {g['style'][0]}",
                 f"💪 <b>قوت:</b> {g['good'][0]}",
                 f"⚠️ <b>ضعف:</b> {g['bad'][0]}",
                 f"👑 <b>رهاسازی:</b> {RELEASE_NAME[race][0]}"]
        if techs:
            lines.append("✨ <b>تکنیک‌ها (همه از لِوِل ۱ باز):</b> " + "، ".join(techs))
        lines.append(f"📊 <b>استت ابیلیتی:</b> {power}")
        lines += [f"🔝 <b>اوج تکامل:</b> {g['peak'][0]}", f"🎯 <b>مناسب:</b> {g['for'][0]}"]
    else:
        lines = [f"🧬 <b>{r['name_en']}</b> · difficulty: {g['level'][1]}",
                 f"⚔️ <b>Style:</b> {g['style'][1]}",
                 f"💪 <b>Strengths:</b> {g['good'][1]}",
                 f"⚠️ <b>Weakness:</b> {g['bad'][1]}",
                 f"👑 <b>Release:</b> {RELEASE_NAME[race][1]}"]
        if techs:
            lines.append("✨ <b>Techniques (all open from level 1):</b> " + ", ".join(techs))
        lines.append(f"📊 <b>Ability stat:</b> {power}")
        lines += [f"🔝 <b>Evolution peak:</b> {g['peak'][1]}", f"🎯 <b>Suits:</b> {g['for'][1]}"]
    return "\n".join(lines)


# ---- weapons -----------------------------------------------------------------------------------------------------------
# weapon type -> (fa, en): its reach (engine_range.TYPE_REACH) and its second-form effect (data_misc.FORM2_EFFECT)
TYPE_GUIDE = {
    "melee": ("نزدیک‌زن (فاصله‌ی ۰ تا ۱). در فرم دوم ۲۵٪ زره دشمن رو نادیده می‌گیره.",
              "Close range (distance 0 to 1). In the second form it ignores 25% of the foe's armour."),
    "elemental": ("نزدیک تا متوسط (فاصله‌ی ۰ تا ۲). در فرم دوم هر ضربه دشمن رو می‌سوزونه.",
                  "Close to mid range (0 to 2). In the second form every hit burns the foe."),
    "kido": ("از فاصله‌ی ۱ تا ۴ می‌زنه، ولی از چسبیده نه. در فرم دوم با هر ضربه ۸٪ ریاتسوی دشمن رو می‌دزده.",
             "Strikes from distance 1 to 4, not at contact. In the second form every hit steals 8% of the foe's reiatsu."),
    "illusion": ("نزدیک تا متوسط (فاصله‌ی ۰ تا ۲). در فرم دوم ۳۰٪ ضربه‌های دشمن به خطا می‌ره.",
                 "Close to mid range (0 to 2). In the second form 30% of the foe's blows miss."),
    "living": ("نزدیک‌زن (فاصله‌ی ۰ تا ۱). در فرم دوم ۲۰٪ آسیبت به جانت برمی‌گرده.",
               "Close range (0 to 1). In the second form 20% of your damage heals you."),
    "defensive": ("نزدیک‌زن (فاصله‌ی ۰ تا ۱). در فرم دوم ۳۵٪ آسیب کمتری می‌خوری.",
                  "Close range (0 to 1). In the second form you take 35% less damage."),
    "ranged": ("دوربرد (فاصله‌ی ۲ تا ۴)؛ اگه دشمن بچسبه، اول عقب می‌کشی. در فرم دوم ۴۰٪ شانس ضربه‌ی دوم.",
               "Long range (2 to 4); if the foe closes in, you step back first. In the second form a 40% chance of a second hit."),
    "speed": ("نزدیک‌زن (فاصله‌ی ۰ تا ۱). در فرم دوم ۵۰٪ شانس ضربه‌ی دوم.",
              "Close range (0 to 1). In the second form a 50% chance of a second hit."),
    "hybrid": ("نزدیک تا متوسط (فاصله‌ی ۰ تا ۲). در فرم دوم ۱۵٪ زره دشمن رو نادیده می‌گیره.",
               "Close to mid range (0 to 2). In the second form it ignores 15% of the foe's armour."),
}
# skill id -> (fa, en) plain explanation ({p} = chance or strength) and who it suits
SKILL_GUIDE = {
    "bleed": ("{p}٪ شانس زخم خونریز: ۴ نوبت، هر نوبت ۲٪ جان دشمن", "{p}% chance of a bleeding wound: 2% of the foe's HP each turn for 4 turns"),
    "burn": ("{p}٪ شانس سوزاندن: ۳ نوبت، هر نوبت ۳٪ جان دشمن", "{p}% chance to burn: 3% of the foe's HP each turn for 3 turns"),
    "poison": ("{p}٪ شانس سم: ۳ نوبت، هر نوبت ۵٪ جان دشمن؛ تا سه لایه روی هم", "{p}% chance to poison: 5% of the foe's HP each turn for 3 turns; stacks up to three"),
    "shock": ("{p}٪ شانس شوک: دشمن ۲ نوبت ۱۵٪ آسیب بیشتر می‌خوره", "{p}% chance to shock: the foe takes 15% more damage for 2 turns"),
    "freeze": ("{p}٪ شانس یخ زدن: دشمن نوبت بعدش رو از دست می‌ده", "{p}% chance to freeze: the foe loses its next turn"),
    "stun": ("{p}٪ شانس گیج کردن: دشمن نوبت بعدش رو از دست می‌ده", "{p}% chance to stun: the foe loses its next turn"),
    "lifesteal": ("{p}٪ آسیبی که می‌زنی به جانت برمی‌گرده", "{p}% of the damage you deal heals you"),
    "pierce": ("{p}٪ زره دشمن رو نادیده می‌گیره", "ignores {p}% of the foe's armour"),
    "double": ("{p}٪ شانس ضربه‌ی دوم با نصف قدرت", "{p}% chance of a second strike at half power"),
    "execute": ("به دشمنِ زیر ۳۰٪ جان، {p}٪ آسیب بیشتر", "{p}% more damage to a foe under 30% HP"),
    "drain": ("با هر ضربه {p}٪ ریاتسوی دشمن رو می‌دزده", "every hit steals {p}% of the foe's reiatsu"),
    "counter": ("وقتی دفاع می‌کنی، {p}٪ آسیب رو به دشمن برمی‌گردونه", "while you guard, {p}% of the damage goes back to the foe"),
    "surge": ("ضربه‌های کاریت {p}٪ قوی‌تر می‌شن", "your critical hits are {p}% stronger"),
    "weaken": ("{p}٪ شانس کم کردن ۱۵٪ دفاع دشمن برای ۳ نوبت", "{p}% chance to cut the foe's defence by 15% for 3 turns"),
}
SKILL_SUITS = {
    "bleed": ("نبردهای طولانی و باس‌ها", "long fights and bosses"), "burn": ("نبردهای طولانی و باس‌ها", "long fights and bosses"),
    "poison": ("نبردهای طولانی و باس‌ها", "long fights and bosses"),
    "shock": ("کسی که می‌خواد ضربه‌های بعدیش سنگین‌تر بشینه", "making your next blows land harder"),
    "weaken": ("کسی که می‌خواد ضربه‌های بعدیش سنگین‌تر بشینه", "making your next blows land harder"),
    "freeze": ("کنترل دشمن و گرفتن نوبتش", "controlling the foe and taking its turns"),
    "stun": ("کنترل دشمن و گرفتن نوبتش", "controlling the foe and taking its turns"),
    "lifesteal": ("دوام آوردن بدون معجون", "lasting without potions"), "drain": ("خالی کردن ریاتسوی دشمن تا نتونه مهارت بزنه", "emptying the foe's reiatsu so it cannot use skills"),
    "pierce": ("دشمن‌های زره‌دار و دوئل", "armoured foes and duels"),
    "double": ("آسیب سریع و انفجاری", "fast burst damage"), "surge": ("آسیب سریع و انفجاری", "fast burst damage"),
    "execute": ("تموم کردن کار دشمنِ نیمه‌جون", "finishing off a wounded foe"),
    "counter": ("بازی دفاعی و دوئل", "a defensive style and duels"),
}
ELEMENT_EN = {"fire": "Fire", "ice": "Ice", "lightning": "Lightning", "earth": "Earth", "water": "Water", "poison": "Poison",
              "shadow": "Shadow", "light": "Light"}
TYPE_EN = {"melee": "Melee", "elemental": "Elemental", "kido": "Kidō", "illusion": "Illusion", "living": "Living",
           "defensive": "Defensive", "ranged": "Ranged", "speed": "Speed", "hybrid": "Hybrid"}


def element_line(el: str, lang: str) -> str:
    strong = BEATS.get(el)
    weak = next((k for k, v in BEATS.items() if v == el), None)  # the defender whose element beats this one
    if lang == "fa":
        if el == "poison":
            return "عنصر سم: به همه ۱۰٪ بیشتر آسیب می‌زنه."
        if strong:
            return f"عنصر {ELEMENT_FA[el]}: به عنصر {ELEMENT_FA[strong]} ۵۰٪ بیشتر و به عنصر {ELEMENT_FA[weak]} ۲۵٪ کمتر می‌زنه."
        return f"عنصر {ELEMENT_FA[el]}: خنثی؛ نه برتری داره نه ضعف."
    if el == "poison":
        return "Poison element: 10% more damage against everyone."
    if strong:
        return f"{ELEMENT_EN[el]} element: 50% more against {ELEMENT_EN[strong]}, 25% less against {ELEMENT_EN[weak]}."
    return f"{ELEMENT_EN[el]} element: neutral, no edge and no weakness."


def weapon_guide(item_id: str, lang: str) -> str:
    """What a race weapon really does: its numbers, skills in plain words, reach, second form, element, who it suits."""
    it = ALL[item_id]
    fa, i = lang == "fa", 0 if lang == "fa" else 1
    pct = lambda v: _n(v, lang)  # noqa: E731
    lines = [f"🗡 <b>{it['name_fa' if fa else 'name_en']}</b> · " + (f"گرایش: {it.get('meaning_fa', '')}" if fa else f"leaning: {it.get('meaning_en', '')}"),
             (f"⚔️ قدرت {pct(it['attack'])} · 🎯 ضربه‌ی کاری {pct(round(it['crit'] * 100, 1)).replace('.', '٫')}٪ · نوع {TYPE_FA[it['weapon_type']]}"
              if fa else f"⚔️ Attack {it['attack']} · 🎯 crit {round(it['crit'] * 100, 1)}% · type {TYPE_EN[it['weapon_type']]}")]
    for s in it.get("skills", []):
        lines.append("✦ " + SKILL_GUIDE[s["id"]][i].format(p=pct(s["p"])))
    lines.append("📏 " + TYPE_GUIDE[it["weapon_type"]][i])
    lines.append(("💥 قدرت سلاح با زنجوتسوی تو جمع می‌شه و هر ضربه‌ی شمشیری (معمولی، سنگین، رهاسازی و تکنیک‌ها) رو بزرگ‌تر می‌کنه؛ "
                  "هر سطح فورج ۶٪ به قدرت سلاح اضافه می‌کنه و پیوند، زنجوتسوت رو تا دو برابر قوی می‌کنه. کیدو از قدرت سلاح استفاده نمی‌کنه.") if fa else
                 ("💥 The weapon's attack is added to your Zanjutsu and enlarges every blade hit (normal, heavy, release and "
                  "techniques); each forge level adds 6% to the weapon's attack, and the bond makes your Zanjutsu up to twice as strong. Kidō does not use the weapon's attack."))
    lines.append("🌀 " + element_line(it["element"], lang))
    first = (it.get("skills") or [{}])[0].get("id")
    if first in SKILL_SUITS:
        lines.append(("🎯 مناسب برای: " if fa else "🎯 Suits: ") + SKILL_SUITS[first][i])
    return "\n".join(lines)
