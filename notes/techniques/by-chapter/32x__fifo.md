# Harvested techniques: 32x/fifo.md

Target: `32x/fifo.md`. 3 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from VRD/AU/MARSDEV -->
### Bulk 68K→SH-2 transfer through the DREQ FIFO
- Source: VRD-NOTES, disasm/modules/68k/game/render/mars_dma_xfer_vdp_fill.asm:17-40; analysis/FRAME_RATE_ARCHITECTURE.md:180-198; analysis/sh2-analysis/SH2_COMMAND_HANDLER_REFERENCE.md:204-210; VR60_ROADMAP.md lessons (2026-03-17)
- What it does and why it is clever: The 68K sets DREQ_LEN=`$500` and `68S` mode, posts a command in COMM0, waits for the SH-2's DMAC to arm (COMM1 bit 1), then streams `$FF6000` into the FIFO with 10 unrolled block calls. The DMAC drains it to SDRAM and the 68K cannot choose where. One transfer per game tick carries camera, viewports and all descriptors.
- Key numbers: 1,280 words = 2,560 B per tick, 128 words per block call.
- Target chapter: 32x/fifo.md
- Evidence: code only

<!-- from VRD/AU/MARSDEV -->
### Zero-COMM DREQ transaction gated by two CMD interrupts
- Source: VRD-NOTES, analysis/evidence/vr60-q020-mode1-cmdint-gate/README.md:25-75; VR60_STATUS.md:186-233
- What it does and why it is clever:
  1. Before the setup edge the 68K publishes `68S`, LEN and the encoded destination, then raises CMD.
  2. The Master ISR arms DMAC0 (SAR/DAR/TCR/CHCR/DMAOR) only if the setup and completion counts match and the interrupted PC is at a known-idle boundary.
  3. The 68K writes groups of four words, checking FIFO FULL before each, waits for LEN=0 and `68S` auto-clear, then raises a second CMD.
  4. The ISR checks DAR, TCR=0 and TE, acknowledges TE (read 1, write 0) and clears CMD.
  
  Every ISR toggles FRT TOCR per the interrupt erratum.
- Key numbers: 64 B in 8 groups (mode 1); 3,840 B in 480 groups (mode 2, `$FF9100` → `$06010000`).
- Target chapter: 32x/fifo.md
- Evidence: emulator measured (PicoDrive, isolated validation stage; explicitly not hardware or authority proof)

---

<!-- from D32XR (hardware survey) -->
### d32xr hardware survey: Data streaming and banking
- WAD in cached ROM at 0x02000000 + WADBASE*1024 (wadbase.s:7; Makefile:31); lumps used in place via `I_RemapPtr` (w_wad.c:556-636); compressed lumps LZSS-decoded into frame-buffer scratch (:621-631). Textures copied on demand into an SDRAM zone cache with a 3-frame lifetime (r_phase9.c:13-247; r_cache.c:173-240; r_local.h:483-484).
- SSF banking: header "SEGA SSF", ROM end 0x4FFFFF (crt0.s:30-49; mars-ssf.ld:37). Master owns bank 6 (COMM0 cmd 0x16), slave bank 7 (via COMM4; 68000 replies 0x1000) (marsnew.c:460-466; marshw.c:705-720; 68000 side crt0.s:548-552, 1591-1633). `I_RemapPtr`: page = (p-0x02000000)>>19; new address = (p&0x7FFFF) + 512K*bank + 0x02000000, above 0x02300000 when ROM > 4 MB (marsnew.c:471, 723-741). Cache purged after switching (:711). The level's segs/nodes page kept resident (p_setup.c:962-979; reselected per frame r_main.c:718).
- 68000 to SH-2 FIFO / DREQ: 68000 side `dma_to_32x` (crt0.s:3140-3245): master CMD with 0xFF10, clear 68S, source/destination/length (rounded to 4 words, "FIFO operates on units of four words"), set 68S, write words to 0xA15112 polling FIFO full (bit 7 of 0xA15107), finish with 0xFF20. SH-2 side `Mars_HandleBeginDMARequest` (marshw.c:915-956): waits for 68S, DMA channel 0 SAR0=0x20004012, DAR0=0x20000000|dest, TCR0=word count, word transfers, DREQ edge; destination callback can refuse; `Mars_HandleEndDMARequest` polls TE (:958-973).
- RoQ: 68000 streams from CD into Word RAM and DMAs chunks (src-md/scd_roq.c:42-229); flags in COMM8 (marshw.h:163-166; marsroq.c:503-540); SH-2 ring buffers video 0xE000 / sound 0x5000 bytes (marsroq.c:36-37); decodes straight into a direct-colour frame buffer; previous frame copied to SDRAM by master DMA channel 1 in 16-byte auto-request units (marsroq.c:628-670).

