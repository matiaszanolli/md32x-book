# Harvested techniques: Collision, physics, line of sight and game logic

Target: Part VI chapter in `src/techniques/` (or `src/howto/emulator-testing.md`). 25 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from S32X-SKILL -->
### Deterministic integer grid logic, interpolated rendering
- Source: S32X-SKILL, references/strategy-and-grid.md:8-23
- What it does and why it is clever: The simulation (collision, A*, rules) uses only whole cells. The renderer interpolates the visual position between cells. Interpolated values never feed back into logic, so saves, replays and host tests stay exact.
- Key numbers: 64×64 RTS grid. About 12-frame sub-tile interpolation.
- Target chapter: NEW: Game logic patterns
- Evidence: warcraft-32x, noudar-32x.

<!-- from S32X-SKILL -->
### A* pathfinding with octile heuristic and no corner cutting
- Source: S32X-SKILL, references/strategy-and-grid.md:25-40
- What it does and why it is clever: 8-direction movement with `h = D·max(dx,dy) + (D2−D)·min(dx,dy)`. A diagonal step is illegal if either orthogonal neighbour is blocked. Building footprints block multiple cells, other units are transient obstacles, a blocked goal falls back to the nearest reachable cell, and a stuck unit replans. Open and closed sets are preallocated to the grid size, so there is no heap. It is a HAL-free translation unit with host tests for direct, detour, corner-cut and unreachable cases.
- Key numbers: D2/D ≈ √2 (e.g. 14/10).
- Target chapter: NEW: Game logic patterns
- Evidence: warcraft-32x, host-tested.

<!-- from S32X-SKILL -->
### Three-state fog of war
- Source: S32X-SKILL, references/strategy-and-grid.md:42-53
- What it does and why it is clever: Each cell is Unknown (draw blank), Fog (draw remembered terrain and buildings, hide live enemies and projectiles) or Visible. It is recomputed each frame from unit sight radii, one byte per cell, and the minimap only reveals explored cells.
- Key numbers: 1 byte per cell (4 KiB for 64×64).
- Target chapter: NEW: Game logic patterns
- Evidence: warcraft-32x.

<!-- from S32X-SKILL -->
### RTS AI, economy and construction as small state machines
- Source: S32X-SKILL, references/strategy-and-grid.md:55-68
- What it does and why it is clever: Each unit has states for aggro scan, attack-move, retaliation, pursuit, range, cooldown and armour. Damage lands at impact time after a windup; death leaves a persistent non-blocking corpse; projectiles have travel time. Workers loop harvest → return → deposit, and exhausted forest tiles flip to passable. Construction validates the footprint and grows hit points over time. Player and enemy units run the same code.
- Key numbers: —
- Target chapter: NEW: Game logic patterns
- Evidence: warcraft-32x.

<!-- from S32X-SKILL -->
### Turn-based crawler rules and flood-fill triggers
- Source: S32X-SKILL, references/strategy-and-grid.md:76-85
- What it does and why it is clever: `damage = attack − defense`. Monsters act once per player turn and chase along the dominant axis. A flood fill opens a whole section ("you hear mechanisms"). The original 40×40 ASCII levels are parsed with their tile-property sheets.
- Key numbers: About 32 host assertions.
- Target chapter: NEW: Game logic patterns
- Evidence: noudar-32x.

<!-- from S32X-SKILL -->
### Rational tick accumulator matching the original's rate
- Source: S32X-SKILL, references/porting-workflow.md:58-61, 117-118
- What it does and why it is clever: Capture the original tick rate as an exact num/den and drive the core from `mars_vblank_count` with an accumulator, rather than one tick per frame. SkyRoads runs at 36.0036 Hz derived from a 180 Hz PIT interrupt.
- Key numbers: 36.0036 Hz.
- Target chapter: NEW: Game logic patterns
- Evidence: skyroads-32x.

<!-- from S32X-SKILL -->
### Fixed game tick decoupled from rendering
- Source: S32X-SKILL, references/testing.md:257-265; references/examples.md:118-120, 192-193
- What it does and why it is clever: When a frame takes about 30 ms, pace logic at exactly 3 vblanks per tick (20 Hz) so recorded input grids line up tick for tick between the desktop oracle and the ROM. Other games use a 30 Hz fixed tick for physics with a variable-rate renderer.
- Key numbers: 20 Hz or 30 Hz ticks. Harness inputs are tripled.
- Target chapter: NEW: Game logic patterns
- Evidence: beachy-beachy-ball-32x (replay-verified), wave-rider-gp-32x.

<!-- from S32X-SKILL -->
### Timers advanced by elapsed vblanks
- Source: S32X-SKILL, references/porting-workflow.md:458-462
- What it does and why it is clever: Every wait, move route, typewriter effect and battle pace advances by the number of 60 Hz vblanks the frame actually covered. Real-time pacing survives a frame rate of about 28 fps.
- Key numbers: —
- Target chapter: NEW: Game logic patterns
- Evidence: raintown-slickers-32x.

<!-- from S32X-SKILL -->
### Menu flow state machine with rising-edge input
- Source: S32X-SKILL, references/2d-and-shmup.md:53-73
- What it does and why it is clever: A single `flow` enum (TITLE/SHIPSEL/DIFF/PLAY/OVER) gates update and draw. Menus react to `nav && !prevNav` so one press advances one screen.
- Key numbers: —
- Target chapter: NEW: Game logic patterns
- Evidence: shmup32x.

<!-- from S32X-SKILL -->
### Event-driven sound by diffing state
- Source: S32X-SKILL, references/2d-and-shmup.md:75-90
- What it does and why it is clever: `main` snapshots counters (hp, particles, cooldown) before `game_update` and fires SFX on the differences. The game module never calls the PWM API, so it stays pure and host-testable.
- Key numbers: —
- Target chapter: NEW: Game logic patterns
- Evidence: shmup32x.

<!-- from S32X-SKILL -->
### Zero entire entity pools on reset; fixed pools with no heap
- Source: S32X-SKILL, references/2d-and-shmup.md:92-98; references/examples.md:142-143
- What it does and why it is clever: Clearing only the `alive` flags left stale velocities and a "ghost boss" from a field added later. Memset the whole arrays on reset. Use fixed pools sized at compile time.
- Key numbers: Raptor: 20 enemies, 64+64 shots, 24 explosions.
- Target chapter: NEW: Game logic patterns
- Evidence: shmup32x bug, raptor32x.

<!-- from S32X-SKILL -->
### Attract / demo mode from a bot input stream
- Source: S32X-SKILL, references/optimization.md:223-229
- What it does and why it is clever: After a period of idle time, feed scripted input into the real game loop. It is what arcade players expect, it keeps the render path smoke-tested, and the same stream seeds record/replay tests.
- Key numbers: About 7.5 s before the demo starts.
- Target chapter: NEW: Game logic patterns
- Evidence: apex-vector-60-32x.

<!-- from S32X-SKILL -->
### BFS road pathfinding and a tiny-RAM simulation
- Source: S32X-SKILL, references/examples.md:105-107
- What it does and why it is clever: A city builder runs its grid simulation with BFS road connectivity and a day/night palette shift.
- Key numbers: About 7 KiB SDRAM. 4-voice PWM.
- Target chapter: NEW: Game logic patterns
- Evidence: pico-city-builder-32x (described only).

---

<!-- from D32XR -->
### Blockmap iteration with a per-CPU validcount
- Source: D32XR, p_maputl.c:254-484, p_setup.c:724-748 (licence: id limited-use)
- What it does and why it is clever: Lines are bucketed in 128-unit cells. A line seen in several cells is checked once by stamping `validcount[line] = vc`, using the current CPU's array from TLS. The thing chains (blocklinks) use 256-unit cells (`blocklinksadjust`), which cuts that array to a quarter. Thing queries halve their cell range to match.
- Key numbers: MAPBLOCKUNITS 128; MAXRADIUS 32.
- Target chapter: NEW: Collision, physics and line-of-sight
- Evidence: code only

<!-- from D32XR -->
### P_TryMove, line crossing and sub-stepped movement
- Source: D32XR, p_move.c:44-334, p_maputl.c:88-133, p_base.c:74-133 (licence: MIT for p_move and p_base; id limited-use for p_maputl)
- What it does and why it is clever:
  - **Position check.** Gathers the tightest floor, ceiling and drop-off from every crossed line and checks things in a box widened by MAXRADIUS.
  - **Box against line.** P_BoxCrossLine tests one box diagonal, picked by the line slope's sign, against the line with two cross products.
  - **Sub-steps.** Big moves are halved until under MAXMOVE.
  - **Move rules.** A move needs room for the object's height, a step up of at most 24 units, and (for non-floaters) a drop-off of at most 24.
  - **Re-entrancy.** All state is in a stack-allocated work struct, so it can run on either CPU.
- Key numbers: step height 24; FRICTION 0xD240 (≈0.82); STOPSPEED 0x1000.
- Target chapter: NEW: Collision, physics and line-of-sight
- Evidence: code only

<!-- from D32XR -->
### Player wall sliding
- Source: D32XR, p_slide.c:61-160, 162-334, 488-546 (licence: MIT)
- What it does and why it is clever:
  - **Contact.** The player is a 23-unit circle. Each blocking line's unit normal (axis-aligned shortcuts, otherwise from R_PointToAngle and sine) gives signed distances, and the move fraction is `d1/(d1-d2)` measured from the circle's contact point.
  - **Slide.** The move is cut to the smallest blocking fraction, and the leftover is projected onto the blocking wall's direction.
  - **Limits.** Up to 3 bumps; fractions under 1/16 are treated as solid.
  - **Specials.** Lines crossed by the final move are found separately with segment-segment side tests.
- Key numbers: CLIPRADIUS 23; ON_SIDE_EPSILON 1/128; 3 iterations.
- Target chapter: NEW: Collision, physics and line-of-sight
- Evidence: code only

<!-- from D32XR -->
### Reject matrix stored as a triangle
- Source: D32XR, p_setup.c:671-714, p_sight.c:277-342 (licence: id limited-use for p_setup; MIT for p_sight)
- What it does and why it is clever: The reject table is assumed symmetric, so only the upper triangle is kept. Bit index = `s1·n + s2 - s1(s1+1)/2` with s1 ≤ s2, about half the original n² bits. The bit mask is built with a computed `braf` into a run of `shll` (see sh2/isa.md). Things in the same subsector skip the test.
- Key numbers: n(n+1)/2 bits.
- Target chapter: NEW: Collision, physics and line-of-sight
- Evidence: code only

<!-- from D32XR -->
### Line-of-sight by BSP walk with narrowing slopes
- Source: D32XR, p_sight.c:61-272, 347-365 (licence: MIT)
- What it does and why it is clever:
  - **Traversal.** The sight line is pushed through the BSP; only nodes it crosses are split, and only subsectors it passes through are visited, with each linedef tested once.
  - **Openings.** Each two-sided line narrows `topslope` and `bottomslope` (from eye height, 3/4 of the looker's height) by the window opening divided by the intercept fraction. Sight fails when they meet.
  - **Integer maths.** Uses int16 integer map units throughout.
  - **No degenerate cases.** Endpoints are snapped to odd integers (`(x & ~0x1FFFF) | 0x10000`) so the trace never passes exactly through a vertex.
- Key numbers: int16 divlines; one 64/32 divide per intercept.
- Target chapter: NEW: Collision, physics and line-of-sight
- Evidence: code only

<!-- from D32XR -->
### Hitscan by BSP order with a one-intercept delay
- Source: D32XR, p_shoot.c:297-523 (licence: MIT)
- What it does and why it is clever:
  - **Ordering.** Front-to-back BSP order replaces sorting all intercepts. Within a subsector, a one-element buffer (`old_intercept`) swaps each new hit with the held one so the nearer of the two is processed first.
  - **Thing tests.** Things are hit-tested against one corner-to-corner diagonal, chosen by the trace direction's sign.
  - **Bullet puff.** The first node that split the trace is remembered so the puff's subsector lookup starts deeper in the tree. The wall impact point is pulled back 4 units.
- Key numbers: aim slopes ±100/160.
- Target chapter: NEW: Collision, physics and line-of-sight
- Evidence: code only

<!-- from D32XR -->
### Deferred side-effects ("latecall")
- Source: D32XR, p_base.c:96-118, 290-322 (licence: MIT)
- What it does and why it is clever: Collisions found while moving (skull slam, missile hit, explosion, removal) are not resolved straight away. They are recorded in a 4-bit `latecall` field plus a short pointer, and applied in a second pass after all thinkers have run. Thinkers never change the list they are iterating, which keeps the base pass simple and lets it run alongside the slave's sight checks.
- Key numbers: 4-bit latecall code.
- Target chapter: NEW: Collision, physics and line-of-sight
- Evidence: code only

---

<!-- from VRD/AU/MARSDEV -->
### 17-step vehicle pipeline with grip-limited force integration
- Source: VRD-NOTES, analysis/PHYSICS_SYSTEM_ARCHITECTURE.md:18-119
- What it does and why it is clever:
  - **Drag:** a surface drag table indexed by `raw_speed>>7`, times a gear factor `>>5`.
  - **Net force:** `drag·force>>7 − (calc_speed<<4) − (drag·$71C0>>7)`. A negative net force is doubled, so braking bites.
  - **Grip:** reset to 1.0 each frame and reduced by excess force, `excess<<8/threshold`, with a floor of 0.5 and a tire-squeal trigger.
  - **Speed:** `final = (net>>1)·grip>>7`; the slope is `final>>2/400`; speed is accumulated, then `raw_speed = display·gear·596/4096`.
  - **Gear shifts:** multiplicative, so speed stays continuous across a shift (upshift `×ratio>>8`, downshift `<<8/ratio`).
  - **Speed curve:** 384-entry speed table plus a multiplier chain (boost `×(16+m)>>4`, high-speed `×11/16`, wind `×1.75`).
- Key numbers: max speed 17,000; delta clamp ±1024 per tick; 6 real gear ratios {171,192,205,213,219,224} (the doc's "7" was corrected in VR60_ROADMAP lessons).
- Target chapter: NEW: Fixed-point game physics and collision
- Evidence: code only

<!-- from VRD/AU/MARSDEV -->
### Steering and drift model
- Source: VRD-NOTES, analysis/PHYSICS_SYSTEM_ARCHITECTURE.md:123-237
- What it does and why it is clever:
  - **Steering input:** a 3-entry acceleration table [−24,+24,0]; counter-steer halving; clamp ±127; deadzone 24; EMA smoothing `(vel<<8 + old)/2`.
  - **Drift:** grip loses `|steer|·drag>>8`. Above a slip of 55, low-speed lateral force is `slip·(512−grip)>>8`, otherwise `slip·3/8`, and heading is corrected by `lat_vel·coeff>>8`.
  - **Spin-out:** triggers at a velocity limit.
  - **Settling:** natural damping zeros velocity on a zero crossing or below 16.
- Key numbers: drift accumulator 0-200, decaying 8 per frame.
- Target chapter: NEW: Fixed-point game physics and collision
- Evidence: code only

<!-- from VRD/AU/MARSDEV -->
### Collision by 4-step binary search over the frame
- Source: VRD-NOTES, analysis/COLLISION_SYSTEM_ARCHITECTURE.md:45-110
- What it does and why it is clever: When any of five probes (centre plus four corners) hits, the routine rolls heading, scale, X and Y back to last frame's snapshot. It then re-advances in four quarter steps (`delta = (cur−prev)/4`), probing each time and undoing the step that collides. This resolves contact to 1/4 frame without solving geometry. Probe heights are then smoothed with an EMA, `h = (old+new)/2`. Physics reaches collision by a `JMP` tail call with no RTS boundary.
- Key numbers: up to 5 probe sets per search; α = 0.5.
- Target chapter: NEW: Fixed-point game physics and collision
- Evidence: code only

<!-- from VRD/AU/MARSDEV -->
### Grid-hashed track lookup and 4-page geometry fetch
- Source: VRD-NOTES, analysis/TRACK_DATA_FORMAT.md:43-99, 154-203
- What it does and why it is clever:
  - **Grid hash:** world X/Y map to a tile via `col = ((X>>4)+$400)>>5` and `row = (($400+(Y>>4)) & $FFE0)<<1`, a centred 32-unit grid. A two-level lookup (segment map, then word offset, then base data) yields the tile pointer.
  - **Geometry pages:** four signed-byte pairs are fetched from four pages spaced `$800` apart. Curvature, normal and gradient therefore live in parallel arrays reached with one pointer, advancing `$7FF` because of the post-increment.
  - **Probe reuse:** probes landing on the same tile as the centre take a fast path.
- Key numbers: 68-byte hot routine, 11+ calls per frame; 2 KB pages.
- Target chapter: NEW: Fixed-point game physics and collision
- Evidence: code only

<!-- from VRD/AU/MARSDEV -->
### Manhattan proximity zones, weighted-speed car collision, AI steering
- Source: VRD-NOTES, analysis/COLLISION_SYSTEM_ARCHITECTURE.md:129-219; analysis/PHYSICS_SYSTEM_ARCHITECTURE.md:167-183
- What it does and why it is clever:
  - **Distances:** all are `|dX|+|dY|`, with no multiplies or square roots.
  - **Zone codes:** put "critical" in bit 15, so callers test with `BMI`.
  - **Car-on-car impulse:** the faster car takes `sum·3/4` and the slower `sum·3/8`, clamped to $04DC.
  - **AI steering:** `frames = (dist<<4)/(speed+1)`, `factor = max(1, frames/2)`, `heading += Δ/factor`.
  - **Billboard rotation:** `lat = −(cos·dX + sin·dY)>>8`.
- Key numbers: thresholds $140/$2C0/$1000; 15 opponents at stride $100.
- Target chapter: NEW: Fixed-point game physics and collision
- Evidence: code only

---

