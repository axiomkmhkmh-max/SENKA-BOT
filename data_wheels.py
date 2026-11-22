"""100 themed wheels (گردونه‌ها). Pure data + pure functions: no I/O, no Telegram, no DB.

Each wheel is spun with the Soul Core token (توکن هسته‌ی روح), which is very hard to get.
Spin cost grows with how many times a player has already spun THAT wheel:
    spins 1-10   -> base cost x1
    spins 11-40  -> base cost x2
    spins 41-90  -> base cost x4
    spins 91+    -> base cost x8
The most expensive wheel is Yamamoto (w_yamamoto), then Ichigo (w_ichigo). The Toshiro wheel is owner-only.
"""
import random

TOKEN = {"id": "soul_core", "icon": "🔮", "fa": "هسته‌ی روح", "en": "Soul Core"}

# Tier thresholds: (last spin number in this tier, multiplier). The last tier has no end.
COST_TIERS = [(10, 1), (40, 2), (90, 4), (None, 8)]

# Rarity outcomes of a spin. Weights do not need to sum to 100.
RARITY_WEIGHTS = {
    "Common": 45, "Rare": 25, "Epic": 14, "Legendary": 9, "Mythic": 3, "Legacy": 1,
}
RARITY_ICON = {"Common": "⬜", "Rare": "🟦", "Epic": "🟪", "Legendary": "🟧",
               "Mythic": "🟥", "Legacy": "🌌", "Soul Core": "🔮"}

# What each rarity gives. Top-tier results drop the wheel's own themed reward.
RARITY_REWARD = {
    "Common": ("🪙", "سکه‌ی کم", "Small coins"),
    "Rare": ("✨", "تجربه‌ی خوب", "Good XP"),
    "Epic": ("🎁", "صندوق ارزشمند", "Valuable crate"),
    "Legendary": ("🎯", "صندوق تم‌دار", "Themed crate"),
    "Mythic": ("💠", "گنجینه‌ی تم‌دار", "Themed treasure"),
    "Legacy": ("🌌", "آیتم بازنشسته‌ی تم‌دار", "Retired themed item"),
    "Soul Core": ("🔮", "یک هسته‌ی روح", "One Soul Core"),
}

# Base cost per spin (in Soul Cores) for each category.
CATEGORIES = {
    "captains": ("👑 کاپیتان‌ها", "👑 Captains", 14),
    "espada": ("🌑 اسپادا", "🌑 Espada", 18),
    "wande": ("✝️ وندن‌رایش", "✝️ Wandenreich", 16),
    "zanpakuto": ("⚔️ زنپاکتو", "⚔️ Zanpakutō", 12),
    "places": ("🗺️ مکان‌ها", "🗺️ Places", 8),
    "races": ("🧬 نژادها", "🧬 Races", 10),
    "events": ("🎉 رویدادی و ایرانی", "🎉 Events & Iranian", 6),
    "items": ("🎒 تخصصی آیتم", "🎒 Item specialist", 9),
    "economy": ("💰 اقتصادی", "💰 Economy", 20),
    "special": ("🌀 ویژه", "🌀 Special", 15),
}

# (id, icon, fa name, en name) per category. Exactly 10 per category.
_WHEEL_LIST = {
    "captains": [
        ("w_yamamoto", "🔥", "یاماموتو", "Yamamoto"),
        ("w_soifon", "🦋", "سوی‌فون", "Soi Fon"),
        ("w_unohana", "🌸", "یونوهانا", "Unohana"),
        ("w_kyoraku", "🍶", "کیوراکو", "Kyōraku"),
        ("w_ukitake", "❄️", "اوکیتاکه", "Ukitake"),
        ("w_byakuya", "🌹", "بیاکویا", "Byakuya"),
        ("w_zaraki", "🪓", "زاراکی", "Zaraki"),
        ("w_mayuri", "🧪", "مایوری", "Mayuri"),
        ("w_hitsugaya", "🧊", "توشیرو هیتسوگایا", "Toshiro Hitsugaya"),
        ("w_komamura", "🐺", "کومامورا", "Komamura"),
    ],
    "espada": [
        ("w_starrk", "🔫", "استارک", "Starrk"),
        ("w_barragan", "👑", "بارگان", "Baraggan"),
        ("w_harribel", "🌊", "هریبل", "Tia Harribel"),
        ("w_ulquiorra", "🕳️", "اولکیورا", "Ulquiorra"),
        ("w_nnoitra", "🗡️", "نوایترا", "Nnoitra"),
        ("w_grimmjow", "🐆", "گریمجو", "Grimmjow"),
        ("w_szayel", "🧬", "سایل‌آپورو", "Szayel Aporro"),
        ("w_aaroniero", "🌀", "آرونیرو", "Aaroniero"),
        ("w_zommari", "🦂", "زوماری", "Zommari"),
        ("w_yammy", "🦖", "یامی", "Yammy"),
    ],
    "wande": [
        ("w_yhwach", "🌕", "یوآخ", "Yhwach"),
        ("w_uryu", "🏹", "اوریو", "Uryū Ishida"),
        ("w_haschwalth", "🛡️", "هاشوالث", "Haschwalth"),
        ("w_jugram", "🪶", "یوگرام", "Jugram"),
        ("w_liltotto", "🎀", "لیلی‌توتو", "Liltotto"),
        ("w_askin", "🎭", "آسکین", "Askin"),
        ("w_gerard", "🛡", "جرارد", "Gerard"),
        ("w_bazzb", "🕶️", "بازبی", "Bazz-B"),
        ("w_candice", "🍬", "کندیس", "Candice"),
        ("w_bambietta", "🎈", "بمبیتا", "Bambietta"),
    ],
    "zanpakuto": [
        ("w_senbonzakura", "🌸", "سنبون‌زاکورا", "Senbonzakura"),
        ("w_zangetsu", "🌙", "زانگتسو", "Zangetsu"),
        ("w_ryujin", "🐉", "ریوجین جاکا", "Ryūjin Jakka"),
        ("w_hyorinmaru", "🐲", "هیورینمارو", "Hyōrinmaru"),
        ("w_kazeshini", "💨", "کازشینی", "Kazeshini"),
        ("w_benihime", "🩸", "بنی‌هیمه", "Benihime"),
        ("w_haineko", "🐈", "های‌نکو", "Haineko"),
        ("w_shinso", "👁️", "شینسو", "Shinsō"),
        ("w_kyokasuigetsu", "🌕", "کیوکا سویگتسو", "Kyōka Suigetsu"),
        ("w_tobiume", "🔥", "توبی‌مه", "Tobiume"),
    ],
    "places": [
        ("w_seireitei", "🏯", "سیرِیتِی", "Seireitei"),
        ("w_karakura", "🏙️", "کاراکورا", "Karakura Town"),
        ("w_hueco", "🏜️", "هوئکو موندو", "Hueco Mundo"),
        ("w_lasnoches", "🌃", "لاس‌نوچس", "Las Noches"),
        ("w_rukongai", "🏘️", "روکونگای", "Rukongai"),
        ("w_senzaikyu", "💴", "سنزایکیو", "Senzaikyū"),
        ("w_sokyoku", "⛰️", "تپه‌ی سوکیوکو", "Sōkyoku Hill"),
        ("w_soulking", "👑", "قصر شاه ارواح", "Soul King Palace"),
        ("w_urahara", "🧳", "مغازه‌ی اوراهارا", "Urahara Shop"),
        ("w_wandepalace", "🏰", "قصر وندن‌رایش", "Wandenreich Palace"),
    ],
    "races": [
        ("w_shinigami", "⚔️", "شینیگامی", "Shinigami"),
        ("w_quincy", "✝️", "کوئینسی", "Quincy"),
        ("w_hollow", "💀", "هالو", "Hollow"),
        ("w_arrancar", "🎭", "آرانکار", "Arrancar"),
        ("w_vizard", "🎭", "ویزورد", "Vizard"),
        ("w_fullbringer", "🧤", "فول‌برینگر", "Fullbringer"),
        ("w_human", "🧑", "انسان", "Human"),
        ("w_soul", "👻", "روح ساده", "Plain Soul"),
        ("w_menos", "🐉", "منوس", "Menos"),
        ("w_vastolorde", "🦴", "واستو لورد", "Vasto Lorde"),
    ],
    "events": [
        ("w_nowruz", "🌱", "نوروز", "Nowruz"),
        ("w_yalda", "🍉", "یلدا", "Yalda"),
        ("w_mehregan", "🍂", "مهرگان", "Mehregan"),
        ("w_chaharshanbe", "🔥", "چهارشنبه‌سوری", "Chaharshanbe Suri"),
        ("w_sizdah", "🌿", "سیزده‌به‌در", "Sizdah Bedar"),
        ("w_ramadan", "🌙", "رمضان", "Ramadan"),
        ("w_eidfitr", "🌟", "عید فطر", "Eid al-Fitr"),
        ("w_botbirthday", "🎂", "تولد ربات", "Bot Birthday"),
        ("w_seasonend", "🏁", "پایان فصل", "Season End"),
        ("w_blackfriday", "🛍️", "جمعه‌ی سیاه", "Black Friday"),
    ],
    "items": [
        ("w_weapon", "🗡️", "سلاح", "Weapon"),
        ("w_armor", "🛡️", "زره", "Armor"),
        ("w_relic", "🗿", "یادگار", "Relic"),
        ("w_pet", "🐾", "پت", "Pet"),
        ("w_cosmetic", "🎨", "کازمتیک", "Cosmetic"),
        ("w_material", "💎", "ماده‌ی کمیاب", "Rare Material"),
        ("w_book", "📘", "کتاب", "Book"),
        ("w_egg", "🥚", "تخم روح", "Spirit Egg"),
        ("w_key", "🔑", "کلید دانجن", "Dungeon Key"),
        ("w_potion", "🧪", "معجون", "Potion"),
    ],
    "economy": [
        ("w_bronze", "🥉", "برنز", "Bronze"),
        ("w_silver", "🥈", "نقره", "Silver"),
        ("w_gold", "🥇", "طلا", "Gold"),
        ("w_platinum", "💠", "پلاتین", "Platinum"),
        ("w_diamond", "💎", "الماس", "Diamond"),
        ("w_reishi", "🔹", "ریشی", "Reishi"),
        ("w_hogyoku", "🔮", "هوگیوکو", "Hōgyoku"),
        ("w_jackpot", "🎰", "جکپات", "Jackpot"),
        ("w_risky", "🎲", "ریسکی (دو برابر یا هیچی)", "Risky (double or nothing)"),
        ("w_lucky7", "7️⃣", "شانس ۷", "Lucky Seven"),
    ],
    "special": [
        ("w_mystery", "❔", "چرخ مرموز", "Mystery Wheel"),
        ("w_bosshunter", "🐉", "بوس‌کش", "Boss Hunter"),
        ("w_tower", "🗼", "برج", "Soul Tower"),
        ("w_dispatch", "🧭", "دیسپچ", "Dispatch"),
        ("w_seasonrank", "🏆", "رنک فصل", "Season Rank"),
        ("w_group", "👥", "گروهی", "Group Wheel"),
        ("w_cursed", "☠️", "نفرین‌شده", "Cursed Wheel"),
        ("w_noloss", "🛟", "بدون باخت", "No-Loss Wheel"),
        ("w_legacy", "🌌", "Legacy", "Legacy Wheel"),
        ("w_ichigo", "🟧", "ایچیگو", "Ichigo Kurosaki"),
    ],
}

# Per-wheel overrides. Yamamoto is now the most expensive (players asked: pricier than Ichigo). Toshiro's is owner-only.
COST_OVERRIDE = {"w_yamamoto": 75, "w_ichigo": 60, "w_hitsugaya": 25}
OWNER_ONLY = {"w_hitsugaya"}

# The "item specialist" wheels pay what their name says (a potion wheel pays potions, an egg wheel eggs ...).
# Before, every wheel paid the same generic materials / relics, so players never saw the item they spun for in the bag.
WHEEL_ITEM_CAT = {"w_relic": "relic", "w_material": "material", "w_potion": "potion", "w_egg": "egg",
                  "w_book": "book", "w_cosmetic": "cosmetic", "w_key": "key"}


def _build():
    out = {}
    for cat, items in _WHEEL_LIST.items():
        cat_fa, cat_en, base = CATEGORIES[cat]
        for wid, icon, fa, en in items:
            out[wid] = {
                "id": wid, "cat": cat, "icon": icon, "fa": fa, "en": en,
                "cat_fa": cat_fa, "cat_en": cat_en,
                "base_cost": COST_OVERRIDE.get(wid, base),
                "owner_only": wid in OWNER_ONLY,
            }
    return out


WHEELS = _build()
WHEEL_IDS = list(WHEELS)


def wheel_by_id(wid: str):
    return WHEELS.get(wid)


def spin_multiplier(spin_number: int) -> int:
    """spin_number is 1-based: how many spins of this wheel the player is making (this one included)."""
    if spin_number < 1:
        raise ValueError("spin_number starts at 1")
    for end, mult in COST_TIERS:
        if end is None or spin_number <= end:
            return mult
    return COST_TIERS[-1][1]


def spin_cost(wid: str, spin_number: int) -> int:
    """Soul Cores needed for the next spin of wheel `wid` when the player has already spun it `spin_number - 1` times."""
    return WHEELS[wid]["base_cost"] * spin_multiplier(spin_number)


def can_spin(wid: str, user_id: int, owner_id: int) -> bool:
    """Owner-only wheels (e.g. Toshiro) can be spun by the owner only."""
    w = WHEELS.get(wid)
    if w is None:
        return False
    if w["owner_only"] and user_id != owner_id:
        return False
    return True


def roll(rng: random.Random | None = None) -> str:
    """Pick a rarity for one spin. Pure except for the RNG, which tests can seed."""
    r = rng or random
    keys = list(RARITY_WEIGHTS)
    return r.choices(keys, [RARITY_WEIGHTS[k] for k in keys])[0]


def reward_for(rarity: str, wid: str) -> tuple:
    """(icon, fa, en) of what the spin gives. Top tiers use the wheel's own theme name."""
    w = WHEELS[wid]
    if rarity in ("Legendary", "Mythic", "Legacy"):
        return (RARITY_ICON[rarity], f"{w['fa']} ({RARITY_REWARD[rarity][1]})",
                f"{w['en']} ({RARITY_REWARD[rarity][2]})")
    icon, fa, en = RARITY_REWARD[rarity]
    return icon, fa, en


# ===================================================================================================
# Deeper system: pity (ضمانت), streaks and odds. Still pure: the RNG is passed in.
# ===================================================================================================
LEG_PLUS = ("Legendary", "Mythic", "Legacy")   # rarities that count as "Legendary or better"
MYTH_PLUS = ("Mythic", "Legacy")               # rarities that count as "Mythic or better"


def wheels_in(cat: str) -> list:
    """Wheel ids of one category, in display order."""
    return [wid for wid, _i, _f, _e in _WHEEL_LIST.get(cat, [])]


def resolve_rarity(rng, leg_streak: int, myth_streak: int, leg_at: int, myth_at: int) -> str:
    """Pick a spin's rarity, honouring pity.
    myth_streak >= myth_at: guaranteed Mythic or better (Mythic 3 : Legacy 1).
    leg_streak  >= leg_at : guaranteed Legendary or better (9 : 3 : 1).
    Otherwise the normal weights. A threshold of 0 disables that pity."""
    if myth_at > 0 and myth_streak >= myth_at:
        return rng.choices(["Mythic", "Legacy"], [3, 1])[0]
    if leg_at > 0 and leg_streak >= leg_at:
        return rng.choices(["Legendary", "Mythic", "Legacy"], [9, 3, 1])[0]
    return roll(rng)


def next_streaks(rarity: str, leg_streak: int, myth_streak: int) -> tuple:
    """Streak counters after a spin: a hit resets its counter, a miss adds one."""
    leg = 0 if rarity in LEG_PLUS else leg_streak + 1
    myth = 0 if rarity in MYTH_PLUS else myth_streak + 1
    return leg, myth


def odds_table() -> list:
    """[(rarity, percent)] for the normal (no pity) roll, highest tier last."""
    total = sum(RARITY_WEIGHTS.values())
    return [(k, RARITY_WEIGHTS[k] / total * 100) for k in RARITY_WEIGHTS]
