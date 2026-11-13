"""Bleach-flavoured depth layer: blade spirits, character epithets, dungeon floors, item flavour, streaks.
Pure data + tiny helpers; every entry is (fa, en)."""

SPIRIT_TYPE = {
    "melee": ("روحش ساده است: «نزدیک‌تر بیا.»", "Its spirit is simple: “Come closer.”"),
    "elemental": ("عنصر در رگ‌هایش می‌تپد؛ تیغه فقط مجرای آن است.", "The element pulses in its veins; the blade is merely its channel."),
    "kido": ("هر برش، وردی نیمه‌تمام است که ریاتسو کاملش می‌کند.", "Every cut is a half-spoken incantation that reiatsu completes."),
    "illusion": ("آنچه می‌بینی، تیغه تعیین می‌کند.", "What you see, the blade decides."),
    "living": ("تیغه نفس می‌کشد؛ با تو بزرگ می‌شود و با تو زخم می‌خورد.", "The blade breathes; it grows and bleeds with you."),
    "defensive": ("تیغه‌ای که می‌ایستد تا تو بمانی.", "A blade that stands so you may remain."),
    "ranged": ("فاصله دوست دشمن است؛ این تیغه از آن می‌گذرد.", "Distance is the enemy's friend; this blade crosses it."),
    "speed": ("پیش از آنکه بشنوی، تمام شده است.", "It is over before you hear it."),
    "hybrid": ("یک روح، دو چهره؛ به‌اندازه‌ی ارادهٔ تو تغییر می‌کند.", "One spirit, two faces; it bends to your will."),
}
SPIRIT_ELEM = {
    "fire": ("هاله‌اش گرم و بی‌قرار است.", "Its aura is warm and restless."),
    "ice": ("هاله‌اش سرد و ساکت است.", "Its aura is cold and still."),
    "lightning": ("هاله‌اش می‌ترکد و می‌گذرد.", "Its aura cracks and passes."),
    "earth": ("هاله‌اش سنگین و صبور است.", "Its aura is heavy and patient."),
    "water": ("هاله‌اش روان و بی‌شکل است.", "Its aura is fluid and formless."),
    "poison": ("هاله‌اش آرام است؛ و همین خطرناک است.", "Its aura is calm, and that is the danger."),
    "shadow": ("هاله‌اش سایه‌ای است که صاحب ندارد.", "Its aura is a shadow with no owner."),
    "light": ("هاله‌اش چشم را می‌زند و دروغ را می‌سوزاند.", "Its aura dazzles and burns away lies."),
}


def spirit_line(weapon: dict, lang: str) -> str:
    i = 0 if lang == "fa" else 1
    return SPIRIT_TYPE[weapon["weapon_type"]][i] + " " + SPIRIT_ELEM[weapon["element"]][i]


CHAR_EPI = {
    "Kon": ("عروسکی پر از حرف، با دلی بزرگ.", "A plush full of words, with a big heart."),
    "Izuru Kira": ("غمی آرام که شمشیر را سنگین می‌کند.", "A quiet sorrow that makes the sword heavy."),
    "Shuhei Hisagi": ("شمشیرش را روی خاطره تیز می‌کند.", "He sharpens his sword on memory."),
    "Momo Hinamori": ("ایمانی که شکست و دوباره ساخته شد.", "A faith that broke and was rebuilt."),
    "Isane Kotetsu": ("دستی که درمان می‌کند، حتی وقتی می‌لرزد.", "A healing hand, even when it trembles."),
    "Ikkaku Madarame": ("جنگ را مثل جشن می‌خواهد.", "He treats battle like a festival."),
    "Yumichika Ayasegawa": ("زیبایی را هم سلاح کرده است.", "He has made beauty a weapon."),
    "Rose Otoribashi": ("نغمه‌ای که پیش از ضربه می‌رسد.", "A melody that arrives before the strike."),
    "Hiyori Sarugaki": ("کوچک، تند، و بی‌حوصله‌ی بزرگ‌ترها.", "Small, sharp, and tired of her elders."),
    "Yasutora Sado": ("مشتی که از دل می‌آید.", "A fist that comes from the heart."),
    "Orihime Inoue": ("مهربانی‌ای که واقعیت را عقب می‌زند.", "A kindness that pushes reality back."),
    "Uryu Ishida": ("غرور کوئینسی، دقت تیرانداز.", "A Quincy's pride, an archer's precision."),
    "Rukia Kuchiki": ("یخی که از قلبی گرم می‌آید.", "Ice that comes from a warm heart."),
    "Renji Abarai": ("اراده‌ای که از روکونگای تا اینجا بالا آمد.", "A will that climbed from Rukongai to here."),
    "Rangiku Matsumoto": ("لبخندی که خاکستر را پنهان می‌کند.", "A smile that hides ash."),
    "Soi Fon": ("سایه‌ای وفادار؛ یک نیشش کافی است.", "A loyal shadow; one sting is enough."),
    "Sajin Komamura": ("گرگی وفادار؛ شرافتش از شمشیرش سنگین‌تر است.", "A loyal wolf whose honor outweighs his sword."),
    "Mayuri Kurotsuchi": ("دانش بی‌وجدان؛ جهان آزمایشگاه اوست.", "Knowledge without conscience; the world is his lab."),
    "Shinji Hirako": ("لبخندی کج، و ماسکی دوم.", "A crooked smile, and a second mask."),
    "Grimmjow Jaegerjaquez": ("پنجه‌ای که قفس نمی‌شناسد.", "A claw that knows no cage."),
    "Byakuya Kuchiki": ("غرور اشرافی؛ قلبی که زخم را نشان نمی‌دهد.", "Noble pride; a heart that hides its wounds."),
    "Toshiro Hitsugaya": ("یخ در قامتی کوچک؛ فرمانده‌ی زمستان.", "Frost in a small frame; commander of winter."),
    "Kenpachi Zaraki": ("فقط برای یک نبرد خوب زنده است.", "He lives only for a good fight."),
    "Yoruichi Shihoin": ("برقی سیاه که زمان را هم جا می‌گذارد.", "A black flash that leaves even time behind."),
    "Kisuke Urahara": ("کلاهی که لبخند و هزار نقشه را پنهان می‌کند.", "A hat that hides a smile and a thousand plans."),
    "Ulquiorra Cifer": ("تهی‌ای که می‌خواهد دل را بفهمد.", "An emptiness that wishes to understand the heart."),
    "Coyote Starrk": ("تنهایی‌ای که به جنگ تبدیل شد.", "A loneliness turned into war."),
    "Nelliel Tu Odelschwanck": ("مهربانی‌ای که روزی قدرتش بود.", "A kindness that was once her strength."),
    "Tier Harribel": ("ملکه‌ای که برای یارانش می‌جنگد.", "A queen who fights for her people."),
    "Kaname Tosen": ("عدالتی که چشم ندارد.", "A justice without eyes."),
    "Ichigo Kurosaki": ("نگهبانی که برای محافظت از همه مرزها می‌گذرد.", "A guardian who crosses every border to protect."),
    "Shunsui Kyoraku": ("شوخی‌ای که تیغی را پنهان می‌کند.", "A joke that hides a blade."),
    "Jushiro Ukitake": ("تنی ناتوان، با سالم‌ترین دل.", "A frail body with the healthiest heart."),
    "Gin Ichimaru": ("لبخندی که راز را پیش از تو می‌دانست.", "A smile that knew the secret before you."),
    "Jugram Haschwalth": ("تعادل؛ بی‌عجله و بی‌خطا.", "Balance; no haste, no error."),
    "Genryusai Yamamoto": ("آتشی هزارساله؛ نظم با شعله.", "A thousand-year fire; order through flame."),
    "Sosuke Aizen": ("کسی که از ابتدا همه‌چیز را دیده بود.", "One who foresaw everything from the start."),
    "Yhwach": ("پدر ارواح؛ سرنوشت در مشت اوست.", "Father of souls; fate in his fist."),
}

DUNGEON_LORE = {  # id -> {entry, mid, final} each (fa, en)
    "trial": {"entry": ("درهای آزمون باز می‌شوند. اینجا شینیگامی ساخته می‌شود — یا شکسته.", "The trial gates open. Here Soul Reapers are forged, or broken."),
              "mid": ("طبقه‌ها سخت‌تر می‌شوند؛ تیغه‌ات را محکم بگیر.", "The floors grow harder. Hold your blade tight."),
              "final": ("آخرین در؛ آنچه پشت آن است، تو را می‌سنجد.", "The last door. What lies behind it will measure you.")},
    "hollow_den": {"entry": ("بوی گرسنگی در هواست. لانه نفس می‌کشد.", "Hunger fills the air. The den breathes."),
                   "mid": ("ماسک‌های ترک‌خورده از دیوار نگاهت می‌کنند.", "Cracked masks watch you from the walls."),
                   "final": ("عمیق‌ترین نقطه؛ مادر لانه بیدار است.", "The deepest point. The den's mother is awake.")},
    "menos_forest": {"entry": ("جنگل بی‌برگ منوس؛ هر درخت یک استخوان است.", "The leafless Menos Forest; every tree is a bone."),
                     "mid": ("سایه‌های عظیم میان شاخه‌ها حرکت می‌کنند.", "Colossal shadows move between the branches."),
                     "final": ("قلب جنگل؛ بزرگ‌ترین سایه منتظر توست.", "The forest's heart. The greatest shadow awaits you.")},
    "noches_depths": {"entry": ("پله‌های اعماق لاس‌نوچس؛ نور اینجا دروغ می‌گوید.", "The stairs into Las Noches' depths; light lies here."),
                      "mid": ("هر تالار پژواک شمشیری است که پیش‌تر شکست.", "Every hall echoes a sword that already broke."),
                      "final": ("تالار آخر؛ سکوتی که فقط یک اسپادا می‌شکند.", "The final hall, a silence only an Espada can break.")},
    "quincy_fort": {"entry": ("دژ کوئینسی؛ صلیب‌ها در دیوار می‌درخشند.", "The Quincy fortress; crosses glow in the walls."),
                    "mid": ("تیرها از سایه می‌آیند، پیش از آنکه ببینی.", "Arrows come from the shadows before you see them."),
                    "final": ("برج بالا؛ فرمانده‌ی دژ کمان را کشیده است.", "The high tower. The fortress commander has drawn his bow.")},
    "palace_trial": {"entry": ("آزمون کاخ سلطنتی؛ اینجا لیاقت سنجیده می‌شود، نه قدرت.", "The Royal Palace trial; worth is measured here, not power."),
                     "mid": ("هر طبقه، گذشته‌ات را بازگو می‌کند.", "Each floor retells your past."),
                     "final": ("آستانه‌ی نهایی؛ آنکه می‌گذرد، دیگر همان نیست.", "The final threshold. Whoever crosses is no longer the same.")},
    "dangai_rift": {"entry": ("شکاف دنگای؛ زمین زیر پایت می‌دود.", "The Dangai rift; the ground runs beneath you."),
                    "mid": ("زمان کش می‌آید؛ هر ضربه سنگین‌تر از قبل است.", "Time stretches; every blow weighs more."),
                    "final": ("انتهای شکاف؛ یا خروج، یا بلعیده شدن.", "The rift's end: exit, or be devoured.")},
}


def dungeon_line(dungeon_id: str, stage: int, total: int, lang: str) -> str:
    lore = DUNGEON_LORE.get(dungeon_id)
    if not lore:
        return ""
    key = "entry" if stage <= 1 else "final" if stage >= total else "mid"
    return lore[key][0 if lang == "fa" else 1]


ITEM_FLAVOR = {  # subtype -> variants
    "material": [("از میدان نبرد جمع شده؛ هنوز ریاتسو در آن می‌تپد.", "Gathered from a battlefield; reiatsu still pulses within."),
                 ("آهنگر می‌گوید: ماده‌ی خوب، نصف تیغه است.", "A smith would say: good material is half a blade."),
                 ("ذره‌ای از جهانی دیگر.", "A mote from another world.")],
    "potion": [("طعمش تلخ است؛ اثرش شیرین.", "Bitter to taste, sweet in effect."),
               ("گاهی یک نفس تازه از هر شمشیری بهتر است.", "Sometimes a fresh breath beats any sword.")],
    "book": [("صفحه‌هایی که دست‌به‌دست شده‌اند.", "Pages that have passed through many hands."),
             ("دانش، بی‌صداترین نوع قدرت است.", "Knowledge is the quietest kind of power.")],
    "evolution": [("قدرتی ناتمام که منتظر لایقش است.", "Unfinished power, waiting for one worthy."),
                  ("لرزشی از چیزی بزرگ‌تر در آن حس می‌شود.", "A tremor of something greater hums inside.")],
    "cosmetic": [("قدرت نمی‌دهد؛ فقط نشان می‌دهد تو که هستی.", "It grants no power; it only shows who you are."),
                 ("یادگاری که از دور هم دیده می‌شود.", "A keepsake visible from afar.")],
    "relic": [("یادگار روزگاری که نام‌ها معنا داشتند.", "A relic of days when names had meaning."),
              ("سنگینی تاریخ در دست توست.", "The weight of history rests in your hand.")],
    "egg": [("درونش چیزی نفس می‌کشد و منتظر ریاتسوی توست.", "Something breathes within, waiting for your reiatsu.")],
}

STREAK_LINE = {
    1: ("گام اول.", "The first step."),
    3: ("سه روز پیاپی؛ عادت شکل می‌گیرد.", "Three days in a row; a habit takes shape."),
    7: ("هفت روز! ارواح نامت را به یاد می‌سپارند.", "Seven days! The spirits begin to remember your name."),
    14: ("دو هفته؛ وفاداری‌ات از تیغه‌ات محکم‌تر است.", "Two weeks; your loyalty is firmer than your blade."),
    30: ("یک ماه کامل. افسانه‌ها همین‌طور آغاز می‌شوند.", "A full month. This is how legends begin."),
}


def streak_line(streak: int, lang: str) -> str:
    v = STREAK_LINE.get(streak)
    return v[0 if lang == "fa" else 1] if v else ""


# ---- Bleach content pack 2 ----
DUNGEON_LORE.update({
    "academy_exam": {"entry": ("سالن امتحان؛ ناظرانی خاموش با قلم در دست نگاهت می‌کنند.", "The exam hall; silent proctors watch you, pens in hand."),
                     "mid": ("سؤال‌ها دشوارتر می‌شوند؛ کیدو دیگر بازی نیست.", "The questions grow harder; kidō is no game now."),
                     "final": ("آخرین آزمون؛ تیغه‌ات را می‌شناسی؟", "The last exam. Do you know your blade?")},
    "urahara_pit": {"entry": ("گودالی که اوراهارا برای «بازی» ساخته؛ قوانینش را فقط خودش می‌داند.", "A pit Urahara built for “games”; only he knows its rules."),
                    "mid": ("هر طبقه تله‌ی تازه‌ای دارد و همه خنده‌دارند، جز برای تو.", "Every floor has a new trap, and all are funny, except to you."),
                    "final": ("عمیق‌ترین طبقه؛ صدایی از بالا: «کمی بیشتر!»", "The deepest floor; a voice from above: “A little more!”")},
    "senzaikyu_tower": {"entry": ("پله‌های برج سنزایکیو؛ هر پله یک سوگند را سنگین می‌کند.", "The steps of Senzaikyū Tower; each one weighs down an oath."),
                        "mid": ("زنجیرها در هوا زمزمه می‌کنند؛ نگهبان‌ها بی‌صدا نزدیک می‌شوند.", "Chains whisper in the air; guards approach in silence."),
                        "final": ("طبقه‌ی بالا؛ دری که به آسمان باز می‌شود.", "The top floor; a door that opens onto the sky.")},
    "maggot_nest": {"entry": ("پایین می‌روی؛ هوا سنگین‌تر و نور کم‌رنگ‌تر می‌شود.", "You descend; the air thickens and the light thins."),
                    "mid": ("هر سلول یک داستان است و هیچ‌کدام پایان خوشی ندارد.", "Each cell is a story, and none of them end well."),
                    "final": ("عمیق‌ترین سلول؛ آنچه در آن است نمی‌خواهد دیده شود.", "The deepest cell; what lies in it does not wish to be seen.")},
    "muken": {"entry": ("دروازه‌ی موکن؛ هر که وارد شود شاید هرگز همان بیرون نیاید.", "The gate of Muken; whoever enters may never leave the same."),
              "mid": ("زمین تکرار می‌شود و زنجیرها پیش از تو می‌رسند.", "The ground repeats and the chains reach you before you reach them."),
              "final": ("پایین‌ترین نقطه؛ فقط خاموشی و یک نگهبان.", "The lowest point; only silence and one warden.")},
})
CHAR_EPI.update({
    "Yachiru Kusajishi": ("خنده‌ای کوچک روی شانه‌ی غول‌ها.", "A small laugh perched on a giant's shoulder."),
    "Kaien Shiba": ("نامش هنوز در دل جوخه‌ی ۱۳ زنده است.", "His name still lives in the heart of the 13th Division."),
    "Ginrei Kuchiki": ("سکوت پیرمردی که یک خاندان را بر دوش دارد.", "The silence of an old man carrying a whole clan."),
    "Cirucci Sanderwicht": ("زبانی تیز و ضربه‌ای بی‌رحم.", "A sharp tongue and a ruthless strike."),
    "Di Roy Linker": ("تیغه‌ای که با هر ضربه محکم‌تر می‌شود.", "A blade that grows firmer with every blow."),
    "Luppi Antenor": ("نگاهی که هرگز آرام نمی‌گیرد.", "A gaze that never rests."),
    "Nirgge Parduoc": ("کوهی از سکوت و فولاد.", "A mountain of silence and steel."),
    "Shawlong Koufang": ("نظمی خاموش پشت هر حرکتش.", "A silent order behind every move."),
    "Avirama Redder": ("سرسخت‌تر از سنگ‌هایی که می‌شکند.", "Stubborner than the stones he breaks."),
    "Meninas McAllon": ("غرور سربازی که ستاره‌اش را کسب کرده.", "The pride of a soldier who earned her star."),
    "Liltotto Lamperd": ("زبانی تیز و اشتهایی بزرگ‌تر.", "A sharp tongue and a bigger appetite."),
    "Robert Accutrone": ("آرامش سربازی پیش از هر یورش.", "A soldier's calm before every charge."),
    "Jerome Guizbatt": ("سایه‌ای که ردش را پاک می‌کند.", "A shadow that wipes out its own trail."),
    "Gremmy Thoumeaux": ("خیالی که واقعیت را کنار می‌زند.", "An imagination that pushes reality aside."),
    "Giselle Gewelle": ("لبخندی که سربازان مرده را بلند می‌کند.", "A smile that raises dead soldiers."),
    "Quilge Opie": ("شکارچی‌ای که قلمروش را با ریاتسو نشان می‌کند.", "A hunter who marks his territory with reiatsu."),
    "As Nodt": ("خشمی که مثل بیماری پخش می‌شود.", "A wrath that spreads like a plague."),
    "Soken Ishida": ("حکمتی خاموش از خاندانی که ایستاد.", "Quiet wisdom from a clan that stood its ground."),
    "Oetsu Nimaiya": ("قدرتی که پایه‌های جهان را نگه می‌دارد.", "Power that holds up the foundations of the world."),
    "Kirio Hikifune": ("دستی که بخشیدن و ساختن را با هم می‌داند.", "A hand that knows both mercy and making."),
    "Senjumaru Shutara": ("سازنده‌ای که با اراده‌اش شکل می‌دهد.", "A maker who shapes with her will."),
    "Tenjiro Kirinji": ("زخم هر نبرد را مثل یک درس نگه می‌دارد.", "He keeps each battle's scar like a lesson."),
})
