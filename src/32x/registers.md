# System registers

The 32X adds one block of 64 bytes of system registers, visible to the 68000 at `$A15100` and to both SH-2s at `0x20004000`. Next to it are the 32X VDP's registers, at `$A15180` and `0x20004100`. The two views of the system block are not the same: the first 32 bytes hold different registers on each side, and only the last 32 bytes, the communication ports and PWM, are the same registers seen twice.

This chapter lists every register bit by bit: who can read it, who can write it, what it holds after the boot, and where the emulators part from the manuals. How to use them is in the chapters linked from each section.

## The map at a glance

| Offset | 68000 side (`$A151xx`) | SH-2 side (`0x200040xx`) |
|--------|------------------------|--------------------------|
| `$00` | [Adapter control](#a15100-adapter-control) | [Interrupt mask](#0x20004000-interrupt-mask). FM (bit 15) is the same bit on both sides |
| `$02` | [Interrupt control](#a15102-interrupt-control) | [Standby change](#0x20004002-standby-change) |
| `$04` | [Bank set](#a15104-bank-set) | [H count](#0x20004004-h-count) |
| `$06` | [DREQ control](#a15106-dreq-control) | [DREQ control](#0x20004006-0x20004012-the-sh-2s-view-of-dreq), read only, plus two status bits of its own |
| `$08`, `$0A` | DREQ source address | The same, read only |
| `$0C`, `$0E` | DREQ destination address | The same, read only |
| `$10` | DREQ length | The same, read only |
| `$12` | FIFO, write only | FIFO, the source for DMA channel 0 |
| `$14`, `$16`, `$18` | — | [VRES, V and H interrupt clear](#0x20004014-0x2000401c-interrupt-clear) |
| `$1A` | [SEGA TV](#a1511a-sega-tv) | CMD interrupt clear |
| `$1C` | — | PWM interrupt clear |
| `$20`-`$2E` | [Communication ports](communication.md#the-communication-ports): the same eight words on both sides | |
| `$30`-`$38` | [PWM](pwm.md#registers): the same five registers on both sides, except that TM and RTP can only be written from the SH-2 | |

Sources: [32X-HWM §3.2.1-3.2.2 pp.19-31; 32X-OV pp.34-43]. Both manual pages were checked on the scans; the text copies get some read/write markings wrong.

General rules:

- **From the SH-2, use the `0x2000xxxx` addresses.** They bypass the cache; the `0x0000xxxx` ones do not, and would return stale values ([Architecture](architecture.md#how-the-sh-2-decodes-addresses)).
- **Access sizes.** Most registers take byte or word accesses from either side. The DREQ address, length and FIFO registers and the five interrupt clears are word only [32X-HWM §3.2.1-3.2.2].
- **Speed.** The 68000 reaches the system registers with no wait states; the SH-2 needs one [32X-HWM §4.4 p.78].
- **Byte addresses.** Both CPUs are big-endian, so the byte at the register's own address is bits 15-8 and the byte one above it is bits 7-0. `$A15101` is the low byte of adapter control, `0x20004001` the low byte of the interrupt mask.

## The 68000 side

### $A15100: adapter control

| Bit | Name | 68000 | Meaning |
|-----|------|-------|---------|
| 15 | FM | R/W | Who owns the 32X VDP, palette and frame buffer: 0 = 68000, 1 = SH-2s |
| 7 | REN | Read only | "SH2 reset enable" |
| 1 | RES | R/W | 0 = both SH-2s held in reset, 1 = running |
| 0 | ADEN | R/W | 1 = 32X enabled: the 68000 sees the 32X memory map |

Sources: [32X-HWM §3.2.1 p.19; 32X-OV p.34]. Bits 14-8 and 6-2 read 0 in both emulators [PICODRIVE, pico/32x/memory.c; ARES, md/m32x/io-external.cpp].

**ADEN and RES belong to Sega's initial program.** The manual says the initial program sets them and nothing else may change them [32X-HWM p.19]. What the initial program does with them, read from the copy at the start of every cartridge [VRD-NOTES, ROM, `$418`, `$4C0`, `$6F8`]:

1. It waits until REN reads 1.
2. Its work-RAM stub writes `$01` to `$A15101`: ADEN = 1, RES = 0. The 68000 now sees the 32X map, and both SH-2s are held in reset.
3. Later it writes `$03`: RES = 1 releases the SH-2s, which run their boot ROMs again, this time with ADEN = 1.

The reset-button code reads ADEN and RES to find out how far the last start got ([Pressing reset](boot.md#pressing-reset)).

**RES is 1 at power-on, not 0.** Sega's register tables give RES an initial value of 0, which would hold the SH-2s in reset from power-on [32X-OV p.34; 32X-INTRO, adapter control register]. But the Master's boot ROM has a path that only runs at power-on, before the 68000 has set ADEN: it waits, writes the standby register, puts the SH-2 into standby and sleeps ([below](#0x20004002-standby-change)). That path can only run if the SH-2s are already out of reset. notaz's power-on test expects `$A15100` to read `$0082`, RES = 1 and REN = 1, once REN has come up; his comment notes that REN seems to stay clear for a while after a reset [TESTPICO, t_32x_init]. PicoDrive, which marks its value as tested, and Ares both start the same way <span class="tag emulator">emulator</span> [VRD-NOTES, 32X BIOS dump; PICODRIVE, pico/32x/32x.c; ARES, md/m32x/m32x.hpp; [discrepancy 30](../appendices/discrepancies.md)]. What REN reports is still unknown, so wait for it to read 1, as Sega's initial program does.

**REN is documented only by its name.** No manual says what sets it, and in both emulators it reads 1 from power-on, so the initial program's wait ends at once. Leave the wait to the initial program; your own code has no reason to read REN.

**FM** can be written from either side, and a write takes effect at once, even if the other side is in the middle of an access. Write only the high byte (`$A15100`) to change FM alone [32X-HWM p.19]. See [Shared registers](#shared-registers-and-simultaneous-writes).

### $A15102: interrupt control

| Bit | Name | 68000 | Meaning |
|-----|------|-------|---------|
| 1 | INTS | R/W | Write 1 to raise CMD on the Slave |
| 0 | INTM | R/W | Write 1 to raise CMD on the Master |

Sources: [32X-HWM §3.2.1 p.20; 32X-OV p.34]. When the bits go back to 0 is <span class="tag disputed">disputed</span> ([discrepancy 11](../appendices/discrepancies.md)); see [The CMD interrupt](communication.md#the-cmd-interrupt).

**Set one bit without clearing the other.** In both emulators a write replaces both bits, so writing `$01` while INTS is still pending withdraws the Slave's request <span class="tag emulator">emulator</span> [PICODRIVE, pico/32x/memory.c; ARES, md/m32x/io-external.cpp]. The manuals do not say what a 0 does. Raise one CPU's interrupt with `bset` on `$A15103`, or write `$03` to raise both, as d32xr does [D32XR, src-md/crt0.s].

### $A15104: bank set

| Bits | Name | Meaning |
|------|------|---------|
| 1-0 | BK1, BK0 | Which megabyte of the cartridge appears at `$900000-$9FFFFF`: 0 to 3 |

Sources: [32X-HWM §3.2.1 p.20; 32X-OV p.35]. 0 after the initial program. See [Architecture](architecture.md#after-the-32x-is-switched-on-aden--1) and [Using more cartridge space](../howto/large-cartridges.md).

### $A15106: DREQ control

| Bit | Name | 68000 | Meaning |
|-----|------|-------|---------|
| 7 | FULL | Read only | 1 = the FIFO has no room |
| 2 | 68S | R/W | 1 starts a FIFO transfer, 0 stops it. Clears itself when the length reaches 0 |
| 1 | — | — | Always 0 in the hardware manual. Earlier documents put a DMA capture mode here ([discrepancy 25](../appendices/discrepancies.md)) |
| 0 | RV | R/W | 1 gives the cartridge back to the Mega Drive map |

Sources: [32X-HWM §3.2.1 p.21; 32X-OV p.35]. See [DREQ and the FIFO](fifo.md) for 68S and FULL, and [The RV bit](architecture.md#the-rv-bit) for RV.

### $A15108-$A15112: DREQ addresses, length and FIFO

| Address | Register | Bits |
|---------|----------|------|
| `$A15108` | Source address, high | Bits 7-0 = address bits 23-16 |
| `$A1510A` | Source address, low | Bits 15-1; bit 0 is always 0 |
| `$A1510C` | Destination address, high | Bits 7-0 = address bits 23-16 |
| `$A1510E` | Destination address, low | Bits 15-0 |
| `$A15110` | Length | Bits 15-2, in words; the low two bits always read 0 |
| `$A15112` | FIFO | Write only |

Sources: [32X-HWM §3.2.1 pp.21-22; 32X-OV pp.36-37]. The transfer itself uses only the length and the FIFO. The SH-2 can read the other four but not write them, so they can carry an argument from the 68000 to the SH-2 ([DREQ and the FIFO](fifo.md#registers)).

### $A1511A: SEGA TV

| Bit | Name | Meaning |
|-----|------|---------|
| 0 | CM | Cartridge mode: 0 = ROM, 1 = DRAM |

Sources: [32X-HWM §3.2.1 p.23; 32X-OV p.37]. The bit makes the 32X send refresh signals to a cartridge built from DRAM. Sega reserved it for a product it called SEGA TV and forbids every other use. Leave it at 0. PicoDrive also keeps bit 8 of this register, logging any write as a mystery [PICODRIVE, pico/32x/memory.c].

## The SH-2 side

### 0x20004000: interrupt mask

| Bit | Name | SH-2 | Shared? | Meaning |
|-----|------|------|---------|---------|
| 15 | FM | R/W | With the 68000 and the other SH-2 | Same bit as `$A15100` bit 15 |
| 9 | ADEN | Read only | Yes | The 68000's ADEN |
| 8 | CART | Read only | Yes | 0 = a cartridge is inserted |
| 7 | HEN | R/W | Between the two SH-2s | 1 = H interrupts also during vertical blank |
| 3 | V | R/W | No: one per SH-2 | 1 = V interrupt allowed |
| 2 | H | R/W | No | 1 = H interrupt allowed |
| 1 | CMD | R/W | No | 1 = CMD interrupt allowed |
| 0 | PWM | R/W | No | 1 = PWM interrupt allowed |

Sources: [32X-HWM §3.2.2 p.26 (scan); 32X-OV p.40]. All bits except ADEN and CART are 0 after reset. The text copy of the manual marks ADEN as writable; the scan shows bits 9 and 8 as read only.

**The boot ROMs read the top byte.** The Master's boot ROM tests ADEN to tell power-on (ADEN = 0) from a real start, tests CART to choose between the cartridge and the Mega-CD path, and on a failed security check writes `$80` to `0x20004000` to take the VDP away from the 68000 [VRD-NOTES, 32X BIOS dump, Master `$018C`, `$021E`, `$024C`]. See [Boot](boot.md).

**Write the mask with a byte write to `0x20004001`.** A word write also writes FM. If the 68000 changed FM between your read and your write, the word write puts the old owner back. Mortal Kombat II and After Burner Complete's Master write the low byte alone. After Burner Complete's Slave writes the word `$8203`, which takes FM for the SH-2s in the same write. Star Wars Arcade reads the word, sets one bit and writes the word back [MK2, SH-2 code at `0x060002B6`, `0x0600516C`; AB32X, SH-2 code at `0x06000244`, `0x06002168`; SWA, SH-2 code at `0x0600093C`, `0x06000F2E`].

**HEN is shared, so either SH-2 can change it for both.** A byte write to the low byte always writes HEN too. If the Master has set HEN and the Slave later writes its own mask as a constant with bit 7 at 0, H interrupts during vertical blank stop for both CPUs. A program that uses HEN should include it in every mask value it writes, on both CPUs.

**Masking does not lose a raised interrupt.** If an interrupt has been raised and is masked before the CPU takes it, VRES, V, H and PWM stay asserted until cleared and are taken when unmasked; CMD is withdrawn while masked and comes back when unmasked if it is still pending [32X-HWM §3.2.2 p.29]. The manual does not say whether a V, H or PWM event that happens while its bit is already 0 is recorded at all. For V, notaz's console test shows it is: a V that arrives while the Slave has it masked is taken as soon as the Slave unmasks it in the same blank, and a V the handler does not clear is taken again and again [TESTPICO, t_32x_irq_vint]. Whether a held V survives past the end of the blank, and what H and PWM do, is still <span class="tag disputed">disputed</span> ([discrepancy 44](../appendices/discrepancies.md)). See [Interrupt controller](../sh2/intc.md#the-32xs-five-interrupts).

What the retail games enable [MK2; AB32X; SWA, as above]:

| Game | Master | Slave |
|------|--------|-------|
| Mortal Kombat II | `$0A`: V and CMD, after writing `$80` to take FM | `$01`: PWM, right after setting up PWM |
| After Burner Complete | `$02`: CMD | `$03`: CMD and PWM, with FM = 1 in the same word write |
| Star Wars Arcade | CMD | PWM |

None of the three ever enables the H interrupt. Sega's Mars Check Program does, and its expected counts show what Sega meant the bits to do. It counts each SH-2's interrupts over 30 frames [MARS-CHECK, 68000 code at `$3D4C`-`$4222`; SH-2 code at `0x06000DF8`-`0x06000E86`]:

| Mask written | H count | Expected per frame | Accepted range per frame |
|--------------|---------|--------------------|--------------------------|
| `$0A` (V, CMD) | — | 1 V interrupt | 0.97-1.07 |
| `$0E` (V, H, CMD) | 0 | 224 H interrupts | 217-231 |
| `$8E` (HEN, V, H, CMD) | 0 | 256 NTSC, 313 PAL | 247-265 NTSC, 311-314 PAL |
| `$8E` | 5 | 42.7 NTSC, 52.2 PAL | 41.3-44.1 NTSC, 50.2-54.2 PAL |

So with HEN = 0 an H interrupt comes on each of the 224 displayed lines, and with HEN = 1 on every line of the frame. The PAL figure is the full 313 lines. The NTSC figure is 256, not the 262 lines of an NTSC frame, but the accepted range takes in 262 as well, so the program does not settle which.

### 0x20004002: standby change

Write only, word access. "Use with system (Boot ROM)": applications must never touch it [32X-HWM §3.2.2 p.30; 32X-OV p.41]. The manual's list describes it as activating the 32X's custom chip.

The Master's boot ROM writes it once, at power-on while ADEN = 0: it counts down 65,536 loops, writes 0 to `0x20004002`, sets the SH-2's own standby control register (`0xFFFFFE91`) to `$9F` and executes `sleep` [VRD-NOTES, 32X BIOS dump, Master `$0192`-`$01A4`]. This is the "Custom Standby" step at the start of the manual's boot flowchart [32X-HWM §5.1]. Neither emulator does anything when it is written [PICODRIVE, pico/32x/memory.c; ARES, md/m32x/io-internal.cpp].

### 0x20004004: H count

| Bits | Meaning |
|------|---------|
| 7-0 | Number of lines between H interrupts, minus 1: 0 = every line |

Sources: [32X-HWM §3.2.2 p.27 (scan)]. One register, shared by both SH-2s, as HEN is.

**A new value starts late.** The 32X keeps an internal counter and reloads it from this register at the end of each horizontal blank. A value written outside horizontal blank is not loaded until the next one ends, so the next interrupt can still come at the old interval. The manual works two examples: changing 0 to 1 during a horizontal blank gives the first interrupt at the second horizontal blank after it, and changing it outside a blank gives one more at the next horizontal blank first [32X-HWM §3.2.2 p.29]. Write it during vertical blank, and expect one interrupt at the old spacing.

**With HEN = 0, nothing comes during vertical blank.** The count goes on from the start of the next frame.

The emulators are weakest here. PicoDrive schedules H interrupts by time, every (*n* + 1) × 488.5 68000 clocks, not from real horizontal blanks, and its source calls the 32X H interrupt useless in practice. Ares counts real horizontal blanks but restarts the count as soon as the register is written <span class="tag emulator">emulator</span> [PICODRIVE, pico/32x/32x.c; ARES, md/m32x/m32x.cpp, io-internal.cpp]. PicoDrive's source also notes that games use H count as one more shared byte between the two SH-2s, which works because both can read and write it [PICODRIVE, pico/32x/memory.c]. Do that only in a program that never enables H interrupts.

### 0x20004006-0x20004012: the SH-2's view of DREQ

| Address | Register | SH-2 | Bits |
|---------|----------|------|------|
| `0x20004006` | DREQ control | Read only | 15 FULL, 14 EMPT (below); 2 68S; 0 RV |
| `0x20004008`, `0x2000400A` | Source address | Read only | As on the 68000 side |
| `0x2000400C`, `0x2000400E` | Destination address | Read only | As on the 68000 side |
| `0x20004010` | Length | Read only | The words still to come |
| `0x20004012` | FIFO | Read only | The source address for DMA channel 0 |

Sources: [32X-HWM §3.2.2 pp.30-31 (scan); 32X-OV pp.41-42].

**68S and RV** let the SH-2 watch the 68000. d32xr waits for 68S before it arms its DMA [D32XR, marshw.c]. The Master's VRES handler must check RV ([Pressing reset](boot.md#pressing-reset)). Sega's equates put the DREQ control byte at `0x20004007`, the low byte, which is the one that holds RV [32X-SUP2, register equates]. Star Wars Arcade reads the whole word and tests bit 0, which also works [SWA, SH-2 code at `0x06000588`]. Mortal Kombat II and After Burner Complete read the byte at `0x20004006` instead and test its bit 0, which is bit 8 of the register. No Sega source defines that bit, and on a console it reads 0 with RV = 1: notaz's test expects `$4001` from `0x20004006` [TESTPICO, t_32x_sh_defaults]. So those games never take the RV = 1 reset path; neither sets RV, so it does them no harm [MK2, SH-2 code at `0x06000356`; AB32X, SH-2 code at `0x0600029C`, `0x06002272`; [discrepancy 33](../appendices/discrepancies.md)]. Read RV as a word or from `0x20004007`.

**Bit 1** is printed as 0 on the SH-2 side. Sega's own Mars Check Program, two months older than the manual, expects it to read back whatever the 68000 wrote there <span class="tag disputed">disputed</span> [MARS-CHECK, 68000 code at `$3876`, SH-2 code at `0x06000D68`; [discrepancy 25](../appendices/discrepancies.md)]. Don't rely on it either way.

**Bits 15 and 14** report the frame buffer's write buffer, according to both Sega manuals: FULL = 1 when it has no room, EMPT = 1 when it is empty. Sega's equates call the byte "Frame Buffer FIFO Condition" [32X-HWM p.30; 32X-OV p.41; 32X-SUP2]. The emulators disagree with each other: PicoDrive always returns EMPT = 1 and FULL = 0, while Ares returns the DREQ FIFO's flags there, and d32xr's header names them as DMA flags, though it never reads them <span class="tag disputed">disputed</span> [PICODRIVE, pico/32x/memory.c; ARES, md/m32x/io-internal.cpp; D32XR, 32x.h; [discrepancy 32](../appendices/discrepancies.md)]. No game in the sources reads them.

### 0x20004014-0x2000401C: interrupt clear

| Address | Clears |
|---------|--------|
| `0x20004014` | VRES |
| `0x20004016` | V |
| `0x20004018` | H |
| `0x2000401A` | CMD |
| `0x2000401C` | PWM |

Sources: [32X-HWM §3.2.2 pp.27-28 (scan)]. Write only, word access; the value written does not matter. Each write clears the request for the SH-2 that makes it; both emulators keep all five separate per CPU [PICODRIVE, pico/32x/memory.c; ARES, md/m32x/io-internal.cpp]. Clear before returning, and read the same address back so the write has arrived before `rte` ([Interrupt controller](../sh2/intc.md#clearing-the-source-before-returning)).

## The VDP registers

The 32X VDP's registers sit at `$A15180-$A1518B` for the 68000 and `0x20004100-0x2000410B` for the SH-2s. Only the side that FM gives them to may use them. How they are used is in [The 32X VDP](vdp.md).

**Bitmap mode** (`$A15180`, `0x20004100`):

| Bit | Name | R/W | Meaning |
|-----|------|-----|---------|
| 15 | PAL | Read only | 0 = PAL console, 1 = NTSC |
| 7 | PRI | R/W | 0 = Mega Drive in front, 1 = 32X in front ([Compositing](compositing.md)) |
| 6 | 240 | R/W | 1 = 240 lines. PAL only |
| 1-0 | M1, M0 | R/W | 00 blank, 01 packed pixel, 10 direct colour, 11 run length |

**Screen shift control** (`$A15182`, `0x20004102`): bit 0 SFT, 1 = shift the picture one pixel left in packed pixel mode ([Fine horizontal scrolling](vdp.md#fine-horizontal-scrolling)).

**Auto fill** ([Auto fill](vdp.md#auto-fill)):

| Address | Register | Bits |
|---------|----------|------|
| `$A15184`, `0x20004104` | Length | 7-0: words to fill, minus 1 |
| `$A15186`, `0x20004106` | Start address | 15-0: word address in the frame buffer. Bits 15-8 stay fixed; bits 7-0 count up during the fill |
| `$A15188`, `0x20004108` | Data | 15-0. Writing it starts the fill |

**Frame buffer control** (`$A1518A`, `0x2000410A`):

| Bit | Name | R/W | Meaning |
|-----|------|-----|---------|
| 15 | VBLK | Read only | 1 = in vertical blank |
| 14 | HBLK | Read only | 1 = in horizontal blank |
| 13 | PEN | Read only | 1 = the palette may be accessed |
| 1 | FEN | Read only | 1 = the frame buffer may not be accessed (a fill is running, or a refresh) |
| 0 | FS | R/W | Which buffer is displayed; a write during display takes effect at the next vertical blank |

Sources: [32X-HWM §3.2.3; §3.3]. Every bit except FS and PAL takes effect from the next line [32X-HWM §3.3, register latch timing].

## Shared registers and simultaneous writes

| Register | Written by | When two write at once |
|----------|------------|------------------------|
| FM | The 68000 and either SH-2 | The last write wins at once, even against an access in progress [32X-HWM pp.19, 26] |
| Communication ports | All three CPUs | Undefined if the 68000 and an SH-2 write the same word at the same moment [32X-HWM §3.2.1] |
| PWM control | 68000: bits 3-0. SH-2: all | Not documented. Keep PWM to one CPU |
| PWM cycle and pulse widths | All three | Not documented |
| INTM, INTS | The 68000 sets them | [Disputed](../appendices/discrepancies.md) how they clear |
| DREQ addresses and length | The 68000 | The SH-2 only reads them |
| HEN, H count | Either SH-2 | One copy for both |
| Mask bits 3-0, interrupt clears | Each SH-2 its own | Separate per CPU |
| VDP registers, palette, frame buffer | The side that owns FM | The manual says the other side waits for FM; emulators drop its writes ([discrepancy 34](../appendices/discrepancies.md)) |

The two SH-2s cannot write at the same moment: they share one bus and take turns, one access at a time [32X-HWM §2.2]. So the only real collisions are between the 68000 and an SH-2, and the manual names only the communication ports and FM. A protocol that gives every shared word one writer at a time never meets the undefined case ([The one hazard](communication.md#the-one-hazard-a-word-that-changes-while-you-read-it)).

## In emulators

| What | PicoDrive | Ares |
|------|-----------|------|
| `$A15100` at power-on | `$0082`: REN and RES set | The same |
| RES | Writing 1 after 0 restarts both SH-2s; clearing ADEN shuts the 32X down | Writing 0 restarts both SH-2s |
| INTM, INTS | Read back the pending requests; a write replaces both | The same |
| Interrupt mask, bits 9-8 | ADEN and CART | The same |
| H interrupt | By time, not by line | By line, but a write restarts the count |
| `0x20004006` bits 15-14 | EMPT always 1, FULL always 0 | DREQ FIFO full and empty |
| VDP registers from the side without FM | The 68000 can still read them; its writes are dropped | Either side can still read them; writes are dropped |
| FEN | Set on every eighth read, imitating the pulses its authors saw on a console | Set during refresh and fills |
| PWM control bit 4 | Not stored | Stored, not used |
| Pulse width reads | Status flags only | Status flags plus the last value written |

Sources: [PICODRIVE, pico/32x/memory.c, 32x.c; ARES, md/m32x/io-external.cpp, io-internal.cpp, m32x.cpp]. Where the table differs from the manuals, the manuals are the better guide until a console test says otherwise.

## What to take away

- The 68000 and the SH-2s see the same offsets but different registers below `$20`. Only the ports and PWM are the same registers on both sides.
- Leave ADEN, RES, the standby register and SEGA TV alone. They belong to the boot.
- Raise CMD with `bset`, so you do not withdraw the other CPU's request.
- On the SH-2, write the interrupt mask as a byte at `0x20004001`, and carry HEN in every value if you use it.
- Change H count during vertical blank and expect one interrupt at the old spacing.
- Read RV as a word, or as the byte at `0x20004007`, never the byte at `0x20004006`.

## Open questions

- What does REN report, and how long does it stay 0 after a reset ([discrepancy 30](../appendices/discrepancies.md))?
- Does writing 0 to INTM or INTS withdraw a pending CMD on a console, as it does in both emulators?
- What do bits 15 and 14 of `0x20004006` report on a console ([discrepancy 32](../appendices/discrepancies.md))?
- What does the 32X do with bit 8 of the SEGA TV register, which PicoDrive stores?

## Sources

- [32X-HWM](../appendices/bibliography.md#32x-hwm): §2.2, §3.2.1-3.2.3 (pp.19-31, checked on the scans), §3.3, §4.1, §5.1
- [32X-OV](../appendices/bibliography.md#32x-ov): MD and SH side SYS REG (pp.34-43, checked on the scan)
- [32X-INTRO](../appendices/bibliography.md#32x-intro): adapter control register
- [32X-SUP2](../appendices/bibliography.md#32x-sup2): register equates
- [VRD-NOTES](../appendices/bibliography.md#vrd-notes): 32X BIOS dump (Master `$018C`-`$024C`); ROM (initial program, `$418`, `$4C0`, `$6F8`)
- [SWA](../appendices/bibliography.md#swa): SH-2 code at `0x06000588`, `0x0600093C`, `0x06000F2E`
- [MK2](../appendices/bibliography.md#mk2): SH-2 code at `0x060002B6`, `0x06000356`, `0x0600516C`
- [AB32X](../appendices/bibliography.md#ab32x): SH-2 code at `0x06000244`, `0x0600029C`, `0x06002168`, `0x06002272`
- [D32XR](../appendices/bibliography.md#d32xr): 32x.h, marshw.c, src-md/crt0.s
- [PICODRIVE](../appendices/bibliography.md#picodrive): pico/32x/memory.c, 32x.c, pwm.c
- [ARES](../appendices/bibliography.md#ares): md/m32x/io-external.cpp, io-internal.cpp, m32x.cpp, m32x.hpp, pwm.cpp
