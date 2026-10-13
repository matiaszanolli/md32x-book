# usage: python3 input.py FRAMES OUT.csv [MASK]   (MASK 259 = B+Y+A, which drives)
# Start at frames 200, 700, 850 and 1,100 reaches the first race at about 1,500;
# from 1,500 hold MASK and steer left, centre, right, centre for 120 frames each.
import sys
n=int(sys.argv[1]); acc=int(sys.argv[3]) if len(sys.argv)>3 else 1
rows=['frame,mask']
for f in range(n):
    m=0
    if any(s<=f<s+4 for s in (200,700,850,1100)): m=8
    if f>=1500:
        m=acc
        m|=(0,64,0,128)[(f//120)%4]
    rows.append('%d,%d'%(f,m))
open(sys.argv[2],'w').write('\n'.join(rows)+'\n')
