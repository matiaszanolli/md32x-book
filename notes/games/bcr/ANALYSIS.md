# BC Racers (32X): analysis notes

Working notes, not part of the book. Started 2026-10-12. Citation key `BCR`.

Evidence levels: **ROM** = read from the dump's code or data. **Emulator** = observed in the VRD project's PicoDrive libretro core (stock, recompiler, unless "timing model" is said), not a console. **Timing model** = the same core built interpreter-only with the real boot ROMs and `VRD_SH2_TIMING=1` (`../tools/build_miss_core.sh`), which charges the 32X manual's wait states and models the cache's tags.

## The dump

- `BC Racers (USA).32x` in the US romset (`32X-ROMSET`), 3,145,728 bytes, MD5 `35a11e021ca0b7ff909e4774eb8b3236`. Header checksum is `$0000`, so the dump **cannot be checked** against its header; the MD5 was not found in any public list (web search, 12 October 2026). No sign of patching was seen, but nothing proves it is the retail original.
- Header: `SEGA 32X`, `(C)T-115 1995.APR`, `BC RACERS X`, `GM T-11505B-00`, user header `MARS CHECK MODE`. Developer Core Design (`COPYRIGHT 1995 CORE DESIGN LTD` at `$048720`); credits at `$064640`: programmed by Martin Gibbins, "Gilbert the Goat", John Kirkland and Stef Walker; graphics by Toby Gard; graphic support Stuart Atkinson, Richard Mort(on?) (string continues). Published in North America by Front Street Publishing (WP-BCR).
- End of ROM (`$2F6BEC`, `$2FF536`) holds stray text from a Multi-Edit macro source (American Cybernetics), padding from the developer's disk.

## Layout (ROM)

- **SH-2 image:** user header copies `$011798`, `0x32EB0` bytes, to `0x06000000`. Master entry `0x060017E4`, VBR `0x060016C4`, stack `0x06040000`; Slave entry `0x06032CC0`, VBR `0x06032BA0`, stack `0x0603F500`.
  - `0x06000000`-`0x060016C3`: data. Menu and race text in English, German and French ("BC RACERS MENU", "RACE DIFFICULTY", "LETZTE RUNDE", "MAUVAISE DIRECTION" …), pointer tables into ROM `0x0205xxxx`-`0x0206xxxx` (handlers of the C code).
  - `0x060017E4`-`0x060031C7`: SDRAM code (Master start-up, interrupt handlers, ground, sprites, scenery, Slave job helpers).
  - `0x060031C8`-`0x06032674`: **193,709 zero bytes** copied from the cartridge at boot (BSS stored in the image). The map at `0x060081F4` and game variables live in this range at run time.
  - `0x06032674`-`0x06032EAF`: Slave main loop, vblank work, Master main start, Slave start-up.
- **SH-2 C code runs from the cartridge** through the cached window: `$044648`-about `$06C000` (main at `0x02048648`). Compiled C (Hitachi-style prologues, `exts.w` everywhere). The Hitachi runtime (variable shifts by a computed jump into a run of `shar`, block copies) sits at `$2F5xxx`-`$2F6xxx` (e.g. `0x022F6028`, `0x022F6040`), called from 78 sites.
- `$044648`-`$048647`: eight 32 × 32 word tables, each a permutation of 0-1023 (the texel offsets of a 32 × 32 tile in one of 8 orientations: 0-3 rotations by 0/90/180/270 degrees, 4-7 the mirrored ones). Checked: each table is a permutation.
- **68000:** program in work RAM `$FFC000`, a copy of cartridge `$010BEA` (4 KB checked).
- Ground texels (race 1): pixel base `0x0207B692` (`[0x0603E1D8]`), 1 KB per 32 × 32 tile; haze table `[0x060348D8]` = `0x0208AA92`.

## Division of labour (ROM + emulator)

| CPU | Job |
|-----|-----|
| 68000 | Command server: polls `$A15120` (`$FFC038`), runs the Master's command through a table at `$FFC05C`, clears `$A15120`. 82% of its time in that poll in a race (stock profile). Commands seen: 5 (sets a flag), 12 (reads `$A10001` >> 6 into `$A1512A`), 13 (clears VRAM), 14/15/17 (write backdrop colour 0 = black / `$0EEE` / `$0007`: debug markers), 18 (stores a word: sound request). Draws the Mega Drive picture, of which only the sky shows (lines 16-79, where the 32X has colour 0) plus lines 0-15 |
| Master SH-2 | Everything else: the game in C from ROM, ground rows 0-31, top half of each sprite, scenery projection and sort, vblank flip and palette, H interrupt |
| Slave SH-2 | A generic worker: ground rows 32-63, bottom half of each large sprite, frame-buffer clears, cache purge on request |

## Start-up and interrupts

- Master (`0x060017E4`): clears the four CMD/H/V/PWM clear registers, FRT set-up as Sega's sample (TIER 0, TOCR `$E2`, OCRA 1 …), waits for `0x20004020` = 0 and for `SLAV` in `0x20004028`, writes `$80` to `0x20004000` (FM), mask `0x0E` (V, H, CMD) to `0x20004001`, SR = `$20`, jumps to `0x060326F8`: handshakes with the 68000 (commands 12, 13, 5), sets bitmap mode `$81` (packed pixel, PRI 1), clears both frame buffers with CPU word stores and writes standard line tables (line *n* at word `$100 + $A0·n`), then `jmp 0x02048648`.
- Slave (`0x06032CC0`): FRT set-up, waits for `0x20004020` = 0, writes `SLAV` to `0x20004028`, SR = `$20`, jumps to `0x06032674`. It never writes its interrupt mask register: it takes no interrupts.
- **Neither CPU writes CCR at start-up.** The Master relies on the boot ROM's CCR (`$11`, 4-way); the Slave too, plus a job `0x060030DE` (CCR = `$11`, purge and enable) that the Master sends from 10 sites in ROM (`0x060030BE` posts it and waits). `PD_CCR_LOG` with boot ROMs: Slave `0x000001A2`, Master `0x000001BE` (boot ROMs), then the Slave job at `0x060030E2`.
- Dispatcher (`0x06001888`, Master; `0x06032D34`, Slave): one entry, `(SR >> 2) & $3C` indexes a table. Master: PWM 6 `0x06001A48`, CMD 8 `0x06001A14` (counter `0x06001A38`), H 10 `0x060019E4`, V 12 `0x060019A8`, VRES 14 `0x06001908`.
- **H interrupt every line for nothing.** Mask `0x0E` (read at run time, low byte of `0x20004000`), HCOUNT (`0x20004005`) = 0, HEN = 0: 224 interrupts a frame. The handler clears the interrupt, touches the FRT and increments `0x06001A04` through the cache-through view. No other code reads `0x06001A04` (searched the whole ROM disassembly for `0x06001A04`/`0x26001A04`; the only other hit is the image copy itself). Cost: stock profile 7.2k clocks/frame in the handler; timing model 8.2k + 6.4k in the dispatcher = 14.6k/frame (3.8% of the Master).
- V handler (`0x060019A8` → `0x06032A66`): counts vblanks in `0x06032B90`; if the flip flag `0x06032B92` is set, clears it, toggles FS (`0x2000410B`) and sends `[0x06032B94]` (two scroll words for the Mega Drive sky) through `0x2000402A`/`0x2000402C`; then, **if COMM `0x20004022` is negative**, rebuilds 255 palette entries (`0x20004202`-) from a source table with a fade level (`0x20004022` & 31) subtracted per channel. In the race `0x20004022` stays `$8000` (watched 600 frames, both modes): level 0, recomputed every vblank. The fade counter at `0x0603E1E8` (`0x02055B06`) sets it with `| $8000` and never clears bit 15. Cost 7.2k (stock) / 9.1k (timing) clocks a frame; 255 palette writes a frame (miss log).
- VRES (`0x06001908`): Sega's handler shape; reads RV at byte 6 of `0x20004006` (`vresscan`: the wrong byte), clears DMAOR and writes CHCR0 correctly (pointer `0xFFFFFF8C`, no slip), waits for `68UP` and `S_OK`, copies the SH-2 image again from the user header and restarts.

## The Slave as a worker

- Main loop `0x06032676`: clears COMM `0x2000402E`, polls it until non-zero, loads a job record at `0x060326B0` (function pointer, r1-r14, GBR at +60), calls the function, loops (clearing the word again).
- The Master posts jobs by filling the record and writing 1 to `0x2000402E`; it waits for 0 when it needs the result. Job posters: ground rows `0x06002438`, ground spans `0x060024E4`/`0x0600263C`, sprite halves `0x06001F44`/`0x06002294`, clears `0x06003056`/`0x06003088`/`0x060030E8`/`0x06003018`, cache purge `0x060030BE`.
- **Posting without checking.** `0x06002438`, `0x060024E4` and `0x06003056` write the record and the word without first waiting for the Slave to be idle (the sprite posters do wait, `0x06001FD0`, `0x060022E6`). If the Slave were still busy, the new record could be overwritten or its flag cleared by the loop's `mov #0` after the previous job. In practice the clear posted before the logic steps is long finished when the ground is posted. A latent race, not seen to fire.

## The race loop (ROM `0x02059734`-)

Per picture (`0x020597AA`-):
1. `0x06002E64` (set-up), read the vblank counter `0x06032B90` into `0x0603E230`, request the flip (`0x06032840`: flag `0x06032B92` = 1, counter = 0).
2. One player: `0x06003056`(`0x24001600`, `$5000`): **waits for the flip flag to clear** (polls `0x26032B92`, cache-through SDRAM), then posts a Slave clear of 10,240 words (64 sky lines, 16-79) by CPU word stores (`0x06002D9C`). Two players: `0x060030E8` → `0x06002DB6` (two 17,920-word clears).
3. Clamp `0x0603E230` to 4.
4. **Game logic once per elapsed vblank** (`0x0205987A`-`0x0205991E`): count from `0x0603E232` (the low word) into `0x06034C24`; each step: per-player code `0x02048BB8`, `0x02060634`, `0x02055B06` and `0x02055B90` (two passes over 256 object slots of 56 bytes at `0x06034C30`, 14 KB, calling handlers through tables at `0x060010B8`/`0x06000F4C`), `0x0206A750`.
5. Scenery `0x02059920`-, camera, `0x0204B680` (ground for each player: camera from sine/cosine tables `0x02052598`/`0x02052998`, six parameters to `0x060031CC`, then `0x06032960`, or `0x060329E6` when `[0x0603E484] >> 2` = 6), sprites, HUD commands to the 68000.
- So the logic keeps game time against the clock, with **at most four steps a picture**; a picture longer than four frames slows the game. Watched (`VRD_WATCH=0x2603E230:4`, 600 race frames from frame 1,800): stock 2 in 582 frames, 3 in 18; timing model 4 in 586, 5 in 14 (5 is clamped to 4).

## Ground ("Mode 7")

- **Screen:** the 3D view is lines 16-143 (frame-buffer base `[0x06034B40]` = `0x24021600`, clip height `0x06001A6E` = 2 × 64). Lines 16-79 are cleared to colour 0 (sky, scenery sprites on top); lines 80-143 are the ground, 64 lines. Palette entry 0 alone has the through bit and PRI = 1 (bitmap mode `$8081`, read at run time), so colour 0 shows the Mega Drive picture. The 32X frame buffer rendered from the state (colour 0 marked): lines 0-79 colour 0 except scenery sprites, so the sky and the top 16 lines are the Mega Drive's; **the bottom panel (position, lap, portraits, lines about 144-200) is in the 32X frame buffer**. Whether the panel is redrawn every picture was not traced.
- **Row set-up `0x06002438`/`0x060024A4`:** 64 rows, Master rows 0-31, Slave 32-63 (the Slave's call starts at row 32: r7 = 514, table + 512). For row *i*, divisor *d* = 2 + 16*i*; four 32/32 divides on the hardware divider: (*A*/*d* + *u*₀, *B*/*d* + *v*₀, *C*/*d*, *D*/*d*) into a 16-byte entry at `0x06032EB4`. The first quotient is read from `0xFFFFFF1C`, the other three from DVDNTL (`0xFFFFFF14`). *A*-*D*, *u*₀, *v*₀ from `0x060031CC`, computed per player in `0x0204B680`.
- **Spans `0x060024E4`:** lines split in two halves (Master first, Slave second; the Slave job is posted first, then the Master draws). The Master's first 8 lines (`0x0600252E`-`0x0600259C`, the rows nearest the horizon) go through a 256-byte colour table per line (haze, base `[0x060348D8]` + `$780`, −256 per line, indexed by the sign-extended texel); the rest `0x0600259E`-`0x060025FE`.
- **Per texel (32 instructions, 33 with haze), 160 per line, each written twice as one word:** map word from the frame buffer (`0x24012E00`, 128 × 128 words, the unused tail of the buffer; both buffers hold a copy); tile record pair from SDRAM `0x060332B4` (pixel base, orientation table); in-tile offset word from the orientation table in ROM; texel byte from ROM; (haze byte from ROM); word store. Map index ((*v* >> 17) & 127, (*u* >> 17) & 127); in-tile (*u* >> 12) & 31, (*v* >> 12) & 31: so each map cell is 32 × 32 texels, with *u*, *v* in a 24.? fixed point.
- **Map set-up `0x06002358`** (from `0x020440CE`): clears the 4 KB record table, then rewrites the 16,384-word map at `0x060081F4` in place: tile number (6 bits, `& $FC`) and orientation (3 bits, after XOR with `[0x060348C0]` << 13) become a record offset; record = (pixel base + tile × 1 KB, `0x02044648` + orientation × 2 KB). 64 tiles × 8 orientations = 512 records of 8 bytes.
- Variant `0x0600263C`/`0x0600274C` (for `[0x0603E484] >> 2` = 6): 16 haze lines, records read through `0x260332B4` (cache-through). Not traced further.

## Divider

`divuscan.py`: five sites read `0xFFFFFF1C`: sprite clip `0x06001F62`, `0x06001FA0`; row set-up `0x060024AA` (first of four divides; the other three read `0xFFFFFF14`); the C code's divide helpers `0x06002E3C` (returns 0 if the divisor is 0) and `0x06002E54` (no check), reads at `0x06002E48`/`0x06002E5C`, called from 6 and 9 sites in ROM. `0x06002B58` (scenery) reads `0xFFFFFF14`.

## Sprites and scenery

- `0x06001F44` (and `0x06002294` for unscaled): clip against `0x06001A6C`/`0x06001A6E`, compute steps with the divider (reads `0xFFFFFF1C`), **wait for the Slave to be idle** (`0x06001FD0`), and if more than one line, give the Slave the bottom half (record + post) and draw the top half itself.
- Blitters, all byte stores through the overwrite image (so colour 0 is skipped by the VDP): `0x06001BB8`/`0x06001BE4` scaled copy (carry-chained 16.16 step with `addc`), `0x06001D98`/`0x06001DC4` scaled with a colour table, `0x06001EBA`/`0x06001EE6` blend: reads the destination byte, looks up (src << 8 | dst) in a 64 KB table, writes a doubled word (shadows / translucency); `0x0600222C`/`0x0600223C` unscaled byte copy; `0x0600226C` colour-table pass over the destination.
- Scenery `0x06002838`: world objects (12-byte entries at `0x0603C97C`, ended by −1), Manhattan-ish distance cull (`|dx| + |dy|/2` against `$1518`), rotate/project (`0x06002BA0`, divide `0x06002B58`), insert into a depth list (`0x06002C22`); then a 40 × 40 window of a byte grid (`[0x06000B9C]`, 16 KB) around the camera, one object per non-zero cell (`0x06002A30`).

## Sound (ROM, not run)

`0x0600312A` (16 sites): DMAOR = 0; PWM mono `0x20004038` ← 0 ×3; PWM control `0x20004030` = `$0385` (RTP set: DREQ to DMA); cycle `0x20004032` = r6; DMA channel 1: SAR1 = r4, DAR1 = `0x20004039` (the low byte of the mono pulse register), TCR1 = r5, CHCR1 = `$10E1` (source increment, byte, DREQ, enable); DMAOR = 1. So 8-bit samples go straight from the cartridge to PWM by DMA, one byte per PWM request. Not checked whether a byte write to `0x20004039` is valid on hardware.

## Measurements

All from the race reached by `input.py` (below), track 1, one player.

### Frame rate

| Run | Pictures a second | Frames per picture |
|-----|-------------------|--------------------|
| Stock PicoDrive, frames 1,500-2,999, FS read every frame | 29.7 (743 flips in 1,500) | 2: 729, 3: 13 |
| Same, 240 frames dumped: every flip shows a new picture | | |
| Timing model + boot ROMs, power-on, frames 1,700-3,499 | 14.0 (420 in 1,800) | 3: 8, 4: 284, 5: 127 |
| Timing model from the frame-1,800 state, `VRD_TIMING_CCR=1` | 14.45 (144 in 598) | 4: 121, 5: 22 |
| Same, under the profiler | 15.05 | 4: 149 |
| Timing model without boot ROMs (Master cache never on) | 1.1 | 23-57 |

### Stock profile (sleep core, `VRD_PROFILE_PC`, 600 frames from the frame-1,800 state)

Clocks per frame (×2 for per picture). Master executed 78.7% of the run, slept on `0x2E` 28.6M clocks (12%). Slave executed 50.7%, slept on `0x2E` 127.5M (55%; sleep totals run high).

| Master | /frame | Slave | /frame |
|--------|--------|-------|--------|
| C code in ROM | 72,487 | ground `0x060025B8` | 84,582 |
| ground `0x060025B8` | 64,393 | idle loop `0x0603267C` | 41,202 |
| flip wait `0x06003056` | 35,132 | sprites `0x06001BB8` | 28,236 |
| sprites `0x06001BB8` | 26,250 | clear `0x06002D9C` | 25,608 |
| ground with haze `0x0600254C` | 22,154 | sprites `0x0600222C` | 11,647 |
| sprite set-up and wait `0x06001F44` | 16,688 | | |
| scenery `0x06002838` | 12,575 | | |
| sprites `0x0600222C` | 11,427 | | |
| scenery grid `0x06002A30` | 7,710 | | |
| H interrupt `0x060019E4` | 7,163 | | |
| vblank palette `0x06032AD2` | 7,158 | | |

### Timing-model profile (miss core, `VRD_TIMING_CCR=1`, 600 frames from `tst1800.bin`, 150 pictures)

Clocks per frame, including the model's waits (checked: the ground loop's 251k a picture = stock 173k + the simulator's 78k of model waits). Master executed 79.0% of the run, slept 0.4M clocks; 21% is not attributed (accounting gap of the profiler under the timing model, not explained). Slave executed 34.0%, slept 151M (66%) on `0x2E`.

| Master | /frame | ×4 per picture |
|--------|--------|----------------|
| C code in ROM | 117,819 | 471k |
| ground (`0x060025B8` + `0x0600254C` + set-up) | 63,400 | 254k |
| flip wait `0x06003056` | 37,921 | 152k |
| sprites (`1BB8`, `222C`, `1F44`, `1B80`, `1B38`, `1EBA`, `1B9E`) | 40,300 | 161k |
| scenery (`2838`, `2A30`, `2BA0`, `2C22`, `2B58`) | 16,700 | 67k |
| H interrupt + dispatcher | 14,571 | 58k |
| vblank palette | 9,110 | 36k |

Slave per frame: ground 57,100, sprites 33,900, clear 17,938, idle loop 21,183 executed.

Hottest ROM: `0x02055B90`/`0x02055B06` (object passes), then `0x02063Dxx`, `0x0206A8xx`, `0x020608xx`-`0x02061xxx`.

### Miss log (timing model, same run), per frame

Master: cartridge 51,123 hits / **2,513 misses (77,912 wait clocks)**; SDRAM 115,100 hits / 1,615 misses (17,767); SDRAM cache-through reads 2,058 (22,639: polls and variables); SDRAM writes 7,436; frame buffer 1,295 reads (7,770), 4,008 writes (8,016); palette 255 writes. Slave: cartridge 3,127 / 516 misses (16,008); frame buffer 1,267 reads, 6,561 writes (13,122). Master misses by 16 KB: `0x06034000` 615 (object slots), `0x02060000` 602 (C code), `0x02044000` 479 (orientation tables), `0x06038000` 333, `0x06000000` 221, `0x0207C000` 203 (texels), `0x02048000` 173, `0x02054000` 172, `0x0603C000` 147, `0x02084000` 131, `0x02088000` 117 …

On the book's figures (64-136 clocks a cartridge line, against the model's 31 waits), the Master's 2,513 cartridge misses a frame would cost 161k-342k clocks a frame instead of 78k: 0.33M-1.06M more per four-frame picture. Estimate only.

### Ground cache simulation (`groundsim.py`)

One picture, track 1, cold cache per CPU (warm in brackets):

| | Master rows 0-31 (8 with haze) | Slave rows 32-63 |
|-|-------------------------------|------------------|
| Texels | 5,120 | 5,120 |
| Texel misses | 793 (777) | 262 (232) |
| Orientation table misses | 394 (378) | 260 (214) |
| Haze table misses | 13 | — |
| Tile record misses (SDRAM) | 73 | 9 |
| Instruction fetch misses | 10 | 5 |
| Cartridge line fills | 1,200 = 0.23 a texel | 522 = 0.10 a texel |
| By the manual: fills / FB map reads / FB stores | 77-163k / 36-72k / 15-26k | 33-71k / 36-72k / 15-26k |

The far rows (Master) step across more texture per pixel and touch more lines. Instructions: Master 8 × 160 × 33 + 24 × 160 × 32 = 165k, Slave 164k (1 clock each, no stalls counted). With SDRAM copies of the tiles and tables, the Master's 1,200 fills would cost 14k instead of 77-163k.

## Recipes

Scratch directory with `fe` (`../tools/build_frontend.sh`), a core, and the ROM as `bcr.32x`.

- **Input** (`input.py` in this folder's recipe, kept here): Start at frames 200, 700, 850 and 1,100 reaches the first race at about 1,500; from 1,500 hold B+Y+A (mask 259) and steer left, centre, right, centre for 120 frames each. The CSV must have exactly FRAMES rows.

  ```python
  import sys
  n=int(sys.argv[1]); acc=int(sys.argv[3]) if len(sys.argv)>3 else 1
  rows=['frame,mask']
  for f in range(n):
      m=0
      if any(s<=f<s+4 for s in (200,700,850,1100)): m=8
      if f>=1500: m=acc|(0,64,0,128)[(f//120)%4]
      rows.append('%d,%d'%(f,m))
  open(sys.argv[2],'w').write('\n'.join(rows)+'\n')
  ```
  The 600-frame replay from a frame-1,800 state uses the same rule with *f* = 1,800 + *i*.
- **States:** stock: `run 1799` / `save st1800.bin`. Timing model: the same with `VRD_SH2_TIMING=1 PD_32X_BIOS_DIR=…/32X BIOS` (the race is reached at the same frames). Load a timing-model state with `VRD_TIMING_CCR=1`, or the model runs uncached.
- **Under the profiler from power-on the game runs slower and the fixed Start presses miss the menu**: profile from a state instead.
- **FS per frame:** debug script `run 1` / `read 68k 0xA1518A 2`; count changes of bit 0. Quit only after the profiler's frame count, or no profile is written.
- **Watch:** `VRD_WATCH=0x2603E230:4,0x20004022:2`.
- **Ground simulation:** from the stock state, a debug script `run 3`, `read master 0x26032EB4 1024`, `read master 0x260332B4 4096`, eight `read master 0x24012E00+n×4096 4096`, `read master 0x260348D8 4`, then `python3 groundsim.py ROM DUMP`.

## Open

- A console run: frame rate in one- and two-player races. GamePro (July 1995, via WP-BCR) reports choppy motion and slowdown, worst in two-player.
- Two-player mode (`0x060030E8` clears, `0x0204B680` loops twice) not run.
- Whether a byte write to `0x20004039` drives PWM on hardware.
- The 21% of the Master's time the timing-model profile does not attribute.
