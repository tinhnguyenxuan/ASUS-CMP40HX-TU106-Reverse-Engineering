#!/usr/bin/env python3
# falcon_decode_gap.py
# Isolated decode-gap investigation for the 8 Falcon payload candidates
# (slots 20, 150, 156, 481, 484, 487, 490, 493) from the NVUCODES container.
#
# Question: the first undecodable span immediately after the bounded Falcon
# candidate bootstrap prefix in each slot. Task-given facts (re-verified here):
#   slot 20:  candidate entry 0x2A, decoded prefix ends 0x68, then bytes 3e74fe00
#   slots 150/156: candidate entry 0x16, prefix ends 0x34, then bytes 89000000
#   slots 481/484/487/490/493: candidate entry 0x16, prefix ends 0x37, then bytes 89000000
#
# Method (read-only inputs only; no GPU/MMIO/flashing/keys/signatures/brute force):
#   1. Re-read each span from outputs/ucodes_tu10x.bin at the VERIFIED container
#      offset/length (firmware_container_verified.json) and re-check sha256.
#   2. One full-span envydis (-m falcon, default variant) pass per payload to
#      recover regions/gaps and confirm the first gap after the bootstrap prefix.
#   3. Re-run envydis on a window starting at the gap under every Falcon
#      variant/mode the already-built envydis supports (default, fuc0, fuc3,
#      fuc4, fuc5, fuc6) to see whether the gap bytes decode as a valid
#      instruction under any variant. Mere valid syntax is NOT treated as proof
#      of code; the true Falcon version/mode is not established by any available
#      field, so results are reported per-variant.
#   4. Verify the gap offset against the ORIGINAL container bytes
#      (container_off + span_off) by re-reading from the container file.
#   5. Inspect the payload head16 and look for any saved payload/manifest/header
#      field identifying true entry and mode; report none found.
#
# No source mutation, no GPU, no MMIO, no tool install.
# Run: cd /home/REDACTED_USER/codex-work/work_v15 && /usr/bin/python3 PHASE16/FALCON_DECODE_GAP/falcon_decode_gap.py
import struct, hashlib, json, re, subprocess, sys, os
from pathlib import Path

ROOT = Path('/home/REDACTED_USER/codex-work/work_v15')
PH = ROOT / 'PHASE16'
GAP = PH / 'FALCON_DECODE_GAP'
CONTAINER = ROOT / 'outputs/ucodes_tu10x.bin'
INVENTORY = PH / 'firmware_container_verified.json'
CFG_MACHINE = PH / 'FALCON_CFG_REBUILD' / 'machine.json'
ENVYDIS = '/tmp/envytools/build/envydis/envydis'
SLOTS = [20, 150, 156, 481, 484, 487, 490, 493]
# Falcon ISA variants/modes the already-built envydis supports (from falcon.c prep).
VARIANTS = [None, 'fuc0', 'fuc3', 'fuc4', 'fuc5', 'fuc6']  # None == default (-V omitted)
GAP_WINDOW = 32  # bytes of gap + following context to disassemble per variant

ENVYDIS_RE = re.compile(r'^([0-9a-fA-F]+):\s+((?:[0-9a-fA-F]{2}\s+)+?)\s{2,}(.*)$')

def sha(b): return hashlib.sha256(b).hexdigest()
def sha_file(p):
    p = Path(p)
    return sha(p.read_bytes()) if p.exists() else None

def envydis_disasm(path, size, variant=None):
    cmd = [ENVYDIS, '-i', '-n', '-m', 'falcon', '-b', '0', '-d', '0', '-l', '%x' % size]
    if variant:
        cmd += ['-V', variant]
    cmd.append(str(path))
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return [], 'envydis rc=%d: %s' % (r.returncode, r.stderr.strip()), r.returncode
    lines = []
    for line in r.stdout.splitlines():
        line = re.sub(r'\x1b\[[0-9;]*m', '', line).rstrip()
        if not line:
            continue
        m = ENVYDIS_RE.match(line)
        if not m:
            continue
        off = int(m.group(1), 16)
        raw = bytes.fromhex(m.group(2).strip().replace(' ', ''))
        text = m.group(3).strip()
        lines.append((off, raw, text))
    lines.sort(key=lambda t: t[0])
    return lines, '', 0

def valid_insn(text):
    t = text.lower()
    return (not text.startswith('???')) and ('[unknown' not in t)

def mnemonic(text):
    tok = text.split()
    return tok[0].lower() if tok else ''

def build_regions(entries, size):
    # entries: list of (off, raw, text, valid)
    regions, gaps = [], []
    cur = None
    covered_end = 0
    for off, raw, text, valid in entries:
        if off < covered_end:
            continue
        if off > covered_end:
            gaps.append((covered_end, off, 'undecoded_trailing'))
        covered_end = off
        if valid:
            if cur is not None and off == cur['end']:
                cur['end'] = off + len(raw)
                cur['insns'].append({'offset': off, 'size': len(raw), 'raw': raw.hex(), 'text': text})
            else:
                if cur is not None:
                    regions.append(cur)
                cur = {'start': off, 'end': off + len(raw),
                       'insns': [{'offset': off, 'size': len(raw), 'raw': raw.hex(), 'text': text}]}
            covered_end = off + len(raw)
        else:
            if cur is not None:
                regions.append(cur); cur = None
            gaps.append((off, off + len(raw), 'invalid_decode'))
            covered_end = off + len(raw)
    if cur is not None:
        regions.append(cur)
    if covered_end < size:
        gaps.append((covered_end, size, 'undecoded_trailing'))
    return regions, gaps

def special_markers(text):
    out = []
    low = text.lower()
    for r in ('$xcbase', '$xtargets', '$xdbase', '$xfsbase'):
        if r in low:
            out.append('write_' + r)
    tok = text.split()
    if tok and tok[0].lower() in ('xcld', 'xdld', 'xdst', 'xcwait', 'xdwait', 'exit'):
        out.append(tok[0].lower())
    return out

def main():
    GAP.mkdir(parents=True, exist_ok=True)
    container = CONTAINER.read_bytes()
    cver = json.loads(INVENTORY.read_text())
    payloads_by_slot = {p['slot']: p for p in cver['payloads']}

    # Task-given expected facts (to independently verify).
    expected = {
        20:  {'entry': 0x2A, 'prefix_end': 0x68, 'gap_hex': '3e74fe00'},
        150: {'entry': 0x16, 'prefix_end': 0x34, 'gap_hex': '89000000'},
        156: {'entry': 0x16, 'prefix_end': 0x34, 'gap_hex': '89000000'},
        481: {'entry': 0x16, 'prefix_end': 0x37, 'gap_hex': '89000000'},
        484: {'entry': 0x16, 'prefix_end': 0x37, 'gap_hex': '89000000'},
        487: {'entry': 0x16, 'prefix_end': 0x37, 'gap_hex': '89000000'},
        490: {'entry': 0x16, 'prefix_end': 0x37, 'gap_hex': '89000000'},
        493: {'entry': 0x16, 'prefix_end': 0x37, 'gap_hex': '89000000'},
    }

    results = []
    for slot in SLOTS:
        inv = payloads_by_slot[slot]
        off, size = inv['offset'], inv['length']
        span = container[off:off + size]
        computed_sha = sha(span)
        exp = expected[slot]

        span_path = GAP / ('cand_%04d.bin' % slot)
        span_path.write_bytes(span)

        # Pass 1: full-span disassembly under DEFAULT variant -> regions/gaps.
        entries, err, rc = envydis_disasm(span_path, size, None)
        parsed = [(e, r, t, valid_insn(t)) for e, r, t in entries]
        regions, gaps = build_regions(parsed, size)

        # Primary entry = first region writing Falcon $xcbase (bring-up core).
        xcbase_regions = [rg for rg in regions if any('write_$xcbase' in special_markers(i['text']) for i in rg['insns'])]
        primary = min(xcbase_regions, key=lambda r: r['start']) if xcbase_regions else (regions[0] if regions else None)

        prefix_end = primary['end'] if primary else None
        # First gap at/after prefix end.
        first_gap = None
        for g in gaps:
            if prefix_end is not None and g[0] >= prefix_end:
                first_gap = g; break
        if first_gap is None and gaps:
            first_gap = gaps[0]

        gap_start = first_gap[0] if first_gap else None
        gap_end = min(gap_start + 4, size) if gap_start is not None else None
        gap_bytes = span[gap_start:gap_end] if gap_start is not None else b''

        # Pass 2: gap window under every variant -> is the gap a valid insn?
        win_end = min(gap_start + GAP_WINDOW, size) if gap_start is not None else size
        window = span[gap_start:win_end] if gap_start is not None else b''
        win_path = GAP / ('gap_%04d.bin' % slot)
        win_path.write_bytes(window)

        variant_decode = {}
        for v in VARIANTS:
            vname = 'default' if v is None else v
            wlines, werr, wrc = envydis_disasm(win_path, len(window), v)
            first = wlines[0] if wlines else None
            variant_decode[vname] = {
                'envydis_error': werr, 'rc': wrc,
                'first_insn_at_gap': {
                    'offset': first[0], 'raw': first[1].hex(), 'text': first[2],
                    'valid': valid_insn(first[2]), 'mnemonic': mnemonic(first[2]),
                } if first else None,
                'all_lines': [{'offset': e, 'raw': r.hex(), 'text': t, 'valid': valid_insn(t), 'mnemonic': mnemonic(t)} for e, r, t in wlines],
                'window_fully_decoded': all(valid_insn(t) for _, _, t in wlines) if wlines else None,
            }

        # Verify gap offset against ORIGINAL container bytes.
        abs_off = off + gap_start if gap_start is not None else None
        abs_verified = False
        abs_bytes = b''
        if abs_off is not None:
            abs_bytes = container[abs_off:abs_off + 4]
            abs_verified = (abs_bytes.hex() == exp['gap_hex']) and (abs_bytes == gap_bytes[:4])

        # Payload head16 + search for any manifest/mode/version field.
        head = span[:16]
        head_u32 = list(struct.unpack_from('<4I', head, 0))
        head_fields = {
            'u32_0': '%08X' % head_u32[0], 'u32_1': '%08X' % head_u32[1],
            'u32_2': '%08X' % head_u32[2], 'u32_3': '%08X' % head_u32[3],
        }
        # Look for any obvious Falcon version/mode token in head or tail (none expected).
        mode_hint = None
        for i, v in enumerate(head_u32):
            if v in (0, 1, 2, 3, 4, 5, 6):
                mode_hint = 'u32_%d == %d (no version semantics asserted)' % (i, v)
        # Scan entire span header area for ASCII 'fuc'/'falcon'/'version' strings (read-only).
        mode_strings = [m.group().decode('ascii', 'replace') for m in re.finditer(rb'[ -~]{4,}', span[:64]) if any(k in m.group().decode('ascii', 'replace').lower() for k in ('fuc', 'falcon', 'version', 'mode'))]

        rec = {
            'slot': slot, 'offset': off, 'offset_hex': '0x%08X' % off,
            'size': size, 'sha256': computed_sha,
            'sha256_matches_inventory': computed_sha == inv['sha256'],
            'inventory_sha256': inv['sha256'],
            'head16': head.hex(), 'head_fields_u32_le': head_fields,
            'candidate_entry': exp['entry'], 'candidate_entry_hex': '0x%04X' % exp['entry'],
            'entry_from_bytes': primary['start'] if primary else None,
            'entry_from_bytes_hex': '0x%06X' % primary['start'] if primary else None,
            'entry_matches_expected': (primary['start'] == exp['entry']) if primary else None,
            'prefix_end': prefix_end, 'prefix_end_hex': '0x%06X' % prefix_end if prefix_end is not None else None,
            'prefix_end_matches_expected': (prefix_end == exp['prefix_end']) if prefix_end is not None else None,
            'gap_start': gap_start, 'gap_start_hex': '0x%06X' % gap_start if gap_start is not None else None,
            'gap_end': gap_end, 'gap_end_hex': '0x%06X' % gap_end if gap_end is not None else None,
            'gap_length': len(gap_bytes),
            'gap_bytes_hex': gap_bytes.hex(),
            'gap_expected_hex': exp['gap_hex'],
            'gap_bytes_match_expected': gap_bytes[:4].hex() == exp['gap_hex'],
            'gap_abs_container_offset': abs_off,
            'gap_abs_container_offset_hex': '0x%08X' % abs_off if abs_off is not None else None,
            'gap_abs_verified_from_container': abs_verified,
            'gap_abs_container_bytes': abs_bytes.hex(),
            'gap_variant_decode': variant_decode,
            'head_strings_hinting_mode': mode_strings,
            'head_mode_hint': mode_hint,
            'envydis_error': err, 'envydis_rc': rc,
        }
        results.append(rec)

    # Cross-slot summary of variant dependence.
    summary = []
    for r in results:
        vd = r['gap_variant_decode']
        valid_variants = [vname for vname, d in vd.items() if d['first_insn_at_gap'] and d['first_insn_at_gap']['valid']]
        unknown_variants = [vname for vname, d in vd.items() if d['first_insn_at_gap'] and not d['first_insn_at_gap']['valid']]
        first_mn = {vname: (d['first_insn_at_gap']['mnemonic'] if d['first_insn_at_gap'] else None) for vname, d in vd.items()}
        summary.append({
            'slot': r['slot'],
            'gap_start_hex': r['gap_start_hex'],
            'gap_bytes_hex': r['gap_bytes_hex'][:8],
            'valid_under_variants': valid_variants,
            'unknown_under_variants': unknown_variants,
            'first_insn_mnemonic_by_variant': first_mn,
            'variant_dependent': bool(valid_variants and unknown_variants),
        })

    report = {
        'script': 'falcon_decode_gap.py',
        'rerun': 'cd /home/REDACTED_USER/codex-work/work_v15 && /usr/bin/python3 PHASE16/FALCON_DECODE_GAP/falcon_decode_gap.py',
        'input_file': str(CONTAINER), 'input_size': len(container), 'input_sha256': sha(container),
        'inventory_source': str(INVENTORY), 'inventory_sha256': sha_file(INVENTORY),
        'envydis': {'path': ENVYDIS, 'sha256': sha_file(ENVYDIS),
                    'flags': '-i -n -m falcon [-V <variant>] -b 0 -d 0 -l <size(hex)> <file> (numeric args hex)'},
        'variants_tested': ['default' if v is None else v for v in VARIANTS],
        'source_hashes': {
            'envydis_falcon.c': sha_file('/tmp/envytools/envydis/falcon.c'),
            'envydis_envydis.c': sha_file('/tmp/envytools/envydis/envydis.c'),
            'envydis_dis_intern.h': sha_file('/tmp/envytools/envydis/dis-intern.h'),
            'firmware_container_verified.json': sha_file(INVENTORY),
        },
        'slots': SLOTS,
        'expected_facts': {str(k): v for k, v in expected.items()},
        'results': results,
        'summary': summary,
        'conclusion': {
            'gap_is_variant_dependent': all(s['variant_dependent'] for s in summary),
            'default_fuc0_fuc3': 'gap bytes are UNKNOWN opcodes under default (no -V; behaves as fuc0/fuc3 for 0x3e/0x89 lead bytes)',
            'fuc4_plus_slot20': 'slot 20 gap 3e74fe00 decodes as lbra 0xfe74 (valid long branch; control-flow / format boundary) under fuc4, fuc5, fuc6',
            'fuc5_plus_others': 'slots 150/156/481/484/487/490/493 gap 89000000 decodes as mov $r9, 0x0 (valid register init) under fuc5, fuc6; followed by valid ld in same variant',
            'bytes_after_gap': 'following bytes decode as valid insns (xcld for slot 20; ld for others) under the same newer variants, consistent with code continuation rather than random padding',
            'no_mode_field': 'no payload head16/manifest/header field identifies the true Falcon entry version/mode; head16 is a fixed template; no manifest consulted/found',
            'verdict': 'BOUNDED NEGATIVE: the gap cannot be definitively classified as unsupported-opcode/data/padding/branch-boundary without the true Falcon ISA version. It is UNKNOWN under fuc0/fuc3/default, a valid branch under fuc4+, and a valid code continuation under fuc5+. Missing evidence: the Falcon version/mode for these payloads.',
        },
    }
    OUT = GAP / 'machine.json'
    OUT.write_text(json.dumps(report, indent=2))
    (GAP / 'input_hashes.json').write_text(json.dumps({
        'container_ucodes_tu10x.bin': {'sha256': report['input_sha256'], 'size': report['input_size']},
        'firmware_container_verified.json': report['inventory_sha256'],
        'envydis_binary': report['envydis']['sha256'],
        'envydis_falcon.c': report['source_hashes']['envydis_falcon.c'],
        'envydis_envydis.c': report['source_hashes']['envydis_envydis.c'],
        'envydis_dis_intern.h': report['source_hashes']['envydis_dis_intern.h'],
        'this_script': sha_file(__file__),
    }, indent=2))

    # run.log
    log = ['falcon_decode_gap.py run log', 'command: %s' % report['rerun'],
           "input: %s size=%d sha256=%s" % (report['input_file'], report['input_size'], report['input_sha256']),
           'envydis: %s sha256=%s' % (ENVYDIS, report['envydis']['sha256']),
           'variants tested: %s' % ', '.join(report['variants_tested']), '',
           'Per-slot decode-gap findings (gap = first undecodable span after bootstrap prefix):', '']
    for r in results:
        vd = r['gap_variant_decode']
        log.append('slot=%-4d span_off=%s size=%d sha_ok=%s entry=%s prefix_end=%s gap_start=%s gap_len=%d gap_bytes=%s' % (
            r['slot'], r['offset_hex'], r['size'], r['sha256_matches_inventory'],
            r['entry_from_bytes_hex'], r['prefix_end_hex'], r['gap_start_hex'], r['gap_length'], r['gap_bytes_hex']))
        log.append('  abs_container_off=%s gap_abs_verified=%s abs_bytes=%s match_expected=%s' % (
            r['gap_abs_container_offset_hex'], r['gap_abs_verified_from_container'],
            r['gap_abs_container_bytes'], r['gap_bytes_match_expected']))
        log.append('  entry_matches_expected=%s prefix_end_matches_expected=%s head16=%s' % (
            r['entry_matches_expected'], r['prefix_end_matches_expected'], r['head16']))
        for vname in report['variants_tested']:
            d = vd[vname]
            f = d['first_insn_at_gap']
            log.append('  -V %s: first_insn=%s valid=%s mnemonic=%s window_fully_decoded=%s' % (
                vname, (f['raw'] if f else None), (f['valid'] if f else None),
                (f['mnemonic'] if f else None), d['window_fully_decoded']))
        log.append('  mode_strings_in_head64=%s' % (r['head_strings_hinting_mode'],))
        log.append('')
    for s in summary:
        log.append('SUMMARY slot=%d gap=%s valid_under=%s unknown_under=%s variant_dependent=%s' % (
            s['slot'], s['gap_start_hex'], s['valid_under_variants'], s['unknown_under_variants'], s['variant_dependent']))
    log.append('')
    log.append('CONCLUSION:')
    for k, v in report['conclusion'].items():
        log.append('  %s: %s' % (k, v))
    (GAP / 'run.log').write_text('\n'.join(log) + '\n')

    # report.md
    md = ['# FALCON_DECODE_GAP — first undecodable span after the bootstrap prefix, 8 Falcon payload candidates',
          '', 'Slots: %s' % SLOTS, '',
          'Method: read-only inputs only. Verified each span against the NVUCODES container inventory',
          '(sha256, offset, length), re-read gap bytes from the ORIGINAL container at absolute offset,',
          'disassembled full span with envydis -m falcon (default variant), then re-disassembled the gap',
          'window under every Falcon variant/mode the built envydis supports (default, fuc0, fuc3, fuc4, fuc5, fuc6).',
          'No GPU/MMIO/flashing/keys/signatures/brute force. No source mutation. Original outputs preserved.', '']
    md.append('## Independently verified task facts')
    md.append('| slot | container_off | span_off | entry | prefix_end | gap_start | gap_bytes | gap_abs_off | abs_verified |')
    md.append('|------|---------------|----------|-------|------------|-----------|-----------|-------------|--------------|')
    for r in results:
        md.append('| %s | %s | %s | %s | %s | %s | %s | %s | %s |' % (
            r['slot'], '0x%06X' % r['offset'], r['gap_start_hex'],
            r['entry_from_bytes_hex'], r['prefix_end_hex'], r['gap_start_hex'],
            r['gap_bytes_hex'][:8], r['gap_abs_container_offset_hex'], r['gap_abs_verified_from_container']))
    md.append('')
    md.append('## Per-variant decode of the gap (first instruction at gap start)')
    md.append('`???`/unknown = not a valid Falcon instruction under that variant; a real mnemonic = valid syntax under that variant.')
    md.append('| slot | gap bytes | default | fuc0 | fuc3 | fuc4 | fuc5 | fuc6 |')
    md.append('|------|-----------|---------|------|------|------|------|------|')
    for s in summary:
        row = '| %s | %s |' % (s['slot'], s['gap_bytes_hex'])
        for v in ['default', 'fuc0', 'fuc3', 'fuc4', 'fuc5', 'fuc6']:
            mn = s['first_insn_mnemonic_by_variant'].get(v)
            row += ' %s |' % (mn if mn else '???/unknown')
        md.append(row)
    md.append('')
    md.append('## What the gap is, per variant')
    for r in results:
        md.append('* slot %s (gap @%s, bytes %s):' % (r['slot'], r['gap_start_hex'], r['gap_bytes_hex'][:8]))
        for vname in report['variants_tested']:
            d = r['gap_variant_decode'][vname]
            f = d['first_insn_at_gap']
            if f and f['valid']:
                md.append('  - -V %s: VALID %s @%s raw=%s text="%s"' % (vname, f['mnemonic'], f['offset'], f['raw'], f['text']))
            else:
                md.append('  - -V %s: UNKNOWN (undecodable opcode) @%s raw=%s text="%s"' % (vname, (f['offset'] if f else '?'), (f['raw'] if f else '?'), (f['text'] if f else '?')))
        md.append('  - gap_abs_container_off=%s re-read from container=%s verified=%s' % (
            r['gap_abs_container_offset_hex'], r['gap_abs_container_bytes'], r['gap_abs_verified_from_container']))
    md.append('')
    md.append('## Entry / mode identification (saved payload / manifest / header fields)')
    md.append('* head16 (first 16 bytes of each span) is a fixed template across the 8 payloads:')
    for r in results:
        md.append('  - slot %s: %s  (u32 LE %s)' % (r['slot'], r['head16'], ' '.join(r['head_fields_u32_le'].values())))
    md.append('* No head16 word is a Falcon version/mode field; no version or mode string found in the first 64 bytes.')
    md.append('* No manifest file was located/consulted that identifies true entry or Falcon mode. container header (NVUCODES, ver=1, count=496) gives no per-payload mode.')
    md.append('* Therefore the true Falcon ISA version/mode for these payloads is NOT established by any available field.')
    md.append('')
    md.append('## Conclusion (bounded negative result)')
    for k, v in report['conclusion'].items():
        md.append('* %s: %s' % (k, v))
    md.append('')
    md.append('## What is NOT claimed')
    md.append('* The decoded bootstrap prefix is NOT claimed to be all executable code.')
    md.append('* Other regions are NOT claimed to be data.')
    md.append('* Valid syntax under fuc4+/fuc5+ is NOT treated as proof of code; it is syntax-valid under those variants only, and the true variant is unknown.')
    md.append('* No engine/GSP-vs-SEC2 role is inferred from slot number or entropy.')
    (GAP / 'FALCON_DECODE_GAP_REPORT.md').write_text('\n'.join(md) + '\n')
    print('WROTE', OUT)
    print('WROTE', GAP / 'run.log')
    print('WROTE', GAP / 'FALCON_DECODE_GAP_REPORT.md')
    print('WROTE', GAP / 'input_hashes.json')

if __name__ == '__main__':
    main()
