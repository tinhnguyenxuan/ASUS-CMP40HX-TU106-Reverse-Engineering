import os,mmap,struct
f=os.open('/sys/bus/pci/devices/0000:03:00.0/resource0',os.O_RDWR|os.O_SYNC)
m=mmap.mmap(f,16*1024*1024,mmap.MAP_SHARED,mmap.PROT_READ|mmap.PROT_WRITE)
rd=lambda a: struct.unpack_from('<I',m,a)[0]
print("=== state of the registers where restore failed ===")
exp={0x210D4:0xFFFFFFFC,0x210D8:0xFFFFFF8F,0x210DC:0xFFFFFF8F,0x210E0:0xFFFFFF8F,
     0x210E4:0xFFFFFF8F,0x210E8:0xFFFFFFFC,0x210EC:0xFFFFFFFC,0x210F0:0xFFFFFFFC,0x210F4:0xFFFFFF8F}
for a,e in exp.items():
    v=rd(a); print(f"  0x{a:05X}  pre=0x{e:08X}  now=0x{v:08X}  {'SAME' if v==e else 'CHANGED'}")
print("\n=== control block 0x21820-0x21860 ===")
for a in range(0x21820,0x21860,4): print(f"  0x{a:05X} = 0x{rd(a):08X}")
print("\n=== is it in the fuse-mirror region only? check 0x21000 ===")
print(f"  0x21000 = 0x{rd(0x21000):08X}   (768 rows of these are fuse mirror)")
m.close(); os.close(f)
