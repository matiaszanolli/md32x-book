# Harvested techniques: howto/profiling.md

Target: `howto/profiling.md`. 16 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from S32X-SKILL -->
### Frame-counter bar read from captures
- Source: S32X-SKILL, references/optimization.md:147-167
- What it does and why it is clever: Draw a white bar whose width is `frame & 127`. Read the bar width in two captures N emulated frames apart: `iters = (w1 − w0) & 127` is the number of game iterations, which gives effective fps from video alone.
- Key numbers: Zepton ran 12-19 iterations per 60 frames.
- Target chapter: howto/profiling.md
- Evidence: Used in PicoDrive.

<!-- from S32X-SKILL -->
### Headroom probe with calibrated ballast
- Source: S32X-SKILL, references/optimization.md:306-325
- What it does and why it is clever: fps can't show a gain that stays inside a vblank boundary. Inject calibrated busy-work and report how much the frame absorbs before dropping a step, which gives a continuous metric. Validate the instrument first: a ballast flag that never reached the compiler, and PicoDrive's dynarec idle-loop detection optimising the ballast away, both made every reading meaningless.
- Key numbers: 4,000,000 dummy iterations that "cost nothing".
- Target chapter: howto/profiling.md
- Evidence: racing-circuit-32x.

<!-- from S32X-SKILL -->
### Host-side fill-cost counter
- Source: S32X-SKILL, references/optimization.md:274-282
- What it does and why it is clever: Run the renderer's span, quad and blit calls against counters on the host. Report pixels and spans per element (backdrop, entities, HUD) to tell fill-rate limits from per-primitive setup cost.
- Key numbers: —
- Target chapter: howto/profiling.md
- Evidence: arkanoid32x (bottleneck turned out to be setup and redraw).

<!-- from S32X-SKILL -->
### Hardware timers and size tracking
- Source: S32X-SKILL, references/optimization.md:82-88; assets/Makefile:89-91
- What it does and why it is clever: Time phases on hardware with `Mars_GetTicCount`, `Mars_GetWDTCount` and `Mars_FRTCounter2Msec`. Print `sh-elf-size` and grep `__bss_end` in every build log.
- Key numbers: —
- Target chapter: howto/profiling.md
- Evidence: d32xr.

<!-- from S32X-SKILL -->
### "run N" emulated frames is not N game iterations
- Source: S32X-SKILL, references/testing.md:207-219
- What it does and why it is clever: Timers count iterations. At about 12 fps, a 40-iteration spawn needs about 200 emulated frames. Brief effects fall between captures, so capture several frames.
- Key numbers: 8-19 iterations per 60 frames.
- Target chapter: howto/profiling.md
- Evidence: Zepton.

---

<!-- from D32XR -->
### Per-phase FRT timing and diagnostic draw modes
- Source: D32XR, r_main.c:1124-1183, marsnew.c:960-1025, marshw.c:86-93, 253, r_cache.c:241-247 (licence: id limited-use for r_main; MIT for the rest)
- What it does and why it is clever: The renderer timestamps BSP, prep, segs, planes, sprites and total with the free-running timer into 4-entry ring arrays; the overlay averages them with `>>2`. Ticks become milliseconds through a 16.16 reciprocal computed once (`4096·1000/clock·65536`), so no division. Debug modes (cycled with MODE in the options menu) cover:
  - FPS only, or all counters plus wall, plane and sprite counts;
  - texture cache disabled;
  - a no-op drawer, so geometry cost can be measured with no fill;
  - each texture-cache entry painted a flat colour from its id, to show residency on screen.
- Key numbers: 10 overlay lines.
- Target chapter: howto/profiling.md
- Evidence: code only

---

<!-- from VRD/AU/MARSDEV -->
### A libretro PicoDrive profiler and debugger
- Source: VRD-NOTES, tools/libretro-profiling/VRD_PROFILING.md:1-66, 339-427
- What it does and why it is clever:
  - **Per-frame CSV:** 68K, Master and Slave cycles; useful cycles; framebuffer FNV hash; scene; state.
  - **PC histograms:** force the SH-2 interpreter because the recompiler hides PCs.
  - **Exact idle/useful split:** idle PCs are derived empirically.
  - **Filters and probes:** scene gating (`VRD_SCENE`), memory watches, dumps, a caller trace on any 68K PC, and a write tracer hooked before opcode fetch so it does not perturb batching.
  - **Determinism:** deterministic input record and replay.
  - **Watching COMM:** use the SH-2 aliases (`$20004020`), and watch COMM7 as a word.
- Key numbers: 2,400-frame runs.
- Target chapter: howto/profiling.md
- Evidence: emulator measured (PicoDrive)

<!-- from VRD/AU/MARSDEV -->
### Profiling traps: idle loops, mixed scenes, truncated histograms
- Source: VRD-NOTES, analysis/profiling/PERFORMANCE_BREAKTHROUGH_SUMMARY.md:1-100; analysis/profiling/PC_PROFILING_CORRECTED_RESULTS.md:1-110; VR60_ROADMAP.md lessons; VR60_STATUS.md:154-160
- What it does and why it is clever:
  1. The Slave's 66.5% "hotspot" was a 64-iteration NOP delay loop. Removing it cut Slave cycles by 66.6% and changed FPS by 0%.
  2. The 13% `sh2_send_cmd` wait was a car-select artifact of mixed-scene profiling; racing alone showed the 68K 63% idle.
  3. A top-200 PC histogram "proved" a hook was dead code; an exact caller trace showed it runs at 20 Hz.
  4. An early PC-masking bug hid the SDRAM region.
- Key numbers: Slave 299,958 → 100,157 cycles per frame with no FPS change.
- Target chapter: howto/profiling.md
- Evidence: emulator measured. The dead-hook and 13%-bottleneck conclusions are invalidated.

<!-- from VRD/AU/MARSDEV -->
### Counting real frames: FS flips, V-INT count and SH-2 frame counters
- Source: VRD-NOTES, BLOG_FPS_COUNTER_SAGA.md:1-130; analysis/profiling/SH2_FRAME_COUNTER_PROFILING.md:1-130; docs/PROFILING_QUICKSTART.md; KNOWN_ISSUES.md:488-497
- What it does and why it is clever:
  - **Counting flips:** counting FBCTL.FS transitions per 60 V-INTs measures displayed frames, not V-INTs or game ticks.
  - **What went wrong:** the counter's RAM was trampled by the game, its source read a live COMM register instead of its variable, it read `$A15100` instead of `$A1518A`, and a vasm `bsr.w` landed at target+2.
  - **Alternative plan:** an SH-2 counter in cache-through SDRAM (`$26000400`) incremented at the renderer's `final_exit`. The hook was never installed.
- Key numbers: V-INT counter 3,600 per minute (useless); expected about 1,200 SH-2 frames per minute.
- Target chapter: howto/profiling.md
- Evidence: invalidated in part. The blog's 6-7 swaps per second conflicts with later exact traces (about 20 Hz state-8 swaps), and the quickstart's "VDP polling 47%" claim is superseded.

<!-- from VRD/AU/MARSDEV -->
### Validation discipline: control ROM pairs and fail-closed gates
- Source: VRD-NOTES, VR60_STATUS.md:152, 235-399, 449-457
- What it does and why it is clever:
  - "Built ≠ executing ≠ validated."
  - Every experiment has an ACTIVE and a CONTROL ROM built from the same source, byte-equal outside an 8-byte hook (both hashes recorded).
  - Fixtures must pass liveness checks: scene pointer, `$C87E` cycling, caller trace, framebuffer change, and COMM not stuck.
  - Validators fail closed.
  - Savestates can be silently broken: one froze `$C87E` regardless of the hook.
- Key numbers: lifecycle suite of 31,137 active frames over three tracks, each run byte-identical on replay.
- Target chapter: howto/profiling.md
- Evidence: emulator measured (PicoDrive)

<!-- from VRD/AU/MARSDEV -->
### Instrumenting the emulator: SH-2 timing model, RV emulation, falsification by slope
- Source: AU-NOTES, ROADMAP.md:2740-2809; disasm/sh2/master/timing_test.c:1-90
- What it does and why it is clever: These are opt-in additions to the shared PicoDrive core: SH-2 wait states plus a timing-only SH7604 cache (min/mid/max, refusing to run under the recompiler), RV window switching, per-frame fingerprints, and VRAM write traces. Each access class is validated by a one-kind test cartridge, measured as the slope between two iteration counts so boot overhead cancels.
- Key numbers: 11.0000 (cache-through SDRAM longword), 2.0000 (framebuffer word write), 7.0000 (cache-through cartridge longword) wait cycles, matching the manual exactly.
- Target chapter: howto/profiling.md
- Evidence: emulator measured (PicoDrive)

<!-- from VRD/AU/MARSDEV -->
### Comparing two builds that diverge: screen fingerprints and inversion counts
- Source: AU-NOTES, ROADMAP.md:2702-2738, 1745-1764; KNOWN_ISSUES.md:250-266
- What it does and why it is clever: Any timing change sends the AI demo down another path, so frame-number comparisons lie. Instead, each frame is fingerprinted by hashing VRAM, CRAM, VSRAM and the VDP registers from one savestate, and frames are paired by screen. Use a CRAM-only key when VRAM layout changes. Screen order is compared by counting inversions of first occurrences, not by elementwise comparison. The first divergent frame is still meaningful.
- Key numbers: 56 of 56 screens matched with constant +7 drift; 0 inversions at min-run 20.
- Target chapter: howto/profiling.md
- Evidence: emulator measured (PicoDrive)

<!-- from VRD/AU/MARSDEV -->
### Cheap PC sampling and savestate-decoding traps
- Source: AU-NOTES, ROADMAP.md:1537-1595; KNOWN_ISSUES.md:225-290, 664-676
- What it does and why it is clever:
  - **PC sampling:** read the 68K PC from savestate chunk 1 (little-endian, offset `$40`) each frame. It is fast, but biased towards idle points because the sample phase is always the same.
  - **Byte order:** VRAM, CRAM, Work RAM and SDRAM chunks are byte-swapped.
  - **Debug reads:** they return 0 for `$A151xx`, so keep counters in SDRAM.
  - **Oracle check:** a pixel oracle that passes on black proves nothing.
- Key numbers: 426,000 frames in 70 s.
- Target chapter: howto/profiling.md
- Evidence: emulator measured (PicoDrive)

<!-- from VRD/AU/MARSDEV -->
### Ares as a hardware stand-in, and what each emulator does not model
- Source: AU-NOTES, HARDWARE_TESTS.md:12-78
- What it does and why it is clever: Ares runs the real BIOS and models the SH-2 cache (12 clocks per miss) but no cache-through or framebuffer wait states and no bus contention. PicoDrive models no cache or SDRAM latency, opens PEN only in V-Blank, drops FS writes outside V-Blank and halts polling 68Ks. A behaviour is trusted only when both agree, and a hardware test list is kept per question.
- Key numbers: see the emulator table in HARDWARE_TESTS.md.
- Target chapter: howto/profiling.md
- Evidence: emulator measured (PicoDrive/Ares)

<!-- from VRD/AU/MARSDEV -->
### Counting DREQ FIFO blocking from logs
- Source: VRD-NOTES, docs/QUICK_FIFO_CAPTURE.md:1-59
- What it does and why it is clever: The emulator runs for a fixed time with stdout logged, and a script counts DREQ blocking events per second and per frame, separating startup from gameplay.
- Key numbers: 33 and 71 blocks (0.3 per second, about 0 per frame) at startup only.
- Target chapter: howto/profiling.md
- Evidence: emulator measured (startup-only; gameplay never captured)

---

<!-- from D32XR (hardware survey) -->
### d32xr hardware survey: Performance notes
- No measured fps or ms figures in the source. Debug overlay shows per-phase times from the WDT (`4096*1000/clock`) (marsnew.c:982-1015; marshw.c:252-253, 54-55); live fps counter (marsnew.c:1116-1122).
- Frame cap ticsperframe 2-4 vblanks (doomdef.h:1313-1315; o_main.c:260-265, 564-565); demos "recorded at 15-20fps" (marsnew.c:1106).
- Comments on bus and cache: "take our hands off the bus" (r_phase7.c:554); plane sort for cache and pipeline (r_phase7.c:477-478, 496); 68000 code in RAM (src-md/main.c:45-48); FixedDiv 39/6 cycles (sh2_fixed.s:47-48); interrupt nops (crt0.s:583); mul.l latency (marsroq.c:178); GCC constant reloads (marssound.c:1175-1176); "64 seems to be too loud" (marssound.c:975); wipe speed halved for double buffering (f_wipe.c:119). Z80 driver quotes 32X Technical Notes 15 and 22 (src-md/z80_vgm.s80:7-12).

