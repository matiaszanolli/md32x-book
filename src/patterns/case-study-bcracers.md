# Case study: BC Racers

*BC Racers* is Core Design's 32X port of its 1994 Mega-CD kart racer, published in North America only, by Front Street Publishing, in June 1995 [WP-BCR]. Like Mortal Kombat II, it comes from a studio that did not work for Sega, and its SH-2 code is mostly compiled C. The race is drawn as a textured ground plane, the "Mode 7" floor of [Pseudo-3D roads and Mode 7](../techniques/roads-mode7.md), with scaled sprites for the racers and the scenery.

It is also a slow game. GamePro's review found it sharper than the Mega-CD version but worse to play, with a choppy frame rate and slowdown [WP-BCR]. In PicoDrive it looks fine: a steady 30 pictures a second. With a model of the 32X's wait states and the SH-2's cache it drops to 14. The difference is the story of this chapter. Almost everything the game does goes through the cache to the cartridge, on one SH-2, while the other waits for work. And a game loop that keeps game time against the clock makes each slow picture slower still.

## How far the evidence goes

The code was read by disassembly. The dump's header checksum is 0, so it cannot be checked against the header, and its MD5 is not in any public list the book could find [BCR]. Nothing in it looks patched, but it is not proven to be the retail original. Timings come from headless PicoDrive runs and are tagged <span class="tag emulator">emulator</span>. All figures are for NTSC: 60 frames a second, 384,000 SH-2 clocks a frame. Two kinds of run matter here:

- **Stock PicoDrive** charges an SH-2 almost nothing for memory: no cache misses, no frame buffer or cartridge wait states ([Access timing per CPU](../32x/timing.md#in-emulators)). It measures how many instructions the game executes.
- **The timing model** in the Virtua Racing Deluxe project's copy of PicoDrive charges the 32X manual's wait states and keeps the cache's tags, run here with the real boot ROMs so that the cache is on [VRD-NOTES, PicoDrive timing patch; AU-NOTES, ROADMAP.md U-093]. It charges a line fill from the cartridge about half the book's 64 to 136 clocks ([discrepancy 48](../appendices/discrepancies.md)), and has no bus contention between the two SH-2s, so on this game it errs towards too fast. A build of it that logs cache misses by address was made for this chapter [BOOK-TOOLS, build_miss_core.sh].

One more caution: under the timing model the profiler attributes only 79% of the Master's time and the rest is unexplained, so the shares below, which are of the whole time, add up to less than 100%.

## How the game divides the work

| CPU | Job |
|-----|-----|
| 68000 | A command server. It waits for a command from the Master in `$A15120`, runs it and clears the word: clear VRAM, report the console's region, pass on a sound request, set the backdrop colour. Its Mega Drive picture supplies the sky. In a race it spends 82% of its time waiting for the next command <span class="tag emulator">emulator</span> |
| Master SH-2 | Everything else: the game itself in C, run from the cartridge; half of the ground; the top half of every sprite; the scenery's projection and sort; the flip and the palette in the vertical interrupt |
| Slave SH-2 | A worker with no program of its own: the other half of the ground and of each large sprite, screen clears, and a cache purge when asked |

Sources: [BCR, 68000 code in work RAM at `$FFC038`-`$FFC058` (a copy of cartridge `$010BEA`); SH-2 code at `0x060017E4`, `0x06032676`-`0x060326AC`, `0x060326F8`-`0x06032734`]; [Splitting work across three CPUs](cpu-split.md#the-68000-as-a-server).

The Slave's whole main loop is about thirty instructions. It clears a communication word, waits until the word is not zero, loads a function address, fourteen registers and GBR from a 64-byte record in SDRAM, calls the function, and starts again. The Master hands over a job by filling the record and writing 1 to the word, and waits for 0 when it needs the result [BCR, SH-2 code at `0x06032676`-`0x060326AC`]. Any routine can be split this way without the Slave knowing what it runs. The price is that both CPUs work in lock step, job by job, and the Slave has nothing to do between jobs.

Three of the Master's job routines write the record without first checking that the Slave has finished the previous job. Had it not, the new record would land under a running job, and the loop's own clear of the word after that job would wipe the new request [BCR, SH-2 code at `0x06002438`, `0x060024E4`, `0x06003056`]. In this game the earlier job is always long finished, so the race never fires; the sprite routines do check first [BCR, SH-2 code at `0x06001FD0`, `0x060022E6`].

## Code in the cartridge

The SH-2 image that the boot copies to SDRAM is 208,560 bytes, but 193,709 of them are zeros, copied from the cartridge at every boot: memory for the game's variables and buffers, which could have been cleared instead. What is left is 5.8 KB of data (the menu and race text in English, German and French, and tables of addresses), 6.6 KB of code for the drawing, the interrupts and the Slave's jobs, and 2 KB for the Slave's loop, the vertical interrupt's work and the start-up [BCR, SH-2 image `0x06000000`-`0x06032EAF`]. Everything else, about 140 KB of compiled C from cartridge `$048648`, runs where it is, through the cached cartridge window ([Code that runs from the cartridge](../howto/toolchain.md#code-that-runs-from-the-cartridge)) [BCR, SH-2 code from `0x02048648`]. The C compiler's run-time helpers sit at the end of the cartridge, so even a shift by a variable amount is a call into the cartridge [BCR, SH-2 code at `0x022F6028`-`0x022F6040`].

Neither SH-2 writes CCR when it starts: both rely on the boot ROMs having turned the cache on. The Master later asks the Slave to purge and re-enable its own cache from ten places in the game [BCR, SH-2 code at `0x060030BE`-`0x060030E4`]. Run under the timing model without the boot ROMs, so that the Master's cache stays off, the game falls to about one picture a second <span class="tag emulator">emulator</span>. That is a measure of how much the game leans on the cache, not something a console would do.

## One picture

Each picture is one pass of a loop in the game's C code [BCR, SH-2 code at `0x020597AA`-`0x02059A46`]:

**1. Count the frames and ask for a flip.** The vertical interrupt counts frames. The loop reads the count, the number of frames the last picture took, then sets a flag that asks the interrupt to show the picture just drawn, and resets the count [BCR, SH-2 code at `0x06032840`, `0x06032A66`-`0x06032A8E`].

**2. Wait for the flip, then have the Slave clear the sky.** Before it can draw into the buffer that is still on screen, the Master polls the flag until the interrupt has cleared it, up to a whole frame. Then it gives the Slave 64 lines to clear, word by word with the CPU rather than with the VDP's auto fill ([Auto fill](../32x/vdp.md#auto-fill)) [BCR, SH-2 code at `0x06003056`-`0x06003078`, `0x06002D9C`].

**3. Run the game once for each frame that passed.** The frame count, capped at 4, says how many game steps to run: a routine for each player, two passes over the 256 object slots, and more [BCR, SH-2 code at `0x0205985C`-`0x0205991E`]. So the game keeps time against the clock, whatever the frame rate, until a picture takes more than four frames; then the game itself slows down ([When a picture runs long](60fps.md#when-a-picture-runs-long)).

**4. Project the scenery.** Objects near the camera are rotated, projected with the hardware divider and inserted into a list sorted by depth; a 40 × 40 window of a grid around the camera adds the trackside scenery [BCR, SH-2 code at `0x06002838`-`0x06002A0A`].

**5. Draw the ground** (next section), then the sprites, then hand the result to the next pass's flip.

The vertical interrupt does two more things every frame. It rebuilds all 255 colours of the palette with a fade level subtracted, because the word that enables the fade is set when a fade starts and never cleared; in a race the level is 0 and the colours come out unchanged <span class="tag emulator">emulator</span> [BCR, SH-2 code at `0x06032A90`-`0x06032B16`, `0x02055B06`-`0x02055B26`]. And the Master also takes a horizontal interrupt on every line, 224 a frame, whose handler adds 1 to a counter that no code reads ([The 32X's five interrupts](../sh2/intc.md#the-32xs-five-interrupts)) [BCR, interrupt mask `$0E` and HCOUNT 0 read in PicoDrive; SH-2 code at `0x060019E4`-`0x06001A00`].

## The ground

The 3D view fills lines 16 to 143. The 64 lines from 16 to 79 are cleared to colour 0 and get only scenery sprites; below them the ground takes 64 lines. Colour 0 is the one palette entry with the through bit, and PRI is 1, so the cleared lines show the Mega Drive's picture behind them: the sky comes from the Mega Drive ([Mixing 32X and Mega Drive graphics](../32x/compositing.md#the-rule-for-each-pixel)) <span class="tag emulator">emulator</span> [BCR, bitmap mode `$8081`, palette and frame buffer read in PicoDrive]. The panel at the bottom is in the 32X frame buffer.

**Rows.** For ground row *i*, the distance is a constant over 2 + 16*i*. Each row gets four divides on the hardware divider, for the texture position at the left edge and the step per pixel, written to a table of 64 rows ([Division unit](../sh2/divu.md)). The Master does rows 0 to 31, the Slave 32 to 63, at the same time [BCR, SH-2 code at `0x06002438`-`0x060024DC`]. One of the four results is read from `0xFFFFFF1C`, the copy of the quotient that Hitachi's manual leaves out ([Two registers the manual leaves out](../sh2/divu.md#two-registers-the-manual-leaves-out)); the other three from DVDNTL [BCR, SH-2 code at `0x060024AA`].

**Spans.** Each line is 160 texels, each written twice as one 16-bit word, so the ground has half the horizontal resolution of the screen, like d32xr's default floors ([A textured floor](../techniques/roads-mode7.md#a-textured-floor-d32xr)). The Master draws the 32 lines nearest the horizon, the Slave the 32 nearest the camera. For each texel the loop runs 32 instructions [BCR, SH-2 code at `0x0600259E`-`0x060025FE`]:

1. Read the map cell under the point: the map is 128 × 128 words, kept in the unused memory at the end of the frame buffer (`0x24012E00`). It has to be in both buffers, since an SH-2 sees only the one not on screen.
2. Use the cell to read a two-word record from SDRAM: where that tile's pixels are, and which of eight orientation tables to use. A tile can be placed in any of four rotations, mirrored or not.
3. Read the texel's offset within its 32 × 32 tile from the orientation table, 2 KB of words that list the tile's 1,024 positions in the turned order.
4. Read the texel.
5. Write it twice as one word.

The first 8 lines, nearest the horizon, add a sixth step: the texel goes through a 256-byte colour table of its own for each line, which darkens the far ground into haze [BCR, SH-2 code at `0x0600252E`-`0x0600259C`]. A set-up routine builds the 512 records, 64 tiles in 8 orientations, and rewrites the map's cells into record numbers in place [BCR, SH-2 code at `0x06002358`-`0x060023A8`; orientation tables at cartridge `$044648`-`$048647`].

The texels, the orientation tables and the haze tables are all in the cartridge, read through the cache. The ground is the only part of the game simple enough to replay outside the emulator, so a simulation ran the loop's arithmetic over one picture's real map, records and rows, and sent every cached access, the loop's own instruction fetches included, through a model of the SH-2's 4 KB, four-way cache [BOOK-TOOLS, groundsim.py]:

| One picture | Master, rows 0-31 | Slave, rows 32-63 |
|-------------|-------------------|-------------------|
| Texels | 5,120 | 5,120 |
| Line fills from the cartridge | 1,200: 793 texels, 394 orientation tables, 13 haze | 522: 262 texels, 260 orientation tables |
| Line fills from SDRAM | 83 | 14 |
| At the manual's costs: cartridge fills | 77,000-163,000 clocks | 33,000-71,000 |
| Map reads from the frame buffer, 7-14 clocks each | 36,000-72,000 | 36,000-72,000 |
| Word stores to the frame buffer, 3-5 clocks each | 15,000-26,000 | 15,000-26,000 |

Each CPU also executes about 165,000 instructions. The lines near the horizon step further across the texture from one pixel to the next and touch more cache lines, so the Master's half needs more than twice the Slave's line fills, on top of its haze lines. The split by line count is not a split by cost.

The figures are for one picture of the first track, with a cold cache, which is close to the game: four game steps run between two pictures and replace what the ground left in the cache. They depend on the model being right about the cache, which the SH7604 manual describes ([Cache](../sh2/cache.md)), and on the manual's costs per access ([Access timing per CPU](../32x/timing.md#the-sh-2)).

## Sprites

Every sprite is split between the two SH-2s. The Master clips it, works out the scale steps with the divider, waits for the Slave to finish its last job, gives it the bottom half of the lines and draws the top half itself [BCR, SH-2 code at `0x06001F44`-`0x06002016`, `0x06001B80`-`0x06001C18`]. The blitters write single bytes through the overwrite image, so the VDP skips colour 0 and the loops test nothing ([The normal and overwrite images](../32x/vdp.md#the-normal-and-overwrite-images)). One variant draws through a colour table. Another reads the destination pixel and looks up the pair in a 64 KB table, the blend table of [Transparency in 8-bit colour](../techniques/2d-effects.md#transparency-in-8-bit-colour), for shadows [BCR, SH-2 code at `0x06001DC4`-`0x06001DDE`, `0x06001EE6`-`0x06001F02`].

## Sound

Sound effects need no CPU per sample. A routine points SH-2 DMA channel 1 at a sample in the cartridge, sets the PWM to request a transfer whenever its FIFO has room, and lets the DMA copy one byte per request into the low byte of the mono pulse-width register, `0x20004039` ([DMA](../32x/pwm.md#2-dma-d32xr)) [BCR, SH-2 code at `0x0600312A`-`0x06003166`]. So the samples are 8-bit values used directly as pulse widths. This was read from the code, not heard; whether the hardware takes a byte write to that address as the game expects has not been checked.

## Where the time goes

**The frame rate.** In stock PicoDrive the race flips 743 times in 1,500 frames, 29.7 pictures a second, almost all of them two frames long, and every flip is a new picture. Under the timing model it flips 420 times in 1,800 frames: 14.0 a second, with pictures of four frames (284) or five (127) <span class="tag emulator">emulator</span> [BCR, FS bit read every frame in PicoDrive, 12 October 2026].

**The loop makes it worse.** The game steps once for each frame the last picture took, so a slower picture means more game logic in the next one. In stock PicoDrive the count was 2 in 582 of 600 frames, and 3 in the rest. Under the timing model it was 4, and in 14 frames 5, which the cap cuts to 4: those pictures run the game slower than the clock <span class="tag emulator">emulator</span> [BCR, frame count at `0x0603E230` watched for 600 frames in each]. GamePro's slowdown is consistent with that cap, on a machine slower than the model.

**The Master is the slow stage.** Per picture of four frames under the timing model <span class="tag emulator">emulator</span> [BCR, PicoDrive per-instruction profile with the timing model, 600 race frames from a saved state, 12 October 2026]:

| Master's work | Clocks a picture | Share of four frames |
|---------------|------------------|----------------------|
| The game's C code in the cartridge, mostly four game steps | 471,000 | 31% |
| Ground, its half | 254,000 | 17% |
| Sprites, the top halves | 161,000 | 10% |
| Waiting for the previous flip | 152,000 | 10% |
| Scenery projection and sort | 67,000 | 4% |
| Horizontal interrupts | 58,000 | 4% |
| Palette in the vertical interrupt | 36,000 | 2% |

The Slave executed 34% of the time and was waiting for its next job the rest. Its ground half took about 228,000 clocks a picture, its sprite halves about 136,000 and its screen clears about 72,000.

Under stock PicoDrive the same Master needs about 600,000 clocks a picture, and pictures fit in two frames with time to spare. The timing model adds the cost of memory, and most of that is the cartridge. In the same run the Master missed the cache 2,513 times a frame on cartridge addresses, plus 1,615 times on SDRAM, and the model charged it 78,000 clocks a frame for the cartridge fills. The misses are spread across the C code (the busiest 16 KB is `$060000`-`$063FFF`), the orientation tables, the texels and, in SDRAM, the 14 KB of object slots that the game's two passes walk every step <span class="tag emulator">emulator</span> [BCR, miss log by address in PicoDrive with the timing model]. At the book's 64 to 136 clocks a fill, instead of the 31 the model adds, those 2,513 fills would cost 161,000 to 342,000 clocks a frame: 0.3 to 1.1 million clocks more for each four-frame picture, one to three more frames. That is an estimate from the counts, not a measurement, and the counts would change on a slower machine. It says the console should run slower than the model's 14, and that the cap of 4 game steps would then make the game itself slow down, which is what GamePro reported.

## What it does well

- **A worker that can run anything.** Handing the Slave a function and its registers makes every routine splittable with a few lines of set-up, and the game splits its ground, its sprites and its clears this way. [Both SH-2s on every stage](cpu-split.md#both-sh-2s-on-every-stage) gets the same effect in d32xr with far more machinery.
- **Half-resolution ground.** Writing each texel twice halves the work per line, the same trade d32xr makes by default.
- **One divide per row and coordinate, in hardware,** and only 64 rows: the far ground is short on screen, and the haze tables hide what little detail it would have shown.
- **Hardware transparency.** Writing every sprite through the overwrite image removes the transparency test from all the blitters.
- **Eight tiles from one.** The orientation tables let a map cell turn or mirror its tile, so the tracks need fewer distinct tiles.
- **Game time held against the clock** down to 15 pictures a second, so a slow scene does not slow the race until pictures pass four frames ([A fixed tick, whatever the frame rate](../techniques/game-logic.md#a-fixed-tick-whatever-the-frame-rate)).
- **Sound effects by DMA,** with no CPU time per sample.

## What it leaves on the table

Roughly in order of what each costs the Master, the slow stage:

- **The game logic runs on the Master, from the cartridge, while the Slave waits.** At four steps a picture it is the largest single cost, and the catch-up loop raises it exactly when the game is already slow. The Slave, idle two thirds of the time, could run the game step for picture *n* + 1 while the Master draws picture *n* ([A pipeline: geometry on the Master, pixels on the Slave](cpu-split.md#a-pipeline-geometry-on-the-master-pixels-on-the-slave)). That would mean sharing the game's state across the two caches ([Sharing between the two SH-2s](cache.md#sharing-between-the-two-sh-2s)), but even moving only the busiest C routines into SDRAM would bring each of their misses down to 12 clocks.
- **The ground's data lives in the cartridge.** Copies in SDRAM of the 64 tiles and the orientation tables, about 80 KB, would cut the Master's ground fills from 77,000-163,000 clocks a picture to about 14,000 by the simulation's count. The orientation tables cost a read per texel and 16 KB of cache footprint; drawing turned tiles from pre-turned copies, or stepping through the tile with signed steps, would avoid both.
- **The wait for the flip comes before the game logic.** The Master waits up to a frame, about 152,000 clocks a picture, before running game steps that never touch the frame buffer. Running them first and waiting afterwards would hide most of that wait ([Waiting without wasting](60fps.md#waiting-without-wasting)).
- **The split is by lines, not by cost.** The Master's half of the ground is the expensive half, and it adds the haze lines, while the Slave waits for its next job. Giving the Slave the far rows, or more of them, would even the two out ([Balancing per picture, not per task](cpu-split.md#balancing-per-picture-not-per-task)).
- **Interrupts that do nothing useful.** The horizontal interrupt on every line, for a count nobody reads, and the palette rebuilt every frame at fade level 0, together cost about 94,000 clocks a picture, 6% of the Master's time.
- **The object passes walk all 256 slots.** Each game step runs two passes over 14 KB of slots, three and a half times the cache, to find the live ones; a list of live objects would visit only those.

The CPU screen clears cost only the Slave, which has time to spare, so in this game they cost nothing in the frame rate.

## What to take away

- **An emulator without a cache model can hide a factor of two.** The same race is 30 pictures a second in stock PicoDrive and 14 with wait states and a cache; code from the cartridge is where the difference comes from.
- **Keep the per-pixel data and the busiest code out of the cartridge.** A line fill from it costs five to eleven times one from SDRAM.
- **A catch-up loop on the rendering CPU feeds on itself.** Run the logic somewhere else, or cap the steps low and accept that the game slows down.
- **A second CPU used only in lock step is mostly idle.** Give it whole stages, not halves of each job.
- **Check what the interrupts do.** A handler on every line costs about 4% of a CPU even when it does nothing.

## Open questions

- What does the race run at on a console, with one player and with two? The two-player mode, which clears two views and draws the ground twice, was not run [BCR, SH-2 code at `0x060030E8`, `0x0204B680`].
- Does the PWM take the DMA's byte writes to the low byte of the mono register, `0x20004039`, as 8-bit pulse widths?
- Where does the 21% of the Master's time go that the profiler does not attribute under the timing model?
- Is the panel at the bottom of the screen redrawn every picture? Its cost was not traced.

## Sources

- [BCR](../appendices/bibliography.md#bcr): SH-2 code at `0x060017E4`, `0x060019E4`-`0x06001A00`, `0x06001B80`-`0x06002316`, `0x06002358`-`0x060023A8`, `0x06002438`-`0x060025FE`, `0x06002838`-`0x06002A0A`, `0x06002D9C`, `0x06003056`-`0x06003166`, `0x06032676`-`0x06032B16`, `0x02055B06`-`0x02055BD4`, `0x020597AA`-`0x02059A46`, `0x0204B680`; orientation tables at `$044648`; 68000 code at `$FFC038` (copied from `$010BEA`); PicoDrive runs with and without the timing model, profiles, miss logs and watches, 12 October 2026 (`notes/games/bcr/ANALYSIS.md`)
- [WP-BCR](../appendices/bibliography.md#wp-bcr): publisher, release and GamePro's review
- [BOOK-TOOLS](../appendices/bibliography.md#book-tools): build_miss_core.sh, groundsim.py
- [VRD-NOTES](../appendices/bibliography.md#vrd-notes), [AU-NOTES](../appendices/bibliography.md#au-notes): the timing model
