# d32xr: hardware-level techniques (agent report, 2026-10-02)

Source: D32XR at commit 957d3a8, cloned to the session scratchpad. Paths are relative to the d32xr root. Licences are mixed: check each file's header (MIT for e.g. marshw.c, sh2_mixer.s; id limited-use for the Jaguar Doom code).

Caveats from the survey:
- The default build has no SH-2 PWM mixing: the Makefile adds `-DDISABLE_DMA_SOUND` unless `ENABLE_DMA_SOUND` is set (Makefile:26-28).
- README resolutions (128x144 to 252x144) do not match the code's viewport table (see 3).
- 32x.h:49-52 labels COMM8-COMM14 "unused"; they are used (RoQ flags in COMM8, 32-bit arguments in COMM8/COMM12).
- Bug: `Mars_SetSecCmdCallback` assigns `pri_cmd_cb` instead of `sci_cmd_cb` (marshw.c:1089-1092).

## 1. Dual SH-2 work split and command protocol

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

## 2. Cache usage and coherency

- Code runs from cached ROM 0x02000000 (mars-ssf.ld:50-99); registers through 0x2000xxxx (32x.h:28-52).
- Cache-through tricks: `MARS_ACTIVE_SCREEN` ORs 0x20000000 into a variable's address so both CPUs see it (marshw.c:88); trig tables read through 0x22000000, "cache-through access" (tables.c:2589-2595); ring-buffer rovers on the uncached alias (mars_ringbuf.h:37-38, 210-211); PCM command block written cache-through (marssound.c:1499-1534); DREQ DMA destinations cache-through (marshw.c:952).
- Lookup tables in spare frame-buffer DRAM read through the CACHED frame-buffer alias: `R_InitMathTables` builds viewangletox, distscale, yslope, xtoviewangle there (r_data.c:534-539) and clears bit 29, "enable caching for LUTs" (r_data.c:619-625). `initmathtables=2` (r_main.c:296), decremented per frame (p_tick.c:546-550); inference: builds the tables in both buffers.
- Shared per-frame structures (visplanes, viswalls, segclip, sorted lists, column caches) carved from the frame buffer past the visible lines (`I_WorkBuffer`, marsnew.c:869-875; r_main.c:878-921), used cache-through, so no purges needed.
- Purges: `SH2_ClearCacheLine` writes 0 to 0x40000000+addr; `SH2_ClearCacheLines` steps 16 bytes; `SH2_ClearCache` writes CCR=0 then CP|CE (32x.h:219-234). `CacheControl` (crt0.s:1268-1283).
- Boot: master CCR=0x10 ("purge and turn it off") before clearing BSS, 0x11 before main (crt0.s:369-372, 406-409); slave 0x11 (:856-859).
- Cross-CPU purges: r_main.c:944-954; texture/flat pointer arrays before the slave draws (r_phase6.c:617-652); plane/sprite list heads (r_phase7.c:305-307, 516-517; r_phase8.c:498-501); mobjs in sight checks (p_sight.c:407-428, 486-490); sound spatialisation (marssound.c:1087-1089, 1148-1153; comment :984 "cache read line loads all vars at once to cache"); RoQ chunks after DMA (marsroq.c:563, 591-592); full slave purge command after view changes (r_main.c:303, 365-366; r_data.c:930-933); purge after a bank switch (marsnew.c:711).
- Cache-line alignment: `.sdata` functions aligned 16 (marshw.h:37); map lumps "aline on cacheline boundary" (p_setup.c:74, 133, 247, 417, 542, 637); ring-buffer read and write rovers on separate lines (mars_ringbuf.h:40-51); zone (marsnew.c:761); sound buffers (marssound.c:70, 74).
- `ATTR_DATA_CACHE_ALIGN` = section ".sdata" (doomdef.h:69), linked into SDRAM 0x06000000 (mars-ssf.ld:102-118), copied from ROM by the 32X header load (crt0.s:116-124). Drawers, mixer, FixedDiv, IRQ handlers and vector tables live there.
- Not found: two-way cache mode / on-chip RAM (defined at 32x.h:96, 149, never used).
- Locks: `-mtas` (Makefile:24) makes atomic_flag_test_and_set use `tas.b`; explicit `tas.b` at f_wipe.c:36-41.

## 3. Frame buffer and 32X VDP

- `Mars_InitVideo` waits for FM, sets 224/240 lines + packed pixel (marshw.c:241-276). PAL uses a letterboxed 240-line mode with an 8-line offset (marsnew.c:426-431; marshw.c:121-125).
- Line table (`Mars_InitLineTable`, marshw.c:112-142): `lines[j] = j*160 + 0x100` (word offsets); unused entries point to one cleared blank line. Drawing base = frame buffer + 0x100 words (marsnew.c:81-83); 320-byte stride (sh2_draw.s:338-339). Menu fire unrolls the title picture by rewriting line-table entries (m_fire.c:375-386). RoQ remaps lines for its canvas pitch (marsroq.c:421-429). Line-table words 0xF0-0xFF used as a 68000 mailbox (marshw.c:388, 656, 679).
- Viewports: 160x90, 224x128, 256x144, 320x180; split-screen 160x100 to 160x144 (r_main.c:232-237). `lowres` halves the width (r_main.c:260-261) by pixel doubling in the drawers: 16-bit colormap entries (r_data.c:911-914), low drawers store words (sh2_drawlow.s:30, 64-66). Low-detail flats alternate `I_DrawSpanLow` / `I_DrawSpanLowSwap` per line (r_phase7.c:164); Swap does `swap.b` on the pixel pair (sh2_drawlow.s:441); purpose not stated. "Potato" mode fills spans with one texel (marsdraw.c:505-585). Anamorphic option changes a stretch constant 22 to 28 (r_main.c:273-282).
- Frame swap: `Mars_FlipFrameBuffers` toggles FS (marshw.c:100-105); `Mars_WaitFrameBuffersFlip` polls FS (:95-98). `I_Update` flips without waiting, then waits ticsperframe vblanks (marsnew.c:1101-1110); next frame waits for the flip before touching the back buffer (marsnew.c:871; r_main.c:253).
- Overwrite image used for text, word-aligned picture blits and the fire (marsnew.c:904-907; marsonly.c:155; marsdraw.c:658, 675-683; m_fire.c:367). Comment marsnew.c:859: "clear the buffer so the fact that 32x ignores 0-byte writes goes unnoticed".
- Palette uploaded in the master VBlank handler (marshw.c:1101-1110, 158-188), skipped and retried if the SH-2 does not own the VDP (:164-165); PEN never checked.
- Auto fill: not used. Direct colour only for RoQ (marsroq.c:434-435). Priority bit toggled for menu/wipe (`Mars_SetVDPPri`, marshw.c:786-793).

## 4. Column and span drawers

- Calling convention r4-r7 + stack; colormap and frame-buffer base from GBR (sh2_draw.s:31-33). `y*320` = `(y<<8)+(y<<6)` (:34-42). Delay-slot branches; loops unrolled 2x with mid-loop entry for odd counts (:50-54); `.p2alignw` on loop heads (:56).
- `I_DrawColumnA` (sh2_draw.s:17-78): 16.16 texture coordinate, `swap.w` for the integer part, mask by texheight-1; per pixel load texel, load colormap, store, add 320: 16 instructions per 2 pixels.
- Non-power-of-2 column wrap by subtracting texheight<<16 (sh2_draw.s:88-154; "tutti frutti" fix explained at marsdraw.c:120-124).
- Fuzz reads the frame buffer at +-320 (sh2_draw.s:166-223; r_data.c:613-617).
- Span drawer (sh2_draw.s:233-335) draws right to left with pre-decrement stores; end coordinates by `dmuls.l step,count` (:276-290); flat index `((yfrac>>16) & 63*64) | ((xfrac>>16) & 63)` with y pre-multiplied by FLATSIZE in C (r_phase7.c:117-119, 378-380); y-mask built with `mulu.w` (sh2_draw.s:267-274).
- Lighting: `HWLIGHT(l) = ((255-l)>>3 & 31)*256`, 32 rows of 256 bytes (r_local.h:47-48). Colormap base is the lump + 128 so the sign-extended `mov.b` texel works as a signed index (r_data.c:906-908; marsdraw.c:98).
- 4-bit textures (sh2_draw4b.s, sh2_drawlow4b.s): two texels per byte; `shlr` halves the index and leaves the nibble select in T. Comment sh2_draw4b.s:61-63: nibbles pre-swapped in the data to save address maths. Per-texture 16-colour x 33-level x 2-byte colormap at the end of the lump (r_main.c:434-436). Expanded to 8-bit when copied to the SDRAM texture cache (r_phase9.c:218-241).
- MIPLEVELS defaults to 1 (r_local.h:151-152).

## 5. Fixed-point maths and division

- FRACBITS 16 (doomdef.h:136); heights 12.4 (r_local.h:34-35).
- FixedMul: `((int64_t)a*b)>>16` (doomdef.h:625) compiles to `dmuls.l`; asm FixedMul2 uses dmuls.l / sts mach / sts macl / xtrct (sh2_fixed.s:28-33).
- FixedDiv on the hardware divider (sh2_fixed.s:39-50): DVSR=b, DVDNTH=exts.w(a>>16), DVDNTL=a<<16 starts it, result read back. Comment: overflow returns 0x7FFFFFFF/0x80000000 after 6 cycles; otherwise the quotient after 39 cycles. IDiv 32/32 via DVDNT (:56-63).
- Overlapped divides (start, do other work, read later): R_DrawSeg iscale = 0x00000000FFFFFFFF / scalefrac (r_phase6.c:190-247); R_MapPlane (lightcoef<<32)/distance (r_phase7.c:82-92, 131-152); wall scalestep (r_phase2.c:191-228); SlopeAngle (r_main.c:96-127); masked segs (r_phase8.c:66-98); sight intersection (p_sight.c:83-95); RoQ sync 64/32 divide (marsroq.c:903-907).
- Idioms: `mov #-128,rX; add rX,rX` makes 0xFFFFFF00 without a literal (r_phase6.c:193-194); `mov #-1; extu.w` makes 0xFFFF (r_phase8.c:117-120).
- Quarter-wave tangent and sine tables with quadrant folding (tables.c:2067-2619). No reciprocal table; per-viewport yslope and distscale built with FixedDiv (r_data.c:595-611).

## 6. Audio

- `Mars_InitPWM` (marshw.c:317-344): MONO=1 written three times (unexplained); CYCLE = (((clock<<1)/rate + 1)>>1) + 1 with clocks 23011361 (NTSC) and 22801467 (PAL), giving 1045 / 1035 at 22050 Hz; PWM_CTRL=0x0185 "TM = 1, RTP, RMD = right, LMD = left"; ramps from minimum to centre while polling FIFO full, "to avoid click in audio (real 32X)".
- Range MIN 2, MAX 1032, centre (MAX-MIN)/2 at 22050 Hz (marssound.c:12-15); no comment on why.
- Formats: 8-bit unsigned PCM (sh2_mixer.s:82-84), 4-bit IMA ADPCM with 2x upsampler (marssound.c:1012-1024; sh2_mixer.s:143-329), WAV parsing (marssound.c:1347-1390). Channel position 18.14 fixed, (freq<<14)/22050 (marssound.c:1388; sh2_mixer.s:60-63). Pan/volume with mulu.w/muls.w (sh2_mixer.s:46-102). s16 to u16 with clamping (marssound.c:1184-1194); comment :1175-1176 on GCC reloading constants.
- Optional DMA mixer on the slave: DMA channel 1 to the PWM stereo register (one long sets both channels, marssound.c:1464); CHCR1=0x18E5 (fixed destination, incrementing source, longs, external DREQ paced by RTP, cycle steal, interrupt) (:1209-1211); double buffer of 2x316 stereo longs, MAX_SAMPLES 316 "70Hz" (:8, 70); completion interrupt restarts DMA on the filled half and mixes the other (marshw.c:1136-1142; marssound.c:1197-1218); commands from the master through a cache-through ring buffer (marssound.c:1411-1451). PWM interrupt unused (crt0.s:695-712).
- Default build: SFX to the Mega CD driver if present (marssound.c:53-54, 185-220); the 68000 plays VGM DAC samples by polling the PWM FIFO in its main loop (src-md/crt0.s:419-444; src-md/vgm.c:250-280).
- RoQ audio on slave DMA 1 at 632 samples "35Hz" (marsroq.c:43, 293-316); comment :178 prefers mulu.w over mul.l for latency.

## 7. 68000 side (src-md/)

- Main loop (crt0.s:412-482): PWM DAC feed, sound control, `bump_fm` refills the Z80 VGM buffer (:2501-2560); Z80 player uses Z80 RAM 0x1000-0x1FFF as eight 512-byte buffers (z80_vgm.s80:50); 68000 decompresses LZSS VGM into a 32 KB RAM buffer (vgm.c:15, 46, 82-199); Mega CD; polls COMM0 (master requests) and COMM4 (slave requests) (:464-482); controller hot-plug.
- Command table: COMM0 high byte selects the handler (crt0.s:498-545); done signalled by COMM0=0.
- Controllers read in the 68000 VBlank (crt0.s:2777-2832; 6-button :2837-2873) and pushed to the master by CMD interrupt + 0xA55A handshake + 0xFF00/0xFF02 with values in COMM2 (:3105-3133); master receives in `Mars_DetectInputDevices` (marshw.c:727-767).
- Parking the SH-2s: `sh2_wait` asserts CMD on both (0xA15102=3) and waits for 0xA55A in COMM0 and COMM4 (crt0.s:92-101); `sh2_cont` writes 0xFFFE and waits (:103-113); the SH-2 CMD handlers spin "in sdram" until 0xFFFE (crt0.s:598-689, 1024-1107). Used around SRAM (:557-671) and SSF mapper writes (:1591-1633). marshw.h:89-97 warns that while RV is set nothing on either CPU may read ROM, including DMA, code and interrupt handlers.
- Code in work RAM: main.c:45-48 "Main loop in ram - you need to have it in ram to avoid bus contention for the rom with the SH2s"; crt0.s:343 "Put remaining code in data section to lower bus contention for the rom". 68000 binary compiled for 0x880800 / 0xFF0000 (D/crt0.s:204).
- The 68000 toggles FM to read strings and arguments from the 32X frame buffer (crt0.s:711-726) and copies frame-buffer columns to MD VRAM or Word RAM (:1686-1760).
- SRAM 32 KB on odd bytes at 0x200001 (D/crt0.s:52-56); demos recorded to SRAM offset 0x800.

## 8. Data streaming and banking

- WAD in cached ROM at 0x02000000 + WADBASE*1024 (wadbase.s:7; Makefile:31); lumps used in place via `I_RemapPtr` (w_wad.c:556-636); compressed lumps LZSS-decoded into frame-buffer scratch (:621-631). Textures copied on demand into an SDRAM zone cache with a 3-frame lifetime (r_phase9.c:13-247; r_cache.c:173-240; r_local.h:483-484).
- SSF banking: header "SEGA SSF", ROM end 0x4FFFFF (crt0.s:30-49; mars-ssf.ld:37). Master owns bank 6 (COMM0 cmd 0x16), slave bank 7 (via COMM4; 68000 replies 0x1000) (marsnew.c:460-466; marshw.c:705-720; 68000 side crt0.s:548-552, 1591-1633). `I_RemapPtr`: page = (p-0x02000000)>>19; new address = (p&0x7FFFF) + 512K*bank + 0x02000000, above 0x02300000 when ROM > 4 MB (marsnew.c:471, 723-741). Cache purged after switching (:711). The level's segs/nodes page kept resident (p_setup.c:962-979; reselected per frame r_main.c:718).
- 68000 to SH-2 FIFO / DREQ: 68000 side `dma_to_32x` (crt0.s:3140-3245): master CMD with 0xFF10, clear 68S, source/destination/length (rounded to 4 words, "FIFO operates on units of four words"), set 68S, write words to 0xA15112 polling FIFO full (bit 7 of 0xA15107), finish with 0xFF20. SH-2 side `Mars_HandleBeginDMARequest` (marshw.c:915-956): waits for 68S, DMA channel 0 SAR0=0x20004012, DAR0=0x20000000|dest, TCR0=word count, word transfers, DREQ edge; destination callback can refuse; `Mars_HandleEndDMARequest` polls TE (:958-973).
- RoQ: 68000 streams from CD into Word RAM and DMAs chunks (src-md/scd_roq.c:42-229); flags in COMM8 (marshw.h:163-166; marsroq.c:503-540); SH-2 ring buffers video 0xE000 / sound 0x5000 bytes (marsroq.c:36-37); decodes straight into a direct-colour frame buffer; previous frame copied to SDRAM by master DMA channel 1 in 16-byte auto-request units (marsroq.c:628-670).

## 9. SH-2 interrupt handling

- Vector tables in `.sdata`; levels 1-15 all to `pri_irq` / `sec_irq` (crt0.s:263-270, 323-330), which mask everything (SR=0xF0), write TOCR=0xE0 and dispatch by SR level through a 16-entry jump table, restoring the level in the jsr delay slot (:450-507, 895-952). On-chip peripherals routed into the same table: WDT VCR=65 priority 2 (marshw.c:303-304); DMA 1 VCR1=66 priority 4 (marsnew.c:354-355).
- FRT init TIER=0, TOCR=0xE2, OCRA=1, CKS=Fs/8, clear on OCRA match (crt0.s:350-365; slave :821-836). Each handler writes TOCR=0xE2 and reads it back, "bump ints if necessary" (e.g. :521-526). Sega's interrupt-bug document not cited by name.
- Enabled: master V + CMD (0x0A, crt0.s:401-402); slave CMD only (0x02, :851-852); slave DMA interrupt. HINT and PWM handlers are stubs with four nops "(remove nops if more than 8 cycles)" (:569-586, 695-712). Interrupt-clear registers written in each handler and at start (:337-348).
- WDT used as a profiling timer: overflow counter (:744-775), on/off 0xA53E/0xA518 (marsnew.c:1090-1096), read by `Mars_GetWDTCount` (marshw.c:235-239).
- VRES: clear VRES, SR=0xD0, reset the stack, jump to pri_reset/sec_reset (crt0.s:781-801, 1223-1243); slave posts S_OK, master waits, recopies the ROM .data image 0x22000000 to 0x26000000 cache-through, posts M_OK, both restart (:1317-1394).
- Startup: 68000 clears RV, waits for M_OK/S_OK (src-md/crt0.s:326-333), releases the master with COMM0=0 (:412-416); master clears COMM4 to release the slave and sets FM (crt0.s:384-402).

## 10. Performance notes

- No measured fps or ms figures in the source. Debug overlay shows per-phase times from the WDT (`4096*1000/clock`) (marsnew.c:982-1015; marshw.c:252-253, 54-55); live fps counter (marsnew.c:1116-1122).
- Frame cap ticsperframe 2-4 vblanks (doomdef.h:1313-1315; o_main.c:260-265, 564-565); demos "recorded at 15-20fps" (marsnew.c:1106).
- Comments on bus and cache: "take our hands off the bus" (r_phase7.c:554); plane sort for cache and pipeline (r_phase7.c:477-478, 496); 68000 code in RAM (src-md/main.c:45-48); FixedDiv 39/6 cycles (sh2_fixed.s:47-48); interrupt nops (crt0.s:583); mul.l latency (marsroq.c:178); GCC constant reloads (marssound.c:1175-1176); "64 seems to be too loud" (marssound.c:975); wipe speed halved for double buffering (f_wipe.c:119). Z80 driver quotes 32X Technical Notes 15 and 22 (src-md/z80_vgm.s80:7-12).
