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
