"""Bilingual intent router: text -> (registry code, arg). Typo tolerant."""
import difflib
import time

from database import col
from security import normalize_text

# intent -> (code, arg, synonyms)
RAW = {
    "home": ("home", "", ["دنیای من", "جهان من", "خانه", "پنل اصلی", "پنل", "منو", "همه چیز", "همه‌چیز", "سنکا", "سِنکا", "home", "my world", "menu", "main", "everything", "senka", "panel", "start", "شروع"]),
    "profile": ("prof", "", ["پروفایل", "مشخصات", "کاراکتر من", "profile", "me", "stats", "character"]),
    "explore": ("exp", "", ["گشت", "گشت و گذار", "گشت‌وگذار", "کاوش", "explore", "patrol", "wander"]),
    "adventure": ("map", "", ["ماجراجویی", "نقشه", "مکان", "adventure", "map", "travel", "location"]),
    "bag": ("bag", "0", ["کوله", "کیف", "اینونتوری", "انبار", "bag", "inventory", "items", "backpack"]),
    "sword": ("bag", "0:w", ["شمشیر من", "سلاح", "زانپاکتو", "my sword", "weapon", "zanpakuto", "equipment"]),
    "market": ("mkt", "", ["بازار", "بازارچه", "market", "shop", "store", "trade"]),
    "battle": ("bt", "", ["نبرد", "مبارزه", "جنگ", "battle", "fight", "combat"]),
    "squad": ("gld", "", ["جوخه", "گیلد", "کلن", "squad", "guild", "clan"]),
    "ranking": ("rnk", "", ["رتبه بندی", "رتبه‌بندی", "لیدربورد", "جدول", "ranking", "leaderboard", "rank", "top"]),
    "quests": ("qst", "", ["ماموریت", "مأموریت", "ماموریت ها", "مأموریت‌ها", "کار", "quests", "quest", "missions", "tasks"]),
    "daily": ("dly", "", ["جایزه روزانه", "روزانه", "جایزه", "daily", "daily reward", "reward", "bonus"]),
    "gacha": ("gch", "", ["احضار", "گاچا", "summon", "gacha", "pull", "banner"]),
    "mini": ("mgm", "", ["مینی گیم", "مینی‌گیم", "بازی", "معما", "minigame", "mini game", "games", "puzzle", "quiz"]),
    "dungeon": ("dgn", "", ["دانجن", "سیاهچال", "زندان", "dungeon", "dungeons", "raid"]),
    "settings": ("set", "", ["تنظیمات", "زبان", "settings", "language", "options", "lang"]),
    "help": ("hlp", "", ["راهنما", "کمک", "help", "guide", "how to play", "؟", "?"]),
    "boss": ("bossinfo", "", ["باس", "باس جهانی", "boss", "world boss"]),
    "admin": ("adm", "", ["مدیریت", "ادمین", "admin", "panel admin", "dashboard"]),
    "forge": ("frg", "", ["آهنگری", "فورج", "تقویت سلاح", "forge", "smith", "blacksmith", "upgrade weapon"]),
    "party": ("pty", "0", ["تیم", "پارتی", "همراهان", "party", "team", "companions"]),
    "commands": ("cmd", "", ["دستورات", "لیست دستورات", "فرمان ها", "فرمان‌ها", "commands", "command list", "cmds", "words"]),
    "world": ("wrd", "", ["دنیا", "جهان زنده", "وضعیت دنیا", "world", "world state", "realm"]),
    "craft": ("crf", "", ["ساخت", "کرافت", "craft", "crafting", "workshop"]),
    "season": ("ssn", "", ["فصل", "season", "seasons"]),
    "chronicle": ("chr", "", ["تاریخچه", "وقایع", "chronicle", "news"]),
    "territory": ("ter", "", ["قلمرو", "territory", "land"]),
    "bounty": ("bty", "", ["باونتی", "جایزه سر", "bounty", "wanted"]),
    "gear": ("eqp", "", ["یادگار", "همراه من", "relic", "relics", "pets", "pet"]),
    "evolution": ("evo", "", ["تکامل", "evolution", "evolve"]),
    "tower": ("twr", "", ["برج", "برج روح", "tower", "soul tower", "spire"]),
    "dispatch": ("dsp", "", ["اعزام", "ماموریت اعزام", "dispatch", "send squad", "expedition"]),
    "wheel": ("whl", "", ["چرخ", "چرخ شانس", "چرخ اوراهارا", "wheel", "spin", "lucky wheel"]),
    "seat": ("sat", "", ["درجه", "درجه گوتی", "کرسی", "seat", "my seat", "gotei seat"]),
    "inner": ("inr", "", ["دنیای درون", "درون", "inner world", "inner", "spirit talk"]),
    "artifact": ("art", "", ["آرتیفکت", "آرتیفکت من", "گنجینه", "گنجینه من", "artifact", "my artifact", "treasure"]),
    "artifact_reg": ("arr", "", ["ثبت نامه آرتیفکت", "ثبت‌نامه آرتیفکت‌ها", "ثبتنامه گنجینه ها", "artifact registry", "registry"]),
    "artifact_mkt": ("axm", "0", ["بازار آرتیفکت", "artifact market", "artifact exchange", "exchange"]),
    "duel": ("*duel", "r", ["دوئل", "دوئل رنکد", "duel", "ranked duel", "challenge"]),
    "duel_friendly": ("*duel", "f", ["دوئل دوستانه", "friendly duel", "friendly"]),
}
GROUP_OK = {"duel", "duel_friendly", "boss", "help", "home", "chronicle", "commands"}
_map: dict = {}
_extra_at = 0.0


def _build(extra=None):
    m = {}
    for name, (code, arg, words) in RAW.items():
        for w in words:
            m[normalize_text(w)] = (name, code, arg)
    for name, words in (extra or {}).items():
        if name in RAW:
            code, arg, _ = RAW[name]
            for w in words:
                m[normalize_text(w)] = (name, code, arg)
    return m


_map = _build()


async def refresh():
    global _map, _extra_at
    if time.monotonic() - _extra_at < 60:
        return
    _extra_at = time.monotonic()
    extra = {}
    try:
        async for d in col("intents").find({}):
            extra[d["action"]] = d.get("words", [])
    except Exception:
        pass
    _map = _build(extra)


async def resolve(text: str):
    """Return (intent name, code, arg) or None."""
    await refresh()
    n = normalize_text(text)
    if not n or len(n) > 40:
        return None
    hit = _map.get(n)
    if hit:
        return hit
    if len(n) >= 4:
        close = difflib.get_close_matches(n, list(_map.keys()), n=1, cutoff=0.84)
        if close:
            return _map[close[0]]
    return None


def word_for(intent: str) -> str:
    """First ASCII synonym of an intent (used to run /commands through the same router)."""
    for w in RAW[intent][2]:
        if w.isascii():
            return w
    return RAW[intent][2][0]
