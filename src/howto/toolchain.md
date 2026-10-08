# Setting up a toolchain

A 32X program is two programs in one cartridge: one for the 68000, one for the SH-2s. Building it takes a compiler or assembler for each CPU, a way to put both into a single image, and a final step that fills in the cartridge header. This chapter covers what to install, the flags that matter, how the two halves are joined, and the traps found along the way. Running the result is covered in [Automated testing in an emulator](emulator-testing.md).

Where this page says something was checked, it was checked for this book with GNU Binutils 2.46, GCC 13.2.0 [GNU-TOOLS] and vasm 2.0d [VASM], as listed in the bibliography. Other versions may differ.

## What to install

| Job | Tool | Where it comes from |
|-----|------|---------------------|
| SH-2 assembler and linker | GNU Binutils for `sh-elf` | Linux distribution packages, or a devkit below |
| SH-2 C compiler | GCC for `sh-elf`, with newlib | Same |
| 68000 assembler | vasm with Motorola syntax (`vasmm68k_mot`), or GNU Binutils for m68k | vasm is built from source; Binutils from packages |
| 68000 C compiler (optional) | GCC for `m68k-elf` | A devkit below |
| Emulators | PicoDrive (libretro core), ares | See [Two emulators, two jobs](emulator-testing.md#two-emulators-two-jobs) |

There are three common ways to get the compilers:

- **Distribution packages.** On Ubuntu, `gcc-sh-elf`, `binutils-sh-elf` and `libnewlib-sh-elf-dev` give a complete SH-2 C toolchain, and `binutils-m68k-linux-gnu` gives a 68000 assembler and linker [GNU-TOOLS]. The m68k package targets Linux, but for plain assembly linked to a raw binary that does not matter: the [hello world ROM](32x-hello.md) is built with it. For 68000 C, use an `m68k-elf` compiler from a devkit. Packages are the easiest route and the least predictable one, because the version changes with the distribution [S32X-SKILL, toolchain notes].
- **Chilly Willy's 32XDK.** A prebuilt archive with `sh-elf` and `m68k-elf` GCC 12.1, unpacked under `/opt/toolchains/sega`, with linker scripts for both sides. Most current 32X homebrew uses it [32XDK; S32X-SKILL, toolchain notes]. d32xr's build pins release `20220418`, and its CI caches the unpacked toolchain so that it is downloaded only once [D32XR, `.github/workflows/build.yml`].
- **marsdev.** Makefiles that build the GCC toolchains from source, with a choice of GCC version, plus optional extras such as SGDK, a C library for Mega Drive games [MARSDEV]. Its build here produced GCC 15.1.0 for the 68000.

All three reference projects assemble their 68000 code with vasm, and the two 32X projects use GNU tools for the SH-2. The VRD project's Makefile downloads and builds vasm itself (`make tools`) [VRD-NOTES, SETUP; AB-DISASM; AU-NOTES].

Two habits save time. Keep a `setup.sh` that installs everything and does nothing if it is already there, so a fresh machine or a reset sandbox is one command from building. And write output to plainly named directories: some sandboxed workspaces throw away directories called `build/` or `dist/` between sessions, which makes a finished ROM vanish [S32X-SKILL, toolchain notes].

## The flags that matter

### SH-2

| Flag | What it does | What happens without it |
|------|--------------|-------------------------|
| `-m2` (GCC) | Compile for the SH-2 | GCC compiles for the SH-1, which has no 32-bit multiply: `a * b` becomes a call to a library routine instead of one `mul.l` (checked) |
| `-mb` (GCC) | Big-endian code and data | The Ubuntu build is big-endian by default (checked), but `-ml` exists and another build may default to it. Say it explicitly |
| `--isa=sh2` (assembler) | Accept only SH-2 instructions | `sh-elf-as` accepts SH-3 instructions such as `shad` without a word, and the SH-2 cannot run them (checked) |
| `-ffreestanding`, `-nostdlib` | No hosted C library or start-up files | The link pulls in start-up code meant for another system |
| libgcc | Division and other helpers the compiler calls | Undefined symbols such as `__udivsi3`. Link the `-m2` copy: `sh-elf-gcc -m2 -mb -print-libgcc-file-name` names it [AU-NOTES, Makefile] |

`-mtas` deserves a warning of its own. Without it, GCC compiles `__atomic_test_and_set` to a plain read followed by a plain write, which is no lock at all between two CPUs, and says nothing. With it, GCC uses `tas.b`, which works in emulators and in d32xr but which Sega's manual forbids on the 32X <span class="tag disputed">disputed</span> ([discrepancy 12](../appendices/discrepancies.md); checked with GCC 13.2). d32xr builds with `-mtas` [D32XR, Makefile]. Either way, don't take a C11 atomic as a lock without reading the code it produced. See [Communication](../32x/communication.md) for locks that need no special instruction.

Optimisation levels: d32xr builds the game at `-Os` with link-time optimisation, but its hardware layer at `-O1` without it, so that its timing stays predictable [D32XR, Makefile]. The 32XDK's GCC 12.1 has its own traps, listed [below](#compiler-traps).

### 68000

- **`-m68000`** for both GCC and the assembler, so nothing from later 680x0 models slips in.
- **`--register-prefix-optional`** for GNU `as`, or it reads `d0` as a symbol (below).
- **Check `-mshort` before linking anything.** marsdev's example compiles the 68000 side with it, which makes `int` 16 bits wide [MARSDEV, `examples/32x-skeleton`]. That suits the 68000's 16-bit bus, but every object file and library in the link must be built the same way.

## Assembler syntax

Most published 68000 source uses Motorola syntax, which vasm reads directly. GNU `as` reads a different dialect, and some of the differences fail silently. All of the rows below were checked:

| | vasm (Motorola syntax) | GNU `as` for m68k |
|---|---|---|
| Comment | `;` | `\|`, or `#` at the start of a line. `;` separates two statements, so `move.w d0,d1 ; copy` fails with "Unknown operator" |
| Hex | `$C00004` | `0xC00004`. `$10` is read as a symbol named `$10`; the error only appears at link time |
| Registers | `d0`, `a7` | `%d0`, unless `--register-prefix-optional` is given. Without it, `d0` is a symbol: `move.w d0,d1` assembles as a memory-to-memory move and fails only at link time |
| Constant | `NAME equ $10` | `.equ NAME, 0x10` |
| Local label | `.loop`, private to the last global label | `1:`, referred to as `1b` (back) or `1f` (forward) |
| Data | `dc.b`, `dc.w`, `dc.l` | `.byte`, `.word`, `.long` |

On the SH-2 side there is only one assembler in common use, GNU `as`, which uses `!` for comments.

### The assembler may choose the encoding

An assembler is free to pick a shorter encoding for what you wrote. vasm does this by default: `move.l #1,d0` becomes `moveq`, a branch to a nearby label becomes a short branch, and an address that fits in 16 bits uses the short form. `-no-opt` turns that off. GNU `as` also made `moveq` out of `move.l #1,d0`, but kept the long form of a forward branch (checked).

For new code this doesn't matter. It matters a great deal when rebuilding someone else's ROM byte for byte, as a disassembly project must. The Aerobiz disassembly lists the traps it met with vasm, all because two encodings mean the same thing [AB-DISASM, KNOWN_ISSUES]:

- **Unused bits.** Byte-immediate instructions carry the value in a word whose top byte is ignored, and the 68000's indexed addressing has three unused bits. The original compiler left junk in them; vasm writes zeros. These instructions have to stay as `dc.w` data.
- **Short absolute addresses.** Under `-no-opt`, a bare address assembles in the long form unless it is written with `.w`.
- **`bsr` against `jsr (pc)`.** They are different opcodes that do the same thing; write the one the original used.
- **A short forward `bra`.** vasm refuses `bra.b` to a forward label under `-no-opt`, whatever the distance [AU-NOTES, KNOWN_ISSUES].

### SNASM

Cross Products' SNASM was one of the development systems of the time: a PC assembler and debugger connected over SCSI to a box that plugs into the console's 68000 socket. The box holds 1 MB of RAM that stands in for the cartridge, and gives the program a few debugger services through calls into its own ROM [SNASM]. The SNASM68K manual itself is not among this book's sources. Its notes on the Z80 assembler show the flavour of the differences: local labels start with `@`, and hex can be written with a trailing `H` [SNASM]. Source written for SNASM therefore needs its local labels, number formats and directives checked before vasm or GNU `as` will take it.

## Putting both CPUs in one ROM

The cartridge must hold the 68000 vectors, the header, the jump table, the user header and Sega's initial program at fixed offsets ([The cartridge layout](32x-hello.md#the-cartridge-layout)), and somewhere after those, the code for both CPUs. There are two ways to arrange the SH-2 side.

### The SH-2 program copied to SDRAM

This is what the user header was designed for: the Master's boot ROM copies one block from the cartridge to SDRAM, and both SH-2s start there ([The user header](../32x/boot.md#the-user-header)). Every retail game this book has read does this except one, and so do most of Sega's sample programs:

| Cartridge | SH-2 program | Copied to | Master entry |
|-----------|--------------|-----------|--------------|
| Star Wars Arcade | 21,644 bytes from `$000854` | `0x06000000` | `0x06000400` |
| Mortal Kombat II | 32,276 bytes from `$000978` | `0x06000000` | `0x06000240` |
| After Burner | 106,496 bytes from `$053000` | `0x06000000` | `0x06002120` |
| Knuckles' Chaotix | 36,864 bytes from `$077800` | `0x06000000` | `0x060001A0` |
| Runlength Mode Test (Sega sample) | 227,516 bytes from `$000910` | `0x06000000` | `0x06000120` |

Sources: [SWA; MK2; AB32X; CHAOTIX; RLT], read from each user header.

The build is then two links. The SH-2 program is linked to run at `0x06000000` and turned into a raw binary. The 68000 side, which also lays out the whole cartridge, includes that binary at a fixed offset and points the user header at it. The [hello world ROM](32x-hello.md#building) does this in a dozen lines of shell.

The awkward part is passing facts from one link to the other: the 68000 side needs the size of the SH-2 image and perhaps the address of the Slave's entry point. Aerobiz Ultimate generates them. After linking the SH-2 side with GNU tools, its Makefile pads the binary to a multiple of four bytes, reads the Slave's entry address from the symbol table with `sh-elf-nm`, and writes both into a small include file that the vasm source assembles against [AU-NOTES, Makefile]. Nothing is copied by hand, so the two sides cannot disagree.

### Code that runs from the cartridge

The other way leaves the code in the cartridge and runs it through the SH-2's cached cartridge window at `0x02000000`. The 32XDK, marsdev and d32xr all work like this. The whole cartridge is one SH-2 link: `.text` is placed at `0x02000000` with load address 0, so the start-up file can lay out the 68000 vectors, header and jump table as data at the start of it. The 68000 program, built separately, is included as a binary. The user header copies only `.data` into SDRAM, and `.data` holds the SH-2 vector tables and entry points [MARSDEV, `examples/32x-skeleton`; D32XR, `crt0.s`, `mars-ssf.ld`].

Sega did this too. Motocross Championship runs both SH-2s from the cartridge, with a dummy four-byte copy in its user header [MCX]. Sega's Gnu Sierra sample keeps its code and vector tables in the cartridge and uses the copy only to fill SDRAM with 256 KB of data [GNU-SIERRA].

The trade-off is speed against space:

- **A cache miss costs far more.** A 16-byte line from the cartridge costs 64 to 136 clocks, against 12 from SDRAM ([Access timing](../32x/timing.md#the-sh-2)). Code that fits in the cache hardly notices; code that doesn't runs much slower.
- **The SH-2 stops while RV = 1.** When the 68000 sets RV to DMA from the cartridge, an SH-2 reading the cartridge waits until RV clears ([The RV bit](../32x/architecture.md#the-rv-bit)). An SH-2 running from the cartridge then waits too, unless its loop is already in the cache.
- **SDRAM is only 256 KB.** Running from the cartridge leaves all of it for data and buffers.

d32xr takes the middle way. A function attribute puts the hot routines, such as the column and span drawers and the sound mixer, in a section that the linker script places inside `.data`, so the boot copy carries them to SDRAM and they run from there [D32XR, `doomdef.h`, `marshw.h`, `mars-ssf.ld`]. See [Cache discipline](../patterns/cache.md) and [Where things should live](../32x/timing.md#where-things-should-live).

### Traps in the link

- **`objcopy -O binary` writes everything from the lowest loaded address to the highest.** One empty section placed at a low address was enough to give the hello world build a 973 MB file. Name the sections you want with `-j` ([Building](32x-hello.md#building)).
- **The copy size must be a multiple of four**, because the boot ROM copies longwords [32X-HWM §5.1]. Pad the binary.
- **Name every section in the linker script.** A section declared as plain `.section .sdata` has no flags, so it is not marked as part of the loaded image. If the linker script collects `.sdata` into `.data`, as d32xr's does, it is loaded anyway. If the script doesn't mention it, it lands nowhere: its bytes are missing from the binary, with no error (checked). One port lost its vector tables this way and booted to a black screen. Declaring the section `"aw",@progbits` is the fix the port used [S32X-SKILL, toolchain notes].
- **`--gc-sections` can remove the whole game.** It throws away code nothing refers to. If the linker cannot see a path from its starting symbols to the game's entry points, it keeps the header and drops the rest, and the ROM boots to black [S32X-SKILL, toolchain notes].
- **Check the image, not the ELF file.** A build check should look for the reset vectors at their offset in the final ROM, and for a few strings from different source files, because a correct ELF file can still produce a wrong image [S32X-SKILL, toolchain notes].

### The header

The last step fills in the cartridge header: the end address at `$1A4`, and the checksum at `$18E`, or 0 to make the initial program and the boot ROM skip the check ([The checksum](../32x/boot.md#the-checksum)). d32xr builds a small C program for this as part of its build [D32XR, Makefile]. The Sega sample programs read for this book all carry 0 [ECCO; RLT; GNU-SIERRA].

## Compiler traps

The GCC 12.1 in the 32XDK miscompiles some valid C for the SH-2. A physics game ported to the 32X met four cases, each of which looked like a logic bug at first <span class="tag emulator">emulator</span> [S32X-SKILL, toolchain notes]:

- **Returning a 12-byte structure by value** could come back corrupted. Pass a pointer to the result instead.
- **Chains of 64-bit multiplies** could go wrong. Use the SH-2's own 32 × 32 → 64-bit multiply through a small inline assembly macro ([Fixed point](../techniques/fixed-point.md)).
- **A store the optimiser wrongly thought dead** was dropped. Make the target `volatile`, or write through a pointer the compiler cannot see through.
- **Calls between files built at different optimisation levels** broke. Build everything at one level, and if a routine is only wrong at `-O3` or with link-time optimisation, drop that routine to `-O2` before suspecting your own code.

These were not checked against GCC 13 or later.

## A known-good start

When a fresh project will not boot, start from something that does. One port's new project produced different SH-2 vectors from identical sources; copying a working project and moving code over one file at a time found the problem faster than debugging the new one [S32X-SKILL, testing notes]. The [hello world ROM](32x-hello.md) is the smallest starting point in this book; marsdev's `32x-skeleton` is a larger one, with C on both CPUs [MARSDEV].

## What to take away

- Install `sh-elf` GCC and Binutils, and either vasm or GNU Binutils for the 68000. Packages, the 32XDK and marsdev all work; pin the version.
- Always pass `-m2 -mb` to GCC and `--isa=sh2` to the assembler.
- Write Motorola-syntax 68000 source for vasm, or give GNU `as` `--register-prefix-optional` and remember that `;` and `$` mean something else there.
- Choose between copying the SH-2 program to SDRAM and running it from the cartridge, knowing what each costs.
- Generate everything one link needs from the other, and check the final ROM image, not the ELF file.

## Open questions

- Which compiler built Sega's sample programs and the retail games? The code may carry the signature of Hitachi's SH C compiler.
- Do the GCC 12.1 miscompiles still happen with GCC 13 and later?
- How much does running from the cartridge cost a real game compared with running from SDRAM, measured on a console?

## Sources

- [GNU-TOOLS](../appendices/bibliography.md#gnu-tools): Binutils 2.46, GCC 13.2.0 (behaviour checked for this book)
- [VASM](../appendices/bibliography.md#vasm): version 2.0d, Motorola syntax module 3.19d (behaviour checked for this book)
- [32XDK](../appendices/bibliography.md#32xdk): release 20220418
- [MARSDEV](../appendices/bibliography.md#marsdev): README; `examples/32x-skeleton` (Makefile, `mars.ld`, `mars_start.s`, `md.ld`)
- [D32XR](../appendices/bibliography.md#d32xr): Makefile, `crt0.s`, `mars-ssf.ld`, `doomdef.h`, `marshw.h`, `.github/workflows/build.yml`
- [S32X-SKILL](../appendices/bibliography.md#s32x-skill): toolchain notes; testing notes
- [SNASM](../appendices/bibliography.md#snasm): console notes; Z80 notes
- [AB-DISASM](../appendices/bibliography.md#ab-disasm): KNOWN_ISSUES (vasm encodings)
- [AU-NOTES](../appendices/bibliography.md#au-notes): Makefile; KNOWN_ISSUES
- [VRD-NOTES](../appendices/bibliography.md#vrd-notes): SETUP
- [32X-HWM](../appendices/bibliography.md#32x-hwm): §5.1
- [SWA](../appendices/bibliography.md#swa), [MK2](../appendices/bibliography.md#mk2), [AB32X](../appendices/bibliography.md#ab32x), [CHAOTIX](../appendices/bibliography.md#chaotix), [MCX](../appendices/bibliography.md#mcx), [RLT](../appendices/bibliography.md#rlt), [ECCO](../appendices/bibliography.md#ecco), [GNU-SIERRA](../appendices/bibliography.md#gnu-sierra): user headers
