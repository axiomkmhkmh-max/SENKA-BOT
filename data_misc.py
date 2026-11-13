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
from data_bleach import ARC_QUESTS
for _a in ARC_QUESTS:
    QUESTS.append(_q(_a[0], "main", _a[1], _a[2], _a[3], _a[4], _a[6], _a[7], _a[5]))
    QUEST_DESC[_a[0]] = (_a[8], _a[9])
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


# ---- extra Bleach locations: atmosphere + lore ----
LOC_DESC.update({
    "zaraki_district": ("جایی که حتی هالوها از ترس راه کنار می‌روند؛ فقط قوی‌ترین زنده می‌ماند.", "Where even Hollows step aside; only the strongest survive."),
    "sokyoku_hill": ("تپه‌ای بلند زیر آسمان سرد؛ هوا بوی سرنوشت می‌دهد.", "A high hill under a cold sky; the air smells of fate."),
    "forest_menos": ("درخت‌هایی از استخوان و شن زیر ماه؛ هر سایه می‌تواند منوس باشد.", "Trees of bone and sand beneath the moon; every shadow may be a Menos."),
    "fake_karakura": ("شهری که روی نقشه است ولی واقعی نیست؛ جنگی بزرگ پیش رو دارد.", "A town on the map but not real; a great war lies ahead."),
    "silbern_palace": ("کاخ سفید و بی‌صدا؛ هر پله‌اش به‌اندازه‌ی یک عمر ریاتسو سنگین است.", "A white, silent palace; every step weighs a lifetime of reiatsu."),
})
LORE.update({
    "zaraki_district": [("مردی بی‌نام می‌گوید: «اینجا اول می‌جنگی، بعد اسم می‌پرسی.»", "A nameless man says: “Here you fight first and ask names later.”"),
                        ("روی دیوار نشانه‌ی دست‌های خونی؛ کسی نمی‌داند کدام جنگ بود.", "Bloody handprints on the wall; no one knows which fight left them."),
                        ("کودکی با چوب‌دستی می‌گوید روزی از همه قوی‌تر می‌شود.", "A kid with a stick swears he will one day be stronger than everyone.")],
    "sokyoku_hill": [("بادی سرد از بالای تپه می‌آید و چیزی را زمزمه می‌کند.", "A cold wind from the hilltop whispers something."),
                     ("طناب‌های آویخته هنوز تکان می‌خورند، گویی کسی هنوز آنجاست.", "Hanging ropes still sway as if someone were still there."),
                     ("نگهبانی می‌گوید: «عدالت گاهی از جایی که انتظارش را نداری می‌آید.»", "A guard says: “Justice sometimes comes from where you least expect.”")],
    "forest_menos": [("شنی نرم زیر پایت صدای استخوان می‌دهد.", "Soft sand under your boots crunches like bone."),
                     ("سایه‌ای بزرگ از کنارت می‌گذرد؛ نفست را حبس می‌کنی.", "A vast shadow passes by; you hold your breath."),
                     ("ماه بالای جنگل نیمه‌شب را نشان می‌دهد؛ اینجا هیچ‌وقت صبح نمی‌شود.", "The moon above shows midnight; morning never comes here.")],
    "fake_karakura": [("خیابان‌ها مثل خانه‌اند، اما هیچ‌کس نیست که صدایت بزند.", "The streets look like home, but no one is here to call your name."),
                      ("آسمان ترک خورده و از میان آن، جهانی دیگر دیده می‌شود.", "The sky is cracked, and another world shows through."),
                      ("هر ساختمان دروغی است، اما نبرد در آن واقعی است.", "Every building is a lie, but the fighting here is real.")],
    "silbern_palace": [("دیوارهای سفید ریاتسو را می‌بلعند؛ سکوت نفس‌گیر است.", "White walls swallow reiatsu; the silence is suffocating."),
                       ("پله‌ها بی‌پایان‌اند و هر کدام نامی را زمزمه می‌کنند.", "The stairs are endless and each whispers a name."),
                       ("ستاره‌ای بر دیوار حک شده؛ می‌گویند پیش از تو هزاران نفر آن را دیده‌اند.", "A star is carved on the wall; they say thousands saw it before you.")],
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
LORE.update({
    "shinigami_academy": [("مربی‌ای فریاد می‌زند: «تیغه را نگه دار، نه اینکه از آن آویزان شو!»", "An instructor shouts: “Hold the blade, don't hang from it!”"),
                          ("روی تخته فهرست نمره‌ها و نام کسانی آویخته که روزی کاپیتان شدند.", "On the board hang the grade lists and the names of those who became captains."),
                          ("شاگردی در حیاط کیدو تمرین می‌کند و بار سوم همان وِرد را اشتباه می‌خواند.", "A student practices kidō in the yard and flubs the same incantation a third time.")],
    "inuzuri": [("کودکی نان کپک‌زده‌اش را با تو نصف می‌کند و می‌گوید: «فردا شاید نباشم.»", "A child splits a moldy loaf with you and says: “Tomorrow I might not be here.”"),
                ("دیواری شکسته پر از نقاشی‌های گچی است؛ هر کدام یک خانواده.", "A broken wall is covered in chalk drawings; each one is a family."),
                ("سگی لاغر دنبالت می‌آید و تا دروازه‌ی محله بدرقه‌ات می‌کند.", "A thin dog follows you and sees you off to the district gate.")],
    "urahara_training": [("تابلویی نوشته: «با مسئولیت خودتان!» و درست زیرش یک تله‌ی تازه کار گذاشته‌اند.", "A sign reads: “Enter at your own risk!” and a fresh trap sits right beneath it."),
                         ("صدایی از بالا: «بهتر شد! حالا دوباره، این بار با کمی ترس کمتر.»", "A voice from above: “Better! Again, with a little less fear this time.”"),
                         ("ریشی در هوا موج می‌زند و هر قدمت را سنگین‌تر می‌کند.", "Reishi ripples in the air and makes each step heavier.")],
    "senzaikyu": [("زنجیرهای خالی از سقف آویزان است، گویی منتظر زندانی بعدی.", "Empty chains hang from the ceiling, as if waiting for the next prisoner."),
                  ("نگهبانی زیر لب می‌گوید: «از اینجا کسی نمی‌رود، مگر آنکه کسی از بیرون بخواهدش.»", "A guard mutters: “No one leaves here, unless someone outside wants them to.”"),
                  ("پله‌ای که به تپه‌ی اعدام می‌رسد؛ هنوز کسی آرام از آن بالا نرفته.", "A staircase that leads to the execution hill; no one has climbed it at peace.")],
    "maggot_nest": [("از سلول‌ها زمزمه‌هایی می‌آید که هیچ‌کس جرأت نمی‌کند جوابشان را بدهد.", "Whispers drift from the cells that no one dares answer."),
                    ("روی دیوار شماره‌ای خراشیده شده؛ شمارش روزهایی که دیگر معنایی ندارند.", "A tally is scratched on the wall, counting days that no longer mean anything."),
                    ("زندانبانی می‌گوید: «اگر صدایی از دیوار شنیدی، جوابش نده؛ بشمارش.»", "A jailer says: “If you hear a voice in the wall, don't answer it. Count it.”")],
    "garganta_tunnel": [("نور ماه از دیواره‌ها می‌چکد و روی زمین ترک می‌اندازد.", "Moonlight drips from the walls and cracks along the floor."),
                        ("صدای پاهایی پشت سرت می‌آید؛ برمی‌گردی و هیچ‌کس نیست.", "You hear footsteps behind you; you turn and no one is there."),
                        ("هوا بوی شن و استخوان می‌دهد؛ مقصد نزدیک است، یا شاید دور.", "The air smells of sand and bone; the destination is near, or perhaps far.")],
    "muken": [("زنجیری از دل سایه بیرون می‌خزد و دور مچت حلقه می‌شود.", "A chain crawls from the shadow and curls around your wrist."),
              ("خنده‌ای دور، از جایی که هیچ‌کس در آن نیست.", "A far-off laugh, from a place where no one is."),
              ("زمین زیر پایت تکرار می‌شود؛ هر قدم همان قدم قبلی است.", "The ground beneath you repeats; every step is the one before.")],
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
LORE.update({
    "kurosaki_clinic": [("پرستاری می‌گوید: «بیمار اتاق سه امشب هم نیامد؛ فقط سایه‌اش آمد.»", "A nurse says: “The patient in room three didn't come tonight, only his shadow did.”"),
                        ("روی میز پذیرش یک فنجان چای هست که هیچ‌وقت سرد نمی‌شود.", "A cup of tea sits on the reception desk and never goes cold."),
                        ("از پنجره‌ی طبقه‌ی بالا صدای دعوای دو خواهر می‌آید؛ بعد خنده‌شان.", "From an upstairs window comes two sisters bickering, then laughing.")],
    "seireitei_gate": [("غولی پای دروازه می‌گوید: «تا زنده‌ام کسی از اینجا رد نمی‌شود، مگر اینکه بتواند مرا بلند کند.»", "A giant at the gate says: “While I live no one passes, unless they can lift me.”"),
                       ("جاده‌ی سفید زیر آفتاب برق می‌زند؛ هر رد پا روی آن زود محو می‌شود.", "The white road gleams in the sun; every footprint fades fast."),
                       ("بالای دروازه پرچمی بی‌نشان تکان می‌خورد، گویی منتظر نامی است.", "A blank banner flutters above the gate as if waiting for a name.")],
    "kuchiki_manor": [("خدمتکاری بی‌صدا تعظیم می‌کند و بی‌آنکه چیزی بپرسد مسیر را نشانت می‌دهد.", "A silent retainer bows and points your way without a question."),
                      ("گلبرگ‌ها در باد می‌چرخند، انگار تیغه‌ای ناپیدا آن‌ها را هدایت می‌کند.", "Petals swirl in the wind as if an unseen blade guides them."),
                      ("پیرمردی کنار حوض می‌گوید: «قانون محکم‌تر از سنگ است، تا وقتی دلی نشکند.»", "An old man by the pond says: “Law is firmer than stone, until a heart breaks.”")],
    "shiba_estate": [("کسی از پشت‌بام فریاد می‌زند: «اول آتش‌بازی، بعد سؤال!»", "Someone shouts from the roof: “Fireworks first, questions later!”"),
                     ("توپی بزرگ و دودزده وسط حیاط ایستاده و هنوز بوی شب‌های جشن می‌دهد.", "A great soot-black cannon stands in the yard and still smells of festival nights."),
                     ("نشان خاندان روی دروازه‌ی چوبی حک شده؛ حاشیه‌اش سوخته اما ناخوانا نیست.", "The clan crest is carved on the wooden gate; its edge is scorched but legible.")],
    "visored_warehouse": [("ماسکی روی دیوار آویزان است و وقتی رد می‌شوی، چشم‌هایش به دنبالت می‌چرخد.", "A mask hangs on the wall and its eyes follow you as you pass."),
                          ("صدایی از زیرزمین: «اگر ماسکت را کنترل نکنی، او کنترلت می‌کند.»", "A voice from the cellar: “If you don't control your mask, it controls you.”"),
                          ("روی زمین تمرین، جای پاهای بی‌شماری مانده؛ بعضی‌ها دو رو دارند.", "The practice floor bears countless footprints; some of them have two faces.")],
    "research_institute": [("پشت شیشه‌ی ضخیم چیزی تکان می‌خورد و نمی‌خواهی بدانی چیست.", "Behind thick glass something moves, and you don't want to know what."),
                           ("روی تخته‌ی آزمایشگاه یادداشتی مانده: «نمونه ۴۴ فرار کرد. دوباره.»", "A note left on the lab board: “Specimen 44 escaped. Again.”"),
                           ("چراغ‌ها بی‌دلیل چشمک می‌زنند، گویی ساختمان هم دارد فکر می‌کند.", "The lights blink for no reason, as though the building itself were thinking.")],
    "las_noches_throne": [("روی تخت، صندلی خالی و سایه‌ای که هنوز اینجا نشسته.", "On the dais an empty chair, and a shadow that still sits there."),
                          ("ستون‌ها از شن ساخته شده‌اند؛ هر کدام آهسته می‌ریزد.", "The pillars are made of sand; each one slowly crumbles."),
                          ("صدایی می‌پرسد: «اگر همه‌چیز را داشتی، باز هم می‌جنگیدی؟»", "A voice asks: “If you had everything, would you still fight?”")],
    "schatten_bereich": [("ستاره‌ای از آسمان می‌افتد و پیش از رسیدن به زمین خاموش می‌شود.", "A star falls from the sky and goes out before it reaches the ground."),
                         ("سایه‌ای از خودت جلوتر می‌رود و پیش از تو تعظیم می‌کند.", "A shadow walks ahead of you and bows before you do."),
                         ("هر قدم یک نام را زمزمه می‌کند، نام کسانی که پیش‌تر اینجا آمدند.", "Each step whispers a name, those of the ones who came here before.")],
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
LORE.update({
    "junrinan": [("پیرمردی نان می‌فروشد و می‌گوید: «همه از همین‌جا شروع می‌کنند.»", "An old man sells bread and says: “Everyone starts right here.”"),
                 ("کودکی نقشه‌ی محله را روی خاک می‌کشد و راه میان‌بُر را نشانت می‌دهد.", "A child draws the district map in the dirt and shows you the shortcut."),
                 ("چراغ‌های کاغذی در باد تکان می‌خورند، گویی یاد کسانی‌اند که رفتند.", "Paper lanterns sway in the wind as if remembering those who left.")],
    "karakura_high": [("زنگ تفریح می‌خورد، اما هیچ‌کس در حیاط نیست.", "The recess bell rings, but the yard is empty."),
                      ("روی تخته نوشته‌ای نیمه‌پاک‌شده: «ریاتسو را جدی بگیرید.»", "A half-erased line on the board: “Take reiatsu seriously.”"),
                      ("از پشت‌بام خنده‌ای می‌آید؛ بالا که می‌روی، فقط باد است.", "Laughter from the roof; you climb up and find only wind.")],
    "urahara_shop": [("تابلوی «تخفیف ویژه» دارد و درست زیرش «ورود با مسئولیت خودتان».", "A “special discount” sign hangs above “enter at your own risk.”"),
                     ("پسرکی جارو را مثل تیغه می‌چرخاند و می‌گوید: «سخت‌تر!»", "A boy swings a broom like a blade and says: “Harder!”"),
                     ("از اتاق پشتی صدای خنده‌ای می‌آید که هیچ‌کس توضیحش نمی‌دهد.", "A laugh comes from the back room that no one will explain.")],
    "relief_station": [("پرستاری با لبخند می‌گوید: «اول بنشین، بعد قهرمان شو.»", "A nurse says with a smile: “Sit first, be a hero after.”"),
                       ("بوی چای گیاهی تمام راهرو را پر کرده است.", "The scent of herbal tea fills the whole corridor."),
                       ("روی تخت آخر پتویی تاشده؛ می‌گویند صاحبش خودش را سالم تحویل داد.", "A blanket lies folded on the last bed; they say its owner left on his own feet.")],
    "captains_hall": [("صندلی‌ها دایره‌وار چیده شده‌اند و یکی خالی است.", "The seats form a circle and one of them is empty."),
                      ("هائوری‌ای سفید روی چوب‌لباسی آویزان است؛ هنوز بوی تیغ می‌دهد.", "A white haori hangs on a stand; it still smells of steel."),
                      ("پیرمردی می‌گوید: «تصمیم‌ها اینجا سنگین‌ترند از شمشیرها.»", "An old man says: “Decisions here weigh more than swords.”")],
    "jigoku": [("زنجیری از دل شعله بیرون می‌آید و پیش از تو می‌ایستد.", "A chain rises from the flame and stops before you."),
               ("صدایی می‌پرسد: «بدهی‌ات را کی می‌پردازی؟»", "A voice asks: “When will you pay your debt?”"),
               ("آسمان سرخ است و هر ستاره‌اش زنجیری است.", "The sky is red and each of its stars is a chain.")],
    "sternritter_hall": [("روی هر صندلی نشانی از یک حرف حک شده.", "A letter is carved on every seat."),
                         ("نوری سرد از سقف می‌ریزد و سایه‌ات را باریک می‌کند.", "Cold light falls from the ceiling and thins your shadow."),
                         ("صدای قدم‌هایی در سکوت؛ و بعد هیچ.", "Footsteps in the silence, and then nothing.")],
    "hogyoku_chamber": [("بلور می‌تپد و ضرباهنگش به دلت می‌افتد.", "The crystal pulses and its beat finds your heart."),
                        ("هر خواسته‌ای را که فکر کنی، اتاق پیش‌تر می‌داند.", "Whatever wish you think of, the room already knows."),
                        ("روی دیوار سایه‌هایی ایستاده‌اند که صاحب ندارند.", "Shadows with no owners stand against the wall.")],
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
LORE.update({
    "riverbank": [("بچه‌ای لب رود سنگ پرت می‌کند و می‌گوید: «سنگ‌ها هم گاهی برمی‌گردند.»", "A child skips stones at the water's edge: “Even stones come back sometimes.”"),
                  ("مه غلیظ می‌شود و از میانش صدای زنگوله‌ای دور می‌آید.", "The mist thickens and a faint bell sounds from within it."),
                  ("روی پل، یک چتر تاشده جا مانده؛ هنوز خیس است.", "A folded umbrella is left on the bridge; it is still wet.")],
    "kusajishi_district": [("پسربچه‌ای با لبخند می‌گوید: «اینجا هر کس برای خودش اسم می‌گذارد.»", "A boy says with a grin: “Here everyone names themselves.”"),
                           ("سگی گرسنه کنار تو راه می‌افتد؛ هر دو می‌دانید این دوستی دوام ندارد.", "A starving dog falls in beside you; you both know this friendship will not last."),
                           ("روی دیوار شکسته با زغال نوشته‌اند: «زنده بمان، حتی اگر زشت.»", "Someone has written on a broken wall in charcoal: “Stay alive, even if ugly.”")],
    "bount_mansion": [("ساعتی بی‌عقربه بر دیوار است و تیک‌تاکش را می‌شنوی.", "A clock with no hands hangs on the wall, and you hear it tick."),
                      ("عروسکی پشت پنجره دست تکان می‌دهد؛ پشتش هیچ‌کس نیست.", "A doll waves from a window; no one stands behind it."),
                      ("روی میز دو فنجان چای مانده، یکی هنوز گرم.", "Two cups of tea sit on the table, one still warm.")],
    "xcution_hideout": [("قاب عکسی خالی روی طاقچه است؛ کسی آن را هر روز گردگیری می‌کند.", "An empty photo frame sits on the shelf; someone dusts it every day."),
                        ("کسی می‌گوید: «قدرت که برگردد، دیگر چیزی از ما نمی‌ماند.»", "Someone says: “Once the power returns, nothing of us will be left.”"),
                        ("یک صندلی بیشتر از آدم‌ها اینجا هست؛ کسی کنارش نمی‌نشیند.", "There is one more chair than there are people; no one sits beside it.")],
    "orihime_chamber": [("بشقابی دست‌نخورده روی میز است و کنارش یک سنجاق کوچک.", "An untouched plate sits on the table beside a small hairpin."),
                        ("پنجره بسته است ولی نسیمی از آن می‌آید و بوی گل دارد.", "The window is shut, yet a breeze comes through it, smelling of flowers."),
                        ("روی دیوار سفید یک ردّ انگشت است؛ کسی همین‌جا دعا کرده.", "A fingerprint marks the white wall; someone prayed right here.")],
    "precipice_world": [("زمین زیر پایت چند ثانیه می‌ماند و بعد می‌رود.", "The ground beneath you stays for a few seconds and then leaves."),
                        ("از دور تک‌صدای بالی می‌آید که هیچ‌وقت نزدیک نمی‌شود.", "The faint sound of a wing drifts in, but never comes closer."),
                        ("روی دیوار نوری باریک می‌دود؛ اگر دنبالش بروی، تا انتها می‌بردت.", "A thin light runs along the wall; follow it and it leads you to the end.")],
    "seireitei_ruins": [("پرچمی نیمه‌سوخته هنوز از یک برج می‌آویزد.", "A half-burned banner still hangs from a tower."),
                        ("زیر آوار صدای ضعیفی می‌گوید: «هنوز نباخته‌ایم.»", "From beneath the rubble a faint voice says: “We have not lost yet.”"),
                        ("خاکستر روی زمین الگوی یک نام را ساخته؛ باد آن را نمی‌خواند.", "Ash on the ground has formed the pattern of a name; the wind will not read it.")],
    "zero_division_hall": [("پنج صندلی در تالار هست و هیچ‌کدام خالی نیست، هرچند چیزی نمی‌بینی.", "Five seats stand in the hall and none is empty, though you see no one."),
                           ("صدایی نرم می‌گوید: «همه‌چیز از همین‌جا نگه داشته شده.»", "A soft voice says: “Everything is held up from right here.”"),
                           ("کلیدی بزرگ روی ستون آویزان است؛ قفلش را هیچ‌جا نمی‌یابی.", "A great key hangs on a pillar; you find no lock for it anywhere.")],
})

# ---- named Hadō / Bakudō spells (names only; card ids and effects never change) ----
KIDO_NAMES.update({("had", 11): "Tsuzuri Raiden", ("had", 12): "Fushibi", ("had", 32): "Ōkasen", ("had", 54): "Haien",
                   ("had", 91): "Senju Kōtenkan", ("had", 96): "Ittō Kasō",
                   ("bak", 21): "Sekienton", ("bak", 26): "Kyokkō", ("bak", 58): "Kakushitsuijaku", ("bak", 75): "Gochūtekkan"})
# ---- pack 3: three more named spells ----
KIDO_NAMES.update({("bak", 8): "Seki", ("bak", 77): "Tenteikūra", ("had", 78): "Zangeki"})
# ---- pack 5: one more named spell ----
KIDO_NAMES.update({("had", 57): "Daichi Tenyō"})
