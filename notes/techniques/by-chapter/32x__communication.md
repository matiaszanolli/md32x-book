# Harvested techniques: 32x/communication.md

Target: `32x/communication.md`. 17 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from S32X-SKILL -->
### d32xr COMM job-dispatch loop
- Source: S32X-SKILL, references/architecture.md:95-111
- What it does and why it is clever: The slave's `Mars_Secondary` spins on a command word, runs the routine, and writes `NONE` back. The master's `Mars_R_SecWait()` waits for idle, writes parameters to another COMM word, then the command. Examples: clear cache, wall prep, planes, sprites, fire, sound DMA, sight checks, melt wipe, RoQ.
- Key numbers: COMM0-COMM14 (16-bit words).
- Target chapter: 32x/communication.md
- Evidence: d32xr.

<!-- from S32X-SKILL -->
### Deliberate COMM slot map with static and runtime guards
- Source: S32X-SKILL, references/architecture.md:217-230; references/testing.md:441-451
- What it does and why it is clever: The boot handshake (M_OK/S_OK), security checksum (COMM8), 68000 pad (COMM12/14), telemetry and jobs all share 8 words. A job sharing COMM4 with `S_OK` let the slave run before FM was granted and corrupt VDP registers, producing a doubled image. Keep a documented slot map, a `check_comm.py` grep for overlaps, and a left/right symmetry assertion in the emulator tests.
- Key numbers: COMM2 is suggested for jobs.
- Target chapter: 32x/communication.md
- Evidence: racing-circuit-32x bug.

<!-- from S32X-SKILL -->
### Sequence-number edge detection for commands
- Source: S32X-SKILL, references/audio.md:240-255
- What it does and why it is clever: Each request word is `(seq7 << 8) | id`, plus a loop bit and a stop sentinel `0x7F`. The receiver reacts when `seq` changes, not when the value changes, so playing the same id twice in a row still fires. The master side is a single store.
- Key numbers: 7-bit seq. COMM2 = BGM, COMM4 = SFX, COMM6 = slave heartbeat, COMM0 = "video ready" magic that gates PWM init.
- Target chapter: 32x/communication.md
- Evidence: raintown-slickers-32x.

<!-- from S32X-SKILL -->
### Boot handshake ordering traps
- Source: S32X-SKILL, references/architecture.md:113-128; references/testing.md:430-436
- What it does and why it is clever: Re-read the handshake register before clearing the release flag; releasing through a stale value stalls. Grant FM before the M_OK handshake or both sides wait forever. A minimal 68000 side must publish the ROM checksum in COMM8 to satisfy the security block.
- Key numbers: —
- Target chapter: 32x/communication.md
- Evidence: Black-screen catalogue (racer).

<!-- from S32X-SKILL -->
### TAS-based spinlocks
- Source: S32X-SKILL, references/toolchain-and-build.md:38-39
- What it does and why it is clever: `-mtas` lets GCC emit the SH-2 atomic test-and-set instruction, used for inter-CPU spinlocks.
- Key numbers: —
- Target chapter: 32x/communication.md
- Evidence: Toolchain flags.

---

<!-- from D32XR -->
### Single-producer, single-consumer queue in cache-line units
- Source: D32XR, mars_ringbuf.h:36-215, marssound.c:612-656, 1411-1453 (licence: MIT for the header; id limited-use for marssound.c)
- What it does and why it is clever: The read and write cursors each own a 16-byte-aligned cache line and are only touched through the uncached alias. Payload advances in 8-word (16-byte) steps, so a cache line belongs to one side at a time. The writer gets a cache-through pointer for its payload; the reader purges the payload lines before reading. Writes are refused if the queue is more than `128 - max(wcnt, 64)` words full. The game sends 8-word sound commands to the slave this way without locks.
- Key numbers: 16 lines = 128 words = 256 bytes.
- Target chapter: 32x/communication.md
- Evidence: code only

<!-- from D32XR -->
### TAS spin locks for shared counters
- Source: D32XR, r_phase6.c:328-337, r_phase7.c:257-291, f_wipe.c:30-58, p_sight.c:387-399 (licence: id limited-use; p_sight.c is MIT)
- What it does and why it is clever: Every shared work cursor is guarded by a one-byte lock taken with `tas.b`: next seg, next visplane (kept in COMM6), next melt column, next sight mobj. GCC's `atomic_flag_test_and_set` emits it under `-mtas`; f_wipe uses inline `tas.b`/`movt`. The lock covers only a read-increment-write, and the unlock is a plain byte store.
- Key numbers: lock = 1 byte.
- Target chapter: 32x/communication.md
- Evidence: code only

---

<!-- from VRD/AU/MARSDEV -->
### COMM hazard rules and set/clear ownership
- Source: VRD-NOTES, analysis/COMM_REGISTERS_HARDWARE_ANALYSIS.md:137-195, 421-438
- What it does and why it is clever: Any overlapping write+write or write+read of one COMM register is undefined, so the manual warns against splitting registers by direction. VRD's model is that the 68K sets non-zero values, the SH-2 clears them, and readiness is signalled through a different register. SH-2 writes sit in a one-level write buffer, so a dummy read of the same address forces visibility.
- Key numbers: 8 registers × 16 bits; SH-2 needs 3 clocks (1 wait) per access.
- Target chapter: 32x/communication.md
- Evidence: manual

<!-- from VRD/AU/MARSDEV -->
### Torn-read defence, level-polled state words and generation tags
- Source: AU-NOTES, disasm/sh2/master/rpc.c:1-90; disasm/32x/map_screen.asm:28-30
- What it does and why it is clever: Every read of a word written by the other side is taken twice and must agree. Map on/off is a level the SH-2 polls, not an RPC, so V-Blank-time changes cannot race the LZ handshake on the same slots. "Drawn" replies carry the switch-on generation, so a stale reply from an earlier visit is ignored.
- Key numbers: generation field `$0F00`; status bit `$8000`.
- Target chapter: 32x/communication.md
- Evidence: emulator measured (PicoDrive/Ares)

<!-- from VRD/AU/MARSDEV -->
### Single-shot command protocol with early parameter release
- Source: VRD-NOTES, analysis/RENDERING_PIPELINE.md:159-182, 233-248; analysis/68K_SH2_COMMUNICATION.md:200-252
- What it does and why it is clever: The original handshake took three waits. In the replacement:
  1. The 68K waits for COMM0_HI to be 0.
  2. It writes all parameters, then the index in LO and the trigger in HI, last.
  3. The SH-2 copies the parameters and clears COMM0_LO ("consumed"), so the 68K can return before the work finishes.
  4. At the end the handler clears HI with a byte write and re-checks LO; if another `$22` is already queued it loops without going back to the dispatcher.
- Key numbers: about 170 versus about 300 cycles per call (cmd $22); about 100 versus about 350 (cmd $25).
- Target chapter: 32x/communication.md
- Evidence: emulator measured (PicoDrive)

<!-- from VRD/AU/MARSDEV -->
### COMM namespace discipline and ack-after-handler
- Source: VRD-NOTES, analysis/68K_SH2_COMMUNICATION.md:166-173; analysis/COMM_REGISTERS_HARDWARE_ANALYSIS.md:324-355; AU-NOTES, KNOWN_ISSUES.md:765-777
- What it does and why it is clever:
  - **Namespace:** writing game command bytes into the COMM7 doorbell triggered uninitialised Slave handlers and crashed (B-006).
  - **Atomic clear:** `hw_init_short` clears COMM0:1 with one longword zero, then sets COMM1 bit 0 ("done"), so COMM1 can never carry parameters.
  - **Ack after handler:** Aerobiz's dispatcher re-dispatched any word left set, so a blocking menu left "3" behind and swallowed later LZ jobs. Every case now clears COMM0 after its handler returns, and every 68K timeout path writes the exit word.
- Key numbers: see above.
- Target chapter: 32x/communication.md
- Evidence: emulator measured (PicoDrive)

<!-- from VRD/AU/MARSDEV -->
### Bounded waits with fallback to the 68K, and PicoDrive's poll detector
- Source: AU-NOTES, disasm/32x/sh2_lz.asm:1-80; ROADMAP.md:1517-1530; KNOWN_ISSUES.md:291-307
- What it does and why it is clever: Each offload thunk counts down (`SH2LZ_TIMEOUT` = 400,000) and runs the stock 68K routine if the SH-2 never answers: a slow screen load beats a hang. Comm slots are protected by masking 68K interrupts for the call. Under PicoDrive the 68K is halted after 11 comm reads less than 64 cycles apart, so timeout paths never execute there; only Ares or hardware exercise them.
- Key numbers: 11 reads / 64 cycles poll-detect threshold.
- Target chapter: 32x/communication.md
- Evidence: emulator measured (PicoDrive/Ares)

<!-- from VRD/AU/MARSDEV -->
### CMD interrupt specifics
- Source: VRD-NOTES, analysis/COMM_REGISTERS_HARDWARE_ANALYSIS.md:216-243; KNOWN_ISSUES.md:216-222; AU-NOTES, KNOWN_ISSUES.md:203-208
- What it does and why it is clever: INTM and INTS raise CMD on the Master or Slave from the 68K. There is no SH-2→68K interrupt. Unlike V/H/PWM, CMD is negated when masked and re-asserts on unmask if still pending. It is cleared via `$2000401A`.
- Key numbers: see above.
- Target chapter: 32x/communication.md
- Evidence: manual

<!-- from VRD/AU/MARSDEV -->
### Boot handshake
- Source: VRD-NOTES, analysis/COMM_REGISTERS_HARDWARE_ANALYSIS.md:263-320; MARSDEV, md_src/md_start.s:162-178
- What it does and why it is clever: The Master posts "M_OK" in COMM0:1; the Slave posts "SLAV" and "S_OK". The 68K waits for both, then clears them to release the SH-2s and sets "INIT". marsdev's 68K also clears RV so the SH-2s can read ROM and sets FM before releasing the Master.
- Key numbers: `$4D5F4F4B`, `$535F4F4B`, `$534C4156`.
- Target chapter: 32x/communication.md
- Evidence: manual

---

<!-- from D32XR (hardware survey) -->
### d32xr hardware survey: Dual SH-2 work split and command protocol
- Slave command loop `Mars_Secondary()` (marsnew.c:336-413): loads GBR with the slave's thread-local block (:339), sets up DMA channels 0/1 (DMA_VCR1=66, priority 4, :354-355), spins on COMM4 until non-zero (:362), dispatches, writes COMM4=0 when done (:411).
- Command ids (mars.h:34-59): NONE, CLEAR_CACHE, BREAK, R_WALL_PREP_NODRAW, R_WALL_PREP, R_DRAW_PLANES, R_DRAW_SPRITES, M_ANIMATE_FIRE, S_INIT_DMA, AM_DRAW, P_SIGHT_CHECKS, MELT_DO_WIPE, S_INIT_ROQ_DMA.
- COMM4 = master to slave command; COMM6 = argument or shared counter. `Mars_R_SecWait()` is an unbounded spin (mars.h:82). No inter-CPU wait has a timeout. `Begin*` helpers wait, write COMM6, then COMM4 (mars.h:84-194).
- Per-frame pipeline (R_RenderPlayerView, r_main.c:1124-1183):
  1. Setup on the master; `Mars_R_BeginWallPrep` sets COMM6=0, COMM4=R_WALL_PREP (mars.h:91-98).
  2. BSP on the master overlapped with wall prep on the slave. Master bumps the COMM6 high byte after each wall (`Mars_R_WallNext`, mars.h:100-103; r_phase1.c:428-430) and writes -2 at the end (mars.h:105-108). Slave (`Mars_Sec_R_WallPrep`, r_phase2.c:360-416) reads added/ready counts from the two COMM6 bytes and prepares segs as they appear, bumping readysegs (:413); purges the last-wall cache line when it sees -2 (:396-400). Comment mars.h:96: "(next seg)<<8|last unready seg".
  3. Wall drawing on both CPUs, dynamically balanced: both run `R_SegCommands` (r_phase6.c:396-613), spin until a seg is prepped (:441), claim it with a test-and-set lock plus an AC_DRAWN flag (:445-455; lock :328-337); the first to finish writes -1 to COMM6 byte 0 and the other exits (:609-612, :439-440).
  4. Visplanes on both CPUs: `R_DrawPlanes` (r_phase7.c:544-566) takes the plane lock to sort, or waits; comment :554 "the secondary CPU is already on it, take our hands off the bus". COMM6 is the shared next-plane counter (`#define pl_next MARS_SYS_COMM6`, r_phase7.c:55-56) advanced under pl_lock (:272-291). Sort key: large planes first, then flat number (:477-510); comments: sort by flat "so that texture data has a better chance to stay in the CPU cache" (:477-478), "to minimize pipeline stalls, the larger planes must be drawn first" (:496).
  5. Sprites split by screen column: pixel-weighted average X "split the draw load between the two CPUs" (r_phase8.c:526-586); sorted list copied to shared memory (:604-608); split passed in COMM6 (mars.h:123-128); master draws +half, slave -half (r_phase8.c:496-509).
  6. Texture cache update on the master (r_phase9.c:251-260).
  7. End of frame: `P_Drawer` waits for the slave (p_tick.c:562).
- Other split jobs: sight checks, both CPUs under a lock (p_sight.c:386-440, 510-541); automap top/bottom halves (am_main.c:629-644, 849-862); melt wipe columns handed out from COMM6 under a `tas.b` lock (f_wipe.c:32-58, 184-203); menu fire runs on the slave until BREAK (m_fire.c:163; mars.h:140-144).
- Per-CPU thread-local storage through GBR: `mars_tls_t` (marsnew.c:42-53; offsets doomdef.h:1373-1379), accessed with `mov.l r0,@(offs,gbr)` (doomdef.h:1386-1390). Each CPU gets its own validcount array and column cache (marsnew.c:368; r_main.c:953).

<!-- from D32XR (hardware survey) -->
### d32xr hardware survey: 68000 side (src-md/)
- Main loop (crt0.s:412-482): PWM DAC feed, sound control, `bump_fm` refills the Z80 VGM buffer (:2501-2560); Z80 player uses Z80 RAM 0x1000-0x1FFF as eight 512-byte buffers (z80_vgm.s80:50); 68000 decompresses LZSS VGM into a 32 KB RAM buffer (vgm.c:15, 46, 82-199); Mega CD; polls COMM0 (master requests) and COMM4 (slave requests) (:464-482); controller hot-plug.
- Command table: COMM0 high byte selects the handler (crt0.s:498-545); done signalled by COMM0=0.
- Controllers read in the 68000 VBlank (crt0.s:2777-2832; 6-button :2837-2873) and pushed to the master by CMD interrupt + 0xA55A handshake + 0xFF00/0xFF02 with values in COMM2 (:3105-3133); master receives in `Mars_DetectInputDevices` (marshw.c:727-767).
- Parking the SH-2s: `sh2_wait` asserts CMD on both (0xA15102=3) and waits for 0xA55A in COMM0 and COMM4 (crt0.s:92-101); `sh2_cont` writes 0xFFFE and waits (:103-113); the SH-2 CMD handlers spin "in sdram" until 0xFFFE (crt0.s:598-689, 1024-1107). Used around SRAM (:557-671) and SSF mapper writes (:1591-1633). marshw.h:89-97 warns that while RV is set nothing on either CPU may read ROM, including DMA, code and interrupt handlers.
- Code in work RAM: main.c:45-48 "Main loop in ram - you need to have it in ram to avoid bus contention for the rom with the SH2s"; crt0.s:343 "Put remaining code in data section to lower bus contention for the rom". 68000 binary compiled for 0x880800 / 0xFF0000 (D/crt0.s:204).
- The 68000 toggles FM to read strings and arguments from the 32X frame buffer (crt0.s:711-726) and copies frame-buffer columns to MD VRAM or Word RAM (:1686-1760).
- SRAM 32 KB on odd bytes at 0x200001 (D/crt0.s:52-56); demos recorded to SRAM offset 0x800.


<!-- from AB32X -->
### FIFO registers as extra mailbox words; VRES marker; lost-CMD watchdog (After Burner Complete)
- Source: AB32X, 68000 `$7348`; SH-2 `0x06002260`, `0x060038E6`
- What it does and why it is clever: Object parameters also go in `$A1510A`, `$A1510D`/`E` and `$A15110` (DREQ source, destination, length), which the transfer never uses. The Master's VRES handler writes ASCII `VRES` to `$A1512C` so the 68000 sees the reset. The Master's main loop counts down 1,500,000 polls and then clears the busy byte and the CMD interrupt itself.
- Target chapter: 32x/communication
- Evidence: ROM
