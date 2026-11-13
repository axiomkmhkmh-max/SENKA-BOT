"""SENKA+ Shikai Riddle: the group guesses a Zanpakutō name letter by letter (like Hangman), shared by everyone.

Each correct letter scores for whoever guesses it; a wrong letter costs one life, and the group loses at zero lives.
Guessing the whole name wins at once. Pure logic: no MongoDB, no Telegram.
"""
import random
import unicodedata

NAMES = [  # (display name, lives)
    "Zangetsu", "Sode no Shirayuki", "Hyorinmaru", "Senbonzakura", "Nozarashi",
    "Kyoka Suigetsu", "Ryujin Jakka", "Tobiume", "Sogyo no Kotowari", "Benihime",
]
LIVES = 7
CORRECT_POINTS = 10
WORD_BONUS = 50

_ALIAS = {"ō": "o", "ū": "u", "ā": "a", "ē": "e", "ī": "i"}


def normalize(text: str) -> str:
    t = unicodedata.normalize("NFKD", text).lower()
    for k, v in _ALIAS.items():
        t = t.replace(k, v)
    return "".join(ch for ch in t if ch.isalpha())


def new_round(rng=None, name=None):
    rng = rng or random.Random()
    name = name or rng.choice(NAMES)
    return {"name": name, "hidden": name, "guessed": set(), "wrong": set(), "lives": LIVES,
            "scores": {}, "done": False, "won": False}


def masked(st):
    """What the group sees: letters shown, others as '_'; spaces are shown as they are."""
    return " ".join(
        ch if not ch.isalpha() or normalize(ch) in st["guessed"] else "_" for ch in st["name"]
    )


def guess(st, uid, text):
    """Returns a dict describing the result of this guess. Ignores guesses after the round ended."""
    if st["done"]:
        return {"k": "over"}
    g = normalize(text)
    if not g:
        return {"k": "ignored"}
    target = normalize(st["name"])
    if len(g) > 1:  # a whole-name guess
        if g == target:
            st["done"], st["won"] = True, True
            st["scores"][uid] = st["scores"].get(uid, 0) + WORD_BONUS
            return {"k": "solved", "uid": uid, "pts": WORD_BONUS}
        st["lives"] -= 1
        return _after_wrong(st, {"k": "wrong_name", "uid": uid})
    letter = g
    if letter in st["guessed"] or letter in st["wrong"]:
        return {"k": "repeat"}
    if letter in target:
        st["guessed"].add(letter)
        st["scores"][uid] = st["scores"].get(uid, 0) + CORRECT_POINTS * target.count(letter)
        if set(target) <= st["guessed"]:
            st["done"], st["won"] = True, True
            return {"k": "solved", "uid": uid, "pts": 0}
        return {"k": "hit", "uid": uid, "letter": letter, "n": target.count(letter)}
    st["wrong"].add(letter)
    st["lives"] -= 1
    return _after_wrong(st, {"k": "miss", "uid": uid, "letter": letter})


def _after_wrong(st, ev):
    if st["lives"] <= 0:
        st["done"], st["won"] = True, False
        ev["lost"] = True
    return ev
