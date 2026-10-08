# Timing tables

The timing figures from across the book, collected for quick lookup. Each table summarises a chapter, linked above it, which gives the conditions, the sources and the confidence tags. Cite the chapter, not this page. Figures are for NTSC unless marked; most come from the manuals and have not been measured on a console.

## Clocks and frames

From [System architecture](../megadrive/architecture.md#clocks) and [Holding 60 frames per second](../patterns/60fps.md#what-one-frame-holds):

| | NTSC | PAL |
|---|---|---|
| 68000 | 7.67 MHz | 7.60 MHz |
| SH-2 (each) | 23.01 MHz | 22.80 MHz |
| Z80 | 3.58 MHz | 3.55 MHz |
| Frames per second | 59.92 | 49.70 |
| Lines per frame | 262 | 313 |
| Lines of vertical blank | 38 (224-line mode) | 89 (224 lines), 73 (240 lines) |
| 68000 clocks per line | 488.6 | 488.6 |
| 68000 clocks per frame | about 128,000 | about 152,900 |
| SH-2 clocks per frame | about 384,000 | about 459,000 |

The PAL line count is <span class="tag disputed">disputed</span> ([discrepancy 8](discrepancies.md)).

## 32X memory, per access

From [Access timing per CPU](../32x/timing.md#the-figures). Clocks per word access, including the CPU's own minimum bus cycle:

| What | SH-2 clocks | 68000 clocks |
|------|-------------|--------------|
| Cartridge ROM | 8-17 | 4-9 |
| Frame buffer, read | 7-14 | 6-8 |
| Frame buffer, write | 3-5 | 4 |
| Palette, read or write | 7 and up | 6-7 and up |
| 32X VDP registers, read | 7 | 6 |
| 32X VDP registers, write | 7 | 4 |
| System registers and communication ports | 3 | 4 |
| Boot ROM | 3 | — |
| SDRAM | 12 per 8-word burst read; 2 per word written | No access |

"And up" means up to a whole display line, when the VDP is reading the palette.

## SH-2: memory through the cache

From [What a 16-bit bus costs](../sh2/bsc.md#what-a-16-bit-bus-costs) and [Cache discipline](../patterns/cache.md#what-a-read-costs-through-each-view):

| Access | Bus clocks |
|--------|------------|
| Cache hit, or on-chip RAM | 0 |
| Cache line (16 bytes) from SDRAM | 12 |
| Cache line from cartridge ROM | 64-136 |
| Cache-through read from SDRAM, any size | 12 |
| Cache-through word from cartridge | 8-17 |

Per byte read: SDRAM cached 0.75; cartridge cached 4-8.5; cartridge cache-through 8-17 by bytes, 4-8.5 by words.

## SH-2 instructions

From [What each instruction costs](../sh2/pipeline.md#what-each-instruction-costs), with nothing in the way:

| Instructions | Clocks |
|--------------|--------|
| Register moves, arithmetic, logic, shifts, `DT`, `DIV1`, `NOP` | 1 |
| Loads and stores | 1, plus memory time |
| `BT`, `BF` | 3 taken, 1 not |
| `BT/S`, `BF/S` | 2 taken, 1 not |
| `BRA`, `BSR`, `BRAF`, `BSRF`, `JMP`, `JSR`, `RTS` | 2 |
| `MULS.W`, `MULU.W` | 1-3 |
| `DMULS.L`, `DMULU.L`, `MUL.L` | 2-4 |
| `MAC.W` | 3 (2 next to other multiplier instructions) |
| `MAC.L` | 3 (2-4 next to other multiplier instructions) |
| `STC.L` to memory | 2 |
| `LDC.L` from memory | 3 |
| `AND.B`, `OR.B`, `TST.B`, `XOR.B` `#imm,@(R0,GBR)` | 3 |
| `TAS.B` | 4 |
| `RTE` | 4 |
| `TRAPA` | 8 |

Extra costs ([Where the clocks go](../sh2/pipeline.md#where-the-clocks-go)):

| Situation | Cost |
|-----------|------|
| A fetch that misses the cache | The line fill: 12 from SDRAM, 64-136 from the cartridge |
| A load or store at an address of the form 4*n* + 2, running from the cache | 1 clock |
| Using a loaded register in the next instruction | 1 clock |

## SH-2 division

From [Division unit](../sh2/divu.md#timing):

| Divide | Clocks |
|--------|--------|
| Division unit, 32/32 or 64/32 | 39 from the write that starts it; reads of the unit wait until it finishes, other work continues |
| Division unit, overflow | 6 |
| `DIV0U` and 16 `DIV1` steps, 16-bit quotient (Mortal Kombat II) | about 20, plus the call |

## 68000

From [The 68000 for Mega Drive work](../megadrive/m68k.md#instruction-costs-that-matter-in-hot-loops), Motorola's figures with four-clock memory cycles:

| Instruction | Clocks |
|-------------|--------|
| `NOP`, register `MOVE`, `ADD`, `MOVEQ` | 4 |
| `MOVE.W (An)+,(An)` | 12 |
| `Bcc` taken / not taken | 10 / 8 (byte offset) |
| `DBcc` looping / count expired | 10 / 14 |
| Shift a register by *n* | 6 + 2*n* (word), 8 + 2*n* (long) |
| `MULU`, `MULS` (16 × 16) | 38 + 2*n*, at most 70 |
| `DIVU.W` | at most 140 |
| `DIVS.W` | at most 158 |
| Taking an interrupt | 44 |

## Mega Drive VDP

From [How much fits in a frame](../megadrive/vdp-dma.md#how-much-fits-in-a-frame) and [When the CPU can get in](../megadrive/vdp.md#when-the-cpu-can-get-in):

| | 32 columns, display | 32 columns, blank | 40 columns, display | 40 columns, blank |
|---|---|---|---|---|
| 68000 → VRAM by DMA, bytes per line | 16 | 167 | 18 | 205 |
| VRAM fill, bytes per line | 15 | 166 | 17 | 204 |
| VRAM copy, bytes per line | 8 | 83 | 9 | 102 |
| CPU access slots per line | 16 | 167 | 18 | 205 |

DMA from 68000 memory to VRAM in one NTSC vertical blank, 40 columns: about 7,380 bytes. In PAL: about 17,835 bytes with 28 rows, 14,555 with 30.

The line interrupt lets a handler change registers for the next line; the VDP reads what it needs within about 36 68000 clocks of the interrupt ([The line interrupt](../megadrive/vdp-timing.md#the-line-interrupt)).

## 32X VDP

From [Auto fill](../32x/vdp.md#auto-fill):

| Operation | Cost |
|-----------|------|
| Auto fill of *n* words | 7 + 3*n* SH-2 clocks; a full 256-word block about 775 clocks, 34 µs |
| Clearing a 320 × 224 packed-pixel screen by auto fill | about 4.7 ms |
| The same clear by one SH-2, a word per write | 107,520 clocks |
| The same screen written by the 68000 | at least 143,360 68000 clocks, 18.7 ms |
| DRAM refresh | FEN reads 1 for 40 clocks |
| FS flip | Takes effect at the next vertical blank |

## Moving data between the CPUs

From [DREQ and the FIFO](../32x/fifo.md#what-it-costs), [Communication](../32x/communication.md) and [Moving data](../patterns/streaming.md#the-paths):

| Path | Cost |
|------|------|
| FIFO, 68000 unrolled loop, no FULL check | 12 68000 clocks per word, about 1.25 MB/s |
| FIFO, 68000 loop checking FULL every four words | about 21.5 68000 clocks per word, about 700 KB/s |
| Communication port, one round trip from the 68000 to an SH-2 and back | about 560 68000 clocks, in Aerobiz Ultimate's measurement in PicoDrive |

## PWM

From [Cycle, sample rate and resolution](../32x/pwm.md#cycle-sample-rate-and-resolution):

| | Value |
|---|---|
| Sample rate | SH-2 clock / (cycle − 1) |
| Cycle for a rate | SH-2 clock / rate + 1 |
| 22,050 Hz, NTSC | cycle 1,045, pulse widths 1-1,045 |
| FIFO depth | 3 samples, 136 µs at 22 kHz |

## Interrupts

From [Interrupt controller](../sh2/intc.md) and [Timing, interrupts and counters](../megadrive/vdp-timing.md):

| Rule | Figure |
|------|--------|
| SH-2: between clearing an external interrupt (write, then read back) and `RTE` | at least one instruction; at least four if the mask is lowered with `LDC` to allow nesting |
| 68000: the last line interrupt before vertical blank, with an interrupt on every line | about 14.7 µs before the vertical interrupt |

## Sources

The chapters linked above. The underlying sources are mainly [32X-HWM](../appendices/bibliography.md#32x-hwm) §3.3 and §4.4; [SH-PM](../appendices/bibliography.md#sh-pm) §7; [SH7604](../appendices/bibliography.md#sh7604) §7, §8, §10; [MD-SWM](../appendices/bibliography.md#md-swm) §2.1, §2.3, §2.7; [M68K-PRM](../appendices/bibliography.md#m68k-prm); [M68K-UM](../appendices/bibliography.md#m68k-um) §8.
