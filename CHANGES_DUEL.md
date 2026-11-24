# Duel rework (Nov 22)
Rules apply only to player-vs-player duels (never bosses, PvE, or the standard-kit tournament). Tune everything in `DUEL` (data_misc.py).

- hit_cap 0.25: one blow takes at most 25% of the target's max HP (no one-shots)
- floor 0.015: a landed blow takes at least 1.5% of max HP (half while guarding); reflect/counter/echo/dot have no floor
- mult_cap 3.0: damage perks, buffs, release and Resolve multiplied together stop at x3
- form_cap 2.5: a form's stat multiplier counts at most x2.5 (Bankai is x3.0)
- release (Bankai/Resurreccion) costs min(max(1000, 10% pool), 35% pool); one release per duel
- while a release is active: Getsuga, Kido (Hado/Bakudo/chant) and the Mask button are locked
- Legendary dungeon, stage 1: enemy HP x1.4, enemy damage x0.5 (LEGEND_S1_HP / LEGEND_S1_DMG)

Files: engine.py, data_misc.py, engine_tournament.py, service_combat.py, test_duel_rules.py (new, 9 tests).

# Mask vs Hado (Nov 22, from a real screenshot: Hollow Claw hits ~1K, Hado 90 hits ~200K)
- Hado damage factor: was 0.7 + 0.3 * n (Hado 90 = x27.7). Now the same slope up to Hado 20, then +0.08 per number (Hado 90 = x12.3). Tune HADO_KNEE / HADO_SLOPE_HIGH in data_kido.py (fmt.py shows the new factor in the spell text).
- Hollow Claw m 0.8 -> 1.3 (3 hits), Mask Strike m 2.2 -> 3.0 (data_abilities.py).
- Files added to this update: data_kido.py, fmt.py, data_abilities.py (engine.py changed again).

# Turn clock and Bakudo cap (Nov 25, from a player report)
- Every duel turn is 5 minutes (`DUEL["turn_seconds"]` = 300; the old live `pvp_turn_seconds` setting stored 30 s and is no longer used by duels).
- First missed turn = automatic Guard (shield). The second missed turn in a row loses the duel (`DUEL["afk_limit"]` = 2, was 3). The panel shows the clock as m:ss.
- Bakudo in duels: the barrier is at most 90% of one ordinary blow the foe lands on the caster (`DUEL["bak_hit_share"]` = 0.9), after the old x0.5 share. Measured at level 300, 37K HP: barrier 18,500 vs a 1,863 blow before, 1,677 now. No more immortal Shinigami.
- Files: data_misc.py, config.py, engine.py, service_combat.py, duel_ui.py, test_duel_rules.py (+4 tests).

# Kidō cards 91-99 (Nov 25, from a player report)
- No spell needs the chant any more (`CHANT_REQUIRED` 100): Hadō/Bakudō 1-99 can be cast bare (x0.75 from number 60 up) or after 📿 Chant (full power), so a 99 card is no longer dead weight.
- Hadō 91-99 now always out-hit Kurohitsugi (90, x1.6): x1.7 at 91 up to ~x1.94 at 99 (`hado_params`, `HADO_TOP_FROM`). Costs unchanged (8% for 91+, 2% below).
- The 📿 Chant button also shows for Bakudō-only casters (engine.can "ch").
- Files: data_kido.py, engine.py, test_kido_system.py, test_boss_kido_call.py, test_fix_winter_chant_join.py, CHANGES_DUEL.md.
