# Historical development systems

Mega Drive and 32X games were not written on the console. They were assembled on a PC, sent down a cable into a board that stood in for the cartridge, and debugged through a monitor program running beside the game. This appendix describes the systems the book's sources document. Their habits survive in shipped code and in Sega's warnings, and a few of their limits explain rules elsewhere in the book.

## The systems at a glance

| System | Maker, date | Connects through | Stands in for the cartridge with | Source |
|--------|-------------|------------------|----------------------------------|--------|
| Sega Development System | Accolade, version 2.0, February 1991 | A card in the cartridge slot; PC parallel port to the console's rear port | A RAM card | [ACC-SDS] |
| Sega Development System, hardware revision B1 | Accolade, April 1993 | A board in the cartridge slot; two parallel ports | 16-32 Mbit of battery-backed RAM | [ACC-IRN] |
| SNASM68K | Cross Products | A pod in the console's 68000 socket; SCSI to the PC | 1 MB of static RAM | [SNASM] |
| Development cartridge boards | Sega of America, 1994 | The cartridge slot | EPROMs, or battery-backed SRAM | [BD-4M; BD-16M; BD-32M] |
| 32X development targets | Sega, versions 1.x to 3.0 | — | — | [32X-HWI; 32X-TI] |

## Accolade's Sega Development System

### Version 2.0 (1991)

Accolade's system was a RAM card in the cartridge slot, a cable from a PC's parallel port to the console's rear port, and a PC program, HOST, that loaded code, data and graphics, set breakpoints and traced [ACC-SDS, setting up]:

- **Files.** Code and data were plain binary images; symbols came from the 2500 A.D. assembler's output format.
- **A resident monitor.** The monitor sat in the top 2 KB or so of the RAM card. It patched itself into three of the program's vectors when the program was loaded: the vertical interrupt (level 6, at `$78`), TRACE and TRAP `$F`. It kept the program's own handlers and called them while it was inactive.
- **Rules for the program.** The monitor talked to the PC from the vertical interrupt. So for the debugger to work, the program had to keep the vertical interrupt enabled (register 1 bit 5) and the interrupt mask at 5 or lower. A program that wanted to ignore vertical interrupts was told to use its own flag instead of masking them. The video commands assumed an auto-increment of 2 (register 15 = `$02`). And the program must not touch the rear port, which carried the debugger's cable.
- **A program could still break it.** Nothing stopped a program from overwriting the vector table while running, which cut the monitor off.

The manual's view of the hardware is that of someone working it out without Sega's documents [ACC-SDS, a view of the SEGA Genesis system; address/register list]:

- It lists `$A10001`, the version register, and `$A14000`, the TMSS lock, as unknown addresses "used in some software" ([The version register](../megadrive/io.md#the-version-register)).
- It has no specifications for the YM2612.
- It gives the 68000's clock as 8 MHz.
- It assumes a 512 KB cartridge, and warns that C may be hard to use for lack of space.

### Hardware revision B1 (1993)

The 1993 board, with an unfinished monitor and a new debugger, XDB, added [ACC-IRN]:

- **More memory.** 16 Mbit of cartridge RAM as standard, with 22, 28 and 32 Mbit options (up to 4 MB). A further 192 KB of expansion RAM could act as extra cartridge ROM or emulate an 8- or 16-bit save EEPROM.
- **Its own RAM.** 64 KB of system RAM for the monitor, which on the older board had taken part of the cartridge RAM.
- **Faster loading.** Two parallel ports, the main one clocked at over 50 KB per second: an 8 Mbit game in under 30 seconds.
- **Battery backup** for the cartridge RAM, and a PC/Cart switch. In Cart mode the program runs as if from a real cartridge, with no monitor at all.
- **A MIDI interface**, so musicians could play the console's sound chips as a synthesiser.

Its known problems repeat the 1991 rule: the monitor still communicates in vertical blank, so a program that turns the vertical interrupt off loses contact with the debugger until an exception, a breakpoint or the interrupt brings it back [ACC-IRN, known problems].

## SNASM68K

Cross Products' system put a small interface pod in the console's 68000 socket, connected to a main unit, which talked to the PC over SCSI [SNASM, installation]:

- **Memory.** 1 MB of static RAM stood in for the cartridge, placed on any 1 MB boundary by DIP switches, normally at 0. Another 32 KB, battery-backed, was the interface's own workspace at `$200000`, with its top 1 KB used by the link software. The main RAM was write-protected while the program ran and writable while the interface's ROM had control.
- **Start-up code.** A file supplied with the system, `startup.68k`, was assembled in front of the program. It pointed the 68000's vectors either at the program's own handlers or at error handlers in the interface's ROM, depending on a setting called KeepTraps. For the final ROM the setting was turned off and the program assembled to a plain binary.
- **Services.** The program could call the interface by jumping to its workspace address plus 16, with a service number in `d0`. Service 0 routed more exception vectors into the debugger, for example the TRAP instructions. Service 1 set masks applied to the status register on entry to the debugger, by default turning interrupts off.
- **Safe memory.** A configuration file listed which addresses the debugger could read and write without side effects, which on a console with registers that react to reads matters.

Cross Products also supplied a Z80 assembler, with syntax close to its 68000 one but its own conventions: local labels starting with `@`, hex with a trailing `H`, several registers in one `PUSH`. [Toolchain setup](../howto/toolchain.md#snasm) covers moving SNASM source to today's assemblers.

## Sega's boards and targets

- **Development cartridge boards.** For the 32X, Sega supplied EPROM boards for 4 and 16 Mbit parts and a battery-backed SRAM board, all with its bank chip, and two memory modes ([Sega's development boards](../megadrive/cartridge.md#segas-development-boards)) [BD-4M; BD-16M; BD-32M]. The Mega Drive has a register for them: the memory mode bit at `$A11000` turns on refresh for development cartridges built from dynamic RAM ([Cartridge hardware](../megadrive/cartridge.md)).
- **32X development targets.** Successive versions of the 32X hardware went to developers before the console shipped, each with its own limits: 4 Mbit of SDRAM instead of the console's 2, a PWM bug in an early interface chip, FIFO transfers limited to under 256 words, quieter PWM. The full list is in [Development hardware only](../32x/bugs.md#development-hardware-only).
- **Not like a console.** Development systems could behave unlike production hardware. Sega's Mega Drive Super Target acknowledged accesses to unmapped addresses that would hang a production console, and Sega's advice was to remove the chip that did it [MD-TB #15].

## What survives in shipped code

- **Error vectors aimed at a debugger.** Mortal Kombat II's SH-2 error vectors point into cartridge ROM at `$3FB000`, which is erased in the retail cartridge. They were presumably aimed at a debugger's handlers on development hardware ([The user header](../32x/boot.md#the-user-header)).
- **Sega's sample header.** The 32X user header's name field, `MARS CHECK MODE`, comes from Sega's sample and appears in shipped games ([The user header](../32x/boot.md#the-user-header)).
- **Settings to remove before release.** Sega warned that developers had set the SH-2 up for the development target's 4 Mbit of SDRAM, and that the setting had to come out for production consoles [32X-HWI (2) item 3].

## Today

Emulators with headless control, save states and scripted input, and flash cartridges, have replaced these systems. See [Testing in emulators](../howto/emulator-testing.md) and [Testing on real hardware](../howto/real-hardware.md). One habit carries over from the 1991 manual: a debugging tool that runs inside the program, as Accolade's monitor did, depends on the program not disabling what the tool needs.

## Sources

- [ACC-SDS](../appendices/bibliography.md#acc-sds): setting up; operational notes; a view of the SEGA Genesis system; address/register list
- [ACC-IRN](../appendices/bibliography.md#acc-irn): new hardware features; known problems
- [SNASM](../appendices/bibliography.md#snasm): installation; services; configuration file; DIP switches; Z80 notes
- [BD-4M](../appendices/bibliography.md#bd-4m), [BD-16M](../appendices/bibliography.md#bd-16m), [BD-32M](../appendices/bibliography.md#bd-32m)
- [32X-HWI](../appendices/bibliography.md#32x-hwi), [32X-TI](../appendices/bibliography.md#32x-ti), [MD-TB](../appendices/bibliography.md#md-tb) #15
