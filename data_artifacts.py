"""Soul Artifacts: one-of-a-kind treasures. Each exists exactly once in the whole world and has a single owner at a time.
Bonus keys are the same ones `data_crafting.player_bonus` already understands (dmg, def, crit, regen, xp, drop, coin, patrol)."""

ARTIFACTS = [
    {"_id": "art_hogyoku", "icon": "🔮", "name_en": "Hōgyoku Shard", "name_fa": "پاره‌ی هوگیوکو",
     "bonus": {"dmg": 0.08, "def": 0.04},
     "lore_en": "A sliver of the orb that bends wishes. It listens to whoever holds it tightest.",
     "lore_fa": "تکه‌ای از گوی خواسته‌ها؛ به محکم‌ترین دست گوش می‌دهد."},
    {"_id": "art_soulking", "icon": "👑", "name_en": "Tear of the Soul King", "name_fa": "اشک شاه ارواح",
     "bonus": {"xp": 0.10},
     "lore_en": "One tear, older than the three worlds. Whoever carries it learns faster than time allows.",
     "lore_fa": "اشکی کهن‌تر از سه جهان؛ صاحبش سریع‌تر از زمان می‌آموزد."},
    {"_id": "art_sokyoku", "icon": "🔥", "name_en": "Sōkyoku Ember", "name_fa": "شراره‌ی سوکیوکو",
     "bonus": {"dmg": 0.10},
     "lore_en": "A spark of the execution flame. Every blow you land burns a little hotter.",
     "lore_fa": "جرقه‌ای از شعله‌ی اعدام؛ هر ضربه‌ات کمی داغ‌تر فرود می‌آید."},
    {"_id": "art_ginto", "icon": "🪞", "name_en": "Ginto Mirror", "name_fa": "آینه‌ی گینتو",
     "bonus": {"drop": 0.10, "coin": 0.03},
     "lore_en": "It shows where treasure lies before the treasure knows it is lost.",
     "lore_fa": "گنج را نشان می‌دهد پیش از آنکه گنج بداند گم شده است."},
    {"_id": "art_mask", "icon": "💀", "name_en": "Primal Hollow Mask", "name_fa": "ماسک هالوی نخستین",
     "bonus": {"crit": 0.06, "dmg": 0.04},
     "lore_en": "Its first owner has been gone for a thousand years. The mask still hungers.",
     "lore_fa": "نخستین صاحبش هزار سال است رفته؛ ماسک هنوز گرسنه است."},
    {"_id": "art_quincy", "icon": "✝️", "name_en": "Quincy Heart Seal", "name_fa": "مهر قلب کوئینسی",
     "bonus": {"def": 0.08, "regen": 0.05},
     "lore_en": "A seal of silver light. Wounds close faster beneath it.",
     "lore_fa": "مهری از نور نقره‌ای؛ زخم‌ها زیرش زودتر بسته می‌شوند."},
    {"_id": "art_garganta", "icon": "🌑", "name_en": "Moonlit Garganta Key", "name_fa": "کلید گارگانتای مهتابی",
     "bonus": {"patrol": 0.10, "drop": 0.04},
     "lore_en": "Opens a crack between worlds. Patrols find more on the other side.",
     "lore_fa": "شکافی میان جهان‌ها باز می‌کند؛ گشت‌ها آن‌سو بیشتر می‌یابند."},
    {"_id": "art_urahara", "icon": "🧳", "name_en": "Urahara's Locked Case", "name_fa": "جعبه‌ی قفل‌شده‌ی اوراهارا",
     "bonus": {"coin": 0.10},
     "lore_en": "Nobody has ever seen inside. Coins seem to find their way in anyway.",
     "lore_fa": "هیچ‌کس درونش را ندیده؛ ولی سکه‌ها راه خودشان را پیدا می‌کنند."},
    {"_id": "art_reishi", "icon": "💠", "name_en": "Heart of Reishi", "name_fa": "قلب ریشی",
     "bonus": {"regen": 0.10, "xp": 0.03},
     "lore_en": "A crystal that beats in time with the world's spirit particles.",
     "lore_fa": "بلوری که با ضربان ذرات روحی جهان می‌تپد."},
    {"_id": "art_senkai", "icon": "⛩️", "name_en": "Senkai Gate Fragment", "name_fa": "پاره‌ی دروازه‌ی سنکای",
     "bonus": {"xp": 0.06, "drop": 0.06},
     "lore_en": "A shard of the gate that links the living and the dead. Both sides pay it tribute.",
     "lore_fa": "تکه‌ای از دروازه‌ی میان زندگان و مردگان؛ هر دو سو به آن باج می‌دهند."},
    {"_id": "art_fallen", "icon": "🌘", "name_en": "Fallen Captain's Shadow", "name_fa": "سایه‌ی کاپیتان سقوط‌کرده",
     "bonus": {"crit": 0.08},
     "lore_en": "A shadow that refuses to leave its blade. It strikes where you cannot look.",
     "lore_fa": "سایه‌ای که از تیغ جدا نمی‌شود؛ جایی می‌زند که نمی‌بینی."},
    {"_id": "art_ice", "icon": "🧊", "name_en": "Sleeping Ice Dragon Seal", "name_fa": "مهر اژدهای یخی خفته",
     "bonus": {"def": 0.10, "dmg": 0.03},
     "lore_en": "The dragon sleeps. Disturb it, and the cold remembers.",
     "lore_fa": "اژدها خفته است؛ بیدارش کنی، سرما به یاد می‌آورد."},
    {"_id": "art_sekkiseki", "icon": "⛓️", "name_en": "Sekkiseki Chain", "name_fa": "زنجیر سکی‌سکی",
     "bonus": {"def": 0.08, "regen": 0.02},
     "lore_en": "A chain of the stone that swallows reiatsu. Worn lightly, it swallows the blows meant for you.",
     "lore_fa": "زنجیری از سنگی که ریاتسو را می‌بلعد؛ سبک ببندی‌اش، ضربه‌های تو را می‌بلعد."},
    {"_id": "art_seele", "icon": "✨", "name_en": "Seele Schneider", "name_fa": "سیله شنایدر",
     "bonus": {"crit": 0.06, "dmg": 0.04},
     "lore_en": "A cross of silver light that cuts what blades cannot reach.",
     "lore_fa": "صلیبی از نور نقره‌ای که آنچه تیغ نمی‌رسد را می‌برد."},
    {"_id": "art_haori", "icon": "🧥", "name_en": "Captain's Haori", "name_fa": "هائوری کاپیتان",
     "bonus": {"def": 0.05, "xp": 0.05},
     "lore_en": "White cloth with a number on the back. It weighs little and asks a lot.",
     "lore_fa": "پارچه‌ای سفید با شماره‌ای روی پشت؛ کم وزن دارد و زیاد می‌طلبد."},
    {"_id": "art_hellbutterfly", "icon": "🦋", "name_en": "Hell Butterfly", "name_fa": "پروانه‌ی دوزخ",
     "bonus": {"patrol": 0.08, "xp": 0.02},
     "lore_en": "It flutters ahead and never lands on the wrong road.",
     "lore_fa": "جلوتر پر می‌زند و هرگز روی راه اشتباه نمی‌نشیند."},
    {"_id": "art_badge", "icon": "🏅", "name_en": "Substitute Shinigami Badge", "name_fa": "نشان شینیگامی جانشین",
     "bonus": {"dmg": 0.06, "xp": 0.04},
     "lore_en": "A skull-faced badge. It does not give power; it reminds you whose it is.",
     "lore_fa": "نشانی با نقش جمجمه؛ قدرت نمی‌دهد، یادت می‌آورد قدرت مال کیست."},
    # ---- content pack 3 ----
    {"_id": "art_shirayuki", "icon": "🎀", "name_en": "Shirayuki's White Ribbon", "name_fa": "روبان سفید شیرایوکی",
     "bonus": {"def": 0.07, "crit": 0.02},
     "lore_en": "A ribbon of snow-white cloth. It cools the blow before it lands.",
     "lore_fa": "روبانی از پارچه‌ی سفیدِ برفی؛ ضربه را پیش از فرود سرد می‌کند."},
    {"_id": "art_kyoka", "icon": "🔍", "name_en": "Kyōka Suigetsu Shard", "name_fa": "پاره‌ی کیوکا سویگتسو",
     "bonus": {"crit": 0.07, "drop": 0.03},
     "lore_en": "A shard that remembers every illusion. It shows you what is real, and what is for sale.",
     "lore_fa": "تکه‌ای که هر توهمی را به یاد دارد؛ نشانت می‌دهد چه واقعی است و چه برای فروش."},
    {"_id": "art_zangetsu_frag", "icon": "🌑", "name_en": "Zangetsu's Broken Fragment", "name_fa": "پاره‌ی شکسته‌ی زانگتسو",
     "bonus": {"dmg": 0.07, "crit": 0.03},
     "lore_en": "A black fragment of a blade. It was broken once; now it only cuts deeper.",
     "lore_fa": "تکه‌ای سیاه از تیغه‌ای؛ یک بار شکست، و حالا فقط عمیق‌تر می‌برد."},
    {"_id": "art_visored_mask", "icon": "🎭", "name_en": "Cracked Visored Mask", "name_fa": "ماسک ترک‌خورده‌ی ویزورد",
     "bonus": {"dmg": 0.04, "def": 0.04},
     "lore_en": "The crack is a promise: the more you push, the more it holds.",
     "lore_fa": "ترک، یک قول است: هر چه بیشتر فشار بیاوری، بیشتر نگه می‌دارد."},
    {"_id": "art_gikongan", "icon": "💊", "name_en": "Gikongan Dispenser", "name_fa": "جعبه‌ی گیکونگان",
     "bonus": {"xp": 0.05, "coin": 0.04},
     "lore_en": "A candy dispenser that steps out of your body and does the work for you. Do not ask who is paying.",
     "lore_fa": "جعبه‌ی آب‌نباتی که از بدنت بیرون می‌رود و کار را به جای تو انجام می‌دهد؛ نپرس چه کسی پول می‌دهد."},
    {"_id": "art_kon_pill", "icon": "🧸", "name_en": "Kon's Mod Soul Pill", "name_fa": "قرص روح‌ساز کن",
     "bonus": {"drop": 0.05, "regen": 0.04},
     "lore_en": "A plush toy's pill. It talks too much and finds too much.",
     "lore_fa": "قرص عروسکی که زیاد حرف می‌زند و زیاد پیدا می‌کند."},
    # ---- content pack 4 ----
    {"_id": "art_senbon", "icon": "🌸", "name_en": "Senbonzakura Petal", "name_fa": "گلبرگ سنبون‌زاکورا",
     "bonus": {"dmg": 0.06, "crit": 0.03},
     "lore_en": "A single petal of a thousand blades. It cuts only when it is already too late.",
     "lore_fa": "یک گلبرگ از هزار تیغه؛ فقط وقتی می‌برد که دیگر دیر شده است."},
    {"_id": "art_benihime", "icon": "📍", "name_en": "Benihime's Crimson Pin", "name_fa": "سنجاق سرخ بنی‌هیمه",
     "bonus": {"dmg": 0.05, "def": 0.03},
     "lore_en": "A red pin that turns what it touches around. Urahara never explains how.",
     "lore_fa": "سنجاقی سرخ که هرچه لمس کند را وارونه می‌کند؛ اوراهارا هیچ‌وقت توضیح نمی‌دهد چگونه."},
    {"_id": "art_santen", "icon": "🌼", "name_en": "Santen Kesshun Hairpins", "name_fa": "سنجاق‌های سانتن کشون",
     "bonus": {"regen": 0.07, "def": 0.03},
     "lore_en": "Six petals of a hairpin; they refuse the wound and push it out of the world.",
     "lore_fa": "شش گلبرگ یک سنجاق؛ زخم را نمی‌پذیرند و از جهان بیرونش می‌رانند."},
    {"_id": "art_shinso", "icon": "🗡️", "name_en": "Shinsō Fragment", "name_fa": "پاره‌ی شینسو",
     "bonus": {"crit": 0.06, "patrol": 0.04},
     "lore_en": "A sliver of a blade that grows when it is not watched.",
     "lore_fa": "تکه‌ای از تیغی که وقتی کسی نگاهش نکند، بلندتر می‌شود."},
    {"_id": "art_mayuri", "icon": "🧪", "name_en": "Kurotsuchi Vial", "name_fa": "ویال کوروتسوچی",
     "bonus": {"drop": 0.06, "xp": 0.04},
     "lore_en": "A vial of something that is not quite a liquid. It leaves a note on your hand: “Thank you for participating.”",
     "lore_fa": "شیشه‌ای از چیزی که کاملاً مایع نیست؛ روی دستت یادداشتی می‌گذارد: «ممنون که شرکت کردی.»"},
    # ---- content pack 5 ----
    {"_id": "art_hat", "icon": "🎩", "name_en": "Urahara's Striped Hat", "name_fa": "کلاه راه‌راه اوراهارا",
     "bonus": {"coin": 0.05, "drop": 0.04},
     "lore_en": "A hat that hides a smile and a ledger. Luck seems to be on its payroll.",
     "lore_fa": "کلاهی که لبخند و دفتر حساب را پنهان می‌کند؛ ظاهراً شانس هم حقوق‌بگیر اوست."},
    {"_id": "art_eyepatch", "icon": "🩹", "name_en": "Zaraki's Restraint Eyepatch", "name_fa": "چشم‌بند مهارکننده‌ی زاراکی",
     "bonus": {"dmg": 0.08, "crit": 0.02},
     "lore_en": "It was made to hold power back. Whatever it holds, you can feel pressing against the cloth.",
     "lore_fa": "برای مهار قدرت ساخته شده؛ آنچه نگه می‌دارد را می‌شود روی پارچه حس کرد."},
    {"_id": "art_glasses", "icon": "👓", "name_en": "Aizen's Folded Spectacles", "name_fa": "عینک تاشده‌ی آیزن",
     "bonus": {"xp": 0.05, "crit": 0.03},
     "lore_en": "Whoever wears them sees each move one step early, and believes it was always so.",
     "lore_fa": "هر که بزند، هر حرکت را یک قدم زودتر می‌بیند و باور می‌کند همیشه همین بوده."},
    {"_id": "art_straw_hat", "icon": "👒", "name_en": "Kyōraku's Straw Hat", "name_fa": "کلاه حصیری کیوراکو",
     "bonus": {"drop": 0.05, "patrol": 0.04},
     "lore_en": "It keeps off the sun and keeps the world off balance. Strangers wave at it without knowing why.",
     "lore_fa": "آفتاب را دور می‌کند و جهان را از تعادل؛ غریبه‌ها بی‌دلیل برایش دست تکان می‌دهند."},
    {"_id": "art_brazo", "icon": "💪", "name_en": "Brazo Derecha Fragment", "name_fa": "پاره‌ی بازوی راست",
     "bonus": {"dmg": 0.05, "def": 0.04},
     "lore_en": "A shard of an arm that learned to answer a promise. It hits like a wall that decided to move.",
     "lore_fa": "تکه‌ای از بازویی که قولی را جواب داد؛ مثل دیواری می‌زند که تصمیم گرفته حرکت کند."},
    {"_id": "art_silver_tube", "icon": "🧿", "name_en": "Quincy Silver Tube", "name_fa": "لوله‌ی نقره‌ی کوئینسی",
     "bonus": {"crit": 0.05, "patrol": 0.03},
     "lore_en": "A tube of silver and a promise of straight lines. Light keeps its word here.",
     "lore_fa": "لوله‌ای نقره‌ای و وعده‌ی خط راست؛ نور اینجا به قولش می‌ماند."},
    # ---- content pack 6 (verified against the Bleach wiki / item database) ----
    {"_id": "art_kukaku_cannon", "icon": "🎆", "name_en": "Kukaku's Cannon", "name_fa": "توپ کوکو",
     "bonus": {"patrol": 0.04, "xp": 0.02},
     "lore_en": "Kukaku Shiba's giant firework cannon. It fires people over Seireitei's walls instead of letting them climb.",
     "lore_fa": "توپ غول‌پیکر آتش‌بازی کوکو شیبا؛ آدم‌ها را از روی دیوارهای سیرئیتی پرتاب می‌کند، نه اینکه از آن بالا بروند."},
    {"_id": "art_shihoin_shield", "icon": "🛡️", "name_en": "Shihōin Shield", "name_fa": "سپر شیهوین",
     "bonus": {"def": 0.05, "regen": 0.02},
     "lore_en": "A shield with the Shihōin family crest and a long cord. Two zanpakutō stabbed into it can break a Sōkyoku.",
     "lore_fa": "سپری با نشان خانواده‌ی شیهوین و یک بند بلند؛ دو زانپاکوتو که در آن فرو بروند می‌تواند سوکیوکو را بشکند."},
    {"_id": "art_denreishinki", "icon": "📟", "name_en": "Denreishinki", "name_fa": "دنرئیشینکی",
     "bonus": {"drop": 0.03, "patrol": 0.03},
     "lore_en": "The Shinigami's pocket communicator. It picks up Hollow signals and sends missions to the human world.",
     "lore_fa": "ارتباطی جیبی شینیگامی‌ها؛ امضای هالوها را می‌گیرد و ماموریت‌ها را به دنیای زندگان می‌فرستد."},
    {"_id": "art_gigai", "icon": "🧍", "name_en": "Reiatsu-Concealing Gigai", "name_fa": "گیکای پنهان‌ساز ریاتسو",
     "bonus": {"def": 0.03, "regen": 0.03},
     "lore_en": "Urahara's artificial body that hides a Shinigami's reiatsu, so they can live unseen in the human world.",
     "lore_fa": "بدن مصنوعی اوراهارا که ریاتسوی شینیگامی را پنهان می‌کند تا بتواند بی‌دیده‌شدن در دنیای زندگان زندگی کند."},
    {"_id": "art_gokon", "icon": "🧤", "name_en": "Gokon Tekkō", "name_fa": "دستکش گوکون تکّو",
     "bonus": {"crit": 0.03, "dmg": 0.02},
     "lore_en": "A red glove with a blue-flame skull. One push and the soul is forced out of the body.",
     "lore_fa": "دستکش قرمزی با نقش جمجمه‌ی شعله‌ور آبی؛ با یک هل دادن، روح را از بدن بیرون می‌کشد."},
    # ---- content pack 7 (verified: Bleach wiki, item database, character pages) ----
    {"_id": "art_kojaku", "icon": "🏹", "name_en": "Kojaku (Lone Sparrow)", "name_fa": "کمان کوجاکو",
     "bonus": {"crit": 0.03, "dmg": 0.02},
     "lore_en": "Uryū Ishida's first spirit bow, made of reishi. Every Quincy can summon this basic form.",
     "lore_fa": "کمان ریشی اولیه‌ی اوریو ایشیدا؛ هر کوئینسی‌ای می‌تواند این شکل پایه را احضار کند."},
    {"_id": "art_ginrei_kojaku", "icon": "🕸️", "name_en": "Ginrei Kojaku (Silver Cliff Sparrow)", "name_fa": "کوجاکوی کوهستان نقره‌ای",
     "bonus": {"dmg": 0.05, "crit": 0.03},
     "lore_en": "Uryū's restored bow, woven like a spider's web. It can fire over a thousand arrows in one volley.",
     "lore_fa": "کمان بازسازی‌شده‌ی اوریو، شبیه تار عنکبوت؛ در یک رگبار بیش از هزار تیر شلیک می‌کند."},
    {"_id": "art_quincy_bangle", "icon": "📿", "name_en": "Quincy Bangle", "name_fa": "دستبند کوئینسی",
     "bonus": {"crit": 0.03, "regen": 0.02},
     "lore_en": "A relic that gathers spirit particles and amplifies them, giving its wearer Quincy power when the bloodline fails.",
     "lore_fa": "یادگاری که ذرات روحی را جمع و تقویت می‌کند و وقتی توان ذاتی کوئینسی از دست می‌رود، قدرت خون را می‌دهد."},
    {"_id": "art_sanrei_glove", "icon": "🧤", "name_en": "Sanrei Glove", "name_fa": "دستکش سانرئی",
     "bonus": {"def": 0.03, "crit": 0.02},
     "lore_en": "A Quincy glove that repels reishi. It lets the wearer get through places where spirit power is dangerous.",
     "lore_fa": "دستکش کوئینسی که ریشی را دفع می‌کند؛ کسی که آن را دارد از جاهایی که نیروی روحی خطرناک است رد می‌شود."},
    {"_id": "art_shihakusho", "icon": "👘", "name_en": "Shihakushō (Shinigami Uniform)", "name_fa": "شیهاکوشو (یونیفرم شینیگامی)",
     "bonus": {"def": 0.03, "xp": 0.03},
     "lore_en": "The standard black Soul Reaper uniform. Simple cloth, but it marks who has trained in Soul Society.",
     "lore_fa": "یونیفرم استاندارد سیاه شینیگامی؛ پارچه‌ی ساده‌ای که نشان می‌دهد چه کسی در سوول سوسایتی آموزش دیده."},
    # ---- content pack 8 (verified: Bleach wiki Quincy and Shinigami item pages) ----
    {"_id": "art_hollow_bait", "icon": "🪙", "name_en": "Hollow Bait", "name_fa": "طعمه‌ی هالو",
     "bonus": {"patrol": 0.03, "drop": 0.03},
     "lore_en": "A coin-shaped disk. Crush it and Hollows come running from far away.",
     "lore_fa": "دیسکی سکه‌ای‌شکل؛ وقتی خردش کنی، هالوها از دور به سمتت می‌آیند."},
    {"_id": "art_quincy_cross", "icon": "✝️", "name_en": "Quincy Cross", "name_fa": "صلیب کوئینسی",
     "bonus": {"crit": 0.02, "dmg": 0.02},
     "lore_en": "The focus every Quincy needs to summon a bow. Ryūken's version is a pentacle, not a cross.",
     "lore_fa": "کانون هر کوئینسی برای احضار کمان؛ نسخه‌ی ریوکن یک پنتاگرام است، نه صلیب."},
    {"_id": "art_zajiku", "icon": "📜", "name_en": "Zajiku (Set Axis)", "name_fa": "زاجیکو (طومار هدف)",
     "bonus": {"patrol": 0.04, "xp": 0.02},
     "lore_en": "A scroll-like device that lists a Shinigami's targets and mission orders, like a Denreishinki on paper.",
     "lore_fa": "طوماری که نام هدف‌ها و دستور ماموریت شینیگامی را نشان می‌دهد؛ مثل دنرئیشینکی، ولی روی کاغذ."},
    # ---- content pack 9 (verified: Bleach wiki and an official-art source) ----
    {"_id": "art_restraint_chair", "icon": "🪑", "name_en": "Aizen's Restraint Chair", "name_fa": "صندلی مهارکننده‌ی آیزن",
     "bonus": {"def": 0.06, "regen": 0.03},
     "lore_en": "Built by the Research Institute to hold Aizen's spiritual pressure in Muken. It never broke until Yhwach destroyed it.",
     "lore_fa": "ساخته‌ی پژوهشگاه شینیگامی برای مهار فشار روحی آیزن در موکن؛ تا وقتی یهواخ نابودش کرد، نشکسته بود."},
]
ART_BY_ID = {a["_id"]: a for a in ARTIFACTS}
BONUS_ICON = (("dmg", "⚔️"), ("def", "🛡️"), ("crit", "🎯"), ("xp", "⭐"), ("drop", "🎁"), ("coin", "🪙"), ("patrol", "🧭"), ("regen", "💚"))


def art_name(aid: str, lang: str) -> str:
    a = ART_BY_ID.get(aid)
    return aid if not a else f"{a['icon']} {a['name_fa' if lang == 'fa' else 'name_en']}"


def art_bonus_text(aid: str, k: float = 1.0) -> str:
    a = ART_BY_ID.get(aid)
    if not a:
        return ""
    return " ".join(f"{ic} +{a['bonus'][key] * k * 100:.0f}%" for key, ic in BONUS_ICON if key in a["bonus"])

# --- NEW BLEACH VIRAL SYSTEM: the true Hogyoku (one copy in the whole database), typing verses, Reiatsu modifiers ---
import time as _time
import unicodedata as _ud

HOGYOKU = {"icon": "🔮", "name_fa": "هوگیوکو", "name_en": "Hōgyoku", "reiatsu_mult": 2.0,
           "bonus": {"xp": 0.20, "coin": 0.20, "drop": 0.10}}
ESPADA_N = 10
VERSES = ["Hadō #90: Kurohitsugi", "Hadō #33: Sōkatsui", "Hadō #4: Byakurai", "Hadō #31: Shakkahō", "Hadō #63: Raikōhō",
          "Hadō #73: Sōren Sōkatsui", "Bakudō #61: Rikujōkōrō", "Bakudō #81: Danku", "Bakudō #9: Hōrin",
          "Senbonzakura Kageyoshi", "Bankai: Tensa Zangetsu", "Bankai: Daiguren Hyōrinmaru", "Bankai: Kokujō Tengen Myōō",
          "Getsuga Tenshō", "Gran Rey Cero", "Cero Oscuras", "Reduce all creation to ash, Ryūjin Jakka"]


def norm_phrase(s: str) -> str:
    """Macrons, case and spacing never decide a typing race (nobody types ō on a phone)."""
    s = _ud.normalize("NFKD", s or "")
    return " ".join("".join(c for c in s if not _ud.combining(c)).lower().split())


def reiatsu_mult(ch: dict, now: float = None) -> float:
    """Hogyoku doubles Reiatsu; a failed theft halves it until `reiatsu_pen_until`."""
    now = now or _time.time()
    m = HOGYOKU["reiatsu_mult"] if (ch or {}).get("hogyoku") else 1.0
    if float((ch or {}).get("reiatsu_pen_until") or 0) > now:
        m *= 0.5
    return m

# --- TIERS (Bleach power ladder) ----------------------------------------------------------------------------------
# Every Soul Artifact now has several copies: `cap` is how many players can hold the same artifact at once.
# Stronger tiers mirror the anime's ranks: the more powerful the owner in canon, the fewer copies exist.
# COPY_MULT scales every tier's copy count at once. Raise it when the player base grows (1 = base copies).
COPY_MULT = 3
TIERS = {
    1: {"name_en": "Gotei Rank & File", "name_fa": "سرباز گوتی ۱۳", "cap": 10 * COPY_MULT},
    2: {"name_en": "Lieutenant / Captain", "name_fa": "ستوان / کاپیتان", "cap": 5 * COPY_MULT},
    3: {"name_en": "Captain-Commander / Espada", "name_fa": "فرمانده‌ی کل / اسپادا", "cap": 3 * COPY_MULT},
    4: {"name_en": "Soul King / Central 46", "name_fa": "پادشاه ارواح / سنترال ۴۶", "cap": 2 * COPY_MULT},
}
TIER_OF = {
    "art_gikongan": 1, "art_kon_pill": 1, "art_hat": 1, "art_straw_hat": 1, "art_hellbutterfly": 1,
    "art_badge": 1, "art_urahara": 1, "art_mayuri": 1, "art_shirayuki": 1, "art_glasses": 1,
    "art_haori": 1, "art_silver_tube": 1, "art_senkai": 1, "art_reishi": 1, "art_garganta": 1,
    "art_ginto": 1,
    "art_eyepatch": 2, "art_benihime": 2, "art_santen": 2, "art_kyoka": 2, "art_senbon": 2,
    "art_shinso": 2, "art_mask": 2, "art_visored_mask": 2, "art_quincy": 2, "art_seele": 2,
    "art_sekkiseki": 2, "art_brazo": 2, "art_fallen": 2,
    "art_zangetsu_frag": 3, "art_ice": 3, "art_sokyoku": 3,
    "art_soulking": 4,
    "art_kukaku_cannon": 2, "art_shihoin_shield": 3, "art_denreishinki": 1, "art_gigai": 1, "art_gokon": 1,
    "art_kojaku": 1, "art_ginrei_kojaku": 2, "art_quincy_bangle": 2, "art_sanrei_glove": 1, "art_shihakusho": 1,
    "art_hollow_bait": 1, "art_quincy_cross": 1, "art_zajiku": 1,
    "art_restraint_chair": 3,
}
MAX_STAT = 0.06  # low power on purpose: every single bonus is capped here (the old 0.10 values were too strong)
for _a in ARTIFACTS:
    _a["tier"] = TIER_OF.get(_a["_id"], 1)
    _a["cap"] = TIERS[_a["tier"]]["cap"]
    _a["bonus"] = {k: min(v, MAX_STAT) for k, v in _a["bonus"].items()}

# Every artifact must be worth carrying: at least two useful stats, each between 3% and MAX_STAT.
_FILLERS = ("def", "regen", "crit", "dmg", "xp", "drop", "patrol", "coin")
for _a in ARTIFACTS:
    _b = _a["bonus"]
    for _k in list(_b):
        _b[_k] = max(0.03, min(MAX_STAT, _b[_k]))
    for _k in _FILLERS:
        if len(_b) >= 2:
            break
        if _k not in _b:
            _b[_k] = 0.03


def art_cap(aid: str) -> int:
    a = ART_BY_ID.get(aid)
    return int(a["cap"]) if a else 1
