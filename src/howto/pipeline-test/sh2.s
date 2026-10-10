! pipeline-test, SH-2 side. Linked at 0x06000000 (the start of SDRAM),
! so the program runs from SDRAM through the cache.
!
! The Master times one texture column loop at two alignments (A: loop
! label at 4n + 2, B: at 4n), each with its stores going to three places:
! on-chip RAM (no bus access at all), SDRAM (write-through: every store
! goes out on the bus) and the frame buffer. Six runs, each timed with the
! free-running timer and preceded by an untimed run that fills the cache.
!
! While the runs are timed:
! - the Master has SR = 0xF0: every interrupt masked;
! - the Slave is asleep with every interrupt masked, so it neither fetches
!   nor uses the bus; it says so in COMM6 before the Master starts;
! - the 68000 touches no 32X register or memory: it waits three seconds,
!   watching only the Mega Drive VDP, before it reads COMM0.
!
! Results: COMM2, COMM4 = on-chip RAM A, B; COMM8, COMM10 = SDRAM A, B;
! COMM12, COMM14 = frame buffer A, B, in counts of 32 clocks.
! COMM0 = 0x80 + one bit per run whose count overflowed (written last).

        .equ    PASSES, 16384           ! two pixels per pass

        .text
        .org    0
vectors:                                ! one table for both CPUs
        .rept   128
        .long   hang
        .endr

! run ROUTINE, DEST, STEP, COMM offset, overflow bit
        .macro  run routine, dest, step, off, bit
        mov.l   \dest, r10
        mov     #\step, r12
        bsr     \routine                ! untimed: fills the cache
        nop
        mov.l   \dest, r10
        mov     #\step, r12
        bsr     \routine                ! the run reported
        nop
        mov     r0, r12                 ! overflow flag
        mov.l   comm0, r3
        mov     r11, r0
        mov.w   r0, @(\off,r3)
        tst     r12, r12
        bt      9f
        mov     #\bit, r0
        or      r0, r15
9:
        .endm

! ANCHOR: master
        .org    0x200
        .global master_start
master_start:
        mov.l   sr_mask, r0             ! SR = 0xF0: interrupts masked
        ldc     r0, sr
        mov.l   sysreg, r14             ! r14 = 0x20004000
        mov.l   frt, r13                ! r13 = 0xFFFFFE10, free-running timer

1:      mov.l   @(0x20,r14), r0         ! wait until the 68000 has cleared M_OK
        tst     r0, r0
        bf      1b
2:      mov.l   @(0x24,r14), r0         ! and until the Slave is asleep:
        cmp/eq  #1, r0                  ! COMM4 = 0, COMM6 = 1
        bf      2b

        mov     #0x80, r0               ! FM = 1: the SH-2s get the frame buffer;
        mov.b   r0, @r14                ! the 32X VDP stays in blank mode

        mov.l   ccr, r1                 ! purge, then cache on in two-way mode:
        mov     #0, r0                  ! 2 KB of cache, and 2 KB of RAM at
        mov.b   r0, @r1                 ! 0xC0000000 for the stores that must
        mov     #0x19, r0               ! not reach the bus
        mov.b   r0, @r1

        mov.l   texture, r1             ! texel j = 127 - j, colour j = j
        mov.l   light, r4
        mov     #127, r2
        mov     #0, r0                  ! r0 = j
3:      mov     r2, r3
        sub     r0, r3
        mov.b   r3, @(r0,r1)
        mov.b   r0, @(r0,r4)
        add     #1, r0
        cmp/hi  r2, r0                  ! until j > 127
        bf      3b

        mov     #1, r0
        mov.b   r0, @(0,r13)            ! TIER: no timer interrupts
        mov     #0xE0, r0
        mov.b   r0, @(7,r13)            ! TOCR: outputs low on a match (a high
                                        ! FTOB on the Master resets the 32X)
        mov     #1, r0
        mov.b   r0, @(6,r13)            ! TCR: count the CPU clock / 32; wraps
                                        ! after 128 clocks a pass

        mov     #0, r15                 ! r15 collects the overflow bits
        run     time_a, to_ram,   0, 2,  1
        run     time_b, to_ram,   0, 4,  2
        run     time_a, to_sdram, 2, 8,  4
        run     time_b, to_sdram, 2, 10, 8
        run     time_a, to_fb,    2, 12, 16
        run     time_b, to_fb,    2, 14, 32

        mov.l   comm0, r3
        mov     r15, r0
        or      #0x80, r0
        mov.w   r0, @(0,r3)             ! COMM0: done, and the overflow bits
4:      sleep
        bra     4b
        nop
! ANCHOR_END: master

! ANCHOR: loop
! time_a and time_b run the same loop, 16 instructions for two pixels:
! load a texel, look up its colour, store it, step on. Before the loop
! label they pad with nops, executed once, so that the label of time_a
! is at 16n + 10 (4n + 2, where d32xr's I_DrawColumnA loop sits) and
! that of time_b at 16n + 12 (4n).
! In: r10 = destination, r12 = destination step.
! Out: r11 = FRC (32 clocks a count), r0 = nonzero if FRC overflowed.
        .macro  column_test pad
        mov.l   texture, r5             ! r5 = texels
        mov.l   light, r7               ! r7 = light table
        mov     r10, r8                 ! r8 = destination
        mov     r12, r1                 ! r1 = destination step (d32xr: 320)
        mov.l   start_pos, r2           ! r2 = texture position, 16.16
        mov.l   step, r3                ! r3 = texture step, 16.16
        mov     #127, r4                ! r4 = texture height - 1
        mov.l   passes, r6              ! r6 = passes
        mov.b   @(1,r13), r0            ! FTCSR: read the flags, then write 0
        mov     #0, r0                  ! to clear them, overflow included
        mov.b   r0, @(1,r13)
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
        or      r0, r11
        mov.b   @(1,r13), r0            ! FTCSR bit 1: the counter overflowed
        rts
        and     #2, r0
        .endm

time_a: column_test 5                   ! loop label at 16n + 10
time_b: column_test 6                   ! loop label at 16n + 12
! ANCHOR_END: loop

hang:   bra     hang
        nop

        .align  4
sr_mask:  .long 0x000000F0
sysreg:   .long 0x20004000
frt:      .long 0xFFFFFE10
ccr:      .long 0xFFFFFE92
comm0:    .long 0x20004020
texture:  .long 0x06010000              ! 128 bytes
light:    .long 0x06010080              ! 128 bytes
to_ram:   .long 0xC0000000              ! on-chip RAM, two-way mode
to_sdram: .long 0x06020000              ! SDRAM through the cache, 64 KB
to_fb:    .long 0x24000200              ! frame buffer, 64 KB
start_pos: .long 0x00000000
step:     .long 0x0000C000              ! 0.75 texels a pixel
passes:   .long PASSES

        .org    0x600
slave_start:
        mov.l   s_sr_mask, r0           ! SR = 0xF0: interrupts masked
        ldc     r0, sr
        mov.l   s_sysreg, r14
1:      mov.l   @(0x24,r14), r0         ! wait until the 68000 has cleared S_OK
        tst     r0, r0
        bf      1b
        mov     #1, r0
        mov.l   r0, @(0x24,r14)         ! COMM4 = 0, COMM6 = 1: about to sleep
2:      sleep                           ! nothing wakes it: no fetches, no bus
        bra     2b
        nop
        .align  4
s_sr_mask: .long 0x000000F0
s_sysreg: .long 0x20004000
