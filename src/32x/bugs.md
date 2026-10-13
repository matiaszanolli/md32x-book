# Hardware bugs and workarounds

Sega shipped the 32X with known faults and described them, with workarounds, in a handful of bulletins written between July and September 1994, with a revised sample sent out in December: a supplement to the hardware manual on the SH-2's interrupts, a numbered list of technical notes, and an attachment with sample code for the reset problem [32X-SUP2; 32X-TI; 32X-TIA1]. Some of the problems were in development boards and were fixed before release; others are in every console sold. Others again were found later, by developers and emulator authors.

This chapter is the index: each problem, Sega's fix, where the book explains it, and what retail games actually do about it. The main three come from three developers whose SH-2 start-up and reset code share nothing beyond Sega's samples: Star Wars Arcade from Sega InterActive, After Burner Complete from Rutubo Games (both published by Sega) and Mortal Kombat II from Probe. That makes their interrupt handlers three separate implementations of the same workaround. Their reset handlers are different: they descend from Sega's sample, so a defect they share there has one origin ([Sega's sample code in the games](../appendices/sample-code.md)).

## Problems in production consoles

| Problem | Sega's fix | Retail games | Details |
|---------|------------|--------------|---------|
| The SH-2 can miss an external interrupt, or jump through the wrong vector | One entry routine for every vector, dispatch on the level in SR, and TOCR written with fixed values in every handler (the revised sample of September 1994; the first sample flipped bit 1, which can handle an interrupt twice) | All three apply it, each in its own way; only Mortal Kombat II follows the revision | [Below](#the-sh-2-interrupt-flaw) |
| A cleared interrupt fires again if the handler returns too soon | Read the clear register back and leave a gap before `rte` | All three read back | [Interrupt controller](../sh2/intc.md#clearing-the-source-before-returning) |
| Reset pressed while RV = 1 can leave the console unable to restart | The Master's VRES handler checks RV and resets the whole 32X | Of five games examined, only Knuckles' Chaotix has a handler that would work, and it is the only one that sets RV | [Below](#reset-while-rv--1) |
| 68000 interrupts while RV = 1 | Mask them | — | [The RV bit](architecture.md#the-rv-bit) |
| 12 bytes of the cartridge read wrong while RV = 1 | Keep data for VDP DMA away from `$001070`, `$002070`, `$003070` | — | [The RV bit](architecture.md#the-rv-bit) |
| Save memory made of FRAM can be read and written only with RV = 1; SRAM does not care | Set RV around FRAM accesses | Knuckles' Chaotix sets RV around every save access (its chip type is not recorded) | [Save RAM on the 32X](../megadrive/cartridge.md#save-ram-on-the-32x) |
| On cartridges over 16 Mbit, `$200000-$3FFFFF` may not show ROM at power-on | Write 0 to `$A130F1` through the vector ROM, once, after power-on | Mortal Kombat II (32 Mbit) and Star Wars Arcade (20 Mbit) skip it; Knuckles' Chaotix (24 Mbit) does it | [Below](#cartridges-over-16-mbit) |
| A Z80 write to the 32X's areas locks up the 68000 | Let the Z80 read the 32X, never write | — | [The Z80's view](architecture.md#the-z80s-view) |
| Z80 PSG writes with its bank window on the cartridge or frame buffer can corrupt 32X reads and registers | Point the bank window elsewhere first | — | [The rules](../megadrive/sound.md#the-rules) |
| SFT is ignored on a line whose table entry ends in `$FF` | Avoid those addresses for shifted lines | — | [Fine horizontal scrolling](vdp.md#fine-horizontal-scrolling) |
| Byte writes from the SH-2 to the PWM pulse width registers | Write words | — | [PWM audio](pwm.md#registers) |
| A Mega Drive VDP DMA from the Mega-CD's Word RAM, with a 32X attached, fetches undefined data | Do not use it | — | [Discrepancy 25](../appendices/discrepancies.md) |
| Consoles with the slower 315-5818 interface chip occasionally garble 68000-SH-2 communication | Do final tests on a 315-5818A unit; make protocols tolerate a bad read | — | [The one hazard](communication.md#the-one-hazard-a-word-that-changes-while-you-read-it) |

Sources: [32X-SUP2; 32X-TI items 7-15, 19, 22; 32X-TIA1]. Retail evidence is in the sections below.

## The SH-2 interrupt flaw

The SH-2 chips in the first production consoles have a fault in how they take external interrupts: one can be missed if it arrives while the CPU is accepting another, and with several at once the CPU can take the wrong vector, though SR still gets the right level. Sega's development boards needed SH-2 cut 2.3 or later to work at all, and a later cut (2.5) of the evaluation chip fixed the fault, but Sega warned that the first consoles used the unfixed chip, so every program must carry the workaround <span class="tag manual">manual</span> [32X-SUP2, limitations, precautions; 32X-TI item 5]. Morita's FAQ instead names cut 2.5 as the faulty chip <span class="tag disputed">disputed</span> [MORITA-FAQ; [discrepancy 41](../appendices/discrepancies.md)]. Nothing tells a program which chip it is running on.

The workaround brings a fault of its own. The free-running timer's output is wired to the lowest interrupt request line, and when two kinds of interrupt are in use its change can make the CPU accept one interrupt twice. Sega revised the sample handler on 20 September 1994 to prevent it and sent the revision out with Technical Bulletin #27 in December, which describes the fault [32X-TB27]. A new program should copy the revised sample: fixed values written to TOCR, not a bit flipped.

The rules and the workaround are in [Interrupt controller](../sh2/intc.md#segas-rules-the-sh-2-interrupt-flaw), and the free-running timer set-up they depend on is in [Timers](../sh2/timers.md). How the retail games apply them is in [Handlers in practice](../sh2/intc.md#handlers-in-practice): Star Wars Arcade copies Sega's first sample almost word for word, Mortal Kombat II follows the revised sample, writing fixed values to TOCR instead of flipping a bit, and After Burner Complete flips the bit at the end of each handler instead of the start. All three dispatch on the level in SR and read their clear registers back.

Two of the games also guard against a CMD that never arrives, whatever the cause:

- **Star Wars Arcade's 68000 raises CMD again.** It writes a command number into `$A15120`, clears and then sets INTM, and polls the command byte up to 8,192 times for the Master to zero it. If the byte is still set, it clears and sets INTM again and goes on waiting [SWA, 68000 code at `$086B72`-`$086B9C`].
- **After Burner Complete's Master gives up on a lost one.** After 1,500,000 idle passes it clears its busy byte and its CMD request, so the 68000 is not left waiting ([Never wait forever](communication.md#never-wait-forever)) [AB32X, SH-2 code at `0x060038E6`].

Neither PicoDrive nor Ares models the flaw, so a program that ignores it works in both (MAME's interrupt code was not read for it) <span class="tag emulator">emulator</span> [PICODRIVE, pico/32x/sh2soc.c; ARES, component/processor/sh2/sh7604/interrupts.cpp].

## Reset while RV = 1

If the reset button is pressed while RV = 1, the console may not restart properly. Sega changed the hardware from development target 2.1 (September 1994) so that the Master SH-2 can reset the whole 32X, and asked every game that uses RV to do so from its VRES handler: clear VRES, check RV, and if it is set, trigger the reset and wait <span class="tag manual">manual</span> [32X-TI items 6, 16; 32X-TIA1 p.1]. A game that never changes RV needs none of this [32X-TIA1 p.1]. The sequence, and how the Master's FTOB output drives the reset, are in [Pressing reset](boot.md#pressing-reset) and [FTOB and the VRES reset](../sh2/timers.md#ftob-and-the-vres-reset).

What the retail games do:

| Game | Reads RV | Reset path |
|------|----------|------------|
| Star Wars Arcade | Word at `0x20004006`, bit 0: correct | Sets FTOB, but never sets OCRB, so the output may never change ([discrepancy 22](../appendices/discrepancies.md)) |
| Mortal Kombat II | Byte at `0x20004006`, bit 0: that is bit 8 of the register, undefined in the manual, in the byte whose bits 15 and 14 the manual describes as the FULL and EMPT flags of the frame buffer write cache. Not RV | Sega's sample, OCRB = 1 |
| After Burner Complete | Byte at `0x20004006`, bit 0, on both CPUs: also bit 8 | Sega's sample, OCRB = 1 |
| Motocross Championship | Byte at `0x20004006`, bit 0, on both CPUs: also bit 8 | Sega's sample, OCRB = 1 |
| Knuckles' Chaotix | Byte at `0x20004007`, bit 0: correct | Sega's sample, OCRB = 1; when RV is 0 it writes `M_OK` to `$A15120` and restarts the Master's program |

Sources: [SWA, SH-2 code at `0x06000584`-`0x0600058A`, `0x060005B2`; MK2, SH-2 code at `0x06000350`-`0x0600035A`, `0x0600037A`; AB32X, SH-2 code at `0x06000296`-`0x060002A0`, `0x06002266`-`0x06002274`, `0x060022B4`; MCX, cartridge-resident SH-2 code at `0x02029F12`-`0x02029F16`, `0x02029F50`-`0x02029F54`, `0x02029F38`, OCRB set at `0x02028A2E`-`0x02028A38`; CHAOTIX, SH-2 code at `0x060008A4`-`0x060008AE`, `0x06001250`-`0x06001270`]. The manual and Sega's own equates agree that RV is in the byte at `0x20004007`, and that the byte at `0x20004006` holds bits 15 and 14, which the manual describes as the FULL and EMPT flags of the frame buffer write cache (Ares reports the DREQ FIFO's there instead, [discrepancy 32](../appendices/discrepancies.md)), and undefined bits <span class="tag manual">manual</span> [32X-HWM §3.2.2 p.30; 32X-SUP2, register equates]. On a console that undefined bit 8 reads 0 even with RV = 1 [TESTPICO, t_32x_sh_defaults], so Mortal Kombat II's, After Burner Complete's and Motocross Championship's checks never see RV. A scan of the rest of the library finds the same wrong byte in many more games. Their reset handlers copy Sega's sample; whether the wrong byte came with the copy or was added by each team is not settled ([Sega's sample code in the games](../appendices/sample-code.md#the-two-defects)).

The first four do not seem to need the check. No 68000 instruction was found in Star Wars Arcade, Mortal Kombat II or After Burner Complete that sets RV: no write to `$A15107`, and no call to the vector ROM's two routines that set it [SWA; MK2; AB32X, 68000 code, searched]. Motocross Championship has no absolute reference to `$A15106` or `$A15107` and no call to the vector ROM at `$0000C0`; a write through an address register would not show in that search [MCX, cartridge, searched]. Under Sega's own rule they could leave the check out, and the wrong byte in three of them never matters. Knuckles' Chaotix is the one that needs it. It sets RV through the vector ROM at start-up ([below](#cartridges-over-16-mbit)) and again around every save RAM access ([Save RAM on the 32X](../megadrive/cartridge.md#save-ram-on-the-32x)). Its header declares save RAM but not whether the chip is SRAM or FRAM, so whether Sega's rule makes RV necessary there is unknown, though setting it is safe either way. Its handler reads RV from the right byte [CHAOTIX, 68000 code at `$0009E0`, `$03E392`, `$03E420`]. That is the lesson for a new program: if it sets RV, for VDP DMA from the cartridge or for save RAM, its VRES handler has to read RV correctly, from the word or from `0x20004007`.

One interaction to rule out: the revised interrupt handlers write fixed values to TOCR, and TOCR bit 0 is the output level the VRES handler raises to reset the board. It is harmless. The VRES handler runs at level 14, so only the NMI can interrupt it and no ordinary handler writes TOCR between the Master raising the level and the reset; before that, the fixed values leave bit 0 clear, so the output stays low until the VRES handler raises it. This follows from the interrupt levels and Sega's sample, not from a console test.

## Cartridges over 16 Mbit

Sega required every 32X game larger than 16 Mbit to run a short sequence after power-on, whether or not it uses a bank chip: read `$A130F1` once, then, with interrupts masked, call the vector ROM routine at `$0000C0` with `$A130F1` in `a1` and 0 in `d0`. The routine sets RV, writes the byte, and clears RV, and the write makes `$200000-$3FFFFF` show ROM. Sega gives two reasons: the sample cartridge misbehaves without it, and the design of the commercial cartridge needs it. A 16 Mbit game with save RAM is exempt <span class="tag manual">manual</span> [32X-TI item 8, scan p.4; VRD-NOTES, 32X BIOS dump]. See [Cartridge hardware](../megadrive/cartridge.md#on-the-32x).

Neither Mortal Kombat II (4 MB) nor Star Wars Arcade (2.5 MB) contains a reference to any address in `$A130xx`, or a call to the routine at `$0000C0` [MK2; SWA, ROM searched]. Both shipped and run, so their cartridges evidently need nothing from it; the next paragraph argues they have no switch there at all. Knuckles' Chaotix (3 MB) follows the rule exactly: early in its start-up it loads `$A130F1` into `a1`, reads it once with `tst.b`, clears `d0` and calls `$0000C0` [CHAOTIX, 68000 code at `$0009D6`-`$0009E0`]. After Burner Complete is exactly 16 Mbit and is not covered by the rule.

The headers suggest why. `$A130F1` is the register that chooses between ROM and save RAM at `$200000` ([When ROM and save RAM overlap](../megadrive/cartridge.md#when-rom-and-save-ram-overlap)). Chaotix is the only one of the three with save RAM: 512 bytes on the odd addresses of `$200001-$2003FF`, inside its own ROM, so its cartridge must have that switch. Mortal Kombat II and Star Wars Arcade declare no save RAM and name no bank register, so their cartridges have no evident use for a switch that could take ROM's place at `$200000` [MK2; SWA; CHAOTIX, headers at `$1B0`]. Writing 0 there makes sure the switch starts on ROM. The exemption fits the same reading: a 16 Mbit game's ROM ends below `$200000`, so its save RAM has nothing to share the space with. What a cartridge with the switch shows at power-on before the write is not known.

## The book's own projects

Aerobiz Ultimate sets RV for Mega Drive DMA from the cartridge, so the four rules that come with RV apply to it ([The RV bit](architecture.md#the-rv-bit)). It has not run on a 32X <span class="tag emulator">emulator</span> [AU-NOTES, PORT_ARCHITECTURE.md, RV constraints; disasm/32x/dma_stub.asm; disasm/sh2/master/main.s]:

- **68000 interrupts masked while RV = 1:** met. `ConfigVDPDMA` starts by masking them.
- **The DMA trigger runs outside the cartridge** (code running from the cartridge would be cut off when RV hides the window): met, from a stub copied to work RAM.
- **The twelve unreadable bytes:** met by construction. The DMA thunk (`MarsDmaThunk`) turns every cartridge source into an address in `$100000-$1FFFFF`, either a `$9xxxxx` window address minus its bias or a Genesis-form `$00xxxx` address plus `$100000`, and a DMA runs upward from its source and, if it crosses a 128 KB boundary, wraps to the start of its own 128 KB block, which is still at `$100000` or above ([Do not cross a boundary](../megadrive/vdp-dma.md#do-not-cross-a-boundary)). None can cover `$001070`, `$002070` or `$003070`, which lie in the boot half. Other sources, such as work RAM, take the stock path without RV. This is read from the code, not from a list of every DMA the game issues.
- **The VRES handler:** not met. PORT_ARCHITECTURE.md lists the rule, "the reset handler must check and clear RV". The Master's handler in `main.s` only clears VRES and returns, and the Slave's halts. A reset pressed during a DMA window could leave the console unable to restart. This is a gap to close in the project before it runs on a console.

The Virtua Racing Deluxe project reports that the game never sets RV ([the contention chapter](../patterns/bus.md#moving-data-without-paying-twice) has its evidence: no DMA from the cartridge to VRAM, and only 68S written to the DREQ control register), so none of these rules bind it.

## Development hardware only

Many of the bulletins' items concern Sega's development targets, not the consoles. They are worth knowing because code written for those boards survives in some sources, and because they explain odd warnings:

| Item | What it was | Source |
|------|-------------|--------|
| Target 1.x | FIFO transfers limited to fewer than 256 words each; PWM registers unreadable; no Mega-CD interface; Japanese region only | [32X-HWI (2) items 6-8, 10] |
| SDRAM size | Development targets carried 4 Mbit of SDRAM, and developers set the SH-2 up for 4 Mbit; production consoles have 2 Mbit, so that setting must be removed before release | [32X-HWI (2) item 3] |
| Interface chip 315-5780 | Version 2.0, with a PWM bug; the chip had to be exchanged | [32X-TI item 11] |
| Target 2.0A | A Z80 access to 68000 space locked the 68000. Targets 2.0B and 2.1 fix it, at the price of the write restriction above | [32X-TI item 15] |
| Target 2.1 | Added the VRES reset hardware; carries the same Z80 fix as 2.0B; joined the NMIs of the CPUs | [32X-TI item 16] |
| Development board security | The board starts from a 68000 boot ROM; a byte write of 1 to `$A14100` allows normal access to the cartridge connector | [32X-TI item 17] |
| PWM volume | Target 2.0 boards played PWM much quieter than FM; two resistors were changed, and production units already had the change | [32X-TI item 20] |
| Picture | From target 3.0, a different video encoder and filter: more vivid colours, less blur. Sega asked for final graphics checks on 3.0 or production units | [32X-TI item 21] |
| SRAM and ROM boards | Mega Drive development cartridge boards needed rewiring to work with a 32X, and EPROMs had to be 120 ns or faster | [32X-TI items 1-3, 18; 32X-HWI (3) item 3] |
| ICE | An in-circuit emulator reset while stopped at a break would not start again | [32X-TI item 4] |

## Found later

Problems that no Sega document describes, or that sources still disagree on:

- **FIFO transfers that stall.** A homebrew developer reported 68000-to-SH-2 FIFO transfers stopping at random on a console. A later report traced it to how the DMA channel was being stopped, not to the hardware. It is still open ([How it fails](fifo.md#how-it-fails); [discrepancy 29](../appendices/discrepancies.md)) [GENDEV-SVDP; GENDEV-DREQ].
- **`tas.b`.** The manual forbids it on the 32X; d32xr uses it for its locks ([Between the two SH-2s](communication.md#between-the-two-sh-2s); [discrepancy 12](../appendices/discrepancies.md)).
- **Which byte holds RV.** Three retail games read the wrong one, and a scan of the library finds it in many more ([above](#reset-while-rv--1)).
- **Interrupt mask semantics.** The manual covers an interrupt that is raised and then masked before the CPU takes it: VRES, V, H and PWM stay asserted until cleared [32X-HWM §3.2.2 p.29]. It does not say what happens to a V, H or PWM event while its mask bit is already 0. For V, notaz's console test answers part of it: a V that arrives while masked is taken on unmask within the same blank, and each SH-2 has its own V request [TESTPICO, t_32x_irq_vint]. The three emulators read for this book give three answers: PicoDrive drops all three, MAME keeps V and drops H and PWM, Ares keeps all three and delivers them on unmask <span class="tag emulator">emulator</span> [PICODRIVE, pico/32x/32x.c; MAME, src/mame/shared/mega32x.cpp; ARES, md/m32x/m32x.cpp, md/m32x/sh7604.cpp; [discrepancy 44](../appendices/discrepancies.md)]. H and PWM, and a V held past the end of the blank, are untested. CMD is in the same position: p.29 covers it only when it is raised first and masked afterwards, and the one console test of an event arriving while masked has the Master take it on unmask [TESTPICO, t_32x_irq_cmd] ([The CMD interrupt](communication.md#the-cmd-interrupt)). Clear an interrupt's source just before unmasking it, so that a stale request cannot fire at once, and do not count on a masked one being saved.
- **The power-on state of RES and REN**, and the status bits at `0x20004006` ([System registers](registers.md); discrepancies [30](../appendices/discrepancies.md) and [32](../appendices/discrepancies.md)).

## In emulators

The emulators hide most of this chapter. Upstream PicoDrive stores RV but does nothing with it, so the cartridge stays readable by the SH-2s and at its old address. Neither PicoDrive nor Ares models the interrupt flaw or the RV reset <span class="tag emulator">emulator</span> [PICODRIVE, pico/32x/sh2soc.c, memory.c; ARES, component/processor/sh2/sh7604/interrupts.cpp; VRD-NOTES, PicoDrive RV patch]. A program that passes in both can still fail on a console in most rows of the first table. The Virtua Racing Deluxe project's copy of PicoDrive adds an optional RV model for that reason ([The RV bit](architecture.md#the-rv-bit)).

## What to take away

- Apply the interrupt workaround in every handler on both CPUs, using Sega's revised sample (fixed values written to TOCR), even though no emulator will show the difference.
- Clear an interrupt's source just before unmasking it, and do not count on a masked interrupt being saved.
- If the program ever sets RV, its Master VRES handler must check RV, reading the word or the byte at `0x20004007`.
- Larger than 16 Mbit: run Sega's `$A130F1` initialisation once after power-on.
- Keep the Z80 away from 32X writes, and its bank window off the cartridge and frame buffer when it writes the PSG.
- Give every wait for the other CPU a time limit and a way back.

## Open questions

- How often does the interrupt flaw strike on a production console, and which consoles have the fixed SH-2? The service manual lists three SH-2 part numbers for production boards, 315-0922 (HD6417095F23) and 315-0922A and 315-0998 (both F28: by Hitachi's naming, the 28 MHz part), but no chip revisions [32X-SVC §7-3; SH7604 product codes].
- Do the 12 bytes listed in item 12 really read wrong on production units? The item names no development target, unlike most of its neighbours. The addresses are `$70`-`$73` plus `$1000`, `$2000` and `$3000`: the 32X's H interrupt vector, which the 68000 can write at `$000070`, repeated every 4 KB. That suggests the register's address is only partly decoded and shows through over the cartridge, but no source says so and no emulator models it.
- What a cartridge that switches save RAM or banks into `$200000-$3FFFFF` shows there at power-on, before the item 8 initialisation. Cartridges with ROM only evidently need nothing: Mortal Kombat II and Star Wars Arcade skip it and work.
- Is an H or PWM event that happens while its mask bit is 0 recorded and taken on unmask, and does a held V survive past the end of the blank ([discrepancy 44](../appendices/discrepancies.md))?

## Sources

- [32X-SUP2](../appendices/bibliography.md#32x-sup2): limitations concerning the SH2 interrupt, corrective action, precautions, register equates
- [32X-TI](../appendices/bibliography.md#32x-ti): items 1-22 (checked on the scan)
- [32X-TIA1](../appendices/bibliography.md#32x-tia1): VRES and RV corrective action, p.1
- [32X-TB27](../appendices/bibliography.md#32x-tb27): FTOA as IRL0, double handling, revised sample
- [MORITA-FAQ](../appendices/bibliography.md#morita-faq): which chip cut has the fault
- [32X-HWI](../appendices/bibliography.md#32x-hwi): (2) items 3, 6-8, 10; (3) item 3
- [32X-HWM](../appendices/bibliography.md#32x-hwm): §3.2.2 p.29
- [VRD-NOTES](../appendices/bibliography.md#vrd-notes): 32X BIOS dump (vector ROM at `$0000C0`); PicoDrive RV patch
- [SWA](../appendices/bibliography.md#swa): 68000 code at `$086B72`-`$086B9C`; SH-2 code at `0x06000584`, `0x060005B2`
- [MK2](../appendices/bibliography.md#mk2): SH-2 code at `0x06000350`, `0x0600037A`; ROM search
- [CHAOTIX](../appendices/bibliography.md#chaotix): header at `$1B0`; 68000 code at `$0009D6`-`$0009E0`, `$03E392`, `$03E420`; SH-2 code at `0x060008A4`-`0x060008AE`, `0x06001250`-`0x06001270`
- [AB32X](../appendices/bibliography.md#ab32x): SH-2 code at `0x06000296`, `0x06002266`, `0x060022B4`, `0x060038E6`
- [GENDEV-SVDP](../appendices/bibliography.md#gendev-svdp), [GENDEV-DREQ](../appendices/bibliography.md#gendev-dreq)
- [PICODRIVE](../appendices/bibliography.md#picodrive): pico/32x/32x.c, sh2soc.c
- [ARES](../appendices/bibliography.md#ares): component/processor/sh2/sh7604/interrupts.cpp; md/m32x/m32x.cpp, md/m32x/sh7604.cpp
- [MAME](../appendices/bibliography.md#mame): src/mame/shared/mega32x.cpp
- [32X-SVC](../appendices/bibliography.md#32x-svc): §7-3, SH-2 parts table
- [SH7604](../appendices/bibliography.md#sh7604): product codes
