# ECCO the Dolphin CinePak Demo: analysis (10 October 2026)

Working notes, not part of the book. The chapter is `src/patterns/case-study-ecco.md`; the older notes on this ROM are in `notes/games/mars/CATALOG.md` (corrected the same day: no audio track, and the green formula).

ROM: `ECCO the Dolphin CinePak Demo (Japan, USA) (Developer Cart).32x` from the US romset, MD5 `c2b642fd…`, the same dump as the playground's `ECCO the Dolphin CinePak Demo (32X) (JU).32x`.

## Method

1. `sh2dis.sh ROM C000 A000 ecco` for the SH-2 program, read by hand.
2. `eccosim.py ROM OUT 180` runs the frame walker at `0x06001788` over the ROM bytes (stream `0x22020000`, staging `0x06010000`, stack `0x06040000`). 70.3 M instructions, 90 s.
3. PicoDrive, VRD headless frontend (`build_frontend.sh`), stock core, 1,500 frames, `VRD_VIDEO_DUMP_*` for every frame. The 32X picture appears at screen (32, 28) as 256 × 152; PicoDrive's RGB565 maps G5 to G6, so compare 5-bit values (R = v >> 11, G = (v >> 5 & 63) >> 1, B = v & 31).
4. `ecco_cinepak.py ROM STAGING.bin FFMPEG.rgb`, where `FFMPEG.rgb` is `ffmpeg -i movie.film -map 0:v -f rawvideo -pix_fmt rgb24` of the container cut out at ROM `$20000` (`$B84` + 2,183,040 bytes).

## Results

- **SH-2 run = PicoDrive's screen**: every one of the 676 distinct pictures after frame 140 equals one of the 180 decoded pictures (hash of the 256 × 152 window), none unmatched. Index steps: 671 of +1, 4 of +2 (the loop point: picture 179 and 0 are both all black, so the screen shows one black picture for 4 frames). Frame gaps: 671 of 2, 3 of 4, 1 of 5.
- **Reference decode = SH-2 run**: 180 of 180 pictures bit-exact with Sega's green (`y − (u + (v >> 1))`).
- **Reference decode = ffmpeg** with the usual green `y − int(u / 2) − v` (C division truncating toward zero): R, G, B all 100% equal at 5 bits in every 15th picture. With `u >> 1` instead G is 92 to 99% equal. Sega's green vs ffmpeg: R and B 100%, G 23% over all 180 pictures; mean G difference 8.5 levels of 255 (0 at picture 0, 24.7 at picture 78).
- **Container**: header `$B84` = 16 + `FDSC` 20 + `STAB` 2,912; 600 ticks/s, 180 samples, contiguous, info 2 = 20 for all, info 1 = 0, 20, 40, … (top bit clear), no sample with info 1 = `0xFFFFFFFF`. Samples 11,220 to 12,140 bytes, mean 12,128, total 2,183,040. Movie ends at `$235B04`.
- **Sample layout**: 16-byte header (BE32 length − 8 = sample − 8; BE16 width 256, height 160, strips 1; `fe 00 00 06 00 00`), strip `0x1000` 12-byte header, chunks `0x2000` (4 + 6n padded to 4: 1,540 for n = 256; n = 103 to 256, 256 in 134 pictures), `0x2200` (4 bytes, empty), `0x3000` (4 + 10,560, plus 4 trailing bytes in 141 pictures).
- **Blocks**: 460,800 blocks, all V4, no V1, no skip; no index beyond the codebook's entries; 254.07 distinct entries used per picture on average (min 103, max 256). Pictures 0 and 179 are all black.
- **68000** (`m68k.py`): `jsr $880868` draws the SEGA logo with `bsr $958` delay loops (about 140 frames in PicoDrive), clears CRAM and the plane, returns; then waits for `'M_OK'` at `$A15120`, clears `$A15120` and `$A15124`, copies 8 bytes (`bra.b *`) to `$FF8000` and jumps there. PicoDrive profile: 90.8% of the 68000's cycles at `$FF8000`; three addresses near `$0005F6` about 1,390 runs each.
- **Slave** (`0x06008120`): waits for the longword at `0x20004020` to read 0, then `bra .`. The decoder's code appears again at +`0x8000` in the Slave's image (literal-pool hits at `0x981C`, `0x930C` and so on), unused.
- **Frame buffer set-up** (`0x06000120`-`0x060001D2`): sets FM, sets the bitmap mode register's low byte to 2 (direct colour), writes the line table twice (12 × `0x100`, then 200 entries `0x100 + n × 0x140`, then 12 × `0x100`), clears 32,641 longwords from `0x24000200`, flips FS and repeats for the other buffer.

## Per-picture counts (mean of pictures 1 to 179; record k = copy of k−1 + decode of k)

| Group | Instructions | Issue clocks | Load-use pairs |
|-------|--------------|--------------|----------------|
| Copy (`0x06000220`-`0x06000272`) | 195,197 | 234,108 | 19,458 |
| Block loop (`0x060002B4`-`0x060003DC`) | 134,673 | 147,312 | 31,081 |
| Codebook conversion (`0x06000F5C`-`0x06001010`) | 66,568 (65,897 to 66,617) | 70,899 | 1,280 |
| Chunk handler | 2,519 | 3,054 | 268 |
| Walker | 29 | 32 | 2 |
| Total | 398,986 | 455,405 | 52,089 |

Memory accesses: cartridge cache-through 12,103 bytes + 5 halfwords + 10 longwords = 12,128 bus cycles (block loop 10,560 bytes, conversion 1,536); SDRAM longword stores 21,789 and word stores 1,028 (block loop 20,486); SDRAM cached longword reads: block loop 20,530 (codebook), copy 19,469 (staging); frame buffer longword stores 19,456.

Issue clocks follow Hitachi's table (bt/bf taken 3, bt/s and bf/s taken 2, bra/bsr/jmp/jsr/rts 2, `mul.l` 2, everything else 1). Load-use pairs follow `src/sh2/pipeline.md` (a load, then an instruction reading its register: +1; a load into the same register: none).

## Cost bracket (SH-2 clocks per picture)

| | Low | High |
|---|-----|------|
| Issue clocks | 455,405 | 455,405 |
| Load-use | 52,089 | 52,089 |
| Cartridge reads, 12,128 × (8 or 17 − 1) | 84,896 | 194,048 |
| Staging line fills, 4,864 × (12 − 1) | 53,504 | 53,504 |
| SDRAM stores, (4 − 1) × 21,789 + (2 − 1) × 1,028, if unhidden | 0 | 66,395 |
| Frame buffer stores, 19,456 × 7 (3 + 5 clocks), if unhidden | 0 | 136,192 |
| Total | 645,894 (1.68 frames) | 957,633 (2.49 frames) |

Assumes the code and codebook hit the cache (the boot ROM turns it on; PicoDrive's HLE start does not). Over the line between two and three frames (768,000) the manual cannot say which side a console is on.

## Loose ends

- The block loop's end-of-row step is a literal `0x600` at `0x060003E8` (and `0x06000558` in the inter routine): 4 × pitch − 512 for a 512-byte pitch, so decoding into the 640-byte frame buffer rows needs `0x800` there and pitch 640 in r5.
- A third, compiled-C style block loop sits at `0x0600156C`-`0x06001786` (`mul.l` by 2 for the index scale, `exts.w` everywhere). No literal anywhere in the program points at it, so it looks like dead code. Not run.
- `0x0600055C`-`0x060005E8`: a routine that draws 8 hex digits as 8 × 8 glyphs of 16-bit pixels from a font at `0x060006A0` into the frame buffer; it never ran in the 1,500-frame profile. The only reference to its address is a literal at `0x06000284`, whose user was not found. Not traced.
- The interrupt handlers (`0x060005FC` and following) are stubs that clear a flag and `rte`; the demo paces by the VBLK bit in the copy routine, not by interrupts.
- Not checked: the end of the inter block loop beyond the skip path; the 0x2100/0x2300 update loops beyond their first instructions (read, not run).
