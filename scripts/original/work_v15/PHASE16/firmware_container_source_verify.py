#!/usr/bin/env python3
# firmware_container_source_verify.py
# Source-corroborated verification of ucodes_tu10x.bin against NVIDIA bindata
# headers, plus GSP pairing search (fingerprint64/numEntries) in gsp_tu10x.bin.
# Offline, read-only, stdlib only. Re-run: /usr/bin/python3 firmware_container_source_verify.py   (cwd PHASE16)
import struct, hashlib, json, sys
from pathlib import Path
from collections import Counter

ROOT = Path('/home/REDACTED_USER/codex-work/work_v15')
PH = ROOT / 'PHASE16'
BIN = ROOT / 'outputs/ucodes_tu10x.bin'
GSP = ROOT / 'outputs/gsp_tu10x.bin'
PREV = PH / 'firmware_container_verified.json'
SRC_H = PH / 'SOURCES/nvidia_bin_data_pvt.h'
MANIFEST = PH / 'SOURCES/manifest.json'
ELF_MAP = PH / 'elf_map.json'
OUT = PH / 'firmware_container_source_verified.json'

HDR = struct.Struct('<8sIIQ')   # magic, version, numEntries, fingerprint64 -> 24 B
REC = struct.Struct('<IIQII')   # actualSize, compressedSize, pData, flags, relOffset -> 24 B
FLAG_COMPRESSED = 0x01
FLAG_EXTERNAL   = 0x04

def sha(b): return hashlib.sha256(b).hexdigest()

def find_all(haystack, needle):
    offs, start = [], 0
    while True:
        i = haystack.find(needle, start)
        if i < 0: break
        offs.append(i); start = i + 1
    return offs

def main():
    data = BIN.read_bytes(); size = len(data)
    inhash = sha(data)
    src_text = SRC_H.read_text(encoding='utf-8')
    srchash = sha(src_text.encode('utf-8'))
    manifest = json.loads(MANIFEST.read_text())

    magic, version, num_entries, fingerprint = HDR.unpack_from(data, 0)
    hdr_size = HDR.size
    table_end = hdr_size + num_entries * REC.size
    val_issues = []
    if magic != b'NVUCODES': val_issues.append({'check': 'header_magic', 'expected': 'NVUCODES', 'got': magic.decode('ascii', 'replace')})
    if version != 1: val_issues.append({'check': 'header_version', 'expected': 1, 'got': version})
    if table_end > size: val_issues.append({'check': 'table_bounds', 'table_end': table_end, 'file_size': size})

    records = []
    for i in range(num_entries):
        roff = hdr_size + i * REC.size
        raw = data[roff:roff + REC.size]
        actualSize, compressedSize, pData, flags, relOffset = REC.unpack_from(raw)
        rec = {
            'slot': i, 'record_offset': roff, 'record_offset_hex': '0x%06X' % roff,
            'actualSize': actualSize, 'compressedSize': compressedSize,
            'pData': pData, 'pData_hex': '0x%016X' % pData,
            'flags': flags, 'flags_hex': '0x%02X' % flags,
            'relOffset': relOffset, 'relOffset_hex': '0x%06X' % relOffset,
            'rawhex': raw.hex(), 'filehash': None, 'class': 'zero', 'issues': [],
        }
        ri = []
        if actualSize == 0 and compressedSize == 0 and pData == 0 and flags == 0 and relOffset == 0:
            rec['class'] = 'zero'
        elif flags & FLAG_EXTERNAL:
            rec['class'] = 'external'
            if flags & FLAG_COMPRESSED:
                ri.append('compressed_flag_set_no_consumer_unsupported')
            if relOffset >= size: ri.append('offset_out_of_range')
            elif relOffset + actualSize > size: ri.append('overflow_eof')
            else:
                rec['filehash'] = sha(data[relOffset:relOffset + actualSize])
                rec['payload_size'] = actualSize
                if compressedSize != 0: ri.append('compressedSize_nonzero_without_consumer')
            if pData != 0: ri.append('pData_nonzero_in_static_table')
            if relOffset % 4: ri.append('relOffset_not_aligned4')
            if actualSize % 4: ri.append('actualSize_not_aligned4')
        else:
            rec['class'] = 'unsupported_flags'
            ri.append('flags_not_zero_or_external')
        rec['issues'] = ri
        val_issues.extend({'slot': i, 'issue': x} for x in ri)
        records.append(rec)

    externals = [r for r in records if r['class'] == 'external' and not r['issues']]
    first_payload = min((r['relOffset'] for r in externals), default=None)
    payloads = []
    for r in externals:
        payloads.append({'slot': r['slot'], 'offset': r['relOffset'],
                         'offset_hex': r['relOffset_hex'], 'length': r['actualSize'],
                         'compressedSize': r['compressedSize'], 'pData': r['pData_hex'],
                         'flags': r['flags_hex'], 'sha256': r['filehash']})
    payloads.sort(key=lambda p: p['offset'])

    prev = json.loads(PREV.read_text()) if PREV.exists() else None
    cross = {'previous_file': str(PREV), 'found': prev is not None, 'identical': None, 'detail': {}}
    if prev:
        prev_pl = {(p['slot'], p['offset'], p['length'], p['sha256']) for p in prev.get('payloads', [])}
        new_pl = {(p['slot'], p['offset'], p['length'], p['sha256']) for p in payloads}
        cross['identical'] = (prev_pl == new_pl)
        cross['detail'] = {'previous_count': len(prev_pl), 'new_count': len(new_pl),
                           'only_previous': sorted(prev_pl - new_pl), 'only_new': sorted(new_pl - prev_pl)}

    flag_counts = Counter(r['flags'] for r in records)
    pdata_values = Counter(r['pData'] for r in records)
    comp_values = Counter(r['compressedSize'] for r in records)

    # ---- GSP pairing search ----
    gsp = GSP.read_bytes() if GSP.exists() else b''
    fp_bytes = struct.pack('<Q', fingerprint)
    ne_bytes = struct.pack('<I', num_entries)
    gsp_hits = find_all(gsp, fp_bytes)
    gsp_ne_fp = find_all(gsp, ne_bytes + fp_bytes)
    gsp_fp_ne = find_all(gsp, fp_bytes + ne_bytes)

    elf_map = {}
    if ELF_MAP.exists():
        elf_map = json.loads(ELF_MAP.read_text())
    sections = elf_map.get('sections', [])

    def locate(o):
        for s in sections:
            so, ss = s.get('offset', 0), s.get('size', 0)
            if ss > 0 and so <= o < so + ss:
                return {'section': s.get('name'), 'section_index': s.get('index'),
                        'file_offset': o, 'section_va': s.get('va') + (o - so),
                        'global_va': 0x40000000 + (o - 64)}
        return {'section': None, 'section_index': None, 'file_offset': o,
                'section_va': None, 'global_va': 0x40000000 + (o - 64)}

    def ctx(o):
        a = max(0, o - 24); b = min(len(gsp), o + len(fp_bytes) + 24)
        return {'start': a, 'end': b, 'hex': gsp[a:b].hex()}

    gsp_pairing = {
        'gsp_file': str(GSP), 'gsp_size': len(gsp),
        'fingerprint64': fingerprint, 'fingerprint64_hex': '0x%016X' % fingerprint,
        'fingerprint64_le_hex': fp_bytes.hex(),
        'numEntries': num_entries, 'numEntries_le_hex': ne_bytes.hex(),
        'fingerprint_literal_hits': len(gsp_hits),
        'fingerprint_hits': [locate(o) | ctx(o) for o in gsp_hits],
        'numEntries_immediately_before_fingerprint': gsp_ne_fp,
        'fingerprint_immediately_before_numEntries': gsp_fp_ne,
        'adjacent_pairs': len(gsp_ne_fp) + len(gsp_fp_ne),
        'conclusion': 'literal_match' if gsp_hits else 'no_literal_match_count_0',
        'note': 'No literal match => count written as 0; compiler may construct the constant; no pairing-mismatch conclusion; engine name not assigned from index.',
    }

    report = {
        'script': 'firmware_container_source_verify.py',
        'rerun': '/usr/bin/python3 firmware_container_source_verify.py  (cwd PHASE16)',
        'log': 'firmware_container_source_verify_run.log',
        'input_file': str(BIN), 'input_size': size, 'input_sha256': inhash,
        'source_header': str(SRC_H), 'source_header_sha256': srchash,
        'source_lines': {'flag_defines': '55-59', 'BINDATA_STORAGE_PVT_struct': '60-67',
                         'BINDATA_UCODES_BIN_HEADER_struct': '84-114',
                         'numEntries_comment': '98-103', 'fingerprint_comment': '105-110'},
        'manifest_entries': [{k: m.get(k) for k in ('file', 'sha256', 'official_source_url', 'release_provenance')} for m in manifest],
        'struct_meaning_from_source': {
            'header': '<8sIIQ = magic NvU64 NVUCODES, version NvU32, numEntries NvU32 (possible bindata files at build), fingerprint NvU64 (hash of filenames in index order)',
            'record': '<IIQII = actualSize u32, compressedSize u32, pData pointer64, flags u32, relOffset u32 (24 B)',
            'flags_4': 'BINDATA_FLAG_EXTERNAL (not an enum "present")',
            'numEntries_meaning': 'number of possible bindata files this driver release can have; known at build time; embedded in gsp.bin',
            'fingerprint_meaning': 'hash of all possible filenames in index order; pairing ucodes.bin<->gsp.bin broken if changed; NOT a payload hash or signature',
        },
        'validation': {'magic': magic == b'NVUCODES', 'version': version == 1,
                       'numEntries': num_entries, 'table_end': table_end,
                       'table_end_hex': '0x%X' % table_end, 'table_within_file': table_end <= size,
                       'issues': val_issues},
        'first_payload': first_payload,
        'first_payload_hex': None if first_payload is None else '0x%X' % first_payload,
        'first_payload_derived_not_hardcoded': True,
        'padding_to_first_payload': (first_payload - table_end) if first_payload is not None else None,
        'record_counts': dict(Counter(r['class'] for r in records)),
        'flag_counts': {hex(k): v for k, v in sorted(flag_counts.items())},
        'pData_values': {hex(k): v for k, v in sorted(pdata_values.items())},
        'compressedSize_values': {hex(k): v for k, v in sorted(comp_values.items())},
        'records': records,
        'payloads': payloads,
        'cross_check_vs_previous_artifact': cross,
        'gsp_pairing': gsp_pairing,
    }
    OUT.write_text(json.dumps(report, indent=2))
    print('HEADER magic=%s version=%d numEntries=%d fingerprint=0x%016X' % (magic.decode(), version, num_entries, fingerprint))
    print('TABLE_END %d (0x%X) FIRST_PAYLOAD %s PAD %s' % (table_end, table_end, first_payload, (first_payload - table_end) if first_payload is not None else None))
    print('CLASSES %s' % dict(Counter(r['class'] for r in records)))
    print('FLAGS %s' % {hex(k): v for k, v in sorted(flag_counts.items())})
    print('PAYLOADS %d FIRST %s' % (len(payloads), hex(first_payload) if first_payload is not None else None))
    print('CROSS_IDENTICAL %s DETAIL %s' % (cross['identical'], cross['detail']))
    print('GSP fingerprint_hits %d adjacent_pairs %d conclusion=%s' % (len(gsp_hits), gsp_pairing['adjacent_pairs'], gsp_pairing['conclusion']))
    print('WROTE', OUT)

if __name__ == '__main__':
    main()
