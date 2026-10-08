# Harvested techniques: patterns/streaming.md

Target: `patterns/streaming.md`. 12 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from D32XR -->
### Resumable LZSS decoder into a ring buffer
- Source: D32XR, liblzss/lzss.c:38-176, liblzss/lzss.h, w_wad.c:72-79, 695-708 (licence: id limited-use; lzss.c has no header)
- What it does and why it is clever:
  - **Format.** A flag byte covers 8 items LSB-first. A literal is one byte. A match is 2 bytes: a 12-bit distance (`b0<<4 | b1>>4`) and a 4-bit length+1. Length 1 is the end marker.
  - **Variant.** Windows larger than 4 KB use a 16-bit distance and 8-bit length.
  - **Streaming.** `lzss_read(chunk)` can stop mid-run and saves its state (run, runlen, runpos, flag bit), so callers pull exactly N bytes at a time: one picture row (DrawJagobjLump) or one VGM read-ahead block.
  - **Copies.** Output wraps by masking, and copies are split at the wrap. `lzss_copy` uses 16-bit moves when source and destination have the same alignment.
  - **Marking.** A compressed lump is flagged by bit 7 of its name's first character.
- Key numbers: LZSS_BUF_SIZE 0x1000.
- Target chapter: patterns/streaming.md
- Evidence: code only

<!-- from D32XR -->
### Streaming compressed VGM music on the 68000
- Source: D32XR, src-md/vgm.c:32-200 (licence: id limited-use; no header)
- What it does and why it is clever: The same LZSS state machine runs on the 68000. A song is decompressed a fixed read-ahead window at a time into a ring buffer for the Z80 player instead of being expanded whole. `lzss_compressed_size` finds where appended PCM data starts. RF5C68 sign-magnitude samples are converted to biased unsigned bytes in place, and loop markers (0xFF) are recorded on the way.
- Key numbers: VGM_READAHEAD / VGM_MAX_READAHEAD (constants in the 68k header).
- Target chapter: patterns/streaming.md
- Evidence: code only

<!-- from D32XR -->
### RoQ vector-quantised video decode
- Source: D32XR, roq_read.c:132-393, 424-471 (licence: id limited-use; header grants "You may freely use this source code" with attribution to Tim Ferguson)
- What it does and why it is clever:
  - **Block coding.** Frames are 16x16 macroblocks split into 8x8 and then 4x4 blocks, each tagged with a 2-bit code. MOT = skip. FCC = copy from the previous frame with a 4-bit x/y motion vector plus the chunk's mean offset. SLD = one 4x4 codebook entry at 2x. CCC = subdivide.
  - **Codebook.** 2x2 YUV cells, converted to RGB555 once per codebook chunk with integer maths (Y·8192, U·2816, V·5888, about 1.44V, 0.34U+0.72V and 1.72U), so the per-frame work is pure 32-bit copies.
  - **Flag reads.** One 16-bit flag word yields eight 2-bit codes through shift-and-mask.
- Key numbers: 256 cells, 256 quad-cells; clamp LUTs of 64 entries offset by 16, already shifted into BGR555 bit positions.
- Target chapter: patterns/streaming.md
- Evidence: code only

<!-- from D32XR -->
### RoQ pipeline: DMA-overlapped frame copy and audio-clock sync
- Source: D32XR, marsroq.c:438-560, 615-672, 711-937 (licence: MIT)
- What it does and why it is clever:
  - **Direct DMA into rings.** CD chunks are DMA'd straight into memory reserved in a video or audio ring buffer (zero copy). `roq_lazybuffer` asks for more data whenever both rings have over 1 KB free, called from busy-wait loops.
  - **Previous-frame copy.** Motion compensation needs the last frame, so after each 16-row band is decoded, SH-2 DMA channel 1 copies that band to `canvascopy` while the CPU decodes the next band.
  - **Audio as the clock.** `sndtime = samples<<16/22050 + 267 ms`; frames whose deadline has passed skip the wait.
  - **Spare memory.** Canvas memory a small video does not need is given to the audio ring.
- Key numbers: video ring 0xE000, audio ring 0x5000 (up to 0xF000); frametics = 16.16 vblanks per frame.
- Target chapter: patterns/streaming.md
- Evidence: code only

<!-- from D32XR -->
### Contiguous-allocation ring buffer (bip buffer) between CPUs
- Source: D32XR, mars_newrb.c:34-281, mars_newrb.h (licence: MIT)
- What it does and why it is clever:
  - **Two-phase API.** `walloc`/`wcommit` and `ralloc`/`rcommit` always hand out contiguous blocks, so DMA and parsers never see a wrap.
  - **Early wrap.** If the tail is too short, the writer records `maxreadpos` (where data ends) and wraps to 0.
  - **Positions.** They run in [0, 2·size) and are reduced only when both read and write pass `size`, which separates full from empty without a counter.
  - **Locking.** A TAS spin lock with a roughly 512-iteration backoff limits bus traffic; the lock can be disabled for single-producer cases.
- Key numbers: header aligned to 16 bytes; 3 cache lines purged per operation.
- Target chapter: patterns/streaming.md
- Evidence: code only

<!-- from D32XR -->
### Jaguar-era decompress-and-convert (historical)
- Source: D32XR, r_phase5.c:37-201 (licence: id limited-use)
- What it does and why it is clever: The original phase 5 decoded LZSS textures into the zone and turned each 8-bit literal into 16-bit CRY colour through `vgatojag[]` in the same pass. The output is twice the input size. A bespoke LRU allocator (`R_Malloc`) purged blocks not locked by the current `framecount`. It is compiled out on the 32X but shows the "stream, decode and convert at once" pattern the MARS cache replaced.
- Key numbers: MINFRAGMENT 64; 8-byte phrase alignment.
- Target chapter: patterns/streaming.md
- Evidence: code only

---

<!-- from VRD/AU/MARSDEV -->
### LZ decompression moved to the SH-2 (patch the routine, not the callers)
- Source: AU-NOTES, ROADMAP.md:1603-1776; disasm/sh2/master/lz.c:1-215; disasm/32x/sh2_lz.asm:1-80
- What it does and why it is clever: An 8-byte size-neutral patch at `LZ_Decompress`'s entry covers all 92 call sites. The thunk:
  1. masks interrupts and gives FM to the SH-2;
  2. passes the source as a cached cartridge address, plus a framebuffer offset;
  3. polls with a timeout;
  4. takes FM back and copies to the 68K buffer.

  The SH-2 decompresses into SDRAM, not the framebuffer: zero bytes cannot be byte-written, and back-reference reads from the framebuffer cost 5-12 waits. It then writes words out.
- Key numbers:

  | | 68000 | SH-2 |
  |---|---|---|
  | Cycles per output byte | 285 | 59.7-60.7 |
  | Largest block (27,872 B) | 62 frames | 4.4 frames |
  
  14.1-14.4× faster in wall clock. The quarter-boundary stall drops from 74-76 frames to about 5. Over 12,000 frames the patched build ran 198 frames ahead, with 31 of 31 matched frames bit-identical.
- Target chapter: patterns/streaming.md
- Evidence: emulator measured (PicoDrive with the opt-in SH-2 timing model added in Aerobiz U-093; Ares)

<!-- from VRD/AU/MARSDEV -->
### The KOEI LZ format and why to transcribe it literally
- Source: AU-NOTES, disasm/sh2/master/lz.c:46-160; tools/lz_decompress.py:1-50
- What it does and why it is clever:
  - **Structure:** a control byte covers 8 tokens (bit set = literal). Matches use a prefix-coded length (the position of the first set bit picks 0-13 extra bits) and nine distance buckets.
  - **Quirk kept on purpose:** `read_bits(n)` plus the caller's `ANDI #$7FFF` consumes n+1 bits.
  - **Interleaving:** literals and refill words share one pointer, and stream words are little-endian.
  - **Copies:** byte-forward, so overlapping copies replicate runs.
  - **Safety:** overrun is refused per token with 0x100 bytes of headroom.

  The 68K, the Python tool and the SH-2 C version are kept diffable.
- Key numbers: 22,528-byte output; FNV-1a `0x3640A33D`, matched independently.
- Target chapter: patterns/streaming.md
- Evidence: emulator measured (PicoDrive)

<!-- from VRD/AU/MARSDEV -->
### Brute-force asset location by decompressing at every offset
- Source: AU-NOTES, HISTORY.md:2035-2057; ROADMAP.md:929-965
- What it does and why it is clever: The map was neither raw nor in the obvious loader. The reimplemented decompressor was run at every even ROM offset with early abort against the first three expected tiles, giving exactly one hit at `$088CF8`. The nametable turned out to be linear (tiles 1..704), so the map is a plain 256×176 bitmap. A 22 KB exact match also validates the decompressor.
- Key numbers: 704 tiles; 100.00% byte match with VRAM.
- Target chapter: patterns/streaming.md
- Evidence: emulator measured (savestate VRAM comparison)

<!-- from VRD/AU/MARSDEV -->
### Forwarding Genesis tile uploads to the SH-2 copy
- Source: AU-NOTES, PORT_ARCHITECTURE.md:353-382; disasm/sh2/master/fb.c:477-558; KNOWN_ISSUES.md:649-720
- What it does and why it is clever:
  - **Hooks:** the game edits map tiles (route dashes, report title bar) before upload, so both upload choke points are hooked: CPU `BulkCopyVDP` and the DMA thunk.
  - **Gate:** the full VRAM-write command shape, which excludes VSRAM.
  - **Address decode:** the VRAM address is unfolded with `(cmd>>16 & $3FFF) | (cmd&3)<<14`.
  - **Transport:** in-range words (slots 1-704) pass through a framebuffer mailbox in `$800`-word chunks.
  - **Decode:** the SH-2 decodes 4bpp nibbles to palette 16-31 at the right cells, honouring the burst's auto-increment, and marks dirty only on real change.
  - **Cost control on Ares:** non-final chunks set bit 31 to skip the redraw.
- Key numbers: 113 of 114 oracle frames exact; Ares 1:1 redraw 2-3 frames; 435 redraws observed against about 40 predicted, so the next lever is redraw count.
- Target chapter: patterns/streaming.md
- Evidence: emulator measured (PicoDrive/Ares)

---

<!-- from AB-DISASM -->
### Spreading big VRAM jobs over frames
- Source: AB-DISASM, disasm/modules/68k/vdp/VRAMBulkLoad.asm:1-79 ($01D568); disasm/modules/68k/vint/VInt_Handler2.asm / VInt_Handler3.asm ($001390 / $001404)
- What it does and why it is clever: Two complementary ways to bound work per frame:
  - Uploads are cut into 4 KB DMA chunks, with frame waits in between.
  - Nametable fills and readbacks are capped at 4 rows per V-blank by the handler itself, which resumes from a saved command long the next frame.

  Both keep each V-blank's VDP work small, so music and input stay smooth while large screens load.
- Key numbers: 4 KB per chunk; 4 rows per frame.
- Target chapter: patterns/streaming.md
- Evidence: code only (shipped)

---

<!-- from D32XR (hardware survey) -->
### d32xr hardware survey: Data streaming and banking
- WAD in cached ROM at 0x02000000 + WADBASE*1024 (wadbase.s:7; Makefile:31); lumps used in place via `I_RemapPtr` (w_wad.c:556-636); compressed lumps LZSS-decoded into frame-buffer scratch (:621-631). Textures copied on demand into an SDRAM zone cache with a 3-frame lifetime (r_phase9.c:13-247; r_cache.c:173-240; r_local.h:483-484).
- SSF banking: header "SEGA SSF", ROM end 0x4FFFFF (crt0.s:30-49; mars-ssf.ld:37). Master owns bank 6 (COMM0 cmd 0x16), slave bank 7 (via COMM4; 68000 replies 0x1000) (marsnew.c:460-466; marshw.c:705-720; 68000 side crt0.s:548-552, 1591-1633). `I_RemapPtr`: page = (p-0x02000000)>>19; new address = (p&0x7FFFF) + 512K*bank + 0x02000000, above 0x02300000 when ROM > 4 MB (marsnew.c:471, 723-741). Cache purged after switching (:711). The level's segs/nodes page kept resident (p_setup.c:962-979; reselected per frame r_main.c:718).
- 68000 to SH-2 FIFO / DREQ: 68000 side `dma_to_32x` (crt0.s:3140-3245): master CMD with 0xFF10, clear 68S, source/destination/length (rounded to 4 words, "FIFO operates on units of four words"), set 68S, write words to 0xA15112 polling FIFO full (bit 7 of 0xA15107), finish with 0xFF20. SH-2 side `Mars_HandleBeginDMARequest` (marshw.c:915-956): waits for 68S, DMA channel 0 SAR0=0x20004012, DAR0=0x20000000|dest, TCR0=word count, word transfers, DREQ edge; destination callback can refuse; `Mars_HandleEndDMARequest` polls TE (:958-973).
- RoQ: 68000 streams from CD into Word RAM and DMAs chunks (src-md/scd_roq.c:42-229); flags in COMM8 (marshw.h:163-166; marsroq.c:503-540); SH-2 ring buffers video 0xE000 / sound 0x5000 bytes (marsroq.c:36-37); decodes straight into a direct-colour frame buffer; previous frame copied to SDRAM by master DMA channel 1 in 16-byte auto-request units (marsroq.c:628-670).

