# Harvested techniques: Fixed-point maths and fast division

Target: Part VI chapter in `src/techniques/` (or `src/howto/emulator-testing.md`). 19 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from S32X-SKILL -->
### 16.16 fixed point with a 64-bit-intermediate multiply
- Source: S32X-SKILL, assets/3d/r3d.h:7-10; references/software-3d.md:15-19; references/optimization.md:37-39
- What it does and why it is clever: All world coordinates, the camera and velocities are `int` in 16.16 format: `FX(n) = n·65536`, `fmul(a,b) = ((int64)a·b) >> 16`. Screen coordinates are plain ints. The core has no floats at all, so the desktop build and the SH-2 build compute bit-identical results, which is what makes desktop-vs-ROM replay tests possible.
- Key numbers: FX_ONE = 65536. Range ±32768 units, resolution 1/65536.
- Target chapter: NEW: Fixed-point maths
- Evidence: Used in two shipped games (a rally racer and a rail shooter) built on r3d; host-tested.

<!-- from S32X-SKILL -->
### 256-entry build-time sine table, cos as a phase offset
- Source: S32X-SKILL, assets/3d/gen_tables.py:1-14; assets/3d/r3d.c:6-7
- What it does and why it is clever: Angles are "brads" (binary angles, 0..255 = one full turn). A Python script writes `sintab[i] = round(sin(2πi/256)·65536)` as a C `.inc` that lands in ROM. `cos(a) = sintab[(a+64)&255]`, and the `&255` gives free wraparound. There is no runtime float and no second table.
- Key numbers: 256 × 4 bytes = 1 KiB of ROM. 1 brad = 1.406°.
- Target chapter: NEW: Fixed-point maths
- Evidence: Shipped engine asset.

<!-- from S32X-SKILL -->
### Reciprocal lookup table replaces the perspective divide
- Source: S32X-SKILL, assets/3d/gen_tables.py:16-32; assets/3d/r3d.c:53-66; references/optimization.md:98-113; references/software-3d.md:39-44
- What it does and why it is clever: Stores `recip[k] = 2^22 / k` with key `k = z_16.16 >> 12`, so `recip[k] ≈ 2^34 / z`. Projection then becomes `sx = W/2 + (x·focal·recip[k]) >> 34`, i.e. multiply and shift with no divide. The general rule: any `a/b` where `b` stays in a bounded range can be turned into a table keyed on `b`.
- Key numbers: 4096 entries × 4 bytes = 16 KiB of ROM, RECIP_SH = 22. Covers z up to 256 units. About 1 px error versus a true divide (much worse very close to the camera; see problem 8). Entry 0 holds 0.
- Target chapter: NEW: Fixed-point maths
- Evidence: Host-checked against the exact divide ("worst error ~1px"). Shipped engine.

<!-- from S32X-SKILL -->
### Fold constant factors into the reciprocal table
- Source: S32X-SKILL, references/optimization.md:327-336
- What it does and why it is clever: Pre-multiply `focal` into the table, `rtab[k] = focal·2^S/k`. A three-factor 64-bit product `x·focal·recip` becomes a single 32×32 multiply. The table is rebuilt only when the folded constant changes (for example an FOV change). A 1-4 K-entry `fx_div_small` table handles per-scanline and per-point divides.
- Key numbers: 1-4 K entries. One racer was doing about 340 `__divdi3` calls per frame before this.
- Target chapter: NEW: Fixed-point maths
- Evidence: Measured as part of a 12→30 fps optimisation log (racing-circuit-32x).

<!-- from S32X-SKILL -->
### Interpolated 16.16 atan2 sized to its consumer
- Source: S32X-SKILL, references/testing.md:465-474
- What it does and why it is clever: A whole-brad atan2 (1.4° steps) is fine for gameplay headings. Used for camera pitch it is not: one brad moves the horizon 4-5 scanlines (focal·tan 1.4° ≈ 0.0245·focal, about 4.4 lines at focal ≈ 180). A 257-entry table with linear interpolation (the extra entry closes the interval) returns 16.16 brads. Size table precision to what the consumer can see on screen.
- Key numbers: 257 entries. Worst-case error drops from 0.99 to 0.0002 brads. Zero horizon jumps over 3000 frames.
- Target chapter: NEW: Fixed-point maths
- Evidence: racing-circuit-32x, measured over 3000 frames.

<!-- from S32X-SKILL -->
### 32-bit `long` overflow in distance and area code
- Source: S32X-SKILL, references/architecture.md:162-170; references/voxel-landscape.md:46-48
- What it does and why it is clever: On the SH-2, `int` and `long` are both 32 bits, so `dx·dx + dz·dz` on 16.16 values silently wraps. On x86-64 `long` is 64 bits, so the same code passes host tests and fails only on hardware. Use `long long` for such intermediates, and grep for `long ` when moving host-tested code over. Voxel example: `frac·CELLZ` (65535 × 98304) overflows; compute `((long long)frac·CELLZ) >> 16`.
- Key numbers: frac ≤ 65535, CELLZ ≈ 98304, product ≈ 6.4e9 > 2^31.
- Target chapter: NEW: Fixed-point maths
- Evidence: Real bug class seen in ports (described).

<!-- from S32X-SKILL -->
### Shifts and masks instead of `* / %`
- Source: S32X-SKILL, references/optimization.md:32-35, 60-62
- What it does and why it is clever: Replace `x/64` with `x>>6`, `x%64` with `x&63`, `x*8` with `x<<3`. A non-power-of-two constant divide becomes a fixed-point reciprocal multiply plus shift. Default locals to `int`, because 8- and 16-bit arithmetic adds masking instructions on the SH-2.
- Key numbers: —
- Target chapter: NEW: Fixed-point maths
- Evidence: Described as a d32xr idiom.

<!-- from S32X-SKILL -->
### Bake transcendentals into ROM tables at build time
- Source: S32X-SKILL, references/optimization.md:342-344, 292-295
- What it does and why it is clever: AI corner-speed logic was calling atan2 twice and hypot twice for each of 14 lookahead points per car, every frame. These were precomputed into a ROM table, along with track centreline tangents and normals. Sprite row/scale tables and sin/atan2 tables follow the same pattern.
- Key numbers: About 750 transcendental calls per frame removed.
- Target chapter: NEW: Fixed-point maths
- Evidence: Measured in the 12→30 fps racer log.

---

<!-- from D32XR -->
### Angles as 32-bit binary fractions of a turn, and fine-angle indices
- Source: D32XR, doomdef.h:136-171, r_local.h:24-35, 353-355 (licence: id limited-use)
- What it does and why it is clever:
  - **Angles.** `angle_t` is unsigned 32-bit with 2^32 = 360° (ANG90 = 0x40000000), so wraparound is free and differences are just subtraction.
  - **Fine angles.** Tables are indexed by `angle >> 19`, giving 8192 fine angles; FIELDOFVIEW = 2048 fine angles (90°); the sky uses `>>22`.
  - **Other formats.** Coordinates are 16.16 `fixed_t`. Wall heights in viswalls are 12.4 int16 (HEIGHTFRACBITS 4). Map vertices and nodes are int16 whole units.
- Key numbers: FINEANGLES 8192; SLOPERANGE 2048 (11 bits); DBITS 5.
- Target chapter: NEW: Fixed-point maths
- Evidence: code only

<!-- from D32XR -->
### Quarter-wave sine and half-period tangent tables
- Source: D32XR, tables.c:2067-2587 (data), 2589-2625 (accessors) (licence: id limited-use)
- What it does and why it is clever: Only sin over [0°, 90°) is stored, as 2048 unsigned 16-bit values (1.0 ≈ 65535). `finesine` takes the quadrant q = angle/2048 and looks up a pointer offset `{0, +4096, -4096, +8192}` words. For odd quadrants it indexes with `~angle`, which equals `-angle-1` and mirrors the quarter, and it negates for q ≥ 2. One table read with no branchy symmetry code. `finetangent` stores 2048 entries and uses `tan(θ) = -tan(π-θ)` through `~angle`.
- Key numbers: sine 4 KB instead of 40 KB (10240 x 4 bytes); tangent 8 KB instead of 16 KB; tantoangle 2049 entries.
- Target chapter: NEW: Fixed-point maths
- Evidence: code only

<!-- from D32XR -->
### R_PointToAngle by octant folding and an arctangent table
- Source: D32XR, r_main.c:96-197 (licence: id limited-use)
- What it does and why it is clever: The vector is folded into the first octant (0 ≤ y ≤ x) while recording a base angle and a sign n per octant. The result is `base + n·tantoangle[min(2048, (num<<3)/(den>>8))]`; the quotient is the slope scaled to 11 bits, from the hardware divider. A denominator below 2 short-circuits to the 45° entry.
- Key numbers: 8 octants; one 32/32 divide.
- Target chapter: NEW: Fixed-point maths
- Evidence: code only

<!-- from D32XR -->
### Distance without square roots, and an integer square root where needed
- Source: D32XR, r_phase2.c:23-42, 92-128; p_maputl.c:29-36 (licence: id limited-use)
- What it does and why it is clever:
  - **R_PointToDist.** Order the axes so dy ≤ dx, look up θ = atan(dy/dx), return `dx / cos θ`: one divide each way, no sqrt.
  - **P_AproxDistance.** `dx+dy - min/2`, an octagonal norm.
  - **P_SegOffset.** Because segs no longer store their offset along the line, it uses a 16-step bitwise square root: try each bit from 0x8000 down and keep it if g² ≤ n.
- Key numbers: isqrt = 16 iterations.
- Target chapter: NEW: Fixed-point maths
- Evidence: code only

---

<!-- from VRD/AU/MARSDEV -->
### Binary-angle quarter-wave sine with quadrant jump table (68K)
- Source: VRD-NOTES, disasm/modules/68k/game/physics/sine_cosine_quadrant_lookup.asm:1-30; analysis/PHYSICS_SYSTEM_ARCHITECTURE.md:165, 253
- What it does and why it is clever: Angles are 16-bit binary angle measurement (BAM) units, `$0000-$FFFF` = 360°, so wraparound is free. Cosine is the sine entry point preceded by `ADDI #$4000`, falling straight through. The top two bits select one of four quadrant handlers through a jump table, so a single quarter table serves all four quadrants.
- Key numbers: 58 B routine; trig table at 68K $930000.
- Target chapter: NEW: Fixed-point maths
- Evidence: code only

<!-- from VRD/AU/MARSDEV -->
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

<!-- from VRD/AU/MARSDEV -->
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

<!-- from VRD/AU/MARSDEV -->
### Divide-by-constant as multiply-shift
- Source: VRD-NOTES, analysis/MASTER_FUNCTION_REFERENCE.md:3656; OPTIMIZATION_PLAN.md:466-470
- What it does and why it is clever: The speed smoothing divides by roughly 102 using `(x·644)>>16`, since 65536/644 ≈ 101.8, replacing a roughly 140-cycle 68000 `DIVS`. QW-5 lists replacing `DIVS #103` this way.
- Key numbers: about 960 cycles per frame saved (estimate).
- Target chapter: NEW: Fixed-point maths
- Evidence: code only

<!-- from VRD/AU/MARSDEV -->
### Packed RGB555 channel arithmetic
- Source: AU-NOTES, disasm/sh2/master/text.c:341-358; MARSDEV, sh_src/mars_start.s:813-858
- What it does and why it is clever: `darken555(v) = (v>>1) & HALF555` halves all three channels in one shift by masking off bits that would leak between channels. `lerp555` does a per-channel `(a·(n−t)+b·t)/n` for 16-step fades. marsdev's `0x7BDE` mask does the same for two-pixel averages.
- Key numbers: fade length MENU_FADE = 16 steps.
- Target chapter: NEW: Fixed-point maths
- Evidence: code only

<!-- from VRD/AU/MARSDEV -->
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

<!-- from D32XR (hardware survey) -->
### d32xr hardware survey: Fixed-point maths and division
- FRACBITS 16 (doomdef.h:136); heights 12.4 (r_local.h:34-35).
- FixedMul: `((int64_t)a*b)>>16` (doomdef.h:625) compiles to `dmuls.l`; asm FixedMul2 uses dmuls.l / sts mach / sts macl / xtrct (sh2_fixed.s:28-33).
- FixedDiv on the hardware divider (sh2_fixed.s:39-50): DVSR=b, DVDNTH=exts.w(a>>16), DVDNTL=a<<16 starts it, result read back. Comment: overflow returns 0x7FFFFFFF/0x80000000 after 6 cycles; otherwise the quotient after 39 cycles. IDiv 32/32 via DVDNT (:56-63).
- Overlapped divides (start, do other work, read later): R_DrawSeg iscale = 0x00000000FFFFFFFF / scalefrac (r_phase6.c:190-247); R_MapPlane (lightcoef<<32)/distance (r_phase7.c:82-92, 131-152); wall scalestep (r_phase2.c:191-228); SlopeAngle (r_main.c:96-127); masked segs (r_phase8.c:66-98); sight intersection (p_sight.c:83-95); RoQ sync 64/32 divide (marsroq.c:903-907).
- Idioms: `mov #-128,rX; add rX,rX` makes 0xFFFFFF00 without a literal (r_phase6.c:193-194); `mov #-1; extu.w` makes 0xFFFF (r_phase8.c:117-120).
- Quarter-wave tangent and sine tables with quadrant folding (tables.c:2067-2619). No reciprocal table; per-viewport yslope and distscale built with FixedDiv (r_data.c:595-611).

