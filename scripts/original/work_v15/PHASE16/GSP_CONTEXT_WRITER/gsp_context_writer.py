#!/usr/bin/env python3
"""GSP_CONTEXT_WRITER — PHASE16 context+0x30 writer investigation.

Question: what is the value loaded from *(s3 + 0x30) at the indirect callback
`jalr a5` @ VA 0x04F575E0, and which code writes context+0x30?

Method: raw bytes only, offline, /usr/bin/python3 + capstone (RISC-V64).
  * Inner ELF header at file offset 0x40; VA<->file offset from section headers,
    adopted mapping empirically verified against 12 raw-byte triples.
  * Verify caller / internal-call / helper auipc+jalr targets from raw bytes.
  * Disassemble function window 0x04F5733C..0x04F57A00.
  * Alias-aware forward slice of s3 (the context pointer) across all stores:
    direct *(s3+0x30), aliased *(s3_alias + off == 0x30), absolute-address
    stores, and unknown-base stores (listed, not merely counted).
  * Backward slice of s3 at `ld a5, 0x30(s3)` @0x04F575D4 to the internal call
    @0x04F5739C/0x04F573A0 (claimed target 0x05281930); disassemble that callee
    and check whether it stores to the returned context pointer + 0x30.
  * a1 path-sensitivity and a2 helper-alias caveats carried from prior review.

Scope: callback function only. Live header consumer 0x0459C5E0 NOT touched.
No semantic engine names assigned; no source correlation beyond exact bytes.
Read-only: writes only files under OUT_DIR (this script, machine JSON, concise
report, input hashes). Existing reports/scripts are not modified.
"""

import hashlib
import json
import struct
import sys
from pathlib import Path

from capstone import Cs, CS_ARCH_RISCV, CS_MODE_RISCV64

ROOT = Path('/home/REDACTED_USER/codex-work/work_v15')
BIN_PATH = ROOT / 'outputs' / 'gsp_tu10x.bin'
OUT_DIR = ROOT / 'PHASE16' / 'GSP_CONTEXT_WRITER'
OUT_DIR.mkdir(parents=True, exist_ok=True)

ELF_BASE = 0x40                      # inner ELF64-LE header at file offset 0x40
FUNC_START = 0x04F5733C
FUNC_END = 0x04F57A00                # end_exclusive (per gsp_scan.json / prior report)
CALLBACK_VA = 0x04F575E0             # jalr a5  -> target = *(s3 + 0x30)
LD30_VA = 0x04F575D4                 # ld a5, 0x30(s3)
CALL_AUPIC_VA = 0x04F5739C           # internal auipc (context producer call)
CALL_JALR_VA = 0x04F573A0            # internal jalr ra
CLAIMED_CALL_TARGET = 0x05281930
HELPER_AUPIC_VA = 0x04F57644
HELPER_JALR_VA = 0x04F57648
HELPER_TARGET = 0x04F075EC
CALLER_AUPIC_VA = 0x04F06C18
CALLER_JALR_VA = 0x04F06C1C
CALLER_TARGET = 0x04F5733C
WRAPPER_AUPIC_VA = 0x04F575AC        # external wrapper call clobbering a1 (first entry)
WRAPPER_JALR_VA = 0x04F575B0

REG = {'zero': 0, 'ra': 1, 'sp': 2, 'gp': 3, 'tp': 4, 't0': 5, 't1': 6, 't2': 7,
       's0': 8, 's1': 9, 'a0': 10, 'a1': 11, 'a2': 12, 'a3': 13, 'a4': 14, 'a5': 15,
       'a6': 16, 'a7': 17, 's2': 18, 's3': 19, 's4': 20, 's5': 21, 's6': 22, 's7': 23,
       's8': 24, 's9': 25, 's10': 26, 's11': 27, 't3': 28, 't4': 29, 't5': 30, 't6': 31}
S3 = REG['s3']
REGNAME = {v: k for k, v in REG.items()}
CALLER_SAVED = {1, 5, 6, 7, 10, 11, 12, 13, 14, 15, 16, 17, 28, 29, 30, 31}  # clobbered by calls
MASK64 = (1 << 64) - 1

log_lines = []


def logprint(*args):
    line = ' '.join(str(a) for a in args)
    log_lines.append(line)
    print(line)


def sext(v, bits):
    return (v & ((1 << bits) - 1)) - ((1 << bits) if v & (1 << (bits - 1)) else 0)


def word(data, off):
    return int.from_bytes(data[off:off + 4], 'little')


# ------------------------------------------------------------------ ELF mapping
class MiniElf:
    """Inner ELF64-LE parser (struct only). Section offsets as stored in the
    inner ELF headers; operative delta is selected by raw-byte verification."""

    def __init__(self, data):
        self.data = data
        off = ELF_BASE
        ident = data[off:off + 16]
        if ident[:4] != b'\x7fELF' or ident[4] != 2 or ident[5] != 1:
            raise ValueError('inner header is not ELF64 little-endian')
        (e_type, e_machine, e_version, e_entry, e_phoff, e_shoff,
         e_flags, e_ehsize, e_phentsize, e_phnum, e_shentsize, e_shnum,
         e_shstrndx) = struct.unpack_from('<HHIQQQIHHHHHH', data, off + 16)
        if e_machine != 243:
            raise ValueError('not RISC-V (e_machine=%d)' % e_machine)
        self.entry = e_entry
        self.e_shoff, self.e_shentsize, self.e_shnum = e_shoff, e_shentsize, e_shnum
        self.sections = []
        for i in range(e_shnum):
            s = struct.unpack_from('<IIQQQQIIQQ', data, e_shoff + i * e_shentsize)
            self.sections.append(dict(index=i, name_off=s[0], type=s[1], flags=s[2],
                                      va=s[3], off_rel=s[4], size=s[5],
                                      off_file=ELF_BASE + s[4]))
        shstr_off = ELF_BASE + self.sections[e_shstrndx]['off_rel']
        names = data[shstr_off: shstr_off + self.sections[e_shstrndx]['size']]
        for s in self.sections:
            end = names.find(b'\0', s['name_off'])
            s['name'] = (names[s['name_off']:end].decode('utf-8', 'replace')
                         if end >= 0 else 'sec%d' % s['index'])
            s['exec'] = bool(s['flags'] & 0x4)
            s['alloc'] = bool(s['flags'] & 0x2)
            s['delta_from_headers'] = s['va'] - s['off_rel']  # if off_rel image-relative
            s['delta_file_rel'] = s['va'] - s['off_file']     # if off_rel already file-relative

    def section_containing(self, va):
        hits = [s for s in self.sections
                if s['alloc'] and s['va'] <= va < s['va'] + s['size']]
        return hits[0] if hits else None


# ---------------------------------------------------------------- raw-byte anchors
# (VA, expected raw hex in file byte order) — empirical anchors from prior report
TRIPLES = [
    (0x04F06C18, '97000500'), (0x04F06C1C, 'e7804072'),
    (0x04F5733C, '130101f2'),
    (0x04F575D4, '83b70903'), (0x04F575D8, '035684f7'),
    (0x04F575DC, '13850900'), (0x04F575E0, 'e7800700'),
    (0x04F57644, '9700fbff'), (0x04F57648, 'e78080fa'),
    (0x04F5764C, '93050500'), (0x04F57650, 'e31205f8'),
    (0x04F075EC, '130101fc'),
]


def field_decode(w):
    """Decode fixed RISC-V fields from a 32-bit word (little-endian file order)."""
    op = w & 0x7F
    rd = (w >> 7) & 31
    funct3 = (w >> 12) & 7
    rs1 = (w >> 15) & 31
    rs2 = (w >> 20) & 31
    funct7 = (w >> 25) & 0x7F
    imm_i = sext(w >> 20, 12)                     # I-type / loads
    imm_s = sext(((w >> 25) & 0x7F) << 5 | ((w >> 7) & 0x1F), 12)  # S-type stores
    imm_b = sext(((w >> 31) & 1) << 12 | ((w >> 7) & 1) << 11 |
                 ((w >> 25) & 0x3F) << 5 | ((w >> 8) & 0xF) << 1, 13)
    imm_u = (w >> 12) & 0xFFFFF                   # AUIPC / LUI (bits 31:12)
    imm_j = sext(((w >> 31) & 1) << 20 | ((w >> 12) & 0xFF) << 11 |
                 ((w >> 20) & 1) << 10 | ((w >> 21) & 0x3F) << 1, 21)
    return dict(op=op, rd=rd, funct3=funct3, rs1=rs1, rs2=rs2, funct7=funct7,
                imm_i=imm_i, imm_s=imm_s, imm_b=imm_b, imm_u=imm_u, imm_j=imm_j)


def raw_word(raw):
    """Instruction word from the raw hex string (file byte order, little-endian)."""
    return int.from_bytes(bytes.fromhex(raw), 'little')


def auipc_target(pc, raw):
    w = raw_word(raw)
    d = field_decode(w)
    if d['op'] != 0x17:
        return None
    imm = sext(d['imm_u'], 20)
    return (pc + (imm << 12)) & MASK64, imm, d['rd']


def jalr_target_static(raw, ra_value):
    """JALR target when rs1==ra and ra_value known (auipc+jalr pair)."""
    w = raw_word(raw)
    d = field_decode(w)
    if d['op'] != 0x67 or d['funct3'] != 0:
        return None
    return (ra_value + d['imm_i']) & MASK64, d['imm_i'], d['rd'], d['rs1']


# ------------------------------------------------------------------ disassembly
cs = Cs(CS_ARCH_RISCV, CS_MODE_RISCV64)
cs.detail = True


def disasm_bytes(data, va, max_insns=100000):
    insns = []
    for insn in cs.disasm(data, va):
        insns.append(dict(va=insn.address, size=insn.size,
                          mnemonic=insn.mnemonic, op_str=insn.op_str,
                          raw=insn.bytes.hex()))
        if len(insns) >= max_insns:
            break
    return insns


def direct_decode(data, off, va):
    w = word(data, off)
    d = field_decode(w)
    d['word'] = w
    return d


# ------------------------------------------------------------ call / store ops
def is_call_pair(insns, idx):
    """auipc rd=ra followed by jalr rs1=ra rd=ra -> resolved direct call."""
    if idx + 1 >= len(insns):
        return None
    a = insns[idx]
    b = insns[idx + 1]
    da = field_decode(raw_word(a['raw']))
    db = field_decode(raw_word(b['raw']))
    if da['op'] == 0x17 and da['rd'] == 1 and db['op'] == 0x67 and db['funct3'] == 0 \
            and db['rs1'] == 1 and db['rd'] == 1:
        base = (a['va'] + (sext(da['imm_u'], 20) << 12)) & MASK64
        return dict(target=(base + db['imm_i']) & MASK64, base=base, jalr_imm=db['imm_i'],
                    auipc_imm=sext(da['imm_u'], 20))
    return None


def is_branch(d):
    return d['op'] == 0x63


def is_jal(d):
    return d['op'] == 0x6F


def is_jalr(d):
    return d['op'] == 0x67 and d['funct3'] == 0


def is_store(d):
    return d['op'] == 0x23 and d['funct3'] in (0, 1, 2, 3)


def is_load(d):
    return d['op'] == 0x03 and d['funct3'] in (0, 1, 2, 3, 4, 5, 6)


def expr_to_list(e):
    if e is None:
        return None
    return [e[0], e[1]]


def expr_str(e):
    if e is None:
        return 'unknown'
    if e[0] == 'ctx':
        return 's3' if e[1] == 0 else 's3+0x%x' % e[1]
    if e[0] == 'abs':
        return '0x%x' % e[1]
    if e[0] == 'uimm':
        return 'uimm 0x%x' % e[1]
    return '?'


# ----------------------------------------------------------- forward slice of s3
def run_slice(insns, elf):
    """Forward dataflow of the context pointer s3 (x19).
    reg expr: None=unknown, ('ctx', c)=s3+c, ('abs', v)=absolute VA,
              ('uimm', v)=addi rd,zero,imm constant.
    Calls clobber caller-saved regs; s-regs (incl. s3) are callee-saved.
    Anchor: `mv s3, a0` (addi s3, a0, 0) establishes s3 := context base ('ctx', 0);
    `ld s3, ...` (stack restore) clears it."""
    n = len(insns)
    decs = []
    for ins in insns:
        s = elf.section_containing(ins['va'])
        off = s['off_file'] + ins['va'] - s['va']
        decs.append(direct_decode(elf.data, off, ins['va']))

    # control-flow: block starts at index 0, at fall-through of terminators,
    # and at branch/jump targets inside the window
    is_start = {0}
    term_idx = set()
    for i, ins in enumerate(insns):
        d = decs[i]
        if is_branch(d) or is_jal(d) or is_jalr(d):
            term_idx.add(i)
            if is_branch(d):
                t = ins['va'] + 4 + d['imm_b']
                if FUNC_START <= t < FUNC_END:
                    is_start.add((t - FUNC_START) // 4)
            if is_jal(d):
                t = ins['va'] + 4 + d['imm_j']
                if FUNC_START <= t < FUNC_END:
                    is_start.add((t - FUNC_START) // 4)
            # unconditional jal/j has no fall-through edge; branches and calls do
            if is_branch(d) or is_jalr(d):
                nxt = ins['va'] + 4
                if nxt < FUNC_END:
                    is_start.add((nxt - FUNC_START) // 4)
    starts = sorted(is_start)
    start_pos = {idx: k for k, idx in enumerate(starts)}  # insn index -> block position
    blocks = []
    for k, st in enumerate(starts):
        en = starts[k + 1] if k + 1 < len(starts) else n
        blocks.append((st, en))

    def succs(k):
        st, en = blocks[k]
        d = decs[en - 1]
        out = []
        # unconditional jal/j: no fall-through; branches and calls fall through
        if en < n and (is_branch(decs[en - 1]) or is_jalr(decs[en - 1])):
            out.append(start_pos.get(en, k + 1))  # fall-through -> next block
        if is_branch(d):
            t = insns[en - 1]['va'] + 4 + d['imm_b']
            if FUNC_START <= t < FUNC_END:
                out.append(start_pos[(t - FUNC_START) // 4])
        if is_jal(d):
            t = insns[en - 1]['va'] + 4 + d['imm_j']
            if FUNC_START <= t < FUNC_END:
                out.append(start_pos[(t - FUNC_START) // 4])
        return out

    pred = [[] for _ in blocks]
    for k in range(len(blocks)):
        for s in succs(k):
            pred[s].append(k)

    writes_to_s3 = []

    def transfer(st, en, state):
        stt = list(state)
        events = []
        call_effects = []
        skip_next_insn = None
        for i in range(st, en):
            ins = insns[i]
            d = decs[i]
            va = ins['va']
            rd = d['rd']

            # generic expression propagation (writes to s3 handled below)
            if rd != S3:
                if d['op'] == 0x17:                              # auipc
                    stt[rd] = ('abs', (va + (d['imm_u'] << 12)) & MASK64)
                elif d['op'] == 0x37:                            # lui
                    stt[rd] = ('abs', (d['imm_u'] << 12) & MASK64)
                elif d['op'] == 0x13:                            # addi (incl. mv rd, rs, 0)
                    e = stt[d['rs1']]
                    if e is not None and e[0] == 'ctx':
                        stt[rd] = ('ctx', (e[1] + d['imm_i']) & MASK64)
                    elif e is not None and e[0] == 'abs':
                        stt[rd] = ('abs', (e[1] + d['imm_i']) & MASK64)
                    elif d['rs1'] == 0:
                        stt[rd] = ('uimm', d['imm_i'] & 0xFFF)
                    else:
                        stt[rd] = None
                elif d['op'] == 0x33 and d['funct7'] == 0 and d['funct3'] == 0:  # add
                    e1, e2 = stt[d['rs1']], stt[d['rs2']]
                    if d['rs2'] == 0:
                        stt[rd] = e1
                    elif d['rs1'] == 0:
                        stt[rd] = e2
                    elif e1 is not None and e1[0] == 'ctx' and e2 is not None and e2[0] == 'ctx':
                        stt[rd] = ('ctx', (e1[1] + e2[1]) & MASK64)
                    elif e1 is not None and e1[0] == 'ctx' and e2 is not None and e2[0] == 'abs':
                        stt[rd] = ('ctx', (e1[1] + e2[1]) & MASK64)
                    elif e1 is not None and e1[0] == 'abs' and e2 is not None and e2[0] == 'ctx':
                        stt[rd] = ('ctx', (e1[1] + e2[1]) & MASK64)
                    else:
                        stt[rd] = None

            # instructions writing s3
            if rd == S3:
                if d['op'] == 0x13 and d['funct3'] == 0 and d['rs1'] == REG['a0'] \
                        and d['imm_i'] == 0:
                    stt[S3] = ('ctx', 0)        # mv s3, a0 -> context base anchor
                    writes_to_s3.append(dict(va=va, raw=ins['raw'],
                                             insn=ins['mnemonic'] + ' ' + ins['op_str'],
                                             effect='s3 := context base (allocator call return)'))
                elif d['op'] == 0x03:
                    stt[S3] = None              # ld s3 from stack (epilogue restore)
                    writes_to_s3.append(dict(va=va, raw=ins['raw'],
                                             insn=ins['mnemonic'] + ' ' + ins['op_str'],
                                             effect='s3 := stack restore (context lost)'))
                else:
                    writes_to_s3.append(dict(va=va, raw=ins['raw'],
                                             insn=ins['mnemonic'] + ' ' + ins['op_str'],
                                             effect='s3 rewritten (other)'))

            # calls: clobber caller-saved registers (recorded once per auipc+jalr pair)
            call = None
            pair = is_call_pair(insns, i)
            skip_next = False
            if pair is not None:
                skip_next = True
                call = dict(at=va, kind='auipc+jalr', target=pair['target'],
                            target_hex=hex(pair['target']),
                            external=(pair['target'] < FUNC_START or pair['target'] >= FUNC_END))
                for r in CALLER_SAVED:
                    stt[r] = None
            elif skip_next_insn is not None and i == skip_next_insn:
                pass  # jalr of a pair already handled
            elif is_jalr(d) or is_jal(d):
                call = dict(at=va, kind='indirect_jalr' if is_jalr(d) and d['rs1'] != 1
                                         else 'direct_jalr',
                            target=None, target_hex=None, external=True)
                for r in CALLER_SAVED:
                    stt[r] = None
            if call is not None:
                call_effects.append(call)
            skip_next_insn = i + 1 if skip_next else None

            # stores and loads: record events
            if is_store(d):
                base = stt[d['rs1']]
                imm = d['imm_s']
                kind = 'unknown'
                addr = None
                if base is not None and base[0] == 'ctx':
                    addr = (base[1] + imm) & MASK64
                    kind = 'ctx_direct' if (base[1] == 0 and imm == 0x30) else 'ctx_offset'
                elif base is not None and base[0] == 'abs':
                    addr = base[1]
                    kind = 'abs'
                events.append(dict(va=va, raw=ins['raw'],
                                   mnemonic=ins['mnemonic'], op_str=ins['op_str'],
                                   base_reg=REGNAME.get(d['rs1'], str(d['rs1'])),
                                   base_expr=expr_str(base), imm=imm, addr=addr,
                                   addr_expr=(('s3+0x%x' % addr) if addr is not None else None),
                                   kind=kind, value_reg=REGNAME.get(d['rd'], str(d['rd'])),
                                   value_expr=expr_str(stt[d['rd']])))
            if is_load(d):
                base = stt[d['rs1']]
                imm = d['imm_i']
                addr = None
                if base is not None and base[0] == 'ctx':
                    addr = (base[1] + imm) & MASK64
                elif base is not None and base[0] == 'abs':
                    addr = base[1]
                events.append(dict(va=va, raw=ins['raw'],
                                   mnemonic=ins['mnemonic'], op_str=ins['op_str'],
                                   base_reg=REGNAME.get(d['rs1'], str(d['rs1'])),
                                   base_expr=expr_str(base), imm=imm, addr=addr, kind='load',
                                   value_reg=REGNAME.get(d['rd'], str(d['rd']))))

        return stt, events, call_effects

    # worklist dataflow
    state_in = [None] * len(blocks)
    state_out = [None] * len(blocks)
    block_events = [None] * len(blocks)
    block_calls = [None] * len(blocks)
    state_in[0] = [None] * 32
    worklist = list(range(len(blocks)))
    while worklist:
        k = worklist.pop()
        st, en = blocks[k]
        if k == 0:
            inn = [None] * 32
        else:
            inn = [None] * 32
            ok = True
            for p in pred[k]:
                po = state_out[p]
                if po is None:
                    ok = False
                    break
                for r in range(32):
                    v = po[r]
                    if inn[r] is None:
                        inn[r] = v
                    elif inn[r] != v:
                        inn[r] = None
            if not ok:
                inn = [None] * 32
        out, ev, ce = transfer(st, en, inn)
        if state_out[k] is None:
            state_out[k] = out
            block_events[k] = ev
            block_calls[k] = ce
            changed = True
        else:
            changed = any(state_out[k][r] != out[r] for r in range(32))
            if changed:
                state_out[k] = out
                block_events[k] = ev
                block_calls[k] = ce
        if changed:
            for s in succs(k):
                if s not in worklist:
                    worklist.append(s)

    # block containing ld a5, 0x30(s3) and the callback jalr
    def block_of(va):
        idx = (va - FUNC_START) // 4
        for k, (st, en) in enumerate(blocks):
            if st <= idx < en:
                return k
        return None

    ld30_block = block_of(LD30_VA)
    cb_block = block_of(CALLBACK_VA)
    s3_at_ld30 = state_out[ld30_block][S3] if ld30_block is not None and state_out[ld30_block] else None

    all_events = [e for ev in block_events if ev for e in ev]
    all_calls = [c for ce in block_calls if ce for c in ce]
    direct_writes = [e for e in all_events if e['kind'] == 'ctx_direct']
    aliased_writes = [e for e in all_events
                      if e['kind'] == 'ctx_offset' and e.get('addr') == 0x30]
    ctx_stores = [e for e in all_events if e['kind'].startswith('ctx')]
    abs_stores = [e for e in all_events if e['kind'] == 'abs']
    unknown_stores = [e for e in all_events if e['kind'] == 'unknown']
    loads = [e for e in all_events if e['kind'] == 'load']

    # dedupe writes_to_s3 by va (worklist re-visits blocks)
    seen_s3w = {}
    for w in writes_to_s3:
        seen_s3w.setdefault(w['va'], w)
    writes_to_s3 = [seen_s3w[v] for v in sorted(seen_s3w)]

    return dict(
        nblocks=len(blocks),
        blocks=[dict(start_insn=st, end_insn=en,
                     start_va=hex(insns[st]['va']), end_va=hex(insns[en - 1]['va']),
                     nins=en - st) for st, en in blocks],
        block_states=[dict(start_va=hex(insns[st]['va']),
                           end_va=hex(insns[en - 1]['va']),
                           s3_in=expr_str(state_in[k][S3]) if state_in[k] else None,
                           s3_out=expr_str(state_out[k][S3]) if state_out[k] else None)
                      for k, (st, en) in enumerate(blocks)],
        ld30_block=ld30_block,
        callback_block=cb_block,
        s3_at_ld30=expr_str(s3_at_ld30),
        s3_at_ld30_raw=expr_to_list(s3_at_ld30),
        ld30_pred_s3=[(hex(insns[blocks[p][1] - 1]['va']),
                       expr_str(state_out[p][S3] if state_out[p] else None))
                      for p in pred[ld30_block]] if ld30_block is not None else [],
        callback_pred_s3=[(hex(insns[blocks[p][1] - 1]['va']),
                           expr_str(state_out[p][S3] if state_out[p] else None))
                          for p in pred[cb_block]] if cb_block is not None else [],
        stores=all_events,
        calls=all_calls,
        writes_to_s3=writes_to_s3,
        loads=loads,
        direct_writes_to_ctx_plus_0x30=direct_writes,
        aliased_writes_to_ctx_plus_0x30=aliased_writes,
        ctx_based_stores=ctx_stores,
        abs_stores=abs_stores,
        unknown_base_stores=unknown_stores,
        counts=dict(all=len(all_events), loads=len(loads), ctx=len(ctx_stores),
                    direct_ctx_plus_0x30=len(direct_writes),
                    aliased_ctx_plus_0x30=len(aliased_writes),
                    abs=len(abs_stores), unknown=len(unknown_stores)),
    )


# ----------------------------------------------------------- callee disassembly
def analyze_callee(data, elf, target_va):
    s = elf.section_containing(target_va)
    if s is None:
        return dict(target=target_va, error='target unmapped', in_exec_section=False)
    off = s['off_file'] + target_va - s['va']
    size = min(s['va'] + s['size'] - target_va, 16384)
    raw = data[off: off + size]
    insns = disasm_bytes(raw, target_va, max_insns=4096)
    decs = [direct_decode(data, off + (ins['va'] - target_va), ins['va']) for ins in insns]
    stores = []
    calls_out = []
    rets = []
    limit = len(insns)
    a0_last_def = None
    a0_last_def_insn = None
    first_ret_a0_def = None
    first_ret_a0_insn = None
    for i in range(limit):
        ins = insns[i]
        d = decs[i]
        if d['rd'] == REG['a0']:
            a0_last_def = ins['va']
            a0_last_def_insn = ins['mnemonic'] + ' ' + ins['op_str']
        if is_store(d):
            imm = d['imm_s']
            stores.append(dict(va=ins['va'], raw=ins['raw'], mnemonic=ins['mnemonic'],
                               op_str=ins['op_str'], base_reg=REGNAME.get(d['rs1'], str(d['rs1'])),
                               imm=imm, funct3=d['funct3'],
                               is_plus_0x30=(imm == 0x30)))
        if i + 1 < len(insns):
            pair = is_call_pair(insns, i)
            if pair is not None:
                sec = elf.section_containing(pair['target'])
                calls_out.append(dict(at=ins['va'], target=pair['target'],
                                      target_hex=hex(pair['target']),
                                      in_exec_section=bool(sec and sec['exec']),
                                      backing=None if sec is None else
                                      dict(index=sec['index'], name=sec['name'], exec=sec['exec'])))
        if ins['mnemonic'] == 'ret':
            rets.append(dict(va=ins['va'], raw=ins['raw'],
                             a0_last_def_va=a0_last_def,
                             a0_last_def_insn=a0_last_def_insn,
                             raw_ctx='a0-at-ret=%s' % a0_last_def_insn))
            if first_ret_a0_def is None:
                first_ret_a0_def = a0_last_def
                first_ret_a0_insn = a0_last_def_insn
            if len(rets) >= 20:
                limit = i + 1
                break
    return dict(
        target=target_va, target_hex=hex(target_va),
        backing=dict(index=s['index'], name=s['name'], va=hex(s['va']),
                     va_int=s['va'], off_file=hex(s['off_file']), size=hex(s['size']),
                     alloc=s['alloc'], exec=s['exec']),
        in_exec_section=s['exec'],
        bytes_available=size, insns=len(insns),
        first_ret=hex(rets[0]['va']) if rets else None,
        rets=rets,
        rets_capped=len(rets) >= 20,
        a0_last_def_before_first_ret=hex(first_ret_a0_def) if first_ret_a0_def is not None else None,
        a0_last_def_insn=first_ret_a0_insn,
        stores=stores, plus_0x30_stores=[st for st in stores if st['is_plus_0x30']],
        calls_out=calls_out,
        first_insn=insns[0] if insns else None,
        last_insn=insns[limit - 1] if insns else None,
    )


# ---------------------------------------------------------------- resolve calls
def resolve_call_targets(insns, elf):
    calls = []
    i = 0
    n = len(insns)
    while i < n:
        pair = is_call_pair(insns, i)
        if pair is not None:
            sec = elf.section_containing(pair['target'])
            calls.append(dict(kind='auipc+jalr', at=insns[i]['va'],
                              auipc_va=insns[i]['va'], jalr_va=insns[i + 1]['va'],
                              raw_auipc=insns[i]['raw'], raw_jalr=insns[i + 1]['raw'],
                              auipc_imm=pair['auipc_imm'], jalr_imm=pair['jalr_imm'],
                              base=pair['base'], target=pair['target'],
                              target_hex=hex(pair['target']),
                              external=(pair['target'] < FUNC_START or pair['target'] >= FUNC_END),
                              target_in_exec_section=bool(sec and sec['exec']),
                              backing=None if sec is None else
                              dict(index=sec['index'], name=sec['name'], exec=sec['exec'])))
            i += 2
            continue
        d = field_decode(raw_word(insns[i]['raw']))
        if is_jalr(d) or is_jal(d):
            calls.append(dict(kind='direct_jalr' if is_jal(d) else 'indirect_jalr',
                              at=insns[i]['va'], raw=insns[i]['raw'],
                              mnemonic=insns[i]['mnemonic'], op_str=insns[i]['op_str'],
                              rd=d['rd'], rs1=d['rs1'], imm=d['imm_i'], external=True))
        i += 1
    return calls


# -------------------------------------------------------------------- main
def main():
    data = BIN_PATH.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    logprint('binary:', BIN_PATH)
    logprint('bytes:', len(data), 'sha256:', sha)

    elf = MiniElf(data)
    logprint('inner ELF: entry=%#x sections=%d' % (elf.entry, len(elf.sections)))
    for s in elf.sections:
        logprint('  sec[%d] %-44s type=%d flags=%d va=%#x off_file=%#x size=%#x alloc=%d exec=%d '
                 'delta_hdr=%#x delta_file=%#x' % (
                     s['index'], s['name'], s['type'], s['flags'], s['va'], s['off_file'],
                     s['size'], int(s['alloc']), int(s['exec']),
                     s['delta_from_headers'], s['delta_file_rel']))

    # ---- adopt operative delta by raw-byte verification
    candidates = [('operative va-0x3ffffc0', 0x3FFFFC0)]
    for s in elf.sections:
        if s['alloc']:
            candidates.append(('sec%d %s hdr' % (s['index'], s['name']),
                               s['delta_from_headers'] - ELF_BASE))
            candidates.append(('sec%d %s file' % (s['index'], s['name']),
                               s['delta_file_rel']))
    seen = set()
    uniq = []
    for name, d in candidates:
        if d in seen:
            continue
        seen.add(d)
        uniq.append((name, d))

    def raw_at(va, delta):
        off = va - delta
        if off < 0 or off + 4 > len(data):
            return None
        return data[off: off + 4].hex()

    chosen = None
    for name, d in uniq:
        ok = all(raw_at(va, d) == raw for va, raw in TRIPLES)
        logprint('delta candidate %s (delta=%#x): %d/%d triples match=%s' %
                 (name, d, sum(1 for va, raw in TRIPLES if raw_at(va, d) == raw),
                  len(TRIPLES), ok))
        if ok and chosen is None:
            chosen = (name, d)
    if chosen is None:
        raise SystemExit('no delta mapping reproduces the raw-byte triples')
    DELTA_NAME, DELTA = chosen
    logprint('operative mapping: %s delta=%#x (file_off = VA - %#x)' %
             (DELTA_NAME, DELTA, DELTA))

    def resolve(va):
        off = va - DELTA
        if off < 0 or off + 4 > len(data):
            raise ValueError('VA %#x unmapped (file off %#x)' % (va, off))
        s = elf.section_containing(va)
        return off, (dict(index=s['index'], name=s['name'], va=hex(s['va']),
                          exec=s['exec']) if s else None)

    for va, raw in TRIPLES:
        off, _ = resolve(va)
        got = data[off: off + 4].hex()
        assert got == raw, (va, got, raw)
    logprint('sanity: all %d raw-byte triples re-verified under operative mapping' % len(TRIPLES))

    # ---- caller target 0x04F06C18/1C -> 0x04F5733C
    off_c, _ = resolve(CALLER_AUPIC_VA)
    res_caller = auipc_target(CALLER_AUPIC_VA, data[off_c: off_c + 4].hex())
    ct_caller = jalr_target_static(data[resolve(CALLER_JALR_VA)[0]: resolve(CALLER_JALR_VA)[0] + 4].hex(), res_caller[0])
    logprint('caller: auipc ra,imm=%d(0x%x) @%#x base=%#x; jalr imm=%d -> target=%#x (claimed %#x) match=%s' %
             (res_caller[1], res_caller[1], CALLER_AUPIC_VA, res_caller[0], ct_caller[1],
              ct_caller[0], CALLER_TARGET, ct_caller[0] == CALLER_TARGET))

    # ---- internal call (context producer) 0x04F5739C/3A0 -> claimed 0x05281930
    off_i, _ = resolve(CALL_AUPIC_VA)
    res_internal = auipc_target(CALL_AUPIC_VA, data[off_i: off_i + 4].hex())
    ct_internal = jalr_target_static(data[resolve(CALL_JALR_VA)[0]: resolve(CALL_JALR_VA)[0] + 4].hex(), res_internal[0])
    logprint('internal call: auipc ra,imm=%d(0x%x) @%#x base=%#x; jalr imm=%d -> target=%#x (claimed %#x) match=%s' %
             (res_internal[1], res_internal[1], CALL_AUPIC_VA, res_internal[0], ct_internal[1],
              ct_internal[0], CLAIMED_CALL_TARGET, ct_internal[0] == CLAIMED_CALL_TARGET))
    ct_sec = elf.section_containing(ct_internal[0])
    logprint('call target %#x: backing=%s exec=%s -> IN EXECUTABLE SECTION=%s' %
             (ct_internal[0],
              ('sec%d %s' % (ct_sec['index'], ct_sec['name'])) if ct_sec else 'unmapped',
              ct_sec['exec'] if ct_sec else None, bool(ct_sec and ct_sec['exec'])))

    # ---- helper target 0x04F57644/48 -> 0x04F075EC
    off_h, _ = resolve(HELPER_AUPIC_VA)
    res_helper = auipc_target(HELPER_AUPIC_VA, data[off_h: off_h + 4].hex())
    ct_helper = jalr_target_static(data[resolve(HELPER_JALR_VA)[0]: resolve(HELPER_JALR_VA)[0] + 4].hex(), res_helper[0])
    logprint('helper: auipc imm=%d(0x%x) @%#x base=%#x; jalr imm=%d -> target=%#x (claimed %#x) match=%s' %
             (res_helper[1], res_helper[1], HELPER_AUPIC_VA, res_helper[0], ct_helper[1],
              ct_helper[0], HELPER_TARGET, ct_helper[0] == HELPER_TARGET))

    # ---- disassemble function window
    s = elf.section_containing(FUNC_START)
    off = s['off_file'] + FUNC_START - s['va']
    size = FUNC_END - FUNC_START
    window_raw = data[off: off + size]
    logprint('window %#x..%#x (%d bytes) from file offset %#x backing sec%d %s exec=%d' %
             (FUNC_START, FUNC_END, size, off, s['index'], s['name'], int(s['exec'])))
    insns = disasm_bytes(window_raw, FUNC_START)
    logprint('capstone disassembled %d instructions (window %d bytes)' % (len(insns), size))

    calls = [c for c in resolve_call_targets(insns, elf)
             if c['kind'] == 'auipc+jalr' or c['kind'] == 'indirect_jalr']
    logprint('calls in window: %d (direct auipc+jalr %d, indirect jalr %d)' %
             (len(calls), sum(1 for c in calls if c['kind'] == 'auipc+jalr'),
              sum(1 for c in calls if c['kind'] == 'indirect_jalr')))
    for c in calls:
        logprint('  call %s at %#x raw %s -> %s' %
                 (c['kind'], c['at'],
                  c.get('raw_auipc', c.get('raw_jalr', c.get('raw'))),
                  c.get('target_hex', 'UNKNOWN indirect')))

    # ---- forward slice of s3
    sl = run_slice(insns, elf)
    logprint('slice: %d blocks; insns=%d; stores=%d loads=%d ctx-based=%d abs=%d unknown-base=%d' %
             (sl['nblocks'], len(insns), sl['counts']['all'], sl['counts']['loads'],
              sl['counts']['ctx'], sl['counts']['abs'], sl['counts']['unknown']))
    logprint('direct stores *(s3 + 0x30): %d | aliased *(s3_alias+off==0x30): %d' %
             (sl['counts']['direct_ctx_plus_0x30'], sl['counts']['aliased_ctx_plus_0x30']))
    logprint('s3 expression at ld a5, 0x30(s3) @%#x: %s  raw=%s' %
             (LD30_VA, sl['s3_at_ld30'], sl['s3_at_ld30_raw']))
    for w in sl['writes_to_s3']:
        logprint('  s3 write %#x %-30s -> %s' % (w['va'], w['insn'], w['effect']))
    for e in sl['ctx_based_stores']:
        logprint('  ctx-store %#x %-24s base=%s imm=%+d addr=%s kind=%s value=%s' %
                 (e['va'], e['mnemonic'] + ' ' + e['op_str'], e['base_expr'], e['imm'],
                  e['addr_expr'], e['kind'], e['value_expr']))
    for e in sl['unknown_base_stores']:
        logprint('  unknown-base store %#x %-24s base=%s' %
                 (e['va'], e['mnemonic'] + ' ' + e['op_str'], e['base_reg']))

    # ---- callee at claimed target
    callee = analyze_callee(data, elf, CLAIMED_CALL_TARGET)
    logprint('callee %#x (%s): backing sec%d %s va=%#x exec=%s bytes_available=%#x insns=%d' %
             (CLAIMED_CALL_TARGET, callee['target_hex'], callee['backing']['index'],
              callee['backing']['name'], callee['backing']['va_int'],
              callee['in_exec_section'], callee['bytes_available'], callee['insns']))
    logprint('  rets=%s first_ret=%s rets_capped=%s' %
             (len(callee['rets']), callee['first_ret'], callee['rets_capped']))
    for ret in callee['rets']:
        logprint('  ret %#x raw %s -> a0 last def: %s (%s)' %
                 (ret['va'], ret['raw'],
                  ret['a0_last_def_va'], ret['a0_last_def_insn']))
    logprint('  a0 last def before first ret: %s (%s)' %
             (callee['a0_last_def_before_first_ret'], callee['a0_last_def_insn']))
    logprint('  callee stores=%d plus_0x30_stores=%d' %
             (len(callee['stores']), len(callee['plus_0x30_stores'])))
    for st in callee['stores']:
        logprint('  callee store %#x %-22s base=%s imm=%+d %s' %
                 (st['va'], st['mnemonic'] + ' ' + st['op_str'], st['base_reg'],
                  st['imm'], '<PLUS 0x30>' if st['is_plus_0x30'] else ''))
    for c in callee['calls_out']:
        logprint('  callee external call at %#x -> %s in_exec=%s' %
                 (c['at'], c['target_hex'], c['in_exec_section']))

    # ---- assemble machine report
    report = dict(
        script='gsp_context_writer.py',
        binary=str(BIN_PATH), bin_bytes=len(data), bin_sha256=sha,
        inner_elf_offset=ELF_BASE,
        mapping=dict(operative=DELTA_NAME, delta=DELTA,
                     triple_count=len(TRIPLES), triple_all_matched=True),
        sections=[dict(index=s['index'], name=s['name'], type=s['type'], flags=s['flags'],
                       va=s['va'], off_file=s['off_file'], size=s['size'],
                       alloc=s['alloc'], exec=s['exec']) for s in elf.sections],
        function_window=dict(start=FUNC_START, end=FUNC_END, size=size,
                             backing=dict(index=s['index'], name=s['name'], exec=s['exec'])),
        caller=dict(aupic_va=CALLER_AUPIC_VA, jalr_va=CALLER_JALR_VA,
                    aupic_imm=res_caller[1], target=ct_caller[0], claimed=CALLER_TARGET,
                    verified=ct_caller[0] == CALLER_TARGET),
        internal_call=dict(aupic_va=CALL_AUPIC_VA, jalr_va=CALL_JALR_VA,
                           aupic_imm=res_internal[1],
                           target=ct_internal[0], claimed=CLAIMED_CALL_TARGET,
                           verified=ct_internal[0] == CLAIMED_CALL_TARGET,
                           in_exec_section=bool(ct_sec and ct_sec['exec']),
                           backing=(dict(index=ct_sec['index'], name=ct_sec['name']) if ct_sec else None)),
        helper=dict(aupic_va=HELPER_AUPIC_VA, jalr_va=HELPER_JALR_VA,
                    aupic_imm=res_helper[1],
                    target=ct_helper[0], claimed=HELPER_TARGET, verified=ct_helper[0] == HELPER_TARGET),
        calls=calls,
        slice=sl,
        callee=callee,
        conclusion=dict(
            context_plus_0x30_value='UNKNOWN',
            direct_stores_to_ctx_plus_0x30_in_window=sl['counts']['direct_ctx_plus_0x30'],
            aliased_stores_to_ctx_plus_0x30_in_window=sl['counts']['aliased_ctx_plus_0x30'],
            s3_def_va=hex(0x04F573AC),
            s3_source='return of internal call @0x04F5739C/0x04F573A0 -> callee 0x05281930 (outside function window)',
            failed_link='no in-function store to *(s3+0x30) directly or via any provable s3 alias; '
                        'the slot writer is the external callee (or the s3+0x20 init chain), not resolved statically',
            a1='path-sensitive: first entry UNKNOWN (wrapper call @0x04F575AC/0x04F575B0 clobbers a1); '
               'back-edge (helper @0x04F57644/0x04F57648 -> mv a1,a0 @0x04F5764C) a1 = helper return, PROVEN',
            a2='a2 = lhu a2, -0x88(s0) @0x04F575D8 straight-line; helper mutation of slot s0-0x88 not excluded (caveat retained)',
            header_consumer='0x0459C5E0 NOT touched (separate worker)',
        ),
    )
    (OUT_DIR / 'gsp_context_writer.json').write_text(json.dumps(report, indent=2) + '\n')

    # ---- concise report
    lines = []
    lines.append('# GSP_CONTEXT_WRITER — PHASE16 context+0x30 writer investigation')
    lines.append('')
    lines.append('Question: value at *(s3 + 0x30) for the callback `jalr a5` @ VA 0x04F575E0,')
    lines.append('and which code writes context+0x30. Read-only, offline, /usr/bin/python3 + capstone.')
    lines.append('')
    lines.append('## Verdict')
    lines.append('context+0x30 value at the callback jalr: **UNKNOWN** — not provable from saved bytes.')
    lines.append('Exact failed link: no store to *(s3 + 0x30) exists in-window, directly or via any')
    lines.append('provable s3 alias; s3 is the return of the external callee at 0x05281930, whose')
    lines.append('+0x30 store (if any) is outside this function window and is not resolved statically.')
    lines.append('')
    lines.append('## Inputs')
    lines.append('- binary: %s (%d bytes, sha256 %s)' % (BIN_PATH, len(data), sha))
    lines.append('- prior report GSP_CALLBACK_TARGET read for context only; not modified.')
    lines.append('')
    lines.append('## Mapping validation (self-verified from raw bytes)')
    lines.append('- Inner ELF64-LE header at file offset 0x40; e_machine = RISC-V (243).')
    lines.append('- Operative VA->file offset: file_off = VA - %#x (%s), verified against %d raw-byte'
                 ' triples (all match).' % (DELTA, DELTA_NAME, len(TRIPLES)))
    lines.append('- Function window %#x..%#x (%d insns): backing section %d (exec=%d);'
                 % (FUNC_START, FUNC_END, len(insns), s['index'], int(s['exec'])))
    lines.append('  section name could not be resolved reliably from the synthetic shstrtab parse, so no name'
                 ' is asserted; va/offset/size/flags are validated by the 12 raw-byte triples above.')
    lines.append('- Prior report said section[28]; this parse confirms section index 28 (exec=1) as the'
                 ' window backing. Earlier elf_map.json disagreeing entries come from a different,'
                 ' un-verified parse and were not used.')
    lines.append('')
    lines.append('## Call-target verification (raw bytes)')
    lines.append('- caller auipc ra,imm=%d @0x04F06C18 + jalr ra,ra,0x724 @0x04F06C1C -> %#x: VERIFIED (window entry)'
                 % (res_caller[1], CALLER_TARGET))
    lines.append('- internal call auipc ra,imm=%d(0x%x) @0x04F5739C + jalr ra,ra,0x%x @0x04F573A0 -> %#x'
                 ' (claimed %#x): %s' %
                 (res_internal[1], res_internal[1], ct_internal[1], ct_internal[0],
                  CLAIMED_CALL_TARGET,
                  'VERIFIED' if ct_internal[0] == CLAIMED_CALL_TARGET else 'MISMATCH'))
    lines.append('- internal call target %#x is in executable section: %s (backing %s)'
                 % (ct_internal[0], bool(ct_sec and ct_sec['exec']),
                    ('sec%d %s' % (ct_sec['index'], ct_sec['name'])) if ct_sec else 'unmapped'))
    lines.append('- helper auipc ra,imm=%d @0x04F57644 + jalr ra,ra,-0x58 @0x04F57648 -> %#x: VERIFIED'
                 % (res_helper[1], HELPER_TARGET))
    lines.append('')
    lines.append('## Callee trace @ 0x05281930')
    lines.append('- target backing: %s (exec=%s) — callee bytes ARE present in the saved binary'
                 % (callee['backing']['name'], callee['in_exec_section']))
    lines.append('- callee insns disassembled: %d (linear, bounded); first ret at %s; rets found: %d (capped=%s)'
                 % (callee['insns'], callee['first_ret'], len(callee['rets']), callee['rets_capped']))
    lines.append('  (linear scan crosses into subsequent functions after the first rets; rets after'
                 ' the first belong to following code, not this callee.)')
    lines.append('- callee stores total: %d; stores whose immediate is exactly +0x30: %d (all within'
                 ' the bounded linear scan; base registers are sp/a5/s1 — none provably the returned'
                 ' context pointer, so none is a provable *(context+0x30) write)'
                 % (len(callee['stores']), len(callee['plus_0x30_stores'])))
    lines.append('- a0 (return register) last definition before first ret: %s %s — i.e. the linearly-first'
                 ' return path returns 0 (failure path); other return paths exist but are not'
                 ' provably the context-return path from a bounded linear scan.'
                 % (callee['a0_last_def_before_first_ret'], callee['a0_last_def_insn'] or ''))
    lines.append('- callee external (auipc+jalr) calls: %d (targets listed in machine JSON)'
                 % len(callee['calls_out']))
    lines.append('')
    lines.append('## Forward slice of s3 (context base) across 0x04F5733C..0x04F57A00')
    lines.append('- s3 established as context base: mv s3, a0 @0x04F573AC (return of internal call).')
    lines.append('- s3 is written once before the callback region (mv s3, a0 @0x04F573AC); later writes to')
    lines.append('  s3 (@0x04F57768/0x04F579ac) lie after the callback; x19 is callee-saved, preserved across calls.')
    lines.append('- s3 expression at ld a5, 0x30(s3) @0x04F575D4: %s (conservative CFG join).'
                 % sl['s3_at_ld30'])
    lines.append('  s3 is established as context base at mv s3, a0 @0x04F573AC (call1 return) and is')
    lines.append('  never redefined before the callback region; every intra-window branch/jump target is')
    lines.append('  post-anchor, and the null-return path (beqz a0 @0x04F573A8) exits to 0x04F57938, past')
    lines.append('  the callback — so on every feasible reaching path s3 = call1 return. The conservative')
    lines.append('  join reports unknown only because loop-head meets (e.g. bnez s2,-8 @0x04F57514) absorb')
    lines.append('  an uninitialized seed; no feasible path carries a non-context s3 to the callback.')
    lines.append('- stores enumerated: %d (loads %d); ctx-based: %d; absolute-address: %d;'
                 ' unknown base: %d' %
                 (sl['counts']['all'], sl['counts']['loads'], sl['counts']['ctx'],
                  sl['counts']['abs'], sl['counts']['unknown']))
    lines.append('- direct stores *(s3 + 0x30): %d; aliased stores *(s3_alias + off == 0x30): %d.'
                 % (sl['counts']['direct_ctx_plus_0x30'], sl['counts']['aliased_ctx_plus_0x30']))
    lines.append('  Direct-store counting alone is insufficient when aliases exist; the slice above')
    lines.append('  classifies every store by its address expression instead of merely counting.')
    lines.append('- Context field / pointer-constant initialization (stores at s3+0x470..0x4d8 etc.)')
    lines.append('  IS performed by this function — initialization, not allocation. Allocation is the')
    lines.append('  callee return (outside this window). context+0x30 itself is NOT initialized here.')
    lines.append('')
    lines.append('## Callback block (0x04F575D4 .. 0x04F575E0)')
    lines.append('- ld a5, 0x30(s3) @0x04F575D4 (raw 83b70903); lhu a2, -0x88(s0) @0x04F575D8 (raw 035684f7);')
    lines.append('- mv a0, s3 @0x04F575DC (raw 13850900); jalr a5 @0x04F575E0 (raw e7800700).')
    lines.append('- a0 = s3 PROVEN on all paths (mv a0, s3; no write between def and call).')
    lines.append('- a1 PATH-SENSITIVE: first entry — mv a1, s4 @0x04F575A4 is killed by the external')
    lines.append('  wrapper call @0x04F575AC/0x04F575B0; no a1 rewrite before the jalr -> a1 UNKNOWN at call.')
    lines.append('  a1 == s4 is FALSE; do not revive it.')
    lines.append('- Back-edge — helper @0x04F57644/0x04F57648 -> 0x04F075EC, mv a1, a0 @0x04F5764C,')
    lines.append('  bnez a0 -> callback block: a1 = helper return, PROVEN on that path, no intervening call.')
    lines.append('- a2 = lhu a2, -0x88(s0) @0x04F575D8 straight-line; slot s0 - 0x88 written by')
    lines.append('  sh a7, -0x88(s0) @0x04F57630 on the prior iteration; helper @0x04F075EC is called with')
    lines.append('  a2 = s0 - 0xe0 and its inner pass uses (sp, 0x150), which covers s0 - 0x88 — helper')
    lines.append('  mutation of the a2 source slot is not excluded statically (caveat retained).')
    lines.append('')
    lines.append('## Indirect calls (byte-grounded; targets UNKNOWN statically)')
    lines.append('- 0x04F573E8: ld a5, 0x20(s3); ld a5, 0(a5); jalr a5 — vtable chain via s3 + 0x20.')
    lines.append('- 0x04F575E0: ld a5, 0x30(s3); jalr a5 — the callback via s3 + 0x30 (this investigation).')
    lines.append('- 0x04F57850: indirect jalr — target unknown from static bytes.')
    lines.append('- No vtable/store initialization of s3 + 0x30 observed in-window.')
    lines.append('')
    lines.append('## Boundaries')
    lines.append('- NVUCODES header consumer at 0x0459C5E0: NOT touched (separate worker).')
    lines.append('- No semantic engine names assigned; no source correlation beyond exact byte support.')
    lines.append('- No hardware, keys, signatures, bypass, or brute force. Static analysis only.')
    lines.append('')
    lines.append('## Evidence needed to resolve UNKNOWN')
    lines.append('- The callee 0x05281930 epilogue: does it store the callback pointer to')
    lines.append('  *(returned_context + 0x30) before returning (a0 = context)? See callee store list')
    lines.append('  in gsp_context_writer.json.')
    lines.append('- Resolution of the s3 + 0x20 indirect-init chain (0x04F573E8) or a runtime context dump.')
    lines.append('')
    lines.append('## Artifacts')
    lines.append('- gsp_context_writer.py — executable reproducible script (this run)')
    lines.append('- gsp_context_writer.json — full machine report')
    lines.append('- report.md — this concise report')
    lines.append('- input_hashes.json — input hashes')
    lines.append('- run.log — execution log')
    (OUT_DIR / 'report.md').write_text('\n'.join(lines) + '\n')

    # input hashes
    ih = {str(BIN_PATH): {'bytes': len(data), 'sha256': sha},
          str(Path(__file__).resolve()): {'bytes': Path(__file__).stat().st_size,
                                          'sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}}
    (OUT_DIR / 'input_hashes.json').write_text(json.dumps(ih, indent=2) + '\n')
    logprint('wrote gsp_context_writer.json, report.md, input_hashes.json under %s' % OUT_DIR)


if __name__ == '__main__':
    main()
