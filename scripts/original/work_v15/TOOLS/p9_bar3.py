#!/usr/bin/env python3
"""P9f: khap sat BAR3 (32 MB) -- cua so chua biet.

Phat hien: 0x00000000 -> 0x00007ff0 ; 0x00010000 -> 0x1f4f4d02
BAR3 = 32 MB @ 0x380800000000, khong phai VRAM.

Quet 32 MB theo trang 4 KB, ghi lai trang nao co du lieu,
roi trich noi dung cac vung do.
"""
import mmap
import os
import struct
import sys
from collections import Counter

BAR3 = "/sys/bus/pci/devices/0000:03:00.0/resource3"
PAGE = 4096


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "p9_bar3.json"
    sz = os.path.getsize(BAR3)
    npages = sz // PAGE
    print(f"=== P9f: BAR3 {sz/2**20:.1f} MiB = {npages} trang ===")

    fd = os.open(BAR3, os.O_RDONLY | os.O_SYNC)
    mm = mmap.mmap(fd, sz, mmap.MAP_SHARED, mmap.PROT_READ)

    hot = []
    for p in range(npages):
        off = p * PAGE
        b = bytes(mm[off:off + 256])          # doc 256 B/trang du de nhan dien
        nz = sum(1 for x in b if x)
        if nz:
            hot.append((off, nz))
    print(f"  trang co du lieu (256 B dau): {len(hot)}")
    for off, nz in hot[:40]:
        print(f"    0x{off:08x}  nonzero {nz}/256")

    # trich noi dung chi tiet cac trang nong
    detail = []
    for off, nz in hot[:20]:
        b = bytes(mm[off:off + PAGE])
        print(f"\n--- 0x{off:08x} ---")
        for i in range(0, 256, 32):
            row = b[i:i + 32]
            if any(row):
                asc = "".join(chr(c) if 32 <= c < 127 else "." for c in row)
                print(f"  +0x{i:03x}: {row.hex()}  {asc}")
        v = struct.unpack_from("<I", b, 0)[0]
        detail.append(dict(off=f"0x{off:08x}", first=f"0x{v:08x}",
                           hex=b[:256].hex()))

    mm.close()
    os.close(fd)
    import json
    json.dump(dict(size=sz, hot_pages=[f"0x{o:08x}" for o, _ in hot],
                   hot_count=len(hot), detail=detail), open(out, "w"), indent=1)
    print(f"\n  -> {out}")


if __name__ == "__main__":
    sys.exit(main())
