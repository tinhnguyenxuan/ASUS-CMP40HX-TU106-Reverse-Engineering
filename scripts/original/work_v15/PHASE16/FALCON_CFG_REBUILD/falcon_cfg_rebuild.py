#!/usr/bin/env python3
# falcon_cfg_rebuild.py
# Repaired + extended Falcon payload control-flow analysis for the 8 candidate
# slots 20, 150, 156, 481, 484, 487, 490, 493 from the saved NVUCODES container.
#
# Fresh isolated job: writes only under PHASE16/FALCON_CFG_REBUILD/. Never touches
# old/live scripts under PHASE16/FW_PAYLOAD_RISCV or PHASE16/FALCON_PAYLOAD_DEEP.
#
# Method (read-only inputs only; stdlib + already-built envydis only; no GPU, no
# hardware/firmware loading or flashing, no keys/signatures, no bypass, no brute
# force, no exploit work):
#   1. Read each span from outputs/ucodes_tu10x.bin at the VERIFIED container
#      offset/length (firmware_container_verified.json) and re-check sha256.
#   2. Disassemble the FULL span with envydis (-m falcon) using EXPLICIT HEXADECIMAL
#      -d/-l argument strings (envydis parses both with sscanf "%x"; the prior phase
#      passed decimal strings, corrupting skip/limit).
#   3. Verify every decoded instruction's raw bytes against the original payload
#      slice before any CFG use; record exact invalid/undecodable spans.
#   4. Classify instruction semantics (Falcon ISA per envytools docs):
#        ret/exit -> terminator, no fallthrough.
#        bra <cond> imm / bra $pN imm -> conditional branch: target edge + fallthrough.
#        bra imm (no cond)          -> unconditional branch: target edge, no fallthrough.
#        bra $rN                    -> register-indirect jump: target UNKNOWN, no fallthrough.
#        call imm                   -> direct call: target edge + return-continuation edge.
#        call $rN                   -> register-indirect call: call-target UNKNOWN +
#                                      return-continuation edge (ABI), tracked SEPARATELY;
#                                      target is never inferred from $r1.
#   5. Build basic blocks: leaders = candidate entry + every proven direct branch/call
#      target landing on a valid decoded instruction start; blocks are split when a
#      proven target lands inside a previously decoded region (not only at region starts).
#   6. Finite worklist reachability from the bounded candidate entry; every unresolved
#      edge carries a reason. Linear-sweep-only (unreachable) regions are NOT counted
#      as reachable code.
#   7. Entry: UNKNOWN unless proven by external crossref/metadata (none established ->
#      kept UNKNOWN). No engine/role inference from slot number or density.
#
# Candidate entries (byte-re-derived by the deep worker, NOT proven true entries;
# used only as bounded CFG traversal anchors):
#   slot 20 -> 0x2A; slots 150/156/481/484/487/490/493 -> 0x16.
#
# Run: cd /home/REDACTED_USER/codex-work/work_v15 && /usr/bin/python3 PHASE16/FALCON_CFG_REBUILD/falcon_cfg_rebuild.py

import struct, hashlib, json, re, subprocess, sys
from pathlib import Path

ROOT = Path('/home/REDACTED_USER/codex-work/work_v15')
PH = ROOT / 'PHASE16'
OUT = PH / 'FALCON_CFG_REBUILD'
CONTAINER = ROOT / 'outputs/ucodes_tu10x.bin'
CONTAINER_VERIFIED = PH / 'firmware_container_verified.json'
ENVYDIS = '/tmp/envytools/build/envydis/envydis'
SLOTS = [20, 150, 156, 481, 484, 487, 490, 493]
CANDIDATE_ENTRY = {20: 0x2A, 150: 0x16, 156: 0x16, 481: 0x16, 484: 0x16,
                   487: 0x16, 490: 0x16, 493: 0x16}

ENVYDIS_RE = re.compile(r'^([0-9a-fA-F]+):\s+((?:[0-9a-fA-F]{2}\s+)+?)\s{2,}(.*)$')
IMM_RE = re.compile(r'0x[0-9a-fA-F]+')

RET_EXIT = ('ret', 'exit')


def sha(b):
    return hashlib.sha256(b).hexdigest()


def sha_file(p):
    p = Path(p)
    return sha(p.read_bytes()) if p.exists() else None


def sext16(v):
    return v - 0x10000 if v >= 0x8000 else v


def envydis_run(path, skip, limit):
    """Run envydis with EXPLICIT hexadecimal -d/-l argument strings (parser uses %x)."""
    argv_skip = '%x' % skip
    argv_limit = '%x' % limit
    cmd = [ENVYDIS, '-i', '-n', '-m', 'falcon', '-b', '0',
           '-d', argv_skip, '-l', argv_limit, str(path)]
    r = subprocess.run(cmd, capture_output=True, text=True)
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
        lines.append({'addr': off, 'raw': raw, 'rawlen': len(raw), 'text': text})
    lines.sort(key=lambda t: t['addr'])
    return lines, r.returncode, r.stderr.strip(), {'argv_skip': argv_skip,
                                                    'argv_limit': argv_limit,
                                                    'cmd': ' '.join(cmd)}


def mnemonic(text):
    tok = text.split()
    return tok[0].lower() if tok else ''


def is_valid(text):
    """Fully decoded instruction: not an envydis '???' line and no '[unknown' marker."""
    return not text.startswith('???') and '[unknown' not in text.lower()


def classify_insn(addr, size, raw, text):
    """Return semantics dict for a valid instruction.

    edges: list of {kind, target, target_hex, status, reason}
      kind: 'branch_target' | 'call_target' | 'call_return' | 'fallthrough'
      status: 'resolved' | 'UNKNOWN' | 'unresolved'
    fallthrough_target: address of the sequential successor (or None if undecodable/OOB)
    """
    tok = text.split()
    m = tok[0]
    sem = {'kind': 'other', 'edges': [], 'fallthrough_target': None,
           'fallthrough_status': None, 'fallthrough_reason': None}
    imm_candidates = []
    for mm in IMM_RE.finditer(text):
        imm_candidates.append(int(mm.group(0), 16))
    imm = imm_candidates[0] if imm_candidates else None

    if m == 'bra':
        if len(tok) >= 2 and tok[1].startswith('$'):
            reg = tok[1]
            if reg.startswith('$p'):
                # bra $pN <imm>: conditional predicate branch -> target + fallthrough
                sem['kind'] = 'cond_branch'
                sem['edges'] = branch_edges(addr, size, imm, text)
                ft = addr + size
                sem['fallthrough_target'] = ft if (0 <= ft < size and ft in _VALID_STARTS) else None
                sem['fallthrough_status'] = 'resolved' if sem['fallthrough_target'] is not None else 'undecodable'
                sem['fallthrough_reason'] = None if sem['fallthrough_target'] is not None \
                    else 'fallthrough lands in undecodable/out-of-bounds bytes'
            elif reg.startswith('$r'):
                # bra $rN: register-indirect unconditional jump -> target UNKNOWN, no fallthrough
                sem['kind'] = 'indirect_branch'
                sem['edges'] = [{'kind': 'branch_target', 'target': None, 'target_hex': None,
                                 'status': 'UNKNOWN',
                                 'reason': 'indirect branch via %s; target not statically resolvable, not inferred' % reg}]
        elif len(tok) == 3 and tok[2].startswith('0x'):
            # bra <cond> <imm>: conditional branch -> target + fallthrough
            sem['kind'] = 'cond_branch'
            sem['edges'] = branch_edges(addr, size, imm, text)
            ft = addr + size
            sem['fallthrough_target'] = ft if (0 <= ft < size and ft in _VALID_STARTS) else None
            sem['fallthrough_status'] = 'resolved' if sem['fallthrough_target'] is not None else 'undecodable'
            sem['fallthrough_reason'] = None if sem['fallthrough_target'] is not None \
                else 'fallthrough lands in undecodable/out-of-bounds bytes'
        elif len(tok) == 2 and tok[1].startswith('0x'):
            # bra imm (no condition): unconditional relative branch -> target, no fallthrough
            sem['kind'] = 'uncond_branch'
            sem['edges'] = branch_edges(addr, size, imm, text)
        else:
            sem['kind'] = 'bra_unrecognized'
            sem['edges'] = [{'kind': 'branch_target', 'target': None, 'target_hex': None,
                             'status': 'unresolved',
                             'reason': 'unrecognized bra form: %s' % text}]
    elif m == 'call':
        if len(tok) >= 2 and tok[1].startswith('$'):
            # call $rN: register-indirect call -> call target UNKNOWN; return continuation is a
            # SEPARATE edge (fallthrough to next insn). Target never inferred from the register.
            sem['kind'] = 'indirect_call'
            sem['edges'] = [{'kind': 'call_target', 'target': None, 'target_hex': None,
                             'status': 'UNKNOWN',
                             'reason': 'register-indirect call via %s; target not statically resolvable, not inferred from $r1' % tok[1]}]
            ft = addr + size
            sem['fallthrough_target'] = ft if (0 <= ft < size and ft in _VALID_STARTS) else None
            sem['fallthrough_status'] = 'resolved' if sem['fallthrough_target'] is not None else 'undecodable'
            sem['fallthrough_reason'] = None if sem['fallthrough_target'] is not None \
                else 'return continuation lands in undecodable/out-of-bounds bytes'
            sem['edges'].append({'kind': 'call_return', 'target': sem['fallthrough_target'],
                                 'target_hex': ('0x%X' % sem['fallthrough_target']) if sem['fallthrough_target'] is not None else None,
                                 'status': sem['fallthrough_status'],
                                 'reason': sem['fallthrough_reason']})
        elif imm is not None:
            # call imm: direct absolute call -> target edge + return continuation
            sem['kind'] = 'direct_call'
            sem['edges'] = branch_edges(addr, size, imm, text, call=True)
            ft = addr + size
            sem['fallthrough_target'] = ft if (0 <= ft < size and ft in _VALID_STARTS) else None
            sem['fallthrough_status'] = 'resolved' if sem['fallthrough_target'] is not None else 'undecodable'
            sem['fallthrough_reason'] = None if sem['fallthrough_target'] is not None \
                else 'return continuation lands in undecodable/out-of-bounds bytes'
            sem['edges'].append({'kind': 'call_return', 'target': sem['fallthrough_target'],
                                 'target_hex': ('0x%X' % sem['fallthrough_target']) if sem['fallthrough_target'] is not None else None,
                                 'status': sem['fallthrough_status'],
                                 'reason': sem['fallthrough_reason']})
        else:
            sem['kind'] = 'call_unrecognized'
            sem['edges'] = [{'kind': 'call_target', 'target': None, 'target_hex': None,
                             'status': 'unresolved', 'reason': 'unrecognized call form: %s' % text}]
    elif m in RET_EXIT:
        sem['kind'] = m  # terminator: no fallthrough, no outgoing edges
    return sem


_VALID_STARTS = set()  # populated per slot: valid decoded instruction start addresses


def branch_edges(addr, size, imm, text, call=False):
    """Resolve an immediate control-flow target byte-groundedly.

    Absolute (imm) and PC-relative (addr + sext16(imm)) interpretations are both
    kept; a target is 'resolved' only if one lands on a valid decoded instruction
    start inside the span. Otherwise unresolved with a reason.
    """
    cands = []
    if imm is not None:
        cands.append(('absolute', imm))
        cands.append(('relative', addr + sext16(imm)))
    resolved = [c for _, c in cands if 0 <= c < size and c in _VALID_STARTS]
    edges = []
    if call:
        if resolved:
            edges.append({'kind': 'call_target', 'target': resolved[0],
                          'target_hex': '0x%X' % resolved[0], 'status': 'resolved',
                          'reason': None,
                          'ambiguous': len(resolved) > 1,
                          'candidates': [{'kind': k, 'value': c, 'value_hex': '0x%X' % c,
                                          'resolved': c in resolved} for k, c in cands]})
        else:
            edges.append({'kind': 'call_target', 'target': None, 'target_hex': None,
                          'status': 'unresolved',
                          'reason': 'direct call target %s not a valid decoded instruction start' %
                                    (['0x%X' % c for _, c in cands]),
                          'candidates': [{'kind': k, 'value': c, 'value_hex': '0x%X' % c,
                                          'resolved': False} for k, c in cands]})
    else:
        if resolved:
            edges.append({'kind': 'branch_target', 'target': resolved[0],
                          'target_hex': '0x%X' % resolved[0], 'status': 'resolved',
                          'reason': None,
                          'ambiguous': len(resolved) > 1,
                          'candidates': [{'kind': k, 'value': c, 'value_hex': '0x%X' % c,
                                          'resolved': c in resolved} for k, c in cands]})
        else:
            oob = [c for _, c in cands if not (0 <= c < size)]
            edges.append({'kind': 'branch_target', 'target': None, 'target_hex': None,
                          'status': 'unresolved',
                          'reason': ('branch target(s) %s out of payload span' %
                                     (['0x%X' % c for c in oob]) if oob else
                                     'branch target(s) %s not a valid decoded instruction start' %
                                     (['0x%X' % c for _, c in cands])),
                          'candidates': [{'kind': k, 'value': c, 'value_hex': '0x%X' % c,
                                          'resolved': c in resolved} for k, c in cands]})
    return edges


def build_regions(lines, size):
    """Split [0,size) into valid-instruction regions and invalid/undecodable spans.

    envydis linearly sweeps and consumes every byte exactly once (valid insn or
    ???/[unknown line), so invalid lines merge into exact invalid spans.
    Single-pass: invalid bytes are accumulated incrementally (no O(n^2) rescan).
    Returns (regions, invalid_spans, insns_by_addr).
    regions: [{start, end, insns:[{addr,size,raw,text,sem}]}]
    invalid_spans: [{start, end, length, bytes_hex}]
    """
    regions = []
    invalid_spans = []
    insns_by_addr = {}
    cur = None
    pending_start = None
    pending_bytes = bytearray()
    for ln in lines:
        a, raw, text = ln['addr'], ln['raw'], ln['text']
        if not is_valid(text):
            if pending_start is None:
                pending_start = a
            pending_bytes += raw
            continue
        # close any pending invalid span
        if pending_start is not None:
            invalid_spans.append({'start': pending_start, 'end': a,
                                  'length': a - pending_start,
                                  'bytes_hex': bytes(pending_bytes).hex()})
            pending_start = None
            pending_bytes = bytearray()
        sem = classify_insn(a, len(raw), raw, text)
        rec = {'addr': a, 'size': len(raw), 'raw': raw.hex(), 'text': text,
               'sem': sem}
        insns_by_addr[a] = rec
        if cur is not None and a == cur['end']:
            cur['end'] = a + len(raw)
            cur['insns'].append(rec)
        else:
            if cur is not None:
                regions.append(cur)
            cur = {'start': a, 'end': a + len(raw), 'insns': [rec]}
    if cur is not None:
        regions.append(cur)
    if pending_start is not None:
        # trailing invalid span to end of sweep
        invalid_spans.append({'start': pending_start, 'end': size,
                              'length': size - pending_start,
                              'bytes_hex': bytes(pending_bytes).hex()})
    return regions, invalid_spans, insns_by_addr


def block_insn_summary(i):
    return {'addr': i['addr'], 'addr_hex': '0x%06X' % i['addr'],
            'size': i['size'], 'raw': i['raw'], 'text': i['text'],
            'sem_kind': i['sem']['kind'],
            'sem_edges': i['sem']['edges']}


def term_edges_for(last):
    """Outgoing CFG edges of a block's last instruction, with reasons for unresolved ones."""
    sem = last['sem']
    if sem['kind'] in RET_EXIT:
        return []  # terminator: no fallthrough, no outgoing edges
    if sem['kind'] == 'uncond_branch':
        return list(sem['edges'])  # target edge only, no fallthrough
    if sem['kind'] == 'cond_branch':
        edges = list(sem['edges'])  # target edge (resolved or unresolved)
        ft = sem['fallthrough_target']
        if ft is not None:
            edges.append({'kind': 'fallthrough', 'target': ft,
                          'target_hex': '0x%X' % ft, 'status': 'resolved', 'reason': None})
        else:
            edges.append({'kind': 'fallthrough', 'target': None, 'target_hex': None,
                          'status': sem['fallthrough_status'], 'reason': sem['fallthrough_reason']})
        return edges
    if sem['kind'] in ('direct_call', 'indirect_call'):
        return list(sem['edges'])  # call_target + call_return (return continuation)
    if sem['kind'] == 'indirect_branch':
        return list(sem['edges'])  # target UNKNOWN, no fallthrough
    return []


def build_blocks(regions, insns_by_addr, size, entry):
    """Partition ALL valid instructions into basic blocks.

    A new block starts at: the candidate entry; any proven direct target (leader, so a
    target landing inside a decoded region splits the block there); the first valid
    instruction; any instruction not fallthrough-contiguous with the previous one
    (preceded by undecodable bytes); or any instruction after a terminator.
    Every decoded instruction is accounted for in exactly one block. Blocks not
    reachable from the candidate entry are orphans (linear sweep only) and are
    reported separately, never counted as reachable code.
    Returns (blocks, leader_starts).
    """
    starts = sorted(insns_by_addr)
    leaders = set([entry]) if entry in insns_by_addr else set()
    for rg in regions:
        for insn in rg['insns']:
            for e in insn['sem']['edges']:
                if e['status'] == 'resolved' and e['target'] is not None \
                        and e['target'] in insns_by_addr:
                    leaders.add(e['target'])
    leader_set = set(leaders)

    blocks = []
    cur = None
    prev_end = None
    prev_terminated = False
    for a in starts:
        insn = insns_by_addr[a]
        contig = prev_end is not None and a == prev_end
        start_new = (a in leader_set) or (cur is None) or (not contig) or prev_terminated
        if start_new:
            if cur is not None:
                blocks.append(cur)
            cur = {'start': a, 'insns': []}
        cur['insns'].append(insn)
        prev_end = a + insn['size']
        prev_terminated = insn['sem']['kind'] in RET_EXIT or insn['sem']['kind'] in (
            'uncond_branch', 'cond_branch', 'direct_call', 'indirect_call', 'indirect_branch')
    if cur is not None:
        blocks.append(cur)

    out = []
    for b in blocks:
        insns = b['insns']
        last = insns[-1]
        b['end'] = last['addr'] + last['size']
        b['insn_count'] = len(insns)
        b['term_edges'] = term_edges_for(last)
        b['insns'] = [block_insn_summary(i) for i in insns]
        out.append(b)
    return out, sorted(leader_set)


def _edge_targets(sem):
    out = []
    for e in sem['edges']:
        out.append({'kind': e['kind'], 'target': e['target'],
                    'target_hex': e.get('target_hex'), 'status': e['status'],
                    'reason': e.get('reason')})
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'spans').mkdir(exist_ok=True)

    container = CONTAINER.read_bytes()
    cver = json.loads(CONTAINER_VERIFIED.read_text())
    payloads_by_slot = {p['slot']: p for p in cver['payloads']}

    per_slot = []
    for slot in SLOTS:
        inv = payloads_by_slot[slot]
        off, size = inv['offset'], inv['length']
        span = container[off:off + size]
        computed_sha = sha(span)
        span_path = OUT / 'spans' / ('cand_%04d.bin' % slot)
        span_path.write_bytes(span)

        lines, rc, stderr, cmdinfo = envydis_run(span_path, 0, size)

        # Byte-grounding: verify every envydis output line's raw bytes against the
        # original payload slice [off + addr : +rawlen].
        mismatches = []
        verified = 0
        for ln in lines:
            a = ln['addr']
            expected = container[off + a:off + a + ln['rawlen']]
            if expected == ln['raw']:
                verified += 1
            else:
                mismatches.append({'addr': a, 'addr_hex': '0x%06X' % a,
                                   'raw': ln['raw'].hex(),
                                   'expected': expected.hex() if expected else None})
        cover_full = (sum(l['rawlen'] for l in lines) == size)

        # Populate valid-start set (per slot) for target resolution.
        global _VALID_STARTS
        _VALID_STARTS = set()
        valid_texts = {}
        for ln in lines:
            if is_valid(ln['text']):
                _VALID_STARTS.add(ln['addr'])
                valid_texts[ln['addr']] = ln

        regions, invalid_spans, insns_by_addr = build_regions(lines, size)
        entry = CANDIDATE_ENTRY[slot]
        entry_proven = entry in _VALID_STARTS

        blocks, leaders = build_blocks(regions, insns_by_addr, size, entry)

        # Finite worklist reachability from the candidate entry over direct edges.
        addr_to_block = {}
        for bi, b in enumerate(blocks):
            for i in b['insns']:
                addr_to_block[i['addr']] = bi
        entry_bi = addr_to_block.get(entry)
        reachable = set()
        work = [entry_bi] if entry_bi is not None else []
        while work:
            bi = work.pop()
            if bi in reachable:
                continue
            reachable.add(bi)
            blk = blocks[bi]
            for e in blk['term_edges']:
                if e['status'] == 'resolved' and e['target'] is not None:
                    tbi = addr_to_block.get(e['target'])
                    if tbi is not None and tbi not in reachable:
                        work.append(tbi)
        reachable_blocks = [blocks[bi] for bi in sorted(reachable)]
        reachable_bytes = sum(i['size'] for b in reachable_blocks for i in b['insns'])
        unreachable_blocks = [b for bi, b in enumerate(blocks) if bi not in reachable]
        unreachable_bytes = sum(i['size'] for b in unreachable_blocks for i in b['insns'])

        # Unresolved edges from reachable blocks, each with a reason.
        unresolved_edges = []
        for bi in sorted(reachable):
            blk = blocks[bi]
            from_addr = blk['insns'][-1]['addr']
            for e in blk['term_edges']:
                if e['status'] != 'resolved' or e['target'] is None:
                    unresolved_edges.append({'from': from_addr,
                                             'from_hex': '0x%06X' % from_addr,
                                             'kind': e['kind'], 'target': e.get('target'),
                                             'target_hex': e.get('target_hex'),
                                             'status': e['status'], 'reason': e.get('reason')})

        # Calls found in reachable blocks: call target tracked separately from
        # the ABI return continuation; indirect call target is UNKNOWN.
        calls = []
        for b in reachable_blocks:
            for i in b['insns']:
                if i['sem_kind'] in ('direct_call', 'indirect_call'):
                    ct = [e for e in i['sem_edges'] if e['kind'] == 'call_target']
                    cr = [e for e in i['sem_edges'] if e['kind'] == 'call_return']
                    ct = ct[0] if ct else None
                    cr = cr[0] if cr else None
                    calls.append({'addr': i['addr'], 'addr_hex': '0x%06X' % i['addr'],
                                  'raw': i['raw'], 'text': i['text'],
                                  'kind': i['sem_kind'],
                                  'call_target': ct['target'] if ct else None,
                                  'call_target_hex': ct.get('target_hex') if ct else None,
                                  'call_target_status': ct['status'] if ct else None,
                                  'call_target_reason': ct.get('reason') if ct else None,
                                  'return_continuation': cr['target'] if cr else None,
                                  'return_continuation_hex': cr.get('target_hex') if cr else None,
                                  'return_continuation_status': cr['status'] if cr else None})

        rec = {
            'slot': slot,
            'container_offset': off, 'container_offset_hex': '0x%08X' % off,
            'size': size, 'sha256': computed_sha,
            'sha256_matches_inventory': computed_sha == inv['sha256'],
            'head16': inv['head16'],
            'envydis': {'path': ENVYDIS, 'args': cmdinfo,
                        'note': '-d/-l passed as explicit hex strings; envydis parses sscanf "%x"'},
            'byte_verification': {'lines_total': len(lines), 'verified_matching': verified,
                                  'mismatches': mismatches, 'cover_full_span': cover_full},
            'valid_instruction_count': len(_VALID_STARTS),
            'invalid_span_count': len(invalid_spans),
            'invalid_span_bytes': sum(s['length'] for s in invalid_spans),
            'invalid_spans': invalid_spans,
            'entry': {'status': 'UNKNOWN',
                      'candidate_entry': entry, 'candidate_entry_hex': '0x%06X' % entry,
                      'candidate_entry_proven_decoded': entry_proven,
                      'basis': ('byte-re-derived primary entry (deep worker FALCON_PAYLOAD_DEEP); '
                                'not proven by external crossref or metadata -> entry kept UNKNOWN')},
            'leaders': sorted(leaders),
            'leader_count': len(leaders),
            'blocks': blocks,
            'block_count': len(blocks),
            'block_bytes': sum(i['size'] for b in blocks for i in b['insns']),
            'reachable': {'block_count': len(reachable_blocks), 'byte_count': reachable_bytes,
                          'block_starts': [b['start'] for b in reachable_blocks]},
            'unreachable': {'block_count': len(unreachable_blocks), 'byte_count': unreachable_bytes,
                            'note': 'linear-sweep decoded regions not reachable via control-flow edges '
                                    'from the candidate entry; NOT counted as reachable code'},
            'calls': calls,
            'call_count': len(calls),
            'unresolved_edges': unresolved_edges,
            'unresolved_edge_count': len(unresolved_edges),
        }
        per_slot.append(rec)

    report = {
        'script': 'falcon_cfg_rebuild.py',
        'rerun': ('cd /home/REDACTED_USER/codex-work/work_v15 && /usr/bin/python3 '
                  'PHASE16/FALCON_CFG_REBUILD/falcon_cfg_rebuild.py'),
        'input_file': str(CONTAINER), 'input_size': len(container),
        'input_sha256': sha(container),
        'inventory_source': str(CONTAINER_VERIFIED),
        'inventory_sha256': sha_file(CONTAINER_VERIFIED),
        'envydis': {'path': ENVYDIS, 'sha256': sha_file(ENVYDIS),
                    'note': 'envydis -d/-l parsed with sscanf "%x"; this script passes explicit hex strings'},
        'radix_defect_note': ('prior phase passed str(skip)/str(limit) (decimal) to envydis -d/-l which '
                              'parses sscanf "%x"; this rebuild uses explicit hex strings so actual == intended'),
        'slots': SLOTS,
        'candidate_entries': {str(s): {'entry': CANDIDATE_ENTRY[s],
                                       'entry_hex': '0x%06X' % CANDIDATE_ENTRY[s]} for s in SLOTS},
        'results': per_slot,
        'conclusion': {
            'entry_status_all_slots': 'UNKNOWN',
            'entry_basis': ('no incoming branch/call target or descriptor cross-reference was established '
                            'for any candidate offset (FALCON_PAYLOAD_DEEP cross-reference analysis: all '
                            'immediates unmatched against container offsets / GSP-SEC2 addresses / descriptor '
                            'VA/file-offsets / GSP disassembly VAs); no linear-sweep offset is promoted to a '
                            'true entry. Candidate entries (0x2A slot 20, 0x16 others) are byte-re-derived '
                            'anchors only, used for bounded CFG traversal.'),
            'engine_role': 'UNKNOWN — no engine<->slot mapping established or inferred; no role guessed from slot number, size, entropy, or decode density.',
            'semantics_enforced': ['no fallthrough after ret/exit/unconditional bra',
                                   'call target UNKNOWN tracked separately from return continuation',
                                   'target never inferred from $r1',
                                   'basic blocks split at proven targets landing inside decoded regions',
                                   'reachable code = control-flow reachable from candidate entry only '
                                   '(linear-sweep orphans excluded)'],
            'limits': ['full-span linear decode IS established for every candidate (no decode window); '
                       'CFG reachability is bounded by the (unproven) candidate entry',
                       'indirect call/jump targets (call $rN, bra $rN) are statically UNKNOWN',
                       'direct branch/call immediates are ambiguous absolute-vs-relative; resolved only '
                       'when one interpretation lands on a valid decoded instruction start',
                       'true entry, engine identity, and indirect targets remain UNKNOWN'],
        },
    }
    (OUT / 'machine.json').write_text(json.dumps(report, indent=2))
    (OUT / 'input_hashes.json').write_text(json.dumps({
        'container_ucodes_tu10x.bin': {'sha256': report['input_sha256'], 'size': report['input_size']},
        'firmware_container_verified.json': report['inventory_sha256'],
        'envydis_binary': report['envydis']['sha256'],
        'this_script': sha_file(__file__),
    }, indent=2))

    log = ['falcon_cfg_rebuild.py run log',
           'command: %s' % report['rerun'],
           'input: %s size=%d sha256=%s' % (report['input_file'], report['input_size'], report['input_sha256']),
           'inventory: %s sha256=%s' % (report['inventory_source'], report['inventory_sha256']),
           'envydis: %s sha256=%s' % (ENVYDIS, report['envydis']['sha256']),
           'script: %s sha256=%s' % (__file__, sha_file(__file__)),
           '',
           'envydis -d/-l passed as explicit hexadecimal strings (parser uses sscanf "%x");',
           'every decoded instruction raw bytes verified against the payload before CFG construction.',
           '']
    for rec in per_slot:
        bv = rec['byte_verification']
        log.append('slot=%-4d off=%s size=%d sha_ok=%s envydis_rc=%s lines=%d verified=%d mismatches=%d cover_full=%s' % (
            rec['slot'], rec['container_offset_hex'], rec['size'],
            rec['sha256_matches_inventory'], rc,
            bv['lines_total'], bv['verified_matching'], len(bv['mismatches']), bv['cover_full_span']))
        log.append('   entry=%s (candidate 0x%06X, UNKNOWN-not-proven) valid_insns=%d invalid_spans=%d invalid_bytes=%d' % (
            rec['entry']['status'], rec['entry']['candidate_entry'],
            rec['valid_instruction_count'], rec['invalid_span_count'], rec['invalid_span_bytes']))
        log.append('   blocks=%d block_bytes=%d reachable_blocks=%d reachable_bytes=%d unreachable_blocks=%d unreachable_bytes=%d calls=%d unresolved_edges=%d' % (
            rec['block_count'], rec['block_bytes'],
            rec['reachable']['block_count'], rec['reachable']['byte_count'],
            rec['unreachable']['block_count'], rec['unreachable']['byte_count'],
            rec['call_count'], rec['unresolved_edge_count']))
        for s in rec['invalid_spans'][:8]:
            log.append('   INVALID_SPAN 0x%06X..0x%06X len=%d bytes=%s' % (
                s['start'], s['end'], s['length'], s['bytes_hex'][:64]))
        if len(rec['invalid_spans']) > 8:
            log.append('   ... %d more invalid spans' % (len(rec['invalid_spans']) - 8))
        for e in rec['unresolved_edges'][:10]:
            log.append('   UNRESOLVED @0x%06X %s target=%s status=%s reason=%s' % (
                e['from'], e['kind'], e.get('target_hex'), e['status'], e['reason']))
        if len(rec['unresolved_edges']) > 10:
            log.append('   ... %d more unresolved edges' % (len(rec['unresolved_edges']) - 10))
    (OUT / 'run.log').write_text('\n'.join(log) + '\n')

    md = ['# FALCON_CFG_REBUILD — repaired Falcon payload CFG, 8 candidate slots',
          '',
          'Slots: %s' % SLOTS,
          '',
          '## Method (read-only, offline)',
          '- Spans re-read from outputs/ucodes_tu10x.bin at VERIFIED container offsets/lengths; sha256 re-checked.',
          '- envydis (-m falcon) run on the FULL span per slot with EXPLICIT HEXADECIMAL -d/-l arguments',
          '  (envydis parses both with sscanf "%x"; the prior phase passed decimal strings and corrupted skip/limit).',
          '- Every decoded instruction raw bytes verified against the payload slice before CFG use;',
          '  exact invalid/undecodable spans recorded.',
          '- Falcon ISA semantics enforced: ret/exit are terminators with no fallthrough;',
          '  bra <cond>/bra $pN imm = conditional branch (target + fallthrough);',
          '  bra imm (no cond) = unconditional branch (target, no fallthrough);',
          '  bra $rN = register-indirect jump (target UNKNOWN, no fallthrough);',
          '  call imm = direct call (target + return continuation);',
          '  call $rN = register-indirect call: call-target UNKNOWN tracked SEPARATELY from the',
          '  ABI return-continuation edge; target never inferred from $r1.',
          '- Basic blocks split whenever a proven direct target lands inside a decoded region.',
          '- Reachability via finite worklist from the bounded candidate entry; every unresolved edge',
          '  carries a reason. Linear-sweep-only regions are not reachable code.',
          '',
          '## Entry status',
          '- All 8 slots: entry = UNKNOWN. No incoming branch/call target or descriptor cross-reference',
          '  was established for any candidate offset (FALCON_PAYLOAD_DEEP cross-reference analysis: all',
          '  immediates unmatched). Candidate entries (byte-re-derived: slot 20 = 0x2A, others = 0x16)',
          '  are bounded traversal anchors only, not proven true entries.',
          '- Engine/role: UNKNOWN — not inferred from slot number, size, entropy, or decode density.',
          '',
          '## Per-slot results',
          '| slot | span_off | size | entry | valid_insns | invalid_spans | invalid_bytes | blocks | reachable_blocks | reachable_bytes | unreachable_blocks | calls | unresolved_edges |',
          '|------|----------|------|-------|-------------|---------------|----------------|--------|------------------|-----------------|--------------------|-------|------------------|',
    ]
    for rec in per_slot:
        md.append('| %s | %s | %d | %s | %d | %d | %d | %d | %d | %d | %d | %d | %d |' % (
            rec['slot'], rec['container_offset_hex'], rec['size'], rec['entry']['status'],
            rec['valid_instruction_count'], rec['invalid_span_count'],
            rec['invalid_span_bytes'], rec['block_count'],
            rec['reachable']['block_count'], rec['reachable']['byte_count'],
            rec['unreachable']['block_count'], rec['call_count'],
            rec['unresolved_edge_count']))
    md.append('')
    md.append('## Limits')
    for k, v in report['conclusion'].items():
        if k == 'limits':
            for item in v:
                md.append('- %s' % item)
    md.append('')
    md.append('## Files')
    md.append('- falcon_cfg_rebuild.py — this script (rerun command in header).')
    md.append('- machine.json — full machine-readable results (per-slot blocks, edges, reachability, invalid spans).')
    md.append('- FALCON_CFG_REBUILD_REPORT.md — this report.')
    md.append('- run.log — execution log with byte-verification and unresolved-edge lines.')
    md.append('- input_hashes.json — input hashes for reproduction.')
    md.append('- spans/cand_NNNN.bin — read-only span copies from the verified container.')
    md.append('')
    md.append('## Constraints honoured')
    md.append('Read-only inputs only; stdlib + already-built envydis; no GPU, no hardware writes, no '
              'signature/key work, no bypass, no brute force, no exploit work. Old/live scripts under '
              'PHASE16/FW_PAYLOAD_RISCV and PHASE16/FALCON_PAYLOAD_DEEP are untouched; this directory '
              'is isolated and new.')
    (OUT / 'FALCON_CFG_REBUILD_REPORT.md').write_text('\n'.join(md) + '\n')
    print('WROTE', OUT / 'machine.json')
    print('WROTE', OUT / 'input_hashes.json')
    print('WROTE', OUT / 'run.log')
    print('WROTE', OUT / 'FALCON_CFG_REBUILD_REPORT.md')


if __name__ == '__main__':
    main()
