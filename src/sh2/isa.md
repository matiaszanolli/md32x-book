# Registers and instruction set

The SH-2 is a 32-bit RISC with sixteen general registers, one condition flag and fixed 16-bit instructions. This chapter covers the registers, how the instructions address memory, the T bit, delayed branches, the instructions that make up for having no barrel shifter and no divide, and an opcode map for reading raw `dc.w` data in a disassembly. Timing is in [Pipeline and cycle counting](pipeline.md).

## Registers

### General registers

| Register | Use |
|----------|-----|
| R0 | An ordinary register, and also the only register some instructions work with: the index in `@(R0,Rn)` and `@(R0,GBR)`, the data register for byte and word loads and stores with a displacement and for every GBR-relative load and store, the target of `MOVA`, and the register for `AND`/`OR`/`XOR`/`TST`/`CMP/EQ` with an immediate |
| R1-R14 | General use |
| R15 | General use, and the stack pointer for exceptions: interrupts and traps push SR and PC through it |

All are 32 bits wide [SH-PM §2.1 p.16].

### Control registers

**SR**, the status register [SH-PM §2.2 pp.16-18]:

| Bit | Name | Meaning |
|-----|------|---------|
| 9 | M | Used by the step-division instructions `DIV0S`, `DIV0U` and `DIV1` |
| 8 | Q | Used by the step-division instructions |
| 7-4 | I3-I0 | Interrupt mask: requests at this level or below wait. See [Interrupt controller](intc.md) |
| 1 | S | Saturation for `MAC.W` and `MAC.L` (see [Multiplies](#multiplies)) |
| 0 | T | The one condition flag (see [The T bit](#the-t-bit)) |

The other bits read 0 and should be written 0.

**GBR**, the global base register, is the base of the `@(disp,GBR)` and `@(R0,GBR)` modes. Hitachi meant it for on-chip peripheral registers. The 32X boot ROM leaves it pointing at the 32X system registers, `0x20004000` (see [Boot](../32x/boot.md#each-sh-2-at-its-entry-point)). Programs use it as they please:
- d32xr points each SH-2's GBR at its own block of per-CPU variables, so the same code finds its own CPU's light table and frame buffer [D32XR, marsnew.c, doomdef.h].
- Star Wars Arcade points it at a block of its own variables in SDRAM, `0x060075E4` [SWA, SH-2 code at `0x060008F2`, `0x06000EE6`].

**VBR**, the vector base register, holds the address of the exception vector table. See [Interrupt controller](intc.md).

### System registers

| Register | Holds |
|----------|-------|
| MACH, MACL | The multiplier's result: a 64-bit product or sum, or a 32-bit product in MACL alone. On the SH-2 all 32 bits of MACH are valid |
| PR | The return address, written by `BSR`, `BSRF` and `JSR`, read by `RTS`. It is the address of the instruction after the call's delay slot: the call's own address + 4 [SH-PM §6.10 p.72, §6.11 p.74, §6.26 p.99] |
| PC | The program counter |

Source: [SH-PM §2.3 p.19].

After reset, SR has the interrupt mask at 15 and VBR is 0. PC and R15 come from the vector table, and everything else is undefined [SH-PM §2.4 p.19]. On the 32X the boot ROM has changed several of these before your code starts (see [Boot](../32x/boot.md#each-sh-2-at-its-entry-point)).

### gcc's register convention

The SH-2 itself has no calling convention. The one that matters on the 32X is gcc's, because d32xr, marsdev and Aerobiz Ultimate's SH-2 code are all built with it. Checked by compiling test functions with sh-elf-gcc 13.2 (`-m2 -mb -O2`), the version in [GNU-TOOLS]. 16.2 gives the same results, and so does marsdev's 15.1, except that its build has no `__builtin_thread_pointer` for the GBR test:

| Registers | Role |
|-----------|------|
| R4-R7 | First four arguments. Further arguments go on the stack |
| R0 | Return value. A 64-bit value comes back in R0 (high half) and R1 |
| R2 | For a function that returns a structure: the address the caller passes for it. The function writes the structure there and returns the address in R0 |
| R0-R7, MACH, MACL | Free for the called function to change |
| R8-R14 | Must be preserved by the called function. R14 is the frame pointer when one is used |
| PR | Saved on the stack by any function that itself makes a call |
| GBR | Never changed by compiled code, and assumed unchanged across a call: two reads of it on either side of a call are merged into one. A program can keep GBR pointing at its own data, as d32xr does |

Assembly routines called from C must follow it. d32xr's drawing routines take their first four arguments in R4-R7 and the rest from the stack [D32XR, sh2_draw.s].

## Data and addressing

**Big-endian, aligned.** The most significant byte is at the lowest address. A word access must be at an even address and a longword at a multiple of 4; anything else is an address error [SH-PM §3.2 p.21].

**Loads sign-extend.** A byte or word read into a register is sign-extended to 32 bits [SH-PM §3.1 p.21]. To use it as unsigned, follow it with `EXTU.B` or `EXTU.W`, or arrange the data so the signed value works directly. d32xr does the latter: its colour lookup tables are addressed through a pointer 128 bytes into the table, so a signed texel from −128 to 127 indexes it with no `EXTU.B` [D32XR, r_data.c, marsdraw.c]. Its RoQ video decoder does the same with its cell tables [D32XR, roq_read.c].

**Immediates are 8 bits.** `MOV`, `ADD` and `CMP/EQ` sign-extend them (−128 to 127). `AND`, `OR`, `XOR` and `TST` zero-extend them, so `AND #imm,R0` always clears the top 24 bits [SH-PM §3.3 p.22]. A larger constant comes from a **literal pool**: a table of words or longwords placed after the code and read with a PC-relative `MOV`. A word literal, read with `MOV.W @(disp,PC),Rn`, is sign-extended like any other word load, so a 16-bit constant from `$8000` to `$FFFF` arrives as a negative longword: a mask of `$FFFF` stored as a word literal becomes `$FFFFFFFF`. Use a longword literal, or the `MOV #-1` and `EXTU.W` pair in the table below. A literal costs a memory access, so a constant that two instructions can build is often better [SH-PM §4.1.8 p.25]:

| Constant | Built with |
|----------|------------|
| `$0000FFFF` | `MOV #-1,Rn`, then `EXTU.W Rn,Rn` |
| `$00010000` | `MOV #1,Rn`, then `SHLL16 Rn` |
| `$FFFFFF00` (the [division unit](divu.md)) | `MOV #-128,Rn`, then `ADD Rn,Rn` |

d32xr uses all three in inline assembly, so that gcc does not load them from a pool [D32XR, r_phase6.c, r_phase8.c].

### Addressing modes

| Mode | Written | Address | Reach |
|------|---------|---------|-------|
| Register | `Rn` | (the operand is the register) | |
| Indirect | `@Rn` | Rn | |
| Post-increment | `@Rm+` | Rm, then Rm += size. Loads only, plus `MAC`, `LDC.L`, `LDS.L` | |
| Pre-decrement | `@-Rn` | Rn −= size, then Rn. Stores only, plus `STC.L`, `STS.L` | |
| Displacement | `@(disp,Rn)` | Rn + disp × size | 0-15 units: 15 bytes, 30 bytes, 60 bytes. Byte and word forms use R0 as the data register |
| Indexed | `@(R0,Rn)` | Rn + R0 | |
| GBR displacement | `@(disp,GBR)` | GBR + disp × size | 0-255 units: up to 1,020 bytes for longwords. Data register is always R0 |
| GBR indexed | `@(R0,GBR)` | GBR + R0 | Only for `AND.B`, `OR.B`, `XOR.B`, `TST.B` with an immediate |
| PC-relative | `@(disp,PC)` | PC + disp × size. For longwords PC's low 2 bits are cleared first | 0-255 units forward: 510 bytes for words, 1,020 for longwords |

Source: [SH-PM §4.2 pp.26-28]. Displacements are never negative, so a literal pool must come after the code that uses it. Here PC means the address of the instruction plus 4.

Two consequences shape SH-2 code:

- **Post-increment is for loads, pre-decrement for stores.** There is no store that steps a pointer up. That is why stacks grow downward, and why loops that store to memory often run backwards (see [Pipeline](pipeline.md#other-patterns-in-real-code)).
- **There is no absolute address mode.** To reach a fixed address, load it from a literal pool into a register first [SH-PM §4.1.9 p.25].

Two tricks with the indexed modes appear in After Burner Complete's code [AB32X, SH-2 code at `0x0600680A`, `0x060082C0`]:

- **`@(R0,R0)` scales by two.** Keep half a word address in R0 and `MOV.W @(R0,R0),Rn` reads the word at twice that, with no shift. The sprite scaler steps through its source this way, so the pointer it advances is in pixel pairs.
- **`TST.B #imm,@(R0,GBR)` tests a register bit in place.** With GBR at the 32X VDP registers and R0 = 11, `TST.B #2,@(R0,GBR)` polls FEN in one instruction, without loading the byte into a register first.

Branch reach [SH-PM §4.2 p.27]:

| Instructions | Target |
|--------------|--------|
| `BT`, `BF`, `BT/S`, `BF/S` | PC + 2 × an 8-bit signed value: −256 to +254 bytes |
| `BRA`, `BSR` | PC + 2 × a 12-bit signed value: −4,096 to +4,094 bytes |
| `BRAF`, `BSRF` | PC + Rm |
| `JMP`, `JSR` | Rm |

## The T bit

The SH-2 has no N, Z, C or V flags, just T. Compares set it, conditional branches test it, and a few arithmetic instructions use it as a carry [SH-PM §4.1.7 p.24]:

- **Compares:** `CMP/EQ`, `CMP/HS` and `CMP/HI` (unsigned ≥ and >), `CMP/GE` and `CMP/GT` (signed ≥ and >), `CMP/PZ` and `CMP/PL` (≥ 0 and > 0), and `CMP/STR` (true if any of the four bytes match). There is no "less than": swap the operands, or branch on false.
- **`TST`** sets T when the AND of its operands is 0.
- **`DT Rn`** subtracts 1 and sets T when the result is 0. It is the loop counter.
- **Carries:** `ADDC`, `SUBC` and `NEGC` take T in and give it back out, which chains them for 64-bit arithmetic. The same chain makes a cheap fixed-point step. Keep the fraction in the high half of one register and the integer in another: `ADDC` on the fraction carries into T, and `ADDC` on the integer adds the step plus that carry, two instructions in all. The first `ADDC` also adds whatever T holds when it runs, so T must be clear there or the fraction gains 1. After Burner Complete's sprite scaler steps through its source like this, eight steps unrolled, and never uses `CLRT` [AB32X, SH-2 code at `0x0600680A`-`0x0600684C`]. T is clear at the top of each pass because the `DT` that closes the loop leaves it 0 when it branches back. Between the unrolled steps T is the carry out of the integer `ADDC`, which a positive step never produces. In any case a stray 1 would land in the lowest bit of a fraction kept in the high half of its register, 16 bits below the precision it uses. `ADDV`/`SUBV` set T on signed overflow. One-bit shifts and rotates put the bit shifted out into T.
- **`MOVT Rn`** copies T to a register, `SETT` and `CLRT` set and clear it.

Most other instructions leave T alone, including `ADD`, `SUB`, `MOV` and the logic operations other than `TST`. That lets a compare sit several instructions ahead of its branch.

**`TAS.B @Rn`** reads a byte, sets T if it was 0, sets the byte's top bit and writes it back, holding the bus from the read to the write [SH-PM §6.66 p.161]. On a machine with two CPUs that is the obvious lock. On the 32X it is disputed: Sega's manual forbids it without giving a reason, d32xr relies on it, and gcc emits it for its atomic test-and-set only with `-mtas` <span class="tag disputed">disputed</span> ([Between the two SH-2s](../32x/communication.md#between-the-two-sh-2s); [discrepancy 12](../appendices/discrepancies.md); [The toolchain](../howto/toolchain.md)).

## Delayed branches

`BRA`, `BSR`, `BRAF`, `BSRF`, `JMP`, `JSR`, `RTS`, `RTE`, `BT/S` and `BF/S` are **delayed**: the instruction after them, in the delay slot, runs before the jump takes effect. `BT`, `BF` and `TRAPA` are not delayed [SH-PM §4.1.5 p.23; SH7604 Table 4.9].

The rules [SH-PM §6.1 p.59; SH7604 §4.5.3, §4.6.1] <span class="tag manual">manual</span>:

- **The branch uses register values from before the slot.** If the delay slot changes the register a `JMP`, `JSR`, `BRAF` or `BSRF` jumps through, the jump still goes to the old address. The same holds for `RTS` and PR: restoring PR in the slot of the `RTS` that uses it returns to the old value [SH-PM §4.1.5 p.23, §6.51 pp.141-142].
- **No branch in a delay slot.** Any instruction that changes PC (all the branches above, plus `BT`, `BF` and `TRAPA`), or any undefined code, raises the **slot-illegal** exception, vector 6, instead of running.
- **Avoid PC-relative loads in a delay slot.** A `MOV @(disp,PC)` or `MOVA` there computes its address from the branch target + 2, not from its own position [SH-PM §6.33 p.117, §6.36 p.125].
- **Nothing interrupts between a branch and its slot.** Neither interrupts nor address errors are accepted there. Interrupts also wait one instruction after any `LDC`, `LDS`, `STC` or `STS` [SH7604 §4.6].

The assembler does not apply the PC-relative rule. sh-elf-as 2.47 assembles a literal load or a `MOVA` in a delay slot without a warning, with the displacement worked out from the instruction's own address, so on a console it reads a different word. gcc 13.2, 15.1 and 16.2 never put one there: they load the literal before the branch and leave a `NOP` in the slot. Both checked for this book by assembling and compiling test cases. ares and PicoDrive follow the manual here ([In emulators](#in-emulators)), so the mistake shows up in testing as well.

d32xr builds 1 << *k* for *k* from 0 to 7 out of the first rule [D32XR, p_sight.c]. It computes 2 × (7 − *k*) into a register, then `BRAF` through that register into a run of seven `SHLL`s, skipping all but *k* of them. Its delay slot loads 1 into the same register. The jump uses the old value, the shifts work on the new one, and the result is 1 << *k* in 5 + *k* instructions with no loop.

## Shifts without a barrel shifter

The SH-2 shifts by 1, 2, 8 or 16 places in one instruction, and only by 1 for arithmetic (sign-keeping) right shifts [SH-PM Table 5.6 p.45]:

| Shift | Instructions |
|-------|--------------|
| Left | `SHLL` (or `SHAL`, the same thing), `SHLL2`, `SHLL8`, `SHLL16` |
| Right, unsigned | `SHLR`, `SHLR2`, `SHLR8`, `SHLR16` |
| Right, signed | `SHAR` only |
| Rotate | `ROTL`, `ROTR`, and `ROTCL`/`ROTCR` through T |

So any shift by a variable amount, and any signed right shift by more than a few places, takes several instructions. sh-elf-gcc 13.2 (`-m2 -O2`, and 15.1 and 16.2 alike) compiles a signed `>> 3` as three `SHAR`s. A signed `>> 8` becomes a call to a library routine, `___ashiftrt_r4_8`, and a shift by a variable amount a call to `___ashrsi3`. A signed `>> 16` is the exception: `SWAP.W` then `EXTS.W`, two instructions (below). d32xr's friction code replaced the original (*x* >> 8) × (*f* >> 8) with a 16.16 multiply. Its comment says the shifts went through gcc's library routines and were much slower on the SH-2 [D32XR, p_base.c].

What helps:

- **`SWAP.W`** exchanges the two halves of a register. On a 16.16 fixed-point value it brings the integer part down in one instruction, which d32xr's texture loops use (the top half then holds the old fraction, so mask or extend before use) [D32XR, sh2_draw.s]. Followed by `EXTS.W`, it is a signed shift right by 16 in two instructions, which is what gcc makes of a signed `>> 16`.
- **Shift unsigned, then let the multiply restore the sign.** `MULS.W` reads only the low 16 bits of each operand, as signed. d32xr's side-of-line tests take the integer part of a 16.16 coordinate with an unsigned `SHLR16`, which is one instruction, instead of a signed shift. The `MULS.W` that follows then treats the low half as signed anyway [D32XR, r_local.h, p_maputl.c].
- **Shift-and-add instead of multiply** for small constants. d32xr computes *y* × 320 as (*y* << 8) + (*y* << 6), using `SHLL8` and then `SHLR2` on the shifted copy [D32XR, sh2_draw.s]. gcc compiles the same `y*320` as a word literal load and `MUL.L` (checked with 13.2, 15.1 and 16.2, `-m2 -mb -O2`).
- **Prefer types that avoid extension.** d32xr compares two sectors' light levels as signed bytes, which saves an `EXTU` [D32XR, r_phase1.c].

## Multiplies

| Instruction | Operation | Result in |
|-------------|-----------|-----------|
| `MULS.W Rm,Rn` / `MULU.W` | Signed / unsigned 16 × 16 → 32 | MACL |
| `MUL.L Rm,Rn` | 32 × 32, low 32 bits | MACL |
| `DMULS.L Rm,Rn` / `DMULU.L` | Signed / unsigned 32 × 32 → 64 | MACH:MACL |
| `MAC.W @Rm+,@Rn+` | Signed 16 × 16 from memory, added to MACH:MACL | MACH:MACL |
| `MAC.L @Rm+,@Rn+` | Signed 32 × 32 from memory, added to MACH:MACL | MACH:MACL |

Sources: [SH-PM Table 5.4 pp.42-43; §6.29 p.105; §6.31 p.109]. Read results with `STS MACH,Rn` and `STS MACL,Rn`. Clear the accumulator with `CLRMAC` before a run of `MAC`s.

The `MAC`s read both operands from memory and step both pointers. With the S bit set they saturate instead of wrapping: `MAC.W` becomes a 32-bit accumulate that sticks at `$7FFFFFFF` or `$80000000`, and `MAC.L` sticks at the limits of a 48-bit value [SH-PM §6.29 p.105, §6.31 p.109].

**A 16.16 × 16.16 multiply** needs the middle 32 bits of the 64-bit product. `XTRCT Rm,Rn` takes the low half of Rm and the high half of Rn and joins them [SH-PM §6.70 p.167]. So the whole multiply is `DMULS.L`, `STS MACH`, `STS MACL`, then `XTRCT` of the MACH copy into the MACL copy. sh-elf-gcc 13.2 produces the same four instructions from `((int64_t)a * b) >> 16`. Later versions do worse: 15.1 and 16.2 replace the `XTRCT` with `SHLL16`, `SHLR16` and `ADD`, six instructions, at `-O2`, `-O3` and `-Os` alike (checked for this book). d32xr writes its `FixedMul` that way in C, and keeps a hand-written copy that puts the `XTRCT` in the `RTS` delay slot [D32XR, doomdef.h, sh2_fixed.s].

**Star Wars Arcade transforms points with `MAC.L`** [SWA, SH-2 code at `0x060028D0`-`0x06002932`]. For each point it reads three 16-bit coordinates into the first three longwords of a four-longword vector. Then for each of three outputs it clears MAC, runs four `MAC.L`s down a column of a 16.16 matrix (stepping the matrix pointer to the next row between them), reads MACH and MACL, joins them with `XTRCT`, and adds an offset held in a register. One output takes `CLRMAC`, four `MAC.L`s, two `STS`, an `XTRCT` and an `ADD`. See [Pipeline](pipeline.md#the-multiplier) for how long the multiplier is busy.

## Division

The SH-2 divides one bit at a time. `DIV0S` (signed) or `DIV0U` (unsigned) sets up M, Q and T, and each `DIV1` then produces one quotient bit, and each `DIV1` is paired with a `ROTCL` that shifts the quotient bit into a register. Hitachi's own examples for a 32-bit quotient are 70 instructions for an unsigned 64 ÷ 32 (five for the checks and setup, 32 pairs, one last `ROTCL`) and 72 for a signed 32 ÷ 32, about as many clocks [SH-PM §6.17-6.19 pp.84-90]. The on-chip [division unit](divu.md) does a 32- or 64-bit divide in 39 clocks without the CPU, and is usually the better choice.

## What only the SH-2 has

The SH-2 adds these to the SH-1 instruction set [SH-PM Table 5.1 p.34]:

| Instruction | Use |
|-------------|-----|
| `BT/S`, `BF/S` | Conditional branches with a delay slot. Taken, they cost 2 clocks instead of 3 |
| `BRAF Rm`, `BSRF Rm` | Branch or call to PC + Rm: jump tables and position-independent calls |
| `DT Rn` | Decrement and set T on zero: one-instruction loop counting |
| `MUL.L` | 32 × 32 → 32 multiply |
| `DMULS.L`, `DMULU.L` | 32 × 32 → 64 multiply |
| `MAC.L` | 32 × 32 + 64 multiply-accumulate |

`MAC.W` also changes: the SH-1 accumulates into 42 bits, the SH-2 into 64.

Later SuperH chips (SH-2A, SH-3, SH-4) add many more. **Disassemblers need care here.** binutils (`objdump -m sh2`) decodes exactly the SH-2's 142 instructions. capstone 5.0.7 in `CS_MODE_SH2` also decodes 452 words that are illegal on an SH-2, as SH-2A and SH-4A instructions such as `movml.l`, `jsr/n`, `rtv/n`, `divu` and `movua.l`. A word that capstone shows as one of those is data, or an error, on a 32X.

## Opcode map

Every instruction is one 16-bit word. Read the first hex digit, then follow the table. In the patterns, `n` is Rn, `m` is Rm, `d` a displacement, `i` an immediate, and `x` any digit.

| First digit | Instruction |
|-------------|-------------|
| `0` | Miscellaneous: see below |
| `1nmd` | `MOV.L Rm,@(d×4,Rn)` |
| `2nm?` | Stores and logic: see below |
| `3nm?` | Compares, add, subtract, `DIV1`, `DMULx.L`: see below |
| `4n??` | One-register operations and system register moves: see below |
| `5nmd` | `MOV.L @(d×4,Rm),Rn` |
| `6nm?` | Loads and register moves: see below |
| `7nii` | `ADD #i,Rn` |
| `8???` | Short-displacement byte and word moves, `CMP/EQ #i`, conditional branches: see below |
| `9ndd` | `MOV.W @(d×2,PC),Rn` |
| `Addd` | `BRA` |
| `Bddd` | `BSR` |
| `C???` | GBR moves, `TRAPA`, `MOVA`, logic with R0 and an immediate: see below |
| `Dndd` | `MOV.L @(d×4,PC),Rn` |
| `Enii` | `MOV #i,Rn` |
| `F` | Undefined on the SH-2 |

**`0` group**, by the last digit (and the third digit where it matters):

| Last digit | Third digit 0 | Third digit 1 | Third digit 2 |
|------------|---------------|---------------|---------------|
| 2 (`0n?2`) | `STC SR,Rn` | `STC GBR,Rn` | `STC VBR,Rn` |
| 3 (`0m?3`) | `BSRF Rm` | | `BRAF Rm` |
| 8 (`00?8`) | `CLRT` | `SETT` | `CLRMAC` |
| 9 | `NOP` (`0009`) | `DIV0U` (`0019`) | `MOVT Rn` (`0n29`) |
| A (`0n?A`) | `STS MACH,Rn` | `STS MACL,Rn` | `STS PR,Rn` |
| B (`00?B`) | `RTS` | `SLEEP` | `RTE` |

The rest of the `0` group ignores the third digit, which is Rm: `0nm4`/`5`/`6` = `MOV.B`/`W`/`L Rm,@(R0,Rn)`; `0nm7` = `MUL.L Rm,Rn`; `0nmC`/`D`/`E` = `MOV.B`/`W`/`L @(R0,Rm),Rn`; `0nmF` = `MAC.L @Rm+,@Rn+`.

**`2nm?`, `3nm?` and `6nm?`**, by the last digit:

| Last digit | `2nm?` | `3nm?` | `6nm?` |
|------------|--------|--------|--------|
| 0 | `MOV.B Rm,@Rn` | `CMP/EQ Rm,Rn` | `MOV.B @Rm,Rn` |
| 1 | `MOV.W Rm,@Rn` | | `MOV.W @Rm,Rn` |
| 2 | `MOV.L Rm,@Rn` | `CMP/HS Rm,Rn` | `MOV.L @Rm,Rn` |
| 3 | | `CMP/GE Rm,Rn` | `MOV Rm,Rn` |
| 4 | `MOV.B Rm,@-Rn` | `DIV1 Rm,Rn` | `MOV.B @Rm+,Rn` |
| 5 | `MOV.W Rm,@-Rn` | `DMULU.L Rm,Rn` | `MOV.W @Rm+,Rn` |
| 6 | `MOV.L Rm,@-Rn` | `CMP/HI Rm,Rn` | `MOV.L @Rm+,Rn` |
| 7 | `DIV0S Rm,Rn` | `CMP/GT Rm,Rn` | `NOT Rm,Rn` |
| 8 | `TST Rm,Rn` | `SUB Rm,Rn` | `SWAP.B Rm,Rn` |
| 9 | `AND Rm,Rn` | | `SWAP.W Rm,Rn` |
| A | `XOR Rm,Rn` | `SUBC Rm,Rn` | `NEGC Rm,Rn` |
| B | `OR Rm,Rn` | `SUBV Rm,Rn` | `NEG Rm,Rn` |
| C | `CMP/STR Rm,Rn` | `ADD Rm,Rn` | `EXTU.B Rm,Rn` |
| D | `XTRCT Rm,Rn` | `DMULS.L Rm,Rn` | `EXTU.W Rm,Rn` |
| E | `MULU.W Rm,Rn` | `ADDC Rm,Rn` | `EXTS.B Rm,Rn` |
| F | `MULS.W Rm,Rn` | `ADDV Rm,Rn` | `EXTS.W Rm,Rn` |

**`4n??`**, by the last digit (and the third digit where it matters; `4nmF` is `MAC.W @Rm+,@Rn+`):

| Last digit | Third digit 0 | Third digit 1 | Third digit 2 |
|------------|---------------|---------------|---------------|
| 0 | `SHLL` | `DT` | `SHAL` |
| 1 | `SHLR` | `CMP/PZ` | `SHAR` |
| 2 | `STS.L MACH,@-Rn` | `STS.L MACL,@-Rn` | `STS.L PR,@-Rn` |
| 3 | `STC.L SR,@-Rn` | `STC.L GBR,@-Rn` | `STC.L VBR,@-Rn` |
| 4 | `ROTL` | | `ROTCL` |
| 5 | `ROTR` | `CMP/PL` | `ROTCR` |
| 6 | `LDS.L @Rm+,MACH` | `LDS.L @Rm+,MACL` | `LDS.L @Rm+,PR` |
| 7 | `LDC.L @Rm+,SR` | `LDC.L @Rm+,GBR` | `LDC.L @Rm+,VBR` |
| 8 | `SHLL2` | `SHLL8` | `SHLL16` |
| 9 | `SHLR2` | `SHLR8` | `SHLR16` |
| A | `LDS Rm,MACH` | `LDS Rm,MACL` | `LDS Rm,PR` |
| B | `JSR @Rm` | `TAS.B @Rn` | `JMP @Rm` |
| E | `LDC Rm,SR` | `LDC Rm,GBR` | `LDC Rm,VBR` |

In the `LDS`, `LDC` (including the `.L` forms), `JSR` and `JMP` rows, the second digit is the source register, Rm.

**`8???` and `C???`**, by the second digit:

| Second digit | `8?xx` | `C?xx` |
|--------------|--------|--------|
| 0 | `MOV.B R0,@(d,Rn)` (`80nd`) | `MOV.B R0,@(d,GBR)` |
| 1 | `MOV.W R0,@(d×2,Rn)` (`81nd`) | `MOV.W R0,@(d×2,GBR)` |
| 2 | | `MOV.L R0,@(d×4,GBR)` |
| 3 | | `TRAPA #i` |
| 4 | `MOV.B @(d,Rm),R0` (`84md`) | `MOV.B @(d,GBR),R0` |
| 5 | `MOV.W @(d×2,Rm),R0` (`85md`) | `MOV.W @(d×2,GBR),R0` |
| 6 | | `MOV.L @(d×4,GBR),R0` |
| 7 | | `MOVA @(d×4,PC),R0` |
| 8 | `CMP/EQ #i,R0` | `TST #i,R0` |
| 9 | `BT` | `AND #i,R0` |
| A | | `XOR #i,R0` |
| B | `BF` | `OR #i,R0` |
| C | | `TST.B #i,@(R0,GBR)` |
| D | `BT/S` | `AND.B #i,@(R0,GBR)` |
| E | | `XOR.B #i,@(R0,GBR)` |
| F | `BF/S` | `OR.B #i,@(R0,GBR)` |

Empty cells are undefined. An undefined word raises the general illegal instruction exception (vector 4), or slot-illegal (vector 6) in a delay slot [SH-PM §6.1 p.59; SH7604 §4.5].

This map was checked against binutils' SH-2 disassembler for all 65,536 words: it has 142 patterns, matching Hitachi's count of 142 instructions, and agrees on every word. Hitachi's own map has three slips in the scan [SH-PM Table A.51 pp.286-287]: it shows `MOV.B Rm,Rn` for `6nm0` and `MOV.B Rm+,Rn` for `6nm4` (both are loads, `@Rm` and `@Rm+`), and `R0` as the destination of `Dndd` (it is Rn, as Table 5.3 has it).

### Reading raw code

Words that turn up often in disassemblies:

| Word | Meaning |
|------|---------|
| `0009` | `NOP`, also used as padding to align code |
| `000B` | `RTS` |
| `002B` | `RTE` |
| `AFFE` | `BRA` to itself: an endless loop (its delay slot comes next) |
| `4F22` / `4F26` | `STS.L PR,@-R15` / `LDS.L @R15+,PR`: saving and restoring the return address, the start and end of a function that makes calls |

A disassembler that reads straight through, from start to end, also decodes literal pools and tables as instructions. A run of `Dndd` loads (`MOV.L @(disp,PC)`) usually points at the pool: its target addresses are where the data lives. Expect a pool after each `RTS` or `BRA` with its delay slot. Instruction counts from a straight-through pass are inflated by these, so count only code you have traced from a known entry point. Mortal Kombat II shows how far off this can be. A straight-through pass over its 32 KB SH-2 program finds 124 `MAC.L`, 88 `MAC.W`, 105 `MUL.L` and 15 `SLEEP`. Following the code from its entry points and jump tables reaches 12.9 KB, which contains none of these. The rest is palettes, tables and pointers [MK2, SH-2 program].

## In emulators

- **Ares** raises the slot-illegal exception for a branch in a delay slot, as the hardware does, and the general illegal exception for undefined words <span class="tag emulator">emulator</span> [ARES, component/processor/sh2/instructions.cpp, exceptions.cpp].
- **PicoDrive** does not raise slot-illegal. Its interpreter treats every undefined word as a general illegal instruction, and its recompiler only logs a branch in a delay slot as an anomaly <span class="tag emulator">emulator</span> [PICODRIVE, cpu/sh2/mame/sh2.c, cpu/sh2/compiler.c]. Code with a branch in a delay slot can therefore run in PicoDrive and trap on a console.
- **A PC-relative load in a delay slot** reads from the branch target + 2 in both, as the manual says, so code that relies on the load's own position fails in the emulators as it would on a console. ares computes it from the branch target in its interpreter and its recompiler. PicoDrive's interpreter runs the slot with PC already set to the target, and its recompiler uses the branch's target for a `BRA` or `BSR` and works it out at run time for a branch through a register <span class="tag emulator">emulator</span> [ARES, component/processor/sh2/instructions.cpp, recompiler.cpp; PICODRIVE, cpu/sh2/mame/sh2.c, cpu/sh2/mame/sh2pico.c, cpu/sh2/compiler.c].

## Open questions

- Is `TAS.B` safe on a production 32X with both SH-2s contending for SDRAM ([discrepancy 12](../appendices/discrepancies.md))?

## Sources

- [SH-PM](../appendices/bibliography.md#sh-pm): §2 pp.16-19, §3 pp.21-22, §4 pp.23-28, §5 pp.34-47, §6.1 p.59, §6.10 p.72, §6.11 p.74, §6.17-6.19 (examples pp.89-90), §6.26 p.99, §6.29, §6.31, §6.33, §6.36, §6.51 pp.141-142, §6.66 p.161, §6.70, appendix A Table A.51 pp.284-287
- [SH7604](../appendices/bibliography.md#sh7604): §4.5 illegal instructions, §4.6 when exceptions are not accepted, Table 4.9
- [D32XR](../appendices/bibliography.md#d32xr): sh2_draw.s, sh2_fixed.s, doomdef.h, marsnew.c, marsdraw.c, r_data.c, r_local.h, r_phase1.c, r_phase6.c, r_phase8.c, p_base.c, p_maputl.c, p_sight.c, roq_read.c
- [MK2](../appendices/bibliography.md#mk2): SH-2 program
- [AB32X](../appendices/bibliography.md#ab32x): SH-2 code at `0x0600680A`-`0x0600684C`, `0x060082C0`
- [SWA](../appendices/bibliography.md#swa): SH-2 code at `0x060008F2`, `0x06000EE6`, `0x060028D0`
- [ARES](../appendices/bibliography.md#ares): component/processor/sh2/instructions.cpp, exceptions.cpp, recompiler.cpp
- [PICODRIVE](../appendices/bibliography.md#picodrive): cpu/sh2/mame/sh2.c, cpu/sh2/mame/sh2pico.c, cpu/sh2/compiler.c
- [GNU-TOOLS](../appendices/bibliography.md#gnu-tools): GCC 13.2.0 (with 15.1 and 16.2 compared), Binutils (sh-elf-as 2.47 for the delay-slot test)
