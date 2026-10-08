# Harvested techniques: howto/32x-hello.md

Target: `howto/32x-hello.md`. 3 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from VRD/AU/MARSDEV -->
### ROM header, 68K jump table and the MARS user header
- Source: MARSDEV, sh_src/mars_start.s:1-100; sh_src/mars.ld:1-98
- What it does and why it is clever:
  - **68K vectors:** all point at `$3F0`.
  - **Exception routing:** after ADEN the cartridge lives at `$880000`, so exceptions go through a jump table at `$200` (`jmp`/`jsr $8808xx`).
  - **MARS header:** gives source, destination and size for the boot-ROM copy, Master/Slave entry points (`$06000240`/`$06000244`) and VBRs (`$06000000`/`$06000120`).
  - **Linking:** SH-2 `.text` is linked to run from ROM at `$02000000`; only `.data` is copied to SDRAM.
- Key numbers: Master stack `$0603F000`, Slave stack `$06040000`.
- Target chapter: NEW: Booting a 32X program
- Evidence: code only

<!-- from VRD/AU/MARSDEV -->
### 68K start-up tricks
- Source: MARSDEV, md_src/md_start.s:105-178
- What it does and why it is clever: `suba.l a1,a1` then `move.l d0,-(a1)` 16,384 times clears Work RAM by predecrement wrap from address 0. a1 then lands at the RAM base for copying `.data`. The 1bpp font becomes 4bpp colour 1 by `AND #$11111111`. The 68K clears RV, waits for M_OK/S_OK, sets FM and releases the Master. Interrupts were left disabled ("crash… why?").
- Key numbers: 64 KB cleared.
- Target chapter: NEW: Booting a 32X program
- Evidence: code only

<!-- from VRD/AU/MARSDEV -->
### SH-2 start-up: interrupt clears, cache, BSS, slave release
- Source: MARSDEV, sh_src/mars_start.s:226-365; AU-NOTES, disasm/sh2/master/main.s:30-100; disasm/sh2/sh2.lds:1-55
- What it does and why it is clever:
  - **marsdev:** walks the five interrupt-clear registers down from `$2000401E` with predecrement, writing each twice; runs init with the cache purged and off, then sets `CCR=$11` before `main`; the Master clears the Slave status to release it.
  - **Per-CPU registers:** the interrupt-enable byte is per-CPU at the same address.
  - **Aerobiz:** zeroes `.bss` itself because `objcopy -O binary` drops NOBITS sections.
  - **Mask rule:** keeps at least one interrupt mask set at all times (manual 5.3).
- Key numbers: SR mask level 6.
- Target chapter: NEW: Booting a 32X program
- Evidence: code only

---

