# Harvested techniques: megadrive/cartridge.md

Target: `megadrive/cartridge.md`. 8 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from S32X-SKILL -->
### Header fix-up and checksum
- Source: S32X-SKILL, assets/romfix.py:1-65; assets/verify_rom.py:67-87; references/toolchain-and-build.md:113-128
- What it does and why it is clever: `SEGA 32X` at 0x100. Checksum at 0x18E = sum of big-endian 16-bit words from 0x200 to end, mod 2^16. ROM end (last byte) at 0x1A4, which must be rewritten because the stock header hardcodes 4 MiB. Mars header at 0x3C0-0x3F0: master entry 0x06000240, slave 0x06000244, VBRs 0x06000000 / 0x06000120.
- Key numbers: 8 KiB `dd` padding, 512 KiB romfix granularity, ROM ≤ 4 MiB.
- Target chapter: megadrive/cartridge.md
- Evidence: verify_rom static check.

<!-- from S32X-SKILL -->
### Banking or 32X-CD: decide before freezing asset addresses
- Source: S32X-SKILL, references/architecture.md:33-35, 232-253
- What it does and why it is clever: Emitting absolute offsets and adding banking later means rewriting the converter. Choose SSF banking (`Mars_SetBankPage`, `SEGA SSF` header) with a lazily activated banked directory, or 32X-CD, up front. Grow the ROM in powers of two.
- Key numbers: Window about 4 MiB. Franzen's source audio was about 170 MiB. 512 KiB → 1 MiB growth.
- Target chapter: megadrive/cartridge.md
- Evidence: franzen-32x.

<!-- from S32X-SKILL -->
### Defensive SRAM save format
- Source: S32X-SKILL, references/architecture.md:172-199
- What it does and why it is clever: A bounded fixed layout with magic/version header and payload checksum. Fields are serialised explicitly in a defined byte order (never memcpy'd structs). Big, mostly-default state is stored sparsely (only depleted forest cells). Validate on boot before enabling Continue. Write on request, never every frame.
- Key numbers: ≤ 2 KiB. 64×64 world diffs fit in a couple of KiB.
- Target chapter: megadrive/cartridge.md
- Evidence: warcraft-32x, with a pixel-compare restore test.

<!-- from S32X-SKILL -->
### Two-phase-commit saves
- Source: S32X-SKILL, references/architecture.md:255-262
- What it does and why it is clever: Write to a spare slot, verify it, then flip an active-slot marker. Power loss mid-write never destroys the only good save, and versioning lets old saves be rejected or migrated.
- Key numbers: —
- Target chapter: megadrive/cartridge.md
- Evidence: franzen-32x (described).

<!-- from S32X-SKILL -->
### 68000 boot image in the fixed low ROM window
- Source: S32X-SKILL, references/architecture.md:125-128
- What it does and why it is clever: Put the 68000 work-RAM image before any large blob; if the 68000 must reach past a music blob, some emulators boot black.
- Key numbers: —
- Target chapter: megadrive/cartridge.md
- Evidence: Black-screen triage.

---

<!-- from AB-DISASM -->
### Save RAM format: odd-byte stride, header, additive checksum
- Source: AB-DISASM, disasm/modules/68k/game/PackSaveState.asm:407-441 ($00EB28, finalize); disasm/modules/68k/game/UpdatePassengerDemand.asm:1-20 ($00F522, header writer); disasm/modules/68k/util/VerifyChecksum.asm:1-35 ($00F552); disasm/modules/68k/math/ByteSum.asm ($01D6FC); disasm/modules/68k/memory/CopyBytesToWords.asm ($01E0E0), CopyAlternateBytes.asm ($01E0FE)
- What it does and why it is clever:
  - The save image is built in RAM at $FF1804. The header word at +2 is a 16-bit sum of the payload bytes, the word at +4 is the payload length, and the payload starts at +6.
  - It is written with stride 2 to SRAM at $200003 + slot × $2000, so only odd addresses (the byte-wide SRAM lane) are used. Starting at $200003 skips the first SRAM byte, which follows Sega's manual: "important data must not be stored in the first word" (docs/genesis-software-development-manual.md:754).
  - Loading reads the image back with the inverse stride, recomputes the sum and compares it with the header.
- Key numbers: 8 KB of SRAM address space; $1000 data bytes per slot; 16-bit sum.
- Target chapter: megadrive/cartridge.md
- Evidence: code only (shipped)

<!-- from AB-DISASM -->
### Compact save serialisation: stride compaction, field trimming, 2-bit packing
- Source: AB-DISASM, disasm/modules/68k/game/PackSaveState.asm:18-406 ($00EB28-$00EF91; city loop at 279, route loop at 315); disasm/modules/68k/game/UnpackPixelData.asm:1-34 ($00EFC8)
- What it does and why it is clever: The serialiser saves the state in a smaller form than it uses in RAM:
  - The C code stores many byte arrays as one byte per word. The serialiser saves only the meaningful byte: 89 cities × 4 entries and the event and table blocks.
  - For each of the 4×40 route slots it saves only the first 12 of 20 bytes; the rest can be recomputed.
  - A 228-entry table of 2-bit values (4 players × 57) is unpacked LSB-first, four per byte, at $FF05C4.
- Key numbers: route slots 3200 bytes in RAM vs 1920 bytes saved; 57 → 228 for the 2-bit table.
- Target chapter: megadrive/cartridge.md (also patterns/case-study-aerobiz.md)
- Evidence: code only (shipped)

<!-- from AB-DISASM -->
### Region lockout screen drawn with a built-in 1bpp font
- Source: AB-DISASM, disasm/modules/68k/boot/EarlyInit.asm:10-30 (region check $003BE8), 154-188 (WriteVDPTileRow $003CE0)
- What it does and why it is clever: The routine reads $A10001 bits 7-6, maps them through the 4-byte table "J,0,U,E", and looks for that letter in the header region field at $1F0-$1FF. If there is no match, it sets up a minimal VDP and prints "DEVELOPED FOR USE ONLY WITH … SYSTEMS." using an ASCII−$20 tile mapping. The address is computed as row×$80 + col×2 plus $40000003. Then it halts.
- Key numbers: 59 glyphs; region letters at $1F0.
- Target chapter: megadrive/cartridge.md
- Evidence: code only (shipped)

---

