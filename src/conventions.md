# How to read this book

## Where a claim comes from

Facts are followed by a short source reference in brackets. The key points to an entry in [Sources](appendices/bibliography.md):

> The SH-2 sees each 32X area twice: once through the cache and once bypassing it [32X-OV, SH-2 memory map].

When a page number or section number is known, it goes after the key: `[SH7604 §8.3]`, `[32X-HWM p.42]`.

## How sure we are

Claims that matter for working code carry one of four tags:

| Tag | Meaning |
|-----|---------|
| <span class="tag tested">tested</span> | Confirmed on a real console. Say which model and revision when it matters. |
| <span class="tag manual">manual</span> | Stated in an official document but not yet tested. |
| <span class="tag emulator">emulator</span> | Seen only in an emulator. Say which one and which version. |
| <span class="tag disputed">disputed</span> | Sources disagree. The full story is in [Where the docs disagree](appendices/discrepancies.md). |

A claim with no tag is background that does not affect how code behaves.

### Timings from emulators

Most of the book's timings (clocks per frame, frame rates, the share of a CPU's time a routine takes) were measured in PicoDrive, a few in ares, none yet on a console, and they carry the <span class="tag emulator">emulator</span> tag. Upstream PicoDrive charges no cycles for an SH-2 memory access and models neither the SH-2 caches nor bus contention [PICODRIVE, `pico/32x/memory.c` at `26ecb2b`]; ares charges a fixed cost per memory region [ARES]. None of the four 32X emulators read for this book (PicoDrive, ares, MAME, BlastEm) has code that makes one SH-2 wait for the other on their shared bus. So for work a CPU does, an emulator's figure is a ceiling on a console's speed: a console does the same work as fast or slower. Waits are the exception. PicoDrive skips the polling loops it recognises and can wake a waiting CPU late, so a wait can come out longer than on a console ([Four traps](howto/profiling.md#four-traps-all-met-in-the-wild)).

## Frames and pictures

The book keeps two words apart that games and manuals often run together:

- A **frame** is one refresh of the television picture, from one vertical blank to the next: 1/60 of a second on NTSC machines, about 384,000 SH-2 clocks, and 1/50 on PAL, about 459,000 ([Clocks and frames](appendices/timing.md#clocks-and-frames)). "Per frame" budgets, "once a frame" interrupts and the frame numbers of emulator runs ("frame 2100") all count refreshes.
- A **picture** is one complete image a program draws and shows. A game that draws 30 pictures a second shows each one for two frames. Work done "per picture", such as building a polygon list, flipping the frame buffers or purging a cache before reading the new list, happens at the game's own rate, not the television's.

Three established terms keep their usual names. The *frame buffer* is the memory a picture is drawn in. The *frame rate* is the number of pictures drawn a second, written "60 frames a second" only when every frame gets a new picture. The frames of a movie or an animation are pictures in this sense, and keep their names where a format defines them (CinePak key frames). Names in code and in quoted documents are left as they are.

## Numbers

Hexadecimal is written `$A15100` for 68000 addresses and `0x20004000` for SH-2 addresses, matching the convention of each CPU's assemblers. Sizes use KB = 1024 bytes and Mbit for chip capacities, as the original documents do.
