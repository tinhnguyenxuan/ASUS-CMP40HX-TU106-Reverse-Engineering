#!/usr/bin/env python3
"""Q1b: tim CALLBACK duoc goi qua `ld a5,0x30(s3); jalr a5`.

Cach lam: quet .text tim lenh `sd aX, 0x30(sY)` — noi NAP con tro vao
context+0x30. Gia tri duoc nap thuong la `auipc ra,+X` + `addi a0,ra,+Y`
(PC-relative toi ham). Tu do suy ra dia chi ham callback.

Dung: /usr/bin/python3 q1_callback.py gsp_tu10x.bin GSP/
"""
import json
import struct
import sys


INNER = 0x40
DELTA = 0x4000000


def elf_sections(d):
    e = d[INNER:INNER + 64]
    shoff = struct.unpack("<Q", e[40:48])[0]
    shsz = struct.unpack("<H", e[58:60])[0]
    shnum = struct.unpack("<H", e[60:62])[0]
    shstr = struct.unpack("<H", e[62:64])[0]
    o = INNER + shoff + shstr * shsz
    stoff = struct.unpack("<Q", d[o + 24:o + 32])[0]
    stsz = struct.unpack("<Q", d[o + 32:o + 40])[0]
    strs = d[INNER + stoff:INNER + stoff + stsz]
    out = []
    for i in range(shnum):
        o = INNER + shoff + i * shsz
        nm = struct.unpack("<I", d[o:o + 4])[0]
        addr = struct.unpack("<Q", d[o + 16:o + 24])[0]
        off = struct.unpack("<Q", d[o + 24:o + 32])[0]
        size = struct.unpack("<Q", d[o + 32:o + 40])[0]
        z = strs.find(b"\x00", nm)
        out.append(dict(name=strs[nm:z].decode("latin1"), vaddr=addr,
                        file_off=INNER + off, size=size))
    return out


def sext(v, bits):
    if v & (1 << (bits - 1)):
        v -= 1 << bits
    return v


def main():
    d = open(sys.argv[1], "rb").read()
    out = sys.argv[2].rstrip("/")
    shs = elf_sections(d)
    txt = [s for s in shs if "text" in s["name"] and s["size"] > 64]

    # --- tim moi `sd` co imm == 0x30 (S-type: opcode 0x23, funct3 0b011) ---
    print("=== quet lenh `sd` voi imm=0x30 trong .text ===")
    cands = []
    for s in txt:
        lo = s["file_off"]
        hi = min(lo + s["size"], len(d) - 4)
        for o in range(lo, hi, 2):
            w = struct.unpack("<I", d[o:o + 4])[0]
            if (w & 3) != 3 or (w & 0x7F) != 0x23:
                continue
            if ((w >> 12) & 7) != 3:        # funct3 = 011 -> sd
                continue
            imm = sext(((w >> 25) << 5) | ((w >> 7) & 0x1F), 12)
            if imm != 0x30:
                continue
            rs1 = (w >> 15) & 0x1F
            rs2 = (w >> 20) & 0x1F
            cands.append(dict(file_off=o, vaddr=DELTA + o, rs1=rs1, rs2=rs2))
    print(f"  {len(cands)} lenh `sd rX, 0x30(rY)`")

    # --- voi moi ung vien, lui ve truoc tim `auipc` nap vao rs2 ---
    #     auipc rd, imm20 ; ... ; addi rd, rd, imm12   -> dia chi ham
    print(f"\n=== lui ve truoc tim auipc+addi nap vao thanh ghi bi store ===")
    resolved = []
    for c in cands:
        o = c["file_off"]
        rd_target = c["rs2"]
        found = None
        # quet 20 lenh (40 byte) truoc
        for back in range(2, 80, 2):
            p = o - back
            if p < 0:
                break
            w = struct.unpack("<I", d[p:p + 4])[0]
            if (w & 3) != 3 or (w & 0x7F) != 0x17:      # auipc
                continue
            rd = (w >> 7) & 0x1F
            if rd != rd_target:
                continue
            hi20 = sext((w >> 12) & 0xFFFFF, 20) << 12
            # tim addi rd, rd, imm12 sau auipc
            for fwd in range(2, 12, 2):
                q = p + fwd
                w2 = struct.unpack("<I", d[q:q + 4])[0]
                if (w2 & 3) != 3:
                    continue
                if (w2 & 0x7F) != 0x13:
                    continue
                if ((w2 >> 7) & 0x1F) != rd or ((w2 >> 15) & 0x1F) != rd:
                    continue
                lo12 = sext((w2 >> 20) & 0xFFF, 12)
                target = (DELTA + p) + hi20 + lo12
                found = dict(target=f"0x{target:08x}", auipc=DELTA + p,
                             addi=DELTA + q, dist_back=back)
                break
            if found:
                break
        if found:
            resolved.append(dict(store=c, **found))

    print(f"  {len(resolved)} store co dia chi ham xac dinh duoc")
    for r in resolved[:30]:
        print(f"    sd @0x{r['store']['vaddr']:08x} <- 0x{r['target']} "
              f"(auipc @0x{r['auipc']:08x})")

    # --- loc theo ham nam trong cum dispatch hoac gan ---
    print(f"\n=== callback ung vien (target trong .text) ===")
    functions = sorted({int(r["target"], 16) for r in resolved})
    for f in functions:
        print(f"  0x{f:08x}")

    json.dump(dict(sd_count=len(cands), resolved=resolved,
                   functions=[f"0x{f:08x}" for f in functions],
                   note="store vao context+0x30 (con tro callback ma ham "
                        "dispatch 0x04F575FC goi qua jalr a5)"),
              open(f"{out}/q1_callback.json", "w"), indent=1)
    print(f"\n  -> {out}/q1_callback.json")


if __name__ == "__main__":
    main()