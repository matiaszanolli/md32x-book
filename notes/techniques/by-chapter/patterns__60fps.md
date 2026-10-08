# Harvested techniques: patterns/60fps.md

Target: `patterns/60fps.md`. 13 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from S32X-SKILL -->
### 60/n vblank quantisation
- Source: S32X-SKILL, references/optimization.md:231-239; SKILL.md:266-270
- What it does and why it is clever: `Mars_FlipFrameBuffers` waits for vblank, so frame rate can only be 60, 30, 20, 15 and so on. Going slightly over a boundary halves the rate. Optimise to get under the next boundary, and measure the boundary rather than raw pixel counts.
- Key numbers: 60/n.
- Target chapter: patterns/60fps.md
- Evidence: arkanoid32x.

<!-- from S32X-SKILL -->
### Dirty rectangles over a cached background, tracked per framebuffer
- Source: S32X-SKILL, references/optimization.md:254-272
- What it does and why it is clever: Compose the static view into `s_bg[]` once and rebuild it only when a cheap signature of its inputs changes. Each frame, restore the rectangles under moving objects from `s_bg`, then draw them. Because the 32X page-flips, keep `s_dirty[2][]` per buffer; a single list leaves smears every other frame. Cache the HUD keyed on a hash of score, lives and level.
- Key numbers: About 932 px per frame instead of about 24,278 (about 25×). 29 → 60 fps.
- Target chapter: patterns/60fps.md
- Evidence: arkanoid32x, measured.

<!-- from S32X-SKILL -->
### Attack overdraw and fill-rate before arithmetic
- Source: S32X-SKILL, references/optimization.md:135-145, 183-195
- What it does and why it is clever: Hoisting about 1800 divides changed nothing, while shortening voxel columns took the game from 12 to 20 fps. If cutting vertex or cell counts does not help, you are fill-bound. A full 320×224 clear alone cost about 9 game iterations of budget.
- Key numbers: 12 → 20 fps. Clear = 71,680 bytes.
- Target chapter: patterns/60fps.md
- Evidence: zepton32x, measured.

<!-- from S32X-SKILL -->
### Shrink the work
- Source: S32X-SKILL, references/optimization.md:47-50
- What it does and why it is clever: Render a narrower or shorter internal buffer, add a "potato" mode with solid-colour floors and ceilings, cap draw distance, and reject off-screen objects early.
- Key numbers: —
- Target chapter: patterns/60fps.md
- Evidence: d32xr idioms.

<!-- from S32X-SKILL -->
### Inline the hot span fill
- Source: S32X-SKILL, references/optimization.md:356-358
- What it does and why it is clever: At about 1600 spans per frame, the span function's call and re-clip overhead was 62% of all span time. Inline it and use a `col → 4·col` word table so 32-bit stores need no shift or OR per span.
- Key numbers: 62% overhead.
- Target chapter: patterns/60fps.md
- Evidence: Measured (racer log).

---

<!-- from D32XR -->
### Variable-timestep game loop with a 15 Hz tic
- Source: D32XR, d_main.c:376-475, marsnew.c:1057-1124, p_user.c:30-31, 153, p_base.c:195, p_tick.c:357-405 (licence: id limited-use except marsnew.c, which is MIT)
- What it does and why it is clever: `vblsinframe` (vblanks the last frame took, capped at 8) scales player momentum and gravity every frame, so control responsiveness follows the frame rate. Monster thinkers, sight checks and specials run only when `gamevbls/4` advances a 15 Hz gametic. I_Update busy-waits until at least `ticsperframe` (2 to 4) vblanks have passed: 30 fps cap at 2, forced to 3 at full width in P_Update, and 4 during demos to keep them deterministic.
- Key numbers: TICRATE 15; TICVBLS 4; MIN/MAXTICSPERFRAME 2/4.
- Target chapter: patterns/60fps.md
- Evidence: code only

---

<!-- from VRD/AU/MARSDEV -->
### Why VR runs at 20 Hz: a state machine, not a compute limit
- Source: VRD-NOTES, analysis/FRAME_RATE_ARCHITECTURE.md:38-98; OPTIMIZATION_PLAN.md:88-118; VR60_ROADMAP.md:1133-1153
- What it does and why it is clever: `$C87E` advances 0→4→8, one state per V-INT. Only state 8 runs the game frame and arms V-INT handler `$54`. That handler swaps buffers and resets the state to 0 only when COMM1_LO bit 0 ("SH-2 done") is set; otherwise the machine stalls and retries. This gives graceful frame dropping with no timeouts. Fps = 60 / max(3, ⌈render time / TV frame⌉).
- Key numbers: 3 TV frames per game tick; racing 68K 63% idle.
- Target chapter: patterns/60fps.md
- Evidence: emulator measured (PicoDrive; exact caller trace confirms about 20 Hz)

<!-- from VRD/AU/MARSDEV -->
### Self-modifying main loop with STOP and per-state V-INT dispatch
- Source: VRD-NOTES, analysis/FRAME_RATE_ARCHITECTURE.md:14-35; analysis/VINT_HANDLER_ARCHITECTURE.md:14-82
- What it does and why it is clever: The main loop lives in Work RAM at `$FF0000`: `JSR <handler>` (target patched at `$FF0002`), then `MOVE.W #state,$C87A` (immediate patched at `$FF0008`), then `STOP #$2300`. V-INT reads and clears `$C87A` and uses it as a direct byte offset into a 4-byte jump table. Switching game mode is one longword write.
- Key numbers: about 21 table slots with pad gaps; frame counter `$C964` at 60 Hz.
- Target chapter: patterns/60fps.md
- Evidence: code only

<!-- from VRD/AU/MARSDEV -->
### STOP wakes on any interrupt: re-check the flag
- Source: VRD-NOTES, KNOWN_ISSUES.md:480-487
- What it does and why it is clever: Replacing V-Blank spin-waits with `STOP #$2300` let H-INT (whose vector is a bare RTE) wake the main loop early. The fix is to follow STOP with `TST.W $C87A / BNE` back to the STOP.
- Key numbers: car-select screen recovered from 1 fps to 5 fps (still slower than the original 20; partially fixed).
- Target chapter: patterns/60fps.md
- Evidence: emulator measured (PicoDrive)

<!-- from VRD/AU/MARSDEV -->
### Faking 30 fps by skipping a state fails without delta-time (S-4)
- Source: VRD-NOTES, OPTIMIZATION_PLAN.md:177-221; analysis/FRAME_RATE_ARCHITECTURE.md:263-330; VR60_ROADMAP.md:2243-2290
- What it does and why it is clever: Changing `ADDQ #4` to `ADDQ #8` gave 30 fps at once, but every per-tick constant is hard-coded for 20 Hz: speed clamp ±$400, air drag $71C0, boost $738, 15/10/30-frame timers, replay at 1 byte per tick, and frame thresholds 1241/1296. Scaling them by ×2/3 and ×1.5 across 20+ files broke collision, checkpoint music and attract timing. The plan now is to move logic into one SH-2 codebase with a single delta-time scale (60 Hz needs ÷3).
- Key numbers: inventory of about 30 constants (FRAME_RATE §6).
- Target chapter: patterns/60fps.md
- Evidence: emulator measured (reverted)

<!-- from VRD/AU/MARSDEV -->
### Camera-interpolated extra renders (A-1 "40 fps")
- Source: VRD-NOTES, analysis/FRAME_RATE_ARCHITECTURE.md:432-496; OPTIMIZATION_PLAN.md:18-45, 223-232
- What it does and why it is clever: The idea: snapshot previous and current camera, average 8 words, re-send by DREQ for a second render in state 4, block-copy and swap, while logic stays at 20 Hz.
- Key numbers: 192 bytes of trampoline; claimed SH-2 headroom 52%.
- Target chapter: patterns/60fps.md
- Evidence: invalidated. The hook was in the 2P dispatcher, and VR60_STATUS no longer accepts any 40-fps 1P result.

<!-- from VRD/AU/MARSDEV -->
### Drop frames by V-Blank clock, never run long
- Source: AU-NOTES, disasm/sh2/master/fb.c:1248-1297
- What it does and why it is clever: The renderer derives its frame index from `vint_count − t0`, counting skipped frames, so a slow frame shortens the motion instead of overrunning a fixed Genesis-side hold.
- Key numbers: 127 drawn, 0 skipped (PicoDrive).
- Target chapter: patterns/60fps.md
- Evidence: emulator measured (PicoDrive)

<!-- from VRD/AU/MARSDEV -->
### A strict definition of "60 fps achieved"
- Source: VRD-NOTES, VR60_STATUS.md:449-471
- What it does and why it is clever: The bar is 60 Hz logic and input (not just swaps or interpolated views), 60 distinct ordered frames per second, real-time equivalence of physics, timers and audio, no COMM deadlock or cache-alias errors over long runs, and a recorded ROM, input and profiler setup.
- Key numbers: see above.
- Target chapter: patterns/60fps.md
- Evidence: manual (project policy)

---

