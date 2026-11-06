#!/usr/bin/env python3
"""Q1 FINAL: bang descriptor theo disasm — 186 entry, name = u32 offset vao
string pool, khong phai u64 con tro truc tiep.

Bang chung disasm (capstone RISC-V, 0x04F57614..0x04F57658):
  ld   a4, 0x10(s1)      <- nap u64 tu entry+0x10
  lhu  a5, 0x18(s1)      <- nap u16 tu entry+0x18
  va entry+0x10 KHONG phai con tro string ma la {u32 handler_off, u32 name_off}

Dung: /usr/bin/python3 q1_final.py gsp_tu10x.bin GSP/
"""
import json
import struct
import sys

DELTA = 0x4000000
BASE_VA = 0x041A70F0      # entry dau tien (sau 2 entry header cua bang)
SPAN = 0x1740
STRIDE = 32


def main():
    d = open(sys.argv[1], "rb").read()
    out = sys.argv[2].rstrip("/")
    base = BASE_VA - DELTA

    rows = []
    for k in range((SPAN - 0x40) // STRIDE):
        fo = base + k * STRIDE
        if fo + STRIDE > len(d):
            break
        u16 = struct.unpack("<H", d[fo:fo + 2])[0]
        u32 = struct.unpack("<I", d[fo + 4:fo + 8])[0]
        u8 = d[fo + 8]
        lo32 = struct.unpack("<I", d[fo + 0x10:fo + 0x14])[0]
        hi32 = struct.unpack("<I", d[fo + 0x14:fo + 0x18])[0]
        u16b = struct.unpack("<H", d[fo + 0x18:fo + 0x1A])[0]
        # name: hi32 la offset vaddr? thu: neu >= DELTA thi la vaddr truc tiep
        nm = None
        if DELTA <= hi32 < DELTA + len(d):
            f2 = hi32 - DELTA
            if 1 <= f2 < len(d) and d[f2 - 1] == 0:
                e = d.find(b"\x00", f2, f2 + 96)
                if e > f2:
                    s = d[f2:e]
                    if all(32 <= c < 127 for c in s):
                        nm = s.decode("latin1")
        rows.append(dict(idx=k, entry_off=fo, entry_off_hex=f"0x{fo:06x}",
                         f00_u16=u16, f04_u32=f"0x{u32:08x}",
                         f08_u8=u8, f10_lo32=f"0x{lo32:08x}",
                         f14_hi32=f"0x{hi32:08x}",
                         f10_u64=f"0x{struct.unpack('<Q', d[fo+0x10:fo+0x18])[0]:016x}",
                         f18_u16=u16b, name=nm))

    named = [r for r in rows if r["name"]]
    print(f"=== bang @0x{BASE_VA:08x}, {len(rows)} entry x {STRIDE} B ===")
    print(f"  {len(named)}/{len(rows)} entry co ten qua hi32(+0x14)")

    # fallback: neu hi32 khong phai vaddr, thu doc u64(+0x10) la 2 u32
    if len(named) < 50:
        print(f"  -> chi {len(named)}, thu cach khac: u64(+0x10) la 2 x u32 "
              f"(handler_off, name_off) tuong doi")
        named = []
        for r in rows:
            # name_off = lo32, cong vao dau string pool 0x1A6040
            for base_sp in (0x1A6040, 0x1A6000, 0x1A7000):
                v = base_sp + (r["f10_lo32"] and int(r["f10_lo32"], 16))
                if v >= len(d):
                    continue
                e = d.find(b"\x00", v, v + 96)
                if e <= v:
                    continue
                s = d[v:e]
                if all(32 <= c < 127 for c in s) and len(s) >= 4:
                    r["name"] = s.decode("latin1")
                    r["name_src"] = f"pool 0x{base_sp:x} + 0x{int(r['f10_lo32'], 16):x}"
                    break
            if r["name"]:
                named.append(r)
        print(f"  -> {len(named)}/{len(rows)} sau khi thu pool")

    print(f"\n=== {len(named)} entry co ten ===")
    for r in named[:60]:
        print(f"  [{r['idx']:>3d}] id={r['f00_u16']:<5d} f08=0x{r['f08_u8']:02x} "
              f"f18={r['f18_u16']:<6d} {r['name']}")

    names = [r["name"] for r in named]
    T = ["RMClkVfOverride", "RmAtsVolOverride", "RmClkControllersOverride",
         "OVERVOLTAGE_LOGIC", "OVERVOLTAGE_NVVDD_0", "OVERVOLTAGE_NVVDD_1",
         "PERFORMANCE_CAP0", "PERF_CF_CONTROLLER_GPC_MAX", "RELIABILITY_NVVDD"]
    print(f"\n=== ten muc tieu ===")
    for t in T:
        print(f"  {t:<32s} {'CO' if t in names else 'khong'}")

    json.dump(dict(base_vaddr=f"0x{BASE_VA:08x}", span=SPAN, stride=STRIDE,
                   entries=rows, named=len(named), names=names,
                   evidence="capstone disasm 0x04F57614..0x04F57658",
                   layout={"f00_u16": "id", "f04_u32": "?", "f08_u8": "?",
                           "f10_u64": "handler_off + name_off (2 x u32)",
                           "f18_u16": "?"},
                   targets_present={t: (t in names) for t in T}),
              open(f"{out}/q1_final.json", "w"), indent=1)
    print(f"\n  -> {out}/q1_final.json")


if __name__ == "__main__":
    main()