# First-person engines: raycasting and BSP

Two ways to draw a first-person world on a 32X appear in the book's sources:

- **A grid raycaster**: the world is a grid of cells, and one ray per screen column finds the nearest wall. It is simple, and fast enough for a dungeon crawler at 30 pictures a second on one SH-2, in PicoDrive <span class="tag emulator">emulator</span>.
- **Doom's BSP renderer**: the world is any arrangement of walls at any angle and floors at any height, sorted into a binary space partition. It is far more general and far more work. d32xr, a Doom engine for the 32X, runs it across both SH-2s.

Most of this chapter follows d32xr's source, read at the commit given in the bibliography [D32XR]. The raycaster comes from a homebrew game described in S32X-SKILL, whose source was read too [NOUDAR-32X], measured in PicoDrive <span class="tag emulator">emulator</span>. Neither is a retail game; Sega's own *Doom* for the 32X is not among the book's sources.

## What every first-person renderer does

Both engines rest on one observation. Walls are vertical, so every pixel in one screen column of a wall is at the same distance from the viewer. Floors and ceilings are flat, so every pixel in one screen row of a floor is at the same distance. So:

- **Walls are drawn as columns.** One divide per column gives the scale; then the texture is stepped down the column at a constant rate, with no division per pixel.
- **Floors and ceilings are drawn as rows (spans).** One distance per row, then constant steps across it.

All the expensive maths happens once per column or once per row. What is left per pixel is a texture read, a light look-up and a store. d32xr's wall-column loop does two pixels in 16 SH-2 instructions: for each pixel, it reads a texel, looks it up in the light table, stores it, steps the texture position, and steps the frame buffer pointer down one line [D32XR, sh2_draw.s `I_DrawColumnA`]. d32xr's default view is 320 × 180, 57,600 pixels [D32XR, r_main.c `viewports`, marssave.c], so even eight instructions a pixel come to about 460,000 a picture, more than the 384,000 clocks an SH-2 has in an NTSC frame, before any other work. That is why the tricks below are all about doing fewer pixels or cheaper ones.

## A grid raycaster

A homebrew dungeon crawler shows the simplest design that works, at 30 pictures a second on one SH-2 in PicoDrive, with the Slave parked <span class="tag emulator">emulator</span> [S32X-SKILL, software-3d.md; NOUDAR-32X, README.md, src/main.c]:

- **One ray per column.** Each ray steps through the map grid cell by cell (a DDA) until it meets a wall. Each ray's direction is the view direction plus a sideways part, so the distance the DDA ends with is already the distance along the view direction, and walls come out straight with no cosine correction. Each column then divides four times: twice to set up the DDA's steps (1 / the ray's *x* and *y* parts), once for the wall's height on screen (view height ÷ distance), and once for the texture step down the column. The game drives the SH-2's division unit by hand, writing the divisor and dividend registers and reading the quotient straight away, about 39 clocks a divide, which is fine a few times per column ([Division unit](../sh2/divu.md)) [NOUDAR-32X, src/render.c `draw_walls`, src/fixed.h `fix_div`]. Its own comment notes that a plain C divide would have gone to libgcc's software routine instead ([Dividing](fixed-point.md#dividing)).
- **Cast at a quarter of the pixels.** The game casts into a 128 × 80 buffer in SDRAM, then expands it two by two into a 256 × 160 view. Two source pixels *a*, *b* become one longword *aabb*, written to two rows, so the expand is aligned 32-bit stores of four pixels each [NOUDAR-32X, src/render.c `blit2x`]. The project calls casting at quarter resolution its single biggest saving.
- **A depth per column.** Each column's wall distance is kept, so that sprites can be clipped against the walls later without a full-screen depth buffer.
- **Floors and ceilings per cell**, with animated textures such as lava, and a scrolling sky wherever a cell has no ceiling.
- **Sprites in two passes.** See-through scenery such as bars and arches is collected during the ray walk. Monsters, items and effects are sorted by depth and drawn as flat sprites facing the viewer, each column clipped against that column's wall depth.
- **A smooth camera over grid moves.** The game moves one cell or turns 90° per step, but the camera slides an eighth of a cell, or 1/32 of a turn, per frame. A turn-based game then scrolls like a free-moving one [S32X-SKILL, strategy-and-grid.md].

## Lighting and fog through the palette

Darkening a pixel by arithmetic costs work per pixel. With 256 palette colours there is a cheaper way: put darker copies of the colours in the palette, and choose which copy a pixel uses.

- **Shade banks.** The crawler uses a 64-colour base palette repeated as four banks of decreasing brightness, filling all 256 entries. A pixel's value is its bank times 64 plus its colour, with the bank chosen per column, per floor row or per sprite from its distance. The project calls the fog free. In its code it costs one OR per pixel: the textures hold colours 0 to 63, and the drawer ORs the bank into each texel as it stores it <span class="tag emulator">emulator</span> [S32X-SKILL, software-3d.md; NOUDAR-32X, src/render.c `shade_of`].
- **Shade tables.** When the palette is organised as brightness ramps of 16 steps per hue, a table indexed by depth and colour gives the darker colour; the drawer reads through it <span class="tag emulator">emulator</span> [S32X-SKILL, software-3d.md].
- **Doom's colormaps.** d32xr keeps 33 tables of 256 bytes: 32 light levels, each mapping every colour to a darker version, and last the inverse map used while the player is invulnerable [D32XR, r_local.h `INVERSECOLORMAP`, r_main.c; content/files/colormap8]. A light level from 0 to 255 picks one of the 32: its byte offset is (255 − light) / 8 × 256. The drawer reads the texel, then reads the table at that offset. d32xr precomputes each wall's light as a straight-line function of the wall's scale, so per column it costs one multiply, a subtraction and a clamp. A wall whose ends have the same light skips even that. Floors use the same ramp driven by distance. Walls running exactly east-west get 8 less light and walls running exactly north-south 8 more, which makes corners readable [D32XR, r_local.h `HWLIGHT`, r_phase1.c, r_phase6.c, r_phase7.c].

d32xr also stores each table rotated and points into it 128 bytes from the start. The SH-2's byte load sign-extends, so texels 128 to 255 load as −128 to −1, and from a base 128 bytes in they reach the table's first 128 bytes. So the tables keep the entries for colours 128 to 255 first and those for 0 to 127 after them, where the non-negative texels reach. Every texel then lands on its own entry, and no instruction is needed to clear the sign. The low-resolution tables, whose entries are 2-byte pixel pairs, are rotated the same way and entered 256 bytes in [D32XR, r_data.c `R_InitColormaps`, marsdraw.c; content/files/colormap8, colormap_new].

The tables also never produce colour 0. The high-resolution drawers store single bytes, and a byte write of 0 to the frame buffer is ignored ([The normal and overwrite images](../32x/vdp.md#the-normal-and-overwrite-images)). No entry in the 8-bit tables of the source tree is 0; colour 0 itself maps to 8. The low-resolution tables do hold zeros, but their drawers store whole words, which write both bytes [D32XR, content/files/colormap8, colormap8_new, colormap_new; sh2_draw.s, sh2_drawlow.s].

## Doom's BSP renderer

A BSP tree divides the level by lines. Each node's line splits its part of the level in two, and the two halves are its children, down to small convex pieces of floor (subsectors) whose walls (segs) can be drawn in any order. Walking the tree with the viewer's side first visits every wall in front-to-back order.

### Walking the tree, and skipping what is hidden

d32xr walks the tree near side first. It visits the far side only if that side's bounding box might still be visible [D32XR, r_phase1.c `R_RenderBSPNode`, `R_CheckBBox`]:

- **Which corners matter.** The viewer is somewhere in a 3 × 3 grid of positions around the box: left of it, inside its span, or right, and the same for front and back. For each position, a table gives the two corners that form the box's outline as seen from there. Their angles from the viewer become screen columns. A viewer inside the box sees it.
- **Hidden already?** If every column between those two is already covered by a solid wall, nothing in that part of the tree can be seen, and the walk skips it.

**Bounding boxes in 16 bits.** Doom stores each child's box as four 16-bit coordinates. d32xr stores each side as a 4-bit count of sixteenths of the parent's box, moving inward from the parent's edge, so the whole box fits in one 16-bit word. The walk rebuilds each child's box from its parent's as it goes, starting at the root from a box around the whole level: the smallest and largest *x* and *y* of all its vertices, worked out when the level is loaded [D32XR, p_setup.c `worldbbox`; r_phase1.c]. The count is rounded so that the rebuilt box always contains the real one: the box can only be too large, which costs an occasional wasted visit but never hides something visible. Each node shrinks from eight 16-bit coordinates to two words [D32XR, p_setup.c `P_EncodeBBox`; r_phase1.c `R_DecodeBBox`].

### Occlusion with solid column ranges

The renderer keeps a sorted list of screen column ranges that solid walls already cover completely, with markers at both screen edges. A new wall is clipped against the list and split into the gaps it falls into. Each visible piece is queued for drawing. If the wall is solid (one-sided, or a closed door), its range is merged into the list. Each range is two 16-bit numbers in one longword, so inserting or removing one moves whole longwords. Once the list covers the whole screen, every bounding box test fails and the walk ends. Up to 32 ranges are kept [D32XR, r_phase1.c].

This is why a BSP renderer draws each screen column of solid wall once: front-to-back order plus the coverage list means hidden walls are never drawn at all.

### From angles to columns

A wall's ends are turned into angles from the viewer, clipped to the field of view, and then into screen columns through a table of 4,096 entries built when the view is set up: the focal length is half the screen width divided by the tangent of half the field of view, and each angle maps to the column where its tangent lands. A second table goes the other way, from column to angle [D32XR, r_data.c, r_phase1.c].

Neighbouring walls share corners, and working out an angle takes a division. d32xr remembers the last wall's two corners and their angles, and reuses them when the next wall shares one. At load time it sorts each subsector's walls so that walls sharing corners come one after another [D32XR, r_phase1.c `R_AddLine`; p_setup.c].

### Classifying each wall

Before any pixel is drawn, each visible wall gets a set of bits saying what it needs: which floor and ceiling areas to add, which of its upper, middle and lower textures to draw, whether it narrows the open space for walls behind it, and what shape it hides sprites with. Two-sided lines with identical sectors on both sides, nothing to draw and the same light are dropped: they exist only to trigger events [D32XR, r_phase1.c `R_WallEarlyPrep`].

## Walls

For each visible wall [D32XR, r_phase2.c, r_phase6.c]:

- **Scale.** The wall's scale (screen pixels per world unit) is worked out exactly at its two ends, from its distance and its angle to the view, and stepped by a constant amount from column to column between them. That is exact, not an approximation: the scale is focal length over depth, and for a flat wall 1 / depth changes in a straight line across the screen, which is why a wall's top and bottom edges are straight lines.
- **Texture column.** The texture column does not change in a straight line across the screen, so it is worked out for each screen column from that column's angle, and textures do not slide along walls. What is linear on screen is stepped; what is not is computed.
- **Down the column.** The texture step is 1 / scale, in 16.16 fixed point ([Fixed-point arithmetic](fixed-point.md)). Each column starts at the texel matching its top edge.
- **Open space.** For each screen column the renderer keeps the highest and lowest row still open, packed as top × 256 + bottom in one 16-bit word. Walls clip their columns to it, and two-sided walls narrow it for what lies behind.

**On the frame buffer.** Every pixel of a wall column is a separate store on a different line. Nothing combines them: no longword store spans two lines, and auto fill only runs along one. The gaps between stores do let the frame buffer's write buffer drain, so each store costs the minimum 3 clocks ([Moving data without paying twice](../patterns/bus.md#moving-data-without-paying-twice)), and with seven other instructions per pixel the loop has work to put in those gaps. In low-resolution mode each texel becomes one word store, two pixels for the price of one [D32XR, sh2_drawlow.s].

**Textures whose height is not a power of two.** The fast drawer wraps the texture by masking with height − 1, which only works for heights of 2, 4, 8 and so on. With any other height the mask keeps only some rows and repeats them out of order: for a texture 72 rows tall, the mask of 71 shows rows 0 to 7 again and again, then 64 to 71. So when d32xr sets up a texture for drawing, any height that is not a power of two gets a second drawer, which wraps by subtracting the height instead [D32XR, r_phase6.c, marsdraw.c, sh2_draw.s].

## Floors and ceilings

### Visplanes

As walls are drawn, the open space above and below them in each column is marked as part of a floor or ceiling area, a *visplane*: a set of columns, each with a top and bottom row, sharing one height, texture and light level. d32xr finds an existing visplane through a 32-bucket hash of height, texture and light. It reuses one only if that plane has nothing yet in the starting column. That one test is enough because the caller repeats it column by column: as a wall marks its columns, whenever the plane it holds already has a piece in the next column, it asks for another plane from that column on. So no visplane ever has two pieces in one column [D32XR, r_main.c `R_FindPlane`; r_phase2.c].

### From columns to rows

A visplane is stored by columns, but floors must be drawn by rows. d32xr converts by walking across the plane's columns and comparing each column's top and bottom with the previous one. A row that was open in the last column but not in this one ends a span, which is drawn from where it started to the previous column. A row that becomes open here records this column as its start. Marker values at both ends close every span. Each pixel of the plane is visited once, and the spans come out ready for the row drawer [D32XR, r_phase7.c `R_PlaneLoop`].

### Drawing a span

For each row [D32XR, r_phase7.c, sh2_draw.s]:

- **Distance** is the plane's height above or below the eye times a per-row table entry, worked out once when the view is set up.
- **The starting texel** comes from the viewer's position, the angle of the span's first column, and the distance, with a per-column correction for the angle.
- **The steps** across the row are constant, from the distance and the view angle.
- **Floor textures are 64 × 64.** The vertical texture position and its step are stored already multiplied by 64, so the drawer's texel index is two masked parts ORed together, with no multiply.

### The sky

The sky ignores distance. Its texture column depends only on the angle of the screen column, and wraps four times in a full turn. Vertically it uses a fixed step of about 1.11 texels per pixel. Each sky column is one call to the column drawer [D32XR, r_phase6.c].

## Making it fast enough

d32xr has several options for trading picture quality for speed:

- **Half the columns.** In low-resolution mode the view is rendered half as wide, and every drawer writes each texel to two pixels [D32XR, r_main.c].
- **Cheaper floors.** The default detail level draws floors at half horizontal resolution. The lowest, called "potato", fills each floor span with one colour: a fixed texel of the floor's texture, through the plane's light table, written two pixels per 16-bit store. Floor textures are then left out of the texture cache altogether [D32XR, r_main.c, r_phase7.c, marsdraw.c, r_phase9.c].
- **4-bit textures.** A texture can store two texels per byte, with its own table of its 16 colours at the same 33 levels (32 of light, plus the inverse map) at the end of its data. The drawer halves the texel index with a single shift, which leaves the low bit in the T flag to choose between the two halves of the byte. The nibbles are stored swapped to save an instruction. Such textures take half the ROM, and are expanded to 8 bits when copied into the texture cache in SDRAM [D32XR, sh2_draw4b.s, r_main.c, r_phase9.c]. See [Caches with a lifetime in pictures](memory.md#caches-with-a-lifetime-in-pictures).
- **Mipmaps**, smaller copies of textures for distant walls and floors, are supported but compiled out by default [D32XR, r_local.h, r_data.c].
- **Both SH-2s.** The renderer's stages are shared between the two CPUs ([Splitting work across three CPUs](../patterns/cpu-split.md#both-sh-2s-on-every-stage)).

One effect reads the frame buffer back. Doom's shimmering "spectre" takes the pixel one row above or below from the frame buffer, using a 64-entry table of ±1 rows already multiplied by the 320-byte row length, and darkens it through one of the light tables [D32XR, r_main.c, r_data.c, sh2_draw.s `I_DrawFuzzColumnA`]. That table ties it to the frame buffer's layout, and the read makes each of its pixels dearer than an ordinary one: a frame buffer read is the slowest access an SH-2 makes there, 7 to 14 clocks against 3 to 5 for a write ([Access timing per CPU](../32x/timing.md#the-figures)).

## In emulators

The raycaster's figures come from PicoDrive, and neither engine has been timed on a console for this book.

- **Frame buffer writes cost only their instructions** in upstream PicoDrive ([Access timing per CPU](../32x/timing.md#in-emulators)). The raycaster's two-by-two expand alone is 10,240 longword stores, 20,480 bus words, written back to back. On a console those cost 3 to 5 clocks a word, about 61,000 to 102,000 clocks a picture that the emulator does not charge: a sixth to a quarter of a frame, or 8 to 13% of the two frames a picture has at 30 a second.
- **Frame buffer reads** cost 7 to 14 clocks on a console and nothing extra in PicoDrive, so the spectre effect is cheaper there than on the hardware.
- **The divider answers at once** in PicoDrive ([Division unit](../sh2/divu.md#in-emulators)). The raycaster reads each quotient straight after starting the divide, so each of its four divides per column is up to 39 clocks dearer on a console. d32xr starts its divides early and reads them late, which saves time on a console and shows no gain in the emulator.
- **The raycaster's rate is the project's claim.** Its README gives 30 pictures a second; its own ROM test in PicoDrive only checks for at least 20 [NOUDAR-32X, README.md, tests/run_tests.py].

## What to take away

- Draw walls as columns and floors as rows: all the division happens once per column or row, never per pixel.
- Keep the per-pixel loop to a texel read, a light look-up and a store.
- For grid worlds, a raycaster at reduced resolution with one divide per column is enough, and far simpler than a BSP.
- Do lighting and fog with the palette: darker copies of colours, or tables of them.
- In a BSP renderer, walk front to back, keep a list of covered columns, and skip any subtree whose box falls entirely behind it.
- Offer quality settings that cut pixels: fewer columns, cheaper floors, smaller textures.

## Open questions

- How does Sega's own *Doom* for the 32X (1994) draw its world, and how does it split the work? Its ROM has not been read for this book.
- What frame rates does d32xr reach on a console at each detail level?
- Does the raycaster hold 30 pictures a second on a console, once its frame buffer writes and divides are charged?

## Sources

- [D32XR](../appendices/bibliography.md#d32xr): r_phase1.c, r_phase2.c, r_phase6.c, r_phase7.c, r_phase9.c, r_main.c, r_data.c, r_local.h, p_setup.c, marsdraw.c, marssave.c, sh2_draw.s, sh2_drawlow.s, sh2_draw4b.s; the colour tables in content/files
- [NOUDAR-32X](../appendices/bibliography.md#noudar-32x): src/render.c, src/fixed.h, src/main.c, README.md, tests/run_tests.py
- [S32X-SKILL](../appendices/bibliography.md#s32x-skill): software-3d.md, strategy-and-grid.md
