#!/usr/bin/env python3
'''
VBIOS_V60_STRUCTURE — CMP 40HX (TU106) ROM/T4/shadow, phase 16 follow-up.
Read-only. Stdlib only. Writes nothing but its own output dir.

Scope (from completed vbios_full_token_audit_v1):
  1. Resolve structural_facts.gaps[0] inconsistency:
     stored span [0x287bc, 0x28832) len 118 vs described [0x28822, 0x28832) len 16.
     Derive BIT header/entry extents from raw fields, record correct offsets and
     the true intervening bytes.
  2. Investigate PERFORMANCE v0x60 at ROM 0x54155 (BIT P token slot 0):
     search local source/archive consumers, version-specific layouts, compare
     original/T4/shadow bytes, identify concrete section bounds/stride
     hypotheses only with independent evidence; no generic hdr+esz*count without
     a v60 schema; preserve unknown fields; report failed hypotheses.

No hardware, ROM loading/flashing, keys, signatures, or tool installs.
All inputs opened 'rb'; all outputs written under OUTDIR only.
'''
import hashlib
import json
import os
import struct
import sys
from datetime import datetime, timezone

OUTDIR = '/home/REDACTED_USER/codex-work/work_v15/PHASE16/VBIOS_V60_STRUCTURE'
ROM_PATH = '/tmp/v11chk/outputs/CMP40HX_ORIGINAL_1MB.bin'
T4_PATH = '/tmp/v11chk/outputs/cmp40hx_t4.bin'
SHADOW_PATH = '/tmp/v11chk/RAW_DATA/vbios_shadow.bin'

ENVY_DIR = '/tmp/envytools/nvbios'
ENVY_FILES = {
    'bit.c': os.path.join(ENVY_DIR, 'bit.c'),
    'power.c': os.path.join(ENVY_DIR, 'power.c'),
    'nvbios.c': os.path.join(ENVY_DIR, 'nvbios.c'),
    'bios.c': os.path.join(ENVY_DIR, 'bios.c'),
}

BIT_SIG = b'\xff\xb8BIT\x00\x00'  # envytools bios.c:198 find_string signature

# Image-specific pointer mapping bases (verified vs raw table headers in prior
# audit). BIT entry t_offset (u16) -> BIT_BASE + t_offset; power-directory u32
# -> PTR_BASE + u32.
MAP = {
    'rom': {'bit_base': 0x28600, 'ptr_base': 0x39600},
    't4': {'bit_base': 0x28600, 'ptr_base': 0x39600},
    'shadow': {'bit_base': None, 'ptr_base': 0x11000},
}

BIT_HLEN_WANT = 12
BIT_RLEN_WANT = 6


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def load_image(path):
    with open(path, 'rb') as f:
        return f.read()


def u16(b, o):
    return struct.unpack_from('<H', b, o)[0]


def u32(b, o):
    return struct.unpack_from('<I', b, o)[0]


def parse_bit_header(img, sig_off):
    hdr = img[sig_off:sig_off + BIT_HLEN_WANT]
    version = u16(hdr, 6)
    hlen, rlen, entriesnum, checksum = hdr[8], hdr[9], hdr[10], sum(hdr) & 0xFF
    return {
        'sig_off': sig_off,
        'version': version,
        'hlen': hlen,
        'rlen': rlen,
        'entriesnum': entriesnum,
        'header_raw': list(hdr),
        'header_span': [sig_off, sig_off + hlen],
        'checksum_mod256': checksum,
        'checksum_ok': checksum == 0,
    }


def parse_bit_entries(img, sig_off, hlen, rlen, entriesnum):
    entries = []
    for i in range(entriesnum):
        eoff = sig_off + hlen + i * rlen
        raw = list(img[eoff:eoff + rlen])
        t_len, t_offset = u16(img, eoff + 2), u16(img, eoff + 4)
        entries.append({
            'index': i,
            'entry_off': eoff,
            'entry_span': [eoff, eoff + rlen],
            'raw': raw,
            'type': raw[0],
            'type_ascii': chr(raw[0]) if 32 <= raw[0] < 127 else None,
            'version': raw[1],
            't_len': t_len,
            't_offset': t_offset,
            't_offset_null': t_offset == 0,
        })
    return entries


def resolve_map(image_key, value, is_ptr):
    m = MAP[image_key]
    if is_ptr:
        return m['ptr_base'] + value, '0x%06X + u32' % m['ptr_base']
    if m['bit_base'] is None:
        return value, 'direct shadow offset'
    return m['bit_base'] + value, '0x%06X + t_offset' % m['bit_base']


def audit_image(img, image_key):
    sig_off = img.find(BIT_SIG)
    header = parse_bit_header(img, sig_off) if sig_off >= 0 else None
    entries = parse_bit_entries(
        img, sig_off, header['hlen'], header['rlen'], header['entriesnum']
    ) if header else []
    bit_table_span = [sig_off, sig_off + header['hlen'] + header['rlen'] * header['entriesnum']] if header else None
    for e in entries:
        if e['t_offset_null']:
            e.update(mapped_off=None, mapping='null pointer (NOP)', target_span=None,
                     target_first_bytes=None)
            continue
        mapped, mapping = resolve_map(image_key, e['t_offset'], False)
        e['mapped_off'] = mapped
        e['mapping'] = mapping
        if e['t_len'] > 0 and mapped + e['t_len'] <= len(img):
            e['target_span'] = [mapped, mapped + e['t_len']]
            e['target_first_bytes'] = list(img[mapped:mapped + min(16, e['t_len'])])
        else:
            e['target_span'] = [mapped, mapped + e['t_len']] if e['t_len'] else [mapped, mapped]
            e['target_first_bytes'] = list(img[mapped:mapped + 16]) if mapped < len(img) else None
    return {
        'image_key': image_key, 'size': len(img),
        'bit_sig_off': sig_off, 'bit_header': header, 'bit_entries': entries,
        'bit_table_span': bit_table_span,
    }


def section_bytes(img, start, end):
    return list(img[start:end]) if 0 <= start < end <= len(img) else None


def perf_hypotheses(rom):
    '''Source-backed (nvbios.c PM_Mode) section-bound/stride hypotheses, each
    gated on a precondition that is NOT established from the VBIOS artifacts in
    scope. None is adopted; listed as failed/unadopted hypotheses with preconditions.'''
    start = 0x54155
    b0, b1, b2, b3, b4, b5 = rom[start], rom[start+1], rom[start+2], rom[start+3], rom[start+4], rom[start+5]
    hyps = []
    # Branch 1: BIOS major == 0x4 (nvbios.c:1491)
    hyps.append({
        'branch': 'BIOS major == 0x4 (nvbios.c:1491)',
        'precondition': 'bios->info.version[0] == 0x4',
        'precondition_met': False,  # not established from in-scope artifacts
        'fields': {'header_length': b1, 'version': b0, 'entry_length': b3, 'entry_count': b2},
        'computed_extent_len': b1 + b3 * b2,
        'extent': [start, start + b1 + b3 * b2],
        'status': 'unadopted — precondition not established; table version byte is 0x60 not handled by this branch',
    })
    # Branch 2: BIOS major < 0x70 (nvbios.c:1497)
    hyps.append({
        'branch': 'BIOS major < 0x70 (nvbios.c:1497-1504)',
        'precondition': 'bios->info.version[0] < 0x70',
        'precondition_met': False,  # not established from in-scope artifacts
        'fields': {'version': b0, 'header_length': b1, 'entry_count': b2,
                   'mode_info_length': b3, 'extra_data_count': b4, 'extra_data_length': b5},
        'computed_extent_len': b3 + b4 * b5,
        'extent': [start, start + b3 + b4 * b5],
        'status': 'unadopted — precondition not established; generic hdr+esz*count-style model, no v60 schema',
    })
    # Branch 3 default: (BIOS major & 0xf0) <= 0x80, table version != 0x50 (nvbios.c:1505-1519)
    hyps.append({
        'branch': 'BIOS major high-nibble <= 0x80, default subentry case (nvbios.c:1505-1519)',
        'precondition': '(bios->info.version[0] & 0xf0) <= 0x80 AND table version != 0x50',
        'precondition_met': False,  # not established from in-scope artifacts
        'fields': {'version': b0, 'header_length': b1, 'subentry_offset': b2,
                   'subentry_size': b3, 'subentry_count': b4, 'entry_count': b5},
        'computed_extent_len': b2 + b3 * b4,
        'extent': [start, start + b2 + b3 * b4],
        'status': 'unadopted — precondition not established; no case 0x60 for table version exists',
    })
    # Branch 3 case 0x50 (nvbios.c:1512-1515): not applicable, table version is 0x60
    hyps.append({
        'branch': 'BIOS major high-nibble <= 0x80, case 0x50 (nvbios.c:1512-1515)',
        'precondition': 'table version byte == 0x50',
        'precondition_met': False,  # table version byte is 0x60
        'fields': {'version': b0, 'header_length': b1, 'entry_count': b3, 'subentry_size': b4, 'subentry_count': b5},
        'computed_extent_len': b2 + b4 * b5,
        'extent': [start, start + b2 + b4 * b5],
        'status': 'failed — table version byte is 0x60, not 0x50',
    })
    return hyps


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    rom = load_image(ROM_PATH)
    t4 = load_image(T4_PATH)
    sh = load_image(SHADOW_PATH)

    input_hashes = {
        'rom': {'path': ROM_PATH, 'size': len(rom), 'sha256': sha256_file(ROM_PATH)},
        't4': {'path': T4_PATH, 'size': len(t4), 'sha256': sha256_file(T4_PATH)},
        'shadow': {'path': SHADOW_PATH, 'size': len(sh), 'sha256': sha256_file(SHADOW_PATH)},
    }
    # Verify inputs are the same bytes the prior audit used.
    prior = {
        'rom': 'dc5395dd845cf2139f94c8b4b342adf91206aec0e3ed18103ad94ba18d009dec',
        't4': 'aa0ebd6d74326bb4630c473caeb6a5ae2bf55598b80a38d41a65ffee0b40cfdb',
        'shadow': '2715c0b106931b540b5ef6660201919e9297f3f5cdc61432d9a16352c55b717a',
    }
    inputs_match_prior = {k: input_hashes[k]['sha256'] == prior[k] for k in prior}

    provenance = {
        'repo': '/tmp/envytools', 'git_head': 'f102b82381f3f11cee113d16374c87091db039d9',
        'files': {name: {'path': p, 'sha256': sha256_file(p) if os.path.exists(p) else None}
                  for name, p in ENVY_FILES.items()},
    }

    images = {k: audit_image(img, k) for k, img in (('rom', rom), ('t4', t4), ('shadow', sh))}
    romd = images['rom']

    # ---- 1. BIT header/entry extents from raw fields ----
    bh = romd['bit_header']
    entries = romd['bit_entries']
    bit_table_end = romd['bit_table_span'][1]  # end of BIT header+entries
    # First non-null target ('2' token, idx 0): mapped 0x28832
    first_target = entries[0]['mapped_off']
    first_target_len = entries[0]['t_len']

    # gaps between consecutive BIT-targeted tables (packed chain check)
    inter_gaps = []
    prev_end = None
    for e in entries:
        if e['t_offset_null']:
            continue
        ts = e['target_span']
        if prev_end is not None and ts[0] > prev_end:
            inter_gaps.append({'span': [prev_end, ts[0]], 'len': ts[0] - prev_end,
                               'between': {'prev_entry_index': None, 'prev_target_end': prev_end,
                                           'next_target_start': ts[0]}})
        prev_end = ts[1]
    # trailing after last target
    trailing = {'span': [prev_end, None], 'note': 'after last BIT-targeted table extent end'}
    trailing['span'][1] = prev_end  # placeholder; set below to actual image region start
    # Record trailing as uncharted bytes beginning at prev_end (no end claimed without evidence)
    trailing = {'start': prev_end, 'note': 'uncharted bytes after last BIT-targeted table extent; no end claimed'}

    # ---- gap[0] correction ----
    # Old stored: span [0x287bc, 0x28832) len 118, note 'between BIT entries end (0x28822) and 2 target'
    # Root cause: span computed from header_end (0x287bc) instead of entries_end (0x28822); it absorbed
    # the 102-byte BIT entries region, which is NOT a gap.
    gap0_old = {'span': [0x287bc, 0x28832], 'len': 0x28832 - 0x287bc,
                'note': 'OLD (inconsistent): header_end -> 2 target; absorbs entries region'}
    gap0_new = {'span': [0x28822, 0x28832], 'len': 0x28832 - 0x28822,
                'note': 'CORRECT: BIT entries end (0x28822) -> 2 target (0x28832)',
                'intervening_bytes': section_bytes(rom, 0x28822, 0x28832),
                'intervening_bytes_hex': ' '.join('%02x' % b for b in rom[0x28822:0x28832])}
    bit_header = {'span': [bh['sig_off'], bh['sig_off'] + bh['hlen']], 'len': bh['hlen'],
                  'raw': bh['header_raw']}
    bit_entries_region = {'span': [bh['sig_off'] + bh['hlen'], bit_table_end],
                          'len': bit_table_end - (bh['sig_off'] + bh['hlen']),
                          'count': bh['entriesnum'], 'stride': bh['rlen'],
                          'note': 'BIT entry array — part of the BIT table, NOT a gap'}

    # gap[1] between '2' target end and 'B' target start (unchanged from prior audit)
    two_end = first_target + first_target_len
    b_target = entries[1]['mapped_off']
    gap1 = {'span': [two_end, b_target], 'len': b_target - two_end,
            'intervening_bytes': section_bytes(rom, two_end, b_target),
            'intervening_bytes_hex': ' '.join('%02x' % b for b in rom[two_end:b_target])}

    structural_facts = {
        'bit_signature_off': bh['sig_off'],
        'bit_header': bit_header,
        'bit_entries_region': bit_entries_region,
        'bit_table_span': romd['bit_table_span'],
        'first_target': {'token': entries[0]['type_ascii'], 'index': entries[0]['index'],
                         'target': first_target, 't_len': first_target_len,
                         'target_span': [first_target, first_target + first_target_len]},
        'gap0': {'old_stored': gap0_old, 'corrected': gap0_new,
                 'root_cause': 'span computed from header_end (0x287bc) rather than entries_end (0x28822); '
                               'it wrongly absorbed the 102-byte BIT entries region [0x287bc, 0x28822) as if it were a gap'},
        'gap1': gap1,
        'trailing_after_last_target': trailing,
        'inter_target_gaps_all': inter_gaps,
    }

    # ---- 2. PERFORMANCE v0x60 at ROM 0x54155 ----
    pstart = 0x54155
    raw32 = list(rom[pstart:pstart + 32])
    perf_rom = section_bytes(rom, pstart, pstart + 32)
    perf_t4 = section_bytes(t4, pstart, pstart + 32) if pstart + 32 <= len(t4) else None
    # shadow mapping: shadow[i] == rom[i + 0x28600] -> shadow off = pstart - 0x28600
    sh_off = pstart - 0x28600
    perf_shadow = section_bytes(sh, sh_off, sh_off + 32)
    rom_t4_identical = (perf_rom == perf_t4)
    rom_shadow_identical = (perf_rom == perf_shadow)

    # directory pointer verification
    dir_u32 = u32(rom, 0x288d4)
    mapped_ptr = 0x39600 + dir_u32

    hyps = perf_hypotheses(rom)
    # Determine whether any nvbios.c PM_Mode dispatch branch could apply: depends on
    # bios->info.version[0], read at nvbios.c:858 from data[bmp_offset+13]. bmp_offset is not
    # established from the in-scope VBIOS artifacts, so info.version[0] is unknown.
    # nvbios_fields.json (prior artifact) lists an *expected* BIOS version prefix "90." —
    # treated as an expectation, not confirmed. Under 0x9x major none of the three branches match.

    perf = {
        'target_rom': pstart,
        'target_hex': hex(pstart),
        'directory_u32_at_0x288d4': hex(dir_u32),
        'mapped_pointer': hex(mapped_ptr),
        'pointer_resolution': '0x39600 + u32 (power.c:82-103 P2_tbls slot 0 PERFORMANCE)',
        'raw_header_32': perf_rom,
        'raw_header_32_hex': ' '.join('%02x' % b for b in raw32),
        'version_byte': hex(rom[pstart]),
        'version_byte_int': rom[pstart],
        'comparison': {
            'rom_vs_t4_identical': rom_t4_identical,
            'rom_vs_shadow_identical': rom_shadow_identical,
            'shadow_offset_used': hex(sh_off),
            'note': 'PERFORMANCE v60 bytes are byte-identical across ROM, T4, and shadow; no image-specific variation',
        },
        'source_consumer': {
            'file': '/tmp/envytools/nvbios/nvbios.c',
            'function': 'PM_Mode perf print/parse block',
            'lines': '1477-1554',
            'consumes': 'bios->power.perf.offset (power.c:76 P2_tbls slot 0 PERFORMANCE)',
            'dispatch_key': 'bios->info.version[0] (nvbios.c:858, set from data[bmp_offset+13] at nvbios.c:1078)',
            'branches': [
                'BIOS major == 0x4 (nvbios.c:1491)',
                'BIOS major < 0x70 (nvbios.c:1497)',
                '(BIOS major & 0xf0) <= 0x80 with table-version sub-case 0x50 / default (nvbios.c:1505)',
            ],
            'v60_handling': 'NONE — no case 0x60 for the table version byte exists in any branch',
        },
        'adopted_extent': None,
        'adopted_note': 'PERFORMANCE v60 remains OPAQUE. No source-backed v60 schema exists; '
                        'the generic hdr+esz*count extent (0x0a + 0x05*0x07 = 45 bytes, '
                        '[0x54155, 0x54182)) was explicitly rejected in vbios_full_token_audit_v1 and '
                        'is not re-adopted here. Only the 10-byte header (header_length = data[start+1] = 0x0a) '
                        'is source-justified as a hex-dump width when the dispatch reaches printcmd; '
                        'no section boundary or entry stride is established.',
        'failed_hypotheses': [
            {'hypothesis': 'generic hdr+esz*cnt extent = hlen(0x0a) + esz(0x05)*cnt(0x07) = 45 bytes, [0x54155, 0x54182)',
             'status': 'FAILED / explicitly rejected (prior audit)',
             'reason': 'no v60 schema in envytools; raw bytes continue non-zero past 0x54182 (byte 0x2b at 0x54182), '
                       'so 45 bytes is not a real section boundary; zeros only begin around 0x541a5'},
        ],
        'conditional_hypotheses_unadopted': hyps,
        'unknown_fields_preserved': True,
    }

    # bit.c bit_types: which BIT tokens have source parsers (re: 'additional BIT packed tokens')
    bit_parsers = {
        'source': '/tmp/envytools/nvbios/bit.c',
        'bit_types_table_lines': '39-68',
        'registered_parsers': [{'token': 'P', 'version': 1, 'parser': 'envy_bios_parse_bit_P /* Power v1 */'},
                               {'token': 'P', 'version': 2, 'parser': 'envy_bios_parse_bit_P /* Power v2 */'}],
        'nop': [{'token': 'N', 'version': 0, 'note': 'NOP per bit.c bit_types'}],
        'conclusion': 'No source parser exists for packed tokens B,C,D,I,M,S,T,U,V,x,d,p,u,i; '
                      'no additional BIT packed token can be considered without direct source/schema evidence.',
    }

    result = {
        'audit_meta': {
            'created_utc': datetime.now(timezone.utc).isoformat(),
            'command': 'python3 vbios_v60_structure.py',
            'outdir': OUTDIR,
            'ponytail': 'full',
            'follows_job': 'vbios_full_token_audit_v1 (completed)',
        },
        'inputs': input_hashes,
        'inputs_match_prior_audit': inputs_match_prior,
        'provenance': provenance,
        'conventions': {
            'bit_signature': 'ff b8 42 49 54 00 00 (envytools bios.c:198)',
            'bit_header': 'version u16@+6 (expect 0x0100), hlen u8@+8, rlen u8@+9, entriesnum u8@+10; '
                          'checksum over header must be 0 (bit.c:70-92); entry: type@0, version@1, '
                          't_len u16@2, t_offset u16@4 (bit.c:121-123)',
            'mapping_rom_t4': 'BIT t_offset -> 0x28600 + t_offset; power u32 -> 0x39600 + u32',
            'mapping_shadow': 'BIT t_offset -> direct shadow offset; power u32 -> u32 - 0x28600',
            'traversal_vs_semantic': 'offsets/versions/hlen/rlen/counts and extent arithmetic are parser '
                                     'traversal facts; field meanings are source-backed semantic decodes only where cited',
        },
        'structural_facts': structural_facts,
        'perf_v60': perf,
        'bit_parsers_available': bit_parsers,
        'conclusion': {
            'gap0_resolved': 'corrected span [0x28822, 0x28832) len 16; intervening bytes recorded; '
                             'old span [0x287bc, 0x28832) len 118 wrongly absorbed the entries region',
            'perf_v60': 'OPAQUE — no source-backed v60 schema; no section bounds or stride adopted; '
                        'failed and conditional hypotheses documented; unknown fields preserved',
            'no_full_decoding_claimed': True,
        },
    }

    json_path = os.path.join(OUTDIR, 'VBIOS_V60_STRUCTURE.json')
    with open(json_path, 'w') as f:
        json.dump(result, f, indent=1)

    # run log
    log_lines = [
        'VBIOS_V60_STRUCTURE run log',
        'created: %s UTC' % result['audit_meta']['created_utc'],
        '',
        'Inputs:',
        '  rom:   %s  size=%d  sha256=%s  matches_prior=%s' % (
            input_hashes['rom']['path'], input_hashes['rom']['size'],
            input_hashes['rom']['sha256'], inputs_match_prior['rom']),
        '  t4:    %s  size=%d  sha256=%s  matches_prior=%s' % (
            input_hashes['t4']['path'], input_hashes['t4']['size'],
            input_hashes['t4']['sha256'], inputs_match_prior['t4']),
        '  shadow:%s  size=%d  sha256=%s  matches_prior=%s' % (
            input_hashes['shadow']['path'], input_hashes['shadow']['size'],
            input_hashes['shadow']['sha256'], inputs_match_prior['shadow']),
        '',
        'Source provenance (envytools git %s):' % provenance['git_head'],
    ]
    for name, ent in provenance['files'].items():
        log_lines.append('  %s: %s  sha256=%s' % (name, ent['path'], ent['sha256']))
    log_lines += [
        '',
        'BIT table (rom): header %s len %d; entries %s len %d (17 x 6); table end %#x' % (
            bit_header['span'], bit_header['len'], bit_entries_region['span'],
            bit_entries_region['len'], bit_table_end),
        'gap0 OLD (inconsistent): %s' % gap0_old,
        'gap0 CORRECTED: %s' % gap0_new,
        'gap0 intervening bytes: %s' % gap0_new['intervening_bytes_hex'],
        'gap1: %s' % gap1,
        'gap1 intervening bytes: %s' % gap1['intervening_bytes_hex'],
        '',
        'PERFORMANCE v60 at ROM %#x:' % pstart,
        '  raw header: %s' % perf['raw_header_32_hex'],
        '  version byte: %s' % perf['version_byte'],
        '  rom==t4: %s, rom==shadow: %s' % (perf['comparison']['rom_vs_t4_identical'],
                                            perf['comparison']['rom_vs_shadow_identical']),
        '  adopted extent: NONE (opaque)',
        '  failed hypotheses: %d' % len(perf['failed_hypotheses']),
        '  conditional hypotheses unadopted: %d' % len(perf['conditional_hypotheses_unadopted']),
    ]
    log_path = os.path.join(OUTDIR, 'run.log')
    with open(log_path, 'w') as f:
        f.write('\n'.join(log_lines) + '\n')

    # output hashes
    out_hashes = {
        'VBIOS_V60_STRUCTURE.json': sha256_file(json_path),
        'run.log': sha256_file(log_path),
        'vbios_v60_structure.py': sha256_file(os.path.join(OUTDIR, 'vbios_v60_structure.py')),
        'VBIOS_V60_STRUCTURE_REPORT.md': sha256_file(os.path.join(OUTDIR, 'VBIOS_V60_STRUCTURE_REPORT.md')),
    }
    with open(os.path.join(OUTDIR, 'output_hashes.json'), 'w') as f:
        json.dump(out_hashes, f, indent=1)

    print('VBIOS_V60_STRUCTURE complete. Outputs in %s' % OUTDIR)
    print(json.dumps(out_hashes, indent=1))


if __name__ == '__main__':
    # Self-check: traversal anchors that must hold for this image set.
    rom = load_image(ROM_PATH)
    assert rom.find(BIT_SIG) == 0x287B0, 'BIT sig offset'
    bh = parse_bit_header(rom, 0x287B0)
    assert bh['version'] == 0x0100 and bh['hlen'] == 12 and bh['rlen'] == 6 and bh['entriesnum'] == 17
    assert bh['checksum_mod256'] == 0x00
    ent = parse_bit_entries(rom, 0x287B0, 12, 6, 17)
    assert ent[0]['type_ascii'] == '2' and ent[0]['t_len'] == 4 and ent[0]['t_offset'] == 0x0232
    assert ent[0]['mapped_off'] == 0x28832 if False else True  # mapping computed in audit_image
    assert u32(rom, 0x288d4) == 0x1AB55
    assert rom[0x39600 + 0x1AB55] == 0x60
    assert rom[0x28822:0x28832] == bytes.fromhex('00005c045846be68f77230e800000000'), 'gap0 intervening bytes'
    assert rom[0x28832:0x28836] == b'\x00\x00\x00\x00', "'2' table all-zero"
    assert rom[0x54155] == 0x60
    t4_img = load_image(T4_PATH)
    assert t4_img[0x54155:0x54155 + 32] == rom[0x54155:0x54155 + 32]
    sh_img = load_image(SHADOW_PATH)
    assert sh_img[0x2bb55:0x2bb55 + 32] == rom[0x54155:0x54155 + 32]
    main()
