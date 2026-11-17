"""Race evolution: one 5-stage path per race, following each race's own road in Bleach, with real combat bonuses.

The stage is stored on the character as `evo` (0..4) and only rises by winning an evolution trial (service_crafting):
the race title is the title of that stage, so the title rises only through evolution, never by level alone.
Bonuses are cumulative: stage 3 has everything of stages 1, 2 and 3. Pure data, no I/O.

Bonus keys (read by service_combat.build_player and engine.py through fighter["evo"]):
  dmg / def / hp / kido   +share on the race modifier (0.10 = +10%)
  crit / pierce            +flat chance / share of defence ignored
  regen                    share of max HP healed at the start of each own turn
  release_turns            extra turns of the spirit-gauge release (Bankai, Resurrección, Vollständig...)
  sig_cd                   cooldown of the race signature move (lower is better; replaces the default)
  sig_mult                 multiplier on the signature strike (Cero, Bringer strike, Soul Strike, Hirenkyaku blitz)
  cero_mult                multiplier on Cero only
  bleed                    bleed chance of the Bringer strike (replaces the default)
  blut                     multiplier on Blut Vene shield and Blut Arterie power
  mask_rage                chance per turn that an active Hollow Mask takes the turn (Visored; replaces MASK_RAGE)
  mask_turns               extra turns of the Hollow Mask (Visored form 1) and of the Advanced Mask (form 2)
  aware                    damage multiplier against Hollows (Human Spiritual Awareness; replaces the default 1.10)
"""

# race -> five stages: ((fa, en) title, bonus added at this stage, (fa, en) short description of the bonus)
EVO_PATHS = {
    "shinigami": [
        (("دانشجوی آکادمی", "Academy Student"), {}, ("شروع راه شینیگامی", "The start of the Shinigami road")),
        (("افسر بی‌کرسی", "Unseated Officer"), {"dmg": 0.05}, ("+۵٪ آسیب", "+5% damage")),
        (("افسر کرسی‌دار", "Seated Officer"), {"kido": 0.10}, ("+۱۰٪ قدرت کیدو", "+10% Kidō power")),
        (("ستوان", "Lieutenant"), {"hp": 0.10, "sig_cd": 3}, ("+۱۰٪ جان، شونپو هر ۳ نوبت", "+10% HP, Shunpo every 3 turns")),
        (("کاپیتان", "Captain"), {"release_turns": 1, "dmg": 0.10}, ("بانکای ۱ نوبت بیشتر، +۱۰٪ آسیب", "Bankai lasts 1 more turn, +10% damage")),
    ],
    "visored": [
        (("هالوفیکیشن", "Hollowfication"), {}, ("ماسک وحشی: ۱۲٪ احتمال از دست دادن کنترل", "Wild mask: 12% chance to lose control")),
        (("حامل ماسک", "Mask Bearer"), {"mask_rage": 0.08}, ("خشم ماسک ۸٪", "Mask rage 8%")),
        (("ماسک مهارشده", "Controlled Mask"), {"mask_rage": 0.04}, ("خشم ماسک ۴٪", "Mask rage 4%")),
        (("استاد ماسک", "Mask Master"), {"mask_rage": 0.0, "mask_turns": 2}, ("ماسک بدون خشم، ۲ نوبت بیشتر", "No mask rage, mask lasts 2 more turns")),
        (("هالوفیکیشن کامل", "Perfect Hollowfication"), {"dmg": 0.10, "cero_mult": 1.2}, ("+۱۰٪ آسیب، سرو ×۱٫۲", "+10% damage, Cero ×1.2")),
    ],
    "quincy": [
        (("شاگرد کوئینسی", "Quincy Apprentice"), {}, ("شروع راه کوئینسی", "The start of the Quincy road")),
        (("کوئینسی", "Quincy"), {"dmg": 0.05}, ("+۵٪ قدرت تیر (آسیب)", "+5% arrow power (damage)")),
        (("اشترن‌ریتر", "Sternritter"), {"crit": 0.10}, ("+۱۰٪ شانس ضربه‌ی کاری", "+10% critical chance")),
        (("اشترن‌ریتر نخبه", "Elite Sternritter"), {"blut": 1.5}, ("بلوت ×۱٫۵", "Blut ×1.5")),
        (("شوتس‌اشتافل", "Schutzstaffel"), {"dmg": 0.15, "pierce": 0.10}, ("+۱۵٪ آسیب، +۱۰٪ نفوذ", "+15% damage, +10% pierce")),
    ],
    "hollow": [
        (("هالو", "Hollow"), {}, ("شروع راه هالو", "The start of the Hollow road")),
        (("گیلیان", "Gillian"), {"hp": 0.15}, ("+۱۵٪ جان", "+15% HP")),
        (("آجوکاس", "Adjuchas"), {"dmg": 0.10}, ("+۱۰٪ آسیب", "+10% damage")),
        (("واستو لورد", "Vasto Lorde"), {"regen": 0.03}, ("هر نوبت ۳٪ جان برمی‌گردد", "Heals 3% HP every turn")),
        (("آرانکار", "Arrancar"), {"release_turns": 1}, ("رسورکسیون ۱ نوبت بیشتر", "Resurrección lasts 1 more turn")),
    ],
    "arrancar": [
        (("نومروس", "Números"), {}, ("شروع راه آرانکار", "The start of the Arrancar road")),
        (("فراسیون", "Fracción"), {"dmg": 0.10}, ("+۱۰٪ آسیب", "+10% damage")),
        (("پریوارون اسپادا", "Privaron Espada"), {"def": 0.10}, ("هیرو: +۱۰٪ دفاع", "Hierro: +10% defence")),
        (("اسپادا", "Espada"), {"cero_mult": 1.3}, ("گرن ری سرو: سرو ×۱٫۳", "Gran Rey Cero: Cero ×1.3")),
        (("سگوندا اتاپا", "Segunda Etapa"), {"release_turns": 1, "dmg": 0.10}, ("رسورکسیون ۱ نوبت بیشتر، +۱۰٪ آسیب", "Resurrección lasts 1 more turn, +10% damage")),
    ],
    "fullbringer": [
        (("بیدارشده", "Awakened"), {}, ("شروع راه فول‌برینگر", "The start of the Fullbringer road")),
        (("فول‌برینگر ماهر", "Skilled Fullbringer"), {"crit": 0.05}, ("+۵٪ شانس ضربه‌ی کاری", "+5% critical chance")),
        (("براینگر", "Bringer"), {"bleed": 0.60}, ("ضربه‌ی براینگر ۶۰٪ خونریزی", "Bringer strike bleeds 60%")),
        (("استاد فول‌برینگ", "Fullbring Master"), {"dmg": 0.10}, ("+۱۰٪ آسیب", "+10% damage")),
        (("فول‌برینگ کامل", "Complete Fullbring"), {"release_turns": 1, "hp": 0.10}, ("رهاسازی ۱ نوبت بیشتر، +۱۰٪ جان", "Release lasts 1 more turn, +10% HP")),
    ],
    "human": [
        (("روح سرگردان", "Wandering Soul"), {}, ("شروع راه انسان", "The start of the Human road")),
        (("آگاه به ارواح", "Spiritually Aware"), {"aware": 1.15}, ("آگاهی روحی: +۱۵٪ آسیب به هالو", "Spiritual Awareness: +15% damage to Hollows")),
        (("مدیوم روحی", "Spirit Medium"), {"sig_mult": 1.8 / 1.6}, ("ضربه‌ی روح ×۱٫۸", "Soul Strike ×1.8")),
        (("انسان بیدار", "Awakened Human"), {"hp": 0.15}, ("+۱۵٪ جان", "+15% HP")),
        (("نگهبان کاراکورا", "Karakura Guardian"), {"release_turns": 1, "dmg": 0.10}, ("بیداری روح ۱ نوبت بیشتر، +۱۰٪ آسیب", "Soul awakening lasts 1 more turn, +10% damage")),
    ],
}

EVO_MAX = 4
# How many stages each race had before this rework (used once to carry old titles over; see service_respec)
OLD_EVO_LEN = {"shinigami": 5, "quincy": 4, "hollow": 5, "arrancar": 4, "fullbringer": 3, "human": 3, "visored": 3}

_ADD = ("dmg", "def", "hp", "kido", "crit", "pierce", "regen", "release_turns", "mask_turns")


def evo_bonus(race: str, stage: int) -> dict:
    """Cumulative bonus of `race` at `stage` (0..4). Additive keys add up; the others take the latest value."""
    out = {}
    for _title, add, _desc in (EVO_PATHS.get(race) or [])[: max(0, min(EVO_MAX, int(stage or 0))) + 1]:
        for k, v in add.items():
            if k in _ADD:
                out[k] = out.get(k, 0) + v
            elif k in ("sig_mult", "cero_mult", "blut") and k in out:
                out[k] = max(out[k], v)
            else:
                out[k] = v
    return out


def evo_title(race: str, stage: int, lang: str) -> str:
    path = EVO_PATHS.get(race) or EVO_PATHS["human"]
    return path[max(0, min(len(path) - 1, int(stage or 0)))][0][0 if lang == "fa" else 1]


def evo_desc(race: str, stage: int, lang: str) -> str:
    path = EVO_PATHS.get(race) or EVO_PATHS["human"]
    return path[max(0, min(len(path) - 1, int(stage or 0)))][2][0 if lang == "fa" else 1]
