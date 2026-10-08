# Harvested techniques: Automated testing in an emulator

Target: Part VI chapter in `src/techniques/` (or `src/howto/emulator-testing.md`). 18 entries. Raw reports and source caveats: [../raw/](../raw/) (paths relative to by-chapter/).

Evidence and licence notes are per entry. Describe in the book's own words; never copy code.

<!-- from S32X-SKILL -->
### Headless libretro harness with a script DSL
- Source: S32X-SKILL, assets/harness.c:1-278; references/testing.md:30-48
- What it does and why it is clever: About 280 lines of C `dlopen` the PicoDrive core and declare only the libretro ABI subset needed. Commands: `run n`, `press b n`, `hold`, `release`, `port`, `shot`. Frames from RGB565, 0RGB1555 or XRGB8888 are converted to dependency-free PPM. Each game state is a small text file.
- Key numbers: Frames up to 512×512.
- Target chapter: NEW: Automated testing with headless PicoDrive
- Evidence: Used by every listed port.

<!-- from S32X-SKILL -->
### Lit / colourful / changing assertions
- Source: S32X-SKILL, assets/run_tests.py:36-39, 68-130; references/testing.md:50-79
- What it does and why it is clever: A frame fails if fewer than 8% of pixels are non-black (any channel > 8) or it has fewer than 8 distinct colours after 5-bit quantisation (6 for flat 3D). CRCs must differ across shots. UI checkpoints need distinct signatures, and region crops catch single objects rendered as black silhouettes.
- Key numbers: 0.08 lit ratio, 8 colours (6 for 3D), black level 8.
- Target chapter: NEW: Automated testing with headless PicoDrive
- Evidence: Template.

<!-- from S32X-SKILL -->
### Bounded-input-effect regression test
- Source: S32X-SKILL, references/testing.md:64-67; assets/scripts/02_menu.txt
- What it does and why it is clever: Pressing Down must change only a small fraction of pixels (the cursor moved), and Up must return the identical earlier frame. This directly catches the 6-button mirroring bug, where Down launches a level.
- Key numbers: 0.0001 < delta < 0.08.
- Target chapter: NEW: Automated testing with headless PicoDrive
- Evidence: Template.

<!-- from S32X-SKILL -->
### Telemetry channels: SDRAM beacon, COMM words, MD work RAM
- Source: S32X-SKILL, references/testing.md:305-327, 382-404, 505-512
- What it does and why it is clever: The master publishes `{magic 'ARK3', frame, state, score, x, y}` at a fixed SDRAM address. PicoDrive stores SDRAM byte-swapped on little-endian hosts, so the harness reads `p[off^1]`. Alternatively write COMM0-10 each frame (cash, loadout, signature|state, level_pos, event_index), or have the 68000 mirror a word into MD work RAM. Tests then assert exact end-state, e.g. `event_index == 1009`.
- Key numbers: —
- Target chapter: NEW: Automated testing with headless PicoDrive
- Evidence: arkanoid32x, tyrian-32x, raintown.

<!-- from S32X-SKILL -->
### In-ROM verification accelerator
- Source: S32X-SKILL, references/testing.md:359-380
- What it does and why it is clever: Holding an unused button runs N simulation ticks per rendered frame and makes the player invulnerable, so a short scripted hold covers a whole level deterministically.
- Key numbers: FAST_TICKS = 12. About 1,450 frames for the full level.
- Target chapter: NEW: Automated testing with headless PicoDrive
- Evidence: tyrian-32x.

<!-- from S32X-SKILL -->
### Desktop-oracle record/replay determinism
- Source: S32X-SKILL, references/testing.md:240-265
- What it does and why it is clever: The same core source builds for desktop and ROM. Record inputs on the PC (`--record`) and replay them into the ROM with a fixed tick. Any divergence is a portability bug (compiler trap, endianness or `long` width).
- Key numbers: 3 frames per tick.
- Target chapter: NEW: Automated testing with headless PicoDrive
- Evidence: beachy-beachy-ball-32x.

<!-- from S32X-SKILL -->
### Oracle against the original's own code
- Source: S32X-SKILL, references/testing.md:453-463
- What it does and why it is clever: Run the shipped JS physics verbatim beside the C port and diff trajectories. Compare frame-exact where the system is stable, and only aggregate behaviour in chaotic stretches (guardrail contact) where sub-LSB differences grow exponentially.
- Key numbers: Max dpos 0.004 units over 220 frames on a 187-unit circuit.
- Target chapter: NEW: Automated testing with headless PicoDrive
- Evidence: racing-circuit-32x.

<!-- from S32X-SKILL -->
### Tests must call the shared maths, not re-derive it
- Source: S32X-SKILL, references/testing.md:465-470
- What it does and why it is clever: Two handedness bugs survived because the test recomputed the same wrong rotation. Put the maths in one function (`r_model_to_world()`) that both the renderer and the test call.
- Key numbers: —
- Target chapter: NEW: Automated testing with headless PicoDrive
- Evidence: racing-circuit-32x.

<!-- from S32X-SKILL -->
### Heavy host testing of the HAL-free core
- Source: S32X-SKILL, references/testing.md:329-346; references/porting-workflow.md:25-50
- What it does and why it is clever: Every feature is a pure C module with a host test before it is wired into `main`. A scripted perfect player must clear level 1. A swept-collision test asserts a full-speed ball cannot tunnel through a brick in one tick. Fast paths are tested against reference code within 1 px.
- Key numbers: About 22,000 assertions (arkanoid32x).
- Target chapter: NEW: Automated testing with headless PicoDrive
- Evidence: arkanoid32x.

<!-- from S32X-SKILL -->
### Corner-screenshot geometry gate
- Source: S32X-SKILL, references/testing.md:348-357
- What it does and why it is clever: `make shots` renders the widest paddle in all four corners and fails the build if a projection retune pushes it off-screen.
- Key numbers: —
- Target chapter: NEW: Automated testing with headless PicoDrive
- Evidence: arkanoid32x.

<!-- from S32X-SKILL -->
### Verifying audio from captured PCM
- Source: S32X-SKILL, references/testing.md:159-178, 71-75
- What it does and why it is clever: Capture PicoDrive's audio callback and compare a normalised Goertzel bank (or FFT bands) against a libopenmpt render, with alignment tolerance and a loudness check. A known SFX is located by sparse normalised cross-correlation so FM music isn't mistaken for it. Only claim "audio confirmed" when such a test has actually run.
- Key numbers: —
- Target chapter: NEW: Automated testing with headless PicoDrive
- Evidence: tracker-player-32x.

<!-- from S32X-SKILL -->
### Symmetry check for the doubled-image fault
- Source: S32X-SKILL, references/testing.md:449-451
- What it does and why it is clever: Assert the left and right halves are not identical, which detects the direct-colour or COMM-collision doubled image.
- Key numbers: —
- Target chapter: NEW: Automated testing with headless PicoDrive
- Evidence: racing-circuit-32x.

<!-- from S32X-SKILL -->
### Black-screen debugging ladder
- Source: S32X-SKILL, references/testing.md:267-303
- What it does and why it is clever: Cheapest step first: print the top colours of the real frame; check the palette-0 tell; cycle the clear colour by `frame & 3` to tell a hang from a palette fault; reduce to a minimal boot; draw unconditionally to split render from logic; `cmp -l` the ROMs; check vectors in the raw ROM; rebuild from a known-good tree.
- Key numbers: 7 rungs.
- Target chapter: NEW: Automated testing with headless PicoDrive
- Evidence: Zepton multi-hour black screen.

<!-- from S32X-SKILL -->
### Heartbeat square plus interpreter-state overlay
- Source: S32X-SKILL, references/testing.md:476-493
- What it does and why it is clever: A per-frame toggling square: frozen means the CPU crashed, animating means a logic deadlock. An overlay shows the current opcode, event and flags (e.g. "parked on 0x6C waiting on switch 12").
- Key numbers: —
- Target chapter: NEW: Automated testing with headless PicoDrive
- Evidence: raintown-slickers-32x.

<!-- from S32X-SKILL -->
### Debug warps
- Source: S32X-SKILL, references/testing.md:495-503
- What it does and why it is clever: Title-screen combos jump to late maps or a test battle, so scripts reach deep content in a few frames.
- Key numbers: —
- Target chapter: NEW: Automated testing with headless PicoDrive
- Evidence: raintown.

<!-- from S32X-SKILL -->
### Harness input gotchas
- Source: S32X-SKILL, references/testing.md:118-130, 230-238
- What it does and why it is clever: Through PicoDrive libretro, script `a` → Genesis C, `b` → B, `c` → A, so accept A|B|C for actions. Presses on frame 0 are ignored; `run 20-30` first. Held buttons stack.
- Key numbers: 20-30 frames of boot.
- Target chapter: NEW: Automated testing with headless PicoDrive
- Evidence: Empirical.

<!-- from S32X-SKILL -->
### Pixel-detection pitfalls
- Source: S32X-SKILL, references/testing.md:132-150, 221-228
- What it does and why it is clever: Detect objects by a unique palette colour with a tight threshold; bullet yellow `#fff03c` was matched by sand `#d2be78`. Look where the projection puts objects, not where you expect them. `u8` positions wrap at 256.
- Key numbers: —
- Target chapter: NEW: Automated testing with headless PicoDrive
- Evidence: zepton32x.

<!-- from S32X-SKILL -->
### Verified-build report
- Source: S32X-SKILL, references/porting-workflow.md:267-277
- What it does and why it is clever: `BUILD_REPORT.md` records ROM size, SHA-256, header checksum, `.text`/`.bss` sizes against the stack guard, toolchain revision, and a table of PicoDrive scenarios with video and PCM metrics.
- Key numbers: —
- Target chapter: NEW: Automated testing with headless PicoDrive
- Evidence: raptor32x, tyrian-32x.

---

That is about 140 entries across 20 chapters. Three of them contain my own additions where the skill gives no maths, each labelled in its entry: the backface-culling formula, the Mode-7 depth formula and the IMA-ADPCM decoder details. Also labelled are my arithmetic for PWM cycles (≈2087 at 11,025 Hz, 1045 at 22 kHz) and the brad-to-scanline check.

