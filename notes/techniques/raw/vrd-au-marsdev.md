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

## NEW: Software 3D on the SH-2

### 16.16 matrix×vector transform with MAC.L + XTRCT
- Source: VRD-NOTES, /mnt/data/src/32x-playground/analysis/POLYGON_TRANSFORMATION_ANALYSIS.md:192-223; analysis/sh2-analysis/SH2_3D_ENGINE_DATA_STRUCTURES.md:308-330
- What it does and why it is clever: Each output component is three back-to-back `MAC.L @R4+,@R5+` operations (matrix row × vector) into the 64-bit MACH:MACL accumulator. `XTRCT MACH,MACL` then takes bits [47:16], which turns a (16.16)×(16.16)=(32.32) product into a 16.16 result with no shifts. The translation term is then added. The 4×4 matrix (64 B = four cache lines) is walked by post-increment, so there is no index arithmetic.
- Key numbers: MAC.L 2-3 cycles; about 11-14 cycles per component, about 33-45 cycles per vertex; about 500 vertices per frame, about 17,500 cycles (4.6% of a 383,000-cycle frame; estimate). Range ±32768.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: code only (cycle figures are static estimates)

### Reciprocal-table edge slopes (span_filler)
- Source: VRD-NOTES, analysis/sh2-analysis/SH2_3D_ENGINE_DEEP_DIVE.md:143-182, 302-312
- What it does and why it is clever: Edge slopes avoid division. `slope = ΔX × recip[ΔY]` uses `MULS.W` and a 256-entry table holding `floor(16384/N)` (0.14 fixed point; entry 0 is a `$7FFF` sentinel), followed by `SHLL2` to rescale. Small ΔY takes a direct-multiply path instead. Vertices are packed Y:X in one register and unpacked with `SWAP.W`/`EXTS.W`. The routine's first instruction doubles as `render_quad`'s RTS delay slot.
- Key numbers: table at ROM $0248D0 → SDRAM $060048D0, 512 B; span_filler about 8% of Slave time.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: code only (table contents verified against ROM; percentage from historical PicoDrive profile)

### Edge-walking quad rasterizer with two orientation paths
- Source: VRD-NOTES, analysis/sh2-analysis/SH2_3D_ENGINE_DEEP_DIVE.md:119-141
- What it does and why it is clever: `render_quad_short` (98 B) uses `MAC.W @R8+,@R9+` for hardware edge interpolation. It has separate left-edge-first and right-edge-first paths so the inner loop never tests orientation. Each path calls the span filler twice, filling R9/R13 edge buffers. Only position is interpolated.
- Key numbers: 98 B; rasterization about 52% of Slave time.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: code only

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

### Flat shading by palette-byte replication plus pre-baked strip tables
- Source: VRD-NOTES, analysis/sh2-analysis/SH2_3D_ENGINE_DEEP_DIVE.md:184-224
- What it does and why it is clever: There is no Gouraud shading, no texture and no Z-buffer. The 8-bit palette index is replicated into a word (`AND $FF00`, `SWAP.B`, `OR`), so spans fill two pixels per `MOV.W` (or via VDP fill). Instead of per-pixel shading, `raster_batch` copies two precomputed 112-byte strips: A is gradient ramps over palette 32-253, B is dither/edge patterns. 112 B = 14×8 exactly matches the unrolled copy size.
- Key numbers: strips at $06003E3C and $060086D4, 112 B each.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: code only

### Painter's algorithm: 68K depth sort, insertion sort exploiting frame coherence
- Source: VRD-NOTES, /mnt/data/src/32x-playground/disasm/modules/68k/game/render/depth_sort.asm:1-60; analysis/RENDERING_PIPELINE.md:116-123; OPTIMIZATION_PLAN.md:485
- What it does and why it is clever: The 68K sorts 16 entries of {key word, object pointer} back-to-front, and the SH-2 simply draws in that order. The original was a selection sort with a camera-quadrant tie-break. The rework uses insertion sort, which is near-linear because car depths barely change between frames. It is also stable, so equal keys keep last frame's order.
- Key numbers: typical cost 15 fast-path compares plus 2-4 shifts, versus 2-3 full 15-compare passes; M-002 measured an 85% reduction.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: emulator measured (PicoDrive)

### Render descriptors and state records (the 68K→SH-2 "command format")
- Source: VRD-NOTES, analysis/sh2-analysis/SH2_RENDERING_ARCHITECTURE.md:37-61, 127-141; analysis/VR60_PHASE5F1_BRIDGE_SPEC.md:20-44, 140-200; VR60_STATUS.md:154-160
- What it does and why it is clever:
  - **On the 68K:** it writes 60-byte (`$3C`) display-object records. Each holds a visibility flag, world X/Y words, camera-adjusted angle, lateral/height/depth `>>3` and negated, a sprite-definition pointer at +$10, rotation at +$1C, and angular data at +$30. These records sit in a 2,560-byte block that is sent by DREQ every game frame.
  - **On the SH-2:** the engine reads only a 20-byte window at the head of each record, transforms it, and writes 48-byte render-state records.
  - **Batches:** 4 + 8 + 3×8 = 36 entity passes per frame. In racing the renderer consumes the descriptor families at SDRAM $0600C128 / $0600C178 / $0600C254.
- Key numbers: 20 B descriptor stride; 48 B state stride; 60 B record stride; up to 36 passes per frame.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: code only. The earlier "$0600C218 is the racing descriptor" finding is invalidated: VR60_STATUS says the renderer consumes C128/C178/C254.

### Display-list encoding with computed dispatch
- Source: VRD-NOTES, analysis/sh2-analysis/SH2_3D_ENGINE_DEEP_DIVE.md:174-182, 241-254; SH2_RENDERING_ARCHITECTURE.md:77-80
- What it does and why it is clever: Display-list entries are 20 B for quads and 16 B for triangles: a flag word, a header word, then 3-4 vertex longwords. `main_coordinator` reads the polygon type, masks it to an even index 0-14 and dispatches with `BSRF`, a PC-relative computed branch with no jump table in memory. Index `$0C` terminates the list. `render_dispatch` lists are `0xFF`-terminated and track visibility across adjacent entries.
- Key numbers: 20/16-byte entries; 8 dispatch slots.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: code only

### Recursive quad subdivision
- Source: VRD-NOTES, analysis/POLYGON_TRANSFORMATION_ANALYSIS.md:292-303; analysis/sh2-analysis/SH2_RENDERING_ARCHITECTURE.md:87-92
- What it does and why it is clever: `recursive_quad` (`vertex_helper`, 86 B) calls itself and then the frustum hub for each of a quad's four vertices. This suggests large polygons are split before culling and clipping. The purpose is inferred, not proven.
- Key numbers: 86 B.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: code only

### Huffman-coded scene data with XOR/delta store mode
- Source: VRD-NOTES, analysis/sh2-analysis/SH2_COMMAND_HANDLER_REFERENCE.md:178-202
- What it does and why it is clever: The decoder first builds a 256-entry fast-lookup table (at $06003000) and decodes 8 bits per lookup. It packs eight 4-bit symbols per output longword. Header bit 31 selects straight store or XOR-with-previous, a cheap delta coding for similar consecutive records.
- Key numbers: decoder about 500 B; output up to 512 longwords (2 KB) at $0600C000.
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: code only. The OPTIMIZATION_PLAN S-1 claim that "racing uses this Huffman renderer" sits in a section whose architecture statements were later contradicted, so treat it as unconfirmed.

### Unrolled stride copy that falls through (space-optimized hot loop)
- Source: VRD-NOTES, analysis/POLYGON_TRANSFORMATION_ANALYSIS.md:327-366; OPTIMIZATION_PLAN.md:551
- What it does and why it is clever: `unrolled_data_copy` computes `table + index×128` with `SHLL8`/`SHLR`, then runs 14 unrolled pairs of `MOV.L` copies with a stride add. It has no RTS and falls through into the next routine. Every modification attempt crashed.
- Key numbers: 150 B; 56 B per call (the doc's "28 longwords" is inconsistent with 56 B); destination is SDRAM, not the framebuffer, so a FIFO-burst rewrite cannot help (B-009).
- Target chapter: NEW: Software 3D on the SH-2
- Evidence: code only. The FIFO-batching idea for it is invalidated (B-009: it writes SDRAM).

---

## NEW: Software 2D effects on the SH-2 (scaling, rotation, intro effects)

### Inverse-mapped affine blit, and why it costs more than scaling
- Source: AU-NOTES, /mnt/data/src/aerobiz-ultimate/disasm/sh2/master/fb.c:699-735, 805-862; ROADMAP.md:967-1004
- What it does and why it is clever: Each display pixel steps source coordinates by `(dudx,dvdx)` along the row and `(dudy,dvdy)` per row, all in 16.16, with `dudx=cos/s`, `dvdx=sin/s`, `dudy=−sin/s`, `dvdy=cos/s`. Two source samples are packed per frame-buffer word. Once source Y varies along a scanline, line-table sharing (the free vertical scaling, see 32x/vdp.md) is impossible, so every display line is rasterized. The inner loop also carries two bounds tests and a row multiply. Correctness is checked by blitting the identity matrix and comparing its checksum with the 1:1 scaler.
- Key numbers: full screen 5.75 frames (about 10 fps) versus 2.13 for the 1:1 scale; a 128×128 region (23% of the screen) is about one frame; identity checksum $8040EA91 matches the 1:1 blit; Q15 sine table of 256 entries (512 B).
- Target chapter: NEW: Software 2D effects on the SH-2
- Evidence: emulator measured (PicoDrive)

### SEGA logo spin/zoom: precomputed inverse matrices, ease curve, V-Blank-indexed frames
- Source: AU-NOTES, tools/make_sega_logo.py:1-163; disasm/sh2/master/fb.c:1156-1297; HISTORY.md:1554-1625
- What it does and why it is clever:
  - **Build time:** a Python script decodes the logo from the ROM and computes, per frame, the Q16.16 inverse matrix `(u0,v0,dudx,dvdx,dudy,dvdy)` and a clipped even-x bounding box. The SH-2 does no trig or division.
  - **Motion:** ease-out `e = 1−(1−t)³`. Scale `s = S0^(1−e)` interpolates in log space, so the zoom feels uniform. Angle is `2 turns·2π·(1−e)`.
  - **Self-check:** the script rasterizes the last frame exactly as the SH-2 does and fails the build unless it lands pixel-for-pixel on the Genesis logo.
  - **Playback:** the SH-2 picks the frame from the V-Blank count, so a slow frame is dropped rather than overrunning the Genesis hold. It clears only the previous box of each buffer, keeping two boxes, one per buffer.
- Key numbers: 96×32 logo; 110 animation frames plus 16 hold frames; S0 = 0.06; 127 frames drawn, 0 skipped (PicoDrive); layer on frames 28-154.
- Target chapter: NEW: Software 2D effects on the SH-2
- Evidence: emulator measured (PicoDrive/Ares; Ares judged "smoothest spin" by eye only)

### Horizontal 2× stretch in place with RGB555 averaging
- Source: MARSDEV, /mnt/data/src/marsdev/examples/32x-skeleton/sh_src/mars_start.s:785-858
- What it does and why it is clever: `ScreenStretch` doubles each direct-colour line in place by walking right-to-left, so the source is not overwritten before it is read. Each source word becomes a longword: pixel and pixel, or pixel and blend. The blend `((prev & 0x7BDE) + (cur & 0x7BDE)) >> 1` averages all three RGB555 channels in one add, because masking off each channel's low bit stops carries crossing channels.
- Key numbers: mask $7BDE; pitch 640 B.
- Target chapter: NEW: Software 2D effects on the SH-2
- Evidence: code only

---

## NEW: Fixed-point maths

### Binary-angle quarter-wave sine with quadrant jump table (68K)
- Source: VRD-NOTES, disasm/modules/68k/game/physics/sine_cosine_quadrant_lookup.asm:1-30; analysis/PHYSICS_SYSTEM_ARCHITECTURE.md:165, 253
- What it does and why it is clever: Angles are 16-bit binary angle measurement (BAM) units, `$0000-$FFFF` = 360°, so wraparound is free. Cosine is the sine entry point preceded by `ADDI #$4000`, falling straight through. The top two bits select one of four quadrant handlers through a jump table, so a single quarter table serves all four quadrants.
- Key numbers: 58 B routine; trig table at 68K $930000.
- Target chapter: NEW: Fixed-point maths
- Evidence: code only

### atan2 by ratio table and octant reduction
- Source: VRD-NOTES, analysis/AI_SYSTEM_ARCHITECTURE.md:80-92; AU-NOTES, disasm/sh2/master/fb.c:900-983
- What it does and why it is clever:
  - **VRD (68K):** `ratio = DX·256/DY` indexes an atan table, returning a 16-bit angle, with ±$4000 when DY = 0.
  - **Aerobiz (SH-2):** reduces to the octant `|y| ≤ |x|`, indexes a 257-entry table with `(ay<<8)/ax`, then reflects (`90°−a`, `180°−a`, negate). Angles are Q8 fractions of 1/256 turn, so 90° = 16384.
  - **Aerobiz asin:** a 257-entry table over [−1,1] with linear interpolation, which is safe because every city lies within 37° latitude, avoiding asin's ill-conditioned ends.
  - **Aerobiz interpolated sine:** removes the 1.4° faceting of a 256-step table.
- Key numbers: 257-entry tables (about 514 B each); ANG_90 = 16384.
- Target chapter: NEW: Fixed-point maths
- Evidence: code only (VRD); emulator measured (Aerobiz arcs, see next entry)

### Great-circle arcs: measured projection, slerp, anchoring, overflow-safe weights
- Source: AU-NOTES, disasm/sh2/master/fb.c:875-1105; ROADMAP.md:1006-1050
- What it does and why it is clever:
  - **Projection fitted, not assumed:** least squares over 34 cities gives `x = 0.5972·lon + 35.13`, `y = −0.7854·lat + 92.25`, i.e. equirectangular.
  - **Arc maths:** cities become unit vectors and the arc uses spherical interpolation with `w = sin(θ)/sin(ω)`. The weight is computed as `(sin<<15)/sinω` (shift then divide) because a Q15 reciprocal of a small sinω overflows 32 bits.
  - **Seam handling:** longitude is unwrapped against the previous sample, seeded from the start city, to survive the mid-Atlantic seam.
  - **Anchoring:** endpoint error is spread linearly along the curve so arcs touch their pins exactly.
  - **Near-coincident cities:** fall back to a straight line when sinω < 64.
- Key numbers: fit error mean 3.5/4.4 px, max 7.7/11.2; 31 of 31 arcs end within 3 px; the rejected quadratic Bezier had median 1.8 px but 90th percentile 15.9 px and worst case 87 px; 16 steps per arc.
- Target chapter: NEW: Fixed-point maths
- Evidence: emulator measured (PicoDrive)

### Divide-by-constant as multiply-shift
- Source: VRD-NOTES, analysis/MASTER_FUNCTION_REFERENCE.md:3656; OPTIMIZATION_PLAN.md:466-470
- What it does and why it is clever: The speed smoothing divides by roughly 102 using `(x·644)>>16`, since 65536/644 ≈ 101.8, replacing a roughly 140-cycle 68000 `DIVS`. QW-5 lists replacing `DIVS #103` this way.
- Key numbers: about 960 cycles per frame saved (estimate).
- Target chapter: NEW: Fixed-point maths
- Evidence: code only

### Packed RGB555 channel arithmetic
- Source: AU-NOTES, disasm/sh2/master/text.c:341-358; MARSDEV, sh_src/mars_start.s:813-858
- What it does and why it is clever: `darken555(v) = (v>>1) & HALF555` halves all three channels in one shift by masking off bits that would leak between channels. `lerp555` does a per-channel `(a·(n−t)+b·t)/n` for 16-step fades. marsdev's `0x7BDE` mask does the same for two-pixel averages.
- Key numbers: fade length MENU_FADE = 16 steps.
- Target chapter: NEW: Fixed-point maths
- Evidence: code only

### Fixed-point conventions of the VR physics
- Source: VRD-NOTES, analysis/PHYSICS_SYSTEM_ARCHITECTURE.md:296-305
- What it does and why it is clever: Each quantity has one shift convention, so 16-bit 68K maths never needs a full 32×32 multiply:
  - grip and steering are 8.8 (`$0100` = 1.0);
  - drag and force scale by `>>7`;
  - gear normalisation is `>>5`;
  - position is `sin·speed >> 12`;
  - friction is `<<4`;
  - gear ratio is `×ratio >> 8`.
- Key numbers: see the shifts listed above.
- Target chapter: NEW: Fixed-point maths
- Evidence: code only

---

## NEW: Fixed-point game physics and collision (VR case material)

### 17-step vehicle pipeline with grip-limited force integration
- Source: VRD-NOTES, analysis/PHYSICS_SYSTEM_ARCHITECTURE.md:18-119
- What it does and why it is clever:
  - **Drag:** a surface drag table indexed by `raw_speed>>7`, times a gear factor `>>5`.
  - **Net force:** `drag·force>>7 − (calc_speed<<4) − (drag·$71C0>>7)`. A negative net force is doubled, so braking bites.
  - **Grip:** reset to 1.0 each frame and reduced by excess force, `excess<<8/threshold`, with a floor of 0.5 and a tire-squeal trigger.
  - **Speed:** `final = (net>>1)·grip>>7`; the slope is `final>>2/400`; speed is accumulated, then `raw_speed = display·gear·596/4096`.
  - **Gear shifts:** multiplicative, so speed stays continuous across a shift (upshift `×ratio>>8`, downshift `<<8/ratio`).
  - **Speed curve:** 384-entry speed table plus a multiplier chain (boost `×(16+m)>>4`, high-speed `×11/16`, wind `×1.75`).
- Key numbers: max speed 17,000; delta clamp ±1024 per tick; 6 real gear ratios {171,192,205,213,219,224} (the doc's "7" was corrected in VR60_ROADMAP lessons).
- Target chapter: NEW: Fixed-point game physics and collision
- Evidence: code only

### Steering and drift model
- Source: VRD-NOTES, analysis/PHYSICS_SYSTEM_ARCHITECTURE.md:123-237
- What it does and why it is clever:
  - **Steering input:** a 3-entry acceleration table [−24,+24,0]; counter-steer halving; clamp ±127; deadzone 24; EMA smoothing `(vel<<8 + old)/2`.
  - **Drift:** grip loses `|steer|·drag>>8`. Above a slip of 55, low-speed lateral force is `slip·(512−grip)>>8`, otherwise `slip·3/8`, and heading is corrected by `lat_vel·coeff>>8`.
  - **Spin-out:** triggers at a velocity limit.
  - **Settling:** natural damping zeros velocity on a zero crossing or below 16.
- Key numbers: drift accumulator 0-200, decaying 8 per frame.
- Target chapter: NEW: Fixed-point game physics and collision
- Evidence: code only

### Collision by 4-step binary search over the frame
- Source: VRD-NOTES, analysis/COLLISION_SYSTEM_ARCHITECTURE.md:45-110
- What it does and why it is clever: When any of five probes (centre plus four corners) hits, the routine rolls heading, scale, X and Y back to last frame's snapshot. It then re-advances in four quarter steps (`delta = (cur−prev)/4`), probing each time and undoing the step that collides. This resolves contact to 1/4 frame without solving geometry. Probe heights are then smoothed with an EMA, `h = (old+new)/2`. Physics reaches collision by a `JMP` tail call with no RTS boundary.
- Key numbers: up to 5 probe sets per search; α = 0.5.
- Target chapter: NEW: Fixed-point game physics and collision
- Evidence: code only

### Grid-hashed track lookup and 4-page geometry fetch
- Source: VRD-NOTES, analysis/TRACK_DATA_FORMAT.md:43-99, 154-203
- What it does and why it is clever:
  - **Grid hash:** world X/Y map to a tile via `col = ((X>>4)+$400)>>5` and `row = (($400+(Y>>4)) & $FFE0)<<1`, a centred 32-unit grid. A two-level lookup (segment map, then word offset, then base data) yields the tile pointer.
  - **Geometry pages:** four signed-byte pairs are fetched from four pages spaced `$800` apart. Curvature, normal and gradient therefore live in parallel arrays reached with one pointer, advancing `$7FF` because of the post-increment.
  - **Probe reuse:** probes landing on the same tile as the centre take a fast path.
- Key numbers: 68-byte hot routine, 11+ calls per frame; 2 KB pages.
- Target chapter: NEW: Fixed-point game physics and collision
- Evidence: code only

### Manhattan proximity zones, weighted-speed car collision, AI steering
- Source: VRD-NOTES, analysis/COLLISION_SYSTEM_ARCHITECTURE.md:129-219; analysis/PHYSICS_SYSTEM_ARCHITECTURE.md:167-183
- What it does and why it is clever:
  - **Distances:** all are `|dX|+|dY|`, with no multiplies or square roots.
  - **Zone codes:** put "critical" in bit 15, so callers test with `BMI`.
  - **Car-on-car impulse:** the faster car takes `sum·3/4` and the slower `sum·3/8`, clamped to $04DC.
  - **AI steering:** `frames = (dist<<4)/(speed+1)`, `factor = max(1, frames/2)`, `heading += Δ/factor`.
  - **Billboard rotation:** `lat = −(cos·dX + sin·dY)>>8`.
- Key numbers: thresholds $140/$2C0/$1000; 15 opponents at stride $100.
- Target chapter: NEW: Fixed-point game physics and collision
- Evidence: code only

---

## patterns/cpu-split.md

### Division of labour in Virtua Racing Deluxe
- Source: VRD-NOTES, analysis/RENDERING_PIPELINE.md:97-128; analysis/SLAVE_SH2_DISPATCH_ARCHITECTURE.md:8-17, 99-137; VR60_ROADMAP.md:1133-1153
- What it does and why it is clever:
  - **68K:** decides *what* to draw: physics, AI, collision, camera, depth sort, descriptor build, then a DREQ to the SH-2s. It never writes pixels in gameplay.
  - **Slave SH-2:** decides *how*: all 3D via two pipelines.
  - **Master SH-2:** is a command router, block copier and scene loader.

  The two SH-2s poll different COMM bytes and are never cross-triggered.
- Key numbers: historical racing-only profile:

  | CPU | Useful cycles per frame | Share |
  |---|---|---|
  | 68K | 45,481 | 63% V-blank idle |
  | Master SH-2 | 158,977 | about 41% of budget |
  | Slave SH-2 | 231,056 | about 60% of budget, about 80% utilised |

  Budgets are 128 K 68K cycles and 383 K SH-2 cycles per TV frame.
- Target chapter: patterns/cpu-split.md
- Evidence: emulator measured (PicoDrive). VR60_STATUS requires re-baselining. Early "Master renders 3D / Slave idle" docs are invalidated.

### Offload break-even: compute ≫ handshake × calls
- Source: AU-NOTES, ROADMAP.md:1442-1495; VRD-NOTES, KNOWN_ISSUES.md:617-636 ("Synchronous COMM offload of angle_normalize")
- What it does and why it is clever: Aerobiz measured a real 68K→SH-2→68K RPC round trip by saturating counters and timing them. The round trip is a flat about 228 calls per frame (about 560 68000 cycles) whatever the work. A 32-bit divide therefore wins when slow (136.6 calls per frame in place on the 68K versus 228.2 offloaded) and loses when fast (443.4 versus 228.2). VRD saw the same rule fail in practice: moving an 8×-per-frame, about 1,500-cycle routine to the Master cost 23% of 68K time spinning on COMM.
- Key numbers: break-even about 560 cycles per call; PicoDrive's comm poll detection makes 228 an upper bound.
- Target chapter: patterns/cpu-split.md
- Evidence: emulator measured (PicoDrive)

### Profile first: "offload AI" premise disproved; offloaded divide never runs
- Source: AU-NOTES, ROADMAP.md:1412-1440, 1497-1595
- What it does and why it is clever: The obvious candidates (AI, economy) were absent from the profile. The 68000 is 69.5% idle; graphics take 20.4% of frames, with the LZ decompressor alone at 11.93%. The "perfect" pure-maths offload (UnsignedDivide's slow path) was built, proven bit-identical over 12,000 frames, and then found to execute 0 times in 200,000 frames. The lesson: target shared engine code, not game logic.
- Key numbers: 418,549 gameplay frames sampled; 74-76-frame stalls every about 4,000 frames.
- Target chapter: patterns/cpu-split.md
- Evidence: emulator measured (PicoDrive)

### Batch, don't call: job lists and FM rendezvous
- Source: AU-NOTES, ROADMAP.md:1650-1668; PORT_ARCHITECTURE.md:398-410
- What it does and why it is clever: Three reasons to batch work, strongest first:
  1. An FM handover is a mutual stall: both CPUs wait.
  2. Framebuffer FIFO writes are cheaper in continuous runs (3 clocks per word unfilled versus 5 filled).
  3. RPC amortisation.

  Cartridge-bus contention is not counted because PicoDrive cannot measure it. Every offloaded routine keeps its 68K version, selectable at assembly time, so results can be diffed.
- Key numbers: see the three reasons above.
- Target chapter: patterns/cpu-split.md
- Evidence: manual (reasoning); emulator measured for the round-trip cost

### Inverted split: SH-2 as main CPU, 68K as an I/O server running from Work RAM
- Source: MARSDEV, /mnt/data/src/marsdev/examples/32x-skeleton/md_src/md_main.c:22-78; sh_src/m_main.c:14-55; sh_src/mars.c:186-233
- What it does and why it is clever: The Master runs the game. The 68K loops in `do_commands`, servicing SH-2 requests posted in COMM0 (`cmd<<8`: read pad into COMM8, set VRAM offset, write a nametable word, write VRAM), then clears COMM0. The 68K also publishes a V-Blank tick in COMM12, which the SH-2 uses for `swapBuffers()` pacing. All per-frame 68K functions are placed in `.data` (Work RAM) so the 68K stays off the cartridge bus and the SH-2s are not slowed.
- Key numbers: commands 3-7; COMM12 is a 32-bit tick.
- Target chapter: patterns/cpu-split.md
- Evidence: code only

### Slave idle time turned into a work drain (COMM7 doorbell)
- Source: VRD-NOTES, analysis/68K_SH2_COMMUNICATION.md:144-198; analysis/RENDERING_PIPELINE.md:184-197
- What it does and why it is clever: The Slave's original idle path was a 64-iteration NOP delay loop. B-003 replaced it with `inline_slave_drain`. When COMM2_HI is idle, the Slave checks COMM7; on `$0027` it reads pixel-operation parameters from COMM2-6, acks by clearing COMM7, ORs the pointer with `$20000000` (cache-through) and does the work. The 68K's `sh2_cmd_27` becomes fire-and-forget.
- Key numbers: about 50 cycles per call versus about 250 via Master dispatch; 21 calls per frame (later found to be menus/attract only; 0 in racing).
- Target chapter: patterns/cpu-split.md
- Evidence: emulator measured (PicoDrive)

---

## patterns/cache.md

### Cache-through alias discipline, and why region bits matter
- Source: VRD-NOTES, KNOWN_ISSUES.md:269-281; analysis/COMM_REGISTERS_HARDWARE_ANALYSIS.md:199-212; AU-NOTES, KNOWN_ISSUES.md:210-214
- What it does and why it is clever: The SH7604 cache does not snoop. Anything another bus master changes (COMM, VDP registers, framebuffer, data shared between SH-2s or written by DMA) must be read through the `$2xxxxxxx` cache-through mirror. The region bits still matter: `$22…` is cartridge ROM and `$26…` is SDRAM. VRD's parallel-processing design put its parameter block at `$2203E000`, which is ROM, so the block never existed.
- Key numbers: COMM base `$20004020`; SDRAM cache-through `$26000000-$2603FFFF`.
- Target chapter: patterns/cache.md
- Evidence: manual. The VRD v4.0 parallel path is invalidated.

### Read streaming input through the cached alias
- Source: AU-NOTES, disasm/sh2/master/lz.c:36-45; disasm/32x/sh2_lz.asm:38-44
- What it does and why it is clever: The compressed stream is read strictly forwards, so the SH-2 reads it via cached cartridge `$02000000`: one 16-byte line fill serves 16 bytes. Cache-through would pay the full cartridge wait on every byte. The output is built in cached SDRAM (back-references hit cache) and copied once to the framebuffer.
- Key numbers: 99.99% hit rate; misses 2,335 per iteration against about 1,920 compulsory.
- Target chapter: patterns/cache.md
- Evidence: emulator measured (PicoDrive with the opt-in SH-2 timing model added in Aerobiz U-093)

### Enable and purge the cache yourself, and the slave-cache surprise
- Source: AU-NOTES, disasm/sh2/master/main.s:63-80; HISTORY.md:1970-2008; HARDWARE_TESTS.md:176-205
- What it does and why it is clever: Startup writes `CCR=0` (CE off, as required before changing CCR), then `$10` (CP purge), then `$01` (CE on). This is idempotent and guards against a boot ROM that did not do it. The timing model first showed the slave's two-instruction idle spin paying an 8-word SDRAM burst on every fetch, which the explicit enable fixed. Later, the BIOS dumps showed both boot ROMs already write `CCR=$11`, so the original run probably took PicoDrive's no-BIOS boot path.
- Key numbers: slave wait cycles 139.4 M → 472,472 (295×); master hit rate 99.5%.
- Target chapter: patterns/cache.md
- Evidence: emulator measured (PicoDrive). The "slave never enabled its cache" attribution is called into doubt by HARDWARE_TESTS item 7.

---

## sh2/cache.md

### 1,748-byte renderer in cache-as-RAM (Pipeline 1)
- Source: VRD-NOTES, analysis/sh2-analysis/SH2_RENDERING_ARCHITECTURE.md:22-68, 154-158
- What it does and why it is clever: At boot the Slave copies 437 longwords of rendering code to `$C0000000`, the SH7604 cache's data array used as 2 KB of on-chip RAM. A 56-byte context lives at `$C0000700`. For each entity, 52 bytes of state are copied to `$C0000740` and the on-chip code is called. It has 77 internal BSRs and zero SDRAM references, so it runs with zero wait states and no misses. It handles 36 entity passes per frame and the project calls it untouchable. (The SH7604 cache-as-RAM mode is general background, not stated in these docs.)
- Key numbers: 1,748 B code; 4 + 8 + 24 = 36 passes.
- Target chapter: sh2/cache.md
- Evidence: code only

### Single-line associative purge and CCR control helpers
- Source: MARSDEV, sh_src/mars_start.s:751-783
- What it does and why it is clever: `CacheClearLine` ORs a 16-byte-aligned address with `$40000000` (the associative-purge area) and writes 0, invalidating just that line so shared data is re-read without purging the whole cache. `CacheControl` writes `CCR` with CP=$10, TW=$08 (two-way mode), CE=$01.
- Key numbers: purge area `$40000000`; CCR at `$FFFFFE92`.
- Target chapter: sh2/cache.md
- Evidence: code only

---

## patterns/bus.md

### What each CPU can reach: the three shared channels
- Source: VRD-NOTES, KNOWN_ISSUES.md:244-268; analysis/COMM_REGISTERS_HARDWARE_ANALYSIS.md:247-259; AU-NOTES, lz.c:170-185
- What it does and why it is clever:
  - The SH-2 cannot see 68K Work RAM at any address; `$02400000-$03FFFFFF` is unmapped.
  - The 68K cannot see SDRAM.
  - The only shared paths are COMM (16 bytes), the DREQ FIFO (68K→SH-2 bulk), and the framebuffer under FM arbitration.
  
  VRD lost three attempts (B-003 v1-v3) to Work-RAM ring buffers before reading the manual.
- Key numbers: COMM 1 wait (SH-2) / 0 wait (68K); framebuffer 5 waits; cartridge 6-15 waits; SDRAM 2-6 waits.
- Target chapter: patterns/bus.md
- Evidence: manual, plus emulator (failed attempts)

### The framebuffer as a shared mailbox
- Source: AU-NOTES, ROADMAP.md:1690-1712; HISTORY.md:183-189; ROADMAP.md:1990-1998
- What it does and why it is clever: With the layer blanked, the frame buffer above `$012000` (past the line table and 224 lines) is free scratch for SH-2→68K results. LZ output is written there in words and copied out by the 68K. Small UX state lives in a measured gap at `$11F00`, stored as value+2 because a byte write cannot store zero.
- Key numbers: copy-back costs about 10 68K clocks per word, under 2-3% of decompression.
- Target chapter: patterns/bus.md
- Evidence: emulator measured (PicoDrive/Ares). Caveats: the region collides with a live 32X layer, and under FS flips the `$0400_0000` aperture bank-swaps.

### FM ownership must be an explicit protocol
- Source: AU-NOTES, KNOWN_ISSUES.md:168-174, 722-738; VRD-NOTES, analysis/RENDERING_PIPELINE.md:71-90; KNOWN_ISSUES.md:153-157
- What it does and why it is clever: Writing FM preempts the other side immediately, even mid-access. VRD toggles FM only inside V-INT. Aerobiz raises a "busy" bit so V-Blank logic leaves FM alone during LZ copies. A "deferred draw" design that flipped FM within microseconds of an RPC answer passed 113/114 on PicoDrive but crashed Ares (wild SH-2 writes). The rule became an explicit grant/acknowledge pair on both sides.
- Key numbers: see above.
- Target chapter: patterns/bus.md
- Evidence: emulator measured (PicoDrive/Ares)

### RV versus SH-2 ROM access
- Source: VRD-NOTES, KNOWN_ISSUES.md:147-152; AU-NOTES, KNOWN_ISSUES.md:216-223; ROADMAP.md:1755-1760
- What it does and why it is clever: While RV=1 (Genesis DMA from ROM), every SH-2 cartridge access stalls. VRD profiled that it never sets RV (it feeds the DREQ FIFO manually), so SH-2 code in expansion ROM is safe. Aerobiz needs RV windows for Genesis DMA, so it keeps SH-2 code in SDRAM and calls the RV-versus-SH-2-ROM-read interaction "the next thing to measure".
- Key numbers: see above.
- Target chapter: patterns/bus.md
- Evidence: emulator measured (B-008 profiling); manual

---

## patterns/60fps.md

### Why VR runs at 20 Hz: a state machine, not a compute limit
- Source: VRD-NOTES, analysis/FRAME_RATE_ARCHITECTURE.md:38-98; OPTIMIZATION_PLAN.md:88-118; VR60_ROADMAP.md:1133-1153
- What it does and why it is clever: `$C87E` advances 0→4→8, one state per V-INT. Only state 8 runs the game frame and arms V-INT handler `$54`. That handler swaps buffers and resets the state to 0 only when COMM1_LO bit 0 ("SH-2 done") is set; otherwise the machine stalls and retries. This gives graceful frame dropping with no timeouts. Fps = 60 / max(3, ⌈render time / TV frame⌉).
- Key numbers: 3 TV frames per game tick; racing 68K 63% idle.
- Target chapter: patterns/60fps.md
- Evidence: emulator measured (PicoDrive; exact caller trace confirms about 20 Hz)

### Self-modifying main loop with STOP and per-state V-INT dispatch
- Source: VRD-NOTES, analysis/FRAME_RATE_ARCHITECTURE.md:14-35; analysis/VINT_HANDLER_ARCHITECTURE.md:14-82
- What it does and why it is clever: The main loop lives in Work RAM at `$FF0000`: `JSR <handler>` (target patched at `$FF0002`), then `MOVE.W #state,$C87A` (immediate patched at `$FF0008`), then `STOP #$2300`. V-INT reads and clears `$C87A` and uses it as a direct byte offset into a 4-byte jump table. Switching game mode is one longword write.
- Key numbers: about 21 table slots with pad gaps; frame counter `$C964` at 60 Hz.
- Target chapter: patterns/60fps.md
- Evidence: code only

### STOP wakes on any interrupt: re-check the flag
- Source: VRD-NOTES, KNOWN_ISSUES.md:480-487
- What it does and why it is clever: Replacing V-Blank spin-waits with `STOP #$2300` let H-INT (whose vector is a bare RTE) wake the main loop early. The fix is to follow STOP with `TST.W $C87A / BNE` back to the STOP.
- Key numbers: car-select screen recovered from 1 fps to 5 fps (still slower than the original 20; partially fixed).
- Target chapter: patterns/60fps.md
- Evidence: emulator measured (PicoDrive)

### Faking 30 fps by skipping a state fails without delta-time (S-4)
- Source: VRD-NOTES, OPTIMIZATION_PLAN.md:177-221; analysis/FRAME_RATE_ARCHITECTURE.md:263-330; VR60_ROADMAP.md:2243-2290
- What it does and why it is clever: Changing `ADDQ #4` to `ADDQ #8` gave 30 fps at once, but every per-tick constant is hard-coded for 20 Hz: speed clamp ±$400, air drag $71C0, boost $738, 15/10/30-frame timers, replay at 1 byte per tick, and frame thresholds 1241/1296. Scaling them by ×2/3 and ×1.5 across 20+ files broke collision, checkpoint music and attract timing. The plan now is to move logic into one SH-2 codebase with a single delta-time scale (60 Hz needs ÷3).
- Key numbers: inventory of about 30 constants (FRAME_RATE §6).
- Target chapter: patterns/60fps.md
- Evidence: emulator measured (reverted)

### Camera-interpolated extra renders (A-1 "40 fps")
- Source: VRD-NOTES, analysis/FRAME_RATE_ARCHITECTURE.md:432-496; OPTIMIZATION_PLAN.md:18-45, 223-232
- What it does and why it is clever: The idea: snapshot previous and current camera, average 8 words, re-send by DREQ for a second render in state 4, block-copy and swap, while logic stays at 20 Hz.
- Key numbers: 192 bytes of trampoline; claimed SH-2 headroom 52%.
- Target chapter: patterns/60fps.md
- Evidence: invalidated. The hook was in the 2P dispatcher, and VR60_STATUS no longer accepts any 40-fps 1P result.

### Drop frames by V-Blank clock, never run long
- Source: AU-NOTES, disasm/sh2/master/fb.c:1248-1297
- What it does and why it is clever: The renderer derives its frame index from `vint_count − t0`, counting skipped frames, so a slow frame shortens the motion instead of overrunning a fixed Genesis-side hold.
- Key numbers: 127 drawn, 0 skipped (PicoDrive).
- Target chapter: patterns/60fps.md
- Evidence: emulator measured (PicoDrive)

### A strict definition of "60 fps achieved"
- Source: VRD-NOTES, VR60_STATUS.md:449-471
- What it does and why it is clever: The bar is 60 Hz logic and input (not just swaps or interpolated views), 60 distinct ordered frames per second, real-time equivalence of physics, timers and audio, no COMM deadlock or cache-alias errors over long runs, and a recorded ROM, input and profiler setup.
- Key numbers: see above.
- Target chapter: patterns/60fps.md
- Evidence: manual (project policy)

---

## 32x/vdp.md

### Packed-pixel line table, and the one-pass word-write rules
- Source: AU-NOTES, PORT_ARCHITECTURE.md:329-351; disasm/sh2/master/fb.c:1-110; VRD-NOTES, analysis/graphics-vdp/32X_FRAME_BUFFER_FORMAT.md:52-131
- What it does and why it is clever:
  - **Layout:** a 256-word line table heads each buffer, each entry the word address of a line. Pixel data starts at word 256, 160 words (320 px) per line.
  - **Rules:**
    - The VDP always shows 320 px, so short rows display garbage.
    - Byte writes cannot store 0, so use word writes.
    - FM=1 hands both the framebuffer and the VDP registers to the SH-2, so the 68K must set the mode first.
  - **VRD's variant:** a power-of-two `$200`-byte stride (320 px used), so line address = base + y<<9.
- Key numbers: 71,680 B per packed screen; direct colour needs 143,360 B, so only about 204 lines fit.
- Target chapter: 32x/vdp.md
- Evidence: manual, plus emulator measured (Aerobiz U-002 gradient test)

### Line-table vertical scaling for free (zoom)
- Source: AU-NOTES, ROADMAP.md:1301-1410; disasm/sh2/master/fb.c:269-353; MARSDEV, sh_src/mars.c:26-70
- What it does and why it is clever: Nothing forbids two line-table entries pointing at the same row. Each distinct source row is rasterized once into the next free slot, and every display line that maps to it reuses the slot. Vertical magnification is free; cost = distinct rows × 320. X scaling is a per-pixel 16.16 loop packing two samples per word. The window is clamped inside the source rather than bounds-tested per pixel. Overlays drawn into a slot scale automatically. marsdev's `lineskip` uses the same idea for line doubling.
- Key numbers: 224/112/56 rows at 1×/2×/4×, giving 2.13/1.06/0.53 frames per blit (28, 56, 60-capped fps); 1:1 output 100.00% identical to a straight copy.
- Target chapter: 32x/vdp.md
- Evidence: emulator measured (PicoDrive; Ares 2-3 frames for a 1:1 redraw)

### SFT is panning, not scaling
- Source: AU-NOTES, ROADMAP.md:1316-1326; PORT_ARCHITECTURE.md:349-351
- What it does and why it is clever: Line-table addresses are word units, so 2-dot granularity. The SFT bit adds 1-dot horizontal panning but cannot scale. It is ignored when the low byte of the line-table base address is `$FF`.
- Key numbers: see above.
- Target chapter: 32x/vdp.md
- Evidence: manual

### Frame swap rules: paint, wait V-Blank, flip, wait for FS to change
- Source: AU-NOTES, KNOWN_ISSUES.md:739-751; disasm/sh2/master/fb.c:461-475; text.c:416-440; VRD-NOTES, KNOWN_ISSUES.md:544-550
- What it does and why it is clever: FS written during display is deferred to the next V-Blank (manual). Only the back buffer may be touched, and only after FS reads back changed. VRD found that a main-loop swap plus a V-INT swap at the same V-Blank cancel out. Aerobiz found that PicoDrive drops an out-of-V-Blank FS write outright, so a full-page paint must come before the V-Blank wait. Both buffers are painted for static screens.
- Key numbers: see above.
- Target chapter: 32x/vdp.md
- Evidence: emulator measured (PicoDrive/Ares disagree; Ares follows the manual)

### Palette window (PEN): poll per word, retry next frame
- Source: AU-NOTES, KNOWN_ISSUES.md:160-166, 753-763; disasm/sh2/master/text.c:442-465; HISTORY.md:157-189
- What it does and why it is clever: In packed mode the palette is word-only and writable only while PEN=1, finishing within about 1 µs of PEN falling. It is always writable while the layer is blank, so the full palette is loaded before raising the layer. Fades check PEN before each entry and simply retry next frame. PicoDrive opens PEN only in V-Blank while Ares also opens it in each H-Blank, so phase assumptions break on one emulator or the other.
- Key numbers: 16-step fades.
- Target chapter: 32x/vdp.md
- Evidence: emulator measured (PicoDrive/Ares)

### Auto-fill hardware and a DIVS delay
- Source: VRD-NOTES, analysis/RENDERING_PIPELINE.md:342-356; disasm/modules/68k/game/render/mars_dma_xfer_vdp_fill.asm:41-62
- What it does and why it is clever: Writing length, address and data registers clears a run in hardware; the code polls FEN. VRD's 68K clears 192 lines of 160 words, stepping the address `$100` words per line. It burns the fill latency with a `DIVS #$378` (a roughly 140-cycle instruction as a cheap delay) before polling.
- Key numbers: fill time = 7 + 3 × length cycles; length up to 256 words.
- Target chapter: 32x/vdp.md
- Evidence: code only

### Framebuffer write FIFO and the 16-bit DRAM bus
- Source: VRD-NOTES, analysis/POLYGON_TRANSFORMATION_ANALYSIS.md:43-51; analysis/RENDERING_PIPELINE.md:335-340
- What it does and why it is clever: The four-word write FIFO gives 3 + 3 + 3 + 5 = 14 cycles per four writes (3.5 per word) only for back-to-back writes. The framebuffer DRAM is 16-bit, so an SH-2 `MOV.L` becomes two word writes with no gain. The overwrite image at `$04020000`/`$860000` treats zero bytes as transparent.
- Key numbers: 3.5 cycles per word in a burst.
- Target chapter: 32x/vdp.md
- Evidence: manual. VRD's plan to apply this to `unrolled_data_copy` is invalidated (B-009).

---

## 32x/compositing.md

### PRI bit plus per-colour through bit
- Source: VRD-NOTES, analysis/RENDERING_PIPELINE.md:405-498
- What it does and why it is clever: With PRI=0 the Genesis layer is in front (VR's HUD over 3D). Bit 15 of a 32X colour inverts priority for that pixel. VR sets palette entry 1 to `$8000`, opaque black that sits in front of the Genesis layer, for masking. Index 0 on the 32X and colour 0 on the Genesis are transparent; when both are transparent the backdrop shows.
- Key numbers: CRAM entry format T|B5|G5|R5.
- Target chapter: 32x/compositing.md
- Evidence: manual

### Covering a repeating Genesis plane with a through-bit sidebar
- Source: AU-NOTES, disasm/sh2/master/fb.c:426-460; HISTORY.md:1155-1170; HARDWARE_TESTS.md:261-289
- What it does and why it is clever: In H40 a 32-cell Genesis plane repeats columns 0-63 at 256-319. The map asset leaves that strip as index 0 and nothing else uses index 0. Setting the through bit on entry 0 alone puts just that strip in front of the Genesis layer under PRI=0, hiding the repeat at zero pixel cost.
- Key numbers: SIDEBAR_COLOUR `$2400 | $8000`.
- Target chapter: 32x/compositing.md
- Evidence: emulator measured (PicoDrive/Ares agree). PicoDrive adds one green step to through-bit colours.

### H32 is illegal under a live layer
- Source: AU-NOTES, ROADMAP.md:191-228, 587-640
- What it does and why it is clever: The 32X video clock is EDCLK (always the H40 clock), so an H32 Genesis screen and the 32X layer differ in scale by 1.25×. The manual allows H32 only with the layer blank. The map screen therefore forces register 12 to H40 from the game's own register shadow each frame while the layer is up, and only then.
- Key numbers: H40 registration 100.00% pixel-identical; a nearest-neighbour stretch of H32 only 95.6%.
- Target chapter: 32x/compositing.md
- Evidence: emulator measured (PicoDrive; Ares agrees in H40)

### Genesis CRAM mirrored into the 32X palette
- Source: AU-NOTES, disasm/32x/map_screen.asm:1-58, 295-343; HISTORY.md:1188-1206; KNOWN_ISSUES.md:640-647
- What it does and why it is clever:
  - **Mirror:** palette entries 16-31 track CRAM line 1, so Genesis fades, tints and dimming apply to the SH-2 map for free. The source is the game's RAM copy of CRAM at `$FF1400`, which needs no VDP read.
  - **Timing:** mirroring from V-Blank ran exactly one frame behind, because the game writes CRAM just after its V-Blank handler. The palette-writer routine is therefore hooked to mirror at the moment of the write, with PEN checked per word.
  - **Conversion:** a 512-entry assembler-generated table converts 9-bit Genesis colour to BGR555 by bit replication, `(v<<2)|(v>>1)`.
  - **Exit:** the layer leaves when the line-1 fade reaches black, or after 48 frames.
- Key numbers: copy equalled CRAM in 64 of 64 words over 222 states; the stale-frame bug showed 12,288 Genesis pixels new against 45,056 map pixels old; 71 of 71 frames exact through a turn change.
- Target chapter: 32x/compositing.md
- Evidence: emulator measured (PicoDrive)

### A palette budget shared by every layer user
- Source: AU-NOTES, PORT_ARCHITECTURE.md:425-445
- What it does and why it is clever:

  | Range | Owner |
  |---|---|
  | 0 | sidebar / transparent |
  | 1-15 | engine UI |
  | 16-31 | CRAM mirror (never written by anything else) |
  | 32-63 | UI ramps |
  | 64-253 | content art, re-uploaded per screen in one PEN window |
  | 254-255 | text ink/paper |

  The layer is double-buffered but the palette is not, so ownership is declared per layer state.
- Key numbers: 256 BGR555 words.
- Target chapter: 32x/compositing.md
- Evidence: code only (design)

### Seamless 32X-to-Genesis hand-off
- Source: AU-NOTES, disasm/sh2/master/fb.c:1270-1290; HISTORY.md:1598-1606; HARDWARE_TESTS.md:223-260
- What it does and why it is clever: When both buffers hold the identity frame, PRI is cleared in V-Blank so the identical Genesis logo takes the front, then the layer blanks unseen. This works around PicoDrive carrying PRI in the green LSB. On hardware, and on Ares, the Genesis DAC is nonlinear (0, 52, 87, 116, 144, 172, 206, 255) against the 32X's linear output, so a small colour step is expected at the first switch.
- Key numbers: level 7 is 255 on the Genesis against about 238 from the 32X palette.
- Target chapter: 32x/compositing.md
- Evidence: emulator measured (PicoDrive/Ares)

---

## 32x/communication.md

### COMM hazard rules and set/clear ownership
- Source: VRD-NOTES, analysis/COMM_REGISTERS_HARDWARE_ANALYSIS.md:137-195, 421-438
- What it does and why it is clever: Any overlapping write+write or write+read of one COMM register is undefined, so the manual warns against splitting registers by direction. VRD's model is that the 68K sets non-zero values, the SH-2 clears them, and readiness is signalled through a different register. SH-2 writes sit in a one-level write buffer, so a dummy read of the same address forces visibility.
- Key numbers: 8 registers × 16 bits; SH-2 needs 3 clocks (1 wait) per access.
- Target chapter: 32x/communication.md
- Evidence: manual

### Torn-read defence, level-polled state words and generation tags
- Source: AU-NOTES, disasm/sh2/master/rpc.c:1-90; disasm/32x/map_screen.asm:28-30
- What it does and why it is clever: Every read of a word written by the other side is taken twice and must agree. Map on/off is a level the SH-2 polls, not an RPC, so V-Blank-time changes cannot race the LZ handshake on the same slots. "Drawn" replies carry the switch-on generation, so a stale reply from an earlier visit is ignored.
- Key numbers: generation field `$0F00`; status bit `$8000`.
- Target chapter: 32x/communication.md
- Evidence: emulator measured (PicoDrive/Ares)

### Single-shot command protocol with early parameter release
- Source: VRD-NOTES, analysis/RENDERING_PIPELINE.md:159-182, 233-248; analysis/68K_SH2_COMMUNICATION.md:200-252
- What it does and why it is clever: The original handshake took three waits. In the replacement:
  1. The 68K waits for COMM0_HI to be 0.
  2. It writes all parameters, then the index in LO and the trigger in HI, last.
  3. The SH-2 copies the parameters and clears COMM0_LO ("consumed"), so the 68K can return before the work finishes.
  4. At the end the handler clears HI with a byte write and re-checks LO; if another `$22` is already queued it loops without going back to the dispatcher.
- Key numbers: about 170 versus about 300 cycles per call (cmd $22); about 100 versus about 350 (cmd $25).
- Target chapter: 32x/communication.md
- Evidence: emulator measured (PicoDrive)

### COMM namespace discipline and ack-after-handler
- Source: VRD-NOTES, analysis/68K_SH2_COMMUNICATION.md:166-173; analysis/COMM_REGISTERS_HARDWARE_ANALYSIS.md:324-355; AU-NOTES, KNOWN_ISSUES.md:765-777
- What it does and why it is clever:
  - **Namespace:** writing game command bytes into the COMM7 doorbell triggered uninitialised Slave handlers and crashed (B-006).
  - **Atomic clear:** `hw_init_short` clears COMM0:1 with one longword zero, then sets COMM1 bit 0 ("done"), so COMM1 can never carry parameters.
  - **Ack after handler:** Aerobiz's dispatcher re-dispatched any word left set, so a blocking menu left "3" behind and swallowed later LZ jobs. Every case now clears COMM0 after its handler returns, and every 68K timeout path writes the exit word.
- Key numbers: see above.
- Target chapter: 32x/communication.md
- Evidence: emulator measured (PicoDrive)

### Bounded waits with fallback to the 68K, and PicoDrive's poll detector
- Source: AU-NOTES, disasm/32x/sh2_lz.asm:1-80; ROADMAP.md:1517-1530; KNOWN_ISSUES.md:291-307
- What it does and why it is clever: Each offload thunk counts down (`SH2LZ_TIMEOUT` = 400,000) and runs the stock 68K routine if the SH-2 never answers: a slow screen load beats a hang. Comm slots are protected by masking 68K interrupts for the call. Under PicoDrive the 68K is halted after 11 comm reads less than 64 cycles apart, so timeout paths never execute there; only Ares or hardware exercise them.
- Key numbers: 11 reads / 64 cycles poll-detect threshold.
- Target chapter: 32x/communication.md
- Evidence: emulator measured (PicoDrive/Ares)

### CMD interrupt specifics
- Source: VRD-NOTES, analysis/COMM_REGISTERS_HARDWARE_ANALYSIS.md:216-243; KNOWN_ISSUES.md:216-222; AU-NOTES, KNOWN_ISSUES.md:203-208
- What it does and why it is clever: INTM and INTS raise CMD on the Master or Slave from the 68K. There is no SH-2→68K interrupt. Unlike V/H/PWM, CMD is negated when masked and re-asserts on unmask if still pending. It is cleared via `$2000401A`.
- Key numbers: see above.
- Target chapter: 32x/communication.md
- Evidence: manual

### Boot handshake
- Source: VRD-NOTES, analysis/COMM_REGISTERS_HARDWARE_ANALYSIS.md:263-320; MARSDEV, md_src/md_start.s:162-178
- What it does and why it is clever: The Master posts "M_OK" in COMM0:1; the Slave posts "SLAV" and "S_OK". The 68K waits for both, then clears them to release the SH-2s and sets "INIT". marsdev's 68K also clears RV so the SH-2s can read ROM and sets FM before releasing the Master.
- Key numbers: `$4D5F4F4B`, `$535F4F4B`, `$534C4156`.
- Target chapter: 32x/communication.md
- Evidence: manual

---

## 32x/fifo.md

### Bulk 68K→SH-2 transfer through the DREQ FIFO
- Source: VRD-NOTES, disasm/modules/68k/game/render/mars_dma_xfer_vdp_fill.asm:17-40; analysis/FRAME_RATE_ARCHITECTURE.md:180-198; analysis/sh2-analysis/SH2_COMMAND_HANDLER_REFERENCE.md:204-210; VR60_ROADMAP.md lessons (2026-03-17)
- What it does and why it is clever: The 68K sets DREQ_LEN=`$500` and `68S` mode, posts a command in COMM0, waits for the SH-2's DMAC to arm (COMM1 bit 1), then streams `$FF6000` into the FIFO with 10 unrolled block calls. The DMAC drains it to SDRAM and the 68K cannot choose where. One transfer per game tick carries camera, viewports and all descriptors.
- Key numbers: 1,280 words = 2,560 B per tick, 128 words per block call.
- Target chapter: 32x/fifo.md
- Evidence: code only

### Zero-COMM DREQ transaction gated by two CMD interrupts
- Source: VRD-NOTES, analysis/evidence/vr60-q020-mode1-cmdint-gate/README.md:25-75; VR60_STATUS.md:186-233
- What it does and why it is clever:
  1. Before the setup edge the 68K publishes `68S`, LEN and the encoded destination, then raises CMD.
  2. The Master ISR arms DMAC0 (SAR/DAR/TCR/CHCR/DMAOR) only if the setup and completion counts match and the interrupted PC is at a known-idle boundary.
  3. The 68K writes groups of four words, checking FIFO FULL before each, waits for LEN=0 and `68S` auto-clear, then raises a second CMD.
  4. The ISR checks DAR, TCR=0 and TE, acknowledges TE (read 1, write 0) and clears CMD.
  
  Every ISR toggles FRT TOCR per the interrupt erratum.
- Key numbers: 64 B in 8 groups (mode 1); 3,840 B in 480 groups (mode 2, `$FF9100` → `$06010000`).
- Target chapter: 32x/fifo.md
- Evidence: emulator measured (PicoDrive, isolated validation stage; explicitly not hardware or authority proof)

---

## 32x/pwm.md

### Keeping PWM fed inside long SH-2 jobs
- Source: VRD-NOTES, analysis/sh2-analysis/SH2_COMMAND_HANDLER_REFERENCE.md:57-79, 107-176, 204-225
- What it does and why it is clever: Every heavy Master handler calls `pwm_fifo_fill` (192 samples) between DMAC setup and the render work. The bulk track loader (`$06004228`) interleaves PWM output with the copy, so audio keeps playing through scene loads without interrupts.
- Key numbers: 192 samples per call; track copy 56,208 B.
- Target chapter: 32x/pwm.md
- Evidence: code only

### PWM versus DMA restrictions
- Source: AU-NOTES, KNOWN_ISSUES.md:197-201; PORT_ARCHITECTURE.md:412-416
- What it does and why it is clever: A CPU that drives PWM, or touches the VDP in an H interrupt, cannot use auto-request DMA. If both SH-2s run auto-request DMA, one crawls. The plan streams PCM over DMA channel 1 accordingly.
- Key numbers: PWM is 2 channels of 11-bit PCM.
- Target chapter: 32x/pwm.md
- Evidence: manual (M6 unbuilt)

---

## patterns/audio.md

### 68K-resident FM/PSG sequencer with a tiny Z80 DAC player
- Source: VRD-NOTES, analysis/SOUND_DRIVER_ARCHITECTURE.md:1-118, 191-330
- What it does and why it is clever:
  - **CPU split:** the 68K synthesizes everything each tick; the Z80 runs only a 653-byte DAC loop with three mailbox bytes.
  - **Commands:** game code writes three priority mailboxes (music, SFX deduplicated, ambient) instead of calling the driver.
  - **SFX overlay:** six SFX channels overlay music FM channels, saving and restoring state.
  - **Volume:** a per-algorithm table scales only carrier operators.
  - **Sequences:** byte streams use call/return and loop counters.
  - **Fades:** separate DAC, FM and PSG fade rates.
- Key numbers: 18 channels × 48 B; 128-entry priority table; PSG table of 128 notes; 4 KB DAC samples.
- Target chapter: patterns/audio.md
- Evidence: code only

---

## patterns/streaming.md

### LZ decompression moved to the SH-2 (patch the routine, not the callers)
- Source: AU-NOTES, ROADMAP.md:1603-1776; disasm/sh2/master/lz.c:1-215; disasm/32x/sh2_lz.asm:1-80
- What it does and why it is clever: An 8-byte size-neutral patch at `LZ_Decompress`'s entry covers all 92 call sites. The thunk:
  1. masks interrupts and gives FM to the SH-2;
  2. passes the source as a cached cartridge address, plus a framebuffer offset;
  3. polls with a timeout;
  4. takes FM back and copies to the 68K buffer.

  The SH-2 decompresses into SDRAM, not the framebuffer: zero bytes cannot be byte-written, and back-reference reads from the framebuffer cost 5-12 waits. It then writes words out.
- Key numbers:

  | | 68000 | SH-2 |
  |---|---|---|
  | Cycles per output byte | 285 | 59.7-60.7 |
  | Largest block (27,872 B) | 62 frames | 4.4 frames |
  
  14.1-14.4× faster in wall clock. The quarter-boundary stall drops from 74-76 frames to about 5. Over 12,000 frames the patched build ran 198 frames ahead, with 31 of 31 matched frames bit-identical.
- Target chapter: patterns/streaming.md
- Evidence: emulator measured (PicoDrive with the opt-in SH-2 timing model added in Aerobiz U-093; Ares)

### The KOEI LZ format and why to transcribe it literally
- Source: AU-NOTES, disasm/sh2/master/lz.c:46-160; tools/lz_decompress.py:1-50
- What it does and why it is clever:
  - **Structure:** a control byte covers 8 tokens (bit set = literal). Matches use a prefix-coded length (the position of the first set bit picks 0-13 extra bits) and nine distance buckets.
  - **Quirk kept on purpose:** `read_bits(n)` plus the caller's `ANDI #$7FFF` consumes n+1 bits.
  - **Interleaving:** literals and refill words share one pointer, and stream words are little-endian.
  - **Copies:** byte-forward, so overlapping copies replicate runs.
  - **Safety:** overrun is refused per token with 0x100 bytes of headroom.

  The 68K, the Python tool and the SH-2 C version are kept diffable.
- Key numbers: 22,528-byte output; FNV-1a `0x3640A33D`, matched independently.
- Target chapter: patterns/streaming.md
- Evidence: emulator measured (PicoDrive)

### Brute-force asset location by decompressing at every offset
- Source: AU-NOTES, HISTORY.md:2035-2057; ROADMAP.md:929-965
- What it does and why it is clever: The map was neither raw nor in the obvious loader. The reimplemented decompressor was run at every even ROM offset with early abort against the first three expected tiles, giving exactly one hit at `$088CF8`. The nametable turned out to be linear (tiles 1..704), so the map is a plain 256×176 bitmap. A 22 KB exact match also validates the decompressor.
- Key numbers: 704 tiles; 100.00% byte match with VRAM.
- Target chapter: patterns/streaming.md
- Evidence: emulator measured (savestate VRAM comparison)

### Forwarding Genesis tile uploads to the SH-2 copy
- Source: AU-NOTES, PORT_ARCHITECTURE.md:353-382; disasm/sh2/master/fb.c:477-558; KNOWN_ISSUES.md:649-720
- What it does and why it is clever:
  - **Hooks:** the game edits map tiles (route dashes, report title bar) before upload, so both upload choke points are hooked: CPU `BulkCopyVDP` and the DMA thunk.
  - **Gate:** the full VRAM-write command shape, which excludes VSRAM.
  - **Address decode:** the VRAM address is unfolded with `(cmd>>16 & $3FFF) | (cmd&3)<<14`.
  - **Transport:** in-range words (slots 1-704) pass through a framebuffer mailbox in `$800`-word chunks.
  - **Decode:** the SH-2 decodes 4bpp nibbles to palette 16-31 at the right cells, honouring the burst's auto-increment, and marks dirty only on real change.
  - **Cost control on Ares:** non-final chunks set bit 31 to skip the redraw.
- Key numbers: 113 of 114 oracle frames exact; Ares 1:1 redraw 2-3 frames; 435 redraws observed against about 40 predicted, so the next lever is redraw count.
- Target chapter: patterns/streaming.md
- Evidence: emulator measured (PicoDrive/Ares)

---

## patterns/layering.md

### 68K decides, SH-2 draws: map-layer lifecycle
- Source: AU-NOTES, disasm/32x/map_screen.asm:1-58; ROADMAP.md:1091-1170
- What it does and why it is clever: The game's screen id (`$FF9A1C` = 7) drives the layer from the V-Blank trampoline:
  1. **Switch on:** a new generation is posted and FM goes to the SH-2, which draws both buffers while the layer is still blank.
  2. **Show:** when the "drawn" reply carries a matching generation, the 68K takes FM back, mirrors the palette, shows the layer with PRI=0 and forces H40.
  3. **Switch off:** happens after the fade, because the screen id changes before the picture does.
  
  Plane B's map cells are filled with transparent tile 0 by a 5-byte same-length patch.
- Key numbers: 21 calling screens; 48-frame linger cap.
- Target chapter: patterns/layering.md
- Evidence: emulator measured (PicoDrive)

---

## megadrive/vdp-dma.md

### Genesis VDP DMA from a banked 32X game: translate at the sink, run the window from the stack
- Source: AU-NOTES, PORT_ARCHITECTURE.md:77-203; disasm/32x/dma_stub.asm:1-139
- What it does and why it is clever:
  - **The real obstacle:** register 23 holds seven source bits (DMD0 doubles as bit 23), so `$900000` encodes fine. The obstacle is that the adapter does not serve `$880000-$9FFFFF` to VDP DMA, which needs RV=1 to place the cartridge at its own offsets.
  - **Translate at the sink:** one sink (`ConfigVDPDMA`) applies `if (src & $F00000) == $900000: src -= $800000`. Genesis-form sources below `$100000` get `+$100000`; Work-RAM sources pass untouched.
  - **Run the window from RAM:** the RV-on / trigger / drain / RV-off sequence must run from RAM, and no Work RAM is reliably free. The thunk copies the position-independent window body below SP each transfer, jumps to it, then pops it.
  - **Size-neutral hook:** the game's own `jsr $FFF000` (6 bytes) is repointed.
- Key numbers: window body about 25 word moves; 3,000 frames with 233 RV mapping changes, 100 of 100 frames identical; later 6,489 frames with 485 changes, all identical.
- Target chapter: megadrive/vdp-dma.md
- Evidence: emulator measured (PicoDrive with Aerobiz's RV-emulation patch to the PicoDrive core, VRD_RV_EMULATION; Ares). Whether `$880000` truly unmaps under RV=1 is unverified on hardware.

### Off-screen plane rows are live scratch
- Source: AU-NOTES, PORT_ARCHITECTURE.md:526-560; ROADMAP.md:1200-1290
- What it does and why it is clever: The game keeps data past the 28 displayed rows (plane A to row 91, B to row 78) at fixed VRAM addresses. Widening the plane from 32 to 64 cells halves the row stride and slides the visible window onto that scratch. A VRAM write trace found the culprit: `CmdSetupDMA` with an absolute destination (192 bytes to `$EA80` at frame 8201).
- Key numbers: 432 of 600 sampled frames differ from frame 8250 onward.
- Target chapter: megadrive/vdp-dma.md
- Evidence: emulator measured (PicoDrive VRAM trace)

### Palette DMA and FB swap inside V-INT
- Source: VRD-NOTES, analysis/VINT_HANDLER_ARCHITECTURE.md:85-134
- What it does and why it is clever: VR's V-INT state `$54`:
  1. writes scroll and colour registers;
  2. requests the Z80 bus;
  3. DMAs 64 palette words from ROM to CRAM;
  4. releases the bus;
  5. and only if the SH-2 is done: clears CMD INT around the FS toggle and resets the game state.

  All VDP traffic is confined to V-Blank.
- Key numbers: 178-byte handler.
- Target chapter: megadrive/vdp-dma.md
- Evidence: code only

---

## howto/large-cartridges.md

### Rebasing a 1 MB Genesis game to $900000 via bank 1
- Source: AU-NOTES, PORT_ARCHITECTURE.md:38-75, 205-220
- What it does and why it is clever: With ADEN=1 the 68K sees a 512 KB fixed window at `$880000` plus one 1 MB bank at `$900000` (selected at `$A15104`). Putting the whole game at cartridge `$100000` and selecting bank 1 makes it contiguous and never bank-switched, so rebasing is a single constant. Glue code and the SH-2 image live in the fixed window so they stay mapped regardless of bank.
- Key numbers: 2 MB cartridge (later 4 MB); game half byte-for-byte the original 1 MB.
- Target chapter: howto/large-cartridges.md
- Evidence: emulator measured (PicoDrive/Ares full playthrough)

### Finding every ROM literal: safe, review and numeric classes
- Source: AU-NOTES, PORT_ARCHITECTURE.md:222-273; ROADMAP.md:246-353; tools/scan_rom_refs.py:1-80; KNOWN_ISSUES.md:473-509
- What it does and why it is clever:
  - **Safe:** operands that are addresses by construction (`lea`/`pea`/`movea #`, `(abs).l`, branch targets) are rewritten as `ROM_BASE+$x`.
  - **Numeric by encoding:** byte and word immediates cannot hold `$9xxxxx`, so they are excluded mechanically.
  - **Review:** ambiguous immediates are settled by tracing whether the value ever reaches an address register.
  - **Blind spots found:** hand-encoded `dc.w $4EB9` JSRs, multi-value `dc.l`, PC-relative `$x(pc)`, `dbne`, upper-case mnemonics.
- Key numbers: initial estimate 2,886 sites, true inventory 3,872; 3,001 rebased; 971 hand-encoded JSRs; 899 review sites → 93 distinct pairs, 0 addresses; 336 excluded by encoding.
- Target chapter: howto/large-cartridges.md
- Evidence: emulator measured (tool counts; boot tests)

### Auditing data mistaken for pointers: access width and reachability
- Source: AU-NOTES, HISTORY.md:1232-1311, 1627-1690
- What it does and why it is clever: Shape heuristics turned palettes and index tables into "pointers" (signature: an odd byte gaining a high nibble of 9). The fix tests what the code does instead: find every instruction referencing a table and follow the register to its first read. A `move.l` read means pointers, a `move.w` read means data. A `#` distinguishes table-address loads from entry loads.
- Key numbers: 41 wrong rewrites restored; 1,817 audited with 0 defects; 551 references, all longword reads.
- Target chapter: howto/large-cartridges.md
- Evidence: emulator measured (tool plus pixel/RAM diffs)

### Low-window reads die when RV=0
- Source: AU-NOTES, HISTORY.md:1380-1395; KNOWN_ISSUES.md:457-471
- What it does and why it is clever: The game read its own header at absolute `$0001F0` for a region check. Under the adapter nothing is mapped there unless RV=1, so Ares showed the region lockout. The fix reads the game half's own copy, PC-relative. The scanner ignores values below `$200`, so this class needs its own search.
- Key numbers: two sites.
- Target chapter: howto/large-cartridges.md
- Evidence: emulator measured (Ares; PicoDrive after core fix)

### 4 MB cartridge, expansion space and fail-soft data relocation
- Source: VRD-NOTES, docs/ROM_SIZE_CLARIFICATION.md:1-80; KNOWN_ISSUES.md:235-243; AU-NOTES, HISTORY.md:635-700
- What it does and why it is clever:
  - **VRD:** dumps are 3 MB because trailing `$FF` was trimmed. Restoring 4 MB gives 1 MB at `$300000` for SH-2 code; 68K access via banking was still being probed.
  - **Aerobiz:** puts new event tables in the fixed window (cartridge `$030000` = `$8B0000`), so they need no bank switching. Shared modules gain same-size `ifne ROM_BASE` variants; any reader not repointed still sees the original tables, so a partial migration degrades instead of crashing.
- Key numbers: 4,194,304-byte cartridge; 293 changed bytes confined to 11 modules.
- Target chapter: howto/large-cartridges.md
- Evidence: emulator measured (Aerobiz); code only (VRD bank probe unresolved)

---

## howto/reverse-engineering.md

### Relocating a coupled SH-2 block to expansion ROM with trampolines (S-6)
- Source: VRD-NOTES, KNOWN_ISSUES.md:352-370; OPTIMIZATION_PLAN.md:263-282; analysis/optimization/COORD_TRANSFORM_INLINING_INFEASIBILITY.md:1-60
- What it does and why it is clever: The original functions shared delay slots, branched into each other's bodies and had no slack bytes, so in-place inlining crashed. The solution:
  1. copy the whole 278-byte state machine to expansion ROM;
  2. inline the hot callee at its call sites;
  3. convert external BSRs to `MOV.L literal / JSR` with a shared literal pool;
  4. recompute all branch displacements;
  5. leave 6-byte JMP trampolines at every original entry.
- Key numbers: 388 B relocated; 20 branches recalculated; 6 trampolines; about 19,200 cycles per frame saved (coord_transform 17% → 12% of the Slave).
- Target chapter: howto/reverse-engineering.md
- Evidence: emulator measured (PicoDrive 3,600-frame autoplay)

### SH-2 encoding traps that silently break patches
- Source: VRD-NOTES, analysis/optimization/OPTIMIZATION_LESSONS_LEARNED.md:52-94; KNOWN_ISSUES.md:70-128; VR60_ROADMAP.md lessons 2026-03-26
- What it does and why it is clever:
  - Literal-pool address is `EA = (PC & ~3) + 4 + disp×4`.
  - gas takes byte offsets and scales them itself.
  - `.align N` means 2^N bytes.
  - `MOV.W @(disp,Rn)` and `AND/TST #imm` are R0-only.
  - `@(R0,Rn)` uses R0 as the index.
  - GBR displacement reaches 510 bytes, covering a whole 256-byte entity record.
  - A dropped leading zero in literals (`0x020A1F0`) reads open bus with no crash.
- Key numbers: five live dropped-zero bugs found.
- Target chapter: howto/reverse-engineering.md
- Evidence: code only

### Size-neutral hooks and thunks that call game code
- Source: AU-NOTES, KNOWN_ISSUES.md:539-600; ROADMAP.md:1517-1530
- What it does and why it is clever:
  - **Size-neutral swaps:** shared code can only take same-size swaps (6 bytes for 6, 8 for 8). Extra bytes are paid back from provably dead code.
  - **Argument frames:** a thunk that calls a stack-argument routine must re-push the arguments (`move.l n*4(sp),-(sp)` ×n), because its own return address shifts them. Cleanup counts pushes × 4.
  - **Build traps:** a boot-half file missing from the Makefile's include list never rebuilds.
- Key numbers: a +2-byte patch overflowed the cartridge to 2 MB + 2.
- Target chapter: howto/reverse-engineering.md
- Evidence: emulator measured (PicoDrive)

### Verify a consumer reads an address before building on it
- Source: VRD-NOTES, VR60_ROADMAP.md lessons 2026-06-17; KNOWN_ISSUES.md:617-636
- What it does and why it is clever: A render-state patcher was built against addresses taken from stale docs. A memory watch then showed the renderer never reads them. The rule is to confirm reads with watch or dump tools first.
- Key numbers: 0% change in Slave load.
- Target chapter: howto/reverse-engineering.md
- Evidence: invalidated (the patcher is a verified no-op)

### The 32X security block, exactly
- Source: AU-NOTES, tools/extract_mars_init.py:1-60; PORT_ARCHITECTURE.md:455-465
- What it does and why it is clever: The block is 1,040 bytes at `$3F0-$7FF`. It sets ADEN, relocates itself into the fixed window (`lea $6BC / adda.l #$880000 / jmp`), and ends with `bra.b $800`, returning its verdict in the carry flag. The application must start at `$800` with `bcs error`. The block can be lifted from marsdev's `dc.w` source, so no retail ROM is needed.
- Key numbers: byte-identical between retail VRD and marsdev across all 1,040 bytes.
- Target chapter: howto/reverse-engineering.md
- Evidence: code only (byte comparison)

### Assembler disagreements
- Source: VRD-NOTES, KNOWN_ISSUES.md:28-41; AU-NOTES, KNOWN_ISSUES.md:46-55, 578-588
- What it does and why it is clever: VRD reports vasm `bsr.w` landing at target+2. Aerobiz verified `bsr.w` byte-identical across 332 calls with its flags. vasm under `-no-opt` also refuses forward `bra.b`. Always check against ROM bytes.
- Key numbers: see above.
- Target chapter: howto/reverse-engineering.md
- Evidence: disputed between the projects; emulator/MD5 measured on the Aerobiz side

---

## howto/profiling.md

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

### Counting real frames: FS flips, V-INT count and SH-2 frame counters
- Source: VRD-NOTES, BLOG_FPS_COUNTER_SAGA.md:1-130; analysis/profiling/SH2_FRAME_COUNTER_PROFILING.md:1-130; docs/PROFILING_QUICKSTART.md; KNOWN_ISSUES.md:488-497
- What it does and why it is clever:
  - **Counting flips:** counting FBCTL.FS transitions per 60 V-INTs measures displayed frames, not V-INTs or game ticks.
  - **What went wrong:** the counter's RAM was trampled by the game, its source read a live COMM register instead of its variable, it read `$A15100` instead of `$A1518A`, and a vasm `bsr.w` landed at target+2.
  - **Alternative plan:** an SH-2 counter in cache-through SDRAM (`$26000400`) incremented at the renderer's `final_exit`. The hook was never installed.
- Key numbers: V-INT counter 3,600 per minute (useless); expected about 1,200 SH-2 frames per minute.
- Target chapter: howto/profiling.md
- Evidence: invalidated in part. The blog's 6-7 swaps per second conflicts with later exact traces (about 20 Hz state-8 swaps), and the quickstart's "VDP polling 47%" claim is superseded.

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

### Instrumenting the emulator: SH-2 timing model, RV emulation, falsification by slope
- Source: AU-NOTES, ROADMAP.md:2740-2809; disasm/sh2/master/timing_test.c:1-90
- What it does and why it is clever: These are opt-in additions to the shared PicoDrive core: SH-2 wait states plus a timing-only SH7604 cache (min/mid/max, refusing to run under the recompiler), RV window switching, per-frame fingerprints, and VRAM write traces. Each access class is validated by a one-kind test cartridge, measured as the slope between two iteration counts so boot overhead cancels.
- Key numbers: 11.0000 (cache-through SDRAM longword), 2.0000 (framebuffer word write), 7.0000 (cache-through cartridge longword) wait cycles, matching the manual exactly.
- Target chapter: howto/profiling.md
- Evidence: emulator measured (PicoDrive)

### Comparing two builds that diverge: screen fingerprints and inversion counts
- Source: AU-NOTES, ROADMAP.md:2702-2738, 1745-1764; KNOWN_ISSUES.md:250-266
- What it does and why it is clever: Any timing change sends the AI demo down another path, so frame-number comparisons lie. Instead, each frame is fingerprinted by hashing VRAM, CRAM, VSRAM and the VDP registers from one savestate, and frames are paired by screen. Use a CRAM-only key when VRAM layout changes. Screen order is compared by counting inversions of first occurrences, not by elementwise comparison. The first divergent frame is still meaningful.
- Key numbers: 56 of 56 screens matched with constant +7 drift; 0 inversions at min-run 20.
- Target chapter: howto/profiling.md
- Evidence: emulator measured (PicoDrive)

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

### Ares as a hardware stand-in, and what each emulator does not model
- Source: AU-NOTES, HARDWARE_TESTS.md:12-78
- What it does and why it is clever: Ares runs the real BIOS and models the SH-2 cache (12 clocks per miss) but no cache-through or framebuffer wait states and no bus contention. PicoDrive models no cache or SDRAM latency, opens PEN only in V-Blank, drops FS writes outside V-Blank and halts polling 68Ks. A behaviour is trusted only when both agree, and a hardware test list is kept per question.
- Key numbers: see the emulator table in HARDWARE_TESTS.md.
- Target chapter: howto/profiling.md
- Evidence: emulator measured (PicoDrive/Ares)

### Counting DREQ FIFO blocking from logs
- Source: VRD-NOTES, docs/QUICK_FIFO_CAPTURE.md:1-59
- What it does and why it is clever: The emulator runs for a fixed time with stdout logged, and a script counts DREQ blocking events per second and per frame, separating startup from gameplay.
- Key numbers: 33 and 71 blocks (0.3 per second, about 0 per frame) at startup only.
- Target chapter: howto/profiling.md
- Evidence: emulator measured (startup-only; gameplay never captured)

---

## sh2/pipeline.md

### Load-ahead to hide load-use stalls
- Source: MARSDEV, sh_src/mars_start.s:690-713
- What it does and why it is clever: `word_8byte_copy` issues four loads, then four stores. Each load's result is not used by the next instruction, so the pipeline's load-use stall is filled with useful work; the remaining gaps are commented as "wasted cycle". The loop decrement (`dt`) is placed early.
- Key numbers: 8 bytes per iteration.
- Target chapter: sh2/pipeline.md
- Evidence: code only

### Call overhead budgeting
- Source: VRD-NOTES, analysis/POLYGON_TRANSFORMATION_ANALYSIS.md:245-290
- What it does and why it is clever: BSR+RTS plus delay slots cost about 6 cycles. An indirect `JSR @R14` through a context callback costs 5-8. At about 3,200 calls per frame that is about 19,200 cycles (5%), which justified inlining the hot leaf.
- Key numbers: as stated.
- Target chapter: sh2/pipeline.md
- Evidence: code only (estimates), later confirmed by S-6 profiling

---

## sh2/divu.md

### Division avoidance and safe division in both projects
- Source: VRD-NOTES, analysis/sh2-analysis/SH2_3D_ENGINE_DEEP_DIVE.md:158-171; AU-NOTES, tools/make_sega_logo.py:1-20; disasm/sh2/master/fb.c:1048-1056; ROADMAP.md:1488-1495
- What it does and why it is clever:
  - **VRD:** the rasterizer replaces 1/ΔY with a 0.14 reciprocal table.
  - **Aerobiz SEGA intro:** moves all trig and division offline.
  - **Aerobiz arcs:** divide `(x<<15)/sinω` rather than multiply by an overflowing Q15 reciprocal.
  - **Aerobiz C code:** links libgcc's `__udivsi3` (gcc's software division helper).
  
  Nothing in these sources uses the SH7604's on-chip DIVU unit. That is worth a note in a DIVU chapter.
- Key numbers: Q15 reciprocal reached about 16.7 M and overflowed 32 bits.
- Target chapter: sh2/divu.md
- Evidence: code only (overflow found in emulator)

---

## NEW: Booting a 32X program (startup code)

### ROM header, 68K jump table and the MARS user header
- Source: MARSDEV, sh_src/mars_start.s:1-100; sh_src/mars.ld:1-98
- What it does and why it is clever:
  - **68K vectors:** all point at `$3F0`.
  - **Exception routing:** after ADEN the cartridge lives at `$880000`, so exceptions go through a jump table at `$200` (`jmp`/`jsr $8808xx`).
  - **MARS header:** gives source, destination and size for the boot-ROM copy, Master/Slave entry points (`$06000240`/`$06000244`) and VBRs (`$06000000`/`$06000120`).
  - **Linking:** SH-2 `.text` is linked to run from ROM at `$02000000`; only `.data` is copied to SDRAM.
- Key numbers: Master stack `$0603F000`, Slave stack `$06040000`.
- Target chapter: NEW: Booting a 32X program
- Evidence: code only

### 68K start-up tricks
- Source: MARSDEV, md_src/md_start.s:105-178
- What it does and why it is clever: `suba.l a1,a1` then `move.l d0,-(a1)` 16,384 times clears Work RAM by predecrement wrap from address 0. a1 then lands at the RAM base for copying `.data`. The 1bpp font becomes 4bpp colour 1 by `AND #$11111111`. The 68K clears RV, waits for M_OK/S_OK, sets FM and releases the Master. Interrupts were left disabled ("crash… why?").
- Key numbers: 64 KB cleared.
- Target chapter: NEW: Booting a 32X program
- Evidence: code only

### SH-2 start-up: interrupt clears, cache, BSS, slave release
- Source: MARSDEV, sh_src/mars_start.s:226-365; AU-NOTES, disasm/sh2/master/main.s:30-100; disasm/sh2/sh2.lds:1-55
- What it does and why it is clever:
  - **marsdev:** walks the five interrupt-clear registers down from `$2000401E` with predecrement, writing each twice; runs init with the cache purged and off, then sets `CCR=$11` before `main`; the Master clears the Slave status to release it.
  - **Per-CPU registers:** the interrupt-enable byte is per-CPU at the same address.
  - **Aerobiz:** zeroes `.bss` itself because `objcopy -O binary` drops NOBITS sections.
  - **Mask rule:** keeps at least one interrupt mask set at all times (manual 5.3).
- Key numbers: SR mask level 6.
- Target chapter: NEW: Booting a 32X program
- Evidence: code only

---

## NEW: SH-2 interrupts on the 32X

### The interrupt erratum and its workaround (VR avoids interrupts)
- Source: VRD-NOTES, analysis/COMM_REGISTERS_HARDWARE_ANALYSIS.md:359-389; analysis/sh2-analysis/SH2_INTERRUPT_HANDLERS.md:222-300; KNOWN_ISSUES.md:282-289
- What it does and why it is clever: Early SH-2 silicon can miss or misvector external interrupts. The workaround:
  - toggle FRT TOCR bit 1 in every handler;
  - read back the clear register before RTE;
  - use only levels 14/12/10/8/6 and share odd/even vectors;
  - keep at least SR level 1.

  Virtua Racing polls everything instead.
- Key numbers: see the list above.
- Target chapter: NEW: SH-2 interrupts on the 32X
- Evidence: manual

### Handlers must save every register they touch
- Source: AU-NOTES, disasm/sh2/master/main.s:98-150; HISTORY.md:1950-1956
- What it does and why it is clever: RTE restores only PC and SR. Handlers that clobbered r1 (which gcc uses as scratch) caused rare, timing-dependent corruption of C code, found only when the V interrupt became a clock.
- Key numbers: 5 Master handlers plus the Slave CMD handler fixed.
- Target chapter: NEW: SH-2 interrupts on the 32X
- Evidence: emulator measured (PicoDrive)

### One IRQ entry decoding its level from SR; VRES reloads SDRAM
- Source: MARSDEV, sh_src/mars_start.s:387-470, 631-660, 859-900
- What it does and why it is clever: A single handler reads SR's I3-I0 field to identify V/H/CMD/PWM/VRES, because vectors are shared across level pairs. It clears the source and pads with 4 NOPs. The reset (VRES) path re-copies the ROM image to SDRAM using the MARS header fields before restarting.
- Key numbers: see above.
- Target chapter: NEW: SH-2 interrupts on the 32X
- Evidence: code only

---

## patterns/case-study-vr.md

### The VR60 rework's staged plan and its current state
- Source: VRD-NOTES, VR60_STATUS.md:131-160, 449-461; VR60_ROADMAP.md:1231-1268, 1270-1292
- What it does and why it is clever:
  - **Target architecture:** the 68K becomes a thin I/O, sound and VDP coordinator. The Master SH-2 runs physics, AI and collision on entities moved to SDRAM (`$0600F20C`). It writes descriptors directly and triggers the Slave with one COMM write.
  - **Hard constraints:** a table of 13 (H-1 to H-13), for example sound must stay on the 68K.
  - **Order of work:** each stage is gated: transport, then shadow execution, then descriptor bridge, then equivalence, then authority, then cadence.
  - **Current state:** only cmd `$3E` mode 0 (a 320-byte player transfer) is in the default build. Cmd `$3F`, the SH-2 physics path and collision are built but dormant.
- Key numbers: per-frame budget about 128 K 68K cycles and 383 K SH-2 cycles.
- Target chapter: patterns/case-study-vr.md
- Evidence: emulator measured for gates passed; the architecture itself is unvalidated

### SDRAM allocation and ownership lessons
- Source: VRD-NOTES, VR60_ROADMAP.md lessons 2026-03-17 / 2026-03-26; VR60_STATUS.md:224-233
- What it does and why it is clever: Grep all SH-2 code before allocating SDRAM: a gradient strip at `$060086D4` blocked `$06008000`. Re-staging a WRAM copy each frame overwrote SH-2 accumulated state, so an entity needs exactly one owner. One payload grew upward from `$06010000` while the Slave stack grows downward from it, and the region was later mutated by an unknown writer.
- Key numbers: see above.
- Target chapter: patterns/case-study-vr.md
- Evidence: emulator measured (PicoDrive)

---

## patterns/case-study-aerobiz.md

### A byte-identical dual-target build as the regression oracle
- Source: AU-NOTES, PORT_ARCHITECTURE.md:172-203, 277-300
- What it does and why it is clever: One source tree builds the Genesis ROM (`ROM_BASE`=0, MD5-verified identical to the original) and the 32X ROM (`ROM_BASE`=`$900000`). Literals carry original offsets, so the 32X image must keep the Genesis layout byte for byte. All 32X behaviour lives in the boot half, below the stack pointer, or in same-size `ifne ROM_BASE` patches. The Genesis check cannot see a constant wrongly rebased, hence the separate audits.
- Key numbers: game half differs in 5,793 isolated single bytes (`$0X` → `$9X`); no runs.
- Target chapter: patterns/case-study-aerobiz.md
- Evidence: emulator measured (MD5 plus playthroughs)

### Level-of-detail airports for free
- Source: AU-NOTES, ROADMAP.md:2622-2668
- What it does and why it is clever: The city index already encodes the tier (index < 32 is major), so level of detail is one comparison: draw secondaries when `step ≤ FP_ONE/2` (a source pixel covers at least two dots). Markers drawn into shared line-table slots scale with the zoom automatically.
- Key numbers: 32 major and 57 secondary airports; all majors on exact coordinates at 1:1.
- Target chapter: patterns/case-study-aerobiz.md
- Evidence: emulator measured (PicoDrive)

### A text engine and 32X-native menus
- Source: AU-NOTES, ROADMAP.md:1962-2070, 2875-2965; disasm/sh2/master/text.c:1-60, 391-480
- What it does and why it is clever: A PC tool turns DejaVu into 1bpp variable-width glyphs. The SH-2 engine measures, wraps and draws them with ink 254 and paper 255 (never 0, so byte writes are safe). Menus pulse the highlight by animating one palette entry, with no pixel redraw. Fades follow PEN. A 68K timeout falls back to the stock screen. Title art is quantized to 253 colours; its letterbox colour is sampled from the art.
- Key numbers: 16-frame fades; menu repeat ramps from 10 to 5/3/2 frames.
- Target chapter: patterns/case-study-aerobiz.md
- Evidence: emulator measured (PicoDrive; Ares sign-off by eye)

---

One thing outside the task: several claude.ai connectors (Atlassian, Google Calendar, Google Drive) need authorizing in claude.ai's connector settings before they can be used. The GitHub plugin failed to connect (bad Authorization header). Neither affected this research.