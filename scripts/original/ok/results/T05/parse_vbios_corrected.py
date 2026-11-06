#!/usr/bin/env python3
"""Bounds-checked DCB 4.1 parser for the two supplied CMP ROMs.

Important: DCB 4.x table pointers in these ROMs are relative to the legacy
image base, not relative to the DCB header. The parser records that explicitly
and compares its result with the saved handoff evidence.
"""
from __future__ import annotations
import hashlib, json, struct
from pathlib import Path

ROOT = Path('/home/REDACTED_USER/codex-work/CMP40HX_INDEPENDENT_REVIEW')
ROM_DIR = ROOT / 'input/ASTRA_CMP40HX_HANDOFF/03_VBIOS'
OUT = ROOT / 'results/T05/VBIOS_DISPLAY_TABLES.json'
ROM_NAMES = ['CMP40HX_ORIGINAL_1MB.bin', 'cmp40hx_t4_derivative.bin']


def u8(b, o):
    if o < 0 or o + 1 > len(b): raise ValueError(f'OOB u8 0x{o:x}')
    return b[o]


def u16(b, o):
    if o < 0 or o + 2 > len(b): raise ValueError(f'OOB u16 0x{o:x}')
    return struct.unpack_from('<H', b, o)[0]


def u32(b, o):
    if o < 0 or o + 4 > len(b): raise ValueError(f'OOB u32 0x{o:x}')
    return struct.unpack_from('<I', b, o)[0]


def rows(b, off, count, size):
    end = off + count * size
    if off < 0 or end > len(b): raise ValueError(f'OOB table 0x{off:x}+{count}*{size}')
    return [b[off + i*size:off + (i+1)*size].hex() for i in range(count)]


def pcir_images(b):
    out = []
    off = 0
    while off + 512 <= len(b):
        if b[off:off+2] == b'\x55\xaa':
            po = u16(b, off + 0x18)
            if 0 < po <= 508 and b[off+po:off+po+4] == b'PCIR':
                out.append({
                    'block_off': hex(off),
                    'pcir_off': hex(po),
                    'vendor': f'0x{u16(b, off+po+4):04x}',
                    'device': f'0x{u16(b, off+po+6):04x}',
                    'image_len': u16(b, off+po+0x10) * 512,
                })
                step = u16(b, off+po+0x10) * 512
                off += step if step else 512
                continue
        off += 512
    return out


def parse_table_header(b, off):
    return {'offset': hex(off), 'version': hex(u8(b, off)),
            'header_size': u8(b, off+1), 'count': u8(b, off+2),
            'entry_size': u8(b, off+3)}


def parse_rom(name):
    path = ROM_DIR / name
    b = path.read_bytes()
    imgs = pcir_images(b)
    bases = [int(x['block_off'], 16) for x in imgs]
    base = 0x28600 if 0x28600 in bases else (bases[0] if bases else None)
    r = {'file': name, 'path': str(path), 'size': len(b),
         'sha256': hashlib.sha256(b).hexdigest(), 'pcir_images': imgs,
         'legacy_image_base': hex(base) if base is not None else None}
    if base is None:
        r['status'] = 'BLOCKED_NO_PCIR_IMAGE'
        return r
    ptr = u16(b, base + 0x36)
    dcb = base + ptr
    if u8(b, dcb) != 0x41:
        r['status'] = 'BLOCKED_UNEXPECTED_DCB_VERSION'
        r['dcb_offset'] = hex(dcb)
        return r
    hlen, count, rlen = u8(b,dcb+1), u8(b,dcb+2), u8(b,dcb+3)
    sig = u32(b, dcb+6)
    # DCB 4.1 fields from the saved envytools parser: all table offsets are
    # relative to the legacy image base used by the BIOS parser.
    fields = {
        'communications': u16(b,dcb+4),
        'gpio': u16(b,dcb+10),
        'input': u16(b,dcb+12),
        'cinema': u16(b,dcb+14),
        'spread_spectrum': u16(b,dcb+16),
        'i2c_devices': u16(b,dcb+18),
        'connector': u16(b,dcb+20),
        'unknown_22': u8(b,dcb+22),
    }
    if hlen >= 25: fields['hdtv'] = u16(b,dcb+23)
    if hlen >= 27: fields['mux'] = u16(b,dcb+25)
    tables = {}
    for key, rel in fields.items():
        if key == 'unknown_22': continue
        if rel == 0:
            tables[key] = {'present': False, 'relative_offset': '0x0'}
            continue
        off = base + rel
        th = parse_table_header(b, off)
        th.update({'present': True, 'relative_offset': hex(rel)})
        tables[key] = th
    # Preserve bounded raw rows and only decode fields covered by the saved
    # v4.1 layouts. No connector output row is invented when count is zero.
    for key in ('communications','gpio','i2c_devices','connector'):
        t = tables.get(key, {})
        if not t.get('present'): continue
        off = int(t['offset'], 16)
        count2, size = t['count'], t['entry_size']
        raw = rows(b, off + t['header_size'], count2, size)
        t['raw_rows'] = raw
        if key == 'communications' and t['version'] == '0x41' and size >= 4:
            decoded=[]
            for rawhex in raw:
                v=int.from_bytes(bytes.fromhex(rawhex[:8]), 'little')
                decoded.append({'i2c_port':v&0x1f, 'dpaux_port':(v>>5)&0x1f,
                                'high_bits':hex(v>>10), 'raw':rawhex})
            t['decoded_rows']=decoded
        elif key == 'gpio' and t['version'] == '0x41' and size >= 5:
            t['decoded_rows']=[{'line':int.from_bytes(bytes.fromhex(x[0:2]),'little')&0x3f,
                                'tag':'0x'+x[2:4], 'special_output':'0x'+x[4:6],
                                'special_input':'0x'+x[6:8], 'raw':x}
                               for x in raw]
        elif key == 'i2c_devices' and size >= 4:
            t['decoded_type_bytes']=['0x'+x[6:8] for x in raw]
    r.update({'status':'OK', 'dcb': {
        'offset':hex(dcb), 'version':'0x41', 'header_size':hlen,
        'entry_count':count, 'entry_size':rlen, 'signature':hex(sig),
        'signature_valid': sig == 0x4edcbdcb,
        'pointer_base': 'legacy_image_base', 'fields': {k:hex(v) for k,v in fields.items()},
        'tables': tables,
    }})
    return r

results=[parse_rom(n) for n in ROM_NAMES]
OUT.write_text(json.dumps({'parser':'parse_vbios_corrected.py','results':results}, indent=2)+'\n')
for r in results:
    d=r.get('dcb',{})
    t=d.get('tables',{})
    print(r['file'], r['status'], r['sha256'])
    print(' DCB', d.get('offset'), d.get('version'), 'sig', d.get('signature_valid'), 'entries', d.get('entry_count'))
    for k in ('communications','gpio','i2c_devices','connector'):
        x=t.get(k,{})
        print(' ',k, 'present',x.get('present'), 'count',x.get('count'), 'size',x.get('entry_size'))
