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
