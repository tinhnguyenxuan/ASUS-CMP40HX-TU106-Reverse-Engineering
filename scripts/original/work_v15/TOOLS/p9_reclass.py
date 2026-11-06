#!/usr/bin/env python3
"""P9c: phan loai LAI cac vung 'DATA' trong aperture map.

TU-06 phan loai 287 trang DATA bang mask poison 0xBADF0000.
Da phat hien 0x010000..0x01FFFF = u32 0xBAD00100 lap vo han -> POISON ma moi.

Can: doc lai TUNG vung DATA, xem co phai 'single u32 lap' khong.
  - neu ca vung chi la 1 gia tri u32 lap -> POISON (ma moi)
  - neu co nhieu gia tri / co cau truc -> DATA that

Doc theo cua so 64 KB.
"""
import mmap
import os
import struct
import sys
from collections import Counter

DEV = "/sys/bus/pci/devices/0000:03:00.0/resource0"
MAP = "TOPOLOGY/aperture_map.json"

# mask poison da biet
KNOWN = {
    0xBADF5040: "0xBADF5040", 0xBADF1300: "0xBADF1300", 0xBADF1100: "0xBADF1100",
    0xBADF1301: "0xBADF1301", 0xBADF510C: "0xBADF510C", 0xBADF0000: "0xBADF0000",
    0xBAD00100: "0xBAD00100",
}


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "p9_reclass.json"
    zones = [z for z in json_zones() if z["state"] == "DATA"]
    print(f"=== P9c: phan loai lai {len(zones)} vung 'DATA' ===")

    fd = os.open(DEV, os.O_RDONLY | os.O_SYNC)
    mm = mmap.mmap(fd, 16 << 20, mmap.MAP_SHARED, mmap.PROT_READ)

    res = []
    for z in zones:
        s = int(z["start"], 16)
        e = int(z["end"], 16) + 1
        buf = b""
        # doc theo cua so 64 KB
        i = s
        while i < e:
            n = min(0x10000, e - i)
            buf += bytes(mm[i:i + n])
            i += n
        if not buf:
            continue
        ctr = Counter(struct.unpack_from("<I", buf, k)[0]
                      for k in range(0, len(buf) - 3, 4))
        nz = sum(1 for b in buf if b)
        top = ctr.most_common(3)
        single = len(ctr) == 1
        v = top[0][0]
        tag = KNOWN.get(v)
        cls = "POISON_MOI" if single and (v & 0xFFFF0000) == 0xBAD00000 else (
              "SINGLE_U32" if single else "DATA_THAT")
        if single and not ((v & 0xFFFF0000) == 0xBAD00000):
            cls = "SINGLE_U32_KHAC"
        print(f"  {z['start']}..{z['end']} ({z['pages']:3d} trang) "
              f"nonzero {nz*100//len(buf):3d}%  distinct_u32 {len(ctr):6d}  "
              f"top 0x{v:08x} x{top[0][1]}  {tag or ''}  -> {cls}")
        for v2, n2 in top:
            print(f"        0x{v2:08x} x{n2}")
        res.append(dict(zone=z, nonzero_pct=round(nz * 100 / len(buf), 2),
                        distinct_u32=len(ctr),
                        top=[{"v": f"0x{v2:08x}", "n": n2} for v2, n2 in top],
                        classification=cls))

    mm.close()
    os.close(fd)

    tot_poison = sum(z["pages"] for z, r in zip(zones, res)
                     if r["classification"] == "POISON_MOI")
    print(f"\n  -> vung DATA that la POISON ma 0xBAD0xxxx: {tot_poison} trang")

    import json
    json.dump(dict(zones=res, poison_pages_found=tot_poison,
                   note="neu POISON_MOI, TU-06 phai sua: DATA 287 -> "
                        f"{287 - tot_poison}"),
              open(out, "w"), indent=1)
    print(f"  -> {out}")


def json_zones():
    import json
    return json.load(open(MAP))["zones"]


if __name__ == "__main__":
    main()
