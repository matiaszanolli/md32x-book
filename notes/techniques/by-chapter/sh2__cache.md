# Harvested techniques: sh2/cache.md

Target: `sh2/cache.md`. 3 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from VRD/AU/MARSDEV -->
### 1,748-byte renderer in cache-as-RAM (Pipeline 1)
- Source: VRD-NOTES, analysis/sh2-analysis/SH2_RENDERING_ARCHITECTURE.md:22-68, 154-158
- Correction (2026-10-03, from the ROM): both SH-2s do this, not only the Slave. Both reset handlers call the CCR routine at `0x060045CC` (`$10`, then `$09` = two-way mode), and command handlers on both CPUs call the copy at `0x0600252C`.
- What it does and why it is clever: At boot the Slave copies 437 longwords of rendering code to `$C0000000`, the SH7604 cache's data array used as 2 KB of on-chip RAM. A 56-byte context lives at `$C0000700`. For each entity, 52 bytes of state are copied to `$C0000740` and the on-chip code is called. It has 77 internal BSRs and zero SDRAM references, so it runs with zero wait states and no misses. It handles 36 entity passes per frame and the project calls it untouchable. (The SH7604 cache-as-RAM mode is general background, not stated in these docs.)
- Key numbers: 1,748 B code; 4 + 8 + 24 = 36 passes.
- Target chapter: sh2/cache.md
- Evidence: code only

<!-- from VRD/AU/MARSDEV -->
### Single-line associative purge and CCR control helpers
- Source: MARSDEV, sh_src/mars_start.s:751-783
- What it does and why it is clever: `CacheClearLine` ORs a 16-byte-aligned address with `$40000000` (the associative-purge area) and writes 0, invalidating just that line so shared data is re-read without purging the whole cache. `CacheControl` writes `CCR` with CP=$10, TW=$08 (two-way mode), CE=$01.
- Key numbers: purge area `$40000000`; CCR at `$FFFFFE92`.
- Target chapter: sh2/cache.md
- Evidence: code only

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

