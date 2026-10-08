# Star Wars Arcade (USA): analysis notes

Working notes, not part of the book. ROM `../32x-playground/Star Wars Arcade (USA).zip` (MD5 `ae3a42c6…`). SH-2 program `0x548C` bytes from ROM `$854` to `0x06000000`: `sh ../tools/sh2dis.sh ROM 854 548c swa`. The Slave's on-chip routine is 2 KB from the cartridge address stored at ROM `$814` (`$02005CE0`, so ROM `$005CE0`); disassemble it with `sh-elf-objdump -b binary -m sh2 -EB -D --adjust-vma=0xC0000000`.

## Interrupts

- One dispatcher per CPU (Master `0x060004B0`, Slave `0x0600051C`) indexes a 16-entry table by SR level. The Master's masks everything first; the Slave's does not.
- Level 5 is the watchdog (IPRA `$50`, VCRWDT vector 72, set at `0x06000928`). Master table entry: stub at `0x060022C4` (TOCR flip + 5 `nop`). Slave table entry: `0xC0000582`, in on-chip RAM, the span drawer below. Only the Slave starts its watchdog.

## Slave renderer

- Frame command 12 (`0x060007D0`): purge cache, start the background clear (`0x06000BD6`), run the on-chip routine once per pointer in the Master's list (`0x060008AC`), wait for the drawer to finish and flip FS (`0x06000B98`).
- **Producer** `0xC0000000`: record word 0 has flags (bit 3 line, bit 4 triangle) and the colour byte (replicated into a word at GBR+132). Vertices x, y (y flipped about GBR+118, x offset by GBR+116), written twice into arrays 32 bytes apart (`0xC0000350`/`0xC0000370`) so walks never wrap. Triangle = quad with repeated vertex; line = 2-pixel-wide quad. Finds top and bottom vertices, rejects if outside y (GBR+124/126) or x (GBR+120/122); polygons crossing left/right go to `0x06000C28` (SDRAM). Builds left/right edge lists (`0xC0000390`, `0xC00003D0`) clipped in y by bisection (`0xC0000490`: midpoint until y matches; same routine on swapped coordinates for x). Emits trapezoids: 24-byte records (left x, left slope, right x, right slope as 16.16; first line, height, colour word) into a ring of 1,000 at `0x06039CB0`-`0x0603FA70`, write pointer GBR+20, count GBR+134, interrupts masked while adding, waits if fewer than 4 free. Slope = dx × word table at `0x06035CB0` (8,192 × `$8000/n`, built with DIVU at `0x06000EFE`) via `MULS.W`, then × 2.
- **Consumer** `0xC0000582` (watchdog interrupt): TOCR flip, state at GBR+114. State 1: wait FEN, fill start += 95 (so after a 161-word fill it lands on the next 256-word line; initial `$A1`), length `$A0`, data 0; restart WDT with WTCNT `$10` (240 counts × 2 = 480 clocks); line counter at `0xC00005CC` (224) → state 4. State 4/0: starfield if GBR+154 (`0x06000DB4`, single bytes of colour 1 from a list at GBR+76), then trapezoids from read pointer GBR+24: per line round both x (+`$8000`, >> 16), ≤ 6 px byte loop, else odd bytes + auto fill of the words; ≥ 80 px: save state, state 3, return with WTCNT 0 (512 clocks). Ring empty: WTCNT `$7F` (about 258 clocks).
- Frame buffer lines are 512 bytes apart (line table at `0x06000B76`: `$100` + 256 n words).

## Master geometry

- Transform `0x060028D0`-`0x06002932` (`MAC.L` ×4, `XTRCT`, `ADD`).
- Bucket key `0x06003110`-`0x060031AC`: record word 0 bit 6 → farthest of 4 depths; bit 7 → nearest (negative → farthest); else average (negative → farthest). Farthest negative or > `$7FFF` → dropped. Depth ≤ `$FFF`: bucket `$2000` − (d + 1); else `$1000` − ((d + 8 − `$1000`) >> 3). Heads at `0x060076C0` (8,192 longwords), nodes of 8 bytes from a pool at GBR+80 (reset to `0x0600F6C0`), pushed on the front.
- Walk `0x06002796`: heads 0 → 8,191 (far → near), clears each, copies record pointers into the flat list for the Slave.

## In the book

`src/techniques/software-3d.md` (rasteriser, timer-paced fills, bisection clipping, bucket sort, starfield), `src/sh2/timers.md` (watchdog as scheduler; replaced the earlier "does nothing" reading), `src/sh2/intc.md` (dispatcher masks), `src/32x/vdp.md` (fills that draw), `src/patterns/cpu-split.md`. Case study: `src/patterns/case-study-starwars.md` (6 Oct 2026); play frame-rate count also in `src/patterns/60fps.md`.

## System registers (checked 2026-10-04)

- Mask set by word read-modify-write: Slave ORs in PWM at `0x0600093C` (from the watchdog set-up called at `0x06000740`), Master ORs in CMD at `0x06000F2E`. FM taken with a byte OR of `$80` (`0x06000B20`, `0x06000DEE`).
- VRES handlers (`0x06000584`, `0x060005E8`): clear VRES, then `mov.w @(6,r2),r0` / `tst #1`, which does read RV correctly (contrast MK2 and AB32X, discrepancy 33).
- 68000 CMD sender (cartridge `$086B72`-`$086B9C`): writes the command byte to `$A15120`, `bclr`/`bset` #0 on `$A15103` (INTM), polls `$A15120` up to `$2000` times for 0, and on timeout clears and sets INTM again. A guard against a lost CMD. No 68000 write to `$A15107` (RV) and no `$A130xx` reference anywhere (20 Mbit, so TI item 8 applies and is skipped). Book: `src/32x/bugs.md`.

## Two-way purge and the on-chip routine (checked 2026-10-05)

- Slave command table at `0x0600077C`, indexed by byte offset: `$04` → `0x060007A4` (calls `0x060008F0`: CCR 0 then `$19`, copy 2 KB from the cartridge pointer at `0x22000814` into `0xC0000000`), `$0C` → `0x060007D0` (CCR `$08` then `$19` = full purge in two-way mode, then runs the on-chip code). The loader also runs once at start-up (`0x0600073C`).
- The 68000's command sender (`$086B72`) has 24 call sites (`$0869E2`-`$086FE8`), all with constant commands: `$0C`, `$10`, `$14`, `$18`, `$1C`, `$20`, `$24`, `$28`, `$2C`, `$34`, `$38`, `$3C`, `$40`, `$44`, `$48`, `$4C`, `$50`, `$54`, `$58`, `$5C`, `$60`. Never `$04`. So the game relies on the on-chip RAM surviving CP in two-way mode. In `src/sh2/cache.md`.

## PWM requests (2026-10-05)

- One PWM voice with a priority. The 68000 sends Master command `$3C` (Master table at `0x060010A4`, entry 15 → `0x060011FA`): the Master copies the sound's address and priority from the parameter block into the shared work area (GBR `0x060075E4`, offsets 68 and 72). Command `$40` (entry 16 → `0x06001206`) posts a silent sound with priority 0.
- The Slave picks the request up once a frame, inside frame command `$0C` (`0x060007E4`-`0x06000878`), with interrupts masked: it starts the new sound only if its priority is at least the current one's (offset 28), else drops it. Bit 7 of the priority picks the decoder (`0x060009CC` or `0x06000A2C`).
- Z80 and PSG: see `notes/games/mars/CATALOG.md`, "Sound paths across the retail cartridges".

## Sound data views (2026-10-05)

- PicoDrive run, 1,500 frames, `notes/games/ab/input.py` for input, `VRD_WATCH=0x26007628:4,0x26007604:4,0x26007610:4` (Slave GBR `0x060075E4` + 68, + 32, + 44). Data pointer walks `0x0221EExx` and on; codebook base stored doubled as `0x0443D500`, so `0x0221EA80`. Both are the **cached** cartridge view. Decoder 1 codebook = 256 × 4 bytes = 1 KB = 64 lines, reused every sample; stream bytes read once. Upper bound for the frame-command `$0C` full purge: 64 × 136 (cartridge) + 64 × 12 (SDRAM) ≈ 9.5k clocks. Book: `src/patterns/cache.md`.

## Frame rate in play (6 October 2026)

Play state at frame 2100 (Start every 150 frames 200-1400), 2,000 frames of fire only, FS read from `$A1518A` each frame through the debug script: 1,084 flips; gaps 1: 273, 2: 708, 3: 101, 4: 1 → about 33 drawn frames a second, not locked. Profiling in play hangs the game (see tools README), so no stage split. An earlier profile (state at 1200) was the in-engine attract demo (ships and lasers, "Press Start"), not the text crawl and not play; corrected 6 October 2026: Master waits ~30% at `0x06000E10` (GBR+108, the 68000's command) and ~25% at `0x06001030` (byte `0x20004023` = 0, Slave took the command); Slave waits ~22% at `0x06000750` (command byte from the Master; dispatch table `0x0600077C`, 12 = frame) and ~13% at `0x06000BBE` (FS flip), ~16% at `0x06000B9A` (ring empty and drawing interrupt idle). Shares of executed cycles, attract scene only.


## What sets the frame rate (6 October 2026)

- **68000 frame loop.** Vblank handler (work RAM `$FFFF0002`, cartridge `$083000`) adds 1 to `$FFFF9004`. Wait routine `$FFFF0158` (cartridge `$083156`): loop while `$9004` < d0, then clear it. The step routine `$FFFF1902` (cartridge `$084900`) loads d0 from `$FFFFDE46`, waits, then calls `$FFFF1948` (cartridge `$084946`: step counter `$900A`, game, `jsr $FFFF3D7A`). `$DE46` = 1 in the whole attract mode (4,800 frames) and in play; written 2 only at cartridge `$01A718` (path not identified). So no lock: one 68000 step per vblank (198/198 frames in the demo; 1,963 in 1,999 frames of play).
- **Draw offer.** `$FFFF3D7A` (cartridge `$086D78`) first calls `$086B40`: `$A15122` non-zero → carry → skip drawing this step. Else command `$18`, `$1C` (set-up), then command `$0C` per object (`$086DFC`, `$086E40`), then `$086A40`: wait for `$A15122` = 0 (`$086B66`), command 8 with parameter `$0C`.
- **Master side.** CMD handler `0x06001074` dispatches on `$A15120` through `0x060010A4`. Command 8 (`0x0600129C`): GBR+108 = parameter and byte `0x20004022` = parameter (busy). Command `$0C` (`0x060012A6`): two-phase call inside the interrupt, all levels masked: read position, clear byte 0, poll for 13 (`0x060012CC`), read angles and model, compute (`0x060029C4`, `0x0600327C`), write 3 words and a long back; the dispatcher clears byte 0. 68000 side `$086C40`-`$086C82`. Idle loop `0x06000E08`: clear GBR+108 and byte `0x20004022`, poll GBR+108, dispatch through `0x06000E34` (12 → frame at `0x06000E96`).
- **Profiles** (`../tools/profgroups.py swa`): demo frames 1300-1490 (flip every 2nd frame): 68000 78% vblank wait; Master 46% computing, 30% idle at `0x06000E10`, 0% at `0x06001030`; Slave 24% waiting for the Master, 12.5% ring drain, 11% FEN polls in the handler, 11% flip, 6% PWM + 1.2% dispatcher, 5% cutter. Crawl frames 3800-3990 (holds 3-4): Master 19% waiting for the Slave, 6% idle; Slave 31% cutter, 20% drawing handler, 0.5% waiting for the Master; 68000 49% vblank wait, 14% handshakes. Executed clocks only (Master 75-77%, Slave 67-75%).
- **Play** (Start every 150 frames 200-1400, B held from 1500, frames 2100-4099): 1,140 flips in 1,999 frames (gaps 1: 346, 2: 728, 3: 65), Master list toggles (`0x0600764A`) = flips. PCs sampled once a frame (`regs master`/`regs slave`): Slave waiting for the Master 59%; Master idle 33%, in an object call at `0x060012CC` 16%.
- **Drawing handler details.** Polls FEN before every line (`0xC0000664`); returns only after a fill of ≥ 80 bytes, with WTCNT 0 at φ/2 = 512 clocks, fixed; when the timer fires (state 3) it resumes at the next line and polls FEN. Clear: WTCNT `$10` = 480 clocks vs 490 for 161 words, so a short FEN poll at `0xC0000594`. Flip `0x06000B98`: poll ring count, poll state, stop WDT, poll FEN, toggle FS, poll FS until it changes.
- **PWM.** Control `$0105` (TM = 1), cycle 1,047: 367 interrupts a frame. Handler `0x06000980` decodes until FULL. About 70 instructions with the dispatcher; PicoDrive: handler + decoder 20,000-23,000 clocks a frame. Five 32X register accesses per interrupt.
- **PicoDrive fill timing** (upstream `26ecb2b`, memory.c): pixels written at once; FEN held 3 + len 68000 cycles if len > 8 words.
- Book: `src/patterns/case-study-starwars.md` (rewritten 6 Oct 2026), `60fps.md`, `cpu-split.md`, `software-3d.md`, `32x/vdp.md`, `32x/pwm.md`.

## Would the codebook survive without the purge? (8 October 2026)

Scripts: `cachesurvey.py` (parse a debug log of `run 1` / `read 68k 0xA1518A 2` / `read slave 0x260075E4 160` / `read slave 0x260310E0 4096` / `read slave 0x260326C8 4096` / `regs slave` per frame) and `cachesim.py` (2-way LRU model fed with those lists and the sound bytes from the ROM). Input: Start every 150 frames 200-1400, B from 1500 (`input8k.csv`, 8,000 rows); debug windows 1475-1655, 1915-1995, 2096-2395. Frontend rebuilt with `../tools/build_frontend.sh` (the committed binary reports "debugger ABI mismatch").

- **Decoder 1 format** (`0x060007FA`-`0x0600082E`, `0x060009CC`): request block = long samples/2, then 256 × 4-byte codebook, then one index byte per 8 samples (each codebook byte held for 2 samples, value (b+1)×4 to `0x20004038`). Confirmed for 5 sounds: header × 2 = GBR+36 at start. Codebooks `0x0221EA80` (aligned, 0.31 s), `0x0222BF0C`, `0x0222F07C`, `0x0225F6EC` (all +12, so 65 lines), `0x0225D1D0` (aligned). Decoder 2 (`0x06000A2C`, bit 7): blocks of a 256 × n codebook + count index bytes; the attract sound at frame 1052 has n = 2 (512-byte codebooks, 4 samples per index), codebook replaced every 8,193 index bytes.
- **PWM sound in the run** (VRD_WATCH on GBR+28/+36/+44): only frames 1052-2003 (one decoder-2 sound, four decoder-1 sounds); nothing from 2003 to 8000 with B held. 367 samples consumed per frame, so 46 index bytes (46 codebook look-ups) per TV frame, 92 per 2-frame picture.
- **Slave cached reads per picture** (PicoDrive): records via `0x0601xxxx`/`0x0602xxxx` (36-byte slots, two buffers from `0x06018690` and `0x06024BB8`); play median 258 records (213-481; earlier run 221-715) = ~580 lines (480-1,083); intro scene up to 924 records (2,079 lines); trapezoids at picture end median 165 in play (81-313) × 24 bytes from the ring at `0x06039CB0` (reset per picture by `0x06000BD6`). Slave PCs once a frame: idle loop 63-65%, producer 14-17%, watchdog handler 7%, PWM 7%, dispatcher 6-7%.
- **Model result**: with the real lists the purge costs 1-2.5 extra codebook misses per picture (of 27-45 codebook lines a picture touches), whatever the producer-phase length (10-50% of the picture); 93-98% of the first uses after the purge would miss anyway, because the producer pulls 6-30 record lines through every entry right after it. Pictures with no polygons (frames 1475-1575): the purge costs 20-31 extra misses per picture. Entries 29-32 hold two lines used every PWM interrupt (handler/decoder code `0x060009D0`-`0x06000A00`, GBR line `0x06007600`, stack lines `0x0603FDD0`-`0x0603FDF0`) and thrash their codebook line every sample in any case. Model timing is assumed; see the script header.
- Not a free option: the Slave reads the Master's lists and records through the cached view, so without the purge it would read stale lines of the other buffer.
