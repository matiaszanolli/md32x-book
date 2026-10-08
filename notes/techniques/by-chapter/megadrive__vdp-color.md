# Harvested techniques: megadrive/vdp-color.md

Target: `megadrive/vdp-color.md`. 4 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from AB-DISASM -->
### Subtractive palette fade (FadePalette)
- Source: AB-DISASM, disasm/modules/68k/display/FadePalette.asm:1-113 ($004BC6); drivers disasm/modules/68k/graphics/DrawLayersForward.asm ($004D04), DrawLayersReverse ($004CB6), disasm/modules/68k/display/FadeInAndWait.asm ($03B3DA)
- What it does and why it is clever: The routine unpacks the Mega Drive colour format `0000BBB0GGG0RRR0` into three 3-bit channels. With level L from 0 to 7, each channel becomes max(0, c − (7 − L)). The result is repacked into a 64-colour stack buffer and uploaded. Subtracting instead of scaling needs no multiply, and it fades in exactly 8 steps. Dim channels reach black first, which gives a slight warm/cool tint shift. FadeInAndWait returns early if a button is pressed.
- Key numbers: 8 levels; channel masks $0E00/$00E0/$000E; up to 64 colours.
- Target chapter: megadrive/vdp-color.md
- Evidence: code only (shipped)

<!-- from AB-DISASM -->
### 8-step cross-fade to a target palette that converges together
- Source: AB-DISASM, disasm/modules/68k/graphics/RenderColorTileset.asm:1-152 ($03B9D4)
- What it does and why it is clever: Each step moves each channel by at most 1 toward the target. Decreases start immediately. An increase happens only when the target is greater than (7 − step), so a brightening channel starts late enough to arrive exactly on step 7. All brightening finishes on the same frame without any division.
- Key numbers: 8 steps; channel range 0-7.
- Target chapter: megadrive/vdp-color.md
- Evidence: code only (shipped)

<!-- from AB-DISASM -->
### Colour shimmer from a sliding window over a gradient table
- Source: AB-DISASM, disasm/modules/68k/game/InitAnimTable.asm:1-60 ($001CA0, table BlueAnimPalette $001D1A); disasm/modules/68k/game/UpdateAnimTimer.asm:1-20 ($001D58); disasm/modules/68k/vdp/DMA_Transfer.asm:1-14 ($00163E)
- What it does and why it is clever: The boot logo animates by copying an 11-colour window of a 31-entry blue gradient (bright → dark → bright) into a RAM buffer. The window start moves back one entry every 2 frames. V-blank sends the window to CRAM byte $0004 (colours 2-12) with a CPU loop. The loop also detects controllers and exits on any button, including mouse buttons, or after 300 iterations.
- Key numbers: 31 entries, an 11-word window; command $C0040000.
- Target chapter: megadrive/vdp-color.md
- Evidence: code only (shipped)

<!-- from AB-DISASM -->
### Recolouring pixels in tile data, one nibble at a time
- Source: AB-DISASM, disasm/modules/68k/game/ApplyPaletteMask.asm:1-58 ($0048D2)
- What it does and why it is clever: Before upload, each 16-bit word of 4bpp tile data is tested nibble by nibble against a mask table at $04735E. Any pixel equal to colour index `from` is replaced with `to`, by shifting both 4 bits per nibble. One tile set can show per-player colours without separate artwork.
- Key numbers: 4 nibbles per word; 16 words per tile.
- Target chapter: megadrive/vdp-color.md
- Evidence: code only (shipped)

---

