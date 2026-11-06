#!/usr/bin/env python3
"""P0: doc 64 NV_FUSE register qua aperture 0x021000 (cua so THAT). Read-only.

Dung: sudo python3 fuse_read2.py registers_all.json out.json
"""
import json
import mmap
import struct
import sys

BDF = "0000:03:00.0"
RES = f"/sys/bus/pci/devices/{BDF}/resource0"
WIN = 0x00021000              # cua so fuse that (theo tu102/dev_fuse.h)
ALT = 0x00820000              # NV_FUSE0_PRI_BASE - KHONG addressable tu BAR0
BLOCK_SPAN = 0x20000          # du rong cho offset 0x4e10


def main():
    rdb = json.load(open(sys.argv[1]))
    out = sys.argv[2]
    regs = {n: r for n, r in rdb["registers"].items() if n.startswith("NV_FUSE")}
    items = []
    for n, r in regs.items():
        a = r["addr"]
        if a >= ALT:
            off = a - ALT                      # offset trong khoi fuse
        elif a >= WIN:
            off = a - WIN
        else:
            continue                            # ZB_* (khong thuoc TU106)
        items.append((n, a, off))
    items.sort(key=lambda x: x[2])
    print(f"=== {len(items)} NV_FUSE register qua cua so 0x{WIN:06x} ===")
    print(f"    offset {items[0][2]:#x}..{items[-1][2]:#x}")

    f = open(RES, "rb")
    need = (WIN + items[-1][2] + 0x1000 + 0xFFFF) & ~0xFFFF
    mm = mmap.mmap(f.fileno(), need, prot=mmap.PROT_READ)
    print(f"    mapped {need:,} B read-only (cua so {WIN:#x}..{WIN + need:#x})")

    vals = {}
    for n, a, off in items:
        try:
            v = struct.unpack("<I", mm[WIN + off:WIN + off + 4])[0]
        except Exception as e:
            v = f"ERR:{e}"
        vals[n] = dict(addr=f"0x{a:08x}", offset=f"0x{off:04x}", value=v,
                       bitfields=[dict(name=b["name"], hi=b["hi"], lo=b["lo"],
                                       value=((v >> b["lo"]) &
                                              ((1 << (b["hi"] - b["lo"] + 1)) - 1))
                                       if isinstance(v, int) else None)
                                  for b in regs[n].get("bitfields", [])])
    mm.close()
    f.close()

    print(f"\n  {'off':>7s} {'value':>12s}  register / bitfield")
    nz = 0
    for n, a, off in items:
        d = vals[n]
        v = d["value"]
        vs = f"0x{v:08x}" if isinstance(v, int) else str(v)
        if isinstance(v, int) and v not in (0, 0xBADF5040, 0xBADF1300):
            nz += 1
        bfs = " ".join(f"{b['name'].split('_')[-1]}={b['value']}"
                       for b in d["bitfields"])
        print(f"  0x{off:05x} {vs:>12s}  {n:<46s} {bfs}")

    badf = sum(1 for d in vals.values()
               if d["value"] in (0xBADF5040, 0xBADF1300, 0xBADF1100))
    zero = sum(1 for d in vals.values() if d["value"] == 0)
    print(f"\n  co du lieu {nz}  zero {zero}  BADF {badf}  tong {len(vals)}")
    json.dump(dict(bdf=BDF, window=f"0x{WIN:06x}", mapped=need,
                   registers=vals,
                   stats=dict(with_data=nz, zero=zero, badf=badf,
                              total=len(vals))),
              open(out, "w"), indent=1)
    print(f"  -> {out}")


if __name__ == "__main__":
    main()