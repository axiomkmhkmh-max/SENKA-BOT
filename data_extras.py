"""Pure data for the six 'addictive loop' features: Soul Tower, Dispatch, win chain,
Urahara's wheel, Gotei seat ranks and the Inner World. No I/O here."""

# ---- Soul Tower ------------------------------------------------------------------------------------
TOWER_ENEMIES = [
    ("هالوی سایه", "Shadow Hollow"), ("استخوان‌خوار", "Bone Eater"), ("نگهبان ماسک‌دار", "Masked Warden"),
    ("گرگ ریاتسو", "Reiatsu Wolf"), ("شکارچی سکوت", "Silent Stalker"), ("دیوِ برج", "Tower Fiend"),
    ("شبح گارگانتا", "Garganta Wraith"), ("پژواک ماسک", "Mask Echo"),
]
TOWER_BOSS_EVERY = 5

# ---- Dispatch --------------------------------------------------------------------------------------
MISSIONS = {
    "patrol": {"hours": 2, "level": 1, "fa": "گشت کاراکورا", "en": "Karakura Patrol", "k": 1.0},
    "hunt": {"hours": 4, "level": 10, "fa": "شکار هالو در روکونگای", "en": "Rukongai Hollow Hunt", "k": 1.15},
    "scout": {"hours": 8, "level": 20, "fa": "دیده‌بانی هوئکو موندو", "en": "Hueco Mundo Scouting", "k": 1.3},
}
RARITY_MULT = {"Common": 1.0, "Uncommon": 1.15, "Rare": 1.35, "Epic": 1.7, "Legendary": 2.2, "Mythic": 3.0}
ROLE_NOTE = {  # role -> (fa, en)
    "attacker": ("سکه‌ی بیشتر", "bonus coins"), "caster": ("تجربه بیشتر", "bonus XP"),
    "tank": ("یک ماده‌ی کمیاب", "a rare material"), "support": ("انرژی برمی‌گرداند", "restores energy"),
}

# ---- Urahara's wheel ---------------------------------------------------------------------------------
# (id, weight, icon, fa, en)
WHEEL = [
    ("coins_s", 26, "🪙", "کیسه‌ی سکه", "Pouch of coins"),
    ("xp", 20, "📖", "درس سخت اوراهارا", "Urahara's lesson (XP)"),
    ("energy", 14, "⚡", "انرژی کامل", "Full energy"),
    ("potion", 12, "🧪", "معجون", "Potion"),
    ("material", 9, "💎", "ماده‌ی کمیاب", "Rare material"),
    ("egg", 6, "🥚", "تخم روح", "Spirit egg"),
    ("key", 5, "🔑", "کلید دانجن", "Dungeon key"),
    ("book", 4, "📘", "کتاب", "Book"),
    ("coins_l", 3, "💰", "گنجینه‌ی سکه", "Treasure of coins"),
    ("relic", 0.9, "🗿", "یادگار", "Relic"),
    ("jackpot", 0.1, "🌟", "جکپات!", "JACKPOT!"),
]

# ---- Gotei seat ranks (season points) -------------------------------------------------------------------
# (min season points, icon, fa, en)
SEATS = [
    (0, "▫️", "عضو بدون درجه", "Unseated"),
    (40, "🔹", "کرسی ۲۰", "20th Seat"),
    (150, "🔷", "کرسی ۱۵", "15th Seat"),
    (400, "⚔️", "کرسی ۱۰", "10th Seat"),
    (800, "🎖️", "کرسی ۵", "5th Seat"),
    (1500, "🌟", "کرسی ۳", "3rd Seat"),
    (2800, "🏵️", "ستوان", "Lieutenant"),
    (4500, "👑", "کاپیتان", "Captain"),
]


def seat_index(pts: int) -> int:
    idx = 0
    for i, (need, *_rest) in enumerate(SEATS):
        if pts >= need:
            idx = i
    return idx


def seat_icon(idx: int) -> str:
    idx = max(0, min(len(SEATS) - 1, int(idx or 0)))
    return SEATS[idx][1] if idx > 0 else ""


# ---- Inner World ------------------------------------------------------------------------------------------
# Each scene: text (fa, en) with {w} = blade name; two choices -> (label fa, label en, outcome fa, outcome en, effect)
# effect: bond = bond points, xp = multiplier of level-based XP, buff = (key, pct, minutes)
INNER = [
    {"t": ("در دنیای درون، {w} روی پلی از شیشه ایستاده و از تو می‌پرسد: «برای چه می‌جنگی؟»",
           "In your inner world {w} stands on a bridge of glass and asks: “What do you fight for?”"),
     "a": ("برای محافظت", "To protect", "تیغه سر تکان می‌دهد. پیوندتان محکم‌تر می‌شود.", "The blade nods. Your bond deepens.", {"bond": 25}),
     "b": ("برای قوی‌تر شدن", "To grow stronger", "تیغه می‌خندد و قدرتش را قرض می‌دهد.", "The blade grins and lends you its edge.", {"bond": 10, "buff": ("xp_pct", 0.10, 30)})},
    {"t": ("آسمان درونت شب است و {w} سایه‌ای را نشان می‌دهد: «این هم بخشی از توست.»",
           "The sky inside you is night, and {w} points at a shadow: “This is a part of you too.”"),
     "a": ("بپذیرمش", "Accept it", "سایه محو می‌شود و ریاتسوی‌ات آرام می‌گیرد.", "The shadow fades; your reiatsu settles.", {"bond": 25}),
     "b": ("با آن بجنگم", "Fight it", "برنده می‌شوی، ولی زخمی بیرون می‌آیی.", "You win, though not unscathed.", {"bond": 10, "xp": 1.0})},
    {"t": ("{w} در ساحلی بی‌پایان نشسته است: «امروز نمی‌خواهم جنگ. فقط حرف بزن.»",
           "{w} sits on an endless shore: “I don't want a fight today. Just talk to me.”"),
     "a": ("از ترس‌هایم بگویم", "Speak of my fears", "سبک‌تر از همیشه بیدار می‌شوی.", "You wake lighter than ever.", {"bond": 30}),
     "b": ("از آرزوهایم بگویم", "Speak of my dreams", "تیغه گوش می‌دهد و سکه‌ها را شانس می‌آورد.", "The blade listens and luck follows your coins.", {"bond": 10, "buff": ("coin_pct", 0.10, 30)})},
    {"t": ("صدای زنگ می‌آید. {w} می‌گوید: «قدرت واقعی را فقط وقتی می‌شناسی که بشکنی.»",
           "A bell tolls. {w} says: “You only know true strength once you've been broken.”"),
     "a": ("آماده‌ام", "I'm ready", "ضربه‌ای درونی می‌خوری و قوی‌تر برمی‌خیزی.", "An inner blow lands; you rise stronger.", {"bond": 15, "xp": 1.5}),
     "b": ("هنوز نه", "Not yet", "تیغه صبور می‌ماند.", "The blade waits, patient.", {"bond": 20})},
    {"t": ("{w} یک پر سفید به تو می‌دهد: «نگهش دار. روزی لازم می‌شود.»",
           "{w} hands you a white feather: “Keep it. One day you will need it.”"),
     "a": ("نگهش می‌دارم", "I'll keep it", "پر در ریاتسوی‌ات حل می‌شود.", "The feather dissolves into your reiatsu.", {"bond": 25}),
     "b": ("به او برمی‌گردانم", "I give it back", "تیغه لبخند می‌زند و شانست را بالا می‌برد.", "The blade smiles and favors your hunts.", {"bond": 10, "buff": ("drop_pct", 0.10, 30)})},
    {"t": ("آینه‌ای در دنیای درونت ترک خورده. {w} می‌گوید: «این تویی، دو سال پیش.»",
           "A mirror in your inner world is cracked. {w} says: “That was you, two years ago.”"),
     "a": ("بشکنمش", "Shatter it", "گذشته می‌شکند و جایش قدرت می‌آید.", "The past breaks and power takes its place.", {"bond": 10, "xp": 1.2}),
     "b": ("نگهش دارم", "Keep it", "پیوندتان از یادآوری محکم می‌شود.", "Remembering strengthens your bond.", {"bond": 25})},
    {"t": ("{w} زمزمه می‌کند: «اسم من را بگو.» ولی هنوز نمی‌دانی…",
           "{w} whispers: “Say my name.” But you do not know it yet…"),
     "a": ("تلاش می‌کنم", "I'll try", "هنوز آماده نیستی؛ ولی تیغه قدردانی می‌کند.", "You aren't ready, but the blade respects the try.", {"bond": 25}),
     "b": ("صبر می‌کنم", "I'll wait", "سکوتتان خودش یک جواب است.", "Your shared silence is an answer.", {"bond": 15, "xp": 0.8})},
    {"t": ("باد می‌وزد و {w} شمشیرش را روی زمین می‌گذارد: «یک دوئل دوستانه؟»",
           "The wind rises and {w} lays down its blade: “A friendly spar?”"),
     "a": ("قبول", "Accept", "ضربه‌های سبک رد و بدل می‌شود. مهارتت صیقل می‌خورد.", "Light blows trade; your skill sharpens.", {"bond": 15, "xp": 1.2}),
     "b": ("فقط تماشا", "Just watch", "از او چیزهایی یاد می‌گیری.", "You learn simply from watching.", {"bond": 20})},
]
