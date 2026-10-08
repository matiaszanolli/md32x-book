# Registers and access

The VDP has 24 write-only registers, numbered 0 to 23, and one read-only status register [MD-TO p.22]. This chapter lists every register bit by bit, explains the status register, and covers the auto-increment register's traps. The basics of talking to the VDP (the ports, the `$8rvv` register word, the two-word memory command and the state the VDP keeps between writes) are in [the VDP overview](vdp.md#the-ports). Read that first.

On the 32X, the Mega Drive VDP's registers are unchanged. The 32X VDP has its own, separate set; see [System registers](../32x/registers.md) and [The 32X VDP](../32x/vdp.md).

## All 24 registers

The "Sega" column is the value Sega's initial program writes at power-on, so every game starts from it (see [the VDP overview](vdp.md#what-lives-where-in-vram)) [AB-DISASM, initial program at `$2A8`]. The initial program uses registers 19-23 to clear VRAM, so after it ends they hold whatever that fill left behind.

| # | Name | Sega | Bits, 7 → 0 | Covered in |
|---|------|------|-------------|------------|
| 0 | Mode set 1 | `$04` | `0 0 0 IE1 0 1 M3 0` | [below](#registers-0-and-1-mode-set-1-and-2) |
| 1 | Mode set 2 | `$14` | `0 DISP IE0 M1 M2 1 0 0` | [below](#registers-0-and-1-mode-set-1-and-2) |
| 2 | Plane A name table | `$30` | `0 0 A15 A14 A13 0 0 0` | [Planes](vdp-planes.md) |
| 3 | Window name table | `$3C` | `0 0 A15 A14 A13 A12 A11 0` | [Planes](vdp-planes.md) |
| 4 | Plane B name table | `$07` | `0 0 0 0 0 A15 A14 A13` | [Planes](vdp-planes.md) |
| 5 | Sprite table | `$6C` | `0 A15 A14 A13 A12 A11 A10 A9` | [Sprites](vdp-sprites.md) |
| 6 | — | `$00` | always 0 | |
| 7 | Backdrop colour | `$00` | `0 0 PAL1 PAL0 C3 C2 C1 C0` | [Colour](vdp-color.md) |
| 8, 9 | — | `$00` | always 0 | |
| 10 | Line interrupt counter | `$FF` | `L7-L0` | [Timing](vdp-timing.md) |
| 11 | Mode set 3 | `$00` | `0 0 0 0 IE2 VSCR HSCR LSCR` | [below](#registers-11-and-12-mode-set-3-and-4) |
| 12 | Mode set 4 | `$81` | `RS0 0 0 0 S/TE LSM1 LSM0 RS1` | [below](#registers-11-and-12-mode-set-3-and-4) |
| 13 | Horizontal scroll table | `$37` | `0 0 A15 A14 A13 A12 A11 A10` | [Planes](vdp-planes.md) |
| 14 | — | `$00` | always 0 | |
| 15 | Auto-increment | `$01` | `I7-I0` | [below](#register-15-auto-increment) |
| 16 | Plane size | `$01` | `0 0 VSZ1 VSZ0 0 0 HSZ1 HSZ0` | [below](#the-other-registers) |
| 17 | Window horizontal | `$00` | `RIGT 0 0 X4-X0` | [below](#the-other-registers) |
| 18 | Window vertical | `$00` | `DOWN 0 0 Y4-Y0` | [below](#the-other-registers) |
| 19 | DMA length, low | `$FF` | `L7-L0` | [DMA](vdp-dma.md) |
| 20 | DMA length, high | `$FF` | `L15-L8` | [DMA](vdp-dma.md) |
| 21 | DMA source, low | `$00` | `S8-S1` | [DMA](vdp-dma.md) |
| 22 | DMA source, middle | `$00` | `S16-S9` | [DMA](vdp-dma.md) |
| 23 | DMA source, high and mode | `$80` | `DMD1 DMD0 S22-S17` | [DMA](vdp-dma.md) |

Sources: [MD-TO pp.22-26; MD-SWM §2.5; GENVDP §17]. Bits shown as 0 or 1 must be written that way. The address bits in registers 2-5 and 13 are the top bits of the table's VRAM address, so plane A and plane B sit on `$2000` boundaries, the window on `$800`, the sprite table on `$200` and the horizontal scroll table on `$400`. In 40-column mode the window's A11 and the sprite table's A9 must be 0 [MD-TO pp.22-23].

A register word is `%10?r rrrr vvvv vvvv`. The VDP ignores bit 13, and writes to register numbers 24-31 do nothing [GENVDP §7].

## Registers 0 and 1: mode set 1 and 2

| Register | Bit | Name | 1 means | 0 means |
|----------|-----|------|---------|---------|
| 0 | 4 | IE1 | Line interrupt on (68000 level 4) | Off |
| 0 | 2 | — | Normal colours | Only the lowest bit of each colour component is used: 8 colours (GENVDP) |
| 0 | 1 | M3 | H/V counter stops (latched) | H/V counter runs |
| 1 | 6 | DISP | Planes and sprites shown | Whole screen shows the backdrop colour |
| 1 | 5 | IE0 | Vertical blank interrupt on (68000 level 6) | Off |
| 1 | 4 | M1 | DMA allowed | DMA commands are ignored |
| 1 | 3 | M2 | 30 rows (240 lines), PAL only | 28 rows (224 lines). Always 0 on NTSC |
| 1 | 2 | M5 | Mega Drive mode (mode 5) | Master System mode (mode 4) |

Sources: [MD-TO p.22; GENVDP §17]. Points that matter in practice:

- **Turn DISP off for big uploads.** With the display off, every line is blank, and the CPU and DMA can reach the VDP's memories without the limits of the active display [GENVDP §17]. Turning it off for one frame shows a frame of backdrop colour, which is why games do it behind a fade.
- **M1 must be 1 for DMA.** A DMA command with M1 = 0 does nothing, and some commercial games send them anyway [GENVDP §11]. Many games keep M1 at 0 and set it only around a transfer. Aerobiz does that in one write to register 1, which also turns the vertical interrupt (IE0) off for the duration, using its RAM copy of the register [AB-DISASM, ConfigVDPScroll.asm].
- **M3 latches the H/V counter** when the external interrupt fires, for light guns. See [Timing, interrupts and counters](vdp-timing.md).
- **Bit 2 of register 0 should stay 1.** Sega's manuals simply show it as 1. GENVDP found that 0 limits the palette to eight colours, as on the Master System.
- **Register 1 bit 7 must be 0, and bit 2 must be 1.** GENVDP describes bit 7 as a Master System leftover that turns every tile into a block of solid colour. With bit 2 at 0 the VDP drops into Master System mode, where none of the Mega Drive registers work [GENVDP §17].

## Registers 11 and 12: mode set 3 and 4

| Register | Bits | Name | Values |
|----------|------|------|--------|
| 11 | 3 | IE2 | 1 = external interrupt on (68000 level 2), from the controller port's TH line |
| 11 | 2 | VSCR | 0 = whole-plane vertical scroll, 1 = per 2-tile column |
| 11 | 1-0 | HSCR, LSCR | `00` whole plane, `10` per tile row (8 lines), `11` per line, `01` not allowed |
| 12 | 7, 0 | RS0, RS1 | Both 0 = 32 columns (256 pixels), both 1 = 40 columns (320 pixels) |
| 12 | 3 | S/TE | 1 = shadow and highlight on |
| 12 | 2-1 | LSM1, LSM0 | `00` no interlace, `01` interlace, `11` interlace at double resolution, `10` not allowed |

Sources: [MD-TO p.24; MD-SWM §2.5]. The scroll and interlace modes are explained in [Planes and scrolling](vdp-planes.md) and [Color, shadow/highlight and interlace](vdp-color.md).

**Set RS0 and RS1 to the same value.** Sega's manuals say so plainly [MD-TO p.24]. GENVDP tried the mixed settings: `01` gives a 40-column picture that is slightly distorted, and one unlicensed game uses it [GENVDP §17].

**Why the mixed settings misbehave.** ares models the two bits as different things. RS1 sets the width: 40 columns, and a pixel clock of the master clock ÷ 4 instead of ÷ 5. RS0 switches the VDP to an external dot clock, its EDCLK input pin [GENVDP §18], for a stretch of slots in every line's horizontal blank. ares runs those slots at an uneven, slower rate (15 of every 17 at ÷ 5, the other 2 at ÷ 4) <span class="tag emulator">emulator</span> [ARES, ares/md/vdp/main.cpp, vdp.hpp]. In that model, RS1 without RS0 gives 40 columns with every line slightly short, which fits the distortion GENVDP saw. In that model, Sega's rule to set both bits together amounts to "use the external clock whenever the picture is 40 columns wide".

**Bits 4 to 6 of register 12.** GENVDP found that bits 4 and 6 do nothing visible, and that bit 5 changes the picture only in the way the mixed `01` setting does [GENVDP §17]. None of the emulators gives any of them an effect. ares stores them under the names `externalColorEnable`, `hsync` and `vsync`, and MAME calls bit 5 "special" and the other two unused [ARES, ares/md/vdp/io.cpp, vdp.hpp; MAME, src/devices/video/315_5313.cpp]. A 2009 description of the VDP's pins fits ares's names: the /VSync pin carries vertical sync "or the pixel clock", /HSync carries horizontal sync "or always 1", and /SPA/B flags whether each pixel comes from a plane or a sprite, "or always 1" [MDWIKI-PINOUT]. That would make the bits switch what three output pins carry, not what is drawn, and a frozen horizontal sync would also explain the distorted picture GENVDP saw with bit 5. No source says which bit chooses which, or how that was found. On a 32X they matter more than on a plain Mega Drive: the 32X takes the Mega Drive's /VSync and /HSync from the cartridge connector [32X-SVC §7-1]. Sega's start-up code writes `$81`, all three 0, in both the Mega Drive and the 32X initial programs, and no retail game read for this book sets them [AB-DISASM, initial program register table at `$0002A8`; SWA, initial program register table at `$0004D4`]. Leave them at 0.

**When changes take effect.** GENVDP reports that the interlace bits change only outside the active display, while every other bit in register 12 takes effect at once, even mid-line [GENVDP §17]. Changing screen width mid-frame is therefore possible, but it is not a documented feature.

## Register 15: auto-increment

After every read or write through the data port, the VDP adds register 15 to its address [MD-SWM §2.6]. The traps:

- **Use 2 for ordinary copies.** VRAM, CRAM and VSRAM are all word-wide from the CPU's side.
- **0 means no increment.** Every write lands on the same address [GENVDP §17]. That is occasionally useful and usually a bug.
- **An odd address swaps bytes.** The increment includes address bit 0, so an odd increment, or an odd starting address, makes every other word go to VRAM with its bytes swapped [MD-SWM §2.6]. Sega's initial program sets 1 because a byte-wide VRAM fill needs it. Set 2 again before writing anything else [AB-DISASM, initial program].
- **Use the increment to write a column.** To go down one column of a plane 64 tiles wide, each next entry is 128 bytes further on, so set `$80` and write one word per row. The same trick fills a column of the horizontal scroll table.
- **DMA uses it too.** Every DMA moves its destination by register 15 after each unit, so a DMA can scatter data down a column the same way [MD-SWM §2.7].
- **The address wraps.** Past `$FFFF` it goes back to 0 in VRAM. CRAM and VSRAM wrap past `$7F` [GENVDP §8-10].
- **Interrupt handlers must put it back.** If a handler changes register 15 for its own copy, the main program's next write goes to the wrong place. This is one more reason to [keep copies of the registers](#keeping-a-copy-of-the-registers) and to keep all VDP work in one place.

## The other registers

- **Register 7** picks the backdrop colour by palette (bits 5-4) and entry (bits 3-0). Entry 0 of each palette, which tiles cannot use because it is transparent, is a valid choice here [GENVDP §17].
- **Register 10** holds the line count for the line interrupt. It is reloaded every time it runs out; see [Timing, interrupts and counters](vdp-timing.md).
- **Register 16** sets the size of both planes in tiles. `00` = 32, `01` = 64, `11` = 128, `10` is not allowed. Only six combinations are allowed: 32 × 32, 32 × 64, 32 × 128, 64 × 32, 64 × 64 and 128 × 32. A name table never takes more than 8 KB [MD-SWM §2.1, §2.5]. With the horizontal size at `10`, the VDP repeats the first row of the table on every line [GENVDP §17].
- **Registers 17 and 18** place the window: a position in 2-tile columns or 8-line rows, and a bit that says whether the window is left of / above it or right of / below it. A position of 0 with the side bit at 0 turns the window off [GENVDP §17]. Details, and a bug at the window's edge, are in [Planes and scrolling](vdp-planes.md).
- **Registers 19-23** hold a DMA's length in words, its source address in words, and the mode in the top two bits of register 23: `0x` copy from 68000 memory (bit 6 is then source bit 23), `10` VRAM fill, `11` VRAM copy [MD-SWM §2.5]. A length of 0 counts as `$10000` [GENVDP §11]. The transfer itself starts with a memory command that has CD5 set; a VRAM copy also sets CD4 [GENVDP §7]. See [DMA](vdp-dma.md).

## The status register

Reading the control port returns [MD-SWM §2.4; GENVDP §6]:

| Bit | Name | 1 means |
|-----|------|---------|
| 9 | EMPT | The write FIFO is empty |
| 8 | FULL | The write FIFO is full: the next write will make the 68000 wait |
| 7 | F | A vertical interrupt has happened |
| 6 | SOVR | Too many sprites on a line: the 17th in 32 columns, the 21st in 40 columns |
| 5 | C | Two sprites' non-transparent pixels overlapped |
| 4 | ODD | Interlace mode, odd frame |
| 3 | VB | In vertical blank |
| 2 | HB | In horizontal blank |
| 1 | DMA | A DMA is running |
| 0 | PAL | PAL console (see below) |

Notes for using it:

- **Reading it also clears the VDP's "half a command written" state** [GENVDP §7; see [the overview](vdp.md#the-vdp-remembers-half-a-command)]. Don't read it between the two words of a command.
- **Bits 15-10 are not defined.** GENVDP saw them read as `001101` [GENVDP §6]. BlastEm, ares and Genesis Plus GX instead return open bus there, part of the last word the 68000 prefetched, and BlastEm's source says GENVDP is wrong on this <span class="tag disputed">disputed</span> [BLASTEM, vdp.c `vdp_status`; ARES, ares/md/vdp/io.cpp; GPGX, core/vdp_ctrl.c; [discrepancy 42](../appendices/discrepancies.md)]. Either way, mask them off before comparing.
- **DMA is only worth polling for fills and copies.** During a copy from 68000 memory the 68000 is stopped, so it can never see the bit set [GENVDP §6]. For fills and copies, wait for it to clear before touching the VDP again. GENVDP found that writing to the ports during a fill corrupts the registers and VRAM [GENVDP §11]. Aerobiz waits for it before rewriting register 15 [AB-DISASM, WaitVDPAndWrite.asm].
- **VB and HB follow the beam in real time.** Polling VB is a way to wait for vertical blank with interrupts off, and Sega suggests it where the vertical interrupt cannot be used <span class="tag manual">manual</span> [MD-TB, addendum 3 §4]. VB also reads 1 the whole time the display is switched off (register 1 bit 6 = 0), in all three emulators below <span class="tag emulator">emulator</span>.
- **F stays set until the 68000 takes the vertical interrupt.** No manual says when F, SOVR and C clear. GENVDP found that reading the status does not clear F [GENVDP §6]. Genesis Plus GX, ares and BlastEm all clear it only when the 68000 accepts the level 6 interrupt with vertical interrupts enabled <span class="tag emulator">emulator</span> [GPGX, core/vdp_ctrl.c; ARES, ares/md/vdp/irq.cpp; BLASTEM, vdp.c]. So with vertical interrupts off, F reads 1 from the first vertical blank on and cannot mark each frame. Poll VB instead.
- **Reading the status clears SOVR and C.** Two emulator authors report it from console tests: the collision flag is set while sprites are drawn and cleared as soon as the status is read, and both flags stay set until that read, through vertical blank [GENDEV-COLL]. They are set only while the display is on; whether turning the display off clears them was not tested. Genesis Plus GX, ares and BlastEm clear both on every status read <span class="tag emulator">emulator</span> [GPGX, core/vdp_ctrl.c `vdp_68k_ctrl_r`; ARES, ares/md/vdp/io.cpp `readControlPort`; BLASTEM, vdp.c `vdp_control_port_read`]. MAME does not: it clears C at the start of each frame and never sets SOVR [MAME, src/devices/video/315_5313.cpp]. ares, at the commit read, never sets SOVR either. Read the status once and keep the bits you need: a second read sees 0 until the next overflow or collision.
- **Many emulators always report the FIFO as empty**, so code that waits for EMPT to clear may never stop under emulation and may behave differently on a console [GENVDP §6].
- **PAL** follows the console, not the 240-line setting. The manuals call it "PAL mode", and GENVDP wondered whether it follows the 240-line setting [GENVDP §6]. But the VDP has a PAL/NTSC select input pin [GENVDP §18], and Genesis Plus GX, ares and BlastEm all set the bit from the console's region and nothing else <span class="tag emulator">emulator</span> [GPGX, core/loadrom.c; ARES, ares/md/vdp/io.cpp; BLASTEM, vdp.c]. The version register at `$A10001` gives the same information and is the documented place to read it [MD-SWM §4.1].

## Keeping a copy of the registers

Because the registers cannot be read, a game that wants to change one bit has to know the rest of the byte. The usual answer is a copy in RAM, updated by the same routine that writes the register.

Aerobiz Supersonic does it in a few instructions. One routine sends every register word to the control port, then takes the register number from bits 14-8 of the word and stores the value at that offset in a 24-byte table at `$FFF010`. Code that needs one bit, such as the DMA and vertical interrupt enables in register 1 or the plane size in register 16, reads the table, changes the bit and writes the result through the same routine. A second routine reads a value back for the game's C code [AB-DISASM, CmdSetVDPReg.asm, CmdGetVDPReg.asm, ConfigVDPScroll.asm].

```asm
; d0.w = register word $8rvv; a5 = copy of registers 0-23 in RAM
SetVdpReg:
        move.w  d0,$C00004       ; to the VDP
        move.w  d0,d1
        lsr.w   #8,d1
        andi.w  #$1F,d1          ; register number
        move.b  d0,(a5,d1.w)     ; and to the copy
        rts
```

Two rules make the copy trustworthy. Every register write goes through this routine, including those in interrupt handlers, and nothing else writes the copy. A copy that drifts from the hardware is worse than none.

## Reading other people's code

Disassembly comments are only as good as their author's reading of the VDP, so check constants yourself. Two names in the Aerobiz disassembly show why:

- `CmdGetVDPStatus` reads `$C00008`, the H/V counter, not the status register [AB-DISASM, CmdGetVDPStatus.asm].
- `ConfigVDPScroll` writes `$C0` to register 23 and sends a command with `$C0` in its low byte. That is a VRAM copy (DMA mode `11`, code bits CD5 and CD4 set), not a scroll setting [AB-DISASM, ConfigVDPScroll.asm].

A register word decodes the same way every time: the high byte minus `$80` is the register number and the low byte is the value. A command decodes with the table in [the overview](vdp.md#two-kinds-of-control-word).

## Where the sources differ

| Register bits | Sega's manuals | GENVDP |
|---------------|----------------|--------|
| Reg 0 bit 2 | Always 1 | 0 limits the colours to 8 |
| Reg 0 bit 0 | Always 0 | 1 turns off the display completely; unlike DISP, the backdrop is not shown either |
| Reg 1 bit 7 | Always 0 | 1 selects a Master System text-like mode |
| Reg 11 HSCR/LSCR `01` | Not allowed | Per-line scroll using only the first 8 lines' entries, repeated |
| Reg 12 LSM `10` | Not allowed | Same as no interlace |
| Reg 12 RS `01` / `10` | Not allowed | `01` = distorted 40 columns, `10` = invalid |
| Reg 15 = 0 | Not described | No increment |

Sources: [MD-TO pp.22-25; GENVDP §17]. None of these is a disagreement about a documented setting: GENVDP tried settings the manuals forbid and reported what happened. Stay with the documented values. The table is here so a strange value in a disassembly can be recognised.

Two errors in the text copies used for this book should not be mistaken for hardware facts:

- The MD-SWM transcription shows registers 0 and 1 without M3, M1 and M2, and puts IE1 in bit 5. It also says plane A sits on `$400` boundaries. The scanned MD-TO, which reproduces the same register pages, and GENVDP both have IE1 in bit 4, all three mode bits, and plane A on `$2000` boundaries [MD-TO p.22].
- GENVDP's text for register 4 says bits 2-0 are A15-A11. Three bits can only be A15-A13, as Sega's diagram shows.

## Open questions

- Does anything besides a status read clear SOVR and C, for example turning the display off? The console reports cover only the read and vertical blank, and name no console model.
- Which of bits 4 to 6 of register 12 selects which pin function, and does a 32X lose sync when bit 5 or 6 is set? Only an oscilloscope on the /VSync, /HSync and /SPA/B pins, or a 32X under test, can tell.

## Sources

- [MD-TO](../appendices/bibliography.md#md-to): pp.22-26 VDP registers (scan checked for registers 0-3)
- [MD-SWM](../appendices/bibliography.md#md-swm): §2.4 status register, §2.5 registers, §2.6 auto-increment, §2.7 DMA
- [GENVDP](../appendices/bibliography.md#genvdp): §6 status register, §7 ports, §8-11, §17 registers, §18 pinout
- [GPGX](../appendices/bibliography.md#gpgx): core/vdp_ctrl.c (`vdp_68k_ctrl_r`, interrupt acknowledge), core/system.c, core/loadrom.c
- [ARES](../appendices/bibliography.md#ares): ares/md/vdp/io.cpp (`readControlPort`, register 12), irq.cpp, main.cpp, vdp.hpp
- [BLASTEM](../appendices/bibliography.md#blastem): vdp.c (`vdp_status`, `vdp_control_port_read`, interrupt acknowledge), vdp.h
- [MD-TB](../appendices/bibliography.md#md-tb): addendum 3 §4
- [GENDEV-COLL](../appendices/bibliography.md#gendev-coll): console tests of the collision and overflow flags
- [MDWIKI-PINOUT](../appendices/bibliography.md#mdwiki-pinout): VDP pin functions
- [MAME](../appendices/bibliography.md#mame): src/devices/video/315_5313.cpp (status read, register 12)
- [32X-SVC](../appendices/bibliography.md#32x-svc): §7-1, the cartridge connector signals the 32X takes
- [SWA](../appendices/bibliography.md#swa): 32X initial program register table at `$0004D4`
- [AB-DISASM](../appendices/bibliography.md#ab-disasm): initial program register table, CmdSetVDPReg, CmdGetVDPReg, CmdGetVDPStatus, ConfigVDPScroll, WaitVDPAndWrite
