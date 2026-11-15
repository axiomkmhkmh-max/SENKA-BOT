# Canon audit: what the game uses, and where it comes from

Method: each race's abilities were checked against sources found by web search (Bleach wikis and
guides). Anything not in a source is marked as a design choice, not as canon.

## What is canon (verified against the sources below)
- Quincy: bow and arrow (Seele Schneider, Licht Regen), Blut (Vene = defence, Arterie = offence),
  Hirenkyaku (high-speed movement on reishi), Ginto (stores reishi). Sources: Bleach Wiki
  (bleachmedia.fandom.com/wiki/Quincy), myanimelist.net/featured/640, animeexplained.com.
  No Kidō: game rules already enforce this (data_race_rules.py).
- Arrancar: Sonído, Bala, Hierro, Pesquisa, Cero, Resurrección and Segunda Etapa. Sources: Bleach Fan
  Fiction Wiki (Halcón page), tvtropes.org Espada page, fables.gg, en.wikipedia List of Hollows in Bleach.
- Hollow: Cero, Garganta, Negación, Pesquisa; Hollows regenerate quickly. Sources: power-in-bleach-explained,
  en.wikipedia List of Hollows in Bleach.
- Visored: Hollowfication (masks, Cero, Hollow powers). Sources: Bleach Wiki Glossary, sportskeeda Cero guide.
  Hierro is not confirmed for Visored (naruto-bleach.fandom.com, Di Roy's Hierro page).
- Human: ordinary humans have no powers, only spiritual awareness. Orihime has Shun Shun Rikka (Santen Kesshun
  shield, Sōten Kisshun rejection). Chad has Brazo Izquierdo del Diablo. Sources: Bleach Wiki Orihime
  (animeandmangauniverse.fandom.com), kb article, microsoft.com episode guide.
- Shinigami: Zanpakutō, Kidō, Shunpo, Bankai/Shikai. Used in the game as is.
- Fullbringer: sources disagree (some say Hollow-born, some say Ichigo's reiatsu exposure). Game uses
  "Fullbring Strike" as the signature. Not settled.

## What is NOT canon (design choices in this game)
- Base stat totals (40 per race) and modifier sizes. Canon has no numeric stats; these are for balance only.
- Human passive "Spiritual Awareness" (+10% vs hollows): inspired by Tatsuki and Keigo seeing spirits, not a
  mechanic from the source. Labelled as design.
- Visored unlock through the Visored Gauntlet: a design, not from canon.
- Espada raid numbers and phase-2 patterns: design. Names and numbers 0-10 come from the sources.

## Closed in this round
- Quincy Blut Vene (shield) and Blut Arterie (timed damage buff): actions blv and bla, Quincy only.
- Arrancar Bala (piercing bullet, 25% armour pierce): action bal, Arrancar only.
- Tests: test_canon_moves.py (race gating, cost, cooldown, shield, buff, pierce).
- Hollow Negación (neg): a power-field shield, Hollow only.
- Hollow and Arrancar Garganta (gar): a tunnel that puts the full distance between the fighters, shared cooldown.
- Visored signature is now Cero (was Shunpo). Shunpo stays available as normal movement.

## Gaps against canon (still open)
- Quincy Ginto as a mechanic: exists only as an artifact.
- Blade-specific bonuses never fire (blade IDs are not items; see CHANGES_RACE_REBALANCE.md).

## Sources used (URLs as found)
- bleachmedia.fandom.com/wiki/Quincy
- myanimelist.net/featured/640/Bleach_Guide_Series__All_About_Quincy
- animeexplained.com/?p=7575
- bleachfanfiction.fandom.com/wiki/Halcón (Halcón page)
- tvtropes.org/pmwiki/pmwiki.php/Characters/BleachEspada
- en.wikipedia.org/wiki/List_of_Hollows_in_Bleach
- power-in-bleach-explained.pages.dev/posts/power-in-bleach-explained
- bleach.fandom.com/wiki/Glossary
- sportskeeda.com/anime/bleach-every-type-cero-explained
- bleachfanfiction.fandom.com/wiki/Excavado
- animeandmangauniverse.fandom.com/wiki/Orihime_Inoue

## Limits of the Garganta and Negación
- Garganta here opens distance inside a fight. Using it to travel to another place is not implemented.
- Negación here is a personal shield. Shielding allies is not implemented (fights are one-on-one).
