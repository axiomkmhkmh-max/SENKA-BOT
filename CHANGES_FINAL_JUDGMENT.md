# SENKA — Combat, Artifacts, Kyoka Suigetsu & The Final Judgment

## Implemented
- Kyoka Suigetsu now has four Sealed actions, four Shikai upgrades, and Kanzen Saimin. Shikai is an actual four-player-action window followed by a four-turn cooldown; the UI shows remaining duration/cooldown. Cooldowns, Reiatsu costs, accuracy disruption, dodge, mirror reflection, 50% outgoing-damage suppression, defense reduction, critical chance, and timed buffs are resolved in the combat engine.
- Kyoka's release bonuses are applied only when Shikai is actually activated (not merely because Shikai was unlocked in the profile). Bankai further amplifies the active release. Hōgyoku resonance multiplies Kyoka's active Shikai damage by 1.35 and adds dodge; it composes with Hōgyoku's separate six-turn evolution without overwriting either bonus.
- Shadow Monarch's summoned echo uses the ordinary damage pipeline, so boss caps, defense, shields, and dodge still apply.
- Soul King now grants +20% maximum HP, +12% regeneration, +8% damage, and one 50%-HP revival. Lifesteal, Almighty precognition dodge, and Transcendent revival remain wired into the engine. Artifact claiming now reserves the world-state transition and holder slot atomically, including rollback on a failed character update.
- Added The Final Judgment as a solo, once-per-day gauntlet. It contains 100 separate enemy encounters, five consecutive bosses, a sealed-ability stage, an oversized giant, a triple-assault stage, 30 consecutive waves, a full-build Dark Reflection AI, a five-phase abomination, five bosses without healing items, and a five-phase Final Judge. The Final Judge changes mechanics across phases (speed, arena burn, barrier/armor penetration, then Absolute Awakening with chained attacks).
- HP, Reiatsu, gauge, shield and artifact emergency lives carry between encounters; no full reset occurs. Loss ends the attempt. The final clear records a permanent profile title and attempts to award The Almighty through the existing artifact ownership system.
- Dungeon XP multiplier increased from 1.8 to 4.0; final-stage multiplier increased from 2.5 to 3.0.
- Added Persian and English UI text, profile recognition for clearers, and regression tests.

## Engine limitation
The current battle engine is a one-opponent engine. The 100-enemy, five-boss and 30-wave portions are therefore represented as consecutive individual encounters. Stage five represents three simultaneous bosses as one shared triple-assault turn (one primary action plus two follow-up strikes), rather than three independent enemy entities.

## Verification
- `compileall` succeeds.
- 75 focused combat, artifact, event-service and regression tests pass.
- Full suite: 699 tests discovered, 11 failures, 25 errors and 14 skipped. The same 11 failures and all 25 errors were present in the supplied baseline suite (the baseline had 15 failures and 26 errors); no new full-suite failure/error was introduced. Most errors are import/runtime dependency issues because `aiogram`, `motor` and `pymongo` are not installed in this offline environment.
- No live Telegram or MongoDB/Railway integration test was possible in this environment.
