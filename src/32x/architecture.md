# Architecture and memory maps

The 32X is not a new console. It is a second computer that plugs into the Mega Drive's cartridge slot, takes the cartridge in its own slot on top, and mixes its picture and sound into the Mega Drive's. The Mega Drive underneath keeps running exactly as before: the 68000, the Z80, the VDP and the sound chips are all still there and still needed.

Most 32X programming problems come from one fact: **the two machines see each other only through narrow, specific windows.** This chapter shows what is on each side, which CPU can reach what, and the address maps that tie it together.

## The parts

| Part | What it is | Who uses it |
|------|------------|-------------|
| Two SH-2 CPUs (SH7604) | 32-bit RISC, 23.01 MHz on NTSC machines, 4 KB of cache each. One is wired as Master, the other as Slave. | 32X side |
| SDRAM | 256 KB (2 Mbit). Main memory for the SH-2s: their code and data live here. | SH-2s only |
| Frame buffers | Two banks of 128 KB DRAM (1 Mbit each). One is on screen while the other is being drawn. | SH-2s or 68000, one side at a time |
| 32X VDP | Turns a frame buffer into a picture: 15-bit direct colour, or 8-bit pixels through a 256-entry palette, or run-length data. No sprites and no tiles. | SH-2s or 68000, one side at a time |
| PWM | Two-channel pulse-width sound output for sampled audio. | Both sides |
| Interface chip | The bridge: system registers, eight communication words, the FIFO for 68000-to-SH-2 transfers, cartridge banking and the PWM unit. | Both sides |
| Boot ROMs | A 256-byte vector ROM for the 68000, 2 KB for the Master SH-2 and 1 KB for the Slave SH-2. | Each CPU its own |

Sources: [32X-HWM §1.1, §2.1-2.2; 32X-OV, hardware specifications]. The boot ROM sizes are those of the three dumps, whose checksums match MAME's list of the retail ROMs [32X-BIOS].

The clocks all come from the Mega Drive's master clock. The 68000 runs at the master clock divided by 7 and each SH-2 runs at three times the 68000's speed: 7.67 MHz and 23.01 MHz on NTSC machines, 7.60 MHz and 22.80 MHz on PAL ones [32X-HWM §3.3, clock; 32X-INTRO, PWM cycle]. Because all the clocks share one source, they stay in step with each other.

## How the pieces connect

```text
        MEGA DRIVE                                     32X
  ┌─────────────────────┐        ┌─────────────────────────────────────────────┐
  │                     │        │     Master SH-2            Slave SH-2       │
  │  68000 ── work RAM  │        │    (4 KB cache)           (4 KB cache)      │
  │    │                │        │          │                      │           │
  │    ├── VDP ── VRAM  │        │          └──────────┬───────────┘           │
  │    │                │        │                     │ SH-2 bus              │
  │    ├── Z80, YM2612, │        │   ┌─────────┬───────┴──────┬────────────┐   │
  │    │   PSG          │        │   │         │              │            │   │
  │    │                │        │ boot     SDRAM          32X VDP       PWM  │
  │    │   68000 bus    │ cart   │ ROMs     256 KB         palette            │
  │    └────────────────┼─slot───┼─► interface chip         frame buffers     │
  │                     │        │   (system registers,     2 × 128 KB        │
  │                     │        │    comm ports, FIFO,                       │
  │                     │        │    bank logic)                             │
  └─────────────────────┘        │          │                                 │
                                 │    cartridge ROM (up to 4 MB)              │
                                 └─────────────────────────────────────────────┘
       video and audio from the Mega Drive are mixed with the 32X's own output
```

Three things in this picture explain most of what follows.

**The SH-2s cannot see the Mega Drive at all.** No Mega Drive address appears in SH-2 address space: not the VDP, not work RAM, not the controllers. Anything the SH-2s need to know about the Mega Drive side has to be passed to them through the communication registers, the FIFO or an interrupt from the 68000 <span class="tag manual">manual</span> [32X-HWM §2.2, SH2 component]. See [68000 and SH-2 communication](communication.md).

**The 68000 can see most of the 32X, but only through windows.** The frame buffer, palette, VDP registers, system registers and the cartridge are mapped into 68000 space at new addresses. SDRAM is not: the 68000 cannot read or write the SH-2s' main memory directly [32X-HWM §2.1, Figure 3.1 p.13].

**The two SH-2s share one bus.** When both want it at once, the Master wins and the Slave waits. In the manual's view their caches keep this from happening often, as long as the code and data they use stay in cache <span class="tag manual">manual</span> [32X-HWM §2.2; 32X-OV, Master access to frame buffers]. A 4 KB cache holds little data, though, so code that moves data through SDRAM, such as copying, drawing from tables or mixing sound, misses often and contends often. No emulator in the sources models the contention: none of PicoDrive, ares, MAME and BlastEm has code that makes one SH-2 wait for the other [PICODRIVE; ARES; MAME; BLASTEM]. The book's timings come from emulators, so for work a CPU does they are a ceiling on a console's speed ([Timings from emulators](../conventions.md#timings-from-emulators)). See [Living with bus contention](../patterns/bus.md).

## Who can reach what

| | 68000 | Z80 | SH-2 |
|---|---|---|---|
| Cartridge ROM | Yes, through a 512 KB fixed window and a 1 MB banked window (or its normal place when RV = 1) | Through its bank window, like any 68000 address | Yes, all 4 MB in one piece, except while RV = 1 |
| Mega Drive work RAM, VDP, I/O, sound | Yes | As on a plain Mega Drive | No |
| SDRAM | No | No | Yes |
| Frame buffer, overwrite image, 32X VDP registers, palette | Only while FM = 0 | Some, see [below](#the-z80s-view) | Only while FM = 1 |
| System registers, communication ports, PWM | Yes | Read only in practice, see [below](#the-z80s-view) | Yes |

Sources: [32X-HWM §2.2, §3.1, §4.1-4.3; 32X-TI item 15].

Two bits in the system registers decide access to the shared parts:

- **FM** (bit 15 of `$A15100` on the 68000, of `0x20004000` on the SH-2) gives the 32X VDP, its registers, the palette and the frame buffer to one side. FM = 0 gives them to the 68000, FM = 1 to the SH-2s. The side that does not own them must leave them alone. Sega's manual says its access waits until FM is handed to it; the emulators disagree with it and with each other ([In emulators](#in-emulators)), and no console test has settled it <span class="tag disputed">disputed</span> [32X-HWM §4.1-4.2 pp.74-75; [discrepancy 34](../appendices/discrepancies.md); [Open questions](#open-questions)]. Writing FM takes ownership immediately, even if the other side is in the middle of an access, and that access is then not guaranteed <span class="tag manual">manual</span> [32X-HWM §3.2.1 p.19; §4.1 p.74].
- **RV** (bit 0 of `$A15106`) temporarily gives the cartridge back to the Mega Drive in its original layout. It has its own [section below](#the-rv-bit).

## The SH-2 memory map

### How the SH-2 decodes addresses

The SH7604 does not treat its 32-bit address as one flat space. The top three bits choose what kind of access it is, and the bits below choose where it goes [SH7604 §7.1.5, Table 7.3; §8.3, Table 8.2]:

| Top bits | Address range | What an access does |
|----------|---------------|---------------------|
| `000` | `0x00000000-0x1FFFFFFF` | Normal access through the cache (when the cache is on) |
| `001` | `0x20000000-0x3FFFFFFF` | Same memory, but bypassing the cache |
| `010` | `0x40000000-0x5FFFFFFF` | Writing here removes one line from the cache (an "associative purge") |
| `011` | `0x60000000-0x7FFFFFFF` | Direct access to the cache's address tags |
| `110` | `0xC0000000-0xC0000FFF` | Direct access to the cache's data, usable as fast on-chip RAM |
| `111` | `0xFFFFFE00-0xFFFFFFFF` | The SH-2's own peripherals: DMA controller, divider, timers, serial port |

So each piece of 32X memory has **two addresses that reach the same place**: a cached one starting with `0x0` and a cache-through one starting with `0x2`. Which one you use is a decision about correctness, not just speed:

- Code and data that only one CPU uses can go through the cache.
- Anything another processor can change behind your back has to go through the cache-through address. That includes every hardware register, the communication ports, and any SDRAM shared between the two SH-2s. The cache does not notice writes made by the other SH-2 or the 32X hardware, and will keep returning an old value <span class="tag manual">manual</span> [32X-HWM §3.1 p.16, cache area access; §4.1 p.74, cache-through access].
- If a cached copy has to be dropped, a longword write to the same address plus `0x40000000` throws away that one 16-byte line <span class="tag manual">manual</span> [SH7604 §8.4.7].

The 4 KB cache can also be split into 2 KB of cache and 2 KB of RAM at `0xC0000000`. With the cache switched off, all 4 KB is usable as RAM there [SH7604 §8.4.8; 32X-OV, dual SH2's]. This is the fastest memory either SH-2 has, and each CPU has its own. See [Cache](../sh2/cache.md) and [Cache discipline](../patterns/cache.md).

### What the 32X puts there

The SH7604 divides its normal space into four 32 MB areas, CS0 to CS3, each with its own bus timing settings [SH7604 §7.1.5]. The 32X uses one area per kind of memory:

| Cached | Cache-through | Size | Contents | Condition |
|--------|---------------|------|----------|-----------|
| `0x00000000` | `0x20000000` | 2 KB / 1 KB | Boot ROM (each CPU sees its own) | |
| `0x00004000` | `0x20004000` | 256 bytes | System registers | Always use the cache-through address |
| `0x00004100` | `0x20004100` | 256 bytes | 32X VDP registers | FM = 1. Cache-through address |
| `0x00004200` | `0x20004200` | 512 bytes | Palette (256 colours) | FM = 1. Word access only |
| `0x02000000` | `0x22000000` | 4 MB | Cartridge ROM | RV = 0 |
| `0x04000000` | `0x24000000` | 128 KB | Frame buffer (the one not on screen) | FM = 1 |
| `0x04020000` | `0x24020000` | 128 KB | Overwrite image of the same frame buffer | FM = 1 |
| `0x06000000` | `0x26000000` | 256 KB | SDRAM | |

Sources: [32X-HWM §3.1 p.15, Figure 3.2; §3.3, VDP memory map; 32X-OV pp.31-32]. The rest of each area is unused.

Some things in this table are worth spelling out:

- **The two SH-2s have the same map but are not identical.** At `0x00000000` each one sees its own boot ROM. In the system registers, the interrupt mask bits and the interrupt-clear registers sit at the same address for both CPUs but are separate per CPU, so each SH-2 can mask and acknowledge its own interrupts [32X-HWM §3.2.2, interrupt mask register].
- **Only one frame buffer is visible at a time.** `0x04000000` always shows the buffer that is *not* being displayed. Changing the FS bit in the frame buffer control register swaps them at the next vertical blank. Until then, the CPU is still looking at the old one <span class="tag manual">manual</span> [32X-HWM §3.3, frame buffer swap]. See [The 32X VDP](vdp.md).
- **The overwrite image is the same memory with a twist.** Writes through `0x04020000` skip any byte that is zero, which leaves the pixel underneath alone. It is a cheap way to draw shapes with transparent parts [32X-HWM §3.3, over write image].
- **The SH-2 sees the whole cartridge at once.** Unlike the 68000, it needs no banking to reach any of the 4 MB. Reads from ROM are slow and compete with the 68000, so the manual's model is to copy SH-2 code and data into SDRAM and run from there [32X-HWM §2.2, SDRAM component; §4.1 p.74, ROM access competition]. See [Access timing per CPU](timing.md). Four megabytes (32 Mbit) is all that either CPU sees of the cartridge directly; a larger cartridge needs Sega's bank chip, which maps 512 KB pages into the cartridge space ([Beyond 16 Mbit, and beyond 4 MB](../howto/large-cartridges.md#beyond-16-mbit-and-beyond-4-mb)).
- **Frame buffer writes are buffered.** The SH-2 can hand off a few writes to the frame buffer without waiting for the DRAM. The manual says the buffer holds four words, while the earlier hardware reference reproduced in the system overview says two <span class="tag disputed">disputed</span> [32X-HWM §3.1 p.16; 32X-OV p.32; [discrepancy 4](../appendices/discrepancies.md); [Open questions](#open-questions)].

## The 68000 memory map

The 68000's view changes during boot. At power-on the machine looks almost like a plain Mega Drive. Sega's initial program, a fixed 1040-byte block at `$0003F0`-`$0007FF`, then switches the adapter on by setting ADEN, and after that the map is different [32X-HWM §5]. All 31 retail cartridges in the sources carry that block byte for byte the same ([Sega's sample code in the games](../appendices/sample-code.md#segas-samples)) [32X-ROMSET; MK2; MCX]. One page of the manual gives the start as `$3FA` instead. The reset vector of all 31 points to `$0003F0` <span class="tag disputed">disputed</span> [32X-HWM §3.1 p.13; 32X-ROMSET; MK2; MCX, cartridge `$000004`; [discrepancy 3](../appendices/discrepancies.md)]. See [Boot, security code and initial program](boot.md).

### At power-on (ADEN = 0)

The cartridge sits at `$000000-$3FFFFF` as usual and everything else is Mega Drive. Two 32X things are visible already, so the initial program can find the 32X and switch it on [32X-HWM Figure 3.1 p.13]:

| Address | Contents |
|---------|----------|
| `$A130EC` | The four ASCII bytes `MARS`, present only when a 32X is attached |
| `$A15100` | 32X system registers |

The March 1994 hardware manual gives the ID address as `$A130FC`, and two Sega overviews from April 1994 repeat it. That address is wrong. Sega's initial program compares the ID at `$A130EC`, and every cartridge that boots must carry that program unchanged (see [Boot](boot.md#the-security-check)). The compare, `cmpi.l #'MARS',$30EC(a5)` with a5 = `$A10000`, sits at cartridge `$00040C` inside that block, so it is the same in all 31 retail cartridges <span class="tag disputed">disputed</span> [32X-OV p.29; 32X-INTRO p.29; 32X-HWM Figure 3.1 p.13; 32X-ROMSET; MK2; MCX, cartridge `$00040C`; [discrepancy 2](../appendices/discrepancies.md)].

### After the 32X is switched on (ADEN = 1)

| Address | Contents | Condition |
|---------|----------|-----------|
| `$000000-$0000FF` | 32X vector ROM | |
| `$000100-$3FFFFF` | Cartridge, in its original layout. Save RAM at `$200000` may be an exception, see [Cartridge hardware](../megadrive/cartridge.md#other-kinds-of-save-memory). notaz's console tests read the cartridge header here with RV = 1, while `$000000-$0000FF` still answers with the vector ROM [TESTPICO, `t_32x_md_rom`] | RV = 1 |
| `$000100-$3FFFFF` | Nothing the manual describes: its map marks the area accessible only when RV = 1 [32X-HWM Figure 3.1 p.13]. What a read returns on a console is not documented, and the console tests do not read it with RV = 0: they run every 32X test with RV = 1 [TESTPICO, test list]. Emulators return the cartridge, no data or zeros ([In emulators](#in-emulators)) | RV = 0 |
| `$400000-$83FFFF` | As on a plain Mega Drive | |
| `$840000-$85FFFF` | Frame buffer (the one not on screen) | FM = 0 |
| `$860000-$87FFFF` | Overwrite image of the same frame buffer | FM = 0 |
| `$880000-$8FFFFF` | Cartridge `$000000-$07FFFF`, always | RV = 0 |
| `$900000-$9FFFFF` | One 1 MB bank of the cartridge, chosen by `$A15104` | RV = 0 |
| `$A130EC` | `MARS` ID | |
| `$A15100-$A1517F` | System registers | |
| `$A15180-$A151FF` | 32X VDP registers | FM = 0 |
| `$A15200-$A153FF` | Palette | FM = 0. Word access only |
| everything else | As on a plain Mega Drive: Z80 area, I/O, VDP, work RAM | |

Sources: [32X-HWM §3.1 pp.13-14, Figure 3.1; §3.2.1, bank set register; §4.2 p.75; 32X-OV pp.29-30].

The cartridge has moved. Code that ran at `$000xxx` on a plain Mega Drive now runs at `$880xxx` or `$9xxxxx`. A 32X game's 68000 code is therefore assembled to run from `$880000` onwards. Virtua Racing Deluxe is built this way: its jump table at `$000200` sends the reset to `$880838`, and its start-up code loads addresses such as `$8806E4` [32X-ROMSET, Virtua Racing Deluxe, 68000 code at `$000200`, `$00085E`].

**The fixed window is 512 KB.** It always shows the first 512 KB of the cartridge. The banked window shows one of the four megabytes. To reach the second, third or fourth megabyte, write 1, 2 or 3 to the bank set register at `$A15104` <span class="tag manual">manual</span> [32X-HWM §3.2.1, bank set register]. Aerobiz Ultimate solves the problem of a 1 MB game written for `$000000` by placing the whole image in bank 1 and selecting that bank once, so the game sits unbroken at `$900000-$9FFFFF` [AU-NOTES, memory map]. See [Using more cartridge space](../howto/large-cartridges.md).

**One address, two CPUs.** Data that both sides read can store 68000 addresses and let the SH-2 convert them. With bank 0 selected, `$900000` shows cartridge offset 0, which the SH-2 sees at `0x02000000`, so adding `0x01700000` turns a banked-window address into the SH-2's. Mortal Kombat II's text and animation tables hold addresses such as `$9286D4`, and its Master adds `0x01700000` before reading through them [MK2, SH-2 code at `0x0600122A`, `0x0600271E`]. It only works for data in the first megabyte. After Burner Complete does the same for the fixed window: its Master reads a 68000 pointer from cartridge offset `$C0A`, subtracts `$880000` and adds `0x22000000`, the cache-through view of the cartridge [AB32X, SH-2 code at `0x060021D0`-`0x060021E6`].

**The vector ROM sends every exception to the cartridge.** The 68000 reads its exception vectors from `$000000`, which is now the 32X's own 256-byte ROM. Each exception vector points to a different address from `$880200` upwards, six bytes apart, which is room for one `JMP` to an absolute address. A 32X cartridge therefore holds a table of jumps starting at offset `$200`, one per vector, instead of relying on the vector table at its start <span class="tag manual">manual</span> [32X-HWM §3.1 p.14]. One vector is different: the horizontal interrupt vector at `$000070` is RAM, so a game can point it anywhere while running [32X-OV p.29].

**Read your own header through `$880000`.** With RV = 0 the manual gives `$000100-$3FFFFF` to nothing, so a game that reads its header at `$0001xx` reads something undocumented, and no console test says what <span class="tag manual">manual</span> [32X-HWM Figure 3.1 p.13]. Upstream PicoDrive leaves the cartridge visible at both addresses all the time, so the mistake goes unnoticed there; ares returns no data and MAME zeros, which show it <span class="tag emulator">emulator</span> ([In emulators](#in-emulators)).

## The RV bit

RV is short for "ROM to VRAM DMA". Setting it puts the cartridge back at `$000100-$3FFFFF`, and while RV is 1 the `$880000-$9FFFFF` windows are gone [32X-HWM §3.1 pp.13-14]. The manual's rule is that a DMA from the cartridge to the Mega Drive VDP needs RV = 1: its register description calls 1 "DMA start allowed" and 0 "no operation" <span class="tag manual">manual</span> [32X-HWM §3.2.1, DREQ control register]. It does not say why the VDP cannot read the cartridge through the high windows, and no source explains it ([Open questions](#open-questions)). A comment in notaz's console tests adds that reading the high windows while RV is 1 hangs the machine, which is why the tests leave them alone [TESTPICO, `t_32x_md_rom`].

While RV is 1, the rest of the machine is restricted:

- **The SH-2s cannot read the cartridge.** An SH-2 that tries is stalled until the 68000 clears RV. SH-2 code running from SDRAM is unaffected <span class="tag manual">manual</span> [32X-HWM §3.1 p.16, cartridge ROM access].
- **68000 interrupts must be off.** Sega's bulletin states the rule without giving a reason <span class="tag manual">manual</span> [32X-TI item 9]. A likely one: every interrupt goes through the jump table at `$880200`, and that window is gone while RV is 1.
- **Code that sets RV must not run from the cartridge.** The instruction after the write would be fetched from a window that has just vanished. The vector ROM provides two short routines for this, which set RV, do their writes and clear RV again, all from inside the vector ROM. The one at `$0000C0` writes the byte in `d0` to the address in `a1`. The one at `$0000D4` writes eight bytes from `a0` to `$A130F1`, `$A130F3` and so on up to `$A130FF`: the save RAM switch and the registers of Sega's bank chip, which cartridges over 4 MB need and which must only be written with RV = 1 [32X-BIOS, vector ROM `$0000C0`-`$0000FF`; 32X-HWM §3.1 p.14]. For the same reason, the code that sets RV around a DMA from the cartridge has to run outside it, from work RAM or through these routines.
- **A few bytes are unreadable.** Four bytes each at cartridge `$001070`, `$002070` and `$003070` do not read correctly while RV is 1. Keep data meant for DMA away from them <span class="tag manual">manual</span> [32X-TI item 12].
- **Reset is dangerous.** Pressing reset with RV = 1 can leave the machine unable to restart. The fix is handled on the SH-2 side and is described in [Hardware bugs and workarounds](bugs.md) [32X-TIA1].

Upstream PicoDrive stores RV and does nothing with it, so none of these problems show up there; of the four emulators read, only ares stalls the SH-2s as the manual says ([In emulators](#in-emulators)) <span class="tag emulator">emulator</span>. The Virtua Racing Deluxe project's copy of PicoDrive adds an optional RV model [VRD-NOTES].

## The Z80's view

The Z80 reaches 68000 space through its usual 32 KB bank window at Z80 `$8000-$FFFF` [32X-HWM §4.3 p.76; MD-SWM, Z80 bank register]. With the window at `$A10000`, for example, the 32X system registers appear at Z80 `$D100`. It sees the same map as the 68000, including the moved cartridge.

The Hardware Manual marks the communication ports, the PWM registers and several VDP and system registers as reachable from the Z80 [32X-HWM §4.1, Table 4.1 p.73]. A later technical bulletin restricts this sharply. On production hardware, a Z80 *write* to `$840000-$9FFFFF` or `$A15100-$A153FF` locks up the 68000. Reads are fine <span class="tag disputed">disputed</span> [32X-TI item 15; [discrepancy 5](../appendices/discrepancies.md); [Open questions](#open-questions)]. Until this is tested, assume the Z80 can watch the 32X but not drive it. By the bulletin's rule, a Z80 sound driver cannot feed PWM directly.

One more rule affects every Z80 sound driver. When the Z80 writes to the PSG, its bank register must not point into `$000000-$3FFFFF` or `$840000-$9FFFFF`. The 32X can mistake the bus activity for an access to itself, return wrong data to the 68000, or corrupt its own registers. How often this happens depends on the console, so it can pass testing and fail in the field <span class="tag manual">manual</span> [32X-TI item 22]. See [Z80 bus control](../megadrive/z80.md).

## In emulators

Four emulators with 32X support were read for this book. On the three points this chapter warns about, they disagree with the manual and with each other <span class="tag emulator">emulator</span>:

| | The side without FM touches the 32X VDP, palette or frame buffer | RV = 1: the 68000's windows at `$880000-$9FFFFF` | RV = 1: an SH-2 reads the cartridge | RV = 0: the 68000 reads `$000100-$3FFFFF` |
|---|---|---|---|---|
| The manual | The access waits until FM is handed over | Gone | Waits until RV = 0 | Not accessible |
| Upstream PicoDrive | Never waits; writes are dropped | Still mapped | Goes ahead | The cartridge, which is never unmapped |
| ares | Never waits; writes are dropped | Return no data | Waits until RV = 0 | No data |
| MAME | Not checked for the frame buffer and palette: either side reads and writes them. Writes to the VDP registers are dropped | Still mapped | Goes ahead | Zeros |
| BlastEm | The 68000 waits until FM is released; an SH-2 read returns `$FFFF` | Unmapped; the cartridge moves to the low area | Goes ahead | Unmapped; what a read returns was not traced |

Sources: [32X-HWM Figure 3.1 p.13; §3.1 p.16; §4.1-4.2 pp.74-75]; [PICODRIVE, `pico/32x/memory.c` at `26ecb2b`: the FM checks in the register write handlers, the DREQ control write that only stores RV, and `PicoMemSetup32x`, whose comment says the ROM is left mapped "so that we can avoid handling the RV bit"]; [ARES, `md/cartridge/board/mega-32x.cpp`, `md/m32x/bus-external.cpp`, `bus-internal.cpp` at `9408cb4`]; [MAME, `src/mame/shared/mega32x.cpp` at `1ecdb57`: `m68k_a15106_w`, whose comment says it "should also UNMAP the banked rom area", `m68k_a15100_w`, `common_vdp_regs_w` and the SH-2 map]; [BLASTEM, `32x.c` at `1e0de94`: `s32x_fb_read_w`, `s32x_sh2_fb_read_w`, `check_cart_map_change`]. For the reads by the side without FM in PicoDrive and ares, see [discrepancy 34](../appendices/discrepancies.md).

Only ares follows the manual on RV, and only BlastEm on FM, for the 68000 alone. None of the four has been checked against a console on these points; the tests that would settle them are below.

## What to take away

- Link 68000 code at `$880000` and remember that only the first 512 KB is always visible. The rest goes through the 1 MB bank window.
- Give every SH-2 access to registers, communication ports or shared memory a `0x2xxxxxxx` address. Cache only what one CPU owns alone.
- The frame buffer and the 32X VDP belong to one side at a time. Check FM before touching them, whatever an emulator lets you do.
- Treat RV = 1 as a short, interrupt-free moment run from outside the cartridge. Keep the SH-2s off the cartridge while it lasts.
- Do not trust an emulator on RV, on FM or on reading the cartridge at its old address. Upstream PicoDrive ignores RV and keeps the cartridge at both addresses, MAME and BlastEm let the SH-2s read the cartridge with RV set, and only ares stalls them as the manual says. Test such code on a console.
- Read the book's timings, which come from emulators, as a ceiling on a console's speed for the work a CPU does.

The same maps, without the explanations, are collected in [Memory maps](../appendices/memory-maps.md).

## Open questions

- **Does a Z80 write to `$840000-$9FFFFF` or `$A15100-$A153FF` lock up the 68000, as the bulletin says?** The manual lists those registers as reachable from the Z80 [32X-HWM Table 4.1 p.73; 32X-TI item 15; discrepancy 5]. Test: with the 68000 incrementing a counter in work RAM and showing it on screen, have the Z80 point its bank window at `$A10000` and write a communication port at Z80 `$D120`; then repeat with a read, and with the frame buffer window. A counter that stops after the write, and not after the read, confirms the bulletin.
- **When the side without FM touches the 32X VDP, palette or frame buffer, does the access wait, as the manual says, or do reads go through and writes get dropped, as PicoDrive and ares do?** Test: give FM to the SH-2s, have the Master hand it back after a known number of lines, and meanwhile let the 68000 read a frame buffer word and the V counter. If the read returns only after the handover, with the right data, the access waits; if it returns at once, it does not. Repeat with a write, checked afterwards by the owner (discrepancy 34).
- **Does the frame buffer's write buffer hold two words or four?** Test: with FM = 1, have an SH-2 write words to the frame buffer back to back and time each write with the free-running timer, or read the FULL bit after each. The first write that stalls, or the count at which FULL sets, gives the depth (discrepancy 4).
- **Why can't the Mega Drive VDP DMA from the cartridge through `$880000-$9FFFFF`?** What is known is the manual's rule: a DMA from the cartridge needs RV = 1, which puts the cartridge back at its old address [32X-HWM §3.1 pp.13-14; §3.2.1, DREQ control register]. The VDP's source registers hold address bits 23-1 ([Setting one up](../megadrive/vdp-dma.md#setting-one-up)), so `$880000` can be written there, but Sega's Mega Drive manual lists only cartridge ROM at `$000000-$3FFFFF` and work RAM as sources [MD-SWM §2.7]. That the windows do not answer a VDP DMA is inferred from the rule and the bit's name; why is unexplained. Test: with RV = 0, run a DMA from `$880000` plus an offset into VRAM and compare VRAM with the cartridge; then the same from the low address with RV = 1.
- **What does the 68000 read at `$000100-$3FFFFF` with RV = 0?** The manual gives the area to nothing and the emulators disagree. Test: read a few cartridge offsets there with RV = 0 and compare with the same offsets through `$880000`.

## Sources

- [32X-HWM](../appendices/bibliography.md#32x-hwm): §1.1, §2, §3.1 (pp.13-16), §3.2, §3.3, §4.1-4.3, §5
- [TESTPICO](../appendices/bibliography.md#testpico): `t_32x_md_rom`; the test list, run with RV = 1
- [32X-OV](../appendices/bibliography.md#32x-ov): hardware specifications; MD and SH-2 memory maps (pp.29-32)
- [32X-INTRO](../appendices/bibliography.md#32x-intro): system features, PWM cycle
- [32X-TI](../appendices/bibliography.md#32x-ti): items 9, 12, 15, 22
- [32X-TIA1](../appendices/bibliography.md#32x-tia1): VRES and RV
- [SH7604](../appendices/bibliography.md#sh7604): §7.1.5, §8.3, §8.4.7-8.4.8
- [MD-SWM](../appendices/bibliography.md#md-swm): Z80 bank register; §2.7, DMA sources
- [32X-BIOS](../appendices/bibliography.md#32x-bios): the boot ROM sizes; the vector ROM's routines at `$0000C0` and `$0000D4`
- [32X-ROMSET](../appendices/bibliography.md#32x-romset), [MK2](../appendices/bibliography.md#mk2), [MCX](../appendices/bibliography.md#mcx): Sega's initial program and reset vector in all 31 retail cartridges; Virtua Racing Deluxe's jump table and start-up code
- [PICODRIVE](../appendices/bibliography.md#picodrive), [ARES](../appendices/bibliography.md#ares), [MAME](../appendices/bibliography.md#mame), [BLASTEM](../appendices/bibliography.md#blastem): FM, RV and the cartridge mapping, at the commits given above
- [MK2](../appendices/bibliography.md#mk2): SH-2 code at `0x0600122A`, `0x0600271E`
- [AB32X](../appendices/bibliography.md#ab32x): SH-2 code at `0x060021D0`
- See also: [VRD-NOTES](../appendices/bibliography.md#vrd-notes) (the BIOS dumps' origin and an optional RV model for PicoDrive) and [AU-NOTES](../appendices/bibliography.md#au-notes) (the bank-1 layout of Aerobiz Ultimate)
