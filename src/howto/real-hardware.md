# Testing on real hardware

Everything in this book that was run, was run in an emulator. Not one claim carries the <span class="tag tested">tested</span> tag yet, and the tag means confirmed on a real console ([Conventions](../conventions.md)). This chapter is about changing that: getting a program onto a console, which console to use, how to design a test that reports its own result, and a checklist of the questions that most need one. The questions themselves come from the open-questions sections of the other chapters, where more than a hundred are waiting.

## Getting code onto a console

There are three ways, and the book's sources document only two of them:

- **Sega's development cartridge boards.** EPROM boards for 4 and 16 Mbit parts and a battery-backed SRAM board that can be rewritten in place, all with Sega's bank chip ([Sega's development boards](../megadrive/cartridge.md#segas-development-boards)). For the 32X, Sega asked for EPROMs of 120 ns or faster, because the SH-2s read the cartridge too, and the older Mega Drive boards needed rewiring to work at all [32X-TI items 1-3, 18; [ROM](../megadrive/cartridge.md#rom)].
- **A development system in the console.** Cross Products' SNASM box replaced the cartridge with 1 MB of RAM and gave the program debugger services over SCSI [SNASM]. Such systems can behave unlike a production console: Sega's Mega Drive Super Target acknowledged accesses to unmapped addresses that would hang a production machine, and Sega's advice was to remove the chip that did it [MD-TB #15].
- **A flash cartridge.** The usual route today. None of this book's sources documents how any particular flash cart maps a 32X image, especially one over 16 Mbit, with save RAM, or with the `SEGA SSF` mapper ([Real cartridges, development boards and flash carts](large-cartridges.md#real-cartridges-development-boards-and-flash-carts)). Treat the cart as part of the test setup and record which one you used.

Whatever the route, start with the smallest program that proves the chain works. The [hello world ROM](32x-hello.md) checks the header, Sega's initial program, the boot ROMs' copy and both SH-2s in one screen, and its expected picture is known from two emulators.

## Which console

Results can depend on the machine. What the sources record:

- **The 32X's interface chip came in two speeds.** Production units carry either the 315-5818 or the faster 315-5818A. On the 5818, communication between the 68000 and the SH-2s occasionally goes wrong, and Sega asked for final checks on a 5818A unit [32X-TI item 11]. A test of the communication ports means more on a 5818.
- **Production units look and sound different from development targets.** From target version 3.0, production units use a different video encoder and filter, with more vivid colour and less blur, and the balance between FM and PWM sound was changed. Sega asked for the final graphics check on a production unit [32X-TI items 20, 21].
- **Some faults depend on the individual Mega Drive.** The hazard when the Z80 writes the PSG with its bank window on the cartridge or frame buffer occurs "at very different frequencies" from one console to another, so a test that passes on one machine proves little [32X-TI item 22; [Sound](../megadrive/sound.md#the-rules)].
- **Mega Drive revisions differ in detail.** Later consoles carry a version number in `$A10001` and need the TMSS write ([I/O](../megadrive/io.md#the-version-register)). The original model sends stereo only to its headphone socket [MD-SWM, FM sound source overview]. Whether the later VDPs handle byte writes the same way is an open question ([The VDP](../megadrive/vdp.md#open-questions)).

So record, with every result: the Mega Drive's model and region, its version number from `$A10001`, the TV standard, the 32X's region and, if the case is opened, its interface chip; the cartridge or flash cart and its firmware; and the MD5 of the ROM that ran.

## Designing a test that reports itself

A console has no debugger attached. The test has to show its own result, and the result has to mean something on its own.

Sega's Mars Check Program, a 32X diagnostic cartridge, is a good model [MARS-CHECK]:

- **One question per test, with a name.** Each test prints a line such as `DREQ CONTROL REGISTER R/W OK` or `… ERROR`, and keeps an error count.
- **On failure, the evidence.** The failing address, the value written and the value read are printed, so one photograph holds the whole result.
- **The expected value is in the test, with a range where timing varies.** Its interrupt tests count interrupts over 30 frames and accept a band around the expected count, wide enough for the console's tolerances and narrow enough to catch a wrong setting ([0x20004000: interrupt mask](../32x/registers.md#0x20004000-interrupt-mask)).
- **Time limits everywhere.** Every wait has a time-out, so a broken console produces an `ERROR` line instead of a hang.
- **Both CPUs take part.** The 68000 sends each SH-2 test a command through the communication ports and reads back `OK` or `ERR` ([Disassembling and annotating a commercial game](reverse-engineering.md#worked-example-one-test-both-cpus)).

Four more habits, from the reference projects:

- **Count, don't watch.** A test that counts events over a known number of frames, or times a loop with the SH-2's free-running timer or the Mega Drive's H counter, gives a number. A test you watch gives an impression ([Timers](../sh2/timers.md); [Timing, interrupts and counters](../megadrive/vdp-timing.md)).
- **Run it in both emulators first.** Write down what PicoDrive and ares show for the same ROM. A console result that matches neither is the finding; a test that already fails in both is a broken test ([Two emulators, two jobs](emulator-testing.md#two-emulators-two-jobs)).
- **Build a control.** A second ROM without the instrumented part, built from the same source, shows whether a failure belongs to the test or to the setup ([When a run fails](emulator-testing.md#when-a-run-fails)).
- **Photograph, don't transcribe.** Colours, alignment and numbers all survive a photograph. Plan how the result reaches the screen before going to the bench: a test whose result sits in work RAM is unreadable without a way to read work RAM <span class="tag emulator">emulator</span> [AU-NOTES, HARDWARE_TESTS].

And Sega's diagnostic itself is a ready-made test: run on a production console, its register tests would show directly whether the console agrees with Sega's 1994 expectations, such as bit 1 of the DREQ control register ([discrepancy 25](../appendices/discrepancies.md)).

## The checklist

These are the questions where a console result would change code or settle a disagreement between sources. Each links to where it is discussed; the test is a sketch.

### Start-up and the cartridge

| Question | Test | Where |
|----------|------|-------|
| Does reset clear ADEN, so the 68000 restarts through the cartridge's own vectors? | Show a different colour from each restart path, press reset | [Boot](../32x/boot.md#open-questions) |
| Does `$880000-$9FFFFF` still answer while RV = 1? | Read a known byte with RV = 1 from code in work RAM, compare | [The RV bit](../32x/architecture.md#the-rv-bit) |
| What happens when a game over 16 Mbit skips Sega's initialisation? | Read markers above `$200000` with and without the sequence, on a real cartridge | [Hardware bugs](../32x/bugs.md#cartridges-over-16-mbit) |
| What does a retail cartridge return past its header's end? | Read past the end from the SH-2's cache-through window | [Using more cartridge space](large-cartridges.md#how-big-is-the-cartridge) |
| What is RES at power-on, and what does REN report? | Print `$A15100` before and after the initial program | [Discrepancy 30](../appendices/discrepancies.md) |

### Registers and interrupts

| Question | Test | Where |
|----------|------|-------|
| Is bit 1 of the DREQ control register stored and visible to the SH-2? | Sega's own test: write 0-7 to `$A15107`, SH-2 echoes `0x20004007` | [Discrepancy 25](../appendices/discrepancies.md) |
| What do bits 15-14 of `0x20004006` report? | Read them while writing the frame buffer at full speed, and while idle | [Discrepancy 32](../appendices/discrepancies.md) |
| Do INTM and INTS clear themselves? | Raise CMD, let the SH-2 clear its source, read `$A15103` | [Discrepancy 11](../appendices/discrepancies.md) |
| How often does the SH-2 interrupt flaw strike? | Run a heavy interrupt load without the TOCR workaround and count lost interrupts | [Interrupt controller](../sh2/intc.md#open-questions) |
| How many H interrupts per NTSC frame with HEN = 1: 256 or 262? | Count over 30 frames, as Sega's test does | [0x20004000](../32x/registers.md#0x20004000-interrupt-mask) |
| Do V, H and PWM interrupts raised while masked stay pending? | Mask, wait a frame, unmask, count | [Hardware bugs](../32x/bugs.md#open-questions) |

### Speed

| Question | Test | Where |
|----------|------|-------|
| How deep is the frame buffer write buffer? | Time runs of 1 to 8 stores with the free-running timer | [Discrepancy 4](../appendices/discrepancies.md) |
| Is a longword access to a 16-bit area one bus cycle or two? | Time *n* longword frame buffer reads against 2*n* word reads | [Bus state controller](../sh2/bsc.md#open-questions) |
| How long does an auto fill take? | Time a 256-word fill until FEN clears | [The 32X VDP](../32x/vdp.md#open-questions) |
| How much do the two SH-2s slow each other? | Time one SH-2's SDRAM loop with the other idle, then busy | [Splitting work across three CPUs](../patterns/cpu-split.md#open-questions) |
| How many waits does the 68000 see on the cartridge while the SH-2s read it? | Time a 68000 loop from the cartridge, with the SH-2s idle and then reading ROM | [Access timing](../32x/timing.md#open-questions) |

### Communication and the FIFO

| Question | Test | Where |
|----------|------|-------|
| What does a port read return while the other side writes it? | Write alternating patterns from one side, check every read on the other for mixtures | [Communication](../32x/communication.md#open-questions) |
| What happens when the 68000 writes the FIFO while FULL? | Fill it with no DMA armed, write more, then drain and compare | [DREQ and the FIFO](../32x/fifo.md#open-questions) |
| Does a FIFO transfer stall and leave FULL stuck? | Long repeated transfers with a time-out and a counter of stalls | [Discrepancy 29](../appendices/discrepancies.md) |
| Is `tas.b` safe on SDRAM with both SH-2s contending? | Both CPUs increment a shared counter under a `tas.b` lock; check the total | [Discrepancy 12](../appendices/discrepancies.md) |

### Picture and sound

| Question | Test | Where |
|----------|------|-------|
| What does H32 look like under a visible 32X layer? | A test card in both widths, photographed | [Discrepancy 26](../appendices/discrepancies.md) |
| Which Mega Drive pixels let the 32X through? | Use the backdrop's palette entry inside a tile | [Discrepancy 27](../appendices/discrepancies.md) |
| Does PWM keep draining with both outputs off, and what does bit 4 of its control register do? | Watch the FIFO flags with outputs off; listen with bit 4 set | [Discrepancies 23, 31](../appendices/discrepancies.md) |
| Where does a Mega Drive DMA source wrap: 64 KB or 128 KB? | DMA across a boundary from a marked source | [Discrepancy 13](../appendices/discrepancies.md) |
| Does the YM2612's CSM bit exist? | Set it and listen for the timer-driven key-on | [Discrepancy 36](../appendices/discrepancies.md) |

Every chapter's own open-questions section lists the rest.

## Recording a result

When a test runs on a console, write it back where the question lives:

1. Change the claim's tag to <span class="tag tested">tested</span>, with the console model and revision, and link the test ROM if there is one ([Conventions](../conventions.md)).
2. If the result settles a discrepancy, record it in that row's last column ([Where the docs disagree](../appendices/discrepancies.md)).
3. If it disagrees with an emulator, add it to that chapter's "In emulators" section, so the next person knows which emulator to trust for it.
4. Keep the photograph and the ROM's MD5 with the result.

## What to take away

- Nothing in this book is confirmed on a console yet; every result you add moves a claim from <span class="tag emulator">emulator</span> or <span class="tag manual">manual</span> to <span class="tag tested">tested</span>.
- Record the console, the 32X's interface chip if you can, the cartridge or flash cart, and the ROM's MD5 with every result.
- Make tests report themselves on screen, with names, expected values, ranges and time-outs, as Sega's own diagnostic does.
- Run every test in both emulators first, and build a control.
- Start with the hello world ROM, then the checklist.

## Open questions

- How does each flash cart in common use map 32X images over 16 Mbit, with save RAM and with `SEGA SSF`?
- Which production 32X units carry the 315-5818 and which the 5818A, and can software tell them apart?
- Do Mega Drive model differences affect the 32X: the later VDPs, the TMSS models, the version numbers in `$A10001`?

## Sources

- [32X-TI](../appendices/bibliography.md#32x-ti): items 1-3, 11, 18, 20-22
- [MD-TB](../appendices/bibliography.md#md-tb): bulletin #15
- [MD-SWM](../appendices/bibliography.md#md-swm): FM sound source overview
- [SNASM](../appendices/bibliography.md#snasm): console notes
- [MARS-CHECK](../appendices/bibliography.md#mars-check): test structure and messages
- [AU-NOTES](../appendices/bibliography.md#au-notes): HARDWARE_TESTS
