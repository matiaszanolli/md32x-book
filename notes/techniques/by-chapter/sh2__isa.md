# Harvested techniques: sh2/isa.md

Target: `sh2/isa.md`. 2 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from D32XR -->
### FixedMul with dmuls.l and xtrct
- Source: D32XR, sh2_fixed.s:23-33, doomdef.h:625 (licence: MIT for sh2_fixed.s; id limited-use for doomdef.h)
- What it does and why it is clever: A 16.16 x 16.16 product needs the middle 32 bits of the 64-bit result. `dmuls.l` produces MACH:MACL and `xtrct mach,macl` pulls out bits 47..16 in one instruction (in the rts delay slot). C code mostly uses `((int64_t)a*b)>>16` and lets GCC emit the same thing. P_ApplyFriction switched from the Jaguar's `(x>>8)*(f>>8)` to FixedMul because arithmetic `>>8` is costly on the SH-2.
- Key numbers: 5 instructions including rts.
- Target chapter: sh2/isa.md
- Evidence: code only (p_base.c:56-64 explains "much slower on the SH-2")

<!-- from D32XR -->
### SH-2 micro-idioms used throughout
- Source: D32XR, r_local.h:280-311, r_data.c:901-915, sh2_draw.s:34-42, r_phase8.c:117-121, p_sight.c:303-319, r_phase1.c:605-621, roq_read.c:189-190, marssound.c:1150-1158 (licence: mixed; id limited-use except p_sight.c, which is MIT)
- What it does and why it is clever:
  - **Biased colormaps.** `mov.b` sign-extends, so texels are fetched as signed bytes and every colormap base is biased +128 (+256 for the 16-bit low-res maps). The signed index needs no `extu.b`. RoQ does the same with `cells = cells_u + 128`, and sector compares cast to `int8_t` "to get rid of the extu.w".
  - **Integer part without an arithmetic shift.** Compute `(unsigned)dx >> 16` (one `shlr16`), then `muls.w`, which only reads the low 16 bits as signed. The sign comes back for free.
  - **Cheap constants.** 0xFFFF = `mov #-1; extu.w`; 0x10000 = `mov #1; shll16`; 0xFFFFFF00 = `mov #-128; add r,r`. Constants are pinned in registers with `asm("mov")` so GCC does not reload them.
  - **Cheap address and leaf tests.** `y*320` = `shll8` plus `shlr2` and two adds. A BSP leaf test is `(int16_t)n < 0` instead of `& 0x8000`.
  - **1<<k without a barrel shifter.** `braf` jumps into a chain of seven `shll`, so k costs at most 7 single shifts (reject matrix).
  - **>>16 for free.** `swap.w` gives frac>>16 in every texture loop.
- Key numbers: n/a.
- Target chapter: sh2/isa.md
- Evidence: code only

---

