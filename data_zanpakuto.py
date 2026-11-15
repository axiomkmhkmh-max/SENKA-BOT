"""Zanpakutō release stages: each named blade gets its own Shikai and Bankai names and an extra power bonus.

The bonus is added on top of the generic release bonus in service_combat.build_player (Shikai +10%,
Bankai +12% plus mastery), so a blade listed here only changes how its release feels, never the base rules.
Blades not listed keep the generic release. Pure data, no I/O.
"""

BLADE_STAGES = {
    "zangetsu": {"shikai": ("تنسا زانگتسو", "Tensa Zangetsu"), "bankai": ("تنسا زانگتسو (بانکای)", "Tensa Zangetsu (Bankai)"),
                 "shikai_bonus": 0.00, "bankai_bonus": 0.04},
    "senbonzakura": {"shikai": ("سنبون‌زاکورا کاگیوشی", "Senbonzakura Kageyoshi"),
                     "bankai": ("سنبون‌زاکورا کاگیوشی (بانکای)", "Senbonzakura Kageyoshi (Bankai)"),
                     "shikai_bonus": 0.02, "bankai_bonus": 0.05},
    "hyorinmaru": {"shikai": ("هیورین‌مارو", "Hyōrinmaru"), "bankai": ("دایگورن هیورین‌مارو", "Daiguren Hyōrinmaru"),
                   "shikai_bonus": 0.04, "bankai_bonus": 0.07},  # Daiguren: among the strongest Bankai
    "kyoka_suigetsu": {"shikai": ("کیوکا سویگتسو", "Kyōka Suigetsu"), "bankai": ("کیوکا سویگتسو (بانکای)", "Kyōka Suigetsu (Bankai)"),
                       "shikai_bonus": 0.03, "bankai_bonus": 0.05},
    "zanka_no_tachi": {"shikai": ("زانکا نو تاچی", "Zanka no Tachi"), "bankai": ("زانکا نو تاچی (بانکای)", "Zanka no Tachi (Bankai)"),
                       "shikai_bonus": 0.02, "bankai_bonus": 0.06},
    "sode_no_shirayuki": {"shikai": ("سوده نو شیرایوکی", "Sode no Shirayuki"),
                          "bankai": ("سوده نو شیرایوکی (بانکای)", "Sode no Shirayuki (Bankai)"),
                          "shikai_bonus": 0.02, "bankai_bonus": 0.03},
    "zabimaru": {"shikai": ("زابیمارو", "Zabimaru"), "bankai": ("زابیمارو (بانکای)", "Zabimaru (Bankai)"),
                 "shikai_bonus": 0.02, "bankai_bonus": 0.04},
    "wabisuke": {"shikai": ("وابی‌سوکه", "Wabisuke"), "bankai": ("وابی‌سوکه (بانکای)", "Wabisuke (Bankai)"),
                 "shikai_bonus": 0.02, "bankai_bonus": 0.03},
    # ---- roster extension: Shinigami and Visored blades whose owners are confirmed in the Bleach sources
    # (CANON_AUDIT.md). Only the Shikai name is listed; Bankai names are not invented, so these show the generic Bankai.
    "minazuki": {"shikai": ("میناتسوکی", "Minazuki"), "shikai_bonus": 0.03, "bankai_bonus": 0.0},
    "ruri_iro_kujaku": {"shikai": ("روری‌ایرو کوجاکو", "Ruri'iro Kujaku"), "shikai_bonus": 0.02, "bankai_bonus": 0.0},
    "haineko": {"shikai": ("هاینکو", "Haineko"), "shikai_bonus": 0.02, "bankai_bonus": 0.0},
    "nejibana": {"shikai": ("نجی‌بانا", "Nejibana"), "shikai_bonus": 0.02, "bankai_bonus": 0.0},
    "kokujo_tengen_myoo": {"shikai": ("کوکوجو تنگن میوئو", "Kokujō Tengen Myōō"), "shikai_bonus": 0.03, "bankai_bonus": 0.0},
    "tachikaze": {"shikai": ("تاچیکازه", "Tachikaze"), "shikai_bonus": 0.02, "bankai_bonus": 0.0},
    "tengumaru": {"shikai": ("تنگومارو", "Tengumaru"), "shikai_bonus": 0.02, "bankai_bonus": 0.0},
    "haguro_tonbo": {"shikai": ("هاگورو تونبو", "Haguro Tonbo"), "shikai_bonus": 0.02, "bankai_bonus": 0.0},
    "kinshara": {"shikai": ("کینشارا", "Kinshara"), "shikai_bonus": 0.02, "bankai_bonus": 0.0},
    "sakanade": {"shikai": ("ساکانادِه", "Sakanade"), "shikai_bonus": 0.02, "bankai_bonus": 0.0},
    "kubikiri_orochi": {"shikai": ("کوبیکیری اوروچی", "Kubikiri Orochi"), "shikai_bonus": 0.02, "bankai_bonus": 0.0},
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
}

# Combat style per blade (moved from service_combat.build_player; design values, applied on release only).
BLADE_STYLE = {
    "zangetsu": {"dmg": 1.08}, "senbonzakura": {"crit": 0.05},
    "hyorinmaru": {"def": 1.12, "dmg": 1.10}, "kyoka_suigetsu": {"crit": 0.04, "dmg": 1.03},
    "zanka_no_tachi": {"dmg": 1.12}, "sode_no_shirayuki": {"def": 1.05, "kido": 1.08},
    "zabimaru": {"dmg": 1.07}, "wabisuke": {"def": 1.10},
    "minazuki": {"def": 1.06}, "ruri_iro_kujaku": {"crit": 0.04}, "haineko": {"dmg": 1.06},
    "nejibana": {"kido": 1.08}, "kokujo_tengen_myoo": {"dmg": 1.10}, "tachikaze": {"crit": 0.03},
    "tengumaru": {"dmg": 1.05}, "haguro_tonbo": {"crit": 0.05}, "kinshara": {"def": 1.06},
    "sakanade": {"dmg": 1.06, "kido": 1.05}, "kubikiri_orochi": {"dmg": 1.07},
}


def unlocked_blades(level: int):
    """Blade ids a character of this level may choose."""
    return [b for b, gate in BLADE_UNLOCK.items() if int(level) >= gate and b in BLADE_STAGES]


def blade_valid(blade_id, level: int) -> bool:
    return blade_id in BLADE_STAGES and blade_id in unlocked_blades(level)
