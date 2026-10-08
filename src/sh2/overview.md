# The SH7604 at a glance

The 32X has two Hitachi SH7604s. Each is an SH-2 CPU core with cache, multiplier, divider, DMA controller, timers, interrupt controller and serial port on the same chip. This chapter is the map for Part II. It shows what is inside the chip, which parts the 32X connects to what, what Sega forbids, where a 32X program's time actually goes, and what the emulators leave out. Each part has its own chapter. This one says where to look.

## What is inside

| Block | What it does | On the 32X | Chapter |
|-------|--------------|-----------|---------|
| CPU core | 32-bit RISC, 16 general registers, fixed 16-bit instructions, delayed branches, five-stage pipeline | Runs at 23.01 MHz (NTSC), three times the 68000's clock | [Registers and instruction set](isa.md), [Pipeline](pipeline.md) |
| Multiplier | 16 × 16 and 32 × 32 multiplies and multiply-accumulate into MACH:MACL | Used for all fixed-point maths | [Multiplies](isa.md#multiplies), [The multiplier](pipeline.md#the-multiplier) |
| Cache | 4 KB, four-way, write-through; or 2 KB of cache plus 2 KB of fast RAM | Decides most of the CPU's speed; does not see the other CPU's writes | [Cache](cache.md) |
| Bus state controller (BSC) | Drives the external bus: four areas, wait states, SDRAM, refresh, bus sharing | Set up by the boot ROM; programs may not change it | [Bus controller](bsc.md) |
| DMA controller (DMAC) | Two channels that copy memory without the CPU | Channel 0 drains the 68000 FIFO; PWM can request channel 1 | [DMA controller](dmac.md) |
| Division unit (DIVU) | 32/32 and 64/32 signed divide in 39 clocks, alongside the CPU | Free to use | [Division unit](divu.md) |
| Free-running timer (FRT) | 16-bit counter with two compare outputs | Reserved for Sega's interrupt workaround and the VRES reset | [Timers](timers.md) |
| Watchdog timer (WDT) | 8-bit counter, interval or reset mode | Interval mode only | [Timers](timers.md#the-watchdog-timer) |
| Interrupt controller (INTC) | Priorities and vectors for external and on-chip interrupts | The 32X's five interrupts arrive on its external lines | [Interrupt controller](intc.md) |
| Serial port (SCI) | Asynchronous or clocked serial | Wired only to the other SH-2 | [Serial port](sci.md) |
| User break controller (UBC) | Two hardware breakpoints on address, data and access type, raising an interrupt at level 15 (vector 12) | No program in the sources sets a breakpoint; After Burner Complete uses its registers as spare storage | (below) |

Sources: [SH7604 §1.1; 32X-HWM §3.3, clock; 32X-OV, dual SH2's].

**The user break controller** has no chapter because no program in the sources uses it for breakpoints. On a console it could serve as a hardware watchpoint: it can raise an interrupt when the CPU or the DMA touches a chosen address [SH7604 §6.1; §4, Tables 4.3, 4.8]. This has not been tried on a 32X. One retail game does use its registers, though not as breakpoints. After Burner Complete's Slave keeps the read and write positions of its sound ring buffer in BARAH and BARAL (`0xFFFFFF40`, `0xFFFFFF42`) and a sample counter in BARBH (`0xFFFFFF60`). With the bus cycle registers at their reset value 0, no break condition can match, so these are spare on-chip words the Slave reads without a bus cycle [SH7604 §6.1.3; AB32X, SH-2 code at `0x0600032E`, `0x060003C0`, `0x06000390`].

## How the 32X wires the chip

Both SH-2s are the same part. Pins sampled at reset make one the Master and the other the Slave, and the 32X board connects the rest. What the sources say about each connection:

| Pins | 32X connection | Source |
|------|----------------|--------|
| MD2-MD0 (clock mode) | Mode 5 on both: the clock arrives on CKIO from the board's SHCLK line at full speed, and PLL circuit 1 runs the internal clock 90° behind it | [32X-SVC §7-3; SH7604 §3.2.2, Table 3.3] |
| MD4-MD3 (area 0 width) | 16 bits | [32X-SVC §7-3; SH7604 §3.3, Table 3.9]; see [Bus controller](bsc.md#the-four-areas-on-the-32x) |
| MD5 (bus mode) | Master in master mode, Slave in slave mode: one external bus, the Slave asks the Master for it | [SH7604 §3.4; 32X-SVC §7-3]; see [Two SH-2s, one bus](bsc.md#two-sh-2s-one-bus) |
| CS0-CS3 (areas) | Boot ROM and registers, cartridge, frame buffer, SDRAM | [32X-HWM §3.1]; see [the SH-2 memory map](../32x/architecture.md#the-sh-2-memory-map) |
| IRL3-IRL1 | The 32X's interrupts: VRES, V, H, CMD, PWM, on a separate set of lines for each CPU (IRL0 is FTOA, below) | [32X-HWM §3.2.2; 32X-SVC §7-3]; see [Interrupt controller](intc.md#the-32xs-five-interrupts) |
| NMI | Tied high: no NMI on the 32X | [32X-HWM §5.3 p.87] |
| DREQ0, DREQ1 | The 68000 → SH-2 FIFO, and the PWM timer | [32X-HWM §5.3, DMA controller settings; p.64]; see [DMA controller](dmac.md) |
| FTOA | Wired to the same CPU's /IRL0, the low bit of the interrupt level. Toggled by every interrupt handler as Sega's workaround for the interrupt flaw | [32X-SUP2; 32X-TB27; 32X-SVC §7-3]; see [Interrupt controller](intc.md#how-the-tocr-flip-works) |
| FTOB | Master: drives the 32X's reset line, which the Master uses after VRES when RV = 1. Slave: not connected | [32X-TIA1 pp.4, 6; 32X-SVC §7-3, §7-4]; see [Timers](timers.md#ftob-and-the-vres-reset) |
| TxD, RxD, SCK | Master and Slave connected to each other, clock included | [32X-HWM §5.3 p.87]; see [Serial port](sci.md) |
| WDTOVF, DACK0/1, IVECF, CKPACK | Not connected, on either CPU | [32X-SVC §7-3] |
| FTI, FTCI | Tied to ground, so the timer has no external clock or capture input | [32X-SVC §7-3] |
| CKPREQ | Tied high: the clock is never paused | [32X-SVC §7-3] |

The SH-2 clock comes from the Mega Drive's master clock, divided by 7 and multiplied by 3 [32X-HWM §3.3, clock]. The board makes that clock and feeds it to both CPUs' CKIO pins, so neither SH-2 multiplies it: clock mode 5 only aligns the phase [32X-SVC §7-3; SH7604 §3.2.2]. See [Architecture](../32x/architecture.md#the-parts).

## The address space

The SH-2 uses the top three bits of an address to choose what an access does: cached, cache-through, cache purge, cache tags, cache data as RAM, or on-chip registers. Every piece of 32X memory therefore has a cached address (`0x0…`) and a cache-through address (`0x2…`). Which one a program uses is a question of correctness: anything another processor can change must be read through the cache-through address. The on-chip registers sit at `0xFFFFFE00`-`0xFFFFFFFF` [SH7604 §7.1.5, §8.3]. The full tables are in [The SH-2 memory map](../32x/architecture.md#the-sh-2-memory-map) and [How an address finds its line](cache.md#how-an-address-finds-its-line).

## What Sega forbids or reserves

| Rule | Why | Chapter |
|------|-----|---------|
| Do not change the bus controller registers | The boot ROM's settings match the board | [Bus controller](bsc.md#hands-off) |
| Do not change the standby control register (`0xFFFFFE91`) | Same list. It can stop on-chip modules and put the chip in standby | [Cache](cache.md#the-control-register) |
| Do not use the watchdog's reset mode | | [Timers](timers.md#the-watchdog-timer) |
| Do not use `SLEEP` | Not given. The boot ROMs use it while waiting for the 68000; no game in the sources does | [Registers and instruction set](isa.md) |
| Do not reset the 32X manually; NMI is tied high | | [Boot](../32x/boot.md#pressing-reset) |
| Leave the FRT alone after setting it up as Sega specifies | It carries the interrupt workaround | [Timers](timers.md#what-sega-asks-for-and-what-games-do) |
| Flip TOCR bit 1 in every interrupt handler | The SH-2 interrupt flaw | [Interrupt controller](intc.md#segas-rules-the-sh-2-interrupt-flaw) |
| Do not use TAS <span class="tag disputed">disputed</span> ([row 12](../appendices/discrepancies.md)) | Not given | [Communication](../32x/communication.md#between-the-two-sh-2s) |
| Access system registers through cache-through addresses | The cache would hold stale copies | [Cache](cache.md#keeping-the-views-in-step) |

Sources: [32X-HWM §5.3 pp.87-89; 32X-SUP2].

## Where the time goes

In rough order of how much they cost a typical 32X program:

1. **Cache misses and the shared bus.** A missed line costs 12 clocks from SDRAM and up to 136 from cartridge ROM. While one SH-2 fills a line, the other waits for the bus. Keep hot code and data in SDRAM and in the cache, and keep the two CPUs' working sets apart. See [Bus controller](bsc.md) and [Cache](cache.md).
2. **Stale data between the CPUs.** This is not slowness but wrong results. The cache never sees the other SH-2's writes or the DMA's. See [Keeping the views in step](cache.md#keeping-the-views-in-step).
3. **Frame buffer and register accesses.** A frame buffer read takes 7 to 14 clocks. Writes go through the one-entry write buffer and are cheap only when spaced out. See [What a 16-bit bus costs](bsc.md#what-a-16-bit-bus-costs).
4. **Divides, and shifts gcc turns into library calls.** A `DIVU` divide costs 39 clocks unless it overlaps other work. A signed `>> 8` in C becomes a function call. See [Division unit](divu.md) and [Shifts without a barrel shifter](isa.md#shifts-without-a-barrel-shifter).
5. **Pipeline details.** Loads used too soon, multiplies read too soon, memory accesses colliding with fetches. These are worth a clock or two each, but they add up in inner loops. See [Pipeline](pipeline.md).

## In emulators

What the two emulators the book's projects use model, in brief:

| Feature | PicoDrive | Ares | Chapter |
|---------|-----------|------|---------|
| Cache | None: a missing purge never shows | Real data lines, 12 clocks per fill | [Cache](cache.md#in-emulators) |
| Bus timing | Almost none | Fixed cost per access; no waiting for the other SH-2 | [Bus controller](bsc.md#emulators-do-not-show-this) |
| Instruction timing | Fixed count per instruction, no pipeline effects | 1 clock per instruction, no pipeline effects | [Pipeline](pipeline.md#in-emulators) |
| Divider | Instant; divide by zero gives 0 with OVF clear | Instant; divide by zero gives `$7FFFFFFF` for any sign (a Saturn test expects the limit with the dividend's sign) | [Division unit](divu.md#in-emulators) |
| Free-running timer | Registers stored, counter not run | Counter runs | [Timers](timers.md#in-emulators) |
| FTOA, FTOB | Not connected | Not connected | [Timers](timers.md#in-emulators) |
| Branch in a delay slot | Runs | Raises slot-illegal, as the hardware does | [Instruction set](isa.md#in-emulators) |
| Serial link | Instant, no bit rate | Instant, no bit rate | [Serial port](sci.md#in-emulators) |

So neither emulator can confirm timing, and only Ares shows cache bugs. Claims in Part II that come only from emulators are tagged <span class="tag emulator">emulator</span>. Nothing in Part II has been measured on a console for this book yet.

## Reading order

For someone new to the SH-2: [Registers and instruction set](isa.md), then [Cache](cache.md) and [Bus controller](bsc.md), which decide most performance questions, then [Interrupt controller](intc.md) for Sega's workaround. Read the rest when the need arises: the [DMA controller](dmac.md) for the FIFO and copying, the [Division unit](divu.md) and [Pipeline](pipeline.md) for inner loops, [Timers](timers.md) for profiling, the [Serial port](sci.md) for SH-2 to SH-2 signalling.

## Sources

- [SH7604](../appendices/bibliography.md#sh7604): §1.1, §3.2.2, §3.3, §3.4, §4 Tables 4.3 and 4.8, §6.1, §7.1.5, §8.3
- [32X-HWM](../appendices/bibliography.md#32x-hwm): §3.1, §3.2.2, §3.3, §5.3 pp.87-89, p.64
- [32X-OV](../appendices/bibliography.md#32x-ov): dual SH2's
- [32X-SUP2](../appendices/bibliography.md#32x-sup2): interrupt corrective action
- [32X-TB27](../appendices/bibliography.md#32x-tb27): FTOA as IRL0
- [32X-SVC](../appendices/bibliography.md#32x-svc): §7-3, SH-2 pin wiring
- [32X-TIA1](../appendices/bibliography.md#32x-tia1): pp.4, 6
- [AB32X](../appendices/bibliography.md#ab32x): SH-2 code at `0x0600032E`, `0x060003C0`
