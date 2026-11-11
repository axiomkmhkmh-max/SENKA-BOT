"""Quests, quizzes, kido and transformation names."""
FORMS = {  # race -> (form1 fa/en, form2 fa/en)
    "shinigami": (("شیکای", "Shikai"), ("بانکای", "Bankai")), "quincy": (("هایلیگ بوگن", "Heilig Bogen"), ("وولشتاندیگ", "Vollständig")),
    "hollow": (("ریسوررکسیون", "Resurrección"), ("ریسوررکسیون کامل", "Full Resurrección")),
    "arrancar": (("ریسوررکسیون", "Resurrección"), ("ریسوررکسیون کامل", "Full Resurrección")),
    "fullbringer": (("فول‌برینگ", "Fullbring"), ("فول‌برینگ کامل", "Complete Fullbring")),
    "human": (("بیداری روح", "Soul Awakening"), ("اوج روح", "Soul Ascension")),
    "visored": (("ماسک هالو", "Hollow Mask"), ("ماسک پیشرفته", "Advanced Mask")),
}
# (stat multiplier, duration, fatigue turns, reiatsu pct) per form
FORM1 = (1.5, 6, 0, 0.20)
FORM2 = {"default": (3.0, 5, 3, 0.30), "hollow": (4.0, 4, 4, 0.30), "arrancar": (4.0, 4, 4, 0.30)}
FORM1_LEVEL, FORM2_LEVEL = 10, 30
# Bankai-level special effect per weapon type: (effect, power)
FORM2_EFFECT = {"melee": ("pierce", 0.25), "elemental": ("burn", 1), "kido": ("drain", 0.08), "illusion": ("miss", 0.30),
                "living": ("lifesteal", 0.20), "defensive": ("guard", 0.35), "ranged": ("double", 0.40),
                "speed": ("double", 0.50), "hybrid": ("pierce", 0.15)}
START_KIDO = {"had": [1], "bak": [1]}
RACE_START_KIDO = {"shinigami": {"had": [1, 4], "bak": [1]}, "quincy": {"had": [1, 4], "bak": [1]}}


def _q(i, cat, goal, n, xp, coins, fa, en, lvl=1):
    return {"_id": i, "quest_id": i, "cat": cat, "goal": goal, "count": n, "xp": xp, "coins": coins,
            "name_fa": fa, "name_en": en, "min_level": lvl}


QUESTS = [
    _q("m_first", "main", "explore", 1, 100, 100, "نخستین گام", "First Steps"),
    _q("m_battle", "main", "battle_win", 3, 200, 200, "آزمون نبرد", "Battle Trial"),
    _q("m_shop", "main", "market_buy", 1, 150, 100, "اولین خرید", "First Purchase", 5),
    _q("m_boss", "main", "boss_hit", 3, 400, 300, "ضربه به باس", "Strike the Boss", 5),
    _q("m_lvl10", "main", "level", 10, 600, 500, "رسیدن به لول ۱۰", "Reach Level 10"),
    _q("m_lvl30", "main", "level", 30, 3000, 3000, "رسیدن به لول ۳۰", "Reach Level 30", 10),
    _q("s_explore", "side", "explore", 25, 700, 500, "کاوشگر", "Pathfinder"),
    _q("s_gacha", "side", "gacha_pull", 5, 500, 400, "احضارگر", "Summoner"),
    _q("s_dungeon", "side", "dungeon_clear", 1, 800, 600, "دانجن‌گرد", "Dungeon Walker", 5),
    _q("s_mini", "side", "minigame_win", 5, 300, 300, "ذهن تیز", "Sharp Mind"),
    _q("r_pvp", "race", "pvp_win", 3, 900, 800, "رقیب جنگجو", "Rival Warrior", 15),
    _q("w_weapon", "weapon", "battle_win", 20, 1200, 900, "تسلط بر تیغه", "Blade Mastery", 10),
    _q("b_bankai", "bankai", "boss_hit", 25, 3500, 2500, "راه بانکای", "Path of Bankai", 30),
    _q("g_guild", "guild", "guild_deposit", 1, 400, 300, "کمک به جوخه", "Support the Squad", 20),
    _q("e_loot", "exploration", "explore", 100, 4000, 3000, "گنج‌یاب", "Treasure Seeker"),
    _q("l_legend", "legendary", "boss_kill", 10, 10000, 10000, "قاتل افسانه‌ها", "Legend Slayer", 40),
    _q("h_hidden", "hidden", "daily_claim", 7, 1500, 2000, "وفادار", "The Faithful"),
    _q("d_explore", "daily", "explore", 3, 150, 120, "گشت روزانه", "Daily Patrol"),
    _q("d_battle", "daily", "battle_win", 3, 200, 150, "شکار روزانه", "Daily Hunt"),
    _q("d_boss", "daily", "boss_hit", 2, 250, 200, "ضربه به باس", "Boss Strike"),
    _q("d_mini", "daily", "minigame_win", 2, 150, 120, "معمای روز", "Riddle of the Day"),
    _q("d_gacha", "daily", "gacha_pull", 1, 150, 150, "یک احضار", "A Summon"),
    _q("d_pvp", "daily", "pvp_win", 1, 300, 250, "دوئل روز", "Duel of the Day", 15),
    _q("d_market", "daily", "market_buy", 1, 150, 100, "خرید روز", "Shopper", 5),
    _q("w_explore", "weekly", "explore", 40, 1500, 1200, "گشت هفتگی", "Weekly Patrol"),
    _q("w_boss", "weekly", "boss_kill", 3, 2500, 2000, "شکار باس هفتگی", "Weekly Boss Hunt", 5),
    _q("w_battle", "weekly", "battle_win", 30, 2000, 1500, "هفته‌ی نبرد", "Battle Week"),
    _q("w_dungeon", "weekly", "dungeon_clear", 2, 2500, 2000, "دانجن هفتگی", "Weekly Dungeon", 5),
]
QUEST_BY_ID = {q["_id"]: q for q in QUESTS}
DAILY_POOL = [q["_id"] for q in QUESTS if q["cat"] == "daily"]

ZANP = [("Zangetsu", "زانگتسو", "Ichigo", "ایچیگو"), ("Senbonzakura", "سنبون‌زاکورا", "Byakuya", "بیاکویا"),
        ("Hyōrinmaru", "هیورینمارو", "Toshiro", "توشیرو"), ("Ryūjin Jakka", "ریوجین جاکا", "Yamamoto", "یاماموتو"),
        ("Benihime", "بنیهیمه", "Urahara", "اوراهارا"), ("Zabimaru", "زابیمارو", "Renji", "رنجی"),
        ("Kyōka Suigetsu", "کیوکا سویگتسو", "Aizen", "آیزن"), ("Katen Kyōkotsu", "کاتن کیوکوتسو", "Shunsui", "شونسویی"),
        ("Haineko", "هایِنکو", "Rangiku", "رانگیکو"), ("Sōgyo no Kotowari", "سوگیو نو کوتووَری", "Ukitake", "اوکیتاکه"),
        ("Sode no Shirayuki", "سوده نو شیرایوکی", "Rukia", "روکیا"), ("Suzumebachi", "سوزومه‌باچی", "Soi Fon", "سوی فون")]
KIDO_Q = [("Shakkahō", "شاکاهو", "had", 31), ("Sōkatsui", "سوکاتسوی", "had", 33), ("Byakurai", "بیاکورای", "had", 4),
          ("Shō", "شو", "had", 1), ("Sai", "سای", "bak", 1), ("Rikujōkōrō", "ریکوجوکورو", "bak", 61),
          ("Shitotsu Sansen", "شیتوتسو سانسن", "bak", 30)]
TRIVIA = [  # (fa q, en q, correct idx fa/en shared, options fa, options en)
    ("کاپیتان گروه ۱۱ گوتی ۱۳ کیست؟", "Who captains Squad 11?", 0, ["کنپاچی", "بیاکویا", "توشیرو", "یاماموتو"], ["Kenpachi", "Byakuya", "Toshiro", "Yamamoto"]),
    ("کاپیتان گروه ۶ کیست؟", "Who captains Squad 6?", 1, ["رنجی", "بیاکویا", "اوکیتاکه", "کنپاچی"], ["Renji", "Byakuya", "Ukitake", "Kenpachi"]),
    ("کاپیتان گروه ۱۰ کیست؟", "Who captains Squad 10?", 2, ["شونسویی", "ماییوری", "توشیرو", "کوماموتو"], ["Shunsui", "Mayuri", "Toshiro", "Komamura"]),
    ("کاپیتان گروه ۱ کیست؟", "Who captains Squad 1?", 3, ["ایچیگو", "گین", "کنپاچی", "یاماموتو"], ["Ichigo", "Gin", "Kenpachi", "Yamamoto"]),
    ("کاپیتان گروه ۱۳ کیست؟", "Who captains Squad 13?", 0, ["اوکیتاکه", "رنجی", "سوی فون", "اوراهارا"], ["Ukitake", "Renji", "Soi Fon", "Urahara"]),
    ("هالوهای قدرتمند در لاس‌نوچس چه نامیده می‌شوند؟", "What are the rulers of Las Noches called?", 2, ["کاپیتان", "استرنریتر", "اسپادا", "فراسیون"], ["Captain", "Sternritter", "Espada", "Fracción"]),
]


KIDO_NAMES = {("had", 1): "Shō", ("had", 4): "Byakurai", ("had", 31): "Shakkahō", ("had", 33): "Sōkatsui", ("had", 58): "Tenran",
              ("had", 63): "Raikōhō", ("had", 73): "Sōren Sōkatsui", ("had", 88): "Hiryūgekizoku Shinten Raihō", ("had", 90): "Kurohitsugi",
              ("bak", 1): "Sai", ("bak", 4): "Hainawa", ("bak", 9): "Geki", ("bak", 30): "Shitotsu Sansen", ("bak", 37): "Tsuribōshi",
              ("bak", 39): "Enkōsen", ("bak", 61): "Rikujōkōrō", ("bak", 62): "Hyapporankan", ("bak", 63): "Sajō Sabaku",
              ("bak", 73): "Tozanshō", ("bak", 81): "Danku", ("bak", 99): "Kin"}

LORE = {  # location -> [(fa, en)] original flavour lines
    "soul_society": [("پیرزنی در کوچه می‌گوید: «ریاتسو بیشتر از فولاد، دل می‌خواهد.»", "An old woman in the alley says: \"Reiatsu takes more heart than steel.\""),
                     ("بچه‌ی روحی شیرینی‌ات را می‌خواهد؛ می‌دهی و او مسیر میان‌بر را نشانت می‌دهد.", "A soul child begs for sweets and points out a shortcut through the district.")],
    "seireitei": [("سربازی زیر سایه‌ی دیوارهای سفید شایعه‌ی تغییر نگهبانی را زمزمه می‌کند.", "A guard whispers of a patrol change beneath the white walls."),
                  ("صدای تمرین از میدان گروه ۱۱ می‌آید؛ زمین زیر پایت می‌لرزد.", "Sparring echoes from the eleventh squad's yard; the ground trembles.")],
    "rukongai": [("بازارچه‌ی روکونگای پر از قصه است؛ فروشنده‌ای تکه‌ی ریشی کوچکی هدیه می‌دهد.", "The Rukongai market is full of tales; a vendor gifts you a tiny reishi shard."),
                 ("مردی کهنه‌پوش می‌گوید روزی شینیگامی بوده است.", "A ragged man claims he was once a Soul Reaper.")],
    "karakura": [("عطر نان از مغازه‌ی کوچکی می‌آید؛ هوای شهر از ریاتسو سنگین است.", "Bread scent drifts from a small shop; the town's air hums with reiatsu."),
                 ("گربه‌ای سیاه از روی دیوار نگاهت می‌کند، انگار بیش از آنچه باید می‌داند.", "A black cat watches from a wall as if it knows more than it should.")],
    "hueco_mundo": [("شن‌های سفید زیر ماه سرد زمزمه می‌کنند؛ فریادی دور از گیلیان‌ها می‌آید.", "White sands whisper beneath a cold moon; a distant Gillian wails."),
                    ("استخوان‌های عظیمی نیمه‌دفن شده‌اند؛ ردپایی تازه از ماسک‌دار روی شن است.", "Colossal bones lie half-buried; fresh Hollow tracks cross the dunes.")],
    "las_noches": [("راهروهای بی‌پایان کاخ از سکوتی سنگین پر است.", "The palace's endless halls are heavy with silence."),
                   ("نگهبانی بی‌حرکت ایستاده؛ ریاتسوی اسپادا از دورها حس می‌شود.", "A sentry stands motionless; an Espada's reiatsu presses from far away.")],
    "dangai": [("جریان‌های تاریک اطرافت می‌چرخند؛ ردیف نگهبانان کوملا از دور دیده می‌شود.", "Dark currents churn around you; the Kumo brood skitters in the distance."),
               ("زمان اینجا کند می‌شود؛ نجوای کسانی را می‌شنوی که هرگز بازنگشتند.", "Time slows here; you hear whispers of those who never returned.")],
    "wandenreich": [("ستاره‌های سفید بر ردای سربازان می‌درخشند؛ کمان‌ها تازه آماده شده‌اند.", "White stars gleam on soldiers' cloaks; their bows are freshly strung."),
                    ("آسمان اینجا بی‌ماه است؛ صلیب‌ها در تاریکی نورانی‌اند.", "The sky here has no moon; crosses glow in the dark.")],
    "royal_palace": [("تالارهای بی‌زمان از نور کهن روشن‌اند؛ اینجا قوانین دیگری حاکم است.", "Timeless halls glow with ancient light; other laws rule here."),
                     ("سایه‌ای از گذشته راهت را می‌بندد و آزمونت می‌کند.", "A shadow of the past bars your way and tests you.")],
    "soul_king": [("قلمرو شاه ارواح ساکت و بی‌انتهاست؛ ریاتسو مثل اقیانوس می‌تپد.", "The Soul King's realm is silent and endless; reiatsu beats like an ocean."),
                  ("بازتاب خودت از دور نگاهت می‌کند و لبخند می‌زند.", "Your own reflection watches from afar and smiles.")],
    "valley_screams": [("فریادهای بی‌صدا در دره می‌پیچد؛ هر سنگ حکایتی از جنگ دارد.", "Silent screams coil through the valley; every stone remembers war."),
                       ("مه رنگ‌پریده راه را می‌پوشاند؛ جنگجوی فراموش‌شده‌ای زیر آن می‌خندد.", "Pale mist veils the path; a forgotten warrior laughs beneath it.")],
}
