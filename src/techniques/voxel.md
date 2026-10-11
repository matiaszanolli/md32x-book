# Voxel landscapes

A voxel landscape is a height map drawn in perspective. The ground is divided into square cells, every cell has its own height and colour, and the view looks down across them as hills scroll towards the viewer. It is not a polygon mesh. Each cell is drawn as a block of colour sized by its distance. Games like *Comanche* (1992) made the style famous on PCs.

No retail 32X game read for this book uses it. The one source is a homebrew port of a voxel shoot-'em-up, `zepton32x`, documented in S32X-SKILL. Its value here is less the technique than its measurement: in PicoDrive the textbook method lost to a simpler one, though not on equal terms ([Which won](#which-won)) <span class="tag emulator">emulator</span> [S32X-SKILL, voxel-landscape.md]. The game's own source was not available for this book, so what follows rests on the project's notes and the code they list, and the pixel and cycle counts below are estimates worked out from that code [BOOK-TOOLS, voxel_counts.py].

## The world

- **A grid of cells**, here 32 columns by 28 depth slices. The nearest slice is a fixed distance ahead of the camera.
- **Heights computed, not stored.** Each cell's height is the sum of two sine waves and a cosine wave of different frequencies, plus shaped features (a river valley, a plateau, a volcano), rounded down to a multiple of a step for the blocky look. The waves are read from the skill's 256-entry sine table [S32X-SKILL, voxel-landscape.md; assets/3d/r3d.c]. The colour comes from the height: water, sand, grass, rock, snow. In the notes' code the height is a function of the cell's column and world row alone, which matters [below](#making-either-method-cheaper).
- **Moving forward** is a 16.16 fixed-point scroll value. Its whole part picks which world row each slice shows; its fraction moves every slice a little nearer, so the motion is smooth between rows ([Fixed-point arithmetic](fixed-point.md)).
- **Choose the scale so the near slice fills the screen.** A near cell should come out about 10 pixels wide. With a cell width of 1 and a focal length of 120, that puts the near plane about 12 units ahead. A near plane at 1 projects everything thousands of pixels off screen, and the result is a black picture. The notes' slices are 1.5 units deep, so the farthest is about 52 units away and its cells are 2 pixels wide.

Watch the fixed-point products. The fraction of a slice times the slice depth overflows 32 bits in this game's units, so it is done as a 64-bit multiply shifted back down.

## Projecting: one divide per slice

Every cell in a depth slice is at the same distance, so they all share the same scale factor, focal length / distance. Projected one by one, each cell needs three divides by its depth: for its screen *x*, its screen *y* and its size. That is 2,688 divides a picture. gcc compiles each into a call to libgcc's software divide, not into use of the SH-2's divider ([Dividing](fixed-point.md#dividing)). For the SH-2 that routine is 77 instructions, about 80 clocks with the call. The notes do not say which compiler built the game. The skill's devkit uses GCC 12.1 [S32X-SKILL, toolchain-and-build.md], and its source gives the SH-2 the same routine, instruction for instruction, as marsdev's GCC 15.1 and GCC 16.2 [GNU-TOOLS], so the figure holds for any of them. The cell-by-cell version therefore spends about 215,000 clocks a picture dividing, more than half a frame. The game computes the scale factor once per slice instead and places every cell in the slice with multiplies: 28 divides, about 2,200 clocks. It keeps the slower, divide-per-point version as a reference, and a test checks that the fast version matches it within a pixel. This is the same saving as in [first-person renderers](first-person.md#what-every-first-person-renderer-does): find what is constant across a row or column, and divide once for it.

The notes add that removing about 1,800 divides this way, by their own count, did not change the picture rate at all <span class="tag emulator">emulator</span> [S32X-SKILL, optimization.md]. That is less odd than it sounds. A picture always lasts a whole number of frames ([Why the rate is 60, 30, 20 or 15](../patterns/60fps.md#why-the-rate-is-60-30-20-or-15)), and 1,800 divides are about 144,000 clocks, under half a frame, which need not move a picture across a frame boundary. The time is still saved, for the next change to use.

## Two ways to draw it

### Method A: blocks, far to near

Draw each slice from the farthest to the nearest, and for each cell fill a rectangle: one more pixel wide than the cell's projected size, twice its size plus two pixels tall, its top at the cell's projected height. Nearer cells paint over farther ones. Cells larger than a pixel get a one-pixel white top edge, which reads as light catching the ridge.

- **Height samples:** one per cell, 896 a picture.
- **Pixels:** the blocks and their ridges come to about 58,000 to 67,000 pixel writes a picture before clipping, more when the scroll fraction has brought every slice nearer. Many pixels are painted more than once.
- **The clear:** the blocks do not cover the screen, so every picture starts with a full clear, another 71,680 pixels at 320 × 224. The project's notes suggest giving the clear to the Slave [S32X-SKILL, voxel-landscape.md].
- **Block height** is the trade: three times the size looks solid but costs too much filling; twice is the balance.

### Method B: one ray per screen column

This is the classic *Comanche* method. For each screen column (two pixels wide here), step from near to far, keeping the highest row drawn so far in that column (a "y-buffer"). At each step, work out which part of the world the column passes through, sample the height there, and project it. If the terrain there is higher on screen than anything drawn so far, fill the column from that height down to the previous top, and record the new top.

- **No overdraw:** every pixel is painted once. Only the sky above the horizon needs clearing, so sky and columns together come to at most one screen, about 72,000 pixels.
- **Height samples:** one per column per slice, 160 × 28 = 4,480 a picture.
- **A wider world.** Each ray crosses the full screen width at every depth, so a slice spans 32 cells at the front and about 140 at the back. Method A draws only its 32 columns, which at the back fill about 73 pixels in the middle of the screen.

### Which won

Method B paints each pixel once and needs no full clear, so it looks like the faster one. Measured in PicoDrive, it ran at about 8 pictures a second and Method A at about 19 <span class="tag emulator">emulator</span> [S32X-SKILL, voxel-landscape.md, optimization.md]. The game shipped with Method A.

| Per picture | Method A | Method B |
|-------------|----------|----------|
| Height samples | 896 | 4,480 |
| Distinct cells sampled | 896 | about 2,400 |
| Divides, as the notes list the code | 28 | 4,480 |
| Pixels drawn | about 58,000-67,000 | at most about 72,000, sky included |
| Clear | 71,680 pixels | none beyond the sky |
| Pixel writes in all | about 129,000-138,000 | at most about 72,000 |
| Average time in PicoDrive | 53 ms (about 19 a second) | 125 ms (about 8 a second) |

The pixel figures are estimates from the notes' code and scale, not measurements. B writes about half as many pixels as A, but the whole difference is A's clear: A's blocks on their own come to about as many pixels as B's columns.

The two methods do not draw the same picture, either. B's rays cover the whole screen width at every depth, about 2,400 distinct cells against A's 896, so part of what B lost on is terrain A never draws. A version of B that stopped at A's 32 columns would take about 2,000 ray steps over the same 896 cells.

**What a ray step costs.** The two times also say what B's extra work costs. Call one height sample and the work that goes with it a step: a cell for A, a ray step for B. A picture takes roughly (steps × the cost of a step) + (pixels × the cost of a pixel). B takes 3,584 more steps than A and writes fewer pixels, yet each picture takes 72 ms longer. So each extra ray step costs at least 72 ms ÷ 3,584 ≈ 20 µs, about 465 SH-2 clocks. Two assumptions sit under that figure:

- **B spends no longer on pixels than A.** It writes fewer, but in narrow strips that cost more instructions per pixel than A's runs ([below](#what-the-32x-changes)). Counting instructions for store loops of plausible shape (the notes do not show the fill routine) gives A 5 to 19 ms of pixel time a picture in PicoDrive and B at most 9. At worst, then, B's pixels take about 4 ms longer than A's, which would lower the figure by about 5%.
- **The rates are exact.** They are not quite. They are counts of pictures over 60 frames [S32X-SKILL, optimization.md], so they are averages over pictures that each lasted a whole number of frames ([Why the rate is 60, 30, 20 or 15](../patterns/60fps.md#why-the-rate-is-60-30-20-or-15)): A's took 3 frames or 4, B's 7 or 8. A picture's real cost can be up to a frame less than the time it was shown for, so the gap is 72 ms give or take a frame (16.7 ms), between 56 and 89 ms. The mix of lengths narrows that. With two neighbouring lengths each, nineteen pictures in 60 frames is 16 of 3 frames and 3 of 4, and eight is 4 of 7 and 4 of 8. A picture whose cost never changed would always last the same number of frames, so a mix means the cost sits close to a frame boundary: A's just under 3 frames, about 50 ms, and B's near 7, about 117 ms. That puts the gap near 67 ms, if the cost varies little from picture to picture.

Taken together, a ray step costs at least about 330 clocks with both assumptions at their worst, 360 if B's pixels cost no more than A's, and most likely about 430.

Three reads of a sine table account for a few dozen of those clocks. Nothing measured says what the height sample costs on its own, and the notes do not show the rest of the height function. Some of the step is other work. As the notes list Method B, the column loop sits outside the slice loop, so each step works out its slice's scale factor again. That is 4,480 library divides a picture, about 80 clocks of every step and 360,000 clocks in all, close to a frame, where A needs 28. The remaining 250 clocks or more of a step, about 350 at the likely figure, are unaccounted for. Candidates are the shaped features, the projection, and the call to the fill routine wherever the terrain rises. If A's cells cost as much as B's steps apart from that divide, A spends 10 ms or more of its 53 on them, about 14 at the likely figure, but that is a condition, not a measurement. So B lost by taking five times as many steps, each of them expensive. A's pixels count too: the notes report that shortening its blocks, from a height they do not give, took it from 12 to 20 pictures a second [S32X-SKILL, optimization.md].

The lesson is the one in [Getting the time per picture down](../patterns/60fps.md#getting-the-time-per-picture-down): find out whether a picture is limited by computation or by filling before choosing an algorithm. Having built a rewrite is no reason to ship it; ship it when it measures faster.

### Making either method cheaper

The changes below combine, and each one changes the figures for the next. The table follows Method B from the code the notes list to a B on A's terms, one change at a time:

| Per picture | Ray steps | Height samples | Divides |
|-------------|-----------|----------------|---------|
| Method B as listed | 4,480 | 4,480 | 4,480 |
| Scale factors in a table | 4,480 | 4,480 | 28 |
| Rays stopped at the grid's sides | about 2,000 | about 2,000 | 28 |
| Plus one sample per cell | about 2,000 | 896 | 28 |
| Plus heights kept in a ring of rows | about 2,000 | 32 per row travelled | 28 |
| Method A as shipped, for comparison | 896 cells | 896 | 28 |
| Method A with the ring | 896 cells | 32 per row travelled | 28 |

**Divide once per slice.** The cheapest fix comes first. Method B as listed breaks this page's first rule: it divides once per ray step, not once per slice. Work out the 28 scale factors once into a table before the column loop, or swap the loops so the slice loop is outside and the 160 y-buffer tops are kept in an array. Either removes about 4,450 divides, some 356,000 clocks or 15.5 ms, from each of B's pictures, for an array of 28 or 160 entries. It does not change the ranking: B would still take about 110 ms against A's 53.

**Stop at the grid's sides.** Give B the same work as A: end each ray where it leaves A's 32 columns. That is about 2,000 steps instead of 4,480, over the same 896 cells A samples, and it draws A's picture. Like A, it then has to clear the screen beside the grid.

**One sample per cell.** Snap each ray step to the cell it falls in, and for each slice remember the last cell sampled and its height, so neighbouring columns that land in the same cell share one sample. Within the grid that brings B down to A's 896 samples. Across the full screen width it saves less: the 160 columns fall in 32 cells at the front but about 140 at the back, so it cuts 4,480 samples to about 2,400, about half. Either way B's look becomes as blocky as A's.

**Keep heights from picture to picture.** The project names the change it expected to turn the result round, though it did not ship it: compute the picture's 32 × 28 height grid once, 896 samples, into an array, and have the rays read from the array [S32X-SKILL, voxel-landscape.md]. That still computes every cell in every picture. Because the height depends only on the cell's column and world row, a row's heights stay valid until the row scrolls out of view. So keep the 28 rows in a ring and compute a new row of 32 heights only when the scroll crosses a row boundary: 32 samples per row travelled instead of 896 every picture. It helps A exactly as much as B. A B that still covers the full width needs a grid about 140 cells wide instead.

**How close that gets.** Removing the divides and the off-grid steps would leave B at about 65 to 85 ms a picture in PicoDrive, plus the clear beside the grid, against A's 50 to 53. That is 15 to 30 ms behind, before either keeps its heights. The low end uses the frame mix above and the high end the floor, and both assume the off-grid steps cost as much as the average step. Keeping heights then saves B more than A, because B takes about 1,100 more steps. If the height sample were all of a step's remaining 250 to 350 clocks, B would gain 12 to 18 ms on A. At best, then, B on A's terms draws about level, and giving A's clear to auto fill ([below](#what-the-32x-changes)) would put A ahead again.

### What the 32X changes

The game uses none of the ideas below, and none has been measured with it.

- **Auto fill suits Method A's clear.** The VDP fills a run of words with one value while the CPUs do other work, at 3 clocks a word after a 7-clock start ([Auto fill](../32x/vdp.md#auto-fill)). A fill covers at most 256 words, so a 320 × 224 screen is 140 fills, about 4.7 ms of fill time by the manual's formula. Some CPU has to issue them, each only after the last has finished, and keep off the frame buffer meanwhile. Knuckles' Chaotix parks its Slave on that job while the Master gets on with its own work ([Living with bus contention](../patterns/bus.md#what-each-program-did)). Method A could do it on the Master if it computes its heights before it draws. One fill lasts 775 clocks, and a ray step costs B several hundred. If A's samples cost anything like that, a Master that starts a fill, computes one or two heights into an array and then starts the next would hardly wait at all. The clear would cost it two register writes and a FEN read per fill, about 3,000 clocks in all. With the ring of rows above there are far fewer heights to compute, and other work would have to fill the gaps. With the clear done either way, A's Master writes no more pixels than B's.
- **Not its blocks.** A block's rows are short: about 11 pixels (5 or 6 words) for the nearest cells, 1 or 2 words at the back. Each fill needs its address and data registers written and FEN read before the next frame buffer access, 7 clocks each from an SH-2 ([Access timing per CPU](../32x/timing.md#the-figures)), on top of its own 7 clocks plus 3 a word. Written by the CPU, the same words cost 3 to 5 clocks each. By these figures a fill the CPU waits for pays at best from about 15 words, 30 pixels, and only against writes that fill the write buffer and pay 5 clocks; against 3-clock writes it never pays, since it costs 3 a word as well. On A's blocks it would lose. Fills pay on long runs, or when the CPU has other work to do meanwhile, as in Star Wars Arcade ([Software 3D](software-3d.md#star-wars-arcade-polygons-as-auto-fills)).
- **B's strips do not combine.** The skill's drawing code uses the 8-bit packed pixel mode [S32X-SKILL, assets/2d/gfx_shapes.c], where a two-pixel strip is one aligned word on each line. No longword store covers it, and no auto fill can draw it, since a fill runs along a line. Each word is a store on its own, followed by a step to the next line, so the frame buffer's write buffer never fills and each write costs the minimum 3 clocks. A's rows go out back to back and pay up to 5 a word once the buffer is full ([Moving data without paying twice](../patterns/bus.md#moving-data-without-paying-twice)). Per pixel the two come out about even on the bus; B pays in instructions instead, one store and one pointer step for every two pixels.
- **The sky can come from the Mega Drive**, as Mortal Kombat II's arenas and Chaotix's levels do. The 32X's cleared field must then be a colour the mixer puts behind the Mega Drive picture, and the terrain colours must be in front of it ([The depth rule](../patterns/layering.md#the-depth-rule-in-front-of-everything-or-behind-it)). This saves no clearing: the terrain moves, so whatever it uncovered must be reset to that colour in every picture. What it buys is a sky with detail, such as clouds or parallax, for no SH-2 time.

## Things that fly into the screen

The game's ships and shots do no 3D maths at all. Everything moves in screen space along a progress value from 0 to 1 <span class="tag emulator">emulator</span> [S32X-SKILL, voxel-landscape.md]:

- **Shots** travel from the player's ship towards the aiming reticle, at the point a fraction *p* of the way, growing smaller as *p* rises. A homing missile moves its target an eighth of the way towards the reticle's current position every frame.
- **Enemies** do the reverse. They appear at the horizon, tiny and central, and as *p* grows they move out to their lane and down towards the player, growing in proportion to *p*.
- **Locking on and hitting** are overlap tests between rectangles on the screen.

This keeps the game rules free of drawing and hardware, so they are tested on a PC: spawn, approach, lock, hit, kill, and an enemy reaching the player.

## In emulators

Both rates come from one emulator, and it leaves out costs that fall unevenly on the two methods.

- **The build.** The notes measured through the skill's own test harness. It loads the libretro version of PicoDrive, built from the libretro project's source at whatever commit was current (the notes give none), and leaves every core option at its default, which the notes say keeps the SH-2 recompiler and its idle-loop detection on [S32X-SKILL, testing.md, optimization.md, assets/harness.c].
- **Frame buffer writes cost only their instructions** in upstream PicoDrive ([Access timing per CPU](../32x/timing.md#in-emulators)). On a console each word costs 3 to 5 clocks, about 1 to 4 clocks a pixel more than PicoDrive charges, depending on whether bytes, words or longwords are stored. A writes about 60,000 more pixels than B, so a console would add roughly 3 to 12 ms to each of A's pictures that it does not add to B's. That narrows a gap of about 67 ms, and at least 52, but probably does not close it. Nobody has measured it.
- **No cache model.** The skill's linker script puts code and constant tables, the sine table among them, in the cartridge at `0x02000000`, read through the cache [S32X-SKILL, assets/mars.ld]. A miss there costs 64 to 136 clocks on a console ([Bus state controller](../sh2/bsc.md#what-a-16-bit-bus-costs)) and nothing in PicoDrive. Which method that hurts more depends on how each one's code falls in the cache, and is not known.
- **Divides are charged in full.** PicoDrive returns the SH-2 divider's results at once ([Division unit](../sh2/divu.md#in-emulators)), but gcc's divides are library code, ordinary instructions, so the divide counts above cost the same clocks in PicoDrive as on a console, cache misses aside.

## What to take away

- A voxel landscape is a height map drawn as blocks or columns of colour, sized by distance.
- Divide once per depth slice, not once per point, and keep that divide out of the inner loop whichever way the loops nest.
- Drawing by blocks paints pixels more than once and needs a full clear; casting per column paints each once but samples the height map five times as often, and as built it also covered more of the world. Most of the pixel difference is the clear, which auto fill can take off the CPU.
- Measure which limit your pictures hit before choosing, and find out what one step of the inner loop costs: here it was hundreds of clocks.
- Heights that depend only on position can be kept from picture to picture. Compute a new row when the view crosses one, not the whole grid every picture.
- Things flying into the screen can live entirely in screen space, with a progress value instead of 3D positions.

## Open questions

- How much of a ray step is the height sample, and where do the rest of its hundreds of clocks go?
- Does Method A still win once frame buffer waits and cache misses are charged, on a console or in an emulator that models them?
- On equal terms (the same 896 cells, one divide per slice) the column method is estimated at 15 to 30 ms behind the block method. Does keeping heights from picture to picture recover that, as it could only if the height sample is most of a ray step?

## Sources

- [S32X-SKILL](../appendices/bibliography.md#s32x-skill): voxel-landscape.md, optimization.md, testing.md, toolchain-and-build.md; assets/3d/r3d.c (sine table), assets/2d/gfx_shapes.c (pixel format), assets/mars.ld (memory map), assets/harness.c (core options)
- [GNU-TOOLS](../appendices/bibliography.md#gnu-tools): libgcc's `___sdivsi3` for `-m2`, 77 instructions, the same in GCC 12.1's source, marsdev's 15.1 and 16.2; GCC 12.1's default divide strategy for the SH-2
- [BOOK-TOOLS](../appendices/bibliography.md#book-tools): voxel_counts.py, the pixel, cell, sample and divide counts on this page
