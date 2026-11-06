#!/usr/bin/env python3
"""Phan tich sau fuse2.json: bit pattern, vung dia chi, lien he topology, +0x0718."""
import json, zlib, struct, os, collections
ROOT='/home/REDACTED_USER/.hermes/cache/scratch/cmp40hx_research'
d=json.load(open(ROOT+'/FUSE/fuse2.json'))
regs=d['regs']; poison=set(d['poison'])
ri={int(k):v for k,v in regs.items()}
POISONS={0xBADF5040,0xBADF1300,0xBADF1100}
data={k:v for k,v in ri.items() if v not in POISONS and v!=0}
zero={k:v for k,v in ri.items() if v==0}
print(f'=== TONG QUAT: data={len(data)} zero={len(zero)} poison={len(ri)-len(data)-len(zero)} ===')
print(f'Poison codes: {[hex(x) for x in POISONS]}')
print(f'Distinct data values: {len(set(data.values()))}')
print()
# 1. Cac word = 1 chi tiet
ones=[(k,v) for k,v in data.items() if v==1]
print(f'=== WORD == 1: {len(ones)} word ===')
# Nhom theo vung
def region(off):
    if off<0x100: return 'strap(0x000-0x0FF)'
    if off<0x200: return 'unk1(0x100-0x1FF)'
    if off<0x400: return 'unk2(0x200-0x3FF)'
    if off<0x600: return 'unk3(0x400-0x5FF)'
    if off<0x800: return 'unk4(0x600-0x7FF)'
    if off<0xC00: return 'unk5(0x800-0xBFF)'
    if off<0x1000: return 'unk6(0xC00-0xFFF)'
    return f'high(0x{off:04X}+)'
regcnt=collections.Counter(region(k) for k,v in ones)
for r,c in regcnt.most_common():
    print(f'  {r}: {c}')
print()
# 2. Cac gia tri data khac 1, top 30
valcnt=collections.Counter(data.values())
print('=== TOP 30 GIA TRI DATA (loai 1) ===')
for val,cnt in valcnt.most_common(30):
    if val==1: continue
    offs=[hex(k) for k,v in data.items() if v==val]
    print(f'  {hex(val):>12} x{cnt} @ {",".join(offs[:8])}{"..." if len(offs)>8 else ""}')
print()
# 3. Vung co du lieu tan suat cao
print('=== RUN DATA CAO NHAT ===')
offs=sorted(data.keys())
runs=[]; s=offs[0]; p=offs[0]
for o in offs[1:]:
    if o==p+4: p=o
    else: runs.append((s,p)); s=p=o
runs.append((s,p))
runs.sort(key=lambda x:-(x[1]-x[0]))
for a,b in runs[:15]:
    print(f'  0x{a:04X}..0x{b:04X} ({(b-a)//4+1} word)')
print()
# 4. Topology cross-check: fuse+0x650, 0xC1C, 0x4D8, 0x56C
print('=== TOPOLOGY CROSS-CHECK ===')
for off,name in [(0x4D8,'PCI ID'),(0x56C,'Family'),(0x650,'TPC/SM'),(0xC1C,'GPC'),(0x074C,'GSP_DEBUG_DIS'),(0x0378,'NVDEC_DISABLE'),(0x0C04,'DISPLAY_ENABLE')]:
    v=ri.get(off,0)
    print(f'  fuse+0x{off:04X} ({name}): {hex(v)}')
print()
# 5. fuse +0x0718: thu CRC32, Adler32, cac hash ngan
print('=== fuse +0x0718 (8 word, 32 byte) ===')
h718=[ri.get(0x718+i*4,0) for i in range(8)]
print('Raw:', ' '.join(f'{x:08X}' for x in h718))
raw32=struct.pack('<8I',*h718)
print(f'CRC32(raw32): {zlib.crc32(raw32):08X}')
print(f'Adler32(raw32): {zlib.adler32(raw32):08X}')
# Thu voi moi word lan luot
for i,w in enumerate(h718):
    print(f'  fuse+0x{0x718+i*4:04X}: {hex(w)}  CRC32={zlib.crc32(struct.pack("<I",w)):08X}')
# Thu ghep 2 word (64 bit) -> CRC32
for i in range(0,8,2):
    pair=struct.pack('<2I',h718[i],h718[i+1])
    print(f'  CRC32(pair {i//2}): {zlib.crc32(pair):08X}')
print()
# 6. So sanh voi cac gia tri biet: PDI, device ID, v.v.
known={
 'PCI_ID':0x1F0B,'FAMILY':0x1F4B,'TPC_SM':0x4001F,'GPC':0x38,
 'PDI_LO':0x40680BB5,'PDI_HI':0x72E259ED,'GSP_DIS':0x1,'DISPLAY_EN':0x1,
 'NVDEC_DIS':0x0,'BADF5040':0xBADF5040,'BADF510C':0xBADF510C,'BADF1300':0xBADF1300,
 'BADF1100':0xBADF1100,'FFFFFF8F':0xFFFFFF8F,'FFFFFFFC':0xFFFFFFFC,
}
print('=== SO SANH DATA VOI GIA TRI BIET ===')
for kn,kv in known.items():
    offs=[hex(k) for k,v in data.items() if v==kv]
    if offs:
        print(f'  {kn} ({hex(kv)}): @ {",".join(offs[:10])}{"..." if len(offs)>10 else ""} ({len(offs)} lan)')
print()
# 7. Bit pattern analysis: cac bit thiet lap nhat nhat trong data
bitcnt=collections.Counter()
for v in data.values():
    for b in range(32):
        if v>>b & 1: bitcnt[b]+=1
print('=== BIT THIET LAP NHAT (trong data) ===')
for b,c in bitcnt.most_common(16):
    print(f'  bit {b}: {c}/{len(data)} word')
print()
os.makedirs(ROOT+'/PHASE15',exist_ok=True)
out={
 'data_count':len(data),'zero_count':len(zero),'poison_count':len(ri)-len(data)-len(zero),
 'distinct_values':len(set(data.values())),
 'word_ones_count':len(ones),'word_ones_regions':dict(regcnt),
 'top_values':[{'value':hex(v),'count':c} for v,c in valcnt.most_common(20) if v!=1],
 'top_runs':[{'start':hex(a),'end':hex(b),'count':(b-a)//4+1} for a,b in runs[:15]],
 'topology':{name:hex(ri.get(off,0)) for off,name in [(0x4D8,'PCI_ID'),(0x56C,'FAMILY'),(0x650,'TPC_SM'),(0xC1C,'GPC'),(0x074C,'GSP_DIS'),(0x0378,'NVDEC_DIS'),(0x0C04,'DISPLAY_EN')]},
 'fuse718_raw':[hex(x) for x in h718],
 'fuse718_crc32':zlib.crc32(raw32),
 'fuse718_adler32':zlib.adler32(raw32),
 'bit_counts':{str(b):c for b,c in bitcnt.most_common(32)},
}
json.dump(out,open(ROOT+'/PHASE15/fuse_deep.json','w'),indent=1)
print('Saved PHASE15/fuse_deep.json')
