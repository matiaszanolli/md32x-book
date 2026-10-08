# Harvested techniques: Text, menus and UI on tile planes

Target: Part VI chapter in `src/techniques/` (or `src/howto/emulator-testing.md`). 4 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from AB-DISASM -->
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

<!-- from AB-DISASM -->
### Compact vsprintf with tile-aware width and money suffix
- Source: AB-DISASM, disasm/modules/68k/text/Vsprintf.asm:1-337 ($03AFF2; currency at 290-297); disasm/modules/68k/text/IntToDecimalStr.asm:1-38 ($03AA02)
- What it does and why it is clever: The formatter handles %d/%u/%x/%s/%c, width, precision, `-` and 0 padding. Two extras matter for a tile UI:
  - `%w` doubles the width and precision so columns line up in the 2-row font.
  - `$` prefixes "$" and appends "0K". Money is stored in units of $10,000, so "$1230K" prints with no 32-bit multiply by 1000. `$$` leaves out the suffix.

  Decimal conversion is recursive: print n/10, then the digit n%10. That is the main reason the V-int stack guard exists.
- Key numbers: 152-byte local output buffer; default precision 6.
- Target chapter: NEW: Text and menus with tile planes
- Evidence: code only (shipped)

<!-- from AB-DISASM -->
### Two digits in one 8×8 tile using a half-row-offset read
- Source: AB-DISASM, disasm/modules/68k/math/RoundValue.asm:5-67 ($01DF30; misnamed); digit glyphs DigitFontTiles $048E00
- What it does and why it is clever: To show 0-99 in a single cell, the routine ORs two glyphs together, 8 longs each. The units glyph is read aligned. The tens glyph is read from glyph address + 2 bytes. With 4-byte tile rows, that misaligned read moves the right half of each row into the left half. The digits are 4 px wide and drawn in the right half of their tiles, so the result is "tens | units" in one tile, with no shifting code. A zero tens digit uses a blank glyph (tile 10).
- Key numbers: 32 bytes per output tile; 8 OR operations.
- Target chapter: NEW: Text and menus with tile planes
- Evidence: code only (shipped)

---

<!-- from MK2 -->
### Proportional 32X fonts and a per-frame text list (Mortal Kombat II)
- Source: MK2, SH-2 code at `0x060011A8` (unpack fonts), `0x060016AC` (draw string), `0x0600122A` (text list)
- What it does and why it is clever: Three proportional fonts are RNC-unpacked into SDRAM (`0x06036B2C`, `0x06037F60`, `0x06038F28`) when a screen starts. A glyph record gives width, height and an offset to its pixels; a pixel value of 1 is replaced by the requested colour, so one font prints in any colour, and 0 is skipped by the overwrite image. Text to show arrives from the 68000 as a 12-entry list in the per-frame state block (message number, position); empty entries and entries below the screen are skipped.
- Key numbers: 3 fonts; 12 messages per frame.
- Target chapter: techniques/text-menus.md
- Evidence: ROM
