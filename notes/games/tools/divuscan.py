import sys,glob,os,struct
# Usage: divuscan.py ROM [ROM ...]  (see notes/games/tools/README.md)
# Find SH-2 code that loads a register with 0xFFFFFF00 and then accesses the DIVU via @(disp,Rn).
def scan(d):
    res=[]
    n=len(d)
    for i in range(0,n-1,2):
        w=struct.unpack('>H',d[i:i+2])[0]
        r=None
        if w>>12==0x9:  # mov.w @(disp,PC),Rn
            a=i+4+(w&0xff)*2
            if a+2<=n and d[a:a+2]==b'\xff\x00': r=(w>>8)&15
        elif w>>12==0xD:
            a=((i+4)&~3)+(w&0xff)*4
            if a+4<=n and d[a:a+4]==b'\xff\xff\xff\x00': r=(w>>8)&15
        if r is None: continue
        acc=[]
        for j in range(i+2,min(n-1,i+2+2*80),2):
            v=struct.unpack('>H',d[j:j+2])[0]
            top=v>>12; rn=(v>>8)&15; rm=(v>>4)&15; disp=v&15
            if top==0x5 and rm==r: acc.append(f"R{disp*4:02X}")
            elif top==0x1 and rn==r: acc.append(f"W{disp*4:02X}")
            elif ((top in (0x6,0x5,0xD,0x9,0xE) and rn==r) or (top==0x7 and rn==r)) : break
        if acc: res.append((i,acc))
    return res
for f in sys.argv[1:]:
    d=open(f,'rb').read()
    res=scan(d)
    hits=[x for x in res if any(a in ('R18','R1C','W18','W1C') for a in x[1])]
    print(f"== {os.path.basename(f)[:50]}: {len(res)} DIVU-base sites, {len(hits)} touching +18/+1C")
    for i,acc in res:
        print(f"   ${i:06X}: {' '.join(acc[:14])}")
