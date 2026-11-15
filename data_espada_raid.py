"""Espada incursions: rare group-chat raids where an Espada opens the Garganta instead of a plain Hollow.

Patterns (readable on purpose, one per Espada):
- "barrier": strikes from a fighter who is NOT released do only a fraction of their damage. The fraction is
  `barrier_hi` above half HP and `barrier_lo` below it (the Espada starts to take the fight seriously).
- "regen": every strike from an unreleased fighter also heals the Espada by `regen` of its max HP. Hesitant groups
  lose ground; a released group ignores this and just hits.
A released fighter (Shikai/Bankai stance) ignores every pattern, so a group that releases together wins.
Pure logic + data, no I/O. Used by service_hollowraid (spawn, strike, settle) and handlers_hollowraid (name, icon).
"""

ESPADA_CHANCE = 0.12  # share of non-Menos incursions that are an Espada, rolled at spawn

ESPADA = {
    1: {"fa": "کویوته استارک", "en": "Coyote Starrk", "hp_mult": 1.6, "phase2": {"barrier": 0.55, "regen": 0.0, "fa": "کویوته استارک بیدار شد: «خسته‌ام، اما تو کافی نیستی.»", "en": "Coyote Starrk wakes: \"I'm tired, but you're not enough.\""}, "barrier_hi": 0.35, "barrier_lo": 0.65,
        "line_fa": "پشت یک صندلی خوابیده؛ بیدار شدنش از همه‌ی کارها سخت‌تر است.",
        "line_en": "Asleep behind a chair; waking him is harder than anything else here."},
    2: {"fa": "باراگان لوئزنبارن", "en": "Baraggan Luisenbarn", "hp_mult": 1.7, "phase2": {"barrier": 0.50, "regen": 0.025, "fa": "باراگان زمان را بلعید و خودش را دوباره جوان کرد.", "en": "Baraggan swallowed time and made himself young again."}, "pattern": "regen", "regen": 0.015,
        "barrier_hi": 0.30, "barrier_lo": 0.60,
        "line_fa": "زمان را از جلوی دهانش می‌خورد؛ هر لحظه‌ی معطلی یعنی پیر شدن بیشتر.",
        "line_en": "He eats time before it reaches him; every moment you hesitate ages you."},
    3: {"fa": "تیا هاریبل", "en": "Tia Harribel", "hp_mult": 1.8, "phase2": {"barrier": 0.60, "regen": 0.0, "fa": "تیا هاریبل سپرش را برای همه‌ی گروه باز کرد: «حالا نوبت توست.»", "en": "Tia Harribel lowers her shield for the whole group: \"Now it's your turn.\""}, "barrier_hi": 0.40, "barrier_lo": 0.70,
        "line_fa": "سپرش را برای یارانش نگه داشته؛ تو تنها کسی نیستی که به آن نیاز داری.",
        "line_en": "She keeps her shield for her comrades; you are not the only one who needs it."},
    4: {"fa": "اولکیورا سیفر", "en": "Ulquiorra Cifer", "hp_mult": 1.9, "phase2": {"barrier": 0.45, "regen": 0.0, "fa": "اولکیورا سیفر دیگر تماشا نمی‌کند؛ نگاهش سرد و کشنده شد.", "en": "Ulquiorra stops watching; his gaze turns cold and lethal."}, "barrier_hi": 0.25, "barrier_lo": 0.55,
        "line_fa": "بی‌احساس‌ترین نگاه گارگانتا؛ هر ضربه‌ی بی‌هدف را ثبت می‌کند.",
        "line_en": "The emptiest gaze in Las Noches; he records every blow that lacks purpose."},
    5: {"fa": "نوئیترا جیلگا", "en": "Nnoitra Gilga", "hp_mult": 2.0, "phase2": {"barrier": 0.70, "regen": 0.02, "fa": "نوئیترا از درد لذت برد و هر ضربه را به خودش برگرداند.", "en": "Nnoitra enjoys the pain and turns every blow back on himself."}, "barrier_hi": 0.35, "barrier_lo": 0.75,
        "line_fa": "از درد لذت می‌برد و از تو بیشتر؛ ضربه‌هایت را بیشتر از هرکسی تحمل می‌کند.",
        "line_en": "He enjoys pain, and more so when it is yours; he takes your blows better than anyone."},
    6: {"fa": "زیل آپورو", "en": "Szayel Aporro", "hp_mult": 1.75, "phase2": {"barrier": 0.50, "regen": 0.02, "fa": "زیل آپورو زخم‌هایش را «پژوهش» کرد و سریع‌تر بهبود یافت.", "en": "Szayel Aporro \"researches\" his wounds and heals faster."}, "pattern": "regen", "regen": 0.01,
        "barrier_hi": 0.30, "barrier_lo": 0.60,
        "line_fa": "هر آسیبی را که می‌بیند، برای آزمایشش یادداشت می‌کند.",
        "line_en": "Every injury you deal becomes a note for his next experiment."},
    7: {"fa": "گریمجو", "en": "Grimmjow Jaegerjaquez", "hp_mult": 2.1,
        "barrier_hi": 0.30, "barrier_lo": 0.60,
        "line_fa": "پانتراى شکارچى؛ هر زخمى فقط گرسنگى‌اش را بیشتر می‌کند.",
        "line_en": "Pantera the hunter; every wound only makes him hungrier.",
        "phase2": {"barrier": 0.45, "regen": 0.0,
                   "fa": "گریمجو: «حالا داره جالب میشه.»",
                   "en": "Grimmjow: \"Now it's getting interesting.\""}},
    8: {"fa": "زوماری روریو", "en": "Zommari Rureaux", "hp_mult": 1.7, "pattern": "regen", "regen": 0.012,
        "barrier_hi": 0.30, "barrier_lo": 0.60,
        "line_fa": "مستیِ سمی؛ هرچه بیشتر بجنگی، بیشتر در خودش فرو می‌رود.",
        "line_en": "Intoxicated calm; the longer you fight, the deeper he sinks into himself.",
        "phase2": {"barrier": 0.50, "regen": 0.02,
                   "fa": "زوماری چشم‌های بیشتری باز کرد و زخم‌هایش را بست.",
                   "en": "Zommari opens more eyes and seals his wounds."}},
    9: {"fa": "آرونیرو آرواروئری", "en": "Aaroniero Arruruerie", "hp_mult": 1.9, "pattern": "regen", "regen": 0.02,
        "barrier_hi": 0.32, "barrier_lo": 0.62,
        "line_fa": "هالوها را می‌بلعد و خودش را از نو می‌سازد.",
        "line_en": "He swallows hollows and rebuilds himself from what he eats.",
        "phase2": {"barrier": 0.50, "regen": 0.03,
                   "fa": "آرونیرو: «خوراک بیشتر، سیری بیشتر.»",
                   "en": "Aaroniero: \"More to eat, more to become.\""}},
    10: {"fa": "یامی یامی لارگو (صفر/ده)", "en": "Yammy Llargo (0/10)", "hp_mult": 2.2,
         "barrier_hi": 0.40, "barrier_lo": 0.70,
         "line_fa": "خشم خام؛ کمترین ظرافت، بیشترین ضربه.",
         "line_en": "Raw rage; the least finesse, the heaviest blows.",
         "phase2": {"barrier": 0.65, "regen": 0.0,
                    "fa": "یامی: «حالا دیگه واقعاً عصبانی شدم!»",
                    "en": "Yammy: \"Now I'm really angry!\""}}
}


def phase(esp, frac):
    """1 above half HP, 2 at or below it (the Espada 'reveals' its second pattern)."""
    return 2 if frac <= 0.5 else 1


def effect(esp, frac, released, dmg, hp, max_hp):
    """Apply the Espada's pattern to one strike. Returns (damage dealt to the Espada, HP it heals back).

    frac: current HP / max HP before the strike. hp / max_hp are used to cap healing at full HP.
    """
    e = ESPADA.get(int(esp or 0))
    if not e:
        return max(1, int(dmg)), 0
    if released:
        return max(1, int(dmg)), 0
    p2 = e.get("phase2") or {}
    if phase(esp, frac) == 2 and p2:
        barrier, regen = float(p2.get("barrier", e["barrier_lo"])), float(p2.get("regen", 0))
    else:
        barrier = float(e["barrier_hi" if frac > 0.5 else "barrier_lo"])
        regen = float(e.get("regen", 0)) if e.get("pattern") == "regen" else 0.0
    out = max(1, int(dmg * barrier))
    heal = min(int(max_hp * regen), max(0, int(max_hp) - int(hp))) if regen else 0
    return out, heal
