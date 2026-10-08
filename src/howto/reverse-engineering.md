# Disassembling and annotating a commercial game

A cartridge dump is a few megabytes of bytes with no labels, no comments and no separation between code and data. This chapter gives a method for turning one into source you can read, rebuild and change, using the tools and lessons of the book's reference projects. It also follows one test in Sega's Mars Check Program, a 32X development disc, all the way from a message string to the code on both CPUs.

Everything here concerns reading programs. What a program shows about the hardware is evidence of what its authors expected, so this book cites it by the ROM's key and treats a single program as one witness.

## First, is this the ROM you think it is?

Check the file before reading a byte of it:

- **Compare its MD5 with a known-good dump.** The Virtua Racing Deluxe project produced a byte-identical disassembly of its ROM, and only later found that the file was not the retail original: earlier patches from the project's own tools were in it. The rebuild matched the file it started from, which proved nothing about the original [VRD-NOTES]. The bibliography lists the MD5 of every ROM the book cites.
- **Check the header checksum, and know how little a match proves.** A retail cartridge's checksum at `$18E` matches its contents, so a mismatch means a damaged file or one changed without fixing the field: the patched Virtua Racing Deluxe copy keeps the retail `$1E4D` but its contents sum to `$4518`. A match proves less. Whoever patches a ROM can recompute the field, so only the MD5 comparison shows that the file is the original. Development discs often carry 0, which tells the initial program to skip the check ([The checksum](../32x/boot.md#the-checksum)).
- **Check the size against the header.** The end address at `$1A4` should match the file. Several circulating dumps of Sega's sample programs are shorter than their headers say, and the files marked `[b1]` or `[b2]` are damaged copies of others [GNU-SIERRA].
- **Don't trust a dump's reputation.** Sega's Egypt sample is often described as a video demo. Its program turned out to be a loop of about 30 instructions that shows a single still picture [EGYPT]. The real video demo among the discs is the Ecco one [ECCO].

The book's `notes/games/tools/header32x.py` prints all of this for any number of cartridges in one run.

## Where everything is

A 32X cartridge has a fixed layout up to `$800`, and the user header says where the SH-2 program is:

| Offset | What | What to do with it |
|--------|------|--------------------|
| `$000` | 68000 vectors | Only the reset vector matters: it points at Sega's initial program (`$3F0`). Once the 32X is on, its vector ROM supplies the vectors and the rest is unused. The other entries differ from game to game (checked in the Check Program, Virtua Racing Deluxe, Star Wars Arcade, Mortal Kombat II and After Burner Complete) |
| `$100` | Mega Drive header | Name, serial, checksum, ROM end |
| `$200` | Jump table, one `jmp` per exception | The 68000's real interrupt handlers, once the 32X is on |
| `$3C0` | User header | SH-2 program offset, size and destination; both entry points and vector bases |
| `$3F0` | Sega's initial program | The same 1,040 bytes in every cartridge. Recognise it by its copyright string and skip it |
| `$800` | Start of the 68000 program | Runs at `$880800` |

See [The cartridge layout](32x-hello.md#the-cartridge-layout) and [The user header](../32x/boot.md#the-user-header).

One byte of the cartridge can be seen in seven ways, each with its own address, and a disassembly needs all that apply:

| View | Address of cartridge offset *n* |
|------|------------------------------|
| File | *n* |
| 68000, 32X on | `$880000` + *n* (first 512 KB), or through the bank window |
| 68000, RV set | `$000000` + *n*, only while RV = 1 ([The RV bit](../32x/architecture.md#the-rv-bit)) |
| SH-2 through the cache | `0x02000000` + *n* |
| SH-2 bypassing the cache | `0x22000000` + *n* |
| The SH-2 program after the boot copy | destination + (*n* − source) |
| A 68000 routine copied to work RAM | RAM address + (*n* − routine start), as with the Check Program's `$3876`, copied to `$FF0000` |

A pointer in the program may use any of these, or none that a CPU can use directly: it may be stored as a file offset, which no CPU can use until the program adds a base. The Check Program does this twice. Its message tables and the routine table at `$42E8` both hold file offsets, and the code adds the base `$880000`, which the start-up code at `$092C` stores at `$34(a6)` (`a6` points at the program's variables in work RAM) [MARS-CHECK]. When searching for references to something, try every form that applies.

For the Check Program, the user header says the SH-2 program is 24,576 bytes from `$00A000`, copied to `0x06000000`, with the Master starting at `0x06000130` and the Slave at `0x06003130` [MARS-CHECK].

## Strings first

The fastest way into an unknown program is its text. `strings` on the Check Program lists more than 300 test names and results, in the order the menus show them: register read/write checks for every 32X register from both sides, the PWM FIFO's empty and full flags, frame buffer overwrite and byte writes, the SH-2 interrupts, the three display modes, sound [MARS-CHECK]. That is a table of contents before any code has been read.

The next step is to find who uses a string. Search the file for the string's address in each of the forms above. The Check Program shows both how this works and how it can mislead, because two of its tests check the DREQ control register:

- `DREQ CONTROL REGISTER R/W OK` is at `$130C8`. Its file offset, as a longword, appears at `$12A0E`, in a table of 64 pointers to the "OK" messages. The table starts at `$129FA`, so the entry is number 5. The routine at `$0DBA` prints a message by number: it loads `$8929FA` (the table at `$880000` + `$129FA`), shifts the number left twice, reads the pointer and adds the base from `$34(a6)`. The "ERROR" messages are in a second table of 63 entries at `$12CB6`, read the same way by `$1142` and `$0FB2`.
- Number 5 is printed by the test that runs on the 68000 alone (code at `$1A60`, which runs the part from `$1ABA` in RAM). The test that needs an SH-2 has its own message, `MD&SH MASTER DREQ CTL R/W OK` at `$13E24`, whose pointer is at `$12ADE`: entry `$39`. A similar-looking string does not mean a similar routine.

To get from the message to its code, search for the number. `moveq #$39,d0` (the word `$7039`) occurs twice in the program's first 64 KB, at `$383A` (just before `bsr.w $0DBA`, the success path) and `$384E` (before `bsr.w $1142`, the failure path). Both are in the routine at `$37DC`. Nothing calls `$37DC` by name: its address occurs once in the whole program, at `$42FA`, in the table of test routines described below. It is the fifth of the 20 routines the test runner calls, the Master's DREQ control test; the sixth, `$38B4`, is the Slave's and prints message `$3A` [MARS-CHECK].

## Following the code

Three things make code harder to find than it should be:

- **Registers through a base.** The Check Program's routines load `$A15100` into an address register and reach every 32X register as an offset from it. A search for `$A15106`, the DREQ control register, finds nothing; a search for `$A15100` finds 52 places, and the offsets follow from there [MARS-CHECK]. On the SH-2, the same idea uses GBR: with GBR = `0x20004000`, `mov.b @(7,gbr),r0` reads `0x20004007`.
- **Tables of routines.** The Check Program's 68000 test runner at `$31B4` walks a table at `$42E8`: a count word (19) and then 20 longword offsets, each added to the base at `$34(a6)`. It calls each routine with `jsr (a1)` and treats a set carry flag as a failure [MARS-CHECK]. Find the dispatcher, and the table lists every routine it can reach.
- **Work split between CPUs.** One feature can be half on the 68000 and half on an SH-2. Find what passes between them, usually the [communication ports](../32x/communication.md), and look for the matching code on the other side.

### Worked example: one test, both CPUs

The Check Program's header dates it May 1994 (`(C)SEGA 1994.MAY` at `$110`). Its test of the DREQ control register that needs an SH-2, the one found under [Strings first](#strings-first), runs like this [MARS-CHECK]:

1. **The 68000 sends a command.** It writes one longword at `$A15120`: `$800D0000` for the Master, which puts `$800D` in the word at `$A15120`, or `$0000800D` for the Slave, which puts it in the word at `$A15122` (the toolchains call these words COMM0 and COMM2, see [the port addresses](../32x/communication.md#addresses-and-names)). It waits for the next frame, sets a bit in `$A15103` (bit 0 for the Master's CMD interrupt, bit 1 for the Slave's), and waits up to 600 frames for the SH-2 to clear it. If the bit stays set, the test ends with the message `SH2 MASTER TIMEOUT ERROR` (number `$15`).
2. **The 68000 copies its test into work RAM and runs it there.** The routine at `$3876` is copied to `$FF0000` before it is called. It writes to RV, which removes the cartridge from the 68000's map, so it must not be running from the cartridge ([The RV bit](../32x/architecture.md#the-rv-bit)).
3. **The test.** With interrupts off, it writes each value from 7 down to 0 into `$A15107`, covering every combination of RV, bit 1 and 68S. After each one it reads the byte at `$A15124` (COMM4 in the toolchains' names), masks it with `$87` and compares it with the value written, until they match. The wait is bounded: a counter starts at `$FFFF` and a `subq.w` and `bcs` pair gives up when it borrows, after 65,535 reads (it is not a `dbra`, which would allow 65,536). If it gives up, the routine clears `$A15107`, restores interrupts and returns failure. The caller sends `END ` anyway, prints `MD&SH MASTER DREQ CTL R/W ERROR` (message `$39` in the error table), counts an error and returns with carry set, which the runner treats as a failed test.
4. **The SH-2's half.** The CMD interrupt handler posts the command word. The Master's main loop masks it with `$7F` and indexes a table at `0x06000214`; entry `$0D` is `0x06000D68`. (The Slave has its own copy of the loop, with a table at `0x06003214` and the same routine at `0x06003D90`.) The routine loops until the longword at `0x20004020` holds `END `. Each time round it reads `0x20004007`, its own view of the register the 68000 writes at `$A15107`, masks it with `$87` and writes the result to the byte at `0x20004024`, which is the byte the 68000 reads at `$A15124`. When `END ` appears it clears the longword and returns.

Two details of the SH-2 half. The two routines have identical bytes, but the Slave's image is not a straight copy of the Master's: from about `0x06003534` it has 40 (`$28`) more bytes of code, so every command routine after that sits `$28` higher than the Master's. And the mask `$87` also keeps bit 7. On the 68000 side that bit of `$A15107` is FULL. On the SH-2 side FULL and EMPT are bits 15 and 14, in the byte at `0x20004006`, so bit 7 of `0x20004007` is not defined in the manual's table, and the test passes only if it reads 0. Why Sega's code keeps it is not known.

`END ` is four characters, 32 bits, and a communication word holds 16. The 68000 therefore writes it as a longword at `$A15120`, and the SH-2 compares a longword at `0x20004020`: the words COMM0 and COMM2 together. These are the two words that carried the command in step 1, the Master's in the first and the Slave's in the second. The longword write replaces whichever was there, and the SH-2 clears both when it sees `END `. The 68000 waits until the longword reads 0 before it starts the next test. The tests run one at a time, so they can share the words.

Because the 68000's wait is bounded and a timeout is reported, the test fails unless the SH-2 reports all three low bits as the 68000 wrote them. On a machine where the SH-2 read bit 1 as 0, the values 7, 6, 3 and 2 would time out. So Sega's own test expected bit 1 to be stored and visible to the SH-2. Sega's July 1994 hardware manual, two months younger than the program, shows bit 1 as a fixed 0 on the SH-2 side [32X-HWM p.30], so the two disagree <span class="tag disputed">disputed</span> ([discrepancy 25](../appendices/discrepancies.md)).

Two other sources explain why the bit exists and why the manual shows it as 0. The April 1994 overview describes bit 1 as a DMA setting that captures a Mega Drive DMA [32X-INTRO], and Sega's later technical information list says that capture DMA cannot be used [32X-TI item 13]. They do not choose between two readings, and both stay open. The hardware may have changed after the program was written, so that the bit is gone. Or the chip may still store the bit, with the function it controlled switched off, and the manual shows 0 because nothing may use it. Only a console can tell them apart.

An emulator can at least run the test. In the VRD project's headless PicoDrive front end, the Check Program runs to its closing screen, which says that everything finished normally, within 7,000 frames, so this test passes there <span class="tag emulator">emulator</span> [VRD-NOTES, libretro profiling front end]. The same front end can run the failing case. Take a copy in which the Master's mask byte, the `$87` of the literal at `0x06000D80` (cartridge offset `$AD83`), is changed to `$85`, so that bit 1 is never reported, and the header checksum at `$18E` is set to 0 so that Sega's initial program skips the check. A control copy with only the checksum change runs to the end like the original.

The patched copy does not pass, and how it fails depends on the emulator. In PicoDrive as built, the 68000's program counter stays at `$FF001C`, inside the wait loop, from frame 585 to the end of a 4,000-frame run, with interrupts masked and the frame counters standing still. The wait should give up after 65,535 reads. It never does, because PicoDrive's poll detection (`m68k_poll_detect`) puts the 68000 to sleep when it keeps reading the same communication port, and the SH-2 keeps writing the same value [PICODRIVE, `pico/32x/memory.c`]. In a core built with that detection switched off (`notes/games/tools/build_nopoll_core.sh`), the wait gives up and the program shows its own error screen: `MD&SH MASTER DREQ CTL R/W ERROR`, address `00A15107`, write data `07`, read data `05`, test 43 of 161, error count 1. Its error log holds the same figures (message `$39`, written 7, read 5). Read data 5 is 7 with bit 1 masked off, as the SH-2's `$85` mask makes it. After the error the runner waits 300 vertical blanks in its failed-test loop (`$3256`-`$326A`, frames 614 to 913), carries on with the remaining tests, and ends on this error screen, waiting for a button in the routines around `$0AF6` <span class="tag emulator">emulator</span>.

This confirms the reading of the code: the test fails when the SH-2 does not report bit 1, and it says which value went wrong. It says nothing about the hardware, because the SH-2 here is the emulator's, with one byte edited. That the unmodified program passes in PicoDrive is weak evidence about a console, since an emulator may have been written, or tuned, to pass this very program.

That is the kind of result this method is for: a question about the hardware answered, or at least sharpened, by code its makers wrote.

## Data that looks like code

A disassembler decodes whatever it is given. Vector tables, literal pools and text all come out as instructions:

- The start of the Check Program's SH-2 program is its vector table, and `sh-elf-objdump` shows it as a run of `mov.b r0,@(r0,r12)` and similar. The constant `END ` in a literal pool comes out as `.word 0x454e` followed by `shal r4`, and the mask `$87` as `mul.l r8,r0` [MARS-CHECK].
- In Mortal Kombat II's SH-2 program, most of what follows `0x060051E2` is palettes and tables [MK2].
- **Delay slots.** On the SH-2 the instruction after a delayed branch (`bra`, `bsr`, `jmp`, `jsr`, `rts`, `bt/s`, `bf/s` and the rest) runs before the branch takes effect, so read the pair as one step. The listing shows the slot after the branch, and the routine's real last instruction is the one after its `rts`; a literal pool starts after that. The Check Program's loop at `0x06000D68` ends with `bra 0x06000D6C` and a `nop` in the slot, and its pool of constants follows [MARS-CHECK; SH-PM §4.1.5 p.23]. The rules are in [Delayed branches](../sh2/isa.md#delayed-branches).

So trace code from known entry points: the vectors, the jump table, the user header's entries and every dispatcher table you find. Treat everything you have not reached as data until something calls it. Tracing by hand has a limit, though. The Check Program's 20 test routines are reached only through the table at `$42E8`, with a base added from RAM: each routine's address occurs once in the 68000 program, in the table, and no branch leads to it, so a disassembler that follows branches never finds them.

An emulator closes that gap. Run the program and log every address that executes, for each CPU: anything in the log is code, whatever the disassembler thought, and a routine called through a table shows up as soon as the table is used. This is the per-address histogram described in [Measuring a game from outside](profiling.md#measuring-a-game-from-outside), taken with the harness in [Emulator testing](emulator-testing.md#the-harness). The book's front end keeps only the 200 busiest addresses per CPU, so it finds the hot code and not all of it; for coverage, record each distinct address once. Run the interpreter, not the recompiler, whose addresses are not the program's. Code that ran in one session proves that address is code, but code that did not run proves nothing: a menu you never opened is still code.

Use a disassembler that decodes only the instructions the CPU has. `sh-elf-objdump -b binary -m sh2 -EB` decodes the SH-2's instruction set exactly. Capstone's SH-2 mode also accepts instructions from later SuperH chips: of the 65,536 possible 16-bit words it decodes 452 that are not SH-2 instructions, and 10 words of Star Wars Arcade's SH-2 program are among them (checked for this book with capstone 5.0.7) [SWA]. A word that shows as one of those is data or an error ([What only the SH-2 has](../sh2/isa.md#what-only-the-sh-2-has)). For the 68000, capstone's 68000 mode works well.

An SH-2 literal load reads relative to the program counter. With *A* the address of the load instruction itself, a longword load (`mov.l @(disp,PC),Rn`) reads `(A & ~3) + 4 + 4 × disp`, and a word load (`mov.w`) reads *A* + 4 + 2 × disp, with no masking. Hitachi's manuals write the same thing with PC = *A* + 4, so `(PC & ~3) + 4 × disp` for a longword [SH-PM §4.2 pp.26-28]. For example, the `mov.l` at `0x06000D68` has disp 4 and reads `0x06000D7C`, which holds `END `; the `mov.w` at `0x060003D4` has disp 10 and reads `0x060003EC` [MARS-CHECK]. The assembler takes the byte offset and scales it itself ([Data and addressing](../sh2/isa.md#data-and-addressing)). Getting either wrong points every constant in a routine at the wrong place [VRD-NOTES, KNOWN_ISSUES].

## Turning `dc.w` back into instructions

The safe way to start a rebuildable disassembly is to have nothing to break:

1. **Begin with the whole ROM as data**: `dc.w` lines or an included binary, which assemble to the original by definition.
2. **Split it into files.** The VRD project used 8 KB sections, 384 of them for its 3 MB ROM [VRD-NOTES, DISASSEMBLY_ANNOTATION_GUIDE]. The Aerobiz disassembly went further, with one file per function [AB-DISASM].
3. **Convert one block at a time to instructions**, rebuild and compare with the original after each. A wrong conversion shows up at once, and only one block is suspect.
4. **Automate the routine part.** The Aerobiz project converted every translatable block with a script that turns capstone's output into vasm source, and kept as `dc.w` anything the assembler would encode differently [AB-DISASM].

What the assembler encodes differently is covered in [The assembler may choose the encoding](toolchain.md#the-assembler-may-choose-the-encoding): unused bits the original compiler filled with junk, short absolute addresses, `bsr` against `jsr (pc)`. One report needs correcting. The VRD project concluded that vasm's `bsr.w` lands two bytes past its target [VRD-NOTES, KNOWN_ISSUES], while the Aerobiz project found it correct across 332 calls [AB-DISASM, KNOWN_ISSUES]. vasm 2.0d encodes it correctly (checked for this book: a `bsr.w` at offset 0 to a target 8 bytes on assembles with displacement 6). The 68000 measures the displacement from the word after the opcode [M68K-PRM], which is what vasm does. Whatever caused the VRD failure, it was not the assembler's arithmetic.

## Naming and annotating

- **Name a routine from what it touches.** The ports, registers and RAM a routine reads and writes say what it does. Names guessed from where a routine is called from are often wrong; many of the Aerobiz disassembly's early labels were [AB-DISASM].
- **Tell compiled code from hand-written code.** Compiled 68000 code usually has `link a6` frames and arguments on the stack cleaned up by the caller; the compiler Aerobiz was built with also widens byte and word values to longwords with `ext.l` and `andi.l #$ff`, a habit of that compiler rather than of compiled code in general. Hand-written code keeps fixed roles for registers, such as one always pointing at the VDP, and uses PC-relative jump tables [AB-DISASM]. Knowing which you are reading tells you what conventions to expect.
- **Write down what is known and how.** A header block per routine with its purpose, inputs, outputs and the RAM it uses [VRD-NOTES, DISASSEMBLY_ANNOTATION_GUIDE], plus how each claim was established: read from the code, seen in an emulator, or guessed.
- **Check that something reads an address before building on it.** The VRD project built a patch around render-state addresses taken from its own older notes. A memory watch then showed the renderer never read them, and the patch changed nothing [VRD-NOTES, VR60 roadmap]. A watch in a headless emulator settles such questions in minutes ([The harness](emulator-testing.md#the-harness)).

## Rebuilding byte for byte

Make the comparison part of the build, so that every build either matches the original or fails. Two cautions:

- **The comparison must see every input.** In the Aerobiz Ultimate Makefile, a file missing from the list of included sources did not trigger a rebuild, and the check then passed against a stale binary [AU-NOTES, Makefile].
- **A match proves equality with the file you have**, nothing more. See the first section.

## Changing it

Once the source rebuilds, it can be changed. The reference projects learned these rules the hard way:

- **Keep shared code the same size.** If anything after a patch has to stay at its address, a patch must not grow it. Aerobiz Ultimate pays for extra bytes with provably dead code nearby: once, a two-byte growth pushed the cartridge to 2 MB + 2 bytes and the game never reached the SEGA screen [AU-NOTES, KNOWN_ISSUES].
- **A hook that calls the original routine must rebuild its arguments.** Routines that take arguments on the stack find them above their return address. A hook that is called in place of the routine and then calls it adds a second return address, and every argument is read four bytes off. Push the arguments again before the call, and remove exactly as many bytes afterwards [AU-NOTES, KNOWN_ISSUES].
- **Move code out with trampolines.** When a routine must grow, copy it elsewhere and leave a jump at each old entry point. Move whole blocks. A branch and its delay slot must stay together, so a patch that ends between them leaves the slot behind, and routines that share a slot or branch into each other cannot be moved one at a time. The VRD project moved three Slave routines that formed one 278-byte state machine into spare cartridge space for this reason: one routine's `rts` slot was the next routine's first instruction [VRD-NOTES, COORD_TRANSFORM_INLINING_INFEASIBILITY]. Moving them was not the saving. It made room to inline a 34-byte helper at the block's three calls to it, which grew the block to 388 bytes. Each copy is 16 words (32 bytes, the helper without its `rts`) and replaces a 2-byte `bsr`. The block's eight other `bsr` calls, to a routine left in place, each became a load and a `jsr`, 2 bytes more, because the new home at cartridge `$301300` is nearly 3 MB from the routine at `$234A0` and a `bsr` reaches only 4 KB either way ([Addressing modes](../sh2/isa.md#addressing-modes)); they share one 4-byte literal. So 278 + 3 × 30 + 8 × 2 + 4 = 388. The project's notes give the 16-word copies, the eight calls and both sizes; the sum is this book's. The project also recomputed 20 branches and left 6 trampolines, and estimated the saving at about 19,200 SH-2 cycles per frame (about 6 cycles for each of 3,200 calls), a figure worked out from the call count, not a measured one. It is also gross: it counts the removed `bsr` and `rts` and does not subtract the literal load that now precedes each of the eight `jsr` calls, whose call counts the notes do not give [VRD-NOTES, KNOWN_ISSUES and OPTIMIZATION_PLAN, S-6].
- **Watch SH-2 assembler details.** In `sh-elf-as`, `.align 2` means four bytes, not two; `@(disp,Rn)` takes a byte offset; and a ROM address in a literal must have all eight hex digits. The VRD project found five literals with a dropped zero, such as `0x020A1F0` for `0x0200A1F0`, each silently reading the wrong memory [VRD-NOTES, KNOWN_ISSUES]. The same slip can hit any address with a leading zero, such as `0x06…`, `0x22…` or `0x20004…`, so search the source for every seven-digit hex constant and check each one. A disassembler listing cannot be searched this way, because it prints addresses without their leading zeros.

## What to take away

- Check a dump's MD5, checksum and size before trusting anything built on it; only the MD5 shows the file is unmodified.
- Read the user header to split the 68000 and SH-2 programs, and keep a table of the addresses a byte has in each view: file, 68000, SH-2 cached and uncached, and any RAM copy.
- Start from strings, follow them to tables, and follow tables to code; look for registers reached through a base.
- Trace code from entry points and treat the rest as data, then run the program and log executed addresses to find the code that tables hide.
- Convert `dc.w` a block at a time with a byte-for-byte comparison in every build.
- Name routines from what they touch, and record how each claim is known.

## Open questions

- The Mars Check Program's register tests agree with the July 1994 manual everywhere except bit 1 of the DREQ control register, and bit 7 of the SH-2's byte at `0x20004007`, which the manual's table leaves undefined and the test requires to read 0, as far as they have been read. Its SH-2-side VDP and frame buffer tests have not been read yet.
- Did the hardware change between the Check Program (May 1994) and the manual (July 1994), or does the manual describe bit 1 as 0 while the chip stores it? Only a console run of the DREQ control test can say.
- What do the SOJ and Texture Test sample discs do?

## Sources

- [MARS-CHECK](../appendices/bibliography.md#mars-check): header date (`$110`) and vectors; strings and message tables (OK `$129FA`, ERROR `$12CB6`), message printers `$0DBA`, `$1142`, `$0FB2`; base store `$092C`; 68000 test runner `$31B4`, routine table `$42E8`; Master DREQ control test `$37DC` with its RAM part `$3876`, Slave test `$38B4`, 68000-only test `$1A60`/`$1ABA`; SH-2 command loop `0x060001BA`, jump tables `0x06000214` and `0x06003214`, echo loops `0x06000D68` and `0x06003D90`, CMD handlers `0x0600044C` and `0x0600344C`
- [PICODRIVE](../appendices/bibliography.md#picodrive): `pico/32x/memory.c` (68000 poll detection)
- [VRD-NOTES](../appendices/bibliography.md#vrd-notes): DISASSEMBLY_ANNOTATION_GUIDE; KNOWN_ISSUES (dropped-zero literals, S-6); OPTIMIZATION_PLAN (S-6); analysis/optimization/COORD_TRANSFORM_INLINING_INFEASIBILITY.md; libretro profiling front end; VR60 roadmap
- [AB-DISASM](../appendices/bibliography.md#ab-disasm): KNOWN_ISSUES; README
- [AU-NOTES](../appendices/bibliography.md#au-notes): KNOWN_ISSUES; Makefile
- [EGYPT](../appendices/bibliography.md#egypt), [GNU-SIERRA](../appendices/bibliography.md#gnu-sierra), [ECCO](../appendices/bibliography.md#ecco), [SWA](../appendices/bibliography.md#swa)
- [32X-HWM](../appendices/bibliography.md#32x-hwm): p.30 (DREQ control register); [32X-INTRO](../appendices/bibliography.md#32x-intro): DREQ control register; [32X-TI](../appendices/bibliography.md#32x-ti): item 13
- [32X-ROMSET](../appendices/bibliography.md#32x-romset), [MK2](../appendices/bibliography.md#mk2), [AB32X](../appendices/bibliography.md#ab32x): vector tables at `$000` (reset vector `$3F0`, the rest differing); MK2's SH-2 program after `0x060051E2`
- [VASM](../appendices/bibliography.md#vasm): `bsr.w` displacement (checked for this book)
- [M68K-PRM](../appendices/bibliography.md#m68k-prm): BSR
- [SH-PM](../appendices/bibliography.md#sh-pm): §4.1.5 p.23 (delayed branches); §4.2 pp.26-28 (PC-relative addressing)
