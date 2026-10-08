# Harvested techniques: megadrive/vdp-registers.md

Target: `megadrive/vdp-registers.md`. 2 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from AB-DISASM -->
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

<!-- from AB-DISASM -->
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

