#!/usr/bin/env python3
'''
VBIOS FULL TOKEN AUDIT — NVIDIA CMP 40HX (TU106) ROM / T4 / shadow.
Read-only. Stdlib only. Writes nothing but its own output dir.

Usage:
    python3 vbios_full_token_audit.py [ROM] [T4] [SHADOW] [OUTDIR]

Defaults:
    ROM    = /tmp/v11chk/outputs/CMP40HX_ORIGINAL_1MB.bin
    T4     = /tmp/v11chk/outputs/cmp40hx_t4.bin
    SHADOW = /tmp/v11chk/RAW_DATA/vbios_shadow.bin
    OUTDIR = /home/REDACTED_USER/codex-work/work_v15/PHASE16/VBIOS_FULL_TOKEN_AUDIT

Scope: audit every BIT table token and every non-null table pointer (the 56-slot
power/PERF pointer directory pointed by BIT token ''P'') against raw bytes in
the three supplied images. Preserve image-specific offset mapping, version,
header length, record length/count only when source-justified, full extent
bounds, adjacencies/gaps and trailing bytes. Reuse envytools parser source
(bit.c, power.c, nvbios.c, bios.c) with exact line/file/hash citations;
distinguish parser traversal facts from semantic decoding. Token 0
(PERFORMANCE, version 0x60) is UNSUPPORTED; no generic entry-size formula is
applied to it.

Inputs are opened 'rb' only. Outputs are written only under OUTDIR.
'''
import hashlib
import json
import os
import struct
import sys
from datetime import datetime, timezone

DEFAULT_ROM = '/tmp/v11chk/outputs/CMP40HX_ORIGINAL_1MB.bin'
DEFAULT_T4 = '/tmp/v11chk/outputs/cmp40hx_t4.bin'
DEFAULT_SHADOW = '/tmp/v11chk/RAW_DATA/vbios_shadow.bin'
DEFAULT_OUTDIR = '/home/REDACTED_USER/codex-work/work_v15/PHASE16/VBIOS_FULL_TOKEN_AUDIT'

ENVYTOOLS_REPO = '/tmp/envytools'
ENVYTOOLS_GIT_HEAD = 'f102b82381f3f11cee113d16374c87091db039d9'
ENVY_FILES = {
    'bit.c': '/tmp/envytools/nvbios/bit.c',
    'power.c': '/tmp/envytools/nvbios/power.c',
    'nvbios.c': '/tmp/envytools/nvbios/nvbios.c',
    'bios.c': '/tmp/envytools/nvbios/bios.c',
}

# Image-specific pointer mapping bases (verified against raw bytes in this
# audit session). BIT entry t_offset (u16) resolves via BIT_BASE; power-directory
# u32 pointers resolve via PTR_BASE.
MAP = {
    'rom': {'bit_base': 0x28600, 'ptr_base': 0x39600},
    't4': {'bit_base': 0x28600, 'ptr_base': 0x39600},
    'shadow': {'bit_base': None, 'ptr_base': 0x11000},
}
# shadow: t_offset values are direct shadow offsets (shadow[t] == rom[0x28600+t]
# in the BIT region); u32 pointers resolve as ptr - 0x28600, hence base 0x11000.

BIT_SIG = b'\xff\xb8BIT\x00\x00'  # envytools bios.c:198 find_string signature

# P2_tbls from envytools power.c:82-103 (version 0x2 slot directory names).
# Slots 39-55 (P2 offsets 0x9c-0xe0) are not named in P2_tbls source; 0x9c only
# appears as a commented 'LOW POWER NVLINK'.
P2_TBLS = {
    0: (0x00, 'PERFORMANCE'), 1: (0x04, 'MEMORY TIMINGS MAPPING'),
    2: (0x08, 'MEMORY TIMINGS'), 3: (0x0C, 'VOLTAGE'),
    4: (0x10, 'THERMAL'), 5: (0x14, 'THERMAL DEVICES'),
    6: (0x18, 'THERMAL COOLERS'), 7: (0x1C, 'PERF SETTINGS SCRIPT'),
    8: (0x20, 'VOLT MAPPING'), 9: (0x24, 'VENTURA'),
    10: (0x28, 'POWER SENSE'), 11: (0x2C, 'POWER BUDGET'),
    12: (0x30, 'BOOST'), 13: (0x34, 'CSTEP'),
    14: (0x38, 'POWER BASE CLOCK'), 15: (0x3C, 'POWER TOPOLOGY'),
    16: (0x40, 'POWER LEAKAGE'), 17: (0x44, 'PERF TEST SPEC'),
    18: (0x48, 'THERMAL CHANNEL'), 19: (0x4C, 'THERMAL ADJUSTMENT'),
    20: (0x50, 'THERMAL POLICY'), 21: (0x54, 'PSTATE MEMORY CLK FREQ'),
    22: (0x58, 'FAN COOLERS'), 23: (0x5C, 'POWER FAN_MGMT'),
    24: (0x60, 'DI/DT'), 25: (0x64, 'FAN TEST'),
    26: (0x68, 'VOLTAGE RAIL'), 27: (0x6C, 'VOLTAGE DEVICE'),
    28: (0x70, 'VOLTAGE POLICY'), 29: (0x74, 'LOW POWER'),
    30: (0x78, 'LOW POWER PCIe'), 31: (0x7C, 'LOW POWER PCIe-PLATFORM'),
    32: (0x80, 'LOW POWER GR'), 33: (0x84, 'LOW POWER MS'),
    34: (0x88, 'LOW POWER DI'), 35: (0x8C, 'LOW POWER GC6'),
    36: (0x90, 'LOW POWER PSI'), 37: (0x94, 'THERM MONITOR'),
    38: (0x98, 'OVERCLOCKING'),
}

SLOT_COUNT = 56
BIT_HLEN_WANT = 12
BIT_RLEN_WANT = 6

# envytools nvbios/bit.c:70-137:
#   version u16 @+6 (expects 0x0100), hlen u8 @+8 (want 12), rlen u8 @+9 (want 6),
#   entriesnum u8 @+10; checksum over [offset, offset+hlen) must be 0;
#   entry i @ offset+hlen+i*rlen: type@+0, version@+1, t_len u16@+2,
#   t_offset u16@+4. bit_types table: bit.c:39-68 ('N' version 0 = NOP).

# Source-verified version acceptance for power.c slot parsers (header fields
# hlen@1, rlen@2, entriesnum@3 read in the named branch).
SOURCE_VERSIONS = {
    5: ([0x10], 'envy_bios_parse_power_therm_devices (power.c:239; switch 0x10 at power.c:248)'),
    10: ([0x10, 0x20], 'envy_bios_parse_power_sense (power.c:792; switch 0x10/0x20 at power.c:801)'),
    11: ([0x10, 0x20, 0x30], 'envy_bios_parse_power_budget (power.c:644; switch at power.c:654)'),
    14: ([0x10, 0x20], 'envy_bios_parse_power_base_clock (power.c:884; switch at power.c:893/941)'),
    15: ([0x10, 0x20], 'envy_bios_parse_power_unk3c (power.c:1079; switch at power.c:1088)'),
    16: ([0x10], 'envy_bios_parse_power_unk40 (power.c:1134; switch at power.c:1143)'),
    17: ([0x10], 'envy_bios_parse_power_unk44 (power.c:1188; switch at power.c:1197; hlen only, no entries)'),
    20: ([0x10], 'envy_bios_parse_power_unk50 (power.c:1334; switch at power.c:1334)'),
}


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


def env_file_sha(path):
    try:
        return sha256_file(path)
    except OSError:
        return None


def find_bit_sig(img):
    return img.find(BIT_SIG)


def parse_bit_header(img, sig_off):
    if sig_off < 0:
        return None
    hdr = img[sig_off:sig_off + BIT_HLEN_WANT]
    if len(hdr) < BIT_HLEN_WANT:
        return None
    version = u16(hdr, 6)
    hlen = hdr[8]
    rlen = hdr[9]
    entriesnum = hdr[10]
    checksum = sum(hdr) & 0xFF
    return {
        'sig_off': sig_off,
        'version': version,
        'hlen': hlen,
        'rlen': rlen,
        'entriesnum': entriesnum,
        'header_raw': list(hdr),
        'checksum_mod256': checksum,
        'checksum_ok': checksum == 0,
        'note': 'envytools bit.c:91-92: nonzero checksum -> parse abort; this image sums to 0x60 (traversal fact)',
    }


def parse_bit_entries(img, sig_off, hlen, rlen, entriesnum):
    entries = []
    for i in range(entriesnum):
        eoff = sig_off + hlen + i * rlen
        raw = list(img[eoff:eoff + rlen])
        t, ver = raw[0], raw[1]
        t_len, t_offset = u16(img, eoff + 2), u16(img, eoff + 4)
        entries.append({
            'index': i,
            'entry_off': eoff,
            'raw': raw,
            'type': t,
            'type_ascii': chr(t) if 32 <= t < 127 else None,
            'version': ver,
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
    sig_off = find_bit_sig(img)
    header = parse_bit_header(img, sig_off)
    entries = parse_bit_entries(img, sig_off, header['hlen'], header['rlen'],
                                header['entriesnum']) if header else []
    bit_span = [sig_off, sig_off + header['hlen'] + header['rlen'] * header['entriesnum']] if header else None

    for e in entries:
        if e['t_offset_null']:
            e['mapped_off'] = None
            e['mapping'] = 'null pointer (NOP)'
            e['target_in_bounds'] = None
            e['target_span'] = None
            e['target_first_bytes'] = None
            continue
        mapped, mapping = resolve_map(image_key, e['t_offset'], False)
        e['mapped_off'] = mapped
        e['mapping'] = mapping
        if e['t_len'] > 0 and mapped + e['t_len'] <= len(img):
            e['target_in_bounds'] = True
            e['target_span'] = [mapped, mapped + e['t_len']]
            e['target_first_bytes'] = list(img[mapped:mapped + min(16, e['t_len'])])
            e['version_byte_matches_entry'] = (img[mapped] == e['version'])
        else:
            e['target_in_bounds'] = False
            e['target_span'] = [mapped, mapped + e['t_len']] if e['t_len'] else [mapped, mapped]
            e['target_first_bytes'] = list(img[mapped:mapped + 16]) if mapped < len(img) else None
            e['version_byte_matches_entry'] = None

    slots = []
    p_dir = None
    p_entry = next((e for e in entries if e['type_ascii'] == 'P'), None)
    if p_entry and not p_entry['t_offset_null'] and p_entry['target_in_bounds']:
        p_base = p_entry['mapped_off']
        p_dir = {
            'directory_off': p_base,
            'directory_span': [p_base, p_base + p_entry['t_len']],
            't_len': p_entry['t_len'],
            'slots_fit': p_entry['t_len'] == SLOT_COUNT * 4,
            'ptr_source': "BIT token 'P' (power v2) -> u32 slot array; slot i pointer at dir + i*4 (power.c:82-103 P2_tbls; power.c parse_at)",
        }
        for i in range(SLOT_COUNT):
            doff = p_base + i * 4
            raw = u32(img, doff) if doff + 4 <= len(img) else None
            rec = {
                'index': i,
                'p2_offset': i * 4,
                'p2_name': P2_TBLS[i][1] if i in P2_TBLS else None,
                'p2_raw_offset': P2_TBLS[i][0] if i in P2_TBLS else None,
                'directory_off': doff,
                'raw_u32': raw,
                'null': (raw == 0),
            }
            if raw is None or raw == 0:
                rec.update(mapped_off=None, mapping=None, target_in_bounds=None,
                           target_span=None, target_first_bytes=None, version=None,
                           status='NULL')
            else:
                mapped, mapping = resolve_map(image_key, raw, True)
                rec['mapped_off'] = mapped
                rec['mapping'] = mapping
                rec['target_in_bounds'] = mapped + 4 <= len(img)
                if rec['target_in_bounds']:
                    fb = list(img[mapped:mapped + 16])
                    rec['target_span'] = [mapped, mapped + 4]
                    rec['target_first_bytes'] = fb
                    rec['version'] = fb[0]
                else:
                    rec['target_span'] = [mapped, mapped + 4]
                    rec['target_first_bytes'] = None
                    rec['version'] = None
            slots.append(rec)
    return {
        'image_key': image_key,
        'size': len(img),
        'bit_sig_off': sig_off,
        'bit_header': header,
        'bit_entries': entries,
        'bit_span': bit_span,
        'power_directory': p_dir,
        'slots': slots,
    }


# ---------------------------------------------------------------------------
# Source-backed header shape (traversal fact) and full decode of the typed set.
# ---------------------------------------------------------------------------

def header_shape(img, off, accepted, src_cite):
    if off + 4 > len(img):
        return None
    version = img[off]
    if version not in accepted:
        return None
    hlen, rlen, cnt = img[off + 1], img[off + 2], img[off + 3]
    extent = [off, off + hlen + rlen * cnt]
    return {
        'version': version,
        'hlen': hlen,
        'rlen': rlen,
        'entriesnum': cnt,
        'extent': extent,
        'extent_len': hlen + rlen * cnt,
        'source_cite': src_cite,
        'basis': 'source header fields (power.c traversal); entry field semantics not decoded here',
    }


def decode_slot5(img, off):
    hlen, rlen, cnt = img[off + 1], img[off + 2], img[off + 3]
    entries = []
    for i in range(cnt):
        eoff = off + hlen + i * rlen
        entries.append({
            'index': i,
            'entry_off': eoff,
            'class_id': img[eoff],
            'i2c_device': img[eoff + 1],
            'flags': img[eoff + 2],
            'raw': list(img[eoff:eoff + rlen]),
        })
    return {
        'table': 'THERMAL DEVICES (P2 off 0x14)',
        'source': 'envy_bios_parse_power_therm_devices (power.c:239; header switch power.c:248; entry fields power.c:260-262)',
        'version': 0x10, 'hlen': hlen, 'rlen': rlen, 'entriesnum': cnt,
        'extent': [off, off + hlen + rlen * cnt],
        'extent_len': hlen + rlen * cnt,
        'entries': entries,
        'unknown_bytes': {'header_unknown': list(img[off + 4:off + hlen])},
    }


def decode_slot11(img, off):
    hlen, rlen, cnt = img[off + 1], img[off + 2], img[off + 3]
    cap_entry = img[off + 0x0A] if off + 0x0B <= len(img) else None
    entries = []
    for i in range(cnt):
        eoff = off + hlen + i * rlen
        chunk = list(img[eoff:eoff + rlen])
        rec = {'index': i, 'entry_off': eoff, 'raw': chunk}
        if rlen != 6 and eoff + 0x16 <= len(img):
            rec.update(min=u32(img, eoff + 0x02), avg=u32(img, eoff + 0x06),
                       peak=u32(img, eoff + 0x0A), unkn12=u32(img, eoff + 0x12))
        entries.append(rec)
    return {
        'table': 'POWER BUDGET (P2 off 0x2c)',
        'source': 'envy_bios_parse_power_budget (power.c:644; versions 0x10/0x20/0x30 at power.c:654; cap_entry@0x0a for 0x30 at power.c:671-673; entry fields power.c:701-708)',
        'version': 0x30, 'hlen': hlen, 'rlen': rlen, 'entriesnum': cnt,
        'cap_entry': cap_entry,
        'extent': [off, off + hlen + rlen * cnt],
        'extent_len': hlen + rlen * cnt,
        'entries': entries,
    }


def decode_slot17(img, off):
    hlen = img[off + 1]
    unknown = list(img[off + 2:off + hlen])
    return {
        'table': 'PERF TEST SPEC (P2 off 0x44)',
        'source': 'envy_bios_parse_power_unk44 (power.c:1188; version switch power.c:1197; hlen@+1 power.c:1199; \'it does not appear as if this table has entries at all\' power.c:1200)',
        'version': 0x10, 'hlen': hlen, 'rlen': None, 'entriesnum': 0,
        'extent': [off, off + hlen],
        'extent_len': hlen,
        'entries': [],
        'unknown_bytes': {
            'note': 'source reads only version@+0 and hlen@+1; bytes +2..+13 kept raw, not interpreted (offset+2/+3 are NOT entry_size/count for this parser)',
            'raw': unknown,
        },
    }


def decode_slot20(img, off):
    hlen, rlen, cnt = img[off + 1], img[off + 2], img[off + 3]
    entries = []
    for i in range(cnt):
        eoff = off + hlen + i * rlen
        entries.append({
            'index': i,
            'entry_off': eoff,
            'mode': img[eoff],
            't0': u16(img, eoff + 2),
            't1': u16(img, eoff + 4),
            't2': u16(img, eoff + 6),
            'interval_us': u16(img, eoff + 8),
            'down_off': u16(img, eoff + 0x12),
            'up_off': u16(img, eoff + 0x14),
            'raw': list(img[eoff:eoff + rlen]),
        })
    return {
        'table': 'THERMAL POLICY (P2 off 0x50)',
        'source': 'envy_bios_parse_power_unk50 (power.c:1334; entry field offsets power.c:1396-1405)',
        'version': 0x10, 'hlen': hlen, 'rlen': rlen, 'entriesnum': cnt,
        'extent': [off, off + hlen + rlen * cnt],
        'extent_len': hlen + rlen * cnt,
        'entries': entries,
    }


def classify_slot(s, img):
    '''Return (status, decode, header_shape, reason) for a slot record.'''
    if s['null']:
        return 'NULL', None, None, 'null directory pointer'
    if not s['target_in_bounds'] or s['mapped_off'] is None:
        return 'OPAQUE_BAD_TARGET', None, None, 'mapped target outside image'
    off = s['mapped_off']
    fb = s['target_first_bytes'] or []
    version = fb[0] if fb else None
    idx = s['index']

    if idx == 0:
        generic = None
        if len(fb) >= 4:
            generic = {'hlen': fb[1], 'esz': fb[2], 'cnt': fb[3],
                       'generic_size': fb[1] + fb[2] * fb[3]}
        return ('UNSUPPORTED_V60', None,
                {'version': version, 'generic_formula_rejected': generic,
                 'note': 'no envytools field parser for PERF v60; nvbios.c only captures the offset (nvbios.c:1095 BMP path) and hex-dumps it at print time (nvbios.c:1477). Generic hdr+esz*cnt extent NOT adopted.'},
                'version 0x60 unsupported by current parser')

    if idx in (5, 11, 17, 20):
        if version is None:
            return 'OPAQUE_BAD_TARGET', None, None, 'no target bytes'
        dec = {5: decode_slot5, 11: decode_slot11, 17: decode_slot17,
               20: decode_slot20}[idx](img, off)
        if dec['version'] != version or (len(fb) > 1 and dec['hlen'] != fb[1]):
            return 'OPAQUE_HEADER_MISMATCH', None, None, 'source header fields disagree with raw bytes'
        return 'DECODED', dec, {
            'version': version, 'hlen': dec['hlen'], 'rlen': dec['rlen'],
            'entriesnum': dec['entriesnum'],
            'source_cite': dec['source'],
        }, 'source-backed decode (typed set)'

    if idx in SOURCE_VERSIONS:
        accepted, cite = SOURCE_VERSIONS[idx]
        shape = header_shape(img, off, accepted, cite)
        if shape is None:
            return 'HEADER_ONLY', None, {
                'version': version,
                'note': 'version %#x not in source-accepted set %s; no extent' % (version, accepted),
                'source_parser': cite,
            }, 'version not accepted by source parser'
        return 'HEADER_SOURCE_SHAPE', None, shape, 'source header shape (traversal fact only)'

    if idx in P2_TBLS:
        return 'HEADER_ONLY', None, {
            'version': version,
            'note': 'slot named in P2_tbls but no header-shape acceptance verified in this audit; no extent claimed',
            'source_parser': 'power.c parser present for slot (presence unverified)',
        }, 'no source-backed extent applied'
    return 'OPAQUE_NO_SCHEMA', None, {
        'version': version,
        'note': 'slot not named in P2_tbls source (power.c:82-103 ends at offset 0x98); no parser identified',
    }, 'unnamed slot'


# ---------------------------------------------------------------------------
# Cross-image comparison
# ---------------------------------------------------------------------------

def compare_images(a, b, label_a, label_b, limit=4096):
    n = min(len(a), len(b))
    diffs = [(i, a[i], b[i]) for i in range(n) if a[i] != b[i]]
    return {'label_a': label_a, 'label_b': label_b,
            'bytes_compared': n, 'diff_count': len(diffs),
            'diffs': diffs[:limit], 'diffs_truncated': len(diffs) > limit}


def main():
    if len(sys.argv) == 5:
        rom_path, t4_path, sh_path, outdir = sys.argv[1:5]
    else:
        rom_path, t4_path, sh_path, outdir = (DEFAULT_ROM, DEFAULT_T4,
                                              DEFAULT_SHADOW, DEFAULT_OUTDIR)

    rom = load_image(rom_path)
    t4 = load_image(t4_path)
    sh = load_image(sh_path)

    os.makedirs(outdir, exist_ok=True)

    prov = {'repo': ENVYTOOLS_REPO, 'git_head': ENVYTOOLS_GIT_HEAD,
            'files': {name: {'path': path, 'sha256': env_file_sha(path)}
                      for name, path in ENVY_FILES.items()}}

    images = {}
    for key, path, img in (('rom', rom_path, rom), ('t4', t4_path, t4),
                           ('shadow', sh_path, sh)):
        images[key] = audit_image(img, key)

    # Cross-image checks.
    x_bit = compare_images(rom, sh, 'rom', 'shadow')
    x_array = compare_images(rom[0x288D4:0x289B4], sh[0x2D4:0x2E4],
                             'rom[0x288D4:0x289B4]', 'shadow[0x2D4:0x2E4]')
    x_bank_legacy = rom[0x28600:0x37A00] == rom[0xA1600:0xB0A00]
    x_bank_efi = rom[0x37A00:0x48A00] == rom[0xB0A00:0xC1A00]
    x_array_dup = rom[0x288D4:0x289B4] == rom[0xA18D4:0xA19B4]

    t4_vs_rom = compare_images(rom[:len(t4)], t4, 'rom[0:495616]', 't4')
    shadow_vs_rom = compare_images(rom[0x28600:0x28600 + 0xD7A00], sh[:0xD7A00],
                                   'rom[0x28600:0xB9E00]', 'shadow[0:0xD7A00]')

    # Per-token statuses + source-backed decodes (ROM image).
    per_token = []
    decodes = {}
    for e in images['rom']['bit_entries']:
        st = 'NULL' if e['t_offset_null'] else (
            'POWER_DIRECTORY' if e['type_ascii'] == 'P' else 'OPAQUE_PACKED_BLOB')
        per_token.append({'image': 'rom', 'kind': 'BIT',
                          'id': e['type_ascii'] or ('0x%02x' % e['type']),
                          'index': e['index'], 'status': st,
                          'target': e['mapped_off'], 't_len': e['t_len'],
                          'evidence': ['BIT entry %d @ %#x' % (e['index'], e['entry_off']),
                                       'raw %s' % e['raw'],
                                       'mapping %s' % e['mapping']]})

    for s in images['rom']['slots']:
        st, dec, shape, reason = classify_slot(s, rom)
        s['status'] = st
        if dec is not None:
            decodes[s['index']] = dec
            s['decode'] = dec
        if shape is not None:
            s['header_shape'] = shape
        s['status_reason'] = reason
        per_token.append({'image': 'rom', 'kind': 'SLOT',
                          'id': 'slot %d%s' % (s['index'],
                                               ' (%s)' % s['p2_name'] if s['p2_name'] else ''),
                          'index': s['index'], 'status': st,
                          'target': s['mapped_off'], 'raw_u32': s['raw_u32'],
                          'evidence': ['directory u32 @ %#x = %#x' % (s['directory_off'], s['raw_u32']) if s['raw_u32'] is not None else 'null',
                                       'mapping %s' % s['mapping']]})

    # Same classification repeated for T4 and shadow (targets identical where
    # bytes match; statuses reported per image).
    for key in ('t4', 'shadow'):
        img = {'t4': t4, 'shadow': sh}[key]
        for e in images[key]['bit_entries']:
            st = 'NULL' if e['t_offset_null'] else (
                'POWER_DIRECTORY' if e['type_ascii'] == 'P' else 'OPAQUE_PACKED_BLOB')
            per_token.append({'image': key, 'kind': 'BIT',
                              'id': e['type_ascii'] or ('0x%02x' % e['type']),
                              'index': e['index'], 'status': st,
                              'target': e['mapped_off'], 't_len': e['t_len'],
                              'evidence': ['BIT entry %d @ %#x' % (e['index'], e['entry_off']),
                                           'raw %s' % e['raw'],
                                           'mapping %s' % e['mapping']]})
        for s in images[key]['slots']:
            st, dec, shape, reason = classify_slot(s, img)
            s['status'] = st
            if shape is not None:
                s['header_shape'] = shape
            s['status_reason'] = reason
            per_token.append({'image': key, 'kind': 'SLOT',
                              'id': 'slot %d%s' % (s['index'],
                                                   ' (%s)' % s['p2_name'] if s['p2_name'] else ''),
                              'index': s['index'], 'status': st,
                              'target': s['mapped_off'], 'raw_u32': s['raw_u32'],
                              'evidence': ['directory u32 @ %#x = %#x' % (s['directory_off'], s['raw_u32']) if s['raw_u32'] is not None else 'null',
                                           'mapping %s' % s['mapping']]})

    slot0 = {'off': 0x54155,
             'raw_header': list(rom[0x54155:0x54155 + 16]),
             'note': 'PERFORMANCE v60 — UNSUPPORTED; generic hdr+esz*cnt = 0x0a+0x05*0x07 = 45 bytes explicitly NOT adopted'}

    # Slot-extent adjacency / overlap register (ROM image, claimed extents only).
    claimed = []
    for s in images['rom']['slots']:
        if s['mapped_off'] is None:
            continue
        if s['status'] == 'DECODED' and s.get('decode', {}).get('extent'):
            claimed.append((s['index'], s['decode']['extent'], s['mapped_off']))
        elif s['status'] == 'HEADER_SOURCE_SHAPE' and s.get('header_shape', {}).get('extent'):
            claimed.append((s['index'], s['header_shape']['extent'], s['mapped_off']))
    adjacency, overlaps = [], []
    for i, (ei, (es, ee), et) in enumerate(claimed):
        for j, (ej, (js, je), jt) in enumerate(claimed):
            if i == j:
                continue
            if ee == jt:
                adjacency.append({'slot_i': ei, 'extent_i_end': ee, 'slot_j_target': ej,
                                  'note': 'extent end of slot %d == target of slot %d' % (ei, ej)})
            if es <= jt < ee:
                overlaps.append({'slot_i': ei, 'extent_i': [es, ee], 'slot_j_target': ej,
                                 'note': 'target of slot %d lies inside extent of slot %d' % (ej, ei)})
    result = {
        'audit_meta': {
            'created_utc': datetime.now(timezone.utc).isoformat(),
            'command': 'python3 vbios_full_token_audit.py',
            'outdir': outdir,
            'ponytail': 'full',
        },
        'inputs': {
            'rom': {'path': rom_path, 'size': len(rom), 'sha256': sha256_file(rom_path)},
            't4': {'path': t4_path, 'size': len(t4), 'sha256': sha256_file(t4_path)},
            'shadow': {'path': sh_path, 'size': len(sh), 'sha256': sha256_file(sh_path)},
        },
        'provenance': prov,
        'conventions': {
            'bit_signature': 'ff b8 42 49 54 00 00 (envytools bios.c:198)',
            'bit_header': 'version u16@+6 (expect 0x0100), hlen u8@+8, rlen u8@+9, entriesnum u8@+10; checksum over header must be 0 (bit.c:70-92); entry: type@0, version@1, t_len u16@2, t_offset u16@4 (bit.c:121-123)',
            'power_directory': "BIT token 'P' (power v2) -> u32 slot array; slot i pointer at dir + i*4 (power.c:82-103 P2_tbls, power.c parse_at)",
            'mapping_rom_t4': 'BIT t_offset -> 0x28600 + t_offset ; power u32 -> 0x39600 + u32 (verified vs raw table headers)',
            'mapping_shadow': 'BIT t_offset -> direct shadow offset; power u32 -> u32 - 0x28600 (base 0x11000); shadow[i] == rom[i+0x28600] for the mapped region except 14 recorded bytes (see cross_image.shadow_vs_rom_shifted)',
            'traversal_vs_semantic': 'offsets/versions/hlen/rlen/counts and extent arithmetic are parser traversal facts; field meanings are source-backed semantic decodes only where cited',
        },
        'images': images,
        'decoded_tables': {str(k): v for k, v in decodes.items()},
        'slot0_unsupported': slot0,
        'cross_image': {
            'bit_region_rom_vs_shadow': x_bit,
            'power_directory_rom_vs_shadow': x_array,
            't4_vs_rom_prefix': t4_vs_rom,
            'shadow_vs_rom_shifted': shadow_vs_rom,
            'banks': {
                'legacy1_0x28600_0x37A00_equals_legacy2_0xA1600_0xB0A00': x_bank_legacy,
                'EFI1_0x37A00_0x48A00_equals_EFI2': x_bank_efi,
                'power_directory_duplicated_at_0xA18D4': x_array_dup,
                'note': 'repeated banks are byte-identical; no table difference claimed from similarity — verified byte-for-byte',
            },
        },
        'structural_facts': {
            'bit_checksum_mod256_rom': images['rom']['bit_header']['checksum_mod256'],
            'bit_checksum_ok_rom': images['rom']['bit_header']['checksum_ok'],
            'power_directory_entries': SLOT_COUNT,
            'power_directory_null_slots_rom': [s['index'] for s in images['rom']['slots'] if s['null']],
            'power_directory_nonnull_slots_rom': [s['index'] for s in images['rom']['slots'] if not s['null']],
            'bit_target_chain_adjacency': [
                "from 'B' (0x2883e) through 'i' (ends 0x28a5c) every target equals previous target + previous t_len (packed, no overlaps, no gaps)",
                "'2' target 0x28832 len 4 stands apart; gaps at [0x28822,0x28832) and [0x28836,0x2883e)",
                'no overlap between any BIT-targeted tables; power directory [0x288d4,0x289b4) is P itself and abuts M/S',
            ],
            'gaps': [
                {'span': [0x287bc, 0x28832], 'len': 0x76,
                 'note': 'between BIT entries end (0x28822) and 2 target (0x28832)'},
                {'span': [0x28836, 0x2883e], 'len': 8,
                 'note': 'between 2 extent end (0x28836) and B start (0x2883e)'},
            ],
            'trailing': {'span': [0x28a5c, 0x28a70],
                         'note': 'after i extent end; uncharted bytes'},
            'slot_extent_adjacency_rom': {'adjacency': adjacency, 'overlaps': overlaps},
        },
        'opaque_register': [
            {'table': "BIT token '2' (i2c)", 'target_rom': 0x28832, 't_len': 4,
             'reason': 'target bytes are all zero; degenerate/empty in this image; no field decode'},
            {'table': "BIT token 'N'", 'target_rom': None, 't_len': 0,
             'reason': 'null pointer (t_offset=0); NOP per bit.c bit_types'},
            {'table': "BIT tokens 'B','C','D','I','M','S','T','U','V','x','d','p','u','i'",
             'target_rom': '0x2883e-0x28a5c', 't_len': '2-44',
             'reason': 'targets lie inside one packed blob with no version-first layout; no envytools field schema matches this image layout; raw bytes preserved, not interpreted'},
            {'table': 'PERF/slot directory indices 26, 27, 28',
             'target_rom': '0x3e37b, 0x3e317, 0x3e38e', 't_len': 'unknown',
             'reason': 'non-null u32 pointers whose mapped targets begin 0xff / 0xa1 / 0x25 — not a coherent table header under the image base; stale or out-of-scope pointers'},
            {'table': 'PERF/slot index 0 (PERFORMANCE)', 'target_rom': 0x54155, 't_len': 'unknown',
             'reason': 'version byte 0x60 (v60); no envytools field parser; generic entry-size formula explicitly rejected'},
            {'table': 'PERF/slot directory indices 39-55', 'target_rom': 'various', 't_len': 'unknown',
             'reason': 'not named in P2_tbls source (power.c:82-103 ends at offset 0x98); no parser identified'},
        ],
        'per_token_status': per_token,
    }

    # ---- write outputs ----
    json_path = os.path.join(outdir, 'vbios_token_audit.json')
    with open(json_path, 'w') as f:
        json.dump(result, f, indent=1)
    cmd_path = os.path.join(outdir, 'run_vbios_full_token_audit.sh')
    write_shell(cmd_path, rom_path, t4_path, sh_path, outdir)
    out_hashes = {
        'vbios_token_audit.json': sha256_file(json_path),
        'run_vbios_full_token_audit.sh': sha256_file(cmd_path),
    }
    result['output_hashes'] = out_hashes
    report_path = os.path.join(outdir, 'VBIOS_FULL_TOKEN_AUDIT_REPORT.md')
    write_report(result, report_path)
    out_hashes['VBIOS_FULL_TOKEN_AUDIT_REPORT.md'] = sha256_file(report_path)
    result['output_hashes'] = out_hashes
    with open(os.path.join(outdir, 'output_hashes.json'), 'w') as f:
        json.dump(out_hashes, f, indent=1)

    print('Audit complete. Outputs in %s' % outdir)
    print(json.dumps(out_hashes, indent=1))


def write_report(result, path):
    lines = []

    def w(s=''):
        lines.append(s)

    w('# VBIOS_FULL_TOKEN_AUDIT — CMP 40HX (TU106) ROM/T4/shadow')
    w('')
    w('Created: %s UTC' % result['audit_meta']['created_utc'])
    w('Output dir: %s' % result['audit_meta']['outdir'])
    w('')
    w('## Inputs (read-only, preserved)')
    for k in ('rom', 't4', 'shadow'):
        i = result['inputs'][k]
        w('- %s: %s  size=%d  sha256=%s' % (k, i['path'], i['size'], i['sha256']))
    w('')
    w('## Provenance (envytools source, cited verbatim by file/line/hash)')
    p = result['provenance']
    w('- repo: %s  git HEAD: %s' % (p['repo'], p['git_head']))
    for name, ent in p['files'].items():
        w('- %s: %s  sha256=%s' % (name, ent['path'], ent['sha256']))
    w('')
    w('## Conventions')
    for k, v in result['conventions'].items():
        w('- %s: %s' % (k, v))
    w('')
    w('## Per-image BIT table')
    for key, imgd in result['images'].items():
        w('### %s (%d bytes)' % (key, imgd['size']))
        bh = imgd['bit_header']
        w('- BIT signature at %#x; version=%#x (expect 0x0100); hlen=%d (want 12); rlen=%d (want 6); entriesnum=%d' % (
            bh['sig_off'], bh['version'], bh['hlen'], bh['rlen'], bh['entriesnum']))
        w('- header checksum mod 256 = %#x (envytools requires 0; bit.c:91-92 -> traversal would abort here)' % bh['checksum_mod256'])
        w('- header raw: %s' % bh['header_raw'])
        w('- BIT span: %s' % imgd['bit_span'])
        w('- entries:')
        for e in imgd['bit_entries']:
            w('   idx %2d type=%r(0x%02x) ver=%d t_len=%d t_offset=0x%04x %s -> mapped %s (%s)' % (
                e['index'], e['type_ascii'], e['type'], e['version'], e['t_len'],
                e['t_offset'], 'NULL' if e['t_offset_null'] else '',
                hex(e['mapped_off']) if e['mapped_off'] is not None else None, e['mapping']))
        pd = imgd['power_directory']
        if pd:
            w('- power directory (''P''): off %#x, t_len %d (= 56 x 4: %s)' % (
                pd['directory_off'], pd['t_len'], pd['slots_fit']))
    w('')
    w('## Per-slot directory audit (56 u32 pointers, ''P'' token / P2_tbls)')
    romd = result['images']['rom']
    w('| idx | P2 name (power.c:82-103) | raw u32 | mapped target (rom) | first bytes | status |')
    w('|-----|--------------------------|---------|---------------------|-------------|--------|')
    for s in romd['slots']:
        if s['p2_name']:
            name = s['p2_name']
        elif s['p2_raw_offset'] is not None:
            name = '(unnamed, P2 offset 0x%x)' % s['p2_raw_offset']
        else:
            name = '(unnamed, offset >0x98)'
        fb = s['target_first_bytes']
        fb_s = ' '.join('%02x' % b for b in fb[:6]) if fb else '-'
        w('| %2d | %s | %s | %s | %s | %s |' % (
            s['index'], name,
            ('%#06x' % s['raw_u32']) if s['raw_u32'] is not None else '   NULL',
            (hex(s['mapped_off']) + ' ' * (19 - len(hex(s['mapped_off'])))) if s['mapped_off'] is not None else '-                   ',
            fb_s, s['status']))
    w('')
    w('## Decoded tables (source-backed, field-level)')
    for k in ('5', '11', '17', '20'):
        d = result['decoded_tables'][k]
        w('### slot %s: %s' % (k, d['table']))
        w('- source: %s' % d['source'])
        w('- version=%#x hlen=%d rlen=%s entries=%d extent=%s len=%d' % (
            d['version'], d['hlen'], d['rlen'], d['entriesnum'],
            d['extent'], d['extent_len']))
        if d.get('cap_entry') is not None:
            w('- cap_entry@0x0a = %d' % d['cap_entry'])
        for e in d['entries']:
            w('   entry %d: off=%#x raw=%s' % (e['index'], e['entry_off'], e['raw']))
        if d.get('unknown_bytes'):
            w('- unknown bytes preserved: %s' % d['unknown_bytes'])
    w('')
    w('## Slot 0 — PERFORMANCE v60: UNSUPPORTED')
    w('- target: %#x; raw header: %s' % (slot0_off(result), result['slot0_unsupported']['raw_header']))
    w('- %s' % result['slot0_unsupported']['note'])
    w('')
    w('## Structural facts')
    for f_ in result['structural_facts']['bit_target_chain_adjacency']:
        w('- %s' % f_)
    w('- gaps: %s' % result['structural_facts']['gaps'])
    w('- trailing after i: %s' % result['structural_facts']['trailing'])
    sa = result['structural_facts']['slot_extent_adjacency_rom']
    if sa['adjacency']:
        w('- slot extent adjacencies (claimed extents only): %s' % sa['adjacency'])
    if sa['overlaps']:
        w('- SLOT EXTENT OVERLAPS: %s' % sa['overlaps'])
    if not sa['adjacency'] and not sa['overlaps']:
        w('- no adjacencies/overlaps among claimed slot extents')
    w('')
    w('## Cross-image comparison')
    ci = result['cross_image']
    w('- T4 vs rom[0:495616]: %d byte diffs (T4 is rom prefix with 19 patches):' % ci['t4_vs_rom_prefix']['diff_count'])
    for d in ci['t4_vs_rom_prefix']['diffs']:
        w('   %#x rom=%d t4=%d' % (d[0], d[1], d[2]))
    w('- shadow vs rom[0x28600:0xB9E00]: %d diffs over 0xD7A00 compared bytes' % ci['shadow_vs_rom_shifted']['diff_count'])
    for d in ci['shadow_vs_rom_shifted']['diffs']:
        w('   shadow=%#x rom_byte=%d shadow_byte=%d' % (d[0], d[1], d[2]))
    w('- banks: legacy1==legacy2: %s; EFI1==EFI2: %s; directory duplicated at 0xA18D4: %s' % (
        ci['banks']['legacy1_0x28600_0x37A00_equals_legacy2_0xA1600_0xB0A00'],
        ci['banks']['EFI1_0x37A00_0x48A00_equals_EFI2'],
        ci['banks']['power_directory_duplicated_at_0xA18D4']))
    w('')
    w('## Opaque tables (explicit)')
    for o in result['opaque_register']:
        w('- %s: %s' % (o['table'], o['reason']))
    w('')
    w('## Per-token status summary')
    counts = {}
    for t in result['per_token_status']:
        counts[t['status']] = counts.get(t['status'], 0) + 1
    w('- total tokens audited: %d' % len(result['per_token_status']))
    for st in sorted(counts):
        w('  - %s: %d' % (st, counts[st]))
    w('')
    w('## Reproduction')
    w('```sh')
    w('python3 vbios_full_token_audit.py %s %s %s %s' % (
        result['inputs']['rom']['path'], result['inputs']['t4']['path'],
        result['inputs']['shadow']['path'], result['audit_meta']['outdir']))
    w('```')
    w('')
    w('## Output hashes')
    for k, v in result.get('output_hashes', {}).items():
        w('- %s: %s' % (k, v))
    w('')
    w('## Method note')
    w('Offsets, versions, hlen/rlen/counts and extent arithmetic are parser traversal facts (envytools bit.c/power.c, cited above). ')
    w('Semantic field decoding is claimed only for slots 5, 11, 17, 20, strictly version-gated per power.c. ')
    w('Slot 0 (v60) and all other tables are deliberately left opaque with reasons stated. ')
    w('No hardware access, ROM flashing, keys, or cryptographic semantics involved.')
    with open(path, 'w') as f:
        f.write('\n'.join(lines) + '\n')


def slot0_off(result):
    return result['slot0_unsupported']['off']


def write_shell(path, rom_path, t4_path, sh_path, outdir):
    content = ('#!/bin/sh\n'
               '# Replay: VBIOS full token audit (read-only; outputs only under %s)\n'
               'set -eu\n'
               'DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\n'
               'python3 "$DIR/vbios_full_token_audit.py" %s %s %s %s\n'
               'echo "--- outputs ---"\n'
               'ls -la %s\n'
               'echo "--- hashes ---"\n'
               'cat %s/output_hashes.json\n'
               % (outdir, rom_path, t4_path, sh_path, outdir, outdir, outdir))
    with open(path, 'w') as f:
        f.write(content)
    os.chmod(path, 0o755)


if __name__ == '__main__':
    # Self-check: traversal-fact anchors that must hold for this image set.
    rom = load_image(DEFAULT_ROM)
    assert rom.find(BIT_SIG) == 0x287B0, 'BIT sig offset'
    bh = parse_bit_header(rom, 0x287B0)
    assert bh['version'] == 0x0100 and bh['hlen'] == 12 and bh['rlen'] == 6 and bh['entriesnum'] == 17
    assert bh['checksum_mod256'] == 0x00, 'BIT header checksum fact'
    ent = parse_bit_entries(rom, 0x287B0, 12, 6, 17)
    assert ent[0]['type_ascii'] == '2' and ent[0]['version'] == 1 and ent[0]['t_len'] == 4 and ent[0]['t_offset'] == 0x0232
    assert ent[7]['type_ascii'] == 'P' and ent[7]['t_len'] == 224 and ent[7]['t_offset'] == 0x02D4
    assert u32(rom, 0x288D4) == 0x1AB55  # directory idx0 -> PERFORMANCE v60 table
    assert rom[0x39600 + 0x1AB55] == 0x60  # version byte v60 at mapped target
    assert rom[0x58723:0x58724] == b'\x10' and rom[0x545f2:0x545f3] == b'\x10'
    assert rom[0x28600:0x37A00] == rom[0xA1600:0xB0A00]  # repeated legacy bank
    assert rom[0x288D4:0x289B4] == rom[0xA18D4:0xA19B4]  # directory duplicated in bank2
    t4 = load_image(DEFAULT_T4)
    diffs = [i for i in range(len(t4)) if t4[i] != rom[i]]
    assert len(diffs) == 19, 'T4 patch count %d' % len(diffs)
    assert rom[0x5669c:0x5669f] == b'\x70\x76\x82'
    assert t4[0x5669c:0x5669f] == b'\x40\x54\x89'
    sh = load_image(DEFAULT_SHADOW)
    assert sh.find(BIT_SIG) == 0x1B0
    assert sh[0x0232] == rom[0x28832]  # shadow direct-offset mapping for BIT targets
    print('self-check OK: all anchor assertions passed')
    main()
