# Cache discipline

The [Cache](../sh2/cache.md) chapter explains how each SH-2's 4 KB cache works: lines, views, purging, two-way mode. This page is about choices. Every piece of code and data on a 32X is read through one of a few views, cached or cache-through, from SDRAM, the cartridge, the frame buffer or on-chip RAM, and the right view depends on who writes the data and how it is read. The cache-through view of any memory is its cached address plus `0x20000000`: SDRAM is `0x06000000` cached and `0x26000000` cache-through, the cartridge `0x02000000` and `0x22000000`, the frame buffer `0x04000000` and `0x24000000` [SH7604 §8.3; [How an address finds its line](../sh2/cache.md#how-an-address-finds-its-line)]. Below are the costs that decide it, a table of choices, and what the shipped games and the reference projects chose.

## What a read costs through each view

Worked out per byte from the manual's figures, in SH-2 clocks <span class="tag manual">manual</span> [32X-HWM §4.4 pp.77-78; [Bus state controller](../sh2/bsc.md#what-a-16-bit-bus-costs)]. A longword read is two word cycles everywhere except SDRAM, where it takes the first two words of a single burst [SH7604 §7.3.1, §7.5.4 p.164]:

| Where | Cached, first read of each 16-byte line | Cached, later reads | Cache-through, byte reads | Cache-through, word reads | Cache-through, longword reads |
|-------|------------------------------------------|---------------------|---------------------------|---------------------------|-------------------------------|
| SDRAM | 0.75 per byte (12 per line) | 0 | 12 per byte | 6 per byte | 3 per byte (12 per longword) |
| Cartridge ROM | 4-8.5 per byte (64-136 per line) | 0 | 8-17 per byte | 4-8.5 per byte | 4-8.5 per byte (16-34 per longword) |
| Frame buffer | 3.5-7 per byte, with conditions ([below](#frame-buffer-scratch)) | 0 | 7-14 per byte | 3.5-7 per byte | 3.5-7 per byte (14-28 per longword) |

Four rules follow. The third comes from the cache's replacement order rather than from the table:

- **For SDRAM, cache-through pays off only for data read once per update.** Every cache-through read costs a whole 12-clock burst, the same as filling a line, whether it reads a byte, a word or a longword. The alternative is to purge the line, one longword write that takes 2 clocks [SH7604 §8.4.7 p.224], and read it cached: one 12-clock fill, after which every read of that line is free. One read costs 12 clocks cache-through against 14; two reads from the same line cost 24 against 14. So as soon as any line is read twice between updates, purging wins. These figures leave out the instructions of the purge loop. A flag or counter that the other SH-2 may change between any two reads is read once per update every time, so 12 clocks beats 14. That is why [the table below](#choosing-a-view) keeps such values cache-through. What cache-through keeps in its favour is that it evicts nothing, where the fill pushes out whatever line held that slot.
- **For the cartridge, a word stream costs the same either way.** A line fill is eight word reads in a row, so reading words or longwords in order costs the same cached or not. The difference is that the cached read pushes 16 bytes of something else out of the cache. Byte-by-byte reads cost twice as much uncached.
- **A stream read cached takes at most one way of the cache**, as long as the program's other lines are in use. Hitachi calls the replacement pseudo-LRU, but the six bits kept for each entry record, for every pair of ways, which one was used last. On a miss the way replaced is the one older than the other three: exactly the least recently used way [SH7604 §8.4.5 pp.222-223, Tables 8.3 and 8.4]. A stream read in order comes back to the same entry once every 1 KB. By then, any line used since the stream's previous visit is newer than the stream's old line, so the old stream line is the one replaced. A line is evicted only if it went unused for that whole 1 KB of stream. In four-way mode, the stream can therefore cost at most a quarter of the cache, and in two-way mode half.
- **For scattered look-ups, cache-through wins** unless the same lines come back soon. A single word from the cartridge costs 8-17 clocks uncached, against a 64-136-clock line fill that also evicts something.

Every cache hit and every on-chip RAM access costs nothing on the bus, so it also takes nothing from the other SH-2 ([Two SH-2s, one bus](../sh2/bsc.md#two-sh-2s-one-bus)).

## Choosing a view

| What | View | Why |
|------|------|-----|
| Code | SDRAM, cached | 12 clocks per miss; the boot ROM copies it there ([Boot](../32x/boot.md#the-master-sh-2-boot-rom)) |
| One hot routine and its data, up to 2 KB | On-chip RAM, two-way mode | No bus at all |
| Data one SH-2 owns | SDRAM, cached | Hits are free |
| Flags, counters, positions shared between the SH-2s | Communication ports, or SDRAM cache-through | Always current; a port costs 3 clocks, SDRAM 12 |
| Larger data one SH-2 writes and the other reads | SDRAM, cached, purged by the reader after a "ready" flag | One purge per update instead of a burst per read ([Keeping the views in step](../sh2/cache.md#keeping-the-views-in-step)) |
| DMA destinations | Cache-through, or purge after the transfer | The DMA controller never updates the cache |
| Cartridge data read byte by byte, in order | Cached | One line fill serves 16 bytes |
| Cartridge data read in words, in order, once | Cache-through | Same cost, and the cache keeps its code |
| Large cartridge tables read at random | Cache-through | One access instead of a line |
| 32X registers and the frame buffer | Cache-through | Required for registers; other writers change the frame buffer |

## What the programs did

### Hot code

- **Most programs run from SDRAM**, where the boot ROM put them, and never touch the cache settings. Mortal Kombat II and After Burner Complete never write CCR on either CPU [MK2, SH-2 program; AB32X, SH-2 program].
- **Star Wars Arcade puts one routine in on-chip RAM.** Its Slave switches to two-way mode and copies 2 KB of code from the cartridge into the RAM: the routine that cuts each polygon into trapezoids, run once per polygon, plus the interrupt handler that draws them ([Two-way mode](../sh2/cache.md#two-way-mode-2-kb-of-on-chip-ram)). Before every picture it purges the whole cache and runs that code again. The purge leaves the RAM alone, which the game depends on [SWA, SH-2 code at `0x060007D0`, `0x060008F0`].
- **d32xr runs from the cartridge and moves only the hot code to SDRAM.** An attribute puts the drawers, the sound mixer, the division routine and the interrupt handlers in a section that the boot copy carries to SDRAM, each function aligned on a 16-byte line [D32XR, `doomdef.h`, `marshw.h`, `mars-ssf.ld`]. See [Code that runs from the cartridge](../howto/toolchain.md#code-that-runs-from-the-cartridge).
- **Motocross Championship runs everything from the cartridge**, and relies on the cache to hold its loops [MCX, user header and entry points]; see [Living with bus contention](bus.md#what-each-program-did).

Whatever the placement, two arrays or loops whose addresses differ by a multiple of 1 KB compete for the same four cache slots ([How an address finds its line](../sh2/cache.md#how-an-address-finds-its-line)). Keep hot data on 16-byte boundaries and avoid laying several hot tables out on 1 KB boundaries.

### Sharing between the two SH-2s

| Program | What the two SH-2s share | How they keep it consistent |
|---------|--------------------------|-----------------------------|
| Mortal Kombat II | Nothing in SDRAM | Nothing to do. The Slave plays sound in its own memory [MK2, SH-2 program] |
| After Burner Complete | Nothing in SDRAM | Nothing to do. The Slave mixes sound from its own memory [AB32X, SH-2 program] |
| Star Wars Arcade | Double-buffered polygon lists in SDRAM | The Master fills one list while the Slave reads the other, and the Slave purges its whole cache before reading each one, once per picture [SWA, SH-2 code at `0x06000E96`-`0x06000ECE`, `0x060007D0`] |
| d32xr | Many per-picture structures; textures; ring buffers | Per-picture structures in spare frame buffer memory, read cache-through, so no purges; purges of just the lines of textures and list heads before the second CPU reads them; ring buffer positions cache-through, each on its own line [D32XR, `marsnew.c`, `r_main.c`, `r_phase6.c`, `r_phase7.c`, `mars_ringbuf.h`] |

The two sound-on-the-Slave games avoid the problem entirely, and that is the cheapest answer when the work splits that way. Star Wars Arcade's full purge before each picture is simple and safe, but it also throws away the Slave's own cached code and data, which then have to come back. It can afford that because the Slave's busiest code sits in on-chip RAM, which the purge does not touch. The cost has a ceiling. In two-way mode the Slave's cache holds 128 lines. Its sound decoder reads the sample stream and a 1 KB codebook through the cached cartridge view: in a PicoDrive run the pointers were `0x0221EExx` and `0x0221EA80` [SWA, SH-2 code at `0x060009CC`-`0x06000A2C`, `0x06000800`-`0x06000828`] <span class="tag emulator">emulator</span>. The stream is read once in any case, but the codebook's 64 lines are reused, and after a purge each comes back from the cartridge at 64 to 136 clocks. Even if the other 64 lines were all needed again from SDRAM at 12 clocks each, a purge costs at most about 64 × 136 + 64 × 12 ≈ 9,500 clocks, which is 2.5% of the 384,000 clocks in a frame. That share assumes a purge at every display refresh, 60 times a second, which is the worst case. The purge actually comes once per picture drawn ([the drawing sequence](case-study-starwars.md#one-frame-from-game-logic-to-the-screen)) [SWA, SH-2 code at `0x060007D0`], and in two PicoDrive runs of play the game drew 32.5 and 34.2 pictures a second <span class="tag emulator">emulator</span> ([Where the time goes](case-study-starwars.md#where-the-time-goes)). At those rates the ceiling is 9,500 × 32.5 to 9,500 × 34.2, about 309,000-325,000 of the Slave's 23,040,000 clocks a second (60 × 384,000): about 1.3-1.4%. Purging only the lists would save most of it; how much depends on how much of the codebook the cache would have kept anyway, which only a cache-accurate measurement can tell. d32xr does the most work per item and pays the least per picture.

Writes need no care at all when the two CPUs write different parts of the frame buffer: the frame buffer is used cache-through, so two SH-2s drawing disjoint rows only have to agree on when the picture is finished <span class="tag emulator">emulator</span> [S32X-SKILL, architecture].

### Frame buffer scratch

Frame buffer memory past the lines on screen is the one large area both SH-2s can use without purges, because they reach it cache-through. d32xr carves its per-picture structures out of it: visible planes, wall lists, clipping arrays, column caches [D32XR, `marsnew.c`, `r_main.c`]. The price is the frame buffer's speed: 7-14 clocks per word read, against nothing for a cache hit.

d32xr also reads one kind of frame buffer data through the cache: lookup tables for the current view, which it writes into both buffers so that either one reads the same ([A safe use of the cached frame buffer](../sh2/cache.md#a-safe-use-of-the-cached-frame-buffer)) [D32XR, `r_data.c`].

### Data from outside

- **Streams from the cartridge.** Aerobiz Ultimate's decompressor reads its input byte by byte through the cached cartridge view. In the project's timing model that held a 99.99% hit rate, with misses close to the one-per-16-bytes minimum <span class="tag emulator">emulator</span> [AU-NOTES, `disasm/sh2/master/lz.c`; ROADMAP M5]. The Ecco CinePak demo reads its movie through the cache-through view instead, also a byte at a time, which by the table above costs about twice the bus time but leaves its decoder's code and colour tables in the cache [ECCO, SH-2 code at `0x060001D8`, `0x060002EA`]. Its SH-2 program never writes CCR, so it runs in the boot ROM's four-way mode [ECCO, SH-2 program, checked statically and at run time]. Read cached, the movie would have taken at most a quarter of that cache ([above](#what-a-read-costs-through-each-view)), provided the decoder used each of its other lines at least once per 1 KB of movie. So the demo paid about twice the bus time to protect at most a quarter of its cache.
- **Large lookup tables.** d32xr reads its big trigonometry tables in the cartridge through the cache-through view, so random look-ups cost one access each and evict nothing [D32XR, `tables.c`].
- **DMA.** d32xr points its FIFO DMA at a cache-through destination, so nothing needs purging afterwards [D32XR, `marshw.c`].

## Mistakes the reference projects made

- **The wrong region in a cache-through address.** The VRD project's design for sharing work between the SH-2s put its parameter block at `0x2203E000`. That is the cartridge's cache-through view, read only. SDRAM's would have been `0x2603E000` ([the views](#cache-discipline)). The block it relied on never existed <span class="tag emulator">emulator</span> [VRD-NOTES, KNOWN_ISSUES].
- **A conclusion drawn without the boot ROM.** Aerobiz Ultimate's timing model showed the Slave's idle loop paying an SDRAM burst on every fetch, and enabling the cache explicitly cut the Slave's wait cycles about 295-fold. The project read this as the Slave never enabling its cache. But the boot ROMs do enable it ([What the boot ROM leaves you](../sh2/cache.md#what-the-boot-rom-leaves-you)), and PicoDrive never runs them. Its loader is compiled out, and its own start-up code does not write CCR [PICODRIVE, `platform/common/emu.c`, `pico/32x/32x.c`]. Rerun with the boot ROMs loaded, the project's build from before the fix gives the answer. Without them, the Slave made no cached accesses and was charged 139 million wait cycles; with them it missed 9 times and was charged 30,029 <span class="tag emulator">emulator</span> [AU-NOTES, zoom test; VRD-NOTES, `third_party/picodrive/pico/32x/vrd_timing.c`; method in `notes/games/au/slave-cache.md`]. The saving was an emulator artefact, not a hardware result. The project's code now enables the cache itself, which costs nothing [AU-NOTES, HISTORY; HARDWARE_TESTS item 7].
- **Testing coherence where there is no cache.** PicoDrive has no cache, so a missing purge never shows there ([In emulators](../sh2/cache.md#in-emulators)). The hit counts above come from the VRD project's timing model, which only does the bookkeeping. It keeps each line's tag, valid bit and age to decide hits and misses and to charge each fill. It stores no data, so every read still returns current memory, and it ignores single-line purges [VRD-NOTES, `third_party/picodrive/pico/32x/vrd_timing.c`]. Test shared data in Ares, with its interpreter forced ([Running ares without a screen](../howto/emulator-testing.md#running-ares-without-a-screen)).

## What to take away

- Pick each view by [the rules above](#what-a-read-costs-through-each-view): who writes the data, and how it is read.
- Share as little as possible between the SH-2s. When they must share, a full purge before each use is simplest, per-line purges are cheapest, and frame buffer scratch needs none.
- Check the region bits of every cache-through address.
- Test coherence in an emulator that has a cache.

## Open questions

- How much of Star Wars Arcade's purge ceiling of about 9,500 clocks a picture is real? Answering it needs a cache-accurate emulator or a console, to count how many codebook lines survive from one picture to the next without the purge. The ceiling is likely generous, because the Slave's own reads of the polygon records would evict much of the codebook anyway ([the evidence](case-study-starwars.md#where-the-time-goes)).
- How much bus time do the two SH-2s actually save each other by staying in their caches, measured on a console?

## Sources

- [32X-HWM](../appendices/bibliography.md#32x-hwm): §4.4 pp.77-78
- [SWA](../appendices/bibliography.md#swa): SH-2 code at `0x060007D0`, `0x06000800`-`0x06000828`, `0x060008AC`-`0x060008CA`, `0x060008F0`, `0x0600095C`, `0x060009CC`-`0x06000A2C`, `0x06000E96`-`0x06000ECE`; on-chip code at `0xC000000A`-`0xC0000040`
- [SH7604](../appendices/bibliography.md#sh7604): §7.3.1 longword accesses; §7.5.4 p.164 single reads; §8.3 address areas; §8.4.5 pp.222-223 replacement, Tables 8.3-8.4; §8.4.7 p.224 associative purge
- [MK2](../appendices/bibliography.md#mk2), [AB32X](../appendices/bibliography.md#ab32x): SH-2 programs
- [MCX](../appendices/bibliography.md#mcx): user header and entry points
- [ECCO](../appendices/bibliography.md#ecco): SH-2 code at `0x060001D8`, `0x060002EA`; SH-2 program (no CCR write; forms checked in the bibliography entry)
- [D32XR](../appendices/bibliography.md#d32xr): `doomdef.h`, `marshw.h`, `marshw.c`, `mars-ssf.ld`, `marsnew.c`, `r_main.c`, `r_data.c`, `r_phase6.c`, `r_phase7.c`, `mars_ringbuf.h`, `tables.c`
- [AU-NOTES](../appendices/bibliography.md#au-notes): `disasm/sh2/master/lz.c`; ROADMAP M5; HISTORY; HARDWARE_TESTS; zoom test from before the Slave cache fix
- [VRD-NOTES](../appendices/bibliography.md#vrd-notes): KNOWN_ISSUES; `third_party/picodrive/pico/32x/vrd_timing.c`
- [PICODRIVE](../appendices/bibliography.md#picodrive): `platform/common/emu.c`, `pico/32x/32x.c`
- [S32X-SKILL](../appendices/bibliography.md#s32x-skill): architecture
