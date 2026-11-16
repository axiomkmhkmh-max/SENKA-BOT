# Changes: race balance, Bleach race identity, respec/race-change fix, group commands

## Race balance (data_races.py)
- Every race now has the same base total (40 points), so no race starts stronger than another.
  Strength comes from level, items and training, not from the race name.
- Each race keeps one signature bonus of similar size:
  Shinigami kido +5%, Quincy pierce +10%, Hollow HP +8%, Arrancar defence +6%,
  Fullbringer crit +4%, Visored dmg/def +3% (locked), Human XP +10% and crit +3%.
- Bleach identities kept: Shinigami/Visored get Kidō and Bankai, Hollow/Arrancar get Resurrección,
  Quincy has no Kidō, humans and Fullbringers have no Kidō or Bankai (data_race_rules.py).

## Respec and race change (intents.py, handlers_core.py, service_respec.py)
- Root cause: /respec and /trade pointed at intents "resp" and "trdhub" that were not in the intent
  table, so the slash command crashed (KeyError) and typed phrases like "ریست استت" were "unknown".
  Both are now registered.
- Admin shortcut "ریست <id>" no longer swallows the player phrase "ریست استت" (multi-word player
  phrases win over admin shortcuts).
- Existing characters are moved onto the new bases once at startup (service_respec.rebase_race_stats_once,
  marker in the `migrations` collection). Allocated points are kept.

## Group chats (handlers_core.py)
- Every command now works in groups (the old GROUP_OK whitelist is no longer enforced).
- Admin text commands work in groups for admins only. Admin-only panels stay hidden from non-admins.
- Registration stays private: an unregistered user is told to use the private chat.
- Note: panels that show personal data (profile, bag, coins) post in the group for everyone to see.

## Tests
- test_race_balance.py: base totals, mod sizes, Kidō/Bankai rules, rebase maths, slash-command routing.
- Not runnable in the build sandbox (aiogram/motor could not be installed): the handler changes were
  compile-checked only. Run the bot against a test MongoDB before release.

## Espada raid roster (data_espada_raid.py)
- Added Grimmjow (7), Zommari (8), Aaroniero (9) and Yammy 0/10 (10) as raid bosses with phase-2 patterns.
- Existing IDs 1-6 are unchanged because stored raid documents reference them (Szayel stays at 6 internally).

## Human signature (data_bleachfx.py, engine.py, locale_bleachfx.py)
- Replaced the invented "Fighting Spirit" with Orihime's Santen Kesshun: a shield worth 20% of max HP.

## Soul Artifact drops (data_artifacts.py, config.py, service_drops.py, handlers_drops.py)
- Root cause: artifacts only came from the 12% branch of automatic drops, and those drops were capped at
  about one per hour per group. That works out to roughly one artifact every 14 busy hours.
- Fix: a pity timer. If a group has gone drop_art_pity_hours (default 6) without an artifact, its next drop is
  an artifact. The timer is stored as groups.last_art_drop and set when an artifact drop is posted.

## Human passive: Spiritual Awareness (data_races.py, engine.py, service_combat.py)
- Humans deal 10% more damage to hollow foes. Hollow foes are the wild enemies that use the Cero signature
  (hollow locations and hollow names). Enemy fighters carry `foe = "hollow"`; the bonus is applied in engine._foe_mult.

## Known issue found, not changed: Zanpakutō blade IDs are not items
- service_combat and handlers_zanpakuto key per-blade behaviour on IDs such as zangetsu or zanka_no_tachi.
  None of these IDs exists in data_items.ALL, so the per-blade bonuses (blade_style) can never fire.
  Shikai and Bankai still work with the generic bonus. Adding roster blades needs a decision about how
  players obtain a blade (weapon items or a separate list). This is not done yet.

## Visored: reachable through the Visored Gauntlet (data_races.py, service_respec.py, handlers_respec.py, service_combat.py)
- Visored was locked for everyone, so its existing mask ladder (mask, controlled mask, mastered Hollowfication)
  could never be reached. A Shinigami who clears the Visored Gauntlet now gets characters.visored_unlocked = True.
- Change race and the race picker accept Visored only when that flag is set (race_selectable).
- Not done: a separate Hollowfication mechanic. The existing race ladder is used as it is.

## Not started: Xcution / Fullbring system
- Fullbringers can be picked and already have a progression ladder. The Xcution gang system (groups, ranks,
  power siphoning) is not built.

## Canon moves: Quincy Blut and Arrancar Bala (data_bleachfx.py, data_race_rules.py, engine.py, render.py, handlers_combat.py, locale_bleachfx.py)
- Quincy: blv (Blut Vene, shield 18% of max HP) and bla (Blut Arterie, 25% more damage for 2 turns). Both share the special cooldown.
- Arrancar: bal (Bala, 1.3x damage with 25% armour pierce). Shares the special cooldown.
- Race gating is in data_race_rules.RACE_ABILITIES. Buttons appear in the combat panel only when the engine allows them.

## Hollow Negación and Garganta, Visored Cero (data_bleachfx.py, data_race_rules.py, engine.py, render.py, handlers_combat.py, locale_bleachfx.py)
- Hollow: neg (Negación, shield 15% of max HP). Hollow and Arrancar: gar (Garganta, opens the full gap, cost 15% reiatsu).
- Visored signature changed from Shunpo to Cero. Shunpo stays as normal movement for everyone.
- Tests: test_hollow_moves.py.

## Zanpakutō: blade catalogue, unlock gates and the blade-ID root fix (data_zanpakuto.py, handlers_zanpakuto.py, service_combat.py)
- Root cause: the blade was taken from the weapon in hand, so blade-specific names and bonuses never matched.
  Now the blade is chosen from the catalogue (zanpakuto.blade_id). Old weapon ids are dropped on the next load.
- 11 blades added (19 in total). Only Shikai names are listed; Bankai names are not invented.
- Unlock: each blade opens at a character level (BLADE_UNLOCK). Gates are design values.
- Choice panel: "تغییر تیغه" / "Choose blade" in the Zanpakutō panel (actions znpb, znpc).
- Tests: test_zanpakuto_blades.py.

## Started: Xcution (DESIGN_XCUTION.md) and Bount (DESIGN_BOUNT.md)
- Designs only. Each has open questions about economy and balance, to be answered before building.

## Xcution slice 1 and Bount slice 1 (data_gangs.py, service_gangs_hook.py, handlers_gangs.py, service_combat.py, intents.py, handlers_core.py)
- Xcution: Fullbringers join at the hideout (panel: "اکسکیوشن" / "xcution"). Wins there add siphon points (daily cap 60).
  Ranks add 2% damage. Leaving is free; rejoining waits 24 hours.
- Bount: a win in the mansion gives soul absorption coins (daily cap 500), for every race.
- Tests: test_xcution_bount.py.
- Not built: Xcution gang wars and boss, Bount seal.

## Race balance by fight type (data_race_rules.py, engine.py, service_combat.py, test_race_balance.py)
- Each race now has a damage multiplier per fight type: pvp (duel vs a player), hollow (wild Hollow foe),
  boss (dungeon final stage and Soul Tower Warden floors), pve (other wild enemies) and world_boss (shared-HP
  world boss, every hit counts).
- Table: data_race_rules.RACE_CONTEXT_DMG, applied in engine._deal through fight_context and ctx_dmg_mult.
- Foes are tagged in service_combat.pve_start: Hollow foes foe="hollow", dungeon/tower bosses foe="boss", other
  wild enemies foe="pve". service_world.boss_hit tags world boss hits foe="world_boss".
- Tuned with a duel simulator at level ~40: equal allocated points for every race, same weapon and armour.
  Results on fresh seeds (about 180 duels per pair, so each figure is only accurate to about +/-4 points):
  pvp 49-51%, hollow 43-49%, boss 41-48%, pve 45-57% (the least certain figure; wild-enemy samples swing about 8 points between runs), world_boss damage per hit 97-103 (100 = average).
- Main changes from the old baseline: Shinigami x1.3 damage in all three contexts, Quincy x1.2, Fullbringer x1.1,
  Visored and Human about x1.05-1.13, Hollow and Arrancar x0.8 in pvp and hollow fights.
- Other bosses (Hollow raid, Xcution, Bount) are not tagged yet and get no fight-type multiplier.
- Caveat: the simulator is an approximation of the real fights (no real items, no player skill, enemy scale
  calibrated to about even). Re-run the balance numbers on real battle logs before release.
