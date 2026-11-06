#!/usr/bin/env python3
"""VBIOS parser CMP 40HX — container, BIT, PERF, VFE. Xuat JSON.

Dung: python3 vbios_parser.py CMP40HX_ORIGINAL_1MB.bin
"""
import json
import struct
import sys

ROM_IMG = 0x28600          # legacy x86 image goc
LEGACY_SZ = 0xF400
EFI_SZ = 0x11000
BIT_OFF = 0x287B0
PERF_OFF = 0x288D4


def ptr(p):
    """Cong thuc con truyen thong VBIOS Turing."""
    a = ROM_IMG + p
    return a + EFI_SZ if p >= LEGACY_SZ else a


def table(rom, at):
    """Header bang chuan: ver, hdr_size, entry_size, count."""
    if at + 4 > len(rom):
        return None
    ver, hdr, esz, cnt = rom[at], rom[at + 1], rom[at + 2], rom[at + 3]
    size = hdr + esz * cnt
    if esz == 0 or size > 0x20000 or at + size > len(rom):
        return None
    return dict(off=at, ver=ver, hdr=hdr, esz=esz, cnt=cnt, size=size)


def bitmap(rom):
    """BIT table: 17 token."""
    hdr, tsz, cnt = rom[BIT_OFF + 8], rom[BIT_OFF + 9], rom[BIT_OFF + 10]
    out = {}
    for i in range(cnt):
        o = BIT_OFF + hdr + i * tsz
        tok = rom[o]
        p = struct.unpack("<H", rom[o + 4:o + 6])[0]
        out[f"0x{tok:02x}"] = dict(file_off=ptr(p), ptr=p)
    return dict(off=BIT_OFF, tokens=cnt, map=out)


def perf_tables(rom):
    out = []
    for i in range(56):
        p = struct.unpack("<I", rom[PERF_OFF + i * 4:PERF_OFF + i * 4 + 4])[0]
        if not p:
            continue
        t = table(rom, ptr(p))
        if t:
            t["idx"] = i
            out.append(t)
    return out


def vfe(rom):
    """VFE: base 0x56699, slot 24 B, 150 slot. VFE_VAR @0x564A5 stride 25."""
    print_slots = []
    for i in range(150):
        o = 0x56699 + i * 24
        b = rom[o:o + 24]
        print_slots.append(dict(
            i=i, off=o, type=b[0], var_idx=b[1], next=b[2],
            lo=struct.unpack("<f", b[3:7])[0],
            hi=struct.unpack("<f", b[7:11])[0],
            c0=struct.unpack("<f", b[11:15])[0],
            c1=struct.unpack("<f", b[15:19])[0],
            c2=struct.unpack("<f", b[19:23])[0],
            flags=b[23]))
    vars_ = []
    for i in range(20):
        o = 0x564A5 + i * 25
        b = rom[o:o + 25]
        vars_.append(dict(i=i, off=o, type=b[0],
                          lo=struct.unpack("<f", b[1:5])[0],
                          hi=struct.unpack("<f", b[5:9])[0]))
    return dict(slot_base=0x56699, slot_stride=24, slot_count=150,
                var_base=0x564A5, var_stride=25, var_count=20,
                slots=print_slots, vars=vars_)


def images(rom):
    """9 image trong 2 bank + container."""
    spec = [("bank1", 0x000000, 0x0A1600),
            ("legacy1", 0x028600, 0x037A00), ("EFI1", 0x037A00, 0x048A00),
            ("NPDS_E0_1", 0x048A00, 0x054000), ("NPDS_E0_2", 0x054000, 0x076800),
            ("NPDS_70_digest", 0x076800, 0x078400),
            ("bank2", 0x0A1600, 0x100000),
            ("legacy2", 0x0A1600, 0x0B0A00), ("EFI2", 0x0B0A00, 0x0C1A00),
            ("NPDS_E0_3", 0x0C1A00, 0x0CD000), ("NPDS_E0_4", 0x0CD000, 0x0EF800),
            ("VN_container", 0x0EF800, 0x0F9E00), ("NPDE", 0x0F9E00, 0x0FA500)]
    out = []
    for nm, s, e in spec:
        if e > len(rom):
            continue
        body = rom[s:e]
        out.append(dict(name=nm, start=s, end=e, size=e - s,
                        sum_mod256=sum(body) & 0xFF,
                        checksum_ok=(sum(body) & 0xFF) == 0))
    return out


def main():
    path = sys.argv[1]
    rom = open(path, "rb").read()
    assert len(rom) == 1048576, f"ROM phai 1 MiB, thay {len(rom)}"

    m = dict(
        file=path, size=len(rom),
        signature=rom[0:2].hex(),
        pcir_ver=struct.unpack("<H", rom[0x18:0x1A])[0],
        vendor=rom[0x24:0x26][::-1].hex(),
        device=rom[0x26:0x28][::-1].hex(),
        images=images(rom),
        bit=bitmap(rom),
        perf=perf_tables(rom),
        vfe=vfe(rom),
    )
    json.dump(m, open("outputs/vbios_map.json", "w"), indent=1)

    print(f"=== {path} ({len(rom):,} B) ===")
    print(f"  sig {m['signature']}  PCIR 0x{m['pcir_ver']:04x}  "
          f"{m['vendor']}:{m['device']}")
    print("\n--- image + checksum (sum%256) ---")
    for im in m["images"]:
        flag = "OK" if im["checksum_ok"] else f"0x{im['sum_mod256']:02x}"
        print(f"  {im['name']:<16s} 0x{im['start']:06x}..0x{im['end']:06x} "
              f"{im['size']:>7d} B  {flag}")
    print(f"\n  BIT {m['bit']['ffset'] if False else m['bit']['off']:#x}  "
          f"{m['bit']['tokens']} token")
    print(f"  PERF {len(m['perf'])} bang")
    print(f"  VFE {m['vfe']['slot_count']} slot x {m['vfe']['slot_stride']} B, "
          f"{m['vfe']['var_count']} var x {m['vfe']['var_stride']} B")


if __name__ == "__main__":
    main()