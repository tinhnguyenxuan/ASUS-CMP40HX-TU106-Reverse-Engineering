#!/usr/bin/env python3
"""Phan tich sau: IBVL digests + VFE_VAR floats + so sanh payload.

Dung: python3 t3_deep.py CMP40HX_ORIGINAL_1MB.bin [payload.bin]
"""
import hashlib
import struct
import sys


def entropy(b):
    """So byte khac nhau / tong — do 'ngau nhien' tho."""
    return len(set(b)) / len(b) if b else 0


def find_digests(rom):
    """Tim cac blob 32 B entropy cao trong vung IBVL."""
    print("=== IBVL @0x7684b: phan tich cau truc ===")
    h = rom[0x7684b:0x7684b + 26]
    print(f"  raw: {h.hex(' ')}")
    sig, size = h[0:4], struct.unpack("<I", h[4:8])[0]
    print(f"  sig={sig} size={size}")
    # thu doc cac u32 con lai
    for o in range(8, 26, 4):
        if o + 4 <= 26:
            print(f"    +0x{o:02x} u32 = {struct.unpack('<I', h[o:o + 4])[0]}")
            print(f"    +0x{o:02x} u8  = {list(h[o:o + 4])}")

    # quet blob 32 B lien tiep entropy cao
    print("\n=== blob 32 B entropy cao trong 0x76860..0x76c00 ===")
    blobs = []
    o = 0x76860
    while o + 32 <= 0x76c00:
        b = rom[o:o + 32]
        if entropy(b) >= 0.95 and b != b"\x00" * 32 and b != b"\xff" * 32:
            blobs.append((o, b))
            o += 32
        else:
            o += 4
    print(f"  {len(blobs)} blob 32 B")
    for k, (o, b) in enumerate(blobs):
        print(f"    [{k}] @0x{o:06x} {b.hex()}")
    return blobs


def match_digests(rom, blobs):
    print("\n=== doi chieu digest voi hash cac vung ROM ===")
    regions = [
        ("legacy x86 #1", 0x028600, 0x037A00),
        ("EFI #1", 0x037A00, 0x048A00),
        ("NPDS-E0 #1", 0x048A00, 0x054000),
        ("NPDS-E0 #2", 0x054000, 0x076800),
        ("NPDS-70", 0x076800, 0x078400),
        ("VFE hdr+var", 0x05649C, 0x056699),
        ("VFE 150 slot", 0x056699, 0x056699 + 150 * 24),
        ("POWER", 0x057E92, 0x057E92 + 1364),
        ("THERMAL", 0x058679, 0x058679 + 170),
        ("FAN", 0x058824, 0x058824 + 58),
        ("PERF/Ps", 0x054155, 0x0541A4),
        ("bang 0x54600", 0x054600, 0x054600 + 2006),
        ("rail row", 0x02D37B, 0x02D38E),
        ("BIT table", 0x0287B0, 0x0287B0 + 12 + 17 * 6),
    ]
    hits = 0
    for algo in ("sha256", "sha384", "sha512", "blake2s", "sha1", "md5"):
        for nm, s, e in regions:
            d = hashlib.new(algo, rom[s:e]).digest()
            for k, (o, b) in enumerate(blobs):
                if d[:32] == b or d[-32:] == b:
                    print(f"  KHOP {algo}: {nm} 0x{s:06x}..0x{e:06x} == blob[{k}]")
                    hits += 1
    print(f"  -> {hits} khop trong {6 * len(regions) * len(blobs)} phep thu")

    # so digest voi nhau
    print("\n=== blob co trung nhau khong ===")
    seen = {}
    for k, (o, b) in enumerate(blobs):
        if b in seen:
            print(f"  blob[{k}] == blob[{seen[b]}]")
        else:
            seen[b] = k
    print(f"  {len(seen)}/{len(blobs)} blob duy nhat")


def vfe_var(rom):
    print("\n" + "=" * 90)
    print("=== VFE_VAR: 25 bien @0x564a5, stride 20 B — thu doc float32 ===")
    print("=" * 90)
    used = {rom[0x56699 + i * 24 + 1] for i in range(150)} - {255}
    for v in range(25):
        o = 0x564A5 + v * 20
        b = rom[o:o + 20]
        fl = struct.unpack("<5f", b)
        u = struct.unpack("<5I", b)
        mark = " <== DUNG" if v in used else ""
        # chi in float neu trong dai hop ly
        good = [(x, round(x, 3)) for x in fl if 1e-6 < abs(x) < 1e7]
        print(f"  var{v:<2d} 0x{o:06x} u32={u} floats={good}{mark}")


def cmp_payload(rom, pay):
    print("\n" + "=" * 90)
    print("=== SO SANH payload T2 vs ROM goc (vung VFE) ===")
    print("=" * 90)
    SK = 0x28600
    for slot, nm in ((0, "REL"), (1, "ALT"), (3, "OV"), (4, "VMIN")):
        ro = 0x56699 + slot * 24
        po = ro - SK
        diffs = []
        for k, fld in ((3, "clamp_lo"), (7, "clamp_hi"), (11, "c0")):
            a = struct.unpack("<f", rom[ro + k:ro + k + 4])[0]
            b = struct.unpack("<f", pay[po + k:po + k + 4])[0]
            if a != b:
                diffs.append(f"{fld}: {a:.2f} -> {b:.2f}")
        print(f"  slot{slot} {nm:<5s} " + ("; ".join(diffs) if diffs else "(khong doi)"))


def main():
    rom = open(sys.argv[1], "rb").read()
    blobs = find_digests(rom)
    match_digests(rom, blobs)
    vfe_var(rom)
    if len(sys.argv) > 2:
        cmp_payload(rom, open(sys.argv[2], "rb").read())


if __name__ == "__main__":
    main()