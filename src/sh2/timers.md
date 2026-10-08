# Timers (FRT and WDT)

Each SH-2 has two timers: a 16-bit free-running timer (FRT) and an 8-bit watchdog timer (WDT). On the 32X neither is free for ordinary use. The FRT is taken over by Sega's workaround for the SH-2 interrupt flaw, and the WDT may not reset the chip, which leaves it as an interval timer. This chapter covers both, the settings Sega asks for, the settings shipped games actually use, and the other ways a 32X program can keep time.

## The free-running timer

A 16-bit counter (FRC) that counts up from the CPU clock divided by 8, 32 or 128, or from an external pin. It is compared all the time with two registers, OCRA and OCRB. A match can set a flag, raise an interrupt, clear the counter (match A only), and drive an output pin (FTOA, FTOB) to a chosen level. A fourth register captures the counter on an input pin's edge [SH7604 §11.1].

| Register | Address | Reset value | Holds |
|----------|---------|-------------|-------|
| TIER | `0xFFFFFE10` | `$01` | Interrupt enables: bit 7 capture, bit 3 match A, bit 2 match B, bit 1 overflow. Bit 0 always reads 1 |
| FTCSR | `0xFFFFFE11` | `$00` | Flags (bit 7 capture, 3 match A, 2 match B, 1 overflow; clear by reading 1 and writing 0). Bit 0 CCLRA: clear FRC on match A |
| FRC | `0xFFFFFE12`-`13` | `$0000` | The counter |
| OCRA / OCRB | `0xFFFFFE14`-`15` | `$FFFF` | Compare values, sharing one address; TOCR bit 4 picks which one you see |
| TCR | `0xFFFFFE16` | `$00` | Bits 1-0: clock ÷ 8, ÷ 32, ÷ 128, or external. Bit 7: capture edge |
| TOCR | `0xFFFFFE17` | `$E0` | Bit 4 OCRS: which compare register the address shows. Bit 1 OLVLA, bit 0 OLVLB: the level each output pin takes on a match. Bits 7-5 always 1 |
| ICR | `0xFFFFFE18`-`19` | `$0000` | Captured counter value |

Source: [SH7604 §11.1.4, §11.2]. Access every register by byte. The 16-bit ones go through an 8-bit temporary register, so write the high byte first and read the high byte first [SH7604 §11.3]. Each access costs 3 to 12 clocks, because the timer runs on a clock of its own and makes the CPU wait [SH7604 §11.7].

### What Sega asks for, and what games do

Sega's restrictions say plainly that programs cannot use the FRT. They give the values to set instead <span class="tag manual">manual</span> [32X-HWM §5.3 p.89]:

| Register | Sega's value | d32xr | Star Wars Arcade | Mortal Kombat II | After Burner Complete |
|----------|--------------|-------|------------------|------------------|-----------------------|
| TIER | `$01` | `$00` | `$00` | `$00` | `$00` |
| TOCR | `$E2` | `$E2` | `$E2` | `$E2` | `$E2` |
| OCRA | `$0002` | `$0001` | `$0001` | `$0001` | `$0001` |
| OCRB | (not given) | | | `$0001`, Master only | `$0001`, Master only |
| TCR | (not given) | `$00` | `$00` | `$00` | `$00` |
| FTCSR | `$01` | `$01` | `$01` | `$01` | `$01` |
| FRC | (not given) | `$0000` | `$0000` | `$0000` | `$0000` |

Sources: [32X-HWM §5.3 p.89; D32XR, crt0.s; SWA, SH-2 code at `0x06000426`, `0x0600046E`; MK2, SH-2 code at `0x06000266`, `0x06005110`; AB32X, SH-2 code at `0x0600212E`, `0x0600020E`]. All four programs write the registers in the same order: TIER, TOCR, OCRA, TCR, FTCSR, then the counter. The three retail games do it on both CPUs at start-up. Sega's own start-up sample writes OCRA = 1 as well, and on the Master it also sets OCRB = 1 (by writing TOCR = `$F2` to select it, then `$E2` again). That is for the reset described [below](#ftob-and-the-vres-reset) [32X-TIA1 p.4]. The revised interrupt sample of September 1994 sets TIER, TOCR, OCRA, TCR, FTCSR and the counter to exactly the values the games use [32X-TB27]. Only the manual's own table gives OCRA = 2 and TIER = `$01`.

The two sets of values mean nearly the same thing:
- No FRT interrupts. TIER `$00` and `$01` differ only in the bit that always reads 1.
- The counter runs at the CPU clock ÷ 8.
- It clears itself on every match A.
- Each match drives FTOA to 1.

With OCRA = 1 the counter goes 0, 1, 0, 1, and match A comes every two counts: 16 CPU clocks. With OCRA = 2 it comes every three counts: 24 clocks [SH7604 §11.2.5, §11.4.3]. Sega's own sample code and shipped game use 1 <span class="tag disputed">disputed</span> ([discrepancy 20](../appendices/discrepancies.md)).

### How the interrupt workaround uses it

Every external interrupt handler flips bit 1 of TOCR (OLVLA), as Sega's first sample does, or sets it to 0 at entry and back to 1 in the handler, as Sega's revised sample and d32xr do [32X-SUP2; 32X-TB27; D32XR, crt0.s; SWA, SH-2 code at `0x06000AB0`]. With the timer set up as above, FTOA takes the new level at the next match, within 16 to 24 clocks. So the workaround amounts to toggling the SH-2's FTOA pin. On each SH-2 that pin is wired straight to the same CPU's own /IRL0 input, the low bit of the interrupt level; the other three request lines come from the 32X's interrupt logic, a separate set for each CPU <span class="tag manual">manual</span> [32X-SVC §7-3; 32X-TB27]. So a change on FTOA moves a pending 32X request between its even level and the odd one above, and the CPU sees a new request [MORITA-FAQ]. Each CPU's flips affect only its own interrupts. What that cures, and the double handling it can cause, are in [How the TOCR flip works](intc.md#how-the-tocr-flip-works).

What follows for code:

- **Leave the FRT alone** after setting it up: no other counting, no FRT interrupts, no changes to OCRA or CCLRA.
- **A TOCR flip costs time.** A read and a write of an FRT register take 6 to 24 clocks between them, in every handler.
- **The FRT cannot measure time** with these settings: the counter only ever reads 0 or 1 (or 0-2 with Sega's OCRA). Use one of the clocks [below](#keeping-time-on-the-32x).

### FTOB and the VRES reset

When the reset button is pressed while RV = 1, the Master must reset the whole 32X (see [Boot](../32x/boot.md#pressing-reset)). Sega's sample does it from the VRES handler by setting TOCR bit 0 (OLVLB) and then looping forever. With OCRB = 1, the next match B drives FTOB high.

The schematic shows where that goes. The Master's FTOB drives a transistor that pulls down the reset input of IC11, a 315-5684, whose reset output is the board's -RESET line, the line that resets the 32X's interface chip (315-5818, its MRES pin). The Mega Drive's own reset, /MRES from the cartridge slot, reaches the same input through a diode. So setting FTOB pulls the same reset line as the Mega Drive's own reset signal <span class="tag manual">manual</span> [32X-SVC §7-1, §7-3, §7-4]. The Slave's FTOB is not connected, and neither CPU's WDTOVF is, so 32X-TIA1's "watch-dog-timer output" can only mean FTOB.

Mortal Kombat II copies the sample, OCRB = 1 included [MK2, SH-2 code at `0x06000286`, `0x0600037A`], and so does After Burner Complete [AB32X, SH-2 code at `0x0600214E`, `0x060022B4`]. Star Wars Arcade's Master handler does the same, but that game never sets OCRB, which stays at `$FFFF`, so by Hitachi's rules FTOB should never change and its reset should never happen <span class="tag disputed">disputed</span> [32X-TIA1 pp.4, 6; SWA, SH-2 code at `0x060005B2`; [discrepancy 22](../appendices/discrepancies.md)]. Set OCRB = 1 at start-up, as Sega's sample does, and leave TOCR bit 0 alone everywhere else.

## The watchdog timer

An 8-bit counter (WTCNT) that counts up from the CPU clock divided by one of eight values. When it overflows, it either raises an interrupt (interval mode) or signals a watchdog reset (watchdog mode) [SH7604 §12.1].

| Register | Write | Read | Holds |
|----------|-------|------|-------|
| WTCSR | Word `$A5xx` to `0xFFFFFE80` | Byte at `0xFFFFFE80` | Bit 7 OVF (interval mode overflow; clear by reading 1 and writing 0). Bit 6 WT/IT: 0 interval, 1 watchdog. Bit 5 TME: run. Bits 4-3 always 1. Bits 2-0: clock divisor |
| WTCNT | Word `$5Axx` to `0xFFFFFE80` | Byte at `0xFFFFFE81` | The counter |
| RSTCSR | Word to `0xFFFFFE82` | Byte at `0xFFFFFE83` | Watchdog reset control |

Source: [SH7604 §12.1.4, §12.2]. The odd write format, a word with a key byte on top, guards against stray writes. Byte or longword writes are ignored [SH7604 §12.2.4].

Sega forbids using the watchdog to reset the chip on the 32X <span class="tag manual">manual</span> [32X-HWM §5.3 p.87], so in practice it is an interval timer. Its interrupt takes its level from IPRA bits 7-4 and its vector from VCRWDT bits 14-8 [SH7604 §5.3.1, §5.3.3]. Sega's interrupt rules put it at level 2-5 (see [Interrupt controller](intc.md)).

Overflow comes every 256 counts. At 23.01 MHz (NTSC):

| Bits 2-0 | Divisor | One count | Overflow every |
|----------|---------|-----------|----------------|
| 000 | 2 | 0.087 µs | 22.2 µs |
| 001 | 64 | 2.78 µs | 712 µs |
| 010 | 128 | 5.56 µs | 1.42 ms |
| 011 | 256 | 11.1 µs | 2.85 ms |
| 100 | 512 | 22.3 µs | 5.70 ms |
| 101 | 1024 | 44.5 µs | 11.4 ms |
| 110 | 4096 | 178 µs | 45.6 ms |
| 111 | 8192 | 356 µs | 91.1 ms |

Divisors from [SH7604 §12.2.2]. The times are worked out for the 32X clock; Hitachi's own table is for 28.7 MHz.

**d32xr** uses the watchdog as a profiling clock [D32XR, marsnew.c, marshw.c, crt0.s]:
- To start it, it writes `$5A00` (counter 0), then `$A53E` (interval mode, running, ÷ 4096). To stop it, it writes `$A518`.
- Its interrupt, at level 2 with vector 65, counts overflows.
- Reading the counter gives overflows × 256 + WTCNT: a 24-bit time in units of 4096 clocks.
- The handler flips TOCR like any other.

**Star Wars Arcade** uses it to pace drawing on its Slave [SWA, SH-2 code at `0x06000928`, `0x0600051C`, `0x06000B98`-`0x06000C0C`; on-chip code at `0xC0000582`-`0xC0000748`]:
- The Slave gives it level 5 and vector 72. Its level-5 entry in the dispatcher's table points into the 2 KB of on-chip RAM, at a handler that drives the 32X VDP's auto fill.
- To start it, the Slave sets the counter to 255 (`$5AFF`) and starts it at ÷ 2 (`$A538`), so the first interrupt comes almost at once.
- Each interrupt starts the next fill, then sets the counter so that the next interrupt comes when that fill should be finished: 240 counts (480 clocks) for a 161-word line of the clear, 256 counts for a long span, 129 counts to look again when there is nothing to draw. It stops the timer (`$A518`) and restarts it each time.
- The Master's level-5 entry is a stub that only flips TOCR bit 1 and waits five `nop`s [SWA, SH-2 code at `0x060022C4`]. The Master never starts its watchdog.

So the watchdog is the Slave's scheduler: the CPU sets up polygons while the VDP fills, and the timer brings it back when the VDP is ready for more. See [Software 3D](../techniques/software-3d.md#star-wars-arcade-polygons-as-auto-fills).

## Keeping time on the 32X

With the FRT taken, the clocks a program can use are:

| Clock | Resolution | Cost | Notes |
|-------|------------|------|-------|
| V interrupt | One frame (16.7 ms NTSC) | One interrupt per frame | Aerobiz Ultimate counts V-Blanks as its clock, because the FRT is off limits [AU-NOTES, disasm/sh2/master/main.s]. Mortal Kombat II's Master does the same, and paces its main loop by waiting for the count to change [MK2, SH-2 code at `0x060003A4`, `0x06001088`] |
| H interrupt | One line, or every *n* lines | One interrupt per *n* lines | See [Interrupt controller](intc.md#the-32xs-five-interrupts) |
| PWM timer interrupt | Set by the PWM cycle and TM bits | One interrupt per period | Often already running for sound. See [PWM audio](../32x/pwm.md) |
| WDT interval | 2 to 8192 clocks per count | One interrupt per 256 counts | Read WTCNT for the fine part, as d32xr does |

## In emulators

- **PicoDrive** counts the watchdog in interval mode, and stores the FRT registers without running the counter <span class="tag emulator">emulator</span> [PICODRIVE, pico/32x/sh2soc.c].
- **Ares** runs both: the FRT counter with its compare and overflow interrupts, and the watchdog in interval mode (watchdog mode is not supported) <span class="tag emulator">emulator</span> [ARES, component/processor/sh2/sh7604/timer.cpp].
- Neither connects FTOA to IRL0, so neither can show whether the TOCR flip helps.

## Open questions

- Does the reset happen without OCRB set, as Star Wars Arcade's handler assumes? Hitachi's rules say no; only a console can say for sure.
- Does OCRA = 1 (games) behave differently from Sega's OCRA = 2 on hardware?

## Sources

- [SH7604](../appendices/bibliography.md#sh7604): §11 free-running timer, §12 watchdog timer, §5.3.1, §5.3.3
- [32X-HWM](../appendices/bibliography.md#32x-hwm): §5.3 pp.87, 89
- [32X-SUP2](../appendices/bibliography.md#32x-sup2): corrective action
- [32X-TB27](../appendices/bibliography.md#32x-tb27): FTOA as IRL0, revised sample
- [MORITA-FAQ](../appendices/bibliography.md#morita-faq): FTOA and the interrupt request lines
- [32X-SVC](../appendices/bibliography.md#32x-svc): §7-1, §7-3, §7-4 schematics (FTOA, FTOB, WDTOVF and the reset path)
- [32X-TIA1](../appendices/bibliography.md#32x-tia1): pp.4, 6, Master start-up and VRES samples
- [D32XR](../appendices/bibliography.md#d32xr): crt0.s, marsnew.c, marshw.c
- [MK2](../appendices/bibliography.md#mk2): SH-2 code at `0x06000266`, `0x06000286`, `0x0600037A`, `0x06005110`, `0x060003A4`, `0x06001088`
- [AB32X](../appendices/bibliography.md#ab32x): SH-2 code at `0x0600212E`, `0x0600020E`, `0x060022B4`
- [SWA](../appendices/bibliography.md#swa): SH-2 code at `0x06000426`, `0x0600046E`, `0x0600051C`, `0x060005B2`, `0x06000928`, `0x06000AB0`, `0x06000B98`-`0x06000C0C`, `0x060022C4`; on-chip code at `0xC0000582`-`0xC0000748`
- [AU-NOTES](../appendices/bibliography.md#au-notes): disasm/sh2/master/main.s
- [PICODRIVE](../appendices/bibliography.md#picodrive): pico/32x/sh2soc.c
- [ARES](../appendices/bibliography.md#ares): component/processor/sh2/sh7604/timer.cpp
