#!/usr/bin/env python3
"""TU-06b: kiem tra vung 0x300000 co phai aperture THAT hay bus tha noi.

Cach kiem: doc cung dia chi 3 lan, cach nhau thoi gian. Neu on dinh -> register.
Neu doi -> bus floating / garbage, KHONG phai aperture.

Cung kiem tra: doc 2 word lien tiep co quan he gi khong; va doc lai 0x300000
sau khi doc vung khac (xem co bi anh huong).

Dung: sudo python3 tu06b_stable.py out.json
"""
import json
import mmap
import os
import struct
import sys
import time

DEV = "/sys/bus/pci/devices/0000:03:00.0/resource0"


def rd(mm, a):
    return struct.unpack_from("<I", mm, a)[0]


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "tu06b.json"
    fd = os.open(DEV, os.O_RDONLY | os.O_SYNC)
    mm = mmap.mmap(fd, 16 << 20, mmap.MAP_SHARED, mmap.PROT_READ)

    # dia chi thu: (ten, addr)
    TESTS = [
        ("0x300000", 0x300000),   # vung "DATA" nghi van
        ("0x300010", 0x300010),
        ("0x310000", 0x310000),
        ("0x3F0000", 0x3F0000),
        ("0x000000", 0x000000),   # doi chung: PMC_BOOT_0 PHAI on dinh
        ("0x021000", 0x021000),   # doi chung: FUSE PHAI on dinh
        ("0x1FA824", 0x1FA824),   # doi chung: WPR2 PHAI on dinh
        ("0x400000", 0x400000),   # doi chung: poison
    ]

    res = []
    print("=== doc 3 lan cach nhau 100 ms ===")
    print(f"  {'addr':<12s} {'lan1':<12s} {'lan2':<12s} {'lan3':<12s} on dinh?")
    for nm, a in TESTS:
        vs = []
        for _ in range(3):
            vs.append(rd(mm, a))
            time.sleep(0.1)
        stable = len(set(vs)) == 1
        res.append(dict(name=nm, addr=f"0x{a:06x}", vals=[f"0x{v:08x}" for v in vs],
                        stable=stable))
        print(f"  {nm:<12s} 0x{vs[0]:08x}   0x{vs[1]:08x}   0x{vs[2]:08x}   "
              f"{'ON DINH' if stable else '*** DOI ***'}")

    # --- doc lai sau khi doc vung khac (kiem nhieu) ---
    print(f"\n=== kiem nhieu: doc 0x300000, chen doc 0x0, roi doc lai ===")
    a = rd(mm, 0x300000)
    _ = rd(mm, 0x000000)
    b = rd(mm, 0x300000)
    _ = rd(mm, 0x021000)
    c = rd(mm, 0x300000)
    print(f"  0x300000 = 0x{a:08x} / sau PMC = 0x{b:08x} / sau FUSE = 0x{c:08x}")
    print(f"  -> {'ON DINH' if len({a,b,c})==1 else 'BI ANH HUONG BOI vung khac'}")

    # --- quet 32 word lien tiep o 0x300000: co pattern khong ---
    print(f"\n=== 32 word lien tiep @0x300000 ===")
    words = []
    for k in range(32):
        v = rd(mm, 0x300000 + k * 4)
        words.append(f"0x{v:08x}")
        if k % 8 == 0:
            print(f"  0x{0x300000+k*4:06x}: ", end="")
        print(f"{v:08x} ", end="")
        if k % 8 == 7:
            print()
    uniq = len(set(words))
    print(f"\n  {uniq}/32 word khac nhau")

    # --- doc lai 32 word do lan 2, so sanh ---
    words2 = [f"0x{rd(mm, 0x300000 + k * 4):08x}" for k in range(32)]
    same = sum(1 for i in range(32) if words[i] == words2[i])
    print(f"  doc lai: {same}/32 word giong -> "
          f"{'ON DINH' if same == 32 else 'KHONG ON DINH'}")

    mm.close()
    os.close(fd)

    # ket luan
    stable_300 = next(r for r in res if r["name"] == "0x300000")["stable"]
    ctrl_stable = all(r["stable"] for r in res
                      if r["name"] in ("0x000000", "0x021000", "0x1FA824"))
    print(f"\n=== KET LUAN ===")
    print(f"  doi chung (PMC/FUSE/WPR2) on dinh: {ctrl_stable}")
    print(f"  0x300000 on dinh qua 3 lan doc:     {stable_300}")
    print(f"  0x300000 doc lai 32 word giong:     {same}/32")
    if stable_300 and same == 32 and ctrl_stable:
        verdict = "APERTURE THAT — vung 0x300000 la register on dinh"
    elif ctrl_stable and not stable_300:
        verdict = "BUS FLOATING — gia tri doi moi lan doc, KHONG phai aperture"
    else:
        verdict = "KHONG KET LUAN DUOC"
    print(f"  -> {verdict}")

    json.dump(dict(tests=res, words_1=words, words_2=words2,
                   same_count=same, control_stable=ctrl_stable,
                   stable_0x300000=stable_300, verdict=verdict),
              open(out, "w"), indent=1)
    print(f"  -> {out}")


if __name__ == "__main__":
    main()