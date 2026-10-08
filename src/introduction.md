# Introduction: Virtua Racing Deluxe

> **Status:** first draft. Lines marked **TODO** need numbers or facts from the project before this page goes public.

Virtua Racing Deluxe was one of the first games made for the 32X. It is a 3D racing game, the kind of software the 32X was sold for, running on an add-on with two SH-2 processors, a 68000 and a Z80. Open it up and look at how it uses those four processors, and you find that most of the machine is sitting still.

That gap, between what the hardware can do and what an early game actually asked of it, is what this book is about. This chapter tells the short version of how the gap was found and what was done about it. The full engineering write-up is in [Part V](patterns/case-study-vr.md).

## What the original game does

**It draws far fewer frames than the screen shows.** The Mega Drive's vertical interrupt fires 60 times a second, and the game's own counter dutifully counts 60 per second. But the 32X only finishes a new 3D frame about once every three interrupts, around 20 frames per second <span class="tag emulator">emulator</span> [VRD-NOTES, profiling].

> **TODO:** replace "around 20" with the measured count from the SH-2 frame counter, and say which emulator and version (or which console).

**The 68000 spends most of its time waiting.** Of the 16.7 ms between two vertical interrupts, game logic takes about 1.4 ms. About 7.8 ms goes to polling: a loop that keeps asking the 32X side whether it is ready yet. Another 5.7 ms is plain idle time <span class="tag emulator">emulator</span> [VRD-NOTES, profiling].

**One of the two SH-2s barely works.**

> **TODO:** the project notes say the Slave SH-2 is about 99.97% idle; other descriptions of the project talk about the Master being idle and the Slave's time being wasted. Settle which CPU does what in the original game and state it here with the measurement.

**A quarter of the cartridge space is never used.** The 32X can map 4 MB of cartridge ROM, but the game's header declares its ROM as ending at `$2FFFFF`, which is 3 MB [VRD-NOTES, ROM size; 32X-HWM §3.1].

## How it was taken apart

The first rule was not to change anything until the original could be rebuilt exactly. The game was disassembled into source files that assemble back into a ROM identical to the original, byte for byte, checked by comparing MD5 hashes [VRD-NOTES, setup]. From then on, every change could be tested against a build known to be correct, and every annotation pass (turning raw data words back into readable instructions, naming functions) had to keep that rebuild identical. [Disassembling and annotating a commercial game](howto/reverse-engineering.md) describes the method.

The second rule was to measure the right thing. The vertical interrupt counter always reads 60 per second, so it says nothing about how fast the game really runs. The real figure comes from a counter placed where the SH-2 finishes a frame, stored in SDRAM and accessed through its cache-through address (`0x26000400`) so the value in memory is always current [VRD-NOTES, profiling; 32X-OV, SH-2 memory map]. [Profiling and finding where time goes](howto/profiling.md) explains why this matters.

## What changed

The empty fourth megabyte was put to use. The build fills the ROM out to 4 MB, updates the header's end address to `$3FFFFF`, and places new Slave SH-2 code at `$300000`, which the SH-2 sees at `0x02300000` through the cache [VRD-NOTES, ROM size; 32X-OV, SH-2 memory map].

The idle SH-2 was given rendering work, so that both processors share each frame.

> **TODO:** describe what the Slave now does, whether polling was replaced with interrupts, the frame rate achieved, and which console the result was tested on.

> **TODO (optional):** the press coverage (RetroRGB, Time Extension, Video Game Esoterica) and links.

## What the rest of the book takes from this

Each problem above is a pattern that shows up across 32X software, and each one has a chapter:

- A processor that waits is the most common waste on the 32X. See [Splitting work across three CPUs](patterns/cpu-split.md).
- Polling loops between the 68000 and the SH-2s burn time on both sides. See [68000 and SH-2 communication](32x/communication.md).
- Frame rate has to be measured where frames are finished, not where the screen refreshes. See [Profiling and finding where time goes](howto/profiling.md).
- Cartridge space and how each CPU sees it. See [Using more cartridge space](howto/large-cartridges.md).
- Knowing which addresses go through the cache and which bypass it. See [Cache discipline](patterns/cache.md).

## How the book is organised

- **Part I** covers the Mega Drive: the 68000, the VDP, the Z80 and its sound chips, I/O and cartridges.
- **Part II** covers the SH7604, the SH-2 chip used twice inside the 32X, reduced to what matters for a game.
- **Part III** covers the 32X itself: memory maps, registers, the frame buffer VDP, communication between CPUs, PWM audio and the hardware bugs.
- **Part IV** is practical: toolchains, headers, first programs, profiling, reverse engineering.
- **Part V** is about getting the most out of the hardware, and ends with two case studies: the full Virtua Racing Deluxe write-up, and Aerobiz Ultimate, a Mega Drive game moved onto the 32X.
- **Part VI** collects the techniques games build on that hardware: fixed-point maths, software 3D, first-person and pseudo-3D engines, 2D effects, compression, memory management, game logic and asset pipelines, drawn from shipped games and current homebrew.

Every claim points to where it came from and says whether it has been tested on a real console. When the sources disagree with each other or with the hardware, the book says so. See [How to read this book](conventions.md).
