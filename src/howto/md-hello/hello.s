| hellomd: the smallest Mega Drive program in this book that sets up the
| VDP, loads a font and a palette, and prints text. Written from scratch;
| it contains no Sega code. Linked at 0. build.sh fills in the checksum.

        .text
| ANCHOR: vectors
| ---- $000: 68000 vectors
        .long   0x00FFFE00              | initial stack pointer
        .long   start                   | reset
        .rept   28                      | vectors 2-29: errors, traps, levels 1-5
        .long   crash
        .endr
        .long   vblank                  | vector 30: level 6, the vertical interrupt
        .rept   33                      | vectors 31-63
        .long   crash
        .endr
| ANCHOR_END: vectors

| ANCHOR: header
| ---- $100: header (see "Mega Drive ROM header and checksum")
        .org    0x100
        .ascii  "SEGA MEGA DRIVE "
        .ascii  "(C)BOOK 2026.OCT"
        .ascii  "HELLO WORLD                                     "
        .ascii  "HELLO WORLD                                     "
        .ascii  "GM 00000000-00"
        .word   0                       | checksum: build.sh writes it
        .ascii  "J               "
        .long   0x00000000, 0x0001FFFF  | ROM start and end
        .long   0x00FF0000, 0x00FFFFFF  | RAM start and end
        .ascii  "            "          | no external RAM
        .ascii  "            "          | no modem
        .ascii  "                                        "
        .ascii  "JUE             "
| ANCHOR_END: header

        .equ    VDP_DATA, 0xC00000
        .equ    VDP_CTRL, 0xC00004
        .equ    frames,   0xFF0000      | a longword in work RAM

| ANCHOR: start
| ---- $200: start-up
start:
        move.w  #0x2700, sr             | no interrupts until we are ready

        move.b  0xA10001, d0            | version register
        andi.b  #0x0F, d0
        beq.s   1f                      | version 0: no TMSS
        move.l  #0x53454741, 0xA14000   | "SEGA": unlocks the VDP
1:
        lea     VDP_CTRL, a0
        lea     VDP_DATA, a1
        tst.w   (a0)                    | forget any half-written command

        lea     vdp_regs(pc), a2        | 19 registers, display still off
        moveq   #19-1, d0
2:      move.w  (a2)+, (a0)
        dbra    d0, 2b
| ANCHOR_END: start

| ANCHOR: clear
        moveq   #0, d1
        move.l  #0x40000000, (a0)       | VRAM write from $0000
        move.w  #0x8000-1, d0           | 32,768 words: all 64 KB
3:      move.w  d1, (a1)
        dbra    d0, 3b

        move.l  #0xC0000000, (a0)       | CRAM write from 0
        moveq   #64-1, d0
4:      move.w  d1, (a1)
        dbra    d0, 4b

        move.l  #0x40000010, (a0)       | VSRAM write from 0
        moveq   #40-1, d0
5:      move.w  d1, (a1)
        dbra    d0, 5b

        lea     0xC00011, a2            | PSG: all four channels silent
        move.b  #0x9F, (a2)
        move.b  #0xBF, (a2)
        move.b  #0xDF, (a2)
        move.b  #0xFF, (a2)
| ANCHOR_END: clear

| ANCHOR: font
        move.l  #0xC0000000, (a0)       | CRAM word 0: backdrop, dark blue
        move.w  #0x0600, (a1)
        move.w  #0x0EEE, (a1)           | CRAM word 1: white, for the text

        move.l  #0x40000000, (a0)       | VRAM $0000: tile n = glyph n
        bsr     load_font               | expand the font into tiles 0-26
| ANCHOR_END: font

| ANCHOR: print
        moveq   #14, d0                 | column
        moveq   #12, d1                 | row
        lea     msg_hello(pc), a2
        bsr     print
        moveq   #14, d0
        moveq   #14, d1
        lea     msg_frame(pc), a2
        bsr     print

        clr.l   frames
        move.w  #0x8164, (a0)           | display on, vertical interrupt on
        move.w  #0x2500, sr             | accept level 6 and above
| ANCHOR_END: print

| ANCHOR: loop
loop:
        move.l  frames, d5
9:      cmp.l   frames, d5              | sleep until the interrupt counts a frame
        beq.s   9b

        moveq   #20, d0                 | it is now early in vertical blank
        moveq   #14, d1
        bsr     set_cursor
        move.l  frames, d5
        bsr     put_hex                 | the count's low word, in hex
        bra.s   loop

vblank:
        addq.l  #1, frames
        rte
| ANCHOR_END: loop

        .include "text.inc"

| Any other exception: red screen, stop.
crash:
        move.w  #0x2700, sr
        move.l  #0xC0000000, VDP_CTRL
        move.w  #0x000E, VDP_DATA
        bra.s   crash

| ANCHOR: regs
vdp_regs:
        .word   0x8004                  | 0: line interrupt off
        .word   0x8104                  | 1: display off, mode 5
        .word   0x8230                  | 2: plane A at $C000
        .word   0x833C                  | 3: window at $F000
        .word   0x8407                  | 4: plane B at $E000
        .word   0x856C                  | 5: sprite table at $D800
        .word   0x8600
        .word   0x8700                  | 7: backdrop = palette 0, colour 0
        .word   0x8800
        .word   0x8900
        .word   0x8A00                  | 10: line counter
        .word   0x8B00                  | 11: whole-screen scrolling
        .word   0x8C81                  | 12: 320 pixels wide (H40)
        .word   0x8D37                  | 13: horizontal scroll table at $DC00
        .word   0x8E00
        .word   0x8F02                  | 15: auto-increment 2
        .word   0x9001                  | 16: planes 64 x 32 cells
        .word   0x9100                  | 17, 18: no window
        .word   0x9200
| ANCHOR_END: regs

msg_hello:
        .asciz  "HELLO, WORLD!"
msg_frame:
        .asciz  "FRAME"
        .even

        .include "font.inc"

        .org    0x20000                 | pad to 128 KB
