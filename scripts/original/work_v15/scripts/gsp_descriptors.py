#!/usr/bin/env python3
"""B4: bang descriptor regkey trong .rodata — {u64 name_ptr, ...}. Xuat gsp_xrefs.json.

Dung: python3 gsp_descriptors.py outputs/gsp_tu10x.bin
"""
import json
import struct
import sys

DELTA = 0x4000000      # vaddr = file_off + DELTA (sh_offset TUYET DOI tu dau file)
INNER = 0x40


def name_at(d, ptr):
    fo = ptr - DELTA
    if not (0 <= fo < len(d)):
        return None
    e = d.find(b"\x00", fo, fo + 96)
    if e < 0:
        return None
    s = d[fo:e]
    if not s or not all(32 <= c < 127 for c in s):
        return None
    return s.decode()


def find_table(d):
    """Quet vung .rodata tim day entry 32 B co u64 ptr -> string hop le."""
    LO, HI = 0x1a5000, 0x1e0000
    runs = []
    cur = 0
    start = 0
    for o in range(LO, HI, 32):
        p = struct.unpack("<Q", d[o:o + 8])[0]
        nm = name_at(d, p)
        if nm and len(nm) >= 4 and nm.replace("_", "").isalnum():
            if cur == 0:
                start = o
            cur += 1
        else:
            if cur >= 8:
                runs.append((start, start + cur * 32, cur))
            cur = 0
    if cur >= 8:
        runs.append((start, start + cur * 32, cur))
    return runs


def parse_entries(d, lo, hi):
    out = []
    for o in range(lo, hi, 32):
        b = d[o:o + 32]
        p = struct.unpack("<Q", b[0:8])[0]
        nm = name_at(d, p)
        if not nm:
            continue
        out.append(dict(entry_off=o, name=nm, name_ptr=p,
                        f08=struct.unpack("<I", b[8:12])[0],
                        f0c=struct.unpack("<I", b[12:16])[0],
                        id=struct.unpack("<I", b[16:20])[0],
                        f14=struct.unpack("<I", b[20:24])[0],
                        f18=struct.unpack("<I", b[24:28])[0],
                        f1c=struct.unpack("<I", b[28:32])[0]))
    return out


def main():
    d = open(sys.argv[1], "rb").read()
    runs = find_table(d)
    print("=== bang descriptor tim duoc ===")
    for s, e, n in runs:
        print(f"  0x{s:06x}..0x{e:06x}  {n} entry x 32 B  (vaddr 0x{s + DELTA:08x})")

    allent = []
    for s, e, n in runs:
        allent += parse_entries(d, s, e)
    print(f"\n  tong {len(allent)} entry doc duoc\n")

    # --- cac key trong tam ---
    WANT = ("ClkVf", "AtsVol", "ClkControllers", "OVERCLOCK", "SPEEDO", "IDDQ",
            "ForceUproc", "SramVmin", "VoltThreshold", "ForceLocked",
            "PERF_CF_CONTROLLER", "OVERVOLTAGE", "PERFORMANCE_CAP")
    print("=== entry lien quan clock/voltage ===")
    print(f"  {'entry':>8s} {'id':>4s} {'f14':>4s} {'f18':>5s}  {'f08':>10s}  ten")
    rel = []
    for x in allent:
        if any(w.lower() in x["name"].lower() for w in WANT):
            rel.append(x)
            print(f"  0x{x['entry_off']:06x} {x['id']:>4d} {x['f14']:>4d} "
                  f"{x['f18']:>5d}  0x{x['f08']:08x}  {x['name']}")

    # --- tim ai doc bang nay: con tro u64 toi base ---
    print("\n=== tham chieu toi bang (u64 ptr base, va base+0x10) ===")
    for s, e, n in runs:
        for base in (s + DELTA, s + DELTA + 0x10):
            pat = struct.pack("<Q", base)
            locs = []
            i = 0
            while True:
                i = d.find(pat, i)
                if i < 0:
                    break
                locs.append(i)
                i += 1
            if locs:
                print(f"  base 0x{base:08x}: {len(locs)} ref -> {[hex(x) for x in locs[:6]]}")

    # --- nhan xet ve y nghia field ---
    print("\n=== phan bo field (doan nghia) ===")
    from collections import Counter
    for f in ("f08", "f0c", "id", "f14", "f18", "f1c"):
        c = Counter(x[f] for x in allent)
        top = c.most_common(6)
        print(f"  {f}: {len(c)} gia tri khac nhau, pho bien {top}")
    ids = [x["id"] for x in allent]
    print(f"  id tang dan? {ids == sorted(ids)}  khoang {min(ids)}..{max(ids)}")

    json.dump(dict(delta=DELTA, tables=[dict(lo=s, hi=e, entries=n, vaddr=s + DELTA)
                                        for s, e, n in runs],
                   entry_count=len(allent), entries=allent,
                   clock_voltage=[x["name"] for x in rel]),
              open("outputs/gsp_xrefs.json", "w"), indent=1)
    print("\n  -> outputs/gsp_xrefs.json")


if __name__ == "__main__":
    main()