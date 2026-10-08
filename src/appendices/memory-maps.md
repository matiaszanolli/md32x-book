# Memory maps

Every address map in the book, collected for quick reference. Each table is a summary; the chapter linked above it explains the conditions, the exceptions and the sources, and is the one to cite.

## 68000, plain Mega Drive

From [System architecture](../megadrive/architecture.md#the-68000-memory-map):

| Address | Contents |
|---------|----------|
| `$000000-$3FFFFF` | Cartridge, up to 4 MB |
| `$400000-$7FFFFF` | Expansion (the Mega-CD) |
| `$800000-$9FFFFF` | Reserved; the 32X uses it |
| `$A00000-$A0FFFF` | Z80 space, while the 68000 holds the Z80 bus; byte access only |
| `$A10000-$A1001F` | I/O: version register at `$A10001`, controller ports |
| `$A11000` | Memory mode (development hardware only) |
| `$A11100` | Z80 bus request |
| `$A11200` | Z80 reset |
| `$A130xx` | Cartridge registers: bank switching, save RAM control |
| `$A14000` | TMSS: `SEGA` written here on consoles with a non-zero version |
| `$C00000` | VDP data port (mirror `$C00002`) |
| `$C00004` | VDP control port (mirror `$C00006`) |
| `$C00008` | VDP H/V counter |
| `$C00011` | PSG |
| `$FF0000-$FFFFFF` | Work RAM, 64 KB |

## 68000, with the 32X switched on

From [Architecture and memory maps](../32x/architecture.md#the-68000-memory-map). At power-on (ADEN = 0) the map is the plain one above, plus `MARS` at `$A130EC` and the system registers at `$A15100`. After the initial program sets ADEN:

| Address | Contents | Condition |
|---------|----------|-----------|
| `$000000-$0000FF` | 32X vector ROM: each exception jumps to `$880200` + 6 × (vector − 1) | |
| `$000070` | Horizontal interrupt vector, in RAM | |
| `$000100-$3FFFFF` | Cartridge in its Mega Drive layout | RV = 1 only |
| `$840000-$85FFFF` | Frame buffer (the one not on screen) | FM = 0 |
| `$860000-$87FFFF` | Overwrite image of the same buffer | FM = 0 |
| `$880000-$8FFFFF` | Cartridge `$000000-$07FFFF`, always | RV = 0 |
| `$900000-$9FFFFF` | One 1 MB bank of the cartridge, chosen at `$A15104` | RV = 0 |
| `$A130EC` | `MARS` | |
| `$A15100-$A1517F` | System registers | |
| `$A15180-$A151FF` | 32X VDP registers | FM = 0 |
| `$A15200-$A153FF` | Palette | FM = 0; word access only |
| everything else | As on a plain Mega Drive | |

A 32X cartridge's own layout, from [Boot](../32x/boot.md#the-pieces):

| Cartridge offset | Contents |
|------------------|----------|
| `$000000` | 68000 vectors, used only before ADEN is set |
| `$000100` | Header, system name `SEGA 32X` |
| `$000200` | Jump table, 6 bytes per exception |
| `$0003C0` | User header: where the SH-2 program is and where each SH-2 starts |
| `$0003F0-$0007FF` | Sega's initial program, unchanged |
| `$000800` | The game's 68000 entry point, reached at `$880800` |

## The 32X system registers

From [System registers](../32x/registers.md#the-map-at-a-glance). The same 64 bytes appear at `$A15100` to the 68000 and at `0x20004000` to the SH-2s, with different registers at some offsets:

| Offset | 68000 | SH-2 |
|--------|-------|------|
| `$00` | Adapter control | Interrupt mask; FM is shared |
| `$02` | Interrupt control (CMD to each SH-2) | Standby change |
| `$04` | Bank set | H count |
| `$06` | DREQ control | DREQ control, read only |
| `$08`-`$10` | DREQ source, destination, length | The same, read only |
| `$12` | FIFO, write only | FIFO, read by DMA channel 0 |
| `$14`-`$1C` | `$1A`: SEGA TV | Interrupt clears: VRES, V, H, CMD, PWM |
| `$20`-`$2E` | Communication ports, eight words | The same |
| `$30`-`$38` | PWM control, cycle, left, right, mono | The same |

## Mega Drive VRAM

VRAM has no fixed layout; the registers place each table. The layout most games use, from Sega's initial program ([What lives where in VRAM](../megadrive/vdp.md#what-lives-where-in-vram)):

| VRAM | Contents | Register |
|------|----------|----------|
| `$0000-$BFFF` | Tiles, 32 bytes each | — |
| `$C000-$CFFF` | Plane A, 64 × 32 | 2 = `$30` |
| `$D800-$DA7F` | Sprite table, 80 sprites | 5 = `$6C` |
| `$DC00-$DF7F` | Horizontal scroll table | 13 = `$37` |
| `$E000-$EFFF` | Plane B, 64 × 32 | 4 = `$07` |
| `$F000-$FFFF` | Window | 3 = `$3C` |

CRAM holds 64 words (four palettes of 16) and VSRAM 40 words, each reached by its own write command ([The three memories](../megadrive/vdp.md#the-three-memories)).

## Z80

From [System architecture](../megadrive/architecture.md#the-z80-memory-map):

| Z80 address | Contents |
|-------------|----------|
| `$0000-$1FFF` | Sound RAM, 8 KB |
| `$4000-$4003` | YM2612: address and data, parts I and II |
| `$6000` | Bank register, written a bit at a time |
| `$7F11` | PSG |
| `$8000-$FFFF` | 32 KB window onto the 68000's space |

With a 32X attached, a Z80 write into `$840000-$9FFFFF` or `$A15100-$A153FF` through the window locks up the 68000, and the window must point elsewhere while the Z80 writes the PSG ([The Z80's view](../32x/architecture.md#the-z80s-view)).

## SH-2

### Address decoding

From [How the SH-2 decodes addresses](../32x/architecture.md#how-the-sh-2-decodes-addresses). The top three bits choose the kind of access:

| Address | Access |
|---------|--------|
| `0x00000000-0x1FFFFFFF` | Through the cache |
| `0x20000000-0x3FFFFFFF` | The same memory, bypassing the cache |
| `0x40000000-0x5FFFFFFF` | Associative purge: a write drops one cache line |
| `0x60000000-0x7FFFFFFF` | Cache address tags |
| `0xC0000000-0xC0000FFF` | Cache data; on-chip RAM in two-way mode |
| `0xFFFFFE00-0xFFFFFFFF` | On-chip peripherals |

### What the 32X puts there

From [What the 32X puts there](../32x/architecture.md#what-the-32x-puts-there):

| Cached | Cache-through | Size | Contents | Condition |
|--------|---------------|------|----------|-----------|
| `0x00000000` | `0x20000000` | 2 KB / 1 KB | Boot ROM, each CPU its own | |
| `0x00004000` | `0x20004000` | 256 bytes | System registers | Use cache-through |
| `0x00004100` | `0x20004100` | 256 bytes | 32X VDP registers | FM = 1 |
| `0x00004200` | `0x20004200` | 512 bytes | Palette | FM = 1; word access only |
| `0x02000000` | `0x22000000` | 4 MB | Cartridge, all of it, no banking | RV = 0 |
| `0x04000000` | `0x24000000` | 128 KB | Frame buffer (the one not on screen) | FM = 1 |
| `0x04020000` | `0x24020000` | 128 KB | Overwrite image | FM = 1 |
| `0x06000000` | `0x26000000` | 256 KB | SDRAM | |

The boot ROMs leave the Master's stack at `0x06040000` and the Slave's at `0x0603F800` ([What your code starts with](../32x/boot.md#each-sh-2-at-its-entry-point)). How programs divide the rest of SDRAM is in [Three SDRAM maps](../techniques/memory.md#three-sdram-maps).

### On-chip peripherals

Each SH-2 has its own set ([The SH7604 at a glance](../sh2/overview.md#the-address-space)):

| Address | Module | Chapter |
|---------|--------|---------|
| `0xFFFFFE00-0xFFFFFE05` | Serial port (SCI) | [Serial port](../sh2/sci.md) |
| `0xFFFFFE10-0xFFFFFE19` | Free-running timer; TOCR at `0xFFFFFE17` | [Timers](../sh2/timers.md) |
| `0xFFFFFE60-0xFFFFFE69` | Interrupt priorities and vector numbers (IPRB, VCRA-VCRD) | [Interrupt controller](../sh2/intc.md) |
| `0xFFFFFE71`, `0xFFFFFE72` | DMA request selects (DRCR0, DRCR1) | [DMA controller](../sh2/dmac.md) |
| `0xFFFFFE80-0xFFFFFE83` | Watchdog timer | [Timers](../sh2/timers.md) |
| `0xFFFFFE91` | Standby control (SBYCR); Sega forbids changing it | [Cache](../sh2/cache.md#the-control-register) |
| `0xFFFFFE92` | Cache control (CCR), one byte | [Cache](../sh2/cache.md) |
| `0xFFFFFEE0-0xFFFFFEE5` | ICR, IPRA, watchdog interrupt vector | [Interrupt controller](../sh2/intc.md) |
| `0xFFFFFF00-0xFFFFFF1F` | Division unit | [Division unit](../sh2/divu.md) |
| `0xFFFFFF40-0xFFFFFF7F` | User break controller | [The SH7604 at a glance](../sh2/overview.md) |
| `0xFFFFFF80-0xFFFFFFB3` | DMA controller: channels 0 and 1, vector registers at `0xFFFFFFA0`/`0xFFFFFFA8`, DMAOR at `0xFFFFFFB0` | [DMA controller](../sh2/dmac.md) |
| `0xFFFFFFE0-0xFFFFFFFB` | Bus state controller | [Bus state controller](../sh2/bsc.md) |

Sega's rules on what applications may change are in [What Sega forbids or reserves](../sh2/overview.md#what-sega-forbids-or-reserves): the bus state controller, for one, is off limits.

## 32X frame buffer

From [The line table](../32x/vdp.md#the-line-table). Each 128 KB frame buffer starts with a table of 256 words, one per display line, giving the word address of that line's pixels; the pixels follow. In packed-pixel mode a line is 160 words (320 pixels), so line *n* is conventionally at word `$100` + 160 × *n*. Direct colour takes 320 words a line and fits 204 lines.

## Sources

The chapters linked above, which cite: [32X-HWM](../appendices/bibliography.md#32x-hwm) §3.1-3.3; [32X-OV](../appendices/bibliography.md#32x-ov) pp.29-32; [MD-SWM](../appendices/bibliography.md#md-swm) §1, §2.5, §4.5; [MD-TO](../appendices/bibliography.md#md-to) §1; [SH7604](../appendices/bibliography.md#sh7604) §7.1.5, §8.3 and the register tables of each module.
