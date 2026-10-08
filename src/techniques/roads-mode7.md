# Pseudo-3D roads and Mode 7

A racing or flying game spends most of its screen on the ground. Drawing that ground as polygons is expensive, and it does not need to be: a flat ground plane seen from a camera that does not roll has the same distance all along each screen line. So the ground can be drawn one line at a time from per-line tables, with no polygons and almost no divides. This chapter covers the three versions in the sources: flat colour split along a tilting horizon, a textured floor ("Mode 7", after the Super Nintendo mode that does this in hardware), and segmented roads. It also covers objects on the ground, and drawing half the lines.

## One distance per line

Put the camera at height *h* above a flat ground, looking level, with focal length *f* in pixels, and the horizon at screen line *y*<sub>h</sub>. A point on the ground at distance *z* appears on line *y*<sub>h</sub> + *h* × *f* / *z*. Turned round: every pixel on line *y* below the horizon shows ground at distance

*z*(*y*) = *h* × *f* / (*y* − *y*<sub>h</sub>)

That is one divide per line, not per pixel, and if *h*, *f* and the horizon do not change it is a table of one entry per line, computed once. Across a line, the ground position moves in equal steps: each pixel to the right is *z* / *f* further along the camera's sideways direction. So a line is two additions per pixel.

Everything below is a variation on this: what the table holds, and what each line is drawn with.

## Flat colour and a tilting horizon (After Burner Complete)

After Burner Complete's sky, sea and land are flat colours. The detail is all scaled sprites: waves, trees, rocks, clouds and enemies, positioned in 3D and drawn by its scaler ([After Burner Complete's scaler](2d-effects.md#after-burner-completes-scaler)). The background is two auto fills per line [AB32X, SH-2 code at `0x06008280`-`0x060082F6`]:

- **A table of split columns,** one word per line at `0x06007674`. Each line is filled with the sky colour up to its split and the ground colour after it, 160 words in all. When the plane banks, the split moves a little further along on each line and the horizon tilts. The two colours swap sides with the roll direction.
- **A split off the screen** gives a line of one colour, drawn with one fill.
- **The fills also clear the screen**, so the frame buffer is never cleared separately ([Auto fill](../32x/vdp.md#auto-fill)).

In a PicoDrive profile of 6,000 frames over sea and land stages, this is the only background routine that runs, and over a third of the Master's time is spent in its loops waiting for fills to finish <span class="tag emulator">emulator</span> [AB32X, PC profile in PicoDrive]. A tilted horizon over flat colour costs 448 fills per frame, and no pixel writes by the CPU at all.

### A runway from runs

The same program has a second background routine, and it draws a runway on flat ground from per-line tables, with no polygons [AB32X, SH-2 code at `0x06008350`-`0x06008436`, tables built at `0x06006F1C`]:

- **One word per line** at `0x06007474`. A line with bit 11 set is one fill in a colour from a 16-entry table, which shades the sky in 14 steps. Any other line holds a depth row number, and the numbers step faster towards the bottom of the screen, as *z*(*y*) does.
- **A pattern per depth row:** a list of runs, each a colour number in the top 4 bits and a length in the low 12. Across a line: ground, edge, surface, line, surface, centre line, surface, line, surface, edge, ground. Nearer rows have wider runs, so the strip narrows towards the horizon.
- **A phase per row** gives how far into the pattern the line starts, which places the runway sideways. The tables are rebuilt every frame.
- **A colour group per row** turns the four colour numbers into palette entries. Two groups differ only in the lines, white in one and surface grey in the other. Alternating them by depth band dashes the centre line, and the dashes run towards the camera as the plane moves: the stripes of the arcade racers below, applied to a runway.
- **Runs of 28 pixels or more** go to auto fill. Shorter ones are written with byte and word stores.

The 68000 picks the routine for each frame: command 7 selects the split fills, and command 8 selects the runway, followed by commands 9 and 10 with its position and scroll [AB32X, 68000 code at `$1EDBE`-`$1EE30`; Master command handlers at `0x0600379E`-`0x060037C6`]. Two kinds of stage use it <span class="tag emulator">emulator</span>:

- **The base landings, stages 5 and 13.** The plane lands on the runway, rolls along it while supply trucks come alongside, and takes off again. The routine draws all of it, about 1,000 frames in PicoDrive, before stage 6 goes back to the split fills.
- **The canyons, stages 8 and 17.** The stage script turns the routine on shortly after the start and off at the end. The runway's pattern then starts beyond the right edge of the screen, so every ground line is a single run. All the routine shows is the shaded sky over plain ground, and the horizon stays level. The canyon walls are scaled sprites.

Stages 13 and 17 run the same scripts as 5 and 8 [AB32X, stage scripts listed at `$3D802`, 68000 code at `$BD08`-`$BD22` and `$E5AE`-`$EA94`]. The play-through profiled above stopped in stage 2, which is why it never saw the routine.

## A textured floor (d32xr)

Doom's floors and ceilings are textured planes, and d32xr draws them as described above, one span of a line at a time [D32XR, r_data.c, r_phase7.c, sh2_draw.s]:

1. **Per view size**, two tables:
   - **One per line:** the stretched half-width divided by the line's distance from the centre of the view, offset by half a pixel so no entry divides by 0. Multiplied by a floor's height above the eye, it gives that line's distance.
   - **One per column:** 1 / cos of the column's angle from the view direction. Multiplied by a line's distance, it gives the true distance to that pixel along its ray.
2. **Per plane**, the sideways direction of the view divided by the half-width: how far one pixel to the right moves across the floor, per unit of distance. Four divides per plane.
3. **Per span**, a multiply for the distance, a multiply for the distance to the first pixel, and two multiplies for the step across the floor. The first pixel's floor position comes from the sine and cosine of its column's angle. The light level for the span comes from a divide, which d32xr starts on the SH-2's divider before the multiplies and reads after them ([Division unit](../sh2/divu.md)).
4. **Per pixel**, about ten instructions, with no multiply:
   - `SWAP.W` on each 16.16 coordinate brings the whole part down.
   - Masks keep 6 bits of each: textures are 64 × 64, and the mask makes them repeat across the floor for nothing.
   - The *y* coordinate was multiplied by 64 before the span started, so its masked whole part is already the row's offset, and an `OR` joins it to the column.
   - One byte load fetches the texel, a second looks it up in the light table, and one store writes the pixel. The loop runs right to left, writing with pre-decrement.

In its default detail setting d32xr samples floors at half the horizontal resolution and writes each texel to two pixels as one word, which halves the look-ups [D32XR, r_local.h, r_phase7.c].

The homebrew notes' Mode 7 racer makes the same moves in its floor loop: a table of distances per line computed at start-up, so the loop has no divide; and texture addressing by shifts and masks, with a table from tile number to the tile's pixels, instead of `/` and `%`. Its inner loop is a few shifts and two table reads per pixel <span class="tag emulator">emulator</span> [S32X-SKILL, references/software-3d.md, references/optimization.md, references/pico8-porting.md].

Keep texture sizes powers of two. Then wrapping is a mask, a row is a shift, and a 16.16 coordinate needs only `SWAP.W` and `AND` to become an index.

## Roads

### A road from segments

Arcade racers of the 1980s draw the road as a striped ground with a road shape on top, and bend it with a running sum:

- **The track is a list of segments**, each with a curvature and a slope.
- **Each line's road centre** is the previous line's plus an amount that grows with the curvature of the segment at that line's distance. Summed from the bottom of the screen up, a constant curvature gives a smooth bend, and the horizon end of the road swings sideways.
- **Hills** move the horizon and change which distance each line shows.
- **Stripes** come from the distance: lines whose distance falls in an even band get one shade, odd bands the other, and the bands move towards the camera as the car advances.

The homebrew notes list an OutRun-style 32X port with a segmented road, forks and per-stage themes, but describe it only in outline [S32X-SKILL, references/software-3d.md, references/examples.md].

### A road from polygons, filled by line

A homebrew racing game draws its road in 3D, as strips of quadrilaterals along the track. Its optimisation notes give three measured gains <span class="tag emulator">emulator</span> [S32X-SKILL, references/optimization.md]:

- **Walk each strip as one shape, line by line.** The strip's two long edges are shared from one segment to the next. Filling it line by line needs about 6 divides per segment, against about 30 when each segment was cut into 10 triangles.
- **Fill only what the road does not cover.** The road filler records each line's left and right edge, and the grass is drawn only beside it. Overdraw fell from 1.36 to 1.05 times the screen, about 21,000 fewer pixel writes per frame.
- **Inline the span fill.** At about 1,600 spans per frame, calling a span routine and clipping again inside it took 62% of the fill time.

### The Mega Drive's own tools

The Mega Drive's VDP can scroll each line of a plane by a different amount ([Horizontal scrolling](../megadrive/vdp-planes.md#horizontal-scrolling)). A road drawn once in tiles, straight, can be bent by moving each line sideways by the running sum above, and hills can be made by changing which line of the picture appears where, a job the 32X's line table can also do for its own layer ([The line table](../32x/vdp.md#the-line-table)). On a 32X, either layer could carry the road while the SH-2s draw only the cars and scenery. None of the programs in the sources does this; it is listed as an open question.

## Objects on the ground

Roadside objects and other cars are almost always scaled sprites:

- **Scale by stepping.** Work out the source step for the sprite's size once, and add it per pixel and per line ([Stepping through the source](2d-effects.md#stepping-through-the-source)). The homebrew Mode 7 racer measured more than ten times the speed of dividing per pixel <span class="tag emulator">emulator</span> [S32X-SKILL, references/optimization.md].
- **Pre-drawn angles.** Render each 3D model from a fixed set of angles when building, and pick the nearest at run time. A homebrew water racer turned 46 models into 8 angles of 48 × 48 pixels each; a car game uses 64 angles [S32X-SKILL, references/software-3d.md].
- **Sprite stacking.** Draw a stack of horizontal slices of an object, each shifted up a little and turned to the same angle, and top-down art looks solid from any direction [S32X-SKILL, references/software-3d.md].
- **Sort them.** Draw far objects first; with many objects, sort into buckets ([Bucket sorts](software-3d.md#bucket-sorts)).

The depth each object needs is the same one-divide-per-object projection as in [Software 3D](software-3d.md#projection-dividing-by-depth). After Burner Complete's bias, a divide by *z*/32 + 32, keeps the nearest objects at a sensible size without a near-plane test.

## Drawing half the lines

The ground changes slowly from one line to the next. The homebrew racer draws only 112 lines and points two display lines at each through the line table, so the VDP shows each one twice at no cost. It left about 40% of the frame free, at the price of half the vertical detail; its notes say to enable it only when that saving moves the game into a faster frame rate step <span class="tag emulator">emulator</span> [S32X-SKILL, references/optimization.md]. See [Scaling the whole layer](2d-effects.md#scaling-the-whole-layer-the-line-table-does-the-vertical-half) for the same trick used for zooming.

## In emulators

After Burner Complete's background is all auto fill, and upstream PicoDrive completes fills instantly while holding FEN for the fill's time. The time the profile shows in the fill loop is therefore set by the emulator's model of FEN, not by the fills ([Auto fill](../32x/vdp.md#auto-fill)). The homebrew measurements were all taken in PicoDrive.

## What to take away

- A flat ground has one distance per line: put it in a table and nothing per pixel needs a divide.
- Flat ground is two fills per line, and a tilting horizon is a table of split points.
- A textured floor is two additions per pixel, with power-of-two textures addressed by `SWAP.W` and masks.
- Bend roads with a running sum per line, and let the distance choose the stripes.
- Draw objects as scaled sprites, pre-drawn from several angles if they must turn.
- Fill only what the road leaves, and consider drawing every other line.

## Open questions

- How fast is a road bent by the Mega Drive's per-line scroll, under 32X sprites drawn by the SH-2s, compared with a road drawn by an SH-2?
- How long does d32xr's floor loop take per pixel on a console, with its texel and light look-ups going through the cache?

## Sources

- [AB32X](../appendices/bibliography.md#ab32x): SH-2 code at `0x06008280`-`0x060082F6`, `0x06008350`-`0x06008436`, `0x06006F1C`, `0x0600379E`-`0x060037C6`; 68000 code at `$BD08`-`$BD22`, `$E5AE`-`$EA94`, `$1EDBE`-`$1EE30`; stage scripts listed at `$3D802`; PC profile and screenshots in PicoDrive, with stages 5 and 8 reached by pointing stage 1's entry at their scripts in a copy of the ROM
- [D32XR](../appendices/bibliography.md#d32xr): r_data.c, r_local.h, r_phase7.c, sh2_draw.s
- [S32X-SKILL](../appendices/bibliography.md#s32x-skill): references/software-3d.md, references/optimization.md, references/pico8-porting.md, references/examples.md
