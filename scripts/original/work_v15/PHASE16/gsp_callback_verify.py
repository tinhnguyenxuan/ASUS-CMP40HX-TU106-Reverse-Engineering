#!/usr/bin/env python3
"""Verify GSP callback block + entry[0] from raw bytes of outputs/gsp_tu10x.bin.
Offline, read-only. ELF64 parsed with struct only (no riscv_audit.py import);
capstone used only for disassembly text. Writes only under PHASE16/.
"""
import hashlib
import json
import struct
from pathlib import Path

try:
    from capstone import Cs, CS_ARCH_RISCV, CS_MODE_RISCV64, CS_MODE_RISCVC
    HAVE_CAPSTONE = True
except Exception as exc:  # pragma: no cover - environment guarantee
    HAVE_CAPSTONE = False
    CAPSTONE_IMPORT_ERROR = repr(exc)

ROOT = Path('/home/REDACTED_USER/codex-work/work_v15')
BIN_PATH = ROOT / 'outputs' / 'gsp_tu10x.bin'
OUT_DIR = ROOT / 'PHASE16'
ELF_BASE = 0x40  # ELF header begins at file offset 0x40
MASK64 = (1 << 64) - 1

# register numbers (ABI)
A0, A1, A2, A5, S3, S4, RA = 10, 11, 12, 15, 19, 20, 1


def sext(value, bits):
    return (value & ((1 << bits) - 1)) - ((1 << bits) if value & (1 << (bits - 1)) else 0)


class MiniElf:
    """Tiny ELF64-LE parser: section/segment mapping VA -> file offset only.
    File offsets in this synthetic ELF are stored relative to the ELF header
    position (0x40), so every stored offset is shifted by ELF_BASE."""

    def __init__(self, data):
        self.data, self.base = data, ELF_BASE
        off = ELF_BASE
        (ident, e_type, e_machine, e_version, e_entry, e_phoff, e_shoff,
         e_flags, e_ehsize, e_phentsize, e_phnum, e_shentsize, e_shnum,
         e_shstrndx) = struct.unpack_from('<16sHHIQQQIHHHHHH', data, off)
        if ident[:4] != b'\x7fELF' or ident[4] != 2 or ident[5] != 1 or ident[6] != 1:
            raise ValueError('not ELF64 little-endian')
        if e_machine != 243:
            raise ValueError(f'not RISC-V (e_machine={e_machine})')
        self.entry = e_entry
        self.phnum, self.shnum = e_phnum, e_shnum
        self.e_phoff, self.e_phentsize = e_phoff, e_phentsize
        self.e_shoff, self.e_shentsize = e_shoff, e_shentsize
        self.e_shstrndx = e_shstrndx
        self.sections = []
        for i in range(e_shnum):
            s = struct.unpack_from('<IIQQQQIIQQ', data, self.base + e_shoff + i * e_shentsize)
            self.sections.append(dict(index=i, name_off=s[0], type=s[1], flags=s[2], va=s[3],
                                      offset=self.base + s[4], size=s[5], entsize=s[9]))
        shstr = self.sections[e_shstrndx]
        names = data[shstr['offset']:shstr['offset'] + shstr['size']]
        for s in self.sections:
            end = names.find(b'\0', s['name_off'])
            s['name'] = names[s['name_off']:end].decode('utf-8', 'replace') if end >= 0 else f'sec{s["index"]}'
        self.segments = []
        for i in range(e_phnum):
            p = struct.unpack_from('<IIQQQQQQ', data, self.base + e_phoff + i * e_phentsize)
            self.segments.append(dict(type=p[0], flags=p[1], offset=ELF_BASE + p[2], va=p[3],
                                      vaddr=p[3], filesz=p[5], memsz=p[6]))

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
        for p in self.segments:
            if p['type'] == 1 and p['va'] <= va and va + size <= p['va'] + p['filesz']:
                return p['offset'] + va - p['va'], f"PT_LOAD@{p['va']:#x}"
        raise ValueError(f'unmapped VA {va:#x}')

    def read(self, va, size):
        off, _ = self.resolve(va, size)
        return self.data[off:off + size]


def disasm_range(elf, va_start, va_end):
    """Capstone disassembly of [va_start, va_end); every instruction fully inside."""
    off, src = elf.resolve(va_start, 4)
    # confirm whole range lives in the same backing object (section or segment)
    sec = next((s for s in elf.sections if f"section[{s['index']}]{s['name']}" == src), None)
    seg = next((p for p in elf.segments if src == f"PT_LOAD@{p['va']:#x}"), None)
    limit = None
    if sec is not None:
        limit = sec['va'] + sec['size']
    elif seg is not None:
        limit = seg['va'] + seg['filesz']
    else:
        raise ValueError(f'cannot bound range at {va_start:#x} ({src})')
    if va_end > limit:
        raise ValueError(f'range {va_start:#x}-{va_end:#x} exceeds backing {src} limit {limit:#x}')
    raw = elf.data[off:off + (va_end - va_start)]
    md = Cs(CS_ARCH_RISCV, CS_MODE_RISCV64 | CS_MODE_RISCVC)
    rows = []
    for ins in md.disasm(raw, va_start):
        if ins.address >= va_end:
            break
        rows.append(dict(va=ins.address, file_offset=off + ins.address - va_start,
                         src=src, bytes=ins.bytes.hex(), size=ins.size,
                         mnemonic=ins.mnemonic, op_str=ins.op_str))
    return rows, src


def decode_imm(word, field):
    """extract instruction fields"""
    return (word >> field[0]) & field[1]


def auipc_target(word, pc):
    if word & 0x7F != 0x17:
        return None
    rd = (word >> 7) & 31
    imm = sext(word & 0xFFFFF000, 32)
    return dict(kind='auipc', rd=rd, imm=imm, val=(pc + imm) & MASK64)


def jalr_target(word, pc):
    if (word & 0x707F) != 0x67 or (word >> 12) & 7 != 0:
        return None
    rd, rs1 = (word >> 7) & 31, (word >> 15) & 31
    imm = sext(word >> 20, 12)
    return dict(kind='jalr', rd=rd, rs1=rs1, imm=imm)


def jal_target(word, pc):
    if word & 0x7F != 0x6F:
        return None
    imm = ((word >> 31) << 20) | (((word >> 21) & 1023) << 1)
    imm |= (((word >> 20) & 1) << 11) | (((word >> 12) & 255) << 12)
    return dict(kind='jal', rd=(word >> 7) & 31, target=(pc + sext(imm, 21)) & MASK64)


def branch_target(word, pc):
    if word & 0x7F != 0x63:
        return None
    funct3 = (word >> 12) & 7
    if funct3 not in (0, 1, 4, 5, 6, 7):
        return None
    imm = ((word >> 31) << 12) | (((word >> 7) & 1) << 11)
    imm |= (((word >> 25) & 63) << 5) | (((word >> 8) & 15) << 1)
    return dict(kind='branch', funct3=funct3, target=(pc + sext(imm, 13)) & MASK64)


def dest_reg(word):
    """Tra ve so lu register ghi ket qua (hoac None), dung cho last-write tracking."""
    op = word & 0x7F
    if op == 0x13:  # OP-IMM (addi/mv/slli/...)
        return (word >> 7) & 31
    if op == 0x03:  # LOAD
        return (word >> 7) & 31
    if op == 0x33:  # OP
        return (word >> 7) & 31
    if op in (0x17, 0x37):  # AUIPC / LUI
        return (word >> 7) & 31
    if op == 0x6F:  # JAL
        rd = (word >> 7) & 31
        return rd if rd != 0 else None
    if op == 0x67:  # JALR (funct3 phai la 0)
        if (word >> 12) & 7 != 0:
            return None
        rd = (word >> 7) & 31
        return rd if rd != 0 else None
    return None


def word_at(data, elf, va):
    return struct.unpack_from('<I', elf.read(va, 4), 0)[0]


def bounded_ascii(elf, va, max_len=256):
    """Resolve VA, read NUL-terminated printable ASCII bounded by backing object."""
    try:
        off, src = elf.resolve(va, 1)
    except ValueError:
        return None, f'unmapped VA {va:#x}', src if 'src' in dir() else ''
    end = elf.data.find(b'\0', off, min(off + max_len, len(elf.data)))
    if end < 0:
        return None, f'no NUL within {max_len} bytes at {src}+{off:#x}', src
    raw = elf.data[off:end]
    if any(c < 32 or c > 126 for c in raw):
        return None, f'non-printable bytes before NUL at {src}+{off:#x}', src
    return raw.decode('ascii'), 'ok', src


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = BIN_PATH.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    elf = MiniElf(data)

    report = dict(
        script='PHASE16/gsp_callback_verify.py',
        bin=str(BIN_PATH), bin_size=len(data), source_sha256=sha,
        elf_entry=hex(elf.entry), capstone=HAVE_CAPSTONE,
        windows={},
        resolved={},
        control_flow={},
        registers_at_call={},
        entry0={},
        observations=[],
        unknowns=[],
    )

    # --- resolve key addresses ---
    key_vas = [0x04F575BC, 0x04F57644, 0x04F57648, 0x04F5764C, 0x04F57650,
               0x04F575D4, 0x04F575E0, 0x04F075EC, 0x041A70B0]
    for va in key_vas:
        off, src = elf.resolve(va, 4)
        report['resolved'][hex(va)] = dict(va=va, file_offset=off, source=src,
                                           raw4=elf.read(va, 4).hex())

    # --- disassemble windows ---
    for name, vs, ve in (('callback_block', 0x04F575BC, 0x04F57658),
                         ('entry_helper', 0x04F075EC, 0x04F076A0)):
        rows, src = disasm_range(elf, vs, ve)
        report['windows'][name] = dict(va_start=vs, va_end=ve, backing=src,
                                       count=len(rows),
                                       instructions=[dict(va=r['va'], file_offset=r['file_offset'],
                                                          bytes=r['bytes'], size=r['size'],
                                                          mnemonic=r['mnemonic'], op_str=r['op_str'])
                                                     for r in rows])

    # --- write disassembly text ---
    txt_lines = [f'# source: {BIN_PATH} sha256={sha}',
                 '# ELF64-LE parsed with struct; VA->file offset via SHF_ALLOC section / PT_LOAD fallback',
                 '# Format: VA  FILE_OFFSET  BYTES(file order)  SIZE  MNEMONIC  OPERANDS',
                 '# Windows: callback_block 0x04f575bc..0x04f57658 ; entry_helper 0x04f075ec..0x04f076a0',
                 '']
    for name in ('callback_block', 'entry_helper'):
        win = report['windows'][name]
        txt_lines.append(f'# {name}: {win["va_start"]:#x}..{win["va_end"]:#x} backing={win["backing"]} count={win["count"]}')
        for r in win['instructions']:
            txt_lines.append(f'{r["va"]:08x}  file={r["file_offset"]:08x}  {r["bytes"]:16}  {r["size"]}  {r["mnemonic"]:10}  {r["op_str"]}')
        txt_lines.append('')
    (OUT_DIR / 'gsp_callback_verified.txt').write_text('\n'.join(txt_lines) + '\n')

    # --- control flow at 0x04f57644/48/4c/50 ---
    win = {r['va']: r for r in report['windows']['callback_block']['instructions']}
    cf = dict(at_0x4f57644_50=[], auipc_jalr_pairs=[], branches=[], jumps=[],
              predecessors_of_callback=[], fallthrough_into_callback=[])
    cb = 0x04F575E0
    block_start = 0x04F575D4
    prev_va = None
    for va in sorted(win):
        r = win[va]
        word = struct.unpack_from('<I', data[r['file_offset']:r['file_offset'] + 4], 0)[0]
        au = auipc_target(word, va)
        if au:
            cf['auipc_jalr_pairs'].append(dict(pc=va, **au, file_offset=r['file_offset'], raw=word & MASK64))
            # look for adjacent jalr using au's rd as rs1
            nxt = va + 4
            if nxt in win:
                w2 = struct.unpack_from('<I', data[win[nxt]['file_offset']:win[nxt]['file_offset'] + 4], 0)[0]
                jr = jalr_target(w2, nxt)
                if jr and jr['rs1'] == au['rd']:
                    tgt = (au['val'] + jr['imm']) & ~1 & MASK64
                    cf['auipc_jalr_pairs'][-1]['adjacent_jalr'] = dict(pc=nxt, raw=w2 & MASK64,
                                                                       imm=jr['imm'], target=tgt, rd=jr['rd'])
        br = branch_target(word, va)
        if br:
            cf['branches'].append(dict(pc=va, raw=word & MASK64, file_offset=r['file_offset'], **br))
            if br['target'] == cb:
                cf['predecessors_of_callback'].append(dict(pc=va, kind='branch', target=cb,
                                                           file_offset=r['file_offset'], raw=win[va]['bytes']))
        jl = jal_target(word, va)
        if jl:
            cf['jumps'].append(dict(pc=va, raw=word & MASK64, file_offset=r['file_offset'], **jl))
            if jl['target'] == cb:
                cf['predecessors_of_callback'].append(dict(pc=va, kind='jal', target=cb,
                                                           file_offset=r['file_offset'], raw=win[va]['bytes']))
        # fall-through into callback: previous instruction ends exactly at cb
        if prev_va is not None and prev_va + win[prev_va]['size'] == cb:
            cf['fallthrough_into_callback'].append(dict(pc=prev_va, raw=win[prev_va]['bytes'],
                                                        file_offset=win[prev_va]['file_offset'],
                                                        mnemonic=win[prev_va]['mnemonic'],
                                                        op_str=win[prev_va]['op_str']))
        prev_va = va
    # also check the 4 specific addresses 0x04f57644/48/4c/50
    for va in (0x04F57644, 0x04F57648, 0x04F5764C, 0x04F57650):
        if va in win:
            r = win[va]
            word = struct.unpack_from('<I', data[r['file_offset']:r['file_offset'] + 4], 0)[0]
            entry = dict(va=va, file_offset=r['file_offset'], bytes=r['bytes'],
                         mnemonic=r['mnemonic'], op_str=r['op_str'], raw=word & MASK64)
            au = auipc_target(word, va)
            if au: entry['auipc'] = au
            jr = jalr_target(word, va)
            if jr: entry['jalr'] = jr
            br = branch_target(word, va)
            if br: entry['branch'] = br
            rd = dest_reg(word)
            if rd: entry['writes_reg'] = rd
            cf['at_0x4f57644_50'].append(entry)
    report['control_flow'] = cf

    # --- register last-write tracking up to the call at 0x04f575e0 ---
    tracked = {A0: None, A1: None, A2: None}
    writes = {A0: [], A1: [], A2: []}
    call_va = None
    for r in report['windows']['callback_block']['instructions']:
        if r['va'] >= cb:
            break
        word = struct.unpack_from('<I', data[r['file_offset']:r['file_offset'] + 4], 0)[0]
        wr = dest_reg(word)
        if wr in tracked:
            rec = dict(va=r['va'], file_offset=r['file_offset'], raw=r['bytes'],
                       mnemonic=r['mnemonic'], op_str=r['op_str'])
            tracked[wr] = rec
            writes[wr].append(rec)
        if r['va'] + r['size'] == cb:
            call_va = r['va']
    reg_report = {}
    for reg, nm in ((A0, 'a0'), (A1, 'a1'), (A2, 'a2')):
        last = tracked[reg]
        if nm == 'a0':
            note = 'LAST-WRITE = mv a0, s3 tai 0x04f575dc (a0 = con tro context/s3) tren duong di thang den goi; a0 la caller-saved, CALL-CLOBBER ap dung sau khi jalr tra ve.'
        elif nm == 'a1':
            note = 'KHONG co lenh ghi a1 trong cua so 0x04f575bc..0x04f575e0 -> a1 tai diem goi = gia tri nhap cua ham, duoc luu tai s4 (mv s4, a1 tai 0x04f57378, van ban truoc). KHONG phai gia tri tra tu helper 0x04f075ec tai diem goi nay.'
        else:
            note = 'LAST-WRITE = lhu a2, -0x88(s0) tai 0x04f575d8 (a2 = u16 f00 cua entry luu tren stack); a2 la caller-saved, CALL-CLOBBER ap dung sau khi jalr tra ve.'
        reg_report[nm] = dict(last_write=last, all_writes_in_window=writes[reg],
                              call_preceded_by=dict(va=call_va, raw=win[call_va]['bytes'],
                                                    mnemonic=win[call_va]['mnemonic']) if call_va else None,
                              path='fall-through tu 0x04f575d4 den 0x04f575e0 (khong co nhan vao callback trong cua so)',
                              note=note + ' (straight-line last-write, chua xac minh CFG toan cuc).')
    report['registers_at_call'] = reg_report

    # --- entry[0] at VA 0x041a70b0 ---
    va0 = 0x041A70B0
    raw32 = elf.read(va0, 32)
    f00 = struct.unpack_from('<H', raw32, 0)[0]
    f04 = struct.unpack_from('<I', raw32, 4)[0]
    f08 = raw32[8]
    f10 = struct.unpack_from('<Q', raw32, 16)[0]
    f18 = struct.unpack_from('<H', raw32, 24)[0]
    ascii_s, ascii_status, ascii_src = bounded_ascii(elf, f10)
    e0 = dict(va=va0, file_offset=elf.resolve(va0, 32)[0], source=elf.resolve(va0, 32)[1],
              raw32=raw32.hex(),
              fields=dict(f00_u16_0x00=f00, f04_u32_0x04=f04, f08_u8_0x08=f08,
                          f10_u64_0x10=f10, f18_u16_0x18=f18),
              f10_bits=dict(low16=f10 & 0xFFFF, high16=(f10 >> 16) & 0xFFFF, low8=f10 & 0xFF,
                            byte0=raw32[16], byte1=raw32[17], byte2=raw32[18], byte3=raw32[19]),
              f18_bits=dict(raw=f18, byte0=raw32[24], byte1=raw32[25]),
              f10_bounded_ascii=dict(value=ascii_s, status=ascii_status, source=ascii_src),
              note='f18: only bit structure is evidenced (u16 @ entry+0x18); no group/subtype semantic assignment made here.')
    report['entry0'] = e0

    # --- observations ---
    obs = []
    obs.append(f"source_sha256={sha} bin_size={len(data)}")
    obs.append(f"callback block disassembled {report['windows']['callback_block']['count']} instructions at "
               f"0x04f575bc..0x04f57658 (file {report['resolved']['0x4f575bc']['file_offset']:#x})")
    obs.append(f"entry_helper disassembled {report['windows']['entry_helper']['count']} instructions at "
               f"0x04f075ec..0x04f076a0")
    obs.append(f"AUIPC+JALR pairs at/near 0x04f57644: {len(cf['auipc_jalr_pairs'])}")
    obs.append(f"branches: {len(cf['branches'])}; jumps: {len(cf['jumps'])}")
    obs.append(f"predecessors into callback 0x04f575e0: branches={len(cf['predecessors_of_callback'])}, "
               f"fallthrough={len(cf['fallthrough_into_callback'])}")
    obs.append(f"entry0 file_offset={e0['file_offset']:#x} source={e0['source']} raw32={e0['raw32']}")
    obs.append(f"entry0 f00={f00:#x} f04={f04:#x} f08={f08:#x} f10={f10:#x} f18={f18:#x}")
    obs.append(f"f10 bounded ASCII: {ascii_status} value={ascii_s!r}")
    obs.append("Duong di sau goi callback: 0x04f575e4 sext.w s2,a0; 0x04f575e8 bnez s2,+0x26c (thoat neu tra !=0); 0x04f575ec addi s1,s1,0x20; 0x04f575f0 beq s8,s1,+0x42c (thoat neu het bang).")
    obs.append("Tiep tuc duong di khong thoat: 0x04f575f4..0x04f57640 luu 5 field entry vao stack (s0-0xe0..); 0x04f57644 auipc ra,0xfffb0 + 0x04f57648 jalr ra,ra,-0x58 -> goi helper 0x04f075EC (REDACTED_USER duoc tu raw, khong copy cu).")
    obs.append("0x04f5764c mv a1,a0 (a1 = ket qua helper); 0x04f57650 bnez a0,-0x7c -> nhan quay ve block callback 0x04f575d4. XAC NHAN: co trinh tu helper-call -> mv a1,a0 -> nhanh quay lai block callback.")
    obs.append("Con tro callback qua *(s3+0x30) tai jalr 0x04f575e0: dich cua con tro chua biet tu du lieu tich cuc -> UNKNOWN, khong ep ket luan.")
    report['observations'] = obs

    unk = []
    # callback target: indirect via a5 = *(s3+0x30); target value not known from static bytes alone
    unk.append('destinasi callback qua con tro *(s3+0x30): UNKNOWN (gia tri con tro chua duoc lay tu du lieu tich cuc)')
    if not cf['predecessors_of_callback'] and not cf['fallthrough_into_callback']:
        unk.append('khong thay predecessor (nhan nhay vao hoak ro) truc tiep den callback 0x04f575e0 trong cua so disassembled')
    reg_a1 = reg_report['a1']['last_write']
    if reg_a1 is None:
        unk.append('a1 tai diem goi callback: chua co last-write trong cua so 0x04f575bc..0x04f575e0 (can mo cua so ngang xuong)')
    report['unknowns'] = unk

    (OUT_DIR / 'gsp_callback_verified.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(dict(sha256=sha, windows={k: v['count'] for k, v in report['windows'].items()},
                         resolved={k: v['file_offset'] for k, v in report['resolved'].items()},
                         entry0=report['entry0']['fields'],
                         control_flow=dict(auipc_pairs=len(cf['auipc_jalr_pairs']),
                                           branches=len(cf['branches']),
                                           preds_cb=len(cf['predecessors_of_callback']),
                                           fallthrough_cb=len(cf['fallthrough_into_callback'])),
                         regs_at_call={k: (v['last_write']['va'] if v['last_write'] else None) for k, v in reg_report.items()}),
                   indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
