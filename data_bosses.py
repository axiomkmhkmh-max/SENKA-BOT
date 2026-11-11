"""50+ world bosses with level scaling and a unique trait each (some)."""
_NAMES = [
    ("Wandering Hollow", "هالوی سرگردان", None), ("Hollow Brute", "هالوی وحشی", None),
    ("Cursed Blade Spirit", "روح شمشیر نفرین‌شده", "bleed"), ("Grand Fisher", "گرند فیشر", None),
    ("Rift Crawler", "خزنده‌ی شکاف", None), ("Menos Grande", "منوس گرانده", None),
    ("Gillian Colossus", "غول گیلیان", None), ("Crimson Moon Beast", "جانور ماه سرخ", "enrage"),
    ("Adjuchas Stalker", "شکارچی آجوکاس", None), ("Bone Matriarch", "مادر استخوان", None),
    ("Vasto Lorde Wraith", "شبح واستو لورد", None), ("Sand Leviathan", "لویاتان شنی", None),
    ("Grimmjow", "گریمجو", "enrage"), ("Nnoitra", "نوایترا", None), ("Nightmare Aspect", "چهره‌ی کابوس", "dodge"),
    ("Ulquiorra", "اولکیورا", "dodge"), ("Starrk", "استارک", None), ("Baraggan", "باراگان", "decay"),
    ("Fallen Captain", "کاپیتان سقوط‌کرده", None), ("Traitor Captain", "کاپیتان خائن", None),
    ("Iron Sentinel", "نگهبان آهنین", None), ("Storm Warden", "نگهبان توفان", None),
    ("Glacier Tyrant", "ستمگر یخچالی", None), ("Ember Sovereign", "فرمانروای شرر", "burn"),
    ("Venom Queen", "ملکه‌ی زهر", "poison"), ("Sternritter Elite", "استرنریتر نخبه", None),
    ("Star Cross Knight", "شوالیه‌ی ستاره", None), ("Holy Archer", "کمان‌دار مقدس", None),
    ("Zaraki", "زارکی", "enrage"), ("Shadow Arbiter", "داور سایه", "dodge"),
    ("Mirror Sovereign", "فرمانروای آینه", "illusion"), ("Aizen", "آیزن", "illusion"),
    ("Gin", "گین", None), ("Void Gardener", "باغبان خلأ", None), ("Abyss Maw", "آروغ ورطه", None),
    ("Yammy-class Titan", "تایتان کلاس یامی", None), ("Soul Reaper Exile", "تبعیدی شینیگامی", None),
    ("Tide Calamity", "فاجعه‌ی جزر", None), ("Thunder Oracle", "پیشگوی تندر", None),
    ("Eclipse Herald", "منادی خسوف", None), ("Palace Gatekeeper", "دروازه‌بان کاخ", None),
    ("Royal Guard Captain", "فرمانده‌ی گارد سلطنتی", None), ("Yamamoto", "یاماموتو", "burn"),
    ("Dangai Devourer", "بلعنده‌ی دنگای", None), ("Origin Echo", "پژواک آغاز", None),
    ("Jugram", "جوگرام", None), ("Yhwach", "یوهابخ", "dodge"), ("Reishi Tyrant", "ستمگر ریشی", None),
    ("Soul King's Shade", "سایه‌ی Soul King", None), ("Calamity Apex", "اوج فاجعه", "enrage"),
]


def _build():
    out = []
    for i, (en, fa, trait) in enumerate(_NAMES):
        lvl = 3 + int(i * 2.2)
        out.append({"_id": f"boss_{i + 1:02d}", "boss_id": f"boss_{i + 1:02d}", "name_en": en, "name_fa": fa,
                    "level": lvl, "hp": int((2.2 * lvl + 15) * 120 * (1 + lvl / 60)), "attack": 20 + lvl * 7,
                    "defense": 2 + lvl * 1.1, "trait": trait})
    return out


BOSSES = _build()
BOSS_BY_ID = {b["_id"]: b for b in BOSSES}
