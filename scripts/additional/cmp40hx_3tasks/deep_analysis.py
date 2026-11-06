#!/usr/bin/env python3
"""Giai ma sau: 40 bang PERF_PTRS + VFE_VAR + IBVL digest.

Dung: python3 deep_analysis.py CMP40HX_ORIGINAL_1MB.bin
"""
import hashlib
import struct
import sys

IMG = 0x28600
IMG_LEN = 0xF400
EFI_LEN = 0x11000
PERF = 0x288D4
VFE_HDR = 0x5649C
VFE_SLOT = 0x56699
SLOT_STRIDE = 24
IBVL = 0x7684B

FREQS = {1650: 0x0672, 1890: 0x0762, 1905: 0x0771, 2100: 0x0834}


def ptr(p):
    a = IMG + p
    return a + EFI_LEN if p >= IMG_LEN else a


def task1(rom):
    print("=" * 96)
    print("NHIEM VU 1: TOAN BO 40 BANG PERF_PTRS")
    print("=" * 96)
    print(f"{'#':>3s} {'ROM':>8s} {'ver':>4s} {'hdr':>4s} {'esz':>4s} {'cnt':>4s} "
          f"{'size':>6s}  header 20B")
    print("-" * 96)
    rows = []
    for i in range(56):
        p = struct.unpack("<I", rom[PERF + i * 4:PERF + i * 4 + 4])[0]
        if not p:
            continue
        at = ptr(p)
        ver, hdr, esz, cnt = rom[at], rom[at + 1], rom[at + 2], rom[at + 3]
        size = hdr + esz * cnt
        rows.append((i, at, ver, hdr, esz, cnt, size))
        print(f"{i:>3d} 0x{at:06x} 0x{ver:02x} {hdr:>4d} {esz:>4d} {cnt:>4d} "
              f"{size:>6d}  {rom[at:at + 20].hex(' ')}")

    # --- kiem chung: co tan so u16 khong ---
    print("\n--- quet u16 tan so (1650/1890/1905/2100) trong tung bang ---")
    found = 0
    for i, at, ver, hdr, esz, cnt, size in rows:
        body = rom[at + hdr:at + size]
        for j in range(len(body) - 1):
            v = struct.unpack("<H", body[j:j + 2])[0]
            if v in FREQS:
                print(f"  PERF[{i}] 0x{at:06x} entry {(j)//esz} +0x{j % esz:02x} "
                      f"u16=0x{v:04x} = {FREQS[v]} MHz")
                found += 1
    print(f"  -> {found} hit")

    # --- PERF[0] = P-table, ver 0x60 ngoai nouveau ---
    p0 = rows[0][1]
    ver, hdr = rom[p0], rom[p0 + 1]
    print(f"\n--- PERF[0] @0x{p0:06x} = P-TABLE ---")
    print(f"  ver=0x{ver:02x} hdr={hdr}  (nouveau chi ho tro ver<=0x41)")
    # tim diem het du lieu
    end = p0 + hdr
    while end < p0 + 0x400 and rom[end] != 0:
        end += 1
    print(f"  body: 0x{p0 + hdr:06x}..0x{end:06x} = {end - p0 - hdr} B")
    print(f"  header 10B: {rom[p0:p0 + hdr].hex(' ')}")
    # thu (body)/N
    body = end - p0 - hdr
    print(f"  body {body} B: " + ", ".join(
        f"{n} entry x {(body // n) if n and body % n == 0 else '?'}B"
        for n in (1, 2, 3, 5, 6, 10, 23) if n and body % n == 0))
    return rows


def task2(rom):
    print("\n" + "=" * 96)
    print("NHIEM VU 2: VFE_VAR + phuong trinh tan so")
    print("=" * 96)

    # --- T3: kiem chung var_idx cua 4 slot ---
    print("--- var_idx (byte +1) cua 4 slot dien ap ---")
    for i, nm in ((0, "REL"), (1, "ALT"), (3, "OV"), (4, "VMIN")):
        o = VFE_SLOT + i * SLOT_STRIDE
        b = rom[o:o + SLOT_STRIDE]
        print(f"  slot{i} {nm:<5s} type={b[0]:>2d} var={b[1]:>3d} next=0x{b[2]:02x} "
              f"c0={struct.unpack('<f', b[11:15])[0]:>10.1f}")
    print("  -> REL/ALT var=10, OV var=7 -> selector 03 03 03 ep kieu 10 vao kieu 7 => SAI")

    # --- VFE_VAR: 0x5649C..0x56699 ---
    span = VFE_SLOT - VFE_HDR - 9
    print(f"\n--- VFE_VAR: 0x{VFE_HDR:06x}..0x{VFE_SLOT:06x} ---")
    print(f"  header 9B: {rom[VFE_HDR:VFE_HDR + 9].hex(' ')}")
    print(f"  con lai {span} B = {span // 20} x 20 B = {span / 20:.1f}")
    used = set()
    for i in range(150):
        o = VFE_SLOT + i * SLOT_STRIDE
        used.add(rom[o + 1])
    print(f"  var_idx duoc dung: {sorted(used - {255})}")
    print(f"\n  {'var':>4s} {'offset':>9s} {'20B hex':<47s} {'u16[0..4]'}")
    for v in range(25):
        o = VFE_HDR + 9 + v * 20
        b = rom[o:o + 20]
        u = struct.unpack("<10H", b)
        mark = " <== DUNG" if v in used else ""
        print(f"  {v:>4d} 0x{o:06x} {b.hex(' ')} {u[:5]}{mark}")

    # --- slot 10: phuong trinh nghi la tan so ---
    print("\n--- slot[10] = phuong trinh bac 2 nghi tan so ---")
    o = VFE_SLOT + 10 * SLOT_STRIDE
    b = rom[o:o + SLOT_STRIDE]
    c0, c1, c2 = (struct.unpack("<f", b[k:k + 4])[0] for k in (11, 15, 19))
    print(f"  y = {c0:.6f} + {c1:.6f}*x + {c2:.9f}*x^2   var={b[1]} type={b[0]}")
    print(f"  nghiem y=0: x = {-c1 / (2 * c2) if c2 else 0:.2f}  (dinh parabol)")
    # thu cac don vi cho x
    for nm, x in (("mV REL", 1068.75), ("MHz 1890", 1890), ("MHz 1650", 1650),
                  ("raw 0x021c=540", 540), ("temp 65C", 65)):
        y = c0 + c1 * x + c2 * x * x
        print(f"    x={nm:<14s} {x:>8.2f} -> y = {y:>12.2f}")

    # --- tim slot co nghiem ~1890 ---
    print("\n--- slot nao cho y=1890 hoac x=1890 ra gia tri hop le ---")
    for i in range(150):
        o = VFE_SLOT + i * SLOT_STRIDE
        b = rom[o:o + SLOT_STRIDE]
        if b[0] == 0:
            continue
        c0, c1, c2 = (struct.unpack("<f", b[k:k + 4])[0] for k in (11, 15, 19))
        if c2 == 0 or c1 == 0:
            continue
        # nghiem cua y = 1890
        disc = c1 * c1 - 4 * c2 * (c0 - 1890)
        if disc < 0:
            continue
        for s in (1, -1):
            x = (-c1 + s * disc ** 0.5) / (2 * c2)
            if 500 < x < 2500:
                print(f"  slot[{i:>3d}] var={b[1]:>3d} y=1890 tai x={x:.2f}"
                      f"   (y = {c0:.2f} + {c1:.4f}x + {c2:.8f}x^2)")
                break


def task3(rom):
    print("\n" + "=" * 96)
    print("NHIEM VU 3: 10 digest trong IBVL vs cac bang ROM")
    print("=" * 96)
    cnt = struct.unpack("<I", rom[IBVL + 8:IBVL + 12])[0]
    print(f"IBVL @0x{IBVL:06x}: {rom[IBVL:IBVL + 26].hex(' ')}")
    print(f"  sig=IBVL cnt={cnt}")

    # 10 entry x 32 B tu 0x76884+? -> da do: 0x768a5 bat dau vung hash
    H0 = 0x768a5
    digests = []
    for k in range(10):
        o = H0 + k * 32
        digests.append(rom[o:o + 32])
        print(f"  [{k}] @0x{o:06x} {digests[k].hex()}")

    # --- so khop: digest co phai hash cua vung ROM nao khong ---
    print("\n--- so digest voi SHA256 cua cac vung da biet ---")
    regions = [
        ("legacy x86 #1", 0x028600, 0x037A00),
        ("EFI #1", 0x037A00, 0x048A00),
        ("NPDS-E0 #1", 0x048A00, 0x054000),
        ("NPDS-E0 #2", 0x054000, 0x076800),
        ("NPDS-70 (chu ky)", 0x076800, 0x078400),
        ("VFE 150 slot", VFE_SLOT, VFE_SLOT + 150 * SLOT_STRIDE),
        ("VFE header+var", VFE_HDR, VFE_SLOT),
        ("POWER TABLE", 0x57E92, 0x57E92 + 1364),
        ("THERMAL", 0x58679, 0x58679 + 170),
        ("FAN", 0x58824, 0x58824 + 58),
        ("PERF table", 0x54155, 0x541A4),
        ("bang 0x54600", 0x54600, 0x54600 + 183 * 70),
    ]
    hits = 0
    for nm, s, e in regions:
        h = hashlib.sha256(rom[s:e]).digest()
        for k, d in enumerate(digests):
            if h == d:
                print(f"  KHOP: {nm} 0x{s:06x}..0x{e:06x} == digest[{k}]")
                hits += 1
    sha384 = [("legacy", 0x028600, 0x037A00), ("EFI", 0x037A00, 0x048A00)]
    for nm, s, e in sha384:
        h = hashlib.sha384(rom[s:e]).digest()
        for k, d in enumerate(digests):
            if h[:32] == d:
                print(f"  KHOP SHA384[:32]: {nm} == digest[{k}]")
                hits += 1
    print(f"  -> {hits} khop ({len(regions) + len(sha384)} vung x 10 digest = "
          f"{(len(regions) + len(sha384)) * 10} phep thu)")

    # --- digest co phai hash cua header/object directory khong ---
    print("\n--- thu SHA256 cua cac cua so 0x2000 B (object nho) ---")
    for s in range(0x28000, 0x79000, 0x2000):
        h = hashlib.sha256(rom[s:s + 0x2000]).digest()
        for k, d in enumerate(digests):
            if h == d:
                print(f"  KHOP: 0x{s:06x}..0x{s + 0x2000:06x} == digest[{k}]")
                hits += 1
    print(f"  tong {hits} khop")


def main():
    rom = open(sys.argv[1], "rb").read()
    task1(rom)
    task2(rom)
    task3(rom)


if __name__ == "__main__":
    main()