"""Soul Artifacts: one-of-a-kind treasures. Each exists exactly once in the whole world and has a single owner at a time.
Bonus keys are the same ones `data_crafting.player_bonus` already understands (dmg, def, crit, regen, xp, drop, coin, hunt)."""

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
     "bonus": {"hunt": 0.10, "drop": 0.04},
     "lore_en": "Opens a crack between worlds. Hunts find more on the other side.",
     "lore_fa": "شکافی میان جهان‌ها باز می‌کند؛ شکارها آن‌سو بیشتر می‌یابند."},
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
     "bonus": {"hunt": 0.08, "xp": 0.02},
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
     "bonus": {"crit": 0.06, "hunt": 0.04},
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
     "bonus": {"drop": 0.05, "hunt": 0.04},
     "lore_en": "It keeps off the sun and keeps the world off balance. Strangers wave at it without knowing why.",
     "lore_fa": "آفتاب را دور می‌کند و جهان را از تعادل؛ غریبه‌ها بی‌دلیل برایش دست تکان می‌دهند."},
    {"_id": "art_brazo", "icon": "💪", "name_en": "Brazo Derecha Fragment", "name_fa": "پاره‌ی بازوی راست",
     "bonus": {"dmg": 0.05, "def": 0.04},
     "lore_en": "A shard of an arm that learned to answer a promise. It hits like a wall that decided to move.",
     "lore_fa": "تکه‌ای از بازویی که قولی را جواب داد؛ مثل دیواری می‌زند که تصمیم گرفته حرکت کند."},
    {"_id": "art_silver_tube", "icon": "🧿", "name_en": "Quincy Silver Tube", "name_fa": "لوله‌ی نقره‌ی کوئینسی",
     "bonus": {"crit": 0.05, "hunt": 0.03},
     "lore_en": "A tube of silver and a promise of straight lines. Light keeps its word here.",
     "lore_fa": "لوله‌ای نقره‌ای و وعده‌ی خط راست؛ نور اینجا به قولش می‌ماند."},
    # ---- content pack 6 (verified against the Bleach wiki / item database) ----
    {"_id": "art_kukaku_cannon", "icon": "🎆", "name_en": "Kukaku's Cannon", "name_fa": "توپ کوکو",
     "bonus": {"hunt": 0.04, "xp": 0.02},
     "lore_en": "Kukaku Shiba's giant firework cannon. It fires people over Seireitei's walls instead of letting them climb.",
     "lore_fa": "توپ غول‌پیکر آتش‌بازی کوکو شیبا؛ آدم‌ها را از روی دیوارهای سیرئیتی پرتاب می‌کند، نه اینکه از آن بالا بروند."},
    {"_id": "art_shihoin_shield", "icon": "🛡️", "name_en": "Shihōin Shield", "name_fa": "سپر شیهوین",
     "bonus": {"def": 0.05, "regen": 0.02},
     "lore_en": "A shield with the Shihōin family crest and a long cord. Two zanpakutō stabbed into it can break a Sōkyoku.",
     "lore_fa": "سپری با نشان خانواده‌ی شیهوین و یک بند بلند؛ دو زانپاکوتو که در آن فرو بروند می‌تواند سوکیوکو را بشکند."},
    {"_id": "art_denreishinki", "icon": "📟", "name_en": "Denreishinki", "name_fa": "دنرئیشینکی",
     "bonus": {"drop": 0.03, "hunt": 0.03},
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
     "bonus": {"hunt": 0.03, "drop": 0.03},
     "lore_en": "A coin-shaped disk. Crush it and Hollows come running from far away.",
     "lore_fa": "دیسکی سکه‌ای‌شکل؛ وقتی خردش کنی، هالوها از دور به سمتت می‌آیند."},
    {"_id": "art_quincy_cross", "icon": "✝️", "name_en": "Quincy Cross", "name_fa": "صلیب کوئینسی",
     "bonus": {"crit": 0.02, "dmg": 0.02},
     "lore_en": "The focus every Quincy needs to summon a bow. Ryūken's version is a pentacle, not a cross.",
     "lore_fa": "کانون هر کوئینسی برای احضار کمان؛ نسخه‌ی ریوکن یک پنتاگرام است، نه صلیب."},
    {"_id": "art_zajiku", "icon": "📜", "name_en": "Zajiku (Set Axis)", "name_fa": "زاجیکو (طومار هدف)",
     "bonus": {"hunt": 0.04, "xp": 0.02},
     "lore_en": "A scroll-like device that lists a Shinigami's targets and mission orders, like a Denreishinki on paper.",
     "lore_fa": "طوماری که نام هدف‌ها و دستور ماموریت شینیگامی را نشان می‌دهد؛ مثل دنرئیشینکی، ولی روی کاغذ."},
    # ---- content pack 9 (verified: Bleach wiki and an official-art source) ----
    {"_id": "art_restraint_chair", "icon": "🪑", "name_en": "Aizen's Restraint Chair", "name_fa": "صندلی مهارکننده‌ی آیزن",
     "bonus": {"def": 0.06, "regen": 0.03},
     "lore_en": "Built by the Research Institute to hold Aizen's spiritual pressure in Muken. It never broke until Yhwach destroyed it.",
     "lore_fa": "ساخته‌ی پژوهشگاه شینیگامی برای مهار فشار روحی آیزن در موکن؛ تا وقتی یهواخ نابودش کرد، نشکسته بود."},
    # ---- content pack 10 (32 more: Gotei, Fullbring, Espada, Wandenreich; canon objects and zanpakutō only) ----
    {"_id": "art_hiyori_sandal", "icon": "🩴", "name_en": "Hiyori's Sandal", "name_fa": "دمپایی هیوری",
     "bonus": {"dmg": 0.04, "crit": 0.03},
     "lore_en": "Thrown at Shinji's head more often than any blade has ever hit him. It does not miss.",
     "lore_fa": "بیشتر از هر تیغی به سر شینجی خورده است؛ هیچ‌وقت خطا نمی‌رود."},
    {"_id": "art_jinta_club", "icon": "🏏", "name_en": "Jinta's Iron Club", "name_fa": "گرز آهنی جینتا",
     "bonus": {"dmg": 0.04, "def": 0.03},
     "lore_en": "A boy's club from the Urahara Shop. It has seen more street fights than most swords.",
     "lore_fa": "گرز یک پسربچه از مغازه‌ی اوراهارا؛ دعوای خیابانی بیشتری از اغلب شمشیرها دیده است."},
    {"_id": "art_kukaku_pipe", "icon": "💨", "name_en": "Kūkaku's Kiseru", "name_fa": "چپق کوکاکو",
     "bonus": {"hunt": 0.04, "xp": 0.03},
     "lore_en": "Kūkaku Shiba's long pipe. The smoke curls toward whatever is about to go wrong.",
     "lore_fa": "چپق بلند کوکاکو شیبا؛ دودش به سمت هر چیزی می‌پیچد که قرار است خراب شود."},
    {"_id": "art_lieutenant_badge", "icon": "🎖️", "name_en": "Lieutenant's Badge", "name_fa": "نشان ستوان",
     "bonus": {"def": 0.03, "xp": 0.04},
     "lore_en": "The badge a Gotei lieutenant wears on the arm. It means a captain trusts you with half a division.",
     "lore_fa": "نشانی که ستوان گوتی روی بازو می‌بندد؛ یعنی یک کاپیتان نیمی از گروهان را به تو سپرده."},
    {"_id": "art_chappy", "icon": "🐰", "name_en": "Chappy the Rabbit Plush", "name_fa": "عروسک خرگوشی چپی",
     "bonus": {"drop": 0.04, "regen": 0.03},
     "lore_en": "Rukia's beloved rabbit. Nobody understands the drawing, and everybody is afraid to say so.",
     "lore_fa": "خرگوش محبوب روکیا؛ هیچ‌کس نقاشی‌اش را نمی‌فهمد و همه می‌ترسند بگویند."},
    {"_id": "art_heilig_pfeil", "icon": "🏹", "name_en": "Heilig Pfeil Arrow", "name_fa": "پیکان مقدس هایلیگ فایل",
     "bonus": {"crit": 0.04, "dmg": 0.03},
     "lore_en": "A holy arrow of gathered reishi. It flies wherever the Quincy is looking.",
     "lore_fa": "پیکانی مقدس از ریشی جمع‌شده؛ به هر جا که کوئینسی نگاه کند می‌رود."},
    {"_id": "art_yukio_console", "icon": "🎮", "name_en": "Invaders Must Die Console", "name_fa": "کنسول مهاجمان باید بمیرند",
     "bonus": {"hunt": 0.04, "drop": 0.03},
     "lore_en": "Yukio's handheld console. It shows the enemies a few seconds before they arrive.",
     "lore_fa": "کنسول دستی یوکیو؛ چند ثانیه پیش از رسیدن دشمن‌ها نشانشان می‌دهد."},
    {"_id": "art_seireitei_news", "icon": "📰", "name_en": "Seireitei Communication", "name_fa": "نشریه‌ی ارتباطات سیرِیتِی",
     "bonus": {"xp": 0.04, "drop": 0.03},
     "lore_en": "The Shinigami Women's Association newsletter. Gossip is slower than a Hell Butterfly and far more accurate.",
     "lore_fa": "خبرنامه‌ی انجمن زنان شینیگامی؛ شایعه از پروانه‌ی دوزخ کندتر است ولی دقیق‌تر."},
    {"_id": "art_urahara_cane", "icon": "🦯", "name_en": "Urahara's Cane", "name_fa": "عصای اوراهارا",
     "bonus": {"dmg": 0.05, "coin": 0.03},
     "lore_en": "A walking stick that is secretly a sword. For a hundred years it was only a good joke.",
     "lore_fa": "عصایی که پنهانی یک شمشیر است؛ صد سال فقط یک شوخی خوب بود."},
    {"_id": "art_zabimaru", "icon": "🐍", "name_en": "Zabimaru's Segmented Blade", "name_fa": "تیغه‌ی بندبند زابیمارو",
     "bonus": {"dmg": 0.05, "hunt": 0.03},
     "lore_en": "A blade that stretches like a snake's spine, once the baboon and the snake finally agree.",
     "lore_fa": "تیغه‌ای که مثل ستون فقرات مار کش می‌آید، وقتی میمون و مار بالاخره توافق کنند."},
    {"_id": "art_wabisuke", "icon": "🪝", "name_en": "Wabisuke's Hooked Blade", "name_fa": "تیغه‌ی قلاب‌دار وابی‌سوکه",
     "bonus": {"def": 0.04, "dmg": 0.03},
     "lore_en": "A hooked blade. Every strike doubles the weight of whatever it touches.",
     "lore_fa": "تیغه‌ای قلاب‌دار؛ هر ضربه وزن هر چیزی که لمس کند را دو برابر می‌کند."},
    {"_id": "art_hozukimaru", "icon": "🔱", "name_en": "Hōzukimaru Spear", "name_fa": "نیزه‌ی هوزوکیمارو",
     "bonus": {"dmg": 0.05, "crit": 0.03},
     "lore_en": "Ikkaku's three-section spear. It only trusts a straight fight and a bald head.",
     "lore_fa": "نیزه‌ی سه‌تکه‌ی ایکاکو؛ فقط به یک دعوای رو در رو و یک سر تاس اعتماد دارد."},
    {"_id": "art_ruriiro_kujaku", "icon": "🪶", "name_en": "Ruri'iro Kujaku Feather", "name_fa": "پر روری‌ایرو کوجاکو",
     "bonus": {"crit": 0.04, "drop": 0.03},
     "lore_en": "A peacock feather from a blade that insists on being beautiful. Beauty, it says, is also a weapon.",
     "lore_fa": "پر طاووسی از تیغه‌ای که اصرار دارد زیبا باشد؛ می‌گوید زیبایی هم یک سلاح است."},
    {"_id": "art_kazeshini", "icon": "🌀", "name_en": "Kazeshini's Twin Sickles", "name_fa": "داس‌های دوقلوی کازه‌شینی",
     "bonus": {"dmg": 0.04, "crit": 0.04},
     "lore_en": "Two sickles on a chain. The wind arrives first and the reaper follows.",
     "lore_fa": "دو داس بر یک زنجیر؛ اول باد می‌رسد و بعد درو‌کننده."},
    {"_id": "art_tobiume", "icon": "🌺", "name_en": "Tobiume's Plum Blossom", "name_fa": "شکوفه‌ی توبیومه",
     "bonus": {"dmg": 0.05, "crit": 0.03},
     "lore_en": "A plum blossom that burns. Its owner trusted the wrong man, and the flame never forgave the word.",
     "lore_fa": "شکوفه‌ی آلویی که می‌سوزد؛ صاحبش به آدم اشتباهی اعتماد کرد و شعله هرگز آن حرف را نبخشید."},
    {"_id": "art_haineko", "icon": "🐈‍⬛", "name_en": "Haineko's Ash Pouch", "name_fa": "کیسه‌ی خاکستر هاینکو",
     "bonus": {"def": 0.04, "hunt": 0.03},
     "lore_en": "Ash that has forgotten it was ever a blade, until the cat is called.",
     "lore_fa": "خاکستری که فراموش کرده زمانی تیغه بوده، تا وقتی که گربه صدا زده شود."},
    {"_id": "art_suzumebachi", "icon": "🐝", "name_en": "Suzumebachi Stinger", "name_fa": "نیش سوزومه‌باچی",
     "bonus": {"crit": 0.05, "dmg": 0.03},
     "lore_en": "A stinger that kills with the second strike. The first one is only a promise.",
     "lore_fa": "نیشی که با ضربه‌ی دوم می‌کشد؛ ضربه‌ی اول فقط یک قول است."},
    {"_id": "art_kenseikan", "icon": "💠", "name_en": "Kenseikan", "name_fa": "کنسیکان",
     "bonus": {"def": 0.04, "xp": 0.04},
     "lore_en": "The hair ornaments of the Kuchiki clan head, made of precious metal. They weigh more than they look.",
     "lore_fa": "زیورهای مو‌ی رئیس خاندان کوچیکی از فلزی گران‌بها؛ سنگین‌تر از آنچه به نظر می‌رسند."},
    {"_id": "art_brazo_izq", "icon": "🦾", "name_en": "Brazo Izquierda del Diablo", "name_fa": "بازوی چپ شیطان",
     "bonus": {"dmg": 0.05, "def": 0.03},
     "lore_en": "The Devil's Left Arm. It answers to someone who learned that saying no is also a kind of fight.",
     "lore_fa": "بازوی چپ شیطان؛ به کسی جواب می‌دهد که یاد گرفته «نه» گفتن هم نوعی جنگ است."},
    {"_id": "art_cross_scaffold", "icon": "✝️", "name_en": "Cross of Scaffold", "name_fa": "صلیب داربست",
     "bonus": {"dmg": 0.04, "def": 0.04},
     "lore_en": "Ginjō's Fullbring, a silver cross that becomes a great sword. A gift from a man who lied and told the truth at once.",
     "lore_fa": "فول‌برینگ گینجو، صلیبی نقره‌ای که به شمشیری بزرگ تبدیل می‌شود؛ هدیه‌ی مردی که هم‌زمان دروغ گفت و راست."},
    {"_id": "art_book_end", "icon": "📖", "name_en": "Book of the End", "name_fa": "کتاب پایان",
     "bonus": {"xp": 0.04, "drop": 0.04},
     "lore_en": "Tsukishima's Fullbring. It cuts into the past of whoever it touches and rewrites how they were remembered.",
     "lore_fa": "فول‌برینگ تسوکیشیما؛ در گذشته‌ی هر کس که لمس کند می‌برد و شیوه‌ی به یاد آوردنش را بازنویسی می‌کند."},
    {"_id": "art_senzaikyu", "icon": "🗼", "name_en": "Senzaikyū Ward", "name_fa": "مهر سنزایکیو",
     "bonus": {"def": 0.05, "regen": 0.03},
     "lore_en": "A shard of the Tower of Penitence, where Rukia was held. It remembers every wall that ever failed to hold a promise.",
     "lore_fa": "تکه‌ای از برج توبه که روکیا در آن نگه داشته شد؛ هر دیواری را به یاد دارد که نتوانست قولی را نگه دارد."},
    {"_id": "art_sternritter_cloak", "icon": "🥼", "name_en": "Sternritter Cloak", "name_fa": "شنل اشترن‌ریتر",
     "bonus": {"def": 0.04, "dmg": 0.03},
     "lore_en": "A white cloak with a letter on the back. Each Sternritter is only as strong as the letter it was given.",
     "lore_fa": "شنلی سفید با حرفی روی پشت؛ هر اشترن‌ریتر فقط به اندازه‌ی حرفی که به او داده‌اند قوی است."},
    {"_id": "art_schrift", "icon": "🔤", "name_en": "Schrift Letter", "name_fa": "حرف شریفت",
     "bonus": {"crit": 0.04, "dmg": 0.03},
     "lore_en": "A single letter Yhwach grants to a soul. It carries a power, a name, and a very short leash.",
     "lore_fa": "یک حرف که یهواخ به روحی می‌بخشد؛ قدرتی، نامی و یک افسار بسیار کوتاه با خود دارد."},
    {"_id": "art_pantera", "icon": "🐆", "name_en": "Pantera Claw Fragment", "name_fa": "پاره‌ی چنگال پانترا",
     "bonus": {"dmg": 0.06, "crit": 0.04},
     "lore_en": "A claw of Grimmjow's Resurrección. The panther never learned to wait, and the blade never learned to stop.",
     "lore_fa": "چنگالی از رسورکسیون گریمجو؛ پلنگ هرگز انتظار را یاد نگرفت و تیغه هرگز ایستادن را."},
    {"_id": "art_murcielago", "icon": "🦇", "name_en": "Murciélago Wing Shard", "name_fa": "پاره‌ی بال مورسیه‌لاگو",
     "bonus": {"crit": 0.05, "def": 0.04},
     "lore_en": "A black wing of Ulquiorra's Resurrección. In its shadow even despair feels calm and orderly.",
     "lore_fa": "بال سیاهی از رسورکسیون اولکیورا؛ در سایه‌اش حتی ناامیدی هم آرام و منظم به نظر می‌رسد."},
    {"_id": "art_los_lobos", "icon": "🐺", "name_en": "Los Lobos Pistols", "name_fa": "تپانچه‌های لوس لوبوس",
     "bonus": {"crit": 0.05, "hunt": 0.04},
     "lore_en": "The twin guns of Starrk's Resurrección. A pack of wolves for a man who hated being alone.",
     "lore_fa": "تپانچه‌های دوقلوی رسورکسیون استارک؛ یک گله‌ی گرگ برای مردی که از تنهایی بیزار بود."},
    {"_id": "art_tiburon", "icon": "🦈", "name_en": "Tiburón's Fin Blade", "name_fa": "تیغه‌ی باله‌ی تیبورون",
     "bonus": {"dmg": 0.05, "def": 0.04},
     "lore_en": "A fin from Harribel's Resurrección. Water that decided it would rather protect than drown.",
     "lore_fa": "باله‌ای از رسورکسیون هاریبل؛ آبی که تصمیم گرفت به جای غرق کردن، محافظت کند."},
    {"_id": "art_santa_teresa", "icon": "🪓", "name_en": "Santa Teresa's Blade", "name_fa": "تیغه‌ی سانتا ترزا",
     "bonus": {"dmg": 0.06, "def": 0.03},
     "lore_en": "A scythe arm of Nnoitra's Resurrección. It has no use for a guard, only for the next arm.",
     "lore_fa": "بازوی داس‌مانند رسورکسیون نویترا؛ نیازی به دفاع ندارد، فقط به بازوی بعدی."},
    {"_id": "art_ryujin_cane", "icon": "🔥", "name_en": "Yamamoto's Cane (Ryūjin Jakka)", "name_fa": "عصای یاماموتو (ریوجین جاکا)",
     "bonus": {"dmg": 0.06, "def": 0.03},
     "lore_en": "The cane of the Captain-Commander. Take your hand off the cane and the world burns for a hundred years.",
     "lore_fa": "عصای فرمانده‌ی کل؛ دستش را که از عصا بردارد، جهان صد سال می‌سوزد."},
    {"_id": "art_aizen_coat", "icon": "⚪", "name_en": "Aizen's White Coat", "name_fa": "کت سفید آیزن",
     "bonus": {"def": 0.04, "xp": 0.05},
     "lore_en": "The coat of a man who sat above every throne in Las Noches. It looks clean, and that is the worst part.",
     "lore_fa": "کت مردی که بالاتر از هر تخت لاس‌نوچس نشست؛ تمیز به نظر می‌رسد و بدترینش همین است."},
    {"_id": "art_unohana_braid", "icon": "🪢", "name_en": "Unohana's Braid", "name_fa": "گیس بافته‌ی یونوهانا",
     "bonus": {"regen": 0.05, "def": 0.03},
     "lore_en": "The braid of the first Kenpachi, worn over her chest. Whoever is healed by it is also being measured.",
     "lore_fa": "بافته‌ی نخستین کنپاچی که روی سینه‌اش می‌افتد؛ هر که با آن شفا یابد، هم‌زمان سنجیده می‌شود."},
]
# ---- Transcendent combat relics: these effects are consumed by service_combat + engine ----
ARTIFACTS.extend([
    {"_id": "art_lifesteal_crown", "icon": "🩸", "name_en": "Crimson Devourer", "name_fa": "تاج بلعنده‌ی سرخ",
     "bonus": {"dmg": 0.10, "regen": 0.08}, "rarity": "Mythic", "tier": 5,
     "effect": {"kind": "lifesteal", "value": 0.10},
     "lore_en": "Every clean strike returns a fraction of the enemy's vitality.",
     "lore_fa": "هر ضربه‌ی موفق بخشی از نیروی حیاتی دشمن را به صاحبش بازمی‌گرداند."},
    {"_id": "art_shadow_monarch", "icon": "🌑", "name_en": "Shadow Monarch Core", "name_fa": "هسته‌ی پادشاه سایه‌ها",
     "bonus": {"dmg": 0.12, "def": 0.08}, "rarity": "Divine", "tier": 6,
     "effect": {"kind": "shadow_echo", "value": 0.12},
     "lore_en": "A sovereign core that lets its bearer command a fragment of the shadow realm.",
     "lore_fa": "هسته‌ای فرمانروا که به صاحبش اجازه می‌دهد بخشی از قلمرو سایه‌ها را به خدمت بگیرد."},
    {"_id": "art_almighty", "icon": "👁️", "name_en": "The Almighty", "name_fa": "آل‌مایتی",
     "bonus": {"crit": 0.10, "def": 0.10}, "rarity": "Divine", "tier": 6,
     "effect": {"kind": "precognition", "dodge": 0.12},
     "lore_en": "A future-sight relic that reads an opening before it becomes an attack.",
     "lore_fa": "یادگاری از دیدن آینده که شکاف دفاعی را پیش از تبدیل‌شدن به حمله تشخیص می‌دهد."},
    {"_id": "art_transcendent_armor", "icon": "🛡️", "name_en": "Armor of the Undying King", "name_fa": "زره پادشاه نامیرا",
     "bonus": {"def": 0.18, "regen": 0.12}, "rarity": "Transcendent", "tier": 7,
     "effect": {"kind": "revive", "uses": 1, "hp": 0.50},
     "lore_en": "Once per battle, the armor rejects a fatal blow and restores half its bearer's vitality.",
     "lore_fa": "این زره در هر نبرد یک بار مرگ را رد می‌کند و صاحبش را با نیمی از جان زنده نگه می‌دارد."},
])

ART_BY_ID = {a["_id"]: a for a in ARTIFACTS}
BONUS_ICON = (("dmg", "⚔️"), ("def", "🛡️"), ("crit", "🎯"), ("xp", "⭐"), ("drop", "🎁"), ("coin", "🪙"), ("hunt", "🧭"), ("regen", "💚"))


def art_name(aid: str, lang: str) -> str:
    a = ART_BY_ID.get(aid)
    return aid if not a else f"{a['icon']} {a['name_fa' if lang == 'fa' else 'name_en']}"


ARTIFACT_EFFECT_TEXT = {
    "art_hogyoku": ("در هر نوبت تا ۲۴٪ قدرت آسیب را تکامل می‌دهد", "Evolves up to +24% damage over six turns"),
    "art_soulking": ("۲۰٪ HP بیشتر، ۱۲٪ ریجن، ۸٪ قدرت و یک احیای ۵۰٪", "+20% HP, +12% regeneration, +8% damage and one 50% revive"),
    "art_lifesteal_crown": ("۱۰٪ آسیب واردشده را به جان تبدیل می‌کند", "Converts 10% of damage dealt into HP"),
    "art_shadow_monarch": ("۱۲٪ آسیب اضافه از پژواک سایه وارد می‌کند", "Adds a 12% shadow-damage echo"),
    "art_almighty": ("۱۲٪ شانس جاخالی با پیش‌بینی حرکت دشمن", "12% additional dodge from precognition"),
    "art_transcendent_armor": ("یک بار در نبرد با ۵۰٪ جان احیا می‌کند", "Revives once per battle with 50% HP"),
    "art_kyoka": ("۱۸٪ آسیب اضافه از پژواک توهم وارد می‌کند", "Adds an 18% illusion-damage echo"),
    "art_glasses": ("۱۵٪ شانس جاخالی با پیش‌بینی حرکت دشمن", "15% additional dodge from precognition"),
    "art_restraint_chair": ("یک بار در نبرد با ۵۵٪ جان احیا می‌کند", "Revives once per battle with 55% HP"),
    "art_ice": ("۱۶٪ شانس جاخالی با پیش‌بینی مسیر ضربه", "16% additional dodge from frozen foresight"),
    "art_zangetsu_frag": ("۲۰٪ آسیب اضافه از پژواک گتسوگا", "Adds a 20% Getsuga damage echo"),
    "art_badge": ("۱۲٪ آسیب واردشده را به جان تبدیل می‌کند", "Converts 12% of damage dealt into HP"),
    "art_visored_mask": ("۱۴٪ آسیب واردشده را به جان تبدیل می‌کند", "Converts 14% of damage dealt into HP"),
}


def art_bonus_text(aid: str, k: float = 1.0, lang: str = "en") -> str:
    a = ART_BY_ID.get(aid)
    if not a:
        return ""
    stats = " ".join(f"{ic} +{a['bonus'][key] * k * 100:.0f}%" for key, ic in BONUS_ICON if key in a["bonus"])
    effect = ARTIFACT_EFFECT_TEXT.get(aid)
    if effect:
        stats += " · " + effect[0 if lang == "fa" else 1]
    tier = TIERS.get(int(a.get("tier", 1)), {})
    tier_name = tier.get("name_fa" if lang == "fa" else "name_en")
    return (tier_name + " · " + stats) if tier_name else stats

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
    """Hogyoku doubles Reiatsu. A failed theft no longer halves it (the old `reiatsu_pen_until` field is ignored,
    so penalties already stored on characters stop counting too)."""
    return HOGYOKU["reiatsu_mult"] if (ch or {}).get("hogyoku") else 1.0

# --- Hōgyoku duel rules (pure, no DB): the theft is a real duel decided by power, not by a dice roll -----------------
def hog_wins_needed(rounds: int) -> int:
    """Best of `rounds` (odd): 3 -> 2 wins."""
    return max(1, int(rounds)) // 2 + 1


def hog_duel_over(wins_thief: int, wins_holder: int, rounds: int):
    """State of the manual Hōgyoku duel after a round: "win" (thief has enough rounds), "fail" (holder has, or the rounds
    ran out without the thief getting there), None = play the next round."""
    if wins_thief >= hog_wins_needed(rounds):
        return "win"
    if wins_holder >= hog_wins_needed(rounds) or wins_thief + wins_holder >= max(1, int(rounds)):
        return "fail"
    return None


def hog_too_weak(power_thief: float, power_holder: float, min_ratio: float) -> bool:
    """A challenger far below the holder cannot even try (no spam from low levels, no free cooldown burn)."""
    return power_thief < max(1.0, power_holder) * float(min_ratio)


# --- TIERS (Bleach power ladder) ----------------------------------------------------------------------------------
# Every Soul Artifact now has several copies: `cap` is how many players can hold the same artifact at once.
# Stronger tiers mirror the anime's ranks: the more powerful the owner in canon, the fewer copies exist.
# COPY_MULT scales every tier's copy count at once. Raise it when the player base grows (1 = base copies).
COPY_MULT = 3
TIERS = {
    1: {"name_en": "Gotei Rank & File", "name_fa": "سرباز گوتی ۱۳", "cap": 10 * COPY_MULT},
    2: {"name_en": "Lieutenant / Captain", "name_fa": "ستوان / کاپیتان", "cap": 5 * COPY_MULT},
    3: {"name_en": "Captain-Commander / Espada", "name_fa": "فرمانده‌ی کل / اسپادا", "cap": 3 * COPY_MULT},
    4: {"name_en": "Legendary", "name_fa": "افسانه‌ای", "cap": 2 * COPY_MULT},
    # High-tier relics are deliberately scarce and have fixed world copy caps.
    5: {"name_en": "Mythic", "name_fa": "میتیک", "cap": 1},
    6: {"name_en": "Divine", "name_fa": "دیواین", "cap": 2},
    7: {"name_en": "Transcendent", "name_fa": "ترنسندنت", "cap": 2},
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
    # pack 10
    "art_hiyori_sandal": 1, "art_jinta_club": 1, "art_kukaku_pipe": 1, "art_lieutenant_badge": 1, "art_chappy": 1,
    "art_heilig_pfeil": 1, "art_yukio_console": 1, "art_seireitei_news": 1,
    "art_urahara_cane": 2, "art_zabimaru": 2, "art_wabisuke": 2, "art_hozukimaru": 2, "art_ruriiro_kujaku": 2,
    "art_kazeshini": 2, "art_tobiume": 2, "art_haineko": 2, "art_suzumebachi": 2, "art_kenseikan": 2,
    "art_brazo_izq": 2, "art_cross_scaffold": 2, "art_book_end": 2, "art_senzaikyu": 2,
    "art_sternritter_cloak": 2, "art_schrift": 2,
    "art_pantera": 3, "art_murcielago": 3, "art_los_lobos": 3, "art_tiburon": 3, "art_santa_teresa": 3,
    "art_ryujin_cane": 3, "art_aizen_coat": 3, "art_unohana_braid": 3,
    "art_lifesteal_crown": 5, "art_shadow_monarch": 6, "art_almighty": 6, "art_transcendent_armor": 7,
}
MAX_STAT = 0.06  # low power on purpose: every single bonus is capped here (the old 0.10 values were too strong)
for _a in ARTIFACTS:
    _a["tier"] = TIER_OF.get(_a["_id"], 1)
    _a["cap"] = TIERS[_a["tier"]]["cap"]
    _a["bonus"] = {k: min(v, MAX_STAT) for k, v in _a["bonus"].items()}

# Every artifact must be worth carrying: at least two useful stats, each between 3% and MAX_STAT.
_FILLERS = ("def", "regen", "crit", "dmg", "xp", "drop", "hunt", "coin")
for _a in ARTIFACTS:
    _b = _a["bonus"]
    for _k in list(_b):
        _b[_k] = max(0.03, min(MAX_STAT, _b[_k]))
    for _k in _FILLERS:
        if len(_b) >= 2:
            break
        if _k not in _b:
            _b[_k] = 0.03


# ---- SIGNATURE RELICS (Aizen / Tōshirō Hitsugaya / Ichigo) --------------------------------------------------------
# Deliberate exception to the low-power rule: these are the strongest and rarest artifacts in the game.
# One artifact per player (ch["artifact"]); data_crafting.player_bonus still caps xp/drop/coin/dmg/def at 60% overall.
SIGNATURE = {
    # Sōsuke Aizen
    "art_hogyoku":         {"dmg": 0.30, "def": 0.18, "xp": 0.18},
    "art_kyoka":           {"crit": 0.22, "dmg": 0.25, "drop": 0.18},
    "art_glasses":         {"xp": 0.32, "crit": 0.18, "hunt": 0.18},
    "art_restraint_chair": {"def": 0.35, "regen": 0.22, "dmg": 0.15},
    # Tōshirō Hitsugaya (Hyōrinmaru)
    "art_ice":             {"def": 0.32, "dmg": 0.28, "regen": 0.14},
    # Ichigo Kurosaki
    "art_zangetsu_frag":   {"dmg": 0.35, "crit": 0.18, "def": 0.14},
    "art_badge":           {"dmg": 0.28, "xp": 0.25, "def": 0.14},
    "art_soulking":        {"dmg": 0.22, "def": 0.22, "regen": 0.20, "xp": 0.20},
    "art_visored_mask":    {"dmg": 0.28, "def": 0.22, "crit": 0.12},
}
SIGNATURE_TIER = 5
SIGNATURE_DROP_WEIGHT = 0.05  # relative chance to be picked for a drop, compared with 1.0 for every other artifact
for _a in ARTIFACTS:
    if _a["_id"] in SIGNATURE:
        _a["tier"] = SIGNATURE_TIER
        _a["cap"] = TIERS[SIGNATURE_TIER]["cap"]
        _a["bonus"] = dict(SIGNATURE[_a["_id"]])

# Hōgyoku and Soul King are evolving relics with one emergency safeguard per battle.
ART_BY_ID["art_hogyoku"]["effect"] = {"kind": "hogyoku_evolution"}
ART_BY_ID["art_soulking"]["effect"] = {"kind": "soulking", "uses": 1, "hp": 0.50, "hp_mult": 1.20, "regen": 0.12, "dmg": 0.08}
# Signature/Mythic artifacts must have a real combat passive, not just panel stats.
# These use the same validated combat hooks as the Divine/Transcendent artifacts.
ART_BY_ID["art_kyoka"]["effect"] = {"kind": "shadow_echo", "value": 0.18}
ART_BY_ID["art_glasses"]["effect"] = {"kind": "precognition", "dodge": 0.15}
ART_BY_ID["art_restraint_chair"]["effect"] = {"kind": "revive", "uses": 1, "hp": 0.55}
ART_BY_ID["art_ice"]["effect"] = {"kind": "precognition", "dodge": 0.16}
ART_BY_ID["art_zangetsu_frag"]["effect"] = {"kind": "shadow_echo", "value": 0.20}
ART_BY_ID["art_badge"]["effect"] = {"kind": "lifesteal", "value": 0.12}
ART_BY_ID["art_visored_mask"]["effect"] = {"kind": "lifesteal", "value": 0.14}


def art_drop_weight(aid: str) -> float:
    """Relative selection weight: Mythic/Divine/Transcendent copies are genuinely rare, not just capped."""
    if aid in SIGNATURE:
        return SIGNATURE_DROP_WEIGHT
    a = ART_BY_ID.get(aid)
    tier = int(a.get("tier", 1)) if a else 1
    return {5: 0.05, 6: 0.02, 7: 0.005}.get(tier, 1.0)


def art_due(chance: float, now: float, last_art_at: float, pity_seconds: float, roll: float) -> bool:
    """Should this drop be a Soul Artifact?

    `roll` is a random number in [0, 1). A plain chance alone made artifacts rare (about one every 14 busy hours),
    so a group that has gone `pity_seconds` without one gets a guaranteed artifact on its next drop.
    `last_art_at` = 0 means the group has never had one, so the pity timer counts from 0 and is already due."""
    if pity_seconds and pity_seconds > 0 and now - float(last_art_at or 0) >= pity_seconds:
        return True
    return roll < float(chance)


def art_cap(aid: str) -> int:
    a = ART_BY_ID.get(aid)
    return int(a["cap"]) if a else 1


def art_held_count(holders: int, active_listings: int) -> int:
    """Reconciled occupied copies. Never clamp to cap: an over-cap legacy state must block new drops."""
    return max(0, int(holders)) + max(0, int(active_listings))


# ---- Anime-accurate artifact powers (Nov 25) --------------------------------------------------------------------
# Tier 6/7 relics (Almighty, Shadow Monarch, Undying King) had tier-1 sized stats; lift them to the Mythic level.
POWER_BONUS = {
    "art_almighty": {"dmg": 0.40, "crit": 0.22, "def": 0.25, "xp": 0.30},
    "art_shadow_monarch": {"dmg": 0.42, "def": 0.22, "regen": 0.15, "crit": 0.15},
    "art_transcendent_armor": {"def": 0.45, "regen": 0.28, "dmg": 0.25},
    "art_lifesteal_crown": {"dmg": 0.30, "regen": 0.15, "def": 0.12},
    "art_ice": {"def": 0.38, "dmg": 0.36, "regen": 0.16},
}
for _id, _b in POWER_BONUS.items():
    ART_BY_ID[_id]["bonus"] = dict(_b)

# extra: dodge, lifesteal, echo (extra damage share), stun_p (on-hit chance the foe loses its next turn, once per 3 turns),
# burn_p / bleed_p (on-hit status chance), thorns (share of damage taken sent back), pierce (armour ignored),
# low_hp [hp share, damage bonus] (the anime "never give up" surge), revive [uses, hp share].
ANIME_EXTRA = {
    # Ichigo
    "art_zangetsu_frag": {"echo": 0.20, "low_hp": [0.50, 0.25], "pierce": 0.08},
    "art_badge": {"lifesteal": 0.12, "low_hp": [0.35, 0.35]},
    "art_visored_mask": {"lifesteal": 0.14, "low_hp": [0.50, 0.20], "turn_heal": 0.01},
    # Aizen
    "art_glasses": {"foresight": 4, "dodge": 0.10, "stun_p": 0.15},
    "art_restraint_chair": {"revive": [1, 0.55], "thorns": 0.20},
    "art_kyoka": {"echo": 0.18, "dodge": 0.08, "stun_p": 0.10},
    "art_aizen_coat": {"dodge": 0.08, "stun_p": 0.08},
    # Toshiro (Hyorinmaru)
    "art_ice": {"dodge": 0.12, "stun_p": 0.25, "pierce": 0.15, "thorns": 0.12},
    # Yhwach
    "art_almighty": {"foresight": 3, "no_crit": True, "dodge": 0.10, "stun_p": 0.12, "revive": [1, 0.60], "pierce": 0.15},
    "art_transcendent_armor": {"revive": [1, 0.60], "thorns": 0.15, "hit_cap": 0.30},
    "art_shadow_monarch": {"echo": 0.22, "lifesteal": 0.08},
    # captains and arrancar relics
    "art_ryujin_cane": {"opener": 0.25, "echo": 0.06},
    "art_sokyoku": {"opener": 0.30, "echo": 0.10},
    "art_unohana_braid": {"lifesteal": 0.10},
    "art_shihoin_shield": {"thorns": 0.12, "dodge": 0.08},
    "art_pantera": {"open_shield": 0.06, "mitigate": 0.03},
    "art_murcielago": {"dodge": 0.06, "turn_heal": 0.01},
    "art_los_lobos": {"pierce": 0.12},
    "art_tiburon": {"lifesteal": 0.05, "mitigate": 0.04},
    "art_santa_teresa": {"echo": 0.08, "open_shield": 0.05},
    "art_senbon": {"echo": 0.06},
    "art_benihime": {"pierce": 0.08},
    "art_seele": {"pierce": 0.10},
    "art_eyepatch": {"low_hp": [0.50, 0.15]},
    "art_mask": {"low_hp": [0.50, 0.12]},
}
for _id, _ex in ANIME_EXTRA.items():
    _eff = ART_BY_ID[_id].get("effect") or {"kind": "extra"}
    _eff["extra"] = dict(_ex)
    if _id == "art_ice":
        _eff = {"kind": "extra", "extra": dict(_ex)}
    ART_BY_ID[_id]["effect"] = _eff


def _extra_text(ex: dict):
    fa, en = [], []
    def add(a, b):
        fa.append(a); en.append(b)
    p = lambda v: f"{round(v * 100):g}"
    if ex.get("dodge"): add(f"+{p(ex['dodge'])}٪ جاخالی", f"+{p(ex['dodge'])}% dodge")
    if ex.get("lifesteal"): add(f"{p(ex['lifesteal'])}٪ دمیج به جان تبدیل می‌شود", f"{p(ex['lifesteal'])}% of damage becomes HP")
    if ex.get("echo"): add(f"+{p(ex['echo'])}٪ دمیج پژواک", f"+{p(ex['echo'])}% echo damage")
    if ex.get("stun_p"): add(f"{p(ex['stun_p'])}٪ شانس از دست رفتن نوبت دشمن", f"{p(ex['stun_p'])}% chance the foe loses its turn")
    if ex.get("burn_p"): add(f"{p(ex['burn_p'])}٪ شانس سوزاندن", f"{p(ex['burn_p'])}% chance to burn")
    if ex.get("bleed_p"): add(f"{p(ex['bleed_p'])}٪ شانس خون‌ریزی", f"{p(ex['bleed_p'])}% chance to bleed")
    if ex.get("thorns"): add(f"{p(ex['thorns'])}٪ دمیج دریافتی بازتاب می‌شود", f"{p(ex['thorns'])}% of damage taken is reflected")
    if ex.get("pierce"): add(f"{p(ex['pierce'])}٪ نفوذ از دفاع", f"{p(ex['pierce'])}% armour ignored")
    if ex.get("foresight"): add(f"آینده را می‌بیند: از هر {ex['foresight']} ضربه‌ی دشمن، یکی حتماً جاخالی می‌شود", f"sees the future: one of every {ex['foresight']} blows against you is always dodged")
    if ex.get("no_crit"): add("ضربه‌ی کریتیکال دشمن بی‌اثر می‌شود", "enemy critical hits are erased")
    if ex.get("hit_cap"): add(f"هیچ ضربه‌ای بیشتر از {p(ex['hit_cap'])}٪ جان را نمی‌گیرد", f"no blow takes more than {p(ex['hit_cap'])}% of your HP")
    if ex.get("opener"): add(f"ضربه‌ی اول مبارزه +{p(ex['opener'])}٪ قوی‌تر", f"your first blow of a fight hits +{p(ex['opener'])}% harder")
    if ex.get("open_shield"): add(f"مبارزه را با سپر {p(ex['open_shield'])}٪ جان شروع می‌کنی", f"start every fight behind a barrier of {p(ex['open_shield'])}% HP")
    if ex.get("mitigate"): add(f"{p(ex['mitigate'])}٪ کاهش هر دمیج دریافتی", f"{p(ex['mitigate'])}% less damage from every blow")
    if ex.get("turn_heal"): add(f"هر نوبت {p(ex['turn_heal'])}٪ ترمیم", f"heals {p(ex['turn_heal'])}% each turn")
    if ex.get("low_hp"): add(f"زیر {p(ex['low_hp'][0])}٪ جان: +{p(ex['low_hp'][1])}٪ دمیج", f"below {p(ex['low_hp'][0])}% HP: +{p(ex['low_hp'][1])}% damage")
    if ex.get("revive"): add(f"یک احیا با {p(ex['revive'][1])}٪ جان", f"one revive at {p(ex['revive'][1])}% HP")
    return "، ".join(fa), "; ".join(en)


for _id, _ex in ANIME_EXTRA.items():
    _fa, _en = _extra_text(_ex)
    ARTIFACT_EFFECT_TEXT[_id] = (_fa, _en)
