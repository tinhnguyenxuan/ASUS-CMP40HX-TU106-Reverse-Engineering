#!/usr/bin/env python3
"""OPT_SM_SPEED_SELECT override test. 9 regs 0x210D4-0x210F4.
Writes 0 (=full speed per Ampere doc), measures, restores."""
import os,mmap,struct,sys,subprocess
f=os.open('/sys/bus/pci/devices/0000:03:00.0/resource0',os.O_RDWR|os.O_SYNC)
m=mmap.mmap(f,16*1024*1024,mmap.MAP_SHARED,mmap.PROT_READ|mmap.PROT_WRITE)
rd=lambda a: struct.unpack_from('<I',m,a)[0]
wr=lambda a,v: struct.pack_into('<I',m,a,v)
REGS=[0x210D4,0x210D8,0x210DC,0x210E0,0x210E4,0x210E8,0x210EC,0x210F0,0x210F4]

def bench(tag):
    r=subprocess.run(['nvidia-smi','--query-gpu=clocks.sm,clocks.max.sm,utilization.gpu,power.draw',
                      '--format=csv,noheader'],capture_output=True,text=True)
    print(f"  [{tag}] {r.stdout.strip()}")

print("=== BEFORE ===")
for a in REGS: print(f"  0x{a:05X} = 0x{rd(a):08X}")
bench("before")

mode=sys.argv[1] if len(sys.argv)>1 else 'zero'
if mode=='zero':
    print("\n=== WRITE 0x00000000 to all 9 ===")
    for a in REGS:
        o=rd(a); wr(a,0x00000000); n=rd(a)
        print(f"  0x{a:05X}: 0x{o:08X} -> 0x{n:08X} {'STUCK' if n==0 else 'BOUNCED'}")
elif mode=='zeroff':
    print("\n=== WRITE 0x00000000 (with 0x21830/0x21834 pre-set) ===")
    for a in (0x21830,0x21834):
        wr(a,0xF); print(f"  0x{a:05X} = 0x{rd(a):08X}")
    for a in REGS:
        o=rd(a); wr(a,0x00000000); n=rd(a)
        print(f"  0x{a:05X}: 0x{o:08X} -> 0x{n:08X} {'STUCK' if n==0 else 'BOUNCED'}")
elif mode=='restore':
    D={0x210D4:0xFFFFFFFC,0x210D8:0xFFFFFF8F,0x210DC:0xFFFFFF8F,0x210E0:0xFFFFFF8F,
       0x210E4:0xFFFFFF8F,0x210E8:0xFFFFFFFC,0x210EC:0xFFFFFFFC,0x210F0:0xFFFFFFFC,
       0x210F4:0xFFFFFF8F}
    for a in REGS: wr(a,D[a])
    print("  restored")

print("\n=== AFTER ===")
for a in REGS: print(f"  0x{a:05X} = 0x{rd(a):08X}")
bench("after")
m.close(); os.close(f)
