# Harvested techniques: patterns/cache.md

Target: `patterns/cache.md`. 10 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from S32X-SKILL -->
### Cache-line-aligned hot routines in SDRAM
- Source: S32X-SKILL, references/architecture.md:27-32; references/optimization.md:52-55, 290-291
- What it does and why it is clever: d32xr's `ATTR_DATA_CACHE_ALIGN` = `section(".sdata"), aligned(16), optimize("O1")`. It puts inner loops in SDRAM (copied at boot) on 16-byte cache-line boundaries, so they run cached and don't straddle lines. The pinned optimisation level stops LTO from changing their timing.
- Key numbers: 16-byte alignment.
- Target chapter: sh2/cache.md
- Evidence: d32xr, wave-rider-gp.

<!-- from S32X-SKILL -->
### Cross-core coherency: cache-through or explicit purge
- Source: S32X-SKILL, references/architecture.md:152-160, 211-215; references/audio.md:138-140
- What it does and why it is clever: SDRAM at `0x06000000` is cached separately on each SH-2. Anything one core writes for the other (audio command blocks, job descriptors) must be read through the uncached alias or cleared with `Mars_ClearCacheLine/ClearCache`. Otherwise the slave mixes stale commands; this fails on hardware but not in some emulators.
- Key numbers: —
- Target chapter: patterns/cache.md
- Evidence: Described; hardware-only bug class.

<!-- from S32X-SKILL -->
### Disjoint rows of the uncached framebuffer need no cache work
- Source: S32X-SKILL, references/architecture.md:154-157, 227-230
- What it does and why it is clever: Because the framebuffer bypasses the cache, two cores writing different rows (the slave fills the sky, the master draws the rest) need no synchronisation beyond the job ack.
- Key numbers: —
- Target chapter: patterns/cache.md
- Evidence: racing-circuit-32x ("sky on the slave over disjoint rows").

---

<!-- from D32XR -->
### Hot code in SDRAM, compiled for size
- Source: D32XR, doomdef.h:65-72, mars-ssf.ld:104-118 (licence: id limited-use; the .ld has no header)
- What it does and why it is clever: The macro `ATTR_DATA_CACHE_ALIGN` puts a function in section `.sdata` and compiles it with `-Os`. The linker places `.sdata` inside `.data`, so crt0 copies it from ROM into SDRAM at boot. Every inner loop (BSP, seg loop, plane loop, the drawers, the mixer, FixedDiv, blockmap iterators) therefore runs from SDRAM rather than the slower cartridge ROM. Small code keeps the working set inside the 4 KB cache.
- Key numbers: SDRAM 0x06000000, 0x3F800 usable; the two stacks sit at the top.
- Target chapter: patterns/cache.md
- Evidence: code only

<!-- from D32XR -->
### Caching policy chosen per table
- Source: D32XR, tables.c:2589-2595, r_data.c:619-625, r_main.c:887-922 (licence: id limited-use)
- What it does and why it is clever: The large ROM trig tables (finesine, finetangent, tantoangle) are always read through the cache-through mirror (address + 0x20000000), so random lookups do not evict the hot working set. The small per-viewport tables (viewangletox, distscale, yslope, xtoviewangle) live in framebuffer scratch and are deliberately made cacheable by clearing that bit (`& ~0x20000000`, "enable caching for LUTs"). Map arrays are also aligned to 16-byte cache lines on load (p_setup.c:73-74 and others).
- Key numbers: 16-byte cache lines; uncached alias = +0x20000000.
- Target chapter: patterns/cache.md
- Evidence: code only

<!-- from D32XR -->
### Per-CPU column cache for composite textures
- Source: D32XR, r_phase6.c:126-147, r_data.c:936-1035, r_main.c:915-926 (licence: id limited-use)
- What it does and why it is clever: Multi-patch wall textures ("decals") are not stored pre-composited. When a column is first needed, R_CompositeColumn builds it into a small per-CPU buffer, and `lastcol` remembers which column is in there, so a wall that repeats a column in adjacent screen columns does not rebuild it. Later decals are written through the framebuffer overwrite alias (see 32x/vdp.md), so their transparent zero bytes need no per-pixel test.
- Key numbers: MAX_COLUMN_LENGTH 128; 2 textures x 128 bytes per CPU (x2 with mips); up to 3 decals per texture (`decals & 3`).
- Target chapter: patterns/cache.md
- Evidence: code only

---

<!-- from VRD/AU/MARSDEV -->
### Cache-through alias discipline, and why region bits matter
- Source: VRD-NOTES, KNOWN_ISSUES.md:269-281; analysis/COMM_REGISTERS_HARDWARE_ANALYSIS.md:199-212; AU-NOTES, KNOWN_ISSUES.md:210-214
- What it does and why it is clever: The SH7604 cache does not snoop. Anything another bus master changes (COMM, VDP registers, framebuffer, data shared between SH-2s or written by DMA) must be read through the `$2xxxxxxx` cache-through mirror. The region bits still matter: `$22…` is cartridge ROM and `$26…` is SDRAM. VRD's parallel-processing design put its parameter block at `$2203E000`, which is ROM, so the block never existed.
- Key numbers: COMM base `$20004020`; SDRAM cache-through `$26000000-$2603FFFF`.
- Target chapter: patterns/cache.md
- Evidence: manual. The VRD v4.0 parallel path is invalidated.

<!-- from VRD/AU/MARSDEV -->
### Read streaming input through the cached alias
- Source: AU-NOTES, disasm/sh2/master/lz.c:36-45; disasm/32x/sh2_lz.asm:38-44
- What it does and why it is clever: The compressed stream is read strictly forwards, so the SH-2 reads it via cached cartridge `$02000000`: one 16-byte line fill serves 16 bytes. Cache-through would pay the full cartridge wait on every byte. The output is built in cached SDRAM (back-references hit cache) and copied once to the framebuffer.
- Key numbers: 99.99% hit rate; misses 2,335 per iteration against about 1,920 compulsory.
- Target chapter: patterns/cache.md
- Evidence: emulator measured (PicoDrive with the opt-in SH-2 timing model added in Aerobiz U-093)

<!-- from VRD/AU/MARSDEV -->
### Enable and purge the cache yourself, and the slave-cache surprise
- Source: AU-NOTES, disasm/sh2/master/main.s:63-80; HISTORY.md:1970-2008; HARDWARE_TESTS.md:176-205
- What it does and why it is clever: Startup writes `CCR=0` (CE off, as required before changing CCR), then `$10` (CP purge), then `$01` (CE on). This is idempotent and guards against a boot ROM that did not do it. The timing model first showed the slave's two-instruction idle spin paying an 8-word SDRAM burst on every fetch, which the explicit enable fixed. Later, the BIOS dumps showed both boot ROMs already write `CCR=$11`, so the original run probably took PicoDrive's no-BIOS boot path.
- Key numbers: slave wait cycles 139.4 M → 472,472 (295×); master hit rate 99.5%.
- Target chapter: patterns/cache.md
- Evidence: emulator measured (PicoDrive). The "slave never enabled its cache" attribution is called into doubt by HARDWARE_TESTS item 7.

---

<!-- from D32XR (hardware survey) -->
### d32xr hardware survey: Cache usage and coherency
- Code runs from cached ROM 0x02000000 (mars-ssf.ld:50-99); registers through 0x2000xxxx (32x.h:28-52).
- Cache-through tricks: `MARS_ACTIVE_SCREEN` ORs 0x20000000 into a variable's address so both CPUs see it (marshw.c:88); trig tables read through 0x22000000, "cache-through access" (tables.c:2589-2595); ring-buffer rovers on the uncached alias (mars_ringbuf.h:37-38, 210-211); PCM command block written cache-through (marssound.c:1499-1534); DREQ DMA destinations cache-through (marshw.c:952).
- Lookup tables in spare frame-buffer DRAM read through the CACHED frame-buffer alias: `R_InitMathTables` builds viewangletox, distscale, yslope, xtoviewangle there (r_data.c:534-539) and clears bit 29, "enable caching for LUTs" (r_data.c:619-625). `initmathtables=2` (r_main.c:296), decremented per frame (p_tick.c:546-550); inference: builds the tables in both buffers.
- Shared per-frame structures (visplanes, viswalls, segclip, sorted lists, column caches) carved from the frame buffer past the visible lines (`I_WorkBuffer`, marsnew.c:869-875; r_main.c:878-921), used cache-through, so no purges needed.
- Purges: `SH2_ClearCacheLine` writes 0 to 0x40000000+addr; `SH2_ClearCacheLines` steps 16 bytes; `SH2_ClearCache` writes CCR=0 then CP|CE (32x.h:219-234). `CacheControl` (crt0.s:1268-1283).
- Boot: master CCR=0x10 ("purge and turn it off") before clearing BSS, 0x11 before main (crt0.s:369-372, 406-409); slave 0x11 (:856-859).
- Cross-CPU purges: r_main.c:944-954; texture/flat pointer arrays before the slave draws (r_phase6.c:617-652); plane/sprite list heads (r_phase7.c:305-307, 516-517; r_phase8.c:498-501); mobjs in sight checks (p_sight.c:407-428, 486-490); sound spatialisation (marssound.c:1087-1089, 1148-1153; comment :984 "cache read line loads all vars at once to cache"); RoQ chunks after DMA (marsroq.c:563, 591-592); full slave purge command after view changes (r_main.c:303, 365-366; r_data.c:930-933); purge after a bank switch (marsnew.c:711).
- Cache-line alignment: `.sdata` functions aligned 16 (marshw.h:37); map lumps "aline on cacheline boundary" (p_setup.c:74, 133, 247, 417, 542, 637); ring-buffer read and write rovers on separate lines (mars_ringbuf.h:40-51); zone (marsnew.c:761); sound buffers (marssound.c:70, 74).
- `ATTR_DATA_CACHE_ALIGN` = section ".sdata" (doomdef.h:69), linked into SDRAM 0x06000000 (mars-ssf.ld:102-118), copied from ROM by the 32X header load (crt0.s:116-124). Drawers, mixer, FixedDiv, IRQ handlers and vector tables live there.
- Not found: two-way cache mode / on-chip RAM (defined at 32x.h:96, 149, never used).
- Locks: `-mtas` (Makefile:24) makes atomic_flag_test_and_set use `tas.b`; explicit `tas.b` at f_wipe.c:36-41.

