# Hello world on the 32X, all CPUs running

This chapter builds a small cartridge in which each of the three CPUs shows on screen that it is running:

- **The 68000** puts a bar of Mega Drive tiles across the bottom of the screen and changes its colour every frame.
- **The Master SH-2** owns the 32X picture. Each frame it swaps the frame buffers, clears the new back buffer, and draws a yellow square moving right.
- **The Slave SH-2** draws a green square moving left, in the same buffer, after the Master tells it the frame number.

If the bar changes colour, the 68000 is alive. If the yellow square moves, the Master is. If the green one moves, the Slave is, and the two SH-2s are in step. The ROM uses no interrupts, no sound and no compiler: two assembly files, 350 lines in all.

<span class="tag emulator">emulator</span> It boots and runs in ares 148, which uses the real 32X boot ROMs, and in the libretro build of PicoDrive [ARES; PICODRIVE]. It has not been run on a console.

The full sources are [`md.s`](32x-hello/md.s) (68000 side and the cartridge layout), [`sh2.s`](32x-hello/sh2.s) (both SH-2s) and [`build.sh`](32x-hello/build.sh). The listings below are taken from them.

## What you need

- **Assemblers.** GNU binutils for `sh-elf` and for the 68000. The build script uses `sh-elf-as`, `sh-elf-ld` and `sh-elf-objcopy`, and `m68k-linux-gnu-as` and `m68k-linux-gnu-ld`; any m68k binutils will do. See [Toolchain setup](toolchain.md).
- **Sega's initial program.** Every 32X cartridge must carry Sega's 1,040-byte block at `$3F0-$7FF`, unchanged, or the Master's boot ROM refuses to start it ([The security check](../32x/boot.md#the-security-check)). It is Sega's code, so this book does not reproduce it. The build script copies it from a 32X cartridge dump you supply.

## The cartridge layout

| Offset | Contents | Read by |
|--------|----------|---------|
| `$000` | 68000 vectors: stack, and reset at `$3F0` | The 68000 at power-on, before the 32X is switched on |
| `$100` | Mega Drive header, starting `SEGA 32X` | The console |
| `$200` | Jump table, one 6-byte `jmp` per exception vector | The 68000, once the 32X is on ([Architecture](../32x/architecture.md#after-the-32x-is-switched-on-aden--1)) |
| `$3C0` | MARS user header: where the SH-2 program is, how big, and where each SH-2 starts | The Master's boot ROM ([The user header](../32x/boot.md#the-user-header)) |
| `$3F0` | Sega's initial program | Both the 68000 and the Master's boot ROM |
| `$800` | The 68000 program | The 68000, at `$880800` |
| `$2000` | The SH-2 program | The Master's boot ROM, which copies it to SDRAM |

```text
{{#include 32x-hello/md.s:layout}}
```

Points to notice:

- **The checksum field at `$18E` is 0**, which tells the initial program and the Master's boot ROM to skip the checksum ([The checksum](../32x/boot.md#the-checksum)).
- **Exception vector *n* jumps to `$880200` + 6 × (*n* − 1)** once the 32X is on, because the 32X's own vector ROM takes over the 68000's vectors. Nothing in this program should raise an exception, so all 47 entries go to a loop that halts [VRD-NOTES, 32X BIOS dump]. Even the reset button does; a real program must handle it ([Pressing reset](../32x/boot.md#pressing-reset)).
- **The SH-2 program is copied to the start of SDRAM** (destination 0). Its size must be a multiple of 4, because the boot ROM copies longwords [32X-HWM §5.1].
- **Both SH-2s use one vector table**, at the start of the SH-2 program. The Master starts at `0x06000200` and the Slave at `0x06000400`.

## The 68000

The initial program returns to `$880800` with the result in the carry flag and `d0` ([The verdict](../32x/boot.md#the-verdict)). The 68000's job after that is short:

```text
{{#include 32x-hello/md.s:start68k}}
```

1. **Check the verdict.** On any error the program shows a red screen and stops.
2. **Release the SH-2s.** Wait for `M_OK` at `$A15120` and `S_OK` at `$A15124`, then clear both. The SH-2 programs wait for exactly that ([The handshake](../32x/boot.md#the-handshake-into-your-code)).
3. **Set up the Mega Drive VDP.** The initial program leaves the display off. Eleven register writes turn it on in 320-pixel mode with plane A at `$C000`, then the program writes one tile filled with colour 1 at VRAM `$0020` and fills three rows of plane A with it. The command words are explained in [The VDP: the ports](../megadrive/vdp.md#the-ports).
4. **Loop once per frame.** Wait for the start of vertical blank on the VDP status register, then write a new value to colour 1 of the Mega Drive palette.

The rest of the Mega Drive screen is backdrop. With PRI = 0 and no through bits, backdrop pixels show the 32X picture and the bar's pixels hide it ([The rule for each pixel](../32x/compositing.md#the-rule-for-each-pixel)).

## Starting both SH-2s

The Master's boot ROM copies the SH-2 program to SDRAM, sets each CPU's vector base from the user header and jumps to the two entry points. Each CPU starts with SR = `$F0` (all interrupts masked), the cache on, and its stack at the top of SDRAM ([What your code starts with](../32x/boot.md#each-sh-2-at-its-entry-point)). This program never lowers the mask, so it needs none of the interrupt workarounds in [Hardware bugs](../32x/bugs.md#the-sh-2-interrupt-flaw).

Each SH-2 first waits until the 68000 has cleared its word. The Master then takes the 32X VDP and sets up the screen:

```text
{{#include 32x-hello/sh2.s:master_setup}}
```

- **Take FM with a byte write.** Writing `$80` to `0x20004000` sets FM and leaves the low byte, with the interrupt mask bits, alone ([System registers](../32x/registers.md#0x20004000-interrupt-mask)).
- **Set the palette while the VDP is blank.** The initial program leaves the 32X in blank mode, where the palette can be written at any time ([Colours and the palette](../32x/vdp.md#colours-and-the-palette)). The colours are 15-bit with red in the low bits: `$3000` is dark blue, `$03FF` yellow, `$03E0` green.
- **Write a line table into both frame buffers.** Each buffer has its own. The program writes one, flips FS, waits until FS reads back the new value, and writes the other. In blank mode the flip happens at once ([Frame buffers and the FS bit](../32x/vdp.md#frame-buffers-and-the-fs-bit)). Line *n* starts at word `$100` + 160 × *n*: 320 pixels of one byte each, after the 256-word table ([The line table](../32x/vdp.md#the-line-table)).
- **Switch on packed pixel mode last**, so nothing half-built is ever shown.

All 32X addresses are the cache-through `0x2…` forms. The program's own code and constants are read through the cache.

## Drawing and swapping

Each frame, the Master runs this loop:

```text
{{#include 32x-hello/sh2.s:master_frame}}
```

1. **Wait for the start of vertical blank.** VBLK is bit 15 of the frame buffer control register, so a signed word read is negative while it is set. The loop waits for it to clear, then to set again, so it catches the start of the blank, not the middle.
2. **Flip FS, and wait until it reads back.** During vertical blank the swap happens at once. Until FS reads the new value, the CPU would still be writing to the buffer on screen.
3. **Clear the back buffer with auto fill.** The pixels take 35,840 words, exactly 140 blocks of 256 words starting at word `$100`. Each fill is one block, and the program waits for FEN to clear before starting the next ([Auto fill](../32x/vdp.md#auto-fill)).
4. **Hand over to the Slave** by writing the frame number into `COMM12` (`0x2000402C`).
5. **Draw the Master's square**, 32 by 32 pixels, two pixels per word write.
6. **Wait for the Slave** to write the same frame number into `COMM14` (`0x2000402E`).

The two helper routines, used by both CPUs:

```text
{{#include 32x-hello/sh2.s:helpers}}
```

## Showing that the Slave is alive

```text
{{#include 32x-hello/sh2.s:slave}}
```

The Slave waits for a new number in `COMM12`, draws its square in the same back buffer, and writes the number back in `COMM14`. Each word has one writer: the Master writes `COMM12` and the Slave writes `COMM14`, which is the rule that keeps the communication ports safe ([The one hazard](../32x/communication.md#the-one-hazard-a-word-that-changes-while-you-read-it)). The two SH-2s draw at the same time; they share the bus, so each waits now and then for the other's writes.

The Slave only starts drawing after the Master has finished clearing. If it drew while a fill was running it could be overwritten, or, by the manual, its accesses could fail ([Auto fill](../32x/vdp.md#auto-fill)).

Both CPUs poll the ports in tight loops. That is fine here, where they have nothing else to do. In a real program a polling SH-2 takes bus time from one that is drawing ([Polling or interrupts?](../32x/communication.md#polling-or-interrupts)).

## Building

```sh
{{#include 32x-hello/build.sh}}
```

Two things went wrong while this ROM was written, and both are easy to repeat:

- **`objcopy` produced a 973 MB file.** Without `-j .text`, `sh-elf-objcopy -O binary` also emitted an empty section that the linker had put at a low address, and filled the space between it and `0x06000000` with zeros.
- **The clear loop never ended.** It was first written `mov #140,r4`. An SH-2 immediate is 8 bits and sign-extended, so 140 loaded as −116 and the loop counted down through four billion. The background still came out blue, because the buffers were already clear, but neither square ever appeared. Constants above 127 have to come from a literal ([Data and addressing](../sh2/isa.md#data-and-addressing)).

## Running it

- **ares 148** runs the real 32X boot ROMs, so the security check, the SDRAM test and the copy all happen as on a console. The ROM shows both squares and the changing bar at 60 frames per second <span class="tag emulator">emulator</span> [ARES].
- **The libretro build of PicoDrive** does not load the 32X boot ROMs, and neither do PicoDrive's other builds: the loader in its source is compiled out. Instead it copies the SH-2 program from the user header itself and starts both CPUs, so it skips the security check and the SDRAM test [PICODRIVE, platform/common/emu.c, pico/32x/32x.c]. The ROM runs the same there. A ROM with a broken initial program would also run there, so test a new layout in ares first <span class="tag emulator">emulator</span>.

## What this leaves out

- **Interrupts.** A real program wants the V interrupt at least. That brings in the free-running timer set-up and the TOCR workaround ([Interrupt controller](../sh2/intc.md#segas-rules-the-sh-2-interrupt-flaw)).
- **The reset button**, and VRES on the SH-2s ([Pressing reset](../32x/boot.md#pressing-reset)).
- **Mega Drive interrupts and the Z80.** The 68000 polls the VDP status and leaves the Z80 held in reset, as the initial program left it.
- **Sound.** See [PWM audio](../32x/pwm.md).
- **A compiler.** Most 32X programs are written in C. The structure stays the same: the start-up code waits for its handshake word, and `main` follows.

## What to take away

- A 32X cartridge is a Mega Drive cartridge with three extra parts: the jump table at `$200`, the user header at `$3C0` and Sega's initial program at `$3F0`.
- The 68000 must check the initial program's verdict and clear `M_OK` and `S_OK`; each SH-2 waits for that before doing anything.
- Take FM, then set up the palette and both line tables while the 32X is still blank.
- Flip FS in vertical blank and wait for it to read back before drawing.
- Give every communication word one writer.
- Test new start-up code in an emulator that runs the real boot ROMs.

## Sources

- [32X-HWM](../appendices/bibliography.md#32x-hwm): §5.1 (user header, boot ROM)
- [VRD-NOTES](../appendices/bibliography.md#vrd-notes): 32X BIOS dump (vector ROM table)
- [ARES](../appendices/bibliography.md#ares): version 148
- [PICODRIVE](../appendices/bibliography.md#picodrive): pico/32x/32x.c (boot without the BIOS), platform/common/emu.c (the compiled-out BIOS loader)
