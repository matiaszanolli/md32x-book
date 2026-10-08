# Case study: Star Wars Arcade

*Star Wars Arcade* (Sega, 1994) is a 32X conversion of Sega's 1993 arcade game, developed at Sega InterActive, as its credits say [SWA, cartridge `$00CCC0`]: X-wing and Y-wing missions in flat-shaded polygons, on a 2.5 MB cartridge. Its retail dump is clean, and it is the most complete shipped 3D renderer in the sources [SWA].

It differs from [After Burner Complete](case-study-afterburner.md), which Rutubo Games programmed for Sega, in most of its choices. After Burner draws scaled sprites with one SH-2 and gives the other only sound. Star Wars Arcade draws polygons with both SH-2s in a pipeline, and lets the 32X's fill hardware draw long spans while the CPU works. It is the better-engineered of the two, and still not a fast game: between 32 and 34 pictures a second in play, unevenly paced, by PicoDrive's measure. It also shares one of After Burner's weaknesses: the 68000 calls the Master once per object and waits for each answer. This chapter follows one picture through the machine, then looks at which stage sets the rate, what the design gains and what it still wastes. The details of each technique are in the chapters it links to.

## How far the evidence goes

The code was read by disassembly from the retail dump, whose header checksum matches; what it does is certain [SWA]. Timings come from headless runs in PicoDrive and are tagged <span class="tag emulator">emulator</span>. All figures are for NTSC: 60 frames a second, 384,000 SH-2 clocks a frame. Three limits matter more here than for most games:

- **PicoDrive writes a fill's pixels at once**, but for a fill of more than 8 words it holds the fill's busy flag (FEN) for 3 + length 68000 cycles, about 9 + 3 × length SH-2 clocks. That is close to the manual's 7 + 3 × length, so the timing of fills against the CPU is roughly right. What PicoDrive lacks is bus contention, which on a console slows both SH-2s ([In emulators](../techniques/software-3d.md#in-emulators)) [PICODRIVE, memory.c].
- **The per-instruction profiler hangs the game in play.** It also switches PicoDrive's SH-2s from the recompiler to the interpreter. So there are three kinds of timing evidence: frame counts in play, profiles of two attract-mode scenes (an in-engine demo and the opening text crawl), and both SH-2s' program counters sampled once a frame in play. Every sample is taken at the same point of its frame, so the samples are a rough guide, not a profile.
- **The profiler counts only executed clocks.** PicoDrive puts a CPU to sleep while it polls a 32X register, between a quarter and a third of each SH-2's time here, so the shares below do not add up to 100%.

## How the game divides the work

| CPU | Job |
|-----|-----|
| 68000 | The game, one step per vblank. Draws the cockpit, score and timer on the Mega Drive VDP, in front of the 32X picture. Sequences the music, writing the PSG itself, with a small Z80 program writing FM registers and samples. Sends commands only to the Master: one call per object, then one to draw the picture, and only when the Master is idle |
| Master SH-2 | Geometry: answers the 68000's object calls, transforms the scene, picks a depth for each polygon, sorts by depth, and hands the Slave a list |
| Slave SH-2 | Pixels and PWM sound: clears the frame buffer, cuts each polygon into trapezoids and has the 32X VDP fill them, plays one compressed PWM voice from its PWM interrupt |

Sources: [SWA, SH-2 code at `0x06000E96`-`0x06000ECE`, `0x060007D0`-`0x060008DE`, `0x0600095C`-`0x06000AAE`, `0x0600129C`-`0x06001334`; 68000 code at `$086B40`-`$086C82`, `$086D78`-`$086E5C`]; [Audio across PWM, FM and PSG](audio.md); [Using both video chips at once](layering.md).

The two SH-2s form a pipeline: the Master builds picture *n* + 1 while the Slave draws picture *n*. Each SH-2 has one kind of work and its own code, and the only data that crosses between them is a finished list, once per picture ([A pipeline: geometry on the Master, pixels on the Slave](cpu-split.md#a-pipeline-geometry-on-the-master-pixels-on-the-slave)). The 68000 is a third stage, but it does not overlap with the Master: it sends a picture's objects only when the Master has finished the last one.

## One picture, from game logic to the screen

**1. The 68000 offers a new picture.** The 68000 runs one game step per vblank: a routine waits until the vblank interrupt has counted at least as many vblanks as a variable at `$FFFFDE46` says, and the game keeps that at 1 in the attract mode and in play. Each step, the 68000 reads a communication byte (`$A15122`) that the Master keeps non-zero while it is busy. If it is set, the step skips drawing; the game logic still runs [SWA, 68000 code at `$083026`, `$083156`, `$084900`-`$084916`, `$086B40`-`$086B56`, `$086D78`-`$086D7C`].

**2. The 68000 calls the Master once per object.** It sends two set-up commands, then one call per object. Each call is a command byte in a communication port plus the Master's command interrupt; the 68000 waits for the byte to be cleared, and if it is not cleared within 8,192 polls, raises the interrupt again ([The CMD interrupt](../32x/communication.md#the-cmd-interrupt)). An object call has a second half. The 68000 writes more parameters and a second byte, and waits while the Master, still inside its interrupt with everything masked, computes four values, writes them back and clears the byte. Then the 68000 sends the draw command [SWA, 68000 code at `$086A40`-`$086A48`, `$086B66`-`$086C82`, `$086D80`-`$086E58`; SH-2 code at `0x06001074`-`0x060010A2`, `0x0600129C`-`0x06001334`].

**3. The Master transforms.** Each point goes through a 16.16 matrix with `MAC.L`, four multiply-accumulates and an `XTRCT` per output coordinate ([Fixed point and the transform](../techniques/software-3d.md#fixed-point-and-the-transform)) [SWA, SH-2 code at `0x060028D0`-`0x06002932`].

**4. The Master sorts.** Each polygon chooses its depth with two flag bits: the average of its corners, its nearest corner or its farthest. It goes into one of 8,192 buckets, fine near the camera and coarser far away, and the Master walks the buckets far to near to build a flat list of pointers ([Bucket sorts](../techniques/software-3d.md#bucket-sorts)) [SWA, SH-2 code at `0x06003110`-`0x060031AC`, `0x06002796`].

**5. The hand-off.** The Master waits until the Slave has taken its last command, switches to the other of two sets of polygon records and lists, and writes command 12 into the Slave's command byte. Then it clears its busy byte and goes idle until the 68000's next draw command [SWA, SH-2 code at `0x06000E08`-`0x06000E24`, `0x06000E96`-`0x06000ECE`, `0x06001030`].

**6. The Slave purges and clears.** It purges its whole cache, so it cannot read stale list data, picks up any sound request, and starts clearing the frame buffer with fills ([Cache discipline](cache.md#sharing-between-the-two-sh-2s)) [SWA, SH-2 code at `0x060007D0`].

**7. The Slave cuts polygons into trapezoids.** A 2 KB routine copied into its on-chip RAM, with the cache in two-way mode, takes each polygon in list order, clips it by repeated halving, and writes trapezoids into a ring in SDRAM. Slopes come from a table of 32,768 ÷ *n*, so there is no division in the loop ([Two-way mode](../sh2/cache.md#two-way-mode-2-kb-of-on-chip-ram); [Clipping](../techniques/software-3d.md#clipping)) [SWA, on-chip code at `0xC0000000`-`0xC0000248`].

**8. A timer interrupt draws them.** The Slave's watchdog timer, in interval mode, raises an interrupt whose handler, also in on-chip RAM, plots the stars and then takes trapezoids off the ring line by line ([Star Wars Arcade: polygons as auto fills](../techniques/software-3d.md#star-wars-arcade-polygons-as-auto-fills); [The watchdog timer](../sh2/timers.md#the-watchdog-timer)) [SWA, on-chip code at `0xC0000582`-`0xC0000748`]:

- **Before each line it polls FEN** until the previous fill has ended.
- **A span of 6 pixels or fewer** it writes with byte stores. A wider one gets its odd end pixels from the CPU and the rest as an auto fill.
- **After a fill of 80 pixels or more** it saves its place and returns to the cutter, with the timer set to fire 512 clocks later. That is a fixed delay, long enough for the widest line the screen has: 160 words take 7 + 3 × 160 = 487 clocks by the manual's formula ([Auto fill](../32x/vdp.md#auto-fill)). It is not worked out for each fill.
- **After a shorter fill** it stays in the handler and goes on to the next line, so the poll before that line waits for the fill.

So the CPU does other work only during long fills. If the timer fires before a fill has ended, the handler's poll waits for it. If the fill ends first, which happens for every line narrower than the screen, the fill hardware sits idle until the timer fires: an 80-pixel fill (40 words) is done after about 127 clocks and then waits about 385. And the handler can itself be interrupted. Its level is 5, and the dispatcher does not raise the interrupt mask, so the PWM interrupt (level 6) can run in the middle of it, about 367 times a frame, and delay the next fill.

**9. The Slave flips.** Its main code waits, polling, until the ring is empty and the drawing interrupt idle. It stops the timer, polls FEN until the last fill ends, and toggles the frame buffer select bit. Then it polls that bit until it changes, which happens at the next vblank [SWA, SH-2 code at `0x06000B98`-`0x06000BC8`].

## Sound between the polygons

The Slave also plays PWM: one voice at about 22 kHz, decoded from a codebook format that stores each sample once and plays it twice. The PWM timer is set to interrupt after every sample (TM = 1), about 22,000 times a second or 367 a frame, and each interrupt decodes until the three-sample FIFO is full, normally one sample. Requests reach the Slave through the Master: the 68000 sends the Master a command, the Master leaves the sound's address and priority in shared memory, and the Slave looks once per picture, replacing the current sound only with one of equal or higher priority ([The PWM interrupt](../32x/pwm.md#1-the-pwm-interrupt-star-wars-arcade); [Audio across PWM, FM and PSG](audio.md)) [SWA, SH-2 code at `0x0600095C`-`0x06000AAE`]. Music stays on the Mega Drive's FM and PSG chips.

## Where the time goes

**The frame rate in play is not locked.** In two runs of a mission, the frame buffer flipped 1,084 times in 2,000 frames and 1,140 times in 1,999: 32.5 and 34.2 pictures a second. In the first run, pictures stayed up one frame 273 times, two frames 708 times, three frames 101 times and four frames once. In the second they stayed up one frame 346 times, two 728 times and three 65 times <span class="tag emulator">emulator</span> [SWA, FS bit read every frame in PicoDrive, 6 October 2026]. Most pictures last two frames, but a quarter to a third last one and 6-9% last three, so motion is uneven. On a console, where contention slows both SH-2s, more pictures would take three frames.

**What sets the rate.** A picture can start only at a 68000 step, once a vblank, and only if the Master is idle; once started, it goes through the 68000's object calls, the Master's geometry and the Slave's drawing, and appears at a vblank. The game has no lock: the 68000 runs a step every vblank in the attract mode, and 1,963 steps in 1,999 frames of play. So the rate is set by whichever SH-2 stage is slower, rounded up to whole frames, and the slower stage changes with the scene. Two attract-mode profiles show both cases <span class="tag emulator">emulator</span> [SWA, PicoDrive per-instruction profiles of frames 1300-1490 and 3800-3990 of the attract mode, 6 October 2026]:

| | In-engine demo, 30 a second | Text crawl, about 20 a second |
|---|---|---|
| 68000 | 78% waiting for vblank, 5% in command handshakes | 49% waiting for vblank, 14% in command handshakes |
| Master | 46% computing, 30% idle waiting for the 68000's next draw command | 49% computing, 19% waiting for the Slave to take its list, 6% idle |
| Slave | 24% waiting for the Master's command, 13% waiting for its drawing interrupt to empty the ring, 11% polling FEN inside the drawing interrupt, 11% waiting for the flip, 6% in the PWM interrupt, 5% cutting polygons | 31% cutting polygons, 20% in the drawing interrupt (5% of it polling FEN), 5% in the PWM interrupt, under 1% waiting for the Master |
| Slow stage | Master | Slave |

The text crawl draws its words as many small polygons, and the Slave's cutter cannot keep up, so pictures last three or four frames. In the demo, the Slave waits for the Master. The Master's work for a picture, the object calls plus the geometry, takes longer than the gap between two 68000 steps, so it is still busy at the next one, and the picture comes every second frame. In both scenes the 68000 has time to spare. It sets the rate only through the object calls, which make the Master wait for it.

**In play, the Master is the slower stage in most frames.** In the 1,999 frames of the second run, the Slave was waiting for the Master's command in 59% of the samples. The Master was idle waiting for the 68000 in 33%, inside an object call waiting for the 68000's second half in 16%, and busy otherwise <span class="tag emulator">emulator</span> [SWA, Master and Slave PCs sampled once a frame in PicoDrive, 6 October 2026]. Whether that holds in a busy battle, and on a console, is not known.

**The purge costs less than its ceiling.** The ceiling assumes the whole codebook would otherwise stay in the cache from one picture to the next, and the Slave's own reads make that unlikely. Right after the purge, the polygon cutter in on-chip RAM reads the Master's records through the cached SDRAM view, one record pointer at a time from the cached list [SWA, SH-2 code at `0x060008AC`-`0x060008CA`, on-chip code at `0xC000000A`-`0xC0000040`]. In a PicoDrive run of play that was a median of 258 records a picture, some 580 lines, about nine for each of the cache's 64 entries <span class="tag emulator">emulator</span> [SWA, lists read every frame in PicoDrive, 8 October 2026]. In two-way mode an entry keeps a codebook line only until two other lines arrive in it ([A stream read cached takes at most one way](cache.md#what-a-read-costs-through-each-view)). The codebook is read far less often. The decoder reads one entry per eight samples, and the PWM cycle of 1047 gives about 367 samples a frame (384,000 / 1046), so about 46 look-ups a frame [SWA, SH-2 code at `0x0600095C`, `0x060009CC`-`0x06000A0A`]. In a two-frame picture those look-ups touch only 27-45 of the codebook's 64 lines [SWA, sound data in the ROM]. A line not used again before two of the cutter's record lines arrive in its entry is lost before the next picture, purge or not. In the same run no PWM sound played once the flight began, and with no sound playing the codebook is not read at all <span class="tag emulator">emulator</span>. How many lines would really survive needs a cache-accurate emulator or a console ([Cache discipline](cache.md#open-questions)).

## What it does well

- **Long fills run while the CPU works.** For a span of 80 pixels or more, the drawing interrupt starts the fill and hands the CPU back to the polygon cutter until the timer fires. After Burner Complete's Master, in contrast, polls for every fill ([Case study: After Burner Complete](case-study-afterburner.md#what-it-leaves-on-the-table)). The overlap is partial: shorter spans are still polled, and polling took between 5% and 11% of the Slave's time in the two profiles.
- **The hot code is off the bus.** The polygon cutter and the drawing interrupt both run from the Slave's on-chip RAM, so the Slave's busiest work leaves the bus to the Master ([Living with bus contention](bus.md)).
- **Both SH-2s work on graphics.** The geometry and the pixels run side by side, on different pictures.
- **The rasteriser has no divide.** Slopes come from a table built once with the division unit; edges are clipped by halving.

## What it leaves on the table

- **The 68000 and the Master take turns.** The Master cannot start a picture's geometry until the 68000 has made every object call, and each call waits for the 68000's second half; in play the Master was found waiting inside a call in 16% of the samples. The 68000 also offers a new picture only once a vblank, so a Master that finishes just after a step sits idle for most of a frame: 30% of its time in the demo. After Burner Complete has the same per-object round trip ([The 68000 and the Master take turns](case-study-afterburner.md#what-it-leaves-on-the-table)).
- **Each SH-2 stage spins when the other is late.** The Master waits for the Slave in a delay loop, and the Slave waits for the Master's command, and which one waits depends on the scene. A pipeline balanced per picture needs work that can move between the stages, and this one has none ([Balancing per picture, not per task](cpu-split.md#balancing-per-picture-not-per-task)).
- **The frame rate is not locked.** Pictures last one, two or three frames as the scene varies. Holding the rate at 30 would turn the one-frame pictures into two-frame ones, at an average of 30 instead of 32.5 to 34. But it would not fix the 6-9% that already take three frames, nor the extra ones a console would add. A steady rate needs a lock at 20, or pictures that always fit in two ([Why the rate is 60, 30, 20 or 15](60fps.md#why-the-rate-is-60-30-20-or-15)).
- **Short fills are polled, and long ones get a fixed wait.** Spans under 80 pixels make the drawing interrupt spin on FEN. Long spans get 512 clocks whatever their length, so the fill hardware idles after any span narrower than the screen.
- **The PWM interrupt costs about 7% of the Slave, for one voice.** Each interrupt runs about 70 instructions, counting the dispatcher, and PicoDrive charges about 75 clocks for them. At 367 interrupts a frame that is about 28,000 clocks, roughly 7% of a frame. On a console it costs more, because each interrupt makes five accesses to 32X registers: two FIFO status reads, a sample write, the interrupt clear and its read-back. After Burner Complete mixes 16 voices on its Slave.
- **The Slave purges its whole cache before every picture.** Throwing away its whole cache to see the new list also throws away the sound codebook, which comes back from the cartridge line by line. That costs at most about 9,500 clocks a picture. That is 2.5% of the Slave's time in the worst case, one purge per display refresh (9,500 of 384,000 clocks), and at worst a third of the PWM interrupt's cost. At the 32.5-34.2 pictures a second measured in play it is about 1.3-1.4% ([Sharing between the two SH-2s](cache.md#sharing-between-the-two-sh-2s)). The ceiling is likely generous ([Where the time goes](#where-the-time-goes)).

## Built to survive, mostly

- **A lost command interrupt is retried** by the 68000 after 8,192 polls [SWA, 68000 code at `$086B72`-`$086B9C`].
- **RV is read correctly, but the reset it guards may never fire.** The VRES handlers read RV from the right byte, unlike After Burner Complete's and Mortal Kombat II's ([discrepancy 33](../appendices/discrepancies.md)). But the handler's reset comes from a timer output that needs a compare value the game never sets, so by Hitachi's rules it never fires ([FTOB and the VRES reset](../sh2/timers.md#ftob-and-the-vres-reset); [discrepancy 22](../appendices/discrepancies.md)). The game never sets RV, so this does not matter in practice.
- **It copies Sega's sample slip.** Its VRES handler writes the DMA control value to the wrong register, as Sega's sample did; Rutubo's After Burner Complete writes it correctly ([Handlers in practice](../sh2/intc.md#handlers-in-practice); [Sega's sample code in the games](../appendices/sample-code.md)).

## What the design teaches

- **Split by stage, then find out which stage is slow.** Geometry on one CPU and pixels on the other, a picture apart, with one list crossing between them, is the cleanest division in the sources. But the slow stage moves with the scene: here it is the Slave in the text crawl and the Master in the demo and, by sampling, in play. Measure the heaviest scenes, and plan for the stage that is slow there.
- **Don't make the geometry CPU wait for the 68000 per object.** Writing each picture's objects into a list in shared memory would let the Master start at once, instead of taking a turn for each object.
- **Use a timer, not a poll, for long hardware waits.** By construction, the CPU does useful work during a long fill instead of polling FEN. How much that saves on a console has not been measured. The wait is also better sized to the job: one sized for the longest fill leaves the hardware idle after shorter ones.
- **Put the inner loop in on-chip RAM.** Two-way cache mode gives 2 KB that never misses and never touches the bus.
- **Lock the frame rate only at a rate the pictures fit.** An unlocked pipeline shows its imbalance as uneven motion. A lock at 30 smooths the fast pictures but not the slow ones.

## Open questions

- What frame rate does it hold in a busy battle on a console, and is the Master or the Slave the slower stage there?
- How much does the timer-paced fill save on a console compared with polling, once contention is real ([Software 3D](../techniques/software-3d.md#open-questions))?
- Why does profiling hang the game in PicoDrive during play? The profiler also turns off PicoDrive's SH-2 recompiler, so the interpreter may be the cause.
- What do the four values the Master returns for each object mean, and which 68000 code path sets the vblank minimum at `$FFFFDE46` to 2?

## Sources

- [SWA](../appendices/bibliography.md#swa):
  - SH-2 code at `0x06000E08`-`0x06000ECE`, `0x06001030`, `0x06001074`-`0x060010A2`, `0x0600129C`-`0x06001334`, `0x060007D0`-`0x060008DE`, `0x0600095C`-`0x06000AAE`, `0x06000B98`-`0x06000BC8`, `0x060028D0`-`0x06002932`, `0x06003110`-`0x060031AC`, `0x06002796`.
  - On-chip code at `0xC0000000`-`0xC0000748`.
  - 68000 code at `$083026`, `$083156`, `$084900`-`$084916`, `$086A40`-`$086C82`, `$086D78`-`$086E5C`.
  - PicoDrive frame counts in play; attract-mode profiles; per-frame PC samples in play; polygon lists read every frame in play (8 October 2026).
  - Sound data in the ROM: codebooks and index streams.
- [PICODRIVE](../appendices/bibliography.md#picodrive): memory.c, fill timing.
- The chapters linked above, which cite each technique in detail.
