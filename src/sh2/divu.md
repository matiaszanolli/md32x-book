# Division unit

The SH-2's instruction set has no divide instruction, only `div1`, which produces one bit of a quotient per step. Each SH-2 therefore has a small on-chip division unit (DIVU) that does a signed 32/32 or 64/32 divide in 39 clocks, in parallel with the CPU. This chapter covers its registers, how to start a divide and collect the result, overflow, how to hide its latency, and how shipped 32X code uses it.

## Registers

| Register | Address | Holds |
|----------|---------|-------|
| DVSR | `0xFFFFFF00` | Divisor |
| DVDNT | `0xFFFFFF04` | 32-bit dividend. Writing it starts a 32/32 divide; the quotient replaces it |
| DVCR | `0xFFFFFF08` | Bit 1 OVFIE: interrupt on overflow. Bit 0 OVF: overflow happened (stays set until you clear it) |
| VCRDIV | `0xFFFFFF0C` | Vector number of the overflow interrupt (bits 6-0) |
| DVDNTH | `0xFFFFFF10` | High half of a 64-bit dividend; the remainder afterwards |
| DVDNTL | `0xFFFFFF14` | Low half of a 64-bit dividend. Writing it starts a 64/32 divide; the quotient replaces it |

Source: [SH7604 §10.1.3, §10.2]. Access every register as a longword, except DVCR and VCRDIV, which also accept words. Word accesses to the others read or write garbage [SH7604 §10.4.1]. Each SH-2 has its own unit.

### Two registers the manual leaves out

The manual's list stops at DVDNTL, but the unit answers at two more addresses, and the block of eight longwords repeats at `0xFFFFFF20`-`0xFFFFFF3F` <span class="tag disputed">disputed</span> [[discrepancy 45](../appendices/discrepancies.md)]:

| Address | Behaves as |
|---------|------------|
| `0xFFFFFF18` | A register of its own that every divide loads with the remainder, the same value it puts in DVDNTH |
| `0xFFFFFF1C` | A register of its own that every divide loads with the quotient, the same value it puts in DVDNTL |

The evidence:

- **A Saturn test.** YabauseUT writes a value to each address and reads it back, then expects the quotient and remainder at both addresses after a 32/32 and a 64/32 divide. It also reads all four result registers through the copy at `0xFFFFFF20`-`0xFFFFFF3F` [YABAUSE, yabauseut/src/sh2.c].
- **Two emulators that follow it.** Mednafen and Yabause treat both as separate registers. A divide fills them, but writing DVDNTH or DVDNTL doesn't change them, and writing them starts nothing [MEDNAFEN, ss/sh7095.inc; YABAUSE, yabause/src/sh2core.c].
- **Sega's own code.** The *Runlength Mode Test* sample starts a 64/32 divide for each polygon edge's slope, calls two routines while it runs, and reads the slope from `0xFFFFFF1C` [RLT, SH-2 code at `0x0603066C`-`0x060306B2`]. The VRD project's copy of Virtua Racing Deluxe does the same in six routines, five 64/32 divides and one 32/32 [VRD-NOTES, SH-2 code at `0x06002398`-`0x060037CA`]. None of the clean retail games read for this book (SWA, MK2, AB32X, CHAOTIX, MCX) touches either address.

Read the documented DVDNT and DVDNTL in new code. An emulator has to keep the copies, though, because Sega code depends on them.

## Doing a divide

**32 by 32** [SH7604 §10.3.2]:

1. Write the divisor to DVSR.
2. Write the dividend to DVDNT. This starts the divide. The unit also copies the dividend into DVDNTL and fills DVDNTH with copies of its sign bit.
3. Read the quotient from DVDNT. The remainder is in DVDNTH.

**64 by 32** [SH7604 §10.3.1]:

1. Write the divisor to DVSR.
2. Write the high half of the dividend to DVDNTH.
3. Write the low half to DVDNTL. This starts the divide.
4. Read the quotient from DVDNTL. The remainder is in DVDNTH.

**Both are signed.** Operands and results are two's-complement. For an unsigned 32-bit dividend that may have its top bit set, use the 64/32 form with a high half of 0. The unit then sees a positive 64-bit number [SH7604 §10.3]. d32xr computes 1/*x* in 16.16 fixed point this way: it divides `0x00000000_FFFFFFFF` by *x* [D32XR, r_phase6.c].

**A 16.16 fixed-point divide** of *a* by *b* is a 64/32 divide of *a* shifted left 16. The high half is *a* shifted right 16, keeping the sign, and the low half is *a* shifted left 16. d32xr's `FixedDiv` does exactly this, and its `IDiv` is the plain 32/32 form [D32XR, sh2_fixed.s].

## Timing

A divide takes 39 clocks from the write that starts it. An overflow ends it after 6 [SH7604 §10.3.1, §10.3.2]. While the unit is busy, any read or write of a DIVU register waits until it finishes, but instructions that do not touch the unit carry on as normal. The DIVU sits on the SH-2's internal bus, so a divide in progress does not use the external bus either [SH7604 §10.4.1, §7.11.2].

So there are two ways to use it:

- **Start and read at once.** The read simply waits, and the divide costs up to 39 clocks. A `div1` loop needs 32 steps plus bookkeeping for a 32-bit quotient.
- **Start early and read late.** Put up to 39 clocks of independent work between the start and the read, and the divide costs almost nothing. Hitachi recommends this [SH7604 §10.4.1]. d32xr does it in every hot loop. Its wall-drawing code starts the 1/*x* divide at the top of each column, works out the column's light level and texture column, and only then reads the quotient. Floor spans, wall preparation, angle calculation, sprite clipping and line-of-sight checks follow the same pattern [D32XR, r_phase6.c, r_phase7.c, r_phase2.c, r_main.c, r_phase8.c, p_sight.c].

Two rules from Hitachi's notes [SH7604 §10.4.1] <span class="tag manual">manual</span>:

- **The instruction right after the one that starts a divide must not write a DIVU register.** The starting write may not have taken effect yet.
- **A read straight after any DIVU write takes an extra clock,** even of the same register.

## Overflow and division by zero

A divide overflows when the quotient does not fit in a signed 32-bit number, or when the divisor is 0 [SH7604 §10.3.3]. Then:

- OVF is set, and stays set until you clear it.
- The unit stops after 6 clocks: three to set the flag, then three steps of the division. DVDNTH keeps the partial remainder those three steps leave [SH7604 §10.3.3].
- If the overflow interrupt is off, the quotient register holds `$7FFFFFFF` if the true quotient was positive, or `$80000000` if it was negative.
- If the overflow interrupt is on (OVFIE = 1), both dividend registers keep the partial result and the interrupt is raised. Its priority is set in IPRA bits 15-12 and its vector in VCRDIV [SH7604 §10.4.2, Table 10.2; §5.3.1].

The manual also counts one quotient inside the range as an overflow: a negative number divided by a negative number, when the quotient comes out at `$7FFFFFFF` and a remainder is left over [SH7604 §10.3.3]. For a 32/32 divide the only quotient out of range is `$80000000` ÷ −1, and a Saturn test notes that it could only cause an overflow with a 64/32 divide (below).

### Divide by zero

The manual does not say which of the two limits a zero divisor gives. A test program run on a Saturn, which uses the same CPU [32X-TB27], answers it. YabauseUT, the hardware test suite of the Yabause emulator, expects these results [YABAUSE, yabauseut/src/sh2.c]:

| Divide | Quotient (DVDNT, DVDNTL) | DVDNTH | OVF |
|--------|--------------------------|--------|-----|
| 32/32: 0 ÷ 0 | `$7FFFFFFF` | `$00000000` | 1 |
| 32/32: `$D0000000` ÷ 0 | `$80000000` | `$FFFFFFFE` | 1 |
| 64/32: `$00000001_00000000` ÷ 1 (overflow, not zero) | `$7FFFFFFF` | `$FFFFFFFE` | 1 |

A third test raises the overflow interrupt by dividing `$D0000000` by 0 with OVFIE set. So a zero divisor gives the limit with the dividend's sign: `$7FFFFFFF` for a dividend of 0 or more, `$80000000` for a negative one. DVDNTH holds what three division steps leave. With a zero divisor, each step only shifts, so for a 32/32 divide that is the dividend shifted right 29 places with its sign copied in: `$D0000000` gives `$FFFFFFFE`. Mednafen and Yabause, two Saturn emulators whose authors test on the console, give all three results, and MAME has given the divide-by-zero ones since September 2026 <span class="tag disputed">disputed</span> [MEDNAFEN, ss/sh7095.inc; YABAUSE, yabause/src/sh2core.c; MAME, sh7604.cpp; [discrepancy 21](../appendices/discrepancies.md)]. PicoDrive and Ares give other values ([In emulators](#in-emulators)), and nobody has run the test on a 32X. Code that might divide by zero should test the divisor first, and then it behaves the same everywhere.

## Interrupts and the divider

There is one unit per CPU, and it has no way to save a divide in progress. If an interrupt handler divides while the interrupted code has a divide in flight, it replaces the operands, and the interrupted code reads the handler's result. With the start-early, read-late pattern, that window is the whole stretch between start and read. Keep divides out of interrupt handlers, or mask interrupts from the start of each divide to its read.

## What shipped code does

- **Star Wars Arcade** uses the divider mainly to build tables at start-up [SWA, SH-2 code at `0x06000EFE`, `0x06002BE8`]:
  - 8,192 words of `$8000 / n`.
  - 2,048 longwords of *k* × 2<sup>16</sup> / *n*, for a value *k* passed in.

  Each entry is a 32/32 divide read back after one `nop`. At run time one routine divides directly, after making both operands positive. Elsewhere the program uses `div1` loops (67 `div1` instructions in its resident code) [SWA, SH-2 code at `0x060015E0`].
- **d32xr** divides in hot loops, always with the start-early, read-late pattern described above [D32XR, sh2_fixed.s, r_phase6.c].
- **Aerobiz Ultimate's** C code uses gcc's software division routine instead of the unit, and moves its heavier trigonometry and division offline [AU-NOTES, ROADMAP.md, tools/make_sega_logo.py].
- **Mortal Kombat II** never uses the unit. Its two divides are the classic 16-step `DIV1` sequence for a 16-bit quotient: shift the divisor up 16 bits, `DIV0U`, sixteen `DIV1`s, then `ROTCL` and `EXTU.W` to collect the result. That is about 20 clocks plus the call, with no set-up, against the unit's 39 when there is nothing to overlap it with [MK2, SH-2 code at `0x0600114C`, `0x060015D2`].
- **After Burner Complete** uses the same unrolled 16-step `DIV1` sequence for its perspective divide, `$7FE0` / (*z* / 32 + 32), once for each object it projects, inside the CMD interrupt that receives the object [AB32X, SH-2 code at `0x060025A0`-`0x060025CC`].

### Avoiding divides altogether

A divide per pixel is never affordable. A divide per column, per scanline or per polygon edge usually is. The S32X-SKILL notes give the budget plainly: divides per column or slice, multiplies per point, shifts and table look-ups per pixel [S32X-SKILL, software-3d.md]. The usual moves:

- **One divide per row of points that share a depth.** Every cell in a voxel slice and every pixel on a road scanline shares one depth. Compute its reciprocal once and multiply by it for each point: about three divides per cell become one per slice. Measure before and after, though. In one voxel game, hoisting about 1,800 divides a picture changed the frame rate not at all, because drawing was the bottleneck [S32X-SKILL, optimization.md; voxel-landscape.md].
- **One slope per edge, not one divide per scanline.** A polygon filler that divided per scanline became twice as fast when it computed a 16.16 *dx/dy* once per edge and added it on each row [S32X-SKILL, optimization.md].
- **Tables, as Star Wars Arcade builds them.** A reciprocal table turns a divide into a look-up and a multiply.
- **Watch for hidden 64-bit divides.** In C, `((int64_t)dx << 16) / dy` compiles to gcc's `__divdi3`, a slow software routine that never touches the unit. Search the disassembly for `__divdi3` and `__udivdi3`. One road renderer was making about 340 such calls a picture [S32X-SKILL, optimization.md]. A small inline function that drives the DIVU directly, as d32xr's `FixedDiv` does, replaces them.

## In emulators

- **PicoDrive and Ares both return the result at once.** Neither charges the 39 clocks or stalls an early read, so code that reads the quotient straight away looks faster than it is, and overlap tuning shows no gain <span class="tag emulator">emulator</span> [PICODRIVE, pico/32x/sh2soc.c; ARES, component/processor/sh2/sh7604/io.cpp].
- **Divide by zero.** For a 32/32 divide, PicoDrive leaves the dividend in DVDNT, puts 0 in DVDNTL, DVDNTH and both copies, and leaves OVF clear. Ares returns `$7FFFFFFF` whatever the dividend's sign, sets OVF and leaves DVDNTH as it was. Neither matches the Saturn test ([Divide by zero](#divide-by-zero)) <span class="tag emulator">emulator</span> [PICODRIVE, pico/32x/sh2soc.c; ARES, component/processor/sh2/sh7604/io.cpp].
- **Other overflows.** PicoDrive returns the right limit after a 64/32 overflow but never sets OVF, so code that checks the flag never sees one. MAME sets the limit and OVF, but its partial remainder differs from the Saturn test: 1 instead of `$FFFFFFFE` for `$00000001_00000000` ÷ 1 [MAME, sh7604.cpp].
- **Ares flags a 64/32 overflow for quotients above `$7FFF7FFF`,** not `$7FFFFFFF`. A divide whose true quotient is between `$7FFF8000` and `$7FFFFFFF` returns `$7FFFFFFF` with OVF set, up to 32,767 too high. Nothing supports this limit. The manual, the Saturn test and the four other emulators all use the signed 32-bit range, and the lower bound on the next line of Ares's code is exactly −2<sup>31</sup>. The line came in with Ares v118r11 (22 March 2021), a release snapshot with no notes, so it is most likely a typo for `$7FFFFFFF` <span class="tag emulator">emulator</span> [ARES, component/processor/sh2/sh7604/io.cpp].
- **The copies at `0xFFFFFF18` and `0xFFFFFF1C`** ([Two registers the manual leaves out](#two-registers-the-manual-leaves-out)) exist in all five emulators, in three different forms. PicoDrive keeps them as separate values that each divide fills. Ares makes them aliases of DVDNTH and DVDNTL, so writing `0xFFFFFF1C` starts a 64/32 divide. MAME makes them read-only aliases. Only Mednafen and Yabause repeat the block at `0xFFFFFF20`.

## Open questions

- Do a 32X's SH-2s give the Saturn test's results: the limit with the dividend's sign for a zero divisor, the three-step remainder in DVDNTH, the separate copies at `0xFFFFFF18` and `0xFFFFFF1C`, and the repeat at `0xFFFFFF20`? The same CPU makes it likely; a run of YabauseUT's DIVU tests on a 32X would settle it.
- Where exactly is the overflow boundary when both operands are negative? The manual flags a quotient of `$7FFFFFFF` with a remainder left over; Mednafen does not flag an exact quotient of 2<sup>31</sup> from two negative operands and lets it wrap to `$80000000`. A test of quotients either side of `$7FFFFFFF` with each sign combination would show which.

## Sources

- [SH7604](../appendices/bibliography.md#sh7604): §10 division unit (§10.3.3 overflow), §5.3.1, §7.11.2
- [D32XR](../appendices/bibliography.md#d32xr): sh2_fixed.s, r_phase2.c, r_phase6.c, r_phase7.c, r_phase8.c, r_main.c, p_sight.c
- [MK2](../appendices/bibliography.md#mk2): SH-2 code at `0x0600114C`, `0x060015D2`
- [AB32X](../appendices/bibliography.md#ab32x): SH-2 code at `0x060025A0`-`0x060025CC`
- [SWA](../appendices/bibliography.md#swa): SH-2 code at `0x06000EFE`, `0x060015E0`, `0x06002BE8`
- [AU-NOTES](../appendices/bibliography.md#au-notes): ROADMAP.md, tools/make_sega_logo.py
- [S32X-SKILL](../appendices/bibliography.md#s32x-skill): software-3d.md, optimization.md, voxel-landscape.md
- [PICODRIVE](../appendices/bibliography.md#picodrive): pico/32x/sh2soc.c
- [ARES](../appendices/bibliography.md#ares): component/processor/sh2/sh7604/io.cpp
- [MAME](../appendices/bibliography.md#mame): src/devices/cpu/sh/sh7604.cpp
- [MEDNAFEN](../appendices/bibliography.md#mednafen): ss/sh7095.inc
- [YABAUSE](../appendices/bibliography.md#yabause): yabause/src/sh2core.c, yabauseut/src/sh2.c
- [RLT](../appendices/bibliography.md#rlt): SH-2 code at `0x0603066C`-`0x060306B2`
- [VRD-NOTES](../appendices/bibliography.md#vrd-notes): SH-2 code at `0x06002398`-`0x060037CA` (the project's patched copy)
- [32X-TB27](../appendices/bibliography.md#32x-tb27): the Saturn uses the same CPU
