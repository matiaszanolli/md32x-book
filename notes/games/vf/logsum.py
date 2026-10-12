#!/usr/bin/env python3
"""Summarise a PD_M68K_LOG file (see patch_m68klog.py): one line per (pc, R/W, size, address)
with count, first and last frame, number of distinct values and the first few values.
usage: logsum.py LOG [--skip ADDR,ADDR]"""
import sys, collections
skip=set()
a=sys.argv[1:]
if '--skip' in a:
    i=a.index('--skip'); skip={int(x,16) for x in a[i+1].split(',')}; del a[i:i+2]
d=collections.OrderedDict()
for ln in open(a[0]):
    if ln.startswith('#'): print(ln.strip()); continue
    f,pc,op,sz,ad,v=ln.split()[:6]
    if int(ad,16) in skip: continue
    k=(int(pc,16),op,int(sz),ad)
    e=d.setdefault(k,[0,int(f),int(f),collections.Counter()])
    e[0]+=1; e[2]=int(f); e[3][v]+=1
for k in sorted(d, key=lambda k:(k[3],k[0],k[1])):
    n,f0,f1,vals=d[k]
    top=",".join("%s*%d"%(v,c) for v,c in vals.most_common(6))
    print("%06x %s%d %s n=%d f=%d-%d vals(%d): %s"%(k[0],k[1],k[2],k[3],n,f0,f1,len(vals),top))
