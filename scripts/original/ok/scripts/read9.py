import os,mmap,struct
f=os.open('/sys/bus/pci/devices/0000:03:00.0/resource0',os.O_RDWR|os.O_SYNC)
m=mmap.mmap(f,16*1024*1024,mmap.MAP_SHARED,mmap.PROT_READ|mmap.PROT_WRITE)
rd=lambda a: struct.unpack_from('<I',m,a)[0]
ORIG={0x210D4:0xFFFFFFFC,0x210D8:0xFFFFFF8F,0x210DC:0xFFFFFF8F,0x210E0:0xFFFFFF8F,
      0x210E4:0xFFFFFF8F,0x210E8:0xFFFFFFFC,0x210EC:0xFFFFFFFC,0x210F0:0xFFFFFFFC,
      0x210F4:0xFFFFFF8F}
print("=== 9 fuse regs after REBOOT vs factory original ===")
chg=0
for a,o in ORIG.items():
    v=rd(a); s='SAME' if v==o else 'CHANGED'
    if v!=o: chg+=1
    print(f"  0x{a:05X}  orig=0x{o:08X}  now=0x{v:08X}  {s}")
print(f"\n  changed={chg}/9  -> {'VOLATILE (reset by power cycle)' if chg==0 else 'PERSISTED across reboot'}")
print("\n=== reference regs ===")
for n,a in (('PMC_BOOT_0',0x0),('STATUS_OPT_TPC_GPC0',0x21C38),('STATUS_OPT_GPC',0x21C1C),
            ('CTRL_OPT_TPC_GPC0',0x21838),('0x21040',0x21040),('0x21830',0x21830),('0x21834',0x21834)):
    print(f"  {n:20s} 0x{a:05X} = 0x{rd(a):08X}")
m.close(); os.close(f)
