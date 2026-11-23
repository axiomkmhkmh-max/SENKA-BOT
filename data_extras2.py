"""Second batch of player ideas (Nov 19): new items, adventures, level bosses, the roll shop, mini-bosses, the summon
jackpot, companion upgrades and new spirits, Inner World 2, the tempering stone and the elite shop. Pure data.
"""

RARITIES = ["Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythic"]

# ---- new single items ---------------------------------------------------------------------------------------------------
TEMPER_STONE = "it_t001"   # needed for forge levels +6..+10 and armour tempering +6..+10 (rare)
INNER_KEY = "it_k001"      # opens Inner World 2 (very rare, like a Soul Core)


def _item(iid, cat, rar, en, fa, d_en, d_fa, price, eff=None, stack=999, tradeable=True):
    return {"_id": iid, "item_id": iid, "category": cat, "subtype": cat, "name_en": en, "name_fa": fa, "desc_en": d_en,
            "desc_fa": d_fa, "rarity": rar, "stats": {}, "effect": eff, "slot": None, "level_req": 1, "base_price": price,
            "sell_price": int(price * 0.4), "tradeable": tradeable, "stack_max": stack}


NEW_ITEMS = [
    _item(TEMPER_STONE, "temper", "Epic", "Tempering Stone", "سنگ آبدیده‌سازی",
          "Forged in Ōetsu's fire. Needed to forge a weapon or temper armour past +5.",
          "در آتش اوئتسو ساخته شده. برای فورج سلاح یا آبدیده کردن زره بعد از +۵ لازم است.", 9000),
    _item(INNER_KEY, "inner_key", "Legendary", "Inner World Key", "کلید دنیای درون",
          "A key to the deepest layer of your soul. Opens Inner World 2 once.",
          "کلید عمیق‌ترین لایه‌ی روحت. یک بار دنیای درون ۲ را باز می‌کند.", 40000, eff={"type": "inner_key"}, tradeable=False),
]

# ---- new relics (kinds the old ones never had: damage, defence, crit, regeneration, XP, hunting) -----------------------
_RV = {"dmg": [0.01, 0.015, 0.02, 0.03, 0.045], "def": [0.01, 0.015, 0.02, 0.03, 0.045], "crit": [0.004, 0.006, 0.009, 0.013, 0.02],
       "regen": [0.002, 0.003, 0.004, 0.006, 0.009], "xp": [0.03, 0.045, 0.06, 0.08, 0.11], "hunt": [0.03, 0.045, 0.06, 0.08, 0.11],
       "drop": [0.04, 0.06, 0.08, 0.10, 0.13]}   # luck: the item-drop chance (Epic 10%, so Legendary 13%)
_R = {"C": 0, "U": 1, "R": 2, "E": 3, "L": 4}
_RELICS = [
    ("Shiba Kūkaku's Fireworks Tube", "لوله‌ی آتش‌بازی کوکاکو", "U", "dmg"), ("Kōtotsu's Wake", "رد پاک‌کننده", "R", "def"),
    ("Kisuke's Benihime Sketch", "طرح بنی‌هیمه‌ی کیسوکه", "R", "crit"), ("Unohana's Healing Salve", "مرهم یونوهانا", "E", "regen"),
    ("Shinō Academy Diploma", "دیپلم آکادمی شینو", "C", "xp"), ("Hollow Hunter's Ledger", "دفتر شکارچی هالو", "U", "hunt"),
    ("Zangetsu's Black Moon", "ماه سیاه زانگتسو", "L", "dmg"), ("Hierro Skin Scrap", "تکه‌ی پوست هیرو", "E", "def"),
    ("Suzumebachi's Sting", "نیش سوزومه‌باچی", "E", "crit"), ("Hachi's Regeneration Seal", "مهر ترمیم هاچی", "R", "regen"),
    ("Captain's Logbook", "دفترچه‌ی کاپیتان", "E", "xp"), ("Fourth Seat's Hunting Map", "نقشه‌ی شکار افسر چهارم", "R", "hunt"),
    ("Ryūjin Jakka Cinder", "خاکستر ریوجین جاکا", "L", "dmg"), ("Bakudō 81 Dankū Wall", "دیوار دانکو", "L", "def"),
    ("Kenpachi's Notched Blade", "تیغه‌ی دندانه‌دار کنپاچی", "L", "crit"), ("Orihime's Sōten Kisshun Petal", "گلبرگ سوتن کیشون", "L", "regen"),
    ("Hōgyoku Researcher Notes", "یادداشت‌های پژوهش هوگیوکو", "L", "xp"), ("Grand Fisher Trophy", "غنیمت گرند فیشر", "U", "hunt"),
    ("Rukongai Brawler's Knuckle", "مشت‌آهنی دعواگر روکونگای", "C", "dmg"), ("Gotei Training Shield", "سپر تمرینی گوتی", "C", "def"),
    ("Lucky Hell Butterfly", "پروانه‌ی جهنمی خوش‌شانس", "C", "crit"), ("Fourth Division Herb", "گیاه دارویی گروهان چهار", "C", "regen"),
    ("Menos Hunter Badge", "نشان شکارچی منوس", "E", "hunt"), ("Espada Rank Plate", "پلاک رتبه‌ی اسپادا", "R", "dmg"),
    ("Blut Vene Vial", "شیشه‌ی بلوت وینه", "R", "def"), ("Quincy Arrow Fletching", "پر پیکان کوئینسی", "U", "crit"),
    ("Mask of Rage", "ماسک خشم", "U", "dmg"), ("Shihōin Shield Crest", "تاج سپر شیهوئین", "U", "def"),
    ("Gotei Archive Scroll", "طومار بایگانی گوتی", "U", "xp"), ("Visored Training Dummy", "آدمک تمرین ویزوردها", "R", "xp"),
    ("Arrancar Hunt Horn", "شیپور شکار آرانکار", "L", "hunt"), ("Senbonzakura Petal Jar", "شیشه‌ی گلبرگ سنبون‌زاکورا", "E", "dmg"),
    ("Kuchiki Clan Crest Plate", "پلاک نشان خاندان کوچیکی", "E", "def"), ("Yoruichi's Flash Cloth", "پارچه‌ی شونپوی یوروئیچی", "R", "crit"),
    ("Isane's Field Kit", "کیف صحرایی ایسانه", "U", "regen"), ("Seireitei Bulletin", "خبرنامه‌ی سیرِیتِی", "R", "xp"),
    ("Las Noches Patrol Map", "نقشه‌ی گشت لاس‌نوچس", "E", "hunt"), ("Nnoitra's Battle Scar", "زخم نبرد نوایترا", "E", "crit"),
    ("Tessai's Barrier Pin", "سنجاق سدّ تسای", "E", "regen"), ("Urahara's Training Ground Rock", "سنگ زمین تمرین اوراهارا", "C", "hunt"),
    ("Urahara's Striped Hat", "کلاه راه‌راه اوراهارا", "L", "drop"),   # the first Legendary luck relic (appended last: ids never move)
]
NEW_RELICS = []
for _n, (_en, _fa, _c, _k) in enumerate(_RELICS, 1):
    _v = _RV[_k][_R[_c]]
    NEW_RELICS.append(_item(f"it_r{_n:03d}", "relic", RARITIES[_R[_c]], _en, _fa,
                            "An old power that answers when attuned.", "قدرتی کهن که با هم‌سازی بیدار می‌شود.",
                            [120, 400, 1500, 5000, 22000][_R[_c]], eff={"type": "relic", "kind": _k, "loc": None, "v": _v}, stack=99))

# ---- mini-boss: a rare stronger foe in a normal battle ------------------------------------------------------------------
BOSS_XP_BONUS = 1.2             # +20% XP on every boss kind (world boss, level boss, mini-boss, raid incursions)
MINI_BOSS_CHANCE = 0.02
MINI_BOSS_SCALE = 2.0
MINI_BOSS_REWARD = 3.0          # XP and coins x3
MINI_BOSS_RELIC = 0.10          # chance of an evolution relic
MINI_BOSS_NAMES = [("منوس گرانده", "Menos Grande"), ("آجوکاس سرگردان", "Wandering Adjuchas"), ("آرانکار فراری", "Rogue Arrancar"),
                   ("اشترن‌ریتر گمشده", "Lost Sternritter"), ("شینیگامی خائن", "Traitor Shinigami"), ("بانت گرسنه", "Starving Bount"),
                   ("هالوی شکارچی", "Hunter Hollow"), ("سایه‌ی وندن‌رایش", "Wandenreich Shade")]

# ---- summon jackpot ------------------------------------------------------------------------------------------------------
SUMMON_JACKPOT = 1 / 10000      # per summon roll
SUMMON_JACKPOT_COINS = 500000

# ---- adventures (daily, multi-stage, coins and XP) ------------------------------------------------------------------------
ADV_DAILY = 5
ADVENTURES = {
    "menos_forest": {"fa": "جنگل منوس (هوئکو موندو)", "en": "Forest of Menos (Hueco Mundo)", "level": 1, "stages": 3,
                     "foes": [("هالوی جنگلی", "Forest Hollow"), ("گیلیان جوان", "Young Gillian"), ("آجوکاس", "Adjuchas")],
                     "boss": ("ملکه‌ی جنگل منوس", "Queen of the Menos Forest")},
    "rukongai_outskirts": {"fa": "حومه‌ی روکونگای", "en": "Rukongai Outskirts", "level": 1, "stages": 3,
                           "foes": [("راهزن روکونگای", "Rukongai Bandit"), ("هالوی سرگردان", "Stray Hollow"), ("روح شرور", "Wicked Soul")],
                           "boss": ("رئیس راهزن‌های زاراکی", "Zaraki Bandit Chief")},
    "quincy_ruins": {"fa": "ویرانه‌های کوئینسی", "en": "Quincy Ruins", "level": 20, "stages": 4,
                     "foes": [("سرباز یاگدآرمه", "Jagdarmee Soldier"), ("شبح کوئینسی", "Quincy Phantom"), ("نگهبان سایه", "Shadow Warden")],
                     "boss": ("اشترن‌ریتر نگهبان", "Guardian Sternritter")},
    "las_noches": {"fa": "دالان‌های لاس‌نوچس", "en": "Halls of Las Noches", "level": 35, "stages": 4,
                   "foes": [("نومروس", "Números"), ("فراسیون", "Fracción"), ("اکسکیاس", "Exequias")],
                   "boss": ("پریوارون اسپادا", "Privaron Espada")},
    "dangai": {"fa": "دنگای", "en": "The Dangai", "level": 50, "stages": 5,
               "foes": [("جریان دنگای", "Dangai Current"), ("هالوی دنگای", "Dangai Hollow"), ("سایه‌ی کوتوتسو", "Kōtotsu Shadow")],
               "boss": ("کوتوتسو", "Kōtotsu, the Cleaner")},
    "wandenreich": {"fa": "شهر سایه‌ی وندن‌رایش", "en": "Wandenreich Shadow City", "level": 70, "stages": 5,
                    "foes": [("سرباز شوتس‌اشتافل", "Schutzstaffel Soldier"), ("اشترن‌ریتر", "Sternritter"), ("شبح زیلبرن", "Silbern Phantom")],
                    "boss": ("گارد سلطنتی یوهاباخ", "Yhwach's Royal Guard")},
}
ADV_COIN_K = 1.6                # coins per stage x the normal reward
ADV_XP_K = 1.3
ADV_FINISH_COINS = 600          # finish purse: x (1 + level / 10)

# ---- level-band bosses (separate from the world boss; only players of the band can fight them, once a day) ---------------
LEVEL_BOSSES = [  # (min level, max level, boss fa, boss en, item colour, sig race)
    (1, 20, "گرند فیشر", "Grand Fisher", 1, "hollow"),
    (21, 40, "منوس گرانده‌ی سیاه", "Black Menos Grande", 2, "hollow"),
    (41, 60, "گریمجو (رسورکسیون)", "Grimmjow (Resurrección)", 3, "arrancar"),
    (61, 80, "اولکیورا (سگوندا اتاپا)", "Ulquiorra (Segunda Etapa)", 4, "arrancar"),
    (81, 100, "آیزن (تکامل هوگیوکو)", "Aizen (Hōgyoku Evolution)", 4, "shinigami"),
    (101, 9999, "یوهاباخ", "Yhwach", 5, "quincy"),
]
LEVEL_BOSS_SCALE = 2.6
LEVEL_BOSS_REWARD = 4.0
LEVEL_BOSS_RELIC = 0.25
LEVEL_BOSS_STONE = 0.20
LEVEL_BOSS_KEY = 0.02
LEVEL_BOSS_MYTHIC = 0.03        # red accessory, top band only


def level_band(level: int):
    for i, b in enumerate(LEVEL_BOSSES):
        if b[0] <= level <= b[1]:
            return i
    return len(LEVEL_BOSSES) - 1


# ---- the roll shop (coins only) --------------------------------------------------------------------------------------------
ROLL_COST = 3000
ROLL_TEN_COST = 27000           # ten rolls for the price of nine
ROLL_JACKPOT_EVERY = 100        # every 100th roll is a guaranteed jackpot
ROLL_WEIGHTS = {"Epic": 96, "Legendary": 4}   # Kidō/race cards and spirit eggs: Epic and up only, Legendary is rare, no Mythic from rolls
ROLL_DAILY_LIMIT = 2             # rolls a player may open per day (the x10 button is gone: it cannot fit this limit)
ROLL_EGG_SHARE = 0.35            # the rest are cards (Kidō cards for Shinigami/Visored, technique cards for others)

# ---- companions: new spirits and upgrades -----------------------------------------------------------------------------------
NEW_PETS = [("Hell Butterfly", "پروانه‌ی جهنمی"), ("Chappy the Rabbit", "خرگوش چپی"), ("Black Cat of Shihōin", "گربه‌ی سیاه شیهوئین"),
            ("Menos Pup", "توله‌ی منوس"), ("Gorō the White Dog", "گورو، سگ سفید"), ("Bonnie the Boar", "بانی، گراز"),
            ("Pesche's Bug", "حشره‌ی پشه"), ("Bawabawa Hatchling", "جوجه‌ی باواباوا"), ("Kon Plush Spirit", "روح عروسکی کن"),
            ("Ruri'iro Peacock", "طاووس روری‌ایرو")]
PET_MAX_TIER = 9                # ★10
PET_UP_COINS = 1000             # x (tier + 1)^2 (was 2500)
PET_UP_MATS = 1                 # spirit materials x (tier + 1), colour min(tier, 3) (was 2)

# ---- Inner World 2 (permanent pure bonuses, opened with the Inner World Key) -----------------------------------------------
INNER2 = {  # path: (fa, en, bonus key, step, cap)
    "hollow": ("رویارویی با هالوی درون", "Face the inner Hollow", "dmg", 0.005, 0.05),
    "zen": ("مراقبه‌ی ذن", "Zen meditation", "def", 0.005, 0.05),
    "breath": ("تنفس ریشی (یوگا)", "Reishi breathing (yoga)", "regen", 0.0008, 0.008),
    "mirror": ("آینه‌ی روح", "Mirror of the soul", "xp", 0.01, 0.10),
}

# ---- elite shop (players from level 50; Epic and up; more stock past level 100) ---------------------------------------------
ELITE_MIN_LEVEL = 50
ELITE_PRICE_K = 1.6
ELITE_STOCK = 12
ELITE_STOCK_100 = 20
