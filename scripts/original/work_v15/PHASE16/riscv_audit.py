#!/usr/bin/env python3
"""Offline ELF/RV64 audit. Writes only to the explicit output directory.

Instruction equations: https://github.com/riscv/riscv-isa-manual
No firmware execution, GPU access, or imports of historical project scripts.
"""
import argparse
import collections
import csv
import gzip
import hashlib
import json
from pathlib import Path
import struct

MASK64 = (1 << 64) - 1


def sext(value, bits):
    return (value & ((1 << bits) - 1)) - ((1 << bits) if value & (1 << (bits - 1)) else 0)


def jal(word, pc):
    if word & 0x7f != 0x6f:
        raise ValueError('not JAL')
    imm = ((word >> 31) << 20) | (((word >> 21) & 1023) << 1)
    imm |= (((word >> 20) & 1) << 11) | (((word >> 12) & 255) << 12)
    return (pc + sext(imm, 21)) & MASK64, (word >> 7) & 31


def auipc_jalr(w1, w2, pc):
    rd = (w1 >> 7) & 31
    if w1 & 127 != 0x17 or not rd or w2 & 0x707f != 0x67 or (w2 >> 15) & 31 != rd:
        return None
    return ((pc + sext(w1 & 0xfffff000, 32) + sext(w2 >> 20, 12)) & MASK64) & ~1


def instruction_length(h):
    if h & 3 != 3:
        return 2
    if h & 0x1f != 0x1f:
        return 4
    if h & 0x3f == 0x1f:
        return 6
    if h & 0x7f == 0x3f:
        return 8
    n = (h >> 12) & 7
    if n == 7:
        raise ValueError('reserved instruction length')
    return 10 + 2 * n


def control(word, pc, size):
    """Decode control-flow in RV64I+C; targets are absolute VAs."""
    if size == 2:
        q, f = word & 3, word >> 13
        if q == 1 and f == 5:  # C.J (funct3=001 is C.ADDIW in RV64)
            imm = (((word >> 12) & 1) << 11) | (((word >> 11) & 1) << 4)
            imm |= (((word >> 9) & 3) << 8) | (((word >> 8) & 1) << 10)
            imm |= (((word >> 7) & 1) << 6) | (((word >> 6) & 1) << 7)
            imm |= (((word >> 3) & 7) << 1) | (((word >> 2) & 1) << 5)
            return dict(kind='jump', target=(pc + sext(imm, 12)) & MASK64, rd=0)
        if q == 1 and f in (6, 7):
            imm = (((word >> 12) & 1) << 8) | (((word >> 10) & 3) << 3)
            imm |= (((word >> 5) & 3) << 6) | (((word >> 3) & 3) << 1) | (((word >> 2) & 1) << 5)
            return dict(kind='branch', target=(pc + sext(imm, 9)) & MASK64)
        if q == 2 and f == 4 and word & 0x7c == 0:
            rs = (word >> 7) & 31
            if rs:
                link = (word >> 12) & 1
                return dict(kind='indirect_call' if link else 'return' if rs in (1, 5) else 'indirect_jump', rs1=rs, rd=link)
            if word == 0x9002:
                return dict(kind='trap')
        return None
    if size != 4:
        return None
    opcode = word & 127
    if opcode == 0x6f:
        target, rd = jal(word, pc)
        return dict(kind='call' if rd in (1, 5) else 'jump' if rd == 0 else 'other_link_jump', target=target, rd=rd)
    if opcode == 0x63 and (word >> 12) & 7 in (0, 1, 4, 5, 6, 7):
        imm = ((word >> 31) << 12) | (((word >> 7) & 1) << 11)
        imm |= (((word >> 25) & 63) << 5) | (((word >> 8) & 15) << 1)
        return dict(kind='branch', target=(pc + sext(imm, 13)) & MASK64)
    if word & 0x707f == 0x67:
        rd, rs = (word >> 7) & 31, (word >> 15) & 31
        return dict(kind='return' if rd == 0 and rs in (1, 5) and word >> 20 == 0 else 'indirect_call' if rd in (1, 5) else 'indirect_jump', rd=rd, rs1=rs)
    if word in (0x73, 0x100073):
        return dict(kind='trap')
    return None


class Elf:
    def __init__(self, data, base=0x40):
        self.data, self.base = data, base
        h = struct.unpack_from('<16sHHIQQQIHHHHHH', data, base)
        if h[0][:7] != b'\x7fELF\x02\x01\x01' or h[2] != 243 or h[3] != 1:
            raise ValueError('expected little-endian ELF64 RISC-V')
        self.entry, self.flags = h[4], h[7]
        ph, sh, pe, pn, se, sn, si = h[5], h[6], h[9], h[10], h[11], h[12], h[13]
        if se != 64 or (pn and pe != 56) or si >= sn:
            raise ValueError('unsupported ELF header')
        raw = [struct.unpack_from('<IIQQQQIIQQ', data, base + sh + i * se) for i in range(sn)]
        st = raw[si]
        names = data[base + st[4]:base + st[4] + st[5]]
        self.sections = []
        for i, s in enumerate(raw):
            end = names.find(b'\0', s[0])
            if end < 0:
                raise ValueError('invalid section name')
            rec = dict(index=i, name=names[s[0]:end].decode(), type=s[1], flags=s[2], va=s[3], offset=base + s[4], size=s[5])
            if s[1] != 8 and rec['offset'] + s[5] > len(data):
                raise ValueError('section outside file')
            self.sections.append(rec)
        self.segments = []
        for i in range(pn):
            p = struct.unpack_from('<IIQQQQQQ', data, base + ph + i * pe)
            self.segments.append(dict(type=p[0], flags=p[1], offset=base + p[2], va=p[3], filesz=p[5], memsz=p[6]))

    def at(self, va, size=1):
        hits = [s for s in self.sections if s['type'] != 8 and s['flags'] & 2 and s['va'] <= va and va + size <= s['va'] + s['size']]
        if len(hits) != 1:
            raise ValueError(f'unmapped or ambiguous VA {va:#x}')
        s = hits[0]
        return s['offset'] + va - s['va']

    def cstring(self, va):
        off = self.at(va)
        s = next(s for s in self.sections if s['type'] != 8 and s['flags'] & 2 and s['va'] <= va < s['va'] + s['size'])
        end = self.data.find(b'\0', off, min(off + 256, s['offset'] + s['size']))
        if end < 0 or any(c < 32 or c > 126 for c in self.data[off:end]):
            raise ValueError('not a bounded ASCII string')
        return self.data[off:end].decode()

    def instructions(self, section):
        off, end = section['offset'], section['offset'] + section['size']
        while off + 2 <= end:
            h = struct.unpack_from('<H', self.data, off)[0]
            size = instruction_length(h)
            if off + size > end:
                raise ValueError('truncated instruction')
            word = int.from_bytes(self.data[off:off + min(size, 4)], 'little')
            yield off, section['va'] + off - section['offset'], size, word
            off += size


def dump(path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n')


def audit(root, out):
    data = (root / 'outputs/gsp_tu10x.bin').read_bytes()
    elf = Elf(data)
    out.mkdir(parents=True, exist_ok=True)
    dump(out / 'elf_map.json', dict(inner_offset=elf.base, entry=elf.entry, flags=elf.flags, sections=elf.sections, segments=elf.segments))
    # Locate code by raw-byte signature rather than recycling old virtual addresses.
    sig = bytes.fromhex('b7741a04371c00009384040b130c0c74338c8401')
    off = data.find(sig)
    if off < 0 or data.find(sig, off + 1) != -1:
        raise ValueError('dispatcher signature not unique')
    sec = next(s for s in elf.sections if s['flags'] & 4 and s['offset'] <= off < s['offset'] + s['size'])
    block = sec['va'] + off - sec['offset']
    start, end = block - 0x280, block + 0x564
    if data[elf.at(start):elf.at(start) + 4] != bytes.fromhex('130101f2'):
        raise ValueError('candidate containing function prologue differs')
    table = []
    for i in range(186):
        va = 0x41a70b0 + i * 32
        p = elf.at(va, 32)
        f00 = struct.unpack_from('<H', data, p)[0]
        f04 = struct.unpack_from('<I', data, p + 4)[0]
        f08 = data[p + 8]
        f10 = struct.unpack_from('<Q', data, p + 16)[0]
        f18 = struct.unpack_from('<H', data, p + 24)[0]
        try:
            name = elf.cstring(f10)
            name_off = elf.at(f10)
            begins_after_nul = data[name_off - 1] == 0
        except ValueError:
            name, begins_after_nul = None, None
        table.append(dict(index=i, va=va, file_offset=p, raw=data[p:p + 32].hex(), f00=f00, f04=f04, f08=f08, f10=f10, f18=f18, name=name, name_begins_after_nul=begins_after_nul))
    dump(out / 'descriptor_table.json', table)
    candidates = collections.defaultdict(lambda: collections.Counter())
    xrefs, counts, local = [], [], []
    edge_count = 0
    with gzip.open(out / 'syntactic_call_edges.csv.gz', 'wt', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['source_va', 'target_va', 'kind', 'section'])
        for s in elf.sections:
            if not s['flags'] & 4 or not s['size'] or s['type'] == 8:
                continue
            stat = collections.Counter()
            prev = None
            for p, pc, size, w in elf.instructions(s):
                stat[f'length_{size}'] += 1
                flow = control(w, pc, size)
                if flow and flow['kind'] in ('indirect_call', 'indirect_jump'):
                    if prev and prev[2] == 4 and size == 4:
                        target = auipc_jalr(prev[3], w, prev[1])
                        if target is not None:
                            flow = dict(flow, target=target, encoding='adjacent_auipc_jalr')
                            stat['resolved_auipc_jalr'] += 1
                if flow:
                    stat[flow['kind']] += 1
                    target = flow.get('target')
                    if target is not None:
                        if flow['kind'] in ('call', 'indirect_call'):
                            candidates[target][flow.get('encoding', 'jal')] += 1
                            writer.writerow([hex(pc), hex(target), flow['kind'], s['name']])
                            edge_count += 1
                        if target in (start, block):
                            xrefs.append(dict(pc=pc, file_offset=p, raw=data[p:p+size].hex(), **flow))
                    if start <= pc < end:
                        local.append(dict(pc=pc, file_offset=p, size=size, raw=data[p:p+size].hex(), **flow))
                prev = (p, pc, size, w)
            counts.append(dict(section=s['name'], counts=dict(stat)))
    inventory = []
    for va, refs in sorted(candidates.items()):
        try:
            p = elf.at(va)
            executable = any(s['flags'] & 4 and s['va'] <= va < s['va'] + s['size'] for s in elf.sections)
        except ValueError:
            p, executable = None, False
        inventory.append(dict(va=va, file_offset=p, in_executable_section=executable, refs=dict(refs), status='candidate_from_syntactic_call'))
    dump(out / 'function_candidates.json', inventory)
    dump(out / 'gsp_scan.json', dict(instruction_walk='linear length walk within SHF_EXECINSTR sections; not proof all bytes are reachable code', sections=counts, call_edges=edge_count, unique_candidate_targets=len(inventory), xrefs=xrefs, function_candidate_start=start, function_candidate_end_exclusive=end, descriptor_loop_block=block))
    # Local basic blocks: direct targets plus fallthrough after control flow.
    leaders = {start}
    for ins in local:
        if start <= ins.get('target', -1) < end:
            leaders.add(ins['target'])
        if ins['pc'] + ins['size'] < end:
            leaders.add(ins['pc'] + ins['size'])
    leaders = sorted(leaders)
    blocks = []
    for i, lo in enumerate(leaders):
        hi = leaders[i + 1] if i + 1 < len(leaders) else end
        term = next((x for x in local if x['pc'] + x['size'] == hi), None)
        edges = []
        if term:
            k = term['kind']
            if 'target' in term:
                edges.append(dict(target=term['target'], kind=k))
            elif k not in ('trap',):
                edges.append(dict(target=None, kind=k))
            if k in ('branch', 'call', 'indirect_call', 'other_link_jump'):
                edges.append(dict(target=hi, kind='fallthrough_after_branch_or_assumed_call_return'))
            elif k == 'trap':
                edges.append(dict(target=hi, kind='possible_resume_after_trap'))
        else:
            edges.append(dict(target=hi, kind='fallthrough'))
        blocks.append(dict(start=lo, end_exclusive=hi, terminator=term, edges=edges))
    dump(out / 'local_cfg.json', dict(start=start, end_exclusive=end, function_boundary_status='candidate: prologue to next prologue, not symbol metadata', blocks=blocks))
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_RISCV, capstone.CS_MODE_RISCV64 | capstone.CS_MODE_RISCVC)
    lines = [f'# capstone {capstone.__version__}; true ELF VAs; file offsets explicit']
    for va, length in [(start, end - start), (0x4f075ec, 0x240), (0x4f06ba0, 0xc0)]:
        p = elf.at(va, length)
        for ins in md.disasm(data[p:p + length], va):
            lines.append(f'{ins.address:08x} file={elf.at(ins.address):08x} {ins.bytes.hex():8} {ins.mnemonic:12} {ins.op_str}')
    (out / 'gsp_local_disassembly.txt').write_text('\n'.join(lines) + '\n')
    summary = dict(firmware_sha256=hashlib.sha256(data).hexdigest(), capstone_version=capstone.__version__, inner_elf_offset=elf.base, corrected_loop_va=block, loop_file_offset=off, function_candidate_start=start, table_base_va=0x41a70b0, table_base_file_offset=elf.at(0x41a70b0), entries=len(table), ascii_names=sum(x['name'] is not None for x in table), names_start_after_nul=sum(x['name_begins_after_nul'] is True for x in table), xrefs=xrefs)
    dump(out / 'gsp_summary.json', summary)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--out', type=Path, default=Path(__file__).resolve().parent)
    a = p.parse_args()
    audit(a.root, a.out)
