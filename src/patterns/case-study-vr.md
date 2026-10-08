# Case study: Virtua Racing Deluxe

*Virtua Racing Deluxe* (Sega, 1994) was one of the 32X's launch titles: Sega's own arcade racer, in 3D, on a 3 MB cartridge. A fan disassembly of it, the VRD project, rebuilds the cartridge from source and documents how the game is put together, then tries to make it faster [VRD-NOTES]. This chapter reads the project's disassembly and architecture documents, on its `master` branch, for what they say about the original game. It then covers what the project changed, what that achieved, and what the attempt teaches about 32X work.

It is also a case study in evidence, and that comes first.

## How far the evidence goes

Three things limit what the project can show about the original game:

- **Its ROM is not the retail original.** The project's cartridge file has MD5 `85eda196…`, where the retail original's is `72b1ad0f…`, and its header checksum does not match. Its SH-2 program contains handshake words written by the project's own tools: the bytes `REDY`, `WORK` and `DONE` at cartridge `$0206A4`-`$0206AF`, the start of the Master's interrupt handler. The disassembly on `master` was matched to that file, so its source contains those words too [VRD-NOTES, master branch, disasm/sections/code_20200.asm]. Compared byte for byte with the retail copy that has since reached the sources, the project's file differs in 103 bytes only, at cartridge `$020650`-`$0206BD` (SH-2 `0x06000650`-`0x060006BD`, from the end of the Slave's CMD handler to the start of the Master's interrupt dispatcher) [32X-ROMSET]. The disassembly source on `master` has further changes of the project's own, for example in the Slave's code from `$020608` [VRD-NOTES, commit `d8b770c`], so it no longer matches either file. The book trusts only the first 2 KB: the headers and Sega's initial program ([VRD-NOTES](../appendices/bibliography.md#vrd-notes)). A retail copy with MD5 `72b1ad0f…` and a matching checksum has since reached the book's sources, but only its VRES handlers have been read so far. They share a reset handshake, the word `VRES` posted in a communication port, with Rutubo Games' After Burner Complete and Space Harrier, and with no other game ([The `VRES` handshake](../appendices/sample-code.md#the-vres-handshake-rutubo-games-and-virtua-racing-deluxe)) [32X-ROMSET, Virtua Racing Deluxe, SH-2 code at `0x060004A4`, `0x06000614`]. The comparisons below have not yet been redone against it.
- **Its documents disagree with each other.** They were written over three months as understanding changed, and some describe the original game while others describe a build already changed by the project. Two documents on `master` give the 3D renderer to different SH-2s ([discrepancy 28](../appendices/discrepancies.md)).
- **Its headline results were later retracted.** `master`'s README reports "40 FPS achieved, 60 FPS one blocker away". The project's current status files say that result was a historical experiment aimed at the two-player mode and does not describe the normal one-player game [VRD-NOTES, README; KNOWN_ISSUES, camera interpolation].

So everything below is the project's account, tagged <span class="tag emulator">emulator</span>, and is compared with the clean retail ROMs read for this book where possible. The project deserves credit for the retractions: it records what turned out wrong instead of deleting it.

## How the game divides the work

| CPU | Job, by the project's account |
|-----|-------------------------------|
| 68000 | Game logic, physics, AI, collision, the camera, depth sorting; the sound sequencer, which writes the FM and PSG chips itself while the Z80 plays only samples; the Mega Drive VDP, which draws the race HUD; and every command to the SH-2s |
| Master SH-2 | A command loop: polls a communication port, looks the command up in a 16-entry table at `0x06000780`, and runs it. Commands include block copies, scene set-up, a 56 KB bulk copy of track data, and the scene and render handlers run once per picture |
| Slave SH-2 | A second command loop with its own table at `0x060005C8`, polling a different port, with a 64-pass delay between polls. Rendering handlers, and a 1,748-byte routine in on-chip RAM that processes the cars and objects |

Sources: [VRD-NOTES, master branch, analysis/SYSTEM_EXECUTION_FLOW.md; analysis/SLAVE_SH2_DISPATCH_ARCHITECTURE.md §1-§3, §5; analysis/SOUND_DRIVER_ARCHITECTURE.md].

**The frame rate.** The 68000 steps through a state machine, one state per vertical interrupt, and asks for a new picture once every three: about 20 pictures a second ([When a picture runs long](60fps.md#when-a-picture-runs-long)) [VRD-NOTES, analysis/FRAME_RATE_ARCHITECTURE.md].

**Commands.** For each picture, by the project's count, the 68000 sends about 14 block copies to the Master and 21 pixel jobs to the Slave. In the original protocol each one was a handshake through the communication ports: write the parameters, raise a flag, wait for the SH-2 to take it, wait again for it to finish. The project calls this "submit → wait → continue": no queue of commands, no overlap between preparing the next job and running this one [VRD-NOTES, analysis/ARCHITECTURAL_BOTTLENECK_ANALYSIS.md §2-§3; SYSTEM_EXECUTION_FLOW.md §3].

**Who renders.** The project's documents give the whole 3D renderer to the Slave. One of them argues that when the Master calls a routine in shared SDRAM, the Slave executes it, because the two share memory. That is not how the hardware works: a `jsr` runs on the CPU that issues it, whatever memory the code sits in, and each SH-2 has its own on-chip RAM ([Two SH-2s, one bus](../sh2/bsc.md#two-sh-2s-one-bus)). Read directly, the patched ROM looks more like Star Wars Arcade's split, with the Master transforming and the Slave filling ([Software 3D](../techniques/software-3d.md#open-questions)). The clean retail ROM settles the filling half: its span-fill routine runs on the Slave <span class="tag emulator">emulator</span>. Which CPU transforms stays open ([discrepancy 28](../appendices/discrepancies.md)).

### Compared with the retail games

The design the project describes is the most serialised of the 3D games in this book:

- **Star Wars Arcade** runs a two-stage pipeline: the Master transforms and sorts the next picture while the Slave draws this one, from double-buffered lists ([Splitting work across three CPUs](cpu-split.md#a-pipeline-geometry-on-the-master-pixels-on-the-slave)).
- **After Burner Complete** also calls the Master once per object, but each call is a CMD interrupt that returns at once, and the Slave runs sound and never waits on the 68000 ([One call per object](../32x/communication.md#one-call-per-object)).
- **Virtua Racing Deluxe**, by the project's account, has the 68000 wait on every command. While the 68000 waits it does no game logic; while the SH-2s wait they draw nothing.

## Where the time went

By the project's profiles in PicoDrive, at different times and in different builds <span class="tag emulator">emulator</span>:

- **The Slave mostly waited.** A January 2026 profile put 66.5% of its cycles in the delay loop between polls, at `0x0600060A`. The project reads this as underuse forced by the handshake design. Later documents put the Slave at 73-78% busy, after the project had moved work to it [VRD-NOTES, analysis/ARCHITECTURAL_BOTTLENECK_ANALYSIS.md §3.2; README].
- **The Master idled between commands**, at 0-36% busy [VRD-NOTES, README; SYSTEM_EXECUTION_FLOW.md].
- **The 68000 was the limit.** It had no spare time in the original game: game logic took most of the frame, and the command waits came on top [VRD-NOTES, SYSTEM_EXECUTION_FLOW.md §4].

The project's own warning about these numbers is the right one: a vertical interrupt count says how often the system ticks, not how often a new picture is finished ([Counting real pictures](../howto/profiling.md#counting-real-pictures)) [VRD-NOTES, ARCHITECTURAL_BOTTLENECK_ANALYSIS.md §4]. [Profiling](../howto/profiling.md#four-traps-all-met-in-the-wild) lists the traps the project met on the way, from averaging across scenes to trusting a truncated histogram.

## What the project changed

| Change | What it did | Result |
|--------|-------------|--------|
| B-003 | The Slave's pixel jobs became fire-and-forget: the 68000 writes the job and a doorbell word, and returns | About 3,000 68000 cycles saved per picture |
| B-004 | Block copies went from three waits to two: the Master clears one flag as soon as it has read the parameters, and another when the copy is done. The next command's first wait doubles as the completion check | About 1,400 cycles saved per picture |
| B-005 | Make block copies fire-and-forget too | Blocked: the same port flag is also how the game keeps the CPUs in step from one picture to the next, so removing the wait breaks it |
| B-006 | Move vertex transforms to the Slave | Reverted: its new commands collided with words the game already used in the ports |
| S-6 | Inline the Slave's coordinate transform at its four call sites, in new code at the top of the cartridge | The routine fell from 17% to 12% of the Slave's time |

Sources: [VRD-NOTES, master branch, analysis/SYSTEM_EXECUTION_FLOW.md §3, §6; SLAVE_SH2_DISPATCH_ARCHITECTURE.md §5] <span class="tag emulator">emulator</span>.

**None of it raised the frame rate.** The project's own conclusion: with the waits reduced to about 100 cycles from about 350, the 68000 was still fully busy with game work, so the pictures came no faster [VRD-NOTES, analysis/ARCHITECTURAL_BOTTLENECK_ANALYSIS.md §2]. Shaving the handshake helps only if the CPU that waited has nothing else to do, and here it had.

Two attempts went after the rate itself:

- **Camera interpolation** (A-1): render a second picture between game steps with the camera moved halfway, so the display runs at 40 pictures a second while the game still steps at 20. `master` records it as achieved. The project later found that the code path it changed serves the two-player mode, and withdrew it as evidence for the normal game [VRD-NOTES, master branch README; KNOWN_ISSUES, camera interpolation].
- **A faster game step**: stepping the game's state machine more often gave 30 pictures a second at once, but about 30 constants assume 20 steps a second, and scaling them broke collisions, music cues and the attract mode. It was reverted ([When a picture runs long](60fps.md#when-a-picture-runs-long)).

## The fourth megabyte

The retail cartridge is 3 MB: its header's ROM end address is `$2FFFFF` [VRD-NOTES, ROM header]. The project extended its build to 4 MB, setting the end address to `$3FFFFF`, and uses the new megabyte for SH-2 code: the inlined transform, the new block-copy handler and other additions, about 2.5 KB in all [VRD-NOTES, master branch, analysis/architecture/ROM_EXPANSION_4MB_IMPLEMENTATION.md; README].

Its first attempt put 68000 code there and gave a black screen. The project's write-up of that failure gets three things wrong, and each one is a common mistake:

- **The 68000 can reach the fourth megabyte.** The document says it cannot. It can, through the banked window: bank 3 shows cartridge `$300000-$3FFFFF` at `$900000-$9FFFFF` ([Who sees what](../howto/large-cartridges.md#who-sees-what)).
- **`0x02000000` is the cached view**, not the cache-through one. The cartridge's cache-through view is `0x22000000` ([Cache discipline](cache.md#what-a-read-costs-through-each-view)).
- **The new megabyte starts at SH-2 address `0x02300000`**, not `0x023F0000`: the SH-2 sees cartridge offset *n* at `0x02000000` + *n* ([Architecture and memory maps](../32x/architecture.md)).

Code that runs from the cartridge pays for it in cache misses and bus time. A small handler called once per frame can afford that; a loop that runs per pixel or per vertex belongs in SDRAM or on-chip RAM ([Code that runs from the cartridge](../howto/toolchain.md#code-that-runs-from-the-cartridge)).

## What the project teaches

- **Check a dump before building on it.** Compare its MD5 with a known-good list and its header checksum with its contents, keep the original file read-only, and write every patched build to a new name. A byte-identical disassembly of a modified file proves only that the disassembly matches that file.
- **A wait is only worth removing if the waiting CPU is the bottleneck.** Measure what the waiting CPU would do with the time first.
- **A design that waits on every command cannot use three CPUs.** Pipelines, queues and commands that return at once are what the retail games that ran faster used.
- **A game's timing constants are part of its frame rate.** Changing the rate of a finished game means finding every one of them.
- **Shared memory does not share execution.** A routine runs on the CPU that calls it.
- **Write retractions down.** The project's status files, which record what was believed and why it was wrong, are worth more to a reader than its success claims.

## Open questions

- How does the retail ROM really divide the 3D work between the SH-2s ([discrepancy 28](../appendices/discrepancies.md))? Answering it needs a clean dump, MD5 `72b1ad0f…`.
- How far does the project's ROM differ from the retail original beyond `$0206A4`?
- What do the Master and Slave spend per picture in the original game, profiled with an SH-2 timing model and gated to one scene?

## Sources

- [VRD-NOTES](../appendices/bibliography.md#vrd-notes): `master` branch (March 2026): README; analysis/SYSTEM_EXECUTION_FLOW.md; analysis/SLAVE_SH2_DISPATCH_ARCHITECTURE.md; analysis/ARCHITECTURAL_BOTTLENECK_ANALYSIS.md; analysis/FRAME_RATE_ARCHITECTURE.md; analysis/SOUND_DRIVER_ARCHITECTURE.md; analysis/architecture/ROM_EXPANSION_4MB_IMPLEMENTATION.md; disasm/sections/code_20200.asm. Current status files: README; KNOWN_ISSUES
- [SWA](../appendices/bibliography.md#swa), [AB32X](../appendices/bibliography.md#ab32x): as linked
