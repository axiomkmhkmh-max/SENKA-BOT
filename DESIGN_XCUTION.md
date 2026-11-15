# Design: Xcution and the Lost Substitute Shinigami arc (started, not yet built)

## What the arc is (sources in CANON_AUDIT.md)
- Anime episodes 343 to 366 (manga chapters 424 to 479). Ichigo lost his powers after the Arrancar arc and
  regained a new strength through Fullbring.
- Xcution is a gang of Fullbringers (Kugo Ginjō and others) who use people's power to get stronger.
  They siphon Fullbring power from others.

## What the game already has
- Fullbringer race, with the Fullbring signature (bring) and a progression ladder: awakened, fullbring, complete.
- Location: xcution_hideout (level 27), with an enemy list.
- Fullbringer Kugo Ginjō and Xcution characters in the roster.

## Proposed slice 1 (smallest useful version)
1. Xcution membership: a Fullbringer character can join Xcution from the hideout. One gang at a time.
2. Siphon: after a won battle at the hideout, a member takes a share of the defeated enemy's reiatsu
   (a bounded amount, capped per day). Siphoned reiatsu gives temporary buffs, like the existing buff system.
3. Rank: Xcution rank rises with siphon points, and each rank gives a small bonus to Fullbring damage.

## Open questions for you (I will not guess these)
- Should Xcution be joinable by other races too, or Fullbringers only?
- How much reiatsu can one siphon take, and how often? (economy and balance)
- Should leaving Xcution cost something?

## Not in this slice
- Gang wars, PvP between gangs, the Xcution boss fight.

## Decisions (made by Claude, built as slice 1)
- Fullbringers only. Join only at xcution_hideout. Leaving is free; rejoining waits 24 hours.
- Siphon: each win at the hideout gives 3 + enemy level / 5 points (doubled for elites), daily cap 60.
- Ranks at 0, 40, 120, 300, 700 points. Each rank adds 2% damage for members.
- Built: data_gangs.py, handlers_gangs.py (panel xgn, actions xgj and xgl), service_gangs_hook.py. Tests: test_xcution_bount.py.
- Not built: gang wars, the Xcution boss.
