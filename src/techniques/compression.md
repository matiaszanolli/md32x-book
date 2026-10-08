# Compression and decompression

A Mega Drive cartridge holds a few megabytes, and a 32X game's art is 8 bits a pixel instead of 4, so it needs twice the space for the same picture. Almost every game in the sources compresses something. This chapter covers the formats they use: LZ for general data, run-length coding for sprites, and fixed-rate packing for sound. It also covers where each one is decompressed and what that costs on each CPU.

Four questions decide the format:

1. **Which CPU decompresses it?** The 68000 has 16-bit registers and slow shifts; an SH-2 has 32-bit registers and a cache, and can read the cartridge directly.
2. **Where does the output go?** RAM is easy. VRAM and the 32X frame buffer are not: each is behind a port or has write rules of its own.
3. **Is it decoded once, or every time it is drawn?** A level loaded once can use a slow, tight format. A sprite drawn every frame needs a format the drawing loop can read directly, or a cache of decoded copies.
4. **Must it keep pace with something?** Sound is decoded inside an interrupt, sample by sample, and needs a format whose cost per sample is fixed.

| Format | Game | Decoded by | Into | Notes |
|--------|------|------------|------|-------|
| Koei's LZSS, bit-packed lengths and distances | Aerobiz Supersonic | 68000 | Work RAM, or VRAM directly | 4 KB window; in Aerobiz Ultimate, moved to the Master SH-2 |
| Rob Northen's ProPack (RNC), method 2 | Mortal Kombat II | Master SH-2 | SDRAM | 47 files, packed to 36% of their size |
| ProPack, method 1 (adds Huffman codes) | Mortal Kombat II | 68000 | Work RAM, or VRAM through a 32 KB ring | 33 files of Mega Drive graphics, packed to 48% |
| Jaguar Doom's LZSS, byte-aligned | d32xr | SH-2 and 68000 | SDRAM, a ring buffer, or work RAM | Resumable; streams pictures and music through a small window |
| Colour and run bytes | Mortal Kombat II | Master SH-2 | Frame buffer, drawn directly | 6+2 or 4+4 bits a byte |
| Signed control byte, runs of zeros | After Burner Complete | Master SH-2 | A cache in SDRAM | Decoded once per shape, then scaled from the cache |
| Packed PCM, codebook PCM | Mortal Kombat II, Star Wars Arcade | Slave SH-2, in the PWM interrupt | PWM | Fixed cost per sample |

## LZ: copy what came before

An LZ decompressor rebuilds the output from two kinds of item. A **literal** is one byte copied from the input. A **back-reference** says "copy *n* bytes from *d* bytes back in the output". Text, tile maps and graphics repeat themselves, so most of the output comes from back-references. LZSS is the common variant in which one flag bit before each item says which kind it is. The **window** is how far back a reference can reach. The decompressor must keep at least that much of its own output where it can read it, so the window, not the size of the output, sets the memory it needs.

The copy runs forwards, a byte at a time, so a reference may overlap the bytes it is producing: a distance of 1 with a length of 100 repeats one byte 100 times. That is how LZ formats encode runs, and it is why a copy routine that moves whole words must check the distance first.

### Koei's LZSS (Aerobiz Supersonic)

Koei's format squeezes the lengths and distances into variable-length bit codes, and mixes three kinds of data into one input stream [AB-DISASM, disasm/modules/68k/boot/EarlyInit.asm `LZ_Decompress`, `$003FEC`-`$00423F`; AU-NOTES, tools/lz_decompress.py]:

- **Flags.** A control byte gives the next eight flags, top bit first. A 1 means a literal, a 0 a back-reference. The routine keeps the control byte in RAM and shifts it by adding it to itself, which puts the next flag in the top bit.
- **One stream.** Control bytes, literal bytes and 16-bit words of length and distance bits all come from the same pointer, in the order the decoder needs them. The bit words are stored low byte first and read a byte at a time, so the stream needs no alignment. A new word is read only when a code needs more bits than are left, so the compressor must put each one exactly where the decoder will run out.
- **Bit reader.** It keeps a 16-bit window of upcoming bits. The decoder compares the whole window with thresholds to find which code is there, then removes that many bits in one call, shifting in new bits through a table of 17 masks at `$04684C`. A back-reference makes at most two calls, one for the length and one for the distance. A literal makes none.
- **Lengths** use a gamma code: a run of zeros says how many value bits follow.

  | Code | Bits | Bytes copied |
  |------|------|--------------|
  | `1` | 1 | 2 |
  | `01x` | 3 | 3-4 |
  | `001xx` | 5 | 5-8 |
  | `0001xxx` | 7 | 9-16 |
  | … one more zero, one more value bit … | | … |
  | `0000001xxxxxx` | 13 | 65-128 |
  | `0000000` then 7 bits | 14 | 129-255 |

  The last row adds `$80` to its 7 bits. With all seven set the result is `$FF`, which is the end of the data. Short matches, which are the most common, get the shortest codes.
- **Distances** use nine ranges, each with a fixed number of bits: 0-3 in 6 bits, 4-7 in 7, 8-31 in 8, 32-127 in 9, 128-255 in 10, then one more bit for each doubling up to 2,048-4,095 in 14. The copy starts *d* + 1 bytes back, so references reach 1 to 4,096 bytes. The window is the output buffer itself; there is no separate history buffer.

Both codes are complete: every bit pattern decodes to something, so no code space is wasted.

The game calls this routine from 123 places, nearly always to unpack graphics into a buffer at `$FF1804` and then DMA them to VRAM [AB-DISASM, EarlyInit.asm; AU-NOTES, ROADMAP.md U-046]. The largest block is 27,872 bytes. Two of the project's own documents give 92 and 86 call sites; both miss calls written as raw data words.

### Decompressing straight into VRAM

Aerobiz Supersonic also has a second copy of the same decoder that writes to VRAM instead of RAM [AB-DISASM, disasm/modules/68k/game/DecompressVDPTiles.asm, `$004342`-`$0045B1`]. VRAM serves as both output and window, so no RAM buffer is needed at all. The cost is in how it reaches VRAM:

- **Writing a byte.** VRAM is accessed in words through the data port, so each output byte is a read-modify-write of its word: set a read address, read the word, replace the high or low byte depending on whether the address is even or odd, set a write address, write the word back. That is four port instructions and six 16-bit bus transfers per byte [AB-DISASM, vdp/VRAMWriteExtended.asm, `$0042F0`].
- **Reading a back-reference** sets a read address and reads a word, two more port instructions per byte [AB-DISASM, vdp/VRAMWriteWithMode.asm, `$0042BA`].
- **Interrupts are masked around every access**, so the vertical interrupt cannot change the VDP's address between the halves of the operation ([The VDP remembers half a command](../megadrive/vdp.md#the-vdp-remembers-half-a-command)).

It is used once, during the intro, to load the font: 3,866 bytes unpacked to 10,112 bytes (316 tiles) at VRAM `$4000`, with the display and the vertical interrupt switched off around it [AB-DISASM, sound/ClearSoundBuffer.asm, GameSetup1.asm]. That is the right use for a slow path: once, early, and when RAM is short. (The disassembly's names for these routines describe other things; the labels above are the ones it uses.)

### ProPack on the SH-2 (Mortal Kombat II)

Mortal Kombat II packs its SH-2 data with Rob Northen's ProPack, a commercial packer of the time. Each file starts with an 18-byte header that begins `RNC` and a method number, followed by the unpacked and packed sizes. The cartridge holds 47 method-2 files, 1.09 MB unpacked and 396 KB packed, 36% of their size; the largest unpacks to 99,132 bytes [MK2, ROM scan for `RNC\x02` headers]. The Master unpacks them straight from the cartridge into SDRAM with a 398-byte routine called from about 30 places [MK2, SH-2 code at `0x06002DF4`-`0x06002F84`]:

- It skips the header. Sizes and checksums are not checked; the data is trusted.
- **Flags and codes share one bit stream**, top bit first, refilled a byte at a time. Literal and length bytes come from the same pointer between refills.
- **Items:** a single literal byte; a block of literal bytes, (4-bit count + 3) × 2 of them, copied two at a time; or a back-reference of 2 or more bytes, with longer lengths given by a whole byte plus 8. The distance is a few bits for the high part plus a whole byte for the low part.
- **A length byte of 0** ends a chunk, and one more flag says whether another chunk follows.

### ProPack on the 68000 (Mortal Kombat II)

The other 33 ProPack files in the cartridge are method 1: 566 KB unpacked, 273 KB packed, 48% [MK2, ROM scan for `RNC\x01` headers]. Method 1 adds **Huffman codes**, which give common values short bit patterns. Each chunk of the file starts with its own code tables. The SH-2 program has no method-1 unpacker. The 68000 has three, all of which rebuild three 128-byte decoding tables on the stack for each chunk [MK2, 68000 code at `$00CFF8`, `$00D186`, `$0292F4`]:

- **Into work RAM** (`$00CFF8`, and `$0292F4`, which first moves the packed data out of the way if it overlaps the output). Two of the three callers of `$0292F4` check for the four bytes `RNC`, 1 first, so the same call takes a packed or an unpacked file. Either way, the result is queued as a VDP DMA from work RAM [MK2, 68000 code at `$028F38`-`$028FCA`].
- **Straight to VRAM** (`$00D186`). The caller sets a VRAM write address, and the routine keeps the last 32 KB of its output in a ring buffer at `$FF0000` as its window. Each time a word is complete, it writes that word to the VDP data port. A file can be any length; only the window needs RAM.

The VRAM routine handles the largest files. Ten loaders, reached through a table of ten pointers at `$008E5E` indexed by the word at `$FFAAC0`, each stream one file of 33 to 47 KB to VRAM and unpack a second file of 9 to 14 KB into work RAM [MK2, 68000 code at `$008E52`-`$008E5C`, `$008E86`, `$0096DC`-`$009704`]. These are presumably the arenas, which the Mega Drive draws ([Using both video chips at once](../patterns/layering.md#what-the-shipped-games-put-where)). Unpacked at `$FF0000`, a 47 KB file would run past `$FF8818`, where the game keeps variables. The ring buffer is what lets it be unpacked at all.

So Mortal Kombat II splits its packed data by the CPU that uses it: method 2 for what the SH-2 draws, method 1 for the Mega Drive's tiles. A Mega Drive game ported to the 32X can keep its 68000 unpacker for Mega Drive graphics in the same way.

### d32xr's LZSS: byte-aligned and resumable

d32xr uses the LZSS format of Jaguar Doom, which keeps everything in whole bytes [D32XR, liblzss/lzss.c, liblzss/lzss.h]:

- A flag byte gives eight flags, lowest bit first. A 1 means a back-reference, the reverse of Koei's.
- With a window of 4 KB, a back-reference is two bytes: 12 bits of distance and 4 of length, for lengths 2 to 16. With a larger window it is three bytes: 16 bits of distance and 8 of length, for lengths 2 to 256. A length field of 0 ends the data.
- **The decoder can stop and resume.** `lzss_read` produces at most a requested number of bytes into a ring buffer, whose size is a power of two of at least 4 KB, and saves its state, including a back-reference stopped half-way. The caller can take a picture or a music stream a piece at a time, in a fixed amount of memory, however large it is.
- **Copies move words when they can.** When the source and destination are both even or both odd, the copy moves 16 bits at a time. That is safe for every distance it allows: the shortest reference with the same alignment starts two bytes back, so every word it reads was finished before it is read.

How d32xr uses it:

- **Lumps.** Doom keeps its data as lumps, named blocks in one archive file (the WAD). Each lump stored compressed has the top bit of the first character of its name set. An uncompressed lump is used where it lies in the cartridge, with no copy. A compressed one is unpacked whole, either into a block of the zone ([Memory](memory.md)) or, while a level is being set up, into the frame buffer that is not on screen. The frame buffer is cleared first. A byte write of 0 is still ignored there, but the byte it should have written is already 0, so the output comes out right [D32XR, w_wad.c, marsnew.c `I_TempBuffer`].
- **Pictures, a line at a time.** The title and menu pictures are unpacked through a 4 KB ring buffer on the stack, one line's width at a time, and each line is copied into the frame buffer as it appears. A full-screen picture needs 4 KB of memory, not 70 KB [D32XR, marsdraw.c `DrawJagobjLump`].
- **Music.** The 68000 unpacks the recorded register stream into a 32 KB ring in work RAM and feeds the Z80 from it ([d32xr: decompress on the 68000, replay on the Z80](../megadrive/sound.md#d32xr-decompress-on-the-68000-replay-on-the-z80)) [D32XR, src-md/vgm.c].

## Reading bits on each CPU

A decoder spends much of its time pulling single bits out of a byte. The two CPUs do this differently:

- **68000.** Add a register to itself (`ADD.B D0,D0`) and the top bit lands in the carry and X flags, ready for `BCS` or `ADDX`. Shifts by more than one bit are slow: 6 + 2*n* clocks for *n* places [M68K-UM §8.6]. Koei avoids shifting a bit at a time by comparing the whole 16-bit window against thresholds and removing a whole code at once.
- **SH-2.** `SHLL` moves the top bit into T. `BT`/`BF` branch on it, and `ROTCL` adds it to a value being built up. Mortal Kombat II keeps the current byte in the top 8 bits of a register, so a 32-bit shift brings out its top bit, and a counter says when to load the next byte. The refill, four instructions, is written out in full at each of the twenty-odd places a bit is read, not called. That makes the routine longer and saves a call and a return for each bit [MK2, SH-2 code at `0x06002DF4`].

On both CPUs the decoder's own working values belong in registers. Koei's 68000 decoder keeps its control byte and bit window in RAM and re-reads them for every item, one reason it costs about 285 clocks per output byte ([Finding the idle processor](../patterns/cpu-split.md#finding-the-idle-processor)).

## Moving decompression to an SH-2

Aerobiz Ultimate moves Koei's decompressor from the 68000 to the Master SH-2. It is shipped, not just demonstrated [AU-NOTES, ROADMAP.md U-046; disasm/sh2/master/lz.c; disasm/32x/sh2_lz.asm]:

- **The hook.** The first 8 bytes of the 68000's routine are replaced by a jump to a short routine, a "thunk", that hands the job over. Every one of the 123 callers is redirected without being touched.
- **The hand-over.** The thunk masks interrupts and sets FM, giving the SH-2 the frame buffer. It writes the source address, converted to the SH-2's cartridge address, into one communication port, the frame buffer offset into another, and a command number last. It then polls until the SH-2 clears the command ([A mailbox that works](../32x/communication.md#a-mailbox-that-works)).
- **The SH-2 side** reads the compressed data from the cartridge through the cached address, so the input arrives a 16-byte line at a time. It unpacks into a 64 KB buffer in SDRAM, then copies the result as words to the frame buffer through the cache-through address.
- **Back on the 68000**, the thunk clears FM, copies the result from the frame buffer into the caller's buffer, and returns as the original routine did. The game's own DMA takes it on to VRAM as before.
- **Fallback.** If the SH-2 has not answered after 400,000 polls, the thunk gives back the frame buffer and runs the original 68000 code ([Never wait forever](../32x/communication.md#never-wait-forever)).

Two rules decided where the output goes. A byte write of 0 to the frame buffer is ignored, so LZ output cannot be written there a byte at a time; and reading back-references from the frame buffer would cost a slow access per byte. So the SH-2 decodes into SDRAM, where both are cheap, and moves the finished block in words ([The normal and overwrite images](../32x/vdp.md#the-normal-and-overwrite-images)). (d32xr gets round the first rule by clearing the frame buffer before decoding into it, as above, and accepts slow reads during level setup.)

The SH-2 version is plain C, a line-by-line translation of the 68000 routine, with byte copies and no unrolling. It still runs at about 60 SH-2 clocks per output byte, against about 285 68000 clocks, and finishes 14 times sooner in real time <span class="tag emulator">emulator</span>. Its output matches the 68000's exactly: a checksum over the 22,528-byte world map agrees with the reference decoder's, and screens captured from both builds are identical <span class="tag emulator">emulator</span> [AU-NOTES, ROADMAP.md U-046, HISTORY.md]. The cache does most of the work: the decoder's loop and the input both stay in it.

While the 68000 has RV set for a DMA from the cartridge, an SH-2 that reads the cartridge is stalled until RV clears ([The RV bit](../32x/architecture.md#the-rv-bit)). Aerobiz Ultimate's design rules that out. The thunk masks all 68000 interrupts and polls until the SH-2 answers, so neither the game nor its interrupt handlers can start a DMA during a job [AU-NOTES, disasm/32x/sh2_lz.asm]. The price is that vertical interrupts wait for the whole job, about 4.4 frames for the largest block in PicoDrive <span class="tag emulator">emulator</span>. The thunk turns them back on before its copy, and screen loads happen behind a fade anyway. The cartridge is still shared. The thunk's poll loop runs from the cartridge, so the 68000's instruction fetches compete with the SH-2's cache line fills, at a cost nobody has measured on a console.

## Run-length sprites

A run-length format stores "this many pixels of this colour" instead of the pixels. Sprites suit it: they have long transparent runs around the figure and flat areas inside it. Unlike LZ, a run-length sprite can be drawn while it is decoded, with no buffer.

### Drawn directly (Mortal Kombat II)

Mortal Kombat II's blitters read run-length data and write the frame buffer as they go [MK2, SH-2 code at `0x060027F0`-`0x06002994`]:

- **The first byte** of a sprite is the end-of-line marker for that sprite. Each line then starts with a skip count, added to the x position.
- **Each following byte packs a colour and a run length.** The fighters use 6 bits of colour and 2 of length. Everything else uses 4 and 4. A length of 0 means the length is in the next byte.
- **Colour 0 is transparent**: the blitter just moves the x position on. A transparent run whose length byte is 0 ends the sprite.
- **A palette offset** is added to every colour as it is written. The two fighters use the same format with different offsets, so each gets its own 64-colour slice of the 256-colour palette.

Two bits of length look short. Fighters are drawn with shading, so runs are short, and two bits leave six for the colour. The fighters' blitter writes runs of 1 to 3 with a short unrolled sequence and takes longer runs from the extra byte.

Mirroring is a second copy of each blitter that moves right to left over the same data ([Sprites without hardware sprites](2d-effects.md#sprites-without-hardware-sprites)).

### Decoded once, into a cache (After Burner Complete)

After Burner Complete scales every sprite, and a scaler needs to read any pixel of the source, which a run-length stream cannot give it. So the game decodes each shape once into SDRAM, keeps the decoded copy while there is room, and scales from it ([Memory](memory.md#a-cache-of-decoded-sprites)). The format is simple, and fast to decode [AB32X, SH-2 code at `0x060066A6`-`0x0600676A`]:

- **A signed control byte.** Positive *n*: *n* literal bytes follow. Negative *n*: a run of −*n* zeros. Zero: the end.
- **One instruction does two jobs.** After the test for positive, `NEGC` turns a negative count into a positive one and, by its borrow, tells a negative count (carry out) from the zero that ends the data (none). So no separate end test is needed.
- **Zero runs are written with Duff's device**: eight stores unrolled in a row, entered part-way through so that the first pass writes the remainder of the count divided by eight, and each later pass writes eight. The entry point is computed from the low three bits of the count.
- **A second version** masks every literal to its low 4 bits, so whatever colours the art uses, the shape comes out in palette entries 0-15. Bit 0 of the shape number chooses it. The cache's key keeps that bit (it is the shape number with bits 1-3 cleared), so a shape's two versions are cached separately [AB32X, SH-2 code at `0x060065BC`-`0x060065C2`, `0x0600670C`-`0x0600676A`]. In the palette the game loads at start-up, entries 1 to 14 are reds and oranges rising to a pale yellow [AB32X, palette at cartridge `$173700`]. So the variant draws any shape in fire colours, which suggests a burning or hit effect. It is rare: none of 24,127 sprites, sampled every 10 frames over 3,900 frames of the first stage, had the bit set <span class="tag emulator">emulator</span>.

The zeros become transparent pixels later, because the scaler writes through the overwrite image ([The normal and overwrite images](../32x/vdp.md#the-normal-and-overwrite-images)).

How good is the format? The shape table at cartridge `$173900` has 767 entries pointing at 364 distinct shapes. Unpacked, they come to 1,574,122 bytes, 74% of them from runs of zeros; packed, to 441,148 bytes, 28% [AB32X, shape table and RLE data at `$061000`-`$0CCD5C`, decoded]. Each shape is decoded on its own when it misses the cache, so any other format must compress each shape separately too. Compressed that way:

| Format | Bytes | Share of the unpacked size |
|--------|-------|----------------------------|
| The game's run-length format | 441,148 | 28.0% |
| LZSS in d32xr's byte-aligned format, 4 KB window, greedy matching | 313,553 | 19.9% |
| Deflate (LZ plus Huffman codes), for comparison | 153,349 | 9.7% |

LZSS would save 127 KB, 29% of the sprite data. The format does not change how often the cache misses, since the cache holds decoded shapes. It changes what each miss costs. LZSS would read 29% fewer bytes from the cartridge, the slow part of a miss. But it would rebuild every zero run by copying bytes from its own output, where the run-length decoder stores zeros from a register, eight to a loop pass. With three quarters of the output in zero runs, that matters. The game spends about 2% of the Master's time in its sprite cache in PicoDrive <span class="tag emulator">emulator</span>, so either way the stakes are small ([Memory](memory.md#a-cache-of-decoded-sprites)). Deflate's tables would cost far more per miss.

## Sound: a fixed cost per sample

Sound data is decoded in the PWM interrupt, one sample at a time, and must never fall behind. Both retail formats in the sources have a fixed cost per sample and a fixed ratio. See [PWM sound](../32x/pwm.md#1-the-pwm-interrupt-star-wars-arcade) for the drivers:

- **Mortal Kombat II** packs 6-bit samples four to three bytes, and plays each one twice. A second of sound at 22 kHz takes about 8.1 KB [MK2, SH-2 code at `0x0600509C`].
- **Star Wars Arcade** uses a codebook: each data byte picks a short block of samples from a 256-entry table, and each sample is played twice. With 4-sample blocks that is one byte per 8 output samples. Its second decoder starts a new table, stored in the data, every so many bytes [SWA, SH-2 code at `0x0600095C`-`0x06000AAE`].

Both halve the rate by playing every sample twice. That is the cheapest compression there is, and it costs the top half of the frequency range.

## Choosing a format

- **Match the format to the decoding CPU.** Bit-packed codes such as Koei's and ProPack's pack tighter, and need cheap single-bit operations. The SH-2 has them (`SHLL`, `ROTCL`, T). The 68000 has them only for one bit at a time. Byte-aligned formats such as d32xr's waste a few bits and decode quickly on either CPU.
- **Decompress where the data will be used, into memory that is cheap to read back.** LZ reads its own output. Decode into RAM or SDRAM, then copy the result in words to VRAM or the frame buffer. Decoding straight into VRAM saves RAM and costs about four port accesses per byte. Decoding straight into the frame buffer works only if the area is cleared first, and reads its back-references slowly.
- **The window sets the memory, not the output.** A resumable decoder with a 4 KB ring can take any size of picture or stream through 4 KB.
- **Sprites drawn often** should be either drawn directly from a run-length format or decoded once into a cache.
- **Sound** wants a fixed ratio and a fixed cost per sample.
- **On the 32X, give the work to an SH-2.** It reads the cartridge itself and has the cache, and it is many times faster even with a plain C decoder. Keep the 68000 version, so the two can be compared byte for byte ([When moving a job pays](../patterns/cpu-split.md#when-moving-a-job-pays)).

## In emulators

PicoDrive does not stall an SH-2 that reads the cartridge while RV is set, and it does not charge for the cartridge bus being shared between the SH-2s and the 68000 ([The RV bit](../32x/architecture.md#the-rv-bit), [Two SH-2s, one bus](../sh2/bsc.md#two-sh-2s-one-bus)). An SH-2 decompressor reading the cartridge will be slower on a console than the emulator's figures, by an amount nobody has measured.

## What to take away

- LZ for general data, run-length coding for sprites, fixed-rate packing for sound.
- Choose bit-packed formats for the SH-2 and byte-aligned ones where the 68000 decodes.
- Decode into RAM or SDRAM and copy out in words. Decode into VRAM only to save RAM, and into the frame buffer only after clearing it.
- A resumable decoder needs only its window, however large the output.
- On the 32X, move decompression to an SH-2: it is one of the few jobs that is both heavy and easy to hand over.

## Open questions

- How much does Aerobiz Ultimate's SH-2 decompressor slow down on a console while the 68000 polls from the cartridge?
- Which effect uses After Burner Complete's 4-bit variant? It did not appear in 3,900 frames of the first stage.
- What would LZSS cost After Burner Complete per cache miss, with fewer cartridge bytes to read but zero runs to copy?

## Sources

- [AB-DISASM](../appendices/bibliography.md#ab-disasm): disasm/modules/68k/boot/EarlyInit.asm, game/DecompressVDPTiles.asm, vdp/VRAMWriteExtended.asm, vdp/VRAMWriteWithMode.asm, sound/ClearSoundBuffer.asm, GameSetup1.asm
- [AU-NOTES](../appendices/bibliography.md#au-notes): tools/lz_decompress.py, disasm/sh2/master/lz.c, disasm/32x/sh2_lz.asm (the thunk), ROADMAP.md U-046, HISTORY.md
- [MK2](../appendices/bibliography.md#mk2): SH-2 code at `0x06002DF4`, `0x060027F0`-`0x06002994`, `0x0600509C`; 68000 code at `$00CFF8`, `$00D186`, `$0292F4`, `$028F38`-`$028FCA`, `$008E86`, `$0096DC`-`$009704`; ROM scan for ProPack headers
- [AB32X](../appendices/bibliography.md#ab32x): SH-2 code at `0x060065BC`-`0x0600676A`; shape table at `$173900`, RLE data at `$061000`, palette at `$173700`; draw lists read in PicoDrive
- [SWA](../appendices/bibliography.md#swa): SH-2 code at `0x0600095C`-`0x06000AAE`
- [D32XR](../appendices/bibliography.md#d32xr): liblzss/lzss.c, liblzss/lzss.h, w_wad.c, marsnew.c, marsdraw.c, src-md/vgm.c
