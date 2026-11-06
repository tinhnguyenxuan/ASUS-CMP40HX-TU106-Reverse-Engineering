#!/usr/bin/env python3
"""P0: phan tich fuse dump + register database -> fuse_map.json, fuse_bitfields.csv.

Dung: python3 fuse_analyze.py <fuse_dump.json> <registers_all.json> <outdir>
"""
import csv
import json
import sys

FUSE_BASE = 0x021000        # aperture cua dump cu
FUSE_BASE_ALT = 0x00820000  # NV_FUSE0_PRI_BASE (driver 615.78.08)
SPAN = 0x1800

GROUPS = [
    ("chip_identification", ["DEVICE", "CHIP", "ID_", "REV", "SKU", "PART"]),
    ("sku_identification", ["SKU", "MARKET", "SEGMENT"]),
    ("gpc_configuration", ["GPC", "TPC", "SM_", "CORE"]),
    ("rop_configuration", ["ROP"]),
    ("l2_configuration", ["L2", "LTC", "SLICE"]),
    ("memory_partition", ["FB", "MEM", "DRAM", "RAM", "PARTITION", "RAMCFG"]),
    ("display_capability", ["DISPLAY", "DISP", "HEAD", "SOR", "DAC", "DP_"]),
    ("video_capability", ["NVDEC", "NVENC", "CODEC", "VIDEO", "MSENC", "DEC",
                          "UCODE", "PFB_NVDEC", "SEC2_UCODE", "GSP_UCODE"]),
    ("security_configuration", ["SECURE", "SEC", "GSP_DEBUG", "AUTH", "SIGN",
                                "WPR", "HS", "BROM", "DEBUG"]),
    ("boot_configuration", ["BOOT", "STRAP", "DEVINIT", "RESET"]),
    ("debug_capability", ["DEBUG", "JTAG", "SPARE", "TEST"]),
    ("production_state", ["STATUS", "PROD", "FUSE_", "LIFE", "REPAIR"]),
    ("feature_flags", ["FEATURE", "READOUT", "OPT_", "CAP"]),
]


def group_of(name, note=""):
    s = (name + " " + note).upper()
    for g, keys in GROUPS:
        for k in keys:
            if k in s:
                return g
    return "unknown_reserved"


def main():
    dump = json.load(open(sys.argv[1]))
    rdb = json.load(open(sys.argv[2]))
    out = sys.argv[3]

    # --- chuan hoa dump: ho tro nhieu dinh dang ---
    words = {}
    # dinh dang fuse_tu106.json: {"base":..,"poison":..,"regs":{"0":..,"4":..}}
    if isinstance(dump, dict) and "regs" in dump:
        if "base" in dump:
            globals()["FUSE_BASE"] = dump["base"]
        dump = dump["regs"]
    if isinstance(dump, dict):
        for k, v in dump.items():
            try:
                words[int(k, 0) if isinstance(k, str) else int(k)] = int(v)
            except (ValueError, TypeError):
                continue
    elif isinstance(dump, list):
        for i, v in enumerate(dump):
            if v is not None:
                words[i] = int(v)

    regs = {n: r for n, r in rdb["registers"].items()
            if r["block"] == "FUSE" or n.startswith("NV_FUSE")}

    # --- map offset trong khoi fuse -> register ---
    # dump key la offset tuong doi (0..SPAN) hoac dia chi tuyet doi?
    keys = sorted(words)
    absolute = min(keys) >= FUSE_BASE if keys else False
    if not keys:
        raise SystemExit("dump rong")
    print(f"=== dump: {len(words)} word, key {keys[0]:#x}..{keys[-1]:#x} "
          f"-> {'TUYET DOI' if absolute else 'TUONG DOI'} ===")

    reglist = []
    for nm, r in regs.items():
        a = r["addr"]
        # quy ve offset trong khoi fuse
        if a >= FUSE_BASE_ALT:
            off = a - FUSE_BASE_ALT
            base_used = FUSE_BASE_ALT
        elif a >= FUSE_BASE:
            off = a - FUSE_BASE
            base_used = FUSE_BASE
        else:
            off = None
            base_used = None
        reglist.append(dict(name=nm, addr=a, offset=off, base=base_used,
                            access=r.get("access"),
                            bitfields=r.get("bitfields", [])))

    # --- ghep gia tri dump ---
    matched = 0
    for x in reglist:
        if x["offset"] is None:
            x["value"] = None
            continue
        k = (FUSE_BASE + x["offset"]) if absolute else x["offset"]
        if k in words:
            x["value"] = words[k]
            x["value_source"] = "dump"
            matched += 1
        else:
            x["value"] = None
    print(f"  {matched}/{len(reglist)} register NV_FUSE* khop offset trong dump")

    # --- bitfield decode ---
    bfrows = []
    for x in reglist:
        for bf in x["bitfields"]:
            hi, lo = bf["hi"], bf["lo"]
            v = x["value"]
            fv = None
            if v is not None:
                fv = (v >> lo) & ((1 << (hi - lo + 1)) - 1)
            bfrows.append(dict(
                register=x["name"], reg_addr=f"0x{x['addr']:08x}",
                fuse_offset=f"0x{x['offset']:x}" if x["offset"] is not None else "",
                bitfield=bf["name"], hi=hi, lo=lo, width=hi - lo + 1,
                access=bf.get("access"),
                reg_value=f"0x{v:08x}" if v is not None else "",
                field_value=fv if fv is not None else "",
                group=group_of(bf["name"], "") ))

    # --- phan loai register ---
    for x in reglist:
        x["group"] = group_of(x["name"])

    # --- unknown: word co du lieu nhung khong register nao phu ---
    covered = {x["offset"] for x in reglist if x["offset"] is not None}
    unknown_words = []
    for k, v in sorted(words.items()):
        off = (k - FUSE_BASE) if absolute else k
        if off in covered:
            continue
        if v in (0, 0xBADF5040, 0xBADF1300, 0xFFFFFFFF):
            continue
        unknown_words.append(dict(offset=off, offset_hex=f"0x{off:04x}",
                                  value=f"0x{v:08x}"))

    # --- thong ke ---
    from collections import Counter
    gc = Counter(x["group"] for x in reglist)
    wdata = sum(1 for v in words.values() if v not in (0, 0xBADF5040, 0xBADF1300))
    wbadf = sum(1 for v in words.values() if v in (0xBADF5040, 0xBADF1300))
    wzero = sum(1 for v in words.values() if v == 0)

    json.dump(dict(
        fuse_aperture=dict(dump_base=f"0x{FUSE_BASE:06x}",
                           alt_base=f"0x{FUSE_BASE_ALT:06x}",
                           note="cung khoi, cung offset, khac cua so BAR0"),
        dump_words=len(words), words_with_data=wdata,
        words_badf=wbadf, words_zero=wzero,
        registers_total=len(reglist), registers_matched=matched,
        bitfields_total=len(bfrows),
        groups={g: n for g, n in gc.most_common()},
        registers=reglist,
        unknown_words=unknown_words,
    ), open(f"{out}/fuse_map.json", "w"), indent=1)

    with open(f"{out}/fuse_bitfields.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(bfrows[0].keys()) if bfrows else [])
        w.writeheader()
        w.writerows(bfrows)

    print(f"\n=== ket qua ===")
    print(f"  {len(reglist)} register, {matched} co gia tri, {len(bfrows)} bitfield")
    print(f"  {len(unknown_words)} word co du lieu nhung KHONG register nao phu")
    print(f"\n  {'nhom':<26s} {'regs':>5s}")
    for g, n in gc.most_common():
        print(f"  {g:<26s} {n:>5d}")
    print(f"\n=== FUSE bitfield DA GIAI NGHIA (co gia tri) ===")
    for r in bfrows:
        if r["field_value"] != "":
            print(f"  0x{int(r['reg_addr'], 16):08x} {r['bitfield'][:52]:<52s} "
                  f"[{r['hi']}:{r['lo']}] = {r['field_value']}")


if __name__ == "__main__":
    main()