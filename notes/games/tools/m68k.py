# usage: python3 m68k.py ROM START COUNT   (START in hex)
# Disassembles COUNT 68000 instructions from a ROM offset with capstone.
import capstone,sys
d=open(sys.argv[1],'rb').read()
md=capstone.Cs(capstone.CS_ARCH_M68K, capstone.CS_MODE_BIG_ENDIAN|capstone.CS_MODE_M68K_000)
s=int(sys.argv[2],16); n=int(sys.argv[3])
for k,i in enumerate(md.disasm(d[s:s+n*10],s)):
    if k>=n: break
    print('%06X %-8s %s'%(i.address,i.mnemonic,i.op_str))
