# Compression and decompression

A Mega Drive cartridge holds a few megabytes, and a 32X game's art is 8 bits a pixel instead of 4, so it needs twice the space for the same picture. Almost every game in the sources compresses something. This chapter covers the formats they use: LZ for general data, run-length coding for sprites, fixed-rate packing for sound, and, from one sample program, vector quantisation for video. It also covers where each one is decompressed and what that costs on each CPU.

Four questions decide the format:

1. **Which CPU decompresses it?** The 68000 runs at 7.67 MHz on a 16-bit bus; an SH-2 runs at three times the clock and has a cache.
2. **Where does the output go?** RAM is easy. VRAM and the 32X frame buffer are not: each is behind a port or has write rules of its own.
3. **Is it decoded once, or every time it is drawn?** A level loaded once can use a slow, tight format. A sprite drawn in every picture needs a format the drawing loop can read directly, or a cache of decoded copies.
4. **Must it keep pace with something?** Sound is decoded inside an interrupt, sample by sample, and needs a format whose cost per sample is fixed.

| Format | Game | Decoded by | Into | Notes |
|--------|------|------------|------|-------|
| Koei's LZSS, bit-packed lengths and distances | Aerobiz Supersonic | 68000 | Work RAM, or VRAM directly | 4 KB window; in Aerobiz Ultimate, moved to the Master SH-2 |
| Rob Northen's ProPack (RNC), method 2 | Mortal Kombat II | Master SH-2 | SDRAM | 47 files the SH-2 uses, packed to 36% of their size |
| ProPack, method 1 (adds Huffman codes) | Mortal Kombat II | 68000 | Work RAM, or VRAM through a 32 KB ring | 33 files of Mega Drive graphics, packed to 48%. The files differ from method 2's, so the two ratios do not compare the methods |
| Jaguar Doom's LZSS, byte-aligned | d32xr | SH-2 and 68000 | SDRAM, a ring buffer, or work RAM | Resumable; streams pictures and music through a small window |
| Colour and run bytes | Mortal Kombat II | Master SH-2 | Frame buffer, drawn directly | 6+2 or 4+4 bits a byte |
| Signed control byte, runs of zeros | After Burner Complete | Master SH-2 | A cache in SDRAM | Decoded once per shape, then scaled from the cache |
| Packed PCM, codebook PCM | Mortal Kombat II, Star Wars Arcade | Slave SH-2, in the PWM interrupt | PWM | Fixed cost per sample |
| Cinepak, vector quantised video | ECCO CinePak demo | Master SH-2 | SDRAM, then the frame buffer | 6.8 times smaller than 15-bit pixels; table lookups and copies |

## LZ: copy what came before

An LZ decompressor rebuilds the output from two kinds of item. A **literal** is one byte copied from the input. A **back-reference** says "copy *n* bytes from *d* bytes back in the output". Text, tile maps and graphics repeat themselves, so most of the output comes from back-references. LZSS is the common variant in which one flag bit before each item says which kind it is. The **window** is how far back a reference can reach. The decompressor must keep at least that much of its own output where it can read it, so the window, not the size of the output, sets the memory it needs.

The copy runs forwards, a byte at a time, so a reference may overlap the bytes it is producing: a distance of 1 with a length of 100 repeats one byte 100 times. That is how LZ formats encode runs, and it is why a copy routine that moves whole words must check the distance first.

### Koei's LZSS (Aerobiz Supersonic)

Koei's format squeezes the lengths and distances into variable-length bit codes, and mixes three kinds of data into one input stream [AB-DISASM, disasm/modules/68k/boot/EarlyInit.asm `LZ_Decompress`, `$003FEC`-`$00423F`; AU-NOTES, tools/lz_decompress.py]:

- **Flags.** A control byte gives the next eight flags, top bit first. A 1 means a literal, a 0 a back-reference. The routine keeps the control byte in RAM. For each item it loads the byte and tests bit 7 with `btst`. After the item it adds the byte in RAM to itself, which moves the next flag up into bit 7. The carry from that add is not used.
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

The game calls this routine from 123 places. That is the number of `jsr $003FEC` instructions in the ROM and the disassembly's own count; Aerobiz Ultimate's roadmap says 92 call sites and does not say how it counted. Of its 92, 66 unpack into a buffer at `$FF1804` and 6 more into `$FF899C`, and the graphics then go by DMA to VRAM [AB-DISASM, EarlyInit.asm, ROM scan for the `jsr`; AU-NOTES, ROADMAP.md U-046]. The largest block is 27,872 bytes.

### Decompressing straight into VRAM

Aerobiz Supersonic also has a second copy of the same decoder that writes to VRAM instead of RAM [AB-DISASM, disasm/modules/68k/game/DecompressVDPTiles.asm, `$004342`-`$0045B1`]. VRAM serves as both output and window, so no RAM buffer is needed at all. The cost is in how it reaches VRAM:

- **Writing a byte.** VRAM is accessed in words through the data port, so each output byte is a read-modify-write of its word: set a read address, read the word, replace the high or low byte depending on whether the address is even or odd, set a write address, write the word back. That is four port instructions and six 16-bit bus transfers per byte [AB-DISASM, vdp/VRAMWriteExtended.asm, `$0042F0`].
- **Reading a back-reference** sets a read address and reads a word, two more port instructions per byte [AB-DISASM, vdp/VRAMWriteWithMode.asm, `$0042BA`].
- **Interrupts are masked around every access**, so the vertical interrupt cannot change the VDP's address between the halves of the operation ([The VDP remembers half a command](../megadrive/vdp.md#the-vdp-remembers-half-a-command)).

It is used once, during the intro, to load the font: 3,866 bytes unpacked to 10,112 bytes (316 tiles) at VRAM `$4000`, with the display and the vertical interrupt switched off around it [AB-DISASM, sound/ClearSoundBuffer.asm, GameSetup1.asm]. That is the right use for a slow path: once, early, and when RAM is short. The file names cited here are the disassembly's own, and some are misnomers: the font load, for instance, is in `sound/ClearSoundBuffer.asm`.

### ProPack on the SH-2 (Mortal Kombat II)

Mortal Kombat II packs its SH-2 data with Rob Northen's ProPack, a commercial packer of the time. Each file starts with an 18-byte header: `RNC` and a method number, the unpacked and packed sizes (4 bytes each), the CRC-16 of the unpacked data and of the packed data (2 bytes each), and two more bytes. The cartridge holds 47 method-2 files, 1.09 MB unpacked and 396 KB packed, 36% of their size; the largest unpacks to 99,132 bytes [MK2, ROM scan for `RNC\x02` headers]. The Master unpacks them straight from the cartridge into SDRAM with a 402-byte routine called from about 30 places. Its last instruction is the `nop` in the delay slot of its `rts`, at `0x06002F84` [MK2, SH-2 code at `0x06002DF4`-`0x06002F84`]:

- It skips the header. Sizes and checksums are not checked; the data is trusted.
- **Flags and codes share one bit stream**, top bit first, refilled a byte at a time. The first two bits of the stream are skipped. Literal and length bytes come from the same pointer between refills.
- **Items** are told apart by their leading bits:

  | Bits | Item |
  |------|------|
  | `0` | One literal byte |
  | `1000`, `1010`, `10010`, `10011`, `10110` | A copy of 4, 5, 6, 7 or 8 bytes, then a distance |
  | `10111`, then 4 bits *c* | A block of (*c* + 3) × 4 literal bytes, copied two bytes at a time |
  | `110` | A copy of 2 bytes, at the distance given by the next whole byte plus 1 (1 to 256) |
  | `1110` | A copy of 3 bytes, then a distance |
  | `1111`, then a length byte *n* | A copy of *n* + 8 bytes, then a distance. A length byte of 0 ends a chunk, and one more bit says whether another chunk follows (0 for none) |

- **A distance** is a high part, 0 to 15, in a prefix code, then a whole byte for the low part. The distance is high × 256 + low + 1, so references reach 1 to 4,096 bytes back. The high part is `0` for 0, `110` for 1, `100x` for 2 + *x*, `1x1y1` for 4 + 2*x* + *y*, and `1x1y0z` for 8 + 4*x* + 2*y* + *z*.

A decoder that follows these codes (`notes/games/mk2/rnc_check.py`, written from the routine) unpacks all 47 method-2 files to exactly the size each header gives, and the CRC-16 of the unpacked data in each header matches the output [MK2, every `RNC\x02` file decoded and checked].

### ProPack on the 68000 (Mortal Kombat II)

The other 33 ProPack files in the cartridge are method 1: 553 KB unpacked, 267 KB packed, 48% [MK2, ROM scan for `RNC\x01` headers]. A standard method-1 decoder unpacks all 33 to their header's size and CRC as well [MK2, every `RNC\x01` file decoded and checked]. Method 1 adds **Huffman codes**, which give common values short bit patterns. Each chunk of the file starts with its own code tables. The SH-2 program has no method-1 unpacker. The 68000 has three, all of which rebuild three 128-byte decoding tables on the stack for each chunk [MK2, 68000 code at `$00CFF8`, `$00D186`, `$0292F4`]:

- **Into work RAM** (`$00CFF8`, and `$0292F4`, which first moves the packed data out of the way if it overlaps the output). Two of the three callers of `$0292F4` first check for the four bytes `RNC`, 1, so the same call takes a packed or an unpacked file. Either way, the result is queued as a VDP DMA from work RAM [MK2, 68000 code at `$028F38`-`$028FCA`].
- **Straight to VRAM** (`$00D186`). The caller sets a VRAM write address, and the routine keeps the last 32 KB of its output in a ring buffer at `$FF0000` as its window. Each time a word is complete, it writes that word to the VDP data port. A file can be any length; only the window needs RAM.

The VRAM routine handles the largest files. Ten loaders, reached through a table of ten pointers at `$008E5E` indexed by the word at `$FFAAC0`, each stream one file of 33 to 46 KB to VRAM and unpack a second file of 9 to 14 KB into work RAM [MK2, 68000 code at `$008E52`-`$008E5C`, `$008E86`, `$0096DC`-`$009704`]. These are presumably the arenas, which the Mega Drive draws ([Using both video chips at once](../patterns/layering.md#what-the-shipped-games-put-where)). Unpacked at `$FF0000`, a 46 KB file would run past `$FF8818`, where the game keeps variables. The ring buffer is what lets it be unpacked at all.

So Mortal Kombat II splits its packed data by the CPU that uses it: method 2 for what the SH-2 draws, method 1 for the Mega Drive's tiles. The code shows why each file is unpacked where it is. Each CPU unpacks the data that ends up in memory it can reach: the SH-2 cannot write VRAM or the 68000's work RAM, and the 68000 cannot reach SDRAM. The code does not show why the heavier method, with its Huffman tables, went to the slower CPU. Its largest files are the arenas, each unpacked once as a fight is set up, where a few frames of decoding are affordable. A Mega Drive game ported to the 32X can keep its 68000 unpacker for Mega Drive graphics in the same way.

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

- **68000.** Add a register to itself and the top bit lands in the carry and X flags, ready for `BCC`/`BCS` or `ADDX`. Shipped code uses this for flag bits: Knuckles' Chaotix counts the set bits of a flag byte with `ADD.B D0,D0` and `BCC` [CHAOTIX, 68000 code at `$004E1C`-`$004E2E`]. Neither 68000 decoder in this chapter takes its codes out that way, though. Koei tests the flag with `BTST #7`, and finds each length and distance by comparing the whole 16-bit window against thresholds, then removes the whole code at once. Mortal Kombat II's method-1 unpacker shifts a whole code off its bit buffer with `LSR.L` by a register count [MK2, 68000 code at `$00D0AA`, `$00D0C8`]. Both avoid a loop per bit, because a shift by *n* places costs 6 + 2*n* clocks, 8 + 2*n* for a long [M68K-UM §8.6], so one multi-bit shift is cheaper than a loop of single-bit steps.
- **SH-2.** `SHLL` moves the top bit into T. `BT`/`BF` branch on it, and `ROTCL` adds it to a value being built up. Mortal Kombat II keeps the current byte in the top 8 bits of a register, so a 32-bit shift brings out its top bit, and a counter says when to load the next byte. The refill, four instructions, is written out in full at each of the twenty-odd places a bit is read, not called. That makes the routine longer and saves a call and a return for each bit [MK2, SH-2 code at `0x06002DF4`]. The SH-2 has no shift by a count held in a register, only shifts of 1, 2, 8 and 16 places ([Shifts without a barrel shifter](../sh2/isa.md#shifts-without-a-barrel-shifter)), which is a likely reason why this unpacker takes its bits one at a time, where both 68000 decoders remove whole codes. The code does not say.

On both CPUs the decoder's own working values belong in registers. Koei's 68000 decoder is compiled C, and it has the compiler's marks ([Naming and annotating](../howto/reverse-engineering.md#naming-and-annotating)). It reads its arguments from the stack, and it pushes an argument with `pea` and pops it after each call to the bit reader. It widens word counters to longs with `moveq #0` and `move.w` before comparing them. And it keeps its control byte and bit window in RAM variables that it re-reads for every item [AB-DISASM, EarlyInit.asm `$003FEC`-`$00423F`, helper at `$003F72`]. Compiled code that keeps its state in RAM explains the cost, about 285 clocks per output byte ([Finding the idle processor](../patterns/cpu-split.md#finding-the-idle-processor)).

## Moving decompression to an SH-2

Aerobiz Ultimate moves Koei's decompressor from the 68000 to the Master SH-2. It is shipped, not just demonstrated [AU-NOTES, ROADMAP.md U-046; disasm/sh2/master/lz.c; disasm/32x/sh2_lz.asm]:

- **The hook.** The first 8 bytes of the 68000's routine are replaced by a jump to a short routine, a "thunk", that hands the job over. Every one of the 123 callers is redirected without being touched.
- **The hand-over.** The thunk masks interrupts and sets FM, giving the SH-2 the frame buffer. It writes the source address, converted to the SH-2's cartridge address, into one communication port, the frame buffer offset into another, and a command number last. It then polls until the SH-2 clears the command ([A mailbox that works](../32x/communication.md#a-mailbox-that-works)).
- **The SH-2 side** reads the compressed data from the cartridge through the cached address, so the input arrives a 16-byte line at a time. It unpacks into a 64 KB buffer in SDRAM, then copies the result as words to the frame buffer through the cache-through address.
- **Back on the 68000**, the thunk clears FM, copies the result from the frame buffer into the caller's buffer, and returns as the original routine did. The game's own DMA takes it on to VRAM as before.
- **Fallback.** If the SH-2 has not answered after 400,000 polls, the thunk gives back the frame buffer and runs the original 68000 code ([Never wait forever](../32x/communication.md#never-wait-forever)).

**Why the frame buffer.** It is the only large block of writable memory both CPUs can reach. The 68000 cannot see SDRAM at all, and the SH-2 cannot reach the 68000's work RAM. The communication ports hold only 16 bytes. The CPUs always reach the back buffer, the one not being displayed ([Frame buffers and the FS bit](../32x/vdp.md#frame-buffers-and-the-fs-bit)). The thunk uses it from offset `$012000`. That is past the 512-byte line table and the 224 lines it points at, so the data would not show as a picture even with the layer on. In the shipping build the 32X layer is blanked anyway [AU-NOTES, ROADMAP.md U-046; disasm/modules/shared/definitions_32x.asm `MARS_LZ_FB_OFFSET`].

Two rules decided why the SH-2 does not decode straight into it. A byte write of 0 to the frame buffer is ignored, so LZ output cannot be written there a byte at a time; and reading back-references from the frame buffer would cost a slow access per byte. So the SH-2 decodes into SDRAM, where both are cheap, and moves the finished block in words ([The normal and overwrite images](../32x/vdp.md#the-normal-and-overwrite-images)). (d32xr gets round the first rule by clearing the frame buffer before decoding into it, as above, and accepts slow reads during level setup.)

The SH-2 version is plain C, a line-by-line translation of the project's Python port of the 68000 routine, with byte copies and no unrolling. Every check found its output equal to the 68000's: a checksum over the 22,528-byte world map agrees with the reference decoder's, and screens captured from both builds are identical <span class="tag emulator">emulator</span> [AU-NOTES, ROADMAP.md U-046, HISTORY.md]. For this book the C source, built for a PC, and the Python port were also run over every compressed block that the ROM's call sites name, directly or through the pointer tables they index: 316 distinct blocks from 107 of the 123 call sites, 683,456 bytes out in all, the largest 27,872 bytes. They decode identically, and for two of the blocks the output equals what the 68000's own routine left in a work RAM snapshot (2,272 and 960 bytes). The other 16 call sites compute their source address, so their blocks are not covered, and the compiled SH-2 code was not itself run on any of them [AU-NOTES, disasm/sh2/master/lz.c, tools/lz_decompress.py; AB-DISASM, ROM and RAM snapshot; `notes/games/tools/aerobiz_lzcheck.py`, 10 October 2026].

How fast it is depends on what is counted. Stock PicoDrive models no SH-2 cache and no memory waits, so its SH-2 timings are instruction counts. The project measured on the Virtua Racing project's build of PicoDrive, which Aerobiz Ultimate also uses and for which it wrote the timing model ([Pipeline and cycle counting](../sh2/pipeline.md#in-emulators)). That model was checked against the manuals, not against a console [AU-NOTES, ROADMAP.md U-093]:

| | 68000 | SH-2 | Ratio |
|---|---|---|---|
| Decoding only, clocks per output byte | 285.5 at 7.67 MHz | 59.7-60.7 at 23.01 MHz | 4.7-4.8 times fewer clocks, at three times the clock rate |
| Decoding only, largest block (27,872 bytes) | 62.2 frames | 4.4 frames | 14 times sooner |
| End to end, largest block | 62.2 frames | about 7.5 frames | about 8 times sooner |

The decode-only figures are measured <span class="tag emulator">emulator</span>, and three things bear on how far to trust them [AU-NOTES, ROADMAP.md U-046, U-093]:

- **What the model includes.** SH-2 wait states for each memory area and a cache that keeps tags only. In it, 99.99% of the decoder's accesses hit the cache. With the model turned off, PicoDrive gives the SH-2 ideal memory with no waits at all, which is not the same as a console without a cache, and the decoder is about 10% faster than with it. So in the model the cache and the waits leave the decoder within about 10% of ideal memory.
- **What it undercharges.** A cartridge line fill costs half this book's figure, four bus cycles instead of eight ([discrepancy 48](../appendices/discrepancies.md)). The decoder reads its input through the cached cartridge address [AU-NOTES, disasm/sh2/master/lz.c]: the world map's 7,761 compressed bytes make about 490 line fills for 22,528 bytes out. At this book's figure each fill costs about 33 to 69 clocks more, which adds 0.7 to 1.5 clocks a byte: about 60.4 to 62.2 instead of 59.7 to 60.7, a change of 1% to 2.5%.
- **What it leaves out.** The cartridge bus the SH-2 shares with the 68000 (below).

The end-to-end figure adds the two copies, estimated from instruction timings, not measured:

- **The SH-2 copies SDRAM to the frame buffer.** The compiled loop is ten instructions a word: two byte loads, a shift and an OR, and a word store through the cache-through address. That is about 11-13 clocks a word, half a frame for the largest block [AU-NOTES, build/sh2/master/lz.o `sh2_lz_job`]. One word load would replace the two byte loads, the shift and the OR. The SDRAM buffer is a plain `unsigned char` array, which C only promises byte alignment for. It happens to start on a 4-byte boundary in the current build, so declaring it aligned and reading it through a matching type would make the cheaper loop safe.
- **The 68000 copies the frame buffer to the caller's buffer.** Each word costs `MOVE.W (A1)+,(A0)+` (12 clocks), 2 to 4 wait states on the frame buffer read, and `DBRA` (10): 24-26 clocks. For the largest block's 13,936 words that is 2.6-2.8 frames [M68K-UM §8; 32X-HWM §4.4].

The game-level measurement agrees better with the end-to-end figure than with the decode-only one. Over 12,000 frames the patched build ran 198 frames ahead of the original. These are emulator frames, not the game's own frame count, which loses about four frames in each large job (below): the project's harness hashes VRAM and CRAM once per emulated frame and pairs the frames on which both builds show the same screen [AU-NOTES, ROADMAP.md U-092]. The original stalls for 74-76 frames at each quarter boundary. The largest block alone is 62 of them. The project describes a stall as decompression plus VDP traffic and does not itemise the other 12 to 14 frames, so a stall is more than one block [AU-NOTES, ROADMAP.md U-045, U-046]. Quarter boundaries come about every 4,000 frames, so the 12,000 frames hold about three, and 198 / 3 is about 66 frames saved at each. That leaves 8 to 10 frames of a 74-76 frame stall, 7.6 to 9.3 times shorter, against about 8 times for the largest block end to end and 14 times for decoding alone <span class="tag emulator">emulator</span>. The stall includes VDP traffic the SH-2 does not take over, so the match is a rough one.

The 68000's copy is now over a third of a hand-over for the largest block, 2.6 to 2.8 of about 7.5 frames, the largest part that is not decoding. A 68000 DMA from the frame buffer straight to VRAM would remove it, but that path is untested. What would have to be true: the Mega Drive VDP reads each word of a DMA source from the 68000's bus, so the 32X would have to answer the frame buffer's 2 to 4 wait states on every word, with the frame buffer handed to the 68000 for the whole transfer [32X-HWM §4.4 p.77]. Whether the VDP's DMA tolerates that is not documented. A related case is a warning: Sega's note says that DMA from the Mega-CD's Word RAM with a 32X attached has a problem in the timing of its data fetch, so that the data is undefined, and must not be used [32X-TI item 13].

While the 68000 has RV set for a DMA from the cartridge, an SH-2 that reads the cartridge is stalled until RV clears ([The RV bit](../32x/architecture.md#the-rv-bit)). Aerobiz Ultimate's design rules that out. The thunk masks all 68000 interrupts and polls until the SH-2 answers, so neither the game nor its interrupt handlers can start a DMA during a job [AU-NOTES, disasm/32x/sh2_lz.asm]. The price is that the 68000's interrupts wait for the whole job: the SH-2's decode and its copy, about 5 frames for the largest block. The thunk turns them back on before its own copy, and screen loads happen behind a fade anyway. The vertical interrupts that arrive meanwhile are not queued. The 68000 takes one when its mask drops, so after a job of the largest block's size the game's frame count runs about four frames short. A small job masks the interrupts for much less than a frame.

**The music keeps playing.** Aerobiz's music runs entirely on the Z80, whose driver sets interrupt mode 1 and keeps time from its own interrupt at `$38` [AB-DISASM, Z80 driver copied from cartridge `$2696`: `im 1` and `ei` at Z80 `$00E0`, handler at `$096B`]. The VDP raises that interrupt whatever the 68000's mask is ([Interrupts on the Z80 side](../megadrive/z80.md#interrupts-on-the-z80-side)). The thunk never takes the Z80's bus, so a job does not stop the driver. It may still disturb it. The driver is 5,458 bytes copied into Z80 RAM, and it contains the Z80's bank-switch routine, which writes the nine bits of the bank register at `$6000`, and builds pointers into the banked window at `$8000` [AB-DISASM, Z80 driver at cartridge `$2696`: bank routine at Z80 `$05BF`, called from `$041A`; `ld hl,$8000` at `$0C58`]. So some of what it plays comes from the cartridge, over the 68000's bus, which an SH-2 reading the cartridge shares. Which data comes that way, and whether the decoder's line fills ever hold up one of the Z80's reads long enough to be heard, was not traced, and PicoDrive does not model the delay. Aerobiz Ultimate still plays through this driver; its PWM audio is not written yet [AU-NOTES, ROADMAP.md M6]. What a job does delay is any new sound command: the 68000 sends those through sound RAM, and it does nothing but poll until the job ends.

**The cartridge is still shared.** The thunk's poll loop runs from the cartridge, so the 68000 fetches from it while the SH-2 fills its cache lines from it. By the manual, a request made at the same moment goes to the SH-2, and a request that arrives while the other CPU's access is under way waits for that access to finish [32X-HWM §4.1 p.74]. So each time the SH-2 asks for the cartridge, it can lose at most the rest of one 68000 access, 12 to 27 SH-2 clocks ([Access timing per CPU](../32x/timing.md#the-figures)), and not a whole fetch loop. For the world map the ceiling is easy to work out. If each of its 490 line fills lost one such wait, that is about 13,000 clocks, 1% of the decode. If each of the 3,920 word cycles in those fills did, it is about 106,000 clocks, 8%. Which is nearer depends on whether the SH-2 keeps the bus between the eight word cycles of a fill, which the manual does not say <span class="tag manual">manual</span>, and nobody has measured it on a console. Copying the six-instruction loop to work RAM would remove the 68000's fetches. The communication port it reads is a 32X register, not cartridge memory. The Mars Check Program copies its RV test to work RAM for a related reason ([Worked example: one test, both CPUs](../howto/reverse-engineering.md#worked-example-one-test-both-cpus)). Aerobiz Ultimate keeps one routine in work RAM already: its DMA stub, which RV forces out of the cartridge. It puts that stub below the stack, the only work RAM the project found reliably free, since the game overwrites areas a static scan had marked unused [AU-NOTES, PORT_ARCHITECTURE.md; HARDWARE_TESTS.md]. The LZ thunk does not touch RV, so nothing forces it there, and the contention has not been measured to say it is worth the RAM.

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

LZSS would save 125 KB (127,595 bytes), 29% of the sprite data. The format does not change how often the cache misses, since the cache holds decoded shapes. It changes what each miss costs. LZSS would read 29% fewer bytes from the cartridge, the slow part of a miss. But it would rebuild every zero run by copying bytes from its own output, where the run-length decoder stores zeros from a register, eight to a loop pass. With three quarters of the output in zero runs, that matters. The game spends about 2% of the Master's time in its sprite cache in PicoDrive <span class="tag emulator">emulator</span>, so either way the stakes are small ([Memory](memory.md#a-cache-of-decoded-sprites)). Deflate's tables would cost far more per miss.

## Sound: a fixed cost per sample

Sound data is decoded in the PWM interrupt, one sample at a time, and must never fall behind. Both retail formats in the sources have a fixed cost per sample and a fixed ratio. See [PWM sound](../32x/pwm.md#1-the-pwm-interrupt-star-wars-arcade) for the drivers:

- **Mortal Kombat II** packs 6-bit samples four to three bytes, and plays each one twice. A second of sound at 22 kHz takes about 8.1 KB. The decoder runs on the Slave: its interrupt dispatcher, a table at `0x06004E64` indexed by interrupt level, sends level 6, the PWM interrupt, to the handler at `0x06004F4C` [MK2, SH-2 code at `0x06004E24`, `0x06004F4C`, `0x0600509C`].
- **Star Wars Arcade** uses a codebook: each data byte picks a short block of samples from a 256-entry table, and each sample is played twice. With 4-sample blocks that is one byte per 8 output samples. Its second decoder starts a new table, stored in the data, every so many bytes. The Slave decodes it too, in its PWM interrupt, between the polygons it cuts [SWA, SH-2 code at `0x0600095C`-`0x06000AAE`; [Case study: Star Wars Arcade](../patterns/case-study-starwars.md#sound-between-the-polygons)].

Both halve the rate by playing every sample twice. That is the cheapest compression there is, and it costs the top half of the frequency range.

## Cinepak: video as vector quantisation

Video is the extreme case of data decoded every time it is shown: tens of pictures a second, each one a fresh frame buffer to fill. The ECCO movie is stored at 30. Sega's own sample plays Cinepak, which codes a picture as numbers into tables of small pixel blocks, and what that asks of the decoder is close to a copy [ECCO; CINEPAK-TD]. The whole demo is in [Case study: the ECCO CinePak demo](../patterns/case-study-ecco.md).

A Cinepak picture is cut into 4 × 4 blocks, and a block is not stored as pixels. The picture carries **codebooks**, tables of up to 256 small pixel blocks, and a block is a few numbers into them. A *V4* block is four numbers, one for each 2 × 2 quarter. A *V1* block is one number, whose four pixels are each stretched over a quarter. A codebook entry is six bytes: four brightness values, one for each pixel, and one pair of colour values shared by the four. One flag bit a block says which kind it is. The first picture of a strip carries whole codebooks; later pictures can update chosen entries and mark whole blocks as unchanged, and a picture can be cut into strips that each carry codebooks of their own [CINEPAK-TD]. The ECCO movie uses only the simplest corner: one strip, whole codebooks, V4 blocks and nothing else.

What the SH-2 does with it is two steps, and each is cheap in its own way:

1. **Turn the codebook into pixels, once a picture.** Each six-byte entry becomes four 15-bit pixels, 8 bytes, with a few adds and clamps. That is 66,600 instructions for 256 entries.
2. **Copy.** A V4 block takes four index bytes from the stream, and each index selects an 8-byte entry whose two longwords go to two rows of the block. It takes 52.6 instructions on average a block, 3.3 a pixel, with no multiply [ECCO, SH-2 code at `0x06000F5C`, `0x060002B4`].

The conversion is done on the table, not the picture: 1,024 pixels instead of 40,960. A 256 × 160 picture costs about 400,000 instructions in all, copy to the frame buffer included, and the copy is half of them. A frame is 384,000 clocks, and the demo shows a new picture every second frame in PicoDrive, 30 a second, the movie's own rate. Its 400,000 instructions take about 455,000 clocks before any memory wait, so on a console the work could run past two frames. The data is 12,128 bytes a picture, 2.4 bits a pixel; reading it byte by byte from the cartridge is about 12,100 bus cycles ([Case study](../patterns/case-study-ecco.md#where-the-time-goes)).

## Choosing a format

- **Match the format to when it is decoded.** Bit-packed codes such as Koei's and ProPack's pack tighter, and cost more to decode: every code has to be shifted out of a bit buffer, a few bits at a time at best. An SH-2 is fast enough for any of these formats. On the 68000 a bit-packed format is affordable when the data is decoded once, at load time, as both Koei's screens and Mortal Kombat II's arenas are. Byte-aligned formats such as d32xr's waste a few bits and decode quickly on either CPU, so they suit data decoded while the game runs.
- **Decompress where the data will be used, into memory that is cheap to read back.** LZ reads its own output. Decode into RAM or SDRAM, then copy the result in words to VRAM or the frame buffer. Decoding straight into VRAM saves RAM and costs four port instructions and six bus transfers for each byte written, and two more instructions for each byte copied from a back-reference. Decoding straight into the frame buffer works only if the area is cleared first, and reads its back-references slowly.
- **The window sets the memory, not the output.** A resumable decoder with a 4 KB ring can take any size of picture or stream through 4 KB.
- **Sprites drawn often** should be either drawn directly from a run-length format or decoded once into a cache.
- **Sound** wants a fixed ratio and a fixed cost per sample.
- **Video** wants a format whose decoder is lookups and copies, because every pixel of every picture goes through it. Cinepak's cost is in the table conversion, once a picture, and the copy, once a block ([Cinepak](#cinepak-video-as-vector-quantisation)).
- **On the 32X, give the work to an SH-2.** It runs at three times the 68000's clock and has a cache, and it is many times faster even with a plain C decoder. Keep the 68000 version, so the two can be compared byte for byte ([When moving a job pays](../patterns/cpu-split.md#when-moving-a-job-pays)).

## In emulators

PicoDrive does not stall an SH-2 that reads the cartridge while RV is set, and it does not charge for the cartridge bus being shared between the SH-2s and the 68000 ([The RV bit](../32x/architecture.md#the-rv-bit), [Two SH-2s, one bus](../sh2/bsc.md#two-sh-2s-one-bus)). Stock PicoDrive models no SH-2 cache and no memory wait states either, so its SH-2 timings are instruction counts; Aerobiz Ultimate's figures come from the Virtua Racing project's build of PicoDrive, which has a model of both that Aerobiz Ultimate wrote ([Moving decompression to an SH-2](#moving-decompression-to-an-sh-2)). An SH-2 decompressor reading the cartridge will be slower on a console than either build's figures, by an amount nobody has measured.

## What to take away

- LZ for general data, run-length coding for sprites, fixed-rate packing for sound, and for video a format that is lookups and copies. Cinepak's cost is a table conversion once a picture and a copy once a block.
- Bit-packed formats suit an SH-2, and the 68000 when the data is decoded once at load time. Byte-aligned formats suit anything decoded while the game runs.
- Decode into RAM or SDRAM and copy out in words. Decode into VRAM only to save RAM, and into the frame buffer only after clearing it.
- A resumable decoder needs only its window, however large the output.
- On the 32X, move decompression to an SH-2: it is one of the few jobs that is both heavy and easy to hand over.

## Open questions

- How much of the ceiling above, 1% to 8% for the world map, does Aerobiz Ultimate's SH-2 decompressor lose on a console while the 68000 polls from the cartridge, and would copying the poll loop to work RAM recover it? The manual's rule bounds each loss at the rest of one 68000 access. What is open is how often the 68000 is mid-access when the SH-2 asks, and whether the bus is free between the word cycles of a line fill.
- Can the 68000's VDP DMA read the 32X frame buffer at `$840000`? If so, Aerobiz Ultimate could send decompressed tiles to VRAM without its 2.6-2.8-frame copy. It needs the 32X to answer 2 to 4 wait states a word, and the VDP's DMA to accept them, with Sega's warning about Word RAM as the reason to doubt it. A test ROM that DMAs a known pattern from the frame buffer to VRAM would show it.
- Why does Mortal Kombat II give method 1, the format with Huffman codes, to the 68000 and method 2 to the SH-2? Each CPU unpacks what lands in memory it can reach, but the code does not show why the methods went the way they did. The Mega Drive version of the game would settle it: if it holds the same `RNC`, 1 files and the same unpackers at `$00CFF8`, `$00D186` and `$0292F4`, the method-1 data came over from that version, and method 2 was chosen only for the new SH-2 side. That cartridge is not among the book's ROMs. Repacking some files of each set with the other method would show what the Huffman codes buy on the same data; no ProPack packer is at hand.
- Which effect uses After Burner Complete's 4-bit variant? It did not appear in 3,900 frames of the first stage.
- What would LZSS cost After Burner Complete per cache miss, with fewer cartridge bytes to read but zero runs to copy?

## Sources

- [AB-DISASM](../appendices/bibliography.md#ab-disasm): disasm/modules/68k/boot/EarlyInit.asm (`LZ_Decompress`, helper at `$003F72`), game/DecompressVDPTiles.asm, vdp/VRAMWriteExtended.asm, vdp/VRAMWriteWithMode.asm, sound/ClearSoundBuffer.asm, GameSetup1.asm; Z80 driver at cartridge `$2696` (Z80 `$00E0`, `$0038`, `$096B`, `$041A`, `$05BF`, `$0C58`); the ROM scanned for `jsr $003FEC` (123 hits); the 68000 work RAM snapshot of 15 September 2026
- [AU-NOTES](../appendices/bibliography.md#au-notes): tools/lz_decompress.py, disasm/sh2/master/lz.c, build/sh2/master/lz.o and sh2.elf (`lz_out` at `0x0602E674`), disasm/32x/sh2_lz.asm (the thunk), disasm/modules/shared/definitions_32x.asm, ROADMAP.md U-046, U-092, U-093 and M6, PORT_ARCHITECTURE.md, HARDWARE_TESTS.md, HISTORY.md
- [MK2](../appendices/bibliography.md#mk2): SH-2 code at `0x06002DF4`-`0x06002F84`, `0x060027F0`-`0x06002994`, `0x06004E24` (Slave dispatcher, table at `0x06004E64`), `0x06004F4C`, `0x0600509C`; 68000 code at `$00CFF8`, `$00D0AA`, `$00D0C8`, `$00D186`, `$0292F4`, `$028F38`-`$028FCA`, `$008E86`, `$0096DC`-`$009704`; ROM scan for ProPack headers, and all 80 ProPack files decoded and checked against their headers' sizes and CRCs
- [M68K-UM](../appendices/bibliography.md#m68k-um): §8 instruction timings (§8.6 for shifts)
- [CHAOTIX](../appendices/bibliography.md#chaotix): 68000 code at `$004E1C`-`$004E2E`
- [32X-HWM](../appendices/bibliography.md#32x-hwm): §4.4, 68000 access to the frame buffer; §4.1 p.74, ROM access competition
- [32X-TI](../appendices/bibliography.md#32x-ti): item 13, Word RAM DMA
- [AB32X](../appendices/bibliography.md#ab32x): SH-2 code at `0x060065BC`-`0x0600676A`; shape table at `$173900`, RLE data at `$061000`, palette at `$173700`; draw lists read in PicoDrive
- [SWA](../appendices/bibliography.md#swa): SH-2 code at `0x0600095C`-`0x06000AAE`
- [ECCO](../appendices/bibliography.md#ecco): SH-2 code at `0x06000F5C`-`0x0600100E`, `0x060002B4`-`0x060003DA`; the movie's chunks and blocks, all 180 pictures
- [CINEPAK-TD](../appendices/bibliography.md#cinepak-td): the stream format
- [D32XR](../appendices/bibliography.md#d32xr): liblzss/lzss.c, liblzss/lzss.h, w_wad.c, marsnew.c, marsdraw.c, src-md/vgm.c
