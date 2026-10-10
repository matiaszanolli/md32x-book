| Text helpers shared by the example programs: the font loader, the
| cursor and the string printer. Expects a0 = VDP control port and
| a1 = VDP data port, and font.inc assembled into the same program.

| ANCHOR: load_font
| Expand the 1-bit font into 4-bit tiles at the VRAM address already set.
load_font:
        lea     font(pc), a2
        move.w  #font_end-font-1, d2    | one byte per glyph row
6:      move.b  (a2)+, d1               | 8 pixels, 1 bit each
        moveq   #0, d4
        moveq   #8-1, d3
7:      lsl.l   #4, d4                  | make room for the next pixel
        add.b   d1, d1                  | leftmost bit into carry
        bcc.s   8f
        addq.l  #1, d4                  | set: colour 1
8:      dbra    d3, 7b
        move.l  d4, (a1)                | one tile row: 8 pixels, 4 bits each
        dbra    d2, 6b
        rts
| ANCHOR_END: load_font

| ANCHOR: helpers
| Point the VDP at plane A, column d0, row d1. Plane A is at $C000,
| 64 cells of 2 bytes per row.
set_cursor:
        move.w  d1, d2
        lsl.w   #6, d2                  | row * 64
        add.w   d0, d2
        add.w   d2, d2                  | * 2 bytes
        addi.w  #0xC000, d2             | VRAM address, 16 bits
        moveq   #0, d4
        move.w  d2, d4
        andi.w  #0x3FFF, d4             | address bits 13-0 ...
        ori.w   #0x4000, d4             | ... with CD1-0 = 01: VRAM write
        swap    d4
        rol.w   #2, d2                  | address bits 15-14 ...
        andi.w  #3, d2
        move.w  d2, d4                  | ... into the second word
        move.l  d4, (a0)
        rts

| Print the zero-terminated string at a2 at column d0, row d1.
print:
        bsr     set_cursor
11:     move.b  (a2)+, d2
        beq.s   13f
        lea     charset(pc), a3         | find the character's glyph number
        moveq   #0, d3
12:     cmp.b   (a3)+, d2
        beq.s   14f
        addq.w  #1, d3
        tst.b   (a3)
        bne.s   12b
        moveq   #0, d3                  | not in the font: blank
14:     move.w  d3, (a1)                | name table entry: palette 0, tile d3
        bra.s   11b
13:     rts

| Write the low word of d5 as four hex digits at the cursor.
put_hex:
        moveq   #4-1, d3                | four hex digits, high first
15:     rol.w   #4, d5
        move.w  d5, d2
        andi.w  #0x000F, d2
        addq.w  #3, d2                  | "0" is glyph 3, and "A"-"F" follow "9"
        move.w  d2, (a1)
        dbra    d3, 15b
        rts
| ANCHOR_END: helpers
