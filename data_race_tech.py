"""Canon race techniques (engine actions t1, t2, t3) so every race has as many anime moves as the Shinigami.

Shinigami already have Kidō, Getsuga, Shunpo, Shikai/Bankai and their blade's technique, so they get none here.
Every technique is open from level 1 (`unlock` stays 0; evolution gives power bonuses only) and has its own cost
(share of max Reiatsu) and cooldown (own turns). Race technique cards raise its mastery (data_racegear). Kinds the engine knows:
  strike  mult (power), hits (split into that many blows), pierce, lifesteal (share of damage healed),
          fx (status on the target: bleed / weaken / skip) with fx_p (chance)
  shield  shield (share of max HP)
  heal    heal (share of max HP), cleanse (removes bleed / burn / poison / fear / weaken / shock)
  buff    dmg (damage multiplier), crit (+chance), guard (damage taken multiplier), turns
  blur    turns of Hirenkyaku-like speed (dodge + crit, the same as the Quincy signature) plus a quick strike `mult`
need_form: only while a form (Hollow Mask for the Visored) is active.
Pure data, no I/O.
"""

TECH_SLOTS = ("t1", "t2", "t3")

# ---- what each race's abilities draw their power from (engine._deal, src="abl") -------------------------------------
# Abilities (signature, race techniques, Getsuga, blade technique, release strike, Bala, general strike...) take
# ABILITY_SHARE of their stat part from the race's own stat and the rest from Zanjutsu (with the bond); the weapon's
# attack is added as for any blade hit. Fullbringer draws on the soul of the object instead: the weapon's attack
# counts FULLBRING_WEAPON times, on top of a full Zanjutsu part. A plain attack uses Zanjutsu only (with the weapon);
# a heavy strike uses Zanjutsu and Reiatsu half and half (with the weapon). Wild enemies keep the plain formula.
ABILITY_STAT = {"shinigami": "kido", "quincy": "reiatsu", "visored": "reiatsu", "human": "reiatsu",
                "arrancar": "hoho", "hollow": "hakuda", "fullbringer": "weapon"}
ABILITY_SHARE = 0.70
HEAVY_REIATSU = 0.50
FULLBRING_WEAPON = 2.0
STAT_FA = {"kido": "کیدو", "reiatsu": "ریاتسو", "hoho": "هوهو", "hakuda": "هاکودا", "zanjutsu": "زنجوتسو", "weapon": "قدرت سلاح"}

RACE_TECH = {
    "quincy": {
        "t1": {"id": "licht_regen", "kind": "strike", "mult": 0.32, "hits": 4, "cost": 0.12, "cd": 4, "unlock": 0,
               "name": ("لیشت رگن", "Licht Regen"), "icon": "🏹"},
        "t2": {"id": "seele_schneider", "kind": "strike", "mult": 1.35, "pierce": 0.40, "cost": 0.10, "cd": 4, "unlock": 0,
               "name": ("زیله اشنایدر", "Seele Schneider"), "icon": "🗡"},
        "t3": {"id": "ginto_gritz", "kind": "strike", "mult": 1.30, "fx": "skip", "fx_p": 0.5, "cost": 0.14, "cd": 5, "unlock": 0,
               "name": ("گینتو: گریتس", "Gintō: Gritz"), "icon": "🧪"},
    },
    "hollow": {
        "t1": {"id": "devour", "kind": "strike", "mult": 1.25, "lifesteal": 0.35, "cost": 0.10, "cd": 4, "unlock": 0,
               "name": ("بلعیدن", "Devour"), "icon": "🦷"},
        "t2": {"id": "regeneration", "kind": "heal", "heal": 0.12, "cost": 0.12, "cd": 6, "unlock": 0,
               "name": ("بازسازی سریع", "High-Speed Regeneration"), "icon": "🦎"},
        "t3": {"id": "pesquisa_h", "kind": "buff", "crit": 0.20, "dmg": 1.10, "turns": 3, "cost": 0.06, "cd": 5, "unlock": 0,
               "name": ("پسکیسا", "Pesquisa"), "icon": "📡"},
    },
    "arrancar": {
        "t1": {"id": "hierro", "kind": "buff", "guard": 0.65, "dmg": 1.10, "turns": 3, "cost": 0.08, "cd": 5, "unlock": 0,
               "name": ("هیرو", "Hierro"), "icon": "🪨"},
        "t2": {"id": "pesquisa_a", "kind": "buff", "crit": 0.25, "dmg": 1.15, "turns": 3, "cost": 0.06, "cd": 5, "unlock": 0,
               "name": ("پسکیسا", "Pesquisa"), "icon": "📡"},
        "t3": {"id": "cero_oscuras", "kind": "strike", "mult": 2.60, "pierce": 0.35, "cost": 0.22, "cd": 5, "unlock": 0,
               "name": ("سرو اسکوراس", "Cero Oscuras"), "icon": "🌑"},
    },
    "fullbringer": {
        "t1": {"id": "bringer_light", "kind": "blur", "mult": 0.90, "turns": 2, "cost": 0.08, "cd": 4, "unlock": 0,
               "name": ("براینگر لایت", "Bringer Light"), "icon": "💫"},
        "t2": {"id": "book_of_the_end", "kind": "strike", "mult": 1.40, "fx": "weaken", "fx_p": 1.0, "cost": 0.10, "cd": 4, "unlock": 0,
               "name": ("کتاب پایان", "Book of the End"), "icon": "📖"},
        "t3": {"id": "time_tells_no_lies", "kind": "strike", "mult": 0.80, "fx": "skip", "fx_p": 0.70, "cost": 0.12, "cd": 5, "unlock": 0,
               "name": ("زمان دروغ نمی‌گوید", "Time Tells No Lies"), "icon": "⏳"},
    },
    "human": {
        "t1": {"id": "santen_kesshun", "kind": "shield", "shield": 0.14, "cost": 0.10, "cd": 5, "unlock": 0,
               "name": ("سانتن کسشون", "Santen Kesshun"), "icon": "🔰"},
        "t2": {"id": "soten_kisshun", "kind": "heal", "heal": 0.12, "cleanse": True, "cost": 0.14, "cd": 6, "unlock": 0,
               "name": ("سوتن کیشون", "Sōten Kisshun"), "icon": "🌸"},
        "t3": {"id": "koten_zanshun", "kind": "strike", "mult": 1.50, "pierce": 0.25, "cost": 0.12, "cd": 4, "unlock": 0,
               "name": ("کوتن زانشون", "Koten Zanshun"), "icon": "✨"},
    },
    "visored": {
        "t1": {"id": "mask_strike", "kind": "strike", "mult": 2.20, "pierce": 0.20, "cost": 0.10, "cd": 3, "unlock": 0,
               "need_form": True, "name": ("ضربه‌ی ماسک", "Mask Strike"), "icon": "🎭"},
    },
}


def tech_of(race: str, slot: str):
    return (RACE_TECH.get(race) or {}).get(slot)


def tech_name(tech: dict, lang: str) -> str:
    return f"{tech['icon']} {tech['name'][0 if lang == 'fa' else 1]}"
