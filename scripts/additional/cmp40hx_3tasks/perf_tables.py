#!/usr/bin/env python3
"""Liet ke toan bo bang PERF_PTRS cua TU106 CMP 40HX.

Layout header (xac nhan bang THERMAL + FAN + POWER):
  byte0 = ver, byte1 = hdr_size, byte2 = entry_size, byte3 = count

Dung: python3 perf_tables.py CMP40HX_ORIGINAL_1MB.bin
"""
import struct
import sys

IMG = 0x28600
IMG_LEN = 0xF400
EFI_LEN = 0x11000
PERF = 0x288D4

KNOWN = {
    0x5649C: "VFE rail header",
    0x57E92: "POWER",
    0x58679: "THERMAL",
    0x58824: "FAN",
    0x2D37B: "rail row (selector VFE)",
    0x550C4: "timing set (60 x 74B)",
}


def ptr(p):
    a = IMG + p
    return a + EFI_LEN if p >= IMG_LEN else a


def main():
    rom = open(sys.argv[1], "rb").read()
    rows = []
    for i in range(56):
        p = struct.unpack("<I", rom[PERF + i * 4:PERF + i * 4 + 4])[0]
        if p == 0:
            continue
        at = ptr(p)
        b = rom[at:at + 4]
        if len(b) < 4:
            continue
        ver, hdr, esz, cnt = b[0], b[1], b[2], b[3]
        size = hdr + esz * cnt
        rows.append((i, p, at, ver, hdr, esz, cnt, size))

    print(f"{'#':>3s} {'ROM':>8s} {'ver':>5s} {'hdr':>4s} {'esz':>4s} "
          f"{'cnt':>4s} {'size':>6s}  ten")
    print("-" * 82)
    for i, p, at, ver, hdr, esz, cnt, size in rows:
        nm = KNOWN.get(at, "")
        print(f"{i:>3d} 0x{at:06x} 0x{ver:02x} {hdr:>4d} {esz:>4d} {cnt:>4d} "
              f"{size:>6d}  {nm}")

    tot = sum(r[7] for r in rows)
    print(f"\n{len(rows)} bang, tong {tot} B "
          f"({100 * tot // (IMG_LEN + EFI_LEN + 0xB600)}% cua vung legacy+EFI+NPDS1)")

    # kiem chung: THERMAL phai ra 4x40, FAN 2x26, POWER 20x66
    assert next(r for r in rows if r[2] == 0x58679)[4:7] == (10, 40, 4)
    assert next(r for r in rows if r[2] == 0x58824)[4:7] == (6, 26, 2)
    assert next(r for r in rows if r[2] == 0x57E92)[4:7] == (44, 66, 20)
    print("[ok] THERMAL/FAN/POWER khop header da biet")


if __name__ == "__main__":
    main()