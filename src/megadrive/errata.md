# Sega's technical bulletins

Between 1990 and 1994 Sega's Technical Support sent bulletins to developers: corrections to the manuals, hardware rules discovered after publication, and standards for approval. They are the Mega Drive's errata layer — a shipped game's odd habits (parking the Z80 around a pad read, rewriting one word after a DMA) are often a bulletin made flesh. This page lists every bulletin in our copy, grouped by what it is: rules that changed how code is written, standards and paperwork, and notes that only applied to development hardware. Each entry says what was wrong, what Sega told developers to do, and whether it still matters. The numbering skips #10; our copy has none, and whether one existed is unknown.

The deep treatments of the topics live in their own chapters; this page is the index.

## Rules that changed how code is written

**#3 — The interrupt that releases the Z80 bus (August 2, 1990).** If the 68000's main routine requests the Z80 bus and an interrupt handler then makes and releases its own request, the main routine resumes writing sound RAM with the Z80 running again: corrupted sound RAM, sound that sometimes stops. The fix is to disable interrupts around every bus request. The bulletin also carries Sega's first pad-reading sample, already wrapping the port read in a bus request and computing edge data (newly pressed buttons) with an XOR. Still matters; see [Z80 bus control](z80.md#taking-the-bus) and [Controllers and I/O ports](io.md#in-a-shipped-game).

**#4 — A wait state the Z80 can see (September 7, 1990).** Reading `$A10000-$A100FF` without holding the Z80 bus changes the port access's wait state from 250 ns to 110 ns, and the Z80 then misreads **all** further data through its bank window <span class="tag manual">manual</span> [MD-TB #4]. The fix: a bus request around the port reads, released afterwards. Still matters; the mechanism is the one described in [Z80 bus control](z80.md#when-sega-says-to-hold-it).

**#5 addendum 3 — When the Z80 cannot do a 68000 bus access (November 26, 1990).** If the 68000 touches `$A100xx` in the bus cycle just before the Z80 enters the main bus, the Z80's cycle is cut short and its data is wrong. Same rule and same cure as MD-SDM's [MD-SDM §5 S1]: stop the Z80 around the port access, or synchronise to the vertical interrupt. The addendum also documents the line 224 problem — a line interrupt on line 224 colliding with the vertical interrupt and cancelling it — and the confusion an external interrupt can cause with both; see [Timing, interrupts and counters](vdp-timing.md#the-line-224-problem).

**#5 addendum 4 — DMA house rules and two more cautions (November 26, 1990).** Three rules for DMA beyond fill and copy: request the Z80 bus, keep the command's address-set writes based in RAM (the source of the ROM-DMA trap in [DMA](vdp-dma.md#three-rules-when-the-source-is-rom-or-ram)), and rewrite the leading word after a work-RAM-source DMA. It also notes that VDP registers 11-23 are unreachable unless register 1 bit 2 (Genesis mode) is set, and warns about save RAM: initialise it at power-up (do not trust the factory fill), check it for garbling, and keep nothing critical in the first and last words, which are the most likely to corrupt [MD-TB #5]. See [Cartridge hardware](cartridge.md#save-ram).

**#6 and #7 III — Pads that lie (April 2, 1991).** A worn pad can report up and down, or left and right, at once. Sega's ruling: read routines must cope — treat an impossible combination as a signal to re-read, and never assume the hardware filters it [MD-TB #6, #7]. Still matters; see [Controllers and I/O ports](io.md).

**#7 — Software guidelines addenda (1991; no date header in our copy).** A bundle: the nesting rule again (#3), the YM2612 busy flag again (#11), the repeated-reset rule again (#12), a correction declaring the software manual's byte access to VRAM, CRAM and VSRAM null and void — data port access is word or longword only [MD-TB #7 II], folded into this book's VDP chapters — and the bank register correction below.

**#13 — Corrections to the software manual (September 9, 1991).** The same two corrections stated formally: VDP data accesses are word or longword only, and the Z80 bank register is set by the Z80, never the 68000 [MD-TB #13]. Both are stated as rules of the machine in [Z80 bus control](z80.md#the-bank-window-from-the-z80-side).

**#11 — Sound stops during play (September 9, 1991).** Reading the YM2612 busy flag at address `$4001` can return "not busy" while the chip is busy, and sound dies during play. Read the flag at `$4000` and nowhere else [MD-TB #11]. (The bulletin's own text names a YM2616 in one line and the YM2612 in the next — a typo, the chip is the YM2612.) Still matters; see [The Z80 and sound](sound.md#the-rules).

**#12 — Repeated resets (September 9, 1991).** The reset button resets the CPUs but not the VDP. A DMA in progress continues across the reset, and a VDP access issued right after re-entering the initial program can be silently ignored. Sega's fix: after the initial program, poll the status register's DMA busy bit before touching the VDP, and do not start a DMA immediately after a reset [MD-TB #12]. Still matters to any code that re-runs its start-up path.

**#15 — VRAM read waits (April 5, 1993).** After a VRAM read and before the next address set, the CPU must wait: more than 116 clocks during the display or horizontal blank, more than 12 during vertical blank <span class="tag manual">manual</span> [MD-TB #15]. Consecutive reads without a new address set are fine. Reads are the rare case — most code writes — which is why the rule is little known.

**#16 — New peripherals (April 5, 1993).** Written as the 6-button pad, mouse and multitap shipped. Register 11's IE2 bit must be 0 unless the external interrupt is really used (the address checker flags it otherwise); pads are read from the vertical interrupt, once, with the device ID re-checked every frame and no more TH toggling than needed [MD-TB #16]. The whole protocol story is in [Controllers and I/O ports](io.md#the-6-button-pad).

**#20 — Games over 16 Mbits (July 8, 1993).** Three parts. First, a software rule that still matters: if the main routine and an interrupt handler can both touch the VDP, either guard it with a "transferring" flag that the handler checks, or mask interrupts from the address set to the end of the data [MD-TB #20]. Second, electrical advice for EPROM development boards — keep the chip count low (about four loads is stable), prefer large devices, and expect the low-power Mega Drive 2 to be the strictest. Third, the capacity map and bank-switching scheme that became the standard cartridge bank chip, covered in [Cartridge hardware](cartridge.md#bank-switching-beyond-4-mb).

**Mega Drive Technical Info #9 — the header's `$1F0` field changes (October 6, 1994).** The three region characters at `$1F0` are replaced by one ASCII hexadecimal digit, the operation hardware code, with spaces after it. The digit says which of the four machine types (domestic or overseas, NTSC or PAL, read from `$A10001`) the program runs on, `F` meaning all of them; Sega checked it at submission, and it applies to the 32X as well [MD-TB, MD Tech Info #9]. Still matters for new ROM headers; see [Mega Drive ROM header and checksum](../howto/md-header.md).

**The address checker (October 28, 1994).** Not a bulletin but the specification of Sega's checking tool. It watches for access to prohibited areas and for register misuse, sees only the code that actually runs, and finds no bugs of any other kind [MD-TB, address checker]. Its memory map is cited in this book for what Sega considered legal (for example the 32X ID location, [discrepancy 2](../appendices/discrepancies.md)).

## Standards and paperwork

**#5 — the ID table (November 26, 1990).** Two cartridge header formats, one for Sega of America (`GM MK-XXXX`) and one for third parties (`GM T-XXXXXX`), replacing the manual's pages. The header fields are described in [Mega Drive ROM header and checksum](../howto/md-header.md).

**#8 — content standards (undated).** Sega of America's approval policy: no sexually suggestive content, no ethnic or religious stereotypes, no excessive violence, no profanity, and so on. A licensing document, not a technical one; it explains what shipped, not how.

**#9 — game standards (revised January 3, 1991).** The user-interface rulebook: the logo-title-demo loop and its timings, Start as pause with sound silenced and "PAUSE" shown, button semantics (A special, B cancel, C decide), two-cell side margins for important displays because some televisions crop the edges. Conventions of the era rather than laws of the hardware; the margins and the pause behaviour aged well.

**#14 — ROM splitting (September 5, 1991).** Masters submitted as 128 KB even and odd interleaved files for the EPROM boards, with Sega's own splitting utilities. Manufacturing practice; irrelevant to a modern build, relevant to reading archival masters.

**#18 — lockout code reminder (May 28, 1993).** Every cartridge must contain lockout code — software that refuses to run on machines outside the header's country list — and QA would bug a game without it [MD-TB #18]. Not to be confused with TMSS, the later consoles' hardware check for `SEGA` written to `$A14000`: the lockout is the game policing the machine, TMSS is the machine policing the game.

**#19 — Mega CD, non-US market (July 6, 1993).** Market rules: no TM or R beside the logo in Japan, TM required in the US and Europe, PAL versions of equal quality to NTSC. Paperwork.

## Development hardware only

**#1 — Microtec example errors (March 13, 1991).** Typos in Sega's C toolchain examples (a stray semicolon, a wrong link command, a misspelled compiler option). Correcting them is pointless now; the bulletin is a reminder that Sega distributed a C toolchain at all.

**#2 — Loader board modification (June 19, 1990).** Two pull-up resistors and a jumper wire for the parallel-port ROM loader, to prevent loading errors. Hardware soldering advice for a device that barely survives in museums.

**#15 part 2 — Super Target IC 19 (April 5, 1993).** The Super Target development system acknowledged accesses to illegal addresses so the CPU would not hang — which hides a real difference: on a production console an access with no acknowledge can hang the machine. Sega's advice was to pull IC 19 so the dev box shows production behaviour [MD-TB #15]. The lesson outlives the hardware: never touch unmapped areas.

**#17 — recommended EPROMs (May 25, 1993).** A chip list for the development boards, with the note that Intel 27C020 2 Mbit devices were found unreliable. Relevant only to rebuilding old development cartridges.

## What still matters

Collected in one place, the bulletins' rules a new program still needs: a Z80 bus request around port reads and around DMAs, interrupts masked around bus requests and around VDP address-set-plus-data sequences, word or longword only on the VDP data port, the busy flag read at `$4000`, the DMA busy bit checked after a reset, impossible pad values handled, IE2 left at 0, the wait after a VRAM read, and a correct `$1F0` code in the header. The rest is history — but it is why shipped code looks the way it does. Aerobiz's habit of parking the Z80 before every DMA and every pad read is addendum 4, bulletin #4 and bulletin #3, all visible in one routine [AB-DISASM, ConfigVDPDMA.asm, InitInputArrays.asm].

## Open questions

- Was there ever a bulletin #10? Our copy jumps from #9 to #11.
- Bulletin #7's date. Its content sits between April and September 1991.

## Sources

- [MD-TB](../appendices/bibliography.md#md-tb): bulletins #1-#9, #11-#20, Mega Drive Technical Info #9, and the Mega Drive/32X address checker specification
- [MD-SDM](../appendices/bibliography.md#md-sdm): §5 S1, the `$A100xx` rule stated on Sega's Japanese track
- [AB-DISASM](../appendices/bibliography.md#ab-disasm): ConfigVDPDMA, InitInputArrays — the bulletins visible in shipped code
