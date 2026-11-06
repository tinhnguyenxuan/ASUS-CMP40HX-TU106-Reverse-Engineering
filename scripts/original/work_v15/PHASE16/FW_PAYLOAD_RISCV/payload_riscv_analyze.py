#!/usr/bin/env python3
# payload_riscv_analyze.py
# Bounded ISA/role analysis of the 38 external payloads in outputs/ucodes_tu10x.bin.
# Phase-16 continuation: RISC-V via capstone (actually available, see discrepancy below),
# Falcon via envydis where present. Read-only inputs; stdlib + installed capstone only;
# no install, no GPU, no keys/signature/bruteforce, no network, no encryption claim,
# no entropy-only ISA claim, no start selection by longest prefix alone.
# Correlates only source-backed structs (RM_RISCV_UCODE_DESC, RM_FLCN_BL_IMG_HEADER,
# BINDATA_UCODES_BIN_HEADER/BINDATA_STORAGE_PVT) from /tmp/nvsrc copies in PHASE16/SOURCES.
# Run: /usr/bin/python3 payload_riscv_analyze.py   (cwd: PHASE16/FW_PAYLOAD_RISCV)
import struct, hashlib, json, math, re, subprocess, sys
from pathlib import Path
from collections import Counter

ROOT = Path('/home/REDACTED_USER/codex-work/work_v15')
PH = ROOT / 'PHASE16' / 'FW_PAYLOAD_RISCV'
ISA_DIR = ROOT / 'PHASE16' / 'FW_PAYLOAD_ISA'
WORK = PH / 'work'
BIN = ROOT / 'outputs/ucodes_tu10x.bin'
INVENTORY_JSON = ISA_DIR / 'payload_isa_verified.json'
ENVYDIS = '/tmp/envytools/build/envydis/envydis'
ENVYDIS_OK = Path(ENVYDIS).exists()

WORK.mkdir(parents=True, exist_ok=True)

def sha(b): return hashlib.sha256(b).hexdigest()
def sha_file(p): return sha(p.read_bytes()) if p.exists() else None

# ---- capstone availability + actual RISC-V decode probe ----
CAPSTONE = {'available': False, 'version': None, 'module': None, 'probe': None, 'error': None}
try:
    from capstone import Cs, CS_ARCH_RISCV, CS_MODE_RISCV64, CS_MODE_RISCVC, CsError
    import capstone as _cap
    CAPSTONE['available'] = True
    CAPSTONE['version'] = getattr(_cap, '__version__', '?')
    CAPSTONE['module'] = _cap.__file__
    md_probe = Cs(CS_ARCH_RISCV, CS_MODE_RISCV64 | CS_MODE_RISCVC)
    probe = bytes.fromhex('130a0000000a0000130b00006780008002a4382380a02083')
    out = [(hex(i.address), i.mnemonic, i.op_str) for i in md_probe.disasm(probe, 0x1000)]
    CAPSTONE['probe'] = {'arch': 'CS_ARCH_RISCV', 'mode': 'CS_MODE_RISCV64|CS_MODE_RISCVC',
                         'bytes': probe.hex(), 'insns': out}
except Exception as e:
    CAPSTONE['error'] = '%s: %s' % (type(e).__name__, e)

MD = None
if CAPSTONE['available']:
    from capstone import Cs, CS_ARCH_RISCV, CS_MODE_RISCV64, CS_MODE_RISCVC, CsError
    MD = Cs(CS_ARCH_RISCV, CS_MODE_RISCV64 | CS_MODE_RISCVC)

# ---- source-backed struct tests ----
DOC_RISCV_VERSIONS = {1, 2, 3, 4, 5}  # rmRiscvUcode.h comment: versions 1-5
RISCV_DESC_FIELDS = ['version','bootloaderOffset','bootloaderSize','bootloaderParamOffset',
    'bootloaderParamSize','riscvElfOffset','riscvElfSize','appVersion','manifestOffset',
    'manifestSize','monitorDataOffset','monitorDataSize','monitorCodeOffset','monitorCodeSize',
    'bIsMonitorEnabled','swbromCodeOffset','swbromCodeSize','swbromDataOffset','swbromDataSize',
    'fbReservedSize','bSignedAsCode','bIsSmp','bIsPlicEnabled']  # 23 u32 = 92 bytes per rmRiscvUcode.h
RISCV_LEN_PAIRS = [(1,2),(3,4),(5,6),(8,9),(10,11),(12,13),(15,16),(17,18)]

def test_riscv_desc(seg):
    n = len(seg)
    if n < 92:
        return False, 'segment_shorter_than_92B_descriptor', {}, []
    vals = struct.unpack_from('<23I', seg, 0)
    bad = []
    if vals[0] not in DOC_RISCV_VERSIONS:
        bad.append({'field': 'version', 'value': vals[0], 'expected': '1-5 (rmRiscvUcode.h)'})
    for i, j in RISCV_LEN_PAIRS:
        off, size = vals[i], vals[j]
        if size and off + size > n:
            bad.append({'field': RISCV_DESC_FIELDS[j], 'offset': off, 'size': size,
                        'segment': n, 'reason': 'offset+size beyond payload'})
        if off and size == 0:
            bad.append({'field': RISCV_DESC_FIELDS[i], 'offset': off, 'size': 0,
                        'reason': 'nonzero offset with zero size'})
    detail = {f: vals[k] for k, f in enumerate(RISCV_DESC_FIELDS)}
    return (len(bad) == 0), ('accepted' if not bad else '; '.join(b['field'] + '=' + str(b.get('value', b.get('offset'))) for b in bad)), detail, bad

def test_falcon_img_header(seg):
    n = len(seg)
    if n < 16:
        return False, 'segment_shorter_than_16B', {}
    co, cs, do, ds = struct.unpack_from('<4I', seg, 0)
    reasons = []
    if cs == 0: reasons.append('codeSize==0')
    if co + cs > n: reasons.append('codeOffset+codeSize beyond payload')
    if ds == 0: reasons.append('dataSize==0')
    if do + ds > n: reasons.append('dataOffset+dataSize beyond payload')
    if co % 256 or do % 256: reasons.append('offsets not 256-aligned (rmflcnbl.h)')
    detail = {'blCodeOffset': co, 'blCodeSize': cs, 'blDataOffset': do, 'blDataSize': ds}
    return (len(reasons) == 0), ('; '.join(reasons) if reasons else 'accepted'), detail

# ---- entropy / strings / padding ----
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

def padding_runs(b):
    out, i, n = [], 0, len(b)
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

# ---- envydis Falcon (reused pattern from Phase 3, never disassembles header as code) ----
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

FALCON_MARKS = ('$xcbase', '$xtargets', ' exit', ' bra', ' call', ' mov $')

# ---- capstone RISC-V bounded scan ----
BRANCH_MN = {'b','beq','bne','blt','bge','bltu','bgeu','jal','jalr','ret','c.ret'}
def is_ct(m):
    return m in BRANCH_MN or m.startswith('c.b') or m.startswith('c.j') or m == 'c.jalr'

def riscv_scan(md, seg, max_start, window):
    """Return list of (start, insns, prefix_bytes, prefix_insns, density) at 4-byte-aligned starts."""
    n = len(seg)
    max_start = min(max_start, n)
    out = []
    for start in range(0, max_start, 4):
        end = min(start + window, n)
        try:
            ins = list(md.disasm(seg[start:end], start))
        except CsError:
            ins = []
        prefix_bytes = 0
        if ins:
            last = ins[-1]
            prefix_bytes = (last.address + last.size) - start
        density = prefix_bytes / float(window)
        out.append({'start': start, 'start_hex': '0x%X' % start, 'prefix_bytes': prefix_bytes,
                    'prefix_insns': len(ins), 'density': round(density, 4),
                    'insns': [{'address': i.address, 'address_hex': '0x%X' % i.address,
                               'size': i.size, 'mnemonic': i.mnemonic, 'op_str': i.op_str,
                               'bytes': i.bytes.hex()} for i in ins]})
    out.sort(key=lambda x: (-x['prefix_insns'], -x['prefix_bytes'], -x['density']))
    return out

def cf_signal(insns, start, window):
    """Control-transfer plausibility: direct branch targets landing inside decoded region."""
    total = 0; in_range = 0; indirect = 0
    end_region = start + window
    for i in insns:
        m = i['mnemonic']
        if not is_ct(m):
            continue
        total += 1
        target = None
        for op in (i.get('operands') or []):
            if op.get('type') == 'imm':
                target = op['value']
        if target is None:
            indirect += 1
            continue
        if target % 4 == 0 and start <= target < end_region:
            in_range += 1
    plausible = (total == 0 and len(insns) >= 16) or (total > 0 and in_range / total >= 0.4)
    return {'ct_total': total, 'ct_in_range': in_range, 'ct_indirect': indirect,
            'cf_ratio': round(in_range/total, 3) if total else None, 'plausible': plausible}

# CS_OP_IMM == 1 in capstone; detail re-disassembly of the chosen stream extracts branch targets.
def cf_signal_detail(md, seg, start, window):
    end = min(start + window, len(seg))
    total = 0; in_range = 0; indirect = 0
    MD2 = Cs(CS_ARCH_RISCV, CS_MODE_RISCV64 | CS_MODE_RISCVC)
    MD2.detail = True
    try:
        ins = list(MD2.disasm(seg[start:end], start))
    except CsError:
        ins = []
    for i in ins:
        m = i.mnemonic
        if not is_ct(m):
            continue
        total += 1
        target = None
        for op in i.operands:
            if op.type == 1:
                target = op.value.imm if hasattr(op.value, 'imm') else op.value
        if target is None:
            indirect += 1
            continue
        if target % 4 == 0 and start <= target < end:
            in_range += 1
    plausible = (total == 0 and len(ins) >= 16) or (total > 0 and in_range / total >= 0.4)
    return {'ct_total': total, 'ct_in_range': in_range, 'ct_indirect': indirect,
            'cf_ratio': round(in_range/total, 3) if total else None, 'plausible': plausible,
            'insn_count': len(ins)}

def score_riscv(res):
    # Combined signal, never longest-prefix alone: prefix insns, density, CF plausibility.
    p = min(res['prefix_insns'], 16) / 16.0
    d = min(res['density'], 1.0)
    c = 1.0 if res.get('cf', {}).get('plausible') else 0.0
    return 0.4*p + 0.4*d + 0.2*c

def verdict_riscv(best):
    if not best or best['prefix_insns'] < 10:
        return False
    if best['density'] < 0.70:
        return False
    return bool(best.get('cf', {}).get('plausible'))

def score_falcon(rec):
    ins = rec['ins']
    if not ins:
        return -1
    prefix = 0
    for x in ins:
        if x['valid']:
            prefix += 1
        else:
            break
    stream = ' '.join(x['text'] for x in ins)
    marks = any(k in stream for k in FALCON_MARKS)
    valid = sum(1 for x in ins if x['valid'])
    density = valid / len(ins)
    return 0.5*min(prefix, 12)/12.0 + 0.3*density + 0.2*(1.0 if marks else 0.0)

def main():
    data = BIN.read_bytes()
    prev = json.loads(INVENTORY_JSON.read_text())
    inventory = prev['inventory']
    assert len(inventory) == 38, len(inventory)

    results = []
    for inv in inventory:
        off = inv['offset']; length = inv['actualSize']
        seg = data[off:off + length]
        rec = {
            'slot': inv['slot'], 'record_offset': inv.get('record_offset'),
            'offset': off, 'offset_hex': inv['offset_hex'],
            'size': length, 'sha256': inv['sha256'], 'entropy': inv['entropy'],
            'headerraw32': inv['headerraw32'], 'flags': inv.get('flags'),
        }
        # Source-backed structural tests at payload offset 0.
        acc_r, why_r, detail_r, bad_r = test_riscv_desc(seg)
        acc_f, why_f, detail_f = test_falcon_img_header(seg)
        rec['struct_tests'] = {
            'RM_RISCV_UCODE_DESC@0': {'source': 'rmRiscvUcode.h lines 36-93', 'version_documented': '1-5',
                                      'accepted': acc_r, 'reason': why_r,
                                      'fields': detail_r, 'failures': bad_r},
            'RM_FLCN_BL_IMG_HEADER@0': {'source': 'rmflcnbl.h lines 108-126', 'accepted': acc_f,
                                        'reason': why_f, 'fields': detail_f},
        }

        # ---- RISC-V bounded capstone scan ----
        riscv = {'engine_available': CAPSTONE['available'], 'capstone': CAPSTONE.copy(),
                 'scan': [], 'best': None, 'verdict': 'no_scan'}
        if MD is not None:
            scan = riscv_scan(MD, seg, max_start=512, window=512)
            # CF + detail only for top candidates (bounded).
            for s in scan[:6]:
                s['cf'] = cf_signal_detail(MD, seg, s['start'], 512)
                s['score'] = score_riscv(s)
                del s['insns']
            scan = scan[:6]
            best = scan[0] if scan else None
            if best:
                best['cf'] = cf_signal_detail(MD, seg, best['start'], 512)
                best['score'] = score_riscv(best)
                # reattach compact insn sample of best stream
                try:
                    ins_sample = []
                    MD3 = Cs(CS_ARCH_RISCV, CS_MODE_RISCV64 | CS_MODE_RISCVC)
                    for i in MD3.disasm(seg[best['start']:best['start']+256], best['start']):
                        ins_sample.append({'address_hex': '0x%X' % i.address, 'size': i.size,
                                           'mnemonic': i.mnemonic, 'op_str': i.op_str,
                                           'bytes': i.bytes.hex()})
                        if len(ins_sample) >= 24:
                            break
                    best['insn_sample'] = ins_sample
                except CsError:
                    best['insn_sample'] = []
            riscv['scan'] = scan
            riscv['best'] = best
            riscv['verdict'] = 'PROVEN_RISCV' if verdict_riscv(best) else 'unsupported_by_signals'
        riscv['discrepancy_note'] = ('payload_isa_verified.json capstone_available=true IS correct for '
                                     '/usr/bin/python3 (capstone 5.0.7); FW_PAYLOAD_ISA_REPORT.md claim '
                                     '"Capstone unavailable" was wrong; RISC-V disassembly below uses '
                                     'CS_ARCH_RISCV | CS_MODE_RISCV64 | CS_MODE_RISCVC')
        rec['riscv'] = riscv

        # ---- Falcon envydis for d0*-family headers (Falcon-era ucode signature bytes) ----
        falcon = {'attempted': ENVYDIS_OK and inv['headerraw32'].startswith('d0'),
                  'entries': [], 'verdict': 'not_attempted'}
        if falcon['attempted']:
            extract = WORK / ('p%d.bin' % inv['slot'])
            extract.write_bytes(seg)
            best_f = None
            for start in range(0, min(256, length), 4):
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
                density = valid / len(ins)
                stream = ' '.join(x['text'] for x in ins)
                marks = any(k in stream for k in FALCON_MARKS)
                falcon['entries'].append({'start': start, 'start_hex': '0x%X' % start,
                                          'prefix': prefix, 'valid': valid, 'total': len(ins),
                                          'density': round(density, 4), 'falcon_marks': marks,
                                          'score': score_falcon({'ins': ins}),
                                          'sample': ins[:12]})
            falcon['entries'].sort(key=lambda x: -x['score'])
            if falcon['entries']:
                best_f = falcon['entries'][0]
                best_f['cf_note'] = 'Falcon CF via envydis text markers, not capstone'
                falcon['verdict'] = ('PROVEN_FALCON' if (best_f['prefix'] >= 8 and best_f['falcon_marks'])
                                     else 'unsupported_by_signals')
            else:
                falcon['verdict'] = 'no_decode'
        rec['falcon'] = falcon

        # ---- Combined verdict ----
        if riscv['verdict'] == 'PROVEN_RISCV':
            rec['verdict'] = {'isa': 'RISC-V', 'role': 'code', 'confidence': 'medium',
                              'basis': 'capstone CS_ARCH_RISCV|CS_MODE_RISCV64|CS_MODE_RISCVC bounded decode: '
                                       '%d insn prefix, density %.3f, CF plausible=%s at payload +%s' % (
                                           riscv['best']['prefix_insns'], riscv['best']['density'],
                                           riscv['best']['cf']['plausible'], riscv['best']['start_hex']),
                              'entry': riscv['best']['start_hex']}
        elif falcon['verdict'] == 'PROVEN_FALCON':
            rec['verdict'] = {'isa': 'Falcon', 'role': 'code', 'confidence': 'medium',
                              'basis': 'envydis -m falcon bounded decode: %d insn prefix, density %.3f, '
                                       'Falcon special-register markers at payload +%s' % (
                                           best_f['prefix'], best_f['density'], best_f['start_hex']),
                              'entry': best_f['start_hex']}
        elif acc_r:
            rec['verdict'] = {'isa': 'RISC-V-descriptor-structure', 'role': 'RM_RISCV_UCODE_DESC',
                              'confidence': 'low', 'basis': 'descriptor fields fit source bounds at offset 0',
                              'entry': '0x0'}
        else:
            rec['verdict'] = {'isa': 'UNKNOWN', 'role': 'undetermined',
                              'confidence': 'none',
                              'basis': 'no source struct accepted; no bounded ISA decode met proof thresholds',
                              'evidence': 'entropy=%.4f header=%s' % (inv['entropy'], inv['headerraw32'][:16])}
        results.append(rec)

    # Summary
    summary = {}
    for r in results:
        key = r['verdict']['isa']
        summary.setdefault(key, []).append(r['slot'])

    report = {
        'script': 'payload_riscv_analyze.py',
        'rerun': '/usr/bin/python3 payload_riscv_analyze.py  (cwd: PHASE16/FW_PAYLOAD_RISCV)',
        'log': 'run.log',
        'input_file': str(BIN), 'input_size': len(data), 'input_sha256': sha(data),
        'inventory_source': str(INVENTORY_JSON),
        'capstone': CAPSTONE,
        'discrepancy_corrected': ('JSON payload_isa_verified.json capstone_available=true was CORRECT for '
                                  '/usr/bin/python3; FW_PAYLOAD_ISA_REPORT.md stated Capstone unavailable — '
                                  'that statement was wrong. capstone 5.0.7 imports under /usr/bin/python3 and '
                                  'CS_ARCH_RISCV | CS_MODE_RISCV64 | CS_MODE_RISCVC decoding was performed. '
                                  'Report corrected below.'),
        'source_refs': [
            {'name': 'BINDATA_UCODES_BIN_HEADER / BINDATA_STORAGE_PVT',
             'file': '/tmp/nvsrc/nvidia/src/kernel/core/bin_data_pvt.h', 'lines': '60-114',
             'sourcehash': sha_file(Path('/tmp/nvsrc/nvidia/src/kernel/core/bin_data_pvt.h'))},
            {'name': 'BINDATA_LABEL enum (per-label index, NOT global slot index)',
             'file': '/tmp/nvsrc/nvidia/inc/kernel/core/bin_data.h', 'lines': '43-110',
             'sourcehash': sha_file(Path('/tmp/nvsrc/nvidia/inc/kernel/core/bin_data.h'))},
            {'name': 'RM_RISCV_UCODE_DESC',
             'file': '/tmp/nvsrc/nvidia/arch/nvalloc/common/inc/rmRiscvUcode.h', 'lines': '36-93',
             'sourcehash': sha_file(Path('/tmp/nvsrc/nvidia/arch/nvalloc/common/inc/rmRiscvUcode.h'))},
            {'name': 'RM_FLCN_BL_DESC / RM_FLCN_BL_IMG_HEADER / RM_FLCN_BL_DMEM_DESC',
             'file': '/tmp/nvsrc/nvidia/arch/nvalloc/common/inc/rmflcnbl.h', 'lines': '45-145',
             'sourcehash': sha_file(Path('/tmp/nvsrc/nvidia/arch/nvalloc/common/inc/rmflcnbl.h'))},
        ],
        'generated_firmware_descriptor_instances': 'none found in /tmp/nvsrc snapshot '
            '(only g_kernel_gsp_nvoc.h declares RM_RISCV_UCODE_DESC *pGspRmBootUcodeDesc; no initializer instance)',
        'record_counts': prev.get('record_counts'), 'external_count': len(inventory),
        'results': results,
        'summary': {k: v for k, v in sorted(summary.items(), key=lambda kv: -len(kv[1]))},
        'conclusion': 'Per-payload proven ISA/role listed in results[].verdict; UNKNOWN entries carry full evidence '
                      '(header, entropy, descriptor reject reasons, decode densities). No ISA claimed from entropy; '
                      'no encryption inferred; no GPU/keys used.',
    }
    OUT = PH / 'payload_riscv_verified.json'
    OUT.write_text(json.dumps(report, indent=2))

    log_lines = [
        'payload_riscv_analyze.py run log',
        'command: /usr/bin/python3 payload_riscv_analyze.py  (cwd: PHASE16/FW_PAYLOAD_RISCV)',
        'input_file: %s  size=%d  sha256=%s' % (str(BIN), len(data), sha(data)),
        'inventory_source: %s  (%d payloads)' % (str(INVENTORY_JSON), len(inventory)),
        'capstone: available=%s version=%s module=%s' % (CAPSTONE['available'], CAPSTONE['version'], CAPSTONE['module']),
        'capstone_probe: %s' % json.dumps(CAPSTONE['probe']),
        'envydis: %s (%s)' % (ENVYDIS_OK, ENVYDIS),
        'discrepancy: payload_isa_verified.json capstone_available=true IS correct for /usr/bin/python3; '
        'FW_PAYLOAD_ISA_REPORT.md claim \"Capstone unavailable\" was wrong; RISC-V decoding below uses '
        'CS_ARCH_RISCV | CS_MODE_RISCV64 | CS_MODE_RISCVC',
        '',
        'per-payload verdict (slot offset_hex size entropy isa role confidence entry basis):',
    ]
    for r in results:
        v = r['verdict']
        rv = r['riscv']; fv = r['falcon']
        entry = v.get('entry') or (rv.get('best') or {}).get('start_hex') or (fv.get('entries') or [{}])[0].get('start_hex') or '-'
        log_lines.append('  slot=%-4d off=%-10s size=%-7d ent=%.4f isa=%-10s role=%-14s conf=%-7s entry=%s basis=%s' % (
            r['slot'], r['offset_hex'], r['size'], r['entropy'], v['isa'], v['role'], v['confidence'],
            entry, v['basis'][:160]))
    log_lines.append('')
    log_lines.append('summary: ' + json.dumps(d['summary'] if False else report['summary']))
    log_lines.append('conclusion: ' + report['conclusion'])
    (PH / 'run.log').write_text('\n'.join(log_lines) + '\n')
    print('WROTE', OUT)
    print('WROTE', PH / 'run.log')

if __name__ == '__main__':
    main()
