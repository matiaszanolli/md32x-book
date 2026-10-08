# Profiling and finding where time goes

A 32X game has three processors and no operating system, so nothing will tell you where the time goes until you measure it yourself. This page is about the two kinds of measuring. If you have the source, you put instruments into the program and read them out. If you only have a cartridge — your own from last year, or a commercial one — you measure it from outside, in an emulator. Both kinds have traps, and the traps are the interesting part: several published numbers about performance have turned out to be artifacts of the way they were measured.

First the arithmetic every measurement hangs on. One NTSC frame is 1/60 of a second, so the per-frame budgets are about 127,800 cycles for the 68000 (7.67 MHz) and about 383,300 for each SH-2 (23 MHz). PAL frames are longer. "That routine costs 10% of a frame" means "10% of those numbers of cycles", and anything a CPU does past its budget is time the next frame starts paying for. (Clock rates and where they come from: [System architecture](../megadrive/architecture.md) and [Architecture and memory maps](../32x/architecture.md).)

## Timing your own code

**Stamp phases with the SH-2's own timers.** The free-running timer counts at a known rate, so a reading taken at the start and end of a phase gives its cost directly. Turning ticks into milliseconds wants a division, so compute the reciprocal once and multiply: one project keeps `4096·1000/clock` as a fixed-point constant and shifts the result down <span class="tag emulator">emulator</span> [D32XR, marsnew.c; S32X-SKILL, optimization notes]. The 32X development libraries wrap the same idea (`Mars_GetTicCount`, `Mars_GetWDTCount`, `Mars_FRTCounter2Msec`) [S32X-SKILL, optimization notes]. Keep an eye on size at the same time: printing `__bss_end` and the section sizes in every build log catches memory growth the day it happens, not the week nothing fits [S32X-SKILL, optimization notes].

**Make the phases visible.** Averaging the last four readings of each phase with a shift, and drawing them as ten lines of text over the picture, is enough to watch the cost change as you play <span class="tag emulator">emulator</span> [D32XR, r_main.c]. Beyond timing, diagnostic draw modes answer *what kind* of cost: a renderer with a no-op drawer measures geometry cost with the fill cost removed, and one debug mode that paints each texture-cache entry a flat colour shows cache residency as a picture <span class="tag emulator">emulator</span> [D32XR, r_main.c, r_cache.c].

**Count pixels, not just time.** Run the renderer's span, quad and copy calls against counters on the host side, reported per element — backdrop, entities, HUD. If the counts say the primitives are few but the time is large, your limit is per-primitive setup; if both are large, it is fill rate <span class="tag emulator">emulator</span> [S32X-SKILL, optimization notes]. One game found its bottleneck was redraw of things that had not changed, which no per-pixel timer would have said.

**Measure frame rate from video, without touching the game.** Draw a white bar whose width is the game's own frame counter cut to seven bits. Capture the screen twice, N emulated frames apart, and the change in width — wrapped — is the number of game iterations in those frames <span class="tag emulator">emulator</span> [S32X-SKILL, optimization notes]. A game running between 12 and 19 iterations per 60 frames can be read this way to within a few percent from two stills.

**Probe headroom with deliberate ballast.** Frame rate cannot show an improvement that stays inside the spare part of a frame: 15 fps and 16 fps both look like "dropping frames". Instead inject busy-work of a known cost and increase it until the frame drops a step; the amount absorbed is your headroom, a continuous number <span class="tag emulator">emulator</span> [S32X-SKILL, optimization notes]. Then validate the instrument before trusting it. In one project a ballast flag was compiled out, and in another the emulator's recompiler recognised the busy loop and skipped it — four million dummy iterations that cost nothing, and every reading after that meaningless <span class="tag emulator">emulator</span> [S32X-SKILL, optimization notes].

## Counting real frames

The obvious counter — "how many vertical interrupts per second?" — is useless: it counts the mains frequency, 3,600 per minute on NTSC, whether the game draws or not [VRD-NOTES, FPS counter notes]. What you want to count is one of:

- **Displayed frames**: count flips of the frame-buffer select bit per 60 vertical interrupts [VRD-NOTES, FPS counter notes].
- **Game iterations**: count how many times the main loop runs, with a counter the loop itself increments. Keep such a counter in cache-through SDRAM, not in a communication register or somewhere a debug read cannot see.

A counter that the instrumented game reads through a communication register deserves suspicion: one project's counter read a *live* register instead of its own variable, another read the adapter control register where it meant to read the frame-buffer control byte, and in one build an assembler bug landed a subroutine call two bytes past its target [VRD-NOTES, FPS counter notes]. Every one of those produced plausible-looking numbers.

**Emulated frames are not game frames.** A "run 2,400 frames" emulator run at an effective 12 fps is about 480 game iterations. Timers that count iterations need the right window, and brief effects can fall entirely between two captured frames — capture several [S32X-SKILL, testing notes].

## Measuring a game from outside

When there is no source to instrument — a commercial cartridge, or a bug that only shows in last month's build — the tool is a headless emulator that runs the ROM unattended and records. The one used for this book is a PicoDrive libretro core driven by the Virtua Racing Deluxe project's headless front end ([The harness](emulator-testing.md#the-harness)), and everything below is measured with it.

- **A script of inputs decides what gets measured.** A text file of one joypad mask per frame, replayed exactly, takes a game from its title screen to the scene you care about, and two runs with the same script visit the same scenes [VRD-NOTES, VR60 status]. Without this, a profile is an anonymous average of whatever the attract mode felt like showing.
- **Per-frame counters** give cycles per CPU, plus a hash of the frame buffer per frame, so scene changes are visible in the log.
- **Per-address histograms** are the main tool: every program counter, its executions and cycles, sorted. The histogram must come from the interpreter. Under the recompiler the program counters of compiled code are not the program's addresses at all — see the traps below.
- **The idle/useful split needs care.** Which addresses count as "waiting" is a judgement you make from the disassembly; report the split with that list, not as a fact.
- **Memory watches, register dumps and video captures** turn a number into a story: watching a status register over time shows the handshake; dumping frames proves the run reached the scene it profiles.

## Four traps, all met in the wild

**A hot spot that is a wait.** One profile showed the Slave spending two thirds of its cycles in one address — which disassembly revealed to be a 64-iteration delay loop. Removing it cut the Slave's measured cycles by two thirds and changed the frame rate not at all <span class="tag emulator">emulator</span> [VRD-NOTES, profiling notes]. Cycle counts measure activity, not value.

**Averages over mixed scenes.** A 13% "communication bottleneck" dissolved when the profile was split by scene: it was entirely the car-select screen, and during racing the same channel was idle two thirds of the time <span class="tag emulator">emulator</span> [VRD-NOTES, profiling notes]. Always gate the measurement window to one scene.

**Truncated histograms lie confidently.** A top-200 address histogram "proved" a hook never ran; a full trace of callers showed it running at 20 Hz, below the cut <span class="tag emulator">emulator</span> [VRD-NOTES, profiling notes].

**The recompiler rewrites the question.** PicoDrive's dynamic recompiler skips recognised poll loops — a CPU that is patiently waiting on a register can show almost no cycles at all — so a waiting CPU's share can look far smaller than it is. Addresses can mislead too: a busy region at `0xC0000000` looks like nothing in SDRAM or the cartridge, but it is real code in on-chip RAM, where Knuckles' Chaotix runs its sound driver ([PWM audio](../32x/pwm.md#1-the-pwm-interrupt-star-wars-arcade)). One game's Master looked like it had vanished from a profile; interpreter-mode register sampling caught it cycling through real work, polling the 32X's status bits between frames <span class="tag emulator">emulator</span> [CHAOTIX, headless runs; PICODRIVE, SH-2 DRC]. Rule: histograms and cycle splits from the interpreter; anything the recompiler reports gets cross-checked before it is quoted.

## What the numbers look like

Measured with the interpreter, with input scripts fixing the scene, several games' splits:

| Game | 68000 | Master SH-2 | Slave SH-2 | Shape |
|------|-------|-------------|------------|-------|
| Motocross Championship, racing | ~128k cycles/frame, mostly a communication wait | ~266k, frame loop plus a bulk frame-buffer upload | parked, even during races | one SH-2 does everything |
| Knuckles' Chaotix, attract | ~126k, wait loop | ~1.5k counted plus elided VDP polling | ~302k: the PWM mixer in on-chip RAM, frame buffer clears by auto fill, and a polling loop | the Master draws; the Slave clears and plays sound |
| Virtua Racing Deluxe, racing | idle two thirds | — | ~100k after a delay loop was removed | both SH-2s active |

Sources: [MCX, headless runs; CHAOTIX, headless runs; VRD-NOTES, profiling notes]. All emulator-measured; see the traps above before comparing them to each other. Two things generalise: some CPU is always parked in a loop (finding that loop is the first thing a profile is for), and the communication handshakes the [boot chapter](../32x/boot.md#the-handshake-into-your-code) describes are exactly the waits that dominate the 68000's counts.

## Comparing two builds of your own game

Once your own game changes timing, it diverges: the same frame number is a different scene in each build. Compare by content, not by number: hash each frame's video memory, palette and registers from a save state, pair frames between builds by their hashes, and compare the order of first appearances by counting inversions — a reordered screen list is a real change, a constant offset in frame numbers is not <span class="tag emulator">emulator</span> [AU-NOTES, comparison notes]. And when a check is meant to catch a failure, make it fail closed: an oracle that passes on a black screen has passed at nothing <span class="tag emulator">emulator</span> [AU-NOTES].

The strict form of this discipline, from the same project: every experiment ships as a pair of ROMs built from one source, identical outside the instrumented bytes, both hashes recorded; the instrumented ROM must pass liveness checks (the scene advances, the frame buffer changes, the communication ports are not stuck) before its numbers are read; and the whole run must replay byte-identically [VRD-NOTES, VR60 status]. A save state that silently freezes a counter is a known failure mode — recheck liveness after loading one [VRD-NOTES, VR60 status].

## On real hardware

Emulator timing is a model. PicoDrive models neither the SH-2 cache nor SDRAM latency; ares models the cache (in its interpreter only) and charges one fixed cost per access to each region, with no competition between the CPUs ([Access timing](../32x/timing.md#in-emulators)) [AU-NOTES, hardware tests; ARES]. Each also stops or skips different edge behaviours ([What an emulator cannot tell you](emulator-testing.md#what-an-emulator-cannot-tell-you)). Trust a timing conclusion when two emulators agree, and keep a list of what only the console can answer. The [hardware testing page](real-hardware.md) covers that side.

## Where to go next

- [Automated testing in an emulator](emulator-testing.md) uses the same front end for correctness instead of speed.
- [Holding 60 frames per second](../patterns/60fps.md) is what to do with the headroom once you can see it.
- [Disassembling and annotating a commercial game](reverse-engineering.md) covers the other half of reading someone else's profile.

## Sources

- [VRD-NOTES](../appendices/bibliography.md#vrd-notes): FPS counter notes; profiling corrected results; performance notes; VR60 status (`VR60_STATUS.md`); libretro profiling front end
- [AU-NOTES](../appendices/bibliography.md#au-notes): comparison notes; hardware tests; PC sampling notes
- [S32X-SKILL](../appendices/bibliography.md#s32x-skill): optimization notes; testing notes
- [D32XR](../appendices/bibliography.md#d32xr): marsnew.c, marshw.c, r_main.c, r_cache.c
- [PICODRIVE](../appendices/bibliography.md#picodrive): SH-2 recompiler and poll detection
- [ARES](../appendices/bibliography.md#ares): modelled hardware
- [MCX](../appendices/bibliography.md#mcx): headless runs, racing scene
- [CHAOTIX](../appendices/bibliography.md#chaotix): headless runs, attract scene
