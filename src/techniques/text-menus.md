# Text, menus and UI

Text is cheap on the Mega Drive VDP. A character is a tile number in a name table, two bytes, and the VDP draws it every frame for nothing. On the 32X layer, text is pixels that a CPU has to write. The Mega Drive side is therefore the cheap default for a 32X game's text and menus: Star Wars Arcade and After Burner Complete keep their HUD there. Mortal Kombat II and Motocross Championship draw text on the 32X anyway, because it must sit inside 32X graphics or because the Mega Drive layer is unused ([What the shipped games put where](../patterns/layering.md#what-the-shipped-games-put-where)).

This chapter shows both. Aerobiz Supersonic is a plain Mega Drive game, but it is the original that Aerobiz Ultimate was ported from ([the case study](../patterns/case-study-aerobiz.md)), and its text engine is a complete one for a menu-heavy game on tile planes [AB-DISASM]. A 32X game's Mega Drive layer works the same way. The 32X half covers the fonts of Mortal Kombat II and Aerobiz Ultimate.

## Text on tile planes

### A font is a run of tiles

Load the font's tiles into VRAM in character order, and a character's tile number is its code minus the code of the first character in the font. Printing is writing those numbers into the plane's name table ([Name table entries](../megadrive/vdp-planes.md#name-table-entries)). The palette and priority bits of the entry choose the colour and whether the text sits in front of low-priority sprites (see below). The [Mega Drive hello world](../howto/md-hello.md#printing) is the minimal version.

Aerobiz Supersonic has two fonts, loaded together into one run of tiles by the graphics loader at `$03A7A0` [AB-DISASM, FindCharInSet.asm `RenderTextBlock`, LoadGameGraphics.asm]:

- **8 × 8.** The name table entry is `$0404` + (character − 32). Tile `$404` is loaded separately and is the formula's slot for the space, which the engine never uses (a space is written as entry 0). Then come 90 glyphs at `$405-$45E` for `!` to `z`. Palette 0. There is no glyph for `{ | } ~`, and the code does not stop them printing: they would pick the first tiles of the 8 × 16 font.
- **8 × 16.** Each character is two tiles, top half then bottom half in consecutive tiles: the entry is `$0404` + 2 × character + `$19`, with no 32 subtracted. The first glyph, `!` (character 33), is tile `$45F`, the one after the last 8 × 8 glyph. The loader's count is 100 glyphs, 200 tiles, `$45F-$526`. A space has no glyph: it is written as a blank entry. A line of this text is two rows tall but still one column per character. The glyphs from `{` upward are not what ASCII has there: the nine I decoded from the game's data are small pictograms, not braces, and I have not identified them. The hundredth entry decoded to 576 bytes instead of 64 and begins like the `{` glyph, so it may be padding or my decoder running past the end of its data; whether the font really has 100 glyphs or 99 is unsettled. The text routine prints codes up to `~` only, so everything past the first four of them (`{ | } ~`) can never be reached by it.

Setting the priority bit adds `$8000` to the entry, giving `$8404`. The escape sequence ESC `P` `1` turns that on and any other value after ESC `P` turns it off. The bit puts the text in front of low-priority sprites. A high-priority sprite still covers it ([Priority](../megadrive/vdp-color.md#priority)).

### Building a line, then sending it

The engine does not write characters to VRAM one at a time. It builds a whole line in two buffers on the stack, one per tile row. Each is 33 words ($42 bytes): the 32 columns the cursor wraps at, plus one. With the usual 32-column window a cursor at the right edge flushes the line before the next character is stored, so 32 words would do and what the 33rd is for is not visible. In the 8 × 16 font, the top halves of the characters go into the first buffer and the bottom halves into the second. When the line is finished it moves the second buffer up to follow the first, so that the two rows sit one after the other in memory. Then it sends the block to the name table as one rectangle of one or two rows, through the game's rectangle-copy command ([Rectangles](../megadrive/vdp-dma.md#dma-in-a-real-game)) [AB-DISASM, RenderTextLine.asm, FindCharInSet.asm]. One VDP transfer per line instead of one per character keeps the cost of text low, and lets the copy wait for vertical blank like any other.

### Word wrap and control codes

- **Word wrap.** Before placing a word, the engine looks ahead to measure it against the window's right edge. If it will not fit, the line is sent and a new one started. A space that falls at the break is dropped.
- **Control codes.** A byte `$1B` (ESC) starts a command. ESC `=` followed by two bytes sets the cursor's row and then its column, each stored plus 32 so that the bytes are printable characters. That is the cursor-addressing sequence of the ADM-3A terminal, row first, so the convention probably came from there. ESC `R` and ESC `E` set the window's left and right margins (after each line the cursor returns to the left margin). ESC `W` makes the text wait, through the game's frame-wait command. ESC `P` is the priority switch above. ESC `G` and ESC `M` set modes whose purpose I have not traced. Storing positions as printable characters keeps every string in the game ordinary text, which a script or a translation tool can edit [AB-DISASM, FindCharInSet.asm `RenderTextBlock`].

### The number formatter

The game formats numbers and strings with its own small `printf`: `%d`, `%u`, `%x`, `%s` and `%c`, with field widths, precision, left alignment and zero padding. Two parts are unusual [AB-DISASM, Vsprintf.asm, IntToDecimalStr.asm]:

- **Money without large multiplies.** A `$` flag writes a dollar sign before the number and "0K" after it. Money is stored in units of $10,000, so a stored 123 prints as `$1230K`, and the 68000 never multiplies a 32-bit value by 10,000. Two `$` flags leave out the "0K".
- **A `W` conversion** prints an unsigned decimal like `%u`, but doubles the field width and the precision first, so `%4W` pads to eight characters. The disassembly's comment says this is for a font two tiles wide. That does not fit: the 8 × 16 font advances one column per character (the cursor moves by one in both fonts), and none of the format strings readable in the ROM uses `W`. Its purpose is unknown. One hypothesis, untested: the engine is shared with the Japanese release, where full-width characters would take two columns, and `W` is left over from that. If that ROM's strings use `W`, the comment was right about another build, and it is also the first place to look for the pictograms above.

The decimal conversion is recursive: it prints the number divided by 10, then the last digit. That is short code, but each digit costs a stack frame: up to ten levels for a 32-bit value, 24 bytes each by my count (saved registers, return address, two arguments), so about 240 bytes. That matters if text can be printed from an interrupt.

### Two digits in one tile

A strategy screen is full of small numbers. Aerobiz Supersonic fits a number from 0 to 99 into a single 8 × 8 tile, built at run time [AB-DISASM, RoundValue.asm at `$01DF30`; digit tiles at `$048E00`]:

- **The digit tiles** are 4 pixels wide, drawn in the right half of their tiles. The left half of every one is blank.
- **The units digit** is read from its tile normally.
- **The tens digit** is read starting 2 bytes into its tile. A tile row is 4 bytes, 8 pixels of 4 bits, so reading each row 2 bytes late takes the right half of one row and the left half of the next. Read as a row, the tens digit lands in the left half, and the right half is the blank left half of the following row.
- **The two are ORed together**, eight longwords, giving tens on the left and units on the right in one 32-byte tile. A tens digit of 0 uses a blank tile.

No shifting code at all: the offset read does the shift. It depends on the tile data in two ways. The left halves must be blank, or the OR would mix pixels. And the last longword of the tens read runs 2 bytes past the end of its tile, into the next tile in the table. For the 9 that is the blank tile placed right after it (offset `$140`). Reorder the tiles and the overrun reads someone else's pixels.

The built tile has to go somewhere. `RoundValue` writes it to a 32-byte buffer on the stack; the caller, `PlaceFormattedTiles`, uploads it as one tile to a VRAM slot it is given (game command 5, sub-command 2), then places that tile number on screen with the same tile-rectangle routine as the cursor below. So each number on screen owns a tile slot, and the real cost is one 32-byte transfer per number, not the building [AB-DISASM, RoundValue.asm `PlaceFormattedTiles`; ProcessTextControl.asm].

## Windows, cursors and fades

### Windows and panels

A window is a rectangle of name table entries: a border of edge and corner tiles, and a fill. The VDP has no two-dimensional transfer, so each row of a rectangle is its own DMA or copy. Aerobiz fills one row of the fill value in a buffer and sends it once per row ([DMA in a real game](../megadrive/vdp-dma.md#dma-in-a-real-game)). The VDP's window plane, a fixed area that replaces plane A on part of the screen, suits a status bar that must not scroll ([The window](../megadrive/vdp-planes.md#the-window)).

### Cursors

Aerobiz's selection cursor is not a sprite. `PlaceCursor` writes a 2 × 2 block of tiles, starting at tile `$744` with the priority bit set, at a given position; a flag adds a second block from tile `$740`, which the disassembly's comment calls two-player mode [AB-DISASM, PlaceCursor.asm]. I have not traced how the old cursor is erased or how the menus read the pad, so this chapter does not describe the menu loops.

### Screen changes behind a fade

Every Aerobiz screen is drawn behind a fade. Before drawing, a screen calls a routine that fades all 64 colours out in eight steps; after drawing, it calls the matching fade-in. Each of the two fade routines checks a flag first and does nothing if the screen is already in that state. Screens that call other screens can therefore call the pair freely, with no double fades. The two routines are called from more than 200 places. The eight steps themselves are a loop in `DrawLayersReverse`, which calls the game's palette-fade routine once per step [AB-DISASM, ResourceLoad.asm, DrawLayersReverse.asm].

## Text on the 32X layer

Text drawn by the SH-2s costs a write per pixel, but it can be any size, any shape and any colour, and it sits inside the 32X picture instead of in front of or behind it.

There are two frame buffers, and the display shows one while the CPUs draw into the other ([Frame buffers and the FS bit](../32x/vdp.md#frame-buffers-and-the-fs-bit)). Text drawn once is in one buffer only. It must be drawn into both, or redrawn every picture. That is the first thing that bites a 32X text screen, and the two games below solve it in opposite ways.

### Mortal Kombat II: proportional fonts and a text list

Mortal Kombat II draws its 32X text on the Master [MK2, SH-2 code at `0x060011A8`, `0x060016AC`, `0x0600122A`]:

- **Three fonts** are unpacked from RNC-packed data into SDRAM when a screen starts, at `0x06036B2C`, `0x06037F60` and `0x06038F28`.
- **Each glyph record** gives its width, height and the offset of its pixels, so the fonts are proportional.
- **One font, any colour.** A glyph pixel of 1 is replaced by the requested colour when drawn. Pixels of 0 are skipped by the hardware, so the background shows through without any test. The routine writes one *byte* per pixel, to the overwrite image address; a byte of 0 is ignored in the normal image too, so for byte writes the overwrite image is not required. It is what lets a *word* write do the same ([The normal and overwrite images](../32x/vdp.md#the-normal-and-overwrite-images)).
- **What to print** arrives from the 68000 each frame as part of its state block: a list of 12 entries, each a message number and a position. Empty entries and entries below the screen are skipped ([Bulk data through the ports](../32x/communication.md#bulk-data-through-the-ports)). Because the list arrives and is drawn every frame, into whichever buffer is the back buffer, nothing needs drawing twice.

### Aerobiz Ultimate: a text engine for the layer

Aerobiz Ultimate adds a text engine to the 32X layer for its new screens <span class="tag emulator">emulator</span> [AU-NOTES, ROADMAP U-090; tools/make_text_font.py; disasm/sh2/master/text.c]:

- **Glyphs from a desktop font**, rendered by a build tool into 1-bit proportional glyphs, each with its width and pen advance, in two sizes.
- **Measuring and wrapping on the SH-2**, by adding up advances from the table.
- **Ink in palette entry 254, paper in 255**, never 0, so that no pixel the engine means to draw is a zero byte, which the normal image ignores ([The normal and overwrite images](../32x/vdp.md#the-normal-and-overwrite-images), [One palette, many users](../32x/compositing.md#one-palette-many-users)). Entry 255 is the paper of screens that fill their background with it, like the title screen; the New Game menu uses its own entries (1 for the background, 3 for the band, 33 for the highlight).
- **No background of its own.** The glyph blitter writes single bytes, and only a glyph's set pixels, in ink. Text takes its background from whatever is underneath, such as a menu bar.
- **A highlight that costs no drawing.** The New Game menu's cursor is a filled bar behind the selected entry, drawn in palette index 33 while the other entries' bars use the background index. The pulse changes only entry 33's colour, every frame; no pixel is redrawn for it.
- **Moving the cursor does redraw.** The menu repaints a whole page: fill, bars, then the labels, because a bar is a filled rectangle and drawing it over a label erases the label. It does this twice, once per buffer: paint the back buffer, flip at vertical blank, paint the other.

### Which side for which text

| Text | Where |
|------|-------|
| HUD, scores, timers, status bars | Mega Drive planes: nothing to draw per frame, in front of the 32X picture with PRI 0 ([Using both video chips at once](../patterns/layering.md)) |
| Menus and dialogue over a Mega Drive screen | Mega Drive planes |
| Text that must sit inside 32X art, scale, or use more than 15 colours | The 32X layer, drawn by an SH-2 |
| Text in a 32X-only game | The 32X layer; Motocross Championship draws its whole HUD there |

## What to take away

- On tile planes, a character is a tile number: load the font in order and write name table entries.
- Build each line in a buffer and send it as one rectangle, not a character at a time.
- Format in the units the game stores: Aerobiz keeps money in units of $10,000 and prints the trailing zeros as text.
- Share a tile between two digits when space is tight; an offset read can do the shifting. Each built tile still needs a VRAM slot and an upload.
- Draw screens behind guarded fades, so screens can be nested freely.
- On the 32X, draw static text into both buffers or redraw it every picture; skip zero pixels with byte writes, or word writes through the overwrite image; recolour one font at draw time; and keep text colours out of entry 0.
- A palette entry can animate a highlight for free, but changing which item is highlighted means redrawing it in both buffers.

## Open questions

- How do the other retail 32X games divide their text between the two layers? Star Wars Arcade and After Burner Complete use Mega Drive tiles, Mortal Kombat II and Motocross Championship the 32X; Knuckles' Chaotix and the rest of the romset have not been checked.
- What `W` in the format strings was for (the Japanese release is the place to test the full-width hypothesis), what the 33rd word of each line buffer is for, and what ESC `G` and ESC `M` do.
- Whether a real console skips a zero byte written to the normal image. The manual says so, and this chapter repeats it ("for byte writes the overwrite image is not required"), but no console test confirms it and no game in this chapter depends on it: Mortal Kombat II writes through the overwrite image, and the Aerobiz Ultimate engine never writes a zero.
- How Aerobiz Supersonic's menus erase and move the cursor, and how they read the pad.

## Names in the disassembly

Some names in the Aerobiz Supersonic disassembly describe something else:

| Disassembly name | What the code does |
|------------------|--------------------|
| `FindCharInSet.asm`, `RenderTextBlock` | The file is named for its first routine, a delimiter lookup; `RenderTextBlock` is the text engine itself |
| `RoundValue` | Builds a two-digit tile |
| `ProcessTextControl` | Uploads tiles to VRAM through the game's command |
| `ResourceLoad`, `ResourceUnload` | Fade out and fade in |
| `DrawLayersReverse` | The eight-step loop that calls the palette-fade routine |

## Sources

- [AB-DISASM](../appendices/bibliography.md#ab-disasm): FindCharInSet.asm (`RenderTextBlock`), RenderTextLine.asm, PrintfDirect.asm, Vsprintf.asm, IntToDecimalStr.asm, RoundValue.asm, LoadGameGraphics.asm, ProcessTextControl.asm, PlaceCursor.asm, ResourceLoad.asm, DrawLayersReverse.asm
- [MK2](../appendices/bibliography.md#mk2): SH-2 code at `0x060011A8`, `0x060016AC`, `0x0600122A`
- [AU-NOTES](../appendices/bibliography.md#au-notes): ROADMAP U-090; tools/make_text_font.py; disasm/sh2/master/text.c (`menu_paint_page`, `menu_paint_both`, `menu_pulse`)
