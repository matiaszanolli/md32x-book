# Mortal Kombat II (32X): analysis notes

Working notes, not part of the book. Started 2026-10-03. Cite as `MK2` (see `src/appendices/bibliography.md`).

Evidence levels: **ROM** = read from the retail dump's code or data. **Emulator** = observed running it in the VRD project's PicoDrive libretro core (not a console).

## The dump

- `Mortal Kombat II (Japan, USA).32x`, 4,194,304 bytes, MD5 `a95c0e7c1d35fd42cd2e3eb7b06cb6d0`. Header checksum `$4EB1` matches the contents. Header: `(C)T-81 1994.DEC`, `GM T-8101B-50`, regions `JUE`. Credits screen: programmed by Probe Entertainment, published by Acclaim.
- Sega's initial program (`$3F0`-`$7FF`) is byte-identical to Star Wars Arcade's.
- User header (`$3C0`): SH-2 program from ROM `$978`, `0x7E14` bytes, to `0x06000000`. Master entry `0x06000240`, Slave entry `0x06000244`, Master VBR `0x06000000`, Slave VBR `0x06000120`.
- ROM `$808`-`$977`: a table of longword pointers the SH-2 reads (asset directory). Mixed forms: SH-2 addresses (`0x020E016A`) and 68000 bank-window addresses (`$9xxxxx`), the latter converted by the SH-2 by adding `0x01700000`.
- 47 `RNC\x02` and 34 `RNC\x01` files (Rob Northen ProPack). The SH-2 program has a method-2 unpacker; method-1 files are the 68000's (checked 5 Oct 2026): three unpackers, ROM `$00CFF8` (to RAM), `$00D186` (32 KB ring at `$FF0000`, each finished word to `$C00000` after the caller sets a VRAM write address), `$0292F4` (to RAM, moves overlapping packed data first; callers `$028F38`/`$028F6E` check `RNC\x01` via `$028FA0` and queue a DMA via `$028FCC`; `$028FB6` does not check). Each builds 3 × 128-byte tables on the stack per chunk. Ten loaders via table `$008E5E` indexed by word `$FFAAC0` (code `$008E52`-`$008E5C`): each streams a 33-47 KB file to VRAM (`$0096E8`) and unpacks a 9-14 KB file to `$FF0000` (`$0096DC`); presumably arenas.

## Division of labour (ROM + emulator)

| CPU | Job |
|-----|-----|
| 68000 | The game. Mega Drive VDP draws the arenas and the HUD. Each frame it packs game state into a 668-byte block at `$FFF79A` and sends it to the Master through the communication ports (`$00DFAA`). Sound requests go to port 7 (`$00E01A`: writes `d0 | $100` to `$A1512E`) |
| Master SH-2 | Draws into the 32X frame buffer: the fighters and some foreground objects during fights, whole screens for the menus (fighter select, Battle Plan). Mode-driven state machine |
| Slave SH-2 | PWM sound only: two sample voices |

During a fight the 32X layer holds only the fighters and objects such as the hanging chain (frame buffer dump, frame 1700). The bitmap mode register reads `$8001`: packed pixel, **PRI = 0** (Mega Drive in front), but 255 of 256 palette entries have the through bit set, so 32X pixels come out in front of the Mega Drive's arena. Fighters get the 32X's colour depth; the arena stays Mega Drive tiles.

The two SH-2s share no SDRAM: the Slave's variables are `0x0600A200`-`0x0600A22B`, and the Master never touches them. They talk only through the ports.

## Start-up

**Master** (`0x06000250`), Sega's start-up sample almost verbatim:
- GBR = `0x20004000`; clears the V, H, CMD and PWM interrupts (two writes each).
- FRT: TIER `$00`, TOCR `$E2`, OCRA `$0001`, TCR `$00`, FTCSR `$01`, FRC 0, **then TOCR `$F2`, OCRB `$0001`, TOCR `$E2`** (Sega's "for correcting VRES" step, which Star Wars Arcade omits).
- Waits for port 0 = 0, then for `SLAV` in port 4 (`0x20004028`).
- FM = 1 (`$80` to `0x20004000`), SR = `$20`, interrupt mask `$0A` (V and CMD), then the main loop at `0x060004DC`.
- No serial port set-up (Sega's sample has one), no cache set-up (boot ROM's four-way, on), no DMA.

**Slave** (`0x0600510C`):
- Same FRT set-up without OCRB. Waits for port 0 = 0, writes `SLAV` to port 4.
- PWM: mono register `$0201` three times (513, the centre), cycle `$0413` (1043 → 23,011,361 / 1042 = 22,084 Hz), control `$0105` (TM = 1, normal L/R, no DREQ1). Interrupt mask `$01` (PWM only). SR = `$20`.
- Command loop: polls port 7 (`0x2000402E`) bit 8; low byte = sound number.

The stack-pointer vectors (`0x0C040000`, `0x0C03F000`) are never used on a 32X; the boot ROM sets the stacks. The error vectors (illegal instruction, address errors and so on) point to `0x023FB0xx`, ROM `$3FB000`, which is erased (`$FF`): a development leftover.

## Interrupts (ROM)

Both CPUs: one entry for all levels (`0x060002D8`, `0x06004E24`). It saves r0-r2, GBR and PR, raises the mask to 15, writes **TOCR = 0**, then calls the handler for SR's level from a 16-entry table. Each handler clears its interrupt, writes **TOCR = 2**, and reads the clear register and TOCR back. That is the scheme d32xr uses, not Star Wars Arcade's XOR.

| Level | Master | Slave |
|-------|--------|-------|
| 14-15 VRES | `0x06000350` | `0x06004EA8` |
| 12-13 V | `0x060003A4`: frame counter `0x0600A234` += 1 | `0x06004ED8`: clear only |
| 10-11 H | `0x060003D0`: clear only | `0x06004F00` |
| 8-9 CMD | `0x060003F4`: receive the 68000's packet | `0x06004F28` |
| 6-7 PWM | `0x060004A8`: clear only | `0x06004F4C`: sound |

**VRES handler** (both CPUs): Sega's corrective sample, including its slip. It writes DMAOR = 0 and CHCR0 = 0, then loads `$44E0` into the *address* register and stores 0 through it (to `0x000044E0`). With RV = 1 the Master sets TOCR bit 0 and loops; the Slave just loops. Same code in Star Wars Arcade. VRES returns by rewriting the exception frame (new SP, PC = start-up resume point, SR = `$F0`) and executing `rte` from inside the called handler.

## The 68000 → Master packet (ROM)

668 bytes (`$29C`) per frame, through ports 2-6, ten bytes per handshake:
- 68000 (`$00DFAA`): port 0 = 2, port 1 = 1, raises CMD on the Master (`$A15103` = 1). Then for each 10-byte step: wait for port 1 = 2, set port 0 = 1, write ports 2-6, set port 0 = 2.
- Master CMD handler (`0x060003F4`): toggles port 1 between 1 and 2 and copies ports 2-6 to `0x0600A248` onward. The handler busy-waits through all ~67 handshakes.
- Layout seen during a fight: `+0` camera X (`$01FA`), `+2` camera Y, `+$14` mode request, `+$3C` (`0x0600A284`) a 12-entry list of text objects, sprite object records further on (`0x0600A2B4`, `0x0600A2C8`, list at `0x0600A4E4`).

No FIFO/DREQ use anywhere.

## Master: modes (ROM + emulator)

Main loop `0x0600051A`: wait for the frame counter, flip FS, then call a handler from the table at `0x06000564`, indexed by the mode word `0x0600A22C`. Two entries per mode: per-frame, and first frame of a new mode.

| Mode | Seen as | First frame | Each frame |
|------|---------|-------------|------------|
| 5 | Fighter select (frame 900) | `0x060006B4` | `0x060006E2` |
| 6 | Battle Plan (frame 1140) | `0x060006FC` | `0x0600071C` |
| 10 | Fight (frames 1700, 2400) | `0x060007B4` | `0x060007DA`: clear, `0x06001BA8`, `0x060022B0` (sprites), `0x06001440`, `0x0600122A` (text), `0x06001E1C` |
| 0-4, 7-9, 11-15 | Not identified yet | | |

## Master: rendering (ROM)

- **Packed pixel, 368-byte lines** (`$170`), 226 lines, pixel data from frame-buffer byte `$8C00` (line table: `0x060010B0` writes words `$4600 + n × $B8`). **Guard bands:** the 35,328 bytes between the line table and `$8C00` are exactly 96 lines of 368 bytes, and the 48-pixel tail of each line is never shown. The clipper (`0x06002CEC`/`0x06002D04`) accepts sprites with x ≥ −48, right edge < 371 and y ≥ −96, so partly off-screen sprites draw into hidden memory and the blitters never clip per pixel. The Battle Plan uses a different table (320-byte lines from `$0980`).
- **Clear** (`0x060010DC`): 161 auto-fills of 256 words of 0 from word `$4600` (exactly the 224 visible lines), waiting for FEN after each one: about 125,000 Master clocks of polling a frame. Skipped while the flag at `0x0600A55A` is set. The idle mode (0) rewrites the line table and clears every frame, so both buffers get a table.
- **Frame flip** (`0x060010A4`): inverts the byte at `0x2000410B` (FS). **Vsync** (`0x06001088`): waits for the V-interrupt counter to change.
- **All sprite and text drawing goes through the overwrite image** (`0x24020000` + offset), so 0 pixels are transparent in hardware.
- **Fighter RLE** (blitters `0x060028C0` normal, `0x0600292C` mirrored): per sprite, a first byte gives the end-of-line marker. Each line starts with a skip count (added to the x position). Each following byte packs colour (bits 7-2) and run (bits 1-0). Run 0 means the run length is in the next byte. Colour 0 is skipped (transparent run). A palette offset (`r3`) is added per object, so each fighter gets a 64-colour slice. The mirrored version writes right to left from the same data.
- **Other objects** (blitters `0x060027F0`/`0x06002858`): the same format with colour in bits 7-4 and run in bits 3-0 (16 colours).
- **Sprite records** (`0x0600271E`): `+1` bit 4 mirror; `+2` bit 5 hidden, bit 0 world (subtract camera) vs screen; `+8` frame number; `+10`/`+12` x/y; `+16` animation table (68000 address, + `0x01700000`). Frame entries: hotspot x/y, width, height. Clipping in `0x06002CEC`/`0x06002D04`.
- **Text**: three proportional fonts unpacked into SDRAM at `0x06036B2C`, `0x06037F60`, `0x06038F28` (`0x060011A8`). Drawn by `0x060016AC` (glyph pixel value 1 → the requested colour).
- **Byte/word rectangle blits** through the overwrite image: `0x06004CC0` (bytes), `0x06004CF2` (words).
- **RNC method 2 unpacker**: `0x06002DF4` (its address is loaded at 30 places), skips the 18-byte header and checks no sizes. Bit buffer: one byte in the top of `r6`, `SHLL` into T, refill inlined at every read. ROM scan: 47 method-2 files, 1,139,686 bytes unpacked from 405,109 (36%), largest 99,132; 33 valid method-1 files, 566,412 from 272,981 (48%), at ROM `$70000`-`$DFCC8`.
- **Palette**: `0x06000982` clears the 256 entries after a vsync; a copy lives at `0x0600A000`.
- Instruction mix in the 12.9 KB of traced code: no `MAC`, no `DMULS.L`, no division unit, 32 `DIV1` (one software divide routine), 21 `MULU.W`, 6 `MULS.W` (mostly y × 368). It is a 2D blitter, nothing more.

## Slave: sound driver (ROM)

- Two voices (`0x0600A204`, `0x0600A218`); active bits at `0x0600A200`.
- Voice records: data pointer, sample count, loop pointer and count, phase (0-3).
- **6-bit samples packed four to three bytes** (`0x0600509C` unpacks phase 0-3). Each sample is played twice (the pointer advances on even counts only), so the data rate is half the output rate: about 11 kHz into 22 kHz.
- Output: one voice → `sample × 2 + $FF`; two voices → `a × 2 + b × 2 + 1`. Written to the mono register until FULL in each PWM interrupt (TM = 1). Silence = `$201`.
- New sound: if voice A is free use A, else B, else the one not used last.
- Sound table pointer at ROM `$970` (SH-2 address `0x02000970`).

## Smaller findings

- **Software divide:** two copies of the 16-step `DIV1` sequence for a 16-bit quotient (`0x0600114C`, `0x060015D2`); the division unit is never used.
- **Short runs unrolled:** the fighter blitter writes runs of 1-3 pixels with a chain of stores and `DT`/`BT/S`, looping only for long runs.
- **Sound requests are fire and forget:** the 68000 does not wait for the Slave to clear `$A1512E`.
- **Slave polls without a delay loop** (`0x06005178`), unlike Star Wars Arcade's Slave.
- **No serial set-up**, though the rest of Sega's start-up sample is copied.
- **Straight-through disassembly misleads:** it shows 124 `MAC.L`, 88 `MAC.W`, 105 `MUL.L` and 15 `SLEEP`; the traced code has none of them.

## Book corrections this produced

- `src/sh2/dmac.md`: Sega's VRES sample leaves CHCR0 = 0 and writes 0 to `0x000044E0` (not "CHCR0 back to `$44E0`"). Checked on the scan (32X-TIA1 p.6), in SWA and MK2.
- Discrepancy 22 and `src/sh2/timers.md`: MK2 sets OCRB = 1 like Sega's sample.
- Folded into: `src/32x/vdp.md` (guard bands, SH-2 FS flip, overwrite image, clear, through bit), `boot.md` (user header, unused vectors, `SLAV` handshake), `communication.md` (state block, bulk data through the ports, fire-and-forget sound, share-nothing SH-2s), `fifo.md`, `pwm.md` (third driver), `architecture.md` (address conversion), `src/sh2/intc.md`, `timers.md`, `cache.md`, `dmac.md`, `sci.md`, `divu.md`, `isa.md`, `pipeline.md`; catalogue entries for compositing, layering, compression, cpu-split, audio, 2d-effects, text-menus, memory, asset-pipelines and bus.

## Possible book uses

- `src/32x/compositing.md`: PRI = 0 plus the through bit on every palette entry to put 32X fighters over a Mega Drive arena.
- `src/32x/vdp.md`: overwrite image as hardware transparency for sprites and text; 368-byte lines; auto-fill clear.
- `src/techniques/compression.md` (written): RNC ProPack method 2 on the SH-2; colour/run RLE sprite formats; 6-bit packed PCM. `memory.md` (written): SDRAM map.
- `src/32x/pwm.md`: a third shipped driver (two voices, 6-bit samples, starts at the centre).
- `src/32x/communication.md`: a 668-byte packet through the ports every frame, no FIFO.
- `src/patterns/cpu-split.md`: Master = graphics, Slave = sound, no shared memory.

## Open questions

- What do modes 0-4, 7-9 and 11-15 show?
- What do `0x06001BA8`, `0x06001440` and `0x06001E1C` add during a fight? (`0x06001BA8` depends on a flag at `0x0600A272` and moves a value towards 96, perhaps a fade or a screen effect.)
- Where are the fighter sprite banks and animation tables in ROM, and are they RNC-packed or stored raw?
- How much of each frame does the Master spend busy-waiting on the 67-step packet transfer?

## Tools

`tools/`: `trace.py LISTING` (follows code from the entry points, dispatcher tables and jump tables; writes `codeset.txt`, `funcs.txt`) and `funcs.py LISTING` (per-function size, call count and hardware references), both MK2-specific. The shared scripts in `../tools/` do the rest: `sh2dis.sh "$ROM" 978 7e14 mk2` makes `mk2.bin` and `mk2.txt`; `rng.sh`, `render32x.py`, `sheet.py`; headless running is in `../tools/README.md`.

## System registers (checked 2026-10-04)

- Master: byte `$80` to `0x20004000` (FM), then byte `$0A` (V, CMD) to `0x20004001` at `0x060002B6`. Slave: PWM set-up (cycle `$413`, control `$0105`), then byte `$01` (PWM) at `0x0600516C`. No H interrupt.
- VRES handler (`0x06000350`): clears VRES, then `mov.b @(6,gbr),r0` / `tst #1` reads bit 8 of `0x20004006`, not RV; same slip as After Burner Complete. Book: `src/32x/registers.md`, discrepancy 33.
- No 68000 write sets RV and no reference to `$A130xx` (32 Mbit cartridge, so TI item 8's `$A130F1` initialisation is skipped). Book: `src/32x/bugs.md`.

## ProPack check (9 October 2026)

`rnc_check.py ROM` decodes every `RNC` file in a ROM and checks it against its
header. Method 2 follows the SH-2 unpacker at `0x06002DF4`-`0x06002F84` (402
bytes; literal blocks are (4-bit count + 3) × 4 bytes, copied two bytes per pass
over (count + 3) × 2 passes). Method 1 is the standard Huffman variant. On MK2 all
47 method-2 files (1,139,686 bytes unpacked, 405,109 packed) and all 33 method-1
files (566,412 unpacked, 272,981 packed) come out at the header's size with a
matching CRC-16. One `RNC\x01` hit at a false offset has impossible sizes and is
skipped.

## ProPack repacked with propack 0.2.0 (10 October 2026)

`rnc_repack.py ROM PROPACK_DIR` (PyPI `propack` 0.2.0, pure Python, unzipped wheel; 80 files, about 4 minutes). Packed sizes are the header's packed-size field. All outputs round-trip with both `rnc_check.py`'s decoders and propack's.

| Data | Unpacked | Original | propack m1 | propack m2 |
|------|----------|----------|------------|------------|
| 33 method-1 files | 566,412 | 272,981 (48.2%) | 291,292 (51.4%) | 299,979 (53.0%) |
| 47 method-2 files | 1,139,686 | 405,109 (35.5%) | 417,318 (36.6%) | 434,698 (38.1%) |

propack is 6.7% (m1) and 7.3% (m2) larger than the original packer in the same method. Method 1 over method 2: 2.9% smaller on the tiles, 4.0% on the SH-2 data (17,380 bytes). The header's byte 17 (chunk count) equals the chunks the method-2 decoder counts in all 47 files; byte 16 (leeway) is 2, 3 or 4 and is read by the 68000 unpacker at `$0292F4` (`move.b -2(a3),d0` with a3 at the packed data) to test whether the packed data overlaps its output.
