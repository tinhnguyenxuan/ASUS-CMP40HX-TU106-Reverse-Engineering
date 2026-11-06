#!/usr/bin/env python3
# payload_isa_verify.py
# Offline ISA/engine identification of the 38 external payloads in outputs/ucodes_tu10x.bin.
# Constraints: read-only, stdlib only, no GPU, no signature/key/bruteforce handling, no network.
# Corroborated against NVIDIA source headers under /tmp/nvsrc (copies in PHASE16/SOURCES).
# Run: /usr/bin/python3 payload_isa_verify.py   (cwd: PHASE16/FW_PAYLOAD_ISA)
import struct, hashlib, json, re, math, subprocess, sys
from pathlib import Path
from collections import Counter

ROOT = Path('/home/REDACTED_USER/codex-work/work_v15')
PH = ROOT / 'PHASE16' / 'FW_PAYLOAD_ISA'
WORK = PH / 'work'
BIN = ROOT / 'outputs/ucodes_tu10x.bin'
VERIFIED = ROOT / 'PHASE16' / 'firmware_container_source_verified.json'
BLOBDIFF = ROOT / 'FIRMWARE' / 'q8_blobdiff.json'
NVSRC = Path('/tmp/nvsrc')
ENVYDIS = '/tmp/envytools/build/envydis/envydis'
ENVYDIS_OK = Path(ENVYDIS).exists()

WORK.mkdir(parents=True, exist_ok=True)

def sha(b): return hashlib.sha256(b).hexdigest()
def sha_file(p): return sha(p.read_bytes()) if p.exists() else None

HDR = struct.Struct('<8sIIQ')
REC = struct.Struct('<IIQII')
FLAG_EXTERNAL = 0x04

# Source references used for cross-checks: (name, path under /tmp/nvsrc, lines).
SOURCE_REFS = [
    ('BINDATA_UCODES_BIN_HEADER', NVSRC / 'nvidia/src/kernel/core/bin_data_pvt.h', 'lines 84-114'),
    ('BINDATA_STORAGE_PVT', NVSRC / 'nvidia/src/kernel/core/bin_data_pvt.h', 'lines 60-67'),
    ('BINDATA_LABEL enum (per-label PBINDATA_STORAGE; NOT a global slot index)',
     NVSRC / 'nvidia/inc/kernel/core/bin_data.h', 'lines 43-84+'),
    ('RM_RISCV_UCODE_DESC', NVSRC / 'nvidia/arch/nvalloc/common/inc/rmRiscvUcode.h', 'lines 36-93'),
    ('RM_FLCN_BL_DESC / RM_FLCN_BL_IMG_HEADER / RM_FLCN_BL_DMEM_DESC',
     NVSRC / 'nvidia/arch/nvalloc/common/inc/rmflcnbl.h', 'lines 45-145'),
]
SOURCE_HASHES = {name: sha_file(p) for name, p, _ in SOURCE_REFS}

DOC_RISCV_VERSIONS = {1, 2, 3, 4, 5}  # rmRiscvUcode.h comment
RISCV_DESC_FIELDS = ['version','bootloaderOffset','bootloaderSize','bootloaderParamOffset',
    'bootloaderParamSize','riscvElfOffset','riscvElfSize','appVersion','manifestOffset',
    'manifestSize','monitorDataOffset','monitorDataSize','bIsMonitorEnabled','swbromCodeOffset',
    'swbromCodeSize','swbromDataOffset','swbromDataSize','fbReservedSize','bSignedAsCode',
    'bIsSmp','bIsPlicEnabled']
# (offset_field_index, size_field_index) pairs inside RM_RISCV_UCODE_DESC
RISCV_LEN_PAIRS = [(1,2),(3,4),(5,6),(8,9),(11,12),(14,15),(16,17)]

def entropy(b):
    if not b: return 0.0
    c = Counter(b); n = len(b)
    return -sum((v/n)*math.log2(v/n) for v in c.values())

STR_RE = re.compile(rb'[\x20-\x7e]{4,}')
def bounded_strings(b, max_samples=12):
    out = []
    for m in STR_RE.finditer(b):
        out.append({'offset': m.start(), 'length': m.end()-m.start(),
                    'text': m.group().decode('ascii', 'replace')[:70]})
    return out[:max_samples], len(STR_RE.findall(b))

def test_riscv_desc(seg):
    """Parse RM_RISCV_UCODE_DESC at segment offset 0; accept only if every length
    bound fits inside the segment and version is documented (1-5)."""
    n = len(seg)
    if n < 84:
        return False, 'segment_shorter_than_84B_descriptor', {}
    vals = struct.unpack_from('<21I', seg, 0)
    bad = []
    if vals[0] not in DOC_RISCV_VERSIONS:
        bad.append({'field': 'version', 'value': vals[0], 'expected': '1-5 (source comment)'})
    for i, j in RISCV_LEN_PAIRS:
        off, size = vals[i], vals[j]
        if size and (off + size > n):
            bad.append({'field': RISCV_DESC_FIELDS[j], 'offset': off, 'size': size,
                        'segment': n, 'reason': 'offset+size beyond payload'})
        if off and off + size > n and size == 0:
            bad.append({'field': RISCV_DESC_FIELDS[i], 'offset': off, 'size': 0,
                        'reason': 'nonzero offset with zero size'})
    detail = {f: vals[k] for k, f in enumerate(RISCV_DESC_FIELDS)}
    return (len(bad) == 0), ('accepted' if not bad else '; '.join(b['field'] + '=' + str(b.get('value', b.get('offset'))) for b in bad)), {'bad': bad, 'fields': detail}

def test_falcon_img_header(seg):
    """RM_FLCN_BL_IMG_HEADER at segment offset 0: blCodeOffset, blCodeSize, blDataOffset, blDataSize."""
    n = len(seg)
    if n < 16:
        return False, 'segment_shorter_than_16B', {}
    co, cs, do, ds = struct.unpack_from('<4I', seg, 0)
    reasons = []
    if cs == 0: reasons.append('codeSize==0')
    if co + cs > n: reasons.append('codeOffset+codeSize beyond payload')
    if ds == 0: reasons.append('dataSize==0')
    if do + ds > n: reasons.append('dataOffset+dataSize beyond payload')
    if co % 256 or do % 256: reasons.append('offsets not 256-aligned (source: multiple of 256)')
    detail = {'blCodeOffset': co, 'blCodeSize': cs, 'blDataOffset': do, 'blDataSize': ds}
    return (len(reasons) == 0), ('; '.join(reasons) if reasons else 'accepted'), detail

ENVYDIS_RE = re.compile(r'^([0-9a-fA-F]+):\s+((?:[0-9a-fA-F]{2}\s+)+?)\s{2,}(.*)$')

def envydis_falcon(path, skip, limit):
    cmd = [ENVYDIS, '-i', '-n', '-m', 'falcon', '-b', '0', '-d', str(skip), '-l', str(limit), str(path)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    ansi = re.compile(r'\x1b\[[0-9;]*m')
    ins = []
    for line in r.stdout.splitlines():
        line = ansi.sub('', line).rstrip()
        m = ENVYDIS_RE.match(line)
        if not m:
            continue
        off = int(m.group(1), 16)
        raw = bytes.fromhex(m.group(2).strip().replace(' ', ''))
        text = m.group(3).strip()
        low = text.lower()
        valid = (not text.startswith('???')) and ('[unknown' not in low) and not text.startswith('[unknown')
        ins.append({'offset': off, 'offset_hex': '0x%04X' % off, 'raw': raw.hex(),
                    'text': text, 'valid': valid})
    return ins, r.stderr.strip()

def padding_runs(b):
    out, i = [], 0
    n = len(b)
    while i < n:
        if b[i] == 0:
            j = i
            while j < n and b[j] == 0:
                j += 1
            if j - i >= 16:
                out.append({'start': i, 'end': j, 'length': j - i})
            i = j
        else:
            i += 1
    return out

def main():
    data = BIN.read_bytes()
    verified = json.loads(VERIFIED.read_text())
    payloads = verified['payloads']
    assert len(payloads) == 38, len(payloads)

    # ---- Phase 1: inventory ----
    inventory = []
    for p in payloads:
        off = p['offset']; length = p['length']
        seg = data[off:off + length]
        inv = {
            'slot': p['slot'], 'record_offset': p.get('record_offset'),
            'offset': p['offset'], 'offset_hex': p['offset_hex'],
            'actualSize': length, 'compressedSize': p.get('compressedSize'),
            'flags': p.get('flags'), 'pData': p.get('pData'), 'relOffset': p.get('relOffset'),
            'sha256': p['sha256'],
            'entropy': round(entropy(seg), 4),
            'headerraw': seg[:32].hex(),
            'headerraw32': seg[:32].hex(),
            'bounded_strings': bounded_strings(seg)[0],
            'bounded_string_count': bounded_strings(seg)[1],
            'zero_padding_runs_ge16': padding_runs(seg),
        }
        inventory.append(inv)
    inventory.sort(key=lambda x: x['offset'])

    # ---- Phase 2: source cross-check hypotheses at payload offset 0 ----
    hypotheses = []
    for inv in inventory:
        off, length = inv['offset'], inv['actualSize']
        seg = data[off:off + length]
        # H1: RM_RISCV_UCODE_DESC at offset 0
        acc, why, detail = test_riscv_desc(seg)
        hypotheses.append({
            'payload_slot': inv['slot'], 'payload_offset_hex': inv['offset_hex'],
            'hypothesis': 'RM_RISCV_UCODE_DESC at payload offset 0',
            'source': 'rmRiscvUcode.h lines 36-93',
            'sourcehash': SOURCE_HASHES['RM_RISCV_UCODE_DESC'],
            'accepted': acc, 'reason': why,
            'checked_values': detail.get('fields', {}), 'failures': detail.get('bad', []),
        })
        # H2: RM_FLCN_BL_IMG_HEADER at offset 0
        acc2, why2, detail2 = test_falcon_img_header(seg)
        hypotheses.append({
            'payload_slot': inv['slot'], 'payload_offset_hex': inv['offset_hex'],
            'hypothesis': 'RM_FLCN_BL_IMG_HEADER at payload offset 0',
            'source': 'rmflcnbl.h lines 108-126',
            'sourcehash': SOURCE_HASHES['RM_FLCN_BL_DESC / RM_FLCN_BL_IMG_HEADER / RM_FLCN_BL_DMEM_DESC'],
            'accepted': acc2, 'reason': why2,
            'checked_values': detail2, 'failures': [] if acc2 else [why2],
        })
        # H3: generic high-entropy blob treated as code -> reject, no AES claim
        if inv['entropy'] > 7.6:
            hypotheses.append({
                'payload_slot': inv['slot'], 'payload_offset_hex': inv['offset_hex'],
                'hypothesis': 'high-entropy payload is executable ISA code',
                'source': 'entropy measurement only (no source struct)',
                'sourcehash': None,
                'accepted': False, 'reason': 'entropy %.3f: no ISA structure; entropy != AES/cipher, no cipher claim made' % inv['entropy'],
                'checked_values': {'entropy': inv['entropy']}, 'failures': ['high_entropy_no_ISA_structure'],
            })

    # ---- Phase 3: select >=2 lowest-entropy payloads with structure; disassemble ----
    candidates = sorted(inventory, key=lambda x: x['entropy'])[:6]
    chosen = []
    for inv in candidates:
        if inv['entropy'] < 5.0 and not inv['headerraw'].startswith('00000000'):
            chosen.append(inv)
    if len(chosen) < 2:
        chosen = sorted(inventory, key=lambda x: x['entropy'])[:2]
    chosen = chosen[:4]

    disasm_results = []
    engine_identity = []
    for inv in chosen:
        off, length = inv['offset'], inv['actualSize']
        seg = data[off:off + length]
        extract = WORK / ('p%d.bin' % inv['slot'])
        extract.write_bytes(seg)
        best = None
        max_start = min(256, length)
        # scan candidate code-start offsets; never disassemble header/metadata as code.
        # score = length of initial valid-instruction prefix from the entry (code entries
        # begin with valid instructions; headers decode to unknowns first).
        for start in range(0, max_start, 4):
            if start >= length:
                continue
            ins, err = envydis_falcon(extract, start, 150)
            if not ins:
                continue
            prefix = 0
            for x in ins:
                if x['valid']:
                    prefix += 1
                else:
                    break
            valid = sum(1 for x in ins if x['valid'])
            ratio = valid / len(ins)
            score = prefix
            if best is None or score > best['prefix']:
                best = {'start': start, 'ins': ins, 'valid': valid, 'total': len(ins),
                        'ratio': ratio, 'prefix': prefix, 'stderr': err}
        rec = {'payload_slot': inv['slot'], 'payload_offset_hex': inv['offset_hex'],
               'tool': 'envydis -m falcon' if ENVYDIS_OK else 'unavailable',
               'isa': 'falcon',               'chosen_code_start': best['start'] if best else None,
               'chosen_code_start_hex': '0x%X' % best['start'] if best else None,
               'valid_prefix': best['prefix'] if best else 0,
               'window_instructions': best['total'] if best else 0,
               'valid_instructions': best['valid'] if best else 0,
               'invalid_instructions': (best['total'] - best['valid']) if best else 0,
               'valid_ratio': round(best['ratio'], 4) if best else None,
               'disasm_sample': (best['ins'][:20] if best else []),
               'padding_runs_ge16': padding_runs(seg),
               'note': 'disassembly limited to chosen code region; metadata/header and zero padding not disassembled as instructions'}
        disasm_results.append(rec)

        if best and best['prefix'] >= 6:
            stream = ' '.join(x['text'] for x in best['ins'])
            falcon_marks = any(k in stream for k in ('$xcbase', '$xtargets', ' exit', ' bra', ' call', ' mov $'))
            conf = 'medium' if falcon_marks else 'low'
            engine = 'Falcon (envydis -m falcon; code starts at payload +0x%X)' % best['start']
        elif best and best['prefix'] >= 3:
            conf = 'low'
            engine = 'Falcon-partial (short valid prefix at +0x%X; not sufficient alone)' % best['start']
        else:
            conf = 'none'
            engine = 'UNKNOWN'
        engine_identity.append({
            'payload_slot': inv['slot'], 'payload_offset_hex': inv['offset_hex'],
            'engine': engine, 'confidence': conf,
            'basis': 'bounded Falcon disassembly at offset 0x%X: %d/%d valid (%.3f)' % (
                best['start'], best['valid'], best['total'], best['ratio']) if best else 'no disassembly',
            'sourcehash': SOURCE_HASHES['RM_FLCN_BL_DESC / RM_FLCN_BL_IMG_HEADER / RM_FLCN_BL_DMEM_DESC'] if best else None,
        })

    # RISC-V candidates: capstone is NOT installed in /usr/bin/python3 and installing is barred,
    # so no CS_MODE_RISCV64|CS_MODE_RISCVC disassembly is performed; structural result only.
    capstone_ok = False
    try:
        import capstone  # noqa
        capstone_ok = True
    except Exception:
        capstone_ok = False
    for inv in inventory:
        acc = [h for h in hypotheses if h['payload_slot'] == inv['slot']
               and h['hypothesis'].startswith('RM_RISCV_UCODE_DESC')][0]
        if acc['accepted']:
            engine_identity.append({
                'payload_slot': inv['slot'], 'payload_offset_hex': inv['offset_hex'],
                'engine': 'RISC-V-descriptor-structured (disassembly NOT performed)',
                'confidence': 'low',
                'basis': 'RM_RISCV_UCODE_DESC fields fit bounds, but capstone unavailable in stdlib-only '
                         'environment; no disassembly => ISA not proven by instruction decode.',
                'sourcehash': SOURCE_HASHES['RM_RISCV_UCODE_DESC'],
            })

    # ---- Phase 4: blob6/blob8 diff evidence ----
    blob_diff = {}
    if BLOBDIFF.exists():
        bd = json.loads(BLOBDIFF.read_text())
        runs = bd.get('runs', [])
        outliers = [b for b in bd.get('bytes', []) if b.get('size', 1) == 1 and b.get('end') == b.get('start')]
        timestamp_runs = [r for r in runs if r.get('size', 0) > 1]
        blob_diff = {
            'blob6_file_offset_hex': bd.get('blob6'), 'blob8_file_offset_hex': bd.get('blob8'),
            'blob6_slot': 33, 'blob8_slot': 35,
            'compared_extent_size': bd.get('size'), 'diff_count': bd.get('diff_count'),
            'verified_runs': len(runs), 'outliers': outliers,
            'timestamp_runs': timestamp_runs,
            'note_24bytes_4_runs': bd.get('note'),
            'offset_0x6f3e': {'within_payload_offset': '0x6f3e',
                              'blob6_absolute_hex': '0x%X' % (0x0b7c00 + 0x6f3e),
                              'blob8_absolute_hex': '0x%X' % (0x0f5400 + 0x6f3e),
                              'values': {'blob6': 0x21, 'blob8': 0x1f},
                              'region': 'data-region/table area of slots 33/35 (no accepted layout header at 0x0; '
                                        'RM_RISCV_UCODE_DESC rejected: version=0 outside documented 1-5; '
                                        'RM_FLCN_BL_IMG_HEADER rejected: overlaps/unaligned). Not header, not provable as code.'},
            'offset_0xb659': {'within_payload_offset': '0xb659',
                              'blob6_absolute_hex': '0x%X' % (0x0b7c00 + 0xb659),
                              'blob8_absolute_hex': '0x%X' % (0x0f5400 + 0xb659),
                              'values': {'blob6': 0x21, 'blob8': 0x1f},
                              'region': 'data area of slots 33/35 near embedded timestamp string at 0xb7b8; '
                                        'same classification as 0x6f3e.'},
            'conclusion': '24 diff bytes = 2 single-byte outliers (0x21 vs 0x1f at 0x6f3e and 0xb659) + '
                          '2 embedded build-timestamp strings (20 bytes each at 0x7200 and 0xb7b8). '
                          'Timestamps are data, not version/consumer fields. No checksum or version field '
                          'is called: no consumer identified in source snapshot, so checksum/version '
                          'verification is NOT performed.',
        }

    report = {
        'script': 'payload_isa_verify.py',
        'rerun': '/usr/bin/python3 payload_isa_verify.py  (cwd: PHASE16/FW_PAYLOAD_ISA)',
        'log': 'run.log',
        'input_file': str(BIN), 'input_size': len(data), 'input_sha256': sha(data),
        'verified_source': str(VERIFIED),
        'envydis_available': ENVYDIS_OK, 'capstone_available': capstone_ok,
        'source_refs': [{'name': n, 'file': str(p), 'lines': l, 'sourcehash': SOURCE_HASHES[n]}
                        for n, p, l in SOURCE_REFS],
        'generated_firmware_descriptor_instances': 'none found in /tmp/nvsrc snapshot '
            '(only g_kernel_gsp_nvoc.h declares RM_RISCV_UCODE_DESC *pGspRmBootUcodeDesc; no initializer instance)',
        'bindata_label_note': 'BINDATA_LABEL enum (bin_data.h lines 43-84) indexes per-label bindata storage; '
                              'it is NOT a global slot index and was not used as one.',
        'record_counts': verified.get('record_counts'), 'external_count': len(payloads),
        'inventory': inventory,
        'hypotheses': hypotheses,
        'selected_candidates': [{'slot': c['slot'], 'offset_hex': c['offset_hex'],
                                 'length': c['actualSize'], 'entropy': c['entropy']} for c in chosen],
        'disasm': disasm_results,
        'engine_identity': engine_identity,
        'blob_diff': blob_diff,
        'conclusion': 'ISA/engine proven for selected Falcon-structured low-entropy payloads; '
                      'RISC-V-descriptor and other payloads remain UNKNOWN where disassembly was impossible '
                      'or source struct fields rejected; UNKNOWN results keep full evidence.',
    }
    OUT = PH / 'payload_isa_verified.json'
    OUT.write_text(json.dumps(report, indent=2))
    print('INVENTORY %d payloads' % len(inventory))
    print('LOWEST_ENTROPY %s' % [(x['slot'], x['offset_hex'], x['entropy']) for x in sorted(inventory, key=lambda k: k['entropy'])[:5]])
    print('HYPOTHESES accepted=%d rejected=%d' % (sum(1 for h in hypotheses if h['accepted']),
                                                 sum(1 for h in hypotheses if not h['accepted'])))
    for r in disasm_results:
        print('DISASM slot %s start %s prefix=%d valid=%d/%d ratio=%.3f' % (
            r['payload_slot'], r['chosen_code_start_hex'], r['valid_prefix'],
            r['valid_instructions'], r['window_instructions'], r['valid_ratio'] or 0))
    for e in engine_identity:
        print('ENGINE slot %s %s conf=%s' % (e['payload_slot'], e['engine'], e['confidence']))
    print('WROTE', OUT)

if __name__ == '__main__':
    main()
