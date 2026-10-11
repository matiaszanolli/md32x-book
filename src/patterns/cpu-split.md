# Splitting work across three CPUs

A 32X game has four processors: the Mega Drive's 68000 and Z80, and two SH-2s, the Master and the Slave. The Z80 stays the Mega Drive's sound processor and reaches everything else through the 68000's bus ([Living with bus contention](bus.md#the-mega-drive-side)), so the work worth dividing is shared by the other three. Nothing in the hardware says which one does what. This chapter looks at how commercial games, homebrew and the author's own projects divide the work, how to find the processor that is sitting idle, when moving a job is worth its cost, how to keep two SH-2s evenly loaded, and how to hand work across without the handing over eating the gain. The mechanisms the processors use to talk are in [68000 and SH-2 communication](../32x/communication.md). This chapter is about what to send through them.

Clock counts are in the clocks of the CPU that spends them: unmarked figures are SH-2 clocks, and 68000 clocks are marked as such.

## What each processor is for

| | 68000 | Each SH-2 |
|---|---|---|
| Clock (NTSC) | 7.67 MHz, about 128,000 clocks per frame | 23.01 MHz, about 384,000 clocks per frame |
| Reaches | Mega Drive VDP, sound chips, pads, save RAM, work RAM, cartridge | SDRAM, 32X VDP and frame buffer, PWM, cartridge |
| Good at | Driving Mega Drive hardware; 16-bit game logic | 32-bit arithmetic, multiply-accumulate, moving pixels |
| Costs it imposes | Cartridge reads compete with both SH-2s [32X-HWM §4.1 p.74] | Every Slave bus access needs the Master's permission ([Bus controller](../sh2/bsc.md#two-sh-2s-one-bus)) |

The frame counts assume an NTSC frame of 1/59.92 s ([System architecture](../megadrive/architecture.md)).

Two facts shape every split. Only the 68000 can touch the Mega Drive side: the pads, the Mega Drive VDP, the Z80 and the FM chip. And the two SH-2s are not two independent computers. They share one external bus, so two SH-2s working out of SDRAM or the frame buffer at the same time slow each other down, while two working from their caches do not ([Where the time goes](../sh2/overview.md#where-the-time-goes)).

## How existing programs divide the work

| Program | Kind | 68000 | Master | Slave |
|---------|------|-------|--------|-------|
| Star Wars Arcade | Retail (Sega InterActive) | Game logic, Mega Drive cockpit and HUD | Geometry: builds a depth-sorted polygon list | Draws the polygons; PWM sound |
| Mortal Kombat II | Retail (Probe) | Game logic, arena and HUD on the Mega Drive | Draws everything on the 32X layer | PWM sound only |
| After Burner Complete | Retail (Rutubo Games, for Sega) | Game logic, player's jet and HUD on the Mega Drive; calls the Master once per object | Projects each object inside its CMD interrupt, sorts, draws everything on the 32X layer | Music sequencer and 16-voice PWM mixer |
| Knuckles' Chaotix | Retail (Sega) | Mega Drive planes, most of the picture. Where the game logic runs has not been traced | Draws the 32X layer | PWM sound from on-chip RAM, and each picture's clear, on the Master's request |
| Motocross Championship | Retail (Artech Studios, for Sega) | Paces the pictures and handles I/O; PWM sound, fed from its line interrupt. Where the game logic runs has not been traced | Everything on the 32X layer | Idle |
| Virtua Racing Deluxe <span class="tag disputed">disputed</span> ([row 28](../appendices/discrepancies.md)) | The VRD project's account of a retail game | Physics, AI, collision, camera, depth sorting | Command dispatch, block copies, run-length decompression | The 3D renderer: the Slave runs the fill routine in the clean retail ROM <span class="tag emulator">emulator</span> |
| d32xr (Doom) | Homebrew | Server: music, save RAM, CD, Mega Drive VDP, ROM bank changes | Game logic, then a share of every render stage | A share of every render stage; sound mixing in builds with DMA sound |
| marsdev skeleton | Homebrew example | Server: pads and Mega Drive VRAM writes, on request | Runs the program | Idle |
| Aerobiz Ultimate | The author's project, in progress | The whole original game | On request: decompression, the Sega logo, title art and the New Game menus | Idle |

Sources: [SWA, SH-2 code at `0x06000734`-`0x060008EC`, `0x06000E08`-`0x06000ECE`, `0x06002570`, `0x06002796`]; [MK2, SH-2 program]; [AB32X, SH-2 program; 68000 code at `$887348`]; [CHAOTIX, SH-2 code at `0x06000284`]; [MCX, profile; 68000 code at `$00081A`]; [VRD-NOTES, analysis/RENDERING_PIPELINE.md §3-§6]; [D32XR, marsnew.c, mars.h, r_main.c, src-md/crt0.s, Makefile]; [MARSDEV, examples/32x-skeleton]; [AU-NOTES, ROADMAP.md, HISTORY.md]. The developer in the Kind column is the one each cartridge's own credits name ([Sega's sample code in the games](../appendices/sample-code.md#the-games-read-in-full)).

The rows carry different weight. The retail games are read from clean dumps: their splits ran on consoles. d32xr's commit history records fixes made after running it on consoles [D32XR, commit history], while marsdev's skeleton is a starting point, not a game. The Aerobiz Ultimate project has not run on a 32X yet, so its measurements below are tagged <span class="tag emulator">emulator</span>.

The Virtua Racing Deluxe (VRD) project's documents disagree with each other about which SH-2 runs the 3D: its rendering pipeline notes and status page give it to the Slave, its communication and SH-2 analysis notes to the Master. Its ROM copy is also patched ([VRD-NOTES](../appendices/bibliography.md#vrd-notes)), so the row above is the project's account. One part is checked against the clean retail ROM: the span-fill routine, which drives the auto fill, runs on the Slave and does not appear in the Master's profile <span class="tag emulator">emulator</span> [32X-ROMSET, Virtua Racing Deluxe (USA); SH-2 code at `0x06003BF8`-`0x06003C5E`, Slave on-chip copy at `0xC0000188`]. Which CPU transforms the scene is still open ([discrepancy 28](../appendices/discrepancies.md)). Read directly, the project's patched ROM copy looks more like a Star Wars Arcade pipeline than a Slave-only renderer; see [Software 3D](../techniques/software-3d.md#open-questions).

### A pipeline: geometry on the Master, pixels on the Slave

Star Wars Arcade splits the 3D work by stage. The 68000 sends commands to the Master through the CMD interrupt: once a vblank, if the Master is idle, one call per object and then a draw command [SWA, 68000 code at `$086B40`, `$086D78`-`$086E5C`]. On the draw command, the Master transforms the scene and writes a polygon record for each visible face. It links them into an 8,192-entry table of depth buckets, then walks the buckets to produce a flat list of pointers in drawing order [SWA, SH-2 code at `0x06002570`, `0x06002796`].

There are two sets of records and lists (`0x06018690`/`0x06024BB8` and `0x060310E0`/`0x060326C8`), chosen by bit 0 of a word in shared SDRAM (`0x0600764A`). When a list is complete, the Master [SWA, SH-2 code at `0x06000E96`-`0x06000ECE`, `0x06001030`]:

1. waits until the Slave's command byte (`$A15123`) reads 0, running a delay loop of 1,100 passes between checks;
2. flips the bit, so the next picture's geometry goes into the other set;
3. writes 12 into the Slave's command byte.

The Slave's command 12 [SWA, SH-2 code at `0x0600074A`, `0x060007D0`-`0x060008DE`]:

1. purges its whole cache, so it cannot see stale list data;
2. starts any sound sample the Master has left for it in shared SDRAM;
3. starts clearing the frame buffer in the background, and runs the 2 KB routine it keeps in its on-chip RAM (see [Cache](../sh2/cache.md#two-way-mode-2-kb-of-on-chip-ram)) once for each pointer in the list the Master just finished. That routine cuts each polygon into trapezoids, and a timer interrupt draws them with the VDP's auto fill while it works ([Software 3D](../techniques/software-3d.md#star-wars-arcade-polygons-as-auto-fills));
4. swaps the frame buffers. The Slave's command loop then writes 0 to its command byte.

Meanwhile the Master is already building the next picture's list in the other set.

This is the cleanest split in the sources. Each SH-2 has one kind of work and its own code, the hand-off is one byte, and the only data that crosses is a list written by one CPU and read by the other a picture later, plus the occasional sound request. The costs are one picture of extra delay between the game deciding and the result showing, and a frame rate set by whichever stage is slower. If geometry took 200,000 clocks and drawing 350,000, the Master would spend the difference, 150,000 clocks a picture, in its delay loop waiting for the Slave's command byte.

### One SH-2 draws, the other plays sound

Mortal Kombat II gives the Master all the drawing and the Slave nothing but sound. The 68000 sends the Master a 668-byte snapshot of the game each frame through the ports and sends sound requests to the Slave through `$A1512E`. The two SH-2s share no SDRAM, and apart from one word the Slave writes to a port at start-up they exchange nothing, so there is no cache to keep coherent and nothing to lock ([Between the two SH-2s](../32x/communication.md#between-the-two-sh-2s)) [MK2, SH-2 program; SH-2 code at `0x0600029C`, `0x06005136`]. It is the simplest arrangement that works, and the one most likely to be correct first time.

The price is the Slave's time. Its sound work is a PWM interrupt that unpacks and mixes up to two voices ([PWM sound](../32x/pwm.md)). The rest of the time its main loop polls a port, using bus cycles the Master could use. A 2D fighting game can afford that. A 3D game cannot.

After Burner Complete, published by Sega and programmed by Rutubo Games, makes the same split and gives the Slave a whole sound system to run: a music sequencer and 16 voices mixed with pitch, interpolation and stereo panning. The mixing happens in the Slave's main loop, which keeps a 64-entry ring of samples topped up, up to 64 samples (about 4 ms) ahead of the PWM interrupt; the interrupt only copies one sample out ([PWM sound](../32x/pwm.md#1-the-pwm-interrupt-star-wars-arcade)). Its Slave never polls the communication ports, because its commands arrive by CMD interrupt. When the ring is full it spins on the ring's own indexes, which live in on-chip registers and cost no bus cycles; in one PicoDrive run that was about half its time <span class="tag emulator">emulator</span>. The Master's drawing never waits for sound, and the two SH-2s share no SDRAM [AB32X, SH-2 program; SH-2 code at `0x060003C0`-`0x0600046E`, `0x06000820`; headless runs].

The homebrew skill puts the case for a sound-only Slave: if the Slave also draws without coordination, a long drawing job can starve the PWM FIFO, and a Master that overruns its frame can never interrupt the sound [S32X-SKILL, architecture.md, optimization.md] <span class="tag emulator">emulator</span>. Star Wars Arcade and d32xr avoid that problem differently: they keep the sound in an interrupt on the Slave, which preempts whatever drawing it is doing. Star Wars Arcade uses the PWM interrupt [SWA, SH-2 code at `0x0600095C` (set-up), `0x06000980` (interrupt)]. d32xr uses the end-of-transfer interrupt of DMA channel 1: it restarts the transfer on the 316 stereo samples just mixed, at 22,050 Hz, and mixes the next 316 into the other half of a pair of buffers. That path is only in builds made with DMA sound enabled, as its cartridge builds are; a plain build leaves it out [D32XR, marsnew.c, marssound.c, Makefile; [DMA (d32xr)](../32x/pwm.md#2-dma-d32xr)].

### Both SH-2s on every stage

d32xr splits Doom's renderer so that both SH-2s work on most stages [D32XR, r_main.c `R_RenderPlayerView`; marsnew.c `Mars_Secondary`; r_phase1.c, r_phase2.c, r_phase7.c, r_phase9.c]:

| Stage | Master | Slave |
|-------|--------|-------|
| Walk the BSP tree, find visible walls | Walks it, starts each wall's preparation | Finishes preparing each wall as the Master finds it |
| Draw walls | Shared, wall by wall | Shared |
| Sort floors and ceilings | Whichever CPU gets there first | |
| Draw floors and ceilings | Shared, plane by plane | Shared |
| Draw sprites | Left part of the screen | Right part |
| Update the texture cache | Yes, at the end of each picture | |

The Slave runs a loop that waits for a job number in `$A15124`, runs the job, and writes 0 back. A picture needs three: "wall prep" carries on from the tree walk through wall drawing and the floor sort by itself, and floors and sprites each get a job of their own. Game logic runs on the Master; the Slave has no game-logic job. It shares a few batch jobs with the Master instead: line-of-sight checks for the monsters about to act, drawing the automap, and the screen-melt wipe. It also animates the title screen's fire [D32XR, marsnew.c, p_sight.c, am_main.c, f_wipe.c, m_fire.c].

This keeps both SH-2s busy, at the price of the hardest code in the sources: shared work lists, per-CPU state, and careful cache handling. The techniques it uses are below.

### The 68000 as a server

When an SH-2 runs the game, the 68000 is left to do what only it can, on request. d32xr's 68000 answers requests for music, sound effects, save RAM, CD access, Mega Drive VDP copies, cartridge bank changes and link-cable networking ([Who asks whom](../32x/communication.md#who-asks-whom)) [D32XR, src-md/crt0.s]. marsdev's skeleton reads the pads and writes Mega Drive VRAM when the Master asks. It also publishes a frame counter that it advances each time it sees vertical blank in the VDP status, and the Master paces its pictures by it [MARSDEV, examples/32x-skeleton/md_src/md_main.c, sh_src/m_main.c].

The skeleton runs its main loop and every routine it calls each frame from work RAM, not from the cartridge; its comments call this recommended, not required, and one colour table it reads each frame stays in ROM [MARSDEV, examples/32x-skeleton/md_src/md_main.c, md_src/md_start.s]. A 68000 running from ROM takes cartridge cycles away from the SH-2s, which win when both ask at once but still wait for an access already in progress [32X-HWM §4.1 p.74]. A server 68000 that spends most of its time polling should poll from work RAM.

## Finding the idle processor

**Measure before moving anything.** The Aerobiz Ultimate project planned to move the game's AI and economy to an SH-2. A profile of a full 20-year demo game then showed the 68000 idle 69.5% of the time (a figure the project calls biased high, because every sample falls at the same point of the frame), with no AI or economy routine among the 25 most expensive. The real cost was graphics and decompression, 20.4% of frames, more than half of it in one LZ decompressor. Before that profile, the port had already moved the slow path of the game's 32-bit divide to the SH-2 and proved it bit-exact over 12,000 frames. Its call counter then read 0 after 200,000 frames: the game never divides by a number that large <span class="tag emulator">emulator</span> [AU-NOTES, ROADMAP.md U-044, U-045].

The decompressor was worth moving. It cost the 68000 285 of its clocks per output byte, so the largest block took 62 frames and caused a 74-76 frame stall at each quarter of a game year. On the Master the decoding alone runs 14 times faster; counting the two copies of the result, about 8 times, and the game-level measurement leaves 8 to 10 frames of each stall ([Moving decompression to an SH-2](../techniques/compression.md#moving-decompression-to-an-sh-2)). The game's frame rate does not change, because it was never short of 68000 time during play <span class="tag emulator">emulator</span> [AU-NOTES, ROADMAP.md U-046].

**Look for waiting loops.** In the retail games, idle time hides in loops that wait:

- Mortal Kombat II's Master clears the frame buffer with 161 auto fills and waits for each to finish. By the manual's formula (7 + 3 × 256 clocks each) that is about 125,000 clocks a frame spent polling FEN, a third of the Master's 384,000 [MK2, SH-2 code at `0x060010DC`; 32X-HWM §3.3, FILL function]. Its Slave spends most of its time polling a port.
- Star Wars Arcade's Master waits for the Slave between pictures, and its Slave waits for the Master. Each side's wait is time the pipeline is unbalanced, and which side waits depends on the scene: in the opening text crawl the Master waits for the Slave about a fifth of its time, in the in-engine demo the Slave waits for the Master about a quarter of its time. In PicoDrive, during play in the first stage, the game flips its frame buffer 1,084 times in 2,000 frames: most often every second frame, sometimes every frame or every third, 32.5 pictures a second. Its rate is not locked; each picture is shown as soon as it is finished <span class="tag emulator">emulator</span> [SWA, headless run with FS read from `$A1518A` every frame, 6 October 2026; attract-mode profiles] ([Case study: Star Wars Arcade](case-study-starwars.md#where-the-time-goes)).
- After Burner Complete's Master draws its sky and sea with auto fills, waiting for each to finish before starting the next. Every one of the 224 lines gets 160 words: two fills split at the horizon, or one 160-word fill when the horizon misses that line. By the manual's formula that is 224 × (2 × 7 + 3 × 160) ≈ 110,700 clocks per picture with two fills on every line (448 fills), and 224 × (7 + 3 × 160) ≈ 109,100 with one, so about 110,000 whatever the bank angle. The game draws 30 pictures a second, so the Master has two NTSC frames, about 768,000 clocks, for each, and the fills take a seventh of that [AB32X, SH-2 code at `0x06008280`-`0x060082F6`; 32X-HWM §3.3, FILL function]. PicoDrive measures more. Over 2,000 frames of the first stage, started from a saved state so the title screen is left out, the Master drew 951 pictures and spent 202 million clocks in that routine: about 212,700 per picture, 1.9 times the formula, or about 950 clocks a line against the formula's 490 <span class="tag emulator">emulator</span> [AB32X, headless run, 6 October 2026].

The earlier profiles' shares, 44% and 36%, disagree for a reason that has nothing to do with the game. A profile's share is a share of the clocks the SH-2 actually executed, and PicoDrive does not execute a CPU that it has caught in a polling loop: it puts it to sleep until something changes. In this run the Master executed only 70% of the run's clocks, so the routine's 26% of the Master's time shows up as 37% of its profile. The share therefore depends on how much the Master slept, and on how much of the run was title screen, which clears the frame buffer with a different routine [AB32X, SH-2 code at `0x0600D0C8`]. Compare clocks per picture, not shares.

PicoDrive's own fill model does not explain the factor of 1.9. It keeps FEN busy for 3 + *n* 68000 clocks for a fill of *n* + 1 words, about 9 + 3*n* SH-2 clocks, which matches the manual's formula, and it wakes a sleeping SH-2 when the fill ends [PICODRIVE, pico/32x/memory.c, pico/32x/32x.c]. The extra time is in how the emulator runs the Master around each fill. A copy of PicoDrive that logs the time each CPU spends asleep shows where. In a later run, built from the current PicoDrive source, the Master also sleeps in the fill poll, and each sleep lasts 700 to 850 clocks on average, longer than any fill the routine starts. So PicoDrive wakes it late, and counting polling and sleep, the waits come to about three times the formula <span class="tag emulator">emulator</span> [AB32X, PicoDrive profile and sleep log, 6 October 2026] ([Case study: After Burner Complete](case-study-afterburner.md#where-the-time-goes)). The console's figure should be nearer the formula.

A count of how often each wait loop runs, kept in SDRAM and read after a play session, is cheap and tells you how much time each CPU has to spare. See [Profiling](../howto/profiling.md).

**Work that suits an SH-2** is batch work on data the SH-2 can reach: decompression from cartridge ROM, transforms, filling and clearing the frame buffer, mixing sound. Work that needs Mega Drive hardware, or is many small calls from 68000 code, does not suit it.

## When moving a job pays

A job sent from the 68000 to an SH-2 and back pays only if it saves more than the round trip costs. The Aerobiz Ultimate project measured the round trip by running a divide 20,000 times each way and timing how long each took. In place, the 68000 managed about 137 slow divides a frame or 443 fast ones, which at 128,000 68000 clocks a frame is about 940 and 290 clocks each. Sent to the SH-2, both ran at the same 228 calls a frame, about 560 68000 clocks a call: the SH-2's work never showed, and the round trip was the whole cost. So the slow divide ran 1.67× faster on the SH-2 and the fast one 1.94× slower <span class="tag emulator">emulator</span> [AU-NOTES, ROADMAP.md U-039]. PicoDrive spots the SH-2's polling loop and may answer sooner than a console would, so the project treats 228 calls a frame as an upper bound: on a console the round trip is probably longer.

After Burner Complete makes a call per object anyway, about 75 per picture (up to 87), because each call carries enough work and returns something the 68000 needs. The Master projects the object, with a 16-step divide and several multiplies, and answers whether it is on screen, which the 68000's game logic uses at once. The cost is still visible: in PicoDrive the 68000 spends about 12% of its time waiting for those answers <span class="tag emulator">emulator</span> [AB32X, 68000 code at `$8873A8`; SH-2 code at `0x0600257C`]. See [One call per object](../32x/communication.md#one-call-per-object).

The VRD project found the same limit in its own code. It moved a routine called 8 times a frame, costing about 1,500 68000 clocks a frame in all, to the Master, and the 68000 then spent 23% of its time over the profiled run waiting on the ports <span class="tag emulator">emulator</span> [VRD-NOTES, KNOWN_ISSUES.md]. That is far more than the Aerobiz Ultimate project's 560 68000 clocks a call would predict, and the notes say why: almost all of the wait was for the Master to finish earlier commands (copies the 68000 had already queued) before it would take the new one; waiting for the routine's own answer took 0.7%. So it measures a busy Master, not the handshake. The project moved the routine back to the 68000. The project's optimisation plan adds that the routine runs about 8 times a frame "during race mode", and estimates a round trip at 200 to 500 68000 clocks [VRD-NOTES, OPTIMIZATION_PLAN.md, COMM offload cost model]. The totals imply a profiled run of about 300 million 68000 clocks, some 39 seconds. Neither document says which scenes it covered, or whether "frame" means a 60 Hz frame or one of the game's own pictures, which last longer. The hotspot list committed with the lesson has no entry for the offload's wait loop, so it comes from a different run [VRD-NOTES, tools/libretro-profiling/68k_hotspots.txt at commit `7b1dd75`].

So **send batches, not calls.** The Aerobiz Ultimate project's decompressor still takes one block per call, but its design notes conclude that it should take a list of blocks, for three reasons, strongest first [AU-NOTES, ROADMAP.md U-046]:

1. Handing the frame buffer between the 68000 and an SH-2 with FM makes both wait; one hand-over per batch is cheaper than one per job.
2. Frame-buffer writes are cheaper in unbroken runs.
3. The round trip is paid once.

The first and third stand. The second does not follow from the manual: 5 clocks a word is the price of an *unbroken* run once the write buffer is full, 3 clocks needs room in the buffer, and only a pause makes room, which by the manual gives back at most what it costs ([Living with bus contention](bus.md#moving-data-without-paying-twice)) [32X-HWM §3.1 p.16; §4.4 p.77]. The batching is still on the project's list of open work.

Keep the 68000 version of every routine you move, selectable when building, so the two can be compared for identical results, and fall back to it when the SH-2 does not answer in time ([Never wait forever](../32x/communication.md#never-wait-forever)). That is the Aerobiz Ultimate project's rule. Its decompressor has the build switch and the fallback; its divide has only the fallback [AU-NOTES, PORT_ARCHITECTURE.md, ROADMAP.md].

## Balancing per picture, not per task

A split by role or by stage is fixed: the same CPU always gets the same work. Each picture then takes as long as the busiest CPU's share. It balances only if the shares happen to be equal, and in a game they change with every scene.

d32xr instead lets both SH-2s take work from the same list as they become free. Three details make that balance well [D32XR, r_phase1.c, r_phase7.c, r_phase8.c]:

- **Cut big jobs up.** A wall at least a quarter of the view wide (80 columns at 320 pixels) is stored as pieces of that width, so one long wall cannot leave a CPU working alone at the end. Splitting stops once 1.5 view widths of unsplit wall (480 columns at 320) have been stored, and a separate check stops the list at its 165 entries.
- **Largest first.** Floor and ceiling areas are sorted widest first, in steps of 16 columns. Each CPU takes the next one when it finishes the last, so the small jobs at the end fill the gaps. Within a step the sort key groups areas by texture, so a CPU that takes several in a row finds its 4 KB texture already in its cache; the code's comment gives that as the reason.
- **Split by pixels, not by objects.** For sprites, d32xr computes the average screen column of everything to be drawn, weighting each sprite (and each see-through wall, and the player's weapon) by its width in pixels. The Master draws left of that column and the Slave right of it. Ten small sprites and one large one then split by drawing work, not by count. If the result is 0 or off screen it uses the middle.

A pipeline like Star Wars Arcade's can be rebalanced by moving work across the stage boundary, for example by letting the drawing CPU do the last step of the geometry. That is a design decision, not something the code does for each picture.

## Handing work across without waiting

The ports and their rules are in [68000 and SH-2 communication](../32x/communication.md). The patterns that keep the processors working rather than waiting for each other:

- **Double-buffer whatever crosses.** Star Wars Arcade's two sets of polygon lists let the Master write the list for picture *n* + 1 while the Slave reads the one for picture *n*. The only wait is at the flip.
- **Hand over progress, not completion.** While d32xr's Master walks the BSP tree, it adds 1 to a byte in `$A15126` for each wall piece it stores. The Slave prepares walls up to that count as they appear, and adds 1 to the other byte, `$A15127`, for each one it finishes. A value of −2 says the tree walk is done. Each byte has one writer and only ever goes up, so neither side needs a lock, and the two stages overlap instead of running one after the other [D32XR, mars.h, r_phase1.c, r_phase2.c].
- **Claim jobs, and keep private copies of shared results.** When both d32xr CPUs draw walls, each one claims a wall by setting a "drawn" flag under a lock, so each is drawn once. The lock is a test-and-set that the compiler turns into `tas.b`. Both CPUs then apply the wall's effect on the screen's clipping to their own private copy, whether or not they drew it, until one of them reports that the walls are all done. The clipping state never has to be shared [D32XR, r_phase6.c, Makefile]. The manual forbids TAS on the 32X <span class="tag disputed">disputed</span> ([discrepancy 12](../appendices/discrepancies.md)).
- **Give each CPU its own state through GBR.** The same drawing code runs on both d32xr SH-2s. Each CPU points GBR at its own small block of pointers to its frame buffer, colour map, column cache and "already checked" marks, plus its cartridge bank state, and reads it with GBR-relative loads, which avoids a test of which CPU is running. Star Wars Arcade does the opposite: both CPUs point GBR at the same block of shared variables at `0x060075E4` [D32XR, doomdef.h, marsnew.c; SWA, SH-2 code at `0x060008F0`, `0x06000EE4`].
- **Purge on the reading side.** Data written by one SH-2 is in SDRAM (the cache writes through), but the other's cache may hold an old copy. Star Wars Arcade's Slave purges its whole cache once per picture, before reading each list. d32xr purges just the lines it needs before reading something the other CPU wrote, and the whole cache at the start of some of the Slave's jobs ([Cache](../sh2/cache.md#keeping-the-views-in-step)) [D32XR, r_main.c, r_phase7.c, marsnew.c].
- **Share nothing** where possible, as Mortal Kombat II and After Burner Complete do. Every shared variable needs purges or a lock; data that stays on one CPU needs neither.
- **Wait with a limit.** A Master that waits forever for a dead Slave hangs the game. A limited wait only makes one picture late [S32X-SKILL, architecture.md]. d32xr's waits between the SH-2s have no limit, apart from one sound wait in its DMA-sound builds [D32XR, mars.h, marssound.c].

## In emulators

Neither PicoDrive nor Ares makes one SH-2 wait for the other's bus accesses, and PicoDrive has no cache ([In emulators](../sh2/overview.md#in-emulators)). So a split that looks balanced in an emulator can be unbalanced on a console, where two SH-2s working out of SDRAM slow each other down. PicoDrive also cuts polling loops short, both a 68000 polling a communication port and SH-2 loops its recompiler recognises, which makes waits and round trips look cheaper than they are; Ares runs them for real ([Two emulators, two jobs](../howto/emulator-testing.md#two-emulators-two-jobs); [Profiling](../howto/profiling.md)). Measure a split's balance on a console where you can, and treat emulator timings as a lower bound.

## What to take away

- Profile first. The obvious candidate for moving may never run.
- Move batch work with plenty of computation per item. A single call is only worth sending if it saves more than the round trip: about 560 68000 clocks in PicoDrive, and likely more on a console. Add the time the SH-2 may spend finishing earlier work first.
- Splitting by role is simple and safe; splitting by stage adds one picture of delay and balances only by luck; sharing a work list balances best and is the hardest to get right.
- Keep sound in an SH-2 interrupt, so the drawing work cannot starve it.
- Double-buffer data that crosses between CPUs, give every shared variable a single writer, and purge before reading what the other CPU wrote.

## Open questions

- How much do the two SH-2s slow each other on a console when both work out of SDRAM, for example in d32xr's shared wall drawing?
- How long is the 68000 → SH-2 → 68000 round trip on a console, without PicoDrive's shortcut for polling loops?
- Which stage of Star Wars Arcade's pipeline is slower in a busy battle, and on a console? PicoDrive's per-instruction profiler makes the game hang during play. Program counters sampled once a frame in play point to the Master ([Case study: Star Wars Arcade](case-study-starwars.md#where-the-time-goes)), but the split was not measured.
- What does After Burner Complete's sky and sea routine take on a console? PicoDrive charges two to three times the formula, mostly because it wakes the polling Master late.
- In the VRD project's offload test, which scenes were profiled, and is its "8 times a frame" per 60 Hz frame or per picture? The profile itself was not kept.

## Sources

- [32X-HWM](../appendices/bibliography.md#32x-hwm): §3.1 p.16 frame buffer write FIFO; §3.3 FILL function; §4.1 p.74 ROM access competition; §4.4 p.77 (checked on the scan)
- [SWA](../appendices/bibliography.md#swa): SH-2 code at `0x06000734`-`0x060008EC`, `0x0600095C`, `0x06000980`, `0x06000E08`-`0x06000ECE`, `0x06001030`, `0x06002570`, `0x06002796`; headless run in play, FS read every frame
- [MK2](../appendices/bibliography.md#mk2): SH-2 program, code at `0x0600029C`, `0x060010DC`, `0x06005136`
- [AB32X](../appendices/bibliography.md#ab32x): SH-2 program, code at `0x060003C0`-`0x0600046E`, `0x0600257C`, `0x06008280`, `0x0600D0C8`; 68000 code at `$887348`-`$8873BC`; headless runs, including a 2,000-frame profile of play from a saved state
- [D32XR](../appendices/bibliography.md#d32xr): marsnew.c, mars.h, r_main.c, r_phase1.c, r_phase2.c, r_phase6.c, r_phase7.c, r_phase8.c, r_phase9.c, p_sight.c, am_main.c, f_wipe.c, m_fire.c, doomdef.h, marshw.c, marssound.c, Makefile, src-md/crt0.s; commit history
- [MARSDEV](../appendices/bibliography.md#marsdev): examples/32x-skeleton (md_src/md_main.c, md_src/md_start.s, sh_src/m_main.c)
- [AU-NOTES](../appendices/bibliography.md#au-notes): PORT_ARCHITECTURE.md; ROADMAP.md U-039, U-044, U-045, U-046; HISTORY.md
- [VRD-NOTES](../appendices/bibliography.md#vrd-notes): analysis/RENDERING_PIPELINE.md §3-§6, KNOWN_ISSUES.md, OPTIMIZATION_PLAN.md (COMM offload cost model), tools/libretro-profiling/68k_hotspots.txt at `7b1dd75`
- [PICODRIVE](../appendices/bibliography.md#picodrive): pico/32x/memory.c (fill timing, poll detection), pico/32x/32x.c (fill end event)
- [S32X-SKILL](../appendices/bibliography.md#s32x-skill): architecture.md, optimization.md
