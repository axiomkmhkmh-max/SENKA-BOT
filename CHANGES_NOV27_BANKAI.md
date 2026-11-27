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

**Blade abilities panel** (`znpa`, button «📖 توانایی‌های تیغه» on the Zanpakutō panel): shows the chosen blade's technique, finisher,
its Bankai finisher, bonuses, the Bankai call and how to unlock the buttons in a fight; buttons open any reachable blade and choose it.

**Bug fix: blade ability buttons never appeared** for anyone who had not unlocked Shikai in the Zanpakutō panel (level 20 + bond 50), even though the
in-fight 🗡 Shikai button opens at level 10. `service_combat.build_player` now gives the technique / finisher to any chosen blade
(`data_zanpakuto.abilities_open`; flip `ABILITIES_NEED_PROFILE_SHIKAI` to True for the old rule). The in-fight Shikai gate is unchanged.

## Round 3 — simple abilities that change in Bankai, and the Hōgyoku clear

**Every blade now has two simple abilities (besides the finisher), and both turn deadlier when the Bankai is open.**
- 🗡 technique (`data_zanpakuto.blade_technique`): gets `bk` = Bankai name + more damage + an extra effect (burn / bleed / weaken / freeze chance).
  Per-kind table `BANKAI_TECH_KIND`, names `BANKAI_TECH_NAME`, hand-tuned `BANKAI_TECH_OVERRIDE` (Zanka, Katen).
- 🔰 second ability `b2` (`blade_b2`, new engine action `b2`, own cooldown `b2_cd`): guard / focus / snare / drain / hex, per blade
  (`BLADE_B2`; blades without an entry get one by technique kind). Bankai form: bigger barrier + mend, 1.55x buff, 60% freeze, drain + bleed, double effects.
- Buttons show the Bankai name with 💥 once the Bankai is open; combat log names the ability. Kyōka keeps its own kit.
- The «📖 توانایی‌های تیغه» panel lists technique, b2 and finisher with their Bankai forms.
Files: data_zanpakuto.py, engine.py (`b2` action, `_blade_fx`), service_combat.py, service_fightfx.py, handlers_combat.py, render.py, handlers_zanpakuto.py.

**Hōgyoku taken from everyone**: admin command `/clear_hogyoku` (level 80, two-step: `/clear_hogyoku_yes <code>`).
It vacates the orb (`hogyoku.main.holder = None`; the document is kept so `hogyoku_state` does not give it to the top Espada again),
clears the `hogyoku` flag on every character, frees every Hōgyoku Shard relic (`artifact_free("art_hogyoku")`) and closes open Hōgyoku duels.
Nobody is chased on the wanted list until you `/give_hogyoku` it to someone. Run it once from the admin account.

**Wheels: 2 free spins a day** (`config.GAME_DEFAULTS["wheel_free_daily"]` 3 -> 2, shared by all the themed wheels). The wheel page shows «n/2».
If you ever changed it from the admin panel (`wheel_free_daily`), the saved value in MongoDB (`settings.game`) overrides this default.
Urahara's wheel (`wheel`: 1 free + `wheel_extra_daily` paid spins) is unchanged.

**Test fix**: `test_wheels` imported service_extras (needs pymongo) and failed wherever the Mongo libs are missing. It now imports through `_stubs.import_with_stubs`; `_stubs.py` got a `pymongo.errors` stub and no-op fallbacks for names imported from the stubbed service_player / database / service_log.
