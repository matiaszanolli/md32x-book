# Serial port (SCI)

Each SH-2 has one serial port, the SCI (serial communication interface). On the 32X the two ports are wired to each other and to nothing else. No shipped game or homebrew project in this book's sources uses the link, and as a data channel it is slow next to SDRAM. Its one real use is that it lets one SH-2 interrupt the other, which nothing else on the 32X does. This chapter covers the registers, the two modes, the speeds at the 32X's clock, Sega's setup code, and how to use the link as a doorbell.

## What the 32X connects

Sega's manual says only that the serial lines of the Master and the Slave are connected to each other, clock line included. One side can therefore drive the clock while the other takes it as input [32X-HWM §5.3 p.87]. Presumably each transmit line goes to the other chip's receive line. No schematic in the sources confirms this. The ports reach no connector, so a 32X cannot talk to a PC or a link cable through them.

The boot ROM clears the standby control register, so the SCI is running when your program starts [VRD-NOTES, 32X BIOS dump]. Sega forbids programs to touch that register [32X-HWM §5.3 p.87], so the port cannot be switched off.

## Registers

| Register | Address | Reset | Holds |
|----------|---------|-------|-------|
| SMR | `0xFFFFFE00` | `$00` | Mode and format (below) |
| BRR | `0xFFFFFE01` | `$FF` | Bit rate divider *N* |
| SCR | `0xFFFFFE02` | `$00` | Enables and clock source (below) |
| TDR | `0xFFFFFE03` | `$FF` | Next byte to send |
| SSR | `0xFFFFFE04` | `$84` | Status flags (below) |
| RDR | `0xFFFFFE05` | `$00` | Last byte received (read only) |

Source: [SH7604 §13.1.4 p.335]. All are bytes. Bytes go out least significant bit first.

**SMR**, the serial mode register [SH7604 §13.2.5 pp.336-338]:

| Bit | Name | Meaning |
|-----|------|---------|
| 7 | C/A | 0 = asynchronous, 1 = clocked synchronous |
| 6 | CHR | Asynchronous only: 0 = 8 data bits, 1 = 7 |
| 5 | PE | Asynchronous only: add and check a parity bit |
| 4 | O/E | 0 = even parity, 1 = odd |
| 3 | STOP | Asynchronous only: 0 = one stop bit, 1 = two |
| 2 | MP | Asynchronous only: multiprocessor format (an extra bit marks address bytes) |
| 1-0 | CKS | Clock for the rate generator: φ/4, φ/16, φ/64, φ/256 (*n* = 0-3) |

**SCR**, the serial control register [SH7604 §13.2.6 pp.339-341]:

| Bit | Name | Meaning |
|-----|------|---------|
| 7 | TIE | Interrupt when TDR is free (TXI) |
| 6 | RIE | Interrupt when a byte arrives (RXI) or a receive error happens (ERI) |
| 5 | TE | Transmitter on |
| 4 | RE | Receiver on |
| 3 | MPIE | Ignore bytes until one with the multiprocessor bit set arrives |
| 2 | TEIE | Interrupt when the last byte has gone out completely (TEI) |
| 1-0 | CKE | Clock source. 00 or 01: internal (in clocked mode the SCK pin outputs it; in asynchronous mode 00 leaves SCK unused). 10 or 11: external, taken from SCK |

**SSR**, the serial status register [SH7604 §13.2.7 pp.342-345]:

| Bit | Name | Set when |
|-----|------|----------|
| 7 | TDRE | TDR is free for the next byte |
| 6 | RDRF | RDR holds a byte not yet taken |
| 5 | ORER | A byte arrived while RDRF was still set. The new byte is lost |
| 4 | FER | Asynchronous: a stop bit was 0 |
| 3 | PER | Asynchronous: parity was wrong |
| 2 | TEND | Transmission finished with nothing waiting in TDR (read only) |
| 1 | MPB | Multiprocessor bit of the last byte received (read only) |
| 0 | MPBT | Multiprocessor bit to send with the next byte |

The flags in bits 7-3 are cleared the same way as the timer flags: read the register while the flag is 1, then write 0 to it. Writing 1 does nothing. While ORER, FER or PER is set, nothing more is received, and in clocked mode nothing is sent either. Clear them first [SH7604 §13.2.7, §13.5].

## Sending and receiving

**To send a byte:** wait for TDRE = 1, write the byte to TDR, then clear TDRE (read SSR, write it back with bit 7 at 0). Clearing TDRE is what tells the SCI the byte is there. Writing TDR while TDRE is still 0 overwrites a byte that has not yet gone [SH7604 §13.5].

**To receive a byte:** wait for RDRF = 1 (or take the RXI interrupt), read RDR, then clear RDRF.

**To set up** [SH7604 §13.3.4 pp.373-374] <span class="tag manual">manual</span>:
1. Clear TE and RE in SCR.
2. Write SMR, then BRR.
3. Write SCR with the clock source, and TE, RE and the interrupt enables still 0.
4. Wait at least one bit time, then set TE and/or RE and the interrupt enables.

Both directions have a one-byte buffer, so a new byte can be written while the previous one is still going out.

### Interrupts and DMA

The SCI has four interrupt sources, in this order of priority: ERI (receive error), RXI (byte received), TXI (TDR free) and TEI (transmission ended). All four share one priority level, IPRB bits 15-12. Each has its own vector, in VCRA (ERI, RXI) and VCRB (TXI, TEI) [SH7604 §13.4 p.380]. See [Interrupt controller](intc.md).

RXI and TXI can also drive a DMA channel: set the channel's DRCR to 1 (RXI) or 2 (TXI). Then the DMA reads RDR or writes TDR, and the SCI clears RDRF or TDRE itself [SH7604 §9.2.6, §13.4]. See [DMA controller](dmac.md).

## Speeds at the 32X's clock

Hitachi's formulas, with φ the CPU clock and *n* the CKS setting [SH7604 §13.2.8 pp.346-351]:

| Mode | Bit rate |
|------|----------|
| Asynchronous | φ / (128 × 4<sup>*n*</sup> × (*N* + 1)) |
| Clocked, internal clock | φ / (16 × 4<sup>*n*</sup> × (*N* + 1)) |
| Clocked, external clock | Up to φ / 24 |

At 23.01 MHz (NTSC), worked out from those formulas <span class="tag manual">manual</span>:

| Setting | Bit rate | Bytes per second | Bytes per 60 Hz frame |
|---------|----------|------------------|-----------------------|
| Asynchronous, *n* = 0, *N* = 0 (fastest), 8 data bits, 1 stop bit | 179,800 | about 18,000 | about 300 |
| Clocked, *n* = 0, *N* = 1 | 719,000 | about 89,900 | about 1,500 |
| Clocked, *N* = 74 (Sega's sample, below) | 19,200 | about 2,400 | about 40 |

A 10-bit frame (start, 8 data, stop) is assumed for the asynchronous row. *N* = 0 in clocked mode would give φ/16, but that is faster than the receiving SH-2's external-clock limit of φ/24, and Hitachi marks it as unable to run continuously [SH7604 Table 13.4 p.349, Table 13.8 p.351]. So *N* = 1 is the fastest clocked rate that should work between the two SH-2s.

For comparison, a word write to SDRAM takes 2 clocks (see [Bus controller](bsc.md#what-a-16-bit-bus-costs)). The serial link is not a way to move data in bulk.

### Which mode

- **Clocked** is the faster mode, but one side supplies the clock (CKE = 00, SCK as output) and the other takes it (CKE = 10). The clock only runs while the side that supplies it is sending or receiving. So that side decides when bytes move, and the other side cannot start a transfer.
- **Asynchronous** needs no shared clock. Each side's own rate generator times its bits, and either side can send whenever it likes, as long as both use the same SMR and BRR. With CKE = 00 both ends leave the shared clock line alone. For a link used to signal events, this is the simpler choice.

## Sega's setup code

Sega's start-up sample sets up the Master's port and leaves the Slave's alone [32X-TIA1, Master SH-2 sample, p.4] <span class="tag manual">manual</span>:

| Step | Write | Meaning |
|------|-------|---------|
| 1 | SMR = `$80` | Clocked synchronous, φ/4 |
| 2 | BRR = 74 | 19,200 bit/s at 23.01 MHz |
| 3 | SCR = `$00` | Internal clock, output on SCK; everything off |
| 4 | Delay loop, 4 × 74 passes | About 1,480 clocks, more than one bit time (1,200 clocks) |
| 5 | SCR = `$20` | Transmitter on |
| 6 | SSR = `$00` | |

This follows Hitachi's setup steps exactly, but the sample never sends a byte, and the Slave's receiver stays off. Sega does not say why the code is there. One plausible reason is to make the Master drive the shared clock line (idle high) rather than leave it floating between two inputs. The text transcription of this sample has the delay count as `#4+74`; the scan has `#4*74`.

Star Wars Arcade does not touch the SCI registers anywhere in its SH-2 program [SWA, SH-2 program], and neither does After Burner Complete [AB32X, SH-2 program]. Neither does d32xr, marsdev or Aerobiz Ultimate. The names `sci_cmd_cb` and `sci_mars_adapter` in d32xr and marsdev belong to the Slave's command interrupt, not the serial port [D32XR, marshw.c; MARSDEV, examples/32x-old-skel/boot.s]. Mortal Kombat II copies Sega's start-up sample almost word for word but leaves the serial set-up out [MK2, SH-2 code at `0x06000250`-`0x060002B8`].

## A doorbell between the SH-2s

The 32X's own interrupts (VRES, V, H, CMD, PWM) all come from the 32X hardware or the 68000. CMD in particular can only be raised by the 68000 (see [Communication](../32x/communication.md)). So the SCI's receive interrupt is the only direct way we know for one SH-2 to interrupt the other:

1. On both SH-2s: set the same asynchronous format and rate, for example SMR = `$00` and BRR = 0, then wait a bit time and turn on TE and RE. On the side that should be woken, also set RIE, give the SCI a priority in IPRB and a receive vector in VCRA.
2. To ring: wait for TDRE = 1, write a byte to TDR, clear TDRE. The byte can carry a command number.
3. In the other SH-2's receive handler: read RDR, clear RDRF (and any error flag), and act on the command. Real work data still goes through SDRAM or the communication ports.

At the fastest asynchronous rate each bit takes 128 CPU clocks, so a 10-bit frame takes 1,280 clocks, about 56 µs, before the other side's interrupt fires. Allow for that delay. This scheme is a suggestion worked out from the manual. No program in the sources does it, and it has not been tried on a console.

## In emulators

- **PicoDrive and Ares** both connect the two SH-2s' ports. When the sender's transmitter is on, its TDRE is cleared and the receiver's RE is set, the byte appears in the other SH-2's RDR at once, RDRF is set, and the interrupts fire if enabled <span class="tag emulator">emulator</span> [PICODRIVE, pico/32x/sh2soc.c; ARES, component/processor/sh2/sh7604/serial.cpp, md/m32x/m32x.cpp].
- Neither models the bit rate, the mode, the clock line, or overrun: a second byte simply replaces an unread one, with no ORER. Code that works in either can still lose bytes or run too fast on a console.
- PicoDrive does not raise TEI, and it takes the transmit interrupt's priority and vector from the other SH-2's registers instead of the sender's [PICODRIVE, pico/32x/sh2soc.c].

## Open questions

- Is each SH-2's transmit line wired to the other's receive line, as assumed here? Is there a pull-up on the shared clock line?
- Why does Sega's sample enable the Master's transmitter? Does the Slave's SCK need the Master to drive it?
- Does a byte sent between the two SH-2s arrive reliably at the fastest asynchronous and clocked rates on a console?

## Sources

- [SH7604](../appendices/bibliography.md#sh7604): §13 pp.333-383, §9.2.6 DRCR, §14.2.1 standby control register
- [32X-HWM](../appendices/bibliography.md#32x-hwm): §5.3 p.87
- [32X-TIA1](../appendices/bibliography.md#32x-tia1): Master SH-2 sample, p.4
- [VRD-NOTES](../appendices/bibliography.md#vrd-notes): 32X BIOS dump
- [MK2](../appendices/bibliography.md#mk2): SH-2 start-up code
- [AB32X](../appendices/bibliography.md#ab32x): SH-2 program
- [SWA](../appendices/bibliography.md#swa): SH-2 program
- [D32XR](../appendices/bibliography.md#d32xr): marshw.c
- [MARSDEV](../appendices/bibliography.md#marsdev): examples/32x-old-skel/boot.s
- [PICODRIVE](../appendices/bibliography.md#picodrive): pico/32x/sh2soc.c
- [ARES](../appendices/bibliography.md#ares): component/processor/sh2/sh7604/serial.cpp, md/m32x/m32x.cpp
