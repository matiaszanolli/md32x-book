# 2D drawing and effects

The 32X has no sprites, no tiles and no scaler of its own. Sega's 1994 introduction to the system lists "enhanced scaling and rotation" among its features [32X-INTRO, overview], but no register does either: every pixel on the 32X layer is written into a frame buffer by an SH-2, by the 68000 or by the VDP's auto fill ([The 32X VDP](../32x/vdp.md)). This chapter is about doing 2D work in software there: filled shapes, sprites, scaling, rotation, transparency, screen transitions and lines. It also covers the one place a 2D effect is drawn into Mega Drive tile memory, and how split screens work.

## What the hardware gives you

Four features of the 32X VDP do part of the work for free. Each is described in [The 32X VDP](../32x/vdp.md); here is what each is good for:

| Feature | Use |
|---------|-----|
| [Line table](../32x/vdp.md#the-line-table) | Repeat or skip whole lines: vertical scaling, wobble and vertical scrolling of the whole layer, for 224 words of writes |
| [Overwrite image](../32x/vdp.md#the-normal-and-overwrite-images) | Zero bytes are not written, so a shape with holes is copied as plain words, with no mask and no test |
| [Auto fill](../32x/vdp.md#auto-fill) | Clears and flat-coloured runs of up to 256 words, while the CPU does something else |
| [Guard bands](../32x/vdp.md#guard-bands-drawing-without-clipping) | Memory around the visible picture, so sprites that hang off the edge need no clipping |

Everything else costs SH-2 time, and in packed pixel mode that time is set mostly by how many words are written to the frame buffer ([Writing from the SH-2](../32x/vdp.md#writing-from-the-sh-2)).

## Shapes: everything is a span

The simplest design draws every filled shape as a set of horizontal runs, one per row, through one routine that clips. The homebrew notes' shape library does this. Its span writer drops rows off the screen, swaps the ends if needed, clamps them to the screen, and fills the bytes between. Every other shape only works out where each row starts and ends [S32X-SKILL, assets/2d/gfx_shapes.c]:

- **Triangle.** For each row between the lowest and highest corner, each of the three edges that crosses the row gives an x by interpolation, and the span runs from the smallest to the largest. A flat edge contributes both its ends. No sorting of corners is needed, but every row costs up to three divides, and a divide in C is a software routine of about 80 clocks ([Projecting: one divide per slice](voxel.md#projecting-one-divide-per-slice)). Stepping each edge's x by a slope computed once per edge removes them; see [Software 3D](software-3d.md).
- **Circle.** For each row at distance *dy* from the centre, the half-width is the largest *dx* with *dx*² ≤ *r*² − *dy*², found by counting up while (*dx* + 1)² still fits. That is free of divides but takes time proportional to *r*² overall. Since the half-width only ever shrinks moving away from the centre row, starting each row's search from the last row's answer makes it linear.
- **Polygon.** An outline stored as pairs of signed bytes relative to a centre, scaled by a fraction, and filled as a fan of triangles from the centre. This is right for outlines that are visible from their centre, such as ships, and one table gives every size.

Two details matter on the 32X. A span written a byte at a time cannot draw colour 0, because byte writes of 0 are ignored in the normal image too ([The normal and overwrite images](../32x/vdp.md#the-normal-and-overwrite-images)). And a span is faster written as words, two pixels at a time, with a byte at each end only when it starts or ends on an odd pixel.

Long flat spans can be handed to the VDP. After Burner Complete draws its whole sky and sea as two auto fills per line, the boundary between them moving along each line to follow the banking horizon ([Auto fill](../32x/vdp.md#auto-fill)) [AB32X, SH-2 code at `0x06008280`]. A fill runs in words and stays within one 256-word block, so it suits wide runs that start and end on even pixels. Its lines are 512 bytes apart, exactly one block, so a fill along a line never crosses a block boundary; the sources do not say whether that was why the pitch was chosen ([Auto fill](../32x/vdp.md#auto-fill)).

## Sprites without hardware sprites

A "sprite" on the 32X is a rectangle of pixels copied into the frame buffer by software. Three things shipped games do to make that cheap:

- **Transparency without a test.** Two ways. After Burner Complete writes every scaled sprite through the overwrite image (the destination register starts at `0x24020200`), and its inner loop copies words and never tests for transparent pixels: the VDP leaves the zero bytes alone [AB32X, SH-2 code at `0x06006778`-`0x06006A44`, `0x06005460`]. Mortal Kombat II's sprite blitters work differently. They read run-length data and skip a transparent run by moving the destination on, and they add a palette offset to every colour they write, so they never write a zero and do not need the overwrite image, although their destination is also an overwrite-image address (`0x24028C00` plus line × 368 plus x) [MK2, SH-2 code at `0x0600271E`, `0x060027F0`-`0x06002994`; [Drawn directly](compression.md#drawn-directly-mortal-kombat-ii)]. The overwrite image does serve Mortal Kombat II's blits of uncompressed rectangles, which copy bytes (`0x06004CC0`) or words (`0x06004CF2`) with holes in them and test nothing [MK2, SH-2 code at `0x06004CC0`, `0x06004CF2`].
- **No clipping.** Mortal Kombat II's lines are 368 bytes apart, so each has a 48-byte tail that is never shown, and there are 96 hidden lines above the first. It only rejects a sprite that is completely off screen ([Guard bands](../32x/vdp.md#guard-bands-drawing-without-clipping)) [MK2, SH-2 code at `0x06002CEC`].
- **One copy of each frame, mirrored when drawn.** Mortal Kombat II has a second blitter for each sprite format that decodes the same data but moves the destination leftwards, and negates the hotspot [MK2, SH-2 code at `0x0600292C`]. After Burner Complete's scaler always writes right to left. For an unmirrored sprite it walks the source from its right-hand end with a negative step; for a mirrored one it walks from the left with a positive step and swaps the two bytes of each source word with `SWAP.B` [AB32X, SH-2 code at `0x06006868`, `0x060053E2`-`0x060054B4`]. Homebrew strategy games store only east-facing frames and mirror them for west [S32X-SKILL, references/strategy-and-grid.md]. Any of these halves the art for anything that faces left and right.

Sprite art is normally compressed in the cartridge. Mortal Kombat II's blitters draw straight from run-length data; After Burner Complete decodes each shape once into a cache in SDRAM and scales from there. See [Compression](compression.md) and [Memory](memory.md).

## Scaling

### Stepping through the source

Scaling a sprite means walking the destination rectangle and, for each pixel, picking a source pixel. Keep the source position as a 16.16 fixed-point number and add a step of source width ÷ destination width to it for each destination pixel. Then read the source at the integer part. The step is worked out once per sprite, so the loop has no divide [S32X-SKILL, references/2d-and-shmup.md]. Rows work the same way, with a second step for the source row.

### After Burner Complete's scaler

After Burner Complete draws up to 92 scaled sprites a picture during play, and up to 143 on its title screen, at 30 pictures a second <span class="tag emulator">emulator</span> [AB32X, sprite list length watched in PicoDrive over 2,000 frames of play and 500 of the title]. Its scaler is a good model [AB32X, SH-2 code at `0x06006778`-`0x06006A44`]:

**Four instructions per two pixels.** The horizontal position is kept in two registers: the fraction in the top half of one, the integer, in units of two pixels, in another. Each step of the loop is:

| Instruction | Does |
|-------------|------|
| `ADDC r13,r8` | Adds the fractional step to the fraction. A carry out goes into T |
| `MOV.W @(r0,r0),r1` | Reads two source pixels. `@(R0,R0)` addresses R0 + R0, so R0 holds half an address and needs no shift |
| `ADDC r14,r0` | Adds the whole-number step and the carry from the fraction |
| `MOV.W r1,@-r6` | Writes the two pixels, moving the destination left |

This is the normal mode, entered at `0x060067B4`. It writes right to left, so for the picture to come out the right way round the source is read from its right-hand end too: the sprite's record holds a negative whole-number step, and the start address is the end of the row (`0x060053E2`). There is no compare and no transparency test. The load's result is used two instructions later, so it does not stall ([Load-use](../sh2/pipeline.md)).

**Unrolled eight times, entered in the middle.** The four instructions are repeated eight times. A computed jump at the start skips enough copies that the first pass covers the remainder of the width, so one counter test serves eight words ([Pipeline](../sh2/pipeline.md#other-patterns-in-real-code)).

**Rows by one multiply.** A 16.16 row counter advances by the vertical step for each line drawn. The source row's address is its integer part times the sprite's width, one `MULS.W`, and the destination moves on 512 bytes, one frame-buffer line.

**Four modes,** chosen per sprite by a byte in its record (the normal and mirrored modes are 8 and 12, picked by the sign of the step; what selects the doubled ones was not traced):

| Mode | Writes |
|------|--------|
| Normal | Two source pixels per word, as above |
| Mirrored | A positive step from the left-hand end, with a `SWAP.B` before each store: five instructions per word instead of four |
| Double | Each source pixel doubled into a word, written to two lines: every source pixel becomes a 2 × 2 block |
| Double, mirrored | The same, mirrored |

The double mode draws large sprites, close to the camera, at half resolution: half the source reads and half the loop passes for the same area of screen.

**Where it falls short.** Steps work in two-pixel units horizontally, so a sprite's edges and its scale move in steps of two pixels. Sprites are drawn in the order of a depth sort and simply overwrite each other, so there is no per-pixel depth ([Software 3D](software-3d.md)).

### Scaling the whole layer: the line table does the vertical half

When the whole picture is scaled, as in a zoom on a map, the line table makes the vertical axis free. Draw each *distinct* source row once into the frame buffer, and point every display line that shows it at the same row. Aerobiz Ultimate measured this on its world map: the time per picture is in proportion to the number of source rows drawn, not to the lines shown <span class="tag emulator">emulator</span> [AU-NOTES, ROADMAP.md U-035]:

| Zoom | Source rows drawn | Frames per picture |
|------|-------------------|--------------------|
| 1× | 224 | 2.13 |
| 2× | 112 | 1.06 |
| 4× | 56 | 0.53 |

So a full 320 × 224 picture drawn pixel by pixel took 2.13 frames in this project's loop, and zooming in makes it cheaper. That is 71,680 pixels in about 818,000 clocks (a frame is about 384,000), 11.4 clocks a pixel: a figure for a compiled per-pixel loop, not a limit of the SH-2. After Burner Complete's scaler spends two instructions a pixel, and the rotation below about 31 clocks a pixel (5.75 frames). The Aerobiz figures come from stock PicoDrive, before the project gave its copy a cache and a wait-state model, so they are instruction counts; Ares put the 1:1 redraw at 2 to 3 frames [AU-NOTES, ROADMAP.md U-035, U-093; [Moving decompression to an SH-2](compression.md#moving-decompression-to-an-sh-2)]. Horizontal scaling still needs the per-pixel loop; the screen shift bit only pans by one pixel, it does not scale.

### Stretching in place

marsdev's sample doubles the width of a direct colour picture in place, line by line, by working from the right-hand end, so no source pixel is overwritten before it is read [MARSDEV, examples/32x-skeleton/sh_src/mars_start.s, `ScreenStretch`]. Its smoothing variant writes each pixel followed by the average of it and its neighbour, and averages all three colour channels with one addition: masking each 15-bit colour with `$7BDE` clears the lowest bit of every channel, so the sum of two masked colours cannot carry from one channel into the next, and one shift right halves all three.

## Rotation

### Mapping each screen pixel back

To rotate and scale a picture, work backwards: for each screen pixel, find the source pixel that lands there. Along a screen row the source position moves by a fixed (*du*/*dx*, *dv*/*dx*), and from one row to the next by (*du*/*dy*, *dv*/*dy*). For a rotation by *t* at scale *s* these are cos *t* / *s*, sin *t* / *s*, −sin *t* / *s* and cos *t* / *s*. Kept in 16.16, stepping the source position along a row needs two additions per pixel and no multiply [AU-NOTES, disasm/sh2/master/fb.c]. The multiply comes in finding the source pixel's address, below.

It costs much more than scaling. Aerobiz Ultimate measured a full-screen rotation at 5.75 frames per picture, against 2.13 for a straight copy of the same source, about 10 pictures a second <span class="tag emulator">emulator</span> [AU-NOTES, ROADMAP.md U-037]. Three reasons:

- **No line can be shared.** Once the source row changes along a screen row, no two screen lines show the same pixels, so the line table trick is lost and every line is drawn.
- **Each pixel needs its own source row,** so the address of the source pixel, row × width + column, costs a multiply (or a table) per pixel. A source 256 or 512 pixels wide turns the multiply into a shift.
- **Each pixel needs a bounds test** on both coordinates, unless the source is a power of two in size and the coordinates are masked instead.

Treat rotation as an effect for a region, not the screen. A 128 × 128 area, about a quarter of the screen, came in at about one frame [AU-NOTES, ROADMAP.md U-037].

A useful test: rotate by zero at scale 1 and compare the result with a straight copy. Aerobiz Ultimate's identity rotation gives the same checksum as its 1:1 blit (`$8040EA91`), which proves the mapping before anything is turned [AU-NOTES, disasm/sh2/master/fb.c `sh2_affine_test`].

### The SEGA logo: every frame worked out in advance

Aerobiz Ultimate opens with the SEGA logo spinning in from a distance [AU-NOTES, tools/make_sega_logo.py; disasm/sh2/master/fb.c] <span class="tag emulator">emulator</span>:

- **Nothing is computed on the SH-2.** A build-time script works out, for each of 110 frames of motion and 16 still ones, the six 16.16 values of the backwards mapping and a box around what the logo covers, its left and right edges rounded to even pixels. The SH-2 does no trigonometry and no division.
- **Motion that feels even.** Time is eased as *e* = 1 − (1 − *t*)³. The scale is 0.06 raised to the power (1 − *e*), so it grows by equal ratios rather than equal amounts, which the eye sees as a steady approach. The angle unwinds two turns.
- **The build checks the result.** The script draws the last picture exactly as the SH-2 will and stops the build unless it lands pixel for pixel on the Mega Drive's own logo.
- **Pictures follow the clock.** The SH-2 picks which picture to draw from the V-Blank count, so when one is slow to draw, the animation skips ahead rather than running late. It clears only the box the logo covered last time in that buffer.

How the layer is then handed back to the Mega Drive without a visible change is in [Mixing 32X and Mega Drive graphics](../32x/compositing.md#handing-the-screen-from-one-layer-to-the-other).

### Rotating without rotating pixels

After Burner Complete shows a lot of rotation and never rotates a pixel [AB32X, notes on the title sequence and play]:

- Its title logo is built from sphere sprites. The logo turns by rotating each sphere's position in 3D; each sphere is then projected and drawn by the scaler. Up to 143 of them a picture.
- When the plane banks, the horizon tilts because each line's two fills meet at a different point. The ground detail, enemies and clouds are upright sprites at rotated positions.

For objects that look the same from any angle, such as spheres, clouds, explosions and trees seen from above, rotating the positions and scaling upright sprites is far cheaper than rotating an image.

## Transparency in 8-bit colour

In packed pixel mode a pixel is a palette number, so there is no blending in hardware. (The through bit decides which of the two video chips is in front, not how they mix; see [Mixing 32X and Mega Drive graphics](../32x/compositing.md).) Two software methods [S32X-SKILL, references/2d-and-shmup.md]:

- **Leave pixels out in a pattern.** Skip one pixel in two for 50%, or compare each pixel's position against a 4 × 4 ordered-dither table to get 16 levels. It costs no memory and is fine for fades of portraits and pictures, at the price of a visible screen-door pattern.
- **A blend table.** For each pair of source and destination palette numbers, store the palette number nearest the mixed colour, computed in advance. That is one table read per pixel, plus a read of the destination, and 64 KB (256 × 256 entries) per level of transparency. Three levels, 25, 50 and 75%, are 192 KB, three quarters of the 256 KB of SDRAM, so they cannot all live there. In the cartridge they miss the cache constantly, because the index is two unrelated palette numbers, at 64 to 136 clocks a miss against 12 from SDRAM ([timing](../32x/timing.md#the-figures)). The ways round it: one level only, in SDRAM; or a table over a reduced palette, since a table for 64 colours needs 64 × 64 = 4 KB a level.

In direct colour mode the mask trick from [Stretching in place](#stretching-in-place) averages two colours in a few instructions.

Reading the destination is the expensive part on the 32X: a frame buffer read costs several wait states ([Writing from the SH-2](../32x/vdp.md#writing-from-the-sh-2)). A blend over a picture that the program drew itself is cheaper done on its own copy in SDRAM.

## Transitions

### Doom's screen melt

d32xr reproduces Doom's melt, where the old screen slides down in uneven columns to reveal the new one [D32XR, f_wipe.c]:

- **Columns of two pixels,** 160 of them, each a word wide. Each column starts after a random delay of up to 15 steps, never more than one step different from its neighbour, so the edge is ragged but connected.
- **Speed.** A column speeds up over its first 16 lines and then moves 4 lines per frame (5 on PAL), half of Doom's rate, because with two frame buffers each buffer is updated every other frame.
- **The new screen waits on the Mega Drive side, and the 68000 moves it.** The SH-2s cannot reach Mega Drive video memory. They send a command through COMM0 (a column number, with offset and length in COMM2). The 68000 takes the frame buffer away by clearing FM, copies one 224-word column between the frame buffer and Mega Drive memory, gives the buffer back and clears COMM0 to say it is done. The SH-2s write the next command only when COMM0 is 0. Every column moved is one such handoff ([Sharing without colliding](../patterns/bus.md#sharing-without-colliding)). The first 140 columns go to VRAM (140 × 448 bytes, nearly all of it); the rest go to a buffer in the Mega CD's word RAM, or to a 16 KB buffer in work RAM without one. The order of a wipe [D32XR, f_wipe.c, marsnew.c `I_StoreScreenCopy`, marshw.c, src-md/crt0.s `cpy_md_vram`]:
  1. The old screen is stored on the Mega Drive side, one column at a time. The frame buffers are then flipped and the copy is put back into the buffer that is now the drawing one, so that both buffers hold the old picture (the code's order of store, flip, restore reads that way, and the in-place shifting needs it, since the two buffers alternate).
  2. The new screen is drawn into the frame buffer.
  3. A swap makes the Mega Drive side hold the new screen and the frame buffer the old one.
  4. Each step, for every column that uncovered a strip since the last step, the strip is fetched back from the Mega Drive side, and the rest of the old picture is shifted down in place, from the bottom up. That is up to 160 handoffs a step.
  The price is the Mega Drive layer: with VRAM full of screen columns it has nothing to show for the length of the wipe, with the 32X put in front, and afterwards the 68000 is told to initialise the VDP and VRAM again.
- **Both SH-2s** take columns from a shared counter, under a `tas.b` lock ([Splitting work across three CPUs](../patterns/cpu-split.md#handing-work-across-without-waiting)).

### Doom's fire

The d32xr title screen burns with a fire effect [D32XR, m_fire.c]:

- **A grid of heat values,** 320 × 72, with a full-heat bottom row. On each pass, every cell copies its heat to the cell above, moved 0 to 2 cells sideways and losing 0 or 1 heat, both taken from one random number.
- **Random numbers from a table:** 256 entries filled once, read in turn, instead of calling the random number generator per cell.
- **Colours chosen at start-up:** the fire's 26-colour ramp is matched to the nearest entries of the game palette by squared colour distance.
- **Going out:** random amounts are taken off the bottom rows, four cells per longword.
- **Two CPUs, no synchronisation.** The Slave spreads the fire continuously; the Master scrolls the title picture and copies the fire into the frame buffer two pixels per word. They do not wait for each other, and the occasional mismatch between the two halves of a picture does not show in a fire.

### Fades

A fade on the 32X layer is a palette change, written during vertical blank because the palette is not double-buffered ([Colours and the palette](../32x/vdp.md#colours-and-the-palette)). When the Mega Drive picture has to fade at the same time, the 32X palette has to follow the Mega Drive's: see [Following the Mega Drive's palette](../32x/compositing.md#following-the-mega-drives-palette).

## Lines

### Smooth lines, split between the CPUs

d32xr's automap draws anti-aliased lines [D32XR, am_main.c]:

- **Two pixels per step.** For each step along the line's long axis, it draws the two pixels the line passes between. The fractional position, cut to 3 bits, sets how dark each is.
- **Darkness is a palette offset.** The automap's colours are runs of 8 palette entries from bright to dark, so "darker by *n*" is just the colour number plus or minus *n*.
- **Cheap rejection.** Lines entirely above or below the area being drawn are skipped before any work.
- **Both SH-2s:** the Master draws the top half of the screen and the Slave the bottom half, each clipping every line to its own rows. No locks are needed, because the two halves never touch the same pixel.

### Drawing into Mega Drive tiles

Aerobiz Supersonic, a plain Mega Drive game, draws its airline routes as lines on the world map. The map is unpacked into work RAM as 704 tiles that are all different (32 × 22), so the tile data forms one bitmap of 256 × 176 pixels at 4 bits per pixel [AB-DISASM, disasm/modules/68k/graphics/DrawTilemapLine.asm, DrawRouteLines.asm, LoadScreenGfx.asm]:

- **Finding a pixel.** Pixel (*x*, *y*) is in tile column *x* / 8, at byte (*x* / 8) × 32 + ((*x* / 4) & 1) × 2 + (*y* / 8) × 1,024 + (*y* & 7) × 4 from the start, in the nibble selected by *x* & 3 within that word.
- **Plotting.** An AND with one of four masks clears the nibble; an OR with the colour, shifted in advance into each of the four positions, sets it.
- **The line** is integer Bresenham along the longer axis.
- **The map wraps.** The world is a cylinder 256 pixels round, so if going the other way is shorter, the line goes that way and each x is wrapped into 0-255. Routes across the Pacific cross the edge of the map.
- **Then the whole map is uploaded** to video memory as 704 tiles, shown by a fixed name table.

Both routines also check for one particular route, from (32, 34) to (220, 102), and move its start up one pixel. One route's appearance was fixed in code rather than in the data [AB-DISASM, DrawTilemapLine.asm, DrawTilemapLineWrap.asm]. (The disassembly's comments call the target a "tilemap" and the colour "palette bits"; the address arithmetic shows it is tile pixel data.)

The same idea works for any picture on the Mega Drive side that must be drawn rather than assembled from tiles: give every tile in the area its own pattern, and the patterns become a bitmap.

## Split screens

Two views side by side or one above the other are the drawing pass run twice, with a camera and a HUD for each player, each clipped to its half of the frame buffer. Every pixel of both views is still written, so the drawing budget does not shrink: two half-height views cost about as much as one full one, plus everything per object, such as transforms and sorting, done twice [S32X-SKILL, references/2d-and-shmup.md].

On the 32X the line table can help: each view can be drawn into its own area of the frame buffer, at its own line pitch, and the line table stacks them on screen. The PRI bit can also change between lines, so one view can be in front of the Mega Drive layer and the other behind it, but it takes a register write timed to each boundary, from an H interrupt ([The rule for each pixel](../32x/compositing.md#the-rule-for-each-pixel)). No program in the sources does either.

## In emulators

PicoDrive charges frame buffer writes almost nothing, and writes an auto fill's data at once, holding only FEN for the fill's time; Ares charges a flat cost per write. Neither models the write buffer's 3- and 5-clock cases or the bus shared with the other SH-2 ([Bus controller](../sh2/bsc.md#emulators-do-not-show-this)). The timings in this chapter marked <span class="tag emulator">emulator</span> show which method is faster in proportion, not how fast it is on a console. Drawing is usually limited by frame buffer writes, the part emulators model least.

## What to take away

- Reduce every shape to spans with one clipping routine, and write words.
- Use the hardware's free work: the overwrite image for transparency, guard bands instead of clipping, auto fill for flat runs, and the line table for vertical scaling and repeats.
- Scale with fixed-point stepping, the fraction and integer in separate registers joined by `ADDC`, unrolled, with no per-pixel test.
- Mirror at draw time instead of storing mirrored art.
- Rotate regions, not screens, and precompute whatever does not depend on the player. Where objects look the same from every angle, rotate positions, not pixels.
- Avoid reading the frame buffer: blend and stretch from a copy in SDRAM.
- Mega Drive memory is storage the 68000 can lend, at the cost of an FM handoff for each transfer and of the Mega Drive layer while it is in use.

## Open questions

- How many words per second can one SH-2 write into the frame buffer on a console, through the normal and the overwrite image, with the other SH-2 also drawing? That number bounds every effect in this chapter.
- How long does After Burner Complete's scaler take per sprite on a console, and is it limited by the loop or by the frame buffer?
- Do the line table and PRI changes per line combine cleanly for split screens on hardware?

## Sources

- [32X-INTRO](../appendices/bibliography.md#32x-intro): overview
- [S32X-SKILL](../appendices/bibliography.md#s32x-skill): assets/2d/gfx_shapes.c, references/2d-and-shmup.md, references/strategy-and-grid.md
- [AB32X](../appendices/bibliography.md#ab32x): SH-2 code at `0x06005300`-`0x060054B4`, `0x06006778`-`0x06006A44`, `0x06006868`, `0x06008280`; sprite counts watched in PicoDrive
- [MK2](../appendices/bibliography.md#mk2): SH-2 code at `0x06002CEC`, `0x0600271E`, `0x060027F0`-`0x06002994`, `0x06004CC0`, `0x06004CF2`
- [AU-NOTES](../appendices/bibliography.md#au-notes): disasm/sh2/master/fb.c, tools/make_sega_logo.py, ROADMAP.md U-035, U-037, U-093
- [MARSDEV](../appendices/bibliography.md#marsdev): examples/32x-skeleton/sh_src/mars_start.s
- [D32XR](../appendices/bibliography.md#d32xr): f_wipe.c, marsnew.c, marshw.c, src-md/crt0.s, m_fire.c, am_main.c
- [AB-DISASM](../appendices/bibliography.md#ab-disasm): disasm/modules/68k/graphics/DrawTilemapLine.asm, DrawTilemapLineWrap.asm, DrawRouteLines.asm, LoadScreenGfx.asm
