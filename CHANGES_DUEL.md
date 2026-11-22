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
