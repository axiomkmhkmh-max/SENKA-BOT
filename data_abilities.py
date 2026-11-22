"""Ability families and types (Nov 21). Pure data and small helpers, no I/O.

Every special battle button of a race is a FAMILY (Shunpo, Getsuga, Cero, Hierro...). A family has many TYPES; each
type has its own job and root power. Types are not ranked: a card's colour is only its rarity. The player owns a type
by learning its card (cards are race-locked), and picks, before a battle, which type each button fires. The family has
one LEVEL (1..10) shared by all its types, raised with duplicate cards of that family and coins.

Type spec keys (read by engine._ab_run):
  m        damage multiplier of one blow          hits      number of blows (each m)      hits_rand (lo, hi) blows
  pierce   extra armour pierce                     charge    first press gathers (breakable by a hard hit), second fires
  gather   Getsuga: needs the gather turn (gc)     anyrange  hits from any distance, no range penalty
  fx       (status, turns) on the foe, fx_p chance (burn, poison, bleed, weaken, skip, daze, seal, root, noregen)
  ls       share of the damage healed              recoil    share of the damage taken back by yourself
  hpcost   paid in HP (share of old-scale HP) instead of reiatsu
  heal     share of old-scale HP healed            cleanse   removes the bad effects
  shield   share of old-scale HP as a barrier      hot/sot   (share, turns) heal / barrier every turn
  re       share of max reiatsu restored           steal_re  share of the foe's max reiatsu taken
  buff     {key: value, "t": turns} on yourself    debuff    {key: value, "t": turns} on the foe
           keys: dmg, def, hoho (bonus shares), red (damage taken reduction), crit, dodge, pierce, cdmg, miss,
                 thorns (melee damage reflected), heal_hit (HP share back per blow taken), lowfoe (damage vs a foe
                 under 50%), nododge, noregen, drain_re, seal, root
  evade    {"n": blows, "p": chance, "all": also abilities, "c": counter mult, "t": turns it waits}
  shadow   no strike now, nothing lands on you next turn      reflect   share of the next blow sent back
  dist     "close" (gap to 0 first) / "back2" / "pull2"       break     share of the foe's barrier broken
  delay    (turns, m) a blow that lands later                 trap      m: explodes next turn unless the gap changed
  stack    (bonus per use, max uses) this button grows         perm      (dmg bonus per use, max) all your damage grows
  low_foe  (hp share, m) stronger finisher                    low_self  (hp share, m) stronger when you are low
  rand_m   (lo, hi) random power                              curhp     share of the foe's current HP added
  miss_self chance the blow misses                            combo     m of a second blow if the first was a crit
  crit_add / cdmg_add  for this blow                          noguard   the foe's Guard does not reduce it
  once     once per fight                                     fatigue   turns you lose after it
  after    {key: value, "t": turns} on yourself after it      absorb    (turns, m) eats the next ability and returns it
  copy     takes the foe's active buffs                       rewind    HP back to what it was two turns ago
  mask_full  the Hollow inside stops fighting you (no rage), +10% damage
  rel_m    m while your release is active                     wpn2      the weapon counts double in this blow
  arr      for Arrancar: replaces buff values (stronger Pesquisa)
"""
from data_weapons import RARITIES, PRICE

LV_MAX = 10
LV_STEP = 0.06       # +6% to the main numbers per level
# cards and coins to go from level L to L+1 (index L-1): 25 cards and 172k coins from 1 to 10
UPGRADE = [(1, 2000), (1, 4000), (2, 7000), (2, 10000), (3, 15000), (3, 20000), (4, 28000), (4, 36000), (5, 50000)]

C_FA, C_EN = "کانن", "canon"
I_FA, I_EN = "ابداعی", "original"

GATES = {  # in-fight states that open some types (the button shows only while it holds)
    "shikai": ("شیکای", "Shikai"), "bankai": ("بانکای", "Bankai"), "mask": ("ماسک هالو", "Hollow Mask"),
    "hierro": ("هیرو", "Hierro"), "rel": ("رهاسازی", "Release"), "res": ("رسورکسیون", "Resurrección"),
    "arterie": ("بلوت آرتری", "Blut Arterie"), "voll": ("فولشتندیگ", "Vollständig"), "rage": ("خشم (جان زیر ۵۰٪)", "Rage (HP under 50%)"),
    "cfb": ("فول‌برینگ کامل", "Complete Fullbring"), "awake": ("بیداری کامل روح", "Full Soul Awakening"),
}
STAT_NAMES = {"zanjutsu": ("زنجوتسو", "Zanjutsu"), "kido": ("کیدو", "Kidō"), "hakuda": ("هاکودا", "Hakuda"),
              "hoho": ("هوهو", "Hohō"), "reiatsu": ("ریاتسو", "Reiatsu"), "weapon": ("قدرت سلاح", "weapon power")}


def T(tid, fa, en, sfa, sen, rar, cost, cd, gate=None, **spec):
    return {"id": tid, "fa": fa, "en": en, "src": (sfa, sen), "rar": rar, "cost": cost, "cd": cd, "gate": gate, "spec": spec}


FAMILIES = {
    "shunpo": {"fa": "شونپو", "en": "Shunpo", "icon": "⚡", "stat": {"hoho": 0.7, "zanjutsu": 0.3}, "types": [
        T("shunpo", "شونپو", "Shunpo", C_FA, C_EN, 0, 0.08, 4, evade={"n": 1, "p": 1.0, "c": 0.5}),
        T("utsusemi", "اوتسوسمی", "Utsusemi", "یوروئیچی، بیاکویا", "Yoruichi, Byakuya", 2, 0.10, 5, evade={"n": 1, "p": 1.0, "all": True}),
        T("senka", "سنکا", "Senka", "بیاکویا", "Byakuya", 3, 0.09, 3, m=1.4, pierce=0.30),
        T("shunko", "شونکو", "Shunkō", "یوروئیچی، سوی‌فون", "Yoruichi, Suì-Fēng", 4, 0.12, 6, buff={"hoho": 0.25, "def": 0.10, "t": 3}),
        T("shadows", "سایه‌های شونپو", "Shunpo Shadows", I_FA, I_EN, 1, 0.10, 5, evade={"n": 2, "p": 0.40, "all": True}),
        T("shunshin", "شونشین", "Shunshin", I_FA, I_EN, 1, 0.08, 3, dist="close", m=1.0),
        T("kageuchi", "کاگه‌اوچی", "Kage-uchi", I_FA, I_EN, 2, 0.08, 4, evade={"n": 1, "p": 1.0, "all": True, "c": 1.6, "t": 1}),
        T("hayate", "هایاته", "Hayate", I_FA, I_EN, 1, 0.08, 5, buff={"dodge": 0.20, "crit": 0.10, "t": 2}),
    ]},
    "getsuga": {"fa": "گتسوگا", "en": "Getsuga", "icon": "🌙", "stat": {"reiatsu": 0.5, "zanjutsu": 0.5}, "types": [
        T("tensho", "گتسوگا تنشو", "Getsuga Tenshō", "ایچیگو", "Ichigo", 0, 0.15, None, "shikai", gather=True, m=2.4),
        T("jujisho", "گتسوگا جوجیشو", "Getsuga Jūjishō", "ایچیگو (ضربدری)", "Ichigo (the cross)", 3, 0.18, None, "shikai", gather=True, m=2.6, pierce=0.25),
        T("black", "گتسوگای سیاه", "Black Getsuga", "ایچیگو (بانکای)", "Ichigo (Bankai)", 4, 0.15, None, "bankai", gather=True, m=2.0, rel_m=2.8, fx=("burn", 2)),
        T("instant", "گتسوگای فوری", "Instant Getsuga", I_FA, I_EN, 1, 0.10, 2, "shikai", m=1.4),
        T("double", "گتسوگای دوگانه", "Twin Getsuga", I_FA, I_EN, 2, 0.16, None, "shikai", gather=True, hits=2, m=1.3),
        T("shieldwave", "گتسوگای سپری", "Shield Getsuga", I_FA, I_EN, 1, 0.15, None, "shikai", gather=True, m=1.6, shield=0.10),
        T("longrange", "گتسوگای دوربرد", "Long Getsuga", I_FA, I_EN, 2, 0.15, None, "shikai", gather=True, m=2.2, anyrange=True),
        T("mugetsu", "موگتسو", "Mugetsu", "ایچیگو (گتسوگای نهایی)", "Ichigo (the final Getsuga)", 5, 0.30, None, "bankai", once=True, m=6.0,
          after={"dmg": -0.30, "t": 2}),
    ]},
    "cero": {"fa": "سرو", "en": "Cero", "icon": "🔴", "stat": {"reiatsu": 1.0}, "types": [
        T("cero", "سرو", "Cero", C_FA, C_EN, 0, 0.12, 2, charge=True, m=2.8, pierce=0.30),
        T("rafaga", "سرو رافاگا", "Cero Ráfaga", I_FA, I_EN, 1, 0.08, 1, m=1.6),
        T("metralleta", "سرو مترایتا", "Cero Metralleta", "استارک", "Stark", 3, 0.16, 3, hits=6, m=0.5),
        T("oscuras", "سرو اسکوراس", "Cero Oscuras", "اولکیورا", "Ulquiorra", 3, 0.22, 5, m=2.6, pierce=0.35, brk=1.0),
        T("granrey", "گرن ری سرو", "Gran Rey Cero", "اسپادا", "the Espada", 4, 0.25, 5, charge=True, m=3.6, pierce=0.40),
        T("doble", "سرو دوبله", "Cero Doble", "نل", "Nel", 2, 0.10, 4, absorb=(2, 1.0)),
        T("sincretico", "سرو سینکرتیکو", "Cero Sincrético", "سه جانور هریبل", "Halibel's three beasts", 2, 0.14, 3, m=2.4),
        T("olaazul", "اولا آسول", "La Ola Azul", "هریبل", "Halibel", 2, 0.12, 3, m=1.8, fx=("bleed", 2)),
        T("lanza", "لانسا دل رلامپاگو", "Lanza del Relámpago", "اولکیورا", "Ulquiorra", 5, 0.30, 6, "rel", m=4.2, miss_self=0.30),
        T("tormenta", "سرو تورمنتا", "Cero Tormenta", I_FA, I_EN, 1, 0.10, 2, hits_rand=(1, 4), m=0.9),
        T("sangre", "سرو سانگره", "Cero Sangre", I_FA, I_EN, 2, 0.0, 3, hpcost=0.08, m=2.4, ls=0.20),
        T("espiral", "سرو اسپیرال", "Cero Espiral", I_FA, I_EN, 1, 0.12, 3, m=1.6, fx=("burn", 3)),
        T("frio", "سرو فریو", "Cero Frío", I_FA, I_EN, 2, 0.14, 4, m=1.8, fx=("skip", 1), fx_p=0.35),
        T("espejo", "سرو اسپخو", "Cero Espejo", I_FA, I_EN, 1, 0.12, 4, m=1.4, reflect=0.30),
        T("silencio", "سرو سیلنسیو", "Cero Silencio", I_FA, I_EN, 2, 0.15, 4, m=1.7, fx=("seal", 1)),
        T("gravedad", "سرو گراودد", "Cero Gravedad", I_FA, I_EN, 2, 0.14, 4, m=2.0, dist="pull2", debuff={"hoho": -0.20, "t": 2}),
        T("luna", "سرو لونا", "Cero Luna", I_FA, I_EN, 3, 0.14, 3, m=2.2, crit_add=0.25, cdmg_add=0.30),
        T("barrera", "سرو باررا", "Cero Barrera", I_FA, I_EN, 1, 0.12, 4, m=1.2, shield=0.12),
        T("oculto", "سرو اوکولتو", "Cero Oculto", I_FA, I_EN, 2, 0.15, 3, m=2.0, noguard=True),
        T("final", "سرو فینال", "Cero Final", I_FA, I_EN, 5, 0.40, None, once=True, m=5.0, fatigue=1),
    ]},
    "mask": {"fa": "ماسک", "en": "Mask", "icon": "🎭", "stat": {"reiatsu": 0.7, "zanjutsu": 0.3}, "types": [
        T("mask_strike", "ضربه‌ی ماسک", "Mask Strike", C_FA, C_EN, 0, 0.10, 3, "mask", m=3.0, pierce=0.20),
        T("sakanade", "ساکاناده", "Sakanade", "شینجی", "Shinji", 3, 0.12, 6, "mask", debuff={"miss": 0.35, "t": 2}),
        T("mask_regen", "بازسازی هالو", "Hollow Regeneration", C_FA, C_EN, 1, 0.12, 6, "mask", heal=0.12),
        T("kinshara", "کینشارا", "Kinshara", "رُز", "Rose", 2, 0.12, 6, "mask", debuff={"dmg": -0.20, "crit": -0.20, "t": 2}),
        T("hollow_rage", "خشم هالو", "Hollow Rage", I_FA, I_EN, 1, 0.08, 5, "mask", buff={"dmg": 0.25, "def": -0.10, "t": 2}),
        T("howl", "زوزه‌ی هالو", "Hollow Howl", I_FA, I_EN, 1, 0.10, 5, "mask", debuff={"dmg": -0.15, "t": 2}),
        T("full_mask", "ماسک کامل", "Full Mask", I_FA, I_EN, 4, 0.10, None, "mask", once=True, mask_full=True),
        T("claw", "پنجه‌ی هالو", "Hollow Claw", I_FA, I_EN, 2, 0.10, 3, "mask", hits=3, m=1.3),
    ]},
    "hiren": {"fa": "هیرن‌کیاکو", "en": "Hirenkyaku", "icon": "💨", "stat": {"reiatsu": 1.0}, "types": [
        T("hiren", "هیرن‌کیاکو", "Hirenkyaku", C_FA, C_EN, 0, 0.10, 4, m=0.7, buff={"dodge": 0.25, "crit": 0.12, "t": 2}),
        T("schatten", "شاتن", "Schatten", "وندن‌رایش (سایه)", "Wandenreich (shadow)", 3, 0.12, 6, shadow=True),
        T("sprung", "اشپرونگ", "Sprung", I_FA, I_EN, 1, 0.08, 3, dist="back2", buff={"dmg": 0.30, "t": 1}),
        T("double_hiren", "هیرن‌کیاکوی دوگانه", "Twin Hirenkyaku", I_FA, I_EN, 1, 0.10, 4, hits=2, m=0.5, buff={"dodge": 0.25, "t": 1}),
        T("light_dance", "رقص نور", "Dance of Light", I_FA, I_EN, 2, 0.10, 5, buff={"dodge": 0.15, "t": 3}),
        T("hunter_hiren", "هیرن‌کیاکوی شکارچی", "Hunter's Hirenkyaku", I_FA, I_EN, 2, 0.10, 4, m=1.0, low_foe=(0.30, 1.8)),
    ]},
    "arrow": {"fa": "تیر", "en": "Arrow", "icon": "🏹", "stat": {"reiatsu": 1.0}, "types": [
        T("licht_regen", "لیشت رگن", "Licht Regen", "اوریو", "Uryū", 0, 0.12, 4, hits=4, m=0.32),
        T("heilig_pfeil", "هایلیگ فایل", "Heilig Pfeil", C_FA, C_EN, 1, 0.06, 1, m=1.1),
        T("schuss", "شوس", "Schuss", I_FA, I_EN, 2, 0.14, 4, charge=True, m=2.6, pierce=0.30),
        T("full_volley", "تیرباران کامل", "Full Volley", "هزار تیر اوریو", "Uryū's thousand arrows", 3, 0.16, 5, hits=8, m=0.2),
        T("chain_arrow", "تیر زنجیری", "Chain Arrow", I_FA, I_EN, 1, 0.08, 3, m=0.9, fx=("root", 1)),
        T("reishi_eater", "تیر ریشی‌خوار", "Reishi-eater Arrow", I_FA, I_EN, 2, 0.10, 4, m=0.8, steal_re=0.15),
        T("silver_arrow", "تیر نقره‌ای", "Silver Arrow", I_FA, I_EN, 1, 0.10, 3, m=1.2, fx=("bleed", 2)),
        T("star_arrow", "تیر ستاره", "Star Arrow", I_FA, I_EN, 2, 0.12, 4, m=1.5, combo=0.7),
        T("voll_licht", "فولشتندیگ لیشت رگن", "Vollständig Licht Regen", "کوئینسی (فولشتندیگ)", "Quincy (Vollständig)", 5, 0.18, 5, "voll",
          hits=8, m=0.45),
    ]},
    "lblade": {"fa": "تیغ نوری", "en": "Light Blade", "icon": "🗡", "stat": {"reiatsu": 1.0}, "types": [
        T("seele", "زیله اشنایدر", "Seele Schneider", "اوریو", "Uryū", 0, 0.10, 4, m=1.35, pierce=0.40),
        T("sprenger", "اشپرنگر", "Sprenger", "اوریو (نبرد با مایوری)", "Uryū (against Mayuri)", 4, 0.18, 6, "arterie", trap=3.0),
        T("double_blade", "تیغ نوری دوگانه", "Twin Light Blades", I_FA, I_EN, 1, 0.10, 3, hits=2, m=0.7, pierce=0.20),
        T("trembling", "تیغ لرزان", "Trembling Blade", I_FA, I_EN, 1, 0.10, 4, m=1.2, brk=0.5),
        T("freund", "فروند شیلد", "Freund Schild", "هاشوالث", "Haschwalth", 3, 0.12, 5, m=1.0, reflect=0.20),
        T("reishi_cut", "تیغ قطع ریشی", "Reishi-cutter", I_FA, I_EN, 2, 0.10, 4, m=1.1, fx=("noregen", 2)),
    ]},
    "ginto": {"fa": "گینتو", "en": "Gintō", "icon": "🧪", "stat": {"reiatsu": 1.0}, "types": [
        T("gritz", "گینتو: گریتس", "Gintō: Gritz", "اوریو", "Uryū", 0, 0.14, 5, m=1.3, fx=("skip", 1), fx_p=0.5),
        T("heizen", "گینتو: هایزن", "Gintō: Heizen", "اوریو (ستون صلیب نور)", "Uryū (the pillar of light)", 3, 0.16, 5, "arterie", m=2.4),
        T("ginto_heal", "گینتو: درمان", "Gintō: Mend", I_FA, I_EN, 1, 0.12, 5, heal=0.12),
        T("ginto_shield", "گینتو: سپر", "Gintō: Ward", I_FA, I_EN, 1, 0.12, 5, shield=0.18),
        T("ginto_blast", "گینتو: انفجار", "Gintō: Blast", I_FA, I_EN, 2, 0.14, 4, m=1.6, fx=("burn", 2)),
        T("ginto_chain", "گینتو: زنجیر", "Gintō: Chain", I_FA, I_EN, 2, 0.14, 5, m=1.0, fx=("seal", 1)),
    ]},
    "devour": {"fa": "بلعیدن", "en": "Devour", "icon": "🦷", "stat": {"hakuda": 1.0}, "types": [
        T("devour", "بلعیدن", "Devour", C_FA, C_EN, 0, 0.10, 4, m=1.25, ls=0.35),
        T("ajuchas", "بلعیدن آجوکاس", "Adjuchas Devour", "کانن (تکامل با بلعیدن)", "canon (evolving by devouring)", 3, 0.10, 4, m=1.0, perm=(0.10, 3)),
        T("soul_devour", "بلعیدن روح", "Soul Devour", I_FA, I_EN, 1, 0.08, 4, m=0.9, steal_re=0.20),
        T("hungry_bite", "گاز گرسنه", "Hungry Bite", I_FA, I_EN, 2, 0.12, 4, "rage", m=1.6, ls=0.15, low_self=(0.50, 2.0)),
        T("venom_fang", "نیش زهری", "Venom Fang", I_FA, I_EN, 1, 0.10, 4, m=1.0, fx=("poison", 3)),
        T("menos_hunger", "گرسنگی منوس", "Menos Hunger", I_FA, I_EN, 4, 0.14, 5, m=0.7, curhp=0.10),
    ]},
    "regen": {"fa": "بازسازی", "en": "Regeneration", "icon": "🦎", "stat": {"hakuda": 1.0}, "types": [
        T("fast_regen", "بازسازی سریع", "High-Speed Regeneration", C_FA, C_EN, 0, 0.12, 6, heal=0.12),
        T("molt", "پوست‌اندازی", "Molting", I_FA, I_EN, 1, 0.10, 5, heal=0.08, cleanse=True),
        T("slow_regen", "بازسازی تدریجی", "Steady Regeneration", I_FA, I_EN, 1, 0.12, 6, hot=(0.06, 3)),
        T("bloody_regen", "بازسازی خونین", "Bloody Regeneration", I_FA, I_EN, 3, 0.22, 8, "rage", heal=0.20),
        T("hard_shell", "پوسته‌ی سخت", "Hard Shell", I_FA, I_EN, 2, 0.10, 5, heal=0.06, buff={"def": 0.20, "t": 2}),
        T("rage_regen", "بازسازی خشم", "Wrathful Regeneration", I_FA, I_EN, 2, 0.12, 6, heal=0.10, buff={"dmg": 0.15, "t": 2}),
    ]},
    "pesq": {"fa": "پسکیسا", "en": "Pesquisa", "icon": "📡", "stat": {"hoho": 1.0}, "types": [
        T("pesquisa", "پسکیسا", "Pesquisa", C_FA, C_EN, 0, 0.06, 5, buff={"crit": 0.20, "dmg": 0.10, "t": 3}, arr={"crit": 0.25, "dmg": 0.15}),
        T("deep_pesq", "پسکیسای عمیق", "Deep Pesquisa", I_FA, I_EN, 2, 0.08, 5, debuff={"nododge": 1, "t": 2}),
        T("danger_sense", "حس خطر", "Danger Sense", I_FA, I_EN, 1, 0.08, 5, buff={"dodge": 0.20, "t": 2}),
        T("reiatsu_track", "ردیابی ریاتسو", "Reiatsu Tracking", I_FA, I_EN, 1, 0.06, 5, buff={"pierce": 0.25, "t": 3}),
        T("hunt_pesq", "پسکیسای شکار", "Hunting Pesquisa", I_FA, I_EN, 2, 0.06, 5, buff={"lowfoe": 0.20, "t": 3}),
    ]},
    "hierro": {"fa": "هیرو", "en": "Hierro", "icon": "🪨", "stat": {"hakuda": 1.0}, "types": [
        T("hierro", "هیرو", "Hierro", C_FA, C_EN, 0, 0.08, 5, buff={"red": 0.35, "dmg": 0.10, "t": 3, "tag": "hierro"}),
        T("nnoitra", "هیروی نویترا", "Nnoitra's Hierro", "نویترا (سخت‌ترین هیرو)", "Nnoitra (the hardest Hierro)", 4, 0.10, 6, buff={"red": 0.50, "t": 2, "tag": "hierro"}),
        T("thorn_hierro", "هیروی خاردار", "Thorned Hierro", I_FA, I_EN, 2, 0.08, 5, buff={"red": 0.20, "thorns": 0.20, "t": 3, "tag": "hierro"}),
        T("light_hierro", "هیروی سبک", "Light Hierro", I_FA, I_EN, 1, 0.08, 5, buff={"red": 0.20, "dodge": 0.15, "t": 3, "tag": "hierro"}),
        T("diamond_skin", "پوست الماسی", "Diamond Skin", I_FA, I_EN, 3, 0.12, 6, buff={"red": 0.80, "t": 1, "tag": "hierro"}),
        T("blood_hierro", "هیروی خونی", "Blood Hierro", I_FA, I_EN, 2, 0.10, 5, buff={"red": 0.25, "heal_hit": 0.02, "t": 3, "tag": "hierro"}),
    ]},
    "bring": {"fa": "ضربه‌ی برینگر", "en": "Bringer Strike", "icon": "✊", "stat": {"weapon": 1.0}, "types": [
        T("bring_strike", "ضربه‌ی برینگر", "Bringer Strike", C_FA, C_EN, 0, 0.10, 4, m=1.25, fx=("bleed", 2), fx_p=0.40),
        T("jackpot", "جک‌پات ناکل", "Jackpot Knuckle", "موئه شیشیگاوارا", "Moe Shishigawara", 3, 0.10, 3, rand_m=(0.5, 3.0)),
        T("dirty_boots", "دِرتی بوتس", "Dirty Boots", "جکی تریستان", "Jackie Tristan", 2, 0.08, 3, m=1.0, stack=(0.15, 4)),
        T("brazo", "براسو درچا", "Brazo Derecha", "چاد", "Chad", 2, 0.10, 4, m=1.6, pierce=0.15),
        T("object_soul", "روح شیء", "Soul of the Object", I_FA, I_EN, 1, 0.10, 4, m=0.8, wpn2=True),
        T("xcution_card", "کارت اکسکیوشن", "Xcution Card", I_FA, I_EN, 1, 0.10, 4, m=1.2, debuff={"def": -0.15, "t": 2}),
    ]},
    "fullbring": {"fa": "فول‌برینگ", "en": "Fullbring", "icon": "📖", "stat": {"weapon": 1.0}, "types": [
        T("book_end", "کتاب پایان", "Book of the End", "تسوکیشیما", "Tsukishima", 2, 0.10, 4, m=1.4, fx=("weaken", 3)),
        T("time_lies", "زمان دروغ نمی‌گوید", "Time Tells No Lies", "گیریکو", "Giriko", 2, 0.12, 5, m=0.8, fx=("skip", 1), fx_p=0.70),
        T("doll_house", "خانه‌ی عروسکی", "Dollhouse", "ریروکا", "Riruka", 3, 0.12, 6, debuff={"dmg": -0.30, "t": 2}),
        T("invaders", "اینویدرز ماست دای", "Invaders Must Die", "یوکیو", "Yukio", 3, 0.12, 6, buff={"dmg": 0.20, "t": 2}, debuff={"drain_re": 0.05, "t": 2}),
        T("scaffold", "صلیب داربست", "Cross of Scaffold", "جینجو", "Ginjō", 4, 0.18, 5, "cfb", m=2.2, pierce=0.30),
        T("steal", "دزدی فول‌برینگ", "Fullbring Theft", "جینجو (گرفتن قدرت)", "Ginjō (taking the power)", 4, 0.12, 5, m=0.9, copy=True),
        T("time_reserve", "ذخیره‌ی زمان", "Time Reserve", "گیریکو (ساعت)", "Giriko (the clock)", 3, 0.12, 5, "cfb", delay=(2, 2.5)),
        T("oath", "سوگند فول‌برینگ", "Fullbring Oath", I_FA, I_EN, 1, 0.08, 5, buff={"crit": 0.25, "t": 2}),
    ]},
    "soul": {"fa": "ضربه‌ی روح", "en": "Soul Strike", "icon": "✨", "stat": {"reiatsu": 1.0}, "types": [
        T("soul_strike", "ضربه‌ی روح", "Soul Strike", C_FA, C_EN, 0, 0.10, 3, m=1.6),
        T("koten", "کوتن زانشون", "Koten Zanshun", "اوریهیمه", "Orihime", 2, 0.12, 4, m=1.5, pierce=0.25),
        T("kanonji", "توپ کانونجی", "Kanonji Cannonball", "دون کانونجی", "Don Kanonji", 1, 0.08, 3, m=1.0, fx=("daze", 1), fx_p=0.20),
        T("el_directo", "ال دیرکتو", "El Directo", "چاد", "Chad", 3, 0.12, 4, m=1.8, anyrange=True, stat={"hakuda": 1.0}),
        T("la_muerte", "لا موئرته", "La Muerte", "چاد", "Chad", 4, 0.18, 5, charge=True, m=2.8, stat={"hakuda": 1.0}),
        T("soul_arrow", "تیر روح", "Soul Arrow", I_FA, I_EN, 0, 0.05, 1, m=1.0),
        T("urahara_bag", "کیسه‌ی معجون اوراهارا", "Urahara's Potion Bag", I_FA, I_EN, 1, 0.10, 4, m=1.2, fx=("poison", 3)),
        T("gigai_strike", "ضربه‌ی گیگای", "Gigai Strike", I_FA, I_EN, 1, 0.10, 3, m=1.3, recoil=0.10),
        T("tsubaki", "نور تسوباکی", "Tsubaki's Light", "اوریهیمه", "Orihime", 2, 0.08, 2, m=0.9, stack=(0.20, 3)),
        T("karakura_cry", "فریاد کاراکورا", "Karakura Cry", I_FA, I_EN, 1, 0.10, 4, m=1.1, buff={"dmg": 0.15, "t": 2}),
    ]},
    "shield": {"fa": "سپر", "en": "Shield", "icon": "🔰", "stat": {"reiatsu": 1.0}, "types": [
        T("santen", "سانتن کسشون", "Santen Kesshun", "اوریهیمه", "Orihime", 0, 0.10, 5, shield=0.14),
        T("shiten", "شیتن کوشون", "Shiten Kōshun", "اوریهیمه (سپر بازتاب)", "Orihime (the reflecting shield)", 3, 0.12, 5, shield=0.08, reflect=0.50),
        T("full_reject", "دفع کامل", "Total Rejection", I_FA, I_EN, 4, 0.14, 7, buff={"red": 0.85, "t": 1}),
        T("big_santen", "سانتن بزرگ", "Great Santen", I_FA, I_EN, 2, 0.14, 7, shield=0.22),
        T("lasting_shield", "سپر ماندگار", "Lasting Shield", I_FA, I_EN, 1, 0.12, 6, sot=(0.06, 3)),
        T("thorn_shield", "سپر خار", "Thorn Shield", I_FA, I_EN, 2, 0.10, 5, shield=0.10, buff={"thorns": 0.15, "t": 2}),
    ]},
    "heal": {"fa": "درمان", "en": "Healing", "icon": "🌸", "stat": {"reiatsu": 1.0}, "types": [
        T("soten", "سوتن کیشون", "Sōten Kisshun", "اوریهیمه", "Orihime", 0, 0.14, 6, heal=0.12, cleanse=True),
        T("rejection", "رد واقعه", "Rejection of Events", "اوریهیمه (اوج قدرت)", "Orihime (at her peak)", 5, 0.20, None, "awake", once=True, rewind=True),
        T("quick_heal", "درمان سریع", "Quick Mend", I_FA, I_EN, 0, 0.08, 3, heal=0.07),
        T("spirit_heal", "درمان روحی", "Spirit Mend", I_FA, I_EN, 2, 0.12, 6, hot=(0.05, 3), buff={"def": 0.10, "t": 3}),
        T("reiatsu_heal", "درمان ریاتسو", "Reiatsu Mend", I_FA, I_EN, 1, 0.08, 5, heal=0.08, re=0.15),
        T("shunshun_guard", "محافظ شون شون ریکا", "Shun Shun Rikka Guard", I_FA, I_EN, 2, 0.14, 6, heal=0.10, shield=0.06),
    ]},
}
for _fid, _fam in FAMILIES.items():
    _fam["id"] = _fid
    _fam["by"] = {t["id"]: t for t in _fam["types"]}

# Kidō families: their types are the spells themselves (Hadō / Bakudō numbers), the level is the spell mastery
KIDO_FAMS = {"hado": {"fa": "تسلط هادو", "en": "Hadō mastery", "icon": "🔮", "branch": "had", "stat": {"kido": 1.0}},
             "bakudo": {"fa": "تسلط باکودو", "en": "Bakudō mastery", "icon": "🛡", "branch": "bak", "stat": {"kido": 1.0}}}

# Fixed abilities: no type to choose, but a level like every family (cards of their own feed it)
FIXED = {
    "sk_shikai": {"fa": "شیکای", "en": "Shikai", "icon": "🗡", "stat": {"zanjutsu": 1.0}, "rar": 2,
                  "d_fa": "از لِوِل ۱۰: یک نوبت و ۱۵٪ ریاتسو، تا پایان نبرد آسیب {s:5} بیشتر و گتسوگا و تکنیک تیغ باز می‌شوند",
                  "d_en": "From level 10: one turn and 15% reiatsu; until the end of the fight +{s:5} damage, Getsuga and the blade technique open"},
    "sk_mask": {"fa": "ماسک هالو", "en": "Hollow Mask", "icon": "🎭", "stat": {"reiatsu": 1.0}, "rar": 2,
                "d_fa": "از لِوِل ۱۰: یک نوبت و ۱۵٪ ریاتسو، تا پایان نبرد آسیب {s:5} بیشتر و سرو، ماسک و جوجیشو باز می‌شوند (هر نوبت ۴٪ شانس سرکشی هالو)",
                "d_en": "From level 10: one turn and 15% reiatsu; until the end of the fight +{s:5} damage, Cero, Mask and Jūjishō open (4% chance a turn the Hollow rebels)"},
    "blade": {"fa": "تکنیک تیغ", "en": "Blade technique", "icon": "⚔️", "stat": {"zanjutsu": 1.0}, "rar": 2,
              "d_fa": "تکنیک خود تیغ (بعد از شیکای)، قدرت {s:100}", "d_en": "The blade's own technique (after Shikai), power {s:100}"},
    "rel": {"fa": "رهاسازی", "en": "Release", "icon": "👑", "stat": {"reiatsu": 1.0}, "rar": 4,
            "d_fa": "با روحیه‌ی ۱۰۰: ضربه‌ی رهاسازی {m:2.0} و آسیب ×۱٫۶ تا چند نوبت؛ از لِوِل ۳۰ فرم دوم",
            "d_en": "At a full spirit gauge: a {m:2.0} release strike and x1.6 damage for a few turns; the second form from level 30"},
    "gen": {"fa": "مهارت عمومی", "en": "General skill", "icon": "🎖", "stat": {"zanjutsu": 1.0}, "rar": 1,
            "d_fa": "گارد / ضربه / تمرکز، قدرت {s:100}", "d_en": "Guard / Strike / Focus, power {s:100}"},
    "bala": {"fa": "بالا", "en": "Bala", "icon": "💥", "stat": {"reiatsu": 1.0}, "rar": 1,
             "d_fa": "{m:1.4} با ۲۵٪ نفوذ، ۱۰۰٪ برخورد (جاخالی، شونپو و تاری بی‌اثرند)؛ با هیروی فعال بدون کول‌داون",
             "d_en": "{m:1.4} with 25% pierce, a 100% hit (no dodge, Shunpo or blur stops it); no cooldown while Hierro holds"},
    "ironfist": {"fa": "ضربه‌ی آهنین", "en": "Iron Fist", "icon": "🦾", "stat": {"hakuda": 1.0}, "rar": 2,
                 "d_fa": "فقط با هیروی فعال: {m:1.5} از هاکودا", "d_en": "Only while Hierro holds: {m:1.5} from Hakuda"},
    "vene": {"fa": "بلوت فنه", "en": "Blut Vene", "icon": "🩸", "stat": {"reiatsu": 1.0}, "rar": 2,
             "d_fa": "سپر {s:18} جان", "d_en": "A barrier of {s:18} HP"},
    "arterie": {"fa": "بلوت آرتری", "en": "Blut Arterie", "icon": "❤️‍🔥", "stat": {"reiatsu": 1.0}, "rar": 2,
                "d_fa": "{t:2} نوبت آسیب ×۱٫۲۵؛ اشپرنگر و گینتو هایزن را باز می‌کند",
                "d_en": "{t:2} turns of x1.25 damage; opens Sprenger and Gintō: Heizen"},
    "neg": {"fa": "نگاسیون", "en": "Negación", "icon": "🟨", "stat": {"hakuda": 1.0}, "rar": 2,
            "d_fa": "سپر {s:18} جان", "d_en": "A barrier of {s:18} HP"},
    "garg": {"fa": "گارگانتا", "en": "Garganta", "icon": "🌀", "stat": {"hoho": 1.0}, "rar": 1,
             "d_fa": "فاصله را باز می‌کند؛ هزینه با هر لِوِل ۲٪ کمتر", "d_en": "Opens the gap; 2% cheaper a level"},
    "blight": {"fa": "برینگر لایت", "en": "Bringer Light", "icon": "💫", "stat": {"weapon": 1.0}, "rar": 1,
               "d_fa": "{m:0.9} و {t:2} نوبت تاری سرعت", "d_en": "{m:0.9} and {t:2} turns of a speed blur"},
}

# Which family fires from which battle button, per race: (engine action, family, slot index). Cards and levels are race-locked.
RACE_SLOTS = {
    "shinigami": [("sg", "shunpo", 0), ("gt", "getsuga", 0), ("kd", "hado", 0), ("bk", "bakudo", 0)],
    "visored": [("sg", "cero", 0), ("t1", "mask", 0), ("gt", "getsuga", 0), ("kd", "hado", 0), ("bk", "bakudo", 0)],
    "quincy": [("sg", "hiren", 0), ("t1", "arrow", 0), ("t2", "lblade", 0), ("t3", "ginto", 0)],
    "hollow": [("sg", "cero", 0), ("t1", "devour", 0), ("t2", "regen", 0), ("t3", "pesq", 0)],
    "arrancar": [("sg", "cero", 0), ("t3", "cero", 1), ("t1", "hierro", 0), ("t2", "pesq", 0)],
    "fullbringer": [("sg", "bring", 0), ("t2", "fullbring", 0), ("t3", "fullbring", 1)],
    "human": [("sg", "soul", 0), ("t3", "soul", 1), ("t1", "shield", 0), ("t2", "heal", 0)],
}
RACE_FIXED = {
    "shinigami": ["sk_shikai", "blade", "rel", "gen"], "visored": ["sk_mask", "blade", "rel", "gen"],
    "quincy": ["vene", "arterie", "rel", "gen"], "hollow": ["neg", "garg", "rel", "gen"],
    "arrancar": ["bala", "ironfist", "garg", "rel", "gen"], "fullbringer": ["blight", "rel", "gen"], "human": ["rel", "gen"],
}
# the buttons of today are the default types, owned by everyone of that race from the start
DEFAULTS = {
    "shinigami": {"sg": "shunpo", "gt": "tensho"}, "visored": {"sg": "cero", "t1": "mask_strike", "gt": "tensho"},
    "quincy": {"sg": "hiren", "t1": "licht_regen", "t2": "seele", "t3": "gritz"},
    "hollow": {"sg": "cero", "t1": "devour", "t2": "fast_regen", "t3": "pesquisa"},
    "arrancar": {"sg": "cero", "t3": "oscuras", "t1": "hierro", "t2": "pesquisa"},
    "fullbringer": {"sg": "bring_strike", "t2": "book_end", "t3": "time_lies"},
    "human": {"sg": "soul_strike", "t3": "koten", "t1": "santen", "t2": "soten"},
}
# Fixed ability of the Visored getsuga: Jūjishō is a Hollow-mask move for them, the rest is open
VISORED_GATE = {("getsuga", "jujisho"): "mask", ("getsuga", "tensho"): None, ("getsuga", "instant"): None, ("getsuga", "double"): None,
                ("getsuga", "shieldwave"): None, ("getsuga", "longrange"): None}
# a Visored Cero is a Hollow power: every Cero type needs the mask on (Lanza keeps its own release gate)
VISORED_MASK_FAMS = ("cero",)
SHIKAI_LEVEL = 10
SHIKAI_COST = 0.15
SHIKAI_DMG = 0.05
MASK_STATE_RAGE = 0.04


def races_of_family(fam: str) -> list:
    return [r for r, slots in RACE_SLOTS.items() if any(f == fam for _a, f, _i in slots)]


def races_of_fixed(fid: str) -> list:
    return [r for r, lst in RACE_FIXED.items() if fid in lst]


def slots_of(race: str) -> list:
    return list(RACE_SLOTS.get(race) or [])


def fam_slots(race: str, fam: str) -> list:
    """The battle buttons this family fires for the race, in slot order (Arrancar: two Cero buttons)."""
    return [a for a, f, _i in sorted(RACE_SLOTS.get(race) or [], key=lambda s: s[2]) if f == fam]


def type_of(fam: str, tid: str):
    f = FAMILIES.get(fam)
    return f["by"].get(tid) if f else None


def gate_of(race: str, fam: str, t: dict):
    """The in-fight state a type needs for this race (None = always open)."""
    if not t:
        return None
    if race == "visored":
        if (fam, t["id"]) in VISORED_GATE:
            return VISORED_GATE[(fam, t["id"])]
        if fam in VISORED_MASK_FAMS and not t.get("gate"):
            return "mask"
    if t.get("gate") == "rel" and race in ("arrancar", "hollow"):
        return "res"
    return t.get("gate")


def default_owned(race: str) -> dict:
    out = {}
    for act, tid in (DEFAULTS.get(race) or {}).items():
        fam = next((f for a, f, _i in RACE_SLOTS[race] if a == act), None)
        if fam:
            out.setdefault(fam, [])
            if tid not in out[fam]:
                out[fam].append(tid)
    return out


# ---- level scaling -----------------------------------------------------------------------------------------------------
def lv_k(lv: int) -> float:
    return 1 + LV_STEP * (max(1, min(LV_MAX, int(lv))) - 1)


def lv_turns(t: int, lv: int) -> int:
    return int(t) + (1 if lv >= 5 else 0) + (1 if lv >= 10 else 0)


def lv_cd(cd, lv: int):
    return None if cd is None else max(1, int(cd) - (1 if lv >= 8 else 0))


def lv_cost(cost: float, lv: int) -> float:
    return float(cost) * (1 - 0.02 * (max(1, int(lv)) - 1))


def lv_p(p: float, lv: int) -> float:
    return min(0.95, float(p) + 0.01 * (max(1, int(lv)) - 1))


def lv_red(r: float, lv: int) -> float:
    return min(0.90, float(r) * lv_k(lv))


CHANCE_KEYS = ("crit", "dodge", "miss")
REDUCE_KEYS = ("red",)
SHARE_KEYS = ("dmg", "def", "hoho", "pierce", "cdmg", "thorns", "heal_hit", "lowfoe", "drain_re")


def scaled_buff(b: dict, lv: int) -> dict:
    """A buff / debuff dict at this level: shares x k (negative ones too: a stronger debuff), chances +1 point a
    level, reductions x k (at most 90%), turns +1 at levels 5 and 10."""
    out = {}
    for k, v in b.items():
        if k == "t":
            out[k] = lv_turns(v, lv)
        elif k == "tag" or k in ("nododge", "noregen", "seal", "root"):
            out[k] = v
        elif k in CHANCE_KEYS:
            out[k] = (lv_p(v, lv) if v > 0 else -lv_p(-v, lv))
        elif k in REDUCE_KEYS:
            out[k] = lv_red(v, lv)
        else:
            out[k] = v * lv_k(lv)
    return out


def upgrade_cost(lv: int):
    """(cards, coins) to raise a family from lv to lv + 1, or None at the top."""
    if lv >= LV_MAX or lv < 1:
        return None
    return UPGRADE[lv - 1]


# ---- descriptions (built from the spec, so the panel always says what the engine does) --------------------------------
def _fa(s) -> str:
    return str(s).translate(str.maketrans("0123456789.", "۰۱۲۳۴۵۶۷۸۹٫"))


def _num(v, lang, pct=False):
    v = round(v * 100, 1) if pct else round(v, 2)
    s = (f"{v:g}")
    return (_fa(s) + ("٪" if pct else "")) if lang == "fa" else (s + ("%" if pct else ""))


_FX_NAME = {"burn": ("سوختن", "burn"), "poison": ("سم", "poison"), "bleed": ("خونریزی", "bleeding"), "weaken": ("ضعف", "weakness"),
            "skip": ("از دست دادن نوبت", "a lost turn"), "daze": ("گیجی (۵۰٪ خطا)", "daze (50% misses)"),
            "seal": ("مهر توانایی (توانایی ویژه نمی‌زند)", "sealed abilities"), "root": ("قفل فاصله", "a locked gap"),
            "noregen": ("قطع بازسازی", "no regeneration")}
_BUFF_NAME = {"dmg": ("آسیب", "damage"), "def": ("دفاع", "defence"), "hoho": ("هوهو", "Hohō"), "red": ("آسیب دریافتی کمتر", "less damage taken"),
              "crit": ("شانس بحرانی", "crit chance"), "dodge": ("جاخالی", "dodge"), "pierce": ("نفوذ", "pierce"),
              "cdmg": ("آسیب بحرانی", "crit damage"), "miss": ("خطای ضربه‌ها", "misses"), "thorns": ("بازتاب ضربه‌های نزدیک", "melee reflection"),
              "heal_hit": ("جان با هر ضربه‌ی خورده", "HP per blow taken"), "lowfoe": ("آسیب به دشمن زیر ۵۰٪", "damage vs a foe under 50%"),
              "nododge": ("بدون جاخالی", "no dodging"), "noregen": ("بدون بازسازی", "no regeneration"),
              "drain_re": ("ریاتسوی از دست رفته هر نوبت", "reiatsu lost a turn")}


def _buff_text(b: dict, lang: str, foe: bool) -> str:
    fa = lang == "fa"
    parts = []
    for k, v in b.items():
        if k in ("t", "tag"):
            continue
        n = _BUFF_NAME.get(k, (k, k))[0 if fa else 1]
        if k in ("nododge", "noregen"):
            parts.append(n)
        elif k == "red":
            parts.append(f"{n} {_num(v, lang, True)}")
        else:
            sign = "+" if v > 0 else "−"
            parts.append(f"{n} {sign}{_num(abs(v), lang, True)}")
    t = b.get("t", 1)
    who = ("روی دشمن" if fa else "on the foe") if foe else ""
    body = "، ".join(parts) if fa else ", ".join(parts)
    return (f"{_fa(t)} نوبت {body} {who}".strip() if fa else f"{body} {who} for {t} turn{'s' if t != 1 else ''}".replace("  ", " ").strip())


def describe(t: dict, lv: int, lang: str, race: str = None) -> str:
    """One line of what the type does at this level (built from its spec)."""
    s, fa, k = t["spec"], lang == "fa", lv_k(lv)
    out = []
    m = s.get("m")
    if s.get("shadow"):
        out.append("به سایه می‌روی: این نوبت حمله نمی‌کنی، نوبت بعد هیچ ضربه‌ای به تو نمی‌خورد" if fa
                   else "into the shadow: no strike now, nothing lands on you next turn")
    if s.get("gather"):
        out.append("یک نوبت جمع کردن، بعد" if fa else "one gathering turn, then")
    if s.get("charge"):
        out.append("یک نوبت شارژ (ضربه‌ی سنگین می‌شکندش)، بعد" if fa else "one charging turn (a hard hit breaks it), then")
    if s.get("dist") == "close":
        out.append("فاصله را صفر می‌کنی و" if fa else "closes the gap to zero and")
    if s.get("dist") == "back2":
        out.append("۲ خانه عقب می‌پری" if fa else "leaps 2 zones back")
    if s.get("rand_m"):
        lo, hi = s["rand_m"]
        out.append(f"آسیب تصادفی ×{_num(lo * k, lang)} تا ×{_num(hi * k, lang)}" if fa else f"random power x{_num(lo * k, lang)}–x{_num(hi * k, lang)}")
    if s.get("trap"):
        out.append(f"تله: نوبت بعد انفجار ×{_num(s['trap'] * k, lang)}، مگر دشمن فاصله را عوض کند" if fa
                   else f"a trap: x{_num(s['trap'] * k, lang)} next turn unless the foe changes the gap")
    if s.get("delay"):
        n, dm = s["delay"]
        out.append(f"{_fa(n)} نوبت بعد ضربه‌ی تاخیری ×{_num(dm * k, lang)}" if fa else f"a delayed blow of x{_num(dm * k, lang)} in {n} turns")
    if s.get("absorb"):
        n, dm = s["absorb"]
        out.append(f"{_fa(lv_turns(n, lv))} نوبت آماده: توانایی ویژه‌ی بعدی دشمن را می‌بلعد و با آسیب خودش + ×{_num(dm * k, lang)} پس می‌زند؛ اگر چیزی نیاید ×{_num(dm * k, lang)}" if fa
                   else f"ready for {lv_turns(n, lv)} turns: swallows the foe's next ability and fires it back plus x{_num(dm * k, lang)}; x{_num(dm * k, lang)} if nothing comes")
    if m:
        hits = s.get("hits")
        if s.get("hits_rand"):
            a, b = s["hits_rand"]
            out.append(f"{_fa(a)} تا {_fa(b)} ضربه‌ی ×{_num(m * k, lang)}" if fa else f"{a}–{b} blows of x{_num(m * k, lang)}")
        elif hits:
            out.append(f"{_fa(hits)} ضربه‌ی ×{_num(m * k, lang)}" if fa else f"{hits} blows of x{_num(m * k, lang)}")
        else:
            out.append(f"×{_num(m * k, lang)}" if fa else f"x{_num(m * k, lang)}")
    if s.get("rel_m"):
        out.append(f"(با رهاسازی فعال ×{_num(s['rel_m'] * k, lang)})" if fa else f"(x{_num(s['rel_m'] * k, lang)} while released)")
    if s.get("pierce"):
        out.append(f"با {_num(s['pierce'] * k, lang, True)} نفوذ" if fa else f"with {_num(s['pierce'] * k, lang, True)} pierce")
    if s.get("anyrange"):
        out.append("از هر فاصله، بدون جریمه" if fa else "from any distance, no penalty")
    if s.get("crit_add"):
        out.append(f"بحرانی +{_num(lv_p(s['crit_add'], lv), lang, True)} و آسیب بحرانی +{_num(s.get('cdmg_add', 0) * k, lang, True)}" if fa
                   else f"crit +{_num(lv_p(s['crit_add'], lv), lang, True)}, crit damage +{_num(s.get('cdmg_add', 0) * k, lang, True)}")
    if s.get("noguard"):
        out.append("گارد دشمن جلویش را نمی‌گیرد" if fa else "the foe's Guard does not soften it")
    if s.get("miss_self"):
        out.append(f"{_num(s['miss_self'], lang, True)} احتمال خطا" if fa else f"{_num(s['miss_self'], lang, True)} chance to miss")
    if s.get("low_foe"):
        th, mm = s["low_foe"]
        out.append(f"اگر دشمن زیر {_num(th, lang, True)} جان باشد ×{_num(mm * k, lang)}" if fa else f"x{_num(mm * k, lang)} on a foe under {_num(th, lang, True)} HP")
    if s.get("low_self"):
        th, mm = s["low_self"]
        out.append(f"اگر جانت زیر {_num(th, lang, True)} باشد ×{_num(mm * k, lang)}" if fa else f"x{_num(mm * k, lang)} while you are under {_num(th, lang, True)} HP")
    if s.get("curhp"):
        out.append(f"به‌اضافه‌ی {_num(s['curhp'] * k, lang, True)} جان فعلی دشمن" if fa else f"plus {_num(s['curhp'] * k, lang, True)} of the foe's current HP")
    if s.get("combo"):
        out.append(f"اگر بحرانی شود تیر دوم ×{_num(s['combo'] * k, lang)}" if fa else f"a second x{_num(s['combo'] * k, lang)} if it crits")
    if s.get("stack"):
        b, n = s["stack"]
        out.append(f"هر بار استفاده {_num(b * k, lang, True)} قوی‌تر (تا {_fa(n)} بار)" if fa else f"+{_num(b * k, lang, True)} each use (up to {n})")
    if s.get("perm"):
        b, n = s["perm"]
        out.append(f"هر بار {_num(b * k, lang, True)} آسیب دائمی تا پایان نبرد (تا {_fa(n)} بار)" if fa else f"+{_num(b * k, lang, True)} damage for the rest of the fight each use (up to {n})")
    if s.get("wpn2"):
        out.append("سهم سلاح دو برابر" if fa else "the weapon counts double")
    if s.get("fx"):
        kind, n = s["fx"]
        nm = _FX_NAME.get(kind, (kind, kind))[0 if fa else 1]
        p = s.get("fx_p")
        pp = (f"{_num(lv_p(p, lv), lang, True)} شانس " if fa else f"{_num(lv_p(p, lv), lang, True)} chance of ") if p else ""
        out.append(f"و {pp}{nm} ({_fa(lv_turns(n, lv) if kind not in ('skip', 'seal', 'root', 'daze') else n)} نوبت)" if fa
                   else f"and {pp}{nm} ({lv_turns(n, lv) if kind not in ('skip', 'seal', 'root', 'daze') else n} turns)")
    if s.get("ls"):
        out.append(f"و {_num(s['ls'] * k, lang, True)} آسیب به جانت برمی‌گردد" if fa else f"and {_num(s['ls'] * k, lang, True)} of the damage heals you")
    if s.get("recoil"):
        out.append(f"ولی {_num(s['recoil'], lang, True)} آسیب به خودت برمی‌گردد" if fa else f"but {_num(s['recoil'], lang, True)} of it hurts you")
    if s.get("hpcost"):
        out.append(f"به‌جای ریاتسو {_num(s['hpcost'], lang, True)} جان می‌گیرد" if fa else f"costs {_num(s['hpcost'], lang, True)} HP instead of reiatsu")
    if s.get("steal_re"):
        out.append(f"و {_num(s['steal_re'] * k, lang, True)} ریاتسوی دشمن را می‌گیری" if fa else f"and steals {_num(s['steal_re'] * k, lang, True)} of the foe's reiatsu")
    if s.get("brk"):
        out.append(("سپر دشمن را می‌شکند" if s["brk"] >= 1 else "سپر دشمن نصف می‌شود") if fa else ("breaks the foe's barrier" if s["brk"] >= 1 else "halves the foe's barrier"))
    if s.get("reflect"):
        out.append(f"و {_num(s['reflect'] * k, lang, True)} آسیب ضربه‌ی بعدی دشمن برمی‌گردد" if fa else f"and {_num(s['reflect'] * k, lang, True)} of the foe's next blow comes back")
    if s.get("heal"):
        out.append(f"{_num(s['heal'] * k, lang, True)} جان" if fa else f"heals {_num(s['heal'] * k, lang, True)} HP")
    if s.get("cleanse"):
        out.append("و پاک شدن اثرهای بد" if fa else "and clears the bad effects")
    if s.get("shield"):
        out.append(f"سپر {_num(s['shield'] * k, lang, True)} جان" if fa else f"a barrier of {_num(s['shield'] * k, lang, True)} HP")
    if s.get("hot"):
        v, n = s["hot"]
        out.append(f"{_fa(lv_turns(n, lv))} نوبت، هر نوبت {_num(v * k, lang, True)} جان" if fa else f"{_num(v * k, lang, True)} HP a turn for {lv_turns(n, lv)} turns")
    if s.get("sot"):
        v, n = s["sot"]
        out.append(f"{_fa(lv_turns(n, lv))} نوبت، هر نوبت سپر {_num(v * k, lang, True)}" if fa else f"a {_num(v * k, lang, True)} barrier a turn for {lv_turns(n, lv)} turns")
    if s.get("re"):
        out.append(f"و {_num(s['re'] * k, lang, True)} ریاتسو" if fa else f"and {_num(s['re'] * k, lang, True)} reiatsu")
    if s.get("evade"):
        e = s["evade"]
        what = ("ضربه‌ی بعدی دشمن، فیزیکی یا ویژه،" if e.get("all") else "ضربه‌ی فیزیکی بعدی دشمن") if fa else ("the foe's next blow, physical or ability," if e.get("all") else "the foe's next physical blow")
        if e.get("n", 1) > 1:
            what = (f"{_fa(e['n'])} ضربه‌ی بعدی دشمن، هر کدام" if fa else f"the foe's next {e['n']} blows, each")
        p = lv_p(e["p"], lv) if e["p"] < 1 else 1.0
        txt = (f"{what} {_num(p, lang, True)} شانس خطا" if p < 1 else f"{what} خطا می‌رود") if fa else (f"{what} {_num(p, lang, True)} to miss" if p < 1 else f"{what} misses")
        if e.get("c"):
            txt += (f" و ضدحمله‌ی ×{_num(e['c'] * k, lang)} می‌زنی" if fa else f" and you counter for x{_num(e['c'] * k, lang)}")
        if e.get("t"):
            txt += (" (فقط نوبت بعد)" if fa else " (next turn only)")
        out.append(txt)
    if s.get("buff"):
        b = scaled_buff(s["buff"], lv)
        if race == "arrancar" and s.get("arr"):
            b.update(scaled_buff(s["arr"], lv))
        out.append(_buff_text(b, lang, False))
    if s.get("debuff"):
        out.append(_buff_text(scaled_buff(s["debuff"], lv), lang, True))
    if s.get("dist") == "pull2":
        out.append("دشمن ۲ خانه نزدیک کشیده می‌شود" if fa else "pulls the foe 2 zones closer")
    if s.get("copy"):
        out.append("و بافر فعال دشمن مال تو می‌شود" if fa else "and the foe's active buffs become yours")
    if s.get("rewind"):
        out.append("جانت به مقدار ۲ نوبت قبل برمی‌گردد" if fa else "your HP returns to what it was two turns ago")
    if s.get("mask_full"):
        out.append("هالوی درون دیگر سرکشی نمی‌کند و تا پایان نبرد آسیب +۱۰٪" if fa else "the Hollow inside stops rebelling, +10% damage for the rest of the fight")
    if s.get("fatigue"):
        out.append(f"بعدش {_fa(s['fatigue'])} نوبت خسته‌ای" if fa else f"then you are spent for {s['fatigue']} turn")
    if s.get("after"):
        out.append(("بعدش " if fa else "afterwards ") + _buff_text(s["after"], lang, False))
    if s.get("once"):
        out.insert(0, "یک بار در نبرد:" if fa else "once a fight:")
    # lead phrases ("one gathering turn, then", "closes the gap and") run into the next part; the rest are a list
    text, glue = "", ""
    for part in out:
        p = part
        for lead in (("و ", "ولی ") if fa else ("and ", "but ")):
            if glue and glue != " " and p.startswith(lead) and lead.strip() in ("و", "and"):
                p = p[len(lead):]
        text += glue + p
        ends_lead = p.endswith(("بعد", " و", ":")) if fa else p.endswith(("then", " and", ":"))
        glue = " " if ends_lead else ("، " if fa else ", ")
    return text


def fixed_text(fid: str, lv: int, lang: str) -> str:
    import re
    fx = FIXED[fid]
    s, k = fx["d_fa" if lang == "fa" else "d_en"], lv_k(lv)

    def rep(m):
        kind, v = m.group(1), float(m.group(2))
        if kind == "m":
            return ("×" if lang == "fa" else "x") + _num(v * k, lang)
        if kind == "s":
            return _num(v * k / 100, lang, True)
        if kind == "t":
            return _fa(lv_turns(int(v), lv)) if lang == "fa" else str(lv_turns(int(v), lv))
        return str(v)
    return re.sub(r"\{(m|s|t):([\d.]+)\}", rep, s)


def cost_text(t: dict, lv: int, lang: str) -> str:
    s = t["spec"]
    if s.get("hpcost"):
        return _num(s["hpcost"], lang, True) + (" جان" if lang == "fa" else " HP")
    return _num(lv_cost(t["cost"], lv), lang, True) + (" ریاتسو" if lang == "fa" else " reiatsu")


def stat_mix(race: str, fam: str, t: dict = None) -> dict:
    if t and t["spec"].get("stat"):
        return dict(t["spec"]["stat"])
    if race == "fullbringer":
        return {"weapon": 1.0}
    f = FAMILIES.get(fam) or KIDO_FAMS.get(fam) or FIXED.get(fam) or {}
    return dict(f.get("stat") or {"zanjutsu": 1.0})


def stat_text(mix: dict, lang: str) -> str:
    fa = lang == "fa"
    parts = []
    for k, v in sorted(mix.items(), key=lambda kv: -kv[1]):
        nm = STAT_NAMES.get(k, (k, k))[0 if fa else 1]
        parts.append(nm if v >= 0.999 else f"{_num(v, lang, True)} {nm}")
    return " + ".join(parts)


# ---- cards ---------------------------------------------------------------------------------------------------------------
def card_id(fam: str, tid: str) -> str:
    return f"ab_{fam}_{tid}"


def fixed_card_id(fid: str) -> str:
    return f"abx_{fid}"


def _build_cards():
    out = []
    for fam, F in FAMILIES.items():
        races = races_of_family(fam)
        for t in F["types"]:
            rar = RARITIES[t["rar"]]
            iid = card_id(fam, t["id"])
            out.append({
                "_id": iid, "item_id": iid, "category": "ability_card", "subtype": "ability_card", "race": races[0] if races else None,
                "races": races, "name_fa": f"کارت {F['fa']}: {t['fa']}", "name_en": f"{F['en']} Card: {t['en']}",
                "desc_fa": f"نوع «{t['fa']}» خانواده‌ی {F['fa']} را باز می‌کند. اگر داشته باشیش، کارت تکراری برای ارتقای لِوِل خانواده است. فقط برای: "
                           + "، ".join({"shinigami": "شینیگامی", "visored": "ویزورد", "quincy": "کوئینسی", "hollow": "هالو", "arrancar": "آرانکار",
                                        "fullbringer": "فول‌برینگر", "human": "انسان"}[r] for r in races),
                "desc_en": f"Opens the «{t['en']}» type of {F['en']}. A duplicate raises the family's level. Only for: " + ", ".join(r.title() for r in races),
                "rarity": rar, "stats": {}, "effect": {"type": "ab_card", "fam": fam, "tid": t["id"], "races": races},
                "slot": None, "level_req": 1, "base_price": int(PRICE[rar] * 0.5), "sell_price": int(PRICE[rar] * 0.2),
                "tradeable": True, "stack_max": 99,
            })
    for fid, fx in FIXED.items():
        races = races_of_fixed(fid)
        rar = RARITIES[fx["rar"]]
        iid = fixed_card_id(fid)
        out.append({
            "_id": iid, "item_id": iid, "category": "ability_card", "subtype": "ability_card", "race": races[0] if races else None,
            "races": races, "name_fa": f"کارت {fx['fa']}", "name_en": f"{fx['en']} Card",
            "desc_fa": f"لِوِل «{fx['fa']}» را بالا می‌برد (در پنل توانایی‌ها، با سکه).", "desc_en": f"Raises the level of «{fx['en']}» (in the ability panel, with coins).",
            "rarity": rar, "stats": {}, "effect": {"type": "ab_card", "fam": fid, "tid": None, "races": races},
            "slot": None, "level_req": 1, "base_price": int(PRICE[rar] * 0.5), "sell_price": int(PRICE[rar] * 0.2),
            "tradeable": True, "stack_max": 99,
        })
    return out


ABILITY_CARD_ITEMS = _build_cards()
ABILITY_CARDS_BY_RACE = {}
for _c in ABILITY_CARD_ITEMS:
    for _r in _c["races"]:
        ABILITY_CARDS_BY_RACE.setdefault(_r, {r: [] for r in RARITIES})[_c["rarity"]].append(_c["_id"])

# old race technique cards rc_{race}_{slot}_{nn} become duplicates of their family's default type
OLD_SLOT_FAMILY = {(race, act): fam for race, slots in RACE_SLOTS.items() for act, fam, _i in slots}


def old_card_to_new(race: str, slot: str):
    fam = OLD_SLOT_FAMILY.get((race, slot))
    if not fam or fam in KIDO_FAMS:
        return None
    tid = (DEFAULTS.get(race) or {}).get(slot) or FAMILIES[fam]["types"][0]["id"]
    return card_id(fam, tid)
