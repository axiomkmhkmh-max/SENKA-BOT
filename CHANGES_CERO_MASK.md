# Cero / Mask / Hado balance (Nov 22) - install AFTER senka_duel_update.zip
Its engine.py contains everything from the duel zip too, so it replaces that engine.py.
- FAMILY_DMG_K in data_abilities.py (players only): Cero x3.0, Mask x2.0
- Hado above spell 20 grows 0.05 per number instead of 0.3 (data_kido.py HADO_KNEE / HADO_SLOPE_HIGH); fmt.py shows the new factor
- Hollow Claw m 0.8 -> 1.3, Mask Strike m 2.2 -> 3.0 (before the x2 family factor)
Measured at level 367: plain ~1.6K, Mask Strike ~9.5K, Claw x3 ~13.9K, Cero ~13.4K, Gran Rey ~17.2K, Cero Final ~23.9K, Hado 90 ~22K.
Files: engine.py, data_abilities.py, data_kido.py, fmt.py
