#!/usr/bin/env python3
"""P1: dung MMIO map TU106 tu register database + doc co muc tieu qua BAR0.

Dung: sudo python3 mmio_scan.py registers_turing.json out.json
Chi doc cac offset cua register DA TAI LIEU HOA, khong quet dai, khong ghi.
"""
import json
import mmap
import os
import struct
import sys

BDF = "0000:03:00.0"
RES = f"/sys/bus/pci/devices/{BDF}/resource0"
POISON = (0xBADF5040, 0xBADF1300, 0xBADF1100, 0xBADF1301, 0xBADF510C, 0xBADF0000)


def main():
    rdb = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    regs = rdb["registers"]
    items = sorted(((n, r["addr"], r) for n, r in regs.items()),
                   key=lambda x: x[1])
    print(f"=== {len(items)} register turing, "
          f"0x{items[0][1]:x}..0x{items[-1][1]:x} ===")

    fd = os.open(RES, os.O_RDONLY | os.O_SYNC)
    mm = mmap.mmap(fd, 16 << 20, mmap.MAP_SHARED, mmap.PROT_READ)
    boot0 = struct.unpack_from("<I", mm, 0)[0]
    print(f"  NV_PMC_BOOT_0 = 0x{boot0:08x}")

    res = {}
    seen_pages = set()
    for n, a, r in items:
        try:
            v = struct.unpack_from("<I", mm, a)[0]
        except Exception:
            v = None
        seen_pages.add(a >> 16)
        bfs = []
        for b in r.get("bitfields", []):
            bfs.append(dict(name=b["name"], hi=b["hi"], lo=b["lo"],
                            value=((v >> b["lo"]) &
                                   ((1 << (b["hi"] - b["lo"] + 1)) - 1))
                            if isinstance(v, int) else None))
        st = ("read_err" if v is None else
              "poison" if v in POISON else
              "zero" if v == 0 else "data")
        res[n] = dict(addr=a, addr_hex=f"0x{a:08x}",
                      page=a >> 16, access=r.get("access"),
                      block=r.get("block") or "OTHER", value=v, state=st,
                      bitfields=bfs)
    mm.close()
    os.close(fd)

    from collections import Counter
    sc = Counter(x["state"] for x in res.values())
    bc = Counter(x["block"] for x in res.values())
    print(f"\n  trang da cham: {len(seen_pages)} (64 KB/page)")

    print(f"\n  {'state':<10s} {'n':>5s}")
    for s, n2 in sc.most_common():
        print(f"  {s:<10s} {n2:>5d}")

    print(f"\n  {'block':<10s} {'regs':>5s} {'co data':>8s} {'poison':>7s}")
    for b, n2 in bc.most_common():
        d = sum(1 for x in res.values() if x["block"] == b and x["state"] == "data")
        p = sum(1 for x in res.values() if x["block"] == b and x["state"] == "poison")
        print(f"  {b:<10s} {n2:>5d} {d:>8d} {p:>7d}")

    print(f"\n=== register CO DU LIEU (doc duoc) ===")
    for n, x in sorted(res.items(), key=lambda y: y[1]["addr"]):
        if x["state"] != "data":
            continue
        bfs = " ".join(f"{b['name'].split('_')[-1]}={b['value']}"
                       for b in x["bitfields"][:3])
        print(f"  0x{x['addr']:06x} 0x{x['value']:08x}  {n:<46s} {bfs}")

    json.dump(dict(bdf=BDF, boot0=f"0x{boot0:08x}",
                   poison=[f"0x{p:08x}" for p in POISON],
                   pages_touched=sorted(seen_pages),
                   stats=dict(states=dict(sc), blocks=dict(bc)),
                   registers=res),
              open(out, "w"), indent=1)
    print(f"\n  -> {out}")


if __name__ == "__main__":
    main()