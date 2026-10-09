# Pseudo-3D roads and Mode 7

A racing or flying game spends most of its screen on the ground. Drawing that ground as polygons is expensive, and it does not need to be: a flat ground plane seen from a camera that does not roll has the same distance all along each screen line. So the ground can be drawn one line at a time from per-line tables, with no polygons and almost no divides. This chapter covers the four versions in the sources: flat colour split along a tilting horizon, a striped runway drawn from runs of colour, a textured floor ("Mode 7", after the Super Nintendo mode of that name), and roads. It also covers objects on the ground, and drawing half the lines.

## One distance per line

Put the camera at height *h* above a flat ground, looking level, with focal length *f* in pixels, and the horizon at screen line *y*<sub>h</sub>. A point on the ground at distance *z* appears on line *y*<sub>h</sub> + *h* × *f* / *z*. Turned round: every pixel on line *y* below the horizon shows ground at distance

*z*(*y*) = *h* × *f* / (*y* − *y*<sub>h</sub>)

That is one divide per line, not per pixel, and if *h*, *f* and the horizon do not change it is a table of one entry per line, computed once. Across a line, the ground position moves in equal steps: each pixel to the right is *z* / *f* further along the camera's sideways direction. So a line is two additions per pixel.

Flat colour needs even less. With no texture there is no distance to look up, only the column where the horizon crosses each line, so a camera that rolls costs nothing extra: the crossing simply moves a little further along on each line.

Everything below is a variation on this: what the table holds, and what each line is drawn with.

## Flat colour and a tilting horizon (After Burner Complete)

After Burner Complete's sky, sea and land are flat colours. The detail is all scaled sprites: waves, trees, rocks, clouds and enemies, positioned in 3D and drawn by its scaler ([After Burner Complete's scaler](2d-effects.md#after-burner-completes-scaler)). The background is two auto fills per line [AB32X, SH-2 code at `0x06008280`-`0x060082F6`]:

- **A table of split columns,** one word per line at `0x06007674`. Each line is filled with the sky colour up to its split and the ground colour after it, 160 words in all. When the plane banks, the split moves a little further along on each line and the horizon tilts. The two colours swap sides with the roll direction.
- **A split off the screen** gives a line of one colour, drawn with one fill [AB32X, SH-2 code at `0x060082A0`-`0x060082BC`].
- **The fills also clear the screen**, so the frame buffer is never cleared separately ([Auto fill](../32x/vdp.md#auto-fill)).

A tilted horizon over flat colour costs at most 448 fills per picture, two on every line, when a steep bank puts the horizon across every line. In level flight the table still splits the one line the horizon falls on, at the middle of the screen, so that line is drawn half in each colour and a picture takes 225 fills <span class="tag emulator">emulator</span> [AB32X, split table at frame 1,260 in PicoDrive: one mid-screen split on line 130]. In stages 1 and 2 of a PicoDrive run the median was 428 and the mean 363, with input that holds a full bank much of the time <span class="tag emulator">emulator</span> [AB32X, split table read every frame, 8 October 2026]. The CPU writes no pixels at all.

A PicoDrive profile of 6,000 frames covered stages 1 and 2, the start of stage 3 and the attract demo. There this is the only background routine that runs (the stages that use the second one, below, were not reached), and over a third of the Master's time is spent in its loops waiting for fills to finish <span class="tag emulator">emulator</span> [AB32X, PC profile in PicoDrive]. That share is set by the emulator's model of FEN, not by the fills ([In emulators](#in-emulators)).

### A runway from runs

The same program has a second background routine, used in other stages. It draws a runway on flat ground from per-line tables, with no polygons [AB32X, SH-2 code at `0x06008350`-`0x06008436`, tables built at `0x06006F1C`]. It is the arcade road technique of [A road from segments](#a-road-from-segments) without the bend: a striped ground drawn line by line from a pattern.

- **One word per line** at `0x06007474`. A line with bit 11 set is one fill in a colour from a 16-entry table, which shades the sky. Any other line holds a depth row number.
- **The row number is the reciprocal of a distance, not the distance.** The routine that builds the tables divides `$7FE0` by *z*/32 + 32, the projection the game uses for its objects ([Projection](software-3d.md#projection-dividing-by-depth)). That is 32 × `$7FE0` / (*z* + 1024): the reciprocal of the biased distance *z* + 1024, not of *z*, which is why the ground's perspective agrees with the objects drawn on it. The routine divides once, for the far limit of the ground, and gives half the result to the line where the ground starts. Below it the row numbers climb in a straight line to 511 at the line where the ground would meet the camera, normally below the bottom of the screen [AB32X, SH-2 code at `0x06006F20`-`0x06006F38`, `0x06006F52`-`0x06006FC8`, `0x06006FEC`-`0x06006FF6`]. Both ends are placed relative to line `$77` minus a camera parameter, so the row on line *y* is 512 × (*y* − *v*) / *A*, where *v* is that line and *A* the height in lines the ground would span. Extended upwards, the ramp reaches 0 at *v*, the true vanishing line, which lies above the drawn horizon and is hidden behind the sky. So the ramp is the perspective of [One distance per line](#one-distance-per-line) for the game's biased distance: 1/(*z* + 1024) grows in proportion to *y* − *v*, and no line needs a divide of its own. The row numbers therefore step evenly down the screen, by between 1.2 and 4.2 rows a line as the camera's height and pitch change, and by the same amount all the way down in any one picture <span class="tag emulator">emulator</span> [AB32X, row table read in PicoDrive, 8 October 2026]. The distance they stand for, *z* = 32 × (16,368 / row − 32), changes fastest just below the horizon, as *z*(*y*) does. Rows 57 and 58 stand for distances of 8,165 and 8,007, about 158 apart; rows 263 and 264 stand for 968 and 960, only 8 apart.
- **A pattern per pair of rows:** a list of runs, each a colour number (0 to 3) above a 12-bit length [AB32X, patterns at `0x060084C0`, colour number masked at `0x060083E8`]. Across a line: ground, edge, surface, line, surface, line, surface, line, surface, line, surface, edge, ground: two side lines and two lines between three lanes, all colour number 1. Nearer rows have wider runs, so the strip narrows towards the horizon; its width in pixels comes to about 0.98 × the row number <span class="tag emulator">emulator</span>.
- **A phase per row** gives how far into the pattern the line starts. The code works it out from a sideways offset scaled by the row, so the runway could slide across the screen in perspective [AB32X, SH-2 code at `0x06007124`-`0x0600717E`]. In every picture sampled the offsets were 0 and the runway stayed centred <span class="tag emulator">emulator</span>. This per-row phase is exactly where a road's curvature sum would go: add each line's running sum to it, and the strip bends.
- **A colour group per row** turns the four colour numbers into palette entries, and alternating groups by depth band make the stripes [AB32X, groups at `0x060084A0`]. In one group the surface is a darker grey, the lines the same grey, so they vanish, and the edges yellow. In the other the surface is a lighter grey, the lines white and the edges the same grey as the surface. So all four lines are dashed: in the bands where the lines vanish the edges are yellow, in the bands where the lines show the edges are grey, and the surface shade alternates slightly <span class="tag emulator">emulator</span> [AB32X, palette entries `$D5`-`$DC` read in PicoDrive]. As the plane moves, the bands run towards the camera: the stripes of the arcade racers below, applied to a runway.
- **Runs of 28 pixels or more** go to auto fill. The threshold is the game's own: each run is clipped to what is left of the line and compared, unsigned, with 28 [AB32X, SH-2 code at `0x060083D6`-`0x060083E6`]. Shorter runs are written with byte and word stores.

Unlike the split fills, this routine cannot tilt. Each line is one row of one pattern, so the horizon and the runway stay level however the plane banks. That is the price of the pattern.

In PicoDrive it is also slower. A profile of the stage-5 landing gives the Master about 548,000 executed clocks per picture in this routine, 488,000 of them polling FEN, mostly before each of the short runs the CPU writes itself <span class="tag emulator">emulator</span> [AB32X, PC profiles in PicoDrive, 8 October 2026]. A frame holds about 384,000 SH-2 clocks ([Clocks and frames](../appendices/timing.md#clocks-and-frames)), so in that run the background alone took more than a frame, and the landing drew a picture every three or four frames; without the profiler almost every picture took two. The split fills took about 213,000 per picture in stages 1 and 2, where the profiled run drew 950 pictures in 2,000 frames, about 28 a second. The canyon stage's one fill per line took about 234,000, slightly more than two. Both fill the same 35,840 words, 224 lines of 160, and nearly all of each figure is the wait for FEN, which follows the words filled rather than the number of fills. Around the waits the runway routine also does more work per line, reading its row, phase and pattern: about 8,700 clocks a picture against the split fills' 1,900. Like the split fills' figure, all of these are set by the emulator's model of FEN ([In emulators](#in-emulators)).

The 68000 picks the routine for each picture: command 7 selects the split fills, and command 8 selects the runway, followed by commands 9 and 10 with its position and scroll [AB32X, 68000 code at `$1EDBE`-`$1EE30`; Master command handlers at `0x0600379E`-`0x060037C6`]. Two kinds of stage use it. Stages 5 and 8 were run in PicoDrive, reached by pointing stage 1's entry in a copy of the ROM at their scripts <span class="tag emulator">emulator</span>. Stages 13 and 17 were not reached, and what they do is read from their scripts [AB32X, stage descriptors at `$3D802`, 68000 code at `$BD08`-`$BD22` and `$E5AE`-`$EA94`]:

- **The base landings, stages 5 and 13.** The plane lands on the runway, rolls along it while supply trucks come alongside, and takes off again. In stage 5 the routine draws all of it, about 1,000 frames in PicoDrive, and the next stage goes back to the split fills. Stage 13's script is a separate copy of stage 5's with the same landing events; it differs in two other events, whose effect has not been traced.
- **The canyons, stages 8 and 17.** The stage script turns the routine on shortly after the start and off at the end; stage 17's script is byte for byte the same as stage 8's. In stage 8 the row table is filled as in stage 5, but the runway's distance is set beyond the far limit of the ground, so no row lies on the runway. Those rows get a phase of 0, and each line starts at the first run of its pattern, ground at least 1,362 pixels long, which covers the 320-pixel line <span class="tag emulator">emulator</span> [AB32X, phase code at `0x06007124`-`0x0600717E`; row and phase tables read in PicoDrive]. All the routine shows is the shaded sky over plain ground, and the horizon stays level. The canyon walls are scaled sprites.

## A textured floor (d32xr)

The name comes from the Super Nintendo, whose hardware steps through the texture along each line while the program loads new steps for every line: the same split as here, a table per line and additions per pixel.

Doom's floors and ceilings are textured planes, and d32xr draws them as described above, one span of a line at a time [D32XR, r_data.c, r_phase7.c, sh2_draw.s]:

1. **Per view size**, two tables:
   - **One per line:** the stretched half-width divided by the line's distance from the centre of the view, offset by half a pixel so no entry divides by 0. This is *f* / (*y* − *y*<sub>h</sub>) from [One distance per line](#one-distance-per-line) without the height, so a floor at any height needs only one multiply, by the absolute height difference between the plane and the eye, to give that line's distance. d32xr does that multiply once per span.
   - **One per column:** 1 / cos of the column's angle from the view direction. Multiplied by a line's distance, it gives the true distance to that pixel along its ray.
2. **Per picture**, the sideways direction of the view divided by the half-width: how far one pixel to the right moves across the floor, per unit of distance. That is two divides, done once before the planes are drawn and shared by all of them. The code computes a second pair for flats drawn rotated by 90 degrees, a case it never selects [D32XR, r_phase7.c, `R_DrawPlanes2`].
3. **Per span**, six multiplies: one for the distance, one for the distance to the first pixel along its ray, two for the step across the floor, and two (by the sine and cosine of the first pixel's angle) for its position on the floor. The light level for the span comes from a divide, which d32xr starts on the SH-2's divider before the multiplies and reads after them ([Division unit](../sh2/divu.md)).
4. **Per pixel**, about ten instructions, with no multiply:
   - `SWAP.W` on each 16.16 coordinate brings the whole part down.
   - Masks keep 6 bits of each: textures are 64 × 64, and the mask makes them repeat across the floor at no cost.
   - The *y* coordinate was multiplied by 64 before the span started, so its masked whole part is already the row's offset, and an `OR` joins it to the column.
   - One byte load fetches the texel, a second looks it up in the light table, and one store writes the pixel. The loop runs right to left, writing with pre-decrement.

In its default detail setting d32xr samples floors and ceilings at half the horizontal resolution and writes each texel to two pixels as one word, which halves the look-ups. Walls keep full resolution: the setting swaps only the span drawer. A separate low-resolution option, off by default, halves the walls too [D32XR, r_local.h, r_main.c, r_phase7.c].

The homebrew notes' Mode 7 racer makes the same moves in its floor loop: a table of distances per line computed at start-up, so the loop has no divide; and texture addressing by shifts and masks, with a table from tile number to the tile's pixels, instead of `/` and `%`. Its inner loop is a few shifts and two table reads per pixel <span class="tag emulator">emulator</span> [S32X-SKILL, references/software-3d.md, references/optimization.md, references/pico8-porting.md].

Keep texture sizes powers of two. Then wrapping is a mask, a row is a shift, and a 16.16 coordinate needs only `SWAP.W` and `AND` to become an index.

## Roads

### A road from segments

Arcade racers of the 1980s draw the road as a striped ground with a road shape on top, and bend it with a running sum:

- **The track is a list of segments**, each with a curvature and a slope.
- **Each line's road centre** is the previous line's plus an amount that grows with the curvature of the segment at that line's distance. Summed from the bottom of the screen up, a constant curvature gives a smooth bend, and the horizon end of the road swings sideways.
- **Hills** move the horizon and change which distance each line shows.
- **Stripes** come from the distance: lines whose distance falls in an even band get one shade, odd bands the other, and the bands move towards the camera as the car advances.

After Burner Complete's runway is this technique with the bend left out, in a disassembled commercial game: a striped ground drawn per line from a pattern, a phase per row where the bend would go, and alternating colour bands ([A runway from runs](#a-runway-from-runs)). The homebrew notes also list an OutRun-style 32X port with a segmented road, forks and per-stage themes, but describe it only in outline [S32X-SKILL, references/software-3d.md, references/examples.md].

### A road from polygons, filled by line

A homebrew racing game draws its road in 3D, as strips of quadrilaterals along the track. Its optimisation notes give three measured gains <span class="tag emulator">emulator</span> [S32X-SKILL, references/optimization.md]:

- **Walk each strip as one shape, line by line.** The strip's two long edges are shared from one segment to the next. Filling it line by line needs about 6 divides per segment, against about 30 when each segment was cut into 10 triangles.
- **Fill only what the road does not cover.** The road filler records each line's left and right edge, and the grass is drawn only beside it. Overdraw fell from 1.36 to 1.05 times the screen. The notes put the saving at about 21,000 pixel writes per picture without giving the screen size; on a full 320 × 224 screen, 0.31 × 71,680 would be about 22,200.
- **Inline the span fill.** At about 1,600 spans per picture, calling a span routine and clipping again inside it took 62% of the fill time.

### The Mega Drive's own tools

The Mega Drive's VDP can scroll each line of a plane by a different amount ([Horizontal scrolling](../megadrive/vdp-planes.md#horizontal-scrolling)). A road drawn once in tiles, straight, can be bent by moving each line sideways by the running sum above, and hills can be made by changing which line of the picture appears where. On the Mega Drive that means changing the vertical scroll from the line interrupt, line by line, since its VSRAM holds only one value per plane or per two-tile column ([Vertical scrolling](../megadrive/vdp-planes.md#vertical-scrolling); [The line interrupt](../megadrive/vdp-timing.md#the-line-interrupt)). Aerobiz does exactly this for one effect, looking up for each line which source row it should show [AB-DISASM, VInt_Handler3.asm] ([Organising the frame](../megadrive/vdp-timing.md#organising-the-frame)). The 32X's line table does the same for its own layer with no interrupt at all ([The line table](../32x/vdp.md#the-line-table)). On a 32X, either layer could carry the road while the SH-2s draw only the cars and scenery. None of the programs in the sources carries a road on a tile layer under sprites drawn by the SH-2s; it is listed as an open question.

## Objects on the ground

Roadside objects and other cars are almost always scaled sprites:

- **Scale by stepping.** Work out the source step for the sprite's size once, and add it per pixel and per line ([Stepping through the source](2d-effects.md#stepping-through-the-source)). The homebrew Mode 7 racer measured more than ten times the speed of dividing per pixel <span class="tag emulator">emulator</span> [S32X-SKILL, references/optimization.md].
- **Pre-drawn angles.** Render each 3D model from a fixed set of angles when building, and pick the nearest at run time. A homebrew water racer turned 46 models into 8 angles of 48 × 48 pixels each; a car game uses 64 angles [S32X-SKILL, references/software-3d.md].
- **Sprite stacking.** Draw a stack of horizontal slices of an object, each shifted up a little and turned to the same angle, and top-down art looks solid from any direction [S32X-SKILL, references/software-3d.md].
- **Sort them.** Draw far objects first; with many objects, sort into buckets ([Bucket sorts](software-3d.md#bucket-sorts)).

The depth each object needs is the same one-divide-per-object projection as in [Software 3D](software-3d.md#projection-dividing-by-depth). After Burner Complete's bias, a divide by *z*/32 + 32, keeps the nearest objects at a sensible size without a near-plane test [AB32X, SH-2 code at `0x0600259C`-`0x060025CA`] ([Projection](software-3d.md#projection-dividing-by-depth)).

## Drawing half the lines

The ground changes slowly from one line to the next. The homebrew racer draws only 112 lines and points two display lines at each through the line table, so the VDP shows each one twice at no cost. It left about 40% of the frame free, at the price of half the vertical detail; its notes say to enable it only when that saving moves the game into a faster frame rate step <span class="tag emulator">emulator</span> [S32X-SKILL, references/optimization.md]. See [Scaling the whole layer](2d-effects.md#scaling-the-whole-layer-the-line-table-does-the-vertical-half) for the same trick used for zooming.

## In emulators

After Burner Complete's backgrounds are mostly auto fill, and upstream PicoDrive completes fills instantly while holding FEN for the fill's time. The time the profiles show waiting on FEN, in the split fills and in the runway routine alike, is therefore set by the emulator's model of FEN, not by the fills ([Auto fill](../32x/vdp.md#auto-fill)). The homebrew measurements were all taken in PicoDrive.

## What to take away

- A flat ground has one distance per line: put it in a table and nothing per pixel needs a divide.
- Flat colour is one or two fills per line, and a tilting horizon is a table of split points.
- A textured floor needs no multiply or divide per pixel: about ten instructions in d32xr, with power-of-two textures.
- Draw a striped road from runs per line: 1/*z* per line steps evenly, a phase per row places it and a running sum added to the phase bends it, and colour groups by depth make the stripes.
- Draw objects as scaled sprites, pre-drawn from several angles if they must turn.
- Fill only what the road leaves, and consider drawing every other line.

## Open questions

- How fast is a road bent by the Mega Drive's per-line scroll, under 32X sprites drawn by the SH-2s, compared with a road drawn by an SH-2?
- How long does d32xr's floor loop take per pixel on a console, with its texel and light look-ups going through the cache?
- What does After Burner Complete's runway cost on a console, where the waits for FEN before each short run are not set by an emulator's model?
- What sets the sideways offset in the runway's phase, which was 0 in every picture sampled, and what do the two events do in which stage 13's script differs from stage 5's?

## Sources

- [AB32X](../appendices/bibliography.md#ab32x): SH-2 code at `0x0600259C`-`0x060025CA`, `0x06006F1C`-`0x06006FF6`, `0x06007124`-`0x0600717E`, `0x06008280`-`0x060082F6`, `0x06008350`-`0x06008436`, `0x0600379E`-`0x060037C6`; patterns at `0x060084C0`, colour groups at `0x060084A0`; 68000 code at `$BD08`-`$BD22`, `$E5AE`-`$EA94`, `$1EDBE`-`$1EE30`; stage descriptors at `$3D802`; PicoDrive runs and PC profiles of stages 1-2, 5 and 8 (split table, row table and palette read every frame, 8 October 2026)
- [D32XR](../appendices/bibliography.md#d32xr): r_data.c, r_local.h, r_main.c, r_phase7.c (`R_MapPlane`, `R_DrawPlanes2`), sh2_draw.s
- [AB-DISASM](../appendices/bibliography.md#ab-disasm): VInt_Handler3.asm (per-line vertical scroll)
- [S32X-SKILL](../appendices/bibliography.md#s32x-skill): references/software-3d.md, references/optimization.md, references/pico8-porting.md, references/examples.md
