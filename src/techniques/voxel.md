# Voxel landscapes

A voxel landscape is a height map drawn in perspective. The ground is divided into square cells, every cell has its own height and colour, and the view looks down across them as hills scroll towards the viewer. It is not a polygon mesh. Each cell is drawn as a block of colour sized by its distance. Games like *Comanche* (1992) made the style famous on PCs.

No retail 32X game read for this book uses it. The one source is a homebrew port of a voxel shoot-'em-up, `zepton32x`, documented in S32X-SKILL. Its value here is less the technique than its measurement: the textbook method lost on the 32X <span class="tag emulator">emulator</span> [S32X-SKILL, voxel-landscape.md].

## The world

- **A grid of cells**, here 32 columns by 28 depth slices. The nearest slice is a fixed distance ahead of the camera.
- **Heights computed, not stored.** Each cell's height is a sum of a few sine and cosine waves of different frequencies, plus shaped features (a river valley, a plateau, a volcano), rounded down to multiples of a step for the blocky look. The colour comes from the height: water, sand, grass, rock, snow.
- **Moving forward** is a 16.16 fixed-point scroll value. Its whole part picks which world row each slice shows; its fraction moves every slice a little nearer, so the motion is smooth between rows ([Fixed-point arithmetic](fixed-point.md)).
- **Choose the scale so the near slice fills the screen.** A near cell should come out about 10 pixels wide. With a cell width of 1 and a focal length of 120, that puts the near plane about 12 units ahead. A near plane at 1 projects everything thousands of pixels off screen, and the result is a black frame.

Watch the fixed-point products. The fraction of a slice times the slice depth overflows 32 bits in this game's units, so it is done as a 64-bit multiply shifted back down.

## Projecting: one divide per slice

Every cell in a depth slice is at the same distance, so they all share the same scale factor, focal length / distance. The game computes that reciprocal once per slice and places every cell in the slice with multiplies: about 28 divides per frame instead of three per cell. It keeps the slower, divide-per-point version as a reference, and a test checks that the fast version matches it within a pixel. This is the same saving as in [first-person renderers](first-person.md#what-every-first-person-renderer-does): find what is constant across a row or column, and divide once for it.

## Two ways to draw it

### Method A: blocks, far to near

Draw each slice from the farthest to the nearest, and for each cell fill a rectangle: one more pixel wide than the cell's projected size, twice its size plus two pixels tall, its top at the cell's projected height. Nearer cells paint over farther ones. Cells larger than a pixel get a one-pixel white top edge, which reads as light catching the ridge.

- **Height samples:** one per cell, about 900 a frame.
- **Cost:** overdraw, since many pixels are painted more than once. And the blocks do not cover the whole screen, so every frame starts with a full clear. The game suggests giving the clear to the Slave.
- **Block height** is the trade: three times the size looks solid but costs too much filling; twice is the balance.

### Method B: one ray per screen column

This is the classic *Comanche* method. For each screen column (two pixels wide here), step from near to far, keeping the highest row drawn so far in that column (a "y-buffer"). At each step, work out which part of the world the column passes through, sample the height there, and project it. If the terrain there is higher on screen than anything drawn so far, fill the column from that height down to the previous top, and record the new top.

- **No overdraw:** every pixel is painted once. Only the sky above the horizon needs clearing.
- **Height samples:** one per column per slice, 160 × 28, about 4,480 a frame.

### Which won

Method B paints far fewer pixels, so it looks like the faster one. Measured in PicoDrive, it ran at about 8 frames per second and Method A at about 19 <span class="tag emulator">emulator</span> [S32X-SKILL, voxel-landscape.md, optimization.md]. Each height sample costs two sines and a cosine, and B takes five times as many samples, so it became limited by computation rather than by pixels. The game shipped with Method A.

The project names the change that would turn it round, though it did not ship it: compute the frame's height grid once, about 900 samples, into an array, and have the ray steps read from the array. B would then be limited only by pixels, where it is strongest.

The lesson is the one in [Getting the frame time down](../patterns/60fps.md#getting-the-frame-time-down): find out whether a frame is limited by computation or by filling before choosing an algorithm. A rewrite that was built is not one that should ship until it measures faster.

Two 32X features suit Method A's solid-colour blocks, though the game does not use them. Every row of a block is a run of one value, which is what the VDP's auto fill writes while the CPU does other work; Star Wars Arcade draws its polygons that way ([Software 3D](software-3d.md#star-wars-arcade-polygons-as-auto-fills)). And the sky could be left to the Mega Drive layer behind a 32X field of one colour, as Mortal Kombat II does with its arenas ([Using both video chips at once](../patterns/layering.md)).

## Things that fly into the screen

The game's ships and shots do no 3D maths at all. Everything moves in screen space along a progress value from 0 to 1 <span class="tag emulator">emulator</span> [S32X-SKILL, voxel-landscape.md]:

- **Shots** travel from the player's ship towards the aiming reticle, at the point a fraction *p* of the way, growing smaller as *p* rises. A homing missile moves its target an eighth of the way towards the reticle's current position every frame.
- **Enemies** do the reverse. They appear at the horizon, tiny and central, and as *p* grows they move out to their lane and down towards the player, growing in proportion to *p*.
- **Locking on and hitting** are overlap tests between rectangles on the screen.

This keeps the game rules free of drawing and hardware, so they are tested on a PC: spawn, approach, lock, hit, kill, and an enemy reaching the player.

## What to take away

- A voxel landscape is a height map drawn as blocks or columns of colour, sized by distance.
- Divide once per depth slice, not once per point.
- Drawing by blocks paints pixels more than once; casting per column paints each once but samples the height map far more.
- Measure which limit your frame hits before choosing. Precomputing the height grid once per frame removes the column method's extra cost.
- Things flying into the screen can live entirely in screen space, with a progress value instead of 3D positions.

## Open questions

- Does the column method with a precomputed height grid beat the block method, as the project expects?

## Sources

- [S32X-SKILL](../appendices/bibliography.md#s32x-skill): voxel-landscape.md, optimization.md
