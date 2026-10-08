# 68000 and SH-2 communication

The 68000 and the two SH-2s have no memory in common. The 68000 cannot see the SH-2s' SDRAM, and the SH-2s cannot see the Mega Drive's work RAM [32X-HWM §2.2; see [who can reach what](architecture.md#who-can-reach-what)]. Everything the three CPUs say to each other goes through a handful of meeting points. The most important are eight 16-bit registers that all three can read and write. This chapter covers those registers, the one interrupt the 68000 can send the other way, and the patterns that keep both working. It closes with the extra channels the two SH-2s have between themselves.

## What the CPUs share

| Channel | Who | Direction | Size | Good for |
|---------|-----|-----------|------|----------|
| Communication ports, `$A15120-$A1512F` | 68000, both SH-2s (and the Z80, see below) | Any | 8 words | Commands, small arguments, status, handshakes |
| CMD interrupt, `$A15102` | 68000 → Master and/or Slave | One way | 1 bit per SH-2 | Waking or stopping an SH-2 without it polling |
| DREQ FIFO | 68000 → SH-2 DMA channel 0 | One way | Any length | Bulk data from the Mega Drive side. See [DREQ and the FIFO](fifo.md) |
| Frame buffer | Whoever holds FM | Either way, one side at a time | 128 KB | Bulk data, especially results going back to the 68000 |
| Cartridge ROM | All three | Read only | Up to 4 MB | Shared constant data |
| SDRAM | Both SH-2s | Any | 256 KB | Everything between the two SH-2s |
| Serial link (SCI) | Master ↔ Slave | Either way | Bytes | Rarely used; see [below](#between-the-two-sh-2s) |

There is no interrupt from an SH-2 to the 68000 <span class="tag manual">manual</span> [32X-HWM §3.3 p.67]. Anything an SH-2 wants the 68000 to know, the 68000 has to find by reading.

## The communication ports

### Addresses and names

The eight words are the same registers seen from both sides [32X-HWM §3.2 pp.23, 31]:

| 68000 | SH-2 | Word number | Toolchain name | Used at boot |
|-------|------|-------------|----------------|--------------|
| `$A15120` | `0x20004020` | 0 | `COMM0` | `M_OK`, first half |
| `$A15122` | `0x20004022` | 1 | `COMM2` | `M_OK`, second half |
| `$A15124` | `0x20004024` | 2 | `COMM4` | `S_OK`, first half |
| `$A15126` | `0x20004026` | 3 | `COMM6` | `S_OK`, second half |
| `$A15128` | `0x20004028` | 4 | `COMM8` | Checksum from the Master; `SLAV` in Sega's sample |
| `$A1512A` | `0x2000402A` | 5 | `COMM10` | Second half of the above |
| `$A1512C` | `0x2000402C` | 6 | `COMM12` | — |
| `$A1512E` | `0x2000402E` | 7 | `COMM14` | — |

The registers have no official names, and two numbering schemes are in use:

- **By word.** Sega's register tables call them COMM0 to COMM7 [32X-INTRO, communication port; 32X-OV, communication port], and the manual's own description puts `S_OK` in "the 2nd and 3rd words", counting from 0 [32X-HWM §3.3 p.67]. The Virtua Racing Deluxe and Aerobiz Ultimate notes use this scheme [VRD-NOTES; AU-NOTES].
- **By byte offset from `$A15120`.** Sega's boot flowchart and sample code say comm0, comm4 and comm8 [32X-HWM §5.1; 32X-TIA1, 68000 and SH-2 samples]. The 32XDK, marsdev and d32xr headers follow it, with names from `COMM0` to `COMM14` [32XDK; MARSDEV, 32x-skeleton mars.h; D32XR, 32x.h].

So "COMM4" means `$A15128` in one project and `$A15124` in the next, and that kind of mix-up has hung a cartridge at boot before (see [the handshake](boot.md#the-handshake-into-your-code)). This book always gives the address. When it quotes a project, it turns the project's name into an address.

### What the boot leaves there

At the end of the boot, the Master has written `M_OK` at `$A15120`, the Slave has written `S_OK` at `$A15124`, and the Master has posted the cartridge checksum at `$A15128`. The 68000 clears the first two to release the SH-2s [32X-HWM §5.1; see [the boot chapter](boot.md#the-handshake-into-your-code)]. After that, all eight words belong to your program [32X-HWM §3.3 p.67]. Two cautions:

- Sega's own startup sample has the Slave write `SLAV` at `$A15128` and the Master wait for it before going on [32X-TIA1, SH-2 sample]. If you copy that startup, the word is busy until the Master has seen it.
- Sega's 1994 sound development plan reserved two words for its PWM sound driver: one for the game's sound requests and one for the driver's own handshake between the SH-2 and the 68000 [32X-INTRO, 32X sound development environment]. Using that driver means giving up those two words.

### Access rules

- **Sizes.** Byte and word access are listed for both sides [32X-HWM §3.2 pp.23, 31]. Sega's own boot code reads and writes the words in pairs as longwords [32X-TIA1], so longword access works, but nothing makes it a single operation. The 68000 has a 16-bit data bus, so a longword is two separate word cycles, and a reader on the other side can see one new word and one old one. Compare a longword only when a half-written value cannot pass for a real one, as with `M_OK`.
- **Speed.** The 68000 reads and writes them with no wait states. The SH-2 needs one wait state per access <span class="tag manual">manual</span> [32X-HWM §4.4; 32X-HWI item 3]. That makes them the cheapest shared memory on the machine.
- **From the SH-2, use the cache-through address.** `0x20004020`, never `0x00004020`, or the SH-2 may read a stale cached copy [32X-HWM §4.1 p.74; SH7604 §8.5.3].
- **FM does not affect them.** FM decides who owns the VDP registers, the frame buffer and the palette [32X-HWM §4.1 p.74, VDP access competition]. The communication ports are system registers, so either side can use them whatever FM says <span class="tag manual">manual</span>. Aerobiz Ultimate depends on this: the 68000 hands the frame buffer to the SH-2 and then waits for its answer through the ports [AU-NOTES, disasm/32x/sh2_lz.asm].
- **The Z80.** The manual marks the ports as reachable from the Z80 [32X-HWM §4.1, Table 4.1], but a later bulletin says Z80 writes to `$A15100-$A153FF` lock up the 68000 on production units <span class="tag disputed">disputed</span> ([discrepancy 5](../appendices/discrepancies.md)). Leave the ports to the 68000 and the SH-2s.

## The one hazard: a word that changes while you read it

The manual's rule is short. If both sides write the same word at the same moment, the word's value is undefined. The same is true if one side writes it while the other is reading it <span class="tag manual">manual</span> [32X-HWM §3.3 p.67; §3.2 p.23]. Reading and reading is the only safe overlap.

The next sentence in the English manual says that dividing the registers into SH-2 → 68000 and 68000 → SH-2 "must be avoided". That contradicts the rule just before it, which is an argument *for* giving each direction its own words. It reads like a translation slip. Every working protocol in the sources does the opposite: it gives each word a clear owner at every moment.

"Undefined" here means a read can return neither the old value nor the new one. Sega also warned that on boards with the slower 315-5818 interface chip, errors in communication between the 68000 and the SH-2s happen occasionally. It asked developers to do final checks on boards with the 315-5818A <span class="tag manual">manual</span> [32X-TI item 11]. Both chips shipped, so code has to survive the occasional bad read.

Three rules cover it:

1. **One writer at a time per word.** Either a word always has the same writer (status the SH-2 posts, a state the 68000 sets), or ownership passes with its value. A command word is written by the 68000 only while it reads 0, and by the SH-2 only while it is not 0. VRD's notes describe this as "the 68000 sets, the SH-2 clears" [VRD-NOTES, analysis/COMM_REGISTERS_HARDWARE_ANALYSIS.md].
2. **Write the data first and the signal last, in a different word.** The reader only reads the data once the signal says it is complete. The signal word is then the only word ever read while it is being written.
3. **When a wrong value would do damage, read twice.** Aerobiz Ultimate reads every word written by the other side twice and acts only when both reads agree [AU-NOTES, disasm/sh2/master/rpc.c] <span class="tag emulator">emulator</span>. This is cheap: one extra access at one wait state.

One more SH-2 detail. Its bus controller has a one-entry write buffer, so a store to a port can still be on its way after the next instruction has started. Reading the same address back makes the CPU wait until the write is done [SH7604 §7.11.2]. Without the read, the other side just sees the value a few cycles later, which is harmless in a polling protocol. It matters when the SH-2 must not go on until the other side can see the value, for example before an `rte` (see [the CMD interrupt](#the-cmd-interrupt)).

## A mailbox that works

Most programs need one thing from the ports: the 68000 asks an SH-2 to do a job and waits for the answer. This version follows the three rules. It uses `$A15120` as the command word and `$A15122` as the argument.

```asm
; 68000: run SH-2 command d0.w (not 0) with argument d1.w; wait for it
Sh2Call:
        move.w  sr,-(sp)
        ori.w   #$0700,sr        ; no interrupt handler may use the mailbox now
.idle:  tst.w   $A15120          ; wait for any previous command to finish
        bne.s   .idle
        move.w  d1,$A15122       ; argument first
        move.w  d0,$A15120       ; command word last: this is the doorbell
.busy:  tst.w   $A15120          ; the SH-2 clears it when the work is done
        bne.s   .busy
        move.w  (sp)+,sr
        rts
```

```c
/* SH-2: serve commands from the 68000 */
#define COMM_CMD (*(volatile unsigned short *)0x20004020)
#define COMM_ARG (*(volatile unsigned short *)0x20004022)

for (;;) {
    unsigned short cmd = COMM_CMD;
    if (cmd == 0 || cmd != COMM_CMD)   /* idle, or caught mid-write */
        continue;
    run_command(cmd, COMM_ARG);         /* argument was written before cmd */
    COMM_CMD = 0;                       /* "done" is written after the work */
}
```

What each detail is for:

- **Interrupts are masked on the 68000** for the whole call. If a V-Blank handler could also call `Sh2Call`, it would overwrite the argument of the call it interrupted. Aerobiz Ultimate masks them for exactly this reason [AU-NOTES, disasm/32x/sh2_lz.asm].
- **Clearing the command word is the reply.** The SH-2 clears it only after the work is done, so a cleared word always means "finished". Clearing it as soon as the command is read would tell the 68000 the job was done while it was still running. Aerobiz Ultimate found the opposite mistake too: a handler that returned without clearing its word was dispatched again on the next pass, and every later command queued behind it. The fix was to clear on every path out of every handler, including handlers that block [AU-NOTES, KNOWN_ISSUES.md] <span class="tag emulator">emulator</span>.
- **Results come back the same way**, in words the SH-2 writes before it clears the command word. Aerobiz Ultimate passes two longword arguments in `$A15124-$A1512B` and reads results back from the same words [AU-NOTES, disasm/sh2/master/rpc.c].

### Let the sender go early

Waiting for the work to finish is often unnecessary. The 68000 only needs to know the SH-2 has *copied the arguments*, so the words can be reused. The Virtua Racing Deluxe rework splits the command word in two:

1. The 68000 waits for the high byte of `$A15120` to read 0.
2. It writes all the arguments, then the command index into the low byte and a non-zero trigger into the high byte, last.
3. The Master copies the arguments into its registers and clears the low byte. That means "arguments taken", and the 68000 can return now.
4. When the work is done, the Master clears the high byte.

This cut one command from about 300 to about 170 68000 cycles per call, and another from about 350 to about 100 <span class="tag emulator">emulator</span> [VRD-NOTES, analysis/68K_SH2_COMMUNICATION.md]. The original game's protocol waited three times for each command.

### Repeating a command: sequence numbers

A receiver that acts when a word *changes* cannot see the same request twice in a row. "Play sound 5" followed by "play sound 5" leaves the word unchanged. Homebrew sound drivers fix this by putting a 7-bit counter in the high byte and the sound number in the low byte. The sender adds 1 to the counter for each request, and the receiver acts whenever the counter differs from the last one it saw [S32X-SKILL, references/audio.md]. The sender does a single store and never waits, so this suits requests sent while the game is in the middle of a picture. The cost is that a request is lost if a second one is written before the receiver has read the first. That is fine for sound effects, but not for anything that must happen.

### State, not commands

Some things are not requests but a state the other side should follow, such as "the map is on". Aerobiz Ultimate keeps these in a word that only the 68000 writes and the SH-2 checks on every pass, instead of sending a command [AU-NOTES, disasm/sh2/master/rpc.c]. A word like that can be changed from the 68000's V-Blank handler without disturbing a command in progress, because it is never part of the command handshake.

The SH-2 answers in its own status word. That answer carries a 4-bit generation number that the 68000 increases every time it turns the map on. A "map drawn" reply left over from the previous visit then cannot be mistaken for this one's <span class="tag emulator">emulator</span>.

Mortal Kombat II takes this to its limit: once a frame the 68000 sends the Master a 668-byte snapshot of everything it needs to draw, including the camera position, the mode, the text to show and the sprite records. The Master never receives a "draw this" command, only the state of the world [MK2, 68000 code at `$00DD9C`, `$00DFAA`]. How the block travels is in [Bulk data through the ports](#bulk-data-through-the-ports).

Homebrew also uses a heartbeat: one word the SH-2 increases on every pass through its main loop. If the word stops changing, that SH-2 has crashed, which a test harness can check [S32X-SKILL, references/audio.md].

### Never wait forever

An SH-2 that has crashed never clears its word, and a plain polling loop then hangs the game. Aerobiz Ultimate counts down while waiting (400,000 passes). If the SH-2 has not answered by then, it does the job with the original 68000 routine, so a screen loads slowly instead of not at all [AU-NOTES, disasm/32x/sh2_lz.asm]. A timeout also has to put the protocol back in a known state. The SH-2 may still answer later, so the timeout path writes an "exit" word before falling back, and an SH-2 that wakes up late then knows to give up [AU-NOTES, KNOWN_ISSUES.md] <span class="tag emulator">emulator</span>.

Test those paths on Ares or on a console, not on PicoDrive. PicoDrive watches for a 68000 that reads a port 11 times with less than 64 cycles between reads, and stops the 68000 until an SH-2 writes a port [PICODRIVE, pico/32x/memory.c]. Under PicoDrive the countdown never runs out, and a timeout path can be broken without anyone noticing <span class="tag emulator">emulator</span> [AU-NOTES, KNOWN_ISSUES.md].

The SH-2 side can guard itself too. After Burner Complete's Master waits for work in its main loop with a count of 1,500,000 passes. If the count runs out, it masks interrupts, writes 0 to `$A15120`'s busy byte, clears its CMD request, and goes back to waiting. A CMD that was lost, or a busy byte left set by a call that went wrong, therefore cannot leave the 68000 spinning for ever [AB32X, SH-2 code at `0x060038E6`-`0x06003910`].

### Keep command numbers apart

When two protocols share a word, a value from one gets read as a command of the other. The Virtua Racing Deluxe rework added a doorbell for the Slave at `$A1512E`. Writing ordinary game command numbers there triggered Slave handlers that had never been set up, and the game crashed [VRD-NOTES, analysis/68K_SH2_COMMUNICATION.md]. In homebrew, a Slave job number written into the word that also carries `S_OK` released the Slave before FM had been handed over, and it wrote over the VDP registers [S32X-SKILL, references/architecture.md].

Keep a written map of which word belongs to which protocol. If two protocols really must share a word, give them separate value ranges. d32xr does this with `$A15124`: the Master sends Slave jobs there as small numbers, and the Slave sends requests to the 68000 there as values above `$1600`. The 68000 ignores everything at or below `$1600` [D32XR, src-md/crt0.s; mars.h].

### Who asks whom

The examples so far have the 68000 giving the orders, which is how Virtua Racing Deluxe and Aerobiz Ultimate work [VRD-NOTES; AU-NOTES]. d32xr reverses it. The SH-2s run the game, and the 68000, running from work RAM, is a server. Its main loop reads `$A15120` for requests from the Master and `$A15124` for requests from the Slave. The high byte indexes a table of 47 entries for services such as save RAM, music, sound effects, copies to the Mega Drive VDP and CD access, and the 68000 writes 0 when it is done [D32XR, src-md/crt0.s]. On the SH-2 side each request is three lines: wait for 0, write the request, wait for 0 again [D32XR, marshw.c].

Either arrangement works. The deciding question is which CPU owns the main loop. The 68000 still has to do anything that touches Mega Drive hardware: the pads, the Z80, the Mega Drive VDP and save RAM.

### Bulk data through the ports

The ports can carry more than commands, if both sides take turns. Mortal Kombat II moves its 668-byte state block every frame this way, ten bytes at a time, without the FIFO [MK2, 68000 code at `$00DFAA`; SH-2 code at `0x060003F4`]:

1. The 68000 writes 2 to `$A15120` and 1 to `$A15122`, then raises CMD on the Master.
2. The Master's CMD handler writes 2 to `$A15122` to say it is ready.
3. The 68000 sees the 2, writes 1 to `$A15120`, puts the next five words in `$A15124`-`$A1512C`, and writes 2 to `$A15120`.
4. The Master copies the five words into SDRAM and writes 1 to `$A15122`, then waits for the next 2, and so on.
5. A short last step carries the remainder (668 is not a multiple of ten).

That is 67 round trips, with both CPUs waiting on each other at every step. By instruction count the 68000's loop needs at least 130 of its clocks per step, about 8,700 a frame or 7% of its time, and the Master sits in its interrupt handler for the same stretch. A few hundred bytes a frame is about the limit for this method. For more, the [FIFO](fifo.md) moves data without the SH-2 taking part.

The same game's sound requests go the other way round: fire and forget. The 68000 writes the sample number with bit 8 set into `$A1512E`, and the Slave, polling that word, takes the number and clears the word. The 68000 never checks that the previous request was taken, so two requests in the same few microseconds keep only the second [MK2, 68000 code at `$00E01A`; SH-2 code at `0x06005178`].

### One call per object

After Burner Complete does the opposite of sending one block: it makes a call for every object in the scene, and waits for each answer [AB32X, 68000 code at `$887348`-`$8873BC`; SH-2 code at `0x0600257C`, `0x0600371C`]:

1. The 68000, with interrupts masked, writes the object's parameters into the ports and into the FIFO's unused source, destination and length registers ([DREQ and the FIFO](fifo.md#registers)).
2. It writes `$010F` to `$A15120`: a busy byte, and command 15 in the low byte. Then it raises CMD on the Master.
3. The Master's CMD handler projects the object onto the screen and, if it is visible, adds it to the list it will draw. It writes −1 to `$A15124` if the object is off screen, or results to `$A15128`, then clears CMD and writes 0 to `$A15120`.
4. The 68000, spinning on `$A15120`'s busy byte, reads the answer back into its object.

The game sends about 75 objects per picture, up to 87, at 30 pictures a second. The Master does the multiplying and dividing, which the 68000 is slow at, and the 68000 gets back what it needs for its own game logic (whether the object is visible). The price is a round trip per object: in PicoDrive the 68000 spends about 12% of its time spinning for answers <span class="tag emulator">emulator</span> [AB32X, watch log of the object rings and per-PC profile over 2,000 frames of play]. PicoDrive cuts polling loops short, so the real figure is probably higher. Compare [When moving a job pays](../patterns/cpu-split.md#when-moving-a-job-pays).

Its sound requests use CMD too, on the Slave, and wait for the answer. In its H-interrupt handler the 68000 takes the Z80's bus, collects a request the Z80 left in its RAM, and sends it to the Slave as `$0203` in `$A15122`, with CMD raised through bit 1 of `$A15102`. It then sends `$0200`, the tick that steps the Slave's music sequencer, waiting for `$A15122`'s high byte to clear after each [AB32X, 68000 code at `$88091E`; SH-2 code at `0x06000684`].

## The CMD interrupt

The 68000 can raise an interrupt on either SH-2 [32X-HWM §3.2 pp.20, 26, 28; §3.3 p.67]:

| Register | Side | Bits | Meaning |
|----------|------|------|---------|
| `$A15102` interrupt control | 68000 | bit 0 INTM, bit 1 INTS | Write 1 to raise CMD on the Master (INTM) or the Slave (INTS) |
| `0x20004000` interrupt mask | SH-2, one copy per CPU | bit 1 CMD | 1 lets CMD through, 0 masks it (0 at reset) |
| `0x2000401A` CMD interrupt clear | SH-2, one copy per CPU | any word write | Clears this CPU's CMD request |

CMD arrives at interrupt level 8, below VRES (14), V (12) and H (10) and above PWM (6) [32X-HWM p.69]. The SH-2's status register mask must be below 8 for it to be taken.

CMD behaves differently from the other four 32X interrupts. While masked, it is not presented to the SH-2 at all. If it is still pending when the SH-2 unmasks it, it is presented again then <span class="tag manual">manual</span> [32X-HWM §3.2 p.29, points to be aware of]. So a CMD raised while the SH-2 has it masked is delayed, not lost. A handler must still not count on the request being presented again once it is running.

What happens to INTM and INTS afterwards is uncertain:

- The scanned manual says they clear themselves "if SH2 does not interrupt clear" [32X-HWM §3.2 p.20].
- The 32X Overview says they clear when the SH-2 clears the interrupt [32X-OV, interrupt control register].
- PicoDrive follows the Overview: a write to `0x2000401A` drops the matching bit at `$A15102` [PICODRIVE, pico/32x/memory.c].
- The Virtua Racing Deluxe rework waits for INTM to read 0 before raising it again [VRD-NOTES, disasm/modules/68k/sh2/vr60_1p_staging_hook.asm].
- Shipped code waits the same way. After Burner Complete and Knuckles' Chaotix poll the bit until it reads 0 [AB32X, 68000 code at `$000926`; CHAOTIX, `$0019BE`], and Sega's Mars Check Program reports an SH-2 timeout if it has not cleared within 600 frames [MARS-CHECK, `$0022D2`]. Every CMD handler in these programs writes `0x2000401A`, so they rely on the bit clearing once the SH-2 has acknowledged the interrupt, never on a clear without it.
- notaz's console test sets INTM while both SH-2s have CMD masked and reads 1 back, then reads 0 once the Master has unmasked CMD and its handler has run [TESTPICO, t_32x_irq_cmd]. It does not wait long with CMD masked.

This is <span class="tag disputed">disputed</span> ([discrepancy 11](../appendices/discrepancies.md)). The 32X-OV reading is very likely, but until a console test settles it, always write `0x2000401A` in the handler, and do not take INTM reading 0 as proof that the handler has finished. Confirm through a port, as d32xr does (below). A second CMD raised before the first was cleared simply merges with it.

A CMD handler has the same duties as any 32X interrupt handler:

1. Apply Sega's fix for the SH-2's interrupt bug, a write to the free-running timer's output control register, at the start of the handler [32X-SUP2; see [hardware bugs](bugs.md)].
2. Clear the request with a write to `0x2000401A`.
3. Make sure the clear has reached the hardware before `rte`: read the same address back, or leave at least a few instructions between the clear and the return. Otherwise the same request fires again <span class="tag manual">manual</span> [32X-SUP2; 32X-HWM p.89 item 5; SH7604 §5.7].

Sega's sample vector table points levels 8 and 9 at the same CMD handler, because the interrupt bug can deliver a neighbouring vector [32X-TIA1].

### Using CMD to stop the SH-2s

The one thing polling cannot do is reach an SH-2 that is busy with something else. d32xr uses CMD to stop both SH-2s whenever the 68000 needs the cartridge to itself, for save RAM or a bank switch [D32XR, src-md/crt0.s; crt0.s]:

1. The 68000 writes 3 to `$A15102`, raising CMD on both SH-2s.
2. Each SH-2's handler saves its mailbox on its stack (`$A15120` and `$A15122` for the Master, `$A15124` for the Slave). It then writes `$A55A` into its first word and waits.
3. The 68000 waits until it reads `$A55A` in both words. Both SH-2s are now spinning inside their handlers, in code that runs from SDRAM.
4. The 68000 does its work, here setting RV, which takes the cartridge away from the SH-2s.
5. It writes `$FFFE` into both words. Each handler sees it, puts back the word it overwrote, and returns.

The save and restore are the clever part: CMD can arrive in the middle of an ordinary mailbox exchange, and the interrupted code finds the words as it left them. The Master's handler also accepts other values in place of `$FFFE`, as small commands. The 68000 sends pad readings this way: it raises CMD, puts the value in `$A15122` and a code in `$A15120`, and waits for each to be acknowledged [D32XR, src-md/crt0.s; marshw.c]. The full save RAM sequence is in [Save RAM on the 32X](../megadrive/cartridge.md#save-ram-on-the-32x).

While an SH-2 is stopped this way, nothing it runs may touch the cartridge: not its code, not its data, not a DMA, and no other interrupt handler [D32XR, marshw.h]. That is why the waiting loop must already be in SDRAM.

## Polling or interrupts?

| | Polling a port | CMD interrupt |
|---|---|---|
| Direction | Any | 68000 → SH-2 only |
| Cost to the receiver | Bus accesses while it waits | None until it fires; one handler entry when it does |
| Delay | Up to one pass of the polling loop | Interrupt entry, as long as nothing at level 8 or above is running |
| Carries data | Yes | No, only "look now"; data still goes through the ports |
| Pitfalls | Wasted time, contention on the bus | The INTM question above, the interrupt bug, and handlers that run in the middle of other code |

Polling is the default in the sources: Virtua Racing Deluxe (as its disassembly project describes it), Aerobiz Ultimate and the SH-2 side of d32xr all poll [VRD-NOTES; AU-NOTES; D32XR]. Mortal Kombat II uses CMD for its Master, which takes the state block in the CMD handler, and polling for its Slave [MK2, SH-2 code at `0x060003F4`, `0x06005178`]. Star Wars Arcade uses both. Its Master is driven by CMD: the handler flips TOCR, takes a command number from the first byte of `$A15120`, runs that command, clears CMD, and zeroes the byte to say it has finished. Its Slave polls its own byte of `$A15122` [SWA, SH-2 code at `0x06001074`, `0x06000744`]. After Burner Complete drives both SH-2s with CMD and polls with neither: its Master runs each command inside the handler, and its Slave's main loop mixes sound until a CMD brings a request [AB32X, SH-2 code at `0x060022EC`, `0x06000684`].

A polling SH-2 is not free, though. Both SH-2s share one external bus, and the Slave has to get the Master's permission for every access it makes [32X-HWM §2.2]. So a Slave reading a port in a tight loop takes bus time from a Master that is drawing. Star Wars Arcade's Slave, when it finds no command, runs a 100-pass delay loop before reading again, which leaves the bus alone [SWA, SH-2 code at `0x06000750`]. The project's copy of Virtua Racing Deluxe does the same with 64 passes [VRD-NOTES, disasm/sh2/3d_engine/slave_command_dispatcher.asm]. Mortal Kombat II's Slave does not: its main loop reads `$A1512E` back to back, and its real work happens in the PWM interrupt. Every one of those reads is a bus cycle the drawing Master has to share [MK2, SH-2 code at `0x06005178`]. The manual forbids the SH-2's `sleep` instruction in games, so a delay loop is the only way to wait cheaply [32X-HWM §5.3 p.87].

On the 68000 side, a protocol that does not have to answer at once can check the ports once per frame in the V-Blank handler instead of spinning.

## Between the two SH-2s

The two SH-2s share everything on the 32X side, so they have more options than the 68000 does.

- **The same ports.** Port accesses skip the cache by nature, so they need no cache maintenance. d32xr runs its Master → Slave jobs through `$A15124` (the job number) and `$A15126` (an argument). During wall drawing, the two bytes of `$A15126` become progress counters: the Master adds 1 to the first byte for each wall it finds, and the Slave adds 1 to the second for each wall it has prepared [D32XR, mars.h; r_phase2.c]. The two SH-2s reach the ports over the same bus, one access at a time, so they cannot collide the way the 68000 and an SH-2 can. That is presumably why d32xr can let them write different bytes of one word.
- **A spare 32X register.** Knuckles' Chaotix never turns on the H interrupt, so the SH-2s' H count register at `0x20004004` has no other use. Its low byte is the Master's command to the Slave: the Master writes 2 to have the frame buffer cleared, carries on with its own work, and later waits for the Slave to write 0 back [CHAOTIX, SH-2 code at `0x060002D4`-`0x060002E8`, `0x06004B12`, `0x06004B9A`]. The register lives on the 32X side, so neither CPU caches it. Only the SH-2s can write it; the 68000 has a different register (bank set) at the same offset. After Burner Complete finds spare words in the same way, in the FIFO's address registers ([One call per object](#one-call-per-object)) and in the SH-2's breakpoint unit ([PWM audio](pwm.md#1-the-pwm-interrupt-star-wars-arcade)).
- **SDRAM, with the cache in mind.** The SH-2 cache does not watch what the other CPU writes [SH7604 §8.5.3]. Hitachi's own advice for two processors: keep the flags that say "ready" or "taken" at cache-through addresses, keep the bulk data cached, and purge it before reading. See [Cache](../sh2/cache.md).
- **A queue with no lock.** d32xr's sound commands go from one SH-2 to the other through a 256-byte ring buffer in SDRAM [D32XR, mars_ringbuf.h]:
  - The read and write positions are counters that only ever go up. Each lives in its own 16-byte cache line and is only accessed at its cache-through address. Fill level is the write counter minus the read counter, so full and empty never look alike.
  - Each side only ever writes its own counter, so no lock is needed.
  - Both counters move in whole 16-byte steps, so a cache line belongs to only one side at a time. The writer fills it through a cache-through pointer, and the reader purges it before reading.
- **Locks with `tas.b`.** `tas.b` reads a byte, sets its top bit and writes it back, and the SH-2 keeps the bus between the read and the write. Its read also skips the cache [SH7604 §7.10, §8.4.4]. That makes it a natural spin lock, and d32xr uses one-byte `tas.b` locks around each shared work counter: the next wall, the next floor area, the next column of the screen wipe [D32XR, r_phase6.c; r_phase7.c; f_wipe.c]. Hitachi recommends TAS for exactly this, semaphores between processors [SH7604 §8.5.3 p.228]. The 32X manual, however, says plainly not to use TAS on the 32X and gives no reason [32X-HWM §5.3 p.87]. No Sega SH-2 code read for this book uses it, retail or sample [SWA; MK2; AB32X; CHAOTIX; MCX; MARS-CHECK, SH-2 code]. d32xr's success on consoles proves less than it seems. Its per-picture locks only stop both CPUs claiming the same piece of work, so a lock that failed now and then would just repeat the work, and nobody would see it <span class="tag disputed">disputed</span> ([discrepancy 12](../appendices/discrepancies.md)). Until a console test settles it, a design that needs no lock, such as the queue above or a counter with only one writer, is the safer choice.
- **The serial link.** The two SH-2s' serial ports are wired to each other, clock line included [32X-HWM §5.3 p.87]. Sega's startup sample sets up the Master's port [32X-TIA1, SH-2 sample]. No game or homebrew project in the sources is known to use it. It is slow, but its receive interrupt is the only direct way for one SH-2 to interrupt the other. See [Serial port (SCI)](../sh2/sci.md#a-doorbell-between-the-sh-2s).

Mortal Kombat II shows the opposite extreme: its two SH-2s share nothing. The Slave keeps its variables at `0x0600A200`-`0x0600A22B`, and the Master never touches that range or any other the Slave uses. The Slave only plays sound and the Master only draws; each takes its orders from the 68000 directly. Apart from the `SLAV` word at start-up (see [Boot](boot.md#the-handshake-into-your-code)), they never talk to each other, so there is nothing to keep coherent [MK2, SH-2 program].

## What to take away

- Eight words, and every access is a byte or a word. Give the address, not a COMM name, because the names mean different things in different headers.
- Give each word one writer at a time, write the data before the signal, and read twice when a bad value would hurt.
- Clear the command word after the work, on every path, and never wait without a limit. Then test the timeout on something other than PicoDrive.
- CMD is the only way to reach an SH-2 that is not listening. Use it to stop the SH-2s, and confirm each step through a port.
- Between the SH-2s, prefer the ports or designs that need no lock. TAS should work by the SH-2's design and works in emulators, but the manual forbids it and no console test has checked it.

## Open questions

- Do INTM and INTS clear themselves when the SH-2 writes `0x2000401A`? ([Discrepancy 11](../appendices/discrepancies.md).)
- Is `tas.b` on SDRAM safe on a production 32X with two SH-2s competing for it? Test it with both CPUs incrementing one shared counter under a `tas.b` lock and checking that no increment is lost ([Discrepancy 12](../appendices/discrepancies.md)).
- What does a port read return when it overlaps a write from the other side: the old value, the new one, or a mix of bits? How often do the communication errors on 315-5818 boards actually happen?
- How much does a Slave polling the ports in a tight loop slow down a Master that is drawing?

## Sources

- [32X-HWM](../appendices/bibliography.md#32x-hwm): §3.2 registers (pp.20, 23, 28-31), §3.3 68000-SH2 communication (p.67), §4.1 block access (p.74), §4.4 access timing, §5.1 boot, §5.3 restrictions (p.87), interrupt restrictions (p.89)
- [32X-SUP2](../appendices/bibliography.md#32x-sup2): SH-2 interrupt limitations and clearing an interrupt
- [32X-OV](../appendices/bibliography.md#32x-ov), [32X-INTRO](../appendices/bibliography.md#32x-intro): register tables, sound driver plan
- [32X-TI](../appendices/bibliography.md#32x-ti): item 11, interface chip versions
- [32X-TIA1](../appendices/bibliography.md#32x-tia1): startup sample code for all three CPUs
- [SH7604](../appendices/bibliography.md#sh7604): §5.7, §7.10, §7.11.2, §8.4.4, §8.5.3
- [PICODRIVE](../appendices/bibliography.md#picodrive): `pico/32x/memory.c`, `pico/32x/32x.c`
- [MK2](../appendices/bibliography.md#mk2): 68000 code at `$00DD9C`, `$00DFAA`, `$00E01A`; SH-2 code at `0x060003F4`, `0x06005178`
- [AB32X](../appendices/bibliography.md#ab32x): 68000 code at `$88091E`, `$887348`-`$8873BC`; SH-2 code at `0x060022EC`, `0x0600257C`, `0x0600371C`, `0x060038E6`, `0x06000684`
- [SWA](../appendices/bibliography.md#swa): SH-2 code at `0x06000744`, `0x06000750`, `0x06001074`
- [VRD-NOTES](../appendices/bibliography.md#vrd-notes), [AU-NOTES](../appendices/bibliography.md#au-notes), [D32XR](../appendices/bibliography.md#d32xr), [S32X-SKILL](../appendices/bibliography.md#s32x-skill), [MARSDEV](../appendices/bibliography.md#marsdev), [32XDK](../appendices/bibliography.md#32xdk)
