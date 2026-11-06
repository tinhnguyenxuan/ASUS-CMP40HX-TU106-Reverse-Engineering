#!/usr/bin/env python3
"""XREF dung chuan RISC-V (auipc+addi) + dump code quanh ref.

Dung: python3 gsp_xref.py gsp_tu10x.bin
"""
import struct
import sys

INNER = 0x40
LOAD = 0x4000000
TEXT_LO, TEXT_HI = 0x588040, 0x1588040   # .section_task_rm_elf_text_instance

KEYS = [
    "RMHwSpeedoOverride", "RMHwSpeedo1Override", "RMHwSpeedo2Override",
    "RMHwSpeedoCheckIgnore", "RmPmgrIddqNvvddOverride", "RmPmgrIddqOverride",
    "RmPmgrIddq1Override", "RmPmgrIddqMsvddOverride", "RmPmgrIddqCheckIgnore",
    "RmPmgrSpeedoCoefficient", "RmPmgrSpeedoOffset", "RMClkVfOverride",
    "RmClockForceUprocVfeVfGen", "RmSramVminCheckIgnore", "RmVoltThresholdCtrlCtrl",
    "RMEnableOverclockingAllPstates", "RMForceLockedClocksMode",
    "RMSec2UseDebugFuseOnlyBinary", "RMNoECCFuseCheck", "RmDisableFspFuseErrorCheck",
    "RmPmgrIsenseVcmOffsetOverride", "RmPmgrIsenseDiffGainOverride",
]


def key_vas(d):
    out = {}
    for k in KEYS:
        i = d.find(k.encode())
        if i < 0:
            continue
        out[k] = (i, LOAD + (i - INNER))
    return out


def scan_auipc(d, vas):
    """auipc rd,imm20 ; addi rd,rd,imm12  -> target = pc + imm20<<12 + imm12"""
    want = {}
    for k, (fo, va) in vas.items():
        want.setdefault(va, []).append(k)
    hits = {k: [] for k in vas}
    for o in range(TEXT_LO, min(TEXT_HI, len(d)) - 8, 4):
        w1 = struct.unpack("<I", d[o:o + 4])[0]
        if (w1 & 0x7F) != 0x17:              # AUIPC
            continue
        rd = (w1 >> 7) & 0x1F
        imm20 = w1 >> 12
        if imm20 & 0x80000:
            imm20 -= 0x100000
        w2 = struct.unpack("<I", d[o + 4:o + 8])[0]
        if (w2 & 0x7F) != 0x13:              # ADDI
            continue
        if ((w2 >> 7) & 0x1F) != rd or ((w2 >> 15) & 0x1F) != rd:
            continue
        imm12 = (w2 >> 20) & 0xFFF
        if imm12 & 0x800:
            imm12 -= 0x1000
        pc = LOAD + (o - INNER)
        tgt = pc + (imm20 << 12) + imm12
        for k in want.get(tgt, []):
            hits[k].append((o, pc, "auipc+addi"))
    return hits


def dump_code(d, off, n=48):
    for k in range(off - 16, off + n, 4):
        if k < 0 or k + 4 > len(d):
            continue
        w = struct.unpack("<I", d[k:k + 4])[0]
        mark = " <<<" if k == off else ""
        print(f"    {k:08x} (0x{LOAD + k - INNER:08x})  {w:08x}{mark}")


def main():
    d = open(sys.argv[1], "rb").read()
    vas = key_vas(d)
    print("=== vi tri chuoi key ===")
    for k, (fo, va) in vas.items():
        print(f"  {k:<34s} file 0x{fo:08x}  vaddr 0x{va:08x}")

    print("\n=== XREF auipc+addi (chuan RISC-V) ===")
    hits = scan_auipc(d, vas)
    found = 0
    for k in vas:
        h = hits[k]
        if h:
            found += 1
            print(f"  {k}:")
            for o, pc, kind in h[:3]:
                print(f"    REF @file 0x{o:08x}  vaddr 0x{pc:08x}  ({kind})")
        else:
            print(f"  {k}: KHONG co xref truc tiep")
    print(f"\n  -> {found}/{len(vas)} key co XREF")

    # dump code quanh cac ref cua key fuse/pvs quan trong
    print("\n=== code quanh XREF (cac key PVS/fuse) ===")
    for k in ("RMHwSpeedoCheckIgnore", "RmPmgrIddqCheckIgnore",
              "RMEnableOverclockingAllPstates", "RMSec2UseDebugFuseOnlyBinary"):
        for o, pc, kind in hits.get(k, [])[:1]:
            print(f"\n  --- {k} @0x{pc:08x} ---")
            dump_code(d, o)


if __name__ == "__main__":
    main()