# After Burner Complete (32X): analysis notes

Working notes, not part of the book. Started 2026-10-03. Proposed citation key `AB32X` (not yet in `src/appendices/bibliography.md`).

Evidence levels: **ROM** = read from the retail dump's code or data. **Emulator** = observed running it in the VRD project's PicoDrive libretro core (not a console). Profile shares are PicoDrive's per-PC cycle counts, in which wait loops count as work.

## The dump

- `After Burner Complete ~ After Burner (Japan, USA).32x`, 2,097,152 bytes, MD5 `ec9529858cc7961b39f5382b2f657b8f`. Header checksum `$4174` matches the contents. Header: `(C)SEGA 1994.OCT`, `GM MK-84507-00`. A Sega release.
- Sega's initial program (`$3F0`-`$7FF`) is byte-identical to Star Wars Arcade's and Mortal Kombat II's.
- User header (`$3C0`): SH-2 program from ROM `$53000`, `0x1A000` bytes (106,496), to `0x06000000`. Master entry `0x06002120`, VBR `0x06002000`, stack `0x0603F000`. Slave entry `0x06000200`, VBR `0x06000000`, stack `0x0603F600`.
- Disassemble with `../tools/sh2dis.sh ROM 53000 1a000 ab`. Headless input: `input.py` here (three Start presses reach stage 1; a fourth pauses).

## Division of labour (ROM + emulator)

| CPU | Job |
|-----|-----|
| 68000 | The game, at 30 frames per second. Mega Drive VDP draws the player's jet, the HUD and the crosshair (in front: PRI = 0, no through bits). Sends every object to the Master as a synchronous call (below). Forwards sound requests from the Z80 to the Slave |
| Master SH-2 | Projects objects (inside its CMD interrupt), sorts them by depth, draws the 32X layer: sky and sea by auto fill, ground detail, enemies, clouds and explosions as scaled sprites |
| Slave SH-2 | Sound only: a music/effects sequencer and a 16-voice PWM mixer |

Steady 30 drawn frames per second in play and on the title (Master frame counter `0x06003AFC` watched for 2,000 frames). Bitmap mode register `$8001` (packed pixel, PRI 0); fill data and palette show no through bits.

## Start-up

- **Master** (`0x06002120`): SR mask, GBR `0x20004000`, VBR, SP. Sets up the FRT itself (TIER 0, TOCR `$E2`, OCRA 1, TCR 0, FTCSR 1, FRC 0, then TOCR `$F2` and OCRB 1, TOCR `$E2`), the same values as MK2. Waits for `$A15120` = 0, enables CMD only (interrupt mask `0x20004001` = 2), sets up three object rings, converts a 68000 pointer at cartridge `$880C0A` to an SH-2 address (`- $880000 + 0x22000000`), copies 256 palette words from ROM `0x02173700`, clears the frame buffer, SR mask 2, jumps to the main loop `0x06003890`.
- **Slave** (`0x06000200`): same FRT set-up, waits for `0x20004020` (long) = 0, writes `$8203` to `0x20004000` (FM, PWM and CMD interrupts), clears its interrupts, initialises the mixer (16 voice records of 32 bytes at `0x0603F600`, a 64-entry ring at `0x0603F100`), PWM control `$0105` and cycle `$05C3`, then its main loop `0x060007A2`.
- Neither CPU writes CCR: both run the boot ROM's four-way cache. No `tas.b` anywhere. No DMA channel is armed and `0x20004012` is never read: the FIFO is unused.

## Interrupts

- **One entry per CPU** (Master `0x060022EC`, Slave `0x0600033C`), as in Sega's sample.
- **Master tells CMD from the rest with one test:** `tst #$60,r0` on SR. After acceptance the mask holds the level; CMD (8 = `1000`) is the only enabled level with bits 5 and 6 clear. VRES (14) and anything else go to `0x060022C4`, which separates VRES by `(SR & $E0) == $E0`.
- **Master CMD dispatch:** the low 6 bits of `$A15120` index a table of 16-bit offsets at `0x0600230C` used with `braf` (position-independent, half the size of an address table). Commands run inside the interrupt handler.
- **Slave dispatch:** `(SR >> 2) & $3C` indexes a table of handler addresses at `0x06000350`. Levels 0-5 and H/V go to a loop that never returns (`0x060002DC`; they are masked). PWM (6/7) `0x06000390`, CMD (8/9) `0x06000684`, VRES (14/15) `0x06000288`.
- **VRES, both CPUs:** DMAOR = 0, CHCR0 = 0 then `$44E0` **written correctly** (the pointer register is `0xFFFFFF80` + 12), unlike the slip in Sega's sample that SWA and MK2 copy. With RV = 1 sets TOCR bit 0 (FTOB) and loops. The Master also blanks the 32X layer, clears `$A15120`-`$A15123` and writes ASCII `VRES` to `$A1512C`-`$A1512F`, so the 68000 can see the reset happened; then it re-enters start-up after its handshake (`0x06002166`). The 68000's hot-start reset path (`$880840`-`$880908`) checks `$A1512C` for `VRES` up to 4,096 times; if it never appears, it raises CMD on both SH-2s and waits for `M_OK`/`S_OK`.
- **Master main-loop watchdog** (`0x060038E6`): polls a mailbox byte in SDRAM that the CMD handler sets, counting down from 1,500,000. If nothing arrives, it masks interrupts, clears the busy byte `0x20004020` and the CMD interrupt (`0x2000401A`), and keeps waiting: recovery from a lost CMD or a stuck handshake.

## 68000 → Master: one call per object (ROM)

68000 code at `$7348`-`$73BC` (`$887348` in the 32X map):
1. Fills the ports **and the FIFO's unused source, destination and length registers** (`$A1510A`, `$A1510D`/`$A1510E`, `$A15110`) with the object's parameters: 13 bytes of extra mailbox space.
2. Writes `$010F` to `$A15120` (busy byte plus command 15) and 1 to `$A15102` (CMD to the Master).
3. Spins until `$A15120`'s high byte is 0 (`$8873A8`).
4. Reads `$A15124`: −1 means culled. Otherwise reads `$A15128` back into the object.

Master command 15 (`0x0600257C`, in the interrupt): perspective by a 16-step `DIV1` reciprocal (`$7FE0 / (z/32 + 32)`, `0x060025A8`), scale and screen position with `muls.w`, appends a 16-byte entry to the current object ring. Three rings rotate (`0x06017588`, `0x060181B0`, `0x06018DD8`, 194 entries each), so the 68000 fills one while the Master draws from another.

68000 profile over 2,000 play frames: about 12% spinning at `$8873A8`/`$8873AC` for the Master's answer, about 26% waiting for vertical blank (`$890B8A`), about 37% in the whole send routine. Emulator; PicoDrive shortens polling loops.

Counts (watch log): 74 objects per drawn frame median, 87 max, in play; draw list up to 92 sprites. Title screen: 127 sprites median, 143 max (the logo is built of spheres, each a scaled sprite, turned by rotating their 3D positions).

## Master frame (ROM + emulator)

Main loop job (`0x06003A6C`-`0x06003AB8`):
1. **Depth sort** (`0x06003B66`): 256 buckets of 32 bytes at `0x06019A00`: a count word plus up to 30 one-byte entry numbers. A full bucket spills into the next. Then walks the buckets and builds 28-byte draw records at `0x06003E00` (`0x06005300`).
2. **Background** (`0x06008280`): for each of 224 lines, reads a split column from a per-line table (`0x06007674`) and issues **two auto fills**: one colour left of the split, the other right, 160 words in all (one 160-word fill, length register `$9F`, when the split is off the line: branch at `0x060082B8`/`0x060082BC`); the colours swap with the roll direction. This draws the sky and sea with the rolled horizon and clears the buffer at the same time. Polls FEN with `tst.b #2,@(r0,gbr)` (GBR = `0x20004100`, r0 = 11): one instruction per poll. Manual estimate: 224 × (2 × 7 + 3 × 160) ≈ 110,700 clocks per drawn frame with two fills on every line, 224 × (7 + 3 × 160) ≈ 109,100 with one. PicoDrive puts 44% of the Master's profile in this loop, more than the formula predicts (not explained). The title uses a one-fill-per-line clear (`0x0600D0C8`, 224 fills of 161 words).
3. **Sprites** (`0x060065A0`), in list order:
   - **Sprite cache** (`0x060065BC`-`0x0600676C`): each sprite (16-bit shape number, scale) is looked up in a 128-entry ring of 8-byte descriptors at `0x0601BA00` (shape, size, 24-bit offset, age). On a miss, the shape's RLE data (ROM `0x02061000` + offset) is decoded into a ring buffer at `0x0601BE00`; entries whose range the new one overlaps are evicted. RLE: negative byte = run of zeros (Duff's-device jump into 8 unrolled `mov.b`), positive = literal bytes (a variant masks each to 4 bits). Shapes `$7Fxx` bypass the cache: 16 resident images in SDRAM `0x0600D4F8` onwards, `$3A0` bytes apart.
   - **Scaled blit** (`0x06006778`): four modes chosen by record byte 2 through a table at `0x060067A4`:
     | Mode | Code | What |
     |------|------|------|
     | 0 | `0x06006960` | Each source pixel doubled into a word (`extu.b`, `shll8`, `or`) and written to two lines: 2 × 2 "fat pixels" |
     | 1 | `0x06006A4C` | As 0, mirrored |
     | 2 | `0x060067B4` | Word copy, normal |
     | 3 | `0x06006868` | Word copy mirrored (`swap.b`, written right to left) |
   - **Inner loop** (mode 2, `0x0600680A`): four instructions per output word: `addc r13,r8` (fraction), `mov.w @(r0,r0),r1` (source; r0 holds half the address, the addressing mode doubles it), `addc r14,r0` (integer step plus carry), `mov.w r1,@-r6` (store, right to left). Unrolled 8 times and entered by a computed jump on the width modulo 8. Per line: row = `(v >> 16) * width` by one `muls.w`, v += vertical step, destination += 512 bytes (1,024 in fat-pixel mode).
   - **Destination** is the overwrite image (`0x2402xxxx`), so zero pixels are skipped by the hardware: no transparency test in the inner loop.
   - No rotation of pixels anywhere: rolls rotate positions and the horizon only.
4. **FS flip** (`0x060038CE`): XOR FS in `0x2000410A`, then wait until FS reads back changed.

Master profile, 2,000 play frames: FEN wait 44%, scaled blit loops about 45%, sprite cache 2%, sort and projection a few percent.

## Slave: sound driver (ROM)

- **Mixer** (`0x060003C0`-`0x0600046E`), runs whenever the ring has room: 16 voices, each a 32-byte record (volume L/R packed in one long, sample base, start count, step, end, handler pointer). Position = (global sample count − start) × step (`dmuls.l`), so positions never accumulate error. **Linear interpolation** between two 8-bit samples (fraction 8 bits, `muls.w`), two `muls.w` for left and right volume, sum, scale by `dmuls.l` with `$733C0` (keep MACH), add 737, clamp ≤ 0 → 1 (`0x06000442`-`0x06000448`). The upper clamp to 1,474 (`mov r1,r11` at `0x0600044C`, `0x0600045C`) is dead code: a positive value takes both `bt`s, since `cmp/pl` leaves T = 1 for the second (checked 5 Oct 2026). Pushes one longword (L and R) into a 64-entry ring.
- **Ring indices in UBC registers:** read index at `0xFFFFFF40` (BARAH), write index at `0xFFFFFF42` (BARAL), sample counter at `0xFFFFFF60` (BARBH). On-chip, so no bus cycles; break conditions are left off.
- **PWM:** cycle `$5C3` → 23.01 MHz / 1,474 ≈ 15.6 kHz; control `$0105` (TM 1: interrupt every sample; L from L, R from R). The interrupt (`0x06000390`) writes one ring entry with a single `mov.l` to `0x20004034`, setting both pulse widths at once, flips TOCR, rte.
- **Sequencer** (`0x06000820`): when the tick flag `0x0600079E` is set, runs request handling (8-slot queue at `0x0603F800`, 4 at `0x0603F814`), 39 track records of 43 bytes at `0x0603F820`, and more.
- **Commands** (CMD handler `0x06000684`, port `$A15122`): `$0200` = tick; `$02xx` = command xx through a table at `0x0600073C`; otherwise a sound number queued into a free slot.
- **Idle shape (checked 2026-10-05):** the ring starts full of silence (`$2E1`, `0x060002E2`-`0x060002F2`) and the mixer runs only while read index ≠ write index (`0x060003C0`-`0x060003C8`), so it works up to 64 samples ahead. When the ring is full the main loop spins on the two UBC index words and the tick flag: no port polling (commands come by CMD interrupt), no bus cycles. PicoDrive per-PC profile, 3,000 frames from power-on with `input.py` (title then play): ring check `0x060003C0`-`CA` 43.3% of Slave cycles, tick test `0x06000820`-`26` 3.7%, branch back `0x060007F4` 2.9%, mixer `0x060003CC`-`0x0600046E` 45.8%, PWM interrupt 2.9%. So about half the Slave is spare. The same run put the 68000's object-call spin (`$8873A8`) at 9.8% (title included) and the whole sky/sea fill routine at 29% of the Master.
- **68000 side** (H-interrupt handler at `$88091E`, reached through jump-table entry 27; V-interrupt goes to `$880C00`): takes the Z80 bus, increments `$A016FF` and reads a request from Z80 RAM `$A016FD`, sends it to the Slave as `$0203`, then sends the `$0200` tick, waiting for each acknowledgement. CMD to the Slave is `$A15102` = 2.

## What is new compared with SWA and MK2

- Auto fill as the background renderer (two fills per line follow a rolled horizon); MK2 uses fills only to clear.
- Per-object synchronous RPC from the 68000 into the Master's CMD interrupt, with the FIFO registers used as extra mailbox words.
- Scaled sprites: decoded-sprite cache in SDRAM with ring allocation, carry-chained DDA, `@(r0,r0)` addressing, mirroring by `swap.b`, 2 × 2 fat-pixel mode, overwrite image for transparency.
- 3D-positioned sprite clusters (title logo) as "rotation" without rotating pixels.
- Triple-buffered object lists; 256-bucket depth sort with spill.
- A 16-voice interpolating PWM mixer on the Slave, with ring indices kept in UBC registers and one `mov.l` writing both PWM channels.
- Sega's VRES handler with the CHCR0 slip fixed, and a `VRES` marker for the 68000.
- A main-loop watchdog that clears a lost CMD.
- 30 fps with the Master waiting on fills for a large share of its time.

## Open questions

- Why does PicoDrive put 44% of the Master's time in the FEN wait when the manual's fill formula predicts about 14% of a drawn frame?
- Are the ground sprites drawn with pre-rotated art when the plane banks (we did not check the shape numbers against the roll angle)?
- How do the art and the RLE format (4-bit literal variant) map to palettes? **Partly answered (5 Oct 2026):** the variant is chosen by bit 0 of the shape word (record word 0, copied from object entry +14 at `0x06005300`); the cache key is word & `$FFF1`, so bit 0 keeps the two versions apart. Masked pixels land in entries 0-15; ROM palette `$173700` entries 1-14 are reds/oranges up to pale yellow (fire). Draw lists sampled every 10 frames, frames 1100-5000 with `input.py` (24,127 sprites): bit 0 never set; also none at frames 700/2000/2600. Shape table `$173900`: 8-byte entries (flags word, width byte, height byte, RLE offset long from `$061000`), 767 entries, 364 distinct shapes; 1,574,122 bytes unpacked (74% zeros), 441,148 packed (28%), data ends `$0CCD5C`. Per-shape d32xr-style LZSS (4 KB window, greedy) 313,553 (19.9%); per-shape deflate 153,349 (9.7%).

## Folded into the book

`src/32x/vdp.md` (fills as background, overwrite image), `fifo.md` (unused; its registers as mailbox), `communication.md` (one call per object, Slave sound via CMD, Master watchdog, CMD-only SH-2s), `pwm.md` (third interrupt driver, 16-voice mixer), `boot.md` (user header, vectors, no `SLAV`, FTOB, `VRES` marker), `compositing.md` (table row), `architecture.md` (pointer conversion), `src/sh2/intc.md`, `timers.md`, `dmac.md`, `cache.md`, `divu.md`, `overview.md` (UBC registers), `isa.md` (`@(R0,R0)`, `TST.B @(R0,GBR)`, ADDC step), `pipeline.md` (unroll by eight), `sci.md`, `src/patterns/cpu-split.md`; discrepancy 22; catalogue entries in ten files. Also `src/techniques/2d-effects.md` (scaler and modes), `memory.md` (SDRAM map, sprite cache with lap numbers, resident images) and `compression.md` (RLE format, `NEGC` end test, Duff's device). And `software-3d.md` (projection with the +32 bias, 256-bucket sort with spill). Case study: `src/patterns/case-study-afterburner.md` (6 Oct 2026), built on the play-only profile below: Master ≤ ~44% useful, ~30% not running, ~26% fill polling; 68000 ~38% waiting; Slave ~half spare.

## Background routines (checked 2026-10-04)

- `0x06008280`: two fills per line from the split table `0x06007674` (sky/sea, rolled horizon); a split off screen gives one 160-word fill (land lines are one orange fill). A 6,000-frame PicoDrive profile from `s1100.mds` (sea and land stages, `input.py 6001 in_g.csv 1100`) shows only this routine; its FEN waits (`0x060082E8`, `0x060082C2`, `0x060082D2`, ...) total about 36% of the Master.
- `0x06008350`: second routine, never seen running. Per-line word at `0x06007474`: bit 11 set = solid line (colour from 16-entry table `0x06008480`, one fill); else index into per-row tables `0x06007A74` (phase) and `0x06007E74` (pattern/colour group, groups of colours at `0x060084A0`), runs from a pattern list at `0x060084C0` (12-bit length, colour index in the top bits); runs of 28+ pixels by auto fill, shorter by byte/word stores, clipped to 320. Tables built at `0x06006F1C` (perspective via the same `$7FE0/(z/32+32)` form, per-line values stepped in 16.16). Looks like a striped-ground renderer; which stage uses it is unknown. The table stayed 0 throughout. **Answered 2026-10-05, see below: it is a runway.**
- In `src/techniques/roads-mode7.md`.

## The runway routine and where it runs (checked 2026-10-05)

- **Selection (ROM).** Master main loop `0x060039E6`: ring word `+$C06` = 0 → no background, 2 → `0x06006F1C` then `0x06008350` (24 parameter bytes from `+$C08`-`+$C1F` copied to `0x06007254`), else → `0x06008280`. Command 3 (`0x06003748`, ring swap) zeroes `+$C06` every frame. Command 7 (`0x0600379E`) sets 1 and 8 bytes at `+$C08`; command 8 (`0x060037B8`) sets 2; commands 9/10 (`0x060037BC`/`0x060037C6`) fill `+$C10`/`+$C18`. CMD table: `braf` base `0x0600230C`, entries from `0x06002310`.
- **68000 side (ROM).** `$1EAF0` sends command 7 (split fills). `$1EDBE` sends 8, 9, 10 back to back from `$8C`/`$96`/`$C2` and `$322`-`$338(a6)` (a6 = `$FF0000`). `$1ED42` calls it when `$321(a6)` = 1, then scrolls `$322`/`$326`/`$338` by speed `$AA` (bit 6 of `$320` moves `$322`; bit 3 picks the second step pair at `$1EDB6`). Main loop `$1C51A`-`$1C61A`: `$321` < 0 → initialise (`$320` = `$0301`, `$322` = `$FFC0`, `$328` = `$FF`, `$32C` = `$010001FF`) and run; `$321` = 2..4 → three more mode-1 frames then 0.
- **Triggers (ROM).** Stage script opcodes (8-byte events at `$FF8A08`: distance word compared with `$6(a6)` >> 4, opcode byte, args; dispatched by `jmp $BB46(pc,d0.w)`): `$11` → `$BD16` writes `$0480` to `$320` (on), `$10` → `$BD08` writes `$0402` (off). Landing object `$E5AE` (waits for game state `$9C(a6)` = `$10`) writes `$0C80` at `$E674`/`$E6E4` and `$0402` at `$EA94`. Stage descriptors: 23 longs at `$3D802`, script pointer at `+$10`; stage order `$FF0010` is the identity, stage index `$60(a6)`.
- **Which stages (ROM).** Scripts with `$11`/`$10`: stages 8 and 17 (on at `$0C00`, off at `$6000`). Stages 5 and 13 have the short `$1F00` scripts with opcodes `$13`/`$14`/`$15`: the base landings.
- **Emulator.** Scratch ROM copies with entry 0 of `$3D802` replaced by entry 4 (stage 5) or 7 (stage 8), same `input.py`. Stage 5: mode 2 from frame 1,274 to 2,310 while the plane lands on a grey runway with yellow edges and a dashed white centre line, rolls past supply trucks and takes off, then stage 6 in mode 1. Stage 8 (the canyon): mode 2 from frame 1,295 to the end of the 2,500-frame run. Lines 0-54 solid (sky colours 0-13), lines 55-223 rows `$39`-`$107`; phase table all 0, so the first run (colour 3, 1,611 px) covers every ground line: plain blue ground, runway off screen. With `0x06008350` patched to `rts`, the sky and ground vanish but the canyon walls stay: they are sprites. Unpatched, 15,000 frames of `input.py` reach game over in stage 2 and never select mode 2.
- **Tables (ROM).** Solid colours `0x06008480`: palette `$C7`-`$D5` (sky gradient, `$D5` = ground blue). Groups `0x060084A0`, four of 4 words, chosen by bits 7-8 of the per-row word at `0x06007E74`: colour 0/1/2/3 = `$D7 $D9 $DB $D6`, `$D8 $DA $DC $D6`, `$D7 $D9 $DB $D5`, `$D8 $DA $DC $D5` (grey, grey/white line, yellow/grey edge, ground). Pattern per row pair at `0x060084C0` + (row & ~1) × 16: ground, edge, surface, line, surface, centre line, surface, line, …; row `$100`: 1,486 ground, 11 edge, 5, 6 line, 66 surface, 4 centre line, 68 ….
- Aside: in the stage 8 frame-buffer dump (frame 1,530) the player's jet is in the 32X layer, not the Mega Drive's as noted above for stage 1. Not followed up.


## System registers (checked 2026-10-04)

- Master mask: byte `$02` (CMD) to `0x20004001` at `0x06002168`. Slave: word `$8203` to `0x20004000` at `0x06000244` (FM = 1, CMD and PWM; bit 9 is read only). No H count writes, no H interrupt.
- Both VRES handlers (Slave `0x06000296`, Master `0x06002266`) clear VRES, read back, then `mov.b @(6,r1),r0` / `tst #1`: the byte at `0x20004006` (frame buffer FIFO status), i.e. register bit 8, not RV (bit 0, byte `0x20004007` per 32X-SUP2 `dreqctl` = 7). Bit 8 reads 0 in PicoDrive and Ares, so the RV = 1 reset path never runs there. Book: `src/32x/registers.md`, discrepancy 33.
- No 68000 write sets RV (searched `bset`/`move` forms on offsets 6/7 from `$A15100`, absolute `$A15106/7`, and calls to the vector ROM routines at `$C0`/`$D4`), so the broken RV check above never matters. Book: `src/32x/bugs.md`.

## Cartridge banking (checked 2026-10-05)

- 68000 start-up at cartridge `$0008FE`: `bsr $8EC` (writes `$0083` to `$A15100`, 0 to `$A15102`), then `move.w #1,$A15104` (bank 1 at `$900000`) and `jmp $880C06`. The only absolute reference to `$A15104`/`$A15105`. 16 Mbit, so TI item 8 does not apply. Book: `src/howto/large-cartridges.md`.

## Sky/sea fill cost, play only (6 October 2026)

Save state at frame 1200 (`input.py`), then 2,000 frames profiled with `input.py ... 1200` and `VRD_WATCH=0x26003AFC:2`: Master frame counter `$1F6` → `$5AD`, 951 drawn frames. Routine `0x06008280`-`0x060082F6`: 202.3M cycles = 212,740 per drawn frame (formula ~110,000; ×1.93), ~950 per line. Master executed 541M of 768M wall clocks (70%); routine = 37.4% of executed, 26.3% of wall. Earlier 44%/36% were shares of executed cycles over runs with different sleep and title content. PicoDrive fill model: FEN busy 3 + n 68000 clocks (`memory.c` fill data write), woken by `fillend_event`; matches the formula, so the ×1.9 is emulator scheduling, not explained. VRD timing patch (`VRD_SH2_TIMING`) was off.


## Where the waits go, with a sleep log (6 October 2026)

Core built with `../tools/build_sleep_core.sh` (current VRD PicoDrive tree, all PCs logged). State at frame 1200 (`input.py 1201`), then `input.py 2000 ... 1200`, 2,000 frames, profile over 1,990: Master frame counter `$1FE` → `$59E` = 928 pictures (interpreter); the same run without the profiler (recompiler) draws 995, gaps of 2 frames 971 times. Group with `../tools/profgroups.py ab`.

- **Master** (share of the run): scaled blits `0x06006778`-`0x06006BEF` 26.0% (normal 9.8, mirrored 6.3, double 1.1, double mirrored 8.6); FEN polls (sky/sea `0x060082C0`/`D0`/`E6`, clear `0x0600D0DA`/`E2`/`EC`, pre-sprite `0x06003A94`) 18.3%; go-ahead wait `0x060038E6`-`0x060038F6` 15.4% (SDRAM flag at `0x06003AF1` read through the cache, so never put to sleep; watchdog 1,500,000); projection and other commands in the interrupt 4.1%; sprite list and cache 3.5%; sort 0.9%; other small code 5.7%; flip-wait poll `0x0600395C` 0.3%. Not executed 25.4%. Sleep log: FEN (`0x2000410B`) 210,038 sleeps, 59.3M 68000 cycles (≈ 847 SH-2 clocks each); FS (`0x2000410A`) 3,278 sleeps, 15.8M. So ~4/5 of the sleep is fill waiting, ~1/5 the flip.
- **Frame order** (`0x06003AB8` → `0x060038CE`): toggle FS, wait for the 68000's go-ahead, take the command (SR `$F0` briefly), sort (`0x06003B66`), wait until FS reads back changed (`0x0600395C`), then background (`0x06008280`, or the plain clear `0x0600D0C8` when the mode word is 0; it ran in this stretch), FEN wait, sprites. SR = `$20` from `0x06003950` on, so CMD (level 8) is taken during fill polls.
- **Per picture** (2.155 frames, 827,500 clocks): useful 336k (0.87 frame), of which frame buffer 215k (0.56), the rest 121k (0.31); fill waits polled + asleep ≈ 318k against ~110k by the formula (~2.9×).
- **68000**: waits for the Master to take list entries (`$89C6CA`, command 1, interrupts masked) 23.0%; answers `$8873A8` 5.6% and `$88A038` (command `$1E`) 3.9%; vblank `$890B8A` 10.1%; rest 56.6% ≈ 1.22 frames per picture. Master command 1 (`0x060036FC`): appends a 16-byte entry to the object ring with no projection.
- **Slave**: mixer `0x060003CC`-`0x0600046E` 28.7%, PWM interrupt `0x06000390` 2.2%, ring-full spin (`0x060003C0`-`CA`, `0x06000820`, `0x060007F4`) 40.7%, not executed 27.5%.
- **Arcade** (MAME at `ab1bc04`): X Board, two 68000s at 12.5 MHz, Z80 4 MHz, YM2151 + Sega PCM 315-5218 (16 voices, 4 MHz / 128 = 31.25 kHz), palette RAM 16 KB = 8,192 entries + shadow/highlight, sprite RAM 4 KB = 256 entries of 16 bytes, per-pixel zoom, screen 6.25 MHz / (400 × 262) ≈ 59.6 Hz. Frame rate of the game itself: HG101 and The Register say 60; not measured.
- Book: `src/patterns/case-study-afterburner.md` (revised 6 Oct 2026), `cpu-split.md`.
