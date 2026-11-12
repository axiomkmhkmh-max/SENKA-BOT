"""50+ world bosses with level scaling and a unique trait each (some)."""
_NAMES = [
    ("Wandering Hollow", "هالوی سرگردان", None), ("Hollow Brute", "هالوی وحشی", None),
    ("Cursed Blade Spirit", "روح شمشیر نفرین‌شده", "bleed"), ("Grand Fisher", "گرند فیشر", None),
    ("Rift Crawler", "خزنده‌ی شکاف", None), ("Menos Grande", "منوس گرانده", "armor"),
    ("Gillian Colossus", "غول گیلیان", None), ("Crimson Moon Beast", "جانور ماه سرخ", "enrage"),
    ("Adjuchas Stalker", "شکارچی آجوکاس", None), ("Bone Matriarch", "مادر استخوان", "regen"),
    ("Vasto Lorde Wraith", "شبح واستو لورد", "regen"), ("Sand Leviathan", "لویاتان شنی", None),
    ("Grimmjow", "گریمجو", "enrage"), ("Nnoitra", "نوایترا", "armor"), ("Nightmare Aspect", "چهره‌ی کابوس", "dodge"),
    ("Ulquiorra", "اولکیورا", "dodge"), ("Starrk", "استارک", "regen"), ("Baraggan", "باراگان", "decay"),
    ("Fallen Captain", "کاپیتان سقوط‌کرده", None), ("Traitor Captain", "کاپیتان خائن", None),
    ("Iron Sentinel", "نگهبان آهنین", "armor"), ("Storm Warden", "نگهبان توفان", None),
    ("Glacier Tyrant", "ستمگر یخچالی", None), ("Ember Sovereign", "فرمانروای شرر", "burn"),
    ("Venom Queen", "ملکه‌ی زهر", "poison"), ("Sternritter Elite", "استرنریتر نخبه", None),
    ("Star Cross Knight", "شوالیه‌ی ستاره", None), ("Holy Archer", "کمان‌دار مقدس", None),
    ("Zaraki", "زارکی", "enrage"), ("Shadow Arbiter", "داور سایه", "dodge"),
    ("Mirror Sovereign", "فرمانروای آینه", "illusion"), ("Aizen", "آیزن", "illusion"),
    ("Gin", "گین", "dodge"), ("Void Gardener", "باغبان خلأ", None), ("Abyss Maw", "آروغ ورطه", None),
    ("Yammy-class Titan", "تایتان کلاس یامی", None), ("Soul Reaper Exile", "تبعیدی شینیگامی", None),
    ("Tide Calamity", "فاجعه‌ی جزر", None), ("Thunder Oracle", "پیشگوی تندر", None),
    ("Eclipse Herald", "منادی خسوف", None), ("Palace Gatekeeper", "دروازه‌بان کاخ", None),
    ("Royal Guard Captain", "فرمانده‌ی گارد سلطنتی", None), ("Yamamoto", "یاماموتو", "burn"),
    ("Dangai Devourer", "بلعنده‌ی دنگای", None), ("Origin Echo", "پژواک آغاز", None),
    ("Jugram", "جوگرام", "armor"), ("Yhwach", "یوهابخ", "dodge"), ("Reishi Tyrant", "ستمگر ریشی", None),
    ("Soul King's Shade", "سایه‌ی شاه ارواح", None), ("Calamity Apex", "اوج فاجعه", "enrage"),
]

# one-line epithets shown under each boss name: name_en -> (fa, en)
EPITHET = {
    "Wandering Hollow": ("گرسنه و بی‌مقصد؛ هر ردپا برایش بوی شام می‌دهد.", "Hungry and aimless; every footprint smells like dinner."),
    "Hollow Brute": ("نه فکر، نه ترس؛ فقط مشت.", "No thought, no fear. Only fists."),
    "Cursed Blade Spirit": ("تیغی که صاحبش را بلعید و حالا دنبال تازه‌ای می‌گردد.", "A blade that swallowed its wielder and now seeks another."),
    "Grand Fisher": ("طعمه‌اش بالای سرِ خودش آویزان است؛ فریب نخور.", "The lure hangs from its own head. Don't be fooled."),
    "Rift Crawler": ("از شکاف می‌خزد و شکاف پشت سرش بسته نمی‌شود.", "It crawls from the rift, and the rift stays open behind it."),
    "Menos Grande": ("سایه‌اش مثل برجی روی تو افتاده است.", "Its shadow falls over you like a tower."),
    "Gillian Colossus": ("صدها روح در یک بدن؛ همه فریاد می‌زنند.", "Hundreds of souls in one body, all screaming."),
    "Crimson Moon Beast": ("وقتی ماه سرخ بتابد، آرام نمی‌گیرد.", "When the crimson moon rises, it will not be calmed."),
    "Adjuchas Stalker": ("کوچک‌تر از گیلیان و هزار بار خطرناک‌تر.", "Smaller than a Gillian, a thousand times deadlier."),
    "Bone Matriarch": ("مادرِ هر استخوانی که در بیابان مانده.", "Mother of every bone left in the desert."),
    "Vasto Lorde Wraith": ("اوج هالوها؛ شبحی با شکل انسان.", "The peak of Hollows, a wraith in human shape."),
    "Sand Leviathan": ("زیر شن می‌خوابد. صبر دارد.", "It sleeps beneath the sand. It is patient."),
    "Grimmjow": ("پلنگی که قفس نمی‌شناسد.", "A panther that knows no cage."),
    "Nnoitra": ("می‌خندد؛ و این بدترین نشانه است.", "He laughs, and that is the worst sign."),
    "Nightmare Aspect": ("کابوسی که بیدار هم دنبالت می‌کند.", "A nightmare that follows you even awake."),
    "Ulquiorra": ("ساکت، سرد و بی‌ترس؛ همه‌چیز برایش بی‌معناست.", "Silent, cold and unafraid; to him everything is meaningless."),
    "Starrk": ("تنبل‌ترین و تنهاترین اسپادا؛ و شاید قوی‌ترین.", "The laziest, loneliest Espada, and perhaps the strongest."),
    "Baraggan": ("پادشاهی پوسیده؛ هرچه لمس کند فرسوده می‌شود.", "A rotting king; whatever he touches withers."),
    "Fallen Captain": ("هائوری‌اش هنوز سفید است؛ دلش نه.", "His haori is still white. His heart is not."),
    "Traitor Captain": ("خیانتش از پشت نبود؛ از رو‌به‌رو بود، با لبخند.", "His betrayal did not come from behind, but from the front, smiling."),
    "Iron Sentinel": ("نمی‌خوابد، نمی‌پرسد، عقب نمی‌نشیند.", "It does not sleep, ask, or retreat."),
    "Storm Warden": ("توفان فرمانبر اوست.", "The storm obeys him."),
    "Glacier Tyrant": ("هر نفسش یک زمستان است.", "Every breath of his is a winter."),
    "Ember Sovereign": ("شعله‌ای که تاج بر سر گذاشته.", "A flame that wears a crown."),
    "Venom Queen": ("بوسه‌اش آخرین چیزی است که حس می‌کنی.", "Her kiss is the last thing you feel."),
    "Sternritter Elite": ("ستاره‌ای بر شانه، مرگی در کمان.", "A star on his shoulder, death in his bow."),
    "Star Cross Knight": ("صلیبش نور است و نورش حکم.", "His cross is light, and his light is judgment."),
    "Holy Archer": ("تیرش پیش از صدایش می‌رسد.", "His arrow arrives before its sound."),
    "Zaraki": ("هر نبرد را مثل آخرین جشنِ عمرش می‌خواهد.", "He wants every fight to be the last feast of his life."),
    "Shadow Arbiter": ("در سایه‌ها قضاوت می‌کند، بی‌رحم و بی‌اپیل.", "He judges in shadow, merciless and beyond appeal."),
    "Mirror Sovereign": ("آنچه می‌بینی، آنچه هست نیست.", "What you see is not what is."),
    "Aizen": ("همه‌چیز طبق نقشه‌ی اوست؛ حتی نبرد تو.", "Everything follows his plan, even your battle."),
    "Gin": ("همیشه لبخند؛ هرگز نمی‌دانی تیغ کجاست.", "Always smiling; you never know where the blade is."),
    "Void Gardener": ("در خلأ، گل‌هایی از ریاتسو می‌کارد.", "In the void, he plants flowers of reiatsu."),
    "Abyss Maw": ("دهانی که سیری نمی‌شناسد.", "A maw that knows no fullness."),
    "Yammy-class Titan": ("عظیم، بلند‌قامت، و بی‌حوصله.", "Colossal, towering, and impatient."),
    "Soul Reaper Exile": ("تبعیدی‌ای که هنوز شیهاکوشو‌اش را نگه داشته.", "An exile who still keeps his shihakushō."),
    "Tide Calamity": ("موجی که نامش فاجعه است.", "A wave whose name is calamity."),
    "Thunder Oracle": ("پیش از آنکه برق بزند، آینده را می‌داند.", "He knows the future before the lightning strikes."),
    "Eclipse Herald": ("نشانه‌ی تاریکی؛ ماه را می‌بلعد.", "Herald of the dark; he swallows the moon."),
    "Palace Gatekeeper": ("دروازه تا او نخواهد باز نمی‌شود.", "The gate does not open until he wills it."),
    "Royal Guard Captain": ("تیغش را فقط برای شاه می‌کشد؛ امشب برای تو.", "He draws his blade only for the king. Tonight, for you."),
    "Yamamoto": ("آتشی هزارساله؛ پیرمردی که جهان را می‌سوزاند.", "A thousand-year flame; an old man who burns the world."),
    "Dangai Devourer": ("راه میان جهان‌ها را می‌بلعد.", "He devours the road between worlds."),
    "Origin Echo": ("پژواک آغازِ همه‌چیز، پیش از نام.", "The echo of the beginning, before names."),
    "Jugram": ("تعادلی که با هر ضربه به سود او می‌چرخد.", "A balance that tips in his favor with every blow."),
    "Yhwach": ("نخستین پدر؛ ریاتسوی ارواح در رگ‌هایش جاری است.", "The first father; the reiatsu of souls runs in his veins."),
    "Reishi Tyrant": ("ذره‌های هوا فرمانبر اویند.", "The very motes of air obey him."),
    "Soul King's Shade": ("سایه‌ی آنکه جهان را نگه داشته است.", "The shade of the one who holds the world."),
    "Calamity Apex": ("پایان، با نامی دیگر.", "The end, under another name."),
}


def _build():
    out = []
    for i, (en, fa, trait) in enumerate(_NAMES):
        lvl = 3 + int(i * 2.2)
        out.append({"_id": f"boss_{i + 1:02d}", "boss_id": f"boss_{i + 1:02d}", "name_en": en, "name_fa": fa,
                    "level": lvl, "hp": int((2.2 * lvl + 15) * 120 * (1 + lvl / 60)), "attack": 20 + lvl * 7,
                    "defense": 2 + lvl * 1.1, "trait": trait,
                    "epi_fa": EPITHET[en][0], "epi_en": EPITHET[en][1]})
    return out


BOSSES = _build()
BOSS_BY_ID = {b["_id"]: b for b in BOSSES}
