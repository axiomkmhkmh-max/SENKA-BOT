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
                   "shikai_bonus": 0.02, "bankai_bonus": 0.04},
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
}


def stage_name(blade_id, stage, lang):
    """Display name of a release stage ('shikai' or 'bankai'), or None for blades without a custom stage."""
    s = BLADE_STAGES.get(blade_id)
    if not s or stage not in s:
        return None
    return s[stage][0 if lang == "fa" else 1]
