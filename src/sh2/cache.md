# Cache

Each SH-2 has 4 KB of cache, shared between instructions and data. On the 32X it decides most of the CPU's speed. A miss to SDRAM costs 12 clocks and a miss to cartridge ROM up to 136 (see [Bus controller and memory timing](bsc.md)). A hit costs nothing, and it doesn't touch the bus the two SH-2s share. The catch is that the cache never notices anyone else's writes: not the other SH-2's, not the DMA controller's, not the 32X hardware's. This chapter covers how the cache is organised, the control register, what the boot ROM leaves you with, how to keep the two CPUs' views of memory in step, and the two-way mode that turns half the cache into 2 KB of fast RAM.

## At a glance

| | |
|---|---|
| Size | 4 KB: 64 entries × 4 ways × 16-byte lines |
| Contents | Instructions and data mixed |
| Replacement | Least recently used, exactly: six bits per entry, one for each pair of ways, record which of the two was used last, and a miss replaces the way older than the other three. Hitachi calls it pseudo-LRU |
| Hit | No wait. One access per clock, pipelined with the CPU |
| Read miss | The whole 16-byte line is read, as four longwords; the one the CPU asked for arrives last |
| Write | Write-through: every write goes to memory. A write that hits also updates the line; a write that misses does not load one |
| Control register (CCR) | `0xFFFFFE92`, one byte |
| When your code starts | Enabled, four-way, nothing from SDRAM in it |

Sources: [SH7604 §8.1, §8.2, §8.4.1, §8.4.2, §8.4.5 pp.222-223 with Tables 8.3-8.4; VRD-NOTES, 32X BIOS dump].

## How an address finds its line

The cache splits an address into three parts [SH7604 §8.1]:

| Bits | Part | Use |
|------|------|-----|
| 31-29 | Area | Picks the cache behaviour (next table) |
| 28-10 | Tag | Stored with the line; compared on every access |
| 9-4 | Entry | Which of the 64 entries the line goes in |
| 3-0 | Byte | Position within the 16-byte line |

Each entry holds up to four lines, one per way. Each way is 64 × 16 bytes = 1 KB, so **addresses 1 KB apart compete for the same four slots**. A loop that walks five or more streams whose addresses differ by a multiple of 1 KB evicts its own lines on every pass, however small each stream is. Some examples: five arrays that each start on a 1 KB boundary, or a table 1,024 bytes wide read down a column. In two-way mode only two slots are left per entry, so two such streams are enough. Offsetting the arrays by 16, 32 or 48 bytes moves them to different entries and ends the fight.

The top three bits choose what an access does [SH7604 §8.3]:

| Bits 31-29 | Addresses | What an access does |
|------------|-----------|---------------------|
| `000` | `0x00000000-0x1FFFFFFF` | Normal memory, through the cache when CE = 1 |
| `001` | `0x20000000-0x3FFFFFFF` | The same memory, bypassing the cache (cache-through) |
| `010` | `0x40000000-0x5FFFFFFF` | Associative purge: a write throws away one line |
| `011` | `0x60000000-0x7FFFFFFF` | The cache's tag array, read and written directly |
| `110` | `0xC0000000-0xC0000FFF` | The cache's data array; on-chip RAM in two-way mode |
| `111` | `0xE0000000-0xFFFFFFFF` | On-chip peripherals; never cached |

[The SH-2 memory map](../32x/architecture.md#what-the-32x-puts-there) shows where the 32X puts its memory in the first two areas.

## The control register

| Bit | Name | Meaning |
|-----|------|---------|
| 7-6 | W1-W0 | Which way the tag array window at `0x60000000` shows |
| 5 | | Reserved, write 0 |
| 4 | CP | Write 1 to purge: clears every line's valid bit and all replacement history. Reads 0 |
| 3 | TW | 0 = four-way cache. 1 = two-way cache plus 2 KB of RAM |
| 2 | OD | 1 = data misses do not load lines (data hits still work) |
| 1 | ID | 1 = instruction misses do not load lines |
| 0 | CE | 1 = cache on |

Source: [SH7604 §8.2 pp.214-215]. All bits are 0 after reset.

Change CCR only while the cache is off: write a value with CE = 0 first, then the value you want. The CPU keeps fetching instructions from the cache during the write, and Hitachi does not guarantee what happens if CCR changes under it <span class="tag manual">manual</span> [SH7604 §8.4.6, §8.5.5]. Sega's list of forbidden registers covers the bus controller and the standby register, not CCR. Programs may set the cache up as they like [32X-HWM §5.3 p.87].

Two slips in Hitachi's own manual, both in the scan: §8.4.6 says a purge is done by writing **0** to CP, where the bit description, §8.5.1 and §8.5.2 all say 1. And the initialisation example in §8.5.1 contains two instructions that do not exist (`MOV.B #R0,@R1` and `MOV.B R0,R1`; the intent is `MOV.B R0,@R1` both times) [SH7604 pp.224, 226].

## What the boot ROM leaves you

Both SH-2 boot ROMs, once released by the 68000, clear the standby control register and then write `$11` to CCR: purge and enable, four-way mode [VRD-NOTES, 32X BIOS dump, code at `0x01B4` in the Master's ROM and `0x0198` in the Slave's]. The cache was off after reset, so this single write follows Hitachi's rule.

The Master then copies your SH-2 program from the cartridge to SDRAM. It reads the cartridge through the cache-through alias and writes SDRAM through the cached one. Writes that miss do not load lines, and the cache has just been purged, so no stale copy of SDRAM can be left behind. The Slave never touches SDRAM before jumping to your code [VRD-NOTES, 32X BIOS dump]. Both CPUs therefore start with the cache on and holding nothing from SDRAM.

Many programs redo the purge anyway, which costs nothing: d32xr writes `$10` (purge, cache off) before clearing its uninitialised data and `$11` before `main` [D32XR, crt0.s]. Aerobiz Ultimate writes 0, then `$10`, then `$01` [AU-NOTES, disasm/sh2/master/main.s].

## Keeping the views in step

The SH7604 has no snooping: nothing tells a CPU's cache that memory changed behind it [SH7604 §8.5.2, §8.5.3]. On the 32X three things change memory behind a CPU's back:

- **The other SH-2**, writing SDRAM or the frame buffer.
- **The DMA controller**, including its own CPU's. DMA writes go to memory only, never to the cache [SH7604 §7.11.2, §8.5.2].
- **The 32X hardware and the 68000**: registers, the communication ports, the frame buffer.

The write-through design gives two guarantees that make this manageable. Your own writes always reach memory, after at most the one-entry write buffer (see [the write buffer](bsc.md#sdram-built-for-cache-fills)). And a line in the cache is never newer than memory, so **purging can never lose data**; the worst it does is cost a refill. The only danger is a reader holding an old copy.

The simplest way of all is to give each CPU its own memory and never share it. Mortal Kombat II does this: its Slave only plays sound and keeps its few variables in a range the Master never touches, and everything either CPU needs from outside arrives through the ports or the cartridge. Neither CPU ever purges a line, and neither needs to [MK2, SH-2 program]. After Burner Complete is laid out the same way: the Slave's code, its sound data and its stack fill the start and the top of SDRAM, and no address in the Master's code points into them except the Master's own stack top [AB32X, SH-2 program]. When the CPUs do share data, the ways to deal with it, from simplest to fastest:

1. **Registers and communication ports: always cache-through.** Sega requires it for the system and VDP registers [32X-HWM §4.1 p.74, cache-through access]. See [the SH-2 memory map](../32x/architecture.md#what-the-32x-puts-there).
2. **Small shared values, such as flags, counters and ring buffer positions: cache-through on every access.** Each read is a bus access (3 clocks for a communication port, 12 for SDRAM), but it is always current. d32xr's ring buffer between the SH-2s reads and writes its two position words only through the cache-through alias, and gives each its own 16-byte line [D32XR, mars_ringbuf.h].
3. **Large shared data, written rarely and read a lot: read it cached, and purge before reading.** This is the scheme Hitachi recommends: keep only the "ready" flags cache-through, keep the data itself cached, and purge the data's lines once, after the flag says new data is there and before the first read [SH7604 §8.5.3]. d32xr purges the texture and flat data lines before its second CPU draws with them, and the visplane list heads before walking the lists [D32XR, r_phase6.c, r_phase7.c].
4. **DMA destinations: purge after the transfer, or never cache them.** Either purge the destination's lines once the DMA has finished, or have the DMA write the cache-through address and read the data the same way. d32xr gives its FIFO DMA a cache-through destination [D32XR, marshw.c]. Hitachi also suggests setting OD, which makes the cache hold instructions only [SH7604 §8.5.2]; no project we have read does.

Two habits make all four easier:

- **Align shared data to 16 bytes, and pad it to a multiple of 16.** Fills and purges work on whole lines. Data that starts mid-line shares that line with whatever sits before it, and a buffer that does not start on a line boundary covers one more line than its size suggests. d32xr purges `(size + 31) / 16` lines for exactly that reason, and aligns its level data to 16 bytes as it loads it [D32XR, r_phase6.c, p_setup.c].
- **Do not let data written by one CPU share a line with data the other CPU reads cached.** The reader picks up the whole line when it reads its own neighbouring data, and keeps the stale copy of the rest.

`TAS.B` always reads memory directly, bypassing the cache, which makes it a lock on other systems [SH7604 §8.4.4]. Sega forbids it on the 32X <span class="tag disputed">disputed</span> ([discrepancy 12](../appendices/discrepancies.md)).

### A safe use of the cached frame buffer

The frame buffer can be read through its cached alias at `0x04000000` too, and d32xr does it for lookup tables kept in spare frame buffer memory [D32XR, r_data.c]. There is a catch: that address always shows the buffer *not* on screen, and the two swap every frame (see [The 32X VDP](../32x/vdp.md)). After a swap, the cache still holds lines read from the other buffer. d32xr builds its tables on two frames in a row, once into each buffer, so a line from either buffer holds the same bytes [D32XR, r_main.c, p_tick.c]. Read-only data stored identically in both buffers can be cached; anything else in the frame buffer must be read cache-through.

## Purging

**One line.** Write any longword to the line's address with `0x40000000` added. If that address is in the cache, in any way, its line is thrown away; if not, nothing happens. Each purge takes 2 clocks, so 256 bytes takes 16 writes [SH7604 §8.4.7]. Use longword writes.

Start from the cached address. `0x06001230` purges through `0x46001230`. Starting from the cache-through alias goes wrong: `0x26001230` with `0x40000000` added is `0x66001230`, which is in the tag array area, and the write changes the tags of a cache entry instead of purging anything [SH7604 §8.3, §8.4.9]. Clear bit 29 first: `(address & 0x1FFFFFFF) | 0x40000000`. marsdev's helper ORs `0x40000000` into the address it is given, and d32xr's adds it, so both expect the cached form [MARSDEV, examples/32x-skeleton/sh_src/mars_start.s; D32XR, 32x.h].

**Everything.** Write 0 to CCR, then `$11` (or `$19` in two-way mode). The purge itself takes one clock [SH7604 §8.4.6]; the cost comes afterwards, as every line the program uses is fetched again, at 12 clocks each from SDRAM. d32xr's whole-cache purge is exactly these two writes [D32XR, 32x.h]. Hitachi's advice is to purge single lines for small updates and the whole cache when the update is large [SH7604 §8.5.3]. Purging one line costs 2 clocks plus loop overhead, while a full purge costs a refill of up to 256 lines; so single lines win until the region approaches a sizeable part of the 4 KB.

## Two-way mode: 2 KB of on-chip RAM

Setting TW splits the cache in half. Ways 2 and 3 stay a two-way cache of 2 KB. Ways 0 and 1 become 2 KB of RAM at `0xC0000000-0xC00007FF` [SH7604 §8.2, §8.5.4]. With the cache turned off altogether, all 4 KB at `0xC0000000-0xC0000FFF` is RAM [SH7604 §8.4.8]. Sega's overview presents the 2 KB + 2 KB mode as the one for tight loops: graphics routines, geometry, sorting [32X-OV, dual SH2's].

What the RAM is like [SH7604 §8.4.8, §7.11.2]:

- **One clock per access**, byte, word or longword, reads and writes alike.
- **It does not use the external bus**, so it runs at full speed while the other SH-2 or a DMA transfer has the bus.
- **Each CPU has its own.** The other SH-2 cannot see it, and the DMA controller cannot reach it; copy into it with the CPU.
- **Code can run from it.**

Setting it up: purge with the cache off, then turn the cache on with TW set. The purge clears the valid bits of ways 0 and 1, which Hitachi requires before two-way operation, because the tags of all four ways are still compared [SH7604 §8.4.5]. Star Wars Arcade's Slave does it in two writes: CCR = 0, then CCR = `$19` (purge, two-way, on) [SWA, SH-2 code at `0x060008F0`].

**A full purge keeps the RAM.** Hitachi says CP "initializes" the cache and the RAM, but lists only the valid and replacement bits as cleared [SH7604 §8.5.4]. Star Wars Arcade settles it in practice. Its Slave copies its on-chip routine in once, at start-up. Every frame, the command that starts drawing writes CCR `$08` and then `$19`, a full purge in two-way mode, and goes straight on to call the on-chip code. The one command that copies the code in again (`$04`) is never sent by the 68000 [SWA, SH-2 code at `0x0600073C`, `0x060007A4`, `0x060007D0`, `0x060008F0`; 68000 command sender calls at `$0869E2`-`$086FE8`]. A purge that cleared the RAM would crash the game on its first frame.

Do not write `0xC0000000` with the cache in four-way mode. That area is then the data of lines in use, and writing it silently changes what the CPU reads for some other address [SH7604 §8.4.8].

The price is a cache half the size with half the ways, so everything else misses more often. It pays when one hot routine and its working data fit in 2 KB. Star Wars Arcade's Slave, right after switching to two-way mode, copies 2 KB of code from the cartridge into the on-chip RAM, filling it. It then calls that code once for each entry of a list it walks [SWA, SH-2 code at `0x060008AC`, `0x060008F0`]. Its Master stays in the boot ROM's four-way mode. d32xr defines the TW bit but never sets it [D32XR, 32x.h]. Mortal Kombat II never writes CCR on either CPU, so both run in the boot ROM's four-way mode throughout [MK2, SH-2 program], and neither does After Burner Complete [AB32X, SH-2 program].

## In emulators

- **PicoDrive has no cache.** Every access reads memory directly, so a missing purge never shows: code that would read stale data on a console works in PicoDrive <span class="tag emulator">emulator</span> [VRD-NOTES, third_party/picodrive/pico/32x/vrd_timing.c]. S32X-SKILL warns about the same thing: coherency bugs that appear on hardware and not in some emulators [S32X-SKILL, architecture.md].
- **The Virtua Racing Deluxe project's timing patch** adds a cache to PicoDrive for timing only. It tracks hits and misses but stores no data, so it cannot show stale reads either [VRD-NOTES, third_party/picodrive/pico/32x/vrd_timing.c].
- **Ares keeps real cache lines** for data accesses, so a missing purge does return stale data there, and it charges 12 clocks per fill on top of the reads <span class="tag emulator">emulator</span> [ARES, component/processor/sh2/sh7604/cache.cpp, bus.cpp]. The Aerobiz Ultimate project found that its default recompiler skips the cache model for timing, and uses the interpreter (`General/ForceInterpreter`) for anything cache-related [AU-NOTES, HARDWARE_TESTS.md].

Use Ares, in interpreter mode, to test that shared data is purged where it should be.

## Open questions

- How long does a full refill take in practice after a whole-cache purge in a real game loop?

## Sources

- [SH7604](../appendices/bibliography.md#sh7604): §8.1-8.5 (pp.214-228), including §8.4.5 pp.222-223 and Tables 8.3-8.4 on replacement; §7.11.2
- [32X-HWM](../appendices/bibliography.md#32x-hwm): §4.1 p.74 cache-through access, §5.3 p.87
- [32X-OV](../appendices/bibliography.md#32x-ov): dual SH2's
- [VRD-NOTES](../appendices/bibliography.md#vrd-notes): 32X BIOS dump; third_party/picodrive/pico/32x/vrd_timing.c
- [SWA](../appendices/bibliography.md#swa): SH-2 code at `0x060008AC`, `0x060008F0`
- [AU-NOTES](../appendices/bibliography.md#au-notes): disasm/sh2/master/main.s; HARDWARE_TESTS.md
- [D32XR](../appendices/bibliography.md#d32xr): crt0.s, 32x.h, mars_ringbuf.h, marshw.c, r_data.c, r_main.c, p_tick.c, p_setup.c, r_phase6.c, r_phase7.c
- [MARSDEV](../appendices/bibliography.md#marsdev): examples/32x-skeleton/sh_src/mars_start.s
- [S32X-SKILL](../appendices/bibliography.md#s32x-skill): architecture.md
- [MK2](../appendices/bibliography.md#mk2): SH-2 program
- [AB32X](../appendices/bibliography.md#ab32x): SH-2 program
- [ARES](../appendices/bibliography.md#ares): component/processor/sh2/sh7604/cache.cpp, bus.cpp
