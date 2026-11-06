#!/usr/bin/env python3
"""P9: xac dinh vung BAR0 0x010000..0x01FFFF (64 KB) chua biet la gi.

TU-06 aperture map cho thay 2 vung DATA lon:
  0x300000..0x3FFFFF  -> da giai = VBIOS shadow
  0x010000..0x01FFFF  -> CHUA BIET  <-- file nay

Doc theo cua so 64 KB, PROT_READ. Sau do:
  - entropy / nonzero / ASCII
  - tim magic nvidia (NVGI, PCIR, BIT, FLCN, NVUC, PRGN, RSD2, "$VGA")
  - tim chuoi ASCII in duoc >= 6 ky tu
  - so sanh voi vbios_shadow.bin va rom_file
"""
import math
import mmap
import os
import re
import struct
import sys
from collections import Counter

DEV = "/sys/bus/pci/devices/0000:03:00.0/resource0"
BASE = 0x010000
SIZE = 0x010000          # 64 KB, 1 cua so
MAGICS = [
    b"NVGI", b"PCIR", b"BIT\x00", b"FLCN", b"NVUC", b"PRGN", b"RSD2",
    b"$VGA", b"\x55\xaa", b"ACPI", b"SMBI", b"COMPAT", b"VBE",
]


def is_poison(v):
    return (v & 0xFFFF0000) == 0xBADF0000


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "p9_zone010000.json"
    fd = os.open(DEV, os.O_RDONLY | os.O_SYNC)
    mm = mmap.mmap(fd, 16 << 20, mmap.MAP_SHARED, mmap.PROT_READ)

    buf = bytearray(SIZE)
    nz = 0
    poison = 0
    ctr = Counter()
    for i in range(SIZE):
        buf[i] = mm[BASE + i]
    for b in buf:
        ctr[b] += 1
        if b:
            nz += 1
    # poison count (u32)
    for i in range(0, SIZE - 3, 4):
        v = struct.unpack_from("<I", buf, i)[0]
        if is_poison(v):
            poison += 1

    ent = -sum((c / SIZE) * math.log2(c / SIZE) for c in ctr.values() if c)
    print("=== P9: BAR0 0x010000..0x01FFFF ===")
    print(f"  size       : {SIZE} B")
    print(f"  nonzero    : {nz} ({nz/SIZE*100:.1f}%)")
    print(f"  entropy    : {ent:.4f} / 8.0")
    print(f"  u32 poison : {poison} / {SIZE//4}")

    # magic
    print("\n--- magic ---")
    hits = []
    for m in MAGICS:
        for mm_ in re.finditer(re.escape(m), bytes(buf)):
            hits.append((mm_.start(), m))
            print(f"  0x{BASE+mm_.start():06x}: {m}")
    if not hits:
        print("  (khong co magic nvidia/pc firmware nao)")

    # ascii
    print("\n--- chuoi ASCII >= 6 ky tu ---")
    strs = re.findall(rb"[\x20-\x7e]{6,}", bytes(buf))
    strs = [s for s in strs if not s.isspace()]
    print(f"  {len(strs)} chuoi")
    for s in strs[:60]:
        print(f"    {s.decode('ascii', 'replace')}")

    # u32 doc thu tu 32 word dau
    print("\n--- 32 word dau (LE) ---")
    row = []
    for i in range(0, 128, 4):
        v = struct.unpack_from("<I", buf, i)[0]
        row.append(f"{i:04x}:{v:08x}")
    print("  " + "  ".join(row))

    # vung zero lon
    print("\n--- cau truc theo trang 4 KB ---")
    for pg in range(0, SIZE, 0x1000):
        w = buf[pg:pg + 0x1000]
        n = sum(1 for b in w if b)
        pz = sum(1 for i in range(0, 0x1000 - 3, 4)
                 if is_poison(struct.unpack_from("<I", w, i)[0]))
        if n or pz:
            print(f"  +0x{pg:04x}: nonzero {n:5d}/4096  poison {pz:5d}/1024")

    mm.close()
    os.close(fd)

    import json
    json.dump(dict(
        base=f"0x{BASE:06x}", size=SIZE, nonzero=nz,
        nonzero_pct=round(nz / SIZE * 100, 2), entropy=round(ent, 4),
        poison_u32=poison, magic_hits=[{"off": f"0x{BASE+o:06x}", "tag": t.decode('latin1')} for o, t in hits],
        strings=[s.decode('ascii', 'replace') for s in strs[:200]],
        first_words=[f"{struct.unpack_from('<I', buf, i)[0]:08x}" for i in range(0, 128, 4)],
    ), open(out, "w"), indent=1)
    print(f"\n  -> {out}")


if __name__ == "__main__":
    main()
