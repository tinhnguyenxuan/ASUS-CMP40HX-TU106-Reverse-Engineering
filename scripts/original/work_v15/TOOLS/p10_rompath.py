#!/usr/bin/env python3
"""Kiem tra duong option-ROM (CVE-2026-72487): rom sysfs, resource size, shadow header."""
import os, sys
D = "/sys/bus/pci/devices/0000:03:00.0"

print("== resource0 size ==")
with open(D + "/resource0", "rb") as f:
    f.seek(0, 2)
    print(f"  size={f.tell():,} B")

print("== rom sysfs ==")
try:
    st = os.stat(D + "/rom")
    print(f"  rom: size={st.st_size}, mode={oct(st.st_mode)}")
except FileNotFoundError:
    print("  rom: KHONG TON TAI (kernel chua expose option-ROM)")
except PermissionError as e:
    print(f"  rom: {e}")

print("== BAR0 shadow header @0x300000 ==")
try:
    with open(D + "/resource0", "rb") as f:
        f.seek(0x300000)
        h = f.read(32)
    print(f"  first 16: {h[:16].hex()}")
    print(f"  55AA: {h[0:2] == b'\\x55\\xaa'}")
    print(f"  sig: {h[:4]}")
    f.seek(0x300000 + 0x18)
    pcir = f.read(16)
    print(f"  PCIR @+0x18: {pcir[:4]} len=0x{int.from_bytes(pcir[2:4],'little'):04X}")
except PermissionError as e:
    print(f"  permission denied: {e}")
    print("  can thi can sudo")
