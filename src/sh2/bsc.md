# Bus controller and memory timing

Everything an SH-2 reads or writes outside the chip goes through its **bus state controller** (BSC). The BSC decides how wide each memory area is, how many wait states (extra clocks per access) to add, how to drive the SDRAM, and how to share the bus with the other SH-2. On the 32X it is set up once by the boot ROM, and Sega forbids applications to touch it. This chapter shows the settings the boot ROM chooses and what they cost your code: where the clocks go on each access, and what happens when both SH-2s want the bus at once.

## Hands off

The BSC's seven registers sit at `0xFFFFFFE0-0xFFFFFFF8` [SH7604 §7.1.4]. Sega's list of things a 32X program must not do includes accessing that range, and accessing the standby control register at `0xFFFFFE91` <span class="tag manual">manual</span> [32X-HWM §5.3 p.87]. The SH7604 manual adds its own warnings: most BSC fields are meant to be written once after power-on and never changed, and nothing outside area 0 may be touched until they are set [SH7604 §7.2.1, §7.2.2, §7.2.4].

So treat the BSC as read-only knowledge, not as something to tune. "Access" includes reads. Bit 15 of BCR1 tells a CPU whether it is wired as master or slave [SH7604 §7.2.1], but code that needs to know which SH-2 it is running on should get that from its entry point instead: the user header gives the Master and the Slave separate start addresses [32X-HWM §5.1]. See [Boot, security code and initial program](../32x/boot.md#the-user-header).

## What the boot ROM sets

Both SH-2 boot ROMs program the BSC as their first real job, before touching anything outside area 0. Each copies the same seven longwords from a table into `0xFFFFFFE0` onwards (code at `0x0162` in both ROMs; table at `0x0348` in the Master's, `0x021C` in the Slave's) [VRD-NOTES, 32X BIOS dump]. Every value starts with `$A55A` because the BSC ignores a 32-bit write unless its upper half is that key [SH7604 §7.1.4].

| Register | Address | Value | What the value selects |
|----------|---------|-------|------------------------|
| BCR1 | `0xFFFFFFE0` | `$0001` | Area 2 ordinary memory, area 3 SDRAM. Big-endian, no burst ROM, full bus sharing (not partial-share) |
| BCR2 | `0xFFFFFFE4` | `$00A8` | Areas 1, 2 and 3 all 16 bits wide |
| WCR | `0xFFFFFFE8` | `$0055` | No idle cycles between areas. Areas 0-2: one programmed wait, and the external WAIT line honoured. Area 3: SDRAM CAS latency 2 |
| MCR | `0xFFFFFFEC` | `$0AB8` | SDRAM is one 2 Mbit chip (128K × 16), 16-bit bus. Bank active mode. Refresh on, auto-refresh. Refresh recovery 3 cycles, other SDRAM delays 1 cycle |
| RTCSR | `0xFFFFFFF0` | `$0008` | Refresh counter runs at the CPU clock ÷ 4. No interrupt |
| RTCNT | `0xFFFFFFF4` | `$0000` | Counter starts at 0 |
| RTCOR | `0xFFFFFFF8` | `$0059` | Refresh every 89 counts: 356 clocks, about 15.5 µs at 23.01 MHz |

Sources: values from [VRD-NOTES, 32X BIOS dump]; meanings from [SH7604 §7.2.1-7.2.7]. The long-wait fields in BCR1 are left at 3 waits, but WCR never selects them.

The Master then writes a word to `0xFFFF8446` (code at `0x0186`). A write into `0xFFFF8000-0xFFFFBFFF` sets the SDRAM chip's own mode register, and this address selects burst reads with single writes, a 16-bit bus and CAS latency 2, matching WCR [SH7604 §7.5.8; VRD-NOTES, 32X BIOS dump]. The Slave skips this step. That is the division Hitachi intended: the master-mode chip initialises and refreshes shared memory, and the slave keeps off it until told the memory is ready [SH7604 §7.10.5]. On the 32X the Slave waits for `M_OK` in a communication port before going near SDRAM (see [the Slave boot ROM](../32x/boot.md#the-slave-sh-2-boot-rom)).

### The four areas on the 32X

| Area | Addresses (cached) | 32X contents | Width | Cost per access, SH-2 clocks |
|------|--------------------|--------------|-------|------------------------------|
| CS0 | `0x00000000` | Boot ROM, system registers, VDP registers, palette | 16 bits, set by the mode pins (MD4 = 0, MD3 = 1) <span class="tag manual">manual</span> [32X-SVC §7-3; SH7604 §3.3, Table 3.9] | Boot ROM and system registers 3. VDP registers 7. Palette 7 or more |
| CS1 | `0x02000000` | Cartridge ROM | 16 bits | 8 to 17 |
| CS2 | `0x04000000` | Frame buffer and its overwrite image | 16 bits | Read 7 to 14, write 3 to 5 |
| CS3 | `0x06000000` | SDRAM | 16 bits | Read 12 per 16-byte burst, write 2 per word |

Sources: widths and contents from the boot ROM settings above and [32X-HWM §3.1 p.15]; costs from [32X-HWM §4.4 pp.77-78]. Sega gives costs as waits on top of the SH-2's 2-clock minimum bus cycle, so "1 wait" is 3 clocks. The table adds the 2 back in, except for SDRAM, which the manual gives as total clocks. Cache-through addresses (`0x2…`) reach the same areas at the same cost. See [the SH-2 memory map](../32x/architecture.md#what-the-32x-puts-there).

With idle cycles set to zero, accesses to different areas follow each other directly, except that the BSC always puts one idle clock between a read and a following write [SH7604 §7.9].

The programmed wait in WCR is the floor: every access to areas 0-2 takes at least 3 clocks. Anything slower is the 32X holding the SH-2's WAIT line until the data is ready, which is why the frame buffer and ROM figures are ranges. Sega's own note says the boot ROM leaves only the external wait in use, but the ROMs program one wait as well, and the manual's constant 1-wait figures for the boot ROM and system registers agree with the ROMs <span class="tag disputed">disputed</span> [32X-HWM §4.4 p.77; VRD-NOTES, 32X BIOS dump; [discrepancy 17](../appendices/discrepancies.md)].

## What a 16-bit bus costs

Every area of the 32X is 16 bits wide, but the SH-2 is a 32-bit CPU. The BSC splits each longword access into two word cycles, back to back [SH7604 §7.3.1]. Instruction fetches are always longwords [SH7604 §7.3.1, §7.11.2], so every fetch from outside the cache is two bus cycles for two instructions.

A cache miss is the expensive case. The cache always fills a whole 16-byte line, as four longword reads [SH7604 §7.11.2]:

- **From SDRAM** the line comes in one burst of eight words: 12 clocks [32X-HWM §4.4 p.78].
- **From anywhere else** it is eight separate word cycles. From cartridge ROM that is 8 × 8 to 8 × 17 clocks, so **64 to 136 clocks per line**, five to eleven times the SDRAM figure.

That gap is why the boot ROM copies your SH-2 program into SDRAM before starting it, and why the manual tells you to run from there [32X-HWM §2.2, SDRAM component].

Some typical costs, worked out from the manual's figures <span class="tag manual">manual</span> [32X-HWM §4.4 pp.77-78]:

| Access | Clocks on the bus |
|--------|-------------------|
| Cache hit, or on-chip RAM | None |
| Cache miss, code or data in SDRAM | 12 |
| Cache miss, code or data in cartridge ROM | 64 to 136 |
| Cache-through read from SDRAM, any size | 12 |
| Word write to SDRAM | 2. A longword is two words: 4 |
| Word read or write of a system register, such as a communication port | 3 |
| Word read from the frame buffer | 7 to 14 |

None of these has been measured on a console for this book. They are the manual's numbers added up.

## SDRAM: built for cache fills

The SDRAM reads only in bursts and writes only singly, which suits a write-through cache with 16-byte lines [SH7604 §7.5.1; 32X-HWM §4.4 p.78]. It has three consequences for code.

**A cache-through read costs a whole burst.** Reading one byte through `0x26000000` still makes the SDRAM deliver eight words; the BSC keeps the one it wanted and sits out the rest. A longword costs no more: on a 16-bit bus it takes the first two words of the same burst, not a second burst [SH7604 §7.5.4 p.164; 32X-HWM §4.4 p.78] <span class="tag manual">manual</span>. Anything shared between the SH-2s has to be read cache-through (see [the SH-2 memory map](../32x/architecture.md#what-the-32x-puts-there)), so:

- Read a shared structure once into registers and work from the copy, rather than re-reading fields.
- Do not spin on a flag in SDRAM. Every pass costs 12 clocks of the bus the other SH-2 needs. Poll a communication port instead (3 clocks), or wait for an interrupt. See [Communication](../32x/communication.md).
- When the DMA controller reads from SDRAM, move 16-byte units aligned on 16 bytes, or every transfer pays for a burst it mostly throws away [SH7604 §7.5.4]. See [DMA controller](dmac.md).

**Every write goes to the bus.** The cache is write-through: a store updates the cache line if present and always goes out to memory too [SH7604 §7.1.1, §7.11.2]. The BSC has a one-entry write buffer, so a single store does not stall the CPU, but a run of stores proceeds at bus speed [SH7604 §7.11.2]. To be sure a write has landed, for example an interrupt clear before `rte`, read the same address back [SH7604 §7.11.2; 32X-SUP2].

**Rows stay open.** The boot ROM sets bank active mode: the SDRAM keeps the last row it used open in each of its two banks. Another access to an open row can skip the step that opens it; an access to a different row in the same bank has to close the old row first, which costs extra [SH7604 §7.5.6]. Sega's manual still gives fixed figures for SDRAM reads and writes [32X-HWM §4.4 p.78], and whether same-row accesses are measurably faster on a 32X is not known.

### Refresh

The SDRAM forgets unless it is refreshed. The Master's BSC does it: with the boot ROM's settings, every 356 clocks it closes all rows, issues a refresh, and then sends nothing for 5 clocks, about 7 clocks in all [SH7604 §7.5.7; VRD-NOTES, 32X BIOS dump]. That is roughly 2% of the bus. Refresh has the highest priority on the chip [SH7604 §7.10], so an access that coincides with it waits. The Slave's copy of the refresh setting does nothing, because a chip in slave mode never refreshes [SH7604 §7.2.4, §7.10.2].

## Two SH-2s, one bus

The two SH-2s share one external bus, and on it sit the SDRAM, the frame buffer, the cartridge and all the 32X registers [32X-INTRO, dual SH2's; 32X-HWM §2.2, SH2 component]. What each CPU has to itself is on the chip: its cache, its on-chip RAM, and its peripherals at `0xFFFFFE00` and up, which it can use while the other CPU has the bus [SH7604 §7.10].

The 32X wires one SH-2 in the SH7604's master mode and the other in slave mode, which is where the names Master and Slave come from [32X-HWM §2.2, SH2 component]. In Hitachi's scheme [SH7604 §7.10, §7.10.1, §7.10.2] <span class="tag manual">manual</span>:

- The **Master** owns the bus by default.
- The **Slave** asks for the bus each time it needs an external access, and gives it back as soon as that access ends.
- The Master hands the bus over at the end of its current bus cycle. Inside each chip, refresh comes first, then an outside request, then DMA, then the CPU; read that way, a Slave request outranks the Master's own CPU and DMA. Sega's overview says the opposite: when both SH-2s go for the bus at once, the Master wins <span class="tag disputed">disputed</span> [32X-OV, Master access to frame buffers; [discrepancy 18](../appendices/discrepancies.md)].
- Some cycles are never split: a cache line fill, a 16-byte DMA transfer, the read and write of a `TAS.B`, and the two halves of a longword access to a 16-bit area.

What follows for code:

- **Cache hits run in parallel.** Two SH-2s working from their caches and on-chip RAM do not slow each other at all. Star Wars Arcade's Slave copies a 2 KB routine into its on-chip RAM and runs it from there, which keeps that work off the shared bus (see [Cache](cache.md#two-way-mode-2-kb-of-on-chip-ram)) [SWA, SH-2 code at `0x060008F0`].
- **One CPU's slow access blocks the other.** While the Master fills a cache line from ROM (up to 136 clocks) or reads the frame buffer, a Slave that misses its cache waits, even though it wants SDRAM, not ROM. The bus is one bus.
- **Two DMA channels on two CPUs fight.** If both SH-2s run DMA at once, one of them slows to a crawl until the other finishes <span class="tag manual">manual</span> [32X-HWM §5.3, DMA restrictions].
- **`TAS.B` holds the bus between its read and its write,** which is what makes it a lock on other systems. Sega forbids it on the 32X <span class="tag disputed">disputed</span> [32X-HWM §5.3 p.87; SH7604 §7.10; [discrepancy 12](../appendices/discrepancies.md)].

### Emulators do not show this

PicoDrive charges no wait states and does not model the two SH-2s taking turns on the bus <span class="tag emulator">emulator</span> [PICODRIVE, pico/32x/memory.c]. The Virtua Racing Deluxe project's opt-in timing patch adds the §4.4 wait states and a cache model, but treats each range as a fixed minimum or maximum rather than simulating the other CPU [VRD-NOTES, third_party/picodrive/pico/32x/vrd_timing.c].

Ares, which the Aerobiz Ultimate project uses as a second opinion, charges fixed costs per access: 6 clocks for a cartridge read, 5 for a frame buffer read and 4 for a write, 4 for the palette, 1 for the boot ROM and registers, and a flat 12 for each cache line fill on top of the reads it makes <span class="tag emulator">emulator</span> [ARES, md/m32x/bus-internal.cpp, md/m32x/io-internal.cpp, component/processor/sh2/sh7604/cache.cpp]. It runs each SH-2 on its own thread and keeps them in step every 10 clocks, so neither ever waits for the other's bus cycle. It stores the BSC registers but never reads them back for timing, and it does no refresh. Its own source notes that cartridge reads should stall while the 68000 is on the bus and do not [ARES, md/m32x/bus-internal.cpp].

None of the three can tell you what contention costs; the VRD project still lists SDRAM contention between the SH-2s as an open risk [VRD-NOTES, analysis/VR60_PHASE5F_SCOPING.md]. Treat any emulator profile of dual-SH-2 code as a best case. [Living with bus contention](../patterns/bus.md) covers ways to arrange work around it.

## Open questions

- How many clocks does a bus handover between the Master and the Slave cost on a 32X?
- Does bank active mode make same-row SDRAM accesses faster than the manual's fixed figures?
- How much of the cartridge ROM's 6-15 wait range comes from the 68000 competing for the ROM, and how much is fixed?
- Is refresh visible as an occasional stall in tight SDRAM loops?

## Sources

- [SH7604](../appendices/bibliography.md#sh7604): §3.3 Table 3.9, §7.1.4 registers, §7.2 register bits, §7.3.1 access sizes, §7.5 SDRAM interface, §7.9 idle cycles, §7.10 bus arbitration, §7.11.2 access from the CPU, write buffer
- [32X-HWM](../appendices/bibliography.md#32x-hwm): §2.2 SH2 and SDRAM components, §3.1 p.15 memory map, §4.4 pp.77-78 access timing, §5.1 user header, §5.3 p.87 restrictions
- [32X-INTRO](../appendices/bibliography.md#32x-intro): dual SH2's
- [32X-OV](../appendices/bibliography.md#32x-ov): Master access to frame buffers
- [32X-SUP2](../appendices/bibliography.md#32x-sup2): synchronising read-back
- [32X-SVC](../appendices/bibliography.md#32x-svc): §7-3, SH-2 mode pins
- [VRD-NOTES](../appendices/bibliography.md#vrd-notes): 32X BIOS dump (Master and Slave boot ROMs); analysis/VR60_PHASE5F_SCOPING.md; third_party/picodrive/pico/32x/vrd_timing.c
- [PICODRIVE](../appendices/bibliography.md#picodrive): pico/32x/memory.c
- [SWA](../appendices/bibliography.md#swa): SH-2 code at `0x060008F0`
- [ARES](../appendices/bibliography.md#ares): md/m32x/bus-internal.cpp, md/m32x/io-internal.cpp, md/m32x/sh7604.cpp; component/processor/sh2/sh7604/cache.cpp, io.cpp
