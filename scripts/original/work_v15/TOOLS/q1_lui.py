#!/usr/bin/env python3
"""Q1-lite: tim hang so bang descriptor trong code RISC-V, KHONG can Ghidra.

RISCV LUI: bits[6:0]=0x37, rd=bits[11:7], imm[31:12]=bits[31:12] (sign-extend).
RISC-V nap dia chi 0x41AA418 bang: lui rd,0x41AA + addi rd,rd,0x418
  imm20 = (addr + 0x800) >> 12  (lam tron)

Quet .text step=2 (RVC), tim LUI co imm20 khop voi base cua 60 bang descriptor.

Dung: python3 q1_lui.py gsp_tu10x.bin GSP/
"""
import json
import os
import struct
import sys

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


def imm20_of_lui(w):
    v = (w >> 12) & 0xFFFFF
    return v - 0x100000 if v & 0x80000 else v


def main():
    d = open(sys.argv[1], "rb").read()
    out = sys.argv[2].rstrip("/")
    shs = elf(d)

    # --- 60 bang descriptor: lay base vaddr ---
    q9 = json.load(open(os.path.join(out, "gsp_functions.json")))
    bases = [t["vaddr"] for t in q9["tables"]]
    print(f"=== {len(bases)} bang descriptor, base vaddr "
          f"0x{min(bases):08x}..0x{max(bases):08x} ===")

    # target imm20 cho moi base (ca base va base+0x10)
    tgt = {}
    for b in bases:
        for off in (0, 0x10):
            a = b + off
            imm = (a + 0x800) >> 12
            tgt.setdefault(imm, []).append((a, off))
    print(f"  {len(tgt)} gia tri imm20 can tim")

    # --- quet .text ---
    txt = [s for s in shs if "text" in s["name"] and s["size"] > 64]
    total_bytes = sum(s["size"] for s in txt)
    print(f"\n=== quet {len(txt)} section text, {total_bytes:,} B, step=2 ===")

    hits = []
    lui_count = 0
    for s in txt:
        lo = s["file_off"]
        hi = min(lo + s["size"], len(d) - 4)
        for o in range(lo, hi, 2):
            w = struct.unpack("<I", d[o:o + 4])[0]
            if (w & 0x7F) != 0x37:          # LUI
                continue
            lui_count += 1
            imm = imm20_of_lui(w)
            if imm in tgt:
                rd = (w >> 7) & 0x1F
                pc_va = DELTA + o
                hits.append(dict(file_off=o, vaddr=pc_va, rd=rd,
                                 imm20=f"0x{imm & 0xFFFFF:x}",
                                 covers=[f"0x{a:08x}" for a, _ in tgt[imm]]))
    print(f"  {lui_count:,} lenh LUI trong text")
    print(f"  {len(hits)} LUI co imm20 khop base bang descriptor")

    if hits:
        print(f"\n=== LUI khop ===")
        for h in hits[:40]:
            print(f"  0x{h['vaddr']:08x} (file 0x{h['file_off']:08x}) "
                  f"lui x{h['rd']}, {h['imm20']}  -> {h['covers']}")
        if len(hits) > 40:
            print(f"  ... va {len(hits) - 40} nua")

    # --- neu co hit, kiem tra addi tiep theo (2..24 byte) ---
    print(f"\n=== kiem tra addi/ld tiep theo de xac nhan dia chi day du ===")
    confirmed = []
    for h in hits[:200]:
        o = h["file_off"]
        rd = h["rd"]
        base = (imm20_of_lui(struct.unpack("<I", d[o:o + 4])[0]) << 12)
        for k in range(1, 13):
            o2 = o + k * 2
            if o2 + 4 > len(d):
                break
            w2 = struct.unpack("<I", d[o2:o2 + 4])[0]
            if (w2 & 3) != 3:
                continue
            op = w2 & 0x7F
            rs1 = (w2 >> 15) & 0x1F
            if rs1 != rd or op not in (0x13, 0x03):
                continue
            imm = (w2 >> 20) & 0xFFF
            if imm & 0x800:
                imm -= 0x1000
            full = base + imm
            if full & 0xFFFFFFFF in [int(x, 16) for x in h["covers"]]:
                confirmed.append(dict(lui=h["vaddr"], insn=DELTA + o2,
                                      dist=k, addr=f"0x{full:08x}",
                                      op=f"0x{op:02x}"))
                break

    print(f"  {len(confirmed)} xac nhan day du (lui + addi/ld = base)")
    for c in confirmed[:20]:
        print(f"  @0x{c['lui']:08x} -> 0x{c['addr']} (cach {c['dist']} lenh, "
              f"op 0x{c['op'][2:]})")

    # --- cung thu: co LUI nao cho vung 0x41A7..0x41B4 khong (mo rong) ---
    print(f"\n=== LUI co imm20 trong dai bang descriptor (0x41A-0x41B) ===")
    zone = [h for h in hits if 0x41A <= (int(h["imm20"], 16)) <= 0x41B]
    print(f"  {len(zone)} LUI")

    json.dump(dict(tables=len(bases), target_imm20=len(tgt),
                   lui_in_text=lui_count, hits=hits,
                   confirmed=confirmed,
                   note="LUI imm20 khop base bang descriptor la bang chung code "
                        "truy cap bang bang hang so (khong qua con tro)"),
              open(os.path.join(out, "q1_lui.json"), "w"), indent=1)
    print(f"\n  -> {out}/q1_lui.json")


if __name__ == "__main__":
    main()