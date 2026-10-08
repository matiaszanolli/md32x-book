# Controllers and I/O ports

The Mega Drive talks to pads, mice and other peripherals through three general-purpose I/O ports: the two controller ports on the front panel and a third on the expansion connector. Electrically all three work the same way: seven signal lines per port, each with its own direction bit, plus two lines that can be borrowed for slow serial data [MD-SWM §4.2]. A version register next to them says which console this is. This chapter covers the registers, how a pad read works, how to tell a pad from a mouse from nothing at all, the 6-button protocol, serial mode, and how a shipped game organises the whole job.

## The registers

Each port has five byte-wide registers at odd addresses in `$A10000-$A1001F` [MD-SWM §4.2]. Word access is allowed, but only the low byte means anything, so byte access is the norm:

| Address | Register | Port | Purpose |
|---------|----------|------|---------|
| `$A10003` | DATA | 1 (front) | Pin levels / output values |
| `$A10005` | DATA | 2 (front) | |
| `$A10007` | DATA | EXP | |
| `$A10009` | CTRL | 1 | Pin directions, TH interrupt |
| `$A1000B` | CTRL | 2 | |
| `$A1000D` | CTRL | EXP | |
| `$A1000F` | TxDATA | 1 | Serial transmit data |
| `$A10011` | RxDATA | 1 | Serial receive data |
| `$A10013` | S-CTRL | 1 | Serial control and status |
| `$A10015`-`$A1001F` | | 2, EXP | The same three, same order |

DATA reads the pins, or holds the value to drive on them when they are outputs [MD-SWM §4.2]:

| Bit | Line | Pin | Pulled up |
|-----|------|-----|-----------|
| D0 | Up | 1 | 10 kΩ |
| D1 | Down | 2 | 10 kΩ |
| D2 | Left | 3 | 10 kΩ |
| D3 | Right | 4 | 10 kΩ |
| D4 | TL | 6 | — |
| D5 | TR | 9 | — |
| D6 | TH | 7 | 10 kΩ |
| D7 | — | — | — |

The pull-ups matter: an empty port does not read as zeroes. With nothing connected, D0-D3 and D6 read 1, and that is what makes device detection possible.

CTRL sets the direction of each line and one interrupt [MD-SWM §4.2]. A bit of 0 makes the line an input, 1 an output:

| Bit | Meaning |
|-----|---------|
| D7 (INT) | 1 allows the external interrupt on a TH change |
| D6 (PC6) | TH direction |
| D5 (PC5) | TR direction |
| D4 (PC4) | TL direction |
| D3-D0 | Right, Left, Down, Up directions |

The TH interrupt arrives as the 68000's level 2 external interrupt, and only when TH is an input; it exists for peripherals that signal on their own, light guns being the classic case. The details are in [Timing, interrupts and counters](vdp-timing.md#the-external-interrupt) [MD-SWM §2.6; GENVDP §4].

## The version register

One byte at `$A10001` identifies the machine [MD-SWM §4.1]:

| Bit | Name | Meaning |
|-----|------|---------|
| 7 | MODE | 0: domestic model, 1: overseas model |
| 6 | VMOD | 0: NTSC, 68000 clock 7.67 MHz; 1: PAL, 7.60 MHz |
| 5 | DISK | 0: disk drive unit connected, 1: not connected |
| 4 | RSV | Unused |
| 3-0 | VER | Hardware version, `$0`-`$F` |

Games read MODE to pick the region's language and VMOD to pick 50 or 60 Hz timing (see [Timing, interrupts and counters](vdp-timing.md#a-frame-line-by-line)). The manual documents only `$0` as a version value <span class="tag manual">manual</span> [MD-SWM §4.1]. Later consoles return other values, and Sega's own start-up code is written for that. The Mega Drive initial program at `$200` and the 32X one at `$3F0` both read VER and, only when it is not 0, write `SEGA` to `$A14000`, the TMSS lock [AB-DISASM, initial program at `$00021C`-`$000226`; SWA, 68000 code at `$000436`-`$000440`]. No Sega document read for this book lists which model returns which value. BlastEm returns 1 on the models it emulates with TMSS (Mega Drive 1 from VA6, Mega Drive 2, Genesis 3) and 0 on the others (Mega Drive 1 VA0 and VA3, Teradrive) <span class="tag emulator">emulator</span> [BLASTEM, systems.cfg, genesis.c]. So test VER for non-zero, as Sega does, never for a particular value.

## How a pad read works

The port has seven lines, but a pad has more than seven things to report, so the pad contains a multiplexer (an HC157 in Sega's diagram) and the console picks which half of the buttons it sees through TH [MD-SDM S2]. TH is driven as an output; the other lines stay inputs. One read gives directions plus two buttons, the other gives Start and A plus the vertical directions again:

| Line | TH = 1 | TH = 0 |
|------|--------|--------|
| D5 | C | Start |
| D4 | B | A |
| D3 | Right | 0 |
| D2 | Left | 0 |
| D1 | Down | Down |
| D0 | Up | Up |

A button reads 0 when pressed: the lines are active low, as the pull-ups and the pad's open outputs make 1 the idle state [MD-SDM S2].

After changing TH, the pad's multiplexer needs about 1 µs to settle — Sega calls this the time of two NOPs, and its own sample inserts two [MD-SDM S2]. A full read of one port:

```asm
    move.b  #$40,$A10009      ; CTRL1: TH output, the rest inputs
    move.b  #$40,$A10003      ; TH = 1
    nop
    nop
    move.b  $A10003,d0        ; C, B, Right, Left, Down, Up
    move.b  #$00,$A10003      ; TH = 0
    nop
    nop
    move.b  $A10003,d1        ; Start, A, 0, 0, Down, Up
```

Sega's peripheral sample program packs the two reads into one byte, from bit 7 down: Start, A, C, B, Right, Left, Down, Up [MD-TB, bulletin 16]. Games are free to pack differently, and do.

## Telling devices apart: the peripheral ID

Not everything plugged into a port is a pad, and games are expected to cope with whatever appears. Every Sega peripheral reports a four-bit ID through the direction lines: read once with TH at 1 and once with TH at 0, and ask, each time, whether any horizontal direction line and any vertical direction line was low (0) [MD-SDM S2]:

```
ID3 = TH at 1 and (Left or Right pressed-side driven low)
ID2 = TH at 1 and (Up or Down driven low)
ID1 = TH at 0 and (Left or Right driven low)
ID0 = TH at 0 and (Up or Down driven low)
```

A pad drives the horizontal lines low while TH is 0 (they read 0 in the table above), and nothing pulls them low when the port is empty, which gives each device class a distinct code:

| ID | Device |
|----|--------|
| `$D` | Control pad, 3- or 6-button |
| `$3` | Sega Mouse |
| `$7` | Team Player multitap |
| `$F` | Nothing connected |

Sources: the `$D`/`$F` meanings and the formula are Sega's [MD-SDM S2]; `$3` and `$7` are what Aerobiz dispatches on [AB-DISASM, InputCaseDispatch.asm]. Sega warns that some Mark III and Master System peripherals cannot be detected this way [MD-SDM S2].

Detection is quick because it needs no toggling beyond one TH change: Aerobiz writes `$70` to the port (TL, TR and TH outputs, all high), reads, writes `$30` (TH low), reads again, and turns each read into one bit pair; `(ID & $E) × 2` then indexes a table of eight `bra.w` entries, one per device class, with the 3-button reader as the shared default [AB-DISASM, ReadPortByte.asm `$195C`, InputCaseDispatch.asm `$198E`, CountInputBits.asm `$19CA`].

## The 6-button pad

The 6-button pad adds X, Y, Z and Mode, four buttons that have no lines of their own. The trick: the pad counts TH changes, and inside a quick burst of toggles it swaps what it puts on the lines. After enough edges, the TH = 0 read stops returning the Start/A nibble and returns the extra buttons instead; a short quiet period resets the pad's counter to ordinary 3-button behaviour, which is why the technique is safe on old pads.

The timing comes from the pad itself, not the console. Ein Terakawa timed a pad with a PC: two rising edges of TH within 1.1 ms switch it over, reads are reliable only within 1.6 ms of the first rising edge, and a new burst cannot start until 1.8 ms after it. He found the interval set by a capacitor discharging inside the pad, so it varies from pad to pad [TERAKAWA-6B]. Emulators pick a single figure: BlastEm resets the counter 56,000 master clocks (about 1.04 ms NTSC) after the last rising edge, Genesis Plus GX after more than 25 lines (about 1.6 ms) <span class="tag emulator">emulator</span> [BLASTEM, io.c; GPGX, core/input_hw/gamepad.c]. Reading once per frame, as Sega asks, leaves over 14 ms of quiet between bursts, far more than any of these figures. Do the whole burst quickly, well inside 1.1 ms, and never read the pad twice within 2 ms.

A TH = 0 read inside the burst that shows no direction bits at all (D0-D3 all 1, since lines idle high) is the signature of a pad that switched: a 3-button pad can never hide its Up/Down lines, because they are wired straight through [AB-DISASM, ReadMultiNibbles.asm `$1A20`]. So the read routine toggles TH up to three times — four NOPs of settle per edge, double Sega's margin — and watches for the directions to disappear. If they do, one more pair of reads collects the extra nibble:

| Line | Last TH = 0 read |
|------|------------------|
| D5 | 0 |
| D4 | 0 |
| D3 | Mode |
| D2 | X |
| D1 | Y |
| D0 | Z |

The nibble layout is Sega's [MD-TB, bulletin 16]; the toggle-and-detect sequence above is the shipped one in Aerobiz, which stores a 6-button pad as type 1 with the X/Y/Z/Mode nibble in its own byte, a 3-button pad as type 0, and an empty port as type `$F` [AB-DISASM, ReadMultiNibbles.asm].

Sega's rules for pad access, written when the 6-button pad and its companions were about to ship <span class="tag manual">manual</span> [MD-TB, bulletin 16]:

- Read pads from the vertical interrupt, once per frame, not repeatedly.
- Re-check the device ID at every vertical interrupt: peripherals can be swapped or (with the Team Player's selector) changed mid-game.
- Do not toggle more than needed — the sample stays within three TH cycles.

One trap is ours rather than Sega's: several emulators mirror the d-pad bits into the extra nibble during the handshake, so on them every direction also reads as X, Y, Z or Mode. Unless a game truly supports the 6-button pad, it should mask input down to the 3-button subset; ports that forgot shipped with Down mapped onto a menu action <span class="tag emulator">emulator</span> [S32X-SKILL, architecture].

## Serial mode

TL and TR can be borrowed from the parallel port and used as one slow serial channel per port, through TxDATA, RxDATA and S-CTRL [MD-SWM §4.2]:

| S-CTRL bit | Meaning |
|------------|---------|
| D7-D6 | Baud rate: 00 = 4800, 01 = 2400, 10 = 1200, 11 = 300 bps |
| D5 (SIN) | 1: TR becomes serial input |
| D4 (SOUT) | 1: TL becomes serial output |
| D3 (RINT) | 1: interrupt when a byte arrives |
| D1 (RERR) | 1: receive error |
| D0 (RRDY) | 1: receive data ready |

The baud rates give the purpose away: this is for modems and similar terminals, not for pads. The Team Player multitap does its four-player handshake in parallel mode, toggling TR and watching TL — the same lines, but with S-CTRL left alone [AB-DISASM, InputStateMachine.asm, PollInputStatus.asm].

## In a shipped game

Aerobiz's input system is one worked example of all of the above [AB-DISASM, input and vint modules]:

- **Every wait has a timeout.** The multitap and mouse handshakes poll with `dbne` counters loaded to 255 and return carry on timeout, so an unplugged or wedged device can never hang the game.
- **The mouse is decoded, not just read.** Packet bytes become 9-bit signed deltas (the ninth bit arrives as the packet's sign flag), overflow clamps to zero, and Y is negated so screen coordinates match.
- **The cursor has two speeds.** With a mouse, movement divides by `3 XOR speed`, so the three settings divide by 3, 2 and 1. With a pad, a hold timer starts slow (1 pixel per frame for 16 frames), then accelerates. Fine positioning and fast travel both work without a separate speed menu.
- **Taps are never lost.** Each vertical interrupt computes `pressed = (old XOR new) AND new` and ORs pressed and held bits for both ports into a latch gated by an enable mask, so a button held for one frame is still seen if the game logic ran slowly that frame.
- **The Z80 is parked first.** The whole port read sequence runs inside a Z80 bus request (see [Z80 bus control](z80.md)), because the TH handshake is timing-sensitive [AB-DISASM, InitInputArrays.asm].

## Open questions

- What does each console model return in the VER field of `$A10001`? Sega's code only tells zero from non-zero; the per-model values in this chapter come from an emulator.
- How much do the 6-button pad's 1.1, 1.6 and 1.8 ms intervals vary between pads and between official and third-party pads? The one measurement is of a single pad.

## Sources

- [MD-SWM](../appendices/bibliography.md#md-swm): §4.1 version register, §4.2 port registers and serial mode
- [MD-SDM](../appendices/bibliography.md#md-sdm): S2 peripheral ID codes, joy pad read and settle time
- [MD-TB](../appendices/bibliography.md#md-tb): bulletin 16, new peripherals and pad access rules
- [S32X-SKILL](../appendices/bibliography.md#s32x-skill): 6-button nibble mirroring in emulators
- [AB-DISASM](../appendices/bibliography.md#ab-disasm): ReadPortByte, InputCaseDispatch, CountInputBits, ReadMultiNibbles, WritePortToggle, InputStateMachine, PollInputStatus, InitInputArrays, the cursor and latch routines
- [GENVDP](../appendices/bibliography.md#genvdp): §4 external interrupt
- [SWA](../appendices/bibliography.md#swa): 32X initial program, version check at `$000436`-`$000440`
- [TERAKAWA-6B](../appendices/bibliography.md#terakawa-6b): 6-button pad timing, measured
- [BLASTEM](../appendices/bibliography.md#blastem): systems.cfg, genesis.c (version register), io.c (6-button timeout)
- [GPGX](../appendices/bibliography.md#gpgx): core/input_hw/gamepad.c, core/input_hw/input.c
