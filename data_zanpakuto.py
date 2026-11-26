"""Zanpakutō release stages and blade-specific combat identities.

The bonus is added on top of the generic release bonus in service_combat.build_player (Shikai +10%,
Bankai +12% plus mastery). Selected signature blades can also receive bespoke combat modifiers there.
Blades not listed keep the generic release. Pure data, no I/O.
"""

BLADE_STAGES = {
    "zangetsu": {"shikai": ("زانگتسو", "Zangetsu"), "bankai": ("تنسا زانگتسو", "Tensa Zangetsu"),
                 "shikai_bonus": 0.00, "bankai_bonus": 0.04},
    "senbonzakura": {"shikai": ("سنبون‌زاکورا", "Senbonzakura"),
                     "bankai": ("سنبون‌زاکورا کاگیوشی", "Senbonzakura Kageyoshi"),
                     "shikai_bonus": 0.02, "bankai_bonus": 0.05},
    "hyorinmaru": {"shikai": ("هیورین‌مارو", "Hyōrinmaru"), "bankai": ("دایگورن هیورین‌مارو", "Daiguren Hyōrinmaru"),
                   "shikai_bonus": 0.08, "bankai_bonus": 0.12},  # Daiguren: among the strongest Bankai
    "kyoka_suigetsu": {"shikai": ("کیوکا سویگتسو", "Kyōka Suigetsu"), "bankai": ("کیوکا سویگتسو (بانکای)", "Kyōka Suigetsu (Bankai)"),
                       "shikai_bonus": 0.22, "bankai_bonus": 0.35},
    "zanka_no_tachi": {"shikai": ("ریوجین جاکا", "Ryūjin Jakka"), "bankai": ("زانکا نو تاچی", "Zanka no Tachi"),
                       "shikai_bonus": 0.02, "bankai_bonus": 0.06},
    "sode_no_shirayuki": {"shikai": ("سوده نو شیرایوکی", "Sode no Shirayuki"),
                          "bankai": ("هاکا نو توگامه", "Hakka no Togame"),
                          "shikai_bonus": 0.02, "bankai_bonus": 0.03},
    "zabimaru": {"shikai": ("زابیمارو", "Zabimaru"), "bankai": ("هیهیئو زابیمارو", "Hihiō Zabimaru"),
                 "shikai_bonus": 0.02, "bankai_bonus": 0.04},
    "wabisuke": {"shikai": ("وابی‌سوکه", "Wabisuke"), "bankai": ("وابی‌سوکه (بانکای)", "Wabisuke (Bankai)"),
                 "shikai_bonus": 0.02, "bankai_bonus": 0.03},
    # ---- roster extension: Shinigami and Visored blades whose owners are confirmed in the Bleach sources
    # (CANON_AUDIT.md). A Bankai name is listed only when the source names it (Pack 1: Tenken/Kokujō, Kinshara Butōdan,
    # Sakashima Yokoshima Happō Fusagari, Minazuki); the rest show the generic Bankai. Display names only: ids never change.
    "minazuki": {"shikai": ("مینازوکی", "Minazuki"), "bankai": ("مینازوکی (بانکای)", "Minazuki (Bankai)"), "shikai_bonus": 0.03, "bankai_bonus": 0.0},
    "ruri_iro_kujaku": {"shikai": ("روری‌ایرو کوجاکو", "Ruri'iro Kujaku"), "shikai_bonus": 0.02, "bankai_bonus": 0.0},
    "haineko": {"shikai": ("هاینکو", "Haineko"), "shikai_bonus": 0.02, "bankai_bonus": 0.0},
    "nejibana": {"shikai": ("نجی‌بانا", "Nejibana"), "shikai_bonus": 0.02, "bankai_bonus": 0.0},
    "kokujo_tengen_myoo": {"shikai": ("تنکن", "Tenken"), "bankai": ("کوکوجو تنگن میوئو", "Kokujō Tengen Myōō"), "shikai_bonus": 0.03, "bankai_bonus": 0.0},
    "tachikaze": {"shikai": ("تاچیکازه", "Tachikaze"), "shikai_bonus": 0.02, "bankai_bonus": 0.0},
    "tengumaru": {"shikai": ("تنگومارو", "Tengumaru"), "shikai_bonus": 0.02, "bankai_bonus": 0.0},
    "haguro_tonbo": {"shikai": ("هاگورو تونبو", "Haguro Tonbo"), "shikai_bonus": 0.02, "bankai_bonus": 0.0},
    "kinshara": {"shikai": ("کینشارا", "Kinshara"), "bankai": ("کینشارا بوتودان", "Kinshara Butōdan"), "shikai_bonus": 0.02, "bankai_bonus": 0.0},
    "sakanade": {"shikai": ("ساکانادِه", "Sakanade"), "bankai": ("ساکاشیما یوکوشیما هاپو فوساگاری", "Sakashima Yokoshima Happō Fusagari"), "shikai_bonus": 0.02, "bankai_bonus": 0.0},
    "kubikiri_orochi": {"shikai": ("کوبیکیری اوروچی", "Kubikiri Orochi"), "shikai_bonus": 0.02, "bankai_bonus": 0.0},
    # ---- Nov 26: blades with real kits. Benihime has TWO shikai uses (attack / defence), Katen Kyōkotsu is a pair of blades.
    "benihime": {"shikai": ("بنی‌هیمه", "Benihime"), "bankai": ("کانون‌بیراکی بنی‌هیمه آراتامه", "Kannonbiraki Benihime Aratame"),
                 "shikai_bonus": 0.03, "bankai_bonus": 0.04},
    "katen_kyokotsu": {"shikai": ("کاتن کیوکوتسو", "Katen Kyōkotsu"), "bankai": ("کاتن کیوکوتسو: کاراماتسو شینجو", "Katen Kyōkotsu: Karamatsu Shinjū"),
                       "shikai_bonus": 0.04, "bankai_bonus": 0.05},
}


def stage_name(blade_id, stage, lang):
    """Display name of a release stage ('shikai' or 'bankai'), or None for blades without a custom stage."""
    s = BLADE_STAGES.get(blade_id)
    if not s or stage not in s:
        return None
    return s[stage][0 if lang == "fa" else 1]


# Each blade opens at a character level (its unlock gate). The weapon in hand plays no part in this choice.
# Gates are design values, not canon; the Shikai order follows the source's arc order.
BLADE_UNLOCK = {
    "zangetsu": 1, "kubikiri_orochi": 20, "senbonzakura": 20, "hyorinmaru": 25, "tengumaru": 25, "tachikaze": 25,
    "zabimaru": 30, "wabisuke": 30, "haguro_tonbo": 30, "kinshara": 30, "sode_no_shirayuki": 35,
    "ruri_iro_kujaku": 35, "nejibana": 35, "sakanade": 40, "zanka_no_tachi": 40, "kyoka_suigetsu": 45,
    "minazuki": 45, "haineko": 45, "kokujo_tengen_myoo": 60,
    "benihime": 50, "katen_kyokotsu": 55,
}

# Combat style per blade (moved from service_combat.build_player; design values, applied on release only).
BLADE_STYLE = {
    "zangetsu": {"dmg": 1.08}, "senbonzakura": {"crit": 0.05},
    "hyorinmaru": {"def": 1.12, "dmg": 1.15}, "kyoka_suigetsu": {"crit": 0.04, "dmg": 1.03},
    "zanka_no_tachi": {"dmg": 1.12}, "sode_no_shirayuki": {"def": 1.05, "kido": 1.08},
    "zabimaru": {"dmg": 1.07}, "wabisuke": {"def": 1.10},
    "minazuki": {"def": 1.06}, "ruri_iro_kujaku": {"crit": 0.04}, "haineko": {"dmg": 1.06},
    "nejibana": {"kido": 1.08}, "kokujo_tengen_myoo": {"dmg": 1.10}, "tachikaze": {"crit": 0.03},
    "tengumaru": {"dmg": 1.05}, "haguro_tonbo": {"crit": 0.05}, "kinshara": {"def": 1.06},
    "sakanade": {"dmg": 1.06, "kido": 1.05}, "kubikiri_orochi": {"dmg": 1.07},
    "benihime": {"def": 1.08, "kido": 1.06}, "katen_kyokotsu": {"dmg": 1.08, "crit": 0.03},
}


# Release commands (kaigo) as spoken in the source. Only canon commands are listed; other blades use a race line.
RELEASE_CALL = {
    "senbonzakura": ("پراکنده شو، سنبون‌زاکورا!", "Scatter, Senbonzakura!"),
    "hyorinmaru": ("بر آسمانِ یخ‌زده بنشین، هیورین‌مارو!", "Sit upon the frozen heavens, Hyōrinmaru!"),
    "kyoka_suigetsu": ("درهم بشکن، کیوکا سویگتسو!", "Shatter, Kyōka Suigetsu!"),
    "zanka_no_tachi": ("همه‌ی آفرینش را به خاکستر بدل کن، ریوجین جاکا!", "Reduce all creation to ash, Ryūjin Jakka!"),
    "sode_no_shirayuki": ("برقص، سوده نو شیرایوکی!", "Dance, Sode no Shirayuki!"),
    "zabimaru": ("زوزه بکش، زابیمارو!", "Howl, Zabimaru!"),
    "wabisuke": ("سرت را بالا بگیر، وابی‌سوکه!", "Raise your head, Wabisuke!"),
    "haineko": ("بغُر، هاینکو!", "Growl, Haineko!"),
    "ruri_iro_kujaku": ("شکوفه کن، روری‌ایرو کوجاکو!", "Bloom, Ruri'iro Kujaku!"),
    "nejibana": ("دریاها و آسمان‌ها را طوفانی کن، نجی‌بانا!", "Flood the seas and the heavens, Nejibana!"),
    "kokujo_tengen_myoo": ("بخروش، تنکن!", "Roar, Tenken!"),
    "kinshara": ("بنواز، کینشارا!", "Play, Kinshara!"),
    "sakanade": ("فرو بیفت، ساکانادِه!", "Collapse, Sakanade!"),
    "benihime": ("گریه کن، بنی‌هیمه!", "Cry, Benihime!"),
    "katen_kyokotsu": ("بازی کنیم، کاتن کیوکوتسو!", "Let's play, Katen Kyōkotsu!"),
}


def release_call(blade_id, lang, stage="shikai"):
    """The spoken release line: the canon Shikai command, or 'Bankai! <name>' for the second form. None if unknown."""
    if stage == "bankai":
        name = stage_name(blade_id, "bankai", lang)
        return (f"بانکای! {name}!" if lang == "fa" else f"Bankai! {name}!") if name else None
    c = RELEASE_CALL.get(blade_id)
    return c[0 if lang == "fa" else 1] if c else None


# ---- Beta blades (Nov 26) ----
# New blades with real kits are open to EVERY player at any level while they are tested: players use them and report
# problems. When a blade is stable, remove its id from BETA_BLADES (it falls back to its level gate above) or lock it to
# the owner live with /znplock (znp_lock.py). Weak, plain blades are never locked.
BETA_BLADES = {"benihime", "katen_kyokotsu"}

# ---- Rarity tiers: shown in the blade picker (best first). 5 = mythic ... 1 = common. ----
TIER_NAMES = {5: ("🔴", "اسطوره‌ای", "Mythic"), 4: ("🟠", "افسانه‌ای", "Legendary"), 3: ("🟣", "حماسی", "Epic"),
              2: ("🔵", "کمیاب", "Rare"), 1: ("⚪", "معمولی", "Common")}
BLADE_TIER = {
    "kyoka_suigetsu": 5, "hyorinmaru": 5,
    "zangetsu": 4, "zanka_no_tachi": 4, "kokujo_tengen_myoo": 4, "benihime": 4,
    "senbonzakura": 3, "sode_no_shirayuki": 3, "zabimaru": 3, "katen_kyokotsu": 3, "minazuki": 3, "nejibana": 3,
    "wabisuke": 2, "haineko": 2, "sakanade": 2, "kinshara": 2, "ruri_iro_kujaku": 2,
    "kubikiri_orochi": 1, "tengumaru": 1, "tachikaze": 1, "haguro_tonbo": 1,
}


def blade_tier(blade_id: str) -> int:
    return BLADE_TIER.get(blade_id, 1)


def tier_label(blade_id: str, lang: str) -> str:
    emoji, fa, en = TIER_NAMES[blade_tier(blade_id)]
    return f"{emoji} {fa if lang == 'fa' else en}"


def unlocked_blades(level: int):
    """Blade ids a character of this level may choose (beta blades are open to everyone), best tier first."""
    ids = [b for b, gate in BLADE_UNLOCK.items()
           if (int(level) >= gate or (b in BETA_BLADES and int(level) >= 1)) and b in BLADE_STAGES]
    return sorted(ids, key=lambda b: -blade_tier(b))  # sorted() is stable: equal tiers keep the unlock order


def blade_valid(blade_id, level: int) -> bool:
    return blade_id in BLADE_STAGES and blade_id in unlocked_blades(level)


# ---- Bond key: the bond belongs to the blade. ----
# Bond used to be keyed by the weapon in hand, so taking the weapon out (or fighting bare-handed) dropped the bond
# to 0 and the Shikai / Bankai power and unlock checks with it. Now the chosen blade holds the bond. A character who
# never chose a blade keeps the old weapon key, so nothing already earned is lost.
def bond_key(ch: dict) -> str:
    """The `bond` dict key this character's bond is read from and written to."""
    blade = (ch.get("zanpakuto") or {}).get("blade_id")
    if blade:
        return blade
    from data_raceweapons import parse_rw, rw_base
    p = parse_rw(ch.get("weapon_id"))
    if p:  # a race weapon keeps one bond through every colour (rw_<race>_<nn>)
        return rw_base(p[0], p[1])
    return ch.get("weapon_id") or "none"


def bond_value(ch: dict) -> int:
    return int((ch.get("bond") or {}).get(bond_key(ch), 0))


# ---- Blade techniques: the blade you choose gives you its own attack (after Shikai). ----
# kind: pierce (ignores part of the armour), bleed (wound that keeps hurting), twin (two quick cuts),
# heavy (a single heavier cut). The kind per blade is a design choice, not canon.
BLADE_TECH_KINDS = {
    "pierce": {"fa": "ضربه‌ی نفوذی", "en": "Piercing cut", "mult": 1.70, "pierce": 0.35},
    "bleed": {"fa": "ضربه‌ی خون‌ریز", "en": "Bleeding cut", "mult": 1.50, "bleed": True},
    "twin": {"fa": "ضربه‌ی دوگانه", "en": "Twin cut", "mult": 1.00, "twice": True},
    "heavy": {"fa": "ضربه‌ی سنگین", "en": "Heavy cut", "mult": 1.90},
}
BLADE_TECH = {
    "zangetsu": "twin", "senbonzakura": "heavy", "hyorinmaru": "pierce", "kyoka_suigetsu": "heavy",
    "zanka_no_tachi": "bleed", "sode_no_shirayuki": "pierce", "zabimaru": "bleed", "wabisuke": "twin",
    "minazuki": "bleed", "ruri_iro_kujaku": "heavy", "haineko": "twin", "nejibana": "pierce",
    "kokujo_tengen_myoo": "pierce", "tachikaze": "bleed", "tengumaru": "heavy", "haguro_tonbo": "twin",
    "kinshara": "bleed", "sakanade": "pierce", "kubikiri_orochi": "heavy",
    "benihime": "pierce", "katen_kyokotsu": "twin",  # Benihime: the attack mode (Akahime-style red blast); its defence mode is the finisher slot below
}
BLADE_TECH_COST = {"cost": 0.09, "cd": 3}


# Owner blades can be stronger than the common ones. Hyōrinmaru: a stronger technique (see znp_lock for the lock).
BLADE_TECH_OVERRIDE = {"hyorinmaru": {"mult": 2.10, "pierce": 0.50, "cd": 2}}


def blade_technique(blade_id: str):
    """{'kind', 'fa', 'en', ...} for a blade's technique, or None for a blade without one."""
    kind = BLADE_TECH.get(blade_id)
    if not kind:
        return None
    stage = BLADE_STAGES.get(blade_id, {}).get("shikai") or (blade_id, blade_id)
    return {"kind": kind, **BLADE_TECH_KINDS[kind], **BLADE_TECH_COST, **BLADE_TECH_OVERRIDE.get(blade_id, {}),
            "blade_fa": stage[0], "blade_en": stage[1]}


# ---- Blade ultimates: every blade's finishing technique (after Shikai), one per blade, own cost / cooldown. ----
# mult: power of the blow (x the ability formula), hits: number of cuts, pierce: share of armour ignored,
# fx: status on the foe (bleed / burn / weaken / skip = loses its next turn, with `skip_p` chance),
# buff: (turns, dmg multiplier) on the wielder. Kyōka Suigetsu keeps its own five-ability kit (engine ks1..ks5).
BLADE_ULT = {
    "zangetsu": {"fa": "گتسوگا تنشو", "en": "Getsuga Tenshō", "mult": 5.2, "pierce": 0.30, "buff": (2, 1.25), "cd": 5},
    "senbonzakura": {"fa": "کاگیوشی سنبونزاکورا", "en": "Senkei Senbonzakura", "mult": 4.6, "pierce": 0.45, "fx": "bleed", "cd": 5},
    "hyorinmaru": {"fa": "ریوسنکا", "en": "Ryūsenka", "mult": 5.0, "pierce": 0.45, "fx": "skip", "skip_p": 0.55, "cd": 5},
    "zanka_no_tachi": {"fa": "ریوجین جاکا: ملتهب", "en": "Ryūjin Jakka: Scorch", "mult": 5.6, "pierce": 0.25, "fx": "burn", "cd": 5},
    "sode_no_shirayuki": {"fa": "تسوگی نو مای: هاکورن", "en": "Tsugi no Mai: Hakuren", "mult": 4.2, "pierce": 0.35, "fx": "skip", "skip_p": 0.5, "cd": 5},
    "zabimaru": {"fa": "هیهیو زابیمارو", "en": "Hihiō Zabimaru", "mult": 5.0, "pierce": 0.30, "fx": "bleed", "cd": 5},
    "wabisuke": {"fa": "وابیسوکه: وزن دوچندان", "en": "Wabisuke: Doubled Weight", "mult": 3.6, "pierce": 0.30, "fx": "weaken", "cd": 4},
    "haineko": {"fa": "هاینکو: خاکستر خفه‌کننده", "en": "Haineko: Choking Ash", "mult": 4.4, "pierce": 0.40, "fx": "weaken", "cd": 5},
    "minazuki": {"fa": "مینازوکی: تیغه‌ی شفابخش", "en": "Minazuki: Bleeding Moon", "mult": 4.8, "pierce": 0.30, "fx": "bleed", "cd": 5},
    # Nov 26: Benihime's second use is DEFENCE: a barrier and a mend instead of a big blow (shield / heal = share of the old HP pool).
    "benihime": {"fa": "بنی‌هیمه: سد سرخ", "en": "Benihime: Crimson Ward", "mult": 1.8, "pierce": 0.20, "shield": 0.30, "heal": 0.10, "cd": 4, "cost": 0.20},
    "katen_kyokotsu": {"fa": "کاتن کیوکوتسو: دو شمشیر، یک بازی", "en": "Katen Kyōkotsu: Two Blades, One Game", "mult": 2.4, "hits": 3, "pierce": 0.25, "fx": "weaken", "cd": 5},
}
BLADE_ULT_KIND = {  # a blade without its own entry gets a finisher from its technique kind
    "pierce": {"mult": 4.4, "pierce": 0.50, "cd": 5}, "bleed": {"mult": 4.6, "pierce": 0.30, "fx": "bleed", "cd": 5},
    "twin": {"mult": 2.6, "hits": 2, "pierce": 0.25, "cd": 5}, "heavy": {"mult": 5.4, "pierce": 0.30, "cd": 5},
}
BLADE_ULT_COST = 0.25


def blade_ultimate(blade_id: str):
    """The blade's finishing technique, or None (no blade, or Kyōka Suigetsu which has its own kit)."""
    if not blade_id or blade_id == "kyoka_suigetsu":
        return None
    spec = BLADE_ULT.get(blade_id)
    if spec is None:
        kind = BLADE_TECH.get(blade_id)
        if not kind:
            return None
        stage = BLADE_STAGES.get(blade_id, {}).get("shikai") or (blade_id, blade_id)
        spec = dict(BLADE_ULT_KIND[kind], fa=f"رهایی نهایی {stage[0]}", en=f"Final Release: {stage[1]}")
    return {"hits": 1, "cost": BLADE_ULT_COST, **spec}
