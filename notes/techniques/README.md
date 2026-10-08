# Technique catalogue

Every clever algorithm and hardware technique harvested on 2026-10-02 from the book's sources, sorted by the chapter that should explain it. Not part of the published book.

Sources: S32X-SKILL (haroldo-ok skill), D32XR (Doom 32X Resurrection), VRD-NOTES / AU-NOTES / MARSDEV (author projects and marsdev skeleton), AB-DISASM (Aerobiz Supersonic). Raw agent reports, including each source's caveats and known bugs, are in [raw/](raw/).

Evidence levels used in entries: "shipped" (commercial game), "code only", "PicoDrive frame test" / "emulator measured", "manual", "invalidated" (the project itself later showed it wrong). Nothing here is tested on real hardware unless an entry says so.

## Existing chapters

| Chapter | Entries | Sources | Catalogue |
|---|---|---|---|
| [32x/bugs.md](../../src/32x/bugs.md) | 1 | D32XR 1 | [by-chapter/32x__bugs.md](by-chapter/32x__bugs.md) |
| [32x/communication.md](../../src/32x/communication.md) | 16 | S32X-SKILL 5, D32XR 4, VRD/AU/MARSDEV 7 | [by-chapter/32x__communication.md](by-chapter/32x__communication.md) |
| [32x/compositing.md](../../src/32x/compositing.md) | 6 | VRD/AU/MARSDEV 6 | [by-chapter/32x__compositing.md](by-chapter/32x__compositing.md) |
| [32x/fifo.md](../../src/32x/fifo.md) | 3 | VRD/AU/MARSDEV 2, D32XR 1 | [by-chapter/32x__fifo.md](by-chapter/32x__fifo.md) |
| [32x/pwm.md](../../src/32x/pwm.md) | 9 | S32X-SKILL 5, D32XR 2, VRD/AU/MARSDEV 2 | [by-chapter/32x__pwm.md](by-chapter/32x__pwm.md) |
| [32x/vdp.md](../../src/32x/vdp.md) | 18 | S32X-SKILL 5, D32XR 6, VRD/AU/MARSDEV 7 | [by-chapter/32x__vdp.md](by-chapter/32x__vdp.md) |
| [howto/32x-hello.md](../../src/howto/32x-hello.md) | 3 | VRD/AU/MARSDEV 3 | [by-chapter/howto__32x-hello.md](by-chapter/howto__32x-hello.md) |
| [howto/large-cartridges.md](../../src/howto/large-cartridges.md) | 6 | VRD/AU/MARSDEV 5, D32XR 1 | [by-chapter/howto__large-cartridges.md](by-chapter/howto__large-cartridges.md) |
| [howto/md-hello.md](../../src/howto/md-hello.md) | 2 | AB-DISASM 2 | [by-chapter/howto__md-hello.md](by-chapter/howto__md-hello.md) |
| [howto/profiling.md](../../src/howto/profiling.md) | 16 | S32X-SKILL 5, D32XR 2, VRD/AU/MARSDEV 9 | [by-chapter/howto__profiling.md](by-chapter/howto__profiling.md) |
| [howto/reverse-engineering.md](../../src/howto/reverse-engineering.md) | 7 | VRD/AU/MARSDEV 6, AB-DISASM 1 | [by-chapter/howto__reverse-engineering.md](by-chapter/howto__reverse-engineering.md) |
| [howto/toolchain.md](../../src/howto/toolchain.md) | 10 | S32X-SKILL 10 | [by-chapter/howto__toolchain.md](by-chapter/howto__toolchain.md) |
| [megadrive/cartridge.md](../../src/megadrive/cartridge.md) | 8 | S32X-SKILL 5, AB-DISASM 3 | [by-chapter/megadrive__cartridge.md](by-chapter/megadrive__cartridge.md) |
| [megadrive/io.md](../../src/megadrive/io.md) | 6 | S32X-SKILL 1, AB-DISASM 5 | [by-chapter/megadrive__io.md](by-chapter/megadrive__io.md) |
| [megadrive/m68k.md](../../src/megadrive/m68k.md) | 4 | AB-DISASM 4 | [by-chapter/megadrive__m68k.md](by-chapter/megadrive__m68k.md) |
| [megadrive/sound.md](../../src/megadrive/sound.md) | 1 | AB-DISASM 1 | [by-chapter/megadrive__sound.md](by-chapter/megadrive__sound.md) |
| [megadrive/vdp-color.md](../../src/megadrive/vdp-color.md) | 4 | AB-DISASM 4 | [by-chapter/megadrive__vdp-color.md](by-chapter/megadrive__vdp-color.md) |
| [megadrive/vdp-dma.md](../../src/megadrive/vdp-dma.md) | 11 | VRD/AU/MARSDEV 3, AB-DISASM 8 | [by-chapter/megadrive__vdp-dma.md](by-chapter/megadrive__vdp-dma.md) |
| [megadrive/vdp-planes.md](../../src/megadrive/vdp-planes.md) | 3 | AB-DISASM 3 | [by-chapter/megadrive__vdp-planes.md](by-chapter/megadrive__vdp-planes.md) |
| [megadrive/vdp-registers.md](../../src/megadrive/vdp-registers.md) | 2 | AB-DISASM 2 | [by-chapter/megadrive__vdp-registers.md](by-chapter/megadrive__vdp-registers.md) |
| [megadrive/vdp-sprites.md](../../src/megadrive/vdp-sprites.md) | 5 | AB-DISASM 5 | [by-chapter/megadrive__vdp-sprites.md](by-chapter/megadrive__vdp-sprites.md) |
| [megadrive/vdp-timing.md](../../src/megadrive/vdp-timing.md) | 6 | AB-DISASM 6 | [by-chapter/megadrive__vdp-timing.md](by-chapter/megadrive__vdp-timing.md) |
| [megadrive/z80.md](../../src/megadrive/z80.md) | 3 | AB-DISASM 3 | [by-chapter/megadrive__z80.md](by-chapter/megadrive__z80.md) |
| [patterns/60fps.md](../../src/patterns/60fps.md) | 13 | S32X-SKILL 5, D32XR 1, VRD/AU/MARSDEV 7 | [by-chapter/patterns__60fps.md](by-chapter/patterns__60fps.md) |
| [patterns/audio.md](../../src/patterns/audio.md) | 22 | S32X-SKILL 14, D32XR 7, VRD/AU/MARSDEV 1 | [by-chapter/patterns__audio.md](by-chapter/patterns__audio.md) |
| [patterns/bus.md](../../src/patterns/bus.md) | 10 | S32X-SKILL 3, D32XR 3, VRD/AU/MARSDEV 4 | [by-chapter/patterns__bus.md](by-chapter/patterns__bus.md) |
| [patterns/cache.md](../../src/patterns/cache.md) | 10 | S32X-SKILL 3, D32XR 4, VRD/AU/MARSDEV 3 | [by-chapter/patterns__cache.md](by-chapter/patterns__cache.md) |
| [patterns/case-study-aerobiz.md](../../src/patterns/case-study-aerobiz.md) | 9 | VRD/AU/MARSDEV 3, AB-DISASM 6 | [by-chapter/patterns__case-study-aerobiz.md](by-chapter/patterns__case-study-aerobiz.md) |
| [patterns/case-study-vr.md](../../src/patterns/case-study-vr.md) | 2 | VRD/AU/MARSDEV 2 | [by-chapter/patterns__case-study-vr.md](by-chapter/patterns__case-study-vr.md) |
| [patterns/cpu-split.md](../../src/patterns/cpu-split.md) | 20 | S32X-SKILL 5, D32XR 9, VRD/AU/MARSDEV 6 | [by-chapter/patterns__cpu-split.md](by-chapter/patterns__cpu-split.md) |
| [patterns/layering.md](../../src/patterns/layering.md) | 1 | VRD/AU/MARSDEV 1 | [by-chapter/patterns__layering.md](by-chapter/patterns__layering.md) |
| [patterns/streaming.md](../../src/patterns/streaming.md) | 12 | D32XR 7, VRD/AU/MARSDEV 4, AB-DISASM 1 | [by-chapter/patterns__streaming.md](by-chapter/patterns__streaming.md) |
| [sh2/cache.md](../../src/sh2/cache.md) | 3 | VRD/AU/MARSDEV 2, D32XR 1 | [by-chapter/sh2__cache.md](by-chapter/sh2__cache.md) |
| [sh2/divu.md](../../src/sh2/divu.md) | 8 | S32X-SKILL 4, D32XR 3, VRD/AU/MARSDEV 1 | [by-chapter/sh2__divu.md](by-chapter/sh2__divu.md) |
| [sh2/intc.md](../../src/sh2/intc.md) | 4 | VRD/AU/MARSDEV 3, D32XR 1 | [by-chapter/sh2__intc.md](by-chapter/sh2__intc.md) |
| [sh2/isa.md](../../src/sh2/isa.md) | 2 | D32XR 2 | [by-chapter/sh2__isa.md](by-chapter/sh2__isa.md) |
| [sh2/pipeline.md](../../src/sh2/pipeline.md) | 5 | D32XR 3, VRD/AU/MARSDEV 2 | [by-chapter/sh2__pipeline.md](by-chapter/sh2__pipeline.md) |

## Part VI and new how-to chapters (added 2026-10-02)

| Proposed chapter | Entries | Sources | Catalogue |
|---|---|---|---|
| 2D drawing and effects: shapes, scaling, rotation, transitions | 18 | S32X-SKILL 10, D32XR 3, VRD/AU/MARSDEV 3, AB-DISASM 2 | [by-chapter/techniques__2d-effects.md](by-chapter/techniques__2d-effects.md) |
| Asset pipelines, data-driven engines and porting | 15 | S32X-SKILL 15 | [by-chapter/techniques__asset-pipelines.md](by-chapter/techniques__asset-pipelines.md) |
| Compression and decompression | 2 | AB-DISASM 2 | [by-chapter/techniques__compression.md](by-chapter/techniques__compression.md) |
| Automated testing in an emulator | 18 | S32X-SKILL 18 | [by-chapter/howto__emulator-testing.md](by-chapter/howto__emulator-testing.md) |
| First-person engines: raycasting, BSP, textured walls and floors | 25 | S32X-SKILL 7, D32XR 18 | [by-chapter/techniques__first-person.md](by-chapter/techniques__first-person.md) |
| Fixed-point maths and fast division | 19 | S32X-SKILL 8, D32XR 5, VRD/AU/MARSDEV 6 | [by-chapter/techniques__fixed-point.md](by-chapter/techniques__fixed-point.md) |
| Collision, physics, line of sight and game logic | 25 | S32X-SKILL 13, D32XR 7, VRD/AU/MARSDEV 5 | [by-chapter/techniques__game-logic.md](by-chapter/techniques__game-logic.md) |
| Memory management on a 256 KB machine | 6 | D32XR 6 | [by-chapter/techniques__memory.md](by-chapter/techniques__memory.md) |
| Pseudo-3D roads and Mode 7 | 7 | S32X-SKILL 7 | [by-chapter/techniques__roads-mode7.md](by-chapter/techniques__roads-mode7.md) |
| Software 3D on the SH-2 | 34 | S32X-SKILL 18, D32XR 5, VRD/AU/MARSDEV 11 | [by-chapter/techniques__software-3d.md](by-chapter/techniques__software-3d.md) |
| Text, menus and UI on tile planes | 3 | AB-DISASM 3 | [by-chapter/techniques__text-menus.md](by-chapter/techniques__text-menus.md) |
| Voxel landscapes | 5 | S32X-SKILL 5 | [by-chapter/techniques__voxel.md](by-chapter/techniques__voxel.md) |

## Source caveats

### raw/s32x-skill.md

# Techniques harvested from S32X-SKILL (haroldo-ok, `sega-32x-gamedev`)

Skill root: `/tmp/claude-1000/-mnt-data-src-md32x-book/014ad006-fdd4-4f3e-a7ed-6836ee1471ee/scratchpad/s32x/skills/sega-32x-gamedev`

I read every file in full: SKILL.md, all 11 reference files, and all assets (r3d.c/h, gen_tables.py, gfx_shapes.c, harness.c, run_tests.py, verify_rom.py, romfix.py, mars.ld, Makefile, scripts). Line numbers below are per file.

## Problems in the source to fix before you quote it
1. **Real bug in `assets/3d/r3d.c:89-98` (painter sort).** `facez[]` holds per-vertex camera-z (line 90). Lines 95-98 then overwrite `facez[i]` with face sums in the same array, so face *i* can read a vertex-z that an earlier face already replaced. The sort keys get corrupted whenever a triangle refers to a vertex index lower than its own face index. Fix: use separate `vertz[]` and `facez[]` arrays.
2. **r3d.c does not follow the skill's own speed advice.** The rasteriser (lines 10-39) does up to two `long long` divides per scanline. Those compile to `__divdi3`, which `optimization.md:327-336` names as a hotspot to remove. The projection (lines 63-64) uses a three-factor `long long` multiply chain, which is one of the GCC 12.1 miscompile patterns (`toolchain-and-build.md:183-185`). Treat r3d.c as a teaching baseline, not optimised code.
3. **r3d.c has no backface culling.** The skill only describes it (`software-3d.md:146-148`). The rasteriser also has no vertical guard clip and no early exit for fully off-screen triangles.
4. **Optimisation-level advice conflicts.** The Makefile (line 38) compiles the audio object at `-O2 -fno-lto` and everything else at `-Os -flto`. `toolchain-and-build.md:189-192` says calls between objects built at different `-O` levels can break on GCC 12.1. The skill admits the tension ("isolating only a well-understood module"), but the book should state it outright.
5. **Advice on which CPU runs the mixer conflicts.** `audio.md:62-68` says the simplest setup is the master running the mixer. `architecture.md:206-209` and `audio.md:138-139` say to dedicate the slave. Present this as a trade-off.
6. **The COMM4 advice depends on the boot code.** d32xr uses COMM4 as the slave command word (`architecture.md:100-104`). Another port's COMM4 collided with its `S_OK` handshake (`testing.md:441-451`). Which slot is safe depends on your boot code; nothing about COMM4 is fixed by hardware.
7. **"CRAM bit 15 clear = transparent" (`testing.md:417-418`) is the skill's wording.** In Sega's documentation bit 15 is the priority/"through" bit. Whether a cleared bit looks transparent depends on the MD plane behind it and the priority setting. Check this against hardware docs before printing it.
8. **The fast reciprocal table is coarse near the camera.** The key is `k = z>>12`, i.e. 1/16-unit steps. At the near limit (z = 0.25, k = 4) the truncation error can reach about 25%. The "~1 px" accuracy claim only holds at mid and far depths.

---

### raw/d32xr-algorithms.md

# D32XR algorithm harvest: Doom 32X Resurrection

Repo root: `/tmp/claude-1000/-mnt-data-src-md32x-book/014ad006-fdd4-4f3e-a7ed-6836ee1471ee/scratchpad/d32xr`. All paths below are relative to it.

**Licence labels.** I applied your rule literally: a file is MIT only if its own header says MIT. Some files fall to "id limited-use" under that rule even though their headers say something else, so check these before quoting any of them:
- **CALICO header only, no MIT text:** `r_phase1.c` to `r_phase9.c`.
- **"Original code by Chilly Willy", no licence text:** `sh2_draw.s`, `sh2_drawlow.s`, `sh2_draw4b.s`.
- **Tim Ferguson's "You may freely use this source code":** `roq_read.c`.
- **No header at all:** `liblzss/lzss.c`, `marssound.c`, `f_wipe.c`.

**Build defaults that change what the code does:**
- **SH-2 mixer is off by default.** The Makefile defines `DISABLE_DMA_SOUND` unless `ENABLE_DMA_SOUND` is set.
- **No mipmaps by default.** `MIPLEVELS` defaults to 1, so the mip code is compiled out.
- **The fire effect is optional.** It needs `ENABLE_FIRE_ANIMATION`.
- **`USE_SMALL_LUMPS` is optional.** It makes the game read segs and nodes straight from ROM.

**Evidence.** No comment anywhere says something was measured or tested on hardware. Two comments come close, and I quote them where they apply: the DIVU cycle-count comment (a spec figure, not stated as measured) and the "minimize pipeline stalls" rationale.

---

### raw/vrd-au-marsdev.md



## Harvest of algorithms and hardware techniques from VRD (32x-playground), Aerobiz Ultimate and the marsdev 32x-skeleton
I read the core docs and sources for all three projects (file:line ranges are given in each entry).

**What the VRD project itself now treats as wrong** (its canonical page is `/mnt/data/src/32x-playground/VR60_STATUS.md`, as of 2026-08-13):
- the "40 FPS achieved / 60 FPS one blocker away" claim;
- the camera-interpolation hook, which was placed in the **2-player** dispatcher (`state_disp_005020`), not normal 1P (`state_disp_004cb8`);
- the 724-framebuffer-hash control;
- the C218 render-bridge specification;
- the `$2203E000` parameter block, which is a cartridge-ROM alias, not SDRAM;
- `render_state_patcher`, which writes addresses the renderer never reads;
- the claim that the "14× sh2_send_cmd / 10.52% COMM wait" was a racing bottleneck. It was an artifact of profiling mixed scenes;
- all early January docs that say "Slave 99.97% idle / Master renders 3D". Later profiling assigns all 3D to the Slave. The docs contradict each other on this point, and I flag it wherever it matters.

**What no project here proves:** no technique below has been run on a real 32X. Aerobiz used Ares as its hardware stand-in.

**Ares SH-2 timing caveat:** Ares models the SH-2 cache but charges no wait states for cache-through, cartridge or framebuffer access (HARDWARE_TESTS.md item 6). Its SH-2 frame rates are therefore optimistic.

---

### raw/ab-disasm.md

# Aerobiz Supersonic (Koei, 1994): techniques harvested from the disassembly

All entries below come from reading the shipped code in the byte-identical disassembly at /mnt/data/src/aerobiz-disasm. Paths are relative to /mnt/data/src/aerobiz-disasm unless they are absolute. ROM addresses are from the module headers.

**Several routines have misleading names in the repo, so don't trust the labels.** I describe what the code actually does:
- `ControllerRead` ($000B42) is a tile-animation DMA.
- `DMA_Transfer` ($00163E) is a CPU copy of 11 colours to CRAM.
- `DiagonalWipe` ($01ACBA) moves a 16x16 sprite.
- `TransitionEffect` ($01F7C0) is a route-slot search.
- `FadeGraphics` ($01F82E) is economy code.
- `ResourceLoad` / `ResourceUnload` are guarded palette fades.
- `CmdTestVRAM` ($0007D8) is a controller-port ID probe.
- `CmdSetupSprite` ($000550) is a generic VDP block copy in either direction.
- `ShowRouteInfo` ($00F104) is the save-slot panel.
- `UpdatePassengerDemand` ($00F522) writes the save header.
- `RAM_MAP.md` says `ram_sub` writes to the VDP *data* port and is called by SubsysUpdate1. In the code it writes to the *control* port (A4 = $C00004) and is called by ConfigVDPDMA.

---

