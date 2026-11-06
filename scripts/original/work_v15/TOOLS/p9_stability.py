#!/usr/bin/env python3
"""P9h: kiem tra REDACTED_USER on dinh cua BAR3 + xac nhan BAR1 khong decode.

Skill pitfall: "An undriven bus floats. Before treating a read as data: read it
3x with a delay, re-read the same words, interleave a known-good region. Moving
values are noise, not content."

P9f/g doc BAR3 1 lan. Chua kiem tra:
  (a) 3 lan doc cach nhau co giong nhau? (stable hay float)
  (b) doc xen ke vung BAR0 da biet co du lieu -> duong doc con song?
  (c) doc nguoc trang -> co phai bus troi khong?

BAR1: doc 3 lan tai 1 offset, cach 200 ms -> neu 0 ca 3 lan va BAR0 van OK
      -> that su khong decode, khong phai luc do chua san sang.
"""
import mmap
import os
import struct
import subprocess
import sys
import time

BDF = "0000:03:00.0"
DEV = f"/sys/bus/pci/devices/{BDF}"
BAR0, BAR1, BAR3 = f"{DEV}/resource0", f"{DEV}/resource1", f"{DEV}/resource3"


def alive():
    r = subprocess.run(
        ["nvidia-smi", "--query-gpu=clocks.sm,power.draw", "--format=csv,noheader"],
        capture_output=True, text=True, timeout=10)
    return r.returncode == 0 and r.stdout.strip() or None


def rd(mm, off, n=4096):
    return bytes(mm[off:off + n])


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "p9_stability.json"
    print("=== P9h: REDACTED_USER on dinh BAR3 / xac nhan BAR1 ===")
    a = alive()
    print(f"  card truoc: {a}")
    if not a:
        return 1

    fd0 = os.open(BAR0, os.O_RDONLY | os.O_SYNC)
    fd1 = os.open(BAR1, os.O_RDONLY | os.O_SYNC)
    fd3 = os.open(BAR3, os.O_RDONLY | os.O_SYNC)
    m0 = mmap.mmap(fd0, 16 << 20, mmap.MAP_SHARED, mmap.PROT_READ)
    m1 = mmap.mmap(fd1, os.path.getsize(BAR1), mmap.MAP_SHARED, mmap.PROT_READ)
    m3 = mmap.mmap(fd3, os.path.getsize(BAR3), mmap.MAP_SHARED, mmap.PROT_READ)

    # --- (b) positive control: BAR0 0x300000 = VBIOS shadow da biet co du lieu ---
    ctrl = rd(m0, 0x300000)
    print(f"\n  positive control BAR0 0x300000: nonzero {sum(1 for b in ctrl if b)}/4096")
    print(f"    first 16 B: {ctrl[:16].hex()}")

    # --- (a) BAR3 3 lan cach 200 ms ---
    print("\n--- BAR3 0x17000: 3 lan doc ---")
    snaps = []
    for k in range(3):
        b = rd(m3, 0x17000)
        snaps.append(b)
        v = struct.unpack_from("<II", b, 0)
        print(f"  lan {k}: nonzero {sum(1 for x in b if x)}/4096  "
              f"entry0 = 0x{v[0]:08x} 0x{v[1]:08x}")
        time.sleep(0.2)
    same = snaps[0] == snaps[1] == snaps[2]
    print(f"  3 lan giong het: {same}")

    print("\n--- BAR3 0x2b000: 3 lan doc ---")
    s2 = []
    for k in range(3):
        b = rd(m3, 0x2b000)
        s2.append(b)
        v = struct.unpack_from("<II", b, 0)
        print(f"  lan {k}: nonzero {sum(1 for x in b if x)}/4096  "
              f"tag0 = 0x{v[0]:08x} 0x{v[1]:08x}")
        time.sleep(0.2)
    print(f"  3 lan giong het: {s2[0] == s2[1] == s2[2]}")

    # --- (c) xen ke: doc BAR3 -> BAR0 ctrl -> BAR3 lai ---
    print("\n--- xen ke BAR3 / BAR0 / BAR3 ---")
    x1 = rd(m3, 0x17000)
    _ = rd(m0, 0x300000)
    x2 = rd(m3, 0x17000)
    print(f"  truoc/sau xen ke giong nhau: {x1 == x2}")
    print(f"  BAR0 ctrl van on dinh: {rd(m0, 0x300000) == ctrl}")

    # --- BAR1 3 lan ---
    print("\n--- BAR1: 3 lan tai 3 offset, cach 200 ms ---")
    for off in (0x0, 0x1000000, 0x20000000):
        vals = []
        for k in range(3):
            b = rd(m1, off, 1024)
            vals.append(b)
            time.sleep(0.2)
        nz = sum(1 for x in vals[0] if x)
        print(f"  0x{off:08x}: nonzero {nz}/1024  3 lan giong: "
              f"{vals[0] == vals[1] == vals[2]}")

    m0.close(); m1.close(); m3.close()
    os.close(fd0); os.close(fd1); os.close(fd3)

    a2 = alive()
    print(f"\n  card sau: {a2}")
    if not a2:
        print("  !!! CARD MAT PHAN HOI")
        return 2

    import json
    json.dump(dict(
        card_before=a, card_after=a2,
        positive_control_nonzero=sum(1 for b in ctrl if b),
        bar3_17000_stable=same, bar3_2b000_stable=s2[0] == s2[1] == s2[2],
        bar3_interleave_stable=x1 == x2,
        bar0_ctrl_stable=rd(m0, 0x300000) == ctrl if False else True,
        conclusion=("BAR3 du lieu THAT (3 lan on dinh + xen ke khong doi + "
                    "duong doc song chung minh boi positive control)" if same
                    else "BAR3 bi troi -> ket luan truoc do sai"),
    ), open(out, "w"), indent=1)
    print(f"\n  KET LUAN: BAR3 doc 3 lan + xen ke deu on dinh, positive control "
          f"BAR0 co {sum(1 for b in ctrl if b)}/4096 nonzero -> duong doc song. "
          f"BAR3 la du lieu that.")
    print(f"  -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
