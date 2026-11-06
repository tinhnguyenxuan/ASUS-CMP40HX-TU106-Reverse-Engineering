#!/usr/bin/env python3
"""CLOCK_PTRS + digest block matching + VFE_VAR float.

Dung: python3 clock_digest.py CMP40HX_ORIGINAL_1MB.bin
"""
import hashlib
import struct
import sys

IMG = 0x28600
IMG_LEN = 0xF400
EFI_LEN = 0x11000


def ptr(p):
    a = IMG + p
    return a + EFI_LEN if p >= IMG_LEN else a


def clock_ptrs(rom):
    print("=" * 88)
    print("CLOCK_PTRS (BIT token 0x43, len 2, ptr 0x0263) -> 0x28863")
    print("=" * 88)
    B = 0x28863
    print(f"  raw 96B: {rom[B:B + 96].hex(' ')}")
    print(f"\n  {'#':>3s} {'ptr':>8s} {'ROM':>9s} {'ver':>4s} {'hdr':>4s} {'esz':>4s} "
          f"{'cnt':>4s} {'size':>6s}  head")
    for i in range(24):
        p = struct.unpack("<I", rom[B + i * 4:B + i * 4 + 4])[0]
        if not p:
            continue
        at = ptr(p)
        ver, hdr, esz, cnt = rom[at], rom[at + 1], rom[at + 2], rom[at + 3]
        size = hdr + esz * cnt
        print(f"  {i:>3d} 0x{p:06x} 0x{at:06x} 0x{ver:02x} {hdr:>4d} {esz:>4d} "
              f"{cnt:>4d} {size:>6d}  {rom[at:at + 12].hex(' ')}")

    # ---- tim bang nao chua MHz ----
    print("\n--- quet MHz (dang u16 thuan va 0x3fff-masked) trong cac bang ---")
    FREQ = {1650, 1710, 1890, 1905, 1965, 2025, 2070, 2100}
    for i in range(24):
        p = struct.unpack("<I", rom[B + i * 4:B + i * 4 + 4])[0]
        if not p:
            continue
        at = ptr(p)
        hdr = rom[at + 1]
        for j in range(0x400):
            o = at + j
            if o + 2 > len(rom):
                break
            v = struct.unpack("<H", rom[o:o + 2])[0]
            for cand in (v, v & 0x3FFF):
                if cand in FREQ:
                    print(f"  CLOCK[{i}] 0x{at:06x} +0x{j:03x} raw=0x{v:04x} "
                          f"-> {cand} MHz")
                    break


def digest_blocks(rom):
    print("\n" + "=" * 88)
    print("DIGEST: so 15 blob 32 B (0x76904..0x76bf4) voi hash tung khoi ROM")
    print("=" * 88)
    H0 = 0x76904
    blobs = [rom[H0 + k * 32:H0 + k * 32 + 32] for k in range(15)]
    print(f"  {len(blobs)} blob, {len(set(blobs))} duy nhat")

    hits = 0
    for algo in ("sha256", "sha1", "md5", "blake2s", "sha512"):
        din = hashlib.new(algo).digest_size
        if din < 32:
            continue
        for blk in (0x200, 0x400, 0x800, 0x1000, 0x2000, 0x4000, 0x10000):
            n = 0
            for s in range(0, 0x79000 - blk + 1, blk):
                d = hashlib.new(algo, rom[s:s + blk]).digest()
                for k, b in enumerate(blobs):
                    if d[:32] == b:
                        print(f"  KHOP {algo} blk 0x{blk:x}: 0x{s:06x} "
                              f"({blk}B) == blob[{k}]")
                        hits += 1
                        n += 1
            if n:
                break
    print(f"  -> {hits} khop")

    # ---- co phai la 1 chu ky RSA lien tuc? ----
    print("\n--- kiem tra: 15 blob co lien tuc tu 0x76904 khong ---")
    # do lai vi tri thuc cua cac blob
    ents = []
    o = 0x76880
    while o + 32 <= 0x76c00 and len(ents) < 20:
        b = rom[o:o + 32]
        if len(set(b)) >= 30 and b != b"\xff" * 32 and b != b"\x00" * 32:
            ents.append(o)
            o += 32
        else:
            o += 1
    print(f"  blob tim duoc @ {[hex(x) for x in ents[:16]]}")
    if len(ents) > 2:
        gaps = [ents[i + 1] - ents[i] for i in range(len(ents) - 1)]
        print(f"  gap: {gaps}")
    # vung 0x768e5..0x76c00 co lien tuc khong
    seg = rom[0x768e5:0x76c00]
    print(f"  0x768e5..0x76c00 = {len(seg)} B, byte lap lai nhieu nhat: "
          f"{max(set(seg), key=seg.count)}")


def main():
    rom = open(sys.argv[1], "rb").read()
    clock_ptrs(rom)
    digest_blocks(rom)


if __name__ == "__main__":
    main()