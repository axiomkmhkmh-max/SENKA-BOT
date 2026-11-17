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
        "جون بیشینه را بالا می‌برد (هر امتیاز ۸ جون) و آسیب دریافتی را کم می‌کند. برای <b>هالو</b> ۷۰٪ قدرت ابیلیتی‌ها، سپرها و درمان‌ها از هاکوداست.\n\n"
        "💨 <b>هوهو</b> — سرعت و چابکی.\n"
        "جاخالی، کمی ضربه‌ی کاری و ترتیب نوبت را بالا می‌برد. برای <b>آرانکار</b> ۷۰٪ قدرت ابیلیتی‌ها و تقویت‌ها از هوهوست.\n\n"
        "✨ <b>ریاتسو</b> — منبع انرژی معنوی.\n"
        "ریاتسوی بیشینه را بالا می‌برد (هر امتیاز ۱۲ واحد) و نصف ضربه‌ی سنگین را می‌سازد. برای <b>کوئینسی، ویزورد و انسان</b> ۷۰٪ قدرت ابیلیتی‌ها، سپرها و درمان‌ها از ریاتسوست.\n\n"
        "🗡 <b>فول‌برینگر</b> استت ابیلیتی ندارد: در ابیلیتی‌هایش قدرت سلاح دو برابر حساب می‌شود.\n\n"
        "<b>امتیاز می‌گیری از کجا؟</b>\n"
        "هر لول سه امتیاز می‌دهد و در لول‌های مضرب ۵ یک امتیاز اضافه. امتیازها را با دکمه‌ی ➕ زیر هر استت خرج می‌کنی.\n\n"
        "<b>سقف نرم (افت بازده)</b>\n"
        "تا ۱۰۰ امتیاز هر امتیاز کامل حساب می‌شود. از ۱۰۰ تا ۲۰۰ فقط ۸۰٪، از ۲۰۰ تا ۵۰۰ فقط ۵۰٪، و بالاتر از ۵۰۰ فقط ۳۰٪. "
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
        "Raises max HP (8 per point) and cuts the damage you take. For a <b>Hollow</b>, 70% of abilities, shields and heals comes from Hakuda.\n\n"
        "💨 <b>Hoho</b> — speed and agility.\n"
        "Raises dodge, a little crit and your place in the turn order. For an <b>Arrancar</b>, 70% of abilities and buffs comes from Hoho.\n\n"
        "✨ <b>Reiatsu</b> — spiritual energy.\n"
        "Raises max reiatsu (12 per point) and makes half of a heavy strike. For a <b>Quincy, Visored or Human</b>, 70% of abilities, shields and heals comes from Reiatsu.\n\n"
        "🗡 A <b>Fullbringer</b> has no ability stat: the weapon's attack counts double in their abilities.\n\n"
        "<b>Where do points come from?</b>\n"
        "Each level gives 3 points, and every 5th level gives 1 extra. Spend them with the ➕ buttons under each stat.\n\n"
        "<b>Soft cap (diminishing returns)</b>\n"
        "The first 100 points count fully. From 100 to 200 they count 80%, from 200 to 500 they count 50%, and above 500 they count 30%. "
        "Pushing one stat very high pays less, so spread your points.\n\n"
        "<b>Note:</b> every race has its own base values; put most points into your race's ability stat, but keep some Zanjutsu for plain attacks."
    ),
}


# ---- guides for every system (handlers_panels.help_panel lists them; numbers come from the code) ----------------------
def _t(fa, en):
    return {"fa": fa, "en": en}


TOPICS = {
    "abil": ("💥 دمیج و ابیلیتی‌ها", "💥 Damage and abilities", _t(
        "💥 <b>دمیج از کجا میاد؟</b>\n━━━━━━━━━━━━━━\n"
        "<b>۱. پایه‌ی ضربه</b>\n"
        "• <b>حمله‌ی معمولی:</b> فقط زنجوتسو + قدرت سلاح\n"
        "• <b>ضربه‌ی سنگین (×۱٫۶):</b> نصف زنجوتسو + نصف ریاتسو + قدرت سلاح\n"
        "• <b>ابیلیتی‌ها:</b> ۷۰٪ از استت نژادت + ۳۰٪ از زنجوتسو + قدرت سلاح\n"
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
        "• <b>Abilities:</b> 70% your race stat + 30% Zanjutsu + weapon attack\n"
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
        "نوار روحیه با زدن و خوردن ضربه پر می‌شود. وقتی به ۱۰۰ رسید دکمه‌ی رهاسازی می‌آید:\n"
        "• ضربه‌ی شروع ۲ برابر\n• ۲ نوبت با ۶۰٪ آسیب بیشتر و ۳۰٪ ضربه‌ی کاری بیشتر\n• تکامل بعضی نژادها یک نوبت اضافه می‌کند\n\n"
        "شینیگامی و ویزورد: بانکای · هالو و آرانکار: رسورکسیون · کوئینسی: فولشتندیگ · فول‌برینگر: فول‌برینگ کامل · انسان: بیداری کامل روح\n\n"
        "⚠️ با جان کمتر از ۳۰٪ ممکن است کنترل رهاسازی از دستت برود و نوبتت بسوزد.",
        "👑 <b>Release</b>\n━━━━━━━━━━━━━━\n"
        "The spirit gauge fills as you hit and get hit. At 100 the release button appears:\n"
        "• the opening strike is ×2\n• 2 turns of +60% damage and +30% crit\n• some evolutions add one more turn\n\n"
        "Shinigami and Visored: Bankai · Hollow and Arrancar: Resurrección · Quincy: Vollständig · Fullbringer: Complete Fullbring · Human: Full Soul Awakening\n\n"
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
        "فقط نبردهای عادی (نه دانجن، برج یا آزمون). لِوِل، دنیا و نژاد اثری ندارند. ۱۸ زیررتبه: میناری، شودن، چودن، اوکودن، کایدن، منکیو کایدن (هر کدام ۱ تا ۳).\n\n"
        "• <b>برد:</b> ۲۲٪ بازه‌ی زیررتبه؛ نوبت کمتر = رنک بیشتر (یک نوبت ۱٫۵ برابر، یازده نوبت به بالا نصف)؛ دشمن الیت ۱٫۳ برابر.\n"
        "• <b>باخت:</b> زنجیره می‌شکند؛ از ۱۰٪ تا حدود ۳۰٪ بازه، هرچه بالاتر بیشتر.\n"
        "• <b>فرار:</b> ۳۵٪ بازه کم می‌شود ولی زنجیره نمی‌شکند.\n"
        "• <b>جایزه:</b> هر زیررتبه یک‌بار در فصل، به رنگ همان رتبه: ۱ صندوق مصرفی، ۲ صندوق زره، ۳ صندوق مواد سلاح.\n"
        "• <b>فصل:</b> ۳۰ روز؛ اول فصل بعد ۴۰٪ امتیاز می‌ماند.\n"
        "• <b>کنپاچی:</b> نفر اول فصل؛ آخر فصل «چشم‌بند کنپاچی» را برای همیشه می‌گیرد (۸٪ آسیب، ۴٪ دفاع، ۳٪ ضربه‌ی کاری).",
        "🎖 <b>Battle Rank</b> (seasonal)\n━━━━━━━━━━━━━━\n"
        "Normal battles only (not dungeons, towers or trials). Level, world and race play no part. 18 divisions: Minarai, Shoden, Chūden, Okuden, Kaiden, Menkyo Kaiden (1 to 3 each).\n\n"
        "• <b>Win:</b> 22% of the division; fewer rounds = more rank (one round ×1.5, eleven or more half); elite foes ×1.3.\n"
        "• <b>Loss:</b> breaks the chain; from 10% up to about 30% of the division, more the higher you are.\n"
        "• <b>Flee:</b> costs 35% but keeps the chain.\n"
        "• <b>Rewards:</b> each division once per season in its tier's colour: 1 consumable chest, 2 armour chest, 3 weapon materials chest.\n"
        "• <b>Season:</b> 30 days; you keep 40% of your points into the next.\n"
        "• <b>Kenpachi:</b> the season's number one; at the end they keep Kenpachi's Eyepatch forever (+8% damage, +4% defence, +3% crit).")),
    "dg": ("🏯 دانجن و صندوق‌ها", "🏯 Dungeons and chests", _t(
        "🏯 <b>دانجن</b>\n━━━━━━━━━━━━━━\n"
        "دانجن سکه و آیتم نمی‌دهد. هر طبقه دو برابر تجربه می‌دهد (طبقه‌ی آخر سه برابر دیگر) و پاک کردن کامل دانجن پوینت می‌دهد:\n"
        "پایه (عادی ۶، سخت ۱۲، کابوس ۲۵، ورطه ۶۰، افسانه‌ای ۱۵۰) × (۱ + سطح دانجن ÷ ۲۰)؛ سقف روزانه ۱۵۰۰.\n\n"
        "📦 <b>صندوق‌های شاپ دانجن</b> (سکه + یک آیتم فقط از رنگ‌های خودش):\n"
        "🥉 برنزی ۴۰: سفید یا سبز · ۲۰٪ شانس یادگار تکامل سفید یا سبز\n"
        "🥈 نقره‌ای ۱۲۰: آبی یا بنفش · ۳۰٪ شانس یادگار آبی یا بنفش\n"
        "🥇 طلایی ۳۶۰: طلایی یا قرمز · ۴۰٪ شانس یادگار بنفش\n"
        "اگر چند صندوق پشت هم رنگ پایین‌تر بدهد، بعدی حتماً رنگ بالاتر است.",
        "🏯 <b>Dungeons</b>\n━━━━━━━━━━━━━━\n"
        "Dungeons pay no coins or items. Each floor pays double XP (the last floor ×3 more) and a full clear pays dungeon points:\n"
        "base (normal 6, hard 12, nightmare 25, abyss 60, legendary 150) × (1 + dungeon level ÷ 20); daily cap 1500.\n\n"
        "📦 <b>Dungeon-shop chests</b> (coins + one item of their own colours only):\n"
        "🥉 Bronze 40: white or green · 20% chance of a white or green evolution relic\n"
        "🥈 Silver 120: blue or purple · 30% chance of a blue or purple relic\n"
        "🥇 Gold 360: gold or red · 40% chance of a purple relic\n"
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
        "• رایگان است؛ فقط هر ۴۸ ساعت یک بار.\n• همه‌ی امتیازهای استت برمی‌گردد تا برای نژاد جدید دوباره پخش کنی.\n"
        "• مرحله‌ی تکاملت حفظ می‌شود.\n• ویزورد می‌تواند به شینیگامی برگردد و بعد بدون آزمون دوباره ویزورد شود.\n"
        "• زره‌هایت به زره نژاد جدید (همان رنگ) تبدیل می‌شوند و سلاح نژاد جدید را با همان سطح سلاح قبلی انتخاب می‌کنی.",
        "🔄 <b>Race change</b>\n━━━━━━━━━━━━━━\n"
        "• Free; once every 48 hours.\n• Every stat point comes back so you can spend it for the new race.\n"
        "• Your evolution stage is kept.\n• A Visored can go back to Shinigami and later become Visored again without the trial.\n"
        "• Your armour turns into the new race's (same colour) and you pick a new race weapon at the same level.")),
}
TOPIC_ORDER = ("stats", "abil", "races", "rel", "evo", "rw", "ra", "brk", "dg", "boss", "rc")
