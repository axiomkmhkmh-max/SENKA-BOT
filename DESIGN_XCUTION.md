# Design: Xcution and the Lost Substitute Shinigami arc (built, slice 2)

## What the arc is (sources in CANON_AUDIT.md)
- Anime episodes 343 to 366 (manga chapters 424 to 479). Ichigo lost his powers after the Arrancar arc and
  regained a new strength through Fullbring.
- Xcution is a gang of Fullbringers led by Kugo Ginjō. They siphon Fullbring power from others to get stronger.

## Built
- Membership: Fullbringers join at xcution_hideout (panel "اکسکیوشن" / "xcution"). Leaving is free; rejoining waits 24 hours.
- Siphon: each win at the hideout gives 3 + enemy level / 5 points (doubled for elites), daily cap 60.
- Ranks at 0, 40, 120, 300, 700 points. Each rank adds 2% damage for members.
- Siphon Surge: a siphon win opens a 30 minute surge, +6% damage for members.
- Weekly boss, Kugo Ginjō: every member win at the hideout is one tally (reset each week, Monday to Monday, UTC).
  Phases open at 10 and 20 tallies: member damage +3%, then +6% in total. Reaching 30 defeats him, pays every member
  80 points, and pays the top contributor a further 40 points. Damage bonuses are stored on each member's character,
  and a player who joins late gets the bonus the group already unlocked.
- Each battle result shows the rewards: absorption, siphon, rank up, surge, boss phase or defeat, and soul stacks.

## Design values (not canon)
- Every number above is a balance choice. Canon has no numeric values.

## Not built
- Gang wars between gangs, a PvP fight against Kugo, Xcution boss phases with their own moves.
