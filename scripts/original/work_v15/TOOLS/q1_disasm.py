#!/usr/bin/env python3
"""Q1: disasm vung dispatch registry bang capstone RISC-V.

Dung: python3 q1_disasm.py gsp_tu10x.bin GSP/ [vaddr_hex ...]
Mac dinh disasm quanh 8 LUI tim duoc.
"""
import json
import os
import struct
import sys

from capstone import Cs, CS_ARCH_RISCV, CS_MODE_RISCV64, CS_MODE_RISCV32

INNER = 0x40
DELTA = 0x4000000


def elf(d):
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
    shs = elf(d)
    txt = next(s for s in shs if "rm_elf_text" in s["name"])

    # 8 LUI tim duoc (tu q1_lui.json neu co)
    q1 = json.load(open(os.path.join(out, "q1_lui.json")))
    hits = q1["hits"]
    print(f"=== disasm quanh {len(hits)} LUI khop base bang descriptor ===")

    md = Cs(CS_ARCH_RISCV, CS_MODE_RISCV64)
    md.detail = False
    all_rows = []
    for h in hits:
        va = h["vaddr"]
        fo = va - DELTA
        # cua so 128 B truoc, 256 B sau
        lo = max(txt["file_off"], fo - 128)
        hi = min(txt["file_off"] + txt["size"], fo + 256)
        base_va = DELTA + lo
        code = d[lo:hi]
        print(f"\n--- LUI @0x{va:08x} (imm20 {h['imm20']}, covers "
              f"{len(h['covers'])} base) ---")
        rows = []
        for i in md.disasm(code, base_va):
            mark = " <<< LUI khop" if i.address == va else ""
            rows.append(dict(addr=i.address, addr_hex=f"0x{i.address:08x}",
                             mnemonic=i.mnemonic, op_str=i.op_str,
                             bytes=i.bytes.hex(), is_hit=(i.address == va)))
            print(f"  {i.address:08x}  {i.bytes.hex():<10s} "
                  f"{i.mnemonic:<10s} {i.op_str}{mark}")
        all_rows.append(dict(lui=va, imm20=h["imm20"],
                             covers=h["covers"], insns=rows))

    # --- tim pattern doc bang: lui + ld/addi voi offset nho ---
    print(f"\n=== tim pattern truy cap bang descriptor ===")
    found = []
    for blk in all_rows:
        for i, ins in enumerate(blk["insns"]):
            if not ins["is_hit"]:
                continue
            # 8 lenh tiep theo
            for j in range(i + 1, min(i + 9, len(blk["insns"]))):
                n = blk["insns"][j]
                if n["mnemonic"] in ("addi", "ld", "lw"):
                    found.append(dict(lui=blk["lui"], imm20=blk["imm20"],
                                      next_insn=n["mnemonic"] + " " + n["op_str"],
                                      addr=n["addr_hex"], dist=j - i))
                    break
    for f in found:
        print(f"  lui @0x{f['lui']:08x} ({f['imm20']}) -> +{f['dist']} "
              f"{f['next_insn']}")

    # --- thong ke mnemonic trong vung ---
    from collections import Counter
    mc = Counter()
    tot = 0
    for blk in all_rows:
        for ins in blk["insns"]:
            mc[ins["mnemonic"]] += 1
            tot += 1
    print(f"\n=== {tot} lenh decode duoc trong cac cua so ===")
    print(f"  top: {mc.most_common(12)}")
    unknown = mc.get("(bad)", 0) + mc.get("invalid", 0)
    print(f"  invalid/bad: {unknown} ({100 * unknown / max(tot, 1):.1f}%)")

    json.dump(dict(tables_used=len(hits), blocks=all_rows,
                   patterns=found, mnemonic_counts=dict(mc),
                   total_decoded=tot, invalid=unknown),
              open(os.path.join(out, "q1_disasm.json"), "w"), indent=1)
    print(f"\n  -> {out}/q1_disasm.json")


if __name__ == "__main__":
    main()