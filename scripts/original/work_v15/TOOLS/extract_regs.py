#!/usr/bin/env python3
"""P0/P1: trich xuat TOAN BO register definition tu NVIDIA driver source.

Dung: python3 extract_regs.py <src_root> <out.json>
Quet *.h, tim #define NV_<BLOCK>_<REG> <addr> va bitfield con.
"""
import json
import os
import re
import sys

# vd: #define NV_FUSE_OPT_NVDEC_DISABLE   0x00021378 /* RW-4R */
RE_REG = re.compile(
    r"^#define\s+(NV_[A-Z0-9_]+?)\s+"
    r"(0x[0-9A-Fa-f]{5,10})\s*(?:/\*\s*([A-Z0-9\-]+)\s*\*/)?\s*$")
# vd: #define NV_FUSE_OPT_NVDEC_DISABLE_DATA   2:0 /* RWIVF */
RE_BF = re.compile(
    r"^#define\s+(NV_[A-Z0-9_]+?)\s+(\d+):(\d+)\s*(?:/\*\s*([A-Z0-9\-]+)\s*\*/)?\s*$")
# vd: #define NV_..._DATA_YES  0x00000001 /* RW--V */
RE_VAL = re.compile(
    r"^#define\s+(NV_[A-Z0-9_]+?)\s+(0x[0-9A-Fa-f]{1,10})\s*(?:/\*\s*([A-Z0-9\-]+)\s*\*/)?\s*$")

BLOCKS = ["PMC", "PBUS", "PFIFO", "PGRAPH", "GR", "GPC", "TPC", "SM", "L2",
          "FEAT", "STATUS", "OPT", "SPARE", "FPF", "READOUT", "ZB",
          "FB", "MMU", "PMU", "SEC", "FECS", "GPCCS", "NVENC", "NVDEC",
          "PDISP", "PCIE", "FUSE", "THERM", "CLK", "PWR", "PTOP", "PTIMER",
          "PDEC", "PEN", "XV", "XVE", "PRAM", "PDMA", "CE", "HUB", "LT",
          "MSENC", "NVA", "GSP", "PCCS", "PRIV", "PFB", "PCIE"]


def block_of(name):
    """NV_<BLOCK>_... -> BLOCK (khop dai nhat trong danh sach)."""
    parts = name.split("_")
    best = "OTHER"
    bestlen = 0
    for i in range(1, len(parts)):
        cand = "_".join(parts[1:i + 1])
        for b in BLOCKS:
            if cand == b or cand.startswith(b):
                if len(b) > bestlen:
                    best, bestlen = b, len(b)
    return best


def main():
    root, out = sys.argv[1], sys.argv[2]
    regs = {}
    bitfields = {}
    values = {}
    files = 0
    for dirpath, _, names in os.walk(root):
        for fn in names:
            if not fn.endswith(".h"):
                continue
            p = os.path.join(dirpath, fn)
            files += 1
            with open(p, "r", errors="ignore") as f:
                for line in f:
                    s = line.strip()
                    m = RE_BF.match(s)
                    if m:
                        bitfields[m.group(1)] = dict(
                            hi=int(m.group(2)), lo=int(m.group(3)),
                            access=m.group(4), file=p)
                        continue
                    m = RE_REG.match(s)
                    if m:
                        nm, addr = m.group(1), int(m.group(2), 16)
                        if 0x1000 <= addr <= 0x100000000:
                            regs[nm] = dict(addr=addr, access=m.group(3), file=p)
                        continue
                    m = RE_VAL.match(s)
                    if m:
                        values[m.group(1)] = dict(
                            val=int(m.group(2), 16), access=m.group(3), file=p)

    # --- gan bitfield vao register cha ---
    for nm, bf in bitfields.items():
        parent = None
        for cand in regs:
            if nm.startswith(cand + "_") and (parent is None or len(cand) > len(parent)):
                parent = cand
        if parent:
            regs[parent].setdefault("bitfields", []).append(
                dict(name=nm, hi=bf["hi"], lo=bf["lo"], access=bf["access"]))

    # --- phan loai theo block ---
    for nm, r in regs.items():
        r["block"] = block_of(nm)
        r.pop("file", None)

    byblock = {}
    for nm, r in regs.items():
        byblock.setdefault(r["block"], []).append(nm)

    # --- ghi ---
    json.dump(dict(
        source_root=root, headers_scanned=files,
        total_registers=len(regs),
        total_bitfields=len(bitfields),
        total_value_defs=len(values),
        blocks={b: dict(count=len(v), registers=sorted(v))
                for b, v in sorted(byblock.items())},
        registers=regs,
    ), open(out, "w"), indent=1)

    print(f"=== {files:,} header, {len(regs):,} register, "
          f"{len(bitfields):,} bitfield, {len(values):,} value def ===")
    print(f"\n  {'block':<10s} {'regs':>6s} {'co bitfield':>12s}")
    for b, v in sorted(byblock.items(), key=lambda x: -len(x[1])):
        nb = sum(1 for n in v if regs[n].get("bitfields"))
        print(f"  {b:<10s} {len(v):>6d} {nb:>12d}")

    # --- FUSE rieng ---
    fuse = {n: r for n, r in regs.items() if r["block"] == "FUSE"}
    print(f"\n=== FUSE: {len(fuse)} register ===")
    for n, r in sorted(fuse.items(), key=lambda x: x[1]["addr"]):
        bf = r.get("bitfields", [])
        bft = ", ".join(f"{x['name'].split('_')[-1]}[{x['hi']}:{x['lo']}]"
                        for x in bf[:3])
        print(f"  0x{r['addr']:08x}  {n:<52s} {len(bf)} bf  {bft}")


if __name__ == "__main__":
    main()