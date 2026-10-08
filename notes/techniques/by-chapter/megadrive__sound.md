# Harvested techniques: megadrive/sound.md

Target: `megadrive/sound.md`. 1 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from AB-DISASM -->
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

