#!/usr/bin/env python3
"""XREF toan file + FALCON_DATA + NVINIT + NVUCODES.

Dung: python3 final4.py gsp_tu10x.bin ucodes_tu10x.bin rom.bin
"""
import math
import struct
import sys
from collections import Counter

INNER = 0x40
LOAD = 0x4000000


def xref_all(d):
    KEYS = ["RMHwSpeedoOverride", "RMHwSpeedoCheckIgnore", "RmPmgrIddqNvvddOverride",
            "RmPmgrIddqCheckIgnore", "RMClkVfOverride", "RmClockForceUprocVfeVfGen",
            "RMEnableOverclockingAllPstates", "RMForceLockedClocksMode",
            "RMSec2UseDebugFuseOnlyBinary", "RmSramVminCheckIgnore"]
    vas = {}
    for k in KEYS:
        i = d.find(k.encode())
        if i >= 0:
            vas[k] = (i, LOAD + i - INNER)

    print("=" * 92)
    print("XREF TOAN FILE — 3 kieu: con tro u32, u64, auipc+addi")
    print("=" * 92)
    for k, (fo, va) in vas.items():
        p32 = struct.pack("<I", va)
        p64 = struct.pack("<Q", va)
        l32, l64 = [], []
        i = 0
        while True:
            i = d.find(p32, i)
            if i < 0:
                break
            l32.append(i)
            i += 1
        i = 0
        while True:
            i = d.find(p64, i)
            if i < 0:
                break
            l64.append(i)
            i += 1
        print(f"  {k:<32s} va=0x{va:08x}  u32ref={len(l32)} {[hex(x) for x in l32[:3]]}  u64ref={len(l64)}")

    # auipc+addi toan file
    print("\n--- auipc+addi toan file ---")
    want = {va: k for k, (fo, va) in vas.items()}
    found = 0
    for o in range(0, len(d) - 8, 4):
        w1 = struct.unpack("<I", d[o:o + 4])[0]
        if (w1 & 0x7F) != 0x17:
            continue
        rd = (w1 >> 7) & 0x1F
        imm20 = w1 >> 12
        if imm20 & 0x80000:
            imm20 -= 0x100000
        w2 = struct.unpack("<I", d[o + 4:o + 8])[0]
        if (w2 & 0x7F) != 0x13:
            continue
        if ((w2 >> 7) & 0x1F) != rd or ((w2 >> 15) & 0x1F) != rd:
            continue
        imm12 = (w2 >> 20) & 0xFFF
        if imm12 & 0x800:
            imm12 -= 0x1000
        pc = LOAD + o - INNER
        tgt = pc + (imm20 << 12) + imm12
        if tgt in want:
            print(f"  {want[tgt]}: auipc+addi @file 0x{o:08x} vaddr 0x{pc:08x}")
            found += 1
    print(f"  -> {found} auipc ref")


def falcon_nvinit(rom):
    print("\n" + "=" * 92)
    print("FALCON_DATA @0x48B54  +  NVINIT @0x28893")
    print("=" * 92)
    for base, nm in ((0x48B54, "FALCON_DATA"), (0x28893, "NVINIT")):
        h = rom[base:base + 16]
        ver, hdr, esz, cnt = h[0], h[1], h[2], h[3]
        print(f"\n{nm} @0x{base:06x}: {h.hex(' ')}")
        print(f"  ver=0x{ver:02x} hdr={hdr} esz={esz} cnt={cnt} "
              f"-> {hdr} + {esz}*{cnt} = {hdr + esz * cnt} B")
        for k in range(min(cnt, 10)):
            o = base + hdr + k * esz
            b = rom[o:o + esz]
            txt = "".join(chr(c) if 32 <= c < 127 else "." for c in b[:esz])
            print(f"    [{k:>2d}] @0x{o:06x} {b.hex(' ')}")
            if any(32 <= c < 127 for c in b):
                print(f"         txt: {txt}")


def ucodes(path):
    print("\n" + "=" * 92)
    print(f"NVUCODES {path}")
    print("=" * 92)
    d = open(path, "rb").read()
    hsz = struct.unpack("<I", d[12:16])[0]
    print(f"  {len(d):,} B  magic={d[:8]}  ver={struct.unpack('<I', d[8:12])[0]}  hdr=0x{hsz:x}")
    N = (hsz - 0x1F0) // 24
    print(f"  entries = {N}")
    print(f"\n  {'#':>3s} {'off':>9s} {'size':>8s} {'ent':>6s} {'nz%':>5s}  head 12B                loai")
    blobs = []
    for i in range(N):
        o = 0x1F0 + i * 24
        boff = struct.unpack("<I", d[o + 4:o + 8])[0]
        bsz = struct.unpack("<I", d[o + 8:o + 12])[0]
        if bsz == 0 or boff + bsz > len(d):
            continue
        blob = d[boff:boff + bsz]
        c = Counter(blob)
        ent = -sum((v / len(blob)) * math.log2(v / len(blob)) for v in c.values())
        nz = sum(1 for x in blob if x) / len(blob)
        kind = "MA HOA" if ent > 7.9 else "plaintext"
        blobs.append((i, boff, bsz, ent, nz, kind, blob[:12]))
        print(f"  {i:>3d} 0x{boff:08x} {bsz:>8d} {ent:>6.3f} {nz:>4.0%}  "
              f"{blob[:12].hex(' '):<23s} {kind}")
    pl = [b for b in blobs if b[5] == "plaintext"]
    en = [b for b in blobs if b[5] == "MA HOA"]
    print(f"\n  plaintext {len(pl)}  |  ma hoa {len(en)}")
    print("\n  plaintext (id, offset, size, entropy):")
    for i, boff, bsz, ent, nz, kind, head in pl:
        print(f"    id={i:<3d} off=0x{boff:08x} size={bsz:>7d} ent={ent:.4f}")
    print("\n  ma hoa:")
    for i, boff, bsz, ent, nz, kind, head in en:
        print(f"    id={i:<3d} off=0x{boff:08x} size={bsz:>7d} ent={ent:.4f}")


def main():
    d = open(sys.argv[1], "rb").read()
    xref_all(d)
    if len(sys.argv) > 3:
        falcon_nvinit(open(sys.argv[3], "rb").read())
    if len(sys.argv) > 2:
        ucodes(sys.argv[2])


if __name__ == "__main__":
    main()