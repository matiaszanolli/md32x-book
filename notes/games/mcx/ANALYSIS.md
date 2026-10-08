# Motocross Championship (32X): analysis notes

Working notes, not part of the book. ROM `../32x-playground/Motocross Championship (32X) (JU) [!].32x`, 2 MB (16 Mbit), MD5 `2c4a9349…`; header checksum `$BDC5` matches the `$200-$1FFFFF` sum. European dump `…(E) [!].32x`, MD5 `6bc36580…`, checksum `$331C` matches, same serial `GM MK-84600-00`; the two differ in the region byte and checksum. Verify with `python3 ../tools/header32x.py ROM`.

## The surprise: both SH-2s run from cartridge ROM

The user header's copy block is a dummy: source `$06000000` (outside the 2 MB ROM), size 4 bytes. Both entry points are in the cached cartridge window, and both vector tables live in ROM too:

- Master entry `$02028A00`, VBR re-pointed to `$02028000` (ROM), stack `$06035220`
- Slave entry `$02028800`, VBR re-pointed to `$02028408` (ROM), stack `$06033220`
- Header VBRs (`$06000000`/`$06000400`) are never used; each CPU re-points VBR as its first real act

Every other reference game copies its SH-2 program into SDRAM. MCX executes in place, so every cold code path pays ROM access, competing with the 68000; only the 4 KB cache makes it tolerable. Worth a paragraph in `src/patterns/cache.md` or `src/32x/timing.md` once the frame-time profile exists.

## The Slave's entry is 0x3E bytes early, and survives

`$02028800` points into filler: four `$02029FFC` longwords, then a duplicate of the Master's FRT-init block. Executed as code, the filler runs `stc sr,r2` / `mov.w @(508,pc),r15` four times (r15 = junk), then `mov.b r0,@(n,r1)` writes through **undefined r1**. This works because:

1. The Slave boot ROM zeroes r0-r14 before jumping to the game entry (`32X_S_BIOS.BIN` `$140-$160`: fifteen `mov #0,rn`), so r1 = 0 and the stray writes are byte writes to cartridge ROM `$00000000-$00000007`, which ignores them.
2. r15 is reloaded by the real init.

The real Slave init begins at `$0202883E` (`mov #-16,r0; ldc r0,sr` …), a byte-for-byte twin of the Master's `$02028A3E` block with different pool literals. The Master entry `$02028A00` is clean and runs the same shape twice (init block, then the twin block back to back — the build evidently laid two copies of the startup object).

## Boot handshakes (verified)

Master `$02028A00`: SR `$F0`; VBR `$02028000`; GBR `$20004000`; FRT set-up at `0xFFFFFE10-17`: TIER 0, TOCR `$E2`, FRC `$0100`, FTCSR bit 0 (clear counter), TCR 0, TOCR `$F2` again — Sega's timer-workaround values (cf. discrepancy 20). Then the twin block: **HEN = 1** (byte `$80` to `0x20004000`), wait `COMM0 == 5` (from the 68000), zero SDRAM `$06000000-$06031220` (word loop, ~202 KB), `COMM0 = 0`, byte `$08` to `0x20004001` (**bit 11 — not in the book's mask-bit table**; harmless unknown), SR = 0 (all interrupts unmasked), `COMM8 = $0105`, `COMM9 = $05B0`, `jmp $021A4FD0` — main program, also in ROM.

Slave `$0202883E`: same shape; wait `COMM2 == 5`, clear it, byte `$08` to `0x20004001`, SR = 0, `COMM3 = 0`, then **`bra` to itself at `$02028868` forever**. The Slave is purely interrupt-driven.

Who writes the 5s (68000 or Master) is the next thing to pin down.

## Interrupt design: Sega's one-dispatcher workaround, by the book

All eight external vectors (64-71) point at one routine per CPU — Master `$02029DEC`, Slave `$02029E7C` — exactly what 32X-SUP2 recommends. The dispatcher pushes r0-r2 (+PR), `stc sr,r1`, masks `$F0`, writes TOCR = 0 (`0xFFFFFE17`), and jumps through `table[(SR>>2)&60]` (index = level × 4).

Master's 16-entry table at `$02029E2C`:

| SR level | Handler | 32X source |
|----------|---------|------------|
| 0-5 | `$02029E6C` (`rts`) | none |
| 6-11 | `$02029FCC` | PWM (6), CMD (8), H (10) share one handler |
| 12-13 | `$02029F7C` | V |
| 14-15 | `$02029EFC` | VRES |

Vector-table oddity: entries 7 and 8 point at `$20100400`/`$20100420` — the cache-through alias of ROM `$100400`, which disassembles as **data** (bitmap-like runs). SH7604 Table 4.3 marks vectors 5, 7, 8 and 13-31 "reserved by system", TIER = 0 disables FRT interrupts, and no VCR writes have been seen yet — so they appear to be never-used, but do not assume it until the VCR registers are searched.

- **V handler `$02029F7C`**: saves r0-r2 + GBR, GBR `$20004000`, clears V with the word write to `@(22,gbr)` (`0x20004016`), TOCR = 2 written and read back, increments a frame-counter longword, continues (rest not yet read).
- **VRES handler `$02029EFC`**: calls `$0202C140(0,0)` and `$0202C2F8(0)` first; clears VRES via `@(20,gbr)` (`0x20004014`); reads the DREQ/RV byte `@(6,gbr)` and tests bit 0 — **if RV = 1 it sets TOCR bit 0** (OLVLB/FTOB, the reset-pulse reading of discrepancy 22 — a third shipped variant: no OCRB = 1 here, like Star Wars Arcade). Before returning it zeroes DMAOR (`0xFFFFFFB0`) and `0xFFFFFF8C` (CHCR0) and stores a longword fetched from pool `$0202A038` — the pool at `$0202A04C` holds **`$000044E0`**, the exact CHCR0 TE-clear value later rediscovered by d32xr's maintainer (discrepancy 29). Confirm which of the two pools feeds which store.

## Runtime: headless PicoDrive, 3000-frame attract run

`tools/libretro-profiling` frontend, `VRD_INPUT_SCRIPT` (Start presses then B presses), `VRD_WATCH` on the mask register, `VRD_PROFILE_PC` on both SH-2s, `VRD_VIDEO_DUMP_DIR` RGB565 frames. The input path reaches: title screen (~frame 650) → options menu MODE/PLAYERS/LEVEL/MUSIC/CREDITS (~frame 1250) → race-start countdown (~frame 2150).

**Everything the player sees is the 32X bitmap layer.** All three checkpoints were identified inside the framebuffer dumps alone: the title lettering, the full options menu (14k+ distinct colours — the purple crosshatch background is not tile art), and the race view — seven riders, grandstand crowd, countdown numeral and the TIME/LAPS/SPEED HUD. The Mega Drive tile layers carry nothing of the presentation; the 68000 is effectively the frame master and I/O pump, not a renderer. Dumped frames alternate between full content and all-black, i.e. the layer is blank during part of the frame while the upload runs (cause not pinned down; see open questions).

**The frame pipeline, from the Master's profile:** Master spends ~24% of 380 sampled frames spinning in its wait loop (`$021E745E`/`$021E7462`), ~6.6% in the upload loop at `$020295BE`, which copies `0xFDC0` words from SDRAM `$06003EF0` to the cache-through frame buffer `$04000200`-alias `$24000200`, gated by a flag at `$06024C04`. So the render goes **into an SDRAM staging buffer first, then bulk-uploads to the real buffer** — a double-buffer that keeps the visible buffer stable while drawing. The 68K sits 54% in a wait loop at `$008A62AA`: it paces frames and owns the communication ports.

**Interrupt mask at runtime:** watch shows the low byte at `$82` — HEN (bit 7) + CMD (bit 1) — with V (bit 3) **never** enabled; at frame ~111 the high byte gains `$08` (bit 11 again, matching the boot-time mystery write). MCX never takes a V interrupt on the SH-2s: the 68000 gets the MD V-int and signals the SH-2s through a COMM register (CMD interrupt). H is presumably raster-linked.

**Slave:** parked in its `$02028868` spin 99.99% of the run. But the dispatcher fired 269 times into the level-0-5 stub (`rts`) — dispatches that should not happen if the mask stayed `$82`/Slave-unmasked. Either something re-masks briefly (the bit-11 writer?) or PicoDrive delivers an interrupt the hardware would not. Unresolved.

**Master takes zero interrupts in 380 frames** despite HEN+CMD enabled — the wait loops above may be doing the pacing instead of interrupts, or the emulator under-delivers (PicoDrive warns `msh2 unhandled sysreg r16 [02] @020295c6` on every upload-iteration store into the cache-through FB alias; video still renders correctly, so the warning looks cosmetic).

## The 68000 side (verified)

The whole 68K boot-to-frame path is mapped. MCX follows Sega's boot sample [per the book's boot chapter] to the letter, with one twist: the "go" value is 5, not 0.

**Boot (`$008806E8-$0088075C`):** COMM0 = COMM2 = 0, then `3` to `$A15101` (ADEN|RES — releases the SH-2s); SSP from cartridge offset 0 through `$00880000`; poll FM clear (68K keeps the VDP); zero the interrupt control, bank, DREQ, COMM8/9 and VDP mode/shift registers; then **blank both frame buffers with the VDP FILL function** (`$00880654`: 256 iterations × 0xFF-word fills with an alternating data bit, FS toggled between them) and clear the 256-word palette at `$A15200` — with the palette zeroed the alternating pattern is invisible, so both buffers start genuinely black. Then 32 KB of work RAM cleared. A `"MARS"` magic check (`CMPI.L #$4D415253`, `$0088040C`) gates the whole thing.

**Handshake (`$00880D46-$00880DA8`), the chain the SH-2 notes hunted:**

1. Wait `COMM0 == "M_OK"` and `COMM2 == "S_OK"` (the SH-2 boot ROMs' signals).
2. Write an `"INIT"` marker to `$FF0000`, run the 68K's own init (`$008A5934` — this resolves the old "$021A5940 caller?" note: different CPU, this is the 68K init called mid-handshake).
3. `COMM0 = 5`, poll until the Master clears it; `COMM2 = 5`, poll until the Slave clears it — **the 5-writers found**: `MOVEQ #5` + `MOVE.L` at `$00880D7A`/`$00880D8E`. Each side's poll-release is the other side's clear: a command/ack ping-pong per word.
4. Verify the `INIT` marker survived (RAM sanity across the SH-2s' SDRAM zeroing), re-write it, jump to main at `$008A3CE4`.

**Frame loop (`$008A62DE+`):** reads COMM0 through the wait helper at `$008A62A8` (the 54% hotspot from the profile — a poll loop), dispatches a jump table on values 0-4, pulling command words from the RAM buffer at `$FF009E/$FF00A0`. The three absolute COMM references (COMM0/1/2 at `$0088062E4-$F2`) exist only here.

**Sound (corrected 2026-10-05):** the 68000 feeds PWM itself, from its **H interrupt** (jump-table entry 27 at `$2A2` → `$0088081A`; entry 29, the V interrupt, is `$00880916`). Set-up at `$0E18`-`$0E5E`: left and right pulse width 1, cycle `$5B9` (1,465 → 15,718 Hz, about the line rate), control `$0105`, all written from the 68000 at `$A15130`-`$A15136`; VDP register 0 = `$14` (H interrupt on), register 10 = `$01` (every second line, 112 per frame). Each interrupt: voice A (looping: position `$FF002C` += step `$FF0030`, wrapped at `$FF0028`, sample byte at `pos >> 7` from `$FF0024`, × volume `$FF0036` >> 4, 0 bumped to 1) is written to the **right** register `$A15136` after polling FULL; voice B (same layout at `$FF0038`-`$FF004A`) to the **left** register `$A15134`. If `$FF0034` bit 15 is set, voice A is replaced by a one-shot byte stream (`$FF004C` pointer, `$FF0050` count, `$FF0054` volume) to the right register; its zero guard bumps the wrong register (`addq.w #1,d1` at `$0008E2`, the value written is `d0`), so a scaled 0 is written as pulse width 0, which per the manual is the maximum. Profile (PicoDrive, 2,000 frames from power-on, attract mode): 211,009 entries (about 105 per frame), 37,228 68000 clocks per frame in `$0088081A`-`$0088090E`, about 29% of the 68000. Music: a 6,278-byte Z80 program copied from cartridge `$23D24`-`$255AA` (`$025640`); the 68000 talks to it through Z80 `$1B20` (request) and `$1B21` (busy). The earlier "COMM8-11" reading was wrong: `$A15130`-`$A15136` are the PWM registers.

**VDP ownership:** boot holds FM = 0 and fills both buffers black; the FM-flip sites at `$0088094A`/`$008809AA`/`$00880D4C` are boot/error paths (ADEN tests, the `SQER`/`SDER` family). The game-time FM ownership stays with the SH-2s (they set it), matching the runtime watch where the mask register's bit 15 never changes.

## Race-mode profile and the JU/E diff (second headless run)

**The Slave stays parked even during actual racing.** Input script (Start at frame 600, B presses through the options menu from 1050, throttle+steering from 2200) reaches a first-person race — verified in the dumped frames (handlebars view, dirt track, consistent scene across frames 2100-2900). Profile over 3,000 frames (attract + menu + race): the Slave spends 886M of its 886M cycles in the `$02028868` park loop — **MCX is effectively a single-SH-2 game even in gameplay**; the only other Slave activity is 98K cycles at `$02029FE6` (~33/frame, negligible). The Master carries everything: ~266k useful cycles/frame on average (≈70% of one SH-2's 383k 60 Hz budget), hottest in the frame loop at `$021A4F24+` and the staging→frame-buffer upload loop at `$020295BE` — the same two loops the attract profile found, now confirmed under race load. The 68K averages ~128k cycles/frame, still dominated by the COMM wait loop (`$008A62AA`, 216M cycles) with the V-int PCM feeder (`$0088085C-$008808C6`) second — the sound path measured.

**JU vs E is a rebuild, not a region patch.** Header: release month `NOV`→`DEC`, checksum `$BDC5`→`$331C`, region `JU`→`E `. Code: a 602-byte boot-block rewrite at `$0DC4-$101D` (the E build even starts differently — `LEA $A15100,A5` where JU has `JMP $008A3CE4`), plus single-byte changes at `$28F`, `$925`, `$D73` (likely 50 Hz timing constants). Data: ~145 KB of graphics/sound tables shifted by 12 bytes across most of the ROM — a relaid-out December build.

## In the book (candidate homes, not yet written)

`src/sh2/intc.md` (a second retail one-dispatcher design; level 6-11 sharing), `src/sh2/timers.md` (TOCR 0 / 2 / bit-0 sequencing across dispatcher, V and VRES), `src/32x/bugs.md` (VRES: TOCR bit 0 + `$44E0` in shipped 1994 code), `src/32x/boot.md` (boot ROM leaves r0-r14 zeroed on the Slave — the reason a mis-pointed entry survives), `src/patterns/cache.md` (running from ROM windows), `src/patterns/frame-buffer.md` / `src/32x/frame-buffer.md` (SDRAM staging buffer + gated bulk upload; whole presentation incl. HUD on the bitmap layer; no SH-2 V interrupt — 68K-driven frame pacing).

## Next steps

- Slave dispatch table at `$0202E7C` region; the shared PWM/CMD/H handler `$02029FCC`; what `$02029FE6` (the Slave's only non-park activity, ~33 cycles/frame) does
- Who writes the bit-11 mask byte at runtime (frame ~111), and whether the 269 stub dispatches follow it
- Search both SH-2 programs for VCR writes (would give meaning to vectors 7/8) and for `0x20004100`/`0x0400xxxx` (VDP register and frame-buffer use)
- Cause of the alternating blank frames during play (boot fills both buffers black; during play a stale buffer may show when rendering lags a frame)
- The E build's boot-block rewrite at `$0DC4-$101D` (what the December changes actually do)

## Scratch files here

`mcx_romwindow.bin/.txt` (ROM `$28000-$38000` as `0x02028000+`), `mcx_100400.bin/.txt` (`0x020100000+`), `master_main.bin` (ROM `$1A4F80+`), `slave_init.bin`, `disp.bin` (`0x02029DEC+`), `h2/h3.bin` (VRES and V handlers). Run artefacts in `/tmp`: `mcx_watch.csv` (mask register), `mcx_pc.csv`/`mcx_idle.csv`/`mcx_play.csv` (profiles), `mcx_vid/` (RGB565 frames; render with `Image.frombytes('RGB',(320,224),raw,'raw','BGR;16')`), `mcx_sheet.png`, `f650/f1250/f2150.png`. Regenerate disassemblies with `sh-elf-objdump -b binary -m sh2 -EB -D --adjust-vma=…` from exact starts; linear sweeps desync on the tables.

## Direct-colour staging copy (2026-10-05)

- Copy routine `0x020295B0`-`0x020295CA`: if the long at `0x06024C04` is 0, copy `0xFDC0` (64,960) words from `0x06003EF0` (cached SDRAM) to `0x24000200` (frame buffer, past the line table), one `mov.w` store per word. 320 × 203 × 2 bytes.
- Mode routine `0x0202C140`: reads `0x20004101` & `$7C`; argument r4 = 0 → mode 2 (direct colour) and flag = 0 (copy on); r4 ≠ 0 → mode 1 (packed pixel) and flag = 1 (copy off); r5 ≠ 0 adds bit 7 (PRI); then waits on VBLK in `0x2000410A` before writing.
- By instruction count about 7-9 clocks per word, 450,000-580,000 clocks per copy. In `src/patterns/streaming.md`.
- The SH-2 DMA registers are written only in the two VRES handlers (`0x02029F24`, `0x02029F62`: CHCR0/DMAOR cleared, plus Sega's `$44E0` slip); the FIFO is never armed.
