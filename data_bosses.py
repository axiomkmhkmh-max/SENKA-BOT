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


# ---- Bleach content pack 2: extra world bosses (appended ids; level is explicit, same stat formulas) ----
# (name_en, name_fa, trait, level, epithet fa, epithet en)
_EXTRA = [
    ("Zommari Rureaux", "زومّاری رورو", "dodge", 33, "سرعتش از سایه‌ی خودش جلوتر است.", "His speed outruns his own shadow."),
    ("Aaroniero Arruruerie", "آرونیرو آرورِری", "illusion", 36, "هزار صدا در یک گلو؛ کدامشان واقعی است؟", "A thousand voices in one throat; which one is real?"),
    ("Szayelaporro Granz", "سزایل‌آپورو گرانز", "poison", 38, "دانشمندی که هر حریف را نمونه‌ی آزمایشگاه می‌بیند.", "A scientist who sees every rival as a specimen."),
    ("Kaname Tosen", "کانامه توسن", None, 42, "عدالتی که چشم ندارد، اما می‌بیند.", "A justice with no eyes that still sees."),
    ("Mayuri Kurotsuchi", "مایوری کوروتسوچی", "poison", 46, "هر زخم برایش یک یادداشت پژوهشی است.", "To him, every wound is a research note."),
    ("Tier Harribel", "تیر هریبل", None, 54, "آرام و نجیب؛ دریایی در تیغش می‌خروشد.", "Calm and noble; a sea roars in her blade."),
    ("Byakuya Kuchiki", "بیاکویا کوچیکی", "bleed", 58, "غرور، قانون و هزار تیغه‌ی گلبرگ.", "Pride, law and a thousand petal-blades."),
    ("Shukuro Tsukishima", "شوکورو تسوکیشیما", "illusion", 62, "گذشته‌ات را می‌برد و خاطره‌ی خودش را جایش می‌گذارد.", "He cuts your past and leaves his own memory in its place."),
    ("Gremmy Thoumeaux", "گرمی تومو", "illusion", 74, "هر چه در خیالش باشد واقعی می‌شود.", "Whatever he imagines becomes real."),
    ("Retsu Unohana", "رتسو اونوهانا", "regen", 78, "لبخندش مهربان‌ترین هشدار جهان است.", "Her smile is the gentlest warning in the worlds."),
    ("Hollow Ichigo", "ایچیگوی هالو", "enrage", 88, "سفید، خندان و گرسنه؛ پاسخگوی هیچ‌کس نیست.", "White, grinning, hungry; answerable to no one."),
]


def _build_extra(start):
    out = []
    for j, (en, fa, trait, lvl, e_fa, e_en) in enumerate(_EXTRA):
        bid = f"boss_{start + j:02d}"
        out.append({"_id": bid, "boss_id": bid, "name_en": en, "name_fa": fa, "level": lvl,
                    "hp": int((2.2 * lvl + 15) * 120 * (1 + lvl / 60)), "attack": 20 + lvl * 7, "defense": 2 + lvl * 1.1,
                    "trait": trait, "epi_fa": e_fa, "epi_en": e_en})
    return out


# ---- Bleach content pack 3: 12 more world bosses (boss_62..boss_73, traits are the existing ones) ----
_EXTRA3 = [
    ("Ikkaku Madarame", "ایککاکو مادارامه", "enrage", 24, "می‌خندد؛ جنگ برایش یک جشن کوچک است.", "He laughs; to him a fight is a small festival."),
    ("Renji Abarai", "رنجی آبارای", "bleed", 29, "تیغه‌اش بند‌بند می‌شود و هر بندش دندان دارد.", "His blade splits into joints, and each joint has teeth."),
    ("Rukia Kuchiki", "روکیا کوچیکی", None, 34, "سفید، سرد و آرام؛ مثل برف پیش از طوفان.", "White, cold and calm, like snow before a storm."),
    ("Nelliel Tu Odelschwanck", "نلیل تو اودلشوانک", "dodge", 44, "یاد گرفته چگونه از ضربه جا بخالی؛ و چگونه برگردد.", "She has learned to slip a blow, and to come back."),
    ("Sajin Komamura", "ساجین کوماموتو", "armor", 48, "غولی از زره و وفاداری.", "A giant of armor and loyalty."),
    ("Toshiro Hitsugaya", "توشیرو هیتسوگایا", None, 52, "کوچک‌ترین کاپیتان؛ سردترین نگاه.", "The smallest captain; the coldest gaze."),
    ("Yoruichi Shihoin", "یورویچی شیهوئین", "dodge", 57, "پیش از آنکه ببینی‌اش، رفته است.", "She is gone before you see her."),
    ("Kisuke Urahara", "کیسوکه اوراهارا", "illusion", 63, "پشت بادبزن لبخند می‌زند؛ و هر ضربه‌اش از قبل حساب شده.", "He smiles behind a fan; every blow is calculated in advance."),
    ("Jushiro Ukitake", "جوشیرو اوکیتاکه", "burn", 68, "نجیب و مریض؛ ولی شعله‌اش را از هیچ‌کس قرض نمی‌گیرد.", "Noble and frail, yet he borrows his flame from no one."),
    ("Shunsui Kyoraku", "شونسویی کیوراکو", "dodge", 72, "بازی می‌کند؛ و قواعد بازی را او می‌نویسد.", "He plays, and he writes the rules of the game."),
    ("Ichibe Hyosube", "ایچیبه هیوسوبه", "decay", 84, "نامی که بگیرد، دیگر مال تو نیست.", "A name he takes is no longer yours."),
    ("Ichigo Kurosaki", "ایچیگو کوروساکی", "enrage", 96, "تیغه‌اش سیاه است و تنها دلیلش، کسانی‌اند که پشت اویند.", "His blade is black and his only reason is those behind him."),
]


def _build_extra3(start):
    out = []
    for j, (en, fa, trait, lvl, e_fa, e_en) in enumerate(_EXTRA3):
        bid = f"boss_{start + j:02d}"
        out.append({"_id": bid, "boss_id": bid, "name_en": en, "name_fa": fa, "level": lvl,
                    "hp": int((2.2 * lvl + 15) * 120 * (1 + lvl / 60)), "attack": 20 + lvl * 7, "defense": 2 + lvl * 1.1,
                    "trait": trait, "epi_fa": e_fa, "epi_en": e_en})
    return out



# ---- Bleach content pack 4: 13 more world bosses (boss_74..boss_86) ----
_EXTRA4 = [
    ("Shuhei Hisagi", "شوهی هیساگی", "bleed", 27, "شمشیرش را روی خاطره تیز می‌کند.", "He sharpens his sword on memory."),
    ("Hiyori Sarugaki", "هیوری ساروگاکی", "enrage", 30, "کوچک است، ولی خشمش از قدش بلندتر است.", "She is small, but her rage stands taller than she does."),
    ("Rangiku Matsumoto", "رانگیکو ماتسوموتو", "decay", 37, "خاکستری که می‌رقصد و هرچه لمس کند، می‌پوسد.", "Ash that dances and withers whatever it touches."),
    ("Yasutora Sado", "یاسوتورا سادو", "armor", 40, "دیواری که مشت می‌زند.", "A wall that throws punches."),
    ("Soi Fon", "سوی فون", "dodge", 41, "سریع‌ترین نیش؛ و بی‌ترین فاصله.", "The fastest sting at the shortest distance."),
    ("Kensei Muguruma", "کنسی موگوروما", "bleed", 45, "مشت و تیغ، یک ضربه.", "Fist and blade, one blow."),
    ("Uryu Ishida", "اوریو ایشیدا", None, 50, "غرور کوئینسی؛ و تیری که خطا نمی‌کند.", "A Quincy's pride and an arrow that does not miss."),
    ("Kugo Ginjo", "کوگو گینجو", "regen", 60, "رهبری که هرگز تنها نمی‌ماند.", "A leader who is never left alone."),
    ("Shinji Hirako", "شینجی هیراکو", "illusion", 66, "همه‌چیز وارونه می‌شود، مثل تیغه‌اش.", "Everything turns upside down, like his blade."),
    ("Bambietta Basterbine", "بامبیتا باستربین", "burn", 70, "هر چیزی را که لمس کند، منفجر می‌کند.", "Whatever she touches, she detonates."),
    ("Askin Nakk Le Vaar", "اسکین ناک لو وار", "poison", 76, "مرگ را هم قابل مذاکره می‌کند.", "He makes even death negotiable."),
    ("Gerard Valkyrie", "جرارد والکیری", "regen", 80, "معجزه‌ای که زخم‌ها را پس می‌زند.", "A miracle that turns wounds back."),
    ("Isshin Shiba", "ایشین شیبا", "burn", 86, "پدری که هنوز می‌تواند جهان را بسوزاند.", "A father who can still burn the world."),
]


def _build_extra4(start):
    out = []
    for j, (en, fa, trait, lvl, e_fa, e_en) in enumerate(_EXTRA4):
        bid = f"boss_{start + j:02d}"
        out.append({"_id": bid, "boss_id": bid, "name_en": en, "name_fa": fa, "level": lvl,
                    "hp": int((2.2 * lvl + 15) * 120 * (1 + lvl / 60)), "attack": 20 + lvl * 7, "defense": 2 + lvl * 1.1,
                    "trait": trait, "epi_fa": e_fa, "epi_en": e_en})
    return out


# ---- Bleach content pack 5: 12 more world bosses (boss_87..boss_98, traits are the existing ones) ----
_EXTRA5 = [
    ("Kon", "کن", "dodge", 4, "کوچک، پشمالو و پر از ادعا؛ فقط یک چیز را خوب بلد است: فرار.", "Small, fluffy and full of claims; he knows exactly one thing well: running."),
    ("Jinta Hanakari", "جینتا هاناکاری", "enrage", 12, "پسری با گرز آهنی؛ هر باخت برایش یک توهین شخصی است.", "A boy with an iron club; every loss is a personal insult."),
    ("Kaien Shiba", "کاین شیبا", "bleed", 21, "سوگندی که یک شب شکست و هنوز در تیغه می‌چرخد.", "An oath broken in one night, still circling in the blade."),
    ("Giriko Kutsuzawa", "گیریکو کوتسوزاوا", "dodge", 26, "هر ثانیه‌ی تو برایش یک سکه است؛ و او خوب حساب می‌کند.", "Every second of yours is a coin to him, and he counts well."),
    ("Momo Hinamori", "مومو هیناموری", "burn", 31, "شعله‌ای که روزی از ایمان می‌آمد و حالا از بی‌اعتمادی.", "A flame that once came from faith and now comes from distrust."),
    ("Izuru Kira", "ایزورو کیرا", "decay", 35, "هر ضربه‌اش سنگینی را بیشتر می‌کند، تا زانو بزنی.", "Each of his blows adds weight until you kneel."),
    ("Yammy Llargo", "یامی لارگو", "armor", 39, "قدرتش از شماره‌اش نیست؛ از خشمی است که هیچ‌وقت خاموش نشد.", "His strength is not his number but a wrath that never went out."),
    ("Nemu Kurotsuchi", "نمو کوروتسوچی", "poison", 43, "بی‌صدا فرمان می‌برد، با زهری که در رگ دارد و خودش انتخابش نکرده.", "She obeys in silence, with a poison in her veins she never chose."),
    ("Wonderweiss Margela", "واندروایس مارگلا", "enrage", 56, "کودکی که کلمه نمی‌داند؛ فریادش پر است از آنچه هیچ‌کس نگفت.", "A child with no words, whose cry is full of what no one said."),
    ("Kirio Hikifune", "کیریو هیکیفونه", "regen", 82, "مهربانی‌ای که جهان را بازمی‌سازد، قدم‌به‌قدم و زخم‌به‌زخم.", "A kindness that rebuilds the world, step by step and wound by wound."),
    ("Tenjiro Kirinji", "تنجیرو کیرینجی", "armor", 85, "پیرمردی که کوه‌ها نامش را می‌شناسند؛ عقب‌نشینی را فراموش کرده.", "An old man whom mountains know by name; he has forgotten how to retreat."),
    ("Senjumaru Shutara", "سنجومارو شوتارا", "illusion", 94, "تیغه‌ها را مثل شعر می‌سازد، و تو در سطرهای آخر خوانده می‌شوی.", "She forges blades like verses, and you are read in the last lines."),
]


def _build_extra5(start):
    out = []
    for j, (en, fa, trait, lvl, e_fa, e_en) in enumerate(_EXTRA5):
        bid = f"boss_{start + j:02d}"
        out.append({"_id": bid, "boss_id": bid, "name_en": en, "name_fa": fa, "level": lvl,
                    "hp": int((2.2 * lvl + 15) * 120 * (1 + lvl / 60)), "attack": 20 + lvl * 7, "defense": 2 + lvl * 1.1,
                    "trait": trait, "epi_fa": e_fa, "epi_en": e_en})
    return out


# ---- Bleach villain pack 6: 6 more world bosses (boss_99..boss_104; canon villains not yet in the list, existing traits only) ----
_EXTRA6 = [
    ("Tia Halibel", "تیا هالیبل", "bleed", 60, "موجی که زیر تو پنهان شده؛ آرام است تا لحظه‌ای که دیر شده.", "A wave hidden beneath you; calm until it is too late."),
    ("Cirucci Sanfilippo", "سیرسی سانفیلیپو", "dodge", 52, "می‌خندد، می‌رقصد، و تو نمی‌فهمی کدام حرکتش واقعی است.", "She laughs, she dances, and you cannot tell which move is real."),
    ("Kokichi Muramasa", "کوکیچی موراماسا", "bleed", 74, "ذهنی که هر دشمنش را پیش از جنگ شکست داده؛ حتی خودش را.", "A mind that defeats every enemy before the battle, even itself."),
    ("Jin Kariya", "جین کاریا", "decay", 66, "جوان‌ترین شکارچی ارواح است و پیرترین اشتیاق را دارد: قدرت.", "The youngest hunter of souls, with the oldest hunger: power."),
    ("Lilynette Gingerbuck", "لیلینت جینجربک", "enrage", 49, "کوچک‌تر از آن که بترسی، و بیشتر از آن که فراموش کنی.", "Too small to fear, too vivid to forget."),
    ("Gamuza", "گاموزا", "regen", 58, "از خوابی بیدار شد که هیچ‌کس نمی‌خواست تمام شود.", "He woke from a sleep no one wanted to end."),
]


def _build_extra6(start):
    out = []
    for j, (en, fa, trait, lvl, e_fa, e_en) in enumerate(_EXTRA6):
        bid = f"boss_{start + j:02d}"
        out.append({"_id": bid, "boss_id": bid, "name_en": en, "name_fa": fa, "level": lvl,
                    "hp": int((2.2 * lvl + 15) * 120 * (1 + lvl / 60)), "attack": 20 + lvl * 7, "defense": 2 + lvl * 1.1,
                    "trait": trait, "epi_fa": e_fa, "epi_en": e_en})
    return out


BOSSES = _build() + _build_extra(len(_NAMES) + 1)
BOSSES = BOSSES + _build_extra3(len(BOSSES) + 1)
BOSSES = BOSSES + _build_extra4(len(BOSSES) + 1)
BOSSES = BOSSES + _build_extra5(len(BOSSES) + 1)
BOSSES = BOSSES + _build_extra6(len(BOSSES) + 1)
BOSS_BY_ID = {b["_id"]: b for b in BOSSES}
