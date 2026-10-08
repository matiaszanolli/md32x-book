# First-person engines: raycasting and BSP

There are two ways to draw a first-person world on a 32X, and both appear in the book's sources:

- **A grid raycaster**: the world is a grid of cells, and one ray per screen column finds the nearest wall. It is simple, and fast enough for a dungeon crawler at 30 pictures a second on one SH-2.
- **Doom's BSP renderer**: the world is any arrangement of walls at any angle and floors at any height, sorted into a binary space partition. It is far more general and far more work. d32xr, a Doom engine for the 32X, runs it across both SH-2s.

Most of this chapter follows d32xr's source, read at the commit given in the bibliography [D32XR]. The raycaster comes from a homebrew game described in S32X-SKILL, measured in PicoDrive <span class="tag emulator">emulator</span>. Neither is a retail game; Sega's own *Doom* for the 32X is not among the book's sources.

## What every first-person renderer does

Both engines rest on one observation. Walls are vertical, so every pixel in one screen column of a wall is at the same distance from the viewer. Floors and ceilings are flat, so every pixel in one screen row of a floor is at the same distance. So:

- **Walls are drawn as columns.** One divide per column gives the scale; then the texture is stepped down the column at a constant rate, with no division per pixel.
- **Floors and ceilings are drawn as rows (spans).** One distance per row, then constant steps across it.

All the expensive maths happens once per column or once per row. What is left per pixel is a texture read, a light look-up and a store. d32xr's wall-column loop does two pixels in 16 SH-2 instructions: for each pixel, it reads a texel, looks it up in the light table, stores it, steps the texture position, and steps the frame buffer pointer down one line [D32XR, sh2_draw.s `I_DrawColumnA`]. A 320 × 224 screen is 71,680 pixels, so even eight instructions a pixel is more than half a million per picture. That is why the tricks below are all about doing fewer pixels or cheaper ones.

## A grid raycaster

A homebrew dungeon crawler shows the simplest design that works, at 30 pictures a second on one SH-2 <span class="tag emulator">emulator</span> [S32X-SKILL, software-3d.md]:

- **One ray per column.** Each ray steps through the map grid cell by cell (a DDA) until it meets a wall. One division, ray length to perpendicular distance, gives the wall's height on screen. The SH-2's division unit does it in about 39 clocks, which is fine once per column ([Division unit](../sh2/divu.md)).
- **Cast at a quarter of the pixels.** The game casts into a 128 × 80 buffer in SDRAM, then expands it two by two into a 256 × 160 view. Two source pixels *a*, *b* become one longword *aabb*, written to two rows, so the expand is aligned 32-bit stores of four pixels each. The project calls casting at quarter resolution its single biggest saving.
- **A depth per column.** Each column's wall distance is kept, so that sprites can be clipped against the walls later without a full-screen depth buffer.
- **Floors and ceilings per cell**, with animated textures such as lava, and a scrolling sky wherever a cell has no ceiling.
- **Sprites in two passes.** See-through scenery such as bars and arches is collected during the ray walk. Monsters, items and effects are sorted by depth and drawn as flat sprites facing the viewer, each column clipped against that column's wall depth.
- **A smooth camera over grid moves.** The game moves one cell or turns 90° per step, but the camera slides an eighth of a cell, or 1/32 of a turn, per frame. A turn-based game then scrolls like a free-moving one [S32X-SKILL, strategy-and-grid.md].

## Lighting and fog through the palette

Darkening a pixel by arithmetic costs work per pixel. With 256 palette colours there is a cheaper way: put darker copies of the colours in the palette, and choose which copy a pixel uses.

- **Shade banks.** The crawler uses a 64-colour base palette repeated as four banks of decreasing brightness, filling all 256 entries. A pixel's value is its bank times 64 plus its colour, with the bank chosen per column or per sprite from its distance. Fog then costs nothing per pixel <span class="tag emulator">emulator</span> [S32X-SKILL, software-3d.md].
- **Shade tables.** When the palette is organised as brightness ramps of 16 steps per hue, a table indexed by depth and colour gives the darker colour; the drawer reads through it <span class="tag emulator">emulator</span> [S32X-SKILL, software-3d.md].
- **Doom's colormaps.** Doom keeps 32 tables of 256 bytes, each mapping every colour to a darker version. A light level from 0 to 255 picks a table: its byte offset is (255 − light) / 8 × 256. The drawer reads the texel, then reads the table at that offset. d32xr precomputes each wall's light as a straight-line function of the wall's scale, so per column it costs one multiply, a subtraction and a clamp. A wall whose ends have the same light skips even that. Floors use the same ramp driven by distance. Walls running exactly east-west get 8 less light and walls running exactly north-south 8 more, which makes corners readable [D32XR, r_local.h `HWLIGHT`, r_phase1.c, r_phase6.c, r_phase7.c].

d32xr also points its colour tables 128 bytes into their data. The SH-2's byte load sign-extends, so a texel above 127 loads as a negative number; with the table base moved up by 128, a signed index still lands on the right entry, and no instruction is needed to clear the sign [D32XR, r_data.c, marsdraw.c].

## Doom's BSP renderer

A BSP tree divides the level by lines. Each node's line splits its part of the level in two, and the two halves are its children, down to small convex pieces of floor (subsectors) whose walls (segs) can be drawn in any order. Walking the tree with the viewer's side first visits every wall in front-to-back order.

### Walking the tree, and skipping what is hidden

d32xr walks the tree near side first. It visits the far side only if that side's bounding box might still be visible [D32XR, r_phase1.c `R_RenderBSPNode`, `R_CheckBBox`]:

- **Which corners matter.** The viewer is somewhere in a 3 × 3 grid of positions around the box: left of it, inside its span, or right, and the same for front and back. For each position, a table gives the two corners that form the box's outline as seen from there. Their angles from the viewer become screen columns. A viewer inside the box sees it.
- **Hidden already?** If every column between those two is already covered by a solid wall, nothing in that part of the tree can be seen, and the walk skips it.

**Bounding boxes in 16 bits.** Doom stores each child's box as four 16-bit coordinates. d32xr stores each side as a 4-bit count of sixteenths of the parent's box, moving inward from the parent's edge, so the whole box fits in one 16-bit word. The walk rebuilds each child's box from its parent's as it goes. The count is rounded so that the rebuilt box always contains the real one: the box can only be too large, which costs an occasional wasted visit but never hides something visible. Each node shrinks from eight 16-bit coordinates to two words [D32XR, p_setup.c `P_EncodeBBox`; r_phase1.c `R_DecodeBBox`].

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

- **Scale.** The wall's scale (screen pixels per world unit) is worked out at its two ends, from its distance and its angle to the view. Across the wall, the scale is interpolated in a straight line, which is not exactly correct in perspective but is what PC Doom did too.
- **Texture column.** The texture column for each screen column is worked out exactly, from the angle of that column, so textures do not slide along walls.
- **Down the column.** The texture step is 1 / scale, in 16.16 fixed point ([Fixed-point arithmetic](fixed-point.md)). Each column starts at the texel matching its top edge.
- **Open space.** For each screen column the renderer keeps the highest and lowest row still open, packed as top × 256 + bottom in one 16-bit word. Walls clip their columns to it, and two-sided walls narrow it for what lies behind.

**Textures whose height is not a power of two.** The fast drawer wraps the texture by masking with height − 1, which only works for heights of 2, 4, 8 and so on. With other heights the mask reads past the texture into whatever follows, which in Doom shows as speckled garbage called "tutti frutti". d32xr has a second drawer for such textures, which wraps by subtracting the height instead [D32XR, marsdraw.c, sh2_draw.s].

## Floors and ceilings

### Visplanes

As walls are drawn, the open space above and below them in each column is marked as part of a floor or ceiling area, a *visplane*: a set of columns, each with a top and bottom row, sharing one height, texture and light level. d32xr finds an existing visplane through a 32-bucket hash of height, texture and light. It reuses one only if that plane has nothing yet in the starting column, so that no visplane ever has two pieces in one column [D32XR, r_main.c `R_FindPlane`].

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
- **4-bit textures.** A texture can store two texels per byte, with its own table of 16 colours at 33 light levels at the end of its data. The drawer halves the texel index with a single shift, which leaves the low bit in the T flag to choose between the two halves of the byte. The nibbles are stored swapped to save an instruction. Such textures take half the ROM, and are expanded to 8 bits when copied into the texture cache in SDRAM [D32XR, sh2_draw4b.s, r_main.c, r_phase9.c]. See [Caches with a lifetime in pictures](memory.md#caches-with-a-lifetime-in-pictures).
- **Mipmaps**, smaller copies of textures for distant walls and floors, are supported but compiled out by default [D32XR, r_local.h, r_data.c].
- **Both SH-2s.** The renderer's stages are shared between the two CPUs ([Splitting work across three CPUs](../patterns/cpu-split.md#both-sh-2s-on-every-stage)).

One effect shows why the frame buffer layout matters: Doom's shimmering "spectre" reads the pixel one row above or below from the frame buffer, from a 64-entry table of ±1 rows already multiplied by the 320-byte row length, and darkens it through one of the light tables [D32XR, r_main.c, r_data.c, sh2_draw.s].

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

## Sources

- [D32XR](../appendices/bibliography.md#d32xr): r_phase1.c, r_phase2.c, r_phase6.c, r_phase7.c, r_phase9.c, r_main.c, r_data.c, r_local.h, p_setup.c, marsdraw.c, sh2_draw.s, sh2_draw4b.s
- [S32X-SKILL](../appendices/bibliography.md#s32x-skill): software-3d.md, strategy-and-grid.md
