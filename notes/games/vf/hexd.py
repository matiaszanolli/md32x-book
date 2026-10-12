#!/usr/bin/env python3
"""hexd.py BIN START [LEN] [W]  dump image words (START as SH-2 address or offset), W words per line (default 8, 16-bit)"""
import sys
d=open(sys.argv[1],'rb').read()
s=int(sys.argv[2],16)&0xFFFFFF
n=int(sys.argv[3],16) if len(sys.argv)>3 else 0x80
w=int(sys.argv[4]) if len(sys.argv)>4 else 8
for a in range(s,s+n,2*w):
    print('%08x '%(0x06000000+a)+' '.join('%04x'%int.from_bytes(d[i:i+2],'big') for i in range(a,min(a+2*w,len(d)),2)))
