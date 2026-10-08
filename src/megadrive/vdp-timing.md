# Timing, interrupts and counters

The VDP sets the pace for the whole console. It draws the picture line by line, raises all three of the 68000's interrupts, and decides when the CPU may reach its memory. This chapter covers the shape of a frame, the H/V counter, the vertical and line interrupts, and when it is safe to touch VDP memory. It ends with how a real game organises its frame around these rules.

The clock figures behind every number here (3,420 master clocks per line, about 488.6 68000 cycles per line, 262 or 313 lines per frame) are in [System architecture](architecture.md#frame-timing).

## A frame, line by line

| | NTSC | PAL, 224 lines | PAL, 240 lines |
|---|---|---|---|
| Lines per frame | 262 | 313 | 313 |
| Visible lines | 0-223 | 0-223 | 0-239 |
| Vertical interrupt on line | 224 | 224 | 240 |
| Vertical blank, lines | 38 | 89 | 73 |
| Vertical blank, time | about 2.4 ms | about 5.7 ms | about 4.7 ms |
| Vertical blank, 68000 cycles | about 18,600 | about 43,500 | about 35,700 |

Sources: line counts [MD-SWM §2.1; 32X-HWM §3.3, V blank and display periods]. Times and cycles are worked out from the clocks. Sega gives about 5.6 ms and 4.6 ms for the two PAL cases [MD-SDM §6.2]. PAL's 313 lines are themselves <span class="tag disputed">disputed</span> ([discrepancy 8](../appendices/discrepancies.md)). The last of the blank lines is not fully blank: the VDP is already preparing line 0 on it, so it gives display-time access, not blank-time ([The H/V counter](#the-hv-counter)).

A line takes the same time in 32-column and 40-column modes. The television signal fixes it, and the narrower mode simply uses wider pixels. In 40-column mode, 2,560 of the line's 3,420 master clocks are the 320 visible pixels, and 860 are horizontal blanking [32X-HWM §3.3, H blank and display periods].

Three practical consequences:

- **NTSC vertical blank is short.** About 18,600 68000 cycles is all the time there is to update VDP memory at full speed. A DMA is the only way to fill it efficiently (see [below](#when-the-cpu-can-reach-vdp-memory)).
- **PAL vertical blank is long and the frame is slower.** A game that ties its speed to vertical interrupts runs at 50/60 of its NTSC speed in PAL unless it adjusts [MD-SDM §6.1].
- **On PAL, part of the vertical blank is visible.** In 224-line mode the bottom border is on screen, so a palette change made at the start of the vertical interrupt shows up there. Sega suggested waiting about 3 ms before changing colours <span class="tag manual">manual</span> [MD-SDM §6.1]. In 240-line mode the picture fills the screen and the problem mostly goes away. A game designed for 30 rows of tiles on PAL can share its layout with NTSC [MD-SDM §6.2].

## The H/V counter

`$C00008` returns where the beam is: the line in the high byte, the position along the line in the low byte. A byte read of `$C00008` gives the line, and `$C00009` the position [MD-SWM §2.6, HV counter; GENVDP §5].

| Byte | Normal | Interlace mode 2 |
|------|--------|------------------|
| High | Line bits 7-0 | Line bits 7-1, then bit 8 in place of bit 0 |
| Low | Horizontal position bits 8-1 | Same |

The low byte drops the lowest bit, so it counts in steps of 2 pixels. Neither counter runs straight from 0 to the end; each jumps back part way through the blanking period so that 8 bits can cover a whole line or frame:

| Counter | Sequence | Where it jumps back |
|---------|----------|---------------------|
| Line, NTSC | `$00-$EA`, then `$E5-$FF` | After line 234, at the start of vertical sync |
| Line, PAL, 28 rows | `$00-$FF`, `$00-$02`, then `$CA-$FF` | After line 258 |
| Line, PAL, 30 rows | `$00-$FF`, `$00-$0A`, then `$D2-$FF` | After line 266 |
| Position, 32 columns | `$00-$93`, then `$E9-$FF` | In the right blanking, just before horizontal sync |
| Position, 40 columns | `$00-$B6`, then `$E4-$FF` | The same. `$E4` lasts only one pixel |

Sources: [EXODUS, S315-5313_Timing.cpp; GPGX, core/vdp_ctrl.c, core/hvc.h; BLASTEM, vdp.c; GENVDP §5; PICODRIVE, pico.c, videoport.c] <span class="tag emulator">emulator</span>. The four emulators agree on every line sequence, and each frame adds up to 262 or 313 lines. Internally both counters have 9 bits, and the byte you read is the position counter without its lowest bit. In 40 columns that counter runs `$000-$16C`, then `$1C9-$1FF`, so `$E4` (from `$1C9`) shows for one pixel before `$E5`. Exodus and Genesis Plus GX have that pixel, while PicoDrive and BlastEm count in 2-pixel steps and go straight from `$B6` to `$E5`. Exodus's comments say several of its horizontal positions were checked with a logic analyser on a console. GENVDP took its horizontal sequence from the Master System and said so.

In interlaced modes Exodus gives every other field one extra line: an extra `$E4` before `$E5` on NTSC (263 lines), and in PAL a jump one line earlier, with the extra line inserted in every other field (312 and 313 lines) [EXODUS, S315-5313_Timing.cpp].

The line number does not change at position `$00`. It changes near the end of the active display, at the same moment as the line interrupt, and the other events follow from there [EXODUS, S315-5313_Timing.cpp; GPGX, core/hvc.h] <span class="tag emulator">emulator</span>:

| Event | 32 columns | 40 columns |
|-------|------------|------------|
| Line number goes up; line interrupt | Position `$85` | Position `$A5` |
| HB set in the status register | `$93` | `$B3` |
| HB cleared | `$05` | `$05` |
| Vertical interrupt and F set, on line 224 (240 in 30-row PAL) | `$00`, 770 master clocks after the line changed | `$00`, 788 master clocks after the line changed |
| VB set | When the line becomes 224 (or 240) | The same |
| VB cleared | When the line becomes the frame's last (261 on NTSC, 312 on PAL; the counter reads `$FF`) | The same |

So VB is set about 113 68000 cycles before the vertical interrupt, and clears a full line before line 0. On that last line the VDP is already fetching sprites for line 0.

So the line count is reliable only during the visible lines. Sega's manual warns that the counter's value is not valid during vertical blank <span class="tag manual">manual</span> [MD-SWM §2.6, HV counter]. In practice: to wait for a line on the screen, compare the high byte with a line number below 224. To do something "in vertical blank", use the vertical interrupt or the status register's VB bit instead.

Setting M3 (register 0 bit 1) freezes the counter at the moment the external interrupt fires. That is how light guns find the spot the gun saw [MD-SWM §2.6; GENVDP §4]. See [Controllers and I/O ports](io.md).

The counter is also a cheap profiler. Read it at the start and end of a routine, and the difference in lines (at about 488 68000 cycles each) is the routine's cost. See [Profiling and cycle counting](../howto/profiling.md).

## The vertical interrupt

With IE0 (register 1 bit 5) set, the VDP raises a level 6 interrupt at the start of the first line after the picture: line 224, or 240 in PAL's 30-row mode [MD-SWM §2.3; GENVDP §4]. The status register's F bit is set at the same moment. The Z80 gets its one interrupt per frame at the same time, held for about one line [PICODRIVE, pico/pico_cmn.c; see [Z80 bus control](z80.md)] <span class="tag emulator">emulator</span>.

The interrupt starts the vertical blank, so it is where VDP updates go. A handler that does nothing but set a flag wastes most of the vertical blank: by the time the main loop has seen the flag, part of it is gone. The usual design is the reverse. The handler does all VDP work itself, from requests the main loop has left in RAM (see [the frame, organised](#organising-the-frame)).

## The line interrupt

The line interrupt (Sega calls it the H interrupt) is a level 4 interrupt every *n* lines, enabled by IE1 (register 0 bit 4). Register 10 sets the spacing: 0 gives an interrupt on every line, 1 on every second line, and so on [MD-SWM §2.3].

How the counter actually works [GENVDP §4]:

- An internal counter goes down by one on every line. When it runs out, the interrupt fires and the counter reloads from register 10.
- It also reloads on every line of vertical blank except the first. So the count restarts from the top of each frame, and during vertical blank the line interrupt does not fire.
- **Writing register 10 does not reload the counter.** A new value takes effect at the next reload, so a handler that wants a different gap for the next interrupt must write it one interrupt early. Exodus, Genesis Plus GX, BlastEm and PicoDrive all agree: a write only changes the value the next reload uses <span class="tag emulator">emulator</span> [EXODUS, S315-5313_Ports.cpp; GPGX, core/system.c; BLASTEM, vdp.c; PICODRIVE, pico/pico_cmn.c].
- When both the line interrupt and the vertical interrupt fall on the same line, the 68000 takes the line interrupt first.

**Which lines get one.** GENVDP lists line 0 itself among the lines that reload the counter. The four emulators reload it on the frame's last line instead, and count on line 0 like any other line. With register 10 set to *n*, the first interrupt comes as the line number becomes *n*, then every *n* + 1 lines: *n*, 2*n* + 1, 3*n* + 2 and so on, up to line 224. With 0, that is one on every line from 0 to 224, 225 a frame. notaz's console test agrees: with 0 it counts 225 interrupts, lines 0 to 224, and with 17 loaded during the blank the first comes on line 17 [TESTPICO, t_irq_hint]. Read literally, GENVDP's reload on line 0 would move every one of them a line later <span class="tag emulator">emulator</span> [EXODUS, S315-5313_General.cpp; GPGX, core/system.c; BLASTEM, vdp.c; PICODRIVE, pico/pico_cmn.c; GENVDP §4; [discrepancy 46](../appendices/discrepancies.md)]. Check the line number in the handler rather than counting interrupts, and the difference does not matter.

The interrupt fires near the end of a line. The VDP fetches what it needs for the next line within about 36 68000 cycles of it, including register values. A handler can therefore change scrolling, colours or registers for the *next* line, but not for the line in progress <span class="tag manual">manual</span> [MD-SWM §2.3]. Effects that change something every line (wavy water, a road, a split screen) are built this way.

### The line 224 problem

With a line interrupt on every line, the last one comes on line 224, only about 14.7 µs before the vertical interrupt. If the 68000 is slow to accept it, for example because it is in the middle of a long multiply or divide, the vertical interrupt's moment passes. That vertical interrupt is lost, and the VDP delivers a second line interrupt (for line 225) in its place <span class="tag manual">manual</span> [MD-SDM §5.2; MD-TB, addendum 3 §2].

Sega gives two fixes. Either clear IE1 during the line 223 interrupt and set it again during the vertical interrupt, or raise the 68000's interrupt mask to 5 during line 223 and restore it in the vertical interrupt handler. In both cases the line 224 interrupt is still taken, just later. The same overlap can happen between a line interrupt and the external interrupt; Sega suggests telling them apart with the I/O port's receive flag [MD-SDM §5.3].

The simplest fix of all is not to use a line interrupt on every line near the bottom of the screen. Most effects only need lines 0-223. Disable the line interrupt from the last one you need until the vertical interrupt turns it back on.

## The external interrupt

The external interrupt is level 2, enabled by IE2 (register 11 bit 3). It is raised when the TH line of a controller port changes, if that port's control register enables it and TH is set as an input. A program cannot raise it by toggling TH itself during a pad read [GENVDP §4]. It exists for light guns and other peripherals; see [Controllers and I/O ports](io.md).

## When the CPU can reach VDP memory

The VDP shares VRAM between drawing and the CPU by giving the CPU a fixed number of access slots per line [MD-SWM §2.6, access timing]. The [VDP overview](vdp.md#when-the-cpu-can-get-in) has the table. In short, there are 16 slots per line in 32-column mode and 18 in 40-column mode while the picture is drawn, and 167 or 205 per line in blanking.

Where that leaves you:

| Time | What you can do |
|------|-----------------|
| Visible lines | A few words per line. Short CRAM or VSRAM changes for raster effects are fine; bulk copies stall the 68000 on the full FIFO |
| Vertical blank | Everything. A DMA moves about 205 bytes per line in 40-column mode, about 7.4 KB per NTSC frame |
| Display off (DISP = 0) | Everything, on every line the display is off [GENVDP §17] |

Sega counts only 36 of NTSC's 38 blank lines (87 and 71 for PAL) as usable for DMA, which gives 7,380 bytes per NTSC frame [MD-SWM §2.7, transfer capacity; MD-TO, system overview]. Plan for less: the vertical interrupt handler's own start-up and any CPU work eat into it. Full figures are in [DMA](vdp-dma.md#how-much-fits-in-a-frame).

The emulators that model the line in detail show where Sega's two lines go <span class="tag emulator">emulator</span> [EXODUS, S315-5313_Timing.cpp; GPGX, core/vdp_ctrl.c `vdp_dma_update`]:

- **The last line is not blank.** VB clears as line 261 starts, and the VDP goes back to its display-time access pattern to fetch sprites for line 0. Blank-rate access covers lines 224-260, 37 lines.
- **The vertical interrupt comes late in the first one.** It fires 788 master clocks into line 224 (770 in 32 columns), so 36.8 lines remain: 125,752 master clocks, about 17,960 68000 cycles.
- **The handler needs time to start the DMA.** The 68000 finishes its current instruction, spends 44 cycles taking the interrupt [M68K-UM], then writes the DMA registers. A handler that does nothing else first starts within about 100-250 cycles, or 0.2-0.5 of a line.

That gives about 7,400-7,500 bytes of 68000 → VRAM DMA in 40 columns, depending on whether a blank line moves 205 bytes (Sega) or 204 (Genesis Plus GX, [discrepancy 43](../appendices/discrepancies.md)), and about 6,000-6,100 in 32 columns. Sega's 7,380 leaves a margin of under one line. A DMA that runs past the end of blanking does not stop. It carries on at the display rate of 18 bytes a line (16 in 32 columns) with the 68000 halted, so a transfer 100 bytes too long costs the CPU several lines, not a few cycles. The same sums for PAL give 87.8 and 71.8 lines from the interrupt in 28 and 30 rows, against Sega's 87 and 71.

Two ways to get more:

- **Turn the display off.** Loading screens do it, behind a fade, for the whole frame. With a line interrupt, the display can also be switched off for some lines above or below the play area. Those lines show the backdrop colour and give full-speed access, which is extra transfer time for a game with a letterboxed screen [GENVDP §17].
- **Spread the work over frames.** If a job does not need to finish in one vertical blank, split it (see the next section).

During a DMA from 68000 memory the 68000 is stopped, so a long DMA steals CPU time as well as bus time. See [DMA](vdp-dma.md).

## Organising the frame

The rules above come down to one design: let a single piece of code own the VDP, run it in vertical blank, and have everything else ask it for work. Aerobiz Supersonic is a clean example [AB-DISASM, VInt_Handler3.asm]:

- **The vertical interrupt handler is a dispatcher.** It saves every register, then runs a fixed list of jobs, each guarded by a flag in RAM that the main program sets. In order: a CPU copy of a few colours to CRAM, sprite blinking, a palette animation DMA, a callback, tile animation DMA, then one of three larger jobs. After that it always reads the controllers and updates the cursor. Last, it clears a "frame done" flag that the main program waits on.
- **One API, with or without interrupts.** Before posting a job, Aerobiz checks its RAM copy of register 1. If the vertical interrupt is on, it sets the job's flag and waits for the handler to clear it. If it is off, as during screen set-up, it calls the same job routine directly. Its "wait *n* frames" call returns at once when the interrupt is off, so nothing can wait forever for an interrupt that will never come [AB-DISASM, CmdWaitFrames.asm, CmdSetupSprite.asm, CmdWaitDMA.asm].
- **Big jobs are sliced.** Filling or reading back a rectangle of a name table is done four rows per vertical blank. The handler keeps the running VDP command in RAM, adds one row's worth to it each time, and clears the job's flag only when the last row is done [AB-DISASM, VInt_Handler1.asm, VInt_Handler2.asm].
- **Latency-critical things skip the queue.** The mouse or pad cursor is sprite 0. The handler rewrites that sprite's 8 bytes straight into the sprite table every frame, so the cursor moves at full frame rate even when the game logic takes several frames per update [AB-DISASM, SubsysUpdate3.asm].
- **A stack check every frame.** The handler compares the stack pointer with `$FFE000`, the bottom of its 4 KB stack, and stops the game in a known loop if it has gone past. A runaway recursion then halts visibly instead of overwriting the game's variables [AB-DISASM, VInt_Handler3.asm].

Aerobiz also has a line interrupt handler for one per-line effect. On every line, it looks up "which row of the source should this line show" in a table, subtracts the current line, and writes the result into VSRAM for both planes. That gives vertical stretching, squashing or flipping from a plain table [AB-DISASM, VInt_Handler3.asm]. Note that this handler sets a VSRAM address on the VDP. If the main program were in the middle of a VDP copy at that moment, its remaining words would go into VSRAM. That is the classic bug described in [the VDP overview](vdp.md#the-vdp-remembers-half-a-command). It is safe only as long as nothing but the vertical blank handler writes to the VDP while the effect runs. Line interrupts cannot break into that handler, because the 68000 raises its mask to 6 on entry.

## Open questions

- Read the H and V counters on a console in both widths, both TV standards and interlace, to confirm the emulators' sequences: the jump lines (234 NTSC, 258 and 266 PAL) and the one-pixel `$E4` in 40 columns. Exodus's logic-analyser checks cover horizontal positions only.
- Does a write to register 10 take effect at once, or only at the next reload? notaz's test suggests the next reload [TESTPICO, t_irq_hint], but does not test a write in the middle of a count.
- Time a vertical-blank DMA on a console: start a 68000 → VRAM DMA as the first thing the vertical interrupt does and read the H/V counter when the 68000 resumes, for lengths around 7,400-7,600 bytes. The emulators predict about 7,450 in 40 columns.

## Sources

- [MD-SWM](../appendices/bibliography.md#md-swm): §2.1 raster line counts, §2.3 interrupts, §2.6 access timing and HV counter
- [MD-SDM](../appendices/bibliography.md#md-sdm): §5.2 H_INT and V_INT, §5.3 interrupts during communication, §6 PAL
- [MD-TB](../appendices/bibliography.md#md-tb): addendum 3 §2
- [MD-TO](../appendices/bibliography.md#md-to): system overview, DMA per vertical blank
- [32X-HWM](../appendices/bibliography.md#32x-hwm): §3.3 Mega Drive clock, H and V blank periods
- [GENVDP](../appendices/bibliography.md#genvdp): §4 interrupts, §5 HV counter, §17 registers
- [PICODRIVE](../appendices/bibliography.md#picodrive): `pico/pico.c`, `pico/pico_cmn.c`, `pico/videoport.c`
- [EXODUS](../appendices/bibliography.md#exodus): `S315-5313_Timing.cpp` (counter sequences, event positions), `S315-5313_General.cpp` (line counter), `S315-5313_Ports.cpp` (register 10)
- [GPGX](../appendices/bibliography.md#gpgx): `core/hvc.h`, `core/vdp_ctrl.c` (`vc_table`, `vdp_dma_update`), `core/system.c` (line counter)
- [BLASTEM](../appendices/bibliography.md#blastem): `vdp.c` (counter jumps, line counter)
- [M68K-UM](../appendices/bibliography.md#m68k-um): interrupt entry, 44 cycles
- [AB-DISASM](../appendices/bibliography.md#ab-disasm): VInt_Handler1-3, SubsysUpdate3, CmdWaitFrames, CmdSetupSprite, CmdWaitDMA
