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
