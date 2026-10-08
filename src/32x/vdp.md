# The 32X VDP

The 32X VDP is simple compared with the Mega Drive's. It has no tiles, no sprites, no scaling and no drawing commands. Every line, it reads 320 pixels from a frame buffer and sends them out to be mixed with the Mega Drive picture. Everything that appears on the 32X layer was put into memory by a CPU, almost always an SH-2.

What makes it more flexible than a plain bitmap is one level of indirection. Each screen line has its own pointer in a **line table**, so you choose where each line's pixels come from. Most of the tricks in this chapter come from that table.

## What the VDP shows

| | NTSC | PAL |
|---|---|---|
| Visible size | 320 × 224 | 320 × 224, or 320 × 240 with the 240-line bit |
| Blank lines per frame | 38 | 89 (224 lines) or 73 (240 lines) |
| Colours | 32,768 directly, or 256 at a time from a palette of 32,768 | same |

Sources: [32X-HWM §3.3, display specifications, vertical blanking periods].

- **The 240-line mode is for PAL only.** Setting the 240 bit on an NTSC machine makes the VDP misbehave <span class="tag manual">manual</span> [32X-HWM §3.3, register latch timing].
- **The Mega Drive must match.** While the 32X layer shows anything, the Mega Drive VDP should be in its 320-pixel-wide mode with the same number of lines. The 256-pixel modes are only allowed when the 32X layer is blanked <span class="tag manual">manual</span> [32X-HWM §3.3, display mode]. What happens if you ignore this is in [Mixing 32X and Mega Drive graphics](compositing.md).

## Frame buffers and the FS bit

There are two frame buffers of 128 KB (65,536 words) each. One is on screen while the other is available for drawing. The CPUs only ever see one of them, the one *not* being displayed, at a single address range [32X-HWM §3.3, switching frame buffers]:

| | Normal | Overwrite image |
|---|---|---|
| SH-2 | `0x24000000-0x2401FFFF` | `0x24020000-0x2403FFFF` |
| 68000 | `$840000-$85FFFF` | `$860000-$87FFFF` |

The overwrite image is the same memory with a different write rule, covered under [Writing pixels](#writing-pixels). The CPU side that owns the 32X VDP is chosen by FM (see [Architecture and memory maps](architecture.md#who-can-reach-what)).

**FS** (bit 0 of the frame buffer control register) chooses which buffer is displayed: 0 shows the first, 1 the second. Writing it always works, but the swap only happens during vertical blanking. A write during the visible part of the frame is held until the next blank. A write during blanking, or while the bitmap mode is blank, takes effect at once. Reading FS gives the buffer that is on screen *now*, so after writing it you know the swap has happened when the value you read changes. Do not touch the frame buffer between the write and the swap: until then you are still looking at the buffer on screen <span class="tag manual">manual</span> [32X-HWM §3.2.3, frame buffer control register].

A typical double-buffered loop:

1. The SH-2s draw into the back buffer.
2. When they are done, they tell the CPU that handles vertical blanking.
3. That CPU waits for vertical blank (VBLK = 1) and flips FS.
4. Drawing starts on the new back buffer, which is the one that was just on screen.

Virtua Racing Deluxe does exactly this: its 68000 flips FS in its vertical blank handler, and only after the SH-2 has flagged the frame complete through a communication port [VRD-NOTES, rendering pipeline]. Mortal Kombat II keeps it all on the Master SH-2. Its main loop waits for the V interrupt to bump a frame counter, then flips FS at once by inverting the low byte of `0x2000410B`. The write lands in blanking, so it takes effect straight away, and the Master starts clearing the new back buffer without reading FS back [MK2, SH-2 code at `0x0600051A`, `0x06001088`, `0x060010A4`].

Each buffer has its own line table and its own pixels. Anything that should look the same in both, such as a static background or the line table itself, has to be written twice, once into each buffer [AU-NOTES, frame buffer]. Mortal Kombat II gets this for free: its idle mode rewrites the line table and clears the screen every frame, and since it flips every frame, both buffers get a table [MK2, SH-2 code at `0x06000608`].

## The line table

The first 256 words of each frame buffer are the line table. Entry *n* holds the **word address** within the same buffer where line *n*'s pixels begin. Only the first 224 or 240 entries are used. Pixel data can go anywhere after the table [32X-HWM §3.3, line table format; 32X-HWI item 5].

```text
word 0     ┌──────────────────────────────┐
           │ line table: 256 entries      │  entry n = word address of line n
word 256   ├──────────────────────────────┤
           │ pixel data for line 0        │  ◄── entry 0 = 256
           │ pixel data for line 1        │  ◄── entry 1
           │ ...                          │
word 65535 └──────────────────────────────┘
```

The VDP reads 320 pixels' worth of data from wherever an entry points. It does not stop at the end of the buffer or check that the data belongs to the line. A line that starts too close to the end shows whatever comes after it <span class="tag manual">manual</span> [32X-HWM §3.3, display precautions; 32X-HWI item 5].

Because the table is just a list of pointers, several effects cost nothing per pixel:

- **Vertical scrolling** is a matter of rewriting the table, not moving pixels.
- **Vertical stretching and line repetition.** Several entries may point to the same data. A row drawn once can fill as many screen lines as you like. Aerobiz Ultimate's map zoom draws only the distinct source rows and lets the table repeat them [AU-NOTES, frame buffer].
- **Plain areas.** All the lines of a solid sky can point to a single line of data.
- **Horizontal offsets per line.** Moving an entry by a word moves that line sideways, which is enough for wavy or sheared effects. The step is one word, so 2 pixels in packed pixel mode and 1 pixel in direct colour mode.

### Guard bands: drawing without clipping

The table also lets the visible lines sit in the middle of the buffer, with memory to spare on every side. A sprite that hangs off the screen then lands in memory nobody displays, and the blitter needs no clipping per pixel.

Mortal Kombat II lays its fight screens out this way [MK2, SH-2 code at `0x060010B0`, `0x06002CEC`]:

- **Lines are 368 bytes apart** (184 words): 320 visible pixels plus a 48-pixel tail that is never shown.
- **Line 0 starts at byte `$8C00`** (table entries `$4600` + *n* × `$B8`, for 226 lines). The 35,328 bytes between the line table and line 0 are exactly 96 lines of 368 bytes.
- **The sprite clipper only rejects sprites that are entirely off-screen,** or that would reach past the bands: it accepts a left edge down to −48, a right edge up to 371, and a top edge down to −96. Anything left of the screen writes into the previous line's hidden tail, and anything above writes into the 96 hidden lines.

The price is memory: 96 + 226 lines of 368 bytes fill most of the 128 KB buffer. A program that wants the spare frame-buffer memory for other data cannot also have wide guard bands.

### Fine horizontal scrolling

In packed pixel mode a word holds two pixels, so the table alone can only move a line in 2-pixel steps. The **SFT** bit of the screen shift control register shifts every line one more pixel to the left, which fills in the odd positions <span class="tag manual">manual</span> [32X-HWM §3.3, screen shift control]. SFT has no effect on any line whose table entry has `$FF` as its low byte. Keep shifted lines off those addresses <span class="tag manual">manual</span> [32X-TI item 14].

## Pixel modes

The two mode bits M1 and M0 in the bitmap mode register choose how the VDP reads the data a line points to. All lines use the same mode, but the register is read again at the start of every line, so a mode change made during a frame applies from the next line on [32X-HWM §3.2.3, bitmap mode register].

| M1 M0 | Mode | Data per pixel | Words per line | Lines that fit after the table |
|-------|------|----------------|----------------|--------------------------------|
| 0 0 | Blank | None: the 32X layer shows nothing | | |
| 0 1 | Packed pixel | 8-bit palette index | 160 | 408 |
| 1 0 | Direct colour | 16-bit colour | 320 | 204 |
| 1 1 | Run length | 8-bit palette index and 8-bit run length per word | varies | varies |

Sources: [32X-HWM §3.2.3; §3.3, direct color, packed pixel and run length modes]. The "lines that fit" column is the 65,280 words left after the line table, divided by one line's size.

### Packed pixel

One byte per pixel, two pixels per word. The high byte of each word is the left pixel [32X-HWM §3.3, Figure 3.11; PICODRIVE, draw.c]. Each byte selects one of the 256 palette entries. A full screen of unique lines needs 224 × 160 = 35,840 words, a little over half a buffer, which leaves room for extra lines to scroll into.

This is the mode most games use. Virtua Racing Deluxe draws its 3D scenes in it, and Aerobiz Ultimate uses it for its world map [VRD-NOTES, rendering pipeline; AU-NOTES, world map].

### Direct colour

One word per pixel in the palette's colour format (see [below](#colours-and-the-palette)), so no palette is needed. A buffer only has room for 204 unique lines of 320 pixels, which is fewer than the screen has. A full 224-line direct colour picture needs some lines to share data, for example a border or a repeated band <span class="tag manual">manual</span> [32X-HWM §3.3, direct color mode]. It also costs twice the memory bandwidth of packed pixel to draw, so it suits still images, fades and effects more than games at full speed.

### Run length

Each word describes a run of identical pixels. The high byte is the run length minus one, so 0 to 255 means 1 to 256 pixels. The low byte is the palette index [32X-HWM §3.3, Figure 3.13; PICODRIVE, draw.c]. The VDP keeps reading words until it has 320 pixels. Anything past pixel 320 is ignored, so the last run of a line may overshoot <span class="tag manual">manual</span> [32X-HWM §3.3, run length mode].

A line of a few large flat areas takes a handful of words instead of 160. That makes the mode fast for flat-shaded polygons and solid backgrounds, but awkward for anything detailed. You cannot easily change one pixel in the middle of a run.

## Colours and the palette

A colour is one 16-bit word [32X-HWM §3.3, color palette]:

| Bit | 15 | 14-10 | 9-5 | 4-0 |
|-----|----|-------|-----|-----|
| Meaning | Through bit | Blue | Green | Red |

Each channel has 32 levels. Red is in the low bits, unlike most PC formats. The through bit (also called the priority bit) decides whether the pixel goes in front of or behind the Mega Drive picture. See [Mixing 32X and Mega Drive graphics](compositing.md). Mortal Kombat II leaves PRI at 0 (Mega Drive in front) and sets the through bit on 255 of its 256 palette entries during a fight. Its fighters, drawn on the 32X, come out in front of an arena drawn by the Mega Drive <span class="tag emulator">emulator</span> [MK2, palette and bitmap mode register read in PicoDrive].

The palette holds 256 such words, at `$A15200` on the 68000 and `0x20004200` on the SH-2. Things that matter in practice:

- **There is only one palette.** It is not double-buffered like the frame buffers. If the two buffers need different palettes, the palette has to change at the moment of the swap, during vertical blank [32X-HWM §3.3, color palette; AU-NOTES, palette budget].
- **Word access only.** Byte reads and writes do not work <span class="tag manual">manual</span> [32X-HWM §3.1].
- **In packed pixel and run length modes, the palette is only reachable during blanking.** The PEN bit in the frame buffer control register reads 1 while access is allowed. An access while PEN is 0 makes the CPU wait, for up to a whole line (about 64 µs) [32X-HWM §3.3, color palette; §4.4]. An access that is still running when PEN drops back to 0 is not reliable, and the hardware gives no warning. The manual asks for accesses to finish at least 1 µs before that point <span class="tag manual">manual</span> [32X-HWM §5.3, DMA restrictions item 5].
- **In direct colour mode and blank mode, the palette is always reachable** [32X-HWM §3.2.3].

The safe rule is to update the palette during vertical blank. Small changes inside horizontal blanking are possible, but the window is short.

## Writing pixels

### The normal and overwrite images

Through the normal range, a word write stores both bytes. A *byte* write of zero is ignored, though any other byte value is stored. To store a 0, write a word or use auto fill <span class="tag manual">manual</span> [32X-HWM §3.3, DRAM; 32X-HWI item 6].

Through the overwrite image, any byte that is zero is skipped and the pixel underneath stays as it was. This is true for word writes too. With palette index 0 as "transparent", you can copy a shape with holes in it as plain words, without reading the frame buffer or masking anything <span class="tag manual">manual</span> [32X-HWM §3.3, over write image]. The same rule makes the overwrite image wrong for ordinary copies, because any 0 in the source is lost [AU-NOTES, 32X pitfalls].

Mortal Kombat II draws everything except its screen clears through the overwrite image (`0x24020000` and up). Its rectangle blits copy whole words and let the hardware drop the 0 bytes. Its font routine writes glyph pixels as they come, so the background shows through the 0s [MK2, SH-2 code at `0x06004CC0`, `0x06004CF2`, `0x060016AC`]. After Burner Complete's sprite scaler writes every scaled sprite through the overwrite image too, so its inner loop has no transparency test at all [AB32X, SH-2 code at `0x06006778`-`0x06006A44`]. See [2D effects](../techniques/2d-effects.md).

### Writing from the SH-2

- **Use the cache-through addresses.** The frame buffer at `0x04000000` always means "the back buffer", which changes at every swap. Cached copies of its contents go stale at the swap, or when the other SH-2 or the auto fill writes underneath them. The manual asks for everything except the palette to be reached through the cache-through range <span class="tag manual">manual</span> [32X-HWM §3.3, VDP configuration]. There is one deliberate exception in practice. d32xr keeps read-only lookup tables in the spare frame buffer memory after the visible lines, builds them in both buffers, and reads them through the cached address. Since the data is the same in both buffers and never changes, a stale cache line still holds the right value [D32XR, r_data.c]. The same project keeps its shared per-frame work lists there too, but reads those cache-through, so neither SH-2 ever needs to purge [D32XR, r_main.c].
- **Writes go into a small buffer.** The SH-2 does not have to wait for the DRAM on every write. While the buffer has room, a write takes 3 clocks. Once it is full, each write takes 5. Bits 15 (full) and 14 (empty) of `0x20004006` show its state <span class="tag disputed">disputed</span> [32X-HWM §4.4, frame buffer; §3.2.2, DREQ control register; [discrepancy #4](../appendices/discrepancies.md)]. The manual says it holds four words. Earlier documents describe a smaller one on the first development boards.
- **A longword write is two word writes.** The boot ROM sets the frame buffer's bus to 16 bits wide, so `mov.l` gives no speed advantage over two `mov.w` [VRD-NOTES, 32X BIOS dump; SH7604 §7.2.2].
- **Reading is slow.** A frame buffer read costs 5 to 12 wait states. Code that would read, modify and write pixels should keep its working copy in SDRAM or on-chip RAM and only write to the frame buffer [32X-HWM §4.4, frame buffer]. See [Access timing per CPU](timing.md).
- **Both SH-2s can draw at the same time.** They share the bus, so they will slow each other down, but splitting the screen between them is allowed and intended [32X-OV, Master access to frame buffers].

The 68000 can also write the frame buffer, with no wait states for writes and 2 to 4 for reads, while FM = 0 [32X-HWM §4.4].

## Auto fill

The VDP can fill part of the back buffer with one word value while the CPUs do something else. It is controlled by three registers:

| Register | 68000 | SH-2 | Contents |
|----------|-------|------|----------|
| Auto fill length | `$A15184` | `0x20004104` | Number of words minus 1 (0-255, so 1 to 256 words) |
| Auto fill start address | `$A15186` | `0x20004106` | Word address of the first word to fill |
| Auto fill data | `$A15188` | `0x20004108` | The value. Writing this register starts the fill |

Sources: [32X-HWM §3.2.3, auto fill registers; §3.3, FILL function].

How it behaves:

- **A fill never crosses a 256-word boundary.** Only the low 8 bits of the address count up. A fill that reaches the end of a 256-word block carries on from the start of the same block. The start address register is left pointing after the last word written <span class="tag manual">manual</span> [32X-HWM §3.3, Figure 3.14]. The usual way to clear a buffer is 256-word fills at addresses `$0000`, `$0100`, `$0200` and so on. Sega's own initial program clears both buffers this way, with a length of `$FF` [VRD-NOTES, ROM]. The manual's example figure shows one word fewer than its text describes. Sega's own code follows the text <span class="tag disputed">disputed</span> [[discrepancy #7](../appendices/discrepancies.md)].
- **It takes 7 + 3 × length cycles.** A full 256-word block takes about 775 SH-2 clocks, roughly 34 µs. Clearing a whole packed pixel screen of 35,840 words takes about 4.7 ms, close to a third of an NTSC frame [32X-HWM §3.3, FILL function]. That is faster than an SH-2 can write the same words, and the CPU is free in the meantime.
- **Stay off the frame buffer until it finishes.** FEN (bit 1 of the frame buffer control register) reads 1 while a fill is running. Do not read or write the frame buffer until it reads 0. The CPUs can carry on with anything else: SDRAM, registers, the palette <span class="tag manual">manual</span> [32X-HWM §3.2.3; §3.3, FILL function]. FEN also reads 1 for 40 clocks during each DRAM refresh, when access is in fact allowed [32X-HWM §3.3, register latch timing].
- **It fills the back buffer**, the one the CPUs see. Sega's initial program flips FS between its two clears to reach both buffers [VRD-NOTES, ROM].

Mortal Kombat II clears only its 224 visible lines: 161 fills of 256 words from word `$4600`, which is exactly 224 lines of 368 bytes. It skips its guard bands, which are never shown. It waits for FEN to clear after every fill before starting the next, so the Master spends the whole clear polling, about 125,000 clocks, a third of its frame, by the timing above [MK2, SH-2 code at `0x060010DC`]. Starting a fill and then doing other work until FEN clears would get that time back.

**A fill can draw, not just clear.** After Burner Complete draws its sky and sea with auto fill. Its frame buffer uses the 256-word line pitch described below, and for each of the 224 lines it reads a split column from a table and starts two fills: one colour up to the split, the other after it, 160 words in all. When the split falls outside a line, that line gets a single 160-word fill. Moving the split from line to line tilts the horizon as the plane banks, and the same fills clear the whole picture, so no separate clear is needed. That is up to 448 fills per drawn frame, about 110,000 clocks by the formula above (224 × (2 × 7 + 3 × 160) ≈ 110,700 with two fills on every line, ≈ 109,100 with one). The Master waits for each one with a single instruction, `tst.b #2,@(r0,gbr)`, with GBR at `0x20004100` and r0 = 11, which tests FEN in place without loading it [AB32X, SH-2 code at `0x06008280`-`0x060082F6`]. Its title screen, which needs no horizon, clears with one 161-word fill per line instead [AB32X, SH-2 code at `0x0600D0C8`].

Star Wars Arcade goes further and fills its polygons this way. The Slave cuts each flat-shaded polygon into horizontal spans and gives every span wider than a few pixels to the VDP as a fill, writing only the odd pixel at either end itself. For a span of 80 pixels or more it does not wait for FEN: the SH-2's watchdog timer interrupts 512 clocks later, long enough for the widest line, and the CPU sets up the next polygons meanwhile. Shorter fills it waits for ([Software 3D](../techniques/software-3d.md#star-wars-arcade-polygons-as-auto-fills)) [SWA, on-chip code at `0xC0000582`-`0xC0000748`].

A layout that suits the fill is a line pitch of 256 words: line *n* at word 256 × (*n* + 1). Each line then sits in its own 256-word block and can be cleared with one fill. Virtua Racing Deluxe uses this layout, at the cost of some unused space at the end of each line [VRD-NOTES, rendering pipeline].

The upstream PicoDrive emulator writes the whole fill at once. For a fill of more than 8 words it keeps FEN set for 3 + length 68000 cycles, about 9 + 3 × length SH-2 clocks, close to the formula above; a shorter fill never sets it. Code that draws over a fill too early works there and fails on hardware <span class="tag emulator">emulator</span> [PICODRIVE, memory.c].

## The registers at a glance

| 68000 | SH-2 | Register | Bits |
|-------|------|----------|------|
| `$A15180` | `0x20004100` | Bitmap mode | 15 PAL (read only: 0 = PAL, 1 = NTSC), 7 PRI, 6 240-line mode, 1-0 M1 M0 |
| `$A15182` | `0x20004102` | Screen shift control | 0 SFT |
| `$A15184` | `0x20004104` | Auto fill length | 7-0 |
| `$A15186` | `0x20004106` | Auto fill start address | 15-0 |
| `$A15188` | `0x20004108` | Auto fill data | 15-0 |
| `$A1518A` | `0x2000410A` | Frame buffer control | 15 VBLK, 14 HBLK, 13 PEN, 1 FEN (all read only), 0 FS |

Sources: [32X-HWM §3.2.3]. All except FS take effect from the next line. The VDP picks up its registers once per line, during horizontal blanking. A write that lands at that moment may apply to either line, so the manual advises avoiding it [32X-HWM §3.3, register latch timing]. Full bit descriptions are in [System registers](registers.md).

## What to take away

- Think of the screen as 224 pointers. Most effects are cheaper done in the line table than in the pixels.
- Draw into the back buffer through cache-through addresses. Flip FS in vertical blank, and only touch the new back buffer once the flip has happened.
- Write words, not bytes, unless you want zero bytes to be skipped.
- Change the palette in vertical blank. There is only one, shared by both buffers.
- Clear with auto fill in 256-word blocks, and keep off the frame buffer until FEN is 0.

## Open questions

- How many words the frame buffer write buffer holds on production units ([discrepancy #4](../appendices/discrepancies.md)).
- What exactly the VDP shows for a line whose 320 pixels run past the end of the buffer.
- Measured auto fill time on hardware, and whether "length" in the manual's formula is the register value or the number of words.

## Sources

- [32X-HWM](../appendices/bibliography.md#32x-hwm): §3.1, §3.2.2, §3.2.3, §3.3 (VDP, Figures 3.8-3.14, register latch timing), §4.4, §5.3
- [32X-HWI](../appendices/bibliography.md#32x-hwi): general target items 4-6; target version differences
- [32X-TI](../appendices/bibliography.md#32x-ti): item 14
- [32X-OV](../appendices/bibliography.md#32x-ov): dual frame buffers, line start table
- [SH7604](../appendices/bibliography.md#sh7604): §7.2.2 bus size
- [VRD-NOTES](../appendices/bibliography.md#vrd-notes): rendering pipeline, frame swap, retail ROM, BIOS dumps, PicoDrive
- [MK2](../appendices/bibliography.md#mk2): SH-2 code at `0x0600051A`, `0x06000608`, `0x06001088`-`0x060010DC`, `0x060016AC`, `0x06002CEC`, `0x06004CC0`
- [AB32X](../appendices/bibliography.md#ab32x): SH-2 code at `0x06006778`-`0x06006A44`, `0x06008280`-`0x060082F6`, `0x0600D0C8`
- [AU-NOTES](../appendices/bibliography.md#au-notes): frame buffer as measured, palette budget, 32X pitfalls
