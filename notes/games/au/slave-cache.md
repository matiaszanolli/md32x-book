# Aerobiz Ultimate: the Slave cache result, rerun with the boot ROMs (8 October 2026)

Working notes, not part of the book. Cited from `src/patterns/cache.md` ("A conclusion drawn without the boot ROM").

**Claim tested.** AU's U-093 (HISTORY, 2026-09-12; commit `11f44e3`) measured zero cached Slave accesses until `slave_start` wrote CCR, and read it as the Slave never enabling its cache. HISTORY 2026-09-15 and HARDWARE_TESTS item 7 later doubted it: the boot ROMs write `$11` to CCR on both CPUs.

**Why PicoDrive never had the boot ROMs.** The 32X BIOS loader in `platform/common/emu.c` is inside `#if 0`, in the VRD copy and upstream `26ecb2b` alike, and the libretro core has no loader of its own. With no BIOS, `p32x_reset_sh2s()` in `pico/32x/32x.c` copies the SH-2 program and sets GBR/VBR itself, and never writes CCR. The timing model (`vrd_timing.c`) starts with CCR = 0 and changes it only on a CCR write, so a program that does not enable its cache runs uncached under it.

**Method.**
- Core: `notes/games/tools/build_bios_core.sh WORKDIR` (interpreter build; loads the boot ROMs when `PD_32X_BIOS_DIR` is set; same core for both runs).
- Boot ROMs: `../32x-playground/32X BIOS/` = `../aerobiz-ultimate/32X_BIOS/` (MD5 G `6a5433f6…`, M `f88354ec…`, S `7f041b6a…`).
- ROM: AU at `0c9d430` (`11f44e3^`, the commit before the fix; `git archive 0c9d430`, then link the untracked `Aerobiz Supersonic (USA).gen`, `reference/` and `tools/vasmm68k_mot`), `make 32x-zoomtest`. Its `slave_start` has no CCR write.
- Run: `VRD_SH2_TIMING=1 ./frontend build/aerobiz-ultimate-zoomtest.32x 500`, once without and once with `PD_32X_BIOS_DIR`.

**Results (Slave).**

| | Accesses | Cached | Misses | Wait cycles |
|---|---|---|---|---|
| No boot ROMs | 12,822,653 | 0 | — | 139,303,827 |
| Boot ROMs | 147,809,178 | 147,794,218 (100.0% hit) | 9 | 30,029 |

The first row matches U-093's 12.8M accesses, 0 cached, 139.4M wait cycles. Master, for comparison: 99.5% hit in both runs. Control: Mortal Kombat II (never writes CCR), 600 frames: 0 cached on both CPUs without the boot ROMs, 100.0% hit with them.

**Caveat.** The timing model is bookkeeping only (tags, valid bits, LRU age; no data, no single-line purges, no contention between CPUs), so these are emulator figures.
