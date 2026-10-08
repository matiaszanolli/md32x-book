# Harvested techniques: patterns/bus.md

Target: `patterns/bus.md`. 11 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from S32X-SKILL -->
### Framebuffer writes are uncached I/O: write aligned 32-bit words
- Source: S32X-SKILL, references/optimization.md:185-186, 220-221, 291-293, 359-360
- What it does and why it is clever: Every byte written to `0x24000000` is a bus transaction. Pack four 8bpp pixels per `uint32_t` and unroll. Keep tiles and the camera on 4-px boundaries so a 16-px tile row is exactly four aligned stores.
- Key numbers: A full 320×224 present takes about 0.3 ms. A map layer is about 19 K longs.
- Target chapter: patterns/bus.md
- Evidence: apex-vector-60-32x, racing-circuit-32x.

<!-- from S32X-SKILL -->
### Use DMA for large copies and overlap it with compute
- Source: S32X-SKILL, references/optimization.md:57-58
- What it does and why it is clever: Framebuffer fills and sample streaming via SH-2 DMA free the CPU.
- Key numbers: —
- Target chapter: patterns/bus.md
- Evidence: Described (d32xr).

<!-- from S32X-SKILL -->
### Immutable data stays in ROM and is read in place
- Source: S32X-SKILL, references/architecture.md:24-26; references/porting-workflow.md:168-174
- What it does and why it is clever: Decoded graphics, palettes, music and levels are read directly from the cartridge at `0x02000000`, which is cacheable and read-only. Only mutable state goes in SDRAM, which is how multi-megabyte games fit in 256 KiB of RAM.
- Key numbers: 256 KiB SDRAM versus a ~4 MiB ROM window.
- Target chapter: patterns/bus.md
- Evidence: All shipped ports.

---

<!-- from D32XR -->
### ROM-to-SDRAM texture cache: one upload per mip level per frame
- Source: D32XR, r_phase9.c:13-247, r_cache.c:84-250, r_main.c:570-596 (licence: id limited-use for r_phase9 and r_main; MIT for r_cache)
- What it does and why it is clever:
  - **Selection.** After each frame, R_UpdateCache walks the viswalls nearest-first. For each mip level it picks the first visible texture or flat not already resident, and copies only that one into a cache zone. Upload cost is spread out and the most prominent surfaces win.
  - **Swap and restore.** The texture's `data[]` pointer is swapped to the RAM copy; on eviction the ROM pointer (`userpold`) is put back, so drawing code never knows which copy it has.
  - **Back-pointer and alignment.** A pointer to the cache entry is stored in the 4 bytes before the pixel data, so "touch" is O(1) from the data pointer. The copy keeps the low 4 address bits of the ROM original.
  - **Lookup and ageing.** `R_InTexCache` classifies any pointer as ROM, RAM or cache with a range compare. Entries age by one per frame and are evicted after 3 untouched frames, or sooner if they are smaller than the request and were not touched this frame.
  - **Sizing.** At level start the zone is sized as the largest free block minus an 8 KB game margin.
  - **4bpp expansion.** 4bpp textures are expanded to 8bpp as they are cached.
- Key numbers: CACHE_FRAMES_WALLS/FLATS = 3; DEFAULT_GAME_ZONE_MARGIN 8 KB; minimum cache = one 64x64 flat plus header.
- Target chapter: patterns/bus.md
- Evidence: code only

<!-- from D32XR -->
### Virtual ROM addresses mapped through 512 KB bank windows
- Source: D32XR, marsnew.c:680-741, p_setup.c:347-365 (licence: MIT for marsnew.c; id limited-use for p_setup.c)
- What it does and why it is clever: Lump pointers beyond the directly mapped ROM are "virtual" addresses. `I_RemapPtr` turns one into a page number `(addr - 0x02000000) >> 19`, switches the current CPU's bank window to that page (cached in TLS, so it is skipped if already selected) and rebuilds the address inside the window. Level setup records which page holds SEGS (`segspage`), and the BSP, sight and sprite code re-select it on entry. That is how levels larger than the window are played straight from ROM.
- Key numbers: 512 KB pages.
- Target chapter: patterns/bus.md
- Evidence: code only

---

<!-- from VRD/AU/MARSDEV -->
### What each CPU can reach: the three shared channels
- Source: VRD-NOTES, KNOWN_ISSUES.md:244-268; analysis/COMM_REGISTERS_HARDWARE_ANALYSIS.md:247-259; AU-NOTES, lz.c:170-185
- What it does and why it is clever:
  - The SH-2 cannot see 68K Work RAM at any address; `$02400000-$03FFFFFF` is unmapped.
  - The 68K cannot see SDRAM.
  - The only shared paths are COMM (16 bytes), the DREQ FIFO (68K→SH-2 bulk), and the framebuffer under FM arbitration.
  
  VRD lost three attempts (B-003 v1-v3) to Work-RAM ring buffers before reading the manual.
- Key numbers: COMM 1 wait (SH-2) / 0 wait (68K); framebuffer 5 waits; cartridge 6-15 waits; SDRAM 2-6 waits.
- Target chapter: patterns/bus.md
- Evidence: manual, plus emulator (failed attempts)

<!-- from VRD/AU/MARSDEV -->
### The framebuffer as a shared mailbox
- Source: AU-NOTES, ROADMAP.md:1690-1712; HISTORY.md:183-189; ROADMAP.md:1990-1998
- What it does and why it is clever: With the layer blanked, the frame buffer above `$012000` (past the line table and 224 lines) is free scratch for SH-2→68K results. LZ output is written there in words and copied out by the 68K. Small UX state lives in a measured gap at `$11F00`, stored as value+2 because a byte write cannot store zero.
- Key numbers: copy-back costs about 10 68K clocks per word, under 2-3% of decompression.
- Target chapter: patterns/bus.md
- Evidence: emulator measured (PicoDrive/Ares). Caveats: the region collides with a live 32X layer, and under FS flips the `$0400_0000` aperture bank-swaps.

<!-- from VRD/AU/MARSDEV -->
### FM ownership must be an explicit protocol
- Source: AU-NOTES, KNOWN_ISSUES.md:168-174, 722-738; VRD-NOTES, analysis/RENDERING_PIPELINE.md:71-90; KNOWN_ISSUES.md:153-157
- What it does and why it is clever: Writing FM preempts the other side immediately, even mid-access. VRD toggles FM only inside V-INT. Aerobiz raises a "busy" bit so V-Blank logic leaves FM alone during LZ copies. A "deferred draw" design that flipped FM within microseconds of an RPC answer passed 113/114 on PicoDrive but crashed Ares (wild SH-2 writes). The rule became an explicit grant/acknowledge pair on both sides.
- Key numbers: see above.
- Target chapter: patterns/bus.md
- Evidence: emulator measured (PicoDrive/Ares)

<!-- from VRD/AU/MARSDEV -->
### RV versus SH-2 ROM access
- Source: VRD-NOTES, KNOWN_ISSUES.md:147-152; AU-NOTES, KNOWN_ISSUES.md:216-223; ROADMAP.md:1755-1760
- What it does and why it is clever: While RV=1 (Genesis DMA from ROM), every SH-2 cartridge access stalls. VRD profiled that it never sets RV (it feeds the DREQ FIFO manually), so SH-2 code in expansion ROM is safe. Aerobiz needs RV windows for Genesis DMA, so it keeps SH-2 code in SDRAM and calls the RV-versus-SH-2-ROM-read interaction "the next thing to measure".
- Key numbers: see above.
- Target chapter: patterns/bus.md
- Evidence: emulator measured (B-008 profiling); manual

---

<!-- from D32XR (hardware survey) -->
### d32xr hardware survey: 68000 side (src-md/)
- Main loop (crt0.s:412-482): PWM DAC feed, sound control, `bump_fm` refills the Z80 VGM buffer (:2501-2560); Z80 player uses Z80 RAM 0x1000-0x1FFF as eight 512-byte buffers (z80_vgm.s80:50); 68000 decompresses LZSS VGM into a 32 KB RAM buffer (vgm.c:15, 46, 82-199); Mega CD; polls COMM0 (master requests) and COMM4 (slave requests) (:464-482); controller hot-plug.
- Command table: COMM0 high byte selects the handler (crt0.s:498-545); done signalled by COMM0=0.
- Controllers read in the 68000 VBlank (crt0.s:2777-2832; 6-button :2837-2873) and pushed to the master by CMD interrupt + 0xA55A handshake + 0xFF00/0xFF02 with values in COMM2 (:3105-3133); master receives in `Mars_DetectInputDevices` (marshw.c:727-767).
- Parking the SH-2s: `sh2_wait` asserts CMD on both (0xA15102=3) and waits for 0xA55A in COMM0 and COMM4 (crt0.s:92-101); `sh2_cont` writes 0xFFFE and waits (:103-113); the SH-2 CMD handlers spin "in sdram" until 0xFFFE (crt0.s:598-689, 1024-1107). Used around SRAM (:557-671) and SSF mapper writes (:1591-1633). marshw.h:89-97 warns that while RV is set nothing on either CPU may read ROM, including DMA, code and interrupt handlers.
- Code in work RAM: main.c:45-48 "Main loop in ram - you need to have it in ram to avoid bus contention for the rom with the SH2s"; crt0.s:343 "Put remaining code in data section to lower bus contention for the rom". 68000 binary compiled for 0x880800 / 0xFF0000 (D/crt0.s:204).
- The 68000 toggles FM to read strings and arguments from the 32X frame buffer (crt0.s:711-726) and copies frame-buffer columns to MD VRAM or Word RAM (:1686-1760).
- SRAM 32 KB on odd bytes at 0x200001 (D/crt0.s:52-56); demos recorded to SRAM offset 0x800.

<!-- from MK2 -->
### Busy-waiting that costs a shipped game (Mortal Kombat II)
- Source: MK2, SH-2 code at `0x060010DC` (clear), `0x06005178` (Slave loop), `0x060003F4` (CMD handler)
- What it does and why it is clever (as a warning): The Master starts each 256-word auto fill and polls FEN until it ends before starting the next: about 125,000 clocks a frame spent waiting, which could overlap other work. The Slave's main loop reads `$A1512E` back to back with no delay, taking bus cycles from the Master. The Master's CMD handler busy-waits through 67 port handshakes to receive the state block.
- Key numbers: 161 fills × about 775 clocks.
- Target chapter: patterns/bus.md
- Evidence: ROM (timing from 32X-HWM)
