"""Ten Mythic (red) items for the categories that had none: potions, books, charms, eggs, relics, cosmetics, materials.

Every item reuses an effect type the bag already handles (hp, reiatsu, kido_book, buff, pet, relic, cosmetic, mat), so no
new rules are needed. They are bound to their owner (Mythic is never tradeable) and kept out of every random pool
(`special`): they come only from the Soul Wheel's Mythic and Legacy prizes, the roll shop's Mythic roll (the egg), and the
top level-band boss. Ids it_m001..it_m010 are new, so no older item id moves.
Pure data, no I/O."""


def _m(iid, cat, en, fa, d_en, d_fa, price, eff, stack=99):
    return {"_id": iid, "item_id": iid, "category": cat, "subtype": cat, "name_en": en, "name_fa": fa, "desc_en": d_en,
            "desc_fa": d_fa, "rarity": "Mythic", "stats": {}, "effect": eff, "slot": None, "level_req": 1,
            "base_price": price, "sell_price": int(price * 0.4), "tradeable": False, "stack_max": stack, "special": True}


MYTHIC_ITEMS = [
    _m("it_m001", "potion", "Sōten Kisshun Elixir", "اکسیر سوتن کیشون",
       "A single drop of Orihime's rejection. It refuses the wound itself: restores 100% HP.",
       "یک قطره از قدرت «رد کردن» اوریهیمه؛ خودِ زخم را نمی‌پذیرد. ۱۰۰٪ جان را بازمی‌گرداند.",
       12000, {"type": "hp", "pct": 100}),
    _m("it_m002", "potion", "Soul King's Spring Water", "آب چشمه‌ی شاه ارواح",
       "Water from beneath the Royal Palace, where reishi runs thickest. Restores 100% reiatsu.",
       "آبی از زیر کاخ سلطنتی، جایی که ریشی غلیظ‌تر از هر جاست. ۱۰۰٪ ریاتسو را بازمی‌گرداند.",
       12000, {"type": "reiatsu", "pct": 100}),
    _m("it_m003", "book", "Tessai's Grand Kidō Grimoire", "طومار بزرگ کیدوی تسای",
       "The Grand Kidō Chief's own notes, written in the margins of every spell. Teaches an unknown Hadō (up to No. 99).",
       "یادداشت‌های خودِ رئیس بزرگ کیدو، حاشیه‌ی تک‌تک وردها. یک هادوی ناشناخته می‌آموزد (تا شماره ۹۹).",
       15000, {"type": "kido_book", "branch": "had", "cap": 99}),
    _m("it_m004", "charm", "Getsuga Tenshō Charm", "طلسم گتسوگا تنشو",
       "A black thread of the Final Getsuga Tenshō. Your strikes hit much harder for 120 minutes.",
       "رشته‌ای سیاه از گتسوگا تنشوی نهایی. ۱۲۰ دقیقه ضربه‌هایت بسیار سنگین‌تر می‌زنند.",
       14000, {"type": "buff", "stat": "dmg", "pct": 0.18, "minutes": 120}),
    _m("it_m005", "charm", "Kenpachi's Eyepatch Charm", "طلسم چشم‌بند کنپاچی",
       "The eyepatch that eats his own reiatsu. Worn loose, it lets the edge show: critical chance is far higher for 120 minutes.",
       "چشم‌بندی که ریاتسوی خودش را می‌بلعد؛ شل ببندی‌اش، لبه‌ی تیغ پیدا می‌شود. ۱۲۰ دقیقه شانس کریتیکال خیلی بیشتر است.",
       14000, {"type": "buff", "stat": "crit", "pct": 0.14, "minutes": 120}),
    _m("it_m006", "egg", "Jigokuchō Royal Egg", "تخم سلطنتی جیگوکوچو",
       "Laid by the butterfly that guides souls through the Dangai. Hatches a companion of the highest grade (★8).",
       "تخمی از پروانه‌ای که ارواح را در دنگای راهنمایی می‌کند. همراهی در بالاترین درجه (★۸) از آن بیرون می‌آید.",
       20000, {"type": "pet", "tier": 7}),
    _m("it_m007", "relic", "Ichigo's Final Getsuga Mark", "نشان نهایی گتسوگای ایچیگو",
       "Scorched into the ground where he stood. An old power that answers when attuned: a great boost to damage.",
       "روی زمینی سوخته که او آنجا ایستاده بود. قدرتی کهن که با هم‌سازی بیدار می‌شود: افزایش بزرگ آسیب.",
       30000, {"type": "relic", "kind": "dmg", "loc": None, "v": 0.07}, stack=99),
    _m("it_m008", "relic", "Soul King's Ledger of Names", "دفتر نام‌های شاه ارواح",
       "Every soul that ever crossed over is written here once. An old power that answers when attuned: you learn far faster.",
       "نام هر روحی که از این جهان گذشته، یک بار اینجا نوشته شده. قدرتی کهن که با هم‌سازی بیدار می‌شود: بسیار سریع‌تر می‌آموزی.",
       30000, {"type": "relic", "kind": "xp", "loc": None, "v": 0.16}, stack=99),
    _m("it_m009", "cosmetic", "Royal Palace Radiance", "درخشش کاخ سلطنتی",
       "A halo cut from the light of the Palace of the Soul King. It shines beside your name for the whole world to see.",
       "هاله‌ای بریده از نور کاخ شاه ارواح؛ کنار نامت می‌درخشد تا همه‌ی جهان ببیند.",
       25000, {"type": "cosmetic", "slot": "aura", "icon": "🌌", "fame": 8}, stack=1),
    _m("it_m010", "material", "Hōgyoku Reishi Crystal", "کریستال ریشی هوگیوکو",
       "A crystal that grew inside the orb while it waited. Crafting material of the reishi group; worth three units at the forge.",
       "بلوری که درون گوی خواسته‌ها رشد کرد وقتی انتظار می‌کشید. ماده‌ی ساخت گروه ریشی؛ در فورج سه واحد حساب می‌شود.",
       18000, {"type": "mat", "kind": "reishi", "group": "reishi"}),
]
MYTHIC_ITEM_IDS = [x["_id"] for x in MYTHIC_ITEMS]
