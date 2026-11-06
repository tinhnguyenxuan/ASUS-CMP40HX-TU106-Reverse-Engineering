#!/usr/bin/env python3
"""D2: dataflow for each `sb *,0x6EA(reg)` writer.

For each site, walk back within its derived function and record every
instruction that writes the destination register (rd == site's rs1) or the
value register (rd == site's rs2, when the store is not `zero`).
Also record the object-base derivation: how rs1 itself was built
(ld from a0/a1 = `this`/`params`, or a chain of adds/lui).
"""
import re, json

DIS = 'gsp.dis'
SITES = ['4a128d4','4b6f3ec','4c89784','4c95fdc','5306de4',
         '530713c','5307604','53076c4','5382d2c','5382f08','538314c']

pat = re.compile(r'^\s*([0-9a-f]+):\s*((?:[0-9a-f]{2} )+)\s*\t?([a-z0-9.]+)?\s*(.*)$')


def load():
    ins, order = {}, []
    for ln in open(DIS, errors='replace'):
        m = pat.match(ln)
        if not m:
            continue
        a = int(m.group(1), 16)
        ins[a] = (m.group(2).replace(' ', ''), (m.group(3) or '').strip(), (m.group(4) or '').strip())
        order.append(a)
    order.sort()
    return ins, order


def prologue(ins):
    pr = []
    for a, (raw, mn, ops) in ins.items():
        if len(raw) == 8:
            w = int.from_bytes(bytes.fromhex(raw), 'little')
            if (w & 0x7F) == 0x13 and ((w >> 7) & 0x1F) == 2 and ((w >> 15) & 0x1F) == 2:
                pr.append(a)
    return sorted(pr)


RD_RE = re.compile(r'^([a-z][a-z0-9]{1,2})\b')
MEM = re.compile(r'^([a-z][a-z0-9]{1,2}),\s*(-?0x[0-9a-f]+|-?\d+)\(([a-z][a-z0-9]{1,2})\)$')


def dest_of(mn, ops):
    """Return (dest_reg, source_regs) for common RISC-V forms; None if not a writer we model."""
    ops = ops.split('#')[0].strip()
    if not ops:
        return None
    parts = [p.strip() for p in ops.split(',')]
    if mn in ('sb', 'sh', 'sw', 'sd'):
        return None  # stores are captured separately
    if mn in ('beqz', 'bnez', 'j', 'jal', 'jalr', 'ret', 'nop', 'slli', 'srli', 'srai', 'seqz', 'snez'):
        if mn == 'jalr':
            return ('ra', parts[0], [])
        return None
    if mn.startswith('b'):
        return None
    if not parts:
        return None
    d = parts[0]
    if not re.match(r'^[a-z][a-z0-9]{0,2}$', d):
        return None
    # source = first register operand after dest
    srcs = [p for p in parts[1:] if re.match(r'^[a-z][a-z0-9]{0,2}$', p)]
    return (d, srcs[0] if srcs else None, srcs)


def main():
    ins, order = load()
    pr = prologue(ins)
    out = []
    for s in SITES:
        a = int(s, 16)
        lo = max([p for p in pr if p <= a], default=None)
        hi = min([p for p in pr if p > a], default=None)
        raw, mn, ops = ins[a]
        m = re.match(r'^(zero|[a-z][a-z0-9]{0,2}),\s*0x6ea\(([a-z][a-z0-9]{0,2})\)$', ops)
        vreg, breg = m.group(1), m.group(2)
        rec = dict(site=hex(a), raw=raw, asm=f"{mn} {ops}", value_reg=vreg,
                   base_reg=breg, fn=hex(lo), fn_end=hex(hi), fn_size=hi - lo,
                   base_provenance=[], value_provenance=[])

        # base-reg provenance: last writer of breg before the site
        for t in [breg]:
            for aa in reversed([x for x in order if lo <= x < a]):
                r, mn2, o2 = ins[aa]
                dm = dest_of(mn2, o2)
                if dm and dm[0] == t:
                    rec['base_provenance'].append(dict(addr=hex(aa), asm=f"{mn2} {o2}", raw=r))
                    if dm[1] and dm[1] != t:
                        t = dm[1]
                    else:
                        break
                    if len(rec['base_provenance']) > 12:
                        break
        # value-reg provenance (skip if zero)
        if vreg != 'zero':
            t = vreg
            for aa in reversed([x for x in order if lo <= x < a]):
                r, mn2, o2 = ins[aa]
                dm = dest_of(mn2, o2)
                if dm and dm[0] == t:
                    rec['value_provenance'].append(dict(addr=hex(aa), asm=f"{mn2} {o2}", raw=r))
                    if dm[1] and dm[1] != t:
                        t = dm[1]
                    else:
                        break
                    if len(rec['value_provenance']) > 12:
                        break
        out.append(rec)
    json.dump(out, open('writers_dataflow.json', 'w'), indent=2)
    for r in out:
        print(f"\n=== {r['site']}  {r['asm']}   fn {r['fn']}..{r['fn_end']} ({r['fn_size']}B)")
        print("  base chain:")
        for p in r['base_provenance']:
            print(f"    {p['addr']}  {p['asm']}")
        if r['value_provenance']:
            print("  value chain:")
            for p in r['value_provenance']:
                print(f"    {p['addr']}  {p['asm']}")


if __name__ == '__main__':
    main()
