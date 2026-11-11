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
    _q("d_explore", "daily", "explore", 3, 150, 120, "گشت شبانه", "Night Patrol"),
    _q("d_battle", "daily", "battle_win", 3, 200, 150, "شکار روز", "Day's Hunt"),
    _q("d_boss", "daily", "boss_hit", 2, 250, 200, "تماس با غول", "Touch of the Giant"),
    _q("d_mini", "daily", "minigame_win", 2, 150, 120, "معمای روز", "Riddle of the Day"),
    _q("d_gacha", "daily", "gacha_pull", 1, 150, 150, "یک فراخوان", "A Single Summon"),
    _q("d_pvp", "daily", "pvp_win", 1, 300, 250, "دوئل روز", "Duel of the Day", 15),
    _q("d_market", "daily", "market_buy", 1, 150, 100, "یک معامله", "A Fair Trade", 5),
    _q("w_explore", "weekly", "explore", 40, 1500, 1200, "پاترول هفته", "Week's Patrol"),
    _q("w_boss", "weekly", "boss_kill", 3, 2500, 2000, "شکار بزرگ", "The Great Hunt", 5),
    _q("w_battle", "weekly", "battle_win", 30, 2000, 1500, "هفته‌ی شمشیر", "Week of the Sword"),
    _q("w_dungeon", "weekly", "dungeon_clear", 2, 2500, 2000, "دو سقوط", "Two Descents", 5),
]
QUEST_DESC = {'m_first': ('هر سفر با یک گشت شروع می\u200cشود.', 'Every journey begins with one patrol.'), 'm_battle': ('سه دشمن را بشکن؛ تیغه\u200cات باید بداند برای چه کشیده شده.', 'Defeat three foes. Your blade must learn why it was drawn.'), 'm_shop': ('از فروشگاه اوراهارا یا بازار چیزی بخر.', "Buy something from Urahara's shop or the market."), 'm_boss': ('سه ضربه به باس جهانی بزن؛ غول\u200cها هم خون دارند.', 'Land three hits on a world boss. Giants bleed too.'), 'm_lvl10': ('به سطح ۱۰ برس؛ تیغه\u200cات نامش را زمزمه می\u200cکند.', 'Reach level 10. Your blade will whisper its name.'), 'm_lvl30': ('به سطح ۳۰ برس؛ شکل نهایی بیدار می\u200cشود.', 'Reach level 30. The final form awakens.'), 's_explore': ('۲۵ بار گشت بزن و ردها را تا آخر دنبال کن.', 'Patrol 25 times and follow the traces to the end.'), 's_gacha': ('پنج بار ارواح را فرا بخوان.', 'Summon the spirits five times.'), 's_dungeon': ('یک دانجن را تا آخرین طبقه پاک کن.', 'Clear a dungeon to its last floor.'), 's_mini': ('پنج معمای درست؛ نبرد فقط با شمشیر نیست.', 'Five right answers. Battle is not only swordplay.'), 'r_pvp': ('سه دوئل را ببر؛ جنگجو بدون رقیب زنگ می\u200cزند.', 'Win three duels. A warrior without rivals rusts.'), 'w_weapon': ('با تیغه\u200cات ۲۰ نبرد را ببر؛ پیوندتان محکم می\u200cشود.', 'Win 20 battles with your blade. Your bond deepens.'), 'b_bankai': ('۲۵ ضربه به باس\u200cها؛ این قدرت با ترس نمی\u200cآید.', '25 hits on bosses. This power does not come with fear.'), 'g_guild': ('به بانک جوخه یا کلنت کمک کن.', 'Contribute to your squad or clan bank.'), 'e_loot': ('۱۰۰ گشت؛ هر گوشه\u200cی جهان را ببین.', '100 patrols. See every corner of the worlds.'), 'l_legend': ('۱۰ باس را از پا درآور و نامت را بر دیوار حک کن.', 'Bring down 10 bosses and carve your name on the wall.'), 'h_hidden': ('۷ بار هدیه\u200cی روزانه؛ بازگشتن هم نوعی قدرت است.', 'Claim the daily gift 7 times. Returning is a kind of strength.'), 'd_explore': ('سه بار گشت بزن.', 'Patrol three times.'), 'd_battle': ('سه دشمن را شکست بده.', 'Defeat three enemies.'), 'd_boss': ('دو ضربه به باس بزن.', 'Strike a boss twice.'), 'd_mini': ('دو معما را درست جواب بده.', 'Answer two riddles correctly.'), 'd_gacha': ('یک بار ارواح را فرا بخوان.', 'Call upon the spirits once.'), 'd_pvp': ('یک دوئل را ببر.', 'Win a duel.'), 'd_market': ('یک خرید از بازار.', 'Make a purchase at the market.'), 'w_explore': ('۴۰ گشت در یک هفته.', '40 patrols in a week.'), 'w_boss': ('سه باس را بکش.', 'Kill three bosses.'), 'w_battle': ('۳۰ نبرد را ببر.', 'Win 30 battles.'), 'w_dungeon': ('دو دانجن را پاک کن.', 'Clear two dungeons.')}
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

LORE = {  # location -> [(fa, en)] original flavour lines
    'soul_society': [
        ('پیرزنی در کوچه می\u200cگوید: «ریاتسو بیشتر از فولاد، دل می\u200cخواهد.»', 'An old woman in the alley says: “Reiatsu takes more heart than steel.”'),
        ('بچه\u200cی روحی شیرینی\u200cات را می\u200cخواهد؛ می\u200cدهی و او مسیر میان\u200cبر را نشانت می\u200cدهد.', 'A soul child begs for sweets and points out a shortcut through the district.'),
        ('اینجا هیچ\u200cکس گرسنه نمی\u200cشود، با این\u200cهمه همه\u200cجا بوی نان است. شاید یادآوری چیزی که از دست رفته.', 'No one starves here, yet bread scent hangs everywhere. Maybe it is memory of what was lost.'),
        ('فانوسی بی\u200cشعله روی سردرِ دکانی می\u200cسوزد. می\u200cگویند روحِ صاحبش هنوز منتظر است.', "A flameless lantern burns over a shop door. They say its owner's soul is still waiting."),
        ('ماه بالای سرت نیم\u200cروشن است؛ مرگ اینجا پایان نیست، فقط پرده\u200cی دوم.', 'The moon overhead is half-lit. Death here is not an ending, only the second act.'),
    ],
    'seireitei': [
        ('سربازی زیر سایه\u200cی دیوارهای سفید شایعه\u200cی تغییر نگهبانی را زمزمه می\u200cکند.', 'A guard whispers of a patrol change beneath the white walls.'),
        ('صدای تمرین از میدان گروه ۱۱ می\u200cآید؛ زمین زیر پایت می\u200cلرزد.', "Sparring echoes from the eleventh squad's yard; the ground trembles."),
        ('بوی چای از دفتر گروه ۱۳ می\u200cآید. حتی اینجا کسی هست که آرامش را از جنگ بیشتر دوست دارد.', "Tea drifts from Squad 13's office. Even here, someone prefers peace to war."),
        ('هائوریِ سفیدِ کاپیتانی از دور می\u200cگذرد. ریاتسویش مثل وزنه\u200cای نامرئی روی شانه\u200cات می\u200cنشیند.', "A captain's white haori passes in the distance. His reiatsu settles on your shoulders like unseen weight."),
        ('پشت یکی از دیوارها نقش یک تیغه\u200cی شکسته حک شده. کسی می\u200cخواهد یادش بماند.', 'Behind one wall, a broken blade is carved. Someone wanted it remembered.'),
    ],
    'rukongai': [
        ('بازارچه\u200cی روکونگای پر از قصه است؛ فروشنده\u200cای تکه\u200cی ریشی کوچکی هدیه می\u200cدهد.', 'The Rukongai market is full of tales; a vendor gifts you a tiny reishi shard.'),
        ('مردی کهنه\u200cپوش می\u200cگوید روزی شینیگامی بوده است.', 'A ragged man claims he was once a Soul Reaper.'),
        ('کودکی با تکه\u200cای چوب شمشیربازی می\u200cکند. چشم\u200cهایش از هر تیغه\u200cای تیزترند.', 'A child fences with a stick. Their eyes are sharper than any blade.'),
        ('زنی سه سکه\u200cی مسی در کفت می\u200cگذارد: «بگیر. فردا شاید نباشم.» و می\u200cرود.', 'A woman presses three copper coins into your hand: “Take them. Tomorrow I may not be here.” She leaves.'),
        ('در دوردست، دودِ کوره\u200cای می\u200cپیچد. روکونگای از ناچیزی قوی می\u200cسازد.', 'Smoke from a distant forge curls upward. Rukongai makes strength out of nothing.'),
    ],
    'karakura': [
        ('عطر نان از مغازه\u200cی کوچکی می\u200cآید؛ هوای شهر از ریاتسو سنگین است.', "Bread scent drifts from a small shop; the town's air hums with reiatsu."),
        ('گربه\u200cای سیاه از روی دیوار نگاهت می\u200cکند، انگار بیش از آنچه باید می\u200cداند.', 'A black cat watches from a wall as if it knows more than it should.'),
        ('غروب پشت\u200cبام\u200cها را نارنجی می\u200cکند. کسی در دوردست سایه\u200cی هالویی را دنبال می\u200cکند.', "Dusk turns the rooftops orange. Someone far off tracks a Hollow's shadow."),
        ('مغازه\u200cای قدیمی با تابلوی کج؛ پشت درش صدای خنده\u200cی مردی می\u200cآید که همیشه بیش از آنچه می\u200cگوید می\u200cداند.', 'An old shop with a crooked sign; behind its door, laughter from a man who always knows more than he says.'),
        ('بچه\u200cها در پارک بازی می\u200cکنند، بی\u200cخبر از ارواحی که میان\u200cشان نشسته\u200cاند و تماشا می\u200cکنند.', 'Children play in the park, unaware of the spirits sitting among them, watching.'),
    ],
    'hueco_mundo': [
        ('شن\u200cهای سفید زیر ماه سرد زمزمه می\u200cکنند؛ فریادی دور از گیلیان\u200cها می\u200cآید.', 'White sands whisper beneath a cold moon; a distant Gillian wails.'),
        ('استخوان\u200cهای عظیمی نیمه\u200cدفن شده\u200cاند؛ ردپایی تازه از ماسک\u200cدار روی شن است.', 'Colossal bones lie half-buried; fresh Hollow tracks cross the dunes.'),
        ('آسمان همیشه شب است. اینجا امید را هم باید مثل ریاتسو از درون خودت بکشی.', 'The sky is always night. Here, even hope must be drawn from within, like reiatsu.'),
        ('درختی سفید و بی\u200cبرگ از شن بیرون زده؛ تنها نشانه\u200cی زندگی تا هر جا که چشم کار کند.', 'A bare white tree rises from the sand, the only sign of life as far as the eye can see.'),
        ('هالویی بی\u200cماسک روی تپه ایستاده و فقط نگاهت می\u200cکند؛ نه حمله می\u200cکند، نه می\u200cرود.', 'A maskless Hollow stands on a dune and merely watches. It neither attacks nor leaves.'),
    ],
    'las_noches': [
        ('راهروهای بی\u200cپایان کاخ از سکوتی سنگین پر است.', "The palace's endless halls are heavy with silence."),
        ('نگهبانی بی\u200cحرکت ایستاده؛ ریاتسوی اسپادا از دورها حس می\u200cشود.', "A sentry stands motionless; an Espada's reiatsu presses from far away."),
        ('آسمانی ساختگی بالای سرت کشیده شده. حتی نور اینجا دروغ می\u200cگوید.', 'An artificial sky stretches overhead. Even the light lies here.'),
        ('روی دیوار، جای شمشیری تازه حک شده. کسی پیش از تو اینجا درس عبرت شد.', 'A fresh sword gash scars the wall. Someone before you became a lesson.'),
        ('از تالاری دور صدای قدم\u200cهایی می\u200cآید که هیچ\u200cوقت نزدیک نمی\u200cشوند.', 'From a distant hall come footsteps that never draw near.'),
    ],
    'dangai': [
        ('جریان\u200cهای تاریک اطرافت می\u200cچرخند؛ ردیف نگهبانان کوملا از دور دیده می\u200cشود.', 'Dark currents churn around you; the Kumo brood skitters in the distance.'),
        ('زمان اینجا کند می\u200cشود؛ نجوای کسانی را می\u200cشنوی که هرگز بازنگشتند.', 'Time slows here; you hear whispers of those who never returned.'),
        ('زمین زیر پایت می\u200cدود. باید بدوی تا سرجایت بمانی.', 'The ground beneath you runs. You must run just to stay in place.'),
        ('شکافی از نور سرد دوردست می\u200cدرخشد؛ شاید خروجی، شاید دامی دیگر.', 'A crack of cold light glimmers far off: an exit, or another trap.'),
        ('پرتو ریاتسوی کسی از میان تاریکی می\u200cگذرد و ناپدید می\u200cشود. هنوز زنده است… شاید.', "A beam of someone's reiatsu crosses the dark and vanishes. Still alive, perhaps."),
    ],
    'wandenreich': [
        ('ستاره\u200cهای سفید بر ردای سربازان می\u200cدرخشند؛ کمان\u200cها تازه آماده شده\u200cاند.', "White stars gleam on soldiers' cloaks; their bows are freshly strung."),
        ('آسمان اینجا بی\u200cماه است؛ صلیب\u200cها در تاریکی نورانی\u200cاند.', 'The sky here has no moon; crosses glow in the dark.'),
        ('پرچم\u200cهایی با نشان صلیب در باد می\u200cلرزند. هر سرباز به چیزی بزرگ\u200cتر از خود باور دارد.', 'Banners with a cross snap in the wind. Every soldier believes in something larger than himself.'),
        ('کوئینسی\u200cای کنارت می\u200cایستد، برانداز می\u200cکند و فقط می\u200cگوید: «هنوز زنده\u200cای؟»', 'A Quincy stops beside you, studies you and says only: “Still alive?”'),
        ('کریستال\u200cهای آبی روی سقف تالار پیچ می\u200cخورند؛ ریشی اینجا مثل برف می\u200cبارد.', "Blue crystals coil along the hall's roof; reishi falls like snow here."),
    ],
    'royal_palace': [
        ('تالارهای بی\u200cزمان از نور کهن روشن\u200cاند؛ اینجا قوانین دیگری حاکم است.', 'Timeless halls glow with ancient light; other laws rule here.'),
        ('سایه\u200cای از گذشته راهت را می\u200cبندد و آزمونت می\u200cکند.', 'A shadow of the past bars your way and tests you.'),
        ('ستون\u200cهای سفید تا آسمان می\u200cروند. هرچه بلندتر نگاه کنی، کوچک\u200cتر می\u200cشوی.', 'White pillars climb into the sky. The higher you look, the smaller you become.'),
        ('صدایی بی\u200cدهان زمزمه می\u200cکند: «لایق بودن یعنی بار را برداشتن.»', 'A voice with no mouth murmurs: “To be worthy is to carry the weight.”'),
        ('نگهبانی نامرئی کنار می\u200cرود. نمی\u200cدانی دعوت است یا هشدار.', 'An unseen guard steps aside. You cannot tell whether it is invitation or warning.'),
    ],
    'soul_king': [
        ('قلمرو شاه ارواح ساکت و بی\u200cانتهاست؛ ریاتسو مثل اقیانوس می\u200cتپد.', "The Soul King's realm is silent and endless; reiatsu beats like an ocean."),
        ('بازتاب خودت از دور نگاهت می\u200cکند و لبخند می\u200cزند.', 'Your own reflection watches from afar and smiles.'),
        ('هر قدم، موجی از نور زیر پایت می\u200cگسترد. جهان نفس می\u200cکشد و تو در سینه\u200cاش ایستاده\u200cای.', 'Each step ripples light beneath you. The world breathes, and you stand in its chest.'),
        ('همه\u200cی ریاتسوی جهان از همین\u200cجا می\u200cآید. هر نبردی شاخه\u200cای از همین ریشه است.', 'All reiatsu in the worlds begins here. Every battle is a branch of this root.'),
        ('آوایی بی\u200cصدا می\u200cپرسد: برای چه می\u200cجنگی؟ پاسخت را می\u200cدانی؟', 'A soundless voice asks: what are you fighting for? Do you know your answer?'),
    ],
    'valley_screams': [
        ('فریادهای بی\u200cصدا در دره می\u200cپیچد؛ هر سنگ حکایتی از جنگ دارد.', 'Silent screams coil through the valley; every stone remembers war.'),
        ('مه رنگ\u200cپریده راه را می\u200cپوشاند؛ جنگجوی فراموش\u200cشده\u200cای زیر آن می\u200cخندد.', 'Pale mist veils the path; a forgotten warrior laughs beneath it.'),
        ('تکه\u200cهای تیغه\u200cهای شکسته مثل کاشی در خاک فرو رفته\u200cاند. هر یک روزی نامی داشت.', 'Shards of broken blades lie in the earth like tiles. Each once had a name.'),
        ('پژواک خودت را می\u200cشنوی، اما کمی دیرتر از آنچه باید و با صدایی غریبه.', "You hear your own echo, a beat too late and in a stranger's voice."),
        ('کسی میان مه نشسته و با سنگ ریتمی می\u200cزند. با هر ضربه، مه کمی عقب می\u200cرود.', 'Someone sits in the mist tapping a rhythm on stone. With each beat the mist recedes a little.'),
    ],
}

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
