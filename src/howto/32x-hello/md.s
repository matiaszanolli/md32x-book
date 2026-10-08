| hello32x, 68000 side and the whole cartridge layout. Linked at 0.
| After the initial program, this code runs at $880000 + its offset.
| Needs security.bin (Sega's initial program, $3F0-$7FF of any 32X
| cartridge) and sh2.bin (the SH-2 program, padded to a multiple of 4).

        .text
| ANCHOR: layout
| ---- $000: 68000 vectors, used only before the 32X is switched on
        .long   0x00FFFE00              | stack
        .long   0x000003F0              | reset: Sega's initial program
        .rept   62
        .long   0x000003F0
        .endr

| ---- $100: Mega Drive header
        .org    0x100
        .ascii  "SEGA 32X        "
        .ascii  "(C)BOOK 2026.OCT"
        .org    0x120
        .ascii  "HELLO 32X"
        .org    0x150
        .ascii  "HELLO 32X"
        .org    0x180
        .ascii  "GM 00000000-00"
        .word   0                       | checksum 0: the initial program skips the check
        .ascii  "J               "
        .long   0x00000000, 0x0001FFFF  | ROM
        .long   0x00FF0000, 0x00FFFFFF  | RAM
        .org    0x1F0
        .ascii  "JUE             "

| ---- $200: jump table. With the 32X on, exception vector n jumps to
| $880200 + 6 * (n - 1). Nothing here is expected to happen.
        .org    0x200
        .rept   47
        jmp     halt+0x880000
        .endr

| ---- $3C0: MARS user header, read by the Master's boot ROM
        .org    0x3C0
        .ascii  "MARS CHECK MODE "
        .long   0                       | version
        .long   sh2_start               | source: cartridge offset of the SH-2 program
        .long   0                       | destination: offset into SDRAM
        .long   sh2_end-sh2_start       | size in bytes, a multiple of 4
        .long   0x06000200              | Master entry
        .long   0x06000400              | Slave entry
        .long   0x06000000              | Master vector base
        .long   0x06000000              | Slave vector base

| ---- $3F0-$7FF: Sega's initial program, unchanged
        .org    0x3F0
        .incbin "security.bin"

| ANCHOR_END: layout
| ANCHOR: start68k
| ---- $800: our code, entered at $880800 with SR = $2700
        .org    0x800
start:
        bcs     fail                    | carry set: the initial program found an error

        lea     0xA15100, a5
1:      cmpi.l  #0x4D5F4F4B, 0x20(a5)   | wait for "M_OK"
        bne.s   1b
2:      cmpi.l  #0x535F4F4B, 0x24(a5)   | and "S_OK"
        bne.s   2b
        clr.l   0x20(a5)                | release the Master
        clr.l   0x24(a5)                | and the Slave

        lea     0xC00004, a0            | VDP control port
        lea     0xC00000, a1            | VDP data port
        lea     vdp_regs(pc), a2
        moveq   #10, d0
3:      move.w  (a2)+, (a0)
        dbra    d0, 3b

        move.l  #0x40200000, (a0)       | VRAM $0020: tile 1, every pixel colour 1
        moveq   #15, d0
4:      move.w  #0x1111, (a1)
        dbra    d0, 4b

        move.l  #0x4C000003, (a0)       | VRAM $CC00: plane A rows 24-26
        move.w  #3*64-1, d0
5:      move.w  #0x0001, (a1)
        dbra    d0, 5b

        moveq   #0, d7                  | frame counter
loop:
6:      move.w  (a0), d0                | wait while in vertical blank
        btst    #3, d0
        bne.s   6b
7:      move.w  (a0), d0                | then for the next one to start
        btst    #3, d0
        beq.s   7b
        addq.w  #1, d7
        move.w  d7, d1                  | colour 1 cycles through the CRAM range
        lsr.w   #2, d1
        add.w   d1, d1
        andi.w  #0x0EEE, d1
        move.l  #0xC0020000, (a0)       | CRAM word 1
        move.w  d1, (a1)
        bra.s   loop

| ANCHOR_END: start68k
fail:
        lea     0xC00004, a0
        move.w  #0x8144, (a0)           | display on
        move.l  #0xC0000000, (a0)       | backdrop (CRAM 0) red
        move.w  #0x000E, 0xC00000
halt:
        bra.s   halt

vdp_regs:
        .word   0x8004, 0x8144, 0x8230, 0x8407, 0x8578, 0x8700
        .word   0x8B00, 0x8C81, 0x8D3F, 0x8F02, 0x9001

| ---- $2000: the SH-2 program, copied to SDRAM by the Master's boot ROM
        .org    0x2000
sh2_start:
        .incbin "sh2.bin"
sh2_end:
        .org    0x20000
