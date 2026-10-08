# 32X header and security code

Every 32X cartridge starts with the same 2 KB layout. Get it right and the boot ROMs start your code on all three CPUs. Get one field wrong and you usually see a black screen with no error. This page goes through the layout in the order you write it. [Boot, security code and initial program](../32x/boot.md) explains what each part is for and what the boot code does with it.

## The first 2 KB at a glance

| Cartridge offset | Size | Contents | Who reads it |
|------------------|------|----------|--------------|
| `$000000-$0000FF` | 256 bytes | 68000 vectors | The 68000, at power-on only |
| `$000100-$0001FF` | 256 bytes | Mega Drive header | The Master SH-2 (checksum, ROM end), the initial program (checksum) |
| `$000200-$000319` | 282 bytes | Jump table: 47 slots of 6 bytes | The 68000, for every exception once the 32X is on |
| `$00031A-$0003BF` | 166 bytes | Free | |
| `$0003C0-$0003EF` | 48 bytes | User header | The Master SH-2 boot ROM |
| `$0003F0-$0007FF` | 1040 bytes | Sega's initial program, unchanged | The 68000. The Master SH-2 compares it |
| `$000800` | | Your 68000 entry point | The 68000, by falling through from the initial program |

Sources: [32X-HWM §3.1, §5.1-5.2; VRD-NOTES, ROM; VRD-NOTES, 32X BIOS dump].

**Assemble as if the cartridge started at `$880000`.** Once the 32X is on, the 68000 runs your code through the fixed window, so every absolute address in your 68000 code must be `$88xxxx` (or `$9xxxxx` for the banked megabyte) [32X-HWM §3.1]. The marsdev toolchain links its 68000 code this way [MARSDEV, 32x-skeleton md.ld]. The few values used before the switch, such as the reset vector, are written as plain numbers.

## 1. The 68000 vectors

At power-on the 32X is not yet enabled, so the 68000 reads the cartridge's own vector table like any Mega Drive game. Only two entries matter:

| Offset | Value |
|--------|-------|
| `$000000` | Initial stack pointer. Any address in work RAM. The initial program reloads it from here, through `$880000`, later on |
| `$000004` | `$000003F0`, the start of Sega's initial program. It must be entered at its first byte <span class="tag manual">manual</span> [32X-HWM §5.2] |

Once the initial program has turned the 32X on, the 68000 takes its vectors from the 32X's vector ROM, and the rest of this table is never used [32X-HWM §3.1]. Interrupts are masked during power-on, so nothing else is read before the switch. Fill the remaining entries with something harmless. Virtua Racing Deluxe points them all at one handler in the fixed window, and marsdev points them at `$3F0` [VRD-NOTES, ROM; MARSDEV, 32x-skeleton mars_start.s].

## 2. The Mega Drive header

This is the ordinary Mega Drive header described in [Mega Drive ROM header and checksum](md-header.md), with three fields that matter more than usual:

- **`$100`, system name.** Retail 32X cartridges put `SEGA 32X` here. Virtua Racing Deluxe has `SEGA 32X U` [VRD-NOTES, ROM]. Sega's Mega Drive manual asks for `SEGA MEGA DRIVE` or `SEGA GENESIS` [MD-SDM §1]. No part of the 32X boot code reads this field [VRD-NOTES, 32X BIOS dump], so `SEGA 32X` is a convention rather than a requirement. Keep the first four characters as `SEGA`.
- **`$18E`, checksum.** The 32X boot checks it for you. The Master SH-2 adds up the ROM and the initial program compares the result with this field. If it is non-zero and wrong, your code receives error `$0020`. Zero skips the check [VRD-NOTES, 32X BIOS dump; VRD-NOTES, ROM]. See [The checksum](../32x/boot.md#the-checksum).
- **`$1A4`, ROM end address.** The Master adds up exactly the range from `$000200` to this address. It must be the true last byte of the ROM. For a 4 MB cartridge that is `$003FFFFF` [VRD-NOTES, 32X BIOS dump].

## 3. The jump table

The 32X's vector ROM sends every 68000 exception to a fixed place in your cartridge. Vector number *N* goes to `$880200 + 6 × (N − 1)` [VRD-NOTES, 32X BIOS dump; 32X-HWM §3.1 p.14]. Six bytes is exactly one `jmp` to an absolute address (`$4EF9` followed by the long address). Each slot holds one jump to your handler.

**Every vector has its own slot, whether you use it or not.** If you pack only the entries you need one after another, they land in the wrong slots: your vertical blank handler sits where vector 16 expects its jump, and the real vertical blank slot holds padding. Aerobiz Ultimate's first 32X build made exactly this mistake [AU-NOTES, header].

The slots you will normally fill:

| Vector | Exception | Slot |
|--------|-----------|------|
| 1 | Reset, after the reset button | `$200` |
| 2-11 | Bus error, address error, illegal instruction, divide by zero, CHK, TRAPV, privilege, trace, line A, line F | `$206-$23C` |
| 24 | Spurious interrupt | `$28A` |
| 26 | Level 2: external interrupt | `$296` |
| 28 | Level 4: horizontal interrupt | `$2A2` |
| 30 | Level 6: vertical interrupt | `$2AE` |
| 32-47 | `TRAP #0` to `TRAP #15` | `$2BA-$314` |

The vector ROM covers vectors 1 to 47, so the table ends at `$319`. The 166 bytes up to the user header are yours to use.

Three details to get right:

- **Use `jmp`, not `jsr`.** A handler that ends with `rte` expects the stack as the exception left it. A `jsr` in the slot pushes an extra return address and the `rte` goes wrong.
- **The reset slot is your reset-button handler.** It is not reached at power-on. It is where the 68000 goes when the reset button is pressed while the 32X is on. What it has to do is in [Pressing reset](../32x/boot.md#pressing-reset).
- **The horizontal interrupt can be redirected at run time.** The vector ROM's entry for level 4, at `$000070`, is RAM. Sega's Mars Check Program tests it with a walking 1 across all 32 bits, and points it at its own handler to count lines [MARS-CHECK, 68000 code at `$1E84`, `$4578`]. Writing an address there sends horizontal interrupts straight to it, bypassing the slot. The initial program puts back the default (`$8802A2`) on every boot <span class="tag manual">manual</span> [32X-OV p.29; VRD-NOTES, ROM].

## 4. The user header

48 bytes at `$3C0` tell the Master SH-2 boot ROM what to copy into SDRAM and where each SH-2 starts [32X-HWM §5.1]:

| Offset | Size | Field | Example (Virtua Racing Deluxe) |
|--------|------|-------|--------------------------------|
| `$3C0` | 16 bytes | Module name. Not checked; Sega's sample uses `MARS CHECK MODE ` | `MARS CHECK MODE ` |
| `$3D0` | long | Version. Not checked | `$00000000` |
| `$3D4` | long | Source: the **cartridge offset** of your SH-2 image | `$00020000` |
| `$3D8` | long | Destination: the **offset into SDRAM** | `$00000000` |
| `$3DC` | long | Size in bytes | `$0000C000` |
| `$3E0` | long | Master entry point, as an SH-2 address | `$06000280` |
| `$3E4` | long | Slave entry point | `$06000288` |
| `$3E8` | long | Master vector base | `$06000000` |
| `$3EC` | long | Slave vector base | `$06000140` |

Sources: [32X-HWM §5.1; VRD-NOTES, ROM; VRD-NOTES, 32X BIOS dump].

Rules:

- **Everything must be a multiple of 4**: source, destination, size, entry points and vector bases. The boot ROM copies longwords and the SH-2 raises an address error on a misaligned one, which shows up as a hang <span class="tag manual">manual</span> [32X-HWM §5.1].
- **Source and destination are offsets, not addresses.** The boot ROM adds `0x22000000` to the source and `0x06000000` to the destination itself [VRD-NOTES, 32X BIOS dump].
- **Leave the top 4 KB of SDRAM out of the copy.** The default stacks live there and grow down from `0x06040000` (Master) and `0x0603F800` (Slave). See [What your code starts with](../32x/boot.md#what-your-code-starts-with).
- **Link your SH-2 code for where it ends up**, at `0x06000000` plus the destination offset, not where it sits in the cartridge.

The Master and Slave usually share one image, with a vector table for each and two entry points in it, as in the example above.

## 5. Sega's initial program

The 1040 bytes from `$3F0` to `$7FF` must be Sega's initial program, copied byte for byte. Each boot, the Master SH-2 compares `$400-$7FF` with its own copy and refuses to start if they differ. The first 16 bytes are not compared, but they are the start of the 68000 code and cannot be changed either <span class="tag manual">manual</span> [32X-HWM §5.2; VRD-NOTES, 32X BIOS dump]. It is the same in every cartridge [AU-NOTES, security block].

The code belongs to Sega and is not reproduced in this book. Two places have it:

- Every retail 32X cartridge, at the same offset. Aerobiz Ultimate's build extracts it from a ROM image you supply with `tools/extract_mars_init.py` [AU-NOTES, security block].
- The marsdev toolchain's `32x-skeleton` example, which carries it as data in `md_src/md_start.s`. It is byte-identical to the retail copy [AU-NOTES, security block].

Never patch it, not even to change where it continues. It always ends by falling through to `$800`, so put your code there instead.

## 6. Your entry point at `$800`

The initial program finishes with the carry flag and `d0` holding its verdict (see [The verdict](../32x/boot.md#the-verdict)). The first instruction at `$800` should be a branch on carry to your error handler <span class="tag manual">manual</span> [32X-HWM §5.2, sample program].

**Make the error path position-independent.** If no 32X is attached, the initial program gives up before switching the memory map. Your code at `$800` is then running at `$000800` on a plain Mega Drive, where nothing is mapped at `$880000`. An absolute jump to a `$88xxxx` address crashes. Use PC-relative branches and addressing until you know the 32X is there. Virtua Racing Deluxe's error path does exactly this [VRD-NOTES, ROM]. The other errors are found after the switch, so they arrive at `$880800`.

After a successful boot, your code:

1. Checks bit 15 of `d0`. If it is set, this was the reset button, not power-on: go to your reset handling.
2. Waits until `$A15120` reads `M_OK` and `$A15124` reads `S_OK`.
3. Clears them to let the SH-2s continue (see [The handshake into your code](../32x/boot.md#the-handshake-into-your-code)).
4. Carries on with its own setup. The 68000 owns the 32X VDP at this point (FM = 0).

In outline:

```asm
; cartridge $000800, reached as $880800 after a good boot
        bcs.s   BootFailed          ; carry set: d0 says why
        btst    #15,d0
        bne.w   WarmStart           ; reset button, not power-on
.waitM: cmpi.l  #'M_OK',$A15120
        bne.s   .waitM
.waitS: cmpi.l  #'S_OK',$A15124
        bne.s   .waitS
        clr.l   $A15120             ; release the SH-2s
        clr.l   $A15124
        ; ... your setup ...

BootFailed:                         ; may be running at $000800: PC-relative only
        ; d0 = $0001 no 32X, $0002 PAL/NTSC mismatch, $0020 checksum,
        ;      $0040 security, $0080 SDRAM
        bra.s   BootFailed
```

## When it does not boot

| Symptom | Likely cause |
|---------|--------------|
| Black screen. `$A15120` reads `SQER` | The initial program is not byte-identical, or not at `$3F0` [VRD-NOTES, 32X BIOS dump] |
| Black screen. `$A15120` never reads `M_OK` | A misaligned field in the user header made the Master take an address error [32X-HWM §5.1] |
| The 68000 waits forever for `S_OK` | It is polling the wrong address. `S_OK` is at `$A15124`, which the manual calls "comm 4" [AU-NOTES, security block] |
| Error `$0020` | Checksum field or ROM end address wrong |
| Error `$0002` | The Mega Drive and the 32X disagree about PAL/NTSC. In an emulator, check that both use the same region setting |
| Boots, but vertical interrupts never run | The jump table is packed instead of one slot per vector |
| Works in PicoDrive, region lockout or garbage on hardware or Ares | Code reads its own header at `$0001xx` instead of `$8801xx` <span class="tag emulator">emulator</span> [VRD-NOTES, PicoDrive RV patch] |
| SH-2 crashes after reaching your code | Your program was copied over the default stacks, or linked for the wrong SDRAM address |
| All three CPUs wait forever after boot | Each side waits for the other: for example, SH-2 start-up code that waits for FM = 1 while the 68000 waits for a message from it. Give the SH-2s FM first [S32X-SKILL, testing] |
| Boots and runs, but the 32X layer stays black | A frame buffer without a line table: both buffers need one. Or a palette still all zero [S32X-SKILL, testing; [The 32X VDP](../32x/vdp.md#the-line-table)] |

## Sources

- [32X-HWM](../appendices/bibliography.md#32x-hwm): §3.1 p.14 jump table, §5.1 user header, §5.2 initial program
- [32X-OV](../appendices/bibliography.md#32x-ov): horizontal interrupt vector (p.29)
- [MD-SDM](../appendices/bibliography.md#md-sdm): §1 cartridge ID
- [VRD-NOTES](../appendices/bibliography.md#vrd-notes): retail ROM, 32X BIOS dumps, PicoDrive RV patch
- [AU-NOTES](../appendices/bibliography.md#au-notes): header, security block
- [MARSDEV](../appendices/bibliography.md#marsdev): `32x-skeleton` example
