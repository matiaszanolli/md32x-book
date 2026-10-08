# Holding 60 frames per second

A 32X can show a new picture every 16.7 ms, 60 times a second on an NTSC television. Few programs manage it, and none of the 3D games read for this book do. This page covers what has to fit into one frame, why the frame rate can only be 60, 30, 20 or 15, what the shipped games actually ran at, the ways programs cut the time each picture takes, and what to do when a picture runs long.

## What one frame holds

| | NTSC (59.92 Hz) | PAL (49.70 Hz) |
|---|---|---|
| Time | 16.7 ms | 20.1 ms |
| Each SH-2 | about 384,000 clocks | about 459,000 clocks |
| 68000 | about 128,000 clocks | about 152,900 clocks |
| Lines in vertical blank | 38 of 262 | 89 of 313 (224-line mode) |

Sources: [System architecture](../megadrive/architecture.md); [Timing, interrupts and counters](../megadrive/vdp-timing.md#a-frame-line-by-line). The SH-2 figures are the clock divided by the number of frames a second; the 68000 runs at a third of the SH-2's speed.

Some prices to set against those budgets, from the manual's figures <span class="tag manual">manual</span>:

| Job | Cost | Share of one NTSC frame |
|-----|------|-------------------------|
| Clearing a 320 × 224 packed pixel screen with auto fill | About 4.7 ms, with the CPU free | 28% of the time, none of an SH-2 |
| Clearing it with one SH-2, a word per write | 35,840 words × 3 clocks = 107,520 clocks | 28% of that SH-2 |
| Clearing it with auto fill and polling FEN throughout, as Mortal Kombat II does | About 125,000 clocks spent waiting | A third of the Master |
| Writing the same screen from the 68000 | At least 143,360 of its clocks | More than a whole frame |

Sources: [Auto fill](../32x/vdp.md#auto-fill); [Access timing](../32x/timing.md#the-68000); [Living with bus contention](bus.md#what-each-program-did).

The lesson is in the first two rows: the pixels themselves take a quarter of a frame before anything is drawn. A program that wants 60 frames a second cannot clear and redraw the whole screen with one CPU.

## Why the rate is 60, 30, 20 or 15

The 32X has two frame buffers. A program draws into the back buffer, flips FS, and the flip takes effect at the next vertical blank. Until FS reads back the new value, the program must not draw, because the buffer it would draw into is still on screen ([Frame buffers and the FS bit](../32x/vdp.md#frame-buffers-and-the-fs-bit)). So every picture lasts a whole number of frames, and the rate is 60 divided by a whole number: 60, 30, 20, 15. A picture that takes 17 ms instead of 16 shows at 30 a second, not 59 <span class="tag emulator">emulator</span> [S32X-SKILL, optimization].

Two consequences:

- **Measure against the step you want, not the frame rate.** Speeding up a game from 25 ms to 20 ms changes nothing on screen: both are 30 per second. The next step is 16.7 ms. The [profiling page](../howto/profiling.md#timing-your-own-code) covers how to measure the spare time inside a frame.
- **Smoothness comes from steadiness.** A game that alternates between 30 and 20 looks worse than one held at 20. Several of the games below hold a lower rate exactly.

## What the shipped games ran at

Measured in PicoDrive for this book, by recording consecutive frames of each game's attract mode and counting how long each picture stays on screen <span class="tag emulator">emulator</span>:

| Game | Scene | Rate | How it shows |
|------|-------|------|--------------|
| After Burner Complete (Rutubo Games) | Play | 30 | Its Master's count of pictures drawn, watched for 2,000 frames [AB32X, headless runs] |
| Star Wars Arcade (Sega InterActive) | Opening text crawl | About 20, not locked | Most pictures held 3 frames, some 4; the Slave's polygon cutting is the slow stage [SWA, attract-mode profile] ([Case study](case-study-starwars.md#where-the-time-goes)) |
| Star Wars Arcade (Sega InterActive) | Play | 32.5 and 34.2 in two runs, not locked | 1,084 flips in 2,000 frames: pictures held 1 frame 273 times, 2 frames 708 times, 3 frames 101 times, 4 frames once. 1,140 flips in 1,999 frames: 346, 728 and 65 times for 1, 2 and 3 frames [SWA, FS bit read every frame] ([Case study](case-study-starwars.md#where-the-time-goes)) |
| Motocross Championship (Artech Studios) | Attract race | 15 | Every picture held exactly 4 frames |
| Virtua Racing Deluxe (Sega) | Racing | About 20 | The project's account of the game's 68000 state machine [VRD-NOTES, FRAME_RATE_ARCHITECTURE] |

Knuckles' Chaotix's attract demo changes every frame, but most of its picture is Mega Drive planes, which scroll every frame on their own, so this method cannot tell how often its 32X layer is redrawn. The method also counts any change at all, including the Mega Drive layer, so it gives an upper limit for the 32X layer.

The table is the honest starting point for a new project: the four 3D games measured, all published by Sega, ran at 15 to about 34 pictures a second, and none at 60. They come from four developers. In the parts compared for this book, the SH-2 start-up code and the reset handling, only After Burner Complete and Virtua Racing Deluxe share code beyond Sega's samples, and that only their reset recovery ([How much else the three share](../appendices/sample-code.md#how-much-else-the-three-share)). So the low rates were reached separately by four teams, which says more about the machine than one team's habits would. The developers are those the cartridges' credits name ([Sega's sample code in the games](../appendices/sample-code.md)).

## Getting the time per picture down

### Draw less

- **Don't clear what you redraw.** After Burner Complete's sky and sea are auto fills that also clear the screen, so it has no separate clear ([Auto fill](../32x/vdp.md#auto-fill)). A full-screen background drawn for every picture makes a clear redundant.
- **Draw what does not move once.** A homebrew game with a fixed camera redrew a 3D tunnel for every picture. Drawing it once at start-up and copying it for each picture took the game from 14.6 to 29 pictures a second <span class="tag emulator">emulator</span> [S32X-SKILL, optimization].
- **Restore only what moved.** The same game then kept a finished background in memory and, for each picture, copied back only the rectangles under the moving objects before drawing them: about 932 pixels a picture instead of 24,278, and 60 frames per second <span class="tag emulator">emulator</span> [S32X-SKILL, optimization]. Keep one list of changed rectangles **per frame buffer**: a rectangle changed in this picture is still old in the other buffer, which comes back two pictures later.
- **Find out what limits you.** In another homebrew game, moving 1,800 divides out of the inner loop changed nothing, while shortening the columns it drew took it from 12 to 20 pictures a second. If drawing fewer objects or vertices does not help, the limit is pixels <span class="tag emulator">emulator</span> [S32X-SKILL, optimization].
- **Shrink the picture.** A narrower or shorter view, simpler floors, a shorter draw distance and early rejection of what is off screen all cut pixels directly <span class="tag emulator">emulator</span> [S32X-SKILL, optimization]. d32xr forces a lower frame rate when its view is the full 320 pixels wide (below).

### Make the drawing cheaper

- **Let the VDP fill, and don't wait for it.** An auto fill runs while the CPU does other work. Mortal Kombat II spends a third of its Master's frame waiting for its clears; Star Wars Arcade hands each long span to the VDP and lets a timer interrupt bring the CPU back, polling only for short ones ([Software 3D](../techniques/software-3d.md#star-wars-arcade-polygons-as-auto-fills)).
- **Remove overhead from the innermost loop.** In one homebrew renderer, calling a function per span and re-clipping in it was 62% of the time spent on spans. Inlining it was the win <span class="tag emulator">emulator</span> [S32X-SKILL, optimization].
- **Keep the drawing loop in the cache or on-chip RAM** ([Cache discipline](cache.md)), and write the frame buffer in runs ([Living with bus contention](bus.md#moving-data-without-paying-twice)).

### Use every CPU

One SH-2 cannot clear and draw a full screen in a frame, but the work can be split. Star Wars Arcade runs a two-stage pipeline: the Master transforms and sorts the next picture while the Slave draws this one. The 68000 can run the game logic meanwhile ([Splitting work across three CPUs](cpu-split.md)).

## When a picture runs long

Every program meets pictures that take too long. What it does then decides whether the game slows down, stutters or breaks.

- **Count time, not pictures.** Aerobiz Ultimate's renderer works out which picture to show from the number of vertical interrupts since it started, so after a slow picture it skips ahead instead of making the whole sequence late <span class="tag emulator">emulator</span> [AU-NOTES, `disasm/sh2/master/fb.c`].
- **Scale movement by the time the last picture took.** d32xr multiplies the player's movement and gravity by the number of vertical blanks the last picture lasted, up to 8. Its game logic runs on a fixed 15 Hz tick whatever the frame rate. It caps the frame rate by waiting at least 2 vertical blanks between flips, 3 when the view is full width, and uses a fixed 4 during demos so that they replay the same way [D32XR, `d_main.c`, `p_user.c`, `marsnew.c`, `p_tick.c`].
- **Wait for the renderer instead of timing out.** By the VRD project's account, Virtua Racing Deluxe's 68000 steps through three states, one per vertical interrupt, and flips only when the SH-2s have signalled that the picture is drawn. If they have not, it waits another interrupt. A slow picture then simply lasts four frames instead of three <span class="tag emulator">emulator</span> [VRD-NOTES, FRAME_RATE_ARCHITECTURE].

Changing the rate of a game written for one rate is hard. The VRD project made its game step faster through its states and got 30 pictures a second at once, but about 30 constants in the game assume 20 game steps a second: speed limits, drag, boost, timers, the replay format. Scaling them broke collisions, music cues and the attract mode, and the change was reverted <span class="tag emulator">emulator</span> [VRD-NOTES, OPTIMIZATION_PLAN; FRAME_RATE_ARCHITECTURE]. Design the time step in from the start.

### Waiting without wasting

A 68000 waiting for the next frame can `stop` until an interrupt instead of polling. But `stop` wakes on any interrupt, not only the vertical one. When the VRD project replaced its waits with `stop`, a horizontal interrupt whose handler did nothing woke the main loop early on one screen. The fix is to check the flag the vertical interrupt sets after every `stop`, and go back to waiting if it is not set <span class="tag emulator">emulator</span> [VRD-NOTES, KNOWN_ISSUES]. On the SH-2 side, Sega forbids `SLEEP`, so a waiting SH-2 polls. Every poll is a bus cycle the other SH-2 may need, so poll slowly, from a loop small enough to stay in the cache, or let the work arrive by interrupt ([Living with bus contention](bus.md#sharing-without-colliding)).

## What "60 frames per second" should mean

Counting flips is not enough. The VRD project's definition, written after several results that did not hold up: game logic and input at 60 Hz, 60 distinct pictures each second in order, physics, timers and sound that run at real-time speed, no hangs over long runs, and a recorded ROM, input and profiler setup that let someone else repeat it [VRD-NOTES, VR60_STATUS]. Count distinct pictures from video, not interrupts or flips ([Counting real pictures](../howto/profiling.md#counting-real-pictures)).

## What to take away

- A frame is 16.7 ms: about 384,000 clocks per SH-2 and 128,000 for the 68000. Clearing the screen alone takes a quarter of that.
- Displayed rates are 60, 30, 20 or 15. Optimise to get under the next step, and hold a steady rate.
- The 3D games read for this book ran at 15 to 30 pictures a second.
- Draw less: skip redundant clears, draw static parts once, restore only what moved, one list per frame buffer.
- Let the VDP fill without waiting, and split the work across the CPUs.
- Design the game's time step so a picture that runs long delays only that picture, not the game.

## Open questions

- How often does Knuckles' Chaotix redraw its 32X layer?
- What does Mortal Kombat II run at in play, as opposed to its attract mode? And what do the games hold on a console, where contention slows the SH-2s that PicoDrive does not slow?
- Does any retail 32X game hold 60 frames per second with a full-screen 32X layer?

## Sources

- [S32X-SKILL](../appendices/bibliography.md#s32x-skill): optimization
- [D32XR](../appendices/bibliography.md#d32xr): `d_main.c`, `p_user.c`, `p_tick.c`, `marsnew.c`, `doomdef.h`
- [VRD-NOTES](../appendices/bibliography.md#vrd-notes): FRAME_RATE_ARCHITECTURE; OPTIMIZATION_PLAN; KNOWN_ISSUES; VR60_STATUS
- [AU-NOTES](../appendices/bibliography.md#au-notes): `disasm/sh2/master/fb.c`
- [AB32X](../appendices/bibliography.md#ab32x): headless runs
- Star Wars Arcade, Motocross Championship and Knuckles' Chaotix: frame captures in PicoDrive for this book ([SWA](../appendices/bibliography.md#swa), [MCX](../appendices/bibliography.md#mcx), [CHAOTIX](../appendices/bibliography.md#chaotix))
