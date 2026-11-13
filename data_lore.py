"""Flavour text was removed: SENKA is a game, not a story. The names remain as empty shims so
existing imports keep working; every call site already treats an empty result as "show nothing"."""

SPIRIT_TYPE = {}
SPIRIT_ELEM = {}
CHAR_EPI = {}
DUNGEON_LORE = {}
ITEM_FLAVOR = {}
STREAK_LINE = {}


def spirit_line(weapon: dict, lang: str) -> str:
    return ""


def dungeon_line(dungeon_id: str, stage: int, total: int, lang: str) -> str:
    return ""


def streak_line(streak: int, lang: str) -> str:
    return ""
