# Duel rework + Legendary dungeon stage 1 (Nov 22)
Rules apply only to player-vs-player duels (never bosses, PvE, or the standard-kit tournament). Tune everything in `DUEL` (data_misc.py).
- hit_cap 0.25: one blow takes at most 25% of the target's max HP (no one-shots)
- floor_share 0.30: a landed blow deals at least 30% of what it would do with the target armour ignored (follows the attacker power, not the target HP)
- mult_cap 3.0: damage perks, buffs, release and Resolve multiplied together stop at x3
- form_cap 2.5: a form's stat multiplier counts at most x2.5
- release costs min(max(1000, 10% pool), 35% pool); one release per duel
- while a release is active: Getsuga, Kido and the Mask button are locked
- Legendary dungeon, stage 1: enemy HP x1.4, damage x0.5 (LEGEND_S1_HP / LEGEND_S1_DMG)
Files: engine.py, data_misc.py, engine_tournament.py, service_combat.py, test_duel_rules.py
- dmg_share 1.0 (off): all duel blows x this share. Tested: 0.7 doubles duel length, 0.5 x4, <=0.35 never ends; 5% is unplayable at current HP/regen

# Cero / Mask / Hado balance (Nov 22)
- FAMILY_DMG_K in data_abilities.py (players only): Cero x3.0, Mask x2.0
- Hado above spell 20 grows 0.05 per number instead of 0.3 (data_kido.py HADO_KNEE / HADO_SLOPE_HIGH); fmt.py shows the new factor
- Hollow Claw m 0.8 -> 1.3, Mask Strike m 2.2 -> 3.0 (before the x2 family factor)
Measured at level 367: plain ~1.6K, Mask Strike ~9.5K, Claw x3 ~13.9K, Cero ~13.4K, Gran Rey ~17.2K, Cero Final ~23.9K, Hado 90 ~22K.
Files: engine.py, data_abilities.py, data_kido.py, fmt.py
