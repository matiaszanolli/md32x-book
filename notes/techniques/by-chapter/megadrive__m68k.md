# Harvested techniques: megadrive/m68k.md

Target: `megadrive/m68k.md`. 4 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from AB-DISASM -->
### 32×32 multiply from three MULU.W, skipping zero halves
- Source: AB-DISASM, disasm/modules/68k/math/Multiply32.asm:1-30 ($03E05C, 204 calls)
- What it does and why it is clever: The low 32 bits of the product are a_lo×b_lo + ((a_hi×b_lo + a_lo×b_hi) << 16). The a_hi×b_hi term can only affect bits 32 and up, so it is never computed. Each cross product is skipped when its high word is 0, which is the common case for game values, so most calls cost a single MULU.
- Key numbers: 1-3 MULU.W (about 70 cycles each at most).
- Target chapter: megadrive/m68k.md
- Evidence: code only (shipped)

<!-- from AB-DISASM -->
### Three-tier 32/32 unsigned divide
- Source: AB-DISASM, disasm/modules/68k/math/UnsignedDivide.asm:1-60 ($03E0C6)
- What it does and why it is clever: The routine picks the cheapest method that is correct:
  1. If the divisor is under $10000, try one DIVU.W.
  2. If that overflows (quotient over 16 bits), do schoolbook long division with two DIVU.W: divide the high word, then (remainder:low word).
  3. If the divisor is $10000 or more, run 16 iterations of shift-and-subtract with `add.l` / `addx.l`. Only 16 are needed because the quotient must fit in 16 bits.

  It returns the quotient in D0 and the remainder in D1.
- Key numbers: 16 loop iterations at most.
- Target chapter: megadrive/m68k.md
- Evidence: code only (shipped)

<!-- from AB-DISASM -->
### Signed divide and modulo with a DIVS.W fast path
- Source: AB-DISASM, disasm/modules/68k/math/SignedDiv.asm:1-35 ($03E08A, 169 calls); disasm/modules/68k/math/SignedMod.asm:1-40 ($03E146); disasm/modules/68k/math/UnsignedMod.asm ($03E12A); disasm/modules/68k/math/MulDiv.asm ($01E11C)
- What it does and why it is clever:
  - If the divisor fits in a signed 16-bit value, one DIVS.W is tried. On overflow or a big divisor, the routine takes absolute values, runs the unsigned divide and fixes the sign with a byte toggled by `not.b`.
  - The modulo takes the sign of the dividend, as in C.
  - MulDiv is (a×b)/c with a zero-divisor guard, used for percentages.

  These are what Koei's C runtime used for all the economy maths.
- Key numbers: DIVS.W is about 158 cycles maximum; the slow path calls UnsignedDivide.
- Target chapter: megadrive/m68k.md
- Evidence: code only (shipped)

<!-- from AB-DISASM -->
### Overlap-safe memmove
- Source: AB-DISASM, disasm/modules/68k/game/DecompressVDPTiles.asm:294-324 (MemMove $0045B2)
- What it does and why it is clever: The routine compares source and destination pointers. If source ≤ destination it copies backwards with `-(a0),-(a1)`, otherwise forwards. That is the minimal correct memmove. The text engine relies on it to shift its row buffers in place.
- Key numbers: 16-bit count.
- Target chapter: megadrive/m68k.md
- Evidence: code only (shipped)

---

