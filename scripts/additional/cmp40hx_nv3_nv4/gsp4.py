#!/usr/bin/env python3
"""Phan tich gsp_tu10x.bin: section + XREF registry key + FALCON_DATA + NVINIT + ucodes.

Dung: python3 gsp4.py gsp_tu10x.bin [ucodes_tu10x.bin] [rom]
"""
import struct
import sys

INNER = 0x40
KEYS = [
    "RMHwSpeedoOverride", "RMHwSpeedo1Override", "RMHwSpeedo2Override",
    "RMHwSpeedoCheckIgnore", "RmPmgrIddqNvvddOverride", "RmPmgrIddqOverride",
    "RmPmgrIddqCheckIgnore", "RmPmgrSpeedoCoefficient", "RmPmgrSpeedoOffset",
    "RMClkVfOverride", "RmClockForceUprocVfeVfGen", "RmSramVminCheckIgnore",
    "RmVoltThresholdCtrlCtrl", "RMEnableOverclockingAllPstates",
    "RMForceLockedClocksMode", "RMSec2UseDebugFuseOnlyBinary",
    "RMNoECCFuseCheck", "RmDisableFspFuseErrorCheck",
]


def sections(d):
    B = INNER
    e = d[B:B + 64]
    shoff = struct.unpack("<Q", e[40:48])[0]
    shnum, shstr = struct.unpack("<H", e[60:62])[0], struct.unpack("<H", e[62:64])[0]
    out = []
    # doc shstrtab truoc
    o = B + shoff + shstr * 64
    name_off = struct.unpack("<I", d[o:o + 4])[0]
    str_off = struct.unpack("<Q", d[o + 24:o + 32])[0]
    str_sz = struct.unpack("<Q", d[o + 32:o + 40])[0]
    strs = d[B + str_off:B + str_off + str_sz]
    for i in range(shnum):
        o = B + shoff + i * 64
        nm = struct.unpack("<I", d[o:o + 4])[0]
        stype = struct.unpack("<I", d[o + 4:o + 8])[0]
        flags = struct.unpack("<Q", d[o + 8:o + 16])[0]
        addr = struct.unpack("<Q", d[o + 16:o + 24])[0]
        off = struct.unpack("<Q", d[o + 24:o + 32])[0]
        size = struct.unpack("<Q", d[o + 32:o + 40])[0]
        z = strs.find(b"\x00", nm)
        name = strs[nm:z].decode("latin1")
        out.append((i, name, stype, flags, addr, B + off, size))
    return out


def dump_sections(d):
    print("=" * 92)
    print("gsp_tu10x.bin — ELF64 RISC-V EXEC, 37 section")
    print("=" * 92)
    print(f"  {'#':>3s} {'ten':<22s} {'type':>5s} {'flags':>5s} {'vaddr':>10s} "
          f"{'off':>10s} {'size':>9s}")
    tot = 0
    for i, name, stype, flags, addr, off, size in sections(d):
        tot += size
        print(f"  {i:>3d} {name or '(null)':<22s} {stype:>5d} 0x{flags:03x} "
              f"0x{addr:08x} 0x{off:08x} {size:>9d}")
    print(f"  tong {tot:,} B")


def xref(d):
    print("\n" + "=" * 92)
    print("XREF: dia chi chuoi registry key trong .fwimage (RISC-V, load base 0x4000000)")
    print("=" * 92)
    # .fwimage vaddr 0x4000000 bat dau tai file off 0x40+0? -> proj 0
    LOAD = 0x4000000
    fw_start = INNER            # .fwimage file offset = 0x40
    fw_vaddr = LOAD
    print(f"  {'key':<32s} {'file off':>10s} {'vaddr':>10s}  refs (auipc+lui/adrp)")
    results = {}
    for k in KEYS:
        b = k.encode()
        offs = []
        i = 0
        while True:
            i = d.find(b, i)
            if i < 0:
                break
            offs.append(i)
            i += 1
        if not offs:
            print(f"  {k:<32s} KHONG THAY")
            continue
        va = fw_vaddr + (offs[0] - fw_start)
        print(f"  {k:<32s} 0x{offs[0]:08x} 0x{va:08x}  ({len(offs)} lan)")
        results[k] = (offs[0], va)

    # ---- tim tham chieu: RISC-V lui (0x37) + addi (0x13) hoac lui+ld ----
    print("\n--- tim cap chi thi lui/addi tro toi vaddr cua key ---")
    for k, (foff, va) in results.items():
        hits = 0
        # lui imm20 | rd ; addi rd, rd, imm12  -> target = (imm20<<12) + imm12 (sign)
        # quet vung .text: 0xa000..0x15d3000
        for o in range(0xa000, min(0x15d3000, len(d)) - 8, 2):
            w1 = struct.unpack("<I", d[o:o + 4])[0]
            w2 = struct.unpack("<I", d[o + 4:o + 8])[0]
            if (w1 & 0x7F) != 0x37:          # LUI
                continue
            rd1 = (w1 >> 7) & 0x1F
            imm20 = w1 >> 12
            if (w2 & 0x7F) != 0x13:          # ADDI
                continue
            rd2 = (w2 >> 7) & 0x1F
            rs1 = (w2 >> 15) & 0x1F
            imm12 = (w2 >> 20) & 0xFFF
            if rd2 != rd1 or rs1 != rd1:
                continue
            if imm12 & 0x800:
                imm12 -= 0x1000
            tgt = (imm20 << 12) + imm12
            if tgt == va:
                print(f"  {k}: REF @file 0x{o:08x} (vaddr 0x{LOAD + o - fw_start:08x})")
                hits += 1
                if hits >= 3:
                    break
        if not hits:
            print(f"  {k}: khong thay cap lui/addi truc tiep")

    # ---- tham chieu qua bang con tro 8 byte ----
    print("\n--- tham chieu qua con tro 8 byte (bang dia chi) ---")
    for k, (foff, va) in results.items():
        pat = struct.pack("<Q", va)
        locs = []
        i = 0
        while True:
            i = d.find(pat, i)
            if i < 0:
                break
            locs.append(i)
            i += 1
        if locs:
            print(f"  {k}: {len(locs)} con tro 8B @ {[hex(x) for x in locs[:4]]}")
        else:
            print(f"  {k}: khong co con tro 8B")


def falcon_nvinit(rom):
    print("\n" + "=" * 92)
    print("FALCON_DATA @0x48B54 + NVINIT @0x28893")
    print("=" * 92)
    for base, nm in ((0x48B54, "FALCON_DATA"), (0x28893, "NVINIT")):
        h = rom[base:base + 16]
        print(f"\n{nm} @0x{base:06x}: {h.hex(' ')}")
        ver, hdr, esz, cnt = h[0], h[1], h[2], h[3]
        print(f"  ver=0x{ver:02x} hdr={hdr} esz={esz} cnt={cnt}  "
              f"-> {hdr} + {esz}*{cnt} = {hdr + esz * cnt} B")
        for k in range(min(cnt, 16)):
            o = base + hdr + k * esz
            b = rom[o:o + esz]
            u32 = [struct.unpack("<I", b[j:j + 4])[0] for j in range(0, min(esz, 16), 4)]
            print(f"    [{k:>2d}] @0x{o:06x} {b.hex(' ')}  u32={u32}")


def ucodes(path):
    print("\n" + "=" * 92)
    print(f"NVUCODES: {path}")
    print("=" * 92)
    d = open(path, "rb").read()
    print(f"  file {len(d):,} B  magic={d[0:8]}")
    ver = struct.unpack("<I", d[8:12])[0]
    hsz = struct.unpack("<I", d[12:16])[0]
    print(f"  ver={ver} header_size=0x{hsz:x}")
    STRIDE = 24
    N = (hsz - 0x1F0) // STRIDE
    print(f"\n  {'#':>3s} {'off':>9s} {'size':>9s} {'entropy':>8s}  head 8B")
    blobs = []
    for i in range(N):
        o = 0x1F0 + i * STRIDE
        boff = struct.unpack("<I", d[o + 4:o + 8])[0]
        bsz = struct.unpack("<I", d[o + 8:o + 12])[0]
        if bsz == 0 or boff + bsz > len(d):
            continue
        blob = d[boff:boff + bsz]
        # entropy xap xi
        import math
        from collections import Counter
        c = Counter(blob)
        ent = -sum((v / len(blob)) * math.log2(v / len(blob)) for v in c.values())
        kind = "MA HOA" if ent > 7.9 else ("plaintext" if ent < 7.0 else "ho?n hop")
        blobs.append((i, boff, bsz, ent, blob[:8], kind))
        print(f"  {i:>3d} 0x{boff:08x} {bsz:>9d} {ent:>8.4f}  {blob[:8].hex(' ')}  {kind}")
    plain = [b for b in blobs if b[3] < 7.9]
    enc = [b for b in blobs if b[3] >= 7.9]
    print(f"\n  plaintext: {len(plain)}  ma hoa: {len(enc)}")

    # thu nhan dien loai blob plaintext
    print("\n--- nhan dien blob plaintext ---")
    for i, boff, bsz, ent, head, kind in plain:
        blob = d[boff:boff + min(bsz, 0x400)]
        tags = []
        for sig, name in ((b"\x1a\x00", "?"), (b"nvoc", "nvoc"),
                          (b"fuc", "falcon-ucode"), (b"\x00\x00\x00\x00", "zero")):
            if blob.startswith(sig):
                tags.append(name)
        nz = sum(1 for x in blob if x) / len(blob)
        print(f"  [{i:>2d}] off 0x{boff:08x} {bsz:>7d} B  ent={ent:.3f}  "
              f"nonzero={nz:.0%}  head={head.hex(' ')}  {tags}")


def main():
    d = open(sys.argv[1], "rb").read()
    dump_sections(d)
    xref(d)
    if len(sys.argv) > 3:
        falcon_nvinit(open(sys.argv[3], "rb").read())
    if len(sys.argv) > 2:
        ucodes(sys.argv[2])


if __name__ == "__main__":
    main()