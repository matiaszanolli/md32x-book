# Harvested techniques: megadrive/vdp-dma.md

Target: `megadrive/vdp-dma.md`. 11 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from VRD/AU/MARSDEV -->
### Genesis VDP DMA from a banked 32X game: translate at the sink, run the window from the stack
- Source: AU-NOTES, PORT_ARCHITECTURE.md:77-203; disasm/32x/dma_stub.asm:1-139
- What it does and why it is clever:
  - **The real obstacle:** register 23 holds seven source bits (DMD0 doubles as bit 23), so `$900000` encodes fine. The obstacle is that the adapter does not serve `$880000-$9FFFFF` to VDP DMA, which needs RV=1 to place the cartridge at its own offsets.
  - **Translate at the sink:** one sink (`ConfigVDPDMA`) applies `if (src & $F00000) == $900000: src -= $800000`. Genesis-form sources below `$100000` get `+$100000`; Work-RAM sources pass untouched.
  - **Run the window from RAM:** the RV-on / trigger / drain / RV-off sequence must run from RAM, and no Work RAM is reliably free. The thunk copies the position-independent window body below SP each transfer, jumps to it, then pops it.
  - **Size-neutral hook:** the game's own `jsr $FFF000` (6 bytes) is repointed.
- Key numbers: window body about 25 word moves; 3,000 frames with 233 RV mapping changes, 100 of 100 frames identical; later 6,489 frames with 485 changes, all identical.
- Target chapter: megadrive/vdp-dma.md
- Evidence: emulator measured (PicoDrive with Aerobiz's RV-emulation patch to the PicoDrive core, VRD_RV_EMULATION; Ares). Whether `$880000` truly unmaps under RV=1 is unverified on hardware.

<!-- from VRD/AU/MARSDEV -->
### Off-screen plane rows are live scratch
- Source: AU-NOTES, PORT_ARCHITECTURE.md:526-560; ROADMAP.md:1200-1290
- What it does and why it is clever: The game keeps data past the 28 displayed rows (plane A to row 91, B to row 78) at fixed VRAM addresses. Widening the plane from 32 to 64 cells halves the row stride and slides the visible window onto that scratch. A VRAM write trace found the culprit: `CmdSetupDMA` with an absolute destination (192 bytes to `$EA80` at frame 8201).
- Key numbers: 432 of 600 sampled frames differ from frame 8250 onward.
- Target chapter: megadrive/vdp-dma.md
- Evidence: emulator measured (PicoDrive VRAM trace)

<!-- from VRD/AU/MARSDEV -->
### Palette DMA and FB swap inside V-INT
- Source: VRD-NOTES, analysis/VINT_HANDLER_ARCHITECTURE.md:85-134
- What it does and why it is clever: VR's V-INT state `$54`:
  1. writes scroll and colour registers;
  2. requests the Z80 bus;
  3. DMAs 64 palette words from ROM to CRAM;
  4. releases the bus;
  5. and only if the SH-2 is done: clears CMD INT around the FS toggle and resets the game state.

  All VDP traffic is confined to V-Blank.
- Key numbers: 178-byte handler.
- Target chapter: megadrive/vdp-dma.md
- Evidence: code only

---

<!-- from AB-DISASM -->
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

<!-- from AB-DISASM -->
### DMA trigger executed from work RAM at $FFF000
- Source: AB-DISASM, disasm/sections/section_000200.asm:57-68 (copy loop at $00034E, stub bytes at $000362-$00036B); call site disasm/modules/68k/vdp/ConfigVDPDMA.asm:53 (`jsr $FFF000`, still encoded as dc.w)
- What it does and why it is clever: At boot the game copies a 10-byte routine (two `move.w $42(a5),(a4)` / `move.w $44(a5),(a4)` plus `rts`) to $FFF000. That is directly above the initial stack pointer, which is also $FFF000. The two halves of the prebuilt VDP command long ($42/$44(a5)) are therefore written to the control port by code fetched from RAM, not ROM. The repo's docs/sega-genesis-reference-sheets.md:65 states the rule: "ROM DMA requires final DMA to be done from RAM". Every DMA in the game (ROM or RAM source) goes through this one stub.
- Key numbers: 10 bytes; command long staged at A5+$42 (A5 = $FFF010, so $FFF052/$FFF054).
- Target chapter: megadrive/vdp-dma.md
- Evidence: code only (shipped)

<!-- from AB-DISASM -->
### First-word rewrite after a RAM-source DMA
- Source: AB-DISASM, disasm/modules/68k/vdp/ConfigVDPDMA.asm:56-66 ($001226-$001242); disasm/modules/68k/vdp/BulkCopyVDP.asm:1-12 ($001386)
- What it does and why it is clever: After the DMA, the routine tests bit 22 of the source address, which is set for any $FFxxxx work-RAM address. If it is set, the routine clears bit 7 (CD5) of the command long, turning it into a plain CPU write to the same destination. It then rewrites the first word by hand through BulkCopyVDP with count 1. This is a cheap guard against a corrupted first word on RAM-source DMA, and it costs only one extra command plus one data write.
- Key numbers: `btst #$16,d0`; one word rewritten; ROM-source DMAs skip it.
- Target chapter: megadrive/vdp-dma.md
- Evidence: code only (shipped)

<!-- from AB-DISASM -->
### One back end for all three DMA modes (68k copy, VRAM fill, VRAM copy)
- Source: AB-DISASM, disasm/modules/68k/game/SelectVDPInit.asm:1-20 ($0015B0); disasm/modules/68k/vdp/ConfigVDPColors.asm:1-39 ($0012DA, fill); disasm/modules/68k/vdp/ConfigVDPScroll.asm:1-48 ($001256, copy); disasm/modules/68k/game/CmdLoadTiles.asm, CmdTransferPlane.asm
- What it does and why it is clever: All three modes share one RAM parameter block (A5+$1D auto-increment, +$1E length, +$20 source, +$24 destination, +$28 fill value).
  - ConfigVDPColors (despite its name) programs reg 23 = $80 (fill mode), writes the destination with CD bits $4000/$0080, then writes the fill word to the data port to start the fill.
  - ConfigVDPScroll programs reg 23 = $C0 (VRAM copy), with regs 21/22 holding the VRAM source and command low bits $00C0.

  A three-bit selector routes a request to the right back end. GameCommands 6 and 7 expose the copy and fill paths to C code.
- Key numbers: reg 23 = $80 for fill and $C0 for copy; 16-bit length.
- Target chapter: megadrive/vdp-dma.md
- Evidence: code only (shipped)

<!-- from AB-DISASM -->
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

<!-- from AB-DISASM -->
### Throttled bulk tile upload in 4 KB chunks
- Source: AB-DISASM, disasm/modules/68k/vdp/VRAMBulkLoad.asm:1-79 ($01D568)
- What it does and why it is clever: Large tile sets are split into chunks of $80 tiles: $800 words (4 KB) per DMA. Source and VRAM destination each advance by $1000 bytes, and the routine waits 4 frames (GameCommand 14) between chunks. The remainder goes in one last DMA of n×16 words. A small upload waits n/100 frames. This spreads a big upload over several frames instead of one long stall.
- Key numbers: 4 KB per chunk, a 4-frame gap; tile number × 32 = VRAM byte address.
- Target chapter: megadrive/vdp-dma.md (also patterns/streaming.md)
- Evidence: code only (shipped)

<!-- from AB-DISASM -->
### Animated tiles: per-frame DMA of selected 32-byte frames
- Source: AB-DISASM, disasm/modules/68k/input/ControllerRead.asm:1-62 ($000B42; misnamed)
- What it does and why it is clever: A countdown at $302(a5), reloaded from $300(a5), drives a frame index. The index wraps at the frame count in $2FE(a5). On each tick, a 16-bit enable mask (the AND of $2FC and $304) is shifted right one bit at a time. For each set bit, the routine queues a 16-word (one tile) DMA from that slot's source (frame×32, slot stride $80) to the slot's VRAM address taken from a table at $FFF316. Up to 16 animated tiles (water, lights and so on) update with no CPU pixel copying.
- Key numbers: 16 slots; 32 bytes per frame; each slot's source block is $80 bytes (4 frames).
- Target chapter: megadrive/vdp-dma.md
- Evidence: code only (shipped)

<!-- from AB-DISASM -->
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

