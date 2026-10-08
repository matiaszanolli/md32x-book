# DMA controller

Each SH-2 has a two-channel DMA controller (DMAC) that copies data without the CPU. On the 32X it has three jobs. Channel 0 takes the data the 68000 pushes into the FIFO; channel 1 can feed the PWM sound hardware; and either channel can copy memory to memory while the CPU works from its cache. This chapter covers the registers, how a transfer is started and ended, how it shares the bus, how it interacts with the cache, Sega's rules, and the settings used by the programs read for this book.

**Shipped games hardly use it, in the sample read so far.** The 32X library has 34 cartridges, and 40 games counting the six that also need the Mega-CD [WP-32XLIST]. Five have been read for this book: Star Wars Arcade, Mortal Kombat II, After Burner Complete, Motocross Championship and Knuckles' Chaotix. Of those five, only Knuckles' Chaotix arms a DMA channel, and only channel 0 for the FIFO, with Sega's settings ([Knuckles' Chaotix: command lists](../32x/fifo.md#knuckles-chaotix-command-lists)) [CHAOTIX, SH-2 code at `0x06001334`]. Star Wars Arcade, Mortal Kombat II, After Burner Complete and Motocross Championship touch the DMA controller only to switch it off in their reset handlers [SWA; MK2; AB32X; MCX, SH-2 programs]. Another 26 cartridges are available but have only been scanned for VRES handler patterns, not read for DMA [32X-ROMSET]. The finding is about the five. The PWM and memory-copy settings below come from d32xr, a homebrew program; no shipped game read so far confirms them.

The 68000's side of the FIFO transfer (the DREQ registers, filling the FIFO, the `68S` bit) is in [DREQ and the FIFO](../32x/fifo.md). The PWM side is in [PWM audio](../32x/pwm.md).

## At a glance

| | |
|---|---|
| Channels | 2 per SH-2, so 4 in the machine |
| Unit | Byte, word, longword, or 16 bytes (four longword reads, then four longword writes) |
| Count | 1 to 16,777,216 units; 0 means the maximum |
| Started by | The program (auto-request), a request line (DREQ0, DREQ1), or the serial port |
| Bus use | Cycle-steal (one unit, then give the bus back) or burst (keep it to the end) |
| When done | A flag (TE), and an interrupt if asked for |
| Cache | Not updated. The DMAC reads and writes memory directly |

Sources: [SH7604 §9.1.1, §9.2, §7.11.2].

## The registers

| Register | Address | Size | Holds |
|----------|---------|------|-------|
| SAR0 | `0xFFFFFF80` | 32 | Source address; counts as the transfer runs |
| DAR0 | `0xFFFFFF84` | 32 | Destination address; counts as the transfer runs |
| TCR0 | `0xFFFFFF88` | 32 | Units left to transfer, 24 bits |
| CHCR0 | `0xFFFFFF8C` | 32 | Channel control (below) |
| SAR1, DAR1, TCR1, CHCR1 | `0xFFFFFF90-0xFFFFFF9C` | 32 | The same for channel 1 |
| VCRDMA0, VCRDMA1 | `0xFFFFFFA0`, `0xFFFFFFA8` | 32 | Vector number of the end-of-transfer interrupt, 0-127 |
| DRCR0, DRCR1 | `0xFFFFFE71`, `0xFFFFFE72` | 8 | What a channel's requests come from: 0 = its DREQ line, 1 or 2 = the serial port |
| DMAOR | `0xFFFFFFB0` | 32 | Shared by both channels (below) |

Source: [SH7604 §9.1.4]. Access DRCR0 and DRCR1 as bytes and everything else as longwords. Sega's register equates for the 32X put DRCR at `0xFFFFFFB4` and `0xFFFFFFB8` and list two extra vector registers; the SH7604 manual, d32xr and PicoDrive all use `0xFFFFFE71` and `0xFFFFFE72` <span class="tag disputed">disputed</span> [32X-SUP2, equates; D32XR, 32x.h; PICODRIVE, pico/32x/sh2soc.c; [discrepancy 19](../appendices/discrepancies.md)].

### CHCR: one channel's settings

| Bits | Name | Meaning |
|------|------|---------|
| 15-14 | DM | Destination: 00 fixed, 01 increment, 10 decrement |
| 13-12 | SM | Source: 00 fixed, 01 increment, 10 decrement. In 16-byte units the source always increments |
| 11-10 | TS | Unit: 00 byte, 01 word, 10 longword, 11 16 bytes |
| 9 | AR | 1 = auto-request (start at once). 0 = wait for requests (DREQ line or serial port) |
| 8 | AM | Which cycle the acknowledge signal goes with; the 32X does not use it |
| 7 | AL | Acknowledge signal polarity; the 32X does not use it |
| 6 | DS | Request line: 0 = level, 1 = edge |
| 5 | DL | Request line: 0 = low or falling, 1 = high or rising |
| 4 | TB | 0 = cycle-steal, 1 = burst |
| 3 | TA | 0 = dual address (read from SAR, write to DAR). 1 = single address, for devices with an acknowledge pin |
| 2 | IE | 1 = interrupt when the transfer ends |
| 1 | TE | Set when TCR reaches 0. Clear it by reading it as 1 and writing 0 |
| 0 | DE | 1 = channel enabled |

Source: [SH7604 §9.2.4]. The upper 16 bits read 0; write them as 0.

The values used on the 32X below (`$44E0`, `$18E5`, `$14E5`, `$5EE1`) all have bit 7 (AL) set. It does nothing there: AM and AL only shape the acknowledge signal, and the 32X leaves both CPUs' acknowledge pins unconnected [32X-SVC §7-3]. In an auto-request transfer DS and DL have no effect either, since no request line is used.

Hitachi's manual contradicts itself on the request line's edge. The CHCR description and Table 9.5 say DS = 1 with DL = 1 is the rising edge; the paragraph just above Table 9.5 says DL = 1 is the falling edge [SH7604 §9.2.4, §9.3.2 p.248]. Sega's 32X manual only says to use edge detection, not level [32X-HWM p.64]; the setting Sega and every 32X program use has DS = DL = 1, so that is what works, whatever it is called.

### DMAOR: both channels

| Bit | Name | Meaning |
|-----|------|---------|
| 3 | PR | 0 = channel 0 first. 1 = round-robin, alternating after each unit |
| 2 | AE | Set by an address error in a DMA transfer; stops both channels. Clear by reading 1 and writing 0 |
| 1 | NMIF | Set by an NMI; stops both channels. The 32X ties NMI off, so it should stay 0 |
| 0 | DME | Master enable for both channels |

Source: [SH7604 §9.2.7; 32X-HWM §5.3 p.87]. The bit diagram in Hitachi's manual calls bit 0 "DMIE"; the description below it, and every other mention, call it DME [SH7604 §9.2.7 p.243].

## Running a transfer

A channel moves data when **all** of these hold: DE = 1 in its CHCR, DME = 1 in DMAOR, TE = 0, and NMIF = AE = 0 [SH7604 §9.3.1]. In practice:

1. Make sure the channel is idle: DE = 0. If TE is still set from the last transfer, read CHCR and write it back with TE = 0.
2. Write SAR, DAR and TCR.
3. Write CHCR with everything except DE.
4. Set DME in DMAOR if it is not already set.
5. Write CHCR again with DE = 1. An auto-request transfer starts at once; a request-driven one waits for requests.
6. Wait for TE, or take the end-of-transfer interrupt.

**Counting.** TCR counts units, except in 16-byte mode, where it counts longwords: set it to 4 × the number of 16-byte blocks [SH7604 §9.2.3]. In 16-byte mode the source must be on a 16-byte boundary [SH7604 §9.2.1].

**Ending.** A transfer ends normally when TCR reaches 0: TE is set, and if IE = 1 the CPU gets an interrupt. Clearing DE stops one channel; clearing DME stops both at the end of the current bus cycle. In both cases TE stays 0, so a program that waits for TE after stopping a transfer waits for ever [SH7604 §9.3.8]. The interrupt's priority is set in bits 11-8 of the interrupt controller's IPRA register, shared by both channels, and its vector number in VCRDMA [SH7604 §5.3.1, Table 5.4; §9.2.5]. See [Interrupt controller](intc.md).

**Priority.** When both channels want the bus, channel 0 goes first unless PR selects round-robin. A higher-priority channel can cut into a lower-priority burst [SH7604 §9.3.3, §9.3.4].

## Sharing the bus

A DMA transfer is a bus master like the CPU, and inside each SH-2 it outranks the CPU [SH7604 §7.10]. Its cycles cost the same as the CPU's, with the same wait states [SH7604 §9.3.5]. See [Bus controller and memory timing](bsc.md).

- **Cycle-steal** gives the bus back after every unit, so the CPU (and the other SH-2) can get in between units.
- **Burst** keeps the bus until the transfer ends. The CPU can still run from its cache, but every cache miss, every write and every register access waits for the whole transfer. So does refresh, which Hitachi warns about for long bursts [SH7604 §9.3.4].
- **The other SH-2 may still get in during a burst.** Hitachi's DMA chapter says a burst keeps the bus to the end [SH7604 §9.3.4 p.256]. Its bus arbitration section says a chip in master mode hands the bus to an outside request at the end of any bus cycle, except in the middle of a cache fill or a 16-byte DMA unit [SH7604 §7.10 p.202]. Read together, a burst on the Master locks out its own CPU but should give way to the Slave between units <span class="tag manual">manual</span>. Sega says only that when both SH-2s run DMA at once, one of them crawls until the other finishes [32X-HWM §5.3 p.86].
- **The CPU and DMA overlap only through the cache.** While a transfer runs, a CPU working from cache hits and on-chip RAM loses nothing; the moment it needs the bus, it competes [SH7604 §9.1.1, §7.10].

**Use 16-byte units from SDRAM.** The SDRAM always reads a 16-byte burst. A DMA that reads it in words or longwords pays for a burst per unit and throws most of it away; in 16-byte units, every burst is used [SH7604 §7.5.4; 32X-HWM §4.4 p.78]. Hitachi recommends 16-byte units on 16-byte boundaries whenever SDRAM is the source [SH7604 §7.5.4]. d32xr's video player copies its decoded frames this way: auto-request, 16-byte units, cycle-steal [D32XR, marsroq.c].

## DMA and the cache

The DMAC writes memory, never the cache, so after a transfer into cached memory the CPU can still see the old data [SH7604 §7.11.2, §8.5.2]. Three ways to handle it, all covered in [Cache](cache.md#keeping-the-views-in-step):

- **Purge the destination** once the transfer has ended (TE set): single lines for a small buffer, the whole cache for a large one [SH7604 §8.5.2, §8.5.3].
- **Write to the cache-through address** and read the data the same way. d32xr points its FIFO transfers at the cache-through alias of the destination [D32XR, marshw.c].
- **Stop the cache holding data** (CCR bit OD), which Hitachi suggests for programs that DMA a lot [SH7604 §8.5.2].

The DMAC cannot reach the cache's on-chip RAM at `0xC0000000`; only the CPU can [SH7604 §7.11.2].

## What the 32X wires to it

The 32X connects two request lines, and Sega allows each one a single use, in dual address mode [32X-HWM p.64, DMA; §3.2.1, PWM control register]:

| Line | From | Used for |
|------|------|----------|
| DREQ0 | The 68000-to-SH-2 FIFO at `0x20004012` | Channel 0: data written by the 68000, into SDRAM |
| DREQ1 | The PWM sound hardware, when bit RTP of the PWM control register is set | Channel 1: samples into the PWM registers |

**Both lines reach both SH-2s.** The service manual's schematic connects the board's two request lines, `-SHDREQ0` and `-SHDREQ1`, to the DREQ0 and DREQ1 pins of the Master and of the Slave alike, and leaves both CPUs' acknowledge pins (DACK0, DACK1) unconnected <span class="tag manual">manual</span> [32X-SVC §7-3]. A request therefore reaches whichever SH-2 has a channel armed for it, and both would answer it if both were armed, so arm each line on one CPU only. With no acknowledge pins, single address mode has nothing to talk to; PicoDrive flags any attempt as an anomaly <span class="tag emulator">emulator</span> [PICODRIVE, pico/32x/sh2soc.c]. PicoDrive also gives each request to whichever SH-2 has the matching channel armed, and the programs we have read arm each line on one CPU only: the FIFO on the Master in d32xr, PWM on the Slave in d32xr's video player <span class="tag emulator">emulator</span> [PICODRIVE, pico/32x/sh2soc.c; D32XR, marshw.c, marsroq.c]. Of the retail games, Knuckles' Chaotix arms DREQ0 on the Master and none arms DREQ1. Star Wars Arcade, Mortal Kombat II, After Burner Complete and Motocross Championship arm neither; apart from switching DMA off in their reset handlers, they never touch the DMA controller [CHAOTIX, SH-2 code at `0x06001334`; SWA; MK2; AB32X; MCX, SH-2 programs].

### Channel 0: the FIFO

Sega's setting, which d32xr and Knuckles' Chaotix use:

| Register | Value |
|----------|-------|
| SAR0 | `0x20004012`, the FIFO register (fixed) |
| DAR0 | Destination in SDRAM |
| TCR0 | Number of words, from the DREQ length register at `0x20004010` |
| CHCR0 | `$44E0`, then `$44E1` to start: word units, destination incrementing, source fixed, request on the line's edge, cycle-steal, dual address, no interrupt (AL also set, with no effect) |
| DMAOR | 1 |

Sources: [32X-HWM §5.3, DMA controller settings; D32XR, marshw.c; CHAOTIX, SH-2 code at `0x06001334`].

Knuckles' Chaotix sends the Master its command lists this way, up to 1 KB each, plus an occasional four-word message ([Knuckles' Chaotix: command lists](../32x/fifo.md#knuckles-chaotix-command-lists)). The Master's CMD handler flips TOCR (Sega's interrupt workaround), clears CMD, and arms channel 0 with exactly the values above, taking TCR0 from the DREQ length register [CHAOTIX, SH-2 code at `0x06001334`-`0x06001362`].

The 68000 and the SH-2 have to agree on when the channel is armed. d32xr runs the exchange through communication port 0, bumping its value at each step [D32XR, marshw.c]:

1. The 68000 asks, with the length in words in another port.
2. The SH-2 picks a destination, or refuses.
3. It waits until the 68000 has set `68S`.
4. It rounds the length up to a multiple of four words (the FIFO's unit), and arms channel 0 with the cache-through address of the destination.
5. Once TE is set, it clears it by writing `$44E0` back to CHCR0, not 0, and acknowledges through the port. Clearing it with 0 has been blamed for transfers that stall on a console ([DREQ and the FIFO](../32x/fifo.md#how-it-fails)).

[DREQ and the FIFO](../32x/fifo.md) has the 68000's half.

**Reset button.** When the reset button is pressed, Sega's VRES handler turns DMA off (DMAOR = 0) and clears CHCR0, so a transfer cut off half-way cannot carry on into the restarted program. The sample then means to write `$44E0` to CHCR0, but loads `$44E0` into the register that holds CHCR0's address and stores 0 through it: the write goes to address `0x000044E0` and CHCR0 stays 0. Star Wars Arcade, Mortal Kombat II and Motocross Championship copy the slip exactly, on both CPUs; [Sega's sample code in the games](../appendices/sample-code.md) follows it through the library. The channel ends up disabled either way; what, if anything, answers at `0x000044E0` is not documented <span class="tag manual">manual</span> [32X-TIA1 p.6, checked on the scan]. The addresses are those of the slipped pointer load in each CPU's handler, Master first for the first two games [SWA, SH-2 code at `0x060005A4`, `0x06000608`; MK2, `0x06000372`, `0x06004ECA`; MCX, cartridge-resident SH-2 code at `0x02029F30`, `0x02029F6E`]. After Burner Complete has it right on both CPUs: it keeps `0xFFFFFF80` in the pointer register and writes 0 and then `$44E0` to CHCR0 at offset 12 [AB32X, SH-2 code at `0x06002280`-`0x0600228A` (Master), `0x060002A4`-`0x060002AE` (Slave)].

### Channel 1: PWM

With RTP set, the PWM hardware raises DREQ1 each time it wants another sample, and channel 1 can deliver it [32X-HWM p.64, DMA; §3.2.1, PWM control register]. d32xr's video player does this on the Slave, double-buffered: the transfer-end interrupt restarts the channel on the other buffer [D32XR, marsroq.c]:

| Register | Stereo | Mono |
|----------|--------|------|
| SAR1 | Sample buffer | Sample buffer |
| DAR1 | Left pulse width register; a longword write sets left and right together | Mono pulse width register |
| CHCR1 | `$18E5`: longwords, source incrementing, destination fixed, edge request, cycle-steal, interrupt at the end (AL set, no effect) | `$14E5`: the same with words |

[PWM audio](../32x/pwm.md) covers the PWM registers and sample formats. Its end-of-transfer handler clears TE by writing 0 to CHCR1, not the channel's settings [D32XR, marshw.c].

### Copying memory

d32xr's video player copies each decoded frame from one buffer to another with an auto-request transfer on the Master's channel 1, while channel 0 stays free for the FIFO [D32XR, marsroq.c, `roq_copyscreen`]:

| Register | Value |
|----------|-------|
| SAR1 | Source, on a 16-byte boundary |
| DAR1 | Destination (d32xr aligns it to 16 bytes as well) |
| TCR1 | 4 × the number of 16-byte blocks |
| CHCR1 | `$5EE1`: 16-byte units, source and destination incrementing, auto-request, cycle-steal, dual address, no interrupt. AL, DS and DL are set too, with no effect |
| DMAOR | 1, set once at start-up [D32XR, marshw.c] |

In 16-byte mode TCR counts longwords, not blocks, and the source must sit on a 16-byte boundary ([Running a transfer](#running-a-transfer)). The program does not wait idly: it polls TE between other work, then writes 0 to CHCR1 to clear it before starting the next copy [D32XR, marsroq.c]. It does not mask interrupts while the copy runs, against Sega's rule (below).

## Sega's rules

<span class="tag manual">manual</span> [32X-HWM p.64, DMA; §5.3 pp.86-87]:

- **Request lines in dual address mode, triggered by the edge.** Level detection is not to be used.
- **Mask interrupts on both SH-2s during an auto-request DMA.** If both SH-2s run DMA at once, one of them crawls until the other finishes.
- **No auto-request DMA if an SH-2 feeds PWM or touches the VDP in its H interrupt.** Interrupts are accepted late while an auto-request transfer runs, and the PWM write or the VDP access can miss its moment.
- **NMI is tied off** on the 32X, so NMIF should never stop a transfer.

The masking rule and the PWM and H interrupt rule name auto-request DMA without a bus mode, so they apply to cycle-steal and burst alike [32X-HWM §5.3 p.86].

d32xr's video player goes against both of those rules: the Master runs auto-request copies on its channel 1 without masking interrupts, while the Slave feeds PWM by DMA [D32XR, marsroq.c]. A likely reason it gets away with it, which has not been tested: Sega's stated reason is that interrupts reach the SH-2 running the auto-request transfer late. Here that is the Master, whose only interrupts during playback are V, which uploads a palette, and CMD, which runs the FIFO handshake [D32XR, marshw.c, `pri_vbi_handler`, `pri_cmd_handler`]. Neither has to happen at a set point in a line. The PWM samples are fed on the Slave, by request-driven DMA, with one end-of-transfer interrupt per buffer of 632 samples (about 29 ms at 22,050 Hz), not one per sample [D32XR, marsroq.c]. So the late interrupts Sega warns of fall on a CPU that has nothing urgent waiting for them. The copies also use cycle-steal mode, which gives the bus back after every 16 bytes, and that may soften the masking rule's other concern, two DMAs at once slowing each other.

## In emulators

- **PicoDrive** completes an auto-request transfer instantly, with the CPU put to sleep for it, and moves FIFO data in groups of four words. Cycle-steal and burst behave the same, and no transfer costs the other CPU anything <span class="tag emulator">emulator</span> [PICODRIVE, pico/32x/sh2soc.c].
- **Ares** also runs a transfer at once and says in its source that cycle-steal mode is ignored. It does read and write past the cache, as the chip does, so a missing purge after DMA shows as stale data <span class="tag emulator">emulator</span> [ARES, component/processor/sh2/sh7604/dma.cpp].
- **MAME** runs a transfer in steps, one unit every 2 CPU clocks, so it takes time and the CPU keeps running beside it. With TB set (burst) it halts the CPU until the transfer ends; with TB clear (cycle-steal) the CPU never waits. Its source calls the halting case cycle-stealing, the reverse of Hitachi's names. A FIFO transfer pauses while the FIFO is empty. MAME does not model the data cache at all: the cached and cache-through addresses read the same memory, so a missing purge never shows <span class="tag emulator">emulator</span> [MAME, src/devices/cpu/sh/sh7604.cpp, sh2.cpp].

Neither can tell you what a DMA costs the CPUs, or whether a program breaks Sega's rules in a way that matters.

## Open questions

- How much does an auto-request transfer delay interrupts in cycle-steal and in burst mode? Sega bans both without giving a figure.
- How fast does the FIFO path run end to end, and what limits it: the 68000's writes, the DREQ handshake or the SDRAM?
- Is a DMA copy faster than a CPU copy loop running from the cache, once Sega's rule about masking interrupts is taken into account? Is d32xr right that the rule can be ignored when the copying CPU has no urgent interrupts?
- Which retail games use DMA, and for what? Of the five read so far, only Knuckles' Chaotix does, for its command lists through the FIFO. The other 26 cartridges in the sources have not been read for it.
- Does a burst on one SH-2 hold the bus against the other for its whole length, as Hitachi's DMA chapter suggests, or give way after each unit, as its bus arbitration section suggests? Time the other SH-2's SDRAM accesses during a long burst from ROM.

## Sources

- [SH7604](../appendices/bibliography.md#sh7604): §9 (pp.231-286), §7.5.4, §7.10, §7.11.2, §5.3.1, §8.5.2
- [32X-HWM](../appendices/bibliography.md#32x-hwm): §3.2.1 PWM control register, p.64 DMA, §4.4 p.78, §5.3 pp.86-87
- [32X-SVC](../appendices/bibliography.md#32x-svc): §7-3, the SH-2s' DREQ and DACK pins
- [32X-TIA1](../appendices/bibliography.md#32x-tia1): VRES corrective program
- [32X-SUP2](../appendices/bibliography.md#32x-sup2): register equates
- [MK2](../appendices/bibliography.md#mk2): SH-2 program; VRES handlers start at `0x06000350` (Master) and `0x06004EA8` (Slave), DMA switch-off at `0x06000372`, `0x06004ECA`
- [AB32X](../appendices/bibliography.md#ab32x): SH-2 program; VRES handlers start at `0x06002260` (Master) and `0x06000288` (Slave), DMA switch-off at `0x06002280`, `0x060002A4`
- [SWA](../appendices/bibliography.md#swa): SH-2 program; VRES handlers start at `0x06000584` (Master) and `0x060005E8` (Slave), DMA switch-off at `0x060005A4`, `0x06000608`
- [MCX](../appendices/bibliography.md#mcx): cartridge-resident SH-2 code; DMA switch-off in the two VRES handlers at `0x02029F30`, `0x02029F6E`
- [CHAOTIX](../appendices/bibliography.md#chaotix): SH-2 code at `0x06001334` (CMD handler arming channel 0), 68000 code at `$0019A8`-`$0019FC`
- [D32XR](../appendices/bibliography.md#d32xr): marshw.c, marsroq.c (`roq_copyscreen`, `roq_snddma1_startdma`), 32x.h
- [MAME](../appendices/bibliography.md#mame): src/devices/cpu/sh/sh7604.cpp, sh2.cpp
- [PICODRIVE](../appendices/bibliography.md#picodrive): pico/32x/sh2soc.c
- [ARES](../appendices/bibliography.md#ares): component/processor/sh2/sh7604/dma.cpp
