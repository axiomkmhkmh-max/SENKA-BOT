# Nov 26 update: balance, artifacts, swap, dungeons, catalog, forge mission

All numbers for the balance live in `data_balance.py` (one file to tune).

## 1. Damage, HP, regen, Hadō
- Players have x1.35 HP (`PLAYER_HP_K`, applied in `service_player.max_hp`). Heals, shields and DoT stay measured on the old pool (`engine._hb` divides by the fighter's `hpk`), so regen is relatively weaker.
- Natural + companion regen share one per-turn budget: 3% of max HP (1.8% in duels). Kyōka Shikai heal 10% -> 5%.
- Duel hit cap now follows power: `cap = hit_cap * (att_rating / def_rating) ** 0.75`, clamped x0.6..x1.4. Rating = level + average of the five stats.
- Hadō 70+ share a 3-turn lock; Hadō under 40 come back after 2 turns (was 3).
- Simulation: duel with 12% pet regen went from 201 turns (the cap, never finished) to about 16.

## 2. Artifacts
- Burn / bleed chance abilities replaced by short-fight ones: `opener` (first blow +x%), `open_shield`, `mitigate`, `turn_heal` (engine hooks in `_deal`, `new_state`, `_take_mult`, `service_combat`).
- Changed: Sokyoku, Ryūjin Jakka cane, Visored mask, Pantera, Murciélago, Tiburón, Santa Teresa.
- Artifact swap between two players: `service_artswap.py`, `handlers_artswap.py`, button in the artifact panel (offer -> accept, guarded swap with roll-back, 2/day per player, 1/day per pair, 10 min offers).

## 3. Zanpakutō
- New: Benihime (attack technique + defence finisher: barrier and mend), Katen Kyōkotsu (twin-blade technique, three-hit finisher). Engine: finishers may carry `shield` / `heal`.

## 4. Dungeons
- Chest colours are clipped to the opener's level (`data_dungeon_drops.clip_chest`); the gold chest's bonus pool too.
- Every dungeon has its own fixed final-stage drops (material, potion, book); one is guaranteed on a full clear, `dg_final_day_cap` (2) a day per dungeon.

## 5. Catalog / patch notes
- `data_catalog.py` + `handlers_catalog.py`: item kinds, skins, chests, every dungeon with its drops. Word «کاتالوگ» or the buttons in the skins / dungeon shop panels. The owner has a button that posts everything to the news channel (the bot must be a channel admin).

## 6. Forge mission (ماموریت ساخت)
- `data_wish.py`, `service_wish.py`, `handlers_wish.py`: pick Rare+ gear for your level, collect final drops of 3 dungeons near your level, pay coins, one finished mission per week. Words: «ماموریت ساخت».

## Tests
- New: test_nov26_balance, test_artswap, test_wish; test_dungeon_chests extended.
- Updated to the new rules: test_final_judgment_kyoka, test_kido_system, test_heal_merge, test_duel_rules.
- Full suite: no new failures (27 failing/erroring tests, all of them failed before too).
