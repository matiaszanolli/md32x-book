| pipeline-test, 68000 side and the cartridge layout. Linked at 0.
| After the initial program, this code runs at $880000 + its offset.
| Needs security.bin (Sega's initial program, $3F0-$7FF of any 32X
| cartridge) and sh2.bin; text.inc and font.inc come from md-hello.
| The layout is the one explained in "Hello world on the 32X".

        .text
        .long   0x00FFFE00              | stack
        .long   0x000003F0              | reset: Sega's initial program
        .rept   62
        .long   0x000003F0
        .endr

        .org    0x100
        .ascii  "SEGA 32X        "
        .ascii  "(C)BOOK 2026.OCT"
        .org    0x120
        .ascii  "PIPELINE TEST"
        .org    0x150
        .ascii  "PIPELINE TEST"
        .org    0x180
        .ascii  "GM 00000000-00"
        .word   0                       | checksum 0: the initial program skips the check
        .ascii  "J               "
        .long   0x00000000, 0x0001FFFF  | ROM
        .long   0x00FF0000, 0x00FFFFFF  | RAM
        .org    0x1F0
        .ascii  "JUE             "

        .org    0x200                   | jump table: nothing is expected here
        .rept   47
        jmp     halt+0x880000
        .endr

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

        .org    0x3F0
        .incbin "security.bin"

        .org    0x800
start:
        bcs     halt                    | carry set: the initial program found an error
        move.l  #0x00FFFE00, sp

        lea     0xA15100, a5
1:      cmpi.l  #0x4D5F4F4B, 0x20(a5)   | wait for "M_OK"
        bne.s   1b
2:      cmpi.l  #0x535F4F4B, 0x24(a5)   | and "S_OK"
        bne.s   2b
        clr.w   0x2C(a5)                | COMM12: not done yet
        clr.l   0x20(a5)                | release the Master
        clr.l   0x24(a5)                | and the Slave

        lea     0xC00004, a0            | VDP control port
        lea     0xC00000, a1            | VDP data port
        lea     vdp_regs(pc), a2
        moveq   #11-1, d0
3:      move.w  (a2)+, (a0)
        dbra    d0, 3b
        move.l  #0x40000000, (a0)       | clear all 64 KB of VRAM
        move.w  #0x8000-1, d0
4:      move.w  #0, (a1)
        dbra    d0, 4b
        move.l  #0xC0000000, (a0)       | CRAM 0: dark blue, 1: white
        move.w  #0x0600, (a1)
        move.w  #0x0EEE, (a1)
        move.l  #0x40000000, (a0)       | VRAM $0000: tile n = glyph n
        bsr     load_font
        move.w  #0x8144, (a0)           | display on

5:      move.w  (a0), d0                | once a frame, look at COMM12
        btst    #3, d0
        beq.s   5b
6:      move.w  (a0), d0
        btst    #3, d0
        bne.s   6b
        tst.w   0x2C(a5)
        beq.s   5b

        | Each row: label, predicted clocks per pass x 100, measured
        | clocks per pass x 100, and the raw count in hex.
        moveq   #10, d1
        lea     msg_a(pc), a2
        move.w  #2300, d6
        move.w  0x28(a5), d7            | COMM8: loop A, counts of 8 clocks
        bsr     row
        moveq   #12, d1
        lea     msg_b(pc), a2
        move.w  #1700, d6
        move.w  0x2A(a5), d7            | COMM10: loop B
        bsr     row

        moveq   #8, d0                  | ratio A / B x 1000: 23 / 17 predicted
        moveq   #14, d1
        lea     msg_ab(pc), a2
        bsr     print
        moveq   #12, d0
        moveq   #14, d1
        bsr     set_cursor
        move.w  #1353, d5
        bsr     put_dec
        move.w  #0, (a1)
        moveq   #0, d5
        move.w  0x28(a5), d2
        mulu    #1000, d2
        move.w  0x2A(a5), d3
        beq.s   7f                      | no count (the timer did not run)
        divu    d3, d2
        bvs.s   7f
        move.w  d2, d5
7:      bsr     put_dec
halt:
        bra.s   halt

| Row d1: the string at a2, then d6 and the count d7 as clocks per pass
| x 100 (count x 8 clocks x 100 / 16384 passes = count x 25 / 512),
| then d7 in hex.
row:
        moveq   #8, d0
        bsr     print
        moveq   #12, d0
        bsr     set_cursor
        move.w  d6, d5
        bsr     put_dec
        move.w  #0, (a1)
        move.w  d7, d5
        mulu    #25, d5
        lsr.l   #8, d5
        lsr.l   #1, d5
        bsr     put_dec
        move.w  #0, (a1)
        moveq   #4-1, d3                | four hex digits, high first
8:      rol.w   #4, d7
        move.w  d7, d2
        andi.w  #0x000F, d2
        addq.w  #3, d2                  | "0" is glyph 3, and "A"-"F" follow "9"
        move.w  d2, (a1)
        dbra    d3, 8b
        rts

| Write d5 (0-65535) as five decimal digits at the cursor.
put_dec:
        moveq   #0, d2
        move.w  d5, d2
        moveq   #5-1, d3
9:      divu    #10, d2                 | remainder in the high word
        swap    d2
        move.w  d2, -(sp)
        clr.w   d2
        swap    d2
        dbra    d3, 9b
        moveq   #5-1, d3
10:     move.w  (sp)+, d2
        addq.w  #3, d2
        move.w  d2, (a1)
        dbra    d3, 10b
        rts

        .include "text.inc"

vdp_regs:
        .word   0x8004, 0x8104, 0x8230, 0x8407, 0x8578, 0x8700
        .word   0x8B00, 0x8C81, 0x8D3F, 0x8F02, 0x9001

msg_a:  .asciz  "A"
msg_b:  .asciz  "B"
msg_ab: .asciz  "AB"
        .even
        .include "font.inc"

        .org    0x2000
sh2_start:
        .incbin "sh2.bin"
sh2_end:
        .org    0x20000
