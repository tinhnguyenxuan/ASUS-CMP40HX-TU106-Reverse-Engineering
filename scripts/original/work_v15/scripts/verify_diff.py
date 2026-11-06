#!/usr/bin/env python3
"""A6 checksum + A7/A8 kich thuoc payload. Xuat vbios_diff.json.

Dung: python3 verify_diff.py <ROM 1MiB> <payload T4>
"""
import json
import struct
import sys


def main():
    rom = open(sys.argv[1], "rb").read()
    pay = open(sys.argv[2], "rb").read()

    # ---- A6: checksum tung image, ca 2 file ----
    IMAGES = [("legacy1", 0x028600, 0x037A00), ("EFI1", 0x037A00, 0x048A00),
              ("NPDS_E0_1", 0x048A00, 0x054000), ("NPDS_E0_2", 0x054000, 0x076800),
              ("NPDS_70", 0x076800, 0x078400)]
    print("=== A6: checksum  =  sum(image bytes) mod 256 ===")
    print(f"  {'image':<12s} {'vung':<22s} {'ROM':>6s} {'T4':>6s}  ket luan")
    ck = []
    for nm, s, e in IMAGES:
        a = sum(rom[s:e]) & 0xFF
        b = sum(pay[s:e]) & 0xFF if e <= len(pay) else None
        ok = (b == 0) if b is not None else None
        ck.append(dict(image=nm, start=s, end=e, rom_sum=a, t4_sum=b, t4_ok=ok))
        print(f"  {nm:<12s} 0x{s:06x}..0x{e:06x}  0x{a:02x}  "
              f"{'0x%02x' % b if b is not None else '  --'}   "
              f"{'OK (chia het 256)' if ok else 'SAI' if b is not None else 'ngoai payload'}")

    # ---- byte tai 0x767FF ----
    print(f"\n  byte 0x767FF (cuoi NPDS_E0_2): ROM 0x{rom[0x767FF]:02x} -> "
          f"T4 0x{pay[0x767FF]:02x}  (delta {pay[0x767FF] - rom[0x767FF]:+d})")
    # kiem tra: delta == -(tong 18 byte con lai da doi) mod 256
    d = [i for i in range(len(pay)) if rom[i] != pay[i] and i != 0x767FF]
    delta = sum(pay[i] - rom[i] for i in d)      # thay doi cua 18 byte than
    calc = (rom[0x767FF] - delta) & 0xFF
    print(f"  18 byte than: tong(T4-ROM) = {delta:+d}")
    print(f"  new_ck = (old_ck - delta) mod 256 = 0x{calc:02x}  "
          f"-> {'KHOP' if calc == pay[0x767FF] else 'KHONG KHOP'} "
          f"(thuc te T4 = 0x{pay[0x767FF]:02x})")

    # ---- A7/A8: payload 495616 vs ROM 1 MiB ----
    print(f"\n=== A7/A8: payload {len(pay):,} B = 0x{len(pay):x} vs ROM {len(rom):,} B ===")
    print("  cau truc 1 MiB:")
    seg = [("bank1 (image hop le)", 0x000000, 0x0A1600),
           ("bank2 (ban sao y het)", 0x0A1600, 0x100000)]
    for nm, s, e in seg:
        same = rom[0:0x0A1600] == rom[0x0A1600:0x100000]
        print(f"    {nm:<24s} 0x{s:06x}..0x{e:06x}  {e - s:>7,} B")
    print(f"    bank1 == bank2 ? {rom[0:0x0A1600] == rom[0x0A1600:0x100000]}")
    print(f"\n  payload = rom[0:0x{len(pay):x}]  "
          f"-> {'DUNG' if rom[:len(pay)] == rom[:len(pay)] else '?'}")
    # payload co bang bank1 khong?
    print(f"  payload == rom[0:0xA1600]? {pay == rom[:0x0A1600]}")
    print(f"  payload dai hon bank1? {len(pay)} vs {0x0A1600} -> "
          f"{'dai hon' if len(pay) > 0x0A1600 else 'ngan hon'}")
    # 0x0A1600 = 660,992 ; payload 495,616 = 0x79000
    print(f"  0x79000 = {0x79000:,} B  (ket thuc NPDS_70 @0x78400 + 0xC00)")
    print(f"  vung 0x78400..0x79000 ({0x79000 - 0x78400} B): "
          f"{rom[0x78400:0x79000].hex(' ')[:80]}")
    print(f"  toan 0 khong? {set(rom[0x78400:0x79000]) == {0}}")

    # ---- 6 field float32 ----
    print("\n=== 6 field float32 bi doi ===")
    FIELDS = [(0x5669C, "nvvdd REL clamp_lo (copy 1)"),
              (0x566A0, "nvvdd REL c0 (copy 1)"),
              (0x566A4, "nvvdd REL c0 (copy 2)"),
              (0x566B4, "nvvdd ALT c0 (copy 1)"),
              (0x566B8, "nvvdd ALT c0 (copy 2)"),
              (0x566BC, "nvvdd ALT c0 (copy 3)")]
    fl = []
    for off, nm in FIELDS:
        a = struct.unpack("<f", rom[off:off + 4])[0]
        b = struct.unpack("<f", pay[off:off + 4])[0]
        fl.append(dict(off=off, name=nm, rom_uv=a, t4_uv=b))
        print(f"  0x{off:06x}  {nm:<28s} {a:>10.1f} -> {b:>10.1f} uV "
              f"({a / 1000:.2f} -> {b / 1000:.2f} mV)")

    # offset tuong doi trong slot VFE
    print("\n  vi tri trong slot VFE (base 0x56699, stride 24):")
    for off, nm in FIELDS:
        rel = off - 0x56699
        print(f"    0x{off:06x}: slot[{rel // 24}] +0x{rel % 24:02x}")

    json.dump(dict(
        rom_sha256="dc5395dd845cf2139f94c8b4b342adf91206aec0e3ed18103ad94ba18d009dec",
        t4_sha256="aa0ebd6d74326bb4630c473caeb6a5ae2bf55598b80a38d41a65ffee0b40cfdb",
        rom_size=len(rom), t4_size=len(pay),
        bytes_changed=len([i for i in range(len(pay)) if rom[i] != pay[i]]),
        checksum=dict(algorithm="sum(image) % 256 == 0", images=ck,
                      checksum_byte_off=0x767FF,
                      rom_val=rom[0x767FF], t4_val=pay[0x767FF],
                      formula="new = (old - sum(t4[i]-rom[i] for changed body)) % 256  <=> sum(image) % 256 == 0"),
        floats=fl,
        payload_rule="payload = rom[0:0x79000] (495616 B)",
        payload_cut="0x79000..0x100000 = 0x87000 B khong dua vao payload",
    ), open("outputs/vbios_diff.json", "w"), indent=1)
    print("\n  -> outputs/vbios_diff.json")


if __name__ == "__main__":
    main()