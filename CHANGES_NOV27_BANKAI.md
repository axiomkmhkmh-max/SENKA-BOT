# Nov 27 — Bankai scenes + Mythic Zanka no Tachi / Katen Kyōkotsu

**Bankai activation scene (all blades).** When a Shinigami / Visored unleashes the 👑 release in a fight, the log now shows
`«Bankai!!! <Bankai name>»` plus an epic line addressed to the opponent. Same text on the Zanpakutō panel release and the
«بانکای» stance word (that one used to print the Shikai call). Every blade in `BLADE_STAGES` has its own line
(`data_zanpakuto.BANKAI_SCENE`); a blade without one gets a generic scene (`BANKAI_GENERIC`).
Typing «بانکای زانکا نو تاچی» / "Bankai <name>" or just the Bankai name releases it too (`handlers_combat.battle_word`).

**Zanka no Tachi (Yamamoto)**: Mythic, strongest Bankai bonus (0.40, Shikai 0.10), style dmg x1.25 +5% crit,
finisher 6.2 -> in Bankai "Zanka no Tachi: Absolute Ash" (8.2, 50% pierce, burn, cost 30%).
**Katen Kyōkotsu (Kyoraku)**: Mythic, Bankai bonus 0.28, style dmg x1.16 +5% crit, finisher 2.9 x3 hits -> in Bankai
"Karamatsu Shinjū" (3.7 x3, 40% pierce, weaken, cost 28%).

Files: data_zanpakuto.py, engine.py (unleash event carries `bl` + `d`), render.py, handlers_zanpakuto.py, handlers_viral.py,
handlers_combat.py, test_bankai_scene.py (new).
