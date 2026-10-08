# Sprites

A sprite is a block of tiles, 1 to 4 tiles wide and 1 to 4 high, that the VDP draws at any pixel position on top of (or between) the planes. The VDP reads all sprites from one table in VRAM. They are drawn in an order set by a linked list inside that table. This chapter covers the table, the list, the limits per line, and the masking trick that comes out of those limits.

## The sprite table

Register 5 sets the table's address in VRAM: a multiple of `$200` in 32-column mode, or of `$400` in 40-column mode. The table holds 64 or 80 entries of 8 bytes each, 512 or 640 bytes [MD-SWM §2.10; see [Registers and access](vdp-registers.md)]. Each entry:

| Word | Bits 15-8 | Bits 7-0 |
|------|-----------|----------|
| 0 | `------yy` | `yyyyyyyy` |
| 1 | `----wwhh` | `-lllllll` |
| 2 | `pccvhnnn` | `nnnnnnnn` |
| 3 | `-------x` | `xxxxxxxx` |

| Field | Bits | Meaning |
|-------|------|---------|
| y | 10 (9 used normally) | Vertical position. The top of the screen is 128 |
| ww, hh | 2 + 2 | Width and height in tiles, minus 1: `00` = 1 tile, `11` = 4 |
| l | 7 | Link: number of the next sprite to draw; 0 ends the list |
| p | 1 | Priority over the planes |
| cc | 2 | Palette, 0-3 |
| v, h | 1 + 1 | Vertical and horizontal flip, of the whole sprite |
| n | 11 | First tile number |
| x | 9 | Horizontal position. The left edge of the screen is 128 |

Sources: [MD-SWM §2.10; GENVDP §15]. Sega notes that the unused bits (shown as `-`) are free for the program to use [MD-SWM §2.10]. The MD-SWM text copy draws the link field one bit to the left (bits 7-1); the scan has it in bits 6-0 [MD-SWM p.56]. GENVDP puts it in bits 6-0, and so does PicoDrive's renderer [PICODRIVE, pico/draw.c]; values up to 79 need exactly those seven bits.

### Coordinates

Positions are in a 512 × 512 space with the visible screen starting at (128, 128) [GENVDP §15]:

| Mode | x on screen | y on screen |
|------|-------------|-------------|
| 32 columns | 128-383 (`$80-$17F`) | |
| 40 columns | 128-447 (`$80-$1BF`) | |
| 28 rows | | 128-351 (`$80-$15F`) |
| 30 rows (PAL) | | 128-367 (`$80-$16F`) |
| Interlace mode 2 | | 256 upwards (`$100-$2BF` or `$2DF`), with a 10-bit y |

Source: [MD-SWM §2.10, display position]. The offset means a sprite can sit partly off the top or left edge without negative numbers. Aerobiz bakes it into its data: a sprite meant for screen position (x, y) is stored as (x + 128, y + 128) in ROM, and positions are then added as plain numbers [AB-DISASM, CmdUpdateSprites.asm].

### Which tiles a sprite uses

A sprite uses `width × height` tiles in a row in VRAM, starting at its tile number. They go **down first, then across**: tile 0 is the top left, tile 1 is under it, and the next column starts after the last tile of the first [MD-SWM §2.10, sprite pattern generator]. A 2 × 2 sprite at tile `n`:

```
n    n+2
n+1  n+3
```

This is the opposite of how most image tools cut a sheet into tiles, so a converter has to reorder them (see [Asset pipelines](../techniques/asset-pipelines.md)). Flipping a sprite flips the whole block, tile order included, so one set of tiles serves both facing directions.

In interlace mode 2 each tile is 8 × 16 pixels, so every height doubles [MD-SWM §2.10, sprite size].

## The link list

The VDP does not draw sprites in table order. It starts at sprite 0, draws it, then follows sprite 0's link to the next sprite, and so on, until it reaches a sprite whose link is 0 [MD-SWM §2.10, priority between sprites; GENVDP §15]:

- **The list sets which sprite is in front.** Sprite 0 is in front of everything, the next sprite in the list is behind it, and so on. That is the priority between sprites. Their priority bits only decide how they sort against the planes (see [Color, shadow/highlight and interlace](vdp-color.md)).
- **Sprites not in the list are not drawn**, whatever their positions.
- **The last sprite must have link 0.** Sega's manual says behaviour is not guaranteed otherwise, and that links must stay below the number of entries (64 or 80). GENVDP found that a loop does no lasting harm, because the VDP stops at the limits below anyway [GENVDP §15]. Still, end the list.

Two ways to use the list:

- **Keep it fixed and move unused sprites away.** Aerobiz links every entry to the next one (0 → 1 → 2 → … → 0), 64 or 80 depending on the screen width read from its copy of register 12. Its game code never touches a link: it only changes positions and tiles. Hiding a sprite means moving it to y = 0, far above the screen, as its blinking code does (below). The whole 512- or 640-byte table is then copied to VRAM by DMA in one go [AB-DISASM, InitSpriteLinks.asm, InitDisplayLayout.asm].
- **Rebuild it every frame.** Link only the sprites in use, sorted front to back, and end the list after the last one. The VDP then reads fewer entries, and front-to-back order is whatever order you link them in. This suits games where sprites need sorting by depth.

Either way, build the table in RAM and copy it by DMA during vertical blank. The table is only 640 bytes.

### Write the table where register 5 points

The VDP keeps its own copy of part of the sprite table: for each entry, the first four bytes (y, size and link). PicoDrive models this copy, refreshing it only when the CPU or a DMA writes VRAM inside the table's current address range. Pointing register 5 at a second table that was built somewhere else then gives the old y, size and link values combined with the new table's tile and x values <span class="tag emulator">emulator</span> [PICODRIVE, pico/videoport.c]. Double-buffering the sprite table by switching register 5 is therefore unsafe. Keep one table address and write the new contents there.

## Limits

The VDP gives up drawing sprites when it reaches any of these [MD-SWM §2.10, sprite's display capacity; GENVDP §15]:

| Limit | 32 columns | 40 columns |
|-------|-----------|------------|
| Sprites in the list | 64 | 80 |
| Sprites on one line | 16 | 20 |
| Sprite pixels on one line | 256 | 320 |

The per-line limits count sprites in list order, so the ones at the end of the list are the ones that disappear. Two consequences:

- **Wide sprites hit the pixel limit first.** Ten 32-pixel-wide sprites on one line use the whole 320-pixel budget in 40-column mode, so an eleventh is not drawn even though only ten of twenty sprites have been used [MD-SWM §2.10]. A sprite that is only partly within the budget is cut off.
- **Hide a sprite with y, not x.** A sprite moved off the left or right edge still occupies its lines, and still counts against both limits there [GENVDP §15]. Moving it above or below the screen (y below 128 or past the bottom) takes it off every visible line. Better still, leave it out of the list.

When the line limit is exceeded, the status register's SOVR bit is set. When two sprites' visible pixels overlap, the C bit is set. Both are described in [Registers and access](vdp-registers.md#the-status-register). Neither says which sprites were involved, so games do their own collision tests in software.

### Flicker

The standard answer to too many sprites on a line is to rotate the order of the list every frame. Each sprite then spends some frames near the front, and instead of always losing the same sprites the game flickers between them. Combined with the fixed-list method above, that means rotating which sprite is linked first.

Blinking on purpose is cheaper still. Aerobiz blinks a range of markers entirely in its vertical blank handler: every *n* frames it either restores their saved y positions or sets y = 0, then copies the table again. The game logic never sees it [AB-DISASM, DisplayUpdate.asm].

## Masking

A sprite with x = 0 is special. On the lines it covers, it hides every sprite after it in the list. Sprites before it in the list are still drawn. Only its height matters: its width, tiles, palette and priority have no effect [MD-SWM §2.10, display position; GENVDP §15]. Games use it to cut a sprite off at a window or status bar: put an x = 0 sprite early in the list, as tall as the area to clear.

GENVDP describes a second rule. Once the VDP has met a sprite with x = 1 in a frame, a sprite at x = 0 masks only on lines where a sprite at x = 1 also appears. GENVDP knew of one game that uses it and was not sure of the details [GENVDP §15]. Avoid x = 0 and x = 1 for ordinary sprites; nothing is visible there anyway.

## Moving sprites cheaply

Each entry is 8 bytes, two longwords, and the fields fall conveniently for the 68000. y is in the top word of the first long, and x is in the bottom word of the second. Aerobiz moves a whole group of sprites with two additions per sprite [AB-DISASM, CmdUpdateSprites.asm]:

```asm
; a0 = source sprites, a1 = destination, d1 = count - 1
; d3.l = dy << 16 (y offset in the high word), d2.w = dx
.loop:  move.l  (a0)+,d4
        add.l   d3,d4            ; y += dy; size and link untouched
        move.l  d4,(a1)+
        move.l  (a0)+,d4
        add.w   d2,d4            ; x += dx; attributes untouched
        move.l  d4,(a1)+
        dbra    d1,.loop
```

Adding to the long's high word changes y without disturbing the size and link word below it, as long as nothing overflows. Adding a word to the second long changes only x.

Aerobiz's animation code shows two more useful habits. Its flight-path markers do not move by adding a speed every frame. Instead it recomputes each position from the start point, the end point and a step count as a weighted average. Rounding errors therefore never build up, and no fixed-point state is needed [AB-DISASM, AnimateFlightPaths.asm, WeightedAverage.asm]. Its take-off and landing animations get acceleration and easing from integer division of the distance travelled (a step of distance ÷ 20 + 2, for example) instead of a velocity variable [AB-DISASM, DiagonalWipe.asm]. Both are covered in more depth in [Fixed-point arithmetic](../techniques/fixed-point.md).

## Open questions

- Confirm the sprite cache on a console: build a second table, switch register 5 to it, and see which fields take effect.
- Does the status register's SOVR bit fire for sprites outside the visible area? (When it clears: on a status read, in every emulator checked; see [The status register](vdp-registers.md#the-status-register).)
- Test GENVDP's second masking rule (x = 1) on a console.

## Sources

- [MD-SWM](../appendices/bibliography.md#md-swm): §2.10 sprites: attribute table, display position, size, pattern order, priority between sprites, display capacity
- [GENVDP](../appendices/bibliography.md#genvdp): §15 sprites: table format, linking, coordinates, masking, limits
- [PICODRIVE](../appendices/bibliography.md#picodrive): `pico/videoport.c` (sprite table cache), `pico/draw.c` (link field)
- [AB-DISASM](../appendices/bibliography.md#ab-disasm): InitSpriteLinks, InitDisplayLayout, CmdUpdateSprites, DisplayUpdate, AnimateFlightPaths, WeightedAverage, DiagonalWipe
