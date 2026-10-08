# Harvested techniques: patterns/cpu-split.md

Target: `patterns/cpu-split.md`. 22 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from S32X-SKILL -->
### Role assignment across three CPUs
- Source: S32X-SKILL, references/architecture.md:6-17; SKILL.md:156-159
- What it does and why it is clever: The master SH-2 runs game logic and drives the frame. The slave runs one heavy parallel job (PWM mixing or a render phase). The 68000 polls pads, services VBlank, plays YM2612/PSG music and handles SRAM. Using the idle slave is described as the biggest single 32X speedup.
- Key numbers: 2 × 23 MHz SH-2, 68000 at 7.6 MHz.
- Target chapter: patterns/cpu-split.md
- Evidence: d32xr and the ports.

<!-- from S32X-SKILL -->
### Offload stage 1: framebuffer clear on the slave with a bounded wait
- Source: S32X-SKILL, references/optimization.md:115-131; references/architecture.md:136-150
- What it does and why it is clever: The master posts `0x8000 | colour`, runs game logic while the slave clears, then waits for the ack before drawing. The framebuffer is uncached and the work is disjoint, so no cache handling is needed. The wait is bounded so a dead slave only slows the frame. The slave dispatcher is a few lines of assembly replacing the `crt0.s` idle loop (interrupts masked, registers only).
- Key numbers: About 72 KB of writes per frame. Wait capped at about 200 k spins.
- Target chapter: patterns/cpu-split.md
- Evidence: fighting-game-3D-32X, voxel ports.

<!-- from S32X-SKILL -->
### Offload stage 2: split rasterisation
- Source: S32X-SKILL, references/optimization.md:128-131
- What it does and why it is clever: The master draws the top half and the slave the bottom. Shared geometry in cached SDRAM needs real coherency work, so do it as its own milestone.
- Key numbers: —
- Target chapter: patterns/cpu-split.md
- Evidence: Described only.

<!-- from S32X-SKILL -->
### Slave dedicated to audio
- Source: S32X-SKILL, references/architecture.md:206-209; references/optimization.md:303-304
- What it does and why it is clever: A slave reserved for the PWM FIFOs means master render spikes can never starve the mixer. Unsynchronised render work on the slave risks FIFO underruns, so a free core is not automatically a free win.
- Key numbers: —
- Target chapter: patterns/cpu-split.md
- Evidence: wave-rider-gp, raintown, tempest-2k (slave = real-time PWM synth with a 140 BPM loop).

<!-- from S32X-SKILL -->
### Slave as a command and cache service
- Source: S32X-SKILL, references/architecture.md:210
- What it does and why it is clever: An RTS keeps gameplay and rendering on the master and runs a command/cache service on the slave.
- Key numbers: —
- Target chapter: patterns/cpu-split.md
- Evidence: warcraft-32x (described).

---

<!-- from D32XR -->
### Renderer phase map and two-CPU schedule
- Source: D32XR, r_main.c:1124-1183, mars.h:82-190, marsnew.c:355-405 (licence: id limited-use for r_main.c; MIT for mars.h and marsnew.c)
- What it does and why it is clever: The nine Jaguar phases survive as function names, but on the 32X they run in this order: R_Setup, then phase 1 (BSP walk, master), overlapped with phase 2 (wall late-prep and visplane marking, slave), then phase 6 (seg drawing, both CPUs), phase 7 (visplanes, both CPUs), phase 3 (sprite projection, master), phase 8 (sprites, screen split between CPUs) and phase 9 (texture-cache update, master). Phase 4 (late prep) just returns true and phase 5 (graphics caching) is an empty stub; their Jaguar bodies did LRU purging and LZSS-to-CRY decoding. The slave is a command loop that polls COMM4 and runs a whole multi-phase job per command; WALL_PREP chains WallPrep, SegCommands and PreDrawPlanes. Most per-frame synchronisation is therefore a single COMM register write.
- Key numbers: 12 secondary command codes (mars.h:36-58); FRT timestamps per phase.
- Target chapter: patterns/cpu-split.md
- Evidence: code only

<!-- from D32XR -->
### Producer/consumer pipeline between BSP and wall prep
- Source: D32XR, r_phase1.c:391-441, r_phase2.c:360-416, mars.h:91-108 (licence: id limited-use for the r_phase files; MIT for mars.h)
- What it does and why it is clever: Each time the master emits a viswall during BSP traversal, it increments a byte counter in COMM6 (Mars_R_WallNext). The slave polls that byte and runs R_WallLatePrep and R_SegLoop on every wall up to it. When BSP finishes the master writes -2, which tells the slave to read the final `lastwallcmd`. Front-to-back traversal and the projection and clip work therefore overlap without locks: the counter is a one-way, monotonic, single-writer channel.
- Key numbers: byte counters cap the list at 255 walls; MAXWALLCMDS = 165.
- Target chapter: patterns/cpu-split.md
- Evidence: code only

<!-- from D32XR -->
### Both CPUs drawing walls: claim flag plus replayed private clip state
- Source: D32XR, r_phase6.c:396-613 (licence: id limited-use)
- What it does and why it is clever: Both CPUs walk the same viswall list in order. CPU A waits until the slave's "ready" byte (COMM6+1) is past index i. It then takes a spin lock (`atomic_flag_test_and_set`, i.e. TAS.B) and sets AC_DRAWN to claim the seg, so each seg is drawn exactly once. Every CPU, whether or not it drew a seg, then copies that seg's new clip bounds into its own private `clipbounds[]` (post_draw). The occlusion state at index i depends only on segs before i, so each CPU rebuilds it independently and never shares it. A CPU that reaches the end writes -1 so the other stops early.
- Key numbers: clipbounds are 160 longs on the stack per CPU (two 16-bit entries per long).
- Target chapter: patterns/cpu-split.md
- Evidence: code only

<!-- from D32XR -->
### Splitting long walls for load balance
- Source: D32XR, r_phase1.c:391-441 (licence: id limited-use)
- What it does and why it is clever: R_StoreWallRange cuts any visible wall range longer than centerX/2 columns into several viswalls. A budget `splitspans` stops it splitting once 1.5x the viewport width in columns has been split. Small work items let the two CPUs' seg-drawing loops finish at about the same time, and the budget keeps the list under MAXWALLCMDS.
- Key numbers: chunk = centerX/2 (80 columns at 320 width); budget = 1.5 x viewportWidth.
- Target chapter: patterns/cpu-split.md
- Evidence: code only

<!-- from D32XR -->
### Visplane work queue sorted largest-first and by flat
- Source: D32XR, r_phase7.c:272-291, 480-566 (licence: id limited-use)
- What it does and why it is clever: The visplanes are insertion-sorted on a 16-bit key, `(127 - min(127, (maxx-minx-1)>>4)) << 8 | flat`, so wide planes come first and planes sharing a flat sit together. Both CPUs then pull the next plane index from a counter in COMM6 under a TAS lock. That is dynamic scheduling with longest jobs first, so the tail imbalance stays small. Grouping by flat keeps the same 4 KB flat in the CPU cache. Whichever CPU gets the lock first does the sort; the other waits.
- Key numbers: MAXVISPLANES 32; key = 7 bits of negated length plus 8 bits of flat. The comment reads "to minimize pipeline stalls, the larger planes must be drawn first".
- Target chapter: patterns/cpu-split.md
- Evidence: code only (rationale comment, not a measurement)

<!-- from D32XR -->
### Sprite screen split at the pixel-weighted centroid
- Source: D32XR, r_phase8.c:516-621, 397-465 (licence: id limited-use)
- What it does and why it is clever: The split column is the weighted mean `half = Σ (x1 + w/2)·w / Σ w` over every sprite, the weapon sprites and every masked mid-texture wall, where w is each one's pixel width. The master draws columns [0, half) and the slave [half, width). The sign of `sprscreenhalf` tells each CPU which side it owns (positive = left limit, negative = right start). Each CPU keeps its own sprite-opening array, so the load balances by drawn pixels rather than by sprite count.
- Key numbers: falls back to width/2 if the centroid is 0 or off-screen.
- Target chapter: patterns/cpu-split.md
- Evidence: code only

<!-- from D32XR -->
### Per-CPU thread-local state through GBR
- Source: D32XR, doomdef.h:1370-1395, sh2_draw.s:31-33, marsnew.c:368 (licence: id limited-use for doomdef.h and sh2_draw.s; MIT for marsnew.c)
- What it does and why it is clever: Each CPU points GBR at its own small TLS block holding the bank page, a bank-switch function pointer, its validcount array, column cache, current colormap, fuzz position and framebuffer base. The same assembly drawers fetch per-CPU state with one `mov.l @(disp,GBR),r0` each, so no CPU-id branch or extra argument is needed. The slave's validcount array sits right after the master's, so blockmap "already checked" marks never collide.
- Key numbers: TLS offsets 0, 4, 8, ..., 24 bytes (7 slots).
- Target chapter: patterns/cpu-split.md
- Evidence: code only

<!-- from D32XR -->
### Parallel, batched sight checks
- Source: D32XR, p_sight.c:367-543, p_base.c:270-288 (licence: MIT)
- What it does and why it is clever: Sight checks are not done on demand from AI code. Once per tic, both CPUs scan the mobj list for monsters whose `tics == 1` (about to change state) and that have a target, and set MF_SEETARGET. A TAS-locked shared cursor (`next_sight`) hands out mobjs; the slave purges cache lines for each mobj and target before reading them. The thinker later purges the cache line holding `flags` before it reads them, so it sees the other CPU's result.
- Key numbers: skipped in demos and real netgames.
- Target chapter: patterns/cpu-split.md
- Evidence: code only

---

<!-- from VRD/AU/MARSDEV -->
### Division of labour in Virtua Racing Deluxe
- Source: VRD-NOTES, analysis/RENDERING_PIPELINE.md:97-128; analysis/SLAVE_SH2_DISPATCH_ARCHITECTURE.md:8-17, 99-137; VR60_ROADMAP.md:1133-1153
- What it does and why it is clever:
  - **68K:** decides *what* to draw: physics, AI, collision, camera, depth sort, descriptor build, then a DREQ to the SH-2s. It never writes pixels in gameplay.
  - **Slave SH-2:** decides *how*: all 3D via two pipelines.
  - **Master SH-2:** is a command router, block copier and scene loader.

  The two SH-2s poll different COMM bytes and are never cross-triggered.
- Key numbers: historical racing-only profile:

  | CPU | Useful cycles per frame | Share |
  |---|---|---|
  | 68K | 45,481 | 63% V-blank idle |
  | Master SH-2 | 158,977 | about 41% of budget |
  | Slave SH-2 | 231,056 | about 60% of budget, about 80% utilised |

  Budgets are 128 K 68K cycles and 383 K SH-2 cycles per TV frame.
- Target chapter: patterns/cpu-split.md
- Evidence: emulator measured (PicoDrive). VR60_STATUS requires re-baselining. Early "Master renders 3D / Slave idle" docs are invalidated.

<!-- from VRD/AU/MARSDEV -->
### Offload break-even: compute ≫ handshake × calls
- Source: AU-NOTES, ROADMAP.md:1442-1495; VRD-NOTES, KNOWN_ISSUES.md:617-636 ("Synchronous COMM offload of angle_normalize")
- What it does and why it is clever: Aerobiz measured a real 68K→SH-2→68K RPC round trip by saturating counters and timing them. The round trip is a flat about 228 calls per frame (about 560 68000 cycles) whatever the work. A 32-bit divide therefore wins when slow (136.6 calls per frame in place on the 68K versus 228.2 offloaded) and loses when fast (443.4 versus 228.2). VRD saw the same rule fail in practice: moving an 8×-per-frame, about 1,500-cycle routine to the Master cost 23% of 68K time spinning on COMM.
- Key numbers: break-even about 560 cycles per call; PicoDrive's comm poll detection makes 228 an upper bound.
- Target chapter: patterns/cpu-split.md
- Evidence: emulator measured (PicoDrive)

<!-- from VRD/AU/MARSDEV -->
### Profile first: "offload AI" premise disproved; offloaded divide never runs
- Source: AU-NOTES, ROADMAP.md:1412-1440, 1497-1595
- What it does and why it is clever: The obvious candidates (AI, economy) were absent from the profile. The 68000 is 69.5% idle; graphics take 20.4% of frames, with the LZ decompressor alone at 11.93%. The "perfect" pure-maths offload (UnsignedDivide's slow path) was built, proven bit-identical over 12,000 frames, and then found to execute 0 times in 200,000 frames. The lesson: target shared engine code, not game logic.
- Key numbers: 418,549 gameplay frames sampled; 74-76-frame stalls every about 4,000 frames.
- Target chapter: patterns/cpu-split.md
- Evidence: emulator measured (PicoDrive)

<!-- from VRD/AU/MARSDEV -->
### Batch, don't call: job lists and FM rendezvous
- Source: AU-NOTES, ROADMAP.md:1650-1668; PORT_ARCHITECTURE.md:398-410
- What it does and why it is clever: Three reasons to batch work, strongest first:
  1. An FM handover is a mutual stall: both CPUs wait.
  2. Framebuffer FIFO writes are cheaper in continuous runs (3 clocks per word unfilled versus 5 filled).
  3. RPC amortisation.

  Cartridge-bus contention is not counted because PicoDrive cannot measure it. Every offloaded routine keeps its 68K version, selectable at assembly time, so results can be diffed.
- Key numbers: see the three reasons above.
- Target chapter: patterns/cpu-split.md
- Evidence: manual (reasoning); emulator measured for the round-trip cost

<!-- from VRD/AU/MARSDEV -->
### Inverted split: SH-2 as main CPU, 68K as an I/O server running from Work RAM
- Source: MARSDEV, /mnt/data/src/marsdev/examples/32x-skeleton/md_src/md_main.c:22-78; sh_src/m_main.c:14-55; sh_src/mars.c:186-233
- What it does and why it is clever: The Master runs the game. The 68K loops in `do_commands`, servicing SH-2 requests posted in COMM0 (`cmd<<8`: read pad into COMM8, set VRAM offset, write a nametable word, write VRAM), then clears COMM0. The 68K also publishes a V-Blank tick in COMM12, which the SH-2 uses for `swapBuffers()` pacing. All per-frame 68K functions are placed in `.data` (Work RAM) so the 68K stays off the cartridge bus and the SH-2s are not slowed.
- Key numbers: commands 3-7; COMM12 is a 32-bit tick.
- Target chapter: patterns/cpu-split.md
- Evidence: code only

<!-- from VRD/AU/MARSDEV -->
### Slave idle time turned into a work drain (COMM7 doorbell)
- Source: VRD-NOTES, analysis/68K_SH2_COMMUNICATION.md:144-198; analysis/RENDERING_PIPELINE.md:184-197
- What it does and why it is clever: The Slave's original idle path was a 64-iteration NOP delay loop. B-003 replaced it with `inline_slave_drain`. When COMM2_HI is idle, the Slave checks COMM7; on `$0027` it reads pixel-operation parameters from COMM2-6, acks by clearing COMM7, ORs the pointer with `$20000000` (cache-through) and does the work. The 68K's `sh2_cmd_27` becomes fire-and-forget.
- Key numbers: about 50 cycles per call versus about 250 via Master dispatch; 21 calls per frame (later found to be menus/attract only; 0 in racing).
- Target chapter: patterns/cpu-split.md
- Evidence: emulator measured (PicoDrive)

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

<!-- from MK2 -->
### Master draws, Slave plays sound, nothing shared (Mortal Kombat II)
- Source: MK2, SH-2 program; notes/games/mk2/ANALYSIS.md
- What it does and why it is clever: The 68000 runs the game and sends the Master a 668-byte state snapshot every frame through the ports. The Master is a pure renderer (16 modes, one per screen type). The Slave is a pure sound player, taking sample numbers from the 68000 through `$A1512E`. The two SH-2s share no SDRAM (the Slave's variables are `0x0600A200`-`0x0600A22B`, which the Master never touches) and never talk except for the `SLAV` handshake at start-up, so no cache purges and no locks are needed. The price is an idle Slave most of the time.
- Key numbers: 668 bytes per frame to the Master; 2 PWM voices on the Slave.
- Target chapter: patterns/cpu-split.md
- Evidence: ROM

<!-- from AB32X -->
### Master as a projection coprocessor, one synchronous call per object (After Burner Complete)
- Source: AB32X, 68000 `$7348`-`$73BC`; SH-2 `0x0600257C`
- What it does and why it is clever: The 68000 runs the game and, for each object, writes its parameters into the ports and the FIFO registers, raises CMD with command 15 and waits. The Master projects it inside the interrupt (16-step DIV1 reciprocal, muls.w), answers culled/position, and appends it to one of three rotating object rings. Its main loop sorts (256 buckets) and draws. The Slave does sound only.
- Key numbers: About 75 objects per drawn frame; 68000 spends about 12% waiting on answers (PicoDrive).
- Target chapter: patterns/cpu-split
- Evidence: ROM + emulator
