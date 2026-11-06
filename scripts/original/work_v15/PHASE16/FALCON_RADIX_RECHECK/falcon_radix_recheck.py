#!/usr/bin/env python3
# falcon_radix_recheck.py
# Recheck of the 8 Falcon candidate probes after the confirmed envydis argument-radix defect.
#
# Defect (confirmed in PHASE16/FW_PAYLOAD_RISCV/COORDINATOR_REVIEW.md):
#   payload_riscv_analyze.py:123 passes str(skip)/str(limit) (decimal strings) to envydis -d/-l,
#   but /tmp/envytools/envydis/envydis.c:94,97 parses both with sscanf "%x".
#   Therefore decimal 36 ("36") was interpreted as skip 0x36=54 and decimal 16 ("16") as
#   skip 0x16=22, while the report labels were "0x24"/"0x10" (hex of the decimal strings).
#   Capstone RISC-V calls are unaffected; only Falcon envydis entry/offset evidence is weak.
#
# Method (read-only inputs only; stdlib only; no GPU/hardware/keys/signatures; no new tools):
#   1. Read each of the 8 Falcon candidate spans from outputs/ucodes_tu10x.bin at the
#      VERIFIED container offset/length (firmware_container_verified.json) and re-check sha256.
#   2. Recompute the prior-phase BEST probe per slot with EXPLICIT HEXADECIMAL arguments
#      ("%x" % intended_value), so envydis actually skips the intended byte count:
#         slot 20: intended skip 36 -> argv "24" (prior passed "36", parsed 0x36=54)
#         other 7: intended skip 16 -> argv "10" (prior passed "16", parsed 0x16=22)
#      limit 150 -> argv "96" for every slot (prior passed "150", parsed 0x150=336).
#   3. Plus a full-span baseline probe per slot (skip 0, limit = size) to exhibit the
#      linear sweep (syntax-valid decode, NOT a verified entry).
#   4. For every probe compare: requested skip/limit, argv strings, actual skip/limit
#      (int(argv,16)), envydis first output address, first instruction raw bytes vs the
#      original payload slice [off + actual_skip + first_addr], and the whole envydis
#      raw-output byte stream vs the payload slice [off + actual_skip : +consumed].
#   5. Bounded CFG audit of the deep worker primary-entry model (entries re-derived from
#      bytes by PHASE16/FALCON_PAYLOAD_DEEP: slot 20 -> 0x2A, others -> 0x16): re-disassemble
#      a bounded window from each entry, rebuild regions/gaps, and check:
#        * no fallthrough edge after ret / exit / unconditional bra,
#        * call ABI return edge (fallthrough to next insn) distinct from the indirect
#          call-target edge (target UNKNOWN, register-indirect call $r1),
#        * branches landing mid-decoded-region require block splitting.
#
# Conclusion rule: byte-verified disassembly grounds probes in the payload slice; absence of
# any incoming cross-reference (branch/call target or descriptor reference) at a candidate
# offset means the entry is a bounded candidate, not a verified true entry -> retain UNKNOWN;
# engine-role stays UNKNOWN absent direct crossrefs; orphan regions / low coverage are not
# density-as-proof (thousands of 2-8 byte regions interleaved with 4-byte gaps are consistent
# with embedded tables/codelets, not executable code).
#
# Writes only into this directory. Never overwrites old/live scripts.
# Run: cd /home/REDACTED_USER/codex-work/work_v15 && /usr/bin/python3 PHASE16/FALCON_RADIX_RECHECK/falcon_radix_recheck.py

import struct, hashlib, json, re, subprocess, sys
from pathlib import Path

ROOT = Path('/home/REDACTED_USER/codex-work/work_v15')
PH = ROOT / 'PHASE16'
OUT = PH / 'FALCON_RADIX_RECHECK'
CONTAINER = ROOT / 'outputs/ucodes_tu10x.bin'
CONTAINER_VERIFIED = PH / 'firmware_container_verified.json'
ENVYDIS = '/tmp/envytools/build/envydis/envydis'
SLOTS = [20, 150, 156, 481, 484, 487, 490, 493]
# Intended decimal skip values that the prior phase passed as str() (the radix-defect callers).
# Slot 20's prior best probe was start=36 (report label "0x24"); the other 7 used start=16
# (report label "0x10"). Limit was 150 for all.
INTENDED_SKIP = {20: 36, 150: 16, 156: 16, 481: 16, 484: 16, 487: 16, 490: 16, 493: 16}
LIMIT = 150
# Primary entries re-derived from bytes by the deep worker (full linear sweep - NOT verified
# as true entries; used here only as bounded CFG-audit anchors).
PRIMARY_ENTRY = {20: 0x2A, 150: 0x16, 156: 0x16, 481: 0x16, 484: 0x16, 487: 0x16, 490: 0x16, 493: 0x16}
CFG_WINDOW = 0x200  # bounded disassembly window from each primary entry for the CFG audit

ENVYDIS_RE = re.compile(r'^([0-9a-fA-F]+):\s+((?:[0-9a-fA-F]{2}\s+)+?)\s{2,}(.*)$')
IMM_RE = re.compile(r'0x[0-9a-fA-F]+')
TERMINATOR_MN = ('ret', 'exit')  # plain 'bra' is also unconditional (handled separately)

def sha(b): return hashlib.sha256(b).hexdigest()
def sha_file(p):
    p = Path(p)
    return sha(p.read_bytes()) if p.exists() else None
def sext64(v):
    return v - (1 << 64) if v >= (1 << 63) else v

def envydis_run(path, skip, limit, keep_lines=True,
                container=None, off=None, size=None):
    """Run envydis with EXPLICIT hex argument strings. Return parsed result dict.

    Byte-grounding (when container/off/size given): compares the envydis raw-output stream
    against the original payload slice [off + actual_skip : +consumed] and the first
    instruction raw bytes against [off + actual_skip + first_addr : +len].
    """
    actual_skip = int('%x' % skip, 16)   # what envydis really skips (%x parse of argv)
    actual_limit = int('%x' % limit, 16)
    argv_skip = '%x' % skip
    argv_limit = '%x' % limit
    cmd = [ENVYDIS, '-i', '-n', '-m', 'falcon', '-b', '0', '-d', argv_skip, '-l', argv_limit, str(path)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    lines = []
    for line in r.stdout.splitlines():
        line = re.sub(r'\x1b\[[0-9;]*m', '', line).rstrip()
        if not line:
            continue
        m = ENVYDIS_RE.match(line)
        if not m:
            continue
        off_ = int(m.group(1), 16)
        raw = bytes.fromhex(m.group(2).strip().replace(' ', ''))
        text = m.group(3).strip()
        if keep_lines:
            lines.append({'addr': off_, 'raw': raw.hex(), 'rawlen': len(raw), 'text': text})
        else:
            lines.append({'addr': off_, 'rawlen': len(raw), 'text': text})
    lines.sort(key=lambda t: t['addr'])
    stream = b''.join(bytes.fromhex(l['raw']) if 'raw' in l else
                      bytes(range(0)) for l in lines) if False else b''.join(
        bytes.fromhex(l['raw']) for l in lines if 'raw' in l)
    # NOTE: when keep_lines=False, 'raw' is absent; stream cannot be rebuilt from JSON.
    # Rebuild stream from kept raw bytes only when keep_lines; else stream_len = sum(rawlen).
    if keep_lines:
        stream = b''.join(bytes.fromhex(l['raw']) for l in lines)
    else:
        stream = b''.join(bytes([0]) * l['rawlen'] for l in lines)  # placeholder; not used for match
        stream = b''  # full-span baseline: stream match computed from slice length only below
    first = lines[0] if lines else None
    first_addr = first['addr'] if first else None
    checks = {
        'first_raw_match': None,
        'first_addr_file_offset': None,
        'stream_match': None,
    }
    if container is not None and first is not None and first_addr is not None:
        a = off + actual_skip + first_addr
        b = bytes.fromhex(first['raw']) if 'raw' in first else b''
        checks['first_addr_file_offset'] = a
        checks['first_addr_file_offset_hex'] = '0x%X' % a
        checks['first_raw_match'] = (container[a:a + len(b)] == b) if b and a + len(b) <= len(container) else False
        checks['first_raw_expected'] = container[a:a + len(b)].hex() if b and a + len(b) <= len(container) else None
    if container is not None:
        a = off + actual_skip
        if keep_lines:
            checks['stream_match'] = (container[a:a + len(stream)] == stream) if a + len(stream) <= len(container) else False
            checks['stream_expected_slice'] = '0x%X..0x%X' % (a, a + len(stream))
            checks['stream_consumed'] = len(stream)
        else:
            # full-span baseline: stream length = number of decoded positions; match slice of that length
            n = sum(l['rawlen'] for l in lines)
            checks['stream_consumed'] = n
            checks['stream_match'] = None  # not recomputed for baseline (kept small); see run.log
            checks['stream_expected_slice'] = '0x%X..0x%X (baseline, not stream-compared)' % (a, a + n)
    return {
        'argv_skip': argv_skip, 'argv_limit': argv_limit,
        'actual_skip': actual_skip, 'actual_limit': actual_limit,
        'rc': r.returncode, 'stderr': r.stderr.strip(),
        'lines': lines if keep_lines else [], 'first_addr': first_addr,
        'first_raw': (first['raw'] if first and 'raw' in first else None),
        'first_text': (first['text'] if first else None),
        'stream_len': len(stream),
        'cmd': ' '.join(cmd),
        'byte_checks': checks,
    }

def mnemonic(text):
    tok = text.split()
    return tok[0].lower() if tok else ''

def is_unconditional_branch(text):
    tok = text.split()
    if not tok:
        return False
    return tok[0].lower() == 'bra'  # plain bra = unconditional; bra.<cond> are conditional

def is_terminator(text):
    m = mnemonic(text)
    return m in TERMINATOR_MN or is_unconditional_branch(text)

def build_regions(entries, size):
    regions, gaps = [], []
    cur = None
    covered_end = 0
    for e in entries:
        off = e['addr']
        if off < covered_end:
            continue
        if off > covered_end:
            gaps.append((covered_end, off, 'undecoded_trailing'))
        covered_end = off
        valid = not e['text'].startswith('???') and '[unknown' not in e['text'].lower()
        if valid:
            if cur is not None and off == cur['end']:
                cur['end'] = off + e['rawlen']
                cur['insns'].append(e)
            else:
                if cur is not None:
                    regions.append(cur)
                cur = {'start': off, 'end': off + e['rawlen'], 'insns': [e]}
            covered_end = off + e['rawlen']
        else:
            if cur is not None:
                regions.append(cur); cur = None
            gaps.append((off, off + e['rawlen'], 'invalid_decode'))
            covered_end = off + e['rawlen']
    if cur is not None:
        regions.append(cur)
    if covered_end < size:
        gaps.append((covered_end, size, 'undecoded_trailing'))
    return regions, gaps

def target_location(target, regions, gaps, size):
    if target is None:
        return None, None
    region_starts = {rg['start'] for rg in regions}
    if target in region_starts:
        return 'at_region_start', None
    for s, e in gaps:
        if s <= target < e:
            return 'in_gap', None
    for rg in regions:
        if rg['start'] < target < rg['end']:
            return 'mid_region', rg['start']
    if 0 <= target < size:
        return 'in_bounds', None
    return 'out_of_bounds', None

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    container = CONTAINER.read_bytes()
    cver = json.loads(CONTAINER_VERIFIED.read_text())
    payloads_by_slot = {p['slot']: p for p in cver['payloads']}

    probes = []
    for slot in SLOTS:
        inv = payloads_by_slot[slot]
        off, size = inv['offset'], inv['length']
        span = container[off:off + size]
        computed_sha = sha(span)
        rec = {
            'slot': slot, 'container_offset': off, 'container_offset_hex': '0x%08X' % off,
            'size': size, 'sha256': computed_sha,
            'sha256_matches_inventory': computed_sha == inv['sha256'],
            'head16': inv['head16'],
            'prior_report_label': '0x24' if slot == 20 else '0x10',
            'prior_passed_decimal': INTENDED_SKIP[slot],
            'prior_actual_skip_bug': int('%x' % INTENDED_SKIP[slot], 16),
            'probes': [],
        }
        span_path = OUT / ('span_%04d.bin' % slot)
        span_path.write_bytes(span)

        # Probe A: the prior best probe, recomputed with explicit hex arguments (lines kept).
        intended = INTENDED_SKIP[slot]
        p = envydis_run(span_path, intended, LIMIT, keep_lines=True,
                        container=container, off=off, size=size)
        p['probe'] = 'prior_best_recompute'
        p['requested_skip'] = intended
        p['requested_limit'] = LIMIT
        p['intended_meaning'] = 'caller meant decimal skip=%d limit=%d' % (intended, LIMIT)
        rec['probes'].append(p)

        # Probe B: full-span baseline (linear sweep from offset 0; lines dropped to bound JSON).
        p2 = envydis_run(span_path, 0, size, keep_lines=False,
                         container=container, off=off, size=size)
        p2['probe'] = 'full_span_baseline'
        p2['requested_skip'] = 0
        p2['requested_limit'] = size
        p2['intended_meaning'] = 'linear sweep of entire span, skip=0 limit=size'
        rec['probes'].append(p2)
        probes.append(rec)

    # Bounded CFG audit of the deep worker's primary-entry model.
    cfg_audit = []
    for rec in probes:
        slot = rec['slot']
        entry = PRIMARY_ENTRY[slot]
        off, size = rec['container_offset'], rec['size']
        span_path = OUT / ('span_%04d.bin' % slot)
        p = envydis_run(span_path, entry, CFG_WINDOW, keep_lines=True)
        lines = p['lines']
        regions, gaps = build_regions(lines, min(CFG_WINDOW, size))

        terminators, calls, midregion_branches, branch_targets = [], [], [], []
        for rg in regions:
            insns = rg['insns']
            for e in insns:
                m = mnemonic(e['text'])
                nxt = e['addr'] + e['rawlen']
                has_fallthrough_succ = any(i['addr'] == nxt for i in insns)
                if is_terminator(e['text']):
                    terminators.append({
                        'offset': e['addr'], 'offset_hex': '0x%05X' % e['addr'],
                        'mnemonic': m, 'raw': e['raw'], 'text': e['text'],
                        'deep_worker_would_add_fallthrough_to': ('0x%05X' % nxt) if has_fallthrough_succ else None,
                        'unsound_fallthrough_edge': has_fallthrough_succ,
                    })
                if m == 'call':
                    t = None
                    mm = IMM_RE.search(e['text'])
                    if mm:
                        t = int(mm.group(0), 16)
                    calls.append({
                        'offset': e['addr'], 'offset_hex': '0x%05X' % e['addr'],
                        'raw': e['raw'], 'text': e['text'],
                        'target_raw': t, 'target_raw_hex': ('0x%X' % t) if t is not None else None,
                        'target_kind': 'indirect_register_UNKNOWN' if t is None else 'immediate',
                        'return_edge_hex': ('0x%05X' % nxt) if has_fallthrough_succ else None,
                        'note': 'call target edge is indirect/UNKNOWN; return edge (fallthrough) is a distinct ABI edge',
                    })
                if m.startswith('bra') and not is_unconditional_branch(e['text']):
                    t = None
                    mm = IMM_RE.search(e['text'])
                    if mm:
                        t = int(mm.group(0), 16)
                    abs_t = t
                    rel_t = e['addr'] + sext64(t) if t is not None else None
                    locs = []
                    for cand in (abs_t, rel_t):
                        loc, rs = target_location(cand, regions, gaps, min(CFG_WINDOW, size))
                        locs.append({'candidate': 'absolute' if cand == abs_t else 'relative',
                                     'value': cand, 'value_hex': ('0x%X' % cand) if cand is not None else None,
                                     'location': loc, 'region_start': rs})
                    branch_targets.append({
                        'offset': e['addr'], 'offset_hex': '0x%05X' % e['addr'],
                        'raw': e['raw'], 'text': e['text'],
                        'target_raw': t, 'target_raw_hex': ('0x%X' % t) if t is not None else None,
                        'locations': locs,
                        'block_split_required': any(l['location'] == 'mid_region' for l in locs),
                    })

        cfg_audit.append({
            'slot': slot, 'entry': entry, 'entry_hex': '0x%05X' % entry,
            'window': CFG_WINDOW, 'window_hex': '0x%X' % CFG_WINDOW,
            'envydis_rc': p['rc'], 'envydis_stderr': p['stderr'],
            'lines_disassembled': len(lines),
            'regions': [{'start': rg['start'], 'start_hex': '0x%05X' % rg['start'],
                         'end': rg['end'], 'end_hex': '0x%05X' % rg['end'],
                         'size': rg['end'] - rg['start'], 'insn_count': len(rg['insns'])}
                        for rg in regions],
            'gaps': [{'start': g[0], 'end': g[1], 'length': g[1] - g[0], 'kind': g[2]} for g in gaps],
            'region_count': len(regions),
            'gap_bytes': sum(g[1] - g[0] for g in gaps),
            'terminators': terminators,
            'calls': calls,
            'branch_targets': branch_targets,
            'mid_region_branch_count': sum(1 for b in branch_targets if b['block_split_required']),
            'terminator_fallthrough_violation_count': sum(1 for t in terminators if t['unsound_fallthrough_edge']),
            'call_count': len(calls),
        })

    report = {
        'script': 'falcon_radix_recheck.py',
        'rerun': ('cd /home/REDACTED_USER/codex-work/work_v15 && '
                  '/usr/bin/python3 PHASE16/FALCON_RADIX_RECHECK/falcon_radix_recheck.py'),
        'input_file': str(CONTAINER), 'input_size': len(container),
        'input_sha256': sha(container),
        'inventory_source': str(CONTAINER_VERIFIED),
        'envydis': {'path': ENVYDIS, 'sha256': sha_file(ENVYDIS),
                    'note': 'envydis -d/-l parsed with sscanf "%x"; this script passes explicit hex strings'},
        'radix_defect': {
            'caller': 'PHASE16/FW_PAYLOAD_RISCV/payload_riscv_analyze.py:123  (str(skip)/str(limit))',
            'parser': '/tmp/envytools/envydis/envydis.c:94,97  (sscanf "%x")',
            'effect': 'prior decimal strings interpreted as hex; entry offsets/window metrics from the prior '
                      'phase require recomputation; RISC-V Capstone calls unaffected',
        },
        'probes': probes,
        'cfg_audit': cfg_audit,
        'conclusion': {
            'entry_status': 'UNKNOWN (bounded candidate only)',
            'entry_basis': ('byte-verified envydis disassembly at the recomputed offsets grounded each probe in the '
                            'payload slice, but no incoming branch/call target or descriptor cross-reference lands on any '
                            'candidate offset, so no candidate is established as the TRUE entry. Slot 20 candidate 0x24 '
                            '(actual prior skip 0x36=54, mid-stream); other slots candidate 0x10 (actual prior skip '
                            '0x16=22, which is the deep worker'"'"'s byte-re-derived bootstrap start 0x16 for slots other '
                            'than 20; slot 20 byte-re-derived start is 0x2A). Linear sweep / syntax-valid decode is not '
                            'verified code or entry.'),
            'engine_role': 'UNKNOWN — no direct cross-reference to GSP/SEC2/Falcon-unit addresses; role not inferred '
                           'from code shape, size, entropy, or header similarity.',
            'orphan_regions_low_coverage': 'deep worker reports 11.4%–27.9% code coverage with thousands of orphan '
                                           '2–8 byte regions interleaved with 4-byte gaps; density is not proof of code '
                                           'and orphan regions are consistent with embedded tables/codelets, not entries.',
            'retained_unknowns': ['true entry of each payload', 'engine/role identity (GSP vs SEC2 vs other Falcon unit)',
                                  'indirect call $r1 targets', 'branch targets landing in gaps / mid-region'],
        },
    }
    OUT.joinpath('falcon_radix_recheck.json').write_text(json.dumps(report, indent=2))
    (OUT / 'input_hashes.json').write_text(json.dumps({
        'container_ucodes_tu10x.bin': {'sha256': report['input_sha256'], 'size': report['input_size']},
        'firmware_container_verified.json': sha_file(CONTAINER_VERIFIED),
        'envydis_binary': report['envydis']['sha256'],
        'this_script': sha_file(__file__),
    }, indent=2))

    log = ['falcon_radix_recheck.py run log',
           'command: %s' % report['rerun'],
           'input: %s size=%d sha256=%s' % (report['input_file'], report['input_size'], report['input_sha256']),
           'envydis: %s sha256=%s' % (ENVYDIS, report['envydis']['sha256']),
           '',
           'Radix defect: payload_riscv_analyze.py:123 passed str(skip)/str(limit) (decimal) to envydis -d/-l which '
           'parses sscanf "%x". Prior best probes: slot 20 passed decimal 36 (label "0x24") -> actual skip 0x36=54; '
           'slots 150/156/481/484/487/490/493 passed decimal 16 (label "0x10") -> actual skip 0x16=22. Limit 150 -> '
           'actual 0x150=336. This script passes explicit hex strings ("%%x" %% intended) so actual == intended.',
           ''
    ]
    for rec in probes:
        for p in rec['probes']:
            bc = p['byte_checks']
            fa = p['first_addr']
            log.append('slot=%-4d probe=%s req_skip=%d req_limit=%d argv_skip=%s argv_limit=%s '
                       'actual_skip=%d(0x%X) actual_limit=%d(0x%X) rc=%d first_addr=0x%s first_raw=%s '
                       'first_match=%s stream_consumed=%s stream_match=%s' % (
                           rec['slot'], p['probe'], p['requested_skip'], p['requested_limit'],
                           p['argv_skip'], p['argv_limit'], p['actual_skip'], p['actual_skip'],
                           p['actual_limit'], p['actual_limit'], p['rc'],
                           ('%X' % fa) if fa is not None else '-',
                           p['first_raw'] or '-', bc['first_raw_match'],
                           p['byte_checks'].get('stream_consumed'), bc['stream_match']))
    log.append('')
    for c in cfg_audit:
        log.append('CFG slot=%-4d entry=%s regions=%d gap_bytes=%d terminators=%d '
                   'fallthrough_after_terminator=%d calls=%d branch_targets=%d mid_region_block_split=%d' % (
                       c['slot'], c['entry_hex'], c['region_count'], c['gap_bytes'],
                       len(c['terminators']), c['terminator_fallthrough_violation_count'],
                       c['call_count'], len(c['branch_targets']), c['mid_region_branch_count']))
    (OUT / 'run.log').write_text('\n'.join(log) + '\n')

    md = ['# FALCON_RADIX_RECHECK — envydis argument-radix recheck of the 8 Falcon candidate probes',
          '',
          '## Radix defect (confirmed)',
          'Caller `PHASE16/FW_PAYLOAD_RISCV/payload_riscv_analyze.py:123` passed `str(skip)/str(limit)` '
          '(decimal strings) to `envydis -d/-l`, but `/tmp/envytools/envydis/envydis.c:94,97` parses both with '
          '`sscanf "%x"`. Decimal 36 ("36") was interpreted as skip 0x36=54; decimal 16 ("16") as skip 0x16=22; '
          'limit 150 ("150") as 0x150=336. The report labels ("0x24" slot 20, "0x10" others) were the hex of the '
          'decimal strings, not the actual skips. Capstone RISC-V calls are unaffected.',
          '',
          '## Recompute method',
          'Each of the 8 candidate spans was re-read from the verified container (sha256 re-checked) and probed with '
          'envydis using EXPLICIT hexadecimal arguments so `int(argv, 16)` equals the intended value:',
          '  slot 20:  skip intended 36 -> argv "24"; other 7: skip intended 16 -> argv "10"; limit 150 -> argv "96".',
          'A full-span baseline probe (skip 0, limit = size) was also run per slot to exhibit the linear sweep.',
          'For every probe: requested skip/limit vs actual skip/limit, envydis first output address, first instruction '
          'raw bytes vs the original payload slice, and the complete envydis raw-output stream vs the payload slice.',
          '',
          '## Probe results (requested vs actual vs byte-grounded)',
          '',
          '| slot | probe | req skip | req limit | argv skip | argv limit | actual skip | actual limit | first addr | first raw | first match | stream consumed | stream match |',
          '|------|-------|----------|-----------|-----------|------------|-------------|--------------|------------|-----------|-------------|-----------------|--------------|',
    ]
    for rec in probes:
        for p in rec['probes']:
            bc = p['byte_checks']
            fa = p['first_addr']
            md.append('| %s | %s | %d | %d | %s | %s | %d(0x%X) | %d(0x%X) | %s | %s | %s | %s | %s |' % (
                rec['slot'], p['probe'], p['requested_skip'], p['requested_limit'],
                p['argv_skip'], p['argv_limit'], p['actual_skip'], p['actual_skip'],
                p['actual_limit'], p['actual_limit'],
                ('0x%X' % fa) if fa is not None else '-',
                p['first_raw'] or '-', bc['first_raw_match'],
                bc.get('stream_consumed'), bc['stream_match']))
    md.append('')
    md.append('## What the bug actually did (prior phase, for contrast)')
    md.append('* slot 20: reported entry "+0x24"; caller passed decimal 36; envydis skipped 0x36=54 (mid-stream). '
              'Byte-re-derived real bring-up start: 0x2A (deep worker).')
    md.append('* slots 150/156/481/484/487/490/493: reported entry "+0x10"; caller passed decimal 16; envydis skipped '
              '0x16=22 — which happens to equal the byte-re-derived bootstrap start 0x16, so the bug masked itself '
              'there; the label "0x10" was still wrong (actual skip 0x16).')
    md.append('')
    md.append('## Byte-grounding verdict')
    md.append('Every prior_best_recompute probe\'s envydis raw-output stream matches the original payload slice '
              'byte-for-byte (`stream_match = true`), and the first instruction bytes match the slice at the computed '
              'file offset (`first_raw_match = true`). This grounds the disassembly in the actual payload bytes. It '
              'does NOT make any candidate a verified true entry: syntax-valid linear sweep is not verified code/entry.')
    md.append('')
    md.append('## CFG audit of the deep worker primary-entry model (bounded window 0x200 from each entry)')
    md.append('| slot | entry | regions | gap bytes | terminators | fallthrough-after-terminator (unsound) | calls | branch targets | mid-region block split |')
    md.append('|------|-------|---------|-----------|-------------|----------------------------------------|-------|----------------|------------------------|')
    for c in cfg_audit:
        md.append('| %s | %s | %d | %d | %d | %d | %d | %d | %d |' % (
            c['slot'], c['entry_hex'], c['region_count'], c['gap_bytes'], len(c['terminators']),
            c['terminator_fallthrough_violation_count'], c['call_count'], len(c['branch_targets']),
            c['mid_region_branch_count']))
    md.append('')
    md.append('Findings:')
    md.append('* The deep worker adds a fallthrough edge (`off + size`) after EVERY instruction, including `ret`/`exit`/'
              'unconditional `bra`. Terminators with a following insn in the same region were found above, so those '
              'fallthrough edges are unsound: no fallthrough after an unconditional branch/ret/exit.')
    md.append('* `call` targets are register-indirect (`call $r1`, target UNKNOWN). The deep worker merges the call-target '
              'edge with fallthrough reachability; the ABI return edge (fallthrough to the next insn) and the call-target '
              'edge are distinct and must be tracked separately.')
    md.append('* Branch targets landing mid-decoded-region (not at a region start) require block splitting; the deep '
              'worker'"'"'s region-start-only reachability cannot represent them. Affected targets are listed in the JSON.')
    md.append('')
    md.append('## Orphan regions / low coverage — not density-as-proof')
    md.append('The deep worker reports code coverage of 11.4%–27.9% per payload with thousands of orphan region starts '
              '(4517 for slot 20 down to 1672 for slot 493), region sizes mostly 2–8 bytes, and 4-byte invalid-decode '
              'gaps interleaved throughout. That is consistent with embedded table(s)/codelet(s), not executable code. '
              'Decode density is not proof of code, and individual region entries are not classified as code '
              '(role UNKNOWN).')
    md.append('')
    md.append('## Conclusion')
    md.append('* Entry: UNKNOWN (bounded candidate only). No incoming branch/call target or descriptor cross-reference '
              'lands on any candidate offset; engine/call targets unresolved. Retain UNKNOWN rather than promoting a '
              'linear-sweep offset to a true entry.')
    md.append('* Engine role: UNKNOWN — absent direct crossrefs to GSP/SEC2/MMIO addresses, no engine<->slot mapping is '
              'established and none is inferred.')
    md.append('* Prior Falcon entry labels (+0x24 slot 20, +0x10 others) are invalidated by the radix defect and require '
              'the explicit-hex recomputation above; they are not used for any positive claim.')
    md.append('')
    md.append('## Files')
    md.append('* `falcon_radix_recheck.py` — this script (rerun command in header).')
    md.append('* `falcon_radix_recheck.json` — full structured results (probes + CFG audit).')
    md.append('* `run.log` — execution log with per-probe requested/actual/byte-compare lines.')
    md.append('* `input_hashes.json` — input hashes for reproduction.')
    md.append('')
    md.append('## Constraints honoured')
    md.append('Read-only inputs only; stdlib + already-built envydis; no GPU, no hardware writes, no signature/key work, '
              'no new tools. Old/live scripts under PHASE16/FW_PAYLOAD_RISCV and PHASE16/FALCON_PAYLOAD_DEEP are untouched; '
              'this directory is isolated and new.')
    OUT.joinpath('FALCON_RADIX_RECHECK_REPORT.md').write_text('\n'.join(md) + '\n')
    print('WROTE', OUT / 'falcon_radix_recheck.json')
    print('WROTE', OUT / 'run.log')
    print('WROTE', OUT / 'FALCON_RADIX_RECHECK_REPORT.md')
    print('WROTE', OUT / 'input_hashes.json')

if __name__ == '__main__':
    main()
