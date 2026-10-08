# Harvested techniques: Voxel landscapes

Target: Part VI chapter in `src/techniques/` (or `src/howto/emulator-testing.md`). 5 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from S32X-SKILL -->
### Procedural, step-quantised heightmap world
- Source: S32X-SKILL, references/voxel-landscape.md:14-31
- What it does and why it is clever: An NX × NZ grid. Height is a sum of a few `r3d_sin/cos` waves plus features (river valley, plateau, volcano), quantised with `h = (h/QSTEP)·QSTEP` for the blocky look. Colour comes from height bands (water/sand/grass/rock/snow). Forward motion advances a 16.16 `scroll`: `worldz = slice + (scroll>>16)`, and the fraction offsets depth smoothly.
- Key numbers: 32 × 28 grid. Scale rule: near cell width `CELL·FOCAL/NEAR ≈ 10 px`, so CELL = 1, FOCAL = 120 gives NEAR ≈ 12. Putting the near plane at z ≈ 1 projects everything off-screen and gives a black frame.
- Target chapter: NEW: Voxel landscapes
- Evidence: zepton32x.

<!-- from S32X-SKILL -->
### Method A: per-cell billboards, painted far to near
- Source: S32X-SKILL, references/voxel-landscape.md:68-94
- What it does and why it is clever: For each slice from far to near: one reciprocal `rf`, `size = (CELL>>8)·rf>>12`, then for each column a rectangle of width `size+1` and height `2·size+2` at `sy = HOR + ((CAMY−h)>>8)·rf>>12`. When size ≥ 2 a 1-px white "lit ridge" is drawn on top. Heights are sampled once per cell, but it needs a full clear and pays for overdraw.
- Key numbers: About 900 samples per frame (32×28). Column height 2× size is the balance point; 3× looks solid but costs too much fill.
- Target chapter: NEW: Voxel landscapes
- Evidence: Shipped default in zepton32x (about 19 fps).

<!-- from S32X-SKILL -->
### Method B: per-screen-column y-buffer raycaster
- Source: S32X-SKILL, references/voxel-landscape.md:96-121
- What it does and why it is clever: For each 2-px screen column, march near to far with `ybuf = SCREEN_H`. Inverse-project the column to world x, sample the height, and when `sy < ybuf` draw a span from `sy` to `ybuf` and set `ybuf = sy`. Every pixel is painted once and only the sky band needs clearing.
- Key numbers: 160 columns × 28 slices ≈ 4480 height samples per frame.
- Target chapter: NEW: Voxel landscapes
- Evidence: Built and measured in zepton32x; not shipped.

<!-- from S32X-SKILL -->
### Compute versus fill-rate measurement (A beat B)
- Source: S32X-SKILL, references/voxel-landscape.md:123-137; references/optimization.md:197-205
- What it does and why it is clever: With trig-heavy height sampling (2 sin + 1 cos per sample), B became compute-bound and lost. The fix the skill proposes but did not ship: compute the frame's heightmap grid once (about 900 samples) and let B read or interpolate from that array, so B becomes fill-bound. Rule: a rewrite you built is not a rewrite you should ship until it measures better.
- Key numbers: B ≈ 8 fps vs A ≈ 19 fps.
- Target chapter: NEW: Voxel landscapes
- Evidence: Measured in PicoDrive with the frame-counter bar.

<!-- from S32X-SKILL -->
### Into-the-screen projectiles and approaching enemies
- Source: S32X-SKILL, references/voxel-landscape.md:139-152
- What it does and why it is clever: Gameplay runs in screen space with a progress value `p` from 0 to 1. Bullets are `lerp(launch, target, p)` with size shrinking as p grows. Homing missiles re-blend the target each frame with `tx += (reticle − tx) >> 3`. Enemies run the reverse: `x = 160 + lane·SPREAD·p`, `y = HOR + (PLAYER_Y − HOR)·p`, `size ∝ p`. No 3D maths is needed, and lock-on/hit is just a screen-space overlap test, all host-testable.
- Key numbers: Homing gain 1/8 per frame.
- Target chapter: NEW: Voxel landscapes
- Evidence: zepton32x (`weapons.c`), host tests.

---

