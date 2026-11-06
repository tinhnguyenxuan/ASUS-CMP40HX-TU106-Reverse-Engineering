#!/usr/bin/env python3
"""P9g: dump vung nong cua BAR3 (0x00000000..0x00040000) va phan tich.

BAR3 = 32 MB @ 0x380800000000. 130/8192 trang co du lieu, tap trung < 0x40000.

Noi dung phat hien:
  0x00010000: u32 0x1F4F4D02, 0x00011000: 0x1F4F4C02 ... (device ID)
  0x00017000: entry 16 B {u32 flags, u32 0x00060000, 8 B zero}, flags +0x20000
  0x00014000: u32 0x00000008 lap
  0x00000000: u32 0x00007FF0

Can: dump day du, liet ke tat ca entry, thu parse thanh bang.
"""
import mmap
import os
import struct
import sys
from collections import Counter

BAR3 = "/sys/bus/pci/devices/0000:03:00.0/resource3"
LO, HI = 0x00000000, 0x00040000


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "bar3_hot.bin"
    fd = os.open(BAR3, os.O_RDONLY | os.O_SYNC)
    mm = mmap.mmap(fd, os.path.getsize(BAR3), mmap.MAP_SHARED, mmap.PROT_READ)
    buf = bytes(mm[LO:HI])
    mm.close()
    os.close(fd)

    with open(out, "wb") as f:
        f.write(buf)
    print(f"=== P9g: BAR3 0x{LO:08x}..0x{HI:08x} = {len(buf)} B -> {out} ===")

    nz = sum(1 for b in buf if b)
    ctr = Counter(buf)
    import math
    ent = -sum((c / len(buf)) * math.log2(c / len(buf)) for c in ctr.values() if c)
    print(f"  nonzero {nz}/{len(buf)} ({nz/len(buf)*100:.1f}%)  entropy {ent:.3f}")

    # 1. liet ke moi vi tri nonzero theo trang
    print("\n--- trang co du lieu ---")
    hot = []
    for p in range(0, len(buf), 0x1000):
        w = buf[p:p + 0x1000]
        n = sum(1 for b in w if b)
        if n:
            hot.append((p, n))
    print(f"  {len(hot)} trang / {len(buf)//0x1000}")
    print("  " + " ".join(f"0x{p:05x}({n})" for p, n in hot))

    # 2. cac u32 doc duoc (bo qua 0)
    print("\n--- u32 khac 0, gom theo vi tri ---")
    vals = []
    for i in range(0, len(buf) - 3, 4):
        v = struct.unpack_from("<I", buf, i)[0]
        if v:
            vals.append((i, v))
    print(f"  {len(vals)} u32 khac 0")
    # nhom theo khoang cach
    print("\n--- 80 u32 dau ---")
    for i, v in vals[:80]:
        print(f"  0x{i:05x}: 0x{v:08x}")

    # 3. thu parse entry 16 B {u32 flags, u32 0x60000, 8B zero}
    print("\n--- thu entry 16 B tai 0x00017000 ---")
    o = 0x17000
    for k in range(12):
        e = buf[o + k * 16:o + k * 16 + 16]
        a, b = struct.unpack_from("<II", e, 0)
        print(f"  +0x{k*16:03x}: flags=0x{a:08x}  f1=0x{b:08x}  "
              f"rest={e[8:].hex()}")

    # 4. liet ke device-id-like u32 (0x1f....)
    print("\n--- u32 co dang 0x1fxxxx (device ID?) ---")
    dev = [(i, v) for i, v in vals if (v >> 16) == 0x1F or (v & 0xFFFF0000) == 0x1F000000]
    for i, v in dev[:60]:
        print(f"  0x{i:05x}: 0x{v:08x}   (hi=0x{v>>16:04x} lo=0x{v&0xffff:04x})")
    print(f"  tong {len(dev)}")

    # 5. ASCII
    print("\n--- ASCII >= 4 ---")
    import re
    for s in re.findall(rb"[\x20-\x7e]{4,}", buf):
        print("   ", s.decode())

    import json
    json.dump(dict(range=[f"0x{LO:08x}", f"0x{HI:08x}"], size=len(buf),
                   nonzero=nz, entropy=round(ent, 3),
                   hot_pages=[f"0x{p:05x}" for p, _ in hot],
                   nonzero_u32=[{"off": f"0x{i:05x}", "v": f"0x{v:08x}"}
                                for i, v in vals],
                   devlike=[{"off": f"0x{i:05x}", "v": f"0x{v:08x}"}
                            for i, v in dev]),
              open("p9_bar3_parsed.json", "w"), indent=1)
    print("\n  -> p9_bar3_parsed.json")


if __name__ == "__main__":
    sys.exit(main())
