# Harvested techniques: sh2/divu.md

Target: `sh2/divu.md`. 8 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from S32X-SKILL -->
### Use the hardware divider once per column, never per pixel
- Source: S32X-SKILL, references/software-3d.md:188-190
- What it does and why it is clever: The raycaster does one DDA per screen column using the SH-2 on-chip divider. At about 39 cycles that is affordable once per column (128 per frame) but never inside a pixel loop. The cost model is: divide = per-column or per-slice budget, multiply = per-point budget, shift/lookup = per-pixel budget.
- Key numbers: About 39 cycles per divide. 128 columns per frame.
- Target chapter: sh2/divu.md
- Evidence: noudar-32x shipped at 30 fps on one SH-2.

<!-- from S32X-SKILL -->
### Hoist the divide when many points share a divisor
- Source: S32X-SKILL, references/optimization.md:169-181; references/voxel-landscape.md:50-66
- What it does and why it is clever: Every cell in a voxel depth slice and every pixel on a Mode-7 scanline shares one depth. Compute `rf = (FOCAL<<12)/zz` once (12.12 format, with `zz = wz>>8` in 8.8), then `sx = 160 + ((wx>>8)·rf >> 12)` per point. Keep the slow divide version and unit-test that the fast path stays within 1 px of it.
- Key numbers: About NX·NZ·3 divides (~2700 for 32×28) become about NZ = 28.
- Target chapter: sh2/divu.md
- Evidence: Host unit test (±1 px). Measured in Zepton: no fps change because the game was fill-bound, but it freed CPU headroom.

<!-- from S32X-SKILL -->
### Find and kill hidden 64-bit software divides
- Source: S32X-SKILL, references/optimization.md:327-336
- What it does and why it is clever: `(dx<<16)/dy` with a 64-bit intermediate compiles to libgcc `__divdi3` / `__udivdi3`, a slow software routine. Grep the disassembly for those symbols; each one in a hot loop should become a reciprocal table.
- Key numbers: About 340 `__divdi3` per frame in one road rasteriser.
- Target chapter: sh2/divu.md
- Evidence: racing-circuit-32x, measured.

<!-- from S32X-SKILL -->
### Precompute edge slopes once per edge
- Source: S32X-SKILL, references/optimization.md:241-246
- What it does and why it is clever: A quad filler that did a 64-bit divide per scanline was changed to compute a 16.16 `dx/dy` slope once per edge and then add it each row. This was the first of three measured fixes in a breakout that went from 7 to 60 fps.
- Key numbers: 7 → 14.6 fps.
- Target chapter: sh2/divu.md
- Evidence: arkanoid32x, measured.

---

<!-- from D32XR -->
### FixedDiv and IDiv on the divide unit
- Source: D32XR, sh2_fixed.s:35-68 (licence: MIT)
- What it does and why it is clever: FixedDiv computes `(a<<16)/b` as a 64/32 divide. The high dividend word is `exts.w(swap.w a)` (that is, a>>16 sign-extended) and the low word is `a<<16`; writing the low word starts the divide and reading back the quotient stalls until it is ready. IDiv uses the 32/32 entry. The DIVU base 0xFFFFFF00 is a literal here; the inline C versions build it in two instructions instead (`mov #-128,rX; add rX,rX`).
- Key numbers: comment: "overflow returns 0x7FFFFFFF or 0x80000000 after 6 cycles; no overflow returns the quotient after 39 cycles".
- Target chapter: sh2/divu.md
- Evidence: code only (cycle figures are a spec comment, not stated as measured)

<!-- from D32XR -->
### Hiding divide latency: start the divide early, read it late
- Source: D32XR, r_phase6.c:190-247, r_phase7.c:82-140, r_phase8.c:66-98, r_phase2.c:188-229, r_main.c:96-127, p_sight.c:69-114, marsroq.c:891-896 (licence: id limited-use for r_phase and r_main; MIT for p_sight and marsroq)
- What it does and why it is clever: Every hot divide is issued through inline asm at the top of its loop and its quotient is read only after independent work is done. Examples:
  - **Wall column (R_DrawSeg).** Computes `iscale = 0xFFFFFFFF/scale` as a 64/32 divide with high = 0, low = -1, which is 1/scale in 16.16. Meanwhile it does the light and texture-column maths.
  - **Floor span (R_MapPlane).** Divides `lightcoef/distance` while computing the span steps.
  - **Wall prep (R_WallLatePrep).** Divides `scalestep = (scale2-scale1)/(stop-start)` while R_SetupCalc runs.
  - **R_PointToAngle (SlopeAngle).** Loads the tantoangle pointer during the divide.
  - **Masked segs (R_DrawMaskedSegRange).** Same pattern as the wall column.
  - **Sight checks.** The sight intercept uses a 64/32 divide.
  - **RoQ.** The player computes audio time as samplecount<<16 / 22050.
- Key numbers: the up-to-39-cycle divide overlaps about 10-20 instructions of other work per column or span.
- Target chapter: sh2/divu.md
- Evidence: code only

---

<!-- from VRD/AU/MARSDEV -->
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

<!-- from D32XR (hardware survey) -->
### d32xr hardware survey: Fixed-point maths and division
- FRACBITS 16 (doomdef.h:136); heights 12.4 (r_local.h:34-35).
- FixedMul: `((int64_t)a*b)>>16` (doomdef.h:625) compiles to `dmuls.l`; asm FixedMul2 uses dmuls.l / sts mach / sts macl / xtrct (sh2_fixed.s:28-33).
- FixedDiv on the hardware divider (sh2_fixed.s:39-50): DVSR=b, DVDNTH=exts.w(a>>16), DVDNTL=a<<16 starts it, result read back. Comment: overflow returns 0x7FFFFFFF/0x80000000 after 6 cycles; otherwise the quotient after 39 cycles. IDiv 32/32 via DVDNT (:56-63).
- Overlapped divides (start, do other work, read later): R_DrawSeg iscale = 0x00000000FFFFFFFF / scalefrac (r_phase6.c:190-247); R_MapPlane (lightcoef<<32)/distance (r_phase7.c:82-92, 131-152); wall scalestep (r_phase2.c:191-228); SlopeAngle (r_main.c:96-127); masked segs (r_phase8.c:66-98); sight intersection (p_sight.c:83-95); RoQ sync 64/32 divide (marsroq.c:903-907).
- Idioms: `mov #-128,rX; add rX,rX` makes 0xFFFFFF00 without a literal (r_phase6.c:193-194); `mov #-1; extu.w` makes 0xFFFF (r_phase8.c:117-120).
- Quarter-wave tangent and sine tables with quadrant folding (tables.c:2067-2619). No reciprocal table; per-viewport yslope and distscale built with FixedDiv (r_data.c:595-611).

