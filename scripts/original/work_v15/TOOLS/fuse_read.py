#!/usr/bin/env python3
"""P0: doc READ-ONLY dung 64 register NV_FUSE da tai lieu hoa. KHONG ghi.

Dung (tren target): python3 fuse_read.py registers_all.json out.json
Doc tung offset 4 byte qua /sys/bus/pci/devices/<bdf>/resource0 (mmap read-only).
Khong quet dai, khong ghi, khong thu register la.
"""
import json
import mmap
import os
import struct
import sys

BDF = "0000:03:00.0"
RES = f"/sys/bus/pci/devices/{BDF}/resource0"
# hai aperture nghi van de
APERTURES = (0x00021000, 0x00820000)


def read_at(mm, off):
    try:
        return struct.unpack("<I", mm[off:off + 4])[0]
    except Exception as e:
        return f"ERR:{e}"


def main():
    rdb = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    regs = {n: r for n, r in rdb["registers"].items() if n.startswith("NV_FUSE")}
    # offset = addr - 0x820000 (block base theo NV_FUSE0_PRI_BASE)
    base = 0x00820000
    items = []
    for n, r in regs.items():
        a = r["addr"]
        off = a - base if a >= base else (a - 0x00021000)
        items.append((n, a, off))
    items.sort(key=lambda x: x[2])
    print(f"=== {len(items)} NV_FUSE register, offset {items[0][2]:#x}..{items[-1][2]:#x} ===")

    if not os.path.exists(RES):
        raise SystemExit(f"khong thay {RES}")

    f = open(RES, "rb")
    # map du 64 KB chunk chua offset lon nhat
    need = max(0x10000, items[-1][2] + 0x1000)
    need = (need + 0xFFFF) & ~0xFFFF
    mm = mmap.mmap(f.fileno(), need, prot=mmap.PROT_READ)
    print(f"  mapped {need:,} B read-only")

    vals = {}
    for n, a, off in items:
        v = read_at(mm, off)
        vals[n] = dict(addr=f"0x{a:08x}", offset=f"0x{off:04x}", value=v,
                       access=None,
                       bitfields=[dict(name=b["name"], hi=b["hi"], lo=b["lo"],
                                       value=((v >> b["lo"]) &
                                              ((1 << (b["hi"] - b["lo"] + 1)) - 1))
                                       if isinstance(v, int) else None)
                                  for b in regs[n].get("bitfields", [])])
    mm.close()
    f.close()

    print(f"\n  {'offset':>8s} {'addr':>12s} {'value':>12s}  register / bitfield")
    nz = 0
    for n, a, off in items:
        d = vals[n]
        v = d["value"]
        vs = f"0x{v:08x}" if isinstance(v, int) else str(v)
        if isinstance(v, int) and v not in (0, 0xBADF5040, 0xBADF1300):
            nz += 1
        bfs = " ".join(f"{b['name'].split('_')[-1]}={b['value']}"
                       for b in d["bitfields"])
        print(f"  0x{off:06x} 0x{a:08x} {vs:>12s}  {n:<48s} {bfs}")

    badf = sum(1 for d in vals.values() if d["value"] in (0xBADF5040, 0xBADF1300))
    zero = sum(1 for d in vals.values() if d["value"] == 0)
    print(f"\n  co du lieu: {nz}   zero: {zero}   BADF: {badf}   "
          f"tong: {len(vals)}")
    json.dump(dict(bdf=BDF, aperture_base=f"0x{base:08x}",
                   mapped=need, registers=vals,
                   stats=dict(with_data=nz, zero=zero, badf=badf, total=len(vals))),
              open(out, "w"), indent=1)
    print(f"  -> {out}")


if __name__ == "__main__":
    main()