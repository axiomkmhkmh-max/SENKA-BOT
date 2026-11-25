# Nov 25 – Kyoka rework, ability scaling, hado fix, relics, guild members, artifacts, soul XP
- engine.py: Kyoka abilities stronger (level term, 35% armour ignore, duel cap x1.6), Absolute Illusion 40% skip, 2-turn controls; abilities get a level term (ABILITY_LEVEL_W); Hado level weight 0.35 and 35% max-HP hit cap on player-like foes.
- locale_fa/en: relic effect texts for xp, dmg, def, crit, regen, hunt.
- handlers_panels.py: guild panel lists members (leader/officer first, level).
- data_artifacts.py: Mythic/signature artifact effects strengthened + texts.
- service_soul.py: Gikongan (Mod Soul) 8h XP reward x3.5.
- engine.py / handlers_combat.py: Kyoka's Shikai button now opens for ANY race and stays usable after a duel release (it was locked, so Ultimate was unreachable in duels/dungeons).
- service_combat.py: dungeon XP was 40-390% of a level per clear (legendary = several levels). DG_XP_MULT 1.0, DG_SCALE_XP_EXP 0.30, DG_FINAL_XP_MULT 1.3, and a per-stage cap of 10% (last stage 20%) of the next level.
