# Text, menus and UI on tile planes

Text is cheap on the Mega Drive VDP. A character is a tile number in a name table, two bytes, and the VDP draws it every frame for nothing. On the 32X layer, text is pixels that a CPU has to write. Most 32X games therefore keep their text and menus on the Mega Drive side, and draw text on the 32X only where it must sit inside 32X graphics. This chapter shows both: Aerobiz Supersonic's text engine, a complete one for a menu-heavy game on tile planes [AB-DISASM], and the 32X fonts of Mortal Kombat II and Aerobiz Ultimate.

## Text on tile planes

### A font is a run of tiles

Load the font's tiles into VRAM in character order, and a character's tile number is its code minus the code of the first character in the font. Printing is writing those numbers into the plane's name table ([Name table entries](../megadrive/vdp-planes.md#name-table-entries)). The palette and priority bits of the entry choose the colour and whether the text sits in front of sprites. The [Mega Drive hello world](../howto/md-hello.md#printing) is the minimal version.

Aerobiz Supersonic has two fonts [AB-DISASM, FindCharInSet.asm `RenderTextBlock`, PrintfDirect.asm, RenderTextLine.asm]:

- **8 × 8.** The name table entry is `$0404` + (character − 32): the font starts at tile `$404`, in palette 0. `$8404` adds the priority bit, which puts the text in front of sprites.
- **8 × 16.** Each character is two tiles, (character × 2 + `$19`) above the next one, added to the same base. A line of this text is two rows tall.

### Building a line, then sending it

The engine does not write characters to VRAM one at a time. It builds a whole line in two buffers on the stack, one per tile row, each 33 words long. In the 8 × 16 font, the top halves of the characters go into the first buffer and the bottom halves into the second. When the line is finished it moves the second buffer up to follow the first, so that the two rows sit one after the other in memory. Then it sends the block to the name table as one rectangle of one or two rows, through the game's rectangle-copy command ([Rectangles](../megadrive/vdp-dma.md#dma-in-a-real-game)) [AB-DISASM, RenderTextLine.asm, FindCharInSet.asm]. One VDP transfer per line instead of one per character keeps the cost of text low, and lets the copy wait for vertical blank like any other.

### Word wrap and control codes

- **Word wrap.** Before placing a word, the engine looks ahead to measure it against the window's right edge. If it will not fit, the line is sent and a new one started. A space that falls at the break is dropped.
- **Control codes.** A byte `$1B` (ESC) starts a command. ESC `=` followed by two bytes sets the cursor's row and column, each stored plus 32 so that the bytes are printable characters. ESC `R` and ESC `E` set the window's left and right margins. ESC `W` makes the text wait, through the game's frame-wait command. A few other letters switch modes.

Sources: [AB-DISASM, FindCharInSet.asm `RenderTextBlock`]. Storing positions as printable characters keeps every string in the game ordinary text, which a script or a translation tool can edit.

### A formatter that knows about tiles

The game formats numbers and strings with its own small `printf`: `%d`, `%u`, `%x`, `%s` and `%c`, with field widths, precision, left alignment and zero padding. Two additions fit a tile screen [AB-DISASM, Vsprintf.asm, IntToDecimalStr.asm]:

- **Columns in the tall font.** A `W` conversion doubles the field width and precision, so that columns of figures line up when each character is two tiles.
- **Money without large multiplies.** A `$` flag writes a dollar sign before the number and "0K" after it. Money is stored in units of $10,000, so a stored 123 prints as `$1230K`, and the 68000 never multiplies a 32-bit value by 10,000. Two `$` flags leave out the "0K".

The decimal conversion is recursive: it prints the number divided by 10, then the last digit. That is short code, but each digit costs a stack frame, which matters if text can be printed from an interrupt.

### Two digits in one tile

A strategy screen is full of small numbers. Aerobiz Supersonic fits a number from 0 to 99 into a single 8 × 8 tile, built at run time [AB-DISASM, RoundValue.asm at `$01DF30`; digit tiles at `$048E00`]:

- **The digit tiles** are 4 pixels wide, drawn in the right half of their tiles.
- **The units digit** is read from its tile normally.
- **The tens digit** is read starting 2 bytes into its tile. A tile row is 4 bytes, 8 pixels of 4 bits, so reading each row 2 bytes late takes the right half of one row and the left half of the next. Read as a row, the tens digit lands in the left half.
- **The two are ORed together**, eight longwords, giving tens on the left and units on the right in one 32-byte tile. A tens digit of 0 uses a blank tile.

No shifting code at all: the offset read does the shift. (The disassembly's name for the routine, `RoundValue`, describes something else.)

### Windows and panels

A window is a rectangle of name table entries: a border of edge and corner tiles, and a fill. The VDP has no two-dimensional transfer, so each row of a rectangle is its own DMA or copy. Aerobiz fills one row of the fill value in a buffer and sends it once per row ([DMA in a real game](../megadrive/vdp-dma.md#dma-in-a-real-game)). The VDP's window plane, a fixed area that replaces plane A on part of the screen, suits a status bar that must not scroll ([The window](../megadrive/vdp-planes.md#the-window)).

### Screen changes behind a fade

Every Aerobiz screen is drawn behind a fade. Before drawing, a screen calls a routine that fades all 64 colours out in eight steps; after drawing, it calls the matching fade-in. Each routine checks a flag first and does nothing if the screen is already in that state. Screens that call other screens can therefore call the pair freely, with no double fades [AB-DISASM, ResourceLoad.asm, DrawLayersReverse]. The two routines are called from more than 200 places. Their names in the disassembly, `ResourceLoad` and `ResourceUnload`, describe something else; reading the code is what shows they are fades.

## Text on the 32X layer

Text drawn by the SH-2s costs a write per pixel, but it can be any size, any shape and any colour, and it sits inside the 32X picture instead of in front of or behind it.

### Mortal Kombat II: proportional fonts and a text list

Mortal Kombat II draws its 32X text on the Master [MK2, SH-2 code at `0x060011A8`, `0x060016AC`, `0x0600122A`]:

- **Three fonts** are unpacked from RNC-packed data into SDRAM when a screen starts, at `0x06036B2C`, `0x06037F60` and `0x06038F28`.
- **Each glyph record** gives its width, height and the offset of its pixels, so the fonts are proportional.
- **One font, any colour.** A glyph pixel of 1 is replaced by the requested colour when drawn. Pixels of 0 are written through the overwrite image, which skips them, so the background shows through without any test ([The normal and overwrite images](../32x/vdp.md#the-normal-and-overwrite-images)).
- **What to print** arrives from the 68000 each frame as part of its state block: a list of 12 entries, each a message number and a position. Empty entries and entries below the screen are skipped ([Bulk data through the ports](../32x/communication.md#bulk-data-through-the-ports)).

### Aerobiz Ultimate: a text engine for the layer

Aerobiz Ultimate adds a text engine to the 32X layer for its new screens <span class="tag emulator">emulator</span> [AU-NOTES, ROADMAP U-090; tools/make_text_font.py]:

- **Glyphs from a desktop font**, rendered by a build tool into 1-bit proportional glyphs, each with its width and pen advance, in two sizes.
- **Measuring and wrapping on the SH-2**, by adding up advances from the table.
- **Ink and paper in palette entries 254 and 255**, never 0, because a byte write of 0 to the frame buffer is skipped ([One palette, many users](../32x/compositing.md#one-palette-many-users)).
- **A highlight that costs no drawing.** The menu cursor pulses by changing one palette entry; no pixel is redrawn.

### Which side for which text

| Text | Where |
|------|-------|
| HUD, scores, timers, status bars | Mega Drive planes: free per frame, crisp, in front of the 32X picture with PRI 0 ([Using both video chips at once](../patterns/layering.md)) |
| Menus and dialogue over a Mega Drive screen | Mega Drive planes |
| Text that must sit inside 32X art, scale, or use more than 15 colours | The 32X layer, drawn by an SH-2 |
| Text in a 32X-only game | The 32X layer; Motocross Championship draws its whole HUD there ([What the shipped games put where](../patterns/layering.md#what-the-shipped-games-put-where)) |

## What to take away

- On tile planes, a character is a tile number: load the font in order and write name table entries.
- Build each line in a buffer and send it as one rectangle, not a character at a time.
- Put formatting where the screen needs it: field widths in tiles, money in the units the game stores.
- Share a tile between two digits when space is tight; an offset read can do the shifting.
- Draw screens behind guarded fades, so screens can be nested freely.
- On the 32X, use the overwrite image for transparent glyph pixels, recolour one font at draw time, and keep text colours out of entry 0.

## Open questions

- How do the other retail 32X games divide their text between the two layers? Star Wars Arcade's score and timer are Mega Drive tiles; the others have not been checked.

## Sources

- [AB-DISASM](../appendices/bibliography.md#ab-disasm): FindCharInSet.asm (`RenderTextBlock`), RenderTextLine.asm, PrintfDirect.asm, Vsprintf.asm, IntToDecimalStr.asm, RoundValue.asm, ResourceLoad.asm, DrawLayersReverse
- [MK2](../appendices/bibliography.md#mk2): SH-2 code at `0x060011A8`, `0x060016AC`, `0x0600122A`
- [AU-NOTES](../appendices/bibliography.md#au-notes): ROADMAP U-090; tools/make_text_font.py
