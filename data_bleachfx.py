"""Bleach combat-feel pack (pure data + tunables, no I/O).

What it adds to the turn-based engine so a fight *plays* like Bleach instead of reading like it:
  * one signature move per race (Shunpo / Hirenkyaku / Cero / Fullbring strike / Fighting spirit),
  * Kidō chanting (spend a turn to chant, stay open, next spell hits much harder),
  * Resolve: a once-per-battle Reiatsu surge when a fighter is pushed to the edge,
  * named zanpakutō moves (a released heavy strike is called "<blade>: <technique>!"),
  * hollow-type / quincy-type wild enemies use Cero / Hirenkyaku too (telegraphed, so it can be answered).
All numbers live here; change them in one place.
"""
import re

# race -> signature action key. The battle button label comes from locale key a_sg_<key>.
RACE_SIG = {"shinigami": "shunpo", "visored": "shunpo", "quincy": "hiren", "hollow": "cero",
            "arrancar": "cero", "fullbringer": "bring", "human": "guts"}

# cost = share of max Reiatsu, cd = turns before it can be used again
SIG = {
    "shunpo": {"cost": 0.08, "cd": 4},                               # next physical hit on you is dodged + countered
    "hiren": {"cost": 0.10, "cd": 4, "strike": 0.7, "dodge": 0.25, "crit": 0.12, "turns": 2},  # blitz strike + a blur of speed
    # Cero: charge one turn (telegraphed), fire the next. Wild enemies fire a weaker one (ai_*) so it stays answerable.
    "cero": {"cost": 0.12, "cd": 2, "mult": 2.8, "pierce": 0.30, "ai_mult": 2.0, "ai_pierce": 0.15},
    "bring": {"cost": 0.10, "cd": 4, "mult": 1.25, "bleed": 0.4},
    "guts": {"cost": 0.10, "cd": 5, "heal": 0.15, "turns": 2, "dmg": 1.15},
}
# a single hit of at least this share of the charger's max HP breaks a gathered Cero (interrupt it!). Wild enemies break
# more easily than players, so a player's own Cero is a real gamble but not a coin-flip against every normal hit.
CERO_BREAK_AI = 0.22
CERO_BREAK_PLAYER = 0.35
SHUNPO_COUNTER = 0.5      # power of the counter-strike after a Shunpo dodge

CHANT_HADO = 1.6          # damage multiplier of the first Hadō after a chant
CHANT_BAK = 1.5           # shield multiplier of the first Bakudō after a chant
CHANT_OPEN = 1.2          # damage taken multiplier while you stand chanting (until your next turn)

# Resolve: once per battle, human-controlled fighters only. Triggers when a hit leaves HP below `hp` share.
RESOLVE = {"hp": 0.25, "heal": 0.03, "dmg": 1.06, "turns": 3}

# Spirit gauge (روحیه‌ی جنگ). It fills while you trade blows; at `full` the fighter may unleash Bankai (or
# Resurrección for Hollow / Arrancar). The released form lasts `turns` turns. While released and low, the Hollow inside
# can take the wheel: the turn is lost (the lg_mask_lost line), which is the price of the power.
GAUGE = {
    "full": 100,
    "deal": 9,          # gauge gained per hit you land
    "take": 6,          # gauge gained per hit you take ...
    "take_share": 40,   # ... plus this many per 100% of your max HP the hit removed ...
    "take_cap": 12,     # ... capped at this bonus
    "cost": 0.10,       # reiatsu paid to unleash (share of max Reiatsu)
    "strike": 1.15,     # the release is itself a strike (power), so unleashing is never a wasted turn
    "turns": 2,         # actions covered by the released form (after the release strike)
    "dmg": 1.06,        # damage multiplier while released
    "crit": 0.02,       # extra crit chance while released
    "hollow_hp": 0.30,  # below this HP share, a released fighter may lose the turn to the Hollow ...
    "hollow_p": 0.12,   # ... with this chance each turn
}
# Resurrección: the Hollow / Arrancar version of Resolve (same once-per-battle trigger, a stronger surge).
RESURRECCION = {"heal": 0.08, "dmg": 1.15, "turns": 3}
RESURRECCION_RACES = ("hollow", "arrancar")

# weapon_type -> (fa, en) technique word. A released fighter's Heavy strike is called "<blade name>: <word>!".
# (The 120 blades are original ids wp_001..wp_120, so the technique is named after the type, not a canon blade id.)
TYPE_MOVES = {
    "melee": ("زانپا", "Zanpa"), "elemental": ("گوکا", "Gōka"), "kido": ("شینپان", "Shinpan"),
    "illusion": ("گن‌ئی", "Gen'ei"), "living": ("هوکو", "Hōkō"), "defensive": ("تپکی", "Teppeki"),
    "ranged": ("سنکو", "Senkō"), "speed": ("رانبو", "Ranbu"), "hybrid": ("کیوگکی", "Kyōgeki"),
}

_HOLLOW_RE = re.compile(r"hollow|menos|gillian|adjuchas|vasto|masked|هالو|منوس|جیلیان|ماسک", re.I)


def enemy_sig(loc_race, names) -> str:
    """Signature a wild enemy uses. `names` = the (fa, en) pair picked for the encounter. None = plain fighter."""
    if loc_race == "hollow" or any(_HOLLOW_RE.search(n or "") for n in names):
        return "cero"
    if loc_race == "quincy":
        return "hiren"
    return None


def sig_for(race) -> str:
    return RACE_SIG.get(race)


def move_name(blade_id, lang) -> str:
    """"<blade name>: <technique word>" for a weapon item id, or "" when the id is not a known weapon."""
    from data_items import ALL, iname
    w = ALL.get(blade_id or "")
    if not w or w.get("category") != "weapon":
        return ""
    term = TYPE_MOVES.get(w.get("weapon_type"), TYPE_MOVES["melee"])
    return f"{iname(blade_id, lang)}: {term[0 if lang == 'fa' else 1]}"


# ---- SENKA+ : canon race killers and Konpaku (PvP only) ----
# attacker race -> {defender race: damage multiplier}. Applied in engine._deal, so it works in every fight.
RACE_KILLER = {
    "quincy": {"hollow": 1.08, "arrancar": 1.08},       # Quincy were made to hunt Hollows
    "shinigami": {"hollow": 1.05, "arrancar": 1.05},    # Soul Reapers purify Hollows
    "visored": {"hollow": 1.06, "arrancar": 1.06},      # Visored carry Hollow power and know its weak spots
    "fullbringer": {"hollow": 1.04},
    "hollow": {"shinigami": 1.04, "visored": 1.04, "quincy": 1.04},   # Hollows hunger for Reapers' souls
    "arrancar": {"shinigami": 1.04, "visored": 1.04, "quincy": 1.04},
}
# Konpaku: in duels (pvp) each fighter gets `lives` extra lives. Falling to 0 HP pulls the soul back once,
# at `hp` share of max HP. PvE is untouched. Tune here (one file).
KONPAKU = {"lives": 1, "hp": 0.35}
