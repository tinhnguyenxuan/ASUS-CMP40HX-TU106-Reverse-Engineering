#!/usr/bin/env python3
"""P0: phan loai fuse TU106 tu dump that. Xuat fuse_map.json + fuse_bitfields.csv.

Dung: python3 fuse_classify.py fuse2.json registers_all.json FUSE/
"""
import csv
import json
import struct
import sys

# register da tai lieu hoa (chi 2 cua turing)
KNOWN = {
    0x378: ("NV_FUSE_OPT_NVDEC_DISABLE", [(2, 0, "DATA")], "RW-4R"),
    0x74C: ("NV_FUSE_OPT_SECURE_GSP_DEBUG_DIS", [(0, 0, "DATA")], "RW-4R"),
}
# tu driver 615.78.08 (khong co trong tu102/dev_fuse.h nhung co header khac)
KNOWN2 = {
    0xC04: ("NV_FUSE_STATUS_OPT_DISPLAY", [(0, 0, "DATA_ENABLE")]),
    0xC1C: ("NV_FUSE_STATUS_OPT_GPC", []),
    0x3814: ("NV_FUSE_FEATURE_READOUT", [(16, 16, "ECC_DRAM_DISABLED")]),
}

# mẫu da biet tu do tren card nay (bang chung doc lap)
MEASURED = {
    0x000: ("NV_PMC_BOOT_0 proxy / fuse strap mirror", 0xC0040000,
            "0x166000A1 la NV_PMC_BOOT_0 tai BAR0+0; gia tri nay cua khoi fuse"),
    0x4D8: ("PCI device ID", 0x00001F0B, "trung 10DE:1F0B"),
    0x56C: ("PCI device ID phu", 0x00001F4B, "trung ho 1F4B"),
    0x650: ("TPC enable mask", 0x0004001F, "17 TPC -> mask"),
}


def hx(v):
    return f"0x{v:08x}"


def main():
    d = json.load(open(sys.argv[1]))
    regs = {int(k): v for k, v in d["regs"].items()}
    poison = set(d["poison"])
    out = sys.argv[2].rstrip("/")

    with_data = {k: v for k, v in regs.items() if v not in poison and v != 0}

    # --- phan loai ---
    rows = []
    for off in sorted(regs):
        v = regs[off]
        state = ("poison" if v in poison else
                 "zero" if v == 0 else "data")
        nm, bfl, acc = "", [], ""
        if off in KNOWN:
            nm, bfl, acc = KNOWN[off]
        elif off in KNOWN2:
            nm, bfl = KNOWN2[off]
        if off in MEASURED:
            nm = nm or MEASURED[off][0]
        fields = []
        for hi, lo, fname in bfl:
            fields.append(dict(name=fname, hi=hi, lo=lo,
                               value=(v >> lo) & ((1 << (hi - lo + 1)) - 1)))
        rows.append(dict(offset=off, offset_hex=f"0x{off:04x}",
                         addr_abs=f"0x{0x21000 + off:06x}",
                         value=hx(v) if isinstance(v, int) else str(v),
                         value_int=v if isinstance(v, int) else None,
                         state=state,
                         documented_name=nm,
                         access=acc,
                         bitfields=fields,
                         note=MEASURED[off][2] if off in MEASURED else ""))

    # --- tim cau truc: cac cum word co du lieu lien tiep ---
    offs = sorted(with_data)
    runs = []
    cur = [offs[0]] if offs else []
    for a, b in zip(offs, offs[1:]):
        if b - a <= 8:
            cur.append(b)
        else:
            runs.append(cur)
            cur = [b]
    if cur:
        runs.append(cur)
    print(f"=== {len(regs)} word, {len(with_data)} co du lieu, "
          f"{len(runs)} cum lien tuc ===")

    # --- bang bit chua biet: nhom theo gia tri giong nhau ---
    from collections import Counter, defaultdict
    vc = Counter(with_data.values())
    print(f"\n  gia tri xuat hien >1 lan:")
    for v, n in vc.most_common(12):
        if n > 1:
            print(f"    {hx(v):>12s} x{n:<3d}  offsets "
                  f"{[f'0x{k:04x}' for k, vv in with_data.items() if vv == v][:6]}")

    # --- doan mask bit: cac word ma moi bit bat doc lap ---
    masks = {k: v for k, v in with_data.items() if v and (v & (v - 1)) == 0}
    print(f"\n  {len(masks)} word la luy thua cua 2 (bitmask 1 bit):")
    for k in sorted(masks)[:20]:
        print(f"    0x{k:04x} = {hx(masks[k])} = 1<<{masks[k].bit_length() - 1}")

    # --- xuat ---
    jm = dict(
        source="fuse_dump2.py (BAR0 aperture 0x021000, read-only, page-wise)",
        aperture=dict(real="0x00021000", alt_not_addressable="0x00820000",
                      note="0x820000 (NV_FUSE0_PRI_BASE trong gb100/hwproject.h) "
                           "tra NV_PMC_BOOT_0 tai offset 0 roi toan poison tren "
                           "TU106 -> KHONG phai cua so cua khoi fuse nay"),
        span_bytes=0x2000,
        note_span="trang 0x2000 toan poison -> khoi fuse ket thuc truoc 0x22000",
        total_words=len(regs), words_with_data=len(with_data),
        runs=len(runs),
        documented_registers=len(KNOWN) + len(KNOWN2),
        rows=rows,
        runs_detail=[dict(start=f"0x{r[0]:04x}", end=f"0x{r[-1]:04x}",
                          words=len(r)) for r in runs],
        power_of_two_words={f"0x{k:04x}": hx(v) for k, v in sorted(masks.items())},
        repeated_values={hx(v): n for v, n in vc.most_common(20) if n > 1},
    )
    json.dump(jm, open(f"{out}/fuse_map.json", "w"), indent=1)

    # csv bitfield
    with open(f"{out}/fuse_bitfields.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["offset", "addr_abs", "register", "bitfield", "hi", "lo",
                    "width", "reg_value", "field_value", "access", "confidence"])
        for r in rows:
            if not r["bitfields"]:
                continue
            for b in r["bitfields"]:
                w.writerow([r["offset_hex"], r["addr_abs"], r["documented_name"],
                            b["name"], b["hi"], b["lo"],
                            b["hi"] - b["lo"] + 1, r["value"], b["value"],
                            r["access"], "DECODED"])

    print(f"\n=== register tai lieu hoa co gia tri ===")
    for r in rows:
        if r["documented_name"] and r["state"] == "data":
            fs = " ".join(f"{b['name']}={b['value']}" for b in r["bitfields"])
            print(f"  0x{r['offset']:04x} {r['documented_name']:<36s} "
                  f"{r['value']:>12s}  {fs}")

    print(f"\n=== mau da biet (doi chieu cheo) ===")
    for off, (nm, exp, note) in sorted(MEASURED.items()):
        got = regs.get(off)
        ok = "KHOP" if got == exp else "KHAC"
        print(f"  0x{off:04x} {nm:<40s} doc {hx(got) if got is not None else '--'}"
              f"  mong {hx(exp)}  {ok}  ({note})")

    print(f"\n  -> {out}/fuse_map.json, {out}/fuse_bitfields.csv")


if __name__ == "__main__":
    main()