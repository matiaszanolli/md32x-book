# Sources

Every source cited in the book. Keys are used in brackets in the text, for example `[SH7604 §8.3]`.

These documents are not reproduced in this book. Most are copyrighted and many are marked confidential by Sega. The book explains, summarises and tabulates facts from them in its own words and points here for the original.

## Mega Drive

### MD-TO
*Genesis Technical Overview.* Sega, about 120 pages. Hardware overview: CPU, memory, VDP, Z80, DMA, interrupts.

### MD-SWM
*Genesis Software Manual.* Sega, version 1.0, in use by February 1990 (the cover prints no date; "New 2/6/90" is handwritten on it, and bulletin #13 names the version), 159 pages. Memory map, full VDP reference, I/O, cartridge data format, sound manual with YM2612 and PSG, bulletins #11-#14 (September 1991). See [discrepancy #1](discrepancies.md). The scan is `SegaGenesisSoftwareManual_1990-02-06.pdf` in `../32x-playground/docs`, with an OCR text layer; in the main manual the printed page is the PDF page − 3, and the sound manual bound in after it restarts its own numbering. The converted text copy used for most of this book is wrong in places (registers 0 and 1 lose bits M3, M1 and M2, register 2's alignment is given as `$400`, and the sprite link field sits one bit too far left; the scan has the link field in bits 6-0, p.56). [MD-TO](#md-to) pp.22-26 reproduces the same register pages and is used for register bits.

### MD-SDM
*Genesis Software Development Manual (Complement)*, Ver. 2.0. Sega Enterprises, 9 July 1991. Header format, initial program, external RAM, peripherals, development precautions, PAL notes.

### MD-TB
*Genesis Technical Bulletins.* Sega of America. Errata, workarounds and guidelines.

### MD-REF
Richard Seaborne, *Sega Genesis Reference Sheets*, 5 November 1992. Condensed tables extracted from MD-SWM.

### GENVDP
Charles MacDonald, *Sega Genesis VDP documentation*, version 1.5f, 10 August 2000. Unofficial, and the most detailed VDP reference of its time.

### SND-V3
*68000 Sound Driver Ver. 3.00*, MAR-61-E-040695. Sega Enterprises. Preliminary.

## SH-2

### SH-PM
*SuperH RISC Engine SH-1/SH-2 Programming Manual.* Hitachi America, 3 September 1996. Instruction set, pipeline, opcode map. Text transcription: [32XDK](#32xdk) `docs/sh1-sh2-cpu-core-architecture.md`. Its instruction summary table has three errors: a stray space in the `MOV #imm,Rn` opcode, `MOV.L Rm,@(disp,Rn)` without the × 4 scaling of the displacement, and wrong opcodes for `SWAP.B` and `SWAP.W` (they are `0110nnnnmmmm1000` and `0110nnnnmmmm1001`). Both text copies also repeat three rows of Table 5.3 (`MOV.L Rm,@(R0,Rn)`, `MOV.W Rm,@(R0,Rn)` and `MOV.L Rm,@(disp,Rn)`) after `MOV.L @Rm+,Rn`. The scan's own opcode map (Table A.51 pp.286-287) has three slips: `MOV.B Rm,Rn` and `MOV.B Rm+,Rn` for the loads `MOV.B @Rm,Rn` and `MOV.B @Rm+,Rn`, and R0 for the destination of `MOV.L @(disp,PC),Rn`. Neither text copy has the body of §7 (pipeline) or appendix B, only their headings. The PDF has a text layer, so `pdftotext` reads them; printed page *n* is PDF page *n* + 4.

### SH7604
*SH7604 Hardware Manual*, ADE-602-085C, revision 4.0. Hitachi, 19 September 2001. On-chip peripherals: cache, bus controller, DMAC, divider, timers, interrupt controller, serial port. Text transcription: [32XDK](#32xdk) `docs/sh7604-hardware-manual.md`, identical in content to the copy used for this book apart from its table of contents. Both text copies garble the wait control register's low byte (§7.2.3) as `W31 W30 W21 W11 W10 W01 W00 W00`; the scan (p.140) has `W31 W30 W21 W20 W11 W10 W01 W00`. Both text copies open §3.3 with a summary of the MD4/MD3 pins (the bus width of area 0) that contradicts their own Table 3.9; the table matches the scan (p.62): 00 = 8 bits, 01 = 16 bits, 10 = 32 bits, 11 prohibited. They also leave out Table 3.3 (p.52, the clock mode pins), which is only in the scan. The copy used for this book also stops §13 (serial port) after §13.3.3 and resumes in the usage notes, leaving out clocked synchronous operation and the interrupt sources, and prints φ/64 as φ/164 in Table 13.5 (the scan has the same slip). The PDF has a text layer, and printed page *n* is PDF page *n* + 16.

## 68000

### M68K-PRM
*M68000 Family Programmer's Reference Manual*, M68000PM/AD Rev. 1. Motorola, 1992.

### M68K-UM
*M68000 8-/16-/32-Bit Microprocessors User's Manual*, M68000UM/AD Rev. 8. Motorola, 1993. Section 8 gives the 68000's instruction execution times in clock periods, with the bus reads and writes of each, assuming four-clock memory cycles; the Programmer's Reference has no timing tables. Read from a 216-page scan with a text layer (MD5 `294d120b1b2c16809b23e9f24abbcf7a`), downloaded from [cdn.hackaday.io](https://cdn.hackaday.io/files/1805367724052224/M68000UM_AD_M68000_Microprocessor_Users_Manual_Rev8_1993.pdf) on 5 October 2026; NXP's own copy was not reachable. Section 7 of this edition times the 8-bit MC68008, section 9 the MC68010; cite section 8 for the Mega Drive.

## Z80

### Z80-UM
*Z80 CPU User Manual*, UM008011-0816. Zilog, 2016, [zilog.com/docs/z80/um0080.pdf](https://www.zilog.com/docs/z80/um0080.pdf) (332 pages, MD5 `6e131738b09d5b30b4d7096bc5092ca5`, read 6 October 2026). Pin descriptions pp.6-7; bus request and interrupt request timing pp.11-12. Cited by printed page.

## 32X

### 32X-HWM
*32X Hardware Manual*, MAR-32-R4-072294. Sega of America, 1994. Text transcription: [32XDK](#32xdk) `docs/32x-hardware-manual.md`. Its bitmap mode register table puts PRI at bit 13 and the 240-line bit at bit 7; the scan has them at bits 7 and 6. Both text copies also leave out the DMA paragraph on p.64, which assigns DREQ0 to the FIFO and DREQ1 to PWM and asks for edge-triggered requests.

### 32X-SUP2
*32X Hardware Manual Supplement 2*, MAR-32-R4-SP2-072694. Sega of America, 26 July 1994. SH-2 interrupt limitations.

### 32X-OV
*Genesis Super 32X System Overview and Hardware Reference.* Sega of America, 26 April 1994. The text transcription inverts the list under the priority figure (it puts a through-bit pixel behind the Mega Drive when PRI = 0); the figure in the scan agrees with 32X-HWM and 32X-INTRO.

### 32X-INTRO
*32X Introduction and System Features.* Sega, 26 April 1994.

### 32X-HWI
*32X H/W Information*, MAR-25-R5/R6-060694. Sega of America, 1994. Text transcription: [32XDK](#32xdk) `docs/32x-hardware-information.md`, identical in content to the copy used for this book apart from its table of contents.

### 32X-TI
*32X Technical Information*, MAR-41-R8-090694. Sega of America, 1994.

### 32X-TIA1
*32X Technical Information Attachment 1*, MAR-42-072694. Sega of America, 1994. VRES and RV bit corrective programs. The text transcription gives the Master sample's serial-port delay count as `#4+74`; the scan (p.4) has `#4*74`.

### 32X-TB27
*32X Technical Bulletin #27: SH2 Interrupt Problems on the 32X.* Sega of America, Developer Technical Support, 8 December 1994, 7 pages. A timing diagram of one CMD interrupt handled twice, labelled with FTOA as IRL0, and a revised interrupt handler sample dated 20 September 1994. Read from the scan in [32XDK](#32xdk) `bulletins/` (5 October 2026); the PDF has a text layer.

### 32X-SVC
*Service Manual No. 012: Genesis 32X (VA0, VA1) / Mega Drive 32X.* Sega Enterprises, June 1995, 34 pages. Board schematics (§7-1 to §7-4, printed pp.9-16), block diagram and parts list for the production units. Read from the Internet Archive's copy of [consolemods.org/wiki/images/1/10/Sega_32X_Service_Manual.pdf](https://web.archive.org/web/20241222192028/https://consolemods.org/wiki/images/1/10/Sega_32X_Service_Manual.pdf) (MD5 `6b06e61a3621d5b3df55beb8191b517a`, read 5 October 2026). A scan; its text layer is OCR and garbles labels, so read the schematics from the rendered pages. Citations give the schematic's section number.

## Cartridge hardware

### BD-4M
*IC BD 4M 32 PIN x 8 EPROM 32X R/D User's Manual*, 837-11069, MAR-47-081594. Sega of America, 1994.

### BD-16M
*IC BD 16M 42 PIN x 4 EPROM 32X R/D User's Manual*, 837-11070, MAR-48-081594. Sega of America, 1994.

### BD-32M
*IC BD 32M SRAM + 256K BUP 32X R/D User's Manual*, 837-11068, MAR-46-081594. Sega of America, 1994.

### DS-MB838200B
*MB838200B/BL* mask ROM datasheet, edition 2.0. Fujitsu, April 1993.

### DS-M27C322
*M27C322* 32 Mbit EPROM datasheet. STMicroelectronics, February 2001.

### DS-HM65256B
*HM65256B Series* pseudo-static RAM datasheet (32,768 × 8, needs refresh). Hitachi America.

## Development systems

### SNASM
*SNASM68K Console and Z80 Notes.* Cross Products.

### ACC-SDS
Tim Wilson, *The Sega Development System*, version 2.0. Accolade, 21 February 1991.

### ACC-IRN
Russell Bornsch+ (the name is cut short with a "+" in the original), *Interim release notes for Accolade's Sega Development System*, hardware revision B1, ROM Monitor 3.2, XDB Debugger 4/16/93. Accolade, 19 April 1993. The scan's file name gives 1992; the document itself is dated 1993.

## Emulators and toolchains

### PICODRIVE
*PicoDrive*, the Mega Drive / Mega-CD / 32X emulator by notaz and contributors, [github.com/notaz/picodrive](https://github.com/notaz/picodrive). Read in the copy inside the Virtua Racing Deluxe project (`third_party/picodrive`). Its upstream base is notaz's commit `26ecb2b` (3 April 2025); the project's six commits on top (`b78a88c` to `e0dc88d`, September 2026) add optional RV and SH-2 timing emulation and are cited as VRD-NOTES. Upstream behaviour is read at `26ecb2b` (`git show 26ecb2b:FILE`). Cited for how a widely used emulator models the hardware, never as proof of what the hardware does.

### ARES
*ares*, the multi-system emulator founded by Near and maintained by the ares team, [github.com/ares-emulator/ares](https://github.com/ares-emulator/ares). Version 148 (30 May 2026); its SH-2 and 32X source was read at the state it has had since September 2025 (`ares/md/m32x/`, `ares/component/processor/sh2/sh7604/`). An implementation independent of PicoDrive, useful as a second opinion on what the CPUs and VDP do. Its SH-2 timing is a set of fixed per-region costs, not a model of the bus. Its Mega Drive VDP source (`ares/md/vdp/`) was read at commit `a776c50` (24 September 2026). Its 32X cartridge decoding, `ares/md/cartridge/board/mega-32x.cpp`, and bus code, `ares/md/m32x/bus-external.cpp` and `bus-internal.cpp`, were read at `9408cb4` (5 October 2026), on 7 October 2026. Cited as an emulator, never as proof of what the hardware does.

### MAME
*MAME*, the multi-system emulator by the MAME team, [github.com/mamedev/mame](https://github.com/mamedev/mame). Its 32X device, `src/mame/shared/mega32x.cpp`, was read as last changed at commit `df862b4` (6 July 2026), and its Mega Drive VDP, `src/devices/video/315_5313.cpp`, as last changed at `4873b41` (4 August 2026); both read 5 October 2026. Its SH-2 on-chip modules, `src/devices/cpu/sh/sh7604.cpp`, were read as last changed at `9481bac` (24 September 2026, which reworked the divider's corner cases), read 6 October 2026. Its SH-2 DMA code (`sh7604.cpp`) and memory access (`sh2.cpp`) were read at `1ecdb57` (6 October 2026), and `mega32x.cpp` again at the same commit on 7 October 2026 for RV, FM and the cartridge mapping; `src/mame/sega/mdconsole.cpp` there gives the CRC32 and SHA-1 of the 32X boot ROMs. A third implementation, independent of PicoDrive and Ares. Its Sega X Board driver, `src/mame/sega/segaxbd.cpp`, the board's sprite generator, `src/mame/sega/sega16sp.cpp`, and the Sega PCM chip, `src/devices/sound/segapcm.cpp`, were read at commit `ab1bc04` (6 October 2026), for the hardware of the *After Burner* arcade game. Cited as an emulator, never as proof of what the hardware does.

### GPGX
*Genesis Plus GX*, the Mega Drive / Mega-CD / Master System emulator by Eke-Eke, [github.com/ekeeke/Genesis-Plus-GX](https://github.com/ekeeke/Genesis-Plus-GX). Its VDP renderer and control code, `core/vdp_render.c` and `core/vdp_ctrl.c`, with `core/system.c` and `core/loadrom.c` for the frame loop and the region, `core/hvc.h` for the H counter tables, and `core/input_hw/gamepad.c` and `input.c` for the pads, were read at commit `70ccb3a` (5 October 2026). Its comments sometimes record which console a behaviour was checked on. Cited as an emulator, never as proof of what the hardware does.

### BLASTEM
*BlastEm*, the Mega Drive emulator by Michael Pavone, [retrodev.com/blastem](https://www.retrodev.com/blastem/). Its `vdp.c`, `systems.cfg`, `genesis.c` and `io.c` were read from the upstream Mercurial repository at revision `9b71c8bd2065` (read 5 October 2026). It emulates several console revisions separately, listed in `systems.cfg`. Its 32X support, `32x.c`, was read in a git mirror at commit `1e0de94` (26 September 2026), on 7 October 2026. Cited as an emulator, never as proof of what the hardware does.

### NUKED-OPN2
*Nuked-OPN2*, a YM3438/YM2612 emulator by Alexey Khokholov (nukeykt), [github.com/nukeykt/Nuked-OPN2](https://github.com/nukeykt/Nuked-OPN2). Its README says it was built from a reverse engineering of the YM3438's die shot and runs cycle by cycle; it also models the YM2612. `ym3438.c` was read at commit `335747d` (11 August 2023; its register `$27` decode is unchanged since v1.0, `229d9eb`, September 2017), read 6 October 2026. Genesis Plus GX carries a copy as `core/sound/ym3438.c`. Cited as an emulator, but the closest thing to the chip's own logic this book has.

### EXODUS
*Exodus*, the Mega Drive emulator by Roger Sanders (Nemesis), [github.com/RogerSanders/Exodus](https://github.com/RogerSanders/Exodus). Its VDP, `Devices/315-5313/`, was read at `S315-5313_Timing.cpp` as last changed at `6165472` (20 August 2018) and `S315-5313_General.cpp` and `S315-5313_Ports.cpp` at `b338b03` (14 February 2024); read 6 October 2026. The comments in `S315-5313_Timing.cpp` tabulate the H and V counter sequences and where each status flag and interrupt falls on the line. Several horizontal positions are marked as confirmed with a logic analyser on a console in November 2012; the model and revision are not given. Cited as an emulator, never as proof of what the hardware does.

### MEDNAFEN
*Mednafen*, the multi-system emulator, [mednafen.github.io](https://mednafen.github.io/). Its Saturn module emulates the Saturn's two SH-2s, the same CPU as the 32X's, and its author tests its behaviour on the console. Its SH-2 on-chip modules, `ss/sh7095.inc`, were read in the libretro port *Beetle Saturn*, [github.com/libretro/beetle-saturn-libretro](https://github.com/libretro/beetle-saturn-libretro) (`mednafen/ss/sh7095.inc`, last changed at `ba2ab4d`, 6 September 2026; read 6 October 2026). Cited as an emulator, never as proof of what the hardware does.

### YABAUSE
*Yabause*, a Saturn emulator, [github.com/Yabause/yabause](https://github.com/Yabause/yabause). Its SH-2 on-chip modules are in `yabause/src/sh2core.c` (last changed at `8fb9afe`, 15 June 2016). The same repository holds *YabauseUT* by Theo Berkau (2013), a test program meant to run on a real Saturn and compare it with the emulator; its SH-2 tests, `yabauseut/src/sh2.c` (last changed at `7c5e921`, 27 June 2016), include divider register, operation and overflow-interrupt tests. Both read 6 October 2026. The test's expected values are cited as what its author expects from the console; the results of a run on hardware are not published with it.

### GNU-TOOLS
GNU Binutils 2.46 and GCC 13.2.0 for `sh-elf`, with newlib 3.3.0, and GNU Binutils 2.46 for `m68k-linux-gnu`, as packaged by Ubuntu (`binutils-sh-elf`, `gcc-sh-elf`, `libnewlib-sh-elf-dev`, `binutils-m68k-linux-gnu`). The book's example ROMs are built with them, and the assembler and compiler behaviour the toolchain chapter describes was checked with these versions (5 October 2026).

### VASM
Volker Barthelmann and Frank Wille, *vasm*, a portable assembler, [sun.hasenbraten.de/vasm](http://sun.hasenbraten.de/vasm/). Version 2.0d with the M68k backend 2.8 and the Motorola syntax module 3.19d, as built by the Virtua Racing Deluxe project (`vasmm68k_mot`). The 68000 assembler of all three reference projects. Behaviour described in the book was checked with this build (5 October 2026).

### 32XDK
Chilly Willy's Sega MD/CD/32X devkit, as maintained by viciious, [github.com/viciious/32XDK](https://github.com/viciious/32XDK). The GCC toolchain used by d32xr and most current 32X homebrew. Its `docs/` folder carries text transcriptions of the 32X Hardware Manual, the 32X H/W Information bulletin, the SH-1/SH-2 Programming Manual and the SH7604 Hardware Manual (added 29 August 2026).

### MARSDEV
*marsdev*, an open-source Mega Drive and 32X toolchain, [github.com/andwn/marsdev](https://github.com/andwn/marsdev). Its `32x-skeleton` example is a working minimal 32X cartridge: header, jump table, user header and startup code for all three CPUs.

### SGDK
Stéphane Dallongeville and contributors, *SGDK*, an open-source development kit for the Mega Drive, [github.com/Stephane-D/SGDK](https://github.com/Stephane-D/SGDK) (read at commit `2b7fa81`, 10 February 2025). Cited for how its library code drives the hardware: `src/dma.c` splits any DMA whose source crosses a 128 KB boundary.

### S32X-SKILL
haroldo-ok, *sega-32x-gamedev*, a Claude skill for building and testing 32X games, [github.com/haroldo-ok/sega-32x-skill-for-claude](https://github.com/haroldo-ok/sega-32x-skill-for-claude) (read at commit `67f74a6`, 26 August 2026). Practical notes collected from shipped homebrew built with Chilly Willy's 32XDK and the d32xr Doom port, tested mostly in PicoDrive. A secondary source: good for pitfalls and working patterns, not for hardware facts on its own.

### D32XR
Victor Luchits and contributors, *Doom 32X: Resurrection*, [github.com/viciious/d32xr](https://github.com/viciious/d32xr) (read at commit `957d3a8`, 1 October 2026). A Doom engine for the 32X, based on the Jaguar Doom source release and the Calico port. Threaded rendering on both SH-2s, hand-written SH-2 column and span drawers, a PWM mixer, VGM music on the 68000, RoQ video and save RAM support. Licences are mixed: the original Jaguar Doom code is under id Software's limited-use licence (`license.txt`), and some 32X-specific files, such as `marshw.c` and `sh2_mixer.s`, are MIT. The book describes its techniques in its own words and copies no code.

## Forum reports

Developers' accounts of their own tests, usually without a test ROM or the console's revision. Cited for what was observed and by whom, not as proof of what the hardware does.

### GENDEV-SVDP
*Super VDP*, a thread on the SpritesMind.Net developer forum, [gendev.spritesmind.net/forum/viewtopic.php?t=95](https://gendev.spritesmind.net/forum/viewtopic.php?t=95), 2010-2026 (read 4 October 2026). It holds Chilly Willy's reports of 68000-to-SH-2 FIFO transfers failing on a console (29 and 31 October 2012, 28 and 29 October 2014). It also holds the 2025-2026 posts by Vic, who maintains d32xr, tracing the failure to how the SH-2 cleared TE in CHCR0 (5, 14 and 22 January 2025, 29 August 2026). Citations give the date of the post. The 32XDK wiki's "Bugs and quirks" page, [github.com/viciious/32XDK/wiki/Bugs-and-quirks](https://github.com/viciious/32XDK/wiki/Bugs-and-quirks), quoted the October 2012 post and the GENDEV-DREQ post until 29 August 2026. It then replaced both with a link to this thread's later posts.

### MORITA-FAQ
Toshiyasu Morita, *Programming the 32x FAQ*. Morita was a technical director at Sega of America. The FAQ itself was not found; it is known from the passages quoted on the 32XDK wiki's "Bugs and quirks" page, [github.com/viciious/32XDK/wiki/Bugs-and-quirks](https://github.com/viciious/32XDK/wiki/Bugs-and-quirks) (read 5 October 2026), under "Unified interrupt handler". The same page goes on, without naming an author, to say that the schematics connect FTOA to /IRL0. Undated, and the quotation cannot be checked against the original.

### TERAKAWA-6B
Ein Terakawa, *Interface Protocol of SEGA MegaDrive's 6-Button-Controller*, [applause.elfmimi.jp/md6bpad-e.html](https://web.archive.org/web/20251208171920/https://applause.elfmimi.jp/md6bpad-e.html) (online since at least December 2001, last updated 24 October 2016; read from the Internet Archive, 5 October 2026, as the site no longer answers). The read sequence and its timing, measured on one pad with a PC's timer. Terakawa notes that the timing comes from a capacitor inside the pad and may differ between pads. Mirrored on the MegaDrive++ wiki.

### GENDEV-COLL
*When is the collision bit cleared?*, a thread on the SpritesMind.Net developer forum, [gendev.spritesmind.net/forum/viewtopic.php?t=2440](http://gendev.spritesmind.net/forum/viewtopic.php?t=2440), May 2016 (read 5 October 2026). Mask of Destiny, author of BlastEm, reports a quick console test (12 May 2016): the collision flag is set while sprites are drawn and cleared as soon as the status is read. Eke, author of Genesis Plus GX, reports from his own tests (13 May 2016) that the overflow and collision flags stay set until the status is read, are not cleared by vertical blank, and are set only while the display is on; he did not test whether turning the display off clears them. Neither names the console.

### MDWIKI-PINOUT
*HardWare:VDPpinout*, a page of the community MegaDrive wiki, wiki.megadrive.org, read from the Internet Archive's copy of 29 June 2009 ([web.archive.org/web/20090629172343/http://wiki.megadrive.org/index.php/HardWare:VDPpinout](https://web.archive.org/web/20090629172343/http://wiki.megadrive.org:80/index.php/HardWare:VDPpinout), 5 October 2026). A list of the VDP's pins with a line on each, apparently from probing a console; the page names no author or method. Cited for what the pins are said to carry, not as proof.

### GENDEV-DREQ
*DMA DREQ delay*, a thread on the SpritesMind.Net developer forum, [gendev.spritesmind.net/forum/viewtopic.php?t=3206](https://gendev.spritesmind.net/forum/viewtopic.php?t=3206), February to May 2021. ob1 reports needing a delay of at least 11 NOPs between setting 68S and the first FIFO write, tested in the Fusion 3.64 and Gens KMod 0.7.3 emulators only.

### GENDEV-VDPINT
*VDP Internals*, a thread on the SpritesMind.Net developer forum, [gendev.spritesmind.net/forum/viewtopic.php?t=1291](https://gendev.spritesmind.net/forum/viewtopic.php?t=1291), page 3 (read 5 October 2026). Nemesis, author of the Exodus emulator, posts his VDP port test ROM with its source (11 September 2013) and a long account of how the VDP's command, FIFO and DMA logic works (13 September 2013). He reports that the tests pass on a console, except for VSRAM size tests on the Genesis 3 and three fill tests that write to the data port during a fill and fail intermittently. He does not give the console's model or revision. The test ROM, `VDPFIFOTesting.zip` (MD5 `240129f2c290846217424020c9eebfb0`), is no longer on his site; it was read from the Internet Archive's copy of [nemesis.hacking-cult.org/MegaDrive/Roms/Test/Mine/VDP/VDPFIFOTesting.zip](https://web.archive.org/web/20170421164545/http://nemesis.hacking-cult.org/MegaDrive/Roms/Test/Mine/VDP/VDPFIFOTesting.zip). Citations name the test's source file. Each test's expected result is what Nemesis reports a console producing. This book has not run the tests itself.

### GENDEV-Z80
*Are we sure MD Z80 can't write to M68K RAM? NCS does it...*, a thread on the SpritesMind.Net developer forum, [gendev.spritesmind.net/forum/viewtopic.php?t=985](https://gendev.spritesmind.net/forum/viewtopic.php?t=985), October 2011 (read 6 October 2026). Charles MacDonald reports a console test (17 October 2011, page 2): the Z80's writes to work RAM through the bank window land, but its reads return `$FF`. He does not name the console. Citations give the date of the post.

### GENDEV-YM
*New Documentation: An authoritative reference on the YM2612*, a thread on the SpritesMind.Net developer forum, [gendev.spritesmind.net/forum/viewtopic.php?t=386](https://gendev.spritesmind.net/forum/viewtopic.php?t=386), page 6 (read 6 October 2026). Nemesis reports his tests of channel 3's modes and CSM on the YM2612 (29 June 2008), with a test ROM, its source and a recording made on a PAL MD1600. TmEE reports the test ROM working on a PAL Mega Drive 2, VA1 board (30 June 2008). Citations give the date of the post.

### TESTPICO
notaz (author of PicoDrive), *testpico*, a test ROM for the Mega Drive and the 32X in the repository [github.com/notaz/megadrive](https://github.com/notaz/megadrive) (`testpico/`), read at commit `30a5783` (29 April 2025; read 6 October 2026). Public domain. Each test compares what it reads back with an expected value. The repository never says in words that those values were measured on a console, but everything points to it. The default build is for a console: a separate build for PicoDrive changes one timing routine, and a branch blanks the screen to protect his TV. Tests that hung or gave unexplained results are commented out of the list. And notaz's PicoDrive commit `c9f9453` (7 May 2024) changes the 32X register handlers "according to hw tests", two days after the 32X tests were added. He does not name the console or the 32X revision. For this book it was built with the marsdev toolchain (with its Z80 macros expanded by hand for sjasm 0.39) and run headless in upstream PicoDrive `26ecb2b`. That build passes 55 of the 57 tests, skips the reset-button test, which needs a hand on the console, and fails "32x irq vint". A test PicoDrive fails cannot have taken its expected values from PicoDrive. Citations name the test function. Cited as one developer's console tests, with the console unknown.

## Press and retrospectives

Articles about the games, written for players. Cited for what they say, not as measurements: none says how its figures were obtained.

### HG101-AB
Kurt Kalata, *After Burner*, Hardcore Gaming 101, 17 August 2017, [hardcoregaming101.net/after-burner](https://www.hardcoregaming101.net/after-burner/) (read 6 October 2026). A history of the series and its ports. Says the 32X version runs at 30 frames per second against the arcade original's 60.

### REGISTER-AB
Giles Hill, *After Burner: Sega's jet-fighting, puke-inducing arcade marvel*, The Register, 15 October 2015, [theregister.com](https://www.theregister.com/on-prem/2015/10/15/after-burner-segas-jet-fighting-puke-inducing-arcade-marvel/1395210) (read 6 October 2026). Says the X Board drew up to 256 sprites in each frame, all output at 60 frames per second.

## Retail ROMs

Dumps of shipped cartridges, read by disassembly. They count as evidence of what Sega's own programmers did, not of what the hardware does.

### 32X-ROMSET
A set of 32X cartridge dumps, 39 files, US and world releases plus Sega's development samples and three prototypes, supplied for this book on 6 October 2026 and kept outside the repository. It holds 29 retail cartridges; with Mortal Kombat II and Motocross Championship from the Virtua Racing Deluxe project folder, the book has 31 of the library's 34 cartridges. All but one retail file have a header checksum that matches the contents (BC Racers stores 0, so it cannot be checked). It includes a retail *Virtua Racing Deluxe* (USA), MD5 `72b1ad0f949f68da7d0a6339ecd51a3f`, checksum `$1E4D`, which matches the original that the VRD project's README names. Its *Mars Check Program* (Set 2) is the file this book calls [SOJ](#soj), and its *Pharaoh* is [EGYPT](#egypt). The MD5 of every file, the results of a signature scan and the developer credits found in each cartridge, with offsets, are listed in `notes/games/romset-us.md`. Citations name the game and give cartridge offsets.

### WP-32XLIST
*List of 32X games*, Wikipedia, [en.wikipedia.org/wiki/List_of_32X_games](https://en.wikipedia.org/wiki/List_of_32X_games) (read 6 October 2026). Counts 40 games, six of which also need the Mega-CD, and gives release dates by region. A secondary source, used for the size of the library, for release dates, and for developers where a cartridge has no plain-text credits. Its developer column cites no sources; for Virtua Racing Deluxe and Virtua Fighter it names Sega's AM2 team, which the Wikipedia article on Virtua Racing also states without a source.

### WP-STUDIOS
Wikipedia articles on the 32X developers, read 7 October 2026, used for where each studio was based. A secondary source. Each location in [Sega's sample code in the games](sample-code.md) comes from the article named here: Artech Digital Entertainment (Ottawa, Canada); List of Acclaim Entertainment subsidiaries (Probe Entertainment, later Acclaim Studios London: Croydon, England; Sculptured Software: Salt Lake City, Utah); Iguana Entertainment (Austin, Texas from 1993; Iguana UK in Stockton-on-Tees, England); Visual Concepts (Novato, California); Blizzard Entertainment (Irvine, California); Midway Studios Los Angeles (Paradox Development: Moorpark, California, undated); High Voltage Software (Hoffman Estates, Illinois); BlueSky Software (San Diego, California); Zono (Costa Mesa, California); Core Design (Derby, England); Appaloosa Interactive (Novotrade International: its development companies in Budapest, Hungary); Bits Studios (London, England); Flashpoint Productions (Lacey, Washington, from July 1994); GameTek (Alternative Reality Technologies: GameTek's studios in London and Miami); Givro Corporation (Almanic Corporation: Tokyo); Zombie Studios (Seattle, Washington); Time Warner Interactive (Burbank, California; the studio that made each game is not given); CRI Middleware and its Japanese article (CSK Research Institute: Japan, no city for 1994-95); Red Entertainment, Japanese article (Red Company: Japan, no city for 1995); ゲームのるつぼ, Japanese article on Rutubo Games (founded 1994 in Osaka Prefecture as a development unit working only for Sega Enterprises; the article has carried a "needs sources" tag since 2010); Sonic Team (Tokyo); Sega AM2 (Tokyo); Knuckles' Chaotix, English and Japanese articles (an internal Sega team; the Japanese article says Sonic Team); バーチャレーシング, Japanese article (Virtua Racing Deluxe made by the Mega Drive port's consumer, "CS", team; uncited). Studios with several offices are noted where the article does not say which office made a game.

### STUDIO-PRESS
Other secondary sources on the 32X developers, read 7 October 2026: *The Scott Tsumura story*, Keiko Fukuda, Discover Nikkei, 28 April 2021 (Big Bang Software in Seattle; it dates the company's founding to 1996, later than Pitfall's 32X release in 1995); *Brutal: Above the Claw* review, Matt Frey, Sega-16, 3 July 2006 (developer Alternative Reality Technologies); *Sega of America, Inc.*, International Directory of Company Histories vol. 10, St. James Press, 1995, as reproduced by FundingUniverse (Redwood City, California); ALU's company page, archived 21 April 2001 at web.archive.org (Chiyoda, Tokyo, as of 2001; Cyber Brawl's 32X programming among its works).

### 32X-BIOS
The 32X's three boot ROMs, dumped from a console, kept in the Virtua Racing Deluxe project folder (`../32x-playground/32X BIOS/`). `32X_G_BIOS.BIN`, the 68000 vector ROM: 256 bytes, CRC32 `5c12eae8`, SHA-1 `dbebd76a…`. `32X_M_BIOS.BIN`, the Master SH-2's: 2,048 bytes, CRC32 `dd9c46b8`, SHA-1 `1e5b0b24…`. `32X_S_BIOS.BIN`, the Slave's: 1,024 bytes, CRC32 `bfda1fe5`, SHA-1 `4103668c…`. All three match the checksums MAME lists for the retail boot ROMs, not marked as bad dumps ([MAME](#mame), `src/mame/sega/mdconsole.cpp`). Citations give offsets in the ROM.

### SWA
*Star Wars Arcade* (USA), Sega, 1994, 32X; developed at Sega InterActive, as its credits say (cartridge `$00CCC0`). Dump of 2,621,440 bytes, MD5 `ae3a42c6297ef25c6018a209fda0194e`. The header checksum (`$CF83`) matches the contents. Kept as `Star Wars Arcade (USA).32x` in the Virtua Racing Deluxe project folder. Its SH-2 program, 21,644 bytes, is loaded from cartridge `$000854` to `0x06000000`. Master entry `0x06000400`, Slave entry `0x06000402`, vector tables at `0x06000000` and `0x06000200`. Citations give SH-2 addresses in that program, or ROM offsets written `$`.

### MK2
*Mortal Kombat II* (Japan, USA), Acclaim, programmed by Probe Entertainment, 1994, 32X. Dump of 4,194,304 bytes, MD5 `a95c0e7c1d35fd42cd2e3eb7b06cb6d0`. The header checksum (`$4EB1`) matches the contents. Kept as `Mortal Kombat II (Japan, USA).32x` in the Virtua Racing Deluxe project folder. Its SH-2 program, 32,276 bytes, is loaded from cartridge `$000978` to `0x06000000`. Master entry `0x06000240`, Slave entry `0x06000244`, vector tables at `0x06000000` and `0x06000120`. A third-party game, so it shows what an outside studio did with Sega's samples. Citations give SH-2 addresses in that program, or ROM offsets written `$`.

### MCX
*Motocross Championship* (Japan, USA), Sega, 1994, 32X; developed by Artech Studios for Sega of America, as its credits say (cartridge `$1F06F3`). Dump of 2,097,152 bytes, MD5 `2c4a934985021624d48725b8d7b039e8`. The header checksum (`$BDC5`) matches the contents. Kept as `Motocross Championship (32X) (JU) [!].32x` in the playground folder. Unusual among 32X games: both SH-2s execute in place from the cached cartridge window (the user header's copy block is a four-byte dummy), with Master entry `$02028A00`, Slave entry `$02028800` and both vector tables in ROM. Citations give SH-2 addresses as the SH-2s see them (`0x02xxxxxx` = cartridge offset), or 68000 addresses as the 68000 sees them with the 32X on (`$88xxxx` = cartridge offset `$xxxx`), or ROM offsets written `$`.

### CHAOTIX
*Knuckles' Chaotix* (Japan, USA), Sega, 1994, 32X. Dump of 3,145,728 bytes, MD5 `47b1095e68b053125cd2cd5b1ac4eb50`. The header checksum (`$B61C`) matches the contents. Kept as `Knuckles' Chaotix (32X) (JU) [!].32x` in the playground folder. Its SH-2 program, 36,864 bytes, is loaded from cartridge `$077800` to `0x06000000`; the two entry points are adjacent branch trampolines (Master `$060001A0`, Slave `$060001A4`) with vector tables at `0x06000000` and `0x06000080`. Citations give SH-2 addresses in that program, or ROM offsets written `$`.

## Development discs

Internal Sega "Mars" development discs, dumped from cartridges that were never sold. They show what Sega's own tools and samples did, one level below retail code. All of them carry header checksum zero (the check is skipped) and the module name `MARS CHECK MODE`.

### ECCO
*ECCO the Dolphin CinePak Demo*, "Mars Sample Program", Sega, 1994, 32X development disc. Dump of 3,145,728 bytes, MD5 `c2b642fdcfff8bff511e45203a1e8679`, serial `Version-10`. Kept as `ECCO the Dolphin CinePak Demo (32X) (JU).32x` in the playground folder. Its SH-2 program, 40,960 bytes, is loaded from cartridge `$00C000` to `0x06000000`; Master entry `0x06000120`, Slave entry `0x06008120` (which parks immediately). The movie is a Sega FILM container at cartridge `$20000`: 180 key frames of 256×160 CinePak plus an 8-bit PCM audio track the disc never plays. Citations give SH-2 addresses in that program, or ROM offsets written `$`. The program never writes CCR (`0xFFFFFE92`). This was checked for every form that could produce that address. Among 32-bit literals, the only ones from `0xE0000000` up are `0xFFFF8001`, `0xFFFF841B` and `0xFFFFFFFF`. Among sign-extended 16-bit `mov.w` literals, the only negative one is `0x8124`. One negative 8-bit immediate is followed by a shift (`0xF0`, then `shll8`, at `0x06001798` and its copy at `0x06009798`), and it adjusts the stack. GBR is loaded twice, both times with `0x20004000`, and no GBR access uses offset `0x92`. At run time, PicoDrive started without the boot ROMs played the movie through and round again in 3,000 frames, and a log of every CCR write stayed empty (8 October 2026; with the boot ROMs the demo shows a black screen in PicoDrive).

### RLT
*Runlength Mode Test*, "Mars Sample Program", Sega, 1994, 32X development disc. Dump of 262,144 bytes, MD5 `915472c8d25c79f819492f660e5a8d06`, serial `Version1.0`. Kept as `Mars Sample Program - Runlength Mode Test (32X) (JU).32x` in the playground folder. Its SH-2 program, 227,516 bytes, is loaded from cartridge `$000910` to `0x06000000`; Master entry `0x06000120`, Slave entry `0x06037378`. It drives the 32X VDP's run-length display mode with a scanline polygon renderer of a rotating Sonic model. Citations give SH-2 addresses in that program, or ROM offsets written `$`.

### MARS-CHECK
*Mars Check Program Version 1.0*, Sega, May 1994, 32X development disc. Dump of 4,194,304 bytes, MD5 `489ded0cc43448881cd863418bacf8e6`, serial `ROM Ver.1.00`; the only development disc here whose header checksum (`$8DA0`) matches. Kept as `Mars Check Program V1.0 (32X) (JU).32x` in the playground folder. A hardware diagnostic: menus of register, frame buffer, palette, DMA, display mode and sound tests, run on the 68000 with the SH-2s answering commands through the communication ports. Its SH-2 program, 24,576 bytes, is loaded from cartridge `$00A000` to `0x06000000`; Master entry `0x06000130`, Slave entry `0x06003130`. Citations give 68000 ROM offsets written `$` and SH-2 addresses.

### EGYPT
*Egypt*, "Mars Sample Program", Sega, 32X development disc. Dump of 262,144 bytes, MD5 `4213c4846622dbefb514a0441a553ace`, serial `ROM Version1.0`. Kept as `Mars Sample Program - Egypt (32X) (JU).32x` in the playground folder (the `[b1]` and `[b2]` files beside it are damaged copies). Its SH-2 program, 4,904 bytes, is loaded from cartridge `$02159C` to `0x06000000`; Master entry `0x06000120`, Slave entry `0x06000AE4`. Despite its reputation as a video sample, it holds one raw 320 × 200 picture at `$00219C` and a short loop that copies it from the cartridge to the frame buffer and flips buffers.

### GNU-SIERRA
*Gnu Sierra*, "Mars Sample Program", Sega, 32X development disc. Dump of 655,360 bytes, MD5 `fc5dc432cef5d977a7b9a0575acd884e`, serial `ROM Version1.2`; its ROM-end field says `$01FFFF`, shorter than the file. Kept as `Mars Sample Program - Gnu Sierra (32X) (JU).32x` in the playground folder (the `[b1]` file beside it is a damaged dump). Unlike the other samples, its SH-2 code runs from the cached cartridge window: Master entry `0x0200C81A`, Slave entry `0x0200C800`, vector tables in the cartridge at `$00C000` and `$00C400`. The user header still copies 262,144 bytes of data from cartridge `$080000` to `0x06000000`, the whole of SDRAM. Citations give SH-2 addresses, or ROM offsets written `$`.

### SOJ
*SOJ*, "Mars Sample Program", Sega, 32X development disc. Dump of 65,536 bytes, MD5 `68e63e08aa1b95d4b5b249ef6de7b1b3`, serial `ROM Ver.1.00`. Its header gives the title `MARS CHECK PROGRAM VERSION 1.0`, like [MARS-CHECK](#mars-check), but the contents are a different program, and its ROM-end field says `$3FFFFF`, far beyond the file. Kept as `Mars Sample Program - SOJ (32X) (JU).32x` in the playground folder (the `[b1]` file beside it is a damaged dump). Its SH-2 program, 16,384 bytes, is loaded from cartridge `$00C000` to `0x06000000`; Master entry `0x06000120`, Slave entry `0x06002120`. Only its header, jump table and initial program have been read so far. Citations give ROM offsets written `$`.

### TEXTURE
*Texture Test*, "Mars Sample Program", Sega, 32X development disc. Dump of 24,576 bytes, MD5 `bd0b324d1edd51103a350e1973179fb7`, serial `ROM Version1.0`; its ROM-end field says `$01FFFF`, beyond the file. Kept as `Mars Sample Program - Texture Test (32X) (JU).32x` in the playground folder (the `[b1]` file beside it is a damaged dump). Its SH-2 program, 15,136 bytes, is loaded from cartridge `$000910` to `0x06000000`; Master entry `0x06000120`, Slave entry `0x060038DC`. Only its header, jump table and initial program have been read so far. Citations give ROM offsets written `$`.

## Reference projects

Original research by the author: full disassemblies of commercial games that rebuild byte for byte, then changed to make better use of the 32X. Claims taken from them have been measured in emulators unless tagged otherwise.

### AB32X
*After Burner Complete* (Japan, USA), Sega, 1994, 32X; reprogrammed by Rutubo Games, as its credits say (cartridge `$01C25C`). Dump of 2,097,152 bytes, MD5 `ec9529858cc7961b39f5382b2f657b8f`. The header checksum (`$4174`) matches the contents. Kept as `After Burner Complete ~ After Burner (Japan, USA).32x` in the Virtua Racing Deluxe project folder. Its SH-2 program, 106,496 bytes, is loaded from cartridge `$053000` to `0x06000000`. Master entry `0x06002120`, Slave entry `0x06000200`, vector tables at `0x06002000` and `0x06000000`. Citations give SH-2 addresses in that program, or 68000 addresses as the 68000 sees them with the 32X on (`$88xxxx` = cartridge offset `$xxxx`) or ROM offsets written `$`.

### VRD-NOTES
*Virtua Racing Deluxe* (32X) disassembly and 60 fps project, [github.com/matiaszanolli/sega-vr-disasm](https://github.com/matiaszanolli/sega-vr-disasm). Notes and tools: setup, profiling, FIFO capture, annotation framework, ROM size analysis, 68000 and SH-2 communication. **Its ROM copy is not the retail original.** The project's file has MD5 `85eda196…` where the original is `72b1ad0f…`, its header checksum does not match, and its SH-2 program contains code injected by the project's own tools: the start of the Master's interrupt handler at `0x060006A4` is overwritten with the handshake words `REDY`, `WORK`, `DONE` written by `tools/inject_master_sync.py`. The first 2 KB (headers, Sega's initial program) and the 32X BIOS dumps are unaffected. Claims about the game's own code past that point are taken from the project's documents, or confirmed against [SWA](#swa). The book reads the `master` branch (March 2026) for the disassembly and the project's account of the original game, and the active branch's status files (`README`, `KNOWN_ISSUES`, `VR60_STATUS`) for which of its results still stand. `master`'s disassembly was matched to the same patched file: its source carries the injected words at cartridge `$0206A4`. Compared with the retail copy in [32X-ROMSET](#32x-romset), the project's file differs only in 103 bytes at `$020650`-`$0206BD`; the source on `master` has since changed further, for example the Slave's code from `$020608` (commit `d8b770c`).

### AB-DISASM
*Aerobiz Supersonic* (Mega Drive, Koei 1994) disassembly, [github.com/matiaszanolli/aerobiz-disasm](https://github.com/matiaszanolli/aerobiz-disasm). A complete disassembly that rebuilds the original 1 MB ROM byte for byte. It is the base Aerobiz Ultimate is forked from, and a fully annotated example of a commercial Mega Drive game: header, Sega's initial program, VDP, DMA, Z80 sound and save RAM.

### AU-NOTES
*Aerobiz Ultimate*, a 32X remaster of *Aerobiz Supersonic* (Mega Drive) in progress, [github.com/matiaszanolli/aerobiz-ultimate](https://github.com/matiaszanolli/aerobiz-ultimate). Port architecture and memory map, one source tree that builds both the original Mega Drive ROM and the 32X cartridge, moving game logic to the SH-2s, the 32X bitmap layer behind Mega Drive planes, PWM audio, and a list of questions only real hardware can answer.
