# Planes and scrolling

The VDP's backgrounds are two grids of tiles, plane A and plane B, plus the window, a fixed grid that replaces plane A in part of the screen. Each grid is a name table in VRAM, one 16-bit entry per tile position. Each plane can be scrolled horizontally as a whole, per row of tiles or per line, and vertically as a whole or per two-tile column. This chapter covers the tile format, name tables, plane sizes, both kinds of scrolling and the window, with their known faults.

## Tiles

A tile (Sega says "pattern" or "cell") is 8 × 8 pixels at 4 bits per pixel: 32 bytes, 4 bytes per row, top row first. In each byte the high nibble is the left pixel. Pixel value 0 is transparent; values 1-15 pick a colour from the palette chosen by the name table entry or sprite [MD-SWM §2.8, pattern generator; GENVDP §12].

Tile *n* lives at VRAM address *n* × 32. Tiles can go anywhere in VRAM that the tables do not use, including unused parts of a table [GENVDP §12]. In interlace mode 2 a tile is 8 × 16 pixels and 64 bytes, and bit 0 of the tile number is ignored [MD-SWM §2.8; GENVDP §13]. See [Color, shadow/highlight and interlace](vdp-color.md).

## Name table entries

Planes A and B and the window all use the same entry format [MD-SWM §2.8, scroll pattern name; GENVDP §13]:

| Bit | 15 | 14-13 | 12 | 11 | 10-0 |
|-----|----|-------|----|----|------|
| Field | Priority | Palette | Vertical flip | Horizontal flip | Tile number |

- **Priority** lifts the tile above low-priority sprites and the other plane's low-priority tiles. In shadow/highlight mode it also decides brightness. See [Color, shadow/highlight and interlace](vdp-color.md#priority).
- **Palette** (0-3) picks one of the four 16-colour palettes in CRAM.
- **The flips** mirror the tile; the same tile can serve all four orientations.
- **Tile number** (0-2047) is the VRAM address divided by 32.

In hex, an entry is `$8000` for priority + `palette × $2000` + `$1000` for a vertical flip + `$800` for a horizontal flip + the tile number.

## Plane size and layout

Register 16 sets one size for both planes. The allowed sizes, in tiles wide × high, are 32 × 32, 64 × 32, 128 × 32, 32 × 64, 64 × 64 and 32 × 128. A name table never exceeds 8 KB [MD-SWM §2.8, scrolling screen size; GENVDP §13]. Entries are stored row by row:

```
address of tile (x, y) = base + (y × width + x) × 2
```

So one row is 64, 128 or 256 bytes (`$40`, `$80`, `$100`) for widths of 32, 64 or 128 [MD-SWM §2.8]. Both planes wrap in both directions: scrolling past the right edge shows the left edge again.

The visible screen (40 × 28 tiles at most) is smaller than every plane, so part of each plane is always off screen. That spare part is where a scrolling game writes the next row or column before it comes into view. The [streaming](../patterns/streaming.md) chapter shows how.

Some games also use off-screen plane rows as plain storage, and that becomes a trap when the plane size changes. Aerobiz Supersonic keeps data in plane rows below the 28 that are shown, at fixed VRAM addresses. When the Aerobiz Ultimate port widened the planes from 32 to 64 tiles, the row stride doubled and those rows landed inside the visible area. A trace of VRAM writes found one DMA writing 192 bytes to `$EA80` at a fixed address [AU-NOTES, PORT_ARCHITECTURE.md] <span class="tag emulator">emulator</span>. Before changing register 16 in someone else's game, find every absolute address that points into a name table.

## Horizontal scrolling

Register 11 bits 1-0 choose the mode for both planes [MD-SWM §2.8, horizontal scrolling; GENVDP §13]:

| HSCR, LSCR | Mode | Table entries read |
|------------|------|--------------------|
| `00` | Whole plane | Line 0's entry only |
| `10` | Per tile row | The entry for the first line of each 8-line row |
| `11` | Per line | Every line's entry |
| `01` | Not allowed | GENVDP: the first 8 lines' entries, repeated every 8 lines |

The scroll values live in VRAM, in the horizontal scroll table set by register 13. Each line has two words, plane A then plane B, so line *n*'s values are at `base + n × 4` and `base + n × 4 + 2`. A full table is 896 bytes for 224 lines (960 for 240) [MD-SWM §2.8]. In the per-row mode only every eighth line's pair is read, but the table keeps the same layout, so the entries are 32 bytes apart.

**In interlace mode 2 the table does not grow.** The picture has 448 lines, but Sega's layout of the table stops at offset `$3FE`, 256 line pairs in 1 KB, with nothing added for this mode [MD-TO, H scroll data table]. All four emulators read for this book pick the entry by the line within the current field, 0-223, so lines 2*n* and 2*n* + 1 of the 448-line picture, drawn in different fields, share entry *n*. Per-line horizontal scrolling then has 224 steps, each two picture lines tall <span class="tag emulator">emulator</span> [GPGX, core/vdp_render.c; BLASTEM, vdp.c; PICODRIVE, pico/draw.c; MAME, src/devices/video/315_5313.cpp].

Each value is 10 bits, 0-1023, and wraps around the plane's width. A larger value moves the plane to the **right** on screen, so to scroll the view right by *x* pixels, write −*x*. Bits 15-10 are ignored, and Sega notes the program may use them [MD-SWM §2.8; GENVDP §13].

Per-line scrolling is the basis of most raster effects: waves, rotating towers, road perspective, parallax bands. Changing a whole table costs at most 896 bytes, a fraction of one vertical blank's DMA.

The per-row mode is cheaper when bands of 8 lines are enough. Aerobiz uses it to move just the map part of the screen [AB-DISASM, PackScrollDeltaToVRAM.asm, AnimateScrollEffect.asm, AnimateScrollWipe.asm]:

- It sets register 11 to `$02`, clears a table in RAM, writes the scroll value only into the 22 rows that hold the map, and copies the table to VRAM by DMA. The status rows above and below stay still with no window plane needed.
- Its "spin" of the world map speeds up from 1 to 16 pixels per frame, cruises, slows down again, and wraps at 256 pixels.
- Its screen shake alternates the offset's sign with a shrinking size: ±16, ±16, ±15 … ±1, holding each step for 5 frames.

## Vertical scrolling

Register 11 bit 2 chooses whole-plane or per-column vertical scrolling. The values live in VSRAM, again as A/B pairs: entries 0 and 1 serve the whole plane, or the first two-tile column, then each next pair serves the next 16-pixel column. 40 words cover 20 columns, 320 pixels [MD-SWM §2.8, V scroll].

A value is 10 bits (11 in interlace mode 2) and wraps around the plane's height. A larger value moves the plane **up** on screen [MD-SWM §2.8; MD-TO, V scroll]. In interlace mode 2 it counts lines of the 448-line picture: the emulators add it to twice the field line, which is why it needs the extra bit. Genesis Plus GX and BlastEm also add 1 in the odd field; PicoDrive does not at this point. A value of 2 moves the plane up by one line of each field <span class="tag emulator">emulator</span> [GPGX, core/vdp_render.c; BLASTEM, vdp.c; PICODRIVE, pico/draw.c].

VSRAM is inside the VDP, so it can be changed in the middle of a frame from a line interrupt. Sega's manual notes that the VDP reads what it needs for the next line within about 36 cycles of the line interrupt [MD-SWM §2.3]. Aerobiz uses this for a stretch effect: on each line, its line interrupt writes "source row for this line minus the line number" into both planes' VSRAM entries, which lets a table of row numbers squash, stretch or flip the picture [AB-DISASM, VInt_Handler3.asm; see [Timing](vdp-timing.md#organising-the-frame)].

### The left column fault

Per-column vertical scrolling has a documented fault. If the plane's horizontal scroll is not a multiple of 16, the screen shows a partial column at the left edge, and covering it would need a 21st VSRAM pair, which does not exist. Up to 15 pixels at the left of the screen then cannot be scrolled vertically as intended <span class="tag manual">manual</span> [MD-SDM §5.4]. Sega's manual does not say what appears instead.

What does appear depends on the console, and the emulators disagree <span class="tag disputed">disputed</span> ([discrepancy 40](../appendices/discrepancies.md)). The partial column takes a single vertical scroll value per plane, and the candidates are:

| Width | Older consoles (40 words of VSRAM) | MD2 VA4 and later (64 words of VSRAM) |
|-------|------------------------------------|---------------------------------------|
| H40 | VSRAM word 38 AND word 39 (column 19's plane A and plane B values, combined bit by bit), the same value for both planes. Some consoles may show 0, or an unstable AND, instead | Each plane's own column 0 value |
| H32 | 0: the column is not scrolled | Not reported |

The older-console row comes from Genesis Plus GX, whose author checked it on a PAL Mega Drive 2, and ares copies it. BlastEm models both columns of the table and reports that consoles with 40 words of VSRAM vary among themselves in H40. All three give 0 for H32, which BlastEm marks as still to be tested <span class="tag emulator">emulator</span> [GPGX, core/vdp_render.c; ARES, ares/md/vdp/layers.cpp; BLASTEM, vdp.c]. PicoDrive follows a different guess: column 0's values in H40, and VSRAM words 32-33 in H32 [PICODRIVE, pico/draw.c]. MAME reads VSRAM words 62 and 63 for planes A and B in both widths, past the 40 words the older consoles have, so it shows whatever was last written there [MAME, src/devices/video/315_5313.cpp]. Games that show the effect include Gynoug and Cutie Suzuki no Ringside Angel (H40), and Formula One and Kawasaki Superbike Challenge (H32) [GPGX, core/vdp_render.c].

No value works on every console, so do not draw anything meaningful there. The usual cover is to hide the first 16 pixels: with the window plane, with high-priority tiles, or with sprites.

## The window

The window is a third tile layer with its own name table (register 3). It shows a fixed area of the screen and never scrolls. Wherever it is shown, plane A is not drawn at all. For priority and shadow/highlight it behaves exactly like plane A [MD-SWM §2.9; GENVDP §13]. Status bars and menus are its usual job.

Its name table always has the screen's width, 32 entries per row in 32-column mode and 64 in 40-column mode (of which 40 are shown), whatever the plane size. Rows are therefore `$40` or `$80` bytes apart, up to 2 KB or 4 KB in total [MD-SWM §2.9, window pattern name].

Registers 17 and 18 set its area [MD-SWM §2.9, display position; GENVDP §17]:

| Register | Bit 7 | Bits 4-0 | Unit |
|----------|-------|----------|------|
| 17 (horizontal) | 0 = window left of the split, 1 = right of it | Split position, 0-16 (H32) or 0-20 (H40) | 2 tiles (16 pixels) |
| 18 (vertical) | 0 = window above the split, 1 = below it | Split position, 0-28 (or 30) | 1 tile (8 lines) |

How the two combine: on lines inside the vertical range set by register 18, the window covers the whole line. On the other lines, register 17 decides which columns it covers [GENVDP §17]. A position of 0 with the side bit at 0 means "no window" for that register. A position of 0 with the side bit at 1 means "the window covers everything".

Two examples:

- A 2-row status bar at the top: register 18 = `$02`, register 17 = `$00`.
- A 64-pixel panel on the right: register 17 = `$80 + 16`, which in H40 starts the window at column 32. Register 18 = `$00`.

### The window's edge fault

When the window is on the left and plane A is scrolled horizontally, the two-tile column of plane A just right of the window's edge is drawn wrong <span class="tag manual">manual</span> [MD-SWM §2.9, window priority]. GENVDP describes what goes wrong: if the low 4 bits of plane A's horizontal scroll are not zero, that column fetches its tile entries from the column after it, so one column of tiles repeats [GENVDP §17]. The fault does not occur with the window on the right, nor when plane A only scrolls vertically. Sega's advice is to cover the column with high-priority tiles in plane A. Scrolling plane A in steps of 16 pixels also avoids it.

## Working with name tables

A few habits from shipped code:

- **Recolour a region without a RAM copy.** To highlight a menu, Aerobiz reads a rectangle of the name table back from VRAM into a buffer on the stack. It replaces each entry's palette bits (`and #$9FFF`, then add the new palette × `$2000`) and writes the block back. Tile numbers and flips survive untouched [AB-DISASM, ApplyPaletteShifts.asm]. Reading VRAM has its own timing rule (see [the VDP overview](vdp.md#using-the-data-port)), and Aerobiz does the readback in vertical blank, a few rows per frame.
- **Draw boxes from nine tiles.** Aerobiz's dialog boxes fill the interior with one DMA, then place four corner tiles and four edge tiles from a run of consecutive tile numbers. All of them have the priority bit set, so boxes cover low-priority sprites. The same call records the box's inner edges as the text area, so later text output wraps inside it [AB-DISASM, DrawBox.asm]. See [Text and menus](../techniques/text-menus.md).
- **Step through rows by adding to the command.** A VDP command holds address bits 13-0 in its bits 29-16, so the next row of a name table is the current command plus row stride × `$10000`: `$00400000` for 32-wide planes, `$00800000` for 64, `$01000000` for 128. Aerobiz picks the constant from its copy of register 16 [AB-DISASM, CmdDMABatchWrite.asm]. This works as long as the row does not cross a 16 KB boundary of VRAM.

## Open questions

- Confirm on consoles what the leftmost partial column shows under per-column vertical scrolling ([discrepancy 40](../appendices/discrepancies.md)). The emulators' accounts need a test ROM covering both planes and both widths, run on several revisions: a Model 1, a Model 2 before and after VA4, and a Genesis 3. H32 on the later revisions has no report at all.
- Confirm on a console that interlace mode 2 reads one horizontal scroll entry per field line, so that the two fields share each entry, as all four emulators assume. GENVDP leaves the question open, and Sega's table layout only implies the answer.

## Sources

- [MD-SWM](../appendices/bibliography.md#md-swm): §2.3 line interrupt timing, §2.8 scrolling (sizes, horizontal and vertical scroll, pattern name, pattern generator), §2.9 window
- [MD-SDM](../appendices/bibliography.md#md-sdm): §5.4 two-cell vertical scroll at the left edge
- [GENVDP](../appendices/bibliography.md#genvdp): §12 patterns, §13 background layers, §17 window registers
- [AB-DISASM](../appendices/bibliography.md#ab-disasm): PackScrollDeltaToVRAM, AnimateScrollEffect, AnimateScrollWipe, VInt_Handler3, ApplyPaletteShifts, DrawBox, CmdDMABatchWrite
- [AU-NOTES](../appendices/bibliography.md#au-notes): PORT_ARCHITECTURE.md, plane rows used as storage
- [GPGX](../appendices/bibliography.md#gpgx): core/vdp_render.c, left partial column under per-column vertical scrolling
- [ARES](../appendices/bibliography.md#ares): ares/md/vdp/layers.cpp, the same
- [BLASTEM](../appendices/bibliography.md#blastem): vdp.c, systems.cfg, the same by console revision
- [PICODRIVE](../appendices/bibliography.md#picodrive): pico/draw.c, the same; horizontal and vertical scroll in interlace mode 2
- [MAME](../appendices/bibliography.md#mame): src/devices/video/315_5313.cpp, the left partial column and interlace mode 2
- [MD-TO](../appendices/bibliography.md#md-to): H scroll data table, V scroll
