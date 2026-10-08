# Harvested techniques: 32x/bugs.md

Target: `32x/bugs.md`. 1 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from D32XR (hardware survey) -->
### d32xr hardware survey: SH-2 interrupt handling
- Vector tables in `.sdata`; levels 1-15 all to `pri_irq` / `sec_irq` (crt0.s:263-270, 323-330), which mask everything (SR=0xF0), write TOCR=0xE0 and dispatch by SR level through a 16-entry jump table, restoring the level in the jsr delay slot (:450-507, 895-952). On-chip peripherals routed into the same table: WDT VCR=65 priority 2 (marshw.c:303-304); DMA 1 VCR1=66 priority 4 (marsnew.c:354-355).
- FRT init TIER=0, TOCR=0xE2, OCRA=1, CKS=Fs/8, clear on OCRA match (crt0.s:350-365; slave :821-836). Each handler writes TOCR=0xE2 and reads it back, "bump ints if necessary" (e.g. :521-526). Sega's interrupt-bug document not cited by name.
- Enabled: master V + CMD (0x0A, crt0.s:401-402); slave CMD only (0x02, :851-852); slave DMA interrupt. HINT and PWM handlers are stubs with four nops "(remove nops if more than 8 cycles)" (:569-586, 695-712). Interrupt-clear registers written in each handler and at start (:337-348).
- WDT used as a profiling timer: overflow counter (:744-775), on/off 0xA53E/0xA518 (marsnew.c:1090-1096), read by `Mars_GetWDTCount` (marshw.c:235-239).
- VRES: clear VRES, SR=0xD0, reset the stack, jump to pri_reset/sec_reset (crt0.s:781-801, 1223-1243); slave posts S_OK, master waits, recopies the ROM .data image 0x22000000 to 0x26000000 cache-through, posts M_OK, both restart (:1317-1394).
- Startup: 68000 clears RV, waits for M_OK/S_OK (src-md/crt0.s:326-333), releases the master with COMM0=0 (:412-416); master clears COMM4 to release the slave and sets FM (crt0.s:384-402).

