#!/usr/bin/env python3
"""P0: dump MO RONG vung fuse TU106, chi doc, theo trang 4KB de an toan.

Dung: sudo python3 fuse_dump2.py out.json [span_hex]
Mac dinh span 0x8000 (32 KB) tu 0x021000 -> phu 0x21000..0x29000.
Ghi tung trang, verify lai sau khi doc, khong ghi MMIO.
"""
import json
import mmap
import os
import struct
import sys

DEV = "/sys/bus/pci/devices/0000:03:00.0/resource0"
FUSE = 0x021000
POISON = (0xBADF5040, 0xBADF1300, 0xBADF1100)
PAGE = 0x1000


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "fuse2.json"
    span = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x8000

    fd = os.open(DEV, os.O_RDONLY | os.O_SYNC)
    mm = mmap.mmap(fd, 16 << 20, mmap.MAP_SHARED, mmap.PROT_READ)
    boot0 = struct.unpack_from("<I", mm, 0)[0]

    regs = {}
    pages = []
    for p in range(0, span, PAGE):
        vals = {}
        ok = True
        for a in range(0, PAGE, 4):
            try:
                vals[a] = struct.unpack_from("<I", mm, FUSE + p + a)[0]
            except Exception:
                ok = False
                break
        if not ok:
            break
        regs.update({p + a: v for a, v in vals.items()})
        nd = sum(1 for v in vals.values() if v not in POISON and v != 0)
        nb = sum(1 for v in vals.values() if v in POISON)
        pages.append(dict(off=p, data=nd, poison=nb))
        print(f"  trang 0x{p:05x}: {nd:>3d} co du lieu, {nb:>3d} poison")
        # dung som neu ca trang poison (ra ngoai khoi fuse)
        if nb == PAGE // 4:
            print(f"  -> trang 0x{p:05x} toan poison, dung dump")
            break

    mm.close()
    os.close(fd)

    nd = sum(1 for v in regs.values() if v not in POISON and v != 0)
    nb = sum(1 for v in regs.values() if v in POISON)
    nz = sum(1 for v in regs.values() if v == 0)
    json.dump(dict(base=FUSE, poison=list(POISON), span=span,
                   pmc_boot_0=f"0x{boot0:08x}", pages=pages,
                   regs=regs,
                   stats=dict(words=len(regs), with_data=nd, poison=nb, zero=nz)),
              open(out, "w"))
    print(f"\n  tong {len(regs)} word: {nd} co du lieu, {nb} poison, {nz} zero")
    print(f"  -> {out}")


if __name__ == "__main__":
    main()