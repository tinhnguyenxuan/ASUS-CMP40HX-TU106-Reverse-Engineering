#!/usr/bin/env python3
"""B: GSP-RM strings + xref + call graph. Xuat gsp_strings.json / gsp_xrefs.json.

Dung: python3 gsp_scan.py ../gsp_tu10x.bin
"""
import json
import struct
import sys

INNER = 0x40
TARGETS = [
    "RMClkVfOverride", "RmAtsVolOverride", "RmClkControllersOverride",
    "OVERVOLTAGE_LOGIC", "OVERVOLTAGE_NVVDD_0", "OVERVOLTAGE_NVVDD_1",
    "PERFORMANCE_CAP0", "PERF_CF_CONTROLLER_GPC_MAX",
    "RMHwSpeedoOverride", "RMHwSpeedoCheckIgnore",
    "RmPmgrIddqNvvddOverride", "RmPmgrIddqCheckIgnore",
    "RmPmgrSpeedoCoefficient", "RmPmgrSpeedoOffset",
    "RmClockForceUprocVfeVfGen", "RmSramVminCheckIgnore",
    "RmVoltThresholdCtrlCtrl", "RMEnableOverclockingAllPstates",
    "RMForceLockedClocksMode", "RMSec2UseDebugFuseOnlyBinary",
]
# chu de power/clock de xay call graph
TOPICS = ("CLK", "VOLT", "PWR", "PERF", "THERM", "VF", "SPEEDO", "IDDQ",
          "OVERCLOCK", "PSTATE", "BOOST", "FREQ", "OCP", "TGP")


def elf(d):
    e = d[INNER:INNER + 64]
    phoff = struct.unpack("<Q", e[32:40])[0]
    shoff = struct.unpack("<Q", e[40:48])[0]
    phsz = struct.unpack("<H", e[54:56])[0]
    phnum = struct.unpack("<H", e[56:58])[0]
    shsz = struct.unpack("<H", e[58:60])[0]
    shnum = struct.unpack("<H", e[60:62])[0]
    shstr = struct.unpack("<H", e[62:64])[0]

    phs = []
    for i in range(phnum):
        o = INNER + phoff + i * phsz
        if struct.unpack("<I", d[o:o + 4])[0] != 1:
            continue
        off = struct.unpack("<Q", d[o + 8:o + 16])[0]
        va = struct.unpack("<Q", d[o + 16:o + 24])[0]
        fsz = struct.unpack("<Q", d[o + 32:o + 40])[0]
        if fsz:
            phs.append((off, va, fsz))

    so = INNER + shoff + shstr * shsz
    stoff = struct.unpack("<Q", d[so + 24:so + 32])[0]
    stsz = struct.unpack("<Q", d[so + 32:so + 40])[0]
    strs = d[INNER + stoff:INNER + stoff + stsz]
    shs = []
    for i in range(shnum):
        o = INNER + shoff + i * shsz
        nm = struct.unpack("<I", d[o:o + 4])[0]
        typ = struct.unpack("<I", d[o + 4:o + 8])[0]
        addr = struct.unpack("<Q", d[o + 16:o + 24])[0]
        off = struct.unpack("<Q", d[o + 24:o + 32])[0]
        size = struct.unpack("<Q", d[o + 32:o + 40])[0]
        z = strs.find(b"\x00", nm)
        shs.append(dict(name=strs[nm:z].decode("latin1"), type=typ,
                        vaddr=addr, file_off=INNER + off, size=size))
    return phs, shs


def to_va(phs, fo):
    for off, va, sz in phs:
        if off <= fo < off + sz:
            return va + (fo - off)
    return None


def scan(d, phs, shs):
    # ---- B1: container ----
    outer = dict(
        size=len(d), magic=d[0:4].hex(),
        elf_class=d[4], machine=struct.unpack("<H", d[18:20])[0],
        sections=len(shs),
        note="lop ngoai REL; lop trong @0x40 la ELF EXEC RISC-V")
    container = dict(outer=outer, inner_sections=shs,
                     ph_load=[dict(file_off=o, vaddr=v, size=s) for o, v, s in phs])
    print("=== B1: firmware container ===")
    print(f"  file {len(d):,} B, {len(shs)} section, {len(phs)} PT_LOAD")
    for s in shs:
        if s["size"] > 0x1000:
            print(f"    {s['name']:<46s} vaddr 0x{s['vaddr']:08x} "
                  f"off 0x{s['file_off']:08x} {s['size']:>10,} B")

    # ---- B3: strings ----
    print("\n=== B3: truy vet chuoi ===")
    strings = {}
    for t in TARGETS:
        i = d.find(t.encode())
        if i < 0:
            strings[t] = None
            print(f"  {t:<34s} KHONG CO")
            continue
        va = to_va(phs, i)
        strings[t] = dict(file_off=i, vaddr=va)
        print(f"  {t:<34s} file 0x{i:08x}  vaddr 0x{va:08x}"
              if va else f"  {t:<34s} file 0x{i:08x}  ngoai PT_LOAD")

    # ---- B3b: dem string theo chu de ----
    print("\n=== B3b: mat do string theo chu de (power/clock) ===")
    import re
    allstr = re.findall(rb"[ -~]{5,80}", d)
    dec = [s.decode("latin1") for s in allstr]
    density = {}
    for t in TOPICS:
        n = sum(1 for s in dec if t in s.upper())
        if n:
            density[t] = n
    for t, n in sorted(density.items(), key=lambda x: -x[1]):
        print(f"  {t:<12s} {n:>6d} string")

    # ---- B4: xref that (step 2, cua so, ca 3 kieu) ----
    print("\n=== B4: XREF (step=2 RVC, cua so o+2..o+24, u32/u64 ptr) ===")
    xrefs = {}
    for t, pos in strings.items():
        if not pos:
            continue
        va = pos["vaddr"]
        p32, p64 = struct.pack("<I", va), struct.pack("<Q", va)
        c32 = d.count(p32)
        c64 = d.count(p64)
        # auipc+addi/ld, step 2
        refs = []
        for s in shs:
            if "text" not in s["name"] or s["size"] < 64:
                continue
            lo, hi = s["file_off"], min(s["file_off"] + s["size"], len(d))
            for o in range(lo, hi - 4, 2):
                w1 = struct.unpack("<I", d[o:o + 4])[0]
                if (w1 & 0x7F) != 0x17:
                    continue
                rd = (w1 >> 7) & 0x1F
                imm20 = w1 >> 12
                if imm20 & 0x80000:
                    imm20 -= 0x100000
                pc = to_va(phs, o)
                if pc is None:
                    continue
                base = pc + (imm20 << 12)
                for k in range(1, 13):
                    o2 = o + k * 2
                    if o2 + 4 > len(d):
                        break
                    w2 = struct.unpack("<I", d[o2:o2 + 4])[0]
                    if (w2 & 3) != 3:
                        continue
                    if (w2 & 0x7F) not in (0x13, 0x03) or ((w2 >> 15) & 0x1F) != rd:
                        continue
                    imm = (w2 >> 20) & 0xFFF
                    if imm & 0x800:
                        imm -= 0x1000
                    if base + imm == va:
                        refs.append(dict(auipc_off=o, pc=pc, dist=k))
                        break
        xrefs[t] = dict(vaddr=va, u32_ptr=c32, u64_ptr=c64, code_refs=refs)
        print(f"  {t:<34s} u32ptr={c32} u64ptr={c64} code_ref={len(refs)}")

    return container, strings, xrefs, density


def main():
    d = open(sys.argv[1], "rb").read()
    phs, shs = elf(d)
    container, strings, xrefs, density = scan(d, phs, shs)
    json.dump(dict(container=container, target_strings=strings,
                   topic_density=density),
              open("outputs/gsp_strings.json", "w"), indent=1)
    json.dump(xrefs, open("outputs/gsp_xrefs.json", "w"), indent=1)
    n = sum(1 for v in xrefs.values() if v["code_refs"] or v["u32_ptr"] or v["u64_ptr"])
    print(f"\n  -> {n}/{len(xrefs)} key co tham chieu nao do")
    print("  -> outputs/gsp_strings.json, outputs/gsp_xrefs.json")


if __name__ == "__main__":
    main()