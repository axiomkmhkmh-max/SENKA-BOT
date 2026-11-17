"""Race weapons: ten raw weapons per race, each with its own leaning, usable only by that race. Blades no longer drop:
every player grows the one race weapon they chose.

Growth: colour (white -> green -> blue -> purple -> gold -> red) rises with evolution items and coins
(service_raceweapon.ascend), the forge adds +1..+10 (service_economy.forge, +6% attack per level), and the bond
grows with every won fight (data_zanpakuto.bond_key). The catalog below makes one item per weapon and colour
(id rw_<race>_<nn>_<colour>), so the rest of the game (names, rarity, forge, combat) reads it like any weapon.

Attack styles: Shinigami sword + Kidō all-rounder (Asauchi), Visored burst swordsman (Asauchi), Quincy ranged
Reiatsu archer (Quincy Cross), Hollow Hakuda brute with regeneration (mask / Hollow core), Arrancar fast swordsman
(sealed Zanpakutō), Fullbringer crit / trick fighter (an object they love), Human support and spiritual defence
(a spiritual keepsake). Pure data, no I/O.
"""
from data_weapons import PRICE, RARITIES

COLOURS = 6
ATTACK_BY_COLOUR = [30, 42, 56, 76, 106, 160]     # base attack of a weapon at each colour (x its own `atk` factor)
LEVEL_BY_COLOUR = [1, 5, 15, 30, 50, 80]          # player level needed to hold that colour
SKILL_STEP = 0.30                                  # skill chances grow +30% of their base per colour
CRIT_STEP = 0.006                                  # crit grows this much per colour

RACE_STYLE = {
    "shinigami": ("شمشیر و کیدو، همه‌کاره (آساؤچی)", "Sword and Kidō all-rounder (Asauchi)"),
    "visored": ("شمشیرزن انفجاری (آساؤچی)", "Burst swordsman (Asauchi)"),
    "quincy": ("کماندار دوربرد ریاتسو (صلیب کوئینسی)", "Ranged Reiatsu archer (Quincy Cross)"),
    "hollow": ("مبارز هاکودای سنگین با بازسازی (ماسک / هسته‌ی هالو)", "Hakuda brute with regeneration (mask / Hollow core)"),
    "arrancar": ("شمشیرزن سریع (زانپاکتوی مهرشده)", "Fast swordsman (sealed Zanpakutō)"),
    "fullbringer": ("ضربه‌ی کاری و ترفند (شیء دلبسته)", "Crit and trick fighter (a beloved object)"),
    "human": ("پشتیبان و دفاع روحی (یادگار روحی)", "Support and spiritual defence (a spiritual keepsake)"),
}


def _w(fa, en, wtype, element, skills, atk=1.0, crit=0.02, lean=("", "")):
    return {"fa": fa, "en": en, "type": wtype, "element": element, "skills": skills, "atk": atk, "crit": crit, "lean": lean}


# race -> 10 raw weapons. skills: [(skill id, base chance %)], see data_weapons.SKILLS
RACE_WEAPONS = {
    "shinigami": [
        _w("آساؤچیِ شعله", "Flame Asauchi", "elemental", "fire", [("burn", 10)], lean=("آتش", "Fire")),
        _w("آساؤچیِ یخ", "Frost Asauchi", "elemental", "ice", [("freeze", 6)], lean=("یخ", "Ice")),
        _w("آساؤچیِ تندر", "Thunder Asauchi", "elemental", "lightning", [("shock", 10)], lean=("برق", "Lightning")),
        _w("آساؤچیِ مه", "Mist Asauchi", "illusion", "shadow", [("weaken", 10)], lean=("توهم", "Illusion")),
        _w("آساؤچیِ کیدو", "Kidō Asauchi", "kido", "light", [("drain", 6)], atk=0.95, lean=("کیدو", "Kidō")),
        _w("آساؤچیِ دوقلو", "Twin Asauchi", "speed", "water", [("double", 10)], lean=("سرعت", "Speed")),
        _w("آساؤچیِ نگهبان", "Guardian Asauchi", "defensive", "earth", [("counter", 12)], atk=0.95, lean=("دفاع", "Defence")),
        _w("آساؤچیِ بلند", "Long Asauchi", "hybrid", "light", [("pierce", 8)], lean=("نفوذ", "Pierce")),
        _w("آساؤچیِ ارغوانی", "Crimson Asauchi", "melee", "fire", [("bleed", 12)], lean=("خونریزی", "Bleed")),
        _w("آساؤچیِ داور", "Judge's Asauchi", "melee", "shadow", [("execute", 10)], atk=1.03, lean=("پایان‌دادن", "Execute")),
    ],
    "visored": [
        _w("آساؤچیِ ماسک", "Masked Asauchi", "melee", "shadow", [("surge", 10)], atk=1.03, lean=("ضربه‌ی کاری", "Critical")),
        _w("آساؤچیِ زوزه", "Howling Asauchi", "speed", "lightning", [("double", 10)], lean=("سرعت", "Speed")),
        _w("آساؤچیِ سروی سیاه", "Black Cero Asauchi", "elemental", "shadow", [("burn", 10)], lean=("انفجار", "Burst")),
        _w("آساؤچیِ شکارچی", "Hunter Asauchi", "melee", "poison", [("bleed", 12)], lean=("خونریزی", "Bleed")),
        _w("آساؤچیِ هالوی درون", "Inner Hollow Asauchi", "living", "shadow", [("lifesteal", 6)], lean=("مکیدن جان", "Lifesteal")),
        _w("آساؤچیِ شکاف", "Rift Asauchi", "hybrid", "light", [("pierce", 8)], lean=("نفوذ", "Pierce")),
        _w("آساؤچیِ دیوانه", "Berserk Asauchi", "melee", "fire", [("execute", 12)], atk=1.05, crit=0.01, lean=("پایان‌دادن", "Execute")),
        _w("آساؤچیِ سایه", "Shadow Asauchi", "illusion", "shadow", [("weaken", 10)], lean=("توهم", "Illusion")),
        _w("آساؤچیِ سپر ماسک", "Mask-Guard Asauchi", "defensive", "earth", [("counter", 12)], atk=0.95, lean=("دفاع", "Defence")),
        _w("آساؤچیِ طوفان", "Storm Asauchi", "elemental", "water", [("shock", 10)], lean=("برق", "Lightning")),
    ],
    "quincy": [
        _w("کمان هایلیگ", "Heilig Bogen Cross", "ranged", "light", [("pierce", 8)], lean=("نفوذ", "Pierce")),
        _w("کوجاکو", "Kojaku Cross", "ranged", "light", [("double", 10)], lean=("تیر پشت تیر", "Rapid shots")),
        _w("گینری کوجاکو", "Ginrei Kojaku Cross", "ranged", "lightning", [("double", 8), ("shock", 6)], atk=0.97, lean=("رگبار", "Volley")),
        _w("صلیب پنج‌پر", "Five-Point Cross", "ranged", "ice", [("freeze", 6)], lean=("یخ", "Ice")),
        _w("صلیب کیرشه", "Kirsche Cross", "ranged", "fire", [("burn", 10)], lean=("آتش", "Fire")),
        _w("صلیب شاتن", "Schatten Cross", "ranged", "shadow", [("weaken", 10)], lean=("سایه", "Shadow")),
        _w("صلیب زیله", "Seele Cross", "hybrid", "light", [("bleed", 12)], lean=("تیغ ریشی", "Reishi blade")),
        _w("صلیب کلاین", "Klein Cross", "speed", "water", [("surge", 10)], lean=("ضربه‌ی کاری", "Critical")),
        _w("صلیب اشترن", "Stern Cross", "ranged", "light", [("execute", 10)], atk=1.03, lean=("پایان‌دادن", "Execute")),
        _w("صلیب هایزن", "Heizen Cross", "kido", "light", [("drain", 6)], atk=0.95, lean=("گینتو", "Gintō")),
    ],
    "hollow": [
        _w("چنگال استخوانی", "Bone Claw", "melee", "earth", [("bleed", 12)], lean=("خونریزی", "Bleed")),
        _w("نیش ماسک", "Mask Fang", "living", "poison", [("lifesteal", 8)], lean=("مکیدن جان", "Lifesteal")),
        _w("دم خاردار", "Spiked Tail", "hybrid", "poison", [("poison", 10)], lean=("سم", "Poison")),
        _w("پوسته‌ی هالو", "Hollow Hide", "defensive", "earth", [("counter", 14)], atk=0.95, lean=("دفاع", "Defence")),
        _w("هسته‌ی سرو", "Cero Core", "elemental", "shadow", [("burn", 10)], lean=("انفجار", "Burst")),
        _w("آرواره‌ی گرسنه", "Starving Jaw", "living", "shadow", [("drain", 6)], lean=("بلعیدن ریاتسو", "Reiatsu drain")),
        _w("مشت شن", "Sand Fist", "melee", "earth", [("stun", 6)], atk=1.03, lean=("گیج‌کردن", "Stun")),
        _w("بال منوس", "Menos Wing", "speed", "water", [("double", 10)], lean=("سرعت", "Speed")),
        _w("شاخ آجوکاس", "Adjuchas Horn", "melee", "fire", [("execute", 10)], atk=1.03, lean=("پایان‌دادن", "Execute")),
        _w("قلب واستو", "Vasto Heart", "living", "light", [("lifesteal", 6), ("weaken", 6)], atk=0.97, lean=("بازسازی", "Regeneration")),
    ],
    "arrancar": [
        _w("تیغ مهرشده‌ی باد", "Sealed Blade: Gale", "speed", "water", [("double", 10)], lean=("سرعت", "Speed")),
        _w("تیغ مهرشده‌ی ماه", "Sealed Blade: Moon", "melee", "shadow", [("surge", 10)], atk=1.03, lean=("ضربه‌ی کاری", "Critical")),
        _w("تیغ مهرشده‌ی پلنگ", "Sealed Blade: Panther", "melee", "earth", [("bleed", 12)], lean=("خونریزی", "Bleed")),
        _w("تیغ مهرشده‌ی خفاش", "Sealed Blade: Bat", "elemental", "shadow", [("weaken", 10)], lean=("ناامیدی", "Despair")),
        _w("تیغ مهرشده‌ی کوسه", "Sealed Blade: Shark", "elemental", "water", [("pierce", 8)], lean=("نفوذ", "Pierce")),
        _w("تیغ مهرشده‌ی مار", "Sealed Blade: Serpent", "hybrid", "poison", [("poison", 10)], lean=("سم", "Poison")),
        _w("تیغ مهرشده‌ی گرگ", "Sealed Blade: Wolf", "living", "ice", [("lifesteal", 6)], lean=("گله", "Pack")),
        _w("تیغ مهرشده‌ی سونیدو", "Sealed Blade: Sonído", "speed", "lightning", [("shock", 10)], lean=("برق", "Lightning")),
        _w("تیغ مهرشده‌ی هیرو", "Sealed Blade: Hierro", "defensive", "earth", [("counter", 12)], atk=0.95, lean=("دفاع", "Defence")),
        _w("تیغ مهرشده‌ی اسپادا", "Sealed Blade: Espada", "melee", "fire", [("execute", 10)], atk=1.04, lean=("پایان‌دادن", "Execute")),
    ],
    "fullbringer": [
        _w("صلیب داربست", "Cross of Scaffold", "melee", "light", [("surge", 10)], atk=1.03, lean=("ضربه‌ی کاری", "Critical")),
        _w("نشانگر کتاب", "Bookmark", "illusion", "shadow", [("weaken", 10)], lean=("بازنویسی گذشته", "Rewrite the past")),
        _w("خانه‌ی عروسکی", "Dollhouse", "illusion", "poison", [("stun", 6)], lean=("گیج‌کردن", "Stun")),
        _w("بوکس جک‌پات", "Jackpot Knuckle", "melee", "lightning", [("double", 10)], lean=("شانس", "Luck")),
        _w("چکمه‌های کثیف", "Dirty Boots", "speed", "earth", [("double", 8), ("bleed", 6)], atk=0.97, lean=("لگد سریع", "Quick kicks")),
        _w("ساعت دروغ‌نگو", "Lying Watch", "illusion", "shadow", [("freeze", 6)], lean=("زمان", "Time")),
        _w("دستکش بازی", "Game Glove", "hybrid", "fire", [("burn", 10)], lean=("آتش", "Fire")),
        _w("شیشه‌ی دلبسته", "Cherished Glass", "ranged", "light", [("pierce", 8)], lean=("نفوذ", "Pierce")),
        _w("زنجیر پیوند", "Bond Chain", "living", "water", [("drain", 6)], lean=("پیوند", "Bond")),
        _w("کارد آشپزخانه", "Kitchen Knife", "melee", "poison", [("execute", 10)], atk=1.03, lean=("پایان‌دادن", "Execute")),
    ],
    "human": [
        _w("سنجاق شش‌گل", "Six-Flower Hairpin", "defensive", "light", [("counter", 12)], atk=0.95, lean=("سپر", "Shield")),
        _w("طلسم کاراکورا", "Karakura Charm", "kido", "light", [("drain", 6)], atk=0.95, lean=("ریاتسو", "Reiatsu")),
        _w("دستبند روحی", "Spirit Bracelet", "defensive", "earth", [("counter", 10)], atk=0.95, lean=("دفاع", "Defence")),
        _w("زنگوله‌ی پدربزرگ", "Grandpa's Bell", "living", "water", [("lifesteal", 6)], lean=("مکیدن جان", "Lifesteal")),
        _w("چوب بیسبال", "Baseball Bat", "melee", "earth", [("stun", 6)], atk=1.03, lean=("گیج‌کردن", "Stun")),
        _w("دفتر نقاشی روح", "Spirit Sketchbook", "illusion", "shadow", [("weaken", 10)], lean=("توهم", "Illusion")),
        _w("دستکش کاراته", "Karate Gloves", "speed", "fire", [("double", 10)], lean=("هاکودا", "Hakuda")),
        _w("گردنبند مادر", "Mother's Pendant", "living", "light", [("lifesteal", 6), ("weaken", 4)], atk=0.97, lean=("محافظت", "Protection")),
        _w("تیرکمان بچگی", "Childhood Slingshot", "ranged", "lightning", [("pierce", 8)], lean=("نفوذ", "Pierce")),
        _w("کتاب دعای قدیمی", "Old Prayer Book", "kido", "ice", [("freeze", 6)], lean=("آرامش", "Calm")),
    ],
}


def rw_base(race: str, n: int) -> str:
    """Base id of a race weapon (the same at every colour): rw_<race>_<nn>."""
    return f"rw_{race}_{n:02d}"


def rw_id(race: str, n: int, colour: int) -> str:
    return f"{rw_base(race, n)}_{int(colour)}"


def parse_rw(item_id: str):
    """(race, n, colour) of a race weapon item id, or None."""
    if not item_id or not str(item_id).startswith("rw_"):
        return None
    parts = str(item_id).split("_")
    if len(parts) != 4:
        return None
    try:
        return parts[1], int(parts[2]), int(parts[3])
    except ValueError:
        return None


def _build():
    out = []
    for race, weapons in RACE_WEAPONS.items():
        for n, w in enumerate(weapons):
            for c in range(COLOURS):
                rar = RARITIES[c]
                iid = rw_id(race, n, c)
                out.append({
                    "_id": iid, "item_id": iid, "category": "weapon", "subtype": "rweapon", "race": race,
                    "rw": rw_base(race, n), "rw_n": n, "rw_c": c,
                    "name_fa": w["fa"], "name_en": w["en"], "meaning_fa": w["lean"][0], "meaning_en": w["lean"][1],
                    "rarity": rar, "element": w["element"], "weapon_type": w["type"],
                    "attack": int(round(ATTACK_BY_COLOUR[c] * w["atk"])), "crit": round(w["crit"] + CRIT_STEP * c, 3),
                    "level_req": LEVEL_BY_COLOUR[c],
                    "skills": [{"id": sid, "p": int(round(p * (1 + SKILL_STEP * c)))} for sid, p in w["skills"]],
                    "durability": 100, "base_price": PRICE[rar], "sell_price": 0, "tradeable": False,
                    "stack_max": 1, "slot": "weapon",
                })
    return out


RACE_WEAPON_ITEMS = _build()


def colour_for_rarity(rarity: str) -> int:
    return RARITIES.index(rarity) if rarity in RARITIES else 0


# Ascension to the next colour: evolution items (count, lowest rarity index) and coins. The level gate is
# LEVEL_BY_COLOUR of the new colour.
def ascend_cost(colour: int):
    """(items needed, min rarity index of those items, coins) to go from `colour` to colour + 1."""
    return colour + 1, max(0, min(3, colour)), 2000 * (colour + 1) ** 2
