! pipeline-test, SH-2 side. Linked at 0x06000000 (the start of SDRAM),
! so the program runs from SDRAM through the cache.
! The Master times one texture column loop at two alignments with the
! free-running timer and leaves the two counts in COMM8 and COMM10 for
! the 68000 to print. The Slave does nothing. No interrupts are used;
! both CPUs keep SR = 0xF0.

        .equ    PASSES, 16384           ! two pixels per pass

        .text
        .org    0
vectors:                                ! one table for both CPUs
        .rept   128
        .long   hang
        .endr

! ANCHOR: master
        .org    0x200
        .global master_start
master_start:
        mov.l   sysreg, r14             ! r14 = 0x20004000
        mov.l   frt, r13                ! r13 = 0xFFFFFE10, free-running timer

1:      mov.l   @(0x20,r14), r0         ! wait until the 68000 has cleared M_OK
        tst     r0, r0
        bf      1b

        mov     #0x80, r0               ! FM = 1: the SH-2s get the frame buffer;
        mov.b   r0, @r14                ! the 32X VDP stays in blank mode

        mov.l   ccr, r1                 ! purge and enable the cache
        mov     #0, r0
        mov.b   r0, @r1
        mov     #0x11, r0
        mov.b   r0, @r1

        mov.l   texture, r1             ! texel j = 127 - j, colour j = j
        mov.l   light, r4
        mov     #127, r2
        mov     #0, r0                  ! r0 = j
2:      mov     r2, r3
        sub     r0, r3
        mov.b   r3, @(r0,r1)
        mov.b   r0, @(r0,r4)
        add     #1, r0
        cmp/hi  r2, r0                  ! until j > 127
        bf      2b

        mov     #1, r0
        mov.b   r0, @(0,r13)            ! TIER: no timer interrupts
        mov     #0, r0
        mov.b   r0, @(1,r13)            ! FTCSR: flags clear, no clear on match A
        mov     #0xE0, r0
        mov.b   r0, @(7,r13)            ! TOCR: outputs low on a match (a high
                                        ! FTOB on the Master resets the 32X)
        mov     #0, r0
        mov.b   r0, @(6,r13)            ! TCR: count the CPU clock / 8

        bsr     time_a                  ! first run fills the cache
        nop
        bsr     time_a                  ! second run is the one reported
        nop
        mov     r11, r12
        bsr     time_b
        nop
        bsr     time_b
        nop

        mov.l   comm8, r1               ! COMM8 = loop A, COMM10 = loop B,
        mov.w   r12, @r1                ! in counts of 8 clocks
        mov     r11, r0
        mov.w   r0, @(2,r1)
        mov     #1, r0
        mov.w   r0, @(4,r1)             ! COMM12 = 1: done
3:      sleep
        bra     3b
        nop
! ANCHOR_END: master

! ANCHOR: loop
! time_a and time_b run the same loop, 16 instructions for two pixels:
! load a texel, look up its colour, store it, step down. Before the loop
! label they pad with nops, executed once, so that the label of time_a
! is at 16n + 10 (4n + 2, where d32xr's I_DrawColumnA loop sits) and
! that of time_b at 16n + 12 (4n). Result: r11 = FRC, 8 clocks a count.
        .macro  column_test pad
        mov.l   texture, r5             ! r5 = texels
        mov.l   light, r7               ! r7 = light table
        mov.l   fb_dest, r8             ! r8 = destination in the frame buffer
        mov     #2, r1                  ! r1 = destination step (d32xr: 320)
        mov.l   start_pos, r2           ! r2 = texture position, 16.16
        mov.l   step, r3                ! r3 = texture step, 16.16
        mov     #127, r4                ! r4 = texture height - 1
        mov.l   passes, r6              ! r6 = passes
        mov     #0, r0
        mov.b   r0, @(2,r13)            ! FRC high byte, held until ...
        mov.b   r0, @(3,r13)            ! ... the low byte: FRC = 0
        swap.w  r2, r0
        and     r4, r0                  ! r0 = first texel index
        .balignw 16, 0x0009
        .rept   \pad
        nop
        .endr
1:      mov.b   @(r0,r5), r0            ! texel
        add     r3, r2                  ! step the position
        mov.b   @(r0,r7), r9            ! its colour
        swap.w  r2, r0                  ! integer part of the position
        mov.b   r9, @r8                 ! store the pixel
        and     r4, r0                  ! wrap to the texture height
        add     r1, r8                  ! next destination
        dt      r6                      ! count the pass
        mov.b   @(r0,r5), r0            ! second pixel, the same way
        add     r3, r2
        mov.b   @(r0,r7), r9
        swap.w  r2, r0
        mov.b   r9, @r8
        and     r4, r0
        bf/s    1b
        add     r1, r8                  ! delay slot: next destination
        mov.b   @(2,r13), r0            ! FRC high byte; the low byte is latched
        extu.b  r0, r11
        shll8   r11
        mov.b   @(3,r13), r0
        extu.b  r0, r0
        rts
        or      r0, r11
        .endm

time_a: column_test 5                   ! loop label at 16n + 10
time_b: column_test 6                   ! loop label at 16n + 12
! ANCHOR_END: loop

hang:   bra     hang
        nop

        .align  4
sysreg:   .long 0x20004000
frt:      .long 0xFFFFFE10
ccr:      .long 0xFFFFFE92
comm8:    .long 0x20004028
texture:  .long 0x06010000              ! 128 bytes
light:    .long 0x06010080              ! 128 bytes
fb_dest:  .long 0x24000200              ! 64 KB written, two bytes a pass
start_pos: .long 0x00000000
step:     .long 0x0000C000              ! 0.75 texels a pixel
passes:   .long PASSES

        .org    0x400
slave_start:
        mov.l   s_sysreg, r14
1:      mov.l   @(0x24,r14), r0         ! wait until the 68000 has cleared S_OK
        tst     r0, r0
        bf      1b
2:      sleep                           ! nothing to do: keep off the bus
        bra     2b
        nop
        .align  4
s_sysreg: .long 0x20004000
