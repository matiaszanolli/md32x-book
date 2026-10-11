# Case study: the ECCO CinePak demo

*ECCO the Dolphin CinePak Demo* is one of Sega's "Mars Sample Programs", dated 1994, from a 3 MB development cartridge that was never sold [ECCO]. It plays six seconds of movie, 180 pictures of 256 × 160 pixels in 15-bit colour: the title of *Ecco the Dolphin* fading up out of black over a sea at sunset. The movie is compressed with Cinepak, a video format that codes each picture as lookups into tables of small pixel blocks, and the 32X's Master SH-2 decodes it.

It is not a game but a video player, which makes it useful in a different way from the other case studies. The format is public, so every byte of the stream can be checked against a description written by someone else; the decoder is small enough to read whole; and one SH-2 does all of it, so there is no pipeline or bus fight to untangle. This chapter follows one picture from the cartridge to the screen, counts what it costs, and then looks at what the design gets right and what it leaves unused. Cinepak itself is in [Compression and decompression](../techniques/compression.md#cinepak-video-as-vector-quantisation).

## How far the evidence goes

The program was read by disassembly from the cartridge dump, whose header checksum is zero (the boot ROM skips that check) [ECCO]. Two further checks make what it does certain, not just plausible:

- **The decoder was run on the cartridge's own bytes.** A small SH-2 interpreter written for this book ran the frame walker, the codebook converter and the block loop over the 180 pictures. Its output equals what PicoDrive puts on the screen for every distinct picture of a 1,500-frame run, pixel for pixel: 676 pictures, none different <span class="tag emulator">emulator</span> [ECCO, headless run of 10 October 2026; BOOK-TOOLS, eccosim.py].
- **An independent decoder agrees.** A second decoder, written from [Ferguson's stream description](../appendices/bibliography.md#cinepak-td) and reading only the stream, gives the same 180 pictures bit for bit when it uses the colour conversion the SH-2 code uses [BOOK-TOOLS, ecco_cinepak.py].

Timings are the weak part. PicoDrive charges every SH-2 instruction its base clocks and nothing for memory ([In emulators](../sh2/pipeline.md#in-emulators)), so its run shows only that the demo keeps a steady rate. The instruction and memory-access counts below are exact, because the interpreter counted them. Turning them into clocks uses the manual's access costs and comes out as a range, tagged <span class="tag manual">manual</span>. No console has run the demo for this book. The cost estimate also assumes the SH-2 cache is on, as the boot ROM leaves it ([What the boot ROM leaves you](../sh2/cache.md#what-the-boot-rom-leaves-you)); PicoDrive's stand-in start never enables it. All figures are NTSC: 60 frames a second, 384,000 SH-2 clocks a frame.

## The movie in the cartridge

| Cartridge offset | What |
|------------------|------|
| `$000000`-`$00BFFF` | 68000 side: Sega's initial program, the demo's own 68000 code and its data, among them the SEGA logo |
| `$00C000`-`$015FFF` | SH-2 program, 40,960 bytes: a Master image and a Slave image, each a linked copy of the same library |
| `$020000`-`$235B03` | The movie, 2,185,988 bytes: 69% of the cartridge |

Sources: [ECCO, header and user header; SH-2 code]; [Boot, security code and initial program](../32x/boot.md).

The movie is a Sega FILM file, the container of Sega's `.cpk` movies [SEGA-FILM]. Its header, `$B84` bytes, is the `FILM` signature, a 20-byte `FDSC` chunk and a `STAB` sample table. The `FDSC` says only `cvid` (Cinepak), 160 high and 256 wide. This short form has no audio fields. The `STAB` gives a time base of 600 ticks a second and 180 entries of 16 bytes: offset, length and two info words. In every entry info 2 is 20 ticks, a thirtieth of a second, and the info 1 values count up in steps of 20 with the top bit clear, which marks each one as a key frame, a picture coded without reference to any other [SEGA-FILM] [ECCO, header and sample table].

**There is no sound.** Audio samples are marked by an info 1 of all ones, and none of the 180 entries is. They also run on from one another with no gaps, so the file is 180 pictures and nothing else. `ffprobe` nevertheless lists a 22,050 Hz mono audio stream and a duration of 0.3 seconds, where the table adds up to six seconds of video. The file holds no audio samples to give it that stream, and ffmpeg's reason for listing one is not checked here [FFMPEG]. Someone who trusted that summary, or who took the table's 16-byte entries for interleaved audio and video, would look for a sound track the cartridge does not have. The player's own walker settles it: it skips audio entries, and finds none to skip.

A picture, as stored, is one sample:

| Part | Bytes | What |
|------|-------|------|
| Sample header | 16 | The Cinepak frame header (10 bytes: flags, a 24-bit length that is 8 less than the sample's, width, height, one strip) and six more bytes, `fe 00 00 06 00 00` in every picture, that the decoder skips |
| Strip header | 12 | Type `0x1000` (intra), then the area it covers: rows 0-160, columns 0-256 |
| V4 codebook chunk, `0x2000` | 4 + 6 per entry, padded to a multiple of 4: 1,540 for 256 entries | The pixel blocks the picture is built from |
| V1 codebook chunk, `0x2200` | 4 | Empty, in every picture |
| Vector chunk, `0x3000` | 4 + 10,560 (+ 4 in 141 pictures) | 80 flag words of 32 bits, 320 bytes, with 10,240 index bytes between them |

Sources: [CINEPAK-TD]; [ECCO, all 180 samples parsed].

The average picture is 12,128 bytes: 2.37 bits for each of its 40,960 pixels, against 81,920 bytes if stored raw in 15 bits, 6.8 times smaller. At the file's own 30 pictures a second that is about 364,000 bytes a second. Of those bytes, 84% are the index bytes, 13% the codebook and 2.6% the flags.

**What the encoder chose is narrower than what the format allows.** All 460,800 blocks of the movie are V4: each is four index bytes, each index picking a 2 × 2 pixel entry from the picture's own 256-entry codebook, and not one block is V1, the cheaper form that stretches one entry over the whole block. Every picture is an intra picture with a codebook built for it alone, and the codebooks are nearly full: on average 254 of the 256 entries are used. In effect the movie is a 2 × 2 vector quantiser at 8 bits for 4 pixels, with a flag bit for each 4 × 4 block that never varies. The first and last pictures are entirely black, so the movie loops without a jump.

## What the decoder handles, and what the movie uses

The decoder is a general Cinepak decoder, not one written for this movie, and it is about 1.7 KB of SH-2 code. It replaces codebooks whole or entry by entry, and it can leave a block unchanged. The table lists the chunk types of [Ferguson's description](../appendices/bibliography.md#cinepak-td) and what happens to each [ECCO, SH-2 code at `0x060010C4`-`0x0600137E`, dispatch table at `0x060011A4`]:

| Chunk | Meaning | Decoder | Movie |
|-------|---------|---------|-------|
| `0x2000` | V4 codebook, whole | Converts all 256 entries | Every picture |
| `0x2100` | V4 codebook, selected entries (a 32-bit mask says which) | Converts the marked ones | No |
| `0x2200` | V1 codebook, whole | As `0x2000`, into the V1 half | Empty chunk |
| `0x2300` | V1 codebook, selected entries | As `0x2100` | No |
| `0x3000` | Vectors, intra: one flag bit a block, V4 or V1 | Routine at `0x060002B4` | Every picture |
| `0x3100` | Vectors, inter: a flag bit says "unchanged", a second says V4 or V1 | Routine at `0x060003EC`: an unchanged block leaves the staging buffer as it is | No |
| `0x3200`, `0x2400`-`0x2700`, and any other | V1-only vectors, 8-bit grey codebooks | Skipped by their length | No |

The inter routine was read and not run, because no picture reaches it. The strip handler steps its output down by each strip's height, so it is written for movies with several strips, though this one has a single strip.

## One picture, from cartridge to screen

**1. The main loop starts a pass over the movie.** It calls the frame walker with a staging buffer at `0x06010000`, a row size of `0x200` bytes (256 pixels) and the address of the movie in the cache-through cartridge window, `0x22020000`. When the walker returns, it starts again, so the movie loops for ever [ECCO, SH-2 code at `0x060001D4`-`0x060001E2`].

**2. The walker finds the pictures in the container itself.** It reads the header size from the stream's own bytes, steps over the `FDSC` by its length, and reads the entry count from the `STAB`. For each entry it skips those marked as audio, adds the entry's offset to the end of the header and hands that address to the strip handler. It reads no other word of the entry: the length is not used, and neither are the time stamps. When the strip handler returns without error, the walker calls the copy routine [ECCO, SH-2 code at `0x06001788`-`0x06001814`].

**3. The strip handler walks the chunks.** It takes the strip's corners, loops over the chunks of the strip, and jumps through a table on each chunk's type. Its two codebooks live in a 4 KB block of the walker's stack, V4 in the first half and V1 in the second, 256 entries of 8 bytes each in each half. The Master's stack starts at the top of SDRAM, `0x06040000` ([Boot](../32x/boot.md#each-sh-2-at-its-entry-point)) [ECCO, SH-2 code at `0x060010C4`-`0x0600137E`, `0x06001798`].

**4. The codebook converter turns each 6-byte entry into four pixels.** An entry in the stream is four luma bytes, one per pixel, and two signed chroma bytes shared by the four. The converter writes four 15-bit pixels, 8 bytes, so the block loop can copy pixels and never has to compute them. For one pixel, with *u* the fifth byte of the entry and *v* the sixth [ECCO, SH-2 code at `0x06000F5C`-`0x0600100E`]:

| Pixel channel | Value |
|---------------|-------|
| Red (bits 0-4) | min(max(*y* + 2*v*, 0), 255) ÷ 8 |
| Green (bits 5-9) | min(max(*y* − *u* − ⌊*v* ÷ 2⌋, 0), 255) ÷ 8 |
| Blue (bits 10-14) | min(max(*y* + 2*u*, 0), 255) ÷ 8 |

It does this for 256 entries whatever the chunk holds, reading on past a short chunk, which is harmless here because a picture uses 254 entries on average and no block ever names an entry the chunk lacks. It costs about 66,600 instructions a picture, 260 an entry and 65 a pixel.

**Sega's green is not the usual green.** The table has the usual red and blue. The usual green is *y* − *u* ÷ 2 − *v* [CINEPAK-TD], and ffmpeg's decoder gives exactly that. The SH-2 code halves the sum 2*u* + *v* instead, so *u* and *v* swap their weights. Over the 180 pictures the demo's green is brighter than ffmpeg's by 8.5 levels of 255 on average, 24.7 at the worst, and equals it in 23% of the values; red and blue match in every one <span class="tag disputed">disputed</span> ([discrepancy 49](../appendices/discrepancies.md)). The result is a yellower, greener sunset than the one the stream describes. Whether Sega meant it is not recorded.

**5. The block loop paints 4 × 4 blocks.** It keeps four row pointers, one for each pixel row of a block, and a 32-bit flag word that it refills from the stream four bytes at a time, most significant bit first. For a V4 block (flag bit set) it reads four index bytes. Each index selects an 8-byte codebook entry, whose two longwords go to two adjacent rows: the first index fills the block's top left 2 × 2 pixels, the next the top right, then bottom left and bottom right. A V1 block (bit clear) reads one index and writes each of the entry's four pixels as a solid 2 × 2 square. A V4 block takes 52.6 instructions on average, 3.3 for each pixel, with four byte reads from the cartridge, eight longword reads from the codebook and eight longword stores to the staging buffer, and no multiply anywhere [ECCO, SH-2 code at `0x060002B4`-`0x060003DA`].

**6. The copy routine puts the picture on screen.** It copies 152 rows of 512 bytes from the staging buffer to the frame buffer at `0x24002A40`, a longword at a time, with five `nop`s after each store, skipping the 128 bytes that finish each 640-byte frame buffer row. The last 8 of the picture's 160 rows are never shown. Then it waits for the vertical-blank bit, inverts the frame buffer select bit, and returns [ECCO, SH-2 code at `0x06000220`-`0x06000272`]. Writing the select bit during blanking makes the swap happen at once ([Frame buffers and the FS bit](../32x/vdp.md#frame-buffers-and-the-fs-bit)).

The picture sits in a direct-colour frame buffer whose line table the start-up code builds with 12 border lines at the top, 200 lines of picture at 640 bytes each and 12 border lines at the bottom, the border lines all pointing at the first, black line: a 224-line screen from the 204 unique lines a direct-colour buffer has room for ([Direct colour](../32x/vdp.md#direct-colour)). The movie's top left is 16 lines and 32 pixels into the 320-pixel picture, which puts it at column 32, line 28 of the screen, with the 32X layer black around it [ECCO, SH-2 code at `0x06000120`-`0x060001D2`].

## Who does what

| CPU | Job |
|-----|-----|
| 68000 | Draws the SEGA logo on the Mega Drive VDP and waits with timed delays, about 140 frames in PicoDrive. Then it waits for the SH-2s' `M_OK` in the communication ports, clears them to start the SH-2s, and spins in a branch-to-self loop copied into work RAM at `$FF8000` |
| Master SH-2 | Everything else: container, codebooks, blocks, copy, flip |
| Slave SH-2 | Waits for the same communication word to read 0, then spins in a branch-to-self for ever |

Sources: [ECCO, 68000 code at `$0820`-`$0858`, `$0868`-`$0956`; SH-2 code at `0x06000120`-`0x0600012C`, `0x06008120`-`0x0600812E`]; [The handshake into your code](../32x/boot.md#the-handshake-into-your-code).

The 68000's loop in work RAM is the right place for it. From the end of the logo it runs nothing from the cartridge but three instructions of Sega's initial program once a frame, so it takes almost none of the bus time the Master spends streaming the movie <span class="tag emulator">emulator</span> ([Living with bus contention](bus.md)) [ECCO, PicoDrive profile of 1,500 frames: three addresses near `$0005F6`, about 1,390 runs each]. With the Slave parked, the Master never shares the bus with the other SH-2 either.

## Where the time goes

**The rate is a result of the cost, not a setting.** In PicoDrive the picture on the screen changes every second frame: of 676 changes after frame 140 in a 1,500-frame run, 671 came two frames after the one before, 3 came four frames after it (at the loop point, where the last and first pictures are both black and the screen does not change) and 1 five (the start) <span class="tag emulator">emulator</span> [ECCO, headless run of 10 October 2026]. That is 30 pictures a second, the rate the file's time stamps give. But the walker never reads those, and nothing in the program counts frames. Each picture is decoded, copied, held until the vertical blank, and shown, so a picture takes as many frames as its cost needs: one if the work fits in about 384,000 clocks, two if it fits in about 768,000, and so on, give or take the vertical blank the wait ends in.

What a picture costs, by the interpreter's count: the mean over pictures 1 to 179, each counted from the start of the previous picture's copy to the start of its own, so one decode and one copy:

| Part | Instructions | Clocks by Hitachi's table | Share of clocks |
|------|--------------|---------------------------|-----------------|
| Copy to the frame buffer | 195,197 | 234,108 | 51% |
| Block loop | 134,673 | 147,312 | 32% |
| Codebook conversion | 66,568 | 70,899 | 16% |
| Walker and chunk handler | 2,548 | 3,086 | 1% |
| Total | 398,986 | 455,405 | |

The clocks are the instruction counts at Hitachi's issue times, with no memory waits and no stalls [ECCO; BOOK-TOOLS, eccosim.py]. That is the nearest to what PicoDrive charges: 455,000 clocks, 1.19 frames, which is why it shows two frames a picture. A console adds two things. A load whose result the next instruction uses costs one more clock ([Using a load's result too soon](../sh2/pipeline.md#using-a-loads-result-too-soon)), and 52,100 of a picture's loads are used at once, 31,100 of them in the block loop and 19,500 in the copy. And the memory costs something, for these accesses:

| Access | Per picture | Cost per access, from the manual |
|--------|-------------|----------------------------------|
| Read from the cartridge, cache-through | 12,128 bus cycles: 12,103 byte reads, 5 halfwords and 10 longwords | 8 to 17 clocks |
| Longword stores to SDRAM | 21,789, with 1,028 word stores | 4 clocks a longword |
| Longword stores to the frame buffer | 19,456 (77,824 bytes) | Two word writes of 3 to 5 clocks |
| Longword reads of the staging buffer | 19,456: 4,864 cache line fills | 12 clocks a fill |

Sources: [ECCO; BOOK-TOOLS, eccosim.py]; costs from [What a 16-bit bus costs](../sh2/bsc.md#what-a-16-bit-bus-costs) and [Writing from the SH-2](../32x/vdp.md#writing-from-the-sh-2). The codebook reads, about 20,500 longwords a picture, mostly hit the cache. The converter's stores go to memory without loading a line, so each of the codebook's 128 lines misses once, about 1,500 clocks, and stays: the stream is read cache-through and the stores load nothing, so nothing else the block loop does disturbs the cache.

Adding the extra clocks to the 455,405:

| | Low | High |
|---|-----|------|
| Instruction clocks | 455,000 | 455,000 |
| Loads used at once | 52,000 | 52,000 |
| Cartridge reads, 12,128 at 8 or 17 clocks, less the instruction's own | 85,000 | 194,000 |
| Staging buffer line fills | 54,000 | 54,000 |
| SDRAM stores, if the CPU waits for each | 0 | 66,000 |
| Frame buffer stores, if the CPU waits for each | 0 | 136,000 |
| **Total** | **646,000, 1.7 frames** | **957,000, 2.5 frames** <span class="tag manual">manual</span> |

The low column assumes the write buffer hides every store; the high one makes each store cost its whole bus time. The frame buffer figure is the book's rule for back-to-back word writes, 3 clocks for the first half of a longword and 5 for the second ([Living with bus contention](bus.md#moving-data-without-paying-twice)). **The manual cannot say whether a console shows this movie at 30 pictures a second or at 20.** The line between two and three frames is about 768,000 clocks, give or take the length of a vertical blank, and the range runs across it. A count of the frame buffer select bit over 60 frames on a console would settle it.

## What it does well

- **It converts the table once and copies afterwards.** The conversion work is 1,024 pixels a picture, one for each pixel of the 256 entries, 66,600 instructions. Converting every pixel of the picture instead would take 40,960 conversions, about 2.7 million instructions at the same 65 a pixel, nearly seven times everything the demo does now. The block loop then does no arithmetic at all, only lookups and copies ([Compression and decompression](../techniques/compression.md#cinepak-video-as-vector-quantisation)).
- **It keeps the stream out of the cache.** It reads the movie through the cache-through window, so 2 MB of sequential data never pushes the decoder's code and codebook out of the cache. The price, a bus cycle for every byte, is in [Cache discipline](cache.md#data-from-outside). The copy does flush the cache once a picture, by reading 78 KB of staging buffer through it, and the next picture refills its code and codebook, a few thousand clocks.
- **The staging buffer in SDRAM holds the last picture.** If the movie had inter pictures, an unchanged block would be left alone, and the picture would be the one before. The frame buffer's two pages could not do that: the page being drawn is two pictures old.
- **It leaves the other processors alone.** A parked Slave and a 68000 spinning in work RAM add no bus contention to a measurement or to the real thing.

## What it leaves on the table

Each of these comes from the counts above and the manual's costs; none has been run.

- **Pace by the time stamps.** The player counts nothing. A decoder 20% faster would run in PicoDrive at 455,000 × 0.8 = 364,000 clocks, inside one frame, and show the movie at 60 pictures a second, twice its intended speed. On a console the figures above could as easily give 30 as 20. The file says what the rate should be; waiting for a fixed number of vertical blanks would hold it there.
- **Decode in place.** The block loop takes the row size as a parameter, 512 bytes here, but its step from one row of blocks to the next is a constant, `0x600`, three rows of 512 bytes, in a literal at `0x060003E8`. For the frame buffer's 640-byte rows the parameter would be 640 and the constant `0x800`, and the destination `0x24002A40`. That drops the whole copy, 234,000 instruction clocks and 54,000 of cache fills, and moves 20,486 stores from SDRAM, at 4 clocks, to the frame buffer, at 6 to 8. The cost is that the movie could have no inter pictures: the back page is two pictures old.
- **Drop the `nop`s.** The five after every store add 97,280 clocks a picture. By the rule above they gain nothing back ([Living with bus contention](bus.md#what-each-program-did)).
- **Read the stream in longwords.** Every byte of the stream is a cartridge cycle of 8 to 17 clocks, 12,128 of them. In this movie the four index bytes of a V4 block always sit aligned together, so one longword read, two bus cycles, would replace four. That would save about 5,300 bus cycles, 42,000 to 90,000 clocks. A general decoder cannot count on it, because a V1 block is one byte and breaks the alignment.
- **Use the Slave.** A movie encoded as two strips could give each SH-2 one strip, since each strip carries its own codebooks and the decoder already steps its output by the strip's height. This movie has one strip, and the two SH-2s share a bus whose contention nothing here measures.

## What the design teaches

- **Convert the table, not the picture.** When many things share a small table of values, apply the expensive transformation to the table once and make the per-pixel work a copy.
- **Keep the cartridge to the SH-2 that is streaming from it.** Spin the 68000 in work RAM, as this demo does, once it has nothing to do ([Living with bus contention](bus.md)).
- **A rate that nothing sets is a result.** The demo's 30 pictures a second comes from its cost sitting between one and two frames. Change the cost, or the console's timing, and it changes with it.
- **Check a decoder against a second one.** Decoding the same stream with ffmpeg showed in one run that the demo's green is not the format's green. A match of red and blue made the difference stand out: only one channel was off.
- **Read the container yourself.** A tool's summary of a file, here a 22,050 Hz audio stream that does not exist, is what the tool assumed. The sample table, entry by entry, shows there is none.
- **Run the code, if you can read it.** A colour conversion read from disassembly is easy to summarise wrongly, in one term of one channel. Running the decoder over its own data and comparing the pictures with another decoder's settles it.

## Open questions

- Does a console show the demo at 30 pictures a second, 20, or something that varies? The range above spans the answer. Counting the frame buffer select bit's flips over 60 frames settles it.
- Is the green weighting deliberate? Sega's encoder may have written chroma for it. Another Sega FILM movie decoded with both formulas would show which one gives sensible colours.
- Why five `nop`s after each store, and why does the copy stop 8 rows short of the picture's 160? Nothing in the ROM says.
- With the boot ROMs PicoDrive shows a black screen instead of the movie ([ECCO](../appendices/bibliography.md#ecco)). The cost bracket assumes the cache is on, as the boot ROM leaves it on a console. PicoDrive's run has no cache, and nothing here shows why the demo is black when the boot ROMs run.

## Sources

- [ECCO](../appendices/bibliography.md#ecco):
  - SH-2 code at `0x06000120`-`0x060001E2` (start-up and main loop), `0x06000220`-`0x06000272` (copy and flip), `0x060002B4`-`0x060003DA` and `0x060003EC`-`0x06000546` (block loops), `0x06000F5C`-`0x0600100E` (codebook conversion), `0x060010C4`-`0x0600137E` (strip and chunk handler, table at `0x060011A4`), `0x06001788`-`0x06001814` (walker), `0x06008120`-`0x0600812E` (Slave).
  - 68000 code at `$0820`-`$0858` and `$0868`-`$0956`.
  - The movie: header, sample table and all 180 samples parsed; V4 and V1 block counts; codebook sizes.
  - A run of the decoder in an SH-2 interpreter, compared with PicoDrive's screen over 1,500 frames, and with a second decoder and ffmpeg (10 October 2026).
- [BOOK-TOOLS](../appendices/bibliography.md#book-tools): eccosim.py, ecco_cinepak.py.
- [CINEPAK-TD](../appendices/bibliography.md#cinepak-td): chunk types, flag bits, block layout, colour conversion.
- [SEGA-FILM](../appendices/bibliography.md#sega-film): container layout.
- [FFMPEG](../appendices/bibliography.md#ffmpeg): reference decode.
- [PICODRIVE](../appendices/bibliography.md#picodrive): the run and the screen output.
- [32X-HWM](../appendices/bibliography.md#32x-hwm): §4.4, access times.
- The chapters linked above, which cite each technique in detail.
