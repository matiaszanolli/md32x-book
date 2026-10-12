# Case study: Virtua Fighter

*Virtua Fighter* (Sega, 1995) is the 32X version of the 1993 arcade fighter: two fighters built from flat-shaded polygons, about fifteen body parts each, in front of a Mega Drive background, on a 4 MB cartridge. Its credit screen names Sega's AM R&D Department #2, AM2 [VF32X]. Two things make it worth a chapter. It is the one retail game in the sources whose **fighting engine runs on the SH-2s**: the 68000 reads the pads, draws the HUD and plays the music, and sends the SH-2s five bytes of data per picture. And its renderer shares a back end with Virtua Racing Deluxe, a game the book has so far known only through a fan project's notes on a patched ROM, so it can be used to check what the [Virtua Racing Deluxe chapter](case-study-vr.md) says.

## How far the evidence goes

The code was read from the retail dump, whose header checksum matches, with a disassembler: what it does is certain [VF32X]. The runs that give counts and orders of events were made in PicoDrive, with a build that logs every 68000 access to the 32X registers, every VDP write and DMA, and every SH-2 write to the system registers. They are tagged <span class="tag emulator">emulator</span>. Nothing has run on a console. Four cautions apply to every number below:

- **PicoDrive charges the SH-2s no memory wait states** and does not model the two SH-2s taking the bus in turns. Counts of instructions and of fills are exact; durations are not console durations ([What the emulators do not show](bus.md#what-emulators-do-not-show)).
- **The interpreter and the recompiler give different periods.** Run with PicoDrive's interpreter, which tracing needs, an attract-mode fight takes three frames a picture; with the recompiler it takes two. Every duration here is from the recompiler runs. Instruction counts come from the interpreter runs and do not depend on the mode.
- **PicoDrive's PC profiler produced a wrong answer on this game.** A first profile showed both SH-2s spending nearly all their time in wait loops, which would have made the game look idle. It was an artefact: a profile-mode run from power-on stalls after about 1,300 frames, the 68000 stops sending commands, and the profiler takes one PC sample per 32-cycle chunk. The profile is not used below ([Profiling](../howto/profiling.md#five-traps-all-met-in-the-wild)).
- **Part of the game was not exercised.** The runs were an attract mode of about 5,700 frames and a scripted played fight. The menus, the tournament and the record and replay modes were read where they send commands, not run.

Reading notes with every address are kept in `notes/games/vf/`.

## How the game divides the work

| CPU | Job |
|-----|-----|
| 68000 | Reads the pads and forwards two bytes. Draws the HUD on Mega Drive plane A and the sky and sea on plane B, and plays the music with Sega's sound driver. Each picture it also clears the 32X back buffer with 240 auto fills, hands the frame buffer to the SH-2s, takes it back and flips the buffer. No fighter, collision, camera or model data |
| Master SH-2 | Runs every command the 68000 sends. Fighter A's game logic, half of the collision test, the pose of both fighters, then the geometry: transform, cull, clip and light, and later the edge chains |
| Slave SH-2 | Fighter B's game logic, the other half of the collision test, the depth sort, the rasteriser and the fills, and three PWM voices |

Sources: [VF32X, 68000 code at `$FF0000`-`$FF2BB3`, SH-2 code at `0x06000528`, `0x06002370`, `0x06002448`, `0x060024C8`, `0x060073B4`, `0x0600729A`, `0x06007948`, `0x0600856C`]. The rest of this chapter walks one picture through that division. [Splitting work across three CPUs](cpu-split.md) compares it with the other games.

The 68000 sends two pad bytes, a replay flag and two sound-request bytes per picture, plus a command word. It gets back up to four status bytes in the communication ports and about two dozen bytes of mailbox. A pose of two fighters, two dozen joints each, does not fit in that, and no 68000 routine builds one [VF32X, 68000 code at `$FF005C`-`$FF0108`, `$FF1006`, `$FF11AE`]. In the attract mode it sends no input at all: both fighters are driven by the SH-2s.

## One picture, from the go to the flip

A picture takes **two vertical blanks**, and the 68000 has one state for each [VF32X, 68000 code at `$FF1152`, `$FF11AE`, `$FF13CC`, `$FF2A46`]:

1. **The go.** The vertical-blank task writes the word `$0186` to COMM0 (`$0184` in a played fight) and raises CMD to the Master. The high byte of the word is a busy flag: the Master clears it when the picture is done.
2. **State A**, right after that blank. It forwards the sound request to the Master, clears the whole back buffer with 240 auto fills of data 0 (one 256-word line each, no wait for FEN), and sets FM, so the frame buffer and the 32X registers now belong to the SH-2s. The plane B and sprite DMAs of the Mega Drive side run in the blank that follows.
3. **State B**, after that second blank. It waits for the busy flag to clear, takes FM back, copies a status block from the frame buffer (about two dozen bytes: the two life gauges and the camera angle that moves the background) and flips FS. The flip takes effect at the next blank, which is also the next go.

What happens on the SH-2s between the go and the flip, in one attract-mode picture, in the order it happens <span class="tag emulator">emulator</span> [VF32X, SH-2 code at the addresses in this chapter; recompiler run at frame 2000]:

| When (frames after the go) | Event |
|----------------------------|-------|
| 0 | The 68000 writes the go word and raises CMD |
| 0.01-0.09 | The Master runs the fighters' first two update passes, one fighter on each CPU, with two handshakes |
| 0.09 | The 68000 sends the sound request and starts its 240 fills (0.33 frame of fill time) |
| 0.13-0.20 | Collision, half on each CPU; the Master merges the two result sets |
| 0.25 | The Master starts the transform and the Slave starts sorting what the Master posts |
| 0.43 | The 68000 sets FM |
| 0.75 | The sort is done. The Master starts walking the buckets to build edge chains and the Slave starts drawing them |
| 1.5 | The Slave has drawn the last polygon; the Master writes the status block and clears the busy flag |
| 1.55 | The 68000 clears FM and flips FS |
| 2.0 | The next go |

Over about 1,470 attract pictures the go-to-done time was 1.17 to 1.82 frames, median 1.38. The low end is censored, because the 68000 only starts looking at about 1.19 frames. In a played fight, one picture in 1,101 took longer (2.44 frames) and the picture lasted three blanks <span class="tag emulator">emulator</span>. Three things follow from the shape of this sequence:

- **The 68000's clear costs the SH-2s nothing.** The SH-2s spend the first 0.75 frame on game logic, collision and the transform, and write no pixel before then, so the 68000's clear of the back buffer, 0.33 frame of fill and write time, lies entirely in their logic phase. The frame buffer changes hands at 0.43 frame, early enough. This is the [FM protocol](bus.md#the-vdp-and-the-frame-buffer) used as a schedule, not only as a handoff.
- **The rate is quantised.** The design cannot go faster than 30 pictures a second, however early the SH-2s finish. A picture that overruns two frames by any amount takes three, which is 20 a second ([What the shipped games ran at](60fps.md#what-the-shipped-games-ran-at)). In PicoDrive the SH-2s use 60% to 91% of the window; whether a console's wait states push them over is the largest open question.
- **A late picture slows the game, it does not skip.** The round timer and the attract demo's length, 900 pictures, are counted per picture, not per blank, so the game's clock and its pictures stay together. The 68000 never looks at real time [VF32X, 68000 code at `$FF0FC2`, `$8C34`].

## Four stages, two rings

The renderer is a pipeline across the two SH-2s with a ring of records in SDRAM between each pair of stages [VF32X, SH-2 code at `0x060073B4`-`0x06007947`, `0x0600729A`, `0x060194FC`, `0x06007948`]:

| Stage | CPU | Code | Reads | Writes |
|-------|-----|------|-------|--------|
| 1. Transform, cull, clip, light | Master | Overlay A, 1,428 bytes in on-chip RAM | Polygon streams, pose matrices | Ring A: 16-byte slots at `0x0603C000` |
| 2. Depth sort | Slave | Overlay D, 60 bytes (command 2) | Ring A | 512 buckets at `0x060368D0` |
| 3. Edge chains | Master | Overlay B, 1,280 bytes | The buckets, far to near | Ring B: 64-byte records at `0x06038000` |
| 4. Rasterise and fill | Slave | Overlay C, 560 bytes (command 1) | Ring B | Frame buffer, VDP fill registers |

**Stage 1.** For each of 34 to 36 body parts a picture, the Master calls overlay A with the part's polygon stream, which was unpacked into SDRAM from the cartridge when the scene loaded. Vertices are three signed halfwords and are rotated with `mac.w`. The perspective divide uses the hardware divider, started early and overlapped with the next rotation, and the quotient is read from the undocumented `0xFFFFFF1C` ([Division unit](../sh2/divu.md)). Then come a back-face test by a 2-D cross product (flag bit 4 of each polygon), 15 hand-written cases of near-plane clipping picked by a 4-bit outcode, and a light step: three `mac.w` against a light vector give a level from -7 to +8 that is **added to the polygon's colour index**. The palette is built in ramps of 16 entries to match, so lighting costs one addition a polygon and nothing a pixel. In one attract picture the Master takes about 640 polygons in and posts 332 slots to ring A, about 126,000 instructions in the overlay <span class="tag emulator">emulator</span>.

**Stage 2.** The Slave takes slots from ring A while the Master is still posting them, and inserts each polygon in one of 512 buckets chosen by `key >> 13`, the top bits of the 22-bit depth key, in descending order inside a bucket. This is the painter's algorithm with a bucket sort ([Bucket sorts](../techniques/software-3d.md#bucket-sorts)): no z-buffer, no comparison sort. Most of the command is spent waiting for the Master, which is the producer.

**Stage 3.** Once the sort is done, the Master walks the buckets from the last to the first, far to near, and for each polygon builds two y-monotone chains of up to seven `(x, y)` points, the left and right edges, clipped to the 320 × 224 screen. Each pair becomes a 64-byte record in ring B. About 273 records are posted a picture, about 64,000 instructions in the overlay <span class="tag emulator">emulator</span>. Giving the Master the geometry that can run beside the Slave's rasterising looks like pipeline balance, but that reason is inference.

**Stage 4.** The Slave consumes ring B while the Master is still building it. For each pair of chains it computes slopes with `muls.w` against a 16-bit reciprocal table that stays in the cartridge, steps both edges in 16.16 and draws each span one of two ways:

- **A span of more than a couple of words goes to the VDP's auto fill.** The Slave writes the length, the start and the data, with the colour index in both bytes. About 1,840 fills a picture in a fight, lengths mostly 3 to 10 words <span class="tag emulator">emulator</span>.
- **The odd edge pixels and the shortest spans are CPU byte and word stores**, about 3,500 byte and 1,500 word writes a picture.

A second path writes only through the overwrite image with CPU stores, so that zero pixels are skipped. A polygon asks for it with bit 1 of its colour word. Of the sixteen parts parsed from one picture, only the ground plate sets it.

The frame buffer is packed pixel with a 256-word line pitch, line *y* at word `0x1000 + 0x100 * y`, 240 lines, which uses the 128 KB exactly. The first words hold the line table the 68000 writes once. The mailbox the SH-2s write at the end of each picture sits just after it, at byte `$200` ([Frame buffers and the FS bit](../32x/vdp.md#frame-buffers-and-the-fs-bit)). The palette has 246 of 256 entries with the through bit; with PRI = 0, index 0 is the only one that lets the Mega Drive sky and sea show through, so the 68000's clear to index 0 is what puts the background behind the fighters ([Compositing](../32x/compositing.md#mega-drive-behind-32x-objects-over-a-tile-background)) [VF32X, 68000 code at `$FF0846`, `$FF2A46`].

### The ring protocol

Both rings use one convention, and the Slave's draw loop at `0x06007948` is its clearest instance:

| Field | Meaning |
|-------|---------|
| Status halfword at record `+28` (ring A: `+0`) | 8 = free, 4 = ready, 6 = ready and the last record of the picture |
| Producer | Waits for 8 through a cache-through read (`0x20000000 | ptr`), writes the record, writes 4, advances by one record |
| Consumer | Waits for 4 the same way; purges the record's cache lines with writes to `0x40000000 | ptr`, reads the record cached, calls the overlay at `0xC0000000`, writes 8, advances |
| Wrap | `and 0xFFFFCFFF` for ring A (4 KB), `and 0xFFFFBFFF` for ring B (16 KB) |
| End | A record with status 6 ends the loop; the consumer writes `0xAB00` (ring B) or `0xAC00` (ring A) and returns |

This is the discipline of [Cache discipline](cache.md): the flag is read through the cache-through view, the data is purged before it is read cached, and nothing else is shared. After each phase that two CPUs work on together, a routine at `0x06000756` purges the whole cache through the CCR mirror at `0xFFFFFE93`. Both CPUs run `CCR = 0x09`: cache on, **two-way mode, 2 KB of on-chip RAM** ([Two-way mode](../sh2/cache.md#two-way-mode-2-kb-of-on-chip-ram)). The on-chip RAM holds an overlay area at `0xC0000000`, reloaded for each phase, a state block at `0xC0000700`, the Master's matrix stack and the Slave's three PWM voices. No code runs from the cartridge or from anywhere but SDRAM and on-chip RAM [VF32X, SH-2 code at `0x06000738`, `0x06000770`, `0x06000756`].

## The fighters run on the SH-2s

The SH-2 image holds a state machine for each fighter, written in the arcade's Japanese move vocabulary, and the retail build left about eighty of its debug names in: `COM_MOTION`, `ACT_MOTION`, `COM_KAMAE` (a stance), `COM_FWALK`, `COM_NAGE` (a throw), `COM_YARARE` (a hit reaction), `COM_DOWN` and so on, in pairs, from a pointer table [VF32X, SH-2 image at `0x06005E54`-`0x060061B0`]. The 68000 holds none of it, and the code the 68000 executed in 1,913 distinct places during 3,600 frames touches no fighter state.

Each picture the two CPUs run **the same update chain, one fighter each**, in two passes: the Master from a task registered in a list at `0x06021000`, the Slave on commands 5 and 6 that the Master sends it, each followed by a whole-cache purge. The collision test is split the same way, the Slave's half on command 3, and the Master merges the two hit masks. Poses are built before the geometry: 15 joints a fighter, one matrix-stack round each, in 16.16 fixed point, from joint angles that come out of motion data the Master reads from the cartridge; the engine's own matrices are 8.8 [VF32X, SH-2 code at `0x06002370`, `0x06002448`, `0x060024C8`, `0x0600984A`, `0x060098A4`]. Models are polygon streams of up to 88 vertices a part; one fighter is 347 vertices and 322 polygons, 38 of them triangles, in 15 parts, plus the ground plate.

This is the opposite of the games that [split Star Wars Arcade or After Burner Complete](cpu-split.md#how-existing-programs-divide-the-work): there the 68000 owns the game and the SH-2s answer. Here the data the logic needs, models, motion and tables, all sits in the 2.9 MB after the SH-2 image, which the 68000 cannot read at all: it never selects a bank, so it sees only the first megabyte. Putting the logic where the data is makes the interface this small.

## The 68000: pictures around the picture

The 68000's main loop, vertical-blank handler, pad reader, picture states and HUD, `$2BBC` bytes, are copied from the cartridge into work RAM at `$FF0000` at boot, and the code that runs in a fight is nearly all there. The current state is the operand of a `jsr` that a state rewrites, and a second rewritten `jsr` names the task the next blank runs. The loop has the same three-line shape as Virtua Racing Deluxe's: `jsr state`, set a flag, wait for the blank handler to clear it, here in a counting loop with interrupts enabled [VF32X, 68000 code at `$FF0000`-`$FF0050`, `$880BEC`].

**The Mega Drive layers.** The sky and sea are plane B, the HUD plane A. The 68000 re-sends 32 rows of 41 cells to plane B by DMA every picture from a panorama in RAM, so the background scrolls by moving a window over the source, not by scrolling the plane, and the camera angle in the mailbox picks the window. The HUD, life gauges, timer, round marks and names, is also the 68000's work, changed on its own schedule. About 1,440 words go through the VDP a picture. Every one of the 37,194 DMAs in a played run reads work RAM, with register 23 = `$7F`; the game never sets RV, never uses the FIFO, never raises INTS and never touches the bank register or `$A130F1`, so it has no save RAM either [VF32X, 68000 code at `$FF2A46`-`$FF2B34`, `$FF1F66`] <span class="tag emulator">emulator</span>.

**Sound** is Sega's driver V3 (its version string reads `V313F`, with the game's tag `VF1`), copied to RAM at `$FF4000` and called at the end of every blank. The 68000 writes the YM2612 and the PSG itself. The Z80 is parked on `DI; DI; JR $`, and the driver instead copies each tune into **Z80 RAM**, about 4.9 KB for the fight music, and reads its sequence from there, presumably to keep the sequencer's reads off the cartridge the SH-2s share. The samples are the Slave's: three voices of 8-bit PCM read straight from the cartridge, summed in the PWM interrupt and written to the mono register once per interrupt, so the output is an 11 kHz sample-and-hold. The 68000 forwards two sound-id bytes a picture to the Master, which queues them for the Slave [VF32X, 68000 code at `$FF4000`, `$FF1006`; SH-2 code at `0x0600856C`, `0x060086C8`] ([Sega's V3](../megadrive/sound.md#segas-v3-sequencing-on-the-68000-samples-on-the-z80), [PWM audio](../32x/pwm.md)).

**Compression.** Three schemes hold the 68000's graphics: a Huffman coder of (pixel, run) symbols for Mega Drive tiles, a Kosinski-style LZ for byte data and for 320 × 224 pictures written straight into the frame buffer, and a word-oriented tilemap coder. The first two were checked by decoding with a port against the emulator's VRAM and RAM [VF32X, 68000 code at `$880D10`, `$881038`, `$880E50`].

## What it shares with Virtua Racing Deluxe

Two kinds of evidence say the two games came from one codebase. The first is bytes. Of the 29 retail cartridges and the development discs in the sources, only these two contain the Slave's idle delay, `mov #64,r7; nop; dt r7; bf`, and the cache set-up routine, `0x10` to CCR, eight `nop`s and `0x09`, followed by a routine that clears the tag array, byte for byte [VF32X, SH-2 code at `0x06000344`, `0x06000738`; 32X-ROMSET, Virtua Racing Deluxe, SH-2 code at `0x06000608`, `0x060045CC`]. The second is shape, the parts below that match in structure.

| Construct | Virtua Fighter | Virtua Racing Deluxe (retail code) | |
|-----------|----------------|------------------------------------|---|
| Slave main loop | Polls a command byte, 16-entry table, 64-pass idle delay | The same, polling `0x20004024`; the table at `0x060005C8` | Same shape, same delay |
| Master to Slave | A command byte only the Master writes; the Slave zeroes it; the Master waits for 0 | The same, in the high byte of COMM2 † | Same pattern, different register |
| Ring to the rasteriser | 64-byte records, status halfword at `+28` (8, 4, 6), end marker, wrap with `and 0xFFFFBFFF`, a 16-pass wait, a call to `0xC0000000` | The same fields and constants | Same design, different register use |
| On-chip RAM | Overlays reloaded per phase at `0xC0000000`, state block at `0xC0000700` | The same layout | Same |
| Perspective | Hardware divider, quotient from `0xFFFFFF1C` | The same, no software divide | Same |
| Depth order | Painter's algorithm, 512 buckets, in a stage of its own on the Slave | Painter's algorithm in buckets, inserted inside the transform overlay † | Same technique, different place |
| Edge-chain stage | Master overlay B, 1,280 bytes | Master overlay B, the same job † | Same job |
| Cache | `CCR = 0x09` on both CPUs | The same | Same |
| Frame buffer | Packed pixel, 256-word pitch, base `0x1000` | Packed pixel, 256-word pitch, base `0x2000` | Same shape |
| Who flips FS | The 68000, after the SH-2s clear the busy flag | The 68000, in its blank task, after a flag from the SH-2s | Same rule |
| 68000 frame loop | `jsr state`, flag, wait for the blank, one hang stub for unused vectors | The same | Same |
| DMA and RV | Every DMA from work RAM, register 23 = `$7F`; RV never set | The same | Same |

Both columns are read from the retail code and the Virtua Fighter column was confirmed in runs. Rows marked † were read by a second reader of the Virtua Racing Deluxe code and not re-checked; the others were checked in both listings for this chapter. Things Sega's own samples contain, the FRT sequence for instance, are left out.

The two games differ in the front end. Virtua Racing Deluxe's 68000 runs the game and sends one command and a **2,560-byte scene description through the FIFO** each picture, and both SH-2s load the same 1,748-byte transform overlay; Virtua Fighter's SH-2s run the game, nothing crosses the FIFO, and only the Master transforms. Virtua Racing Deluxe takes FM and flips FS in the 68000's blank task and finishes a picture in a multiple of three blanks (859 pictures in 2,574 frames); Virtua Fighter does it from main-loop states and finishes in two. Virtua Racing Deluxe's 68000 runs from the cartridge with a 24-byte stub in RAM and selects bank 1; Virtua Fighter's runs from RAM and never selects a bank. Virtua Racing Deluxe's Z80 runs a 653-byte sample player; Virtua Fighter's is parked and its Slave plays the samples.

### What this settles in the Virtua Racing Deluxe chapter

The retail code of both games supports the pipeline reading that [the Virtua Racing Deluxe chapter](case-study-vr.md) left open, and it contradicts three of that chapter's claims. Which of them rest on the retail 68000 code, read for this book and not run on a console:

- **Confirmed.** The 68000 flips FS only after the SH-2s signal that the picture is drawn; if not, it tries again at the next blank. The game steps once per blank and finishes a picture every third. The Slave's loop has a 16-entry table and a 64-pass delay.
- **Contradicted.** The chapter lists "depth sorting" under the 68000. The second reader found no sort in the 68000 code and a bucket sort on the SH-2s, as in Virtua Fighter, which the other findings here make likely but nobody re-checked. The "14 block copies and 21 pixel jobs a picture, each a handshake" the project describes are not visible from the 68000, which sends one command and one FIFO block a picture and raises no CMD interrupt; if the jobs exist they travel inside the block or between the SH-2s. And the one-line summary "the 68000 sets, the SH-2 clears" does not describe the 68000's waits: it waits on flag bits that the SH-2 sets in the low byte of COMM1 and clears them itself with `bclr`.
- **Settled, in part.** Which CPU transforms ([discrepancy 28](../appendices/discrepancies.md)): the Master's command 1 and the Slave's command 2 both call the routine at `0x0600252C`, which copies 436 longwords, 1,744 bytes, into on-chip RAM at `0xC0000000`, and then the same transform drivers, so Virtua Racing Deluxe loads its transform code on both SH-2s and the Slave is not only a renderer. How the work is split between them, and which CPU builds the edge chains, was not traced. It differs from Virtua Fighter, where only the Master transforms.
- **Corrected.** The line table is at word `256 × (n + 1)` in no game here: Virtua Racing Deluxe's is at `0x2000 + 0x100 * n` and Virtua Fighter's at `0x1000 + 0x100 * n`. Only the 256-word pitch is general ([Auto fill](../32x/vdp.md#auto-fill)).

## What the code does well

- **It keeps the 68000 out of the loop.** Five bytes a picture and a command is the smallest interface of the games in the book. Nothing the 68000 does waits on the SH-2s except the one poll in state B, which the emulator puts at about 8% of the picture. The 68000 spends a quarter of the picture on the clear and the blank-time DMAs, and the rest idling.
- **It overlaps three producers and consumers.** Stage 1 and the sort run together, stage 3 and the rasteriser run together, and the 68000's clear runs under the SH-2s' game logic.
- **It uses the 2 KB of on-chip RAM as an overlay area.** Four routines of 60 to 1,428 bytes take turns in the same 2 KB, each copied in at the start of its phase for a few dozen instructions.
- **Lighting is free.** One addition to the colour index per polygon, against ramps in the palette.
- **The VDP does the spans.** About 1,840 auto fills a picture, most three to ten words long, draw the interiors of about 270 polygons, and the Slave stores only the edge pixels and the shortest spans itself.
- **Game time counts pictures.** A slow picture slows the game and nothing else gets out of step.

## What it leaves on the table

- **There is no known margin.** The SH-2s finish in 1.2 to 1.8 frames of a two-frame window in PicoDrive. Because the flip takes effect only at a blank and there are two buffers, a picture that needs 2.01 frames costs three, which is the cliff from 30 pictures a second to 20, and the design has nothing in reserve to catch it. The only slack in the game is what the SH-2s leave in the window; whether a console leaves any is not known.
- **It polls a lot.** The Slave reads the VDP's FEN flag about 34,000 times a picture through cache-through reads, and the ring statuses and the command byte the same way, and it reads the reciprocal table and the PCM from the cartridge. On a console each of those is a bus cycle the Master also needs. PicoDrive does not charge them. They may be what moves a picture from two frames to three.
- **The Master does the geometry and the logic; the Slave waits for it.** About 126,000 plus 64,000 instructions in the overlays and 60,000 to 100,000 more in logic and poses is 250,000 to 290,000 instructions a picture on the Master, a third of the two-frame window at one clock each, before any cache miss; the Slave's busy time was not separated from its waits.

## Built to survive, mostly

- **The Master's dispatcher follows Sega's revised sample**: mask to `0xF0`, write TOCR and read it back, a level table at VBR + `0x40`. The Slave does not: its PWM handler is copied into on-chip RAM, patched into the vector table at boot and clears the interrupt through the cached alias with no read-back, which is none of the workaround's steps ([Hardware bugs and workarounds](../32x/bugs.md)).
- **The reset handler restarts both CPUs at their manual-reset vectors**: clear VRES through the cached alias `0x00004014`, reload the stack pointer from the vector table, push the saved SR and the reset PC and `rte`. It never tests RV. That is safe here because the game never sets RV. There is no `VRES` word anywhere in the 68000 code, unlike Virtua Racing Deluxe's, so the 68000 reads the CPUs' own `M_OK` and `S_OK` again after a reset [VF32X, SH-2 code at `0x06000150`; 68000 code at `$8808B4`] ([Sega's sample code in the games](../appendices/sample-code.md)).
- **The Master checks its own stack after every command** and hangs if it is unbalanced.
- **The retail image still holds the debug names**, 18 error stubs and seven more that nothing references, and a `JUDGE ERROR` string.
- **The 68000 refuses a PAL console** with a message and a divide by zero, found by reading, not run.

## What the design teaches

- **Put the simulation where the data is.** Five bytes a picture is possible because the models, the motion and the tables live in the cartridge the SH-2s read and the 68000 cannot.
- **Link pipeline stages with rings and purge by hand.** The convention is small: a status halfword in each record, a cache-through read for the flag, a purge before the cached read, a whole-cache purge at the end of each phase.
- **Use on-chip RAM as an overlay area when the phases are short and the code is small.**
- **Hide a handoff by using it.** The back-buffer clear fills the time the SH-2s spend before they draw.
- **Colour the light.** Ramps in the palette move lighting out of the pixel loop.
- **Count pictures, not blanks, for anything the player can feel.**
- **Know what the cadence is.** Two blanks a picture is a design choice with a ceiling and a cliff; so is three.

## Open questions

- Does a console finish a picture in two blanks? The SH-2s' wait states, the Slave's polling and the Master's cartridge reads are not modelled. Counting FS flips on a console over an attract fight would settle it.
- Where does the status block's first half come from, and which routine writes the words at offset 16 and 20? The 68000 reads 24 bytes; the SH-2 side writes a 16-byte block at the end of each picture, and a second routine's literal pool names offset `0x210`. They were not reconciled.
- What do the commands the attract mode never sends do (`0x83`, `0x88`-`0x8D`, `10`, `11`, `13`-`16`)? Their roles are inferred from the data they touch.
- The fighter state machine, the model packer, the motion data's format and the collision tables were located but not read.
- Does colour-word bit 1, which only the ground plate sets, mean "ground" or "needs the overwrite image"?
- Why does the Master write `0x34` to `0x06000034` before every command byte? It looks like a write barrier; only a console can show whether it matters.
- Does the Slave's CMD vector, which is a register dump, ever run? The Slave enables CMD, nobody raises INTS in 5,700 frames, and one scene might.

## Sources

- [VF32X](../appendices/bibliography.md#vf32x): the SH-2 program and the 68000 code, as cited; the notes `notes/games/vf/SH2.md` and `M68K.md`
- [32X-ROMSET](../appendices/bibliography.md#32x-romset): Virtua Racing Deluxe (USA), SH-2 code at `0x06000608`, `0x060039F0`-`0x06003A4C`, `0x060045CC`, `0x06000780`, `0x060005C8`; 68000 code at `$881D0C`, `$8828C0`, `$881D70`
- [VRD-NOTES](../appendices/bibliography.md#vrd-notes): the claims checked
- [SWA](../appendices/bibliography.md#swa), [AB32X](../appendices/bibliography.md#ab32x): for comparison
