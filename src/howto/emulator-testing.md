# Automated testing in an emulator

Nobody watches a ninety-second boot sequence on every build. Sega's answer for submission was the address checker, a box that watched a running game for accesses it should not make ([Sega's technical bulletins](../megadrive/errata.md)). The answer today is the same idea with better instruments: an emulator with no window, a script of inputs, and checks on what the game did.

You will be in one of two situations. With your own ROM you can instrument the program and check numbers it publishes. With a cartridge you cannot change, such as last month's build or a commercial game, you check what comes out of it: frames, sound and memory. The [profiling page](profiling.md) uses the same tools to measure speed; this page uses them to check correctness.

Everything on this page is about emulators, so every claim in it is tagged <span class="tag emulator">emulator</span> unless it says otherwise.

## Two emulators, two jobs

This book uses two emulators, and they answer different questions.

| | PicoDrive (libretro core) | ares 148 |
|---|---|---|
| Boot | Never runs the boot ROMs: its loader for them is compiled out. It copies the SH-2 program from the user header itself and starts both CPUs: no security check, no SDRAM test, no boot ROM register set-up [PICODRIVE, platform/common/emu.c, pico/32x/32x.c] | Runs Sega's real boot ROMs, byte-identical to the dumps [AU-NOTES, hardware tests] |
| Control from a script | Full: the libretro interface lets a small C program run frames, press buttons and read memory | None from the command line: no input scripts, no frame capture, no debugger for the 32X [AU-NOTES, hardware tests] |
| SH-2 cache | Not modelled; the cache control register is ignored [PICODRIVE, pico/32x/sh2soc.c] | Modelled, but only in the interpreter (below) [ARES, component/processor/sh2] |
| Access costs | Almost none ([Access timing](../32x/timing.md#in-emulators)) | One fixed cost per region ([Access timing](../32x/timing.md#in-emulators)) |
| Palette during the display | Writes always land, though PEN reads 0 [PICODRIVE, pico/32x/memory.c, 32x.c] | Writes wait for the palette to be free [AU-NOTES, hardware tests] |
| A 68000 polling a communication port | Stopped after a few fast reads until an SH-2 writes one (below) [PICODRIVE, pico/32x/memory.c] | Runs the loop for real |
| Speed | Fast enough to run tens of thousands of frames per test | Real time, with a window |

So the daily tests run in PicoDrive, and anything about start-up, or anything that the two might model differently, also goes through ares. The [hello world chapter](32x-hello.md#running-it) is a small example of why: its ROM runs in both, but only ares proves the cartridge layout is right, because only ares runs the boot ROM that checks it.

## The harness

The harness used for this book's measurements is the Virtua Racing Deluxe project's headless front end: one C file of about 1,500 lines that loads a PicoDrive libretro core with `dlopen`, runs a given number of frames and writes out what it is asked for [VRD-NOTES, libretro profiling front end]. Its environment variables give:

- **an input script**: a CSV file with one joypad mask per frame;
- **video dumps**: every *n*th frame between two frame numbers, as image files;
- **memory watches**: one row per frame with the values at chosen addresses;
- **frame fingerprints**: per frame, the 68000's program counter and hashes of video RAM, colour RAM and the VDP registers, taken from a save state;
- **a save state to start from**, and a small debugger script language: run *n* frames, print registers, read memory, save a state.

The memory reads and register dumps call debug functions that only the project's patched copy of the core provides, so the front end needs that core for those [VRD-NOTES, libretro profiling front end]. The book keeps its notes on building and driving it in `notes/games/tools/`, which is not published.

A harness does not have to be that big. A minimal one of about 280 lines covers running, pressing, holding and screenshotting, converts each frame to a plain image file with no libraries, and reads each test from a short text file [S32X-SKILL, harness]. The libretro interface was designed so that an emulator and the program driving it can be separate, and both harnesses rely on that.

### Input

An input script replayed into the same emulator and the same ROM gives the same run every time. The VRD project records this as a requirement, not a hope: two fresh replays of one script produced byte-identical frames and watch logs, and an 18,360-frame recording replayed and re-recorded to the same bytes [VRD-NOTES, VR60 status]. Without that, no comparison built on top means anything.

The strongest form of this keeps a desktop build too. If the game's core is plain C, build it once for the PC and once for the cartridge, record input on the PC and replay it into the ROM at a fixed rate of ticks. Any difference between the two runs is now a portability bug, such as a byte-order slip, a `long` of the wrong width or a compiler fault, found without touching a console [S32X-SKILL, testing notes].

Five things go wrong with input in practice:

- **The script must have one row per frame, exactly.** The VRD front end checks the length before it loads the core, and stops if it is wrong. Anything the core was meant to log then writes no file and prints no error, which looks like a broken feature rather than a run that never happened [AU-NOTES, known issues].
- **Button names shift.** Through PicoDrive's libretro mapping, a script's "a" reaches the console as button C, "b" as B and "c" as A. A test that means "the confirm button" should accept any of the three [S32X-SKILL, testing notes].
- **The first frames ignore input.** A press on frame 0 is lost. Let the boot run for 20-30 frames before the first press [S32X-SKILL, testing notes].
- **Emulated frames are not game frames.** A game running at 12 frames per second gets 12 updates in every 60 emulated frames, so a test that waits *n* frames for *n* steps waits too little, and a short effect can fall between two captured frames [S32X-SKILL, testing notes]. The [profiling page](profiling.md#counting-real-frames) shows how to measure the real rate.
- **Any timing change sends a run down a different path.** Shifting an input by one frame is enough to make an attract mode or a computer opponent choose differently. Two builds are then on different screens at the same frame number. The first frame at which two builds disagree still tells you where to look, because up to there they were in step; the frames after it may only show the divergence [AU-NOTES, known issues]. See [Comparing two builds](profiling.md#comparing-two-builds-of-your-own-game).

## Running ares without a screen

ares has no command-line way to capture frames, but it does not need a real display either. Run it inside a virtual X server and photograph that server's screen. This is how the hello world ROM was checked:

```sh
xvfb-run -n 97 -s "-screen 0 1280x960x24" sh -c '
  flatpak run dev.ares.ares --system "Mega 32X" --no-file-prompt "$HOME/ares-test/hello32x.32x" &
  sleep 20; import -window root shot1.png
  sleep 3;  import -window root shot2.png
  kill $!'
```

`xvfb-run` provides the virtual display and `import` (from ImageMagick) saves it. Two captures a few seconds apart show whether the picture is moving; the window's status bar also shows the frame rate. When the script ends, `xvfb-run` closes the display and ares exits with it. Points learned along the way:

- **Keep the ROM out of `/tmp`.** The flatpak build can read the host's files, but it has its own private `/tmp`, so a ROM there is invisible to it.
- **Timing questions need the interpreter.** ares's default SH-2 recompiler fetches instructions from its own compiled blocks, not through the cache model [ARES, component/processor/sh2/recompiler.cpp]. Add `--setting General/ForceInterpreter=true` for anything where the cache matters [AU-NOTES, hardware tests]. The hello world ROM runs at full speed either way.
- **Its log is not a list of your bugs.** ares prints each kind of unusual event once. The hello world ROM prints four notices, the same four that retail Virtua Racing Deluxe prints: two for the boot ROM's write to the SDRAM mode register, which ares does not handle, one "illegal slot instruction" for a branch-to-self in the boot ROMs, and one for the 32X's register writes passing through the cartridge hook [AU-NOTES, hardware tests]. With the interpreter forced, the slot notice goes away, so it comes from the recompiler; that is also a quick check that the setting took effect. Compare against a retail game before chasing a notice; one that a retail game does not print is worth a look.

This only tells you what appeared on screen. Input and exact frame numbers need a front end that ares does not have.

## Checking the picture

The cheapest checks read the frame itself.

- **Lit, colourful, changing.** Fail a frame if fewer than about 8% of its pixels are lit, or if it has fewer than eight distinct colours once reduced to 15 bits (six for flat-shaded 3D). Require each checkpoint to produce a different frame checksum, so a frozen picture cannot pass [S32X-SKILL, testing notes].
- **A check that passes on black has checked nothing.** One project's comparison against the original game passed 301 of 301 frames of a build that had faded to black for good, because the expected picture was black too. Any comparison should report how much of what it compared was actually lit, and treat "all equal, nothing lit" as a failure [AU-NOTES, known issues].
- **One input, one small change.** Pressing Down should change a small fraction of the pixels (the cursor moved), and pressing Up should give back the earlier frame exactly. This pair caught a misread six-button pad that made Down start a level, which a plain "did the screen change?" test would have passed [S32X-SKILL, testing notes].
- **Left is not right.** Checking that the two halves of the frame differ catches the doubled picture, where a communication collision or a direct colour mistake draws everything twice [S32X-SKILL, testing notes].
- **Find objects by a colour only they use**, with a tight tolerance: one project's yellow bullets were close enough to its sand that a loose match found beaches. Look where the projection puts the object, not where you expect it, and remember that an 8-bit position wraps at 256 [S32X-SKILL, testing notes].
- **Geometry gates.** Drawing the widest sprite in all four corners and failing the build if any of it is off screen turns a changed projection into a caught regression [S32X-SKILL, testing notes].

Two traps in comparing frames with save states. A frame and the save state taken after it can be one update apart: the frame may already show a change that the state only holds one frame later. So a check should accept state *f* + 1 as well as *f*, but never *f* − 1, because matching the past is a real lag [AU-NOTES, known issues]. And PicoDrive draws a 256-pixel-wide Mega Drive screen stretched to 320, so its frames cannot be compared pixel for pixel with a renderer that draws 256 wide [AU-NOTES, known issues].

## Telemetry from inside your own ROM

When the ROM is yours, the game can publish its state and the tests can check numbers instead of pixels.

- **A beacon in SDRAM.** The Master writes a small structure every frame to a fixed SDRAM address: a magic word, the frame number, the game state, score and position. Tests then check exact end states, such as "event 1009 reached" [S32X-SKILL, testing notes]. A word the 68000 copies into work RAM works the same way.
- **Not in a register.** The VRD core's debug reads return zero for the 32X system registers at `$A151xx`, so a counter kept in a communication port reads as zero, which looks exactly like "never ran". Keep anything you will read from outside in RAM, and check the read path once on a value you know is not zero [AU-NOTES, known issues].
- **A heartbeat.** A square that changes every frame separates the two causes of a frozen game: if the square stops, the CPU has crashed; if it keeps changing, the logic is stuck. An overlay with the current state turns a hang into a sentence, such as "parked at opcode `$6C`, waiting on switch 12" [S32X-SKILL, testing notes]. The hello world ROM's squares are this idea in its smallest form.
- **Fast-forward and warps built into the ROM.** One project ran twelve game updates per drawn frame while an unused button was held, with the player made invulnerable, and covered a whole level in about 1,450 frames. Button combinations on the title screen that jump to late levels put deep content a few presses away [S32X-SKILL, testing notes]. Take them out of the release build.

### Reading memory from a save state

A save state turns any moment into a test fixture: load it, read the memory you care about, run on. PicoDrive's state is a short header followed by numbered chunks, one per memory or chip, and three things trip people up [VRD-NOTES, libretro profiling front end; AU-NOTES, known issues]:

- **Words are stored in the host's byte order.** On a PC, video RAM, colour RAM, work RAM and SDRAM come out with each pair of bytes swapped: the console's byte at address *a* is at *a* XOR 1. Read big-endian, a tile map turns into convincing coloured noise. A quick test: Mega Drive colours have the form `0000 bbb0 ggg0 rrr0`, so read the first sixteen both ways and see which way fits.
- **The format belongs to the core version.** Don't keep fixtures across core updates without checking them.
- **A state can be broken without looking broken.** One recorded state stopped advancing a game variable after a while, whatever the game did, and a result built on it had to be withdrawn [VRD-NOTES, VR60 status]. After loading a state, check that the game is alive before trusting its numbers.

A state also limits a test to what can be reached from it. A comparison started deep in the game says nothing about the screens before that point [AU-NOTES, known issues].

## Oracles

An oracle is a second, trusted implementation to compare against.

- **The original's own code.** For a port, run the shipped game's physics beside the new version and compare the paths. Compare frame by frame where the system is stable and only overall behaviour where it is chaotic: one port stayed within 0.004 units over 220 frames, except while scraping a guard rail, where tiny differences grow fast [S32X-SKILL, testing notes].
- **Tests must call the shared maths.** Two mirrored-world bugs survived because the test worked out the rotation itself and made the same mistake as the renderer. Put the maths in one function that both the renderer and the test call [S32X-SKILL, testing notes].
- **The core on the PC.** A core with no hardware dependencies can be tested natively at full speed. One project runs about 22,000 assertions, including one that a ball at full speed cannot pass through a brick in one update [S32X-SKILL, testing notes].
- **Sound.** Capture the emulator's audio output and compare a bank of frequency detectors, or FFT bands, against a trusted render, allowing for small timing offsets and checking loudness. Find a known sound effect by cross-correlation, so music is not mistaken for it. Say "sound confirmed" only when such a test has actually run [S32X-SKILL, testing notes].
- **Builds that diverge are compared by content.** When a change alters timing, hash each frame's memories and pair frames between builds by hash. The [profiling page](profiling.md#comparing-two-builds-of-your-own-game) covers the method [AU-NOTES, comparison notes].

## When a run fails

- **Every experiment is a pair.** An instrumented ROM and a control ROM built from the same source, identical outside the instrumented bytes, with both hashes recorded. If the control fails, the experiment proves nothing. Checks fail closed: a missing result is a failure, not a pass [VRD-NOTES, VR60 status].
- **The black-screen ladder.** Cheapest step first: print the frame's most common colours; check whether palette entry 0 is the only one in use; change the clear colour with the frame number to tell a hang from a palette fault; cut down to a minimal boot; draw without conditions to separate drawing from logic; compare the ROM byte by byte with a good build; check the vectors in the raw ROM; rebuild from clean [S32X-SKILL, testing notes]. One project spent hours on a black screen that this list would have settled in minutes.
- **Record what was checked.** A build report with the ROM's hash and size, its section sizes against the stack limit, the toolchain version and the table of scenes with their picture and sound results turns "it worked when I tried it" into a claim someone else can repeat [S32X-SKILL, porting notes].

## What an emulator cannot tell you

An emulator is a model with holes, and some holes hide whole classes of bug.

- **PicoDrive never lets a 68000 time out.** After eleven reads of a communication port less than 64 cycles apart, it stops the 68000 until an SH-2 writes one. A wait loop with a time-out therefore never reaches the time-out, and every "the SH-2 did not answer" path is dead code under PicoDrive. To test such a path, space the reads out: a short delay between them is enough. One project did that and saw 95 of 340 calls fall back correctly [AU-NOTES, known issues; PICODRIVE, pico/32x/memory.c].
- **PicoDrive's quiet start.** PicoDrive never runs the boot ROMs, so nothing checks the cartridge layout or Sega's initial program, and the boot ROMs' own set-up never happens: no SDRAM test, and no write that switches the cache on [PICODRIVE, platform/common/emu.c, pico/32x/32x.c]. PicoDrive has no cache to switch on, but a timing model added to it does, and under it a program that does not enable its own cache runs uncached. One project concluded from such a run that its Slave had never enabled its cache. Rerun with the boot ROMs loaded, the cache was on all along ([Mistakes the reference projects made](../patterns/cache.md#mistakes-the-reference-projects-made)) <span class="tag emulator">emulator</span> [AU-NOTES, HISTORY, hardware tests].
- **The palette.** PicoDrive accepts a palette write during the display; ares makes it wait; on a console it waits up to a line ([Colours and the palette](../32x/vdp.md#colours-and-the-palette)). One project shipped its first fix for a difference between the two emulators here, on a menu fade [AU-NOTES, hardware tests].
- **Timing.** Neither emulator charges the manual's access costs, the competition between the CPUs, or the frame buffer's write buffer ([Access timing](../32x/timing.md#in-emulators)). In PicoDrive, switching the cache on changes the measured time by exactly nothing, which says something about the emulator, not about whether the cache was on [AU-NOTES, known issues].
- **Access without FM.** Both emulators drop a frame buffer or VDP write from the CPU without FM; the manual says it waits ([discrepancy 34](../appendices/discrepancies.md)).

A behaviour that passes in both emulators is worth taking to a console. A behaviour that differs between them is a finding, not a nuisance. Keep a list of what only real hardware can answer, and take it to the [hardware testing page](real-hardware.md).

## What to take away

- Run the daily tests headless in PicoDrive, and check start-up and anything timing-related in ares, which runs the real boot ROMs.
- Make every run reproducible: one input row per frame, and the same bytes out every time.
- Never let a check pass on a black or frozen picture.
- Publish the state of your own ROM in RAM, not in registers, and read it from outside.
- Fix the byte order when reading a PicoDrive save state, and check a state is alive before trusting it.
- Under PicoDrive, a 68000 waiting on the SH-2s never times out; test those paths with spaced reads or in ares.

## Open questions

- Does PicoDrive's poll detection hide any retail game's time-out path, and does any retail game depend on one?
- Which of ares's fixed access costs come from measurement, and which from the manual?

## Where to go next

- [Profiling and finding where time goes](profiling.md): the same harness, asked about speed.
- [Disassembling and annotating a commercial game](reverse-engineering.md): when the ROM under test is not yours.
- [Testing on real hardware](real-hardware.md): the questions this page cannot settle.

## Sources

- [S32X-SKILL](../appendices/bibliography.md#s32x-skill): harness; testing notes; porting notes
- [VRD-NOTES](../appendices/bibliography.md#vrd-notes): libretro profiling front end (`tools/libretro-profiling/profiling_frontend.c`); VR60 status (`VR60_STATUS.md`)
- [AU-NOTES](../appendices/bibliography.md#au-notes): known issues (`KNOWN_ISSUES.md`); HISTORY; hardware tests (`HARDWARE_TESTS.md`, the ares section); comparison notes
- [PICODRIVE](../appendices/bibliography.md#picodrive): pico/32x/32x.c, memory.c, sh2soc.c; platform/common/emu.c
- [ARES](../appendices/bibliography.md#ares): version 148, component/processor/sh2 (cache, recompiler)
