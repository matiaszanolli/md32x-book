# Harvested techniques: howto/large-cartridges.md

Target: `howto/large-cartridges.md`. 6 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from VRD/AU/MARSDEV -->
### Rebasing a 1 MB Genesis game to $900000 via bank 1
- Source: AU-NOTES, PORT_ARCHITECTURE.md:38-75, 205-220
- What it does and why it is clever: With ADEN=1 the 68K sees a 512 KB fixed window at `$880000` plus one 1 MB bank at `$900000` (selected at `$A15104`). Putting the whole game at cartridge `$100000` and selecting bank 1 makes it contiguous and never bank-switched, so rebasing is a single constant. Glue code and the SH-2 image live in the fixed window so they stay mapped regardless of bank.
- Key numbers: 2 MB cartridge (later 4 MB); game half byte-for-byte the original 1 MB.
- Target chapter: howto/large-cartridges.md
- Evidence: emulator measured (PicoDrive/Ares full playthrough)

<!-- from VRD/AU/MARSDEV -->
### Finding every ROM literal: safe, review and numeric classes
- Source: AU-NOTES, PORT_ARCHITECTURE.md:222-273; ROADMAP.md:246-353; tools/scan_rom_refs.py:1-80; KNOWN_ISSUES.md:473-509
- What it does and why it is clever:
  - **Safe:** operands that are addresses by construction (`lea`/`pea`/`movea #`, `(abs).l`, branch targets) are rewritten as `ROM_BASE+$x`.
  - **Numeric by encoding:** byte and word immediates cannot hold `$9xxxxx`, so they are excluded mechanically.
  - **Review:** ambiguous immediates are settled by tracing whether the value ever reaches an address register.
  - **Blind spots found:** hand-encoded `dc.w $4EB9` JSRs, multi-value `dc.l`, PC-relative `$x(pc)`, `dbne`, upper-case mnemonics.
- Key numbers: initial estimate 2,886 sites, true inventory 3,872; 3,001 rebased; 971 hand-encoded JSRs; 899 review sites → 93 distinct pairs, 0 addresses; 336 excluded by encoding.
- Target chapter: howto/large-cartridges.md
- Evidence: emulator measured (tool counts; boot tests)

<!-- from VRD/AU/MARSDEV -->
### Auditing data mistaken for pointers: access width and reachability
- Source: AU-NOTES, HISTORY.md:1232-1311, 1627-1690
- What it does and why it is clever: Shape heuristics turned palettes and index tables into "pointers" (signature: an odd byte gaining a high nibble of 9). The fix tests what the code does instead: find every instruction referencing a table and follow the register to its first read. A `move.l` read means pointers, a `move.w` read means data. A `#` distinguishes table-address loads from entry loads.
- Key numbers: 41 wrong rewrites restored; 1,817 audited with 0 defects; 551 references, all longword reads.
- Target chapter: howto/large-cartridges.md
- Evidence: emulator measured (tool plus pixel/RAM diffs)

<!-- from VRD/AU/MARSDEV -->
### Low-window reads die when RV=0
- Source: AU-NOTES, HISTORY.md:1380-1395; KNOWN_ISSUES.md:457-471
- What it does and why it is clever: The game read its own header at absolute `$0001F0` for a region check. Under the adapter nothing is mapped there unless RV=1, so Ares showed the region lockout. The fix reads the game half's own copy, PC-relative. The scanner ignores values below `$200`, so this class needs its own search.
- Key numbers: two sites.
- Target chapter: howto/large-cartridges.md
- Evidence: emulator measured (Ares; PicoDrive after core fix)

<!-- from VRD/AU/MARSDEV -->
### 4 MB cartridge, expansion space and fail-soft data relocation
- Source: VRD-NOTES, docs/ROM_SIZE_CLARIFICATION.md:1-80; KNOWN_ISSUES.md:235-243; AU-NOTES, HISTORY.md:635-700
- What it does and why it is clever:
  - **VRD:** dumps are 3 MB because trailing `$FF` was trimmed. Restoring 4 MB gives 1 MB at `$300000` for SH-2 code; 68K access via banking was still being probed.
  - **Aerobiz:** puts new event tables in the fixed window (cartridge `$030000` = `$8B0000`), so they need no bank switching. Shared modules gain same-size `ifne ROM_BASE` variants; any reader not repointed still sees the original tables, so a partial migration degrades instead of crashing.
- Key numbers: 4,194,304-byte cartridge; 293 changed bytes confined to 11 modules.
- Target chapter: howto/large-cartridges.md
- Evidence: emulator measured (Aerobiz); code only (VRD bank probe unresolved)

---

<!-- from D32XR (hardware survey) -->
### d32xr hardware survey: Data streaming and banking
- WAD in cached ROM at 0x02000000 + WADBASE*1024 (wadbase.s:7; Makefile:31); lumps used in place via `I_RemapPtr` (w_wad.c:556-636); compressed lumps LZSS-decoded into frame-buffer scratch (:621-631). Textures copied on demand into an SDRAM zone cache with a 3-frame lifetime (r_phase9.c:13-247; r_cache.c:173-240; r_local.h:483-484).
- SSF banking: header "SEGA SSF", ROM end 0x4FFFFF (crt0.s:30-49; mars-ssf.ld:37). Master owns bank 6 (COMM0 cmd 0x16), slave bank 7 (via COMM4; 68000 replies 0x1000) (marsnew.c:460-466; marshw.c:705-720; 68000 side crt0.s:548-552, 1591-1633). `I_RemapPtr`: page = (p-0x02000000)>>19; new address = (p&0x7FFFF) + 512K*bank + 0x02000000, above 0x02300000 when ROM > 4 MB (marsnew.c:471, 723-741). Cache purged after switching (:711). The level's segs/nodes page kept resident (p_setup.c:962-979; reselected per frame r_main.c:718).
- 68000 to SH-2 FIFO / DREQ: 68000 side `dma_to_32x` (crt0.s:3140-3245): master CMD with 0xFF10, clear 68S, source/destination/length (rounded to 4 words, "FIFO operates on units of four words"), set 68S, write words to 0xA15112 polling FIFO full (bit 7 of 0xA15107), finish with 0xFF20. SH-2 side `Mars_HandleBeginDMARequest` (marshw.c:915-956): waits for 68S, DMA channel 0 SAR0=0x20004012, DAR0=0x20000000|dest, TCR0=word count, word transfers, DREQ edge; destination callback can refuse; `Mars_HandleEndDMARequest` polls TE (:958-973).
- RoQ: 68000 streams from CD into Word RAM and DMAs chunks (src-md/scd_roq.c:42-229); flags in COMM8 (marshw.h:163-166; marsroq.c:503-540); SH-2 ring buffers video 0xE000 / sound 0x5000 bytes (marsroq.c:36-37); decodes straight into a direct-colour frame buffer; previous frame copied to SDRAM by master DMA channel 1 in 16-byte auto-request units (marsroq.c:628-670).

