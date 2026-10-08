# Harvested techniques: megadrive/vdp-planes.md

Target: `megadrive/vdp-planes.md`. 3 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from AB-DISASM -->
### Band scrolling with per-cell H-scroll (map spin and screen shake)
- Source: AB-DISASM, disasm/modules/68k/game/PackScrollDeltaToVRAM.asm:1-63 ($01D990); disasm/modules/68k/graphics/AnimateScrollEffect.asm:1-117 ($023B6A); disasm/modules/68k/graphics/AnimateScrollWipe.asm:1-81 ($023C9A); disasm/modules/68k/game/SetScrollOffset.asm ($01D8F4)
- What it does and why it is clever: PackScrollDeltaToVRAM switches reg 11 to $02 (one H-scroll entry per 8-line cell row). It zeroes a 2 KB RAM table and writes −offset only into the N cell rows of one plane, every 32 bytes. It then DMAs 1 KB to the H-scroll table at $FC00. Only the 22 map rows move; the status rows stay fixed.
  - AnimateScrollEffect "spins" the 256-px world map: speed goes 1→16 px/frame (one step per 32 px), cruises, then slows 16→1, with position taken mod 256.
  - AnimateScrollWipe is a damped shake: ±16, ±16, then ±15 … ±1, 5 frames per step.
- Key numbers: reg 11 = $02; table at VRAM $FC00; 22 rows ($16); wrap at $100.
- Target chapter: megadrive/vdp-planes.md
- Evidence: code only (shipped)

<!-- from AB-DISASM -->
### Highlighting by nametable read-modify-write
- Source: AB-DISASM, disasm/modules/68k/game/ApplyPaletteShifts.asm:1-75 ($004A66)
- What it does and why it is clever: To recolour a menu region, the game reads the nametable rectangle back from VRAM into a 2 KB stack buffer (GameCommand 28, the V-int readback). It rewrites each cell's palette bits with `andi #$9FFF` and adds pal<<13, then blits the block back (GameCommand 27). No RAM copy of the plane is needed, and tile numbers and flips are preserved.
- Key numbers: up to 1024 cells (2 KB of stack); palette field in bits 14-13.
- Target chapter: megadrive/vdp-planes.md
- Evidence: code only (shipped)

<!-- from AB-DISASM -->
### 9-slice dialog boxes that also set the text window
- Source: AB-DISASM, disasm/modules/68k/graphics/DrawBox.asm:1-242 ($005A04, 42 call sites)
- What it does and why it is clever: The interior is a single rectangle fill (GameCommand 26 DMA). Corners and edges are placed per cell from a consecutive tile run ($8527 TL, $8528 BL, $8529 TR, $852A BR, $852B/$852C left/right edges, $852D/$852E top/bottom edges), stepped with `addq.w #1,(a3)`. All tiles have the priority bit set ($8000), so windows sit above low-priority sprites. The same call stores win_left/top/right/bottom and the text cursor, so following printf calls wrap inside the box.
- Key numbers: 8 border tiles; priority bit $8000; window = box inset by 1 cell.
- Target chapter: megadrive/vdp-planes.md (also NEW: Text and menus with tile planes)
- Evidence: code only (shipped)

---

