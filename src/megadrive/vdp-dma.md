# DMA

The VDP can move data into its own memories without the 68000 copying it word by word. That is DMA (direct memory access). There are three kinds: a copy from 68000 memory into VRAM, CRAM or VSRAM, a fill of VRAM with one value, and a copy from one part of VRAM to another. This chapter covers how each is set up, how much each can move per frame, the hardware's traps, and how shipped games organise their DMA. A last section covers DMA on the 32X, where the cartridge is not where the VDP expects it.

## The three kinds at a glance

| | 68000 memory → VDP | VRAM fill | VRAM copy |
|---|---|---|---|
| Register 23 bits 7-6 | `0x` | `10` | `11` |
| Source | ROM or work RAM | One data word | VRAM |
| Destination | VRAM, CRAM or VSRAM | VRAM | VRAM |
| Length counts | Words | Bytes | Bytes |
| Starts when | The command's second word is written | A word is written to the data port | The command's second word is written |
| The 68000 | Stopped until the end | Runs, but may not touch the VDP | Runs, but may not touch the VDP |

Sources: [MD-SWM §2.7; GENVDP §11]. During a fill or copy, the 68000 may still read the status register and the H/V counter and write to the PSG; anything else may corrupt the operation [MD-SWM §2.7]. GENVDP found that writing to the ports during a fill corrupts the registers and VRAM [GENVDP §11]. Wait for the status register's DMA bit to clear first.

## Setting one up

Every DMA follows the same steps [MD-SWM §2.7, setting of DMA]:

1. Set M1 (register 1 bit 4) to allow DMA.
2. Set the auto-increment (register 15). It is applied to the destination after every unit, exactly as for CPU writes.
3. Write the length to registers 19 (low byte) and 20 (high byte).
4. Write the source and the mode to registers 21, 22 and 23.
5. Write a memory command with CD5 set (`$80` in the command's low byte). For a fill, then write the fill value to the data port.
6. When the DMA is finished, clear M1 again.

Sega's manual says to keep M1 at 1 only while a DMA runs, and does not guarantee behaviour otherwise <span class="tag manual">manual</span> [MD-SWM §2.7]. It is also good protection: with M1 at 0, a stray command with CD5 set does nothing.

A length of 0 does not mean "nothing": it means `$10000` words. notaz's console test runs a second DMA without reloading the length registers, which the first left at 0, and the last of `$10000` words lands at VRAM `$FFFE` [TESTPICO, t_dma_zero_wrap]. PicoDrive counts it the same way <span class="tag emulator">emulator</span> [PICODRIVE, pico/videoport.c]. GENVDP's `$FFFF` is wrong ([discrepancy 37](../appendices/discrepancies.md)) [GENVDP §11]. Never start a DMA with a length of 0.

The length and source registers are counters that the DMA runs down, not settings it copies. Each step adds 1 to the word address in registers 21-22 and subtracts 1 from the length in registers 19-20, and the DMA ends when the length reaches 0. Register 23 is never changed. Nemesis describes this, and his VDP test ROM checks it on a console by leaving out one register write and seeing where the next DMA starts [GENDEV-VDPINT, post of 13 September 2013; test ROM, TestDMATransferSourceRegUpdate, TestDMATransferLengthRegUpdate, TestDMAFillSourceRegUpdate]. PicoDrive does the same <span class="tag emulator">emulator</span> [PICODRIVE, pico/videoport.c]. So after a DMA the length registers hold 0 and the source registers point just past the data. A fill or a copy also advances the source registers, although it does not read them. Writing only registers 19-20 and a new command starts a second transfer where the first stopped. Shipped code should still write all five registers for every DMA, so that no routine depends on what ran before it.

## From 68000 memory

The source can be cartridge ROM (`$000000-$3FFFFF`) or work RAM (`$FF0000-$FFFFFF`) [MD-SWM §2.7]. Registers 21-23 hold the source address divided by 2, a word address:

| Register | Holds |
|----------|-------|
| 21 | Source bits 8-1 |
| 22 | Source bits 16-9 |
| 23 | Bit 7 = 0, then source bits 23-17 (bit 6 is source bit 23) |

Source: [MD-SWM §2.7; MD-TB, address checker §5.1]. For a work-RAM source, register 23 is therefore `$7F` [MD-TB, address checker §5.1]. The register value for any source is `source >> 17`, masked to 7 bits.

Each step reads one word from the source and writes it to the destination, then adds 2 to the source and register 15 to the destination. A VRAM destination swaps the bytes if the address is odd, like a CPU write [GENVDP §11]. The 68000 is stopped for the whole transfer. The Z80 keeps running, unless it tries to reach the 68000's side of the bus [MD-SWM §2.7].

A complete transfer of a block of words from ROM to VRAM, with the guards from the sections below: interrupts masked, the Z80 bus held, the command's second word read from RAM, a wait for the end of the DMA, and M1 cleared again:

```asm
; In:  d0.l = source (ROM or work RAM, even), d1.w = length in words (not 0),
;      d2.w = VRAM destination (even), a4 = $C00004
; Needs: Reg1Copy, a byte in RAM holding register 1's current value with M1 = 0;
;        DmaCmd, a longword in work RAM.
; Changes: d0-d3, a0. SR is saved and restored.
DmaToVram:
        move.w  sr,-(sp)
        ori.w   #$0700,sr            ; no interrupts until the end
        lea     $A11100,a0
        move.w  #$0100,(a0)          ; request the Z80 bus
.z80:   btst    #0,(a0)
        bne.s   .z80                 ; 0 = granted
.idle:  move.w  (a4),d3
        btst    #1,d3                ; status DMA bit: wait for an earlier DMA
        bne.s   .idle
        move.w  #$8100,d3
        move.b  Reg1Copy,d3
        bset    #4,d3                ; M1 on, other bits as they are
        move.w  d3,(a4)
        move.w  #$8F02,(a4)          ; increment 2
        move.w  #$9300,d3
        move.b  d1,d3                ; length low
        move.w  d3,(a4)
        lsr.w   #8,d1
        ori.w   #$9400,d1            ; length high
        move.w  d1,(a4)
        lsr.l   #1,d0                ; source in words
        move.w  #$9500,d3
        move.b  d0,d3                ; source bits 8-1
        move.w  d3,(a4)
        lsr.l   #8,d0
        move.w  #$9600,d3
        move.b  d0,d3                ; source bits 16-9
        move.w  d3,(a4)
        lsr.l   #8,d0
        andi.w  #$7F,d0
        ori.w   #$9700,d0            ; source bits 23-17, mode 0
        move.w  d0,(a4)
        andi.l  #$0000FFFF,d2        ; command = $40000080 + address bits
        lsl.l   #2,d2                ; A15-A14 move up into bits 17-16
        lsr.w   #2,d2                ; A13-A0 back down to bits 13-0
        swap    d2
        ori.l   #$40000080,d2        ; VRAM write, CD5 = 1
        move.l  d2,DmaCmd
        move.w  DmaCmd,(a4)          ; first word
        move.w  DmaCmd+2,(a4)        ; second word, read from RAM: the DMA runs now
.busy:  move.w  (a4),d3
        btst    #1,d3                ; wait until the DMA bit clears
        bne.s   .busy
        move.w  #$8100,d3
        move.b  Reg1Copy,d3          ; M1 off again
        move.w  d3,(a4)
        move.w  #$0000,(a0)          ; release the Z80
        move.w  (sp)+,sr
        rts
```

The command is built as in the [VDP overview](vdp.md). For a source in work RAM, add the first-word rewrite described next after the DMA bit clears. For CRAM or VSRAM, change `$40000080` to `$C0000080` or `$40000090`.

### Three rules when the source is ROM or RAM

**ROM source: the last write must come from RAM.** Sega warns that a DMA from ROM sometimes fails unless the command's second word is written as a word, and fetched by an instruction executing from work RAM or reading its operand from work RAM <span class="tag manual">manual</span> [MD-SWM §2.7; MD-REF, DMA ROM to VRAM]. GENVDP describes the failure as a lock-up [GENVDP §11]. The two usual answers:

- Keep the command in RAM and write its second word with `move.w (ram),(a4)`.
- Run the two writes themselves from RAM. Aerobiz copies a 10-byte routine (two `move.w` from its variables to the control port, then `rts`) to `$FFF000` at boot. Every DMA in the game, from ROM or RAM, ends with `jsr $FFF000` [AB-DISASM, section_000200.asm `$34E`, ConfigVDPDMA.asm].

**RAM source: rewrite the first word afterwards.** For DMA from work RAM to VRAM, CRAM or VSRAM, Sega's bulletin says to rewrite the first word of the data by hand once the DMA has finished <span class="tag manual">manual</span> [MD-TB, addendum 4 §1]. Aerobiz does this. After the DMA it tests one bit of the source address, bit 22 (`$400000`), and if it is set, it clears CD5 in the same command and writes the first word again with the CPU [AB-DISASM, ConfigVDPDMA.asm, BulkCopyVDP.asm]. One bit is enough because a DMA source can only be ROM at `$000000-$3FFFFF`, where bit 22 is always clear, or work RAM at `$FF0000-$FFFFFF`, where it is always set [MD-SWM §2.7]. Other addresses with bit 22 set are never DMA sources.

**Both: hold the Z80 bus.** The same bulletin asks for a Z80 bus request around every DMA from 68000 memory, so the Z80 cannot try to reach the 68000's bus during the transfer [MD-TB, addendum 4 §1]. See [Z80 bus control](z80.md).

### Do not cross a boundary

Only registers 21 and 22 count, and register 23 never changes (see [Setting one up](#setting-one-up)). The counter therefore covers 16 bits of word address, 128 KB, and a transfer that crosses a 128 KB boundary reads the start of the same 128 KB block instead of the next one. Nemesis's test ROM checks this on a console with a 4-word DMA that starts 4 bytes before a 128 KB boundary. The last two words come from the start of the block, not from 64 KB further on, where the test data differs [GENDEV-VDPINT, post of 13 September 2013; test ROM, TestDMATransferSourceAddressWrapping]. All four emulators read for this book wrap the same way, each in its own code. Genesis Plus GX keeps register 23's bits above a 17-bit window. ares and BlastEm count only the low 16 bits of the word address <span class="tag emulator">emulator</span> [PICODRIVE, pico/videoport.c; GPGX, core/vdp_ctrl.c; ARES, ares/md/vdp/dma.cpp; BLASTEM, vdp.c].

SGDK, the open-source Mega Drive development kit, follows the same rule. Its DMA routines check whether a transfer reaches past the end of its 128 KB block and, if it does, split it into two DMAs at the boundary [SGDK, src/dma.c, `DMA_doDma` and `DMA_queueDma`]. Do the same, or align graphics in ROM so that no block straddles a 128 KB boundary.

Sega's reference sheet gives a stricter rule from a licensee's experience: a DMA should not cross a 64 KB boundary [MD-REF, DMA ROM to VRAM]. No other source supports it. The test above rules out a wrap at 64 KB, and Nemesis's counter model, PicoDrive and SGDK all let a transfer run across a 64 KB boundary inside a 128 KB block. notaz's console test tries that case. Its ROM holds a different value in every longword, and a 128 KB DMA from `$3C0014` reads on across `$3D0000` and wraps only at `$3E0000` [TESTPICO, t_dma_zero_wrap]. No shipped code read for this book tries it. A DMA from work RAM cannot tell the two rules apart, because the 64 KB of RAM repeats throughout `$E00000-$FFFFFF`, so either wrap lands on the same bytes. In logs of 5,000 emulated frames, the 68000 sides of Star Wars Arcade, Mortal Kombat II and Knuckles' Chaotix made DMAs only from RAM. Aerobiz made 150 from ROM, and all of them stayed inside one 64 KB block <span class="tag emulator">emulator</span> [SWA; MK2; CHAOTIX; AB-DISASM; PICODRIVE with a DMA log added]. The 64 KB rule is wrong ([discrepancy 13](../appendices/discrepancies.md)).

### CRAM and VSRAM

Lengths for CRAM and VSRAM count words too. Sources disagree on what happens when a DMA runs past address `$7F` <span class="tag disputed">disputed</span> ([discrepancy 38](../appendices/discrepancies.md)):

- **It wraps.** The VDP uses only the low 7 bits of the address, so the DMA carries on from address 0. Nemesis's test ROM checks this on a console for both memories: 128 words written from address 0 leave words 64-67 at addresses 0-6, and a DMA started at `$40A0` lands at `$20` [GENDEV-VDPINT, test ROM, TestDMATransferToCRAMWrapping, TestDMATransferToVSRAMWrapping]. PicoDrive does the same <span class="tag emulator">emulator</span> [PICODRIVE, pico/videoport.c]. CPU writes wrap the same way [GENVDP §8-10].
- **It stops.** GENVDP says a DMA into CRAM ends once the address passes `$7F`, that Batman & Robin needs this to show the right palettes, and that VSRAM may behave the same [GENVDP §11].

MD-SWM says nothing either way. The disagreement only matters for a DMA that runs past `$7F`, so keep every CRAM or VSRAM DMA inside `$00-$7F`. A whole palette is 64 words and fits in a single line of vertical blank [MD-SWM §2.7, transfer capacity].

## VRAM fill

A fill writes one value over a range of VRAM [MD-SWM §2.7, VRAM fill; GENVDP §11]:

1. Register 23 = `$80`. Registers 21-22 are ignored.
2. Registers 19-20 = the number of **bytes** to fill, **minus 1** (see below).
3. Register 15 = the step, usually 1.
4. Write the VRAM write command with CD5 set: `$40000080` plus the address bits.
5. Write the fill value to the data port. The fill starts now.

How the bytes land is not obvious. The word written to the data port is first stored like any other data port write: high byte at the even address, low byte at the odd one, and the address steps by register 15. Then the fill proper starts. It writes the value's **high** byte once per unit of length, each time at the current address with bit 0 flipped, and steps by register 15 after each write [GENDEV-VDPINT, post of 13 September 2013]. Nemesis's test ROM checks the result on a console. A fill of `$68AC` at `$8002` with a length of 5 and a step of 1 leaves `$68 $AC $68 $68 $68 $68` at `$8002-$8007`: six bytes, and the low byte survives only at `$8003` [GENDEV-VDPINT, test ROM, TestDMAFillToVRAMV2]. PicoDrive does the same <span class="tag emulator">emulator</span> [PICODRIVE, pico/videoport.c].

So a fill covers **one byte more than its length**: the data port write covers two bytes, and the fill then writes one byte per unit of length, the first of them over a byte the data port write already set. To fill an even number of bytes from an even address with a step of 1, set the length to the number of bytes minus 1. With an even length the pattern breaks: the last write lands one byte beyond the end and the byte before it is skipped. Use a value whose two bytes are equal, such as `$0000` or `$1111`, so that the odd byte left by the data port write is not a surprise.

GENVDP describes it differently: the low byte goes to the start address, then the high byte to the address next to it, then the address steps and the high byte is written again until the length runs out. In its example code, the length counts the high-byte writes, so the start byte is overwritten and, with a step of 1 and an odd length, the second-to-last byte of the range is never written <span class="tag disputed">disputed</span> [GENVDP §11; [discrepancy 39](../appendices/discrepancies.md)]. With a value whose two bytes are equal, that skipped byte is the only difference. The test ROM's result above rules GENVDP's order out.

Sega's initial program clears all of VRAM this way: register 23 = `$80`, a length of `$FFFF`, step 1, the command `$40000080`, then a 0 to the data port [AB-DISASM, initial program]. The data port write clears bytes 0 and 1, and the fill clears the remaining `$FFFE` bytes, so `$FFFF` covers all `$10000`.

## VRAM copy

A copy moves bytes from one VRAM address to another [MD-SWM §2.7, VRAM copy; GENVDP §11]:

1. Register 23 = `$C0`.
2. Registers 21 and 22 = the source VRAM address, low byte first. This is a byte address, not divided by 2.
3. Registers 19-20 = the number of bytes.
4. Write a command with CD5 and CD4 set and CD1-CD0 = 0: `$000000C0` plus the destination address bits. The copy starts.

It reads one byte, writes one byte, and steps the destination by register 15. Because it alternates byte by byte, a copy whose source and destination overlap may not give the expected result [MD-SWM §2.7]. It runs at half the rate of a fill. Aerobiz uses one routine for all three kinds: a small selector sets register 23 to `$80` or `$C0`, or builds a 68000 source, and the rest of the code is shared [AB-DISASM, SelectVDPInit.asm, ConfigVDPColors.asm, ConfigVDPScroll.asm].

## How much fits in a frame

Bytes per line, from Sega's table [MD-SWM §2.7, transfer capacity]:

| | 32 columns, display | 32 columns, blank | 40 columns, display | 40 columns, blank |
|---|---|---|---|---|
| 68000 → VDP | 16 | 167 | 18 | 205 |
| VRAM fill | 15 | 166 | 17 | 204 |
| VRAM copy | 8 | 83 | 9 | 102 |

For CRAM and VSRAM the figures are words, not bytes. "Blank" means vertical blank or any line where the display is turned off with register 1 [MD-SWM §2.7; GENVDP §11]. Sega's manual adds that DMA in vertical blank is about twice the speed of the fastest 68000 copy loop. During the display it is no faster than the CPU [MD-SWM §2.7].

Genesis Plus GX uses the same table one byte lower on blank lines (166 and 204 for 68000 → VDP, 165 and 203 for fills) <span class="tag disputed">disputed</span> ([discrepancy 43](../appendices/discrepancies.md)). For copies from 68000 memory to CRAM or VSRAM on blank lines it goes lower still, 161 and 198 words, because each of the VDP's refresh slots, 5 a line in 32 columns and 6 in 40, costs such a transfer one more slot <span class="tag emulator">emulator</span> [GPGX, core/vdp_ctrl.c `vdp_dma_update`]. BlastEm puts its refresh slots at the same count in 40 columns and marks the 32-column ones as guesses [BLASTEM, vdp.c `is_refresh`].

Sega counts these blank lines as usable for DMA per frame [MD-SWM §2.7]:

| | Lines | 68000 → VRAM in 40 columns |
|---|---|---|
| NTSC, 28 rows | 36 | 7,380 bytes |
| PAL, 28 rows | 87 | 17,835 bytes |
| PAL, 30 rows | 71 | 14,555 bytes |

Each count is two lines fewer than the frame's blank lines: 38, 89 and 73 against 36, 87 and 71 (see [Timing](vdp-timing.md#a-frame-line-by-line)) [32X-HWM §3.3]. The PAL pair holds only if a PAL frame has 313 lines, which is itself <span class="tag disputed">disputed</span>: MD-SWM's own display table gives 98 and 82 blank lines ([discrepancy 8](../appendices/discrepancies.md)). MD-TO's figure of 7,380 bytes per NTSC vertical blank uses the same 36 lines [MD-TO, system overview]. These are ceilings: the vertical interrupt's entry and any CPU work in the handler come off the top. Counted from the vertical interrupt, the emulators that model the line in detail leave 36.8 blank lines on NTSC, about 7,400-7,500 bytes in 40 columns once the handler has started the DMA ([Timing](vdp-timing.md#when-the-cpu-can-reach-vdp-memory)) <span class="tag emulator">emulator</span>.

## DMA in a real game

The patterns below are all from shipped code.

**One routine, with guards** [AB-DISASM, ConfigVDPDMA.asm]. Aerobiz programs every 68000-source DMA in one place:

1. Mask interrupts.
2. Request the Z80 bus, unless a flag says the caller already has it.
3. Wait for any running DMA to finish, then set register 15.
4. Write register 1 from its RAM copy with M1 set and the vertical interrupt off.
5. Write the length and the source.
6. Call the RAM routine to write the command, then wait for the DMA bit to clear.
7. For a RAM source, rewrite the first word.
8. Restore register 1 (M1 off), release the Z80 and restore the interrupt mask.

**Only in vertical blank.** Palette animation in Aerobiz checks the status register's VB bit before starting its CRAM DMA. If the vertical blank handler is running late and the display has started, it skips this frame's update instead of risking coloured dots on screen [AB-DISASM, VInt_Sub1.asm]. Virtua Racing Deluxe's vertical interrupt does all its Mega Drive VDP traffic itself: scroll and colour registers, then a 64-colour palette DMA from ROM inside a Z80 bus request [VRD-NOTES, analysis/VINT_HANDLER_ARCHITECTURE.md].

**Big uploads in chunks.** Aerobiz splits large tile sets into DMAs of 128 tiles (4 KB) and waits 4 frames between them, so a screen load never stalls the game for one long transfer [AB-DISASM, VRAMBulkLoad.asm].

**Animated tiles.** Up to 16 tiles of water, lights and the like are animated by DMAing one 32-byte frame per tile from ROM when a timer runs out. A bit mask says which slots are active [AB-DISASM, ControllerRead.asm, which despite its name runs the tile animation].

**Rectangles.** The VDP has no two-dimensional DMA, so a rectangle in a name table takes one DMA per row. To fill one, Aerobiz builds a single row of the fill value in a buffer on the stack, DMAs it once per row, then frees the stack space. To find the next row, it adds the row stride to the prebuilt command (see [Planes and scrolling](vdp-planes.md#working-with-name-tables)) [AB-DISASM, CmdDMABatchWrite.asm, CmdDMARowWrite.asm].

## DMA on the 32X

With the 32X switched on, the 68000 sees the cartridge at `$880000-$8FFFFF` and `$900000-$9FFFFF`, not at `$000000`. The register encoding is not the problem: `$900000` fits in registers 21-23. The problem is that the 32X does not appear to serve those addresses to the VDP when it is the one reading. To DMA from the cartridge, the 68000 sets the RV bit, which puts the cartridge back at `$000100-$3FFFFF` for the length of the transfer [32X-HWM §3.1 pp.13-14; AU-NOTES, PORT_ARCHITECTURE.md]. Everything the [RV bit section](../32x/architecture.md#the-rv-bit) lists then applies: interrupts off, code that sets RV running from RAM, SH-2s stalled if they touch the cartridge, and twelve bytes that read wrongly.

Aerobiz Ultimate handles this in one place, the routine every DMA already went through <span class="tag emulator">emulator</span> [AU-NOTES, PORT_ARCHITECTURE.md, disasm/32x/dma_stub.asm]:

- **Translate the source where it is used.** The game's code keeps passing addresses as it sees them, and only this routine turns them into cartridge offsets (table below).
- **Run the RV window from RAM.** Setting RV, writing the command, waiting for the end of the DMA and clearing RV must all run from RAM, and no work RAM was reliably free. The routine copies a small, position-independent body to the stack below the stack pointer, calls it there, and then drops it.
- **Results.** 3,000 frames with 233 RV switches, then 6,489 frames with 485, gave pictures identical to the original game. This used PicoDrive with the project's own RV patch, and Ares. Whether `$880000` really disappears with RV set has not been checked on a console.

The routine sorts each source into one of three cases [AU-NOTES, disasm/32x/dma_stub.asm, definitions_32x.asm]:

| Source the game passes | Translated to | Fetched |
|---|---|---|
| `$900000-$9FFFFF`, the game image at the address it is assembled for | source − `$800000`, cartridge `$100000-$1FFFFF` | With RV set, from RAM |
| Below `$100000`: a ROM address still in its Mega Drive form, as some of the game's screen data tables hold | source + `$100000`, the same cartridge bytes | With RV set, from RAM |
| Anything else: work RAM in practice | Unchanged | By the game's own RAM routine, RV clear |

The − `$800000` is not a general rule. It is right only because the port selects bank 1 at start-up, which shows cartridge `$100000-$1FFFFF` at `$900000`, and never selects another [AU-NOTES, PORT_ARCHITECTURE.md §2, disasm/32x/md_main.asm]. In general, a source in the banked window is at cartridge offset source − `$900000` + bank × `$100000`, and a source in the fixed window `$880000-$8FFFFF` is at source − `$880000` [32X-HWM §3.1 pp.13-14; §3.2.1, bank set register].

So the routine depends on two assumptions, and checks neither:

- **The bank is always 1.** The start-up code says nothing after it may change the bank without restoring it [AU-NOTES, disasm/32x/md_main.asm]. A DMA made while another bank was selected would fetch from the wrong megabyte.
- **No DMA source is in the fixed window.** A source at `$880000-$8FFFFF` matches neither translated case, so it would reach the VDP unchanged with RV clear, where the VDP cannot read it. The port's fixed window holds its 68000 glue code, the SH-2 program and new assets [AU-NOTES, PORT_ARCHITECTURE.md, cartridge layout]. None of these can be a DMA source until the routine also handles `$88xxxx`.

DMA from the Mega-CD's Word RAM has a separate fault when a 32X is attached, and Sega says not to use it <span class="tag manual">manual</span> [32X-TI item 13].

## Open questions

- The 128 KB wrap, the counters and the fill order rest on two developers' test ROMs, each run on a console of unknown model ([discrepancy 13](../appendices/discrepancies.md)). Repeat them on a console of known model.
- Does a CRAM DMA stop or wrap past `$7F` ([discrepancy 38](../appendices/discrepancies.md))? Run the test ROM's CRAM wrapping test and look at Batman & Robin's palette code.
- Why does a work-RAM DMA need its first word rewritten? A test should show what that word contains without the fix.
- Does `$880000-$9FFFFF` really disappear while RV = 1 (see [DMA on the 32X](#dma-on-the-32x))? Only emulators have been checked. The same console session that settles the boot chapter's reset questions can answer it; see [Boot, open questions](../32x/boot.md#open-questions).

## Sources

- [MD-SWM](../appendices/bibliography.md#md-swm): §2.7 DMA: modes, setting, fill, copy, transfer capacity
- [MD-TB](../appendices/bibliography.md#md-tb): addendum 4 §1 (Z80 bus request, first-word rewrite); address checker §5.1 (register 23 values)
- [MD-REF](../appendices/bibliography.md#md-ref): DMA ROM to VRAM notes
- [MD-TO](../appendices/bibliography.md#md-to): system overview, DMA per vertical blank
- [GENVDP](../appendices/bibliography.md#genvdp): §11 DMA
- [GENDEV-VDPINT](../appendices/bibliography.md#gendev-vdpint): Nemesis's post of 13 September 2013 (DMA counters, fill); test ROM tests TestDMATransferSourceAddressWrapping, TestDMATransferSourceRegUpdate, TestDMATransferLengthRegUpdate, TestDMAFillSourceRegUpdate, TestDMATransferToCRAMWrapping, TestDMATransferToVSRAMWrapping, TestDMAFillToVRAMV2
- [SGDK](../appendices/bibliography.md#sgdk): `src/dma.c`, splitting at 128 KB
- [PICODRIVE](../appendices/bibliography.md#picodrive): `pico/videoport.c`
- [GPGX](../appendices/bibliography.md#gpgx): `core/vdp_ctrl.c`, DMA source window, `vdp_dma_update` (rates per line)
- [ARES](../appendices/bibliography.md#ares): `ares/md/vdp/dma.cpp`, DMA source counter
- [BLASTEM](../appendices/bibliography.md#blastem): `vdp.c`, DMA source counter, `is_refresh`
- [32X-HWM](../appendices/bibliography.md#32x-hwm): §3.1 RV bit and the cartridge windows; §3.2.1 bank set register; §3.3 blank lines
- [32X-TI](../appendices/bibliography.md#32x-ti): item 13
- [AB-DISASM](../appendices/bibliography.md#ab-disasm): ConfigVDPDMA, the RAM routine at `$FFF000`, BulkCopyVDP, SelectVDPInit, ConfigVDPColors, ConfigVDPScroll, VInt_Sub1, VRAMBulkLoad, ControllerRead, CmdDMABatchWrite, CmdDMARowWrite, initial program
- [AU-NOTES](../appendices/bibliography.md#au-notes): PORT_ARCHITECTURE.md §2 (bank 1, cartridge layout) and §2.1, `disasm/32x/dma_stub.asm`, `md_main.asm`, `definitions_32x.asm`
- [VRD-NOTES](../appendices/bibliography.md#vrd-notes): analysis/VINT_HANDLER_ARCHITECTURE.md
