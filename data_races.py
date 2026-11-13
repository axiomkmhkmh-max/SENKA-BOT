"""Races, evolution paths and world locations (static game data)."""
STATS = ("zanjutsu", "kido", "hakuda", "hoho", "reiatsu")
STAT_ICON = {"zanjutsu": "⚔️", "kido": "🔮", "hakuda": "🛡️", "hoho": "💨", "reiatsu": "✨"}
LEVEL_GATES = [1, 15, 35, 60, 90]


def _r(fa, en, st, home, mods, evo, locked=False):
    return {"name_fa": fa, "name_en": en, "stats": dict(zip(STATS, st)), "home": home,
            "mods": mods, "evo": evo, "locked": locked}


RACES = {
    "shinigami": _r("شینیگامی", "Shinigami", (10, 8, 7, 8, 8), "soul_society", {"dmg": 1.05},
                    [("دانشجو", "Academy Student"), ("عضو رسمی", "Officer Seat"), ("افسر", "Lieutenant Rank"),
                     ("ستوان", "Vice Captain"), ("کاپیتان", "Captain")]),
    "quincy": _r("کوئینسی", "Quincy", (6, 10, 5, 7, 6), "wandenreich", {"pierce": 0.15},
                 [("شاگرد", "Apprentice"), ("کوئینسی", "Quincy"), ("استرنریتر", "Sternritter"),
                  ("استرنریتر نخبه", "Elite Sternritter")]),
    "hollow": _r("هالو", "Hollow", (8, 4, 9, 7, 8), "hueco_mundo", {"hp": 1.10},
                 [("هالو", "Hollow"), ("گیلیان", "Gillian"), ("آجوکاس", "Adjuchas"),
                  ("واستو لورد", "Vasto Lorde"), ("آرانکار", "Arrancar Ascendant")]),
    "arrancar": _r("آرانکار", "Arrancar", (9, 4, 10, 9, 9), "las_noches", {"def": 1.08},
                   [("پایه", "Base Arrancar"), ("فراسیون", "Fracción"), ("کاندیدای اسپادا", "Espada Candidate"),
                    ("اسپادا", "Espada")]),
    "fullbringer": _r("فول‌برینگر", "Fullbringer", (7, 7, 7, 8, 7), "karakura", {"crit": 0.05},
                      [("بیدار", "Awakened"), ("ماهر", "Skilled"), ("استاد", "Master")]),
    "human": _r("انسان / روح", "Human / Soul", (7, 7, 7, 7, 7), "karakura", {"xp": 1.10},
                [("روح سرگردان", "Wandering Soul"), ("روح بیدار", "Awakened Soul"), ("روح قدرتمند", "Potent Soul")]),
    "visored": _r("ویزورد", "Visored", (9, 9, 8, 9, 10), "karakura", {"dmg": 1.03, "def": 1.03, "crit": 0.02},
                  [("هولوفیکیشن", "Hollowfication"), ("ماسک کنترل‌شده", "Controlled Mask"), ("پیشرفته", "Advanced")],
                  locked=True),
}


def race_title(race: str, level: int, lang: str) -> str:
    evo = RACES[race]["evo"]
    n = len(evo)
    idx = 0
    for i, gate in enumerate(LEVEL_GATES[:n]):
        if level >= gate:
            idx = i
    return evo[idx][0 if lang == "fa" else 1]


def soft_stat(value: float) -> float:
    """Soft caps: x1 to 100, x0.8 to 200, x0.5 to 500, x0.3 beyond."""
    v = max(0.0, float(value))
    out = min(v, 100)
    if v > 100:
        out += (min(v, 200) - 100) * 0.8
    if v > 200:
        out += (min(v, 500) - 200) * 0.5
    if v > 500:
        out += (v - 500) * 0.3
    return out


def _l(i, fa, en, lvl, enemies, race=None):
    return {"id": i, "fa": fa, "en": en, "level": lvl, "enemies": enemies, "race": race}


LOCATIONS = {
    "soul_society": _l("soul_society", "سول‌سوسایتی", "Soul Society", 1, [("روح گمشده", "Lost Plus"), ("نگهبان محله", "District Guard"), ("قاچاقچی", "Smuggler")]),
    "seireitei": _l("seireitei", "سیرایتی", "Seireitei", 10, [("سرباز نگهبان", "Patrol Soldier"), ("شبح دیوار", "Wall Wraith"), ("تمرین‌کار", "Sparring Rival")]),
    "rukongai": _l("rukongai", "روکونگای", "Rukongai", 5, [("هالوی ضعیف", "Stray Hollow"), ("راهزن", "Bandit"), ("سایه کوچه", "Alley Shade")]),
    "karakura": _l("karakura", "کاراکورا تاون", "Karakura Town", 8, [("هالوی خیابانی", "Street Hollow"), ("روح کینه‌جو", "Vengeful Spirit"), ("شکارچی نیمه‌شب", "Midnight Stalker")]),
    "hueco_mundo": _l("hueco_mundo", "هوئکو موندو", "Hueco Mundo", 20, [("جیلیان کوچک", "Lesser Gillian"), ("ماسک‌دار صحرا", "Dune Masked"), ("گرگ شنی", "Sand Wolf")], "hollow"),
    "las_noches": _l("las_noches", "لاس‌نوچس", "Las Noches", 35, [("نگهبان کاخ", "Palace Guard"), ("فراسیون", "Fracción Sentinel"), ("سایه اسپادا", "Espada Shade")]),
    "dangai": _l("dangai", "دنگای", "Dangai", 45, [("جریان بی‌قرار", "Restless Current"), ("نگهبان شکاف", "Rift Warden"), ("کوملا", "Kumo Brood")]),
    "wandenreich": _l("wandenreich", "وندن‌رایش", "Wandenreich", 55, [("سرباز مقدس", "Holy Soldier"), ("کمان‌دار", "Bow Adept"), ("ستاره‌دار", "Star Knight")], "quincy"),
    "royal_palace": _l("royal_palace", "کاخ سلطنتی", "Royal Palace", 70, [("نگهبان سلطنتی", "Royal Guard"), ("ارواح باستان", "Ancient Wraith"), ("قاضی سایه", "Shadow Judge")]),
    "soul_king": _l("soul_king", "قلمرو شاه ارواح", "Soul King Realm", 90, [("بازتاب بی‌پایان", "Endless Reflection"), ("نگهبان خلأ", "Void Keeper"), ("پژواک آغاز", "Echo of Origin")]),
    "valley_screams": _l("valley_screams", "دره فریادها", "Valley of Screams", 100, [("فریاد بی‌صدا", "Silent Scream"), ("روح خسته", "Wearied Shade"), ("جنگجوی فراموش‌شده", "Forgotten Warrior")]),
}

# ---- extra Bleach locations (levels fill the gaps between the first eleven) ---------------------------------
LOCATIONS.update({
    "zaraki_district": _l("zaraki_district", "ناحیه‌ی زاراکی (روکونگای ۸۰)", "Zaraki District (Rukongai 80)", 14,
                          [("راهزن خونین", "Blood Bandit"), ("جنگجوی بی‌نام", "Nameless Brawler"), ("سگ وحشی ناحیه", "District Wild Dog")]),
    "sokyoku_hill": _l("sokyoku_hill", "تپه‌ی سوکیوکو", "Sōkyoku Hill", 22,
                       [("جلاد نقاب‌دار", "Masked Executioner"), ("نگهبان دار", "Gallows Guard"), ("شبح محکوم", "Condemned Wraith")]),
    "forest_menos": _l("forest_menos", "جنگل منوس", "Forest of Menos", 28,
                       [("منوس کوچک", "Lesser Menos"), ("ماسک‌دار خزنده", "Creeping Masked"), ("سایه‌ی تنه‌ی استخوانی", "Bone-Trunk Shade")]),
    "fake_karakura": _l("fake_karakura", "کاراکورای ساختگی", "Fake Karakura Town", 40,
                        [("نگهبان شهر دروغین", "False Town Sentinel"), ("پژواک جنگ", "Echo of War"), ("سایه‌ی ریاتسو", "Reiatsu Phantom")]),
    "silbern_palace": _l("silbern_palace", "سیلبرن، کاخ وندن‌رایش", "Silbern, Wandenreich Palace", 65,
                         [("نگهبان سیلبرن", "Silbern Guard"), ("کوئینسی تاریک", "Dark Quincy"), ("پژواک امپراتور", "Echo of the Emperor")], "quincy"),
    # ---- Bleach content pack 2 ----
    "shinigami_academy": _l("shinigami_academy", "آکادمی شینیگامی", "Shinigami Academy", 3,
                            [("حریف تمرینی", "Sparring Cadet"), ("هالوی آزمایشی", "Trial Hollow"), ("مربی سخت‌گیر", "Strict Instructor")]),
    "inuzuri": _l("inuzuri", "اینوزوری (روکونگای ۷۸)", "Inuzuri (Rukongai 78)", 11,
                  [("سگ ولگرد گرسنه", "Starving Stray Dog"), ("دزد کوچه", "Alley Thief"), ("روح گرسنه", "Hungry Soul")]),
    "urahara_training": _l("urahara_training", "میدان تمرین زیرزمینی اوراهارا", "Urahara's Training Ground", 17,
                           [("دستگاه تمرین ریشی", "Reishi Training Rig"), ("تله‌ی اوراهارا", "Urahara's Trap"), ("شبح شکارچی", "Stalker Shade")]),
    "senzaikyu": _l("senzaikyu", "کاخ توبه (سنزایکیو)", "Palace of Penitence", 24,
                    [("نگهبان کاخ توبه", "Penitence Guard"), ("روح زنجیری", "Chained Soul"), ("شبح اعتراف", "Confessor Wraith")]),
    "maggot_nest": _l("maggot_nest", "لانه‌ی کرم‌ها", "Maggot's Nest", 32,
                      [("زندانی خطرناک", "Dangerous Inmate"), ("زندانبان بی‌صدا", "Silent Jailer"), ("آزمایش ناموفق", "Failed Experiment")]),
    "garganta_tunnel": _l("garganta_tunnel", "تونل گارگانتا", "Garganta Tunnel", 38,
                          [("شبح گارگانتا", "Garganta Wraith"), ("هالوی گذرنده", "Passing Hollow"), ("سایه‌ی تونل", "Tunnel Shade")]),
    "muken": _l("muken", "موکن (جهنم بی‌پایان)", "Muken (Infinite Hell)", 80,
                [("روح محکوم", "Condemned Soul"), ("زنجیر دوزخ", "Hell Chain"), ("نگهبان دوزخ", "Hell Warden")]),
    # ---- Bleach content pack 3 ----
    "kurosaki_clinic": _l("kurosaki_clinic", "کلینیک کوروساکی", "Kurosaki Clinic", 6,
                          [("هالوی شبانه", "Night Hollow"), ("روح بیمار", "Ailing Spirit"), ("شکارچی پشت‌بام", "Rooftop Stalker")]),
    "seireitei_gate": _l("seireitei_gate", "دروازه‌ی سیرایتی (جاده‌ی سفید)", "Seireitei Gate (White Road)", 13,
                         [("نگهبان دروازه", "Gate Sentry"), ("مهاجم شبانه", "Night Intruder"), ("سایه‌ی دیوار سفید", "White Wall Shade")]),
    "kuchiki_manor": _l("kuchiki_manor", "عمارت کوچیکی", "Kuchiki Manor", 19,
                        [("خدمتکار سایه", "Shadow Retainer"), ("نگهبان باغ", "Garden Sentinel"), ("شبح خاندان", "Clan Wraith")]),
    "shiba_estate": _l("shiba_estate", "املاک شیبا", "Shiba Estate", 26,
                       [("آتش‌باز بی‌پروا", "Reckless Fireworker"), ("نگهبان توپ‌خانه", "Cannon-House Guard"), ("سایه‌ی میدان آتش", "Fire-Yard Shade")]),
    "visored_warehouse": _l("visored_warehouse", "انبار ویزوردها", "Visored Warehouse", 34,
                            [("مبارز ماسک‌دار", "Masked Sparrer"), ("پژواک هالو", "Hollow Echo"), ("حریف تمرینی ویزورد", "Visored Sparring Rival")]),
    "research_institute": _l("research_institute", "مؤسسه‌ی پژوهش و توسعه", "Research & Development Institute", 42,
                             [("آزمایش فراری", "Escaped Specimen"), ("نگهبان آزمایشگاه", "Lab Warden"), ("نمونه‌ی شکست‌خورده", "Failed Sample")]),
    "las_noches_throne": _l("las_noches_throne", "تالار تخت لاس‌نوچس", "Las Noches Throne Hall", 50,
                            [("نگهبان تالار", "Hall Guardian"), ("سایه‌ی تاج", "Crown Shade"), ("فراسیون وفادار", "Loyal Fracción")]),
    "schatten_bereich": _l("schatten_bereich", "شاتن‌برایش (قلمرو سایه)", "Schatten Bereich (Shadow Realm)", 75,
                           [("سایه‌ی امپراتور", "Emperor's Shadow"), ("ستاره‌ی سایه", "Shade Star"), ("خادم تاریکی", "Servant of the Dark")]),
    # ---- Bleach content pack 4 ----
    "junrinan": _l("junrinan", "جونرینان (روکونگای ۱)", "Junrinan (Rukongai 1)", 2,
                   [("روح تازه‌رسیده", "Newly Arrived Soul"), ("دزد بازار", "Market Thief"), ("سگ نگهبان", "Guard Dog")]),
    "karakura_high": _l("karakura_high", "دبیرستان کاراکورا", "Karakura High School", 4,
                        [("هالوی راهرو", "Hallway Hollow"), ("روح کلاس", "Classroom Spirit"), ("سایه‌ی پشت‌بام", "Rooftop Shade")]),
    "urahara_shop": _l("urahara_shop", "فروشگاه اوراهارا", "Urahara Shop", 9,
                       [("موش آزمایشگاهی", "Test Subject"), ("تله‌ی ناشناس", "Unmarked Trap"), ("مشتری مشکوک", "Suspicious Customer")]),
    "relief_station": _l("relief_station", "ایستگاه امداد جوخه‌ی ۴", "4th Division Relief Station", 16,
                         [("بیمار بی‌قرار", "Restless Patient"), ("روح زخمی", "Wounded Soul"), ("سایه‌ی بیمارستان", "Infirmary Shade")]),
    "captains_hall": _l("captains_hall", "تالار جلسه‌ی کاپیتان‌ها", "Captains' Assembly Hall", 31,
                        [("نگهبان تالار", "Assembly Guard"), ("پژواک فرمان", "Echo of Command"), ("سایه‌ی هائوری", "Haori Shade")]),
    "jigoku": _l("jigoku", "جیگوکو (دوزخ)", "Jigoku (Hell)", 58,
                 [("گناهکار زنجیری", "Chained Sinner"), ("نگهبان دوزخ", "Hell Keeper"), ("شعله‌ی محکوم", "Condemned Flame")]),
    "sternritter_hall": _l("sternritter_hall", "تالار استرنریترها", "Sternritter Hall", 62,
                           [("ستاره‌دار خاموش", "Silent Star"), ("نگهبان مقدس", "Holy Guard"), ("پژواک ستاره", "Star Echo")]),
    "hogyoku_chamber": _l("hogyoku_chamber", "اتاق هوگیوکو", "Hōgyoku Chamber", 95,
                          [("پژواک خواسته", "Echo of a Wish"), ("نگهبان بلور", "Crystal Keeper"), ("سایه‌ی اراده", "Shade of Will")]),
})
# ---- Bleach content pack 5 ----
LOCATIONS.update({
    "riverbank": _l("riverbank", "کنار رود کاراکورا", "Karakura Riverbank", 7,
                    [("هالوی مه‌آلود", "Mist Hollow"), ("روح کنار رود", "Riverside Spirit"), ("سایه‌ی پل", "Bridge Shade")]),
    "kusajishi_district": _l("kusajishi_district", "کوساجیشی (روکونگای ۷۹)", "Kusajishi (Rukongai 79)", 12,
                             [("راهزن کوچه‌ی خشک", "Dry Alley Bandit"), ("سگ گرسنه‌ی محله", "District Starving Hound"), ("روح تنها", "Lone Soul")]),
    "bount_mansion": _l("bount_mansion", "عمارت بونت‌ها", "Bount Mansion", 21,
                        [("عروسک جان‌گرفته", "Animated Doll"), ("خدمتکار عمارت", "Mansion Retainer"), ("شبح مکانیکی", "Clockwork Wraith")]),
    "xcution_hideout": _l("xcution_hideout", "پناهگاه اکسکیوشن", "Xcution Hideout", 27,
                          [("فول‌برینگر سرکش", "Rogue Fullbringer"), ("دیده‌بان پناهگاه", "Hideout Lookout"), ("پژواک قدرت ازدست‌رفته", "Echo of Lost Power")]),
    "orihime_chamber": _l("orihime_chamber", "اتاق اسیر لاس‌نوچس", "Captive's Chamber, Las Noches", 36,
                          [("نگهبان شب‌زنده‌دار", "Sleepless Guard"), ("سایه‌ی پنجره‌ی قفل‌شده", "Locked-Window Shade"), ("پژواک یک دعا", "Echo of a Prayer")]),
    "precipice_world": _l("precipice_world", "جهان پرتگاه (دنگای)", "Precipice World", 47,
                          [("جریان پرتگاه", "Precipice Current"), ("کوملای پرتگاه", "Precipice Kumo"), ("مه‌ی زمان", "Time Fog")]),
    "seireitei_ruins": _l("seireitei_ruins", "ویرانه‌های سیرایتی", "Seireitei in Ruins", 68,
                          [("سرباز ستاره‌دار مهاجم", "Invading Star Soldier"), ("نگهبان تسلیم‌نشده", "Unyielding Sentry"), ("سایه‌ی خاکستر", "Ash Shade")]),
    "zero_division_hall": _l("zero_division_hall", "تالار نیروی صفر", "Zero Division Hall", 88,
                             [("نگهبان صفر", "Zero Sentinel"), ("پژواک پادشاه", "Echo of the King"), ("سایه‌ی کلید", "Shade of the Key")]),
})
LOCATIONS = dict(sorted(LOCATIONS.items(), key=lambda kv: kv[1]["level"]))

DUNGEONS = {
    "trial": {"fa": "آزمون سول‌سوسایتی", "en": "Soul Society Trial", "level": 5, "stages": 3},
    "hollow_den": {"fa": "لانه‌ی هالو", "en": "Hollow Den", "level": 15, "stages": 4},
    "menos_forest": {"fa": "جنگل منوس", "en": "Menos Forest", "level": 30, "stages": 5},
    "noches_depths": {"fa": "اعماق لاس‌نوچس", "en": "Depths of Las Noches", "level": 45, "stages": 5},
    "quincy_fort": {"fa": "دژ کوئینسی", "en": "Quincy Fortress", "level": 55, "stages": 6},
    "palace_trial": {"fa": "آزمون کاخ سلطنتی", "en": "Royal Palace Trial", "level": 70, "stages": 6},
    "dangai_rift": {"fa": "شکاف دنگای", "en": "Dangai Rift", "level": 85, "stages": 7},
}
# ---- Bleach content pack 2 (appended; keep the order of DUNGEON_IDS in data_items / data_crafting in sync) ----
DUNGEONS.update({
    "academy_exam": {"fa": "آزمون نهایی آکادمی", "en": "Academy Final Exam", "level": 8, "stages": 3},
    "urahara_pit": {"fa": "گودال تمرین اوراهارا", "en": "Urahara's Training Pit", "level": 20, "stages": 4},
    "senzaikyu_tower": {"fa": "برج سنزایکیو", "en": "Senzaikyū Tower", "level": 25, "stages": 4},
    "maggot_nest": {"fa": "لانه‌ی کرم‌ها", "en": "Maggot's Nest", "level": 38, "stages": 5},
    "muken": {"fa": "موکن؛ جهنم بی‌پایان", "en": "Muken, the Infinite Hell", "level": 78, "stages": 6},
})
# ---- Bleach content pack 3 (appended; DUNGEON_IDS in data_items / data_crafting get the same four ids at the end) ----
DUNGEONS.update({
    "clinic_nightwatch": {"fa": "نگهبانی شب کلینیک", "en": "Clinic Night Watch", "level": 12, "stages": 3},
    "visored_gauntlet": {"fa": "گذرگاه آزمون ویزورد", "en": "Visored Gauntlet", "level": 35, "stages": 4},
    "srdi_lab": {"fa": "آزمایشگاه مؤسسه‌ی پژوهش", "en": "SRDI Laboratory", "level": 48, "stages": 5},
    "schatten_depths": {"fa": "اعماق شاتن‌برایش", "en": "Depths of Schatten Bereich", "level": 90, "stages": 7},
})
# ---- Bleach content pack 4 ----
DUNGEONS.update({
    "karakura_midnight": {"fa": "نیمه‌شب دبیرستان کاراکورا", "en": "Karakura High Midnight", "level": 6, "stages": 3},
    "captains_trial": {"fa": "آزمون تالار کاپیتان‌ها", "en": "Captains' Assembly Trial", "level": 32, "stages": 4},
    "jigoku_pit": {"fa": "گودال جیگوکو", "en": "Pit of Jigoku", "level": 60, "stages": 6},
    "hogyoku_vault": {"fa": "خزانه‌ی هوگیوکو", "en": "Hōgyoku Vault", "level": 95, "stages": 7},
})
# ---- Bleach content pack 5 (DUNGEON_IDS in data_items / data_crafting get the same four ids at the end) ----
DUNGEONS.update({
    "riverbank_vigil": {"fa": "شب‌زنده‌داری کنار رود", "en": "Riverbank Vigil", "level": 10, "stages": 3},
    "bount_labyrinth": {"fa": "هزارتوی عمارت بونت‌ها", "en": "Bount Mansion Labyrinth", "level": 22, "stages": 4},
    "precipice_run": {"fa": "عبور از جهان پرتگاه", "en": "Run of the Precipice World", "level": 50, "stages": 5},
    "zero_trial": {"fa": "آزمون نیروی صفر", "en": "Zero Division Trial", "level": 92, "stages": 7},
})
DUNGEONS = dict(sorted(DUNGEONS.items(), key=lambda kv: kv[1]["level"]))
DIFFICULTY = {"normal": 1.0, "hard": 1.5, "nightmare": 2.2, "abyss": 3.2, "legendary": 4.5}
DIFF_FA = {"normal": "عادی", "hard": "سخت", "nightmare": "کابوس", "abyss": "ورطه", "legendary": "افسانه‌ای"}
