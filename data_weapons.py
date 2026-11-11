"""110+ zanpakuto/blades. Each has a distinct on-hit skill (not just stats)."""
RARITIES = ["Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythic"]
RARITY_ICON = {"Common": "⚪", "Uncommon": "🟢", "Rare": "🔵", "Epic": "🟣", "Legendary": "🟠", "Mythic": "🔴"}
ELEMENTS = ["fire", "ice", "lightning", "earth", "water", "poison", "shadow", "light"]
ELEMENT_FA = {"fire": "آتش", "ice": "یخ", "lightning": "برق", "earth": "خاک", "water": "آب", "poison": "سم", "shadow": "سایه", "light": "نور"}
TYPES = ["melee", "elemental", "kido", "illusion", "living", "defensive", "ranged", "speed", "hybrid"]
TYPE_FA = {"melee": "ملی", "elemental": "عنصری", "kido": "کیدو‌محور", "illusion": "توهمی", "living": "زنده",
           "defensive": "دفاعی", "ranged": "پرتابی", "speed": "سرعت‌محور", "hybrid": "ترکیبی"}
# element wheel: key beats value (x1.5), reverse is x0.75
BEATS = {"fire": "ice", "ice": "lightning", "lightning": "earth", "earth": "water", "water": "fire"}

# skill id -> (fa text, en text); {p} is the proc percentage
SKILLS = {
    "bleed": ("{p}٪ شانس خونریزی (۲٪ در ۴ نوبت)", "{p}% chance to cause bleeding (2% x 4 turns)"),
    "burn": ("{p}٪ شانس سوختن (۳٪ در ۳ نوبت)", "{p}% chance to ignite (3% x 3 turns)"),
    "poison": ("{p}٪ شانس سم (۵٪ در ۳ نوبت، انباشتی)", "{p}% chance to poison (5% x 3 turns, stacks)"),
    "shock": ("{p}٪ شانس شوک (+۱۵٪ آسیب دریافتی)", "{p}% chance to shock (+15% damage taken)"),
    "freeze": ("{p}٪ شانس انجماد (دشمن یک اکشن را از دست می‌دهد)", "{p}% chance to freeze (target loses an action)"),
    "stun": ("{p}٪ شانس استان یک نوبتی", "{p}% chance to stun for one turn"),
    "lifesteal": ("{p}٪ از آسیب به HP تبدیل می‌شود", "{p}% of damage returns as HP"),
    "pierce": ("{p}٪ دفاع هدف نادیده گرفته می‌شود", "ignores {p}% of target defense"),
    "double": ("{p}٪ شانس ضربه‌ی دوم با نصف قدرت", "{p}% chance of a second strike at half power"),
    "execute": ("+{p}٪ آسیب به هدف زیر ۳۰٪ HP", "+{p}% damage to targets below 30% HP"),
    "drain": ("{p}٪ ریاتسو حداکثر هدف را می‌دزدد", "steals {p}% of target max reiatsu"),
    "counter": ("هنگام دفاع، {p}٪ آسیب را بازمی‌گرداند", "reflects {p}% damage while guarding"),
    "surge": ("+{p}٪ ضریب کریتیکال", "+{p}% critical multiplier"),
    "weaken": ("{p}٪ شانس کاهش ۱۵٪ دفاع هدف (۳ نوبت)", "{p}% chance to cut target defense by 15% (3 turns)"),
}
SKILL_KEYS = list(SKILLS)
PREF = [("Tsuki", "تسوکی", "Moon", "ماه"), ("Kuro", "کورو", "Black", "سیاه"), ("Aka", "آکا", "Crimson", "سرخ"),
        ("Shiro", "شیرو", "White", "سفید"), ("Ao", "آئو", "Azure", "لاجورد"), ("Kaze", "کازه", "Wind", "باد"),
        ("Yami", "یامی", "Dark", "تاریک"), ("Hikari", "هیکاری", "Radiant", "درخشان"), ("Kori", "کوری", "Frost", "یخ"),
        ("Rai", "رای", "Thunder", "تندر"), ("Mizu", "میزو", "Water", "آب"), ("Tsuchi", "تسوچی", "Earth", "خاک")]
SUFF = [("kage", "کاگه", "Shadow", "سایه"), ("ba", "با", "Blade", "تیغ"), ("hime", "هیمه", "Princess", "شاهدخت"),
        ("mai", "مای", "Dance", "رقص"), ("kiri", "کیری", "Mist", "مه"), ("tsume", "تسومه", "Claw", "چنگال"),
        ("ryu", "ریو", "Dragon", "اژدها"), ("ki", "کی", "Spirit", "روح"), ("sen", "سن", "Flash", "جرقه"),
        ("kokoro", "کوکورو", "Heart", "قلب")]
TIERS = [("Common", 30, 8, 1), ("Uncommon", 30, 16, 5), ("Rare", 24, 30, 15),
         ("Epic", 18, 55, 30), ("Legendary", 12, 95, 50), ("Mythic", 6, 160, 80)]
PRICE = {"Common": 120, "Uncommon": 400, "Rare": 1500, "Epic": 6000, "Legendary": 30000, "Mythic": 150000}


def _build():
    out, i = [], 0
    for rarity, count, base, lvl in TIERS:
        for k in range(count):
            pi, si = i // 10, i % 10
            skill = SKILL_KEYS[(i * 5 + i // 14) % len(SKILL_KEYS)]
            skill2 = SKILL_KEYS[(i * 3 + 7) % len(SKILL_KEYS)] if rarity in ("Epic", "Legendary", "Mythic") else None
            if skill2 == skill:
                skill2 = SKILL_KEYS[(SKILL_KEYS.index(skill) + 1) % len(SKILL_KEYS)]
            tier_i = TIERS.index((rarity, count, base, lvl))
            pct = 8 + tier_i * 4 + (k % 5) * 2
            if skill in ("lifesteal", "pierce", "execute", "drain", "counter", "surge"):
                pct = 6 + tier_i * 4 + (k % 4) * 2
            skills = [{"id": skill, "p": pct}] + ([{"id": skill2, "p": max(6, pct - 4)}] if skill2 else [])
            wid = f"wp_{i + 1:03d}"
            out.append({
                "_id": wid, "item_id": wid, "category": "weapon",
                "name_en": f"{PREF[pi][0]}{SUFF[si][0]}", "name_fa": f"{PREF[pi][1]}\u200c{SUFF[si][1]}",
                "meaning_en": f"{PREF[pi][2]} {SUFF[si][2]}", "meaning_fa": f"{SUFF[si][3]} {PREF[pi][3]}",
                "rarity": rarity, "element": ELEMENTS[i % 8], "weapon_type": TYPES[i % 9],
                "attack": base + k * 2, "crit": round(0.005 * (k % 6) + 0.004 * tier_i, 3),
                "level_req": lvl, "skills": skills, "durability": 100 + tier_i * 20,
                "base_price": int(PRICE[rarity] * (1 + (k % 5) / 10)), "tradeable": rarity != "Mythic",
                "stack_max": 1, "slot": "weapon",
            })
            i += 1
    return out


WEAPONS = _build()
WEAPON_BY_ID = {w["_id"]: w for w in WEAPONS}


def skill_text(skill: dict, lang: str) -> str:
    return SKILLS[skill["id"]][0 if lang == "fa" else 1].format(p=skill["p"])
