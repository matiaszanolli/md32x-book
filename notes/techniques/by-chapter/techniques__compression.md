# Harvested techniques: Compression and decompression

Target: Part VI chapter in `src/techniques/` (or `src/howto/emulator-testing.md`). 6 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from AB-DISASM -->
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

<!-- from AB-DISASM -->
### Decompressing straight into VRAM, using VRAM as the history window
- Source: AB-DISASM, disasm/modules/68k/game/DecompressVDPTiles.asm:7-292 ($004342-$0045B1); disasm/modules/68k/vdp/VRAMWriteExtended.asm:1-34 ($0042F0); disasm/modules/68k/vdp/VRAMWriteWithMode.asm:1-25 ($0042BA); disasm/modules/68k/vdp/WriteColorBitsVRAM.asm:1-50 ($004240, bit reader with mask table $04686E)
- What it does and why it is clever: This is the same format with a different output path, so no RAM buffer is needed.
  - Literals and match bytes are written one at a time by read-modify-write of the containing VRAM word: set the read address (even), read the word, merge the byte into the high or low half by address parity, set the write address, write the word back.
  - Back-references read from VRAM through a byte-read helper.
  - Every access masks interrupts so the V-int handler cannot disturb the VDP address latch.

  It is slow, at 4 control/data accesses per byte, so it is used once (one call site, reached twice during the intro), to load the font to VRAM $4000 (3,866 bytes to 10,112). In exchange it can unpack data larger than free RAM.
- Key numbers: zero RAM window; 1 byte of output per read-modify-write cycle.
- Target chapter: NEW: Compression on the Mega Drive
- Evidence: code only (shipped)

---

<!-- from MK2 -->
### Rob Northen ProPack (RNC) method 2 unpacked on the SH-2 (Mortal Kombat II)
- Source: MK2, SH-2 code at `0x06002DF4` (address loaded at 30 places); ROM signatures `RNC\x02` (47 files) and `RNC\x01` (34 files)
- What it does and why it is clever: Assets are RNC-packed; the Master unpacks method-2 files from ROM straight into SDRAM (fonts, graphics). The unpacker skips the 18-byte RNC header and reads a flag bit stream, MSB first, refilled a byte at a time. Flags choose: a single literal byte; a literal block of (4-bit count + 3) × 2 bytes; or a back-reference copied from earlier output, with a length of 2 or more (longer lengths from an extra byte, + 8) and an offset built from a few bits plus a byte. A length byte of 0 ends the data. Method-1 files are presumably the 68000's (not checked).
- Key numbers: 18-byte header; 398-byte routine.
- Target chapter: techniques/compression.md
- Evidence: ROM

<!-- from MK2 -->
### Colour/run RLE sprites with a palette offset (Mortal Kombat II)
- Source: MK2, SH-2 blitters at `0x060028C0`/`0x0600292C` (fighters) and `0x060027F0`/`0x06002858` (other objects)
- What it does and why it is clever: Each sprite frame starts with a byte giving the end-of-line marker. Each line starts with a skip count, then bytes that pack colour and run length: fighters use 6 bits of colour and 2 of run (16-colour objects use 4 + 4). A run of 0 means the length is in the next byte; colour 0 is a transparent run (just advance). A per-object palette offset is added to each colour, so two fighters share one sprite format but use different 64-colour slices of the 256-entry palette. Mirroring is a second copy of the decoder that writes right to left; the data is stored once.
- Key numbers: 6+2 bits (fighters), 4+4 bits (others).
- Target chapter: techniques/compression.md
- Evidence: ROM

<!-- from MK2 -->
### 6-bit PCM, four samples in three bytes (Mortal Kombat II)
- Source: MK2, SH-2 code at `0x0600509C` (unpack), `0x06004F4C` (PWM handler)
- What it does and why it is clever: Sound samples are 6-bit, packed four to three bytes; a phase counter (0-3) picks which bits to take. Each sample is played twice at 22 kHz, so the data is effectively 11 kHz. Together that is 8.1 KB of ROM per second of sound instead of 22 KB for 8-bit at the output rate.
- Key numbers: 0.75 byte per sample; 11,042 samples/s of data.
- Target chapter: techniques/compression.md
- Evidence: ROM

<!-- from AB32X -->
### RLE sprite format decoded with Duff's device (After Burner Complete)
- Source: AB32X, SH-2 code at `0x060066A6`-`0x0600676A`
- What it does and why it is clever: Signed control byte: negative = run of zeros, written by jumping into 8 unrolled `mov.b`; positive = that many literal bytes. A second variant masks literals to 4 bits. Zero runs become transparent pixels later (overwrite image).
- Target chapter: techniques/compression
- Evidence: ROM
