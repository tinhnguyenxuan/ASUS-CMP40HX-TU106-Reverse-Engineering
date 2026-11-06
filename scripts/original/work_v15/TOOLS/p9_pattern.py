#!/usr/bin/env python3
"""P9b: phan tich pattern cua vung BAR0 0x010000..0x01FFFF.

Biet: entropy 2.0000, 3072 nonzero/trang, word dau 0xbad00100.
Can biet: chu ky lap, cau truc 3/4 vs 1/4, y nghia 0xBAD00100.
"""
import mmap
import os
import struct
import sys
from collections import Counter

DEV = "/sys/bus/pci/devices/0000:03:00.0/resource0"
BASE = 0x010000
SIZE = 0x010000


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "p9_pattern.json"
    fd = os.open(DEV, os.O_RDONLY | os.O_SYNC)
    mm = mmap.mmap(fd, 16 << 20, mmap.MAP_SHARED, mmap.PROT_READ)
    buf = bytes(mm[BASE:BASE + SIZE])
    mm.close()
    os.close(fd)

    print("=== P9b: pattern 0x010000..0x01FFFF ===")

    # 1. byte distribution
    ctr = Counter(buf)
    print("\n--- phan bo byte (4 gia tri) ---")
    for b, n in ctr.most_common():
        print(f"  0x{b:02x} ({b:3d})  {n:6d}  ({n/SIZE*100:5.1f}%)")

    # 2. tim chu ky lap: thu period 1..4096
    print("\n--- tim chu ky lap ---")
    best = None
    for p in range(1, 4097):
        if SIZE % p:
            continue
        if buf == buf[:p] * (SIZE // p):
            best = p
            break
    if best:
        print(f"  TOAN BO vung lap voi chu ky {best} B")
        print(f"  pattern: {buf[:best].hex()}")
    else:
        print("  khong lap toan bo -> tim chu ky theo trang")
        pg = buf[:0x1000]
        for p in range(1, 4097):
            if 0x1000 % p == 0 and pg == pg[:p] * (0x1000 // p):
                print(f"  trang 0 lap voi chu ky {p} B")
                print(f"  pattern: {pg[:p].hex()}")
                break

    # 3. kiem tra tung trang co giong nhau khong
    print("\n--- 16 trang co giong nhau? ---")
    pgs = [buf[i:i + 0x1000] for i in range(0, SIZE, 0x1000)]
    same = [i for i in range(1, 16) if pgs[i] == pgs[0]]
    print(f"  trang 0 giong trang: {same if same else '(khong trang nao)'}")

    # 4. vi tri zero trong trang 0
    print("\n--- vi tri zero trong trang 0 (4096 B) ---")
    z = [i for i, b in enumerate(pgs[0]) if b == 0]
    if z:
        print(f"  {len(z)} byte zero, tu {z[0]:04x} den {z[-1]:04x}")
        # lien tuc?
        runs = []
        s = z[0]
        prev = z[0]
        for x in z[1:]:
            if x != prev + 1:
                runs.append((s, prev))
                s = x
            prev = x
        runs.append((s, prev))
        print(f"  {len(runs)} doan lien tuc:")
        for a, b in runs[:12]:
            print(f"    0x{a:04x}..0x{b:04x}  ({b-a+1} B)")

    # 5. u32 doc 1 trang, xem cac gia tri khac nhau
    print("\n--- gia tri u32 khac nhau trong trang 0 ---")
    vs = [struct.unpack_from("<I", pgs[0], i)[0] for i in range(0, 0x1000, 4)]
    vc = Counter(vs)
    for v, n in vc.most_common():
        print(f"  0x{v:08x}  {n:5d} lan  ({(v>>16)&0xffff:04x}:{v&0xffff:04x})")

    # 6. so sanh voi vbios shadow o cung offset
    sh = "RAW_DATA/vbios_shadow.bin"
    if os.path.exists(sh):
        sb = open(sh, "rb").read()
        off = BASE - 0x300000
        if 0 <= off < len(sb):
            seg = sb[off:off + 0x100]
            print(f"\n--- shadow[0x{BASE:06x}] 256 B dau ---")
            print("  " + seg[:64].hex())
            print(f"  giong BAR0 0x010000? {seg[:0x100] == pgs[0][:0x100]}")

    import json
    json.dump(dict(
        byte_dist={f"0x{b:02x}": n for b, n in ctr.most_common()},
        period_whole=best,
        pages_identical_to_page0=same,
        zero_runs_in_page0=[list(r) for r in runs],
        distinct_u32={f"0x{v:08x}": n for v, n in vc.most_common()},
        pattern_hex=pgs[0][:best].hex() if best else None,
    ), open(out, "w"), indent=1)
    print(f"\n  -> {out}")


if __name__ == "__main__":
    main()
