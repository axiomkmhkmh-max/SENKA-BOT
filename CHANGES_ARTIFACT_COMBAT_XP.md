# SENKA — Artifact / Combat / XP patch and root-cause audit

## Retained features from the previous patch

- Four combat artifacts: Crimson Devourer (lifesteal), Shadow Monarch Core (shadow damage), The Almighty (precognition/dodge), and Armor of the Undying King (one-use 50% revival).
- Soul King's Tear has signature combat bonuses and a one-use revival.
- Hōgyoku evolves the bearer's damage during combat, up to six stacks.
- Kyōka Suigetsu receives stronger Shikai/Bankai modifiers and Hōgyoku resonance.
- Dungeon XP multipliers remain increased: stage multiplier 1.8, difficulty exponent 0.80, final-stage multiplier 2.5.

## Root-cause fixes in this audit

1. **Shadow Monarch damage bypassed combat rules.** Its extra damage was applied as a second direct HP subtraction after mitigation. That bypassed shields and duel hit caps. The echo is now folded into the original damage packet before the common damage resolver, so shields, mitigation and caps apply normally.
2. **Hōgyoku exceeded its stated ceiling.** Repeatedly multiplying by 1.04 compounded to about +26.5% after six turns. It now stores the battle's base damage multiplier and applies a direct additive progression, stopping at exactly +24%.
3. **Invalid explicit Kidō selections silently cast a different spell.** An invalid in-fight pick now returns no spell instead of unexpectedly casting the strongest available spell. The persistent profile pick still has its deliberate fallback through `ready_hado()`.
4. **Artifact reconciliation could reopen copies beyond the world cap.** It previously clamped `held` to the cap even when the real holder/listing count was higher. Reconciliation now preserves the actual occupied count, blocking additional drops until the over-cap legacy state is resolved.
5. **Mythic/Divine/Transcendent relics were not truly rare.** They had copy caps, but their drop selection weight was still 1.0. Their tiers now have progressively lower weights (Mythic 0.05, Divine 0.02, Transcendent 0.005), and the tier name is displayed in both Persian and English artifact descriptions.
6. **Persian artifact registry descriptions could appear in English.** The artifact list now passes the current locale to the description formatter.
7. **Test harness and assertion defects.** The combat import stub now exposes the HP/Reiatsu helpers required by `service_combat`; the duel shield test now accounts for the legitimate opening guard already granted by `new_state()`.

## Validation performed

- `compileall` completed successfully for the full extracted source tree.
- Focused combat/artifact/Kidō/evolution/duel regression set: **60 passed, 1 skipped**.
- Additional project test modules were run in isolated processes to avoid the repository's global test-module stubs leaking between tests.
- The broad legacy suite is **not fully green** in this environment. Some tests cannot import because `aiogram`, `motor`, or `pymongo` are not installed and network access prevents installing them. Other failures are stale test expectations (for example, old duel multipliers, the old mentor XP API, the old wheel price, or checking a tournament helper in `service_combat` after it moved to `engine_tournament`). These are reported rather than being hidden or misrepresented as passing.
- No live Telegram, Railway, or MongoDB integration test was possible in this environment.

## Still not implemented

- The complete five-ability Kyōka Suigetsu kit and its actual illusion/control states are not yet connected to the battle action menu.
- The complete ten-stage, daily-entry **The Final Judgment** event, including persistence, boss phases, solo restrictions and reward distribution, is not implemented.
- The Shadow Monarch relic currently supplies a bounded shadow-damage echo; a persistent summon/companion subsystem is not included.
