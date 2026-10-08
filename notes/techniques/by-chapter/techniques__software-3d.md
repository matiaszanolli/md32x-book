# Harvested techniques: Software 3D on the SH-2

Target: Part VI chapter in `src/techniques/` (or `src/howto/emulator-testing.md`). 36 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from S32X-SKILL -->
### Per-object transform pipeline
- Source: S32X-SKILL, references/software-3d.md:26-37; assets/3d/r3d.c:42-51, 75-91
- What it does and why it is clever: For each vertex: yaw-rotate in model space and translate (`w.x = x·cos − z·sin + at.x`, `w.z = x·sin + z·cos + at.z`), subtract the camera position, rotate by −camera yaw (`o.x = dx·c − dz·s`, `o.z = dx·s + dz·c`), then project. Only rotation about Y is needed, so it costs 4 fmuls per stage and no matrices.
- Key numbers: Yaw 0..255. Up to 256 verts and 512 tris per mesh (static buffers).
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: Shipped in a rally racer and a rail shooter.

<!-- from S32X-SKILL -->
### Projection with near-plane rejection
- Source: S32X-SKILL, references/software-3d.md:31-33; assets/3d/r3d.c:53-66
- What it does and why it is clever: `sx = W/2 + x·f/z`, `sy = H/2 − y·f/z` (Y up). Points with z < 0.25 are rejected before the reciprocal lookup. A triangle is dropped if any vertex fails, so no clipping code is needed (the cost is triangles popping at the near plane).
- Key numbers: focal ≈ 140-160 px. Near plane z = 0.25 (FX(1)/4). Key clamped to RECIP_N − 1.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: Shipped engine.

<!-- from S32X-SKILL -->
### Flat-shaded scanline triangle rasteriser writing to a HAL-free buffer
- Source: S32X-SKILL, assets/3d/r3d.c:10-39; references/software-3d.md:49-56
- What it does and why it is clever: Sort the three vertices by y. For each row, interpolate x on the long edge (v0→v2) and on the short edge (v0→v1 above y1, v1→v2 below), swap if needed, clip, and memset the span with one palette byte. It writes into a caller-supplied `{u8 *px; int w,h;}`, so the same code runs in a host test (fill into a malloc'd buffer, assert area and an interior pixel) and on the 32X back buffer. Caveat: as written it does a `long long` divide per edge per row (see problems 2 and 3).
- Key numbers: 8bpp, one byte per pixel.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: Host-tested and shipped.

<!-- from S32X-SKILL -->
### Painter's sort by summed vertex depth (no z-buffer)
- Source: S32X-SKILL, assets/3d/r3d.c:93-108; references/software-3d.md:35-37
- What it does and why it is clever: Each face's key is `z_a + z_b + z_c`; skipping the divide by 3 keeps the same order. Faces are insertion-sorted descending (far first) and drawn in that order. With no z-buffer there is no 2-bytes-per-pixel RAM cost and no per-pixel compare, which matters with 256 KiB of SDRAM. Fine for convex-ish meshes and separated objects. Note the aliasing bug (problem 1).
- Key numbers: O(n²) insertion sort; fine for small n.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: Shipped engine; contains the facez bug described above.

<!-- from S32X-SKILL -->
### Backface culling (described, not in r3d)
- Source: S32X-SKILL, references/software-3d.md:146-148; references/examples.md:113-116
- What it does and why it is clever: The fighters use painter sort plus backface culling with no z-buffer. Culling removes about half the faces of a closed mesh before sorting and filling, and it hides the painter errors that inward-facing faces cause. The skill gives no formula. The standard one (my addition): cull if the screen-space signed area `(x1−x0)(y2−y0) − (x2−x0)(y1−y0)` has the wrong sign for your winding.
- Key numbers: About 50% fewer faces on closed meshes.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: Shipped in hit8ox-32x and fighting-game-3D-32X (described only).

<!-- from S32X-SKILL -->
### Cull before sorting; frustum cull, LOD, and drop buried faces at build
- Source: S32X-SKILL, references/optimization.md:351-353
- What it does and why it is clever: Culling before the O(n²) insertion sort roughly halves n, so sort cost drops about 4×. Distant meshes switch LOD: a far car becomes 13 triangles, then a single box. The build tool deletes coincident quads sealed inside abutting boxes, so no runtime work is spent on faces that can never be seen.
- Key numbers: Far car = 13 tris → 1 box.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: Measured in the 12→30 fps racer log.

<!-- from S32X-SKILL -->
### Hoist the camera basis once per frame
- Source: S32X-SKILL, references/optimization.md:354-355
- What it does and why it is clever: Look up sin/cos of camera yaw and pitch once per frame and pass them in, instead of once per vertex. Note that r3d's `to_camera` re-reads them per vertex.
- Key numbers: About 600 table lookups per frame removed.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: Measured (racer log).

<!-- from S32X-SKILL -->
### Interpolated reciprocal-depth projection and shell sort
- Source: S32X-SKILL, references/optimization.md:296-299
- What it does and why it is clever: Compute one reciprocal per depth step and interpolate between steps, which generalises divide hoisting to continuous depth. Sort few objects far-to-near with a shell sort.
- Key numbers: —
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: wave-rider-gp audit checklist (described).

<!-- from S32X-SKILL -->
### Scanline shared-edge road strips
- Source: S32X-SKILL, references/optimization.md:345-347
- What it does and why it is clever: A road strip's long edges are shared between segments. Walking the strip by scanline as one shape needs about 6 divides, versus about 30 edge-slope divides plus vertex sorts when each segment is split into 10 triangles.
- Key numbers: About 30 → about 6 divides per segment.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: Measured (racer log).

<!-- from S32X-SKILL -->
### Low-poly ROM mesh format with distinct palette colours
- Source: S32X-SKILL, references/software-3d.md:58-69; assets/3d/r3d.h:12-19
- What it does and why it is clever: A `const` mesh `{verts, nverts, tris{a,b,c,color}, ntris}` lives in ROM and costs no SDRAM. Each object gets its own palette index, which makes it readable on screen and makes pixel-based emulator tests unambiguous.
- Key numbers: Car ≈ 16 verts / 20 tris. Enemy ≈ 6 verts / 8 tris.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: Shipped.

<!-- from S32X-SKILL -->
### Chase camera
- Source: S32X-SKILL, references/software-3d.md:73-74
- What it does and why it is clever: `cam.pos = obj.pos − heading·dist`, `cam.yaw = obj.yaw`. Two lines give a third-person racer camera.
- Key numbers: —
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: Shipped racer.

<!-- from S32X-SKILL -->
### Track or rail ribbon from a segment list
- Source: S32X-SKILL, references/software-3d.md:78-80
- What it does and why it is clever: Expand `{curve, slope, len}` segments into centreline nodes `{x,y,z,yaw}`. Edge points are centre ± perpendicular·half_width, and each segment is drawn as two triangles. A compact, authorable track format.
- Key numbers: 2 tris per segment.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: Shipped racer and rail shooter.

<!-- from S32X-SKILL -->
### Scrolling ground detail to show speed
- Source: S32X-SKILL, references/software-3d.md:75-77
- What it does and why it is clever: A flat single-colour ground shows no motion. Transverse lines or road dashes whose world-z scrolls with distance travelled give a cheap sense of speed.
- Key numbers: —
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: Shipped.

<!-- from S32X-SKILL -->
### Fixed-camera tunnel projection
- Source: S32X-SKILL, references/software-3d.md:155-177
- What it does and why it is clever: When the camera never rotates and looks down +z, use `r = 1/(z + CAM_BACK)` once per depth slice, then `sx = cx + x·r·FOCAL`, `sy = cy − y·r·FOCAL`. No matrices. Clamp `z + CAM_BACK` away from 0. Tune FOCAL, CAM_BACK and the world z extents together so the near plane matches the 320×224 viewport; this is a correctness constraint enforced by a corner-screenshot test.
- Key numbers: One reciprocal per depth.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: arkanoid32x, with a host `make shots` corner gate.

<!-- from S32X-SKILL -->
### Rasterise static geometry once
- Source: S32X-SKILL, references/optimization.md:247-250; references/software-3d.md:169-170
- What it does and why it is clever: With a fixed camera the corridor is identical every frame. Rasterise it once at boot into an offscreen buffer and copy it each frame. Half the frame time had been spent redrawing unchanging geometry.
- Key numbers: 14.6 → 29 fps.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: arkanoid32x, measured.

<!-- from S32X-SKILL -->
### Handedness and axis-sign gotcha when porting
- Source: S32X-SKILL, references/software-3d.md:91-102
- What it does and why it is clever: Symptoms: mirrored steering, scenery receding as you drive forward, objects facing away. Fix with a sign flip when rebuilding the heading, e.g. `atan2(dx, −dy)` instead of `(dx, dy)`. Test: approaching objects must grow; if they shrink, your forward axis is flipped.
- Key numbers: —
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: speed-haste-32x applies exactly this fix.

<!-- from S32X-SKILL -->
### Wireframe / vector rendering
- Source: S32X-SKILL, references/software-3d.md:109-113
- What it does and why it is clever: Project vertices as usual and draw edges with Bresenham lines. No rasteriser and no depth sort. A whole game can run on `plot()` + `gfx_line()` into the 8bpp framebuffer.
- Key numbers: —
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: Shipped in wirefight-32x, xquest-32x and tempest-2k-32x (16 webs).

<!-- from S32X-SKILL -->
### Skeletal / keyframe character animation
- Source: S32X-SKILL, references/software-3d.md:129-153; references/pico8-porting.md:22-27
- What it does and why it is clever: A fighter is an 18-point skeleton with 13 tapered prism segments (each with dimensions, roll, cap flags). Authored key poses are interpolated by move and phase, with explicit windup / active / recovery phases. Per-segment light/dark CRAM pairs give colour customisation for free. Mocap can seed the poses offline; ship only the baked keyframes.
- Key numbers: 18 points, 13 segments, 117 keyframes (converted from the cart).
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: Shipped in hit8ox-32x and fighting-game-3D-32X.

---

<!-- from D32XR -->
### Sprite projection, rotation pick and culling
- Source: D32XR, r_phase3.c:17-192 (licence: id limited-use)
- What it does and why it is clever:
  - **View space.** Translate into view space with 4 FixedMuls.
  - **Culling.** Reject depth below MINZ (4 units). Reject |tx| > 4·tz before any per-frame lookup. Cull vertically with `gzt·xscale` against centerY.
  - **Scale.** `xscale = centerX/tz`; yscale = xscale·stretch for aspect.
  - **Rotation.** `rot = (angle_to_thing - thing_angle + 9·ANG45/2) >> 29` picks one of 8 views.
  - **Flags in the lump number.** Flip and single-sided status ride in its top bits, so there is no separate frame table.
- Key numbers: SL_SINGLESIDED 0x8000, SL_FLIPPED 0x4000.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: code only

<!-- from D32XR -->
### Sprite sort key and insertion sort
- Source: D32XR, r_phase8.c:533-590, d_main.c:169-183 (licence: id limited-use)
- What it does and why it is clever: Each sprite gets the int key `(xscale<<7) + index`, depth in the high bits and slot in the low 7. A plain insertion sort on these ints orders sprites back to front; the low bits recover the sprite with `& 0x7F`. The same D_isort sorts visplanes. Insertion sort suits the small and often nearly sorted lists.
- Key numbers: 7-bit index field (128 sprites) with MAXVISSPRITES 165, so a mismatch is possible.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: code only

<!-- from D32XR -->
### Clipping sprites against wall silhouettes and interleaving masked walls
- Source: D32XR, r_phase8.c:257-395, 21-143, 397-465 (licence: id limited-use)
- What it does and why it is clever:
  - **Clip list.** Each CPU builds the list of walls that cast silhouettes or have masked mid-textures. For each sprite it walks them; a wall is behind the sprite if both end scales are smaller, or if a cross-product side test says so.
  - **Walls behind.** Their masked mid-texture columns are drawn there and then, and each column is marked OPENMARK so it is drawn once.
  - **Walls in front.** They narrow the sprite's top and bottom openings: byte-wise for top-only or bottom-only silhouettes, both bytes for both, the whole column for solid.
  - **Masked mid-textures.** Phase 6 stored `light|colnum` per column for them.
- Key numbers: silhouette = actionbits / AC_TOPSIL (1, 2, 3 or ≥4 = solid).
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: code only

<!-- from D32XR -->
### Drawing masked patch columns
- Source: D32XR, r_phase8.c:145-252 (licence: id limited-use)
- What it does and why it is clever: Sprites are Doom posts (topdelta, length, data offset) per column. Each post's screen top is rounded up with `+0xFFFF` (built in two instructions) and clipped to the opening; frac starts at `(clip - top)·iscale`. Columns are stepped by `xiscale`, negative when flipped. Shadow sprites switch to the fuzz drawer through a negative colormap value.
- Key numbers: posts end at 0xFF.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: code only

<!-- from D32XR -->
### Viewport aspect stretch and weapon placement
- Source: D32XR, r_main.c:232-305, r_phase3.c:197-292 (licence: id limited-use)
- What it does and why it is clever: `stretch = (16·h/180·22)/w` in 16.16 (28 instead of 22 for anamorphic). It scales wall heights through `stretchX = stretch·centerX` and sprites through yscale, so any viewport keeps Doom's 2.2 pixel aspect. Weapon sprites use a fixed x scale (halved in low-res) and a vertical offset chosen per viewport height.
- Key numbers: 4 viewport presets x 2 (single or split screen).
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: code only

---

<!-- from VRD/AU/MARSDEV -->
### 16.16 matrix×vector transform with MAC.L + XTRCT
- Source: VRD-NOTES, /mnt/data/src/32x-playground/analysis/POLYGON_TRANSFORMATION_ANALYSIS.md:192-223; analysis/sh2-analysis/SH2_3D_ENGINE_DATA_STRUCTURES.md:308-330
- What it does and why it is clever: Each output component is three back-to-back `MAC.L @R4+,@R5+` operations (matrix row × vector) into the 64-bit MACH:MACL accumulator. `XTRCT MACH,MACL` then takes bits [47:16], which turns a (16.16)×(16.16)=(32.32) product into a 16.16 result with no shifts. The translation term is then added. The 4×4 matrix (64 B = four cache lines) is walked by post-increment, so there is no index arithmetic.
- Key numbers: MAC.L 2-3 cycles; about 11-14 cycles per component, about 33-45 cycles per vertex; about 500 vertices per frame, about 17,500 cycles (4.6% of a 383,000-cycle frame; estimate). Range ±32768.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: code only (cycle figures are static estimates)

<!-- from VRD/AU/MARSDEV -->
### Reciprocal-table edge slopes (span_filler)
- Source: VRD-NOTES, analysis/sh2-analysis/SH2_3D_ENGINE_DEEP_DIVE.md:143-182, 302-312
- What it does and why it is clever: Edge slopes avoid division. `slope = ΔX × recip[ΔY]` uses `MULS.W` and a 256-entry table holding `floor(16384/N)` (0.14 fixed point; entry 0 is a `$7FFF` sentinel), followed by `SHLL2` to rescale. Small ΔY takes a direct-multiply path instead. Vertices are packed Y:X in one register and unpacked with `SWAP.W`/`EXTS.W`. The routine's first instruction doubles as `render_quad`'s RTS delay slot.
- Key numbers: table at ROM $0248D0 → SDRAM $060048D0, 512 B; span_filler about 8% of Slave time.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: code only (table contents verified against ROM; percentage from historical PicoDrive profile)

<!-- from VRD/AU/MARSDEV -->
### Edge-walking quad rasterizer with two orientation paths
- Source: VRD-NOTES, analysis/sh2-analysis/SH2_3D_ENGINE_DEEP_DIVE.md:119-141
- What it does and why it is clever: `render_quad_short` (98 B) uses `MAC.W @R8+,@R9+` for hardware edge interpolation. It has separate left-edge-first and right-edge-first paths so the inner loop never tests orientation. Each path calls the span filler twice, filling R9/R13 edge buffers. Only position is interpolated.
- Key numbers: 98 B; rasterization about 52% of Slave time.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: code only

<!-- from VRD/AU/MARSDEV -->
### Frustum hub with bounding-box classification and four render paths
- Source: VRD-NOTES, analysis/sh2-analysis/SH2_3D_ENGINE_DEEP_DIVE.md:66-117; analysis/VR60_PHASE5F1_BRIDGE_SPEC.md:166-176
- What it does and why it is clever: The pipeline per polygon is:
  - load four vertices;
  - project them (`screen_coords`);
  - track the X min/max;
  - assign Y bounds and clip flags (0 inside, 4 edge A, 8 edge B, 12 both);
  - pick one of four paths with `CMP/GT` tests: culled, basic scanline, edge-walking quad, or display-list processor.

  `TST #8` decides whether flat or clipped handling applies, so most polygons skip clipping maths entirely. The per-entity transform also compares against `$0064`/`$00C8` cull thresholds.
- Key numbers: 238 B, the largest standalone function; about 12% of Slave time.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: code only

<!-- from VRD/AU/MARSDEV -->
### Flat shading by palette-byte replication plus pre-baked strip tables
- Source: VRD-NOTES, analysis/sh2-analysis/SH2_3D_ENGINE_DEEP_DIVE.md:184-224
- What it does and why it is clever: There is no Gouraud shading, no texture and no Z-buffer. The 8-bit palette index is replicated into a word (`AND $FF00`, `SWAP.B`, `OR`), so spans fill two pixels per `MOV.W` (or via VDP fill). Instead of per-pixel shading, `raster_batch` copies two precomputed 112-byte strips: A is gradient ramps over palette 32-253, B is dither/edge patterns. 112 B = 14×8 exactly matches the unrolled copy size.
- Key numbers: strips at $06003E3C and $060086D4, 112 B each.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: code only

<!-- from VRD/AU/MARSDEV -->
### Painter's algorithm: 68K depth sort, insertion sort exploiting frame coherence
- Source: VRD-NOTES, /mnt/data/src/32x-playground/disasm/modules/68k/game/render/depth_sort.asm:1-60; analysis/RENDERING_PIPELINE.md:116-123; OPTIMIZATION_PLAN.md:485
- What it does and why it is clever: The 68K sorts 16 entries of {key word, object pointer} back-to-front, and the SH-2 simply draws in that order. The original was a selection sort with a camera-quadrant tie-break. The rework uses insertion sort, which is near-linear because car depths barely change between frames. It is also stable, so equal keys keep last frame's order.
- Key numbers: typical cost 15 fast-path compares plus 2-4 shifts, versus 2-3 full 15-compare passes; M-002 measured an 85% reduction.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: emulator measured (PicoDrive)

<!-- from VRD/AU/MARSDEV -->
### Render descriptors and state records (the 68K→SH-2 "command format")
- Source: VRD-NOTES, analysis/sh2-analysis/SH2_RENDERING_ARCHITECTURE.md:37-61, 127-141; analysis/VR60_PHASE5F1_BRIDGE_SPEC.md:20-44, 140-200; VR60_STATUS.md:154-160
- What it does and why it is clever:
  - **On the 68K:** it writes 60-byte (`$3C`) display-object records. Each holds a visibility flag, world X/Y words, camera-adjusted angle, lateral/height/depth `>>3` and negated, a sprite-definition pointer at +$10, rotation at +$1C, and angular data at +$30. These records sit in a 2,560-byte block that is sent by DREQ every game frame.
  - **On the SH-2:** the engine reads only a 20-byte window at the head of each record, transforms it, and writes 48-byte render-state records.
  - **Batches:** 4 + 8 + 3×8 = 36 entity passes per frame. In racing the renderer consumes the descriptor families at SDRAM $0600C128 / $0600C178 / $0600C254.
- Key numbers: 20 B descriptor stride; 48 B state stride; 60 B record stride; up to 36 passes per frame.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: code only. The earlier "$0600C218 is the racing descriptor" finding is invalidated: VR60_STATUS says the renderer consumes C128/C178/C254.

<!-- from VRD/AU/MARSDEV -->
### Display-list encoding with computed dispatch
- Source: VRD-NOTES, analysis/sh2-analysis/SH2_3D_ENGINE_DEEP_DIVE.md:174-182, 241-254; SH2_RENDERING_ARCHITECTURE.md:77-80
- What it does and why it is clever: Display-list entries are 20 B for quads and 16 B for triangles: a flag word, a header word, then 3-4 vertex longwords. `main_coordinator` reads the polygon type, masks it to an even index 0-14 and dispatches with `BSRF`, a PC-relative computed branch with no jump table in memory. Index `$0C` terminates the list. `render_dispatch` lists are `0xFF`-terminated and track visibility across adjacent entries.
- Key numbers: 20/16-byte entries; 8 dispatch slots.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: code only

<!-- from VRD/AU/MARSDEV -->
### Recursive quad subdivision
- Source: VRD-NOTES, analysis/POLYGON_TRANSFORMATION_ANALYSIS.md:292-303; analysis/sh2-analysis/SH2_RENDERING_ARCHITECTURE.md:87-92
- What it does and why it is clever: `recursive_quad` (`vertex_helper`, 86 B) calls itself and then the frustum hub for each of a quad's four vertices. This suggests large polygons are split before culling and clipping. The purpose is inferred, not proven.
- Key numbers: 86 B.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: code only

<!-- from VRD/AU/MARSDEV -->
### Huffman-coded scene data with XOR/delta store mode
- Source: VRD-NOTES, analysis/sh2-analysis/SH2_COMMAND_HANDLER_REFERENCE.md:178-202
- What it does and why it is clever: The decoder first builds a 256-entry fast-lookup table (at $06003000) and decodes 8 bits per lookup. It packs eight 4-bit symbols per output longword. Header bit 31 selects straight store or XOR-with-previous, a cheap delta coding for similar consecutive records.
- Key numbers: decoder about 500 B; output up to 512 longwords (2 KB) at $0600C000.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: code only. The OPTIMIZATION_PLAN S-1 claim that "racing uses this Huffman renderer" sits in a section whose architecture statements were later contradicted, so treat it as unconfirmed.

<!-- from VRD/AU/MARSDEV -->
### Unrolled stride copy that falls through (space-optimized hot loop)
- Source: VRD-NOTES, analysis/POLYGON_TRANSFORMATION_ANALYSIS.md:327-366; OPTIMIZATION_PLAN.md:551
- What it does and why it is clever: `unrolled_data_copy` computes `table + index×128` with `SHLL8`/`SHLR`, then runs 14 unrolled pairs of `MOV.L` copies with a stride add. It has no RTS and falls through into the next routine. Every modification attempt crashed.
- Key numbers: 150 B; 56 B per call (the doc's "28 longwords" is inconsistent with 56 B); destination is SDRAM, not the framebuffer, so a FIFO-burst rewrite cannot help (B-009).
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: code only. The FIFO-batching idea for it is invalidated (B-009: it writes SDRAM).

---


---

<!-- from SWA -->
### Depth buckets and a two-CPU polygon pipeline (Star Wars Arcade)
- Source: SWA, SH-2 code at `0x06002570` (frame geometry), `0x06002A5A`/`0x06002AB8`/`0x06002B1C`/`0x060028B8` (transforms), `0x06002796` (bucket walk), `0x060008AC` (Slave draw loop), `0x060007D0` (Slave frame command)
- What it does: The Master transforms with `clrmac` + three `mac.l @rA+,@rB+` + `sts mach`/`sts macl` + `xtrct` (a 16.16 matrix row in four instructions plus the fetch). Polygon records go into one of two buffers (`0x06018690`/`0x06024BB8`). Each record is linked into an 8,192-entry bucket table at `0x060076C0` (node: +0 next, +4 record); the walk at `0x06002796` empties every bucket while copying record pointers into one of two flat lists (`0x060310E0`/`0x060326C8`, counts at `0x0600764C`/`0x0600764E`), giving draw order with no comparison sort. The Slave purges its cache, auto-fills, calls its 2 KB on-chip routine at `0xC0000000` once per list pointer, flips FS.
- Key numbers: 8,192 buckets (32 KB of heads); node pool reset to `0x0600F6C0` each frame; Master waits for the Slave with a 1,100-pass delay between polls of `$A15123`.
- Target chapter: techniques/software-3d (bucket sort, MAC.L transform); patterns/cpu-split already uses the pipeline.
- Evidence: ROM

<!-- from AB32X -->
### 256-bucket depth sort with spill; triple-buffered object rings (After Burner Complete)
- Source: AB32X, SH-2 code at `0x06003B66`
- What it does and why it is clever: Buckets are 32 bytes: a count and up to 30 one-byte entry numbers. A full bucket spills into the next. Three object rings of 194 entries rotate between the 68000's calls and the Master's drawing.
- Target chapter: techniques/software-3d
- Evidence: ROM

---

## Check of the VRD entries (2026-10-03, against the project's patched ROM copy, SH-2 code from ROM `$20000` at `0x06000000`)

Most VRD entries above come from the project's analysis documents and do not survive a reading of the code. Do not cite them.

- **Transform:** real (`0x06003120`-`0x06003176`), but the matrix is 3×4 (48 bytes, copied to `0xC0000740`), and the perspective divide runs on DIVU (64/32) in parallel with the remaining `MAC.L` rows; the quotient is read from `0xFFFFFF1C` (undocumented copy, see `src/sh2/divu.md`).
- **Reciprocal table** at ROM `$0248D0` is two-sided: `t[N] = floor(16384/N)` and `t[-N] = -floor(16384/N)` for N = 1..255, `t[0] = $7FFF`. `0x0600375E` is a Y-clip intersection (table for |dY| ≤ 255, DIVU above), not the span filler. Vertices packed X high, Y low.
- **render_quad_short** (`0x060036FA`) has no `MAC.W` (`$018E` is `MOV.L @(R0,R8),R1`); it builds one Y-clipped edge chain. The "frustum hub" (`0x06003508`) returns top/bottom vertex slots 0/4/8/12, not clip flags; `TST #8` waits for a free ring slot.
- **Gradient strips:** wrong. `$06003E3C` is a pointer table; `$060086D4` is glyph data; "raster_batch" and `unrolled_data_copy` (`0x06003F2E`, returns normally, 112 bytes per call) draw HUD characters.
- **68000 depth sort:** wrong. `depth_sort` (`$009DE2`) ranks cars by lap and segment. "85%" (M-002) has no method; commit `b0719b9` reports 62% against an earlier rework. The painter's sort is on the Master: bubble sort of scenery pieces (`0x0600115C`) and a bucket walk (`0x06003456`/`0x06003468`, not recursion).
- **Huffman decoder:** Master command `$23`; runs of nibbles, mode bit 15 of the first header word; no evidence it runs in racing.
- **Which CPU renders:** the documents say the Slave; the code reads as a Master producer (edge lists into a 16 KB ring, `0x060032D4`) and a Slave consumer (`0x060039F0`, 580-byte on-chip rasteriser with auto-fill spans at `0xC0000188` and a checkerboard path writing the overwrite image at `0xC00001F4`), like Star Wars Arcade. Needs a clean retail ROM before the book attributes it to Sega.
- The book uses none of this as fact; `src/techniques/software-3d.md` raises the renderer split as an open question.
