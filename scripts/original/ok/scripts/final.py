import os,mmap,struct,time
f=os.open('/sys/bus/pci/devices/0000:03:00.0/resource0',os.O_RDWR|os.O_SYNC)
m=mmap.mmap(f,16*1024*1024,mmap.MAP_SHARED,mmap.PROT_READ|mmap.PROT_WRITE)
rd=lambda a: struct.unpack_from('<I',m,a)[0]
wr=lambda a,v: struct.pack_into('<I',m,a,v)
A=0x210D4
print("=== PROOF: written value is irrelevant (access side-effect) ===")
for v in (0x00000000, 0xFFFFFFFF, 0x12345678, 0xFFFFFFFC):
    wr(A,v); print(f"  wrote 0x{v:08X} -> readback 0x{rd(A):08X}")
print("\n=== PROOF: repeated read changes value with NO write? ===")
for i in range(5):
    print(f"  read#{i} = 0x{rd(A):08X}"); time.sleep(0.05)
print("\n=== PROOF: is the field at 0x21830/0x21834 really writable & sticky? ===")
for a in (0x21830,0x21834):
    o=rd(a); wr(a,0xABCDEF01); n=rd(a)
    print(f"  0x{a:05X}: 0x{o:08X} -> wrote 0xABCDEF01 -> 0x{n:08X}")
    wr(a,o); print(f"           restored -> 0x{rd(a):08X}")
m.close(); os.close(f)
