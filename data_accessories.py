"""500 Bleach accessories (players asked: the old 150 were the same few names repeated at several colours, which
confused drops). Every accessory here is one unique object from the anime with exactly ONE colour: no "II" or
"stage 2" copies. If an object's power needs a stronger version, it is a different canon object.

Slots: "r" = 💍 hand / badge slot (subtype ring -> acc_id), "n" = 📿 neck / head / cloak slot (subtype necklace -> charm_id).
Colours: C white, U green, R blue, E purple, L gold, M red (red ones are special: they never drop at random, they come
from jackpots, the roll shop and level bosses).
Stats: z Zanjutsu, k Kidō, h Hakuda, s Hohō, r Reiatsu, l luck.
Pure data, no I/O. Ids ac_001 .. ac_500 never change once published.
"""

RAR = {"C": "Common", "U": "Uncommon", "R": "Rare", "E": "Epic", "L": "Legendary", "M": "Mythic"}
MAIN = {"C": 3, "U": 5, "R": 7, "E": 10, "L": 14, "M": 20}       # main stat bonus by colour
SECOND = {"C": 0, "U": 0, "R": 3, "E": 4, "L": 6, "M": 9}       # second stat bonus by colour
LUCK = {"C": 1, "U": 1, "R": 2, "E": 2, "L": 3, "M": 4}
LEVEL = {"C": 1, "U": 5, "R": 15, "E": 30, "L": 50, "M": 80}
PRICE = {"C": 90, "U": 320, "R": 1300, "E": 4800, "L": 21000, "M": 60000}
STAT = {"z": "zanjutsu", "k": "kido", "h": "hakuda", "s": "hoho", "r": "reiatsu"}

_E = []   # (en, fa, slot, colour, main stat, second stat or "", group flavour key)


def _add(group, rows):
    for row in rows:
        _E.append((*row, group))


# ---- Gotei 13: lieutenant armbands (each division has its own flower) ------------------------------------------------
_FLOWERS = [("Chrysanthemum", "گل داوودی"), ("Pasque Flower", "گل باد"), ("Marigold", "گل همیشه‌بهار"), ("Gentian", "گل جنتیانا"),
            ("Andromeda", "گل آشیبی"), ("Camellia", "گل کاملیا"), ("Iris", "گل زنبق"), ("Bird of Paradise", "گل مرغ بهشتی"),
            ("White Poppy", "خشخاش سفید"), ("Narcissus", "گل نرگس"), ("Yarrow", "گل بومادران"), ("Thistle", "گل خار"),
            ("Snowdrop", "گل حسرت")]
_FA_NUM = "۰۱۲۳۴۵۶۷۸۹"


def _fa(n: int) -> str:
    return str(n).translate(str.maketrans("0123456789", _FA_NUM))


_DIV_STAT = ["z", "k", "z", "k", "k", "z", "h", "k", "s", "z", "z", "k", "s"]
_add("lieutenant", [(f"{d}th Division Lieutenant Armband ({f_en})".replace("1th", "1st").replace("2th", "2nd").replace("3th", "3rd")
                     .replace("11st", "11th").replace("12nd", "12th").replace("13rd", "13th"),
                     f"بازوبند ستوان گروهان {_fa(d)} ({f_fa})", "r", "R", _DIV_STAT[d - 1], "r")
                    for d, (f_en, f_fa) in enumerate(_FLOWERS, 1)])
_add("captain", [(f"Captain's Haori of Division {d}", f"هائوری کاپیتان گروهان {_fa(d)}", "n", "E", _DIV_STAT[d - 1], "h")
                 for d in range(1, 14)])
_add("seat", [(f"Seated Officer Pin of Division {d}", f"سنجاق افسر رده‌دار گروهان {_fa(d)}", "r", "U", _DIV_STAT[d - 1], "")
              for d in range(1, 14)])

# ---- Espada and Privaron numbers ---------------------------------------------------------------------------------------
_ESP = [("Starrk", "استارک", "L", "r"), ("Barragan", "بارگان", "L", "h"), ("Harribel", "هریبل", "E", "s"), ("Ulquiorra", "اولکیورا", "L", "r"),
        ("Nnoitra", "نوایترا", "E", "z"), ("Grimmjow", "گریمجو", "E", "h"), ("Zommari", "زوماری", "E", "s"),
        ("Szayel Aporro", "سایل‌آپورو", "E", "k"), ("Aaroniero", "آرونیرو", "E", "k"), ("Yammy", "یامی", "E", "h")]
_ESP_NUM = [1, 2, 3, 4, 5, 6, 7, 8, 9, 0]
_add("espada", [(f"Espada Number {num} Brand ({n_en})", f"نشان شماره‌ی {_fa(num)} اسپادا ({n_fa})", "n", c, s, "r")
                for (n_en, n_fa, c, s), num in zip(_ESP, _ESP_NUM)])
_add("espada", [(f"Mask Remnant of {n_en}", f"بقایای ماسک {n_fa}", "n", "E" if c == "E" else "L", s, "h") for n_en, n_fa, c, s in _ESP])
_add("espada", [("Privaron Number 103 Brand (Dordoni)", "نشان پریوارون ۱۰۳ (دوردونی)", "n", "R", "s", "h"),
                ("Privaron Number 105 Brand (Cirucci)", "نشان پریوارون ۱۰۵ (سیروچی)", "n", "R", "s", "k"),
                ("Privaron Number 107 Brand (Gantenbainne)", "نشان پریوارون ۱۰۷ (گانتنباین)", "n", "R", "h", "z")])
_add("arrancar", [
    ("Lilynette's Horn Half", "نیمه‌ی شاخ لیلینت", "n", "R", "s", "r"),
    ("Apacci's Horn", "شاخ آپاچی", "n", "U", "h", ""), ("Mila Rose's Crown Remnant", "تاج ماسک میلا رز", "n", "U", "z", ""),
    ("Sung-Sun's Sleeve Veil", "روبند آستین سونگ‌سون", "n", "U", "k", ""),
    ("Nel's Skull Mask", "ماسک جمجمه‌ی نل", "n", "E", "h", "s"), ("Pesche's Loincloth Charm", "طلسم لنگ پشه", "r", "C", "s", ""),
    ("Dondochakka's Mask Fragment", "پاره‌ی ماسک دوندوچاکا", "n", "C", "h", ""), ("Bawabawa's Sand Scale", "فلس شنی باواباوا", "r", "U", "h", ""),
    ("Ggio Vega's Tiger Fang", "دندان ببری جیو وگا", "r", "R", "s", "z"), ("Findorr's Crab Claw Mask", "ماسک چنگال خرچنگ فیندور", "n", "R", "z", "h"),
    ("Charlotte's Rose", "رز شارلوت", "r", "U", "k", ""), ("Avirama's Feather", "پر آویراما", "r", "U", "s", ""),
    ("Choe Neng Poww's Mask Shard", "پاره‌ی ماسک چوئه‌نِنگ‌پو", "n", "U", "h", ""), ("Nirgge's Mammoth Tusk", "عاج ماموت نیرگه", "r", "R", "h", "z"),
    ("Abirama's War Plume", "کاکل جنگی آبیراما", "n", "U", "z", ""), ("Shawlong's Mask Crest", "تاج ماسک شاولونگ", "n", "R", "z", "s"),
    ("Edrad's Fire Gauntlet", "دستکش آتشین ادراد", "r", "R", "h", "r"), ("Yylfordt's Horned Mask", "ماسک شاخ‌دار ایلفورت", "n", "U", "z", ""),
    ("Nakeem's Mask Shard", "پاره‌ی ماسک ناکیم", "n", "U", "h", ""), ("Di Roy's Tooth", "دندان دی روی", "r", "C", "z", ""),
    ("Ilfort's Bull Horn", "شاخ گاو ایلفورت", "n", "U", "z", ""), ("Loly's Hair Clip", "گیره‌ی موی لولی", "r", "C", "k", ""),
    ("Menoly's Mask Shard", "پاره‌ی ماسک منولی", "n", "C", "h", ""), ("Tesla's Eyepatch Strap", "بند چشم‌بند تسلا", "n", "R", "h", "z"),
    ("Luppi's Tentacle Ribbon", "روبان شاخکی لوپی", "n", "R", "z", "s"), ("Wonderweiss's Flower", "گل واندروایس", "r", "E", "r", "h"),
    ("Rudbornn's Skull Mask", "ماسک جمجمه‌ی رودبورن", "n", "R", "z", "h"), ("Exequias Skull Badge", "نشان جمجمه‌ی اگزکیاس", "r", "U", "z", ""),
    ("Patros's Mask Crest", "تاج ماسک پاتروس", "n", "U", "z", ""), ("Demoura's Mask Shard", "پاره‌ی ماسک دموئورا", "n", "C", "h", ""),
    ("Aisslinger's Nail", "ناخن آیسلینگر", "r", "C", "s", ""), ("Grantz's Glasses Lens", "عدسی عینک گرانتز", "r", "R", "k", "r"),
    ("Cyan Sung-Sun's Hollow Hole Veil", "روبند حفره‌ی هالو سیان", "n", "R", "k", "r"),
    ("Dordoni's Wind Drill Bracer", "مچ‌بند گردباد دوردونی", "r", "U", "s", ""),
    ("Gantenbainne's Dragon Claw", "پنجه‌ی اژدهای گانتنباین", "r", "R", "h", "z"),
])

# ---- Wandenreich: the twenty-six Schrift medallions and Quincy keepsakes ---------------------------------------------
_SCHRIFT = [("A", "The Almighty", "قادر مطلق", "Yhwach", "یوهاباخ", "M"), ("B", "The Balance", "ترازو", "Haschwalth", "هاشوالث", "L"),
            ("C", "The Compulsory", "اجبار", "Pernida", "پرنیدا", "E"), ("D", "The Deathdealing", "مرگ‌آفرین", "Askin", "آسکین", "E"),
            ("E", "The Explode", "انفجار", "Bambietta", "بمبیتا", "E"), ("F", "The Fear", "ترس", "Äs Nödt", "اس نوت", "E"),
            ("G", "The Glutton", "پرخور", "Liltotto", "لیلتوتو", "E"), ("H", "The Heat", "گرما", "Bazz-B", "باز-بی", "E"),
            ("I", "The Iron", "آهن", "Cang Du", "سانگ دو", "R"), ("J", "The Jail", "زندان", "Quilge", "کیلگه", "E"),
            ("K", "The K", "حرف K", "BG9", "بی‌جی ناین", "R"), ("L", "The Love", "عشق", "Pepe", "پپه", "R"),
            ("M", "The Miracle", "معجزه", "Gerard", "جرارد", "L"), ("N", "The Nightmare", "کابوس", "Robert", "رابرت", "R"),
            ("O", "The Overkill", "فراکشتار", "Driscoll", "دریسکول", "R"), ("P", "The Power", "قدرت", "Meninas", "منیناس", "R"),
            ("Q", "The Question", "پرسش", "Berenice", "برنیس", "U"), ("R", "The Roar", "غرش", "Jerome", "جروم", "R"),
            ("S", "The Superstar", "سوپراستار", "Mask De Masculine", "ماسک دو ماسکولین", "E"),
            ("T", "The Thunderbolt", "صاعقه", "Candice", "کندیس", "E"), ("U", "The Underbelly", "نقطه‌ضعف", "NaNaNa", "نانانا", "R"),
            ("V", "The Visionary", "خیال‌پرداز", "Gremmy", "گرمی", "L"), ("W", "The Wind", "باد", "Nianzol", "نیانزول", "U"),
            ("X", "The X-Axis", "محور ایکس", "Lille Barro", "لیله بارو", "L"), ("Y", "The Yourself", "خودِ تو", "Royd Lloyd", "روید لوید", "R"),
            ("Z", "The Zombie", "زامبی", "Giselle", "ژیزل", "E")]
_SCH_STAT = "rrkhrkhrhkhkzhrrkhrrkkskrk"
_add("schrift", [(f"Schrift '{L}' Medallion ({t_en}, {n_en})", f"مدال حرف «{L}» ({t_fa}، {n_fa})", "n", c, _SCH_STAT[i], "r" if c in "LM" else "")
                 for i, (L, t_en, t_fa, n_en, n_fa, c) in enumerate(_SCHRIFT)])
_add("quincy", [
    ("Sanrei Glove", "دستکش سانری", "r", "L", "r", "s"), ("Quincy Cross", "صلیب کوئینسی", "n", "L", "r", "s"),
    ("Masaki's Quincy Bracelet", "دستبند کوئینسی ماساکی", "r", "E", "r", "h"), ("Sōken's Ginrei Kojaku Charm", "طلسم گینری کوجاکوی سوکن", "n", "E", "r", "k"),
    ("Ryūken's Hospital ID Card", "کارت شناسایی بیمارستان ریوکن", "r", "U", "r", ""), ("Uryū's Sewing Kit", "جعبه‌خیاطی اوریو", "r", "U", "s", ""),
    ("Uryū's Glasses", "عینک اوریو", "n", "R", "r", "k"), ("Schutzstaffel Badge", "نشان شوتس‌اشتافل", "r", "E", "r", "z"),
    ("Jagdarmee Soldier Pin", "سنجاق سرباز یاگدآرمه", "r", "U", "r", ""), ("Letzt Stil Ribbon", "روبان لتسته اشتیل", "n", "L", "r", "h"),
    ("Wandenreich Shadow Token", "ژتون سایه‌ی وندن‌رایش", "r", "R", "s", "r"), ("Silbern Ice Crystal", "کریستال یخی زیلبرن", "n", "R", "k", "r"),
    ("Haschwalth's Shield Crest", "تاج سپر هاشوالث", "r", "L", "z", "h"), ("Bambietta's Hair Ribbon", "روبان موی بمبیتا", "n", "R", "r", "s"),
    ("Liltotto's Lollipop", "آب‌نبات چوبی لیلتوتو", "r", "U", "h", ""), ("Candice's Hair Pin", "سنجاق موی کندیس", "n", "R", "r", "s"),
    ("Giselle's Zombie Bandage", "باند زامبی ژیزل", "r", "R", "k", "h"), ("Meninas's Hair Bow", "پاپیون موی منیناس", "n", "U", "h", ""),
    ("Bazz-B's Mohawk Comb", "شانه‌ی موهاک باز-بی", "r", "R", "r", "z"), ("Askin's Lucky Dice", "تاس شانس آسکین", "r", "E", "k", "l"),
    ("Gerard's Shield Shard", "پاره‌ی سپر جرارد", "n", "L", "h", "z"), ("Äs Nödt's Thorn Collar", "گردن‌بند خار اس نوت", "n", "E", "k", "r"),
    ("Quilge's Cape Clasp", "سگک شنل کیلگه", "n", "R", "r", "z"), ("Mask De Masculine's Star Mask", "ماسک ستاره‌ی ماسک دو ماسکولین", "n", "R", "h", "r"),
    ("Pernida's Glove", "دستکش پرنیدا", "r", "E", "k", "h"), ("Robert's Revolver Charm", "طلسم هفت‌تیر رابرت", "r", "R", "r", "s"),
    ("Yhwach's Cape Clasp", "سگک شنل یوهاباخ", "n", "M", "r", "k"), ("Royal Guard Insignia", "نشان گارد سلطنتی", "r", "L", "r", "z"),
    ("Quincy Zeichen Pendant", "آویز زایشن کوئینسی", "n", "R", "r", ""), ("Kojaku Bowstring", "زه کمان کوجاکو", "r", "R", "r", "s"),
    ("Hirenkyaku Boots", "چکمه‌ی هیرنکیاکو", "r", "R", "s", "r"), ("Blut Training Band", "باند تمرین بلوت", "r", "U", "h", ""),
    ("Seele Glove Strap", "بند دستکش زیله", "r", "C", "r", ""), ("Gintō Belt", "کمربند گینتو", "n", "U", "k", ""),
])

# ---- Zanpakutō guards (one per blade) ----------------------------------------------------------------------------------
_add("tsuba", [
    ("Tsuba of Zangetsu", "گارد زانگتسو", "r", "L", "z", "r"), ("Tsuba of Senbonzakura", "گارد سنبون‌زاکورا", "r", "L", "z", "k"),
    ("Tsuba of Hyōrinmaru", "گارد هیورینمارو", "r", "E", "z", "k"), ("Tsuba of Ryūjin Jakka", "گارد ریوجین جاکا", "r", "M", "z", "r"),
    ("Tsuba of Kyōka Suigetsu", "گارد کیوکا سویگتسو", "r", "M", "k", "z"), ("Tsuba of Katen Kyōkotsu", "گارد کاتن کیوکوتسو", "r", "L", "z", "s"),
    ("Tsuba of Sōgyo no Kotowari", "گارد سوگیو نو کوتوواری", "r", "L", "k", "z"), ("Tsuba of Minazuki", "گارد مینازوکی", "r", "L", "k", "r"),
    ("Tsuba of Nozarashi", "گارد نوزاراشی", "r", "L", "z", "h"), ("Tsuba of Suzumebachi", "گارد سوزومه‌باچی", "r", "E", "s", "z"),
    ("Tsuba of Ashisogi Jizō", "گارد آشیسوگی جیزو", "r", "E", "k", "z"), ("Tsuba of Tenken", "گارد تنکن", "r", "E", "h", "z"),
    ("Tsuba of Benihime", "گارد بنی‌هیمه", "r", "L", "z", "k"), ("Tsuba of Shinsō", "گارد شینسو", "r", "E", "s", "z"),
    ("Tsuba of Suzumushi", "گارد سوزوموشی", "r", "E", "k", "s"), ("Tsuba of Zabimaru", "گارد زابی‌مارو", "r", "R", "z", "h"),
    ("Tsuba of Sode no Shirayuki", "گارد سوده نو شیرایوکی", "r", "E", "k", "z"), ("Tsuba of Haineko", "گارد های‌نکو", "r", "R", "z", "s"),
    ("Tsuba of Tobiume", "گارد توبی‌مه", "r", "R", "k", "z"), ("Tsuba of Kazeshini", "گارد کازشینی", "r", "R", "z", "s"),
    ("Tsuba of Wabisuke", "گارد وابیسوکه", "r", "R", "z", "k"), ("Tsuba of Hōzukimaru", "گارد هوزوکی‌مارو", "r", "R", "z", "h"),
    ("Tsuba of Ruri'iro Kujaku", "گارد روری‌ایرو کوجاکو", "r", "R", "k", "z"), ("Tsuba of Itegumo", "گارد ایته‌گومو", "r", "U", "k", ""),
    ("Tsuba of Gegetsuburi", "گارد گه‌گتسوبوری", "r", "U", "h", ""), ("Tsuba of Nejibana", "گارد نجی‌بانا", "r", "E", "z", "k"),
    ("Tsuba of Engetsu", "گارد انگتسو", "r", "L", "z", "r"), ("Tsuba of Sakanade", "گارد ساکاناده", "r", "E", "k", "s"),
    ("Tsuba of Kinshara", "گارد کینشارا", "r", "E", "k", "r"), ("Tsuba of Tachikaze", "گارد تاچی‌کازه", "r", "E", "z", "h"),
    ("Tsuba of Kubikiri Orochi", "گارد کوبی‌کیری اوروچی", "r", "E", "z", "s"), ("Tsuba of Haguro Tonbo", "گارد هاگورو تونبو", "r", "E", "k", "z"),
    ("Tsuba of Tengumaru", "گارد تنگومارو", "r", "E", "z", "r"), ("Tsuba of Ichimonji", "گارد ایچیمونجی", "r", "M", "k", "r"),
    ])

# ---- Visored masks, Zero Division, Fullbringers ------------------------------------------------------------------------
_add("visored", [(f"Hollow Mask of {e}", f"ماسک هالوی {f}", "n", "E", s, "h") for e, f, s in (
    ("Shinji", "شینجی", "z"), ("Hiyori", "هیوری", "h"), ("Love", "لاو", "h"), ("Rose", "رز", "k"), ("Lisa", "لیسا", "z"),
    ("Kensei", "کنسی", "h"), ("Mashiro", "ماشیرو", "s"), ("Hachi", "هاچی", "k"), ("Ichigo", "ایچیگو", "z"))])
_add("zero", [
    ("Ichibei's Ink Brush", "قلم‌موی جوهر ایچیبه", "r", "M", "k", "r"), ("Senjumaru's Sewing Needle", "سوزن خیاطی سنجومارو", "r", "L", "k", "s"),
    ("Tenjirō's Hot-Spring Towel", "حوله‌ی چشمه‌ی آب گرم تنجیرو", "n", "E", "h", "r"), ("Kirio's Rice Paddle", "کفگیر برنج کیریو", "r", "E", "h", "r"),
    ("Ōetsu's Sunglasses", "عینک آفتابی اوئتسو", "n", "L", "z", "s"), ("Ōetsu's Forge Hammer", "پتک آهنگری اوئتسو", "r", "L", "z", "h"),
    ("Zero Division Bone Charm", "طلسم استخوان گروهان صفر", "n", "L", "r", "k"), ("Soul King Palace Gate Seal", "مهر دروازه‌ی قصر شاه ارواح", "r", "E", "r", "k"),
])
_add("fullbring", [
    ("Ginjō's Cross Pendant", "آویز صلیبی گینجو", "n", "L", "z", "r"), ("Tsukishima's Bookmark", "نشانه‌ی کتاب تسوکیشیما", "r", "L", "z", "s"),
    ("Riruka's Dollhouse Charm", "طلسم خانه‌عروسکی ریروکا", "n", "E", "r", "k"), ("Yukio's Game Console", "کنسول بازی یوکیو", "r", "E", "k", "s"),
    ("Jackie's Dirty Boots", "چکمه‌های کثیف جکی", "r", "E", "h", "s"), ("Giriko's Pocket Watch", "ساعت جیبی گیریکو", "n", "E", "s", "r"),
    ("Abuelo's Coin Pendant", "آویز سکه‌ی آبوئلو", "n", "R", "h", "z"), ("Orihime's Hairpins", "سنجاق‌های موی اوریهیمه", "n", "L", "r", "k"),
    ("Xcution Bar Coaster", "زیرلیوانی بار اکسکیوشن", "r", "C", "s", ""), ("Moe's Ring", "انگشتر مو شیشیگاوارا", "r", "U", "h", ""),
])

# ---- Gotei 13 people and Karakura ---------------------------------------------------------------------------------------
_add("people", [
    ("Byakuya's Kenseikan", "کنسیکان بیاکویا", "n", "L", "z", "k"), ("Ginpaku Kazahana no Usuginu", "شال گین‌پاکو کازاهانا نو اوسوگینو", "n", "M", "z", "r"),
    ("Rukia's Chappy Hair Clip", "گیره‌ی موی چپی روکیا", "r", "U", "k", ""), ("Rukia's Sketchbook", "دفتر نقاشی روکیا", "r", "C", "k", ""),
    ("Renji's Bandana", "دستمال سر رنجی", "n", "R", "z", "h"), ("Renji's Goggles", "عینک محافظ رنجی", "n", "U", "z", ""),
    ("Hitsugaya's Star-Cross Clip", "گیره‌ی ستاره‌ی صلیبی هیتسوگایا", "n", "E", "z", "k"), ("Hitsugaya's Dried Persimmon", "خرمالوی خشک هیتسوگایا", "r", "C", "k", ""),
    ("Rangiku's Necklace", "گردنبند رانگیکو", "n", "R", "z", "s"), ("Rangiku's Pink Scarf", "شال صورتی رانگیکو", "n", "U", "s", ""),
    ("Kenpachi's Hair Bells", "زنگوله‌های موی کنپاچی", "n", "L", "h", "z"), ("Yachiru's Candy Bag", "کیسه‌ی آب‌نبات یاچیرو", "r", "U", "s", ""),
    ("Ikkaku's Sake Gourd", "قمقمه‌ی ساکه‌ی ایکاکو", "r", "U", "h", ""), ("Yumichika's Feather Ornaments", "زیورهای پری یومیچیکا", "n", "R", "z", "s"),
    ("Soi Fon's Braid Rings", "حلقه‌های گیس سوی‌فون", "n", "E", "s", "h"), ("Ōmaeda's Gold Chain", "زنجیر طلای اوماِدا", "n", "U", "h", "l"),
    ("Unohana's Braid Ribbon", "روبان گیس یونوهانا", "n", "L", "k", "z"), ("Isane's Hair Clip", "گیره‌ی موی ایسانه", "r", "U", "k", ""),
    ("Hanatarō's First-Aid Pouch", "کیف کمک‌های اولیه‌ی هاناتارو", "r", "C", "k", ""), ("Kyōraku's Straw Hat", "کلاه حصیری کیوراکو", "n", "L", "z", "s"),
    ("Kyōraku's Flowered Kimono", "کیمونوی گل‌دار کیوراکو", "n", "E", "z", "r"), ("Kyōraku's Hairpins", "سنجاق‌های موی کیوراکو", "r", "R", "s", "z"),
    ("Nanao's Glasses", "عینک نانائو", "n", "R", "k", "r"), ("Nanao's Kidō Book", "کتاب کیدوی نانائو", "r", "U", "k", ""),
    ("Ukitake's Medicine Box", "جعبه‌ی داروی اوکیتاکه", "r", "E", "k", "r"), ("Ukitake's Candy Stash", "ذخیره‌ی آب‌نبات اوکیتاکه", "r", "C", "r", ""),
    ("Kiyone and Sentarō's Rival Armbands", "بازوبندهای رقابتی کیونه و سنتارو", "r", "C", "s", ""), ("Komamura's Helmet", "کلاه‌خود کومامورا", "n", "E", "h", "z"),
    ("Gorō's Collar", "قلاده‌ی گورو", "n", "U", "h", ""), ("Iba's Sunglasses", "عینک آفتابی ایبا", "n", "U", "z", ""),
    ("Tōsen's Visor", "عینک تیغه‌ای توسن", "n", "E", "s", "z"), ("Tōsen's Orange Scarf", "شال نارنجی توسن", "n", "R", "s", "k"),
    ("Hisagi's 69 Choker", "گردن‌بند ۶۹ هیساگی", "n", "R", "z", "s"), ("Seireitei Communication Issue", "شماره‌ی مجله‌ی سیرِیتِی", "r", "C", "k", ""),
    ("Mayuri's Golden Headdress", "سربند طلایی مایوری", "n", "E", "k", "r"), ("Mayuri's Poison Fingernail", "ناخن سمی مایوری", "r", "R", "k", "z"),
    ("Nemu's Hair Bow", "پاپیون موی نمو", "r", "C", "k", ""), ("Kira's Poetry Scroll", "طومار شعر کیرا", "r", "U", "k", ""),
    ("Gin's Dried Persimmon String", "رشته‌ی خرمالوی خشک گین", "r", "U", "s", ""), ("Gin's Shinsō Sheath Tassel", "منگوله‌ی غلاف شینسو گین", "r", "E", "s", "z"),
    ("Aizen's Glasses", "عینک آیزن", "n", "L", "k", "r"), ("Aizen's White Coat Clasp", "سگک ردای سفید آیزن", "n", "M", "r", "k"),
    ("Hinamori's Hair Wrap", "پارچه‌ی موی هیناموری", "r", "R", "k", "z"), ("Yamamoto's Beard Ribbon", "روبان ریش یاماموتو", "n", "M", "z", "r"),
    ("Sasakibe's Tea Set", "سرویس چای ساساکیبه", "r", "R", "z", "k"), ("Lisa's Magazine", "مجله‌ی لیسا", "r", "C", "z", ""),
    ("Kaien's Shiba Crest", "نشان خاندان شیبای کایئن", "n", "E", "z", "k"), ("Kūkaku's Firework", "آتش‌بازی کوکاکو", "r", "R", "k", "h"),
    ("Bonnie's Saddle Charm", "طلسم زین بانی", "r", "C", "h", ""), ("Substitute Shinigami Badge", "نشان شینیگامی جایگزین", "r", "E", "z", "r"),
    ("Ichigo's School Tie", "کراوات مدرسه‌ی ایچیگو", "n", "C", "z", ""), ("Tensa Zangetsu Coat Chain", "زنجیر ردای تنسا زانگتسو", "n", "L", "z", "s"),
    ("Isshin's Poster of Masaki", "پوستر ماساکیِ ایشین", "r", "U", "h", "l"), ("Tatsuki's Black Belt", "کمربند مشکی تاتسوکی", "n", "U", "h", ""),
    ("Keigo's Bandage", "باند کیگو", "r", "C", "h", ""), ("Mizuiro's Phone Strap", "بند گوشی میزوئیرو", "r", "C", "s", "l"),
    ("Karin's Soccer Keychain", "جاکلیدی فوتبال کارین", "r", "C", "s", ""), ("Yuzu's Apron", "پیش‌بند یوزو", "n", "C", "r", ""),
    ("Don Kanonji's Cane", "عصای دون کانونجی", "r", "U", "r", "l"), ("Kon's Plushie", "عروسک کن", "n", "C", "h", "l"),
    ("Urahara's Bucket Hat", "کلاه سطلی اوراهارا", "n", "L", "k", "s"), ("Urahara's Folding Fan", "بادبزن تاشوی اوراهارا", "r", "E", "k", "z"),
    ("Urahara's Wooden Geta", "پاپوش چوبی اوراهارا", "r", "U", "s", ""), ("Yoruichi's Cat Bell", "زنگوله‌ی گربه‌ای یوروئیچی", "n", "E", "s", "h"),
    ("Yoruichi's Shunkō Sash", "شال شونکوی یوروئیچی", "n", "L", "s", "h"), ("Tessai's Glasses", "عینک تسای", "n", "R", "k", "h"),
    ("Jinta's Baseball Bat Charm", "طلسم چوب بیسبال جینتا", "r", "C", "h", ""), ("Ururu's Cannon Strap", "بند توپ اورورو", "r", "U", "z", ""),
    ("Hiyori's Sandal", "صندل هیوری", "r", "U", "h", ""), ("Love's Shades", "عینک آفتابی لاو", "n", "U", "h", ""),
    ("Rose's Guitar Pick", "مضراب گیتار رز", "r", "U", "k", ""), ("Lisa's Sailor Ribbon", "روبان ملوانی لیسا", "n", "C", "z", ""),
    ("Mashiro's Goggles", "عینک محافظ ماشیرو", "n", "C", "s", ""), ("Kensei's 69 Tattoo Patch", "وصله‌ی خالکوبی ۶۹ کنسی", "r", "R", "h", "z"),
    ("Hachi's Barrier Pendant", "آویز سدّ هاچی", "n", "R", "k", "r"), ("Kaname's Justice Bracelet", "دستبند عدالت کانامه", "r", "R", "s", "z"), ("Chōjirō's Monocle", "عینک تک‌چشمی چوجیرو", "n", "U", "z", ""),
    ("Shūhei's Guitar Strap", "بند گیتار شوهِی", "n", "U", "z", ""), ("Akon's Horn Cap", "کلاهک شاخ آکون", "n", "C", "k", ""),
    ("Marechiyo's Croquette Bag", "کیسه‌ی کروکت مارچیو", "r", "C", "h", ""), ("Rikichi's Renji Fan Badge", "نشان طرفداری ریکیچی از رنجی", "r", "C", "z", ""),
    ("Yasochika's Kidō Corps Hood", "کلاه کوه‌ی سپاه کیدوی یاسوچیکا", "n", "E", "k", "r"), ("Ginrei Kuchiki's Scarf Clip", "گیره‌ی شال گینری کوچیکی", "n", "E", "z", "k"),
    ("Ganju's Bandana", "دستمال سر گانجو", "n", "C", "h", ""),
    ("Masaki's Hair Clip", "گیره‌ی موی ماساکی", "r", "R", "r", "h"),
    ("Kisuke's Hōgyoku Pouch", "کیسه‌ی هوگیوکوی کیسوکه", "n", "M", "k", "r"), ("Yoruichi's Onmitsukidō Mask", "ماسک اونمیتسوکیدوی یوروئیچی", "n", "E", "s", "z"),
    ("Unohana's Flower Pin", "سنجاق گل یونوهانا", "r", "R", "k", "r"),
    ("Kyōraku's Sake Cup", "جام ساکه‌ی کیوراکو", "r", "R", "z", "l"), ("Soi Fon's Hornet Tattoo Patch", "وصله‌ی خالکوبی زنبوری سوی‌فون", "r", "R", "s", "z"),
    ("Rangiku's Hair Clip", "گیره‌ی موی رانگیکو", "r", "C", "s", ""), ("Momo's Peach Charm", "طلسم هلوی مومو", "r", "U", "k", ""),
    ("Byakuya's Kuchiki Gloves", "دستکش‌های خاندان کوچیکی بیاکویا", "r", "E", "z", "k"), ("Rukia's Hollow Hunting Glove", "دستکش شکار هالوی روکیا", "r", "U", "k", ""),
    ("Renji's Tattoo Ink", "جوهر خالکوبی رنجی", "r", "U", "z", ""), ("Ichigo's Combat Pass", "مجوز نبرد ایچیگو", "r", "R", "z", "h"),
    ("Uryū's Quincy Cape Pin", "سنجاق شنل کوئینسی اوریو", "n", "U", "r", ""), ("Chad's Guitar Case Strap", "بند جعبه‌ی گیتار چد", "n", "U", "h", ""),
    ("Orihime's Bean Paste Bread", "نان خمیر لوبیای اوریهیمه", "r", "C", "r", ""), ("Tatsuki's Hair Tie", "کش موی تاتسوکی", "r", "C", "h", ""),
])

# ---- noble houses, Seireitei, Rukongai --------------------------------------------------------------------------------
_add("places", [
    ("Kuchiki Clan Crest", "نشان خاندان کوچیکی", "n", "E", "z", "k"), ("Shihōin Clan Crest", "نشان خاندان شیهوئین", "n", "E", "s", "h"),
    ("Shiba Clan Crest", "نشان خاندان شیبا", "n", "E", "k", "z"), ("Tsunayashiro Clan Crest", "نشان خاندان تسونایاشیرو", "n", "E", "r", "k"),
    ("Kyōraku Clan Crest", "نشان خاندان کیوراکو", "n", "E", "z", "r"), ("Senkaimon Gate Charm", "طلسم دروازه‌ی سنکایمون", "r", "R", "r", "s"),
    ("Hell Butterfly Wing Pendant", "آویز بال پروانه‌ی جهنمی", "n", "R", "s", "r"), ("Sōkyoku Halberd Shard", "پاره‌ی تبرزین سوکیوکو", "n", "L", "r", "z"),
    ("Sekkiseki Bracelet", "دستبند سکی‌سکی", "r", "R", "h", "r"), ("Kuchiki Manor Key", "کلید عمارت کوچیکی", "r", "R", "z", "l"),
    ("Inuzuri District Token", "ژتون محله‌ی اینوزوری", "r", "C", "h", ""), ("Zaraki District Token", "ژتون محله‌ی زاراکی", "r", "U", "h", "z"),
    ("Junrinan Stone", "سنگ جونرینان", "r", "C", "r", ""), ("Kusajishi Wildflower", "گل وحشی کوساجیشی", "n", "C", "s", ""),
    ("Shin'ō Academy Student Badge", "نشان دانشجوی آکادمی شینو", "r", "C", "k", ""), ("Seireitei White Wall Stone", "سنگ دیوار سفید سیرِیتِی", "r", "U", "h", ""),
    ("Gotei 13 Recruitment Scroll", "طومار عضوگیری گوتی ۱۳", "r", "U", "z", ""), ("Onmitsukidō Mask", "ماسک اونمیتسوکیدو", "n", "R", "s", "h"),
    ("Kidō Corps Hood", "کلاه سپاه کیدو", "n", "R", "k", "r"), ("Central 46 Seal", "مهر مرکز ۴۶", "r", "E", "k", "r"),
    ("Shinigami Women's Association Badge", "نشان انجمن زنان شینیگامی", "r", "U", "k", "l"), ("Fourth Division Medic Armband", "بازوبند امدادگر گروهان چهار", "r", "C", "k", ""), ("Eleventh Division Bell", "زنگوله‌ی گروهان یازده", "n", "U", "h", ""),
    ("Twelfth Division Lab Badge", "نشان آزمایشگاه گروهان دوازده", "r", "U", "k", ""), ("Second Division Kunai Charm", "طلسم کونای گروهان دو", "r", "C", "s", ""),
    ("Thirteenth Division Kaien Memorial", "یادبود کایئن گروهان سیزده", "n", "R", "z", "k"), ("Senzaikyū Tower Shard", "پاره‌ی برج سنزایکیو", "r", "R", "r", "h"),
    ("Penitentiary Robe Sash", "شال ردای زندان", "n", "C", "r", ""), ("Shrine of Kidō Key", "کلید زیارتگاه کیدو", "r", "R", "k", "l"),
    ("Dangai Current Stone", "سنگ جریان دنگای", "r", "R", "s", "r"), ("Kōtotsu Cleaner Scale", "فلس پاک‌کننده‌ی دنگای", "n", "E", "s", "r"),
    ("Muken Chain Link", "حلقه‌ی زنجیر موکن", "r", "L", "r", "h"), ("Jigoku Gate Chain", "زنجیر دروازه‌ی جیگوکو", "n", "E", "h", "r"),
    ("Kushanāda Claw", "چنگال کوشانادا", "r", "E", "h", "z"), ("Royal Realm Shard", "پاره‌ی قلمرو سلطنتی", "n", "L", "r", "k"),
    ("Shinō Training Sword Tassel", "منگوله‌ی شمشیر تمرینی شینو", "r", "C", "z", ""), ("Rukongai Water Flask", "قمقمه‌ی آب روکونگای", "r", "C", "r", ""),
    ("Seireitei Lantern", "فانوس سیرِیتِی", "n", "C", "k", ""),
    ("Karakura Town Map", "نقشه‌ی شهر کاراکورا", "r", "C", "s", "l"), ("Urahara Shop Receipt", "رسید مغازه‌ی اوراهارا", "r", "C", "k", "l"),
    ("Kurosaki Clinic Badge", "نشان کلینیک کوروساکی", "r", "C", "r", ""), ("Karakura High Student ID", "کارت دانش‌آموزی دبیرستان کاراکورا", "r", "C", "h", ""),
    ("Fake Karakura Town Pillar Shard", "پاره‌ی ستون کاراکورای جعلی", "n", "E", "h", "r"), ("Tenkai Kesshū Pillar Seal", "مهر ستون تنکای کشو", "n", "R", "k", "r"),
    ("Gigai Shell Fragment", "پاره‌ی پوسته‌ی گیگای", "r", "U", "r", ""), ("Denreishinki Strap", "بند دن‌ریشینکی", "r", "U", "s", ""),
    ("Kikanshinki Memory Charm", "طلسم کیکانشینکی", "n", "U", "k", ""), ("Senkaimon Hell Butterfly Cage", "قفس پروانه‌ی جهنمی", "n", "R", "s", "k"),
])

# ---- Hueco Mundo and Hollows ------------------------------------------------------------------------------------------
_add("hueco", [
    ("Las Noches Moon Shard", "پاره‌ی ماه لاس‌نوچس", "n", "E", "r", "h"), ("Menos Forest Crystal", "کریستال جنگل منوس", "r", "R", "h", "r"),
    ("Garganta Rift Shard", "پاره‌ی شکاف گارگانتا", "r", "R", "s", "r"), ("Hollow Hole Pendant", "آویز حفره‌ی هالو", "n", "R", "h", "s"),
    ("Menos Grande Mask Fragment", "پاره‌ی ماسک منوس گرانده", "n", "R", "h", "r"), ("Adjuchas Fang", "دندان آجوکاس", "r", "R", "h", "z"),
    ("Grand Fisher's Lure", "طعمه‌ی گرند فیشر", "n", "U", "k", ""), ("Shrieker's Bomb Leech", "زالوی انفجاری شریکر", "r", "C", "k", ""),
    ("Acidwire's Fang", "دندان اسیدوایر", "r", "C", "h", ""), ("Fishbone D's Mask Chip", "تراشه‌ی ماسک فیش‌بون دی", "n", "C", "h", ""),
    ("Hollow Bait Pill", "قرص طعمه‌ی هالو", "r", "C", "s", ""), ("Metastacia's Tentacle", "شاخک متاستاسیا", "n", "R", "k", "h"),
    ("Numb Chandelier's Egg", "تخم نام شاندلیر", "r", "U", "k", ""), ("Hexapodus Leg", "پای هگزاپودوس", "r", "U", "s", ""),
    ("Runuganga's Sand Grain", "دانه‌ی شن رونوگانگا", "n", "U", "h", ""), ("Gillian Black Cloak Thread", "نخ ردای سیاه گیلیان", "n", "U", "r", ""),
    ("Vasto Lorde Claw", "چنگال واستو لورد", "r", "E", "h", "s"), ("Hueco Mundo Quartz Tree Twig", "شاخه‌ی درخت کوارتز هوئکو موندو", "r", "U", "r", ""),
    ("Las Noches Throne Shard", "پاره‌ی تخت لاس‌نوچس", "n", "L", "r", "k"), ("Arrancar Uniform Sash", "شال لباس آرانکار", "n", "U", "h", ""),
    ("Hollowfication Shard", "پاره‌ی هالوشدن", "n", "E", "h", "r"), ("Cero Oscuras Ember", "اخگر سرو اسکوراس", "r", "L", "r", "h"),
    ("Gran Rey Cero Spark", "جرقه‌ی گران ری سرو", "r", "E", "r", "s"), ("Bala Bead", "مهره‌ی بالا", "r", "R", "s", "h"),
    ("Sonído Anklet", "خلخال سونیدو", "r", "R", "s", ""), ("Hierro Bracer", "مچ‌بند هیرو", "r", "R", "h", "z"),
    ("Pesquisa Antenna", "آنتن پسکیسا", "n", "U", "s", ""), ("Negación Fragment", "پاره‌ی نگاسیون", "n", "E", "h", "r"),
    ("Caja Negación Cube", "مکعب کاخا نگاسیون", "r", "L", "h", "k"), ("Hollow Herald Horn", "شیپور منادی هالو", "n", "U", "r", ""),
])

# ---- Bount, filler arcs, Shinigami Golden, Karakura extras --------------------------------------------------------------
_add("filler", [
    ("Kariya's Messer Pendant", "آویز مسر کاریا", "n", "E", "r", "z"), ("Ugaki's Doll Charm", "طلسم عروسک اوگاکی", "r", "R", "r", "h"),
    ("Ichinose's Nijigasumi Tassel", "منگوله‌ی نیجی‌گاسومی ایچینوسه", "r", "R", "z", "s"), ("Mabashi's Ruri Wing", "بال روری ماباشی", "n", "U", "s", ""),
    ("Yoshino's Flower Pin", "سنجاق گل یوشینو", "r", "U", "k", ""), ("Go Koga's Dalk Chain", "زنجیر دالک گو کوگا", "n", "R", "h", "r"),
    ("Sawatari's Pocket Watch", "ساعت جیبی ساواتاری", "n", "U", "s", ""), ("Muramasa's Hilt Ribbon", "روبان دسته‌ی موراماسا", "r", "L", "k", "z"), ("Kōga's Kuchiki Scarf", "شال کوچیکی کوگا", "n", "E", "z", "k"),
    ("Amagai's Bakkōtō Bracer", "مچ‌بند باکوتوی آماگای", "r", "E", "z", "h"), ("Kasumiōji Clan Fan", "بادبزن خاندان کاسومی‌اوجی", "r", "R", "k", "s"),
    ("Rurichiyo's Hair Ornament", "زیور موی روریچیو", "n", "R", "k", "l"), ("Reigai Shell Fragment", "پاره‌ی پوسته‌ی ریگای", "r", "R", "z", "r"),
    ("Kageroza's Mirror Shard", "پاره‌ی آینه‌ی کاگروزا", "n", "E", "k", "r"), ("Nozomi's Hair Clip", "گیره‌ی موی نوزومی", "r", "R", "k", "s"),
    ("Zanpakutō Rebellion Banner", "پرچم شورش زانپاکتوها", "n", "R", "z", "h"), ("Tōjūrō's Fan", "بادبزن توجورو", "r", "U", "k", ""),
    ("Sōma's Lantern", "فانوس سوما", "n", "U", "r", ""), ("Hollow Ichigo's Cloak Tatter", "تکه‌ی ردای ایچیگوی هالو", "n", "L", "z", "h"),
    ("Shinigami Golden Mascot Pin", "سنجاق نماد شینیگامی گلدن", "r", "C", "s", "l"), ("Chappy Candy Dispenser", "دستگاه آب‌نبات چپی", "r", "C", "s", ""), ("Karakura Superheroes Badge", "نشان ابرقهرمانان کاراکورا", "r", "U", "h", "l"),
    ("Hell Verse Chain Shard", "پاره‌ی زنجیر جهنم", "n", "E", "h", "k"),
    ("Kokutō's Chain", "زنجیر کوکوتو", "n", "L", "h", "z"), ("Shuren's Horn", "شاخ شورن", "n", "R", "h", "r"),
    ])

# ---- spirit trinkets (common keepsakes that fill the low colours with real Bleach things) -------------------------------
_add("trinket", [
    ("Shiratama Dango Charm", "طلسم دانگوی شیراتاما", "r", "C", "r", ""), ("Seireitei Tea Bowl", "کاسه‌ی چای سیرِیتِی", "r", "C", "k", ""),
    ("Hell Butterfly Cocoon Thread", "نخ پیله‌ی پروانه‌ی جهنمی", "r", "C", "s", ""), ("Reishi Prayer Beads", "تسبیح ریشی", "n", "C", "r", ""),
    ("Konpaku Bell", "زنگوله‌ی کونپاکو", "n", "C", "r", ""), ("Asauchi Hilt Wrap", "نوار دسته‌ی آساؤچی", "r", "C", "z", ""),
    ("Soul Ticket of Konsō", "بلیت روح کونسو", "r", "C", "k", ""), ("Plus Soul Chain Link", "حلقه‌ی زنجیر روح پلاس", "n", "C", "h", ""),
    ("Hollow Mask Crumb", "خرده‌ی ماسک هالو", "n", "C", "h", ""), ("Gigai Hair Pin", "سنجاق موی گیگای", "r", "C", "s", ""),
    ("Ryōka Entry Pass", "مجوز ورود ریوکا", "r", "C", "s", "l"), ("Rukongai Straw Sandal", "صندل حصیری روکونگای", "r", "C", "s", ""),
    ("Shinigami Uniform Sash", "شال لباس شینیگامی", "n", "C", "z", ""), ("Zanjutsu Practice Bracer", "مچ‌بند تمرین زنجوتسو", "r", "C", "z", ""),
    ("Hakuda Hand Wraps", "باند دست هاکودا", "r", "C", "h", ""), ("Hohō Leg Wraps", "باند پای هوهو", "r", "C", "s", ""),
    ("Kidō Chalk", "گچ کیدو", "r", "C", "k", ""), ("Reiatsu Sensor Pin", "سنجاق حسگر ریاتسو", "r", "C", "r", ""),
    ("Kurosaki Family Photo", "عکس خانوادگی کوروساکی", "n", "U", "r", "l"), ("Zanpakutō Polishing Cloth", "دستمال صیقل زانپاکتو", "r", "U", "z", ""),
    ("Gotei Messenger Scroll", "طومار پیک گوتی", "r", "U", "s", ""), ("Kidō Ward Paper", "کاغذ محافظ کیدو", "n", "U", "k", ""),
    ("Shinigami Lieutenant Training Weights", "وزنه‌های تمرین ستوان", "r", "U", "h", ""), ("Reishi Thread Bracelet", "دستبند نخ ریشی", "r", "U", "r", ""),
    ("Rukongai Festival Mask", "ماسک جشن روکونگای", "n", "U", "s", "l"), ("Hollow Detector Phone", "گوشی ردیاب هالو", "r", "U", "s", ""),
    ("Captain Meeting Bell", "زنگ جلسه‌ی کاپیتان‌ها", "n", "R", "r", "k"), ("Bankai Training Doll", "عروسک تمرین بانکای", "n", "R", "z", "h"),
    ("Tenshintai Doll Cloth", "پارچه‌ی عروسک تنشین‌تای", "n", "R", "z", "r"), ("Shunkō Training Wraps", "باند تمرین شونکو", "r", "R", "s", "h"),
    ("Reiraku Ribbon", "روبان ریراکو", "n", "R", "r", "s"), ("Inner World Sky Shard", "پاره‌ی آسمان دنیای درون", "n", "E", "r", "z"), ("Jinzen Meditation Mat Thread", "نخ زیرانداز مراقبه‌ی جینزن", "r", "R", "z", "k"),
    ("Shikai Release Charm", "طلسم رهاسازی شیکای", "r", "R", "z", "r"), ("Bankai Release Charm", "طلسم رهاسازی بانکای", "r", "E", "z", "r"),
    ("Resurrección Release Charm", "طلسم رهاسازی رسورکسیون", "r", "E", "h", "r"), ("Vollständig Release Charm", "طلسم رهاسازی فولشتندیگ", "r", "E", "r", "s"),
    ("Fullbring Release Charm", "طلسم رهاسازی فول‌برینگ", "r", "E", "z", "s"), ("Hollow Mask Release Charm", "طلسم رهاسازی ماسک هالو", "r", "E", "z", "h"),
])

# ---- legendary relics of the story (gold and red) ------------------------------------------------------------------------
_add("legend", [
    ("Ōken Prism", "منشور اوکن", "n", "M", "r", "k"), ("Soul King's Right Arm Shard", "پاره‌ی بازوی راست شاه ارواح", "n", "M", "h", "r"),
    ("Mimihagi's Eye Charm", "طلسم چشم میمیهاگی", "n", "M", "r", "s"), ("Pernida's Nerve Thread", "رشته‌ی عصب پرنیدا", "r", "L", "k", "h"),
    ("Ichibei's Name Brush Ink", "جوهر نام‌گذاری ایچیبه", "r", "L", "k", "r"), ("Hōgyoku Light Fragment", "پاره‌ی نور هوگیوکو", "n", "M", "r", "h"),
    ("Kyōka Suigetsu Illusion Shard", "پاره‌ی توهم کیوکا سویگتسو", "n", "L", "k", "s"), ("Zangetsu Old Man's Coat Button", "دکمه‌ی پالتوی پیرمرد زانگتسو", "r", "L", "z", "r"),
    ("Mugetsu Ember", "اخگر موگتسو", "r", "M", "z", "r"), ("Kaname's Suzumushi Tsuishiki Bell", "زنگ سوزوموشی تسوئی‌شیکی", "n", "L", "s", "k"),
    ("Yamamoto's Zanka no Tachi Ash", "خاکستر زانکا نو تاچی", "r", "M", "z", "h"), ("Unohana's Minazuki Bankai Bead", "مهره‌ی بانکای مینازوکی", "n", "L", "k", "h"),
    ("Kenpachi's Nozarashi Shikai Thread", "رشته‌ی شیکای نوزاراشی", "r", "M", "h", "z"), ("Byakuya's Shūkei Hakuteiken Wing", "بال شوکی هاکوتیکن", "n", "L", "z", "s"),
    ("Hitsugaya's Hyōten Hyakkasō Snowflake", "دانه‌ی برف هیوتن هیاکاسو", "n", "L", "k", "z"), ("Rukia's Hakka no Togame Frost", "شبنم یخی هاکا نو توگامه", "n", "L", "k", "r"),
    ("Renji's Sōō Zabimaru Fang", "دندان سوئو زابی‌مارو", "r", "L", "z", "h"), ("Uryū's Antithesis Arrow", "پیکان آنتی‌تزیس اوریو", "r", "L", "r", "s"),
    ("Ichigo's Final Getsuga Ember", "اخگر آخرین گتسوگای ایچیگو", "r", "L", "z", "r"), ("Aizen's Chrysalis Shell", "پوسته‌ی پیله‌ی آیزن", "n", "M", "k", "h"),
    ("Starrk's Los Lobos Fur", "پشم لوس لوبوس استارک", "n", "L", "r", "s"), ("Barragan's Respira Ash", "خاکستر رسپیرای بارگان", "n", "L", "h", "k"),
    ("Harribel's Tiburón Fin", "باله‌ی تیبورون هریبل", "n", "L", "s", "r"), ("Ulquiorra's Lanza del Relámpago", "شعله‌ی لانسا دل رلامپاگوی اولکیورا", "r", "M", "r", "z"),
    ("Grimmjow's Desgarrón Claw", "پنجه‌ی دسگارون گریمجو", "r", "L", "h", "s"), ("Nnoitra's Santa Teresa Crescent", "هلال سانتا ترزای نوایترا", "r", "L", "z", "h"),
    ("Yhwach's Auswählen Light", "نور آوسوِلن یوهاباخ", "n", "M", "r", "k"), ("Haschwalth's Freund Schild Feather", "پر فروند شیلد هاشوالث", "n", "L", "z", "r"),
    ("Askin's Gift Ball", "توپ هدیه‌ی آسکین", "r", "L", "k", "h"), ("Gremmy's Imagination Orb", "گوی تخیل گرمی", "n", "L", "k", "r"),
])

# ---- extra seasonal and Iranian keepsakes (the bot's own culture) ---------------------------------------------------------
_add("seasonal", [
    ("Nowruz Haft-Sin Coin", "سکه‌ی هفت‌سین نوروز", "r", "U", "r", "l"), ("Yalda Pomegranate Charm", "طلسم انار یلدا", "n", "U", "h", "l"),
    ("Chaharshanbe Suri Ember", "اخگر چهارشنبه‌سوری", "r", "U", "k", "l"), ("Sizdah Bedar Sabzeh Knot", "گره سبزه‌ی سیزده‌به‌در", "r", "C", "s", "l"),
    ("Mehregan Autumn Leaf", "برگ پاییزی مهرگان", "n", "C", "r", "l"), ("Ramadan Lantern", "فانوس رمضان", "n", "U", "k", "l"),
    ("Bot Birthday Candle", "شمع تولد ربات", "r", "R", "r", "l"), ("Season End Trophy Pin", "سنجاق جام پایان فصل", "r", "R", "z", "l"),
    ("Persian Rug Thread Bracelet", "دستبند نخ فرش", "r", "C", "h", "l"), ("Saffron Tea Cup", "فنجان چای زعفرانی", "r", "C", "r", "l"),
])


_FLAVOR = {  # (fa, en) one line per family
    "lieutenant": ("بازوبند رسمی ستوان‌های گوتی ۱۳.", "The official armband of a Gotei 13 lieutenant."),
    "captain": ("هائوری سفید کاپیتان، با شماره‌ی گروهان پشتش.", "A captain's white haori, the division number on its back."),
    "seat": ("سنجاق افسرهای رده‌دار.", "The pin of a seated officer."),
    "espada": ("نشانی از ده اسپادای لاس‌نوچس.", "A mark of the ten Espada of Las Noches."),
    "arrancar": ("یادگاری از ارتش آرانکارها.", "A keepsake of the Arrancar army."),
    "schrift": ("مدال حرفی که یوهاباخ به یک اشترن‌ریتر داد.", "The letter Yhwach gave a Sternritter."),
    "quincy": ("یادگاری از کوئینسی‌ها.", "A Quincy keepsake."),
    "tsuba": ("گارد شمشیر یک زانپاکتوی معروف.", "The guard of a famous Zanpakutō."),
    "visored": ("ماسک هالوی یکی از ویزوردها.", "The Hollow mask of a Visored."),
    "zero": ("از گنجینه‌ی گروهان صفر.", "From the treasury of Squad Zero."),
    "fullbring": ("شیئی که فول‌برینگر به آن روح داد.", "An object a Fullbringer gave a soul."),
    "people": ("وسیله‌ی شخصی یک شخصیت بلیچ.", "A Bleach character's own belonging."),
    "places": ("یادگاری از سرزمین‌های بلیچ.", "A keepsake from the lands of Bleach."),
    "hueco": ("از شن‌های هوئکو موندو.", "From the sands of Hueco Mundo."),
    "filler": ("از قصه‌های فرعی بلیچ.", "From Bleach's side stories."),
    "trinket": ("یک یادگاری کوچک.", "A small keepsake."),
    "legend": ("ردی از بزرگ‌ترین قدرت‌های داستان.", "A trace of the story's greatest powers."),
    "seasonal": ("یادگار مناسبتی.", "A seasonal keepsake."),
}
_SFA = {"zanjutsu": "زنجوتسو", "kido": "کیدو", "hakuda": "هاکودا", "hoho": "هوهو", "reiatsu": "ریاتسو"}


def _build():
    out = []
    for n, (en, fa, slot, c, s1, s2, grp) in enumerate(_E, 1):
        iid = f"ac_{n:03d}"
        main = MAIN[c] + (n % 3 == 0)          # a little spread inside one colour
        stats = {"stat": STAT[s1], "bonus": main}
        d_fa, d_en = [f"+{main} {_SFA[STAT[s1]]}"], [f"+{main} {STAT[s1]}"]
        if s2 == "l":
            stats["luck"] = LUCK[c]
            d_fa.append(f"+{LUCK[c]} شانس")
            d_en.append(f"+{LUCK[c]} luck")
        elif s2 and SECOND[c]:
            stats["stat2"], stats["bonus2"] = STAT[s2], SECOND[c]
            d_fa.append(f"+{SECOND[c]} {_SFA[STAT[s2]]}")
            d_en.append(f"+{SECOND[c]} {STAT[s2]}")
        f_fa, f_en = _FLAVOR.get(grp, ("", ""))
        out.append({"_id": iid, "item_id": iid, "category": "accessory", "subtype": "ring" if slot == "r" else "necklace",
                    "name_en": en, "name_fa": fa, "desc_fa": "، ".join(d_fa) + ". " + f_fa, "desc_en": ", ".join(d_en) + ". " + f_en,
                    "rarity": RAR[c], "stats": stats, "effect": None, "slot": "accessory", "level_req": LEVEL[c],
                    "base_price": PRICE[c], "sell_price": int(PRICE[c] * 0.4), "tradeable": c != "M", "stack_max": 1,
                    "acc_group": grp, "special": c == "M"})
    return out


ACCESSORIES = _build()
