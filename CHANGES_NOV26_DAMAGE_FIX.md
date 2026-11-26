# Nov 26 damage fix (player reports: plain / heavy / Kyoka did ~0 in hard+ dungeons, enemies out-healed blows)

## Bugs
1. **Armour ate whole blows.** `_deal` computes `(attack - armour*0.6) * power`. On a x1.5+ dungeon enemy the armour was larger
   than the attack, so a plain or heavy blow did 0-1 damage and Kyoka techniques fell from thousands to single digits in Abyss.
   Hado never had the problem (armour comes off after its multipliers, and it has a floor), so it looked "constant".
2. **Wild enemies out-healed the player.** Natural regen was raised to 5% (Nov 26) for everyone; only bosses had a reduced share.
   A war commander healed 2,204 a turn against a 2,108 heavy strike.

## Fix (numbers in `data_misc.py`)
- `PVE_ARMOR_FLOOR = 0.30`: a player blow on a wild enemy / hollow / dungeon boss deals at least 30% of its armour-free damage
  (`engine._deal`). The world boss and Final Judgment keep their own floors; counters, echoes, DoT and reflects are untouched.
- `PVE_REGEN_SHARE = 0.35`: `pve` and `hollow` foes recover 35% of the normal per-turn regen (`engine.start_turn`). Bosses keep 20%.

## Tests
- New: `test_pve_armor_floor.py`.
- Updated to the current rules: `test_boss_regen` (wild regen share), `test_update_nov21` (boss damage multipliers, player HP x1.35),
  `test_wheels_service` (Yamamoto's own base price), `test_final_judgment_service` (the closed event is opened for its tests),
  `test_mentor_trade` (`share_to_apprentices` replaced `share_xp`: the master earns, apprentices get the bonus).
- Known open item: `test_gotei_trial.TrainingDuelKit` fails on purpose. `service_combat.duel_accept` / `pvp_settle` no longer use the
  tournament standard kit or call `service_tournament.record_training`, so Gotei Trial training points are never recorded.
