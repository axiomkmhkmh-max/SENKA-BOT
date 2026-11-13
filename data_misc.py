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
MASK_RAGE = 0.12  # per-turn chance a Visored loses control of an active Hollow Mask (lose that action)
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
    _q("m_first", "main", "explore", 1, 100, 100, "نخستین قدم در جهان ارواح", "First Step Into the Soul World"),
    _q("m_battle", "main", "battle_win", 3, 200, 200, "آزمون نخستین زخم", "Trial of the First Wound"),
    _q("m_shop", "main", "market_buy", 1, 150, 100, "بهای یک آرزو", "The Price of a Wish", 5),
    _q("m_boss", "main", "boss_hit", 3, 400, 300, "رویارویی با غول", "Face the Giant", 5),
    _q("m_lvl10", "main", "level", 10, 600, 500, "طعم شیکای", "A Taste of Shikai"),
    _q("m_lvl30", "main", "level", 30, 3000, 3000, "فراخوان بانکای", "Call of Bankai", 10),
    _q("s_explore", "side", "explore", 25, 700, 500, "ردپای ریاتسو", "Trail of Reiatsu"),
    _q("s_gacha", "side", "gacha_pull", 5, 500, 400, "ندای ارواح", "Call of the Spirits"),
    _q("s_dungeon", "side", "dungeon_clear", 1, 800, 600, "سقوط به اعماق", "Descent", 5),
    _q("s_mini", "side", "minigame_win", 5, 300, 300, "ذهن تیز، تیغ تیز", "Sharp Mind, Sharp Blade"),
    _q("r_pvp", "race", "pvp_win", 3, 900, 800, "غرور جنگجو", "A Warrior's Pride", 15),
    _q("w_weapon", "weapon", "battle_win", 20, 1200, 900, "هم‌نفسی با تیغه", "In Step With Your Blade", 10),
    _q("b_bankai", "bankai", "boss_hit", 25, 3500, 2500, "راه بانکای", "The Road to Bankai", 30),
    _q("g_guild", "guild", "guild_deposit", 1, 400, 300, "برادران شمشیر", "Sworn Comrades", 20),
    _q("e_loot", "exploration", "explore", 100, 4000, 3000, "جهان‌گرد", "World Walker"),
    _q("l_legend", "legendary", "boss_kill", 10, 10000, 10000, "قاتل افسانه‌ها", "Slayer of Legends", 40),
    _q("h_hidden", "hidden", "daily_claim", 7, 1500, 2000, "سوگند وفاداری", "Oath of the Faithful"),
    _q("d_explore", "daily", "explore", 3, 150, 120, "شکار شبانه", "Night Hunt"),
    _q("d_battle", "daily", "battle_win", 3, 200, 150, "شکار روز", "Day's Hunt"),
    _q("d_boss", "daily", "boss_hit", 2, 250, 200, "تماس با غول", "Touch of the Giant"),
    _q("d_mini", "daily", "minigame_win", 2, 150, 120, "معمای روز", "Riddle of the Day"),
    _q("d_gacha", "daily", "gacha_pull", 1, 150, 150, "یک فراخوان", "A Single Summon"),
    _q("d_pvp", "daily", "pvp_win", 1, 300, 250, "دوئل روز", "Duel of the Day", 15),
    _q("d_market", "daily", "market_buy", 1, 150, 100, "یک معامله", "A Fair Trade", 5),
    _q("w_explore", "weekly", "explore", 40, 1500, 1200, "شکار هفته", "Week's Hunt"),
    _q("w_boss", "weekly", "boss_kill", 3, 2500, 2000, "شکار بزرگ", "The Great Hunt", 5),
    _q("w_battle", "weekly", "battle_win", 30, 2000, 1500, "هفته‌ی شمشیر", "Week of the Sword"),
    _q("w_dungeon", "weekly", "dungeon_clear", 2, 2500, 2000, "دو سقوط", "Two Descents", 5),
]
QUEST_DESC = {'m_first': ('هر سفر با یک شکار شروع می\u200cشود.', 'Every journey begins with one hunt.'), 'm_battle': ('سه دشمن را بشکن؛ تیغه\u200cات باید بداند برای چه کشیده شده.', 'Defeat three foes. Your blade must learn why it was drawn.'), 'm_shop': ('از فروشگاه اوراهارا یا بازار چیزی بخر.', "Buy something from Urahara's shop or the market."), 'm_boss': ('سه ضربه به باس جهانی بزن؛ غول\u200cها هم خون دارند.', 'Land three hits on a world boss. Giants bleed too.'), 'm_lvl10': ('به سطح ۱۰ برس؛ تیغه\u200cات نامش را زمزمه می\u200cکند.', 'Reach level 10. Your blade will whisper its name.'), 'm_lvl30': ('به سطح ۳۰ برس؛ شکل نهایی بیدار می\u200cشود.', 'Reach level 30. The final form awakens.'), 's_explore': ('۲۵ بار شکار بزن و ردها را تا آخر دنبال کن.', 'Hunt 25 times and follow the traces to the end.'), 's_gacha': ('پنج بار ارواح را فرا بخوان.', 'Summon the spirits five times.'), 's_dungeon': ('یک دانجن را تا آخرین طبقه پاک کن.', 'Clear a dungeon to its last floor.'), 's_mini': ('پنج معمای درست؛ نبرد فقط با شمشیر نیست.', 'Five right answers. Battle is not only swordplay.'), 'r_pvp': ('سه دوئل را ببر؛ جنگجو بدون رقیب زنگ می\u200cزند.', 'Win three duels. A warrior without rivals rusts.'), 'w_weapon': ('با تیغه\u200cات ۲۰ نبرد را ببر؛ پیوندتان محکم می\u200cشود.', 'Win 20 battles with your blade. Your bond deepens.'), 'b_bankai': ('۲۵ ضربه به باس\u200cها؛ این قدرت با ترس نمی\u200cآید.', '25 hits on bosses. This power does not come with fear.'), 'g_guild': ('به بانک جوخه یا کلنت کمک کن.', 'Contribute to your squad or clan bank.'), 'e_loot': ('۱۰۰ شکار؛ هر گوشه\u200cی جهان را ببین.', '100 hunts. See every corner of the worlds.'), 'l_legend': ('۱۰ باس را از پا درآور و نامت را بر دیوار حک کن.', 'Bring down 10 bosses and carve your name on the wall.'), 'h_hidden': ('۷ بار هدیه\u200cی روزانه؛ بازشکارن هم نوعی قدرت است.', 'Claim the daily gift 7 times. Returning is a kind of strength.'), 'd_explore': ('سه بار شکار بزن.', 'Hunt three times.'), 'd_battle': ('سه دشمن را شکست بده.', 'Defeat three enemies.'), 'd_boss': ('دو ضربه به باس بزن.', 'Strike a boss twice.'), 'd_mini': ('دو معما را درست جواب بده.', 'Answer two riddles correctly.'), 'd_gacha': ('یک بار ارواح را فرا بخوان.', 'Call upon the spirits once.'), 'd_pvp': ('یک دوئل را ببر.', 'Win a duel.'), 'd_market': ('یک خرید از بازار.', 'Make a purchase at the market.'), 'w_explore': ('۴۰ شکار در یک هفته.', '40 hunts in a week.'), 'w_boss': ('سه باس را بکش.', 'Kill three bosses.'), 'w_battle': ('۳۰ نبرد را ببر.', 'Win 30 battles.'), 'w_dungeon': ('دو دانجن را پاک کن.', 'Clear two dungeons.')}
for _x in QUESTS:
    _x["desc_fa"], _x["desc_en"] = QUEST_DESC[_x["_id"]]
QUEST_BY_ID = {q["_id"]: q for q in QUESTS}
DAILY_POOL = [q["_id"] for q in QUESTS if q["cat"] == "daily"]

ZANP = [("Zangetsu", "زانگتسو", "Ichigo", "ایچیگو"), ("Senbonzakura", "سنبون‌زاکورا", "Byakuya", "بیاکویا"),
        ("Hyōrinmaru", "هیورینمارو", "Toshiro", "توشیرو"), ("Ryūjin Jakka", "ریوجین جاکا", "Yamamoto", "یاماموتو"),
        ("Benihime", "بنیهیمه", "Urahara", "اوراهارا"), ("Zabimaru", "زابیمارو", "Renji", "رنجی"),
        ("Kyōka Suigetsu", "کیوکا سویگتسو", "Aizen", "آیزن"), ("Katen Kyōkotsu", "کاتن کیوکوتسو", "Shunsui", "شونسویی"),
        ("Haineko", "هایِنکو", "Rangiku", "رانگیکو"), ("Sōgyo no Kotowari", "سوگیو نو کوتووَری", "Ukitake", "اوکیتاکه"),
        ("Sode no Shirayuki", "سوده نو شیرایوکی", "Rukia", "روکیا"), ("Suzumebachi", "سوزومه‌باچی", "Soi Fon", "سوی فون"),
        ("Nozarashi", "نوزاراشی", "Kenpachi", "کنپاچی"), ("Kazeshini", "کازه‌شینی", "Hisagi", "هیساگی"),
        ("Tobiume", "توبیومه", "Momo", "مومو"), ("Shinsō", "شینسو", "Gin", "گین"),
        ("Wabisuke", "وابی‌سوکه", "Kira", "کیرا"), ("Hōzukimaru", "هوزوکی‌مارو", "Ikkaku", "ایککاکو")]
KIDO_Q = [("Shakkahō", "شاکاهو", "had", 31), ("Sōkatsui", "سوکاتسوی", "had", 33), ("Byakurai", "بیاکورای", "had", 4),
          ("Shō", "شو", "had", 1), ("Sai", "سای", "bak", 1), ("Rikujōkōrō", "ریکوجوکورو", "bak", 61),
          ("Shitotsu Sansen", "شیتوتسو سانسن", "bak", 30), ("Kurohitsugi", "کوروهیتسوگی", "had", 90),
          ("Danku", "دانکو", "bak", 81), ("Tsuribōshi", "تسوریبوشی", "bak", 37)]
KIDO_NUM_POOL = [1, 4, 30, 31, 33, 37, 61, 63, 73, 81, 90, 99]
TRIVIA = [  # (fa q, en q, correct idx fa/en shared, options fa, options en)
    ("کاپیتان گروه ۱۱ گوتی ۱۳ کیست؟", "Who captains Squad 11?", 0, ["کنپاچی", "بیاکویا", "توشیرو", "یاماموتو"], ["Kenpachi", "Byakuya", "Toshiro", "Yamamoto"]),
    ("کاپیتان گروه ۶ کیست؟", "Who captains Squad 6?", 1, ["رنجی", "بیاکویا", "اوکیتاکه", "کنپاچی"], ["Renji", "Byakuya", "Ukitake", "Kenpachi"]),
    ("کاپیتان گروه ۱۰ کیست؟", "Who captains Squad 10?", 2, ["شونسویی", "ماییوری", "توشیرو", "کوماموتو"], ["Shunsui", "Mayuri", "Toshiro", "Komamura"]),
    ("کاپیتان گروه ۱ کیست؟", "Who captains Squad 1?", 3, ["ایچیگو", "گین", "کنپاچی", "یاماموتو"], ["Ichigo", "Gin", "Kenpachi", "Yamamoto"]),
    ("کاپیتان گروه ۱۳ کیست؟", "Who captains Squad 13?", 0, ["اوکیتاکه", "رنجی", "سوی فون", "اوراهارا"], ["Ukitake", "Renji", "Soi Fon", "Urahara"]),
    ("هالوهای قدرتمند در لاس‌نوچس چه نامیده می‌شوند؟", "What are the rulers of Las Noches called?", 2, ["کاپیتان", "استرنریتر", "اسپادا", "فراسیون"], ["Captain", "Sternritter", "Espada", "Fracción"]),
    ("کاپیتان گروه ۱۲، دانشمند دیوانه‌ی گوتی، کیست؟", "Who captains Squad 12, the Gotei's mad scientist?", 0, ["ماییوری", "سوی فون", "اونوهانا", "توسن"], ["Mayuri", "Soi Fon", "Unohana", "Tosen"]),
    ("کاپیتان گروه ۲ و فرمانده‌ی نیروی ویژه کیست؟", "Who captains Squad 2 and leads the covert forces?", 1, ["رانگیکو", "سوی فون", "یورویچی", "کنپاچی"], ["Rangiku", "Soi Fon", "Yoruichi", "Kenpachi"]),
    ("کاپیتان گروه ۸ که کلاه حصیری روی دوش دارد کیست؟", "Who captains Squad 8, the one with the straw hat?", 2, ["یاماموتو", "کوماموتو", "شونسویی", "آیزن"], ["Yamamoto", "Komamura", "Shunsui", "Aizen"]),
    ("شماره‌ی کواترو، چهارمین اسپادا، با کیست؟", "Which Espada holds the number 4 (Cuatro)?", 1, ["گریمجو", "اولکیورا", "نوایترا", "استارک"], ["Grimmjow", "Ulquiorra", "Nnoitra", "Starrk"]),
    ("نخستین اسپادا کیست؟", "Who is the first Espada?", 1, ["باراگان", "استارک", "هریبل", "آیزن"], ["Baraggan", "Starrk", "Harribel", "Aizen"]),
    ("خالق هوگیوکو کیست؟", "Who created the Hōgyoku?", 1, ["آیزن", "اوراهارا", "ماییوری", "یوهابخ"], ["Aizen", "Urahara", "Mayuri", "Yhwach"]),
    ("پادشاه وندن‌رایش کیست؟", "Who is the king of the Wandenreich?", 1, ["جوگرام", "یوهابخ", "گینجو", "اوریو"], ["Jugram", "Yhwach", "Ginjo", "Uryu"]),
    ("نام بانکای ایچیگو چیست؟", "What is the name of Ichigo's Bankai?", 0, ["تنسا زانگتسو", "سنبون‌زاکورا کاگه‌یوشی", "دایگورن هیورینمارو", "زابیمارو هیهیو"], ["Tensa Zangetsu", "Senbonzakura Kageyoshi", "Daiguren Hyōrinmaru", "Zabimaru Hihio"]),
    ("بانکای توشیرو چه نام دارد؟", "What is Toshiro's Bankai called?", 2, ["تنسا زانگتسو", "کوکوجو تنگن", "دایگورن هیورینمارو", "رِنبو زابیمارو"], ["Tensa Zangetsu", "Kokujō Tengen", "Daiguren Hyōrinmaru", "Renbu Zabimaru"]),
    ("مراسم فرستادن روح به سول‌سوسایتی چه نام دارد؟", "What is the rite that sends a soul to Soul Society?", 0, ["کونسو", "گارگانتا", "بانکای", "سونیدو"], ["Konsō", "Garganta", "Bankai", "Sonído"]),
    ("تکنیک حرکت سریع کوئینسی‌ها چه نام دارد؟", "What is the Quincy flash-step technique called?", 2, ["شونپو", "سونیدو", "هیرنکیاکو", "باکودو"], ["Shunpo", "Sonído", "Hirenkyaku", "Bakudō"]),
    ("دروازه‌ی میان هوئکو موندو و جهان‌های دیگر چه نام دارد؟", "What is the gate that tears open between Hueco Mundo and other worlds?", 1, ["سنکایمون", "گارگانتا", "دنگای", "روکونگای"], ["Senkaimon", "Garganta", "Dangai", "Rukongai"]),
    ("کاپیتان گروه ۵ که به همه خیانت کرد کیست؟", "Which Squad 5 captain betrayed everyone?", 0, ["آیزن", "گین", "توسن", "کیرا"], ["Aizen", "Gin", "Tosen", "Kira"]),
    ("کاپیتان گروه ۹ که به آیزن پیوست کیست؟", "Which Squad 9 captain followed Aizen?", 2, ["گین", "شینجی", "توسن", "کوماموتو"], ["Gin", "Shinji", "Tosen", "Komamura"]),
    ("باکودو چه نوع کیدویی است؟", "What kind of kidō is Bakudō?", 1, ["حمله‌ی مستقیم", "بند و دفاع", "احضار", "شفا"], ["Direct attack", "Binding and defense", "Summoning", "Healing"]),
    ("هادو چه نوع کیدویی است؟", "What kind of kidō is Hadō?", 0, ["تخریبی و تهاجمی", "بند و دفاع", "پنهان‌سازی", "شفا"], ["Destructive and offensive", "Binding and defense", "Concealment", "Healing"]),
    ("چشم‌بند کنپاچی چه می‌کند؟", "What does Kenpachi's eyepatch do?", 2, ["بینایی‌اش را تیز می‌کند", "زخمش را می‌پوشاند", "ریاتسویش را فرو می‌نشاند", "زانپاکتویش را مهر می‌کند"], ["Sharpens his sight", "Covers a wound", "Suppresses his reiatsu", "Seals his zanpakuto"]),
    ("چه کسی قدرت شینیگامی را به ایچیگو داد؟", "Who passed Shinigami powers to Ichigo?", 0, ["روکیا", "اوراهارا", "رنجی", "یورویچی"], ["Rukia", "Urahara", "Renji", "Yoruichi"]),
    ("هالو پس از گیلیان به چه تبدیل می‌شود؟", "A Gillian evolves into what?", 0, ["آجوکاس", "واستو لورد", "آرانکار", "فراسیون"], ["Adjuchas", "Vasto Lorde", "Arrancar", "Fracción"]),
    ("کدام ماده ریاتسو را خنثی می‌کند و دیوارهای سیرایتی را می‌سازد؟", "Which stone nullifies reiatsu and forms Seireitei's walls?", 0, ["سکی‌سکی", "ریشی", "هوگیوکو", "گیگای"], ["Sekkiseki", "Reishi", "Hōgyoku", "Gigai"]),
]


KIDO_NAMES = {("had", 1): "Shō", ("had", 4): "Byakurai", ("had", 31): "Shakkahō", ("had", 33): "Sōkatsui", ("had", 58): "Tenran",
              ("had", 63): "Raikōhō", ("had", 73): "Sōren Sōkatsui", ("had", 88): "Hiryūgekizoku Shinten Raihō", ("had", 90): "Kurohitsugi",
              ("bak", 1): "Sai", ("bak", 4): "Hainawa", ("bak", 9): "Geki", ("bak", 30): "Shitotsu Sansen", ("bak", 37): "Tsuribōshi",
              ("bak", 39): "Enkōsen", ("bak", 61): "Rikujōkōrō", ("bak", 62): "Hyapporankan", ("bak", 63): "Sajō Sabaku",
              ("bak", 73): "Tozanshō", ("bak", 81): "Danku", ("bak", 99): "Kin"}


LOC_DESC = {  # location -> (fa, en) one-line atmosphere
    'soul_society': ('شهر ارواح؛ جایی که مرگ آغاز است، نه پایان.', 'City of souls, where death is a beginning, not an end.'),
    'seireitei': ('دیوارهای سفید، کاپیتان\u200cها، و سکوتی که وزن دارد.', 'White walls, captains, and a silence that carries weight.'),
    'rukongai': ('کوچه\u200cهای بی\u200cنام؛ اینجا همه\u200cچیز را باید با دندان نگه داشت.', 'Nameless streets where you hold everything with your teeth.'),
    'karakura': ('شهری معمولی که ریاتسو در هوایش نفس می\u200cکشد.', 'An ordinary town whose air breathes reiatsu.'),
    'hueco_mundo': ('شن سفید، ماهی همیشگی و گرسنگی بی\u200cپایان.', 'White sand, a permanent moon, and endless hunger.'),
    'las_noches': ('قصر سنگی اسپادا؛ هر راهرو یک پرسش مرگبار است.', "The Espada's stone palace, where every hall asks a deadly question."),
    'dangai': ('گذرگاه میان جهان\u200cها؛ زمان اینجا اعتباری ندارد.', 'The passage between worlds, where time holds no credit.'),
    'wandenreich': ('امپراتوری بی\u200cماه؛ ستاره\u200cها اینجا سلاح\u200cاند.', 'The moonless empire, where stars are weapons.'),
    'royal_palace': ('قلمرو اصل\u200cها؛ تنها لایق از آستانه می\u200cگذرد.', 'Realm of origins; only the worthy cross its threshold.'),
    'soul_king': ('قلب جهان؛ هر ریاتسو از اینجا آغاز می\u200cشود.', 'The heart of the worlds, where all reiatsu begins.'),
    'valley_screams': ('دره\u200cای که جنگ\u200cهای فراموش\u200cشده در آن هنوز زنده\u200cاند.', 'A valley where forgotten wars are still alive.'),
}


# ---- extra Bleach locations: atmosphere + lore ----
LOC_DESC.update({
    "zaraki_district": ("جایی که حتی هالوها از ترس راه کنار می‌روند؛ فقط قوی‌ترین زنده می‌ماند.", "Where even Hollows step aside; only the strongest survive."),
    "sokyoku_hill": ("تپه‌ای بلند زیر آسمان سرد؛ هوا بوی سرنوشت می‌دهد.", "A high hill under a cold sky; the air smells of fate."),
    "forest_menos": ("درخت‌هایی از استخوان و شن زیر ماه؛ هر سایه می‌تواند منوس باشد.", "Trees of bone and sand beneath the moon; every shadow may be a Menos."),
    "fake_karakura": ("شهری که روی نقشه است ولی واقعی نیست؛ جنگی بزرگ پیش رو دارد.", "A town on the map but not real; a great war lies ahead."),
    "silbern_palace": ("کاخ سفید و بی‌صدا؛ هر پله‌اش به‌اندازه‌ی یک عمر ریاتسو سنگین است.", "A white, silent palace; every step weighs a lifetime of reiatsu."),
})


# ---- Bleach content pack 2: atmosphere + lore for the new locations ----
LOC_DESC.update({
    "shinigami_academy": ("سالن‌های چوبی و صدای تیغه‌های تمرینی؛ هر شینیگامی از اینجا شروع کرده.", "Wooden halls and the clatter of practice blades; every Soul Reaper starts here."),
    "inuzuri": ("محله‌ای که نان را با پنجه باید نگه داشت؛ دوستی اینجا گران‌بهاترین کالاست.", "A district where bread is held with claws; friendship is the costliest commodity."),
    "urahara_training": ("غاری بی‌سقف زیر فروشگاه؛ آسمانش نقاشی است ولی ضربه‌هایش واقعی.", "A roofless cavern beneath the shop; its sky is painted but the blows are real."),
    "senzaikyu": ("برجی سفید در دل سیرایتی؛ سکوتش از دیوارهایش سنگین‌تر است.", "A white tower at the heart of Seireitei; its silence is heavier than its walls."),
    "maggot_nest": ("زندانی عمیق برای خطرناک‌ترین‌ها؛ تاریکی‌اش خودش نگهبان است.", "A deep prison for the most dangerous; its darkness is a guard in itself."),
    "garganta_tunnel": ("گذرگاهی تاریک میان جهان‌ها؛ دیواره‌اش نفس می‌کشد.", "A dark corridor between worlds; its walls breathe."),
    "muken": ("زندان بی‌پایان در اعماق؛ زمان اینجا فقط تکرار می‌شود.", "An endless prison in the depths; time here only repeats."),
})

# ---- Bleach content pack 3: atmosphere + lore for the new locations ----
LOC_DESC.update({
    "kurosaki_clinic": ("کلینیکی کوچک با چراغ همیشه روشن؛ شبانه، بیمارانش همیشه انسان نیستند.", "A small clinic with a lamp always lit; at night, not every patient is human."),
    "seireitei_gate": ("دروازه‌ای که از آن بالاتر راهی نیست؛ گذر از آن یعنی رسیدن یا مردن.", "A gate with no road beyond it; to cross is to arrive or to fall."),
    "kuchiki_manor": ("باغی بی‌نقص و دیوارهایی بی‌صدا؛ غرور اینجا با سنگ ساخته شده.", "A flawless garden and silent walls; pride here is built of stone."),
    "shiba_estate": ("خانه‌ای که آتش‌بازی را به هنر و جنگ را به جشن تبدیل می‌کند.", "A house that turns fireworks into art and war into festival."),
    "visored_warehouse": ("انباری قدیمی با ماسک‌هایی که نگاهت می‌کنند؛ تمرین اینجا دو رو دارد.", "An old warehouse with masks that watch you; training here has two faces."),
    "research_institute": ("آزمایشگاهی که پرسش را بر جان مقدم می‌دارد؛ نمونه‌ها هنوز نفس می‌کشند.", "A laboratory that puts the question before the life; its specimens still breathe."),
    "las_noches_throne": ("تالاری که تاجش را از شن ساخته‌اند؛ هر ستون یک خواسته‌ی برآورده‌نشده است.", "A hall whose crown is made of sand; every pillar is an unfulfilled wish."),
    "schatten_bereich": ("جهان سایه‌ی امپراتور؛ ستاره‌ها اینجا روی زمین می‌افتند.", "The Emperor's shadow-world; here the stars fall to the ground."),
})

# ---- Bleach content pack 4: atmosphere + lore ----
LOC_DESC.update({
    "junrinan": ("اولین محله‌ی روکونگای؛ جایی که هر سفر پس از مرگ آغاز می‌شود.", "The first district of Rukongai, where every journey after death begins."),
    "karakura_high": ("راهروهای ساکت، کلاس‌های خالی و ریاتسویی که از دیوار می‌چکد.", "Quiet halls, empty classrooms, and reiatsu dripping from the walls."),
    "urahara_shop": ("مغازه‌ای کوچک که هرچه می‌خواهی در آن هست، به‌جز پاسخ سؤال‌هایت.", "A small shop with everything you want except answers to your questions."),
    "relief_station": ("بوی گیاهان دارویی و سکوتی که می‌خواهد زخم‌ها را بخواباند.", "The smell of herbs and a silence that tries to put wounds to sleep."),
    "captains_hall": ("تالاری که فرمان‌ها در آن می‌افتند و جهان‌ها تصمیم‌شان را می‌گیرند.", "A hall where orders are given and worlds make up their minds."),
    "jigoku": ("دوزخ؛ زنجیر و شعله، و ردی از خندهی گناهان کهنه.", "Hell: chains, flame, and the faint laugh of old sins."),
    "sternritter_hall": ("تالاری از نور سرد؛ هر ستاره‌ی روی دیوار نامی دارد.", "A hall of cold light; every star on the wall bears a name."),
    "hogyoku_chamber": ("بلوری در میانه‌ی اتاق می‌تپد؛ هر خواسته‌ای را می‌شنود و هیچ‌کدام را رایگان برآورده نمی‌کند.", "A crystal pulses in the middle of the room; it hears every wish and grants none for free."),
})

# ---- Bleach content pack 5: atmosphere + lore ----
LOC_DESC.update({
    "riverbank": ("آب آرام می‌گذرد، مه روی آن می‌نشیند و کسی در آن‌سوی مه منتظر است.", "The water runs slowly, mist settles on it, and someone waits on the far side."),
    "kusajishi_district": ("محله‌ای که نامش از یک کودک مانده و کودکانش از جنگ.", "A district named for a child, and full of children shaped by war."),
    "bount_mansion": ("پنجره‌ها همیشه روشن‌اند و ساعت‌ها هیچ‌وقت زمان را درست نشان نمی‌دهند.", "The windows are always lit and the clocks never agree on the time."),
    "xcution_hideout": ("پناهگاهی که از دست‌دادن‌ها ساخته شده؛ هر اتاق یک گمشده دارد.", "A hideout built from losses; every room is missing someone."),
    "orihime_chamber": ("اتاقی سفید با پنجره‌ای که ماه را به‌اندازه‌ی یک زندان نشان می‌دهد.", "A white room whose window shows the moon at the size of a prison."),
    "precipice_world": ("دالانی که زیر پایت می‌دود و پشت سرت می‌بلعد.", "A corridor that runs beneath you and devours behind you."),
    "seireitei_ruins": ("دیوارهای سفید ترک خورده‌اند و در هر ترک، سایه‌ای نشسته است.", "The white walls have cracked, and a shadow sits in every crack."),
    "zero_division_hall": ("تالاری که هیچ‌کس را به نام نمی‌خواند؛ فقط نگاه می‌کند.", "A hall that calls no one by name; it only watches."),
})

# ---- named Hadō / Bakudō spells (names only; card ids and effects never change) ----
KIDO_NAMES.update({("had", 11): "Tsuzuri Raiden", ("had", 12): "Fushibi", ("had", 32): "Ōkasen", ("had", 54): "Haien",
                   ("had", 91): "Senju Kōtenkan", ("had", 96): "Ittō Kasō",
                   ("bak", 21): "Sekienton", ("bak", 26): "Kyokkō", ("bak", 58): "Kakushitsuijaku", ("bak", 75): "Gochūtekkan"})
# ---- pack 3: three more named spells ----
KIDO_NAMES.update({("bak", 8): "Seki", ("bak", 77): "Tenteikūra", ("had", 78): "Zangeki"})
# ---- pack 5: one more named spell ----
KIDO_NAMES.update({("had", 57): "Daichi Tenyō"})
