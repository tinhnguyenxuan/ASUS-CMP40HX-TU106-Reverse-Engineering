#!/usr/bin/env python3
"""Q1: parse bang descriptor THEO CODE (base 0x41A70B0, entry 32, name@+0x10).

Base va layout lay tu disasm vung 0x4F5761C..0x4F57658 (capstone RISC-V):
  lui  s1, 0x41a7
  addi s1, s1, 0xb0          -> base = 0x041A70B0
  lui  s8, 1 ; addi s8,s8,0x740 ; add s8,s1,s8   -> end = base + 0x1740
vong lap:
  addi s1, s1, 0x20          -> stride 32
  beq  s8, s1, <thoat>
  lhu  a7, 0x00(s1)
  lw   a6, 0x04(s1)
  lbu  a3, 0x08(s1)
  ld   a4, 0x10(s1)          -> u64 = name_ptr
  lhu  a5, 0x18(s1)

Dung: /usr/bin/python3 q1_regtable.py gsp_tu10x.bin GSP/
"""
import json
import os
import struct
import sys

DELTA = 0x4000000
BASE_VA = 0x041A70B0
SPAN = 0x1740
STRIDE = 32


def main():
    d = open(sys.argv[1], "rb").read()
    out = sys.argv[2].rstrip("/")
    base = BASE_VA - DELTA

    def name_of(va):
        fo = va - DELTA
        if not (1 <= fo < len(d)) or d[fo - 1] != 0:
            return None
        e = d.find(b"\x00", fo, fo + 96)
        if e <= fo:
            return None
        s = d[fo:e]
        return s.decode("latin1") if all(32 <= c < 127 for c in s) else None

    rows = []
    for k in range(SPAN // STRIDE):
        fo = base + k * STRIDE
        if fo + STRIDE > len(d):
            break
        u16 = struct.unpack("<H", d[fo:fo + 2])[0]
        u32 = struct.unpack("<I", d[fo + 4:fo + 8])[0]
        u8 = d[fo + 8]
        u64 = struct.unpack("<Q", d[fo + 0x10:fo + 0x18])[0]
        u16b = struct.unpack("<H", d[fo + 0x18:fo + 0x1A])[0]
        rows.append(dict(idx=k, entry_off=fo, entry_off_hex=f"0x{fo:06x}",
                         f00_u16=u16, f04_u32=f"0x{u32:08x}", f04_u32_int=u32,
                         f08_u8=u8, f10_u64=f"0x{u64:016x}",
                         f18_u16=u16b, name=name_of(u64) if u64 >= DELTA else None))
    named = [r for r in rows if r["name"]]
    names = [r["name"] for r in named]

    print(f"=== bang descriptor @0x{BASE_VA:08x}, {SPAN // STRIDE} entry x "
          f"{STRIDE} B, span 0x{SPAN:x} ===")
    print(f"  {len(named)}/{len(rows)} entry co name_ptr tro toi DAU chuoi that")

    # --- phan bo ---
    from collections import Counter
    print(f"\n=== phan bo field ===")
    print(f"  f08_u8: {dict(Counter(r['f08_u8'] for r in named).most_common(10))}")
    print(f"  f18_u16: {dict(Counter(r['f18_u16'] for r in named).most_common(8))}")
    print(f"  f00_u16 (id): {min(r['f00_u16'] for r in named)}.."
          f"{max(r['f00_u16'] for r in named)}")

    # --- ten muc tieu ---
    T = ["RMClkVfOverride", "RmAtsVolOverride", "RmClkControllersOverride",
         "OVERVOLTAGE_LOGIC", "OVERVOLTAGE_NVVDD_0", "OVERVOLTAGE_NVVDD_1",
         "PERFORMANCE_CAP0", "PERF_CF_CONTROLLER_GPC_MAX", "RELIABILITY_NVVDD",
         "VMIN_NVVDD_0", "VMIN_NVVDD_1", "MCLK_LIMIT", "RATED_TDP_MIN"]
    print(f"\n=== ten muc tieu (bai gio co trong bang) ===")
    for t in T:
        r = next((x for x in named if x["name"] == t), None)
        if r:
            print(f"  {t:<30s} CO  idx={r['idx']:<4d} id={r['f00_u16']:<5d} "
                  f"f08=0x{r['f08_u8']:02x} f18={r['f18_u16']}")
        else:
            print(f"  {t:<30s} khong")

    # --- in toan bo ---
    print(f"\n=== {len(named)} entry co ten (in het) ===")
    for r in named:
        print(f"  [{r['idx']:>3d}] id={r['f00_u16']:<5d} f08=0x{r['f08_u8']:02x} "
              f"f18={r['f18_u16']:<6d} {r['name']}")

    json.dump(dict(
        base_vaddr=f"0x{BASE_VA:08x}", base_file=base, span=SPAN,
        stride=STRIDE, entries=rows, named=len(named), names=names,
        evidence_source="capstone RISC-V disasm cua 0x04F5761C..0x04F57658",
        layout={"f00_u16": "id", "f04_u32": "?", "f08_u8": "? (32 gia tri)",
                "f10_u64": "name_ptr", "f18_u16": "? (13 gia tri)"},
        targets_present={t: (t in names) for t in T},
    ), open(f"{out}/q1_table_final.json", "w"), indent=1)
    print(f"\n  -> {out}/q1_table_final.json")


if __name__ == "__main__":
    main()