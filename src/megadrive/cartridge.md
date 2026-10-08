# Cartridge hardware

A Mega Drive cartridge is little more than memory on the 68000's bus. It holds ROM, sometimes battery-backed save RAM, and, in the largest games, a chip that switches banks of ROM in and out. This chapter covers what the console expects from a cartridge, the chips games used, and the development boards Sega provided for 32X-era work.

## What the cartridge sees

The cartridge slot carries the 68000's address and data buses, so a cartridge simply answers 68000 reads and writes in its part of the memory map:

| 68000 address | What the cartridge can put there |
|---------------|----------------------------------|
| `$000000-$3FFFFF` | ROM, up to 4 MB, and save RAM from `$200000` up |
| `$A130xx` | Cartridge registers: bank switching and save RAM control |

Sources: [MD-SWM §1; MD-TB, address checker memory map; BD-4M §3].

- **The bus is 16 bits wide.** Even addresses are the upper byte, on data lines D8-D15. Odd addresses are the lower byte, on D0-D7. Sega's EPROM boards make this concrete: each pair of 8-bit EPROMs has one chip for the even bytes and one for the odd [BD-4M §4]. A 16-bit ROM chip serves both at once.
- **The cartridge tells the console it is there** through a cartridge-present signal. Sega's development boards have a switch to connect or disconnect it [BD-4M §3.3]. On the 32X, the same signal is readable by the SH-2s as the CART bit [32X-HWM §3.2.2].
- **A cartridge can put the console in Master System mode.** One cartridge pin forces the VDP into its Master System graphics mode [GENVDP, pinout]. Mega Drive cartridges leave it alone.
- **The console can refresh dynamic RAM on a cartridge.** Writing 1 to bit 8 of `$A11000` turns on refresh signals for development cartridges built from dynamic RAM. Production cartridges must leave it at 0 (ROM mode) [MD-SWM §4.3]. Pseudo-static RAM such as Hitachi's HM65256B also needs regular refresh, 256 cycles every 4 ms [DS-HM65256B].

**The connector has 64 contacts, in rows A and B of 32.** Sega's service manual for the 32X draws the plug that goes into the Mega Drive's slot, which is the same connector a cartridge uses. The names are as the 32X schematic prints them: `VA` and `VD` are the 68000's address and data lines, a leading `-` marks a signal that is active low, and an `M` marks a signal from the Mega Drive side [32X-SVC §7-1, P1].

| Pin | Row A | Row B |
|-----|-------|-------|
| 1 | `GND` | `SL1` |
| 2 | `+5V` | `-MMRES` |
| 3 | `VA8` | `SR1` |
| 4 | `VA11` | `VA9` |
| 5 | `VA7` | `VA10` |
| 6 | `VA12` | `VA18` |
| 7 | `VA6` | `VA19` |
| 8 | `VA13` | `VA20` |
| 9 | `VA5` | `VA21` |
| 10 | `VA14` | `VA22` |
| 11 | `VA4` | `VA23` |
| 12 | `VA15` | `-MYS` |
| 13 | `VA3` | `-MVSYNC` |
| 14 | `VA16` | `-MHSYNC` |
| 15 | `VA2` | `EDCLK` |
| 16 | `VA17` | `-MCAS0` |
| 17 | `VA1` | `-MCE0` |
| 18 | `GND` | `-AS` |
| 19 | `VD7` | `MVCLK` |
| 20 | `VD0` | `-MDTAK` |
| 21 | `VD8` | `-MCAS2` |
| 22 | `VD6` | `VD15` |
| 23 | `VD1` | `VD14` |
| 24 | `VD9` | `VD13` |
| 25 | `VD5` | `VD12` |
| 26 | `VD2` | `-MASEL` |
| 27 | `VD10` | `-MVRES` |
| 28 | `VD4` | `-MLWR` |
| 29 | `VD3` | `-MUWR` |
| 30 | `VD11` | `-M3` |
| 31 | `+5V` | `-TIME` |
| 32 | `GND` | `-MCART` |

Some of these the book can name with confidence. There is no `VA0`: the bus is 16 bits wide, and byte selection uses the separate upper and lower write strobes (`-MUWR`, `-MLWR`). `-MCART` is the cartridge-present signal and `-M3` the pin that selects Master System mode, both described above. `-TIME` presumably selects the `$A130xx` register area and `-MCE0` the ROM area, `SL1` and `SR1` carry sound from the cartridge: on the 32X they go to the inputs its audio mixer chip names `ROMIN1` and `ROMIN2` [32X-SVC §7-4]; `-MVRES` and `-MMRES` are the two resets, and `-MVSYNC`, `-MHSYNC`, `-MYS` and `EDCLK` are video timing and the pixel clock, which the 32X needs to merge its picture with the Mega Drive's. The schematic does not explain `-MCAS0`, `-MCAS2`, `-MASEL` or `-MDTAK`.

## ROM

Cartridge ROM sits at `$000000` and is read 16 bits at a time. Two representative parts from the bibliography:

| | Fujitsu MB838200B | ST M27C322 |
|---|---|---|
| Type | Mask ROM, programmed at the factory | UV-erasable EPROM (or one-time PROM) |
| Size | 8 Mbit (1 MB) | 32 Mbit (4 MB) |
| Organisation | 512K × 16, or 1M × 8 using a BYTE pin | 2M × 16 |
| Access time | 120 ns | 80 ns |
| Package | 42-pin DIP, 44-pin SOP, 48-pin TSOP | 42-pin DIP |

Sources: [DS-MB838200B; DS-M27C322]. The M27C322 is pin-compatible with 32 Mbit mask ROMs, so an EPROM can stand in for a production chip [DS-M27C322].

Speed matters most on the 32X, where the SH-2s read the cartridge too. Sega asked for EPROMs of 120 ns or faster on 32X development cartridges [32X-TI item 18]. The earlier Mega Drive EPROM boards took 150 ns parts [MD-TB, EPROM list; BD-4M §1].

## Save RAM

Most games that save use a small battery-backed static RAM. Sega defined two standard sizes, both on odd addresses only [MD-SDM §7]:

| Size | Addresses |
|------|-----------|
| 64 Kbit (8 KB) | odd addresses in `$200000-$203FFF` |
| 256 Kbit (32 KB) | odd addresses in `$200000-$20FFFF` |

The RAM is 8 bits wide and wired to the lower byte only, so consecutive save bytes are two addresses apart. The header's external RAM field at `$1B0` describes it (see [Mega Drive ROM header and checksum](../howto/md-header.md#1b0-external-ram)).

*Aerobiz Supersonic* uses the 8 KB type. Its save code walks odd addresses in steps of two, starting from `$200003`, keeps a checksum per save slot, and checks it before loading [AB-DISASM].

Sega's rules for save RAM are short and still good advice <span class="tag manual">manual</span> [MD-SDM §7]:

- **Assume nothing about the contents.** A new cartridge's RAM is often all `$FF`, but not always. Initialise it the first time you find it invalid.
- **Check it every time.** Save data can occasionally be corrupted. Keep a checksum and treat a mismatch as an empty save.
- **Avoid the first and last word.** They are the most likely to be corrupted, for example as the power goes off. Keep important data away from them.

### When ROM and save RAM overlap

In a game of 2 MB (16 Mbit) or less, ROM ends below `$200000`, and the save RAM simply sits there with nothing to switch. *Aerobiz Supersonic* is 1 MB and never touches the cartridge registers [AB-DISASM].

A larger game has ROM at `$200000` too. Then bit 0 of the register at `$A130F1` chooses which one answers there: 0 for ROM, 1 for save RAM. Bit 1 protects the save RAM from writes when set [BD-4M §3; BD-16M §3; BD-32M §3]. These boards describe Sega's bank chip, covered next. Production cartridges with other mapping hardware may differ. One shipped cartridge behaves as the boards describe: *Knuckles' Chaotix* is 3 MB, its header puts 512 bytes of battery-backed save RAM on the odd addresses of `$200001-$2003FF`, inside its own ROM, and its save code writes 3, 1 and 2 to `$A130F1` ([below](#save-ram-on-the-32x)) [CHAOTIX, header; 68000 code at `$03E392`, `$03E420`].

### Other kinds of save memory

The header also has codes for serial EEPROMs, which are read and written a bit at a time through a few control lines instead of being mapped as memory [MD-SDM §3]. On the 32X, Sega's bulletin distinguishes SRAM, which works regardless of the RV bit, from FRAM (ferroelectric RAM), which needs RV = 1 to be read or written [32X-TI item 7].

## Bank switching beyond 4 MB

The 68000's cartridge area is 4 MB. Sega's bank chip, the 315-5709, makes more ROM reachable by switching it in 512 KB pieces [BD-4M §3; BD-16M §3]:

- The 4 MB area is split into eight **areas** of 512 KB each, at `$000000`, `$080000`, `$100000` and so on up to `$380000`.
- **Area 0 is fixed** to the first 512 KB of ROM, because it holds the vectors and the startup code.
- Areas 1 to 7 each have a register, at `$A130F3`, `$A130F5`, … `$A130FF`. The number written there (0 to 63) selects which 512 KB **bank** of ROM appears in that area. 64 banks of 512 KB is 32 MB.
- At power-on and reset, area *n* shows bank *n*. That is the plain linear layout, so a game that never writes the registers sees its first 4 MB unchanged.
- Register 0 at `$A130F1` holds the save RAM switch and write protect described above.

The registers are byte-wide and live on odd addresses [MD-TB, address checker memory map; BD-4M §3]. Writing a bank number that has no ROM behind it gives garbage [BD-16M §3].

Emulators have no bank chip to detect, so they decide from the ROM whether to emulate one. The 32X homebrew toolchains ask for it by putting `SEGA SSF` in the header's system name instead of `SEGA 32X` <span class="tag emulator">emulator</span> [S32X-SKILL, architecture]. A flash cartridge may have its own rule.

### On the 32X

The 32X adds two complications. Its own bank register at `$A15104` selects which megabyte the 68000 sees at `$900000` (see [Architecture and memory maps](../32x/architecture.md#after-the-32x-is-switched-on-aden--1)). The Mega Drive bank chip's registers at `$A130F1-$A130FF` may only be written while RV = 1 [32X-HWM §3.1 p.14]. Code in the cartridge cannot set RV and keep running, so the 32X's vector ROM provides two small routines for this. The one at `$0000C0` writes one byte. The one at `$0000D4` writes all eight registers from a table [VRD-NOTES, 32X BIOS dump].

Sega also required 32X games of more than 16 Mbit, with or without a bank chip, to do a short initialisation after power-on. They must read `$A130F1` once, then call the routine at `$0000C0` with `$A130F1` in `a1` and 0 in `d0`, with interrupts masked. That puts ROM back at `$200000-$3FFFFF` <span class="tag manual">manual</span> [32X-TI item 8]. Neither Mortal Kombat II (32 Mbit) nor Star Wars Arcade (20 Mbit) does it; Knuckles' Chaotix (24 Mbit) does ([Hardware bugs and workarounds](../32x/bugs.md#cartridges-over-16-mbit)).

### Save RAM on the 32X

The d32xr Doom port shows one complete way to reach save RAM with the 32X on. Its 68000 does every save access itself, one byte at a time, from code in work RAM [D32XR, src-md/crt0.s]:

1. Mask 68000 interrupts.
2. Park both SH-2s. The 68000 raises the command interrupt on both, and each SH-2's handler writes `$A55A` to its communication word (`$A15120` for the Master, `$A15124` for the Slave) and waits there, away from the cartridge.
3. Set RV.
4. Write `$A130F1`: 3 to enable save RAM read-only, or 1 to enable it for writing.
5. Read or write the byte at `$200001` plus twice the offset.
6. Write 2 to `$A130F1` to disable and write-protect save RAM again, then clear RV.
7. Release the SH-2s and unmask interrupts.

Taking the save RAM out of the map after each access means a stray write cannot reach it, and parking the SH-2s keeps them off the cartridge while RV is set. Sega's bulletin says RV does not matter to SRAM [32X-TI item 7]. d32xr sets it anyway, for the bank chip register writes if nothing else.

*Knuckles' Chaotix*, the one shipped 32X game in the sources that saves, does the same with a whole save at a time [CHAOTIX, 68000 code at `$03E322`-`$03E4B8`]:

1. Mask 68000 interrupts and quiet the other processors. It asks the Z80's sound driver to pause (1 written to Z80 `$1C10`, `$80` afterwards) and writes `$0015` to the four communication words at `$A15128-$A1512F`, which its Slave reads as sound requests ([PWM audio](../32x/pwm.md#1-the-pwm-interrupt-star-wars-arcade)). Then it waits for the Master's command word at `$A15120` to read 0, followed by a delay loop. There is no handshake that stops the SH-2s, as d32xr has.
2. Copy a 64-byte routine to work RAM at `$FF0200` and call it, because setting RV takes the cartridge away from `$880000`, where the game's code runs.
3. In that routine: set RV, write 3 (to load) or 1 (to save) to `$A130F1`, move 256 bytes one at a time between work RAM and every second address, write 2 to put ROM back with the save RAM write-protected, and clear RV.
4. Keep two copies, at `$200001` and `$200201`, each starting with a checksum of the rest. Saving writes both; loading reads the second only if the first fails its check.

Both programs set RV around every save access and leave `$A130F1` at 2 afterwards. Only Chaotix shipped, so its sequence is the one known to work on retail hardware with a cartridge that has ROM at `$200000`.

## Sega's development boards

For 32X-era development, Sega of America supplied three cartridge boards. All use the same 315-5709 bank chip and register layout, so code written for them runs unchanged on a production cartridge with that chip [BD-4M; BD-16M; BD-32M]:

| | IC BD 4M | IC BD 16M | IC BD 32M |
|---|---|---|---|
| Product number | 837-11069 | 837-11070 | 837-11068 |
| Program memory | Up to 8 × 4 Mbit EPROMs (TC574000AD, 150 ns): 32 Mbit | 4 × 16 Mbit or 4 × 8 Mbit EPROMs (TC5716200D / TC578200D, 150 ns): 64 or 32 Mbit | 32 Mbit battery-backed SRAM (HM628128, 100 ns), rewritable in place |
| Save RAM | 256 Kbit, battery-backed | 256 Kbit, battery-backed | 256 Kbit, 512 Kbit or 1 Mbit, battery-backed |
| Valid bank numbers | 0-7 | 0-15 (16 Mbit parts) or 0-7 | 0-7 |

Each board has two memory modes, chosen by DIP switches [BD-4M §3.1-3.2]:

- **32M mode** (the factory setting): the bank registers work, and the whole 4 MB area is ROM at power-on.
- **16M mode**: ROM at `$000000-$1FFFFF` and save RAM from `$200000`, the classic layout for a 16 Mbit game with saves. The bank registers must not be written in this mode.

The SRAM board adds a write-enable register at `$A130F0`, bit 15. It is 0 at power-on, which makes the program memory read-only so a crashing program cannot overwrite itself. Set it to 1 to load new code, and an LED flashes while writes are enabled [BD-32M §3]. The board also has LEDs that warn of a low battery [BD-32M §1].

Older Mega Drive boards needed modifications to work with the 32X, listed in Sega's 32X bulletin [32X-TI items 1-3].

## What to take away

- Treat everything between `$000000` and `$3FFFFF` as the cartridge's business, and `$A130xx` as its control registers.
- Save RAM is usually 8 or 32 KB on odd addresses from `$200001`. Checksum it, and avoid its first and last word.
- Games over 2 MB with saves have to switch `$200000` between ROM and RAM. Games over 4 MB switch 512 KB banks through `$A130F3-$A130FF`.
- On the 32X, write the bank chip only with RV = 1, through the vector ROM's routines.

## Open questions

- Whether save RAM at `$200001` answers on hardware while the 32X is on and RV = 0, without the bank chip register being written. Aerobiz Ultimate saves and loads that way under PicoDrive <span class="tag emulator">emulator</span>, based on Sega's statement that RV does not matter for SRAM [AU-NOTES, save and load; 32X-TI item 7]. On Ares, its save did not survive a power cycle [AU-NOTES, Ares runs]. Sega's own memory map argues against it: with ADEN = 1 the 68000 reaches the cartridge's `$000100-$3FFFFF` only while RV = 1, so with RV = 0 an access to `$200001` should not reach the cartridge at all [32X-HWM §3.1 p.13, Figure 3.1]. Ares follows that map, upstream PicoDrive does not, and the save's fate in each fits. Item 7 may then mean that SRAM, unlike FRAM, works through the `$900000` window with RV = 0, with bank 2 at `$A15104` showing it at `$900001`; nothing in the sources tries that. Chaotix's and d32xr's sequences above, with RV set, are the conservative choice until this is tested.
- Which chip Knuckles' Chaotix's cartridge uses to switch `$200000` between ROM and save RAM: Sega's bank chip, or simpler logic that only answers `$A130F1`. Its code names none of `$A130F3-$A130FF` by an absolute address and never calls the vector ROM's routine that writes them [CHAOTIX, ROM searched].

## Sources

- [MD-SWM](../appendices/bibliography.md#md-swm): §1 memory map, §4.3 memory mode
- [MD-SDM](../appendices/bibliography.md#md-sdm): §3 external RAM information, §7 notes on the backup RAMs
- [MD-TB](../appendices/bibliography.md#md-tb): address checker memory map, EPROM list
- [BD-4M](../appendices/bibliography.md#bd-4m), [BD-16M](../appendices/bibliography.md#bd-16m), [BD-32M](../appendices/bibliography.md#bd-32m): bank registers, memory modes, board specifications
- [DS-MB838200B](../appendices/bibliography.md#ds-mb838200b), [DS-M27C322](../appendices/bibliography.md#ds-m27c322), [DS-HM65256B](../appendices/bibliography.md#ds-hm65256b): parts
- [32X-HWM](../appendices/bibliography.md#32x-hwm): §3.1 pp.13-14 (Figure 3.1), §3.2.2
- [32X-SVC](../appendices/bibliography.md#32x-svc): §7-1 edge connector P1, §7-4 audio mixer inputs
- [32X-TI](../appendices/bibliography.md#32x-ti): items 1-3, 7, 8, 18
- [GENVDP](../appendices/bibliography.md#genvdp): pinout
- [VRD-NOTES](../appendices/bibliography.md#vrd-notes): 32X BIOS dump
- [AB-DISASM](../appendices/bibliography.md#ab-disasm): save RAM routines
- [AU-NOTES](../appendices/bibliography.md#au-notes): save RAM under the 32X
- [CHAOTIX](../appendices/bibliography.md#chaotix): header; save RAM code at `$03E322`-`$03E4B8`; ROM searched for `$A130F3-$A130FF`
