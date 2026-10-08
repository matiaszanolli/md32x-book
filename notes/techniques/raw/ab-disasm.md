# Aerobiz Supersonic (Koei, 1994): techniques harvested from the disassembly

All entries below come from reading the shipped code in the byte-identical disassembly at /mnt/data/src/aerobiz-disasm. Paths are relative to /mnt/data/src/aerobiz-disasm unless they are absolute. ROM addresses are from the module headers.

**Several routines have misleading names in the repo, so don't trust the labels.** I describe what the code actually does:
- `ControllerRead` ($000B42) is a tile-animation DMA.
- `DMA_Transfer` ($00163E) is a CPU copy of 11 colours to CRAM.
- `DiagonalWipe` ($01ACBA) moves a 16x16 sprite.
- `TransitionEffect` ($01F7C0) is a route-slot search.
- `FadeGraphics` ($01F82E) is economy code.
- `ResourceLoad` / `ResourceUnload` are guarded palette fades.
- `CmdTestVRAM` ($0007D8) is a controller-port ID probe.
- `CmdSetupSprite` ($000550) is a generic VDP block copy in either direction.
- `ShowRouteInfo` ($00F104) is the save-slot panel.
- `UpdatePassengerDemand` ($00F522) writes the save header.
- `RAM_MAP.md` says `ram_sub` writes to the VDP *data* port and is called by SubsysUpdate1. In the code it writes to the *control* port (A4 = $C00004) and is called by ConfigVDPDMA.

---

## megadrive/vdp-dma.md

### Full 68k-to-VDP DMA sequence (ConfigVDPDMA)
- Source: AB-DISASM, disasm/modules/68k/vdp/ConfigVDPDMA.asm:1-70 ($001198-$001255); helpers disasm/modules/68k/game/DispatchVDPWrite.asm:21-29 (VDPWriteZ80Path $00114A), disasm/modules/68k/game/SetVDPDisplayBit.asm ($00116A), disasm/modules/68k/vdp/WaitVDPAndWrite.asm ($00117A)
- What it does and why it is clever: This is a complete, defensive DMA sequence in one place:
  1. Mask interrupts with `ori #$700,sr`.
  2. Request the Z80 bus, unless the flag at $C70(a5) says not to, so the Z80 cannot touch the 68k bus during the DMA.
  3. Spin until status bit 1 (DMA busy) clears, then set the auto-increment register (reg 15) from a parameter byte.
  4. Rewrite reg 1 from its RAM shadow with bit 5 (V-int enable, IE0) cleared and bit 4 (DMA enable, M1) set.
  5. Write length to regs 19/20 and source>>1 to regs 21/22/23 (masked to $7F, which selects 68k-source mode).
  6. Fire the DMA through the RAM stub (next entry) and poll the busy bit again.
  7. Restore reg 1 with M1 cleared, release the Z80 and restore SR.

  The DMA enable bit is on only during a transfer, so a stray control-port write with CD5 set can never start a DMA by accident.
- Key numbers: register words $93xx/$94xx (length), $95xx/$96xx/$97xx (source); length is in words; the source address is shifted right by 1.
- Target chapter: megadrive/vdp-dma.md
- Evidence: code only (shipped)

### DMA trigger executed from work RAM at $FFF000
- Source: AB-DISASM, disasm/sections/section_000200.asm:57-68 (copy loop at $00034E, stub bytes at $000362-$00036B); call site disasm/modules/68k/vdp/ConfigVDPDMA.asm:53 (`jsr $FFF000`, still encoded as dc.w)
- What it does and why it is clever: At boot the game copies a 10-byte routine (two `move.w $42(a5),(a4)` / `move.w $44(a5),(a4)` plus `rts`) to $FFF000. That is directly above the initial stack pointer, which is also $FFF000. The two halves of the prebuilt VDP command long ($42/$44(a5)) are therefore written to the control port by code fetched from RAM, not ROM. The repo's docs/sega-genesis-reference-sheets.md:65 states the rule: "ROM DMA requires final DMA to be done from RAM". Every DMA in the game (ROM or RAM source) goes through this one stub.
- Key numbers: 10 bytes; command long staged at A5+$42 (A5 = $FFF010, so $FFF052/$FFF054).
- Target chapter: megadrive/vdp-dma.md
- Evidence: code only (shipped)

### First-word rewrite after a RAM-source DMA
- Source: AB-DISASM, disasm/modules/68k/vdp/ConfigVDPDMA.asm:56-66 ($001226-$001242); disasm/modules/68k/vdp/BulkCopyVDP.asm:1-12 ($001386)
- What it does and why it is clever: After the DMA, the routine tests bit 22 of the source address, which is set for any $FFxxxx work-RAM address. If it is set, the routine clears bit 7 (CD5) of the command long, turning it into a plain CPU write to the same destination. It then rewrites the first word by hand through BulkCopyVDP with count 1. This is a cheap guard against a corrupted first word on RAM-source DMA, and it costs only one extra command plus one data write.
- Key numbers: `btst #$16,d0`; one word rewritten; ROM-source DMAs skip it.
- Target chapter: megadrive/vdp-dma.md
- Evidence: code only (shipped)

### One back end for all three DMA modes (68k copy, VRAM fill, VRAM copy)
- Source: AB-DISASM, disasm/modules/68k/game/SelectVDPInit.asm:1-20 ($0015B0); disasm/modules/68k/vdp/ConfigVDPColors.asm:1-39 ($0012DA, fill); disasm/modules/68k/vdp/ConfigVDPScroll.asm:1-48 ($001256, copy); disasm/modules/68k/game/CmdLoadTiles.asm, CmdTransferPlane.asm
- What it does and why it is clever: All three modes share one RAM parameter block (A5+$1D auto-increment, +$1E length, +$20 source, +$24 destination, +$28 fill value).
  - ConfigVDPColors (despite its name) programs reg 23 = $80 (fill mode), writes the destination with CD bits $4000/$0080, then writes the fill word to the data port to start the fill.
  - ConfigVDPScroll programs reg 23 = $C0 (VRAM copy), with regs 21/22 holding the VRAM source and command low bits $00C0.

  A three-bit selector routes a request to the right back end. GameCommands 6 and 7 expose the copy and fill paths to C code.
- Key numbers: reg 23 = $80 for fill and $C0 for copy; 16-bit length.
- Target chapter: megadrive/vdp-dma.md
- Evidence: code only (shipped)

### Rectangle fill and blit by repeated row DMA, stepping the command long
- Source: AB-DISASM, disasm/modules/68k/game/CmdDMABatchWrite.asm:1-70 ($000876, GameCommand 26); disasm/modules/68k/game/CmdDMARowWrite.asm:1-57 ($000944, GameCommand 27); disasm/modules/68k/graphics/ComputeMapCoordOffset.asm ($000816)
- What it does and why it is clever:
  - Fill (cmd 26): there is no 2D fill on the VDP, so the routine lowers A7 by width×2 bytes, fills that temporary stack buffer with the fill word, and DMAs it once per row. It then gives the stack space back.
  - Blit (cmd 27): DMAs one source row per nametable row and advances the source by width×2.
  - In both, the next row's VRAM address is made by adding $00400000 directly to the prebuilt command long (VRAM address bits 13-0 live in bits 29-16). That constant is shifted left once for 64-cell planes and twice for 128-cell planes, based on the reg 16 shadow at $10(a5).
  - ComputeMapCoordOffset turns (plane, column, row) into a nametable byte offset with the same plane-width test.
- Key numbers: row stride $40/$80/$100 bytes for 32/64/128-cell planes; the fill buffer lives on the stack.
- Target chapter: megadrive/vdp-dma.md
- Evidence: code only (shipped)

### Throttled bulk tile upload in 4 KB chunks
- Source: AB-DISASM, disasm/modules/68k/vdp/VRAMBulkLoad.asm:1-79 ($01D568)
- What it does and why it is clever: Large tile sets are split into chunks of $80 tiles: $800 words (4 KB) per DMA. Source and VRAM destination each advance by $1000 bytes, and the routine waits 4 frames (GameCommand 14) between chunks. The remainder goes in one last DMA of n×16 words. A small upload waits n/100 frames. This spreads a big upload over several frames instead of one long stall.
- Key numbers: 4 KB per chunk, a 4-frame gap; tile number × 32 = VRAM byte address.
- Target chapter: megadrive/vdp-dma.md (also patterns/streaming.md)
- Evidence: code only (shipped)

### Animated tiles: per-frame DMA of selected 32-byte frames
- Source: AB-DISASM, disasm/modules/68k/input/ControllerRead.asm:1-62 ($000B42; misnamed)
- What it does and why it is clever: A countdown at $302(a5), reloaded from $300(a5), drives a frame index. The index wraps at the frame count in $2FE(a5). On each tick, a 16-bit enable mask (the AND of $2FC and $304) is shifted right one bit at a time. For each set bit, the routine queues a 16-word (one tile) DMA from that slot's source (frame×32, slot stride $80) to the slot's VRAM address taken from a table at $FFF316. Up to 16 animated tiles (water, lights and so on) update with no CPU pixel copying.
- Key numbers: 16 slots; 32 bytes per frame; each slot's source block is $80 bytes (4 frames).
- Target chapter: megadrive/vdp-dma.md
- Evidence: code only (shipped)

### Palette animation by DMA, only inside V-blank
- Source: AB-DISASM, disasm/modules/68k/vint/VInt_Sub1.asm:1-61 ($000C38); setup disasm/modules/68k/game/CmdInitAnimation.asm ($000BF0)
- What it does and why it is clever: When the delay counter $BE2 reaches 0, the routine computes:
  - source = table + frame × count × 2
  - CRAM address = start index × 2
  - command long = $C0000080 | address bits

  It reads VDP status and fires the CRAM DMA only if bit 3 (V-blank) is set. If the handler has run late into active display, the update is skipped instead of risking CRAM dots on screen. Frame and delay counters wrap at configurable limits.
- Key numbers: `btst #3` on the status word; parameters at A5+$BD5..$BE2.
- Target chapter: megadrive/vdp-dma.md (also megadrive/vdp-color.md)
- Evidence: code only (shipped)

---

## megadrive/vdp-registers.md

### Write-only VDP registers shadowed in RAM
- Source: AB-DISASM, disasm/modules/68k/vdp/CmdSetVDPReg.asm:1-13 ($0003A2); disasm/modules/68k/vdp/CmdGetVDPReg.asm ($00045A); disasm/modules/68k/boot/HardwareInit.asm ($00070A)
- What it does and why it is clever: Every register write `$8RVV` goes through one routine. It sends the word to the control port and also stores VV at A5 + (R & $7F). Since A5 = $FFF010, $FFF010-$FFF027 mirrors registers 0-23. Later code can then change single bits safely:
  - reg 1 V-int and DMA bits in ConfigVDPDMA
  - the reg 16 plane size used for row strides
  - the V-int-enabled test in the sync commands

  GameCommand 2 reads a shadow back for C code.
- Key numbers: 24 shadow bytes; index taken from bits 14-8 of the command word.
- Target chapter: megadrive/vdp-registers.md
- Evidence: code only (shipped)

### Building VDP address commands with shifts and swaps
- Source: AB-DISASM, disasm/modules/68k/graphics/CmdSetupDMA.asm:9-35 ($00047C, GameCommand 5); the same idiom is in InitDisplayLayout.asm, VInt_Sub1.asm, VRAMWriteExtended.asm:8-20 ($0042F0)
- What it does and why it is clever: A 16-bit VRAM address A becomes the 32-bit command with no lookup tables:
  - `((A<<2)&$30000)` swapped gives A15..A14 in the low word.
  - `(A&$3FFF)` swapped gives A13..A0 in the high word.
  - OR in the target code: $40000080 for VRAM DMA, $C0000080 for CRAM DMA, $40000090 for VSRAM DMA, or $40000000 for a CPU write. A read uses $00000000.

  CmdSetupDMA picks among these from a type byte. Learn this idiom once and every routine in the game reads the same way.
- Key numbers: CD bits: VRAM write $4000.0000, CRAM write $C000.0000, VSRAM write $4000.0010, DMA flag $0000.0080.
- Target chapter: megadrive/vdp-registers.md
- Evidence: code only (shipped)

---

## megadrive/vdp-timing.md

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

### Stack-overflow guard inside the V-int handler
- Source: AB-DISASM, disasm/modules/68k/vint/VInt_Handler3.asm:98-101 ($0014EA); initial SP in the vectors = $00FFF000 (analysis/ROM_MAP.md:108)
- What it does and why it is clever: Every frame the handler compares SP with $FFE000. If SP is below that, it branches to an emergency stub at $001928 that spins forever, so a recursion bug halts the game visibly instead of corrupting globals. Recursion is real here, for example the recursive IntToDecimalStr. The stack is therefore bounded to 4 KB ($FFE000-$FFF000), sitting just below the RAM DMA stub and the A5 globals.
- Key numbers: 4 KB stack; checked about 60 times a second.
- Target chapter: megadrive/vdp-timing.md (also megadrive/m68k.md)
- Evidence: code only (shipped)

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

### Multi-frame VRAM fill and readback in V-blank slices
- Source: AB-DISASM, disasm/modules/68k/vint/VInt_Handler2.asm:1-46 ($001390, fill); disasm/modules/68k/vint/VInt_Handler3.asm:1-53 ($001404, readback); disasm/modules/68k/vint/VInt_Handler1.asm:1-29 ($001346)
- What it does and why it is clever: A nametable rectangle is filled with a constant word, or read back into RAM, four rows per V-blank. The handler keeps the running command long at $4E(a5) and adds the plane row stride ($400000 shifted for plane width). It decrements the remaining-row count at $4D(a5) and clears the dispatch flag only when done. Handler1 does a one-shot block in either direction: it tests command bit 30 (CD0) to choose `(a3)->(a0)+` (read) or BulkCopyVDP (write).
- Key numbers: 4 rows per frame (`moveq #3,d7`); width in $4C, rows in $4D.
- Target chapter: megadrive/vdp-timing.md (also patterns/streaming.md)
- Evidence: code only (shipped)

### Per-scanline VSRAM remap in the H-blank handler
- Source: AB-DISASM, disasm/modules/68k/vint/VInt_Handler3.asm:65-90 ($001484-$0014E5); enable flag set by GameCommand 37 (disasm/modules/68k/game/CmdInitGameVars.asm)
- What it does and why it is clever: The handler increments a line counter, which the V-blank handler zeroes. For each plane it writes `table[line] - line` to VSRAM ($40000010 and $40020010), with two table pointers held in RAM. Subtracting the current line means each table entry is simply "which source row to show on this line". That gives vertical stretch, squash or flip with plain tables. The handler masks interrupts and saves only five registers.
- Key numbers: 2 VSRAM writes per H-int; tables pointed to by $C48/$C4C(a5).
- Target chapter: megadrive/vdp-timing.md
- Evidence: code only (shipped; I found the capability but did not trace which screen enables it)

### Low-latency cursor: sprite 0 rewritten by the CPU every V-blank
- Source: AB-DISASM, disasm/modules/68k/vint/SubsysUpdate3.asm:1-38 ($001864)
- What it does and why it is clever: When enabled, the handler adds the scroll offsets to the cursor position at $FFFC74. It rebuilds the four words of sprite 0 in the sprite buffer, re-links the chain, and writes those four words straight to the sprite attribute table ($3E(a5) = SAT base) through the data port. The mouse or pad cursor therefore moves at a full 60 Hz even when the C game logic takes several frames per loop.
- Key numbers: 4 words (8 bytes) per frame.
- Target chapter: megadrive/vdp-timing.md (also megadrive/vdp-sprites.md)
- Evidence: code only (shipped)

---

## megadrive/vdp-planes.md

### Band scrolling with per-cell H-scroll (map spin and screen shake)
- Source: AB-DISASM, disasm/modules/68k/game/PackScrollDeltaToVRAM.asm:1-63 ($01D990); disasm/modules/68k/graphics/AnimateScrollEffect.asm:1-117 ($023B6A); disasm/modules/68k/graphics/AnimateScrollWipe.asm:1-81 ($023C9A); disasm/modules/68k/game/SetScrollOffset.asm ($01D8F4)
- What it does and why it is clever: PackScrollDeltaToVRAM switches reg 11 to $02 (one H-scroll entry per 8-line cell row). It zeroes a 2 KB RAM table and writes −offset only into the N cell rows of one plane, every 32 bytes. It then DMAs 1 KB to the H-scroll table at $FC00. Only the 22 map rows move; the status rows stay fixed.
  - AnimateScrollEffect "spins" the 256-px world map: speed goes 1→16 px/frame (one step per 32 px), cruises, then slows 16→1, with position taken mod 256.
  - AnimateScrollWipe is a damped shake: ±16, ±16, then ±15 … ±1, 5 frames per step.
- Key numbers: reg 11 = $02; table at VRAM $FC00; 22 rows ($16); wrap at $100.
- Target chapter: megadrive/vdp-planes.md
- Evidence: code only (shipped)

### Highlighting by nametable read-modify-write
- Source: AB-DISASM, disasm/modules/68k/game/ApplyPaletteShifts.asm:1-75 ($004A66)
- What it does and why it is clever: To recolour a menu region, the game reads the nametable rectangle back from VRAM into a 2 KB stack buffer (GameCommand 28, the V-int readback). It rewrites each cell's palette bits with `andi #$9FFF` and adds pal<<13, then blits the block back (GameCommand 27). No RAM copy of the plane is needed, and tile numbers and flips are preserved.
- Key numbers: up to 1024 cells (2 KB of stack); palette field in bits 14-13.
- Target chapter: megadrive/vdp-planes.md
- Evidence: code only (shipped)

### 9-slice dialog boxes that also set the text window
- Source: AB-DISASM, disasm/modules/68k/graphics/DrawBox.asm:1-242 ($005A04, 42 call sites)
- What it does and why it is clever: The interior is a single rectangle fill (GameCommand 26 DMA). Corners and edges are placed per cell from a consecutive tile run ($8527 TL, $8528 BL, $8529 TR, $852A BR, $852B/$852C left/right edges, $852D/$852E top/bottom edges), stepped with `addq.w #1,(a3)`. All tiles have the priority bit set ($8000), so windows sit above low-priority sprites. The same call stores win_left/top/right/bottom and the text cursor, so following printf calls wrap inside the box.
- Key numbers: 8 border tiles; priority bit $8000; window = box inset by 1 cell.
- Target chapter: megadrive/vdp-planes.md (also NEW: Text and menus with tile planes)
- Evidence: code only (shipped)

---

## megadrive/vdp-sprites.md

### Sprite link chain rebuilt for H32/H40 and DMAed whole
- Source: AB-DISASM, disasm/modules/68k/game/InitSpriteLinks.asm:1-27 ($000FE2); disasm/modules/68k/game/InitDisplayLayout.asm:1-34 ($0015D6)
- What it does and why it is clever: The RAM sprite table at $FFF08A always has a valid link chain. Link n = n+1 is written into byte 3 of each 8-byte entry, and the last link is 0. The count is 64 or 80 depending on the H40 bit in $FFF01C. The whole table is then DMAed to the SAT at the address in $3E(a5). Game code only edits positions and tiles, never links.
- Key numbers: 64×8 = $100 words (H32) or 80×8 = $140 words (H40).
- Target chapter: megadrive/vdp-sprites.md
- Evidence: code only (shipped)

### Moving a sprite block with two long adds
- Source: AB-DISASM, disasm/modules/68k/game/CmdUpdateSprites.asm:1-35 ($00074A, GameCommand 15)
- What it does and why it is clever: When copying an object's sprite list from ROM, the Y offset is pre-swapped into the high word of D3. Then `add.l d3` on long 0 changes only Y and leaves the size/link word alone. `add.w d2` on long 1 changes only X and leaves the attribute word alone. Each sprite takes two long moves and two adds.
- Key numbers: 8 bytes per sprite; the 128-pixel origin is pre-applied in the ROM data.
- Target chapter: megadrive/vdp-sprites.md
- Evidence: code only (shipped)

### Sprite blinking done entirely in V-blank
- Source: AB-DISASM, disasm/modules/68k/display/DisplayUpdate.asm:1-41 ($001660)
- What it does and why it is clever: Every N frames (reload value $B26), the handler toggles a range of sprites. One phase copies saved Y words from $FFFB3E into the sprite table. The other writes Y = 0, which is off-screen because sprite Y has a 128-pixel origin. It then re-DMAs the table. Blinking markers cost the main loop nothing.
- Key numbers: first sprite and count in $B2B/$B2C; phase in $B2D.
- Target chapter: megadrive/vdp-sprites.md
- Evidence: code only (shipped)

### Flight-path animation by per-frame weighted interpolation
- Source: AB-DISASM, disasm/modules/68k/graphics/AnimateFlightPaths.asm:1-94 ($01ABB0); disasm/modules/68k/math/WeightedAverage.asm:1-40 ($01E346)
- What it does and why it is clever: Each of 4 flight slots (18 bytes each, at $FF153C) holds endpoints, a step counter t and a total T. Every frame the position is computed fresh with WeightedAverage:
  - P = (A×(T−t−1) + B×t) / ((T−t−1) + t)
  - The result is 0 if both weights are 0.

  Recomputing from scratch avoids accumulated error and needs no fixed-point state. The sprite is written as Y+$7C, size $0500 (2×2 cells), X+$7C ($7C = 128 origin − 4). When no slot advanced, the next set of flights is started.
- Key numbers: 4 sprites; 32-bit products through Multiply32 and UnsignedDivide.
- Target chapter: megadrive/vdp-sprites.md (also NEW: Fixed-point maths)
- Evidence: code only (shipped)

### Eased takeoff and landing sprite motion ("DiagonalWipe")
- Source: AB-DISASM, disasm/modules/68k/graphics/DiagonalWipe.asm:1-261 ($01ACBA-$01AEB7); disasm/modules/68k/graphics/TilePlacement.asm:1-40 ($01E044)
- What it does and why it is clever: Despite the name, this moves a 2×2-cell sprite (tile $0750) through TilePlacement / GameCommand 15. Speed comes from integer division instead of a velocity variable:
  - Mode 1 accelerates with step = d/20 + 2, along X, then climbs (Y decreases) with step = d/20 + 1 + 1: a takeoff.
  - Mode 0 descends with ease-out, step = (54 − d)/20 + 1, then rolls out horizontally: a landing.
- Key numbers: distances 20, 34 ($22) and 54 ($36) pixels; one frame per step (GameCommand 14).
- Target chapter: megadrive/vdp-sprites.md
- Evidence: code only (shipped)

---

## megadrive/vdp-color.md

### Subtractive palette fade (FadePalette)
- Source: AB-DISASM, disasm/modules/68k/display/FadePalette.asm:1-113 ($004BC6); drivers disasm/modules/68k/graphics/DrawLayersForward.asm ($004D04), DrawLayersReverse ($004CB6), disasm/modules/68k/display/FadeInAndWait.asm ($03B3DA)
- What it does and why it is clever: The routine unpacks the Mega Drive colour format `0000BBB0GGG0RRR0` into three 3-bit channels. With level L from 0 to 7, each channel becomes max(0, c − (7 − L)). The result is repacked into a 64-colour stack buffer and uploaded. Subtracting instead of scaling needs no multiply, and it fades in exactly 8 steps. Dim channels reach black first, which gives a slight warm/cool tint shift. FadeInAndWait returns early if a button is pressed.
- Key numbers: 8 levels; channel masks $0E00/$00E0/$000E; up to 64 colours.
- Target chapter: megadrive/vdp-color.md
- Evidence: code only (shipped)

### 8-step cross-fade to a target palette that converges together
- Source: AB-DISASM, disasm/modules/68k/graphics/RenderColorTileset.asm:1-152 ($03B9D4)
- What it does and why it is clever: Each step moves each channel by at most 1 toward the target. Decreases start immediately. An increase happens only when the target is greater than (7 − step), so a brightening channel starts late enough to arrive exactly on step 7. All brightening finishes on the same frame without any division.
- Key numbers: 8 steps; channel range 0-7.
- Target chapter: megadrive/vdp-color.md
- Evidence: code only (shipped)

### Colour shimmer from a sliding window over a gradient table
- Source: AB-DISASM, disasm/modules/68k/game/InitAnimTable.asm:1-60 ($001CA0, table BlueAnimPalette $001D1A); disasm/modules/68k/game/UpdateAnimTimer.asm:1-20 ($001D58); disasm/modules/68k/vdp/DMA_Transfer.asm:1-14 ($00163E)
- What it does and why it is clever: The boot logo animates by copying an 11-colour window of a 31-entry blue gradient (bright → dark → bright) into a RAM buffer. The window start moves back one entry every 2 frames. V-blank sends the window to CRAM byte $0004 (colours 2-12) with a CPU loop. The loop also detects controllers and exits on any button, including mouse buttons, or after 300 iterations.
- Key numbers: 31 entries, an 11-word window; command $C0040000.
- Target chapter: megadrive/vdp-color.md
- Evidence: code only (shipped)

### Recolouring pixels in tile data, one nibble at a time
- Source: AB-DISASM, disasm/modules/68k/game/ApplyPaletteMask.asm:1-58 ($0048D2)
- What it does and why it is clever: Before upload, each 16-bit word of 4bpp tile data is tested nibble by nibble against a mask table at $04735E. Any pixel equal to colour index `from` is replaced with `to`, by shifting both 4 bits per nibble. One tile set can show per-player colours without separate artwork.
- Key numbers: 4 nibbles per word; 16 words per tile.
- Target chapter: megadrive/vdp-color.md
- Evidence: code only (shipped)

---

## megadrive/z80.md

### Loading the Z80 driver with bus request and reset
- Source: AB-DISASM, disasm/modules/68k/sound/Z80_SoundInit.asm:1-34 ($00260A); disasm/modules/68k/sound/Z80_RequestBus.asm ($002662), Z80_ReleaseBus.asm ($002678); disasm/modules/68k/vdp/VDP_Init4.asm ($0010FE)
- What it does and why it is clever: This is the textbook sequence:
  1. Mask interrupts.
  2. Request the bus ($A11100 = $100) and assert reset ($A11200 = $100).
  3. Spin on bit 0 until the bus is granted.
  4. Copy the driver from ROM into $A00000 one byte at a time.
  5. Write reset = 0, bus = 0, reset = $100, so the Z80 restarts at $0000 with the new code.

  Driver size is computed from two PC-relative labels. The `dbra` uses the byte count without subtracting 1, so one extra byte is copied; this is harmless.
- Key numbers: driver $002696-$003BE7, 5458 bytes, in 8 KB of Z80 RAM.
- Target chapter: megadrive/z80.md
- Evidence: code only (shipped)

### Z80 held off the bus during DMA and controller reads
- Source: AB-DISASM, disasm/modules/68k/vdp/ConfigVDPDMA.asm:6-8,66-68; disasm/modules/68k/input/InitInputArrays.asm:9-24 (ControllerPoll $00192E); disasm/modules/68k/game/CmdTestVRAM.asm ($0007D8)
- What it does and why it is clever: The game requests the Z80 bus around every 68k-to-VDP DMA and around every I/O port read sequence, then releases it right afterwards. During a DMA the VDP owns the 68k bus, and a Z80 bank-window access at that moment is unsafe. The pad port handshakes are timing-sensitive, so they are also done with the Z80 parked. A flag at $C70(a5) lets callers skip the request when they already own the bus.
- Key numbers: $A11100 = $100 to request and $0000 to release; poll bit 8 (word read) or bit 0 (byte).
- Target chapter: megadrive/z80.md
- Evidence: code only (shipped)

### Mailbox command protocol with handshake and return byte
- Source: AB-DISASM, disasm/modules/68k/sound/CmdSendZ80Param.asm:1-126 ($0024B8-$002609; GameCommands 18-25); disasm/modules/68k/sound/Z80_Delay.asm:1-12 ($002688)
- What it does and why it is clever: The protocol has four steps:
  1. A 3-byte parameter goes into Z80 RAM $0004-$0006 (big-endian, written backwards with `ror.l #8`), or a single byte into $0008.
  2. The command code (GameCommand − 18) goes into $0007, and the busy flag $000D is set to 2.
  3. The 68k releases the bus, busy-waits, re-requests the bus and polls until the Z80 clears $000D.
  4. It returns the byte at $000E.

  The 68k never holds the bus while the Z80 works, and every command gets an acknowledgement and a result.
- Key numbers: delay = 6350 `dbra` loops ≈ 63.5k cycles ≈ 8.3 ms at 7.67 MHz (the repo comment says ~5 ms); mailbox at $0004-$000E.
- Target chapter: megadrive/z80.md (also megadrive/sound.md)
- Evidence: code only (shipped)

---

## megadrive/sound.md

### Uploading voice tables and per-channel data blocks
- Source: AB-DISASM, disasm/modules/68k/sound/CmdSendZ80Param.asm:37-104 (CmdLoadZ80Tables $00250A, CmdLoadZ80Encoded $002568)
- What it does and why it is clever: There are two upload commands:
  - GameCommand 22 copies up to three 39-byte records into Z80 RAM at $003B, $0062 and $0089, skipping empty slots. It builds a "present" bitmask (`asl` then `addi #1`) that goes into $0008. These are most likely FM voice patches, though that is my inference.
  - GameCommand 23 packs three 16-byte per-channel slots at $00B0. The source stream is made of 3-byte groups, ended by a byte ≥ $FC. $FF continues the stream; anything else is copied as the terminator. A slot is capped at 13 bytes, and $FE is forced as the end marker.

  The 68k pre-formats data so the Z80 driver only reads fixed-size slots.
- Key numbers: 3×39 bytes; 3×16 bytes; terminators $FC-$FF.
- Target chapter: megadrive/sound.md
- Evidence: code only (shipped)

---

## megadrive/io.md

### Standard peripheral-ID detection and dispatch
- Source: AB-DISASM, disasm/modules/68k/input/ReadPortByte.asm ($00195C); disasm/modules/68k/input/InputCaseDispatch.asm ($00198E); disasm/modules/68k/game/CountInputBits.asm ($0019CA)
- What it does and why it is clever: The port is driven to TH=1 ($70), then TH=0 ($30). Each read contributes two ID bits: (Left|Right) ≠ 0 and (Up|Down) ≠ 0, giving the 4-bit Sega peripheral ID. Then `(ID & $E) * 2` indexes a table of `bra.w` entries:
  - ID $D: control pad (3- or 6-button)
  - ID 3: Sega Mouse
  - ID 7: Team Player multitap
  - ID $F: nothing connected
- Key numbers: 8 dispatch slots, 4 bytes each.
- Target chapter: megadrive/io.md
- Evidence: code only (shipped)

### 6-button pad detection by extra TH pulses
- Source: AB-DISASM, disasm/modules/68k/input/ReadMultiNibbles.asm:1-59 ($001A20); disasm/modules/68k/util/WritePortToggle.asm ($0019E8)
- What it does and why it is clever: The routine toggles TH up to three times with 4 NOPs of settle time per edge. A TH-low read with U/D/L/R all zero identifies a 6-button pad. Then the base buttons are packed as `(lowread<<2 & $C0) | (highread & $3F)`, inverted, and stored. The extra X/Y/Z/Mode nibble goes into a second slot with type 1. A 3-button pad is stored as type 0, and an empty port as type $F.
- Key numbers: 3 TH cycles maximum; 4 NOPs ≈ 16 cycles settle.
- Target chapter: megadrive/io.md
- Evidence: code only (shipped)

### Sega Mouse and Team Player handshake with timeouts
- Source: AB-DISASM, disasm/modules/68k/input/WaitInputReady.asm ($001AA2); disasm/modules/68k/game/ParseInputData.asm ($001AD4); disasm/modules/68k/game/ParseInputExtended.asm:1-35 ($001B22); disasm/modules/68k/input/InputStateMachine.asm ($001B70); disasm/modules/68k/input/PollInputStatus.asm ($001C6C); disasm/modules/68k/input/WaitInputZero.asm ($001C86)
- What it does and why it is clever:
  - The TR/TL nibble handshake toggles TR ($20/$00) and waits for TL (bit 4). PollInputStatus flips a phase bit in D6, so consecutive calls wait for the alternate edge.
  - Every wait is a `dbne` / `dbeq` with D7 = $FF and returns carry on timeout, so an unplugged device cannot hang the game.
  - Mouse packets are decoded with sign and overflow flags: the X/Y bytes become 9-bit signed (−$100 when the sign bit is set), are clamped to 0 on overflow, and Y is negated.
  - The Team Player path reads four device-type nibbles and then parses each sub-port by type (0 = 3-button, 1 = 6-button, 2 = mouse).
- Key numbers: 255-iteration timeouts; 8 input records of 10 bytes (2 ports × 4 sub-ports) at $FFFC06.
- Target chapter: megadrive/io.md
- Evidence: code only (shipped)

### Edge detection in three instructions, plus a sticky press latch
- Source: AB-DISASM, disasm/modules/68k/util/XorAndUpdate.asm ($001A14); disasm/modules/68k/vint/SubsysUpdate4.asm:1-32 ($0018D0); disasm/modules/68k/input/ReadInput.asm ($01E1EC); disasm/modules/68k/input/CmdReadInput.asm ($00060C)
- What it does and why it is clever:
  - XorAndUpdate stores the held byte and the newly pressed byte as `pressed = (old XOR new) AND new`.
  - Every V-blank, SubsysUpdate4 ORs pressed<<8 | held for both ports into a long latch at $BE8(a5), filtered by an enable mask at $BE4. A tap shorter than one game-loop iteration is never lost, even when the C code runs at a low frame rate.
  - ReadInput returns pressed, held, or pressed|held depending on its argument.
- Key numbers: port B in the high word; mask at $FFA790.
- Target chapter: megadrive/io.md
- Evidence: code only (shipped)

### Cursor control: mouse speed divisor and D-pad acceleration
- Source: AB-DISASM, disasm/modules/68k/vint/SubsysUpdate1.asm:1-50 ($0016D4); disasm/modules/68k/vint/SubsysUpdate2.asm:1-101 ($00175C); defaults disasm/modules/68k/boot/Init6.asm ($001090)
- What it does and why it is clever:
  - Mouse (type 2): the cursor moves by delta / (3 XOR speed), so a speed setting of 0/1/2 gives a divisor of 3/2/1. The result is clamped to a bounds box (default 0-255 × 0-223) and the mouse buttons are merged into click flags.
  - D-pad: a hold timer reloads to 32 when no direction is held. For the first 16 frames of a hold the cursor moves 1 px/frame, then 2 + speed, then 3 + speed when the timer runs out.

  Fine positioning and fast travel both work without a separate menu.
- Key numbers: timer 32 frames, 16-frame first stage; start position (128, 112).
- Target chapter: megadrive/io.md
- Evidence: code only (shipped)

---

## megadrive/cartridge.md

### Save RAM format: odd-byte stride, header, additive checksum
- Source: AB-DISASM, disasm/modules/68k/game/PackSaveState.asm:407-441 ($00EB28, finalize); disasm/modules/68k/game/UpdatePassengerDemand.asm:1-20 ($00F522, header writer); disasm/modules/68k/util/VerifyChecksum.asm:1-35 ($00F552); disasm/modules/68k/math/ByteSum.asm ($01D6FC); disasm/modules/68k/memory/CopyBytesToWords.asm ($01E0E0), CopyAlternateBytes.asm ($01E0FE)
- What it does and why it is clever:
  - The save image is built in RAM at $FF1804. The header word at +2 is a 16-bit sum of the payload bytes, the word at +4 is the payload length, and the payload starts at +6.
  - It is written with stride 2 to SRAM at $200003 + slot × $2000, so only odd addresses (the byte-wide SRAM lane) are used. Starting at $200003 skips the first SRAM byte, which follows Sega's manual: "important data must not be stored in the first word" (docs/genesis-software-development-manual.md:754).
  - Loading reads the image back with the inverse stride, recomputes the sum and compares it with the header.
- Key numbers: 8 KB of SRAM address space; $1000 data bytes per slot; 16-bit sum.
- Target chapter: megadrive/cartridge.md
- Evidence: code only (shipped)

### Compact save serialisation: stride compaction, field trimming, 2-bit packing
- Source: AB-DISASM, disasm/modules/68k/game/PackSaveState.asm:18-406 ($00EB28-$00EF91; city loop at 279, route loop at 315); disasm/modules/68k/game/UnpackPixelData.asm:1-34 ($00EFC8)
- What it does and why it is clever: The serialiser saves the state in a smaller form than it uses in RAM:
  - The C code stores many byte arrays as one byte per word. The serialiser saves only the meaningful byte: 89 cities × 4 entries and the event and table blocks.
  - For each of the 4×40 route slots it saves only the first 12 of 20 bytes; the rest can be recomputed.
  - A 228-entry table of 2-bit values (4 players × 57) is unpacked LSB-first, four per byte, at $FF05C4.
- Key numbers: route slots 3200 bytes in RAM vs 1920 bytes saved; 57 → 228 for the 2-bit table.
- Target chapter: megadrive/cartridge.md (also patterns/case-study-aerobiz.md)
- Evidence: code only (shipped)

### Region lockout screen drawn with a built-in 1bpp font
- Source: AB-DISASM, disasm/modules/68k/boot/EarlyInit.asm:10-30 (region check $003BE8), 154-188 (WriteVDPTileRow $003CE0)
- What it does and why it is clever: The routine reads $A10001 bits 7-6, maps them through the 4-byte table "J,0,U,E", and looks for that letter in the header region field at $1F0-$1FF. If there is no match, it sets up a minimal VDP and prints "DEVELOPED FOR USE ONLY WITH … SYSTEMS." using an ASCII−$20 tile mapping. The address is computed as row×$80 + col×2 plus $40000003. Then it halts.
- Key numbers: 59 glyphs; region letters at $1F0.
- Target chapter: megadrive/cartridge.md
- Evidence: code only (shipped)

---

## howto/md-hello.md

### Expanding 1bpp to 4bpp with a self-restoring rotating mask
- Source: AB-DISASM, disasm/modules/68k/boot/EarlyInit.asm:54-70 ($003C4A-$003C74)
- What it does and why it is clever: The mask register D2 starts at $10000000. For each of 8 pixels it does `rol.l #4,d2`, then `ror.b #1,d1` to shift the next source bit into carry, then `or.l d2,d4` if the bit was set. After 8 rotations of 4 bits, D2 is back to $10000000, so it never needs reloading. Each set bit becomes colour index 1. The repo comment calls this a cycling palette, but the data is a single nibble that walks through positions. One long goes to the data port per row.
- Key numbers: 8 bytes → 32 bytes per tile; 59 tiles; no lookup table.
- Target chapter: howto/md-hello.md
- Evidence: code only (shipped)

### Minimal VDP clear and init
- Source: AB-DISASM, disasm/modules/68k/vdp/VDP_Init1.asm:1-26 ($001036); disasm/modules/68k/vdp/VDP_Init2.asm ($00101C); disasm/modules/68k/vdp/VDP_Init3.asm ($00107A); disasm/modules/68k/boot/Init5.asm ($0010DA)
- What it does and why it is clever:
  - VDP_Init1 sets auto-increment to 2, then clears VRAM with 32768 word writes ($40000000), CRAM with 64 ($C0000000) and VSRAM with 40 ($40000010).
  - VDP_Init2 zeroes the RAM sprite table and relinks it.
  - VDP_Init3 sets all three port control registers to $40 (TH as output).
  - Init5 uploads 800 words of boot tiles to VRAM 0.

  Each step is a single small loop.
- Key numbers: 32768/64/40 words.
- Target chapter: howto/md-hello.md
- Evidence: code only (shipped)

---

## NEW: Compression on the Mega Drive

### Koei LZSS with an interleaved bit stream
- Source: AB-DISASM, disasm/modules/68k/boot/EarlyInit.asm:293-516 (LZ_Decompress $003FEC-$00423F; bit reader $003F72 is still dc.w at lines ~280-292); /mnt/data/src/aerobiz-ultimate/tools/lz_decompress.py:1-138 (reference implementation)
- What it does and why it is clever:
  - **Literal flags.** A control byte supplies 8 flags, MSB first; 1 means a literal byte. The byte is shifted with `add.b x,x` on itself.
  - **One stream.** Control bytes, literals and 16-bit little-endian bit-reservoir words all come in order from the same pointer, so the encoder interleaves them and needs no side streams.
  - **Lengths.** A match's length uses an Elias-gamma code: "1" = 1, "01x" = 2-3, "001xx" = 4-7, and so on up to 7 zero bits. The escape "0000000" is followed by 7 bits with a +$80 bias, and $FF there means end of stream. The match copies v+1 bytes.
  - **Distances.** A hand-tuned prefix code: 0-3 in 6 bits, 4-7 in 7, 8-31 in 8 (a 24-value bucket), 32-127 in 9, 128-255 in 10, 256-511 in 11, 512-1023 in 12, 1024-2047 in 13, 2048-4095 in 14. The source is out − d − 1.
  - **Bit reader.** It keeps a 16-bit window; read_bits(n) shifts in n bits through a mask table at $04684C.
- Key numbers: 4 KB window; match length 2-255; 123 call sites; the aerobiz-ultimate notes measure it at 11.93% of gameplay frames.
- Target chapter: NEW: Compression on the Mega Drive
- Evidence: code only (shipped)

### Decompressing straight into VRAM, using VRAM as the history window
- Source: AB-DISASM, disasm/modules/68k/game/DecompressVDPTiles.asm:7-292 ($004342-$0045B1); disasm/modules/68k/vdp/VRAMWriteExtended.asm:1-34 ($0042F0); disasm/modules/68k/vdp/VRAMWriteWithMode.asm:1-25 ($0042BA); disasm/modules/68k/vdp/WriteColorBitsVRAM.asm:1-50 ($004240, bit reader with mask table $04686E)
- What it does and why it is clever: This is the same format with a different output path, so no RAM buffer is needed.
  - Literals and match bytes are written one at a time by read-modify-write of the containing VRAM word: set the read address (even), read the word, merge the byte into the high or low half by address parity, set the write address, write the word back.
  - Back-references read from VRAM through a byte-read helper.
  - Every access masks interrupts so the V-int handler cannot disturb the VDP address latch.

  It is slow, at 4 control/data accesses per byte, so it is used only 3 times, for example to reload the font to VRAM $4000. In exchange it can unpack data larger than free RAM.
- Key numbers: zero RAM window; 1 byte of output per read-modify-write cycle.
- Target chapter: NEW: Compression on the Mega Drive
- Evidence: code only (shipped)

---

## NEW: Text and menus with tile planes

### Two-row line buffer: 8x8 and 8x16 fonts, word wrap, escape codes
- Source: AB-DISASM, disasm/modules/68k/game/FindCharInSet.asm:51-587 (RenderTextBlock $03ACDC); disasm/modules/68k/graphics/RenderTextLine.asm:1-64 ($03ABA6); disasm/modules/68k/text/PrintfDirect.asm:35-65 (PrintfNarrow $03B246 / PrintfWide $03B270)
- What it does and why it is clever: Text is turned into nametable words in two parallel stack buffers, one per tile row.
  - Narrow mode emits tile = char − $20 (attribute $0404, or $8404 for high priority).
  - "Wide" mode emits tile = char×2 + $19 into the first buffer and that tile + 1 into the second, which makes 8×16 glyphs with a line pitch of 2.
  - At flush time the lower row is moved to sit right after the upper row, and the 2-row block goes out in one GameCommand 27 rectangle DMA.
  - Word wrap looks ahead to measure the next word against the window's right edge; a space at the wrap point is dropped.
  - Escape codes: ESC = y x (each +$20) positions the cursor; ESC R/E set the left/right margins; G, W and M are input and wait helpers; P toggles priority.
- Key numbers: 33-word row buffers ($42 bytes); cursor coordinates taken mod 32.
- Target chapter: NEW: Text and menus with tile planes
- Evidence: code only (shipped)

### Compact vsprintf with tile-aware width and money suffix
- Source: AB-DISASM, disasm/modules/68k/text/Vsprintf.asm:1-337 ($03AFF2; currency at 290-297); disasm/modules/68k/text/IntToDecimalStr.asm:1-38 ($03AA02)
- What it does and why it is clever: The formatter handles %d/%u/%x/%s/%c, width, precision, `-` and 0 padding. Two extras matter for a tile UI:
  - `%w` doubles the width and precision so columns line up in the 2-row font.
  - `$` prefixes "$" and appends "0K". Money is stored in units of $10,000, so "$1230K" prints with no 32-bit multiply by 1000. `$$` leaves out the suffix.

  Decimal conversion is recursive: print n/10, then the digit n%10. That is the main reason the V-int stack guard exists.
- Key numbers: 152-byte local output buffer; default precision 6.
- Target chapter: NEW: Text and menus with tile planes
- Evidence: code only (shipped)

### Two digits in one 8×8 tile using a half-row-offset read
- Source: AB-DISASM, disasm/modules/68k/math/RoundValue.asm:5-67 ($01DF30; misnamed); digit glyphs DigitFontTiles $048E00
- What it does and why it is clever: To show 0-99 in a single cell, the routine ORs two glyphs together, 8 longs each. The units glyph is read aligned. The tens glyph is read from glyph address + 2 bytes. With 4-byte tile rows, that misaligned read moves the right half of each row into the left half. The digits are 4 px wide and drawn in the right half of their tiles, so the result is "tens | units" in one tile, with no shifting code. A zero tens digit uses a blank glyph (tile 10).
- Key numbers: 32 bytes per output tile; 8 OR operations.
- Target chapter: NEW: Text and menus with tile planes
- Evidence: code only (shipped)

---

## NEW: Software rendering into tile memory

### A 256×176 map stored as unique tiles, with Bresenham line drawing
- Source: AB-DISASM, disasm/modules/68k/graphics/DrawTilemapLine.asm:1-274 ($01DA34); disasm/modules/68k/graphics/DrawRouteLines.asm:1-80 ($0098D2); disasm/modules/68k/graphics/LoadScreenGfx.asm:6-44 ($0068CA)
- What it does and why it is clever:
  - The world map is LZ-decompressed into RAM as 704 unique tiles (32×22). This makes it a linear 4bpp bitmap with byte address = (x>>3)×32 + ((x>>2)&1)×2 + (y>>3)×$400 + (y&7)×4.
  - Pixels are plotted with an AND mask from the table at $05F9B6 and an OR of the colour. The colour is pre-shifted into the four nibble positions (<<12, <<8, <<4, <<0) and selected by x&3.
  - Integer Bresenham steps along the major axis.
  - Each player's route is coloured 1 or 2 depending on whether it is profitable.
  - The finished bitmap is uploaded as $2C0 tiles and shown with a static nametable.
- Key numbers: 22,528-byte canvas ($5800); 40 routes per player; x wraps mod 256.
- Target chapter: NEW: Software rendering into tile memory
- Evidence: code only (shipped)

### Shortest-path line wrap on a cylindrical map, plus a one-line data patch
- Source: AB-DISASM, disasm/modules/68k/graphics/DrawTilemapLineWrap.asm:5-70 ($01DC26)
- What it does and why it is clever: The map wraps horizontally at 256 px. If $100 − dx is smaller than dx, the line is drawn the other way round the globe: dx becomes $100 − dx and x0 is shifted by +256, with each plotted x reduced mod 256. So Pacific routes wrap across the seam. Both line routines also contain a hard-coded check: when the endpoints are exactly (32,34)→(220,102), y0 is decremented. That fixes the look of one specific route in code instead of in the data.
- Key numbers: wrap width $100.
- Target chapter: NEW: Software rendering into tile memory (also howto/reverse-engineering.md)
- Evidence: code only (shipped)

---

## megadrive/m68k.md

### 32×32 multiply from three MULU.W, skipping zero halves
- Source: AB-DISASM, disasm/modules/68k/math/Multiply32.asm:1-30 ($03E05C, 204 calls)
- What it does and why it is clever: The low 32 bits of the product are a_lo×b_lo + ((a_hi×b_lo + a_lo×b_hi) << 16). The a_hi×b_hi term can only affect bits 32 and up, so it is never computed. Each cross product is skipped when its high word is 0, which is the common case for game values, so most calls cost a single MULU.
- Key numbers: 1-3 MULU.W (about 70 cycles each at most).
- Target chapter: megadrive/m68k.md
- Evidence: code only (shipped)

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

### Overlap-safe memmove
- Source: AB-DISASM, disasm/modules/68k/game/DecompressVDPTiles.asm:294-324 (MemMove $0045B2)
- What it does and why it is clever: The routine compares source and destination pointers. If source ≤ destination it copies backwards with `-(a0),-(a1)`, otherwise forwards. That is the minimal correct memmove. The text engine relies on it to shift its row buffers in place.
- Key numbers: 16-bit count.
- Target chapter: megadrive/m68k.md
- Evidence: code only (shipped)

---

## patterns/streaming.md

### Spreading big VRAM jobs over frames
- Source: AB-DISASM, disasm/modules/68k/vdp/VRAMBulkLoad.asm:1-79 ($01D568); disasm/modules/68k/vint/VInt_Handler2.asm / VInt_Handler3.asm ($001390 / $001404)
- What it does and why it is clever: Two complementary ways to bound work per frame:
  - Uploads are cut into 4 KB DMA chunks, with frame waits in between.
  - Nametable fills and readbacks are capped at 4 rows per V-blank by the handler itself, which resumes from a saved command long the next frame.

  Both keep each V-blank's VDP work small, so music and input stay smooth while large screens load.
- Key numbers: 4 KB per chunk; 4 rows per frame.
- Target chapter: patterns/streaming.md
- Evidence: code only (shipped)

---

## patterns/case-study-aerobiz.md

### A trap-style "BIOS": GameCommand, 47 assembly services called from C
- Source: AB-DISASM, disasm/modules/68k/game/GameCommand.asm:1-46 ($000D64, 306 call sites)
- What it does and why it is clever: The C-compiled game logic pushes long arguments and calls one entry point with a command number.
  - The entry saves SR before LINK, loads A5 = $FFF010 and A4 from a 47-entry jump table, and returns with RTR.
  - An out-of-range number locks up deliberately.
  - Handlers cover VDP register access, DMA, rectangle fill and blit, sprites, input, Z80 mailbox commands, frame waits, and so on.

  This splits hardware code from portable game code: Koei's PC-98 title becomes C plus a small hand-written Mega Drive back end.
- Key numbers: 47 handlers; arguments start at $E(a6).
- Target chapter: patterns/case-study-aerobiz.md
- Evidence: code only (shipped)

### One shared scratch arena for mutually exclusive screens
- Source: AB-DISASM, analysis/RAM_MAP.md:250-270 ($FF1804); users: disasm/modules/68k/graphics/LoadScreenGfx.asm:11-19, disasm/modules/68k/game/PackSaveState.asm:22-25, disasm/modules/68k/game/PackScrollDeltaToVRAM.asm:9-15, disasm/modules/68k/game/DecompressGraphicsData.asm:8-9
- What it does and why it is clever: The block at $FF1804 is reused for different jobs on different screens:
  - the LZ output buffer
  - the 22.5 KB map bitmap canvas
  - the save image (header + payload)
  - the H-scroll table builder (at +$5000)
  - portrait decompression

  Only one of these screens is ever active, so there is no allocator: each screen owns the arena while it runs. That is static overlaying, and it is how a 64 KB machine runs a large strategy game.
- Key numbers: at least $5800 bytes for the map canvas, plus the +$5000 H-scroll area.
- Target chapter: patterns/case-study-aerobiz.md
- Evidence: code only (shipped)

### RNG: C's LCG mixed with the HV counter
- Source: AB-DISASM, disasm/modules/68k/math/RandRange.asm:1-34 ($01D6A4, 64 calls); disasm/modules/68k/vdp/CmdGetVDPStatus.asm ($00046A, reads $C00008)
- What it does and why it is clever: The state at $FFA7E0 advances as s = s×1103515245 + 12345 (the ANSI C constants), using Multiply32. The value returned is (low word of the *previous* state + the VDP H/V counter) mod (max − min + 1), plus min. Mixing in the raster position adds entropy that depends on when the player pressed a button, at the cost of one port read.
- Key numbers: multiplier $41C64E6D, increment $3039; range via SignedMod.
- Target chapter: patterns/case-study-aerobiz.md
- Evidence: code only (shipped)

### Economy formulas as integer percentage chains
- Source: AB-DISASM, disasm/modules/68k/game/CalcOptimalTicketPrice.asm:60-120 ($00F75E); disasm/modules/68k/game/CalcQuarterBonus.asm ($0140DC)
- What it does and why it is clever: Prices are pure integer maths with no fixed point:
  - market = (cap + 20)(skill + 1)(frame/3 + 30) / 100
  - cost = (cap×15×2 + 600)(skill + 1) / 2, with ×15 done as `(x<<4) − x` and the halving done with sign-correct rounding (+1 if negative, then `asr`)
  - The frame counter is used as a slow time-varying "market" term.
  - Bonuses are ×20 / k, clamped to 100%.
- Key numbers: base 600 ($258); /100 percentages.
- Target chapter: patterns/case-study-aerobiz.md (or NEW: Fixed-point maths)
- Evidence: code only (shipped)

### Region membership as a range test on sorted city IDs
- Source: AB-DISASM, disasm/sections/section_000200.asm:529-591 (RangeLookup $00D648, 114 calls); disasm/modules/68k/game/FindBitInField.asm:1-42 ($009DC4)
- What it does and why it is clever: The 89 cities are numbered so that each of the 8 regions owns a contiguous run in two ID blocks (0-31 and 32-88). A table of (startA, countA, startB, countB) turns "which region is city n in?" into a scan of 8 entries. FindBitInField uses the same start values to turn a per-player 32-bit ownership mask into global IDs, starting from bit = 1 << start.
- Key numbers: 8 regions × 4 bytes at $05ECBC.
- Target chapter: patterns/case-study-aerobiz.md
- Evidence: code only (shipped)

### Idempotent fade guards (misnamed ResourceLoad / ResourceUnload)
- Source: AB-DISASM, disasm/modules/68k/game/ResourceLoad.asm:1-16 ($01D71C, 106 calls); ResourceUnload ($01D748, 95 calls)
- What it does and why it is clever: Before drawing, every screen calls a guarded "fade out if not already faded" that fades all 64 colours over 8 steps of 2 frames and sets a flag. After drawing it calls the matching fade-in. The flag lets calls nest safely, so screens can be drawn in any order without double fades.
- Key numbers: 64 colours, 8 steps × 2 frames ≈ 0.27 s.
- Target chapter: patterns/case-study-aerobiz.md
- Evidence: code only (shipped)

---

## howto/reverse-engineering.md

### Telling C-compiled code from hand-written assembly, and checking labels
- Source: AB-DISASM, e.g. disasm/modules/68k/game/CalcAffinityScore.asm:6 ("compiler junk" word), disasm/modules/68k/game/CalcOptimalTicketPrice.asm (link/movem/cdecl), compared with disasm/modules/68k/vint/*.asm (register-only, A5 globals)
- What it does and why it is clever:
  - **C-compiled code** has `link a6` frames, cdecl long arguments cleaned with `lea n(sp),sp`, `moveq #0; move.w` zero-extension before every helper call, `ext.l` before pushes, and stray padding words.
  - **The hand-written core** ($0200-$4600) uses fixed register roles (A5 = $FFF010, A4/A3 = VDP ports), RTR returns and PC-relative jump tables.
  - **Labels need checking.** Many function names in this repo were guessed from call sites and are wrong. Confirm a routine's purpose from the ports and RAM it touches; the label list at the top of this report shows how often that matters.
- Key numbers: about 860 functions; the hand-written core is roughly the first 18 KB.
- Target chapter: howto/reverse-engineering.md
- Evidence: code only (shipped)