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

Source: [MD-SWM §2.10, display position]. The offset means a sprite can sit partly off the top or left edge without negative numbers. Aerobiz Supersonic, the Mega Drive game ("Aerobiz" in the rest of this chapter), bakes it into its data: a sprite meant for screen position (x, y) is stored as (x + 128, y + 128) in ROM, and positions are then added as plain numbers [AB-DISASM, CmdUpdateSprites.asm].

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

Either way, build the table in RAM and copy it by DMA during vertical blank, because the VDP reads the table while it draws the picture and a copy made then can show a half-updated list. The table is only 640 bytes.

### Write the table where register 5 points

The VDP keeps its own copy of part of the sprite table: for each entry, the first four bytes (y, size and link). Console reports agree on how it behaves. The author of GENVDP described it in 2010: a write to VRAM, by the CPU or by DMA, that lands inside the table's address range is also stored in the copy; the VDP uses the copy for each sprite's y and size when it picks the sprites for a line, and reads x and the attribute word from VRAM at whatever address register 5 holds; changing register 5 neither clears nor reloads the copy. He lists y and size only; Sega's patent, as another emulator author read it, also holds the link, and the emulators keep all four bytes [GENDEV-SAT].

A developer's own test on a console found that after he switched register 5 between four prepared tables, the new tables' x positions took effect and their y positions did not, until he wrote to VRAM [GENDEV-SAT]. Genesis Plus GX, ares and PicoDrive all model the copy the same way <span class="tag emulator">emulator</span> [GPGX, core/vdp_ctrl.c, vdp_render.c `parse_satb_m5`; ARES, ares/md/vdp/sprite.cpp `Sprite::write`; PICODRIVE, pico/videoport.c]. None of this was tested on a console for this book.

Pointing register 5 at a second table that was built somewhere else therefore gives the old y, size and link values combined with the new table's tile and x values. Double-buffering the sprite table by switching register 5 is unsafe. Keep one table address and write the new contents there.

## Limits

The VDP gives up drawing sprites when it reaches any of these [MD-SWM §2.10, sprite's display capacity; GENVDP §15]:

| Limit | 32 columns | 40 columns |
|-------|-----------|------------|
| Sprites in the list | 64 | 80 |
| Sprites on one line | 16 | 20 |
| Sprite pixels on one line | 256 | 320 |

The per-line limits count sprites in list order, so the ones at the end of the list are the ones that disappear. Two consequences:

- **Wide sprites hit the pixel limit first.** Ten 32-pixel-wide sprites on one line use the whole 320-pixel budget in 40-column mode, so an eleventh is not drawn even though only ten of twenty sprites have been used [MD-SWM §2.10]. A sprite that is only partly within the budget is cut off.
- **Hide a sprite with y, not x.** A sprite moved off the left or right edge still occupies its lines, and still counts against both limits there [GENVDP §15]. Moving it clear of the screen takes it off every visible line, but the condition is on the whole sprite: it must end above the first line (y + height at or below 128; a sprite four tiles tall at y = 100 covers lines 100 to 131 and still shows and still counts) or start below the last. Aerobiz's y = 0 is safe for every size, which is why zero is the usual choice. Better still, leave it out of the list.

When the line limit is exceeded, the status register's SOVR bit is set. When two sprites' visible pixels overlap, the C bit is set. Both are described in [Registers and access](vdp-registers.md#the-status-register). Neither says which sprites were involved, so games do their own collision tests in software.

### Flicker

The standard answer to too many sprites on a line is to rotate the order of the list every frame. Each sprite then spends some frames near the front, and instead of always losing the same sprites the game flickers between them. The VDP always starts at table entry 0, and no register changes that, so with the fixed list above the links cannot rotate: what rotates is which object is written into which entry, with a different starting object each frame. With the rebuilt list it is the order in which the sprites are linked.

Blinking on purpose is cheaper still. Aerobiz blinks a range of markers entirely in its vertical blank handler: every *n* frames it either restores their saved y positions or sets y = 0, then copies the table again. The game logic never sees it [AB-DISASM, DisplayUpdate.asm].

## Masking

A sprite with x = 0 is special: on the lines it covers, it can hide the sprites after it in the list. Sprites before it are still drawn. Sega's manual says only that an x of 0 is a special case to take care with [MD-SWM §2.10, display position]. GENVDP gives the simple rule: every sprite after it is hidden on the lines it covers, and only its height matters [GENVDP §15]. That rule is incomplete <span class="tag disputed">disputed</span> ([discrepancy 50](../appendices/discrepancies.md)). Console tests by the author of the Exodus emulator, posted in March 2009 and confirmed by the author of Fusion, found three conditions [GENDEV-MASK]:

- **The mask only works behind a sprite that is not at x = 0.** On a given line, at least one sprite earlier in the list must have a non-zero x. A mask that is the first sprite on its line is ignored, and so are two masks in a row at the start of the line.
- **Unless the line before overflowed.** If the previous line ran out of its sprite pixel budget, a mask is effective on this line even as the first sprite, and it stays effective on each following line as long as the line before it overflowed too.
- **A mask still costs its width.** It counts against the line's sprite and pixel limits like any sprite, and it does not stop the VDP reading the rest of the list: it only stops the pixels of the sprites after it from being shown. A line where every sprite is masked can still overflow.

So the way to cut a sprite off at a window or status bar is a pair: first a sprite with any x other than 0 (x = 1 puts it off the left edge, so nothing shows, though it uses 8 to 32 pixels of the line's budget), then the x = 0 sprite, both tall enough to cover the lines to clear. The tests name Galaxy Force II as the game that relies on this pair, and Mickey Mania as the one that relies on the second and third conditions: its lines begin with several masks, which are ignored but still use up the pixel budget [GENDEV-MASK]. GENVDP's second rule, that a sprite at x = 1 switches the VDP into another masking mode for the rest of the frame, is a misreading of that pair: the tests found no mode switch, and any non-zero x does the same [GENDEV-MASK]. Genesis Plus GX and ares implement the first two conditions <span class="tag emulator">emulator</span> [GPGX, core/vdp_render.c `render_obj_m5`; ARES, ares/md/vdp/sprite.cpp `patternFetch`]. None of this was tested on a console for this book. Avoid x = 0 for ordinary sprites; nothing is visible there anyway.

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

Adding to the long's high word changes y without touching the size and link word below it, whatever the values: a carry out of the high word is dropped, so an out-of-range y only wraps. Adding a word to the second long changes only x, and a carry out of that word is dropped the same way.

Aerobiz's animation code shows two more useful habits: its flight-path markers are recomputed from their end points each frame, and its screen wipe eases by dividing the distance covered, with no velocity variable. [Fixed-point arithmetic](../techniques/fixed-point.md#moving-things-without-a-velocity) explains both.

## Open questions

- Confirm the sprite cache on a console for this book: build a second table, switch register 5 to it, and see which fields take effect. A developer's console test and the VDP documentation's author already say y and size stay and x and the attributes follow [GENDEV-SAT].
- Does the status register's SOVR bit fire for sprites outside the visible area? (When it clears: on a status read in Genesis Plus GX, ares and BlastEm, and in the console reports; MAME clears C at the start of each frame and never sets SOVR. See [The status register](vdp-registers.md#the-status-register).)
- Does an overflow of the sprite count on the previous line, not only of the pixel budget, also make a mask effective on the next line? The author of the console tests had not confirmed it [GENDEV-MASK].
- Run the masking conditions on a console for this book: a mask first on its line, behind a dummy sprite, and after an overflowing line.

## Sources

- [MD-SWM](../appendices/bibliography.md#md-swm): §2.10 sprites: attribute table, display position, size, pattern order, priority between sprites, display capacity
- [GENVDP](../appendices/bibliography.md#genvdp): §15 sprites: table format, linking, coordinates, masking, limits
- [GENDEV-SAT](../appendices/bibliography.md#gendev-sat): the sprite table's internal copy, tested on a console
- [GENDEV-MASK](../appendices/bibliography.md#gendev-mask): console tests of sprite masking
- [GPGX](../appendices/bibliography.md#gpgx): `core/vdp_render.c` (`render_obj_m5`, `parse_satb_m5`), `core/vdp_ctrl.c` (sprite table copy)
- [ARES](../appendices/bibliography.md#ares): `ares/md/vdp/sprite.cpp`
- [PICODRIVE](../appendices/bibliography.md#picodrive): `pico/videoport.c` (sprite table cache), `pico/draw.c` (link field)
- [AB-DISASM](../appendices/bibliography.md#ab-disasm): InitSpriteLinks, InitDisplayLayout, CmdUpdateSprites, DisplayUpdate, AnimateFlightPaths, WeightedAverage, DiagonalWipe
