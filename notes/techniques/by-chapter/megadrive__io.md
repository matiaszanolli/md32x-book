# Harvested techniques: megadrive/io.md

Target: `megadrive/io.md`. 6 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from S32X-SKILL -->
### Mask pads to the 3-button subset
- Source: S32X-SKILL, references/architecture.md:85-93
- What it does and why it is clever: Several emulators mirror d-pad bits into the 6-button nibble during the handshake, so every direction also reads as X/Y/Z/Mode (jump/back). Mask to U/D/L/R/A/B/C/Start. The Sega Mouse is available through `Mars_PollMouse`.
- Key numbers: —
- Target chapter: megadrive/io.md
- Evidence: Real shipped bug, with a regression test.

---

<!-- from AB-DISASM -->
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

<!-- from AB-DISASM -->
### 6-button pad detection by extra TH pulses
- Source: AB-DISASM, disasm/modules/68k/input/ReadMultiNibbles.asm:1-59 ($001A20); disasm/modules/68k/util/WritePortToggle.asm ($0019E8)
- What it does and why it is clever: The routine toggles TH up to three times with 4 NOPs of settle time per edge. A TH-low read with U/D/L/R all zero identifies a 6-button pad. Then the base buttons are packed as `(lowread<<2 & $C0) | (highread & $3F)`, inverted, and stored. The extra X/Y/Z/Mode nibble goes into a second slot with type 1. A 3-button pad is stored as type 0, and an empty port as type $F.
- Key numbers: 3 TH cycles maximum; 4 NOPs ≈ 16 cycles settle.
- Target chapter: megadrive/io.md
- Evidence: code only (shipped)

<!-- from AB-DISASM -->
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

<!-- from AB-DISASM -->
### Edge detection in three instructions, plus a sticky press latch
- Source: AB-DISASM, disasm/modules/68k/util/XorAndUpdate.asm ($001A14); disasm/modules/68k/vint/SubsysUpdate4.asm:1-32 ($0018D0); disasm/modules/68k/input/ReadInput.asm ($01E1EC); disasm/modules/68k/input/CmdReadInput.asm ($00060C)
- What it does and why it is clever:
  - XorAndUpdate stores the held byte and the newly pressed byte as `pressed = (old XOR new) AND new`.
  - Every V-blank, SubsysUpdate4 ORs pressed<<8 | held for both ports into a long latch at $BE8(a5), filtered by an enable mask at $BE4. A tap shorter than one game-loop iteration is never lost, even when the C code runs at a low frame rate.
  - ReadInput returns pressed, held, or pressed|held depending on its argument.
- Key numbers: port B in the high word; mask at $FFA790.
- Target chapter: megadrive/io.md
- Evidence: code only (shipped)

<!-- from AB-DISASM -->
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

