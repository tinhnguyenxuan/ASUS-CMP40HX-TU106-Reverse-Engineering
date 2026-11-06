#!/usr/bin/env python3
"""Offline read-only audit of a CMP40HX Hermes research directory.
Usage: python cmp40hx_v15_independent_audit.py /path/to/cmp40hx_research
Does not execute any project scripts, access GPU devices, or modify source files.
"""
import collections
import json
import pathlib
import struct
import sys

TARGET = 0x04F575FC
VADDR_BASE = 0x04000000  # Verified for this firmware at file offset 0xF575FC


def jal_target(word, pc):
    imm = (((word >> 31) & 1) << 20)
    imm |= (((word >> 21) & 0x3ff) << 1)
    imm |= (((word >> 20) & 1) << 11)
    imm |= (((word >> 12) & 0xff) << 12)
    if imm & (1 << 20):
        imm -= (1 << 21)
    return pc + imm, (word >> 7) & 31, imm


def main(root):
    r = pathlib.Path(root)
    fw = (r / 'outputs/gsp_tu10x.bin').read_bytes()
    if fw[TARGET - VADDR_BASE: TARGET - VADDR_BASE + 4] != bytes.fromhex('b7741a04'):
        raise ValueError('Firmware build/virtual address mapping differs; do not scan with VADDR_BASE until section mapping is verified')
    jumps = []
    for off in range(0, len(fw) - 3, 4):
        ins = struct.unpack_from('<I', fw, off)[0]
        if ins & 0x7f == 0x6f:
            dest, rd, imm = jal_target(ins, VADDR_BASE + off)
            if dest == TARGET:
                jumps.append({'pc': f'0x{VADDR_BASE+off:08X}', 'target': f'0x{dest:08X}', 'rd': rd, 'relative_offset': imm, 'instruction': f'0x{ins:08X}', 'kind': 'call' if rd else 'jump'})

    f = json.loads((r / 'FUSE/fuse2.json').read_text())
    regs = {int(k): v for k, v in f['regs'].items()}
    poison = set(f['poison'])
    classify = collections.Counter('poison' if v in poison else 'zero' if v == 0 else 'data' for v in regs.values())
    meaningful = [k for k, v in regs.items() if v not in poison]
    ones = [k for k, v in regs.items() if v == 1]

    uc = (r / 'outputs/ucodes_tu10x.bin').read_bytes()
    b6 = uc[0x0B7C00:0x0D6700]
    b8 = uc[0x0F5400:0x113F00]
    diffs = [i for i in range(min(len(b6), len(b8))) if b6[i] != b8[i]]

    u = json.loads((r / 'UNKNOWN_DATABASE.json').read_text())
    stats = collections.Counter(x['status'] for x in u['items'])
    out = {
        'read_only': True,
        'gsp_mapping_verified': True,
        'jal_xrefs_to_dispatcher': jumps,
        'fuse': {
            'dumped_words': len(regs),
            'dumped_bytes': len(regs) * 4,
            'requested_span_bytes': f.get('span'),
            'first_to_last_dumped_offset': [hex(min(regs)), hex(max(regs))],
            'last_nonpoison_offset': hex(max(meaningful)),
            'class_counts': dict(classify),
            'words_equal_one': len(ones),
            'meaning_of_one_values_proven': False,
        },
        'ucodes_blob6_blob8': {'bytes_compared': min(len(b6),len(b8)), 'different_byte_positions':len(diffs), 'note':'different bytes need not be contiguous'},
        'unknown_database': {'total':len(u['items']), 'statuses':dict(stats)},
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python cmp40hx_v15_independent_audit.py /path/to/research_dir')
    main(sys.argv[1])
