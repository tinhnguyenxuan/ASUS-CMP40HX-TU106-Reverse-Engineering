#!/usr/bin/env python3
# typed_table_verify.py — offline, read-only typed VBIOS table verification.
# Decodes BIT P pointer-table slots strictly per envytools source parsers
# (/tmp/envytools/nvbios/power.c; nvbios.c only for PERF offset provenance).
# Never writes the ROM. Unknown bytes are kept with raw values; nothing is guessed.
# ponytail: single file, stdlib only, assert-based self-check as the runnable check.

import datetime, hashlib, json, os, struct, sys

ROM = '/tmp/CMP40HX_ORIGINAL_1MB.bin'
OUT_DIR = '/home/REDACTED_USER/codex-work/work_v15/PHASE16/VBIOS_TYPED'
EXPECTED_ROM_SHA256 = 'dc5395dd845cf2139f94c8b4b342adf91206aec0e3ed18103ad94ba18d009dec'
SOURCE_FILES = ['/tmp/envytools/nvbios/power.c',
                '/tmp/envytools/nvbios/bit.c',
                '/tmp/envytools/nvbios/nvbios.c']

def sha_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()

ROM_BYTES = open(ROM, 'rb').read()
FSIZE = len(ROM_BYTES)
ROM_SHA = sha_file(ROM)

def u8(off):
    if off is None or off < 0 or off + 1 > FSIZE: return None
    return ROM_BYTES[off]

def u16(off):
    if off is None or off < 0 or off + 2 > FSIZE: return None
    return struct.unpack_from('<H', ROM_BYTES, off)[0]

def u32(off):
    if off is None or off < 0 or off + 4 > FSIZE: return None
    return struct.unpack_from('<I', ROM_BYTES, off)[0]

def s16(off):
    if off is None or off < 0 or off + 2 > FSIZE: return None
    return struct.unpack_from('<h', ROM_BYTES, off)[0]

def raw(off, n):
    if off is None or n < 0 or off < 0 or off + n > FSIZE: return None
    return ROM_BYTES[off:off+n]

def F(name, off, size, value, line, note=''):
    rb = raw(off, size)
    return {'name': name, 'abs_offset': off, 'abs_offset_hex': hex(off),
            'size': size, 'raw_value': value,
            'raw_hex': rb.hex() if rb is not None else None,
            'interpretation': note, 'source_line': line}

def unknown_gaps(start, end, covered):
    covered = sorted((max(a, start), min(b, end)) for a, b in covered if b > a)
    gaps, cur = [], start
    for a, b in covered:
        if b <= a: continue
        if a > cur:
            rb = raw(cur, a - cur)
            gaps.append({'offset': cur, 'offset_hex': hex(cur), 'size': a - cur,
                         'raw_hex': rb.hex() if rb is not None else None})
        cur = max(cur, b)
    if cur < end:
        rb = raw(cur, end - cur)
        gaps.append({'offset': cur, 'offset_hex': hex(cur), 'size': end - cur,
                     'raw_hex': rb.hex() if rb is not None else None})
    return gaps

# ---------------------------------------------------------------------------
# Source-faithful analyzers. Each returns (status, header_fields, entries,
# extent_start, extent_end, extent_basis, unknowns, notes).
# ---------------------------------------------------------------------------

def analyze_unk44(off):  # slot 17 PERF TEST SPEC — power.c:1188 case 0x10
    notes = []
    v = u8(off + 0); hlen = u8(off + 1)
    if v is None or hlen is None:
        return 'outofrange', [], [], off, None, 'raw range invalid', [], ['version/hlen byte unreadable']
    fields = [F('version', off + 0, 1, v, 1195,
                'source power.c:1195 bios_u8(offset+0x0, &unk44->version)'),
              F('hlen', off + 1, 1, hlen, 1198,
                'source power.c:1198 bios_u8(offset+0x1, &unk44->hlen)')]
    extent_end = off + hlen
    notes.append("source power.c:1200: 'it doesn't appear as if this table has entries at all' -> no entries read")
    notes.append('offset+2 (0x46=70) and offset+3 (0xb7=183) are NOT entry_size/count for this parser; source reads hlen at offset+1 only and never reads offset+2/+3 as esz/cnt')
    return ('decoded', fields, [], off, extent_end, 'hlen=14 read at offset+1 by source (power.c:1198)',
            unknown_gaps(off, extent_end, [(off, off + 2)]), notes)

def analyze_therm_devices(off):  # slot 5 THERMAL DEVICES — power.c:239 case 0x10
    v = u8(off + 0); hlen = u8(off + 1); rlen = u8(off + 2); num = u8(off + 3)
    if None in (v, hlen, rlen, num):
        return 'outofrange', [], [], off, None, 'raw range invalid', [], ['header byte unreadable']
    fields = [F('version', off + 0, 1, v, 249, 'source power.c:249 bios_u8(offset+0x0, &version)'),
              F('hlen', off + 1, 1, hlen, 250, 'source power.c:250 bios_u8(offset+0x1, &hlen)'),
              F('rlen', off + 2, 1, rlen, 251, 'source power.c:251 bios_u8(offset+0x2, &rlen)'),
              F('entriesnum', off + 3, 1, num, 252, 'source power.c:252 bios_u8(offset+0x3, &entriesnum)')]
    entries = []
    covered = [(off, off + 4)]
    for i in range(num):
        eoff = off + hlen + i * rlen
        ef = []
        cid = u8(eoff + 0); i2c = u8(eoff + 1); fl = u8(eoff + 2)
        if cid is not None: ef.append(F('class_id', eoff + 0, 1, cid, 266,
                                        'source power.c:266 bios_u8(data+0x0, &class_id)'))
        if i2c is not None: ef.append(F('i2c_device', eoff + 1, 1, i2c, 267,
                                        'source power.c:267 bios_u8(data+0x1, &i2c_device)'))
        if fl is not None: ef.append(F('flags', eoff + 2, 1, fl, 268,
                                       'source power.c:268 bios_u8(data+0x2, &flags)'))
        entries.append({'index': i, 'abs_offset': eoff, 'abs_offset_hex': hex(eoff),
                        'raw_hex': raw(eoff, rlen).hex() if raw(eoff, rlen) is not None else None,
                        'fields': ef,
                        'entry_basis': 'offset = table + hlen + i*rlen (power.c:262), i in [0,entriesnum)'})
        covered.append((eoff, eoff + rlen))
    extent_end = off + hlen + num * rlen
    return ('decoded', fields, entries, off, extent_end,
            'hlen + entriesnum*rlen (source power.c:260-268)',
            unknown_gaps(off, extent_end, covered),
            ['class_id 0x01 = GPU per therm_class_types (power.c:234-237)'])

def analyze_unk50(off):  # slot 20 THERMAL POLICY — power.c:1334 case 0x10
    v = u8(off + 0); hlen = u8(off + 1); rlen = u8(off + 2); num = u8(off + 3)
    if None in (v, hlen, rlen, num):
        return 'outofrange', [], [], off, None, 'raw range invalid', [], ['header byte unreadable']
    fields = [F('version', off + 0, 1, v, 1344, 'source power.c:1344 bios_u8(offset+0x0, &version)'),
              F('hlen', off + 1, 1, hlen, 1345, 'source power.c:1345 bios_u8(offset+0x1, &hlen)'),
              F('rlen', off + 2, 1, rlen, 1346, 'source power.c:1346 bios_u8(offset+0x2, &rlen)'),
              F('entriesnum', off + 3, 1, num, 1347, 'source power.c:1347 bios_u8(offset+0x3, &entriesnum)')]
    entries = []
    covered = [(off, off + 4)]
    for i in range(num):
        eoff = off + hlen + i * rlen
        mode = u8(eoff + 0); t0 = u16(eoff + 2); t1 = u16(eoff + 4); t2 = u16(eoff + 6)
        iv = u16(eoff + 8); doff = s16(eoff + 0x12); uoff = s16(eoff + 0x14)
        ef = []
        if mode is not None: ef.append(F('mode', eoff + 0, 1, mode, 1361,
                                         'source power.c:1361 bios_u8(e->offset+0x0, &e->mode)'))
        if t0 is not None: ef.append(F('t0', eoff + 2, 2, t0, 1362,
                                       'source power.c:1362 bios_u16(e->offset+0x2, &e->t0); printed /32 C'))
        if t1 is not None: ef.append(F('t1', eoff + 4, 2, t1, 1363,
                                       'source power.c:1363 bios_u16(e->offset+0x4, &e->t1); printed /32 C'))
        if t2 is not None: ef.append(F('t2', eoff + 6, 2, t2, 1363,
                                       'source power.c:1363 bios_u16(e->offset+0x6, &e->t2); printed /32 C'))
        if iv is not None: ef.append(F('interval_us', eoff + 8, 2, iv, 1364,
                                       'source power.c:1364 bios_u16(e->offset+0x8, &e->interval_us)'))
        if doff is not None: ef.append(F('down_off', eoff + 0x12, 2, doff, 1366,
                                         'source power.c:1366 bios_u16(e->offset+0x12, &e->down_off); int16, /32 C'))
        if uoff is not None: ef.append(F('up_off', eoff + 0x14, 2, uoff, 1367,
                                         'source power.c:1367 bios_u16(e->offset+0x14, &e->up_off); int16, /32 C'))
        entries.append({'index': i, 'abs_offset': eoff, 'abs_offset_hex': hex(eoff),
                        'raw_hex': raw(eoff, rlen).hex() if raw(eoff, rlen) is not None else None,
                        'fields': ef,
                        'entry_basis': 'offset = hlen + i*rlen (power.c:1359), i in [0,entriesnum); mode switch prints only mode==1 (power.c:1392)'})
        covered.append((eoff, eoff + rlen))
    extent_end = off + hlen + num * rlen
    return ('decoded', fields, entries, off, extent_end,
            'hlen + entriesnum*rlen (source power.c:1355-1368)',
            unknown_gaps(off, extent_end, covered),
            ['t0/t1/t2/down_off/up_off printed as value/32 °C (power.c:1393-1396)'])

def analyze_budget(off, version):  # slot 11 POWER BUDGET — power.c:644
    v = u8(off + 0); hlen = u8(off + 1); rlen = u8(off + 2); num = u8(off + 3)
    if None in (v, hlen, rlen, num):
        return 'outofrange', [], [], off, None, 'raw range invalid', [], ['header byte unreadable']
    fields = [F('version', off + 0, 1, v, 657, 'source power.c:657 bios_u8(offset+0x0, &version)'),
              F('hlen', off + 1, 1, hlen, 658, 'source power.c:658 bios_u8(offset+0x1, &hlen)'),
              F('rlen', off + 2, 1, rlen, 659, 'source power.c:659 bios_u8(offset+0x2, &rlen)'),
              F('entriesnum', off + 3, 1, num, 660, 'source power.c:660 bios_u8(offset+0x3, &entriesnum)')]
    cap = None
    if version == 0x30:
        cap = u8(off + 0xa)
        if cap is not None:
            fields.append(F('cap_entry', off + 0xa, 1, cap, 673,
                            'source power.c:673 bios_u8(offset+0xa, &cap_entry) [0x30 branch]'))
    elif version == 0x20:
        cap = u8(off + 0x9)
        if cap is not None:
            fields.append(F('cap_entry', off + 0x9, 1, cap, 669,
                            'source power.c:669 bios_u8(offset+0x9, &cap_entry) [0x20 branch]'))
    entries = []
    covered = [(off, off + hlen)]
    for i in range(num):
        eoff = off + hlen + i * rlen
        ef = []
        if rlen == 0x6:
            avg = u32(eoff + 0x02)
            if avg is not None:
                ef.append(F('avg', eoff + 0x02, 4, avg, 686,
                            'source power.c:686 bios_u32(data+0x02, &avg) [rlen==6]'))
        else:
            mn = u32(eoff + 0x02); avg = u32(eoff + 0x06); pk = u32(eoff + 0x0a); unk = u32(eoff + 0x12)
            if mn is not None: ef.append(F('min', eoff + 0x02, 4, mn, 688,
                                           'source power.c:688 bios_u32(data+0x02, &min)'))
            if avg is not None: ef.append(F('avg', eoff + 0x06, 4, avg, 688,
                                            'source power.c:688 bios_u32(data+0x06, &avg)'))
            if pk is not None: ef.append(F('peak', eoff + 0x0a, 4, pk, 689,
                                           'source power.c:689 bios_u32(data+0x0a, &peak)'))
            if unk is not None: ef.append(F('unkn12', eoff + 0x12, 4, unk, 691,
                                            'source power.c:691 bios_u32(data+0x12, &unkn12)'))
        entries.append({'index': i, 'abs_offset': eoff, 'abs_offset_hex': hex(eoff),
                        'raw_hex': raw(eoff, rlen).hex() if raw(eoff, rlen) is not None else None,
                        'fields': ef,
                        'entry_basis': 'offset = hlen + i*rlen (power.c:680); rlen!=6 path reads min/avg/peak/unkn12 (power.c:688-691)'})
        covered.append((eoff, eoff + rlen))
    extent_end = off + hlen + num * rlen
    return ('decoded', fields, entries, off, extent_end,
            'hlen + entriesnum*rlen (source power.c:677-691)',
            unknown_gaps(off, extent_end, covered),
            ['cap_entry only for version 0x20/0x30 branches (power.c:667-674)'])

# ---------------------------------------------------------------------------
# Table specifications (slot -> file offset taken from the task's observed ROM
# offsets; P2 index = slot number; P2_tbls names from power.c:82-103).
# ---------------------------------------------------------------------------

TABLE_SPECS = [
    {'slot': 17, 'name': 'PERF TEST SPEC', 'p2_off': 0x44, 'off': 0x545f2,
     'src_file': '/tmp/envytools/nvbios/power.c', 'src_fn': 'envy_bios_parse_power_unk44',
     'src_line': 1188, 'supported': [0x10], 'kind': 'unk44'},
    {'slot': 5, 'name': 'THERMAL DEVICES', 'p2_off': 0x14, 'off': 0x58723,
     'src_file': '/tmp/envytools/nvbios/power.c', 'src_fn': 'envy_bios_parse_power_therm_devices',
     'src_line': 239, 'supported': [0x10], 'kind': 'therm_devices'},
    {'slot': 20, 'name': 'THERMAL POLICY', 'p2_off': 0x50, 'off': 0x58679,
     'src_file': '/tmp/envytools/nvbios/power.c', 'src_fn': 'envy_bios_parse_power_unk50',
     'src_line': 1334, 'supported': [0x10], 'kind': 'unk50'},
    {'slot': 11, 'name': 'POWER BUDGET', 'p2_off': 0x2c, 'off': 0x57e92,
     'src_file': '/tmp/envytools/nvbios/power.c', 'src_fn': 'envy_bios_parse_power_budget',
     'src_line': 644, 'supported': [0x10, 0x20, 0x30], 'kind': 'budget'},
    {'slot': 0, 'name': 'PERFORMANCE', 'p2_off': 0x00, 'off': 0x054155,
     'src_file': '/tmp/envytools/nvbios/nvbios.c', 'src_fn': '(no table field parser)',
     'src_line': 1095, 'supported': [], 'kind': 'perf'},
]

ANALYZERS = {'unk44': analyze_unk44, 'therm_devices': analyze_therm_devices,
             'unk50': analyze_unk50, 'budget': lambda off, ver=None: analyze_budget(off, ver)}

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    results = []
    for spec in TABLE_SPECS:
        off = spec['off']
        version = u8(off)
        rec = {
            'slot': spec['slot'], 'name': spec['name'], 'p2_offset': spec['p2_off'],
            'p2_offset_hex': hex(spec['p2_off']),
            'file_offset': off, 'file_offset_hex': hex(off),
            'source_file': spec['src_file'], 'source_function': spec['src_fn'],
            'source_line': spec['src_line'],
            'version_raw': version, 'version_raw_hex': None if version is None else hex(version),
            'source_supported_versions': [hex(x) for x in spec['supported']],
            'branch_taken': None, 'status': None, 'extent': None,
            'header': {'offset': off, 'size': None, 'raw_hex': None, 'fields': []},
            'entries': [], 'unknown_bytes': [], 'notes': [],
        }
        if version is None:
            rec['status'] = 'outofrange'; rec['notes'].append('version byte at file offset unreadable (raw range invalid)')
            results.append(rec); continue
        if spec['supported'] and version in spec['supported']:
            rec['branch_taken'] = hex(version)
            analyzer = ANALYZERS[spec['kind']]
            if spec['kind'] == 'budget':
                status, hfields, entries, estart, eend, basis, unknowns, notes = analyzer(off, version)
            else:
                status, hfields, entries, estart, eend, basis, unknowns, notes = analyzer(off)
            rec['status'] = status
            rec['header']['size'] = (eend - estart) if status != 'decoded' else None
            rec['header']['fields'] = hfields
            rec['header']['raw_hex'] = raw(off, hfields and sum(f['size'] for f in hfields) or 0).hex() if hfields else None
            rec['entries'] = entries
            rec['unknown_bytes'] = unknowns
            rec['notes'] = notes
            rec['extent'] = {'start': estart, 'end': eend, 'len': eend - estart,
                             'end_hex': hex(eend), 'basis': basis} if eend is not None else None
        else:
            rec['status'] = 'unsupported'
            rec['notes'].append('version %s not in source-supported branches %s; no field schema decoded'
                                % (hex(version), [hex(x) for x in spec['supported']] or 'none (no table field parser in source)'))
            rb = raw(off, 32)
            rec['header']['raw_hex'] = rb.hex() if rb is not None else None
            rec['unknown_bytes'].append({'offset': off, 'offset_hex': hex(off), 'size': 32 if rb else 0,
                                         'raw_hex': rb.hex() if rb is not None else None,
                                         'note': 'preserved raw bytes; no source schema to interpret'})
            if spec['kind'] == 'perf':
                rec['notes'].append('perf.offset provenance: nvbios.c:1095 le16(bmp_offset+148); table bytes only hex-dumped in print routine nvbios.c:1477 — no envytools field parser for PERF table contents')
        results.append(rec)

    decoded = [r for r in results if r['status'] == 'decoded']
    unsupported = [r for r in results if r['status'] == 'unsupported']
    out_of_range = [r for r in results if r['status'] == 'outofrange']

    report = {
        'tool': 'typed_table_verify.py',
        'generated_at': datetime.datetime.now(datetime.timezone.utc).isoformat() + 'Z',
        'rom': {'path': ROM, 'size': FSIZE, 'sha256': ROM_SHA,
                'expected_sha256': EXPECTED_ROM_SHA256, 'sha256_match': ROM_SHA == EXPECTED_ROM_SHA256},
        'sources': {p: sha_file(p) for p in SOURCE_FILES},
        'tables': results,
        'overlap_reassessment': {
            'slot17_generic_model_extent': {'start': 0x545f2, 'end': 0x05780a, 'len': 12824,
                                            'basis': 'generic hdr+esz*cnt model: esz=70 cnt=183 — NOT read by source parser'},
            'slot17_source_extent': {'start': 0x545f2, 'end': 0x54600, 'len': 14,
                                     'basis': 'hlen=14 read at offset+1 by source power.c:1198'},
            'slot17_header_bytes_misread': {'offset+2': 70, 'offset+3': 183,
                                            'note': 'generic model read raw bytes 0x46/0xb7 as entry_size/count; source parser (power.c:1198) reads only version@+0 and hlen@+1, never offset+2/+3'},
            'adjacency': 'slot17 source extent end 0x54600 == next slot (slot 1) table start 0x054600 per prior pointer mapping — adjacent, NOT overlapping',
            'conclusion': 'the 14 generic-model overlaps involving slot17 are artifacts of the unverified generic header size (esz*cnt), not real table overlaps. Real source-schema decode: 4 tables (slots 17, 5, 20, 11). PERF slot 0 is UNSUPPORTED (no source field schema). Do not report 40 decoded tables.'
        },
        'summary': {'tables_total': len(results), 'decoded': len(decoded),
                    'unsupported': len(unsupported), 'out_of_range': len(out_of_range),
                    'at_least_3_decoded': len(decoded) >= 3,
                    'decoded_slots': [r['slot'] for r in decoded],
                    'unsupported_slots': [r['slot'] for r in unsupported]},
    }

    # ---- self-check (runnable check) ----
    assert report['rom']['sha256_match'], 'ROM sha256 mismatch'
    s17 = next(r for r in results if r['slot'] == 17)
    assert s17['version_raw'] == 0x10 and s17['extent']['len'] == 14 and s17['extent']['end'] == 0x54600, 'slot17 extent'
    s5 = next(r for r in results if r['slot'] == 5)
    assert s5['version_raw'] == 0x10 and s5['extent']['len'] == 4 + 18 * 3, 'slot5 extent'
    s20 = next(r for r in results if r['slot'] == 20)
    assert s20['version_raw'] == 0x10 and s20['extent']['len'] == 10 + 4 * 40, 'slot20 extent'
    s11 = next(r for r in results if r['slot'] == 11)
    assert s11['version_raw'] == 0x30 and s11['extent']['len'] == 44 + 20 * 66, 'slot11 extent'
    s0 = next(r for r in results if r['slot'] == 0)
    assert s0['version_raw'] == 0x60 and s0['status'] == 'unsupported', 'slot0 unsupported'
    assert len(decoded) >= 3, 'need >=3 source-decoded tables'

    with open(os.path.join(OUT_DIR, 'typed_tables_verified.json'), 'w') as f:
        json.dump(report, f, indent=2)
    print(json.dumps({'summary': report['summary'], 'rom_sha256': ROM_SHA, 'out_dir': OUT_DIR}, indent=2))
    for r in results:
        print('slot %-2d %-18s off %-9s ver %-5s status %-12s extent %s' % (
            r['slot'], r['name'], r['file_offset_hex'], r['version_raw_hex'], r['status'],
            None if r['extent'] is None else ("%s..%s len=%d" % (hex(r['extent']['start']), hex(r['extent']['end']), r['extent']['len']))))

if __name__ == '__main__':
    main()
