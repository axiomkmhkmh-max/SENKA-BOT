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
* New live keys (see `config.GAME_DEFAULTS`): `drop_*`, `art_*`, `log_*`. New collections: `drops`, `artifacts`, `art_listings`, `action_logs`; new character field `artifact` (no migration needed).
