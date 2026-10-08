# Access timing per CPU

Every CPU in a 32X pays a different price to reach each part of the machine, and the prices decide where code and data should live. Sega gives them as wait states: clocks added to the CPU's shortest bus cycle, which is 4 clocks for the 68000 and 2 for the SH-2 [32X-HWM §4.4 p.77]. This chapter collects those figures for all three CPUs, explains why most of them are ranges, and ends with what they mean for placing things in memory.

None of the figures here has been measured on a console for this book. They are the manual's numbers, sometimes added up.

## The figures

| What | SH-2 waits | SH-2 clocks | 68000 waits | 68000 clocks |
|------|------------|-------------|-------------|--------------|
| Cartridge ROM | 6-15 | 8-17 | 0-5 | 4-9 |
| Frame buffer, read | 5-12 | 7-14 | 2-4 | 6-8 |
| Frame buffer, write | 1-3 | 3-5 | 0 | 4 |
| Palette, read | 5 and up | 7 and up | 2 and up | 6 and up |
| Palette, write | 5 and up | 7 and up | 3 and up | 7 and up |
| VDP registers, read | 5 | 7 | 2 | 6 |
| VDP registers, write | 5 | 7 | 0 | 4 |
| System registers (including the communication ports) | 1 | 3 | 0 | 4 |
| Boot ROM | 1 | 3 | — | — |
| SDRAM | — | 12 per 8-word burst read, 2 per word written | — | No access |

Sources: [32X-HWM §4.4 pp.77-78 (checked on the scan); 32X-HWI (1) items 1-4]. "And up" means up to 64 µs, a whole display line, when the VDP is using the palette.

Clocks are not time. The 68000 runs at a third of the SH-2's speed (7.67 MHz against 23.01 MHz on NTSC machines), so the same access takes very different times:

| One word from | SH-2 | 68000 |
|---------------|------|-------|
| System register | 0.13 µs | 0.52 µs |
| Cartridge ROM | 0.35-0.74 µs | 0.52-1.17 µs |
| Frame buffer, write | 0.13-0.22 µs | 0.52 µs |
| Frame buffer, read | 0.30-0.61 µs | 0.78-1.04 µs |

The SH-2 is not much quicker at reaching the cartridge than the 68000. And a cache line from the cartridge costs it 64 to 136 clocks, against 12 from SDRAM ([Bus state controller](../sh2/bsc.md#what-a-16-bit-bus-costs)). That gap is the whole reason SH-2 programs run from SDRAM.

## Why most figures are ranges

A range means something else can be using the same memory.

- **Cartridge ROM is shared between the 68000 and the SH-2s.** When both ask at once, the SH-2 goes first and the 68000 waits for it to finish [32X-HWM §4.1 p.74, ROM access competition]. The 68000's 0-5 waits are mostly waiting for the SH-2s. While RV = 1 the SH-2s cannot reach the cartridge at all and wait until the 68000 clears it ([The RV bit](architecture.md#the-rv-bit)).
- **The frame buffer is shared with the VDP.** The VDP reads the displayed buffer to make the picture, the DRAM needs refreshing (FEN reads 1 for 40 clocks while it happens), and an auto fill holds the buffer for its whole length ([Auto fill](vdp.md#auto-fill)) [32X-HWM §3.3, register latch timing].
- **SH-2 frame buffer writes go through a small write buffer.** While it has room a write takes 3 clocks; once it is full, 5. Idle clocks between writes let it drain, down to a 3-clock minimum [32X-HWM §4.4 p.77]. The manual says it holds four words; an earlier reference says two <span class="tag disputed">disputed</span> ([discrepancy 4](../appendices/discrepancies.md)). The 68000 writes with no wait at all.
- **The palette is read by the VDP during the display.** A CPU access that collides with it waits until the end of the line, up to 64 µs. PEN in the frame buffer control register reads 1 when the palette is free: in blanking, and always in direct colour mode, which does not use it [32X-HWM §4.4 p.77; §3.2.3]. See [Colours and the palette](vdp.md#colours-and-the-palette).

Registers, the boot ROM and SDRAM have fixed figures. The SDRAM's fixed figure hides the other SH-2: the two SH-2s share one bus, so a Slave access waits while the Master is using it, and the other way round ([Two SH-2s, one bus](../sh2/bsc.md#two-sh-2s-one-bus)).

## The 68000

The 68000's own Mega Drive memory is unchanged by the 32X. What changes:

- **The cartridge can now be slow.** On a plain Mega Drive nothing else uses the cartridge. In 32X mode the 68000 can wait up to five clocks per access, because the SH-2s share it and win ties [32X-HWM §4.4 p.77; §4.1 p.74]. A 68000 loop running from the cartridge slows down whenever the SH-2s read the cartridge. The manual's remedies are for the SH-2s to copy what they need into SDRAM and read the cartridge rarely, or for the 68000 to set RV, which shuts the SH-2s out [32X-HWM §4.1 p.74]. RV also removes the `$880000` window the 68000's own code runs from, so that only helps code running from work RAM ([The RV bit](architecture.md#the-rv-bit)).
- **The 32X registers are free.** System and VDP register writes take no wait states, so the communication ports are as cheap for the 68000 as work RAM [32X-HWM §4.4 p.78].
- **The frame buffer is cheap to write and slow to fill.** No waits on writes, but every word still takes a 4-clock bus cycle. A whole packed pixel screen of 35,840 words is at least 143,360 clocks, 18.7 ms, before counting the instructions: more than an NTSC frame. The 68000 can patch the frame buffer, not redraw it.

## The Z80

The Z80 reaches the 32X only through its 32 KB window into 68000 space, and every access through that window is a 68000 bus cycle that holds the 68000 off ([System architecture](../megadrive/architecture.md)). On top of that, Sega's manual says the competition for the 32X between the 68000 and the SH-2s applies to the Z80 in the same way [32X-HWM §4.3 p.76]. And on production consoles a Z80 write to the 32X's areas locks up the 68000 ([The Z80's view](architecture.md#the-z80s-view)). In practice the Z80 can read a communication port now and then. Anything more belongs to the 68000.

## The SH-2

The SH-2's costs, worked out per access and per cache line, are in [Bus state controller](../sh2/bsc.md#what-a-16-bit-bus-costs). The short version:

| Access | Clocks on the bus |
|--------|-------------------|
| Cache hit, or on-chip RAM | 0 |
| Cache miss in SDRAM (one 16-byte line) | 12 |
| Cache miss in cartridge ROM (one line) | 64-136 |
| Any read through `0x26000000` | 12 |
| Word written to SDRAM | 2 |
| System register or communication port | 3 |
| Word written to the frame buffer | 3-5 |
| Word read from the frame buffer | 7-14 |

Every area is 16 bits wide, so a longword is two of these. The cache is write-through, so every store goes to the bus whether or not the line is cached [SH7604 §7.11.2].

## Where things should live

| What | Where | Why |
|------|-------|-----|
| SH-2 code | SDRAM, cached | A miss costs 12 clocks there, up to 136 in the cartridge. The boot ROM puts it there for you ([Boot](boot.md#the-master-sh-2-boot-rom)) |
| The hottest SH-2 loop | On-chip RAM (two-way cache mode) | No bus at all, so the other SH-2 is not held up ([Cache](../sh2/cache.md#two-way-mode-2-kb-of-on-chip-ram)) |
| Data one SH-2 owns | SDRAM, cached | Hits are free; writes cost 2 clocks a word |
| Data both SH-2s use | SDRAM, read once through `0x26000000` | Each uncached read costs a full burst ([Cache discipline](../patterns/cache.md)) |
| Flags and small messages between CPUs | Communication ports | 0 waits for the 68000, 3 clocks for the SH-2, and never cached ([Communication](communication.md)) |
| Bulk data from the 68000 | The FIFO | See [DREQ and the FIFO](fifo.md#what-it-costs) |
| Large read-only assets | Cartridge, compressed | Read by the SH-2 in a few large runs, or unpacked into SDRAM ([Compression](../techniques/compression.md)) |
| Pixels that are read back | SDRAM or on-chip RAM | Frame buffer reads cost 7-14 clocks. Build there, then write to the frame buffer |
| Pixels written once | Frame buffer, in runs | 3 clocks a word while the write buffer has room |
| Large areas of one colour | Auto fill | About 3 clocks a word with the CPU free ([Auto fill](vdp.md#auto-fill)) |
| Palette changes | In blanking, or when PEN = 1 | Otherwise up to a line of waiting |
| 68000 code that must not slow down | Work RAM | The cartridge is shared with the SH-2s |

## In emulators

Neither common emulator charges these costs faithfully, so a profile taken in one shows where a program spends its instructions, not where it waits for memory.

- **Upstream PicoDrive** adds a small fixed charge to an SH-2's byte and word reads of the boot ROM, registers and palette, and nothing for any other access. It has no cache model, so a cache miss costs nothing either <span class="tag emulator">emulator</span> [PICODRIVE, pico/32x/memory.c]. The Virtua Racing Deluxe project's copy adds an optional model of the manual's table and of the cache [VRD-NOTES, PicoDrive timing patch]. In the copy read for this book nothing tells that model when the cache is switched on, so it charges every access as uncached.
- **Ares** adds a fixed number of clocks per access: 1 for registers and the boot ROM, 6 for the cartridge, 5 for a frame buffer read and 4 for a write, nothing for SDRAM. It makes the SH-2 wait while RV = 1 and while the VDP holds the palette, and it drops frame buffer accesses made while FEN = 1 rather than making them wait <span class="tag emulator">emulator</span> [ARES, md/m32x/bus-internal.cpp, io-internal.cpp].

Neither models the competition between the 68000 and the SH-2s for the cartridge, or the frame buffer's write buffer.

## What to take away

- Run SH-2 code from SDRAM and keep the hottest loop in on-chip RAM. The cartridge is up to eleven times slower per cache line.
- Never read the frame buffer if you can avoid it, and write it in runs.
- Use the communication ports for anything small that crosses between CPUs; they are the cheapest shared memory on the machine.
- Expect the 68000 to slow down when the SH-2s read the cartridge, and keep its critical loops in work RAM.
- Do not trust an emulator's cycle counts for memory-bound code.

## Open questions

- How many wait states does the 68000 actually see on the cartridge while both SH-2s are drawing from SDRAM, and while one is reading the cartridge?
- How deep is the frame buffer write buffer ([discrepancy 4](../appendices/discrepancies.md))?
- Does an SH-2 access to an open SDRAM row cost less than the manual's fixed figures?
- What does a Z80 read of a communication port cost the 68000?

## Sources

- [32X-HWM](../appendices/bibliography.md#32x-hwm): §3.2.3, §3.3, §4.1 p.74, §4.3 p.76, §4.4 pp.77-78 (checked on the scan)
- [32X-HWI](../appendices/bibliography.md#32x-hwi): (1) items 1-4
- [SH7604](../appendices/bibliography.md#sh7604): §7.11.2
- [VRD-NOTES](../appendices/bibliography.md#vrd-notes): PicoDrive timing patch (`pico/32x/vrd_timing.c`)
- [PICODRIVE](../appendices/bibliography.md#picodrive): pico/32x/memory.c
- [ARES](../appendices/bibliography.md#ares): md/m32x/bus-internal.cpp, io-internal.cpp
