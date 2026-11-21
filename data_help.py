"""In-game guide topics (راهنما). Pure text, keyed by language. Add a topic here and a button in handlers_panels.

Every number below is taken from the code (service_player, engine, data_races), so the guide and the game agree.
"""

STATS_TOPIC = {
    "fa": (
        "📊 <b>استت‌ها</b>\n"
        "━━━━━━━━━━━━━━\n"
        "هر کاراکتر پنج استت دارد. هر استت یک عدد پایه از نژادت می‌گیرد و بعد با امتیازهایی که با بالا رفتن لول می‌گیری زیاد می‌شود.\n\n"
        "⚔️ <b>زنجوتسو</b> — قدرت ضربه‌ی تیغه.\n"
        "تنها استتِ حمله‌ی معمولی است، نصف ضربه‌ی سنگین را می‌سازد، ۳۰٪ قدرت ابیلیتی‌ها از آن است و ضربه‌ی کاری را سنگین‌تر می‌کند.\n\n"
        "🔮 <b>کیدو</b> — قدرت جادوهای کیدو.\n"
        "آسیب هادو و قدرت باکودو را بالا می‌برد. برای <b>شینیگامی</b> ۷۰٪ قدرت همه‌ی ابیلیتی‌ها (شونپو، گتسوگا، تکنیک زانپاکتو، ضربه‌ی بانکای) از کیدو است.\n\n"
        "🛡️ <b>هاکودا</b> — بدنه و دفاع.\n"
        "جون بیشینه را بالا می‌برد (هر امتیاز ۱۰ جون، ×۶ از آپدیت جدید) و آسیب دریافتی را کم می‌کند. برای <b>هالو</b> ۷۰٪ قدرت ابیلیتی‌ها، سپرها و درمان‌ها از هاکوداست.\n\n"
        "💨 <b>هوهو</b> — سرعت و چابکی.\n"
        "جاخالی را به نسبت سرعت دو طرف بالا می‌برد (۵٪ + ۲۵٪ × (هوهوی مدافع ÷ هوهوی مهاجم − ۱)، تا ۶۰٪)، کمی ضربه‌ی کاری، نوبت اول و حرکت ارزان‌تر (هر ۱۰۰ هوهو ۱۰٪، تا ۵۰٪). برای <b>آرانکار</b> ۷۰٪ قدرت ابیلیتی‌ها و تقویت‌ها از هوهوست.\n\n"
        "✨ <b>ریاتسو</b> — منبع انرژی معنوی.\n"
        "ریاتسوی بیشینه را بالا می‌برد (هر امتیاز ۱۵ واحد) و نصف ضربه‌ی سنگین را می‌سازد. برای <b>کوئینسی، ویزورد و انسان</b> ۷۰٪ قدرت ابیلیتی‌ها، سپرها و درمان‌ها از ریاتسوست.\n\n"
        "🗡 <b>فول‌برینگر</b> استت ابیلیتی ندارد: در ابیلیتی‌هایش قدرت سلاح دو برابر حساب می‌شود.\n\n"
        "<b>امتیاز می‌گیری از کجا؟</b>\n"
        "هر لول سه امتیاز می‌دهد و در لول‌های مضرب ۵ یک امتیاز اضافه. امتیازها را با دکمه‌ی ➕ زیر هر استت خرج می‌کنی.\n\n"
        "<b>سقف نرم (افت بازده)</b>\n"
        "تا ۱۵۰ امتیاز هر امتیاز کامل حساب می‌شود. از ۱۵۰ تا ۳۰۰ فقط ۸۵٪، از ۳۰۰ تا ۶۰۰ فقط ۶۰٪، و بالاتر از ۶۰۰ فقط ۴۰٪. "
        "یعنی زیاد کردن یک استت خیلی بالا صرفه‌ی کمتری دارد؛ بهتره بین استت‌ها پخش کنی.\n\n"
        "<b>نکته:</b> هر نژاد عدد پایه‌ی خودش را دارد؛ امتیاز را بیشتر روی استت ابیلیتی نژادت بگذار، ولی زنجوتسو را برای حمله‌ی معمولی فراموش نکن."
    ),
    "en": (
        "📊 <b>Stats</b>\n"
        "━━━━━━━━━━━━━━\n"
        "Every character has five stats. Each starts from your race's base value and grows with the points you earn by levelling up.\n\n"
        "⚔️ <b>Zanjutsu</b> — blade power.\n"
        "The only stat of a plain attack, half of a heavy strike, 30% of every ability, and it makes critical hits hit harder.\n\n"
        "🔮 <b>Kidō</b> — spell power.\n"
        "Raises Hadō damage and Bakudō strength. For a <b>Shinigami</b>, 70% of every ability (Shunpo, Getsuga, Zanpakutō technique, Bankai strike) comes from Kidō.\n\n"
        "🛡️ <b>Hakuda</b> — body and defence.\n"
        "Raises max HP (10 per point, then x6 since the long-fight update) and cuts the damage you take. For a <b>Hollow</b>, 70% of abilities, shields and heals comes from Hakuda.\n\n"
        "💨 <b>Hoho</b> — speed and agility.\n"
        "Raises dodge by the ratio of the two speeds (5% + 25% x (defender Hohō / attacker Hohō - 1), up to 60%), a little crit, the first turn, and cheaper movement (10% per 100 Hohō, up to 50%). For an <b>Arrancar</b>, 70% of abilities and buffs comes from Hoho.\n\n"
        "✨ <b>Reiatsu</b> — spiritual energy.\n"
        "Raises max reiatsu (15 per point) and makes half of a heavy strike. For a <b>Quincy, Visored or Human</b>, 70% of abilities, shields and heals comes from Reiatsu.\n\n"
        "🗡 A <b>Fullbringer</b> has no ability stat: the weapon's attack counts double in their abilities.\n\n"
        "<b>Where do points come from?</b>\n"
        "Each level gives 3 points, and every 5th level gives 1 extra. Spend them with the ➕ buttons under each stat.\n\n"
        "<b>Soft cap (diminishing returns)</b>\n"
        "The first 150 points count fully. From 150 to 300 they count 85%, from 300 to 600 they count 60%, and above 600 they count 40%. "
        "Pushing one stat very high pays less, so spread your points.\n\n"
        "<b>Note:</b> every race has its own base values; put most points into your race's ability stat, but keep some Zanjutsu for plain attacks."
    ),
}


# ---- guides for every system (handlers_panels.help_panel lists them; numbers come from the code) ----------------------
def _t(fa, en):
    return {"fa": fa, "en": en}


TOPICS = {
    "fam": ("⚔️ توانایی‌ها، نوع‌ها و نبرد طولانی", "⚔️ Ability types and long fights", _t(
        "⚔️ <b>پنل توانایی‌ها</b>\n━━━━━━━━━━━━━━\n"
        "هر دکمه‌ی ویژه‌ی نژادت یک <b>خانواده</b> است با نوع‌های مختلف؛ مثلاً ۲۰ نوع سرو، یا شونپو / اوتسوسمی / سنکا / شونکو. "
        "نوع‌ها رتبه ندارند: رنگ کارت فقط کمیابی است، هر نوع کار خودش را می‌کند.\n"
        "• هر نوع با <b>کارتش</b> باز می‌شود. کارت‌ها فقط مال نژاد خودت دراپ می‌شوند (دراپ، شاپ رول، فروشگاه، جایزه‌ها)؛ کارت نژاد دیگر را فقط می‌توانی بفروشی.\n"
        "• قبل از نبرد در پنل انتخاب کن هر دکمه کدام نوع را بزند؛ وسط نبرد قفل است. آرانکار دو خانه‌ی سرو دارد.\n"
        "• <b>لِوِل خانواده</b> (۱ تا ۱۰) بین همه‌ی نوع‌هایش مشترک است: هر لِوِل ضریب‌ها +۶٪، شانس‌ها +۱، مدت +۱ نوبت در لِوِل ۵ و ۱۰، کول‌داون −۱ در لِوِل ۸ و هزینه −۲٪.\n"
        "• ارتقا = کارت تکراری + سکه (از ۱ تا ۱۰ جمعاً ۲۵ کارت و ۱۷۲ هزار سکه). توانایی‌های ثابت (بالا، بلوت، رهاسازی...) هم لِوِل دارند.\n"
        "• هادو و باکودو: طلسم هر دکمه را خودت انتخاب می‌کنی؛ کارت کیدوی تکراری «تسلط هادو/باکودو» را بالا می‌برد.\n"
        "• هر توانایی استت خودش را دارد و پنل آن را با مقدار استت تو نشان می‌دهد (مثلاً سرو = ریاتسو، هیرو = هاکودا، شونپو = ۷۰٪ هوهو + ۳۰٪ زنجوتسو).\n\n"
        "🔐 <b>حالت‌ها:</b> بعضی نوع‌ها فقط وقتی دیده می‌شوند که حالتی فعال باشد: گتسوگا بعد از <b>شیکای</b> (دکمه‌ی جدا از لِوِل ۱۰، یک نوبت و ۱۵٪ ریاتسو، تا آخر نبرد)، "
        "گتسوگای سیاه و موگتسو با بانکای، سرو و ماسک ویزورد با <b>ماسک هالو</b>، ضربه‌ی آهنین و بالای بی‌کول‌داون با هیرو، لانسا با رسورکسیون، اشپرنگر و هایزن با بلوت آرتری...\n\n"
        "⏳ <b>نبرد طولانی:</b> جان همه ۶ برابر شد و اکس‌پی فارم هم ۶ برابر. بازسازی‌ها و درمان‌های تکراری با جان قدیمی حساب می‌شوند تا نبرد گیر نکند. سقف نبرد ۲۰۰ نوبت.\n"
        "↔️ <b>حالت جانبی:</b> رایگان (نوبت نمی‌گیرد)، هر نوبت یک بار، ۳٪ ریاتسو: هوهو ×۲ و آسیب خودت ×۰٫۵.\n"
        "🌍 <b>دنیاها:</b> همه باز هستند و هر کدام سطح دشمن خودش را دارد (🟢 آسان، 🟡 چالش، 🔴 خطرناک). دشمن قوی‌تر جایزه‌ی بیشتر (تا +۶۰٪)، دشمن خیلی ضعیف‌تر کمتر.\n"
        "🎯 <b>چالش هر نبرد:</b> هر نبرد معمولی یک چالش تصادفی دارد؛ انجامش بدهی +۲۵٪ اکس‌پی و سکه و شانس کارت توانایی.",
        "⚔️ <b>The ability panel</b>\n━━━━━━━━━━━━━━\n"
        "Every special button of your race is a <b>family</b> with many types: 20 Ceros, or Shunpo / Utsusemi / Senka / Shunkō. Types are not ranked: "
        "a card's colour is only rarity, each type has its own job.\n"
        "• A type opens with its <b>card</b>. Only your race's cards drop for you; another race's card can only be sold.\n"
        "• Before a fight, pick the type of each button in the panel; it is locked during the fight. Arrancar have two Cero slots.\n"
        "• The <b>family level</b> (1-10) is shared by all its types: +6% multipliers, +1 chance, +1 turn at levels 5 and 10, cooldown -1 at level 8, cost -2% a level.\n"
        "• Levelling = duplicate cards + coins (25 cards and 172k coins from 1 to 10). Fixed abilities (Bala, Blut, release...) have levels too.\n"
        "• Hadō and Bakudō: you pick each button's spell; duplicate Kidō cards raise Hadō/Bakudō mastery.\n"
        "• Every ability has its own stat, shown in the panel with your value (Cero = Reiatsu, Hierro = Hakuda, Shunpo = 70% Hohō + 30% Zanjutsu).\n\n"
        "🔐 <b>States:</b> some types show only while a state holds: Getsuga after <b>Shikai</b> (its own button from level 10, one turn and 15% reiatsu, for the whole fight), "
        "Black Getsuga and Mugetsu with Bankai, the Visored Cero and Mask with the <b>Hollow Mask</b>, Iron Fist and cooldown-free Bala with Hierro, Lanza with Resurrección...\n\n"
        "⏳ <b>Long fights:</b> everyone's HP is x6 and farm XP is x6. Repeating heals and regen count on the old HP so fights do not stall. Turn cap 200.\n"
        "↔️ <b>Side stance:</b> free (no turn), once a turn, 3% reiatsu: Hohō x2, your damage x0.5.\n"
        "🌍 <b>Worlds:</b> all open, each with its own enemy levels (🟢 easy, 🟡 a challenge, 🔴 dangerous). Stronger foes pay more (up to +60%), far weaker ones less.\n"
        "🎯 <b>Fight challenge:</b> every normal fight has a random challenge; meet it for +25% XP and coins and a chance of an ability card.")),
    "abil": ("💥 دمیج و ابیلیتی‌ها", "💥 Damage and abilities", _t(
        "💥 <b>دمیج از کجا میاد؟</b>\n━━━━━━━━━━━━━━\n"
        "<b>۱. پایه‌ی ضربه</b>\n"
        "• <b>حمله‌ی معمولی:</b> فقط زنجوتسو + قدرت سلاح\n"
        "• <b>ضربه‌ی سنگین (×۱٫۶):</b> نصف زنجوتسو + نصف ریاتسو + قدرت سلاح\n"
        "• <b>ابیلیتی‌ها:</b> استت خانواده‌ی خودشان (در پنل ⚔️ توانایی‌ها نوشته شده) + قدرت سلاح\n"
        "  شینیگامی کیدو · کوئینسی، ویزورد و انسان ریاتسو · آرانکار هوهو · هالو هاکودا · فول‌برینگر قدرت سلاح دو برابر\n"
        "ابیلیتی یعنی: حرکت ویژه‌ی نژاد (سرو، هیرنکیاکو، شونپو، ضربه‌ی براینگر، ضربه‌ی روح)، تکنیک‌های نژادی، گتسوگا، تکنیک زانپاکتو، بالا و ضربه‌ی شروع رهاسازی.\n"
        "سپرها، درمان‌ها و تقویت‌های نژاد هم با همان استت قوی‌تر می‌شوند.\n\n"
        "<b>۲. سلاح:</b> هر سطح فورج ۶٪ به قدرت سلاح اضافه می‌کند و پیوند، بخش زنجوتسو را تا دو برابر قوی می‌کند. قدرت بالای ۹۰ فقط ۶۰٪ حساب می‌شود.\n"
        "<b>۳. دفاع دشمن:</b> ۶۰٪ دفاعش (نصف هاکودا + زره) کم می‌شود؛ «نفوذ» بخشی از آن را نادیده می‌گیرد.\n"
        "<b>۴. ضریب حرکت:</b> معمولی ۱ · سنگین ۱٫۶ · شروع رهاسازی ۲ · گتسوگا ۲٫۴ · تکنیک‌ها ضریب خودشان.\n"
        "<b>۵. ضربه‌ی کاری:</b> شانس ۵٪ + هوهو + کریت سلاح؛ حدود ۱٫۵ برابر.\n"
        "<b>۶. ضریب‌ها:</b> عنصر (برتر ۱٫۵، ضعیف ۰٫۷۵)، نژاد، تکامل، زره، و ۶۰٪ بیشتر در رهاسازی.\n\n"
        "کیدو جداست: با استت کیدو و لِوِل حساب می‌شود و قدرت سلاح در آن نیست.",
        "💥 <b>Where damage comes from</b>\n━━━━━━━━━━━━━━\n"
        "<b>1. The base of a blow</b>\n"
        "• <b>Plain attack:</b> Zanjutsu only + weapon attack\n"
        "• <b>Heavy strike (×1.6):</b> half Zanjutsu + half Reiatsu + weapon attack\n"
        "• <b>Abilities:</b> their family's own stats (shown in the ⚔️ Abilities panel) + weapon power\n"
        "  Shinigami Kidō · Quincy, Visored and Human Reiatsu · Arrancar Hohō · Hollow Hakuda · Fullbringer weapon attack counted twice\n"
        "Abilities are: the race move (Cero, Hirenkyaku, Shunpo, Bringer strike, Soul Strike), race techniques, Getsuga, the Zanpakutō technique, Bala and the release strike.\n"
        "Race shields, heals and buffs grow with the same stat.\n\n"
        "<b>2. Weapon:</b> each forge level adds 6% to its attack; the bond makes the Zanjutsu part up to twice as strong. Attack above 90 counts 60%.\n"
        "<b>3. Enemy defence:</b> 60% of it (half Hakuda + armour) is subtracted; pierce ignores part of it.\n"
        "<b>4. Move power:</b> plain 1 · heavy 1.6 · release strike 2 · Getsuga 2.4 · techniques their own.\n"
        "<b>5. Critical:</b> 5% + Hohō + weapon crit; about ×1.5.\n"
        "<b>6. Multipliers:</b> element (strong 1.5, weak 0.75), race, evolution, armour, and +60% while released.\n\n"
        "Kidō is separate: it uses the Kidō stat and level, not the weapon.")),
    "rel": ("👑 رهاسازی", "👑 Release", _t(
        "👑 <b>رهاسازی</b>\n━━━━━━━━━━━━━━\n"
        "نوار روحیه با زدن و خوردن ضربه پر می‌شود. فرم‌ها دیگر از اول نبرد آزاد نیستند (برای همه‌ی نژادها، آرانکار هم): "
        "فقط وقتی روحیه به ۱۰۰ رسید دکمه‌ی 👑 رهاسازی می‌آید و همان یک دکمه هم ضربه می‌زند هم فرم را باز می‌کند:\n"
        "• ضربه‌ی شروع ۲ برابر\n• ۲ نوبت با ۶۰٪ آسیب بیشتر و ۳۰٪ ضربه‌ی کاری بیشتر\n• تکامل بعضی نژادها یک نوبت اضافه می‌کند\n"
        "• از لِوِل ۱۰ فرم اول باز می‌شود (۱٫۵ برابر استت، ۶ نوبت)\n"
        "• از لِوِل ۳۰ فرم دوم (۳ برابر استت، ۵ نوبت، بعدش ۳ نوبت خستگی)\n\n"
        "شینیگامی: شیکای ← بانکای · آرانکار و هالو: رسورکسیون ← رسورکسیون کامل · کوئینسی: هایلیگ بوگن ← لتسته اشتیل · "
        "فول‌برینگر: فول‌برینگ ← فول‌برینگ تکامل‌یافته · انسان: بیداری روح ← اوج روح · ویزورد: ماسک هالو ← ماسک پیشرفته\n\n"
        "⚠️ با جان کمتر از ۳۰٪ ممکن است کنترل رهاسازی از دستت برود و نوبتت بسوزد.",
        "👑 <b>Release</b>\n━━━━━━━━━━━━━━\n"
        "The spirit gauge fills as you hit and get hit. Forms are no longer free at the start of a fight (every race, Arrancar too): "
        "only at 100 does the 👑 release button appear, and that one button both strikes and opens your form:\n"
        "• the opening strike is ×2\n• 2 turns of +60% damage and +30% crit\n• some evolutions add one more turn\n"
        "• from level 10 it opens the first form (stats ×1.5, 6 turns)\n"
        "• from level 30 the second form (stats ×3, 5 turns, then 3 turns of fatigue)\n\n"
        "Shinigami: Shikai → Bankai · Arrancar and Hollow: Resurrección → Full Resurrección · Quincy: Heilig Bogen → Letzt Stil · "
        "Fullbringer: Fullbring → Evolved Fullbring · Human: Soul Awakening → Soul Ascension · Visored: Hollow Mask → Advanced Mask\n\n"
        "⚠️ Below 30% HP the release can slip out of control and cost you the turn.")),
    "evo": ("🧬 تکامل و تکنیک‌ها", "🧬 Evolution and techniques", _t(
        "🧬 <b>تکامل</b>\n━━━━━━━━━━━━━━\n"
        "هر نژاد یک مسیر پنج‌مرحله‌ای مطابق انیمه دارد (مثلاً شینیگامی: دانشجوی آکادمی ← افسر بی‌کرسی ← افسر کرسی‌دار ← ستوان ← کاپیتان).\n"
        "• هر مرحله با برنده شدن در «آزمون تکامل» و خرج یادگار تکامل باز می‌شود؛ هر مرحله گیت لِوِل دارد (۱، ۱۵، ۳۵، ۶۰، ۹۰).\n"
        "• جایزه‌ها روی هم جمع می‌شوند: آسیب، جان، کیدو، نوبت اضافه‌ی رهاسازی، خشم کمتر ماسک، سرو قوی‌تر و…\n"
        "• لقب نژادت فقط با تکامل بالا می‌رود.\n\n"
        "✨ <b>تکنیک‌های نژادی</b>\n"
        "کوئینسی، هالو، آرانکار، فول‌برینگر، انسان و ویزورد هر کدام تکنیک‌های انیمه‌ای خودشان را دارند و <b>همه از لِوِل ۱ بازند</b>. "
        "با «کارت تکنیک نژادی» هر تکنیک تا سطح ۱۰ قوی‌تر می‌شود (هر سطح ۴٪؛ کارت‌ها به ترتیب). شینیگامی و ویزورد کارت کیدو می‌گیرند.\n"
        "مسیر نژادت را با «مسیر نژاد» ببین.",
        "🧬 <b>Evolution</b>\n━━━━━━━━━━━━━━\n"
        "Every race has one five-stage path from the anime (Shinigami: Academy Student → Unseated → Seated Officer → Lieutenant → Captain).\n"
        "• Each stage opens by winning the evolution trial and spending evolution relics; each has a level gate (1, 15, 35, 60, 90).\n"
        "• Rewards stack: damage, HP, Kidō, extra release turns, less mask rage, stronger Cero...\n"
        "• Your race title rises only through evolution.\n\n"
        "✨ <b>Race techniques</b>\n"
        "Quincy, Hollow, Arrancar, Fullbringer, Human and Visored each have their anime techniques, <b>all open from level 1</b>. "
        "Race technique cards raise each one up to level 10 (+4% each, in order). Shinigami and Visored get Kidō cards.\n"
        "See your path in «race path».")),
    "rw": ("🗡 سلاح نژاد", "🗡 Race weapon", _t(
        "🗡 <b>سلاح نژاد</b>\n━━━━━━━━━━━━━━\n"
        "تیغه دیگر دراپ نمی‌شود. هر نژاد ۱۰ سلاح خام با گرایش خودش دارد؛ یکی را انتخاب می‌کنی و با خودت بزرگش می‌کنی.\n\n"
        "🔗 <b>پیوند:</b> با هر برد بیشتر می‌شود؛ بخش زنجوتسوی ضربه را تا دو برابر می‌کند.\n"
        "🔨 <b>فورج +۱ تا +۱۰:</b> هر سطح ۶٪ قدرت.\n"
        "⬆️ <b>رنگ:</b> سفید ← سبز ← آبی ← بنفش ← طلایی ← قرمز با یادگار تکامل و سکه (قدرت پایه ۳۰ ← ۴۲ ← ۵۶ ← ۷۶ ← ۱۰۶ ← ۱۶۰؛ گیت لِوِل ۱، ۵، ۱۵، ۳۰، ۵۰، ۸۰).\n"
        "🔄 <b>مهر بازآفرینی سلاح:</b> نوع سلاح را بین ۱۰ سلاح نژادت عوض می‌کند و رنگ، فورج و پیوند را نگه می‌دارد.\n\n"
        "یادگار تکامل شانسی از صندوق‌های شاپ دانجن می‌آید. سلاح نژادی ترید نمی‌شود و همیشه دستت می‌ماند. پنل: «سلاح».",
        "🗡 <b>Race weapon</b>\n━━━━━━━━━━━━━━\n"
        "Blades no longer drop. Every race has 10 raw weapons with their own leaning; you pick one and grow it.\n\n"
        "🔗 <b>Bond:</b> grows with every win; makes the Zanjutsu part of a blow up to twice as strong.\n"
        "🔨 <b>Forge +1 to +10:</b> +6% attack per level.\n"
        "⬆️ <b>Colour:</b> white → green → blue → purple → gold → red with evolution relics and coins (base attack 30 → 42 → 56 → 76 → 106 → 160; level gates 1, 5, 15, 30, 50, 80).\n"
        "🔄 <b>Weapon Rebirth Seal:</b> switches to another of your race's 10 weapons, keeping colour, forge and bond.\n\n"
        "Evolution relics come by luck from dungeon-shop chests. A race weapon cannot be traded and always stays in hand. Panel: «weapon».")),
    "ra": ("🛡 زره نژاد", "🛡 Race armour", _t(
        "🛡 <b>زره نژاد</b>\n━━━━━━━━━━━━━━\n"
        "هر نژاد ۵ لباس مخصوص دارد و هر لباس در ۴ ساخت می‌آید (آهنین، روحی، جنگی، چابک): ۲۰ نوع زره.\n"
        "• هر زره دفاع دارد + دو ویژگی (یکی از لباس، یکی از ساخت)؛ ویژگی‌ها در رنگ قرمز ۴ برابر سفیدند.\n"
        "• زره انتخابی نیست؛ فقط شانسی می‌آید: دراپ نبرد، چرخونه‌ی «زره»، صندوق شاپ دانجن و جایزه‌ی رنک نبرد.\n"
        "• فقط نژاد خودت می‌تواند بپوشد؛ در ترید و بازار هم فقط به همان نژاد می‌رسد.\n"
        "گردنبند و انگشتر بین همه‌ی نژادها مشترک‌اند.",
        "🛡 <b>Race armour</b>\n━━━━━━━━━━━━━━\n"
        "Every race has 5 garments, each in 4 make-ups (Iron, Spirit, War, Swift): 20 kinds of armour.\n"
        "• Each has defence plus two perks (one from the garment, one from the make-up); at red the perks are 4× white.\n"
        "• Armour is never chosen, only won: battle drops, the armour wheel, dungeon-shop chests and Battle Rank rewards.\n"
        "• Only your own race can wear it; in trades and the market it only goes to that race.\n"
        "Necklaces and rings are shared by every race.")),
    "brk": ("🎖 رنک نبرد", "🎖 Battle Rank", _t(
        "🎖 <b>رنک نبرد</b> (فصلی)\n━━━━━━━━━━━━━━\n"
        "از نبرد عادی و دوئل رنکی (نه دانجن، برج یا آزمون). لِوِل، قدرت، دنیا و نژاد هیچ اثری ندارند؛ همه با یک قانون بالا می‌روند. "
        "۱۸ زیررتبه: میناری، شودن، چودن، اوکودن، کایدن، منکیو کایدن (هر کدام ۱ تا ۳). هر زیررتبه چند روز طول می‌کشد و بالای نردبان برای کل فصل است.\n\n"
        "• <b>برد در نبرد عادی:</b> +۲۰ (دشمن الیت +۲۵)، برای همه یکسان؛ سقف روزانه ۶۰۰.\n"
        "• <b>دوئل رنکی:</b> برد مقابل رتبه‌ی بالاتر بیشتر می‌دهد (از ۱۵ تا ۸۰)، بازنده حدود ۸۰٪ همان را از دست می‌دهد. "
        "با یک حریف فقط ۳ دوئل اول هر روز حساب است؛ سقف روزانه‌ی دوئل ۵۰۰. دوئل دوستانه رنک ندارد.\n"
        "• <b>باخت در نبرد عادی:</b> زنجیره نصف می‌شود؛ از ۱۰ تا حدود ۳۵ امتیاز رنک کم می‌کند، هرچه بالاتر بیشتر.\n"
        "• <b>فرار:</b> دست‌کم ۴۰ و همیشه بیشتر از باخت، ولی زنجیره نمی‌شکند.\n"
        "• <b>جایزه:</b> هر زیررتبه یک‌بار در فصل، به رنگ همان رتبه: ۱ صندوق مصرفی، ۲ صندوق زره، ۳ صندوق مواد سلاح.\n"
        "• <b>فصل:</b> ۳۰ روز؛ اول فصل بعد ۴۰٪ امتیاز می‌ماند.\n"
        "• <b>کنپاچی:</b> نفر اول فصل؛ آخر فصل «چشم‌بند کنپاچی» را برای همیشه می‌گیرد (۸٪ آسیب، ۴٪ دفاع، ۳٪ ضربه‌ی کاری).",
        "🎖 <b>Battle Rank</b> (seasonal)\n━━━━━━━━━━━━━━\n"
        "From normal battles and ranked duels (not dungeons, towers or trials). Level, power, world and race play no part; everyone climbs by the same rule. "
        "18 divisions: Minarai, Shoden, Chūden, Okuden, Kaiden, Menkyo Kaiden (1 to 3 each). Each one takes days; the top takes the whole season.\n\n"
        "• <b>Normal win:</b> +20 (elite foe +25), the same for everyone; daily cap 600.\n"
        "• <b>Ranked duel:</b> beating a higher rank pays more (15 to 80); the loser drops about 80% of it. "
        "Only the first 3 duels a day against the same opponent count; duel daily cap 500. Friendly duels give no rank.\n"
        "• <b>Normal loss:</b> halves the chain; costs 10 up to about 35 rank, more the higher you are.\n"
        "• <b>Flee:</b> at least 40 and always more than a loss, but keeps the chain.\n"
        "• <b>Rewards:</b> each division once per season in its tier's colour: 1 consumable chest, 2 armour chest, 3 weapon materials chest.\n"
        "• <b>Season:</b> 30 days; you keep 40% of your points into the next.\n"
        "• <b>Kenpachi:</b> the season's number one; at the end they keep Kenpachi's Eyepatch forever (+8% damage, +4% defence, +3% crit).")),
    "dg": ("🏯 دانجن و صندوق‌ها", "🏯 Dungeons and chests", _t(
        "🏯 <b>دانجن</b>\n━━━━━━━━━━━━━━\n"
        "دانجن آیتم نمی‌دهد (ورطه و افسانه‌ای با پاکسازی کامل سکه هم می‌دهند). بین هر دو طبقه ۲۵٪ جان و ریاتسو برمی‌گردد، قبل از باس ۴۰٪. هر طبقه دو برابر تجربه می‌دهد (طبقه‌ی آخر سه برابر دیگر) و پاک کردن کامل دانجن پوینت می‌دهد:\n"
        "پایه (عادی ۶، سخت ۱۲، کابوس ۲۵، ورطه ۶۰، افسانه‌ای ۱۵۰) × (۱ + سطح دانجن ÷ ۲۰)؛ سقف روزانه ۱۵۰۰.\n\n"
        "📦 <b>صندوق‌های شاپ دانجن</b> (سکه + یک آیتم فقط از رنگ‌های خودش):\n"
        "🥉 برنزی ۴۰: سفید یا سبز · ۲۰٪ شانس یادگار تکامل سفید یا سبز\n"
        "🥈 نقره‌ای ۱۲۰: آبی یا بنفش · ۳۰٪ شانس یادگار آبی یا بنفش\n"
        "🥇 طلایی ۳۶۰: طلایی یا قرمز · ۴۰٪ شانس یادگار بنفش · و یک جایزه‌ی دوم (مواد، معجون یا کتاب) · ۱۵٪ شانس سنگ آبدیده‌سازی\nمواد همیشه ۲ تا ۳ تایی می‌آیند.\n"
        "اگر چند صندوق پشت هم رنگ پایین‌تر بدهد، بعدی حتماً رنگ بالاتر است.",
        "🏯 <b>Dungeons</b>\n━━━━━━━━━━━━━━\n"
        "Dungeons pay no items (Abyss and Legendary also pay coins on a full clear). Between floors 25% HP and reiatsu come back, 40% before the boss. Each floor pays double XP (the last floor ×3 more) and a full clear pays dungeon points:\n"
        "base (normal 6, hard 12, nightmare 25, abyss 60, legendary 150) × (1 + dungeon level ÷ 20); daily cap 1500.\n\n"
        "📦 <b>Dungeon-shop chests</b> (coins + one item of their own colours only):\n"
        "🥉 Bronze 40: white or green · 20% chance of a white or green evolution relic\n"
        "🥈 Silver 120: blue or purple · 30% chance of a blue or purple relic\n"
        "🥇 Gold 360: gold or red · 40% chance of a purple relic · plus a second prize (materials, potions or a book) · 15% chance of a Tempering Stone\nMaterials always come 2-3 at a time.\n"
        "After a run of lower colours, the next chest is the higher one for sure.")),
    "boss": ("💀 باس جهانی", "💀 World boss", _t(
        "💀 <b>باس جهانی</b>\n━━━━━━━━━━━━━━\n"
        "جان باس = عدد تصادفی بین ۱۰۰ تا ۲۰۰ هزار × تعداد بازیکن‌های آنلاین همان لحظه (فعال در ۱۵ دقیقه‌ی اخیر). باس ۲۰ دقیقه وقت دارد؛ همه باید با هم بزنند.\n"
        "سه نفر اول دمیج جایزه‌ی بیشتری می‌گیرند و پنج نفر اول اگر باس بمیرد ۳۰٪ شانس یادگار تکامل دارند.",
        "💀 <b>World boss</b>\n━━━━━━━━━━━━━━\n"
        "Boss HP = a random 100k–200k × the players online at that moment (active in the last 15 minutes). It stays 20 minutes; everyone has to hit it together.\n"
        "The top three by damage get more, and if it dies the top five have a 30% chance of an evolution relic.")),
    "rc": ("🔄 تغییر نژاد", "🔄 Race change", _t(
        "🔄 <b>تغییر نژاد</b>\n━━━━━━━━━━━━━━\n"
        "• رایگان است؛ فقط هر ۵ روز یک بار.\n• همه‌ی امتیازهای استت برمی‌گردد تا برای نژاد جدید دوباره پخش کنی.\n"
        "• مرحله‌ی تکاملت حفظ می‌شود.\n• ویزورد می‌تواند به شینیگامی برگردد و بعد بدون آزمون دوباره ویزورد شود.\n"
        "• زره‌هایت به زره نژاد جدید (همان رنگ) تبدیل می‌شوند و سلاح نژاد جدید را با همان سطح سلاح قبلی انتخاب می‌کنی.",
        "🔄 <b>Race change</b>\n━━━━━━━━━━━━━━\n"
        "• Free; once every 5 days.\n• Every stat point comes back so you can spend it for the new race.\n"
        "• Your evolution stage is kept.\n• A Visored can go back to Shinigami and later become Visored again without the trial.\n"
        "• Your armour turns into the new race's (same colour) and you pick a new race weapon at the same level.")),
    "adv": ("🧭 ماجراجویی و باس‌ها", "🧭 Adventures and bosses", _t(
        "🗺 <b>تابلوی کوئست گیلد (ماجراجویی)</b>\n━━━━━━━━━━━━━━\n"
        "هر روز یک تابلوی ۵ کوئستی با سطح رندوم؛ روزی تا ۵ کوئست و هر کوئست یک بار. هر کوئست چند مرحله دارد (۲ تا ۶) و رنکش (F تا S) با فاصله‌ی سطحش از سطح تو بالا می‌رود. نوع‌ها: پاکسازی، سرکوب (باس منطقه) و آزمون سخت (باس، یک مرحله بیشتر، بدون استراحت قبل از مرحله‌ی ۳، یک آیتم اضافه). هر مرحله تجربه می‌دهد و آخرش: آیتم هم‌رنگ رنک، پیشرفت آزادسازی زانپاکتو (پیوند برای شیکای؛ مهارت برای بانکای بعد از آزاد کردن شیکای) و کمی سکه. هر منطقه از یک لِوِل باز می‌شود.\n\n"
        "👺 <b>مینی‌باس</b>: در نبرد عادی ۲٪ شانس دارد به‌جای دشمن معمولی یک مینی‌باس دو برابر قوی‌تر بیاید. بردن آن: تجربه و سکه ×۳، یک دراپ حتمی و ۱۰٪ شانس یادگار تکامل.\n\n"
        "👹 <b>باس سطح</b>: هر بازه‌ی لِوِل (۱–۲۰، ۲۱–۴۰، ۴۱–۶۰، ۶۱–۸۰، ۸۱–۱۰۰، ۱۰۱+) باس خودش را دارد و فقط همان بازه می‌تواند با آن بجنگد؛ روزی یک بار. جایزه: تجربه و سکه ×۴، یک آیتم هم‌رنگ بازه، ۲۵٪ یادگار تکامل، ۲۰٪ سنگ آبدیده‌سازی، ۲٪ کلید دنیای درون.",
        "🗺 <b>Guild Quest Board (adventures)</b>\n━━━━━━━━━━━━━━\n"
        "Every day a board of 5 random-level quests; up to 5 a day, each quest once. A quest has 2 to 6 stages and its rank (F to S) rises with how far its level is above yours. Types: Purge, Subjugation (the region's boss) and Gauntlet (a boss, one more stage, no breather before stage 3, one extra item). Every stage pays XP; the finish pays an item of the rank's colour, Zanpakutō release progress (bond toward Shikai; Mastery toward Bankai once Shikai is released) and a few coins. Each region opens at a level.\n\n"
        "👺 <b>Mini-boss</b>: a normal fight has a 2% chance of a mini-boss twice as strong instead. Beating it: XP and coins ×3, a guaranteed drop and a 10% chance of an evolution relic.\n\n"
        "👹 <b>Level boss</b>: each level band (1–20, 21–40, 41–60, 61–80, 81–100, 101+) has its own boss that only that band can fight, once a day. Reward: XP and coins ×4, an item of the band's colour, 25% evolution relic, 20% Tempering Stone, 2% Inner World Key.")),
    "shp": ("🎰 شاپ رول و نخبگان", "🎰 Roll and elite shops", _t(
        "🎰 <b>شاپ رول</b>\n━━━━━━━━━━━━━━\n"
        "هر رول ۳٬۰۰۰ سکه (ده تا ۲۷٬۰۰۰). جایزه: کارت کیدو (باکودو و هادو برای شینیگامی و ویزورد) یا کارت تکنیک نژادت، یا تخم روح؛ فقط آبی به بالا: آبی ۶۰٪، بنفش ۳۰٪، طلایی ۹٪، قرمز ۱٪. هر ۱۰۰ رول یک جک‌پات حتمی: اکسسوری قرمز + سنگ آبدیده‌سازی.\n\n"
        "🏛 <b>شاپ نخبگان</b>: از لِوِل ۵۰ (و از ۱۰۰ موجودی بیشتر و بدون سقف لِوِل). آیتم‌های بنفش و طلایی و سنگ آبدیده‌سازی؛ قفسه هر روز عوض می‌شود و از هر کدام روزی ۳ تا.\n\n"
        "🎴 <b>جک‌پات احضار</b>: هر احضار ۱ در ۱۰٬۰۰۰ شانس دارد: ۵۰۰٬۰۰۰ سکه + اکسسوری قرمز + کلید دنیای درون.\n\n"
        "🎡 گردونه‌ی یاماموتو حالا گران‌ترین گردونه است (۷۵)، بعد ایچیگو (۶۰).",
        "🎰 <b>Roll shop</b>\n━━━━━━━━━━━━━━\n"
        "Each roll costs 3,000 coins (ten for 27,000). Prize: a Kidō card (Bakudō and Hadō for Shinigami and Visored) or your race's technique card, or a spirit egg; blue and up only: blue 60%, purple 30%, gold 9%, red 1%. Every 100 rolls is a guaranteed jackpot: a red accessory + a Tempering Stone.\n\n"
        "🏛 <b>Elite shop</b>: from level 50 (bigger stock and no level cap from 100). Purple and gold items and the Tempering Stone; the shelf changes daily, up to 3 of each.\n\n"
        "🎴 <b>Summon jackpot</b>: each summon has a 1 in 10,000 chance: 500,000 coins + a red accessory + an Inner World Key.\n\n"
        "🎡 Yamamoto's wheel is now the most expensive (75), then Ichigo (60).")),
    "acc": ("💍 اکسسوری، سنگ و دنیای درون ۲", "💍 Accessories, stones and Inner World 2", _t(
        "💍 <b>اکسسوری‌ها</b>\n━━━━━━━━━━━━━━\n"
        "۵۰۰ اکسسوری تازه از دنیای بلیچ (نشان ستوان‌ها و کاپیتان‌ها، اسپادا، اشتیرن‌ریتر، کوئینسی، زیرو دیویژن، فول‌برینگ و…). هر اسم فقط یک بار و فقط یک رنگ دارد؛ دیگر «مرحله‌ی ۱ و ۲» نیست. انگشترها در جای انگشتر و گردنبندها در جای طلسم. رنگ بالاتر = استت اصلی بیشتر و از آبی به بالا یک استت دوم یا شانس. قرمزها (۲۰ تا) فقط از جک‌پات‌ها، شاپ رول، باس سطح و احضار قرمز می‌آیند و قابل معامله نیستند.\n"
        "اکسسوری‌های قدیمی خودکار به یک اکسسوری جدید هم‌رنگ و هم‌جا تبدیل شدند.\n\n"
        "🪨 <b>سنگ آبدیده‌سازی</b>: برای آهنگری سلاح و آبدیده کردن زره از +۶ به بعد لازم است (+۶ یک سنگ، +۷ دو سنگ، … +۱۰ پنج سنگ). سقف هر دو حالا +۱۰ است. منبع: صندوق طلایی (۱۵٪)، باس سطح (۲۰٪)، شاپ نخبگان، جک‌پات شاپ رول و هر ۵۰ طبقه‌ی برج.\n\n"
        "🌌 <b>دنیای درون ۲</b>: با «کلید دنیای درون» (خیلی کمیاب) هر بار یک بونوس دائمی خالص بگیر: هالو +۰.۵٪ آسیب (سقف ۵٪)، ذن +۰.۵٪ دفاع (سقف ۵٪)، نفس +۰.۰۸٪ بازسازی جان در هر نوبت (سقف ۰.۸٪)، آینه +۱٪ تجربه (سقف ۱۰٪).\n\n"
        "🐾 <b>همراه‌ها</b>: ۱۰ روح همراه جدید و ارتقا تا ★۱۰ با سکه و مواد روحی.",
        "💍 <b>Accessories</b>\n━━━━━━━━━━━━━━\n"
        "500 new accessories from the Bleach world (lieutenant and captain badges, Espada, Sternritter, Quincy, Zero Division, Fullbring…). Every name exists once with one colour; no more \"stage 1 and 2\". Rings go in the ring slot and necklaces in the charm slot. A higher colour = a bigger main stat, and from blue up a second stat or luck. The 20 red ones only come from jackpots, the roll shop, level bosses and red summons, and cannot be traded.\n"
        "Old accessories were turned into a new one of the same colour and slot automatically.\n\n"
        "🪨 <b>Tempering Stone</b>: needed for weapon forging and armour tempering from +6 (+6 one stone, +7 two, … +10 five). Both now go to +10. Sources: gold chest (15%), level boss (20%), elite shop, roll-shop jackpot and every 50th tower floor.\n\n"
        "🌌 <b>Inner World 2</b>: each Inner World Key (very rare) gives a small permanent pure bonus: Hollow +0.5% damage (cap 5%), Zen +0.5% defence (cap 5%), Breath +0.08% HP regen per turn (cap 0.8%), Mirror +1% XP (cap 10%).\n\n"
        "🐾 <b>Companions</b>: 10 new spirit companions and upgrades up to ★10 with coins and spirit materials.")),
    "war": ("⚔️ میدان جنگ رویدادها", "⚔️ Event battlefield", _t(
        "⚔️ <b>میدان جنگ</b>\n━━━━━━━━━━━━━━\n"
        "هر رویداد جهانی یک جنگ بین دو جناح از داستان بلیچ است؛ مثلاً در جنگ زمستانی ارتش آیزن (هالو و آرانکار) در برابر گوتی ۱۳ (شینیگامی و ویزورد)، در وندن‌رایش کوئینسی‌ها در برابر گوتی، در گارگانتا هالوها در برابر همه، و در جشنواره تیم سرخ در برابر تیم سفید.\n"
        "• نژادی که داستان جایش را مشخص کرده خودکار به جناحش می‌رود؛ بقیه یک بار طرف انتخاب می‌کنند و تا پایان جنگ عوض نمی‌شود.\n"
        "• 🗡 سرباز دشمن (+۱، گاهی افسر +۲)، 🪞 جنگجوی واقعی دشمن (+۳): کپی هوش مصنوعی یک بازیکن واقعی جناح مقابل، هم‌سطح تو و با تجهیزات خودش. 👑 فرمانده‌ی دشمن بعد از ۵ برد، یک بار در هر جنگ (+۱۰ و جایزه).\n"
        "• ⚖️ برنده با امتیاز «متعادل‌شده» تعیین می‌شود: امتیاز هر طرف بر اساس تعداد جنگجوهای فعالش وزن می‌گیرد، پس جناح پرجمعیت‌تر فقط به خاطر تعداد نمی‌برد.\n"
        "• 🔥 خشم جناح: طرفی که خیلی عقب است ۲۵٪ امتیاز بیشتر برای هر برد می‌گیرد.\n"
        "• 🪞 سایه‌ی تو وقتی آفلاینی هم می‌جنگد: اگر کسی به آن ببازد، یک امتیاز برای جناح تو (تا ۱۵ در هر جنگ).\n"
        "• ضد فارم: هر جنگ حداکثر ۴۰ نبرد؛ بردن دوباره از همان جنگجو نصف امتیاز و بار سوم هیچ؛ حساب‌های خیلی تازه نمی‌توانند شرکت کنند.\n"
        "• امتیاز میدان جنگ به پیشرفت خود رویداد هم اضافه می‌شود.\n"
        "• 🎁 پایان جنگ: هر کس حداقل ۲ امتیاز دارد سکه و تجربه می‌گیرد؛ سهمت با امتیازت بزرگ می‌شود و از ۱۰ امتیاز کامل است (برنده‌ها کامل، بازنده‌ها ۴۵٪، در جشنواره ۷۰٪). سه نفر اول برنده سنگ آبدیده‌سازی، نفر اول بازنده یک سنگ (هر دو با حداقل ۱۰ امتیاز)، برنده‌های ۱۰+ امتیاز ۲۵٪ شانس آیتم بنفش به بالا، و برنده‌های ۵+ امتیاز ۲۴ ساعت +۵٪ تجربه.",
        "⚔️ <b>Battlefield</b>\n━━━━━━━━━━━━━━\n"
        "Every world event is a war between two factions of the Bleach story: in the Winter War, Aizen's Army (Hollows and Arrancar) against the Gotei 13 (Shinigami and Visored); in the Wandenreich war, the Quincy against the Gotei; in the Garganta, the Hollows against everyone; at the festival, the Red Team against the White Team.\n"
        "• Races the story places join their faction automatically; the others pick a side once, locked until the war ends.\n"
        "• 🗡 Enemy soldier (+1, sometimes an officer +2), 🪞 real enemy fighter (+3): an AI copy of a real player of the other side, near your level, with their own gear. 👑 The enemy general after 5 wins, once per war (+10 and a reward).\n"
        "• ⚖️ The winner is decided by balanced points: each side's points are weighed by its number of active fighters, so the bigger side does not win just by being bigger.\n"
        "• 🔥 Rally: a side far behind scores 25% more per win.\n"
        "• 🪞 Your shadow fights while you are offline: when someone loses to it, your side gets a point (up to 15 per war).\n"
        "• Anti-farming: 40 fights per war; beating the same fighter again pays half, a third time nothing; brand-new accounts cannot join.\n"
        "• Battlefield points also push the event itself forward.\n"
        "• 🎁 War end: everyone with 2+ points gets coins and XP; your share grows with your points and is full from 10 (winners in full, losers 45%, 70% at the festival). The winners' top three get Tempering Stones, the losers' best gets one (both need 10+ points), winners with 10+ points have a 25% chance of a purple-or-better item, and winners with 5+ points get +5% XP for 24 hours.")),
    "mnt": ("🎓 ترید و استاد و شاگرد", "🎓 Trade & master / apprentice", _t(
        "🤝 <b>ترید دو نفره</b>\n━━━━━━━━━━━━━━\n"
        "• منو ← اجتماعی ← «ترید»، یا بنویس «ترید».\n"
        "• «ترید دو نفره»: اسم یا شناسه‌ی پلیر رو بفرست (یا از لیست همین مکان انتخاب کن). بهش دعوت میره و وقتی قبول کرد میز باز میشه؛ تا قبل از قبول، هیچ‌کدوم قفل نمی‌شید و دعوت بعد از ۳ دقیقه خودش می‌میره.\n"
        "• توی گروه: روی پیام پلیر ریپلای کن و بنویس «ترید».\n"
        "• هر کدوم آیتم و سکه می‌ذاری (سکه‌ی دلخواه هم می‌تونی تایپ کنی)؛ هر تغییری تأییدها رو پاک می‌کنه و وقتی هر دو تأیید کنید جابه‌جا میشه. حداقل لول ۱۰.\n\n"
        "🎓 <b>استاد و شاگرد</b>\n━━━━━━━━━━━━━━\n"
        "• منو ← اجتماعی ← «استاد و شاگرد»، یا بنویس «استاد».\n"
        "• شاگرد: از یه پلیر قوی‌تر (لول ۲۰+ و حداقل ۱۰ لول بالاتر از تو) درخواست بده؛ درخواست میره توی پنل استاد.\n"
        "• استاد: درخواست‌ها رو قبول یا رد می‌کنه؛ حداکثر ۳ شاگرد.\n"
        "• از هر نبرد و دانجنی که شاگرد ببره، خود شاگرد ۳٪ تجربه‌ی اضافه به‌عنوان پاداش آموزش می‌گیره.\n"
        "• استاد از پنلش می‌تونه به شاگردش کتاب «رساله» و «خاطرات» هدیه بده (روزی تا ۱۰ کتاب برای هر شاگرد).\n"
        "• وقتی شاگرد به لول استاد برسه فارغ‌التحصیل میشه؛ هر دو طرف هم هر وقت خواستن می‌تونن بند رو تموم کنن.",
        "🤝 <b>One-to-one trade</b>\n━━━━━━━━━━━━━━\n"
        "• More ← Social ← “Trade”, or write “trade”.\n"
        "• “One-to-one”: send a player's name or id (or pick from the list of players here). They get an invitation and the table opens when they accept; until then neither of you is locked, and the invitation dies after 3 minutes.\n"
        "• In a group: reply to a player's message and write “trade”.\n"
        "• Each side puts up items and coins (you can type any coin amount); any change clears the confirmations, and when you both confirm the swap happens. Level 10 minimum.\n\n"
        "🎓 <b>Master & apprentice</b>\n━━━━━━━━━━━━━━\n"
        "• More ← Social ← “Master & Apprentice”, or write “mentor”.\n"
        "• Apprentice: ask a stronger player (level 20+ and at least 10 levels above you); the request lands in the master's panel.\n"
        "• Master: accepts or declines requests; at most 3 apprentices.\n"
        "• For every battle and dungeon an apprentice wins, the master earns 3% extra XP (the apprentice's own XP is not reduced).\n"
        "• From their panel a master can give apprentices “Treatise” and “Memoir” books (up to 10 books a day per apprentice).\n"
        "• When the apprentice reaches the master's level they graduate; either side can also end the bond any time.")),
}
TOPIC_ORDER = ("fam", "stats", "abil", "races", "rel", "evo", "rw", "ra", "brk", "dg", "war", "adv", "shp", "acc", "boss", "rc", "mnt")
