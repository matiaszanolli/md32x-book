# DREQ and the FIFO

The SH-2s cannot read the Mega Drive's work RAM, and the 68000 cannot write SDRAM. The one bulk path between them is a FIFO: the 68000 writes words to a 32X register, and each SH-2 can have its DMA controller take them from there into SDRAM through request line DREQ0. This chapter is the 68000's half of that path: the registers, the sequence, how the two sides agree on when to start, what it costs, and how it fails. The SH-2's half, setting up DMA channel 0, is in [DMA controller](../sh2/dmac.md#channel-0-the-fifo).

## Registers

| 68000 | SH-2 | Register | Notes |
|-------|------|----------|-------|
| `$A15106` | `0x20004006` | DREQ control | Below |
| `$A15108`, `$A1510A` | `0x20004008`, `0x2000400A` | Source address | Not used by the hardware |
| `$A1510C`, `$A1510E` | `0x2000400C`, `0x2000400E` | Destination address | Not used by the hardware |
| `$A15110` | `0x20004010` | Length, in words | Bits 1 and 0 are fixed at 0, so the length is a multiple of 4. 0 means 65,536. Counts down by one for each word the 68000 writes to the FIFO (see step 5 below), and reads back the remaining count |
| `$A15112` | `0x20004012` | FIFO | The 68000 writes words here; SH-2 DMA channel 0 reads them |

**DREQ control**, 68000 side [32X-HWM §3.2.1, DREQ control register]:

| Bit | Name | Meaning |
|-----|------|---------|
| 7 | FULL | 1 = the FIFO has no room. Read only |
| 2 | 68S | Write 1 to start a transfer, 0 to stop it at once. Clears itself when the length reaches 0 |
| 0 | RV | Gives the cartridge back to the Mega Drive map; unrelated to the FIFO. See [The RV bit](architecture.md#the-rv-bit) |

The SH-2 sees 68S and RV as read-only bits of `0x20004006`. Bits 15 and 14 of the same SH-2 register are FULL and EMPTY for the *frame buffer's* write buffer, not for this FIFO, according to both Sega manuals. PicoDrive follows them; Ares reports this FIFO's flags there instead <span class="tag disputed">disputed</span> [32X-HWM §3.2.2 p.30; PICODRIVE, pico/32x/memory.c; ARES, md/m32x/io-internal.cpp; [discrepancy 32](../appendices/discrepancies.md)]. See [System registers](registers.md#0x20004006-0x20004012-the-sh-2s-view-of-dreq).

The source and destination registers are not used by the transfer. The SH-2 decides where the data goes when it programs its DMA [32X-HWM §3.2.1]. The 68000 can write them, but the SH-2 can only read them [32X-HWM §3.2.2 p.30], so they work as spare mailbox space for passing an argument from the 68000 to the SH-2: 23 bits in the source register and 24 in the destination [32X-HWM §3.2.1 pp.21-22, checked on the scan]. d32xr packs an argument into them for the SH-2 to read [D32XR, src-md/crt0.s, marshw.c]. After Burner Complete, which never uses the FIFO, writes object parameters alongside the communication ports: words to `$A1510A`, `$A1510E` and `$A15110`, and a byte to `$A1510D`, the low half of `$A1510C` and the only part of that register that is stored. Its Master reads them back as extra mailbox words [AB32X, 68000 code at `$887348`; SH-2 code at `0x0600257C`].

The length register works for this too, because nothing counts it down while 68S is clear, but as a mailbox it carries only 14 bits: bits 1 and 0 always read back 0 [32X-HWM §3.2.1 p.22, checked on the scan; PICODRIVE, pico/32x/memory.c; ARES, md/m32x/io-external.cpp]. Bit 0 of `$A1510A` is fixed at 0 in the manual and in PicoDrive, though Ares keeps it [32X-HWM §3.2.1 p.21, checked on the scan]. After Burner never needs the lost bits: its Master shifts the length word right by 3 and the source word right by 5 before using them [AB32X, SH-2 code at `0x0600259C`, `0x06002622`].

**The FIFO holds eight words, in two blocks of four.** Sega's block diagram shows two 4-word FIFOs between the 68000 and the SH-2s, and both emulators use eight words [32X-HWM §3.5, Figure 3.28 p.67; PICODRIVE, pico/pico_int.h; ARES, md/m32x/m32x.hpp]. Sega's Mars Check Program tests exactly that: with 68S set and no DMA running, FULL must still read 0 after seven words and 1 after the eighth, and clear again when 68S is cleared [MARS-CHECK, 68000 code at `$1ADA`-`$1B1C`].

## A transfer, step by step

1. **The SH-2 arms DMA channel 0:** source `0x20004012`, destination in SDRAM (preferably its cache-through address), count = the length in words, Sega's CHCR0 value. When it clears TE from the previous transfer, it writes `$44E0` back, not 0 ([How it fails](#how-it-fails)). See [DMA controller](../sh2/dmac.md#channel-0-the-fifo).
2. **The 68000 writes the length** (rounded up to a multiple of four words) to `$A15110`.
3. **The 68000 sets 68S** (`$04` to `$A15107`). A 2021 forum report says the first FIFO write had to wait at least 11 NOPs after this. It was seen in the Fusion 3.64 and Gens KMod 0.7.3 emulators, not on a console <span class="tag emulator">emulator</span> [GENDEV-DREQ]. d32xr's maintainer later wrote that no delay is needed once the SH-2 clears TE correctly [GENDEV-SVDP, posts of 5 January 2025 and 29 August 2026]. d32xr and Virtua Racing Deluxe both wait for the SH-2 to answer through a communication port between setting 68S and the first write, which leaves a gap anyway (below).
4. **The 68000 writes the data**, a word at a time, to `$A15112`. Sega asks for a FULL check after each group of four words, waiting while it is set, because the SH-2's DMA may answer more slowly than the 68000 writes, depending on what else is using the bus [32X-HWM §5.3, DMA restrictions, item 4] <span class="tag manual">manual</span>. That wait can hang: if the DMA stops taking words, FULL never clears. A developer reported exactly this on a console in 2012 ([How it fails](#how-it-fails)), so give the wait a time limit.
5. **Each word the 68000 writes decrements the length.** When it reaches 0, 68S clears itself. The manual says only that the register counts down at each transfer and reads back the remaining count [32X-HWM §3.2.1 p.22, checked on the scan]. PicoDrive's source notes, as tested, that the length counts down and 68S clears even when no SH-2 DMA is armed, so the count follows the 68000's writes, not the DMA's reads. Ares counts the same way <span class="tag emulator">emulator</span> [PICODRIVE, pico/32x/memory.c; ARES, md/m32x/io-external.cpp]. So 68S reading 0 means the 68000 has written every word, not that the SH-2 has them.
6. **The SH-2's channel sets TE** when its count runs out. The data is then in SDRAM, but not in either SH-2's cache: purge before reading it through cached addresses ([Cache](../sh2/cache.md#keeping-the-views-in-step)).

## Agreeing on start and end

The hardware has no way to tell the 68000 that the SH-2 is ready, or the SH-2 that the data has all arrived. Programs build that out of the [communication ports](communication.md) and the CMD interrupt.

**d32xr** [D32XR, src-md/crt0.s `dma_to_32x`; marshw.c]:
1. The 68000 raises CMD on the Master and waits until communication port 0 reads `$A55A` (idle), then writes `$FF10` ("start a FIFO transfer").
2. The Master's CMD handler steps port 0 on, and both sides step it once more for each stage. Meanwhile the 68000 clears 68S, puts the length in port 1 (`$A15122`) and the argument in the source and destination registers.
3. The Master asks its program for a destination. It refuses by changing the length in port 1; otherwise it waits for 68S.
4. The 68000 sets the length and 68S. The Master sees 68S, arms channel 0 and returns.
5. The 68000 waits for port 0 to return to idle, then writes four words at a time with a FULL check after each group.
6. It raises CMD again and writes `$FF20` ("end"). The Master waits for TE, clears it by writing `$44E0`, acknowledges, and hands the buffer to its program.

d32xr uses this only in its Mega-CD build, to stream RoQ video from the Mega-CD's Word RAM [D32XR, src-md/scd_roq.c].

**Virtua Racing Deluxe**, as the VRD project's disassembly describes it, sends one 2,560-byte block of render parameters per picture. The 68000 sets the length to `$500` words and sets 68S, posts a command in port 0, and waits for an acknowledge bit in the ports that says the SH-2 has armed its DMA. It then copies the block from `$FF6000` with ten calls to a routine of 128 unrolled word writes, with no FULL check at all [VRD-NOTES, analysis/FRAME_RATE_ARCHITECTURE.md; disasm/modules/68k/game/render/mars_dma_xfer_vdp_fill.asm] <span class="tag emulator">emulator</span>. That works only if the SH-2's DMA always keeps up. A 68000 word write every 12 of its clocks is one every 36 SH-2 clocks. If the FIFO is empty when the DMA stalls, and each word frees its place as soon as the DMA takes it, the stall can last about eight of those writes, around 290 SH-2 clocks, before the FIFO overflows. If words instead move between the two 4-word blocks four at a time, a stall that starts with one block waiting for the DMA leaves room for only four more words: the margin is about half. No source we have says which ([Open questions](#open-questions)).

Leaving out the FULL check is a risk, but it is also what the 2012 report of stalling transfers recommended, because a FULL wait hung while a further write restarted the DMA ([How it fails](#how-it-fails)). VRD-NOTES gives no reason for the missing check, so whether Sega's programmers chose it as a workaround is not known. The ROM copy behind this description is not the retail original (see [VRD-NOTES](../appendices/bibliography.md#vrd-notes)).

Star Wars Arcade does not use the FIFO. Its SH-2 program never sets up channel 0, except to switch it off on reset [SWA, SH-2 program]. Neither does Mortal Kombat II, which needs 668 bytes a frame from the 68000 and moves them through the communication ports instead, ten bytes per handshake, with the Master's CPU taking part in every step ([Communication](communication.md#bulk-data-through-the-ports)) [MK2, SH-2 program]. Through the FIFO, the same block would cost the 68000 about 4,000 clocks with VRD's unrolled loop and the Master nothing but the DMA's bus cycles. After Burner Complete does not use it either. It never arms a DMA channel or reads `0x20004012` [AB32X, SH-2 program]. Knuckles' Chaotix does ([below](#knuckles-chaotix-command-lists)).

### Knuckles' Chaotix: command lists

Knuckles' Chaotix is the one retail game read for this book that uses the FIFO, and it uses it to send the Master its work, not bulk data.

**Command lists.** The 68000 builds a list of commands for the Master in work RAM, ending at `$FFD45E`, and closes it with a 0 word. To send it, it masks interrupts, writes the length, rounded up to whole 4-word groups, to `$A15110`, sets `68S`, raises CMD on the Master and waits for INTM to clear. Then it writes the list four words at a time and waits for FULL to clear after each group, as Sega's manual asks [CHAOTIX, 68000 code at `$003202`-`$003260`; 32X-HWM §5.3 p.87]. For each transfer the Master's CMD handler arms channel 0 with Sega's settings, taking the destination from `0x06003814` ([DMA controller](../sh2/dmac.md#channel-0-the-fifo)) [CHAOTIX, SH-2 code at `0x06001334`-`0x06001362`].

**On the Master.** `0x06003814` and the longword after it hold the addresses of two 1 KB buffers (`0x06004B10` and `0x06004F10` in the loaded program). When the Master starts on a new list it swaps the two, so that the next transfer fills the other buffer. It purges the filled buffer from its cache, 64 lines, by writing to the purge area at `0x40000000` plus each line's address. Then it runs the list: each command's first byte selects a routine from a jump table [CHAOTIX, SH-2 code at `0x06000984`-`0x060009B4`]. That purge is the one retail example read for this book of the rule in [DMA and the cache](../sh2/dmac.md#dma-and-the-cache), and the buffer size caps a list at 1 KB.

**A four-word message.** A second routine sends a single group. It sets the length to 4 and `68S`, raises CMD and waits as above, then writes four words built from work RAM: the bytes at `$FFDFF3` and `$FFDFF5`; bits 2-1 of `$FFDFF7` with the byte at `$FFE039` shifted right by 2; and the word at `$FFE03A` shifted left by 6 with its low byte cleared, written twice to fill the group. It then waits for communication port 0 to clear, resets the list, and sends two lists that hold only the closing 0, each followed by the same handshake [CHAOTIX, 68000 code at `$0019A8`-`$001A3E`]. What those work RAM variables hold has not been decoded. The four words land in the same buffer as the lists, so the Master presumably reads them as a short list; this is inference, not traced. Eight bytes would fit in the communication ports, which hold 16, and the game sends them through the FIFO and DMA anyway. The command lists, up to 1 KB, would not fit.

## What it costs

The 68000's write loop sets the speed. The SH-2's DMA moves a word in a few of its own clocks, far faster than the 68000 can supply them. Counting 68000 clocks <span class="tag manual">manual</span>:

| Loop | 68000 clocks per word | Throughput at 7.67 MHz | 2,560 bytes take |
|------|------------------------|------------------------|------------------|
| Unrolled `move.w (a1)+,(a2)`, no FULL check (VRD) | 12 | about 1.25 MB/s | 15,700 clocks with the calls, 12% of a 60 Hz frame |
| Four writes, then `btst #7` and `dbra` (d32xr) | about 21.5 | about 700 KB/s | 27,500 clocks, 22% of a frame |

These are instruction counts, not measurements. They assume the 32X registers take no wait states from the 68000 side [32X-HWM §4.4], and that the source is in work RAM. On the SH-2 side, the DMA takes bus cycles away from the CPUs while it runs, one word at a time in cycle-steal mode ([Bus controller](../sh2/bsc.md#two-sh-2s-one-bus)).

So the FIFO is for blocks of a few KB per frame: scene parameters, a decoded video chunk, a table. For anything bigger, put the data in the cartridge and let the SH-2s read it themselves.

## How it fails

- **The SH-2 is not armed.** The FIFO fills, FULL stays set and a 68000 that waits for it hangs. Always confirm the DMA is armed before writing, and put a time limit on the FULL wait.
- **The DMA stops partway and FULL sticks** <span class="tag disputed">disputed</span>. In 2012 Chilly Willy reported from a console that DREQ sometimes stopped triggering the SH-2's DMA, at random. FULL then stuck at 1 and a 68000 waiting on it hung. Ignoring FULL and writing again restarted the DMA but lost one word, 20 to 120 words in a 65,536-word transfer. He suspected a hardware bug left in the production chips, and in 2014 advised short transfers with checksums, a timeout on the SH-2 side and retries [GENDEV-SVDP, posts of 31 October 2012 and 29 October 2014]. In January 2025 Vic, who maintains d32xr, traced it to the SH-2 code, which cleared TE by writing 0 to CHCR0. Writing `$44E0` instead, which keeps the bits Sega's settings fix [32X-HWM §5.3, DMA controller settings], made the transfers work. He added that this held only while the SH-2 waited in a loop for the transfer to end, and that words were still lost or corrupted when it went on working. In August 2026 he wrote that with the fix the transfer simply works, with no checksums or delays, and pointed to d32xr, whose Master arms the channel and returns to its own work [GENDEV-SVDP, posts of 5 and 14 January 2025 and 29 August 2026; D32XR, marshw.c]. None of these reports names a console revision or gives a test ROM ([discrepancy 29](../appendices/discrepancies.md)). Clear TE by writing `$44E0`, and keep the time limit on the FULL wait so a stalled transfer is caught instead of hanging the 68000.
- **The lengths disagree.** The 68000's count drops as it writes and TCR0 as the channel reads. If TCR0 is smaller than the 68000's length, the channel stops early, the words after it stay in the FIFO, and once it fills FULL stays on. If TCR0 is larger, the 68000's count reaches 0 first and clears 68S, so no more words go in and the channel never sets TE. Round both to the same multiple of four.
- **Writing without 68S** does nothing: the words are dropped. PicoDrive notes this as tested [PICODRIVE, pico/32x/memory.c] <span class="tag emulator">emulator</span>.
- **Writing when FULL** loses the word in both emulators. Sega's manuals do not say what the hardware does. The 2012 report says that when the DMA had stalled, a write made while FULL was set restarted it and one word was lost. That was with the CHCR0 clearing later blamed for the stall <span class="tag disputed">disputed</span> [GENDEV-SVDP, post of 31 October 2012]. Check FULL every four words, as Sega asks, with a time limit on the wait.
- **Stale cache.** DMA writes past the cache. Purge or use cache-through addresses ([DMA controller](../sh2/dmac.md)).
- **Reset mid-transfer.** Sega's VRES handler turns the DMA off and resets CHCR0, so a cut-off transfer cannot run on into the restarted program ([DMA controller](../sh2/dmac.md#channel-0-the-fifo)). On the 68000 side, writing 0 to 68S stops the transfer [32X-HWM §3.2.1]. The manual does not say whether that also empties the FIFO. Both emulators empty it <span class="tag emulator">emulator</span> [PICODRIVE, pico/32x/memory.c; ARES, md/m32x/io-external.cpp].
- **Early development boards** (version 1.x) could not take more than `$100` words per transfer [32X-HWI item 10]. Production units do not have this limit.

## The capture mode that was dropped

Sega's April 1994 introduction shows a different DREQ control layout. FULL is at bit 15, and a DMA bit at bit 1 selects a "DMA write" mode: the 32X would capture the data of a Mega Drive VDP DMA whose source address matched the source register, valid only with a Mega-CD attached [32X-INTRO, DREQ control register]. The later hardware manual has FULL at bit 7, bit 1 fixed at 0, and only CPU writes [32X-HWM §3.2.1]. A technical bulletin then says capture DMA from Word RAM cannot be used, because its data fetch timing is wrong [32X-TI item 13]. Both emulators still store a bit 1 <span class="tag disputed">disputed</span> ([discrepancy 25](../appendices/discrepancies.md)). Use the hardware manual's layout and CPU writes only.

## In emulators

- **PicoDrive** moves the FIFO's words to the armed SH-2 four at a time, at once, and puts that SH-2 to sleep for the duration. It drops writes made without 68S or when full, and empties the FIFO when 68S is cleared. Length and 68S count down on each 68000 write even with no DMA armed, which its source marks as tested <span class="tag emulator">emulator</span> [PICODRIVE, pico/32x/memory.c, pico/32x/sh2soc.c].
- **Ares** keeps an 8-word FIFO and raises DREQ0 whenever it is not empty. It counts the length down on each 68000 write, drops writes without 68S or when full, and empties the FIFO when 68S is cleared. Its source says the real FIFO's two-block structure is not modelled, and adds a delay for Night Trap's last write <span class="tag emulator">emulator</span> [ARES, md/m32x/io-external.cpp, md/m32x/m32x.hpp].

Neither models how fast the SH-2 drains the FIFO, or the bus time the DMA takes. A 68000 loop with no FULL check, like VRD's, therefore cannot fail in either. Nor does either model the stall reported in 2012: the code behind that report worked in the Fusion emulator and failed only on the console [GENDEV-SVDP, post of 29 October 2012].

## Open questions

- What happens on a console when the 68000 writes while FULL: is the word dropped, does an older word get overwritten, or does the 68000 wait? The 2012 report says that such a write, made after the DMA had stalled, restarted the DMA and lost one word.
- With TE cleared by writing `$44E0`, can a transfer still lose or corrupt words while the SH-2 that owns the channel keeps working? d32xr's maintainer said yes in January 2025 and no in August 2026 ([discrepancy 29](../appendices/discrepancies.md)).
- Is any delay needed on a console between setting 68S and the first FIFO write? The only report of one comes from emulators.
- Do words move between the FIFO's two 4-word blocks one at a time or four at a time? That decides how long the SH-2 side can stall before a loop with no FULL check loses data.
- How long can the SH-2 side stall the FIFO in practice, for example while the other SH-2 fills a cache line from cartridge ROM?

## Sources

- [32X-HWM](../appendices/bibliography.md#32x-hwm): §3.2.1 DREQ registers (68000 side pp.21-22, SH-2 side p.30), §3.5 Figure 3.28 p.67, §4.4, §5.3 DMA restrictions and DMA controller settings
- [GENDEV-SVDP](../appendices/bibliography.md#gendev-svdp): posts of 29 and 31 October 2012, 29 October 2014, 5 and 14 January 2025, 29 August 2026
- [GENDEV-DREQ](../appendices/bibliography.md#gendev-dreq): post of 6 February 2021
- [32X-INTRO](../appendices/bibliography.md#32x-intro): DREQ control register
- [32X-TI](../appendices/bibliography.md#32x-ti): item 13
- [32X-HWI](../appendices/bibliography.md#32x-hwi): item 10
- [D32XR](../appendices/bibliography.md#d32xr): src-md/crt0.s, src-md/scd_roq.c, marshw.c
- [VRD-NOTES](../appendices/bibliography.md#vrd-notes): analysis/FRAME_RATE_ARCHITECTURE.md, disasm/modules/68k/game/render/mars_dma_xfer_vdp_fill.asm
- [SWA](../appendices/bibliography.md#swa): SH-2 program
- [MK2](../appendices/bibliography.md#mk2): SH-2 program
- [AB32X](../appendices/bibliography.md#ab32x): SH-2 program, code at `0x0600257C`-`0x06002622`; 68000 code at `$887348`
- [PICODRIVE](../appendices/bibliography.md#picodrive): pico/32x/memory.c, pico/32x/sh2soc.c, pico/pico_int.h
- [ARES](../appendices/bibliography.md#ares): md/m32x/io-external.cpp, md/m32x/m32x.hpp
