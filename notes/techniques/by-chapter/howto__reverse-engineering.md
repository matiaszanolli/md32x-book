# Harvested techniques: howto/reverse-engineering.md

Target: `howto/reverse-engineering.md`. 7 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from VRD/AU/MARSDEV -->
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

<!-- from VRD/AU/MARSDEV -->
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

<!-- from VRD/AU/MARSDEV -->
### Size-neutral hooks and thunks that call game code
- Source: AU-NOTES, KNOWN_ISSUES.md:539-600; ROADMAP.md:1517-1530
- What it does and why it is clever:
  - **Size-neutral swaps:** shared code can only take same-size swaps (6 bytes for 6, 8 for 8). Extra bytes are paid back from provably dead code.
  - **Argument frames:** a thunk that calls a stack-argument routine must re-push the arguments (`move.l n*4(sp),-(sp)` ×n), because its own return address shifts them. Cleanup counts pushes × 4.
  - **Build traps:** a boot-half file missing from the Makefile's include list never rebuilds.
- Key numbers: a +2-byte patch overflowed the cartridge to 2 MB + 2.
- Target chapter: howto/reverse-engineering.md
- Evidence: emulator measured (PicoDrive)

<!-- from VRD/AU/MARSDEV -->
### Verify a consumer reads an address before building on it
- Source: VRD-NOTES, VR60_ROADMAP.md lessons 2026-06-17; KNOWN_ISSUES.md:617-636
- What it does and why it is clever: A render-state patcher was built against addresses taken from stale docs. A memory watch then showed the renderer never reads them. The rule is to confirm reads with watch or dump tools first.
- Key numbers: 0% change in Slave load.
- Target chapter: howto/reverse-engineering.md
- Evidence: invalidated (the patcher is a verified no-op)

<!-- from VRD/AU/MARSDEV -->
### The 32X security block, exactly
- Source: AU-NOTES, tools/extract_mars_init.py:1-60; PORT_ARCHITECTURE.md:455-465
- What it does and why it is clever: The block is 1,040 bytes at `$3F0-$7FF`. It sets ADEN, relocates itself into the fixed window (`lea $6BC / adda.l #$880000 / jmp`), and ends with `bra.b $800`, returning its verdict in the carry flag. The application must start at `$800` with `bcs error`. The block can be lifted from marsdev's `dc.w` source, so no retail ROM is needed.
- Key numbers: byte-identical between retail VRD and marsdev across all 1,040 bytes.
- Target chapter: howto/reverse-engineering.md
- Evidence: code only (byte comparison)

<!-- from VRD/AU/MARSDEV -->
### Assembler disagreements
- Source: VRD-NOTES, KNOWN_ISSUES.md:28-41; AU-NOTES, KNOWN_ISSUES.md:46-55, 578-588
- What it does and why it is clever: VRD reports vasm `bsr.w` landing at target+2. Aerobiz verified `bsr.w` byte-identical across 332 calls with its flags. vasm under `-no-opt` also refuses forward `bra.b`. Always check against ROM bytes.
- Key numbers: see above.
- Target chapter: howto/reverse-engineering.md
- Evidence: disputed between the projects; emulator/MD5 measured on the Aerobiz side

---

<!-- from AB-DISASM -->
### Telling C-compiled code from hand-written assembly, and checking labels
- Source: AB-DISASM, e.g. disasm/modules/68k/game/CalcAffinityScore.asm:6 ("compiler junk" word), disasm/modules/68k/game/CalcOptimalTicketPrice.asm (link/movem/cdecl), compared with disasm/modules/68k/vint/*.asm (register-only, A5 globals)
- What it does and why it is clever:
  - **C-compiled code** has `link a6` frames, cdecl long arguments cleaned with `lea n(sp),sp`, `moveq #0; move.w` zero-extension before every helper call, `ext.l` before pushes, and stray padding words.
  - **The hand-written core** ($0200-$4600) uses fixed register roles (A5 = $FFF010, A4/A3 = VDP ports), RTR returns and PC-relative jump tables.
  - **Labels need checking.** Many function names in this repo were guessed from call sites and are wrong. Confirm a routine's purpose from the ports and RAM it touches; the label list at the top of this report shows how often that matters.
- Key numbers: about 860 functions; the hand-written core is roughly the first 18 KB.
- Target chapter: howto/reverse-engineering.md
- Evidence: code only (shipped)

