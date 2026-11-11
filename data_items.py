"""1000+ catalog items generated from themed name banks (original text)."""
from data_lore import ITEM_FLAVOR
from data_misc import KIDO_NAMES as KN
from data_races import DUNGEONS, LOCATIONS
from data_weapons import PRICE, RARITIES, WEAPONS

ADJ = [("Seireitei", "سیرایتی"), ("Rukongai", "روکونگای"), ("Hueco Mundo", "هوئکو موندو"), ("Garganta", "گارگانتا"),
       ("Gotei", "گوتی"), ("Quincy", "کوئینسی"), ("Karakura", "کاراکورا"), ("Dangai", "دنگای"), ("Vasto Lorde", "واستو لورد"),
       ("Gillian", "گیلیان"), ("Soul King", "شاه ارواح"), ("Senkaimon", "سنکایمون"), ("Las Noches", "لاس‌نوچس"),
       ("Wandenreich", "وندن‌رایش"), ("Fullbring", "فول‌برینگ"), ("Visored", "ویزورد")]
NOUNS = {
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
        ("relic", 60, None, 1, 4.0), ("egg", 30, None, 99, 4.0), ("key", 35, None, 99, 2.0)]
# material noun -> crafting tag (see data_crafting)
MAT_TAGS = ["reishi", "sekki", "bone", "thread", "fang", "cloth", "mask", "ribbon", "ore", "dust"]
RELIC_PCT = [1, 1.5, 2, 3, 4, 5]          # global relic bonus by rarity tier (%)
RELIC_LOC_PCT = [3, 4, 6, 8, 10, 12]      # location-bound XP bonus by rarity tier (%)
RELIC_KINDS = ["xp_loc", "xp_pct", "coin_pct", "drop_pct"]
COSM_NOUNS = [("trail", "🌙"), ("aura", "✨"), ("banner", "🚩"), ("aura", "🎭"), ("trail", "🌸")]
EVO_RACES = ["shinigami", "quincy", "hollow", "arrancar", "fullbringer", "human", "visored"]
EVO_MAX_STAGE = {"shinigami": 4, "quincy": 3, "hollow": 4, "arrancar": 3, "fullbringer": 2, "human": 2, "visored": 2}
PET_ROLES = ["fang", "heal", "luck"]
KIDO_NAMES = {"had": ("Hadō", "هادو"), "bak": ("Bakudō", "باکودو")}
DUNGEON_IDS = ["trial", "hollow_den", "menos_forest", "noches_depths", "quincy_fort", "palace_trial", "dangai_rift"]
DIFFS = ["normal", "hard", "nightmare", "abyss", "legendary"]
STATS = ["zanjutsu", "kido", "hakuda", "hoho", "reiatsu"]


def nouns_of(cat):
    return NOUNS.get(cat, NOUNS["relic"])


# evolution items: 20 race-specific (every stage of every race) + 10 universal
_EVO_SLOTS = [(r, st) for r in EVO_RACES for st in range(1, EVO_MAX_STAGE[r] + 1)]
_LOC_IDS = list(LOCATIONS)


def _rarity(i, n):
    f = i / n
    return RARITIES[0 if f < .5 else 1 if f < .75 else 2 if f < .9 else 3 if f < .97 else 4 if f < .995 else 5]


def _name(cat, i):
    nouns = NOUNS.get(cat, NOUNS["relic"])
    a, n = i % len(ADJ), (i // len(ADJ)) % len(nouns)
    if cat == "material":   # noun cycles fastest so every material type exists at every rarity
        a, n = (i // len(nouns)) % len(ADJ), i % len(nouns)
    tier = i // (len(ADJ) * len(nouns))
    suf = "" if tier == 0 else " " + ["", "II", "III", "IV", "V", "VI"][min(tier, 5)]
    return f"{ADJ[a][0]} {nouns[n][0]}{suf}", f"{nouns[n][1]} {ADJ[a][1]}{suf}"


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
                fa = f"کارت {KIDO_NAMES[branch][1]} {num}{' (' + sp + ')' if sp else ''}"
                rar = RARITIES[min(5, num // 20)]
                tier = RARITIES.index(rar)
                eff = {"type": "kido", "branch": branch, "num": num}
                desc_en, desc_fa = f"Teaches {KIDO_NAMES[branch][0]} {num}.", f"{KIDO_NAMES[branch][1]} شماره {num} را می‌آموزد."
            elif cat == "potion":
                if i % 2 == 0:
                    eff = {"type": "hp", "pct": 15 + tier * 10}
                    desc_en, desc_fa = f"Restores {eff['pct']}% HP.", f"{eff['pct']}٪ HP را بازمی‌گرداند."
                else:
                    eff = {"type": "reiatsu", "pct": 15 + tier * 10}
                    desc_en, desc_fa = f"Restores {eff['pct']}% reiatsu.", f"{eff['pct']}٪ ریاتسو را بازمی‌گرداند."
            elif cat == "book":
                kind = i % 3
                if kind == 0:
                    eff = {"type": "xp", "amount": 150 * (tier + 1) ** 2}
                    desc_en, desc_fa = f"Grants {eff['amount']} XP.", f"{eff['amount']} XP می‌دهد."
                elif kind == 1:
                    br = "had" if (i // 3) % 2 == 0 else "bak"
                    num = min(99, 4 + tier * 15 + (i // 6) % 9)
                    eff = {"type": "tome", "kind": "kido", "branch": br, "num": num}
                    desc_en, desc_fa = f"Teaches {KIDO_NAMES[br][0]} {num}.", f"{KIDO_NAMES[br][1]} شماره {num} را می‌آموزد."
                else:
                    key = ["xp_pct", "coin_pct", "drop_pct"][(i // 3) % 3]
                    eff = {"type": "tome", "kind": "buff", "key": key, "pct": [5, 8, 12, 16, 20, 25][tier]}
                    desc_en, desc_fa = "Temporary blessing.", "برکتی موقت."
            elif cat == "egg":
                eff = {"type": "pet", "tier": tier, "role": PET_ROLES[i % 3]}
                desc_en, desc_fa = "Incubates a companion.", "یک همراه از آن بیرون می‌آید."
            elif cat == "key":
                d, df = DUNGEON_IDS[i // 5], DIFFS[i % 5]
                en, fa = f"{DUNGEONS[d]['en']} Key ({df})", f"کلید {DUNGEONS[d]['fa']} ({df})"
                eff = {"type": "key", "dungeon": d, "diff": df}
                rar = RARITIES[min(5, 1 + i % 5)]
                tier = RARITIES.index(rar)
                desc_en, desc_fa = f"Opens {DUNGEONS[d]['en']} on {df} difficulty.", f"ورود به {DUNGEONS[d]['fa']} در سختی {df}."
            elif cat == "armor":
                stats = {"def": 4 + tier * 9 + (i % 6) * 2}
                desc_en, desc_fa = f"+{stats['def']} defense.", f"+{stats['def']} دفاع."
            elif cat in ("ring", "necklace"):
                st = STATS[(i + (2 if cat == "necklace" else 0)) % 5]
                stats = {"stat": st, "bonus": 1 + tier * 2 + (i % 3)}
                if i % 7 == 0:
                    stats["luck"] = 1 + tier
                desc_en, desc_fa = f"+{stats['bonus']} {st}.", f"+{stats['bonus']} {st}."
            elif cat == "material":
                n_idx = i % len(nouns_of("material"))
                eff = {"type": "mat", "tag": MAT_TAGS[n_idx], "pw": tier + 1}
                desc_en, desc_fa = "Crafting material.", "ماده‌ی ساخت."
            elif cat == "evolution":
                if i < 20:
                    race, stage = _EVO_SLOTS[i]
                else:
                    race, stage = "*", 1 + (i - 20) % 4
                eff = {"type": "evo", "race": race, "stage": stage}
                rar = RARITIES[min(5, stage + 1)]
                tier = RARITIES.index(rar)
                desc_en, desc_fa = "Used in evolution trials.", "برای آزمون‌های تکامل."
            elif cat == "relic":
                kind = RELIC_KINDS[i % 4]
                if kind == "xp_loc":
                    eff = {"type": "relic", "kind": kind, "loc": _LOC_IDS[(i // 4) % len(_LOC_IDS)], "pct": RELIC_LOC_PCT[tier]}
                else:
                    eff = {"type": "relic", "kind": kind, "pct": RELIC_PCT[tier]}
                desc_en, desc_fa = "An ancient relic.", "یک یادگار باستانی."
            elif cat == "cosmetic":
                slot, glyph = COSM_NOUNS[(i // len(ADJ)) % len(nouns_of("cosmetic"))]
                eff = {"type": "cosm", "slot": slot, "glyph": glyph, "fame": tier + 1}
                if tier >= 3:
                    eff["buff"] = {"xp_pct": 1} if i % 2 == 0 else {"drop_pct": 1}
                desc_en, desc_fa = "A mark of renown.", "نشان شهرت."
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
ALL = {x["_id"]: x for x in ITEMS}
for _w in WEAPONS:
    _w.setdefault("sell_price", max(2, int(_w["base_price"] * 0.4)))
    ALL[_w["_id"]] = _w
BY_RARITY = {r: [x["_id"] for x in ITEMS if x["rarity"] == r and x["category"] in ("material", "potion", "armor", "accessory", "book", "egg", "relic")] for r in RARITIES}
BY_RARITY_EXTRA = {r: [x["_id"] for x in ITEMS if x["rarity"] == r and x["subtype"] in ("cosmetic", "evolution")] for r in RARITIES}
WEAPON_BY_RARITY = {r: [w["_id"] for w in WEAPONS if w["rarity"] == r] for r in RARITIES}


def iname(item_id: str, lang: str) -> str:
    x = ALL.get(item_id)
    return item_id if not x else x["name_fa" if lang == "fa" else "name_en"]
