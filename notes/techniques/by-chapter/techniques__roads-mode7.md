# Harvested techniques: Pseudo-3D roads and Mode 7

Target: Part VI chapter in `src/techniques/` (or `src/howto/emulator-testing.md`). 7 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from S32X-SKILL -->
### Per-scanline depth table for a Mode-7 floor
- Source: S32X-SKILL, references/software-3d.md:115-124; references/optimization.md:213-214; references/pico8-porting.md:65-67
- What it does and why it is clever: Precompute `z_fov_table[row]`, the ground distance for each screen row below the horizon, once at init. The floor loop reads it instead of dividing. Then step fixed-point (u,v) across the row and fetch tile pixels with shifts and lookups. The skill names the table but gives no formula. The standard form (my addition): `z(y) = cam_h·focal/(y − y_hor)`, with per-pixel world step `z/focal` along the rotated right vector.
- Key numbers: `z_fov_table[128]` (or [SCREEN_H]). The inner loop is "a few shifts + two lookups".
- Target chapter: NEW: Pseudo-3D roads and Mode 7
- Evidence: Shipped in apex-vector-60-32x.

<!-- from S32X-SKILL -->
### Tile lookup by shifts plus a sprite-offset table
- Source: S32X-SKILL, references/pico8-porting.md:68-70; references/optimization.md:215-217
- What it does and why it is clever: Build `sprid_to_gfx_offset[256]` at startup (sprite id → byte offset in the 128×128 sheet). Replace `/` and `%` in tile and pixel addressing with `>>16`, `>>13`, `&127`, so the inner loop is a couple of shifts and two array reads.
- Key numbers: 256 entries. Sheet 128×128.
- Target chapter: NEW: Pseudo-3D roads and Mode 7
- Evidence: apex-vector-60-32x.

<!-- from S32X-SKILL -->
### Segmented OutRun-style road
- Source: S32X-SKILL, references/software-3d.md:121-124; references/examples.md:14-17
- What it does and why it is clever: The road is a list of segments with forks and per-stage themes, and objects are scaled sprites. Usually much cheaper than polygons for ground racers.
- Key numbers: —
- Target chapter: NEW: Pseudo-3D roads and Mode 7
- Evidence: cannonball-outrun-32x and skyroads-32x (1:1 reverse-engineered). Described only.

<!-- from S32X-SKILL -->
### Only fill what the road does not cover
- Source: S32X-SKILL, references/optimization.md:348-350
- What it does and why it is clever: The road rasteriser records its left/right extent per scanline, and grass is filled only beside it instead of under it.
- Key numbers: Overdraw 1.36× → 1.05×. About 21 K pixel writes per frame saved.
- Target chapter: NEW: Pseudo-3D roads and Mode 7
- Evidence: Measured (racer log).

<!-- from S32X-SKILL -->
### Pre-baked view-angle sprites
- Source: S32X-SKILL, references/software-3d.md:213-221
- What it does and why it is clever: Render each 3D model offline at N view angles, pick the nearest angle at runtime, and scale by depth with an offline row/scale table. The "3D" costs one scaled blit.
- Key numbers: 46 OBJ models → 8 angles × 48×48 (wave-rider-gp). 64 angles for Death Dash Crash cars.
- Target chapter: NEW: Pseudo-3D roads and Mode 7
- Evidence: Shipped in wave-rider-gp-32x and dmar.

<!-- from S32X-SKILL -->
### Sprite stacking
- Source: S32X-SKILL, references/software-3d.md:222-224
- What it does and why it is clever: Draw a stack of 2D slices with a small vertical offset and a shared rotation per slice. The result looks like a voxel object made from top-down art, with no 3D maths.
- Key numbers: —
- Target chapter: NEW: Pseudo-3D roads and Mode 7
- Evidence: Shipped in the dmar collection racers.

<!-- from S32X-SKILL -->
### Fixed-point scaled sprite stepping
- Source: S32X-SKILL, references/pico8-porting.md:71-73; references/optimization.md:218-219
- What it does and why it is clever: Replace the per-pixel divide in the scaled blitter with 16.16 `step_x = (srcW<<16)/dstW` computed once, then accumulate and read `src>>16`.
- Key numbers: More than 10× faster on billboard and car scaling.
- Target chapter: NEW: Pseudo-3D roads and Mode 7
- Evidence: apex-vector-60-32x, measured.

---

