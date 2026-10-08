# System architecture

The Mega Drive is two computers sharing one box. The 68000 runs the game. The Z80 was carried over from the Master System and normally runs the sound. Between them sit the VDP, which owns the picture and its own memory, and a bus arbiter that decides who may use which bus. Knowing who owns what, and who can stop whom, explains most of the rules in the rest of Part I.

## The parts

| Part | What it is | Notes |
|------|------------|-------|
| 68000 | Main CPU, 16-bit data bus, 24-bit addresses | 7.67 MHz (NTSC), 7.60 MHz (PAL) |
| Work RAM | 64 KB | On the 68000's bus |
| VDP (315-5313) | Video chip: two scrolling planes, sprites, DMA, interrupts | Owns its own memory. Also contains the PSG |
| VRAM | 64 KB of video memory | Only reachable through the VDP |
| CRAM, VSRAM | 64 colours, and vertical scroll values | Inside the VDP |
| Z80 | 8-bit CPU, normally the sound processor | About 3.58 MHz (NTSC) |
| Sound RAM | 8 KB | On the Z80's bus |
| YM2612 | Six-channel FM sound chip | On the Z80's bus |
| PSG (SN76489 type) | Four-channel square wave and noise | Built into the VDP |
| I/O chip | Three controller ports, the version register | On the 68000's bus |
| Cartridge | Up to 4 MB in the normal map, plus any save RAM | On the 68000's bus |

Sources: [MD-TO, system overview; MD-SWM §1, §4.1; GENVDP, pinout]. The PSG is part of the VDP chip: the VDP has a PSG audio output pin, and both CPUs reach the PSG through VDP addresses [GENVDP, pinout; MD-SWM §1].

## How they connect

```text
                               cartridge (ROM, save RAM)
                                         │
  ┌───────┐                              │
  │ 68000 ├──────────────────── 68000 bus (main bus) ───────────────────────┐
  └───────┘        │                     │                   │              │
             work RAM 64 KB      ┌───────┴───────┐       I/O chip      bus arbiter
                                 │ VDP  (+ PSG)  │   pads, version          │
                                 └───────┬───────┘                          │
                                     VRAM 64 KB                ┌────────────┴───────┐
                                                               │      Z80 bus       │
                                                               │  Z80, 8 KB RAM,    │
                                                               │  YM2612            │
                                                               └────────────────────┘
```

Four rules come out of this picture:

- **The 68000 owns the main bus.** The VDP and the Z80 can each borrow it, and while they do, the 68000 waits. VDP DMA from 68000 memory into VRAM takes the 68000 off the bus for the whole transfer [MD-TO, system overview]. See [DMA](vdp-dma.md).
- **The Z80 has a bus of its own.** The 68000 can only reach Z80 memory and the YM2612 after stopping the Z80 [MD-SWM §4.4]. The Z80 can reach the main bus through a 32 KB window, borrowing it from the 68000 for each access [MD-SWM §4.5].
- **VRAM belongs to the VDP.** Neither CPU can address it. Everything that goes into VRAM passes through the VDP's ports at `$C00000`, by CPU writes or by DMA [MD-SWM §2.2]. See [Registers and access](vdp-registers.md).
- **The VDP raises every 68000 interrupt.** Vertical blank is level 6, horizontal is level 4 and the external interrupt (from the controller port) is level 2, all through the 68000's autovectors [MD-SWM §2.3]. See [Timing, interrupts and counters](vdp-timing.md).

## Clocks

Every clock in the machine is a division of one master crystal:

| | NTSC | PAL | Derivation |
|---|---|---|---|
| Master clock | 53.693175 MHz | 53.203424 MHz | Crystal |
| 68000, YM2612 | 7.670454 MHz | 7.600489 MHz | Master ÷ 7 |
| Z80, PSG | 3.579545 MHz | 3.546895 MHz | Master ÷ 15 |

Sources: the master clock figures are from the 32X Hardware Manual, which lists the Mega Drive's [32X-HWM §3.3, clock]. The 68000 figures are confirmed by the version register description [MD-SWM §4.1]. The ÷ 15 for the Z80 and PSG, and the ÷ 7 for the YM2612, come from the PicoDrive emulator <span class="tag emulator">emulator</span> [PICODRIVE, pico_int.h, sound.c]. Sega's early overview rounds to 8 MHz and 4 MHz [MD-TO, system overview], and the sound manual's YM2612 timer formulas assume 8 MHz [MD-SWM, YM2612 timers]. Charles MacDonald's VDP notes give the master clock as 53.64165 MHz [GENVDP, pinout], but every clock in Sega's manuals follows from the 32X-HWM figures, so that figure is an error <span class="tag manual">manual</span> ([discrepancy #9](../appendices/discrepancies.md)).

Because the 68000 runs at exactly 15/7 the speed of the Z80, the two stay in step. Each one's cycle counts can be converted into the other's with no drift.

## Frame timing

A scan line lasts 3,420 master clocks: 2,560 for the 320 visible pixels and 860 for horizontal blanking [32X-HWM §3.3, H-blank and display periods]. That is 63.7 µs on NTSC, the figure Sega's own interrupt timing diagram uses [MD-SDM §5]. From this:

| | NTSC | PAL |
|---|---|---|
| Lines per frame | 262 | 313 |
| Visible lines | 224 | 224 or 240 |
| Frames per second | 59.92 | 49.70 |
| 68000 cycles per line | 488.6 | 488.6 |
| 68000 cycles per frame | about 128,000 | about 152,900 |
| Z80 cycles per line | 228 | 228 |

The line counts are from the manuals [MD-SWM §2.1; 32X-HWM §3.3]. The rest is calculated from the clocks above. The Software Manual gives PAL as 312 lines, but its visible and blanking counts add up to 322, and its own DMA table fits 313. The 32X Hardware Manual's counts add up to its 313 <span class="tag disputed">disputed</span> [MD-SWM §2.1; 32X-HWM §3.3; [discrepancy #8](../appendices/discrepancies.md)].

The 128,000 figure is the 68000's whole budget for one NTSC frame, before DMA and the Z80 take their share. A PAL machine has about 19% more time per frame but runs 17% fewer frames per second, so a game tuned for NTSC runs slower in PAL unless it adjusts. See [Holding 60 frames per second](../patterns/60fps.md).

## The 68000 memory map

| Address | Contents |
|---------|----------|
| `$000000-$3FFFFF` | Cartridge, up to 4 MB |
| `$400000-$7FFFFF` | Expansion: the Mega-CD lives here when attached |
| `$800000-$9FFFFF` | Reserved. The 32X uses it when attached |
| `$A00000-$A0FFFF` | The Z80's address space, when the 68000 holds the Z80 bus |
| `$A10000-$A1001F` | I/O chip: version register, three controller ports |
| `$A11000` | Memory mode (development hardware only) |
| `$A11100` | Z80 bus request |
| `$A11200` | Z80 reset |
| `$A130xx` | Cartridge registers (bank switching, save RAM control) |
| `$A14000` | TMSS: write `SEGA` here on consoles with a non-zero version number |
| `$C00000-$C00003` | VDP data port |
| `$C00004-$C00007` | VDP control port |
| `$C00008-$C0000F` | VDP H/V counter |
| `$C00011` | PSG |
| `$E00000-$FEFFFF` | Do not use |
| `$FF0000-$FFFFFF` | Work RAM |

Sources: [MD-SWM §1; MD-TO §1; MD-TB, address checker memory map; 32X-HWM §3.1 p.14]. The VDP's ports respond at more than one address each, so the PSG also appears at `$C00013`, `$C00015` and `$C00017` [GENVDP §3]. Use the addresses in the table.

Some practical notes:

- **Work RAM can be reached with short addresses.** The 68000's absolute short addressing mode sign-extends a 16-bit address. `$8000-$FFFF` becomes `$FFFF8000-$FFFFFFFF`, and with only 24 address lines that is `$FF8000-$FFFFFF`, the top 32 KB of work RAM. Variables placed there cost one fewer word per instruction and run faster [M68K-PRM §2]. See [The 68000 for Mega Drive work](m68k.md).
- **The I/O and control registers are on odd bytes** (`$A10001`, `$A10003`), or bit 8 of a word (`$A11100`, `$A11200`) [MD-SWM §4]. See [Controllers and I/O ports](io.md).
- **`$A130xx` belongs to the cartridge.** Cartridges larger than 4 MB use registers at `$A130F1-$A130FF` to switch banks, and must only be touched with care on a 32X [32X-HWM §3.1 p.14; MD-TB, address checker memory map]. See [Cartridge hardware](cartridge.md).
- **With a 32X attached, the cartridge moves.** See [Architecture and memory maps](../32x/architecture.md).

## The Z80 memory map

| Z80 address | Contents |
|-------------|----------|
| `$0000-$1FFF` | Sound RAM, 8 KB |
| `$2000-$3FFF` | Reserved |
| `$4000-$4003` | YM2612: address and data for part I (`$4000`, `$4001`) and part II (`$4002`, `$4003`) |
| `$6000` | Bank register |
| `$7F11` | PSG |
| `$8000-$FFFF` | A 32 KB window onto the 68000's address space |

Sources: [MD-SWM §1; MD-TO §1].

The 68000 sees this space at `$A00000`. `$A00000-$A01FFF` is sound RAM, `$A04000` the YM2612, `$A06000` the bank register [MD-SWM §4.5]. Only byte accesses are allowed in this area [MD-SWM §4.5].

### The bank window

The window at Z80 `$8000-$FFFF` can show any 32 KB of the 68000's 16 MB. The bank register holds address bits 15-23 of the window's start. It is written one bit at a time: nine single-byte writes to `$6000`, each using only bit 0. The first write carries A15 and the ninth A23, as shipped drivers show; MD-SWM's table has the order backwards ([discrepancy 35](../appendices/discrepancies.md)) [MD-SWM §4.5; PICODRIVE, memory.c]. Only the Z80 may set it [MD-SWM §4.5]. A sound driver that plays samples straight from the cartridge points the window at its sample data and reads through it.

Every access through the window is a 68000 bus cycle. The Z80 waits for the main bus, and the 68000 is held off while the Z80 has it. PicoDrive charges the Z80 about 3.3 extra cycles for each one <span class="tag emulator">emulator</span> [PICODRIVE, memory.c]. Streaming samples this way costs both CPUs a little time on every byte.

Two documented restrictions apply:

- **Right after the 68000 touches `$A100xx`, a Z80 access to the main bus can read or write the wrong data.** That range covers the controller ports. The cure is to stop the Z80 with a bus request around the 68000's access to `$A100xx` <span class="tag manual">manual</span> [MD-SDM §5; MD-TB, Z80/68000 bus access issues].
- **The Z80 can write work RAM through the window, but not read it.** Sega's manual says only that the window reaches all of 68000 memory [MD-SWM, Z80 mapping], and the 32X bulletin lists work RAM as writable by the Z80 [32X-TI item 15]. Reads of `$E00000` and up return `$FF`, not the RAM's contents: Charles MacDonald saw this on a console [GENDEV-Z80, 17 October 2011], and Genesis Plus GX, PicoDrive and ares do the same <span class="tag emulator">emulator</span> [GPGX, core/genesis.c; PICODRIVE, memory.c; [discrepancy #10](../appendices/discrepancies.md)]. Pass data to the Z80 through its own RAM instead.

## Who can stop whom

| Who | Stops whom | How | Where to read more |
|-----|------------|-----|--------------------|
| 68000 | Z80 | Bus request at `$A11100`: write `$0100`, wait until bit 8 reads 0, access the Z80 area, write `$0000` | [Z80 bus control](z80.md) |
| 68000 | Z80 | Reset at `$A11200`: write 0 to hold the Z80 in reset, `$0100` to let it run | [Z80 bus control](z80.md) |
| VDP | 68000 | DMA from 68000 memory: the 68000 is off the bus until the transfer ends | [DMA](vdp-dma.md) |
| Z80 | 68000 | Each access through the bank window borrows the main bus for one cycle | above |
| VDP | 68000 | Interrupts at levels 6, 4 and 2 | [Timing, interrupts and counters](vdp-timing.md) |
| VDP | Z80 | One interrupt per frame, at vertical blank | [Z80 bus control](z80.md) |

Sources: [MD-SWM §2.3, §4.4; MD-TO, system overview]. The Z80's only interrupt is the vertical blank interrupt, every 16 ms and about 64 µs long, which is one line [MD-SWM, sound software manual §I.2]. PicoDrive raises it at the start of vertical blank and holds it for one line, in agreement <span class="tag emulator">emulator</span> [PICODRIVE, pico_cmn.c].

Three things to keep in mind:

- **At power-on the Z80 is held in reset** [MD-SWM §4.4]. Load its program while it is held, then release it.
- **Bus requests do not nest.** If the main program requests the Z80 bus and an interrupt handler does the same, the handler's release also releases the main program's request. The main program then writes Z80 RAM while the Z80 is running, and the sound program gets corrupted. Either disable interrupts around the main program's bus request, or never take the Z80 bus inside interrupt handlers <span class="tag manual">manual</span> [MD-TB, bulletin 3; MD-SDM §5].
- **A long DMA delays everything that needs the main bus**, including a Z80 that is reading samples through the window. Sample playback can stutter if DMA runs while the Z80 streams from the cartridge.

## What to take away

- Plan each frame around about 128,000 68000 cycles on NTSC, minus what DMA takes.
- Everything that goes into VRAM passes through the VDP. Nothing else can reach it.
- Treat the Z80 bus as borrowed. Take it briefly, never from two places at once, and give it back.
- Assume every Z80 access to the main bus costs both CPUs time.

## Open questions

- Measure the master clock and the ÷ 15 Z80 divider on a real console ([discrepancy #9](../appendices/discrepancies.md)).
- Confirm the PAL line count ([discrepancy #8](../appendices/discrepancies.md)).
- Measure the cost of a Z80 bank window access to both CPUs.

## Sources

- [MD-TO](../appendices/bibliography.md#md-to): system overview, §1 memory map
- [MD-SWM](../appendices/bibliography.md#md-swm): §1 memory map, §2.1 display specification, §2.3 interrupts, §4 system I/O, Z80 mapping, YM2612 timers
- [MD-SDM](../appendices/bibliography.md#md-sdm): §5 precautions
- [MD-TB](../appendices/bibliography.md#md-tb): bulletin 3, Z80/68000 bus access issues, address checker memory map
- [GENVDP](../appendices/bibliography.md#genvdp): §3 port map, pinout
- [M68K-PRM](../appendices/bibliography.md#m68k-prm): §2 addressing modes
- [32X-HWM](../appendices/bibliography.md#32x-hwm): §3.1, §3.3 clocks and line timing
- [32X-TI](../appendices/bibliography.md#32x-ti): item 15
- [VRD-NOTES](../appendices/bibliography.md#vrd-notes): PicoDrive source
