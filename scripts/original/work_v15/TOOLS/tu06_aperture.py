#!/usr/bin/env python3
"""TU-06: lap BAN DO APERTURE duoc decode trong BAR0 16 MB. CHI DOC.

Quet tung trang 4 KB, doc 1 word dau + 1 word giua. Phan loai:
  DATA   = co gia tri khac poison va khac 0
  ZERO   = toan 0
  POISON = 0xBADFxxxx
  MIXED  = khac nhau

Doc theo trang 4 KB, khong doc lien tuc (tranh sap may).

Dung: sudo python3 tu06_aperture.py out.json
"""
import json
import mmap
import os
import struct
import sys


def is_poison(v):
    return (v & 0xFFFF0000) == 0xBADF0000


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "tu06.json"
    dev = "/sys/bus/pci/devices/0000:03:00.0/resource0"
    size = 16 << 20
    fd = os.open(dev, os.O_RDONLY | os.O_SYNC)
    mm = mmap.mmap(fd, size, mmap.MAP_SHARED, mmap.PROT_READ)

    pages = []
    for pg in range(size >> 12):
        base = pg << 12
        # doc 4 word rai deu trong trang
        vals = []
        for k in (0, 0x400, 0x800, 0xC00):
            vals.append(struct.unpack_from("<I", mm, base + k)[0])
        np_ = sum(1 for v in vals if is_poison(v))
        nz = sum(1 for v in vals if v == 0)
        if np_ == len(vals):
            st = "POISON"
            rate = 1.0
        elif nz == len(vals):
            st = "ZERO"
            rate = 0.0
        elif np_ == 0 and nz == 0:
            st = "DATA"
            rate = 1.0
        else:
            st = "MIXED"
            rate = (len(vals) - np_ - nz) / len(vals)
        pages.append(dict(page=pg, base=f"0x{base:06x}", state=st,
                          data_rate=round(rate, 2), vals=[f"0x{v:08x}" for v in vals]))

    # gom thanh vung lien tuc
    zones = []
    cur = pages[0]
    start = cur["page"]
    prev_state = cur["state"]
    for p in pages[1:]:
        if p["state"] != prev_state or p["page"] != cur["page"] + 1:
            zones.append(dict(start_page=start, end_page=cur["page"],
                              start=f"0x{start << 12:06x}",
                              end=f"0x{((cur['page'] + 1) << 12) - 1:06x}",
                              pages=cur["page"] - start + 1, state=prev_state))
            start = p["page"]
            prev_state = p["state"]
        cur = p
    zones.append(dict(start_page=start, end_page=cur["page"],
                      start=f"0x{start << 12:06x}",
                      end=f"0x{((cur['page'] + 1) << 12) - 1:06x}",
                      pages=cur["page"] - start + 1, state=prev_state))

    from collections import Counter
    st = Counter(p["state"] for p in pages)
    print(f"=== BAN DO APERTURE BAR0 16 MB ({len(pages)} trang 4 KB) ===")
    for k, v in st.most_common():
        print(f"  {k:<8s} {v:>5d} trang  ({100 * v / len(pages):5.1f}%)")

    print(f"\n=== {len(zones)} vung lien tuc ===")
    for z in zones:
        print(f"  {z['start']}..{z['end']}  {z['pages']:>5d} trang  {z['state']}")

    # vung DATA > 1 trang la aperture that
    real = [z for z in zones if z["state"] in ("DATA", "MIXED")
            and z["pages"] >= 1]
    print(f"\n=== {len(real)} vung co du lieu that (ung vien aperture) ===")
    for z in real:
        print(f"  {z['start']}..{z['end']}  {z['pages']} trang")

    mm.close()
    os.close(fd)
    json.dump(dict(bdf=dev, page_size=4096, total_pages=len(pages),
                   stats=dict(st), zones=zones, pages=pages,
                   note="POISON = ngoai cua so BAR0 duoc decode, KHONG phai "
                        "block khong ton tai"),
              open(out, "w"), indent=1)
    print(f"\n  -> {out}")


if __name__ == "__main__":
    main()