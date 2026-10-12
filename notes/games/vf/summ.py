import collections,sys
names={1:'FB',2:'OVR',3:'SDRAM',4:'CART',5:'VDPREG',6:'PAL',7:'PWM',8:'SYSREG',9:'ONCHIP',10:'PERIPH',11:'BOOT',12:'OTHER'}
t=collections.Counter()
for l in open(sys.argv[1]):
    if not l.startswith("cpu"): continue
    p=l.split(); cpu='M' if p[0]=='cpu0' else 'S'; reg=names[int(p[1][6:])]; op=p[2]; w='bwl'[int(p[3][1:])]; n=int(p[6])
    t[(cpu,reg,op,w)]+=n
for k in sorted(t):
    if k[1] in ('FB','OVR','VDPREG','PAL','PWM','SYSREG','CART'): print(k,t[k])
