"""Races, evolution paths and world locations (static game data)."""
STATS = ("zanjutsu", "kido", "hakuda", "hoho", "reiatsu")
STAT_ICON = {"zanjutsu": "⚔️", "kido": "🔮", "hakuda": "🛡️", "hoho": "💨", "reiatsu": "✨"}
LEVEL_GATES = [1, 15, 35, 60, 90]


def _r(fa, en, st, home, mods, evo, locked=False):
    return {"name_fa": fa, "name_en": en, "stats": dict(zip(STATS, st)), "home": home,
            "mods": mods, "evo": evo, "locked": locked}


RACES = {
    "shinigami": _r("شینیگامی", "Shinigami", (8, 9, 5, 10, 8), "soul_society", {"kido": 1.05}, None),
    "quincy": _r("کوئینسی", "Quincy", (4, 3, 9, 10, 14), "wandenreich", {"pierce": 0.10, "dmg": 1.12, "def": 1.03, "hp": 1.09}, None),
    "hollow": _r("هالو", "Hollow", (6, 2, 10, 9, 13), "hueco_mundo", {"dmg": 0.90, "hp": 0.92}, None),  # Hakuda drives its abilities too (HP + power), so a lower HP base
    "arrancar": _r("آرانکار", "Arrancar", (10, 2, 8, 11, 9), "las_noches", {"dmg": 0.91, "hp": 0.98}, None),
    "fullbringer": _r("فول‌برینگر", "Fullbringer", (8, 2, 8, 10, 12), "karakura", {"crit": 0.04, "hp": 1.12}, None),
    "human": _r("انسان / روح", "Human / Soul", (9, 3, 8, 11, 9), "karakura", {"xp": 1.10, "crit": 0.03, "dmg": 1.06, "def": 0.97, "hp": 1.09}, None),
    "visored": _r("ویزورد", "Visored", (10, 5, 6, 10, 9), "karakura", {"dmg": 1.15, "hp": 1.15}, None, locked=True),  # raised after the ability-stat rework
}
# Evolution titles come from the one 5-stage canon path per race (data_evolution.EVO_PATHS)
from data_evolution import EVO_PATHS as _EVO_PATHS  # noqa: E402
for _k, _race in RACES.items():
    _race["evo"] = [title for title, _add, _desc in _EVO_PATHS[_k]]


# Base stats before the balance pass. Characters store absolute stats, so a one-time migration moves each
# character onto the new base while keeping every point they put in (see rebased_stats).
OLD_RACE_BASE = {
    "shinigami": (10, 8, 7, 8, 8), "quincy": (6, 10, 5, 7, 6), "hollow": (8, 4, 9, 7, 8),
    "arrancar": (9, 4, 10, 9, 9), "fullbringer": (7, 7, 7, 8, 7), "human": (7, 7, 7, 7, 7),
    "visored": (9, 9, 8, 9, 10),
}


# Bases before the second balance pass (equal win rates at ~1.0 multipliers). Characters that already moved onto these
# are moved once more by service_respec.rebase_race_stats_v3_once.
PREV_RACE_BASE = {
    "shinigami": (10, 9, 6, 8, 7), "quincy": (6, 3, 7, 9, 15), "hollow": (7, 2, 12, 8, 11),
    "arrancar": (10, 2, 8, 10, 10), "fullbringer": (8, 2, 8, 9, 13), "human": (8, 3, 9, 10, 10),
    "visored": (8, 7, 8, 8, 9),
}


def rebased_stats(race: str, stats: dict, old_base=None, new_base=None) -> dict:
    """New absolute stats for a character of `race`: new base + the points allocated over the old base.
    Defaults: OLD_RACE_BASE -> the current RACES base."""
    old = dict(zip(STATS, old_base if old_base is not None else OLD_RACE_BASE[race]))
    new = dict(zip(STATS, new_base)) if new_base is not None else RACES[race]["stats"]
    return {k: int(new[k]) + max(0, int(stats.get(k, 0)) - old[k]) for k in STATS}


# Human passive: Tatsuki, Keigo and Mizuiro can see spirits and hollows, so they strike harder at them.
SPIRITUAL_AWARENESS_VS_HOLLOW = 1.10


def spiritual_awareness_mult(race: str, foe: str) -> float:
    """Damage multiplier a fighter gets from its race against its foe kind (1.0 when there is no passive)."""
    return SPIRITUAL_AWARENESS_VS_HOLLOW if race == "human" and foe == "hollow" else 1.0


# Visored: the Visored race is locked, so players reach it by clearing the Visored Gauntlet as a Shinigami.
VISORED_UNLOCK_DUNGEON = "visored_gauntlet"


def unlocks_visored(race: str, dungeon_id: str) -> bool:
    """True when clearing `dungeon_id` as `race` unlocks the Visored race (only Shinigami can take the trial)."""
    return race == "shinigami" and dungeon_id == VISORED_UNLOCK_DUNGEON


def race_selectable(race_key: str, ch: dict) -> bool:
    """Can this character pick `race_key` (locked races need their unlock)?"""
    if race_key not in RACES:
        return False
    if not RACES[race_key].get("locked"):
        return True
    return race_key == "visored" and bool((ch or {}).get("visored_unlocked"))


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
    "soul_society": _l("soul_society", "سول‌سوسایتی", "Soul Society", 1, [("پلاس گمشده", "Lost Plus"), ("قلدر روکونگای", "Rukongai Thug"), ("قاچاقچی ریشی", "Reishi Smuggler")]),
    "seireitei": _l("seireitei", "سیرایتی", "Seireitei", 10, [("گشت اونمیتسوکیدو", "Onmitsukidō Patroller"), ("شینیگامی جوخه‌ی ۱۱", "11th Division Brawler"), ("افسر بی‌کرسی گوته‌ی ۱۳", "Unseated Gotei Officer")]),
    "rukongai": _l("rukongai", "روکونگای", "Rukongai", 5, [("هالوی ولگرد روکونگای", "Rukongai Stray Hollow"), ("راهزن ناحیه‌های دور", "Outer District Bandit"), ("شینیگامی تبعیدی", "Exiled Shinigami")]),
    "karakura": _l("karakura", "کاراکورا تاون", "Karakura Town", 8, [("نیمه‌هالو", "Demi-Hollow"), ("جیباکورِی کینه‌جو", "Vengeful Jibakurei"), ("کوئینسی رقیب", "Rival Quincy")]),
    "hueco_mundo": _l("hueco_mundo", "هوئکو موندو", "Hueco Mundo", 20, [("جیلیان (منوس گرانده)", "Gillian (Menos Grande)"), ("آجوکاس شکارچی", "Adjuchas Hunter"), ("هالوی کرم شنی", "Sand-Worm Hollow")], "hollow"),
    "las_noches": _l("las_noches", "لاس‌نوچس", "Las Noches", 35, [("سرباز نومروس", "Numeros Soldier"), ("جلاد اکسکیاس", "Exequias Executioner"), ("اسپادای پریوارون", "Privaron Espada")]),
    "dangai": _l("dangai", "دنگای", "Dangai", 45, [("کوریو، جریان مهارکننده", "Kōryū, the Restraining Current"), ("کوتوتسو، پاک‌کننده", "Kōtotsu, the Cleaner"), ("روح گرفتار کوریو", "Kōryū-Trapped Soul")]),
    "wandenreich": _l("wandenreich", "وندن‌رایش", "Wandenreich", 55, [("سولدات وندن‌رایش", "Wandenreich Soldat"), ("شکارچی یاگدآرمه", "Jagdarmee Hunter"), ("استرنریتر تازه‌کار", "Novice Sternritter")], "quincy"),
    "royal_palace": _l("royal_palace", "کاخ سلطنتی", "Royal Palace", 70, [("نگهبان ریئوکیو", "Reiōkyū Sentinel"), ("خدمتکار قصر کیرینجی", "Kirinji Palace Attendant"), ("بافنده‌ی قصر شوتارا", "Shutara's Weaver")]),
    "soul_king": _l("soul_king", "قلمرو شاه ارواح", "Soul King Realm", 90, [("پرتو میمی‌هاگی", "Mimihagi's Gleam"), ("نگهبان قصر شاه ارواح", "Soul King Palace Keeper"), ("پژواک پرنیدا", "Pernida's Echo")]),
    "valley_screams": _l("valley_screams", "دره فریادها", "Valley of Screams", 100, [("تاریک‌زاده", "Dark One"), ("روح طردشده", "Rejected Soul"), ("سرگردان بی‌خاطره", "Memory-Lost Wanderer")]),
}

# ---- extra Bleach locations (levels fill the gaps between the first eleven) ---------------------------------
LOCATIONS.update({
    "zaraki_district": _l("zaraki_district", "ناحیه‌ی زاراکی (روکونگای ۸۰)", "Zaraki District (Rukongai 80)", 14,
                          [("راهزن ناحیه‌ی ۸۰", "District 80 Raider"), ("جنگجوی تشنه‌ی نبرد", "Battle-Mad Brawler"), ("مدعی لقب کنپاچی", "Would-be Kenpachi")]),
    "sokyoku_hill": _l("sokyoku_hill", "تپه‌ی سوکیوکو", "Sōkyoku Hill", 22,
                       [("منوس نگاسیون", "Negación Menos"), ("جلاد سپاه کیدو", "Kidō Corps Executioner"), ("پژواک ققنوس کیکوئو", "Kikōō Phoenix Echo")]),
    "forest_menos": _l("forest_menos", "جنگل منوس", "Forest of Menos", 28,
                       [("جیلیان جنگل منوس", "Forest Gillian"), ("آجوکاس گرسنه", "Starving Adjuchas"), ("شکارچی گله‌ی شاولونگ", "Shawlong's Pack Hunter")]),
    "fake_karakura": _l("fake_karakura", "کاراکورای ساختگی", "Fake Karakura Town", 40,
                        [("فراسیون باراگان", "Baraggan's Fracción"), ("فراسیون هریبل", "Harribel's Fracción"), ("سایه‌ی آیون", "Shade of Ayon")]),
    "silbern_palace": _l("silbern_palace", "سیلبرن، کاخ وندن‌رایش", "Silbern, Wandenreich Palace", 65,
                         [("نگهبان سیلبرن", "Silbern Guard"), ("کوئینسی گمیشت", "Gemischt Quincy"), ("پژواک آئوسوِلن", "Auswählen Echo")], "quincy"),
    # ---- Bleach content pack 2 ----
    "shinigami_academy": _l("shinigami_academy", "آکادمی شینیگامی", "Shinigami Academy", 3,
                            [("دانشجوی آکادمی شینئو", "Shin'ō Academy Cadet"), ("هالوی مصنوعی تمرینی", "Artificial Training Hollow"), ("مربی کیدوی آکادمی", "Academy Kidō Instructor")]),
    "inuzuri": _l("inuzuri", "اینوزوری (روکونگای ۷۸)", "Inuzuri (Rukongai 78)", 11,
                  [("سگ ولگرد اینوزوری", "Inuzuri Stray Hound"), ("یتیم دزد اینوزوری", "Inuzuri Orphan Thief"), ("روح گرسنه‌ی ریشی", "Reiryoku-Starved Soul")]),
    "urahara_training": _l("urahara_training", "میدان تمرین زیرزمینی اوراهارا", "Urahara's Training Ground", 17,
                           [("زنجیر در حال خوردگی", "Encroaching Chain"), ("رگبار تمرینی اورورو", "Ururu's Sparring Barrage"), ("بند باکودوی تسّای", "Tessai's Bakudō Bind")]),
    "senzaikyu": _l("senzaikyu", "کاخ توبه (سنزایکیو)", "Palace of Penitence", 24,
                    [("نگهبان برج از جوخه‌ی ۶", "6th Division Tower Guard"), ("مأمور شورای ۴۶", "Central 46 Enforcer"), ("نگهبان پل سنزایکیو", "Senzaikyū Bridge Sentry")]),
    "maggot_nest": _l("maggot_nest", "لانه‌ی کرم‌ها", "Maggot's Nest", 32,
                      [("زندانی لانه‌ی کرم‌ها", "Maggot's Nest Inmate"), ("زندانبان واحد بازداشت", "Detention Unit Jailer"), ("شینیگامی دیوانه", "Deranged Shinigami")]),
    "garganta_tunnel": _l("garganta_tunnel", "تونل گارگانتا", "Garganta Tunnel", 38,
                          [("سرگردان مسیر ریشی", "Reishi-Path Wanderer"), ("هالوی کمین‌کرده در گارگانتا", "Garganta-Lurking Hollow"), ("آرانکار پیشرو", "Arrancar Vanguard")]),
    "muken": _l("muken", "موکن (جهنم بی‌پایان)", "Muken (Infinite Hell)", 80,
                [("زندانی موکن", "Muken Prisoner"), ("مهر بند سپاه کیدو", "Kidō Corps Seal"), ("نگهبان موکن", "Muken Warden")]),
    # ---- Bleach content pack 3 ----
    "kurosaki_clinic": _l("kurosaki_clinic", "کلینیک کوروساکی", "Kurosaki Clinic", 6,
                          [("هالوی فیش‌بون دی", "Fishbone D Hollow"), ("پلاس زنجیرشکسته", "Plus with a Broken Chain"), ("شریکر", "Shrieker")]),
    "seireitei_gate": _l("seireitei_gate", "دروازه‌ی سیرایتی (جاده‌ی سفید)", "Seireitei Gate (White Road)", 13,
                         [("دروازه‌بان غول‌پیکر", "Giant Gatekeeper"), ("ریوکای مزاحم", "Intruding Ryoka"), ("نگهبان دیوار سکی‌سکی", "Sekkiseki Wall Guard")]),
    "kuchiki_manor": _l("kuchiki_manor", "عمارت کوچیکی", "Kuchiki Manor", 19,
                        [("ملازم خاندان کوچیکی", "Kuchiki Retainer"), ("نگهبان باغ شکوفه‌ی گیلاس", "Cherry-Blossom Garden Guard"), ("روح نیای کوچیکی", "Kuchiki Ancestral Spirit")]),
    "shiba_estate": _l("shiba_estate", "املاک شیبا", "Shiba Estate", 26,
                       [("خدمه‌ی آتش‌بازی کوکاکو", "Kūkaku's Fireworks Crew"), ("نگهبان توپ گل‌لک‌لک", "Flower Crane Cannon Guard"), ("دروازه‌بان دوقلوی شیبا", "Shiba Twin Gatekeeper")]),
    "visored_warehouse": _l("visored_warehouse", "انبار ویزوردها", "Visored Warehouse", 34,
                            [("ویزورد ماسک‌دار", "Masked Visored"), ("هالوی درونی", "Inner Hollow"), ("حریف تمرینی ویزورد", "Visored Sparring Partner")]),
    "research_institute": _l("research_institute", "مؤسسه‌ی پژوهش و توسعه", "Research & Development Institute", 42,
                             [("نمونه‌ی فراری مایوری", "Mayuri's Escaped Specimen"), ("پژوهشگر جوخه‌ی ۱۲", "12th Division Researcher"), ("ماکت سری نموری", "Nemuri Series Replica")]),
    "las_noches_throne": _l("las_noches_throne", "تالار تخت لاس‌نوچس", "Las Noches Throne Hall", 50,
                            [("فراسیون اسپادا", "Espada Fracción"), ("آرانکار نگهبان تخت", "Throne Room Arrancar"), ("نومروس نخبه", "Elite Numeros")]),
    "schatten_bereich": _l("schatten_bereich", "شاتن‌برایش (قلمرو سایه)", "Schatten Bereich (Shadow Realm)", 75,
                           [("سولدات شاتن", "Schatten Soldat"), ("استرنریتر سایه‌گرد", "Shadow-Walking Sternritter"), ("دروازه‌بان شاتن", "Schatten Gatekeeper")]),
    # ---- Bleach content pack 4 ----
    "junrinan": _l("junrinan", "جونرینان (روکونگای ۱)", "Junrinan (Rukongai 1)", 2,
                   [("پلاس تازه کونسوشده", "Freshly Konsō'd Plus"), ("دزد بازار جونرینان", "Junrinan Market Thief"), ("گراز دار و دسته‌ی گانجو", "Ganju Gang Boar")]),
    "karakura_high": _l("karakura_high", "دبیرستان کاراکورا", "Karakura High School", 4,
                        [("هالوی جذب‌شده با طعمه‌ی ایشیدا", "Bait-Drawn Hollow"), ("جیباکورِی کلاس", "Classroom Jibakurei"), ("مادسول سرکش", "Rogue Mod Soul")]),
    "urahara_shop": _l("urahara_shop", "فروشگاه اوراهارا", "Urahara Shop", 9,
                       [("گیگای معیوب", "Defective Gigai"), ("مادسول قاچاق", "Contraband Mod Soul"), ("گیکونگان چاپی سرکش", "Rogue Chappy Gikon")]),
    "relief_station": _l("relief_station", "ایستگاه امداد جوخه‌ی ۴", "4th Division Relief Station", 16,
                         [("بیمار شرور جوخه‌ی ۱۱", "Unruly 11th Division Patient"), ("امدادگر سرکش جوخه‌ی ۴", "Rogue 4th Division Medic"), ("کارآموز کایدو", "Kaidō Trainee")]),
    "captains_hall": _l("captains_hall", "تالار جلسه‌ی کاپیتان‌ها", "Captains' Assembly Hall", 31,
                        [("افسر جوخه‌ی ۱", "1st Division Officer"), ("افسر کرسی سوم", "Third Seat Officer"), ("سایه‌ی هائوری کاپیتان", "Captain's Haori Shade")]),
    "jigoku": _l("jigoku", "جیگوکو (دوزخ)", "Jigoku (Hell)", 58,
                 [("توگابیتو، گناهکار دوزخ", "Togabito"), ("کوشاناده، نگهبان دوزخ", "Kushanāda"), ("زنجیر دوزخ", "Chain of Hell")]),
    "sternritter_hall": _l("sternritter_hall", "تالار استرنریترها", "Sternritter Hall", 62,
                           [("محافظ شوتس‌اشتافل", "Schutzstaffel Guard"), ("سولدات ارشد", "Senior Soldat"), ("دارنده‌ی شریفت", "Schrift Bearer")]),
    "hogyoku_chamber": _l("hogyoku_chamber", "اتاق هوگیوکو", "Hōgyoku Chamber", 95,
                          [("پژواک آرزو", "Echo of a Wish"), ("توهم کیوکا سویگتسو", "Kyōka Suigetsu Illusion"), ("سایه‌ی پیله‌ی آیزن", "Aizen's Chrysalis Shade")]),
})
# ---- Bleach content pack 5 ----
LOCATIONS.update({
    "riverbank": _l("riverbank", "کنار رود کاراکورا", "Karakura Riverbank", 7,
                    [("هالوی پیرو گرند فیشر", "Grand Fisher's Brood Hollow"), ("طعمه‌ی دختر شبح", "Phantom Girl Lure"), ("جیباکورِی کنار رود", "Riverside Jibakurei")]),
    "kusajishi_district": _l("kusajishi_district", "کوساجیشی (روکونگای ۷۹)", "Kusajishi (Rukongai 79)", 12,
                             [("گردن‌زن کوساجیشی", "Kusajishi Cutthroat"), ("لاشخور میدان جنگ", "Battlefield Scavenger"), ("شمشیرزن بی‌نام", "Nameless Swordsman")]),
    "bount_mansion": _l("bount_mansion", "عمارت بونت‌ها", "Bount Mansion", 21,
                        [("دال (عروسک بونت)", "Bount Doll"), ("دسته‌ی بیتو", "Bitto Swarm"), ("بونت گرسنه‌ی روح", "Soul-Starved Bount")]),
    "xcution_hideout": _l("xcution_hideout", "پناهگاه اکسکیوشن", "Xcution Hideout", 27,
                          [("فول‌برینگر سرکش", "Rogue Fullbringer"), ("عروسک دال‌هاوس ریروکا", "Riruka's Dollhouse Doll"), ("بازیچه‌ی بوک‌مارک تسوکیشیما", "Tsukishima's Bookmarked Pawn")]),
    "orihime_chamber": _l("orihime_chamber", "اتاق اسیر لاس‌نوچس", "Captive's Chamber, Las Noches", 36,
                          [("آرانکار حسود ملازم", "Jealous Arrancar Attendant"), ("خدمتکار آرانکار", "Arrancar Servant"), ("سایه‌ی نگهبانی اولکیورا", "Ulquiorra's Watchful Shade")]),
    "precipice_world": _l("precipice_world", "جهان پرتگاه (دنگای)", "Precipice World", 47,
                          [("جریان پرتگاه", "Precipice Current"), ("رهگذر گم‌شده‌ی دنگای", "Lost Dangai Traveler"), ("مه زمان دنگای", "Dangai Time Fog")]),
    "seireitei_ruins": _l("seireitei_ruins", "ویرانه‌های سیرایتی", "Seireitei in Ruins", 68,
                          [("سولدات مهاجم", "Invading Soldat"), ("شینیگامی زامبی‌شده‌ی جیزل", "Giselle's Zombie Shinigami"), ("پژواک بانکای دزدیده‌شده", "Stolen-Bankai Echo")]),
    "zero_division_hall": _l("zero_division_hall", "تالار نیروی صفر", "Zero Division Hall", 88,
                             [("نگهبان نیروی صفر", "Squad Zero Sentinel"), ("پژواک نام‌های ایچیبه", "Echo of Ichibē's Names"), ("سایه‌ی کلید اوکن", "Ōken Key Shade")]),
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

# Each dungeon fights its own Bleach enemies (before, dungeons borrowed the enemy list of wherever the player stood,
# so Muken could throw a "Street Hollow"). race works like LOCATIONS race: "hollow" = every foe uses Cero,
# "quincy" = Hirenkyaku, None = decided by the name (data_bleachfx.enemy_sig). "boss" names the last stage.
DUNGEON_ENEMIES = {
    "trial": {"race": None, "boss": ("افسر کرسی سوم ممتحن", "Third Seat Examiner"),
        "enemies": [("افسر بی‌کرسی ممتحن", "Unseated Examiner"), ("گشت اونمیتسوکیدو", "Onmitsukidō Patroller"), ("پلاس سرکش", "Unruly Plus")]},
    "karakura_midnight": {"race": None, "boss": ("منوس گرانده‌ی طعمه‌ی ایشیدا", "Menos Grande of Ishida's Bait"),
        "enemies": [("هالوی جذب‌شده با طعمه", "Bait-Drawn Hollow"), ("جیباکورِی مدرسه", "School Jibakurei"), ("مادسول سرکش", "Rogue Mod Soul")]},
    "academy_exam": {"race": None, "boss": ("هالوی عظیم حادثه‌ی تمرین", "Huge Hollow of the Training Incident"),
        "enemies": [("هالوی مصنوعی امتحان", "Exam Training Hollow"), ("دانشجوی رقیب آکادمی", "Rival Academy Cadet"), ("ممتحن کیدو", "Kidō Examiner")]},
    "riverbank_vigil": {"race": None, "boss": ("پژواک هالوی گرند فیشر", "Grand Fisher's Hollow Echo"),
        "enemies": [("هالوی پیرو گرند فیشر", "Grand Fisher's Brood Hollow"), ("طعمه‌ی دختر شبح", "Phantom Girl Lure"), ("جیباکورِی باران", "Rain Jibakurei")]},
    "clinic_nightwatch": {"race": None, "boss": ("نیمه‌هالوی بولبوس جی", "Bulbous G, Demi-Hollow"),
        "enemies": [("هالوی فیش‌بون دی", "Fishbone D Hollow"), ("شریکر", "Shrieker"), ("پلاس زنجیرشکسته", "Plus with a Broken Chain")]},
    "hollow_den": {"race": 'hollow', "boss": ("هالوی عظیم", "Huge Hollow"),
        "enemies": [("هالوی درنده", "Ravenous Hollow"), ("آجوکاس جوان", "Young Adjuchas"), ("نیمه‌هالو", "Demi-Hollow")]},
    "urahara_pit": {"race": None, "boss": ("هالوی درونی شافت شکسته", "Inner Hollow of the Shattered Shaft"),
        "enemies": [("زنجیر در حال خوردگی", "Encroaching Chain"), ("رگبار تمرینی اورورو", "Ururu's Sparring Barrage"), ("بند باکودوی تسّای", "Tessai's Bakudō Bind")]},
    "bount_labyrinth": {"race": None, "boss": ("سایه‌ی جین کاریا", "Shade of Jin Kariya"),
        "enemies": [("دال (عروسک بونت)", "Bount Doll"), ("دسته‌ی بیتو", "Bitto Swarm"), ("بونت گرسنه‌ی روح", "Soul-Starved Bount")]},
    "senzaikyu_tower": {"race": None, "boss": ("ستوان نگهبان سنزایکیو", "Senzaikyū Warden Lieutenant"),
        "enemies": [("نگهبان برج از جوخه‌ی ۶", "6th Division Tower Guard"), ("مأمور شورای ۴۶", "Central 46 Enforcer"), ("نگهبان پل سنزایکیو", "Senzaikyū Bridge Sentry")]},
    "menos_forest": {"race": 'hollow', "boss": ("واستو لورد جنگل", "Forest Vasto Lorde"),
        "enemies": [("جیلیان جنگل منوس", "Forest Gillian"), ("آجوکاس گرسنه", "Starving Adjuchas"), ("شکارچی گله‌ی شاولونگ", "Shawlong's Pack Hunter")]},
    "captains_trial": {"race": None, "boss": ("ممتحن آزمون کاپیتانی", "Captain Proficiency Examiner"),
        "enemies": [("افسر جوخه‌ی ۱", "1st Division Officer"), ("افسر کرسی سوم", "Third Seat Officer"), ("ستوان ممتحن", "Examining Lieutenant")]},
    "visored_gauntlet": {"race": None, "boss": ("هالوی درونی مهارنشده", "Uncontrolled Inner Hollow"),
        "enemies": [("ویزورد ماسک‌دار", "Masked Visored"), ("هالوی درونی", "Inner Hollow"), ("حریف تمرینی ویزورد", "Visored Sparring Partner")]},
    "maggot_nest": {"race": None, "boss": ("پژواک مایوریِ زندانی", "Echo of Mayuri the Inmate"),
        "enemies": [("زندانی لانه‌ی کرم‌ها", "Maggot's Nest Inmate"), ("زندانبان واحد بازداشت", "Detention Unit Jailer"), ("شینیگامی دیوانه", "Deranged Shinigami")]},
    "noches_depths": {"race": None, "boss": ("رودبورن چلوته، فرمانده‌ی اکسکیاس", "Rudbornn Chelute, Exequias Commander"),
        "enemies": [("سرباز نومروس", "Numeros Soldier"), ("جلاد اکسکیاس", "Exequias Executioner"), ("اسپادای پریوارون", "Privaron Espada")]},
    "srdi_lab": {"race": None, "boss": ("آکون، کرسی سوم مؤسسه", "Akon, SRDI Third Seat"),
        "enemies": [("نمونه‌ی فراری مایوری", "Mayuri's Escaped Specimen"), ("پژوهشگر جوخه‌ی ۱۲", "12th Division Researcher"), ("ماکت سری نموری", "Nemuri Series Replica")]},
    "precipice_run": {"race": None, "boss": ("کوریوی خشمگین", "Raging Kōryū"),
        "enemies": [("کوریو، جریان مهارکننده", "Kōryū, the Restraining Current"), ("رهگذر گم‌شده‌ی دنگای", "Lost Dangai Traveler"), ("مه زمان دنگای", "Dangai Time Fog")]},
    "quincy_fort": {"race": 'quincy', "boss": ("فرمانده‌ی استرنریتر", "Sternritter Commander"),
        "enemies": [("سولدات وندن‌رایش", "Wandenreich Soldat"), ("شکارچی یاگدآرمه", "Jagdarmee Hunter"), ("دارنده‌ی شریفت", "Schrift Bearer")]},
    "jigoku_pit": {"race": None, "boss": ("کوکوتو، توگابیتوی رهاشده", "Kokutō, the Unchained Togabito"),
        "enemies": [("توگابیتو، گناهکار دوزخ", "Togabito"), ("کوشاناده، نگهبان دوزخ", "Kushanāda"), ("زنجیر دوزخ", "Chain of Hell")]},
    "palace_trial": {"race": None, "boss": ("محافظ نیروی صفر", "Squad Zero Guardian"),
        "enemies": [("نگهبان ریئوکیو", "Reiōkyū Sentinel"), ("خدمتکار قصر کیرینجی", "Kirinji Palace Attendant"), ("بافنده‌ی قصر شوتارا", "Shutara's Weaver")]},
    "muken": {"race": None, "boss": ("سایه‌ی آیزنِ مهروموم‌شده", "Shade of the Sealed Aizen"),
        "enemies": [("زندانی موکن", "Muken Prisoner"), ("مهر بند سپاه کیدو", "Kidō Corps Seal"), ("نگهبان موکن", "Muken Warden")]},
    "dangai_rift": {"race": None, "boss": ("کوتوتسو، پاک‌کننده", "Kōtotsu, the Cleaner"),
        "enemies": [("کوریو، جریان مهارکننده", "Kōryū, the Restraining Current"), ("روح گرفتار کوریو", "Kōryū-Trapped Soul"), ("پژواک کوتوتسو", "Kōtotsu Echo")]},
    "schatten_depths": {"race": 'quincy', "boss": ("سایه‌ی یوهابخ", "Shadow of Yhwach"),
        "enemies": [("سولدات شاتن", "Schatten Soldat"), ("استرنریتر سایه‌گرد", "Shadow-Walking Sternritter"), ("محافظ شوتس‌اشتافل", "Schutzstaffel Guard")]},
    "zero_trial": {"race": None, "boss": ("پژواک ایچیبه هیوسوبه", "Echo of Ichibē Hyōsube"),
        "enemies": [("نگهبان نیروی صفر", "Squad Zero Sentinel"), ("پژواک نام‌های ایچیبه", "Echo of Ichibē's Names"), ("سایه‌ی کلید اوکن", "Ōken Key Shade")]},
    "hogyoku_vault": {"race": None, "boss": ("آیزنِ یکی‌شده با هوگیوکو", "Hōgyoku-Fused Aizen"),
        "enemies": [("پژواک آرزو", "Echo of a Wish"), ("توهم کیوکا سویگتسو", "Kyōka Suigetsu Illusion"), ("سایه‌ی پیله‌ی آیزن", "Aizen's Chrysalis Shade")]},
}
# Dungeons have a FIXED enemy level (DUNGEONS[id]["level"]) that does not follow the player's level.
# Difficulty only multiplies the enemies' strength (hp, attack, defense) and, in the same direction, the rewards:
#   DIFFICULTY = enemy power multiplier        DIFF_DROP = reward multiplier (items on a full clear; coins/XP already follow the power)
# Tune both here. Keep the keys in sync with DIFFS in data_items / data_crafting (one key per difficulty).
DIFFICULTY = {"normal": 1.0, "hard": 1.5, "nightmare": 3.0, "abyss": 8.0, "legendary": 16.0}  # legendary was x30: unwinnable
DIFF_DROP = {"normal": 1.0, "hard": 1.5, "nightmare": 3.0, "abyss": 10.0, "legendary": 30.0}
DIFF_FA = {"normal": "عادی", "hard": "سخت", "nightmare": "کابوس", "abyss": "ورطه", "legendary": "افسانه‌ای"}
