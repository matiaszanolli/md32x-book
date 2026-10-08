# Harvested techniques: megadrive/vdp-timing.md

Target: `megadrive/vdp-timing.md`. 6 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from AB-DISASM -->
### V-blank handler as a flag-driven work dispatcher
- Source: AB-DISASM, disasm/modules/68k/vint/VInt_Handler3.asm:97-167 ($0014E6-$0015AF)
- What it does and why it is clever: The handler saves all registers, loads A5 = $FFF010 (globals) and A4 = $C00004, and resets the H-int line counter. It then runs a fixed priority chain, each step gated by a flag the main code sets:
  1. $4B bit 0: CPU copy of 11 colours to CRAM.
  2. $B2A: sprite blink.
  3. $BD4: palette-animation DMA.
  4. $BCE: a C callback through the pointer at $BD0.
  5. $2FB: tile-animation DMA.
  6. $2B: a mutually exclusive bitfield. Bit 0 does a one-shot block copy, bit 1 a multi-frame fill, bit 2 a multi-frame readback.

  It then always polls the controllers and runs four subsystem updates (mouse, D-pad cursor, cursor sprite, input latch). Finally it clears the "frame done" flag $36(a5), which main-loop waits poll.
- Key numbers: about 10 work slots; the flags are bytes, with one word flag.
- Target chapter: megadrive/vdp-timing.md
- Evidence: code only (shipped)

<!-- from AB-DISASM -->
### Stack-overflow guard inside the V-int handler
- Source: AB-DISASM, disasm/modules/68k/vint/VInt_Handler3.asm:98-101 ($0014EA); initial SP in the vectors = $00FFF000 (analysis/ROM_MAP.md:108)
- What it does and why it is clever: Every frame the handler compares SP with $FFE000. If SP is below that, it branches to an emergency stub at $001928 that spins forever, so a recursion bug halts the game visibly instead of corrupting globals. Recursion is real here, for example the recursive IntToDecimalStr. The stack is therefore bounded to 4 KB ($FFE000-$FFF000), sitting just below the RAM DMA stub and the A5 globals.
- Key numbers: 4 KB stack; checked about 60 times a second.
- Target chapter: megadrive/vdp-timing.md (also megadrive/m68k.md)
- Evidence: code only (shipped)

<!-- from AB-DISASM -->
### Synchronous deferral: post to V-int, or run inline if V-int is off
- Source: AB-DISASM, disasm/modules/68k/game/CmdSetupSprite.asm:1-61 ($000550, GameCommand 8); disasm/modules/68k/game/CmdWaitDMA.asm:1-33 ($0009F6, GameCommand 28); disasm/modules/68k/game/CmdWaitFrames.asm ($000724, GameCommand 14)
- What it does and why it is clever: Before posting VDP work, each command checks the reg 1 shadow bit 5 (V-int enabled):
  - If V-int is on, it stores parameters, sets a dispatch bit in $2B(a5) and spins until the V-blank handler clears it.
  - If V-int is off (screen setup), it calls the same handler routine directly. CmdWaitDMA even loops the handler until the multi-frame job finishes.
  - CmdWaitFrames returns at once when V-int is off.

  One API works both during display-off loading and during gameplay, and it cannot deadlock.
- Key numbers: dispatch bits 0/1/2 at A5+$2B; the frame flag is A5+$36.
- Target chapter: megadrive/vdp-timing.md
- Evidence: code only (shipped)

<!-- from AB-DISASM -->
### Multi-frame VRAM fill and readback in V-blank slices
- Source: AB-DISASM, disasm/modules/68k/vint/VInt_Handler2.asm:1-46 ($001390, fill); disasm/modules/68k/vint/VInt_Handler3.asm:1-53 ($001404, readback); disasm/modules/68k/vint/VInt_Handler1.asm:1-29 ($001346)
- What it does and why it is clever: A nametable rectangle is filled with a constant word, or read back into RAM, four rows per V-blank. The handler keeps the running command long at $4E(a5) and adds the plane row stride ($400000 shifted for plane width). It decrements the remaining-row count at $4D(a5) and clears the dispatch flag only when done. Handler1 does a one-shot block in either direction: it tests command bit 30 (CD0) to choose `(a3)->(a0)+` (read) or BulkCopyVDP (write).
- Key numbers: 4 rows per frame (`moveq #3,d7`); width in $4C, rows in $4D.
- Target chapter: megadrive/vdp-timing.md (also patterns/streaming.md)
- Evidence: code only (shipped)

<!-- from AB-DISASM -->
### Per-scanline VSRAM remap in the H-blank handler
- Source: AB-DISASM, disasm/modules/68k/vint/VInt_Handler3.asm:65-90 ($001484-$0014E5); enable flag set by GameCommand 37 (disasm/modules/68k/game/CmdInitGameVars.asm)
- What it does and why it is clever: The handler increments a line counter, which the V-blank handler zeroes. For each plane it writes `table[line] - line` to VSRAM ($40000010 and $40020010), with two table pointers held in RAM. Subtracting the current line means each table entry is simply "which source row to show on this line". That gives vertical stretch, squash or flip with plain tables. The handler masks interrupts and saves only five registers.
- Key numbers: 2 VSRAM writes per H-int; tables pointed to by $C48/$C4C(a5).
- Target chapter: megadrive/vdp-timing.md
- Evidence: code only (shipped; I found the capability but did not trace which screen enables it)

<!-- from AB-DISASM -->
### Low-latency cursor: sprite 0 rewritten by the CPU every V-blank
- Source: AB-DISASM, disasm/modules/68k/vint/SubsysUpdate3.asm:1-38 ($001864)
- What it does and why it is clever: When enabled, the handler adds the scroll offsets to the cursor position at $FFFC74. It rebuilds the four words of sprite 0 in the sprite buffer, re-links the chain, and writes those four words straight to the sprite attribute table ($3E(a5) = SAT base) through the data port. The mouse or pad cursor therefore moves at a full 60 Hz even when the C game logic takes several frames per loop.
- Key numbers: 4 words (8 bytes) per frame.
- Target chapter: megadrive/vdp-timing.md (also megadrive/vdp-sprites.md)
- Evidence: code only (shipped)

---

