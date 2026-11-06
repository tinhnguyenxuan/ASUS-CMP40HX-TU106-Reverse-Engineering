#!/usr/bin/env python3
"""P3: parse LAI bang descriptor GSP-RM dung cach (loai bo fragment chuoi).

Van de ban cu: entry 32 B khong can le dung -> doc ra duoi chuoi cua entry truoc
(vd 'CONTROLLER_GPC_MAX' la phan con lai cua 'PERF_CF_CONTROLLER_GPC_MAX').

Sua: chi nhan entry khi name_ptr tro toi DAU chuoi (byte truoc la 0x00 hoac
ngoai vung string), va khi truong name khong phai suffix cua entry truoc.

Dung: python3 gsp_desc2.py gsp_tu10x.bin GSP/
"""
import json
import struct
import sys

DELTA = 0x4000000
INNER = 0x40


def load_elf(d):
    e = d[INNER:INNER + 64]
    shoff = struct.unpack("<Q", e[40:48])[0]
    shsz = struct.unpack("<H", e[58:60])[0]
    shnum = struct.unpack("<H", e[60:62])[0]
    shstr = struct.unpack("<H", e[62:64])[0]
    o = INNER + shoff + shstr * shsz
    stoff = struct.unpack("<Q", d[o + 24:o + 32])[0]
    stsz = struct.unpack("<Q", d[o + 32:o + 40])[0]
    strs = d[INNER + stoff:INNER + stoff + stsz]
    shs = []
    for i in range(shnum):
        o = INNER + shoff + i * shsz
        nm = struct.unpack("<I", d[o:o + 4])[0]
        addr = struct.unpack("<Q", d[o + 16:o + 24])[0]
        off = struct.unpack("<Q", d[o + 24:o + 32])[0]
        size = struct.unpack("<Q", d[o + 32:o + 40])[0]
        z = strs.find(b"\x00", nm)
        shs.append(dict(name=strs[nm:z].decode("latin1"), vaddr=addr,
                        file_off=INNER + off, size=size))
    return shs


def main():
    d = open(sys.argv[1], "rb").read()
    out = sys.argv[2].rstrip("/")
    shs = load_elf(d)
    rodata = next(s for s in shs if "rm_elf_rodata" in s["name"])

    # ---------- 1. quet string da ket thuc (dense string table) ----------
    LO, HI = rodata["file_off"], rodata["file_off"] + rodata["size"]
    strs = []            # (file_off, name)
    i = LO
    while i < HI:
        if 32 <= d[i] < 127:
            j = d.find(b"\x00", i, min(i + 128, HI))
            if j > i:
                s = d[i:j]
                if all(32 <= c < 127 for c in s) and len(s) >= 4:
                    strs.append((i, s.decode()))
                i = j + 1
                continue
        i += 1
    print(f"=== {len(strs):,} string trong .rodata ({rodata['size']:,} B) ===")

    # ---------- 2. tim day entry 32 B that ----------
    # dieu kien: u64 ptr -> file_off cua string CO THAT (dung bang strs),
    #            f0c == 0, va ptr tang dan.
    off2name = {}
    for fo, nm in strs:
        off2name.setdefault(fo, nm)
    VA2FILE = lambda va: va - DELTA

    cands = []
    step = 4
    for o in range(LO, HI - 32, step):
        p = struct.unpack("<Q", d[o:o + 8])[0]
        if not (DELTA < p < DELTA + len(d)):
            continue
        fo = VA2FILE(p)
        if fo not in off2name:
            continue
        f0c = struct.unpack("<I", d[o + 12:o + 16])[0]
        if f0c != 0:
            continue
        idv = struct.unpack("<I", d[o + 16:o + 20])[0]
        f18 = struct.unpack("<I", d[o + 24:o + 28])[0]
        if not (idv < 10000 and f18 < 10000):
            continue
        cands.append((o, off2name[fo], p, idv, f18))
    print(f"  {len(cands)} ung vien entry 32 B (f0c=0, ptr hop le)")

    # gom thanh bang: entry lien tiep cach nhau 32
    runs = []
    cur = [cands[0]] if cands else []
    for a, b in zip(cands, cands[1:]):
        if b[0] - a[0] == 32:
            cur.append(b)
        else:
            runs.append(cur)
            cur = [b]
    if cur:
        runs.append(cur)
    runs = [r for r in runs if len(r) >= 3]
    print(f"  {len(runs)} bang (>=3 entry lien tiep)")

    total = 0
    tables = []
    for r in runs:
        base = r[0][0]
        print(f"\n--- bang @0x{base:06x} (vaddr 0x{DELTA + base:08x}), "
              f"{len(r)} entry ---")
        ents = []
        for o, nm, p, idv, f18 in r:
            f08 = struct.unpack("<I", d[o + 8:o + 12])[0]
            f14 = struct.unpack("<I", d[o + 20:o + 24])[0]
            e = dict(entry_off=o, name=nm, name_ptr=p, id=idv,
                     f08=f"0x{f08:08x}", f14=f14, f18=f18)
            ents.append(e)
            total += 1
            print(f"  0x{o:06x} id={idv:<4d} f08=0x{f08:08x} f14={f14:<4d} "
                  f"f18={f18:<4d}  {nm}")
        tables.append(dict(base=base, vaddr=DELTA + base, entries=ents))

    print(f"\n  TONG: {total} entry that trong {len(tables)} bang")

    # ---------- 3. doi chieu voi strings muc tieu ----------
    TARGETS = ["RMClkVfOverride", "RmAtsVolOverride", "RmClkControllersOverride",
               "OVERVOLTAGE_LOGIC", "OVERVOLTAGE_NVVDD_0", "OVERVOLTAGE_NVVDD_1",
               "PERFORMANCE_CAP0", "PERF_CF_CONTROLLER_GPC_MAX"]
    have = {e["name"] for t in tables for e in t["entries"]}
    print(f"\n=== string muc tieu co trong bang descriptor? ===")
    for t in TARGETS:
        print(f"  {t:<34s} {'CO' if t in have else 'KHONG'}")

    # ---------- 4. xref: co con tro nao toi base khong ----------
    print(f"\n=== xref toi base cac bang ===")
    for t in tables:
        for what, va in (("base", t["vaddr"]), ("+0x10", t["vaddr"] + 0x10)):
            w = struct.pack("<Q", va)
            n = d.count(w)
            if n:
                loc = []
                i = 0
                while True:
                    i = d.find(w, i)
                    if i < 0:
                        break
                    loc.append(i)
                    i += 1
                print(f"  bang @0x{t['base']:06x} {what}: {n} hit {[hex(x) for x in loc[:4]]}")
    print("  (khong in dong nao = 0 hit)")

    json.dump(dict(delta=DELTA, rodata=dict(file_off=rodata["file_off"],
                                            size=rodata["size"]),
                   strings_found=len(strs),
                   candidate_entries=len(cands),
                   real_entries=total, real_tables=len(tables),
                   tables=tables,
                   targets_present={t: (t in have) for t in TARGETS},
                   note="ban cu dem 139 entry la SAI: nhieu 'entry' chi la duoi "
                        "chuoi cua entry truoc (vd CONTROLLER_GPC_MAX sau "
                        "PERF_CF_CONTROLLER_GPC_MAX)"),
              open(f"{out}/gsp_functions.json", "w"), indent=1)
    print(f"\n  -> {out}/gsp_functions.json")


if __name__ == "__main__":
    main()