# Collision, physics and game logic

Everything a game does besides drawing: moving things, stopping them at walls, deciding who can see whom, steering cars, finding paths, keeping time. On a 32X all of it is integer arithmetic, it competes with drawing for CPU time, and it has to give the same answer every time if replays, demos and tests are to work. This chapter collects how the book's sources do it:

- **d32xr**, the Doom engine, for movement, collision and line of sight in a world of arbitrary walls [D32XR];
- **Virtua Racing Deluxe**, for car physics and track collision, by the VRD project's account of the game on its `master` branch [VRD-NOTES];
- **Aerobiz Supersonic**, for a strategy game's arithmetic, from its disassembly [AB-DISASM];
- **homebrew ports** collected in S32X-SKILL, for grid games, pathfinding and structure [S32X-SKILL].

The Virtua Racing and homebrew material was checked only in emulators, and the VRD project's ROM copy is not the retail original ([VRD-NOTES](../appendices/bibliography.md#vrd-notes)), so those sections are tagged <span class="tag emulator">emulator</span>.

## Time

### A fixed tick, whatever the frame rate

A game whose logic steps once per drawn picture runs slower whenever drawing does. The fix is to step the logic at a fixed rate and draw when a picture is ready. [When a frame runs long](../patterns/60fps.md#when-a-frame-runs-long) shows three shipped answers: d32xr's 15 Hz tick with movement scaled by elapsed time, Aerobiz Ultimate's count of vertical interrupts, and Virtua Racing's three-state machine. Homebrew adds three refinements <span class="tag emulator">emulator</span> [S32X-SKILL, porting-workflow.md, testing.md]:

- **Advance every timer by the vertical blanks the frame covered**, not by one per frame: waits, typewriter text, move routes, battle pacing. A port running at about 28 frames per second then keeps the original's real-time pace.
- **Match an odd original rate exactly.** One port's original ran its logic from a 180 Hz PC timer at 36.0036 steps a second. The port keeps that ratio as a fraction and adds it to an accumulator each vertical blank, stepping whenever it passes a whole step, instead of stepping once per frame.
- **Tie the tick to vertical blanks for replays.** A game whose frames take about 30 ms steps its logic exactly every third vertical blank (20 Hz), so a recorded input sequence lines up step for step between the ROM and a PC version used as a reference.

Choose the rate before writing the game. Virtua Racing's logic assumes 20 steps a second in about 30 constants, which is why changing its rate broke it ([When a frame runs long](../patterns/60fps.md#when-a-frame-runs-long)).

### Determinism

- **Logic in whole units, drawing in between.** Grid games keep units on whole cells and draw them sliding between cells: an RTS over about 12 frames per cell, a dungeon crawler an eighth of a cell per frame. Interpolated positions never feed back into the logic, so saves, replays and tests stay exact <span class="tag emulator">emulator</span> [S32X-SKILL, strategy-and-grid.md].
- **Fixed pools, cleared whole.** Enemies, shots and explosions live in arrays sized at build time, with no heap. Clear the entire array on reset, not just each entry's "alive" flag: one homebrew shooter cleared only the flags, and a field added later carried a boss's state into the next game <span class="tag emulator">emulator</span> [S32X-SKILL, 2d-and-shmup.md].
- **Side effects after the pass.** When an object's move hits something (a charging monster slamming into a wall, a missile striking), d32xr does not resolve it at once. It records a small code on the object and applies all such effects in a second pass, after every object has moved. No object changes the list while it is being walked [D32XR, p_base.c].
- **Randomness that can be replayed.** Aerobiz Supersonic's random numbers come from the linear congruential generator with the ANSI C constants (multiply by 1,103,515,245, add 12,345). It returns the low word of the previous state plus the Mega Drive VDP's H/V counter, reduced to the requested range [AB-DISASM, RandRange.asm, CmdGetVDPStatus.asm]. The counter adds variation from the exact moment the player acted, but a replay of the same button presses on different frames gives different numbers. For replays and tests, take randomness only from state the game saves.

## Movement and collision in a Doom world

d32xr's collision is the Doom design, reworked for two CPUs and little memory [D32XR, p_maputl.c, p_move.c, p_slide.c, p_base.c, p_local.h, p_setup.c]:

- **The blockmap.** Walls are sorted into a grid of 128-unit cells, so a moving object tests only the walls in the cells it touches. A wall that spans several cells must still be tested once: each test stamps the wall with the current query number and skips walls already stamped. d32xr keeps one array of stamps per CPU, so both SH-2s can query at the same time. Objects are linked into coarser 256-unit cells, which makes that array a quarter of the size.
- **Trying a move.** The new position is checked against every wall it crosses, collecting the highest floor, the lowest ceiling and the lowest floor nearby. The move is allowed if the object fits under the ceiling, steps up at most 24 units, and, unless it can fly or fall, does not stand over a drop of more than 24. A box is tested against a wall with just one of its diagonals, chosen by the sign of the wall's slope. A large move is halved until it is small enough not to skip through walls. All the working state is in a structure on the stack, so either CPU can run it.
- **Friction.** Each tick, an object's momentum is multiplied by `$D240`, about 0.82, and set to zero once it falls below `$1000`, a sixteenth of a unit.
- **Sliding along walls.** The player is a circle of radius 23. For each blocking wall, the signed distances of the start and end of the move give the fraction of the move that fits. The move is cut there, and what is left is turned along the wall's direction, up to three times. This is what lets a player run along a wall instead of stopping dead.

## Line of sight

A monster has to know whether it can see its target, every tick, for every awake monster. d32xr makes it cheap in three layers [D32XR, p_setup.c, p_sight.c]:

1. **The reject table.** Doom levels carry a precomputed bit table saying which pairs of sectors can never see each other. d32xr assumes the table is symmetric and keeps only half of it: for *n* sectors, *n*(*n* + 1) / 2 bits instead of *n*². The bit for a pair is found with the smaller sector number first, and the bit within its byte is selected with a computed branch into a row of shifts.
2. **A walk of the BSP tree.** If the table allows it, the line from the looker's eyes, three quarters of its height up, to the target is pushed through the BSP tree, visiting only the nodes it crosses. Each two-sided wall it passes narrows the range of slopes still open above and below. When the top and bottom slopes meet, sight is blocked.
3. **No exact corners.** Both ends of the line are moved to odd whole-unit coordinates, so the line never passes exactly through a wall's corner, and the walk has no tie to break.

**Both CPUs check sight.** The Master and the Slave take objects from one shared list and check them in parallel. A monster that sees its target sets a flag, and because the other CPU may have set it, the movement pass purges that flag's cache line before reading it ([Keeping the views in step](../sh2/cache.md#keeping-the-views-in-step)). The Slave stays out while a demo is being recorded or played and in network games, where the results must come out the same every time [D32XR, p_sight.c, p_base.c, p_tick.c].

**Hitscan.** A bullet must hit the nearest thing on its line. Instead of collecting every crossing and sorting them, d32xr walks the BSP tree front to back, which gives nearly the right order already. Within one subsector it holds back one crossing and swaps it with the next if the next is nearer [D32XR, p_shoot.c].

## Car physics: Virtua Racing

By the VRD project's account, every car is simulated on the 68000 each frame by a fixed pipeline of 17 steps: camera, timers, steering, forces, speed, gears, tilt, drift, position, then collision. Computer cars and replays use shorter versions <span class="tag emulator">emulator</span> [VRD-NOTES, master branch, analysis/PHYSICS_SYSTEM_ARCHITECTURE.md]:

- **Grip in 8.8 fixed point.** Grip starts each frame at 1.0 (`$0100`). If the net force is more than the tyres can take, grip falls in proportion to the excess, never below 0.5, and the tyres squeal.
- **Braking bites harder.** A negative net force is doubled before it is applied.
- **Speed changes are limited** to 1,024 units per frame either way.
- **Gear changes keep the speed.** Changing up multiplies the internal speed by the gear ratio over 256; changing down divides by it. The speed the player sees does not jump.
- **Speed from a table.** A 384-entry table gives the base speed, then a chain of multipliers adjusts it: boost, a reduction at high speed (11/16), a tail wind (×1.75).
- **Steering** is filtered through a dead zone, then smoothed by averaging with the previous value; drift reduces grip in proportion to steering and speed.

**Collision by searching the frame** <span class="tag emulator">emulator</span> [VRD-NOTES, master branch, analysis/COLLISION_SYSTEM_ARCHITECTURE.md]. Five probe points (the centre and four corners) are tested against the track's edges. If any hits, the car's heading, scale and position are set back to the previous frame's values. The move is then repeated in four quarter steps, probing after each, and stopped at the first quarter that collides. Contact is resolved to a quarter of a frame without working out where the car meets the wall geometrically. The ground height under each probe is then averaged with the last frame's, which smooths bumps.

**Track look-up** <span class="tag emulator">emulator</span> [VRD-NOTES, master branch, analysis/TRACK_DATA_FORMAT.md, COLLISION_SYSTEM_ARCHITECTURE.md]:

- **Finding the tile.** A car's position becomes a track tile index through shifts on a 32-unit grid.
- **Reading its geometry.** The tile's curvature, normal and gradient are stored in four parallel 2 KB pages, so one pointer reaches all four with a fixed stride.
- **Distances between cars** are |dx| + |dy|: no multiply, no square root.
- **When cars touch,** the faster takes three quarters of their combined speed and the slower three eighths.

## Paths, fog and AI on a grid

Homebrew strategy and dungeon games show the usual algorithms at 32X scale <span class="tag emulator">emulator</span> [S32X-SKILL, strategy-and-grid.md, examples.md]:

- **A\* search** on an 8-direction grid. The estimate of remaining cost is the diagonal ("octile") distance: the longer axis times the straight cost, plus the shorter axis times the extra cost of a diagonal, with the two costs about 10 and 14. A diagonal step is not allowed past a blocked corner. The open and closed sets are arrays the size of the map, allocated once. A blocked goal falls back to the nearest reachable cell, and a stuck unit plans again. The code has no hardware calls, so it is tested on a PC with direct, detour, corner and unreachable cases.
- **Breadth-first search** checks which buildings a city builder's roads connect, in a simulation that fits in about 7 KB of SDRAM.
- **Fog of war** in three states per cell, one byte each: never seen (drawn blank), seen before (terrain and buildings as remembered, no live enemies), and visible now. It is recomputed every frame from each unit's sight radius.
- **AI as small state machines**: look for a target, move, attack, retreat. Damage lands at the end of the attack's wind-up, and projectiles take time to arrive. The player's units and the enemy's run the same code.

## A strategy game's arithmetic: Aerobiz Supersonic

Aerobiz Supersonic does its economy in plain integers, with no fixed point [AB-DISASM, CalcOptimalTicketPrice.asm, section_000200.asm `RangeLookup`]:

- **Percentages.** One price is a rating plus 20, times a skill plus 1, times a time term, divided by 100. Another multiplies a rating by 15 as (×16 − ×1), adds 600, multiplies by the skill plus 1 and halves the result, rounding towards zero.
- **A time term that does not vary.** That time term is meant to be the frame counter at `$FF0006` divided by 3, plus 30. The Aerobiz Ultimate project measured that word staying at 1 for a whole game, so in practice the term is a constant 30 [AU-NOTES, ROADMAP U-045]. Labels and comments in a disassembly describe intent; only running the game shows what the values are.
- **Regions as ranges.** The 89 cities are numbered so that each of the 8 regions owns one unbroken run of numbers in each of two blocks: 0-31 for the major cities and 32-88 for the rest. "Which region is this city in?" is a scan of an 8-entry table of starts and counts. Because the major cities come first, Aerobiz Ultimate's map shows only major airports when zoomed out with a single comparison ([The map](../patterns/case-study-aerobiz.md#the-map)).

## Structure that keeps logic testable

- **One state variable for the game's flow**: title, selection, play, game over. Each screen's update and drawing are chosen by it, and menus act on a button's press, not while it is held, so one press moves one screen <span class="tag emulator">emulator</span> [S32X-SKILL, 2d-and-shmup.md].
- **Sound from differences.** The main loop records a few counters (hit points, explosions, cooldowns) before the game update and plays sounds for what changed. The game logic never calls the sound code, so it can be tested on a PC <span class="tag emulator">emulator</span> [S32X-SKILL, 2d-and-shmup.md].
- **Attract mode from recorded input.** After about seven and a half seconds without input, one homebrew game feeds a recorded input stream into its real game loop. Players expect the demo, it exercises the drawing code, and the same stream drives its replay tests <span class="tag emulator">emulator</span> [S32X-SKILL, optimization.md]. Recorded input only replays correctly at the rate it was recorded at: Virtua Racing's replay format assumes 20 game steps a second, and changing the rate broke its attract mode ([When a frame runs long](../patterns/60fps.md#when-a-frame-runs-long)).

## Where the logic runs

In the shipped games whose split has been traced, the 68000 runs the game logic, and Virtua Racing's physics shows why that can be the limit ([Case study: Virtua Racing Deluxe](../patterns/case-study-vr.md#where-the-time-went)). d32xr runs its logic on the Master SH-2 and shares only sight checks with the Slave. [Splitting work across three CPUs](../patterns/cpu-split.md) covers the choices.

## What to take away

- Step the logic at a fixed rate chosen up front, and advance timers by elapsed vertical blanks.
- Keep logic in whole units and draw in between; take randomness only from saved state if replays matter.
- Use fixed pools, clear them completely, and apply side effects after the pass that finds them.
- Bucket walls into a grid, stamp each one per query, and give each CPU its own stamps.
- Check sight in layers: a precomputed table, then a walk that narrows the open slopes.
- For fast objects, back up and search the frame in fractions instead of solving the geometry.
- Use |dx| + |dy| where an exact distance is not needed.

## Open questions

- Does the retail Virtua Racing Deluxe use the physics the project describes? Its account was read from a patched ROM copy.
- Does any retail 32X game run its game logic on an SH-2? Star Wars Arcade, Mortal Kombat II and After Burner Complete run it on the 68000; where Motocross Championship and Knuckles' Chaotix run theirs has not been traced.

## Sources

- [D32XR](../appendices/bibliography.md#d32xr): p_maputl.c, p_move.c, p_slide.c, p_base.c, p_sight.c, p_shoot.c, p_tick.c, p_setup.c, p_local.h
- [VRD-NOTES](../appendices/bibliography.md#vrd-notes): `master` branch: analysis/PHYSICS_SYSTEM_ARCHITECTURE.md, COLLISION_SYSTEM_ARCHITECTURE.md, TRACK_DATA_FORMAT.md
- [AB-DISASM](../appendices/bibliography.md#ab-disasm): RandRange.asm, CmdGetVDPStatus.asm, CalcOptimalTicketPrice.asm, section_000200.asm
- [AU-NOTES](../appendices/bibliography.md#au-notes): ROADMAP U-045
- [S32X-SKILL](../appendices/bibliography.md#s32x-skill): strategy-and-grid.md, porting-workflow.md, testing.md, 2d-and-shmup.md, optimization.md, examples.md
