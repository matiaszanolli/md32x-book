import re,collections,struct,sys
ins={};order=[]
for l in open(sys.argv[1] if len(sys.argv)>1 else "mk2.txt"):
    m=re.match(r'\s*([0-9a-f]+):\t([0-9a-f]{2}) ([0-9a-f]{2}) +\t(\S+)\s*(.*)',l)
    if m: a=int(m.group(1),16); ins[a]=(m.group(4),m.group(5)); order.append(a)
seen=set(int(x,16) for x in open('codeset.txt').read().split())
funcs=sorted(int(x,16) for x in open('funcs.txt').read().split())
callers=collections.defaultdict(set)
for a in seen:
    if a in ins and ins[a][0]=='bsr':
        m=re.match(r'0x([0-9a-f]+)',ins[a][1]); callers[int(m.group(1),16)].add(a)
    if a in ins and ins[a][0]=='mov.l' and '!' in ins[a][1]:
        v=int(ins[a][1].split('!')[1],16)
        if v in funcs: callers[v].add(a)
fs=set(funcs)
rows=[]
for i,f in enumerate(funcs):
    nxt=funcs[i+1] if i+1<len(funcs) else 0x06008000
    body=[a for a in range(f,nxt,2) if a in seen]
    refs=set(); kinds=collections.Counter()
    for a in body:
        mn,op=ins[a]; kinds[mn]+=1
        if mn=='mov.l' and '!' in op:
            v=int(op.split('!')[1],16)
            if v>=0x20004000 and v<0x20004400: refs.add('reg%03x'%(v&0xfff))
            elif 0x24000000<=v<0x24020000: refs.add('FB')
            elif 0x24020000<=v<0x24040000: refs.add('OVR')
            elif 0x04000000<=v<0x04040000: refs.add('FBc')
            elif 0x02000000<=v<0x04000000: refs.add('ROM')
            elif v>=0xfffffe00: refs.add('io%03x'%(v&0xfff))
    muls=sum(kinds[k] for k in('muls.w','mulu.w','div1'))
    rows.append((f,len(body)*2,len(callers[f]),' '.join(sorted(refs)),muls))
for f,sz,nc,r,m in rows:
    print('%08x %5d calls=%2d mul/div=%2d %s'%(f,sz,nc,m,r))
