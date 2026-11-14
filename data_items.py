"""1000+ catalog items generated from themed name banks (original text)."""
from data_crafting import EVO_KINDS, MAT_GROUP, MAT_KINDS, book_effect, cosmetic_effect, relic_effect
from data_lore import ITEM_FLAVOR
from data_misc import KIDO_NAMES as KN
from data_races import DUNGEONS
from data_weapons import PRICE, RARITIES, WEAPONS

ADJ = [("Seireitei", "سیرایتی"), ("Rukongai", "روکونگای"), ("Hueco Mundo", "هوئکو موندو"), ("Garganta", "گارگانتا"),
       ("Gotei", "گوتی"), ("Quincy", "کوئینسی"), ("Karakura", "کاراکورا"), ("Dangai", "دنگای"), ("Vasto Lorde", "واستو لورد"),
       ("Gillian", "گیلیان"), ("Soul King", "شاه ارواح"), ("Senkaimon", "سنکایمون"), ("Las Noches", "لاس‌نوچس"),
       ("Wandenreich", "وندن‌رایش"), ("Fullbring", "فول‌برینگ"), ("Visored", "ویزورد")]
NOUNS = {
    "charm": [("Kon Plush Charm", "طلسم عروسک کن"), ("Kuchiki Ribbon Charm", "طلسم روبان کوچیکی"),
             ("Visored Mask Charm", "طلسم ماسک ویزورد"), ("Konpaku Tag Charm", "طلسم برچسب کونپاکو"),
             ("Urahara Hat Charm", "طلسم کلاه اوراهارا")],
    "material": [("Reishi Shard", "تکه‌ی ریشی"), ("Sekkiseki Chip", "تراشه‌ی سکی‌سکی"), ("Hollow Bone", "استخوان هالو"),
                 ("Spirit Thread", "نخ روحی"), ("Menos Fang", "نیش منوس"), ("Gigai Cloth", "پارچه‌ی گیگای"),
                 ("Mask Fragment", "پاره‌ی ماسک"), ("Spirit Ribbon", "نوار روحی"), ("Zanpakuto Ore", "سنگ‌معدن زانپاکتو"),
                 ("Reiatsu Dust", "غبار ریاتسو")],
    "potion": [("Soul Candy", "شیرینی روح"), ("Reiatsu Tonic", "نوشدارو ریاتسو"), ("Kidō Salve", "مرهم کیدو"),
               ("Sakura Tea", "چای شکوفه"), ("Urahara Elixir", "اکسیر اوراهارا")],
    "armor": [("Shihakushō", "شیهاکوشو"), ("Haori", "هائوری"), ("Quincy Vest", "جلیقه‌ی کوئینسی"), ("Hollow Plate", "زره‌ی هالو"),
              ("Espada Coat", "کت اسپادا"), ("Captain's Cloak", "شنل کاپیتان"), ("Hirenkyaku Wrap", "نوار هیرنکیاکو"),
              ("Fullbring Jacket", "ژاکت فول‌برینگ"), ("Gotei Sash", "کمربند گوتی"), ("Reishi Mantle", "عبای ریشی")],
    "ring": [("Seal Ring", "انگشتر مهر"), ("Reiatsu Band", "حلقه‌ی ریاتسو"), ("Vice-Captain Signet", "مهر معاون")],
    "necklace": [("Quincy Cross", "صلیب کوئینسی"), ("Spirit Pendant", "آویز روح"), ("Mask Amulet", "طلسم ماسک")],
    "scroll": [("Scroll", "طومار")],
    "book": [("Academy Manual", "راهنمای آکادمی"), ("Kidō Treatise", "رساله‌ی کیدو"), ("Captain's Journal", "خاطرات کاپیتان")],
    "evolution": [("Hōgyoku Fragment", "پاره‌ی هوگیوکو"), ("Vasto Core", "هسته‌ی واستو"), ("Ginto Sigil", "نشان گینتو")],
    "cosmetic": [("Moonlit Trail", "رد مهتابی"), ("Reiatsu Aura", "هاله‌ی ریاتسو"), ("Squad Banner", "پرچم جوخه"),
                 ("Hollow Mask Charm", "آویز ماسک هالو"), ("Sakura Petals", "گلبرگ‌های شکوفه")],
    "relic": [("Soul King Relic", "یادگار شاه ارواح"), ("Ancient Seal", "مهر باستانی"), ("Zanpakuto Idol", "تندیس زانپاکتو"),
              ("Reishi Idol", "تندیس ریشی")],
    "egg": [("Spirit Egg", "تخم روح")], "key": [("Key", "کلید")],
}
# category, count, slot, stack, base price factor
PLAN = [("material", 160, None, 99, 1.0), ("potion", 100, None, 99, 1.2), ("armor", 150, "armor", 1, 2.5),
        ("ring", 75, "accessory", 1, 3.0), ("necklace", 75, "accessory", 1, 3.0), ("kido_card", 198, None, 99, 2.0),
        ("book", 40, None, 99, 2.0), ("evolution", 30, None, 99, 3.0), ("cosmetic", 80, None, 1, 1.5),
        ("relic", 60, None, 1, 4.0), ("egg", 30, None, 99, 4.0), ("key", 120, None, 99, 2.0),
        ("charm", 30, None, 99, 2.0)]  # SENKA+: appended last so every older item id stays the same
KIDO_NAMES = {"had": ("Hadō", "هادو"), "bak": ("Bakudō", "باکودو")}
DUNGEON_IDS = ["trial", "hollow_den", "menos_forest", "noches_depths", "quincy_fort", "palace_trial", "dangai_rift",
               "academy_exam", "urahara_pit", "senzaikyu_tower", "maggot_nest", "muken",
               "clinic_nightwatch", "visored_gauntlet", "srdi_lab", "schatten_depths",
               "karakura_midnight", "captains_trial", "jigoku_pit", "hogyoku_vault",
               "riverbank_vigil", "bount_labyrinth", "precipice_run", "zero_trial"]
DIFFS = ["normal", "hard", "nightmare", "abyss", "legendary"]
assert dict((c[0], c[1]) for c in PLAN)["key"] == 5 * len(DUNGEON_IDS), "key count must match DUNGEON_IDS x difficulties"
STATS = ["zanjutsu", "kido", "hakuda", "hoho", "reiatsu"]


_STAT_EN = {"dmg": "damage", "def": "defense", "crit": "crit chance", "xp": "XP", "drop": "drop rate"}
_RSTAT_FA = {"zanjutsu": "زنجوتسو", "kido": "کیدو", "hakuda": "هاکودا", "hoho": "هوهو", "reiatsu": "ریاتسو"}
DIFF_FA = {"normal": "عادی", "hard": "سخت", "nightmare": "کابوس", "abyss": "ورطه", "legendary": "افسانه‌ای"}
# Persian spellings of the named Hadō / Bakudō spells, so Persian card names carry no Latin letters
KN_FA = {"Sai": "سای", "Hainawa": "هاینوا", "Geki": "گکی", "Shitotsu Sansen": "شیتوتسو سانسن", "Tsuribōshi": "تسوریبوشی",
         "Enkōsen": "انکوسن", "Rikujōkōrō": "ریکوجوکورو", "Hyapporankan": "هیاپورانکان", "Sajō Sabaku": "ساجو ساباکو",
         "Tozanshō": "توزانشو", "Danku": "دانکو", "Kin": "کین", "Shō": "شو", "Byakurai": "بیاکورای", "Shakkahō": "شاکاهو",
         "Sōkatsui": "سوکاتسوی", "Tenran": "تن‌ران", "Raikōhō": "رایکوهو", "Sōren Sōkatsui": "سورن سوکاتسوی",
         "Hiryūgekizoku Shinten Raihō": "هیریوگکیزوکو شینتن رایهو", "Kurohitsugi": "کوروهیتسوگی",
         "Tsuzuri Raiden": "تسوزوری رایدن", "Fushibi": "فوشیبی", "Ōkasen": "اوکاسن", "Haien": "هاین", "Senju Kōtenkan": "سنجو کوتنکان",
         "Ittō Kasō": "ایتو کاسو", "Sekienton": "سکیینتون", "Kyokkō": "کیوککو", "Kakushitsuijaku": "کاکوشیتسویجاکو", "Gochūtekkan": "گوچوتکان",
         "Seki": "سکی", "Tenteikūra": "تنتی‌کورا", "Zangeki": "زانگکی", "Daichi Tenyō": "دایچی تن‌یو"}
_STAT_FA = {"dmg": "آسیب", "def": "دفاع", "crit": "شانس کریتیکال", "xp": "تجربه", "drop": "نرخ دراپ"}


def _book_desc(e):
    t = e["type"]
    if t == "xp":
        return f"Grants {e['amount']} XP.", f"{e['amount']} تجربه می‌دهد."
    if t == "buff":
        p = f"{e['pct'] * 100:g}"
        return (f"+{p}% {_STAT_EN[e['stat']]} for {e['minutes']} min.", f"+{p}٪ {_STAT_FA[e['stat']]} تا {e['minutes']} دقیقه.")
    if t == "kido_book":
        b_en, b_fa = KIDO_NAMES[e["branch"]]
        return f"Teaches an unknown {b_en} (up to No. {e['cap']}).", f"یک {b_fa} ناشناخته می‌آموزد (تا شماره {e['cap']})."
    return f"+{e['amount']} bond with your blade.", f"+{e['amount']} پیوند با تیغه‌ات."


def _rarity(i, n):
    f = i / n
    return RARITIES[0 if f < .5 else 1 if f < .75 else 2 if f < .9 else 3 if f < .97 else 4 if f < .995 else 5]


# Portals, monster ranks and the like don't brew potions or sew armour: these place/faction words are skipped for
# those kinds of item so names stay believable. Only names change; item ids, stats and effects never do.
_NOT_FOR = {k: {"Garganta", "Dangai", "Senkaimon", "Gillian", "Vasto Lorde"} for k in ("potion", "armor", "ring", "necklace", "book")}
_ROMAN = ["", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]
_ROMAN_FA = ["", "۲", "۳", "۴", "۵", "۶", "۷", "۸", "۹", "۱۰", "۱۱", "۱۲"]  # Persian names never carry Latin numerals
_SEEN: set = set()


def _name(cat, i):
    nouns = NOUNS.get(cat, NOUNS["relic"])
    adjs = [x for x in ADJ if x[0] not in _NOT_FOR.get(cat, ())]
    A = len(adjs)
    a, n = i % A, (i // A) % len(nouns)
    tier = i // (A * len(nouns))
    for _ in range(A):  # no "Quincy Quincy Vest": skip an adjective whose first word is already in the noun
        if adjs[a][0].split()[0].lower() not in nouns[n][0].lower().split():
            break
        a = (a + 1) % A
    if cat not in NOUNS:  # kido cards etc. rename themselves later; they must not use up names
        return f"{adjs[a][0]} {nouns[n][0]}", f"{nouns[n][1]} {adjs[a][1]}"
    while True:
        k = min(tier, len(_ROMAN) - 1)
        suf = "" if tier == 0 else " " + _ROMAN[k]
        suf_fa = "" if tier == 0 else " " + _ROMAN_FA[k]
        en = f"{adjs[a][0]} {nouns[n][0]}{suf}"
        if en not in _SEEN or tier >= len(_ROMAN) - 1:
            break
        tier += 1
    _SEEN.add(en)
    return en, f"{nouns[n][1]} {adjs[a][1]}{suf_fa}"


def _build():
    out = []
    seq = 0
    for cat, count, slot, stack, fac in PLAN:
        for i in range(count):
            seq += 1
            iid = f"it_{seq:04d}"
            rar = _rarity(i, count)
            tier = RARITIES.index(rar)
            en, fa = _name(cat, i)
            eff, stats, desc_en, desc_fa = None, {}, "", ""
            if cat == "kido_card":
                branch = "had" if i < 99 else "bak"
                num = (i % 99) + 1
                sp = KN.get((branch, num))
                en = f"{KIDO_NAMES[branch][0]} {num}{': ' + sp if sp else ''} Card"
                fa = f"کارت {KIDO_NAMES[branch][1]} {num}{' (' + KN_FA[sp] + ')' if sp else ''}"
                rar = RARITIES[min(5, num // 20)]
                tier = RARITIES.index(rar)
                eff = {"type": "kido", "branch": branch, "num": num}
                desc_en, desc_fa = f"Teaches {KIDO_NAMES[branch][0]} {num}.", f"{KIDO_NAMES[branch][1]} شماره {num} را می‌آموزد."
            elif cat == "charm":  # SENKA+ charms: a timed battle buff, or a Konpaku life for duels
                if i % 2 == 0:
                    stat = ["dmg", "def", "crit"][(i // 2) % 3]
                    eff = {"type": "buff", "stat": stat, "pct": round((0.03 if stat == "crit" else 0.05) + 0.01 * tier, 3),
                           "minutes": 45 + 15 * tier}
                    desc_en, desc_fa = _book_desc(eff)
                else:
                    eff = {"type": "konpaku", "minutes": 60 + 30 * tier}
                    desc_en = f"Duel charm: one extra Konpaku life for {eff["minutes"]} minutes."
                    desc_fa = f"طلسم دوئل: یک جان کونپاکوی اضافه برای {eff["minutes"]} دقیقه."
            elif cat == "potion":
                if i % 2 == 0:
                    eff = {"type": "hp", "pct": 15 + tier * 10}
                    desc_en, desc_fa = f"Restores {eff['pct']}% HP.", f"{eff['pct']}٪ جان را بازمی‌گرداند."
                else:
                    eff = {"type": "reiatsu", "pct": 15 + tier * 10}
                    desc_en, desc_fa = f"Restores {eff['pct']}% reiatsu.", f"{eff['pct']}٪ ریاتسو را بازمی‌گرداند."
            elif cat == "book":
                eff = book_effect(i, tier)
                desc_en, desc_fa = _book_desc(eff)
            elif cat == "egg":
                eff = {"type": "pet", "tier": tier}
                desc_en, desc_fa = "Hatches a companion.", "یک همراه از آن بیرون می‌آید."
            elif cat == "key":
                d, df = DUNGEON_IDS[i // 5], DIFFS[i % 5]
                en, fa = f"{DUNGEONS[d]['en']} Key ({df})", f"کلید {DUNGEONS[d]['fa']} ({DIFF_FA[df]})"
                eff = {"type": "key", "dungeon": d, "diff": df}
                rar = RARITIES[min(5, 1 + i % 5)]
                tier = RARITIES.index(rar)
                desc_en, desc_fa = f"Opens {DUNGEONS[d]['en']} on {df} difficulty.", f"ورود به {DUNGEONS[d]['fa']} در سختی {DIFF_FA[df]}."
            elif cat == "armor":
                stats = {"def": 4 + tier * 9 + (i % 6) * 2}
                desc_en, desc_fa = f"+{stats['def']} defense.", f"+{stats['def']} دفاع."
            elif cat in ("ring", "necklace"):
                st = STATS[(i + (2 if cat == "necklace" else 0)) % 5]
                stats = {"stat": st, "bonus": 1 + tier * 2 + (i % 3)}
                if i % 7 == 0:
                    stats["luck"] = 1 + tier
                desc_en, desc_fa = f"+{stats['bonus']} {st}.", f"+{stats['bonus']} {_RSTAT_FA[st]}."
            elif cat == "material":
                kind = MAT_KINDS[(i // 16) % len(MAT_KINDS)]
                eff = {"type": "mat", "kind": kind, "group": MAT_GROUP[kind]}
                desc_en, desc_fa = "Crafting material.", "ماده‌ی ساخت."
            elif cat == "evolution":
                eff = {"type": "evo", "kind": EVO_KINDS[(i // 16) % len(EVO_KINDS)]}
                desc_en, desc_fa = "Fuel for evolution trials.", "سوخت آزمون‌های تکامل."
            elif cat == "relic":
                eff = relic_effect(i, tier)
                desc_en, desc_fa = "An old power that answers when attuned.", "قدرتی کهن که با هم‌سازی بیدار می‌شود."
            elif cat == "cosmetic":
                eff = cosmetic_effect(i, tier)
                desc_en, desc_fa = "Worn beside your name for the world to see.", "کنار نامت می‌درخشد تا جهان ببیند."
            else:
                desc_en, desc_fa = "A collectible keepsake.", "یک یادگاری کلکسیونی."
            fl = ITEM_FLAVOR.get(cat)
            if fl:
                f_fa, f_en = fl[i % len(fl)]
                desc_fa, desc_en = f"{desc_fa} {f_fa}".strip(), f"{desc_en} {f_en}".strip()
            base = int(PRICE[rar] * fac / 6 * (1 + (i % 7) / 10))
            out.append({"_id": iid, "item_id": iid, "category": "accessory" if cat in ("ring", "necklace") else cat,
                        "subtype": cat, "name_en": en, "name_fa": fa, "desc_en": desc_en, "desc_fa": desc_fa,
                        "rarity": rar, "stats": stats, "effect": eff, "slot": slot, "level_req": [1, 5, 15, 30, 50, 80][tier] if slot else 1,
                        "base_price": max(5, base), "sell_price": max(2, int(base * 0.4)),
                        "tradeable": rar != "Mythic" and cat != "key", "stack_max": stack})
    return out


ITEMS = _build()
# Curated Quincy items (Bleach). Appended after the generated catalog on purpose: inserting earlier would renumber
# every item id and break existing inventories. Category "quincy" keeps them out of random drop pools;
# Quincy raids hand them out directly (service_hollowraid.raid_settle).
CURATED = []
CURATED.append({"_id": "it_q001", "item_id": "it_q001", "category": "quincy", "subtype": "quincy", "name_en": "Yhwach's Eye", "name_fa": 'چشم یوهاباخ', "desc_en": 'The eye of the Almighty. For an hour, the first fatal blow of each battle leaves you standing with a sliver of life.', "desc_fa": 'چشم «Almighty». تا یک ساعت، اولین ضربه\u200cی کشنده\u200cی هر نبرد فقط تو را با یک تکه جان باقی می\u200cگذارد.', "rarity": "Mythic", "stats": {}, "effect": {"type": "almighty", "minutes": 60}, "slot": None, "level_req": 1, "base_price": 5000, "sell_price": 2000, "tradeable": False, "stack_max": 1})
CURATED.append({"_id": "it_q002", "item_id": "it_q002", "category": "quincy", "subtype": "quincy", "name_en": 'Blut Arterie', "name_fa": 'بلوت آرتری', "desc_en": 'Reishi sent through the blood vessels. Your strikes hit harder for an hour.', "desc_fa": 'ریشی که از رگ\u200cها عبور می\u200cکند. ضربه\u200cهایت یک ساعت سنگین\u200cتر می\u200cزنند.', "rarity": "Epic", "stats": {}, "effect": {"type": "buff", "stat": "dmg", "pct": 0.12, "minutes": 60}, "slot": None, "level_req": 1, "base_price": 1500, "sell_price": 600, "tradeable": True, "stack_max": 99})
CURATED.append({"_id": "it_q003", "item_id": "it_q003", "category": "quincy", "subtype": "quincy", "name_en": 'Blut Vene', "name_fa": 'بلوت وینه', "desc_en": 'Reishi that reinforces the body. You take less damage for an hour.', "desc_fa": 'ریشی که بدن را تقویت می\u200cکند. یک ساعت آسیب کمتری می\u200cبینی.', "rarity": "Epic", "stats": {}, "effect": {"type": "buff", "stat": "def", "pct": 0.12, "minutes": 60}, "slot": None, "level_req": 1, "base_price": 1500, "sell_price": 600, "tradeable": True, "stack_max": 99})
CURATED.append({"_id": "it_q004", "item_id": "it_q004", "category": "quincy", "subtype": "quincy", "name_en": 'Quincy Cross', "name_fa": 'صلیب کوئینسی', "desc_en": 'A cross that gathers spirit energy. Your critical hits land more often for an hour.', "desc_fa": 'صلیبی که انرژی روحی را جمع می\u200cکند. یک ساعت ضربه\u200cهای کاری\u200cات بیشتر می\u200cنشینند.', "rarity": "Rare", "stats": {}, "effect": {"type": "buff", "stat": "crit", "pct": 0.08, "minutes": 60}, "slot": None, "level_req": 1, "base_price": 600, "sell_price": 240, "tradeable": True, "stack_max": 99})
CURATED.append({"_id": "it_q005", "item_id": "it_q005", "category": "quincy", "subtype": "quincy", "name_en": 'Medallion', "name_fa": 'مدال', "desc_en": 'A medallion that pins down the strongest fighters. Critical chance is higher for an hour.', "desc_fa": 'مدالی که قوی\u200cترین رزمنده\u200cها را میخکوب می\u200cکند. یک ساعت شانس ضربهٔ کاری بالاتره.', "rarity": "Legendary", "stats": {}, "effect": {"type": "buff", "stat": "crit", "pct": 0.10, "minutes": 60}, "slot": None, "level_req": 1, "base_price": 4000, "sell_price": 1600, "tradeable": True, "stack_max": 99})
CURATED.append({"_id": "it_q006", "item_id": "it_q006", "category": "quincy", "subtype": "quincy", "name_en": 'Heilig Bogen', "name_fa": 'هایلیگ بوگن', "desc_en": "The Quincy bow. For half an hour your strikes carry a bow's force.", "desc_fa": 'کمان کوئینسی. نیم ساعت ضربه\u200cهایت قدرت کمان را دارند.', "rarity": "Rare", "stats": {}, "effect": {"type": "buff", "stat": "dmg", "pct": 0.15, "minutes": 30}, "slot": None, "level_req": 1, "base_price": 600, "sell_price": 240, "tradeable": True, "stack_max": 99})
CURATED.append({"_id": "it_q007", "item_id": "it_q007", "category": "quincy", "subtype": "quincy", "name_en": 'Reishi Sword', "name_fa": 'شمشیر ریشی', "desc_en": 'A sword made of hardened reishi. Your strikes hit a little harder for an hour.', "desc_fa": 'شمشیری از ریشی سخت\u200cشده. یک ساعت ضربه\u200cهایت کمی قوی\u200cتر می\u200cزنند.', "rarity": "Uncommon", "stats": {}, "effect": {"type": "buff", "stat": "dmg", "pct": 0.10, "minutes": 60}, "slot": None, "level_req": 1, "base_price": 300, "sell_price": 120, "tradeable": True, "stack_max": 99})
CURATED.append({"_id": "it_q008", "item_id": "it_q008", "category": "quincy", "subtype": "quincy", "name_en": 'Ginjo', "name_fa": 'گینجو', "desc_en": 'A reishi guard. You take less damage for an hour.', "desc_fa": 'سپر ریشی. یک ساعت آسیب کمتری می\u200cبینی.', "rarity": "Uncommon", "stats": {}, "effect": {"type": "buff", "stat": "def", "pct": 0.10, "minutes": 60}, "slot": None, "level_req": 1, "base_price": 300, "sell_price": 120, "tradeable": True, "stack_max": 99})
CURATED.append({"_id": "it_q009", "item_id": "it_q009", "category": "quincy", "subtype": "quincy", "name_en": 'Seele Schneider', "name_fa": 'زیله اشنایدر', "desc_en": 'A blade that cuts through the soul. Critical chance is higher for 45 minutes.', "desc_fa": 'تیغی که روح را می\u200cبرد. ۴۵ دقیقه شانس ضربهٔ کاری بالاتره.', "rarity": "Epic", "stats": {}, "effect": {"type": "buff", "stat": "crit", "pct": 0.12, "minutes": 45}, "slot": None, "level_req": 1, "base_price": 1500, "sell_price": 600, "tradeable": True, "stack_max": 99})
CURATED.append({"_id": "it_q010", "item_id": "it_q010", "category": "quincy", "subtype": "quincy", "name_en": 'Auswahlen', "name_fa": 'آوسوالن', "desc_en": "The Quincy's selection of power. Your strikes hit harder for 45 minutes.", "desc_fa": 'انتخاب قدرت کوئینسی. ۴۵ دقیقه ضربه\u200cهایت قوی\u200cتر می\u200cزنند.', "rarity": "Epic", "stats": {}, "effect": {"type": "buff", "stat": "dmg", "pct": 0.10, "minutes": 45}, "slot": None, "level_req": 1, "base_price": 1500, "sell_price": 600, "tradeable": True, "stack_max": 99})
CURATED.append({"_id": "it_q011", "item_id": "it_q011", "category": "quincy", "subtype": "quincy", "name_en": 'Kraft', "name_fa": 'کرافت', "desc_en": 'Quincy power held in the body. You take less damage for 45 minutes.', "desc_fa": 'قدرت کوئینسی که در بدن نگه داشته می\u200cشود. ۴۵ دقیقه آسیب کمتری می\u200cبینی.', "rarity": "Rare", "stats": {}, "effect": {"type": "buff", "stat": "def", "pct": 0.12, "minutes": 45}, "slot": None, "level_req": 1, "base_price": 600, "sell_price": 240, "tradeable": True, "stack_max": 99})
CURATED.append({"_id": "it_q012", "item_id": "it_q012", "category": "quincy", "subtype": "quincy", "name_en": 'Soul Distribution', "name_fa": 'توزیع روح', "desc_en": 'Part of a soul shared with you. You take less damage for 90 minutes.', "desc_fa": 'بخشی از یک روح که با تو تقسیم شده. ۹۰ دقیقه آسیب کمتری می\u200cبینی.', "rarity": "Epic", "stats": {}, "effect": {"type": "buff", "stat": "def", "pct": 0.08, "minutes": 90}, "slot": None, "level_req": 1, "base_price": 1500, "sell_price": 600, "tradeable": True, "stack_max": 99})
CURATED.append({"_id": "it_q013", "item_id": "it_q013", "category": "quincy", "subtype": "quincy", "name_en": 'Antithesis', "name_fa": 'آنتی\u200cتزیس', "desc_en": 'The Schrift of opposition. Your strikes hit harder for an hour.', "desc_fa": 'شرفت تضاد. یک ساعت ضربه\u200cهایت قوی\u200cتر می\u200cزنند.', "rarity": "Legendary", "stats": {}, "effect": {"type": "buff", "stat": "dmg", "pct": 0.10, "minutes": 60}, "slot": None, "level_req": 1, "base_price": 4000, "sell_price": 1600, "tradeable": True, "stack_max": 99})
CURATED.append({"_id": "it_q014", "item_id": "it_q014", "category": "quincy", "subtype": "quincy", "name_en": 'Balance', "name_fa": 'بالانس', "desc_en": 'The Schrift of balance. You take less damage for an hour.', "desc_fa": 'شرفت تعادل. یک ساعت آسیب کمتری می\u200cبینی.', "rarity": "Legendary", "stats": {}, "effect": {"type": "buff", "stat": "def", "pct": 0.08, "minutes": 60}, "slot": None, "level_req": 1, "base_price": 4000, "sell_price": 1600, "tradeable": True, "stack_max": 99})
CURATED.append({"_id": "it_q015", "item_id": "it_q015", "category": "quincy", "subtype": "quincy", "name_en": 'Fear', "name_fa": 'فیر', "desc_en": 'The Schrift of fear. Critical chance is higher for an hour.', "desc_fa": 'شرفت ترس. یک ساعت شانس ضربهٔ کاری بالاتره.', "rarity": "Legendary", "stats": {}, "effect": {"type": "buff", "stat": "crit", "pct": 0.10, "minutes": 60}, "slot": None, "level_req": 1, "base_price": 4000, "sell_price": 1600, "tradeable": True, "stack_max": 99})
CURATED.append({"_id": "it_q016", "item_id": "it_q016", "category": "quincy", "subtype": "quincy", "name_en": 'Vollständig', "name_fa": 'ولشتندیگ', "desc_en": 'The full Quincy transformation. A short, violent surge of strength.', "desc_fa": 'تبدیل کامل کوئینسی. یک افزایش قدرت کوتاه و شدید.', "rarity": "Mythic", "stats": {}, "effect": {"type": "buff", "stat": "dmg", "pct": 0.20, "minutes": 15}, "slot": None, "level_req": 1, "base_price": 5000, "sell_price": 2000, "tradeable": True, "stack_max": 99})
CURATED.append({"_id": "it_q017", "item_id": "it_q017", "category": "quincy", "subtype": "quincy",
                "name_en": "Zanpakuto Rebirth Seal", "name_fa": "مهر بازآفرینی زانپاکتو",
                "desc_en": "Use it with the blade you want equipped. Your zanpakuto is reborn as that blade: bond, mastery, Shikai and Bankai start over.",
                "desc_fa": "با تیغه‌ای که می‌خواهی زانپاکتوت شود، استفاده‌اش کن. زانپاکتو با آن تیغه از نو متولد می‌شود: پیوند، مستری، شیکای و بانکای از صفر شروع می‌شوند.",
                "rarity": "Legendary", "stats": {}, "effect": {"type": "znp_reset"}, "slot": None, "level_req": 1,
                "base_price": 8000, "sell_price": 3000, "tradeable": True, "stack_max": 99})
ITEMS += CURATED
QUINCY_DROPS = [x["_id"] for x in CURATED if x["_id"] not in ("it_q001", "it_q017")]  # raids: no eye, no seal
ALL = {x["_id"]: x for x in ITEMS}
for _w in WEAPONS:
    _w.setdefault("sell_price", max(2, int(_w["base_price"] * 0.4)))
    ALL[_w["_id"]] = _w
EVO_BY_RARITY = {r: [x["_id"] for x in ITEMS if x["rarity"] == r and x["category"] == "evolution"] for r in RARITIES}
COSMETIC_BY_RARITY = {r: [x["_id"] for x in ITEMS if x["rarity"] == r and x["category"] == "cosmetic"] for r in RARITIES}
BY_RARITY = {r: [x["_id"] for x in ITEMS if x["rarity"] == r and x["category"] in ("material", "potion", "armor", "accessory", "book", "egg", "relic")] for r in RARITIES}
WEAPON_BY_RARITY = {r: [w["_id"] for w in WEAPONS if w["rarity"] == r] for r in RARITIES}


def iname(item_id: str, lang: str) -> str:
    x = ALL.get(item_id)
    return item_id if not x else x["name_fa" if lang == "fa" else "name_en"]
