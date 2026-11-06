#!/usr/bin/env python3
"""Find writable registers in fuse window 0x021000-0x022000.
Writes 0xFFFFFFFF then restores original. Reports STUCK/RW/RO/POISON."""
import os,mmap,struct
BAR='/sys/bus/pci/devices/0000:03:00.0/resource0'
f=os.open(BAR,os.O_RDWR|os.O_SYNC)
m=mmap.mmap(f,16*1024*1024,mmap.MAP_SHARED,mmap.PROT_READ|mmap.PROT_WRITE)
rd=lambda a: struct.unpack_from('<I',m,a)[0]
wr=lambda a,v: struct.pack_into('<I',m,a,v)
P={0xbadf5040,0xbadf1300,0xbadf1100}
rw=[];ro=[];snap={}
for a in range(0x021000,0x022000,4):
    o=rd(a); snap[a]=o
    if o in P or o==0xFFFFFFFF or (o>>12) in (0xBADF2,0xBADF5,0xBADF1): continue
    wr(a,0xFFFFFFFF); n=rd(a); wr(a,o); back=rd(a)
    if n==0xFFFFFFFF: rw.append(a)
    elif n!=o: ro.append((a,o,n))
    if back!=o: print(f"  !! RESTORE FAIL 0x{a:05X} expected 0x{o:08X} got 0x{back:08X}")
print(f"=== WRITABLE (accept 0xFFFFFFFF): {len(rw)} ===")
for a in rw: print(f"  0x{a:05X}  orig=0x{snap[a]:08X}")
print(f"\n=== PARTIAL / masked write: {len(ro)} ===")
for a,o,n in ro[:20]: print(f"  0x{a:05X}  orig=0x{o:08X} -> wrote FF.. -> 0x{n:08X}")
m.close(); os.close(f)
