import re,struct,sys,collections
BASE=0x06000000
LISTING=sys.argv[1] if len(sys.argv)>1 else 'mk2.txt'
code=open(LISTING[:-4]+'.bin','rb').read()
ins={}
for l in open(LISTING):
    m=re.match(r'\s*([0-9a-f]+):\t([0-9a-f]{2}) ([0-9a-f]{2}) +\t(\S+)\s*(.*)',l)
    if m: ins[int(m.group(1),16)]=(m.group(4),m.group(5))
def L(a): o=a-BASE; return struct.unpack('>I',code[o:o+4])[0] if 0<=o<len(code)-3 else None
entries=[0x06000240,0x06000244,0x0600510c,0x060002d8,0x06004e24,0x060004cc]
# dispatcher tables
for t,n in ((0x0600030c,16),(0x06004e64,16),(0x06000564,32)):
    entries += [L(t+4*i) for i in range(n)]
tables=[]; seen=set(); funcs=set(entries); work=list(entries); jsr_unres=[]
while work:
    a=work.pop()
    if a is None or a in seen or not (BASE<=a<BASE+len(code)): continue
    regs={}
    while a not in seen and a in ins:
        seen.add(a); mn,op=ins[a]
        def tgt():
            m=re.match(r'0x([0-9a-f]+)',op); return int(m.group(1),16) if m else None
        if mn=='mov.l' and '!' in op and ',r' in op:
            rn=op.split('!')[0].split(',')[1].strip(); regs[rn]=int(op.split('!')[1],16)
        elif mn=='mova':
            pass
        if mn in('bra',):
            work.append(tgt()); seen.add(a+2); work.append(a+2) if False else None
            # delay slot
            d=a+2
            if d in ins: seen.add(d)
            break
        if mn in('bt','bf'):
            work.append(tgt())
        if mn in('bt.s','bf.s'):
            work.append(tgt())
        if mn=='bsr':
            t=tgt(); funcs.add(t); work.append(t)
        if mn in('jsr','jmp'):
            r=op.strip('@'); t=regs.get(r)
            if t and BASE<=t<BASE+len(code): (funcs.add(t) if mn=='jsr' else None); work.append(t)
            else:
                # jump table: look back for mov.l @(r0,rX),r0 with rX literal
                tb=None
                for b in range(a-2,a-12,-2):
                    if b in ins and ins[b][0]=='mov.l' and ins[b][1].startswith('@(r0,'):
                        rx=ins[b][1].split(',')[1].rstrip(')'); tb=regs.get(rx); break
                if tb:
                    k=0
                    while k<64:
                        v=L(tb+4*k)
                        if v is None or not (BASE<=v<BASE+len(code)) or v&1: break
                        work.append(v); (funcs.add(v) if mn=='jsr' else None); seen.add(tb+4*k); seen.add(tb+4*k+2); k+=1
                    tables.append((hex(a),hex(tb),k))
                else: jsr_unres.append((hex(a),mn,op,hex(t) if t else None))
            if mn=='jmp':
                seen.add(a+2); break
        if mn in('rts','rte','braf') :
            seen.add(a+2); break
        if mn=='.word' and op.startswith('0x'):
            break
        a+=2
print('code bytes',len(seen)*2,'of',len(code),'functions',len(funcs))
cnt=collections.Counter(ins[a][0] for a in seen if a in ins)
for k in ['mac.l','mac.w','dmuls.l','dmulu.l','mul.l','muls.w','mulu.w','div1','div0s','div0u','xtrct','swap.w','swap.b','sleep','tas.b','braf','bsrf','dt','bt.s','bf.s','clrmac','trapa']:
    print(k,cnt[k])
print('tables',tables); print('unresolved',len(jsr_unres)); print(jsr_unres[:30])
open('codeset.txt','w').write('\n'.join(hex(a) for a in sorted(seen)))
open('funcs.txt','w').write('\n'.join(hex(a) for a in sorted(funcs) if a))
