#!/usr/bin/env python3
"""P9e: xac nhan BAR1/BAR3 co decode khong, truoc khi ket luan WPR.

P9d cho TAT CA vung (ke ca doi chung) deu 0 -> co the la:
  (a) BAR1 raw khong decode, can driver lap trinh aperture
  (b) chon offset sai
  (c) resource khong duoc enable

Thu: quet 24 offset rai rac trong BAR1 (8 GB) + BAR3 (32 MB).
Neu TAT CA deu 0 -> ket luan BAR raw khong doc duoc -> BLOCKED.
"""
import mmap
import os
import struct
import sys
from collections import Counter

RES = {
    "BAR1": "/sys/bus/pci/devices/0000:03:00.0/resource1",
    "BAR3": "/sys/bus/pci/devices/0000:03:00.0/resource3",
}
OFFS = [0, 0x1000, 0x10000, 0x100000, 0x1000000, 0x10000000,
        0x20000000, 0x40000000, 0x60000000, 0x7F000000,
        0x80000000, 0xA0000000, 0xC0000000, 0xE0000000,
        0xFF000000, 0x1F0000000, 0x1F7000000, 0x1F7E00000,
        0x3F0000000, 0x7F0000000, 0x7FFFF0000, 0x400000000,
        0x800000000, 0x1000000000]


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "p9_barscan.json"
    res = {}
    for nm, path in RES.items():
        if not os.path.exists(path):
            print(f"{nm}: khong co {path}")
            continue
        sz = os.path.getsize(path)
        fd = os.open(path, os.O_RDONLY | os.O_SYNC)
        m = mmap.mmap(fd, sz, mmap.MAP_SHARED, mmap.PROT_READ)
        print(f"\n=== {nm} ({sz/2**20:.1f} MiB) ===")
        rows = []
        nz_total = 0
        for off in OFFS:
            if off + 4096 > sz:
                continue
            try:
                b = bytes(m[off:off + 4096])
            except Exception as e:
                print(f"  0x{off:09x}  LOI {e}")
                continue
            nz = sum(1 for x in b if x)
            nz_total += nz
            v = struct.unpack_from("<I", b, 0)[0]
            flag = "  <-- CO DATA" if nz else ""
            print(f"  0x{off:09x}  nonzero {nz:5d}/4096  first=0x{v:08x}{flag}")
            rows.append(dict(off=f"0x{off:09x}", nonzero=nz, first=f"0x{v:08x}"))
        m.close()
        os.close(fd)
        res[nm] = dict(size=sz, rows=rows, nonzero_total=nz_total,
                       any_data=nz_total > 0)
        print(f"  -> tong nonzero: {nz_total} / {len(rows)*4096}")
        if nz_total == 0:
            print(f"  => {nm} KHONG decode duoc qua PCI resource raw")

    import json
    json.dump(res, open(out, "w"), indent=1)
    print(f"\n  -> {out}")
    if not any(v.get("any_data") for v in res.values()):
        print("\nKET LUAN: BAR1 va BAR3 khong doc duoc qua PCI resource raw.")
        print("  BAR1 = aperture can driver lap tring (NV_PBUS_BAR1_BLOCK=0x801F7CC0).")
        print("  Doc VRAM/WPR2 can GHI register aperture -> nam ngoai read-only.")
        print("  -> WPR2 read test: BLOCKED (khong phai 'WPR chan doc')")
    return 0


if __name__ == "__main__":
    sys.exit(main())
