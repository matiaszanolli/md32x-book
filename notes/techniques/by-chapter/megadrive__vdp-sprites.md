# Harvested techniques: megadrive/vdp-sprites.md

Target: `megadrive/vdp-sprites.md`. 5 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from AB-DISASM -->
### Sprite link chain rebuilt for H32/H40 and DMAed whole
- Source: AB-DISASM, disasm/modules/68k/game/InitSpriteLinks.asm:1-27 ($000FE2); disasm/modules/68k/game/InitDisplayLayout.asm:1-34 ($0015D6)
- What it does and why it is clever: The RAM sprite table at $FFF08A always has a valid link chain. Link n = n+1 is written into byte 3 of each 8-byte entry, and the last link is 0. The count is 64 or 80 depending on the H40 bit in $FFF01C. The whole table is then DMAed to the SAT at the address in $3E(a5). Game code only edits positions and tiles, never links.
- Key numbers: 64×8 = $100 words (H32) or 80×8 = $140 words (H40).
- Target chapter: megadrive/vdp-sprites.md
- Evidence: code only (shipped)

<!-- from AB-DISASM -->
### Moving a sprite block with two long adds
- Source: AB-DISASM, disasm/modules/68k/game/CmdUpdateSprites.asm:1-35 ($00074A, GameCommand 15)
- What it does and why it is clever: When copying an object's sprite list from ROM, the Y offset is pre-swapped into the high word of D3. Then `add.l d3` on long 0 changes only Y and leaves the size/link word alone. `add.w d2` on long 1 changes only X and leaves the attribute word alone. Each sprite takes two long moves and two adds.
- Key numbers: 8 bytes per sprite; the 128-pixel origin is pre-applied in the ROM data.
- Target chapter: megadrive/vdp-sprites.md
- Evidence: code only (shipped)

<!-- from AB-DISASM -->
### Sprite blinking done entirely in V-blank
- Source: AB-DISASM, disasm/modules/68k/display/DisplayUpdate.asm:1-41 ($001660)
- What it does and why it is clever: Every N frames (reload value $B26), the handler toggles a range of sprites. One phase copies saved Y words from $FFFB3E into the sprite table. The other writes Y = 0, which is off-screen because sprite Y has a 128-pixel origin. It then re-DMAs the table. Blinking markers cost the main loop nothing.
- Key numbers: first sprite and count in $B2B/$B2C; phase in $B2D.
- Target chapter: megadrive/vdp-sprites.md
- Evidence: code only (shipped)

<!-- from AB-DISASM -->
### Flight-path animation by per-frame weighted interpolation
- Source: AB-DISASM, disasm/modules/68k/graphics/AnimateFlightPaths.asm:1-94 ($01ABB0); disasm/modules/68k/math/WeightedAverage.asm:1-40 ($01E346)
- What it does and why it is clever: Each of 4 flight slots (18 bytes each, at $FF153C) holds endpoints, a step counter t and a total T. Every frame the position is computed fresh with WeightedAverage:
  - P = (A×(T−t−1) + B×t) / ((T−t−1) + t)
  - The result is 0 if both weights are 0.

  Recomputing from scratch avoids accumulated error and needs no fixed-point state. The sprite is written as Y+$7C, size $0500 (2×2 cells), X+$7C ($7C = 128 origin − 4). When no slot advanced, the next set of flights is started.
- Key numbers: 4 sprites; 32-bit products through Multiply32 and UnsignedDivide.
- Target chapter: megadrive/vdp-sprites.md (also NEW: Fixed-point maths)
- Evidence: code only (shipped)

<!-- from AB-DISASM -->
### Eased takeoff and landing sprite motion ("DiagonalWipe")
- Source: AB-DISASM, disasm/modules/68k/graphics/DiagonalWipe.asm:1-261 ($01ACBA-$01AEB7); disasm/modules/68k/graphics/TilePlacement.asm:1-40 ($01E044)
- What it does and why it is clever: Despite the name, this moves a 2×2-cell sprite (tile $0750) through TilePlacement / GameCommand 15. Speed comes from integer division instead of a velocity variable:
  - Mode 1 accelerates with step = d/20 + 2, along X, then climbs (Y decreases) with step = d/20 + 1 + 1: a takeoff.
  - Mode 0 descends with ease-out, step = (54 − d)/20 + 1, then rolls out horizontally: a landing.
- Key numbers: distances 20, 34 ($22) and 54 ($36) pixels; one frame per step (GameCommand 14).
- Target chapter: megadrive/vdp-sprites.md
- Evidence: code only (shipped)

---

