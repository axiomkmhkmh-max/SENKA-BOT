# SENKA — Living World design (phases 1–5)

## Item category → real effect (all data-driven: `item["effect"]`, tables in `data_crafting.py`)
| Category | Role |
|---|---|
| material | Craft input (potions, dungeon keys, armor tempering) by group reishi/spirit/hard/any + rarity; forge value 1–3 units by rarity |
| relic | Passive via `player_bonus`: +XP in one location, +drop, +coin, calmer world (more Threat reduction), steadier Seireitei. `relic_slots` (2) |
| evolution | Needed (count + min rarity) for each race evolution trial; stage = displayed title + `evo_bonus_pct` dmg/def per stage. Old players grandfathered by migration |
| cosmetic | aura/trail/banner icons beside the name (ranking, battle log, boss board, chronicle); Fame → tiny XP boost (capped) |
| egg/pet | 6 species = 6 roles: drop, regen (engine), dmg, def, patrol rewards, crit; choose active pet |
| book | xp / timed buff / teach unknown kidō / blade bond |
| key | dungeon entry; also offered to world events for points |
| armor | temper +1..+5 (workshop), applied in `build_player` |
| ring/necklace/weapon/kido_card | already applied in engine; item_card now states effects (`fmt.effect_text`) |

## New collections
`world_state` (_id "main": threat, stability, reishi{loc}, season{id,start,end}, boss_id, event_id, next_*_at, terr_week),
`world_events`, `world_log` (TTL 14d), `territories`, `territory_scores` (TTL 60d), `traces` (TTL), `bounties`,
`counters` (atomic capped counters + TTL, all daily limits), `season_scores`, `seasons`.
New character fields (defaults via migration): `evo, relics, cosmetics, armor_plus, buffs, seen_at`.

## World variables → gameplay
Threat (0–100): enemy power, boss HP/spawn gap, shop prices, triggers Garganta. Stability: XP, triggers Siege.
Reishi[loc]: drop rate there. Written only through `world_adjust` (single clamped pipeline update, MongoDB 4.2+).

## Files
`data_world.py`, `data_crafting.py` (pure) · `service_worldcore.py` (state/chronicle/season pts) · `service_worldstate.py` (on_action, events, territories, season, tick) ·
`service_interact.py` (crowd, traces/graves, aid, bounties) · `service_crafting.py` · `handlers_world.py` (UI + broadcasts) · `service_world.py` (single global boss).

## Anti-abuse (all live `set` keys)
New-account gate (`new_acct_minutes`), daily caps via `counters` (event pts, territory pts, boss paid kills, aid, traces, bounty claims, season pts),
cooldowns, guild min members/level/age for territory, pair cooldown for aid, bounty fee and claim only in ranked non-capped duels.

## Admin (text)
`world`, `world set threat|stability <v>`, `world set reishi <loc> <v>`, `world reset`, `world event <kind>|end`, `world boss spawn|end`, `world season end`, `world territory reset <loc>`.
