# Fixed-point maths and fast division

Neither the 68000 nor the SH-2 has floating point. Every coordinate, angle, speed and colour fade on a Mega Drive or 32X is an integer with an agreed scale. This chapter covers how to choose those scales, how each CPU multiplies and divides them, how angles and the tables that replace trigonometry work, distances, packed colour arithmetic, and the overflow traps that catch code moved from a PC.

The instructions themselves are covered elsewhere: multiplies and `XTRCT` in [Registers and instruction set](../sh2/isa.md#multiplies), shifts in [Shifts without a barrel shifter](../sh2/isa.md#shifts-without-a-barrel-shifter), and the SH-2's divider in [Division unit](../sh2/divu.md). This chapter is about using them.

## Fixed point

A fixed-point number is an integer that stands for itself divided by a fixed power of two. In 16.16 format a 32-bit integer has 16 bits of whole number and 16 of fraction: 1.0 is `$10000`, 0.5 is `$8000`, and the step between values is 1/65,536. Adding and subtracting work as for plain integers. Multiplying two 16.16 numbers gives a result scaled by 2<sup>32</sup>, which must be shifted back down by 16; dividing needs the dividend shifted up by 16 first.

The formats in the sources, and what each is for:

| Format | Bits | Range | Step | Used for |
|--------|------|-------|------|----------|
| 16.16 | 32 | ±32,768 | 1/65,536 | World positions, speeds, scales: d32xr, the homebrew renderer, Aerobiz Ultimate's scaler [D32XR, doomdef.h; S32X-SKILL, assets/3d/r3d.h; AU-NOTES, disasm/sh2/master/fb.c] |
| 12.4 | 16 | ±2,048 | 1/16 | Wall heights relative to the viewer, stored small in d32xr's wall records and widened back to 16.16 when used [D32XR, r_local.h] |
| 2.14 | 16 | ±2 | 1/16,384 | Star Wars Arcade's sine table, 1.0 = `$4000`, shifted left 2 to give 16.16 [SWA, SH-2 code at `0x06002B7C`] |
| 1.15 (Q15) | 16 | ±1 | 1/32,768 | Aerobiz Ultimate's sines and unit vectors [AU-NOTES, disasm/sh2/master/fb.c] |
| 0.16 unsigned | 16 | 0 to 1 | 1/65,536 | d32xr's sine table, which never needs to hold 1.0 exactly (see below) [D32XR, tables.c] |
| 8.8 | 16 | ±128 | 1/256 | The VRD project's copy of Virtua Racing Deluxe: grip and steering factors, and a 257-entry sine table [VRD-NOTES, disasm/modules/68k/game/physics] |

Choose the format per quantity, from the range it needs and the smallest step that matters on screen. Store it in the smallest type that holds it, and widen it for arithmetic. d32xr keeps wall heights in 16 bits as 12.4 because there are 165 wall records per picture, and works in 16.16.

Write the formats down. Bugs in fixed-point code are nearly always a value in one format used as another, and nothing in C or assembler catches them.

### Shifts as a convention

On the 68000, the cheapest scheme is to give each quantity its own scale and fold the scaling into a shift after each 16 × 16 multiply. In the VRD project's copy of Virtua Racing Deluxe, a force is a `MULS` followed by a right shift of 7, a gear ratio a `MULU` and a right shift of 5, a position step a `MULS` and a shift of 12, and grip is 8.8 with `$0100` = 1.0 [VRD-NOTES, PHYSICS_SYSTEM_ARCHITECTURE.md; disasm/modules/68k/game/physics]. No product ever needs more than the 68000's 32-bit `MULS` result. (The project's ROM copy is patched, so this is the project's copy, not checked against a retail cartridge.)

### Keeping the host build exact

Integer maths gives the same answer on every machine. The homebrew notes use no floating point at all in game code, so the same C runs on a PC and on the 32X with identical results, and a game recorded on one can be replayed and checked on the other [S32X-SKILL, references/optimization.md, references/testing.md]. Two things break that: `long` (see [Traps](#traps)) and any table generated with floating point at run time rather than at build time.

## Multiplying

**On the SH-2**, a 16.16 multiply is four instructions: `DMULS.L`, two `STS` and an `XTRCT` ([Multiplies](../sh2/isa.md#multiplies)). In C, write it as a 64-bit product shifted right by 16. sh-elf-gcc 13.2 compiles that to the same four instructions, so d32xr uses the C form and leaves its hand-written assembler version unused [D32XR, doomdef.h, sh2_fixed.s]. A chain of three such factors also compiles inline with 13.2. The homebrew notes report that GCC 12.1 miscompiles some chains of 64-bit multiplies, and advise writing them with `DMULS.L` or `MAC` directly on that compiler [S32X-SKILL, references/toolchain-and-build.md].

When both values fit in 16 bits, `MULS.W` is cheaper: a 16 × 16 → 32 product into MACL. Star Wars Arcade and After Burner Complete use it for edge slopes and projection ([Software 3D](software-3d.md)).

**On the 68000**, `MULS` and `MULU` multiply 16 bits by 16 and give 32. A 32 × 32 product needs pieces. Aerobiz Supersonic's routine keeps only the low 32 bits of the result: it multiplies the two low halves, adds each cross product shifted up 16, and skips a cross product when its high half is 0, which is the common case. The two high halves together only affect bits above 32, so they are never multiplied. Because only the low 32 bits are kept, the same routine is right for signed numbers [AB-DISASM, disasm/modules/68k/math/Multiply32.asm]. Its random number generator uses it [AB-DISASM, RandRange.asm].

## Dividing

From cheapest to most general:

1. **Divide by a constant: multiply instead.** *x* / *c* is *x* × (2<sup>*n*</sup>/*c*) shifted right *n*. GCC already does this for constants it can see: sh-elf-gcc 13.2 turns `a / 10` into a `DMULS.L` by `$66666667` (checked by compiling for this book). On the 68000 it is worth doing by hand. The VRD project replaced the game's `DIVS #103` with `MULS #644` and a `SWAP`, which divides by 65,536/644 ≈ 101.8 [VRD-NOTES, OPTIMIZATION_PLAN.md QW-5]. That shows both catches: the result is not exactly the same (101.8, not 103), and the `SWAP` rounds towards minus infinity where `DIVS` rounds towards zero, so negative values come out one lower. Check that both are acceptable.
2. **Divide once, multiply many times.** Aerobiz Ultimate's zoomed map positions 178 cities with one divide per picture: it computes 2<sup>24</sup> / step once, and each city's column is then a subtraction, a shift and a multiply [AU-NOTES, disasm/sh2/master/fb.c].
3. **A table of reciprocals.** For divisors in a known range, store 2<sup>*n*</sup>/*d* for each *d*. Star Wars Arcade builds 8,192 words of 32,768 / *n* at start-up with the divider and takes edge slopes from it ([Filling polygons](software-3d.md#filling-polygons)) [SWA, SH-2 code at `0x06000EFE`]. Constant factors can be folded into the table: the homebrew notes put the focal length into the projection table, turning a three-factor product into one multiply, which removed about 340 software divides a picture from a racing game <span class="tag emulator">emulator</span> [S32X-SKILL, references/optimization.md]. A table's step size sets its error; see [Projection](software-3d.md#projection-dividing-by-depth) for how badly a coarse one does close up.
4. **The SH-2's divider.** 39 clocks for a 32/32 or 64/32 divide, and free if started early and read late ([Division unit](../sh2/divu.md)). d32xr's 16.16 `FixedDiv` is the 64/32 form. In a test build, its wall loop puts about 69 instructions of other work between starting each column's divide and reading it, and its floor loop about 64 [D32XR, sh2_fixed.s, r_phase6.c, r_phase7.c]. **The compiler never uses the divider**: a `/` between two variables in C compiles to a call to libgcc's software routine (`___sdivsi3`, or `___divdi3` for 64 bits). Drive the unit by hand, with an inline function as d32xr does. Aerobiz Ultimate's SH-2 code divides only with `/`, so all its divides are software ones [AU-NOTES, Makefile].
5. **`DIV1` steps.** Sixteen `DIV1`s give a 16-bit quotient in about 20 clocks with no set-up, which beats the divider when nothing could overlap it. Mortal Kombat II and After Burner Complete divide this way ([What shipped code does](../sh2/divu.md#what-shipped-code-does)).

### The 68000's divide

The 68000's `DIVU` and `DIVS` divide 32 bits by 16 and give a 16-bit quotient and a 16-bit remainder. If the quotient does not fit in 16 bits they set V and change nothing. A full 32/32 divide needs more. Aerobiz Supersonic's has three paths [AB-DISASM, disasm/modules/68k/math/UnsignedDivide.asm, SignedDiv.asm]:

- **Divisor below `$10000`, quotient fits:** one `DIVU`.
- **Divisor below `$10000`, quotient too big:** two `DIVU`s, the high half of the dividend first, then the remainder joined to the low half.
- **Divisor `$10000` or more:** a 16-step shift-and-subtract loop. Sixteen steps are enough because such a divisor leaves at most 16 bits of quotient.

The signed version uses one `DIVS` when it can and otherwise divides the magnitudes and fixes the sign. In PicoDrive, the one-`DIVU` path costs about 289 cycles a call including the call itself, and the loop about 937 <span class="tag emulator">emulator</span>. Aerobiz Ultimate moved the loop to an SH-2, and then found it never runs: its call counter read 0 after 200,000 frames of play [AU-NOTES, ROADMAP.md U-044, U-045]. See [Finding the idle processor](../patterns/cpu-split.md#finding-the-idle-processor).

## Angles

### Binary angles

Store an angle as a fraction of a turn, with one full turn equal to a power of two. Then adding angles wraps round by itself, the difference between two angles is a subtraction, and the top bits index a table directly.

| Program | Turn = | Table index |
|---------|--------|-------------|
| d32xr | 2<sup>32</sup> (`$40000000` = 90°) | Top 13 bits: 8,192 steps [D32XR, doomdef.h] |
| VRD project's copy | 2<sup>16</sup> (`$4000` = 90°) | Top 10 bits: 1,024 steps [VRD-NOTES, sine_cosine_quadrant_lookup.asm] |
| Aerobiz Ultimate | 2<sup>16</sup> (16,384 = 90°) | Top 8 bits, plus 8 bits for interpolation [AU-NOTES, disasm/sh2/master/fb.c] |
| Star Wars Arcade | 4,096 | 12 bits [SWA, SH-2 code at `0x06002B7C`] |
| Homebrew renderer | 256 | 8 bits [S32X-SKILL, assets/3d/r3d.c] |

Keep more bits than the table needs. The extra bits cost nothing, keep slow turns smooth, and are there if you later interpolate.

### Sine tables

Cosine is sine a quarter turn on, so one table serves both. The choice is how much of the wave to store:

- **The whole wave.** Star Wars Arcade stores 4,096 words of sine over a full turn, in 2.14, 8 KB in SDRAM. Every look-up is one masked index and one load; cosine is the same with 1,024 added [SWA, SH-2 code at `0x06002B7C`-`0x06002BD6`; table at `0x0600348C`].
- **A quarter wave, folded.** d32xr keeps 2,048 16-bit values for the first quarter turn. A quadrant number picks one of four base offsets; odd quadrants index the table backwards by using the bitwise complement of the angle, which is −angle − 1; the second half of the turn is negated. Its tangent table is folded the same way. Together they take 12 KB where PC Doom's took 56 KB [D32XR, tables.c]. The VRD project's copy does the same on the 68000 with 257 words in 8.8 and a jump table of four quadrant routines [VRD-NOTES, sine_cosine_quadrant_lookup.asm]. The angle's top 10 bits index it, so a turn is 1,024 steps of about 0.35°.
- **A small table.** The homebrew renderer's 256 entries of 16.16, built by a script at build time, with cosine at index + 64 [S32X-SKILL, assets/3d/gen_tables.py, r3d.c].

d32xr's values are sampled half a step off the exact angles: entry *i* is sin((*i* + ½) × 90° / 2,048). The table therefore never holds exactly 0 or 1.0, and its largest value, 65,535, fits in 16 unsigned bits [D32XR, tables.c]. The homebrew table is sampled on the exact angles and holds exactly 1.0, which needs 17 bits, so it uses 32-bit entries.

The VRD project's table, read at `$930000` from cartridge `$130000`, is truncated: every one of its 257 entries is the exact sine times 256 rounded down. Each is between 0 and one step (1/256) low, half a step on average, never more than 0.4% of 1.0. Truncation also lengthens the flat runs at the top of the wave: the 14 entries from 242 to 255 all hold 255, so the cosine of every angle from 1 to 14 steps (up to about 5°) reads 255/256, and only an angle of exactly 0 gives 1.0 [VRD-NOTES, project's ROM copy, cartridge `$130000`]. Rounding to the nearest value instead would halve the worst error at no cost. (The copy is patched elsewhere; none of the project's tools writes near this table, and none of the clean 32X dumps in the sources contains it, so it cannot be compared with a retail cartridge.)

### Interpolate where it shows

A table with coarse steps is fine where nobody sees the steps. Aerobiz Ultimate interpolates between its 256 sine entries with the angle's low 8 bits, because its great-circle routes (below) showed facets otherwise [AU-NOTES, disasm/sh2/master/fb.c]. A racing game in the homebrew notes found that a whole-step arctangent (1.4°) moved the horizon 4 to 5 lines at a time when used for camera pitch. An interpolated 257-entry table cut its worst error from 0.99 steps to 0.0002 and the horizon stopped jumping <span class="tag emulator">emulator</span> [S32X-SKILL, references/testing.md]. The 257th entry closes the last interval, so the interpolation never reads past the end.

Size the precision to what the result controls on screen, not to the angle.

### Arctangent

Finding the angle of a vector (*x*, *y*) needs atan2. All the sources fold the vector into one octant, look up an arctangent of a ratio between 0 and 1, then unfold:

- **d32xr** folds into eight octants by the signs of *x* and *y* and which is larger. It divides the smaller by the larger with the divider, scaled to 11 bits, and looks the result up in a 2,049-entry table of angles. Each octant then adds a base angle or subtracts from it [D32XR, r_main.c].
- **Aerobiz Ultimate** does the same with a 257-entry table indexed by 256 × smaller / larger, and reflects the result into the right octant [AU-NOTES, disasm/sh2/master/fb.c].
- **The VRD project's copy** works from the tangent in 8.8 with three ranges: a table in steps of 4 for tangents below 4, a coarser table up to 13.56, and a straight line above, where the arctangent barely changes [VRD-NOTES, disasm/modules/68k/math/atan2_calc.asm].

Aerobiz Ultimate's arcsine table covers −1 to 1 in 257 interpolated steps. Arcsine is steep near ±1, where a table is least accurate; its comment notes that no city on its map is far enough from the equator to reach those ends [AU-NOTES, disasm/sh2/master/fb.c].

Where the inputs are known in advance, compute the angles when building. A homebrew racing game's opponents called atan2 and a distance function about 750 times a picture to plan corners; storing the results per track point removed them <span class="tag emulator">emulator</span> [S32X-SKILL, references/optimization.md].

## Distances

- **Compare squares.** To find the nearer of two objects, compare *dx*² + *dy*², with no square root. Watch the size: the squares of 16.16 values overflow 32 bits (see [Traps](#traps)).
- **An octagon instead of a circle.** d32xr's approximate distance is the larger of |*dx*| and |*dy*| plus half the smaller. It is exact along the axes, 6% high on the diagonal, at worst 12% high, and never low [D32XR, p_maputl.c].
- **Through the angle.** For exact distances to walls, d32xr divides the larger axis by the cosine of the angle from its arctangent table: two table look-ups and one divide, and no square root [D32XR, r_phase2.c].
- **An integer square root** where one is unavoidable: try each bit of the result from the top, keeping it if its square still fits. Sixteen steps give a 16-bit root. d32xr uses one to recompute a value it no longer stores, to save memory ([Smaller structures](memory.md#smaller-structures)) [D32XR, r_phase2.c].

## Curves on a sphere: a worked example

Aerobiz Ultimate draws airline routes on its world map as great-circle arcs. It is a demonstration build, not the shipping game, but it shows several fixed-point problems solved in one place [AU-NOTES, disasm/sh2/master/fb.c; ROADMAP.md U-032] <span class="tag emulator">emulator</span>:

- **Measure the map first.** Fitting the 34 city positions against their latitudes and longitudes showed the map is a plain rectangular projection, with an average error of 3.5 and 4.4 pixels. Mercator fitted no better.
- **Weights without overflow.** Each point on an arc mixes the two end cities' directions with weights sin(*t*ω) / sin ω. Computing 1 / sin ω once and multiplying would overflow 32 bits when ω is small, so the code shifts sin(*t*ω) up 15 bits and then divides. For cities so close that sin ω is tiny it draws a straight line.
- **Wrap the longitude.** Each point's longitude is unwrapped against the previous one, so a route across the edge of the map does not jump.
- **Pin the ends.** The remaining error at the far end is spread back along the arc, so every route starts and ends exactly on its cities: all 31 test routes ended within 3 pixels.
- **What it replaced.** A quadratic curve through a raised midpoint was off by a median of 1.8 pixels, but 15.9 at the 90th percentile and 87 at worst.

## Packed colour arithmetic

A 32X colour packs blue, green and red into 5 bits each, with the through bit on top ([Colours and the palette](../32x/vdp.md#colours-and-the-palette)). Some operations work on all three channels at once, if you stop bits leaking between them:

- **Halve every channel.** Shift right by 1 and mask with `$3DEF`. The mask clears the bit each channel received from the one above it (bits 4 and 9), and bits 14 and 15 [AU-NOTES, disasm/sh2/master/text.c]. The through bit is lost and must be put back if it matters.
- **Average two colours.** Mask both with `$7BDE`, which clears the lowest bit of each channel and the through bit, add, and shift right by 1. The cleared bits leave room for each channel's carry ([Stretching in place](2d-effects.md#stretching-in-place)) [MARSDEV, examples/32x-skeleton/sh_src/mars_start.s].
- **Fade between two colours** needs the channels apart: Aerobiz Ultimate's fade takes each channel, mixes it, and repacks [AU-NOTES, disasm/sh2/master/text.c].

## Traps

- **`long` is 32 bits on the SH-2.** On a 64-bit Linux or macOS PC it is 64. Code that keeps a 16.16 product in a `long` passes its tests on the PC and overflows on the 32X. Use `int64_t` for products [S32X-SKILL, references/architecture.md]. The homebrew notes' voxel example multiplies a fraction of up to 65,535 by 98,304, about 6.4 × 10<sup>9</sup>, too big even for 32 unsigned bits [S32X-SKILL, references/voxel-landscape.md].
- **The divider is signed.** A dividend with its top bit set is negative to it. d32xr's angle routine shifts its numerator, the smaller of the two coordinate differences, left 3 before a 32/32 divide. At 4,096 map units that numerator is 2<sup>28</sup> in 16.16, so the shift sets the top bit, the divider returns a negative quotient, and the routine's clamp turns it into the table's last entry, 45° [D32XR, r_main.c `SlopeAngle`]. Any point at least 4,096 units away on both axes is therefore reported on the diagonal of its octant, wrong by 45° minus its true angle within the octant: nothing on the diagonal, up to about 38° at the largest differences a map allows. The original Doom code had the same shift on an unsigned value, which wraps at 8,192 units instead; and until a 2024 fix, d32xr's 32X path had no clamp at all, so the negative quotient indexed past the end of the table [D32XR, commit `e0b4409`, "SlopeAngle fix"]. The routine feeds the renderer (the angles of wall ends and sprites), monster aiming and turning, and sound panning [D32XR, r_phase1.c, r_phase2.c, r_phase3.c, p_enemy.c, marssound.c]. For unsigned dividends, use the 64/32 form with a high half of 0 ([Doing a divide](../sh2/divu.md#doing-a-divide)).
- **No overflow guard.** The Jaguar version of `FixedDiv`, still in d32xr's source but not built, checks that a 16.16 divide cannot overflow before doing it. The 32X version does not: it relies on the divider returning its largest value instead, and on whatever uses the result clamping it [D32XR, sh2_fixed.s, jagonly.c]. That works, but the emulators disagree about divide by zero ([discrepancy 21](../appendices/discrepancies.md)); test for it.
- **Small types cost instructions.** A `short` loop counter or accumulator makes GCC sign-extend after every operation, and stops it using its one-instruction count-and-branch loop (checked with sh-elf-gcc 13.2). Use `int` for locals, and small types only in stored structures [S32X-SKILL, references/optimization.md].
- **Signed shifts by more than one place are slow** on the SH-2, and some become library calls ([Shifts without a barrel shifter](../sh2/isa.md#shifts-without-a-barrel-shifter)).
- **Rounding direction differs.** Arithmetic right shifts round towards minus infinity, `DIVS` and C division towards zero. Mixing them moves negative results by one.

## In emulators

PicoDrive returns a divide's result at once ([Division unit](../sh2/divu.md#in-emulators)), so timings of divide-heavy code in it say little about a console. It also gets a divide by zero wrong: it leaves OVF clear and puts 0 in DVDNTL, where a Saturn test expects `$7FFFFFFF` or `$80000000` by the dividend's sign ([Divide by zero](../sh2/divu.md#divide-by-zero)). Test the divisor first and both agree.

## What to take away

- Pick a format per quantity, write it down, store small and compute wide.
- Use 16.16 with `DMULS.L` and `XTRCT` on the SH-2; on the 68000, pick scales so that 16 × 16 multiplies and shifts are enough.
- Avoid divides in this order: constant as multiply, one divide per picture or slice, a reciprocal table, the divider started early, `DIV1` steps.
- Make a turn a power of two, keep spare angle bits, and fold the sine table if memory is short or store it whole if speed is.
- Interpolate tables only where the steps would show, and compute what you can when building.
- Use `int64_t`, not `long`, for products, and remember the divider is signed.

## Open questions

- Does d32xr's 45° clamp show in play? It needs a map where the viewer and a wall end, thing or sound are at least 4,096 units apart on both axes; the 32X map set was not available to check.
- Does a clean retail Virtua Racing Deluxe cartridge hold the same truncated sine table at `$130000`?

## Sources

- [D32XR](../appendices/bibliography.md#d32xr): doomdef.h, r_local.h, tables.c, sh2_fixed.s, jagonly.c, r_main.c, r_phase1.c, r_phase2.c, r_phase3.c, r_phase6.c, r_phase7.c, p_maputl.c, p_enemy.c, marssound.c; commit `e0b4409`
- [S32X-SKILL](../appendices/bibliography.md#s32x-skill): assets/3d/r3d.h, r3d.c, gen_tables.py; references/optimization.md, testing.md, architecture.md, voxel-landscape.md, toolchain-and-build.md
- [SWA](../appendices/bibliography.md#swa): SH-2 code at `0x06000EFE`, `0x06002B7C`-`0x06002BD6`; table at `0x0600348C`
- [AB-DISASM](../appendices/bibliography.md#ab-disasm): disasm/modules/68k/math/Multiply32.asm, UnsignedDivide.asm, SignedDiv.asm, RandRange.asm
- [AU-NOTES](../appendices/bibliography.md#au-notes): disasm/sh2/master/fb.c, text.c, Makefile; ROADMAP.md U-032, U-044, U-045
- [VRD-NOTES](../appendices/bibliography.md#vrd-notes): the project's copy of the game's 68000 code (disasm/modules/68k/game/physics/sine_cosine_quadrant_lookup.asm, math/atan2_calc.asm); the sine table at cartridge `$130000` in the project's ROM copy; PHYSICS_SYSTEM_ARCHITECTURE.md; OPTIMIZATION_PLAN.md QW-5
- [MARSDEV](../appendices/bibliography.md#marsdev): examples/32x-skeleton/sh_src/mars_start.s
