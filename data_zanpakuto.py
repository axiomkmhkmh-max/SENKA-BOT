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
                       "shikai_bonus": 0.10, "bankai_bonus": 0.40},  # Nov 27: the strongest Bankai in the game (was 0.02 / 0.06)
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
                 "shikai_bonus": 0.10, "bankai_bonus": 0.12},  # was 0.03 / 0.04: far below every other Legendary blade
    "katen_kyokotsu": {"shikai": ("کاتن کیوکوتسو", "Katen Kyōkotsu"), "bankai": ("کاتن کیوکوتسو: کاراماتسو شینجو", "Katen Kyōkotsu: Karamatsu Shinjū"),
                       "shikai_bonus": 0.10, "bankai_bonus": 0.28},  # Nov 27: Mythic (was 0.04 / 0.05)
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
    "zanka_no_tachi": {"dmg": 1.25, "crit": 0.05}, "sode_no_shirayuki": {"def": 1.05, "kido": 1.08},
    "zabimaru": {"dmg": 1.07}, "wabisuke": {"def": 1.10},
    "minazuki": {"def": 1.06}, "ruri_iro_kujaku": {"crit": 0.04}, "haineko": {"dmg": 1.06},
    "nejibana": {"kido": 1.08}, "kokujo_tengen_myoo": {"dmg": 1.10}, "tachikaze": {"crit": 0.03},
    "tengumaru": {"dmg": 1.05}, "haguro_tonbo": {"crit": 0.05}, "kinshara": {"def": 1.06},
    "sakanade": {"dmg": 1.06, "kido": 1.05}, "kubikiri_orochi": {"dmg": 1.07},
    "benihime": {"def": 1.10, "dmg": 1.08, "kido": 1.06}, "katen_kyokotsu": {"dmg": 1.16, "crit": 0.05},
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


# ---- Blade abilities in a fight (Nov 27) ----
# The technique / finisher buttons used to need the PROFILE Shikai (level 20 + bond 50 unlocked in the Zanpakutō panel), while the
# in-fight 🗡 Shikai button opens at level 10 with no such unlock: a player who pressed Shikai in a fight and chose a blade still saw
# no ability buttons. Now a chosen blade is enough (the in-fight Shikai gate in engine.gate_ok is unchanged). Set True to restore the old rule.
ABILITIES_NEED_PROFILE_SHIKAI = False


def abilities_open(zstate: dict) -> bool:
    """Does this Zanpakutō state put the blade's technique and finisher on the fighter?"""
    if not (zstate or {}).get("blade_id"):
        return False
    return bool(zstate.get("shikai")) if ABILITIES_NEED_PROFILE_SHIKAI else True


# ---- Bankai activation scenes (Nov 27) ----
# What the screen says when a Bankai is unleashed: the shout «Bankai!!! <name>» and a short epic line. {a} = the wielder,
# {d} = the opponent. Every blade has its own line; a blade without one gets a generic scene (BANKAI_GENERIC).
BANKAI_SCENE = {
    "zanka_no_tachi": (
        "🔥 آسمان و زمین شعله کشید؛ همه‌جا خاکستر شد و {d} زیر خورشید یاماموتو خشکش زد!\n⚠️ بانکای ممنوعه: اگه نیم‌ساعت بمونه، یه جهان رو نابود می‌کنه.",
        "🔥 Heaven and earth ignite; everything is ash, and {d} freezes beneath Yamamoto's sun!\n⚠️ The forbidden Bankai: let it burn for half an hour and a whole world is gone."),
    "katen_kyokotsu": (
        "🎭 سایه‌ی غول‌آسای کاراماتسو بالای سر {d} سبز شد؛ بازی بچگونه تموم شد، حالا بازی بزرگ‌ها شروع میشه!",
        "🎭 The towering shadow of Karamatsu rises over {d}; the children's game is over, the grown-ups' game begins!"),
    "zangetsu": (
        "⚫ همه‌ی قدرت یه شمشیر تو یه تیغه‌ی سیاه جمع شد؛ سرعت {a} از چشم {d} هم گذشت!",
        "⚫ The power of a thousand blades folds into one black edge; {a} is faster than {d}'s eyes can follow!"),
    "senbonzakura": (
        "🌸 هزار تیغه‌ی صورتی بیدار شد؛ {d} وسط بهارِ مرگ گم شد!",
        "🌸 A thousand pink blades wake; {d} is lost in a spring of death!"),
    "hyorinmaru": (
        "🐉 آسمون یخ بست؛ اژدهای یخی بالای سر {d} غرید و زمان همون‌جا ایستاد!",
        "🐉 The sky freezes; the ice dragon roars over {d} and time itself stands still!"),
    "kyoka_suigetsu": (
        "🪞 هیچی اون‌جوری نیست که {d} می‌بینه؛ از همون لحظه‌ی اول فریب خورده بود!",
        "🪞 Nothing is as {d} sees it; they were deceived from the very first moment!"),
    "sode_no_shirayuki": (
        "❄️ سفیدترین زمستونِ دنیا نازل شد؛ {d} تا بفهمه چی شده، یخ زده بود!",
        "❄️ The whitest winter in the world descends; {d} was frozen before they understood!"),
    "zabimaru": (
        "🐍 مار و میمون یکی شدن؛ بدنِ غول‌آسای زابیمارو {d} رو زیر سایه‌اش بلعید!",
        "🐍 Snake and baboon become one; Zabimaru's colossal body swallows {d} whole in its shadow!"),
    "wabisuke": (
        "⚖️ هر ضربه سنگین‌تر از قبلی؛ {d} زیر بار پشیمونی زانو زد!",
        "⚖️ Every blow heavier than the last; {d} kneels beneath the weight of regret!"),
    "minazuki": (
        "🌙 ماهِ خونین بالا اومد؛ مرگبارترین تیغه‌ی شفابخش روی {d} باز شد!",
        "🌙 The blood moon rises; the deadliest healing blade opens over {d}!"),
    "kokujo_tengen_myoo": (
        "🗿 غول زره‌پوش برخاست؛ {d} قبل از اولین ضربه، سایه‌ی پولادینش رو روی خودش دید!",
        "🗿 The armoured giant rises; {d} sees its steel shadow fall before the first blow lands!"),
    "kinshara": (
        "🎶 رقص طلایی شروع شد؛ هر نُت یه ضربه‌ست و {d} باید همه‌شون رو بشنوه!",
        "🎶 The golden dance begins; every note is a blow, and {d} must hear every one!"),
    "sakanade": (
        "🌀 دنیا وارونه شد؛ بالا و پایین برای {d} دیگه معنی نداره!",
        "🌀 The world turns upside down; up and down no longer mean anything to {d}!"),
    "benihime": (
        "🩸 دروازه‌ی کانون باز شد؛ هر چی شکسته بود دوباره ساخته شد و {d} فقط تماشا کرد!",
        "🩸 The gate of Kannon opens; everything broken is made anew while {d} can only watch!"),
}
BANKAI_GENERIC = [
    ("⚡ ریاتسوی {a} از مرز گذشت؛ {name} به اوج رسید و {d} زیر فشارش زانو زد!",
     "⚡ {a}'s reiatsu breaks every limit; {name} reaches its peak and {d} drops to one knee under the pressure!"),
    ("🌩 زمین لرزید؛ شکل واقعیِ {name} آزاد شد و {d} فهمید با چی طرفه!",
     "🌩 The ground shakes; the true form of {name} is loose and {d} finally knows what they face!"),
]
BANKAI_DEFAULT_FOE = ("حریف", "the foe")


def bankai_shout(blade_id, lang):
    """«Bankai!!! <name>»: the activation word, with the blade's Bankai name (its Shikai name when the source names no Bankai)."""
    s = BLADE_STAGES.get(blade_id) or {}
    pair = s.get("bankai") or s.get("shikai")
    name = pair[0 if lang == "fa" else 1] if pair else ""
    return ("بانکای!!! " if lang == "fa" else "Bankai!!! ") + name if name else ("بانکای!!!" if lang == "fa" else "Bankai!!!")


def bankai_scene(blade_id, lang, a="", d=None):
    """The full activation text: the shout and the epic line, for EVERY blade (own line, or a generic one). Plain text, no HTML.
    `a` / `d` are the wielder's and the opponent's names (already escaped by the caller)."""
    i = 0 if lang == "fa" else 1
    d = d or BANKAI_DEFAULT_FOE[i]
    a = a or ("تو" if lang == "fa" else "you")
    shout = bankai_shout(blade_id, lang)
    line = BANKAI_SCENE.get(blade_id)
    if line:
        body = line[i]
    else:
        pair = (BLADE_STAGES.get(blade_id) or {}).get("shikai")
        name = pair[i] if pair else ("تیغه" if lang == "fa" else "the blade")
        body = BANKAI_GENERIC[sum(map(ord, str(blade_id))) % len(BANKAI_GENERIC)][i].replace("{name}", name)
    return f"«{shout}»\n" + body.replace("{a}", a).replace("{d}", d)


# ---- Beta blades (Nov 26) ----
# New blades with real kits are open to EVERY player at any level while they are tested: players use them and report
# problems. When a blade is stable, remove its id from BETA_BLADES (it falls back to its level gate above) or lock it to
# the owner live with /znplock (znp_lock.py). Weak, plain blades are never locked.
BETA_BLADES = set()  # empty: Benihime and Katen Kyōkotsu both left the beta, they are paid blades now (PAID_BLADES)

# ---- Paid blades: a blade that is bought once with coins (admin decision: Benihime and Katen Kyōkotsu are not free, 20M each). ----
# The level gate in BLADE_UNLOCK still applies; on top of it the player must own the blade, i.e. its id is in
# characters.zanpakuto.owned (written by handlers_zanpakuto.blade_buy). Change the price here.
PAID_BLADES = {"benihime": 20_000_000, "katen_kyokotsu": 20_000_000}


def blade_price(blade_id) -> int:
    """Coins a paid blade costs; 0 for a free blade."""
    return int(PAID_BLADES.get(blade_id, 0))

# ---- Rarity tiers: shown in the blade picker (best first). 5 = mythic ... 1 = common. ----
TIER_NAMES = {5: ("🔴", "اسطوره‌ای", "Mythic"), 4: ("🟠", "افسانه‌ای", "Legendary"), 3: ("🟣", "حماسی", "Epic"),
              2: ("🔵", "کمیاب", "Rare"), 1: ("⚪", "معمولی", "Common")}
BLADE_TIER = {
    "kyoka_suigetsu": 5, "hyorinmaru": 5, "zanka_no_tachi": 5, "katen_kyokotsu": 5,  # Nov 27: Yamamoto's and Kyoraku's blades are Mythic
    "zangetsu": 4, "kokujo_tengen_myoo": 4, "benihime": 4,
    "senbonzakura": 3, "sode_no_shirayuki": 3, "zabimaru": 3, "minazuki": 3, "nejibana": 3,
    "wabisuke": 2, "haineko": 2, "sakanade": 2, "kinshara": 2, "ruri_iro_kujaku": 2,
    "kubikiri_orochi": 1, "tengumaru": 1, "tachikaze": 1, "haguro_tonbo": 1,
}


def blade_tier(blade_id: str) -> int:
    return BLADE_TIER.get(blade_id, 1)


def tier_label(blade_id: str, lang: str) -> str:
    emoji, fa, en = TIER_NAMES[blade_tier(blade_id)]
    return f"{emoji} {fa if lang == 'fa' else en}"


def reachable_blades(level: int):
    """Blade ids this level has reached, owned or not (beta blades are open to everyone), best tier first."""
    ids = [b for b, gate in BLADE_UNLOCK.items()
           if (int(level) >= gate or (b in BETA_BLADES and int(level) >= 1)) and b in BLADE_STAGES]
    return sorted(ids, key=lambda b: -blade_tier(b))  # sorted() is stable: equal tiers keep the unlock order


def unlocked_blades(level: int, owned=()):
    """Blade ids a character of this level may choose. A paid blade also needs to be in `owned`."""
    own = set(owned or ())
    return [b for b in reachable_blades(level) if b not in PAID_BLADES or b in own]


def blade_valid(blade_id, level: int, owned=()) -> bool:
    return blade_id in BLADE_STAGES and blade_id in unlocked_blades(level, owned)


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
BLADE_TECH_OVERRIDE = {
    "zanka_no_tachi": {"mult": 3.00, "pierce": 0.20, "cd": 2, "cost": 0.10},  # Nov 27: Yamamoto's blade is the strongest (see BANKAI_TECH_OVERRIDE)
    "katen_kyokotsu": {"mult": 1.15, "cd": 2},
    "hyorinmaru": {"mult": 2.10, "pierce": 0.50, "cd": 2},
    # Benihime, mode 1 (attack): a red blast that bites through armour; in Bankai it hits 35% harder.
    "benihime": {"mult": 2.30, "pierce": 0.45, "cd": 2, "cost": 0.10, "bk_mult": 1.35,
                 "fa": "انفجار سرخ", "en": "Crimson Burst"},
}


# ---- Bankai versions of the simple abilities (Nov 27) ----
# A Shikai blade has two simple abilities: the TECHNIQUE (button 🗡) and the second ability b2 (button 🔰, below). When the Bankai opens,
# BOTH change into a deadlier form with their own name, more damage and an extra effect (the finisher already did: BLADE_ULT["bk"]).
BANKAI_TECH_OVERRIDE = {"zanka_no_tachi": {"mult": 5.2, "pierce": 0.40, "fx": "burn"}, "katen_kyokotsu": {"mult": 1.75, "fx": ["bleed", "weaken"]}}
BANKAI_TECH_NAME = {  # blade -> (fa, en) name of the technique while in Bankai
    "zangetsu": ("گتسوگا: برش سیاه", "Black Getsuga Cut"), "senbonzakura": ("کاگیوشی: بارش تیغه‌ها", "Kageyoshi: Blade Rain"),
    "hyorinmaru": ("دایگورن: شکافت یخ", "Daiguren: Ice Rend"), "zanka_no_tachi": ("زانکا: برش خاکستر", "Zanka: Ash Cut"),
    "sode_no_shirayuki": ("هاکا: برش سفید", "Hakka: White Cut"), "zabimaru": ("هیهیو: نیش مار", "Hihiō: Serpent Fang"),
    "wabisuke": ("وزن پشیمانی", "Weight of Regret"), "minazuki": ("مینازوکی: تیغ خونین", "Minazuki: Bloody Edge"),
    "kokujo_tengen_myoo": ("کوکوجو: مشت پولادین", "Kokujō: Steel Fist"), "kinshara": ("بوتودان: رقص ضربه", "Butōdan: Strike Dance"),
    "sakanade": ("ساکانادِه: ضربه‌ی وارونه", "Sakanade: Inverted Cut"), "benihime": ("کانون‌بیراکی: انفجار سرخ", "Kannonbiraki: Crimson Burst"),
    "katen_kyokotsu": ("کاراماتسو: برش دوگانه", "Karamatsu: Twin Cut"),
}
# kind -> what the technique gains in Bankai (applied over the Shikai values)
BANKAI_TECH_KIND = {
    "pierce": {"mult": 2.6, "pierce": 0.55, "fx": "weaken"},
    "bleed": {"mult": 2.3, "fx": "burn"},
    "twin": {"mult": 1.45, "fx": "bleed"},  # two cuts, each 1.45x
    "heavy": {"mult": 3.0, "pierce": 0.30, "fx": "skip", "skip_p": 0.35},
}

# Second ability: kind -> values (base / Bankai). guard: barrier + mend. focus: damage buff. snare: a cut that may freeze the foe.
# drain: a cut that heals the wielder. hex: a cut that cripples (one effect or a list).
BLADE_B2_KINDS = {
    "guard": {"base": {"shield": 0.18, "heal": 0.05}, "bk": {"shield": 0.32, "heal": 0.12, "mult": 1.3}},
    "focus": {"base": {"buff": (2, 1.25)}, "bk": {"buff": (3, 1.55), "mult": 1.2}},
    "snare": {"base": {"mult": 1.2, "fx": "skip", "skip_p": 0.30}, "bk": {"mult": 2.1, "fx": "skip", "skip_p": 0.60, "pierce": 0.30}},
    "drain": {"base": {"mult": 1.4, "heal": 0.06}, "bk": {"mult": 2.3, "heal": 0.14, "fx": "bleed"}},
    "hex": {"base": {"mult": 1.1, "fx": "weaken"}, "bk": {"mult": 2.0, "fx": ["weaken", "burn"], "pierce": 0.30}},
}
BLADE_B2_OVERRIDE = {  # Nov 27 round 4: Ryūjin Jakka's second ability (Burning Blade) hits like a real fire technique
    "zanka_no_tachi": {"mult": 3.2, "pierce": 0.20, "fx": ["weaken", "burn"], "cd": 3, "cost": 0.11,
                      "bk": {"mult": 5.0, "pierce": 0.40, "fx": ["weaken", "burn"]}},
}
BLADE_B2_COST = {"cost": 0.10, "cd": 4}
BLADE_B2 = {  # blade -> (kind, fa, en, bankai fa, bankai en)
    "zangetsu": ("focus", "تمرکز تنسا", "Tensa Focus", "گتسوگای سیاه‌پوش", "Black Getsuga Aura"),
    "senbonzakura": ("guard", "دیوار تیغه‌ها", "Blade Wall", "کاگیوشی: دیوار هزارتیغ", "Kageyoshi: Thousand-Blade Wall"),
    "hyorinmaru": ("snare", "لمس یخ", "Ice Touch", "دایگورن: انجماد مطلق", "Daiguren: Absolute Freeze"),
    "zanka_no_tachi": ("hex", "شعله‌ی ملتهب", "Scorching Flame", "زانکا: شعله‌ی نابودگر", "Zanka: Annihilating Flame"),
    "sode_no_shirayuki": ("snare", "رقص برف", "Snow Dance", "هاکا: یخ‌بندان سفید", "Hakka: White Frost"),
    "zabimaru": ("drain", "نیش ماری", "Serpent Bite", "هیهیو: بلعیدن", "Hihiō: Devour"),
    "wabisuke": ("hex", "وزن دوبرابر", "Doubled Weight", "وزن پشیمانیِ بی‌پایان", "Endless Regret"),
    "minazuki": ("drain", "تیغ شفابخش", "Healing Edge", "ماه خونین", "Blood Moon"),
    "kokujo_tengen_myoo": ("guard", "زره پولادین", "Steel Armour", "غول زره‌پوش", "Armoured Giant"),
    "kinshara": ("focus", "نُت تند", "Quickened Note", "بوتودان: رقص زرین", "Butōdan: Golden Dance"),
    "sakanade": ("hex", "وارونگی", "Inversion", "دنیای وارونه", "Inverted World"),
    "benihime": ("guard", "حالت دفاعی بنی‌هیمه", "Benihime Guard", "کانون‌بیراکی: بازسازی", "Kannonbiraki: Rebuild"),
    "katen_kyokotsu": ("snare", "بازی کودکانه", "Children's Game", "بازی بزرگ‌ها", "The Grown-ups' Game"),
}
_B2_BY_TECH = {"pierce": "snare", "bleed": "drain", "twin": "focus", "heavy": "guard"}  # blades without an entry above


def blade_technique(blade_id: str):
    """{'kind', 'fa', 'en', ..., 'bk': {...}} for a blade's technique, or None for a blade without one.
    `bk` holds what changes in Bankai (name, more damage, an extra effect); the engine merges it over the Shikai values."""
    kind = BLADE_TECH.get(blade_id)
    if not kind:
        return None
    stage = BLADE_STAGES.get(blade_id, {}).get("shikai") or (blade_id, blade_id)
    t = {"kind": kind, **BLADE_TECH_KINDS[kind], **BLADE_TECH_COST, **BLADE_TECH_OVERRIDE.get(blade_id, {}),
         "blade_fa": stage[0], "blade_en": stage[1]}
    bk = dict(BANKAI_TECH_KIND[kind])
    if t.get("bk_mult"):  # Benihime keeps her own Bankai multiplier: only the name and the effect change
        bk.pop("mult", None); bk.pop("pierce", None)
    bk.update(BANKAI_TECH_OVERRIDE.get(blade_id, {}))
    nm = BANKAI_TECH_NAME.get(blade_id)
    bk["fa"], bk["en"] = nm if nm else (f"{t['fa']} (بانکای)", f"{t['en']} (Bankai)")
    t["bk"] = bk
    return t


def blade_b2(blade_id: str):
    """The blade's second simple ability {'kind', 'fa', 'en', 'cost', 'cd', ..., 'bk': {...}} or None (Kyōka has its own kit).
    Every blade with a technique gets one; the kind is a design choice, not canon."""
    if blade_id == "kyoka_suigetsu" or blade_id not in BLADE_TECH:
        return None
    ent = BLADE_B2.get(blade_id)
    if ent:
        kind, fa, en, bfa, ben = ent
    else:
        kind = _B2_BY_TECH[BLADE_TECH[blade_id]]
        stage = (BLADE_STAGES.get(blade_id) or {}).get("shikai") or (blade_id, blade_id)
        fa, en = f"{stage[0]}: حالت ویژه", f"{stage[1]}: Special Stance"
        bfa, ben = f"{stage[0]}: حالت ویژه (بانکای)", f"{stage[1]}: Special Stance (Bankai)"
    k = BLADE_B2_KINDS[kind]
    out = {"kind": kind, "fa": fa, "en": en, **BLADE_B2_COST, **k["base"], "bk": {**k["bk"], "fa": bfa, "en": ben}}
    ov = BLADE_B2_OVERRIDE.get(blade_id)
    if ov:  # Nov 27 round 4: an owner blade can keep its own numbers
        out.update({k2: v for k2, v in ov.items() if k2 != "bk"})
        out["bk"].update(ov.get("bk", {}))
    return out



# ---- Third and fourth simple abilities (Nov 27, round 4): Yamamoto (Ryūjin Jakka) and Urahara (Benihime) ----
# Same shape as the second ability (guard-style shield / heal, a blow with mult / pierce / fx, a damage buff, cleanse): button 🔥/🛠 in
# Shikai, 💥 with the Bankai name once the Bankai is open. The Bankai itself is the ordinary one: only names and numbers change.
BLADE_EXTRA = {
    "zanka_no_tachi": {
        "b3": {"fa": "جوکاکو انجو: دیوار آتش", "en": "Jōkaku Enjō: Wall of Flame", "cost": 0.12, "cd": 4,
               "shield": 0.40, "mult": 2.2, "pierce": 0.10, "fx": "burn",
               "bk": {"fa": "زانجیتسو گوکوی: حرارت مطلق", "en": "Zanjitsu Gokui: Absolute Heat", "shield": 0.60, "heal": 0.12, "mult": 3.6, "pierce": 0.25, "fx": ["burn", "weaken"]}},
        "b4": {"fa": "اِنِتسو جیگوکو: جهنم شعله‌ور", "en": "Ennetsu Jigoku: Scorching Hell", "cost": 0.15, "cd": 4,
               "mult": 4.4, "pierce": 0.25, "fx": ["burn", "weaken"],
               "bk": {"fa": "کاکا جومانوکوشی: ارتش خاکستر", "en": "Kaka Jūmanokushi: Army of Ash", "mult": 6.4, "pierce": 0.45, "fx": ["weaken", "burn"]}},
        "b5": {"fa": "گوکا: انفجار آتشین", "en": "Gōka: Great Blast", "cost": 0.18, "cd": 5,
               "mult": 5.0, "pierce": 0.30, "fx": "weaken", "buff": (2, 1.20),
               "bk": {"fa": "کیوکوجیتسوجین: خورشید سوزان", "en": "Kyokujitsujin: Burning Sun", "mult": 7.4, "pierce": 0.50, "fx": ["weaken", "burn"], "buff": (3, 1.40)}},
    },
    "benihime": {
        "b3": {"fa": "شیباری: زندان خون", "en": "Shibari: Blood Prison", "cost": 0.12, "cd": 5,
               "mult": 1.3, "fx": "skip", "skip_p": 0.30,
               "bk": {"fa": "تجزیه‌ی سرخ", "en": "Crimson Deconstruction", "mult": 3.0, "pierce": 0.25, "fx": ["weaken", "skip"], "skip_p": 0.45}},
        "b4": {"fa": "تسوپانه: برش انرژی", "en": "Tsuppane: Energy Dissection", "cost": 0.12, "cd": 5,
               "heal": 0.10, "buff": (2, 1.20),
               "bk": {"fa": "بازسازی کامل بدن", "en": "Perfect Body Modification", "heal": 0.18, "buff": (3, 1.45), "cleanse": True}},
    },
}
EXTRA_SLOTS = ("b3", "b4", "b5")


def blade_extra(blade_id: str, slot: str):
    """Third / fourth simple ability of a blade (slot 'b3' | 'b4' | 'b5') or None. Same shape as blade_b2."""
    ent = (BLADE_EXTRA.get(blade_id) or {}).get(slot)
    if not ent:
        return None
    bk = dict(ent["bk"])
    return {**{k: v for k, v in ent.items() if k != "bk"}, "bk": bk}



# ---- Blade ultimates: every blade's finishing technique (after Shikai), one per blade, own cost / cooldown. ----
# mult: power of the blow (x the ability formula), hits: number of cuts, pierce: share of armour ignored,
# fx: status on the foe (bleed / burn / weaken / skip = loses its next turn, with `skip_p` chance),
# buff: (turns, dmg multiplier) on the wielder. Kyōka Suigetsu keeps its own five-ability kit (engine ks1..ks5).
BLADE_ULT = {
    "zangetsu": {"fa": "گتسوگا تنشو", "en": "Getsuga Tenshō", "mult": 5.2, "pierce": 0.30, "buff": (2, 1.25), "cd": 5},
    "senbonzakura": {"fa": "کاگیوشی سنبونزاکورا", "en": "Senkei Senbonzakura", "mult": 4.6, "pierce": 0.45, "fx": "bleed", "cd": 5},
    "hyorinmaru": {"fa": "ریوسنکا", "en": "Ryūsenka", "mult": 5.0, "pierce": 0.45, "fx": "skip", "skip_p": 0.55, "cd": 5},
    "zanka_no_tachi": {"fa": "ریوجین جاکا: ملتهب", "en": "Ryūjin Jakka: Scorch", "mult": 8.0, "pierce": 0.35, "fx": "burn", "cd": 5,
                       # Nov 27: in Bankai the finisher becomes the forbidden Zanka no Tachi: all creation turned to ash
                       "bk": {"fa": "زانکا نو تاچی: خاکستر مطلق", "en": "Zanka no Tachi: Absolute Ash", "mult": 11.0, "pierce": 0.55,
                              "fx": "burn", "cost": 0.30}},
    "sode_no_shirayuki": {"fa": "تسوگی نو مای: هاکورن", "en": "Tsugi no Mai: Hakuren", "mult": 4.2, "pierce": 0.35, "fx": "skip", "skip_p": 0.5, "cd": 5},
    "zabimaru": {"fa": "هیهیو زابیمارو", "en": "Hihiō Zabimaru", "mult": 5.0, "pierce": 0.30, "fx": "bleed", "cd": 5},
    "wabisuke": {"fa": "وابیسوکه: وزن دوچندان", "en": "Wabisuke: Doubled Weight", "mult": 3.6, "pierce": 0.30, "fx": "weaken", "cd": 4},
    "haineko": {"fa": "هاینکو: خاکستر خفه‌کننده", "en": "Haineko: Choking Ash", "mult": 4.4, "pierce": 0.40, "fx": "weaken", "cd": 5},
    "minazuki": {"fa": "مینازوکی: تیغه‌ی شفابخش", "en": "Minazuki: Bleeding Moon", "mult": 4.8, "pierce": 0.30, "fx": "bleed", "cd": 5},
    # Nov 26: Benihime's second use is DEFENCE: a barrier and a mend instead of a big blow (shield / heal = share of the old HP pool).
    "benihime": {"fa": "بنی‌هیمه: سد سرخ", "en": "Benihime: Crimson Ward", "mult": 2.6, "pierce": 0.30, "shield": 0.45, "heal": 0.18, "cd": 4, "cost": 0.20,
                 # Bankai: the same button becomes Kannonbiraki Benihime Aratame (bigger blow, barrier and mend, and it cleanses your wounds)
                 "bk": {"fa": "کانون‌بیراکی بنی‌هیمه آراتامه", "en": "Kannonbiraki Benihime Aratame", "mult": 3.6, "pierce": 0.40,
                        "shield": 0.65, "heal": 0.28, "cleanse": True}},
    "katen_kyokotsu": {"fa": "کاتن کیوکوتسو: دو شمشیر، یک بازی", "en": "Katen Kyōkotsu: Two Blades, One Game", "mult": 2.9, "hits": 3, "pierce": 0.30, "fx": "weaken", "cd": 5,
                       # Nov 27: Mythic. In Bankai the finisher becomes Karamatsu Shinjū (a harder-hitting three-cut game)
                       "bk": {"fa": "کاتن کیوکوتسو: کاراماتسو شینجو", "en": "Katen Kyōkotsu: Karamatsu Shinjū", "mult": 3.7, "hits": 3,
                              "pierce": 0.40, "fx": "weaken", "cost": 0.28}},
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



# ---- Nov 27 round 4: every blade hits harder (Ryūjin Jakka was buffed by hand above and is left out) ----
# Scales the damage, shield, heal and buff numbers of every shared table once, at import. Kyōka Suigetsu has its own kit (engine ks1..ks5).
_HAND_TUNED = {"zanka_no_tachi"}


def _buff_spec(d, mult=1.45, soft=1.30, pierce=0.05):
    if not isinstance(d, dict):
        return
    if "mult" in d:
        d["mult"] = round(d["mult"] * mult, 2)
    for k in ("shield", "heal"):
        if k in d:
            d[k] = round(min(0.9, d[k] * soft), 3)
    if d.get("pierce"):
        d["pierce"] = round(min(0.60, d["pierce"] + pierce), 2)
    if d.get("buff"):
        d["buff"] = (d["buff"][0], round(d["buff"][1] + 0.10, 2))
    if isinstance(d.get("bk"), dict):
        _buff_spec(d["bk"], mult, soft, pierce)


def _buff_all():
    for tbl in (BLADE_TECH_KINDS, BANKAI_TECH_KIND):
        for spec in tbl.values():
            _buff_spec(spec)
    for spec in BLADE_B2_KINDS.values():
        _buff_spec(spec["base"]); _buff_spec(spec["bk"])
    for tbl in (BLADE_TECH_OVERRIDE, BANKAI_TECH_OVERRIDE, BLADE_B2_OVERRIDE):
        for bid, spec in tbl.items():
            if bid not in _HAND_TUNED:
                _buff_spec(spec)
    for bid, slots in BLADE_EXTRA.items():
        if bid not in _HAND_TUNED:
            for spec in slots.values():
                _buff_spec(spec)
    for bid, spec in BLADE_ULT.items():
        if bid not in _HAND_TUNED:
            _buff_spec(spec, mult=1.30, soft=1.20, pierce=0.05)
    for spec in BLADE_ULT_KIND.values():
        _buff_spec(spec, mult=1.30, soft=1.20, pierce=0.05)


_buff_all()
