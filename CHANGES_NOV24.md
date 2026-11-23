# Nov 24 — Cero / Hollow Claw fix, XP, stats, Soul Hub

## Bugs
- Hollow Claw (3 hits) bypassed the duel hit cap (25% HP per blow -> ~70% per press). One ability press now shares one
  cap (engine.DUEL_PRESS_CAP = 1.2 x hit_cap). Claw m 1.3 -> 0.9.
- Cero / Mask family factor x3.0 / x2.0 -> x2.2 / x1.6 (lv10 Cero ~ Hado 90, Claw below Mask Strike).
## XP
- Dungeon: difficulty counts at power 0.75 (was 0.5), DG_XP_MULT 1.2. Abyss x8 now pays ~x5.7 a plain fight.
- Open world: a win in 1 / 2 turns pays 50% / 70% XP (one-tap farming).
## Stats
- Awakened stats: from level 300 pick 2 stats (upgrade panel); their cap = stat_max + (level - 300). Stat reset frees them.
- Admin: /pts_all -> /pts_yes <code> resets every player's stats to the race base and refunds all points (levels kept,
  over-cap stats like Kido 500 included). /pts_undo yes restores the backup.
## Soul Hub (/soul, "مرکز روح") — service_soul.py, handlers_soul.py
- Inner World duel (weekly mirror fight vs your zanpakuto spirit: bond +25, XP), Urahara training (72h: 6 stat points + XP),
  Human World patrol (group per chat, 4h, +15%/member), Gikongan (uses it_d002: 8h offline farming),
  Dangai run vs the Kototsu (5 steps, run/hide), Reiatsu Clash (3 rounds vs a similar-level player, 5/day).
