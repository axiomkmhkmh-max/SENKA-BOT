# Nov 23 — drop limits, Kidō gates, harder levelling

## Roll shop (data_extras2.py, service_adventure.py, handlers_adventure.py)
- Weights: Epic 96 / Legendary 4 (no Rare, no Mythic). 2 rolls per day (ROLL_DAILY_LIMIT, atomic counter). x10 button removed.
## Kidō cards (data_kido.py card_min_level, service_economy.py, service_effects.py)
- Cards 1-59 unchanged (0.8 x number); Epic 60-79 need level 100-195; Legendary 80-99 need level 205-300.
## Mastery upgrades (data_abilities.py, service_abilities.py, handlers_abilities.py)
- Level gate per step: 10,25,45,70,100,140,190,250,300. Cost 25 cards/172k -> 67 cards/516k.
## XP (service_combat.py, config.py)
- Dungeon XP x1 (was x2), last stage x2 (was x3), difficulty multiplier counts as its square root. xp_curve_k 1.5 -> 2.5
  (a value saved in the DB with `set xp_curve_k` overrides the default).
## Other drop sources (service_economy.py, data_wheels.py, service_dungeonshop.py, handlers_dungeonshop.py, config.py)
- Normal drops DROP_W [55,27,12,5,0.9,0.1]; pity legendary 400 / epic 60 / rare 20.
- Wheel weights: Legendary 9->4, Mythic 3->0.8, Legacy 1->0.2; pity_leg 60, pity_myth 250.
- Dungeon chests: silver odds 75/25, gold 92/8; pity bronze 6 / silver 5 / gold 10; gold Tempering Stone 15% -> 8%;
  new daily limit dp_chest_daily = 6 chests (0 = off).
## Tests
- New: test_limits_nov23.py. Updated: test_update_nov19b.py, test_update_nov21.py, test_dungeon_chests.py.
- Pre-existing failures (same before and after): test_kido_system x2, test_update_nov21 x2, test_wheels x1; test_update_nov19b does not import.
