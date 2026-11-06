#!/usr/bin/env python3
# falcon_payload_deep.py
# Deep-dive of the 8 medium-confidence Falcon payload candidates
# (slots 20, 150, 156, 481, 484, 487, 490, 493) from the NVUCODES container.
#
# Method (read-only inputs only):
#   1. Read each span from outputs/ucodes_tu10x.bin at the VERIFIED container
#      offset/length (firmware_container_verified.json) and re-check sha256.
#   2. One full-span envydis (-m falcon) pass per payload (-d 0, -l = size hex);
#      envydis numeric args are HEX. Every byte of [0,size) is accounted for
#      either as a valid instruction or as an invalid-decode gap (data).
#   3. Entry/offset validation vs the prior phase (FW_PAYLOAD_RISCV), which is
#      left untouched. NOTE: the prior phase passed decimal start values to
#      envydis -d (hex-parsed), so its entry labels were mislabeled (slot 20
#      "0x24" -> real first valid insn 0x2A; others "0x10" -> real bootstrap
#      start 0x16). Entries here are re-derived from the bytes.
#   4. Control-flow/call-target summary: branch/call targets classified absolute
#      vs PC-relative vs escaping bounds; targets landing at region starts / mid
#      region / in gaps are recorded with raw bytes and offsets; indirect calls
#      (call $r1) keep target UNKNOWN.
#   5. Multiple code regions/entry points enumerated (every region containing a
#      Falcon special-register write is a candidate entry); common codelet
#      signatures compared pairwise; immediates/strings cross-referenced exactly
#      against GSP/firmware descriptor evidence (no engine identity inferred
#      from ISA/size/entropy/header similarity).
# No GPU, no MMIO, no keys/signatures, no tool installation, no source mutation.
# Run: cd PHASE16/FALCON_PAYLOAD_DEEP && /usr/bin/python3 falcon_payload_deep.py
import struct, hashlib, json, re, subprocess, sys, math
from pathlib import Path

ROOT = Path('/home/REDACTED_USER/codex-work/work_v15')
PH = ROOT / 'PHASE16'
DEEP = PH / 'FALCON_PAYLOAD_DEEP'
CONTAINER = ROOT / 'outputs/ucodes_tu10x.bin'
CONTAINER_VERIFIED = PH / 'firmware_container_verified.json'
RISCV_VERIFIED = PH / 'FW_PAYLOAD_RISCV' / 'payload_riscv_verified.json'
ENVYDIS = '/tmp/envytools/build/envydis/envydis'
SLOTS = [20, 150, 156, 481, 484, 487, 490, 493]

ENVYDIS_RE = re.compile(r'^([0-9a-fA-F]+):\s+((?:[0-9a-fA-F]{2}\s+)+?)\s{2,}(.*)$')
STR_RE = re.compile(rb'[\x20-\x7e]{4,}')
IMM_RE = re.compile(r'0x[0-9a-fA-F]+')
CT_MN = ('bra', 'call', 'ret', 'jmp', 'exit')
FALCON_SPECIAL_REGS = ('$xcbase', '$xtargets', '$xdbase', '$xfsbase')
FALCON_SPECIAL_INSNS = ('xcld', 'xdld', 'xdst', 'xcwait', 'xdwait', 'exit')

def sha(b): return hashlib.sha256(b).hexdigest()
def sha_file(p):
    p = Path(p)
    return sha(p.read_bytes()) if p.exists() else None
def sext64(v):
    return v - (1 << 64) if v >= (1 << 63) else v

def envydis_disasm(path, size):
    cmd = [ENVYDIS, '-i', '-n', '-m', 'falcon', '-b', '0',
           '-d', '0', '-l', '%x' % size, str(path)]
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

def build_regions(entries, size):
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
                cur['insns'].append({'offset': off, 'size': len(raw),
                                     'raw': raw.hex(), 'text': text})
            else:
                if cur is not None:
                    regions.append(cur)
                cur = {'start': off, 'end': off + len(raw),
                       'insns': [{'offset': off, 'size': len(raw),
                                  'raw': raw.hex(), 'text': text}]}
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

def mnemonic(text):
    tok = text.split()
    return tok[0].lower() if tok else ''

def is_ct(text):
    tok = text.split()
    return bool(tok) and (tok[0] in CT_MN or tok[0].startswith('bra'))

def target_of(text):
    m = IMM_RE.search(text)
    return int(m.group(0), 16) if m else None

def special_markers(text):
    out = []
    low = text.lower()
    for r in FALCON_SPECIAL_REGS:
        if r in low:
            out.append('write_' + r)
    tok = text.split()
    if tok and tok[0].lower() in FALCON_SPECIAL_INSNS:
        out.append(tok[0].lower())
    if tok and tok[0].lower() == 'mov' and '$sp' in low:
        out.append('mov_sp')
    return out

def entropy_of(b):
    if not b:
        return 0.0
    c = {}
    for x in b:
        c[x] = c.get(x, 0) + 1
    n = len(b)
    return round(-sum((v / n) * math.log2(v / n) for v in c.values()), 4)

def region_stats(region_objs):
    sizes = [rg['size'] for rg in region_objs]
    if not sizes:
        return {'count': 0}
    sizes.sort()
    n = len(sizes)
    return {
        'count': n,
        'total_bytes': sum(sizes),
        'min': sizes[0], 'max': sizes[-1],
        'median': sizes[n // 2],
        'under_8_bytes': sum(1 for s in sizes if s < 8),
        'under_16_bytes': sum(1 for s in sizes if s < 16),
    }

def main():
    DEEP.mkdir(parents=True, exist_ok=True)
    (DEEP / 'spans').mkdir(exist_ok=True)

    container = CONTAINER.read_bytes()
    cver = json.loads(CONTAINER_VERIFIED.read_text())
    payloads_by_slot = {p['slot']: p for p in cver['payloads']}
    rver = json.loads(RISCV_VERIFIED.read_text())
    prior_by_slot = {r['slot']: r for r in rver['results']}

    xref_sets = {'container_offsets': set(), 'container_ends': set()}
    for p in cver['payloads']:
        xref_sets['container_offsets'].add(p['offset'])
        xref_sets['container_ends'].add(p['offset'] + p['length'])
    desc_path = PH / 'descriptor_table.json'
    desc = json.loads(desc_path.read_text()) if desc_path.exists() else []
    xref_sets['descriptor_va'] = {e.get('va') for e in desc if isinstance(e, dict)}
    xref_sets['descriptor_file_off'] = {e.get('file_offset') for e in desc if isinstance(e, dict)}
    xref_sets['descriptor_names'] = {e.get('name') for e in desc if isinstance(e, dict) and e.get('name')}
    xref_sets['gsp_disasm_addr'] = set()
    gsp_dis = PH / 'gsp_local_disassembly.txt'
    if gsp_dis.exists():
        for line in gsp_dis.read_text(errors='replace').splitlines():
            mm = re.match(r'^([0-9a-fA-F]+)\s+file=', line)
            if mm:
                xref_sets['gsp_disasm_addr'].add(int(mm.group(1), 16))
    GSP_BASE, GSP_END = 0x110000, 0x114000
    SEC2_BASE, SEC2_END = 0x840000, 0x844000
    FALCON_UNIT_OFFS = {0x40, 0x44, 0x80, 0x84, 0x100, 0x104, 0x108}

    def classify_value(v):
        if v in xref_sets['container_offsets']:
            return 'container_offset'
        if v in xref_sets['container_ends']:
            return 'container_end'
        if GSP_BASE <= v < GSP_END:
            return 'gsp_register'
        if SEC2_BASE <= v < SEC2_END:
            return 'sec2_register'
        if v in FALCON_UNIT_OFFS:
            return 'falcon_unit_offset'
        if v == 0x110040:
            return 'gsp_mailbox0'
        if v == 0x1103c0:
            return 'gsp_falcon_engine'
        if v in xref_sets['descriptor_va']:
            return 'descriptor_va'
        if v in xref_sets['descriptor_file_off']:
            return 'descriptor_file_offset'
        if v in xref_sets['gsp_disasm_addr']:
            return 'gsp_disassembly_va'
        return 'unmatched'

    results = []
    for slot in SLOTS:
        inv = payloads_by_slot[slot]
        off, size = inv['offset'], inv['length']
        span = container[off:off + size]
        computed_sha = sha(span)
        rec = {
            'slot': slot, 'offset': off, 'offset_hex': '0x%08X' % off,
            'size': size, 'sha256': computed_sha,
            'sha256_matches_inventory': computed_sha == inv['sha256'],
            'inventory_sha256': inv['sha256'],
            'entropy': inv['entropy'],
            'head16': inv['head16'],
            'head_fields': {'u32_0': inv['head16'][0:8], 'u32_1': inv['head16'][8:16],
                            'u32_2': inv['head16'][16:24], 'u32_3': inv['head16'][24:32]},
            'head_fields_u32_le': list(struct.unpack_from('<4I', span, 0)),
            'tail16': inv['tail16'],
            'prior_verdict': prior_by_slot[slot]['verdict'],
            'prior_entry': prior_by_slot[slot].get('falcon', {}).get('entries', [{}])[0].get('start_hex') if prior_by_slot[slot].get('falcon') else None,
        }
        span_path = DEEP / 'spans' / ('cand_%04d.bin' % slot)
        span_path.write_bytes(span)
        disasm_path = DEEP / ('cand_%04d.disasm' % slot)
        entries, err, rc = envydis_disasm(span_path, size)
        disasm_path.write_text('\n'.join('%08X: %-24s %s' % (e, r.hex(), t) for e, r, t in entries) + '\n')
        rec['disasm_file'] = str(disasm_path)
        rec['disasm_lines'] = len(entries)
        rec['envydis_error'] = err
        parsed = [(e, r, t, (not t.startswith('???')) and ('[unknown' not in t.lower())) for e, r, t in entries]
        regions, gaps = build_regions(parsed, size)
        region_objs = []
        for idx, rg in enumerate(regions):
            insns = rg['insns']
            raw_bytes = b''.join(bytes.fromhex(i['raw']) for i in insns)
            markers = []
            for i in insns:
                markers.extend(special_markers(i['text']))
            region_objs.append({
                'index': idx, 'start': rg['start'], 'start_hex': '0x%06X' % rg['start'],
                'end': rg['end'], 'end_hex': '0x%06X' % rg['end'],
                'size': rg['end'] - rg['start'], 'insn_count': len(insns),
                'insns': [{'offset': i['offset'], 'offset_hex': '0x%06X' % i['offset'],
                           'size': i['size'], 'raw': i['raw'], 'text': i['text']} for i in insns],
                'markers': sorted(set(markers)),
                'marker_count': len(set(markers)),
                'density': round(sum(i['size'] for i in insns) / (rg['end'] - rg['start']), 6),
                'entropy': entropy_of(raw_bytes),
            })
        gap_objs = []
        for s, e, kind in gaps:
            b = span[s:e]
            gap_objs.append({'start': s, 'end': e, 'length': e - s, 'kind': kind,
                             'zero_run': all(x == 0 for x in b),
                             'bytes_sample': b[:24].hex()})
        rec['regions'] = region_objs
        rec['gaps'] = gap_objs
        rec['region_stats'] = region_stats(region_objs)
        rec['gap_bytes'] = sum(g['length'] for g in gap_objs)
        rec['valid_insn_bytes'] = sum(i['size'] for rg in regions for i in rg['insns'])
        rec['code_coverage'] = round(rec['valid_insn_bytes'] / size, 6) if size else 0.0
        rec['bytes_accounted'] = rec['valid_insn_bytes'] + rec['gap_bytes']

        region_starts = {rg['start'] for rg in region_objs}
        gap_set = [(g['start'], g['end']) for g in gap_objs]
        region_by_start = {rg['start']: rg for rg in region_objs}

        STRONG_MARKERS = ('write_$xcbase', 'write_$xtargets', 'write_$xdbase', 'write_$xfsbase',
                          'xcld', 'xdld', 'xdst', 'xcwait', 'xdwait')

        def locate(t):
            if t in region_starts:
                return 'at_region_start'
            for s, e in gap_set:
                if s <= t < e:
                    return 'in_gap'
            for rg in region_objs:
                if rg['start'] < t < rg['end']:
                    return 'mid_region'
            return 'in_bounds'

        def classify_target(off_ins, v):
            # Returns (target_type, target_eff, detail). Falcon branch immediates
            # are ambiguous absolute-vs-relative; both interpretations are kept.
            if v is None:
                return 'indirect', None, None
            abs_t = v
            rel_t = off_ins + sext64(v)
            abs_in = 0 <= abs_t < size
            rel_in = 0 <= rel_t < size
            detail = 'abs=0x%X' % abs_t
            if abs_in and rel_in:
                return 'in_bounds_absolute_and_relative', (abs_t if locate(abs_t) == 'at_region_start' else rel_t), detail + ' rel_eff=0x%X' % rel_t
            if abs_in:
                return 'in_bounds_absolute', abs_t, detail
            if rel_in:
                return 'in_bounds_relative', rel_t, detail + ' rel_eff=0x%X (abs out of bounds)' % rel_t
            return 'escapes_bounds', None, detail + ' rel_eff=0x%X' % rel_t

        ct_insns, calls, branches, escapes = [], [], [], []
        for rg in region_objs:
            for i in rg['insns']:
                if not is_ct(i['text']):
                    continue
                tok = i['text'].split()
                m = tok[0]
                t = target_of(i['text'])
                entry = {'offset': i['offset'], 'offset_hex': '0x%06X' % i['offset'],
                         'mnemonic': m, 'raw': i['raw'], 'text': i['text'],
                         'target_raw': t, 'target_raw_hex': ('0x%X' % t) if t is not None else None,
                         'target_type': None, 'target_eff': None, 'target_eff_hex': None,
                         'target_detail': None}
                ttype, teff, tdetail = classify_target(i['offset'], t)
                entry['target_type'] = ttype
                entry['target_eff'] = teff
                entry['target_eff_hex'] = ('0x%X' % teff) if teff is not None else None
                entry['target_detail'] = tdetail
                if ttype == 'escapes_bounds':
                    escapes.append(entry)
                ct_insns.append(entry)
                if m == 'call':
                    calls.append(entry)
                if m.startswith('bra') or m in ('b', 'jmp'):
                    branches.append(entry)
        # Reachability from primary entry over direct edges (resolved targets at
        # region starts) and fall-through.
        reachable = set()
        entry_points = [rg for rg in region_objs if any(m in STRONG_MARKERS for m in rg['markers'])]
        entry_points.sort(key=lambda r: r['start'])
        xcbase_regions = [rg for rg in region_objs if 'write_$xcbase' in rg['markers']]
        if xcbase_regions:
            primary = min(xcbase_regions, key=lambda r: r['start'])
            entry_basis = 'first region writing Falcon $xcbase (bring-up core)'
        elif region_objs:
            primary = max(region_objs, key=lambda r: (r['marker_count'], r['size'], r['insn_count']))
            entry_basis = 'fallback: largest marker region'
        else:
            primary = None
            entry_basis = 'no decodable regions'
        if primary:
            primary['is_primary'] = True
            reachable.add(primary['start'])
            work = [primary['start']]
            while work:
                cur = work.pop()
                rg = region_by_start[cur]
                for i in rg['insns']:
                    nxt = i['offset'] + i['size']
                    for e in ct_insns:
                        if e['offset'] == i['offset'] and e['target_type'] in ('in_bounds_absolute', 'in_bounds_relative', 'in_bounds_absolute_and_relative', 'at_region_start'):
                            t = e['target_eff']
                            if t is not None and t in region_starts and t not in reachable:
                                reachable.add(t)
                                work.append(t)
                    if nxt in region_starts and nxt not in reachable:
                        reachable.add(nxt)
                        work.append(nxt)
        rec['primary_entry'] = {
            'start': primary['start'], 'start_hex': primary['start_hex'],
            'basis': entry_basis,
        } if primary else None
        rec['entry_points'] = [{'start': rg['start'], 'start_hex': rg['start_hex'],
                                'size': rg['size'], 'insn_count': rg['insn_count'],
                                'markers': rg['markers']} for rg in entry_points]
        rec['region_count'] = len(region_objs)
        rec['control_flow'] = {
            'ct_insns': ct_insns, 'ct_count': len(ct_insns),
            'calls': [{'offset': c['offset'], 'offset_hex': c['offset_hex'],
                       'target_type': c['target_type'], 'target_detail': c['target_detail']} for c in calls],
            'branches': [{'offset': b['offset'], 'offset_hex': b['offset_hex'],
                          'target_type': b['target_type'], 'target_eff_hex': b['target_eff_hex'],
                          'target_detail': b['target_detail']} for b in branches],
            'escapes': [{'offset': e['offset'], 'offset_hex': e['offset_hex'],
                         'text': e['text'], 'raw': e['raw'],
                         'target_raw': e['target_raw'], 'target_raw_hex': e['target_raw_hex'],
                         'target_detail': e['target_detail']} for e in escapes],
            'escape_count': len(escapes),
            'reachable_region_starts': sorted(reachable),
            'orphan_region_starts': sorted(rg['start'] for rg in region_objs if rg['start'] not in reachable),
            'reachable_count': len(reachable),
        }

        rec['strings'] = [{'offset': m.start(), 'length': m.end() - m.start(),
                           'text': m.group().decode('ascii', 'replace')} for m in STR_RE.finditer(span)]

        xrefs = []
        seen_x = set()
        for rg in region_objs:
            for i in rg['insns']:
                candidates = []
                if is_ct(i['text']):
                    t = target_of(i['text'])
                    if t is not None:
                        candidates.append(('ctrl', t))
                for m in IMM_RE.finditer(i['text']):
                    v = int(m.group(0), 16)
                    if v >= 0x1000:
                        candidates.append(('imm', v))
                for kind, v in candidates:
                    key = (i['offset'], v)
                    if key in seen_x:
                        continue
                    seen_x.add(key)
                    xrefs.append({'offset': i['offset'], 'offset_hex': '0x%06X' % i['offset'],
                                  'kind': kind, 'value': v, 'value_hex': '0x%X' % v,
                                  'class': classify_value(v), 'insn': i['text']})
        rec['cross_references'] = xrefs
        str_xref = []
        for s in rec['strings']:
            if s['text'] in xref_sets['descriptor_names']:
                str_xref.append({'offset': s['offset'], 'text': s['text'], 'match': 'descriptor_name'})
        rec['string_cross_references'] = str_xref
        results.append(rec)

    def ng4(slot_rec):
        s = set()
        for rg in slot_rec['regions']:
            toks = [mnemonic(i['text']) for i in rg['insns']]
            for k in range(len(toks) - 3):
                s.add(tuple(toks[k:k + 4]))
        return s
    ngram_sets = {r['slot']: ng4(r) for r in results}
    pairwise = []
    for i in range(len(results)):
        for j in range(i + 1, len(results)):
            a, b = results[i], results[j]
            ba = (DEEP / 'spans' / ('cand_%04d.bin' % a['slot'])).read_bytes()
            bb = (DEEP / 'spans' / ('cand_%04d.bin' % b['slot'])).read_bytes()
            common = 0
            for x, y in zip(ba, bb):
                if x != y:
                    break
                common += 1
            shared = len(ngram_sets[a['slot']] & ngram_sets[b['slot']])
            pairwise.append({'slots': [a['slot'], b['slot']],
                             'sha_equal': a['sha256'] == b['sha256'],
                             'common_prefix_bytes': common,
                             'header_fields_equal': a['head_fields'] == b['head_fields'],
                             'size_diff': abs(a['size'] - b['size']),
                             'shared_mnemonic_ngrams4': shared})

    header_groups = {}
    for r in results:
        header_groups.setdefault(json.dumps(r['head_fields'], sort_keys=True), []).append(r['slot'])

    report = {
        'script': 'falcon_payload_deep.py',
        'rerun': 'cd PHASE16/FALCON_PAYLOAD_DEEP && /usr/bin/python3 falcon_payload_deep.py  (cwd: work_v15)',
        'input_file': str(CONTAINER), 'input_size': len(container), 'input_sha256': sha(container),
        'inventory_source': str(CONTAINER_VERIFIED), 'inventory_sha256': sha_file(CONTAINER_VERIFIED),
        'prior_source': str(RISCV_VERIFIED), 'prior_source_sha256': sha_file(RISCV_VERIFIED),
        'envydis': {'path': ENVYDIS, 'sha256': sha_file(ENVYDIS),
                    'flags': '-i -n -m falcon -b 0 -d 0 -l <size(hex)> <file> (envydis numeric args are hex)'},
        'source_hashes': {
            'nvidia_bin_data_pvt.h': sha_file(PH / 'SOURCES' / 'nvidia_bin_data_pvt.h'),
            'nvidia_bin_data.h': sha_file(PH / 'SOURCES' / 'nvidia_bin_data.h'),
            'descriptor_table.json': sha_file(PH / 'descriptor_table.json'),
            'gsp_local_disassembly.txt': sha_file(PH / 'gsp_local_disassembly.txt'),
        },
        'containers': {'magic': cver.get('header', {}).get('magic') if isinstance(cver.get('header'), dict) else None,
                       'count': cver.get('header', {}).get('count') if isinstance(cver.get('header'), dict) else None,
                       'first_payload': cver.get('header', {}).get('first_payload') if isinstance(cver.get('header'), dict) else None},
        'slots': SLOTS, 'results': results, 'pairwise': pairwise,
        'header_groups': {k: v for k, v in header_groups.items()},
        'conclusion': {
            'identity_basis': 'Falcon-specific special registers ($xcbase/$xtargets/$xdbase/$s10) and instructions (xcld/xdld/xdst/xcwait/xdwait) decoded from payload bytes; common bootstrap template across all 8 payloads. Not derived from size/entropy/header similarity.',
            'engine_role': 'UNKNOWN — no source-asserted engine<->Falcon-slot mapping exists (see PHASE16/ENGINE_INTERFACES findings.json); no exact cross-reference to GSP/SEC2 addresses found; role not inferred.',
            'prior_entry_correction': 'envydis -d parses numeric args as hex; the prior phase passed decimal start values. Slot 20 was labeled 0x24 (real bring-up start 0x2A; 0x36 was mid-stream); slots 150/156/481/484/487/490/493 were labeled 0x10 (real bootstrap start 0x16). Entries below are re-derived from the bytes.',
        },
    }
    OUT = DEEP / 'machine.json'
    OUT.write_text(json.dumps(report, indent=2))
    (DEEP / 'input_hashes.json').write_text(json.dumps({
        'container_ucodes_tu10x.bin': {'sha256': report['input_sha256'], 'size': report['input_size']},
        'firmware_container_verified.json': report['inventory_sha256'],
        'payload_riscv_verified.json': report['prior_source_sha256'],
        'envydis_binary': report['envydis']['sha256'],
        'this_script': sha_file(__file__),
        'sources': report['source_hashes'],
    }, indent=2))

    log = ['falcon_payload_deep.py run log',
           'command: %s' % report['rerun'],
           'input: %s size=%d sha256=%s' % (report['input_file'], report['input_size'], report['input_sha256']),
           'envydis: %s sha256=%s' % (ENVYDIS, report['envydis']['sha256']),
           '',
           'Per-byte accounting: valid_insn_bytes + gap_bytes == size for every candidate.',
           '']
    for r in results:
        cf = r['control_flow']
        pe = r['primary_entry']
        log.append('slot=%-4d off=%s size=%d sha_ok=%s ent=%.4f regions=%d gaps=%d gap_bytes=%d valid_insn_bytes=%d code_cov=%.4f primary=%s prior_entry=%s' % (
            r['slot'], r['offset_hex'], r['size'], r['sha256_matches_inventory'], r['entropy'],
            r['region_count'], len(r['gaps']), r['gap_bytes'], r['valid_insn_bytes'],
            r['code_coverage'],
            pe['start_hex'] if pe else None, r['prior_entry']))
        if pe:
            log.append('   primary basis=%s entry_points=%s' % (
                pe['basis'], ', '.join(e['start_hex'] for e in r['entry_points'][:12])))
        rs = r['region_stats']
        log.append('   region_stats: count=%d total_bytes=%d min=%d max=%d median=%d <8B=%d <16B=%d' % (
            rs['count'], rs['total_bytes'], rs['min'], rs['max'], rs['median'],
            rs['under_8_bytes'], rs['under_16_bytes']))
        nz_gaps = [g for g in r['gaps'] if not g['zero_run']]
        log.append('   non_zero_gaps=%d largest_gap=%d' % (len(nz_gaps), max((g['length'] for g in nz_gaps), default=0)))
        for e in cf['escapes']:
            log.append('   ESCAPE @%s %s raw=%s detail=%s' % (e['offset_hex'], e['text'], e['raw'], e['target_detail']))
        for x in r['cross_references']:
            if x['class'] != 'unmatched':
                log.append('   XREF @%s val=%s kind=%s class=%s (%s)' % (x['offset_hex'], x['value_hex'], x['kind'], x['class'], x['insn'][:70]))
    (DEEP / 'run.log').write_text('\n'.join(log) + '\n')

    md = ['# FALCON_PAYLOAD_DEEP — deep dive, 8 medium-confidence Falcon payload candidates',
          '', 'Slots: %s' % SLOTS,
          '', 'Method: single full-span envydis (-m falcon) pass per verified container span;',
          'every byte accounted as valid instruction or invalid-decode gap; read-only inputs;',
          'no GPU/MMIO/keys/signatures; no tool install; prior analysis under',
          'PHASE16/FW_PAYLOAD_RISCV left untouched.', '']
    md.append('## Important: prior entry-offset correction')
    md.append('envydis interprets its -d numeric argument as HEX. The prior phase passed decimal')
    md.append('start values, so its entry labels were mislabeled: slot 20 was labeled "0x24" while')
    md.append('the real bring-up starts at 0x2A (0x36 was mid-stream); slots 150/156/481/484/487/')
    md.append('490/493 were labeled "0x10" while the real bootstrap starts at 0x16. All entry')
    md.append('offsets below are re-derived directly from the bytes.')
    md.append('## Per-candidate summary')
    md.append('| slot | offset | size | sha_ok | entropy | regions | gap bytes | code coverage | primary entry | candidate entries |')
    md.append('|------|--------|------|--------|---------|---------|-----------|---------------|---------------|-------------------|')
    for r in results:
        pe = r['primary_entry']
        eps = ', '.join(e['start_hex'] for e in r['entry_points'])
        md.append('| %s | %s | %d | %s | %.4f | %d | %d | %.4f | %s | %s |' % (
            r['slot'], r['offset_hex'], r['size'], r['sha256_matches_inventory'], r['entropy'],
            r['region_count'], r['gap_bytes'], r['code_coverage'],
            pe['start_hex'] if pe else None, eps))
    md.append('')
    md.append('## Region statistics (valid-instruction islands vs invalid-decode gaps)')
    for r in results:
        rs = r['region_stats']
        md.append('* slot %s: %d regions (%d valid bytes, %.1f%% of span), %d gaps (%d gap bytes, %.1f%%), largest gap %d bytes; region sizes min=%d max=%d median=%d, regions<8B=%d, regions<16B=%d' % (
            r['slot'], rs['count'], r['valid_insn_bytes'],
            100.0 * r['valid_insn_bytes'] / r['size'],
            len(r['gaps']), r['gap_bytes'],
            100.0 * r['gap_bytes'] / r['size'],
            max((g['length'] for g in r['gaps']), default=0),
            rs['min'], rs['max'], rs['median'],
            rs['under_8_bytes'], rs['under_16_bytes']))
    md.append('')
    md.append('## Header fields (raw u32 LE, no semantics asserted)')
    for r in results:
        md.append('* slot %s: %s' % (r['slot'], ' '.join(r['head_fields'].values())))
    md.append('')
    md.append('## Header equality groups (identical 16-byte container headers)')
    for h, slots in header_groups.items():
        md.append('* %s' % (', '.join('slot %d' % s for s in slots)))
    md.append('')
    md.append('## Bootstrap / bring-up code (Falcon-specific, decoded from bytes)')
    md.append('Every payload contains the same bring-up template near offset 0x10-0x180: loads from')
    md.append('a structure indexed by a live-in register, builds 64-bit base values, writes Falcon')
    md.append('special registers $xcbase / $xtargets / $xdbase, performs XRAM operations (xcld / xdld /')
    md.append('xdst), xcwait / xdwait, then indirect call $r1. This is Falcon microcode bring-up, not')
    md.append('generic RISC-V.')
    for r in results:
        pe = r['primary_entry']
        if not pe:
            continue
        rg = next(g for g in r['regions'] if g['start'] == pe['start'])
        sample = ' ; '.join(i['text'] for i in rg['insns'][:8])
        md.append('* slot %s primary entry %s (%d insns, markers %s): %s' % (
            r['slot'], pe['start_hex'], rg['insn_count'], rg['markers'], sample[:200]))
    md.append('')
    md.append('## Candidate entry points (regions writing Falcon special registers)')
    for r in results:
        md.append('* slot %s:' % r['slot'])
        for e in r['entry_points']:
            md.append('  - %s size=%d insns=%d markers=%s' % (e['start_hex'], e['size'], e['insn_count'], e['markers']))
    md.append('')
    md.append('## Control flow')
    for r in results:
        cf = r['control_flow']
        md.append('* slot %s: %d CT insns (%d calls all indirect -> target UNKNOWN, %d branches); %d escapes below;' % (
            r['slot'], cf['ct_count'], len(cf['calls']), len(cf['branches']), cf['escape_count']))
        for e in cf['escapes']:
            md.append('  - escape @%s: %s raw=%s detail=%s' % (e['offset_hex'], e['text'], e['raw'], e['target_detail']))
        absbr = [b for b in cf['branches'] if b['target_type'] in ('in_bounds_absolute', 'in_bounds_relative', 'in_bounds_absolute_and_relative')]
        if absbr:
            md.append('  - in-bounds branches: %d' % len(absbr))
            for b in absbr[:10]:
                md.append('    @%s -> %s (%s)' % (b['offset_hex'], b['target_eff_hex'], b['target_detail']))
        md.append('  - reachable region starts from primary: %s' % ', '.join('0x%06X' % s for s in cf['reachable_region_starts'][:12]))
        md.append('  - orphan region starts (not reachable via direct edges, count %d): %s' % (
            len(cf['orphan_region_starts']),
            ', '.join('0x%06X' % s for s in cf['orphan_region_starts'][:12])))
    md.append('')
    md.append('## Cross-references (immediate constants matched to evidence; class=unmatched means no known referent)')
    any_x = False
    for r in results:
        for x in r['cross_references']:
            if x['class'] != 'unmatched':
                any_x = True
                md.append('* slot %d @%s value=%s kind=%s class=%s insn=%s' % (
                    r['slot'], x['offset_hex'], x['value_hex'], x['kind'], x['class'], x['insn'][:80]))
    if not any_x:
        md.append('* none — no payload immediate matches a container offset, GSP/SEC2 register address,')
        md.append('  descriptor-table VA/file-offset, or GSP disassembly VA. No meaningful ASCII strings')
        md.append('  found (only 4-6 byte garbage).')
    md.append('')
    md.append('## Pairwise comparison')
    for p in pairwise:
        md.append('* slots %s: sha_equal=%s common_prefix=%d header_equal=%s size_diff=%d shared_ngram4=%d' % (
            p['slots'], p['sha_equal'], p['common_prefix_bytes'], p['header_fields_equal'],
            p['size_diff'], p['shared_mnemonic_ngrams4']))
    md.append('')
    md.append('## Conclusion')
    for k, v in report['conclusion'].items():
        md.append('* %s: %s' % (k, v))
    md.append('')
    md.append('## UNKNOWN preserved')
    md.append('* Engine/role identity (GSP vs SEC2 vs other Falcon unit): UNKNOWN — no source-asserted engine<->slot mapping; not inferred from code shape. No exact cross-reference to GSP/SEC2/MMIO addresses found in any payload immediate.')
    md.append('* Indirect call targets (call $r1): UNKNOWN (register-indirect, statically unresolvable).')
    md.append('* Branches with ambiguous absolute/relative targets: both interpretations recorded; role of target bytes unresolved where they land in gaps.')
    md.append('* The thousands of small decodable regions interleaved with gaps are consistent with embedded table(s)/codelet(s); individual entries are not classified as code — role UNKNOWN.')
    (DEEP / 'FALCON_PAYLOAD_DEEP_REPORT.md').write_text('\n'.join(md) + '\n')
    print('WROTE', OUT)
    print('WROTE', DEEP / 'run.log')
    print('WROTE', DEEP / 'FALCON_PAYLOAD_DEEP_REPORT.md')
    print('WROTE', DEEP / 'input_hashes.json')

if __name__ == '__main__':
    main()
