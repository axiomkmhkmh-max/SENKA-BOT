"""Collectible gacha characters (name_en, name_fa, rarity, role, element)."""
_C = [
    ("Kon", "کن", "Common", "support"), ("Izuru Kira", "ایزورو کیرا", "Common", "tank"),
    ("Shuhei Hisagi", "شوهی هیساگی", "Common", "attacker"), ("Momo Hinamori", "مومو هیناموری", "Common", "caster"),
    ("Isane Kotetsu", "ایزانه کوتتسو", "Common", "support"),
    ("Ikkaku Madarame", "ایککاکو مادارامه", "Uncommon", "attacker"), ("Yumichika Ayasegawa", "یومیچیکا آیاساوا", "Uncommon", "attacker"),
    ("Rose Otoribashi", "روز اوتوریباشی", "Uncommon", "caster"), ("Hiyori Sarugaki", "هیوری ساروگاکی", "Uncommon", "attacker"),
    ("Yasutora Sado", "یاسوتورا سادو", "Uncommon", "tank"), ("Orihime Inoue", "اوریهیمه اینوئه", "Uncommon", "support"),
    ("Uryu Ishida", "اوریو ایشیدا", "Uncommon", "caster"),
    ("Rukia Kuchiki", "روکیا کوچیکی", "Rare", "caster"), ("Renji Abarai", "رنجی آبارای", "Rare", "attacker"),
    ("Rangiku Matsumoto", "رانگیکو ماتسوموتو", "Rare", "caster"), ("Soi Fon", "سوی فون", "Rare", "attacker"),
    ("Sajin Komamura", "ساجین کوماموتو", "Rare", "tank"), ("Mayuri Kurotsuchi", "مایوری کوروتسوچی", "Rare", "caster"),
    ("Shinji Hirako", "شینجی هیراکو", "Rare", "attacker"), ("Grimmjow Jaegerjaquez", "گریمجو", "Rare", "attacker"),
    ("Byakuya Kuchiki", "بیاکویا کوچیکی", "Epic", "caster"), ("Toshiro Hitsugaya", "توشیرو هیتسوگایا", "Epic", "caster"),
    ("Kenpachi Zaraki", "کنپاچی زاراکی", "Epic", "attacker"), ("Yoruichi Shihoin", "یورویچی شیهوئین", "Epic", "attacker"),
    ("Kisuke Urahara", "کیسوکه اوراهارا", "Epic", "support"), ("Ulquiorra Cifer", "اولکیورا", "Epic", "attacker"),
    ("Coyote Starrk", "کویوت استارک", "Epic", "attacker"), ("Nelliel Tu Odelschwanck", "نلیل", "Epic", "tank"),
    ("Tier Harribel", "تیر هریبل", "Epic", "caster"), ("Kaname Tosen", "کانامه توسن", "Epic", "tank"),
    ("Ichigo Kurosaki", "ایچیگو کوروساکی", "Legendary", "attacker"), ("Shunsui Kyoraku", "شونسویی کیوراکو", "Legendary", "caster"),
    ("Jushiro Ukitake", "جوشیرو اوکیتاکه", "Legendary", "support"), ("Gin Ichimaru", "گین ایچیمارو", "Legendary", "attacker"),
    ("Jugram Haschwalth", "جوگرام هاشوالت", "Legendary", "tank"),
    ("Genryusai Yamamoto", "گنریوسای یاماموتو", "Mythic", "attacker"), ("Sosuke Aizen", "سوسکه آیزن", "Mythic", "caster"),
    ("Yhwach", "یوهابخ", "Mythic", "caster"),
]
CHARS = [{"_id": f"ch_{i + 1:02d}", "name_en": e, "name_fa": f, "rarity": r, "role": role,
          "element": ["fire", "ice", "lightning", "earth", "water", "poison", "shadow", "light"][i % 8]}
         for i, (e, f, r, role) in enumerate(_C)]
CHAR_BY_ID = {c["_id"]: c for c in CHARS}
BASE_PCT = {"Common": 1.0, "Uncommon": 2.0, "Rare": 3.0, "Epic": 5.0, "Legendary": 8.0, "Mythic": 12.0}
STAR_AT = [1, 3, 6, 10]  # copies needed for awakening stars 0..3
GACHA_RATES = {"Common": 50.0, "Uncommon": 25.0, "Rare": 15.0, "Epic": 7.0, "Legendary": 2.5, "Mythic": 0.5}


def copies_to_level_star(copies: int):
    level = max(1, min(10, copies))
    star = sum(1 for t in STAR_AT[1:] if copies >= t)
    return level, star


def char_bonus(char_id: str, copies: int) -> dict:
    c = CHAR_BY_ID[char_id]
    level, star = copies_to_level_star(copies)
    pct = BASE_PCT[c["rarity"]] * (1 + 0.25 * star) * (1 + 0.05 * (level - 1))
    key = {"attacker": "dmg", "tank": "def", "caster": "kido", "support": "xp"}[c["role"]]
    return {key: round(pct / 100, 4)}
