"""Player catalog / patch notes (Nov 26): what every kind of item is, where it comes from, how it is activated, every skin,
and every dungeon with its goal and its own final drops. Pure text builders, built from the game's own data so they cannot
drift from the rules. Each builder returns a list of messages that each fit one Telegram message."""
from data_dungeon_drops import FINAL_DAY_CAP, RARITIES, RARITY_LEVEL, final_drops
from data_skins import LABEL, RARITY_ICON, SKINS, bonus_text

LIMIT = 3400   # characters per message (Telegram allows 4096; headers and buttons need room)
_FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def _n(v, lang):
    return str(v).translate(_FA) if lang == "fa" else str(v)


def _name(iid, lang):
    from data_items import ALL
    x = ALL.get(iid) or {}
    return x.get("name_fa" if lang == "fa" else "name_en", iid)


def _pack(title: str, lines: list) -> list:
    """Split lines into messages under LIMIT, repeating the title on each."""
    pages, cur = [], title
    for ln in lines:
        if len(cur) + len(ln) + 1 > LIMIT and cur != title:
            pages.append(cur)
            cur = title
        cur += "\n" + ln
    pages.append(cur)
    return pages


# ---- item kinds: (icon, fa name, en name, fa text, en text). Only facts that the code enforces. ---------------------------
KINDS = [
    ("⚔️", "سلاح، زره، اکسسوری", "Weapons, armour, accessories",
     "نوع: تجهیزات. از شکار، باس، جعبه‌ی دانجن و گردونه می‌آیند. هر رنگ یک سطح لازم دارد (بالا را ببین). فعال‌سازی: از کیف بپوش.",
     "Type: gear. From hunts, bosses, dungeon chests and wheels. Each colour needs a level (see below). Activate: wear it from the bag."),
    ("🌀", "کارت کیدو", "Kidō cards",
     "نوع: کارت. به‌طور تخصصی از نبرد و زنجیره‌ی دراپ به‌دست می‌آید و در دانجن هم احتمالش هست. فعال‌سازی: از کیف مصرف کن تا کیدو یاد بگیری.",
     "Type: card. Mainly from battle and the drop chain, and it can also drop in dungeons. Activate: use it from the bag to learn the Kidō."),
    ("📜", "کارت مهارت", "Skill cards",
     "نوع: کارت. به‌طور تخصصی از ماجراجویی و برج روح می‌آید. فعال‌سازی: از کیف مصرف کن تا مهارت را یاد بگیری.",
     "Type: card. Mainly from adventures and the Soul Tower. Activate: use it from the bag to learn the skill."),
    ("🧪", "ماده، معجون، کتاب", "Materials, potions, books",
     "نوع: مصرفی. هر دانجن در مرحله‌ی آخر یکی از دراپ‌های مخصوص خودش را تضمینی می‌دهد (لیست دانجن‌ها را ببین). مواد برای ساخت و فورج، معجون‌ها برای مبارزه، کتاب‌ها برای تجربه.",
     "Type: consumable. Every dungeon guarantees one of its own drops at the final stage (see the dungeon list). Materials for crafting and forging, potions for fights, books for XP."),
    ("🗝", "کلید", "Keys",
     "نوع: کلید. ورود به دانجن با سختی مشخص. قابل ترید نیست. فعال‌سازی: هنگام ورود به دانجن مصرف می‌شود.",
     "Type: key. Opens a dungeon on its difficulty. Not tradeable. Activate: used when you enter the dungeon."),
    ("🔶", "یادگار تکامل", "Evolution relics",
     "نوع: سوخت تکامل و رنگ سلاح نژاد. از جعبه‌های دانجن می‌آید: برنزی (سفید/سبز)، نقره‌ای (آبی/بنفش)، طلایی (بنفش).",
     "Type: fuel for evolution and a race weapon's colour. From dungeon chests: bronze (white/green), silver (blue/purple), gold (purple)."),
    ("🎁", "آیتم مخصوص دانجن", "Dungeon special items",
     "نوع: ویژه. با شانس کم بعد از پاک‌کردن کامل دانجن، بر اساس سختی. سقف روزانه دارد.",
     "Type: special. A small chance after a full clear, by difficulty. Daily cap applies."),
    ("🔨", "سنگ آبدیده‌سازی", "Tempering stone",
     "نوع: ماده‌ی ویژه. برای فورج سلاح و آبدیده‌کردن زره بعد از +۵. از جعبه‌ی طلایی با شانس کم.",
     "Type: special material. Needed to forge a weapon / temper armour past +5. Rarely from the gold chest."),
    ("🏺", "آرتیفکت", "Artifacts",
     "نوع: یادگار منحصربه‌فرد، یکی برای هر پلیر. از دراپ گروهی و بازار آرتیفکت. می‌توانی با پلیر دیگر یک‌به‌یک تعویض کنی. فعال‌سازی: خودکار وقتی نگهش داری.",
     "Type: unique relic, one per player. From group drops and the Artifact Exchange. You can swap one-for-one with another player. Activate: automatic while you hold it."),
]


def kinds_pages(lang: str) -> list:
    fa = lang == "fa"
    head = "📖 <b>" + ("راهنمای آیتم‌ها" if fa else "Item guide") + "</b>"
    lines = [f"{ic} <b>{f if fa else e}</b>\n{tf if fa else te}\n" for ic, f, e, tf, te in KINDS]
    lines.append(("🎚 <b>سطح لازم هر رنگ</b>\n" if fa else "🎚 <b>Level needed by colour</b>\n") +
                 " · ".join(f"{RARITIES[i]} {_n(RARITY_LEVEL[i], lang)}" for i in range(6)))
    return _pack(head, lines)


def skins_pages(lang: str) -> list:
    fa = lang == "fa"
    head = "🎭 <b>" + ("کاتالوگ اسکین‌ها" if fa else "Skin catalog") + "</b>\n" + (
        "اسکین از گردونه‌ها و ایونت‌ها می‌آید. فقط یکی فعال است و بونوسش را می‌دهد." if fa else
        "Skins come from wheels and events. One is active at a time and gives its bonus.")
    lines = []
    for r in ("Mythic", "Legendary", "Epic"):
        group = [s for s in SKINS.values() if s["rarity"] == r]
        if group:
            lines.append(f"\n{RARITY_ICON.get(r, '')} <b>{r}</b>")
            lines += [f"{s['icon']} {s['fa'] if fa else s['en']}: {bonus_text(s, lang)}" for s in group]
    lines.append("\n" + ("نوع بونوس‌ها: " if fa else "Bonus kinds: ") + "، ".join(v[0 if fa else 1] for v in LABEL.values()))
    return _pack(head, lines)


def dungeons_pages(lang: str) -> list:
    from data_items import DG_SPECIAL
    from data_races import DUNGEONS
    fa = lang == "fa"
    head = "🏰 <b>" + ("دانجن‌ها: هدف و دراپ" if fa else "Dungeons: goal and drops") + "</b>"
    lines = [(f"هدف همه‌ی دانجن‌ها: تجربه و DP. در مرحله‌ی آخر یکی از دراپ‌های مخصوص همان دانجن تضمینی است (تا {_n(FINAL_DAY_CAP, lang)} بار در روز برای هر دانجن)."
              if fa else f"Every dungeon's goal: XP and DP. The final stage guarantees one of that dungeon's own drops (up to {FINAL_DAY_CAP} times a day per dungeon).")]
    for did, d in sorted(DUNGEONS.items(), key=lambda kv: kv[1].get("level", 0)):
        drops = ", ".join(_name(i, lang) for i in final_drops(did))
        nm = d.get("fa" if fa else "en") or did
        lines.append(f"\n<b>{nm}</b> — {'لول' if fa else 'Lv'} {_n(d['level'], lang)} · {_n(d['stages'], lang)} {'مرحله' if fa else 'stages'}\n"
                     f"{'هدف: تجربه · دراپ نهایی: ' if fa else 'Goal: XP · Final drop: '}{drops}")
    lines.append("\n" + ("🎁 <b>آیتم مخصوص (شانسی، بر اساس سختی)</b>" if fa else "🎁 <b>Special items (chance, by difficulty)</b>"))
    for diff, ids in DG_SPECIAL.items():
        lines.append(f"{diff}: " + "، ".join(_name(i, lang) for i in ids))
    return _pack(head, lines)


def chests_pages(lang: str, BOXES: dict) -> list:  # BOXES lives in service_dungeonshop (database import): the caller passes it
    fa = lang == "fa"
    head = "🥇 <b>" + ("جعبه‌های دانجن" if fa else "Dungeon chests") + "</b>"
    lines = [("جعبه با DP خریده می‌شود. رنگ آیتم‌ها به سطح خودت بستگی دارد: چیزی که هنوز نمی‌توانی بپوشی نمی‌آید." if fa else
              "Chests are bought with DP. The colours follow YOUR level: nothing you cannot yet use will drop.")]
    for k, b in BOXES.items():
        lo, hi = b["rar"]
        lines.append(f"\n{b['icon']} <b>{b['fa'] if fa else b['en']}</b> — {_n(b['cost'], lang)} DP\n"
                     f"{RARITIES[lo]} / {RARITIES[hi]} · {'سکه' if fa else 'coins'} {_n(b['coins'][0], lang)}–{_n(b['coins'][1], lang)}")
    lines.append("\n" + ("سطح لازم: " if fa else "Level needed: ") + " · ".join(f"{RARITIES[i]} {_n(RARITY_LEVEL[i], lang)}" for i in range(6)))
    return _pack(head, lines)


def all_pages(lang: str, boxes: dict) -> list:
    """Everything, in posting order (for the news channel)."""
    return kinds_pages(lang) + skins_pages(lang) + chests_pages(lang, boxes) + dungeons_pages(lang)
