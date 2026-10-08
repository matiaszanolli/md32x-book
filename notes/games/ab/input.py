# usage: python3 input.py FRAMES OUT.csv [SKIP]
# Start at frames 300, 420 and 540 reaches the first stage (a fourth press
# pauses it); from frame 1100, fire (B) every other 20 frames, missile (A) one
# 45-frame period in three, and steer left, centre, right, up for 180 frames each.
# SKIP drops the first SKIP rows, for a replay that starts from a save state.
import sys
n=int(sys.argv[1]); skip=int(sys.argv[3]) if len(sys.argv)>3 else 0
rows=['frame,mask']
for i in range(n):
    f=i+skip; m=0
    if any(s<=f<s+4 for s in (300,420,540)): m=8
    if f>=1100:
        m=1 if (f//20)%2==0 else 0
        m|=256 if (f//45)%3==0 else 0
        m|=(64,0,128,16)[(f//180)%4]
    rows.append('%d,%d'%(i,m))
open(sys.argv[2],'w').write('\n'.join(rows)+'\n')
