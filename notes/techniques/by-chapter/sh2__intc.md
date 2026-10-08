# Harvested techniques: sh2/intc.md

Target: `sh2/intc.md`. 5 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from VRD/AU/MARSDEV -->
### The interrupt erratum and its workaround (VR avoids interrupts)
- Source: VRD-NOTES, analysis/COMM_REGISTERS_HARDWARE_ANALYSIS.md:359-389; analysis/sh2-analysis/SH2_INTERRUPT_HANDLERS.md:222-300; KNOWN_ISSUES.md:282-289
- What it does and why it is clever: Early SH-2 silicon can miss or misvector external interrupts. The workaround:
  - toggle FRT TOCR bit 1 in every handler;
  - read back the clear register before RTE;
  - use only levels 14/12/10/8/6 and share odd/even vectors;
  - keep at least SR level 1.

  Virtua Racing polls everything instead.
- Key numbers: see the list above.
- Target chapter: NEW: SH-2 interrupts on the 32X
- Evidence: manual

<!-- from VRD/AU/MARSDEV -->
### Handlers must save every register they touch
- Source: AU-NOTES, disasm/sh2/master/main.s:98-150; HISTORY.md:1950-1956
- What it does and why it is clever: RTE restores only PC and SR. Handlers that clobbered r1 (which gcc uses as scratch) caused rare, timing-dependent corruption of C code, found only when the V interrupt became a clock.
- Key numbers: 5 Master handlers plus the Slave CMD handler fixed.
- Target chapter: NEW: SH-2 interrupts on the 32X
- Evidence: emulator measured (PicoDrive)

<!-- from VRD/AU/MARSDEV -->
### One IRQ entry decoding its level from SR; VRES reloads SDRAM
- Source: MARSDEV, sh_src/mars_start.s:387-470, 631-660, 859-900
- What it does and why it is clever: A single handler reads SR's I3-I0 field to identify V/H/CMD/PWM/VRES, because vectors are shared across level pairs. It clears the source and pads with 4 NOPs. The reset (VRES) path re-copies the ROM image to SDRAM using the MARS header fields before restarting.
- Key numbers: see above.
- Target chapter: NEW: SH-2 interrupts on the 32X
- Evidence: code only

---

<!-- from D32XR (hardware survey) -->
### d32xr hardware survey: SH-2 interrupt handling
- Vector tables in `.sdata`; levels 1-15 all to `pri_irq` / `sec_irq` (crt0.s:263-270, 323-330), which mask everything (SR=0xF0), write TOCR=0xE0 and dispatch by SR level through a 16-entry jump table, restoring the level in the jsr delay slot (:450-507, 895-952). On-chip peripherals routed into the same table: WDT VCR=65 priority 2 (marshw.c:303-304); DMA 1 VCR1=66 priority 4 (marsnew.c:354-355).
- FRT init TIER=0, TOCR=0xE2, OCRA=1, CKS=Fs/8, clear on OCRA match (crt0.s:350-365; slave :821-836). Each handler writes TOCR=0xE2 and reads it back, "bump ints if necessary" (e.g. :521-526). Sega's interrupt-bug document not cited by name.
- Enabled: master V + CMD (0x0A, crt0.s:401-402); slave CMD only (0x02, :851-852); slave DMA interrupt. HINT and PWM handlers are stubs with four nops "(remove nops if more than 8 cycles)" (:569-586, 695-712). Interrupt-clear registers written in each handler and at start (:337-348).
- WDT used as a profiling timer: overflow counter (:744-775), on/off 0xA53E/0xA518 (marsnew.c:1090-1096), read by `Mars_GetWDTCount` (marshw.c:235-239).
- VRES: clear VRES, SR=0xD0, reset the stack, jump to pri_reset/sec_reset (crt0.s:781-801, 1223-1243); slave posts S_OK, master waits, recopies the ROM .data image 0x22000000 to 0x26000000 cache-through, posts M_OK, both restart (:1317-1394).
- Startup: 68000 clears RV, waits for M_OK/S_OK (src-md/crt0.s:326-333), releases the master with COMM0=0 (:412-416); master clears COMM4 to release the slave and sets FM (crt0.s:384-402).


<!-- from AB32X -->
### Telling CMD from other interrupts with one test (After Burner Complete)
- Source: AB32X, SH-2 code at `0x060022EC`
- What it does and why it is clever: With one entry for all levels, the handler tests SR with `tst #$60`: CMD (level 8) is the only enabled level with bits 5 and 6 clear. Commands then dispatch through a `braf` table of 16-bit offsets.
- Target chapter: sh2/intc
- Evidence: ROM
