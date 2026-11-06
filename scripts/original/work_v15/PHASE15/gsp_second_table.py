#!/usr/bin/env python3
"""Tim bang descriptor thu 2 chua 7 ten thua trong gsp_tu10x.bin (offline, read-only)."""
import struct, os, json
ROOT='/home/REDACTED_USER/.hermes/cache/scratch/cmp40hx_research'
gsp=open(ROOT+'/outputs/gsp_tu10x.bin','rb').read()
print(f'gsp_tu10x.bin size: {len(gsp):,} B')

# 7 ten can tim
TARGETS = [b'RMClkVfOverride', b'RmAtsVolOverride', b'RmClkControllersOverride',
           b'OVERVOLTAGE_LOGIC', b'OVERVOLTAGE_NVVDD_0', b'OVERVOLTAGE_NVVDD_1',
           b'PERFORMANCE_CAP0']

# Tim offset cua moi ten trong file (string null-terminated)
found_strings = {}
for t in TARGETS:
    offs = []
    start = 0
    while True:
        i = gsp.find(t, start)
        if i < 0: break
        # kiem tra co phai chuoi null-terminated (byte sau ten la 0x00)
        if i + len(t) < len(gsp) and gsp[i+len(t)] == 0:
            offs.append(i)
        start = i + 1
    found_strings[t.decode()] = offs
    print(f'{t.decode()}: {len(offs)} occurrence(s) at {[hex(x) for x in offs]}')

# Layout entry da biet (tu Q1 disasm):
# +0x00 u16, +0x04 u32, +0x08 u8, +0x10 u64, +0x18 u16, stride 32
# name_ptr (u64@+0x10) tro toi dau chuoi ASCII

# Voi moi ten, quet xung quanh (+-512 byte) tim pattern entry
print('\n=== Quet bang entry xung quanh moi ten ===')
for name, offs in found_strings.items():
    for str_off in offs:
        # name_ptr trong entry tro toi str_off
        # entry base = str_off - 0x10 (vi name_ptr o +0x10)
        # Nhung co the co padding. Quet cac base trong khoang str_off-0x200 .. str_off+0x200
        candidates = []
        for base in range(str_off - 0x200, str_off + 0x201, 4):
            # Doc entry tai base
            if base + 32 > len(gsp): continue
            f00 = struct.unpack('<H', gsp[base:base+2])[0]
            f04 = struct.unpack('<I', gsp[base+4:base+8])[0]
            f08 = gsp[base+8]
            f10 = struct.unpack('<Q', gsp[base+0x10:base+0x18])[0]
            f18 = struct.unpack('<H', gsp[base+0x18:base+0x1a])[0]
            # name_ptr = f10 phai tro toi str_off
            if f10 == str_off:
                # Kiem tra layout co hop le khong
                # f08 (u8) phai nho (policy type), f18 (u16) phai la {group,subtype}
                if f08 <= 0xFF and f18 <= 0xFFFF:
                    candidates.append({'base': base, 'f00': f00, 'f04': f04, 'f08': f08, 'f10': f10, 'f18': f18})
        if candidates:
            print(f'\n  {name} @ str_off 0x{str_off:06X}:')
            for c in candidates:
                print(f'    entry base 0x{c["base"]:06X}: f00=0x{c["f00"]:04X} f04=0x{c["f04"]:08X} f08=0x{c["f08"]:02X} f10=0x{c["f10"]:08X} f18=0x{c["f18"]:04X}')

# Cung quet pattern: nhieu entry lien nhau co stride 32, tung entry co name_ptr tro toi chuoi
print('\n=== Quet vung chua nhieu entry lien nhau (stride 32) ===')
# Tim cac vung co it nhat 3 entry lien nhau co name_ptr hop le
entry_chains = []
for base in range(0x400000, len(gsp) - 256, 4):
    count = 0
    for i in range(8):  # kiem tra 8 entry lien nhau
        ebase = base + i * 32
        if ebase + 32 > len(gsp): break
        f10 = struct.unpack('<Q', gsp[ebase+0x10:ebase+0x18])[0]
        # name_ptr phai tro toi vung string (co byte 0x00 sau chuoi)
        if 0x100000 <= f10 < 0x2000000:  # trong vung rodata
            # kiem tra co chuoi null-terminated tai f10
            str_end = gsp.find(b'\x00', f10 - 0x400000)
            if str_end >= 0 and str_end - (f10 - 0x400000) < 64:
                count += 1
            else:
                break
        else:
            break
    if count >= 3:
        entry_chains.append({'start': base, 'count': count})
        if len(entry_chains) >= 30:
            break

print(f'Tim {len(entry_chains)} chain co >= 3 entry lien nhau:')
for c in entry_chains[:15]:
    print(f'  start 0x{c["start"]:06X} (~vaddr 0x{0x4000000+c["start"]:08X}): {c["count"]} entry')

# Luu ket qua
os.makedirs(ROOT+'/PHASE15', exist_ok=True)
json.dump({
 'found_strings': {k: v for k, v in found_strings.items()},
 'entry_chains': [{'start': c['start'], 'count': c['count']} for c in entry_chains[:30]],
}, open(ROOT+'/PHASE15/gsp_second_table.json','w'), indent=1)
print('\nSaved PHASE15/gsp_second_table.json')
