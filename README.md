# SENKA | @BleachArenaBot

Bleach-themed MMORPG for Telegram. Python 3.11+, aiogram 3, MongoDB (motor), Railway. All files live in the project root.

## Deploy (Railway)
1. Push these files to GitHub, create a Railway service from the repo.
2. Variables: `BOT_TOKEN`, `MONGODB_URI`, `OWNER_ID`, `HMAC_SECRET` (>= 32 chars). Optional: `DATABASE_NAME`, `LOG_LEVEL`, `DROP_PENDING_UPDATES`.
3. Run **one** instance (a DB lease already stops duplicate schedulers, polling still needs one).
4. Health check: `GET /health`.

## Chosen design (live-tunable by admin `set <key> <value>`)
No second currency · hardcore PvP (ranked, anti-farm caps) · balanced economy · world boss every 45 min ·
gacha = characters + gear + awakening stars · bilingual groups (`group language fa|en|both`) · fully free · balanced-to-hard progression.

## Player words (the game is driven by words, no keyboards)
Typing `/` shows Telegram's command list (home, profile, explore, forge, ...); every command simply runs the same word router.
home, profile, explore, battle, bag, market, quests, summon, squad, ranking, daily (and Persian equivalents). In groups: reply `duel`.

## Admin (text, private chat)
`stats`, `user <id>`, `ban/unban <id>`, `warn <id>`, `give|take <id> coins|xp|item ...`, `item <id> base_price|sell_price|attack|level_req <n>`,
`set <key> <value>`, `maintenance on|off`, `broadcast fa|en|all <text>`, `reset <id>` + `confirm <code>`, `addadmin|rmadmin <id>` (owner). In a group: `spawn boss`.
Every action is written to `admin_logs`.

## Files
config, security, database, i18n, locale_fa/en, intents, ui, fmt, render · data_* (races, 120 blades, 1033 items, 50 bosses, 38 characters, quests) ·
engine (pure combat) · service_* (player, economy, combat, world, social) · handlers_* · scheduler · main.


## Living world (v2)
One shared world: global boss (every 2h, 20 min, one HP bar for all groups and DMs), Hollow Threat / Stability / Reishi, world events
(Garganta, Siege, Wandenreich), weekly guild territories, World Chronicle, traces/graves, spirit aid, bounties and 30-day seasons.
Items now have real roles (crafting, relics, evolution, cosmetics, pets, books, keys) — see `DESIGN.md`.
Requires **MongoDB 4.2+** (atomic clamped pipeline updates). New live keys are in `config.GAME_DEFAULTS` (`set <key> <value>`).
Admin: `world`, `world set ...`, `world event ...`, `world boss spawn|end`, `world season end`, `world territory reset <loc>`.
Commands added: /world /craft /season.


## Retention loops (v3)
Six small, live-tunable loops (keys in `config.GAME_DEFAULTS`, all `set <key> <value>`); code in `data_extras.py`, `service_extras.py`, `handlers_extras.py`, texts in `locale_extras.py`.
| Word / command | What it is |
|---|---|
| `tower` / برج | Soul Tower: endless floors, a Warden every 5th, HP carries over, weekly leaderboard, milestone loot. Daily rewarded-floor cap (`tower_daily_floors`) stops XP farming. |
| (automatic) | Win chain: consecutive plain PvE wins add `chain_step` (cap `chain_cap`) to coin/XP rewards; a free drop every `chain_bonus_every` wins; a loss breaks it. |
| `dispatch` / اعزام | Send gacha characters on 2/4/8h missions (`dispatch_slots` at once). Reward scales with rarity; role bonus: attacker = coins, caster = XP, tank = material, support = energy. |
| `wheel` / چرخ | Urahara's wheel: 1 free spin a day, `wheel_extra_daily` paid spins at `wheel_cost`. |
| `seat` / درجه | Gotei seat ranks (Unseated → Captain) from season points; icon shown beside the name; one-time promotion rewards. |
| `inner` / دنیای درون | Weekly (`inner_weekly`) two-choice talks with the zanpakutō spirit: blade bond, XP or a short buff. |
New collection `dispatches` (TTL on claimed docs); new character fields `tower, chain, seat, seat_claimed` (created on first use, no migration needed).


## Group drops, Soul Artifacts, Artifact Exchange, log channel (v4)
* **Group drops** (`service_drops.py`, `handlers_drops.py`): while a group chats (`drop_min_msgs` messages from `drop_min_users` different people) a treasure drops now and then. Reply to the drop message with `بردار` / `take` — the first valid reply wins. Admin of the bot: write `دراپ` or `دراپ آرتیفکت` in a group to drop by hand. Group admins: `دراپ خاموش` / `دراپ روشن` (`drops off|on`).
* **Player drops**: in a group a player writes `دراپ <نام آیتم>` / `drop <item name>` to throw one tradeable item from their bag; first reply `بردار` wins, unclaimed items return to the owner. Limits (all `set`-able, `drop_player_*`, `drop_pair_daily`): level 10, account age 24h, 1 per hour, 3 per day, the dropper cannot grab their own drop, and the same pair can exchange at most 2 per day (anti alt-farming). Artifacts cannot be player-dropped.
* **Soul Artifacts** (`data_artifacts.py`): 12 one-of-a-kind treasures, **one copy each in the whole world**, one per player. Passive bonuses plug into `player_bonus`. Words: `آرتیفکت` / `artifact`; world registry shows who owns what.
* **Artifact Exchange** (`axm`, inside the market menu): fixed-price player listings; the artifact is escrowed (its bonus is off while listed); seller fee `art_fee` is burned.
* **Log channel** (`service_log.py`): every action is queued, stored in `action_logs` (14-day TTL) and posted in batches to `LOG_CHANNEL` (default `@senkalog`). **Add the bot as an admin of the channel** with "post messages". Pure navigation clicks are skipped unless `set log_nav on`. `set log_enabled off` stops it.
* **Update notice** (`service_notify.py`): after a deploy whose code differs (hash of all `.py` files), every player gets one message in their language asking for a `/start` (with a Start button). Resumable, ~16 msg/s, skips banned/blocked users. Edit `NEWS_FA/NEWS_EN` in that file before deploying; `NOTIFY_UPDATES=0` turns it off.
* New live keys (see `config.GAME_DEFAULTS`): `drop_*`, `art_*`, `log_*`. New collections: `drops`, `artifacts`, `art_listings`, `action_logs`; new character field `artifact` (no migration needed).


## Direction: gameplay-first (v5)
SENKA is a combat/progression/competition MMORPG. Story mode is **retired**: the Story button, `story` word and `/story` command are gone, and the old panel only shows a short notice. Saved `story_progress` documents are untouched. NPC-style menus stay short and functional. New work is judged by: better combat, character growth, player competition, loot/collection, group play, or a reason to keep playing.


## Bleach content pack 2 (data-only, additive)
- 7 locations: Shinigami Academy, Inuzuri, Urahara's Training Ground, Palace of Penitence (Senzaikyū), Maggot's Nest, Garganta Tunnel, Muken.
- 5 dungeons (each with 4 key difficulties + key recipes): Academy Final Exam, Urahara's Training Pit, Senzaikyū Tower, Maggot's Nest, Muken.
- 11 world bosses (`boss_51`..`boss_61`, only existing traits), 39 gacha characters (`ch_81`..`ch_119`), 9 organisations, 5 one-of-a-kind artifacts, 2 dispatch missions, 8 Soul Tower enemies, 10 named Hadō/Bakudō spells.
- Rule: old ids never change. New items are appended (keys come last in `data_items.PLAN`); only the 10 Kidō cards that gained a spell name were renamed (id, stats and effect unchanged).
- When adding a dungeon: add it to `data_races.DUNGEONS`, `DUNGEON_IDS` in **both** `data_items` and `data_crafting`, raise the `key` count in `PLAN` (5 per dungeon) and add `DUNGEON_LORE`. When adding a location: `LOCATIONS`, `LOC_DESC` and `LORE`.
- Tests: `python -m unittest discover -s tests -v` (pure data checks, no MongoDB/Telegram needed).


## Bleach content pack 3 (data-only, additive)
- 8 locations: Kurosaki Clinic, Seireitei Gate (White Road), Kuchiki Manor, Shiba Estate, Visored Warehouse, R&D Institute, Las Noches Throne Hall, Schatten Bereich. Wired into `LOC_DESC`, `LORE`, the Siege / Garganta / Winter War event location lists.
- 4 dungeons (4 × 5 key difficulties + key recipes): Clinic Night Watch, Visored Gauntlet, SRDI Laboratory, Depths of Schatten Bereich. `DUNGEON_IDS` (items + crafting), `PLAN` key count (60 → 80), `_KEY_COST_K` and `DUNGEON_LORE` updated.
- 12 world bosses `boss_62`..`boss_73` (Ikkaku, Renji, Rukia, Nelliel, Komamura, Hitsugaya, Yoruichi, Urahara, Ukitake, Kyōraku, Ichibe, Ichigo) using only existing traits.
- 30 gacha characters `ch_120`..`ch_149` (Rare+ have epithets), 8 organisations, 6 one-of-a-kind artifacts, 6 story quests (`arcx*`), 6 dispatch missions, 12 Soul Tower enemies, 3 named spells (Seki, Tenteikūra, Zangeki).
- Rule kept: old ids never change. Only 3 Kidō cards gained a spell name (id, stats and effect unchanged).
- Tests: `python -m unittest discover -s tests -v` (pure data checks; no MongoDB / Telegram needed).


## Bleach content pack 4 (data-only, additive)
- 8 locations: Junrinan, Karakura High School, Urahara Shop, 4th Division Relief Station, Captains' Assembly Hall, Jigoku, Sternritter Hall, Hōgyoku Chamber.
- 4 dungeons (+20 keys, key count 80 → 100): Karakura High Midnight, Captains' Assembly Trial, Pit of Jigoku, Hōgyoku Vault.
- 13 world bosses `boss_74`..`boss_86`, 25 gacha characters `ch_150`..`ch_174` (Bankai / Resurrección / Shikai forms of fan favourites), 6 organisations, 5 artifacts, 6 quests (`arcy*`), 6 dispatch missions, 12 Soul Tower enemies.
- Old ids unchanged (verified against the pack 3 build). Tests: `python -m unittest discover -s tests -v`.


## Bleach content pack 5 (data-only, additive)
- 8 locations: Karakura Riverbank, Kusajishi (Rukongai 79), Bount Mansion, Xcution Hideout, Captive's Chamber (Las Noches), Precipice World, Seireitei in Ruins, Zero Division Hall. Wired into `LOC_DESC`, `LORE`, and the Siege / Garganta / Winter War / Dangai event location lists.
- 4 dungeons (+20 keys, key count 100 → 120): Riverbank Vigil, Bount Mansion Labyrinth, Run of the Precipice World, Zero Division Trial. `DUNGEON_IDS` (items + crafting), `PLAN` key count, `_KEY_COST_K` and `DUNGEON_LORE` updated.
- 12 world bosses `boss_87`..`boss_98` (Kon, Jinta, Kaien, Giriko, Momo, Kira, Yammy, Nemu, Wonderweiss, Hikifune, Kirinji, Senjumaru) using only existing traits.
- 32 gacha characters `ch_175`..`ch_206`: Rukongai-days / Academy-era childhood forms, Shikai / Resurrección / Bankai forms, Visored and Espada releases (Rare+ have epithets).
- 6 organisations (Detention Unit, Academy Cadets, Gillian Legion, Silbern Court, Bount Circle, Arisawa Dojo), 6 one-of-a-kind artifacts, 6 story quests (`arcz*`), 6 dispatch missions, 12 Soul Tower enemies, 1 named spell (Hadō 57).
- Old ids unchanged. Tests: `python -m unittest discover -s tests -v` (pure data checks; no MongoDB / Telegram needed).


## Bleach combat feel pack (v6) — gameplay, not story
Code: `data_bleachfx.py` (all numbers), `engine.py`, `render.py`, `handlers_combat.py`, `handlers_panels.py`, texts in `locale_bleachfx.py`, tests in `tests/test_bleachfx.py`.
Everything is button-driven inside the existing fight panel; old saved battles keep working (new fighter fields are created lazily).

| Mechanic | How it plays |
|---|---|
| **Signature move per race** (one extra button) | Shinigami/Visored **Shunpo** (next physical hit on you is dodged, then you counter) · Quincy **Hirenkyaku** (blitz strike + dodge/crit for 2 turns) · Hollow/Arrancar **Cero** · Fullbringer **Fullbring Strike** (hit + bleed) · Human **Fighting Spirit** (heal, cleanse, damage buff). Reiatsu cost + cooldown. Shunpo does not dodge Hadō. |
| **Cero** (two steps) | Turn 1 *Gather Cero*: telegraphed in the log and with ⚠️ next to the name. Turn 2 *Fire Cero*: big pierce hit. Answer it: **Guard** (halves), **Bakudō** shield, **stun**, or **interrupt** with one hard hit (>= 22% of an enemy's max HP, 35% of a player's). |
| **Wild enemies use it too** | Hollow-type enemies (Hueco Mundo or names with Hollow/Gillian/Menos/Masked/هالو…) gather Cero; Quincy-location enemies use Hirenkyaku. Their Cero is weaker than a player's so it stays answerable. |
| **Kidō chanting** (`📿`) | Costs the turn and leaves you open (+20% damage taken) but the next Hadō hits x1.6 (Bakudō shield x1.5). The incantation line is printed before the spell (original wording). |
| **Resolve** | Once per battle, a human-controlled fighter pushed under 25% HP gets a small heal, ailments cleansed and a short damage buff. Wild enemies never get it. |
| **Named technique** | A released (Shikai/Bankai) fighter's Heavy strike is shown as "<blade>: <technique>!" by weapon type (Zanpa, Gōka, Shinpan, Gen'ei, Hōkō, Teppeki, Senkō, Ranbu, Kyōgeki). |
| **Spirit pressure** | The opening of a fight prints who crushes whom (the existing fear effect now shows). |
| **Patrol events** | *Konsō*: a lost soul asks to be sent on (XP/coins, every 10th soul a keepsake) — **ignore it and it becomes a Hollow that finds you on a later patrol**. *Pressure*: a strong reiatsu approaches — face it (elite fight, better rewards) or slip away. Event odds are in `handlers_panels.EVENTS`. |

New character fields (created on first use): `konso`, `bx_hollow`, `bx_pending`. `pve_start` gained `force_elite`; `start_pve_panel` now really passes `scale` through.
Measured with a 2-5k-fight simulation (see the tuning notes in `data_bleachfx.py`): each player signature is worth roughly +0..+6 win-rate points, Resolve about +3, an unanswered enemy Cero about -3, interrupting it about +6.
