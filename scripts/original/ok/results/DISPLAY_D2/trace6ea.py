#!/usr/bin/env python3
"""D2: trace writers to *(base+0x6EA) in GSP-RM 615.78.08.

Firmware is stripped (0 symbols, 7 section markers). So "function boundary" is
derived by scanning .rm_text for prologues: RV32/RV64 `addi sp,sp,-N`
(0x??010113) which begin every compiled function in this blob.
ponytail: prologue heuristic, upgrade to CFG-based if a site lands ambiguous.
"""
import re, sys, json

DIS = 'gsp.dis'
RM_TEXT = (0x4588000, 0x55C1000)   # vaddr start/end of .section_task_rm_elf_text_instance
SITES = ['4a128d4','4b6f3ec','4c89784','4c95fdc','5306de4',
         '530713c','5307604','53076c4','5382d2c','5382f08','538314c']


def load():
    """-> {vaddr:int -> (rawbytes:str, mnem:str, ops:str, lineno)}"""
    ins = {}
    pat = re.compile(r'^\s*([0-9a-f]+):\s*((?:[0-9a-f]{2} )+)\s*\t?([a-z0-9.]+)?\s*(.*)$')
    for ln in open(DIS, errors='replace'):
        m = pat.match(ln)
        if not m:
            continue
        a = int(m.group(1), 16)
        raw = m.group(2).replace(' ', '')
        ins[a] = (raw, (m.group(3) or '').strip(), (m.group(4) or '').strip())
    return ins


def prologues(ins):
    """vaddrs whose raw encoding is `addi sp, sp, -N` (rd=x2, rs1=x2, opcode 0x13)."""
    out = []
    for a, (raw, mn, ops) in ins.items():
        if len(raw) == 8:
            w = int.from_bytes(bytes.fromhex(raw), 'little')
            if (w & 0x7F) == 0x13 and ((w >> 7) & 0x1F) == 2 and ((w >> 15) & 0x1F) == 2 and (w >> 20) & 0x800:
                out.append(a)
    return sorted(out)


if __name__ == '__main__':
    ins = load()
    pr = prologues(ins)
    prs = set(pr)
    print(f"decoded {len(ins)} instructions in file")
    print(f"prologues (addi sp,sp,-N): {len(pr)}")
    print("\n=== 11 byte-0x6EA writers ===")
    res = []
    for s in SITES:
        a = int(s, 16)
        # walk back to nearest prologue
        lo = max([p for p in pr if p <= a], default=None)
        # walk forward to next prologue = fn end
        hi = min([p for p in pr if p > a], default=None)
        raw, mn, ops = ins.get(a, ('?', '?', '?'))
        res.append(dict(site=hex(a), raw=raw, asm=f"{mn} {ops}",
                        fn=hex(lo) if lo else None, fn_end=hex(hi) if hi else None,
                        size=(hi - lo) if (lo and hi) else None))
        print(f"  {hex(a)}  {raw:<8}  {mn} {ops:<18} fn={hex(lo) if lo else '?'}"
              f" end={hex(hi) if hi else '?'} size={hi-lo if (lo and hi) else '?'}")
    json.dump(res, open('writers_sites.json', 'w'), indent=2)
