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

## NEW: Fixed-point maths

### 16.16 fixed point with a 64-bit-intermediate multiply
- Source: S32X-SKILL, assets/3d/r3d.h:7-10; references/software-3d.md:15-19; references/optimization.md:37-39
- What it does and why it is clever: All world coordinates, the camera and velocities are `int` in 16.16 format: `FX(n) = n·65536`, `fmul(a,b) = ((int64)a·b) >> 16`. Screen coordinates are plain ints. The core has no floats at all, so the desktop build and the SH-2 build compute bit-identical results, which is what makes desktop-vs-ROM replay tests possible.
- Key numbers: FX_ONE = 65536. Range ±32768 units, resolution 1/65536.
- Target chapter: NEW: Fixed-point maths
- Evidence: Used in two shipped games (a rally racer and a rail shooter) built on r3d; host-tested.

### 256-entry build-time sine table, cos as a phase offset
- Source: S32X-SKILL, assets/3d/gen_tables.py:1-14; assets/3d/r3d.c:6-7
- What it does and why it is clever: Angles are "brads" (binary angles, 0..255 = one full turn). A Python script writes `sintab[i] = round(sin(2πi/256)·65536)` as a C `.inc` that lands in ROM. `cos(a) = sintab[(a+64)&255]`, and the `&255` gives free wraparound. There is no runtime float and no second table.
- Key numbers: 256 × 4 bytes = 1 KiB of ROM. 1 brad = 1.406°.
- Target chapter: NEW: Fixed-point maths
- Evidence: Shipped engine asset.

### Reciprocal lookup table replaces the perspective divide
- Source: S32X-SKILL, assets/3d/gen_tables.py:16-32; assets/3d/r3d.c:53-66; references/optimization.md:98-113; references/software-3d.md:39-44
- What it does and why it is clever: Stores `recip[k] = 2^22 / k` with key `k = z_16.16 >> 12`, so `recip[k] ≈ 2^34 / z`. Projection then becomes `sx = W/2 + (x·focal·recip[k]) >> 34`, i.e. multiply and shift with no divide. The general rule: any `a/b` where `b` stays in a bounded range can be turned into a table keyed on `b`.
- Key numbers: 4096 entries × 4 bytes = 16 KiB of ROM, RECIP_SH = 22. Covers z up to 256 units. About 1 px error versus a true divide (much worse very close to the camera; see problem 8). Entry 0 holds 0.
- Target chapter: NEW: Fixed-point maths
- Evidence: Host-checked against the exact divide ("worst error ~1px"). Shipped engine.

### Fold constant factors into the reciprocal table
- Source: S32X-SKILL, references/optimization.md:327-336
- What it does and why it is clever: Pre-multiply `focal` into the table, `rtab[k] = focal·2^S/k`. A three-factor 64-bit product `x·focal·recip` becomes a single 32×32 multiply. The table is rebuilt only when the folded constant changes (for example an FOV change). A 1-4 K-entry `fx_div_small` table handles per-scanline and per-point divides.
- Key numbers: 1-4 K entries. One racer was doing about 340 `__divdi3` calls per frame before this.
- Target chapter: NEW: Fixed-point maths
- Evidence: Measured as part of a 12→30 fps optimisation log (racing-circuit-32x).

### Interpolated 16.16 atan2 sized to its consumer
- Source: S32X-SKILL, references/testing.md:465-474
- What it does and why it is clever: A whole-brad atan2 (1.4° steps) is fine for gameplay headings. Used for camera pitch it is not: one brad moves the horizon 4-5 scanlines (focal·tan 1.4° ≈ 0.0245·focal, about 4.4 lines at focal ≈ 180). A 257-entry table with linear interpolation (the extra entry closes the interval) returns 16.16 brads. Size table precision to what the consumer can see on screen.
- Key numbers: 257 entries. Worst-case error drops from 0.99 to 0.0002 brads. Zero horizon jumps over 3000 frames.
- Target chapter: NEW: Fixed-point maths
- Evidence: racing-circuit-32x, measured over 3000 frames.

### 32-bit `long` overflow in distance and area code
- Source: S32X-SKILL, references/architecture.md:162-170; references/voxel-landscape.md:46-48
- What it does and why it is clever: On the SH-2, `int` and `long` are both 32 bits, so `dx·dx + dz·dz` on 16.16 values silently wraps. On x86-64 `long` is 64 bits, so the same code passes host tests and fails only on hardware. Use `long long` for such intermediates, and grep for `long ` when moving host-tested code over. Voxel example: `frac·CELLZ` (65535 × 98304) overflows; compute `((long long)frac·CELLZ) >> 16`.
- Key numbers: frac ≤ 65535, CELLZ ≈ 98304, product ≈ 6.4e9 > 2^31.
- Target chapter: NEW: Fixed-point maths
- Evidence: Real bug class seen in ports (described).

### Shifts and masks instead of `* / %`
- Source: S32X-SKILL, references/optimization.md:32-35, 60-62
- What it does and why it is clever: Replace `x/64` with `x>>6`, `x%64` with `x&63`, `x*8` with `x<<3`. A non-power-of-two constant divide becomes a fixed-point reciprocal multiply plus shift. Default locals to `int`, because 8- and 16-bit arithmetic adds masking instructions on the SH-2.
- Key numbers: —
- Target chapter: NEW: Fixed-point maths
- Evidence: Described as a d32xr idiom.

### Bake transcendentals into ROM tables at build time
- Source: S32X-SKILL, references/optimization.md:342-344, 292-295
- What it does and why it is clever: AI corner-speed logic was calling atan2 twice and hypot twice for each of 14 lookahead points per car, every frame. These were precomputed into a ROM table, along with track centreline tangents and normals. Sprite row/scale tables and sin/atan2 tables follow the same pattern.
- Key numbers: About 750 transcendental calls per frame removed.
- Target chapter: NEW: Fixed-point maths
- Evidence: Measured in the 12→30 fps racer log.

---

## sh2/divu.md

### Use the hardware divider once per column, never per pixel
- Source: S32X-SKILL, references/software-3d.md:188-190
- What it does and why it is clever: The raycaster does one DDA per screen column using the SH-2 on-chip divider. At about 39 cycles that is affordable once per column (128 per frame) but never inside a pixel loop. The cost model is: divide = per-column or per-slice budget, multiply = per-point budget, shift/lookup = per-pixel budget.
- Key numbers: About 39 cycles per divide. 128 columns per frame.
- Target chapter: sh2/divu.md
- Evidence: noudar-32x shipped at 30 fps on one SH-2.

### Hoist the divide when many points share a divisor
- Source: S32X-SKILL, references/optimization.md:169-181; references/voxel-landscape.md:50-66
- What it does and why it is clever: Every cell in a voxel depth slice and every pixel on a Mode-7 scanline shares one depth. Compute `rf = (FOCAL<<12)/zz` once (12.12 format, with `zz = wz>>8` in 8.8), then `sx = 160 + ((wx>>8)·rf >> 12)` per point. Keep the slow divide version and unit-test that the fast path stays within 1 px of it.
- Key numbers: About NX·NZ·3 divides (~2700 for 32×28) become about NZ = 28.
- Target chapter: sh2/divu.md
- Evidence: Host unit test (±1 px). Measured in Zepton: no fps change because the game was fill-bound, but it freed CPU headroom.

### Find and kill hidden 64-bit software divides
- Source: S32X-SKILL, references/optimization.md:327-336
- What it does and why it is clever: `(dx<<16)/dy` with a 64-bit intermediate compiles to libgcc `__divdi3` / `__udivdi3`, a slow software routine. Grep the disassembly for those symbols; each one in a hot loop should become a reciprocal table.
- Key numbers: About 340 `__divdi3` per frame in one road rasteriser.
- Target chapter: sh2/divu.md
- Evidence: racing-circuit-32x, measured.

### Precompute edge slopes once per edge
- Source: S32X-SKILL, references/optimization.md:241-246
- What it does and why it is clever: A quad filler that did a 64-bit divide per scanline was changed to compute a 16.16 `dx/dy` slope once per edge and then add it each row. This was the first of three measured fixes in a breakout that went from 7 to 60 fps.
- Key numbers: 7 → 14.6 fps.
- Target chapter: sh2/divu.md
- Evidence: arkanoid32x, measured.

---

## NEW: Software 3D on the SH-2

### Per-object transform pipeline
- Source: S32X-SKILL, references/software-3d.md:26-37; assets/3d/r3d.c:42-51, 75-91
- What it does and why it is clever: For each vertex: yaw-rotate in model space and translate (`w.x = x·cos − z·sin + at.x`, `w.z = x·sin + z·cos + at.z`), subtract the camera position, rotate by −camera yaw (`o.x = dx·c − dz·s`, `o.z = dx·s + dz·c`), then project. Only rotation about Y is needed, so it costs 4 fmuls per stage and no matrices.
- Key numbers: Yaw 0..255. Up to 256 verts and 512 tris per mesh (static buffers).
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: Shipped in a rally racer and a rail shooter.

### Projection with near-plane rejection
- Source: S32X-SKILL, references/software-3d.md:31-33; assets/3d/r3d.c:53-66
- What it does and why it is clever: `sx = W/2 + x·f/z`, `sy = H/2 − y·f/z` (Y up). Points with z < 0.25 are rejected before the reciprocal lookup. A triangle is dropped if any vertex fails, so no clipping code is needed (the cost is triangles popping at the near plane).
- Key numbers: focal ≈ 140-160 px. Near plane z = 0.25 (FX(1)/4). Key clamped to RECIP_N − 1.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: Shipped engine.

### Flat-shaded scanline triangle rasteriser writing to a HAL-free buffer
- Source: S32X-SKILL, assets/3d/r3d.c:10-39; references/software-3d.md:49-56
- What it does and why it is clever: Sort the three vertices by y. For each row, interpolate x on the long edge (v0→v2) and on the short edge (v0→v1 above y1, v1→v2 below), swap if needed, clip, and memset the span with one palette byte. It writes into a caller-supplied `{u8 *px; int w,h;}`, so the same code runs in a host test (fill into a malloc'd buffer, assert area and an interior pixel) and on the 32X back buffer. Caveat: as written it does a `long long` divide per edge per row (see problems 2 and 3).
- Key numbers: 8bpp, one byte per pixel.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: Host-tested and shipped.

### Painter's sort by summed vertex depth (no z-buffer)
- Source: S32X-SKILL, assets/3d/r3d.c:93-108; references/software-3d.md:35-37
- What it does and why it is clever: Each face's key is `z_a + z_b + z_c`; skipping the divide by 3 keeps the same order. Faces are insertion-sorted descending (far first) and drawn in that order. With no z-buffer there is no 2-bytes-per-pixel RAM cost and no per-pixel compare, which matters with 256 KiB of SDRAM. Fine for convex-ish meshes and separated objects. Note the aliasing bug (problem 1).
- Key numbers: O(n²) insertion sort; fine for small n.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: Shipped engine; contains the facez bug described above.

### Backface culling (described, not in r3d)
- Source: S32X-SKILL, references/software-3d.md:146-148; references/examples.md:113-116
- What it does and why it is clever: The fighters use painter sort plus backface culling with no z-buffer. Culling removes about half the faces of a closed mesh before sorting and filling, and it hides the painter errors that inward-facing faces cause. The skill gives no formula. The standard one (my addition): cull if the screen-space signed area `(x1−x0)(y2−y0) − (x2−x0)(y1−y0)` has the wrong sign for your winding.
- Key numbers: About 50% fewer faces on closed meshes.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: Shipped in hit8ox-32x and fighting-game-3D-32X (described only).

### Cull before sorting; frustum cull, LOD, and drop buried faces at build
- Source: S32X-SKILL, references/optimization.md:351-353
- What it does and why it is clever: Culling before the O(n²) insertion sort roughly halves n, so sort cost drops about 4×. Distant meshes switch LOD: a far car becomes 13 triangles, then a single box. The build tool deletes coincident quads sealed inside abutting boxes, so no runtime work is spent on faces that can never be seen.
- Key numbers: Far car = 13 tris → 1 box.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: Measured in the 12→30 fps racer log.

### Hoist the camera basis once per frame
- Source: S32X-SKILL, references/optimization.md:354-355
- What it does and why it is clever: Look up sin/cos of camera yaw and pitch once per frame and pass them in, instead of once per vertex. Note that r3d's `to_camera` re-reads them per vertex.
- Key numbers: About 600 table lookups per frame removed.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: Measured (racer log).

### Interpolated reciprocal-depth projection and shell sort
- Source: S32X-SKILL, references/optimization.md:296-299
- What it does and why it is clever: Compute one reciprocal per depth step and interpolate between steps, which generalises divide hoisting to continuous depth. Sort few objects far-to-near with a shell sort.
- Key numbers: —
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: wave-rider-gp audit checklist (described).

### Scanline shared-edge road strips
- Source: S32X-SKILL, references/optimization.md:345-347
- What it does and why it is clever: A road strip's long edges are shared between segments. Walking the strip by scanline as one shape needs about 6 divides, versus about 30 edge-slope divides plus vertex sorts when each segment is split into 10 triangles.
- Key numbers: About 30 → about 6 divides per segment.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: Measured (racer log).

### Low-poly ROM mesh format with distinct palette colours
- Source: S32X-SKILL, references/software-3d.md:58-69; assets/3d/r3d.h:12-19
- What it does and why it is clever: A `const` mesh `{verts, nverts, tris{a,b,c,color}, ntris}` lives in ROM and costs no SDRAM. Each object gets its own palette index, which makes it readable on screen and makes pixel-based emulator tests unambiguous.
- Key numbers: Car ≈ 16 verts / 20 tris. Enemy ≈ 6 verts / 8 tris.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: Shipped.

### Chase camera
- Source: S32X-SKILL, references/software-3d.md:73-74
- What it does and why it is clever: `cam.pos = obj.pos − heading·dist`, `cam.yaw = obj.yaw`. Two lines give a third-person racer camera.
- Key numbers: —
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: Shipped racer.

### Track or rail ribbon from a segment list
- Source: S32X-SKILL, references/software-3d.md:78-80
- What it does and why it is clever: Expand `{curve, slope, len}` segments into centreline nodes `{x,y,z,yaw}`. Edge points are centre ± perpendicular·half_width, and each segment is drawn as two triangles. A compact, authorable track format.
- Key numbers: 2 tris per segment.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: Shipped racer and rail shooter.

### Scrolling ground detail to show speed
- Source: S32X-SKILL, references/software-3d.md:75-77
- What it does and why it is clever: A flat single-colour ground shows no motion. Transverse lines or road dashes whose world-z scrolls with distance travelled give a cheap sense of speed.
- Key numbers: —
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: Shipped.

### Fixed-camera tunnel projection
- Source: S32X-SKILL, references/software-3d.md:155-177
- What it does and why it is clever: When the camera never rotates and looks down +z, use `r = 1/(z + CAM_BACK)` once per depth slice, then `sx = cx + x·r·FOCAL`, `sy = cy − y·r·FOCAL`. No matrices. Clamp `z + CAM_BACK` away from 0. Tune FOCAL, CAM_BACK and the world z extents together so the near plane matches the 320×224 viewport; this is a correctness constraint enforced by a corner-screenshot test.
- Key numbers: One reciprocal per depth.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: arkanoid32x, with a host `make shots` corner gate.

### Rasterise static geometry once
- Source: S32X-SKILL, references/optimization.md:247-250; references/software-3d.md:169-170
- What it does and why it is clever: With a fixed camera the corridor is identical every frame. Rasterise it once at boot into an offscreen buffer and copy it each frame. Half the frame time had been spent redrawing unchanging geometry.
- Key numbers: 14.6 → 29 fps.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: arkanoid32x, measured.

### Handedness and axis-sign gotcha when porting
- Source: S32X-SKILL, references/software-3d.md:91-102
- What it does and why it is clever: Symptoms: mirrored steering, scenery receding as you drive forward, objects facing away. Fix with a sign flip when rebuilding the heading, e.g. `atan2(dx, −dy)` instead of `(dx, dy)`. Test: approaching objects must grow; if they shrink, your forward axis is flipped.
- Key numbers: —
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: speed-haste-32x applies exactly this fix.

### Wireframe / vector rendering
- Source: S32X-SKILL, references/software-3d.md:109-113
- What it does and why it is clever: Project vertices as usual and draw edges with Bresenham lines. No rasteriser and no depth sort. A whole game can run on `plot()` + `gfx_line()` into the 8bpp framebuffer.
- Key numbers: —
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: Shipped in wirefight-32x, xquest-32x and tempest-2k-32x (16 webs).

### Skeletal / keyframe character animation
- Source: S32X-SKILL, references/software-3d.md:129-153; references/pico8-porting.md:22-27
- What it does and why it is clever: A fighter is an 18-point skeleton with 13 tapered prism segments (each with dimensions, roll, cap flags). Authored key poses are interpolated by move and phase, with explicit windup / active / recovery phases. Per-segment light/dark CRAM pairs give colour customisation for free. Mocap can seed the poses offline; ship only the baked keyframes.
- Key numbers: 18 points, 13 segments, 117 keyframes (converted from the cart).
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: Shipped in hit8ox-32x and fighting-game-3D-32X.

---

## NEW: Pseudo-3D roads and Mode 7

### Per-scanline depth table for a Mode-7 floor
- Source: S32X-SKILL, references/software-3d.md:115-124; references/optimization.md:213-214; references/pico8-porting.md:65-67
- What it does and why it is clever: Precompute `z_fov_table[row]`, the ground distance for each screen row below the horizon, once at init. The floor loop reads it instead of dividing. Then step fixed-point (u,v) across the row and fetch tile pixels with shifts and lookups. The skill names the table but gives no formula. The standard form (my addition): `z(y) = cam_h·focal/(y − y_hor)`, with per-pixel world step `z/focal` along the rotated right vector.
- Key numbers: `z_fov_table[128]` (or [SCREEN_H]). The inner loop is "a few shifts + two lookups".
- Target chapter: NEW: Pseudo-3D roads and Mode 7
- Evidence: Shipped in apex-vector-60-32x.

### Tile lookup by shifts plus a sprite-offset table
- Source: S32X-SKILL, references/pico8-porting.md:68-70; references/optimization.md:215-217
- What it does and why it is clever: Build `sprid_to_gfx_offset[256]` at startup (sprite id → byte offset in the 128×128 sheet). Replace `/` and `%` in tile and pixel addressing with `>>16`, `>>13`, `&127`, so the inner loop is a couple of shifts and two array reads.
- Key numbers: 256 entries. Sheet 128×128.
- Target chapter: NEW: Pseudo-3D roads and Mode 7
- Evidence: apex-vector-60-32x.

### Segmented OutRun-style road
- Source: S32X-SKILL, references/software-3d.md:121-124; references/examples.md:14-17
- What it does and why it is clever: The road is a list of segments with forks and per-stage themes, and objects are scaled sprites. Usually much cheaper than polygons for ground racers.
- Key numbers: —
- Target chapter: NEW: Pseudo-3D roads and Mode 7
- Evidence: cannonball-outrun-32x and skyroads-32x (1:1 reverse-engineered). Described only.

### Only fill what the road does not cover
- Source: S32X-SKILL, references/optimization.md:348-350
- What it does and why it is clever: The road rasteriser records its left/right extent per scanline, and grass is filled only beside it instead of under it.
- Key numbers: Overdraw 1.36× → 1.05×. About 21 K pixel writes per frame saved.
- Target chapter: NEW: Pseudo-3D roads and Mode 7
- Evidence: Measured (racer log).

### Pre-baked view-angle sprites
- Source: S32X-SKILL, references/software-3d.md:213-221
- What it does and why it is clever: Render each 3D model offline at N view angles, pick the nearest angle at runtime, and scale by depth with an offline row/scale table. The "3D" costs one scaled blit.
- Key numbers: 46 OBJ models → 8 angles × 48×48 (wave-rider-gp). 64 angles for Death Dash Crash cars.
- Target chapter: NEW: Pseudo-3D roads and Mode 7
- Evidence: Shipped in wave-rider-gp-32x and dmar.

### Sprite stacking
- Source: S32X-SKILL, references/software-3d.md:222-224
- What it does and why it is clever: Draw a stack of 2D slices with a small vertical offset and a shared rotation per slice. The result looks like a voxel object made from top-down art, with no 3D maths.
- Key numbers: —
- Target chapter: NEW: Pseudo-3D roads and Mode 7
- Evidence: Shipped in the dmar collection racers.

### Fixed-point scaled sprite stepping
- Source: S32X-SKILL, references/pico8-porting.md:71-73; references/optimization.md:218-219
- What it does and why it is clever: Replace the per-pixel divide in the scaled blitter with 16.16 `step_x = (srcW<<16)/dstW` computed once, then accumulate and read `src>>16`.
- Key numbers: More than 10× faster on billboard and car scaling.
- Target chapter: NEW: Pseudo-3D roads and Mode 7
- Evidence: apex-vector-60-32x, measured.

---

## NEW: Raycasting

### Quarter-resolution cast with a 2×2 expand using 32-bit stores
- Source: S32X-SKILL, references/software-3d.md:184-187
- What it does and why it is clever: Cast into a 128×80 8bpp buffer in SDRAM, then expand 2×2 into a 256×160 viewport. Each pair of source pixels `a,b` becomes one word `aabb`, stored to two rows, so the blit is aligned word writes. Casting at a quarter of the pixel count is the biggest single win.
- Key numbers: 128×80 = 10,240 casts → 256×160 viewport. 4 pixels per store.
- Target chapter: NEW: Raycasting
- Evidence: noudar-32x, 30 fps on one SH-2.

### One DDA per column with a column z-buffer
- Source: S32X-SKILL, references/software-3d.md:188-190
- What it does and why it is clever: Standard grid DDA per column. The one divide (ray to perpendicular distance) uses the hardware divider. Store each column's depth for occluding sprites later.
- Key numbers: 128 divides per frame at about 39 cycles each.
- Target chapter: NEW: Raycasting
- Evidence: noudar-32x.

### Per-cell textured floors and ceilings with a sky fallback
- Source: S32X-SKILL, references/software-3d.md:191-192
- What it does and why it is clever: Floors and ceilings are textured per grid cell, with animated flats (lava) and a scrolling sky wherever a cell has no ceiling.
- Key numbers: —
- Target chapter: NEW: Raycasting
- Evidence: noudar-32x.

### Two-pass billboards clipped against the column z-buffer
- Source: S32X-SKILL, references/software-3d.md:193-195
- What it does and why it is clever: Masked scenery (bars, arches, seals) is collected during the ray walk. Monsters, items and effects are depth-sorted and drawn as billboards, each column clipped against the wall z-buffer so walls occlude them correctly without a full-screen z-buffer.
- Key numbers: —
- Target chapter: NEW: Raycasting
- Evidence: noudar-32x.

### Shade-bank palette fog
- Source: S32X-SKILL, references/software-3d.md:197-205
- What it does and why it is clever: Replicate a 64-colour base palette as N darker copies in CRAM. A pixel index is `(shade<<6) | colour`, with `shade` chosen per column or billboard from depth. Fog costs nothing per pixel; it is just which bank the index lands in.
- Key numbers: 64 colours × 4 banks = 256 CRAM entries.
- Target chapter: NEW: Raycasting
- Evidence: noudar-32x.

### Shade lookup table for per-hue ramps
- Source: S32X-SKILL, references/software-3d.md:206-209
- What it does and why it is clever: When the palette is organised as 16-step brightness ramps per hue, `shade_lut[d][i] = (i & 0xF0) | min(0x0F, (i & 0x0F) + d)`. The blitter indexes through it, so one table read gives fog.
- Key numbers: depth × 256 bytes.
- Target chapter: NEW: Raycasting
- Evidence: breakfree-32x.

### Smooth camera over turn-based grid movement
- Source: S32X-SKILL, references/strategy-and-grid.md:18-20
- What it does and why it is clever: Logic moves one cell or 90° per turn. The camera slides 1/8 cell and 1/32 turn per frame, so a turn-based crawler scrolls like a free-look one.
- Key numbers: 8 frames per step, 8 frames per 90° turn.
- Target chapter: NEW: Raycasting
- Evidence: noudar-32x.

---

## NEW: Voxel landscapes

### Procedural, step-quantised heightmap world
- Source: S32X-SKILL, references/voxel-landscape.md:14-31
- What it does and why it is clever: An NX × NZ grid. Height is a sum of a few `r3d_sin/cos` waves plus features (river valley, plateau, volcano), quantised with `h = (h/QSTEP)·QSTEP` for the blocky look. Colour comes from height bands (water/sand/grass/rock/snow). Forward motion advances a 16.16 `scroll`: `worldz = slice + (scroll>>16)`, and the fraction offsets depth smoothly.
- Key numbers: 32 × 28 grid. Scale rule: near cell width `CELL·FOCAL/NEAR ≈ 10 px`, so CELL = 1, FOCAL = 120 gives NEAR ≈ 12. Putting the near plane at z ≈ 1 projects everything off-screen and gives a black frame.
- Target chapter: NEW: Voxel landscapes
- Evidence: zepton32x.

### Method A: per-cell billboards, painted far to near
- Source: S32X-SKILL, references/voxel-landscape.md:68-94
- What it does and why it is clever: For each slice from far to near: one reciprocal `rf`, `size = (CELL>>8)·rf>>12`, then for each column a rectangle of width `size+1` and height `2·size+2` at `sy = HOR + ((CAMY−h)>>8)·rf>>12`. When size ≥ 2 a 1-px white "lit ridge" is drawn on top. Heights are sampled once per cell, but it needs a full clear and pays for overdraw.
- Key numbers: About 900 samples per frame (32×28). Column height 2× size is the balance point; 3× looks solid but costs too much fill.
- Target chapter: NEW: Voxel landscapes
- Evidence: Shipped default in zepton32x (about 19 fps).

### Method B: per-screen-column y-buffer raycaster
- Source: S32X-SKILL, references/voxel-landscape.md:96-121
- What it does and why it is clever: For each 2-px screen column, march near to far with `ybuf = SCREEN_H`. Inverse-project the column to world x, sample the height, and when `sy < ybuf` draw a span from `sy` to `ybuf` and set `ybuf = sy`. Every pixel is painted once and only the sky band needs clearing.
- Key numbers: 160 columns × 28 slices ≈ 4480 height samples per frame.
- Target chapter: NEW: Voxel landscapes
- Evidence: Built and measured in zepton32x; not shipped.

### Compute versus fill-rate measurement (A beat B)
- Source: S32X-SKILL, references/voxel-landscape.md:123-137; references/optimization.md:197-205
- What it does and why it is clever: With trig-heavy height sampling (2 sin + 1 cos per sample), B became compute-bound and lost. The fix the skill proposes but did not ship: compute the frame's heightmap grid once (about 900 samples) and let B read or interpolate from that array, so B becomes fill-bound. Rule: a rewrite you built is not a rewrite you should ship until it measures better.
- Key numbers: B ≈ 8 fps vs A ≈ 19 fps.
- Target chapter: NEW: Voxel landscapes
- Evidence: Measured in PicoDrive with the frame-counter bar.

### Into-the-screen projectiles and approaching enemies
- Source: S32X-SKILL, references/voxel-landscape.md:139-152
- What it does and why it is clever: Gameplay runs in screen space with a progress value `p` from 0 to 1. Bullets are `lerp(launch, target, p)` with size shrinking as p grows. Homing missiles re-blend the target each frame with `tx += (reticle − tx) >> 3`. Enemies run the reverse: `x = 160 + lane·SPREAD·p`, `y = HOR + (PLAYER_Y − HOR)·p`, `size ∝ p`. No 3D maths is needed, and lock-on/hit is just a screen-space overlap test, all host-testable.
- Key numbers: Homing gain 1/8 per frame.
- Target chapter: NEW: Voxel landscapes
- Evidence: zepton32x (`weapons.c`), host tests.

---

## NEW: 2D drawing primitives

### Clipped horizontal span as the only pixel writer
- Source: S32X-SKILL, assets/2d/gfx_shapes.c:15-25; references/2d-and-shmup.md:9-20
- What it does and why it is clever: `hspan(x0,x1,y,c)` rejects rows off-screen, orders x0/x1, clamps to [0, W−1] and fills bytes. Every shape reduces to spans, so clipping lives in one place.
- Key numbers: Stride = SCREEN_W (320).
- Target chapter: NEW: 2D drawing primitives
- Evidence: shmup32x.

### Triangle fill by per-row edge intersection
- Source: S32X-SKILL, assets/2d/gfx_shapes.c:27-43
- What it does and why it is clever: For each row in [ymin, ymax], intersect all three edges, `x = ax + (bx−ax)(y−ay)/(by−ay)`, and keep min/max as the span. Horizontal edges contribute both endpoints. It is order-independent with no vertex sort, simpler than the r3d version, but it does three integer divides per row; the edge-slope trick would remove them.
- Key numbers: Up to 3 divides per row.
- Target chapter: NEW: 2D drawing primitives
- Evidence: shmup32x.

### Circle fill by integer square root per row
- Source: S32X-SKILL, assets/2d/gfx_shapes.c:45-54
- What it does and why it is clever: For each dy in [−r, r], find the largest dx with `(dx+1)² ≤ r² − dy²` and draw `hspan(cx−dx, cx+dx)`. No floats and no divides. The linear-search square root makes it O(r²) overall; for big circles carry dx between rows (it only shrinks moving away from the centre) or use a midpoint circle.
- Key numbers: —
- Target chapter: NEW: 2D drawing primitives
- Evidence: shmup32x.

### Polygon fill as a triangle fan with scaling
- Source: S32X-SKILL, assets/2d/gfx_shapes.c:56-65
- What it does and why it is clever: Takes relative `signed char` point pairs scaled by `num/den` and fans triangles from (cx,cy). Correct for star-shaped outlines visible from the centre, such as ships and enemies. Scaling one shape table gives multiple sizes.
- Key numbers: 2 bytes per vertex.
- Target chapter: NEW: 2D drawing primitives
- Evidence: shmup32x.

### Faithful graphics reconstruction from the original's draw code
- Source: S32X-SKILL, references/2d-and-shmup.md:32-51
- What it does and why it is clever: Grep the original (canvas or PICO-8) for colour literals and build CRAM from the exact `#rrggbb` values. Grep `moveTo/lineTo` paths for vertices and reproduce them with FillPoly/FillTri/FillCircle, scaled to the hitbox.
- Key numbers: About 40 px ship on a 600 px canvas → about 20 px on 224.
- Target chapter: NEW: 2D drawing primitives
- Evidence: shmup32x.

### Stipple / Bayer transparency in 8bpp indexed mode
- Source: S32X-SKILL, references/2d-and-shmup.md:134-138
- What it does and why it is clever: With no hardware alpha, skip a fraction of pixel writes in an ordered pattern: 1-in-2 for 50%, a 4×4 Bayer threshold for 16 levels. Zero memory cost; the screen-door look is acceptable for fades.
- Key numbers: 4×4 Bayer gives 16 levels.
- Target chapter: NEW: 2D drawing primitives
- Evidence: pail-court-of-demon-king-32x (33 portraits).

### Blend lookup table
- Source: S32X-SKILL, references/2d-and-shmup.md:139-142
- What it does and why it is clever: `blend[src][dst] → index`, computed offline by mixing the two palette RGBs and snapping to the nearest palette entry. One table read per pixel for a true translucent blend.
- Key numbers: 64 KiB per level (256×256). Keep only the levels you use (25/50/75%).
- Target chapter: NEW: 2D drawing primitives
- Evidence: Described.

### Software zoom by fixed-point source stepping
- Source: S32X-SKILL, references/2d-and-shmup.md:143-152
- What it does and why it is clever: Walk the destination rectangle with `src += (1<<16)·srcW/dstW` and read `src>>16`, skipping index 0. The step is computed once. Zoom and alpha are tweened over elapsed vblanks so animation keeps real time when the frame rate varies.
- Key numbers: 100-1000% zoom, 0-100% transparency.
- Target chapter: NEW: 2D drawing primitives
- Evidence: Pail RM2K port.

### Directional sprites by horizontal flip
- Source: S32X-SKILL, references/strategy-and-grid.md:70-74
- What it does and why it is clever: Store east-facing frames only and mirror them for west-facing directions.
- Key numbers: Halves directional sprite ROM.
- Target chapter: NEW: 2D drawing primitives
- Evidence: warcraft-32x.

### Split-screen viewports
- Source: S32X-SKILL, references/2d-and-shmup.md:111-124
- What it does and why it is clever: Run the render pass twice with separate cameras and HUDs, each clipped to its half of the 320×224 framebuffer. Pixel writes double, so the 60/n budget gets tighter. Cohen-Sutherland clipping is also mentioned for this collection (examples.md:199).
- Key numbers: Two passes = 2× fill.
- Target chapter: NEW: 2D drawing primitives
- Evidence: dmar collection.

---

## NEW: Game logic patterns

### Deterministic integer grid logic, interpolated rendering
- Source: S32X-SKILL, references/strategy-and-grid.md:8-23
- What it does and why it is clever: The simulation (collision, A*, rules) uses only whole cells. The renderer interpolates the visual position between cells. Interpolated values never feed back into logic, so saves, replays and host tests stay exact.
- Key numbers: 64×64 RTS grid. About 12-frame sub-tile interpolation.
- Target chapter: NEW: Game logic patterns
- Evidence: warcraft-32x, noudar-32x.

### A* pathfinding with octile heuristic and no corner cutting
- Source: S32X-SKILL, references/strategy-and-grid.md:25-40
- What it does and why it is clever: 8-direction movement with `h = D·max(dx,dy) + (D2−D)·min(dx,dy)`. A diagonal step is illegal if either orthogonal neighbour is blocked. Building footprints block multiple cells, other units are transient obstacles, a blocked goal falls back to the nearest reachable cell, and a stuck unit replans. Open and closed sets are preallocated to the grid size, so there is no heap. It is a HAL-free translation unit with host tests for direct, detour, corner-cut and unreachable cases.
- Key numbers: D2/D ≈ √2 (e.g. 14/10).
- Target chapter: NEW: Game logic patterns
- Evidence: warcraft-32x, host-tested.

### Three-state fog of war
- Source: S32X-SKILL, references/strategy-and-grid.md:42-53
- What it does and why it is clever: Each cell is Unknown (draw blank), Fog (draw remembered terrain and buildings, hide live enemies and projectiles) or Visible. It is recomputed each frame from unit sight radii, one byte per cell, and the minimap only reveals explored cells.
- Key numbers: 1 byte per cell (4 KiB for 64×64).
- Target chapter: NEW: Game logic patterns
- Evidence: warcraft-32x.

### RTS AI, economy and construction as small state machines
- Source: S32X-SKILL, references/strategy-and-grid.md:55-68
- What it does and why it is clever: Each unit has states for aggro scan, attack-move, retaliation, pursuit, range, cooldown and armour. Damage lands at impact time after a windup; death leaves a persistent non-blocking corpse; projectiles have travel time. Workers loop harvest → return → deposit, and exhausted forest tiles flip to passable. Construction validates the footprint and grows hit points over time. Player and enemy units run the same code.
- Key numbers: —
- Target chapter: NEW: Game logic patterns
- Evidence: warcraft-32x.

### Turn-based crawler rules and flood-fill triggers
- Source: S32X-SKILL, references/strategy-and-grid.md:76-85
- What it does and why it is clever: `damage = attack − defense`. Monsters act once per player turn and chase along the dominant axis. A flood fill opens a whole section ("you hear mechanisms"). The original 40×40 ASCII levels are parsed with their tile-property sheets.
- Key numbers: About 32 host assertions.
- Target chapter: NEW: Game logic patterns
- Evidence: noudar-32x.

### Rational tick accumulator matching the original's rate
- Source: S32X-SKILL, references/porting-workflow.md:58-61, 117-118
- What it does and why it is clever: Capture the original tick rate as an exact num/den and drive the core from `mars_vblank_count` with an accumulator, rather than one tick per frame. SkyRoads runs at 36.0036 Hz derived from a 180 Hz PIT interrupt.
- Key numbers: 36.0036 Hz.
- Target chapter: NEW: Game logic patterns
- Evidence: skyroads-32x.

### Fixed game tick decoupled from rendering
- Source: S32X-SKILL, references/testing.md:257-265; references/examples.md:118-120, 192-193
- What it does and why it is clever: When a frame takes about 30 ms, pace logic at exactly 3 vblanks per tick (20 Hz) so recorded input grids line up tick for tick between the desktop oracle and the ROM. Other games use a 30 Hz fixed tick for physics with a variable-rate renderer.
- Key numbers: 20 Hz or 30 Hz ticks. Harness inputs are tripled.
- Target chapter: NEW: Game logic patterns
- Evidence: beachy-beachy-ball-32x (replay-verified), wave-rider-gp-32x.

### Timers advanced by elapsed vblanks
- Source: S32X-SKILL, references/porting-workflow.md:458-462
- What it does and why it is clever: Every wait, move route, typewriter effect and battle pace advances by the number of 60 Hz vblanks the frame actually covered. Real-time pacing survives a frame rate of about 28 fps.
- Key numbers: —
- Target chapter: NEW: Game logic patterns
- Evidence: raintown-slickers-32x.

### Menu flow state machine with rising-edge input
- Source: S32X-SKILL, references/2d-and-shmup.md:53-73
- What it does and why it is clever: A single `flow` enum (TITLE/SHIPSEL/DIFF/PLAY/OVER) gates update and draw. Menus react to `nav && !prevNav` so one press advances one screen.
- Key numbers: —
- Target chapter: NEW: Game logic patterns
- Evidence: shmup32x.

### Event-driven sound by diffing state
- Source: S32X-SKILL, references/2d-and-shmup.md:75-90
- What it does and why it is clever: `main` snapshots counters (hp, particles, cooldown) before `game_update` and fires SFX on the differences. The game module never calls the PWM API, so it stays pure and host-testable.
- Key numbers: —
- Target chapter: NEW: Game logic patterns
- Evidence: shmup32x.

### Zero entire entity pools on reset; fixed pools with no heap
- Source: S32X-SKILL, references/2d-and-shmup.md:92-98; references/examples.md:142-143
- What it does and why it is clever: Clearing only the `alive` flags left stale velocities and a "ghost boss" from a field added later. Memset the whole arrays on reset. Use fixed pools sized at compile time.
- Key numbers: Raptor: 20 enemies, 64+64 shots, 24 explosions.
- Target chapter: NEW: Game logic patterns
- Evidence: shmup32x bug, raptor32x.

### Attract / demo mode from a bot input stream
- Source: S32X-SKILL, references/optimization.md:223-229
- What it does and why it is clever: After a period of idle time, feed scripted input into the real game loop. It is what arcade players expect, it keeps the render path smoke-tested, and the same stream seeds record/replay tests.
- Key numbers: About 7.5 s before the demo starts.
- Target chapter: NEW: Game logic patterns
- Evidence: apex-vector-60-32x.

### BFS road pathfinding and a tiny-RAM simulation
- Source: S32X-SKILL, references/examples.md:105-107
- What it does and why it is clever: A city builder runs its grid simulation with BFS road connectivity and a day/night palette shift.
- Key numbers: About 7 KiB SDRAM. 4-voice PWM.
- Target chapter: NEW: Game logic patterns
- Evidence: pico-city-builder-32x (described only).

---

## NEW: PICO-8 compatibility layer

### Convert the cart, do not embed a PICO-8 interpreter
- Source: S32X-SKILL, references/pico8-porting.md:1-27
- What it does and why it is clever: Pull `__gfx__`, `__map__`, `__gff__`, `__sfx__` and Lua tables from the unmodified `.p8` with a build tool (`iconv -c` handles the non-UTF-8 sections). Emit C arrays and reimplement the logic in native C.
- Key numbers: gfx 128×128 at 1 byte per pixel, map 128×32-64, gff 256.
- Target chapter: NEW: PICO-8 compatibility layer
- Evidence: Five shipped PICO-8 ports.

### `pico8_api` shim: palette to CRAM, pal swaps, transparent 0
- Source: S32X-SKILL, references/pico8-porting.md:29-47
- What it does and why it is clever: Upload the fixed 16-colour PICO-8 palette to CRAM once. `pico_pal()` does palette remaps, `spr/sspr` blit from `gfx_data` with colour 0 transparent, and `print` uses a small bitmap font. Game code then reads almost like the Lua.
- Key numbers: 16 colours, RGB555.
- Target chapter: NEW: PICO-8 compatibility layer
- Evidence: apex-vector-60-32x and others.

### PICO-8 angle convention for atan2, sin and cos
- Source: S32X-SKILL, references/pico8-porting.md:42-46
- What it does and why it is clever: PICO-8 angles run 0..1 with 0 = right, 0.25 = up (dy < 0), 0.5 = left, 0.75 = down. Its `sin` is inverted to match screen-down y. Implement `pico_atan2(dx,dy)` and `pico_sin/cos` to match exactly, or everything spawns facing 180° wrong.
- Key numbers: —
- Target chapter: NEW: PICO-8 compatibility layer
- Evidence: Shipped ports.

### Resolution: native re-projection or logical doubling
- Source: S32X-SKILL, references/pico8-porting.md:49-58
- What it does and why it is clever: 3D and Mode-7 games re-project natively at 320×224. 2D games render a logical 160×112 surface and pixel-double it in `pico_present`. Doubling pairs well with 32-bit stores (two source pixels → one `aabb` word) and the line-table trick (two display lines pointing at one row).
- Key numbers: 160×112 → 320×224.
- Target chapter: NEW: PICO-8 compatibility layer
- Evidence: picohot-32x.

### Faithful down to silence
- Source: S32X-SKILL, references/pico8-porting.md:81-89
- What it does and why it is clever: If the cart ships sound data but never calls `sfx()` or `music()`, the port stays silent.
- Key numbers: —
- Target chapter: NEW: PICO-8 compatibility layer
- Evidence: hit8ox-32x.

---

## patterns/60fps.md

### 60/n vblank quantisation
- Source: S32X-SKILL, references/optimization.md:231-239; SKILL.md:266-270
- What it does and why it is clever: `Mars_FlipFrameBuffers` waits for vblank, so frame rate can only be 60, 30, 20, 15 and so on. Going slightly over a boundary halves the rate. Optimise to get under the next boundary, and measure the boundary rather than raw pixel counts.
- Key numbers: 60/n.
- Target chapter: patterns/60fps.md
- Evidence: arkanoid32x.

### Dirty rectangles over a cached background, tracked per framebuffer
- Source: S32X-SKILL, references/optimization.md:254-272
- What it does and why it is clever: Compose the static view into `s_bg[]` once and rebuild it only when a cheap signature of its inputs changes. Each frame, restore the rectangles under moving objects from `s_bg`, then draw them. Because the 32X page-flips, keep `s_dirty[2][]` per buffer; a single list leaves smears every other frame. Cache the HUD keyed on a hash of score, lives and level.
- Key numbers: About 932 px per frame instead of about 24,278 (about 25×). 29 → 60 fps.
- Target chapter: patterns/60fps.md
- Evidence: arkanoid32x, measured.

### Attack overdraw and fill-rate before arithmetic
- Source: S32X-SKILL, references/optimization.md:135-145, 183-195
- What it does and why it is clever: Hoisting about 1800 divides changed nothing, while shortening voxel columns took the game from 12 to 20 fps. If cutting vertex or cell counts does not help, you are fill-bound. A full 320×224 clear alone cost about 9 game iterations of budget.
- Key numbers: 12 → 20 fps. Clear = 71,680 bytes.
- Target chapter: patterns/60fps.md
- Evidence: zepton32x, measured.

### Shrink the work
- Source: S32X-SKILL, references/optimization.md:47-50
- What it does and why it is clever: Render a narrower or shorter internal buffer, add a "potato" mode with solid-colour floors and ceilings, cap draw distance, and reject off-screen objects early.
- Key numbers: —
- Target chapter: patterns/60fps.md
- Evidence: d32xr idioms.

### Inline the hot span fill
- Source: S32X-SKILL, references/optimization.md:356-358
- What it does and why it is clever: At about 1600 spans per frame, the span function's call and re-clip overhead was 62% of all span time. Inline it and use a `col → 4·col` word table so 32-bit stores need no shift or OR per span.
- Key numbers: 62% overhead.
- Target chapter: patterns/60fps.md
- Evidence: Measured (racer log).

---

## patterns/bus.md

### Framebuffer writes are uncached I/O: write aligned 32-bit words
- Source: S32X-SKILL, references/optimization.md:185-186, 220-221, 291-293, 359-360
- What it does and why it is clever: Every byte written to `0x24000000` is a bus transaction. Pack four 8bpp pixels per `uint32_t` and unroll. Keep tiles and the camera on 4-px boundaries so a 16-px tile row is exactly four aligned stores.
- Key numbers: A full 320×224 present takes about 0.3 ms. A map layer is about 19 K longs.
- Target chapter: patterns/bus.md
- Evidence: apex-vector-60-32x, racing-circuit-32x.

### Use DMA for large copies and overlap it with compute
- Source: S32X-SKILL, references/optimization.md:57-58
- What it does and why it is clever: Framebuffer fills and sample streaming via SH-2 DMA free the CPU.
- Key numbers: —
- Target chapter: patterns/bus.md
- Evidence: Described (d32xr).

### Immutable data stays in ROM and is read in place
- Source: S32X-SKILL, references/architecture.md:24-26; references/porting-workflow.md:168-174
- What it does and why it is clever: Decoded graphics, palettes, music and levels are read directly from the cartridge at `0x02000000`, which is cacheable and read-only. Only mutable state goes in SDRAM, which is how multi-megabyte games fit in 256 KiB of RAM.
- Key numbers: 256 KiB SDRAM versus a ~4 MiB ROM window.
- Target chapter: patterns/bus.md
- Evidence: All shipped ports.

---

## patterns/cache.md / sh2/cache.md

### Cache-line-aligned hot routines in SDRAM
- Source: S32X-SKILL, references/architecture.md:27-32; references/optimization.md:52-55, 290-291
- What it does and why it is clever: d32xr's `ATTR_DATA_CACHE_ALIGN` = `section(".sdata"), aligned(16), optimize("O1")`. It puts inner loops in SDRAM (copied at boot) on 16-byte cache-line boundaries, so they run cached and don't straddle lines. The pinned optimisation level stops LTO from changing their timing.
- Key numbers: 16-byte alignment.
- Target chapter: sh2/cache.md
- Evidence: d32xr, wave-rider-gp.

### Cross-core coherency: cache-through or explicit purge
- Source: S32X-SKILL, references/architecture.md:152-160, 211-215; references/audio.md:138-140
- What it does and why it is clever: SDRAM at `0x06000000` is cached separately on each SH-2. Anything one core writes for the other (audio command blocks, job descriptors) must be read through the uncached alias or cleared with `Mars_ClearCacheLine/ClearCache`. Otherwise the slave mixes stale commands; this fails on hardware but not in some emulators.
- Key numbers: —
- Target chapter: patterns/cache.md
- Evidence: Described; hardware-only bug class.

### Disjoint rows of the uncached framebuffer need no cache work
- Source: S32X-SKILL, references/architecture.md:154-157, 227-230
- What it does and why it is clever: Because the framebuffer bypasses the cache, two cores writing different rows (the slave fills the sky, the master draws the rest) need no synchronisation beyond the job ack.
- Key numbers: —
- Target chapter: patterns/cache.md
- Evidence: racing-circuit-32x ("sky on the slave over disjoint rows").

---

## patterns/cpu-split.md

### Role assignment across three CPUs
- Source: S32X-SKILL, references/architecture.md:6-17; SKILL.md:156-159
- What it does and why it is clever: The master SH-2 runs game logic and drives the frame. The slave runs one heavy parallel job (PWM mixing or a render phase). The 68000 polls pads, services VBlank, plays YM2612/PSG music and handles SRAM. Using the idle slave is described as the biggest single 32X speedup.
- Key numbers: 2 × 23 MHz SH-2, 68000 at 7.6 MHz.
- Target chapter: patterns/cpu-split.md
- Evidence: d32xr and the ports.

### Offload stage 1: framebuffer clear on the slave with a bounded wait
- Source: S32X-SKILL, references/optimization.md:115-131; references/architecture.md:136-150
- What it does and why it is clever: The master posts `0x8000 | colour`, runs game logic while the slave clears, then waits for the ack before drawing. The framebuffer is uncached and the work is disjoint, so no cache handling is needed. The wait is bounded so a dead slave only slows the frame. The slave dispatcher is a few lines of assembly replacing the `crt0.s` idle loop (interrupts masked, registers only).
- Key numbers: About 72 KB of writes per frame. Wait capped at about 200 k spins.
- Target chapter: patterns/cpu-split.md
- Evidence: fighting-game-3D-32X, voxel ports.

### Offload stage 2: split rasterisation
- Source: S32X-SKILL, references/optimization.md:128-131
- What it does and why it is clever: The master draws the top half and the slave the bottom. Shared geometry in cached SDRAM needs real coherency work, so do it as its own milestone.
- Key numbers: —
- Target chapter: patterns/cpu-split.md
- Evidence: Described only.

### Slave dedicated to audio
- Source: S32X-SKILL, references/architecture.md:206-209; references/optimization.md:303-304
- What it does and why it is clever: A slave reserved for the PWM FIFOs means master render spikes can never starve the mixer. Unsynchronised render work on the slave risks FIFO underruns, so a free core is not automatically a free win.
- Key numbers: —
- Target chapter: patterns/cpu-split.md
- Evidence: wave-rider-gp, raintown, tempest-2k (slave = real-time PWM synth with a 140 BPM loop).

### Slave as a command and cache service
- Source: S32X-SKILL, references/architecture.md:210
- What it does and why it is clever: An RTS keeps gameplay and rendering on the master and runs a command/cache service on the slave.
- Key numbers: —
- Target chapter: patterns/cpu-split.md
- Evidence: warcraft-32x (described).

---

## 32x/communication.md

### d32xr COMM job-dispatch loop
- Source: S32X-SKILL, references/architecture.md:95-111
- What it does and why it is clever: The slave's `Mars_Secondary` spins on a command word, runs the routine, and writes `NONE` back. The master's `Mars_R_SecWait()` waits for idle, writes parameters to another COMM word, then the command. Examples: clear cache, wall prep, planes, sprites, fire, sound DMA, sight checks, melt wipe, RoQ.
- Key numbers: COMM0-COMM14 (16-bit words).
- Target chapter: 32x/communication.md
- Evidence: d32xr.

### Deliberate COMM slot map with static and runtime guards
- Source: S32X-SKILL, references/architecture.md:217-230; references/testing.md:441-451
- What it does and why it is clever: The boot handshake (M_OK/S_OK), security checksum (COMM8), 68000 pad (COMM12/14), telemetry and jobs all share 8 words. A job sharing COMM4 with `S_OK` let the slave run before FM was granted and corrupt VDP registers, producing a doubled image. Keep a documented slot map, a `check_comm.py` grep for overlaps, and a left/right symmetry assertion in the emulator tests.
- Key numbers: COMM2 is suggested for jobs.
- Target chapter: 32x/communication.md
- Evidence: racing-circuit-32x bug.

### Sequence-number edge detection for commands
- Source: S32X-SKILL, references/audio.md:240-255
- What it does and why it is clever: Each request word is `(seq7 << 8) | id`, plus a loop bit and a stop sentinel `0x7F`. The receiver reacts when `seq` changes, not when the value changes, so playing the same id twice in a row still fires. The master side is a single store.
- Key numbers: 7-bit seq. COMM2 = BGM, COMM4 = SFX, COMM6 = slave heartbeat, COMM0 = "video ready" magic that gates PWM init.
- Target chapter: 32x/communication.md
- Evidence: raintown-slickers-32x.

### Boot handshake ordering traps
- Source: S32X-SKILL, references/architecture.md:113-128; references/testing.md:430-436
- What it does and why it is clever: Re-read the handshake register before clearing the release flag; releasing through a stale value stalls. Grant FM before the M_OK handshake or both sides wait forever. A minimal 68000 side must publish the ROM checksum in COMM8 to satisfy the security block.
- Key numbers: —
- Target chapter: 32x/communication.md
- Evidence: Black-screen catalogue (racer).

### TAS-based spinlocks
- Source: S32X-SKILL, references/toolchain-and-build.md:38-39
- What it does and why it is clever: `-mtas` lets GCC emit the SH-2 atomic test-and-set instruction, used for inter-CPU spinlocks.
- Key numbers: —
- Target chapter: 32x/communication.md
- Evidence: Toolchain flags.

---

## 32x/pwm.md

### PWM registers, cycle and sample rate
- Source: S32X-SKILL, references/audio.md:11-21, 233-236
- What it does and why it is clever: Control at 0x20004030, cycle at 0x20004032, L/R/mono FIFOs at 0x20004034/36/38. `cycle = SH2_clock / rate`. My arithmetic: 23.011 MHz / 11025 ≈ 2087; `NTSC_SH2 / 1045` ≈ 22.02 kHz.
- Key numbers: 11,025 Hz is the robust choice; about 22 kHz for streaming.
- Target chapter: 32x/pwm.md
- Evidence: tracker-player-32x (PCM-capture verified).

### Safe amplitude range
- Source: S32X-SKILL, references/architecture.md:70-74; references/audio.md:21
- What it does and why it is clever: Sample values must stay inside about 2..1032. My inference: the value range is bounded by the cycle count (about 1045 at 22 kHz, so roughly 10 bits). Clamp after mixing.
- Key numbers: 2..1032. The skill also says "~12-bit" elsewhere, which is inconsistent.
- Target chapter: 32x/pwm.md
- Evidence: d32xr (described).

### Keep the tiny FIFO fed: polling or DMA
- Source: S32X-SKILL, references/audio.md:40-48
- What it does and why it is clever: The FIFO holds only a few entries. Either poll-fill at the sample rate (deterministic, emulator-friendly) or stream through SH-2 DMA with half/full refill interrupts.
- Key numbers: —
- Target chapter: 32x/pwm.md
- Evidence: Tracker polls.

### Framebuffer redraw starves the FIFO into buzz
- Source: S32X-SKILL, references/audio.md:50-60
- What it does and why it is clever: A long full-framebuffer write blocks refills and the output becomes a frame-rate buzz. Initialise both framebuffers before starting PWM, redraw only on change, or move audio to the slave, a timer or DMA.
- Key numbers: —
- Target chapter: 32x/pwm.md
- Evidence: tracker-player-32x.

### Timing-critical mixer at fixed -O2 without LTO
- Source: S32X-SKILL, references/optimization.md:77-80; assets/Makefile:37-38
- What it does and why it is clever: The mixer must meet a per-sample deadline, so its object is pinned to `-O2 -fno-lto` (d32xr uses `-O1 -fno-lto` for `marshw.c`) so whole-program LTO cannot reshape it. This conflicts with the mixed-`-O` miscompile trap (problem 4).
- Key numbers: 1/22050 s deadline.
- Target chapter: 32x/pwm.md
- Evidence: d32xr.

---

## patterns/audio.md

### Software voice mixer
- Source: S32X-SKILL, references/audio.md:23-30, 76-90
- What it does and why it is clever: Each voice has `{pos (fixed-point), loop_start/end, pitch_inc, vol, pan}`. Per output sample: `L = Σ s[pos>>F]·vol·(1−pan)`, `R = Σ …·pan`, clamp, push to FIFO, `pos += inc` with loop wrap. Eight voices fit on one SH-2. Row-0 with all 8 notes is the stress test.
- Key numbers: 8 voices at 11,025 Hz stereo.
- Target chapter: patterns/audio.md
- Evidence: tracker-player-32x, verified by PCM capture against an OpenMPT render.

### Voice stealing for priority SFX
- Source: S32X-SKILL, references/audio.md:32-34, 88-89
- What it does and why it is clever: An SFX takes over an existing voice (for example voice 8) instead of using a ninth, and the next music note on that lane reclaims it. The voice budget stays fixed and behaviour stays deterministic.
- Key numbers: —
- Target chapter: patterns/audio.md
- Evidence: tracker-player-32x.

### Validate sample formats in the converter
- Source: S32X-SKILL, references/audio.md:35-38
- What it does and why it is clever: The build tool rejects packed, 16-bit or stereo instruments instead of letting the runtime mis-decode them. One format (8-bit mono unpacked) keeps the mixer simple.
- Key numbers: —
- Target chapter: patterns/audio.md
- Evidence: Tracker converter.

### Compute gain once per block, not per sample
- Source: S32X-SKILL, references/audio.md:135-137
- What it does and why it is clever: Per-voice gain is computed once per output block, keeping multiplies by volume and pan out of the sample loop.
- Key numbers: —
- Target chapter: patterns/audio.md
- Evidence: wave-rider-gp.

### IMA-ADPCM sample banks decoded on the slave
- Source: S32X-SKILL, references/audio.md:124-140
- What it does and why it is clever: Store clips as 4-bit IMA ADPCM with each clip's starting predictor and step index in ROM. The slave runs the predictor/step-index state machine per voice (4 bits in, one 16-bit sample out), sums and clamps. The skill gives no decoder details. Standard IMA (my addition): 89-entry step table, `diff = step>>3 + (b2?step) + (b1?step>>1) + (b0?step>>2)`, sign from b3, index += {−1,−1,−1,−1,2,4,6,8}.
- Key numbers: About 4:1 compression. 26 sounds at 11,025 Hz mono.
- Target chapter: patterns/audio.md
- Evidence: wave-rider-gp-32x.

### Streaming BGM from ROM, played twice for 22 kHz, with concurrent SFX
- Source: S32X-SKILL, references/audio.md:224-238
- What it does and why it is clever: A ROM directory `(offset, num_samples, loop_flag)` indexes the tracks. One uninterrupted ADPCM stream plus a 2-voice PCM SFX layer runs on the slave. Each 11 kHz sample is output twice to reach about 22 kHz PWM, halving ROM and decode cost. Music uses zero SDRAM.
- Key numbers: 6 tracks, 11 kHz, 4-bit. 2 SFX voices. `PWM_CYCLE ≈ NTSC_SH2/1045`.
- Target chapter: patterns/audio.md
- Evidence: raintown-slickers-32x.

### BGM memorize/restore and fade
- Source: S32X-SKILL, references/audio.md:257-263
- What it does and why it is clever: RM2K-style `MemorizeBGM` before a battle and `PlayMemorizedBGM` after, plus loop and N-frame fade-out, hooked into the map loader and the battle/victory/return paths.
- Key numbers: —
- Target chapter: patterns/audio.md
- Evidence: raintown-slickers-32x.

### Genesis-side music (XGM/SGDK) with the UI on the SH-2
- Source: S32X-SKILL, references/audio.md:100-122
- What it does and why it is clever: An SGDK-built 68000 program linked at 0x880800 runs the XGM driver (Z80 + YM2612/PSG). The SH-2 draws the UI and sends play/pause/stop over COMM (SH-2 0x20004020 ↔ 68000 0xA15120). PWM stays free for SFX.
- Key numbers: 68000 ROM window 0x880800.
- Target chapter: patterns/audio.md
- Evidence: xgm-player-32x.

### 68000 VGM player paced by YM2612 Timer A with bounded waits
- Source: S32X-SKILL, references/architecture.md:75-83
- What it does and why it is clever: Convert the score to VGM 1.50 at build time and play it from a work-RAM 68000 player paced by YM2612 Timer A at the source tick rate. YM busy-waits and per-tick command batches are bounded so bad data can't stall pad/VBlank service. Leave a few dB of headroom on FM carriers so PWM SFX cut through.
- Key numbers: —
- Target chapter: patterns/audio.md
- Evidence: Described (ports).

### MIDI→VGM: routing per part, demand-driven
- Source: S32X-SKILL, references/audio.md:142-178
- What it does and why it is clever: The pipeline is Ingest (tempo map, CC64 sustain, CC7/CC11 loudness, pitch-bend cents, ch10 drums) → IR → Map/Allocate → Emit. Each part (not each note) is routed to FM or PSG so timbre never flips mid-phrase. Parts the PSG would ruin claim FM first, and the rest spills to PSG. Notes below the PSG floor (~C2) are folded up whole octaves and bass is penalised on PSG (clamping gave ~890-cent errors). Per-part mean cents error is used as a routing cost. Chords are thinned to root + top only when a pool is oversubscribed.
- Key numbers: 6 FM + 3 PSG tone + 1 noise + 1 DAC.
- Target chapter: patterns/audio.md
- Evidence: midi2vgm, verified against Nuked-OPN2.

### FM retrigger gap and role-based mixing
- Source: S32X-SKILL, references/audio.md:179-185
- What it does and why it is clever: Key-off and key-on at the same timestamp means the envelope never releases and the note goes silent; insert a gap. A 3-note pad carries about 3× the energy of one lead note, so offset levels by role and spread them across voice counts.
- Key numbers: KEY_GAP ≈ 1.5 ms. Lead −6 dB, pad +12 dB.
- Target chapter: patterns/audio.md
- Evidence: Found only with a cycle-accurate core.

### Polyphonic drums pre-mixed into the DAC, plus a PSG noise transient layer
- Source: S32X-SKILL, references/audio.md:187-201
- What it does and why it is clever: Overlapping drum hits are pre-mixed offline into one mono PCM stream on FM channel 6, so the DAC is effectively polyphonic. The 0x2B trap: an init write of `0x2B = 0` at t = 0 lands after DAC enable and kills the drums, and channel 6 must be excluded from key-off and allocation. The PSG noise channel layers a short decay over hats, snares and toms; hits within 20 ms collapse, loudest wins.
- Key numbers: DAC about 13.75 kHz, 8-bit. +44% energy in 6-15 kHz.
- Target chapter: patterns/audio.md
- Evidence: midi2vgm, regression-tested.

### VGM DAC-stream emission and calibration
- Source: S32X-SKILL, references/audio.md:203-215
- What it does and why it is clever: Command order: `0x67 0x66` data block → `0x90` (chip 0x02, port 0, reg 0x2A) → `0x91` → `0x92` → `0x2B = 0x80` → `0x93` → … → `0x94`, `0x2B = 0`. Calibrate the checker before trusting it: A4 → fnum 1083 at block 4, FM error under 1 cent for MIDI 24-107, SN76489 `f = clock/(32n)`, and an FFT round trip within about 0.1 semitone.
- Key numbers: VGM ≥ 1.61. NTSC clocks 7,670,453 / 3,579,545; PAL 7,600,489 / 3,546,895.
- Target chapter: patterns/audio.md
- Evidence: midi2vgm.

### Choosing a music path: streaming ADPCM or MIDI→VGM
- Source: S32X-SKILL, references/audio.md:265-281
- What it does and why it is clever: ADPCM plays the real recording, is simple, uses no SDRAM and mixes with SFX, but costs megabytes of ROM. VGM is tiny and authentic FM, but needs MIDI and a 68000 player.
- Key numbers: About 4 MB cart for a handful of ADPCM loops.
- Target chapter: patterns/audio.md
- Evidence: Comparison across ports.

---

## 32x/vdp.md

### Line-doubling through the per-line table
- Source: S32X-SKILL, references/optimization.md:361-364; references/architecture.md:47-50
- What it does and why it is clever: Render 112 rows and point two display lines at each row in the framebuffer line table, so the VDP doubles vertically for free.
- Key numbers: About 40% frame slack. Only worth it if that crosses a vblank boundary.
- Target chapter: 32x/vdp.md
- Evidence: Racer log.

### The palette is the top silent black-screen cause
- Source: S32X-SKILL, references/architecture.md:60-64; references/testing.md:276-281
- What it does and why it is clever: In 8bpp mode an unseeded CRAM maps every index to black. Seed before the first flip. Diagnostic: if `GFX_Clear(C_SKY)` comes out pure (0,0,0), the palette never landed or the CPU hung first; it is not a geometry problem.
- Key numbers: —
- Target chapter: 32x/vdp.md
- Evidence: Zepton black-screen ladder.

### CRAM word format
- Source: S32X-SKILL, references/testing.md:417-421
- What it does and why it is clever: `0x8000 | (B<<10) | (G<<5) | R`. Swapping R and B turns sky red. The skill says bit 15 clear = transparent (see problem 7).
- Key numbers: RGB555 + bit 15.
- Target chapter: 32x/vdp.md
- Evidence: Black-screen catalogue.

### Mode mis-set gives two half-width copies; re-assert every flip
- Source: S32X-SKILL, references/testing.md:422-429
- What it does and why it is clever: Left in direct-colour mode, each row consumes 640 bytes instead of 320, giving two half-width images with indices read as RGB555. Write every DISPMODE field explicitly and re-assert on each flip. Both buffers need a valid line table at init.
- Key numbers: 320 vs 640 bytes per row.
- Target chapter: 32x/vdp.md
- Evidence: racing-circuit-32x.

### Full-CRAM swaps for flashes and day/night
- Source: S32X-SKILL, references/software-3d.md:210-211; references/examples.md:105-106
- What it does and why it is clever: Uploading a reddened or whitened palette gives a full-screen damage or heal flash in one write with no redraw. Shifting the palette does day/night the same way.
- Key numbers: 512 bytes per CRAM upload.
- Target chapter: 32x/vdp.md
- Evidence: noudar, city builder.

---

## howto/profiling.md

### Frame-counter bar read from captures
- Source: S32X-SKILL, references/optimization.md:147-167
- What it does and why it is clever: Draw a white bar whose width is `frame & 127`. Read the bar width in two captures N emulated frames apart: `iters = (w1 − w0) & 127` is the number of game iterations, which gives effective fps from video alone.
- Key numbers: Zepton ran 12-19 iterations per 60 frames.
- Target chapter: howto/profiling.md
- Evidence: Used in PicoDrive.

### Headroom probe with calibrated ballast
- Source: S32X-SKILL, references/optimization.md:306-325
- What it does and why it is clever: fps can't show a gain that stays inside a vblank boundary. Inject calibrated busy-work and report how much the frame absorbs before dropping a step, which gives a continuous metric. Validate the instrument first: a ballast flag that never reached the compiler, and PicoDrive's dynarec idle-loop detection optimising the ballast away, both made every reading meaningless.
- Key numbers: 4,000,000 dummy iterations that "cost nothing".
- Target chapter: howto/profiling.md
- Evidence: racing-circuit-32x.

### Host-side fill-cost counter
- Source: S32X-SKILL, references/optimization.md:274-282
- What it does and why it is clever: Run the renderer's span, quad and blit calls against counters on the host. Report pixels and spans per element (backdrop, entities, HUD) to tell fill-rate limits from per-primitive setup cost.
- Key numbers: —
- Target chapter: howto/profiling.md
- Evidence: arkanoid32x (bottleneck turned out to be setup and redraw).

### Hardware timers and size tracking
- Source: S32X-SKILL, references/optimization.md:82-88; assets/Makefile:89-91
- What it does and why it is clever: Time phases on hardware with `Mars_GetTicCount`, `Mars_GetWDTCount` and `Mars_FRTCounter2Msec`. Print `sh-elf-size` and grep `__bss_end` in every build log.
- Key numbers: —
- Target chapter: howto/profiling.md
- Evidence: d32xr.

### "run N" emulated frames is not N game iterations
- Source: S32X-SKILL, references/testing.md:207-219
- What it does and why it is clever: Timers count iterations. At about 12 fps, a 40-iteration spawn needs about 200 emulated frames. Brief effects fall between captures, so capture several frames.
- Key numbers: 8-19 iterations per 60 frames.
- Target chapter: howto/profiling.md
- Evidence: Zepton.

---

## howto/toolchain.md

### GCC 12.1 trap: 12-byte struct returns
- Source: S32X-SKILL, references/toolchain-and-build.md:173-181
- What it does and why it is clever: Returning a 3-word struct by value can be corrupted. Return through an out-pointer instead (note r3d's `to_camera` returns a 12-byte `vec3`).
- Key numbers: 12 bytes.
- Target chapter: howto/toolchain.md
- Evidence: beachy-beachy-ball-32x.

### GCC 12.1 trap: 64-bit multiply chains
- Source: S32X-SKILL, references/toolchain-and-build.md:182-185
- What it does and why it is clever: Chains of `long long` multiplies can miscompile. Use the SH-2 `dmuls.l` / MAC through tiny inline-asm macros for fixed-point multiplies.
- Key numbers: —
- Target chapter: howto/toolchain.md
- Evidence: beachy-beachy-ball-32x.

### GCC 12.1 trap: dropped stores
- Source: S32X-SKILL, references/toolchain-and-build.md:186-188
- What it does and why it is clever: The optimiser can wrongly decide a store is dead. If a value doesn't stick, make the target `volatile` or route the write through an opaque pointer.
- Key numbers: —
- Target chapter: howto/toolchain.md
- Evidence: beachy-beachy-ball-32x.

### GCC 12.1 trap: calls across mixed -O levels
- Source: S32X-SKILL, references/toolchain-and-build.md:189-198
- What it does and why it is clever: Build everything at one level (`-O2`). If a routine only breaks at `-O3` or with LTO, drop that routine to `-O2` before suspecting your own logic.
- Key numbers: —
- Target chapter: howto/toolchain.md
- Evidence: beachy-beachy-ball-32x.

### `--gc-sections` can strip the whole game; guard with live markers
- Source: S32X-SKILL, references/toolchain-and-build.md:64-68; references/testing.md:88-96, 152-157; assets/verify_rom.py:89-100
- What it does and why it is clever: If entry points are unreachable, the linker keeps only the header and the ROM boots black. verify_rom checks marker strings from different translation units, `.text` ≥ 64 KiB and at least 2048 non-zero bytes. Markers must be string literals passed to a call, or `volatile`, because a `const char[]` read only as `arr[0]` gets constant-folded away.
- Key numbers: `--min-text` = 0x10000.
- Target chapter: howto/toolchain.md
- Evidence: Static check in build.

### `.sdata @progbits` vector-copy invariant
- Source: S32X-SKILL, references/toolchain-and-build.md:210-234
- What it does and why it is clever: GAS can emit `.sdata` as non-loadable, so `objcopy -O binary` writes padding where the SH-2 vectors belong and the boot ROM copies zeros. Fix: `.section .sdata,"aw",@progbits`, and verify the reset vectors are present in the raw ROM payload, not just the ELF.
- Key numbers: —
- Target chapter: howto/toolchain.md
- Evidence: tyrian-32x.

### Linker map with split stacks and a BSS guard
- Source: S32X-SKILL, assets/mars.ld:1-87; references/toolchain-and-build.md:93-111; assets/verify_rom.py:25-28, 116-118
- What it does and why it is clever: `.text/.rodata` at 0x02000000 with LMA 0. `.data` is addressed at 0x06000000 but loaded after `.text`. Then `.bss`, with the heap above it. With one CPU the stack top is 0x0603FC00. Using the slave, master = 0x0603F800 and slave = 0x06040000. The check asserts `__bss_end < 0x0603C000`.
- Key numbers: RAM length 0x3FC00 (or 0x3F800 with the slave).
- Target chapter: howto/toolchain.md
- Evidence: d32xr CI assertion.

### Embedding the 68000 program in the SH-2 ROM
- Source: S32X-SKILL, references/toolchain-and-build.md:78-91; assets/Makefile:67-79
- What it does and why it is clever: Build a tiny m68k ELF, `objcopy -O binary`, and `.incbin` it in `mars_start.s`.
- Key numbers: —
- Target chapter: howto/toolchain.md
- Evidence: Template.

### Start from a known-good tree
- Source: S32X-SKILL, references/testing.md:182-196; references/porting-workflow.md:279-286
- What it does and why it is clever: A fresh scaffold produced different SH-2 vectors and code from byte-identical sources. Instead of debugging it, `cp -r` a booting tree and swap code in file by file, or start from an MIT boot foundation (hexgl-32x).
- Key numbers: —
- Target chapter: howto/toolchain.md
- Evidence: zepton32x.

### Workspace hygiene: neutral directory names and setup.sh
- Source: S32X-SKILL, references/toolchain-and-build.md:200-208, 147-171
- What it does and why it is clever: Some sandboxes discard `dist/` and `build/` between sessions, so write output to `rom/` and `obj/`. An idempotent `setup.sh` reinstalls the toolchain and PicoDrive; distro `gcc-sh-elf` packages work as a fallback. CI caches `/opt/toolchains`.
- Key numbers: —
- Target chapter: howto/toolchain.md
- Evidence: trial-of-the-sorcerer, God of Thunder.

---

## megadrive/cartridge.md

### Header fix-up and checksum
- Source: S32X-SKILL, assets/romfix.py:1-65; assets/verify_rom.py:67-87; references/toolchain-and-build.md:113-128
- What it does and why it is clever: `SEGA 32X` at 0x100. Checksum at 0x18E = sum of big-endian 16-bit words from 0x200 to end, mod 2^16. ROM end (last byte) at 0x1A4, which must be rewritten because the stock header hardcodes 4 MiB. Mars header at 0x3C0-0x3F0: master entry 0x06000240, slave 0x06000244, VBRs 0x06000000 / 0x06000120.
- Key numbers: 8 KiB `dd` padding, 512 KiB romfix granularity, ROM ≤ 4 MiB.
- Target chapter: megadrive/cartridge.md
- Evidence: verify_rom static check.

### Banking or 32X-CD: decide before freezing asset addresses
- Source: S32X-SKILL, references/architecture.md:33-35, 232-253
- What it does and why it is clever: Emitting absolute offsets and adding banking later means rewriting the converter. Choose SSF banking (`Mars_SetBankPage`, `SEGA SSF` header) with a lazily activated banked directory, or 32X-CD, up front. Grow the ROM in powers of two.
- Key numbers: Window about 4 MiB. Franzen's source audio was about 170 MiB. 512 KiB → 1 MiB growth.
- Target chapter: megadrive/cartridge.md
- Evidence: franzen-32x.

### Defensive SRAM save format
- Source: S32X-SKILL, references/architecture.md:172-199
- What it does and why it is clever: A bounded fixed layout with magic/version header and payload checksum. Fields are serialised explicitly in a defined byte order (never memcpy'd structs). Big, mostly-default state is stored sparsely (only depleted forest cells). Validate on boot before enabling Continue. Write on request, never every frame.
- Key numbers: ≤ 2 KiB. 64×64 world diffs fit in a couple of KiB.
- Target chapter: megadrive/cartridge.md
- Evidence: warcraft-32x, with a pixel-compare restore test.

### Two-phase-commit saves
- Source: S32X-SKILL, references/architecture.md:255-262
- What it does and why it is clever: Write to a spare slot, verify it, then flip an active-slot marker. Power loss mid-write never destroys the only good save, and versioning lets old saves be rejected or migrated.
- Key numbers: —
- Target chapter: megadrive/cartridge.md
- Evidence: franzen-32x (described).

### 68000 boot image in the fixed low ROM window
- Source: S32X-SKILL, references/architecture.md:125-128
- What it does and why it is clever: Put the 68000 work-RAM image before any large blob; if the 68000 must reach past a music blob, some emulators boot black.
- Key numbers: —
- Target chapter: megadrive/cartridge.md
- Evidence: Black-screen triage.

---

## megadrive/io.md

### Mask pads to the 3-button subset
- Source: S32X-SKILL, references/architecture.md:85-93
- What it does and why it is clever: Several emulators mirror d-pad bits into the 6-button nibble during the handshake, so every direction also reads as X/Y/Z/Mode (jump/back). Mask to U/D/L/R/A/B/C/Start. The Sega Mouse is available through `Mars_PollMouse`.
- Key numbers: —
- Target chapter: megadrive/io.md
- Evidence: Real shipped bug, with a regression test.

---

## NEW: Asset pipelines and data-driven engines

### Build-time conversion to big-endian read-in-place ROM archives
- Source: S32X-SKILL, references/porting-workflow.md:83-97, 151-174
- What it does and why it is clever: Decompress, de-plane Mode-X/EGA planar art to chunky 8bpp, byte-swap 16/32-bit fields at pack time, and emit a header plus offset table. C code then reads structs straight from ROM with no runtime conversion. Regeneration sits behind a stamp file.
- Key numbers: —
- Target chapter: NEW: Asset pipelines and data-driven engines
- Evidence: God of Thunder, Hocus Pocus.

### Proprietary container decoding
- Source: S32X-SKILL, references/porting-workflow.md:325-345
- What it does and why it is clever: Implement the exact decompressor in the build tool (`DATA.WAR`: offset table plus a 4 KiB-window LZSS) and quantise everything into one 8-bit palette with index 0 transparent.
- Key numbers: 4 KiB LZSS window.
- Target chapter: NEW: Asset pipelines and data-driven engines
- Evidence: warcraft-32x, breakfree-32x.

### Global palette by median cut, then exact nearest mapping
- Source: S32X-SKILL, references/porting-workflow.md:400-403, 464-471
- What it does and why it is clever: Median-cut per asset group, merge into 256 entries, map every image to its nearest entry with index 0 transparent. Small games fit one palette; big ones need per-scene palettes decided up front.
- Key numbers: 256 entries. One game used about 364 source colours.
- Target chapter: NEW: Asset pipelines and data-driven engines
- Evidence: super-sonic-rpg-32x.

### Compile scripts to bytecode plus a tiny VM instead of porting the interpreter
- Source: S32X-SKILL, references/porting-workflow.md:369-393, 434-439
- What it does and why it is clever: A build-time LCF reader (BER chunk streams) compiles RM2K event pages into compact bytecode `{code, indent, params[], string}` + sentinel. A runtime VM implements only the opcodes the game uses (page conditions, touch/action triggers, parallel pages). Move routes are flattened at build time.
- Key numbers: About 250-line VM, versus a ~30 MB EasyRPG player.
- Target chapter: NEW: Asset pipelines and data-driven engines
- Evidence: super-sonic-rpg-32x, raintown (complete game).

### Autotile to a deduplicated atlas with one-byte passability
- Source: S32X-SKILL, references/porting-workflow.md:440-444
- What it does and why it is clever: Evaluate the RM2K autotile rules (A/B/C/D, 47/50 subtile tables) at build time, deduplicate the resulting 16×16 tiles, and bake passability, wall and above-hero flags into one byte per cell.
- Key numbers: 13,025 cells → 243 tiles (Raintown). 597 tiles (Pail).
- Target chapter: NEW: Asset pipelines and data-driven engines
- Evidence: Shipped RM2K ports.

### Original data tables verbatim plus a level-event interpreter
- Source: S32X-SKILL, references/porting-workflow.md:288-323
- What it does and why it is clever: Ship the original's enemy, weapon and port records unchanged in ROM, so behaviour is read from data. A `switch(type)` VM walks a sorted event stream as the scroll position passes each trigger. Unused opcodes are explicit commented no-ops. `level_pos` and `event_index` double as test telemetry.
- Key numbers: 851 enemy / 781 weapon / 43 port records. 1,009 events over positions 0-8,100. About 559 KB asset bank in 19 sections.
- Target chapter: NEW: Asset pipelines and data-driven engines
- Evidence: tyrian-32x, 7 PicoDrive scenarios to LEVEL COMPLETE.

### Tiled TMX to a sorted ROM event stream
- Source: S32X-SKILL, references/porting-workflow.md:257-265
- What it does and why it is clever: The CSV tile layer becomes the tilemap. Objects become `(trigger_row, column, type, difficulty, gang)` sorted by trigger then group, in a `const LevelEvent[]`.
- Key numbers: 299 mission events (Raptor).
- Target chapter: NEW: Asset pipelines and data-driven engines
- Evidence: raptor32x.

### Content audit before writing the runtime
- Source: S32X-SKILL, references/porting-workflow.md:407-427
- What it does and why it is clever: Parse every map and count commands, opcode coverage by the existing VM, and the hard systems still missing. The result is a bounded backlog and an early answer to whether the game fits.
- Key numbers: 176 maps, 2,159 events, 2,716 pages, 15,580 commands, 45 opcodes, 86.88% already covered.
- Target chapter: NEW: Asset pipelines and data-driven engines
- Evidence: franzen-32x.

### Resolve map-tree inheritance at build time
- Source: S32X-SKILL, references/porting-workflow.md:468-471
- What it does and why it is clever: Music, background, permissions and encounters inherited down the RM2K map tree are flattened into each map so the runtime never walks the tree. Maps go into a banked directory with lazy activation.
- Key numbers: —
- Target chapter: NEW: Asset pipelines and data-driven engines
- Evidence: franzen-32x.

### Ship derived data, not source assets (mocap bake)
- Source: S32X-SKILL, references/porting-workflow.md:216-235
- What it does and why it is clever: Bake mocap into keyframes offline and ship only the keyframes, documenting the bake pipeline. For proprietary data, ship the converter and let the user build the ROM locally.
- Key numbers: —
- Target chapter: NEW: Asset pipelines and data-driven engines
- Evidence: fighting-game-3D-32X, tyrian-32x.

---

## NEW: Automated testing with headless PicoDrive

### Headless libretro harness with a script DSL
- Source: S32X-SKILL, assets/harness.c:1-278; references/testing.md:30-48
- What it does and why it is clever: About 280 lines of C `dlopen` the PicoDrive core and declare only the libretro ABI subset needed. Commands: `run n`, `press b n`, `hold`, `release`, `port`, `shot`. Frames from RGB565, 0RGB1555 or XRGB8888 are converted to dependency-free PPM. Each game state is a small text file.
- Key numbers: Frames up to 512×512.
- Target chapter: NEW: Automated testing with headless PicoDrive
- Evidence: Used by every listed port.

### Lit / colourful / changing assertions
- Source: S32X-SKILL, assets/run_tests.py:36-39, 68-130; references/testing.md:50-79
- What it does and why it is clever: A frame fails if fewer than 8% of pixels are non-black (any channel > 8) or it has fewer than 8 distinct colours after 5-bit quantisation (6 for flat 3D). CRCs must differ across shots. UI checkpoints need distinct signatures, and region crops catch single objects rendered as black silhouettes.
- Key numbers: 0.08 lit ratio, 8 colours (6 for 3D), black level 8.
- Target chapter: NEW: Automated testing with headless PicoDrive
- Evidence: Template.

### Bounded-input-effect regression test
- Source: S32X-SKILL, references/testing.md:64-67; assets/scripts/02_menu.txt
- What it does and why it is clever: Pressing Down must change only a small fraction of pixels (the cursor moved), and Up must return the identical earlier frame. This directly catches the 6-button mirroring bug, where Down launches a level.
- Key numbers: 0.0001 < delta < 0.08.
- Target chapter: NEW: Automated testing with headless PicoDrive
- Evidence: Template.

### Telemetry channels: SDRAM beacon, COMM words, MD work RAM
- Source: S32X-SKILL, references/testing.md:305-327, 382-404, 505-512
- What it does and why it is clever: The master publishes `{magic 'ARK3', frame, state, score, x, y}` at a fixed SDRAM address. PicoDrive stores SDRAM byte-swapped on little-endian hosts, so the harness reads `p[off^1]`. Alternatively write COMM0-10 each frame (cash, loadout, signature|state, level_pos, event_index), or have the 68000 mirror a word into MD work RAM. Tests then assert exact end-state, e.g. `event_index == 1009`.
- Key numbers: —
- Target chapter: NEW: Automated testing with headless PicoDrive
- Evidence: arkanoid32x, tyrian-32x, raintown.

### In-ROM verification accelerator
- Source: S32X-SKILL, references/testing.md:359-380
- What it does and why it is clever: Holding an unused button runs N simulation ticks per rendered frame and makes the player invulnerable, so a short scripted hold covers a whole level deterministically.
- Key numbers: FAST_TICKS = 12. About 1,450 frames for the full level.
- Target chapter: NEW: Automated testing with headless PicoDrive
- Evidence: tyrian-32x.

### Desktop-oracle record/replay determinism
- Source: S32X-SKILL, references/testing.md:240-265
- What it does and why it is clever: The same core source builds for desktop and ROM. Record inputs on the PC (`--record`) and replay them into the ROM with a fixed tick. Any divergence is a portability bug (compiler trap, endianness or `long` width).
- Key numbers: 3 frames per tick.
- Target chapter: NEW: Automated testing with headless PicoDrive
- Evidence: beachy-beachy-ball-32x.

### Oracle against the original's own code
- Source: S32X-SKILL, references/testing.md:453-463
- What it does and why it is clever: Run the shipped JS physics verbatim beside the C port and diff trajectories. Compare frame-exact where the system is stable, and only aggregate behaviour in chaotic stretches (guardrail contact) where sub-LSB differences grow exponentially.
- Key numbers: Max dpos 0.004 units over 220 frames on a 187-unit circuit.
- Target chapter: NEW: Automated testing with headless PicoDrive
- Evidence: racing-circuit-32x.

### Tests must call the shared maths, not re-derive it
- Source: S32X-SKILL, references/testing.md:465-470
- What it does and why it is clever: Two handedness bugs survived because the test recomputed the same wrong rotation. Put the maths in one function (`r_model_to_world()`) that both the renderer and the test call.
- Key numbers: —
- Target chapter: NEW: Automated testing with headless PicoDrive
- Evidence: racing-circuit-32x.

### Heavy host testing of the HAL-free core
- Source: S32X-SKILL, references/testing.md:329-346; references/porting-workflow.md:25-50
- What it does and why it is clever: Every feature is a pure C module with a host test before it is wired into `main`. A scripted perfect player must clear level 1. A swept-collision test asserts a full-speed ball cannot tunnel through a brick in one tick. Fast paths are tested against reference code within 1 px.
- Key numbers: About 22,000 assertions (arkanoid32x).
- Target chapter: NEW: Automated testing with headless PicoDrive
- Evidence: arkanoid32x.

### Corner-screenshot geometry gate
- Source: S32X-SKILL, references/testing.md:348-357
- What it does and why it is clever: `make shots` renders the widest paddle in all four corners and fails the build if a projection retune pushes it off-screen.
- Key numbers: —
- Target chapter: NEW: Automated testing with headless PicoDrive
- Evidence: arkanoid32x.

### Verifying audio from captured PCM
- Source: S32X-SKILL, references/testing.md:159-178, 71-75
- What it does and why it is clever: Capture PicoDrive's audio callback and compare a normalised Goertzel bank (or FFT bands) against a libopenmpt render, with alignment tolerance and a loudness check. A known SFX is located by sparse normalised cross-correlation so FM music isn't mistaken for it. Only claim "audio confirmed" when such a test has actually run.
- Key numbers: —
- Target chapter: NEW: Automated testing with headless PicoDrive
- Evidence: tracker-player-32x.

### Symmetry check for the doubled-image fault
- Source: S32X-SKILL, references/testing.md:449-451
- What it does and why it is clever: Assert the left and right halves are not identical, which detects the direct-colour or COMM-collision doubled image.
- Key numbers: —
- Target chapter: NEW: Automated testing with headless PicoDrive
- Evidence: racing-circuit-32x.

### Black-screen debugging ladder
- Source: S32X-SKILL, references/testing.md:267-303
- What it does and why it is clever: Cheapest step first: print the top colours of the real frame; check the palette-0 tell; cycle the clear colour by `frame & 3` to tell a hang from a palette fault; reduce to a minimal boot; draw unconditionally to split render from logic; `cmp -l` the ROMs; check vectors in the raw ROM; rebuild from a known-good tree.
- Key numbers: 7 rungs.
- Target chapter: NEW: Automated testing with headless PicoDrive
- Evidence: Zepton multi-hour black screen.

### Heartbeat square plus interpreter-state overlay
- Source: S32X-SKILL, references/testing.md:476-493
- What it does and why it is clever: A per-frame toggling square: frozen means the CPU crashed, animating means a logic deadlock. An overlay shows the current opcode, event and flags (e.g. "parked on 0x6C waiting on switch 12").
- Key numbers: —
- Target chapter: NEW: Automated testing with headless PicoDrive
- Evidence: raintown-slickers-32x.

### Debug warps
- Source: S32X-SKILL, references/testing.md:495-503
- What it does and why it is clever: Title-screen combos jump to late maps or a test battle, so scripts reach deep content in a few frames.
- Key numbers: —
- Target chapter: NEW: Automated testing with headless PicoDrive
- Evidence: raintown.

### Harness input gotchas
- Source: S32X-SKILL, references/testing.md:118-130, 230-238
- What it does and why it is clever: Through PicoDrive libretro, script `a` → Genesis C, `b` → B, `c` → A, so accept A|B|C for actions. Presses on frame 0 are ignored; `run 20-30` first. Held buttons stack.
- Key numbers: 20-30 frames of boot.
- Target chapter: NEW: Automated testing with headless PicoDrive
- Evidence: Empirical.

### Pixel-detection pitfalls
- Source: S32X-SKILL, references/testing.md:132-150, 221-228
- What it does and why it is clever: Detect objects by a unique palette colour with a tight threshold; bullet yellow `#fff03c` was matched by sand `#d2be78`. Look where the projection puts objects, not where you expect them. `u8` positions wrap at 256.
- Key numbers: —
- Target chapter: NEW: Automated testing with headless PicoDrive
- Evidence: zepton32x.

### Verified-build report
- Source: S32X-SKILL, references/porting-workflow.md:267-277
- What it does and why it is clever: `BUILD_REPORT.md` records ROM size, SHA-256, header checksum, `.text`/`.bss` sizes against the stack guard, toolchain revision, and a table of PicoDrive scenarios with video and PCM metrics.
- Key numbers: —
- Target chapter: NEW: Automated testing with headless PicoDrive
- Evidence: raptor32x, tyrian-32x.

---

That is about 140 entries across 20 chapters. Three of them contain my own additions where the skill gives no maths, each labelled in its entry: the backface-culling formula, the Mode-7 depth formula and the IMA-ADPCM decoder details. Also labelled are my arithmetic for PWM cycles (≈2087 at 11,025 Hz, 1045 at 22 kHz) and the brad-to-scanline check.