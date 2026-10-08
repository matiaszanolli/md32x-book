! hello32x, SH-2 side. Linked at 0x06000000 (the start of SDRAM).
! Master: takes the VDP, sets up the line tables and palette, then each
! frame flips the buffers, clears the new back buffer with auto fill,
! tells the Slave to draw, draws its own square and waits for the Slave.
! Slave: waits for a frame number in COMM12, draws its square, answers
! in COMM14. No interrupts are used; both CPUs keep SR = 0xF0.

        .text
        .org    0
vectors:                        ! one table for both CPUs: every vector hangs
        .rept   128
        .long   hang
        .endr

! ANCHOR: master_setup
        .org    0x200
        .global master_start
master_start:
        mov.l   sysreg, r14     ! r14 = 0x20004000, system registers
        mov.l   vdpreg, r13     ! r13 = 0x20004100, VDP registers
        mov.l   comm12, r11     ! r11 = 0x2000402C, Master -> Slave
        mov.l   comm14, r10     ! r10 = 0x2000402E, Slave -> Master

        ! 1. wait until the 68000 has cleared M_OK
1:      mov.l   @(0x20,r14), r0
        tst     r0, r0
        bf      1b

        ! 2. take the VDP, palette and frame buffer: FM = 1
        mov     #0x80, r0
        mov.b   r0, @r14        ! byte write: changes FM only

        ! 3. palette, while the VDP is still in blank mode
        mov.l   palette, r1
        mov.w   col_bg, r0
        mov.w   r0, @r1         ! 0: dark blue
        mov.w   col_m, r0
        mov.w   r0, @(2,r1)     ! 1: yellow, the Master's square
        mov.w   col_s, r0
        mov.w   r0, @(4,r1)     ! 2: green, the Slave's square

        ! 4. a line table in each frame buffer
        bsr     line_table
        nop
        mov.w   @(10,r13), r0   ! flip FS; in blank mode it takes effect at once
        xor     #1, r0
        mov.w   r0, @(10,r13)
        mov     r0, r1
2:      mov.w   @(10,r13), r0   ! wait until FS reads back the new value
        xor     r1, r0
        tst     #1, r0
        bf      2b
        bsr     line_table
        nop

        ! 5. packed pixel mode, PRI = 0 (Mega Drive in front)
        mov     #1, r0
        mov.w   r0, @(0,r13)

        mov     #1, r12         ! r12 = frame number
! ANCHOR_END: master_setup
! ANCHOR: master_frame
frame:
        ! wait for the start of vertical blank (VBLK is bit 15)
3:      mov.w   @(10,r13), r0
        cmp/pz  r0
        bf      3b              ! still in the last blank
4:      mov.w   @(10,r13), r0
        cmp/pz  r0
        bt      4b              ! still displaying

        ! show the buffer we drew last frame
        xor     #1, r0
        mov.w   r0, @(10,r13)
        mov     r0, r1
5:      mov.w   @(10,r13), r0
        xor     r1, r0
        tst     #1, r0
        bf      5b

        ! clear the new back buffer: 140 fills of 256 words from word 0x100
        mov.w   w0100, r3
        mov.w   w008c, r4       ! 140: mov #imm is signed 8-bit, so it cannot hold 140
6:      mov.w   w00ff, r0
        mov.w   r0, @(4,r13)    ! length - 1
        mov     r3, r0
        mov.w   r0, @(6,r13)    ! start address
        mov     #0, r0
        mov.w   r0, @(8,r13)    ! data: writing it starts the fill
7:      mov.w   @(10,r13), r0
        tst     #2, r0          ! FEN
        bf      7b
        mov.w   w0100, r0
        add     r0, r3
        dt      r4
        bf      6b

        ! tell the Slave which frame to draw
        mov     r12, r0
        mov.w   r0, @r11

        ! draw the Master's square: x = (frame & 127) * 2, y = 40
        mov     r12, r5
        mov     #127, r0
        and     r0, r5
        add     r5, r5
        mov     #40, r6
        mov.w   pix_m, r7
        bsr     square
        nop

        ! wait for the Slave to report the same frame number
8:      mov.w   @r10, r0
        extu.w  r0, r0
        cmp/eq  r12, r0
        bf      8b

        bra     frame
        add     #1, r12

! ANCHOR_END: master_frame
! ANCHOR: helpers
! line_table: entries 0-223 of the back buffer point at 0x100 + 160 * n
line_table:
        mov.l   fb, r1
        mov.w   w0100, r2
        mov.w   w00a0, r3
        mov.w   w00e0, r4
1:      mov.w   r2, @r1
        add     #2, r1
        add     r3, r2
        dt      r4
        bf      1b
        rts
        nop

! square: 32 x 32 pixels at x = r5 (even), y = r6, two pixels per word in r7
square:
        mov.l   fb_pix, r1      ! 0x24000200: word 0x100 of the back buffer
        mov.w   w0140, r2       ! 320 bytes per line
        mulu.w  r6, r2
        sts     macl, r0
        add     r0, r1
        add     r5, r1
        mov     #32, r3
1:      mov     r1, r8
        mov     #16, r4
2:      mov.w   r7, @r8
        dt      r4
        bf/s    2b
        add     #2, r8
        mov.w   w0140, r0
        add     r0, r1
        dt      r3
        bf      1b
        rts
        nop

! ANCHOR_END: helpers
hang:   bra     hang
        nop

        .align  2
w0100:  .word   0x0100
w00ff:  .word   0x00ff
w008c:  .word   140
w00a0:  .word   160
w00e0:  .word   224
w0140:  .word   320
col_bg: .word   0x3000          ! RGB555, red in the low bits: blue 12
col_m:  .word   0x03ff          ! red 31, green 31
col_s:  .word   0x03e0          ! green 31
pix_m:  .word   0x0101
        .align  4
sysreg: .long   0x20004000
vdpreg: .long   0x20004100
palette: .long  0x20004200
comm12: .long   0x2000402C
comm14: .long   0x2000402E
fb:     .long   0x24000000
fb_pix: .long   0x24000200

! ANCHOR: slave
        .org    0x400
slave_start:
        mov.l   s_sysreg, r14
        mov.l   s_comm12, r11
        mov.l   s_comm14, r10

        ! wait until the 68000 has cleared S_OK
1:      mov.l   @(0x24,r14), r0
        tst     r0, r0
        bf      1b

        mov     #0, r12         ! last frame drawn
2:      mov.w   @r11, r0        ! wait for a new frame number
        extu.w  r0, r0
        cmp/eq  r12, r0
        bt      2b
        mov     r0, r12

        ! x = 254 - (frame & 127) * 2, y = 150
        mov     #127, r5
        and     r12, r5
        add     r5, r5
        mov.w   s_w254, r0
        sub     r5, r0
        mov     r0, r5
        mov.w   s_w150, r6
        mov.w   s_pix, r7
        bsr     square
        nop

        mov     r12, r0         ! report the frame as done
        mov.w   r0, @r10
        bra     2b
        nop

! ANCHOR_END: slave
        .align  2
s_w254: .word   254
s_w150: .word   150
s_pix:  .word   0x0202
        .align  4
s_sysreg: .long 0x20004000
s_comm12: .long 0x2000402C
s_comm14: .long 0x2000402E
        .align  4
