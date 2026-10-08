# Register quick reference

The registers a 32X program touches most, on one page. Each table links to the chapter that explains the bits; check there before relying on a value marked as disputed. 68000 addresses are written `$A15100`, SH-2 addresses `0x20004000` (always the cache-through form).

## Mega Drive VDP

| Address | Read | Write |
|---------|------|-------|
| `$C00000` | Data | Data |
| `$C00004` | Status | Register word `$8rvv`, or a two-word memory command |
| `$C00008` | H/V counter | — |
| `$C00011` | — | PSG, byte writes |

| # | Name | Bits, 7 → 0 |
|---|------|-------------|
| 0 | Mode 1 | `0 0 0 IE1 0 1 M3 0` |
| 1 | Mode 2 | `0 DISP IE0 M1 M2 1 0 0` |
| 2 | Plane A table | `0 0 A15 A14 A13 0 0 0` |
| 3 | Window table | `0 0 A15-A11 0` |
| 4 | Plane B table | `0 0 0 0 0 A15 A14 A13` |
| 5 | Sprite table | `0 A15-A9` |
| 7 | Backdrop colour | `0 0 PAL1 PAL0 C3-C0` |
| 10 | Line interrupt counter | `L7-L0` |
| 11 | Mode 3 | `0 0 0 0 IE2 VSCR HSCR LSCR` |
| 12 | Mode 4 | `RS0 0 0 0 S/TE LSM1 LSM0 RS1` |
| 13 | Horizontal scroll table | `0 0 A15-A10` |
| 15 | Auto-increment | `I7-I0` |
| 16 | Plane size | `0 0 VSZ1 VSZ0 0 0 HSZ1 HSZ0` |
| 17, 18 | Window position | `RIGT 0 0 X4-X0`, `DOWN 0 0 Y4-Y0` |
| 19-23 | DMA length and source | Length L15-L0; source S22-S1; register 23 bits 7-6 the mode |

Status: 9 EMPT, 8 FULL, 7 F (vertical interrupt), 6 SOVR, 5 C, 4 ODD, 3 VB, 2 HB, 1 DMA, 0 PAL.

Sources: [MD-TO pp.22-26; MD-SWM §2.4-2.5; GENVDP §6, §17]. See [Registers and access](../megadrive/vdp-registers.md).

## 32X system registers, 68000 side

| Address | Register | Bits |
|---------|----------|------|
| `$A15100` | Adapter control | 15 FM, 7 REN (read only), 1 RES, 0 ADEN |
| `$A15102` | Interrupt control | 1 INTS, 0 INTM: raise CMD on the Slave or Master |
| `$A15104` | Bank set | 1-0: megabyte shown at `$900000` |
| `$A15106` | DREQ control | 7 FULL (read only), 2 68S, 0 RV |
| `$A15108`-`$A1510E` | DREQ source, destination | Not used by the transfer |
| `$A15110` | DREQ length | 15-2, in words |
| `$A15112` | FIFO | Write only |
| `$A1511A` | SEGA TV | 0 CM. Leave at 0 |
| `$A15120`-`$A1512E` | Communication ports | 8 words |
| `$A15130`-`$A15138` | PWM | [Below](#pwm) |

## 32X system registers, SH-2 side

| Address | Register | Bits |
|---------|----------|------|
| `0x20004000` | Interrupt mask | 15 FM; 9 ADEN, 8 CART (read only); 7 HEN (both SH-2s); 3 V, 2 H, 1 CMD, 0 PWM (one set per SH-2) |
| `0x20004002` | Standby change | Boot ROM only |
| `0x20004004` | H count | 7-0: lines between H interrupts, minus 1 |
| `0x20004006` | DREQ control | Read only: 15 FULL, 14 EMPT <span class="tag disputed">disputed</span> ([row 32](discrepancies.md)); 2 68S; 0 RV |
| `0x20004008`-`0x20004012` | DREQ addresses, length, FIFO | Read only |
| `0x20004014` | VRES clear | Write any word |
| `0x20004016` | V clear | Write any word |
| `0x20004018` | H clear | Write any word |
| `0x2000401A` | CMD clear | Write any word |
| `0x2000401C` | PWM clear | Write any word |
| `0x20004020`-`0x2000402E` | Communication ports | Same words as `$A15120` |
| `0x20004030`-`0x20004038` | PWM | [Below](#pwm) |

Interrupt levels: VRES 14, V 12, H 10, CMD 8, PWM 6.

Sources: [32X-HWM §3.2.1-3.2.2 pp.19-31; 32X-OV pp.34-43]. See [System registers](../32x/registers.md), [discrepancy 32](discrepancies.md) for bits 15-14 of `0x20004006` and [discrepancy 33](discrepancies.md) for reading RV.

## 32X VDP

| 68000 | SH-2 | Register | Bits |
|-------|------|----------|------|
| `$A15180` | `0x20004100` | Bitmap mode | 15 PAL (read only, 0 = PAL), 7 PRI, 6 240-line, 1-0 mode: 00 blank, 01 packed, 10 direct, 11 run length |
| `$A15182` | `0x20004102` | Screen shift | 0 SFT |
| `$A15184` | `0x20004104` | Auto fill length | 7-0: words minus 1 |
| `$A15186` | `0x20004106` | Auto fill start | 15-0: word address; bits 7-0 count |
| `$A15188` | `0x20004108` | Auto fill data | Writing starts the fill |
| `$A1518A` | `0x2000410A` | Frame buffer control | 15 VBLK, 14 HBLK, 13 PEN, 1 FEN (read only); 0 FS |
| `$A15200` | `0x20004200` | Palette | 256 words: bit 15 through bit, then blue, green, red in 5 bits each |

Only the side that FM gives them to may use them. Sources: [32X-HWM §3.2.3, §3.3]. See [The 32X VDP](../32x/vdp.md).

## PWM

| 68000 | SH-2 | Register | Bits |
|-------|------|----------|------|
| `$A15130` | `0x20004030` | Control | 11-8 TM (interrupt every TM samples, 0 = 16), 7 RTP (DREQ1), both written from the SH-2 only; 3-2 right output, 1-0 left output: 01 own channel, 10 the other |
| `$A15132` | `0x20004032` | Cycle | 11-0: sample period plus one, in SH-2 clocks |
| `$A15134` | `0x20004034` | Left pulse width | Write 11-0; read 15 FULL, 14 EMPTY |
| `$A15136` | `0x20004036` | Right pulse width | As left |
| `$A15138` | `0x20004038` | Mono pulse width | Writes both channels |

Sources: [32X-HWM §3.2.1 p.24, §3.4 p.57]. See [PWM audio](../32x/pwm.md).

## SH7604 on-chip registers

| Address | Register | What it is for |
|---------|----------|----------------|
| `0xFFFFFE00`-`0xFFFFFE05` | SMR, BRR, SCR, TDR, SSR, RDR | [Serial port](../sh2/sci.md) |
| `0xFFFFFE10`-`0xFFFFFE19` | TIER, FTCSR, FRC, OCRA/B, TCR, TOCR, ICR | [Free-running timer](../sh2/timers.md); TOCR is in Sega's interrupt workaround |
| `0xFFFFFE60`, `0xFFFFFEE2` | IPRB, IPRA | [Interrupt priorities](../sh2/intc.md) |
| `0xFFFFFE62`-`0xFFFFFE68`, `0xFFFFFEE4` | VCRA-VCRD, VCRWDT | On-chip interrupt vector numbers |
| `0xFFFFFE71`, `0xFFFFFE72` | DRCR0, DRCR1 | DMA request sources |
| `0xFFFFFE80`-`0xFFFFFE83` | WTCSR, WTCNT, RSTCSR | [Watchdog timer](../sh2/timers.md#the-watchdog-timer); written as words with a key byte |
| `0xFFFFFE91` | SBYCR | Standby control. Applications must not touch it |
| `0xFFFFFE92` | CCR | [Cache control](../sh2/cache.md) |
| `0xFFFFFF00`-`0xFFFFFF14` | DVSR, DVDNT, DVCR, VCRDIV, DVDNTH, DVDNTL | [Division unit](../sh2/divu.md) |
| `0xFFFFFF80`-`0xFFFFFF9C` | SAR, DAR, TCR, CHCR for channels 0 and 1 | [DMA controller](../sh2/dmac.md) |
| `0xFFFFFFA0`, `0xFFFFFFA8` | VCRDMA0, VCRDMA1 | DMA end vectors |
| `0xFFFFFFB0` | DMAOR | DMA master enable |
| `0xFFFFFFE0`-`0xFFFFFFF8` | BCR1, BCR2, WCR, MCR, RTCSR, RTCNT, RTCOR | [Bus state controller](../sh2/bsc.md). Set by the boot ROM; leave alone |

Sources: [SH7604 §5, §7-§13; 32X-HWM §5.3].
