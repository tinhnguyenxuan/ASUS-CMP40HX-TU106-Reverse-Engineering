#!/usr/bin/env python3
"""GSP callback target investigation: function candidate VA 0x04F5733C (file 0xF5737C).

Read-only, offline. Source binary: /home/REDACTED_USER/codex-work/work_v15/outputs/gsp_tu10x.bin
Inner ELF header at file offset 0x40. VA->file offset via SHF_ALLOC section headers
(stored offsets are relative to the ELF header start at 0x40, so +0x40 header bias is
applied). Empirically verified constant delta: VA - file_offset = 0x3FFFFC0
(e.g. 0x04F575BC - 0xF575FC = 0x3FFFFC0; caller 0x04F06C18 - 0xF06C58 = 0x3FFFFC0).

Disassembles with capstone RISC-V64 + compressed (RISCVC); auipc/jalr/jal/branch/store
fields decoded from raw 32-bit words (little-endian file order).

Scope (per task):
- candidate function 0x04F5733C .. 0x04F57A00 (end_exclusive from gsp_scan.json)
- callback call site 0x04F575E0: ld a5, 0x30(s3); jalr a5
- caller auipc/jalr at 0x04F06C18/1C -> 0x04F5733C (verification from raw bytes)
- helper auipc/jalr at 0x04F57644/48 -> 0x04F075EC (verification from raw bytes)
- live header consumer at 0x0459C5E0 is NOT touched (out of scope, different worker)

Writes only: this directory (report json/md, log, input_hashes.json).
"""

import hashlib
import json
import struct
import sys
from pathlib import Path

ROOT = Path('/home/REDACTED_USER/codex-work/work_v15')
BIN_PATH = ROOT / 'outputs' / 'gsp_tu10x.bin'
OUT_DIR = ROOT / 'PHASE16' / 'GSP_CALLBACK_TARGET'
OUT_DIR.mkdir(parents=True, exist_ok=True)

ELF_BASE = 0x40          # inner ELF header starts at file offset 0x40
VA_FILE_DELTA = 0x3FFFFC0  # VA = file_offset + VA_FILE_DELTA (verified on 6 mapped VAs)
MASK64 = (1 << 64) - 1

REG_NAME = {0: 'zero', 1: 'ra', 2: 'sp', 5: 't0', 6: 't1', 7: 't2', 8: 's0', 9: 's1',
            10: 'a0', 11: 'a1', 12: 'a2', 13: 'a3', 14: 'a4', 15: 'a5', 16: 'a6', 17: 'a7',
            18: 's2', 19: 's3', 20: 's4', 21: 's5', 22: 's6', 23: 's7', 24: 's8',
            28: 't3', 29: 't4', 30: 't5', 31: 't6'}

log_lines = []


def log(*args):
    line = ' '.join(str(a) for a in args)
    log_lines.append(line)
    print(line)


def sext(value, bits):
    return (value & ((1 << bits) - 1)) - ((1 << bits) if value & (1 << (bits - 1)) else 0)


# ---------------------------------------------------------------- ELF mapping

class MiniElf:
    """Tiny ELF64-LE parser: section/segment mapping VA -> file offset only.

    Section header offsets stored in this synthetic ELF are relative to the ELF
    header position (0x40), so the stored offset is shifted by ELF_BASE.
    """

    def __init__(self, data):
        self.data, self.base = data, ELF_BASE
        off = ELF_BASE
        (ident, e_type, e_machine, e_version, e_entry, e_phoff, e_shoff,
         e_flags, e_ehsize, e_phentsize, e_phnum, e_shentsize, e_shnum,
         e_shstrndx) = struct.unpack_from('<16sHHIQQQIHHHHHH', data, off)
        if ident[:4] != b'\x7fELF' or ident[4] != 2 or ident[5] != 1:
            raise ValueError('not ELF64 little-endian')
        if e_machine != 243:
            raise ValueError(f'not RISC-V (e_machine={e_machine})')
        self.entry = e_entry
        self.e_shoff, self.e_shentsize, self.e_shnum = e_shoff, e_shentsize, e_shnum
        self.sections = []
        for i in range(e_shnum):
            s = struct.unpack_from('<IIQQQQIIQQ', data, e_shoff + i * e_shentsize)
            self.sections.append(dict(index=i, name_off=s[0], type=s[1], flags=s[2], va=s[3],
                                      offset=self.base + s[4], size=s[5]))
        shstr = self.sections[e_shstrndx]
        names = data[shstr['offset']:shstr['offset'] + shstr['size']]
        for s in self.sections:
            end = names.find(b'\0', s['name_off'])
            s['name'] = names[s['name_off']:end].decode('utf-8', 'replace') if end >= 0 else f'sec{s["index"]}'

    def resolve(self, va, size=1):
        """Map VA -> (file_offset, source). SHF_ALLOC section first, then PT_LOAD."""
        hits = [s for s in self.sections
                if s['type'] != 8 and (s['flags'] & 2)
                and s['va'] <= va and va + size <= s['va'] + s['size']]
        if len(hits) == 1:
            s = hits[0]
            return s['offset'] + va - s['va'], f"section[{s['index']}]{s['name']}"
        if len(hits) > 1:
            raise ValueError(f'ambiguous VA {va:#x}: {[s["name"] for s in hits]}')
        raise ValueError(f'unmapped VA {va:#x}')

    def read(self, va, size):
        off, _ = self.resolve(va, size)
        return self.data[off:off + size]


# ------------------------------------------------------------- instruction decode

def auipc_decode(word, pc):
    if word & 0x7F != 0x17:
        return None
    rd = (word >> 7) & 31
    imm = sext((word >> 12) & 0xFFFFF, 20)
    return dict(kind='auipc', rd=rd, imm=imm, val=(pc + (imm << 12)) & MASK64)


def jalr_decode(word, pc):
    if (word & 0x707F) != 0x67 or ((word >> 12) & 7) != 0:
        return None
    rd = (word >> 7) & 31
    rs1 = (word >> 15) & 31
    imm = sext(word >> 20, 12)
    return dict(kind='jalr', rd=rd, rs1=rs1, imm=imm)


def jal_decode(word, pc):
    if word & 0x7F != 0x6F:
        return None
    imm = (((word >> 31) & 1) << 20) | (((word >> 21) & 0x3FF) << 1)
    imm |= (((word >> 20) & 1) << 11) | (((word >> 12) & 0xFF) << 12)
    return dict(kind='jal', rd=(word >> 7) & 31,
                target=(pc + sext(imm, 21)) & MASK64)


def branch_decode(word, pc):
    if word & 0x7F != 0x63:
        return None
    funct3 = (word >> 12) & 7
    if funct3 not in (0, 1, 4, 5, 6, 7):
        return None
    imm = (((word >> 31) & 1) << 12) | (((word >> 7) & 1) << 11)
    imm |= (((word >> 25) & 0x3F) << 5) | (((word >> 8) & 0xF) << 1)
    return dict(kind='branch', funct3=funct3,
                target=(pc + sext(imm, 13)) & MASK64)


def dest_reg(word):
    op = word & 0x7F
    if op in (0x13, 0x03, 0x33):
        return (word >> 7) & 31
    if op in (0x17, 0x37):
        return (word >> 7) & 31
    if op == 0x6F:
        rd = (word >> 7) & 31
        return rd if rd != 0 else None
    if op == 0x67:
        if (word >> 12) & 7 != 0:
            return None
        rd = (word >> 7) & 31
        return rd if rd != 0 else None
    return None


def store_decode(word):
    """S-type: sd/sw/sh/sb. base=rs1 bits[19:15], value(rs2) bits[24:20],
    imm = imm[11:5]@bits[31:25] << 5 | imm[4:0]@bits[11:7], sext 12."""
    if word & 0x7F != 0x23:
        return None
    funct3 = (word >> 12) & 7
    kinds = {0: 'sb', 1: 'sh', 2: 'sw', 3: 'sd'}
    if funct3 not in kinds:
        return None
    base = (word >> 15) & 31
    value = (word >> 20) & 31
    imm = sext(((word >> 25) & 0x7F) << 5 | ((word >> 7) & 0x1F), 12)
    return dict(kind=kinds[funct3], base=base, rd=value, offset=imm)


def load_decode(word):
    if word & 0x7F != 0x03:
        return None
    funct3 = (word >> 12) & 7
    kinds = {0: 'lb', 1: 'lh', 2: 'lw', 3: 'ld', 4: 'lbu', 5: 'lhu'}
    if funct3 not in kinds:
        return None
    base = (word >> 15) & 31
    rd = (word >> 7) & 31
    imm = sext(word >> 20, 12)
    return dict(kind=kinds[funct3], base=base, rd=rd, offset=imm)


# ---------------------------------------------------------------- main analysis

def main():
    data = BIN_PATH.read_bytes()
    source_sha = hashlib.sha256(data).hexdigest()
    elf = MiniElf(data)

    report = dict(
        script='PHASE16/GSP_CALLBACK_TARGET/gsp_callback_target_analyze.py',
        bin=str(BIN_PATH),
        bin_size=len(data),
        source_sha256=source_sha,
        inner_elf_offset=ELF_BASE,
        va_file_delta=VA_FILE_DELTA,
        capstone=False,
        delta_verified=False,
        mapping_sanity={},
        caller={},
        function_window={},
        calls=[],
        branches=[],
        jumps=[],
        stores=[],
        loads=[],
        pointer_constants=[],
        context_derivation={},
        callback_site={},
        helper={},
        static_pointer_constants=[],
        context_plus_0x30_store=None,
        conclusion={},
        unknowns=[],
        evidence=[],
    )

    try:
        from capstone import Cs, CS_ARCH_RISCV, CS_MODE_RISCV64, CS_MODE_RISCVC
        report['capstone'] = True
    except Exception as exc:
        report['capstone_error'] = repr(exc)

    # delta cross-check on mapped key VAs
    delta_ok = True
    for va in (0x04F575BC, 0x04F5733C, 0x04F575E0, 0x04F06C18, 0x04F075EC, 0x041A70B0):
        try:
            off, src = elf.resolve(va, 4)
            if va - off != VA_FILE_DELTA:
                delta_ok = False
        except ValueError:
            delta_ok = False
    report['delta_verified'] = delta_ok
    log(f"VA-file delta verified={delta_ok} (delta=0x{VA_FILE_DELTA:08x})")

    def word_at(va):
        off, src = elf.resolve(va, 4)
        return struct.unpack_from('<I', data, off)[0], off, src

    def raw_file_order(va, size=4):
        off, src = elf.resolve(va, size)
        return data[off:off + size].hex(), off, src

    # expected raw bytes (file order) from verified disassembly - mapping sanity checks
    expected_raw = {
        0x04F06C18: '97000500',   # auipc ra, 5
        0x04F06C1C: 'e7804072',   # jalr ra, ra, 0x724
        0x04F5733C: '130101f2',   # addi sp, sp, -0xe0  (function candidate entry)
        0x04F575D4: '83b70903',   # ld a5, 0x30(s3)
        0x04F575D8: '035684f7',   # lhu a2, -0x88(s0)
        0x04F575DC: '13850900',   # mv a0, s3
        0x04F575E0: 'e7800700',   # jalr a5   (callback indirect call)
        0x04F57644: '9700fbff',   # auipc ra, 0xfffb0
        0x04F57648: 'e78080fa',   # jalr ra, ra, -0x58
        0x04F5764C: '93050500',   # mv a1, a0
        0x04F57650: 'e31205f8',   # bnez a0, -0x7c
        0x04F075EC: '130101fc',   # entry helper addi sp, sp, -0x40
    }
    mapping_ok = True
    for va, exp in expected_raw.items():
        got, off, src = raw_file_order(va)
        ok = got == exp
        mapping_ok = mapping_ok and ok
        report['mapping_sanity'][hex(va)] = dict(file_offset=off, source=src, raw=got,
                                                 expected=exp, match=ok)
        log(f"sanity 0x{va:08x} file {off:#x} raw {got} expected {exp} match={ok}")
    if not mapping_ok:
        raise RuntimeError('mapping sanity check failed: resolved bytes do not match verified disassembly')

    # ----------------------------------------------- caller verification (0x0459C5E0 not touched)
    caller_va = 0x04F06C18
    w_auipc, off_auipc, src_auipc = word_at(caller_va)
    w_jalr, off_jalr, src_jalr = word_at(caller_va + 4)
    au = auipc_decode(w_auipc, caller_va)
    jr = jalr_decode(w_jalr, caller_va + 4)
    target = (au['val'] + jr['imm']) & ~1 & MASK64 if (au and jr) else None
    rau, _o1, _s1 = raw_file_order(caller_va)
    rjr, _o2, _s2 = raw_file_order(caller_va + 4)
    report['caller'] = dict(
        va=caller_va, file_offset=off_auipc, source=src_auipc,
        auipc_va=caller_va, auipc_raw=rau, jalr_va=caller_va + 4, jalr_raw=rjr,
        auipc_decoded=au, jalr_decoded=jr,
        computed_target=target, verified_target_0x4f5733c=(target == 0x04F5733C),
        note='AUIPC ra,5 @0x4F06C18 + JALR ra,ra,0x724 @0x4F06C1C; live header consumer at 0x0459C5E0 NOT touched',
    )
    log(f"caller 0x{caller_va:08x} (file {off_auipc:x}): auipc raw {rau} jalr raw {rjr} -> computed target 0x{target:08x} (verified={target == 0x04F5733C})")

    # ----------------------------------------------- disassemble candidate function
    fn_start = 0x04F5733C
    fn_end = 0x04F57A00  # function_candidate_end_exclusive (gsp_scan.json)
    off_start, src_start = elf.resolve(fn_start, fn_end - fn_start)
    raw = data[off_start:off_start + (fn_end - fn_start)]

    from capstone import Cs, CS_ARCH_RISCV, CS_MODE_RISCV64, CS_MODE_RISCVC
    md = Cs(CS_ARCH_RISCV, CS_MODE_RISCV64 | CS_MODE_RISCVC)
    insns = []
    for ins in md.disasm(raw, fn_start):
        if ins.address >= fn_end:
            break
        off, src = elf.resolve(ins.address, ins.size)
        insns.append(dict(va=ins.address, file_offset=off, src=src,
                          bytes=ins.bytes.hex(), size=ins.size,
                          mnemonic=ins.mnemonic, op_str=ins.op_str))

    report['function_window'] = dict(
        start=fn_start, start_file_offset=off_start, end_exclusive=fn_end,
        end_file_offset=off_start + (fn_end - fn_start),
        backing=src_start, count=len(insns),
        instructions=insns,
    )
    log(f"function 0x{fn_start:08x}..0x{fn_end:08x} (file 0x{off_start:x}..0x{off_start + fn_end - fn_start:x}) backing={src_start} insns={len(insns)}")

    word_by_va = {}
    raw_by_va = {}
    for ins in insns:
        word_by_va[ins['va']] = struct.unpack_from('<I', data, ins['file_offset'])[0]
        raw_by_va[ins['va']] = ins['bytes']

    # ----------------------------------------------- control flow, calls, stores, loads, pointer constants (one pass)
    CALLER_SAVED_REGS = {1, 5, 6, 7, 10, 11, 12, 13, 14, 15, 16, 17, 28, 29, 30, 31}
    auipc_pending = None
    calls = []
    branches = []
    jumps = []
    stores = []
    loads = []
    pointer_constants = []
    reg_const = {}  # rd -> (constant, forming_va) for lui/addi/ori address formation

    def drop_caller_saved():
        for r in CALLER_SAVED_REGS:
            reg_const.pop(r, None)

    for ins in insns:
        va = ins['va']
        word = word_by_va[va]
        raw = raw_by_va[va]
        wr = dest_reg(word)
        just_formed = False
        au = auipc_decode(word, va)
        if au:
            auipc_pending = (va, au)
            reg_const[au['rd']] = (au['val'], va)
            just_formed = True
            continue
        if auipc_pending is not None:
            pv, pdec = auipc_pending
            auipc_pending = None
            jr = jalr_decode(word, va)
            if jr and jr['rs1'] == pdec['rd'] and va == pv + 4:
                tgt = (pdec['val'] + jr['imm']) & ~1 & MASK64
                calls.append(dict(kind='direct_auipc_jalr', auipc_va=pv, jalr_va=va,
                                  auipc_raw=raw_by_va[pv], jalr_raw=raw,
                                  computed_target=tgt,
                                  target_in_function=(fn_start <= tgt < fn_end),
                                  note='adjacent auipc+jalr pair'))
                drop_caller_saved()
                continue
        jr = jalr_decode(word, va)
        if jr:
            calls.append(dict(kind='indirect_jalr', va=va, file_offset=ins['file_offset'],
                              raw=raw, rs1=REG_NAME.get(jr['rs1'], jr['rs1']),
                              imm=jr['imm'], target='UNKNOWN_indirect',
                              note='jalr through register; target not derivable from static bytes'))
            drop_caller_saved()
            if wr is not None and wr != 1:
                reg_const.pop(wr, None)
            continue
        jl = jal_decode(word, va)
        if jl:
            jumps.append(dict(kind='jal', va=va, raw=raw, target=jl['target'],
                              target_in_function=(fn_start <= jl['target'] < fn_end)))
            drop_caller_saved()
            if jl['rd'] != 0:
                reg_const.pop(jl['rd'], None)
            continue
        br = branch_decode(word, va)
        if br:
            branches.append(dict(kind='branch', va=va, raw=raw, funct3=br['funct3'],
                                 target=br['target'],
                                 target_in_function=(fn_start <= br['target'] < fn_end)))
            continue
        st = store_decode(word)
        if st:
            entry = dict(va=va, file_offset=ins['file_offset'], raw=raw,
                         **st, base_reg=REG_NAME.get(st['base'], st['base']),
                         value_reg=REG_NAME.get(st['rd'], st['rd']))
            if st['rd'] in reg_const:
                const, src = reg_const[st['rd']]
                entry['stored_constant'] = const
                entry['stored_constant_hex'] = format(const, '016x')
                entry['constant_formed_at'] = src
                pointer_constants.append(dict(store_va=va,
                                              value_reg=REG_NAME.get(st['rd'], st['rd']),
                                              address_expr=f"{entry['base_reg']}+{st['offset']:#x}",
                                              constant=const, constant_hex=format(const, '016x'),
                                              formed_at=src))
            stores.append(entry)
        ld = load_decode(word)
        if ld:
            loads.append(dict(va=va, file_offset=ins['file_offset'], raw=raw,
                              **ld, base_reg=REG_NAME.get(ld['base'], ld['base']),
                              dest_reg=REG_NAME.get(ld['rd'], ld['rd'])))
        op = word & 0x7F
        if op == 0x37:  # LUI
            rd = (word >> 7) & 31
            reg_const[rd] = (((word >> 12) & 0xFFFFF) << 12, va)
            just_formed = True
        elif op == 0x13:  # OP-IMM: addi(f3=0), ori(f3=1), ...
            rd = (word >> 7) & 31
            rs1 = (word >> 15) & 31
            imm = sext(word >> 20, 12)
            funct3 = (word >> 12) & 7
            if rs1 in reg_const:
                base_const, _ = reg_const[rs1]
                if funct3 == 0:   # ADDI
                    reg_const[rd] = ((base_const + imm) & MASK64, va)
                elif funct3 == 1:  # ORI (zero-extended 12-bit imm)
                    reg_const[rd] = (base_const | (imm & 0xFFF), va)
                else:
                    reg_const.pop(rd, None)
                just_formed = True
            else:
                reg_const.pop(rd, None)
        if not just_formed and wr is not None:
            reg_const.pop(wr, None)

    report['calls'] = calls
    report['branches'] = branches
    report['jumps'] = jumps
    report['stores'] = stores
    report['loads'] = loads
    report['pointer_constants'] = pointer_constants
    ndirect = sum(1 for c in calls if c['kind'] == 'direct_auipc_jalr')
    nindirect = sum(1 for c in calls if c['kind'] == 'indirect_jalr')
    log(f"calls={len(calls)} (direct={ndirect}, indirect={nindirect}) branches={len(branches)} jumps={len(jumps)}")
    for c in calls:
        tgt = c.get('computed_target', c.get('target'))
        tgt_s = f"0x{tgt:08x}" if isinstance(tgt, int) else str(tgt)
        log(f"  call {c['kind']} @0x{c.get('va', c.get('auipc_va')):08x} -> {tgt_s} "
            f"{'in-fn' if c.get('target_in_function', False) else 'EXTERNAL'}")
    log(f"stores={len(stores)} loads={len(loads)} stored_pointer_constants={len(pointer_constants)}")
    for pc_ in pointer_constants:
        log(f"  store {pc_['value_reg']} -> {pc_['address_expr']} @0x{pc_['store_va']:08x} "
            f"constant 0x{pc_['constant']:016x} (formed @0x{pc_['formed_at']:08x})")

    # any store to s3 + 0x30 (context + 0x30, the callback pointer slot)?
    s3 = 19
    store_to_context_0x30 = [s for s in stores if s['base'] == s3 and s['offset'] == 0x30]
    report['context_plus_0x30_store'] = store_to_context_0x30
    log(f"stores to *(s3+0x30) in-function: {len(store_to_context_0x30)} -> "
        f"{'PROVEN write present' if store_to_context_0x30 else 'NONE (slot writer is outside this function)'}")

    # ----------------------------------------------- context derivation at function entry
    context = dict(
        arg0_a0_copied_to_s5_at='0x04F5736C',
        arg1_a1_copied_to_s4_at='0x04F57378',
        arg2_a2_copied_to_s8_at='0x04F57394',
        arg3_a3_copied_to_s1_at='0x04F57390',
        s3_context='mv s3, a0 @ 0x04F573AC (a0 = return of auipc+jalr internal call @ 0x04F5739C/0x04F573A0)',
        s0_frame='addi s0, sp, 0xe0 @ 0x04F57368',
        note='s3 (context pointer loaded at callback via ld a5, 0x30(s3)) is the return value of the '
             'internal call at 0x04F5739C/0x04F573A0, not an original function argument',
    )
    w1 = word_by_va.get(0x04F5739C)
    w2 = word_by_va.get(0x04F573A0)
    if w1 is not None and w2 is not None:
        au = auipc_decode(w1, 0x04F5739C)
        jr = jalr_decode(w2, 0x04F573A0)
        if au and jr and jr['rs1'] == au['rd']:
            tgt = (au['val'] + jr['imm']) & ~1 & MASK64
            context['internal_call_target'] = tgt
            context['internal_call_target_hex'] = format(tgt, '08x')
    report['context_derivation'] = context
    if 'internal_call_target_hex' in context:
        log(f"context: s3 = return of internal call @0x04F5739C/3A0 target=0x{context['internal_call_target']:08x}")
    else:
        log("context: s3 = internal call return (target decode pending)")

    vchain = []
    for va in (0x04F573D4, 0x04F573DC, 0x04F573E8):
        if va in word_by_va:
            vchain.append(dict(va=va, raw=raw_by_va[va]))
    report['vtable_indirect_call_chain'] = vchain
    log(f"indirect call chain at s3+0x20: {vchain}")

    # ----------------------------------------------- callback site analysis 0x04F575E0
    cb_va = 0x04F575E0
    cb_instrs = [ins for ins in insns if 0x04F575D4 <= ins['va'] < cb_va + 4]
    cb_predecessors = []
    for b in branches:
        if b['target'] == cb_va:
            cb_predecessors.append(dict(kind='branch', **b))
    for j in jumps:
        if j['target'] == cb_va:
            cb_predecessors.append(dict(kind='jal', **j))
    fallthrough = None
    for ins in insns:
        if ins['va'] + ins['size'] == cb_va:
            fallthrough = ins
    report['callback_site'] = dict(
        va=cb_va, file_offset=elf.resolve(cb_va, 4)[0],
        instructions=[dict(va=i['va'], file_offset=i['file_offset'], raw=i['bytes'],
                           mnemonic=i['mnemonic'], op_str=i['op_str']) for i in cb_instrs],
        predecessors=cb_predecessors,
        fallthrough=dict(va=fallthrough['va'], raw=fallthrough['bytes'],
                         mnemonic=fallthrough['mnemonic'], op_str=fallthrough['op_str']) if fallthrough else None,
    )
    # register defs straight-line from 0x04F575D4 to callback
    reg_last_write = {10: None, 11: None, 12: None}
    reg_writes = {10: [], 11: [], 12: []}
    calls_in_window = [c for c in calls
                       if (c['kind'] == 'direct_auipc_jalr' and 0x04F575D4 <= c['auipc_va'] < cb_va)
                       or (c['kind'] == 'indirect_jalr' and 0x04F575D4 <= c['va'] < cb_va)]
    for ins in insns:
        va = ins['va']
        if va > cb_va:
            break
        if va < 0x04F575D4:
            continue
        wr = dest_reg(word_by_va[va])
        if wr in reg_last_write:
            rec = dict(va=va, file_offset=ins['file_offset'], raw=raw_by_va[va],
                       mnemonic=ins['mnemonic'], op_str=ins['op_str'])
            reg_last_write[wr] = rec
            reg_writes[wr].append(rec)
    reg_report = {}
    for reg, name in ((10, 'a0'), (11, 'a1'), (12, 'a2')):
        reg_report[name] = dict(
            last_write=reg_last_write[reg],
            all_writes=reg_writes[reg],
            calls_between_def_and_use=calls_in_window,
        )
    report['callback_site']['register_defs_straight_line'] = reg_report

    path_first_entry = dict(
        name='first_entry_via_j_0x04F575D0',
        route='0x04F575BC..0x04F575D0 j -> 0x04F575D4 fall-through into callback',
        a0='s3 (mv a0, s3 @ 0x04F575DC; no write between def and call) -> PROVEN',
        a1=('mv a1, s4 @ 0x04F575A4 is KILLED by external auipc+jalr call @ 0x04F575AC/0x04F575B0 '
            '(computed target 0x04F4B504); no a1 write between that call and 0x04F575E0 -> '
            'CALL-CLOBBERED, UNKNOWN statically'),
        a2=('lhu a2, -0x88(s0) @ 0x04F575D8 -> PROVEN straight-line; slot s0-0x88 written earlier by '
            'sh a7, -0x88(s0) @ 0x04F57630 of a prior iteration; first-iteration initializing store not '
            'dominated in this function -> initial value not determined statically'),
    )
    path_backedge = dict(
        name='loop_backedge_via_bnez_0x04F57650',
        route='helper call @0x04F57644/48 -> mv a1, a0 @0x04F5764c -> bnez a0,-0x7c @0x04F57650 taken -> 0x04F575D4',
        a0='s3 (mv a0, s3 @ 0x04F575DC) -> PROVEN',
        a1=('helper return: mv a1, a0 @ 0x04F5764C (a0 = helper return value); no call between mv and '
            'callback -> PROVEN = helper return'),
        a2=('lhu a2, -0x88(s0) @ 0x04F575D8 reloaded after helper; slot possibly mutated by helper '
            '(see a2_alias) -> NOT statically pinned'),
    )
    report['callback_site']['predecessor_paths'] = [path_first_entry, path_backedge]

    # helper target from raw @ 0x04F57644/48
    h_auipc = word_by_va.get(0x04F57644)
    h_jalr = word_by_va.get(0x04F57648)
    h_au = auipc_decode(h_auipc, 0x04F57644)
    h_jr = jalr_decode(h_jalr, 0x04F57648)
    h_target = (h_au['val'] + h_jr['imm']) & ~1 & MASK64 if (h_au and h_jr and h_jr['rs1'] == h_au['rd']) else None
    raport, _ro, _rs = raw_file_order(0x04F57644)
    rjh, _ro2, _rs2 = raw_file_order(0x04F57648)
    report['helper'] = dict(
        auipc_va=0x04F57644, auipc_raw=raport, jalr_va=0x04F57648, jalr_raw=rjh,
        decoded=dict(auipc=h_au, jalr=h_jr),
        computed_target=h_target, verified=(h_target == 0x04F075EC),
    )
    log(f"helper 0x04F57644/48: auipc raw {raport} jalr raw {rjh} -> 0x{h_target:08x} verified={h_target == 0x04F075EC}")

    report['a2_alias_note'] = dict(
        a2_at_callback='lhu a2, -0x88(s0) @ 0x04F575D8 (slot = s0-0x88 = sp+0x58, frame field save area)',
        slot_writer_in_function='sh a7, -0x88(s0) @ 0x04F57630 (a7 = lhu entry+0, i.e. entry f00 u16)',
        helper_args='a0=s5, a1=s4, a2=s0-0xe0 (= caller sp, frame base) @ 0x04F57624/0x04F57620/0x04F575FC',
        helper_inner_call='auipc+jalr @ 0x04F57664/0x04F57668 with a2=0x150 (memset-like span from frame base) '
                          '-> slot s0-0x88 lies within [sp, sp+0x150); helper mutation of the a2 source slot '
                          'is NOT excluded statically',
        conclusion='a2 == entry.f00 chain is evidenced per iteration; helper aliasing of the slot unresolved',
    )

    # ----------------------------------------------- conclusion
    static_constants_hex = [p['constant_hex'] for p in pointer_constants]
    conclusion = dict(
        callback_target='UNKNOWN_indirect',
        callback_mechanism='jalr a5 at 0x04F575E0 where a5 = ld a5, 0x30(s3) @ 0x04F575D4 (indirect via context+0x30)',
        context_plus_0x30_writer='NOT found in-function 0x04F5733C..0x04F57A00; slot written by callee(s) '
                                 '(context allocator call @0x04F5739C/3A0 callee, or s3+0x20 vtable init chain) outside this window',
        proven_assignments_to_context_0x30=[],
        candidate_static_pointer_constants=static_constants_hex,
        candidate_static_targets_proven=False,
        a0_at_call='s3 (context) PROVEN on both predecessor paths',
        a1_at_call='PATH-SENSITIVE: first entry = call-clobbered UNKNOWN (external call @0x04F575AC/5B0 kills mv a1,s4 @0x04F575A4); '
                   'back-edge = helper return PROVEN via mv a1,a0 @0x04F5764C',
        a2_at_call='entry f00 u16 from stack slot s0-0x88 PROVEN straight-line; helper mutation of slot not excluded',
        a1_equals_s4_at_call=False,
        a1_equals_s4_note='do not revive a1=s4 at the callback call; mv a1,s4 @ 0x04F57378/0x04F575A4/0x04F5761C are defs elsewhere '
                          '(arg copy / helper arg / post-call), none is the live def at 0x04F575E0 on all paths',
        header_consumer_0x0459c5e0='NOT touched; out of scope for this worker',
        unknowns=[
            'callback target via *(s3+0x30): indirect, value not derivable from static bytes',
            'writer of context+0x30: outside this function window (context allocator call @0x04F5739C/3A0 callee, or s3+0x20 vtable init chain)',
            'a1 at callback on first-entry path: call-clobbered by external call @0x04F575AC/5B0',
            'initial value of stack slot s0-0x88 before first loop iteration: no dominating store in this function',
            'helper 0x04F075EC effect on stack slot s0-0x88 (a2 source for next iteration): not excluded statically',
        ],
    )
    report['conclusion'] = conclusion
    log("CONCLUSION: callback target UNKNOWN (indirect *(s3+0x30)); context+0x30 store: none in-function; "
        "a0=s3 proven; a1 path-sensitive (first entry UNKNOWN clobbered, back-edge helper return); "
        "a1=s4 at call: FALSE (do not revive)")

    report['evidence'] = [
        dict(path=str(BIN_PATH), sha256=source_sha, bytes=len(data), role='source binary (original ELF container)'),
        dict(path='/home/REDACTED_USER/codex-work/work_v15/PHASE16/gsp_callback_verified.json', role='prior verified callback window'),
        dict(path='/home/REDACTED_USER/codex-work/work_v15/PHASE16/gsp_callback_verified.txt', role='prior verified disassembly text'),
        dict(path='/home/REDACTED_USER/codex-work/work_v15/PHASE16/gsp_callback_coordinator_review.json', role='coordinator review gates'),
        dict(path='/home/REDACTED_USER/codex-work/work_v15/PHASE16/REVIEW_NOTES.md', role='coordinator review notes'),
        dict(path='/home/REDACTED_USER/codex-work/work_v15/PHASE16/gsp_scan.json', role='function window bounds (start/end exclusive)'),
        dict(path='/home/REDACTED_USER/codex-work/work_v15/PHASE16/gsp_local_disassembly.txt', role='reference disassembly of candidate function'),
        dict(path='/home/REDACTED_USER/codex-work/work_v15/PHASE16/gsp_callback_verify.py', role='reference verifier (ELF0x40 mapping pattern)'),
    ]

    (OUT_DIR / 'gsp_callback_target_report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    (OUT_DIR / 'run.log').write_text('\n'.join(log_lines) + '\n')
    (OUT_DIR / 'input_hashes.json').write_text(json.dumps({
        str(BIN_PATH): dict(bytes=len(data), sha256=source_sha),
        '/home/REDACTED_USER/codex-work/work_v15/PHASE16/gsp_callback_verified.json': dict(
            bytes=Path('/home/REDACTED_USER/codex-work/work_v15/PHASE16/gsp_callback_verified.json').stat().st_size,
            sha256=hashlib.sha256(Path('/home/REDACTED_USER/codex-work/work_v15/PHASE16/gsp_callback_verified.json').read_bytes()).hexdigest()),
        '/home/REDACTED_USER/codex-work/work_v15/PHASE16/gsp_callback_verified.txt': dict(
            bytes=Path('/home/REDACTED_USER/codex-work/work_v15/PHASE16/gsp_callback_verified.txt').stat().st_size,
            sha256=hashlib.sha256(Path('/home/REDACTED_USER/codex-work/work_v15/PHASE16/gsp_callback_verified.txt').read_bytes()).hexdigest()),
        '/home/REDACTED_USER/codex-work/work_v15/PHASE16/gsp_callback_coordinator_review.json': dict(
            bytes=Path('/home/REDACTED_USER/codex-work/work_v15/PHASE16/gsp_callback_coordinator_review.json').stat().st_size,
            sha256=hashlib.sha256(Path('/home/REDACTED_USER/codex-work/work_v15/PHASE16/gsp_callback_coordinator_review.json').read_bytes()).hexdigest()),
        '/home/REDACTED_USER/codex-work/work_v15/PHASE16/REVIEW_NOTES.md': dict(
            bytes=Path('/home/REDACTED_USER/codex-work/work_v15/PHASE16/REVIEW_NOTES.md').stat().st_size,
            sha256=hashlib.sha256(Path('/home/REDACTED_USER/codex-work/work_v15/PHASE16/REVIEW_NOTES.md').read_bytes()).hexdigest()),
        '/home/REDACTED_USER/codex-work/work_v15/PHASE16/gsp_scan.json': dict(
            bytes=Path('/home/REDACTED_USER/codex-work/work_v15/PHASE16/gsp_scan.json').stat().st_size,
            sha256=hashlib.sha256(Path('/home/REDACTED_USER/codex-work/work_v15/PHASE16/gsp_scan.json').read_bytes()).hexdigest()),
    }, indent=2, ensure_ascii=False) + '\n')
    log(f"WROTE {OUT_DIR/'gsp_callback_target_report.json'} {OUT_DIR/'run.log'} {OUT_DIR/'input_hashes.json'}")


if __name__ == '__main__':
    main()
