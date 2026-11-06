#!/usr/bin/env python3
"""P8: doc WPR / PLM / ACR register tu BAR0. CHI DOC.

Lay gia tri tu MMIO de doi chieu voi dmesg da co.
WPR registers (TU106):
  0x1FA800 WPR0_LO/HI
  0x1FA810 WPR1_LO/HI
  0x1FA820 WPR2_LO/HI
  dmesg bao: WPR2_lo = 0x1FFFFE00

Dung: sudo python3 p8_wpr.py out.json
"""
import json
import mmap
import os
import struct
import sys

DEV = "/sys/bus/pci/devices/0000:03:00.0/resource0"

# (ten, offset)
REG = [
    ("NV_PGC6_AON_SECURE_SCRATCH_GROUP_00", 0x1180F8),
    ("WPR0_LO", 0x1FA800), ("WPR0_HI", 0x1FA804),
    ("WPR1_LO", 0x1FA810), ("WPR1_HI", 0x1FA814),
    ("WPR2_LO", 0x1FA820), ("WPR2_HI", 0x1FA824),
    ("WPR2_LO_ALT", 0x1FA828),
    ("WPR2_HI_ALT", 0x1FA82C),
    ("WPR_CFG", 0x1FA830),
    ("PLM_FECS", 0x1FA840), ("PLM_RESET", 0x1FA844),
    ("ACR_CMD", 0x1FA850), ("ACR_STATUS", 0x1FA854),
    ("SEC2_STATUS", 0x1FA860),
    # PMC/PGC6 da biet co du lieu
    ("NV_PMC_BOOT_0", 0x000000),
    ("NV_PMC_ENABLE", 0x000200),
]


def is_poison(v):
    return (v & 0xFFFF0000) == 0xBADF0000


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "p8_wpr.json"
    fd = os.open(DEV, os.O_RDONLY | os.O_SYNC)
    mm = mmap.mmap(fd, 16 << 20, mmap.MAP_SHARED, mmap.PROT_READ)

    res = []
    print("=== P8: WPR / PLM / ACR register (read-only) ===")
    print(f"  {'register':<40s} {'off':>9s}  {'gia tri':>12s}  trang thai")
    for nm, off in REG:
        v = struct.unpack_from("<I", mm, off)[0]
        # doc lai 1 lan
        v2 = struct.unpack_from("<I", mm, off)[0]
        st = ("poison" if is_poison(v) else
              "zero" if v == 0 else
              "DATA" if v == v2 else "UNSTABLE")
        res.append(dict(name=nm, off=f"0x{off:06x}", value=f"0x{v:08x}",
                        value_int=v, second_read=f"0x{v2:08x}", state=st))
        print(f"  {nm:<40s} 0x{off:06x}  0x{v:08x}  {st}")

    mm.close()
    os.close(fd)

    # --- doi chieu voi dmesg ---
    print("\n=== DOI CHIEU voi dmesg ===")
    dm = json.load(open("SECURITY/security_registers.json"))
    wpr = dm["dmesg_wpr"]
    reg = {r["name"]: r["value_int"] for r in res}
    checks = [
        ("WPR2_LO", 0x1FA820, 0x1FFFFE00, "wpr2_lo=0x1ffffe00"),
        ("WPR2_HI", 0x1FA824, None, None),
        ("WPR2_LO_ALT", 0x1FA828, 0x01F7E000, "WPR=01ffee00:01ffe000"),
    ]
    for nm, off, exp, tag in checks:
        got = reg.get(nm)
        line = f"  {nm:<12s} doc=0x{got:08x}"
        if exp is not None:
            line += f"  dmesg=0x{exp:08x}  {'*** KHOP ***' if got == exp else 'KHAC'}"
        if tag:
            line += f"   ({tag})"
        print(line)

    # gia tri chinh tu dmesg (parse thu cong)
    print("\n=== GIA TRI THUC TU DMESG (nguon: boot log) ===")
    facts = {
        "WPR2_lo": 0x1FFFFE00,
        "WPR_at_boot": "01FFEE00:01FFE000",
        "FECS_PLM": 0xFFFFFF8F,
        "RESET_PLM": 0x000000FF,
        "SS0": 0x88888888,
        "SS1": 0x00000008,
        "ACR_TOKEN": 0xC2,
        "fresh_wpr_phys_1": 0x8EFDE000,
        "fresh_wpr_sig": 0xFFE40000,
        "fresh_wpr_size_1": 0xFA00,
        "fresh_wpr_phys_2": 0x8EFDD000,
        "fresh_wpr_size_2": 0x1000,
        "advertised": 0x1000,
        "backing": 0xFA00,
        "mailbox": 0x1CDD,
        "mutex_release": 0x0D27,
        "stack": 0xFF14,
        "stage": 0xC100,
        "tail": 0x3988,
        "ls_version": 0x344,
        "ls_id": 1,
        "header": 0x00020001,
        "gadgets": [0x0CC8, 0x0CBD, 0x0C1D, 0x1D62, 0x1F89, 0x5FF, 0x64EC],
        "tracepc": 0x7D11,
        "CPUCTL": 0x00000010,
        "idx_phase_boundary": 96,
        "conf_compute_protected_total": "0 MiB",
        "dma_mask_bits": 47,
        "iommu_group": 31,
        "bar1_size": "64 GiB",
        "rebar_bar0": "16 MiB",
        "rebar_bar1": "64 GiB",
        "rebar_bar3": "32 MiB",
    }
    for k, v in facts.items():
        if isinstance(v, list):
            print(f"  {k:<34s} {[hex(x) for x in v]}")
        elif isinstance(v, int):
            print(f"  {k:<34s} 0x{v:08x} ({v:,})")
        else:
            print(f"  {k:<34s} {v}")

    json.dump(dict(registers=res, dmesg_facts=facts,
                   note="gia tri dmesg la BO CHUNG KHOI DONG THUC; "
                        "register MMIO doc duoc o tren la bo chung RUNTIME"),
              open(out, "w"), indent=1)
    print(f"\n  -> {out}")


if __name__ == "__main__":
    main()
