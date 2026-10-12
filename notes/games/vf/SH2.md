# Virtua Fighter (32X): the SH-2 program

Working notes for the case-study chapter. Source of everything below: the clean retail cartridge `Virtua Fighter (Japan, USA).32x` (32X-ROMSET; header checksum matches; SH-2 image at cartridge `$100000`, `$22000` bytes, loaded to SDRAM `0x06000000`), read as a listing (`sh-elf-objdump -b binary -m sh2 -EB`) and run in an instrumented PicoDrive. The 68000 side is in `M68K.md` (another reader); this file only needs its interface.

Evidence tags used here: **[ROM]** read in the retail code or tables; **[run]** observed in PicoDrive (emulator evidence, no SH-2 wait states charged, not a console measurement); **[inf]** inference, with what would decide it. "Not traced" means exactly that.

## 0. Most important findings

1. **Both SH-2s run the game, not only the picture.** The fight engine (finite-state machine per fighter with `COM_*`/`ACT_*` states, pad handling, collision, motion decoding) lives in the SH-2 image. The 68000 forwards pad bytes, option bytes and sound requests and draws the Mega Drive side. Per picture the Master and the Slave run **the same per-fighter update on one fighter each**, in lock step with two handshakes (Slave commands 5 and 6), and **split the collision test** between them (Master `0x06019FF4`, Slave command 3). [ROM, run]
2. **The 3D pipeline is a four-stage pipeline across the two CPUs, linked by two rings in SDRAM.** Master: pose matrices, then a transform/cull/clip/project/light routine copied to on-chip RAM (1,428 bytes at image `0x73B4`) that posts one 16-byte slot per visible polygon into **ring A** (`0x0603C000`, 256 slots). Slave command 2 consumes ring A concurrently and **bucket-sorts** the polygons by depth (512 buckets, `0x060368D0`). Then the Master walks the buckets far to near with a second on-chip routine (1,280 bytes at `0x194FC`) that turns each polygon into two y-monotone **edge chains clipped to a viewport**, posting 64-byte records into **ring B** (`0x06038000`, 256 records). Slave command 1 consumes ring B concurrently and rasterises with a third on-chip routine (560 bytes at `0x79EC`). Depth ordering is a painter's algorithm: no z-buffer. [ROM, run]
3. **Pixels are written two ways, chosen per polygon:** each scanline span of a flat-coloured polygon goes to the **VDP auto fill** (registers `0x20004104/06/08`; the Slave issues about 1,840 fills per picture in a fight; the length register is mostly 2-9, that is 3-10 words, 6-20 pixels), or, when the polygon's flag bit 1 is set, to the **overwrite image through CPU byte/word writes**. Edge pixels of fills are single CPU stores. Nothing uses SH-2 DMA. The frame buffer is packed-pixel with a 256-word line pitch, lines at word `0x1000 + 0x100*y`, one flat colour index per polygon (the index carries a light level: base index plus a shade of -7..+8). [ROM, run]
4. **The 68000 and the VDP fill do the housekeeping around it.** Per picture the 68000 clears the whole back buffer with **240 auto fills of data 0** (register `$A15184` = `$00A0`, start `$A15186` = `$1000, $1100, ...`), gives the VDP to the SH-2s with FM = 1, waits for `COMM0` high byte (`0x20004020`) to read 0, takes FM back and flips FS. It is the picture-complete handshake: **COMM0 high byte = busy**, set by the 68000's word write `$01xx`, cleared by the Master at the very end of its post-command routine (`0x06000988`). [ROM, run]
5. **Command protocol, 68000 to Master:** one byte in the low byte of `COMM0` (`0x20004021`) plus a CMD interrupt. Bit 7 clear (`$01`-`$10`): an **immediate command** that runs inside the CMD interrupt handler at `SR = 0x20`. Bit 7 set (`$80`+*n*): the handler stores `(cmd xor $80) * 4` in a one-halfword **mailbox** (`0x06020290`) and returns; the Master's main loop (`0x06000528`) polls the mailbox, calls through a longword table, checks that the stack pointer is unchanged, and then runs a common post-command routine (`0x06000900`). **Master to Slave:** a command number 1-8 in the byte `0x20004005`, which is the low byte of the **H count register** (used as shared storage, as PicoDrive's source already says some games do). The Slave polls it (table of 16 at `0x06000304`, 64-pass idle delay at `0x06000344`) and clears it when done. [ROM, run]
6. **Interrupts follow Sega's revised sample on the Master and nothing at all on the Slave.** The Master's single dispatcher (`0x06000120`) masks (`SR = 0xF0`), writes 0 to TOCR and reads it back, then jumps through a 16-entry level table at VBR+0x40; the CMD handler writes 2 to TOCR and reads back TOCR and the clear register. The Slave has per-level vectors: PWM straight to a handler **copied to on-chip RAM and patched into the vector table** at boot; its CMD vector is a register dump that never returns, and the Slave does enable CMD (INTM bit 1) although nobody ever raises INTS. The VRES handler on both CPUs clears VRES through the **cached alias** `0x00004014`, reloads SP and rewrites the saved PC/SR to restart at the manual-reset vector, and **does not read RV at all** (neither the wrong byte nor the right one). [ROM, run]
7. **PWM: Slave only, 3 voices, 8-bit samples summed into the mono register.** The PWM interrupt (level 6, every second PWM cycle: cycle register `0x417`, control `0x205`, about 11 kHz) mixes three resampled voices into `0x20004038`. A voice reads bytes straight from the cartridge (`0x22188000` table; PCM at cart `$1C6000`-`$1DB000`). Voices are started by Slave command 4 from a list the Master fills (the 68000 forwards two sound-id bytes per picture with immediate command 8). [ROM, run]
8. **Cache/memory discipline:** both CPUs run with `CCR = 0x09` (cache on, **two-way mode, 2 KB on-chip RAM**), SP = `0xC0000800`. On-chip RAM is used as an **overlay area** at `0xC0000000` (each phase copies its routine in) plus a state block at `0xC0000700`, a matrix stack and the three PWM voices. Shared data is handled by hand: cache-through reads (`0x2xxxxxxx`) for flags, associative purges (`0x4xxxxxxx` writes) before reading records the other CPU wrote, a whole-cache purge through CCR after each cross-CPU phase (`0x06000756`). The retail code never runs from the cartridge, SDRAM, and on-chip RAM only. [ROM, run]
9. **Against Virtua Racing Deluxe (same developer) the render back end is the same code lineage; almost everything around it differs.** Slave command 1 (ring consumer) is VRD's `0x060039F0` almost instruction for instruction (status halfword at record `+28` with the same values 8/4/6, end marker `0xAB00`, wrap `and 0xFFFFBFFF`, 16-iteration idle spin, purge-then-call), the Slave idle delay is byte-identical, the CCR routine has the same shape (`0x10`, eight `nop`s, `0x09`), both use the hardware divider with the quotient read from `0xFFFFFF1C`, both bucket-sort polygons and both let the 68000 flip FS. What differs is the front end: VRD streams a 2,560-byte scene description through the DREQ FIFO and transforms on **both** SH-2s with one on-chip routine; VF has no FIFO traffic, runs the game on the SH-2s, transforms on the Master only and gives the Slave the sort as a separate ring-A stage. Section 7 has the table. The VRD column comes from a separate read of the retail VRD code (by a delegated reader; the numbers were spot-checked here only for the ring consumer and the CCR routine).

Picture rate [run]: in the normal (recompiler) run the attract fights come at **exactly 2 frames per picture** (1,470 of 1,471 intervals), the SH-2 phase ends 1.17-1.82 frames after the go. In the interpreter run needed for tracing the same scenes take 3 frames; every duration below is from the recompiler run unless marked.

## 1. Memory map of the program

### 1.1 Image regions (SDRAM `0x06000000`-`0x06021FFF`)

Classification by recursive descent from the entry points and the tables, plus the set of instructions executed in about 5,500 frames of attract mode (21,326 distinct instruction addresses in SDRAM, 30,610 bytes; `regmap.py`). "E" = executed in the runs, "C" = code reached statically but not executed in attract mode (mostly interactive-play code), "D" = data or not reached.

| Range | What | Evidence |
|-------|------|----------|
| `0x000`-`0x0FF` | Master vector table (vectors 0-63); the slots of vectors 16-31 (`0x40`-`0x7F`) double as the **16-entry level table** the dispatcher indexes | [ROM] |
| `0x080`-`0x0FF` | Slave vector table (VBR `0x06000080`), laid over the Master's unused TRAPA vectors 32-63 | [ROM] |
| `0x100`-`0x11F` | Master IRL vectors 64-71, all to the dispatcher | [ROM] |
| `0x120`-`0x14F` | Master interrupt dispatcher | [ROM] |
| `0x150`-`0x162` | VRES handler (both CPUs) and a bare `rte` at `0x160` used as the Slave's stray-interrupt vector | [ROM] |
| `0x180`-`0x19F` | Slave IRL vectors 64-71 (PWM `0x856C` at 67, CMD `0x350` at 68, VRES `0x150` at 71) | [ROM] |
| `0x1A0`-`0x1BF` | Entry trampoline (`stc vbr,r0; mov.l @r0+,r1; jmp @r1; mov.l @r0+,r15`), `rts` at `0x1A8`, five `bra self` stubs at `0x1AC`-`0x1BC` used by the error vectors | [ROM] |
| `0x1C0`-`0x253`, `0x26C`-`0x2E3` | Master and Slave start-up, then the Slave's main loop at `0x2D2` | [ROM] |
| `0x254`-`0x26B` | Zero-fill `0x06021000`-`0x06029CA6` (called by the Master at boot and by immediate command 1) | [ROM] |
| `0x304`-`0x343` | Slave command table (16 longwords); `0x344` idle delay; `0x350`-`0x38B` Slave CMD register dump | [ROM] |
| `0x38C`-`0x497` | **Dead code**: 18 stubs (9 codes x Master/Slave COMM address). Each loads a 4-character code and `0x20004028`/`0x2000402C` into r0/r1 and then **pops them again without storing**, then spins. Nothing references them (no vector, no pointer) | [ROM] |
| `0x498`-`0x527` | Master CMD handler | [ROM, run] |
| `0x528`-`0x577` | Master main loop; `0x578`-`0x5BF` immediate command 9 (cold start); `0x5C0`-`0x603` immediate table (17 entries); `0x604`-`0x63B` deferred table (14 entries) | [ROM] |
| `0x64C` | Null command (`rts`). `0x650`-`0x6EB`: seven **unreferenced** stubs that guard on `0x0601EA60` and write `0xFFFFxxxx` words through a bad address | [ROM] |
| `0x70C`-`0x7D3` | Cross-CPU helpers (send/wait/ack), CCR set-up `0x738`/`0x770`, whole-cache purge `0x756`, wait-for-VDP-fill-idle `0x7C4` (polls bit 1 of `0x2000410A`) | [ROM] |
| `0x7D4`-`0x8FF` | Variable initialisation and two table-driven copy lists | [ROM] |
| `0x900`-`0xD5F` | Post-command routine, immediate commands 1/13/14/15, deferred commands 0x82-0x84 | [ROM] |
| `0xD60`-`0x2040` | Game-state handlers of the interactive mode (16-entry table at `0x0D54`) | [ROM] mostly **C** |
| `0x2048`-`0x2527` | Task registration (`0x2048` enables the task list entries, `0x222C` disables them) and the per-picture tasks `0x2370`, `0x2448`, `0x24C8` | [ROM, run] |
| `0x2528`-`0x5200` | Per-fighter state handlers (`COM_*`/`ACT_*` of the move state machine), object task `0x2528` and helpers | [ROM] partly E |
| `0x5E54`-`0x61B0` | **Debug name strings** left in the retail image: `COM_MOTION`, `ACT_MOTION`, `COM_KAMAE`, `COM_FWALK`, `COM_JUMP`, `COM_GUARD`, `COM_NAGE`, `COM_YARARE`, `COM_DOWN`, `COM_TARGET2`, ... (Japanese move vocabulary, about 50 pairs) referenced from a pointer table at `0x61B8`; also `JUDGE ERROR` at `0x1494` (unreferenced) | [ROM] |
| `0x5200`-`0x6450` | Fighter state code and tables | [ROM] |
| `0x6450`-`0x7360` | Slave commands 8 and 7, Master commands, the cross-fighter tasks `0x63F0`, `0x69A8`, `0x6D1E`, `0x6E68`, `0x6F40`; `0x71C4`-`0x72F3` the Master's and Slave's ring/sort set-up (`0x7214` Slave) | [ROM] |
| `0x7364`-`0x73B3` | Master loop that calls the on-chip engine for each body part | [ROM, run] |
| **`0x73B4`-`0x7947`** | **Overlay A**: the transform/cull/clip/light routine, 1,428 bytes, copied to `0xC0000000` (`0x7398`) | [ROM, run] |
| `0x730C`-`0x7347` | **Overlay D**: depth-bucket insertion stub, 60 bytes, copied by the Slave (`0x72F4`) | [ROM, run] |
| `0x7948`-`0x79EB` | Slave command 1 (draw loop); `0x79EC`-`0x7C1B` **overlay C**: rasteriser, 560 bytes (`0x79D0` copies it); `0x7BE8`, `0x7AE0`: span routines (CPU stores / VDP fill) | [ROM, run] |
| `0x7C1C`-`0x82F3` | Deferred commands 0x88-0x8B (demo/attract set-up: scripts read from cart `$120430`...) | [ROM] mostly C |
| `0x82F4`-`0x8873` | Immediate commands 2-8, 12, 16 (sound enqueue, ROM image decompress/blit, option bytes), Slave commands 3 and 4, PWM interrupt (`0x856C`), voice start (`0x86C8`) | [ROM, run] |
| `0x8840`-`0x8A0B` | Task-list builder and the task spec table (`0x8888`) | [ROM] |
| `0x8A0C`-`0x9B7F` | Fighter pose/matrix code (`0x8B04` and callers), `0x969C` the main render task | [ROM, run] |
| `0x9B80`-`0xE000` | Fighter AI / move logic (compares `[obj+64]` with move numbers `0x19E`, `0x286`, ...), mostly **C** | [ROM] |
| `0xE000`-`0x12000` | Fighter logic, the camera and animation code | [ROM] partly E |
| `0x12000`-`0x19000` | Animation/motion decoding, joint code, task entries (`0x12A08`, `0x16830`...) and the **matrix library** at `0x190B8`-`0x19400` | [ROM, run] |
| `0x19424`-`0x199FB` | `0x194A8` post-sort stage and **overlay B**: edge-chain builder, 1,280 bytes at `0x194FC` | [ROM, run] |
| `0x19F00`-`0x1A00B` | Sprite-list drain (`0x19F00`), run-length image blitter (`0x19F3A`), LZ-type image decompressor (`0x19F64`) | [ROM] |
| `0x1A00C`-`0x1A357` | Collision test (both CPUs) | [ROM, run] |
| `0x1A358`-`0x1A3F5` | Software 32/32 divide (`div0s`/`div1` x32); `0x1A808` motion-channel decode | [ROM] |
| `0x1A6A4`-`0x1B4C0` | Fixed-point/matrix and animation helpers | [ROM] |
| `0x1B4B0`-`0x1C300` | Data: 16-byte record arrays (zero/`ffff ffff` patterns), small constant tables | [ROM] D |
| `0x1C300`-`0x1C4A7` | 16-bit monotone table (about 39 steps; function not determined) | [ROM] |
| `0x1C4A8`-`0x1C5BF` | Per-picture collision driver (`0x1C4A8`) | [ROM, run] |
| `0x1C5C0`-`0x1D7FF` | Pair tables for the collision test (`0x1C5D0`), 16-byte record arrays | [ROM] |
| `0x1D6E0`-`0x1E47F` | **Pointer tables to cartridge data** (`0x22xxxxxx`): the motion table, indexed by move number | [ROM] |
| `0x1E480`-`0x1E85B` | Master hit-mask routines (`0x1E48C`), blitter with a `braf` table (`0x1E7FC`) | [ROM, run] |
| `0x1E85C`-`0x1FFFF` | **Padding**: the string `(C)1994-1995 COPYRIGHT SEGA ENTERPRISES,LTD. 1993-1995 ` repeated | [ROM] |
| `0x20000`-`0x20FFF` | Initialised data: character/move parameter tables (16-bit fractions such as `$4CCD`, `$B333`), pointer table to cart `$120144`..., and the **variable block** `0x06020264`-`0x060202FF` (mailbox `0x06020290`, loop counter `0x0602028C`, option values `0x0602026C`-`0x0602029C`) whose initial bytes are leftovers | [ROM] |
| `0x21000`-`0x21FFF` | Tail of the image; **zeroed at boot** (`0x254`), so its image bytes are not used | [ROM] |

### 1.2 SDRAM beyond the image

All from literal pools; not every variable is understood.

| Address | Use | Tag |
|---------|-----|-----|
| `0x0601E95C` / `0x0601EA5C` | Master / Slave initial SP from the vector tables; they matter only until the start-up code sets SP = `0xC0000800`, and after a VRES (the handler reloads SP from the vector table) | [ROM] |
| `0x0601EA5C` | The Master main loop stores its SP in this longword (just above the Slave's boot stack) to check balance after each command | [ROM] |
| `0x0601EA60` | Halfword cleared by the CMD handler's mailbox path; only the unreferenced stubs set it | [ROM] |
| `0x06020290`, `0x0602028C` | Mailbox, free-running pass counter (copied to `0x0600F3A8` and used as entropy for the random routine) | [ROM] |
| `0x060202A0` | Pointer into the sprite list `0x060202A4`... (RLE images to draw, drained by `0x19F00`) | [ROM] |
| `0x06021000`-`0x0602102F` | **Task list**: entries of 16 bytes (flag, function pointer, offset to the next entry, argument) | [ROM, run] |
| `0x06021030`, `0x06023230`, ... | **Fighter objects**, `0x2200` bytes each, linked in the task list; pointers `0x0602700C` (fighter A), `0x06027010` (fighter B), `0x06027028` (a third object) | [ROM, run] |
| object `+0x360` position (3 longs), `+0x4EC`, `+0x518`, `+0xE78` (character id, indexes the pointer table at cart `0x2212A94C`), `+0xF80` pose blocks (48 bytes each), `+0xFB0` joint angles, `+0x20BC` body-part descriptors (20 bytes: enable halfword, model pointer at `+16`), `+0x1814`, `+0x1834`, `+0x1878` | Fields used by the engine, motion and HUD code | [ROM] |
| `0x06027000`-`0x0602703C` | Task slot pointers (each points at an entry of the task list) | [ROM] |
| `0x06027100`-`0x06027160` | Mode/phase flags (`0x06027114` bit 15 = skip object, `0x06027120` bit 0, `0x06027154`/`55`, `0x06027156`...) | [ROM] |
| `0x060272E8`-`0x06027928`, `0x06027450`, `0x06027720`, `0x060275B8`, `0x06027888`-`0x06027908` | Joint position and collision scratch (cleared by Slave command 3; Slave result at `0x06027908`) | [ROM, run] |
| `0x06029984`, `0x06029988` | Phase counter and **game state** (`0x06029988` runs 0-4 through a round in attract mode; 0-15 in the interactive handler table) | [ROM, run] |
| `0x06029A58`-`0x06029BE4` | Matrix helper state, pad state (`0x06029BAC`), results | [ROM] |
| `0x06029C24`-`0x06029C33` | The 16-byte **status block** copied into the frame buffer mailbox at the end of every picture | [ROM, run] |
| `0x06029CA7` | End of the boot clear (`0x06021000`-`0x06029CA6`) | [ROM] |
| `0x06030000`-`0x060368CF` | **Unpacked models**: the polygon streams of both fighters (16 parts each) and the arena, unpacked from cart `0x22144000`... at scene load by `0x19D5C`/`0x19DDA` (destination `0x06030000`); e.g. the arena octagon at `0x060367D0`, fighter parts at `0x0603290C`-`0x060361xx` | [ROM, run] |
| **`0x060368D0`**-`0x06036CCF` | **Depth bucket table**: 512 halfword list heads (`0xFFFF` = empty) | [ROM, run] |
| `0x06036CD0`-`0x06037FFF` | Sort node pool (8-byte nodes: next, key, pointer; about 600 nodes), allocated from offset `0x400` past the head table | [ROM, run] |
| **`0x06038000`**-`0x0603BFFF` | **Ring B**: 256 records of 64 bytes (section 4.4) | [ROM, run] |
| **`0x0603C000`**-`0x0603CFFF` | **Ring A**: 256 slots of 16 bytes | [ROM, run] |
| `0x0603D000`-`0x0603FFF7` | Polygon records written by overlay A (20 bytes each), grows from `0x0603D000` | [ROM, run] |
| `0x06038020` | The engine's per-vertex scratch (16 bytes a vertex) overlaps the first ring B records; ring B is only initialised (`0x19424`) after the transform phase, so the two uses do not coincide in time | [ROM] |

### 1.3 On-chip RAM (`0xC0000000`-`0xC00007FF`, per CPU, two-way mode)

| CPU | Address | Contents | Source / size |
|-----|---------|----------|---------------|
| Master | `0xC0000000` | Overlay A (transform/cull/clip/light), later overlay B (edge chains) | image `0x73B4`, 1,428 B, by `0x7398`; image `0x194FC`, 1,280 B (`0x140` longwords), by `0x194E0` |
| Master | `0xC0000000`-`0xC00002xx` | While `0x1E48C` runs: five small bit arrays used as work space | [ROM] |
| Master | `0xC0000400`... | **Matrix stack** (3x4 matrices, 16.16, 48 bytes each); stack pointer in `0xC0000680`; reset to one identity matrix by `0x190B8` | [ROM] |
| Master | `0xC0000700`-`0xC000074E` | **State block** of the engine (see 4.2); `0xC0000748` holds the decoded light vector | [ROM] |
| both | `0xC0000800` | Initial SP, growing down | [ROM] |
| Slave | `0xC0000000` | Overlay C (rasteriser) during command 1; overlay D (60-byte sort stub) during command 2 | image `0x79EC`, 560 B (`0x8C` longwords); image `0x730C`, 60 B (15 longwords) |
| Slave | `0xC00005F0` | PWM interrupt handler and voice-step routine (96 bytes copied from image `0x856C` at boot, **vector 67 patched to this address**) | [ROM, run: PCs `0xC00005FE`...] |
| Slave | `0xC0000650`, `0x660`, `0x670` | Three 16-byte **voice** records | [ROM] |
| Slave | `0xC0000080`... | Collision accumulator (`0xC00000A4`, `0xC00000A8`, `0xC00000AC`, `0xC00000B0`, `0xC00000B4`: loop controls) and result words, `0xC0000170` table | [ROM] |
| Slave | `0xC0000400`, `0xC0000680`, `0xC0000700` | Matrix stack (reset by Slave command 7), engine-style state block used by the ring code | [ROM] |

The Master reuses the matrix-stack area for overlay A's tail: overlay A (1,428 bytes) covers `0xC0000400`-`0xC0000593`; the pose code that uses the stack runs before the copy, in `0x969C`. [ROM, inferred from order]

## 2. The interrupt side

### 2.1 Vector tables and dispatcher

Master table at `0x06000000`: power-on PC `0x060001CC`, SP `0x0601E95C`; manual-reset PC `0x060001C0`; vectors 4, 6, 9, 10 (illegal instruction, slot illegal, CPU address error, DMA address error) go to four separate `bra self` stubs `0x1B0`, `0x1B4`, `0x1B8`, `0x1BC`; every other non-IRL vector to `bra self` at `0x1AC`; TRAPA vectors to `rts` at `0x1A8`. IRL vectors 64-71 (VBR+0x100) all point to `0x06000120`. Slave table at `0x06000080`: power-on `0x06000278`, manual reset `0x0600026C`, SP `0x0601EA5C`; IRL vectors at `0x180`: 64-66, 69, 70 to the `rte` at `0x160`, 67 (PWM) to `0x0600856C` (patched at boot, 1.3 above), 68 (CMD) to `0x06000350`, 71 (VRES) to `0x06000150`. [ROM]

**Master dispatcher `0x06000120`** (revised-sample style, as MK2 in `src/sh2/intc.md`): push r0, r1, r2, PR; `ldc 0xF0,sr` (mask all) with the old SR kept in r0; `TOCR (0xFFFFFE17) := 0` and read back; level = `(SR >> 4) & 15` from the saved SR; `jsr` through the table at VBR+0x40; pop and `rte`. The table (vectors 16-31 of the vector table, `0x40`-`0x7F`): levels 8 and 9 to `0x498` (CMD), levels 14 and 15 to `0x150` (VRES), everything else to an `rts`. V, H and PWM entries are `rts` because the Master enables none of them. There is **no** exclusive-OR of TOCR anywhere: the byte is written only by the dispatcher (`0x06000130`, value 0), by the CMD handler through the pointer the dispatcher leaves in r1 (`0x0600049E`, value 2) and by the FRT start-up code (2.2). [ROM]

**Master CMD handler `0x06000498`**: writes 2 to `0x2000401A` (CMD clear), writes the same 2 to TOCR (`mov.b r0,@r1` with r1 still `0xFFFFFE17` from the dispatcher), reads TOCR and the clear register back, then reads `COMM0` low byte (`0x20004021`):

- bit 7 clear: **immediate command**. Saves r3-r14 and PR, picks the handler from `0x060005C0 + 4*cmd`, calls it with `SR = 0x20` loaded in the `jsr` delay slot (so level-8 requests can nest again and anything above mask 2), then writes 0 to `0x20004021`, restores, `rts`. [ROM]
- bit 7 set: **deferred command**: writes 1 to `0x2000401A` a second time (harmless), computes `((cmd xor 0x80) & 0xFF) << 2`, stores it in the halfword `0x06020290`, clears `0x0601EA60`, returns. The 68000 never sees an acknowledge of the byte itself: the Master clears `0x20004021` later (at the start of the command handler, e.g. `0x06000A3A`, `0x060065DE`). [ROM, run]

**VRES handler `0x06000150` (both CPUs)**: `mov.w r0,@(0x4014)` (a halfword write to the **cached alias** `0x00004014` of the VRES clear register), `SP := [VBR+12]`, push `0xF0` (SR), push `[VBR+8]` (the manual-reset PC), `rte`. So after the reset button each CPU restarts at its manual-reset vector (`0x1C0` Master, `0x26C` Slave) with a fresh stack and all interrupts masked, re-posts `M_OK`/`S_OK` (the 68000's reset path waits for them as the sample does) and runs its normal start-up again [run: PicoDrive's core reset at frame 1200 shows exactly this: the Master writes the clear register with r0 = `0x150`, the Slave with r0 = `0x344`, then `M_OK` and `S_OK` appear in COMM0/COMM2 again]. There is **no RV test of either byte, no DMA off, no `0x44E0`**: it matches neither defect of Sega's sample (`src/appendices/sample-code.md` lists VF under "Neither matched"; the handler shape is new: it is closest to MK2's "rewrite saved PC/SR/SP and `rte`", without the rest). [ROM]

**Slave**: vector 67 (PWM, level 6) is the on-chip copy of `0x0600856C`: push r0-r4/PR, run the voice step for three voices (r3 = `0xC0000650`, `+16`, `+16`, r4 = running sum), `mov.w r0,@(0x401C)` (clear through the cached alias, no read-back), write the sum to `0x00004038` (PWM mono), pop, `rte`. No dispatcher, no TOCR access, no `nop`s: it does not follow Sega's interrupt sample at all (the other CMD, H/V entries are `rte`). Vector 68 (CMD) is a register dump (`0x06000350`: masks, saves r0-r15, PR, PC and SR as 19 longwords at `0x060000B4`-`0x060000FF`, spins). **The Slave sets INTM bit 1 (CMD) anyway** (`0x060002C8`: `or #2`), and bit 0 (PWM, `0x06008640`); nobody raises INTS: the 68000 only writes `$A15103 = 1` (Master) in 5,500 frames. [ROM, run (boot trace: `S 0x20004000 := 0x0203`, `M 0x20004000 := 0x0202`)]

### 2.2 Set-up code

- **FRT/TOCR** (both CPUs, `0x1D6`-`0x206`, `0x282`-`0x2B0`): TIER 0, TOCR `0xE2`, OCR 1, TCR 0, FTCSR 1, FRC 0, TOCR `0xF2`, OCR 1, TOCR `0xE2`: Sega's FRT sequence for the interrupt workaround. [ROM]
- **INTM mask** `0x20004000`: Master `0x0202` (ADEN, CMD), Slave `0x0203` (ADEN, CMD, PWM) [run].
- **SR**: both CPUs run the main loops at `SR = 0x20` (mask 2); handlers mask `0xF0` on entry. [ROM]
- **CCR**: `0x738` writes 0x10 (purge) then, after 8 `nop`s, 0x09; `0x770` first writes the low byte of `r1 << 4` to CCR (it is `0x20`: r1 still holds `0xFFFFFE92` from `0x738`, so this is a leftover, bit 5 is documented as reserved), zeroes 64 tag entries at `0x60000000` (way 0) and finally writes 0x09 again. So **CE = 1, TW = 1 (two-way, on-chip RAM), ID = OD = 0**, no way locking. A third site, `0x756`, reads CCR through the mirror address `0xFFFFFE93`, ORs 0x10 (purge) and writes it back: a whole-cache purge with the cache enabled. [ROM]
- Neither CPU touches SCI, WDT, DMAC, the bank/RV registers, or the PWM registers (except the Slave's PWM set-up) in the code that was executed; a literal scan finds none of the DMAC/WDT addresses. The SH-2 DMAC and the 32X DREQ FIFO are **not used** [ROM, run: no 68000 FIFO write in 5,700 frames].

### 2.3 What the 68000 raises and how it is acknowledged

Only `$A15103 = 1` (INTM, the Master); every command raises CMD, immediate or deferred. Acknowledge of the command byte is implicit (the Master writes 0 to `0x20004021`); completion of a **picture command** is the busy flag (`COMM0` high byte, 3.3). The 68000's first command after boot is immediate 9 (cold start). [run]

## 3. The command protocol

### 3.1 COMM words as the SH-2s use them (68000 side in `M68K.md`)

SH-2 address / 68000 address | Role as read from the SH-2 code | Tag
---|---|---
`0x20004020` / `$A15120` (COMM0 high byte) | **Busy flag**: the 68000 writes `$01cc` as a word, the Master writes 0 at the end of `0x06000900` | [ROM, run]
`0x20004021` / `$A15121` (COMM0 low byte) | Command byte (bit 7 selects deferred); cleared by the Master | [ROM, run]
`0x20004022` (COMM1 word) | Pad bytes of the two players, read by `0x06018B04`; also written back by immediate command 11 (results) | [ROM]
`0x20004024` (COMM2) | Boot handshake `S_OK` (Slave); the high byte is read by command 0x88 (`0x06007C1C`) as a script number | [ROM] (second use [inf])
`0x20004028`-`0x2000402B` (COMM4, COMM5) | Parameters of immediate commands: the two bytes of COMM4 are the sound ids for 2/8, COMM4+COMM5 as one longword is a ROM offset for 3-7; COMM1-COMM4 hold the eight option bytes of 12 | [ROM, run]
`0x2000402C`-`0x2000402F` (COMM6, COMM7) | 68000 to SH-2: x and y halfwords of the blit commands (`0x060084CC`). SH-2 to 68000: COMM7 high byte `0x2000402E` cleared at the end of the post routine (bit 0 follows "state == 15"), COMM7 low byte `0x2000402F` written by command handlers (`M68K.md` reads it as the scene code and bit 2 as a timer freeze) | [ROM, run]
Frame buffer `0x24000200`... / `$840200` | 16-byte status block (two energy values and one more halfword, from `0x06029C24`) written by `0x06009800`-`0x0600983A` after the picture; the 68000 reads 24 bytes of it | [ROM, run]

### 3.2 Master immediate commands (table `0x060005C0`, `COMM0` low byte 1-16)

| Cmd | Handler | What it does | Tag |
|-----|---------|--------------|-----|
| 0 | `0x064C` | Nothing (`rts`) | [ROM] |
| 1 | `0x09C4` | Re-initialise: zero SDRAM (`0x254`), build the task list from the spec at `0x06008888` (`0x8840`), set up counters, clear `COMM1`-`COMM7` | [ROM] |
| 2 | `0x8318` | Enqueue the two sound-id bytes in `0x20004028`/`29` (`0x8750`), send Slave command 4, wait for the Slave: used in menus | [ROM], 68000 side [M68K] |
| 3 | `0x8404` | Decompress a cart image (`COMM4/5` long + `0x21700000`, `0x19F64`) into `0x06021000`, copy a 112 x 120 block into the frame buffer at (x, y) from `COMM6/7`, with a 320-byte line stride, while holding FM = 1 | [ROM] |
| 4 | `0x8454` | Same with the block flipped horizontally (byte-swapped) | [ROM] |
| 5 | `0x8350` | FM := 1 (write `0x80` to the byte `0x00004000`), decompress a cart image straight into the overwrite image at `0x24020200`, FM := 0. Used for the SEGA/AM2/title screens (14 times in 5,700 frames of attract) | [ROM, run] |
| 6, 7 | `0x838C`, `0x83C8` | FM := 1, call the run-length/blit routine `0x1E7FC` with mode 0 / 1 for a cart object at (x, y), FM := 0 | [ROM] |
| 8 | `0x82F4` | **Sound request**: enqueue the two bytes `COMM4`/`COMM5` (`0x8750`: appends to a list of at most 7 halfwords at `0x06008776`, byte count at `0x06008774`). Sent **once per picture** (1,472 times in 5,700 frames), usually with 0, 0 | [ROM, run] |
| 9 | `0x0578` | **Cold start**: zero `0x06020332`-down 0x1AD5 bytes, `0x07D4` and `0x083C` (variable and table initialisation), reset the sprite list pointer, clear COMM0 low byte. The first command the 68000 sends | [ROM, run] |
| 10 | `0x69A8` | Select a two-player/handicap set-up: `mode_a := 2`, copy parameter blocks from cart tables at `0x221202A0`, `0x221202A8`, `0x221203A8` indexed by `mode_b` | [ROM], role [inf] |
| 11 | `0x6D1E` | **Return time/score digits**: divides the counter at `0x0602027C` by 100 and 60 (`0x0600F368`), writes the result to `COMM4`/`COMM1`/... for the 68000 (ranking screen) | [ROM], role [inf] |
| 12 | `0x8784` | **Option bytes**: reads eight bytes from `COMM1`-`COMM4`; each indexes a ROM table (`0x22122650`, `0x22122664`, `0x2212266C`, `0x22122680`, `0x22122628`, `0x22122688`) and fills `0x0602026C`, `0x06020270`, `0x06020295`, `0x06020274`, `0x06020298`, `0x06020278`, `0x06020292`, `0x0602029C`. Sent twice in attract with bytes `2 2 1 2 1 2 0 0` | [ROM, run] |
| 13 | `0x099C` | `[0x06027156] := 10` | [ROM] |
| 14 | `0x09C0` | `rts` | [ROM] |
| 15 | `0x09A8` | Clear `0x0602027C`, `0x06020280` | [ROM] |
| 16 | `0x8818` | Read one byte of `COMM1`, map through `0x22122688` into `0x0602029C`, call `0x6009964` | [ROM] |

### 3.3 Master deferred commands (table `0x06000604`, `COMM0` low byte `0x80 + n`)

The main loop (`0x06000528`) reads the halfword at `0x06020290`, increments the pass counter, hangs in a `bra self` if the value exceeds `0x80` (index > 32), saves SP in `0x0601EA5C`, calls through the table, hangs at `0x574` if SP changed, and if the command was non-zero jumps to the post routine. The table has **14 valid entries** (index 0-13); the check allows more, but the words after entry 13 are code. [ROM]

| Cmd | Handler | Role | Tag |
|-----|---------|------|-----|
| 0x80, 0x81 | `0x064C` | Null | [ROM] |
| 0x82, 0x87 | `0x0A28` | **Start a match**: clear command byte, rebuild the task list, enable the tasks (`0x2048`), read `COMM1`: two bytes (low 5 bits = character, `0x20` = flag) into `0x0602996A`/`0x0602996C`, a stage byte from `COMM4` through a table (`0xB70`) into `0x06027156`, ... | [ROM] |
| 0x83 | `0x0B7C` | Set mode: sign of `COMM1` byte, `COMM2` low byte indexed through `0x0C6C`, call `0x12600`, `0x8A0C` | [ROM] |
| 0x84 | `0x0C70` | **Interactive picture step**: call `0x18B04` (pads), then the 16-entry state table at `0x0D54` indexed by `game_state` (`0x06029988`), set `COMM7`-low byte | [ROM] |
| 0x85 | `0x652C` | Reset to the first scene state: `0x06027152 := 1`, mailbox `:= 0x18`, copy matrices, call `0x19E2C`, `0x19E6C`; sent twice in attract | [ROM, run] |
| 0x86 | `0x65D8` | **Attract/demo picture step**: clear command byte, `0x06029988` selects one of five phases through the table at `0x06006628` (`0x663C`, `0x6662`, `0x67B8`, `0x6834`, `0x68BC`); then, if bit 3 of `[0x0602713C]` is set, call `0x19ED0` with r4 = 2 and r5 = `0x240378F6` (an overwrite-image address). Sent **once per picture: 1,472 times in 5,700 frames of attract** (plus the 0x85 above twice). In play the 68000 sends `0x84` instead [M68K] | [ROM, run] |
| 0x88, 0x89 | `0x7C1C`, `0x7C90` | Demo set-up: pick a script from cart `0x22120430` by `COMM2` (and `0x7C90` steps it) | [ROM], not run |
| 0x8A, 0x8B | `0x7FB4`, `0x7FE8` | Demo/replay variants | not traced |
| 0x8C | `0x6E68` | Another picture step with its own 3-state table at `0x06006FBC` (`0x6FC8`, `0x70A8`, `0x713A`) | [ROM], not run |
| 0x8D | `0x6F40` | Step used with `0x06020290 == 0x34` checks in the render task | not traced |

**After any deferred command the main loop goes to the post routine `0x06000900`** [ROM, run]:

1. `jsr 0x060190B8` (reset the Master's matrix stack).
2. `0x20004005 := 7` (Slave command 7: the Slave resets its matrix stack; the byte is written directly here, not through `0x70C`) and wait for it to read 0.
3. Walk the **task list** at `0x06021000`: for each entry whose flag word is non-zero call the function in its second word; stop when the third word (offset to the next entry) is 0.
4. Decrement `0x06029984` unless bit 0 of `0x06027120` is set; clear the mailbox; set/clear bit 0 of `0x2000402E` according to `game_state == 15`; dummy write; write 0 to `0x20004020` (**picture done**); back to the main loop.

The task list of an attract fight, at frame 2000 [run, `0x06021000`]: `0x0600B0E4` (arg `0x00070000`), `0x06012A08`, `0x06012A14`, then one object entry per fighter (`0x06002528`, 0x2200 bytes apart). Other task functions registered by `0x2048` are `0x0601229C`, `0x06012350`, `0x06002340`/`0x06002350` (switch a slot to `0x2528`), `0x06002360` (switch to `0x2370`), `0x060167D4`, `0x06012518`, `0x060098F4`, `0x06018CF4` (sends Slave command 4 each picture), `0x06018D1C`, `0x060063DC` (switch to `0x063F0`, which sends Slave command 8), `0x0600967C` (switch to `0x969C`), `0x06018B54`. [ROM]

### 3.4 Slave commands (table `0x06000304`, byte `0x20004005`)

Main loop `0x060002D2`: `r2 := byte @0x20004005` (sign-extended), `jsr @(table + 4*r2)`, loop. Entries 0 and 9-15 go to the idle delay at `0x344` (`mov #64,r7; nop; dt r7; bf`: about 320 clocks between polls). A value above 15 or below 0 would index outside the table (never sent). Each command ends by `jmp 0x724`: a dummy write of `0x34` to `0x06000034` (the low byte of r0, which holds that address; the word at `0x06000034` is an unused vector slot) and `0x20004005 := 0`. Commands are only written by the Master, through `0x0600070C` (wait until the byte reads 0, then store) and waited for with `0x060007A0`. [ROM, run]

| Cmd | Address | Role | Tag |
|-----|---------|------|-----|
| 1 | `0x7948` | **Draw loop**: copy overlay C (`0x79D0`), then consume ring B records at `0x06038000` (64 bytes, status halfword at `+28` through `0x2xxxxxxx`, bit 2 = ready, bit 1 = end marker `6`), purge the record's four cache lines, call the rasteriser at `0xC0000000`, write 8 (free) back, step 64 with wrap `and 0xFFFFBFFF`; on the end marker write `0xAB00` and finish. About **270 polygons per picture** in a fight (273 on average over 11 pictures) | [ROM, run] |
| 2 | `0x729A` | **Sort stage**: copy overlay D, initialise ring A (256 slots := 8) and the bucket table (512 halfwords := `0xFFFF`) (`0x7214`), then consume ring A at `0x0603C000` (16-byte slots, status at `+0`, bit 2 = ready, bit 1 = end marker; purge, call the stub at `0xC0000000`, write 8, wrap `and 0xFFFFCFFF`); on the end marker write `0xAC00` and finish | [ROM, run] |
| 3 | `0x84FC` | Zero `0x060272E8`-`0x06027927` (5 blocks of `0x140` bytes through GBR), run the collision routine `0x1A00C`, copy its three result longwords from `0xC0000080` to `0x06027908` | [ROM, run] |
| 4 | `0x8674` | **Start PWM voices**: with SR := `0xF0`, take the sound-id list at `0x06008774`, start a voice per id (`0x86C8`), clear the list | [ROM, run] |
| 5 | `0x2448` | **Per-fighter update, pass 1 for fighter B** (`[0x06027010]`): `0xF3B0`, `0x117BC`, `0x11B5C` (unless game_state 14), `0x5472`, `0x5B8C`, then purge the whole cache (`0x756`) | [ROM, run] |
| 6 | `0x24C8` | **Pass 2 for fighter B**: `0x12604`, `0x8B04`, `0x165F4`, `0x1679C`, `0x10B74`, purge | [ROM, run] |
| 7 | `0x6E4C` | Reset the Slave's matrix stack (`0x190B8`) | [ROM, run] |
| 8 | `0x6450` | Pose of fighter B (`0x8B04`) and a function of its position `[obj+0x360..]` (`0x64B8`), result to `0x06029B64` (the Master does the same for fighter A and stores it at `0x06029B60`), purge | [ROM, run] |
| 0, 9-15 | `0x344` | Idle | [ROM] |

### 3.5 Per-picture sequence

All times are 68000 cycles from the go (`COMM0 := $0186`), **recompiler run** at frame 2000 of the attract mode (127,987 cycles per frame; the 68000 clock is the unit of PicoDrive's event time, not the SH-2's) [run]:

| t | Event |
|---|-------|
| 0 | 68000 writes `COMM0 := $0186`, then `$A15103 := 1` (CMD to the Master) |
| +50 | Master CMD handler stores the mailbox; the main loop picks it up, runs `0x65D8`, clears `COMM0` low byte |
| +135 | Post routine: Master writes `0x20004005 := 7` |
| +460 | Slave command 7 done |
| +1,100 | Master task `0x2370` sends Slave command 5 (fighter B pass 1) and runs the same chain for fighter A; Slave done at +4,650 |
| +4,670 | Slave command 6 (pass 2); done at +11,000 |
| +11,700 | 68000: sound request (`$A15121 := 8`, `COMM4/5 := 0`, `$A15103 := 1`); the immediate command runs inside the Master's current command (nested) |
| +12,100 | 68000 starts 240 auto fills of data 0, **one 256-word line each**, `$A15184 := $A0` |
| +16,700 | Master sends Slave command 3 (collision), Master runs its half; done at +21,500 |
| +21,600 | Slave command 8; done at +25,300 |
| +25,800 | Slave command 4 (PWM voices); done +26,000 |
| +32,250 | Master (`0x71C4`) sends Slave command 2 (sort), Slave initialises ring A and the buckets; Master loads overlay A and runs the transform loop (`0x969C`: 36 calls of overlay A per picture, about 126,000 instructions) posting ring A slots |
| +55,600 | 68000: `$A15100 := $8083` (**FM := 1**) |
| +94,300 | Slave command 2 done |
| +95,700 | Master sends Slave command 1; loads overlay B and walks the buckets building ring B records (about 64,000 instructions) |
| +98,300 to +190,700 | Slave draws; **about 1,840 auto fills** (5,500 VDP register writes), about 3,500 FB byte writes and 1,500 word writes per picture |
| +190,700 | Slave command 1 done |
| +197,600 | Master writes the frame-buffer status block, `0x2000402E := 0`, `0x20004020 := 0` (**picture done**) |
| +198,100 | 68000: `$A15100 := $0083` (**FM := 0**), then `$A1518B` toggles **FS** |
| +255,974 | Next go |

Over 1,471 consecutive attract pictures: go to FM-take-back 1.17-1.82 frames (median 1.38), go to FM := 1 0.35-0.57 frames, FM := 1 to FM := 0 0.71-1.48 frames (median 0.94) [run, plain run]. The two SH-2s are therefore busy about 70% of the 2-frame window; the interpreter run showed the same order of events but about 1.6 times longer (3-frame period), so any timing taken from an interpreter run is distorted.

## 4. The renderer

### 4.1 Division of work per picture

| CPU | Work | Instructions per picture (interpreter run, fight, picture of 3 frames) [run] |
|-----|------|------------------------------------------------------------|
| 68000 | pads, HUD, sound requests, 240 background auto fills, FM/FS | not counted here |
| Master | game logic for fighter A (the same chain as the Slave's for B), collision half, pose matrices, overlay A transform loop, overlay B edge chains, frame-buffer status block | about 126,000 in overlay A, 64,000 in overlay B, 60,000-100,000 in logic and matrices |
| Slave | game logic for fighter B, collision half, bucket sort, rasteriser and fills, PWM (about 11,000 interrupts a second) | about 100,000 in the sort wait/work, 260,000 in command 1 (includes polling the VDP for FEN, about 34,000 byte reads per picture) |

The spin-wait counts depend on the run mode; only the work routines are comparable.

### 4.2 Stage 1: overlay A, transform, cull, clip, project, light (Master)

Called from `0x06007364` for each enabled body part of a fighter (20-byte descriptors at object `+0x20BC`, 48-byte pose blocks at `+0xF80`; 16 parts per fighter, 34-36 calls per picture for both); `r13` points to the part's polygon stream (in SDRAM: the models are unpacked from the cartridge at scene load, see below), `r14 = 0xC0000700` (state block), `r5` the pose block. Reading of the code at `0x73B4`-`0x7947` [ROM]:

- **State block** (`0xC0000700`, initialised from `0x7268`): `+4 = 0x256` (focal constant, 598), `+8 = 0x10000` (near plane, 1.0), `+12 = 0x400000` (far limit, 64.0), `+20` = pointer to the pose decoder (`0x74E0` or `0x7514`), `+24 = 0x06038020` (vertex scratch), `+28 = 0x0603C000` (ring A write pointer), `+32 = 0x0603D000` (polygon record pointer), `+36 = 0x0603FFF8` (limit), `+40 = 0x060368D0` (bucket table), `+44` (node free pointer).
- **Pose decode** (`0x74E0`): three 32-bit fixed-point matrix rows from the pose block, each `>> 8`, stored as halfwords; a variant at `0x7514` scales them by 3/4 (`x*3 >> 2`) and is chosen when bit 0 of the option halfword `0x06020292` is set (`0x071D2`-`0x071DC`; the byte comes from immediate command 12).
- **Vertex loop** (`0x7458`): vertices are three signed halfwords `(x, y, z)` from the stream; `mac.w` against three halfword matrix rows gives view-space `z'`, then `x'`, `y'`. Whole-part rejection: `z' >= 0x400000` or `|x'|, |y'| >= 0x36CBC5` (any vertex) returns with T clear and the part is skipped. Perspective uses the **hardware divider**: `DVSR (0xFFFFFF00) := z'`, `DVDNTH := 0x256`, `DVDNTL := 0` (64/32 divide started early, overlapped with the next `mac.w` sequence), the quotient read from **`0xFFFFFF1C`**, then `dmuls.l` with `x'` and `y'` and the high word (`mach`) stored as the screen coordinates. Each vertex becomes a 16-byte record at `[r14+24]`: `x'`, `y'`, `z'` (longs), screen x, screen y (halfwords at `+12`, `+14`). Division: hardware for projection and clipping; software `div1` (32 steps unrolled, `0x1A358`) elsewhere (motion decoding).
- **Light vector**: the part's orientation applied to a light direction with three `mac.w` (`0x73C4`), stored at `0xC0000746`-`0xC000074A` for the shading routine.
- **Polygon loop** (`0x73EA`): per polygon a flag halfword (`r9`), a colour halfword and 1-4 vertex indices (byte offsets into the vertex scratch, 16 per vertex). Bits 11-9 of the flag select a **vertex-sharing variant** by a `bsrf` through a table of offsets at `0x7420`: 0 = four new indices, 1 = keep the first, take the old fourth as the second, 2 = take the old fourth and third as the first two (an edge shared with the previous polygon), 3 = take the old third as the first, 4 and 5 = no change, **6 (flag `0x0C00`) = end of the part** (the table entry jumps to the routine's exit). Colour-word bit 0 = triangle (only three indices follow). Flag bit 4 (`0x10`) = **back-face test** on (`0x7664`: sign of a 2-D cross product with `muls.w`), bit 5 (`0x20`) = a normal vector of three halfwords follows the indices (lighting on), bits 3-1 = **depth-key mode** (average of three or four, maximum or minimum `z`, jump table at `0x769C`). The only other exit is a full output buffer (`r11 >= [r14+36]`).
- **Near-plane clipping per polygon** (`0x7538`/`0x7598`): the four (three) vertex `z` values are compared with the near plane and a 4-bit outcode picks one of 15 hand-written clip cases (tables at `0x7578`/`0x75D0`, code `0x7720`-`0x78BF`); new vertices come from `0x78C0`, which interpolates along the edge with the divider and `dmuls.l`/`xtrct`.
- **Light**: `0x7918` takes three `mac.w` products of the normal against the light vector, `>> 16`, clamps to `[-7, 8]` and adds `shade << 8` to the colour word. The polygon's colour index in the high byte of the word is therefore **base index + light level**; the palette is built to match (ramps of 16 entries).
- **Counts** [run, picture at frame 2000, interpreter run]: about 640 polygons submitted (two fighters), **332 ring A posts per picture** after back-face culling and clipping, about 273 ring B records after the viewport clip.
- **Output**: a 20-byte record at `[r14+32]` (flags/colour long with bit 0 = triangle, then four `(x, y)` halfword pairs) and a **ring A slot**: wait until the slot's status has bit 3 (free), write the depth key (long) at `+4`, the record pointer at `+8`, status 4 at `+0`, advance 16 with `and 0xFFFFCFFF`. The depth key is a long such as `0x00043507`; the sorter takes `key >> 13` as the bucket.
- **End of the picture's list**: after the last part, `0x7348` waits for the next ring A slot to be free and writes status 6 (end marker).
- **Model format** [ROM, run: dump of `0x060367D0` and `0x06033B2E`]: `halfword N` (vertex count), a second halfword (equal to N in the examples; skipped by the code), `N` vertices of three signed halfwords, then the polygon list: `flags, colour, indices...` per polygon, ending with `0x0C00`. The arena part at `0x060367D0` is `0008 0008`, eight vertices of an octagon at y = 0 (x or z of +-55, +-135), then three polygons `0010 0502 0030 0040 0050 0000`, `0210 0502 0010 0020`, `0410 0502 0060 0070` and `0C00`: colour index 5, mode bit 1 set (floor drawn through the overwrite image). A fighter part such as `0x06033B2E` has 39 vertices and 43 polygons. Parsed with `modelparse.py` from a dump at frame 2000, one fighter's list is 16 parts: the ground plate (`0x060367D0`, the same arena octagon in both fighters' lists) and 15 body parts with 347 vertices and 322 polygons (38 triangles) in all, the largest a 88-vertex, 74-polygon part. Polygon colour words use high bytes `0x17`, `0x27`, `0x37`, `0x47`, `0x57`, `0x67`, `0x77` (the middle entry of seven 16-entry light ramps at palette indices `0x10`-`0x7F`; the second fighter's records show `0x8x`-`0x9x`), flag low byte `0x30` (cull + normal present) or `0x31`-`0x34`; **only the ground plate has colour-word bit 1 set** (`0x0502`), every fighter polygon uses the VDP fill path.

The pose matrices themselves are computed before the overlay is loaded: `0x98A4` (twice, once per fighter) runs 15 rounds of `0x19344`/`0x193AC`/`0x192FC`/`0x19394` on the **matrix stack** (16.16 matrices, `mac.l` or `dmuls.l` with `xtrct`): one round per joint of the skeleton (15 joints), from the joint angles at object `+0xFB0` (the angle/translation values come from decoded motion data). Fixed-point formats: pose matrices 16.16 (long), engine matrices 8.8 (halfword), model vertices 16-bit integers, screen coordinates 16-bit integers, `1/z` in 0.32 times 598. [ROM; the interpretation of the angle format is [inf]]

### 4.3 Stage 2: the sort (Slave command 2)

`0x729A`: loop over ring A. For a ready slot (status bit 2): purge the slot's cache line (`0x40000000 | ptr` write), call the stub at `0xC0000000` (image `0x730C`), write status 8, step 16 with wrap. The stub takes `key = [slot+4]`, `ptr = [slot+8]`, computes the bucket offset `(key >> 13) * 2` into the halfword table at `[r14+40]`, walks the bucket's list (nodes of 8 bytes: next halfword, 13-bit key halfword, pointer long, allocated at `[r14+44]`) and inserts the node in **descending key order** (larger `z` first). 512 buckets of 13-bit keys: the far limit `0x400000` of stage 1 is 2^22, so the 22-bit depth range is covered exactly [ROM]. The end marker (status bit 1) makes it write `0xAC00` to the slot and finish. The Master is the producer; the Slave spends most of the command waiting for the Master (the loop at `0x72AA`-`0x72F2` polls the slot through `0x20000000 | ptr`, delay 16 iterations). The command lasts about as long as the Master's stage-1 work (about 62,000 cycles) [run].

### 4.4 Stage 3: edge chains (Master, overlay B)

Before it, `0x19424` (called after the Master has waited for the sort to finish) loads seven parameters into the Master's second state block at `0xC0000688`: `+8 = 0xA0`, `+12 = 0x80` (screen centre 160, 128), `+16 = 0`, `+20 = 0x13F` (x range 0-319), `+24 = 0`, `+28 = 0xDF` (y range 0-223), `+32 = 0x06038000` (ring B); sets the status of all 256 ring B records to 8 (free); and **purges 372 cache lines** (writes to `0x460368D0`, `+16`, ... : the associative-purge alias of the bucket table and node pool) so that the Master reads the lists the Slave just wrote. `0x194A8` then copies overlay B (`0x194E0`), sends Slave command 1, runs the overlay function at `0xC0000022` (image `0x1951E`), posts the end marker (status 6, after waiting for a free slot, `0x1954E`), waits for the Slave and for the VDP (`0x7C4`). The overlay walks the bucket table **from the last bucket down** (offset `0x400`, step -2: far to near, **painter's algorithm**), for each polygon builds two **y-monotone chains** of `(x, y)` halfword pairs (left and right edges) clipped to the rectangle, and posts them into **ring B**:

| Offset in the 64-byte record | Contents |
|------------------------------|----------|
| `+0`..`+27` | Chain 1: up to 7 points `(x, y)`, halfwords; terminated by a negative `y` (`ffff ffff`) |
| `+28` | Status halfword: 4 = ready, 6 = ready + end of list, 8 = free (written by the Slave) |
| `+30` | Colour halfword: **high byte = palette index** (base + light), bit 1 = write through the overwrite image with the CPU instead of the VDP fill |
| `+32`..`+59` | Chain 2, same format |

Example at frame 2000 (record 0, `0x06038000`): chain 1 `(0x55,0xBC) (0x00,0xBC) (0x00,0xC3) (0x46,0xC4)`, chain 2 `(0x55,0xBC) (0x46,0xC4)`, status 8, colour `0x0300`: a quad clipped at x = 0. The Master waits for each record's status to read 8 through `0x20000000 | ptr`. [ROM, run]

### 4.5 Stage 4: rasteriser and fill (Slave command 1)

Overlay C (`0x79EC`) takes two chains (`r8` at `+0`, `r9` at `+32`), computes for each segment `dx * recip[dy]` with `muls.w` from a **16-bit reciprocal table at cart `0x2212570C`** (the Slave's most-read cartridge block: about 330,000 reads in 900 frames), steps both edges in 16.16 per scanline and calls the span routine in `r14`:

- `0x7AE0` (flag bit 1 clear): converts the 16.16 span ends to word addresses, issues one **auto fill** (GBR = `0x20004100`: length `+4`, start `+6`, data `+8`, after waiting for FEN, bit 1 of the byte at `+0x0B`) when the word count is above a small limit (the code compares it with 2; one of four start/length parity cases is taken first), and writes the odd leading/trailing pixel and the short spans with CPU byte/word stores to the frame buffer at `0x24002000 + y*0x200`. Fill data is the colour index duplicated into both bytes.
- `0x7BE8` (flag bit 1 set): CPU stores only, into the **overwrite image** at `0x24022000 + y*0x200` (zero pixels are skipped by the hardware).

Frame buffer: `A15180` mode 1 (packed pixel, **PRI = 0**), 256-word line pitch, line table written once by the 68000 (448 word stores: both buffers), line *y* at word `0x1000 + 0x100*y` for `y = 0..239`. Palette (read at frame 2000): index 0 `$0000` **without** the through bit, 246 of 256 entries with bit 15 set (indices 1-6 the floor greys, 7-14 `$0000` without the bit, 15-25 black with the bit, light ramps above): the fighters are drawn with through bits over the Mega Drive picture, as in Mortal Kombat II ([`src/32x/compositing.md`](../../../src/32x/compositing.md)); the SH-2s never write the palette (no reference to `0x20004200` in the image). [ROM, run]

### 4.6 Double buffering and the picture-complete signal

FS is written only by the 68000 (`$A1518B`); the SH-2 image has no reference to the FS register. Sequence per picture (3.5): the 68000 owns the VDP (FM = 0) while it clears the back buffer, hands it over with `$A15100 := $8083`, the Slave and the Master draw, the Master clears `COMM0` high byte, the 68000 takes FM back and flips FS at once. The 68000 also reads back the 16-byte status block the Master left at frame-buffer word `0x100`. Immediate commands 3-7 take FM themselves (`0x00004000 := 0x80`) around image blits. [ROM, run]

### 4.7 Other drawing code

- **Image decompression** (`0x19F64`): an LZ scheme with a bit-flag byte stream (literal bit 1, then match with a 13-bit offset and a short or long length), used by immediate commands 3-5 for 71,680-byte and 25,600-byte pictures in cart `$170000` and above. [ROM]
- **Run-length sprites** (`0x19F3A`, driven by the list at `0x060202A0` from `0x19F00`): (count, colour) byte pairs per line, zero-colour runs skipped, 112-byte-wide strips at a stride of `0x200`: writes to the overwrite image, about 970 byte stores per picture from the Master. [ROM, run] role [inf]
- **Tile hit masks** (`0x1E48C`): bit-field arithmetic in on-chip RAM, part of collision, not drawing. [ROM]

## 5. Memory placement and cache

- **CCR** `0x09` on both CPUs (2.2), set once at start-up; the Slave and the Master never change it again except for the whole-cache purge `0x756` after the cross-CPU phases (the call sites load its address from literal-pool entries at `0x2430`, `0x24C0`, `0x2520`, `0x644C`, `0x64B0`: Master task `0x2370`, Slave commands 5, 6 and 8, Master task `0x63F0`).
- **Cached (default)**: all code and variables in SDRAM `0x06...`, and 14 sites that read cartridge tables through the cached window `0x02000000` (e.g. `0x3E9A`, `0x6B30`, `0x105B6`).
- **Cache-through reads**: flags written by the other CPU (`0x20000000 | ptr`: ring statuses and 71 literal sites in all, most in the game code for fields of the two fighter objects), the command byte `0x20004005`, all cart tables (`0x22xxxxxx`: 210 literals), PWM samples, frame buffer (`0x24xxxxxx`).
- **Associative purge** (`0x40000000 | addr`, 36 literal sites): Slave command 1 purges the four lines of each ring B record, command 2 one line per ring A slot, then reads the record cached; the same idiom appears in the shared-state game code at `0x134C`-`0x4132`, `0xA5C4`-`0xE960`, `0x1066A`-`0x18BFC`.
- **On-chip RAM code**: overlays A-D and the PWM handler (1.3). The **only** executed code addresses in 5,500 frames are `0x06xxxxxx` and `0xC00000xx`.
- **Why**: the design gives each CPU a private copy of its hot routine in 2 KB of single-cycle RAM while the shared SDRAM is accessed through the cache with explicit invalidation at every producer/consumer boundary. [inf]
- **Cartridge reads** [run, SH-2 reads per 4 KB block over nine 100-frame attract windows, interpreter run]: Slave `0x125000` (the reciprocal table) 331,000, `0x12A000` 102,000, `0x13B000` 28,000, `0x123000` 26,000, PCM blocks `0x1C7000` 34,000, `0x1CF000` 26,000, `0x1D7000` 19,000, `0x1D2000` 16,000, sample descriptors `0x188000`-`0x18B000` about 4,700; Master `0x12A000` 103,000, `0x123000` 31,000, `0x13B000` 24,000, `0x125000` 15,000, `0x150000`-`0x156000` about 25,000 (motion data), `0x295000` 10,700, `0x2C7000` 6,900. Nothing is executed from the cartridge.

## 6. Sound on the SH-2 side

Slave only. Start-up (`0x85CC`): zero the eight halfwords at `0x06008774`, copy the 96-byte handler to `0xC00005F0` and write that address into the Slave's PWM vector (`0x0600018C`), initialise three voices, `0x20004030 := 0x0205`, `0x20004032 := 0x0417` (cycle 1047, so a 21.98 kHz PWM and, with the interval field 2, an interrupt about every 2,090 SH-2 clocks, **11 kHz**; measured 697 68000 cycles apart [run]), INTM bit 0 := 1. [ROM, run] Because the handler writes one mono value per interrupt, that is every second PWM period, the FIFO runs empty in between and the hardware repeats the last width ([`src/32x/pwm.md`](../../../src/32x/pwm.md), manual): the output is an 11 kHz sample-and-hold.

- **Voice** (16 bytes at `0xC0000650`, `0x660`, `0x670`): `+0` data pointer, `+4` remaining count, `+8` a 32-bit **rate pattern** rotated right once per interrupt (the carry becomes the pointer increment), `+12` the last sample, `+14` the sound id (0 = free).
- **Interrupt**: for each voice, if the count is 0 keep the last sample and mark free, else decrement, rotate the pattern, read the byte at the pointer (unsigned 8-bit PCM), advance by the carry; the three samples are summed (0..765, inside the cycle of 1047) and written to **`0x20004038`** (PWM mono, both channels). With pattern `0xFFFFFFFF` a voice plays at 11 kHz, with `0xAAAAAAAA` at 5.5 kHz.
- **Starting a voice** (`0x86C8`, from the list at `0x06008774`): the descriptor is at cart `0x22188000 + 16*id`-ish (`+0` offset to the data from `0x22188000`, `+4` length, `+8` priority byte, `+14` flag: `0x0800` = full rate and length as is, anything else = half rate and double length); a free voice is taken, or the lowest-priority voice is replaced if the new priority is higher. Samples are read from the cartridge at `0x22188000 + offset` (PCM at `$1C6000`-`$1DB000`: the Slave's most-read blocks `0x1C7000`, `0x1CF000`, `0x1D7000`).
- **Who asks**: the 68000's sound driver (Sega's, in 68000 RAM; FM and PSG are 68000-written) forwards **two bytes per picture** to the Master (immediate command 8; command 2 in menus); the Master appends them to the list (`0x8750`: byte count at `0x06008774`, at most 7 halfwords at `0x06008776`) and the task `0x06018CF4` (or command 2) sends Slave command 4. The 68000 never writes the PWM registers [M68K, ROM].

## 7. Comparison with Virtua Racing Deluxe

VRD column: retail ROM MD5 `72b1ad0f...`, SH-2 image at cartridge `$020000`, `$C000` bytes, read by a second reader with the same instrumented core (evidence tags as above; I re-read only `0x060039F0`-`0x06003A4C` and `0x060045CC`, which match what is said here). Addresses are VRD's. "Same" = same instructions or nearly; "same shape" = same steps, different details; "different" = different design.

| Construct | Virtua Fighter | Virtua Racing Deluxe | Verdict |
|-----------|----------------|----------------------|---------|
| Entry | Trampoline `stc vbr,r0; mov.l @r0+,r1; jmp @r1; mov.l @r0+,r15`, both CPUs at `0x1A0` | Trampolines at `0x280`/`0x288` that load the table address from a literal and jump through its reset PC | Same idea, different code |
| Vector tables | Master `0x06000000`, Slave `0x06000080` (overlaid), level table in vectors 16-31, stubs `bra self` | Master `0x06000000`, Slave `0x06000140`; error vectors to stubs that push r0-r14, store a 4-char code (`INST`, `SLOT`, `CPUA`, `DMAA`, `NMI`, `UBRK`, `TRAP`, `IRL`, `RSRV`) to `0x20004028`/`0x2000402C` and spin | Same idea (code stubs), different: VF's equivalent stubs are dead code that cannot post |
| Dispatcher | Master only: mask `0xF0`, TOCR := 0 and read back, level table at VBR+0x40 (revised sample, MK2 style). Slave: none | One per CPU, `jsr @r1` through a 16-long table by SR mask; **no** TOCR write, no mask change; only CMD and VRES mapped, others hang | Different (VF follows the revised sample; VRD only has the sample's table shape) |
| TOCR | 0 in the dispatcher, 2 in the CMD handler | Sega's FRT sequence, last value `0xE2`, never touched again | Different |
| Interrupts enabled | Master CMD; Slave CMD (unused) and **PWM** | CMD on both, nothing else; PWM, V, H unused; CMD is a restart | Different |
| CMD use | Real command path: immediate commands inside the handler, deferred ones through a mailbox | Only restarts the CPU (hot start) | Different |
| 68000 to Master | Byte `0x20004021` + CMD interrupt; busy flag `0x20004020` | Polled: flag byte `0x20004020` (written last), command byte `0x20004021`, 64-entry `jsr` table at `0x780`, no delay | Same registers and flag convention, different trigger and loop |
| Master main loop | Mailbox poll, SP-balance check, post routine with task list | Tight poll of the flag byte | Different |
| Master to Slave | Command 1-8 in the **H-count byte** `0x20004005` | Command in COMM2 high byte `0x20004024`, written only by the Master | Same pattern (Master-only writes, Slave zeroes when done, Master waits for 0), different register |
| Slave loop | 16-entry table at `0x304`, idle `mov #64,r7; nop; dt r7; bf` | 16-entry table at `0x5C8`, the same idle loop | **Same** idle delay, same table size |
| Completion to the 68000 | Master clears `0x20004020` and writes status bytes `0x2000402E/F` | Master clears `0x20004020`, sets bit 0 of `0x20004023` (after waiting for FEN = 0) | Same shape |
| Data to the SH-2s | Pads, option and sound bytes in COMM; no FIFO, no SH-2 DMA | 2,560-byte scene description per picture through the DREQ FIFO into `0x0600C000` by SH-2 DMA channel 0 (`CHCR0 = 0x44E1`) | Different |
| Who runs the game | SH-2s (fighter FSM, pads, collision) | 68000 | Different |
| Transform / cull / light | Master only (overlay A, 1,428 B); the Slave runs the other fighter's logic | **Both** CPUs load one 1,748-byte overlay and each transforms half the scene | Different split, same technique (on-chip overlay, `mac`, hardware divider) |
| Perspective divide | `DVSR`/`DVDNTH`/`DVDNTL`, quotient from `0xFFFFFF1C` | Same, no software divide | **Same** |
| Depth ordering | 512 buckets by `key >> 13`, a **separate Slave stage** over ring A, nodes sorted inside a bucket | Bucket index about `z >> 12`, 8 slots per CPU per bucket, inserted inside the transform overlay | Same technique, different placement; both are painter's algorithms, **no 68000 sort** |
| Polygon stage | Master overlay B (1,280 B): bucket walk far to near, clip to the viewport, edge chains | Master overlay B (1,608 B): same job | Same |
| Ring to the rasteriser | 256 x 64 B at `0x06038000`, flags at `+28` (8 free, 4 ready, 6 end), chains at `+0` and `+32`, colour word at `+30`, wrap `and 0xFFFFBFFF`, end marker `0xAB00` | 256 x 64 B at `0x06018000`, same fields, same constants | **Same** |
| Rasteriser | Slave overlay (560 B): reciprocal table, VDP auto fill for spans, CPU stores for edges, overwrite-image path by colour bit 1 | Slave overlay (580 B): same design, 2.14 reciprocal table | **Same** |
| Cache | `CCR = 0x09` both CPUs; purge-then-read of ring records; whole-cache purge after cross-CPU phases | `CCR = 0x09` both; purge routine `0x10`, 8 `nop`s, `0x09` twice per picture per CPU; purge-then-read of ring records | **Same** (one more purge site in VF: `0x756` through `0xFFFFFE93`) |
| On-chip RAM | Overlays reloaded per phase at `0xC0000000`, variable block at `0xC0000700` | Overlays reloaded per phase, variable block at `0xC0000700-7FF` | **Same** layout idea |
| Frame buffer | Packed pixel, 256-word pitch, line *y* at word `0x1000 + 0x100*y` (240 entries), through bits on 246 entries, index 0 = `$0000` | Packed pixel, 256-word pitch, line *n* at word `0x2000 + 0x100*n` (224), through bits on every used entry, index 1 = `$8000` | Same shape, different base |
| Clearing the back buffer | 68000, 240 auto fills per picture | Master and Slave auto fills (lines 16-115 and 116-179, rest inline) | Different |
| Frame flip | 68000 flips FS after FM is returned; SH-2s never write FS | 68000 flips FS in its vblank handler; SH-2 flip routines are dead code | Same convention |
| Picture rate | 2 frames per picture in attract (30 pictures/s) [run] | A multiple of 3 vblanks: 20, 15, 12, 10 pictures/s measured | Different |
| PWM | Slave interrupt mixer, 3 voices, 8-bit, 11 kHz | One blocking polled player on the Master (power-on chime), none in play | Different |
| VRES | Clears via `0x4014`, restarts at the manual-reset vector, no RV test | Reads byte `0x20004006`, posts `VRES` in COMM12, DMA off, `CHCR0 := 0x44E0`; Slave reads through r1 | Different |
| Stacks / memory | SP `0xC0000800` on both; SDRAM `0x06021000`-`0x06029CA6` cleared at boot | SP `0x0600FF80` / `0x06010000`; SDRAM `0x0600C000`-`0x0603FFFF` cleared at every restart | Different |
| Models | Unpacked from the cartridge into SDRAM at scene load; matrices from per-joint chains | Model blocks copied by CPU loops (10-16 KB + 35 KB); matrices from Euler angles and a 4096-entry 2.14 sine table | Different |

**What the VF code says about the claims in the book (`src/patterns/case-study-vr.md`, `cpu-split.md`, `vdp.md`, `compositing.md`) and the VRD project's account**, with the VRD reader's verdicts where VF cannot speak:

| Claim | Verdict |
|-------|---------|
| The Master's command loop and the 16-entry table at `0x06000780` | The table is 64 entries with 23 distinct handlers (VRD reader); VF has a table of 14 for the deferred commands and 17 immediate ones, so both are larger than 16 |
| The Slave loop with a 16-entry table at `0x060005C8` and a 64-pass delay between polls | Confirmed (VRD reader); VF has the same table size and the identical delay loop |
| "The Slave renders everything" / "the Master transforms" (discrepancy 28) | Both contradicted for VRD: transform on both, polygon stage on the Master, raster on the Slave (VRD reader). VF has the same back end and a different front end, which supports reading VRD as a pipeline like Star Wars Arcade's |
| "The 68000 sorts" | Contradicted for polygons in VRD; VF also has no 68000 sort |
| 14 block copies and 21 pixel jobs per picture, three waits per command | Not seen in VRD (one command per picture, the Slave's commands come from the Master); VF is the same: one picture command, Slave commands posted by the Master |
| "About 20 pictures per second, one per three vblanks" | VRD: 20 only when the picture fits, 15/12/10 measured; VF: 30 in the same emulator |
| The 68000 flips FS only after the SH-2 flagged completion | Confirmed in both |
| Palette entry 1 `$8000` and through bits (compositing) | Confirmed in VRD; VF uses entry 0 without and 246 entries with the bit |
| 56 KB bulk copy of track data | Not confirmed: VRD cmd 3 copies 10-16 KB plus 35 KB with CPU loops (VRD reader). VF cannot speak |
| Line table "line *n* at word `256 * (n + 1)`" (`vdp.md`) | VRD uses `0x2000 + 0x100*n`, VF `0x1000 + 0x100*n`; only the 256-word pitch is general |

## 8. Open questions and things suspected but not shown

**Not traced at all**
- Deferred commands 0x83 (partly read), 0x88-0x8D and immediate commands 10, 11, 13-16 were read but not run (the attract mode never sends them); their roles in 3.2/3.3 are inferences from the data they touch. What the sixteen `game_state` values of the interactive handler table at `0x0D54` mean, and what the five attract phases (`0x663C`...`0x68BC`) do, is not worked out.
- The fighter state machine (`COM_*`/`ACT_*`, table at `0x5DC0`, handlers in `0x2800`-`0x5200`), the move-number logic of `0x9B80`-`0xE000`, hit resolution and the camera were located but not read.
- Formats not decoded: the **motion data** (cart `0x14C000`-`0x156000`: signed delta bytes; `0x1A808` builds 43 channels per frame, which looks like 15 joints x 3 angles minus fixed ones, inference), the model **packer** (input at cart `0x22144000`, unpacker `0x19D5C`/`0x19DDA`), the run-length sprite format, the bit layout of the LZ-type picture compression at `0x19F64` (the 68000 side decodes the same family, `M68K.md`), the collision pair tables at `0x1C5D0`.
- What triggers the model unpack (it was seen writing `0x06030000`-`0x060368FF` in the window of frames 900-1,000, the first fight of the attract mode).
- The 16-bit table at `0x1C300` (about 39 steps; an arc tangent or square-root table is a guess).

**Two readings, and what would decide**
- *Why the Master builds the edge chains and the Slave only draws.* The code shows it plainly; the reason is inference (the Slave is the longer path in the fill phase, so giving the Master the geometry work that can run beside it balances the pipeline). A per-CPU busy trace on a console would decide; PicoDrive's numbers cannot, because it charges no bus contention.
- *The dummy write of `0x34` to `0x06000034` before every command byte and before every `0x20004021` clear.* It writes to a cached SDRAM address, so it forces the earlier store through the one-entry write buffer; the intent looks like a write barrier between data written to SDRAM and the command byte that announces it. Inference; only a console can show it matters.
- *Colour-word bit 1 selects the CPU/overwrite span path.* In the 16 parsed parts only the ground plate sets it, so it may mean "ground" rather than a speed choice; whether the path is needed for correctness (overwrite skips zero pixels) is unknown.
- *Command 0x85 versus 0x86 versus 0x84.* The 68000 sends 0x86 (attract) and 0x84 (play) per picture [M68K]; the SH-2 side shows 0x86's handler walking five phases and 0x84's walking sixteen states, but whether 0x86 is the demo-only path is inference.

**Things the SH-2 code suggests but I could not show**
- The Slave enables its CMD interrupt although its vector is a register dump: probably a leftover of Sega's start-up code; nobody raises INTS in 5,700 frames, but whether another scene does is not known.
- The 18 error stubs, the seven stubs at `0x650`-`0x6EB`, `JUDGE ERROR` and the move-name strings look like the remains of a debug build; none is reachable.
- Time and bus effects on a console: PicoDrive charges no SH-2 wait states and no bus contention, but the Slave polls `0x20004005`, ring statuses and the VDP's FEN flag through cache-through reads (about 34,000 FEN reads per picture in a fight) and reads PCM and the reciprocal table from the cartridge, all of which take bus cycles the Master also needs. The 2-frame picture rate seen here (1.17-1.82 frames of work) may not survive that.
- The PWM write of a sum that can be 0 (maximum output, since a pulse width of 0 is the maximum) if all three voices are at 8-bit value 0: not seen, not checked.
- Whether the `0xFFFFFF1C` read of the divider (undocumented mirror) is the only way the engine reads its quotient on hardware: it is used at every hardware divide in the image (14 of 22 divider sites touch `+0x18` or `+0x1C`, `divuscan.py`).

## Appendix A: routines

Addresses are SH-2 addresses in the image. Sizes are read from the code where the routine's end was seen and marked `~` where they come from the gap to the next entry. Confidence: **H** read and seen running, **M** read, partly traced or run only in one scene, **L** inferred.

| Address | Size | CPU | Role | Conf |
|---------|------|-----|------|------|
| `0x000`-`0x0FF`, `0x100`-`0x11F` | 288 | M | Vector table, IRL vectors to `0x120`; slots 16-31 are the level table | H |
| `0x080`-`0x0FF`, `0x180`-`0x19F` | 160 | S | Slave vector table (overlaid), IRL vectors | H |
| `0x120` | 48 | M | Interrupt dispatcher (mask, TOCR := 0, level table) | H |
| `0x150` | 20 | M, S | VRES: clear through `0x4014`, reload SP, rewrite PC/SR, `rte` | H (run: a core reset at frame 1200 shows both CPUs writing the clear register, then re-posting `M_OK`/`S_OK`) |
| `0x1A0` | 16 | M, S | Entry trampoline through the vector table | H |
| `0x1C0`-`0x253` | 148 | M | Start-up: INTM := 0, `M_OK`, CCR, FRT, clear interrupt registers, wait for COMM0/1 = 0, INTM |= 2, clear SDRAM, SP, SR, main loop | H |
| `0x254` | 24 | M | Zero `0x06021000`-`0x06029CA6` | H |
| `0x26C`-`0x2E3` | 120 | S | Start-up: INTM := 0, `S_OK`, CCR, FRT, `0x20004005 := 0`, PWM init (`0x85CC`), INTM |= 2, main loop `0x2D2` | H |
| `0x344` | 12 | S | Idle delay (64 passes) | H |
| `0x350` | 60 | S | CMD vector: register dump and spin | M (never entered) |
| `0x38C`-`0x497` | 268 | - | 18 unreferenced error stubs | H (dead) |
| `0x498` | 144 | M | CMD handler (immediate and deferred) | H |
| `0x528` | 80 | M | Main loop: mailbox, table, SP check | H |
| `0x578` | 46 | M | Immediate 9: cold start | H |
| `0x64C` | 4 | M | Null command | H |
| `0x650`-`0x6EB` | 156 | - | Seven unreferenced stubs | M |
| `0x70C` | 24 | M | `send_slave_cmd`: wait for `0x20004005 == 0`, store r1 | H |
| `0x724` | 20 | S | `slave_ack`: dummy write, `0x20004005 := 0` | H |
| `0x738`, `0x770` | 30, 48 | both | CCR 0x10 then 0x09; tag clear | H |
| `0x756` | 24 | both | Whole-cache purge through `0xFFFFFE93` | H |
| `0x7A0` | 36 | M | `wait_slave_idle` | H |
| `0x7C4` | 12 | M | Wait for the VDP fill to end | H |
| `0x7D4`, `0x83C` | 64, ~50 | M | Variable and table initialisation | M |
| `0x900`-`0x992` | 148 | M | Post-command routine (matrix reset, Slave cmd 7, task list, done flag) | H |
| `0x9C4`, `0x8318`, `0x8350`, `0x838C`, `0x83C8`, `0x8404`, `0x8454`, `0x82F4`, `0x8784`, `0x8818`, `0x69A8`, `0x6D1E`, `0x99C`, `0x9A8` | | M | Immediate commands 1-8, 10-13, 15, 16 (3.2) | H/M |
| `0x0A28`, `0x0B7C`, `0x0C70`, `0x652C`, `0x65D8`, `0x7C1C`, `0x7C90`, `0x7FB4`, `0x7FE8`, `0x6E68`, `0x6F40` | | M | Deferred commands (3.3) | H (0x86, 0x85), M, L |
| `0x2048`, `0x222C` | 484, 276 | M | Enable / disable the task list entries | M |
| `0x2370` | 216 | M | Per-picture fighter A chain with Slave commands 5 and 6 | H |
| `0x2448`, `0x24C8` | 128, 96 | S | Slave commands 5 and 6 (fighter B chains) | H |
| `0x2528` | 176 | M | Per-object task (state step, motion) | M |
| `0x2800`-`0x5200` | ~10 KB | M, S | Fighter `COM_*`/`ACT_*` state handlers (table at `0x5DC0`) | M |
| `0x63F0` | 96 | M | Task: Slave command 8 plus fighter A pose/position | H |
| `0x6450` | 104 | S | Slave command 8 | H |
| `0x6E4C` | 18 | S | Slave command 7 | H |
| `0x71C4` | 80 | M | Ring A set-up: send Slave command 2, init the state block | H |
| `0x7214`, `0x724E` | 58, 76 | S, M | Ring A / bucket initialisation, state block copy | H |
| `0x729A` | 90 | S | Slave command 2 (ring A consumer, sort) | H |
| `0x72F4`, `0x730C` | 84, 60 | S | Copy and body of the 60-byte insertion stub (overlay D) | H |
| `0x7348` | 28 | M | Post the end marker (status 6) to ring A | H |
| `0x7364` | 52 | M | Loop over body parts: call overlay A | H |
| `0x7398` | ~28 | M | Copy overlay A to on-chip RAM | H |
| `0x73B4`-`0x7947` | 1,428 | M | Overlay A body | H |
| `0x7458` | 136 | M (ovl A) | Vertex transform, cull, project | H |
| `0x7538`, `0x7598`, `0x75E0`, `0x7664`, `0x7688`, `0x76D6`, `0x76FC` | | M (ovl A) | Quad / triangle clip dispatch, fast path, back-face test, depth key, ring A post | H |
| `0x78C0`, `0x7918` | 136, 48 | M (ovl A) | Edge clip interpolation, shading | H |
| `0x7948` | 136 | S | Slave command 1 (ring B consumer) | H |
| `0x79D0`, `0x79EC`-`0x7C1B` | 24, 560 | S | Copy and body of overlay C (rasteriser) | H |
| `0x7AE0`, `0x7BE8` | ~264, ~100 | S (ovl C) | Span routines: VDP fill, CPU stores | H |
| `0x84FC` | 90 | S | Slave command 3 (collision) | H |
| `0x8674`, `0x86C8` | 54, ~130 | S | Slave command 4, voice start | H |
| `0x856C`, `0x85A4`, `0x85CC` | 56, 40, 126 | S | PWM interrupt, voice step, PWM init | H |
| `0x8750` | 28 | M | Enqueue a sound id | H |
| `0x8840` | ~60 | M | Build the task list from a spec table (`0x8888`) | M |
| `0x8B04` | ~190 | M, S | Fighter pose from joint data (matrix chain) | M |
| `0x969C` | 352 | M | Main render task (poses, overlay A, ring A, overlay B) | H |
| `0x98A4` | 56 | M | 15-joint matrix chain for one fighter | H |
| `0x99F8`, `0x9964` | | M | Task / helper called from `0x969C` and command 16 | L |
| `0x16830` | 174 | M | Task: collision driver and a pose step | M |
| `0x190B8`, `0x190EC`, `0x19120`, `0x19294`-`0x19400` | | M, S | Matrix stack reset, rotate-vector, scale, push/pop, rotations | H (190B8), M |
| `0x19424` | 52 | M | Ring B init, parameters, cache purge | H |
| `0x194A8` | 56 | M | Stage 3 driver | H |
| `0x194E0`, `0x194FC`-`0x199FB` | 28, 1,280 | M | Copy and body of overlay B | H |
| `0x19564`, `0x19734`, `0x197E6`, `0x19800`, `0x198C0` | | M (ovl B) | Polygon to chains, clipping, chain emit | M |
| `0x19D5C`, `0x19DDA` | | M | Model unpacker (cart `0x22144000` to `0x06030000`) | M |
| `0x19F00`, `0x19F3A` | 58, 42 | M | Sprite list drain; run-length blitter | M |
| `0x19F64` | 144 | M | LZ-type decompressor for pictures | M |
| `0x19FF4`, `0x1A00C` | 12, 844 | M, S | Collision test (Master half starts at 19FF4, Slave at 1A00C) | H |
| `0x1A358` | 180 | M | Software 32/32 divide (`div1` x32) | H |
| `0x1A808` | ~570 | M, S | Motion-channel decode (43 channels per frame) | L |
| `0x1C4A8` | 236 | M | Collision driver: mid-points, Slave cmd 3, merge masks | H |
| `0x1E48C` | 612 | M | Hit-mask arithmetic in on-chip RAM | M |
| `0x1E7FC` | | M | Blitter with a `braf` table (immediate 6, 7) | L |
| `0x18B04` | 72 | M | Pad edge detection from `COMM1` | H |

## Appendix B: how this was done

- **Listing and code map**: `sh-elf-objdump -b binary -m sh2 -EB` on the image (`vf.bin`/`vf.txt` in the session scratch directory; rebuild with `notes/games/tools/sh2dis.sh ROM 0x100000 0x22000 vf`). `vfa.py` (recursive descent with register tracking and trial-decoding of literal-pool pointers; `map`, `funcs`, `refs`), `dd.py` (compact disassembly with names from `syms.txt`), `hexd.py`, `regmap.py` (code/executed/data map), `fprof.py`/`fprof2.py` (executed-instruction histograms by function).
- **Instrumented PicoDrive**: `vf_trace.patch` on the sleep core of `notes/games/tools/build_sleep_core.sh` (`build_vf_core.sh`). It adds, in the interpreter (set `VRD_PROFILE_PC=1`): `VF_PCH` exact executed-instruction histogram; `VF_CALLS` call/return/interrupt log with instruction counters (`ctree.py`, `cagg.py` build call trees from it); `VF_TRACE` access counts by region and exact PC; `VF_WATCH=LO-HI` + `VF_WATCH_LOG` SDRAM access log with PC; `VF_EVT` event log of 68000 writes to `$A15100`-`$A1513F` and `$A15180`-`$A1518F` and SH-2 writes to the system and VDP registers (this one also works in the normal recompiler run, which is where the timing numbers come from); `VF68_TRACE` 68000 frame-buffer and FIFO writes. `dumpmem.py` dumps SDRAM through the debugger, `fbrender.py` renders a frame-buffer dump.
- **Traps met**: (1) a profile run from power-on stalls after about 1,300 frames (the 68000 stops sending commands), so the earlier "99% idle" profile of this game is an artefact: save states in a plain run every 100 frames and run profile windows from them; (2) the stock profiler samples the PC once per 32-cycle chunk, so its per-address cycles are coarse (use `VF_PCH`); (3) timings from interpreter runs are about 1.6x too long for the SH-2 phase (3-frame pictures instead of 2): use `VF_EVT` in a plain run; (4) spin-wait loops are counted as instructions in the interpreter and as sleep in the recompiler: compare work routines only.
