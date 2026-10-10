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
        .long   0x06000600              | Slave entry
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
        clr.l   0x24(a5)                | release the Slave, which goes to sleep,
        clr.l   0x20(a5)                | then the Master, which waits for it

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

        | The twelve runs take under 1.2 s even at 128 clocks a pass. Keep off the 32X for three
        | seconds, watching only the Mega Drive VDP, then look at COMM0
        | once a frame.
        move.w  #180, d7
5:      bsr     next_frame
        subq.w  #1, d7
        bne.s   5b
6:      tst.w   0x20(a5)
        bne.s   7f
        bsr     next_frame
        bra.s   6b
7:      lea     results, a4             | copy COMM0-COMM14 to work RAM
        moveq   #8-1, d0
        lea     0x20(a5), a2
8:      move.w  (a2)+, (a4)+
        dbra    d0, 8b

        moveq   #6, d1                  | column headings
        moveq   #12, d0
        lea     msg_a(pc), a2
        bsr     print
        moveq   #19, d0
        lea     msg_b(pc), a2
        bsr     print
        moveq   #24, d0
        lea     msg_ab(pc), a2
        bsr     print

        moveq   #8, d1                  | clocks per pass x 100
        lea     msg_calc(pc), a2
        lea     calc(pc), a4
        moveq   #0, d6
        bsr     row
        moveq   #10, d1
        lea     msg_ram(pc), a2
        lea     results+2, a4
        moveq   #1, d6
        bsr     row
        moveq   #12, d1
        lea     msg_sdram(pc), a2
        lea     results+8, a4
        moveq   #4, d6
        bsr     row
        moveq   #14, d1
        lea     msg_fb(pc), a2
        lea     results+12, a4
        moveq   #16, d6
        bsr     row

        moveq   #17, d1                 | the raw counts, 32 clocks each
        lea     msg_ram(pc), a2
        lea     results+2, a4
        bsr     hexrow
        moveq   #19, d1
        lea     msg_sdram(pc), a2
        lea     results+8, a4
        bsr     hexrow
        moveq   #21, d1
        lea     msg_fb(pc), a2
        lea     results+12, a4
        bsr     hexrow
halt:
        bra.s   halt

| Wait for the start of the next vertical blank.
next_frame:
        move.w  (a0), d0
        btst    #3, d0
        bne.s   next_frame
1:      move.w  (a0), d0
        btst    #3, d0
        beq.s   1b
        rts

| Row d1: the string at a2, then the counts at (a4) and 2(a4) as clocks
| per pass x 100, each followed by "!" if its overflow bit (d6 for A,
| d6 x 2 for B) is set in COMM0, then A - B.
row:
        moveq   #3, d0
        bsr     print
        move.w  (a4), d5
        bsr     per_pass
        move.w  d5, d7                  | A
        moveq   #10, d0
        bsr     set_cursor
        bsr     put_dec
        bsr     flag
        move.w  2(a4), d5
        bsr     per_pass
        movea.w d5, a6                  | B
        moveq   #17, d0
        bsr     set_cursor
        bsr     put_dec
        add.w   d6, d6
        bsr     flag
        moveq   #23, d0
        bsr     set_cursor
        move.w  d7, d5
        sub.w   a6, d5                  | A - B, signed
        bpl.s   1f
        neg.w   d5
        move.w  #26, (a1)               | "-"
        bra.s   2f
1:      move.w  #0, (a1)
2:      bsr     put_dec
        rts

| A count of 32 clocks over 16,384 passes, in d5, to clocks per pass
| x 100: count x 32 x 100 / 16384 = count x 25 / 128.
per_pass:
        mulu    #25, d5
        lsr.l   #7, d5
        rts

| "!" if the bit in d6 is set in COMM0, else a space.
flag:
        move.w  results, d2
        and.w   d6, d2
        beq.s   1f
        move.w  #1, (a1)                | "!"
        rts
1:      move.w  #0, (a1)
        rts

| Row d1: the string at a2, then the counts at (a4) and 2(a4) in hex.
hexrow:
        moveq   #3, d0
        bsr     print
        moveq   #11, d0
        bsr     set_cursor
        move.w  (a4), d5
        bsr     put_hex
        moveq   #18, d0
        bsr     set_cursor
        move.w  2(a4), d5
        bsr     put_hex
        rts

| Write d5 (0-65535) as five decimal digits at the cursor.
put_dec:
        moveq   #0, d2
        move.w  d5, d2
        moveq   #5-1, d3
1:      divu    #10, d2                 | remainder in the high word
        swap    d2
        move.w  d2, -(sp)
        clr.w   d2
        swap    d2
        dbra    d3, 1b
        moveq   #5-1, d3
2:      move.w  (sp)+, d2
        addq.w  #3, d2                  | "0" is glyph 3
        move.w  d2, (a1)
        dbra    d3, 2b
        rts

        .include "text.inc"

vdp_regs:
        .word   0x8004, 0x8104, 0x8230, 0x8407, 0x8578, 0x8700
        .word   0x8B00, 0x8C81, 0x8D3F, 0x8F02, 0x9001

msg_a:     .asciz "A"
msg_b:     .asciz "B"
msg_ab:    .asciz "A-B"
msg_calc:  .asciz "CALC"
msg_ram:   .asciz "RAM"
msg_sdram: .asciz "SDRAM"
msg_fb:    .asciz "FB"
        .even
calc:   .word   11776, 8704             | 23 and 17 clocks a pass, as counts
        .even
        .include "font.inc"

        .equ    results, 0xFF0000       | COMM0-COMM14, copied

        .org    0x2000
sh2_start:
        .incbin "sh2.bin"
sh2_end:
        .org    0x20000
