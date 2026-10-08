# Mega Drive ROM header and checksum

Every Mega Drive cartridge carries a 256-byte header at `$000100-$0001FF`. It names the game, says which controllers and regions it supports, describes any save RAM, and holds a checksum. Sega used it to approve and track releases. Today emulators, flash carts and the 32X boot ROMs read it. This page goes through it field by field, then shows how to compute the checksum.

The example values throughout come from *Aerobiz Supersonic* (USA), whose header is reproduced exactly in its byte-identical disassembly [AB-DISASM].

## The layout

| Offset | Size | Field | Aerobiz Supersonic |
|--------|------|-------|--------------------|
| `$100` | 16 | System name | `SEGA GENESIS    ` |
| `$110` | 16 | Copyright and release date | `(C)T-76 1994.DEC` |
| `$120` | 48 | Title for Japan | the title in Shift-JIS katakana, padded with spaces |
| `$150` | 48 | Title for elsewhere | `AEROBIZ          SUPERSONIC  ...` |
| `$180` | 14 | Product type, number and version | `GM T-76136 -00` |
| `$18E` | 2 | Checksum | `$4620` |
| `$190` | 16 | Supported I/O devices | `J` |
| `$1A0` | 8 | ROM start and end address | `$00000000`, `$000FFFFF` |
| `$1A8` | 8 | RAM start and end address | `$00FF0000`, `$00FFFFFF` |
| `$1B0` | 12 | External RAM (save memory) | `RA`, `$F8`, `$20`, `$00200001`, `$00203FFF` |
| `$1BC` | 12 | Modem | spaces |
| `$1C8` | 40 | Not used | spaces |
| `$1F0` | 16 | Regions | `U` |

Sources: [MD-SDM §1; MD-SWM, ROM cartridge data; MD-TB, cartridge identification].

**Every unused byte is a space** (`$20`), not zero. That includes the ends of the text fields and whole fields you do not use <span class="tag manual">manual</span> [MD-SDM §1].

## Field by field

### `$100` System name

`SEGA MEGA DRIVE ` or `SEGA GENESIS    `. Both are accepted for any region [MD-SDM §1; MD-TB, cartridge identification]. 32X cartridges use `SEGA 32X` by convention (see [32X header and security code](32x-header.md)).

Emulators also use this field to decide on extra hardware. `SEGA SSF` asks for Sega's bank chip (see [Cartridge hardware](../megadrive/cartridge.md#bank-switching-beyond-4-mb)) <span class="tag emulator">emulator</span> [S32X-SKILL, architecture].

The first four characters matter in practice. The PicoDrive emulator recognises a Mega Drive cartridge by `SEGA` (or ` SEG`) at `$100`, in the role of the boot ROM in later consoles <span class="tag emulator">emulator</span> [PICODRIVE, media.c]. The manuals do not say what, if anything, the console itself checks here.

### `$110` Copyright and date

`(C)`, a four-character company code, a space, then the release year and month: `(C)SEGA 1994.SEP`. Sega's own games use `SEGA`. Licensed developers used the code Sega assigned them, written `T-` and a number: Aerobiz's `T-76` is Koei [MD-SDM §1; MD-TB, cartridge identification].

### `$120` and `$150` Titles

48 bytes each, padded with spaces. The first is the title for Japan and may use Shift-JIS, as Aerobiz's does. The second is the title for everywhere else [MD-SDM §1].

### `$180` Product code

14 characters: a type (`GM` for a game, `AI` for educational software), the product number, and a version number after a dash [MD-SDM §1]. The version was meant to go up with each revision of the same game. Sega's own products and third-party ones put the number in slightly different formats, `MK-` and `T-` respectively [MD-TB, cartridge identification].

### `$18E` Checksum

A 16-bit sum of the ROM. See [The checksum](#the-checksum) below.

### `$190` Supported I/O devices

Up to 16 one-letter codes, one per supported device, padded with spaces [MD-SDM §1]:

| Code | Device |
|------|--------|
| `J` | Mega Drive control pad |
| `0` | Master System control pad |
| `K` | Keyboard |
| `R` | Serial (RS-232C) |
| `P` | Printer |
| `T` | Tablet |
| `B` | Trackball |
| `V` | Paddle |
| `F` | Floppy drive |
| `C` | CD-ROM |
| `A` | Analogue joystick |

Later games use codes that are not in this list. Virtua Racing Deluxe declares `J6`, adding `6` for the six-button pad [VRD-NOTES, ROM].

### `$1A0` ROM start and end

Two longwords: `$00000000` and the address of the last byte, so the ROM size minus 1. A 1 MB (8 Mbit) game has `$000FFFFF` [MD-SDM §1]. The checksum covers exactly up to this address, so it has to be right.

### `$1A8` RAM start and end

Always `$00FF0000` and `$00FFFFFF`, the console's 64 KB of work RAM [MD-SDM §1].

### `$1B0` External RAM

For a cartridge with save memory, twelve bytes [MD-SDM §3]:

```text
$1B0  'R','A'            marker
$1B2  %1x1yz000          x  = 1 keeps data with the power off (battery or EEPROM), 0 does not
                         yz = 10 even bytes only, 11 odd bytes only, 00 whole words,
                              01 anything else (serial EEPROM, 4-bit RAM)
$1B3  %abc00000          abc = 001 SRAM, 010 EEPROM
$1B4  start address      longword
$1B8  end address        longword
```

Aerobiz's `$F8`, `$20` means battery-backed, odd bytes only, SRAM. `$200001-$203FFF` makes that 8 KB on the odd addresses only, the standard battery save cartridge. It is the same as the example in Sega's manual [MD-SDM §3]. Without save memory, all twelve bytes are spaces.

### `$1BC` Modem

`MO`, the company code, a game number with a version, and a byte describing microphone support. It was used only for Sega's Japanese modem services, and Sega of Japan handed out the numbers [MD-SDM §4]. Everything else fills it with spaces.

### `$1F0` Regions

The regions the game may be sold in: `J` (Japan), `U` (USA), `E` (Europe), padded with spaces [MD-SDM §1]. A game sold in all three has `JUE`.

The console does not enforce this field. A game that wants to refuse to run in the wrong region has to check the console's version register at `$A10001` itself (see [Controllers and I/O ports](../megadrive/io.md)). Emulators do read it to choose a region automatically. PicoDrive accepts the letters and also a single hexadecimal digit, a form some later games use <span class="tag emulator">emulator</span> [PICODRIVE, pico.c].

## The checksum

### What it covers

The checksum is the sum of every 16-bit word from `$000200` up to the ROM end address in the header, keeping only the low 16 bits. The vectors and the header itself are left out, so the checksum does not include itself <span class="tag manual">manual</span> [MD-SDM §5; MD-SWM, how to obtain check sum].

Sega's procedure fills the unused part of the ROM with `$FF` before adding up, and asks for the same filling when the ROM is programmed [MD-SDM §5]. If your tools pad with zeros, the sum changes, so compute it on the file as it will be programmed.

### Computing it

On the build machine, after the final link and padding:

```python
import struct

def md_checksum(rom: bytes) -> int:
    end = struct.unpack(">I", rom[0x1A4:0x1A8])[0]   # last byte, from the header
    words = struct.unpack(">%dH" % ((end + 1 - 0x200) // 2), rom[0x200:end + 1])
    return sum(words) & 0xFFFF

def fix_checksum(rom: bytearray) -> None:
    rom[0x18E:0x190] = struct.pack(">H", md_checksum(rom))
```

For Aerobiz Supersonic this gives `$4620`, the value in its header [AB-DISASM].

The same calculation in 68000 code, for a game that wants to check itself at startup:

```asm
; returns the computed checksum in d0.w; Z flag set if it matches the header
CheckRom:
        movea.l #$200,a0
        move.l  ($1A4).w,d1         ; last byte of the ROM
        addq.l  #1,d1
        sub.l   a0,d1
        lsr.l   #1,d1               ; number of words
        moveq   #0,d0
.loop:  add.w   (a0)+,d0
        subq.l  #1,d1
        bne.s   .loop
        cmp.w   ($18E).w,d0
        rts
```

On a plain Mega Drive this takes a noticeable moment for a large ROM, since every word is read once. On a 32X cartridge, read the header at `$8801A4` and `$88018E` and the ROM through the 32X windows, or use the result the boot code already computed (see below).

### Who checks it

- **The Mega Drive itself does not.** Checking is up to the game. Many games skip it: Aerobiz Supersonic's checksum routines are for its save data, and nothing in it checks the ROM [AB-DISASM].
- **The 32X boot code does**, on every 32X cartridge with a non-zero checksum field. The Master SH-2 adds up the ROM the same way, and the result reaches your code as error `$0020`. What to do about it is still your choice. See [The checksum](../32x/boot.md#the-checksum).
- **Tools and emulators** often report a wrong checksum as a warning. A bad checksum usually means the header's ROM end address is wrong, or the file was padded differently from the way it was summed.

## The code at `$200`

The checksum starts at `$200` because that is where the program starts. Sega required every Mega Drive game to begin with its standard initial program (`ICD_BLK4.PRG`), unchanged, right at the program start. It tells a cold start from a reset, writes `SEGA` to `$A14000` on consoles with a non-zero version number, and sets the VDP, Z80 and PSG to a known state <span class="tag manual">manual</span> [MD-SDM §2; MD-SWM, precautions for M5 software]. Aerobiz Supersonic's program begins with it at `$200` [AB-DISASM].

Nothing in a plain Mega Drive compares this code the way the 32X compares its own initial program. What a console with a non-zero version number does need is the four-byte write to `$A14000`. Leave that out and your game may run in an emulator and on early consoles, but not on later ones. See [Hello world on the Mega Drive](md-hello.md).

## Checklist

- System name starts with `SEGA`.
- Text fields and unused fields are padded with spaces, not zeros.
- ROM end address = file size − 1, after padding.
- Checksum computed last, over the padded file.
- External RAM field matches the hardware on the cartridge, or is all spaces.
- Region field lists every region you intend to support. Region locking, if you want it, is done in code.

## Sources

- [MD-SDM](../appendices/bibliography.md#md-sdm): §1 cartridge ID, §2 initial program, §3 external RAM, §4 modem, §5 checksum
- [MD-SWM](../appendices/bibliography.md#md-swm): ROM cartridge data, how to obtain check sum, U.S. security software
- [MD-TB](../appendices/bibliography.md#md-tb): cartridge identification (26 November 1990)
- [AB-DISASM](../appendices/bibliography.md#ab-disasm): header, initial program, save checksum routines
- [VRD-NOTES](../appendices/bibliography.md#vrd-notes): retail ROM header, PicoDrive
