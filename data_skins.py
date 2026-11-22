"""Skins (اسکین‌ها): 30 outfits, 10 Epic + 10 Legendary + 10 Mythic. Pure data and pure functions: no I/O, no Telegram.

A skin is never only decoration. The ONE equipped skin adds small, capped, useful passives:
  xp / coin / drop   -> go through data_crafting.player_bonus (the same pipeline relics use);
  calm / stab        -> the world-calm and Seireitei-stability numbers of player_bonus;
  core               -> raises the chance of every Soul Core roll (quests, dungeons, events) by this fraction;
  wheel              -> discount on the Soul Core price of paid wheel spins (capped at WHEEL_DISCOUNT_CAP);
  pity               -> pulls both wheel pity thresholds closer by this many spins.
Nothing here touches damage, defence, crit or the attack panel on purpose.
Strength by rarity: Epic = one passive, Legendary = two, Mythic = three.
"""

RARITIES = ("Epic", "Legendary", "Mythic")
RARITY_ICON = {"Epic": "🟪", "Legendary": "🟧", "Mythic": "🟥"}
RARITY_FA = {"Epic": "حماسی", "Legendary": "افسانه‌ای", "Mythic": "اسطوره‌ای"}

PB_KEYS = ("xp", "coin", "drop", "calm", "stab")        # added through player_bonus
EXTRA_KEYS = ("core", "wheel", "pity")                  # read by service_cores / service_wheels
WHEEL_DISCOUNT_CAP = 0.10
CORE_BOOST_CAP = 0.30

LABEL = {
    "xp": ("تجربه", "XP"), "coin": ("سکه", "Coins"), "drop": ("شانس دراپ", "Drop rate"),
    "calm": ("آرامش جهان", "World calm"), "stab": ("ثبات سیرِیتِی", "Seireitei stability"),
    "core": ("شانس هسته‌ی روح", "Soul Core chance"), "wheel": ("تخفیف چرخش گردونه", "Wheel spin discount"),
    "pity": ("نزدیک‌تر شدن ضمانت", "Closer pity"),
}

# coins paid when a spin gives a skin the player already owns
DUP_COINS = {"Epic": 4000, "Legendary": 15000, "Mythic": 50000}

# id, icon, rarity, fa, en, bonus
_RAW = [
    # ---- Epic: one passive ------------------------------------------------------------------------------------
    ("sk_e01", "🌙", "Epic", "شیهاکوشوی مهتابی", "Moonlit Shihakushō", {"xp": 0.04}),
    ("sk_e02", "🌸", "Epic", "هائوری گلبرگ‌ریز", "Petal-Drift Haori", {"coin": 0.05}),
    ("sk_e03", "🎩", "Epic", "شنل کلاه‌راه‌راه", "Striped-Hat Cloak", {"drop": 0.04}),
    ("sk_e04", "🛡️", "Epic", "یونیفرم نگهبان گوتی", "Gotei Guard Uniform", {"stab": 0.04}),
    ("sk_e05", "🎭", "Epic", "نقاب هالو", "Hollow Mask Veil", {"calm": 0.08}),
    ("sk_e06", "✝️", "Epic", "ردای صلیب کوئینسی", "Quincy Cross Vestment", {"core": 0.08}),
    ("sk_e07", "🧊", "Epic", "شنل یخ‌زده", "Frostbound Cloak", {"wheel": 0.03}),
    ("sk_e08", "🔥", "Epic", "کمربند اخگر", "Ember Sash", {"pity": 3}),
    ("sk_e09", "🧤", "Epic", "کت فول‌برینگ", "Fullbring Coat", {"xp": 0.04}),
    ("sk_e10", "🌧️", "Epic", "پانچوی باران روکونگای", "Rukongai Rain Poncho", {"coin": 0.05}),
    # ---- Legendary: two passives ------------------------------------------------------------------------------
    ("sk_l01", "👑", "Legendary", "هائوری سپیده‌دم کاپیتان", "Captain's Haori of Dawn", {"xp": 0.07, "coin": 0.07}),
    ("sk_l02", "🌑", "Legendary", "کت رنگ‌پریده‌ی اسپادا", "Espada Pale Coat", {"drop": 0.07, "calm": 0.14}),
    ("sk_l03", "🏹", "Legendary", "شنل استرنریتر", "Sternritter Mantle", {"core": 0.15, "stab": 0.07}),
    ("sk_l04", "🐺", "Legendary", "شنل پادشاه جانوران", "Beast-King Cloak", {"coin": 0.08, "wheel": 0.05}),
    ("sk_l05", "🌺", "Legendary", "کیمونوی هزار گلبرگ", "Thousand-Petal Kimono", {"xp": 0.07, "pity": 5}),
    ("sk_l06", "🩸", "Legendary", "جامه‌ی ماه خونین", "Blood-Moon Garb", {"drop": 0.07, "core": 0.15}),
    ("sk_l07", "🔮", "Legendary", "نقاب پیشگوی هوگیوکو", "Veil of the Hōgyoku Seer", {"wheel": 0.05, "pity": 5}),
    ("sk_l08", "🦋", "Legendary", "ابریشم جیگوکوچو", "Jigokuchō Silk", {"calm": 0.14, "stab": 0.07}),
    ("sk_l09", "🌌", "Legendary", "کت مسافر دنگای", "Dangai Traveler's Coat", {"xp": 0.07, "drop": 0.07}),
    ("sk_l10", "⚜️", "Legendary", "جامه‌ی نگهبان سلطنتی", "Royal Guard Regalia", {"coin": 0.08, "core": 0.15}),
    # ---- Mythic: three passives -------------------------------------------------------------------------------
    ("sk_m01", "🔱", "Mythic", "ردای شاه ارواح", "Soul King's Vestment", {"xp": 0.10, "coin": 0.12, "core": 0.25}),
    ("sk_m02", "🌕", "Mythic", "شنل سایه‌ی امپراتور", "Mantle of the Shadow Emperor", {"drop": 0.10, "core": 0.25, "wheel": 0.08}),
    ("sk_m03", "🟧", "Mythic", "جامه‌ی شینیگامی جانشین", "Substitute Shinigami Regalia", {"xp": 0.10, "drop": 0.10, "pity": 8}),
    ("sk_m04", "⚫", "Mythic", "نقاب سیاهی مطلق", "Mask of Absolute Black", {"calm": 0.20, "stab": 0.10, "core": 0.25}),
    ("sk_m05", "🦋", "Mythic", "ردای رؤیای پروانه", "Robe of the Butterfly Dream", {"coin": 0.12, "wheel": 0.08, "pity": 8}),
    ("sk_m06", "🐉", "Mythic", "هائوری شعله‌ی اژدها", "Dragon-Flame Haori", {"xp": 0.10, "coin": 0.12, "drop": 0.10}),
    ("sk_m07", "❄️", "Mythic", "جامه‌ی زمستان ابدی", "Eternal Winter Regalia", {"stab": 0.10, "calm": 0.20, "wheel": 0.08}),
    ("sk_m08", "🌹", "Mythic", "کیمونوی ده‌هزار تیغه‌ی گل", "Ten-Thousand Blossom Kimono", {"drop": 0.10, "coin": 0.12, "core": 0.25}),
    ("sk_m09", "⚡", "Mythic", "شنل خشم جوخه‌ی یازدهم", "Cloak of the Eleventh's Fury", {"xp": 0.10, "coin": 0.12, "pity": 8}),
    ("sk_m10", "🕳️", "Mythic", "ردای تاج منوس", "Menos Crown Raiment", {"core": 0.25, "wheel": 0.08, "pity": 8}),
]


def _build():
    out = {}
    for sid, icon, rar, fa, en, bonus in _RAW:
        out[sid] = {"id": sid, "icon": icon, "rarity": rar, "fa": fa, "en": en, "bonus": dict(bonus)}
    return out


SKINS = _build()
SKIN_IDS = list(SKINS)
BY_RARITY = {r: [s for s in SKIN_IDS if SKINS[s]["rarity"] == r] for r in RARITIES}


def skin_by_id(sid):
    return SKINS.get(sid or "")


def equipped_skin(ch: dict):
    """The equipped skin dict, or None. A skin only counts when the character really owns it."""
    sid = (ch or {}).get("skin")
    if not sid or sid not in SKINS:
        return None
    if sid not in ((ch or {}).get("skins_owned") or []):
        return None
    return SKINS[sid]


def skin_bonus(ch: dict) -> dict:
    """The part that goes through player_bonus: {xp, coin, drop, calm, stab} (only keys the skin has)."""
    s = equipped_skin(ch)
    if not s:
        return {}
    return {k: float(v) for k, v in s["bonus"].items() if k in PB_KEYS}


def skin_extra(ch: dict) -> dict:
    """Always returns {core, wheel, pity}, zeros when no skin, all capped."""
    out = {"core": 0.0, "wheel": 0.0, "pity": 0}
    s = equipped_skin(ch)
    if not s:
        return out
    b = s["bonus"]
    out["core"] = min(CORE_BOOST_CAP, float(b.get("core", 0.0)))
    out["wheel"] = min(WHEEL_DISCOUNT_CAP, float(b.get("wheel", 0.0)))
    out["pity"] = int(b.get("pity", 0))
    return out


def bonus_text(skin: dict, lang: str = "fa") -> str:
    """One readable line, e.g. '+7% XP · +7% Coins'."""
    parts = []
    for k, v in skin["bonus"].items():
        label = LABEL[k][0 if lang == "fa" else 1]
        if k == "pity":
            parts.append(f"{label}: {int(v)}" if lang == "fa" else f"{label}: {int(v)} spins")
        else:
            parts.append(f"+{round(v * 100)}٪ {label}" if lang == "fa" else f"+{round(v * 100)}% {label}")
    return " · ".join(parts)


# ---- how likely each wheel result is to also carry a skin / a katana boost -------------------------------------
# keys of game settings (admin-tunable); defaults are used when the setting is missing.
SKIN_CHANCE_KEY = {"Epic": "skin_chance_epic", "Legendary": "skin_chance_leg", "Mythic": "skin_chance_myth", "Legacy": "skin_chance_legacy"}
SKIN_CHANCE_DEFAULT = {"Epic": 0.05, "Legendary": 0.20, "Mythic": 0.40, "Legacy": 0.70}
KATANA_CHANCE_KEY = {"Legendary": "katana_chance_leg", "Mythic": "katana_chance_myth", "Legacy": "katana_chance_legacy"}
KATANA_CHANCE_DEFAULT = {"Legendary": 0.06, "Mythic": 0.15, "Legacy": 0.35}
SKIN_RARITY_OF = {"Epic": "Epic", "Legendary": "Legendary", "Mythic": "Mythic", "Legacy": "Mythic"}

# themed wheels: (skin multiplier, katana multiplier). Blade wheels pay katanas more, outfit wheels pay skins more.
_BOOST_CAT = {"zanpakuto": (1.0, 2.0), "captains": (1.3, 1.5), "espada": (1.3, 1.5), "wande": (1.3, 1.5)}
_BOOST_WID = {"w_weapon": (1.0, 2.5), "w_cosmetic": (2.0, 1.0), "w_legacy": (1.5, 1.5), "w_ichigo": (1.5, 1.5),
              "w_yamamoto": (1.5, 1.5)}


def wheel_boost(wid: str, cat: str) -> tuple:
    return _BOOST_WID.get(wid) or _BOOST_CAT.get(cat) or (1.0, 1.0)
