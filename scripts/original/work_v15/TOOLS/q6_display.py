#!/usr/bin/env python3
"""Q6: kiem tra display engine co addressable khong. CHI DOC.

Dung: sudo python3 q6_display.py out.json
Thu 3 vung theo dev_disp.h v05_02 + cac offset chuan:
  0x610000 (PDISP), 0x616000 (SOR), 0x61C000 (DAC), 0x612000 (HEAD)
Ghi tung word 4 byte, khong ghi MMIO.
"""
import json
import mmap
import os
import struct
import sys

DEV = "/sys/bus/pci/devices/0000:03:00.0/resource0"
POISON = (0xBADF5040, 0xBADF1300, 0xBADF1100, 0xBADF1301, 0xBADF510C,
          0xBADF0000, 0xBADFBADF)

# vung thu: (ten, base, so word)
ZONES = [
    ("PDISP_head0", 0x610000, 32),      # FE / head
    ("PDISP_611000", 0x611000, 32),     # core
    ("PDISP_FE_RM_INTR_EN1_HEAD_TIMING", 0x611EF0, 8),   # register duy nhat trong source
    ("PDISP_612000", 0x612000, 32),
    ("PDISP_616000_SOR", 0x616000, 32),
    ("PDISP_61C000_DAC", 0x61C000, 32),
    ("PDISP_620000", 0x620000, 16),
    ("PDISP_640000", 0x640000, 16),
    # doi chung: vung PGRAPH (0x400000) va PFB (0x100000) da biet song
    ("CTRL_PGRAPH_400000", 0x400000, 16),
    ("CTRL_PBUS_000000", 0x000000, 8),
    ("CTRL_FUSE_021000", 0x021000, 8),
]


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "q6.json"
    fd = os.open(DEV, os.O_RDONLY | os.O_SYNC)
    mm = mmap.mmap(fd, 16 << 20, mmap.MAP_SHARED, mmap.PROT_READ)

    res = []
    print(f"=== Q6 kiem tra display engine (BAR0 16 MB, read-only) ===")
    for name, base, n in ZONES:
        words = []
        for i in range(n):
            a = base + i * 4
            try:
                v = struct.unpack_from("<I", mm, a)[0]
            except Exception as e:
                v = None
            words.append(dict(addr=a, addr_hex=f"0x{a:06x}", value=v))
        vals = [w["value"] for w in words]
        ok = [v for v in vals if isinstance(v, int)]
        npoison = sum(1 for v in ok if v in POISON)
        nzero = sum(1 for v in ok if v == 0)
        ndata = len(ok) - npoison - nzero
        state = ("poison" if npoison == len(ok) else
                 "zero" if nzero == len(ok) else
                 "DATA" if ndata else "mixed")
        res.append(dict(name=name, base=f"0x{base:06x}", words=words,
                        stats=dict(poison=npoison, zero=nzero, data=ndata,
                                   state=state)))
        print(f"\n  {name:<34s} 0x{base:06x}  -> {state}")
        print(f"    poison {npoison}/{len(ok)}  zero {nzero}  data {ndata}")
        # in mau
        for w in words[:6]:
            v = w["value"]
            s = f"0x{v:08x}" if isinstance(v, int) else str(v)
            mark = " POISON" if v in POISON else (" zero" if v == 0 else "")
            print(f"      {w['addr_hex']} = {s}{mark}")

    mm.close()
    os.close(fd)

    # ket luan
    disp = [r for r in res if r["name"].startswith("PDISP")]
    ctrl = [r for r in res if r["name"].startswith("CTRL")]
    disp_data = sum(r["stats"]["data"] for r in disp)
    ctrl_data = sum(r["stats"]["data"] for r in ctrl)
    print(f"\n=== KET LUAN ===")
    print(f"  vung display: {disp_data} word co du lieu / "
          f"{sum(len(r['words']) for r in disp)}")
    print(f"  vung doi chung: {ctrl_data} word co du lieu / "
          f"{sum(len(r['words']) for r in ctrl)}")
    if disp_data == 0 and ctrl_data > 0:
        print("  -> display KHONG addressable qua BAR0, nhung vung khac THI CO.")
        print("     => KHONG phai 'doc sai dia chi'; la address decoder/clock gate.")
    elif disp_data > 0:
        print("  -> display CO addressable! Mau thuan cu da giai.")
    json.dump(dict(bdf=DEV, zones=res,
                   conclusion=dict(display_data_words=disp_data,
                                   control_data_words=ctrl_data)),
              open(out, "w"), indent=1)
    print(f"  -> {out}")


if __name__ == "__main__":
    main()