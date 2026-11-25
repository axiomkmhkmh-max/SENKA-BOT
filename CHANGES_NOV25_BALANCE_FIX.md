# Nov 25 — Kyōka, relics, artifacts and dungeon economy

- Restored a meaningful sealed-state damage multiplier for Kyōka Suigetsu while preserving its tested Shikai/Bankai resonance scaling.
- Added two more relic equipment slots. Slots unlock at levels 1, 35, 60 and 85; equipped relic bonuses now use the same level-aware slot calculation as the equipment panel.
- Added real combat passives and Persian/English descriptions to signature/Mythic artifacts that previously only had stat bonuses.
- Reduced dungeon XP multipliers to curb runaway leveling from repeated high-tier dungeon clears.
- Increased dungeon-key crafting material and coin costs; added daily key crafting caps: 4 Nightmare, 2 Abyss and 1 Legendary per player.
- Kept the event recovery path that frees a stale `settling`/completed event slot during scheduler ticks. A live MongoDB event cannot be closed from a source ZIP; deploy-time/database action is still required if the current event document remains active.


## Kyōka Suigetsu stat scaling

- Illusion Strike, False Reality's decoy counter, Mind Distortion, and Phantom Step now use one explicit damage formula: 60% effective Reiatsu + 40% effective Zanjutsu, plus weapon attack.
- Upgrading either Reiatsu or Zanjutsu increases these techniques' damage. The battle header displays the effective values and scaling weights in both Persian and English.
- Added regression tests for all four actions, checking Reiatsu-only and Zanjutsu-only upgrades independently.
