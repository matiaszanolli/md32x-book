# Harvested techniques: megadrive/z80.md

Target: `megadrive/z80.md`. 3 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from AB-DISASM -->
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

<!-- from AB-DISASM -->
### Z80 held off the bus during DMA and controller reads
- Source: AB-DISASM, disasm/modules/68k/vdp/ConfigVDPDMA.asm:6-8,66-68; disasm/modules/68k/input/InitInputArrays.asm:9-24 (ControllerPoll $00192E); disasm/modules/68k/game/CmdTestVRAM.asm ($0007D8)
- What it does and why it is clever: The game requests the Z80 bus around every 68k-to-VDP DMA and around every I/O port read sequence, then releases it right afterwards. During a DMA the VDP owns the 68k bus, and a Z80 bank-window access at that moment is unsafe. The pad port handshakes are timing-sensitive, so they are also done with the Z80 parked. A flag at $C70(a5) lets callers skip the request when they already own the bus.
- Key numbers: $A11100 = $100 to request and $0000 to release; poll bit 8 (word read) or bit 0 (byte).
- Target chapter: megadrive/z80.md
- Evidence: code only (shipped)

<!-- from AB-DISASM -->
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

