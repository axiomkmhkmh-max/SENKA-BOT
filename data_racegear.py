"""Race armour and race technique cards.

Race armour: twenty kinds per race (five garments of the race x four make-ups), every kind in all six colours
(id ra_<race>_<nn>_<colour>). Armour is never chosen: it comes by luck (drops, the armour wheel, dungeon-shop chests,
battle-pass chests). Only its own race can wear it. Each kind has its own two perks (one from the garment, one from
the make-up) on top of its defence; perks grow with the colour.

Race technique cards: each race with canon techniques (data_race_tech) has ten cards per technique. Card n raises that
technique's mastery to n (learned in order, like Kidō); each mastery level adds TECH_LVL_STEP power. Shinigami and
Visored keep the Kidō cards. Pure data, no I/O.
"""
from data_race_tech import RACE_TECH
from data_weapons import PRICE, RARITIES

COLOURS = 6
DEF_BY_COLOUR = [9, 18, 27, 36, 45, 54]          # base defence of race armour at each colour (x the make-up factor)
LEVEL_BY_COLOUR = [1, 5, 15, 30, 50, 80]
PERK_STEP = 0.6                                    # perks grow +60% of their base per colour (red = x4)

# perk kind -> base value at white. Read by service_combat.build_player.
PERK_BASE = {"hp": 0.025, "dmg": 0.015, "def": 0.02, "crit": 0.008, "regen": 0.003, "kido": 0.02, "pierce": 0.015}
PERK_FA = {"hp": "جان", "dmg": "آسیب", "def": "دفاع", "crit": "ضربه‌ی کاری", "regen": "بازسازی هر نوبت", "kido": "کیدو", "pierce": "نفوذ"}

# race -> five garments: ((fa, en), perk kind)
GARMENTS = {
    "shinigami": [(("شیهاکوشو", "Shihakushō"), "hp"), (("هائوری", "Haori"), "kido"), (("هاکاما", "Hakama"), "crit"),
                  (("اوبی", "Obi Sash"), "def"), (("شنل جوخه", "Squad Cloak"), "dmg")],
    "visored": [(("ژاکت ویزورد", "Visored Jacket"), "dmg"), (("کلاه ماسک", "Mask Hood"), "crit"), (("کت انبار", "Warehouse Coat"), "hp"),
                (("هائوری هالوزده", "Hollow-Marked Haori"), "kido"), (("دستکش ماسک", "Mask Gloves"), "pierce")],
    "quincy": [(("یونیفرم کوئینسی", "Quincy Uniform"), "hp"), (("شنل اشترن‌ریتر", "Sternritter Cloak"), "crit"),
               (("کت وندن‌رایش", "Wandenreich Coat"), "def"), (("دستکش ریشی", "Reishi Gloves"), "pierce"), (("شنل سفید", "White Cape"), "dmg")],
    "hollow": [(("زره استخوانی", "Bone Plate"), "def"), (("پوسته‌ی ماسک", "Mask Shell"), "hp"), (("لاک هالو", "Hollow Carapace"), "regen"),
               (("ردای منوس", "Menos Robe"), "dmg"), (("پوست شکار", "Hunting Hide"), "crit")],
    "arrancar": [(("یونیفرم آرانکار", "Arrancar Uniform"), "hp"), (("ژاکت اسپادا", "Espada Jacket"), "dmg"),
                 (("هاکامای لاس‌نوچس", "Las Noches Hakama"), "crit"), (("کمربند هیرو", "Hierro Sash"), "def"), (("کت فراسیون", "Fracción Coat"), "pierce")],
    "fullbringer": [(("ژاکت اکسکیوشن", "Xcution Jacket"), "crit"), (("هودی خیابانی", "Street Hoodie"), "hp"), (("کت چرمی", "Leather Coat"), "def"),
                    (("دستکش فول‌برینگ", "Fullbring Gloves"), "dmg"), (("شال‌گردن", "Scarf"), "pierce")],
    "human": [(("یونیفرم دبیرستان کاراکورا", "Karakura High Uniform"), "hp"), (("لباس کاراته", "Karate Gi"), "dmg"),
              (("روپوش کلینیک", "Clinic Coat"), "regen"), (("پالتوی زمستانی", "Winter Coat"), "def"), (("جلیقه‌ی طلسم‌دار", "Charm Vest"), "crit")],
}
# make-up: ((fa, en) word, defence factor, perk kind)
MAKEUPS = [(("آهنین", "Iron"), 1.12, "def"), (("روحی", "Spirit"), 0.95, "hp"), (("جنگی", "War"), 1.0, "dmg"), (("چابک", "Swift"), 0.92, "crit")]


_FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def _fa(text: str) -> str:
    return text.translate(_FA_DIGITS)


def ra_id(race: str, n: int, colour: int) -> str:
    return f"ra_{race}_{n:02d}_{int(colour)}"


def parse_ra(item_id):
    if not item_id or not str(item_id).startswith("ra_"):
        return None
    parts = str(item_id).split("_")
    if len(parts) != 4:
        return None
    try:
        return parts[1], int(parts[2]), int(parts[3])
    except ValueError:
        return None


def _perks(g_kind, m_kind, colour):
    out = {}
    for k in (g_kind, m_kind):
        out[k] = round(out.get(k, 0) + PERK_BASE[k] * (1 + PERK_STEP * colour), 4)
    return out


def _build_armour():
    out = []
    for race, garments in GARMENTS.items():
        for gi, (gname, gk) in enumerate(garments):
            for mi, (mname, dfac, mk) in enumerate(MAKEUPS):
                n = gi * len(MAKEUPS) + mi
                for c in range(COLOURS):
                    rar = RARITIES[c]
                    perks = _perks(gk, mk, c)
                    iid = ra_id(race, n, c)
                    d = int(round(DEF_BY_COLOUR[c] * dfac))
                    pf = "، ".join(f"+{_fa(format(round(v * 100, 1), 'g').replace('.', '٫'))}٪ {PERK_FA[k]}" for k, v in perks.items())
                    pe = ", ".join(f"+{format(round(v * 100, 1), 'g')}% {k}" for k, v in perks.items())
                    out.append({
                        "_id": iid, "item_id": iid, "category": "armor", "subtype": "rarmor", "race": race, "ra_n": n, "ra_c": c,
                        "name_fa": f"{gname[0]} {mname[0]}", "name_en": f"{mname[1]} {gname[1]}",
                        "desc_fa": f"+{_fa(str(d))} دفاع · {pf}", "desc_en": f"+{d} defence · {pe}",
                        "rarity": rar, "stats": {"def": d}, "perk": perks, "effect": None, "slot": "armor",
                        "level_req": LEVEL_BY_COLOUR[c], "base_price": int(PRICE[rar] * 0.6), "sell_price": int(PRICE[rar] * 0.25),
                        "tradeable": True, "stack_max": 1,
                    })
    return out


RACE_ARMOUR_ITEMS = _build_armour()

# ---- race technique cards ----------------------------------------------------------------------------------------------
TECH_LVL_MAX = 10
TECH_LVL_STEP = 0.04     # +4% technique power per mastery level (level 10 = +40%)


def rc_id(race: str, slot: str, lvl: int) -> str:
    return f"rc_{race}_{slot}_{int(lvl):02d}"


def _build_cards():
    out = []
    for race, techs in RACE_TECH.items():
        for slot, t in techs.items():
            for lvl in range(1, TECH_LVL_MAX + 1):
                c = min(COLOURS - 1, (lvl - 1) // 2)
                rar = RARITIES[c]
                iid = rc_id(race, slot, lvl)
                out.append({
                    "_id": iid, "item_id": iid, "category": "race_card", "subtype": "race_card", "race": race,
                    "name_fa": _fa(f"کارت {t['name'][0]} {lvl}"), "name_en": f"{t['name'][1]} Card {lvl}",
                    "desc_fa": _fa(f"تسلط «{t['name'][0]}» را به سطح {lvl} می‌رساند (+{lvl * 4}٪ قدرت این تکنیک). باید به ترتیب یاد گرفته شود."),
                    "desc_en": f"Raises «{t['name'][1]}» mastery to level {lvl} (+{lvl * 4}% power). Learned in order.",
                    "rarity": rar, "stats": {}, "effect": {"type": "tech_lvl", "race": race, "slot": slot, "lvl": lvl},
                    "slot": None, "level_req": 1, "base_price": int(PRICE[rar] * 0.5), "sell_price": int(PRICE[rar] * 0.2),
                    "tradeable": True, "stack_max": 99,
                })
    return out


RACE_CARD_ITEMS = _build_cards()
