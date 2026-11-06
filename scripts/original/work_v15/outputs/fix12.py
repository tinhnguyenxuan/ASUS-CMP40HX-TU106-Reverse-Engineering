#!/usr/bin/env python3
"""Sua 2 loi: (1) u16 tan so o moi offset, (2) huong x/y + don vi uV trong VFE.

Dung: python3 fix12.py CMP40HX_ORIGINAL_1MB.bin
"""
import struct
import sys

IMG, IL, EL, PERF = 0x28600, 0xF400, 0x11000, 0x288D4
VFE_SLOT, STRIDE, VAR_BASE, VAR_STRIDE = 0x56699, 24, 0x564A5, 25

# xung GDDR6/GPCCLK thuc te cua TU106 (CMP 40HX / RTX 2060S)
PLAUSIBLE = {300, 405, 620, 810, 860, 1350, 1410, 1440, 1485, 1515, 1635,
             1638, 1650, 1697, 1710, 1740, 1785, 1815, 1890, 1905, 1920,
             1942, 1965, 1980, 2025, 2040, 2070, 2100, 3300, 3500, 5000,
             6000, 6800, 7000, 7500, 8000}


def ptr(p):
    a = IMG + p
    return a + EL if p >= IL else a


def scan_u16(rom):
    print("=" * 96)
    print("LOI 1: quet u16 MOI offset (ca le) trong 40 bang PERF_PTRS")
    print("=" * 96)
    hits = 0
    for i in range(56):
        p = struct.unpack("<I", rom[PERF + i * 4:PERF + i * 4 + 4])[0]
        if not p:
            continue
        at = ptr(p)
        if at + 4 > len(rom):
            continue
        ver, hdr, esz, cnt = rom[at], rom[at + 1], rom[at + 2], rom[at + 3]
        size = hdr + esz * cnt
        if esz == 0 or size > 0x10000:
            continue
        found = []
        for j in range(0, size - 1):          # MOI offset, ca le
            v = struct.unpack("<H", rom[at + j:at + j + 2])[0]
            if v in PLAUSIBLE and v >= 300:
                found.append((j, v, j - hdr, (j - hdr) // esz if esz else -1,
                              (j - hdr) % esz if esz else -1))
        if found:
            hits += 1
            print(f"\n  PERF[{i:>2d}] @0x{at:06x} ver=0x{ver:02x} hdr={hdr} "
                  f"esz={esz} cnt={cnt}  -- {len(found)} u16 tan so:")
            for j, v, eo, ent, ec in found[:14]:
                print(f"     +0x{j:03x} (entry {ent:>3d} +0x{ec:02x})  "
                      f"u16=0x{v:04x} = {v:>5d} MHz")
    print(f"\n  -> {hits} bang co u16 tan so (truoc day bao 0 hit)")


def scan_u32(rom):
    print("\n" + "=" * 96)
    print("Quet u32 tan so (mot so bang dung u32)")
    print("=" * 96)
    for i in range(56):
        p = struct.unpack("<I", rom[PERF + i * 4:PERF + i * 4 + 4])[0]
        if not p:
            continue
        at = ptr(p)
        ver, hdr, esz, cnt = rom[at], rom[at + 1], rom[at + 2], rom[at + 3]
        size = hdr + esz * cnt
        if esz == 0 or size > 0x10000:
            continue
        found = []
        for j in range(0, size - 3):
            v = struct.unpack("<I", rom[at + j:at + j + 4])[0]
            if v in PLAUSIBLE and v >= 300:
                found.append((j, v))
        if found:
            print(f"  PERF[{i:>2d}] @0x{at:06x}: " +
                  ", ".join(f"+0x{j:03x}={v}" for j, v in found[:8]))


def vfe_fixed(rom):
    print("\n" + "=" * 96)
    print("LOI 2: VFE dung huong x/y + don vi uV")
    print("=" * 96)
    sl = []
    for i in range(150):
        o = VFE_SLOT + i * STRIDE
        b = rom[o:o + STRIDE]
        sl.append(dict(i=i, type=b[0], var=b[1], next=b[2],
                       lo=struct.unpack("<f", b[3:7])[0],
                       hi=struct.unpack("<f", b[7:11])[0],
                       c0=struct.unpack("<f", b[11:15])[0],
                       c1=struct.unpack("<f", b[15:19])[0],
                       c2=struct.unpack("<f", b[19:23])[0]))

    # --- var[13] = dien ap uV. Slot nao dung var 13? ---
    V = [(693500.0, "VMIN"), (850000.0, "850mV"), (1068750.0, "REL"), (1125000.0, "OV")]
    print("\n--- slot co var=13 (dien ap uV) -> y = ? ---")
    print(f"  {'slot':>5s} {'type':>4s} {'lo':>12s} {'hi':>12s} {'c0':>13s} "
          f"{'c1':>12s} {'c2':>12s}   y(693.5k) y(850k) y(1068.75k) y(1125k)")
    n13 = 0
    for s in sl:
        if s["var"] != 13:
            continue
        n13 += 1
        ys = [s["c0"] + s["c1"] * x + s["c2"] * x * x for x, _ in V]
        lo = "inf" if abs(s["lo"]) > 1e12 else f"{s['lo']:.0f}"
        hi = "inf" if abs(s["hi"]) > 1e12 else f"{s['hi']:.0f}"
        print(f"  {s['i']:>5d} {s['type']:>4d} {lo:>12s} {hi:>12s} "
              f"{s['c0']:>13.2f} {s['c1']:>12.6f} {s['c2']:>12.9f}   "
              + " ".join(f"{y:>10.1f}" for y in ys))
    print(f"  -> {n13} slot dung var=13")

    # --- slot var=7: x la TAN SO, y la dien ap/he so ---
    print("\n--- slot co var=7 (x = TAN SO MHz) -> y = ? (thu x=1890) ---")
    print(f"  {'slot':>5s} {'type':>4s} {'c0':>13s} {'c1':>12s} {'c2':>12s} "
          f"  y(1650) y(1890) y(2100) y(2335)")
    for s in sl:
        if s["var"] != 7 or (s["c1"] == 0 and s["c2"] == 0):
            continue
        ys = [s["c0"] + s["c1"] * x + s["c2"] * x * x for x in (1650, 1890, 2100, 2335)]
        print(f"  {s['i']:>5d} {s['type']:>4d} {s['c0']:>13.2f} {s['c1']:>12.6f} "
              f"{s['c2']:>12.9f}   " + " ".join(f"{y:>9.2f}" for y in ys))

    # --- slot nao cho y trong dai dien ap khi x la tan so? ---
    print("\n--- slot var=7 cho y = dien ap (600k..1300k uV) tai x=1890 ---")
    for s in sl:
        if s["var"] != 7:
            continue
        y = s["c0"] + s["c1"] * 1890 + s["c2"] * 1890 * 1890
        if 500000 < y < 1400000:
            print(f"  slot[{s['i']:>3d}] y(1890) = {y:>12.1f} uV = {y / 1000:.2f} mV")

    # --- slot nao cho y = MHz khi x la uV (var 13) ---
    print("\n--- slot var=13 cho y trong dai MHz (1000..2500) ---")
    for s in sl:
        if s["var"] != 13:
            continue
        y = s["c0"] + s["c1"] * 1068750.0 + s["c2"] * 1068750.0 ** 2
        if 1000 < y < 2500:
            print(f"  slot[{s['i']:>3d}] y(REL 1068.75mV) = {y:.2f} MHz")
        if 1000 < y < 2500:
            pass

    # --- type 0/2/3/4: dump tho ---
    print("\n" + "=" * 96)
    print("type 0 (compare) / 2 (minmax) / 3 / 4: 24 byte tho")
    print("=" * 96)
    for t in (0, 2, 3, 4):
        ids = [s["i"] for s in sl if s["type"] == t]
        print(f"\n--- type {t}: {len(ids)} slot -> {ids[:20]}")
        for i in ids[:6]:
            o = VFE_SLOT + i * STRIDE
            b = rom[o:o + STRIDE]
            u8 = list(b)
            u16 = [struct.unpack("<H", b[k:k + 2])[0] for k in range(0, 24, 2)]
            print(f"  slot[{i:>3d}] {b.hex(' ')}")
            print(f"           u8 ={u8}")
            print(f"           u16={u16}")


def main():
    rom = open(sys.argv[1], "rb").read()
    scan_u16(rom)
    scan_u32(rom)
    vfe_fixed(rom)


if __name__ == "__main__":
    main()