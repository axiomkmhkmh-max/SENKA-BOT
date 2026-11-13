"""Bleach flavour data: allegiances (Gotei divisions, Espada numbers, Wandenreich orders, Karakura allies),
story-arc quests and extra collectible characters. Pure data, no I/O."""

# faction by race
FACTION_OF = {"shinigami": "gotei", "quincy": "wande", "hollow": "espada", "arrancar": "espada",
              "human": "allies", "fullbringer": "allies", "visored": "allies"}
FACTION_TITLE = {"gotei": ("🏯 جوخه‌ی گوتی ۱۳", "🏯 Gotei 13 Division"), "wande": ("✝️ فرمان وندن‌رایش", "✝️ Wandenreich Order"),
                 "espada": ("💀 مقام اسپادا", "💀 Espada Number"), "allies": ("🌸 یاران کاراکورا", "🌸 Karakura Allies")}


def _d(i, faction, icon, fa, en, bonus, dfa, den):
    return {"_id": i, "faction": faction, "icon": icon, "fa": fa, "en": en, "bonus": bonus, "desc_fa": dfa, "desc_en": den}


DIVISIONS = [
    # ---- Gotei 13 -----------------------------------------------------------------------------------
    _d("g01", "gotei", "🔥", "جوخه‌ی ۱", "1st Division", {"dmg": 0.05, "def": 0.02}, "قدرت خالص و انضباط فرمانده‌کل.", "Raw power and the Captain-Commander's discipline."),
    _d("g02", "gotei", "🥷", "جوخه‌ی ۲ (نیروی مخفی)", "2nd Division (Stealth Force)", {"crit": 0.05, "patrol": 0.05}, "سریع، بی‌صدا، کشنده.", "Fast, silent, lethal."),
    _d("g03", "gotei", "🪙", "جوخه‌ی ۳", "3rd Division", {"coin": 0.05, "patrol": 0.03}, "همیشه یک قدم جلوتر از نقشه.", "Always a step ahead of the map."),
    _d("g04", "gotei", "💚", "جوخه‌ی ۴ (امداد)", "4th Division (Relief)", {"regen": 0.08, "def": 0.03}, "تیغ‌شان زخم می‌بندد.", "Their blades mend wounds."),
    _d("g05", "gotei", "🕯️", "جوخه‌ی ۵", "5th Division", {"calm": 0.15, "def": 0.03}, "آرامشی که تهدید جهان را فرو می‌نشاند.", "A calm that soothes the world's threat."),
    _d("g06", "gotei", "🌸", "جوخه‌ی ۶", "6th Division", {"def": 0.06, "dmg": 0.02}, "نجابت و قانون، دیواری از گلبرگ.", "Nobility and law, a wall of petals."),
    _d("g07", "gotei", "📖", "جوخه‌ی ۷", "7th Division", {"xp": 0.04, "coin": 0.02}, "درس‌هایی که با هر نبرد بیشتر می‌شود.", "Lessons that grow with every fight."),
    _d("g08", "gotei", "🍶", "جوخه‌ی ۸", "8th Division", {"drop": 0.05, "xp": 0.02}, "شانس با آدم‌های بی‌خیال مهربان‌تر است.", "Luck favours the carefree."),
    _d("g09", "gotei", "📰", "جوخه‌ی ۹", "9th Division", {"patrol": 0.05, "xp": 0.03}, "هر کوچه‌ای را می‌شناسند.", "They know every back alley."),
    _d("g10", "gotei", "❄️", "جوخه‌ی ۱۰", "10th Division", {"calm": 0.20, "dmg": 0.02}, "سرما، سکوت و تمرکز.", "Cold, silence and focus."),
    _d("g11", "gotei", "⚔️", "جوخه‌ی ۱۱", "11th Division", {"dmg": 0.07, "crit": 0.02}, "فقط یک قانون: بجنگ.", "One rule only: fight."),
    _d("g12", "gotei", "🧪", "جوخه‌ی ۱۲ (پژوهش)", "12th Division (Research)", {"drop": 0.07, "coin": 0.02}, "هر شکستی یک نمونه است.", "Every defeat is a specimen."),
    _d("g13", "gotei", "🌿", "جوخه‌ی ۱۳", "13th Division", {"regen": 0.05, "xp": 0.04}, "امید آرام، رشد پایدار.", "Quiet hope, steady growth."),
    # ---- Espada (hollow / arrancar) -------------------------------------------------------------------
    _d("e01", "espada", "🐺", "پریمرا — تنهایی", "Primera — Solitude", {"dmg": 0.04, "regen": 0.06}, "قدرتی که از تنهایی می‌آید.", "Strength born of solitude."),
    _d("e02", "espada", "⏳", "سگوندا — پوسیدگی", "Segunda — Decay", {"xp": 0.05, "def": 0.03}, "زمان با تو متحد است.", "Time is on your side."),
    _d("e03", "espada", "🌊", "ترسرا — قربانی", "Tercera — Sacrifice", {"def": 0.06, "regen": 0.04}, "سپری برای یارانت.", "A shield for your comrades."),
    _d("e04", "espada", "🦇", "کوارتا — ناامیدی", "Cuarta — Despair", {"crit": 0.05, "dmg": 0.03}, "سکوتی سرد پیش از ضربه.", "A cold silence before the strike."),
    _d("e05", "espada", "🌙", "کوینتا — خشم", "Quinta — Wrath", {"dmg": 0.07}, "خشم بی‌مهار.", "Unbridled wrath."),
    _d("e06", "espada", "🐆", "سکستا — تخریب", "Sexta — Destruction", {"dmg": 0.05, "crit": 0.03}, "پنجه‌ای که هر چیز را می‌شکند.", "Claws that break everything."),
    _d("e07", "espada", "🎴", "سپتیما — شکار", "Septima — Hunt", {"patrol": 0.06, "drop": 0.03}, "ردیابی که هرگز گم نمی‌کند.", "A tracker that never loses the trail."),
    _d("e08", "espada", "🧬", "اوکتاوا — جنون", "Octava — Madness", {"drop": 0.06, "xp": 0.03}, "دانشی که از جنون زاده شد.", "Knowledge born of madness."),
    _d("e09", "espada", "🪞", "نوودا — طمع", "Novena — Greed", {"coin": 0.06, "xp": 0.02}, "هر چه ببلعی، مال توست.", "Whatever you devour is yours."),
    _d("e10", "espada", "💪", "دسیما — خشونت", "Decima — Brutality", {"def": 0.05, "dmg": 0.04}, "قدرت بدنی بی‌رحم.", "Ruthless physical might."),
    # ---- Wandenreich ----------------------------------------------------------------------------------
    _d("w01", "wande", "🏹", "کمان‌داران هایلیگ", "Heilig Archers", {"crit": 0.05, "dmg": 0.04}, "هر تیر، یک تصمیم.", "Every arrow is a decision."),
    _d("w02", "wande", "🛡️", "شوتس‌شتافل (نگهبان)", "Schutzstaffel (Guard)", {"def": 0.07, "calm": 0.10}, "نگهبانان بی‌چهره‌ی امپراتور.", "The faceless guardians of the Emperor."),
    _d("w03", "wande", "⭐", "پیشتازان ستاره", "Sternritter Vanguard", {"dmg": 0.06, "xp": 0.02}, "هر ستاره، یک توانایی منحصر.", "Every star, a unique power."),
    _d("w04", "wande", "📜", "پژوهشگران خون", "Blut Scholars", {"xp": 0.05, "drop": 0.03}, "خون یادگار است؛ بخوان.", "Blood is memory; read it."),
    # ---- Karakura allies ----------------------------------------------------------------------------------
    _d("a01", "allies", "🎩", "فروشگاه اوراهارا", "Urahara Shop", {"drop": 0.06, "coin": 0.03}, "هر چیزی بهایی دارد.", "Everything has a price."),
    _d("a02", "allies", "🎭", "ویزوردها", "Visored Warehouse", {"dmg": 0.04, "crit": 0.04}, "نیمی انسان، نیمی هالو؛ تمام‌وقت جنگجو.", "Half soul, half hollow, all fighter."),
    _d("a03", "allies", "🔗", "کراس‌زنده (فول‌برینگ)", "Fullbring Circle", {"xp": 0.04, "regen": 0.04}, "پیوند با چیزهایی که دوستشان داری.", "A bond with the things you love."),
    _d("a04", "allies", "🍃", "یاران کاراکورا", "Karakura Gang", {"def": 0.04, "xp": 0.04, "coin": 0.02}, "قدرت دوستی واقعی است.", "The power of friendship is real."),
    # ---- content pack 2: more organisations (same total power as the others) ----
    _d("g14", "gotei", "🔮", "سپاه کیدو", "Kidō Corps", {"crit": 0.04, "xp": 0.03}, "کلمات درست، در لحظه‌ی درست.", "The right words at the right moment."),
    _d("g15", "gotei", "🎆", "خاندان شیبا", "Shiba Clan", {"dmg": 0.04, "drop": 0.03}, "آتشی که جشن می‌گیرد و می‌سوزاند.", "Fire that celebrates and burns."),
    _d("g16", "gotei", "🏛️", "گارد سلطنتی", "Royal Guard", {"dmg": 0.04, "xp": 0.03}, "وزن جهان بر شانه‌هایشان است.", "The weight of the world rests on their shoulders."),
    _d("e11", "espada", "🕳️", "اسپادای فروافتاده", "Privaron Espada", {"dmg": 0.05, "def": 0.02}, "تاج افتاد؛ غرور نه.", "The crown fell; the pride did not."),
    _d("e12", "espada", "🔢", "نومروس", "Números", {"coin": 0.04, "xp": 0.03}, "شماره‌ای برای هر جنگجو و راهی برای بالا رفتن.", "A number for every fighter, and a way up the ranks."),
    _d("e13", "espada", "🐾", "فراسیون‌های اسپادا", "Espada Fracción", {"regen": 0.04, "def": 0.03}, "وفاداری پشت سایه‌ی ارباب.", "Loyalty behind the master's shadow."),
    _d("w05", "wande", "🌙", "بازماندگان کوئینسی", "Quincy Remnants", {"def": 0.04, "crit": 0.03}, "ستاره‌ای که از خاموشی بازگشت.", "A star that returned from the dark."),
    _d("a05", "allies", "🏥", "کلینیک کوروساکی", "Kurosaki Clinic", {"regen": 0.06, "def": 0.03}, "درمان در اتاق انتظار، نبرد در کوچه.", "Healing in the waiting room, battle in the alley."),
    _d("a06", "allies", "🩸", "شینیگامی جانشین", "Substitute Soul Reapers", {"dmg": 0.04, "xp": 0.03}, "قدرتی قرضی که مال خودت شد.", "Borrowed power that became your own."),
]
DIV_BY_ID = {d["_id"]: d for d in DIVISIONS}


def divisions_for(race: str) -> list:
    f = FACTION_OF.get(race, "allies")
    return [d for d in DIVISIONS if d["faction"] == f]


def division_bonus(ch: dict) -> dict:
    d = DIV_BY_ID.get(ch.get("division") or "")
    return {k: v for k, v in (d or {}).get("bonus", {}).items() if v > 0}


# ---- story arcs: main-line quests (goal, count, xp, coins, min level, fa, en, desc_fa, desc_en) -----------------
ARC_QUESTS = [
    ("arc1_a", "explore", 15, 500, 400, 1, "قدم در راه جانشین", "Path of the Substitute",
     "پا به دنیایی بگذار که ارواح در آن راه گم می‌کنند.", "Step into a world where souls lose their way."),
    ("arc1_b", "battle_win", 15, 900, 700, 5, "نخستین هالو", "The First Hollow",
     "با هالوها روبه‌رو شو و ثابت کن شایسته‌ی تیغه‌ای.", "Face the Hollows and prove you deserve a blade."),
    ("arc2_a", "level", 15, 1500, 1200, 5, "نجات از اعدام", "Rescue from the Execution",
     "به سیرایتی برو؛ سطح ۱۵ نخستین دروازه را باز می‌کند.", "Head into Seireitei: level 15 opens the first gate."),
    ("arc2_b", "dungeon_clear", 3, 2500, 2000, 10, "نفوذ به سیرایتی", "Break Into Seireitei",
     "سه دانجن را پاک کن تا راهت را باز کنی.", "Clear three dungeons to carve your way in."),
    ("arc3_a", "level", 30, 4000, 3000, 20, "شب هوئکو موندو", "Night of Hueco Mundo",
     "سطح ۳۰: ماه بی‌رحم هوئکو موندو منتظر است.", "Level 30: the merciless moon of Hueco Mundo waits."),
    ("arc3_b", "boss_hit", 40, 5000, 4000, 20, "نبرد برای اینوئه", "Battle for the Captive",
     "به باس جهانی ضربه بزن؛ یاران گرفتار منتظرند.", "Strike the world boss; captive friends are waiting."),
    ("arc4_a", "level", 45, 7000, 5500, 30, "جنگ زمستانی", "The Winter War",
     "سطح ۴۵: جنگ برای کاراکورا آغاز شده.", "Level 45: the war for Karakura has begun."),
    ("arc4_b", "pvp_win", 10, 6000, 5000, 15, "تیغ‌ها روبه‌روی هم", "Blades Face to Face",
     "ده دوئل ببر؛ جنگجو در دوئل شناخته می‌شود.", "Win ten duels; a warrior is known by his duels."),
    ("arc5_a", "dungeon_clear", 10, 9000, 7000, 40, "راه کاخ سلطنتی", "Road to the Royal Palace",
     "ده دانجن؛ راه ستاره‌ها هموار می‌شود.", "Ten dungeons: the road of stars opens."),
    ("arc5_b", "level", 60, 12000, 9000, 50, "جنگ هزارساله‌ی خون", "Thousand-Year Blood War",
     "سطح ۶۰: ارتش وندن‌رایش از سایه بیرون می‌آید.", "Level 60: the Wandenreich army steps out of the shadows."),
    ("arc6_a", "boss_kill", 15, 15000, 12000, 60, "قاتل پادشاهان", "Slayer of Kings",
     "پانزده باس را شکست بده.", "Defeat fifteen bosses."),
    ("arc6_b", "level", 90, 30000, 25000, 80, "فراتر از پادشاه روح", "Beyond the Soul King",
     "سطح ۹۰: آخرین دیوار فرو می‌ریزد.", "Level 90: the last wall falls."),
]

# ---- extra gacha characters (appended, so existing ids never change): (en, fa, rarity, role) -------------------
EXTRA_CHARS = [
    ("Hanataro Yamada", "هاناتارو یامادا", "Common", "support"), ("Nanao Ise", "نانائو ایسه", "Common", "support"),
    ("Chojiro Sasakibe", "چوجیرو ساساکیبه", "Common", "tank"), ("Ganju Shiba", "گانجو شیبا", "Common", "attacker"),
    ("Keigo Asano", "کیگو آسانو", "Common", "support"),
    ("Tatsuki Arisawa", "تاتسوکی آریساوا", "Uncommon", "attacker"), ("Kukaku Shiba", "کوکاکو شیبا", "Uncommon", "caster"),
    ("Hachigen Ushoda", "هاچیگن اوشودا", "Uncommon", "support"), ("Tessai Tsukabishi", "تسای تسوکابیشی", "Uncommon", "tank"),
    ("Mashiro Kuna", "ماشیرو کونا", "Uncommon", "attacker"), ("Kensei Muguruma", "کنسی موگوروما", "Uncommon", "attacker"),
    ("Lisa Yadomaru", "لیزا یادومارو", "Uncommon", "caster"), ("Love Aikawa", "لاو آیکاوا", "Uncommon", "tank"),
    ("Jinta Hanakari", "جینتا هاناکاری", "Uncommon", "attacker"), ("Ririn", "ریرین", "Uncommon", "support"),
    ("Ryuken Ishida", "ریوکن ایشیدا", "Rare", "caster"), ("Izuru Kira Captain", "ایزورو کیرا (ستوان ارشد)", "Rare", "tank"),
    ("Nnoitra Gilga", "نویترا گیلگا", "Rare", "attacker"), ("Szayelaporro Granz", "سزایل آپورو", "Rare", "caster"),
    ("Zommari Rureaux", "زومّاری", "Rare", "attacker"), ("Aaroniero Arruruerie", "آرونیرو", "Rare", "caster"),
    ("Yammy Llargo", "یامی لارگو", "Rare", "tank"), ("Dordoni Alessandro", "دوردونی", "Rare", "attacker"),
    ("Bazz-B", "بَز‌بی", "Rare", "attacker"), ("Candice Catnipp", "کندیس", "Rare", "caster"),
    ("Giriko Kutsuzawa", "گیریکو کوتسوزاوا", "Rare", "attacker"), ("Kugo Ginjo", "کوگو گینجو", "Epic", "attacker"),
    ("Shukuro Tsukishima", "شوکورو تسوکیشیما", "Epic", "caster"), ("Retsu Unohana", "رتسو اونوهانا", "Epic", "support"),
    ("Marechiyo Omaeda", "ماره‌چیو اوماِدا", "Rare", "tank"), ("Barragan Louisenbairn", "باراگان", "Epic", "tank"),
    ("Lille Barro", "لیله بارو", "Epic", "caster"), ("Gerard Valkyrie", "جرارد والکیری", "Epic", "attacker"),
    ("Askin Nakk Le Vaar", "اسکین ناک لو وار", "Epic", "support"), ("Bambietta Basterbine", "بامبیتا", "Epic", "caster"),
    ("Ichibe Hyosube", "ایچیبه هیوسوبه", "Legendary", "caster"), ("Masaki Kurosaki", "ماساکی کوروساکی", "Legendary", "support"),
    ("Isshin Shiba", "ایشین شیبا", "Legendary", "attacker"), ("Zangetsu", "زانگتسو (روح تیغه)", "Legendary", "attacker"),
    ("Hollow Ichigo", "ایچیگوی هالو", "Legendary", "attacker"),
    ("Soul King", "پادشاه روح", "Mythic", "support"), ("Hogyoku", "هوگیوکو", "Mythic", "caster"),
    # ---- content pack 2 (appended last, so every existing ch_xx id stays the same) ----
    ("Kiyone Kotetsu", "کیونه کوتتسو", "Common", "support"), ("Sentaro Kotsubaki", "سنتارو کوتسوباکی", "Common", "attacker"),
    ("Rikichi", "ریکیچی", "Common", "support"), ("Mizuiro Kojima", "میزویرو کوجیما", "Common", "support"),
    ("Don Kanonji", "دون کانونجی", "Common", "caster"), ("Tetsuzaemon Iba", "تتسوزائمون ایبا", "Common", "attacker"),
    ("Jidanbo Ikkanzaka", "جیدانبو ایکانزاکا", "Common", "tank"), ("Lilynette Gingerbuck", "لیلینت جینجرباک", "Common", "caster"),
    ("Pesche Guatiche", "پشه گواتیچه", "Uncommon", "tank"), ("Dondochakka Birstanne", "دوندوچاکا بیرستن", "Uncommon", "tank"),
    ("Apacci", "آپاچی", "Uncommon", "attacker"), ("Mila Rose", "میلا رز", "Uncommon", "attacker"),
    ("Sung-Sun", "سونگ‌سان", "Uncommon", "caster"), ("Findor Carias", "فیندور کاریاس", "Uncommon", "attacker"),
    ("Loly Aivirrne", "لولی آیویرن", "Uncommon", "attacker"), ("Menoly Mallia", "منولی مالیا", "Uncommon", "attacker"),
    ("Ggio Vega", "جیو وگا", "Uncommon", "attacker"),
    ("Yachiru Kusajishi", "یاچیرو کوساجیشی", "Rare", "support"), ("Kaien Shiba", "کاین شیبا", "Rare", "attacker"),
    ("Ginrei Kuchiki", "گینری کوچیکی", "Rare", "tank"), ("Cirucci Sanderwicht", "چیروچی ساندرویشت", "Rare", "caster"),
    ("Di Roy Linker", "دی روی لینکر", "Rare", "attacker"), ("Luppi Antenor", "لوپی آنتنور", "Rare", "caster"),
    ("Nirgge Parduoc", "نیرگ پاردوک", "Rare", "tank"), ("Shawlong Koufang", "شالون کوفانگ", "Rare", "attacker"),
    ("Avirama Redder", "آویراما ردر", "Rare", "attacker"), ("Meninas McAllon", "منیناس مک‌آلون", "Rare", "attacker"),
    ("Liltotto Lamperd", "لیلتوتو لمپرد", "Rare", "attacker"), ("Robert Accutrone", "رابرت آکوترون", "Rare", "tank"),
    ("Jerome Guizbatt", "جروم گیزبات", "Rare", "attacker"),
    ("Gremmy Thoumeaux", "گرمی تومو", "Epic", "caster"), ("Giselle Gewelle", "جیزل گوئله", "Epic", "caster"),
    ("Quilge Opie", "کویلگه اوپی", "Epic", "attacker"), ("As Nodt", "آس نوت", "Epic", "attacker"),
    ("Soken Ishida", "سوکن ایشیدا", "Epic", "caster"),
    ("Oetsu Nimaiya", "اوتسو نیمایا", "Legendary", "attacker"), ("Kirio Hikifune", "کیریو هیکیفونه", "Legendary", "support"),
    ("Senjumaru Shutara", "سنجومارو شوتارا", "Legendary", "caster"), ("Tenjiro Kirinji", "تنجیرو کیرینجی", "Legendary", "tank"),
]
