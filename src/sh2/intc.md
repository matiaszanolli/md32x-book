# Interrupt controller

An SH-2 takes interrupts from three kinds of source: its four external request pins, its own peripherals (DMA, divider, timers, serial port), and NMI. The interrupt controller (INTC) ranks them, compares them with the CPU's mask, and picks the vector. On the 32X the external pins carry five interrupts from the 32X hardware, and an SH-2 design flaw adds a set of rules every handler has to follow. This chapter covers the SH-2's machinery, the 32X's five interrupts, what the boot ROM leaves set up, Sega's rules, and how working programs write their handlers.

How the 68000 raises the CMD interrupt, and how programs use it, is in [Communication](../32x/communication.md#the-cmd-interrupt).

## Levels and the mask

Every interrupt has a priority level from 0 to 16 [SH7604 §4.4.2, §5.2]:

| Source | Level |
|--------|-------|
| NMI | 16; cannot be masked |
| User break | 15 |
| External pins (IRL) | 1-15, given by the value on the four pins |
| On-chip peripherals | 0-15, set in IPRA and IPRB; 0 means never taken |

The status register's I3-I0 bits hold the CPU's mask level. An interrupt is taken only if its level is **above** the mask [SH7604 §4.4.3, §5.4.1]. Taking one sets the mask to that interrupt's level, so the handler can be interrupted only by something higher. Lowering the mask inside a handler lets equal and lower levels back in.

## Vectors

Exceptions find their handlers through a table of longword addresses at the vector base register (VBR): vector *n* is read from VBR + 4*n* [SH7604 §4.1.3]. The two resets are the exception: their PC and stack pointer always come from absolute addresses 0-15, which on the 32X is each SH-2's boot ROM.

| Vectors | Use |
|---------|-----|
| 0-3 | Power-on and manual reset: PC and SP |
| 4, 6 | Illegal instruction; illegal instruction in a delay slot |
| 9, 10 | CPU address error; DMA address error |
| 11, 12 | NMI; user break |
| 32-63 | `TRAPA #32` to `TRAPA #63` |
| 64-71 | External pins, auto-vectored (below) |
| 0-127 | On-chip peripherals: you choose the numbers, in their vector registers |

Source: [SH7604 §4.1.3, Table 4.3]. VBR and the stack pointer must be multiples of 4, or the exception itself causes an address error [SH7604 §4.8.1, §4.8.2].

**External interrupts share vectors in pairs.** With the default auto-vector mode, the four pins give fifteen levels but only eight vectors: level 1 uses vector 64, levels 2 and 3 vector 65, and so on up to levels 14 and 15 on vector 71 [SH7604 §5.2.3, Table 5.3]. A handler that serves both levels of a pair finds out which one it got from the mask level in SR.

**Peripheral vectors are yours to choose.** Each peripheral interrupt gets its number from a register:

| Register | Address | Size | Vectors for |
|----------|---------|------|-------------|
| VCRA | `0xFFFFFE62` | 16 | Serial receive error (bits 14-8), receive full (6-0) |
| VCRB | `0xFFFFFE64` | 16 | Serial transmit empty (14-8), transmit end (6-0) |
| VCRC | `0xFFFFFE66` | 16 | Free-running timer input capture (14-8), output compare (6-0) |
| VCRD | `0xFFFFFE68` | 16 | Free-running timer overflow (14-8) |
| VCRWDT | `0xFFFFFEE4` | 16 | Watchdog interval (14-8), refresh compare match (6-0) |
| VCRDIV | `0xFFFFFF0C` | 32 | Divider overflow |
| VCRDMA0, VCRDMA1 | `0xFFFFFFA0`, `0xFFFFFFA8` | 32 | DMA channel 0 and 1 end of transfer |

And its level from a priority register; sources sharing a field share a level:

| Register | Address | Bits 15-12 | Bits 11-8 | Bits 7-4 |
|----------|---------|------------|-----------|----------|
| IPRA | `0xFFFFFEE2` | Divider | DMA (both channels) | Watchdog and refresh counter |
| IPRB | `0xFFFFFE60` | Serial port | Free-running timer | |

Sources: [SH7604 §5.1.4, §5.3.1-5.3.7]. All of these are 0 after reset, so every peripheral interrupt starts at level 0: off [SH7604 §5.2.5].

**ICR** (`0xFFFFFEE0`) selects the NMI edge (bit 8) and auto-vector or external-vector mode for the pins (bit 0). Bit 15 reads the NMI pin [SH7604 §5.3.8]. The 32X holds NMI high, so NMI never happens [32X-HWM §5.3 p.87], and nothing we have read changes ICR from its reset value: auto-vectors.

## What happens when one is taken

1. The CPU finishes the instruction it is executing.
2. It pushes SR, then PC. The stack ends up with PC at the stack pointer and SR above it.
3. It sets the mask to the interrupt's level.
4. It reads the handler's address from the vector table and jumps there.

`RTE` reverses steps 2 and 3, restoring PC and SR. Nothing else is saved for you [SH7604 §4.1.2, §4.7, §5.4].

An interrupt is never taken between a delayed branch and its delay slot, nor straight after an instruction that loads or stores a control or system register (`LDC`, `STC`, `LDS`, `STS` and their memory forms). It waits until the next instruction [SH7604 §4.6].

### How long it takes

Hitachi gives the time from an external request to the first instruction fetch of the handler as 13 clocks plus the memory accesses: the two pushes, the vector read and the first fetch. To that add whatever is left of the instruction in progress [SH7604 §5.5, Table 5.8]. On the 32X, with the stack and the vector table in SDRAM and nothing cached, the four accesses come to roughly 4 + 4 + 12 + 12 clocks (two longword writes on a 16-bit bus, and two 16-byte bursts; see [Bus controller and memory timing](bsc.md)). That gives about 45 clocks, around 2 µs. Those figures are added up from the manuals, not measured. The instruction in progress can add far more: a cache miss to cartridge ROM can take over 100 clocks, and a DMA burst on the same CPU holds the bus until it ends.

### Clearing the source before returning

A request that is still asserted when `RTE` lowers the mask is taken again at once. A store that clears a request may still be in the write buffer when the next instruction runs. Reading the same address back makes the CPU wait until the write has finished. Hitachi's rule, which 32X-SUP2's timing figures repeat, is [SH7604 §5.7; 32X-SUP2, pipeline operation] <span class="tag manual">manual</span>:

- **External sources (all five 32X interrupts):** write the clear register, read the same address back, and leave at least one cycle, so at least one instruction, between that read and `RTE`. If you lower the mask with `LDC` instead, to allow nesting, leave at least four.
- **On-chip sources:** read back the register you cleared. The read-back is enough on its own: `RTE` may follow it directly. Before an `LDC` that lowers the mask, leave two instructions after the read.

Sega's own documents put it differently, and changed their minds. The main manual asks for at least two cycles between the write that clears an external interrupt and `RTE`, and does not mention a read-back. It then asks for two or more instructions after the `RTE`, without saying what that means for a handler [32X-HWM §5.3 p.89]. Sega's first sample handler, dated 6 July 1994, does not read back either: after the clearing write it asks for five clocks or more of other work before returning [32X-SUP2, interrupt correction sample program]. The revised sample, dated 20 September 1994 and sent to developers with Technical Bulletin #27 in December, reads back both the clear register and TOCR, and then asks for more than eight clocks of other work before the `RTE` <span class="tag manual">manual</span> [32X-TB27]. So Sega's last word puts the fixed delay on top of the read-back, not in place of it. No document says how the numbers were chosen. Only Hitachi's read-back is guaranteed to wait for the write, whatever it costs. Star Wars Arcade reads back and then runs five `nop`s; Mortal Kombat II follows the revised sample, with four to eight `nop`s after reading back both registers (see [Handlers in practice](#handlers-in-practice)).

## The 32X's five interrupts

The 32X drives the external pins of both SH-2s [32X-HWM §3.2.2, interrupt sources and priority levels; p.69]:

| Interrupt | Level | Vector | Mask bit at `0x20004000` | Clear register | Raised by |
|-----------|-------|--------|--------------------------|----------------|-----------|
| VRES | 14 | 71 | None | `0x20004014` | The Mega Drive reset button |
| V | 12 | 70 | Bit 3 | `0x20004016` | Start of vertical blank |
| H | 10 | 69 | Bit 2 | `0x20004018` | Horizontal blank, every *n* lines |
| CMD | 8 | 68 | Bit 1 | `0x2000401A` | The 68000, through `$A15102` |
| PWM | 6 | 67 | Bit 0 | `0x2000401C` | The PWM timer |

All five use even levels, so with auto-vectors each one has a vector to itself. The odd levels between them are never raised by the 32X.

**Each SH-2 has its own mask bits.** The interrupt mask register sits at the same address for both CPUs, but bits 0-3 are separate for each. The other bits are shared: FM (bit 15), ADEN (bit 9), CART (bit 8) and HEN (bit 7, which allows H interrupts during vertical blank). The mask bits are 0 after reset [32X-HWM §3.2.2, interrupt mask register]. Sega says the CMD clear is also separate per CPU [32X-HWM §3.2.2]. It says nothing about the other four clear registers. For V, notaz's console test shows the same: a V clear written by the Master does not stop the Slave's V [TESTPICO, t_32x_irq_vint]. PicoDrive, Ares and MAME all treat all five as per-CPU <span class="tag emulator">emulator</span> [PICODRIVE, pico/32x/memory.c; ARES, md/m32x/io-internal.cpp; MAME, src/mame/shared/mega32x.cpp]. All the register bits are in [System registers](../32x/registers.md#the-sh-2-side).

**VRES, V, H and PWM stay asserted until cleared.** A handler that forgets the clear is re-entered as soon as it returns. CMD is different: masking it withdraws the request, and unmasking it brings back one that is still pending [32X-HWM §3.2.2, points to be aware of]. See [The CMD interrupt](../32x/communication.md#the-cmd-interrupt).

**The H interrupt interval** is set by the H count register at `0x20004004`: 0 means every line. A new value takes effect only after the next horizontal blank, so the first interrupt after a change can still come at the old interval [32X-HWM §3.2.2, H count register; points to be aware of].

## What your code starts with

Both boot ROMs run with every interrupt masked (SR = `$F0`, mask level 15) and never lower it. Every entry of their own vector tables points at a branch to itself at `0x13C`, so any exception during boot simply hangs. Just before jumping to your code they load VBR from your user header [VRD-NOTES, 32X BIOS dump]. So your code starts with:

- SR mask 15: nothing gets in until you lower it.
- VBR pointing at your vector table.
- The 32X mask bits all 0, every peripheral at priority 0, ICR in auto-vector mode.
- The free-running timer at its reset values; the boot ROMs do not touch it.

## Sega's rules: the SH-2 interrupt flaw

The SH-2s in production 32X units have a flaw in how they accept external interrupts. Sega describes two symptoms [32X-SUP2, limitations concerning the SH2 interrupt]:

1. An external interrupt that arrives while the CPU is accepting another one, or while a lower-level one is pending, can be **missed**.
2. With several requests at once, the CPU can **jump through the wrong vector**, although it still sets the correct mask level in SR.

Toshiyasu Morita, then at Sega of America, describes the same fault more narrowly: if a higher-level request arrives within three cycles of a lower one, the CPU jumps through the lower one's vector and the higher one is lost, though SR is set to the higher level [MORITA-FAQ]. A later revision of the chip fixed this, but Sega warns that the first production units use the unfixed one, so every program must work around it [32X-SUP2, precautions]. Sega names the fixed revision cut 2.5; Morita names cut 2.5 as the faulty one <span class="tag disputed">disputed</span> ([discrepancy 41](../appendices/discrepancies.md)).

### How the TOCR flip works

The free-running timer's output pin FTOA is wired to IRL0, the lowest of the four interrupt request lines <span class="tag manual">manual</span>. The service manual's schematic shows each SH-2's FTOA tied straight to its own /IRL0 pin, and /IRL1-/IRL3 driven by the 32X's interrupt logic, separately for each CPU [32X-SVC §7-3]. Sega's timing diagram labels a change of FTOA "FTOA (IRL0) transition", and shows it moving the request level from 8 to 9 [32X-TB27]. So the 32X's own interrupts have only the upper three lines, which is why they all sit at even levels: FTOA supplies the low bit. With the timer set up as Sega asks, FTOA copies TOCR bit 1 within 16 to 24 clocks (see [Timers](timers.md#how-the-interrupt-workaround-uses-it)), so writing that bit moves a pending request between its even level and the odd one above it.

That is how the workaround recovers a missed interrupt. A request the CPU failed to accept is still asserted, and the flip turns it into a new, higher level, which the CPU then sees and takes. Morita's FAQ says so in as many words: the flip makes the level bounce between odd and even, and that retriggers the lost interrupt [MORITA-FAQ]. It also explains three of the rules below:

- A 32X interrupt can arrive at its own level or the odd level above it, so both levels of each pair must lead to the same handler, and the dispatcher must ignore the low bit.
- With no 32X request pending, FTOA alone can present level 1; the diagram ends at level 1 after the last request is cleared [32X-TB27]. A mask of 0 would let that through, so the mask must stay at 1 or above.
- FTOA can turn a request into level 1, 7, 9, 11, 13 or 15: exactly the levels the main manual forbids (rule 3). Levels 3 and 5 never appear on the pins, since no 32X interrupt sits at 2 or 4, which is why peripherals may use 2-5 (rule 2).

The wiring has a cost of its own. When two kinds of interrupt are in use, one interrupt can be **handled twice**. In Sega's example a CMD interrupt is accepted at level 8, but a V interrupt arrives before the CMD handler has masked SR. The V handler runs, writes TOCR and clears V, and the request falls back to 8. FTOA then changes before the CMD handler's mask takes effect, the request becomes 9, and the CPU accepts CMD again at level 9. When that handler returns, the first one, accepted at level 8, carries on and handles the same CMD a second time [32X-TB27]. The bulletin says this happens only on the 32X, not on the Saturn, which uses the same CPU. Its cure is the revised sample below. The rules come from two documents: that supplement and the restrictions in the main manual [32X-SUP2; 32X-HWM §5.3 p.89] <span class="tag manual">manual</span>. Each rule names its source:

1. **Never run with the mask at 0.** Keep SR's mask at 1 or more [32X-SUP2, precautions; 32X-HWM §5.3 p.89].
2. **Put peripheral interrupts at levels 2-5**, below all five 32X interrupts [32X-SUP2, precautions]. The main manual does not say this.
3. **Do not use levels 1, 7, 9, 11, 13 or 15.** If one arrives anyway, return without doing anything [32X-HWM §5.3 p.89].
4. **Send every interrupt vector to one entry routine.** That is all eight external vectors and every peripheral vector you use. The routine reads the level from SR and dispatches from that, because the level is right even when the vector was wrong [32X-SUP2, corrective action; 32X-HWM §5.3 p.89]. Give both levels of each pair the same entry in your dispatch table [32X-SUP2, interrupt correction sample program].
5. **Change bit 1 of the free-running timer's TOCR register in every external interrupt handler** [32X-SUP2, corrective action, sample program; 32X-TB27]. For that to work, the timer must be set up exactly as Sega specifies, so programs cannot use it for anything else [32X-HWM §5.3 p.89]. See [Timers](timers.md) and [How the TOCR flip works](#how-the-tocr-flip-works).
6. **Make sure the clear has reached the register before returning** [32X-SUP2, precautions; 32X-HWM §5.3 p.89]. The two documents ask for this in different ways; see [Clearing the source before returning](#clearing-the-source-before-returning).
7. **If an on-chip peripheral shares a level with a 32X interrupt**, check that peripheral's own flags to tell which one fired [32X-HWM §5.3 p.89]. This comes from the main manual, which does not limit peripherals to levels 2-5. A program that follows rule 2 never has a shared level, so rule 7 matters only to a program that puts a peripheral at 6 or above anyway.

Sega published two sample routines:

| | First sample, 6 July 1994 [32X-SUP2] | Revised sample, 20 September 1994 [32X-TB27] |
|-|------|------|
| Entry | Masks everything (SR = `$F0`) | Masks everything, writes 0 to TOCR and reads it back |
| TOCR in the handler | Flips bit 1 with an exclusive OR | Writes 2 (bit 1 set) and reads it back |
| Clearing the source | Writes the clear register | Writes the clear register, then reads it back after TOCR |
| Before returning | Five clocks or more of other work | More than eight clocks of other work |

The bulletin offers the revision as the cure for the double handling. What changes is that TOCR gets fixed values, bit 1 cleared when any interrupt is entered and set when its handler finishes, instead of being toggled from whatever state it was in. Both samples dispatch from a 16-entry table indexed by the SR level, with each pair of levels sharing a handler. The bulletin says the revised code also appears in the 32X Hardware Manual Supplement 2 [32X-TB27]; the July 1994 edition used for this book has only the first sample, so a later edition presumably carried it.

## Handlers in practice

**d32xr** follows the rules closely [D32XR, crt0.s]:

- All eight external vectors on each CPU point at one routine.
- That routine saves three registers and masks everything. It sets TOCR to `$E0` and reads it back, then picks a handler from a 16-entry table indexed by the level in SR.
- Each level pair shares an entry, and levels 0 and 1 go to a routine that returns at once.
- Just before calling the handler, it sets the mask to the interrupt's level plus one (`ldc` in the delay slot of the `jsr`). Higher interrupts can then nest.
- Each handler sets TOCR back to `$E2`, reads it back, and clears its source. That is the scheme of Sega's revised sample [32X-TB27].
- Peripheral interrupts are routed into the same table at even levels below 6: the watchdog at level 2 with vector 65, the second DMA channel at level 4 with vector 66. Those are the vectors external levels 2-5 would use, which already point at the shared routine [D32XR, marshw.c, marsnew.c]. The Master sets up the watchdog, the Slave the DMA channel.
- Both CPUs run at SR = `$10`, mask 1, set in their start-up code just before they enable their 32X interrupts. Nothing changes it later. The Master enables V and CMD (mask register `$0A`), the Slave only CMD (`$02`) [D32XR, crt0.s]. Mask 1 is the lowest rule 1 allows, and it has to be below 2 for the level-2 watchdog to be taken at all.

**Star Wars Arcade** follows the same rules in a shipped game, though not in the same way as d32xr [SWA, SH-2 code at `0x060004B0`, `0x0600051C`, `0x06000928`, `0x06000F2E`]:

- Every external vector on each CPU, and vector 72, points at one routine per CPU. That routine saves `PR`, `r0` and `r1` and calls a 16-entry table indexed by the SR level. The Master's masks everything first; the Slave's leaves the mask at the interrupt's level. Unused levels go to a bare `rts`, and level pairs share entries.
- Each handler flips TOCR bit 1 with an exclusive OR, writes its clear register, reads it back, and runs five `nop`s before returning. That is Sega's first sample almost word for word, with a read-back added and the sample's five clocks of other work filled with `nop`s [SWA, SH-2 code at `0x06000AB0`]. It does not take up the September revision, so it is open to the double handling Bulletin #27 describes [32X-TB27]. d32xr writes `$E0` in its entry routine and `$E2` in each handler; Star Wars Arcade's entry routines leave TOCR alone, and its handlers only flip the bit. The Slave's watchdog handler is the exception: it lives in the on-chip RAM and draws (see [Timers](timers.md#the-watchdog-timer) and [Software 3D](../techniques/software-3d.md)).
- The Slave gives the watchdog level 5 and vector 72, enables the PWM interrupt, and runs with SR = `$20` (mask 2). The Master enables CMD and also runs at mask 2.
- Both CPUs set up the free-running timer at start-up exactly as d32xr does (see [Timers](timers.md)).

**Mortal Kombat II**, from an outside studio, has its own variant [MK2, SH-2 code at `0x060002D8`, `0x06004E24`, `0x06000350`-`0x060004C8`]:

- One entry routine per CPU for all eight external vectors. It saves `r0`-`r2`, GBR and PR, masks everything, writes 0 to TOCR (which reads back as `$E0`), and calls a 16-entry table by the SR level. Unlike d32xr it never lowers the mask, so handlers do not nest.
- Each handler clears its source, writes 2 to TOCR (`$E2`), reads back both the clear register and TOCR, and then runs four to eight `nop`s. This is Sega's revised sample [32X-TB27], the scheme d32xr also uses, not the exclusive OR of the first one.
- No peripheral interrupts at all. The Master unmasks V and CMD (mask register `$0A`), the Slave only PWM (`$01`), and both run at SR = `$20`.
- The VRES handler, called like any other, does not return to the entry routine. It rewrites the saved PC, SR and stack pointer and executes `rte` itself, so the CPU resumes at its start-up code with a fresh stack. It is Sega's sample handler, with both of the sample's defects ([Sega's sample code in the games](../appendices/sample-code.md)).

**After Burner Complete**, published by Sega and programmed by Rutubo Games, has a variant of its own [AB32X, SH-2 code at `0x060022EC`-`0x0600230A`, `0x060022C4`, `0x0600371C`, `0x0600033C`-`0x0600034C`, `0x060003A2`]:

- Again one entry routine per CPU. The Master's tells CMD from everything else with a single test: after an interrupt is accepted, SR's mask equals its level, and of the levels the Master can take, CMD (8, binary `1000`) is the only one with SR bits 5 and 6 (mask bits I1 and I2) both clear, so `tst #$60,r0` on a copy of SR picks it out. VRES and anything unexpected go to a second path that checks for VRES with `(SR & $E0) = $E0`.
- The CMD command number, the low 6 bits of `$A15120`, indexes a table of 16-bit offsets used with `braf`. Such a table is half the size of a table of addresses and works wherever the code is loaded. The command runs inside the handler.
- The Slave indexes a table of handler addresses with `(SR >> 2) & $3C`. Levels it never enables point at a loop that never returns.
- Every handler flips TOCR bit 1 at the *end*, after masking everything and just before it clears its source and reads the clear register back. Sega's sample flips it at the start [32X-SUP2].
- The Master enables only CMD (mask register 2), the Slave PWM and CMD (`$03`), both at SR = `$20`.

**marsdev's** example dispatches on SR level the same way, comparing the level with the low bit ignored. It clears the source and then waits four `nop`s rather than reading it back, and it does not touch TOCR [MARSDEV, examples/32x-skeleton/sh_src/mars_start.s].

**Save every register a handler uses.** `RTE` restores only PC and SR. Aerobiz Ultimate's handlers once used `r1` without saving it, and that caused rare, timing-dependent corruption of whatever C code was interrupted. It went unnoticed until the V interrupt was turned on as a clock [AU-NOTES, HISTORY.md; disasm/sh2/master/main.s]. A handler that calls C must save every register C code may change without restoring. Under GCC's default SH conventions that is `r0-r7`, `PR`, `MACH` and `MACL`. Alternatively, declare the C function with GCC's `interrupt_handler` attribute and let the compiler do the saving.

## In emulators

Neither PicoDrive nor Ares models the flaw: they never miss an interrupt or take the wrong vector. TOCR is just a stored value in both, and FTOA is not wired to IRL0, so the double handling of Bulletin #27 cannot happen either <span class="tag emulator">emulator</span> [PICODRIVE, pico/32x/sh2soc.c; ARES, component/processor/sh2/sh7604/interrupts.cpp, io.cpp]. A handler that skips the workaround works in both, and so does a missing read-back. Aerobiz Ultimate's handlers, which skip both, are an example [AU-NOTES, disasm/sh2/master/main.s]. Only a console can show whether a program gets this right.

## Open questions

- How often does the flaw strike on a production 32X, and under what load? Morita's three-cycle window suggests rarely, but nobody has counted.
- Which chip revision is the faulty one ([discrepancy 41](../appendices/discrepancies.md)), and which consoles carry it?
- Are the V, H, PWM and VRES clear registers separate for each SH-2, as they are for CMD? PicoDrive, Ares and MAME all assume so; no Sega document says.
- What is the real interrupt response time on a 32X, from request to the first instruction of the handler?
- Is a fixed delay with no read-back, as in the main manual and the first sample, enough on a console? How were the two, five and eight clock figures chosen? And what does the main manual mean by two or more instructions *after* the `RTE`?

## Sources

- [SH7604](../appendices/bibliography.md#sh7604): §4 exception handling (§4.1.2-4.1.3, §4.4, §4.6-4.8), §5 interrupt controller (§5.1.4, §5.2-5.7)
- [32X-HWM](../appendices/bibliography.md#32x-hwm): §3.2.2 SH-2 system registers, p.69 interrupt priorities, §5.3 pp.87, 89 restrictions
- [32X-SUP2](../appendices/bibliography.md#32x-sup2): limitations concerning the SH2 interrupt, corrective action, precautions, pipeline operation, interrupt correction sample program
- [32X-TB27](../appendices/bibliography.md#32x-tb27): FTOA as IRL0, double handling, revised sample (20 September 1994)
- [MORITA-FAQ](../appendices/bibliography.md#morita-faq): the fault's three-cycle window, FTOA retriggering
- [32X-SVC](../appendices/bibliography.md#32x-svc): §7-3, SH-2 interrupt pins
- [VRD-NOTES](../appendices/bibliography.md#vrd-notes): 32X BIOS dump
- [D32XR](../appendices/bibliography.md#d32xr): crt0.s, marshw.c, marsnew.c
- [MARSDEV](../appendices/bibliography.md#marsdev): examples/32x-skeleton/sh_src/mars_start.s
- [MK2](../appendices/bibliography.md#mk2): SH-2 code at `0x060002D8`, `0x06004E24`, `0x06000350`-`0x060004C8`
- [AB32X](../appendices/bibliography.md#ab32x): SH-2 code at `0x060022EC`-`0x0600230A`, `0x060022C4`, `0x0600371C`, `0x0600033C`-`0x0600034C`, `0x060003A2`
- [SWA](../appendices/bibliography.md#swa): SH-2 code at `0x060004B0`, `0x0600051C`, `0x06000928`, `0x06000AB0`, `0x06000F2E`
- [AU-NOTES](../appendices/bibliography.md#au-notes): HISTORY.md, disasm/sh2/master/main.s
- [PICODRIVE](../appendices/bibliography.md#picodrive): pico/32x/memory.c, pico/32x/sh2soc.c
- [ARES](../appendices/bibliography.md#ares): component/processor/sh2/sh7604/interrupts.cpp, io.cpp; md/m32x/io-internal.cpp
- [MAME](../appendices/bibliography.md#mame): src/mame/shared/mega32x.cpp
