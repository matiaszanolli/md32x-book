# Access timing per CPU

Every CPU in a 32X pays a different price to reach each part of the machine, and the prices decide where code and data should live. Sega gives them as wait states: clocks added to the CPU's shortest bus cycle, which is 4 clocks for the 68000 and 2 for the SH-2 [32X-HWM §4.4 p.77]. This chapter collects those figures for the 68000, the Z80 and the SH-2, explains why most of them are ranges, and ends with what they mean for placing things in memory.

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

| One word access to | SH-2 | 68000 |
|---------------|------|-------|
| System register | 0.13 µs | 0.52 µs |
| Cartridge ROM | 0.35-0.74 µs | 0.52-1.17 µs |
| Frame buffer, write | 0.13-0.22 µs | 0.52 µs |
| Frame buffer, read | 0.30-0.61 µs | 0.78-1.04 µs |

The SH-2 is not much quicker at reaching the cartridge than the 68000. And a cache line from the cartridge costs it 64 to 136 clocks, against 12 from SDRAM ([Bus state controller](../sh2/bsc.md#what-a-16-bit-bus-costs)). That gap is the whole reason SH-2 programs run from SDRAM.

## Why most figures are ranges

A range means something else may be using the same memory. The manual says only that waits depend on the kind of access and on the state of the machine [32X-HWM §4.1 p.74]; it does not say which part of any range is which cause, and neither does any other source read for this book. What follows is what each range can contain.

- **Cartridge ROM is shared between the 68000 and the SH-2s.** When both ask at once, the SH-2 goes first and the 68000 waits for it to finish; a request that arrives while the other CPU's access is under way waits for that access [32X-HWM §4.1 p.74, ROM access competition] ([The rule at the cartridge](../patterns/bus.md#the-rule-at-the-cartridge)). The 68000's 0-5 waits can be waiting for the SH-2s. While RV = 1 the SH-2s cannot reach the cartridge at all and wait until the 68000 clears it ([The RV bit](architecture.md#the-rv-bit)), which is a wait of a different kind, not part of either range.
- **What an SH-2 loses to the 68000 is 9 to 12 clocks at most.** The manual does not say whether the SH-2's 6-15 already contains waiting for the 68000. If it does, the loss is at most 9 clocks beyond the best case (15 - 6). If it does not, the loss comes on top, and it is at most the rest of one 68000 access. A 68000 access that has the cartridge takes its 4-clock minimum, 12 SH-2 clocks: the 68000's waits, up to 5 more, are time it spends waiting for something else, not time it holds the cartridge (an inference from the 68000's waits being mostly the SH-2s' doing, not a measurement). So the two readings give 9 and 12, and this book plans with 12. The [contention chapter](../patterns/bus.md#the-rule-at-the-cartridge) and the [compression chapter](../techniques/compression.md#moving-decompression-to-an-sh-2) price the loss that way.
- **The same figures bear on whether the SH-2 holds the bus across a line fill.** The 68000's maximum of 5 waits is about 15 SH-2 clocks, one SH-2 word cycle (8-17 clocks). If that maximum includes waiting for the SH-2s, a 68000 can never wait out an eight-word fill (64-136 SH-2 clocks, 21-45 68000 clocks), so the bus would have to be given up between the words of a fill. That is an inference from the range, not something the manual states, and it is open ([Open questions](#open-questions)).
- **The frame buffer is shared with the VDP.** The VDP reads the buffer FS shows while the CPUs work on the other one, and the manual does not say what the sharing costs inside the 5-12 and 1-3 ranges. Refresh is not clearly a cause: FEN reads 1 for 40 clocks while it happens, but the manual says the DRAM can still be accessed then [32X-HWM §3.3, register latch timing]. An auto fill is not a wait inside any range. While one runs, the program must keep off the buffer it fills, and what an access made then does is not documented ([Auto fill](vdp.md#auto-fill); [The VDP and the frame buffer](../patterns/bus.md#the-vdp-and-the-frame-buffer)).
- **SH-2 frame buffer writes go through a small write buffer.** While it has room a write takes 3 clocks; once it is full, 5. Idle clocks between writes let it drain, down to a 3-clock minimum [32X-HWM §4.4 p.77]. The manual says it holds four words; an earlier reference says two <span class="tag disputed">disputed</span> ([discrepancy 4](../appendices/discrepancies.md)). The 68000 writes with no wait at all.
- **The palette is read by the VDP during the display.** A CPU access that collides with it waits until the end of the line, up to 64 µs. PEN in the frame buffer control register reads 1 when the palette is free: in blanking, and always in direct colour mode, which does not use it [32X-HWM §4.4 p.77; §3.2.3]. See [Colours and the palette](vdp.md#colours-and-the-palette).

Registers, the boot ROM and SDRAM have fixed figures. The SDRAM's fixed figure hides the other SH-2: the two SH-2s share one bus, so a Slave access waits while the Master is using it, and the other way round ([Two SH-2s, one bus](../sh2/bsc.md#two-sh-2s-one-bus)).

## The 68000

The 68000's own Mega Drive memory is unchanged by the 32X. What changes:

- **The cartridge can now be slow.** On a plain Mega Drive nothing else uses the cartridge. In 32X mode the 68000 can wait up to five clocks per access, because the SH-2s share it and win ties [32X-HWM §4.4 p.77; §4.1 p.74]. A 68000 loop running from the cartridge slows down whenever the SH-2s read the cartridge. The manual's remedies are for the SH-2s to copy what they need into SDRAM and read the cartridge rarely, or for the 68000 to set RV, which shuts the SH-2s out [32X-HWM §4.1 p.74]. RV also removes the `$880000` window the 68000's own code runs from, so that only helps code running from work RAM ([The RV bit](architecture.md#the-rv-bit)).
- **The 32X registers are free.** System and VDP register writes take no wait states, so the communication ports are as cheap for the 68000 as work RAM [32X-HWM §4.4 p.78].
- **The frame buffer is cheap to write and slow to fill.** No waits on writes, but the instructions that do the writing are what cost. A whole packed pixel screen is 35,840 words, and an NTSC frame is about 128,000 68000 clocks. A fill loop of `MOVE.W D0,(A0)+` (8 clocks) and `DBRA` (10 while looping) is 18 clocks a word, about 645,000 clocks: 5 frames. A copy from work RAM, `MOVE.W (A1)+,(A0)+` (12) and `DBRA`, is 22, about 788,000: 6 frames. Unrolling with `MOVE.L D0,(A0)+` (12 clocks for two words) reaches 6 clocks a word, 215,000 clocks, 1.7 frames. The fastest fill is `MOVEM.L` of fourteen registers that all hold the fill value, to `-(A0)`: 8 + 8*n* clocks for *n* longwords, so 28 words in 120 clocks, 4.3 a word, about 154,000 clocks and 1.2 frames. The floor is the 4-clock bus cycle of each word, 143,360 clocks, 1.12 frames, and that is nearly reached [M68K-UM §8; [Instruction costs that matter in hot loops](../megadrive/m68k.md#instruction-costs-that-matter-in-hot-loops)]. So even the fastest fill the 68000 has takes more than a frame, and a copy, which cannot use the trick, takes several. The 68000 can patch the frame buffer, not redraw it.

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
| Word read from the cartridge through its cache-through address (`0x22000000`) | 8-17 |
| Word written to SDRAM | 2 |
| System register or communication port | 3 |
| Word written to the frame buffer | 3-5 |
| Word read from the frame buffer | 7-14 |

Every area is 16 bits wide, so a longword access to any area but SDRAM's reads is two of these: a longword from the cartridge through the cache-through address is 16-34 clocks, and a longword written to SDRAM is 4. An SDRAM read is the exception: it is one eight-word burst of 12 clocks whatever its size, so a longword read through `0x26000000` costs 12, not 24, and so does a cache line fill ([Bus state controller](../sh2/bsc.md#what-a-16-bit-bus-costs)). The cache is write-through, so every store goes to the bus whether or not the line is cached [SH7604 §7.11.2].

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
| Pixels written once | Frame buffer, with other work between the stores | 3 clocks a word while the write buffer has room; back-to-back stores fill it and pay 5 ([Living with bus contention](../patterns/bus.md#moving-data-without-paying-twice)) |
| Large areas of one colour | Auto fill | About 3 clocks a word after a 7-clock start, with the CPU free. A CPU must issue each fill of up to 256 words and keep off the buffer meanwhile, so it pays on long runs only ([Auto fill](vdp.md#auto-fill); [Knuckles' Chaotix](../patterns/bus.md#what-each-program-did)) |
| Palette changes | In blanking, or when PEN = 1 | Otherwise up to a line of waiting |
| 68000 code that must not slow down | Work RAM | The cartridge is shared with the SH-2s |

## In emulators

Neither common emulator charges these costs faithfully, so a profile taken in one shows where a program spends its instructions, not where it waits for memory.

- **Upstream PicoDrive** adds a small fixed charge to an SH-2's byte and word reads of the boot ROM, registers and palette, and nothing for any other access. It has no cache model, so a cache miss costs nothing either <span class="tag emulator">emulator</span> [PICODRIVE, pico/32x/memory.c]. The model of the manual's table and of the cache that Aerobiz Ultimate's measurements use was written for that project (U-093) and lives in the Virtua Racing Deluxe project's copy of PicoDrive, switched on with `VRD_SH2_TIMING=1` [VRD-NOTES, PicoDrive timing patch; AU-NOTES, ROADMAP.md U-093]. The model starts with the cache off and learns that it is on only from a write to CCR, which the copy forwards from the SH-2's register file. The boot ROMs are what normally write CCR, and PicoDrive's loader for them is compiled out; a build made to load them does so when told where the images are. Without them, a program that relies on them is charged as uncached throughout, and one project once concluded from such a run that its Slave never enabled its cache ([Mistakes the reference projects made](../patterns/cache.md#mistakes-the-reference-projects-made)). A program that writes CCR itself, as Aerobiz Ultimate's does, gets the cache, which is why the compression chapter's measurement sees 99.99% hits. On a console the boot ROMs do enable the cache, so for a program that relies on them the model errs towards too slow, the reverse of the other emulators' bias <span class="tag emulator">emulator</span> [VRD-NOTES, third_party/picodrive pico/32x/vrd_timing.c, sh2soc.c; AU-NOTES, ROADMAP.md U-093, HARDWARE_TESTS item 7]. The model charges a cartridge line fill as four bus cycles, not eight, so it is about half this book's 64-136 clocks ([discrepancy 48](../appendices/discrepancies.md)); it has no write buffer and keeps PicoDrive's fixed instruction costs ([Pipeline and cycle counting](../sh2/pipeline.md#in-emulators)).
- **Ares** adds a fixed number of clocks per access: 1 for registers and the boot ROM, 6 for the cartridge, 5 for a frame buffer read and 4 for a write, nothing for SDRAM. It makes the SH-2 wait while RV = 1 and while the VDP holds the palette, and it drops frame buffer accesses made while FEN = 1 rather than making them wait <span class="tag emulator">emulator</span> [ARES, md/m32x/bus-internal.cpp, io-internal.cpp].

Neither models the competition between the 68000 and the SH-2s for the cartridge, or the frame buffer's write buffer.

## What to take away

- Run SH-2 code from SDRAM and keep the hottest loop in on-chip RAM. The cartridge is up to eleven times slower per cache line.
- Never read the frame buffer if you can avoid it. Write it with other work between the stores, so the write buffer drains, and give long flat areas to auto fill.
- Use the communication ports for anything small that crosses between CPUs; they are the cheapest shared memory on the machine.
- Expect the 68000 to slow down when the SH-2s read the cartridge, and keep its critical loops in work RAM. An SH-2 loses at most about 12 clocks to a 68000 access in progress, and only when it asks while one is under way; that figure rests on an inference and is waiting for a console test ([Testing on real hardware](../howto/real-hardware.md#speed)).
- Do not trust an emulator's cycle counts for memory-bound code.

## Open questions

- How many wait states does the 68000 actually see on the cartridge while both SH-2s are drawing from SDRAM, and while one is reading the cartridge? Does an SH-2 see more than its 6-15 when the 68000 is using the cartridge, or is that loss already inside the range? Does the SH-2 keep the bus across the eight word cycles of a line fill, or give it up between words, as the 68000's 5-wait maximum suggests?
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
