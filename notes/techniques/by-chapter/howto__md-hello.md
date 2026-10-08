# Harvested techniques: howto/md-hello.md

Target: `howto/md-hello.md`. 2 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from AB-DISASM -->
### Expanding 1bpp to 4bpp with a self-restoring rotating mask
- Source: AB-DISASM, disasm/modules/68k/boot/EarlyInit.asm:54-70 ($003C4A-$003C74)
- What it does and why it is clever: The mask register D2 starts at $10000000. For each of 8 pixels it does `rol.l #4,d2`, then `ror.b #1,d1` to shift the next source bit into carry, then `or.l d2,d4` if the bit was set. After 8 rotations of 4 bits, D2 is back to $10000000, so it never needs reloading. Each set bit becomes colour index 1. The repo comment calls this a cycling palette, but the data is a single nibble that walks through positions. One long goes to the data port per row.
- Key numbers: 8 bytes → 32 bytes per tile; 59 tiles; no lookup table.
- Target chapter: howto/md-hello.md
- Evidence: code only (shipped)

<!-- from AB-DISASM -->
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

