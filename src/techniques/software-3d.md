# Software 3D on the SH-2

The 32X has no 3D hardware: no transform unit, no rasteriser, no depth buffer. Every polygon on screen was transformed, projected, sorted and filled by an SH-2 program, and the 32X VDP only displays the result and fills runs of one colour ([Auto fill](../32x/vdp.md#auto-fill)). This chapter follows that pipeline stage by stage, using four sources:

- **Star Wars Arcade**, Sega's flat-shaded polygon game: a clean retail ROM, and the most complete shipped renderer in the sources.
- **After Burner Complete**, also Sega's, which builds its 3D world from scaled sprites ([2D drawing and effects](2d-effects.md#after-burner-completes-scaler)).
- **d32xr**, the Doom port, which spreads one renderer over both SH-2s.
- **The homebrew notes' example renderer**, r3d: short, readable teaching code, with bugs listed at the end.

## The pipeline

| Stage | Job | Typical cost |
|-------|-----|--------------|
| Transform | Move each vertex from the object's space into the camera's | A few multiplies per vertex |
| Cull | Drop what cannot be seen: behind the camera, off screen, facing away | A compare or two per object or face |
| Project | Divide by depth to get screen positions | One divide, or a table look-up, per vertex |
| Sort | Decide the drawing order | Per face |
| Clip | Cut what crosses the screen edge | Per edge that crosses |
| Fill | Turn each polygon into spans and write them | Per pixel; usually most of the time |

The last stage dominates. In a PicoDrive profile of After Burner Complete, the Master spends about 45% of its time in the scaler's loops and another 44% waiting for its sky and sea fills; sorting and projection take a few percent <span class="tag emulator">emulator</span> [AB32X, PC profile in PicoDrive]. Every renderer here is designed around making the fill cheap.

## Fixed point and the transform

All the renderers here use 16.16 fixed point: a 32-bit integer whose low 16 bits are the fraction ([Fixed-point arithmetic](fixed-point.md)). Multiplying two 16.16 numbers gives a 64-bit product whose middle 32 bits are the 16.16 result. The SH-2 gets them with `DMULS.L` or `MAC.L` followed by `XTRCT`, with no shifts ([Registers and instruction set](../sh2/isa.md)).

- **Star Wars Arcade** transforms a point with `MAC.L`s down a column of a 16.16 matrix for each output: `CLRMAC`, four `MAC.L`s, two `STS`, an `XTRCT` and an `ADD` per output [SWA, SH-2 code at `0x060028D0`-`0x06002932`]. See [Registers and instruction set](../sh2/isa.md) for the sequence and [Pipeline](../sh2/pipeline.md#the-multiplier) for how long the multiplier stays busy.
- **d32xr** multiplies with `DMULS.L` and `XTRCT`, written in C as a 64-bit multiply shifted right by 16, which GCC compiles to the same instructions [D32XR, doomdef.h, sh2_fixed.s]. Its view transform is four multiplies, because Doom's camera only turns about the vertical axis.
- **The homebrew renderer** also turns only about the vertical axis: a yaw, with a 256-step sine table. Each vertex costs four multiplies to place the object in the world and four to bring it into the camera's view [S32X-SKILL, assets/3d/r3d.c]. The notes advise looking up the camera's sines and cosines once per frame, not per vertex, which saved a racing game about 600 table look-ups a frame <span class="tag emulator">emulator</span> [S32X-SKILL, references/optimization.md]. The example renderer itself still looks them up for every vertex.

If the game's camera never rolls or pitches, use the cheaper form: a 2D rotation and a translation instead of a matrix.

## Projection: dividing by depth

A point at camera-space (*x*, *y*, *z*) lands at screen *x* = centre + *x* × *f* / *z*, with *f* the focal length in pixels. The divide is the expensive part, and the renderers handle it four ways:

- **The division unit.** d32xr divides with the SH-2's divider, in 64/32 mode for 16.16 quotients: one divide per sprite for its scale, one per wall column. The result takes 39 clocks; d32xr starts the divide early and reads it late, so the CPU works in the meantime ([Division unit](../sh2/divu.md)) [D32XR, sh2_fixed.s, r_phase3.c, r_phase6.c].
- **`DIV1` steps.** After Burner Complete works out each object's scale as `$7FE0` ÷ (*z*/32 + 32) with sixteen `DIV1`s, a 16-bit quotient. Adding 32 means the divisor is never 0, and caps the largest scale at about 4 × full size, so there is no near-plane problem at all: an object at the camera is simply drawn big. The screen position then takes a few 16-bit multiplies per coordinate, one of them by that scale [AB32X, SH-2 code at `0x0600257C`-`0x06002662`].
- **A table of reciprocals.** The homebrew renderer has no divide in its projection. It uses 4,096 entries of 2<sup>22</sup> / *k*, indexed by the depth in steps of 1/16 of a unit, without interpolation. Checking it shows how much a coarse table costs: at the screen edge with a focal length of 150, a point less than half a unit away lands up to 39 pixels from where a true divide puts it; from 8 units outward the error is 1 pixel or less. Past about 256 units the index stops at the end of the table, and distant objects stop shrinking [S32X-SKILL, assets/3d/r3d.c, assets/3d/gen_tables.py]. Make a reciprocal table finer where depths are small, or interpolate between entries.
- **One reciprocal per depth slice.** When the camera never turns, every point at the same depth shares one reciprocal. The homebrew notes' tunnel game works out 1 / (*z* + distance behind the camera) once per ring and multiplies each point by it [S32X-SKILL, references/software-3d.md].

**The near plane.** Points at or behind the camera cannot be divided by their depth. The homebrew renderer drops any triangle that has a vertex nearer than a quarter of a unit, so nothing needs clipping, at the price of triangles vanishing as the camera reaches them [S32X-SKILL, assets/3d/r3d.c]. d32xr drops sprites nearer than 4 units [D32XR, r_phase3.c]. After Burner Complete's bias, above, removes the problem instead.

## Culling

What is not drawn costs nothing, and culling early saves every later stage:

- **Outside the view.** d32xr rejects a sprite whose sideways offset is more than four times its depth before it divides, then rejects it again once its height on screen is known [D32XR, r_phase3.c]. After Burner Complete rejects an object once its centre is further outside the 160-pixel half-width than its own scaled half-size [AB32X, SH-2 code at `0x0600261E`-`0x06002646`]. Star Wars Arcade drops a polygon whose farthest vertex has a negative depth or one beyond 32,767 before it is sorted, and the rasteriser drops one wholly above, below or beside the screen [SWA, SH-2 code at `0x06003150`-`0x0600318C`; on-chip code at `0xC00000F8`, `0xC000022E`].
- **Facing away.** On a closed mesh about half the faces face away from the camera. The test: after projection, work out (*x*1 − *x*0)(*y*2 − *y*0) − (*x*2 − *x*0)(*y*1 − *y*0), and drop the face if its sign is wrong for the winding the models use. The homebrew notes' fighting games use this [S32X-SKILL, references/software-3d.md]; their example renderer does not.
- **Level of detail.** A racing game in the homebrew notes replaces a distant car with 13 triangles, then with a single box, and its build tool deletes faces sealed inside touching boxes, so they never reach the game [S32X-SKILL, references/optimization.md].
- **Cull before sorting.** A comparison sort costs more than in proportion to its length; the same racing game culls first for exactly that reason.

## Drawing order without a depth buffer

A depth buffer for a 320 × 224 screen at 16 bits a pixel is 140 KB, more than half of SDRAM, and each pixel written would need a read and a compare. None of the renderers has one. They draw in an order that makes nearer things cover farther ones, the painter's algorithm.

### The sort key

- **The sum or average of the vertex depths.** The homebrew renderer adds the three depths and skips the divide by 3, which does not change the order [S32X-SKILL, assets/3d/r3d.c]. Star Wars Arcade lets each polygon choose, with two flag bits, between the average of its four depths, its nearest vertex and its farthest. If the chosen value is negative it falls back to the farthest [SWA, SH-2 code at `0x06003110`-`0x060031AC`]. A choice per polygon presumably lets the models' authors fix the order of faces that a single rule would get wrong.
- **A depth byte.** Each of After Burner Complete's object records starts with a depth from 0 to 255, filled in when the object is projected [AB32X, SH-2 code at `0x06002674`-`0x0600267E`, `0x06003B84`].
- **The scale.** d32xr sorts sprites by their scale on screen, which grows as they come nearer. It packs the scale into the upper bits of an integer and the sprite's slot number into the low 7, sorts the integers, and recovers each sprite from its low bits [D32XR, r_phase8.c].

### Comparison sorts

For a few dozen items, an insertion sort is the usual choice: the homebrew renderer and d32xr both use one, on a list built afresh each frame. Objects move little between frames, so a list kept in last frame's order would start nearly sorted, and an insertion sort of a nearly sorted list takes little more than one pass.

Packing an index into the key needs room for every index. d32xr's key has 7 bits for the slot, enough for 128 sprites, but the game allows up to 163. With more than 128 sprites in view, a slot number spills into the scale bits: one sprite would be drawn twice and another not at all [D32XR, r_phase3.c, r_phase8.c]. The 7-bit field dates from when the limit was 128.

### Bucket sorts

With many items, both games use buckets instead, though they come from different developers (Star Wars Arcade from Sega InterActive, After Burner Complete from Rutubo Games) and share no code that has been found ([Sega's sample code in the games](../appendices/sample-code.md#how-much-else-the-three-share)): one list per range of depth, filled in any order and read out in depth order. Inserting costs the same however many faces there are, and nothing is compared.

**Star Wars Arcade** [SWA, SH-2 code at `0x0600318E`-`0x060031D6`, `0x06002796`-`0x060027D2`]:

- **8,192 list heads**, one longword each, 32 KB in all.
- **Two resolutions.** Depths up to 4,095 get a bucket each. Depths from 4,096 to 32,767 share buckets in groups of 8. Order mistakes show most close to the camera, so that is where the buckets are finest.
- **Insertion** takes an 8-byte node from a pool (next node, polygon record) and pushes it on the front of its bucket's list.
- **Reading out** walks every head from far to near, copies each polygon's pointer into a flat list for the other SH-2, and clears the head as it goes, so the table is ready for the next frame with no separate clear. The node pool is then reset to its start.

The walk visits all 8,192 heads every frame, empty or not: tens of thousands of clocks however few polygons there are. That is the price of fine buckets.

**After Burner Complete** [AB32X, SH-2 code at `0x06003B66`-`0x06003BF4`]:

- **256 buckets of 32 bytes**, 8 KB: a count, then up to 30 one-byte object numbers. No pointers and no pool.
- **A full bucket spills into the next one**, which is drawn just after it. If every bucket from there on is full, the object is dropped.
- **Reading out** walks the 256 buckets in order, clears each count, and builds a draw record for every object listed.

| | Star Wars Arcade | After Burner Complete |
|---|---|---|
| Buckets | 8,192, in two resolutions | 256 |
| Memory | 32 KB of heads, plus 8 bytes per polygon | 8 KB |
| Insert | Take a node, push on a list | Store one byte |
| Read out | 8,192 heads | 256 counts |
| When a bucket fills | Never: lists grow | Spill into the next; at worst, drop |
| Order within a bucket | Last in, first drawn | First in, first drawn |

Pick the bucket count from the depth precision the scene needs. After Burner Complete's sprites are well spread in depth, and 256 levels are plenty; Star Wars Arcade's polygons touch and overlap, and need finer steps close up.

### Where painting fails

A painter's sort orders whole faces, so it gets two cases wrong: faces that pass through each other, and faces whose order depends on which part you look at, such as a long wall beside a short object. Backface culling removes the most common error, faces on the far side of the same object. Beyond that the remedies are in the content: keep objects apart, split large faces.

d32xr shows the other way to avoid errors: order by structure, not by depth. Doom's map is a binary space partition (BSP), a tree that gives the walls in front-to-back order from any viewpoint. d32xr draws walls front to back, remembering for each screen column how much of it is already covered, so no wall pixel is ever overwritten. Floors and ceilings fill only the gaps the walls left. Only sprites are drawn back to front, and each is clipped against the outline of the walls in front of it [D32XR, r_phase1.c, r_phase7.c, r_phase8.c]. No wall or floor pixel is drawn twice, and the order is never wrong, at the price of a map built for it.

## Clipping

Clipping a polygon against the screen edges means finding where its edges cross them, which normally takes a divide per crossing.

- **Avoid it.** Drop polygons that cross the near plane, and draw sprites into guard bands ([Guard bands](../32x/vdp.md#guard-bands-drawing-without-clipping)).
- **Clamp each span.** The homebrew renderer limits its loop to the screen's rows and clamps each span's ends to its columns. That costs nothing when the triangle is on screen; a triangle wholly off to one side still costs a full pass over its rows [S32X-SKILL, assets/3d/r3d.c].
- **Clip by halving (Star Wars Arcade).** To find where an edge crosses a boundary line, the rasteriser takes the edge's midpoint, keeps whichever half still crosses the line, and repeats until the midpoint lands exactly on it. Each step is two additions and two shifts, and an edge a few hundred pixels long needs at most nine steps. There is no divide and no multiply. The same routine clips against left and right edges with the coordinates swapped [SWA, on-chip code at `0xC0000490`-`0xC00004E2`]. Polygons that do not cross the left or right edge take a fast path; the others go to a slower routine in SDRAM [SWA, on-chip code at `0xC000022E`-`0xC0000256`; SH-2 code at `0x06000C28`].

## Filling polygons

### Edges, slopes and spans

Every renderer here fills polygons one horizontal span at a time. It walks the left and right edges down the screen, stepping each edge's *x* by its slope, *dx*/*dy*, for each row. The slope is the one divide per edge.

- **Slopes from a table (Star Wars Arcade).** At start-up the game builds 8,192 words of 32,768 ÷ *n* with the division unit [SWA, SH-2 code at `0x06000EFE`]. An edge's slope is then *dx* × table[*dy*] with one `MULS.W`, doubled to give 16.16 [SWA, on-chip code at `0xC00002B2`-`0xC00002C0`]. No divide is left in the rasteriser.
- **A divide per row (the homebrew renderer)** recomputes the edges' *x* with a 64-bit divide on every row, which GCC turns into a library call. Another homebrew game measured what replacing that with precomputed 16.16 slopes is worth: from 7 to 14.6 frames per second <span class="tag emulator">emulator</span> [S32X-SKILL, references/optimization.md].
- **Write words.** A flat-shaded span is one colour, so put the colour byte in both halves of a word and write two pixels at a time, with a byte store for an odd pixel at either end ([Shapes: everything is a span](2d-effects.md#shapes-everything-is-a-span)).

Star Wars Arcade's rasteriser has three more tricks worth copying [SWA, on-chip code at `0xC0000000`-`0xC0000248`]:

- **Store the vertex list twice.** Each vertex is written into two arrays 32 bytes apart. Walking round the polygon from any vertex then never needs to wrap back to the start.
- **One shape for all.** A triangle is a quadrilateral with its last vertex repeated, and a line is a quadrilateral two pixels wide. One routine draws everything.
- **Trapezoids.** The routine walks both edges from the top vertex to the bottom one, and cuts the polygon into trapezoids wherever either edge turns a corner. Each trapezoid is then just two starting *x* values, two slopes, a first line and a height.

### Star Wars Arcade: polygons as auto fills

Star Wars Arcade's Slave does not write most of its pixels itself. It makes the 32X VDP's auto fill draw them, and uses the SH-2's watchdog timer to keep the fill busy while the CPU works on the next polygons [SWA, SH-2 code at `0x060007D0`-`0x060008DE`, `0x06000B98`-`0x06000C0C`; on-chip code at `0xC0000000`-`0xC0000748`]:

1. **The producer** is the 2 KB routine in the Slave's on-chip RAM ([Two-way mode](../sh2/cache.md#two-way-mode-2-kb-of-on-chip-ram)), run once per polygon in the Master's list. It does the clipping and edge set-up above and appends each trapezoid as a 24-byte record to a ring of 1,000 in SDRAM: left *x* and slope, right *x* and slope (all 16.16), first line, height and colour word. It masks interrupts while it adds a record, and waits if fewer than four places are free.
2. **The consumer** is the watchdog's interrupt handler, also in on-chip RAM ([The watchdog timer](../sh2/timers.md#the-watchdog-timer)). Each time it runs it does one step of a small state machine:
   - **Clearing.** It clears one screen line with a 161-word auto fill and sets the timer to interrupt again 480 clocks later, about the time that fill takes. The frame's 224 lines are cleared this way, one interrupt each, while the producer fills the ring.
   - **Stars.** Then it plots the starfield as single pixels.
   - **Trapezoids.** Then it takes trapezoids off the ring. For each line it rounds the two edges to pixels. A span of 6 pixels or fewer it writes with byte stores. A wider one it writes as an odd byte at either end and an auto fill for the words between. After a fill of 80 pixels or more it returns and sets the timer for 512 clocks, so the producer runs while the VDP fills. Shorter fills it waits for, and carries on.
   - **Idle.** With the ring empty, it sets the timer to look again about 260 clocks later.
3. **At the end of the frame** the Slave waits until the ring is empty and the state machine idle, stops the timer, and swaps the frame buffers.

Two things make this pay. The VDP fills a word in 3 clocks without the CPU, so a long span costs the CPU only the few register writes that start it ([Auto fill](../32x/vdp.md#auto-fill)). And because the timer brings the CPU back after 512 clocks, enough for the widest line (160 words, 487 clocks by the manual's formula), the CPU never polls FEN while a long fill runs: it does the set-up for the next polygons instead. The design depends on knowing how long a fill takes, which is fixed by the hardware. The wait is the same for every long fill, so after a narrower span the VDP finishes early and sits idle until the timer fires: an 80-pixel span (40 words) takes about 127 clocks. Short spans are still polled. The PWM interrupt, at a higher level, can also break into the handler ([Case study: Star Wars Arcade](../patterns/case-study-starwars.md#one-frame-from-game-logic-to-the-screen)).

This is something no emulator in the sources shows faithfully. Upstream PicoDrive writes each fill's pixels the instant it starts, though it keeps FEN set for about as long as the manual's formula ([Auto fill](../32x/vdp.md#auto-fill)). It has no bus contention, so what the overlap saves on a console cannot be measured there.

## Sprites in a 3D world

Objects that look the same from every side, or from a few sides, are cheaper drawn as scaled sprites ("billboards") than as polygons.

- **After Burner Complete** builds almost its whole world this way: ground objects, enemies, missiles and clouds are sprites, positioned by the projection above, sorted into buckets, and drawn by the scaler ([After Burner Complete's scaler](2d-effects.md#after-burner-completes-scaler)). Up to 92 sprites a frame in play, at 30 frames per second <span class="tag emulator">emulator</span> [AB32X, sprite list length watched in PicoDrive].
- **d32xr** draws Doom's monsters and items as sprites among polygon walls [D32XR, r_phase3.c, r_phase8.c]:
  - **Eight views.** The angle from the viewer to the object, less the way it faces, picks one of eight pictures. Mirrored views are drawn from the same picture with a negative step, and a flag in the top bits of the picture number says so, together with a flag for objects that look the same from every side.
  - **Scale.** One divide gives the scale across; the scale down is that times a stretch factor, so any size of view keeps Doom's pixel shape.
  - **Clipping against walls.** For each sprite, the walls in front of it narrow its top and bottom limits column by column, and see-through wall textures behind it are drawn first, each column only once.
- **Star Wars Arcade's stars** are single pixels, plotted after the clear and before any polygon, so everything covers them [SWA, SH-2 code at `0x06000DB4`].

## Using both SH-2s

The renderers split the work in three different ways:

- **By stage: Star Wars Arcade.** The Master transforms and sorts, the Slave draws, a frame behind ([A pipeline: geometry on the Master, pixels on the Slave](../patterns/cpu-split.md#a-pipeline-geometry-on-the-master-pixels-on-the-slave)).
- **By job and by screen area: d32xr** [D32XR, marsnew.c, mars.h, r_phase2.c, r_phase6.c, r_phase7.c, r_phase8.c]:
  - **Walls are pipelined, then shared.** While the Master walks the BSP and emits walls, the Secondary prepares each one as it appears, using a communication port as the count of walls emitted and prepared. Then both CPUs draw walls from the same list, each claiming the next undrawn wall under a lock. Long walls are cut into pieces first, so the work divides finely. Each CPU replays the coverage updates of the walls the other drew.
  - **Floors and ceilings** are taken one at a time from a shared counter. They are sorted first, largest first and grouped by texture.
  - **Sprites** are split at a screen column chosen so that each CPU gets about half the sprite pixels: the Master draws to the left, the Secondary to the right.
  - The lock is `TAS.B`, which Sega's manual says not to use on the 32X <span class="tag disputed">disputed</span> ([discrepancy 12](../appendices/discrepancies.md)).
- **One draws, one plays sound: After Burner Complete and Mortal Kombat II** ([One SH-2 draws, the other plays sound](../patterns/cpu-split.md#one-sh-2-draws-the-other-plays-sound)).

The homebrew notes suggest starting smaller: let the Slave clear the frame buffer while the Master transforms, then try giving each CPU half the screen's rows [S32X-SKILL, references/optimization.md]. Splitting by rows needs no locks on the frame buffer, but each half must know about every polygon that crosses it.

## Other kinds of 3D

- **Wireframe.** Project the points and draw the edges as lines: no fill, no sort. Several homebrew games are built entirely this way [S32X-SKILL, references/software-3d.md].
- **Static scenes drawn once.** A homebrew brick-breaking game with a fixed camera drew its 3D tunnel every frame; drawing it once at start-up and copying it raised the frame rate from 14.6 to 29, and redrawing only the areas that changed took it to 60 <span class="tag emulator">emulator</span> [S32X-SKILL, references/optimization.md].
- **Tracks from a list of bends.** A track stored as segments of {curve, slope, length} is expanded into centre points with a heading, and the road edges are those points plus and minus half its width across: two triangles per segment. Walking each strip of road as one shape, row by row, needs about 6 divides per segment instead of about 30 for the same area as separate triangles [S32X-SKILL, references/software-3d.md, references/optimization.md].
- **Animated figures.** The homebrew fighting games draw each fighter as 13 tapered prisms on an 18-point skeleton, interpolating between stored key poses [S32X-SKILL, references/software-3d.md].
- **Check the axes first.** Steering that turns the wrong way, or scenery that shrinks as you drive towards it, means an axis sign is wrong. Test early that approaching objects grow [S32X-SKILL, references/software-3d.md].

## Teaching code and its traps

The homebrew notes' r3d is a good map of the pipeline in about a hundred lines, and worth reading for that. Checking it for this chapter found five problems to fix before reusing it [S32X-SKILL, assets/3d/r3d.c, r3d.h]:

1. **The depth sort corrupts its own keys.** One array holds the vertex depths and is then overwritten in place with the faces' sums. A face that uses a vertex numbered lower than itself reads another face's sum instead of a depth. On a test with a near triangle listed after a far one, the far triangle was painted over the near one. Use separate arrays for vertex depths and face keys.
2. **The model and camera rotations turn the same way.** The camera's rotation is described as the inverse but uses the same formula as the object's. Following the notes' chase camera, which gives the camera the car's own angle, turns the car on screen by twice its angle. Negate one of them.
3. **The projection table is coarse close up**, as measured above: up to 39 pixels off within half a unit, and no shrinking beyond about 256 units.
4. **The rasteriser divides on every row**, with a 64-bit library divide; precompute the slopes. It also spends a full pass on triangles wholly off the side of the screen.
5. **The buffer limits are checked in some loops but not others.** A mesh of more than 512 triangles, or one naming a vertex numbered 256 or more, overruns the fixed buffers.

The notes' measurements, here and throughout, come from PicoDrive, read from a frame counter in captured video, not from a console.

## In emulators

- **Auto fill writes its pixels at once in upstream PicoDrive.** It keeps FEN set for about the manual's time, but with no bus contention, so Star Wars Arcade's overlap of fills and set-up, and any design like it, cannot be timed there as a console would run it.
- **The division unit** takes 39 clocks on the chip. Check how your emulator charges for it before comparing a divide with a table ([Division unit](../sh2/divu.md)).
- **Frame-buffer writes** are cheap in PicoDrive and costly on a console, where the fill stage usually decides the frame rate ([Bus controller](../sh2/bsc.md#emulators-do-not-show-this)).

## What to take away

- Spend the effort on the fill: everything else is a small share of the frame.
- Use 16.16 fixed point with `DMULS.L` or `MAC.L` and `XTRCT`; skip the matrix if the camera only turns.
- Divide once per vertex at most, with the division unit started early, a fine table, or a bias that keeps the divisor away from 0. Take edge slopes from a table of reciprocals.
- Cull before you sort, and sort with buckets once there are hundreds of faces; put the fine buckets close to the camera.
- Clip by halving if a divide per crossing is too dear, and avoid clipping where a guard band or a rejection will do.
- Let the VDP fill long spans, and give the CPU something else to do while it does.
- Split the work between the SH-2s by stage, by job or by screen area, and know which data each CPU must see fresh.

## Open questions

- How much does Star Wars Arcade's timer-paced fill save on a console, compared with filling spans by CPU?
- How do Star Wars Arcade's Master and Slave balance in a busy scene: which waits for which?
- Does d32xr's `TAS.B` lock behave on a production 32X with both SH-2s contending ([discrepancy 12](../appendices/discrepancies.md))?
- How does Virtua Racing Deluxe render? The VRD project's documents give the whole renderer to the Slave. Read directly, the project's patched copy of the ROM looks more like Star Wars Arcade's design: the Master transforms, clips and builds edge lists into a ring in SDRAM, and the Slave fills them from an on-chip routine with auto fills [VRD-NOTES, SH-2 code at `0x06000CFC`, `0x060032D4`, `0x060039F0`]. The clean retail ROM confirms the filling half: its span-fill routine runs from the Slave's on-chip RAM <span class="tag emulator">emulator</span> [32X-ROMSET, Virtua Racing Deluxe (USA); SH-2 code at `0x06003BF8`-`0x06003C5E`]. Which CPU transforms and builds the edge lists is still unread. The same documents call the 68000 routine that ranks the cars a depth sort; it orders cars by lap and track segment, not by distance from the camera, so it is not evidence of how the 3D scene is sorted.

## Sources

- [SWA](../appendices/bibliography.md#swa): SH-2 code at `0x060007D0`-`0x060008DE`, `0x06000B98`-`0x06000C0C`, `0x06000C28`, `0x06000DB4`, `0x06000EFE`, `0x060028D0`-`0x06002932`, `0x06002796`-`0x060027D2`, `0x06003110`-`0x060031D6`; on-chip code at `0xC0000000`-`0xC0000748` (copied from cartridge `$005CE0`)
- [AB32X](../appendices/bibliography.md#ab32x): SH-2 code at `0x0600257C`-`0x06002662`, `0x06003B66`-`0x06003BF4`; sprite counts watched in PicoDrive
- [D32XR](../appendices/bibliography.md#d32xr): doomdef.h, sh2_fixed.s, mars.h, marsnew.c, r_main.c, r_phase1.c, r_phase2.c, r_phase3.c, r_phase6.c, r_phase7.c, r_phase8.c
- [S32X-SKILL](../appendices/bibliography.md#s32x-skill): assets/3d/r3d.c, r3d.h, tools/gen_tables.py, references/software-3d.md, references/optimization.md
- [VRD-NOTES](../appendices/bibliography.md#vrd-notes): the project's ROM copy, SH-2 code at `0x06000CFC`, `0x060032D4`, `0x060039F0` (open question only)
