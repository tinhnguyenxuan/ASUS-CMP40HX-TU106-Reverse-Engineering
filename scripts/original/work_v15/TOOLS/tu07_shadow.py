#!/usr/bin/env python3
"""TU-07: so VBIOS shadow (BAR0 0x300000) voi ROM file de tim offset that.

Shadow bat dau 55 AA, PCIR @0x170 -> day la VBIOS legacy header that.
ROM file bat dau 'NVGIf' -> ROM file la CONTAINER, image that o offset khac.

Kiem tra: shadow co bang rom[0x28600:] khong?
"""
import hashlib
import json
import sys

s = open("RAW_DATA/vbios_shadow.bin", "rb").read()
r = open("outputs/CMP40HX_ORIGINAL_1MB.bin", "rb").read()

print(f"shadow {len(s):,} B  sha256 {hashlib.sha256(s).hexdigest()[:32]}...")
print(f"rom    {len(r):,} B  sha256 {hashlib.sha256(r).hexdigest()[:32]}...")
print()

# tim 0x55AA trong rom
print("=== tim signature 55AA trong ROM ===")
for off in range(0, min(len(r) - 2, 0x40000)):
    if r[off] == 0x55 and r[off + 1] == 0xAA:
        print(f"  rom[0x{off:06x}] = 55 AA")
        break

# so sanh shadow voi cac ung vien offset trong rom
print("\n=== so shadow[0:N] voi rom[cand:...] ===")
best = []
for cand in (0x0, 0x10000, 0x20000, 0x28600, 0x30000, 0x40000):
    n = min(0x1000, len(r) - cand)
    if n <= 0:
        continue
    same = sum(1 for i in range(n) if s[i] == r[cand + i])
    best.append((same / n, cand, n))
    print(f"  rom[0x{cand:06x}]: {same}/{n} = {100 * same / n:.1f}% giong")

best.sort(reverse=True)
ratio, cand, n = best[0]
print(f"\n  tot nhat: rom[0x{cand:06x}] ({100*ratio:.1f}%)")

# --- neu tim duoc offset, so toan bo ---
if ratio > 0.9:
    print(f"\n=== so toan bo shadow voi rom[0x{cand:06x}] ===")
    m = min(len(s), len(r) - cand)
    diff = [i for i in range(m) if s[i] != r[cand + i]]
    print(f"  {len(diff)} byte khac / {m:,} B")
    # gom cum
    if diff:
        runs = []
        cur = [diff[0]]
        for a, b in zip(diff, diff[1:]):
            if b - a < 256:
                cur.append(b)
            else:
                runs.append((cur[0], cur[-1]))
                cur = [b]
        runs.append((cur[0], cur[-1]))
        print(f"  {len(runs)} cum khac:")
        for st, en in runs[:15]:
            print(f"    +0x{st:06x}..0x{en:06x} ({en-st+1} B)")
            print(f"      shadow: {s[st:min(en+1, st+32)].hex(' ')}")
            print(f"      rom   : {r[cand+st:cand+min(en+1, st+32)].hex(' ')}")

# --- cau truc header legacy trong shadow ---
print("\n=== header legacy cua SHADOW ===")
print(f"  +0x00 sig     : {s[0:2].hex(' ')}")
print(f"  +0x18 pointer : 0x{s[0x18] | (s[0x19] << 8):04x}  (PCIR offset)")
print(f"  +0x1A PnP     : 0x{s[0x1A] | (s[0x1B] << 8):04x}")
i = s.find(b"PCIR")
print(f"  PCIR @0x{i:x}: {s[i:i+24].hex(' ')}")
if i >= 0:
    j = i + 4
    print(f"    vendor  = 0x{s[j] | (s[j+1] << 8):04x}")
    print(f"    device  = 0x{s[j+2] | (s[j+3] << 8):04x}")
    print(f"    devlist = 0x{s[j+4] | (s[j+5] << 8):04x}")
    print(f"    structlen = 0x{s[j+6] | (s[j+7] << 8):04x}")
    print(f"    classcode = 0x{s[j+9]:02x}{s[j+8]:02x}{s[j+11]:02x}{s[j+10]:02x}")

# so header ROM goc
print("\n=== header cua ROM FILE ===")
print(f"  +0x00: {r[0:16].hex(' ')}  ({r[0:4]!r})")
i2 = r.find(b"PCIR")
print(f"  PCIR @0x{i2:x}" if i2 >= 0 else "  khong co PCIR trong ROM file")

json.dump(dict(shadow_size=len(s), shadow_sha256=hashlib.sha256(s).hexdigest(),
               shadow_starts_55aa=True, shadow_pcir_off=i,
               rom_size=len(r), rom_sha256=hashlib.sha256(r).hexdigest(),
               rom_starts=str(r[0:4]),
               best_match=dict(cand=cand, offset_hex=f"0x{cand:06x}",
                               ratio=round(ratio, 4)),
               conclusion="BAR0 0x300000 = VBIOS shadow bat dau bang legacy "
                          "55AA header; ROM file la container bat dau NVGIf"),
          open("VBIOS/shadow_vs_rom.json", "w"), indent=1)
print("\n-> VBIOS/shadow_vs_rom.json")
