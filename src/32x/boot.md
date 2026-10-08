# Boot, security code and initial program

Between power-on and the first instruction of your game, three programs written by Sega run on three CPUs. They check that the cartridge is licensed, put every chip in a known state, copy your SH-2 code into SDRAM and start both SH-2s on it. The manuals describe this with a flowchart and a sample listing. This chapter follows the code itself, because several details your program depends on are only visible there.

> **How this chapter was worked out.** The boot steps below come from disassembling the three 32X boot ROM dumps and the copy of Sega's initial program in the Virtua Racing Deluxe project's cartridge, which is byte for byte the same as in every retail game read for this book [VRD-NOTES, 32X BIOS dump; VRD-NOTES, ROM], and from checking them against the manuals. Reading the code tells you what it *does*. It does not prove how the hardware reacts, so claims about hardware timing or reset behaviour are marked where they rest on the manual alone.

## The pieces

| Piece | Where | Size | Written by | Runs on |
|-------|-------|------|------------|---------|
| Cartridge vectors | Cartridge `$000000` | 256 bytes | You | 68000, at power-on only |
| Jump table | Cartridge `$000200` | 6 bytes per vector | You | 68000, once the 32X is on |
| User header | Cartridge `$0003C0-$0003EF` | 48 bytes | You | Read by the Master SH-2 boot ROM |
| Initial program | Cartridge `$0003F0-$0007FF` | 1040 bytes | Sega, copied unchanged | 68000 |
| 68000 vector ROM | Inside the 32X | 256 bytes | Sega | 68000, once the 32X is on |
| Master boot ROM | Inside the 32X | 2 KB | Sega | Master SH-2 |
| Slave boot ROM | Inside the 32X | 1 KB | Sega | Slave SH-2 |

Sources: [32X-HWM §3.1, §5.1-5.2; AU-NOTES, security block].

The initial program is the same in every cartridge that boots. For `$000400-$0007FF` the boot ROM guarantees it: the Master compares those 1024 bytes with its own copy and stops on any difference (see [The security check](#the-security-check)). Nothing checks the first 16 bytes, `$0003F0-$0003FF`, but they match as well in 13 of the 14 undamaged 32X images in the project, retail games and development samples alike. (One of the 14 is the Virtua Racing Deluxe project's own copy, trusted only for its first 2 KB, which is the part compared here.) The exception is the ECCO demo from Sega's development disc. It carries an earlier build of the program, which starts at `$000400` with no 16-byte prefix and differs from the released one in 746 of the 1040 bytes, so the boot ROM's comparison would reject it [SWA; MK2; AB32X; CHAOTIX; MCX, both dumps; MARS-CHECK; EGYPT; RLT; GNU-SIERRA; SOJ; TEXTURE; ECCO; VRD-NOTES, ROM, cartridge `$0003F0-$0007FF` compared]. The copy in the marsdev toolchain's 32x-skeleton example matches byte for byte too [MARSDEV, md_start.s; AU-NOTES, security block]. Your own 68000 code begins right after the initial program, at cartridge `$000800`.

How to lay these out in your own cartridge is covered in [32X header and security code](../howto/32x-header.md).

## The sequence at a glance

```text
 68000                                  Master SH-2                    Slave SH-2
 ─────                                  ───────────                    ──────────
 power-on: cartridge reset vector       boot ROM: 32X not enabled      boot ROM: 32X not enabled
   → $0003F0 (initial program)            → put 32X chip on standby,     → sleep
 look for "MARS", wait for REN            sleep
 unlock TMSS, clear VDP, start Z80,
   silence PSG
 set ADEN from a stub in work RAM;
   continue at $8806BC
 clear work RAM, hold Z80 in reset
 set RES ─────────────────────────────► restart boot ROM               restart boot ROM
 take FM, clear 32X registers,          set up bus, SDRAM, cache       set up bus, cache
   both frame buffers, palette          test and clear SDRAM           wait for "M_OK" in $A15120
                                        compare security code
                                        checksum → $A15128
                                        copy your program to SDRAM
 check for errors, PAL/NTSC match,      "M_OK" → $A15120 ──────────►   "S_OK" → $A15124
   checksum                             jump to your Master code       jump to your Slave code
 fall through to $880800, carry = verdict
 your code: wait for M_OK and S_OK,
   then clear them
```

The rest of the chapter goes through each column.

## Power-on

At power-on the adapter is off (ADEN = 0), so the 68000 sees a plain Mega Drive memory map with the cartridge at `$000000`. It loads its stack pointer and start address from the cartridge's own vector table. The manual requires the start address to be `$0003F0`, the first byte of Sega's initial program, and warns that the 32X is not released if the program is changed or not entered at its start <span class="tag manual">manual</span> [32X-HWM §5.2]. The homebrew start-up code in the bibliography does what the manual asks, with `$0003F0` in its reset vector [MARSDEV, 32x-skeleton mars_start.s; D32XR, crt0.s].

The boot ROM enforces only part of the rule. It compares `$000400-$0007FF`, so it cannot tell whether the 68000 started at `$0003F0` or at `$000400`. Two of Sega's own development samples, Gnu Sierra and the ECCO demo, start at `$000400` [GNU-SIERRA; ECCO, ROM `$000004`]. Neither shows that this works on a console. Nothing in the project records either one running on a console. ECCO's earlier version of the initial program would fail the comparison anyway, and starting at `$000400` skips the work done by the first 16 bytes (see [The security check](#the-security-check)). Start at `$0003F0`.

At the same time both SH-2s start their boot ROMs. Each one reads the adapter control bits, finds ADEN = 0 and goes to sleep. The Master also puts the 32X's own chip on standby first, after a short delay [VRD-NOTES, 32X BIOS dump]. This matches the start of the manual's flowchart, which shows the Master waiting, putting the chip on standby and sleeping before anything else happens [32X-HWM §5.1].

## Sega's initial program on the 68000

### Before the switch

Running from the cartridge at its plain Mega Drive address, the initial program:

1. Clears the communication word at `$A15128`, where the Master will later post the checksum, and masks all 68000 interrupts.
2. Looks for `MARS` at `$A130EC`. If it is missing, no 32X is attached and the program gives up at once with error code 1 (see [the verdict](#the-verdict)).
3. Waits until the REN bit in `$A15101` reads 1. The manual names REN "SH2 reset enable" and says nothing more about it [32X-HWM §3.2.1]; see [System registers](registers.md#a15100-adapter-control).
4. Checks whether this is a restart after the reset button rather than a power-on. If the control registers of I/O ports 1 and 2 (`$A10008`, read as one longword) and of the expansion port (`$A1000C`) are both non-zero, and ADEN already reads 1, it skips everything else. It writes 1 to `$A15106`, which sets RV, and branches to `$000800` with `d0` = `$8000` and the carry clear. A zero in either control register counts as a power-on. The code, with `a5` = `$A10000`, is `tst.l $8(a5)` / `beq.b $436` at `$000420`, `tst.w $C(a5)` / `beq.b $436` at `$000426`, and `btst #0,$5101(a5)` / `bne.w $7EC` at `$00042C`. Each zero test branches to the cold path at `$000436`, so all three conditions must hold. Sega's start-up code for a plain Mega Drive uses the same two reads the other way round: `tst.l $A10008` / `bne.b $20E`, then `tst.w $A1000C`, and at `$00020E` a second `bne.b` to the restart path. There, either register being non-zero counts as a restart [AB-DISASM, ROM `$000200`-`$00020E`]. It is not clear how the 68000 could ever reach this test with ADEN = 1; see [The warm-start exit](#the-warm-start-exit).
5. Writes `SEGA` to `$A14000` if the console's version number is not zero. This is the same four-byte write Sega requires at the start of every Mega Drive program [MD-SWM, security software].
6. Loads 19 VDP registers, clears all of VRAM with a DMA fill, and clears CRAM and VSRAM.
7. Takes the Z80 bus, copies a short startup program into Z80 RAM, lets the Z80 run it, and silences all four PSG channels.

### The switch to the 32X map

Setting ADEN moves the cartridge from `$000000` to `$880000` (see [Architecture and memory maps](architecture.md#the-68000-memory-map)). If the CPU were running from the cartridge at that moment, its next instruction would be fetched from an address that no longer holds it. So the initial program copies a 32-byte stub into work RAM at `$FF0000` and jumps there. The stub sets ADEN and jumps to `$8806BC`, which is the same initial program reached through the new fixed window [VRD-NOTES, ROM; AU-NOTES, security block].

### After the switch

Now running at `$88xxxx`, the program:

1. Clears all 64 KB of work RAM, including the stub it just used, and holds the Z80 in reset.
2. Clears the communication words at `$A15120-$A15127`, then writes 3 to `$A15101` (ADEN and RES). This releases the SH-2s, which start their boot ROMs again, this time with ADEN = 1. See the next section.
3. Loads the 68000 stack pointer from cartridge offset 0, through `$880000`.
4. Takes the 32X VDP for the 68000 (FM = 0). It then zeroes the interrupt control, bank set, DREQ and FIFO setup, and PWM registers, along with the 32X bitmap mode and screen shift.
5. Clears both frame buffers with the 32X VDP's fill function, swapping FS between them, and clears the palette.
6. Reads the Master's status in `$A15120` once, without waiting. `SQER` means the security check failed and `SDER` means the SDRAM test failed. Any other value, including 0, counts as a pass. See [A race in the error checks](#a-race-in-the-error-checks).
7. Puts the default address back into the horizontal interrupt vector at `$000070`, which is RAM ([Architecture and memory maps](architecture.md#after-the-32x-is-switched-on-aden--1)).
8. Compares the PAL/NTSC setting of the Mega Drive (bit 6 of `$A10001`) with that of the 32X (bit 15 of `$A15180`, which reads 1 for NTSC [32X-HWM §3.3, bitmap mode register]). A mismatch is an error.
9. If the cartridge header's checksum field at `$00018E` is not zero, waits until `$A15128` is no longer zero, then compares it with the field. The wait has no time limit and does not look at `$A15120`. See [The checksum](#the-checksum).
10. Clears `$A15128-$A1512F`, zeroes most data and address registers and falls through to `$000800` in the cartridge, which the CPU is now reaching as `$880800`.

Sources: [VRD-NOTES, ROM; 32X-HWM §5.1-5.2].

### A race in the error checks

The 68000 cleared `$A15120` just before it released the SH-2s, so a 0 there at step 6 only means that the Master has not reported yet. The Master posts nothing until both its SDRAM test and its security comparison are over. When either one fails, it stays in a loop that keeps rewriting its error code, and it never posts a checksum [VRD-NOTES, 32X BIOS dump]. Nothing in either program makes the 68000 wait for the Master before step 6. If the Master is still testing when the 68000 reads `$A15120`, a later failure is missed:

- **With a non-zero checksum field**, the 68000 waits at step 9 for a checksum that never comes, and hangs inside the initial program.
- **With a zero checksum field**, the initial program reports success: carry clear, `d0` = 0. Your code then waits for `M_OK`, which never comes.

Either way the console hangs instead of reporting `$0040` or `$0080`.

**Which side wins, estimated from the code.** The count starts when the 68000 sets RES, which releases both SH-2s at once. What follows is arithmetic on the instructions and the manual's timings, not a measurement.

The 68000 spends nearly all of that time on the two frame buffer clears. Each one is 256 fills of 256 words, started one at a time with a wait on FEN after each, so there are 512 fills in all [VRD-NOTES, ROM `$000654`-`$000690`]. A 256-word fill takes 7 + 3 × 256 = 775 SH-2 clocks, 33.7 µs at 23.01 MHz ([Auto fill](vdp.md#auto-fill)). Between two fills the 68000 makes about 17 bus cycles (two register writes, the last FEN test, the loop count), at least 4 clocks each, so about 70 clocks, or 9 µs at 7.67 MHz [32X-HWM §4.4 p.77]. The palette clear adds about 0.3 ms:

| 68000 | Time after RES |
|-------|----------------|
| 512 fills alone | 512 × 33.7 µs = 17.2 ms |
| Fills plus the 68000's own instructions | 512 × (33.7 + 9) µs ≈ 21.9 ms |
| Read of `$A15120` at step 6 | about 17.5-22 ms |

The Master's loops run from its cache and reach SDRAM through the cache-through addresses. An instruction takes one clock and a taken conditional branch three [SH-PM §7.7.5]. A word written to SDRAM takes 2 clocks, and a word read through `0x26000000` takes 12 [32X-HWM §4.4 p.78; SH7604 §7.5.4]:

| Master step | Work | Clocks | Time |
|-------------|------|--------|------|
| Write the counting pattern | 32,768 passes of 4 words, 12-16 clocks each | 0.39-0.52 million | 17.1-22.8 ms |
| Read it back and compare | 131,072 words, 20-22 clocks each, 12 of them for the read | 2.62-2.88 million | 114-125 ms |
| Clear SDRAM | 16,384 passes of 4 longwords, 18-20 clocks each | 0.29-0.33 million | 13-14 ms |
| Compare `$000400-$0007FF` | 512 words from the cartridge, about 25 clocks each | about 13,000 | 0.6 ms |

Source: [VRD-NOTES, 32X BIOS dump, Master boot ROM `0x01C6`-`0x0238`]. A working SDRAM passes the test about 131-148 ms after RES, and `SQER` can be posted no earlier than about 145 ms. The 68000 has read `$A15120` by about 22 ms, at least six times sooner. By this estimate:

- **`$0040` (`SQER`) is never reported.** A cartridge that fails the security check hangs at step 9 if its checksum field is non-zero. If it is zero, the cartridge reaches your code with a clean verdict and no `M_OK`.
- **`$0080` (`SDER`) is reported only for a fault near the top of SDRAM.** The read-back works down from the top. A fault in its first words can be posted from about 17 ms, while the 68000 may still be clearing. Even if the write pass is at its fastest and the 68000 at its slowest, that covers only the first 5,000 or so words, about the top 10 KB. A fault anywhere else hangs the console the same way.

The arithmetic leaves out DRAM refresh, which holds FEN and the SDRAM for short spells, and the Slave, which polls a communication port on the bus it shares with the Master. Both can only make the Master slower. A game that wants to show an error screen should not count on these two codes. It can give its own wait for `M_OK` a time limit and look at `$A15120` for `SQER` and `SDER` while it waits.

The wait at step 9 has a smaller flaw of its own. It treats a sum of exactly `$0000` as "not posted yet", so a cartridge whose words add up to 0 hangs there if its header field is wrong and not zero, instead of reporting `$0020`.

### The verdict

The initial program reports its result in the carry flag and `d0` <span class="tag manual">manual</span> [32X-HWM §5.2, sample program]. Two separate rules follow:

- **Your entry code must be at `$000800`.** The initial program does not jump to an address taken from a header. It ends by branching to `$000800`, the byte after its own last byte, and whatever is there runs. Aerobiz Ultimate's first 32X build took the jump to `$8806BC` near `$0004C0` for the hand-off to the game. That jump is the program moving itself into the fixed window, so the build put its own code on top of the work-RAM clear at `$0006BC`, and it never booted [AU-NOTES, security block].
- **That code should check the carry flag first, then `d0`.** The verdict is only advice. A console that passes every check boots just as well if you ignore it. On one that fails, your code carries on as if the 32X were ready, and its first wait for `M_OK` may never end. Sega's sample opens with `bcs`, then tests bit 15 of `d0` [32X-TIA1 p.1].

| Carry | `d0` | Meaning |
|-------|------|---------|
| 0 | `$0000` | Cold start, all checks passed |
| 0 | `$8000` | Restart after the reset button. Nothing was initialised |
| 1 | `$0001` | No `MARS` ID: no 32X attached |
| 1 | `$0002` | The Mega Drive and the 32X disagree about PAL/NTSC |
| 1 | `$0020` | Checksum mismatch |
| 1 | `$0040` | Security check failed (`SQER`) |
| 1 | `$0080` | SDRAM test failed (`SDER`) |

The codes come from reading the code [VRD-NOTES, ROM]. What a game does with them is its own choice. After Burner Complete and Motocross Championship stop for good on any error, with a branch to itself at `$000800`, and Star Wars Arcade jumps to a loop that does the same. Knuckles' Chaotix treats a bad checksum (bit 5) on its own path and checks for `MARS` again for the rest. Mortal Kombat II puts a `JMP` at `$000800` instead. It does not affect the flags, and the first instruction at the other end is the same branch-to-itself on carry [AB32X; MCX; SWA; CHAOTIX; MK2, 68000 code at `$000800`, `$00878C`].

## The Master SH-2 boot ROM

Once released, the Master:

1. Masks all interrupts, zeroes its registers and programs the bus controller for the 32X's memory.
2. Puts the SDRAM into its operating mode, turns the cache on after clearing it, and takes itself out of standby.
3. Tests all 256 KB of SDRAM by writing a counting pattern and reading it back. On failure it writes `SDER` to `$A15120` (`0x20004020`) and stops. On success it clears SDRAM to zero.
4. Checks the cartridge-present bit. With no cartridge it follows the Mega-CD path described [below](#booting-from-a-mega-cd).
5. Compares cartridge `$000400-$0007FF` with a copy it holds of the same code. On a mismatch it writes `SQER` to `$A15120`, sets FM to take the 32X VDP away from the 68000, and stops.
6. Computes the checksum (if the header asks for one) and writes it to `$A15128`.
7. Copies your SH-2 program from the cartridge to SDRAM as the user header describes, sets its vector base register, writes `M_OK` to `$A15120` and jumps to your Master entry point.

Sources: [VRD-NOTES, 32X BIOS dump; 32X-HWM §5.1].

The boot ROM does not wait for anything after writing `M_OK`. Your Master code starts at once, in parallel with the end of the 68000's initial program.

## The Slave SH-2 boot ROM

The Slave sets up its bus controller and cache the same way, then polls `$A15120` until it reads `M_OK`. Only then does it write `S_OK` to `$A15124` and jump to the Slave entry point in the user header. Waiting for the Master guarantees that the Slave's code is already in SDRAM when it starts [VRD-NOTES, 32X BIOS dump].

Two consequences:

- **Do not let your Master code overwrite `$A15120` early.** If the Master replaces `M_OK` before the Slave has read it, the Slave waits forever. Leave it to the 68000, which only changes it after it has seen both `M_OK` and `S_OK` (see [the handshake](#the-handshake-into-your-code)).
- The Slave never computes the checksum. Its boot ROM has no code for it, and the manual's flowchart for the Slave has no such step. The text transcriptions of the manual wrongly add one [32X-HWM §5.1 Figure 5.3 p.83; VRD-NOTES, 32X BIOS dump; [discrepancy #6](../appendices/discrepancies.md)].

## The security check

The "security" is a byte-for-byte comparison. The Master compares the 1024 bytes at cartridge `$000400-$0007FF` with a copy stored inside its boot ROM [VRD-NOTES, 32X BIOS dump]. There is no signature or cryptography. A cartridge passes if it contains Sega's initial program unchanged.

The first 16 bytes of the initial program, `$0003F0-$0003FF`, are not part of the comparison. They still do work on the 68000: they set up an address register and clear `$A15128`, the word the 68000 later watches for the checksum. Keep them as Sega wrote them. Sega's own Gnu Sierra sample skips them: its cartridge reset vector and its jump-table reset entry both point at `$000400` [GNU-SIERRA, ROM `$000004`, `$000200`]. Its checksum field is 0, so the 68000 never waits on `$A15128` and the missing clear does no harm there. The address register is still read once, at `$0007DA`, before the end of the program reloads most registers. If the check fails, the Master takes the 32X VDP away from the 68000 and stops, so the 68000 can no longer use the 32X display <span class="tag manual">manual</span> [32X-HWM §5.2].

## The user header

The Master reads the 48 bytes at cartridge `$0003C0` to learn what to load and where to start each SH-2 [32X-HWM §5.1]:

| Offset | Size | Field | What the boot ROM does with it |
|--------|------|-------|--------------------------------|
| `$3C0` | 16 bytes | Module name, `MARS CHECK MODE ` in Sega's sample | Nothing |
| `$3D0` | long | Version | Nothing |
| `$3D4` | long | Source: cartridge offset of the SH-2 program | Reads from cartridge offset + `0x22000000` |
| `$3D8` | long | Destination: offset into SDRAM | Writes to `0x06000000` + offset |
| `$3DC` | long | Size in bytes | Copies this many bytes, four at a time |
| `$3E0` | long | Master entry point | Master jumps here |
| `$3E4` | long | Slave entry point | Slave jumps here |
| `$3E8` | long | Master vector base | Loaded into the Master's VBR |
| `$3EC` | long | Slave vector base | Loaded into the Slave's VBR |

All addresses and the size must be multiples of four. The copy works in longwords and the SH-2 raises an address error otherwise <span class="tag manual">manual</span> [32X-HWM §5.1]. The entry points and vector bases are SH-2 addresses, normally in SDRAM (`0x06xxxxxx`).

The Virtua Racing Deluxe image the project works from copies 48 KB from cartridge `$020000` to the start of SDRAM. Its Master starts at `0x06000280` and its Slave at `0x06000288`, with vector tables at `0x06000000` and `0x06000140`. That image is not the retail original. The header sits in its first 2 KB, the part the book relies on, and none of the project's tools writes there, but no retail dump is at hand to confirm these values [VRD-NOTES, ROM `$0003C0`]. Mortal Kombat II copies 32,276 bytes from `$000978`. The 376 bytes between the end of the initial program and that address hold a six-byte `JMP` into the game's 68000 code, two bytes of padding, and a table of 92 cartridge addresses in SH-2 form (`0x02xxxxxx`), which the Master's code reads in place from the cartridge [MK2, ROM `$000800-$000977`; SH-2 code at `0x060006D0`]. The game packs its two vector tables back to back at `0x06000000` and `0x06000120`. That is 72 vectors each, which is enough: the highest vector the 32X uses is 71, for VRES [MK2, ROM `$3C0`]. After Burner Complete copies 106,496 bytes from `$053000`, with the Slave's table and code first at `0x06000000` and the Master's table at `0x06002000` [AB32X, ROM `$3C0`].

Only some entries of your vector tables matter. The boot ROM sets the stack pointers itself, so the reset PC and SP entries are never read. Mortal Kombat II's hold leftover values (`0x0C040000`). Its error vectors (illegal instruction, address errors) point into cartridge ROM at `$3FB000`, which is erased in the retail cartridge. They were presumably aimed at a debugger on the development hardware. On a console, a crash there jumps into `$FFFF` words, which are themselves illegal instructions [MK2, SH-2 vector tables; ROM `$3FB000`]. After Burner Complete fills the same entries with care. Its reset entries hold the real entry points and stacks. Each of the Master's error vectors leads to a one-instruction loop of its own, so a debugger that stops the CPU can tell from the program counter which exception happened. The Slave's illegal-instruction and address-error vectors restart its start-up code instead [AB32X, SH-2 vector tables; code at `0x06003878`-`0x0600388A`, `0x060002D8`].

The copy is limited to what fits in SDRAM: 256 KB, less what the stacks need (see [below](#what-your-code-starts-with)). Anything else your SH-2 code needs, it loads itself, from the cartridge at `0x02000000` or through the [FIFO](fifo.md).

## The checksum

On a plain Mega Drive, checking the header checksum is up to the game. On the 32X the boot sequence checks it for you, and the work is split. The Master SH-2 adds up the cartridge as 16-bit words from `$000200` to the ROM end address in the header at `$0001A4`, and posts the 16-bit sum at `$A15128`. The 68000 initial program compares that sum with the header's checksum field at `$00018E` [VRD-NOTES, 32X BIOS dump; VRD-NOTES, ROM].

- A checksum field of zero skips the check.
- The ROM end address has to be right: the Master adds up exactly what it says.
- A mismatch only sets error `$0020`. What happens next is up to your code at `$000800`.

How to compute the value for your own ROM is in [Mega Drive ROM header and checksum](../howto/md-header.md).

## What your code starts with

### 68000, at `$880800`

| | State |
|---|---|
| Status register | `$2700`: supervisor mode, all interrupts masked |
| Stack pointer | The value stored in the cartridge's first vector, the longword at cartridge offset 0 (read through `$880000`). User stack pointer is 0 |
| Registers | `d0` holds the verdict. `d3-d7` and `a0-a6` are 0. `d1` and `d2` are left over |
| Work RAM | All zero |
| Mega Drive VDP | Display off, 320-pixel mode, VRAM, CRAM and VSRAM cleared |
| Z80 | Held in reset, bus released |
| PSG | All channels silent |
| 32X | FM = 0 (68000 owns the 32X VDP). Bank 0 at `$900000`. RV = 0. Bitmap mode blank. Both frame buffers and the palette cleared. PWM off |

### Each SH-2, at its entry point

| | State |
|---|---|
| Status register | `0xF0`: all interrupts masked |
| Stack pointer | From the boot ROM's vector table: `0x06040000` for the Master (the top of SDRAM), `0x0603F800` for the Slave, 2 KB lower |
| VBR | From the user header |
| GBR | `0x20004000`, the system registers |
| Cache | On, freshly cleared, four-way (no on-chip RAM) |
| Bus controller | Set up for the 32X. The manual forbids applications from touching it [32X-HWM §5.3] |
| SDRAM | Cleared by the Master, then your program copied in |
| Free-running timer | Not set up. It must be initialised before interrupts are used [32X-TI item 10; 32X-SUP2] |

Sources: [VRD-NOTES, ROM; VRD-NOTES, 32X BIOS dump].

The two default stacks are close together. The Master's starts at the top of SDRAM and the Slave's 2 KB below it, and both grow down. So the Master has only 2 KB of stack before it starts writing over the Slave's, and nothing stops it or reports it when it does. If your Master code needs more, for deep calls, large local buffers or nested interrupts, move one of the two stacks before doing real work. Mortal Kombat II, for example, puts the Slave's at `0x0603F000`, which leaves the Master 4 KB [MK2, SH-2 code at `0x0600513C`]. The Slave's stack in turn grows down into the SDRAM below `0x0603F800`, so a program copied into the top 4 KB of SDRAM will be overwritten by its own stacks unless your code moves them first.

## The handshake into your code

The last step is a handshake through the communication ports. The 68000 waits until `$A15120` reads `M_OK` and `$A15124` reads `S_OK`, then clears them to tell the SH-2s to go ahead. The manual says only that the SH-2 side waits for the clear. It does not say which word each SH-2 should watch [32X-HWM §5.1], and the code that exists answers in different ways:

| Code | 68000, after seeing both words | Master waits for | Slave waits for |
|------|--------------------------------|------------------|-----------------|
| Sega's sample | Clears `$A15120` and `$A15124` | `$A15120` = 0, then `SLAV` in `$A15128` | Not in the sample |
| Mortal Kombat II | Clears `$A15120` and `$A15124` | `$A15120` = 0, then `SLAV` in `$A15128` | `$A15120` = 0, then writes `SLAV` to `$A15128` |
| After Burner Complete | Clears `$A15124`, then `$A15120` | `$A15120` = 0 | `$A15120` = 0 |
| Star Wars Arcade | Writes `SHGO` into `$A15120`, then waits for `$A15120` to read 0 | `SHGO`, then clears `$A15120-$A15122` | Upper half of `$A15120` = 0, then clears `$A15122-$A15123` |

Sources: [32X-TIA1 pp.2-4; MK2, SH-2 code at `0x06000296`, `0x06005130`, 68000 code at `$008BC4`; AB32X, SH-2 code at `0x0600215E`, `0x0600022E`, 68000 code at `$000808`-`$000828`; SWA, SH-2 code at `0x06000DE4`-`0x06000E0E`, `0x06000734`-`0x0600074E`, 68000 code at `$000820`-`$000846`].

So in the code that shows both CPUs, no SH-2 watches its own word. Both watch `$A15120`, and clearing `M_OK` is what releases both of them. Clearing `S_OK` as well only tidies up. Sega's sample shows the Master's side alone; Mortal Kombat II supplies the Slave's half, with the Slave posting `SLAV` so that the Master knows it has started. Star Wars Arcade reverses the direction: the 68000 gives the go-ahead with `SHGO` and then waits until both SH-2s have finished their own set-up. The Master clears `$A15120-$A15122` with a word write to `$A15120` and a byte write to `$A15122`. The Slave clears `$A15122-$A15123` with a word write to `$A15122`. The longword reads 0 only after both have done so. Each scheme works. What matters is that your 68000 code and your SH-2 code agree. A Slave that waits for `$A15124` to clear hangs if the 68000 only clears `$A15120` and nothing else clears `$A15124` for it.

The boot flowchart calls these words "comm 0" and "comm 4". Those are byte offsets from `$A15120`, not register numbers, so `S_OK` is at `$A15124`, the third communication word. The toolchains use the same convention and name the eight words `COMM0`, `COMM2` and so on up to `COMM14` [MARSDEV, 32x-skeleton mars.h]. Sega's register tables number the same words COMM0 to COMM7 instead; see [the two naming schemes](communication.md#addresses-and-names). Aerobiz Ultimate's first build waited on `$A15128` and hung [AU-NOTES, security block].

Plan your own use of the communication words around the boot's: `COMM0` and `COMM4` carry the handshake and `COMM8` the checksum. A command protocol that reuses one of those words can be mistaken for the handshake. Homebrew has hit exactly this: a slave command written to `COMM4` let the Slave start before it should, and it wrote over the VDP registers [S32X-SKILL, architecture]. See [68000 and SH-2 communication](communication.md).

## Pressing reset

The Mega Drive's reset button does not reset the SH-2s. Each one gets a VRES interrupt at level 14 instead, and must acknowledge it by writing to `0x20004014`, or no further VRES interrupts arrive <span class="tag manual">manual</span> [32X-HWM §3.2.2; 32X-OV p.33]. The 68000 does restart. Three complications follow:

- **The 68000 may find the 32X half set up.** The 32X's registers are not reset with the 68000, so on the way back in, the code has to check what state the adapter is in. Sega's bulletin gives a sample that every game is expected to follow, and After Burner Complete's reset path makes the same checks in the same order: bit 15 of the verdict, then ADEN, then RES [32X-TIA1, 68000 sample; AB32X, 68000 code at `$00082E`-`$000866`]:
  - ADEN is 0: enable the adapter again through a work-RAM stub, then jump back into the initial program at `$8806E4`. That point is just after the work RAM clear, so the SH-2s are reset and restarted.
  - ADEN is 1 but RES is 0: jump back into the initial program at `$8806E4` in the same way.
  - ADEN and RES are both 1: a "hot start". Skip the 32X setup and restart the game.
- **RV = 1 during reset can hang the machine.** If the reset arrives while RV is 1, the console may not restart cleanly. On production units, the Master's VRES handler checks RV and, if it is set, resets the whole 32X. Sega's text says the watchdog timer's output does the reset, but its sample code sets the free-running timer's FTOB output instead, and so do Star Wars Arcade and After Burner Complete [32X-TIA1 pp.1, 4, 6; SWA, SH-2 code at `0x060005B2`; AB32X, SH-2 code at `0x060022B4`]. The service manual's schematic settles it: the Master's FTOB drives the 32X's reset line, and the watchdog output is not connected <span class="tag manual">manual</span> [32X-SVC §7-3, §7-4; [discrepancy 22](../appendices/discrepancies.md)]. See [Hardware bugs and workarounds](bugs.md).
- **The 68000 cannot see when the SH-2s have finished their own reset.** On a hot start the 68000 skips the 32X setup, but the SH-2s are still inside their VRES handlers, and nothing in the boot protocol tells the 68000 when they are done. Some games add a signal of their own. When RV is 0, After Burner Complete's Master does more than the sample before it restarts: it blanks the 32X layer, clears `$A15120`-`$A15123`, and writes the ASCII word `VRES` into `$A1512C`-`$A1512F`. The game's 68000 reset code, on a hot start, checks `$A1512C` for that word up to 4,096 times and restarts the game as soon as it appears. If it never does, it takes a slower path: it raises CMD on both SH-2s and waits for `M_OK` and `S_OK` in the ports before going on [AB32X, SH-2 code at `0x06002260`-`0x06002296`; 68000 code at `$880840`-`$880908`]. Space Harrier, from the same studio, and Virtua Racing Deluxe post the same word, and their 68000 code waits for it with the same loop; no other game in the sources does ([The `VRES` handshake](../appendices/sample-code.md#the-vres-handshake-rutubo-games-and-virtua-racing-deluxe)). Star Wars Arcade reuses the boot's own words: its Master's VRES handler writes `M_OK` again, and its Slave's waits for that and then writes `S_OK` [SWA, SH-2 code at `0x060005A8`, `0x0600060C`-`0x0600061A`]. A marker like this turns "the SH-2s have probably finished their reset" into something the 68000 can check.

With the adapter on, the 68000's reset vector in the vector ROM points to `$880200`, the first entry of the cartridge's jump table [VRD-NOTES, 32X BIOS dump]. After Burner Complete points that entry at its reset path, `$880838`. Star Wars Arcade points it at `$880820`, its normal start-up, which simply repeats the handshake [AB32X; SWA, jump table at `$000200`].

### The warm-start exit

The initial program has its own restart test (step 4 of [Before the switch](#before-the-switch)), but nothing found so far shows how the 68000 could reach it in a state where it passes. The test only passes when ADEN = 1, and it runs before the program moves to the `$88xxxx` window, so it would be running from the cartridge's plain address, `$0003F0`. With ADEN = 1, the 68000 sees the cartridge there only while RV = 1 [32X-HWM §3.1 pp.13-14]. Its reset vector then comes from the vector ROM, which sends it to `$880200`, not to `$0003F0` [VRD-NOTES, 32X BIOS dump]. None of the 14 undamaged 32X dumps in the project has a jump-table entry for `$8803F0`. Three of Sega's development samples point their reset entry at the initial program's low address: Egypt with `JMP $0003F0`, and Gnu Sierra and the ECCO demo with `JMP $000400`. While ADEN = 1 and RV = 0, the manual maps nothing at either address [EGYPT; GNU-SIERRA; ECCO, ROM `$000200`]. The retail games send reset to code of their own. Some of them, like Sega's sample, re-enter the initial program halfway, at `$8806E4`. The homebrew start-up code in the bibliography points its reset entry at `$880800`, its own start-up code, and never goes back into the initial program at all. D32XR goes further and rebuilds the whole hand-over on reset. In its SH-2 VRES code the Slave posts `S_OK`, and the Master copies the program into SDRAM again and posts `M_OK`. Its 68000 code at `$880800` then waits for both words as it does at power-on [MARSDEV, 32x-skeleton mars_start.s, md_start.s; D32XR, crt0.s, src-md/crt0.s].

For the exit to work, the 68000 has to fetch everything from the restart test at `$000420` to the branch at `$0007FA`, and ADEN has to read 1 at `$00042C`. The exit's branches are relative to the program counter, so they return to `$000800` from a run at `$0003F0` and to `$880800` from a run at `$8803F0`. Under the manual's memory map [32X-HWM §3.1 pp.13-14]:

| ADEN | RV | Running at | Result |
|------|----|------------|--------|
| 0 | 0 | `$0003F0` | The test fails at `$00042C` and the program takes the normal cold path |
| 1 | 0 | `$0003F0` | Nothing is mapped there, so the program cannot run |
| 1 | 0 | `$8803F0` | The test passes, but the write to `$A15106` sets RV and hides the window. The branch at `$0007FA`, two instructions later, would be fetched from an address that holds nothing |
| 1 | 1 | `$0003F0` | Works. The cartridge is at its plain address, the RV write changes nothing, and the branch lands on `$000800` |
| 1 | 1 | `$8803F0` | Nothing is mapped there while RV = 1 |

Only the fourth row works, and the manual's map gives the 68000 no way into it. A reset reads its vectors from the vector ROM, which sends the CPU to `$880200`, a window that RV = 1 hides, and no jump-table entry can help for the same reason. The exit would fit one case the map rules out: a reset while RV = 1 that took its vectors from the cartridge rather than from the vector ROM. That would start the 68000 at the cartridge's `$0003F0` with ADEN and RV both 1. A reset while RV = 1 is exactly the situation Sega's bulletin warns about [32X-TIA1 p.1]. But the manual's figure shows the vector ROM at `$000000` whatever RV holds, and nothing in the project tests it.

Sega nonetheless expects the exit to be taken. Its bulletin says that the initial program runs again when the console is reset, and that it goes straight to the game because the Mega Drive's I/O chip is not reset. Its 68000 sample tests bit 15 of `d0` straight after the initial program [32X-TIA1 p.1]. After Burner Complete and Mortal Kombat II test it too, and send it to the same handler as their jump-table reset entry, so they are covered whichever way a reset arrives [AB32X, 68000 code at `$00082E`; MK2, 68000 code at `$008796`, `$0087FC`]. Whether a console ever takes the exit is one of the [open questions](#open-questions).

## Booting from a Mega-CD

With no cartridge inserted, the Master skips the security check, the checksum and the cartridge copy. It waits for the 68000 to write `_CD_` to `$A15120`, takes the 32X VDP, and reads a small header at frame buffer offset `$18`. That header gives the destination, size, entry point and vector base, and the Master copies the program from the frame buffer into SDRAM. The Slave waits for `_CD_` and then for `M_OK`, and reads its entry point and vector base from the same header. In other words, a 32X CD game's 68000 side delivers the SH-2 program through the frame buffer [VRD-NOTES, 32X BIOS dump]. The manual's boot flowcharts show the branch: the Master waits for `_CD_` and loads the initial data, and the Slave waits for `_CD_` and then `M_OK` [32X-HWM §5.1 Figures 5.2-5.3 pp.82-83]. They do not say where the data comes from, and no manual in the bibliography describes the frame buffer header.

## Open questions

- Whether reset clears ADEN on hardware, and so whether the 68000 restarts through the cartridge vectors (`$0003F0`) or the vector ROM (`$880200`). Sega's sample is written to cope with both.
- How the initial program's warm-start exit is ever reached. Its test needs ADEN = 1 while the code runs at `$0003F0`, which the manual's memory map allows only with RV = 1, and no ROM in the project enters it that way. See [The warm-start exit](#the-warm-start-exit).
- On its warm-start path the initial program writes 1 to `$A15106` before returning. Bit 0 of that register is RV, and the manuals do not explain why it would be set there. It keeps `$000800` visible to code running at its low address, but it also hides the `$88xxxx` and `$90xxxx` windows that the reset handlers of Sega's sample and Mortal Kombat II jump into next.

The three questions above, and the [DMA chapter's](../megadrive/vdp-dma.md#open-questions) question of whether `$880000` really disappears while RV = 1, can all be settled in one session on a console. Press reset with a test ROM that records which path the 68000 takes (the cartridge's own vector, the jump-table entry, or the initial program's `$8000` exit) and the values of ADEN and RV on the way in. Do it twice, once with RV = 0 and once with RV = 1 at the moment of the reset. In the same session, set RV from code in work RAM and read a known byte through `$880000`. See [Testing on real hardware](../howto/real-hardware.md#start-up-and-the-cartridge).

- How long the whole sequence takes, from power-on to `M_OK`. It has not been measured. The estimate in [A race in the error checks](#a-race-in-the-error-checks) puts the 68000's read of `$A15120` at about 17.5-22 ms after RES and the Master's earliest `SQER` at about 145 ms, so `$0040` should never be reported. A cartridge with a deliberately altered initial program would test this: by the estimate, it hangs instead of returning `$0040`.

## Sources

- [32X-HWM](../appendices/bibliography.md#32x-hwm): §3.1 pp.13-14 memory map, §3.2.1-3.2.2, §4.4 pp.77-78 access timing, §5.1 boot ROM and user header, §5.2 security and initial program, §5.3 restrictions
- [32X-TIA1](../appendices/bibliography.md#32x-tia1): VRES and RV, 68000 reset sample pp.1-3, Master SH-2 start-up sample p.4
- [32X-SVC](../appendices/bibliography.md#32x-svc): §7-3, §7-4 schematics, the FTOB reset path
- [MK2](../appendices/bibliography.md#mk2): ROM `$3C0`, `$800-$977`, SH-2 vector tables, start-up code and stacks, 68000 code at `$000800`, `$00878C`-`$0087FC`, `$008BC4`
- [SWA](../appendices/bibliography.md#swa): 68000 code at `$000800`, jump table, boot handshake on both SH-2s, VRES handlers
- [CHAOTIX](../appendices/bibliography.md#chaotix), [MCX](../appendices/bibliography.md#mcx): 68000 code at `$000800`, jump table, boot handshake
- [MARS-CHECK](../appendices/bibliography.md#mars-check), [RLT](../appendices/bibliography.md#rlt), [SOJ](../appendices/bibliography.md#soj), [TEXTURE](../appendices/bibliography.md#texture): initial program
- [MARSDEV](../appendices/bibliography.md#marsdev): 32x-skeleton `mars_start.s` (cartridge vectors, jump table) and `md_start.s` (initial program, 68000 start-up)
- [D32XR](../appendices/bibliography.md#d32xr): `crt0.s` (cartridge vectors, jump table, SH-2 VRES code) and `src-md/crt0.s` (68000 start-up)
- [AB-DISASM](../appendices/bibliography.md#ab-disasm): Sega's plain Mega Drive start-up code at ROM `$000200`
- [SH-PM](../appendices/bibliography.md#sh-pm): §7.7.5, branch timing; [SH7604](../appendices/bibliography.md#sh7604): §7.5.4, cache-through reads of SDRAM
- [EGYPT](../appendices/bibliography.md#egypt), [GNU-SIERRA](../appendices/bibliography.md#gnu-sierra), [ECCO](../appendices/bibliography.md#ecco): initial program, reset vector and jump table
- [AB32X](../appendices/bibliography.md#ab32x): ROM `$3C0`, SH-2 vector tables, start-up code, VRES handler at `0x06002260`; 68000 start-up and reset code at `$000800`-`$000908`
- [32X-OV](../appendices/bibliography.md#32x-ov): interrupt levels
- [32X-TI](../appendices/bibliography.md#32x-ti): item 10
- [32X-SUP2](../appendices/bibliography.md#32x-sup2): SH-2 interrupt limitations
- [MD-SWM](../appendices/bibliography.md#md-swm): TMSS security register
- [VRD-NOTES](../appendices/bibliography.md#vrd-notes): 32X BIOS dumps; the project's ROM, first 2 KB only (header, user header, jump table, initial program)
- [AU-NOTES](../appendices/bibliography.md#au-notes): security block, first boot
